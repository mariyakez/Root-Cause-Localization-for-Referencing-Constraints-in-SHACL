#Two output formats: text tree for the thesis writeup, JSON for machine consumption.

# renderer.py
import csv
import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from rdflib import BNode, Literal
from rdflib.namespace import RDF
from .tree import LeafFailure, ReferenceNode

PREFIXES = [
    ("ex:", "http://example.org/"),
    ("ub:", "http://swat.cse.lehigh.edu/onto/univ-bench.owl#"),
    ("sh:", "http://www.w3.org/ns/shacl#"),
    ("xsd:", "http://www.w3.org/2001/XMLSchema#"),
]

SHACL_NS = "http://www.w3.org/ns/shacl#"

COMPONENT_SHORT = {
    "NodeConstraintComponent":    "sh:node",
    "DatatypeConstraintComponent":"datatype",
    "MinCountConstraintComponent":"minCount",
    "MaxCountConstraintComponent":"maxCount",
    "PatternConstraintComponent": "pattern",
    "ClassConstraintComponent":   "class",
    "InConstraintComponent":      "in",
    "NodeKindConstraintComponent":"nodeKind",
    "MinInclusiveConstraintComponent":"minInclusive",
    "MaxInclusiveConstraintComponent":"maxInclusive",
    "MinExclusiveConstraintComponent":"minExclusive",
    "MaxExclusiveConstraintComponent":"maxExclusive",
    "LessThanConstraintComponent":"lessThan",
    "LessThanOrEqualsConstraintComponent":"lessThanOrEquals",
    "HasValueConstraintComponent":"hasValue",
    "EqualsConstraintComponent":  "equals",
    "DisjointConstraintComponent":"disjoint",
    "ClosedConstraintComponent":  "closed",
    "OrConstraintComponent":      "or",
    "XoneConstraintComponent":    "xone",
    "NotConstraintComponent":     "not",
}

def configure_prefixes(*graphs):
    seen = {namespace for _, namespace in PREFIXES}
    dynamic = []

    for graph in graphs:
        for prefix, namespace in graph.namespaces():
            if not prefix:
                continue
            namespace = str(namespace)
            if namespace in seen:
                continue
            seen.add(namespace)
            dynamic.append((f"{prefix}:", namespace))

    # Longest namespaces first avoids shortening with a less specific prefix.
    dynamic.sort(key=lambda item: len(item[1]), reverse=True)
    PREFIXES[:0] = dynamic

def short_uri(uri) -> str:
    if uri is None:
        return ""
    if isinstance(uri, Literal):
        return uri.n3()
    s = str(uri)
    for prefix, ns in PREFIXES:
        if s.startswith(ns):
            return prefix + s[len(ns):]
    return f"<{s}>"

def format_chain(chain) -> str:
    return " -> ".join(short_uri(shape) for shape in chain)

def full_leaf_chain(leaf: LeafFailure, chain=None) -> list:
    full_chain = list(chain if chain is not None else leaf.ref_chain)
    source_shape = leaf.source_shape
    if (
        full_chain
        and source_shape is not None
        and not isinstance(source_shape, BNode)
        and str(source_shape) not in {str(shape) for shape in full_chain}
    ):
        full_chain.append(source_shape)
    return full_chain

def format_alt_chains(leaf: LeafFailure) -> str:
    chains = []
    for chain in getattr(leaf, "alt_chains", []):
        full_chain = full_leaf_chain(leaf, chain)
        if full_chain:
            chains.append(format_chain(full_chain))
    return " | ".join(chains)

def component_label(component) -> str:
    compact = short_uri(component).split(":")[-1]
    return COMPONENT_SHORT.get(compact, compact)

def repair_hint(leaf: LeafFailure) -> str | None:
    comp = component_label(leaf.component)
    path = short_uri(leaf.result_path) or "the required path"
    focus = short_uri(leaf.focus_node) or "the focus node"
    value = short_uri(leaf.value_node)

    if comp == "minCount":
        return f"Add at least one {path} value to {focus}."
    if comp == "maxCount":
        return f"Remove extra {path} values from {focus}."
    if comp == "datatype" and value:
        return f"Replace {value} on {path} with a value of the required datatype."
    if comp == "pattern" and value:
        return f"Change {value} on {path} so it matches the required pattern."
    if comp == "class":
        return f"Make {focus} conform to the required class."
    if comp == "in" and value:
        return f"Replace {value} on {path} with one of the allowed values."
    return None

COMPONENT_WIDTH = 10   # fixed column width for component names

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}

def color_text(text: str, *styles: str, enabled=False) -> str:
    if not enabled:
        return text
    prefix = "".join(ANSI[style] for style in styles)
    return f"{prefix}{text}{ANSI['reset']}"

def to_text_tree(nodes: list, indent=0, hints=False, color=False) -> str:
    # At the top level, group by focus node and print a header per group
    if indent == 0:
        groups = {}
        for node in nodes:
            fn = str(getattr(node, "focus_node", ""))
            groups.setdefault(fn, []).append(node)

        blocks = []
        for fn, group_nodes in groups.items():
            block = []
            focus_line = f"Focus node: {short_uri_from_str(fn)}/"
            block.append(color_text(focus_line, "cyan", "bold", enabled=color))
            rendered = _render_nodes(group_nodes, prefix="", hints=hints, color=color)
            if rendered:
                block.append(rendered)
            blocks.append("\n".join(block))

        sep = "\n\n"
        return sep.join(blocks)

    return _render_nodes(nodes, prefix="   " * indent, hints=hints, color=color)


def short_uri_from_str(s: str) -> str:
    """short_uri for a plain string (not an RDFNode)."""
    for prefix, ns in PREFIXES:
        if s.startswith(ns):
            return prefix + s[len(ns):]
    return f"<{s}>"


def _render_nodes(nodes: list, prefix: str, hints: bool, color: bool) -> str:
    lines = []

    for index, node in enumerate(nodes):
        is_last = index == len(nodes) - 1
        branch = "└── " if is_last else "├── "
        child_prefix = prefix + ("    " if is_last else "│   ")

        if isinstance(node, LeafFailure):
            comp  = component_label(node.component).ljust(COMPONENT_WIDTH)
            path  = short_uri(node.result_path) if node.result_path else ""
            value = short_uri(node.value_node)  if node.value_node  else "(missing)"

            # main violation line
            error_icon = color_text("❌", "red", "bold", enabled=color)
            comp_text = color_text(comp, "red", "bold", enabled=color)
            path_text = color_text(path, "yellow", enabled=color)
            value_style = ("red",) if value == "(missing)" else ("yellow",)
            value_text = color_text(value, *value_style, enabled=color)
            lines.append(f"{prefix}{branch}{error_icon} {comp_text}  {path_text} = {value_text}")

            details = []
            primary_chain = full_leaf_chain(node)
            if primary_chain:
                details.append(color_text(f"via {format_chain(primary_chain)}", "magenta", enabled=color))
            if node.message:
                details.append(color_text(f"message: {node.message}", "dim", enabled=color))
            if hints:
                hint = repair_hint(node)
                if hint:
                    details.append(color_text(f"→ fix: {hint}", "green", enabled=color))
            if node.alt_chains:
                for chain in node.alt_chains:
                    alt_chain = full_leaf_chain(node, chain)
                    if alt_chain:
                        details.append(color_text(f"also via {format_chain(alt_chain)}", "magenta", enabled=color))

            lines.extend(_render_detail_lines(details, child_prefix))

        else:   # ReferenceNode
            label = short_uri(node.source_shape)
            if node.result_path:
                label += f"  path={short_uri(node.result_path)}"

            ref_text = color_text(f"sh:node {label}/", "magenta", "bold", enabled=color)
            lines.append(f"{prefix}{branch}{ref_text}")
            rendered_children = _render_nodes(node.children, child_prefix, hints, color)
            if rendered_children:
                lines.append(rendered_children)

    return "\n".join(lines)

def _render_detail_lines(details: list[str], prefix: str) -> list[str]:
    lines = []
    for index, detail in enumerate(details):
        branch = "└── " if index == len(details) - 1 else "├── "
        lines.append(f"{prefix}{branch}{detail}")
    return lines

def iter_leaves(nodes):
    for node in nodes:
        if isinstance(node, LeafFailure):
            yield node
        else:
            yield from iter_leaves(node.children)

def iter_references(nodes):
    for node in nodes:
        if isinstance(node, ReferenceNode):
            yield node
            yield from iter_references(node.children)

def focus_matches(node, focus: str) -> bool:
    if not focus:
        return True
    focus_node = getattr(node, "focus_node", None)
    if focus_node is None:
        return False
    return focus in {str(focus_node), short_uri(focus_node)}

def filter_by_focus(nodes, focus: str):
    if not focus:
        return nodes
    return [node for node in nodes if focus_matches(node, focus)]

def matches_compact(value, expected: str | None) -> bool:
    if not expected:
        return True
    return expected in {str(value), short_uri(value)}

def filter_tree(nodes, path=None, component=None, reference_path=None):
    """
    Return a filtered tree without mutating the input nodes.

    This keeps callers free to render the original tree again as text, JSON,
    CSV, or summary after applying a filtered view.
    """
    if not any([path, component, reference_path]):
        return nodes

    def walk(node, ref_path_matched):
        if isinstance(node, LeafFailure):
            if path and not matches_compact(node.result_path, path):
                return None
            if component and component not in {
                str(node.component),
                short_uri(node.component),
                component_label(node.component),
            }:
                return None
            if reference_path and not ref_path_matched:
                return None
            return node

        current_ref_match = ref_path_matched or matches_compact(
            node.result_path, reference_path)
        children = [
            child for child in
            (walk(child, current_ref_match) for child in node.children)
            if child is not None
        ]
        if not children:
            return None
        return replace(node, children=children)

    return [node for node in (walk(node, False) for node in nodes) if node is not None]

def limit_roots(nodes, limit: int | None):
    if limit is None:
        return nodes
    return nodes[:limit]

def to_summary(nodes: list, top=None, stats=None) -> str:
    leaves     = list(iter_leaves(nodes))
    references = list(iter_references(nodes))

    # focus nodes
    focus_nodes = {str(getattr(n, "focus_node", "")) for n in nodes}

    # max reference depth
    max_depth = max((len(full_leaf_chain(l)) for l in leaves), default=0)

    # counters
    leaf_paths = Counter(
        (short_uri(l.result_path) or "none",
         component_label(l.component))
        for l in leaves
    )
    leaf_components = Counter(component_label(l.component) for l in leaves)
    leaf_chain_errors = Counter()
    for leaf in leaves:
        leaf_error = f"{component_label(leaf.component)} {short_uri(leaf.result_path) or 'none'}"
        chain = full_leaf_chain(leaf)
        if chain:
            leaf_chain_errors[(format_chain(chain), leaf_error)] += 1
        for alt_chain in getattr(leaf, "alt_chains", []):
            full_alt_chain = full_leaf_chain(leaf, alt_chain)
            if full_alt_chain:
                leaf_chain_errors[(format_chain(full_alt_chain), leaf_error)] += 1

    reference_paths = Counter(
        f"{short_uri(ref.result_path)} -> {short_uri(ref.source_shape)}"
        if ref.result_path
        else f"sh:node -> {short_uri(ref.source_shape)}"
        for ref in references
    )

    direct   = sum(1 for l in leaves if not l.ref_chain)
    via_node = sum(1 for l in leaves if     full_leaf_chain(l))

    sep = "━" * 44
    lines = [
        sep,
        "SHACL Explanation Summary",
        sep,
        f"Focus nodes affected  : {len(focus_nodes)}",
        f"Total leaf failures   : {len(leaves)}"
          f"  ({via_node} via sh:node,  {direct} direct)",
        f"Unique paths failing  : {len(leaf_paths)}",
        f"Max reference depth   : {max_depth} level{'s' if max_depth != 1 else ''}",
    ]

    if stats:
        lines += [
            "",
            "Input",
            f"  Data triples        : {stats.get('data_triples', 0)}",
            f"  Shape triples       : {stats.get('shape_triples', 0)}",
            f"  Pyshacl results     : {stats.get('all_results', 0)}"
              f"  ({stats.get('top_results', 0)} top-level)",
        ]

    def add_table(title, rows, col1="", col2=""):
        lines.append("")
        lines.append(title)
        if not rows:
            lines.append("  (none)")
            return
        for item, count in rows:
            lines.append(f"  {str(count):>5}  {item}")

    # combined path + component table
    lines.append("")
    lines.append("Top failing paths")
    if not leaf_paths:
        lines.append("  (none)")
    else:
        items = leaf_paths.most_common(top)
        for (path, comp), count in items:
            lines.append(f"  {str(count):>5}  {path:<30}  {comp}")

    add_table(
        "Top components",
        [(comp, count) for comp, count
         in leaf_components.most_common(top)],
    )
    add_table(
        "Top reference paths",
        [(path, count) for path, count
         in reference_paths.most_common(top)],
    )
    lines.append("")
    lines.append("Top full leaf reference chains")
    if not leaf_chain_errors:
        lines.append("  (none)")
    else:
        for (chain, error), count in leaf_chain_errors.most_common(top):
            lines.append(f"  {str(count):>5}  {chain}  → {error}")

    lines.append(sep)
    return "\n".join(lines)

def write_csv(nodes: list, destination):
    close_after = False
    if isinstance(destination, str):
        destination = open(destination, "w", newline="", encoding="utf-8")
        close_after = True

    try:
        writer = csv.DictWriter(
            destination,
            fieldnames=[
                "focus_node",
                "depth",
                "reference_chain",
                "alternate_reference_chains",
                "leaf_path",
                "component",
                "value",
                "message",
                "kind",
                "repair_hint",
            ],
        )
        writer.writeheader()
        for leaf in iter_leaves(nodes):
            chain = full_leaf_chain(leaf)
            writer.writerow({
                "focus_node": short_uri(leaf.focus_node),
                "depth": len(chain),
                "reference_chain": format_chain(chain),
                "alternate_reference_chains": format_alt_chains(leaf),
                "leaf_path": short_uri(leaf.result_path),
                "component": short_uri(leaf.component),
                "value": short_uri(leaf.value_node),
                "message": leaf.message or "",
                "kind": "referenced" if chain else "direct",
                "repair_hint": repair_hint(leaf) or "",
            })
    finally:
        if close_after:
            destination.close()
def serialise_value(node):
    """Return a clean Python value for JSON, without RDF literal quoting."""
    if node is None:
        return None
    if isinstance(node, Literal):
        return str(node)
    return short_uri(node)

def tree_to_data(nodes: list) -> list:
    """Serialise explanation nodes once so JSON and HTML stay consistent."""
    def serialise(node):
        if isinstance(node, LeafFailure):
            d = {
                "type":       "leaf",
                "focusNode":  serialise_value(node.focus_node),
                "path":       serialise_value(node.result_path),
                "component":  serialise_value(node.component),
                "value":      serialise_value(node.value_node) if node.value_node else None,
                "message":    node.message,
                "repairHint": repair_hint(node),
                "refChain":   [short_uri(s) for s in full_leaf_chain(node)],
                "altChains":  [
                    [short_uri(s) for s in full_leaf_chain(node, chain)]
                    for chain in getattr(node, "alt_chains", [])
                    if full_leaf_chain(node, chain)
                ],
            }
        else:
            d = {
                "type":            "reference",
                "focusNode":       serialise_value(node.focus_node),
                "shape":           serialise_value(node.source_shape),
                "referencedShape": short_uri(node.referenced_shape) if node.referenced_shape else None,
                "path":            serialise_value(node.result_path),
                "refChain":        [short_uri(s) for s in node.ref_chain],
                "children":        [serialise(c) for c in node.children],
            }
        return {k: v for k, v in d.items() if v is not None}

    return [serialise(n) for n in nodes]

def shape_catalog_data(shapes_graph) -> dict:
    """
    Serialise a lightweight map of shape -> direct child constraints so HTML can
    optionally show non-violating direct constraints in graph view.
    """
    from rdflib import Namespace

    SH = Namespace(SHACL_NS)
    catalog: dict[str, list[dict[str, str]]] = {}

    for shape in set(shapes_graph.subjects(RDF.type, SH.NodeShape)):
        shape_key = short_uri(shape)
        children: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()

        for prop_shape in shapes_graph.objects(shape, SH.property):
            path = shapes_graph.value(prop_shape, SH.path)
            if path is None:
                continue
            path_key = short_uri(path)
            referenced = shapes_graph.value(prop_shape, SH.node)
            if referenced is not None:
                ref_key = short_uri(referenced)
                marker = ("shape", path_key, ref_key)
                if marker not in seen:
                    seen.add(marker)
                    children.append({
                        "type": "shape",
                        "path": path_key,
                        "shape": ref_key,
                    })
            else:
                marker = ("leaf", path_key, "")
                if marker not in seen:
                    seen.add(marker)
                    children.append({
                        "type": "leaf",
                        "path": path_key,
                    })

        if children:
            children.sort(key=lambda item: (item["type"] != "shape", item.get("shape", item["path"])))
            catalog[shape_key] = children

    return catalog

def to_json(nodes: list) -> str:
    return json.dumps(tree_to_data(nodes), indent=2)

def to_html(nodes: list, title: str = "SHACL Explanation Report", metadata=None, shape_catalog=None) -> str:
    """
    Produce a self-contained HTML file embedding the explanation tree.
    The JSON data is injected into the REPORT_DATA constant in the
    page's <script> block. No external dependencies required.
    """
    import datetime
    import html as _html

    metadata = metadata or {}
    shape_catalog = shape_catalog or {}
    data_json = json.dumps(tree_to_data(nodes), indent=2)
    catalog_json = json.dumps(shape_catalog, indent=2)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = _load_template().replace("__REPORT_DATA__", data_json)
    html = html.replace("__SHAPE_CATALOG__", catalog_json)
    html = html.replace("__TITLE__", _html.escape(title))
    html = html.replace("__DATASET__", _html.escape(metadata.get("dataset", "unknown")))
    html = html.replace("__SHAPES__", _html.escape(metadata.get("shapes", "unknown")))
    html = html.replace("__COMMIT__", _html.escape(metadata.get("commit", "unknown")))
    html = html.replace("__TIMESTAMP__", timestamp)
    return html

def _load_template() -> str:
    template = Path(__file__).with_name("report_template.html")
    return template.read_text(encoding="utf-8")
