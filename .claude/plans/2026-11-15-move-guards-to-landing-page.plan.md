# Move the agent guards to landing-page

## Problem

The command and batch guards are global hooks in `~/.claude/settings.json`. Every repo without
`.claude/guard-rules.json` gets blocked on its first Bash command and asked whether it wants
rules. Only `landing-page` has real rules; three repos carry a `{"_comment"}` stub just to stop
the question, and `dev-setup` carries only a `batch` key.

## Approach

The guards belong to the one repo that uses them. Move the engine, its tests, its fixture and
its docs to `landing-page`, wire the hooks in that repo's `.claude/settings.json` via
`$CLAUDE_PROJECT_DIR`, and drop the global hooks. A repo that never wired them never sees them.

Not "keep it global and make no-rules silent": that still runs a global hook for every Bash
command everywhere, for one repo's benefit. Engine code moves as-is; no behaviour change.

`dev-setup` keeps one README line saying what the guards are for and where they live.

## Sequence

1. landing-page: copy the guard tests and fixture in, pointed at `scripts/guards/`. Run them —
   they fail, no engine there.
2. landing-page: copy the engine to `scripts/guards/`. Tests pass.
3. landing-page: `.claude/settings.json` with both hooks; un-ignore it. README "Agent
   guardrails" absorbs dev-setup's Enforcement docs; CLAUDE.md and rules `_comment` updated.
   Commit.
4. `~/.claude/settings.json`: remove the `PreToolUse`/`PostToolUse` guard hooks. Trim the
   global CLAUDE.md enforcement section to a pointer.
5. dev-setup: delete engine, tests, fixture, `.claude/guard-rules.json`; README Enforcement
   becomes the one-liner; drop the guard backlog items. Tests pass. Commit.
6. Delete the stubs in `decks`, `dajana`, `devopsdays-bcn-2026-otel`.

## Open

- Whether the guards outlive landing-page at all — they may be deprecated. Not decided here.
