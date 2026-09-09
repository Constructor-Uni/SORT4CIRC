# Architecture

How the reference implementation is put together, and which of its boundaries are worth
reproducing in your own system.

This is a teaching design. It describes no project deployment, and it is not the only valid
architecture. What is worth copying is the **separation of responsibilities**: each seam
below exists because something on either side of it changes independently.

## Components

~~~
             ┌──────────────┐
 request ──→ │ AuthProvider │──→ Principal (subject, role, organisation)
             └──────────────┘
                    │
                    ▼
             ┌──────────────┐     scope check + view projection
             │ access.py    │
             └──────────────┘
                    │
                    ▼
  ┌────────────────────────────────────────────┐
  │ api.py — FastAPI exchange surface (/v1)    │
  └────────────────────────────────────────────┘
        │                │                 │
        ▼                ▼                 ▼
 ┌─────────────┐  ┌─────────────┐   ┌────────────────┐
 │PassportStore│  │  ReadIndex  │   │ EvidenceWorker │
 │ (authority) │→ │ (projection)│   │  (async queue) │
 └─────────────┘  └─────────────┘   └────────────────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │ LedgerAdapter│──→ InMemoryLedger (mock)
                                     └──────────────┘
~~~

`create_app(store=..., ledger=..., auth_provider=...)` injects all three replaceable
components. Nothing else in the application holds state, which is what makes the API
instances stateless and each component independently substitutable.

| Module | Responsibility |
| --- | --- |
| [`api.py`](../src/sort4circ_dpp/api.py) | The `/v1` exchange surface; correlation identifiers; problem responses |
| [`auth.py`](../src/sort4circ_dpp/auth.py) | `AuthProvider` protocol; `PublicOnlyAuth` (default) and `DemoAuth` (opt-in) |
| [`access.py`](../src/sort4circ_dpp/access.py) | Scopes, views, projections, write-path restrictions |
| [`store.py`](../src/sort4circ_dpp/store.py) | Versioned records, append-only collections, carrier bindings, idempotency |
| [`index.py`](../src/sort4circ_dpp/index.py) | The sorting projection and its measured lag |
| [`validation.py`](../src/sort4circ_dpp/validation.py) | Schema, then vocabulary, then cross-field rules |
| [`vocab.py`](../src/sort4circ_dpp/vocab.py) | Vocabulary loading and field bindings |
| [`canonical.py`](../src/sort4circ_dpp/canonical.py) | Integrity projection, RFC 8785 canonicalisation, SHA-256 |
| [`evidence.py`](../src/sort4circ_dpp/evidence.py) | Evidence state machine and the async worker |
| [`ledger/base.py`](../src/sort4circ_dpp/ledger/base.py) | The adapter contract every backend satisfies |
| [`ledger/memory.py`](../src/sort4circ_dpp/ledger/memory.py) | The mock adapter used by the contract tests |
| [`gateway/readzone.py`](../src/sort4circ_dpp/gateway/readzone.py) | Read classification before resolution |
| [`mapping.py`](../src/sort4circ_dpp/mapping.py) | JSON ↔ XML ↔ RDF projections |
| [`reasons.py`](../src/sort4circ_dpp/reasons.py) | The reason-code catalogue and RFC 9457 problem documents |
| [`config.py`](../src/sort4circ_dpp/config.py) | Spec locations, versions, page-size limits |
| [`synthetic.py`](../src/sort4circ_dpp/synthetic.py) | The deterministic synthetic fixture factory |
| [`public_summary.py`](../src/sort4circ_dpp/public_summary.py) | The allowlisted conformance summary exporter |

## The seams worth copying

**Identity is injected, not built in.** `AuthProvider` returns a `Principal` or raises. The
access layer never sees a credential, and the identity mechanism can be replaced without
touching authorisation logic. See [Security model](security.md).

**Authorisation is data, not code.** Roles, scopes and views live in
[`spec/access-matrix.json`](../spec/access-matrix.json). Changing policy is changing a
specification asset, which is reviewable and versionable; scattering it through handlers is
neither.

**Reads are always projected.** No handler returns a stored record directly. `project()`
never mutates the record and always carries the `recordVersion` it was produced from, so a
decision taken on a view can be replayed against the exact content that produced it.

**The authoritative store and the read projection are separate.** `PassportStore` holds
version snapshots and append-only collections; `ReadIndex` maintains the sorting projection
and reports its own lag. A caller chooses `projected` or `strong` per read. See
[Scalability](scalability.md).

**Read classification precedes resolution.** `ReadZone` separates absent, malformed,
ambiguous, weak-signal and duplicate-suppressed reads *before* any identifier is resolved,
and maps each outcome to the safe action published in the reason-code catalogue. Deciding
locally is the point: a service round trip cannot tell you which of two tags in the zone is
in front of the actuator. See [Sorting integration](sorting-integration.md).

**Integrity work is asynchronous and behind a contract.** Writes enqueue; `EvidenceWorker`
drains; `LedgerAdapter` is four methods (`submit`, `status`, `anchored_digest`, `verify`).
A new backend passes the same contract tests as every other, so a platform change is a
configuration change rather than a rewrite. Anchoring latency never lands on the write
path. See [Integrity](integrity.md).

**Validation is layered and returns distinct codes.** Structure, then vocabulary, then
cross-field rules — because a vocabulary check on a malformed document reports the wrong
failure, and a client needs to tell a shape problem from a meaning problem.

## Implementation tiers

The architecture supports incremental adoption. You do not need the whole diagram on day
one.

| Tier | Components involved |
| --- | --- |
| **1 — Core Passport** | Schema and vocabularies, a store with versioning and carrier binding, read/resolve endpoints, the access matrix and projections |
| **2 — Operational Passport** | Adds append endpoints, idempotency and conditional writes, the read projection and sorting view, enterprise translation |
| **3 — Assured Passport** | Adds canonicalisation and digests, the evidence state machine and worker, a ledger adapter, independent verification |

These tiers are an adoption sequence defined by this profile. They are not an EU
certification scheme and confer no external status.

## What the reference implementation is not

- **Not durable.** `PassportStore` is process memory. Every record is lost on restart.
- **Not authenticated.** `DemoAuth` performs no verification of any kind.
- **Not anchored.** `InMemoryLedger` simulates outcomes; there is no network, account, key
  or contract.
- **Not a deployment.** No topology, no persistence layer, no operational signing
  arrangement, no physical-line settings, no latency targets.

Every one of these is a deliberate boundary, and each is documented where it is replaced:
[Customisation](customisation.md), [Security model](security.md),
[Scalability](scalability.md), [Integrity](integrity.md).

## Related pages

- [API guide](api.md) — the surface these components serve
- [Data model](concepts.md) — what the store holds
- [Traceability](traceability.md) — which behaviours are implemented, specified or out of scope
