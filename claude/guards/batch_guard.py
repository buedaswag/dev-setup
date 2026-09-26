#!/usr/bin/env python3
"""PostToolUse guard: work in small batches, as a check rather than a suggestion.

`How I Work` says commit often. Prose is a suggestion -- agent sessions pile up
uncommitted changes and nothing counts them while the work is happening. This
runs after every Edit, Write and NotebookEdit and counts.

The config is the `batch` key in the project's `.claude/guard-rules.json`, loaded
through the command guard's `load_rules`, so there is still one rules file and
one place it lives:

    "batch": {"check": "python3 -m unittest discover tests/", "commit_at": 3, "push_at": 5}

No `batch` key, no rules file, no project: the hook does nothing. Asking whether
a project wants rules at all is the command guard's job.

The count lives in `.git/batch-guard.json`, tied to HEAD. Any commit -- mine, the
agent's or this hook's -- moves HEAD, and a count against an old HEAD is zero.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from command_guard import BadRules, NoRules, load_rules  # noqa: E402

STATE_FILE = "batch-guard.json"


def git(project, *args):
    """Run git in the project; return (exit code, stdout stripped)."""
    result = subprocess.run(
        ["git", "-C", project, *args], capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip()


def inside(path, project):
    project = os.path.realpath(project)
    path = os.path.realpath(path)
    return os.path.commonpath([path, project]) == project


def count_change(project):
    """Add one to the count since the last commit and return the new count."""
    status, git_dir = git(project, "rev-parse", "--absolute-git-dir")
    if status != 0:
        return None
    _, head = git(project, "rev-parse", "HEAD")
    path = os.path.join(git_dir, STATE_FILE)

    changes = 0
    try:
        with open(path) as handle:
            state = json.load(handle)
        if state.get("head") == head:
            changes = int(state.get("changes", 0))
    except (OSError, ValueError, AttributeError, TypeError):
        pass  # No count yet, or an unreadable one: start over.

    changes += 1
    with open(path, "w") as handle:
        json.dump({"head": head, "changes": changes}, handle)
    return changes


def main():
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return
    try:
        rules = load_rules()
    except (NoRules, BadRules):
        # No file: the command guard asks. A broken one: the command guard blocks.
        return
    if rules is None or rules.batch is None:
        return

    try:
        payload = json.load(sys.stdin)
        tool_input = payload["tool_input"]
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return
    if not path or not inside(path, project):
        return

    count_change(project)


if __name__ == "__main__":
    main()
