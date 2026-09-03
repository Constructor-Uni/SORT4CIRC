# DPP mapping package

Version `1.0.0` binds all 124 schema-defined exchange paths in the SORT4CIRC
DPP profile to JSON, XML and RDF. The authoritative machine-readable source is
`dpp-mapping-1.0.0.json`; it is validated by
`dpp-mapping-1.0.0.schema.json`. The CSV is a generated review projection.

The package is derived from `spec/schemas/dpp-1.0.0.schema.json` and
`spec/ontology/sort4circ-1.0.0.ttl`. JSON paths use dot notation and `[]` for
repeated values. XML uses the `https://data.sort4circ.eu/dpp/1.0.0` namespace.
RDF uses `https://data.sort4circ.eu/vocabulary/` and the class/property IRIs
present in the ontology.

A row with no direct ontology predicate names `rdf:value/rdf:JSON` as its RDF
construct. The RDF projection emits the ontology-backed triples that version
1.0.0 can express and a canonical `rdf:JSON` snapshot on the passport subject.
That snapshot makes every exchange field reversible without inventing ontology
terms. It is a transport fallback, not a claim that the missing field has a
field-specific RDF predicate. Identifier rows that create resources use
`rdf:subject`.

The XML Schema covers every JSON object, array and scalar. XSD 1.0 cannot encode
the JSON Schema's conditional rules, so JSON validation remains normative for
granularity identifiers, carrier closure, transformation references,
percentage/basis pairs and sorting overrides. Conversion always validates the
normative JSON form. Unknown, not-measured, not-applicable and withheld states
remain explicit and are never coerced to zero or an empty string.

Run the mapping checks with:

```text
python -m pytest tests/test_mapping.py -q
python tools/gen_mapping_csv.py --check
```

The package does not claim EN 18223 conformity. No XML serialization existed
before mapping package 1.0.0; this versioned XML representation is derived from
the repository schema and should be extended only through a versioned change.
