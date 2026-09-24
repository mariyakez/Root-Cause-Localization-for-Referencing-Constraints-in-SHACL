#!/usr/bin/env python3
"""Reconstruct every fixture from a real validator's report and diff it against
pySHACL's own explanation.

This is the check behind RQ2 in Chapter 5. For each fixture it runs Apache Jena
and TopBraid over the same file, feeds each report back through --report, and
compares the resulting explanation with the one the tool produces natively.

Three levels are compared, taken from the JSON output, so that a weaker repair
hint is not reported as a different failure:

  failures  each leaf as (focus node, path, component, value)
  hints     the repair hint attached to each leaf
  chains    the reference chain and alternate chains attached to each leaf

Root and sibling order is not compared, since the report fixtures are unordered
sets; blank-node labels are normalised because rdflib mints them afresh on every
parse. Leaf messages are excluded: each validator words its own.

Requires: both external validators on PATH, neither of which ships with this
repository. Verified against Apache Jena SHACL 6.2.0 and TopBraid SHACL 1.5.0:
    shacl              (Apache Jena, `shacl validate`)
    shaclvalidate.sh   (TopBraid SHACL)

    python3 tools/compare_external_validators.py [--only sh_node_cases] [-v]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BNODE = re.compile(r"<?_?:?N?[0-9a-f]{16,}>?")

ENGINES = {
    "jena":     lambda f: ["shacl", "validate", "--shapes", str(f), "--data", str(f)],
    "topbraid": lambda f: ["shaclvalidate.sh", "-datafile", str(f), "-shapesfile", str(f)],
}


def explain(data, shapes, report=None):
    """The tool's JSON explanation, or None when it reports the data as valid."""
    cmd = [sys.executable, "-m", "shacl_explainer.cli", str(data), str(shapes), "--format", "json"]
    if report is not None:
        cmd += ["--report", str(report)]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[-400:])
    text = out.stdout.strip()
    return None if text.startswith("✓") else json.loads(text)


def leaves(nodes, level, acc=None):
    """level: "failures", "hints" or "chains"."""
    acc = [] if acc is None else acc
    for n in nodes or []:
        if n.get("type") == "leaf":
            key = (n.get("focusNode"), BNODE.sub("<bnode>", str(n.get("path"))),
                   n.get("component"), n.get("value"))
            if level == "hints":
                key += (n.get("repairHint"),)
            elif level == "chains":
                key += (tuple(BNODE.sub("<bnode>", s) for s in n.get("refChain") or []),
                        tuple(tuple(BNODE.sub("<bnode>", s) for s in c)
                              for c in n.get("altChains") or []))
            acc.append(key)
        else:
            leaves(n.get("children"), level, acc)
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restrict to one fixture directory, e.g. sh_node_cases")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    missing = [b for b in ("shacl", "shaclvalidate.sh") if shutil.which(b) is None]
    if missing:
        print(f"not on PATH: {', '.join(missing)}; skipping")
        return 0

    fixtures = sorted(ROOT.glob("all_test_cases/*/tc*.ttl"))
    if args.only:
        fixtures = [f for f in fixtures if f.parent.name == args.only]
    # the external_report_cases fixtures are hand-written reports, not inputs
    fixtures = [f for f in fixtures if f.parent.name != "external_report_cases"]

    differences, checked = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for fixture in fixtures:
            native = explain(fixture, fixture)
            for engine, build in ENGINES.items():
                produced = subprocess.run(build(fixture), cwd=ROOT, capture_output=True, text=True)
                report = Path(tmp) / f"{fixture.stem}.{engine}.ttl"
                report.write_text(produced.stdout)
                try:
                    rebuilt = explain(fixture, fixture, report)
                except RuntimeError as exc:
                    differences.append((fixture.stem, engine, f"tool failed: {exc}"))
                    continue
                checked += 1
                if (native is None) != (rebuilt is None):
                    differences.append((fixture.stem, engine, "conformance verdict differs"))
                    continue
                if native is None:
                    continue
                for level, label in (("failures", "leaf failures differ"),
                                     ("chains",   "reference chains differ"),
                                     ("hints",    "repair hints differ")):
                    if sorted(leaves(native, level)) != sorted(leaves(rebuilt, level)):
                        differences.append((fixture.stem, engine, label))
                        break
                else:
                    if args.verbose:
                        print(f"  ok  {fixture.stem:38} {engine}")

    print(f"\ncompared {len(fixtures)} fixtures x {len(ENGINES)} validators ({checked} reconstructions)")
    for stem, engine, why in differences:
        print(f"  DIFF  {stem:38} {engine:9} {why}")
    print(f"differences: {len(differences)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
