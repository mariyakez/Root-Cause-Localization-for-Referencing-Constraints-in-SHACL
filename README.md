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

Many test files in this repository contain both data and shapes in the same Turtle file. For those, pass the same file twice:

```bash
python3 -m shacl_explainer.cli \
  test_cases/tc1_single_leaf.ttl \
  test_cases/tc1_single_leaf.ttl
```

If the data is valid, the CLI prints:

```text
✓ Data is valid.
```

If the data is invalid, the CLI prints an explanation tree.

## Example

```bash
python3 -m shacl_explainer.cli \
  test_cases/tc7_property_node.ttl \
  test_cases/tc7_property_node.ttl \
  --hints
```

Example output:

```text
via ex:CompanyShape  path=ex:worksFor  focus=ex:alice
   ❌ [minCount]  path=ex:legalName
      → ex:legalName is required
      repair: Add at least one ex:legalName value to ex:acme.
```

This means `ex:alice` failed through the property `ex:worksFor`, because the value node `ex:acme` did not satisfy `ex:CompanyShape`.

## Output Modes

Text tree output:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl
```

JSON output:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --format json
```

Summary output:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --summary
```

Repair hints:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --hints
```

CSV export:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --csv failures.csv
```

Save the raw validation report:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --save-report report.ttl
```

Timing information:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --summary --timing
```

Timing CSV:

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --timing-csv timings.csv
```

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
  test_cases/tc7_property_node.ttl \
  test_cases/tc7_property_node.ttl \
  --report test_cases/jena_report_tc7_node_source_no_detail.ttl \
  --hints
```

The Jena compatibility path handles reports where:

- `sh:detail` is absent,
- `sh:sourceShape` points to the enclosing node shape,
- `sh:resultPath` identifies the failing property,
- `sh:value` is the node that must be revalidated against the referenced shape.

## Pipeline

| Module | Input | Output |
|---|---|---|
| `cli.py` | Data graph, shapes graph, optional external report, CLI options | Validation report and final user-facing output |
| `tree.py` | Explanation-tree structure | `ReferenceNode` and `LeafFailure` data model |
| `parser.py` | SHACL validation report graph | Top-level validation results |
| `expander.py` | Root results plus report/data/shapes graphs | Explanation tree |
| `fallback.py` | Focus/value node and referenced shape | Reconstructed nested validation results |
| `deduplicator.py` | Explanation tree | Deduplicated tree with alternate chains preserved |
| `renderer.py` | Deduplicated tree | Text, JSON, CSV, summary, and repair hints |

## Test Cases

| File | Purpose |
|---|---|
| `test_cases/testdata.ttl` | Valid baseline data graph |
| `test_cases/testshapes.ttl` | Baseline shapes graph |
| `test_cases/tc1_single_leaf.ttl` | One hidden leaf failure under `sh:node` |
| `test_cases/tc2_multi_leaf.ttl` | Multiple hidden leaf failures under one referenced shape |
| `test_cases/tc3_two_level.ttl` | Two-level reference chain |
| `test_cases/tc4_mixed.ttl` | Multiple `sh:node` branches on the same focus node |
| `test_cases/tc5_diamond.ttl` | Diamond reference pattern and deduplication |
| `test_cases/tc6_complex_org.ttl` | Larger organization example with deeper nesting, repeated shapes, and all failures reached through `sh:node` |
| `test_cases/tc7_property_node.ttl` | Property-level `sh:node` where the value node must be revalidated |
| `test_cases/tc8_cycle_property_paths.ttl` | Cyclic property references and cycle-guard behavior |
| `test_cases/external_report_tc2_no_detail.ttl` | External report without `sh:detail` |
| `test_cases/external_report_tc7_property_no_detail.ttl` | Property-level external report without `sh:detail` |
| `test_cases/jena_report_tc7_node_source_no_detail.ttl` | Apache Jena-style external report fixture |

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
Ran 24 tests
OK
```

## Large Dataset Evaluation

The tool was tested on the supervisor-provided LUBM-style dataset:

- data file: `/Users/mariyakezdekbayeva/Downloads/lubm_skg_1.ttl`
- shapes file: `/Users/mariyakezdekbayeva/Downloads/schema1.ttl`
- data size: approximately 163 MB

Command:

```bash
python3 -m shacl_explainer.cli \
  /Users/mariyakezdekbayeva/Downloads/lubm_skg_1.ttl \
  /Users/mariyakezdekbayeva/Downloads/schema1.ttl \
  --summary \
  --timing
```

Observed result:

```text
Explanation roots: 891
Reference nodes: 554
Leaf failures: 992

By leaf path:
    992  ub:name

By leaf component:
    992  minCount

By reference path:
    307  ub:doctoralDegreeFrom -> ub:UniversityShape
    161  ub:mastersDegreeFrom -> ub:UniversityShape
     86  ub:undergraduateDegreeFrom -> ub:UniversityShape
```

Interpretation: the concrete repair action is consistently missing `ub:name` values, many reached through professor degree properties that reference `ub:UniversityShape`.

## Thesis Report

The generated feature report is available as:

```text
SHACL_Explainer_Feature_Report.pdf
```

Regenerate it with:

```bash
python3 build_feature_report.py
```

## Repository

GitHub repository:

```text
https://github.com/mariyakez/Root-Cause-Localization-for-Referencing-Constraints-in-SHACL.git
```
