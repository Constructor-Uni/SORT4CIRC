# Architecture

## The separation that everything else follows from

Two paths run at different speeds and must not be coupled.

The **time-critical path** is: read the identifier, apply read-zone controls,
resolve the passport, retrieve the operational view, publish the routing
decision. It has a hard deadline set by physics, and it must complete before the
garment reaches the actuator.

The **evidence path** is: record the lifecycle event, compute the digest, queue
the evidence, submit to the ledger, record the confirmation. It has no deadline
at all.

Coupling them makes line throughput depend on consensus timing. The reference
implementation's process-local in-memory outbox keeps them apart:
the passport write and its evidence-queue entry are recorded together, and
everything after that is asynchronous. A production deployment must provide
durable persistence if restart survival is required.

## Components

| Component | Responsibility | Module |
| --- | --- | --- |
| Read zone | Ambiguity, malformed identifiers, weak signal and duplicate suppression, decided at the edge | `gateway/readzone.py` |
| Passport store | Version history, append-only collections, carrier bindings, outbox | `store.py` |
| Read index | Compact projection for the sorting path, publishing its own lag | `index.py` |
| Access layer | Role, scope and view enforcement, default deny | `access.py` |
| Canonicalisation | RFC 8785 serialisation, integrity projection, digest | `canonical.py` |
| Evidence worker | State machine, retry, reconciliation | `evidence.py` |
| Ledger adapters | One contract, several platforms | `ledger/` |
| API | The interface contract | `api.py` |

## Why the index publishes its lag

A projection is always some amount behind the record it projects. An
implementation can hide that or report it. Hiding it means a sorting controller
cannot tell whether it is acting on current information. Reporting it as
`indexLagMs` lets the controller decide: accept the projection, or re-request
with `consistency=strong` and pay the latency of the authoritative path.

An entry older than the configured limit is refused outright rather than served,
because a routing decision taken on stale data cannot be detected downstream.

## Why observations are never merged

Two technologies observing one garment produce two observation sets. The service
retains both. It does not average them, prefer the newer, or mark either
superseded, because none of those has a defensible basis: near-infrared
spectroscopy and quantitative chemical analysis measure different things and are
reliable under different conditions.

Selecting between them is the job of the consuming rule set, and the selection
rule is versioned with that rule set. Encoding it into the passport would
prevent a second consumer from applying a different and equally legitimate rule.

The composition sum rule follows from this. It applies within an observation
set, never across sets. A laboratory set of 95 polyester plus 5 elastane and a
later near-infrared set of 93.4 polyester sum to 193.4 across the array and are
both correct.

## Why the ledger holds a digest and nothing else

The evidence envelope carries an identifier, a subject reference, a version, a
canonicalisation profile, an algorithm, a digest and a timestamp. No passport
content, no personal data, no commercial terms.

This is what makes a public ledger acceptable. The property belongs to the
envelope design, not to any platform: a design that placed passport content on a
public ledger would fail the confidentiality requirement for every public
platform, and the failure would be the design's, not the platform's.

The reference adapter retrieves the exact version the evidence cited, recomputes
the digest and compares. External adapters must independently retrieve the
anchored digest before making that comparison; the current Besu adapter does not
implement that readback and therefore reports verification as `unverifiable`.
Verifying against the current version instead would report a mismatch for every
record that has legitimately changed since, which is why `subjectVersion` is
mandatory.

## Blockchain profile status

D4.3 identifies permissioned Besu/QBFT as the current project reference
baseline. The public repository supplies the replaceable adapter and a local
Besu smoke service, but not a production validator topology or signed platform
selection record. This is insufficient to reproduce the D4.3 operational-network
claim and is not a demonstrator deployment authorisation.

Besu/Teku is a candidate Ethereum-compatible proof-of-stake migration profile.
It is not selected. It remains subject to the same frozen environmental limits,
evidence-sufficiency screen, comparative benchmark and integration validation as
every other candidate. Detailed passport content remains off-chain in every
profile.
