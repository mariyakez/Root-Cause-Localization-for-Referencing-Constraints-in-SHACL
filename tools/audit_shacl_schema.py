#!/usr/bin/env python3
"""Check a SHACL schema against the data it is meant to validate.

Reports three kinds of defect that make a shape fail, or pass, by construction
rather than because of the data:

  unused-path      a constraint path that occurs on no triple of the data, so
                   every targeted node fails a minCount on it;
  node-not-shape   an sh:node value that is not a shape in the schema, so it
                   carries no constraints and every value satisfies it;
  result-term      a term of SHACL's validation-result vocabulary used as a
                   constraint parameter, which validators ignore.

Requires: nothing beyond requirements.txt. Runs on any data and schema
pair; Chapter 5 ran it on the LUBM graphs, which are not in this repository.

Usage:
    python3 tools/audit_shacl_schema.py DATA.ttl SCHEMA.ttl [SCHEMA.ttl ...]
"""
import sys
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, URIRef
from rdflib.namespace import SH

# Terms that may appear as predicates inside a shapes graph.
CONSTRAINT_TERMS = {
    "targetClass", "targetNode", "targetSubjectsOf", "targetObjectsOf", "target",
    "path", "property", "node", "name", "description", "message", "severity",
    "deactivated", "order", "group", "class", "datatype", "nodeKind",
    "minCount", "maxCount", "minExclusive", "minInclusive", "maxExclusive",
    "maxInclusive", "minLength", "maxLength", "pattern", "flags", "languageIn",
    "uniqueLang", "equals", "disjoint", "lessThan", "lessThanOrEquals", "not",
    "and", "or", "xone", "qualifiedValueShape", "qualifiedMinCount",
    "qualifiedMaxCount", "qualifiedValueShapesDisjoint", "closed",
    "ignoredProperties", "hasValue", "in", "sparql", "select", "ask",
    "prefixes", "declare", "prefix", "namespace", "rule", "condition",
    "construct", "subject", "predicate", "object", "expression", "defaultValue",
    "nodeValidator", "propertyValidator", "validator", "parameter", "optional",
    "labelTemplate", "entailment", "shapesGraph", "suggestedShapesGraph",
    "alternativePath", "inversePath", "zeroOrMorePath", "oneOrMorePath",
    "zeroOrOnePath", "this", "filterShape", "nodes", "values", "jsLibrary",
    "jsLibraryURL", "jsFunctionName", "js",
}
# Terms that belong to a validation report, not to a shape.
RESULT_TERMS = {
    "value", "focusNode", "resultPath", "resultMessage", "resultSeverity",
    "sourceShape", "sourceConstraintComponent", "sourceConstraint", "detail",
    "conforms", "result", "ValidationReport", "ValidationResult",
}
SHAPE_TYPES = {SH.NodeShape, SH.PropertyShape}


def is_shape(node, schema):
    return (any((node, RDF.type, t) in schema for t in SHAPE_TYPES)
            or any((node, p, None) in schema for p in (SH.property, SH.path, SH.node)))


def describe(node, schema):
    """A readable name for a shape, falling back to the shape that owns it."""
    if isinstance(node, URIRef):
        return node.n3(schema.namespace_manager)
    for owner in schema.subjects(SH.property, node):
        return f"property shape of {describe(owner, schema)}"
    return "anonymous shape"


def audit(schema_path, data):
    schema = Graph().parse(schema_path)
    findings = []

    for prop_shape, path in schema.subject_objects(SH.path):
        if isinstance(path, URIRef) and not any(data.triples((None, path, None))):
            owner = describe(prop_shape, schema)
            findings.append(("unused-path", path.n3(schema.namespace_manager), owner))

    for shape, referenced in schema.subject_objects(SH.node):
        if not is_shape(referenced, schema):
            findings.append(("node-not-shape", referenced.n3(schema.namespace_manager),
                             describe(shape, schema)))

    for _, predicate, obj in schema:
        if predicate.startswith(str(SH)):
            term = predicate[len(str(SH)):]
            if term in RESULT_TERMS:
                findings.append(("result-term", predicate.n3(schema.namespace_manager), ""))
            elif term not in CONSTRAINT_TERMS:
                findings.append(("unknown-term", predicate.n3(schema.namespace_manager), ""))
    return findings


def main():
    data_path, *schema_paths = sys.argv[1:]
    data = Graph().parse(data_path)
    print(f"data: {Path(data_path).name} ({len(data)} triples)\n")
    for schema_path in schema_paths:
        findings = audit(schema_path, data)
        print(f"== {Path(schema_path).name}: {len(findings)} finding(s)")
        seen = set()
        for kind, term, where in sorted(findings):
            if (kind, term, where) in seen:
                continue
            seen.add((kind, term, where))
            count = sum(1 for f in findings if f == (kind, term, where))
            print(f"   {kind:15} {term:35} {where}" + (f"  (x{count})" if count > 1 else ""))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
