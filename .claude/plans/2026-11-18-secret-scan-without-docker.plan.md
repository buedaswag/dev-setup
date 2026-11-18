# Secret scan runs gitleaks natively, not in Docker

## Problem

`scripts/secret_scan.sh` only knows `docker run`. With Docker stopped, every push blocks and
every commit says "could not run" -- though gitleaks is already installed by Homebrew.

## Approach

Call the `gitleaks` binary. Keep what Docker was for:

- **Pinned:** the script checks `gitleaks version` against a pinned version and treats a mismatch
  as "could not run". A `brew upgrade` stops the gate until I bump the pin, instead of changing
  it silently.
- **Not PATH-fragile:** `command -v gitleaks`, falling back to the Homebrew paths, since hooks
  run from GUI git clients get a thin PATH.
- **Same as CI:** CI installs and the action runs the same pinned version.

## Sequence

1. Tests: the no-scanner seam becomes `SECRET_SCAN_GITLEAKS`; a version-mismatched scanner is
   not a pass; the script pins a version, not an image. Watch them fail.
2. Script: native `gitleaks dir` / `gitleaks git`, version check, drop the mounts.
3. CI: install the pinned gitleaks for the tests job; pin the action's version.
4. Docs: README "Secret leak gate", script header.

## Open

- Turning on GitHub push protection for this repo as an extra server-side layer. Miguel's call.
