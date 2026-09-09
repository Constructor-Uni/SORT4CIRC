# Conformance

"How do I check whether my implementation conforms to this profile?"

Conformance here means **conformance with the SORT4CIRC DPP implementation profile
versioned in this repository**. It is not an EU specification, a CEN/CENELEC standard, an
external certification, or evidence of legal or regulatory conformity. Nobody issues a
certificate against it. See [Regulatory context](regulatory-context.md).

## Two kinds of check

Be clear about which you are dealing with, because the second kind cannot be automated
away.

| | |
| --- | --- |
| **Machine-testable** | Schema validity, vocabulary validity, identifier classification, API contract behaviour, negative cases, provenance requirements, canonicalisation and digest agreement, projection and access behaviour, representation round trips |
| **Organisational or deployment decisions** | Identity provider correctness, durability, transport security, retention, rate limiting, physical-line behaviour, industrial validation, and whether any legal obligation is satisfied |

The suite in this repository covers the first column against **this** implementation. For
your own implementation, the specification assets and fixtures are the contract; the tests
here are a worked example of how to exercise it.

## Running the suite against the reference implementation

~~~sh
python -m pytest -q                     # everything
python tools/conformance_report.py      # category pass/fail summary
~~~

`conformance_report.py` runs the categories below and emits an allowlisted summary — fixed
identifiers, categories, version fields and result values (`pass`, `fail`,
`not-applicable`). It deliberately does **not** export raw test output, environment data or
free text, so a summary you publish cannot leak paths, identities or private data. Exit
status is non-zero if any category fails.

| Category | Tests |
| --- | --- |
| `schema` | `test_validation.py`, `test_synthetic.py` |
| `canonical` | `test_canonical.py` |
| `integrity` | `test_ledger_contract.py`, `test_evidence.py` |
| `identifier` | `test_readzone.py`, `test_store.py` |
| `api` | `test_api_contract.py`, `test_access.py` |
| `mapping` | `test_mapping.py` |
| `publication` | `test_public_release.py`, `test_public_summary.py`, `test_licensing.py` |

## Checking your own implementation

The specification assets are language-neutral. Below, each requirement area is paired with
the asset that defines it, the command that exercises it here, and what you must do in your
own stack.

### 1. JSON Schema validity — Tier 1

*Asset:* [`spec/schemas/dpp-1.0.0.schema.json`](../spec/schemas/dpp-1.0.0.schema.json)
(JSON Schema 2020-12, usable from any language).

~~~sh
python -m sort4circ_dpp.cli validate your-record.json
python tools/validate_fixtures.py
python -m pytest tests/test_validation.py -q
~~~

*Your implementation must:* accept all four positive fixtures and reject all ten negative
fixtures with the declared reason code. Note that `$expect` is a test-only member; strip it
before validating.

### 2. Controlled vocabulary validity — Tier 1

*Asset:* the 18 files under `spec/vocabularies/`, for example
[`fibre-type.json`](../spec/vocabularies/fibre-type.json).

~~~sh
python -m pytest tests/test_vocab.py -q
~~~

*Your implementation must:* reject an unknown token with a distinct code
(`S4C-PAYLOAD-VOCAB-INVALID`) rather than the schema code, and **never** coerce an unknown
value to a default. Vocabulary checking must be separate from structural checking; the
codes must differ, because clients branch on them.

### 3. Provenance requirements — Tier 1

*Asset:* the schema's `materialObservation` definition, plus the `method` and `value-status`
vocabularies.

~~~sh
python -m pytest tests/test_validation.py tests/test_mapping.py -q
~~~

*Your implementation must:* require `observationId`, `fibreType`, `valueStatus`, `method`,
`sourceOrganisationId` and `observedAt` on every observation; forbid `percentage` when
`valueStatus` is not `supplied`; require `percentageBasis` whenever `percentage` is
present; apply the composition tolerance **within** an observation set and never across
sets; and preserve absence states (`notMeasured`, `unknown`, `notApplicable`, `withheld`)
without converting them to zero, null or an omission.

### 4. Identifier behaviour — Tier 1

*Assets:* [`spec/reason-codes.json`](../spec/reason-codes.json), the schema's identity and
carrier rules.

~~~sh
python -m pytest tests/test_readzone.py tests/test_store.py -q
~~~

*Your implementation must:* distinguish unknown, malformed and ambiguous reads rather than
returning a single generic failure; refuse to bind an encoded identifier already bound to
another passport (`S4C-IDENT-DUPLICATE-BINDING`); never reassign a retired identifier to a
different product; require `closedAt` on a non-`commissioned` binding; and commission
atomically, so a failure never leaves two commissioned bindings.

### 5. API contract behaviour — Tier 1–2

*Asset:* [`spec/openapi/dpp-api-v1.json`](../spec/openapi/dpp-api-v1.json).

~~~sh
python -m pytest tests/test_api_contract.py -q
python tools/gen_openapi.py --check      # the contract has not drifted from the app
~~~

*Your implementation must:* implement the documented routes with the documented status
codes; return `application/problem+json` (RFC 9457) with a `reasonCode`; support
`If-Match`/`412` on `PATCH` and `If-None-Match`/`304` on `GET`; support `Idempotency-Key`
scoped to caller, organisation, role, operation and resource, returning
`S4C-STATE-IDEMPOTENCY-CONFLICT` on the same key with different content; paginate by cursor
with deterministic ordering and a capped `limit`; and echo `X-Correlation-Id`.

### 6. Negative cases — all tiers

The ten negative fixtures under `examples/fixtures/` (see the
[fixture README](../examples/fixtures/README.md)) are the minimum
corpus. Rejection is the behaviour under test: an implementation that accepts an invalid
record has a silent gap, and a fixture that stops failing is a regression. Both are why the
negative fixtures assert the **expected reason code** and not merely "not valid".

Also test negatively at the API: a wrong role, a missing `If-Match`, a stale `ETag`, a
replayed idempotency key with different content, an append-only member in a `PATCH`, an
unknown view, an unresolvable identifier.

### 7. Access-control behaviour — Tier 1–2

*Asset:* [`spec/access-matrix.json`](../spec/access-matrix.json).

~~~sh
python -m pytest tests/test_access.py -q
~~~

*Your implementation must:* default-deny; treat a held scope as necessary and never
sufficient; project every read through a view; narrow a too-wide view request rather than
refusing it; return an explicit withheld marker instead of dropping a field the caller may
know exists but not read; scope the `partner` view's events by the caller's organisation;
and refuse writes to append-only members regardless of role.

The **model** is testable. Your **identity provider** is not testable from here — that is
your own test suite, and it must cover expired, malformed, replayed, wrong-audience and
absent credentials. See [Security model](security.md).

### 8. Canonicalisation and digest verification — Tier 3

*Asset:* [`canonical.py`](../src/sort4circ_dpp/canonical.py) and the fixed vectors in
`tests/test_canonical.py`.

~~~sh
python -m sort4circ_dpp.cli digest your-record.json
python -m sort4circ_dpp.cli digest your-record.json --show-projection
python -m pytest tests/test_canonical.py -q
~~~

*Your implementation must:* project exactly the documented field subset; canonicalise per
RFC 8785 (keys sorted by UTF-16 code unit, ECMAScript number and string serialisation);
produce SHA-256 lower-case hex; treat array order as significant; exclude access, view and
integrity members; and reproduce the fixed vectors byte for byte.

When two implementations disagree, compare `--show-projection` output before comparing
hashes — the divergence is almost always in the projection or in number formatting, not in
the hash.

### 9. Integrity backend contract — Tier 3, optional

*Asset:* [`ledger/base.py`](../src/sort4circ_dpp/ledger/base.py).

~~~sh
python -m pytest tests/test_ledger_contract.py tests/test_evidence.py -q
~~~

The contract tests run against **any** adapter. If you implement one, run them against it.

*Your implementation must:* make `submit` idempotent per `evidence_id`; return a receipt
with a transaction reference, a network identifier and a state; distinguish `match`,
`mismatch`, `unanchored` and `unverifiable`; enforce the evidence state machine, refusing
impossible transitions; and keep passport content out of the envelope.

### 10. Representation round trips — Tier 2

*Assets:* [XSD](../spec/schemas/dpp-1.0.0.xsd),
[ontology](../spec/ontology/sort4circ-1.0.1.ttl),
[mapping](../spec/mappings/dpp-mapping-1.0.0.json).

~~~sh
python -m pytest tests/test_mapping.py -q
python tools/gen_mapping_csv.py --check
~~~

*Your implementation must,* if it offers XML or RDF: round-trip without information loss;
have exactly one mapping row per schema-defined exchange path; resolve every RDF binding to
a declared ontology property or a declared construct; and preserve absence states across
every representation.

### 11. Version and migration compatibility

~~~sh
python -m pytest tests/test_store.py -q
~~~

*Your implementation must:* advance `recordVersion` on every committed change; retain
earlier versions for as long as any integrity evidence references them; supersede rather
than delete; and version schema, vocabularies, mappings and ontology together. See
[Versioning and migration](versioning-and-migration.md).

### 12. Repeatability of the checks themselves

~~~sh
python -m ruff check src tests tools examples
python verify_files.py
python tools/verify_public_release.py --files-only
~~~

The last two are specific to this repository's publication process rather than to the DPP
profile. See [Release verification](public-release.md).

## What a passing run means

It means **the tests that were executed passed against the code that executed them**. It is
evidence, and it is bounded evidence. A passing run is not:

- physical-line or industrial validation;
- proof of durability, availability or recoverability;
- a performance guarantee;
- comprehensive security assurance;
- legal or regulatory conformity;
- a certification of any kind.

Nothing in this repository issues, and nothing external recognises, a conformance
certificate against this profile. Claim what you tested.

## Conformance by tier

| Tier | Checks 1–12 in scope |
| --- | --- |
| **1 — Core Passport** | 1, 2, 3, 4, 5 (read/resolve), 6, 7 |
| **2 — Operational Passport** | Tier 1, plus 5 (write, idempotency, concurrency), 10, and the full access behaviour in 7 |
| **3 — Assured Passport** | Tier 2, plus 8, 9, 11, and your own performance, recovery, security and migration testing |

Declaring the tier you implement is more useful to a counterparty than a bare claim of
"conformance", because it says which behaviours they may rely on.

## Related pages

- [Traceability](traceability.md) — requirement → specification asset → implementation → test
- [Validation](validation.md) — the fixture corpus in detail
- [Testing methodology](testing-methodology.md) — measuring your own deployment honestly
- [Regulatory context](regulatory-context.md) — the limits of the word "conformance" here
