"""CI's unit tests job: the tests shell out to zsh, which ubuntu-latest doesn't ship.

Without it 14 tests error with `No such file or directory: 'zsh'` and the job has been
red since the first zsh test landed -- a red that means nothing stops meaning anything.
"""

import unittest
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "security.yml"


class CiWorkflowTest(unittest.TestCase):
    def test_tests_job_installs_zsh_before_running_tests(self):
        steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["tests"]["steps"]
        runs = [s.get("run", "") for s in steps]
        install = next(i for i, r in enumerate(runs) if "apt-get install" in r and "zsh" in r)
        tests = next(i for i, r in enumerate(runs) if "unittest" in r)
        self.assertLess(install, tests)


if __name__ == "__main__":
    unittest.main()
