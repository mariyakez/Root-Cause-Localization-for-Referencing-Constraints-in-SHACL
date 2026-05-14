# SHACL Explainer Progress Log

This file tracks implemented changes and thesis-relevant progress. Add a new
entry whenever a feature, test case, output format, or compatibility improvement
is added.

## 2026-05-14

### Adaptive HTML Filter Noise Reduction

Reduced visual noise in the HTML filter bar for reports where some facets have
only a single meaningful value.

When the following filter groups have only one non-`all` option, they now
render as passive summary chips instead of full button groups:

- component
- leaf path
- shape

This keeps high-value controls such as reference path and kind filters
prominent, while still exposing useful context like:

- `component: minCount`
- `path: ub:name`
- `shape: ub:UniversityShape`

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Summary Visual Hierarchy

Improved the visual hierarchy of the HTML summary panel with restrained,
semantic color coding.

Changes:

- `focus nodes` metric uses a cyan-tinted card
- `leaf failures` metric uses a red-tinted card
- `direct` metric uses a warm yellow-tinted card
- `via sh:node` metric uses a blue-tinted card
- the root-cause breakdown section now has a slightly stronger framed surface so
  it stands out as a key explanatory block

This makes the summary easier to scan in demos and thesis review without making
the page look overly decorative.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Report Actions Bar

Moved the HTML export actions out of the filter bar and into a separate
report-level actions row above the summary panel.

This separates:

- report actions: export/copy
- overview: summary panel
- exploration controls: sticky filter bar

The result is less visual crowding in the filter bar and a clearer distinction
between report-wide actions and detail-exploration controls.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Summary Panel Placement

Moved the HTML summary panel above the filter bar.

This makes the report read more naturally:

1. overview of the validation result
2. filters and controls for exploring the details

The sticky filter bar still remains available during long scrolling, but the
user now sees the high-level report context first.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Performance Precomputation

Optimized the HTML report for future larger validation outputs by moving several
filtering and sidebar count operations onto precomputed flat indexes.

The report now builds and reuses:

- a flat leaf-entry list for all failures
- a focus-node entry index
- an issue-cluster entry index

This means repeated UI actions such as:

- updating the visible failure count
- deciding which focus nodes remain visible
- deciding which issue clusters remain visible
- exporting the currently visible failures

no longer require recursive traversal of the whole explanation tree on every
interaction.

Tree rendering still uses the original grouped structure, but the frequent
counting and filtering paths now operate on cached leaf records.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass
- full test suite passes

### HTML Sidebar Accessibility

Improved accessibility for the HTML sidebar before thesis and demo use.

Changes:

- sidebar focus-node and issue-cluster entries are now real `button` elements
- sidebar mode switch now uses tab semantics:
  - `role="tablist"`
  - `role="tab"`
  - `aria-selected`
  - `aria-controls`
  - arrow-key, Home, and End navigation
- the search input now has an explicit `aria-label`
- focus styling was strengthened for keyboard users

This brings the sidebar closer to the same accessibility standard already used
for expandable reference and leaf headers.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Offline HTML Font Stack

Removed the external Google Fonts dependency from the HTML report template.

The report now uses only system font stacks:

- `--mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`
- `--sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

This keeps the generated HTML report fully self-contained and portable for
offline thesis sharing, local review, and archival use.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Export Actions

Added export actions directly to the HTML report so the interactive view also
works as an analysis artifact.

The filter bar now includes:

- `export visible CSV`
- `copy visible JSON`
- `copy root-cause summary`

The visible-failure exports follow the current HTML state:

- active filters
- selected focus node in `By focus` mode
- selected issue cluster in `By issue` mode

The root-cause summary export mirrors the report summary and copies the current
filtered breakdown as tab-delimited text.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass
- full test suite passes

### HTML Root-Cause Breakdown Table

Added a root-cause breakdown table to the HTML summary panel.

The table combines:

- repeated leaf symptom, such as `missing ub:name`
- how the failure was reached, such as `direct` or
  `via ub:doctoralDegreeFrom -> ub:UniversityShape`
- the count for that combination

This makes large reports much more thesis-friendly because repeated symptoms are
now paired with their path-based explanation instead of appearing only as flat
issue counts.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Issue View Causal Context

Improved the HTML `By issue` view so repeated leaf failures keep their causal
reference context visible.

Expanded leaf bodies in issue mode can now show:

- original focus node (`reached from`)
- reference path
- target/value node
- referenced shape

This makes repeated issue clusters such as `missing ub:name` much more useful,
because the user can immediately see whether the failure was reached through
paths such as `ub:doctoralDegreeFrom`, `ub:mastersDegreeFrom`, or
`ub:undergraduateDegreeFrom`.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML No-Script Fallback

Added a fallback for HTML reports before JavaScript renders.

The report now includes:

- a `noscript` block explaining that the interactive tree needs JavaScript
- static metadata in the no-script view
- a non-empty loading card inside `#report` so the body is not blank before the
  JavaScript renderer runs

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Keyboard Accessibility

Improved keyboard accessibility for expandable HTML report nodes.

Reference and leaf headers now include:

- `role="button"`
- `tabindex="0"`
- `aria-expanded`
- `aria-controls`
- Enter/Space keyboard toggling
- visible focus outline

Expansion controls keep `aria-expanded` synchronized when nodes are opened,
collapsed, expanded all, or collapsed all.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Focus Sidebar Preview Limit

Limited the HTML focus-node sidebar to the first 20 matching focus nodes by
default.

When more than 20 focus nodes match the current filters, the sidebar now shows a
toggle:

```text
show all N focus nodes
show first 20 focus nodes
```

Search still works across the matching focus-node set, and the currently
selected focus node remains visible even when it is outside the first 20.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Sticky HTML Filter Bar

Made the HTML filter bar sticky under the top report header.

This keeps component/path/reference/shape filters and view controls available
during long scrolling sessions in large reports.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Main Summary Panel

Added an orientation panel at the top of the HTML main area.

The panel appears above the selected focus/issue content and shows:

- total focus nodes
- total leaf failures
- direct failures
- failures reached through `sh:node`
- top issue clusters

Top issue clusters are clickable and switch the report into `By issue` mode for
that repeated failure pattern.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Clearer HTML Reference Depth Labels

Renamed the reference-depth pill in HTML reports.

Before:

```text
root
depth 1
```

Now:

```text
1st reference
2 levels deep
```

This makes nested `sh:node` chains easier to read without thesis-specific
terminology.

Updated:

- `shacl_explainer/report_template.html`

### HTML Copy Buttons

Added small copy controls to make repair workflows faster.

Copy buttons now appear on hover for:

- selected focus node IRI
- leaf focus node IRI
- leaf path
- repair hint text

The buttons use the browser clipboard API with a fallback copy method and are
kept visually subtle so they do not compete with the validation content.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Metadata Panel

Removed absolute local paths from the HTML report title.

Before, reports could expose paths such as:

```text
/Users/.../Desktop/lubm_skg_1.ttl
```

Now the browser title is generic and the report shows a metadata panel with
shareable information:

```text
Dataset: lubm_skg_1.ttl
Shapes: schema2.ttl
Generated: 2026-05-14 16:01
Commit: <short git commit>
```

Updated:

- `shacl_explainer/cli.py`
- `shacl_explainer/renderer.py`
- `shacl_explainer/report_template.html`
- `tests/test_cli_pipeline.py`

Test coverage:

- HTML output tests verify the generic title and filename metadata

### HTML Escaping Hardening

Hardened HTML report rendering by escaping additional data-derived values before
inserting them into `innerHTML`.

Updated escaping for:

- reference chains
- alternate reference chains
- component labels/classes used in generated markup

This makes generated reports more robust when RDF literals or IRIs contain
surprising characters.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Improved HTML IRI Labels

Improved IRI shortening in the HTML report.

Before, the sidebar used `split(":").pop()`, which worked for compact names
like `ex:alice` but produced poor labels for full HTTP IRIs.

Now the template uses a display helper:

```text
<http://www.Department13.University6.edu/FullProfessor1>
```

can be displayed as:

```text
FullProfessor1
```

with the full IRI preserved in the hover title.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Issue Clusters View

Added a second HTML navigation mode for issue clusters.

The sidebar now has two tabs:

- `By focus`: inspect one RDF focus node at a time
- `By issue`: inspect repeated failure patterns across the dataset

Issue clusters are generated from the leaf failures, for example:

```text
missing ub:type
missing ub:name
too many ub:teacherOf
```

Clicking an issue cluster renders the affected leaf failures in the main panel,
making it easier to identify large-scale root-cause patterns instead of
debugging only one RDF individual at a time.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Lazy HTML Focus Rendering

Changed the HTML report from eager full-DOM rendering to focus-node rendering.

Before, the browser created every focus block, reference branch, and leaf row at
page load. That was acceptable for small examples but heavy for large reports
with thousands of leaf failures.

Now:

- the sidebar still indexes all focus nodes
- filter chips are still computed from the full report data
- the main panel renders only the selected focus node
- clicking a sidebar focus node replaces the main panel content
- filtering updates sidebar visibility and selects the first focus node with
  matching failures when needed

This makes the generated HTML more practical for large LUBM-style reports
because the initial browser DOM is much smaller.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- Full suite passes with `33 tests OK`

### HTML Filtering Prunes Empty Branches

Improved HTML filtering for large reports.

Filtering now also hides:

- reference branches with no visible leaf failures
- focus blocks with no visible leaf failures
- sidebar focus-node entries whose focus block has no visible leaf failures

Added a visible count so the user can see the filter result size:

```text
Showing 981 of 10099 failures
```

Changed the default HTML report state to compressed:

- reference children start collapsed
- leaf bodies start collapsed
- `expand all` remains available
- added `collapse all`
- added `expand visible only`

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### Dynamic HTML Filter Chips

Replaced hard-coded HTML component filters with filter chips generated from the
actual report data.

The HTML report now builds chips for:

- component, such as `minCount` and `maxCount`
- leaf path, such as `ub:type`, `ub:name`, and `ub:teacherOf`
- reference path, such as `ub:takesCourse` and `ub:doctoralDegreeFrom`
- referenced shape, such as `ub:CourseShape` and `ub:UniversityShape`
- violation kind, direct or nested

Each chip includes the number of matching leaf failures and filters the visible
tree without requiring a new CLI run.

Updated:

- `shacl_explainer/report_template.html`

Test coverage:

- HTML output tests pass

### HTML Leaf Header Shows Broken RDF Node

Updated future HTML reports so each leaf failure header identifies the failing
focus/value node without requiring expansion.

Before, many rows could look identical in large reports:

```text
minCount ub:type (missing)
```

Now the header is self-contained:

```text
Course43 · missing ub:type
University384 · missing ub:name
FullProfessor1 · too many ub:teacherOf
```

Updated:

- `shacl_explainer/report_template.html`

Note:

- Existing HTML files were not regenerated for this change.

Test coverage:

- HTML output tests pass

### HTML Reference Header Shows Causal Path

Updated the HTML report reference-node header so the property path that caused a
`sh:node` reference is visible immediately.

Before, the header emphasized the source shape and referenced shape but hid the
causal bridge. Now it shows:

```text
reference path -> referenced shape · leaf failure count
```

Example:

```text
ub:doctoralDegreeFrom -> ub:UniversityShape · 2 leaf failures
```

Updated:

- `shacl_explainer/report_template.html`
- `html_outputs/jena_tc7_report.html`
- `html_outputs/lubm_skg1_schema2_report.html`

Test coverage:

- Full suite passes with `33 tests OK`

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
