# API guide

The exchange interface, organised by what you are trying to do. The machine-readable
contract is [`spec/openapi/dpp-api-v1.json`](../spec/openapi/dpp-api-v1.json); the live
service serves interactive documentation at `/docs`.

Route prefix is `/v1`, an independently versioned exchange-route major. The normative
DPP implementation profile version is `1.0.0`, reported by `/health` and carried in every payload as
`schemaVersion`. That is not the version of this repository — see
[Versioning and migration](versioning-and-migration.md#two-version-numbers).

Examples below assume the local service from [Getting started](getting-started.md), started
with `DPP_DEMO_AUTH=1`. The `X-DPP-Role` and `X-DPP-Organisation` headers are **fictional
identity assertions for local demonstration, not credentials**. In the fail-closed default
configuration those headers are rejected outright. See [Security model](security.md).

## The endpoints

| Method | Path | Scope required | Purpose |
| --- | --- | --- | --- |
| `POST` | `/v1/dpps` | `dpp.write` | Create a passport |
| `GET` | `/v1/dpps` | `dpp.read` | List passports, cursor-paginated |
| `GET` | `/v1/dpps/{dppId}` | `dpp.read` | Retrieve one passport in a view |
| `PATCH` | `/v1/dpps/{dppId}` | `dpp.write` | Update non-append-only members |
| `POST` | `/v1/dpps/{dppId}/carriers` | `dpp.write` | Commission a data-carrier binding |
| `POST` | `/v1/dpps/{dppId}/observations` | `observation.write` | Append a material observation |
| `POST` | `/v1/dpps/{dppId}/events` | `dpp.event` | Append a lifecycle event |
| `GET` | `/v1/dpps/{dppId}/sorting-view` | `sorting.read` | The operational projection for a sorting decision |
| `GET` | `/v1/identifiers/{encodedIdentifier}/dpp` | `dpp.resolve` | Resolve a carrier read to a passport |
| `GET` | `/v1/dpps/{dppId}/integrity` | `integrity.read` | List integrity evidence entries |
| `POST` | `/v1/dpps/{dppId}/integrity/verify` | `integrity.verify` | Recompute and compare a digest |
| `GET` | `/health` | — | Liveness and served schema version |

That is the whole public surface. There is deliberately **no** administrative endpoint in
the exchange contract: draining the reference implementation's integrity worker is a
Python operation (`app.state.worker.drain()`), not an HTTP route, because it is
reference-implementation plumbing and not a thing any interoperating party should depend
on. If your deployment needs operational endpoints, add them outside `/v1` and treat them
as your own contract, not part of this profile.

The two layers, kept deliberately apart:

| Layer | What it is | Where |
| --- | --- | --- |
| **Public interoperability API** | The twelve operations above. Normative within the DPP implementation profile; what another organisation codes against. | [`spec/openapi/dpp-api-v1.json`](../spec/openapi/dpp-api-v1.json) |
| **Implementation administration** | Draining the evidence worker, seeding, inspection. Not normative, not interoperable, not versioned by the profile. | Python API of the reference service |

Keeping administration out of the published contract is a boundary decision about this
repository's reference implementation, not a change to the DPP implementation profile. The profile
version is unaffected, and `tests/test_public_release.py` asserts that no `/internal` or
`/admin` path can enter the public contract.

`/health` returns liveness and the served schema version only. It exposes no build,
environment, dependency or topology information.

## Flow 1 — Create and retrieve

~~~sh
curl -s -X POST http://127.0.0.1:8000/v1/dpps \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  -H "Idempotency-Key: create-000001" \
  --data @my-first-dpp.json
~~~

`201 Created`, with:

- `Location: /v1/dpps/urn:example:dpp:000001`
- `ETag: "dpp-000001-v1"` — keep it; you need it for `If-Match`
- `Cache-Control: no-store`
- `X-Correlation-Id` — echoed from your request or generated

The payload is validated on write. A failure returns `application/problem+json`; see
[Error responses](#error-responses).

Retrieve it:

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001" -H "X-DPP-Role: brand"
~~~

Supply `If-None-Match` with a known `ETag` to get `304 Not Modified` instead of a body.

List with a cursor:

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps?limit=50" -H "X-DPP-Role: brand"
~~~

Ordering is deterministic on `(updatedAt, dppId)`, and paging is by cursor, not offset.
Offset paging omits or duplicates records when the collection changes during traversal, and
a passport collection changes continuously. Pass the returned `nextCursor` as `cursor`.

## Flow 2 — Resolve an identifier

A reader gives you an encoded identifier; you need the passport.

~~~sh
curl -s "http://127.0.0.1:8000/v1/identifiers/urn%3Aexample%3Acarrier%3A000001/dpp" \
  -H "X-DPP-Role: sortingOperator"
~~~

The identifier is URL-encoded in the path. Resolution goes through the commissioned carrier
bindings, so the answer distinguishes the failure modes that matter:

| Condition | Status | Reason code |
| --- | --- | --- |
| Resolves to a live passport | 200 | — |
| Well-formed, nothing bound | 404 | `S4C-IDENT-UNKNOWN` |
| Bound to a closed binding | 410 | `S4C-IDENT-RETIRED` (with the superseding record where known) |
| Bound to two active passports | 409 | `S4C-IDENT-DUPLICATE-BINDING` |

Add `?view=` to request a narrower projection than your role's default. A view **wider**
than your default is narrowed rather than refused, so a tightening policy returns less
instead of breaking a working integration.

See [Identifiers](identifiers.md) and [Carrier binding](carrier-binding.md).

## Flow 3 — The sorting view

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/sorting-view?consistency=strong" \
  -H "X-DPP-Role: sortingOperator"
~~~

Returns exactly what a sorting decision consumes and nothing else: `dppId`,
`recordVersion`, `generatedAt`, the operationally relevant `product` members, a
`materialSummary`, any `priorDecision`, plus `indexLagMs` and `consistency`.

`consistency=projected` (default) reads a projection and reports its lag;
`consistency=strong` reads the store directly. Because the response carries the
`recordVersion` it was produced from, a decision taken on this view can be replayed later
against the exact content that produced it. See
[Sorting integration](sorting-integration.md).

## Flow 4 — Append an observation

Observations are append-only. You add, you never edit.

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/observations" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: pssrSystem" \
  -H "X-DPP-Organisation: urn:example:org:sorter-a" \
  -H "Idempotency-Key: nir-scan-2044-01-16-0001" \
  -d '{"fibreType":"polyester","percentage":93.4,"percentageBasis":"mass",
       "valueStatus":"supplied","method":"nirSpectroscopy",
       "sourceOrganisationId":"urn:example:org:sorter-a",
       "sourceSystemId":"urn:example:system:nir-line",
       "confidence":{"value":0.86,"scale":"unitInterval"},
       "observedAt":"2044-01-16T09:03:00Z"}'
~~~

`201`, returning `observationId`, `dppId` and the new `recordVersion`. An `observationId`
you do not supply is generated. Disagreement with an existing observation is not an error —
see [Provenance](provenance.md).

## Flow 5 — Append a lifecycle event

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/events" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: collector" \
  -H "X-DPP-Organisation: urn:example:org:collector-a" \
  -H "Idempotency-Key: collection-000001" \
  -d '{"eventType":"collection","eventTime":"2043-07-10T12:00:00Z",
       "eventTimeZoneOffset":"+00:00","recordedAt":"2043-07-10T12:05:00Z",
       "actorOrganisationId":"urn:example:org:collector-a",
       "sourceSystemId":"urn:example:system:collection-client",
       "facilityId":"urn:example:facility:collection-site-a"}'
~~~

`eventId`, `recordedAt` and `actorOrganisationId` are defaulted when omitted, but supplying
them explicitly is better practice — the defaults describe the moment the server was told,
not the moment the thing happened. See [Lifecycle events](lifecycle-events.md).

## Flow 6 — Update a passport

`PATCH` is a shallow merge over non-append-only members, and requires `If-Match`:

~~~sh
ETAG=$(curl -sD - -o /dev/null "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001" \
  -H "X-DPP-Role: brand" | grep -i '^etag:' | cut -d' ' -f2 | tr -d '\r')

curl -s -X PATCH "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001" \
  -H "Content-Type: application/json" -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  -H "If-Match: $ETAG" \
  -d '{"product":{"articleClass":"homeTextileFlat","condition":"good"}}'
~~~

Two guards apply:

- **Optimistic concurrency.** A missing or stale `If-Match` returns `412` with
  `S4C-STATE-VERSION-CONFLICT`. Re-read, reapply, retry.
- **Append-only enforcement.** Patching `materialObservations`, `lifecycleEvents`,
  `sortingDecisions` or `integrity` returns `422` with
  `S4C-STATE-APPEND-ONLY-VIOLATION`, naming the member. Use the append endpoints instead.

Which members a role may write is in `WRITABLE_PATHS`
([`access.py`](../src/sort4circ_dpp/access.py)): `brand` may write `product`,
`identity.sourceRecordId`, `registryIdentifier` and `environmentalValues`; `administrator`
may write anything; every other role may not update a passport at all. A refused path is
named in the error rather than silently dropped.

## Flow 7 — Integrity verification

Optional, Tier 3. Nothing above depends on it.

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/integrity" \
  -H "X-DPP-Role: authority"

curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/integrity/verify" \
  -H "Content-Type: application/json" -H "X-DPP-Role: integrityVerifier" \
  -d '{"evidenceId":"urn:example:evidence:…"}'
~~~

Verification recomputes the digest from the stored version and compares it with the
anchored value. Four verdicts, deliberately distinct: `match`, `mismatch`, `unanchored`
(no confirmation yet — an operational condition, not tampering) and `unverifiable` (the
subject version or the receipt is no longer retrievable — a retention defect). Collapsing
the last two into `mismatch` would misattribute an availability problem to an integrity
failure. See [Integrity](integrity.md).

## Idempotency

Send `Idempotency-Key` on `POST` to `/v1/dpps`, `/carriers`, `/observations` and `/events`.

The key is scoped to the caller **subject, organisation, role, operation and resource**, so
two organisations using the same key string do not collide, and a key cannot be replayed
across operations. Repeating a request with the same key and the same body returns the
original result. Repeating it with the same key and a **different** body is a conflict:
`409` with `S4C-STATE-IDEMPOTENCY-CONFLICT`.

Use a key that is stable for the real-world operation — a scan identifier, a work-order
line — not a fresh UUID per HTTP attempt, which defeats the purpose.

## Views and access

Every read is projected. Views, narrowest to widest:

`integrityOnly` → `public` → `partner` → `sorting` → `recycler` → `authority` → `full`

Your role has a default view. Requesting a **narrower** view is honoured; requesting a
wider one silently returns your default rather than an error. The public view keeps the
composition but replaces `sourceOrganisationId` with an explicit
`"sourceOrganisationStatus": "withheld"` — marked rather than dropped, because silently
omitting it would let a consumer conclude the data was never collected.

The policy is data, not code: [`spec/access-matrix.json`](../spec/access-matrix.json). Full
role and scope tables are in [Security model](security.md).

## Error responses

All errors are RFC 9457 `application/problem+json` with `Content-Type:
application/problem+json` and an `X-Correlation-Id` header.

~~~json
{
  "type": "https://data.sort4circ.eu/problems/s4c-state-version-conflict",
  "title": "If-Match does not equal the current record version.",
  "status": 412,
  "detail": "If-Match is required for an update",
  "instance": "/v1/dpps/urn:example:dpp:000001",
  "reasonCode": "S4C-STATE-VERSION-CONFLICT",
  "safeAction": "rereadAndReapply",
  "correlationId": "…"
}
~~~

Payload failures add `errors: [{"path": "..."}]`; vocabulary failures add `vocabulary` and
`vocabularyVersion`. Branch on `reasonCode`, not on the HTTP status alone — several codes
share a status and call for different client behaviour.

The full catalogue is [`spec/reason-codes.json`](../spec/reason-codes.json). The ones you
will meet most often:

| Code | Status | What to do |
| --- | --- | --- |
| `S4C-PAYLOAD-SCHEMA-INVALID` | 422 | Fix the paths in `errors` |
| `S4C-PAYLOAD-VOCAB-INVALID` | 422 | Map the value to a published token |
| `S4C-AUTHZ-OPERATION-FORBIDDEN` | 403 | Your role lacks the scope |
| `S4C-AUTHZ-VIEW-FORBIDDEN` | 403 | Unknown view, or a view this role may never receive |
| `S4C-STATE-VERSION-CONFLICT` | 412 | Re-read, reapply, retry |
| `S4C-STATE-IDEMPOTENCY-CONFLICT` | 409 | Same key, different body — fix one of them |
| `S4C-STATE-APPEND-ONLY-VIOLATION` | 422 | Use the append endpoint |
| `S4C-STATE-NOT-FOUND` | 404 | The passport or evidence identifier does not exist |
| `S4C-IDENT-*` | 400/404/409/410 | See [Identifiers](identifiers.md) |
| `S4C-LEDGER-*` | — | See [Integrity](integrity.md) |

`safeAction` names the defined outcome the profile requires for that code — `divert`,
`noCommand`, `quarantine`, `rejectAtClient`, `noEffectOnSorting` and so on. The profile
fixes *which* outcome applies to each code; how your deployment realises it physically is
your decision. See [Sorting integration](sorting-integration.md).

## Regenerating and checking the contract

~~~sh
python tools/gen_openapi.py --check   # fails if the checked-in contract has drifted
python tools/gen_openapi.py           # regenerate it
python -m pytest tests/test_api_contract.py tests/test_access.py -q
~~~

The checked-in OpenAPI document is generated from the application definition, so it cannot
drift from the implemented routes without CI noticing.

## Related pages

- [Security model](security.md) — roles, scopes, views, and replacing `DemoAuth`
- [Scalability](scalability.md) — pagination, projections, caching, consistency
- [Conformance](conformance.md) — testing your own API implementation against this contract
