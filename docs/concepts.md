# Data model

The structure of a passport record, and the reasoning behind the parts that are not
obvious. The machine-readable definition is
[`spec/schemas/dpp-1.0.0.schema.json`](../spec/schemas/dpp-1.0.0.schema.json); this page
explains it.

All examples are synthetic. See the scoping notice in the [documentation index](index.md).

## Shape of a record

A passport is a single JSON object, versioned, with `additionalProperties: false` at every
level. Unknown members are rejected rather than ignored, so a typo in a field name is an
error instead of silent data loss.

| Member | Required | Kind | Purpose |
| --- | --- | --- | --- |
| `dppId` | ● | URI | Identifies the record |
| `schemaVersion` | ● | semver | Which profile release the payload conforms to |
| `recordVersion` | ● | integer ≥ 1 | Monotonic version, advanced by every committed change |
| `status` | ● | vocabulary | `draft`, `active`, `superseded`, `retired` |
| `createdAt`, `updatedAt` | ● | timestamp | RFC 3339 **with an explicit offset** |
| `responsibleOperatorId` | ● | URI | Organisation accountable for the record |
| `identity` | ● | object | What the record is about, and at what granularity |
| `product` | ● | object | Article-level characteristics |
| `materialObservations` | ● | array, ≥ 1 | Attributed material claims |
| `supersededBy` | | URI | Replacement record, when `status` is `superseded` |
| `registryIdentifier` | | string | Registration reference in an external registry |
| `accessPolicyVersion` | | semver | Which access-matrix release applied |
| `carriers` | | array | Data-carrier bindings and their lifecycle |
| `components` | | array | Bill of materials, hierarchical |
| `lifecycleEvents` | | array | What happened to the item, and when |
| `sortingDecisions` | | array | Sorting outcomes and the rules that produced them |
| `environmentalValues` | | array | Quantified environmental metrics with full method context |
| `integrity` | | array | Integrity evidence entries |

The first nine members give you a Tier 1 Core Passport. Everything after `accessPolicyVersion`
is Tier 2 or Tier 3.

## Identity: record, subject, granularity

`dppId` names the record. `identity` names the subject the record is about. They are
separate so that a record can be superseded, migrated or reissued without changing what it
describes.

`identity.granularity` is one of `model`, `batch` or `item`, and the schema conditionally
requires the matching identifier (`modelId`, `batchId`, `itemId`). Optional members:
`epc` (the legacy carrier-identifier field), `sampleId` and `sourceRecordId`.

Full treatment: [Identifiers](identifiers.md).

## Product

`product` requires only `articleClass`. Optional members are `fabricConstruction`,
`colourPrimary`, `sizeDesignation`, `mass`, `condition`, `qualityGrade` and
`technicalFlags`.

Two modelling rules apply throughout the profile and show up here first:

- **Coded fields are vocabulary tokens, not free text.** `articleClass`,
  `fabricConstruction`, `colourPrimary`, `condition` and each `technicalFlags` entry are
  validated against a published vocabulary version and rejected — never coerced — if
  absent from it.
- **A bare number is never a quantity.** `mass` is `{"value": 0.42, "unit": "kg"}`. A
  number without a unit cannot be safely aggregated by a consumer, so the schema does not
  permit one.

`technicalFlags` records properties that change how a machine should treat the item: a
metal hard point, a pigment that defeats an optical technology, a laminate. An empty array
is a positive statement that no flags were recorded, which is not the same as the member
being absent.

## Material observations

`materialObservations` is **not** a composition field. It is an append-only sequence of
attributed claims, each of which carries its own method, source and time.

Required on every observation: `observationId`, `fibreType`, `valueStatus`, `method`,
`sourceOrganisationId`, `observedAt`. Optional: `percentage` (which then requires
`percentageBasis`), `confidence` as `{value, scale}`, `sourceSystemId` and `evidenceRef`.

Two schema rules encode the model's core commitments:

1. `percentage` requires `percentageBasis`. A percentage whose basis is unstated cannot be
   compared with another percentage.
2. When `valueStatus` is anything other than `supplied`, `percentage` is **forbidden**.
   "Unknown, 62%" is not expressible.

### Observation sets and the composition rule

An **observation set** is the group of observations sharing the same
`sourceOrganisationId`, `sourceSystemId`, `method` and `observedAt` — that is, one
measurement occasion.

Within a set, supplied `mass` fractions may not exceed 100 plus a 0.5 percentage-point
tolerance (`COMPOSITION_TOLERANCE` in
[`validation.py`](../src/sort4circ_dpp/validation.py)). Exceeding it means double
counting, a wrong basis, or two occasions wrongly merged into one — all three are errors.

A set summing to less than 100 is **accepted**. Partial characterisation is a normal state.
Requiring the sum to reach 100 would force implementations to fabricate a residual, and a
fabricated residual is indistinguishable from a measurement afterwards.

The rule is applied per set and never across sets. Summing across sets would make a second
opinion look like a contradiction: a laboratory result of 95% polyester plus 5% elastane,
alongside a later near-infrared result of 93.4% polyester, sums to 193.4 and is entirely
correct.

See [Provenance](provenance.md).

## Components

`components` expresses a bill of materials as a flat array with `parentComponentId`
references, so an arbitrary containment hierarchy — garment → fabric → yarn → fibre, plus
trims — is representable without nesting the JSON.

Each component requires `componentId` and `componentType` (a vocabulary token). Optional:
`parentComponentId`, `materialObservationRefs` (URIs of observations in this record that
describe this component), `mass` and `separable`.

`separable` is the field a recycler acts on: it says whether the component can be removed
in practice, which determines whether the item is a single-stream input or needs
dismantling.

## Lifecycle events

`lifecycleEvents` records what happened to the item. Required on every event: `eventId`,
`eventType`, `eventTime`, `eventTimeZoneOffset`, `recordedAt`, `actorOrganisationId`,
`sourceSystemId`.

`eventTime` and `recordedAt` are different facts: when the thing happened, and when the
system was told. They diverge routinely — an offline scanner uploads hours later — and
conflating them destroys the ability to reconstruct what was known at decision time.
`eventTimeZoneOffset` is carried separately because local time is often the operationally
meaningful frame even when the timestamp is normalised.

`transformation` events additionally require `inputRefs` and `outputRefs`, because a
transformation that does not say what went in and what came out is not traceable.

Corrections use `correctsEventId` rather than deletion. See
[Lifecycle events](lifecycle-events.md).

## Sorting decisions

`sortingDecisions` records outcomes, not just categories. Required: `decisionId`,
`basedOnObservations`, `ruleSetId`, `ruleSetVersion`, `sortingCategory`, `decidedAt`,
`decidedBy`, `outcomeStatus`.

The mandatory `basedOnObservations` and `ruleSetVersion` exist so a decision can be
replayed: you can see exactly which claims and which rule release produced it. The optional
`basedOnRecordVersion` pins the record state as well. `outcomeStatus` is `issued`,
`confirmed`, `rejected` or `overridden`, and an `overridden` decision must carry an
`overrideReason`.

See [Sorting integration](sorting-integration.md).

## Environmental values

`environmentalValues` is deliberately demanding. Every entry requires `metricType`,
`quantity`, `functionalUnit`, `systemBoundary`, `processStage`, `geography`,
`periodStart`, `periodEnd`, `method`, `allocationRule`, `factorSource`, `factorVersion`
and `responsibleOrganisationId`.

That is thirteen mandatory members for one number, and the reason is simple: an
environmental figure without its functional unit, boundary, allocation rule and factor
version is not comparable with any other figure. Permitting a bare value would produce a
field that looks aggregatable and is not.

## Integrity

`integrity` carries evidence entries. Required: `evidenceId`, `subjectRef`,
`subjectVersion`, `canonicalisation`, `digestAlgorithm`, `digestValue` (64 lower-case hex
characters) and `evidenceState`. Optional: `createdAt`, `ledgerNetworkId`,
`transactionRef`, `confirmedAt`, `attempts`, `lastReasonCode`.

The array is entirely optional. A Tier 1 passport has no `integrity` member at all. See
[Integrity](integrity.md).

## Versioning and append-only semantics

- `recordVersion` advances on every committed change; earlier versions are retained so a
  digest or a decision can be checked against the exact content that produced it.
- `materialObservations`, `lifecycleEvents`, `sortingDecisions` and `integrity` are
  **append-only**. The reference implementation refuses to modify or remove an existing
  entry through `PATCH` and returns `S4C-STATE-APPEND-ONLY-VIOLATION`.
- Superseding a record sets `status` to `superseded` and `supersededBy` to the replacement.
  The old record is not deleted.
- The `schemaVersion` in the payload and `PROFILE_VERSION` in
  [`config.py`](../src/sort4circ_dpp/config.py) are both `1.0.0` — the version of the
  normative DPP implementation profile, not of this repository. The API route prefix `/v1` is an
  independently versioned exchange-route major.

See [Versioning and migration](versioning-and-migration.md).

## What validity does and does not tell you

A record that passes schema, vocabulary and cross-field validation is well-formed and
interoperable. It is not evidence that any claim inside it is factually accurate. The
profile's job is to make every claim attributable so that a consumer can judge it; judging
it remains the consumer's responsibility.

## Related pages

- [Create your first DPP](first-dpp.md) — the same structure, built up step by step
- [Identifiers](identifiers.md) · [Provenance](provenance.md) · [Vocabularies](vocabularies.md)
- [Validation](validation.md) — how the rules are enforced
- [Representations and semantics](interoperability.md) — the same model in XML and RDF
