#!/usr/bin/env bash
# Mirror my global Claude Code config into this repo and commit what changed.
# Wired up as a Stop hook in ~/.claude/settings.json, async, failure-tolerant.
#
# Direction is one-way: ~/.claude is where I edit, this repo is the mirror. Never
# the reverse -- a restore is a deliberate `cp` by hand, not something a hook does.
set -euo pipefail

REPO="$HOME/ws/dev-setup"
SRC_ROOT="$HOME/.claude"
DEST_ROOT="$REPO/global-claude"

# Paths relative to ~/.claude. Add a line to sync one more thing.
PATHS=(
  settings.json
  CLAUDE.md
)

changed=()

for rel in "${PATHS[@]}"; do
  src="$SRC_ROOT/$rel"
  dest="$DEST_ROOT/$rel"

  [ -f "$src" ] || continue

  # Never overwrite a good copy with a truncated or half-written one. A Stop hook
  # can fire while something else is mid-write.
  case "$rel" in
    *.json) python3 -m json.tool "$src" >/dev/null 2>&1 || continue ;;
  esac

  cmp -s "$src" "$dest" && continue

  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  changed+=("global-claude/$rel")
done

[ ${#changed[@]} -eq 0 ] && exit 0

# Path-limited add/commit: never picks up other work in progress in this repo.
git -C "$REPO" add -- "${changed[@]}"
git -C "$REPO" diff --cached --quiet -- "${changed[@]}" && exit 0
git -C "$REPO" commit -q \
  -m "Sync Claude global config ($(date +%Y-%m-%d))" \
  -- "${changed[@]}"
