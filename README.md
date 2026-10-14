# Dev Setup

How my machine and my Claude Code agents are set up. Lives at `~/ws/dev-setup`.

## Machine

- [Maccy](https://maccy.app/) — clipboard manager
- [Rectangle](https://rectangleapp.com/) — window management
- Shell config is in `zsh/`. Install: `echo 'source ~/ws/dev-setup/zsh/.zshrc' > ~/.zshrc` -- a
  stub, so edits in `zsh/` are live and installers that append to `~/.zshrc` don't touch the repo.
- VS Code user config is in `vscode/`: saving trims trailing whitespace and ends the file in one
  newline, and `Cmd+T` opens the terminal. Install by linking, so edits made in VS Code land here:
  `ln -sf ~/ws/dev-setup/vscode/{settings,keybindings}.json ~/Library/Application\ Support/Code/User/`
  On a new laptop: clone this repo to `~/ws/dev-setup`, open VS Code once so that directory
  exists, then run the `ln` — it needs no admin rights, and it replaces any settings already
  there. To confirm where VS Code keeps them, run "Preferences: Open User Settings (JSON)" from
  the Command Palette and right-click the tab → Reveal in Finder.
  On a machine whose own settings must stay (a work laptop), merge instead of linking:
  `python3 ~/ws/dev-setup/scripts/vscode_merge.py` adds these to the files already there and
  keeps the rest. Run it again after a `git pull`; see the script's docstring for the rules.

## Conventions

| Path | What it is | Where to edit |
| --- | --- | --- |
| `global-claude/CLAUDE.md`, `global-claude/settings.json` | Copies of my global `~/.claude` config | `~/.claude` — `global-claude/sync.sh` (a `Stop` hook) copies changes here and commits them |
| `global-claude/guards/` | The command guard engine | Here — `~/.claude/settings.json` runs it from this repo |
| `.claude/` | This repo's own project config (`plans/`, `guard-rules.json`), same as any project | Here |

On a new laptop, link the global `CLAUDE.md` rather than copying it:
`mkdir -p ~/.claude && ln -sf ~/ws/dev-setup/global-claude/CLAUDE.md ~/.claude/CLAUDE.md`
Claude Code reads it there, and so does Copilot Chat in VS Code when `chat.useClaudeMdFile` is
on. A linked file is edited in this repo directly, so `sync.sh` has nothing to copy — commit it
by hand.

A project's own `CLAUDE.md` holds only what's specific to it — ports, build command, tests.

## Enforcement

`global-claude/guards/command_guard.py` is a global `PreToolUse` hook that checks every Bash command
against the project's `.claude/guard-rules.json`:

- **Rules:** `deny` blocks a command with a reason; `rewrite` swaps it for `rewrite_to` (the
  README's documented command). See `tests/fixtures/docker-node-rules.json` for an example.
- **Static:** only real commands match — not text in strings, heredocs or comments.
- **No rules file:** blocks once and asks whether to add rules. A `{"_comment": "..."}` stub means
  "no rules" and never asks again.
- **Fails closed:** broken rules, or a crashing guard, block.

`global-claude/guards/batch_guard.py` is a global `PostToolUse` hook on `Edit|Write|NotebookEdit` that
makes "commit often" a check. It reads the `batch` key of the same rules file —
`{"check": "<the README's test command>", "commit_at": 3, "push_at": 5}` — and after every
change inside the project:

- **Check:** runs `check`. A failure goes back to the agent; nothing is asked or committed.
- **Commit:** below `commit_at` changes since the last commit, the agent asks "Commit?". At
  `commit_at`, the hook stages the whole tree and commits it as `wip: <every file>`.
- **Push:** at `push_at` unpushed commits, the agent asks "Push?". The hook never pushes.
- **No `batch` key:** does nothing. The count lives in `.git/batch-guard.json`, tied to `HEAD`.

## Secret leak gate

`.githooks/pre-commit` runs gitleaks (Docker, pinned) on every commit and blocks any that carries
a credential — enable with `git config core.hooksPath .githooks`.

Tests: `python3 -m unittest discover tests/`

## Pipeline

<!-- pipeline:start -->
[![Pipeline](docs/pipeline.svg)](docs/pipeline.md)

<sub>Generated from the hooks and workflows. Full detail: [`docs/pipeline.md`](docs/pipeline.md).</sub>

<details><summary>Shape, in text</summary>

```mermaid
graph LR
    agent["<b>Agent</b><br/>batch guard"]
    commit["<b>git commit</b><br/>pre-commit, post-commit (1 of 2 gate)"]
    ci["<b>CI — on push</b><br/>gitleaks, tests"]
    agent --> commit
    commit --> ci
```

</details>
<!-- pipeline:end -->

## Backlog: Refactor Along the Way

Known and deliberately not done yet. Each one gets picked up the next time I'm in that file.

- **Let one repo reuse another's guard rules** — an `extends` key in `guard-rules.json` resolved
  before `Rules.__init__`. Today every repo keeps its own copy, and copy-paste is fine until
  there are enough of them to drift.
- **Retire the `SessionStart` `cp` in `~/.claude/settings.json`.** It copies skills out of
  `interview-prep` and `CV` into `~/.claude/` on every session start — the direction this repo's
  mirroring deliberately reverses, and it's ungated.
- **`ASK_USER` is tested for wording, not for being answerable.** The tests pin length, jargon and
  a closing question; nothing catches a question that's short, clean and still confusing.
- **Package the pipeline diagram.** Make it a `pyproject.toml` package with a `pipeline-diagram`
  entry point that depends on PyYAML. It gets installed at a pinned version in each repo's CI,
  replacing the copied `scripts/pipeline_*.py`. Do it when a third repo copies the files, or the
  first time two copies drift. Until then, deploying means `cp`.
