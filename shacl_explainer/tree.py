# ExplanationTree / LeafNode / ReferenceNode dataclasses. Define the tree nodes before writing any parsing logic. Everything else depends on these shapes.

from dataclasses import dataclass, field
from typing import Optional, Union
from rdflib import URIRef, BNode, Literal

RDFNode = Union[URIRef, BNode, Literal]

@dataclass
class LeafFailure:
    focus_node:  RDFNode
    value_node:  Optional[RDFNode]      # the offending value, if present
    result_path: Optional[URIRef]       # sh:resultPath (absent for node-level)
    component:   URIRef                 # e.g. sh:DatatypeConstraintComponent
    source_shape: RDFNode               # blank node or named shape
    message:     Optional[str]
    ref_chain:   list[RDFNode]          # [ContractorShape, EmployeeShape, PersonShape]
    alt_chains:  list[list[RDFNode]] = field(default_factory=list)

    def dedup_key(self):
        return (str(self.focus_node), str(self.result_path),
                str(self.component),  str(self.value_node))

@dataclass
class ReferenceNode:
    focus_node:    RDFNode
    source_shape:  RDFNode              # shape containing the sh:node constraint
    referenced_shape: Optional[RDFNode] # shape named by sh:node, if available
    result_path:   Optional[RDFNode]    # property path, for property-level sh:node
    message:       Optional[str]
    ref_chain:     list[RDFNode]
    children:      list[Union["ReferenceNode", LeafFailure]] = field(default_factory=list)
