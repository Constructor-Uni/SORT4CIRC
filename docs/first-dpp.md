# Create your first DPP

This walkthrough builds a passport field by field and explains why each field exists. By
the end you will have a Tier 1 Core Passport: a record with persistent identity, product
information, attributed material observations, controlled values and a bound data carrier.

Prerequisites: the install from [Getting started](getting-started.md). All values below
are synthetic.

## The shortest possible start

~~~sh
python -m sort4circ_dpp.cli example > my-first-dpp.json
python -m sort4circ_dpp.cli validate my-first-dpp.json    # -> VALID
~~~

That is a complete, valid passport. The rest of this page explains what is in it and what
you should change for your own product.

## The minimum valid record

A passport must carry ten members. Everything else is optional and additive.

~~~json
{
  "dppId": "urn:example:dpp:000001",
  "schemaVersion": "1.0.0",
  "recordVersion": 1,
  "status": "active",
  "createdAt": "2042-02-11T08:00:00Z",
  "updatedAt": "2042-02-13T10:30:00Z",
  "responsibleOperatorId": "urn:example:org:manufacturer-a",
  "identity": {
    "granularity": "item",
    "itemId": "urn:example:item:000001",
    "epc": "urn:example:carrier:000001",
    "sampleId": "SYNTH-0001"
  },
  "product": {
    "articleClass": "homeTextileFlat",
    "fabricConstruction": "woven",
    "colourPrimary": "light",
    "technicalFlags": []
  },
  "materialObservations": [
    {
      "observationId": "urn:example:observation:000001-cotton",
      "fibreType": "cotton",
      "percentage": 62,
      "percentageBasis": "declaredLabel",
      "valueStatus": "supplied",
      "method": "supplierDeclaration",
      "sourceOrganisationId": "urn:example:org:manufacturer-a",
      "observedAt": "2042-02-12T09:00:00Z"
    },
    {
      "observationId": "urn:example:observation:000001-flax",
      "fibreType": "flax",
      "percentage": 38,
      "percentageBasis": "declaredLabel",
      "valueStatus": "supplied",
      "method": "supplierDeclaration",
      "sourceOrganisationId": "urn:example:org:manufacturer-a",
      "observedAt": "2042-02-12T09:00:00Z"
    }
  ]
}
~~~

This is [`examples/fixtures/valid-minimum.json`](../examples/fixtures/valid-minimum.json).

## Step 1 — Passport identity

| Field | Meaning |
| --- | --- |
| `dppId` | The identifier **of the record**. Must be an absolute URI, and is stable for the life of the passport. |
| `schemaVersion` | Which profile release the payload conforms to. Consumers use it to decide how to read the document. |
| `recordVersion` | A monotonically increasing integer. Every committed change advances it. Version 1 is the record as first created. |
| `status` | A `passport-status` vocabulary token — `active` for a live record. |
| `createdAt` / `updatedAt` | RFC 3339 timestamps **with an explicit offset**. A timestamp without an offset is rejected. |
| `responsibleOperatorId` | The organisation accountable for the record, as an absolute URI. |

Use your own URI namespace in production. `urn:example:` and `https://example.org/` are
reserved for documentation and must never appear in a real deployment. Do not put a
customer name, a person, an order number or anything else you would not publish inside an
identifier — identifiers travel further than the data behind them.

## Step 2 — What the passport is about, and at what granularity

`identity` names the **subject**: the physical thing the record describes. This is not the
same as `dppId`, which names the record. Keeping them separate is what lets you reissue,
supersede or migrate a record without changing what it is about.

`granularity` declares how specific the subject is, and the schema then requires the
matching identifier:

| `granularity` | Required | Use when |
| --- | --- | --- |
| `model` | `modelId` | The record describes a product design or SKU, and every unit is treated as identical. |
| `batch` | `batchId` | The record describes a production lot or bale, and units are not individually distinguished. |
| `item` | `itemId` | The record describes one physical unit. Required for item-level sorting, reuse and resale. |

Choose the coarsest granularity that answers the questions you actually need to answer.
Moving from `model` to `item` later means issuing new passports, not editing this field.
Optional members: `sampleId` (a laboratory or inspection sample reference) and
`sourceRecordId` (your originating system's key — see
[Enterprise integration](enterprise-integration.md)).

The `epc` member is the legacy name for the carrier identifier associated with the item.
It is a plain string in this profile; the example value is a fictional URI and does **not**
claim a GS1 EPC encoding. Full identifier guidance is in [Identifiers](identifiers.md).

## Step 3 — Product information

`product` requires only `articleClass`. Everything else is optional but improves what a
downstream sorter or recycler can do:

~~~json
"product": {
  "articleClass": "homeTextileFlat",
  "fabricConstruction": "woven",
  "colourPrimary": "light",
  "condition": "good",
  "mass": { "value": 0.42, "unit": "kg" },
  "technicalFlags": []
}
~~~

`articleClass`, `fabricConstruction`, `colourPrimary`, `condition` and each entry of
`technicalFlags` are **controlled vocabulary tokens**, not free text. A value outside the
published vocabulary is rejected with `S4C-PAYLOAD-VOCAB-INVALID`; it is never silently
coerced to a default. See [Vocabularies](vocabularies.md).

`mass` is a `{value, unit}` object. A bare number is never a quantity in this profile,
because a number without a unit cannot be safely aggregated by anyone downstream.

`technicalFlags` carries properties that change how a machine should treat the item — for
example the presence of a hard point, or a pigment that defeats an optical technology.
An empty array is a meaningful statement: no flags were recorded.

## Step 4 — Material observations, and why provenance is the point

`materialObservations` is the heart of the profile, and it is where most implementations
get the model wrong. It is **not** a composition field. It is an append-only sequence of
attributed claims.

Compare these two statements:

> "95% polyester."

> "95% polyester by mass, determined by quantitative laboratory analysis, asserted by
> organisation X, observed at 2042-06-18T11:02:10Z."

Only the second can be acted on. The first cannot answer any of the questions a downstream
party actually has: is this a label transcription or a measurement? Who is accountable if
it is wrong? Was it observed before or after the garment was dyed? Is a newer observation
available? Is it consistent with what my own scanner just measured?

That is why every observation requires six members:

| Field | Why it is mandatory |
| --- | --- |
| `observationId` | An absolute URI. Lets a later record, decision or correction refer to *this* claim rather than to "the composition". |
| `fibreType` | A `fibre-type` vocabulary token. |
| `valueStatus` | A `value-status` token: `supplied`, `notMeasured`, `unknown`, `notApplicable` or `withheld`. Distinguishes "not measured" from "measured and absent" from "withheld from you". |
| `method` | A `method` token. `labelDeclaration` and `labQuantitativeIso1833` are both legitimate and are not interchangeable. |
| `sourceOrganisationId` | Who asserts the claim. Accountability, and the basis for trust decisions. |
| `observedAt` | When the observation was made — not when it was written down. |

Optional but frequently important: `percentage` with its mandatory `percentageBasis`,
`confidence` as a `{value, scale}` object, `sourceSystemId` (which instrument or system
produced it), and `evidenceRef` (a pointer to a report or record).

### Percentages

If you supply `percentage`, you must supply `percentageBasis`. There are two bases and
they mean genuinely different things:

- `mass` — a mass fraction, comparable and summable within one measurement occasion;
- `declaredLabel` — what the label says, which is a declaration and not a measurement.

Within one **observation set** — the same source organisation, source system, method and
observation time — supplied `mass` fractions may not exceed 100 plus a 0.5 percentage-point
tolerance. Exceeding it means double counting, a wrong basis, or two occasions wrongly
merged into one.

A set summing to **less than** 100 is accepted and normal. An instrument that identifies
the majority fibre and reports nothing else has made a true statement about what it found.
Requiring the sum to reach 100 would force implementations to fabricate a residual, and a
fabricated residual is indistinguishable from a measurement afterwards.

### Unknown and unavailable values

Never invent a number, and never drop the observation. Record what you actually know:

~~~json
{
  "observationId": "urn:example:observation:000001-unresolved",
  "fibreType": "blendUnresolved",
  "valueStatus": "notMeasured",
  "method": "manualInspection",
  "sourceOrganisationId": "urn:example:org:sorter-a",
  "observedAt": "2044-01-16T09:00:00Z"
}
~~~

When `valueStatus` is anything other than `supplied`, the schema **forbids** a
`percentage`. "Unknown, 62%" is not a state this profile allows you to express. See
[`examples/fixtures/valid-uncharacterised-garment.json`](../examples/fixtures/valid-uncharacterised-garment.json)
and the negative fixture `invalid-unknown-carrying-a-value.json`.

### Two technologies that disagree

Do not overwrite, average or reconcile conflicting observations. Append both.

Because the composition rule applies **within** an observation set and never across sets,
a laboratory result of 95% polyester plus 5% elastane and a later near-infrared result of
93.4% polyester coexist without error, even though they sum to 193.4. Retaining both is
the entire point of the append-only model: the consumer sees two attributed claims with
two methods, two sources and two times, and decides for itself.

See [`examples/fixtures/valid-two-technologies-disagree.json`](../examples/fixtures/valid-two-technologies-disagree.json)
and [Provenance](provenance.md).

## Step 5 — Validate

~~~sh
python -m sort4circ_dpp.cli validate my-first-dpp.json
~~~

Validation runs in three stages, in this order: JSON Schema structure, then controlled
vocabulary membership, then cross-field rules such as the composition tolerance. The
stages produce different reason codes so your client can tell a shape problem
(`S4C-PAYLOAD-SCHEMA-INVALID`) from a meaning problem (`S4C-PAYLOAD-VOCAB-INVALID`).
Details and the full negative-fixture list: [Validation](validation.md).

## Step 6 — Create it through the API

Start the service with the local demo identity, as described in
[Getting started](getting-started.md), then:

~~~sh
curl -s -X POST http://127.0.0.1:8000/v1/dpps \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  -H "Idempotency-Key: my-first-create-001" \
  --data @my-first-dpp.json
~~~

The response is `201` with a `Location` header and an `ETag`. Keep the `ETag`: you need it
for `If-Match` on any later update. Repeating the request with the same `Idempotency-Key`
returns the original result rather than creating a second passport; repeating it with the
same key but different content is a conflict. See [API guide](api.md).

## Step 7 — Bind a data carrier

A passport nobody can find is not useful. Commission a carrier so a physical read resolves
to the record:

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/carriers" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  -d '{"carrierType":"qrCode","encodingScheme":"proprietary",
       "encodedIdentifier":"urn:example:carrier:000001",
       "resolverUri":"https://example.org/dpp/000001",
       "boundBy":"urn:example:org:manufacturer-a"}'
~~~

The carrier holds an identifier that **resolves** to the passport. It does not hold the
passport. See [Carrier binding](carrier-binding.md).

## Step 8 — Read it back as somebody else

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001"          # public
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001" \
  -H "X-DPP-Role: sortingOperator"                                       # sorting view
~~~

The public response keeps the composition but replaces `sourceOrganisationId` with an
explicit `"sourceOrganisationStatus": "withheld"`. It is marked rather than silently
dropped, because a consumer that sees nothing would wrongly conclude the data was never
collected. That is a different — and false — statement. See [Security model](security.md).

## You now have a Tier 1 Core Passport

Next steps, in the order most implementations need them:

1. [Identifiers](identifiers.md) — get your URI scheme and granularity right before you
   issue records at scale.
2. [Provenance](provenance.md) — the rules behind step 4.
3. [Vocabularies](vocabularies.md) — the token sets, and how to extend them safely.
4. [Lifecycle events](lifecycle-events.md) — Tier 2: recording what happened to the item.
5. [Enterprise integration](enterprise-integration.md) — populating all of this from an
   ERP, MES or database instead of by hand.
6. [Conformance](conformance.md) — proving your own implementation behaves correctly.
