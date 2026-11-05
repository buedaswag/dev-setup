"""The secret gate: a credential must not leave this machine.

A secret leaks when it is pushed, not when it is committed. A commit is a local save
point, and blocking one only grows the uncommitted tree. So the gate is split:

- `.githooks/pre-commit` scans the work tree and reports. It never blocks.
- `.githooks/pre-push` scans every commit not yet on the remote and blocks. It fails
  closed: if the scan cannot run, the push does not go.

`scripts/secret_scan.sh` is where the scanner lives; both hooks call it. These tests
drive the script directly for what the scan sees, and drive real `git commit` and
`git push` in a scratch repo for what each hook does with the result.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS = REPO_ROOT / ".githooks"
SCANNER_SCRIPT = REPO_ROOT / "scripts" / "secret_scan.sh"

# A GitHub personal access token by shape: `ghp_` and 36 random alphanumerics.
# Randomly generated for this test, never issued by anyone, matches no account.
#
# The first version of this fixture was `AKIAIOSFODNN7EXAMPLE`, and the test failed
# against a working hook: that string is AWS's own documentation example and
# gitleaks allowlists it deliberately, precisely so docs and tutorials do not trip
# every scanner on earth. Worth knowing before planting a fixture -- a scanner that
# fires on the canonical example is a scanner nobody keeps switched on.
#
# The trailing `gitleaks:allow` is load-bearing: without it the gate finds this
# fixture in its own test file and blocks every push of this repo. An exception
# for one known-fake line, inline where the line is, and nowhere else -- not a
# .gitleaks.toml rule that would quietly excuse this whole file forever.
PLANTED_SECRET = 'github_token = "ghp_Ku4mR2xQ7vTnL9bWsZ0aYcHj5dEgF8pO1iN3"\n'  # gitleaks:allow

# Points the scanner at a docker that does not exist: the scan cannot run.
NO_DOCKER = {"SECRET_SCAN_DOCKER": "/nonexistent/docker"}


def run_scanner(target, env=None):
    return subprocess.run(
        [str(SCANNER_SCRIPT), str(target)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=dict(os.environ, **(env or {})),
    )


class ScratchRepo:
    """A clone-like repo with this repo's real pre-commit and pre-push installed.

    Only those two hooks: post-commit redraws this repo's pipeline diagram, which
    has no business running in a scratch repo. `scripts/` is linked in because the
    hooks call `scripts/secret_scan.sh` from the work tree root, as they do here.
    """

    def __init__(self, test):
        tmp = tempfile.TemporaryDirectory()
        test.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.remote = base / "remote.git"
        self.path = base / "work"
        self.path.mkdir()

        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        self.git("init", "-q", "-b", "master")
        self.git("config", "user.name", "test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", ".githooks")
        self.git("remote", "add", "origin", str(self.remote))

        hooks = self.path / ".githooks"
        hooks.mkdir()
        for name in ("pre-commit", "pre-push"):
            (hooks / name).symlink_to(HOOKS / name)
        (self.path / "scripts").symlink_to(REPO_ROOT / "scripts")
        (self.path / ".git" / "info" / "exclude").write_text(".githooks\nscripts\n")

    def git(self, *args, env=None, check=True):
        result = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            env=dict(os.environ, **(env or {})),
        )
        if check and result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed:\n{result.stderr}")
        return result

    def commit(self, name, content, env=None, no_verify=False):
        (self.path / name).write_text(content)
        self.git("add", name)
        flags = ["--no-verify"] if no_verify else []
        return self.git("commit", "-q", *flags, "-m", f"add {name}", env=env, check=False)

    def push(self, *refspec, env=None, no_verify=False):
        flags = ["--no-verify"] if no_verify else []
        return self.git("push", "-q", *flags, "origin", *(refspec or ["master"]),
                        env=env, check=False)

    def remote_has(self, ref):
        return subprocess.run(
            ["git", "-C", str(self.remote), "rev-parse", "--verify", "-q", ref],
            capture_output=True,
        ).returncode == 0

    def commits(self):
        return int(self.git("rev-list", "--count", "HEAD").stdout)


class TestWhatTheScanSees(unittest.TestCase):
    """The work tree scan pre-commit runs. Exit code: 0 clean, non-zero otherwise."""

    def test_planted_secret_is_found_and_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "config.sh").write_text(PLANTED_SECRET)
            result = run_scanner(tmp)

        self.assertNotEqual(
            result.returncode, 0,
            f"scan exited 0 on a planted token.\nstdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertIn("config.sh", result.stdout + result.stderr,
                      "scan found something but did not name the file")

    def test_clean_tree_passes(self):
        """A scan that flags everything is not a scan, it is a broken hook."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("# just prose\n\nno secrets here\n")
            result = run_scanner(tmp)

        self.assertEqual(
            result.returncode, 0,
            f"scan flagged a clean tree.\nstdout: {result.stdout}\nstderr: {result.stderr}",
        )

    def test_gitignored_files_are_not_scanned(self):
        """Only what git would commit. Ignored junk is noise, and noise kills gates.

        Found the hard way: the first version mounted the directory and scanned
        everything, so it flagged the planted token inside this file's compiled
        `__pycache__/*.pyc` -- a file `.gitignore` excludes and git will never
        commit. The `gitleaks:allow` comment cannot save it either, because
        comments do not survive into bytecode.

        The same bug would flag `node_modules`, `.venv` and every build artifact
        in any repo this hook is installed in, and a gate that cries wolf is a
        gate I switch off. So the scan covers tracked and untracked-but-not-
        ignored files, which is exactly the set a commit can carry.
        """
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            (Path(tmp) / ".gitignore").write_text("secrets-here/\n")
            ignored = Path(tmp) / "secrets-here"
            ignored.mkdir()
            (ignored / "leak.txt").write_text(PLANTED_SECRET)
            result = run_scanner(tmp)

        self.assertEqual(
            result.returncode, 0,
            "scan flagged a gitignored file. Nothing there can reach a commit, "
            f"so this is a false positive.\nstdout: {result.stdout}\n{result.stderr}",
        )

    def test_untracked_files_are_still_scanned(self):
        """Not-yet-added is not safe: `git add -A` is one keystroke away."""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            (Path(tmp) / "fresh.sh").write_text(PLANTED_SECRET)
            result = run_scanner(tmp)

        self.assertNotEqual(result.returncode, 0, "scan ignored an untracked file carrying a secret")

    def test_this_repos_own_tree_is_clean(self):
        """The scan, run against the thing it guards. Fails the day I paste a token."""
        result = run_scanner(REPO_ROOT)
        self.assertEqual(
            result.returncode, 0,
            f"secrets found in this repo's work tree:\n{result.stdout}\n{result.stderr}",
        )

    def test_missing_scanner_is_not_a_pass(self):
        """No scanner is "could not scan", never "clean". The hooks decide what that costs."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("clean\n")
            result = run_scanner(tmp, env=NO_DOCKER)

        self.assertNotEqual(result.returncode, 0, "scan exited 0 with no scanner available")

    def test_scanner_image_is_pinned_by_digest(self):
        """A floating tag means the gate silently changes under me.

        `:latest` also re-pulls, which turns a 30ms hook into a network round trip
        at every commit.
        """
        source = SCANNER_SCRIPT.read_text()
        self.assertNotRegex(
            source,
            r"gitleaks:(latest|v?\d)",
            "scanner image is pinned by tag, not digest -- use "
            "ghcr.io/gitleaks/gitleaks@sha256:...",
        )
        self.assertRegex(
            source,
            r"gitleaks@sha256:[0-9a-f]{64}",
            "no digest-pinned gitleaks image found in scripts/secret_scan.sh",
        )

    def test_nothing_builds_anything(self):
        """Pull-and-run only. A hook that builds is a hook I will disable."""
        source = "".join(p.read_text() for p in (HOOKS / "pre-commit", HOOKS / "pre-push", SCANNER_SCRIPT))
        for forbidden in ("docker build", "docker compose", "Dockerfile"):
            self.assertNotIn(forbidden, source, f"`{forbidden}` found -- pull and run, never build")


class TestPreCommitReports(unittest.TestCase):
    """pre-commit says what it found and lets the commit through, always."""

    def test_hook_exists_and_is_executable(self):
        hook = HOOKS / "pre-commit"
        self.assertTrue(hook.exists(), f"{hook} does not exist")
        self.assertTrue(hook.stat().st_mode & 0o111, f"{hook} is not executable")

    def test_commit_carrying_a_secret_goes_through_and_says_so(self):
        repo = ScratchRepo(self)
        result = repo.commit("config.sh", PLANTED_SECRET)

        self.assertEqual(result.returncode, 0, f"pre-commit blocked the commit:\n{result.stderr}")
        self.assertEqual(repo.commits(), 1)
        self.assertIn("config.sh", result.stderr, "pre-commit did not name the file it found")
        self.assertIn("push", result.stderr.lower(), "pre-commit did not say the push will block")

    def test_commit_without_a_scanner_goes_through_and_says_so(self):
        repo = ScratchRepo(self)
        result = repo.commit("notes.md", "clean\n", env=NO_DOCKER)

        self.assertEqual(result.returncode, 0, f"pre-commit blocked the commit:\n{result.stderr}")
        self.assertEqual(repo.commits(), 1)
        self.assertIn("could not run", result.stderr, "pre-commit hid that the scan never ran")

    def test_clean_commit_is_quiet(self):
        repo = ScratchRepo(self)
        result = repo.commit("notes.md", "clean\n")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.strip(), "", "a clean commit should print nothing")


class TestPrePushBlocks(unittest.TestCase):
    """pre-push scans the commits not yet on the remote and refuses the push on any finding."""

    def test_hook_exists_and_is_executable(self):
        hook = HOOKS / "pre-push"
        self.assertTrue(hook.exists(), f"{hook} does not exist")
        self.assertTrue(hook.stat().st_mode & 0o111, f"{hook} is not executable")

    def test_push_of_a_commit_carrying_a_secret_is_rejected(self):
        repo = ScratchRepo(self)
        repo.commit("config.sh", PLANTED_SECRET)
        result = repo.push()

        self.assertNotEqual(result.returncode, 0, "push carrying a secret went through")
        self.assertFalse(repo.remote_has("master"), "the remote received the commit anyway")
        self.assertIn("config.sh", result.stderr, "pre-push blocked but did not name the file")

    def test_clean_push_goes_through(self):
        repo = ScratchRepo(self)
        repo.commit("notes.md", "clean\n")
        result = repo.push()

        self.assertEqual(result.returncode, 0, f"pre-push blocked a clean push:\n{result.stderr}")
        self.assertTrue(repo.remote_has("master"))

    def test_a_secret_deleted_in_a_later_commit_still_blocks(self):
        """It scans the commits, not the tree: the deleted token is still in what gets pushed."""
        repo = ScratchRepo(self)
        repo.commit("config.sh", PLANTED_SECRET)
        repo.git("rm", "-q", "config.sh")
        repo.git("commit", "-q", "-m", "remove config.sh")
        result = repo.push()

        self.assertNotEqual(result.returncode, 0, "the token is in history and the push went through")
        self.assertFalse(repo.remote_has("master"))

    def test_commits_already_on_the_remote_are_not_rescanned(self):
        """Scope is what this push adds. What the remote already has was this check's job then."""
        repo = ScratchRepo(self)
        repo.commit("config.sh", PLANTED_SECRET)
        repo.push(no_verify=True)
        repo.commit("notes.md", "clean\n")
        result = repo.push()

        self.assertEqual(result.returncode, 0,
                         f"pre-push rescanned a commit already on the remote:\n{result.stderr}")

    def test_push_without_a_scanner_is_rejected(self):
        """Fail closed: a push that could not be scanned does not go."""
        repo = ScratchRepo(self)
        repo.commit("notes.md", "clean\n")
        result = repo.push(env=NO_DOCKER)

        self.assertNotEqual(result.returncode, 0, "push went through with no scanner -- it failed open")
        self.assertFalse(repo.remote_has("master"))

    def test_deleting_a_branch_scans_nothing(self):
        """A deletion carries no commits, so there is nothing to scan and no scanner needed."""
        repo = ScratchRepo(self)
        repo.commit("notes.md", "clean\n")
        repo.git("branch", "feature")
        repo.push("master", "feature", no_verify=True)
        result = repo.push(":feature", env=NO_DOCKER)

        self.assertEqual(result.returncode, 0, f"deleting a branch was blocked:\n{result.stderr}")
        self.assertFalse(repo.remote_has("feature"))


if __name__ == "__main__":
    unittest.main()
