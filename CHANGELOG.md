# Changelog

Format follows Keep a Changelog. Versions follow semantic versioning, applied
independently to each artefact under `spec/`.

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
