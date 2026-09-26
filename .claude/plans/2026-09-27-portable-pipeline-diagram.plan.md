# Show this repo's pipeline as a generated diagram in the README

## Problem

`landing-page`'s README shows a diagram of its pipeline, generated from the hooks, workflows and
guard rules and redrawn by a post-commit hook whenever it goes stale. This repo's README has no
such diagram. Its pipeline is described in hand-written prose, which is the drift that generator
was written to kill.

Copying the code over as-is doesn't work:

- **Stage 0 would lie.** Any rules file puts "command guard" on the map. This repo's
  `.claude/guard-rules.json` is the `_comment` stub (no command rules) plus a `batch` key, so the
  diagram would show a guard that doesn't run and leave out the batch guard, which does.
- **This repo's hooks are unannotated.** `.githooks/pre-commit` has no `# pipeline:` line, and
  the scan raises `UnannotatedHook`, as it's meant to.
- **Three diagram tests are specific to `landing-page`.** `test_non_blocking_stages_are_marked`,
  `test_the_deploy_reaches_the_live_site` and `test_needs_are_drawn_within_their_own_workflow`
  assume a deploy step, a job that reports without blocking, and `landing-page`'s job names.
- **The scan needs PyYAML.** This repo is stdlib-only, and CI installs nothing.

## Approach

Copy from `~/ws/personal/landing-page`. `landing-page` is **not** changed.

| From `landing-page` | To here | Note |
| --- | --- | --- |
| `scripts/pipeline_scan.py`, `scripts/pipeline_diagram.py`, `scripts/__init__.py` | same paths | new `scripts/` dir |
| `tests/test_pipeline_scan.py` | same | fixture-based, repo-agnostic |
| `tests/test_pipeline_diagram.py` | same, minus the 3 tests above | the rest check this repo |
| `.githooks/post-commit` | same | redraws the diagram after a commit |
| — | not copied | `tests/test_pipeline_gates.py`, which tests `landing-page`'s own hooks |

Changes to the copied code:

- **Stage 0 reads the rules file's keys.** Draw a command-guard stage only if there are `deny`/`rewrite`
  rules, and a batch-guard stage only if there's a `batch` key. `batch.check` is its one step,
  and it blocks the auto-commit.
- **Neutral header.** "Everything from a command an agent proposes to the live site" becomes
  "…to the last gate". This repo has no deploy, and the live node is already conditional.
- **Pin the mermaid-cli image** by digest, as `.githooks/pre-commit` pins gitleaks.

The expected result is Agent (batch guard) → git commit (`pre-commit` blocks, `post-commit`
reports) → CI on push (`security.yml`: `gitleaks`, `tests`). There's no live node, because
nothing deploys from here.

## Sequence

Tests first for each step, and one commit per step. Run the tests with `python3 -m unittest discover tests/`.

1. **Copy the scan.** Add `requirements.txt` with `pyyaml`, add a `pip install -r requirements.txt`
   step to the `tests` job in `.github/workflows/security.yml`, and install it locally. Copy
   `scripts/` and `test_pipeline_scan.py`, which pass unchanged.
2. **Stage 0 tells the truth.** Add two tests to `test_pipeline_scan.py`: stub plus `batch` gives
   a `batch guard` stage and no `command guard`, and a `deny` key gives `command guard`. Watch the
   first one fail, then fix `_agent()`.
3. **Make pre-commit legible.** Move the gitleaks body out of `.githooks/pre-commit` into
   `scripts/secret_scan.sh`. The hook becomes `# pipeline: blocks` plus
   `scripts/secret_scan.sh "$@" || exit 1`. In `tests/test_secret_scan.py`, the two tests that read
   the hook's source (`test_scanner_image_is_pinned_by_digest`, `test_hook_does_not_build_anything`)
   must read `scripts/secret_scan.sh` instead. Change them first and watch them fail. Every
   behaviour test stays unchanged, and passing them is the proof that the annotation is true.
4. **Generate the diagram.** Copy `test_pipeline_diagram.py` minus the 3 tests, and watch the drift
   test fail. Add a `## Pipeline` section to `README.md` between "Secret leak gate" and "Backlog",
   with `<!-- pipeline:start -->` / `<!-- pipeline:end -->`. Copy `post-commit` and change nothing
   in it. Run `python3 scripts/pipeline_diagram.py`, which writes `docs/pipeline.{md,mmd,svg}` and
   fills the markers. Leave the Enforcement prose alone: it explains the rules, and the diagram
   shows where they run.
   **Done when:** the README on GitHub shows this repo's pipeline diagram and the suite is green.
5. **Backlog.** Add the item below to the README's backlog.

## Backlog item (README)

- **Package the pipeline diagram.** Make it a `pyproject.toml` package with a `pipeline-diagram`
  entry point that depends on PyYAML. It gets installed at a pinned version in each repo's CI,
  replacing the copied `scripts/pipeline_*.py`. Do it when a third repo copies the files, or the
  first time two copies drift. Until then, deploying means `cp`.

## Open — mine to decide (defaults let an agent start)

1. **PyYAML as this repo's first dependency.** Default: `requirements.txt`, as above.
2. **Should the diagram say the guards are live before commit?** `~/.claude/settings.json` runs
   them from this working tree. Default: no. That file is per-machine, and the scan deliberately
   reads only tracked files.
