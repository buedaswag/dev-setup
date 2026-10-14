"""zsh/db-proxy.zsh: shortcuts for the corporate laptop's local Kerberos proxy (myproxy).

`edge` starts Edge through myproxy; `krenew` renews the ticket and restarts myproxy via
their LaunchAgents. The agents are labelled com.<mac user>.*, so the labels come from
$USER -- this repo is public and the account name stays out of it.
"""

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PROXY_FILE = REPO_ROOT / "zsh" / "db-proxy.zsh"
ZSHRC = REPO_ROOT / "zsh" / ".zshrc"


def alias_in(name, user="someone"):
    result = subprocess.run(
        ["zsh", "-f", "-c", f'source "{DB_PROXY_FILE}"; alias {name}'],
        env={"USER": user, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    return result


class DbProxyTest(unittest.TestCase):
    def test_zshrc_sources_it(self):
        self.assertIn("source ~/ws/dev-setup/zsh/db-proxy.zsh", ZSHRC.read_text())

    def test_edge_goes_through_myproxy(self):
        result = alias_in("edge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--proxy-server="http://127.0.0.1:9080"', result.stdout)

    def test_krenew_targets_this_users_agents(self):
        result = alias_in("krenew", user="someone")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("com.someone.krb-renew", result.stdout)
        self.assertIn("com.someone.myproxy", result.stdout)


if __name__ == "__main__":
    unittest.main()
