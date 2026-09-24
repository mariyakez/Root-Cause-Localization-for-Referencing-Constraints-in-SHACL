"""
Shared helpers for the stored expected-JSON snapshots.

The fixtures listed in SNAPSHOT_FIXTURES had no content assertion of their own:
the only test that touched them checked that the command produced a summary or
reported the data as valid. Each of them now has a stored expected JSON
document under tests/expected_json/, and test_expected_json.py compares the
tool's output against it.

Comparison is order-insensitive. The explanation tree is walked over unordered
RDF node sets, so root order and sibling order vary between runs and between
serialisations of the same graph, while the set of failures and the chains
attached to them do not. canonical() sorts every node list by content, so a
snapshot pins what the explanation says without pinning an ordering the tool
does not promise.

These documents were captured from the implementation, so they detect change
rather than establish correctness. No value in them is known to be wrong. One
is easy to misread: a leaf promoted by deduplication out of a pruned branch
keeps its own refChain, which can name a different shape from the step it now
sits under. See expected_json/README.md.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = Path(__file__).resolve().parent / "expected_json"

VALID_MARKER = "Data is valid."

# Fixtures whose only previous assertion was "produces a summary or is valid".
SNAPSHOT_FIXTURES = [
    "all_test_cases/mixed_constraint_cases/tc24_mixed_direct_and_node.ttl",
    "all_test_cases/mixed_constraint_cases/tc25_mixed_multiple_focus_nodes.ttl",
    "all_test_cases/mixed_constraint_cases/tc26_mixed_direct_plus_diamond.ttl",
    "all_test_cases/multi_focus_cases/tc27_two_focus_nodes_same_shape.ttl",
    "all_test_cases/multi_focus_cases/tc28_many_focus_nodes_same_violation.ttl",
    "all_test_cases/multi_focus_cases/tc29_same_focus_multiple_shapes.ttl",
    "all_test_cases/property_path_cases/tc30_inverse_path.ttl",
    "all_test_cases/property_path_cases/tc31_sequence_path.ttl",
    "all_test_cases/property_path_cases/tc32_alternative_path.ttl",
    "all_test_cases/property_path_cases/tc33_zero_or_more_path.ttl",
    "all_test_cases/severity_cases/tc34_warning_result.ttl",
    "all_test_cases/severity_cases/tc35_info_result.ttl",
    "all_test_cases/severity_cases/tc36_mixed_severities.ttl",
    "all_test_cases/message_metadata_cases/tc37_missing_message.ttl",
    "all_test_cases/message_metadata_cases/tc38_multiple_messages.ttl",
    "all_test_cases/message_metadata_cases/tc39_language_tagged_message.ttl",
    "all_test_cases/message_metadata_cases/tc40_named_vs_blank_property_shapes.ttl",
    "all_test_cases/cycle_cases/tc46_self_recursive_shape.ttl",
    "all_test_cases/cycle_cases/tc47_two_shape_cycle.ttl",
    "all_test_cases/cycle_cases/tc48_cycle_with_leaf_failure.ttl",
    "all_test_cases/cycle_cases/tc49_cycle_without_leaf_failure.ttl",
    "all_test_cases/scale_cases/tc50_100_focus_nodes.ttl",
    "all_test_cases/scale_cases/tc51_many_values_max_count.ttl",
    "all_test_cases/scale_cases/tc52_large_diamond_dedup.ttl",
    "all_test_cases/sh_node_cases/tc53_deep_gradient_graph.ttl",
]


def snapshot_path(fixture: str) -> Path:
    return SNAPSHOT_DIR / (Path(fixture).stem + ".json")


def run_json(fixture: str) -> list:
    """Run the CLI in JSON mode and return the parsed forest.

    A conforming fixture produces no explanation tree; it is represented by an
    empty forest so that every fixture has a comparable snapshot.
    """
    result = subprocess.run(
        [sys.executable, "-m", "shacl_explainer.cli", fixture, fixture, "json"],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    if VALID_MARKER in result.stdout:
        return []
    return json.loads(result.stdout)


# rdflib mints a fresh label for every blank node on every parse, so a complex
# property path, which the renderer prints as the raw label of its path
# expression, is different text on every run. The placeholder keeps the snapshot
# stable and records the fact that the renderer does not expand such a path.
BLANK_LABEL = re.compile(r"<n[0-9a-f]{16,}>|_:[A-Za-z0-9]+")
BLANK_PLACEHOLDER = "_:blank-path-expression"


# Fixtures whose shape declares more than one sh:message. The report carries
# them all, and the explanation must show them all, sorted, on every run.
MULTIPLE_MESSAGES = {
    "tc38_multiple_messages": "Email is required | Provide one primary contact email",
    "tc39_language_tagged_message": "Name is required | Name ist erforderlich",
}


def _normalise(value):
    if isinstance(value, str):
        return BLANK_LABEL.sub(BLANK_PLACEHOLDER, value)
    if isinstance(value, list):
        return [_normalise(v) for v in value]
    return value


def canonical(nodes: list) -> list:
    """Sort a forest by content, recursively, so ordering cannot affect equality."""
    out = []
    for node in nodes:
        clean = {
            key: _normalise(value)
            for key, value in node.items()
            if key != "children"
        }
        if node.get("altChains"):
            clean["altChains"] = sorted(clean["altChains"])
        if node.get("children"):
            clean["children"] = canonical(node["children"])
        out.append(clean)
    return sorted(out, key=lambda n: json.dumps(n, sort_keys=True))


def messages(nodes: list) -> list:
    """Every message string in a forest, for the multiple-message fixtures."""
    found = []
    for node in nodes:
        if node.get("message"):
            found.append(node["message"])
        found.extend(messages(node.get("children") or []))
    return found


def dump(fixture: str, nodes: list) -> str:
    return json.dumps(canonical(nodes), indent=2, sort_keys=True) + "\n"
