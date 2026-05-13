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

If the data is valid, the CLI prints:

```text
✓ Data is valid.
```

If the data is invalid, the CLI prints an explanation tree.

## Example

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
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

External-report helper files:

- `all_test_cases/external_report_cases/tc41_data_shapes.ttl`
- `all_test_cases/external_report_cases/tc43_data_shapes.ttl`

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
Ran 32 tests
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
