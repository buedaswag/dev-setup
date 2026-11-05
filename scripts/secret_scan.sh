#!/usr/bin/env bash
# Secret scan. Exit 0 when clean, non-zero when it found something or could not run.
# The hooks decide what that costs:
#
#   .githooks/pre-commit  secret_scan.sh           work tree; reports, never blocks
#   .githooks/pre-push    secret_scan.sh --pushed  outgoing commits; blocks
#
# A secret leaks when it is pushed, not when it is committed. A commit is a local
# save point, and blocking one only grows the uncommitted tree -- worse with
# global-claude/sync.sh committing on its own from a Stop hook. So the commit gets a
# heads-up and the push is the gate. The GitHub Action in .github/workflows/security.yml
# is a backstop for what gets in around the push hook, not the gate itself.
#
# Scanner is gitleaks in Docker, pinned by digest:
#   - Docker, so the gate does not depend on an activated venv being on PATH.
#     zsh/py-venvs.sh auto-activates one, and a gate that silently stops gating the
#     day that changes is worse than no gate.
#   - the same tool CI runs, so local and CI cannot drift apart.
#   - by digest, because a floating tag changes the gate under me and re-pulls on
#     every run, turning 30ms into a network round trip.
# Pull and run only. Never build -- a hook that builds is a hook I disable.
#
set -uo pipefail

SCANNER="ghcr.io/gitleaks/gitleaks@sha256:e1b35e12a8c6fa8901f060459cfb6b2fc4c484d3afbe3b029733a3bbfab07055"
# The seam the tests use to take the scanner away. Normal runs never set it.
DOCKER="${SECRET_SCAN_DOCKER:-docker}"

# gitleaks exits 1 for findings. Anything else is the scanner itself failing --
# daemon down, image unpullable, no network on a cold cache. Both are non-zero,
# but they are different problems and the message should say which.
#
# --verbose is what prints the file and line of each finding; without it the output
# is a bare "leaks found: 3", which tells me there is a problem and not where.
# --redact keeps the value itself out of the terminal and my scrollback.
# Docker's own options go in RUN_OPTS; the arguments are gitleaks'.
RUN_OPTS=()
scan() {
  local what="$1" strip="$2"
  shift 2
  local output status
  # No scanner is not a pass -- it is "could not scan", and the caller decides.
  if ! command -v "$DOCKER" >/dev/null 2>&1; then
    echo "secret scan: could not run -- docker not found. Start Docker." >&2
    return 2
  fi
  output="$("$DOCKER" run --rm "${RUN_OPTS[@]}" "$SCANNER" "$@" --redact --no-banner --verbose 2>&1)"
  status=$?
  [ $status -eq 0 ] && return 0
  if [ $status -ne 1 ]; then
    echo "secret scan: could not run (exit $status)." >&2
    echo "$output" >&2
    return 2
  fi
  # Paths come back rooted at the container mount; show them as I would type them.
  echo "secret scan: possible secrets in $what." >&2
  echo "${output//$strip/}" >&2
  echo "Values above are redacted." >&2
  return 1
}

# --- pre-push: every commit this push adds ---------------------------------------
#
# git feeds one line per ref: <local ref> <local sha> <remote ref> <remote sha>.
# The range is `<local sha> --not --remotes`: commits no remote ref has yet. What a
# remote already has was scanned when it was pushed, and rescanning it only makes
# every push slower. A deletion pushes the all-zero sha and carries nothing.
#
# This is gitleaks' git mode, so a token added in one commit and deleted in the
# next is still found -- it is in what gets pushed.
if [ "${1:-}" = "--pushed" ]; then
  top="$(git rev-parse --show-toplevel)" || exit 2
  common="$(git rev-parse --path-format=absolute --git-common-dir)" || exit 2
  # Mounted at their own paths so a worktree's `.git` file, which names the common
  # dir by absolute path, still resolves inside the container.
  RUN_OPTS=(-v "$top:$top:ro" -w "$top")
  case "$common" in "$top"/*) ;; *) RUN_OPTS+=(-v "$common:$common:ro") ;; esac

  worst=0
  while read -r _ local_sha _ _; do
    [ -z "${local_sha//0/}" ] && continue
    scan "commits about to be pushed" "$top/" \
      detect --source "$top" --log-opts="$local_sha --not --remotes"
    status=$?
    [ $status -gt $worst ] && worst=$status
  done
  exit $worst
fi

# --- pre-commit: the work tree ---------------------------------------------------
#
# Scans the whole work tree, not just staged files: a secret sitting unstaged in the
# tree is one `git add -A` away from being committed anyway.

# argv[1] is the seam the tests drive. Normal hook invocation passes nothing.
TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  TARGET="$(git rev-parse --show-toplevel)" || {
    echo "secret scan: not inside a git work tree" >&2
    exit 2
  }
fi

# Scan what a commit could actually carry: tracked files plus untracked ones that
# .gitignore does not exclude. Untracked counts -- `git add -A` is one keystroke.
#
# gitleaks has no flag for this. `--no-git` walks the filesystem and ignores
# .gitignore entirely, which meant scanning __pycache__, and would mean node_modules
# and .venv in any other repo. Those cannot reach a commit, so a finding there is
# always a false positive, and a gate that cries wolf is a gate I switch off. So the
# file list comes from git and gets staged into a scratch tree that gitleaks sees.
SCAN_ROOT="$TARGET"
STAGE=""
cleanup() { [ -n "$STAGE" ] && rm -rf "$STAGE"; }
trap cleanup EXIT

if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  STAGE="$(mktemp -d)"
  # NUL-delimited throughout: paths with spaces or newlines are still paths.
  if ! git -C "$TARGET" ls-files -z --cached --others --exclude-standard \
      | (cd "$TARGET" && tar -cf - --null -T - 2>/dev/null) \
      | tar -xf - -C "$STAGE" 2>/dev/null; then
    echo "secret scan: could not run -- could not assemble the file list." >&2
    exit 2
  fi
  SCAN_ROOT="$STAGE"
fi

RUN_OPTS=(-v "$SCAN_ROOT:/scan:ro")
scan "the work tree" "/scan/" detect --no-git --source /scan
