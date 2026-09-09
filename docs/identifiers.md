# Identifiers

Identifier design is the decision you are least able to change later. This page explains
what each identifier in the profile names, why they are kept separate, and what happens
when an implementation collapses them.

All example values below use the reserved `urn:example:` and `https://example.org/`
namespaces. Replace them with a namespace your organisation controls. The Annex G
fixture keeps its published `urn:sort4circ:` identifiers, which are equally synthetic.

## The six identifiers, and what each one names

| Identifier | Field | Names | Lifetime |
| --- | --- | --- | --- |
| Passport identifier | `dppId` | The **record** | Stable for the life of the record |
| Item / product identifier | `identity.itemId`, `identity.batchId`, `identity.modelId` | The **physical subject** at the declared granularity | Stable for the life of the subject |
| Carrier identifier | `carriers[].carrierId` | One **physical tag or code instance** | Ends when the carrier is replaced, retired or fails |
| Encoded identifier | `carriers[].encodedIdentifier`, `identity.epc` | The value actually **written on** the carrier and read back | As long as that carrier is in service |
| Resolver URI | `carriers[].resolverUri` | The **address** at which a reader can look the passport up | Deployment-dependent |
| Sample / source identifier | `identity.sampleId`, `identity.sourceRecordId`, observation `evidenceRef` | A **provenance anchor** in some other system | Owned by that other system |

Every URI-typed identifier must be an absolute URI: the schema requires a leading scheme
(`^[A-Za-z][A-Za-z0-9+.-]*:`). `sampleId`, `sourceRecordId` and `encodedIdentifier` are
plain non-empty strings, because they frequently come from systems that do not mint URIs.

## Why passport ID and item ID are separate

`dppId` names the record; `identity.itemId` names the thing.

They diverge in ordinary operations:

- a record is **superseded**: `status` becomes `superseded`, `supersededBy` points at the
  replacement, and the new record describes the **same** item. Two `dppId` values, one
  `itemId`.
- a record is migrated between registries, or reissued under a new profile version, while
  the physical garment is untouched.
- a `model`-granularity passport describes a design that thousands of items share. The
  record has one identity; the items do not.

If you make `dppId` equal to `itemId`, you have made "the record" and "the thing" the same
entity, and you can no longer express any of the above without either lying about the item
or losing the earlier record.

## Granularity

`identity.granularity` is a declared enum, and the schema enforces the matching field:

| `granularity` | Requires | Choose it when |
| --- | --- | --- |
| `model` | `modelId` | The claim is about a design or SKU and every unit is treated as identical |
| `batch` | `batchId` | The claim is about a lot, bale or roll, and units are not individually distinguished |
| `item` | `itemId` | The claim is about one physical unit |

Granularity is a statement about what your data actually supports, not an ambition. A
`model` passport whose composition came from a design specification is honest. The same
values presented at `item` granularity claim that each unit was individually
characterised, which is a different and stronger assertion.

Granularity cannot be "upgraded" by editing the field. Moving from `model` or `batch` to
`item` means issuing item-level passports, each with its own `dppId`, optionally carrying
observations with `method: computedInherited` to record that a value was derived from the
parent record rather than observed on that unit.

## Carrier identifiers are not passport identifiers

This is the single most common architectural mistake, and the profile is deliberately
structured to prevent it.

A carrier entry is a first-class object with its own lifecycle:

~~~json
{
  "carrierId": "urn:example:carrier-instance:000001",
  "carrierType": "qrCode",
  "encodingScheme": "proprietary",
  "encodedIdentifier": "urn:example:carrier:000001",
  "resolverUri": "https://example.org/dpp/000001",
  "bindingStatus": "commissioned",
  "boundAt": "2042-02-11T08:05:00Z",
  "boundBy": "urn:example:org:manufacturer-a",
  "placement": "sideSeamLabel"
}
~~~

`bindingStatus` takes `commissioned`, `replaced`, `retired` or `failed`. The schema
requires `closedAt` on any status other than `commissioned`, so a superseded binding cannot
be left ambiguously open. A passport may carry several carrier entries over its life —
a QR label that was damaged and replaced, plus a UHF RFID tag added later. `carriers` is
an array precisely because "which tag is on this garment" changes while the passport does
not.

If you treat the tag value **as** the passport identifier:

- replacing a damaged tag either changes the passport identifier or forces you to keep
  using a dead one;
- a tag cloned onto a second garment makes two physical things share one identity, and you
  cannot detect it — the profile reserves `S4C-IDENT-DUPLICATE-BINDING` for exactly this
  condition;
- you cannot carry two carrier technologies on the same item;
- your identifier scheme is now dictated by whatever the tag encoding permits.

Keep them separate, and resolve from one to the other:

~~~
physical read → encodedIdentifier → resolution → dppId → record
~~~

The reference API exposes that resolution as
`GET /v1/identifiers/{encodedIdentifier}/dpp` (the value is URL-encoded in the path).
See [Carrier binding](carrier-binding.md).

## The `epc` field

`identity.epc` is the legacy name in this profile for the carrier identifier associated
with the item. Two things to know:

- it is typed as a plain string, and the profile does **not** implement or validate GS1
  EPC encoding. The example value `urn:example:carrier:000001` is a fictional URI and makes
  no EPC claim;
- it is a convenience denormalisation of the current primary carrier. The authoritative
  binding record is the `carriers` array, which has status, times and an actor.

If you use real GS1 identifiers, declare the scheme on the carrier entry — the
`encoding-scheme` vocabulary offers `gs1Sgtin198` and `gs1DigitalLink` alongside
`proprietary` and `proprietary` — and follow the GS1 specifications themselves for
construction and check characters. This repository does not restate them.

## Resolver URIs

`resolverUri` is where a reader goes to fetch the passport. It is deployment-specific, and
it is the one identifier you should expect to change: registries move, domains change, and
a resolver is infrastructure. Keep it out of your logical identity.

Practical guidance:

- for a QR or Data Matrix, an HTTPS resolver URI that a phone camera can open directly is
  usually the right payload;
- for UHF RFID, memory is scarce; encode a compact identifier and resolve it, rather than
  a long URL;
- never encode a credential, a token or a private hostname in a resolver URI. It is
  printed on a physical object and is world-readable.

## Sample and source identifiers as provenance

`identity.sampleId` and `identity.sourceRecordId`, plus the `sourceSystemId` and
`evidenceRef` members on observations, exist so that a claim in the passport can be traced
back to the record that produced it in some other system.

They are provenance anchors, not addresses. Two rules:

1. **Preserve the original value.** Do not re-key it into your own scheme; the point is
   that the originating system can recognise it.
2. **Do not leak through it.** These values are frequently visible to the roles that can
   read the record. Do not use a value that embeds a person, a customer, a price, an order
   or an internal hostname. If your source key is sensitive, store a stable opaque
   surrogate and keep the mapping in the source system.

## Choosing your own namespace

- Use a namespace your organisation actually controls — a URN namespace you have
  registered, or an HTTPS namespace under a domain you own.
- Prefer opaque identifiers. An identifier that encodes a factory line, a production date
  or a customer discloses that information to everyone who ever reads the tag.
- Decide before issuing whether identifiers are globally unique or unique per issuer, and
  write it down. Retrofitting global uniqueness is expensive.
- Never publish `urn:example:` or `example.org` values outside documentation.

## Identifier failures the profile names

An implementation is expected to distinguish these conditions rather than returning a
generic error. See [`spec/reason-codes.json`](../spec/reason-codes.json).

| Reason code | HTTP | Condition |
| --- | --- | --- |
| `S4C-IDENT-MALFORMED` | 400 | Identifier fails syntax or check-digit validation |
| `S4C-IDENT-UNKNOWN` | 404 | Well-formed identifier, no passport behind it |
| `S4C-IDENT-RETIRED` | 410 | Passport retired; a successor is returned where one exists |
| `S4C-IDENT-AMBIGUOUS` | 409 | More than one tag read within the observation window |
| `S4C-IDENT-DUPLICATE-BINDING` | 409 | One identifier resolves to two active passports |

"Malformed" and "unknown" are different problems with different remedies: one is a client
defect, the other is a data gap. Collapsing them into `404` hides real integration faults.
The reference implementation's classification logic is
[`gateway/readzone.py`](../src/sort4circ_dpp/gateway/readzone.py) and is tested in
`tests/test_readzone.py`.

## Related pages

- [Carrier binding](carrier-binding.md) — QR, NFC, UHF RFID and TTRFID specifics
- [Data model](concepts.md) — where identifiers sit in the record
- [Sorting integration](sorting-integration.md) — safe handling of unreadable and
  ambiguous reads
- [Enterprise integration](enterprise-integration.md) — preserving source keys
