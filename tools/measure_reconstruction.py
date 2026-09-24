"""Cost of rebuilding an explanation when sh:detail is removed, per LUBM combination.

For one dataset x schema, this parses and validates once, then builds the
explanation three ways and compares them:

  detail    read the sh:detail the validator attached (the normal path)
  shared    every sh:detail triple deleted, re-validations shared by a cache
  unshared  the same, with one pySHACL call per sh:node result

The three must agree field for field and in the same order. Timings are
comparable with each other, not with the command line, because parsing and
validation happen once and are excluded.

Requires: a large data graph, which is NOT in this repository. Chapter 5 used
the two LUBM graphs (171 MB and 732 MB); any data graph big enough to produce
many sh:node results works. Expect minutes of runtime and several GB of memory.

    python3 tools/measure_reconstruction.py <data.ttl> <schema.ttl> <tag> <out.json>
"""
import json, resource, statistics, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyshacl
from rdflib import Graph, Namespace
from shacl_explainer import fallback as fb
from shacl_explainer.expander import build_explanation_tree
from shacl_explainer.renderer import configure_prefixes, to_json

SH = Namespace("http://www.w3.org/ns/shacl#")


def peak_gb():
    # macOS reports ru_maxrss in bytes.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**3


def instrumented():
    """Wrap revalidate_against_shape so calls and per-call durations are counted."""
    original = fb.revalidate_against_shape
    stats = {"calls": 0, "durations": []}

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            stats["calls"] += 1
            stats["durations"].append(time.perf_counter() - start)

    fb.revalidate_against_shape = wrapper
    return original, stats


def restore(original):
    fb.revalidate_against_shape = original


def main():
    data_path, schema_path, tag, out_path = sys.argv[1:5]
    result = {"tag": tag, "data": data_path, "schema": schema_path}

    data = Graph().parse(data_path)
    shapes = Graph().parse(schema_path)
    configure_prefixes(data, shapes)
    result["data_triples"] = len(data)

    _, report, _ = pyshacl.validate(
        data, shacl_graph=shapes, inference="none",
        abort_on_first=False, serialize_report_graph=False)

    result["shape_triples"] = len(shapes)
    result["node_results"] = sum(
        1 for _ in report.subjects(SH.sourceConstraintComponent, SH.NodeConstraintComponent))

    # 1. the normal path, before any triple is removed
    start = time.perf_counter()
    tree_detail = build_explanation_tree(report, data, shapes)
    result["detail_seconds"] = time.perf_counter() - start
    json_detail = to_json(tree_detail)
    del tree_detail

    # 2. and 3. the same report with every sh:detail link gone
    for subject, _, obj in list(report.triples((None, SH.detail, None))):
        report.remove((subject, SH.detail, obj))
    result["detail_triples_removed"] = True

    for label, cache in (("shared", True), ("unshared", False)):
        original, stats = instrumented()
        start = time.perf_counter()
        tree = build_explanation_tree(report, data, shapes, cache_revalidation=cache)
        elapsed = time.perf_counter() - start
        restore(original)
        result[f"{label}_seconds"] = elapsed
        result[f"{label}_calls"] = stats["calls"]
        result[f"{label}_identical"] = (to_json(tree) == json_detail)
        if label == "unshared" and stats["durations"]:
            per_result = [d * 1000 for d in stats["durations"]]
            result["unshared_ms_per_result_mean"] = statistics.fmean(per_result)
            result["unshared_ms_per_result_p95"] = statistics.quantiles(
                per_result, n=20)[-1] if len(per_result) > 1 else per_result[0]
        del tree

    result["peak_gb"] = peak_gb()
    Path(out_path).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
