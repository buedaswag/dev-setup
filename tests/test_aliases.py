"""zsh/aliases.zsh and functions.zsh: the git shortcuts, including those replacing omz's.

`gc "message" [flags]` commits with that message; `gp` pushes the current branch to
origin; `gpull` pulls it from origin; `gacp` adds, commits and pushes. omz's git plugin defines gc and gp
(`gc='git commit --verbose'`, `gp='git push'`) and aliases.zsh is sourced after it,
so these tests define those aliases first, the way a real shell would have them.

Each test runs in a throwaway $HOME (aliases.zsh writes `git config --global`) and a
fresh repo, so they never touch the real ones.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALIASES_FILE = REPO_ROOT / "zsh" / "aliases.zsh"
FUNCTIONS_FILE = REPO_ROOT / "zsh" / "functions.zsh"

OMZ_ALIASES = "alias gc='git commit --verbose'\nalias gp='git push'"


class GitShortcutsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin:/opt/homebrew/bin"}
        self.repo = self.home / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        (self.repo / "file").write_text("one\n")
        self.git("add", "file")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo,
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def shell(self, line):
        # On stdin, not -c: -c parses the whole script before the alias exists, stdin
        # reads line by line, as at a prompt.
        script = f'{OMZ_ALIASES}\nsource "{ALIASES_FILE}"\nsource "{FUNCTIONS_FILE}"\n{line}\n'
        return subprocess.run(
            ["zsh", "-f"],
            input=script,
            cwd=self.repo,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def subjects(self):
        return self.git("log", "--format=%s").splitlines()

    def test_gc_message_becomes_the_commit_message(self):
        result = self.shell('gc "this is my comment"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects(), ["this is my comment"])

    def test_gc_flags_after_the_message_go_to_git_commit(self):
        self.shell('gc "first"')
        (self.repo / "file").write_text("two\n")
        # -a stages tracked changes, so nothing was `git add`ed here.
        result = self.shell('gc "second" -a')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects(), ["second", "first"])

    def test_gc_flags_before_the_message_go_to_git_commit(self):
        self.shell('gc "first"')
        result = self.shell('gc --amend "first, reworded"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects(), ["first, reworded"])

    def test_gd_shows_the_unstaged_diff(self):
        self.git("commit", "-q", "-m", "first")
        (self.repo / "file").write_text("two\n")
        result = self.shell("gd")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-one\n+two\n", result.stdout)

    def add_origin(self):
        origin = self.home / "origin.git"
        self.git("init", "-q", "--bare", str(origin))
        self.git("remote", "add", "origin", str(origin))
        self.git("commit", "-q", "-m", "first")
        # A new branch with no upstream: plain `git push` refuses this.
        self.git("switch", "-q", "-c", "feature")
        return origin

    def test_gp_pushes_the_current_branch_to_origin(self):
        origin = self.add_origin()
        result = self.shell("gp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.git("rev-parse", "feature", cwd=origin),
            self.git("rev-parse", "HEAD"),
        )

    def test_gpull_pulls_the_current_branch_from_origin(self):
        origin = self.add_origin()
        self.git("push", "-q", "origin", "feature")
        # Someone else pushes to feature; this repo still has no upstream set.
        other = self.home / "other"
        self.git("clone", "-q", "-b", "feature", str(origin), str(other), cwd=self.home)
        # CI has no global identity to fall back on; macOS guesses one, Linux won't.
        self.git("config", "user.email", "other@example.com", cwd=other)
        self.git("config", "user.name", "Other", cwd=other)
        (other / "file").write_text("theirs\n")
        self.git("commit", "-q", "-am", "theirs", cwd=other)
        self.git("push", "-q", cwd=other)
        result = self.shell("gpull")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects()[0], "theirs")

    def test_gacp_commits_everything_and_pushes_the_current_branch(self):
        origin = self.add_origin()
        (self.repo / "new").write_text("new\n")
        result = self.shell("gacp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects()[0], "Modified files: new")
        self.assertEqual(
            self.git("rev-parse", "feature", cwd=origin),
            self.git("rev-parse", "HEAD"),
        )


class HistoryGrepTest(unittest.TestCase):
    """`hg word [word...]` lists the commands I ran: the line's command (alias expanded) is one
    of the words, every word appears, any order, any case. Plain, deduplicated, newest last."""

    HISTORY = [
        "terraform init",
        "terraform login tralalalala",
        "mkdir terraform",
        "cp ../terraform-google-vm/examples/simple/* terraform/",
        "tf plan -out plan.tfplan",
        "git status",
        "locust -f locustfile.py -t 10min",
        "Terraform apply -auto-approve",
        "terraform init",
        "terraform version\\",
        "",
    ]

    def script(self, tmp, line):
        histfile = Path(tmp) / "history"
        histfile.write_text("\n".join(self.HISTORY) + "\n")
        return (
            f'HISTSIZE=100\nfc -R "{histfile}"\n'
            f'source "{ALIASES_FILE}"\n{line}\n'
        )

    def hg(self, args):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HOME": tmp, "PATH": "/usr/bin:/bin"}
            return subprocess.run(
                ["zsh", "-f"],
                input=self.script(tmp, f"hg {args}"),
                env=env,
                capture_output=True,
                text=True,
            )

    def commands(self, result):
        return result.stdout.splitlines()

    def test_lists_only_lines_whose_command_is_the_word(self):
        result = self.hg("terraform")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("mkdir terraform", self.commands(result))
        self.assertIn("terraform login tralalalala", self.commands(result))

    def test_aliases_count_as_their_command(self):
        self.assertIn("tf plan -out plan.tfplan", self.commands(self.hg("terraform")))
        self.assertIn("tf plan -out plan.tfplan", self.commands(self.hg("tf")))
        self.assertNotIn("locust -f locustfile.py -t 10min", self.commands(self.hg("tf")))

    def test_several_words_must_all_appear_in_any_order(self):
        result = self.hg("login terraform")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(result), ["terraform login tralalalala"])

    def test_case_is_ignored(self):
        result = self.hg("terraform apply")
        self.assertEqual(self.commands(result), ["Terraform apply -auto-approve"])

    def test_no_command_match_falls_back_to_anywhere(self):
        result = self.hg("terraform-google-vm")
        self.assertEqual(
            self.commands(result),
            ["cp ../terraform-google-vm/examples/simple/* terraform/"],
        )

    def test_plain_deduplicated_newest_last(self):
        self.assertEqual(
            self.commands(self.hg("terraform")),
            [
                "terraform login tralalalala",
                "tf plan -out plan.tfplan",
                "Terraform apply -auto-approve",
                "terraform init",
                "terraform version",
            ],
        )

    def test_nothing_found_fails(self):
        result = self.hg("nonexistent")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_at_a_terminal_the_pick_goes_on_the_next_prompt(self):
        import os
        import pty

        with tempfile.TemporaryDirectory() as tmp:
            # read -z pops what print -z pushed: that is what the next prompt would show.
            script = Path(tmp) / "script.zsh"
            script.write_text(self.script(tmp, 'hg terraform\nread -z picked\nprint "PICKED:$picked"'))
            env = {"HOME": tmp, "PATH": "/usr/bin:/bin"}
            pid, fd = pty.fork()
            if pid == 0:
                os.execve("/bin/zsh", ["zsh", "-f", str(script)], env)
            out = b""
            os.write(fd, b"2\n")
            while True:
                try:
                    chunk = os.read(fd, 1024)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
            os.waitpid(pid, 0)
        text = out.decode()
        self.assertIn("2) tf plan -out plan.tfplan", text)
        self.assertIn("PICKED:tf plan -out plan.tfplan", text)


if __name__ == "__main__":
    unittest.main()
