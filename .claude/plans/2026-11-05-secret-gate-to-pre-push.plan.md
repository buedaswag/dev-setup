# Secret gate moves from pre-commit to pre-push

## Problem

`.githooks/pre-commit` runs `scripts/secret_scan.sh || exit 1`. It blocks every commit that
has a finding, and also every commit when Docker is down, because it fails closed. A commit is a
local save point, and blocking it only grows the uncommitted tree. A secret leaks when it is
pushed, not when it is committed.

## Approach

- **pre-commit reports, never blocks.** It scans the work tree as now, prints any finding and
  says the push will block, then exits 0. This also covers the scanner being down.
- **pre-push blocks.** For each ref being pushed, it scans the commits not yet on any remote
  (`<sha> --not --remotes`) with gitleaks in git mode, using the same pinned image. It fails
  closed: no Docker, or a scanner error, blocks the push. Deleting a ref scans nothing.
- `secret_scan.sh` stays the one place the scanner lives. It gains a commit-range mode, and its
  messages stop saying "pre-commit: BLOCKED", since the hooks now decide what blocks.

Scoping to "not on any remote" rather than "not on master": commits already on the remote were
scanned when they were pushed, and rescanning them only makes the push slower.

## Sequence

1. Tests: pre-commit exits 0 with a planted secret and with no Docker, but still names the file.
2. Tests: pre-push blocks an unpushed commit carrying a secret, passes clean commits, blocks
   with no Docker, ignores commits already on the remote, passes a ref deletion.
3. Make them pass: range mode in `secret_scan.sh`, new `.githooks/pre-push`, advisory pre-commit.
4. Docs: README "Secret leak gate", `security.yml` comments, script and test headers. The
   pipeline diagram regenerates on its own in post-commit.

## Open

- `batch_guard.py` still refuses to auto-commit while `check` fails. That is a separate rule
  from the hook, and Miguel's call whether it should also become advisory.
- The landing-page pre-commit still blocks on the lockfile policy. Also Miguel's call.
