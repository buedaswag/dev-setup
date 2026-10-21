# Small-batch harness: check every change, commit on the third, ask to push

## Problem

"Commit often" is prose, so it's a suggestion. Agent sessions pile up uncommitted changes and
unpushed commits, and nothing counts either one while the work is happening.

## Approach

One `PostToolUse` hook, `claude/guards/batch_guard.py`, runs after every `Edit|Write|NotebookEdit`:

1. **Check.** Run the project's `check`. If it fails, the output goes to the agent (exit 2), and
   nothing gets asked or committed.
2. **Count.** Count the changes made since the last commit.
   - Change 1 and change 2: the agent asks me "commit?"
   - Change 3: the hook commits by itself.
3. **Push.** Once there are `push_at` unpushed commits, the agent asks me "push?" It never
   pushes on its own.

The config goes in `.claude/guard-rules.json`:
`"batch": {"check": "python3 -m unittest discover tests/", "commit_at": 3, "push_at": 5}`.
No `batch` key → the hook does nothing.

## Sequence

Tests first, one commit per step.

1. Count changes since the last commit.
2. Run the check; a failure goes back to the agent.
3. Ask on changes 1 and 2, commit on change 3.
4. Ask to push at `push_at`.
5. Wire it up here and use it for a week.

## Changes

| File | Change |
| --- | --- |
| `tests/test_batch_guard.py` (new) | Temp git repo with a bare upstream; hook input as JSON on stdin |
| `claude/guards/batch_guard.py` (new) | The hook. Reuses `load_rules` from `command_guard.py` |
| `.claude/guard-rules.json` | Add the `batch` key |
| `~/.claude/settings.json` | One `PostToolUse` entry, matcher `Edit\|Write\|NotebookEdit` |

## Decided

- The auto-commit stages the whole tree, my work in progress included, since the batches are
  small. Its message is `wip: <every file in it>`, so nothing goes in unmentioned.
- The change count lives in `.git/batch-guard.json`, tied to `HEAD`: any commit (mine, the
  agent's or the hook's) starts it over.
