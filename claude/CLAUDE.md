# How I Work

This applies to every project. Anything specific to one repo — ports, build commands, where
the tests live — belongs in that repo's own `CLAUDE.md`, not here.

## Plans

Plans live in `.claude/plans/`, one file per piece of work, named `YYYY-MM-DD-slug.plan.md`.

A plan is one page. If it doesn't fit on one page, the problem isn't understood well enough to
be described succinctly yet — go back and understand it, don't write more.

Structure: **Problem** (what's actually wrong, concretely), **Approach** (what we do about it
and why that and not the alternative), **Sequence** (the order, so each step proves the next),
**Open** (decisions I haven't made, named as mine to make).

## TDD

Tests and security checks first. Write the test, run it, watch it fail for the right reason,
then write the code that makes it pass. A test that has never failed has proved nothing.

## Work in Small Batches

One piece flow. Commit often — small batches mean the hooks run often and a bad change is
one revert, not an archaeology session.

## Rules Worth Having Are Worth Enforcing

A rule written in prose is a suggestion: an agent reads it and still proposes the thing it
says not to do, and I'm the one who has to say No at the permission prompt.

When a rule matters, make it a static check. `claude/guards/command_guard.py` in
`~/ws/dev-setup` is a `PreToolUse` hook that matches every Bash command before the prompt
appears and either rewrites it to the documented equivalent or denies it with a reason the
agent can act on. No prompt, no LLM in the loop.

Per-project rules go in `.claude/guard-rules.json` in the project. The engine is shared; the
rules are not. See that repo's README for wiring a project up.

## Documented Commands Are The Source Of Truth

When a guard rewrites a command, it rewrites to whatever the project's `README` documents. If
the README and the guard disagree, the README is right and the guard is the one that moves.
