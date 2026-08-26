import unittest

from rdflib import Literal, URIRef

from shacl_explainer.deduplicator import deduplicate
from shacl_explainer.tree import LeafFailure, ReferenceNode


EX = "http://example.org/"
SH = "http://www.w3.org/ns/shacl#"


class DeduplicatorTests(unittest.TestCase):
    def make_leaf(self, chain):
        return LeafFailure(
            focus_node=URIRef(EX + "alice"),
            value_node=Literal("twenty"),
            result_path=URIRef(EX + "age"),
            component=URIRef(SH + "DatatypeConstraintComponent"),
            source_shape=URIRef(EX + "AgePropertyShape"),
            message="age must be integer",
            ref_chain=[URIRef(EX + shape) for shape in chain],
        )

    def make_tree(self):
        return [
            ReferenceNode(
                focus_node=URIRef(EX + "alice"),
                source_shape=URIRef(EX + "EmployeeShape"),
                referenced_shape=URIRef(EX + "EmployeeShape"),
                result_path=None,
                message=None,
                ref_chain=[],
                children=[
                    self.make_leaf(["EmployeeShape", "FulltimeShape"]),
                    self.make_leaf(["EmployeeShape", "ParttimeShape"]),
                ],
            )
        ]

    def test_deduplicate_is_safe_to_call_twice_on_same_tree(self):
        roots = self.make_tree()

        first = deduplicate(roots)
        second = deduplicate(roots)

        self.assertEqual(len(first[0].children), 1)
        self.assertEqual(len(second[0].children), 1)
        self.assertEqual(len(first[0].children[0].alt_chains), 1)
        self.assertEqual(len(second[0].children[0].alt_chains), 1)

        # The original input tree remains unchanged.
        self.assertEqual(len(roots[0].children), 2)
        self.assertEqual(roots[0].children[0].alt_chains, [])
        self.assertEqual(roots[0].children[1].alt_chains, [])


if __name__ == "__main__":
    unittest.main()
