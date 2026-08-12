# SORT4CIRC DPP Development Guidelines & Reference Implementation

<p align="center">
  <img
    src="docs/assets/sort4circ-hero-dark.svg"
    alt="SORT4CIRC garment flow from RFID capture through passport resolution, sorting decision and asynchronous integrity anchoring."
    width="100%">
</p>

<p align="center">
  <a href="https://github.com/Constructor-Uni/SORT4CIRC/actions/workflows/ci.yml"><img alt="CI status" src="https://github.com/Constructor-Uni/SORT4CIRC/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.11, 3.12 and 3.13" src="https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&amp;logoColor=white">
  <a href="LICENSE"><img alt="Code license: Apache 2.0" src="https://img.shields.io/badge/code-Apache--2.0-7e57c2"></a>
  <a href="LICENSE-DOCS"><img alt="Specification and documentation license: CC BY 4.0" src="https://img.shields.io/badge/spec%20%26%20docs-CC%20BY%204.0-20a89a"></a>
</p>

Reference implementation and normative specification artefacts for the textile
Digital Product Passport (DPP) developed in SORT4CIRC work package 4, task 4.2,
and published in deliverable **D4.3, DPP development guidelines**.

Deliverable **D4.3 — DPP Development Guidelines** is the public SORT4CIRC
deliverable led by Constructor University (CU), with contributions from the CU
WP4 team. This repository provides specifications and reference software
supporting the sanitised D4.3 implementation profile; it is not the submitted
deliverable itself.

The repository has two halves that serve different purposes.

**`spec/` is normative.** It holds the JSON Schema, ontology, controlled
vocabularies, reason-code catalogue and access matrix that define
what a conformant passport is. An implementation in any language conforms by
satisfying these artefacts.

**`src/` is a reference implementation.** It exists to be read, to be tested
against, and to prove the specification is buildable. It is not a product.
Where the code and the specification disagree, the specification governs and the
disagreement is a bug in the code.

---

## What this is for

An organisation that has to produce a DPP faces the same first problem every
time: the regulation states what information must be available, and the
harmonised standards state how a passport system behaves, but neither says what
the record actually looks like or how a sorting line talks to it. This
repository answers that, at the level of field names, datatypes, endpoints,
error codes and a worked example whose digest can be recomputed by hand.

The specification is aligned with Regulation (EU) 2024/1781, the six harmonised
DPP standards cited in Commission Implementing Decision (EU) 2026/1736
(EN 18216, EN 18219, EN 18220, EN 18221, EN 18222, EN 18223), and the two
further JTC 24 standards EN 18239 and EN 18246 that are not cited in the
Official Journal. Alignment with a standard is not a claim of conformity
assessment; see [`docs/conformance.md`](docs/conformance.md) for what may and
may not be claimed.

## Quick start

```bash
git clone https://github.com/Constructor-Uni/SORT4CIRC.git
cd SORT4CIRC
make install          # installs into the active environment
make test             # full test suite
make example          # the D4.3 Annex G worked example, end to end
make serve            # API on http://localhost:8000, docs at /docs
```

The worked example is the fastest way to understand the model. It follows one
garment through creation, carrier commissioning, a read at the sorting gate,
resolution, a routing decision, a second technology that disagrees with the
first, digest calculation, anchoring and verification using the deterministic
reference adapter. Besu submission/status support exists, but independent
on-chain digest readback is not implemented.

## Idempotency semantics

The reference implementation scopes an `Idempotency-Key` by API operation and
resource. Within the same scope, reusing a key with the same body replays the
original outcome; reusing it with a different body returns an idempotency
conflict. Principal or organisation scoping is not currently defined,
`IDEMPOTENCY_WINDOW_SECONDS` is not enforced, and concurrent first-use duplicate
suppression is not guaranteed.

## The three conformance tiers

A single undifferentiated requirement set is not usable by an organisation
building a first passport. The guideline is therefore expressed as three
cumulative tiers, each a complete and testable state with its own exit test.

| Tier | Scope | Exit test |
| --- | --- | --- |
| **1, Core passport** | A persistent record at one granularity, a carrier bound to it, the mandatory field set, explicit unknown-value states, provenance on every observation, and an authenticated read API. | `make test` passes and the tier 1 checklist rows are green. |
| **2, Operational passport** | Adds lifecycle and sorting events, the write path with idempotency and optimistic concurrency, the sorting projection, the observation interface, translation with reconciliation, and the full access matrix. | Tier 1 plus the tier 2 rows. |
| **3, Assured passport** | Adds deterministic digests, ledger anchoring behind a replaceable adapter, independent verification of an altered record, and the measured performance and recovery campaign. | Tier 1 and 2 plus the tier 3 rows and an executed measurement campaign. |

An implementation may stop at a tier and still make a defensible conformance
statement, provided the statement names the tier. A statement that names no tier
is not a conformance statement.

## Two decisions that cannot be undone later

Both cost almost nothing at the first write and cannot be reconstructed
afterwards. They are the reason this repository exists in the shape it does.

**A material value never travels without its method and its source.** A record
that stores "95 percent polyester" without recording whether the figure came
from a sewn-in label, a supplier declaration or a quantitative analysis under
ISO 1833 cannot later distinguish a claim from a measurement. No downstream
processing recovers that distinction.

**Observations are appended, never overwritten.** When a near-infrared
instrument reports 93.4 percent polyester on a garment the laboratory measured
at 95 percent, both results are retained with their own method, source, time and
confidence. The service does not average them, does not prefer the newer one and
does not mark either superseded, because none of those operations has a
defensible basis: the methods differ in what they measure and in the conditions
under which each is reliable. An implementation that overwrites cannot answer
the question its operator most needs answered, which is whether its instrument
reads low on dark carbon-black-bearing polyester.

## Repository layout

```
spec/           normative artefacts
  schemas/      JSON Schema 2020-12 for the passport payload
  ontology/     OWL 2 DL vocabulary in Turtle, with the axioms that make it testable
  vocabularies/ 18 controlled vocabularies, versioned independently
  reason-codes.json   30 stable codes, each with an HTTP status and a safe gateway action
  access-matrix.json  roles, scopes and views, default deny
  openapi/      generated OpenAPI 3.1 contract
src/sort4circ_dpp/
  canonical.py  RFC 8785 canonicalisation, the integrity projection and the digest
  store.py      versioning, append-only collections, carrier bindings, in-memory outbox
  access.py     role, scope and view enforcement
  index.py      the read projection for the time-critical path, publishing its own lag
  evidence.py   the evidence state machine and the anchoring worker
  ledger/       the adapter contract, a reference adapter and a Hyperledger Besu adapter
  gateway/      read-zone controls applied before any sorting command is issued
  api.py        the RESTful interface
tests/          unit tests plus a conformance suite mapped to the D4.3 checklist rows
examples/       the worked example and fixtures
docs/           getting started, architecture, conformance, glossary
```

## The latency budget

Sorting is a real-time problem, and a latency target that is not derived from
the line it serves cannot be justified. The reference configuration in D4.3 is a
1.5 m/s conveyor with 2.40 m between the read zone and the first actuator, which
gives 1600 ms of transit. Subtracting reader decode, gateway settle, controller
scan, actuator engagement and a safety margin leaves **920 ms** for software.

Of that, 240 ms is allocated across gateway validation, network, the passport
lookup, rule evaluation and decision publication, and 175 ms is reserved for one
retry. The remaining headroom absorbs burst queueing. The derived server-side
lookup targets are p50 25 ms, p95 80 ms, p99 150 ms.

These are targets for the reference configuration, not measured results.
Substitute the measured parameters of the installed line and recompute; the
derivation is published in D4.3 so recomputation needs nothing else.

## Read-zone safety

Two tags in the read window means the system does not know which garment faces
the actuator. That is a state, not a transient fault: retrying resolves nothing
and consumes the remaining budget. The only correct outcome is diversion to
manual review, decided at the edge before the passport service is called at all.

Every negative read case has a defined safe action in
[`spec/reason-codes.json`](spec/reason-codes.json), and the test suite runs each
one 100 times asserting zero uncontrolled commands.

## Ledger anchoring

The evidence envelope carries a reference and a digest and no passport content.
That single property is the reason a public ledger can satisfy the
confidentiality requirement at all; it belongs to the envelope design and not to
any platform. Anchoring runs asynchronously through the reference
implementation's process-local in-memory outbox, so
an unavailable ledger never stops the line.

The repository ships a deterministic reference adapter and a Hyperledger Besu
adapter behind one contract. The generic ledger contract tests exercise
`InMemoryLedger`; Besu has focused unit tests, not live end-to-end
contract/network coverage. Besu submission/status support exists, but
independent on-chain digest readback is not implemented, so unsupported digest
verification fails closed as `unverifiable`. The Besu profile is an implementation
of the anchoring flow and is **not the outcome
of the assessment** procedure defined in D4.3 for EBSI, Algorand, IOTA and
Ethereum; that comparative benchmark and its TOPSIS ranking are scheduled work
and no ranking is claimed here.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). A change to anything under `spec/`
requires a version bump, a migration note and a corresponding test. A released
vocabulary token is never removed, only deprecated with a replacement reference,
because removal would invalidate records already written by other parties.

## Licensing

| Path / content | License |
| --- | --- |
| Python implementation under `src/` (excluding `src/sort4circ_dpp/_spec/`), tests, tools, examples, Docker, `.github/`, and repository build/development/configuration files | Apache License 2.0 |
| Generated API artifact under `spec/openapi/` | Apache License 2.0 |
| Specifications under `spec/` (excluding `spec/openapi/`) and documentation under `docs/` | Creative Commons Attribution 4.0 International |
| Packaged resources under `src/sort4circ_dpp/_spec/` | Creative Commons Attribution 4.0 International; byte-for-byte distribution copies of the corresponding specification files |

## Citation

See [`CITATION.cff`](CITATION.cff).

## Funding

**Funded by the European Union**

| Project metadata | Authority text |
| --- | --- |
| Formal project name | SORT4CIRC - Intelligent Textile SORting for enable CIRCularity |
| Grant agreement | 101181988 |
| Programme | Horizon Europe |
| Call | HORIZON-CL6-2024-CIRCBIO-02 |
| Topic | HORIZON-CL6-2024-CircBio-02-1-two-stage |
| Type of action | HORIZON-RIA |
| Coordinator | CONSTRUCTOR UNIVERSITY BREMEN GGMBH (CU) |
| Project start | 1 December 2025 |
| Duration | 36 months |
| Project website | <https://sort4circ.eu> |

Views and opinions expressed are however those of the author(s) only and do
not necessarily reflect those of the European Union or REA. Neither the
European Union nor the granting authority can be held responsible for them.
