# Chapter 3: Related Work

This chapter surveys existing work related to root-cause localization for SHACL validation failures. We organize the discussion into five areas: (1) SHACL validation tools and their reporting capabilities, (2) formal foundations and expressiveness of SHACL, (3) explanation and debugging of SHACL constraint violations, (4) repair-based approaches to SHACL non-conformance, and (5) validation and explanation in adjacent schema languages. For each area, we describe the relevant contributions and explain how they relate to — and differ from — the approach presented in this thesis.

## 3.1 SHACL Validation Tools

The primary SHACL validation engines relevant to this work are pySHACL, Apache Jena SHACL, and the TopBraid SHACL API. All three implement the SHACL Core specification [1] and produce standardized validation reports, but they differ significantly in the level of detail they expose for referencing constraint failures.

### 3.1.1 pySHACL

pySHACL [2] is an open-source Python implementation of the SHACL specification, built on the rdflib library. It supports the full SHACL Core constraint set and produces validation reports that include `sh:detail` sub-results for `sh:NodeConstraintComponent` violations. This means that when a `sh:node` reference fails, pySHACL's report contains nested `sh:ValidationResult` nodes that reveal the concrete failures inside the referenced shape.

This `sh:detail` support makes pySHACL the most informative engine for our purposes: the explanation tool can walk the detail tree directly to extract leaf-level failures without needing to re-validate. However, pySHACL's `sh:detail` output has important limitations for end-users:

- The detail tree is embedded in the RDF report graph, requiring programmatic traversal to interpret — it is not surfaced in a human-readable format.
- For multi-level `sh:node` chains, the user must recursively navigate `sh:detail` links to find the actual root cause, which is impractical for deep nesting.
- The report provides no reference chain context: a leaf failure deep inside a detail tree does not indicate which sequence of shapes led to it.
- Diamond-shaped references produce duplicate detail entries, and pySHACL does not deduplicate them.

Our tool uses pySHACL both as the primary validation engine and as the re-validation backend for external reports, but its contribution is in transforming pySHACL's raw detail output into structured, deduplicated explanation trees with full reference chains and repair hints.

### 3.1.2 Apache Jena SHACL

Apache Jena [3] is a Java-based RDF framework whose SHACL processor does not produce `sh:detail` sub-results. For a `sh:node` failure, Jena reports a single `sh:NodeConstraintComponent` result with `sh:sourceShape` pointing to the enclosing node shape, `sh:resultPath` identifying the property where the `sh:node` constraint appears, and `sh:value` containing the node that failed to conform. This information is sufficient to locate the referenced shape in the shapes graph, but it does not reveal why the referenced shape failed.

Our tool handles Jena-style reports through a fallback re-validation strategy: it reads the source shape and result path from the Jena report, finds the `sh:node` declaration on the matching property shape, and re-validates the value node against the referenced shape using pySHACL to reconstruct the missing detail.

### 3.1.3 TopBraid SHACL API

The TopBraid SHACL API [4], developed by Holger Knublauch (one of the SHACL specification editors), is a Java-based implementation that also builds on Apache Jena. TopBraid serves as a reference implementation and is used by the European Commission's RDF validator. Like Jena, TopBraid does not produce structured `sh:detail` sub-results. It may include the name of the referenced shape in the `sh:resultMessage` text, but this information is unstructured and cannot be reliably extracted programmatically.

### 3.1.4 Trav-SHACL

Figuera, Rohde, and Vidal [5] proposed Trav-SHACL, a SHACL engine focused on validation efficiency for large knowledge graphs. Trav-SHACL optimizes the traversal order of shapes in a shape schema so that invalid entities are detected early, reducing needless validation. On benchmarks with up to 34 million triples, Trav-SHACL achieves speedups of up to 28.93x compared to prior approaches.

Trav-SHACL addresses a complementary problem to ours: it focuses on *how fast* validation can determine which nodes violate which shapes, whereas our tool focuses on *explaining why* a referencing constraint violation occurred after validation is complete. The two concerns are orthogonal — Trav-SHACL's output is still a standard SHACL validation report, and our explanation tool could operate on reports produced by any engine, including Trav-SHACL.

### 3.1.5 SHACL Dashboard

Mäkelburg, Zacouris, Ke, and Acosta [19] presented the SHACL Dashboard, a tool for interactive visualization and multidimensional analysis of SHACL validation reports over large-scale knowledge graphs. The dashboard loads both the shapes graph and the validation report into a SPARQL endpoint, then uses 63 pre-defined SPARQL queries to compute summary statistics, violation distributions, and per-shape breakdowns. Its GUI provides three analytical views: a Home View with aggregate statistics and violation distributions, a Shapes View correlating the number of constraints per shape with the number of violations, and a Shape Insights view showing per-attribute heatmaps of violated constraint components. The dashboard also computes a Shannon entropy metric to quantify whether violations within a shape are concentrated on one constraint type or spread across many.

The SHACL Dashboard is the closest existing work to our tool in terms of *user-facing goals*: both aim to make large validation reports interpretable and actionable. However, the two tools address different aspects of the problem:

**Key differences:**
- *Scope*: The SHACL Dashboard analyzes the *aggregate structure* of a validation report — which shapes have the most violations, which constraint types dominate, how violations are distributed. Our tool explains *individual* referencing constraint violations — what concrete leaf failure caused an opaque `sh:NodeConstraintComponent` result, through which chain of shapes.
- *Referencing constraints*: The SHACL Dashboard treats all `sh:ValidationResult` entries uniformly. It does not distinguish between self-contained violations (e.g., `sh:minCount`) and opaque referencing failures (`sh:NodeConstraintComponent`), and does not expand nested `sh:node` chains. Our tool specifically targets this gap.
- *Architecture*: The SHACL Dashboard queries the report as-is via SPARQL; our tool *transforms* the report by recursively expanding referencing constraints, deduplicating diamond paths, and generating repair hints.
- *Complementarity*: The two tools are complementary. The SHACL Dashboard could be used to identify which shapes and constraint types produce the most violations at scale, while our tool could then be used to drill down into specific referencing constraint failures to understand their root causes.

**Difference from our approach.** All validation tools above focus on *detecting* violations or *visualizing* their aggregate distribution. None of them produce structured explanation trees that trace referencing constraint failures to their root causes. The raw reports require users to manually navigate the shapes graph and data graph to understand opaque `sh:NodeConstraintComponent` results. Our tool fills this gap by post-processing validation reports into actionable explanations.

## 3.2 Formal Foundations of SHACL

Several works have established formal frameworks for reasoning about SHACL's expressiveness, semantics, and complexity. While these do not directly address the explanation problem, they provide the theoretical grounding for understanding what SHACL can express and how validation works.

### 3.2.1 Semantics and Validation of Recursive SHACL

Corman, Reutter, and Savkovic [6] provided the first concise formal semantics for SHACL Core constraint components, extending the language to handle arbitrary recursion. They showed that validation under supported-model semantics is NP-complete in both data and combined complexity, while the non-recursive case (which covers the standard SHACL specification) is P-complete in combined complexity and NLogSpace-complete in data complexity.

Their work is relevant because our tool's expansion algorithm must handle shapes that reference other shapes — a form of navigation through the shapes graph that, in the non-recursive case, always terminates. Our cycle detection mechanism (the visited set) guards against the recursive case, which the standard SHACL specification leaves undefined.

### 3.2.2 SHACL as a Description Logic

Bogaerts, Jakubowski, and Van den Bussche [7] demonstrated that SHACL is essentially a description logic in disguise, establishing formal connections between SHACL constraints and description logic axioms. This perspective clarifies that SHACL's `sh:node` constraint corresponds to concept inclusion — requiring a node to be in the extension of another concept — and that the expansion of `sh:node` references is analogous to unfolding concept definitions.

### 3.2.3 Common Foundations for Graph Schema Languages

Ahmetaj et al. [8] provided a unified formal framework for comparing SHACL, ShEx, and PG-Schema, the three principal graph schema languages. Their Common Graph Schema Language (CoGSL) identifies the functionalities shared by all three. Importantly, they show that all three languages share the ability to express cardinality constraints, datatype constraints, and shape references — though their mechanisms differ.

Their formalization of SHACL shapes as unary formulas over graphs (Section 3 of their paper) directly informs our understanding of what a shape validation failure means: a node fails a shape when the graph around it does not satisfy the formula. Our contribution is making this failure *visible* when the formula involves nested shape references.

### 3.2.4 SHACL Review

Pareti and Konstantinidis [9] provided a comprehensive review of SHACL covering its constructs, formal semantics, and reasoning problems (satisfiability, containment). Their survey identifies the interaction between different SHACL constructs as a key source of complexity for users. While their review focuses on schema-level reasoning rather than instance-level explanation, it highlights the need for tools that make SHACL validation results interpretable — a need our tool addresses.

## 3.3 Explanation and Debugging of SHACL Violations

This is the area most closely related to our work. We discuss three approaches: formal explanation through repairs, rule-based explanation through logical proofs, and LLM-based explanation through natural language generation.

### 3.3.1 Reasoning about Explanations for Non-Validation

Ahmetaj, David, Ortiz, Polleres, Shehu, and Simkus [10] studied the problem of explaining why an RDF graph does not validate against SHACL constraints. Their notion of explanation is a *repair*: a set of additions to and deletions from the data graph such that the repaired graph satisfies the constraints. They define decision problems for reasoning about such explanations, including checking whether a repair exists, whether a specific triple must appear in every repair, and whether a repair of bounded size exists.

Their work addresses explanation at the *constraint-set level*: given a graph that violates a set of SHACL shapes, what changes would make it valid? This is a fundamentally different question from ours. Our tool explains *individual* `sh:NodeConstraintComponent` violations: for a single opaque result, what are the concrete leaf-level failures that caused it? Their approach reasons about repairs across the entire shapes schema, whereas our approach drills down into the referencing chain of a single violation.

**Key differences:**
- *Scope*: Ahmetaj et al. explain non-validation of the full constraint set; we explain individual referencing constraint failures.
- *Output*: Their output is a repair (additions/deletions); our output is an explanation tree with reference chains and leaf failures.
- *Complexity*: Their decision problems are computationally hard (coNP-complete for minimal repair existence); our expansion is polynomial in the size of the shapes graph (bounded by the number of shapes and properties).
- *Practical focus*: Their approach is theoretical (complexity characterization); our tool is implemented and evaluated on real datasets.

### 3.3.2 Repairing SHACL Constraint Violations Using Answer Set Programming

In a follow-up work, Ahmetaj, David, Polleres, and Simkus [11] proposed a practical method for computing SHACL repairs using Answer Set Programming (ASP). They encode the explanation problem as a logic program where answer sets correspond to minimal repairs, and implement it using the clingo ASP solver.

This work bridges theory and practice for the repair problem, but its focus remains on computing *what to change in the data* to achieve conformance. Our tool has a different user-facing goal: it explains *what went wrong and where*, showing the user exactly which leaf constraint failed, through which reference chain. We do generate repair *hints* (e.g., "Add at least one `ex:legalName` value to `ex:acme`"), but these are derived from the constraint type and the specific failure, not from a global repair computation. Our hints are local and immediate; their repairs are global and minimal.

### 3.3.3 RDF Graph Validation Using Rule-Based Reasoning (Validatrr)

De Meester, Heyvaert, Arndt, Dimou, and Verborgh [12] proposed an alternative approach to RDF validation using rule-based reasoning with N3Logic and the EYE reasoner. Their system, Validatrr, translates SHACL constraints into N3 inference rules and uses the reasoner to validate the data graph. A key advantage of this approach is that the EYE reasoner produces formal logical proofs, which can serve as root-cause explanations for violations.

Validatrr's proof-based explanations are the closest prior work to our explanation trees. The EYE reasoner's proof traces show which rules fired and which data triggered them, providing a formal justification for each violation. However, there are important differences:

**Key differences:**
- *Architecture*: Validatrr replaces the standard SHACL validation pipeline with a custom rule-based reasoner; our tool works *on top of* existing SHACL engines, post-processing their standard reports.
- *Explanation format*: Validatrr's proofs are formal logical derivations (useful for automated reasoning but difficult for end-users to interpret); our explanation trees are structured as human-readable hierarchies with reference chains, leaf failures, and repair hints.
- *Referencing constraints*: Validatrr handles direct constraint violations well, but its treatment of nested `sh:node` chains and the specific information gap in `sh:NodeConstraintComponent` reports — the central problem of this thesis — is not its primary focus.
- *Compatibility*: Validatrr requires the EYE reasoner and N3Logic infrastructure; our tool works with any SHACL engine's output (pySHACL, Jena, TopBraid) through its fallback re-validation mechanism.
- *Scalability*: The authors evaluated Validatrr on relatively small datasets; we evaluate our tool on a LUBM-style dataset of approximately 163 MB with 891 focus nodes and 992 leaf failures.

### 3.3.4 xpSHACL: Explainable SHACL Validation Using LLMs

Publio and Labra Gayo [13] proposed xpSHACL, a system that combines rule-based justification trees with retrieval-augmented generation (RAG) over knowledge graphs and large language models (LLMs) to generate human-readable, multilingual explanations for SHACL constraint violations. The justification tree represents a step-by-step breakdown of the reasoning process that led to the identification of a violation, while the LLM transforms this tree into natural language.

xpSHACL is the most recent work on explainable SHACL validation and shares our goal of making violations understandable. However, the approaches differ substantially:

**Key differences:**
- *Focus*: xpSHACL generates natural-language explanations for individual constraint violations; our tool specifically targets the *referencing constraint* problem — tracing opaque `sh:NodeConstraintComponent` results through chains of `sh:node` references to concrete leaf failures.
- *Method*: xpSHACL uses LLMs to produce human-readable text from justification trees; our tool uses deterministic algorithmic expansion (recursive tree-building with cycle detection and deduplication) and produces structured output formats (text trees, JSON, CSV, HTML).
- *Determinism*: Our tool produces deterministic, reproducible results; LLM-based explanations may vary across invocations.
- *Nested references*: xpSHACL's justification trees trace individual constraint evaluations but do not specifically address the multi-level nesting, diamond deduplication, or cross-engine compatibility problems that are central to our work.
- *Output*: xpSHACL produces natural-language text; our tool produces structured explanation trees with multiple output formats and an interactive HTML report with filtering, searching, and an expandable graph view.

## 3.4 RDF Data Quality and Validation

### 3.4.1 Validating RDF Data

The book *Validating RDF Data* by Labra Gayo, Prud'hommeaux, Boneva, and Kontokostas [14] provides a comprehensive treatment of both SHACL and ShEx, including their design rationales, semantics, and practical usage. The book discusses validation reports and their interpretation but does not address the specific problem of explaining opaque referencing constraint failures. It serves as foundational reference material for understanding the validation landscape in which our tool operates.

### 3.4.2 SHACL and ShEx in the Wild

Rabbani, Lissandrini, and Hose [15] conducted a community survey on how SHACL and ShEx shapes are generated and adopted in practice. Their findings indicate that many practitioners find SHACL validation reports difficult to interpret, particularly when shapes are complex or involve multiple levels of referencing. This empirical evidence supports the motivation for our work: the gap between what validation reports contain and what users need to act on is a recognized practical problem.

## 3.5 Adjacent Domains

### 3.5.1 Shape Expressions (ShEx)

Shape Expressions (ShEx) [16, 17] is an alternative schema language for RDF that takes a different approach to validation. ShEx uses *triple expressions* — a generative formalism based on regular expressions — to specify the allowed neighborhoods of nodes. ShEx validators can produce structured validation output that shows which triple expression failed to match, offering a form of explanation that is inherent to the matching process.

However, ShEx's approach to referencing (shape labels in triple expressions) is structurally different from SHACL's `sh:node`: in ShEx, the referenced shape is part of the matching grammar, so failures are naturally localized during the match. SHACL's approach of delegating validation to a separate shape creates the information gap that our tool addresses. The explanation problem we solve is specific to SHACL's architecture.

### 3.5.2 Consistent Query Answering over SHACL Constraints

Ahmetaj et al. [18] studied consistent query answering (CQA) in the context of SHACL: how to answer queries over a data graph that does not satisfy its SHACL constraints, by reasoning over all possible minimal repairs. While CQA addresses a different problem (query answering under inconsistency rather than violation explanation), it shares the notion that understanding *why* constraints are violated is fundamental to working with invalid data.

## 3.6 Summary and Positioning

Table 3.1 summarizes the positioning of our approach relative to the most closely related works.

**Table 3.1: Comparison of approaches to SHACL violation explanation**

| Approach | Focus | Handles nested `sh:node` | Output format | Cross-engine | Deterministic | Scale tested |
|---|---|---|---|---|---|---|
| pySHACL `sh:detail` | Validation | Partially (raw RDF) | RDF graph | No | Yes | Large |
| Validatrr [12] | Rule-based proof | Not specifically | Logical proof | No (EYE only) | Yes | Small |
| Ahmetaj et al. [10] | Repair explanation | Schema-level | Repair sets | N/A | Yes | Theoretical |
| Ahmetaj et al. [11] | Repair computation | Schema-level | ASP answer sets | N/A | Yes | Small–Medium |
| xpSHACL [13] | NL explanation | Not specifically | Natural language | pySHACL | No (LLM) | Small–Medium |
| SHACL Dashboard [19] | Report visualization | No | Interactive dashboard | Yes (any engine) | Yes | 30M+ triples |
| **Our approach** | **Root-cause localization** | **Yes (core focus)** | **Tree, JSON, CSV, HTML** | **Yes (3 engines)** | **Yes** | **163 MB LUBM** |

The key distinction of our approach is its specific focus on the referencing constraint problem: the information gap in `sh:NodeConstraintComponent` results. While prior works address SHACL explanation from the perspectives of logical proof (Validatrr), repair computation (Ahmetaj et al.), natural language generation (xpSHACL), or aggregate report visualization (SHACL Dashboard), none of them specifically target the problem of expanding opaque `sh:node` failures into structured explanation trees with full reference chains, diamond deduplication, cycle detection, and cross-engine compatibility. Our tool fills this gap with a practical, deterministic, and scalable solution.

---

## References

[1] H. Knublauch and D. Kontokostas, "Shapes Constraint Language (SHACL)," W3C Recommendation, July 2017. https://www.w3.org/TR/shacl/

[2] A. Sommer, "pySHACL: A Python validator for SHACL." https://github.com/RDFLib/pySHACL

[3] Apache Software Foundation, "Apache Jena SHACL." https://jena.apache.org/documentation/shacl/

[4] H. Knublauch, "TopBraid SHACL API." https://github.com/TopQuadrant/shacl

[5] M. Figuera, P. D. Rohde, and M.-E. Vidal, "Trav-SHACL: Efficiently Validating Networks of SHACL Constraints," in *Proceedings of the Web Conference 2021 (WWW '21)*, pp. 3337–3347, ACM, 2021.

[6] J. Corman, J. L. Reutter, and O. Savkovic, "Semantics and Validation of Recursive SHACL," in *Proceedings of the 17th International Semantic Web Conference (ISWC 2018)*, LNCS 11136, pp. 318–336, Springer, 2018.

[7] B. Bogaerts, M. Jakubowski, and J. Van den Bussche, "SHACL: A Description Logic in Disguise," in *Logic Programming and Nonmonotonic Reasoning (LPNMR 2022)*, LNCS 13416, pp. 75–88, Springer, 2022.

[8] S. Ahmetaj, I. Boneva, J. Hidders, K. Hose, M. Jakubowski, J. E. Labra Gayo, W. Martens, F. Mogavero, F. Murlak, C. Okulmus, A. Polleres, O. Savkovic, M. Simkus, and D. Tomaszuk, "Common Foundations for SHACL, ShEx, and PG-Schema," in *Proceedings of the ACM Web Conference 2025*, ACM, 2025.

[9] P. Pareti and G. Konstantinidis, "A Review of SHACL: From Data Validation to Schema Reasoning for RDF Graphs," in *Reasoning Web. Declarative Artificial Intelligence*, LNCS 13100, pp. 115–164, Springer, 2022.

[10] S. Ahmetaj, R. David, M. Ortiz, A. Polleres, B. Shehu, and M. Simkus, "Reasoning about Explanations for Non-validation in SHACL," in *Proceedings of the 18th International Conference on Principles of Knowledge Representation and Reasoning (KR 2021)*, pp. 12–21, 2021.

[11] S. Ahmetaj, R. David, A. Polleres, and M. Simkus, "Repairing SHACL Constraint Violations Using Answer Set Programming," in *The Semantic Web – ISWC 2022*, LNCS 13489, pp. 375–391, Springer, 2022.

[12] B. De Meester, P. Heyvaert, D. Arndt, A. Dimou, and R. Verborgh, "RDF Graph Validation Using Rule-Based Reasoning," *Semantic Web Journal*, vol. 12, pp. 117–142, 2021.

[13] G. C. Publio and J. E. Labra Gayo, "xpSHACL: Explainable SHACL Validation using Retrieval-Augmented Generation and Large Language Models," in *VLDB 2025 Workshop on LLM+Graph*, 2025. arXiv:2507.08432.

[14] J. E. Labra Gayo, E. Prud'hommeaux, I. Boneva, and D. Kontokostas, *Validating RDF Data*, Synthesis Lectures on the Semantic Web, Morgan & Claypool, 2018.

[15] K. Rabbani, M. Lissandrini, and K. Hose, "SHACL and ShEx in the Wild: A Community Survey on Validating Shapes Generation and Adoption," in *Companion Proceedings of the Web Conference 2022*, ACM, 2022.

[16] E. Prud'hommeaux, J. E. Labra Gayo, and H. Solbrig, "Shape Expressions: An RDF Validation and Transformation Language," in *Proceedings of the 10th International Workshop on Semantic Evaluation (SemEval)*, 2014.

[17] I. Boneva, J. E. Labra Gayo, and E. Prud'hommeaux, "Semantics and Validation of Shapes Schemas for RDF," in *Proceedings of the 16th International Semantic Web Conference (ISWC 2017)*, LNCS 10587, pp. 104–120, Springer, 2017.

[18] S. Ahmetaj, S. Fischl, R. Pichler, A. Polleres, and M. Simkus, "Consistent Query Answering over SHACL Constraints," in *Proceedings of the 21st International Conference on Principles of Knowledge Representation and Reasoning (KR 2024)*, 2024.

[19] J. Mäkelburg, Z. Zacouris, J. Ke, and M. Acosta, "SHACL Dashboard: Analyzing Data Quality Reports over Large-Scale Knowledge Graphs," in *Proceedings of the 24th International Semantic Web Conference (ISWC 2025)*, 2025.
