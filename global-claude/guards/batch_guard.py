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


def run_check(project, check):
    """Run the project's check from the project root; return (passed, output)."""
    result = subprocess.run(
        check, shell=True, cwd=project, capture_output=True, text=True
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def commit_everything(project):
    """Stage the whole tree and commit it as `wip: <every file>`.

    Returns (committed, detail): the message on success, git's output on a
    rejected commit, and (False, "") when there was nothing to commit.
    """
    git(project, "add", "-A")
    # -z: otherwise git quotes and escapes unusual paths, and the message would
    # name files that do not exist under that spelling.
    _, names = git(project, "diff", "--cached", "--name-only", "-z")
    files = sorted(name for name in names.split("\0") if name)
    if not files:
        return False, ""
    message = "wip: " + ", ".join(files)
    result = subprocess.run(
        ["git", "-C", project, "commit", "-q", "-m", message],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, (result.stdout + result.stderr).strip() or "git commit failed"
    return True, message


def unpushed(project):
    """Commits on HEAD that its upstream lacks; 0 when there is no upstream."""
    status, count = git(project, "rev-list", "--count", "@{upstream}..HEAD")
    return int(count) if status == 0 and count.isdigit() else 0


def push_question(project, push_at):
    ahead = unpushed(project)
    if ahead < push_at:
        return ""
    return (
        f' There are {ahead} unpushed commits. Also ask the user: "Push?" -- and push '
        f"only on yes. Never push without asking."
    )


def tell_agent(message):
    """Context for the agent's next step; the change itself has already happened."""
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            }
        },
        sys.stdout,
    )


def block(message):
    """Exit 2: for PostToolUse, Claude Code shows stderr to the agent."""
    print(message, file=sys.stderr)
    sys.exit(2)


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

    changes = count_change(project)

    passed, output = run_check(project, rules.batch["check"])
    if not passed:
        block(
            f"The check failed after this change (`{rules.batch['check']}`). Fix it "
            f"before anything else -- nothing gets committed while it fails.\n\n{output}"
        )

    commit_at = rules.batch["commit_at"]
    if changes is None:
        return
    if changes < commit_at:
        message = (
            f"Change {changes} of {commit_at} since the last commit; the check passes. "
            f'Ask the user: "Commit?" -- one word, nothing else. On yes, commit what is '
            f"there. On no, carry on; change {commit_at} is committed automatically."
        )
    else:
        committed, detail = commit_everything(project)
        if not committed and detail:
            block(
                f"Change {changes} was due to be committed, and the commit was rejected. "
                f"Fix what it reports; the next change tries again.\n\n{detail}"
            )
        message = f"Committed automatically at change {changes}: {detail}" if committed else ""

    message = (message + push_question(project, rules.batch["push_at"])).strip()
    if message:
        tell_agent(message)


if __name__ == "__main__":
    main()
