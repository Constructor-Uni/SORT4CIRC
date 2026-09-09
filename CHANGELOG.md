# Changelog

Format follows Keep a Changelog. Two version numbers are tracked separately:
the **repository release** (this file's headings) and the **SORT4CIRC DPP
implementation profile** version carried by the artefacts under `spec/`.

## [1.2.0] - unreleased

Repository release 1.2.0 implements the SORT4CIRC DPP implementation profile
**1.0.0**. This release changes the documentation, tooling, packaging and tests.
It does **not** change the normative profile: records valid under 1.1.1 remain
valid and no migration is required.

### Added

- Developer-oriented documentation. `README.md` is now the entry point for
  someone building a textile DPP from scratch, with an "I want to..." index and a
  quickstart. The `docs/` tree is organised around implementation questions and a
  sixteen-step developer journey rather than specification section order.
- New guides: [Create your first DPP](docs/first-dpp.md),
  [Identifiers](docs/identifiers.md), [Validation](docs/validation.md),
  [Provenance](docs/provenance.md), [Vocabularies](docs/vocabularies.md),
  [Lifecycle events](docs/lifecycle-events.md),
  [Carrier binding](docs/carrier-binding.md),
  [Enterprise integration](docs/enterprise-integration.md),
  [Sorting integration](docs/sorting-integration.md),
  [Security model](docs/security.md), [Scalability](docs/scalability.md) and
  [Traceability](docs/traceability.md).
- Implementation tiers - Core, Operational and Assured Passport - giving an
  adoption sequence in which integrity anchoring and RDF/OWL come after a
  working, exchangeable passport rather than before it. A profile-defined
  sequence, not a certification scheme.
- Requirement traceability: each requirement area mapped to its specification
  asset, implementation and test, and classified by origin (standards-profile,
  project-scope or engineering decision) and status (implemented, specified,
  optional, deployment-specific, out of scope).
- An explicit public-file policy (`public-release-policy.json`) with generated
  manifests and checksums, verified by `tools/verify_public_release.py`.
- `CONTRIBUTING.md` and `SECURITY.md` covering installation, tests, fixtures,
  specification changes, private vulnerability reporting and the
  synthetic-data-only contribution rule.

### Changed

- The Docker compose example is fail-closed by default: `DPP_DEMO_AUTH` defaults
  to `0`, so the service starts read-only and rejects claimed role headers. The
  local header-based demo identity is opt-in and documented.
- The reference implementation's local evidence-drain route is no longer part of
  the **public** OpenAPI contract. It is implementation administration, not part
  of the interoperability surface, and its absence does not change the profile.
  A test keeps `/internal` and `/admin` plumbing out of the public contract.
- Package metadata declares the repository release version (1.2.0) separately
  from the profile version (1.0.0); `sort4circ_dpp.config.PROFILE_VERSION`
  carries the latter.

### Fixed

- Restored the Annex G worked example
  (`examples/fixtures/valid-annex-g-garment.json`) and its published canonical
  digest vector, so the repository again reproduces the published reference
  record exactly. The
  reference digest is
  `dd14a3f2487f2b22deda4a7bc2b37e775f378e05d60dc1e6ad26fdf26038ae9f` over 871
  canonical bytes. The Annex G identifiers are synthetic.
- Restored the normative SORT4CIRC namespace `https://data.sort4circ.eu/` across the
  ontology, XSD, mapping package, schema `$id`, access matrix, reason-code
  problem types and documentation.
- Restored the full reason-code catalogue to 30 codes, including
  `S4C-READ-SUPPRESSED-DUPLICATE` and `S4C-READ-WEAK-SIGNAL`, together with the
  profile safe-action vocabulary (`divert`, `divertAndAlert`, `noCommand`,
  `quarantine`, `retryOnceThenDivert`, `noEffectOnSorting` and the rest). Safe
  actions are part of gateway behaviour for PSSR and sorting-system
  interoperability.
- Restored the access role `pssrSystem` and the `gs1Sgtin96` carrier
  encoding token.
- Restored the Apache License 2.0 software grant. A change to MIT had been
  introduced without a recorded decision; documentation and package metadata now
  state the Apache-2.0 / CC BY 4.0 component split factually, with no claim of an
  approval history.
- Removed a duplicate positive fixture whose content was identical to
  `valid-minimum.json`.

### Security

- `SECURITY.md` states the supported release line, the reference-implementation
  boundary, and which reports are and are not vulnerabilities.

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
