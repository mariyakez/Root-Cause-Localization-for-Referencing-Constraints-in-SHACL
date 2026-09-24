# LUBM Evaluation Results

Full results from running the SHACL explainer against two LUBM-generated data graphs,
each checked against three progressively larger SHACL shape schemas. Regenerated on
2026-09-20 using:

```bash
python3 -m shacl_explainer.cli <data> <shapes> --format html --hints --timing --output html_outputs/lubm_<dataset>_<schema>_report.html
python3 -m shacl_explainer.cli <data> <shapes> --summary --timing
```

## Setup

| | Size | Data triples |
|---|---|---|
| `lubm_skg_1.ttl` | 171.0 MB | 1,001,716 |
| `lubm_mkg_1.ttl` | 732.0 MB | 4,258,329 |

| Schema | Shape triples |
|---|---|
| `schema1.ttl` | 54 |
| `schema2.ttl` | 110 |
| `schema3.ttl` | 341 |

Both data files were parsed directly from Turtle (no pre-parsed `.pkl`), so parse
timings reflect real Turtle-parsing cost.

## Timing summary

All times in seconds, from the pipeline's own `--timing` output (not counting Python
process startup). From the HTML run of each combination.

| Dataset x Schema | Parse data | Validate | Build tree | Render | Pipeline total |
|---|---:|---:|---:|---:|---:|
| skg1 x schema1 | 19.188 | 0.829 | 0.095 | 0.045 | 20.16 |
| skg1 x schema2 | 19.267 | 62.041 | 10.194 | 0.338 | 91.84 |
| skg1 x schema3 | 19.158 | 92.290 | 17.751 | 0.645 | 129.84 |
| mkg1 x schema1 | 84.199 | 3.225 | 0.291 | 0.068 | 87.78 |
| mkg1 x schema2 | 83.941 | 302.849 | 50.090 | 1.309 | 438.19 |
| mkg1 x schema3 | 83.167 | 471.000 | 85.502 | 2.783 | 642.45 |

**Key observation:** parse time depends only on data size (~19s for skg1, ~83-84s for
mkg1) and is essentially constant across schemas for the same dataset. Validate and
build-tree time, by contrast, depend mostly on schema reach, observed through
validation-result volume, not data size alone: schema2/schema3 add
`ub:takesCourse` constraints (via `ub:CourseShape` / `ub:GraduateCourseShape`)
that apply to a much larger population than the degree-granting-university
constraints in schema1, causing pyshacl's result count (and therefore validate +
tree-build time) to grow by two orders of magnitude between schema1 and schema3
on the same data.

Build-tree time is higher across the board than in the previous (2026-08-25/26)
measurement, most visibly on skg1/schema2 (9.378s -> 10.194s) and mkg1/schema3
(75.837s -> 85.502s). This tracks the repair-hint work added since then
(constraint parameter lookup per leaf), not a regression: content is unaffected,
see the explanation-output table below.

Wall-clock times for the full CLI invocation (including process startup, matches
closely but not exactly the pipeline total above). Each figure below is from an
isolated run with nothing else active on the machine; earlier attempts at the four
largest combinations showed wall-clock inflation of 260-670s from concurrent disk
activity (Spotlight re-indexing the freshly regenerated `html_outputs/`) and were
discarded.

| Dataset x Schema | HTML run total | HTML run wall | Summary run total | Summary run wall |
|---|---:|---:|---:|---:|
| skg1 x schema1 | 20.16 | 21 | 20.03 | 21 |
| skg1 x schema2 | 91.84 | 96 | 91.00 | 95 |
| skg1 x schema3 | 129.84 | 135 | 129.20 | 134 |
| mkg1 x schema1 | 87.78 | 94 | 86.32 | 91 |
| mkg1 x schema2 | 438.19 | 464 | 416.26 | 443 |
| mkg1 x schema3 | 642.45 | 680 | 631.75 | 675 |

## Explanation output summary

Unchanged from the previous run: these are content counts, unaffected by machine
load or by the repair-hint timing change above.

| Dataset x Schema | Pyshacl results (top-level / all) | Focus nodes affected | Leaf failures (via sh:node / direct) |
|---|---|---:|---|
| skg1 x schema1 | 2,136 / 3,280 | 870 | 992 (655 / 337) |
| skg1 x schema2 | 189,776 / 369,453 | 6,306 | 10,099 (8,781 / 1,318) |
| skg1 x schema3 | 280,602 / 537,637 | 16,207 | 21,170 (17,043 / 4,127) |
| mkg1 x schema1 | 5,836 / 10,704 | 839 | 968 (958 / 10) |
| mkg1 x schema2 | 799,665 / 1,559,594 | 25,032 | 39,736 (35,597 / 4,139) |
| mkg1 x schema3 | 2,281,457 / 1,189,565 | 67,941 | 87,396 (69,729 / 17,667) |

## Per-combo detail

### skg1 x schema1
- Top failing paths: `ub:name` minCount - 992
- Top components: minCount - 992
- Top reference paths: `ub:doctoralDegreeFrom -> ub:UniversityShape` - 216, `ub:mastersDegreeFrom -> ub:UniversityShape` - 180, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 137
- Top full leaf reference chains: `ub:UniversityShape -> minCount ub:name` - 655

### skg1 x schema2
- Top failing paths: `ub:type` minCount - 8,126; `ub:name` minCount - 992; `ub:teacherOf` maxCount - 981
- Top components: minCount - 9,118; maxCount - 981
- Top reference paths: `ub:takesCourse -> ub:CourseShape` - 4,871, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 216, `ub:mastersDegreeFrom -> ub:UniversityShape` - 180, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 137
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 8,126; `ub:UniversityShape -> minCount ub:name` - 655

### skg1 x schema3
- Top failing paths: `ub:type` minCount - 16,134; `ub:teacherOf` maxCount - 4,044; `ub:name` minCount - 992
- Top components: minCount - 17,126; maxCount - 4,044
- Top reference paths: `ub:takesCourse -> ub:GraduateCourseShape` - 5,739, `ub:teachingAssistantOf -> ub:CourseShape` - 4,156, `ub:takesCourse -> ub:CourseShape` - 3,058, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 655, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 162, `ub:mastersDegreeFrom -> ub:UniversityShape` - 109
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 8,126; `ub:GraduateCourseShape -> minCount ub:type` - 7,925; `ub:UniversityShape -> minCount ub:name` - 992

### mkg1 x schema1
- Top failing paths: `ub:name` minCount - 968
- Top components: minCount - 968
- Top reference paths: `ub:doctoralDegreeFrom -> ub:UniversityShape` - 311, `ub:mastersDegreeFrom -> ub:UniversityShape` - 287, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 231
- Top full leaf reference chains: `ub:UniversityShape -> minCount ub:name` - 958

### mkg1 x schema2
- Top failing paths: `ub:type` minCount - 34,639; `ub:teacherOf` maxCount - 4,127; `ub:name` minCount - 968; `ub:publicationAuthor` maxCount - 2
- Top components: minCount - 35,607; maxCount - 4,129
- Top reference paths: `ub:takesCourse -> ub:CourseShape` - 20,707, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 311, `ub:mastersDegreeFrom -> ub:UniversityShape` - 287, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 231
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 34,639; `ub:UniversityShape -> minCount ub:name` - 958

### mkg1 x schema3
- Top failing paths: `ub:type` minCount - 69,117; `ub:teacherOf` maxCount - 17,309; `ub:name` minCount - 968; `ub:publicationAuthor` maxCount - 2
- Top components: minCount - 70,085; maxCount - 17,311
- Top reference paths: `ub:takesCourse -> ub:GraduateCourseShape` - 24,511, `ub:teachingAssistantOf -> ub:CourseShape` - 17,839, `ub:takesCourse -> ub:CourseShape` - 12,945, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 605, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 176, `ub:mastersDegreeFrom -> ub:UniversityShape` - 119
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 34,639; `ub:GraduateCourseShape -> minCount ub:type` - 34,122; `ub:UniversityShape -> minCount ub:name` - 968

Note: the "Top reference paths" counts are per traversed `sh:node` step (reference
nodes, before leaf-level deduplication), while the "Top full leaf reference chains"
counts are per distinct deduplicated leaf failure; the two do not sum to the same
total and neither is derived from the other.

## Generated HTML reports

| File | Size |
|---|---:|
| `html_outputs/lubm_skg1_schema1_report.html` | 664K |
| `html_outputs/lubm_skg1_schema2_report.html` | 6.1M |
| `html_outputs/lubm_skg1_schema3_report.html` | 14M |
| `html_outputs/lubm_mkg1_schema1_report.html` | 756K |
| `html_outputs/lubm_mkg1_schema2_report.html` | 24M |
| `html_outputs/lubm_mkg1_schema3_report.html` | 57M |

## Peak resident memory

Measured with `/usr/bin/time -l` around the HTML run of each combination (single
measurement, same machine as the timings above).

| Dataset x Schema | Peak RSS |
|---|---:|
| skg1 x schema1 | 1.59 GB |
| skg1 x schema2 | 4.96 GB |
| skg1 x schema3 | 6.26 GB |
| mkg1 x schema1 | 6.69 GB |
| mkg1 x schema2 | 11.02 GB |
| mkg1 x schema3 | 13.87 GB |

Reconstructing from a report with every `sh:detail` triple removed, measured the
same way on skg1 x schema2, peaks at 5.22 GB against 4.96 GB for the normal run,
about five percent more: the re-validation cache holds one small report per
distinct (target node, referenced shape) pair.

## Cost of reconstruction without sh:detail

Measured separately, in one process per combination: validate once, build the
explanation from `sh:detail` (`detail`), then delete every `sh:detail` triple and
build it again with re-validations shared by `RevalidationCache` (`shared`) and
with one pySHACL call per `sh:node` result (`unshared`). All three trees serialize
to byte-identical JSON on every combination. Figures are comparable with each
other, not with the timing summary above (see `tools/measure_reconstruction.py`).

| Dataset x Schema | sh:node results | detail | shared (calls) | unshared (calls) |
|---|---:|---:|---:|---:|
| skg1 x schema1 | 1,144 | 0.09 s | 0.52 s (655) | 0.84 s (1,144) |
| skg1 x schema2 | 179,677 | 12.99 s | 22.59 s (8,781) | 173.00 s (179,677) |
| skg1 x schema3 | 257,035 | 22.30 s | 37.55 s (17,043) | 248.38 s (257,035) |
| mkg1 x schema1 | 4,868 | 0.39 s | 1.17 s (958) | 4.57 s (4,868) |
| mkg1 x schema2 | 759,929 | 57.94 s | 88.66 s (35,597) | 642.48 s (759,929) |
| mkg1 x schema3 | 1,091,892 | 118.02 s | 215.93 s (69,729) | 931.05 s (1,091,892) |

Unshared per-result cost: 0.64-0.88 ms mean, 0.69-1.08 ms at the 95th percentile.
Sharing cuts calls by 1.7x to 21.3x and keeps the rebuilt explanation at 1.5x to
3.0x the cost of reading `sh:detail`, on the five combinations larger than
skg1/schema1. Peak RSS across the six runs: 1.59-13.96 GB.

## Schema audit and corrected variants

`tools/audit_shacl_schema.py` checks a schema against the data it validates and
reports constraints that fail or pass by construction. On the supplied schemas:

| Schema | Findings |
|---|---|
| `schema1.ttl` | none |
| `schema2.ttl` | `sh:path ub:type` (no such predicate in LUBM); `sh:value` (a result term, not a constraint); `sh:node ub:Course` (a class, not a shape) |
| `schema3.ttl` | the same three, on two course shapes and eight `sh:node` references, plus `sh:manCount` (a misspelling of `sh:maxCount`) on `ub:FullProfessorShape` and `ub:LecturerShape` |

`lubm_schemas/corrected/` holds copies with exactly those defects repaired: the
`ub:type` property shapes removed, the class-valued `sh:node` references pointed
at the shapes, and `sh:manCount` corrected. The `ub:name` requirement on
universities is deliberately kept: the universities that fail it are ones the
LUBM generator names without describing, which is a property of the data.

Summary runs, one per combination, supplied against corrected:

| Dataset x Schema | Top-level results | Leaf failures | Validation (s) | Build tree (s) |
|---|---|---|---|---|
| skg1 x schema2 | 189,776 -> 3,117 | 10,099 -> 1,973 | 62.0 -> 25.3 | 10.19 -> 0.12 |
| skg1 x schema3 | 280,602 -> 22,555 | 21,170 -> 5,036 | 92.3 -> 42.9 | 17.75 -> 1.18 |
| mkg1 x schema2 | 799,665 -> 9,965 | 39,736 -> 5,097 | 302.8 -> 106.1 | 50.09 -> 0.42 |
| mkg1 x schema3 | 1,189,565 -> 93,058 | 87,396 -> 18,279 | 471.0 -> 184.9 | 85.50 -> 4.97 |

The `ub:type` group disappears; `ub:teacherOf` maxCount becomes the largest
group (981/4,044 on skg1 under schema2/schema3, 4,127/17,309 on mkg1 — the
`maxCount` component totals above are two higher on mkg1 from two unrelated
`ub:publicationAuthor` failures), and the `ub:name` group is unchanged (992 on
skg1, 968 on mkg1). Failures reached through `sh:node` fall from 8,781 to 655
(skg1 x schema2) and from 69,729 to 968 (mkg1 x schema3), so most of the
referencing workload in the supplied schemas came from the defect.
