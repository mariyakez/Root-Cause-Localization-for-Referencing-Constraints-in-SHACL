# Root Cause Localization for Referencing Constraints in SHACL

Reference implementation accompanying the bachelor's thesis
**Root-Cause Localization for SHACL Referencing-Constraint Failures**.

|  |  |
|---|---|
| **Author** | Mariya Kezdekbayeva |
| **Supervisor** | Jin Ke, M.Sc. |
| **Examiner** | Prof. Maribel Acosta |
| **Degree** | Bachelor of Science (B.Sc.) Information Engineering |
| **Institution** | Technical University of Munich — TUM School of Computation, Information and Technology, Professorship of Data Engineering |
| **Submitted** | 24 September 2026 |
| **Thesis** | [thesis.pdf](thesis.pdf) |

This repository holds the tool, its test corpus, and the generated artifacts
behind the evaluation chapter, so every result reported in the thesis can be
reproduced or inspected directly.

## What it does

Standard SHACL validation reports can tell a user that a referenced shape failed, but they do not always make it easy to see the concrete property-level failures inside that referenced shape. This tool turns those reports into an explanation tree that shows:

- which exact SHACL Core constraint failed,
- on which `sh:path`,
- on which value node, when available,
- through which chain of referenced shapes the failure was reached,
- and what concrete repairs are needed.

## Contents

**Getting started** — [Quick Start](#quick-start) · [Scope](#scope) · [Installation](#installation) · [Repository Layout](#repository-layout)

**Using the tool** — [Basic Usage](#basic-usage) · [Reading the Tree](#reading-the-explanation-tree) · [Output Modes](#output-modes) · [HTML Report](#html-report) · [Input Formats](#input-formats) · [Filters](#filters) · [CLI Reference](#cli-reference)

**How it works** — [Pipeline](#pipeline) · [External Report Compatibility](#external-report-compatibility-apache-jena-topbraid)

**Evaluation** — [Test Cases](#test-cases) · [Running Tests](#running-tests) · [Large Dataset Evaluation](#large-dataset-evaluation) · [Generated Artifacts](#generated-artifacts)

## Quick Start

Clone the repository, install the two dependencies, and explain a failure in
under a minute. Requires **Python 3.10 or newer** (the code uses `X | None`
type syntax).

```bash
git clone https://github.com/mariyakez/Root-Cause-Localization-for-Referencing-Constraints-in-SHACL.git
cd Root-Cause-Localization-for-Referencing-Constraints-in-SHACL

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**1. Explain one failure.** The fixtures carry data and shapes in the same
Turtle file, so the file is passed twice:

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

pySHACL alone reports only that `ex:CompanyShape` was violated. The `minCount`
line, the value node `ex:acme`, and the repair are what this tool recovers.

**2. Render the same explanation as an interactive HTML report.** A bare
filename is placed in `html_outputs/` automatically:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl \
  all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl \
  --format html --output tc53_quickstart.html
open html_outputs/tc53_quickstart.html   # Linux: xdg-open
```

**3. Verify the installation.**

```bash
python3 -m unittest discover -s tests
```

```text
Ran 52 tests
OK
```

**Nothing to install?** Every report is pre-generated and committed. Open any
file in [`html_outputs/`](html_outputs/) directly in a browser, for example
[`html_outputs/tc53_deep_gradient_graph.html`](html_outputs/tc53_deep_gradient_graph.html)
for the deepest reference chain, or
[`html_outputs/lubm_skg1_schema1_report.html`](html_outputs/lubm_skg1_schema1_report.html)
for a real-scale run.

## Scope

The current implementation focuses on:

- SHACL Core constraints,
- `sh:node` referencing constraints,
- nested referencing chains,
- property-level `sh:node`,
- multiple referenced-shape failures on the same focus node,
- diamond-shaped references,
- reports with or without `sh:detail`,
- external SHACL reports, including real reports from Apache Jena and TopBraid.

Out of scope for now:

- SHACL SPARQL constraints,
- full support for logical constraint families such as `sh:and`, `sh:or`, `sh:not`, `sh:xone`,
- full support for `sh:qualifiedValueShape`,
- advanced SHACL property paths beyond what the current report/fallback logic can reconstruct.

## Installation

The three commands are in [Quick Start](#quick-start) above; this section
records what they install and why.

Two runtime dependencies are pinned in [`requirements.txt`](requirements.txt):

| Package | Version | Used for |
|---|---|---|
| `pyshacl` | 0.31.0 | Producing the validation report, and re-validating referenced shapes in `fallback.py` |
| `rdflib` | 7.6.0 | Parsing the data, shapes, and report graphs |

`tools/check_report_template.py` additionally runs the HTML report's own
JavaScript under `node`; it is skipped when Node.js is not installed. Nothing
else is required.

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

Most fixtures in this repository carry data and shapes in one Turtle file, so
the same path is passed twice, as in [Quick Start](#quick-start).

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

## Reading the Explanation Tree

Every tree is rooted at a focus node. Each `sh:node` hop becomes its own level,
the `❌` line names the failing SHACL Core component and the leaf path, the
`via` line spells out the full chain of referenced shapes that reached it, and
`--hints` adds a `→ fix:` line.

The [Quick Start](#quick-start) example shows one hop. Reference chains nest to
any depth; here are two levels:

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

`ex:carol` was validated against `ex:ContractorShape`, which references
`ex:EmployeeShape`, which inherits the failing constraint from
`ex:PersonShape` — and the actual defect is a non-integer `ex:age`. pySHACL
reports only that `ex:ContractorShape` was violated; the two intermediate hops,
the terminal `datatype` failure, and the offending literal are what this tool
recovers. `all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl` carries
the same structure eight levels deep.

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

Repair hints (text mode only; JSON, CSV, and HTML always carry them):

```bash
python3 -m shacl_explainer.cli DATA.ttl SHAPES.ttl --hints
```

A hint is produced for `minCount`, `maxCount`, `datatype`, `class`, `pattern`,
and `in`, and names what the shape requires:

```text
→ fix: Replace "three" on ex:credits with a value of type xsd:integer.
→ fix: Add 2 more ex:reviewer values to ex:project1 (has 1, needs at least 3).
→ fix: Make ex:charlie, the ex:student value of ex:enrollment1, an instance of ex:Student, or replace it with one.
```

Two details decide what a hint may say. The node it names is the one the
constraint was checked on, so for a constraint on a property shape that is the
value reached along the path rather than the focus node holding it. The
requirement itself is read from the shape that produced the result; where an
external report identifies that shape only as an anonymous blank node, it is
read from the reported path instead, and only where every property shape on
that path agrees, so a hint never guesses a requirement. Otherwise it falls
back to wording that states no parameter, such as "a value of the required
datatype". The count of existing values is read from the data graph for a
minimum above one and nowhere else, since it costs one path evaluation per
leaf.

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

`--format html` renders the report as a single HTML file: the explanation tree is
embedded as JSON in the page and all styling and interaction is inlined, with no build
step and no runtime library, so the report can be opened directly from disk or handed
over as a standalone artifact.

The one exception to self-containment is typography. The document head contains two
`preconnect` links and one stylesheet link to `fonts.googleapis.com` /
`fonts.gstatic.com`, loading Inter, Geist Mono, and JetBrains Mono. Nothing else is
fetched over the network, and every feature of the report works offline; without those
requests, typography falls back to the local font stacks declared alongside each web
font.

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

## External Report Compatibility (Apache Jena, TopBraid)

The tool can explain an existing SHACL validation report instead of running
pySHACL directly, for example one produced by Apache Jena or TopBraid SHACL.

Turtle report:

```bash
python3 -m shacl_explainer.cli data.ttl shapes.ttl \
  --report report.ttl \
  --report-format turtle
```

RDF/XML report:

```bash
python3 -m shacl_explainer.cli data.ttl shapes.ttl \
  --report report.rdf \
  --report-format xml
```

Real Apache Jena report (TopBraid's, `topbraid_real_tc7_property_no_detail.ttl`,
has the same structure):

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  all_test_cases/sh_node_cases/tc7_property_node.ttl \
  --report all_test_cases/sh_node_cases/jena_real_tc7_property_no_detail.ttl \
  --hints
```

Neither validator writes `sh:detail`, so the nested failures are reconstructed.
The referenced shape of an `sh:node` result is found from `sh:sourceShape` in
one of three ways:

- the source shape itself declares `sh:node` (a node-level result, or a named
  property shape);
- the source shape is a node shape whose property shape on `sh:resultPath`
  declares `sh:node` (a structure only the synthetic fixtures use);
- the source shape matches nothing in the shapes graph, which is what Jena and
  TopBraid report for a property-level result when the property shape is
  anonymous. The property shapes declaring `sh:node` on the reported path are
  then used, narrowed, if several match, by whether their node shape targets the
  focus node, by whether the value actually fails the referenced shape, and by
  the result's declared `sh:severity`/`sh:message` or, failing those, by pairing
  results with candidates one to one.

Verified against Apache Jena SHACL 6.2.0 and TopBraid SHACL 1.5.0 in Turtle: on
all 48 fixtures that are not themselves hand-written reports, both validators'
reports reconstruct to the same leaf failures as pySHACL's own explanation.
Reference chains differ only on TC46 from Jena, whose report has no `sh:node`
result for the self-reference. With `sh:detail` removed from pySHACL's own
report, the rebuilt explanation of every fixture is byte-identical to the one
read from `sh:detail`. RDF/XML parsing is supported but was not tested with a
real validator's output.

Rebuilding costs one pySHACL re-validation per `sh:node` result, about 0.6-0.9 ms
each. Results are shared within a build by (target node, referenced shape), which
cut the re-validations by 1.7x to 21.3x on the LUBM reports and keeps rebuilding at
1.5 to 3.0 times the cost of reading `sh:detail`. On those reports the
rebuilt explanation is byte-identical to the one read from `sh:detail`.

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
| `all_test_cases/external_report_cases/` | pySHACL, Jena-style, synthetic property-level, and incomplete external reports |
| `all_test_cases/cycle_cases/` | Recursive and cyclic shape references |
| `all_test_cases/scale_cases/` | Synthetic scale and performance-oriented cases |
| `all_test_cases/repair_hint_cases/` | Named, non-numbered cases for the repair-hint wording the TC corpus does not reach |

### Numbered Test Case Inventory

<details>
<summary>All 53 numbered fixtures, TC1&ndash;TC53 (click to expand)</summary>

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
| TC38 | `all_test_cases/message_metadata_cases/tc38_multiple_messages.ttl` | Multiple messages on one constraint, all shown |
| TC39 | `all_test_cases/message_metadata_cases/tc39_language_tagged_message.ttl` | Language-tagged messages |
| TC40 | `all_test_cases/message_metadata_cases/tc40_named_vs_blank_property_shapes.ttl` | Named and blank property shapes |
| TC41 | `all_test_cases/external_report_cases/tc41_pyshacl_report_with_detail.ttl` | pySHACL-style external report with `sh:detail` |
| TC42 | `all_test_cases/external_report_cases/tc42_jena_report_no_detail.ttl` | Jena-style external report without `sh:detail` |
| TC43 | `all_test_cases/external_report_cases/tc43_enclosing_shape_property_report.ttl` | Synthetic property-level `sh:node` report naming the enclosing node shape |
| TC44 | `all_test_cases/external_report_cases/tc44_referenced_shape_property_report.ttl` | Synthetic property-level `sh:node` report naming the referenced shape |
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

</details>

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

Expected result:

```text
Ran 52 tests
OK
```

| Test module | Tests | Covers |
|---|---:|---|
| `tests/test_cli_pipeline.py` | 40 | End-to-end CLI runs across the test-case corpus, output modes, filters, real Jena/TopBraid reports, and run-to-run determinism |
| `tests/test_fallback.py` | 8 | Re-validation when an external report has no `sh:detail`: byte-identical to `sh:detail` on every fixture, a referenced shape with its own target, the re-validation cache, and matching a result to its property shape by declared metadata |
| `tests/test_expected_json.py` | 2 | Complete JSON explanation of 25 fixtures against stored documents; every declared message shown |
| `tests/test_deduplicator.py` | 1 | Diamond-reference deduplication with alternate chains preserved |
| `tests/test_report_template.py` | 1 | Wraps `tools/check_report_template.py`, so the HTML summary-panel invariants are checked by the suite; skipped when `node` is absent |

The stored JSON documents behind `test_expected_json.py` live in
[`tests/expected_json/`](tests/expected_json/) and are regenerated with
`python3 tools/regenerate_expected_json.py`.

None of these execute the JavaScript of the HTML report, so two properties of its
summary panel are checked separately, by running the template's own functions
under `node`:

```bash
python3 tools/check_report_template.py [fixture.ttl]
```

It asserts that "How reached" in the root-cause breakdown reads `direct` exactly
when the leaf has no reference chain, and that a filter which hides leaves also
moves the headline counters and the breakdown. Both were once wrong: a route made
only of node-level `sh:node` references reported `direct` while the headline
counted it under `sh:node`, and the counters were computed once at startup from
the whole report. The check is skipped when `node` is not installed.

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

`lubm_schemas/corrected/` holds copies of schema2 and schema3 with the defects
reported by `tools/audit_shacl_schema.py` repaired (a constraint on the
non-existent `ub:type`, `sh:node` values naming classes rather than shapes, and
a misspelled `sh:manCount`). Both variants are evaluated; see
`lubm_evaluation_results.md`.

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
| skg1 x schema1 | 19.2 | 0.8 | 0.1 | 0.05 |
| skg1 x schema2 | 19.3 | 62.0 | 10.2 | 0.34 |
| skg1 x schema3 | 19.2 | 92.3 | 17.8 | 0.65 |
| mkg1 x schema1 | 84.2 | 3.2 | 0.3 | 0.07 |
| mkg1 x schema2 | 83.9 | 302.8 | 50.1 | 1.31 |
| mkg1 x schema3 | 83.2 | 471.0 | 85.5 | 2.78 |

Explanation output summary:

| Dataset x Schema | Focus nodes affected | Leaf failures (via sh:node / direct) |
|---|---:|---|
| skg1 x schema1 | 870 | 992 (655 / 337) |
| skg1 x schema2 | 6,306 | 10,099 (8,781 / 1,318) |
| skg1 x schema3 | 16,207 | 21,170 (17,043 / 4,127) |
| mkg1 x schema1 | 839 | 968 (958 / 10) |
| mkg1 x schema2 | 25,032 | 39,736 (35,597 / 4,139) |
| mkg1 x schema3 | 67,941 | 87,396 (69,729 / 17,667) |

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
| [`tools/audit_shacl_schema.py`](tools/audit_shacl_schema.py) | Checks a schema against the data it validates: paths absent from the data, `sh:node` values that are not shapes, result-vocabulary terms used as constraints |
| [`tools/measure_reconstruction.py`](tools/measure_reconstruction.py) | Builds one combination's explanation three ways — from `sh:detail`, rebuilt with the re-validation cache, and rebuilt with one call per `sh:node` result — checks all three agree, and reports timings, call counts and peak memory. Produces the reconstruction table in [`lubm_evaluation_results.md`](lubm_evaluation_results.md) |
| [`tools/compare_external_validators.py`](tools/compare_external_validators.py) | Runs Apache Jena and TopBraid over every fixture, feeds each report back through `--report`, and diffs the reconstruction against pySHACL's own explanation at three levels: leaf failures, reference chains and repair hints. This is the check behind RQ2 |
| [`tools/check_report_template.py`](tools/check_report_template.py) | Runs the shipped HTML report's own JavaScript under `node` to check the summary-panel invariants. Also wrapped by `tests/test_report_template.py` |

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

## Repository Layout

```text
.
├── shacl_explainer/          the tool
│   ├── cli.py                argument parsing, validation, orchestration
│   ├── parser.py             top-level results out of a report graph
│   ├── expander.py           walks sh:detail / sh:node into an explanation tree
│   ├── fallback.py           rebuilds nested results when sh:detail is absent
│   ├── deduplicator.py       collapses diamond references, keeps alternate chains
│   ├── tree.py               ReferenceNode / LeafFailure data model
│   ├── renderer.py           text, JSON, HTML, CSV, summary, repair hints
│   └── report_template.html  self-contained HTML report template
├── tests/                    unittest suite (52 tests) and stored JSON expectations
├── all_test_cases/           TC1–TC53 fixtures plus named repair-hint cases
├── html_outputs/             pre-generated HTML reports (53 test cases + 6 LUBM runs)
├── output_mode_examples/     reference samples of the JSON, summary, and CSV modes
├── lubm_schemas/             the three LUBM shape schemas, plus corrected variants
├── tools/                    evaluation and maintenance scripts (see Generated Artifacts)
├── lubm_evaluation_results.md  full per-combination LUBM breakdown
├── requirements.txt          pyshacl 0.31.0, rdflib 7.6.0
└── thesis.pdf                the submitted thesis (103 pages)
```

| Path | What it is | Start here if you want to |
|---|---|---|
| [`shacl_explainer/`](shacl_explainer/) | The tool itself, ~2,000 lines across eight modules | Read the implementation; the pipeline order is in [Pipeline](#pipeline) |
| [`tests/`](tests/) | 52 unittest tests | Verify the tool end to end |
| [`all_test_cases/`](all_test_cases/) | Every fixture, grouped by scenario | Reproduce a specific behaviour from the thesis |
| [`html_outputs/`](html_outputs/) | 59 committed reports | See real output without installing anything |
| [`lubm_schemas/`](lubm_schemas/) | The evaluation schemas | Re-run the large-dataset evaluation |
| [`tools/`](tools/) | Five scripts behind the evaluation chapter | Regenerate a result reported in the thesis |
| [`thesis.pdf`](thesis.pdf) | The full thesis, 103 pages | Read the method, the evaluation and the results in full |

The two LUBM data graphs (171 MB and 732 MB) are **not** committed; see
[Large Dataset Evaluation](#large-dataset-evaluation).

GitHub repository:

```text
https://github.com/mariyakez/Root-Cause-Localization-for-Referencing-Constraints-in-SHACL.git
```
