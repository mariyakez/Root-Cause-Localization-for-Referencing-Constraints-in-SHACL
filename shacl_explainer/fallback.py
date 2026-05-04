# re-validation path for non-pyshacl reports
# For non-pyshacl engines where sh:detail is absent. This is where re-validation happens.

import pyshacl
from rdflib import Graph, Namespace, RDF, URIRef

SH = Namespace("http://www.w3.org/ns/shacl#")

def revalidate_against_shape(focus_node: URIRef,
                              shape_uri: URIRef,
                              data_graph: Graph,
                              shapes_graph: Graph):
    """
    Manually re-validate focus_node against shape_uri.
    Returns the fresh report_graph and its top-level ValidationResult nodes.
    Used only when sh:detail is absent (non-pyshacl engine output).
    """
    # Build a minimal shapes graph: copy just this shape + its dependencies
    targeted = build_targeted_shapes(shape_uri, shapes_graph, focus_node)

    _, report, _ = pyshacl.validate(
        data_graph,
        shacl_graph=targeted,
        inference="none",
        abort_on_first=False,
        serialize_report_graph=False,
    )

    report_node = report.value(predicate=RDF.type,
                               object=SH.ValidationReport)
    return report, list(report.objects(report_node, SH.result))


def build_targeted_shapes(shape_uri, shapes_graph, focus_node):
    """
    Extract shape_uri and all shapes it references (transitively)
    into a new graph, then add a sh:target triple pointing at focus_node.
    This ensures pyshacl validates only the node we care about.
    """
    targeted = Graph()
    _copy_shape_recursive(shape_uri, shapes_graph, targeted, set())
    targeted.add((shape_uri, SH.targetNode, focus_node))
    return targeted


def _copy_shape_recursive(shape, source, target, visited):
    if str(shape) in visited:
        return
    visited.add(str(shape))
    for triple in source.triples((shape, None, None)):
        target.add(triple)
        if triple[1] == SH.node:
            _copy_shape_recursive(triple[2], source, target, visited)
        if triple[1] == SH.property:
            for prop_triple in source.triples((triple[2], None, None)):
                target.add(prop_triple)
