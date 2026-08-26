# Direct SHACL Core Constraint Cases

These files intentionally avoid `sh:node`. They test direct SHACL Core leaf
failures so the explainer can demonstrate that it renders ordinary validation
results as well as nested referencing failures.

Run any case with:

```bash
python3 -m shacl_explainer.cli all_test_cases/direct_constraint_cases/tc9_direct_min_count.ttl all_test_cases/direct_constraint_cases/tc9_direct_min_count.ttl
```
