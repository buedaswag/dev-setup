"""zsh/tools.zsh: PATH and tool environment, one block per tool.

It holds machine-specific install paths, so .zshrc sources it on its own line: on a
machine where those paths differ, comment that one line out. The python venv helpers
are not machine-specific and are sourced from .zshrc directly.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ZSHRC = REPO_ROOT / "zsh" / ".zshrc"
TOOLS = REPO_ROOT / "zsh" / "tools.zsh"


class ToolsTest(unittest.TestCase):
    def test_zshrc_sources_tools_and_venvs(self):
        zshrc = ZSHRC.read_text()
        self.assertIn("source ~/ws/dev-setup/zsh/tools.zsh", zshrc)
        self.assertIn("source ~/ws/dev-setup/zsh/py-venvs.sh", zshrc)

    def test_paths_zsh_is_gone(self):
        self.assertFalse((REPO_ROOT / "zsh" / "paths.zsh").exists())
        self.assertNotIn("paths.zsh", ZSHRC.read_text())

    def test_tools_holds_each_tool(self):
        tools = TOOLS.read_text()
        for marker in (
            "Visual Studio Code.app",
            "Cursor.app",
            "/Library/PostgreSQL/",
            "openssl",
            ".poetry/bin",
            "google-cloud-sdk",
        ):
            self.assertIn(marker, tools, marker)

    def test_venvs_not_sourced_from_tools(self):
        self.assertNotIn("py-venvs.sh", TOOLS.read_text())

    def test_db_proxy_is_purged(self):
        self.assertFalse((REPO_ROOT / "zsh" / "db-proxy.zsh").exists())
        self.assertNotIn("db-proxy", ZSHRC.read_text())


if __name__ == "__main__":
    unittest.main()
