# entry point: accepts .ttl files, prints result
import argparse
import csv
import pickle
import subprocess
import sys
import time
from pathlib import Path
import pyshacl
from rdflib import Graph, Namespace, RDF
from .expander import build_explanation_tree
from .renderer import (
    configure_prefixes,
    filter_by_focus,
    filter_tree,
    limit_roots,
    to_html,
    to_json,
    to_summary,
    to_text_tree,
    write_csv,
)

SH = Namespace("http://www.w3.org/ns/shacl#")

def run(data_path: str, shapes_path: str, fmt="text",
        summary=False, limit=None, focus=None, csv_path=None, timing=False,
        top=None, path=None, component=None, reference_path=None,
        hints=False, save_report=None, timing_csv=None, report_path=None,
        data_format="turtle", shapes_format="turtle", report_format="turtle",
        output=None, color="auto"):
    timings = {}
    output_path = resolve_output_path(fmt, output) if output else None

    start = time.perf_counter()
    data_graph = load_graph(data_path, rdf_format=data_format)
    timings["parse data"] = time.perf_counter() - start

    start = time.perf_counter()
    shapes_graph = load_graph(shapes_path, rdf_format=shapes_format)
    timings["parse shapes"] = time.perf_counter() - start
    configure_prefixes(data_graph, shapes_graph)

    if report_path:
        start = time.perf_counter()
        report_graph = load_graph(report_path, rdf_format=report_format)
        timings["parse report"] = time.perf_counter() - start
        conforms_value = report_graph.value(predicate=SH.conforms)
        conforms = bool(conforms_value.toPython()) if conforms_value is not None else False
    else:
        start = time.perf_counter()
        conforms, report_graph, _ = pyshacl.validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="none",
            abort_on_first=False,
            serialize_report_graph=False,
        )
        timings["validate"] = time.perf_counter() - start
    stats = collect_stats(data_graph, shapes_graph, report_graph)

    if save_report:
        report_graph.serialize(destination=save_report, format="turtle")

    if conforms:
        output_str = "✓ Data is valid."
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(output_str + "\n")
            print(f"Output written to {output_path}", file=sys.stderr)
        else:
            print(output_str)
        if timing:
            print_timings(timings)
        if timing_csv:
            write_timing_csv(timing_csv, timings, stats, data_path, shapes_path)
        return

    start = time.perf_counter()
    tree = build_explanation_tree(report_graph, data_graph, shapes_graph)
    timings["build explanation tree"] = time.perf_counter() - start

    tree = filter_by_focus(tree, focus)
    tree = filter_tree(
        tree,
        path=path,
        component=component,
        reference_path=reference_path,
    )

    if csv_path:
        write_csv(tree, csv_path)

    display_tree = limit_roots(tree, limit)
    use_color = should_colorize(color, fmt, summary, output_path)

    start = time.perf_counter()
    if summary:
        output_str = to_summary(display_tree, top=top, stats=stats)
    elif fmt == "json":
        output_str = to_json(display_tree)
    elif fmt == "html":
        output_str = to_html(
            display_tree,
            title="SHACL Explanation Report",
            metadata=html_metadata(data_path, shapes_path),
        )
    else:
        output_str = to_text_tree(display_tree, hints=hints, color=use_color)
    timings["render"] = time.perf_counter() - start

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(output_str)
            if not output_str.endswith("\n"):
                handle.write("\n")
        print(f"Output written to {output_path}", file=sys.stderr)
    else:
        print(output_str)

    if timing:
        print_timings(timings)
    if timing_csv:
        write_timing_csv(timing_csv, timings, stats, data_path, shapes_path)

def collect_stats(data_graph, shapes_graph, report_graph):
    report_node = report_graph.value(predicate=RDF.type, object=SH.ValidationReport)
    top_results = list(report_graph.objects(report_node, SH.result))
    all_results = list(report_graph.subjects(RDF.type, SH.ValidationResult))
    return {
        "data_triples": len(data_graph),
        "shape_triples": len(shapes_graph),
        "top_results": len(top_results),
        "all_results": len(all_results),
    }

def html_metadata(data_path, shapes_path):
    return {
        "dataset": Path(data_path).name,
        "shapes": Path(shapes_path).name,
        "commit": current_commit(),
    }

def current_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"

def load_graph(path, rdf_format="turtle"):
    graph_path = Path(path)
    if graph_path.suffix.lower() in {".pkl", ".pickle"}:
        with open(graph_path, "rb") as handle:
            graph = pickle.load(handle)
        if not isinstance(graph, Graph):
            raise TypeError(
                f"Expected an rdflib.Graph in {graph_path}, got {type(graph).__name__}"
            )
        return graph

    return Graph().parse(path, format=rdf_format)

def resolve_output_path(fmt, output):
    path = Path(output)
    if fmt == "html" and not path.is_absolute() and path.parent == Path("."):
        return Path("html_outputs") / path
    return path

def should_colorize(color, fmt, summary, output_path):
    if fmt != "text" or summary:
        return False
    if color == "always":
        return True
    if color == "never":
        return False
    return output_path is None and sys.stdout.isatty()

def print_timings(timings):
    print("\nTimings:", file=sys.stderr)
    for label, seconds in timings.items():
        print(f"  {label}: {seconds:.3f}s", file=sys.stderr)

def write_timing_csv(path, timings, stats, data_path, shapes_path):
    fieldnames = [
        "data_path",
        "shapes_path",
        "data_triples",
        "shape_triples",
        "top_results",
        "all_results",
        "parse_data_seconds",
        "parse_shapes_seconds",
        "validate_seconds",
        "build_explanation_tree_seconds",
        "render_seconds",
    ]
    row = {
        "data_path": data_path,
        "shapes_path": shapes_path,
        "data_triples": stats.get("data_triples", 0),
        "shape_triples": stats.get("shape_triples", 0),
        "top_results": stats.get("top_results", 0),
        "all_results": stats.get("all_results", 0),
        "parse_data_seconds": f"{timings.get('parse data', 0):.6f}",
        "parse_shapes_seconds": f"{timings.get('parse shapes', 0):.6f}",
        "validate_seconds": f"{timings.get('validate', 0):.6f}",
        "build_explanation_tree_seconds": f"{timings.get('build explanation tree', 0):.6f}",
        "render_seconds": f"{timings.get('render', 0):.6f}",
    }
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Explain SHACL sh:node validation failures as a tree."
    )
    parser.add_argument("data_path", help="Data graph path, e.g. .ttl or pickled rdflib.Graph")
    parser.add_argument("shapes_path", help="Shapes graph path, e.g. .ttl or pickled rdflib.Graph")
    parser.add_argument(
        "legacy_format",
        nargs="?",
        choices=["text", "json", "html"],
        help="Deprecated positional output format; prefer --format.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default=None,
        help="Output format for the explanation tree.",
    )
    parser.add_argument(
        "--output",
        help="Write rendered output to this file instead of stdout.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print aggregate counts instead of the full tree.",
    )
    parser.add_argument(
        "--top",
        type=int,
        help="Limit each summary table to the top N entries.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of top-level explanation roots printed.",
    )
    parser.add_argument(
        "--focus",
        help="Show only explanation roots for this focus node URI or compact name.",
    )
    parser.add_argument(
        "--path",
        help="Show only leaf failures on this leaf path URI or compact name.",
    )
    parser.add_argument(
        "--component",
        help="Show only leaf failures for this component, e.g. minCount.",
    )
    parser.add_argument(
        "--reference-path",
        help="Show only failures reached through this referencing property path.",
    )
    parser.add_argument(
        "--hints",
        action="store_true",
        help="Add repair hints to text output.",
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Colorize text-tree output: auto for terminals, always to force, never for plain text.",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        help="Write leaf failures to a CSV file.",
    )
    parser.add_argument(
        "--save-report",
        help="Save the raw pySHACL validation report graph as Turtle.",
    )
    parser.add_argument(
        "--report",
        dest="report_path",
        help="Use an existing SHACL validation report graph instead of running pySHACL.",
    )
    parser.add_argument(
        "--data-format",
        default="turtle",
        help="RDF format for the data graph when it is not .pkl/.pickle, e.g. turtle, xml, json-ld, nt.",
    )
    parser.add_argument(
        "--shapes-format",
        default="turtle",
        help="RDF format for the shapes graph when it is not .pkl/.pickle, e.g. turtle, xml, json-ld, nt.",
    )
    parser.add_argument(
        "--report-format",
        default="turtle",
        help="RDF format for --report when it is not .pkl/.pickle, e.g. turtle, xml, json-ld, nt.",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Print parse, validation, build, and render timings to stderr.",
    )
    parser.add_argument(
        "--timing-csv",
        help="Write reproducibility and timing metrics to a CSV file.",
    )
    return parser.parse_args(argv)

if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    run(
        args.data_path,
        args.shapes_path,
        fmt=args.format or args.legacy_format or "text",
        summary=args.summary,
        limit=args.limit,
        focus=args.focus,
        csv_path=args.csv_path,
        timing=args.timing,
        top=args.top,
        path=args.path,
        component=args.component,
        reference_path=args.reference_path,
        hints=args.hints,
        save_report=args.save_report,
        timing_csv=args.timing_csv,
        report_path=args.report_path,
        data_format=args.data_format,
        shapes_format=args.shapes_format,
        report_format=args.report_format,
        output=args.output,
        color=args.color,
    )
    
# Running against TC3 should produce:
# ↳ via ex:ContractorShape
#    ↳ via ex:ContractorShape → ex:EmployeeShape
#      ❌ [datatype]  path=ex:age  value="thirty-one"
#          → ex:age must be an xsd:integer
