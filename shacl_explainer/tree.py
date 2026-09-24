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
    # Set when this leaf is the validator's own sh:node result, kept because
    # re-validation could not break it down into a concrete failure.
    note:        Optional[str] = None
    # What the shape requires: sh:minCount 3, sh:datatype xsd:integer,
    # sh:class ex:Company, the members of sh:in, and so on. A repair hint names
    # it instead of saying "the required datatype". None where the shape that
    # produced the result cannot be identified, which is what an external
    # report gives for an anonymous property shape; the hint then falls back to
    # its unparameterised wording.
    parameter:   Optional[Union[RDFNode, list[RDFNode]]] = None
    # How many values the focus node already has on the failing path. Only
    # counted where a hint cannot be written without it, that is a minimum
    # above one, since reading it costs a path evaluation per leaf.
    value_count: Optional[int] = None

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
