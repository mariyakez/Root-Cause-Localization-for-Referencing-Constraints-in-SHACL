"""The interactive report's JavaScript is not otherwise exercised by the suite.

tools/check_report_template.py runs the shipped template's own functions under
node and checks the two invariants that were broken once before:

  1. the root-cause breakdown says "direct" exactly when a leaf's reference
     chain is empty;
  2. the headline counters and the breakdown follow the active filters.

This wrapper puts that check in the suite so the invariants cannot regress
unnoticed. It skips when node is unavailable, since node is not a dependency of
the tool itself.
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check_report_template.py"

# One fixture per shape of report the invariants can break on: a deep chain, a
# diamond, and a report mixing direct with referenced failures.
FIXTURES = [
    "all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl",
    "all_test_cases/sh_node_cases/tc5_diamond.ttl",
    "all_test_cases/mixed_constraint_cases/tc26_mixed_direct_plus_diamond.ttl",
]


@unittest.skipIf(shutil.which("node") is None, "node is not installed")
class ReportTemplateInvariantTests(unittest.TestCase):
    def test_shipped_template_holds_its_summary_invariants(self):
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture):
                result = subprocess.run(
                    [sys.executable, str(CHECKER), str(ROOT / fixture)],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"{fixture}\n{result.stdout}\n{result.stderr}",
                )
                self.assertNotIn("FAIL", result.stdout)


if __name__ == "__main__":
    unittest.main()
