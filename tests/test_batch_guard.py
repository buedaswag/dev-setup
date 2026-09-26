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
            # Not the project: the hook must find it through CLAUDE_PROJECT_DIR.
            cwd=tempfile.gettempdir(),
        )

    def state(self):
        path = self.path / ".git" / "batch-guard.json"
        return json.loads(path.read_text()) if path.exists() else None

    def head(self):
        return git(self.path, "rev-parse", "HEAD")

    def message(self):
        return git(self.path, "log", "-1", "--format=%B")

    def commits(self):
        return int(git(self.path, "rev-list", "--count", "HEAD"))


def context(result):
    """What the hook told the agent, or "" if it said nothing."""
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


PASSING = {"batch": {"check": "true", "commit_at": 3, "push_at": 5}}


def batch(**overrides):
    return {"batch": {**PASSING["batch"], **overrides}}


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



class TestTheCheck(unittest.TestCase):
    """The project's check runs after every change; a failure goes to the agent."""

    def test_passing_check_is_silent_to_the_agent(self):
        repo = Repo(self, PASSING)
        result = repo.edit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.strip(), "")

    def test_failing_check_goes_back_to_the_agent(self):
        """Exit 2 is what Claude Code feeds back to the agent from a PostToolUse hook."""
        repo = Repo(self, batch(check="echo 'boom: test_x failed'; exit 1"))
        result = repo.edit()
        self.assertEqual(result.returncode, 2)
        self.assertIn("boom: test_x failed", result.stderr)

    def test_failing_check_output_includes_stderr(self):
        repo = Repo(self, batch(check="echo 'on stderr' >&2; exit 1"))
        self.assertIn("on stderr", repo.edit().stderr)

    def test_check_runs_in_the_project(self):
        """`tests/` in the check means the project's tests, wherever the hook runs from."""
        repo = Repo(self, batch(check="test -f .claude/guard-rules.json"))
        self.assertEqual(repo.edit().returncode, 0)

    def test_a_failing_change_still_counts(self):
        """It is still a change since the last commit."""
        repo = Repo(self, batch(check="false"))
        repo.edit()
        self.assertEqual(repo.state()["changes"], 1)


class TestAskThenCommit(unittest.TestCase):
    """Changes 1 and 2: the agent asks me "commit?". Change 3: the hook commits."""

    def test_first_and_second_change_ask_to_commit(self):
        repo = Repo(self, PASSING)
        for _ in range(2):
            result = repo.edit()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Commit?", context(result))
        self.assertEqual(repo.commits(), 1, "nothing is committed before change 3")

    def test_the_ask_is_meant_for_the_user(self):
        result = Repo(self, PASSING).edit()
        self.assertIn("ask the user", context(result).lower())

    def test_third_change_commits(self):
        repo = Repo(self, PASSING)
        repo.edit()
        repo.edit()
        result = repo.edit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(repo.commits(), 2)
        self.assertEqual(git(repo.path, "status", "--porcelain"), "")
        self.assertIn("Committed", context(result))
        self.assertNotIn("Commit?", context(result))

    def test_commit_takes_the_whole_tree_and_names_every_file(self):
        """My work in progress goes in too -- and nothing goes in unmentioned."""
        repo = Repo(self, PASSING)
        (repo.path / "mine.md").write_text("by hand\n")
        (repo.path / "README.md").write_text("changed by hand\n")
        repo.edit("a.txt")
        repo.edit("b.txt")
        repo.edit("a.txt")
        self.assertEqual(git(repo.path, "status", "--porcelain"), "")
        self.assertEqual(repo.message(), "wip: README.md, a.txt, b.txt, mine.md")

    def test_commit_at_is_read_from_the_config(self):
        repo = Repo(self, batch(commit_at=1))
        repo.edit()
        self.assertEqual(repo.commits(), 2)

    def test_the_count_starts_over_after_the_hook_commits(self):
        repo = Repo(self, PASSING)
        for _ in range(3):
            repo.edit()
        result = repo.edit()
        self.assertEqual(repo.state(), {"head": repo.head(), "changes": 1})
        self.assertIn("Commit?", context(result))

    def test_failing_check_neither_asks_nor_commits(self):
        repo = Repo(self, batch(check="false"))
        for _ in range(3):
            result = repo.edit()
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(repo.commits(), 1)

    def test_commit_waits_for_the_check_to_pass(self):
        """Change 3 failed; change 4 passes and commits -- the batch was due."""
        repo = Repo(self, batch(check="test ! -f broken"))
        repo.edit()
        repo.edit()
        self.assertEqual(repo.edit("broken").returncode, 2)
        (repo.path / "broken").unlink()
        result = repo.edit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(repo.commits(), 2)

    def test_nothing_to_commit_is_not_an_error(self):
        """An edit that left the file as it was leaves a clean tree."""
        repo = Repo(self, batch(commit_at=1))
        result = repo.hook(str(repo.path / "README.md"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(repo.commits(), 1)

    def test_a_rejected_commit_goes_back_to_the_agent(self):
        """The pre-commit hook (the secret gate, here) still gates the auto-commit."""
        repo = Repo(self, batch(commit_at=1))
        hooks = repo.path / ".git" / "hooks"
        (hooks / "pre-commit").write_text("#!/bin/sh\necho 'secret found' >&2\nexit 1\n")
        (hooks / "pre-commit").chmod(0o755)
        result = repo.edit()
        self.assertEqual(result.returncode, 2)
        self.assertIn("secret found", result.stderr)
        self.assertEqual(repo.commits(), 1)


class TestBadBatchConfig(unittest.TestCase):
    """A malformed `batch` key is a broken rules file, and the command guard blocks on those."""

    @staticmethod
    def load():
        sys.path.insert(0, str(GUARD.parent))
        from command_guard import BadRules, Rules

        return Rules, BadRules

    def test_batch_without_a_check_is_bad(self):
        Rules, BadRules = self.load()
        with self.assertRaises(BadRules):
            Rules({"batch": {"commit_at": 3, "push_at": 5}})

    def test_batch_counts_must_be_positive_whole_numbers(self):
        Rules, BadRules = self.load()
        for bad in (0, -1, "3", 2.5, None):
            with self.assertRaises(BadRules, msg=repr(bad)):
                Rules({"batch": {"check": "true", "commit_at": bad, "push_at": 5}})

    def test_good_batch_loads(self):
        Rules, _ = self.load()
        self.assertEqual(Rules(PASSING).batch, PASSING["batch"])


if __name__ == "__main__":
    unittest.main()
