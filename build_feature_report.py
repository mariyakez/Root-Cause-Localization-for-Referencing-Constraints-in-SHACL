#!/usr/bin/env python3
"""
Build a dependency-free PDF report describing the SHACL explainer tool.

The script writes SHACL_Explainer_Feature_Report.pdf in the project root.
It intentionally uses only the Python standard library so the report can be
regenerated on the same environment without extra packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import textwrap
import zlib


OUT = Path(__file__).with_name("SHACL_Explainer_Feature_Report.pdf")


def pdf_escape(text: str) -> str:
    replacements = {
        "\\": "\\\\",
        "(": "\\(",
        ")": "\\)",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2192": "->",
        "\u2713": "OK",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


@dataclass
class PdfReport:
    path: Path
    width: int = 612
    height: int = 792
    margin_x: int = 54
    margin_top: int = 58
    margin_bottom: int = 54
    y: int = field(init=False)
    page_no: int = 0
    pages: list[list[str]] = field(default_factory=list)

    def __post_init__(self):
        self.new_page()

    def new_page(self):
        self.pages.append([])
        self.page_no += 1
        self.y = self.height - self.margin_top
        self._footer_pending = True

    @property
    def content(self) -> list[str]:
        return self.pages[-1]

    def ensure(self, height: int):
        if self.y - height < self.margin_bottom:
            self.add_footer()
            self.new_page()

    def text(self, x: int, y: int, text: str, size=10, font="F1", color="0 0 0"):
        escaped = pdf_escape(text)
        self.content.append(f"BT /{font} {size} Tf {color} rg {x} {y} Td ({escaped}) Tj ET")

    def line(self, x1, y1, x2, y2, color="0.75 0.78 0.82", width=0.6):
        self.content.append(f"q {color} RG {width} w {x1} {y1} m {x2} {y2} l S Q")

    def rect_fill(self, x, y, w, h, color):
        self.content.append(f"q {color} rg {x} {y} {w} {h} re f Q")

    def h1(self, text):
        self.ensure(44)
        self.text(self.margin_x, self.y, text, size=18, font="F2", color="0.10 0.20 0.34")
        self.y -= 16
        self.line(self.margin_x, self.y, self.width - self.margin_x, self.y, color="0.22 0.42 0.66", width=1.2)
        self.y -= 20

    def h2(self, text):
        self.ensure(36)
        self.y -= 4
        self.text(self.margin_x, self.y, text, size=13, font="F2", color="0.12 0.28 0.42")
        self.y -= 18

    def para(self, text, width=92, size=10, leading=13, indent=0):
        lines = []
        for part in text.split("\n"):
            if not part.strip():
                lines.append("")
            else:
                lines.extend(textwrap.wrap(part, width=width))
        self.ensure(max(leading * len(lines), leading))
        for line in lines:
            if line:
                self.text(self.margin_x + indent, self.y, line, size=size)
            self.y -= leading
        self.y -= 4

    def bullet(self, text, width=86):
        wrapped = textwrap.wrap(text, width=width)
        self.ensure(13 * len(wrapped))
        for i, line in enumerate(wrapped):
            prefix = "- " if i == 0 else "  "
            self.text(self.margin_x + 10, self.y, prefix + line, size=10)
            self.y -= 13
        self.y -= 2

    def code(self, text, width=86):
        lines = []
        for raw in text.strip("\n").splitlines():
            lines.extend(textwrap.wrap(raw, width=width, replace_whitespace=False) or [""])
        box_h = 14 * len(lines) + 12
        self.ensure(box_h)
        self.rect_fill(self.margin_x, self.y - box_h + 8, self.width - 2 * self.margin_x, box_h, "0.96 0.97 0.98")
        yy = self.y - 8
        for line in lines:
            self.text(self.margin_x + 10, yy, line, size=8.5, font="F3", color="0.12 0.15 0.18")
            yy -= 12
        self.y -= box_h + 6

    def kv_table(self, rows, col1=190, col2=310, size=9):
        row_h = 24
        self.ensure(row_h * (len(rows) + 1))
        x = self.margin_x
        w = col1 + col2
        self.rect_fill(x, self.y - row_h + 6, w, row_h, "0.88 0.92 0.96")
        self.text(x + 8, self.y - 10, "Item", size=size, font="F2")
        self.text(x + col1 + 8, self.y - 10, "Result / Description", size=size, font="F2")
        self.y -= row_h
        for key, val in rows:
            wrapped = textwrap.wrap(val, width=58) or [""]
            h = max(row_h, 13 * len(wrapped) + 10)
            self.ensure(h)
            self.line(x, self.y + 6, x + w, self.y + 6, color="0.82 0.85 0.88")
            self.text(x + 8, self.y - 10, key, size=size, font="F2")
            yy = self.y - 10
            for line in wrapped:
                self.text(x + col1 + 8, yy, line, size=size)
                yy -= 12
            self.y -= h
        self.y -= 8

    def add_footer(self):
        if not getattr(self, "_footer_pending", False):
            return
        self.line(self.margin_x, 40, self.width - self.margin_x, 40, color="0.80 0.83 0.86")
        self.text(self.margin_x, 26, "SHACL Explainer Tool Feature Report", size=8, color="0.35 0.38 0.42")
        self.text(self.width - self.margin_x - 42, 26, f"Page {self.page_no}", size=8, color="0.35 0.38 0.42")
        self._footer_pending = False

    def build(self):
        self.add_footer()
        objects = []
        font_objs = [
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        ]
        objects.extend(font_objs)
        page_refs = []
        for page in self.pages:
            stream = "\n".join(page).encode("latin-1", "replace")
            compressed = zlib.compress(stream)
            content_obj_num = len(objects) + 1
            objects.append(f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode() + compressed + b"\nendstream")
            page_obj_num = len(objects) + 1
            page_refs.append(page_obj_num)
            objects.append(
                f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {self.width} {self.height}] "
                f"/Resources << /Font << /F1 1 0 R /F2 2 0 R /F3 3 0 R >> >> "
                f"/Contents {content_obj_num} 0 R >>"
            )

        pages_obj_num = len(objects) + 1
        kids = " ".join(f"{num} 0 R" for num in page_refs)
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>")
        catalog_obj_num = len(objects) + 1
        objects.append(f"<< /Type /Catalog /Pages {pages_obj_num} 0 R >>")

        # Patch parent references now that /Pages object number is known.
        for obj_num in page_refs:
            idx = obj_num - 1
            objects[idx] = objects[idx].replace("/Parent 0 0 R", f"/Parent {pages_obj_num} 0 R")

        offsets = []
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode())
            if isinstance(obj, bytes):
                out.extend(obj)
            else:
                out.extend(obj.encode("latin-1", "replace"))
            out.extend(b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for off in offsets:
            out.extend(f"{off:010d} 00000 n \n".encode())
        out.extend(
            f"trailer\n<< /Size {len(objects)+1} /Root {catalog_obj_num} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n".encode()
        )
        self.path.write_bytes(out)


def build_report():
    pdf = PdfReport(OUT)

    pdf.text(54, 700, "SHACL Explainer Tool", size=26, font="F2", color="0.08 0.22 0.38")
    pdf.text(54, 672, "Feature, Scope, Pipeline, and Evaluation Report", size=15, font="F1", color="0.20 0.28 0.34")
    pdf.text(54, 640, "Prepared for thesis discussion and supervisor review", size=10, color="0.35 0.38 0.42")
    pdf.y = 595
    pdf.rect_fill(54, 505, 504, 70, "0.92 0.96 0.99")
    pdf.text(70, 552, "Core result", size=12, font="F2", color="0.10 0.20 0.34")
    pdf.text(70, 532, "The tool converts raw SHACL validation results involving sh:node references", size=10)
    pdf.text(70, 518, "into explanation trees that expose the concrete leaf failures users must repair.", size=10)
    pdf.y = 470

    pdf.h1("1. Goal And Scope")
    pdf.para(
        "The tool is designed to explain SHACL Core validation failures that involve referencing constraints, "
        "primarily sh:node. Instead of leaving the user at a high-level NodeConstraintComponent result, it reveals "
        "the concrete property constraints inside referenced shapes that caused the top-level failure."
    )
    pdf.kv_table([
        ("In scope", "SHACL Core constraints, sh:node referencing, nested references, property-level sh:node, direct and referenced failures, diamond references, reports with or without sh:detail."),
        ("Out of scope", "SPARQL constraints and full support for all SHACL logical constructs such as sh:and, sh:or, sh:not, sh:xone, and qualified value shapes."),
        ("Primary user question", "Which exact path, value, component, and referenced-shape chain explains this validation failure?"),
    ])

    pdf.h2("Goal coverage")
    for item in [
        "Identifies exact failed property constraints such as minCount, datatype, pattern, in, and maxCount.",
        "Shows sh:path and offending sh:value where SHACL provides a value.",
        "Preserves the chain of referenced shapes through nested sh:node constraints.",
        "Aims to find all reachable leaf failures so users can fully repair the data.",
        "Deduplicates repeated leaf failures while preserving alternate reference paths.",
    ]:
        pdf.bullet(item)

    pdf.h1("2. Pipeline")
    pdf.para("The pipeline is intentionally small and reproducible. It accepts a data graph and a shapes graph, runs pySHACL, and then transforms the validation report graph into a user-facing explanation tree.")
    pdf.code(
        "data.ttl + shapes.ttl\n"
        "  -> pyshacl.validate(...)\n"
        "  -> report_graph\n"
        "  -> get top-level sh:result entries\n"
        "  -> expand NodeConstraintComponent results recursively\n"
        "  -> build ReferenceNode / LeafFailure tree\n"
        "  -> deduplicate repeated leaves, preserve alternate paths\n"
        "  -> render as text, JSON, CSV, or summary"
    )
    pdf.kv_table([
        ("Root nodes", "Top-level referencing failures such as NodeConstraintComponent, or direct leaves if pySHACL reports them as top-level failures."),
        ("Internal nodes", "Additional referencing failures discovered through sh:detail or fallback revalidation."),
        ("Leaf nodes", "Concrete SHACL Core failures such as minCount, maxCount, datatype, pattern, class, or in."),
        ("Fallback path", "If sh:detail is absent, the tool revalidates the focus node against the referenced shape to recover missing leaf failures."),
    ])
    pdf.h2("Pipeline by source file")
    pdf.kv_table([
        ("1. cli.py", "Input: data path, shapes path, optional external report, CLI flags. Processing: parses RDF graphs, runs pySHACL or loads a report, applies filters and output options. Output: validation report, rendered terminal output, and optional CSV/report/timing files."),
        ("2. tree.py", "Input: internal design requirements. Processing: defines the explanation-tree dataclasses. Output: ReferenceNode for referencing failures and LeafFailure for concrete SHACL failures."),
        ("3. parser.py", "Input: SHACL report graph. Processing: extracts only direct sh:result entries from the ValidationReport node. Output: top-level ValidationResult roots for expansion."),
        ("4. expander.py", "Input: top-level results, report graph, data graph, shapes graph. Processing: recursively expands sh:node results through sh:detail or fallback revalidation. Output: raw explanation tree."),
        ("5. fallback.py", "Input: target focus/value node, referenced shape, data graph, shapes graph. Processing: builds a targeted shapes graph and revalidates when sh:detail is absent. Output: reconstructed validation results with concrete leaves."),
        ("6. deduplicator.py", "Input: raw explanation tree. Processing: removes duplicate leaves, merges repeated reference siblings, and preserves alternate chains. Output: deduplicated explanation tree."),
        ("7. renderer.py", "Input: deduplicated explanation tree and output/filter flags. Processing: shortens prefixes, filters, summarizes, formats, and generates repair hints. Output: text tree, JSON, CSV, or summary."),
        ("8. cli.py", "Input: rendered result plus timing/statistics. Processing: prints output and writes optional artifacts. Output: user-facing terminal result, saved report, CSV export, or timing CSV."),
    ], col1=105, col2=395, size=8.5)

    pdf.h2("Compact module input/output view")
    pdf.kv_table([
        ("cli.py", "Input: data graph, shapes graph, optional external report, CLI options. Output: validation report and final user-facing output."),
        ("tree.py", "Input: conceptual explanation-tree structure. Output: shared ReferenceNode and LeafFailure data model."),
        ("parser.py", "Input: SHACL validation report graph. Output: root validation results."),
        ("expander.py", "Input: root results plus report/data/shapes graphs. Output: explanation tree."),
        ("fallback.py", "Input: focus or value node and referenced shape. Output: reconstructed nested validation results."),
        ("deduplicator.py", "Input: explanation tree. Output: deduplicated tree with alternate chains preserved."),
        ("renderer.py", "Input: deduplicated tree. Output: text, JSON, CSV, summary, and repair hints."),
    ], col1=120, col2=380, size=8.5)

    pdf.h1("3. Implemented Features")
    pdf.kv_table([
        ("Text tree output", "Readable explanation tree with focus node, reference path, referenced shape, leaf path, component, value, message, and alternate paths."),
        ("JSON output", "Machine-readable representation of reference and leaf nodes."),
        ("CSV export", "Flat leaf-failure export with focus node, reference chain, path, component, value, message, kind, and repair hint."),
        ("Summary mode", "Counts roots, reference nodes, leaf failures, direct vs referenced failures, triples, validation results, top paths, components, and reference paths."),
        ("Filtering", "Filter by focus node, leaf path, component, or reference path."),
        ("Output limiting", "Limit displayed explanation roots for large reports."),
        ("Repair hints", "Actionable hints for common Core constraints such as minCount, maxCount, datatype, pattern, class, and in."),
        ("Raw report export", "Save the pySHACL validation report graph as Turtle for comparison and audit."),
        ("Timing CSV", "Export parse, validation, tree-building, rendering, triples, and result counts for reproducibility."),
        ("Dynamic prefixes", "Uses prefixes from loaded RDF graphs, with built-in support for ex, ub, sh, and xsd."),
    ])

    pdf.h2("Apache Jena compatibility")
    pdf.kv_table([
        ("External report input", "The CLI can load an existing SHACL validation report with --report instead of always running pySHACL. This allows reports produced by Apache Jena SHACL to be explained."),
        ("No sh:detail fallback", "Jena reports may not include pySHACL-style nested sh:detail results. The fallback path revalidates the relevant node against the referenced shape to recover concrete leaf failures."),
        ("Node-shape sourceShape", "Jena-style reports may set sh:sourceShape to the enclosing node shape while sh:resultPath identifies the property constraint. The expander uses the original shapes graph to find the matching property shape and its sh:node target."),
        ("Property-level sh:node", "When a property-level sh:node fails, the referenced shape applies to sh:value, not necessarily to sh:focusNode. The pipeline revalidates the value node so the explanation points to the real broken resource."),
        ("Supported formats", "The report parser accepts RDF formats through --report-format, for example turtle for .ttl reports or xml for RDF/XML reports."),
        ("Jena fixture", "test_cases/jena_report_tc7_node_source_no_detail.ttl simulates a Jena-style report for the property-level worksFor -> CompanyShape case."),
    ], col1=145, col2=355, size=8.5)

    pdf.h2("Command examples")
    pdf.code(
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl\n"
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl --summary --top 5\n"
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl --limit 20 --hints\n"
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl --path ub:name\n"
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl --reference-path ub:doctoralDegreeFrom\n"
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl --csv failures.csv --timing-csv timings.csv"
    )
    pdf.h2("Apache Jena command examples")
    pdf.code(
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl \\\n"
        "  --report jena_report.ttl --report-format turtle\n\n"
        "python3 -m shacl_explainer.cli data.ttl shapes.ttl \\\n"
        "  --report jena_report.rdf --report-format xml\n\n"
        "python3 -m shacl_explainer.cli test_cases/tc7_property_node.ttl \\\n"
        "  test_cases/tc7_property_node.ttl \\\n"
        "  --report test_cases/jena_report_tc7_node_source_no_detail.ttl --hints"
    )

    pdf.h1("4. Output Formats")
    pdf.kv_table([
        ("Text tree", "Best for human inspection and thesis examples."),
        ("Summary", "Best for large datasets and evaluation tables."),
        ("JSON", "Best for downstream tooling or UI integration."),
        ("CSV", "Best for spreadsheet analysis and quantitative thesis results."),
        ("Raw report TTL", "Best for comparing the explainer with the original pySHACL report."),
        ("Timing CSV", "Best for reproducibility and performance evaluation."),
    ])
    pdf.h2("Example text tree")
    pdf.code(
        "via ex:CompanyShape  path=ex:worksFor  focus=ex:alice\n"
        "   [minCount]  path=ex:legalName\n"
        "      -> ex:legalName is required\n"
        "      repair: Add at least one ex:legalName value to ex:alice."
    )

    pdf.h1("5. Test Coverage")
    pdf.para("The tool is covered by automated unittest tests. At the time of this report, the suite contains 24 tests and passes successfully.")
    pdf.kv_table([
        ("TC1", "Single sh:node reference with one hidden leaf failure."),
        ("TC2", "Multiple leaf failures under one referenced shape."),
        ("TC3", "Two-level reference chain: ContractorShape -> EmployeeShape -> PersonShape."),
        ("TC4", "Mixed direct and nested violations on the same focus node."),
        ("TC5", "Diamond reference with deduplication and alternate-path preservation."),
        ("TC6", "Complex organization case with deeper nesting, sibling references, direct failures, and diamond reuse."),
        ("TC7", "Property-level sh:node, matching the pattern discovered in the supervisor LUBM schema."),
        ("Fallback tests", "Remove all sh:detail triples and verify that revalidation reconstructs the missing leaves."),
        ("CLI tests", "Summary mode, limits, focus/path/component/reference filters, CSV export, raw report export, and timing CSV."),
    ])
    pdf.h2("Test case files")
    pdf.para(
        "The .ttl files below form the controlled evidence base for the thesis. Each file isolates one behavior "
        "that the explanation pipeline should handle, from simple hidden leaves to Jena-style external reports."
    )
    pdf.kv_table([
        ("testdata.ttl", "Small valid baseline data graph used to confirm that the CLI correctly reports conforming data."),
        ("testshapes.ttl", "Companion baseline shapes graph for testdata.ttl; useful for checking the no-violation path."),
        ("tc1_single_leaf.ttl", "Minimal sh:node case where one concrete datatype failure is hidden behind a referencing result."),
        ("tc2_multi_leaf.ttl", "One referenced shape produces several concrete leaf failures, testing complete leaf recovery."),
        ("tc3_two_level.ttl", "Nested reference chain, ContractorShape -> EmployeeShape, used to verify multi-level expansion."),
        ("tc4_mixed.ttl", "Combines direct property failures with nested referenced-shape failures on the same data node."),
        ("tc5_diamond.ttl", "Diamond-shaped reference graph that tests deduplication and preservation of alternate reference chains."),
        ("tc6_complex_org.ttl", "Larger organization example with deeper nesting, sibling references, direct failures, and repeated shapes."),
        ("tc7_property_node.ttl", "Property-level sh:node case where the referenced value node must be revalidated, matching the LUBM pattern."),
        ("tc8_cycle_property_paths.ttl", "Pathological cyclic reference case used to prove that the cycle guard stops repeated expansion."),
        ("external_report_tc2_no_detail.ttl", "External report fixture with sh:detail removed, testing fallback reconstruction for TC2."),
        ("external_report_tc7_property_no_detail.ttl", "External report fixture for property-level sh:node without sh:detail, testing value-node fallback."),
        ("jena_report_tc7_node_source_no_detail.ttl", "Apache Jena-style report where sourceShape points to the node shape and resultPath identifies the property shape."),
    ], col1=205, col2=295, size=8.5)
    pdf.code("python3 -m unittest discover -s tests -v\n\nRan 24 tests\nOK")

    pdf.h1("6. Detailed Stress-Test Rationale")
    pdf.para(
        "The following three tests were added to exercise risks that appear in realistic SHACL deployments: "
        "large reusable shape graphs, property-level references, and cyclic references."
    )
    pdf.h2("TC6: tc6_complex_org.ttl")
    pdf.kv_table([
        ("What it models", "A ProjectLead must satisfy ProjectLeadShape, which references EmploymentShape and SecurityClearanceShape. Those shapes further reference PersonShape and ContactShape."),
        ("Potential issue", "A high-level sh:node failure may hide the actual repair actions across several shapes, such as missing name, invalid age, invalid email, missing employeeId, invalid clearanceLevel, or missing projectCode."),
        ("Why this test exists", "It checks practical completeness: nested references, sibling references, direct property failures, and diamond reuse of PersonShape."),
        ("Pipeline solution", "parser.py selects roots, expander.py recursively expands sh:node details, deduplicator.py removes repeated PersonShape leaves while preserving alternate chains, and renderer.py displays the actionable tree."),
        ("Applicability", "Useful for enterprise or ontology validation where one entity, such as employee, project lead, patient, contract, or professor, is validated through reusable referenced shapes."),
    ], col1=125, col2=375, size=8.5)

    pdf.h2("TC7: tc7_property_node.ttl")
    pdf.kv_table([
        ("What it models", "An Employee has ex:worksFor ex:acme. The worksFor value must satisfy CompanyShape."),
        ("Potential issue", "The failing node is the property value ex:acme, not the original focus node ex:alice. Revalidating the wrong node would produce the wrong explanation."),
        ("Why this test exists", "It tests property-level sh:node, the same pattern found in the supervisor LUBM schema where degree properties point to UniversityShape."),
        ("Pipeline solution", "expander.py detects the property path and uses sh:value as the target for fallback revalidation. The leaf failure becomes ex:legalName minCount on ex:acme."),
        ("Applicability", "Applies whenever a property value must satisfy another shape: worksFor company, degreeFrom university, order customer, invoice address, patient doctor, and similar object references."),
    ], col1=125, col2=375, size=8.5)

    pdf.h2("TC8: tc8_cycle_property_paths.ttl")
    pdf.kv_table([
        ("What it models", "CycleShape references itself through ex:left and ex:right, while ex:a points back to itself on both properties."),
        ("Potential issue", "Without a cycle guard, expansion could loop forever: CycleShape -> CycleShape -> CycleShape, especially because the same shape is reachable through more than one property path."),
        ("Why this test exists", "It proves the explainer is safe on recursive schemas and pathological inputs, not only clean acyclic examples."),
        ("Pipeline solution", "expander.py keeps a visited set per traversal branch using the focus node and shape. Once ex:a against CycleShape has been expanded in that branch, recursion stops while the concrete ex:required minCount leaf remains visible."),
        ("Applicability", "Applies to recursive models such as organization hierarchies, category trees, folder structures, graph nodes, dependencies, and part-whole relationships."),
    ], col1=125, col2=375, size=8.5)

    pdf.h1("7. Large Dataset Evaluation: LUBM")
    pdf.para("The tool was tested on the supervisor-provided LUBM-style dataset and schema: lubm_skg_1.ttl and schema1.ttl. The data file is about 163 MB. The schema includes property-level sh:node constraints from FullProfessorShape to UniversityShape.")
    pdf.kv_table([
        ("Data file", "/Users/mariyakezdekbayeva/Downloads/lubm_skg_1.ttl"),
        ("Shapes file", "/Users/mariyakezdekbayeva/Downloads/schema1.ttl"),
        ("Explanation roots", "891"),
        ("Reference nodes", "554"),
        ("Leaf failures", "992"),
        ("Leaf path", "ub:name: 992"),
        ("Leaf component", "minCount: 992"),
        ("Reference paths", "ub:doctoralDegreeFrom -> ub:UniversityShape: 307; ub:mastersDegreeFrom -> ub:UniversityShape: 161; ub:undergraduateDegreeFrom -> ub:UniversityShape: 86."),
    ])
    pdf.h2("Performance")
    pdf.kv_table([
        ("Parse data", "19.248 seconds"),
        ("Parse shapes", "0.001 seconds"),
        ("Validate", "0.811 seconds"),
        ("Build explanation tree", "0.070 seconds"),
        ("Render summary", "0.006 seconds"),
        ("Interpretation", "The expensive step is loading the 163 MB Turtle data graph; the explanation algorithm itself is fast on this report."),
    ])
    pdf.h2("LUBM interpretation")
    pdf.para(
        "The summary shows that the concrete repair action is consistently missing ub:name values. Many failures are reached through professor degree properties that point to university resources. The explainer therefore converts a broad FullProfessor validation failure into actionable repairs on referenced university nodes."
    )

    pdf.h1("8. Why The Tool Works As Expected")
    pdf.kv_table([
        ("Completeness within scope", "The controlled tests show all reachable leaf failures for single, multiple, nested, mixed, diamond, property-level, and fallback cases."),
        ("Usability", "The tree output answers where the failure happened, which value/path is involved, and how it was reached."),
        ("Reproducibility", "Automated tests, timing CSV, raw report export, and summary mode support repeatable evaluation."),
        ("Scalability evidence", "The LUBM run demonstrates behavior on a large real dataset; tree construction and rendering are small compared with RDF parsing."),
        ("Honest limitation", "The implementation focuses on sh:node-based SHACL Core references; other logical SHACL Core constructs are future work."),
    ])

    pdf.h1("9. Recommended Presentation Points")
    for item in [
        "Start with TC2 or TC3 to show the explanation tree on a simple case.",
        "Show TC5 or TC6 to demonstrate deduplication and multi-level references.",
        "Show TC7 to prove property-level sh:node support, which appears in the supervisor schema.",
        "Use the LUBM summary table to demonstrate practical scale and quantitative evidence.",
        "Emphasize that the tool does not replace pySHACL; it turns pySHACL's report into actionable root-cause explanations.",
    ]:
        pdf.bullet(item)

    pdf.build()


if __name__ == "__main__":
    build_report()
    print(OUT)
