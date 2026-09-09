# Enterprise integration

Tier 2. How to populate passports from the systems you already run — ERP, PLM, MES, WMS,
LIMS or a plain database — without inventing data you do not have.

The examples below use generic field names. They describe no specific product, vendor or
deployment.

## The shape of the problem

Your source systems were built to run your business, not to publish passports. They will
typically have:

- codes in your own scheme (`MAT-4471`), not in a controlled vocabulary;
- values with no method, no source and no observation time — someone typed them once;
- units that are implicit, or inconsistent between tables;
- rows that are simply wrong or incomplete.

Translation is therefore not a field-rename exercise. It is a process that must add
provenance, map vocabulary, normalise units, and **refuse** the rows it cannot honestly
translate.

## A worked mapping

| Source field | Example value | DPP target | Notes |
| --- | --- | --- | --- |
| `article_no` | `4471-BLU-M` | `identity.itemId` or `identity.modelId` | Granularity depends on whether the number identifies a design or a unit |
| `serial_no` | `SN-00019233` | `identity.itemId` | Present ⇒ item granularity is available |
| `lot_no` | `LOT-2044-03` | `identity.batchId` | Use when no serial exists |
| `article_no` (source key) | `4471-BLU-M` | `identity.sourceRecordId` | **Preserve the original**, unchanged |
| `product_group` | `HOME_FLAT` | `product.articleClass` | Vocabulary mapping required |
| `construction` | `W` | `product.fabricConstruction` | `W` → `woven` |
| `colour_code` | `NAVY-07` | `product.colourPrimary` | Many-to-one onto the `colour-family` tokens |
| `net_weight` + `weight_uom` | `420`, `G` | `product.mass` | `{"value": 0.42, "unit": "kg"}` |
| `material_code` | `MAT-4471` | a **material observation** | See below |
| `material_pct` | `62` | `materialObservations[].percentage` | Needs an explicit `percentageBasis` |
| `bom_line` | | `components[]` | `componentType` is vocabulary-mapped |
| `goods_receipt` transaction | | `lifecycleEvents[]` with `eventType: receipt` | `eventTime` from the transaction, `recordedAt` from your ingestion |
| `lab_result_id` | | `materialObservations[].evidenceRef` | Points back into the LIMS record |

### `material_code` is the interesting one

An ERP material code does not become a field. It becomes an **observation**, and the
translation has to supply the four things the ERP row does not contain:

~~~json
{
  "observationId": "urn:example:observation:erp-4471-000019233-1",
  "fibreType": "cotton",
  "percentage": 62,
  "percentageBasis": "declaredLabel",
  "valueStatus": "supplied",
  "method": "supplierDeclaration",
  "sourceOrganisationId": "urn:example:org:manufacturer-a",
  "sourceSystemId": "urn:example:system:erp",
  "observedAt": "2044-02-11T00:00:00+01:00",
  "evidenceRef": "urn:example:record:erp-material-4471"
}
~~~

- `fibreType` comes from your mapping table (`MAT-4471` → `cotton`), not from the code.
- `method` is the honest one: a value maintained in an ERP master record because a supplier
  declared it is `supplierDeclaration`. It is **not** `labQuantitativeIso1833`. If the
  figure originally came from a laboratory report, then the laboratory is the source and
  the report is the `evidenceRef` — but only if you can actually establish that link.
- `percentageBasis` must be decided, not assumed. If your ERP field records what the label
  says, it is `declaredLabel`. Only call it `mass` if it really is a mass fraction.
- `observedAt` should be the date the value was established, from the source record's own
  audit fields where they exist. Do not substitute the ingestion timestamp — that is
  `recordedAt` on an event, and it means something different.
- `sourceSystemId` names the system, which lets a consumer weigh an ERP-sourced claim
  against a laboratory-sourced one.

If a value has been in the master record since 2019 and nobody can say where it came from,
say so: use `method: supplierDeclaration` with the best `observedAt` you can defend, or
record `valueStatus: notMeasured` and no percentage. Do not manufacture provenance. See
[Provenance](provenance.md).

## Units

`mass` is `{value, unit}`. A bare number is never a quantity in this profile.

- convert explicitly and record the **converted** value with its unit;
- keep the conversion in the mapping table, versioned, not scattered across code;
- when a source unit is missing or unrecognised, that is a rejection, not a default.
  `S4C-MAP-UNIT-CONVERSION-FAILED` exists for it.

Guessing that a bare `420` is grams because it usually is will eventually be wrong by three
orders of magnitude in a published passport.

## Version your mapping

The mapping table is a specification asset in your own system, not configuration. Version
it, and record which version produced a record:

~~~json
{
  "mappingVersion": "1.3.0",
  "sourceSystemId": "urn:example:system:erp",
  "rules": [
    { "sourceField": "product_group", "sourceValue": "HOME_FLAT",
      "target": "product.articleClass", "targetToken": "homeTextileFlat" },
    { "sourceField": "material_code", "sourceValue": "MAT-4471",
      "target": "materialObservations[].fibreType", "targetToken": "cotton" }
  ]
}
~~~

Why it matters: when someone asks in eighteen months why a batch of passports says
`homeTextileFlat`, the answer must be "mapping version 1.3.0 rule 12", not "someone changed
a lookup". A silent mapping change rewrites the meaning of every record produced after it,
with no trace.

Record the mapping version somewhere durable — in your own pipeline metadata, in the
`sourceSystemId` you mint, or in an `evidenceRef` pointing at the mapping release. The
profile does not reserve a field for it; that is a deployment decision.

The repository's own JSON ↔ XML ↔ RDF mapping
([`spec/mappings/dpp-mapping-1.0.0.json`](../spec/mappings/dpp-mapping-1.0.0.json)) is a
worked example of the discipline: every row carries a mapping identifier, a version, a
datatype, an obligation, a controlled vocabulary reference and an explicit status, and the
CSV rendering is generated from it rather than maintained by hand.

## Reject and quarantine — do not coerce

The most important behaviour in an integration is what it does with a row it cannot
translate. Three outcomes, and only three:

| Outcome | When | What you do |
| --- | --- | --- |
| **Translate** | Every mandatory member can be honestly populated | Emit the passport or the append |
| **Quarantine** | A source value has no target token, a unit is missing, a mandatory member has no defensible value | Hold the row, report it, do not emit |
| **Reject** | The source row is structurally invalid or internally contradictory | Fail the row, report it |

Never coerce. The named failures are:

| Reason code | Condition |
| --- | --- |
| `S4C-MAP-NO-TARGET-RULE` | No mapping rule exists for this source field |
| `S4C-MAP-VOCAB-UNMAPPED` | The source value has no target vocabulary token |
| `S4C-MAP-UNIT-CONVERSION-FAILED` | The unit is missing or cannot be converted |
| `S4C-PAYLOAD-VOCAB-INVALID` | A token was emitted that is not in the vocabulary version |

A quarantine queue that nobody reads becomes a silent data-loss channel, so make the
quarantine count a monitored figure. It is also your best signal about where the mapping
table is incomplete: a source value appearing repeatedly in quarantine is a missing rule,
not a bad row.

A partially translatable row is often still worth emitting. A passport with `articleClass`
and an observation carrying `valueStatus: notMeasured` is a true and useful record. A
passport with a fabricated composition is neither.

## Pipeline shape

~~~
source extract
  → structural validation (does the row have what the mapping needs?)
  → vocabulary mapping (versioned table; unmapped ⇒ quarantine)
  → unit normalisation (explicit; unconvertible ⇒ quarantine)
  → provenance assembly (method, source, system, time)
  → profile validation (schema + vocabulary + cross-field)
  → emit: POST /v1/dpps, or an append to an existing passport
~~~

Validate **before** you emit. `validate_payload()` is importable, so a non-HTTP pipeline
can run exactly the checks the API would run:

~~~python
from sort4circ_dpp.validation import validate_payload
from sort4circ_dpp.reasons import DppError

try:
    validate_payload(candidate)
except DppError as exc:
    quarantine(row, exc.code, exc.fields)
~~~

## Incremental updates

Source systems change rows. The passport model is append-only where it matters, so map
changes accordingly:

| Source change | Passport action |
| --- | --- |
| A new laboratory or scan result | **Append** an observation. Do not replace the old one. |
| A corrected master-data attribute (`product.*`) | `PATCH` with `If-Match`, which advances `recordVersion` |
| A goods movement or process transaction | **Append** a lifecycle event |
| A row deleted in the source | Do **not** delete the passport. Set `status` and, where a replacement exists, `supersededBy` |
| A re-run of yesterday's batch | Same `Idempotency-Key` per real-world operation ⇒ no duplicates |

Derive idempotency keys from the source system's own stable keys — a transaction number, a
document line — not from a fresh UUID per attempt. That way a replayed nightly load is a
no-op instead of a duplication event.

## Which role your integration should hold

Integrations authenticate as a role from
[`spec/access-matrix.json`](../spec/access-matrix.json). For an ERP/MES feed, `brand` (full
write) or `pssrSystem` (resolve, read the sorting view, write observations and events,
but **not** create or patch passports) are the usual choices. Grant the narrower one unless
the pipeline genuinely needs to create passports.

`DemoAuth` header identities are for local demonstration only. A production integration
needs a real identity provider — see [Security model](security.md) and
[Customisation](customisation.md).

## Related pages

- [Provenance](provenance.md) — what your mapping must add
- [Vocabularies](vocabularies.md) — the token sets you are mapping onto, and how to extend
  them
- [Lifecycle events](lifecycle-events.md) — turning transactions into events
- [Sorting integration](sorting-integration.md) — the same discipline on the operational side
- [Representations and semantics](interoperability.md) — if your exchange partner needs XML
  or RDF
