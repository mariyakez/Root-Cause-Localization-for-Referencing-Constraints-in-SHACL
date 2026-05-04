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

def to_text_tree(nodes: list, indent=0, hints=False) -> str:
    lines = []
    pad = "   " * indent
    for node in nodes:
        if isinstance(node, LeafFailure):
            comp = component_label(node.component)
            line = f"{pad}❌ [{comp}]"
            if node.result_path:
                line += f"  path={short_uri(node.result_path)}"
            if node.value_node:
                line += f"  value={short_uri(node.value_node)}"
            if node.message:
                line += f"\n{pad}   → {node.message}"
            if hints:
                hint = repair_hint(node)
                if hint:
                    line += f"\n{pad}   repair: {hint}"
            if hasattr(node, 'alt_chains') and node.alt_chains:
                chains = [
                    format_chain(chain)
                    for chain in node.alt_chains
                    if chain
                ]
                if chains:
                    line += f"\n{pad}   (also reachable via {', '.join(chains)})"
            lines.append(line)
        else:
            label = short_uri(node.source_shape)
            if node.result_path:
                label += f"  path={short_uri(node.result_path)}"
            if indent == 0 and node.focus_node:
                label += f"  focus={short_uri(node.focus_node)}"
            lines.append(f"{pad}via {label}")
            lines.append(to_text_tree(node.children, indent + 1, hints=hints))
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
    leaves = list(iter_leaves(nodes))
    references = list(iter_references(nodes))

    leaf_paths = Counter(short_uri(leaf.result_path) or "none" for leaf in leaves)
    leaf_components = Counter(component_label(leaf.component) for leaf in leaves)
    reference_paths = Counter(
        f"{short_uri(ref.result_path)} -> {short_uri(ref.source_shape)}"
        for ref in references
        if ref.result_path
    )

    lines = [
        f"Explanation roots: {len(nodes)}",
        f"Reference nodes: {len(references)}",
        f"Leaf failures: {len(leaves)}",
        f"Referenced leaf failures: {sum(1 for leaf in leaves if leaf.ref_chain)}",
        f"Direct leaf failures: {sum(1 for leaf in leaves if not leaf.ref_chain)}",
    ]

    if stats:
        lines.extend([
            f"Data triples: {stats.get('data_triples', 0)}",
            f"Shape triples: {stats.get('shape_triples', 0)}",
            f"Top-level validation results: {stats.get('top_results', 0)}",
            f"All validation results: {stats.get('all_results', 0)}",
        ])

    def add_counter(title, counter):
        lines.append("")
        lines.append(title)
        if not counter:
            lines.append("  none")
            return
        for key, count in counter.most_common(top):
            lines.append(f"  {count:>5}  {key}")

    add_counter("By leaf path:", leaf_paths)
    add_counter("By leaf component:", leaf_components)
    add_counter("By reference path:", reference_paths)

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

def to_json(nodes: list) -> str:
    def serialise(node):
        if isinstance(node, LeafFailure):
            return {
                "type":       "leaf",
                "focusNode":  short_uri(node.focus_node),
                "path":       short_uri(node.result_path) if node.result_path else None,
                "component":  short_uri(node.component),
                "value":      short_uri(node.value_node) if node.value_node else None,
                "message":    node.message,
                "repairHint": repair_hint(node),
                "refChain":   [short_uri(s) for s in node.ref_chain],
            }
        else:
            return {
                "type":       "reference",
                "focusNode":  short_uri(node.focus_node),
                "shape":      short_uri(node.source_shape),
                "referencedShape": short_uri(node.referenced_shape) if node.referenced_shape else None,
                "path":       short_uri(node.result_path) if node.result_path else None,
                "refChain":   [short_uri(s) for s in node.ref_chain],
                "children":   [serialise(c) for c in node.children],
            }
    return json.dumps([serialise(n) for n in nodes], indent=2)
