# Provenance

Why every claim in a passport carries a method, a source and a time — and what to do when
claims disagree, when nothing was measured, or when you must not disclose the source.

## The core idea

Consider two records of the same garment.

~~~json
{ "fibreType": "polyester", "percentage": 95 }
~~~

~~~json
{
  "observationId": "urn:example:observation:000042-polyester",
  "fibreType": "polyester",
  "percentage": 95,
  "percentageBasis": "mass",
  "valueStatus": "supplied",
  "method": "labQuantitativeIso1833",
  "sourceOrganisationId": "urn:example:org:lab-a",
  "sourceSystemId": "urn:example:system:lab-lims",
  "observedAt": "2042-06-18T11:02:10Z"
}
~~~

Both say "95% polyester". Only the second is usable, because only the second answers the
questions a downstream party actually has:

- **Is this a measurement or a transcription?** `labQuantitativeIso1833` and
  `labelDeclaration` are both legitimate values and mean entirely different things.
- **Ninety-five per cent of what?** `mass` and `declaredLabel` are not comparable.
- **Who is accountable if it is wrong?** `sourceOrganisationId`.
- **Is it still current?** `observedAt` — a value observed before dyeing is not a statement
  about the finished article.
- **Can I refer to this specific claim later?** `observationId`, so a sorting decision or a
  correction can cite it rather than "the composition".

The first record is a number with no owner. It cannot be verified, superseded, contested
or audited. The profile makes it unrepresentable: the schema requires `observationId`,
`fibreType`, `valueStatus`, `method`, `sourceOrganisationId` and `observedAt` on every
material observation.

## The six mandatory members

| Member | Type | What it establishes |
| --- | --- | --- |
| `observationId` | URI | Identity of the claim, so it can be cited and superseded |
| `fibreType` | `fibre-type` token | What is being claimed about |
| `valueStatus` | `value-status` token | Whether there is a value at all, and why not if there is not |
| `method` | `method` token | How the claim was arrived at |
| `sourceOrganisationId` | URI | Who asserts it |
| `observedAt` | RFC 3339 with offset | When it was true |

Optional and often decisive: `percentage` + `percentageBasis`, `confidence`
(`{value, scale}`), `sourceSystemId` (which instrument or system), `evidenceRef` (a
pointer to a report, certificate or record).

## `valueStatus`: five distinct states

`valueStatus` is the field that keeps absence honest. The vocabulary distinguishes states
that implementations routinely collapse into "null", which then cannot be told apart.

| Token | Meaning |
| --- | --- |
| `supplied` | A value is present in this observation |
| `notMeasured` | The property was not determined on this occasion |
| `unknown` | It was looked for and could not be determined |
| `notApplicable` | The property does not apply to this subject |
| `withheld` | A value exists but is not disclosed to this caller |

Schema rule: when `valueStatus` is anything other than `supplied`, `percentage` is
**forbidden**. You cannot write "unknown, 62%".

`withheld` is also used by the access layer. A caller who may know that a field exists but
may not read its value receives an explicit withheld marker rather than nothing at all —
because a consumer that sees nothing would conclude the data was never collected, which is
a different and false statement. See [Security model](security.md).

## `method`: how the claim was produced

The `method` vocabulary separates declaration from measurement, and separates measurement
technologies from one another:

| Token | Kind |
| --- | --- |
| `labelDeclaration` | Read from the sewn-in label — a declaration, not a measurement |
| `supplierDeclaration` | Asserted by an upstream party |
| `computedInherited` | Derived from a parent model or batch record, not observed on this unit |
| `manualInspection` | Human assessment |
| `opticalRecognition` | Image-based classification |
| `nirSpectroscopy` | Near-infrared spectroscopy |
| `hyperspectralImaging` | Hyperspectral imaging |
| `labQuantitativeIso1833` | Quantitative laboratory analysis |

`computedInherited` deserves attention: it is how you honestly express an item-level
passport whose composition actually came from the model record. Recording it as a
measurement would overstate what you know.

## Conflicting observations: append, never merge

When a second technology disagrees with the first, the profile's answer is to keep both.

~~~json
"materialObservations": [
  { "observationId": "urn:example:observation:000042-a",
    "fibreType": "polyester", "percentage": 95, "percentageBasis": "mass",
    "valueStatus": "supplied", "method": "labQuantitativeIso1833",
    "sourceOrganisationId": "urn:example:org:lab-a",
    "observedAt": "2042-06-18T11:02:10Z" },
  { "observationId": "urn:example:observation:000042-b",
    "fibreType": "polyester", "percentage": 93.4, "percentageBasis": "mass",
    "valueStatus": "supplied", "method": "nirSpectroscopy",
    "sourceOrganisationId": "urn:example:org:sorter-a",
    "sourceSystemId": "urn:example:system:nir-line",
    "confidence": { "value": 0.86, "scale": "unitInterval" },
    "observedAt": "2044-01-16T09:03:00Z" }
]
~~~

Do **not** overwrite, average, or "reconcile" these. Each is a true statement about what a
particular party observed with a particular method at a particular time. Averaging them
produces a number nobody measured, attributed to nobody.

The validator supports this directly: the composition rule applies **within an observation
set** — same source organisation, source system, method and time — and never across sets.
The two observations above sum to 188.4 and are entirely valid, because they belong to
different sets. See [`valid-two-technologies-disagree.json`](../examples/fixtures/valid-two-technologies-disagree.json)
and `observation_sets()` in [`validation.py`](../src/sort4circ_dpp/validation.py).

The consumer decides which claim to act on, using the method, the source, the time and the
confidence. That decision is a policy question, and the profile deliberately does not make
it for you.

## Confidence

`confidence` is `{"value": 0.86, "scale": "unitInterval"}`. The scale is mandatory, from
the `confidence-scale` vocabulary (`unitInterval` or `percent`), because `0.86` and `86`
are the same confidence in different scales and an unlabelled number is ambiguous. The
negative fixture `invalid-confidence-without-scale.json` exercises this.

Confidence is meaningful only relative to the method that produced it. A `0.86` from one
instrument family is not comparable with a `0.86` from another. Do not aggregate
confidences across methods.

## Time: observed, recorded, and why both

- `observedAt` on an observation — when the claim was true of the item.
- `eventTime` and `recordedAt` on a lifecycle event — when it happened, and when the system
  was told.

These diverge routinely: an offline reader uploads hours later, a laboratory result is
entered the next day. If you store only one, you cannot reconstruct what was known at
decision time, which is exactly the question an audit or an incident review asks.

All timestamps must be RFC 3339 **with an explicit offset**. A timestamp without one is
rejected (`invalid-timestamp-without-offset.json`), because a local time with no offset is
not a point in time.

## Provenance across the whole record

Provenance is not only an observation-level concern:

| Where | Members |
| --- | --- |
| Record | `responsibleOperatorId`, `createdAt`, `updatedAt`, `recordVersion` |
| Observation | `method`, `sourceOrganisationId`, `sourceSystemId`, `observedAt`, `evidenceRef` |
| Lifecycle event | `actorOrganisationId`, `sourceSystemId`, `eventTime`, `recordedAt`, `facilityId`, `readPointId` |
| Carrier binding | `boundBy`, `boundAt`, `closedAt`, `bindingStatus` |
| Sorting decision | `decidedBy`, `decidedAt`, `basedOnObservations`, `ruleSetId`, `ruleSetVersion` |
| Environmental value | `responsibleOrganisationId`, `method`, `factorSource`, `factorVersion`, `allocationRule` |
| Integrity evidence | `canonicalisation`, `digestAlgorithm`, `subjectVersion`, `ledgerNetworkId` |
| Source systems | `identity.sourceRecordId`, `identity.sampleId` |

Every one of these answers "who said this, on what basis, and when". Integrity evidence
([Integrity](integrity.md)) adds a different guarantee on top: that the content has not
changed since a given version. Provenance says who claimed it; integrity says it has not
been altered. Neither substitutes for the other.

## Practical rules

1. **Never write a value without its method, source and time.** If you cannot supply them,
   you do not yet have an observation.
2. **Never invent a residual** to make percentages reach 100.
3. **Never merge disagreeing observations.** Append.
4. **Never reuse an `observationId`** for a different claim.
5. **Never move `observedAt`** to the ingestion time. Use `recordedAt`-style separation.
6. **Do not put sensitive detail into provenance identifiers.** `sourceSystemId` and
   `evidenceRef` are visible to the roles that can read the record; they must not embed a
   person, a customer, an internal hostname or a credential.

## Related pages

- [Create your first DPP](first-dpp.md) — provenance in the context of a whole record
- [Vocabularies](vocabularies.md) — the `method`, `value-status` and `confidence-scale`
  token sets
- [Validation](validation.md) — the negative fixtures that enforce these rules
- [Enterprise integration](enterprise-integration.md) — deriving provenance from ERP/MES
  fields that do not have it
