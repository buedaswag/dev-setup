"""Tests for the PreToolUse command guard.

The guard is a static regex check -- no LLM, no network -- so these run fast and
need nothing else running.

They drive the engine through the same path Claude Code does: JSON on stdin,
JSON on stdout, with a rules file supplied as argv[1]. The fixture is the real
Docker/npm ruleset from the landing-page project, so these are the engine's
tests and that project's integration test at once.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "claude" / "guards" / "command_guard.py"
RULES = ROOT / "tests" / "fixtures" / "docker-node-rules.json"
DOCKER_UP = "docker compose up --build -d"


def run_guard(command, tool_name="Bash", rules=RULES, project_dir=None):
    payload = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command, "description": "test"},
        }
    )
    argv = [sys.executable, str(GUARD)]
    if rules is not None:
        argv.append(str(rules))
    # These tests run under Claude Code, which sets CLAUDE_PROJECT_DIR. Leaving it
    # set would let the real environment decide what the fallback path resolves to.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        argv, input=payload, capture_output=True, text=True, env=env
    )


def decide(command, tool_name="Bash", rules=RULES):
    """Run the guard the way Claude Code does, returning its decision or None."""
    result = run_guard(command, tool_name, rules)
    assert result.returncode == 0, f"guard exited {result.returncode}: {result.stderr}"
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


class TestDeniedCommands(unittest.TestCase):
    """Installs never happen on the host -- deps go in package.json."""

    def test_npm_install_is_denied(self):
        out = decide("npm install")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("package.json", out["permissionDecisionReason"])

    def test_npm_install_with_package_is_denied(self):
        self.assertEqual(decide("npm install lodash")["permissionDecision"], "deny")

    def test_npm_shorthand_install_is_denied(self):
        self.assertEqual(decide("npm i lodash")["permissionDecision"], "deny")

    def test_npm_ci_is_denied(self):
        self.assertEqual(decide("npm ci")["permissionDecision"], "deny")

    def test_yarn_and_pnpm_install_are_denied(self):
        self.assertEqual(decide("yarn install")["permissionDecision"], "deny")
        self.assertEqual(decide("pnpm install")["permissionDecision"], "deny")

    def test_npm_init_is_not_mistaken_for_install(self):
        self.assertNotEqual(decide("npm init -y")["permissionDecision"], "deny")


class TestRewrittenCommands(unittest.TestCase):
    """Everything else becomes the one command the README documents."""

    def test_npm_run_build_is_rewritten(self):
        out = decide("npm run build")
        self.assertEqual(out["permissionDecision"], "allow")
        self.assertEqual(out["updatedInput"]["command"], DOCKER_UP)

    def test_rewrite_preserves_trailing_pipeline(self):
        """Was `drops`: the rewrite used to discard everything after the pipe.

        Dropping neighbours is the bug this guard was fixed for. A pipe consumes
        output rather than running after the server is up, so no readiness wait.
        """
        out = decide("npm run build 2>&1 | tail -15")
        rewritten = out["updatedInput"]["command"]
        self.assertIn(DOCKER_UP, rewritten)
        self.assertIn("| tail -15", rewritten)
        self.assertNotIn("localhost:4444", rewritten)

    def test_npm_run_dev_is_rewritten(self):
        self.assertEqual(decide("npm run dev")["updatedInput"]["command"], DOCKER_UP)

    def test_npm_start_is_rewritten(self):
        self.assertEqual(decide("npm start")["updatedInput"]["command"], DOCKER_UP)

    def test_npm_run_preview_is_rewritten(self):
        self.assertEqual(decide("npm run preview")["updatedInput"]["command"], DOCKER_UP)

    def test_npm_test_is_rewritten(self):
        self.assertEqual(decide("npm test")["updatedInput"]["command"], DOCKER_UP)

    def test_astro_build_is_rewritten(self):
        self.assertEqual(decide("npx astro build")["updatedInput"]["command"], DOCKER_UP)
        self.assertEqual(decide("astro dev")["updatedInput"]["command"], DOCKER_UP)

    def test_rewrite_is_detached(self):
        """A foreground `up` never exits and would hang the agent to its timeout."""
        self.assertIn(" -d", decide("npm run build")["updatedInput"]["command"])

    def test_rewrite_preserves_other_tool_input_fields(self):
        out = decide("npm run build")
        self.assertEqual(out["updatedInput"]["description"], "test")

    def test_rewrite_explains_itself(self):
        out = decide("npm run build")
        self.assertIn("README", out["permissionDecisionReason"])


class TestPassThrough(unittest.TestCase):
    """Anything the rules do not match runs untouched."""

    def test_unrelated_command_is_untouched(self):
        self.assertIsNone(decide("git status"))

    def test_npm_inside_docker_is_untouched(self):
        self.assertIsNone(decide("docker compose run --rm web npm ci"))

    def test_npm_as_an_argument_is_untouched(self):
        self.assertIsNone(decide('grep "npm install" README.md'))

    def test_python_tests_are_untouched(self):
        self.assertIsNone(decide("python -m unittest discover tests/"))

    def test_non_bash_tools_are_untouched(self):
        self.assertIsNone(decide("npm install", tool_name="Read"))


class TestMalformedInput(unittest.TestCase):
    """A broken hook must never block the agent."""

    def test_garbage_stdin_exits_clean(self):
        result = subprocess.run(
            [sys.executable, str(GUARD), str(RULES)],
            input="not json",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


class TestRulesLoading(unittest.TestCase):
    """The hook is global, so the engine runs in every project.

    No file means the project has never been asked. An empty file means it was
    asked and said no. The difference is the whole point: the guard asks once.
    """

    def rules_file(self, content):
        """A guard-rules.json in a throwaway project directory."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        path = Path(tmp) / "guard-rules.json"
        path.write_text(content)
        return path

    def test_missing_rules_file_asks_to_create_them(self):
        """Blocks once so the agent can put the question to the user."""
        missing = Path(tempfile.mkdtemp()) / "guard-rules.json"
        result = run_guard("npm run build", rules=missing)
        self.assertEqual(result.returncode, 2)
        self.assertIn("guard-rules.json", result.stderr)
        self.assertIn("ask", result.stderr.lower())

    def test_empty_rules_file_runs_everything(self):
        """An empty file is an answer: this project doesn't want guarding."""
        result = run_guard("npm install", rules=self.rules_file("{}"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_comment_only_stub_runs_everything(self):
        """The stub the agent writes when the answer is no."""
        stub = self.rules_file('{"_comment": "No guard rules. Hook: ~/.claude/settings.json"}')
        result = run_guard("npm install", rules=stub)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_rules_without_a_rewrite_rule_need_no_rewrite_to(self):
        """Deny-only rules are legitimate -- nothing is being rewritten."""
        deny_only = self.rules_file(
            '{"deny": {"pattern": "npm\\\\s+install\\\\b", "reason": "no"}}'
        )
        result = run_guard("npm install", rules=deny_only)
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")

    def test_malformed_rules_file_blocks(self):
        """Opted in with a broken config -- silently running unguarded is the bug."""
        bad = self.rules_file("{ not json")
        result = run_guard("npm install", rules=bad)
        self.assertEqual(result.returncode, 2)
        self.assertIn("guard-rules.json", result.stderr)

    def test_rewrite_rule_without_rewrite_to_blocks(self):
        """A rewrite rule with nothing to rewrite into cannot be honoured."""
        bad = self.rules_file('{"rewrite": {"pattern": "npm\\\\b", "reason": "x"}}')
        result = run_guard("npm run build", rules=bad)
        self.assertEqual(result.returncode, 2)
        self.assertIn("rewrite_to", result.stderr)

    def test_no_project_dir_exits_clean(self):
        """Not running under Claude Code at all -- there is no project to guard."""
        result = run_guard("npm install", rules=None)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_project_dir_is_used_to_find_the_rules(self):
        stub = self.rules_file("{}")
        result = run_guard("npm install", rules=None, project_dir=stub.parent)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


class TestTextIsNotCode(unittest.TestCase):
    """Text being written INTO a file is data, not a command to intercept.

    Regression: a heredoc writing ASTRO_MIGRATION.md contained the English
    phrase "PR #30 (astro 5->7)". CMD_POS treats "(" as a command position, so
    the parenthetical matched the rewrite pattern, and the whole script --
    including the `cat >` that wrote the file -- was replaced by the Docker
    command. The file was never written and the output looked like a clean build.
    """

    def test_heredoc_body_mentioning_astro_is_untouched(self):
        command = (
            "cat > NOTES.md <<'MD'\n"
            "This is exactly how PR #30 (astro 5->7) sat open looking green.\n"
            "MD\n"
            "git status --short"
        )
        self.assertIsNone(decide(command))

    def test_parenthetical_before_a_tool_name_is_untouched(self):
        self.assertIsNone(decide("echo 'upgrade (astro 5->7) is pending'"))

    def test_heredoc_body_mentioning_npm_install_is_untouched(self):
        command = "cat > NOTES.md <<'MD'\nRun npm install to set up.\nMD"
        self.assertIsNone(decide(command))

    def test_comment_mentioning_npm_is_untouched(self):
        self.assertIsNone(decide("git status  # not npm run build"))


class TestCompoundCommands(unittest.TestCase):
    """Rewrite only the offending segment; never discard its neighbours."""

    def test_compound_preserves_neighbours(self):
        out = decide("cd /app && npm run build && git status --short")
        rewritten = out["updatedInput"]["command"]
        self.assertIn("cd /app", rewritten)
        self.assertIn("docker compose up --build", rewritten)
        self.assertIn("git status --short", rewritten)

    def test_compound_containing_an_install_is_denied_entirely(self):
        """Rewriting the build half while dropping the install is the same bug."""
        out = decide("npm install lodash && npm run build")
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("package.json", out["permissionDecisionReason"])

    def test_a_following_segment_gets_a_readiness_wait(self):
        """`&&` means "after that finished", but `-d` returns immediately.

        Without a wait, the next segment races a server that is not up yet.
        """
        out = decide("npm run build && python -m unittest tests.test_site")
        rewritten = out["updatedInput"]["command"]
        self.assertIn("localhost:4444", rewritten)
        self.assertIn("python -m unittest tests.test_site", rewritten)

    def test_bare_command_needs_no_wait(self):
        """Nothing follows it, so the plain detached form stays."""
        self.assertEqual(decide("npm run build")["updatedInput"]["command"], DOCKER_UP)


class TestTheQuestionIsAnswerable(unittest.TestCase):
    """The guard blocks so I can be *asked* something. Test what I'm asked.

    Every other test here covers the engine -- what gets rewritten, what gets
    denied. None covered the one piece of output a human reads, and it drifted
    into jargon unnoticed: it opened by announcing that Bash was blocked and
    went on about permission prompts and which JSON keys to write. What came
    back out of the agent was a paragraph I could not answer.

    So the ASK text is split in two. `ASK_USER` is the question, worded to be
    put to me verbatim. `ASK_AGENT` is the mechanical half -- which file, which
    keys -- which is the agent's problem and which I should never see. These
    tests hold that line, because prose drifts and a check does not.
    """

    # Words that mean something to whoever wrote the guard and nothing to the
    # person being asked. Any of these in the question is the drift coming back.
    JARGON = [
        "pretooluse",
        "stdin",
        "stdout",
        "exit code",
        "json",
        "guard-rules",
        "hook",
        "regex",
        "llm",
        "permission prompt",
        "bash",
        "block",
    ]

    @staticmethod
    def guard_module():
        import importlib.util

        spec = importlib.util.spec_from_file_location("command_guard", GUARD)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def question(self):
        return self.guard_module().ASK_USER

    def test_the_question_is_short(self):
        """If I have to read a paragraph to answer yes or no, it failed."""
        words = len(self.question().split())
        self.assertLessEqual(
            words,
            45,
            f"the question is {words} words. Cut it to 45 or fewer -- what it "
            f"does, one example, yes or no.",
        )

    def test_the_question_ends_by_asking(self):
        """A description is not a question. It has to be answerable."""
        self.assertRegex(
            self.question().strip().lower(),
            r"yes or no\?$",
            "the question must end with 'Yes or no?' -- that is the whole "
            "point of stopping to ask",
        )

    def test_the_question_carries_a_concrete_example(self):
        """`landing-page` rewrites npm to compose. Naming it beats defining it."""
        question = self.question()
        self.assertIn("landing-page", question)
        self.assertIn("npm", question)
        self.assertIn("docker compose", question)

    def test_the_question_has_no_jargon(self):
        found = [word for word in self.JARGON if word in self.question().lower()]
        self.assertEqual(
            found,
            [],
            f"the question uses words only the guard's author understands: "
            f"{found}. Those belong in ASK_AGENT.",
        )

    def test_the_mechanics_are_kept_away_from_the_question(self):
        """The agent still needs the file path and the stub -- separately."""
        module = self.guard_module()
        self.assertIn("{path}", module.ASK_AGENT)
        self.assertIn("{stub}", module.ASK_AGENT)
        for placeholder in ("{path}", "{stub}"):
            self.assertNotIn(
                placeholder,
                module.ASK_USER,
                f"{placeholder} is mechanics -- keep it out of the question",
            )

    def test_blocking_output_still_carries_both_halves(self):
        """Split for readability, not so half of it goes missing."""
        missing = Path(tempfile.mkdtemp()) / "guard-rules.json"
        result = run_guard("npm run build", rules=missing)
        self.assertEqual(result.returncode, 2)
        self.assertIn("landing-page", result.stderr)
        self.assertIn("Yes or no?", result.stderr)
        self.assertIn(str(missing), result.stderr)
        self.assertIn("_comment", result.stderr)

    def test_the_agent_is_told_not_to_paraphrase(self):
        """Left free to summarise, an agent rebuilds the paragraph I complained about."""
        module = self.guard_module()
        self.assertIn("verbatim", module.ASK_AGENT.lower())


if __name__ == "__main__":
    unittest.main()
