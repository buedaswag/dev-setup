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

Shell config is mirrored in `shell/` — `zshrc`, `zprofile`. `~/.zshrc` is the canonical copy and
the one I edit; these are a snapshot, committed by hand:

```bash
cp ~/.zshrc shell/zshrc && cp ~/.zprofile shell/zprofile
```

Unlike `~/.claude`, nothing syncs these automatically — see the backlog for why that's deliberate
rather than unfinished.

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

The hook is registered once, globally, in `~/.claude/settings.json`, so it runs in every project:

```
python3 "$HOME/ws/dev-setup/claude/guards/command_guard.py" || exit 2
```

`|| exit 2` is the fail-closed part: 2 is the only exit code Claude Code treats as blocking, and
an unexpected crash exits 1. If this repo isn't cloned, Python exits 2 with the missing path.

The engine is shared; the opinions aren't. A project supplies a `guard-rules.json` at its root:

```json
{
  "rewrite_to": "docker compose up --build -d",
  "ready_wait": "until curl -sf localhost:4444 >/dev/null; do sleep 1; done",
  "skip_if": ["docker"],
  "deny":    { "pattern": "(?:npm|yarn|pnpm)\\s+(?:install|i|ci|add)\\b", "reason": "..." },
  "rewrite": { "pattern": "(?:npm|npx|yarn|pnpm|astro)\\b",              "reason": "..." }
}
```

Patterns match in command position only, and heredocs, quoted strings and comments are masked
first — writing *about* `npm install` isn't running it. Compound commands get only the offending
segment rewritten, but a deny match anywhere denies the whole command. `ready_wait` is appended
when a step follows, so it can't race a detached server.

Because the hook is global, a project with no rules file has never been asked rather than opted
out — so the guard asks, once:

| Project state | Guard does |
| --- | --- |
| No `guard-rules.json` | Blocks once and tells the agent to ask whether to create rules. Answer no and it writes `{"_comment": "..."}`, which never asks again. |
| `{}` or a comment-only stub | Nothing. Every command runs. |
| Real rules | Enforces them. |
| Unusable rules | Blocks until fixed — opted in and broken is the one case that must never fail open. |

### The secret gate

Shell config is exactly where a token ends up when I'm in a hurry, and `claude/sync.sh` commits
on its own from a `Stop` hook — no prompt, no human. So `githooks/pre-commit` refuses any commit
whose files carry a credential. Install it once per repo:

```bash
git config core.hooksPath githooks
```

gitleaks in Docker, pinned by digest, ~260ms. Docker so the gate doesn't depend on a venv being
on `PATH` — `py-venvs.sh` activates one, and a gate that silently stops gating is worse than
none. Pinned because a floating tag changes the gate under me and re-pulls on every commit. Pull
and run only; it never builds.

It scans the files a commit could carry — tracked, plus untracked that `.gitignore` doesn't
exclude — not the whole directory. `--no-git` walks the filesystem and ignores `.gitignore`, so
scanning the directory means flagging `__pycache__`, `node_modules` and `.venv`, where a finding
is always a false positive. A gate that cries wolf is a gate I switch off.

No Docker means **blocked**, not passed: a commit that can't be scanned isn't waved through. When
a finding is wrong, `git commit --no-verify`, having looked at it.

```bash
python3 -m unittest discover tests/
```

## Refactor Along the Way

Known and deliberately not done yet. Each one gets picked up the next time I'm in that file.

- **Auto-commit `shell/zshrc` on change.** Manual `cp` for now. `claude/sync.sh` only walks paths
  under `~/.claude`, so this needs its `PATHS` generalised to `src:dest` pairs. Deliberately
  second: an auto-committer pointed at `.zshrc` is what made the secret gate a prerequisite, and
  the gate should have some mileage on it before anything commits that file unattended.
- **Let one repo reuse another's guard rules** — an `extends` key in `guard-rules.json` resolved
  before `Rules.__init__`. Today every repo keeps its own copy, and copy-paste is fine until
  there are enough of them to drift.
- **Retire the `SessionStart` `cp` in `~/.claude/settings.json`.** It copies skills out of
  `interview-prep` and `CV` into `~/.claude/` on every session start — the direction this repo's
  mirroring deliberately reverses, and it's ungated.
- **`ASK_USER` is tested for wording, not for being answerable.** The tests pin length, jargon and
  a closing question; nothing catches a question that's short, clean and still confusing.
