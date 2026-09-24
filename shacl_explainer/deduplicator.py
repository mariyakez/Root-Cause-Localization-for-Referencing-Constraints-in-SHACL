# removes diamond duplicates
# deduplicator.py
from dataclasses import replace
from rdflib import BNode
from .tree import LeafFailure, ReferenceNode


def _label(term) -> str:
    # A blank node's label is new on every parse, so it must not decide order.
    return "" if term is None or isinstance(term, BNode) else str(term)


def child_order(node):
    """Content key for the children of one step. Merging sibling steps appends
    one step's children after another's, so a step's children are sorted again
    afterwards; the sort is stable, so ties keep their earlier order."""
    if isinstance(node, LeafFailure):
        return (1, _label(node.focus_node), _label(node.result_path),
                _label(node.component), _label(node.value_node))
    return (0, _label(node.focus_node), _label(node.source_shape), _label(node.result_path))

def deduplicate(roots: list) -> list:
    """
    Return a deduplicated copy of the explanation tree.

    The input tree is left untouched, so callers may safely call deduplicate()
    more than once on the same roots or render the original tree separately.
    """
    seen_leaves: dict[tuple, LeafFailure] = {}

    def ref_key(node: ReferenceNode):
        return (
            str(node.focus_node),
            str(node.source_shape),
            tuple(str(shape) for shape in node.ref_chain),
        )

    def merge_reference_siblings(nodes: list) -> list:
        merged = []
        by_key = {}

        for node in nodes:
            if not isinstance(node, ReferenceNode):
                merged.append(node)
                continue

            key = ref_key(node)
            if key in by_key:
                by_key[key].children = sorted([*by_key[key].children, *node.children],
                                              key=child_order)
            else:
                by_key[key] = node
                merged.append(node)

        return merged

    def walk(node):
        if isinstance(node, LeafFailure):
            key = node.dedup_key()
            if key in seen_leaves:
                # Merge: add this chain as an alternative path
                #The alt_chains field on a deduplicated LeafFailure lets the renderer say something like: 
                # "this failure is reachable via two paths: ContractorShape → EmployeeShape → PersonShape and ContractorShape → ParttimeShape → PersonShape" — which is genuinely useful information for the user.
                existing = seen_leaves[key]
                if node.ref_chain and node.ref_chain != existing.ref_chain and node.ref_chain not in existing.alt_chains:
                    existing.alt_chains = [*existing.alt_chains, node.ref_chain.copy()]
                return None         # signal: already recorded
            else:
                clone = replace(
                    node,
                    ref_chain=node.ref_chain.copy(),
                    alt_chains=[chain.copy() for chain in node.alt_chains],
                )
                seen_leaves[key] = clone
                return clone
        else:
            # ReferenceNode — filter out deduplicated children
            children = [c for c in
                        (walk(ch) for ch in node.children)
                        if c is not None]
            children = merge_reference_siblings(children)
            if not children:
                return None
            return replace(
                node,
                ref_chain=node.ref_chain.copy(),
                children=children,
            )

    deduped_roots = [r for r in (walk(root) for root in roots) if r is not None]
    return merge_reference_siblings(deduped_roots)

#The diamond case (TC5) showed that pyshacl duplicates PersonShape leaf failures when it's reachable via two parent shapes. 
#  deduplicator removes duplicates but preserves all reference chains that led to each leaf — that information is useful to the user.
