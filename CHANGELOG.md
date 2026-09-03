# Changelog

Format follows Keep a Changelog. Versions follow semantic versioning, applied
independently to each artefact under `spec/`.

## [Unreleased]

### Fixed

- Corrected the new release-support evidence package identity from the
  historical 1.1.1 release to the future 1.2.0 release, co-located safe raw
  results with their records, and marked raw results containing personal local
  paths as restricted with their exact digest and byte count preserved.

## [1.1.1] - 2026-08-11

Presentation and release-integrity maintenance for the software package. No
normative specification artefact changed.

### Added

- A self-contained animated SVG overview of the implemented sorting workflow,
  including RFID capture, passport resolution, independently retained material
  observations, a versioned routing decision and asynchronous integrity
  anchoring outside the critical sorting path.
- Automated coverage that keeps `MANIFEST.sha256` aligned with the delivered
  tree, plus an explicit `python verify_files.py --write` regeneration command.

### Fixed

- Aligned the Python package, runtime module, citation metadata and Docker image
  target on software release 1.1.1.
- Added a compact CI, Python support and dual-license badge row to the project
  overview, and declared Python 3.13 in the package classifiers to match CI.

### Unchanged

Nothing under `spec/` changed. The payload schema, ontology, access policy,
controlled vocabularies and OpenAPI v1 contract retain their intentional 1.0.0
versions. This patch release changes software and documentation only; no record
migration is required.

## [1.1.0] - 2026-08-11

Measurement harnesses and one defect fix in the read path. No normative
artefact changed, so an implementation conformant to 1.0.0 remains conformant.

### Added

- `tools/loadtest.py`, which measures the reference service under concurrent
  load across resolution, the sorting projection, observation submission and
  search, and reports the outbox drain separately because it is not on the
  sorting path. The executed campaign is published under `docs/benchmarks/`.
- `tools/anchor_bench.py`, which measures anchoring submission latency, time to
  confirmation, fee and metered energy per ledger platform, with a four-platform
  configuration example in `docs/benchmarks/anchor-targets.example.json`. A
  platform it cannot reach is reported as `notReached` rather than modelled, and
  an energy figure is withheld unless a meter log and a matching idle log are
  supplied.
- `tests/test_index_staleness.py`, covering the projection staleness behaviour
  corrected below.

### Fixed

- **Projection staleness was measured against the wall clock.** The read index
  bounded the age of a sorting projection against the staleness limit whether or
  not the authoritative record had changed, so a line idle for longer than the
  limit had every sorting read refused with `S4C-DEP-UNAVAILABLE` until the next
  write. Idleness is not an error and the refusal stopped sorting for a
  condition that was not a fault. The limit now bounds the interval by which the
  projector trails the source: `PassportStore` records the monotonic time of its
  most recent commit, `ReadIndex` records the moment it last caught up, and
  `ReadIndex.backlog_ms()` is the difference. A projection nothing has
  invalidated is served; a projector that stopped while writes continued is
  still refused. The problem document now carries `backlogMs` alongside
  `indexLagMs`, so the two conditions are distinguishable by the caller.

### Unchanged

Nothing under `spec/` changed in this release. The payload schema stays
`dpp-1.0.0`, the ontology stays `sort4circ-1.0.0`, every controlled vocabulary
keeps the version it carried at 1.0.0, and `SCHEMA_VERSION` stays `1.0.0`. The
version bump is to the software package only; records written against 1.0.0 are
read and written identically by 1.1.0, and no migration is required.

## [1.0.0] - 2026-08-10

First public release, accompanying deliverable D4.3 "DPP development
guidelines" (SORT4CIRC work package 4, task 4.2).

### Specification

- Passport payload schema `dpp-1.0.0` (JSON Schema 2020-12).
- Ontology `sort4circ-1.0.0` (OWL 2 DL, Turtle) with the axioms that make the
  model testable: observations disjoint from the things they describe, a
  minimum cardinality of one on method and source, and an irreflexive
  asymmetric part-of relation so component cycles are detectable.
- Eighteen controlled vocabularies, versioned independently.
- Thirty reason codes, each with an HTTP status and a normative safe action for
  the edge gateway.
- Access matrix with ten roles, seven views and default deny.

### Implementation

- RFC 8785 canonicalisation and the integrity projection, reproducing the
  digest published in D4.3 Annex G byte for byte.
- Passport store with version history, append-only collections, atomic carrier
  commissioning, identifier non-reuse and a transactional outbox.
- Evidence state machine with retry on the same evidence identifier and
  reconciliation before any resubmission.
- Ledger adapter contract with a deterministic reference adapter and a
  Hyperledger Besu adapter.
- Read-zone controls resolving ambiguity, malformed identifiers, weak signal and
  duplicate reads at the edge, before the passport service is called.
- RESTful API with ETag, If-Match, idempotency keys, cursor pagination and
  RFC 9457 problem details.

### Corrections to the deliverable text

- **Composition rule.** D4.3 states that where every fibre observation is a
  supplied mass fraction the percentages sum to 100. Applied across the whole
  observation array this contradicts the append-only model: a laboratory result
  of 95 plus 5 and a later near-infrared result of 93.4 sum to 193.4 and are
  both correct. The rule is applied per observation set, identified by source,
  system, method and observation time. Within a set, supplied mass fractions may
  not exceed 100 plus tolerance; a set summing to less than 100 is accepted,
  because requiring 100 would force an implementation to fabricate a residual.
- **Public read scope.** The access matrix in D4.3 Annex F grants the public
  role read access but the scope list omitted the read scope, which would have
  made the public view unreachable. The scope is granted in
  `spec/access-matrix.json`.
- **Missing safe action.** The reason-code table used the action
  `rereadAndReapply` without defining it. It is now defined.
