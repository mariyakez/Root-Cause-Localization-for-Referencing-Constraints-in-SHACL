#!/usr/bin/env python3
"""Check the two invariants of the HTML report's summary panel.

Requires: Node.js (`node`) on PATH. The check skips itself, reporting success,
when node is absent, so it is safe to run anywhere.

    python3 tools/check_report_template.py [fixture.ttl]

The interactive report is a single template whose JavaScript no Python test
exercises, so these two properties are easy to break unnoticed. Both were
broken once:

1. "How reached" in the root-cause breakdown must read "direct" exactly when
   the leaf's reference chain is empty. A route made only of node-level
   sh:node references contributes no reference path, and the breakdown used to
   call every such leaf "direct" while the headline counted it under sh:node.

2. The headline counters, the issue clusters and the breakdown must follow the
   active filters. They used to be computed once at startup from the whole
   report, so filtering the tree left them unchanged.

The check runs the template's own functions under node, so it tests the
shipped code rather than a copy of it. It is skipped when node is absent.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PROJECT_ROOT / "shacl_explainer" / "report_template.html"
DEFAULT_FIXTURE = PROJECT_ROOT / "all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl"

# Functions pulled out of the template and run directly.
FUNCTIONS = [
    "referenceStep",
    "collectLeafEntries",
    "countMapEntries",
    "formatHowReached",
    "dataLeafMatches",
    "countMatchingEntries",
    "visibleEntries",
    "countDirect",
    "rootCauseBreakdownRows",
]

HARNESS = """
const compInfo = (c) => ({ short: String(c).replace("sh:", "").replace("ConstraintComponent", ""), cls: "x" });
const leafHeaderText = (n, info) => info.short + " on " + (n.path || "path");
let activeFilters = { component: "all", path: "all", referencePath: "all", shape: "all", kind: "all" };
let ALL_LEAF_ENTRIES = collectLeafEntries(REPORT_DATA);

const failures = [];

// 1. "direct" means no reference chain, and nothing else.
for (const entry of ALL_LEAF_ENTRIES) {
  const how = formatHowReached(entry.ctx, entry.node);
  const nested = (entry.node.refChain || []).length > 0;
  if (nested === (how === "direct")) {
    failures.push(`how_reached "${how}" contradicts refChain ${JSON.stringify(entry.node.refChain)}`);
  }
}

// 2. A filter that hides leaves must move the counters and the breakdown.
const before = { leaves: visibleEntries().length, rows: rootCauseBreakdownRows().length };
const narrowing = ALL_LEAF_ENTRIES.find(entry => entry.node.path);
if (narrowing && before.leaves > 1) {
  activeFilters.path = narrowing.node.path;
  const after = { leaves: visibleEntries().length, rows: rootCauseBreakdownRows().length };
  if (after.leaves >= before.leaves) failures.push(`path filter did not reduce the visible leaves (${before.leaves} -> ${after.leaves})`);
  if (after.rows >= before.rows) failures.push(`path filter did not reduce the breakdown rows (${before.rows} -> ${after.rows})`);
  activeFilters.path = "all";
}

console.log(JSON.stringify({ leaves: before.leaves, failures }));
"""


def extract(name: str, source: str) -> str:
    match = re.search(r"\nfunction " + name + r"\([\s\S]*?\n\}\n", source)
    if match is None:
        raise SystemExit(f"function {name}() is no longer in {TEMPLATE.name}; update this script")
    return match.group(0)


def report_data(fixture: Path) -> str:
    """Generate a report for one fixture and return its embedded REPORT_DATA."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "report.html"
        subprocess.run(
            [sys.executable, "-m", "shacl_explainer.cli", str(fixture), str(fixture),
             "--format", "html", "--output", str(out)],
            cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
        )
        html = out.read_text(encoding="utf-8")
    match = re.search(r"const REPORT_DATA = (\[[\s\S]*?\]);\nconst SHAPE_CATALOG", html)
    if match is None:
        raise SystemExit("could not find REPORT_DATA in the generated report")
    return match.group(1)


def main() -> int:
    if shutil.which("node") is None:
        print("node not found; skipping the report-template check")
        return 0

    fixture = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FIXTURE
    source = TEMPLATE.read_text(encoding="utf-8")
    script = "\n".join([
        f"const REPORT_DATA = {report_data(fixture)};",
        *(extract(name, source) for name in FUNCTIONS),
        HARNESS,
    ])

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "check.js"
        path.write_text(script, encoding="utf-8")
        result = subprocess.run(["node", str(path)], capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stderr.strip())
        return 1

    outcome = json.loads(result.stdout)
    for failure in outcome["failures"]:
        print(f"FAIL  {failure}")
    if outcome["failures"]:
        return 1
    print(f"ok  {fixture.name}: {outcome['leaves']} leaves, "
          "how-reached agrees with the counters, filters move both")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
