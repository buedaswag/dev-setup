"""scripts/vscode_merge.py: add vscode/ to a machine that already has VS Code settings.

Linking vscode/ into place replaces whatever is there, which is wrong on a machine
with settings of its own -- a work laptop, say. VS Code has no way for one settings
file to include another, so the merge has to be done to the file itself: this
repo's keys are written over the local file, and every other local key is kept.

Everything runs against a throwaway user directory, never the real one.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import vscode_merge
from scripts.vscode_merge import merge_into, parse_jsonc

REPO_SETTINGS = {
    "[markdown]": {"files.trimTrailingWhitespace": False},
    "files.trimTrailingWhitespace": True,
}
REPO_KEYBINDINGS = [
    {"key": "cmd+t", "command": "workbench.action.terminal.new", "when": "!terminal.active"}
]


class ParseJsoncTest(unittest.TestCase):
    def test_comments_and_trailing_commas_are_allowed(self):
        # VS Code writes and accepts both in its own settings files.
        text = '{\n  // line\n  "a": 1, /* block */\n  "b": [1, 2,],\n}\n'
        self.assertEqual(parse_jsonc(text), {"a": 1, "b": [1, 2]})

    def test_comment_markers_inside_strings_are_text(self):
        self.assertEqual(
            parse_jsonc('{"proxy": "http://host:8080", "glob": "**/*.py,}"}'),
            {"proxy": "http://host:8080", "glob": "**/*.py,}"},
        )

    def test_a_quote_inside_a_comment_does_not_open_a_string(self):
        # If it did, the proxy URL's "//" would be read as a comment and cut off.
        text = '{\n  // the "old proxy\n  "proxy": "http://host:8080" /* 3" */\n}'
        self.assertEqual(parse_jsonc(text), {"proxy": "http://host:8080"})

    def test_an_escaped_quote_does_not_close_a_string(self):
        self.assertEqual(parse_jsonc(r'{"a": "say \"hi\" // not a comment"}'),
                         {"a": 'say "hi" // not a comment'})


class MergeIntoTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.repo = root / "repo"
        self.user = root / "User"
        self.repo.mkdir()
        self.user.mkdir()
        (self.repo / "settings.json").write_text(json.dumps(REPO_SETTINGS))
        (self.repo / "keybindings.json").write_text(json.dumps(REPO_KEYBINDINGS))

    def tearDown(self):
        self._tmp.cleanup()

    def merge(self):
        return merge_into(self.user, self.repo)

    def settings(self):
        return json.loads((self.user / "settings.json").read_text())

    def keybindings(self):
        return json.loads((self.user / "keybindings.json").read_text())

    def test_local_settings_are_kept_alongside_the_repo_ones(self):
        (self.user / "settings.json").write_text('{"http.proxy": "http://bank:8080"}')
        self.merge()
        self.assertEqual(self.settings(), {"http.proxy": "http://bank:8080", **REPO_SETTINGS})

    def test_the_repo_wins_a_key_both_define(self):
        (self.user / "settings.json").write_text('{"files.trimTrailingWhitespace": false}')
        self.merge()
        self.assertIs(self.settings()["files.trimTrailingWhitespace"], True)

    def test_language_blocks_are_merged_key_by_key(self):
        # Replacing the whole "[markdown]" block would drop the local wordWrap.
        (self.user / "settings.json").write_text('{"[markdown]": {"editor.wordWrap": "on"}}')
        self.merge()
        self.assertEqual(
            self.settings()["[markdown]"],
            {"editor.wordWrap": "on", "files.trimTrailingWhitespace": False},
        )

    def test_local_keybindings_are_kept_and_the_repo_ones_added(self):
        local = [{"key": "cmd+k", "command": "something.local"}]
        (self.user / "keybindings.json").write_text(json.dumps(local))
        self.merge()
        self.assertEqual(self.keybindings(), local + REPO_KEYBINDINGS)

    def test_a_machine_with_no_files_gets_the_repo_ones(self):
        self.merge()
        self.assertEqual(self.settings(), REPO_SETTINGS)
        self.assertEqual(self.keybindings(), REPO_KEYBINDINGS)

    def test_running_twice_changes_nothing(self):
        (self.user / "settings.json").write_text('{"http.proxy": "http://bank:8080"}')
        self.merge()
        first = [(self.user / name).read_text() for name in ("settings.json", "keybindings.json")]
        self.assertEqual(self.merge(), [])
        second = [(self.user / name).read_text() for name in ("settings.json", "keybindings.json")]
        self.assertEqual(first, second)
        self.assertEqual(len(self.keybindings()), 1)

    def test_the_file_as_it_was_is_kept_beside_the_new_one(self):
        # The rewrite drops comments, so the original has to stay recoverable.
        original = '{\n  // set by IT\n  "http.proxy": "http://bank:8080"\n}\n'
        (self.user / "settings.json").write_text(original)
        self.merge()
        self.assertEqual((self.user / "settings.json.bak").read_text(), original)

    def test_a_later_run_does_not_overwrite_the_first_backup(self):
        # Otherwise the second rewrite would replace the true original with the first merge.
        original = '{\n  // set by IT\n  "http.proxy": "http://bank:8080"\n}\n'
        (self.user / "settings.json").write_text(original)
        self.merge()
        after_first = (self.user / "settings.json").read_text()
        (self.repo / "settings.json").write_text(json.dumps({**REPO_SETTINGS, "new.key": 1}))
        self.merge()
        self.assertEqual((self.user / "settings.json.bak").read_text(), original)
        self.assertEqual((self.user / "settings.json.bak2").read_text(), after_first)

    def test_a_broken_local_file_stops_the_run_before_anything_is_written(self):
        # keybindings.json is the second file: settings.json must not be half-deployed.
        settings = '{"http.proxy": "http://bank:8080"}'
        (self.user / "settings.json").write_text(settings)
        (self.user / "keybindings.json").write_text('[{"key": "cmd+k"')
        with self.assertRaises(ValueError):
            self.merge()
        self.assertEqual((self.user / "settings.json").read_text(), settings)
        self.assertEqual(sorted(p.name for p in self.user.iterdir()),
                         ["keybindings.json", "settings.json"])

    def test_a_local_file_of_the_wrong_shape_is_refused(self):
        (self.user / "settings.json").write_text('["not", "settings"]')
        with self.assertRaises(ValueError):
            self.merge()
        self.assertEqual((self.user / "settings.json").read_text(), '["not", "settings"]')

    def test_a_file_holding_only_a_comment_counts_as_empty(self):
        # What VS Code's keybindings.json looks like before anything is bound.
        (self.user / "keybindings.json").write_text("// Place your key bindings in this file\n")
        self.merge()
        self.assertEqual(self.keybindings(), REPO_KEYBINDINGS)

    def test_text_outside_ascii_survives_as_written(self):
        local = '{"window.title": "Lisboa — São Bento"}'
        (self.user / "settings.json").write_bytes(local.encode("utf-8"))
        self.merge()
        written = (self.user / "settings.json").read_bytes().decode("utf-8")
        self.assertIn('"Lisboa — São Bento"', written)

    def test_a_byte_order_mark_is_read_past_and_kept_in_the_backup(self):
        # Windows editors leave one; VS Code reads past it, and so must this.
        original = b"\xef\xbb\xbf" + b'{"http.proxy": "http://bank:8080"}'
        (self.user / "settings.json").write_bytes(original)
        self.merge()
        self.assertEqual(self.settings()["http.proxy"], "http://bank:8080")
        self.assertEqual((self.user / "settings.json.bak").read_bytes(), original)

    def test_the_file_keeps_its_permissions(self):
        target = self.user / "settings.json"
        target.write_text('{"http.proxy": "http://bank:8080"}')
        target.chmod(0o600)
        self.merge()
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_a_read_only_file_is_refused(self):
        # Renaming over it would succeed, and undo whoever locked it.
        target = self.user / "settings.json"
        target.write_text('{"http.proxy": "http://bank:8080"}')
        target.chmod(0o444)
        with self.assertRaises(ValueError):
            self.merge()
        self.assertEqual(target.read_text(), '{"http.proxy": "http://bank:8080"}')
        self.assertFalse((self.user / "keybindings.json").exists())

    def test_profiles_are_pointed_out_because_they_are_not_merged(self):
        # A profile has its own settings.json; merging the default one changes nothing in it.
        (self.user / "profiles" / "-1a2b3c").mkdir(parents=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(vscode_merge, "REPO_DIR", self.repo):
            self.assertEqual(vscode_merge.main(["vscode_merge.py", str(self.user)]), 0)
        self.assertIn(str(self.user / "profiles" / "-1a2b3c"), out.getvalue())

    def test_a_file_linked_to_the_repo_is_left_alone(self):
        # Merging through the link would write the repo's own file.
        (self.user / "settings.json").symlink_to(self.repo / "settings.json")
        self.merge()
        self.assertTrue((self.user / "settings.json").is_symlink())
        self.assertEqual(json.loads((self.repo / "settings.json").read_text()), REPO_SETTINGS)
        self.assertFalse((self.user / "settings.json.bak").exists())


if __name__ == "__main__":
    unittest.main()
