"""zsh/aliases.zsh: `gc "message" [flags]` commits with that message.

omz's git plugin defines `gc='git commit --verbose'`, and aliases.zsh is sourced
after it, so these tests define that alias first, the way a real shell would have it.

Each test runs in a throwaway $HOME (aliases.zsh writes `git config --global`) and a
fresh repo, so they never touch the real ones.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALIASES_FILE = REPO_ROOT / "zsh" / "aliases.zsh"

OMZ_GC = "alias gc='git commit --verbose'"


class GcTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.repo = self.home / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        (self.repo / "file").write_text("one\n")
        self.git("add", "file")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env={"HOME": str(self.home), "PATH": "/usr/bin:/bin:/opt/homebrew/bin"},
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def gc(self, args):
        # On stdin, not -c: -c parses the whole script before the alias exists, stdin
        # reads line by line, as at a prompt.
        script = f'{OMZ_GC}\nsource "{ALIASES_FILE}"\ngc {args}\n'
        return subprocess.run(
            ["zsh", "-f"],
            input=script,
            cwd=self.repo,
            env={"HOME": str(self.home), "PATH": "/usr/bin:/bin:/opt/homebrew/bin"},
            capture_output=True,
            text=True,
        )

    def subjects(self):
        return self.git("log", "--format=%s").splitlines()

    def test_message_becomes_the_commit_message(self):
        result = self.gc('"this is my comment"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects(), ["this is my comment"])

    def test_flags_after_the_message_go_to_git_commit(self):
        self.gc('"first"')
        (self.repo / "file").write_text("two\n")
        # -a stages tracked changes, so nothing was `git add`ed here.
        result = self.gc('"second" -a')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects(), ["second", "first"])

    def test_amend_replaces_the_previous_commit(self):
        self.gc('"first"')
        result = self.gc('"first, reworded" --amend')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.subjects(), ["first, reworded"])


if __name__ == "__main__":
    unittest.main()
