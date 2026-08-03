import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, RDF

from shacl_explainer.validator import build_jena_command, run_validation

SH = Namespace("http://www.w3.org/ns/shacl#")


class ValidatorBackendTests(unittest.TestCase):
    def test_build_jena_command_uses_validate_subcommand_for_shacl(self):
        argv = build_jena_command(
            "/opt/homebrew/opt/jena/bin/shacl",
            "/tmp/data.ttl",
            "/tmp/shapes.ttl",
            "/tmp/report.ttl",
        )

        self.assertEqual(argv[:2], ["/opt/homebrew/opt/jena/bin/shacl", "validate"])
        self.assertIn("--data", argv)
        self.assertIn("--shapes", argv)

    def test_jena_engine_rejects_unparseable_text_output(self):
        # Jena must produce a real RDF report; free-text console output is no
        # longer scraped with regexes (that path used to silently capture only
        # the first violation and could even report false conformance).
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "data.ttl"
            shapes_path = temp_path / "shapes.ttl"
            report_path = temp_path / "report.ttl"
            script_path = temp_path / "fake-jena"

            data_path.write_text("<ex:s> <ex:p> <ex:o> .\n", encoding="utf-8")
            shapes_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n", encoding="utf-8")

            script_path.write_text(
                "#!/bin/sh\n"
                "echo 'Node=<http://example.org/alice>'\n"
                "echo '  Value: <http://example.org/alice>'\n"
                "echo '  Message: Node[<http://example.org/PersonShape>] at focusNode <http://example.org/alice>'\n",
                encoding="utf-8",
            )
            script_path.chmod(0o755)

            env = os.environ.copy()
            env["JENA_SHACL_COMMAND"] = str(script_path)

            with self.assertRaises(RuntimeError):
                run_validation(
                    data_path=str(data_path),
                    shapes_path=str(shapes_path),
                    engine="jena",
                    report_path=str(report_path),
                    env=env,
                )

    def test_jena_engine_parses_turtle_stdout_with_multiple_violations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "data.ttl"
            shapes_path = temp_path / "shapes.ttl"
            report_path = temp_path / "report.ttl"
            script_path = temp_path / "fake-jena"

            data_path.write_text("<ex:s> <ex:p> <ex:o> .\n", encoding="utf-8")
            shapes_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n", encoding="utf-8")

            script_path.write_text(
                "#!/bin/sh\n"
                "cat <<'EOF'\n"
                "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                "@prefix ex: <http://example.com/> .\n"
                "[] a sh:ValidationReport ;\n"
                "  sh:conforms \"false\"^^<http://www.w3.org/2001/XMLSchema#boolean> ;\n"
                "  sh:result [ a sh:ValidationResult ; sh:focusNode ex:s ; sh:resultSeverity sh:Violation ] ;\n"
                "  sh:result [ a sh:ValidationResult ; sh:focusNode ex:t ; sh:resultSeverity sh:Violation ] .\n"
                "EOF\n",
                encoding="utf-8",
            )
            script_path.chmod(0o755)

            env = os.environ.copy()
            env["JENA_SHACL_COMMAND"] = str(script_path)

            conforms, report_graph, timings = run_validation(
                data_path=str(data_path),
                shapes_path=str(shapes_path),
                engine="jena",
                report_path=str(report_path),
                env=env,
            )

            self.assertFalse(conforms)
            self.assertIsInstance(report_graph, Graph)
            SH = Namespace("http://www.w3.org/ns/shacl#")
            report_node = report_graph.value(predicate=RDF.type, object=SH.ValidationReport)
            self.assertIsNotNone(report_node)
            self.assertEqual(len(list(report_graph.objects(report_node, SH.result))), 2)
            self.assertIn("jena", timings)

    def test_jena_engine_uses_configured_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "data.ttl"
            shapes_path = temp_path / "shapes.ttl"
            report_path = temp_path / "report.ttl"
            script_path = temp_path / "fake-jena"

            data_path.write_text("<ex:s> <ex:p> <ex:o> .\n", encoding="utf-8")
            shapes_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n", encoding="utf-8")

            script_path.write_text(
                "#!/bin/sh\n"
                "cat > \"$REPORT\" <<'EOF'\n"
                "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                "@prefix ex: <http://example.com/> .\n"
                "[] a sh:ValidationReport ;\n"
                "  sh:conforms \"false\"^^<http://www.w3.org/2001/XMLSchema#boolean> ;\n"
                "  sh:result [ a sh:ValidationResult ; sh:focusNode ex:s ; sh:resultSeverity sh:Violation ] .\n"
                "EOF\n",
                encoding="utf-8",
            )
            script_path.chmod(0o755)

            env = os.environ.copy()
            env["JENA_SHACL_COMMAND"] = str(script_path)

            conforms, report_graph, timings = run_validation(
                data_path=str(data_path),
                shapes_path=str(shapes_path),
                engine="jena",
                report_path=str(report_path),
                env=env,
            )

            self.assertFalse(conforms)
            self.assertIsInstance(report_graph, Graph)
            self.assertTrue(report_path.exists())
            self.assertIn("jena", timings)

    def test_jena_engine_uses_original_files_instead_of_reserializing_parsed_graphs(self):
        # Mirrors how cli.py calls run_validation: it already parsed the data
        # and shapes into Graph objects for stats/tree-building, but should
        # still hand Jena the *original* turtle files via data_source/
        # shapes_source rather than paying to serialize the in-memory graphs
        # back out to fresh temp files.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "data.ttl"
            shapes_path = temp_path / "shapes.ttl"
            report_path = temp_path / "report.ttl"
            argv_log_path = temp_path / "argv.log"
            script_path = temp_path / "fake-jena"

            data_path.write_text("<ex:s> <ex:p> <ex:o> .\n", encoding="utf-8")
            shapes_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n", encoding="utf-8")

            script_path.write_text(
                "#!/bin/sh\n"
                'echo "$@" > "{argv_log}"\n'
                'cat > "$REPORT" <<\'EOF\'\n'
                "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
                "[] a sh:ValidationReport ; sh:conforms \"true\"^^<http://www.w3.org/2001/XMLSchema#boolean> .\n"
                "EOF\n".format(argv_log=argv_log_path),
                encoding="utf-8",
            )
            script_path.chmod(0o755)

            env = os.environ.copy()
            env["JENA_SHACL_COMMAND"] = str(script_path)

            data_graph = Graph().parse(str(data_path), format="turtle")
            shapes_graph = Graph().parse(str(shapes_path), format="turtle")

            run_validation(
                data_graph,
                shapes_graph,
                engine="jena",
                report_path=str(report_path),
                env=env,
                data_source=str(data_path),
                shapes_source=str(shapes_path),
            )

            argv_used = argv_log_path.read_text(encoding="utf-8")
            self.assertIn(str(data_path), argv_used)
            self.assertIn(str(shapes_path), argv_used)

    def test_jena_engine_fails_fast_without_configured_command(self):
        # There is no sensible guess for a Jena CLI's executable name, so an
        # unconfigured jena engine must raise immediately rather than trying
        # to spawn a made-up binary name.
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "data.ttl"
            shapes_path = temp_path / "shapes.ttl"
            data_path.write_text("<ex:s> <ex:p> <ex:o> .\n", encoding="utf-8")
            shapes_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n", encoding="utf-8")

            env = os.environ.copy()
            env.pop("JENA_SHACL_COMMAND", None)

            with self.assertRaisesRegex(RuntimeError, "no executable was provided"):
                run_validation(
                    data_path=str(data_path),
                    shapes_path=str(shapes_path),
                    engine="jena",
                    env=env,
                )

    def test_jena_engine_reports_clean_error_on_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            data_path = temp_path / "data.ttl"
            shapes_path = temp_path / "shapes.ttl"
            script_path = temp_path / "fake-jena"

            data_path.write_text("<ex:s> <ex:p> <ex:o> .\n", encoding="utf-8")
            shapes_path.write_text("@prefix sh: <http://www.w3.org/ns/shacl#> .\n", encoding="utf-8")

            script_path.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
            script_path.chmod(0o755)

            env = os.environ.copy()
            env["JENA_SHACL_COMMAND"] = str(script_path)

            with self.assertRaisesRegex(RuntimeError, "timed out"):
                run_validation(
                    data_path=str(data_path),
                    shapes_path=str(shapes_path),
                    engine="jena",
                    env=env,
                    jena_timeout=0.2,
                )
