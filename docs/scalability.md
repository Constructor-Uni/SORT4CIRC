# Scalability

Design decisions in the profile that determine whether an implementation scales, and what
you have to supply yourself. This is about **what to build**; measuring what you built is
[Testing methodology](testing-methodology.md).

The reference implementation is an in-memory teaching service. It demonstrates the
interface properties that make scaling possible; it is not a scalable deployment and no
performance figure in this repository describes one.

## What the profile gets right, and why it matters

### Cursor pagination, never offset

`GET /v1/dpps` orders deterministically on `(updatedAt, dppId)` and pages by **cursor**:

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps?limit=200" -H "X-DPP-Role: brand"
# -> {"items": [...], "nextCursor": "urn:example:dpp:000200"}
curl -s "http://127.0.0.1:8000/v1/dpps?limit=200&cursor=urn:example:dpp:000200" ...
~~~

Offset pagination is not offered, and this is deliberate. A passport collection changes
continuously; with an offset, records inserted or updated mid-traversal cause other records
to be **skipped or duplicated**, silently. A consumer doing a full sync gets a wrong answer
and no error. Offsets also cost more to serve as the offset grows.

`limit` defaults to 50 and is capped at 500 (`config.py`). Cap it in your implementation
too: an uncapped page size is a denial-of-service surface.

### Projections instead of full documents

The sorting view is a purpose-built projection, not a filtered copy of the passport. It
carries exactly what a routing decision consumes. At line speed, with thousands of
decisions per hour, the difference between a small projection and a full document is the
difference between a viable and a non-viable integration — in payload size, in
serialisation cost, and in what an operational system is exposed to.

Build projections for read paths that are hot and narrow. Do not serve `full` to a system
that needs six fields.

### Explicit consistency, chosen per read

~~~sh
GET /v1/dpps/{id}/sorting-view?consistency=projected   # default; reports indexLagMs
GET /v1/dpps/{id}/sorting-view?consistency=strong      # reads the store
~~~

The choice is per request, not global, and the response **reports its own lag**
(`indexLagMs`) and mode (`consistency`). A caller can therefore decide, per decision,
whether the freshness it got is good enough.

`ReadIndex` also supports an optional `max_lag_ms` bound: when the projector trails the
source by more than the bound, the read is **rejected** rather than served stale. Note how
lag is defined — `backlog_ms()` compares the last commit the projector processed against
the store's last commit, so it is zero when the projector has caught up, whatever the wall
clock says. That distinction matters: a projector idle because nothing is being written is
healthy; a projector idle because it has stopped while writes continue is an incident, and
elapsed-time-since-last-update cannot tell them apart.

### Idempotency that survives retries

`Idempotency-Key` is scoped to caller subject, organisation, role, operation and resource.
Consequences worth having:

- two organisations can use the same key string without colliding;
- a key cannot be replayed across operations;
- a retried write after a timeout returns the original result instead of duplicating;
- the same key with **different** content is a conflict
  (`S4C-STATE-IDEMPOTENCY-CONFLICT`), not a silent overwrite.

This is what lets a sorting line or a nightly ERP load queue writes locally and replay them
without duplication. Derive keys from stable real-world operations — a scan identifier, a
document line — not from a fresh UUID per HTTP attempt.

### Optimistic concurrency, not locks

`PATCH` requires `If-Match` against the current `ETag`; a stale value returns `412`
`S4C-STATE-VERSION-CONFLICT`. Reads support `If-None-Match` → `304`.

Optimistic concurrency scales where pessimistic locking does not: there is no lock to hold
across a network round trip, no lock to leak when a client dies, and conflicts are rare in
practice because most writes are appends to different passports.

### Append-only collections

`materialObservations`, `lifecycleEvents`, `sortingDecisions` and `integrity` are
append-only. Appends do not contend with each other the way read-modify-write updates do,
they are naturally idempotent given a stable key, and they never lose a concurrent writer's
data. This is the reason a sorting line and a laboratory can both write to the same
passport without coordination.

### Integrity work is asynchronous

Writes enqueue evidence work; they do not block on it. `EvidenceWorker` drains the queue
separately. Anchoring latency — which for a real ledger can be seconds to minutes — is
therefore never on the write path. If you implement anchoring, keep this property: a
passport write must not wait for a ledger.

### Correlation identifiers

Every response carries `X-Correlation-Id`, echoed from the request when supplied. Propagate
it across services; without it, tracing a single item's path through resolve → view →
observation → decision across several systems is guesswork.

## What you must supply

The reference implementation stops here. Everything below is yours.

| Concern | What the reference does | What a deployment needs |
| --- | --- | --- |
| Storage | In-process dict, lost on restart | A durable store with the same version, append, uniqueness, idempotency and conditional-update semantics |
| Horizontal scaling | Single process | Stateless API instances behind a load balancer; state in the store |
| Projections | In-process, synchronous on commit | A projection pipeline with monitored lag and a rebuild path |
| Caching | `Cache-Control: no-store` on projected reads | A deliberate policy; `ETag` supports conditional requests |
| Rate limiting | None; `S4C-RATE-LIMITED` exists as a code | An actual limiter, per principal |
| Backpressure | None | Queue depth limits, `S4C-DEP-UNAVAILABLE`, client back-off |
| Archival | All versions retained in memory | A retention policy — note that integrity verification needs the anchored `subjectVersion` to remain retrievable, or the verdict becomes `unverifiable` |
| Recovery | None | Backup, restore, and a tested rebuild of projections |

Two of these interact in a way that is easy to miss: **retention and integrity**. If you
anchor a digest of record version 4 and later prune version 4, verification returns
`unverifiable` — a retention defect, correctly reported, but a defect. Decide the retention
window and the anchoring policy together.

`Cache-Control: no-store` is set on projected reads because the response depends on the
caller's view; a shared cache would serve one role's projection to another. If you
introduce caching, key it on the principal's view, or cache only immutable
version-addressed representations.

## Rough shape of a scaled deployment

~~~
clients ─→ TLS / rate limit / authn ─→ stateless API instances
                                            ├─→ passport store (durable, versioned)
                                            ├─→ read projections (lag-monitored)
                                            └─→ evidence queue ─→ ledger adapter (async)
~~~

Keep the API instances stateless. The reference `create_app(store=..., ledger=...,
auth_provider=...)` signature is already shaped for this: all state is injected, nothing is
held in the application object that could not be shared.

## Measuring

Do not take any number from this repository as a performance figure. `tools/loadtest.py`
runs a small in-process workload against fictional records and cannot measure a network, a
database or a deployment:

~~~sh
python tools/loadtest.py --requests 12
~~~

It counts failures and computes latency percentiles for **your** run. It supplies no
target, and this repository records no results. A target is a requirement you choose before
measuring; an observed value is a measurement. Do not confuse them, and do not compare runs
without a documented method.

Full guidance, including what to record and what short in-process measurements exclude:
[Testing methodology](testing-methodology.md).

## Related pages

- [Customisation](customisation.md) — replacing the store with something durable
- [API guide](api.md) — pagination, idempotency and concurrency in detail
- [Sorting integration](sorting-integration.md) — degradation and local queueing at the edge
- [Integrity](integrity.md) — asynchronous anchoring and retention
