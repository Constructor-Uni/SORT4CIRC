# Integrity and optional anchoring

Tier 3. Proving that a passport record has not changed since a given version — and,
optionally, anchoring that proof somewhere a third party can check.

**This is an assurance layer, not a prerequisite.** A Tier 1 Core Passport has no
`integrity` member at all and is a complete, valid, exchangeable record. Implement
identity, provenance, vocabularies and the API first. Come back here when you have a
counterparty who needs to verify that a record they saw earlier is the record you still
hold.

## The pipeline

~~~
a specific record version
  → deterministic canonical representation   (a fixed field projection, RFC 8785 JSON)
  → digest                                   (SHA-256 over those bytes)
  → evidence envelope                        (identifiers + digest, no passport content)
  → optional ledger adapter → anchor         (submit, await confirmation)
  → receipt                                  (transaction reference, network, state)
  → independent verification                 (recompute, compare, four verdicts)
~~~

Every stage is separable. You can stop after the digest and still have something useful:
a stable fingerprint you can publish, sign, timestamp or send to a counterparty by any
means you like. The ledger is the last and most optional step.

## Stage 1 — Canonical representation

A digest is only meaningful if two implementations agree byte for byte on what was hashed.
Two decisions produce that agreement.

### The projection

The digest covers an **explicit field subset**, not the whole record
([`canonical.py`](../src/sort4circ_dpp/canonical.py)):

| Level | Fields |
| --- | --- |
| Top level | `dppId`, `recordVersion`, `updatedAt` |
| `identity` | `granularity`, `itemId`, `epc` |
| `product` | `articleClass`, `fabricConstruction`, `technicalFlags` |
| Each `materialObservations` entry | `observationId`, `fibreType`, `percentage`, `percentageBasis`, `valueStatus`, `method`, `sourceOrganisationId`, `observedAt` |

Fields carrying access decisions, view artefacts and the `integrity` array itself are
**excluded**, because including them would make the digest depend on who was asking. A
digest that differs between a public read and an authority read is not a digest of the
record.

Array order **is** significant. Reordering observations changes the digest, which is
correct: the sequence is part of the record's history.

### The canonicalisation

RFC 8785 (JSON Canonicalisation Scheme): object keys sorted by UTF-16 code unit, no
insignificant whitespace, ECMAScript number serialisation, the ECMAScript JSON string
escape set.

The implementation is deliberately **restricted rather than permissive**. Numbers requiring
exponential notation, non-finite values, and non-string object keys are **rejected** with a
`CanonicalisationError` instead of being serialised in a form another implementation might
not reproduce. The profile's quantities all have plain decimal representations, so the
restriction costs nothing and removes a class of silent cross-implementation divergence.

Key sorting explicitly encodes to UTF-16 big-endian before comparison, because Python sorts
strings by code point and RFC 8785 sorts by UTF-16 code unit. The two orders differ where a
supplementary-plane character meets a code point in U+E000–U+FFFF.

This is an implementation of the parts of RFC 8785 the profile uses, verified against fixed
vectors. It is **not** a general certification that every possible RFC 8785 input is handled.

~~~sh
python -m sort4circ_dpp.cli digest my-dpp.json
python -m sort4circ_dpp.cli digest my-dpp.json --show-projection   # see the exact bytes
~~~

`--show-projection` is the tool to reach for when two implementations disagree: compare the
canonical text before comparing hashes.

## Stage 2 — Digest

SHA-256 over the canonical bytes, lower-case hexadecimal, 64 characters. The schema
enforces the format on `integrity[].digestValue`.

~~~python
from sort4circ_dpp import canonical

canonical.digest(record)                       # -> "…64 hex chars…"
canonical.canonical_bytes(record)              # the exact bytes hashed
canonical.verify_digest(record, expected)      # constant-time comparison
~~~

`verify_digest` uses a constant-time comparison. A mismatch means the stored record changed
after the digest was taken. It does **not** mean the ledger is wrong, and the two conditions
are reported separately.

Fixed digest vectors, including a changed-value vector, are in `tests/test_canonical.py`.
The primary vector is the digest published in deliverable D4.3, Annex G
(`dd14a3f2487f2b22deda4a7bc2b37e775f378e05d60dc1e6ad26fdf26038ae9f`, over 871 canonical
bytes). It is written out in the test rather than recomputed from the shipped fixture, so a
change to the projection code cannot silently move the published expectation. If your own
implementation canonicalises the same record and gets a different digest, your
canonicalisation differs from this profile — start there.
If you implement this profile in another language, those vectors are your first
cross-implementation test.

## Stage 3 — The evidence envelope

What gets submitted for anchoring:

~~~json
{
  "evidenceId": "urn:example:evidence:000001",
  "subjectRef": "urn:example:dpp:000001",
  "subjectVersion": 4,
  "canonicalisation": "rfc8785",
  "digestAlgorithm": "sha-256",
  "digestValue": "…64 hex chars…",
  "createdAt": "2044-01-16T09:05:00Z"
}
~~~

**No passport content leaves the system.** The envelope carries a reference and a digest,
and that is all. This is a property of the *envelope design*, not of any platform: it holds
whether you anchor to a permissioned ledger, a public chain, a notary, or a signed log
file. Detailed DPP content stays off-chain, permanently.

The corresponding record in the passport is an `integrity` entry, adding `evidenceState`
and, once anchored, `ledgerNetworkId`, `transactionRef`, `confirmedAt`, `attempts` and
`lastReasonCode`.

## Stage 4 — Evidence states

`created` → `queued` → `submitted` → `confirmed`, with `retryableFailed` and
`terminalFailed` as the failure branches.

~~~
created ─→ queued ─→ submitted ─→ confirmed        (terminal)
              │  ╲       │  ╲
              │   ╲      │   ╲
              │    ╲     ↓    ╲
              │     → retryableFailed ─→ queued
              │                       ╲
              └───────────────────────→ terminalFailed   (terminal)
~~~

Transitions are validated: an impossible transition raises rather than recording a history
that could not have happened. `confirmed` and `terminalFailed` are terminal.

`retryableFailed` and `terminalFailed` are distinct because they call for different
responses — one is a back-off, the other is an escalation. See
[`evidence.py`](../src/sort4circ_dpp/evidence.py) and the `evidence-state` vocabulary.

## Stage 5 — The ledger adapter (optional)

The `LedgerAdapter` interface ([`ledger/base.py`](../src/sort4circ_dpp/ledger/base.py)) is
four methods:

| Method | Contract |
| --- | --- |
| `submit(evidence_id, envelope)` | Broadcast. Submitting the same `evidence_id` twice returns the original receipt rather than creating a second anchor. |
| `status(evidence_id)` | The current receipt, or `None` if unknown. |
| `anchored_digest(evidence_id)` | The digest recorded on the ledger. |
| `verify(evidence_id, recomputed)` | A verdict. |

The idempotency of `submit` is the important one: a retry after an ambiguous outcome — you
broadcast, the connection dropped, you do not know whether it landed — must not produce a
second anchor indistinguishable from a replay afterwards.

`Receipt` is platform-independent: `evidence_id`, `transaction_ref`, `network_id`, `state`,
`confirmed_at`, `block_ref`, and an optional `raw` for platform detail.

`LedgerError` carries a reason code and a `retryable` flag, so the worker knows whether to
re-queue or escalate. The relevant codes are `S4C-LEDGER-UNAVAILABLE`,
`S4C-LEDGER-SUBMIT-REJECTED`, `S4C-LEDGER-TIMEOUT-AFTER-BROADCAST` and
`S4C-LEDGER-DIGEST-MISMATCH`. `TIMEOUT-AFTER-BROADCAST` deserves its own code because "we
do not know whether it landed" is a genuinely different state from "it failed".

### What ships here

`InMemoryLedger` — a mock that produces deterministic simulated outcomes for contract
tests. There is no deployed network, no signing arrangement, no account, no key material
and no configuration recipe in this repository. That is a deliberate publication boundary,
not an omission: a working anchoring deployment involves credentials and network
configuration that must not be distributed.

### Bringing your own

Implement the four methods and pass the adapter to `create_app(ledger=...)`. The generic
contract tests in `tests/test_ledger_contract.py` run against **any** adapter, so a
platform change is a configuration change rather than a rewrite:

~~~sh
python -m pytest tests/test_ledger_contract.py -q
~~~

Beyond the generic contract, you need your own private tests for provider-specific
behaviour, retention, key management and recovery. Those are deployment concerns, and this
repository supplies no recipe for them.

**Any platform is acceptable** — permissioned or public ledger, a notary service, a
transparency log, an internal append-only store, or a signed timestamp — provided the
external behaviour holds: idempotent submission, a retrievable receipt, a retrievable
anchored digest, and the four verdicts below. The profile constrains behaviour, not
technology.

## Stage 6 — Independent verification

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/integrity/verify" \
  -H "Content-Type: application/json" -H "X-DPP-Role: integrityVerifier" \
  -d '{"evidenceId":"urn:example:evidence:000001"}'
~~~

The service fetches the stored record **at the anchored `subjectVersion`**, recomputes the
digest, and compares. Four verdicts, kept distinct because they call for different actions:

| Verdict | Meaning | What it is not |
| --- | --- | --- |
| `match` | The record at that version reproduces the anchored digest | Not proof that the claims are true |
| `mismatch` | The record changed after anchoring | Reported with `S4C-LEDGER-DIGEST-MISMATCH` |
| `unanchored` | No confirmation yet | An **operational** condition, not a tampering indication |
| `unverifiable` | The subject version or the receipt is no longer retrievable | A **retention** defect |

Collapsing `unanchored` or `unverifiable` into `mismatch` would misattribute an
availability problem to an integrity failure — and integrity failures get escalated to
people, so the difference is expensive.

The `integrityVerifier` role exists for exactly this: it holds `dpp.read`,
`integrity.read` and `integrity.verify`, and receives the `integrityOnly` view —
`dppId` and the integrity array, nothing else. A verifier does not need to see the product.

## What a match does and does not establish

A `match` establishes **byte-level agreement between the stored record's canonical
projection and the digest recorded at anchoring time**. That is a strong and useful
property. It is not:

- proof that any material claim in the passport is factually true;
- proof that the responsible operator is who they claim to be;
- a legal or regulatory conformity statement;
- a guarantee about fields outside the digest projection.

Integrity and provenance answer different questions. Provenance
([Provenance](provenance.md)) says who claimed what, on what basis, and when. Integrity says
the content has not changed since a version. Neither substitutes for the other, and neither
establishes truth.

## Trying it locally

The [worked example](../examples/worked_example.py) runs the whole pipeline in-process:

~~~sh
python examples/worked_example.py
~~~

It creates a passport, appends an observation, drains the local worker through Python
(`app.state.worker.drain()` — deliberately **not** an HTTP endpoint; it is
reference-implementation plumbing, not part of the exchange contract), then verifies the
resulting digest and asserts `match`.

Relevant tests:

~~~sh
python -m pytest tests/test_canonical.py tests/test_evidence.py tests/test_ledger_contract.py -q
~~~

## Reference implementation limits

- state is in process memory and does not survive a restart;
- the only supplied adapter is the in-memory mock, so receipts are simulated outcomes;
- there is no durable queue, no external anchoring, no operational finality and no
  retention assurance;
- `tools/anchor_bench.py` exercises the mock adapter's behaviour. It benchmarks this
  process and says nothing about any distributed ledger.

## Related pages

- [Customisation](customisation.md) — implementing a real adapter
- [Security model](security.md) — who may read and verify integrity evidence
- [Conformance](conformance.md) — digest verification as a conformance check
- [Data model](concepts.md#integrity) — the `integrity` array's schema
