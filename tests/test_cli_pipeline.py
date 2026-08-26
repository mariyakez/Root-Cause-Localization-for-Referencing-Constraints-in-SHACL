import pickle
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = "all_test_cases/sh_node_cases"
DIRECT_CASE_DIR = "all_test_cases/direct_constraint_cases"
ADDITIONAL_CASE_DIRS = [
    "all_test_cases/mixed_constraint_cases",
    "all_test_cases/multi_focus_cases",
    "all_test_cases/property_path_cases",
    "all_test_cases/severity_cases",
    "all_test_cases/message_metadata_cases",
    "all_test_cases/cycle_cases",
    "all_test_cases/scale_cases",
]


class ShaclExplainerCliTests(unittest.TestCase):
    def run_explainer(self, ttl_file):
        path = f"{CASE_DIR}/{ttl_file}"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "shacl_explainer.cli",
                path,
                path,
            ],
            cwd=PROJECT_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout

    def run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, "-m", "shacl_explainer.cli", *args],
            cwd=PROJECT_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return result

    def assert_contains_all(self, output, expected_parts):
        for part in expected_parts:
            with self.subTest(part=part):
                self.assertIn(part, output)

    def test_direct_core_constraint_cases_have_no_sh_node(self):
        expected = {
            "tc9_direct_min_count.ttl": ["minCount", "ex:name"],
            "tc10_direct_max_count.ttl": ["maxCount", "ex:nickname"],
            "tc11_direct_datatype.ttl": ["datatype", "ex:credits"],
            "tc12_direct_class.ttl": ["class", "ex:student"],
            "tc13_direct_pattern.ttl": ["pattern", "ex:courseCode"],
            "tc14_direct_in.ttl": ["in", "ex:level"],
            "tc15_direct_node_kind.ttl": ["nodeKind", "ex:teacher"],
            "tc16_direct_min_max_inclusive.ttl": ["minInclusive", "maxInclusive", "ex:score"],
            "tc17_direct_less_than.ttl": ["lessThan", "ex:startDate"],
            "tc18_direct_has_value.ttl": ["hasValue", "ex:status"],
            "tc19_direct_equals.ttl": ["equals", "ex:preferredEmail"],
            "tc20_direct_disjoint.ttl": ["disjoint", "ex:primaryRole"],
            "tc21_direct_closed_shape.ttl": ["closed", "ex:unknownProperty"],
            "tc22_direct_logical_constraints.ttl": ["or", "xone", "not"],
            "tc23_direct_core_mix.ttl": ["minCount", "datatype", "in", "pattern"],
        }

        for filename, expected_parts in expected.items():
            with self.subTest(filename=filename):
                path = f"{DIRECT_CASE_DIR}/{filename}"
                result = self.run_cli(path, path, "--summary")

                self.assertIn("via sh:node,  ", result.stdout)
                self.assertIn("0 via sh:node", result.stdout)
                self.assertNotIn("sh:node ex:", result.stdout)
                self.assert_contains_all(result.stdout, expected_parts)

    def test_additional_case_groups_run_in_summary_mode(self):
        for case_dir in ADDITIONAL_CASE_DIRS:
            for path in sorted((PROJECT_ROOT / case_dir).glob("tc*.ttl")):
                relative_path = path.relative_to(PROJECT_ROOT).as_posix()
                with self.subTest(path=relative_path):
                    result = self.run_cli(relative_path, relative_path, "--summary")

                    self.assertTrue(
                        "SHACL Explanation Summary" in result.stdout
                        or "Data is valid." in result.stdout
                    )

    def test_external_report_compatibility_cases_run(self):
        cases = [
            (
                "all_test_cases/external_report_cases/tc41_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc41_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc41_pyshacl_report_with_detail.ttl",
                "ex:name",
            ),
            (
                "all_test_cases/external_report_cases/tc41_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc41_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc42_jena_report_no_detail.ttl",
                "ex:name",
            ),
            (
                "all_test_cases/external_report_cases/tc43_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc43_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc43_jena_property_shape_report.ttl",
                "ex:legalName",
            ),
            (
                "all_test_cases/external_report_cases/tc43_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc43_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc44_topbraid_like_report.ttl",
                "ex:legalName",
            ),
            (
                "all_test_cases/external_report_cases/tc41_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc41_data_shapes.ttl",
                "all_test_cases/external_report_cases/tc45_report_missing_source_shape.ttl",
                "ex:name",
            ),
        ]

        for data_path, shapes_path, report_path, expected_path in cases:
            with self.subTest(report=report_path):
                result = self.run_cli(
                    data_path,
                    shapes_path,
                    "--report",
                    report_path,
                    "--summary",
                )

                self.assertIn("SHACL Explanation Summary", result.stdout)
                self.assertIn(expected_path, result.stdout)

    def test_valid_separate_data_and_shapes(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "shacl_explainer.cli",
                f"{CASE_DIR}/testdata.ttl",
                f"{CASE_DIR}/testshapes.ttl",
            ],
            cwd=PROJECT_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn("Data is valid.", result.stdout)

    def test_pickle_data_graph_input(self):
        ttl_path = PROJECT_ROOT / CASE_DIR / "tc1_single_leaf.ttl"
        graph = Graph().parse(ttl_path, format="turtle")

        with tempfile.TemporaryDirectory() as temp_dir:
            pkl_path = Path(temp_dir) / "tc1_single_leaf.pkl"
            with open(pkl_path, "wb") as handle:
                pickle.dump(graph, handle)

            result = self.run_cli(
                str(pkl_path),
                f"{CASE_DIR}/tc1_single_leaf.ttl",
            )

        self.assert_contains_all(
            result.stdout,
            [
                "sh:node ex:EmployeeShape",
                "datatype",
                "ex:age",
                '"twenty"',
            ],
        )

    def test_tc1_single_leaf_violation(self):
        output = self.run_explainer("tc1_single_leaf.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:EmployeeShape",
                "datatype",
                "ex:age",
                '"twenty"',
            ],
        )

    def test_tc2_multiple_leaf_violations(self):
        output = self.run_explainer("tc2_multi_leaf.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:EmployeeShape",
                "minCount    ex:age",
                "minCount    ex:name",
                "pattern     ex:email",
                '"not-an-email"',
            ],
        )

    def test_tc3_two_level_reference_chain(self):
        output = self.run_explainer("tc3_two_level.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:ContractorShape",
                "ex:ContractorShape",
                "ex:EmployeeShape",
                "datatype",
                "ex:age",
                '"thirty-one"',
            ],
        )

    def test_tc4_multiple_sh_node_branches(self):
        output = self.run_explainer("tc4_mixed.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:ManagerShape",
                "datatype    ex:age",
                "minCount    ex:name",
                "minCount    ex:department",
                '"forty-two"',
            ],
        )

    def test_tc5_diamond_deduplicates_and_preserves_branches(self):
        output = self.run_explainer("tc5_diamond.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:StaffShape",
                "ex:FulltimeShape",
                "ex:ParttimeShape",
                "datatype    ex:age",
                "minCount    ex:name",
                "minCount    ex:hoursPerWeek",
                "minCount    ex:contractHours",
                "also via ex:StaffShape",
            ],
        )

        self.assertEqual(output.count("datatype    ex:age"), 1)
        self.assertEqual(output.count("minCount    ex:name"), 1)

    def test_tc6_complex_organization_references(self):
        output = self.run_explainer("tc6_complex_org.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:ProjectLeadShape",
                "Focus node: ex:frank",
                "sh:node ex:EmploymentShape",
                "ex:SecurityClearanceShape",
                "datatype    ex:age",
                "minCount    ex:name",
                "pattern     ex:email",
                "minCount    ex:employeeId",
                "in          ex:clearanceLevel",
                "minCount    ex:projectCode",
                "via ex:ProjectLeadShape -> ex:EmploymentShape -> ex:PersonShape",
                "also via ex:ProjectLeadShape -> ex:SecurityClearanceShape -> ex:PersonShape",
                "via ex:ProjectLeadShape -> ex:EmploymentShape -> ex:ContactShape",
            ],
        )

        self.assertEqual(output.count("datatype    ex:age"), 1)
        self.assertEqual(output.count("minCount    ex:name"), 1)

    def test_tc7_property_shape_node_reference(self):
        output = self.run_explainer("tc7_property_node.ttl")

        self.assert_contains_all(
            output,
            [
                "sh:node ex:CompanyShape  path=ex:worksFor",
                "Focus node: ex:alice",
                "minCount    ex:legalName",
                "ex:legalName is required",
            ],
        )

    def test_tc8_cycle_on_different_property_paths_terminates(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc8_cycle_property_paths.ttl",
            f"{CASE_DIR}/tc8_cycle_property_paths.ttl",
            "--summary",
        )

        self.assertIn("Total leaf failures", result.stdout)
        self.assertIn("ex:required", result.stdout)

    def test_external_node_report_without_details_uses_fallback(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            "--report",
            f"{CASE_DIR}/external_report_tc2_no_detail.ttl",
        )

        self.assert_contains_all(
            result.stdout,
            [
                "sh:node ex:EmployeeShape",
                "minCount    ex:age",
                "minCount    ex:name",
                "pattern     ex:email",
            ],
        )

    def test_external_property_report_without_details_revalidates_value_node(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc7_property_node.ttl",
            f"{CASE_DIR}/tc7_property_node.ttl",
            "--report",
            f"{CASE_DIR}/external_report_tc7_property_no_detail.ttl",
            "--hints",
        )

        self.assert_contains_all(
            result.stdout,
            [
                "sh:node ex:CompanyShape  path=ex:worksFor",
                "Focus node: ex:alice",
                "minCount    ex:legalName",
                "→ fix: Add at least one ex:legalName value to ex:acme.",
            ],
        )
        self.assertNotIn("value to ex:alice", result.stdout)

    def test_jena_report_node_source_shape_with_result_path(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc7_property_node.ttl",
            f"{CASE_DIR}/tc7_property_node.ttl",
            "--report",
            f"{CASE_DIR}/jena_report_tc7_node_source_no_detail.ttl",
            "--hints",
        )

        self.assert_contains_all(
            result.stdout,
            [
                "sh:node ex:CompanyShape  path=ex:worksFor",
                "Focus node: ex:alice",
                "minCount    ex:legalName",
                "→ fix: Add at least one ex:legalName value to ex:acme.",
            ],
        )
        self.assertNotIn("sh:node ex:EmployeeShape", result.stdout)

    def test_summary_mode(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            "--summary",
        )

        self.assert_contains_all(
            result.stdout,
            [
                "SHACL Explanation Summary",
                "Total leaf failures   : 3",
                "ex:age",
                "ex:name",
                "ex:email",
                "minCount",
                "pattern",
                "Top full leaf reference chains",
                "ex:EmployeeShape",
            ],
        )

    def test_limit_roots(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc6_complex_org.ttl",
            f"{CASE_DIR}/tc6_complex_org.ttl",
            "--limit",
            "1",
        )

        self.assertEqual(result.stdout.count("Focus node:"), 1)

    def test_focus_filter(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc6_complex_org.ttl",
            f"{CASE_DIR}/tc6_complex_org.ttl",
            "--focus",
            "ex:frank",
        )

        self.assertIn("Focus node: ex:frank", result.stdout)

    def test_csv_export(self):
        with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
            result = self.run_cli(
                f"{CASE_DIR}/tc2_multi_leaf.ttl",
                f"{CASE_DIR}/tc2_multi_leaf.ttl",
                "--csv",
                tmp.name,
                "--summary",
            )

            csv_text = Path(tmp.name).read_text()

        self.assertIn("Total leaf failures   : 3", result.stdout)
        self.assertIn(
            "focus_node,depth,reference_chain,alternate_reference_chains,leaf_path,component,value,message,kind,repair_hint",
            csv_text,
        )
        self.assertIn("ex:email", csv_text)

        with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
            self.run_cli(
                f"{CASE_DIR}/tc6_complex_org.ttl",
                f"{CASE_DIR}/tc6_complex_org.ttl",
                "--csv",
                tmp.name,
                "--summary",
            )
            tc6_csv_text = Path(tmp.name).read_text()

        self.assertIn(
            "ex:ProjectLeadShape -> ex:SecurityClearanceShape -> ex:PersonShape",
            tc6_csv_text,
        )

    def test_repair_hints(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            "--hints",
        )

        self.assertIn("→ fix: Add at least one ex:age value to ex:bob.", result.stdout)
        self.assertIn("→ fix: Change \"not-an-email\" on ex:email", result.stdout)

    def test_text_tree_color_modes(self):
        plain = self.run_cli(
            f"{CASE_DIR}/tc1_single_leaf.ttl",
            f"{CASE_DIR}/tc1_single_leaf.ttl",
            "--color",
            "never",
        )
        colored = self.run_cli(
            f"{CASE_DIR}/tc1_single_leaf.ttl",
            f"{CASE_DIR}/tc1_single_leaf.ttl",
            "--color",
            "always",
        )

        self.assertNotIn("\033[", plain.stdout)
        self.assertIn("\033[", colored.stdout)
        self.assertIn("sh:node ex:EmployeeShape", colored.stdout)

    def test_path_and_component_filters(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            "--path",
            "ex:email",
            "--component",
            "pattern",
        )

        self.assertIn("ex:email", result.stdout)
        self.assertNotIn("path=ex:age", result.stdout)
        self.assertNotIn("path=ex:name", result.stdout)

    def test_reference_path_filter(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc7_property_node.ttl",
            f"{CASE_DIR}/tc7_property_node.ttl",
            "--reference-path",
            "ex:worksFor",
        )

        self.assertIn("path=ex:worksFor", result.stdout)
        self.assertIn("ex:legalName", result.stdout)

    def test_top_summary_limit(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            f"{CASE_DIR}/tc2_multi_leaf.ttl",
            "--summary",
            "--top",
            "1",
        )

        by_leaf_path = result.stdout.split("Top failing paths", 1)[1].split("Top components", 1)[0]
        self.assertEqual(by_leaf_path.count("ex:"), 1)

    def test_summary_includes_full_leaf_reference_chains(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc6_complex_org.ttl",
            f"{CASE_DIR}/tc6_complex_org.ttl",
            "--summary",
        )

        self.assertIn("Top full leaf reference chains", result.stdout)
        self.assertIn(
            "ex:ProjectLeadShape -> ex:EmploymentShape -> ex:PersonShape",
            result.stdout,
        )
        self.assertIn(
            "ex:ProjectLeadShape -> ex:SecurityClearanceShape -> ex:PersonShape",
            result.stdout,
        )

    def test_html_output_to_stdout(self):
        result = self.run_cli(
            f"{CASE_DIR}/tc6_complex_org.ttl",
            f"{CASE_DIR}/tc6_complex_org.ttl",
            "--format",
            "html",
        )

        self.assertIn("<!DOCTYPE html>", result.stdout)
        self.assertIn("const REPORT_DATA =", result.stdout)
        self.assertIn("<title>SHACL Explanation Report</title>", result.stdout)
        self.assertIn("Dataset", result.stdout)
        self.assertIn("tc6_complex_org.ttl", result.stdout)
        self.assertNotIn("SHACL Report - all_test_cases", result.stdout)
        self.assertIn("ex:ProjectLeadShape", result.stdout)
        self.assertIn("ex:projectCode", result.stdout)

    def test_html_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "report.html"
            result = self.run_cli(
                f"{CASE_DIR}/tc6_complex_org.ttl",
                f"{CASE_DIR}/tc6_complex_org.ttl",
                "--format",
                "html",
                "--output",
                str(html_path),
            )

            html = html_path.read_text()

        self.assertEqual("", result.stdout)
        self.assertIn("Output written to", result.stderr)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("filter-panel", html)
        self.assertIn("filter-select", html)
        self.assertIn("ex:frank", html)

    def test_html_output_relative_file_goes_to_html_outputs(self):
        output_dir = PROJECT_ROOT / "html_outputs"
        html_path = output_dir / "test_report.html"
        if html_path.exists():
            html_path.unlink()

        result = self.run_cli(
            f"{CASE_DIR}/tc6_complex_org.ttl",
            f"{CASE_DIR}/tc6_complex_org.ttl",
            "--format",
            "html",
            "--output",
            "test_report.html",
        )

        try:
            html = html_path.read_text()
        finally:
            if html_path.exists():
                html_path.unlink()

        self.assertEqual("", result.stdout)
        self.assertIn("Output written to html_outputs/test_report.html", result.stderr)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("ex:frank", html)

    def test_save_report_and_timing_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "report.ttl"
            timing_path = Path(tmpdir) / "timing.csv"
            result = self.run_cli(
                f"{CASE_DIR}/tc1_single_leaf.ttl",
                f"{CASE_DIR}/tc1_single_leaf.ttl",
                "--summary",
                "--save-report",
                str(report_path),
                "--timing-csv",
                str(timing_path),
            )

            report_text = report_path.read_text()
            timing_text = timing_path.read_text()

        self.assertIn("Total leaf failures   : 1", result.stdout)
        self.assertIn("sh:ValidationReport", report_text)
        self.assertIn("data_triples,shape_triples,top_results,all_results", timing_text)


if __name__ == "__main__":
    unittest.main()
