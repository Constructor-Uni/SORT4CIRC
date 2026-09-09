# Validation

"Is this DPP structurally valid?" — how to answer that question in one command, what the
three validation stages check, and what a passing result does and does not mean.

## The one command

~~~sh
python -m sort4circ_dpp.cli validate path/to/my-dpp.json
~~~

Output is `VALID` with exit code 0, or `INVALID <reason-code>` with exit code 1. The
console script `s4c-dpp validate path/to/my-dpp.json` is equivalent.

## Where the specification assets are

| Asset | Path | Validates |
| --- | --- | --- |
| JSON Schema (2020-12) | [`spec/schemas/dpp-1.0.0.schema.json`](../spec/schemas/dpp-1.0.0.schema.json) | Structure, types, required members, conditional requirements |
| Controlled vocabularies | 18 files under `spec/vocabularies/`, e.g. [`fibre-type.json`](../spec/vocabularies/fibre-type.json) | Coded values |
| XSD | [`spec/mappings/dpp-1.0.0.xsd`](../spec/mappings/dpp-1.0.0.xsd) | The XML representation |
| Mapping contract | [`spec/mappings/dpp-mapping-1.0.0.json`](../spec/mappings/dpp-mapping-1.0.0.json) | JSON ↔ XML ↔ RDF field correspondence |
| Ontology | [`spec/ontology/sort4circ-1.0.0.ttl`](../spec/ontology/sort4circ-1.0.0.ttl) | RDF classes and properties |
| OpenAPI | [`spec/openapi/dpp-api-v1.json`](../spec/openapi/dpp-api-v1.json) | The exchange contract |
| Access matrix | [`spec/access-matrix.json`](../spec/access-matrix.json) | Roles, scopes and views |
| Reason codes | [`spec/reason-codes.json`](../spec/reason-codes.json) | Error identity and HTTP status |

The JSON Schema is self-contained: you can point any Draft 2020-12 validator, in any
language, at it. It will catch structure but not vocabulary membership or the composition
rule, which is why the profile defines three stages.

## The three stages

`validate_payload()` in [`validation.py`](../src/sort4circ_dpp/validation.py) runs them in
this order, and the order matters: a vocabulary check on a malformed document reports the
wrong failure.

### 1. Structure — JSON Schema

Types, required members, `additionalProperties: false` everywhere, URI and semver patterns,
RFC 3339 timestamps with a mandatory offset, and the conditional rules:

- `identity.granularity: item` requires `itemId` (likewise `batch`/`batchId`,
  `model`/`modelId`);
- `percentage` requires `percentageBasis`;
- `valueStatus` other than `supplied` **forbids** `percentage`;
- a carrier whose `bindingStatus` is not `commissioned` requires `closedAt`;
- a `transformation` event requires `inputRefs` and `outputRefs`;
- an `overridden` sorting decision requires `overrideReason`;
- `confidence` requires both `value` and `scale`.

Failure: **`S4C-PAYLOAD-SCHEMA-INVALID`**, with every failing path listed in `fields`.

### 2. Meaning — controlled vocabularies

Every coded value is checked against its published vocabulary version. Unknown tokens are
rejected, never coerced to a default.

Failure: **`S4C-PAYLOAD-VOCAB-INVALID`**, naming the path, the vocabulary and its version.

### 3. Cross-field rules

Currently the composition rule: within an observation set — same `sourceOrganisationId`,
`sourceSystemId`, `method` and `observedAt` — supplied `mass` fractions may not exceed 100
plus a 0.5 percentage-point tolerance. Sums below 100 are accepted; the rule never applies
across sets. See [Data model](concepts.md#observation-sets-and-the-composition-rule).

Failure: **`S4C-PAYLOAD-SCHEMA-INVALID`** on `materialObservations`.

## Worked examples

### A document that should pass

[`examples/fixtures/valid-minimum.json`](../examples/fixtures/valid-minimum.json) — the
smallest complete record. Also valid:
[`valid-annex-g-garment.json`](../examples/fixtures/valid-annex-g-garment.json)
(the Annex G worked example),
[`valid-two-technologies-disagree.json`](../examples/fixtures/valid-two-technologies-disagree.json)
(two conflicting observation sets, correctly retained) and
[`valid-uncharacterised-garment.json`](../examples/fixtures/valid-uncharacterised-garment.json)
(nothing measured, honestly stated).

~~~sh
python -m sort4circ_dpp.cli validate examples/fixtures/valid-minimum.json    # -> VALID
~~~

### Documents that should fail

Ten negative fixtures, each isolating one rule. Every one carries a test-only `$expect`
member naming the reason code it must produce, so a negative fixture that stops failing is
caught rather than silently passing.

| Fixture | Rule it violates | Expected code |
| --- | --- | --- |
| `invalid-article-class-token.json` | Article class outside the vocabulary | `S4C-PAYLOAD-VOCAB-INVALID` |
| `invalid-fibre-token.json` | Fibre type outside the vocabulary | `S4C-PAYLOAD-VOCAB-INVALID` |
| `invalid-composition-above-one-hundred.json` | Mass fractions exceed 100 within one set | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-confidence-without-scale.json` | Confidence value with no scale | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-item-without-item-id.json` | `granularity: item` with no `itemId` | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-no-material-observation.json` | Empty `materialObservations` | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-observation-without-method.json` | Observation with no `method` | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-percentage-without-basis.json` | Percentage with no basis | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-timestamp-without-offset.json` | Timestamp with no UTC offset | `S4C-PAYLOAD-SCHEMA-INVALID` |
| `invalid-unknown-carrying-a-value.json` | `valueStatus: unknown` carrying a percentage | `S4C-PAYLOAD-SCHEMA-INVALID` |

Because `$expect` is not a schema member, validating one of these files **directly** with
the CLI reports a schema error for the extra member rather than the intended failure. Use
the fixture runner, which strips it:

~~~sh
python tools/validate_fixtures.py
# ok   invalid-fibre-token.json: S4C-PAYLOAD-VOCAB-INVALID
# ...
# 14/14 fixtures behaved as declared
~~~

## Validating from Python

~~~python
import json
from sort4circ_dpp.validation import validate_payload
from sort4circ_dpp.reasons import DppError

document = json.loads(open("my-dpp.json", encoding="utf-8").read())
try:
    validate_payload(document)
    print("valid")
except DppError as exc:
    print(exc.code, exc.detail, exc.fields)
~~~

`validate_schema()` runs stage 1 alone; `sort4circ_dpp.vocab.validate_record()` runs stage
2 alone; `check_composition()` runs stage 3 alone. Splitting them is useful when you want
to accept a structurally valid record into a quarantine queue while reporting a vocabulary
gap.

## Validating over HTTP

The API validates on write. A rejected payload comes back as `application/problem+json`
with the reason code, the failing field paths and a correlation identifier:

~~~json
{
  "type": "https://data.sort4circ.eu/problems/s4c-payload-vocab-invalid",
  "title": "Coded value outside the declared vocabulary version.",
  "status": 422,
  "detail": "'bamboo' is not in vocabulary fibre-type version 1.0.0",
  "instance": "/v1/dpps",
  "reasonCode": "S4C-PAYLOAD-VOCAB-INVALID",
  "safeAction": "rejectAtClient",
  "correlationId": "…",
  "errors": [{ "path": "materialObservations[0].fibreType" }],
  "vocabulary": "fibre-type",
  "vocabularyVersion": "1.0.0"
}
~~~

See [API guide](api.md#error-responses).

## Validating other representations

~~~sh
python -m pytest tests/test_mapping.py -q      # XML against the XSD, RDF round trips
python tools/gen_mapping_csv.py --check        # generated CSV matches the mapping JSON
python tools/gen_openapi.py --check            # checked-in OpenAPI matches the application
~~~

XML is validated against [`dpp-1.0.0.xsd`](../spec/mappings/dpp-1.0.0.xsd) with
`xmlschema`; RDF round trips use `rdflib` against the ontology. Both are development
dependencies (`pip install -e ".[dev]"`). See
[Representations and semantics](interoperability.md).

## Testing your own implementation's validation

If you are building a non-Python implementation, the shipped fixtures are your test
corpus. A conforming implementation must accept all four positive fixtures and reject all
ten negative ones with the declared reason code. That is the first row of
[Conformance](conformance.md).

~~~sh
python -m pytest tests/test_validation.py tests/test_vocab.py tests/test_synthetic.py -q
~~~

## What validity does not establish

A valid record is well-formed and interoperable. It is **not** evidence that:

- the composition is factually correct;
- the observation actually took place;
- the responsible operator is who they claim to be;
- the record satisfies any legal or regulatory obligation.

Validation checks form and vocabulary. Attribution ([Provenance](provenance.md)) tells you
whose claim it is; integrity evidence ([Integrity](integrity.md)) tells you it has not
changed since a given version. Truth is not a property any of the three can supply.
