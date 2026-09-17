# Dev Setup

How my machine and my agents are set up. Three layers: the **machine**, the **conventions** I
work by, and the **enforcement** that makes a convention non-optional.

## Machine

Mac apps:

- [Maccy](https://maccy.app/) — clipboard manager
- [Rectangle](https://rectangleapp.com/) — window management

Python venvs — add to `~/.zshrc`:

```bash
source ~/ws/dev-setup/py-venvs.sh
```

## Conventions

`claude/CLAUDE.md` is how I work: one-page plans in `.claude/plans/`, tests before code, small
batches.

Canonical copy is `~/.claude/CLAUDE.md`, which Claude Code loads in every project — nothing to
sync between projects. This repo is the mirror. `claude/sync.sh` runs as a `Stop` hook, copies
the paths in `PATHS` out of `~/.claude` when they change, and commits just those paths. JSON is
validated before copying and the `git add` is path-limited, so it can't clobber a good file or
sweep up unrelated work.

A project's own `CLAUDE.md` holds only what's specific to it — ports, build command, tests.

## Enforcement

A rule in prose is a suggestion: an agent reads "everything runs in Docker" and still proposes
`npm run build`. `claude/guards/command_guard.py` is a `PreToolUse` hook that matches every
Bash command statically, before the prompt appears, and rewrites it to the documented command
or denies it with a reason. No prompt, no LLM in the loop.

The engine is shared; the rules aren't. Wire up a project with a `guard-rules.json` at its root:

```json
{
  "rewrite_to": "docker compose up --build -d",
  "ready_wait": "until curl -sf localhost:4444 >/dev/null; do sleep 1; done",
  "skip_if": ["docker"],
  "deny":    { "pattern": "(?:npm|yarn|pnpm)\\s+(?:install|i|ci|add)\\b", "reason": "..." },
  "rewrite": { "pattern": "(?:npm|npx|yarn|pnpm|astro)\\b",              "reason": "..." }
}
```

and a `PreToolUse` hook on `Bash` in its `.claude/settings.json`:

```
python3 "$HOME/ws/dev-setup/claude/guards/command_guard.py" 2>/dev/null || true
```

Patterns match in command position only, and heredocs, quoted strings and comments are masked
first — writing *about* `npm install` isn't running it. Compound commands get only the
offending segment rewritten, but a deny match anywhere denies the whole command. `ready_wait`
is appended when a step follows, so it can't race a detached server. No rules file, or a bad
one, and the guard exits clean — a broken guard must never block the agent.

```bash
python3 -m unittest discover tests/
```
