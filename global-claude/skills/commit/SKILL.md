---
name: commit
description: Commit what's staged with a message in my style; `/commit all` stages the whole worktree first. Use when I say /commit, "commit this", or answer yes to "Commit?".
argument-hint: "[all]"
model: haiku
allowed-tools: Bash(git add:*), Bash(git diff:*), Bash(git commit:*)
---

1. If the arguments are `all`, or I asked to commit everything, `git add -A` first. Otherwise don't stage anything.
2. `git diff --cached`. If it's empty, say nothing is staged, suggest `/commit all`, and stop.
3. Commit with `git commit -F -`. The message is one short lowercase sentence saying what changed. Add 1-3 bullets only if one sentence can't carry it. Nothing else, apart from
   any attribution trailer this session asks for.
4. If a hook fails, show its output and stop. Never `--no-verify`.
