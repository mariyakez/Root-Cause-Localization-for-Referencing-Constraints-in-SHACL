# All Test Cases

This folder groups every SHACL explainer test fixture by scenario.

| Folder | Purpose |
|---|---|
| `sh_node_cases/` | Original `sh:node` and referencing-constraint cases |
| `direct_constraint_cases/` | Direct SHACL Core violations without `sh:node` |
| `mixed_constraint_cases/` | Reports containing both direct and referenced failures |
| `multi_focus_cases/` | Multiple focus nodes and repeated violations |
| `property_path_cases/` | Inverse, sequence, alternative, and zero-or-more paths |
| `severity_cases/` | `sh:Violation`, `sh:Warning`, and `sh:Info` |
| `message_metadata_cases/` | Missing, multiple, language-tagged messages, and shape metadata |
| `external_report_cases/` | pySHACL, Jena-style, TopBraid-like, and incomplete external reports |
| `cycle_cases/` | Recursive and cyclic shape references |
| `scale_cases/` | Synthetic scale and performance-oriented cases |

Example:

```bash
python3 -m shacl_explainer.cli \
  all_test_cases/sh_node_cases/tc6_complex_org.ttl \
  all_test_cases/sh_node_cases/tc6_complex_org.ttl \
  --summary
```
