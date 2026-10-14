"""proxy-hell/vault.sh: password-encrypt a file so only its ciphertext is committed.

This repo is public. Notes that name internal hosts and accounts live here as FILE.enc,
the plaintext FILE is gitignored, and the corporate laptop pulls and decrypts with the
same script and nothing installed: macOS ships LibreSSL as /usr/bin/openssl, so a file
encrypted with Homebrew's OpenSSL must decrypt with that one.

The tests pass the password through VAULT_PASSWORD; at a terminal openssl prompts for it.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT = REPO_ROOT / "proxy-hell" / "vault.sh"
SYSTEM_OPENSSL = Path("/usr/bin/openssl")

PLAINTEXT = "kinit --keychain someone@CORP.EXAMPLE.COM\n"


class VaultTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.plain = self.dir / "notes.md"
        self.enc = self.dir / "notes.md.enc"
        self.plain.write_text(PLAINTEXT)

    def tearDown(self):
        self._tmp.cleanup()

    def vault(self, *args, password="correct horse", path=None):
        env = {**os.environ, "VAULT_PASSWORD": password}
        if path:
            env["PATH"] = path
        return subprocess.run(
            [str(VAULT), *args], env=env, capture_output=True, text=True
        )

    def test_encrypt_writes_ciphertext_next_to_the_file(self):
        result = self.vault("encrypt", str(self.plain))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("CORP.EXAMPLE.COM", self.enc.read_text())

    def test_decrypt_restores_the_plaintext(self):
        self.vault("encrypt", str(self.plain))
        self.plain.unlink()
        result = self.vault("decrypt", str(self.enc))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.plain.read_text(), PLAINTEXT)

    def test_wrong_password_fails_and_writes_nothing(self):
        self.vault("encrypt", str(self.plain))
        self.plain.unlink()
        result = self.vault("decrypt", str(self.enc), password="wrong")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.plain.exists())

    def test_decrypt_refuses_to_overwrite_local_edits(self):
        self.vault("encrypt", str(self.plain))
        self.plain.write_text("edited after the last encrypt\n")
        result = self.vault("decrypt", str(self.enc))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs", result.stderr)
        self.assertEqual(self.plain.read_text(), "edited after the last encrypt\n")

    @unittest.skipUnless(SYSTEM_OPENSSL.exists(), "no macOS LibreSSL here")
    def test_macos_builtin_openssl_decrypts_it(self):
        self.vault("encrypt", str(self.plain))
        self.plain.unlink()
        result = self.vault("decrypt", str(self.enc), path="/usr/bin:/bin")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.plain.read_text(), PLAINTEXT)


class PlaintextIsIgnoredTest(unittest.TestCase):
    def test_proxy_hell_plaintext_is_gitignored(self):
        result = subprocess.run(
            ["git", "check-ignore", "-q", "proxy-hell/debug.md"], cwd=REPO_ROOT
        )
        self.assertEqual(result.returncode, 0, "proxy-hell/debug.md is not gitignored")


if __name__ == "__main__":
    unittest.main()
