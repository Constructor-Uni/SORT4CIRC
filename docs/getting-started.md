# Getting started

Get the reference implementation running, create a passport, validate it, resolve it and
run the test suite. Every command below is copy-pasteable, and no prior reading is
required.

All data you will touch here is synthetic. See the scoping notice in the
[documentation index](index.md).

## Prerequisites

- **Python 3.11 or later** (3.11, 3.12 and 3.13 are tested). Check with `python --version`.
- **git**.
- Optional: **Docker** with the Compose plugin, if you prefer the container route.
- No database, message broker, network service, hardware reader or ledger account is
  required. Nothing in this repository contacts an external service.

## 1. Clone and install

~~~sh
git clone https://github.com/Constructor-Uni/SORT4CIRC.git
cd SORT4CIRC
python -m venv .venv
# sh/bash:      source .venv/bin/activate
# PowerShell:   .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
~~~

`.[dev]` adds the tooling used by the tests, mappings and linting: `pytest`, `httpx`,
`ruff`, `rdflib`, `pyyaml` and `xmlschema`. Runtime alone needs only `fastapi`,
`uvicorn`, `jsonschema` and `pydantic`.

Confirm the install:

~~~sh
python -m sort4circ_dpp.cli example | head -12
~~~

The package also installs a console script, so `s4c-dpp example` is equivalent to
`python -m sort4circ_dpp.cli example`.

## 2. Inspect a valid passport

~~~sh
python -m sort4circ_dpp.cli example > my-first-dpp.json
~~~

This writes a deterministic, fully valid synthetic record: a woven home textile with two
declared fibre observations. [Create your first DPP](first-dpp.md) walks through every
field and explains why each one exists.

## 3. Validate it

~~~sh
python -m sort4circ_dpp.cli validate my-first-dpp.json          # -> VALID
~~~

Now break it. Change `"fibreType": "cotton"` to `"fibreType": "bamboo"` and validate
again: the document is still structurally correct, but `bamboo` is not a token in the
`fibre-type` vocabulary, so validation fails with `INVALID S4C-PAYLOAD-VOCAB-INVALID` and
a non-zero exit code. Shape errors and meaning errors carry different reason codes on
purpose.

Check every shipped fixture, positive and deliberately negative, in one run:

~~~sh
python tools/validate_fixtures.py        # -> 14/14 fixtures behaved as declared
~~~

The negative fixtures under `examples/fixtures/` carry a test-only `$expect` member naming
the reason code they must produce. The fixture runner strips it before validating; the CLI
does not, so validating one of those files directly reports a schema error for the extra
member rather than the intended failure. Validation is covered in detail in
[Validation](validation.md).

## 4. Run the end-to-end worked example

~~~sh
python examples/worked_example.py
~~~

This runs the whole Tier 1 and Tier 2 loop in-process, with no network: it validates a
synthetic passport, creates it through the API, commissions a data carrier, resolves the
carrier identifier back to the passport, appends a lifecycle event and a material
observation, then drains the local integrity worker and verifies the resulting digest.
Read [`examples/worked_example.py`](../examples/worked_example.py) alongside the output —
it is short and is the fastest way to see the intended request sequence.

## 5. Start the HTTP service

### Local Python route

~~~sh
# sh/bash
DPP_DEMO_AUTH=1 python -m uvicorn sort4circ_dpp.api:app --host 127.0.0.1 --port 8000

# PowerShell
$env:DPP_DEMO_AUTH = "1"; python -m uvicorn sort4circ_dpp.api:app --host 127.0.0.1 --port 8000
~~~

`DPP_DEMO_AUTH=1` opts into the local header-based demo identity. Without it the service
starts fail-closed with `PublicOnlyAuth`: reads return the public view and any request
carrying an `X-DPP-Role` header is rejected. That is the correct default; set the
variable only for a loopback-bound instance holding synthetic records, and read
[Security model](security.md) before you expose anything.

### Docker route

~~~sh
# sh/bash
DPP_DEMO_AUTH=1 docker compose -f docker/compose.example.yml up --build

# PowerShell
$env:DPP_DEMO_AUTH = "1"; docker compose -f docker/compose.example.yml up --build
~~~

The compose file binds to `127.0.0.1:8000` only, runs read-only with all capabilities
dropped and `no-new-privileges`, and defaults `DPP_DEMO_AUTH` to `0`. Omit the variable
entirely to run the fail-closed public-read configuration.

## 6. Check the service is running

~~~sh
curl -s http://127.0.0.1:8000/health
# {"status":"ok","schemaVersion":"1.0.0"}
~~~

Interactive API documentation generated from the live application is at
<http://127.0.0.1:8000/docs>. The checked-in contract is
[`spec/openapi/dpp-api-v1.json`](../spec/openapi/dpp-api-v1.json).

## 7. Create and retrieve a DPP over HTTP

With `DPP_DEMO_AUTH=1` running:

~~~sh
curl -s -X POST http://127.0.0.1:8000/v1/dpps \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  --data @my-first-dpp.json

curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001" \
  -H "X-DPP-Role: brand"

# the same record as an anonymous public caller: fewer fields, no source attribution
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001"
~~~

Compare the two responses. The public view keeps the composition but withholds who
observed it. That difference is the access model doing its job; see
[Security model](security.md).

## 8. Bind a carrier and resolve it

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/carriers" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  -d '{"carrierType":"qrCode","encodingScheme":"proprietary",
       "encodedIdentifier":"urn:example:carrier:000001",
       "resolverUri":"https://example.org/dpp/000001",
       "boundBy":"urn:example:org:manufacturer-a"}'

# resolve the carrier identifier back to the passport (the value is URL-encoded)
curl -s "http://127.0.0.1:8000/v1/identifiers/urn%3Aexample%3Acarrier%3A000001/dpp" \
  -H "X-DPP-Role: sortingOperator"
~~~

See [Identifiers](identifiers.md) for why the carrier identifier and the passport
identifier are different things, and [Carrier binding](carrier-binding.md) for what
belongs on the physical tag.

## 9. Run the test suite

~~~sh
python -m pytest -q                  # full suite
python tools/conformance_report.py   # category-level pass/fail summary
~~~

The suite covers schema and vocabulary rules, canonical digest vectors, mock integrity
outcomes, identifier classification, API access and idempotency, JSON/XML/RDF mappings and
release boundaries. A passing run is evidence of exactly those tests against this code —
it is not industrial validation, a durability guarantee or a security assurance. See
[Conformance](conformance.md).

Other useful commands, all also available as `make` targets:

~~~sh
python -m ruff check src tests tools examples   # lint            (make lint)
python tools/validate_fixtures.py               # fixtures        (make fixtures)
python tools/gen_mapping_csv.py --check         # mapping CSV     (make mapping)
python tools/gen_openapi.py --check             # OpenAPI drift   (make openapi)
python tools/verify_public_release.py --files-only   # file policy (make verify)
~~~

## Where to go next

- Field-by-field: [Create your first DPP](first-dpp.md)
- The record's shape and rules: [Data model](concepts.md)
- Why an observation without a method is not usable: [Provenance](provenance.md)
- Replacing the memory store, identity provider and ledger adapter:
  [Customisation](customisation.md)

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `401`/`403` with `S4C-AUTH-INVALID-TOKEN` on a request carrying `X-DPP-Role` | The service is running fail-closed. Restart it with `DPP_DEMO_AUTH=1`. |
| A write returns `S4C-AUTHZ-OPERATION-FORBIDDEN` | The role you asserted does not hold that scope. Check the role table in [Security model](security.md). |
| `S4C-PAYLOAD-VOCAB-INVALID` | A coded value is not in the vocabulary version. See [Vocabularies](vocabularies.md). |
| `S4C-STATE-VERSION-CONFLICT` on `PATCH` | `If-Match` is missing or stale. Re-read the record and retry with the current `ETag`. |
| A `404` on `/v1/identifiers/.../dpp` | The carrier identifier must be URL-encoded, and the carrier must be commissioned first. |
| Records vanished after a restart | Expected. The reference store is in-process memory. |
