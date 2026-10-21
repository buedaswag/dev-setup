"""vscode/: the VS Code user settings and keybindings a new machine starts with.

VS Code reads these through symlinks from its user directory, so what is in this
repo is what the editor runs. Both files are kept as plain JSON -- no comments, no
trailing commas -- so they can be checked here without a JSONC parser.

Two things are pinned. Saving a file tidies its whitespace: trailing spaces go, and
the file ends in exactly one newline. And Cmd+T belongs to the terminal, which means
taking it from its default of "Go to Symbol in Workspace".
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = REPO_ROOT / "vscode" / "settings.json"
KEYBINDINGS_FILE = REPO_ROOT / "vscode" / "keybindings.json"


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.settings = json.loads(SETTINGS_FILE.read_text())

    def test_save_strips_trailing_whitespace(self):
        self.assertIs(self.settings["files.trimTrailingWhitespace"], True)

    def test_save_ends_the_file_with_a_newline(self):
        self.assertIs(self.settings["files.insertFinalNewline"], True)

    def test_save_leaves_only_one_newline_at_the_end(self):
        self.assertIs(self.settings["files.trimFinalNewlines"], True)

    def test_markdown_keeps_its_trailing_spaces(self):
        # Two trailing spaces are a line break in Markdown, not stray whitespace.
        self.assertIs(self.settings["[markdown]"]["files.trimTrailingWhitespace"], False)


class KeybindingsTest(unittest.TestCase):
    def setUp(self):
        self.bindings = json.loads(KEYBINDINGS_FILE.read_text())

    def cmd_t(self):
        return {b["when"]: b["command"] for b in self.bindings if b["key"] == "cmd+t"}

    def test_cmd_t_opens_a_terminal_when_there_is_none(self):
        self.assertEqual(self.cmd_t()["!terminal.active"], "workbench.action.terminal.new")

    def test_cmd_t_toggles_the_terminal_when_there_is_one(self):
        self.assertEqual(
            self.cmd_t()["terminal.active"], "workbench.action.terminal.toggleTerminal"
        )

    def test_cmd_t_is_never_left_to_the_default(self):
        # A cmd+t binding with no `when` would shadow both of the above.
        self.assertEqual(set(self.cmd_t()), {"terminal.active", "!terminal.active"})


if __name__ == "__main__":
    unittest.main()
