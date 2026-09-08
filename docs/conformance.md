# Public-profile conformance

Normative means normative only for this repository's versioned public profile. The suite tests schema and vocabulary constraints, synthetic vectors, mock backend behaviour, identifier classification, API access and idempotency, JSON/XML/RDF mappings, summary filtering and release boundaries.

Run python -m pytest -q for the full suite. Run python tools/conformance_report.py for a strict summary of its selected categories. Result values are pass, fail or not-applicable. The exporter fixes identifiers, categories, version fields, synthetic dataset label and limitations; raw output, arbitrary text and environment fields are excluded.

A passing run is evidence of the tests actually executed against this code. It is not physical-line validation, industrial validation, proof of durability, a performance guarantee, comprehensive security assurance or legal/regulatory conformity.

Human publication review, Git history remediation and an approved private security reporting channel remain separate decisions. The complete owner-approved component licence coverage is recorded in [LICENSING.md](../LICENSING.md).
