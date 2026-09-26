"""Tests for the pipeline scanner (copied from landing-page; see .claude/plans/2026-09-27-portable-pipeline-diagram.plan.md).

The scanner builds one model of the delivery pipeline from the files that
actually define it, so the README's diagram can be generated instead of
hand-maintained in five places that drift apart.

Everything here runs against a fixture directory: no Docker, no git repo, no
network. The scanner is pure file-reading, and keeping these tests hermetic is
what lets them assert things that would be destructive to assert for real
(deleting a hook, removing the rules file).
"""

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.pipeline_scan import Group, UnannotatedHook, scan


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip())


class PipelineScanTestCase(unittest.TestCase):
    """A fixture repo with one hook and one workflow, mutated per test."""

    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.hooks = self.root / ".githooks"
        self.workflows = self.root / ".github" / "workflows"

        write(self.hooks / "pre-commit", """
            #!/bin/sh
            # pipeline: advisory
            python scripts/ensure_server.py pre-commit || exit 1
            python -m unittest discover tests/
        """)
        write(self.workflows / "deploy.yml", """
            name: CI/CD Pipeline
            on:
              push:
                branches: [main]
            jobs:
              build-and-test:
                steps:
                  - uses: actions/checkout@v4
                  - run: npm ci
              deploy:
                needs: [build-and-test]
                steps:
                  - uses: actions/deploy-pages@v4
        """)

    def stage(self, name):
        stages = scan(self.root)
        found = [s for s in stages if s.name == name]
        self.assertEqual(
            len(found), 1,
            f"expected exactly one stage named {name!r}, "
            f"got {[s.name for s in stages]}",
        )
        return found[0]

    def names(self):
        return [s.name for s in scan(self.root)]


class TestHookDiscovery(PipelineScanTestCase):

    def test_hooks_are_found_by_listing_not_by_hardcoded_names(self):
        """A hook added to the directory shows up without touching the scanner.

        This is the whole point: the pipeline gains a step and the description
        follows automatically.
        """
        self.assertNotIn("post-commit", self.names())
        write(self.hooks / "post-commit", """
            #!/bin/sh
            # pipeline: advisory
            echo committed
        """)
        self.assertIn("post-commit", self.names())

    def test_hooks_land_in_the_phase_their_name_implies(self):
        write(self.hooks / "pre-push", """
            #!/bin/sh
            # pipeline: blocks
            python -m unittest discover tests/
        """)
        self.assertEqual(self.stage("pre-commit").group, Group.COMMIT)
        self.assertEqual(self.stage("pre-push").group, Group.PUSH)


class TestBlockingIsDeclared(PipelineScanTestCase):
    """Blocking is read from an annotation, never guessed from the shell.

    Inferring it would mean reasoning about `exit`, `||` and `&&` in general,
    which fails quietly -- the exact failure this whole exercise exists to end.
    """

    def test_annotation_sets_blocking(self):
        self.assertFalse(self.stage("pre-commit").blocks)
        write(self.hooks / "pre-commit", """
            #!/bin/sh
            # pipeline: blocks
            python -m unittest discover tests/
        """)
        self.assertTrue(self.stage("pre-commit").blocks)

    def test_one_hook_can_gate_on_one_command_and_report_another(self):
        """The case that broke CLAUDE.md.

        `pre-commit` blocks on the lockfile policy and merely reports the test
        suite. One flag per hook cannot say that, and saying "the pre-commit
        hook runs the suite" without the distinction is what went stale.
        """
        write(self.hooks / "pre-commit", """
            #!/bin/sh
            # pipeline: blocks
            python scripts/ensure_server.py pre-commit || exit 1
            # pipeline: advisory
            python -m unittest discover tests/
        """)
        gating, reporting = self.stage("pre-commit").steps
        self.assertTrue(gating.blocks)
        self.assertFalse(reporting.blocks)
        self.assertIn("ensure_server", gating.command)
        self.assertIn("unittest", reporting.command)

    def test_unannotated_command_is_loud(self):
        """No annotation must not quietly mean "blocks" or "advisory".

        A default here would be a guess about whether a gate exists, printed
        with the same confidence as a fact.
        """
        write(self.hooks / "pre-commit", """
            #!/bin/sh
            python -m unittest discover tests/
        """)
        with self.assertRaises(UnannotatedHook) as caught:
            scan(self.root)
        self.assertIn("pre-commit", str(caught.exception))

    def test_an_annotation_carries_to_following_commands(self):
        """One annotation covers the run of commands under it.

        Known limit, stated rather than hidden: a command appended below an
        `advisory` block inherits `advisory` silently. Only the *first*
        command in a hook is forced to declare. Requiring a line per command
        would catch that, at the cost of a comment on every line; the gates
        worth describing come in runs, so this is the trade taken.
        """
        write(self.hooks / "pre-commit", """
            #!/bin/sh
            # pipeline: advisory
            python -m unittest discover tests/
            echo appended-later
        """)
        self.assertEqual(
            [(s.command, s.blocks) for s in self.stage("pre-commit").steps],
            [("python -m unittest discover tests/", False),
             ("echo appended-later", False)],
        )


class TestCommandExtraction(PipelineScanTestCase):

    def test_commands_are_listed_in_order(self):
        self.assertEqual(
            self.stage("pre-commit").commands,
            [
                "python scripts/ensure_server.py pre-commit || exit 1",
                "python -m unittest discover tests/",
            ],
        )

    def test_multiline_quoted_strings_are_not_commands(self):
        """A commit message body is prose that happens to span lines.

        `post-commit` writes a multi-line `-m "..."`; without this its message
        showed up in the diagram as three more steps the pipeline runs.
        """
        write(self.hooks / "pre-commit", """
            #!/bin/sh
            # pipeline: advisory
            git commit -m "Regenerate the diagram

            python this line is the message, not a command."
            echo done
        """)
        self.assertEqual(
            self.stage("pre-commit").commands,
            ['git commit -m "Regenerate the diagram', "echo done"],
        )

    def test_heredoc_bodies_are_not_commands(self):
        """Prose inside a heredoc is text, not pipeline steps.

        The real pre-commit prints a banner this way; without this the diagram
        would list the banner's words as things the pipeline runs.
        """
        write(self.hooks / "pre-commit", """
            #!/bin/sh
            # pipeline: advisory
            python -m unittest discover tests/ && exit 0
            cat <<'EOF'
            TESTS FAILED -- commit allowed, PUSH WILL BLOCK
            python this is prose, not a command
            EOF
            exit 0
        """)
        self.assertEqual(
            self.stage("pre-commit").commands,
            ["python -m unittest discover tests/ && exit 0"],
        )


class TestWorkflows(PipelineScanTestCase):

    def test_jobs_become_stages_carrying_their_run_steps(self):
        job = self.stage("build-and-test")
        self.assertEqual(job.group, Group.CI)
        self.assertEqual(job.commands, ["npm ci"])
        self.assertEqual(job.source, ".github/workflows/deploy.yml")

    def test_needs_becomes_an_edge(self):
        self.assertEqual(self.stage("deploy").needs, ["build-and-test"])
        self.assertEqual(self.stage("build-and-test").needs, [])

    def test_continue_on_error_means_the_job_does_not_gate(self):
        write(self.workflows / "deploy.yml", """
            name: CI/CD Pipeline
            on:
              push:
                branches: [main]
            jobs:
              npm-audit:
                continue-on-error: true
                steps:
                  - run: npm audit
              deploy:
                needs: [npm-audit]
                steps:
                  - uses: actions/deploy-pages@v4
        """)
        self.assertFalse(self.stage("npm-audit").blocks)
        self.assertTrue(self.stage("deploy").blocks)

    def test_on_is_read_despite_yaml_reading_it_as_a_boolean(self):
        """`on:` is YAML's `True`. Miss that and every trigger looks absent."""
        self.assertEqual(self.stage("build-and-test").triggers, ["push"])


class TestAgentStage(PipelineScanTestCase):
    """The command guard runs before anything else, so it is stage zero.

    Only `guard-rules.json` is scanned. The engine and its hook registration
    live in ~/ws/dev-setup and ~/.claude/settings.json -- outside the repo and
    per-machine, so reading them would make the output differ by machine and
    break the drift check for everyone but the author.
    """

    RULES = """
        {
          "rewrite_to": "docker compose up --build -d",
          "deny": {"pattern": "(?:npm|yarn)\\\\s+install\\\\b", "reason": "..."},
          "rewrite": {"pattern": "(?:npm|npx|astro)\\\\b", "reason": "..."}
        }
    """

    def test_rules_file_puts_the_guard_on_the_map(self):
        write(self.root / "guard-rules.json", self.RULES)
        guard = self.stage("command guard")
        self.assertEqual(guard.group, Group.AGENT)
        self.assertEqual(guard.source, "guard-rules.json")

    def test_no_rules_file_means_no_guard_stage(self):
        """Deleting the rules file disarms the guard, and the map says so.

        The engine exits clean when it finds no rules, so this is the one way
        stage 0 can vanish. It can't be caught in the global hook without
        breaking projects that have no rules; the map showing the truth is the
        compensation.
        """
        self.assertNotIn("command guard", self.names())

    def test_a_stub_with_a_batch_key_is_a_batch_guard_not_a_command_guard(self):
        """The rules file's keys decide which guards run, not its existence.

        A `_comment` stub means the command guard has nothing to match, so
        drawing it would show a gate that isn't there. The `batch` key is what
        turns the batch guard on, and its `check` blocks the auto-commit.
        """
        write(self.root / ".claude" / "guard-rules.json", """
            {
              "_comment": "No command rules for this project.",
              "batch": {"check": "python3 -m unittest discover tests/", "commit_at": 3}
            }
        """)
        self.assertNotIn("command guard", self.names())
        guard = self.stage("batch guard")
        self.assertEqual(guard.group, Group.AGENT)
        self.assertEqual(guard.source, ".claude/guard-rules.json")
        self.assertEqual(
            [(s.command, s.blocks) for s in guard.steps],
            [("python3 -m unittest discover tests/", True)],
        )

    def test_a_deny_key_alone_is_a_command_guard(self):
        write(self.root / "guard-rules.json", """
            {"deny": {"pattern": "rm -rf", "reason": "..."}}
        """)
        self.assertIn("command guard", self.names())
        self.assertNotIn("batch guard", self.names())


if __name__ == "__main__":
    unittest.main()
