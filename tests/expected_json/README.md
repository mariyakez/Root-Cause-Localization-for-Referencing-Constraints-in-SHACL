# Stored expected explanations

One document per fixture, compared field by field by `tests/test_expected_json.py`.
These fixtures previously had no content assertion of their own: the only test
that reached them checked that the command produced a summary or reported the
data as valid.

Regenerate with:

    python3 tools/regenerate_expected_json.py

Review the diff before committing it. A snapshot that changes without an
intended reason is a regression, not a file to refresh.

## What these documents are, and are not

They were captured from the implementation, not derived independently. They
establish that the explanation does not change silently. They do not establish
that the captured output was correct in the first place.

No value here is known to be wrong.

### `referencedShape`, and why it is not an oracle for the chain below it

A reference node records the shape its `sh:node` step points at. This field was
previously resolved by taking the first `sh:node` declared by the step's source
shape, which was wrong wherever a shape declares several and the branch that
survived deduplication was not the one listed first. `display_reference_shape`
now resolves it from the source shapes of the result's own `sh:detail` children,
which name the branch the result actually travelled. The values in this
directory were correct even before that change, because in `tc26` and `tc52` the
surviving branch happened to be the first one listed; `tc4` and `tc6`, asserted
in `tests/test_cli_pipeline.py`, were the two that were wrong.

The field can still disagree with the chain of a leaf beneath it, and that is
deduplication rather than a defect. In `tc26` the `ex:StaffShape` branch loses
its shared leaves to the `ex:ContractorShape` branch, is pruned once empty, and
its one unique leaf is promoted to the surviving step:

```json
{ "type": "reference", "shape": "ex:WorkerShape", "referencedShape": "ex:ContractorShape",
  "children": [
    { "type": "leaf", "path": "ex:department", "refChain": ["ex:WorkerShape", "ex:StaffShape"] }
  ] }
```

The step really did reach `ex:ContractorShape`; the leaf really was reached
through `ex:StaffShape`. Read `refChain`, not the enclosing step, for the route
to a leaf.

On the fallback path there are no `sh:detail` children to attribute with, and
the sibling results of a diamond are otherwise identical, so a step there
records no referenced shape at all rather than guessing one.
`tests/test_fallback.py` asserts that reconstruction may lose this attribution
but may never contradict it.

## Normalizations

Comparison is order-insensitive: root and sibling order vary between runs, so
both sides are sorted by content first.

- A complex property path is reported as a blank-node label, which `rdflib`
  mints afresh on every parse, so those labels become
  `_:blank-path-expression`. The comparison establishes that the path is a
  blank-node expression, not which expression it is.
- TC38 and TC39 declare two `sh:message` values each. The explanation shows
  both, sorted and joined with ` | `, so their message is compared like any
  other field; a separate test also checks that it is the same on repeated
  runs. (Earlier the renderer showed one of the two, chosen differently from
  run to run.)
