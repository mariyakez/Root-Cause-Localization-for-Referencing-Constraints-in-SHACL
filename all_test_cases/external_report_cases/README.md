# External Report Compatibility Cases

These cases contain external validation reports that can be passed with
`--report`. They exercise pySHACL-style reports with `sh:detail`, Jena-style
node-level reports without `sh:detail`, two synthetic property-level report
structures, and reports with missing metadata.

TC43 and TC44 are hand-written and do not reproduce any validator checked so
far. For a property-level `sh:node` result, both Apache Jena 6.2.0 and TopBraid
SHACL 1.5.0 name the property shape in `sh:sourceShape`, usually as a blank
node, rather than the enclosing node shape (TC43) or the referenced shape
(TC44). Real reports of that kind are committed next to the fixture they were
produced from, in `sh_node_cases/jena_real_tc7_property_no_detail.ttl` and
`sh_node_cases/topbraid_real_tc7_property_no_detail.ttl`.

`shared_path/` holds four data-and-shapes files in which two property shapes
declare `sh:node` on the same path, each with the real reports that Apache Jena
6.2.0 (`*.jena.ttl`) and TopBraid SHACL 1.5.0 (`*.topbraid.ttl`) produce for
it. They check that a result naming an anonymous property shape is resolved to
the property shape that produced it, by targeting, by evidence, and by declared
metadata or pairing; each file's header says which step it exercises. They are
not numbered fixtures and are asserted by
`test_shared_path_reports_resolve_to_the_applicable_property_shape`.

`fallback_edges/` holds the inputs for two cases in which re-validation cannot
break a reported `sh:node` result down: data in which the value now conforms,
paired with the real Jena report for TC7, and a report whose `sh:value` was
removed by hand, paired with data in which the path leads to no value. In both,
the validator's own result must be kept and marked with a note.

`fallback_edges/targeted_referenced_shape.ttl` has a referenced shape with a
target of its own, with the real Jena and TopBraid reports for it. Re-validation
must check the one value a result names, not every node the shape targets.

`fallback_edges/nested_property_node.ttl` has a referenced shape that itself
declares a property-level `sh:node`, with the real Jena and TopBraid reports for
it. Re-validation must carry the nested shape along, or the failure below it is
lost.
