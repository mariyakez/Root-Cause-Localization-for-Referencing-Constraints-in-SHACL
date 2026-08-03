import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pyshacl
from rdflib import Graph, Namespace, URIRef

from shacl_explainer.expander import build_explanation_tree
from shacl_explainer.fallback import revalidate_against_shape
from shacl_explainer.renderer import to_text_tree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = PROJECT_ROOT / "all_test_cases/sh_node_cases"
SH = Namespace("http://www.w3.org/ns/shacl#")


class FallbackExpansionTests(unittest.TestCase):
    def build_report_without_details(self, ttl_file):
        graph = Graph().parse(CASE_DIR / ttl_file, format="turtle")

        _, report_graph, _ = pyshacl.validate(
            graph,
            shacl_graph=graph,
            inference="none",
            abort_on_first=False,
            serialize_report_graph=False,
        )

        for triple in list(report_graph.triples((None, SH.detail, None))):
            report_graph.remove(triple)

        return graph, report_graph

    def test_fallback_revalidates_missing_tc2_details(self):
        graph, report_graph = self.build_report_without_details(
            "tc2_multi_leaf.ttl"
        )

        tree = build_explanation_tree(report_graph, graph, graph)
        output = to_text_tree(tree)

        self.assertIn("minCount    ex:age", output)
        self.assertIn("minCount    ex:name", output)
        self.assertIn("pattern     ex:email", output)
        self.assertIn('"not-an-email"', output)

    def test_fallback_preserves_diamond_branches(self):
        graph, report_graph = self.build_report_without_details(
            "tc5_diamond.ttl"
        )

        tree = build_explanation_tree(report_graph, graph, graph)
        output = to_text_tree(tree)

        self.assertIn("ex:FulltimeShape", output)
        self.assertIn("ex:ParttimeShape", output)
        self.assertIn("minCount    ex:hoursPerWeek", output)
        self.assertIn("minCount    ex:contractHours", output)
        self.assertIn("also via ex:StaffShape", output)

    def test_revalidate_against_shape_gives_clear_error_when_pyshacl_missing(self):
        # fallback.py is the only place pyshacl gets exercised when the
        # explainer is expanding a report that has no sh:detail (e.g. every
        # Jena report). If pyshacl isn't installed, that should surface as a
        # clear, actionable error rather than a bare ModuleNotFoundError deep
        # in an internal import.
        with patch.dict(sys.modules, {"pyshacl": None}):
            with self.assertRaisesRegex(RuntimeError, "pip install -r requirements.txt"):
                revalidate_against_shape(
                    URIRef("http://example.com/focus"),
                    URIRef("http://example.com/Shape"),
                    Graph(),
                    Graph(),
                )


if __name__ == "__main__":
    unittest.main()
