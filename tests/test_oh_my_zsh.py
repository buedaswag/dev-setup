"""zsh/oh-my-zsh.zsh: apply omz settings only for the parts that are installed.

On a fresh machine omz, Powerlevel10k and the two custom plugins arrive one at a
time, if at all. Each missing piece used to cost something at every shell start: no
omz fails the source outright, a missing theme or plugin makes omz print
"[oh-my-zsh] ... not found" above the prompt. The file should ask only for what is
on disk, and say nothing about what is not.

These tests source the file under a throwaway $HOME with a stub `oh-my-zsh.sh` that
reports what it was asked to load, so they never touch a real omz install.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OMZ_FILE = REPO_ROOT / "zsh" / "oh-my-zsh.zsh"

# Stands in for omz's loader: records what the config asked it for.
STUB_LOADER = 'print -r -- "loaded theme=$ZSH_THEME plugins=${(j:,:)plugins}"\n'


def source_in(home):
    return subprocess.run(
        ["zsh", "-f", "-c", f'source "{OMZ_FILE}"; print -r -- "rc=$?"'],
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


class OhMyZshTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.zsh = self.home / ".oh-my-zsh"

    def tearDown(self):
        self._tmp.cleanup()

    def install_omz(self):
        self.zsh.mkdir()
        (self.zsh / "oh-my-zsh.sh").write_text(STUB_LOADER)
        (self.zsh / "plugins" / "git").mkdir(parents=True)

    def install_custom(self, kind, name):
        (self.zsh / "custom" / kind / name).mkdir(parents=True)

    def test_no_omz_is_silent_and_loads_nothing(self):
        result = source_in(self.home)
        self.assertEqual(result.stdout, "rc=0\n")
        self.assertEqual(result.stderr, "")

    def test_empty_omz_dir_is_not_an_install(self):
        # A half-finished clone, or a leftover dir after uninstall.
        self.zsh.mkdir()
        result = source_in(self.home)
        self.assertEqual(result.stdout, "rc=0\n")
        self.assertEqual(result.stderr, "")

    def test_bare_omz_gets_default_theme_and_only_bundled_plugins(self):
        self.install_omz()
        result = source_in(self.home)
        self.assertEqual(result.stdout, "loaded theme=robbyrussell plugins=git\nrc=0\n")
        self.assertEqual(result.stderr, "")

    def test_everything_installed_loads_everything(self):
        self.install_omz()
        self.install_custom("themes", "powerlevel10k")
        self.install_custom("plugins", "zsh-syntax-highlighting")
        self.install_custom("plugins", "zsh-autosuggestions")
        result = source_in(self.home)
        self.assertEqual(
            result.stdout,
            "loaded theme=powerlevel10k/powerlevel10k "
            "plugins=git,zsh-syntax-highlighting,zsh-autosuggestions\nrc=0\n",
        )
        self.assertEqual(result.stderr, "")

    def test_p10k_config_is_skipped_without_the_theme(self):
        # ~/.p10k.zsh survives a reinstall; without p10k itself it only makes noise.
        self.install_omz()
        (self.home / ".p10k.zsh").write_text('print -r -- "p10k config sourced"\n')
        result = source_in(self.home)
        self.assertNotIn("p10k config sourced", result.stdout)


if __name__ == "__main__":
    unittest.main()
