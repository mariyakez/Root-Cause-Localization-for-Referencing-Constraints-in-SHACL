import unittest
import warnings
from pathlib import Path
from unittest import mock

import pyshacl
from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, RDFS

from shacl_explainer.expander import build_explanation_tree, pair_results_with_candidates
from shacl_explainer import fallback
from shacl_explainer.cli import configure_prefixes
from shacl_explainer.fallback import build_targeted_shapes
from shacl_explainer.renderer import to_text_tree, tree_to_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = PROJECT_ROOT / "all_test_cases/sh_node_cases"
SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("http://example.org/")

# Fixtures with a shape that declares more than one sh:node. Which of those
# references a result travelled is recorded only in its sh:detail children: the
# validator reports the shape once per reference, and the sibling results are
# otherwise identical. Strip sh:detail and that attribution is gone for good, so
# the rebuilt step honestly names no referenced shape rather than guessing one.
# It is the only field re-validation cannot recover; the failures themselves,
# their chains, order and messages all still match exactly.
DIAMOND_FIXTURES = {
    "tc4_mixed.ttl",
    "tc5_diamond.ttl",
    "tc6_complex_org.ttl",
    "tc26_mixed_direct_plus_diamond.ttl",
    "tc52_large_diamond_dedup.ttl",
}

def without_referenced_shape(nodes):
    return [
        {key: (without_referenced_shape(value) if key == "children" else value)
         for key, value in node.items() if key != "referencedShape"}
        for node in nodes
    ]


class FallbackExpansionTests(unittest.TestCase):
    def build_report_without_details(self, ttl_file, case_dir=CASE_DIR):
        graph = Graph().parse(case_dir / ttl_file, format="turtle")

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


    def test_targeted_copy_drops_the_shapes_own_targets(self):
        """Re-validation copies the referenced shape and binds it to one node.
        A target the copy kept, explicit or the implicit class target of a
        shape that is also a class, would make it check every node that
        target selects."""
        declarations = [
            (SH.targetClass, EX.Company),
            (SH.targetNode, EX.globex),
            (SH.targetSubjectsOf, EX.legalName),
            (SH.targetObjectsOf, EX.worksFor),
            (RDF.type, RDFS.Class),
            (RDF.type, OWL.Class),
        ]
        for predicate, obj in declarations:
            with self.subTest(declaration=str(predicate)):
                shapes = Graph()
                prop, nested_prop = BNode(), BNode()
                shapes.add((EX.CompanyShape, RDF.type, SH.NodeShape))
                shapes.add((EX.CompanyShape, predicate, obj))
                shapes.add((EX.CompanyShape, SH.property, prop))
                shapes.add((prop, SH.path, EX.legalName))
                shapes.add((prop, SH.minCount, Literal(1)))
                # A dependency reached through sh:node, with a target of its own.
                shapes.add((EX.CompanyShape, SH.node, EX.RegisteredShape))
                shapes.add((EX.RegisteredShape, RDF.type, SH.NodeShape))
                shapes.add((EX.RegisteredShape, predicate, obj))
                shapes.add((EX.RegisteredShape, SH.property, nested_prop))
                shapes.add((nested_prop, SH.path, EX.registrationNumber))
                shapes.add((nested_prop, predicate, obj))

                copy = build_targeted_shapes(EX.CompanyShape, shapes, EX.acme)

                self.assertNotIn((None, predicate, obj), copy)
                self.assertEqual(set(copy.subject_objects(SH.targetNode)),
                                 {(EX.CompanyShape, EX.acme)})
                self.assertIn((prop, SH.minCount, Literal(1)), copy)
                self.assertIn((nested_prop, SH.path, EX.registrationNumber), copy)

    def test_fallback_on_a_targeted_referenced_shape_matches_sh_detail(self):
        """Removing sh:detail must not change the explanation when the
        referenced shape has a target of its own."""
        edges = PROJECT_ROOT / "all_test_cases/external_report_cases/fallback_edges"
        graph = Graph().parse(edges / "targeted_referenced_shape.ttl", format="turtle")
        _, detailed, _ = pyshacl.validate(graph, shacl_graph=graph, inference="none",
                                          abort_on_first=False, serialize_report_graph=False)
        expected = tree_to_data(build_explanation_tree(detailed, graph, graph))

        _, stripped = self.build_report_without_details(
            "targeted_referenced_shape.ttl", case_dir=edges)
        rebuilt = tree_to_data(build_explanation_tree(stripped, graph, graph))

        self.assertEqual(rebuilt, expected)

    def test_fallback_reproduces_sh_detail_exactly_on_every_fixture(self):
        """With every sh:detail removed, re-validation must rebuild exactly the
        explanation pySHACL's own sh:detail gives: the same failures, chains,
        order and messages, with and without the re-validation cache. This is
        what a copy that lost an sh:in list, a nested shape or a prefix, or an
        order that depended on where a result came from, would break."""
        fixtures = [
            path for path in sorted(PROJECT_ROOT.glob("all_test_cases/*/tc*.ttl"))
            if path.parent.name != "external_report_cases"
        ] + [
            path for path in sorted(PROJECT_ROOT.glob("all_test_cases/external_report_cases/*/*.ttl"))
            if not any(part in path.name for part in (".jena.", ".topbraid.", "report"))
        ]
        for path in fixtures:
            with self.subTest(fixture=path.name):
                graph = Graph().parse(path, format="turtle")
                configure_prefixes(graph, graph)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    _, report, _ = pyshacl.validate(graph, shacl_graph=graph, inference="none",
                                                    abort_on_first=False, serialize_report_graph=False)
                    expected = tree_to_data(build_explanation_tree(report, graph, graph))
                    for triple in list(report.triples((None, SH.detail, None))):
                        report.remove(triple)
                    cached = tree_to_data(build_explanation_tree(report, graph, graph))
                    uncached = tree_to_data(build_explanation_tree(
                        report, graph, graph, cache_revalidation=False))

                if path.name in DIAMOND_FIXTURES:
                    # See DIAMOND_FIXTURES: everything but the attribution of a
                    # step to one of several referenced shapes must still match.
                    self.assertEqual(without_referenced_shape(cached),
                                     without_referenced_shape(expected))
                    self.assertEqual(without_referenced_shape(uncached),
                                     without_referenced_shape(expected))
                else:
                    self.assertEqual(cached, expected)
                    self.assertEqual(uncached, expected)

    def test_removing_sh_detail_costs_the_attribution_of_a_diamond_step(self):
        """The one thing sh:detail carries that re-validation cannot recover.

        This is the limitation DIAMOND_FIXTURES describes, asserted rather than
        assumed. Reading sh:detail names the reference every step travelled.
        Rebuilding without it loses that name on the steps taken from the
        stripped report, while steps below them are rebuilt from fresh
        re-validation whose own sh:detail is intact and so keep it. What must
        never happen is the third case: reconstruction may decline to attribute
        a step, but it may not attribute one to a different shape.
        """
        def referenced_shapes(nodes):
            found = []
            for node in nodes:
                if node.get("type") == "reference":
                    found.append(node.get("referencedShape"))
                found.extend(referenced_shapes(node.get("children", [])))
            return found

        for name in sorted(DIAMOND_FIXTURES):
            with self.subTest(fixture=name):
                path = next(PROJECT_ROOT.glob(f"all_test_cases/*/{name}"))
                graph = Graph().parse(path, format="turtle")
                configure_prefixes(graph, graph)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    _, report, _ = pyshacl.validate(graph, shacl_graph=graph, inference="none",
                                                    abort_on_first=False, serialize_report_graph=False)
                    with_detail = referenced_shapes(
                        tree_to_data(build_explanation_tree(report, graph, graph)))
                    for triple in list(report.triples((None, SH.detail, None))):
                        report.remove(triple)
                    without_detail = referenced_shapes(
                        tree_to_data(build_explanation_tree(report, graph, graph)))

                self.assertTrue(all(with_detail), f"{name}: sh:detail should name every step")
                self.assertNotEqual(without_detail, with_detail)
                for rebuilt, from_detail in zip(without_detail, with_detail):
                    self.assertIn(rebuilt, (None, from_detail))

    def test_revalidation_cache_reuses_one_result_per_node_and_shape(self):
        """Three employees of one company need one re-validation of that
        company, not three."""
        graph = Graph().parse(CASE_DIR / "tc7_property_node.ttl", format="turtle")
        for employee in (EX.bob, EX.carol):
            graph.add((employee, RDF.type, EX.Employee))
            graph.add((employee, EX.worksFor, EX.acme))
        _, report, _ = pyshacl.validate(graph, shacl_graph=graph, inference="none",
                                        abort_on_first=False, serialize_report_graph=False)
        for triple in list(report.triples((None, SH.detail, None))):
            report.remove(triple)

        results = {}
        for cached in (True, False):
            with mock.patch.object(fallback, "revalidate_against_shape",
                                   wraps=fallback.revalidate_against_shape) as spy:
                results[cached] = tree_to_data(build_explanation_tree(
                    report, graph, graph, cache_revalidation=cached))
            results[cached, "calls"] = spy.call_count

        self.assertEqual(results[True, "calls"], 1)
        self.assertEqual(results[False, "calls"], 3)
        self.assertEqual(results[True], results[False])

    def test_declared_metadata_decides_when_pairing_cannot(self):
        """One result against two candidate property shapes cannot be paired.
        A declared sh:message or sh:severity carried by the result still
        identifies its property shape, and without either none is chosen."""
        shapes = Graph().parse(
            PROJECT_ROOT / "all_test_cases/external_report_cases/shared_path/both_types_messages.ttl",
            format="turtle",
        )
        candidates = {
            shapes.value(prop_shape, SH.node): prop_shape
            for prop_shape in shapes.subjects(SH.path, EX.worksFor)
        }
        company, charity = candidates[EX.CompanyShape], candidates[EX.CharityShape]

        def assign(message, severity=SH.Violation):
            report = Graph()
            result = BNode()
            report.add((result, RDF.type, SH.ValidationResult))
            report.add((result, SH.resultMessage, Literal(message)))
            report.add((result, SH.resultSeverity, severity))
            return pair_results_with_candidates([result], [company, charity], report, shapes).get(result)

        # Both candidates carry the default severity, so only the message can decide.
        self.assertEqual(assign("An employer must be a valid company"), company)
        self.assertEqual(assign("A volunteering organisation must be a registered charity"), charity)
        self.assertIsNone(assign("Value does not conform"))

        # A declared severity decides where the message does not.
        shapes.add((charity, SH.severity, SH.Warning))
        self.assertEqual(assign("Value does not conform", SH.Warning), charity)
        self.assertEqual(assign("Value does not conform", SH.Violation), company)
        self.assertIsNone(assign("Value does not conform", SH.Info))


if __name__ == "__main__":
    unittest.main()
