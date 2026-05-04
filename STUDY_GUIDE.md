# SHACL Test Cases — Study Guide
## What to Observe in Each Validation Report

---

## How to Run

```bash
pip install pyshacl rdflib
python run_tests.py
```

---

## The Core Problem in One Diagram

```
SHACL Report today:                 What your tool must produce:

❌ NodeConstraintComponent          ❌ NodeConstraintComponent
   focusNode: ex:alice                 focusNode: ex:alice
   sourceShape: :EmployeeShape         sourceShape: :EmployeeShape
   value: ex:alice                     └── ❌ DatatypeConstraintComponent
   resultPath: —                               path:    ex:age
   (nothing else)                              value:   "twenty"
                                               message: must be xsd:integer
```

The report tells you **something failed** inside `:PersonShape`.
It does NOT tell you **what** failed or **where**. That gap is the thesis.

---

## What a `sh:ValidationResult` Looks Like in RDF

```turtle
[] a sh:ValidationResult ;
   sh:resultSeverity sh:Violation ;
   sh:focusNode ex:alice ;
   sh:resultPath ex:age ;            # ← ABSENT for NodeConstraintComponent!
   sh:value "twenty" ;               # ← ABSENT for NodeConstraintComponent!
   sh:sourceConstraintComponent sh:DatatypeConstraintComponent ;
   sh:sourceShape _:b0 ;             # blank node (anonymous sh:property [])
   sh:resultMessage "must be xsd:integer" .
```

For a **NodeConstraintComponent** result, the report looks like:

```turtle
[] a sh:ValidationResult ;
   sh:resultSeverity sh:Violation ;
   sh:focusNode ex:alice ;
   sh:resultPath ???  ;              # likely absent or the focus node itself
   sh:value ex:alice ;               # value = the focus node (unhelpful)
   sh:sourceConstraintComponent sh:NodeConstraintComponent ;
   sh:sourceShape ex:EmployeeShape ; # shape that CONTAINS the sh:node
   sh:resultMessage "..." .          # vague — "does not conform to :PersonShape"
```

**Notice what's missing:** which shape was referenced, which property failed,
what value was wrong.

---

## TC1 — Single Leaf: What to Look For

**File:** `tc1_single_leaf.ttl`

Run and check:

1. How many `sh:ValidationResult` nodes are in the report?
   - Expected: **1** (only the NodeConstraintComponent)
   - The DatatypeConstraintComponent on `ex:age = "twenty"` is NOT reported.

2. What does `sh:sourceShape` point to?
   - It points to `ex:EmployeeShape` (the shape that *contains* `sh:node`),
     NOT to `ex:PersonShape` (the shape that *detected* the failure).

3. Is `sh:resultPath` present?
   - Expected: **no** — this is key. NodeConstraintComponent does not set a path.

4. What is `sh:value`?
   - It will be `ex:alice` (the focus node itself) — not the offending value.

**Reconstruction needed:**
- Re-validate `ex:alice` against `ex:PersonShape`
- Find the DatatypeConstraintComponent result
- That gives you path=`ex:age`, value=`"twenty"`, message

---

## TC2 — Multiple Leaves: What to Look For

**File:** `tc2_multi_leaf.ttl`

Run and check:

1. How many results? Expected: **1** (NodeConstraintComponent only).
   - Even though there are 3 real violations inside `:PersonShape`, the
     report hides all of them behind one NodeConstraintComponent.

2. Does pyshacl surface ANY of the three leaf failures?
   - If it does, note which ones and update your thesis claim.
   - If it doesn't, this confirms your tool must find all 3 independently.

3. What `sh:resultMessage` does pyshacl generate for NodeConstraintComponent?
   - Is it informative enough to tell the user what broke?

**Reconstruction needed:**
- Re-validate `ex:bob` against `ex:PersonShape`
- Expect 3 results:
  - MinCount on `ex:age` (minCount=1, count=0)
  - MinCount on `ex:name` (minCount=1, count=0)
  - Pattern on `ex:email` (value="not-an-email")

---

## TC3 — Two-Level Nesting: What to Look For

**File:** `tc3_two_level.ttl`

Chain: ContractorShape → EmployeeShape → PersonShape

Run and check:

1. How many NodeConstraintComponent results appear?
   - Option A: **1** — only the top-level (ContractorShape)
   - Option B: **2** — top + middle (EmployeeShape)
   - This reveals whether pyshacl recurses into nested shapes at all.

2. Does the report mention `ex:EmployeeShape` as a sourceShape anywhere?
   - If yes: the engine partially expands. Your tool can leverage this.
   - If no: your tool must walk the full chain itself.

3. The leaf DatatypeConstraintComponent (age="thirty-one") — does it appear?
   - Expected: **no** — it is 2 levels deep.

**Key insight for your expansion engine:**
```
expand(carol, ContractorShape):
  → NodeConstraintComponent found → recurse into EmployeeShape
    expand(carol, EmployeeShape):
      → NodeConstraintComponent found → recurse into PersonShape
        expand(carol, PersonShape):
          → DatatypeConstraintComponent  ← LEAF, return this
```

---

## TC4 — Mixed Direct + Nested: What to Look For

**File:** `tc4_mixed.ttl`

Run and check:

1. How many results? Expected: **2**:
   - MinCountConstraintComponent for `ex:department` (direct, on ManagerShape)
   - NodeConstraintComponent (nested, pointing to PersonShape)

2. Check `sh:sourceShape` on each result:
   - The direct MinCount should have `sourceShape = ex:ManagerShape`
   - The NodeConstraintComponent should have `sourceShape = ex:ManagerShape`
     (NOT ex:PersonShape — that's the shape referenced, not the source)

3. Are the leaf failures inside PersonShape (age Datatype, name MinCount) present?
   - Expected: **no** — both hidden behind the NodeConstraintComponent.

**Key insight for your tool:**
- You must handle a mixed set of results per focus node.
- Some results are already actionable (the direct MinCount).
- Others need expansion (the NodeConstraintComponent).
- Your tree should show both at the same level under the focus node.

---

## TC5 — Diamond Reference: What to Look For

**File:** `tc5_diamond.ttl`

Chain: StaffShape → FulltimeShape → PersonShape
                  → ParttimeShape → PersonShape  (PersonShape hit twice!)

Run and check:

1. How many NodeConstraintComponent results? Expected: **2**:
   - One for FulltimeShape branch
   - One for ParttimeShape branch

2. Are the PersonShape leaf failures reported **twice** (once per branch)?
   - If yes: pyshacl does NOT deduplicate → your tool must.
   - If no: pyshacl deduplicates → your tool should match this behaviour.

3. Are the hoursPerWeek and contractHours MinCount violations reported?
   - These are direct violations of FulltimeShape/ParttimeShape respectively.
   - Expected: they appear as separate MinCount results.

4. What happens in your expansion engine with a diamond?
   Without cycle/dedup detection:
   ```
   expand(eve, StaffShape)
     → expand(eve, FulltimeShape)
         → expand(eve, PersonShape)   ← 1st visit
             → age DatatypeConstraint (LEAF)
             → name MinCount (LEAF)
     → expand(eve, ParttimeShape)
         → expand(eve, PersonShape)   ← 2nd visit (same node+shape!)
             → age DatatypeConstraint (DUPLICATE!)
             → name MinCount (DUPLICATE!)
   ```
   Solution: track `visited: set[tuple[focusNode, shape]]`

---

## Summary: The Information Gap Table

| What you need       | In NodeConstraintComponent result? | How to get it          |
|---------------------|------------------------------------|------------------------|
| Focus node          | ✅ sh:focusNode                    | Direct                 |
| Which shape failed  | ⚠️  sh:sourceShape (parent shape)  | Must navigate sh:node  |
| Which property      | ❌ absent                          | Re-validate            |
| Offending value     | ❌ absent (just focus node)        | Re-validate            |
| Constraint type     | ❌ only "NodeConstraintComponent"  | Re-validate            |
| Human message       | ⚠️  vague                          | Re-validate            |
| Reference chain     | ❌ absent                          | Track during expansion |

---

## Minimal Expansion Engine (Starter)

```python
from pyshacl import validate
from rdflib import Graph, Namespace, RDF

SH = Namespace("http://www.w3.org/ns/shacl#")

def expand(focus_node, shape_uri, shapes_graph, data_graph,
           chain=None, visited=None):
    """
    Returns a list of LeafFailure dicts for all concrete violations
    reachable from (focus_node, shape_uri).
    """
    if chain   is None: chain   = []
    if visited is None: visited = set()

    key = (str(focus_node), str(shape_uri))
    if key in visited:
        return []                          # cycle / diamond guard
    visited.add(key)

    # Build a minimal shapes graph: just this one shape targeting this node
    local_shapes = build_targeted_shapes_graph(shape_uri, shapes_graph, focus_node)

    conforms, report, _ = validate(
        data_graph,
        shacl_graph=local_shapes,
        inference="none",
        abort_on_first=False,
    )

    leaves = []
    for result in report.subjects(RDF.type, SH.ValidationResult):
        component = report.value(result, SH.sourceConstraintComponent)
        if str(component) == str(SH.NodeConstraintComponent):
            # Find the referenced shape from the shapes graph
            ref_shape = find_referenced_shape(result, shapes_graph)
            leaves += expand(
                focus_node, ref_shape, shapes_graph, data_graph,
                chain=chain + [shape_uri], visited=visited
            )
        else:
            leaves.append({
                "focus_node":  focus_node,
                "value_node":  report.value(result, SH.value),
                "path":        report.value(result, SH.resultPath),
                "component":   component,
                "message":     report.value(result, SH.resultMessage),
                "chain":       chain + [shape_uri],
            })
    return leaves
```

The two helpers (`build_targeted_shapes_graph`, `find_referenced_shape`) are
the interesting implementation challenges to solve in your thesis.
