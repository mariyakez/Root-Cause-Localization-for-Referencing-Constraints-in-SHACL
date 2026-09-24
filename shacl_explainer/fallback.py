# re-validation path for non-pyshacl reports
# For non-pyshacl engines where sh:detail is absent. This is where re-validation happens.

import pyshacl
from rdflib import BNode, Graph, Namespace, OWL, RDF, RDFS, URIRef

SH = Namespace("http://www.w3.org/ns/shacl#")

# Declarations that make a shape select focus nodes of its own. A copied shape
# must not keep them, or re-validation would check every node they select
# instead of the one node it was asked about.
TARGET_PREDICATES = {
    SH.targetClass, SH.targetNode, SH.targetSubjectsOf, SH.targetObjectsOf, SH.target,
}
IMPLICIT_CLASS_TARGETS = {RDFS.Class, OWL.Class}
SHAPE_TYPES = {SH.NodeShape, SH.PropertyShape}

def revalidate_against_shape(focus_node: URIRef,
                              shape_uri: URIRef,
                              data_graph: Graph,
                              shapes_graph: Graph,
                              namespaces=None):
    """
    Manually re-validate focus_node against shape_uri.
    Returns the fresh report_graph and its top-level ValidationResult nodes.
    Used only when sh:detail is absent (non-pyshacl engine output).
    """
    # Build a minimal shapes graph: copy just this shape + its dependencies
    targeted = build_targeted_shapes(shape_uri, shapes_graph, focus_node, namespaces)

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


class RevalidationCache:
    """Re-validation results by (target node, referenced shape), for one
    explanation build. Many sh:node results re-validate the same node against
    the same shape: a university named as the degree-granting institution of
    hundreds of people is re-validated once, not once per person. A report
    from re-validation is only read afterwards, never changed, so sharing it
    between results cannot alter an explanation.
    """

    def __init__(self, data_graph: Graph, shapes_graph: Graph):
        self.data_graph = data_graph
        self.shapes_graph = shapes_graph
        self.namespaces = list(shapes_graph.namespaces())
        self.entries = {}

    def __call__(self, focus_node, shape_uri):
        key = (focus_node, shape_uri)
        if key not in self.entries:
            self.entries[key] = revalidate_against_shape(
                focus_node, shape_uri, self.data_graph, self.shapes_graph, self.namespaces)
        return self.entries[key]


def build_targeted_shapes(shape_uri, shapes_graph, focus_node, namespaces=None):
    """
    Extract shape_uri and all shapes it references (transitively)
    into a new graph, then add a sh:targetNode triple pointing at focus_node.
    The copies drop their own targets, including the implicit class target of
    a shape that is also a class, so pyshacl validates only the node we care
    about. The prefixes of the shapes graph are bound as well, so that the
    messages pyshacl writes name terms as they do in the original report.
    """
    targeted = Graph()
    for prefix, namespace in (namespaces if namespaces is not None else shapes_graph.namespaces()):
        targeted.bind(prefix, namespace, override=True, replace=True)
    _copy_shape_recursive(shape_uri, shapes_graph, targeted, set())
    targeted.add((shape_uri, SH.targetNode, focus_node))
    return targeted


def _copy_shape_recursive(shape, source, target, visited):
    """Copy a shape with everything its constraints need, at any depth: every
    blank node below it, which covers its property shapes, complex paths and
    the RDF lists of sh:in, sh:or, sh:and, sh:xone and sh:languageIn, and
    every named shape it refers to, through sh:node on a property shape as
    much as on the shape itself. A copy that stopped short would leave pyshacl
    an empty sh:in list, which every value fails, or a sh:node to a shape it
    cannot see, which every value passes."""
    if shape in visited:
        return
    visited.add(shape)
    for triple in source.triples((shape, None, None)):
        if _selects_targets(triple):
            continue
        target.add(triple)
        obj = triple[2]
        if isinstance(obj, BNode) or _is_named_shape(obj, source):
            _copy_shape_recursive(obj, source, target, visited)


def _is_named_shape(node, graph):
    return isinstance(node, URIRef) and (
        any((node, RDF.type, shape_type) in graph for shape_type in SHAPE_TYPES)
        or any((node, predicate, None) in graph for predicate in (SH.property, SH.path, SH.node))
    )


def _selects_targets(triple):
    _, predicate, obj = triple
    return predicate in TARGET_PREDICATES or (predicate == RDF.type and obj in IMPLICIT_CLASS_TARGETS)
