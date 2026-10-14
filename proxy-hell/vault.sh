#!/usr/bin/env bash
# Password-encrypt a file so only its ciphertext is committed. This repo is public;
# notes naming internal hosts and accounts live here as FILE.enc, FILE is gitignored.
#
#   proxy-hell/vault.sh encrypt proxy-hell/debug.md      # -> proxy-hell/debug.md.enc
#   proxy-hell/vault.sh decrypt proxy-hell/debug.md.enc  # -> proxy-hell/debug.md
#
# openssl prompts for the password; VAULT_PASSWORD is read instead when set.
#
# Plain `openssl enc`, because the corporate laptop can't install age or gpg but ships
# LibreSSL as /usr/bin/openssl, and that decrypts this. AES-256-CBC with a PBKDF2 key
# makes guessing the password slow -- it is still only as strong as the password, and
# the ciphertext is public forever, so use a long one.
set -euo pipefail

CIPHER=(-aes-256-cbc -pbkdf2 -iter 600000 -md sha256 -a)

usage() { echo "usage: $0 encrypt FILE | decrypt FILE.enc" >&2; exit 2; }
[ $# -eq 2 ] || usage

pass=()
[ -n "${VAULT_PASSWORD:-}" ] && pass=(-pass env:VAULT_PASSWORD)

case "$1" in
  encrypt)
    openssl enc "${CIPHER[@]}" -salt ${pass[@]+"${pass[@]}"} -in "$2" -out "$2.enc"
    ;;
  decrypt)
    [[ "$2" == *.enc ]] || usage
    out="${2%.enc}"
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    openssl enc -d "${CIPHER[@]}" ${pass[@]+"${pass[@]}"} -in "$2" -out "$tmp"
    # Pulling then decrypting must not eat edits made since the last encrypt.
    if [ -e "$out" ] && ! cmp -s "$tmp" "$out"; then
      echo "vault: $out differs from $2 -- encrypt it first, or delete it to take the committed version" >&2
      exit 1
    fi
    mv "$tmp" "$out"
    ;;
  *) usage ;;
esac
