# walks sh:detail recursively, builds the tree, accumulating the reference chain.

from types import SimpleNamespace

from rdflib import BNode, Graph, Namespace, RDF, RDFS
from .tree import LeafFailure, ReferenceNode

SH = Namespace("http://www.w3.org/ns/shacl#")

# Notes attached to a validator's own sh:node result when re-validation cannot
# break it down into a concrete failure.
NOTE_NOT_REPRODUCED = (
    "reported by the validator, but re-validation against the referenced "
    "shape found no violation to explain it"
)
NOTE_NO_VALUE = (
    "the report gives no sh:value and the reported path leads to no value, "
    "so there was nothing to re-validate"
)

def stable_key(node, graph: Graph, depth: int = 0) -> str:
    """A sort key for an RDF term that does not depend on rdflib's iteration
    order. IRIs and literals sort by their text. A blank node's label is minted
    afresh on every parse, so it sorts by the triples it has in graph instead,
    to a small depth; blank nodes that carry no triples, such as the fresh
    sh:sourceShape of a Jena or TopBraid report, sort equal."""
    if node is None:
        return ""
    if not isinstance(node, BNode):
        return str(node)
    if depth >= 4:
        return "_:"
    parts = sorted(f"{p} {stable_key(o, graph, depth + 1)}"
                   for p, o in graph.predicate_objects(node))
    return "_:[" + "; ".join(parts) + "]"

def sort_results(results, report_graph: Graph) -> list:
    """Results in an order fixed by their content rather than by the order in
    which the validator or rdflib yields them. Deduplication keeps the first
    occurrence of a leaf, so this order decides which root holds a shared leaf
    and which of its chains is primary; fixing it makes the output the same on
    every run. Referenced-shape results come first, as before."""
    return [result for result, _ in sort_result_pairs((r, report_graph) for r in results)]

# The fields that order results, by position in the sort key. Looked up once
# here: rdflib resolves every SH.name attribute afresh, which is measurable
# across a million results.
_FOCUS_NODE, _RESULT_PATH, _VALUE = SH.focusNode, SH.resultPath, SH.value
_COMPONENT, _SOURCE_SHAPE = SH.sourceConstraintComponent, SH.sourceShape
_KEY_FIELDS = {_FOCUS_NODE: 0, _RESULT_PATH: 1, _COMPONENT: 2, _VALUE: 3}
_NODE_COMPONENT = str(SH.NodeConstraintComponent)

def sort_result_pairs(pairs) -> list:
    """(result, graph) pairs in the order of sort_results, for results drawn
    from several graphs, such as the reports of several re-validations that
    together stand in for one result's sh:detail."""
    pairs = list(pairs)
    if len(pairs) < 2:
        # Most sh:detail lists hold a single result; there is nothing to order.
        return pairs

    def key(pair):
        result, graph = pair
        # One pass over the result's triples rather than a lookup per field.
        fields = [None, None, None, None]
        for predicate, obj in graph.predicate_objects(result):
            index = _KEY_FIELDS.get(predicate)
            if index is not None and fields[index] is None:
                fields[index] = obj
        focus, path, component, value = fields
        return (
            str(component) != _NODE_COMPONENT,
            stable_key(focus, graph),
            stable_key(path, graph),
            str(component),
            stable_key(value, graph),
        )

    def tie_break(pair):
        # Rare ties are broken by the source shape, whose key is costlier to
        # compute, then by message and severity.
        result, graph = pair
        return (
            stable_key(graph.value(result, SH.sourceShape), graph),
            sorted(str(m) for m in graph.objects(result, SH.resultMessage)),
            str(graph.value(result, SH.resultSeverity)),
        )

    keyed = sorted(((key(pair), pair) for pair in pairs), key=lambda item: item[0])
    ordered = []
    i = 0
    while i < len(keyed):
        j = i
        while j < len(keyed) and keyed[j][0] == keyed[i][0]:
            j += 1
        group = [pair for _, pair in keyed[i:j]]
        if len(group) > 1:
            group.sort(key=tie_break)
        ordered.extend(group)
        i = j
    return ordered

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
    if len(values) > 1:
        values.sort(key=lambda value: stable_key(value, shapes_graph))
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

def property_shapes_by_path(result_path, report_graph: Graph, shapes_graph: Graph):
    """Every property shape in either graph whose sh:path is result_path."""
    if result_path is None:
        return []

    found = {}
    for graph in (report_graph, shapes_graph):
        for prop_shape in graph.subjects(SH.path, result_path):
            found.setdefault(str(prop_shape), prop_shape)
    return [found[key] for key in sorted(found)]

def references_directly(source_shape, result_path, report_graph: Graph, shapes_graph: Graph):
    """The referenced shapes reachable from sh:sourceShape itself: either it
    declares sh:node, or it is a node shape whose property shape on the
    reported path does."""
    direct = values_from_graphs(source_shape, SH.node, report_graph, shapes_graph)
    if direct:
        return direct

    # Some reports set sh:sourceShape to the enclosing node shape and
    # sh:resultPath to the failing property. Recover the referenced shape from
    # the matching property shape in the original shapes graph.
    referenced = []
    for prop_shape in property_shapes_for(source_shape, result_path, report_graph, shapes_graph):
        referenced.extend(values_from_graphs(prop_shape, SH.node, report_graph, shapes_graph))
    return referenced

def is_instance_of(node, cls, data_graph: Graph):
    """SHACL instance: rdf:type followed by rdfs:subClassOf* in the data graph."""
    return any(cls in data_graph.transitive_objects(node_type, RDFS.subClassOf)
               for node_type in data_graph.objects(node, RDF.type))

def shape_targets_node(shape, focus, data_graph: Graph, shapes_graph: Graph):
    """True if a SHACL Core target of shape selects focus. A shape with a
    target this cannot evaluate (a SPARQL-based sh:target) is assumed to
    apply, so that uncertainty never discards a real failure."""
    if (shape, SH.target, None) in shapes_graph:
        return True
    if (shape, SH.targetNode, focus) in shapes_graph:
        return True
    classes = list(shapes_graph.objects(shape, SH.targetClass))
    if (shape, RDF.type, RDFS.Class) in shapes_graph:
        classes.append(shape)
    if any(is_instance_of(focus, cls, data_graph) for cls in classes):
        return True
    if any((focus, prop, None) in data_graph
           for prop in shapes_graph.objects(shape, SH.targetSubjectsOf)):
        return True
    return any((None, prop, focus) in data_graph
               for prop in shapes_graph.objects(shape, SH.targetObjectsOf))

def declared_severity(prop_shape, shapes_graph: Graph):
    return shapes_graph.value(prop_shape, SH.severity) or SH.Violation

def pair_results_with_candidates(group, candidates, report_graph: Graph, shapes_graph: Graph):
    """Assign each result of group at most one candidate property shape.

    A result goes to the one candidate whose declared metadata it carries:
    a matching severity, and where declared, the exact sh:message, which
    validators copy into sh:resultMessage. Results left over are then paired
    with the candidates left over, one to one, when the counts agree. Such
    results agree on everything the explanation displays, since the message
    of a reference step is not rendered, so the order of pairing does not
    change the output.
    """
    remaining = list(candidates)
    assignment = {}
    unmatched = []
    for result in group:
        severity = report_graph.value(result, SH.resultSeverity) or SH.Violation
        messages = {str(m) for m in report_graph.objects(result, SH.resultMessage)}
        compatible = [c for c in remaining if declared_severity(c, shapes_graph) == severity]
        by_message = [c for c in compatible
                      if messages & {str(m) for m in shapes_graph.objects(c, SH.message)}]
        if len(by_message) == 1:
            choice = by_message[0]
        elif len(compatible) == 1:
            choice = compatible[0]
        else:
            unmatched.append(result)
            continue
        assignment[result] = choice
        remaining.remove(choice)

    if unmatched and len(unmatched) == len(remaining):
        assignment.update(zip(unmatched, remaining))
    return assignment

def property_shapes_for_unresolved(result_node, result_path, report_graph: Graph,
                                   data_graph: Graph, shapes_graph: Graph):
    """The property shapes that can have produced a property-level sh:node
    result whose sh:sourceShape identifies nothing in the shapes graph.

    Apache Jena and TopBraid identify such a result by its property shape,
    which is usually anonymous, so the blank node in sh:sourceShape is fresh
    and the reported path is the only remaining link back to the constraint.
    The path alone can match property shapes that never applied, so the
    candidates are narrowed in turn by targeting, by evidence and by the
    result's declared metadata or, failing that, by pairing. A stage that
    would rule out every candidate is skipped rather than explain nothing.
    """
    candidates = sorted(
        (prop_shape
         for prop_shape in property_shapes_by_path(result_path, report_graph, shapes_graph)
         if values_from_graphs(prop_shape, SH.node, report_graph, shapes_graph)),
        key=lambda prop_shape: (
            sorted(str(s) for s in values_from_graphs(prop_shape, SH.node, report_graph, shapes_graph)),
            str(owner_shape_for_property_shape(prop_shape, report_graph, shapes_graph)),
        ),
    )
    if len(candidates) <= 1 or data_graph is None:
        return candidates

    focus = report_graph.value(result_node, SH.focusNode)
    value = report_graph.value(result_node, SH.value)

    # A result read from the report came from a shape that targets its focus
    # node, so a property shape whose owner does not was never evaluated.
    candidates = [
        prop_shape for prop_shape in candidates
        if shape_targets_node(prop_shape, focus, data_graph, shapes_graph)
        or shape_targets_node(owner_shape_for_property_shape(prop_shape, report_graph, shapes_graph),
                              focus, data_graph, shapes_graph)
    ] or candidates

    # An sh:node violation means the value fails the referenced shape, so a
    # candidate whose referenced shapes the value satisfies cannot be the one.
    # These probes call the validator directly rather than through the build's
    # RevalidationCache, so they are not shared with the re-validations that
    # rebuild the explanation. The step only runs where several property shapes
    # declare sh:node on one reported path, which no LUBM schema does, so it
    # costs nothing in the measurements of Chapter 5; routing it through the
    # cache would be the fix if a schema ever made it hot.
    if len(candidates) > 1 and value is not None:
        from .fallback import revalidate_against_shape
        candidates = [
            prop_shape for prop_shape in candidates
            if any(revalidate_against_shape(value, shape, data_graph, shapes_graph)[1]
                   for shape in values_from_graphs(prop_shape, SH.node, report_graph, shapes_graph))
        ] or candidates

    if len(candidates) <= 1:
        return candidates

    # Several candidates remain. The other results for the same focus node,
    # path and value that are equally unresolved compete for them.
    group = sorted(
        (other for other in report_graph.subjects(SH.focusNode, focus)
         if report_graph.value(other, SH.resultPath) == result_path
         and report_graph.value(other, SH.value) == value
         and report_graph.value(other, SH.sourceConstraintComponent) == SH.NodeConstraintComponent
         and not references_directly(report_graph.value(other, SH.sourceShape), result_path,
                                     report_graph, shapes_graph)),
        key=lambda other: (
            sorted(str(m) for m in report_graph.objects(other, SH.resultMessage)),
            str(report_graph.value(other, SH.resultSeverity)),
            str(other),
        ),
    )
    assignment = pair_results_with_candidates(group, candidates, report_graph, shapes_graph)
    if result_node in assignment:
        return [assignment[result_node]]
    return candidates

def referenced_shapes_for(result_node, source_shape, result_path, report_graph: Graph,
                          data_graph: Graph | None, shapes_graph: Graph):
    referenced = references_directly(source_shape, result_path, report_graph, shapes_graph)
    if referenced:
        return referenced

    candidates = property_shapes_for_unresolved(
        result_node, result_path, report_graph, data_graph, shapes_graph)
    for prop_shape in candidates:
        referenced.extend(values_from_graphs(prop_shape, SH.node, report_graph, shapes_graph))
    return referenced

def shapes_owning_details(result_node, report_graph: Graph, shapes_graph: Graph):
    """The declaring shapes of a node-level result's own sh:detail children.

    A shape that declares several sh:node references is reported once per
    reference, and each result carries only the details that its one referenced
    shape produced. A detail that is itself a node constraint names that shape
    in sh:sourceShape; a detail reporting a property failure names an anonymous
    property shape the same shape owns. Either way the child leads back to the
    reference its parent result travelled.
    """
    owners = set()
    for detail in report_graph.objects(result_node, SH.detail):
        source = report_graph.value(detail, SH.sourceShape)
        if source is not None:
            owners.add(str(owner_shape_for_property_shape(source, report_graph, shapes_graph)))
    return owners

def attributed_reference_shape(referenced_shapes, result_node,
                               report_graph: Graph, shapes_graph: Graph):
    """Which of a step's referenced shapes this result reached its failures
    through.

    With a single candidate there is nothing to decide. With several -- a
    diamond -- the first is not the answer: the reference travelled is the one
    the result's own sh:detail children belong to. Where the children do not
    settle it, or there are none, as on the fallback path of
    Section~\ref{sec:external-reports-and-the-fallback-path}, the step records
    no referenced shape rather than a guess. The value is not cosmetic: it
    reaches the reader in the JSON output, in the per-leaf row and shape chain
    of the HTML report, and in the referenced_shape column of its CSV export.
    """
    if not referenced_shapes:
        return None
    if len(referenced_shapes) == 1:
        return referenced_shapes[0]

    owners = shapes_owning_details(result_node, report_graph, shapes_graph)
    attributed = [shape for shape in referenced_shapes if str(shape) in owners]
    return attributed[0] if len(attributed) == 1 else None

# The parameter each of these components declares in its shape. Components not
# listed here are reported in full but carry no parameterised repair hint.
COMPONENT_PARAMETER = {
    SH.MinCountConstraintComponent: SH.minCount,
    SH.MaxCountConstraintComponent: SH.maxCount,
    SH.DatatypeConstraintComponent: SH.datatype,
    SH.ClassConstraintComponent:    SH["class"],
    SH.PatternConstraintComponent:  SH.pattern,
    SH.InConstraintComponent:       SH["in"],
}

def rdf_list(head, report_graph: Graph, shapes_graph: Graph) -> list:
    """The members of an RDF collection, read from whichever graph carries it."""
    graph = report_graph if (head, RDF.first, None) in report_graph else shapes_graph
    try:
        return list(graph.items(head))
    except Exception:
        return []

def declared_parameter(shape, predicate, report_graph: Graph, shapes_graph: Graph):
    """The value a shape declares for one constraint parameter, with the
    members of sh:in resolved, so that nothing downstream reads a graph."""
    declared = shape_value(shape, predicate, report_graph, shapes_graph)
    if declared is None:
        return None
    return rdf_list(declared, report_graph, shapes_graph) if predicate == SH["in"] else declared

def parameter_key(value):
    return tuple(str(member) for member in value) if isinstance(value, list) else str(value)

def constraint_parameter(component, source_shape, result_path,
                         report_graph: Graph, shapes_graph: Graph):
    """What the shape requires of the values it rejected, for a repair hint.

    The shape named by sh:sourceShape declares it, which settles the case for
    pySHACL, whose reports identify the property shape itself. Apache Jena and
    TopBraid instead report an anonymous property shape as a fresh blank node
    that matches nothing in either graph, exactly as in
    property_shapes_for_unresolved, so the reported path is again the only link
    back to the constraint. The path alone can reach several property shapes,
    and this function is not free to guess: a wrong parameter would put a
    concrete but false requirement in front of the reader. The value is
    therefore taken only where every property shape on the path agrees on it,
    and a disagreement leaves the hint unparameterised.
    """
    predicate = COMPONENT_PARAMETER.get(component)
    if predicate is None:
        return None

    declared = declared_parameter(source_shape, predicate, report_graph, shapes_graph)
    if declared is not None:
        return declared

    candidates = [
        value for value in (
            declared_parameter(prop_shape, predicate, report_graph, shapes_graph)
            for prop_shape in property_shapes_by_path(result_path, report_graph, shapes_graph)
        ) if value is not None
    ]
    if not candidates:
        return None
    first = candidates[0]
    return first if all(parameter_key(c) == parameter_key(first) for c in candidates) else None

def as_int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None

def existing_value_count(component, parameter, focus, result_path,
                        report_graph: Graph, data_graph: Graph, shapes_graph: Graph):
    """How many values the focus node has on the failing path, where a hint
    needs it, and None otherwise.

    Only a minimum above one needs it: at a minimum of one "add at least one
    value" is already exact, and a maximum is stated against its own bound
    rather than against the current count. That matters at scale, because this
    evaluates the path against the data graph once per leaf, and the large
    graphs of Chapter 5 produce tens of thousands of count failures, nearly all
    of them against a minimum or maximum this rule skips.
    """
    if component != SH.MinCountConstraintComponent:
        return None
    minimum = as_int(parameter)
    if minimum is None or minimum <= 1:
        return None
    return len(values_along_path(focus, result_path, report_graph, data_graph, shapes_graph))

def result_message(result_node, report_graph: Graph):
    """Every sh:resultMessage of a result, sorted and joined.

    A shape may declare several sh:message values, one per language for
    instance, and the report then carries them all. Reading only one would
    pick whichever rdflib happens to yield first, which varies between runs.
    """
    messages = sorted({str(m) for m in report_graph.objects(result_node, SH.resultMessage)})
    return " | ".join(messages) if messages else None

def values_along_path(focus, result_path, report_graph: Graph,
                      data_graph: Graph, shapes_graph: Graph) -> list:
    """The value nodes reached from focus along result_path in the data graph,
    for a property-level result whose report omits sh:value. A complex path is
    a blank-node structure, read from whichever graph carries it."""
    from pyshacl.helper.expression_helper import value_nodes_from_path

    if focus is None or result_path is None:
        return []
    path_graph = report_graph if (result_path, None, None) in report_graph else shapes_graph
    try:
        values = value_nodes_from_path(
            SimpleNamespace(graph=path_graph), focus, result_path, data_graph)
    except Exception:
        return []
    return sorted(values, key=lambda value: stable_key(value, data_graph))

def display_reference_shape(result_node, source_shape, report_graph: Graph, shapes_graph: Graph,
                            data_graph: Graph | None = None):
    result_path = result_path_for(result_node, source_shape, report_graph, shapes_graph)

    referenced_shapes = referenced_shapes_for(
        result_node, source_shape, result_path, report_graph, data_graph, shapes_graph)
    referenced_shape = attributed_reference_shape(
        referenced_shapes, result_node, report_graph, shapes_graph)

    # For property-level sh:node, showing the referenced shape plus path is
    # clearer (e.g. "via CompanyShape path=worksFor"). For node-level sh:node,
    # preserve the outer source shape so multi-level chains remain visible.
    display_shape = referenced_shape if result_path is not None and referenced_shape else source_shape
    # referenced_shapes is returned whole, and separately: the fallback path
    # re-validates against every reference the step could have travelled, so
    # narrowing that list would drop the subtrees of the ones left out.
    return display_shape, referenced_shape, referenced_shapes, result_path

def expand_result(result_node, report_graph: Graph,
                  data_graph: Graph, shapes_graph: Graph,
                  ref_chain: list, visited: set,
                  revalidate=None) -> ReferenceNode | LeafFailure:
    """
    Recursively expand one ValidationResult into the explanation tree.
    ref_chain accumulates the shapes traversed to reach this result.
    visited guards against cycles on the current traversal path.
    revalidate re-validates a node against a shape for the fallback path; a
    RevalidationCache shares the work across one build, and without one each
    call re-validates afresh.
    """
    # Read the result's fields in one pass rather than one lookup per field.
    fields = {}
    for predicate, obj in report_graph.predicate_objects(result_node):
        fields.setdefault(predicate, obj)
    get = fields.get

    focus     = get(_FOCUS_NODE)
    value     = get(_VALUE)
    component = get(_COMPONENT)
    shape     = get(_SOURCE_SHAPE)
    message   = result_message(result_node, report_graph)

    if str(component) != _NODE_COMPONENT:
        # Base case — this is a leaf. Read what the constraint requires before
        # the source shape is resolved to its owner, since the parameter is
        # declared on the property shape rather than on the node shape holding
        # it, and the owner is kept only to give the chain a readable name.
        leaf_path = get(_RESULT_PATH)
        parameter = constraint_parameter(component, shape, leaf_path,
                                         report_graph, shapes_graph)
        leaf_shape = owner_shape_for_property_shape(shape, report_graph, shapes_graph)
        return LeafFailure(
            focus_node   = focus,
            value_node   = value,
            result_path  = leaf_path,
            component    = component,
            source_shape = leaf_shape,
            message      = message,
            ref_chain    = ref_chain.copy(),
            parameter    = parameter,
            value_count  = existing_value_count(component, parameter, focus, leaf_path,
                                                report_graph, data_graph, shapes_graph),
        )

    # Recursive case — NodeConstraintComponent
    display_shape, referenced_shape, referenced_shapes, result_path = display_reference_shape(
        result_node, shape, report_graph, shapes_graph, data_graph)
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
        message      = message,
        ref_chain    = ref_chain.copy(),
    )

    details = sort_results(report_graph.objects(result_node, SH.detail), report_graph)

    if details:
        # pyshacl path — walk sh:detail children
        for detail in details:
            child = expand_result(detail, report_graph,
                                  data_graph, shapes_graph,
                                  ref_chain + [display_shape], branch_visited,
                                  revalidate)
            if child:
                node.children.append(child)
    else:
        # Fallback path — non-pyshacl engine, no sh:detail present
        if revalidate is None:
            from .fallback import revalidate_against_shape
            revalidate = lambda node, shape: revalidate_against_shape(
                node, shape, data_graph, shapes_graph)
        # For property-level sh:node, the referenced shape is applied to the
        # value node. A report that omits sh:value leaves the values to be
        # found along the reported path; the focus node is never substituted,
        # since it is not the node the constraint was checked on. For
        # node-level sh:node, the focus node is the target.
        if result_path is None:
            targets = [focus]
        elif value is not None:
            targets = [value]
        else:
            targets = values_along_path(focus, result_path, report_graph,
                                        data_graph, shapes_graph)

        # The results of every re-validation stand in for this result's
        # sh:detail together, so they are ordered together, as sh:detail is.
        rebuilt = []
        for candidate_shape in referenced_shapes or [display_shape]:
            for target_node in targets:
                fallback_report, fallback_results = revalidate(target_node, candidate_shape)
                rebuilt.extend((fr, fallback_report) for fr in fallback_results)
        reproduced = bool(rebuilt)
        for fr, fallback_report in sort_result_pairs(rebuilt):
            child = expand_result(fr, fallback_report,
                                  data_graph, shapes_graph,
                                  ref_chain + [display_shape], branch_visited,
                                  revalidate)
            if child:
                node.children.append(child)

        if not reproduced:
            # The validator reported a violation that re-validation cannot
            # break down. Keep the validator's own result, marked as such,
            # rather than let the step vanish from the explanation.
            node.children.append(LeafFailure(
                focus_node   = focus,
                value_node   = value,
                result_path  = result_path,
                component    = SH.NodeConstraintComponent,
                source_shape = display_shape,
                message      = message,
                ref_chain    = ref_chain + [display_shape],
                note         = NOTE_NOT_REPRODUCED if targets else NOTE_NO_VALUE,
            ))

    return node


def build_explanation_tree(report_graph: Graph,
                            data_graph: Graph,
                            shapes_graph: Graph,
                            cache_revalidation: bool = True):
    from .parser import get_top_level_results
    from .deduplicator import deduplicate
    from .fallback import RevalidationCache

    top_results = sort_results(get_top_level_results(report_graph), report_graph)
    revalidate = RevalidationCache(data_graph, shapes_graph) if cache_revalidation else None
    roots = []

    for result in top_results:
        tree = expand_result(result, report_graph,
                             data_graph, shapes_graph,
                             ref_chain=[], visited=set(),
                             revalidate=revalidate)
        if tree:
            roots.append(tree)

    return deduplicate(roots)
