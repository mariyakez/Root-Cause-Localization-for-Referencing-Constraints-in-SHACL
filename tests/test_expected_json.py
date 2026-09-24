"""
Content assertions for the fixtures that previously had none.

Before this file, twenty-five of the fifty-three fixtures were exercised only
by test_additional_case_groups_run_in_summary_mode, which asserts that the
command produces a summary or reports the data as valid. That checks the tool
does not crash; it does not check what the explanation says. Each of those
fixtures now has a stored expected JSON document under expected_json/, compared
here field by field.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from expected_json_support import (  # noqa: E402
    MULTIPLE_MESSAGES,
    SNAPSHOT_FIXTURES,
    canonical,
    messages,
    run_json,
    snapshot_path,
)


class ExpectedJsonTests(unittest.TestCase):
    def test_json_output_matches_stored_expectation(self):
        for fixture in SNAPSHOT_FIXTURES:
            with self.subTest(fixture=fixture):
                path = snapshot_path(fixture)
                self.assertTrue(
                    path.exists(),
                    f"missing snapshot {path}; run tools/regenerate_expected_json.py",
                )
                expected = json.loads(path.read_text(encoding="utf-8"))
                actual = canonical(run_json(fixture))
                self.assertEqual(expected, actual)

    def test_multiple_message_fixtures_emit_every_declared_message(self):
        """A shape with several sh:message values yields a result carrying all
        of them; the explanation must show every one, in a fixed order, so the
        output does not depend on which triple rdflib yields first."""
        for fixture in SNAPSHOT_FIXTURES:
            stem = Path(fixture).stem
            if stem not in MULTIPLE_MESSAGES:
                continue
            with self.subTest(fixture=fixture):
                for _ in range(3):
                    self.assertEqual(messages(run_json(fixture)), [MULTIPLE_MESSAGES[stem]])


if __name__ == "__main__":
    unittest.main()
