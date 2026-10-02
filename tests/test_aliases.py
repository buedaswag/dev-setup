"""zsh/aliases.zsh and functions.zsh: the git shortcuts, including those replacing omz's.

`gc "message" [flags]` commits with that message; `gp` pushes the current branch to
origin; `gacp` adds, commits and pushes. omz's git plugin defines gc and gp
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


if __name__ == "__main__":
    unittest.main()
