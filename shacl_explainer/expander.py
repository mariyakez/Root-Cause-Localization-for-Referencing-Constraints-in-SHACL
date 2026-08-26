# walks sh:detail recursively, builds the tree, accumulating the reference chain.

from rdflib import Graph, Namespace
from .tree import LeafFailure, ReferenceNode, RDFNode

SH = Namespace("http://www.w3.org/ns/shacl#")

def shape_value(node, predicate, report_graph: Graph, shapes_graph: Graph):
    return (
        report_graph.value(node, predicate)
        or shapes_graph.value(node, predicate)
    )

def values_from_graphs(node, predicate, report_graph: Graph, shapes_graph: Graph):
    seen = set()
    values = []
    for graph in (report_graph, shapes_graph):
        for value in graph.objects(node, predicate):
            key = str(value)
            if key not in seen:
                seen.add(key)
                values.append(value)
    return values

def result_path_for(result_node, source_shape, report_graph: Graph, shapes_graph: Graph):
    return (
        report_graph.value(result_node, SH.resultPath)
        or shape_value(source_shape, SH.path, report_graph, shapes_graph)
    )

def property_shapes_for(source_shape, result_path, report_graph: Graph, shapes_graph: Graph):
    if result_path is None:
        return []

    candidates = []
    for prop_shape in values_from_graphs(source_shape, SH.property, report_graph, shapes_graph):
        prop_path = shape_value(prop_shape, SH.path, report_graph, shapes_graph)
        if prop_path == result_path:
            candidates.append(prop_shape)
    return candidates

def owner_shape_for_property_shape(property_shape, report_graph: Graph, shapes_graph: Graph):
    for graph in (report_graph, shapes_graph):
        owner = graph.value(predicate=SH.property, object=property_shape)
        if owner is not None:
            return owner
    return property_shape

def referenced_shapes_for(source_shape, result_path, report_graph: Graph, shapes_graph: Graph):
    direct = values_from_graphs(source_shape, SH.node, report_graph, shapes_graph)
    if direct:
        return direct

    # Jena-style reports may set sh:sourceShape to the enclosing node shape
    # and sh:resultPath to the failing property. Recover the referenced shape
    # from the matching property shape in the original shapes graph.
    referenced = []
    for prop_shape in property_shapes_for(source_shape, result_path, report_graph, shapes_graph):
        referenced.extend(values_from_graphs(prop_shape, SH.node, report_graph, shapes_graph))
    return referenced

def display_reference_shape(result_node, source_shape, report_graph: Graph, shapes_graph: Graph):
    result_path = result_path_for(result_node, source_shape, report_graph, shapes_graph)
    referenced_shape = None

    referenced_shapes = referenced_shapes_for(
        source_shape, result_path, report_graph, shapes_graph)
    if referenced_shapes:
        referenced_shape = referenced_shapes[0]

    # For property-level sh:node, showing the referenced shape plus path is
    # clearer (e.g. "via CompanyShape path=worksFor"). For node-level sh:node,
    # preserve the outer source shape so multi-level chains remain visible.
    display_shape = referenced_shape if result_path is not None and referenced_shape else source_shape
    return display_shape, referenced_shape, result_path

def expand_result(result_node, report_graph: Graph,
                  data_graph: Graph, shapes_graph: Graph,
                  ref_chain: list, visited: set) -> ReferenceNode | LeafFailure:
    """
    Recursively expand one ValidationResult into the explanation tree.
    ref_chain accumulates the shapes traversed to reach this result.
    visited guards against cycles on the current traversal path.
    """
    get = lambda p: report_graph.value(result_node, p)

    focus     = get(SH.focusNode)
    value     = get(SH.value)
    component = get(SH.sourceConstraintComponent)
    shape     = get(SH.sourceShape)
    message   = get(SH.resultMessage)

    if str(component) != str(SH.NodeConstraintComponent):
        leaf_shape = owner_shape_for_property_shape(shape, report_graph, shapes_graph)
        # Base case — this is a leaf
        return LeafFailure(
            focus_node   = focus,
            value_node   = get(SH.value),
            result_path  = get(SH.resultPath),
            component    = component,
            source_shape = leaf_shape,
            message      = str(message) if message else None,
            ref_chain    = ref_chain.copy(),
        )

    # Recursive case — NodeConstraintComponent
    display_shape, referenced_shape, result_path = display_reference_shape(
        result_node, shape, report_graph, shapes_graph)
    # Use a path-insensitive key for the current traversal branch. Sibling
    # references get independent visited sets, but a cycle that reaches the
    # same focus/shape through another property path is still stopped.
    visit_key = (str(focus), str(display_shape))
    if visit_key in visited:
        return None               # cycle guard
    branch_visited = visited | {visit_key}

    node = ReferenceNode(
        focus_node   = focus,
        source_shape = display_shape,
        referenced_shape = referenced_shape,
        result_path  = result_path,
        message      = str(message) if message else None,
        ref_chain    = ref_chain.copy(),
    )

    details = list(report_graph.objects(result_node, SH.detail))

    if details:
        # pyshacl path — walk sh:detail children
        for detail in details:
            child = expand_result(detail, report_graph,
                                  data_graph, shapes_graph,
                                  ref_chain + [display_shape], branch_visited)
            if child:
                node.children.append(child)
    else:
        # Fallback path — non-pyshacl engine, no sh:detail present
        from .fallback import revalidate_against_shape
        referenced_shapes = referenced_shapes_for(
            shape, result_path, report_graph, shapes_graph)
        if not referenced_shapes:
            referenced_shapes = [display_shape]

        for referenced_shape in referenced_shapes:
            # For property-level sh:node, the referenced shape is applied to
            # sh:value. For node-level sh:node, sh:value is often absent or the
            # same as the focus node, so the focus node is the target.
            target_node = value if result_path is not None and value is not None else focus
            fallback_report, fallback_results = revalidate_against_shape(
                target_node, referenced_shape, data_graph, shapes_graph)
            for fr in fallback_results:
                child = expand_result(fr, fallback_report,
                                      data_graph, shapes_graph,
                                      ref_chain + [display_shape], branch_visited)
                if child:
                    node.children.append(child)

    return node


def build_explanation_tree(report_graph: Graph,
                            data_graph: Graph,
                            shapes_graph: Graph):
    from .parser import get_top_level_results
    from .deduplicator import deduplicate

    top_results = get_top_level_results(report_graph)
    top_results.sort(
        key=lambda result: str(
            report_graph.value(result, SH.sourceConstraintComponent)
        ) != str(SH.NodeConstraintComponent)
    )
    roots = []

    for result in top_results:
        tree = expand_result(result, report_graph,
                             data_graph, shapes_graph,
                             ref_chain=[], visited=set())
        if tree:
            roots.append(tree)

    return deduplicate(roots)
