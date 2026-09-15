#!/usr/bin/env bash
# Mirror ~/.claude/settings.json into this repo and commit it when it changes.
# Wired up as a Stop hook in the global Claude Code settings.
set -euo pipefail

REPO="$HOME/ws/python-dev-setup"
SRC="$HOME/.claude/settings.json"
DEST="$REPO/claude/settings.json"

[ -f "$SRC" ] || exit 0

# Never overwrite a good copy with a truncated or half-written one.
python3 -m json.tool "$SRC" >/dev/null 2>&1 || exit 0

mkdir -p "$(dirname "$DEST")"
cmp -s "$SRC" "$DEST" && exit 0
cp "$SRC" "$DEST"

# Path-limited add/commit: never picks up other work in progress in this repo.
git -C "$REPO" add -- claude/settings.json
git -C "$REPO" diff --cached --quiet -- claude/settings.json && exit 0
git -C "$REPO" commit -q \
  -m "Sync Claude global settings ($(date +%Y-%m-%d))" \
  -- claude/settings.json
