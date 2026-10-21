"""zsh/.zshrc installs as a one-line stub in ~/.zshrc that sources the repo copy.

Not `cp` (edits here need re-copying to take effect) and not a symlink (installers that
append to ~/.zshrc -- nvm, conda, pyenv -- would write machine-specific lines into this
public repo). The stub keeps repo edits live and gives installers a file of their own.
The README and the header of .zshrc both say how to install; they have to agree.
"""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
ZSHRC = REPO_ROOT / "zsh" / ".zshrc"

STUB = "echo 'source ~/ws/dev-setup/zsh/.zshrc' > ~/.zshrc"


class ZshrcInstallTest(unittest.TestCase):
    def test_readme_installs_the_stub(self):
        self.assertIn(STUB, README.read_text())

    def test_zshrc_header_installs_the_stub(self):
        self.assertIn(STUB, ZSHRC.read_text())

    def test_nothing_says_to_copy_it(self):
        for f in (README, ZSHRC):
            self.assertNotIn("cp ~/ws/dev-setup/zsh/.zshrc", f.read_text(), f.name)


if __name__ == "__main__":
    unittest.main()
