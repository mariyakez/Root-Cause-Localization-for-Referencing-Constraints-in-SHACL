# SHACL Explainer Progress Log

This file tracks implemented changes and thesis-relevant progress. Add a new
entry whenever a feature, test case, output format, or compatibility improvement
is added.

## 2026-05-13

### Pickled RDF Graph Input

Added `.pkl`/`.pickle` loading for graph inputs when the file contains a
trusted `rdflib.Graph`. This lets large pre-parsed datasets skip Turtle parsing
and go directly into validation.

Updated:

- `shacl_explainer/cli.py`
- `tests/test_cli_pipeline.py`
- `README.md`

Example:

```bash
python3 -m shacl_explainer.cli DATA.pkl SHAPES.ttl --summary --timing
```

Test coverage:

- Added `test_pickle_data_graph_input`
- Full suite now passes with `33 tests OK`

### Unified Test Case Folder

Moved all test case groups under one parent folder:

```text
all_test_cases/
```

Current structure:

- `all_test_cases/sh_node_cases/`
- `all_test_cases/direct_constraint_cases/`
- `all_test_cases/mixed_constraint_cases/`
- `all_test_cases/multi_focus_cases/`
- `all_test_cases/property_path_cases/`
- `all_test_cases/severity_cases/`
- `all_test_cases/message_metadata_cases/`
- `all_test_cases/external_report_cases/`
- `all_test_cases/cycle_cases/`
- `all_test_cases/scale_cases/`

Updated automated tests and documentation references to use the new paths.

### Complete Test Case Inventory

The project now has numbered test coverage from `tc1` through `tc52`, grouped
under `all_test_cases/`.

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

External report helper files:

- `all_test_cases/external_report_cases/tc41_data_shapes.ttl`
- `all_test_cases/external_report_cases/tc43_data_shapes.ttl`

### Broader SHACL Test Case Groups

Added new folders to cover more situations users may face when validating RDF
with SHACL:

- `all_test_cases/mixed_constraint_cases/`
- `all_test_cases/multi_focus_cases/`
- `all_test_cases/property_path_cases/`
- `all_test_cases/severity_cases/`
- `all_test_cases/message_metadata_cases/`
- `all_test_cases/external_report_cases/`
- `all_test_cases/cycle_cases/`
- `all_test_cases/scale_cases/`

These groups cover mixed direct/referenced failures, multiple focus nodes,
complex property paths, severities, message metadata, external report formats,
recursive/cyclic shapes, and scale-oriented examples.

Added test coverage to run these cases in summary mode and verify that external
report compatibility examples still produce expected leaf paths.

### Direct SHACL Core Constraint Coverage

Added `all_test_cases/direct_constraint_cases/` to test direct validation failures that do not
involve `sh:node`.

Covered constraints:

- `sh:minCount`
- `sh:maxCount`
- `sh:datatype`
- `sh:class`
- `sh:pattern`
- `sh:in`
- `sh:nodeKind`
- `sh:minInclusive`
- `sh:maxInclusive`
- `sh:lessThan`
- `sh:hasValue`
- `sh:equals`
- `sh:disjoint`
- `sh:closed`
- `sh:or`
- `sh:xone`
- `sh:not`

Added regression coverage confirming these cases report `0 via sh:node`.

### HTML Report Usability

Improved `shacl_explainer/report_template.html`.

Added:

- Search bar in the focus-node sidebar.
- Resizable focus-node panel.
- Sidebar width persistence using `localStorage`.
- Canonical package template loaded by `renderer.py`.

Removed the old inline `_HTML_TEMPLATE` fallback from `renderer.py`, so
`report_template.html` is now the single HTML source of truth.

### Full Reference Chains

Expanded output support for full leaf reference chains.

Outputs now show the full path from top referencing shape to the leaf owning
shape, for example:

```text
ex:ProjectLeadShape -> ex:EmploymentShape -> ex:PersonShape  -> datatype ex:age
```

This applies to:

- Text tree output
- JSON output
- HTML output
- CSV export
- Summary output

Alternate diamond paths are preserved and displayed, for example:

```text
also via ex:ProjectLeadShape -> ex:SecurityClearanceShape -> ex:PersonShape
```

### Text Tree Output

Changed text output to a Linux-tree-style layout.

Example:

```text
Focus node: ex:badCourse/
├── ❌ minCount    ex:title = (missing)
│   ├── message: A course must have a title
│   └── → fix: Add at least one ex:title value to ex:badCourse.
└── ❌ pattern     ex:courseCode = "abc123"
    ├── message: Course code must look like CS-101
    └── → fix: Change "abc123" on ex:courseCode so it matches the required pattern.
```

Added optional terminal colors:

```bash
--color auto
--color always
--color never
```

### Apache Jena Report Compatibility

Added support for Jena-style reports where `sh:detail` is absent and the report
uses `sh:sourceShape` plus `sh:resultPath`.

Test case:

```text
all_test_cases/sh_node_cases/jena_report_tc7_node_source_no_detail.ttl
```

The fallback revalidates the referenced value node and reconstructs the concrete
leaf failures.

### Large LUBM Experiment

Regenerated the large LUBM HTML report using the latest template.

Output:

```text
html_outputs/lubm_report.html
```

Observed timing from latest regeneration:

```text
parse data: 19.378s
parse shapes: 0.002s
validate: 0.798s
build explanation tree: 0.089s
render: 0.022s
```

### Current Verification

Latest full test suite result:

```text
33 tests OK
```

## Template For Future Entries

### YYYY-MM-DD: Short Feature Name

Summary:

- What changed.
- Why it matters.
- Which files were added or modified.
- How it was tested.

Commands:

```bash
python3 -m unittest discover -s tests -v
```
