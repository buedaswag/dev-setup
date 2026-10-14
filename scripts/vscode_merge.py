"""Merge vscode/ into a VS Code user directory that already has settings of its own.

Linking vscode/ into place is the install on my own machine, and it replaces what is
there. On a machine with settings that must stay -- a work laptop -- that is the
wrong tool, and VS Code gives no other: a settings file cannot include another one.
So this rewrites the local files in place:

    settings.json     this repo's keys are set; every other local key is kept.
                      "[language]" blocks are merged key by key, not replaced.
    keybindings.json  this repo's bindings are appended, unless already there.

The repo wins a key both sides define -- that is what deploying means -- and each
one it overwrites is printed. The rewrite is plain JSON, so comments in the local
file are lost; the file as it was is kept beside it as `<name>.bak`, and a later
rewrite backs up to `.bak2`, `.bak3`: no backup is ever written over.

Both files are read and merged before either is written, so a local file that will
not parse stops the run with nothing changed. So does one that is read-only: someone
locked it, and that is theirs to undo. A file that is a link is left alone.

Only the default profile is merged. A VS Code profile keeps its own files under
`profiles/<id>/`; the run lists any it finds, and each can be passed as the user-dir.

Run it again after pulling: it only writes when something would change.

    python3 scripts/vscode_merge.py [user-dir]

Standard library only, and nothing newer than Python 3.9, so it runs on the
python3 a locked-down Mac already has.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent / "vscode"
MAC_USER_DIR = Path.home() / "Library" / "Application Support" / "Code" / "User"


def _string_end(text: str, start: int) -> int:
    """Index just past the string whose opening quote is at `start`."""
    i = start + 1
    while i < len(text) and text[i] != '"':
        i += 2 if text[i] == "\\" else 1
    return i + 1


def _strip_comments(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            end = _string_end(text, i)
            out.append(text[i:end])
            i = end
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _strip_trailing_commas(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            end = _string_end(text, i)
            out.append(text[i:end])
            i = end
            continue
        if text[i] != "," or text[i + 1 :].lstrip()[:1] not in ("}", "]"):
            out.append(text[i])
        i += 1
    return "".join(out)


def parse_jsonc(text: str):
    """Parse JSON the way VS Code reads its own files: comments and trailing commas allowed."""
    # Comments first, so a comma that only a comment separates from its bracket is still trailing.
    return json.loads(_strip_trailing_commas(_strip_comments(text)))


def merge_settings(local: dict, repo: dict, overwritten: list) -> dict:
    merged = dict(local)
    for key, value in repo.items():
        if key.startswith("[") and isinstance(value, dict) and isinstance(local.get(key), dict):
            merged[key] = merge_settings(local[key], value, overwritten)
            continue
        if key in local and local[key] != value:
            overwritten.append(f"{key}: {json.dumps(local[key])} -> {json.dumps(value)}")
        merged[key] = value
    return merged


def merge_keybindings(local: list, repo: list) -> list:
    return local + [binding for binding in repo if binding not in local]


def _free_backup(target: Path) -> Path:
    backup = target.with_name(target.name + ".bak")
    n = 2
    while backup.exists():
        backup = target.with_name(f"{target.name}.bak{n}")
        n += 1
    return backup


def _replace(target: Path, text: str) -> None:
    """Write beside the target and rename over it, so a crash never leaves half a file."""
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    if target.exists():
        shutil.copymode(target, tmp)
    os.replace(tmp, target)


def merge_into(user_dir: Path, repo_dir: Path = REPO_DIR) -> list:
    """Merge both files into `user_dir`. Returns a line for each thing it did.

    Raises ValueError, having written nothing, if a local file cannot be read as
    what it should be, or is read-only.
    """
    report = []
    writes = []
    for name, shape in (("settings.json", dict), ("keybindings.json", list)):
        target = user_dir / name
        if target.is_symlink():
            report.append(f"{name}: is a link, left alone")
            continue
        if target.exists() and not target.stat().st_mode & 0o200:
            # Renaming a new file over it would work, which is exactly the problem.
            raise ValueError(f"{target}: is read-only")
        try:
            # utf-8-sig reads past a byte order mark, as VS Code does.
            before = target.read_text(encoding="utf-8-sig") if target.exists() else None
            # Nothing but comments is what VS Code leaves before anything is set.
            local = parse_jsonc(before) if before and _strip_comments(before).strip() else shape()
        except ValueError as error:
            raise ValueError(f"{target}: not valid JSON ({error})") from None
        if not isinstance(local, shape):
            raise ValueError(f"{target}: expected a JSON {shape.__name__} at the top level")
        repo = json.loads((repo_dir / name).read_text(encoding="utf-8"))
        overwritten = []
        if shape is dict:
            merged = merge_settings(local, repo, overwritten)
        else:
            merged = merge_keybindings(local, repo)
        if merged == local and before is not None:
            continue
        writes.append((target, before, json.dumps(merged, indent=2, ensure_ascii=False) + "\n"))
        report.append(f"{name}: updated")
        report.extend(f"  overwrote {line}" for line in overwritten)
    for target, before, after in writes:
        if before is not None:
            backup = _free_backup(target)
            shutil.copy2(target, backup)
            report.append(f"{target.name}: original kept as {backup.name}")
        _replace(target, after)
    return report


def main(argv: list) -> int:
    user_dir = Path(argv[1]).expanduser() if len(argv) > 1 else MAC_USER_DIR
    if not user_dir.is_dir():
        print(f"No VS Code user directory at {user_dir}. Open VS Code once, or pass the path.")
        return 1
    try:
        report = merge_into(user_dir)
    except ValueError as error:
        print(f"Nothing changed. {error}")
        return 1
    print("\n".join(report) if report else "Already up to date.")
    profiles = user_dir / "profiles"
    for profile in sorted(profiles.iterdir()) if profiles.is_dir() else []:
        print(f"Not merged, a profile with its own settings: {profile}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
