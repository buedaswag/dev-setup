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

When a rule matters, make it a static check: a hook or a git hook, not a paragraph. The one
working example is `~/ws/personal/landing-page/scripts/guards/`, Claude Code hooks wired in that
repo only. Its README's "Agent guardrails" says what they do.

## The Code Is The Source Of Truth

The code is what actually runs: the compose file, the git hooks, CI. The README describes it and
points at it; everything else points at the README instead of restating it. When the README
and the code disagree, the README is stale -- fix it, and a guard's `rewrite_to` moves with it.
