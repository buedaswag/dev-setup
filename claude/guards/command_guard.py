#!/usr/bin/env python3
"""PreToolUse guard: make a project's documented command the only one that runs.

`How I Work` says rules worth having are worth enforcing. Prose is a suggestion --
an agent reads "everything runs in Docker" and still asks to run `npm run build`,
and someone has to say No at the permission prompt. This makes it a static check.

Claude Code pipes the pending Bash command here as JSON before the prompt is
shown. We match it against the project's rules and print one of three decisions:

    nothing   the command was not matched; it runs untouched
    deny      with a reason the agent can act on (edit package.json)
    allow     carrying `updatedInput` -- a rewritten command, which is what runs

The rewrite path is the point: no prompt appears, the documented command runs
instead, and the agent's turn continues. No LLM in the loop.

This file is the engine and is project-agnostic. The rules are not: they load
from `guard-rules.json` at the project root ($CLAUDE_PROJECT_DIR), or from the
path given as argv[1]. No rules file, no decision -- the guard exits clean.

Three rules keep the rewrite honest, all three learned from a real failure where
a heredoc writing ASTRO_MIGRATION.md was silently replaced by the Docker command
because the prose inside it contained "PR #30 (astro 5->7)":

  1. Text is not code. Heredoc bodies, quoted strings and comments are masked
     out before matching, so writing *about* npm never looks like running it.
  2. Rewrite the segment, not the script. Only the offending segment of a
     compound command is replaced; its neighbours survive untouched.
  3. Never drop an install. If any segment is a deny match, the whole command is
     denied -- rewriting one half while discarding the other is the same bug.

The replacement is whatever the project's README documents. When the README
changes, change `guard-rules.json` to match -- the README is the source of truth.
"""

import json
import os
import re
import sys

# A command only counts when it sits in command position -- start of the line, or
# right after a separator. Keeps `grep "npm install" README.md` from matching.
CMD_POS = r"(?:^|[;&|(]\s*|\bthen\s+|\bdo\s+|\bsh\s+-c\s+['\"]?)"

# Top-level separators. Splitting on these lets us rewrite one segment and leave
# the rest of the script alone.
SEPARATOR = re.compile(r"&&|\|\||;|\n|\|")

# A pipe consumes the previous segment's output; `&&`, `;` and a newline are
# sequential steps that can race a server that has not finished coming up.
SEQUENTIAL = {"&&", "||", ";", "\n"}

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


class NoRules(Exception):
    """No guard-rules.json at all -- this project has never been asked."""


class BadRules(Exception):
    """There is a rules file and it cannot be used. Never fail open on this."""


class Rules:
    """A project's guard-rules.json, validated enough to fail loudly at load.

    Fields, all optional -- `{}` is a valid, inert ruleset:
      rewrite_to    the documented command a matched invocation becomes.
                    Required only when there is a `rewrite` rule to use it.
      ready_wait    appended after `rewrite_to` when another segment follows it
                    sequentially, so the next step cannot race a server that has
                    been started detached and is not up yet
      skip_if       substrings that mean "this segment is already correct"
      deny/rewrite  {pattern, reason}; `{rewrite_to}` in a reason is filled in
    """

    def __init__(self, data):
        if not isinstance(data, dict):
            raise BadRules("the top level must be a JSON object")
        self.rewrite_to = data.get("rewrite_to", "")
        self.ready_wait = data.get("ready_wait", "")
        self.skip_if = data.get("skip_if", [])
        if data.get("rewrite") and not self.rewrite_to:
            raise BadRules("a `rewrite` rule needs `rewrite_to` -- nothing to rewrite into")

        def compile_rule(key):
            rule = data.get(key)
            if not rule:
                return None, ""
            try:
                pattern = re.compile(CMD_POS + rule["pattern"])
                reason = rule["reason"].format(rewrite_to=self.rewrite_to)
            except (KeyError, TypeError, IndexError, re.error) as error:
                raise BadRules(f"`{key}` rule is unusable: {error}") from error
            return pattern, reason

        self.deny_pattern, self.deny_reason = compile_rule("deny")
        self.rewrite_pattern, self.rewrite_reason = compile_rule("rewrite")

    @property
    def rewrite_then_wait(self):
        if not self.ready_wait:
            return self.rewrite_to
        return f"{self.rewrite_to} && {self.ready_wait}"


def load_rules(path=None):
    """Load the project's rules.

    Raises NoRules when there is no file (never been asked) and BadRules when
    there is one that cannot be used (asked, answered, and now broken). Returns
    None only when there is no project to guard at all.
    """
    if path is None:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        if not project_dir:
            # Not running under Claude Code, so there is no project in play.
            return None
        path = os.path.join(project_dir, "guard-rules.json")

    if not os.path.exists(path):
        raise NoRules(path)

    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise BadRules(f"cannot be read as JSON: {error}") from error

    return Rules(data)


def mask_data(command):
    """Blank out everything that is data, keeping length and structure intact.

    Returns a string the same length as `command` with heredoc bodies, quoted
    strings and comments replaced by spaces. Offsets still line up, so a match
    found in the mask points at the same place in the original.
    """
    chars = list(command)

    def blank(start, end):
        for i in range(start, min(end, len(chars))):
            if chars[i] != "\n":
                chars[i] = " "

    # Heredoc bodies first: they can contain quotes and #, and must not be read
    # as either. This is the case that caused the original failure.
    for match in HEREDOC.finditer(command):
        delimiter = match.group(2)
        body_start = command.find("\n", match.end())
        if body_start == -1:
            continue
        terminator = re.compile(r"^\s*" + re.escape(delimiter) + r"\s*$", re.M)
        end = terminator.search(command, body_start + 1)
        blank(body_start + 1, end.start() if end else len(command))

    masked = "".join(chars)

    # Quoted strings. `sh -c "npm run build"` is a real invocation, so a quoted
    # string used as a -c payload stays visible; everything else is data.
    def mask_quoted(match):
        preceding = masked[: match.start()].rstrip()
        if preceding.endswith("-c"):
            return match.group(0)
        body = match.group(0)
        return body[0] + " " * (len(body) - 2) + body[-1]

    masked = re.sub(r"'[^']*'", mask_quoted, masked)
    masked = re.sub(r'"[^"]*"', mask_quoted, masked)

    # Comments last -- any # inside a string or heredoc is already gone.
    masked = re.sub(r"#[^\n]*", lambda m: " " * len(m.group(0)), masked)

    return masked


def split_segments(masked):
    """Yield (start, end, separator_after) for each top-level segment."""
    spans = []
    start = 0
    for match in SEPARATOR.finditer(masked):
        spans.append((start, match.start(), match.group(0)))
        start = match.end()
    spans.append((start, len(masked), ""))
    return spans


def decide(command, rules):
    """Return (decision, reason, new_command) for a Bash command, or None.

    `new_command` is only meaningful for an "allow" decision.
    """
    masked = mask_data(command)
    spans = split_segments(masked)

    to_rewrite = []
    for index, (start, end, _separator) in enumerate(spans):
        segment = masked[start:end]
        if not segment.strip():
            continue
        # Already correct -- `docker compose run web npm ci` is exactly right.
        if any(token in segment for token in rules.skip_if):
            continue
        if rules.deny_pattern and rules.deny_pattern.search(segment.lstrip()):
            return "deny", rules.deny_reason, None
        if rules.rewrite_pattern and rules.rewrite_pattern.search(segment.lstrip()):
            to_rewrite.append((index, start, end))

    if not to_rewrite:
        return None

    # Splice the replacements into the ORIGINAL text, back to front so the
    # earlier spans keep their offsets.
    result = command
    for index, start, end in reversed(to_rewrite):
        separator_after = spans[index][2]
        follows_sequentially = separator_after in SEQUENTIAL and any(
            masked[s:e].strip() for s, e, _ in spans[index + 1:]
        )
        replacement = rules.rewrite_then_wait if follows_sequentially else rules.rewrite_to
        # Replace only the segment's content, keeping the whitespace that sits
        # against the separators -- otherwise `... && npm run build && ...`
        # splices into `...&&docker compose up...`, which is valid but unreadable.
        segment = command[start:end]
        lead = len(segment) - len(segment.lstrip())
        trail = len(segment) - len(segment.rstrip())
        result = result[:start + lead] + replacement + result[end - trail:]

    return "allow", rules.rewrite_reason, result


STUB = '{"_comment": "No guard rules for this project. Hook: ~/.claude/settings.json"}'

ASK = """No guard-rules.json in this project, so the command guard has nothing to enforce.

Ask the user whether they want guard rules here. Guard rules let a repo force agents onto its
documented commands instead of trusting them to read the README -- the landing-page project
rewrites any `npm`/`npx`/`astro` call to `docker compose up --build -d` and denies installs
outright, with no permission prompt and no LLM in the loop.

If they want them, write {path} with `rewrite_to` and a `deny`/`rewrite` pattern pair.
If they don't, write exactly this to {path} so the question is never asked again:

    {stub}

Do not work around this by other means."""


def block(message):
    """Exit 2: the only exit code Claude Code treats as blocking."""
    print(message, file=sys.stderr)
    sys.exit(2)


def main():
    try:
        rules = load_rules(sys.argv[1] if len(sys.argv) > 1 else None)
    except NoRules as error:
        block(ASK.format(path=error, stub=STUB))
    except BadRules as error:
        path = sys.argv[1] if len(sys.argv) > 1 else "guard-rules.json"
        block(
            f"This project's guard-rules.json ({path}) is opted in but unusable: {error}\n"
            "Fix the rules file. Do not work around this, and do not delete the file to "
            "silence it -- an empty object is how a project opts out."
        )

    if rules is None:
        return

    try:
        payload = json.load(sys.stdin)
        tool_input = payload["tool_input"]
        command = tool_input["command"]
        if payload["tool_name"] != "Bash":
            return
    except (json.JSONDecodeError, KeyError, TypeError):
        # A broken guard must never block the agent: say nothing, exit clean.
        return

    verdict = decide(command, rules)
    if verdict is None:
        return
    decision, reason, new_command = verdict

    output = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    if decision == "allow":
        # Carry the rest of the tool input through; only the command changes.
        output["updatedInput"] = {**tool_input, "command": new_command}

    json.dump({"hookSpecificOutput": output}, sys.stdout)


if __name__ == "__main__":
    main()
