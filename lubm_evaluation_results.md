# LUBM Evaluation Results

Full results from running the SHACL explainer against two LUBM-generated data graphs,
each checked against three progressively larger SHACL shape schemas. Generated on
2026-08-25/26 using:

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
process startup).

| Dataset x Schema | Parse data | Validate | Build tree | Render | Pipeline total |
|---|---:|---:|---:|---:|---:|
| skg1 x schema1 | 18.944 | 0.816 | 0.088 | 0.011 | 19.86 |
| skg1 x schema2 | 19.144 | 61.762 | 9.852 | 0.120 | 90.88 |
| skg1 x schema3 | 19.024 | 91.901 | 16.153 | 0.257 | 127.34 |
| mkg1 x schema1 | 83.925 | 3.274 | 0.283 | 0.013 | 87.50 |
| mkg1 x schema2 | 83.228 | 308.074 | 49.680 | 0.473 | 441.46 |
| mkg1 x schema3 | 93.793 | 469.582 | 70.914 | 1.060 | 635.35 |

**Key observation:** parse time depends only on data size (~19s for skg1, ~84-94s for
mkg1) and is essentially constant across schemas for the same dataset. Validate and
build-tree time, by contrast, depend almost entirely on schema complexity, not data
size alone: schema2/schema3 add `ub:takesCourse` constraints (via `ub:CourseShape` /
`ub:GraduateCourseShape`) that apply to a much larger population than the
degree-granting-university constraints in schema1, causing pyshacl's result count
(and therefore validate + tree-build time) to grow by two orders of magnitude between
schema1 and schema3 on the same data.

Wall-clock times for the full CLI invocation (including process startup, matches
closely but not exactly the pipeline total above):

| Dataset x Schema | HTML run wall | Summary run wall |
|---|---:|---:|
| skg1 x schema1 | 21.4s | 21.2s |
| skg1 x schema2 | 94.9s | 94.4s |
| skg1 x schema3 | 132.0s | 131.9s |
| mkg1 x schema1 | 94.1s | 93.1s |
| mkg1 x schema2 | 467.1s | 467.6s |
| mkg1 x schema3 | 732.8s | 918.8s |

## Explanation output summary

| Dataset x Schema | Pyshacl results (top-level / all) | Focus nodes affected | Leaf failures (via sh:node / direct) |
|---|---|---:|---|
| skg1 x schema1 | 2,136 / 3,280 | 890 | 992 (655 / 337) |
| skg1 x schema2 | 189,776 / 369,453 | 6,281 | 10,099 (8,781 / 1,318) |
| skg1 x schema3 | 280,602 / 537,637 | 15,950 | 21,170 (17,043 / 4,127) |
| mkg1 x schema1 | 5,836 / 10,704 | 933 | 968 (958 / 10) |
| mkg1 x schema2 | 799,665 / 1,559,594 | 25,058 | 39,736 (35,597 / 4,139) |
| mkg1 x schema3 | 1,189,565 / 2,281,457 | 67,561 | 87,396 (69,729 / 17,667) |

## Per-combo detail

### skg1 x schema1
- Top failing paths: `ub:name` minCount - 992
- Top components: minCount - 992
- Top reference paths: `ub:doctoralDegreeFrom -> ub:UniversityShape` - 307, `ub:mastersDegreeFrom -> ub:UniversityShape` - 163, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 83
- Top full leaf reference chains: `ub:UniversityShape -> minCount ub:name` - 655

### skg1 x schema2
- Top failing paths: `ub:type` minCount - 8,126; `ub:name` minCount - 992; `ub:teacherOf` maxCount - 981
- Top components: minCount - 9,118; maxCount - 981
- Top reference paths: `ub:takesCourse -> ub:CourseShape` - 4,835, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 307, `ub:mastersDegreeFrom -> ub:UniversityShape` - 161, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 80
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 8,126; `ub:UniversityShape -> minCount ub:name` - 655

### skg1 x schema3
- Top failing paths: `ub:type` minCount - 16,134; `ub:teacherOf` maxCount - 4,044; `ub:name` minCount - 992
- Top components: minCount - 17,126; maxCount - 4,044
- Top reference paths: `ub:takesCourse -> ub:GraduateCourseShape` - 5,707, `ub:teachingAssistantOf -> ub:CourseShape` - 4,156, `ub:takesCourse -> ub:CourseShape` - 3,020, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 442, `ub:mastersDegreeFrom -> ub:UniversityShape` - 231, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 197
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 8,126; `ub:GraduateCourseShape -> minCount ub:type` - 7,925; `ub:UniversityShape -> minCount ub:name` - 992

### mkg1 x schema1
- Top failing paths: `ub:name` minCount - 968
- Top components: minCount - 968
- Top reference paths: `ub:doctoralDegreeFrom -> ub:UniversityShape` - 799, `ub:mastersDegreeFrom -> ub:UniversityShape` - 108, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 16
- Top full leaf reference chains: `ub:UniversityShape -> minCount ub:name` - 958

### mkg1 x schema2
- Top failing paths: `ub:type` minCount - 34,639; `ub:teacherOf` maxCount - 4,127; `ub:name` minCount - 968; `ub:publicationAuthor` maxCount - 2
- Top components: minCount - 35,607; maxCount - 4,129
- Top reference paths: `ub:takesCourse -> ub:CourseShape` - 20,693, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 799, `ub:mastersDegreeFrom -> ub:UniversityShape` - 111, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 15
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 34,639; `ub:UniversityShape -> minCount ub:name` - 958

### mkg1 x schema3
- Top failing paths: `ub:type` minCount - 69,117; `ub:teacherOf` maxCount - 17,309; `ub:name` minCount - 968; `ub:publicationAuthor` maxCount - 2
- Top components: minCount - 70,085; maxCount - 17,311
- Top reference paths: `ub:takesCourse -> ub:GraduateCourseShape` - 24,457, `ub:teachingAssistantOf -> ub:CourseShape` - 17,839, `ub:takesCourse -> ub:CourseShape` - 12,870, `ub:doctoralDegreeFrom -> ub:UniversityShape` - 882, `ub:mastersDegreeFrom -> ub:UniversityShape` - 63, `ub:undergraduateDegreeFrom -> ub:UniversityShape` - 7
- Top full leaf reference chains: `ub:CourseShape -> minCount ub:type` - 34,639; `ub:GraduateCourseShape -> minCount ub:type` - 34,122; `ub:UniversityShape -> minCount ub:name` - 968

## Generated HTML reports

| File | Size |
|---|---:|
| `html_outputs/lubm_skg1_schema1_report.html` | 664K |
| `html_outputs/lubm_skg1_schema2_report.html` | 6.1M |
| `html_outputs/lubm_skg1_schema3_report.html` | 14M |
| `html_outputs/lubm_mkg1_schema1_report.html` | 780K |
| `html_outputs/lubm_mkg1_schema2_report.html` | 24M |
| `html_outputs/lubm_mkg1_schema3_report.html` | 54M |

## Interpretation for thesis writing

- **Parsing scales with data size, not schema.** ~19s for skg1 (171MB) and ~84-94s for
  mkg1 (732MB), consistently across all three schemas on the same dataset.
- **Validation and tree-building scale with schema complexity, not just data size.**
  Going from schema1 to schema3 on the *same* data increases validate time by ~100x
  (skg1: 0.8s -> 92s; mkg1: 3.3s -> 470s), because schema2/schema3 add constraints
  (`ub:CourseShape`, `ub:GraduateCourseShape` via `ub:takesCourse` /
  `ub:teachingAssistantOf`) that apply to a much larger fraction of the population
  than the degree-granting-university constraints alone.
- **The explanation layer stays cheap relative to validation.** Even on the largest
  run (mkg1 x schema3, ~2.28M pyshacl results), building the explanation tree
  (70.9s) is an order of magnitude cheaper than the pySHACL validation it
  post-processes (469.6s) - the tool's own contribution is not the bottleneck.
  Rendering (HTML, summary, etc.) is negligible (<1.1s) even at this scale.
- **The core repair story replicates across scale.** In every combo, the dominant
  leaf failure remains missing `ub:name` (minCount) reached through
  `...DegreeFrom -> ub:UniversityShape`; schema2/schema3 add a second dominant story
  (missing `ub:type` reached through `ub:takesCourse`/`ub:teachingAssistantOf` into
  course shapes). This is consistent between the smaller skg1 and 4x larger mkg1
  dataset, suggesting the finding is a property of the schema/data pattern rather
  than a scale artifact.
