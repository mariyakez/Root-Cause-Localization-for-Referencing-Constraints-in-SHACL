# Chapter 1: Introduction

## 1.1 Motivation

The Resource Description Framework (RDF) is a foundational standard for representing knowledge on the Semantic Web. As RDF datasets grow in size and complexity, ensuring data quality becomes a critical concern. The Shapes Constraint Language (SHACL), a W3C recommendation since 2017, addresses this need by allowing data engineers to define shapes — sets of constraints that RDF nodes must satisfy — and to validate datasets against those shapes automatically.

SHACL validation engines such as pySHACL, Apache Jena SHACL, and TopBraid produce standardized validation reports that list every constraint violation found in a dataset. For simple, direct constraint violations — for instance, a missing property value or an incorrect datatype — these reports are immediately actionable. They identify the focus node, the property path, the offending value, and the constraint that was violated.

However, SHACL also supports *referencing constraints*, most notably `sh:node`, which allow one shape to delegate part of its validation to another shape. When a focus node fails a referencing constraint, the validation report records a single `sh:NodeConstraintComponent` result. This result states that the focus node "does not conform to" the referenced shape, but it does not explain *why*. The concrete property-level failures that occurred inside the referenced shape — the actual root causes — are hidden behind an opaque summary. The following diagram illustrates this information gap:

```
Standard SHACL report:              What the user actually needs:

[Violation]                          [Violation]
  focusNode: ex:alice                  focusNode: ex:alice
  component: NodeConstraint            sourceShape: :EmployeeShape
  sourceShape: :EmployeeShape          via sh:node -> :PersonShape
  value: ex:alice                        path: ex:age
  (nothing else)                         value: "twenty"
                                         component: DatatypeConstraint
                                         fix: ex:age must be xsd:integer
```

This problem intensifies when referencing constraints are nested. A shape may reference a second shape, which in turn references a third, forming multi-level reference chains. In such cases, the root cause may be buried several levels deep, and the validation report provides no indication of which intermediate shapes were traversed or where the actual failure occurred. For data engineers working with large, schema-rich datasets — such as those modeled on the Lehigh University Benchmark (LUBM) — this means that a single opaque `sh:NodeConstraintComponent` result can hide dozens or even hundreds of concrete leaf failures, all reachable only through manual inspection of the shapes graph and the data.

The absence of root-cause explanations for referencing constraint failures represents a significant usability gap in current SHACL tooling. Users must either manually trace through shape definitions to understand what went wrong, or resort to trial-and-error modifications of their data — neither of which scales to real-world knowledge graphs.

## 1.2 Problem Definition

Given:
- A data graph *G* containing RDF triples,
- A shapes graph *S* defining SHACL shapes with potentially nested referencing constraints (e.g., `sh:node`),
- A SHACL validation report *R* produced by validating *G* against *S*,

the problem is to produce, for each `sh:NodeConstraintComponent` result in *R*, an **explanation tree** that:

1. **Localizes** the concrete, property-level constraint violations (leaf failures) that caused the referenced shape to fail,
2. **Traces** the full chain of referencing shapes from the top-level shape to the shape that owns the failing constraint,
3. **Identifies** the specific focus node or value node on which each leaf failure occurred,
4. **Handles** structural complexities including multi-level nesting, diamond-shaped references (where two reference paths converge on the same shape), and cyclic shape definitions,
5. **Suggests** concrete repair actions based on the type of each leaf constraint violation.

More formally, the output is a function:

```
explain(G, S, R) -> { ExplanationTree_1, ..., ExplanationTree_n }
```

where each `ExplanationTree_i` is a rooted tree whose:
- **Root** is a violated focus node,
- **Internal nodes** are referenced shapes reached through `sh:node` constraints, annotated with the property path that triggered the reference,
- **Leaves** are concrete constraint violations (e.g., `sh:minCount`, `sh:datatype`, `sh:pattern`) with their property path, offending value, and a repair hint.

## 1.3 Research Questions

This thesis addresses the following research questions:

**RQ1: How can root-cause constraint violations be automatically localized from opaque `sh:NodeConstraintComponent` results in SHACL validation reports?**

Standard SHACL reports do not expose the concrete failures hidden behind referencing constraints. This question investigates algorithms and strategies for expanding these opaque results into actionable leaf-level explanations.

**RQ2: How can the explanation handle structural complexities such as multi-level nesting, diamond references, and cyclic shape definitions?**

Real-world shapes graphs are not always simple trees. Reference chains can be arbitrarily deep, multiple paths can converge on the same shape (diamonds), and shapes may even reference themselves (cycles). This question examines how an explanation engine can handle these cases correctly — producing complete explanations without duplication or infinite recursion.

**RQ3: How can the approach be made compatible with validation reports from different SHACL engines that vary in the level of detail they provide?**

Different SHACL engines (pySHACL, Apache Jena, TopBraid) produce structurally different reports. Some include `sh:detail` sub-results; others provide only top-level results with minimal metadata. This question investigates how a single explanation tool can accommodate these variations through fallback re-validation strategies.

**RQ4: How does the approach scale to large, real-world RDF datasets?**

Explanation generation must remain practical for datasets with hundreds of thousands of triples and thousands of validation failures. This question evaluates the tool's performance on datasets of increasing size.

## 1.4 Overview of Our Approach

We present a tool that takes as input a data graph, a shapes graph, and optionally an external validation report, and produces an explanation tree for every referencing constraint failure. The tool is implemented as a Python command-line application built on top of pySHACL and rdflib, with a modular pipeline consisting of five stages:

1. **Parsing.** The validation report is parsed to extract top-level `sh:ValidationResult` entries, identifying which are direct (already actionable) and which are `sh:NodeConstraintComponent` results requiring expansion.

2. **Expansion.** Each `sh:NodeConstraintComponent` result is recursively expanded by re-validating the focus node (or value node) against the referenced shape. If the re-validation produces further `sh:NodeConstraintComponent` results, the process recurses until only concrete leaf failures remain. A visited-set guards against infinite recursion in cyclic shape definitions.

3. **Fallback re-validation.** When the input is an external report (e.g., from Apache Jena) that lacks `sh:detail` sub-results, the tool reconstructs the missing information by re-validating the relevant node against the referenced shape using pySHACL, then integrating the results into the explanation tree.

4. **Deduplication.** Diamond-shaped references — where two paths through the shapes graph converge on the same shape — can produce duplicate leaf failures. The deduplicator identifies structurally identical leaves reached through different reference chains and merges them, preserving all alternate paths as metadata.

5. **Rendering.** The deduplicated explanation tree is rendered in multiple output formats: a Linux-tree-style text output with optional color, structured JSON, CSV, a statistical summary with root-cause breakdown, and an interactive HTML report with filtering, searching, and an expandable graph view.

The tool covers all SHACL Core constraint types, supports nested `sh:node` references of arbitrary depth, and has been validated against 53 test cases spanning direct constraints, nested references, diamonds, cycles, multiple focus nodes, property paths, severities, and external report formats. It has been evaluated on a LUBM-style dataset of approximately 163 MB, producing explanations for 891 focus nodes with 992 leaf failures.

## 1.5 Structure of the Thesis

The remainder of this thesis is organized as follows:

**Chapter 2: Preliminaries** introduces the technical foundations: RDF, the SHACL specification (shapes, constraints, validation reports, referencing constraints), and the SHACL validation report vocabulary. It also covers the specific SHACL engines relevant to this work.

**Chapter 3: Related Work** surveys existing SHACL validation tools and their explanation capabilities, as well as related work on constraint explanation and debugging in adjacent domains. It positions our contribution relative to the state of the art.

**Chapter 4: Our Approach** describes the explanation pipeline in detail — the parsing, expansion, fallback, deduplication, and rendering stages — including the data model, algorithms, and design decisions for handling structural complexities.

**Chapter 5: Experiments** presents the experimental evaluation: the test case taxonomy (53 cases across 10 categories), the LUBM-scale experiment, performance measurements, and a discussion of correctness and completeness.

**Chapter 6: Conclusions and Future Work** summarizes the contributions, reflects on lessons learned, and identifies open questions including support for logical constraint families (`sh:and`, `sh:or`, `sh:not`), `sh:qualifiedValueShape`, SHACL-SPARQL constraints, and advanced property paths.
