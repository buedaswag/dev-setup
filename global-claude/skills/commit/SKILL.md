---
name: commit
description: Stage everything in the worktree and commit it with a message in my style. Use when I say /commit, "commit this", or answer yes to "Commit?".
model: haiku
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*)
---

Commit what's in the worktree. Commit only. Don't push, don't review, don't run tests; the git hooks handle checks.

1. Run `git status --short` and `git diff HEAD`. If nothing changed, say so and stop.
2. Run `git add -A`.
3. Write the message:
   - One short sentence saying what changed and why. Lowercase, no trailing period, under 72 chars.
     Use a `scope: ` prefix only if recent `git log --oneline -10` subjects use one.
   - Add 1-3 bullet points only if the sentence can't carry the change. Most commits have none.
   - Nothing else: no body paragraphs, no file lists, no "this commit".
4. Run `git commit -F -` with the message on stdin, then the attribution trailer the session tells you to add.
5. If a hook fails, show its output and stop. Don't retry with `--no-verify`.
6. Print the commit's subject line.
