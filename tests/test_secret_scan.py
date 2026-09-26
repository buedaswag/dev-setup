"""The pre-commit gate: a credential in the work tree must not reach a commit.

`sync.sh` commits on its own from a Stop hook, and I commit by hand all day. Either
path can carry a token into version control, and once it is committed and pushed the
only remaining move is rewriting history. A scan in CI runs after that point, so it
is a backstop, not a gate. The gate is here, before the commit, on this machine.

These tests drive `.githooks/pre-commit` through its one seam: it scans the directory
given as argv[1], defaulting to the repo root. Everything else -- which scanner, in
what container, pinned how -- is an implementation detail these tests pin down only
where getting it wrong would silently stop the gating.
"""

import re
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".githooks" / "pre-commit"

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
# fixture in its own test file and blocks every commit to this repo. An exception
# for one known-fake line, inline where the line is, and nowhere else -- not a
# .gitleaks.toml rule that would quietly excuse this whole file forever.
PLANTED_SECRET = 'github_token = "ghp_Ku4mR2xQ7vTnL9bWsZ0aYcHj5dEgF8pO1iN3"\n'  # gitleaks:allow


def run_hook(target):
    return subprocess.run(
        [str(HOOK), str(target)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


class TestSecretScanGate(unittest.TestCase):
    def test_hook_exists_and_is_executable(self):
        self.assertTrue(HOOK.exists(), f"{HOOK} does not exist")
        self.assertTrue(HOOK.stat().st_mode & 0o111, f"{HOOK} is not executable")

    def test_planted_secret_blocks_the_commit(self):
        """The whole plan in one test: a credential in the tree fails the hook."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "config.sh").write_text(PLANTED_SECRET)
            result = run_hook(tmp)

        self.assertNotEqual(
            result.returncode,
            0,
            "hook exited 0 on a tree containing a planted AWS key -- the commit "
            f"would have gone through.\nstdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertIn(
            "config.sh",
            result.stdout + result.stderr,
            "hook blocked the commit but did not name the offending file",
        )

    def test_clean_tree_passes(self):
        """A gate that blocks everything is not a gate, it is a broken hook."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("# just prose\n\nno secrets here\n")
            result = run_hook(tmp)

        self.assertEqual(
            result.returncode,
            0,
            f"hook blocked a clean tree.\nstdout: {result.stdout}\nstderr: {result.stderr}",
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
        import subprocess as sp
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            sp.run(["git", "init", "-q"], cwd=tmp, check=True)
            (Path(tmp) / ".gitignore").write_text("secrets-here/\n")
            ignored = Path(tmp) / "secrets-here"
            ignored.mkdir()
            (ignored / "leak.txt").write_text(PLANTED_SECRET)

            result = run_hook(tmp)

        self.assertEqual(
            result.returncode,
            0,
            "hook blocked on a gitignored file. Nothing there can reach a commit, "
            f"so this is a false positive.\nstdout: {result.stdout}\n{result.stderr}",
        )

    def test_untracked_files_are_still_scanned(self):
        """Not-yet-added is not safe: `git add -A` is one keystroke away."""
        import subprocess as sp
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            sp.run(["git", "init", "-q"], cwd=tmp, check=True)
            (Path(tmp) / "fresh.sh").write_text(PLANTED_SECRET)

            result = run_hook(tmp)

        self.assertNotEqual(
            result.returncode,
            0,
            "hook ignored an untracked file carrying a secret",
        )

    def test_this_repos_own_tree_is_clean(self):
        """The gate, run against the thing it guards. Fails the day I paste a token."""
        result = run_hook(REPO_ROOT)
        self.assertEqual(
            result.returncode,
            0,
            f"secrets found in this repo's work tree:\n{result.stdout}\n{result.stderr}",
        )

    def test_scanner_image_is_pinned_by_digest(self):
        """A floating tag means the gate silently changes under me.

        `:latest` also re-pulls, which turns a 30ms hook into a network round trip
        at every commit.
        """
        source = HOOK.read_text()
        self.assertNotRegex(
            source,
            r"gitleaks:(latest|v?\d)",
            "scanner image is pinned by tag, not digest -- use "
            "ghcr.io/gitleaks/gitleaks@sha256:...",
        )
        self.assertRegex(
            source,
            r"gitleaks@sha256:[0-9a-f]{64}",
            "no digest-pinned gitleaks image found in the hook",
        )

    def test_hook_does_not_build_anything(self):
        """Pull-and-run only. A hook that builds is a hook I will disable."""
        source = HOOK.read_text()
        for forbidden in ("docker build", "docker compose", "Dockerfile"):
            self.assertNotIn(
                forbidden,
                source,
                f"hook references `{forbidden}` -- it must pull and run, never build",
            )

    def test_missing_scanner_fails_closed(self):
        """No scanner must block the commit, never wave it through.

        Simulated by running the hook with a PATH that cannot find `docker`.
        """
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("clean\n")
            env = dict(os.environ, PATH="/nonexistent")
            result = subprocess.run(
                [str(HOOK), tmp],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                env=env,
            )

        self.assertNotEqual(
            result.returncode,
            0,
            "hook exited 0 with no scanner available -- it failed open, so every "
            "commit from a machine without Docker is ungated",
        )


if __name__ == "__main__":
    unittest.main()
