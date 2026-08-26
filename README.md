# Root Cause Localization for Referencing Constraints in SHACL

This project is a thesis prototype for explaining SHACL validation failures that involve referencing constraints, especially `sh:node`.

Standard SHACL validation reports can tell a user that a referenced shape failed, but they do not always make it easy to see the concrete property-level failures inside that referenced shape. This tool turns those reports into an explanation tree that shows:

- which exact SHACL Core constraint failed,
- on which `sh:path`,
- on which value node, when available,
- through which chain of referenced shapes the failure was reached,
- and what concrete repairs are needed.

## Scope

The current implementation focuses on:

- SHACL Core constraints,
- `sh:node` referencing constraints,
- nested referencing chains,
- property-level `sh:node`,
- multiple referenced-shape failures on the same focus node,
- diamond-shaped references,
- reports with or without `sh:detail`,
- Apache Jena-style external SHACL reports.

Out of scope for now:

- SHACL SPARQL constraints,
- full support for logical constraint families such as `sh:and`, `sh:or`, `sh:not`, `sh:xone`,
- full support for `sh:qualifiedValueShape`,
- advanced SHACL property paths beyond what the current report/fallback logic can reconstruct.

## Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Basic Usage

Run the explainer with a data graph and a shapes graph:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl
```

The data graph, shapes graph, and external report can also be loaded from a
trusted `.pkl`/`.pickle` file if it contains an `rdflib.Graph`. This is useful
for large datasets because it skips Turtle parsing:

```bash
python3 -m shacl_explainer.cli DATA.pkl SHAPES.ttl --summary --timing
```

Many test files in this repository contain both data and shapes in the same Turtle file. For those, pass the same file twice:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc1_single_leaf.ttl \
  all_test_cases/sh_node_cases/tc1_single_leaf.ttl
```

When the data conforms, the CLI reports that and exits without building a tree:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/testdata.ttl \
  all_test_cases/sh_node_cases/testshapes.ttl
```

```text
✓ Data is valid.
```

When it does not conform, the CLI prints an explanation tree.

## Example

Property-level `sh:node`, with repair hints enabled:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  --hints
```

```text
Focus node: ex:alice/
└── sh:node ex:CompanyShape  path=ex:worksFor/
    └── ❌ minCount    ex:legalName = (missing)
        ├── via ex:CompanyShape
        ├── message: ex:legalName is required
        └── → fix: Add at least one ex:legalName value to ex:acme.
```

This means `ex:alice` failed through the property `ex:worksFor`, because the value node `ex:acme` did not satisfy `ex:CompanyShape`. The standard SHACL report only states that `ex:CompanyShape` was violated; the `minCount` line, the offending value node, and the repair are what this tool recovers.

Each tree is rooted at a focus node. Every `sh:node` hop is shown as its own level, the `❌` line names the failing SHACL Core component and the leaf path, and the `via` line spells out the full chain of referenced shapes that reached it. Two nested levels, without `--hints`:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc3_two_level.ttl \
  all_test_cases/sh_node_cases/tc3_two_level.ttl
```

```text
Focus node: ex:carol/
└── sh:node ex:ContractorShape/
    └── sh:node ex:EmployeeShape/
        └── ❌ datatype    ex:age = "thirty-one"
            ├── via ex:ContractorShape -> ex:EmployeeShape -> ex:PersonShape
            └── message: ex:age must be an xsd:integer
```

## Output Modes

Three rendering formats are selected with `--format`, and `--summary` overrides the
format with aggregate counts.

| Mode | Flag | Description |
|---|---|---|
| Text tree | `--format text` (default) | Unicode explanation tree, optionally colorized |
| JSON | `--format json` | Machine-readable nested tree |
| HTML | `--format html` | Self-contained interactive report |
| Summary | `--summary` | Aggregate counts and top-N tables |

Text tree output:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl
```

Repair hints (text mode only):

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --hints
```

JSON output:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --format json
```

```json
[
  {
    "type": "reference",
    "focusNode": "ex:alice",
    "shape": "ex:CompanyShape",
    "referencedShape": "ex:CompanyShape",
    "path": "ex:worksFor",
    "refChain": [],
    "children": [
      {
        "type": "leaf",
        "focusNode": "ex:acme",
        "path": "ex:legalName",
        "component": "sh:MinCountConstraintComponent",
        "message": "ex:legalName is required",
        "repairHint": "Add at least one ex:legalName value to ex:acme.",
        "refChain": ["ex:CompanyShape"],
        "altChains": []
      }
    ]
  }
]
```

Summary output:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --summary
```

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHACL Explanation Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Focus nodes affected  : 1
Total leaf failures   : 1  (1 via sh:node,  0 direct)
Unique paths failing  : 1
Max reference depth   : 1 level

Input
  Data triples        : 15
  Shape triples       : 17
  Pyshacl results     : 2  (1 top-level)

Top failing paths
      1  ex:legalName                    minCount
...
```

Limit each summary table to the top N rows:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --summary --top 10
```

CSV export (one row per leaf failure):

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --csv failures.csv
```

```text
focus_node,depth,reference_chain,alternate_reference_chains,leaf_path,component,value,message,kind,repair_hint
ex:acme,1,ex:CompanyShape,,ex:legalName,sh:MinCountConstraintComponent,,ex:legalName is required,referenced,Add at least one ex:legalName value to ex:acme.
```

Save the raw validation report:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --save-report report.ttl
```

Timing information (printed to stderr):

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --summary --timing
```

Timing CSV:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --timing-csv timings.csv
```

### Writing Output to a File

By default the rendered explanation goes to stdout. `--output` redirects it to a file
instead (the confirmation line goes to stderr, so it never pollutes redirected output):

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --format json --output tree.json
```

For `--format html`, a bare filename with no directory component is placed inside
`html_outputs/` automatically; paths containing a directory are used as given.

### Colorized Text Output

Text-tree output is colorized when stdout is a terminal. `--color` overrides the
detection, which is useful when piping into a pager or capturing output for a report:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --color always | less -R
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --color never > tree.txt
```

Color is only applied to the plain text tree — JSON, HTML, summary, and `--output`
runs are always uncolored.

## HTML Report

`--format html` renders a single self-contained HTML file with no external
dependencies: the explanation tree is embedded as JSON in the page and all styling
and interaction is inlined, so the report can be opened directly from disk or handed
over as a standalone artifact.

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl \
  all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl \
  --format html --output tc53_deep_gradient_graph.html
```

The report provides:

- an **analytical view** listing failures with summary statistics and a breakdown table,
- a **graph view** drawing the reference chains, with colors cycling by nesting depth,
- a sidebar with **By focus**, **By issue**, and **All** tabs plus focus-node search,
- interactive filters on component, leaf path, reference path, shape, and direct-vs-referenced kind,
- a light/dark theme toggle,
- a provenance header recording the data file, shapes file, generation timestamp, and the git commit the report was produced from.

Pre-generated reports for every test case and every LUBM combination are committed
under [`html_outputs/`](html_outputs/) (59 files).

## Input Formats

Data, shapes, and external reports are parsed as Turtle by default. Use the matching
flag to load another RDF serialization, e.g. `xml`, `json-ld`, or `nt`:

```bash
python3 -m shacl_explainer.cli data.rdf shapes.ttl --data-format xml
python3 -m shacl_explainer.cli data.ttl shapes.jsonld --shapes-format json-ld
```

| Flag | Applies to | Default |
|---|---|---|
| `--data-format` | Data graph | `turtle` |
| `--shapes-format` | Shapes graph | `turtle` |
| `--report-format` | External `--report` graph | `turtle` |

These flags are ignored for `.pkl`/`.pickle` inputs, which are unpickled directly.

## Filters

Filter by focus node:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --focus ex:alice
```

Filter by leaf path:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --path ex:name
```

Filter by component:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --component minCount
```

Filter by reference path:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --reference-path ex:worksFor
```

Limit printed explanation roots:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --limit 20
```

Filters compose, and `--csv` is written before `--limit` is applied, so a CSV export
always contains the full filtered result set even when the printed tree is truncated:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl \
  --component minCount --reference-path ex:worksFor --limit 5 --csv failures.csv
```

## CLI Reference

```text
python3 -m shacl_explainer.cli DATA SHAPES [options]
```

| Option | Description |
|---|---|
| `DATA`, `SHAPES` | Positional: data graph and shapes graph (`.ttl`, another RDF format via `--data-format`/`--shapes-format`, or a pickled `rdflib.Graph`) |
| `--format {text,json,html}` | Output format (default `text`) |
| `--output PATH` | Write rendered output to a file instead of stdout |
| `--summary` | Print aggregate counts instead of the tree |
| `--top N` | Limit each summary table to the top N entries |
| `--hints` | Add repair hints to text output |
| `--color {auto,always,never}` | Colorize the text tree (default `auto`: on only for terminals) |
| `--limit N` | Limit the number of top-level explanation roots printed |
| `--focus URI` | Show only roots for this focus node |
| `--path URI` | Show only leaf failures on this leaf path |
| `--component NAME` | Show only leaf failures for this component, e.g. `minCount` |
| `--reference-path URI` | Show only failures reached through this referencing property |
| `--csv PATH` | Write leaf failures to CSV |
| `--save-report PATH` | Save the raw validation report graph as Turtle |
| `--report PATH` | Explain an existing report instead of running pySHACL |
| `--data-format FMT` | RDF format of the data graph (default `turtle`) |
| `--shapes-format FMT` | RDF format of the shapes graph (default `turtle`) |
| `--report-format FMT` | RDF format of the `--report` graph (default `turtle`) |
| `--timing` | Print parse, validation, build, and render timings to stderr |
| `--timing-csv PATH` | Write reproducibility and timing metrics to CSV |

A third positional argument is still accepted as a deprecated way of setting the output
format (`... DATA.ttl SHAPES.ttl json`). It is retained for backward compatibility with
earlier scripts; `--format` takes precedence and should be preferred.

## Apache Jena Report Compatibility

The tool can explain an existing SHACL validation report instead of running pySHACL directly. This is useful for Apache Jena SHACL reports.

Turtle report:

```bash
python3 -m shacl_explainer.cli data.ttl shapes.ttl \
  --report jena_report.ttl \
  --report-format turtle
```

RDF/XML report:

```bash
python3 -m shacl_explainer.cli data.ttl shapes.ttl \
  --report jena_report.rdf \
  --report-format xml
```

Local Jena-style fixture:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  --report all_test_cases/sh_node_cases/jena_report_tc7_node_source_no_detail.ttl \
  --hints
```

The Jena compatibility path handles reports where:

- `sh:detail` is absent,
- `sh:sourceShape` points to the enclosing node shape,
- `sh:resultPath` identifies the failing property,
- `sh:value` is the node that must be revalidated against the referenced shape.

When `--report` is supplied, pySHACL is not used to produce the top-level report. It is
still used internally by `fallback.py`, which re-validates the referenced value node
against a minimal targeted copy of the referenced shape in order to reconstruct the
nested results the external report omitted.

## Pipeline

| Module | Input | Output |
|---|---|---|
| `cli.py` | Data graph, shapes graph, optional external report, CLI options | Validation report and final user-facing output |
| `tree.py` | Explanation-tree structure | `ReferenceNode` and `LeafFailure` data model |
| `parser.py` | SHACL validation report graph | Top-level validation results |
| `expander.py` | Root results plus report/data/shapes graphs | Explanation tree |
| `fallback.py` | Focus/value node and referenced shape | Reconstructed nested validation results |
| `deduplicator.py` | Explanation tree | Deduplicated tree with alternate chains preserved |
| `renderer.py` | Deduplicated tree | Text tree, JSON, HTML, CSV, summary, and repair hints |
| `report_template.html` | — | Static template that `renderer.py` fills in to produce the HTML report |

## Test Cases

All fixtures are grouped under `all_test_cases/`.

| Folder | Purpose |
|---|---|
| `all_test_cases/sh_node_cases/` | Original `sh:node` and referencing-constraint cases |
| `all_test_cases/direct_constraint_cases/` | Direct SHACL Core violations without `sh:node` |
| `all_test_cases/mixed_constraint_cases/` | Reports containing both direct and referenced failures |
| `all_test_cases/multi_focus_cases/` | Multiple focus nodes and repeated violations |
| `all_test_cases/property_path_cases/` | Inverse, sequence, alternative, and zero-or-more paths |
| `all_test_cases/severity_cases/` | `sh:Violation`, `sh:Warning`, and `sh:Info` |
| `all_test_cases/message_metadata_cases/` | Missing, multiple, language-tagged messages, and shape metadata |
| `all_test_cases/external_report_cases/` | pySHACL, Jena-style, TopBraid-like, and incomplete external reports |
| `all_test_cases/cycle_cases/` | Recursive and cyclic shape references |
| `all_test_cases/scale_cases/` | Synthetic scale and performance-oriented cases |

### Numbered Test Case Inventory

| ID | File | Purpose |
|---|---|---|
| TC1 | `all_test_cases/sh_node_cases/tc1_single_leaf.ttl` | Single hidden leaf failure under `sh:node` |
| TC2 | `all_test_cases/sh_node_cases/tc2_multi_leaf.ttl` | Multiple hidden leaf failures under one referenced shape |
| TC3 | `all_test_cases/sh_node_cases/tc3_two_level.ttl` | Two-level `sh:node` reference chain |
| TC4 | `all_test_cases/sh_node_cases/tc4_mixed.ttl` | Multiple `sh:node` branches on one focus node |
| TC5 | `all_test_cases/sh_node_cases/tc5_diamond.ttl` | Diamond reference pattern and deduplication |
| TC6 | `all_test_cases/sh_node_cases/tc6_complex_org.ttl` | Complex organization hierarchy with deeper nested references |
| TC7 | `all_test_cases/sh_node_cases/tc7_property_node.ttl` | Property-level `sh:node` where the value node is revalidated |
| TC8 | `all_test_cases/sh_node_cases/tc8_cycle_property_paths.ttl` | Cycle guard for recursive property-path references |
| TC9 | `all_test_cases/direct_constraint_cases/tc9_direct_min_count.ttl` | Direct `sh:minCount` |
| TC10 | `all_test_cases/direct_constraint_cases/tc10_direct_max_count.ttl` | Direct `sh:maxCount` |
| TC11 | `all_test_cases/direct_constraint_cases/tc11_direct_datatype.ttl` | Direct `sh:datatype` |
| TC12 | `all_test_cases/direct_constraint_cases/tc12_direct_class.ttl` | Direct `sh:class` |
| TC13 | `all_test_cases/direct_constraint_cases/tc13_direct_pattern.ttl` | Direct `sh:pattern` |
| TC14 | `all_test_cases/direct_constraint_cases/tc14_direct_in.ttl` | Direct `sh:in` |
| TC15 | `all_test_cases/direct_constraint_cases/tc15_direct_node_kind.ttl` | Direct `sh:nodeKind` |
| TC16 | `all_test_cases/direct_constraint_cases/tc16_direct_min_max_inclusive.ttl` | Direct numeric range constraints |
| TC17 | `all_test_cases/direct_constraint_cases/tc17_direct_less_than.ttl` | Direct `sh:lessThan` |
| TC18 | `all_test_cases/direct_constraint_cases/tc18_direct_has_value.ttl` | Direct `sh:hasValue` |
| TC19 | `all_test_cases/direct_constraint_cases/tc19_direct_equals.ttl` | Direct `sh:equals` |
| TC20 | `all_test_cases/direct_constraint_cases/tc20_direct_disjoint.ttl` | Direct `sh:disjoint` |
| TC21 | `all_test_cases/direct_constraint_cases/tc21_direct_closed_shape.ttl` | Direct `sh:closed` |
| TC22 | `all_test_cases/direct_constraint_cases/tc22_direct_logical_constraints.ttl` | Direct `sh:or`, `sh:xone`, and `sh:not` |
| TC23 | `all_test_cases/direct_constraint_cases/tc23_direct_core_mix.ttl` | Multiple direct SHACL Core failures in one shape |
| TC24 | `all_test_cases/mixed_constraint_cases/tc24_mixed_direct_and_node.ttl` | Direct failures and nested `sh:node` failures in one report |
| TC25 | `all_test_cases/mixed_constraint_cases/tc25_mixed_multiple_focus_nodes.ttl` | Mixed failures across multiple focus nodes |
| TC26 | `all_test_cases/mixed_constraint_cases/tc26_mixed_direct_plus_diamond.ttl` | Direct failures plus diamond-shaped nested references |
| TC27 | `all_test_cases/multi_focus_cases/tc27_two_focus_nodes_same_shape.ttl` | Two focus nodes failing the same shape |
| TC28 | `all_test_cases/multi_focus_cases/tc28_many_focus_nodes_same_violation.ttl` | Many focus nodes with the same direct violation |
| TC29 | `all_test_cases/multi_focus_cases/tc29_same_focus_multiple_shapes.ttl` | One focus node validated by multiple shapes |
| TC30 | `all_test_cases/property_path_cases/tc30_inverse_path.ttl` | Inverse property path |
| TC31 | `all_test_cases/property_path_cases/tc31_sequence_path.ttl` | Sequence property path |
| TC32 | `all_test_cases/property_path_cases/tc32_alternative_path.ttl` | Alternative property path |
| TC33 | `all_test_cases/property_path_cases/tc33_zero_or_more_path.ttl` | Zero-or-more property path |
| TC34 | `all_test_cases/severity_cases/tc34_warning_result.ttl` | `sh:Warning` severity |
| TC35 | `all_test_cases/severity_cases/tc35_info_result.ttl` | `sh:Info` severity |
| TC36 | `all_test_cases/severity_cases/tc36_mixed_severities.ttl` | Mixed `Violation`, `Warning`, and `Info` severities |
| TC37 | `all_test_cases/message_metadata_cases/tc37_missing_message.ttl` | Constraint result with no custom message |
| TC38 | `all_test_cases/message_metadata_cases/tc38_multiple_messages.ttl` | Multiple messages on one constraint |
| TC39 | `all_test_cases/message_metadata_cases/tc39_language_tagged_message.ttl` | Language-tagged messages |
| TC40 | `all_test_cases/message_metadata_cases/tc40_named_vs_blank_property_shapes.ttl` | Named and blank property shapes |
| TC41 | `all_test_cases/external_report_cases/tc41_pyshacl_report_with_detail.ttl` | pySHACL-style external report with `sh:detail` |
| TC42 | `all_test_cases/external_report_cases/tc42_jena_report_no_detail.ttl` | Jena-style external report without `sh:detail` |
| TC43 | `all_test_cases/external_report_cases/tc43_jena_property_shape_report.ttl` | Jena-style property-level `sh:node` external report |
| TC44 | `all_test_cases/external_report_cases/tc44_topbraid_like_report.ttl` | TopBraid-like external report naming the referenced shape |
| TC45 | `all_test_cases/external_report_cases/tc45_report_missing_source_shape.ttl` | External report missing `sh:sourceShape` |
| TC46 | `all_test_cases/cycle_cases/tc46_self_recursive_shape.ttl` | Self-recursive shape |
| TC47 | `all_test_cases/cycle_cases/tc47_two_shape_cycle.ttl` | Two-shape recursive cycle |
| TC48 | `all_test_cases/cycle_cases/tc48_cycle_with_leaf_failure.ttl` | Recursive cycle with a concrete leaf failure |
| TC49 | `all_test_cases/cycle_cases/tc49_cycle_without_leaf_failure.ttl` | Recursive cycle without a concrete failure |
| TC50 | `all_test_cases/scale_cases/tc50_100_focus_nodes.ttl` | Synthetic scale case with 100 focus nodes |
| TC51 | `all_test_cases/scale_cases/tc51_many_values_max_count.ttl` | Many values on one property with `sh:maxCount` |
| TC52 | `all_test_cases/scale_cases/tc52_large_diamond_dedup.ttl` | Larger diamond deduplication case |
| TC53 | `all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl` | Eight nested `sh:node` levels for graph color cycling and expansion |

External-report helper files:

- `all_test_cases/external_report_cases/tc41_data_shapes.ttl`
- `all_test_cases/external_report_cases/tc43_data_shapes.ttl`

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
Ran 33 tests
OK
```

| Test module | Tests | Covers |
|---|---:|---|
| `tests/test_cli_pipeline.py` | 30 | End-to-end CLI runs across the test-case corpus, output modes, and filters |
| `tests/test_fallback.py` | 2 | Re-validation when an external report has no `sh:detail` |
| `tests/test_deduplicator.py` | 1 | Diamond-reference deduplication with alternate chains preserved |

## Large Dataset Evaluation

The tool was tested on two supervisor-provided LUBM-style data graphs, each checked
against three progressively larger SHACL shape schemas (six combinations total):

| Dataset | Size | Data triples |
|---|---|---|
| `lubm_skg_1.ttl` | 171 MB | 1,001,716 |
| `lubm_mkg_1.ttl` | 732 MB | 4,258,329 |

| Schema | Shape triples |
|---|---|
| [`lubm_schemas/schema1.ttl`](lubm_schemas/schema1.ttl) | 54 |
| [`lubm_schemas/schema2.ttl`](lubm_schemas/schema2.ttl) | 110 |
| [`lubm_schemas/schema3.ttl`](lubm_schemas/schema3.ttl) | 341 |

Shape-triple counts are taken from `collect_stats` in `cli.py`, which reads
`len(shapes_graph)` after `pyshacl.validate()` has run. pySHACL adds two fixed
RDFS/OWL axiom triples to the shapes graph in place during validation, so parsing
one of the files above standalone gives two fewer triples (52 / 108 / 339) than the
counts above.

The two LUBM data graphs are not committed to this repository because of their size
(171 MB and 732 MB); the shape schemas above are small enough to commit and are
included so the evaluation can be re-run against any LUBM-generated data graph of the
same university-benchmark ontology. The resulting reports in
[`html_outputs/`](html_outputs/) and the full breakdown in
[`lubm_evaluation_results.md`](lubm_evaluation_results.md) are also committed.

Command (one HTML report and one summary+timing run per combination):

```bash
python3 -m shacl_explainer.cli <data> <shapes> --format html --hints --timing --output html_outputs/lubm_<dataset>_<schema>_report.html
python3 -m shacl_explainer.cli <data> <shapes> --summary --timing
```

Timing summary (seconds):

| Dataset x Schema | Parse data | Validate | Build tree | Render |
|---|---:|---:|---:|---:|
| skg1 x schema1 | 18.9 | 0.8 | 0.1 | 0.01 |
| skg1 x schema2 | 19.1 | 61.8 | 9.9 | 0.12 |
| skg1 x schema3 | 19.0 | 91.9 | 16.2 | 0.26 |
| mkg1 x schema1 | 83.9 | 3.3 | 0.3 | 0.01 |
| mkg1 x schema2 | 83.2 | 308.1 | 49.7 | 0.47 |
| mkg1 x schema3 | 93.8 | 469.6 | 70.9 | 1.06 |

Explanation output summary:

| Dataset x Schema | Focus nodes affected | Leaf failures (via sh:node / direct) |
|---|---:|---|
| skg1 x schema1 | 890 | 992 (655 / 337) |
| skg1 x schema2 | 6,281 | 10,099 (8,781 / 1,318) |
| skg1 x schema3 | 15,950 | 21,170 (17,043 / 4,127) |
| mkg1 x schema1 | 933 | 968 (958 / 10) |
| mkg1 x schema2 | 25,058 | 39,736 (35,597 / 4,139) |
| mkg1 x schema3 | 67,561 | 87,396 (69,729 / 17,667) |

**Interpretation:** parse time scales with data size alone and stays constant across
schemas on the same dataset. Validate and tree-build time instead scale with schema
complexity: schema2/schema3 add `ub:takesCourse`/`ub:teachingAssistantOf` constraints
that apply to a much larger population than schema1's degree-granting-university
constraints, growing pySHACL's result count (and validate/build time) by roughly two
orders of magnitude. Across every combination, the dominant repair action remains
missing `ub:name` values reached through degree properties into `ub:UniversityShape`,
with schema2/schema3 adding a second dominant story around missing `ub:type` reached
through course shapes. Full per-combination breakdowns (top failing paths, reference
paths, and reference chains) are in [`lubm_evaluation_results.md`](lubm_evaluation_results.md).

## Generated Artifacts

Committed outputs, so the results can be inspected without re-running the tool:

| Path | Contents |
|---|---|
| [`html_outputs/`](html_outputs/) | Interactive HTML reports: one per test case (TC1–TC53) plus six LUBM dataset × schema combinations |
| [`output_mode_examples/`](output_mode_examples/) | Reference samples of the non-HTML output modes |
| [`lubm_evaluation_results.md`](lubm_evaluation_results.md) | Full per-combination LUBM breakdown behind the summary tables above |

The output-mode samples were produced with:

```bash
# JSON tree
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  --format json --output output_mode_examples/tc7_property_node.json

# Summary
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl \
  all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl \
  --summary > output_mode_examples/tc53_deep_gradient_graph_summary.txt

# Failure CSV and timing CSV
python3 -m shacl_explainer.cli \
  all_test_cases/scale_cases/tc50_100_focus_nodes.ttl \
  all_test_cases/scale_cases/tc50_100_focus_nodes.ttl \
  --csv output_mode_examples/tc50_100_focus_nodes_failures.csv \
  --timing-csv output_mode_examples/tc50_100_focus_nodes_timings.csv
```

Re-running these reproduces the same content, with two expected differences: CSV row
order varies between runs (the tree is walked over unordered RDF node sets), and the
timing columns naturally differ per machine and run.

## Repository

GitHub repository:

```text
https://github.com/mariyakez/Root-Cause-Localization-for-Referencing-Constraints-in-SHACL.git
```
