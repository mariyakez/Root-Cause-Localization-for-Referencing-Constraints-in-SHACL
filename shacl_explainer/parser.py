 # reads report_graph, extracts top-level results
#Extract only top-level results from the report. This is the entry point to the tree walk.

from rdflib import Graph, Namespace, RDF
SH = Namespace("http://www.w3.org/ns/shacl#")

def get_report_node(report_graph: Graph):
    return report_graph.value(predicate=RDF.type,
                              object=SH.ValidationReport)

def get_top_level_results(report_graph: Graph):
    """
    Returns only direct sh:result children of the ValidationReport node.
    Avoids the trap of report.subjects(RDF.type, SH.ValidationResult)
    which also returns all sh:detail nodes.
    """
    report_node = get_report_node(report_graph)
    return list(report_graph.objects(report_node, SH.result))

def is_node_constraint(result_node, report_graph: Graph) -> bool:
    component = report_graph.value(result_node,
                                   SH.sourceConstraintComponent)
    return str(component) == str(SH.NodeConstraintComponent)


#The key lesson from TC4 output: direct property violations appear as top-level sh:result entries with a blank-node sh:sourceShape. 
# Nested sh:node violations appear as top-level sh:result entries with a named sh:sourceShape and sh:detail children. 
# The parser separates these two populations at the top level.