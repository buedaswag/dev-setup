"""The README's pipeline diagram must match the pipeline it describes.

A generated diagram is only worth more than a hand-written one if something
notices when it stops matching. That is what `--check` is for, and what
`.githooks/post-commit` runs it for.

These tests are about the *renderer*, run against this repo's own pipeline.
Copied from landing-page minus the tests that assume a deploy; see
.claude/plans/2026-09-27-portable-pipeline-diagram.plan.md.
"""

import re
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.pipeline_diagram import (
    MERMAID_CLI, OUTPUT, SPINE, _id, main, render, render_overview,
)
from scripts.pipeline_scan import Group, Stage, Step, scan

PROJECT_ROOT = Path(__file__).parent.parent
README = PROJECT_ROOT / "README.md"


class TestDiagramIsCurrent(unittest.TestCase):

    def test_diagram_matches_the_pipeline(self):
        """The whole point. Change a hook, regenerate, or this fails.

            python scripts/pipeline_diagram.py
        """
        self.assertEqual(
            main(["--check"]), 0,
            f"{OUTPUT.name} no longer matches the hooks and workflows. Run "
            "`python scripts/pipeline_diagram.py` and commit the result.",
        )

    def test_the_readme_points_at_it(self):
        """A generated file nobody links to is a file nobody reads."""
        self.assertIn(
            str(OUTPUT.relative_to(PROJECT_ROOT)), README.read_text()
        )

    def test_the_readme_carries_the_overview_diagram(self):
        """The shape has to be visible without clicking through.

        GitHub renders mermaid in any markdown file, so the README gets its
        own smaller rendering of the same model rather than a picture of one.
        """
        text = README.read_text()
        self.assertIn(render_overview(scan(PROJECT_ROOT)), text)
        self.assertIn("```mermaid", text)

    def test_check_notices_a_changed_pipeline(self):
        """Proof the check isn't vacuous: perturb the model, lose the match."""
        current = render(scan(PROJECT_ROOT))
        perturbed = render(scan(PROJECT_ROOT) + [
            Stage(
                name="new-gate",
                group=Group.COMMIT,
                source=".githooks/new-gate",
                steps=[Step(command="echo hi", blocks=True)],
            )
        ])
        self.assertNotEqual(current, perturbed)
        self.assertNotEqual(perturbed, OUTPUT.read_text())

    def test_mermaid_cli_is_pinned_by_digest(self):
        """Same rule as the gitleaks image: a floating tag changes the SVG under me.

        A new mermaid release that lays the graph out differently would fail the
        drift check on a commit that changed nothing.
        """
        image = next(arg for arg in MERMAID_CLI if "mermaid-cli" in arg)
        self.assertRegex(image, r"^minlag/mermaid-cli@sha256:[0-9a-f]{64}$")


class TestRendering(unittest.TestCase):
    """Things that make the diagram wrong rather than merely ugly."""

    def setUp(self):
        self.stages = scan(PROJECT_ROOT)
        self.diagram = render(self.stages)

    def test_every_stage_appears(self):
        for stage in self.stages:
            with self.subTest(stage=stage.key):
                self.assertIn(stage.name, self.diagram)

    def test_the_spine_skips_a_phase_with_no_stages(self):
        """No pre-push hook here, so git commit must lead straight into CI.

        Linking only adjacent phases left CI floating, unconnected to anything.
        """
        ids = {group: [_id(s.key) for s in self.stages if s.group is group] for group in Group}
        present = [group for group in SPINE if ids[group]]
        for earlier, later in zip(present, present[1:]):
            with self.subTest(edge=f"{earlier.value} -> {later.value}"):
                self.assertTrue(
                    any(f"{a} --> {b}" in self.diagram for a in ids[earlier] for b in ids[later]),
                    f"nothing in {earlier.value} leads into {later.value}",
                )

    def test_a_hook_box_lists_the_scripts_it_calls_not_its_plumbing(self):
        """post-commit calls pipeline_diagram.py twice and a lot of git and echo.

        The box should say it runs the diagram script, once, and nothing else.
        """
        box = next(
            line for line in self.diagram.splitlines()
            if line.strip().startswith("post_commit[")
        )
        self.assertEqual(box.count("scripts/pipeline_diagram.py"), 1)
        for plumbing in ("git diff", "git add", "echo", "#125;"):
            self.assertNotIn(plumbing, box)

    def test_node_ids_are_unique(self):
        """`npm-audit` is defined in both workflows.

        Mermaid silently merges two nodes that share an id, which would draw
        the pull-request audit and the deploy-gating audit as one box.
        """
        ids = re.findall(r"^\s+([A-Za-z0-9_]+)\[", self.diagram, re.MULTILINE)
        self.assertEqual(sorted(ids), sorted(set(ids)))

    def test_mermaid_control_characters_are_escaped(self):
        """Real commands contain `"`, `|` and braces; raw, they break the graph.

        `health-check` runs `curl --write-out "%{http_code}"`, which has all
        three.
        """
        for label in re.findall(r'\["(.*?)"\]', self.diagram):
            with self.subTest(label=label[:40]):
                for char in '"|{}':
                    self.assertNotIn(char, label)

    def test_labels_use_mermaid_escapes_not_html_entities(self):
        """GitHub decodes `&quot;` into a real quote before mermaid parses it.

        That ends the label early and takes the whole graph down with it, so
        the escapes have to be mermaid's own `#nn;` form. This is a regression
        test for a diagram that rendered as "Unable to render rich display".
        """
        for label in re.findall(r'\["(.*?)"\]', self.diagram):
            with self.subTest(label=label[:40]):
                self.assertNotRegex(label, r"&[a-zA-Z]+;|&#\d+;")





if __name__ == "__main__":
    unittest.main()
