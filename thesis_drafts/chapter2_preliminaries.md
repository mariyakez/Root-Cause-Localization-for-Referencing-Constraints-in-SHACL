# Chapter 2: Preliminaries

This chapter introduces the technical foundations needed to understand the rest of this thesis. We begin with the Resource Description Framework (RDF), the data model on which SHACL operates. We then present SHACL itself — its shapes, constraints, targeting mechanism, and validation reports. Finally, we examine the specific vocabulary and structure of SHACL validation reports, with particular attention to how referencing constraints such as `sh:node` are represented, as this is where the information gap addressed by this thesis arises.

## 2.1 The Resource Description Framework (RDF)

The Resource Description Framework (RDF) [14] is a W3C standard for representing information as a directed, labeled graph. The fundamental unit of RDF data is the *triple*, consisting of a subject, predicate, and object:

```
(subject, predicate, object)
```

An RDF graph is a finite set of such triples. Subjects and predicates are identified by Internationalized Resource Identifiers (IRIs), while objects may be IRIs, blank nodes, or literal values. Formally:

**Definition 2.1 (RDF Triple).** Let **I** be the set of all IRIs, **B** the set of all blank nodes, and **L** the set of all literals. An *RDF triple* is a tuple *(s, p, o)* where *s* ∈ **I** ∪ **B**, *p* ∈ **I**, and *o* ∈ **I** ∪ **B** ∪ **L**.

**Definition 2.2 (RDF Graph).** An *RDF graph* is a finite set of RDF triples *G* ⊆ (**I** ∪ **B**) × **I** × (**I** ∪ **B** ∪ **L**).

IRIs serve as globally unique identifiers for resources. In practice, IRIs are often abbreviated using namespace prefixes. For instance, the prefix `ex:` may stand for `http://example.org/`, so that `ex:alice` denotes the full IRI `http://example.org/alice`.

Blank nodes are locally scoped identifiers used to represent anonymous resources — nodes that exist in the graph but have no global name. They frequently appear in SHACL shapes graphs to represent anonymous property shapes.

Literals represent concrete data values. Each literal has a lexical form (a string) and a datatype IRI. For example, `"twenty"` is a plain string literal, while `"42"^^xsd:integer` is a typed literal with the XML Schema datatype `xsd:integer`.

**Example 2.1.** The following RDF graph (in Turtle syntax) describes an employee:

```turtle
@prefix ex:  <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:alice  a            ex:Employee ;
          ex:employeeId "E001" ;
          ex:age        "twenty" .
```

This graph contains three triples. The predicate `a` is shorthand for `rdf:type`. The object `"twenty"` is a string literal — notably, not a valid `xsd:integer`, which will become relevant when we discuss SHACL validation.

## 2.2 The Shapes Constraint Language (SHACL)

SHACL (Shapes Constraint Language) [27] is a W3C recommendation for validating RDF graphs against a set of conditions called *shapes*. A SHACL *shapes graph* is itself an RDF graph that defines these shapes. Given a *data graph* (the RDF graph to be validated), a SHACL processor checks whether the data conforms to the shapes and produces a *validation report* listing any violations found.

### 2.2.1 Shapes and Targets

A SHACL shape defines a set of constraints that apply to specific nodes in the data graph. SHACL distinguishes two kinds of shapes:

- **Node shapes** (`sh:NodeShape`): constraints that apply to a focus node directly.
- **Property shapes**: constraints that apply to the values of a specific property of a focus node, identified by `sh:path`.

Each shape may declare *targets* that determine which nodes in the data graph it applies to. The most common targeting mechanisms are:

| Targeting property      | Meaning                                               |
|-------------------------|-------------------------------------------------------|
| `sh:targetClass C`      | All instances of class `C` (via `rdf:type`)           |
| `sh:targetNode n`       | The specific node `n`                                 |
| `sh:targetSubjectsOf p` | All nodes that appear as subjects of predicate `p`    |
| `sh:targetObjectsOf p`  | All nodes that appear as objects of predicate `p`     |

A node selected by a target is called a *focus node*. The SHACL processor validates each focus node against the constraints defined in the shape.

**Example 2.2.** The following shape targets all instances of `ex:Employee` and requires that each has at least one `ex:employeeId`:

```turtle
ex:EmployeeShape
    a sh:NodeShape ;
    sh:targetClass ex:Employee ;
    sh:property [
        sh:path    ex:employeeId ;
        sh:minCount 1 ;
    ] .
```

The anonymous node `[ sh:path ex:employeeId ; sh:minCount 1 ]` is a *property shape*. It is a blank node in the shapes graph — it has no global IRI, but it defines the constraint that the property `ex:employeeId` must have at least one value.

### 2.2.2 SHACL Core Constraint Components

The SHACL Core specification defines a fixed set of *constraint components*, each corresponding to a specific type of condition. When a constraint is violated, the validation report records the component that detected the failure. Table 2.1 lists the constraint components relevant to this thesis.

**Table 2.1: SHACL Core Constraint Components**

| Component                   | Parameter(s)         | Meaning                                                 |
|-----------------------------|----------------------|---------------------------------------------------------|
| `MinCountConstraint`        | `sh:minCount`        | Property must have at least *n* values                  |
| `MaxCountConstraint`        | `sh:maxCount`        | Property must have at most *n* values                   |
| `DatatypeConstraint`        | `sh:datatype`        | All values must have the specified datatype             |
| `ClassConstraint`           | `sh:class`           | All values must be instances of the specified class     |
| `NodeKindConstraint`        | `sh:nodeKind`        | Values must be IRIs, blank nodes, or literals           |
| `PatternConstraint`         | `sh:pattern`         | String value must match a regular expression            |
| `InConstraint`              | `sh:in`              | Value must be one of a specified list                   |
| `HasValueConstraint`        | `sh:hasValue`        | Property must contain a specific value                  |
| `MinInclusiveConstraint`    | `sh:minInclusive`    | Numeric value must be ≥ a bound                        |
| `MaxInclusiveConstraint`    | `sh:maxInclusive`    | Numeric value must be ≤ a bound                        |
| `EqualsConstraint`          | `sh:equals`          | Values must equal those of another property             |
| `DisjointConstraint`        | `sh:disjoint`        | Values must not overlap with another property           |
| `LessThanConstraint`        | `sh:lessThan`        | Each value must be less than the corresponding value    |
| `ClosedConstraint`          | `sh:closed`          | Node must not have properties outside a declared set    |
| **`NodeConstraint`**        | **`sh:node`**        | **Value must conform to a specified shape (referencing)**|

All components except `NodeConstraintComponent` produce *self-contained* validation results: the result includes the focus node, the property path, the offending value, the constraint type, and typically a human-readable message. These are the results we call *leaf failures* — they are immediately actionable.

The last component, `NodeConstraintComponent`, is fundamentally different. It is a *referencing constraint* that delegates validation to another shape. This distinction is central to the problem addressed in this thesis.

### 2.2.3 Referencing Constraints: `sh:node`

The constraint parameter `sh:node` declares that a node (or the values of a property) must conform to another named shape. This mechanism enables *modular* shape definitions: rather than duplicating constraints, a shape designer can factor common requirements into a shared shape and reference it from multiple places.

**Definition 2.3 (Referencing Constraint).** A *referencing constraint* is a constraint that, instead of directly testing a property of the focus node, requires the focus node (or a value node) to satisfy an entire separate shape. In SHACL Core, `sh:node` is the primary referencing constraint.

There are two common patterns for `sh:node`:

**Node-level `sh:node`.** The referenced shape is declared directly on a node shape. The focus node itself must conform to the referenced shape.

```turtle
ex:EmployeeShape
    a sh:NodeShape ;
    sh:targetClass ex:Employee ;
    sh:node ex:PersonShape .
```

Here, every `ex:Employee` must also satisfy all constraints in `ex:PersonShape`.

**Property-level `sh:node`.** The referenced shape is declared inside a property shape. Each value of the property must conform to the referenced shape.

```turtle
ex:EmployeeShape
    a sh:NodeShape ;
    sh:targetClass ex:Employee ;
    sh:property [
        sh:path ex:worksFor ;
        sh:node ex:CompanyShape ;
    ] .
```

Here, the value node reached via `ex:worksFor` (e.g., `ex:acme`) must satisfy `ex:CompanyShape`. If `ex:CompanyShape` requires `ex:legalName` and `ex:acme` lacks it, the concrete failure is a missing `ex:legalName` — but the top-level report only says that `ex:alice`'s `ex:worksFor` value "does not conform to `ex:CompanyShape`".

### 2.2.4 Nested References and Structural Complexities

Referencing constraints can be *nested*: a shape referenced by `sh:node` may itself reference another shape, forming a chain. This thesis identifies three structural patterns that arise in practice:

**Multi-level chains.** Shape A references shape B via `sh:node`, and shape B references shape C. A failure in shape C is two levels deep and invisible in the top-level report.

```
ContractorShape  --sh:node-->  EmployeeShape  --sh:node-->  PersonShape
```

**Diamond references.** Two intermediate shapes both reference the same base shape. A single focus node may fail the base shape, but the failure is reached through two distinct paths. Without deduplication, the same leaf failure is reported twice.

```
       StaffShape
      /          \
 sh:node       sh:node
    |              |
FulltimeShape  ParttimeShape
      \          /
   sh:node    sh:node
         \  /
     PersonShape
```

**Cyclic references.** A shape references itself, either directly or through a chain. Without cycle detection, naive expansion would recurse infinitely.

```
TreeShape  --sh:node-->  TreeShape   (self-reference)
```

### 2.2.5 Property Path Expressions

SHACL supports a subset of SPARQL property paths for use in `sh:path`. A property path specifies how to navigate from a focus node to its value nodes. The SHACL specification supports the following path types:

| Path type        | Syntax                   | Meaning                                       |
|------------------|--------------------------|-----------------------------------------------|
| Predicate path   | `ex:name`                | Direct property traversal                     |
| Inverse path     | `[ sh:inversePath p ]`   | Traverse property `p` in reverse              |
| Sequence path    | `( p1 p2 )`             | Traverse `p1` then `p2`                       |
| Alternative path | `[ sh:alternativePath (p1 p2) ]` | Traverse either `p1` or `p2`        |
| Zero-or-more     | `[ sh:zeroOrMorePath p ]`| Traverse `p` zero or more times               |

In validation reports, the `sh:resultPath` property records which path was used to reach the violating value. For simple predicate paths, this is straightforward. For complex paths, the report serializes the path structure as an RDF list, which must be reconstructed to display a meaningful explanation.

## 2.3 SHACL Validation Reports

When a SHACL processor validates a data graph against a shapes graph, it produces a *validation report* — itself an RDF graph conforming to the SHACL vocabulary. The report serves as the primary interface between the validation engine and the user.

### 2.3.1 Report Structure

**Definition 2.4 (Validation Report).** A SHACL validation report is an RDF graph containing:

1. Exactly one node of type `sh:ValidationReport`, with:
   - `sh:conforms` — a boolean indicating whether the data graph conforms,
   - Zero or more `sh:result` edges pointing to `sh:ValidationResult` nodes.

2. Each `sh:ValidationResult` carries:

| Property                        | Meaning                                         |
|---------------------------------|-------------------------------------------------|
| `sh:focusNode`                  | The node being validated                        |
| `sh:resultPath`                 | The property path (if applicable)               |
| `sh:value`                      | The offending value (if applicable)             |
| `sh:sourceConstraintComponent`  | The constraint component that detected the failure |
| `sh:sourceShape`                | The shape containing the violated constraint    |
| `sh:resultSeverity`             | `sh:Violation`, `sh:Warning`, or `sh:Info`      |
| `sh:resultMessage`              | Human-readable description (optional)           |

**Example 2.3.** For a direct `sh:minCount` violation where `ex:alice` is missing `ex:employeeId`, the validation result is self-contained:

```turtle
[] a sh:ValidationResult ;
   sh:focusNode                   ex:alice ;
   sh:resultPath                  ex:employeeId ;
   sh:sourceConstraintComponent   sh:MinCountConstraintComponent ;
   sh:sourceShape                 _:b0 ;
   sh:resultSeverity              sh:Violation ;
   sh:resultMessage               "An employee must have an employeeId" .
```

This result is *actionable*: it tells the user exactly which node failed, on which property, and what kind of constraint was violated.

### 2.3.2 The `sh:NodeConstraintComponent` Result

When a referencing constraint (`sh:node`) fails, the validation result looks fundamentally different:

```turtle
[] a sh:ValidationResult ;
   sh:focusNode                   ex:alice ;
   sh:sourceConstraintComponent   sh:NodeConstraintComponent ;
   sh:sourceShape                 ex:EmployeeShape ;
   sh:value                       ex:alice ;
   sh:resultMessage               "Value does not conform to shape ex:PersonShape" .
```

**Table 2.2: Information gap in `sh:NodeConstraintComponent` results**

| Information needed          | Present in NodeConstraintComponent result? | How to obtain it            |
|-----------------------------|--------------------------------------------|-----------------------------|
| Focus node                  | Yes (`sh:focusNode`)                       | Direct                      |
| Which shape failed          | Partially (`sh:sourceShape` = parent)      | Navigate `sh:node`          |
| Which property failed       | No (`sh:resultPath` absent)                | Re-validate                 |
| Offending value             | No (only focus node repeated)              | Re-validate                 |
| Concrete constraint type    | No (only `NodeConstraintComponent`)        | Re-validate                 |
| Actionable message          | Partially (vague)                          | Re-validate                 |
| Reference chain             | No                                         | Track during expansion      |

This table summarizes the core problem: a `sh:NodeConstraintComponent` result reports *that* a referenced shape failed, but not *why*. The concrete property-level violations — the root causes — are hidden.

### 2.3.3 The `sh:detail` Mechanism

The SHACL specification defines an optional property `sh:detail` that allows a validation result to link to more granular sub-results. If a SHACL engine supports `sh:detail`, a `NodeConstraintComponent` result may include nested results that reveal the failures inside the referenced shape:

```turtle
[] a sh:ValidationResult ;
   sh:focusNode                   ex:alice ;
   sh:sourceConstraintComponent   sh:NodeConstraintComponent ;
   sh:sourceShape                 ex:EmployeeShape ;
   sh:detail [
       a sh:ValidationResult ;
       sh:focusNode               ex:alice ;
       sh:resultPath              ex:age ;
       sh:value                   "twenty" ;
       sh:sourceConstraintComponent sh:DatatypeConstraintComponent ;
       sh:sourceShape             _:b0 ;
   ] .
```

However, `sh:detail` is **not mandatory** in the SHACL specification. Its support varies across engines:

- **pySHACL** provides `sh:detail` sub-results for `sh:node` failures.
- **Apache Jena SHACL** does not include `sh:detail`. It reports only the top-level `NodeConstraintComponent` result, with `sh:sourceShape` pointing to the enclosing node shape and `sh:resultPath` identifying the property that triggered the reference.
- **TopBraid** may include the name of the referenced shape in the result message but does not use `sh:detail`.

This variation across engines is significant: an explanation tool cannot assume that `sh:detail` is present. When it is absent, the tool must reconstruct the missing information by other means — specifically, by re-validating the focus node or value node against the referenced shape.

## 2.4 SHACL Validation Engines

This thesis works with validation reports from multiple SHACL engines. Each engine conforms to the SHACL specification but differs in the structure and completeness of its reports.

### 2.4.1 pySHACL

pySHACL [16] is a Python implementation of the SHACL specification built on top of the rdflib library. It supports SHACL Core constraints and produces validation reports with `sh:detail` sub-results for referencing constraint failures. This makes pySHACL reports the most informative for our purposes: when `sh:detail` is present, the explanation engine can walk the detail tree directly to find leaf failures without re-validation.

pySHACL is used in two roles in this thesis:
1. As the **primary validation engine** when the user provides a data graph and a shapes graph directly.
2. As the **re-validation backend** when the user provides an external report from another engine — the explanation tool uses pySHACL to re-validate specific nodes against specific shapes when `sh:detail` is absent.

### 2.4.2 Apache Jena SHACL

Apache Jena [25] is a Java-based RDF framework that includes a SHACL validation processor. Jena's SHACL reports do not include `sh:detail`. For a `sh:node` failure, Jena typically reports:

- `sh:sourceShape` pointing to the enclosing node shape (not the referenced shape),
- `sh:resultPath` identifying the property under which the `sh:node` constraint appears,
- `sh:value` containing the node that should have conformed to the referenced shape.

This information is sufficient to *locate* the referenced shape in the shapes graph (by finding the property shape with the matching path under the source shape, then reading its `sh:node` value), but it does not reveal *why* the referenced shape failed.

### 2.4.3 TopBraid-like Engines

TopBraid and similar engines may include the name of the referenced shape in the `sh:resultMessage` (e.g., "Value does not conform to shape ex:PersonShape") but do not provide structured sub-results. Some engines may omit `sh:sourceShape` entirely, requiring the explanation tool to rely on other heuristics.

## 2.5 Formal Problem Formulation

We conclude this chapter by restating the problem addressed in this thesis using the notation introduced above.

**Definition 2.5 (Explanation Tree).** Given a data graph *G*, a shapes graph *S*, and a validation report *R* = validate(*G*, *S*), an *explanation tree* for a focus node *f* is a rooted tree *T* where:

- The **root** is labeled with the focus node *f* and the top-level shape that *f* was validated against.
- Each **internal node** is a *reference node* labeled with:
  - A source shape *s* (the shape containing the `sh:node` constraint),
  - A referenced shape *r* (the shape that `sh:node` points to),
  - A property path *p* (for property-level `sh:node`), and
  - The chain of shapes traversed from the root to reach this reference.
- Each **leaf** is a *leaf failure* recording:
  - The focus node or value node on which the failure occurred,
  - The property path (`sh:resultPath`),
  - The offending value (`sh:value`),
  - The constraint component (e.g., `sh:DatatypeConstraintComponent`),
  - The full reference chain from the top-level shape to the leaf's owning shape.

**Definition 2.6 (Root-Cause Localization Problem).** The *root-cause localization problem for referencing constraints* is: given *G*, *S*, and *R*, produce an explanation tree for every `sh:NodeConstraintComponent` result in *R*, such that:

1. **Completeness**: every concrete constraint violation reachable through chains of `sh:node` references appears as a leaf in some explanation tree.
2. **Soundness**: every leaf corresponds to an actual constraint violation in *G* against *S*.
3. **Non-redundancy**: when the same leaf failure is reachable through multiple reference paths (diamond pattern), it appears exactly once, with all alternate paths recorded as metadata.
4. **Termination**: expansion terminates even in the presence of cyclic shape references.
