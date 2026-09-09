# DPP mapping package

Version `1.0.0` binds all 124 schema-defined exchange paths in the SORT4CIRC
DPP profile to JSON and XML and explicitly classifies RDF applicability. The
authoritative machine-readable source is
`dpp-mapping-1.0.0.json`; it is validated by
`dpp-mapping-1.0.0.schema.json`. The CSV is a generated review projection.

The package is derived from `spec/schemas/dpp-1.0.0.schema.json` and
`spec/ontology/sort4circ-1.0.1.ttl`. JSON paths use dot notation and `[]` for
repeated values. XML uses the `https://data.sort4circ.eu/dpp/1.0.0` namespace.
RDF uses `https://data.sort4circ.eu/vocabulary/` and the class/property IRIs
present in the ontology.

The audited coverage is 124/124 JSON paths and 124/124 XML paths, 111 direct
RDF properties, 7 RDF subject identifiers, 6 RDF-not-applicable structural or
interface rows and 0 unresolved semantic RDF gaps. The transport snapshot
retains 124/124 fields for reversal independently of semantic coverage.

A row is classified as `direct`, `subjectIdentifier`, `notApplicable` or
`unresolved`. Direct rows name an ontology property and identifier rows create
resources with `rdf:subject`. Not-applicable rows are structural or interface
transport fields with an explicit reason. Unresolved rows identify a semantic
ontology gap rather than hiding it. A canonical `rdf:JSON` snapshot remains on
the passport subject for lossless transport reversal, but it is never counted
as direct semantic RDF coverage.

The XML Schema is XSD 1.1 and covers every JSON object, array and scalar. Its
assertions enforce granularity identifiers, carrier closure, transformation
references, percentage/basis pairs, non-supplied observations and sorting
overrides. It is validated with `xmlschema.XMLSchema11` version 4.3.2. JSON
Schema remains the normative JSON validation path. Cross-record reference
existence, vocabulary membership and aggregate composition checks remain
service-level validation. Unknown, not-measured, not-applicable and withheld
states remain explicit and are never coerced to zero or an empty string.

Run the mapping checks with:

```text
python -m pytest tests/test_mapping.py -q
python tools/gen_mapping_csv.py --check
```

The package does not claim EN 18223 conformity. No XML serialization existed
before mapping package 1.0.0; this versioned XML representation is derived from
the repository schema and should be extended only through a versioned change.
