#!/usr/bin/env python3
"""
run_tests.py — Validate all 5 SHACL test cases and dissect the raw
validation reports so you can see exactly what pyshacl gives you
(and what information is missing / needs reconstruction).

Each test case prints:
  - conforms: True/False
  - every sh:ValidationResult with ALL its triples
  - a structured summary per result
  - a "gap analysis": what the report says vs. what we need
"""

from pathlib import Path
from rdflib import Graph, Namespace, RDF, URIRef, Literal, BNode
from rdflib.namespace import XSD
import pyshacl

SH   = Namespace("http://www.w3.org/ns/shacl#")
EX   = Namespace("http://example.org/")

# ── Helpers ──────────────────────────────────────────────────────────────────

COMPONENT_LABELS = {
    str(SH.NodeConstraintComponent):       "NodeConstraintComponent     ← referencing",
    str(SH.PropertyConstraintComponent):   "PropertyConstraintComponent",
    str(SH.MinCountConstraintComponent):   "MinCountConstraintComponent ← LEAF",
    str(SH.MaxCountConstraintComponent):   "MaxCountConstraintComponent ← LEAF",
    str(SH.DatatypeConstraintComponent):   "DatatypeConstraintComponent ← LEAF",
    str(SH.PatternConstraintComponent):    "PatternConstraintComponent  ← LEAF",
    str(SH.ClassConstraintComponent):      "ClassConstraintComponent    ← LEAF",
    str(SH.InConstraintComponent):         "InConstraintComponent       ← LEAF",
    str(SH.MinLengthConstraintComponent):  "MinLengthConstraintComponent← LEAF",
    str(SH.MaxLengthConstraintComponent):  "MaxLengthConstraintComponent← LEAF",
    str(SH.HasValueConstraintComponent):   "HasValueConstraintComponent ← LEAF",
    str(SH.AndConstraintComponent):        "AndConstraintComponent",
    str(SH.OrConstraintComponent):         "OrConstraintComponent",
    str(SH.NotConstraintComponent):        "NotConstraintComponent",
}

def short(uri):
    """Shorten a URI/BNode/Literal for display."""
    if uri is None:
        return "—"
    if isinstance(uri, BNode):
        return f"_:{str(uri)[:8]}"
    if isinstance(uri, Literal):
        return f'"{uri}"^^{uri.datatype.n3() if uri.datatype else "plain"}'
    s = str(uri)
    for prefix, ns in [("sh:", str(SH)), ("ex:", str(EX)),
                       ("xsd:", str(XSD)),
                       ("rdf:", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")]:
        if s.startswith(ns):
            return prefix + s[len(ns):]
    return f"<{s}>"

def component_label(uri):
    return COMPONENT_LABELS.get(str(uri), short(uri))

# ── Core analysis ────────────────────────────────────────────────────────────

def analyse_result(r, report_graph, idx):
    """Extract and print every meaningful triple on one ValidationResult."""
    g = report_graph
    get = lambda p: g.value(r, p)

    component = get(SH.sourceConstraintComponent)
    focus     = get(SH.focusNode)
    value     = get(SH.value)
    src_shape = get(SH.sourceShape)
    result_path = get(SH.resultPath)
    message   = get(SH.resultMessage)
    severity  = get(SH.resultSeverity)

    is_referencing = str(component) == str(SH.NodeConstraintComponent) if component else False

    print(f"  ┌─ Result #{idx+1} {'(REFERENCING)' if is_referencing else '(LEAF)'}")
    print(f"  │  sh:sourceConstraintComponent  {component_label(component)}")
    print(f"  │  sh:focusNode                  {short(focus)}")
    if value is not None:
        print(f"  │  sh:value                      {short(value)}")
    if result_path is not None:
        print(f"  │  sh:resultPath                 {short(result_path)}")
    print(f"  │  sh:sourceShape                {short(src_shape)}")
    print(f"  │  sh:resultSeverity             {short(severity)}")
    if message:
        print(f"  │  sh:resultMessage              {message}")

    # For referencing failures: check what sh:value carries
    if is_referencing:
        print(f"  │")
        print(f"  │  ⚠  This is a NodeConstraintComponent failure.")
        print(f"  │     sh:value (the failing node) = {short(value)}")
        print(f"  │     sh:resultPath               = {short(result_path)}  (expected: None)")
        print(f"  │     → The report does NOT reveal which constraints inside")
        print(f"  │       {short(src_shape)} failed.")
        print(f"  │     → Your tool must re-validate {short(focus)} against")
        print(f"  │       the referenced shape to find the leaf failures.")

    print(f"  └{'─'*60}")

def gap_summary(results_info):
    """Print a gap analysis table."""
    referencing = [r for r in results_info if r["is_ref"]]
    leaves      = [r for r in results_info if not r["is_ref"]]

    print(f"\n  GAP ANALYSIS")
    print(f"  {'─'*58}")
    print(f"  Total results in report : {len(results_info)}")
    print(f"  Referencing (sh:node)   : {len(referencing)}  ← need expansion")
    print(f"  Leaf failures           : {len(leaves)}   ← already actionable")

    if referencing:
        print(f"\n  Referencing results that need expansion:")
        for r in referencing:
            print(f"    focusNode={r['focus']}  shape={r['shape']}")
    if not leaves:
        print(f"\n  ⚠  NO leaf failures surfaced directly — user sees nothing actionable!")
    else:
        print(f"\n  Leaf failures already in report:")
        for r in leaves:
            print(f"    focusNode={r['focus']}  path={r['path']}  "
                  f"component={r['component']}")

# ── Per-test runner ──────────────────────────────────────────────────────────

TEST_CASES = [
    ("tc1_single_leaf.ttl",
     "TC1: Simple sh:node failure — one leaf violation",
     "Expect: 1 NodeConstraintComponent result, 0 leaf results surfaced.\n"
     "  The single DatatypeConstraintComponent on ex:age is hidden."),

    ("tc2_multi_leaf.ttl",
     "TC2: sh:node failure — multiple leaf violations",
     "Expect: 1 NodeConstraintComponent result.\n"
     "  Three leaf violations (age MinCount, name MinCount, email Pattern) hidden.\n"
     "  Key question: does pyshacl report ANY of them directly?"),

    ("tc3_two_level.ttl",
     "TC3: Two-level nesting  ContractorShape → EmployeeShape → PersonShape",
     "Expect: 1 NodeConstraintComponent at the top level only.\n"
     "  The middle NodeConstraintComponent (EmployeeShape) may or may not appear.\n"
     "  The actual leaf DatatypeConstraintComponent is definitely hidden."),

    ("tc4_mixed.ttl",
     "TC4: Mixed — direct property violations + sh:node violation on same node",
     "Expect: direct MinCount for ex:department + 1 NodeConstraintComponent.\n"
     "  Key question: are the nested leaf failures (age Datatype, name MinCount)\n"
     "  reported alongside the direct ones, or hidden behind NodeConstraintComponent?"),

    ("tc5_diamond.ttl",
     "TC5: Diamond — PersonShape reached via two different parent shapes",
     "Expect: 2 NodeConstraintComponent results (one per branch).\n"
     "  Key question: are PersonShape leaf failures duplicated in the report?\n"
     "  This reveals whether the engine deduplicates, and what your tool must handle."),
]

def run_test(filename, title, expectation):
    path = Path(__file__).parent / filename
    print("\n" + "═"*70)
    print(f"  {title}")
    print("═"*70)
    print(f"  File: {filename}")
    print(f"  What to expect:\n  {expectation}")
    print()

    combined = Graph().parse(str(path), format="turtle")
    # Split the file into shapes + data by convention:
    #   Everything with sh:targetClass / sh:property / sh:node → shapes
    #   Everything with a ex: class type → data
    # pyshacl accepts a combined graph fine.
    conforms, report_graph, report_text = pyshacl.validate(
        combined,
        shacl_graph=combined,
        inference="none",
        serialize_report_graph=False,
        abort_on_first=False,   # ← collect ALL failures
    )

    print(f"  conforms = {conforms}")
    print()

    results = list(report_graph.subjects(RDF.type, SH.ValidationResult))
    print(f"  Validation results in report: {len(results)}")
    print()

    results_info = []
    for i, r in enumerate(results):
        get = lambda p, node=r: report_graph.value(node, p)
        component = get(SH.sourceConstraintComponent)
        is_ref = str(component) == str(SH.NodeConstraintComponent) if component else False
        results_info.append({
            "is_ref":    is_ref,
            "focus":     short(get(SH.focusNode)),
            "shape":     short(get(SH.sourceShape)),
            "path":      short(get(SH.resultPath)),
            "component": component_label(component),
        })
        analyse_result(r, report_graph, i)

    gap_summary(results_info)

    # Also dump raw Turtle of the report for inspection
    print(f"\n  RAW REPORT TURTLE (for study):")
    print("  " + "·"*58)
    raw = report_graph.serialize(format="turtle")
    for line in raw.splitlines():
        print("  " + line)

# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("SHACL Validation Report Dissection")
    print("Thesis: Root Cause Localization for sh:node Constraints")
    print("="*70)

    for filename, title, expectation in TEST_CASES:
        try:
            run_test(filename, title, expectation)
        except Exception as e:
            print(f"\n  ERROR running {filename}: {e}")
            import traceback; traceback.print_exc()

    print("\n" + "═"*70)
    print("  DONE — study the NodeConstraintComponent results above.")
    print("  Your expansion engine must take every referencing result and")
    print("  re-validate the focusNode against the referenced shape to")
    print("  surface the hidden leaf failures.")
    print("="*70)
