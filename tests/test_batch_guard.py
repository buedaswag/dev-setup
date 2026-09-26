"""Tests for the PostToolUse batch guard.

"Commit often" is prose, so on its own it is a suggestion. The batch guard makes it
a check: after every edit it runs the project's check, counts the changes since the
last commit, and commits on the `commit_at`th.

These drive the hook the way Claude Code does -- hook input as JSON on stdin, with
CLAUDE_PROJECT_DIR pointing at a throwaway git repo that has a bare upstream, so
committing and "unpushed" are both real.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "claude" / "guards" / "batch_guard.py"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


class Repo:
    """A git repo with a bare upstream, one commit in, pushed, and clean."""

    def __init__(self, test, rules):
        tmp = Path(tempfile.mkdtemp())
        test.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        self.upstream = tmp / "upstream.git"
        self.path = tmp / "project"
        subprocess.run(["git", "init", "-q", "--bare", str(self.upstream)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.path)], check=True)
        git(self.path, "config", "user.name", "Test")
        git(self.path, "config", "user.email", "test@example.com")
        git(self.path, "config", "commit.gpgsign", "false")
        git(self.path, "remote", "add", "origin", str(self.upstream))
        if rules is not None:
            (self.path / ".claude").mkdir()
            (self.path / ".claude" / "guard-rules.json").write_text(json.dumps(rules))
        (self.path / "README.md").write_text("start\n")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "initial")
        git(self.path, "push", "-q", "-u", "origin", "main")

    def edit(self, name="file.txt", text=None, tool_name="Edit"):
        """Change a file, then tell the hook about it -- the order Claude Code uses."""
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        previous = target.read_text() if target.exists() else ""
        target.write_text(previous + (text or f"line {len(previous)}\n"))
        return self.hook(str(target), tool_name)

    def hook(self, file_path, tool_name="Edit"):
        key = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
        payload = json.dumps(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": tool_name,
                "tool_input": {key: file_path},
                "tool_response": {},
            }
        )
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        env["CLAUDE_PROJECT_DIR"] = str(self.path)
        return subprocess.run(
            [sys.executable, str(GUARD)],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            cwd=str(self.path),
        )

    def state(self):
        path = self.path / ".git" / "batch-guard.json"
        return json.loads(path.read_text()) if path.exists() else None

    def head(self):
        return git(self.path, "rev-parse", "HEAD")


PASSING = {"batch": {"check": "true", "commit_at": 3, "push_at": 5}}


class TestCountingChanges(unittest.TestCase):
    """Every edit since the last commit counts once, and any commit starts it over."""

    def test_first_edit_counts_one(self):
        repo = Repo(self, PASSING)
        result = repo.edit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(repo.state(), {"head": repo.head(), "changes": 1})

    def test_second_edit_counts_two(self):
        repo = Repo(self, PASSING)
        repo.edit()
        repo.edit()
        self.assertEqual(repo.state()["changes"], 2)

    def test_write_and_notebook_edit_count_too(self):
        repo = Repo(self, PASSING)
        repo.edit(tool_name="Write")
        repo.edit(name="n.ipynb", tool_name="NotebookEdit")
        self.assertEqual(repo.state()["changes"], 2)

    def test_any_commit_starts_the_count_over(self):
        """Mine, the agent's or the hook's -- the count is tied to HEAD."""
        repo = Repo(self, PASSING)
        repo.edit()
        repo.edit()
        git(repo.path, "add", "-A")
        git(repo.path, "commit", "-q", "-m", "by hand")
        repo.edit()
        self.assertEqual(repo.state(), {"head": repo.head(), "changes": 1})

    def test_edits_outside_the_project_do_not_count(self):
        """Editing ~/.claude/settings.json is not a change to this repo."""
        repo = Repo(self, PASSING)
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(outside, ignore_errors=True))
        result = repo.hook(str(outside / "elsewhere.txt"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(repo.state())

    def test_no_batch_key_does_nothing(self):
        repo = Repo(self, {"_comment": "no rules"})
        result = repo.edit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")
        self.assertIsNone(repo.state())

    def test_no_rules_file_does_nothing(self):
        """Asking about rules is the command guard's job, not this one's."""
        repo = Repo(self, None)
        result = repo.edit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip() + result.stderr.strip(), "")
        self.assertIsNone(repo.state())

    def test_garbage_stdin_exits_clean(self):
        result = subprocess.run(
            [sys.executable, str(GUARD)], input="not json", capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
