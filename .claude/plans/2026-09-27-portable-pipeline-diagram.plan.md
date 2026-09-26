# Bring the pipeline diagram here, and make it portable

## Problem

`landing-page` generates its pipeline diagram from the pipeline itself
(`scripts/pipeline_scan.py` → `scripts/pipeline_diagram.py`, redrawn by `.githooks/post-commit`,
drift-checked by a test). This repo has the same kind of pipeline — guards, a blocking
pre-commit, CI — and describes it by hand in the README, which is the drift that code was
written to kill.

The code can't just be copied over. It only works for `landing-page`:

- **Paths come from `__file__`.** `PROJECT_ROOT`, `README`, `docs/pipeline.*` are module
  constants, and `pipeline_diagram` imports `scripts.pipeline_scan`. Put it anywhere else and it breaks.
- **Stage 0 would lie here.** Finding a rules file puts "command guard" on the map. This repo's rules
  file is the `_comment` stub (no command rules) plus a `batch` key, so the diagram would show
  a guard that isn't there and leave out the batch guard, which is.
- **This repo's hooks are unannotated.** `.githooks/pre-commit` has no `# pipeline:` line, so
  the scan raises `UnannotatedHook`, as it's meant to.
- **This repo is stdlib-only.** The scan needs PyYAML; CI runs `unittest` with nothing installed.

## Approach

**This repo becomes the canonical home, and other repos copy from it verbatim.** Same files,
same paths (`scripts/pipeline_scan.py`, `scripts/pipeline_diagram.py`), so deploying means running
`cp ~/ws/dev-setup/scripts/pipeline_*.py scripts/` plus four one-time steps in the repo: markers
in the README, a `# pipeline:` line per hook command, the post-commit hook and the drift test.
The copies have no per-repo edits, so a diff against this repo shows any drift.

Why not run it from `~/ws/dev-setup` the way the guards run? The drift check runs in each repo's
CI, and CI has no dev-setup clone. The guards get away with it because they only run on my
machine. The honest fix for "same code in many repos" is a package, and that goes on the backlog, not in
this plan.

To make the copies verbatim, the code needs to change:

- **Root from the repo, not the file.** Use `git rev-parse --show-toplevel` (or `--root`). Output paths and
  markers stay as today's defaults. Add no config file until a repo needs different ones.
- **Sibling import.** `pipeline_diagram` imports `pipeline_scan` from its own directory.
- **Stage 0 reads the rules file's keys.** Draw a command-guard stage only if there are `deny`/`rewrite` rules,
  and a batch-guard stage only if there's a `batch` key. `batch.check` is its one blocking step (it
  gates the auto-commit). Still only the tracked file, never `~/.claude/settings.json`.
- **Neutral header copy.** Drop "to the live site"; the deploy node is already conditional.
- **Pin the mermaid-cli image**, as the gitleaks image is pinned.

## Sequence

Tests first for each step, and one commit per step.

1. **Faithful copy.** Copy both modules and `test_pipeline_scan.py`/`test_pipeline_diagram.py`
   into this repo and add PyYAML (Open 1). The scan tests pass as-is. That's expected: they prove the copy is faithful.
2. **Root-independent.** New test: run `main()` against a fixture repo in a tmp dir and expect
   `docs/pipeline.md` there. It fails because the output lands next to the script. Fix it.
3. **Stage 0 tells the truth.** New tests: a stub-plus-`batch` rules file gives a batch-guard stage
   and no command-guard stage, and a `deny` rule gives a command-guard stage. The first fails today.
4. **Annotate and generate here.** The drift test fails with `UnannotatedHook`. Add
   `# pipeline: blocks` above the gitleaks run (`test_secret_scan.py` already proves it
   blocks). Add README markers, generate `docs/`, add `post-commit`, and replace the hand-written
   Enforcement prose with a pointer to the generated diagram wherever the two overlap.
   **Done when:** the README here shows this repo's pipeline diagram.
5. **Backlog.** Add the item below to the README's backlog.

## Backlog item (README)

- **Package the pipeline diagram.** Make it a `pyproject.toml` package with a `pipeline-diagram`
  entry point that depends on PyYAML. It gets installed at a pinned version in each repo's CI and
  dev image, and the scripts/ copies go away. Do it when a third repo copies the files, or the
  first time two copies drift, whichever comes first. Until then, `cp` plus a `diff` is the deployment.

## Open — mine to decide

1. **PyYAML here:** a `requirements.txt` plus `pip install -r` in `security.yml` (recommended),
   or give up stdlib-only a different way. This repo has no dependencies today.
2. **Should the map say the guards are live before commit?** `~/.claude/settings.json` runs
   them from this working tree, so a saved edit is live before any gate runs. That's true, but it's
   per-machine, which is the reason the scan doesn't read settings. Leave it as README prose, or
   draw it anyway?

Out of scope: changing `landing-page`. It keeps its own copy for now.
