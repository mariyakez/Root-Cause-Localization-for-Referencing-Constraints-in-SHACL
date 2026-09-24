# Repair Hint Cases

These cases cover the repair hints that the numbered fixtures do not reach.
They are named rather than numbered, are not part of the TC1–TC53 corpus, and
are asserted by `test_repair_hints_name_the_constraint_parameter` and
`test_repair_hint_parameter_from_an_anonymous_property_shape` in
`tests/test_cli_pipeline.py`.

`min_count_above_one.ttl` declares `sh:minCount 3` against a node that has one
value. "Add at least one value" is true only of a minimum of one, so the hint
has to say how many values are missing. This is also the only case in which the
count of existing values is read from the data graph; a minimum of one and any
maximum are stated from the shape alone, which keeps the cost off the large
graphs of Chapter 5.

`node_level_class.ttl` puts `sh:class` on a node shape instead of a property
shape. With no `sh:path` the constraint is about the focus node, so this is the
one `sh:class` hint that names it. On a property shape the constraint is about
each value reached along the path, as in `tc12_direct_class.ttl`, and naming
the focus node there would point the reader at the wrong node.

`anonymous_property_shape.ttl` and `anonymous_property_shape.report.ttl` are
read together with `--report`. Two node shapes constrain the same two paths,
and the report identifies the failing shape the way Apache Jena and TopBraid do
for an anonymous property shape: a blank node matching nothing in the shapes
graph. The path is then the only link back to the constraint. On `ex:agreed`
every property shape on the path requires the same datatype, so the hint may
name it; on `ex:disputed` they disagree, and the hint must fall back to its
unparameterised wording rather than guess which shape produced the result.
