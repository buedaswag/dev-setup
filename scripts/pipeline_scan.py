"""Read the delivery pipeline out of the files that define it.

The gate behaviour used to be written down in five places -- two README
sections, CLAUDE.md, the pre-commit comment block and ensure_server.py's
docstring -- so one behaviour change cost five edits and missing one produced
a document that lied rather than a build that broke. That is what happened to
CLAUDE.md when the test gate moved to pre-push.

This module builds one model instead. It knows about git hooks, GitHub
workflows and the command guard's rules file; it knows nothing about diagrams.
Rendering lives in `pipeline_diagram.py`, deliberately separate: the model
answers questions a picture can't -- "does anything un-gated reach production?"
is a graph query, not a visual.

Scanned, in pipeline order:

    guard-rules.json        the PreToolUse guard, before a command ever runs
    $(core.hooksPath)/*     git hooks, by listing -- not by a hardcoded list
    .github/workflows/*.yml one stage per job, with `needs:` as edges

Blocking is *declared*, not inferred. See `ANNOTATION` below.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class Group(str, Enum):
    """Phases of the path from keystroke to live site, in order.

    Workflow jobs are grouped by what *triggers* them rather than by which
    file they sit in: `security.yml` and `deploy.yml` both define a job called
    `npm-audit`, but only one of them is on the road to production.
    """

    AGENT = "agent"
    COMMIT = "commit"
    PUSH = "push"
    CI = "ci"
    PR = "pr"
    SCHEDULED = "scheduled"


@dataclass
class Step:
    """One command, and whether failing it stops the operation."""

    command: str
    blocks: bool


@dataclass
class Stage:
    """One step of the pipeline, wherever it was declared.

    `blocks` is per-*step*, not per-stage, because a single hook can do both:
    `.githooks/pre-commit` gates on the lockfile policy and merely reports the
    test suite. Collapsing that to one flag per hook is what made CLAUDE.md
    claim the suite gates commits -- true of the hook, false of the suite.
    """

    name: str
    group: Group
    source: str
    steps: list[Step] = field(default_factory=list)
    needs: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)
    uses: list[str] = field(default_factory=list)
    blocks: bool = True

    @property
    def key(self) -> str:
        """Unique id for this stage, safe to use as a diagram node.

        `name` alone is not unique: `npm-audit`, `pip-audit` and `gitleaks`
        are each defined in both workflow files.
        """
        if self.group in (Group.CI, Group.PR, Group.SCHEDULED):
            return f"{Path(self.source).stem}:{self.name}"
        return self.name

    @property
    def commands(self) -> list[str]:
        return [step.command for step in self.steps]

    @property
    def deploys(self) -> bool:
        """Whether this stage is what puts the site live."""
        return any("deploy-pages" in action for action in self.uses)


class UnannotatedHook(Exception):
    """A git hook with no `# pipeline:` line.

    Raised rather than defaulted. A default would be a guess about whether a
    gate exists, rendered on the diagram with the same confidence as a fact --
    and a wrong "blocks" is exactly the lie this module exists to prevent.
    """


# Whether a command blocks is declared in the hook, next to the code it
# describes. Deciding it statically would mean analysing `exit`, `||` and `&&`
# in the general case: a rabbit hole whose failure mode is a confident wrong
# answer. Workflows need no annotation -- `continue-on-error` already says it.
#
# An annotation applies to every command after it, until the next one. So a
# hook that gates on one thing and reports another says so in two lines.
ANNOTATION = re.compile(r"^#\s*pipeline:\s*(advisory|blocks)\b")

# `cat <<'EOF'` ... `EOF`. The real pre-commit prints its banner this way, and
# the banner's prose must not be mistaken for steps the pipeline runs.
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# Control flow, not a step worth drawing.
BARE_EXIT = re.compile(r"^exit\s+\d+$")

# Where the shared guard engine looks for a project's rules, in its order.
RULE_LOCATIONS = (".claude/guard-rules.json", "guard-rules.json")

HOOK_GROUPS = {
    "pre-commit": Group.COMMIT,
    "commit-msg": Group.COMMIT,
    "post-commit": Group.COMMIT,
    "pre-push": Group.PUSH,
}

# Git's lifecycle order, so the diagram reads top to bottom. Hooks not listed
# here sort after these, alphabetically.
HOOK_ORDER = ["pre-commit", "commit-msg", "post-commit", "pre-push"]


def scan(root: Path | str) -> list[Stage]:
    """Build the full pipeline model for the repo at `root`."""
    root = Path(root)
    return _agent(root) + _hooks(root) + _workflows(root)


def _agent(root: Path) -> list[Stage]:
    """Stage zero: the command guard, if this project supplies rules.

    Only the rules file is read. The engine (~/ws/dev-setup) and its hook
    registration (~/.claude/settings.json) sit outside the repo and differ per
    machine, so reading them would make the generated diagram machine-specific
    and fail the drift check for everyone but the author. The rules file is
    tracked, and its presence is what activates the engine anyway.

    Corollary worth knowing: delete the rules file and the guard silently stops
    guarding, because the engine exits clean when it finds none. The map going
    quiet about stage 0 is the only signal there is.
    """
    rules_path = next(
        (root / name for name in RULE_LOCATIONS if (root / name).exists()), None
    )
    if rules_path is None:
        return []

    # The file is referenced, not parsed. What it denies and rewrites is the
    # guard's business and is already written out in the README; the diagram's
    # job is to say a gate exists here and point at where it is declared.
    return [
        Stage(
            name="command guard",
            group=Group.AGENT,
            source=str(rules_path.relative_to(root)),
        )
    ]


def _hooks_dir(root: Path) -> Path:
    """Honour `core.hooksPath` rather than assuming `.githooks`."""
    try:
        configured = subprocess.run(
            ["git", "-C", str(root), "config", "core.hooksPath"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        configured = ""
    return root / (configured or ".githooks")


def _hooks(root: Path) -> list[Stage]:
    """One stage per hook actually present, found by listing the directory."""
    hooks_dir = _hooks_dir(root)
    if not hooks_dir.is_dir():
        return []

    stages = []
    for path in sorted(hooks_dir.iterdir(), key=_hook_sort_key):
        if not path.is_file() or path.name.endswith(".sample"):
            continue
        steps = _steps(path.read_text(), path.relative_to(root))
        stages.append(
            Stage(
                name=path.name,
                group=HOOK_GROUPS.get(path.name, Group.COMMIT),
                source=str(path.relative_to(root)),
                steps=steps,
                blocks=any(step.blocks for step in steps),
            )
        )
    return stages


def _hook_sort_key(path: Path):
    known = path.name in HOOK_ORDER
    return (0, HOOK_ORDER.index(path.name)) if known else (1, path.name)


def _steps(script: str, source: Path) -> list[Step]:
    """The commands a hook runs, each carrying the gating declared above it.

    No comments, and no heredoc prose: the real pre-commit prints its banner
    with `cat <<'EOF'`, and those words are text, not steps.
    """
    steps = []
    mode = None
    closing = None
    quoted = False
    for line in script.splitlines():
        stripped = line.strip()
        if closing is not None:
            if stripped == closing:
                closing = None
            continue
        if quoted:
            # Inside a multi-line quoted string -- a commit message body, not
            # commands. Same rule as the heredoc above: text is not code.
            quoted = line.count('"') % 2 == 0
            continue

        declared = ANNOTATION.match(stripped)
        if declared:
            mode = declared.group(1)
            continue

        opened = HEREDOC.search(line)
        if opened:
            closing = opened.group(2)
            continue
        if not stripped or stripped.startswith("#") or BARE_EXIT.match(stripped):
            continue

        if mode is None:
            raise UnannotatedHook(
                f"{source} runs `{stripped}` with no `# pipeline:` line above "
                f"it, so whether it gates is unknown. Add `# pipeline: blocks` "
                f"or `# pipeline: advisory` above the command it describes."
            )
        steps.append(Step(command=stripped, blocks=mode == "blocks"))
        quoted = stripped.count('"') % 2 == 1
    return steps


def _workflows(root: Path) -> list[Stage]:
    """One stage per workflow job, with `needs:` carried through as edges."""
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []

    stages = []
    for path in sorted(workflows_dir.glob("*.yml")):
        document = yaml.safe_load(path.read_text()) or {}
        triggers = _triggers(document)
        for job_id, job in (document.get("jobs") or {}).items():
            needs = job.get("needs") or []
            # `continue-on-error` is a property of the job, so every step in it
            # shares the same answer -- unlike a hook, where it varies by line.
            gates = not job.get("continue-on-error", False)
            steps = job.get("steps") or []
            stages.append(
                Stage(
                    name=job_id,
                    group=_group_for(triggers),
                    source=str(path.relative_to(root)),
                    steps=[
                        Step(command=step["run"].strip(), blocks=gates)
                        for step in steps
                        if isinstance(step, dict) and step.get("run")
                    ],
                    needs=[needs] if isinstance(needs, str) else list(needs),
                    triggers=triggers,
                    uses=[
                        step["uses"]
                        for step in steps
                        if isinstance(step, dict) and step.get("uses")
                    ],
                    blocks=gates,
                )
            )
    return stages


# What starts a workflow decides where it sits. Ordered: a workflow that runs
# on push is on the road to production even if it also runs on a schedule.
TRIGGER_GROUPS = [
    ("push", Group.CI),
    ("pull_request", Group.PR),
    ("schedule", Group.SCHEDULED),
]


def _group_for(triggers: list[str]) -> Group:
    for trigger, group in TRIGGER_GROUPS:
        if trigger in triggers:
            return group
    return Group.CI


def _triggers(document: dict) -> list[str]:
    """Workflow trigger names.

    YAML 1.1 reads a bare `on:` as the boolean `True`, so the key is `True`
    and not `"on"`. Miss that and every workflow looks untriggered.
    """
    triggers = document.get("on", document.get(True)) or {}
    if isinstance(triggers, str):
        return [triggers]
    return list(triggers)
