#Two output formats: text tree for the thesis writeup, JSON for machine consumption.

# renderer.py
import csv
import json
from collections import Counter
from dataclasses import replace
from rdflib import Literal
from .tree import LeafFailure, ReferenceNode

PREFIXES = [
    ("ex:", "http://example.org/"),
    ("ub:", "http://swat.cse.lehigh.edu/onto/univ-bench.owl#"),
    ("sh:", "http://www.w3.org/ns/shacl#"),
    ("xsd:", "http://www.w3.org/2001/XMLSchema#"),
]

COMPONENT_SHORT = {
    "NodeConstraintComponent":    "sh:node",
    "DatatypeConstraintComponent":"datatype",
    "MinCountConstraintComponent":"minCount",
    "MaxCountConstraintComponent":"maxCount",
    "PatternConstraintComponent": "pattern",
    "ClassConstraintComponent":   "class",
    "InConstraintComponent":      "in",
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

def to_text_tree(nodes: list, indent=0, hints=False) -> str:
    lines = []

    # At the top level, group by focus node and print a header per group
    if indent == 0:
        groups = {}
        for node in nodes:
            fn = str(getattr(node, "focus_node", ""))
            groups.setdefault(fn, []).append(node)

        blocks = []
        for fn, group_nodes in groups.items():
            block = []
            block.append(f"Focus node: {short_uri_from_str(fn)}")
            block.append("─" * 44)
            block.append(_render_nodes(group_nodes, indent=0, hints=hints))
            blocks.append("\n".join(block))

        sep = "\n\n" + "━" * 44 + "\n\n"
        return sep.join(blocks)

    return _render_nodes(nodes, indent, hints)


def short_uri_from_str(s: str) -> str:
    """short_uri for a plain string (not an RDFNode)."""
    for prefix, ns in PREFIXES:
        if s.startswith(ns):
            return prefix + s[len(ns):]
    return f"<{s}>"


def _render_nodes(nodes: list, indent: int, hints: bool) -> str:
    lines = []
    pad = "   " * indent

    for node in nodes:
        if isinstance(node, LeafFailure):
            comp  = component_label(node.component).ljust(COMPONENT_WIDTH)
            path  = short_uri(node.result_path) if node.result_path else ""
            value = short_uri(node.value_node)  if node.value_node  else "(missing)"

            # main violation line
            lines.append(f"{pad}❌ {comp}  {path} = {value}")

            # message
            if node.message:
                lines.append(f"{pad}   {'':>{COMPONENT_WIDTH}}  {node.message}")

            # repair hint
            if hints:
                hint = repair_hint(node)
                if hint:
                    lines.append(f"{pad}   {'':>{COMPONENT_WIDTH}}  → fix: {hint}")

            # alt chains
            if node.alt_chains:
                for chain in node.alt_chains:
                    if chain:
                        lines.append(
                            f"{pad}   {'':>{COMPONENT_WIDTH}}  "
                            f"⎇  also via {format_chain(chain)}"
                        )

        else:   # ReferenceNode
            label = short_uri(node.source_shape)
            if node.result_path:
                label += f"  path={short_uri(node.result_path)}"

            lines.append(f"{pad}↳ sh:node {label}")
            lines.append(_render_nodes(node.children, indent + 1, hints))

    return "\n".join(lines)

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
    max_depth = max((len(l.ref_chain) for l in leaves), default=0)

    # counters
    leaf_paths = Counter(
        (short_uri(l.result_path) or "none",
         component_label(l.component))
        for l in leaves
    )
    leaf_components = Counter(component_label(l.component) for l in leaves)
    reference_paths = Counter(
        f"{short_uri(ref.result_path)} -> {short_uri(ref.source_shape)}"
        for ref in references
        if ref.result_path
    )

    direct   = sum(1 for l in leaves if not l.ref_chain)
    via_node = sum(1 for l in leaves if     l.ref_chain)

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
            writer.writerow({
                "focus_node": short_uri(leaf.focus_node),
                "depth": len(leaf.ref_chain),          
                "reference_chain": format_chain(leaf.ref_chain),
                "leaf_path": short_uri(leaf.result_path),
                "component": short_uri(leaf.component),
                "value": short_uri(leaf.value_node),
                "message": leaf.message or "",
                "kind": "referenced" if leaf.ref_chain else "direct",
                "repair_hint": repair_hint(leaf) or "",
            })
    finally:
        if close_after:
            destination.close()
def serialise_value(node):
    """Return a clean Python value for JSON — no RDF quoting."""
    if node is None:
        return None
    if isinstance(node, Literal):
        return str(node)        # "forty" not "\"forty\""
    return short_uri(node)

def to_json(nodes: list) -> str:
    def serialise(node):
        if isinstance(node, LeafFailure):

            d = {
                "type":       "leaf",
                "focusNode":  serialise_value(node.value_node),
                "path":       serialise_value(node.value_node) if node.result_path else None,
                "component":  serialise_value(node.value_node),
                "value":      serialise_value(node.value_node) if node.value_node else None,
                "message":    node.message,
                "repairHint": repair_hint(node),
                "refChain":   [short_uri(s) for s in node.ref_chain],
            }
        else:
            d = {
                "type":       "reference",
                "focusNode":  short_uri(node.focus_node),
                "shape":      short_uri(node.source_shape),
                "referencedShape": short_uri(node.referenced_shape) if node.referenced_shape else None,
                "path":       short_uri(node.result_path) if node.result_path else None,
                "refChain":   [short_uri(s) for s in node.ref_chain],
                "children":   [serialise(c) for c in node.children],
            }
        return {k: v for k, v in d.items() if v is not None}
    
    return json.dumps([serialise(n) for n in nodes], indent=2)
