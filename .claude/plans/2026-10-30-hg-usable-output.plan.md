# hg: list the commands I ran, and let me pick one

## Problem

`hg terraform` is a substring grep over `fc -l`, so what comes back isn't "the terraform
commands I ran":

- **Wrong lines.** It matches the word anywhere: `mkdir terraform`, `g c -b terraform`,
  `cp ../terraform-google-vm/...`. `hg tf` matches `locustfile` and `fontfamily`.
- **Missing lines.** `tf plan` never matches `hg terraform`; aliases aren't expanded.
- **Noise.** Every repeat is printed again; each line carries an event number and a trailing
  `\n` from multi-line entries.
- **Dead end.** The output is text to copy by hand. Nothing gets it back onto the prompt.

## Approach

- A line matches when its command — the first word, alias expanded — is one of the words and
  every word appears in the (expanded) line, any order, any case. If no line's command is one
  of the words, fall back to matching anywhere, so `hg terraform-google-vm` still works.
- Print plain commands, deduplicated (latest occurrence kept), oldest first so the newest sits
  next to the prompt.
- At a terminal, number them and ask for one; the pick goes on the next prompt with `print -z`,
  to edit or run with Enter. Never executed directly. Piped, it just prints the list.

Not fzf: it isn't installed, and a numbered pick needs nothing new.

## Sequence

Tests first, one commit each.

1. Command matching with alias expansion, plus the fallback.
2. Plain, deduplicated output.
3. The picker (tested under a pty).

## Open

- Whether to add fzf as a dependency later for fuzzy picking.
- `hgt` stays as is; fold it into `hg` or drop it — mine to decide.
