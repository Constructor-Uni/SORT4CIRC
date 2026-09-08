# Interoperability

The authoritative mapping JSON and its generated CSV identify public-profile JSON paths, XML paths and RDF properties. All example resource namespaces use example.org or urn:example:.

JSON is validated against the public schema and controlled vocabularies. XML follows the versioned XSD. RDF uses the public ontology and structured nodes where collections require them. Mapping rows declare their representation status and explain omissions; an exchange should not silently imply a lossless mapping where a field is omitted.

Run python tools/gen_mapping_csv.py --check and python -m pytest tests/test_mapping.py -q. These check local mapping contracts, XML validation, ontology properties and round trips covered by the suite. They do not certify interoperability with any external partner or service.

See [Mapping contract](../spec/mappings/README.md).
