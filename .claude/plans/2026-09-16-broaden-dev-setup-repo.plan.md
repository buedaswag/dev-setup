# Broaden `python-dev-setup` into my dev-environment repo

**Status: done** (2026-09-26)

## Problem

Three things I actually rely on live in the wrong place. `claude_guard.py` — the hook that
rewrites `npm run build` into `docker compose up --build -d` — is buried in `landing-page`, so
the next Docker project starts from nothing. `How I Work` is a `.cursor/rules/*.mdc` in one
repo, so every project either copies it or drifts from it. And `~/.claude/settings.json` is
already mirrored here by `claude/sync-settings.sh`, which proves the shape works but only
covers one file.

The repo's name says Python; what it holds is "how my machine and my agents are set up".

## Approach

Repo keeps three layers, in dependency order:

| Layer | What | Where |
| --- | --- | --- |
| Machine | shell, venvs, Mac apps | `py-venvs.sh`, README |
| Conventions | How I Work — plans, TDD, small batches, one-piece flow | `claude/CLAUDE.md` |
| Enforcement | the guard hook that makes a convention non-optional | `claude/guards/` |

**Conventions.** Canonical copy is `~/.claude/CLAUDE.md`, which Claude Code loads in every
project for free — that is the "sync between projects" answer, no tooling needed. The repo is
the mirror, not the source. Rename `sync-settings.sh` → `claude/sync.sh` and give it a list
(`settings.json`, `CLAUDE.md`, `skills/`, `commands/`) instead of one hardcoded path; keep the
existing safety properties — JSON validated before copy, path-limited `git add`, one commit,
`Stop` hook, async. It already retires the fragile `SessionStart` `cp` line that copies skills
*out of* project repos into `~/.claude/`; that direction goes away.

Each project's `CLAUDE.md` then holds only what is true of that project — ports, compose
command, where the tests are. `landing-page`'s `how-i-work.mdc` shrinks to that half.

**Enforcement.** `claude_guard.py` splits in two. The engine — mask heredocs/quotes/comments,
split on top-level separators, rewrite one segment or deny the whole command — is project-
agnostic and moves to `claude/guards/command_guard.py` with its tests. The Docker/npm specifics
(`DOCKER_UP`, the install and node-command regexes, the two reasons) become a `guard-rules.json`
the engine reads from `$CLAUDE_PROJECT_DIR`. A project opts in with one hook line pointing at
the shared script, and its rules file. No rules file, or no shared script → the hook exits
clean and the agent is never blocked by a broken guard.

**README.** Rewrite the opening to state the broadened scope in two lines, then three sections
matching the layers above. Each section says what it is and how to wire it into a new machine
or a new project. Succinct — the detail lives in the files.

## Sequence

1. `claude/sync.sh` generalised, `CLAUDE.md` added to the list, `SessionStart` `cp` removed.
2. `How I Work` portable half → `~/.claude/CLAUDE.md`; first sync commit proves the loop.
3. Guard engine + tests moved, rules extracted to JSON, `landing-page` switched over and its
   tests re-run against the shared engine.
4. README.

## Open

The name. `python-dev-setup` no longer describes it — `dev-setup` is accurate and the rename
is one `gh repo rename` plus the `source` line in `~/.zshrc`. Not doing it in this pass unless
I say so; every path above assumes the current name.

Cursor won't read `~/.claude/CLAUDE.md`. Accepted for now: Claude is what I actually drive, and
a per-project `.mdc` pointing at the repo is a fix I can add the day I need Cursor to agree.
