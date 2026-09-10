# Changelog

Format follows Keep a Changelog. Two version numbers are tracked separately:
the **repository release** (this file's headings) and the **SORT4CIRC DPP
implementation profile** version carried by the artefacts under `spec/`.

## [1.3.1] - 2026-09-09

Patch release. Documentation, licensing and metadata corrections from an external
pre-publication review. No specification asset, schema, vocabulary, ontology, mapping,
XSD, OpenAPI contract or reason code is changed, and the DPP implementation profile
remains at 1.0.0.

### Added

- EU funding statement in `README.md`, recording Horizon Europe grant agreement number
  101181988 and the standard disclaimer of Union responsibility.
- European Union emblem at `docs/assets/eu-emblem.svg`, displayed in the README funding
  section. Article 17.2 of the Horizon Europe grant agreement requires the emblem
  alongside the funding statement and the disclaimer. The file is the unmodified
  full-colour SVG from the European Union's official visual identity downloads.
- A reserved-rights section in `LICENSING.md` for third-party material that carries
  neither component grant, and a guard in `tests/test_licensing.py` asserting that no
  component grant is claimed over the emblem.
- Named software copyright notice in `LICENSE`, replacing the unfilled Apache appendix
  placeholder. The software copyright holder is Constructor University gGmbH.

### Fixed

- Restored four documentation statements that a previous README revision had rewritten,
  reinstating the normative-scope and release-identification wording asserted by
  `tests/test_public_release.py`.
- Removed a self-contradiction in `CITATION.cff`, where `date-released` was set while an
  adjacent comment stated that no date had been recorded.
- Corrected the statement in `LICENSING.md` about the scope of the coverage map: the
  repository's Git history is public, and the map makes no licence grant over material
  reachable only through earlier commits.

### Changed

- `LICENSING.md` now states the current licensing position, that the software component is
  licensed under Apache-2.0 and that Apache-2.0 is the licence in force, in place of
  narrating an earlier licence change and its reversal.
- `PUBLICATION_BOUNDARY.md` and `LICENSING.md` record that the publication boundary review
  was applied on 2026-09-09 and covers the repository as published at release v1.3.0, and
  that the automated checks support that review rather than replacing it. The record is
  anchored to the review date so that it remains verifiable independently of the release
  in which the statement ships.
- Repository release version advanced to 1.3.1 in `README.md`, `pyproject.toml`,
  `src/sort4circ_dpp/config.py`, `CITATION.cff`, `SECURITY.md` and
  `docs/versioning-and-migration.md`. The DPP implementation profile remains at 1.0.0 and
  no specification asset version changed.

## [1.3.0] - 2026-09-09

Repository release 1.3.0 implements the SORT4CIRC DPP implementation profile
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
- Package metadata declares the repository release version (1.3.0) separately
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

### Reconciled with the published 1.2.0 line

Release 1.2.0 was published while this developer-focused work was in progress. 1.3.0 is
the union of both, not a replacement for either. Carried forward from 1.2.0:

- **Ontology 1.0.1** — an additive patch (33 classes, 109 properties, 585 triples): two
  object properties and ten datatype properties added, nothing removed or changed. The
  other specification assets remain at 1.0.0; asset versions are independent.
- **SPARQL conformance queries** — six released queries under `spec/queries/` with an
  expected-result fixture, exercised against the RDF projection.
- **Governance record schemas** — selection and standards-deviation schemas with
  unpopulated templates under `spec/governance/`. No name, approval, threshold or
  measurement is supplied or inferred.
- **XML exchange** — `exchange.py`, XML content negotiation on `/v1`, the released
  XSD 1.1 at `spec/schemas/dpp-1.0.0.xsd`, and two XML fixtures.
- **Packaged specification resources** — `src/sort4circ_dpp/_spec/` so an installed wheel
  resolves the profile without a source checkout.
- **RFC 9457 body-validation normalisation**, the always-on read-projection staleness
  guard, the reference Besu ledger adapter with its fail-closed verification, `rdflib` and
  `xmlschema` as runtime dependencies, and the wider CI matrix.

### One normative exchange path

Two parallel JSON/XML/RDF mappings existed across the two lines. They are now one:

- the **124-row term-level mapping package** is normative, and its `xmlXPath` column was
  regenerated onto the published XML profile;
- the **published XML namespace `https://data.sort4circ.eu/vocabulary/` is unchanged**, as
  is the document shape, so previously produced XML remains valid;
- `exchange.py` is the single serialiser; `mapping.py` delegates XML to it and owns the RDF
  projection. The partial 21-row mapping and the competing XSD were retired.
- The XSD now accepts an empty optional list, and the parser reads an empty wrapper back as
  an empty array, so a present-but-empty array survives a JSON→XML→JSON round trip. This
  relaxation accepts strictly more documents than before.

### Security

- No configuration in this repository enables header authentication by default. The
  previous development compose file, which set `S4C_ALLOW_HEADER_AUTH=1` and published the
  service on all interfaces, is replaced by `docker/compose.example.yml`: fail-closed,
  bound to `127.0.0.1`, read-only, all capabilities dropped, `no-new-privileges`.
- No Besu service ships in any default configuration, and no default binds a JSON-RPC
  endpoint to `0.0.0.0` or opens CORS. The Besu adapter is optional, imported by nothing,
  and configured only through environment variables.
- Benchmark records keep their workload, seed, run count, payload size, latency
  percentiles and digest, and no longer carry CPU model, core count, memory, kernel or
  build strings, or runner identifiers.
- Project-status traceability was replaced by organisation-neutral requirement →
  asset → implementation → test rows using implemented / specified / optional /
  deployment-dependent / external validation required / outside reference implementation.

### Security

- `SECURITY.md` states the supported release line, the reference-implementation
  boundary, and which reports are and are not vulnerabilities.

## [1.2.0] - 2026-08-17

Published release. Specification artefacts retain independent semantic versions:
this release advanced the ontology to 1.0.1 and the OpenAPI contract to 1.1.0
while the DPP JSON Schema stayed at 1.0.0.

### Specification

- Added XML Schema 1.1, XML fixtures, a versioned mandatory-field JSON/XML/RDF
  mapping, and the six-subject SPARQL conformance query package.
- Released ontology `sort4circ-1.0.1`, adding terms required by that mapping for
  passport state, responsibility, identity, component, event, sorting and
  environmental projections. Existing identifiers and meanings are unchanged;
  records conforming to 1.0.0 require no migration.
- Added environmental-selection governance controls and open EN 18223 deviation
  controls with unpopulated templates, machine-checked separation of duties and
  deployment gates.
- Corrected the material-divergence query to return one ordered pair when
  different methods report different percentages for the same fibre. The actual
  Annex G values 95 and 93.4 are the positive conformance fixture.

### Implementation and evidence

- Added negotiated XML API support with XSD 1.1 validation while retaining JSON
  as the existing representation. The independently versioned OpenAPI contract
  advances to 1.1.0 for this backward-compatible addition; the `/v1` path and
  DPP JSON Schema version remain unchanged.
- Added RDF derivation, JSON/XML/RDF round-trip tests and released SPARQL
  conformance queries tied to expected-result fixtures.
- Added read-index reconstruction and write-prohibition controls, plus
  repository-wide guards against superseded terminology and unselected
  serialisation profiles.
- Expanded requirement traceability across specification, implementation,
  governance and conformance, recording for each row whether it is implemented,
  specified, optional, deployment-dependent or requires external validation.
- Recorded the limits of the reference implementation rather than manufacturing
  evidence for claims it does not support.

## [1.1.2] - 2026-08-13

Correctness, packaging, reproducibility and documentation maintenance for the
reference implementation. Normative specification artefacts are unchanged.

### Fixed

- Reused one correlation identifier throughout each request, normalized body
  validation errors, scoped idempotency keys by operation and resource, and
  made unsupported Besu digest verification fail closed as unverifiable.

### Packaging and reproducibility

- Packaged the runtime specification resources, added an installed-wheel smoke
  check, constrained CI dependency resolution, and made pytest and generated
  OpenAPI checks portable across Windows and Linux.

### Documentation

- Aligned API, Besu, persistence, idempotency, D4.3/project-context,
  licensing, citation, security-reporting and README claims with the current
  reference implementation.

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
