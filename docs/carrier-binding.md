# Carrier binding

How a physical object leads to its passport. QR, Data Matrix, NFC and UHF RFID — including
temperature/time-sensing RFID (TTRFID) — are all handled by the same binding model.

## The one principle

**The carrier carries an identifier. The identifier resolves to the passport. The carrier
does not carry the passport.**

~~~
physical read → encodedIdentifier → resolution → dppId → record (in a view)
~~~

Embedding passport content in the tag looks attractive and fails in every direction:

- **It goes stale immediately.** A passport gains observations, events and decisions
  throughout its life. A tag written at production cannot.
- **It cannot be access-controlled.** Anyone with a reader gets everything. The view model
  — public, sorting, recycler, authority — exists precisely because different parties are
  entitled to different content, and that decision has to be made at read time by a system
  that knows who is asking.
- **It does not fit.** A UHF RFID user memory bank is tens to a few hundred bytes. A
  passport is kilobytes.
- **It cannot be corrected.** An error written to a tag is on the garment.

Cache aggressively at the reader if you need offline operation, but the tag holds the
identifier.

## The carrier binding record

`carriers` is an array of first-class binding objects, each with its own lifecycle:

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

| Member | Required | Meaning |
| --- | --- | --- |
| `carrierId` | ● | Identifies **this tag instance**, not the item and not the passport |
| `carrierType` | ● | `uhfRfid`, `nfc`, `qrCode` or `dataMatrix` |
| `encodingScheme` | ● | `proprietary`, `gs1Sgtin198`, `gs1DigitalLink` or `proprietary` |
| `encodedIdentifier` | ● | The value actually written on the carrier and read back |
| `bindingStatus` | ● | `commissioned`, `replaced`, `retired` or `failed` |
| `boundAt`, `boundBy` | ● | When the binding was made, and by whom |
| `resolverUri` | | Where a reader looks the passport up |
| `closedAt` | conditional | **Required** when `bindingStatus` is not `commissioned` |
| `placement` | | Where on the article the carrier physically is |

`placement` matters more than it looks: a sorting line needs to know where to aim a reader,
and a recycler needs to know where to remove a metal-bearing tag before shredding.

## Binding lifecycle

`commissioned` → `replaced` | `retired` | `failed`

A carrier that stops being the active binding must record `closedAt`; the schema enforces
it, so a superseded binding cannot be left ambiguously open. Commissioning a new carrier
on a passport automatically closes the previous commissioned one in the reference
implementation.

Two safety rules are enforced by the store
([`store.py`](../src/sort4circ_dpp/store.py)), and any implementation should reproduce
them:

1. **An encoded identifier already bound to another passport is refused** —
   `S4C-IDENT-DUPLICATE-BINDING`. One identifier resolving to two active passports is
   exactly the failure a cloned tag produces, and it must be detectable.
2. **A retired identifier is never reassigned to a different product.** Reuse would make
   historical reads silently resolve to the wrong item.

Commissioning is atomic: either the binding, the encoded value and the status are all
created, or nothing is. A failed attempt never leaves two commissioned bindings.

## Commissioning a carrier

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/carriers" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: brand" \
  -H "X-DPP-Organisation: urn:example:org:manufacturer-a" \
  -H "Idempotency-Key: commission-000001" \
  -d '{"carrierType":"qrCode","encodingScheme":"proprietary",
       "encodedIdentifier":"urn:example:carrier:000001",
       "resolverUri":"https://example.org/dpp/000001",
       "boundBy":"urn:example:org:manufacturer-a",
       "placement":"sideSeamLabel"}'
~~~

Resolve it back:

~~~sh
curl -s "http://127.0.0.1:8000/v1/identifiers/urn%3Aexample%3Acarrier%3A000001/dpp" \
  -H "X-DPP-Role: sortingOperator"
~~~

The identifier is URL-encoded in the path. The response is the passport in the view your
role is entitled to. See [API guide](api.md#flow-2--resolve-an-identifier).

## Choosing a carrier technology

| | QR / Data Matrix | NFC | UHF RFID |
| --- | --- | --- | --- |
| Read range | Line of sight, centimetres | Centimetres | Metres |
| Bulk reading | No | No | Yes, many tags at once |
| Consumer readable | Yes, any phone camera | Yes, most phones | No, needs a dedicated reader |
| Survives wear | Poor once soiled or abraded | Good | Good |
| Typical payload | A resolver URL | A resolver URL or compact identifier | A compact identifier |
| Cost per unit | Lowest | Medium | Higher |

Practical consequences:

- **Consumer access** points to QR or NFC. A `gs1DigitalLink` HTTPS payload opens directly
  from a phone camera.
- **Automated sorting** points to UHF RFID: bulk reading at line speed is the whole
  argument, and no optical technology gives you that on a moving, overlapping stream.
- **Both is normal.** A garment may carry a printed QR for the consumer and a UHF tag for
  the sorting line. That is two entries in `carriers`, two `carrierId` values, one
  passport. The `carriers` array is an array for this reason.

For UHF encoding, keep the payload compact. Memory is scarce and read reliability falls as
payload grows, so encode a short identifier and resolve it — do not encode a long URL.

## TTRFID and other sensing carriers

Temperature/time-sensing RFID (TTRFID) and similar sensing transponders fit the model
without any extension to the binding record, because the sensing capability is not a
property of the *binding*:

- The **carrier binding** stays exactly as above: `carrierType: uhfRfid`, an encoded
  identifier, a status, a placement.
- What the sensor **reports** is data, and data enters the passport through the mechanisms
  that already carry attribution:
  - a condition, exposure or handling reading becomes a **lifecycle event**
    (`inspection` or `identification`) with `sourceSystemId` naming the sensing system and
    `eventTime` distinct from `recordedAt`;
  - a material-relevant determination becomes a **material observation** with the
    appropriate `method` token, `sourceOrganisationId`, `sourceSystemId`, `observedAt` and
    a `confidence` where the technology supplies one.

The rule is that a sensor reading is an attributed claim like any other. It gets a method,
a source, a time and — where available — a confidence. It never becomes an unattributed
field, because then nobody downstream can judge it.

The synthetic worked example in
[`examples/worked_example.py`](../examples/worked_example.py) exercises the
commission-and-resolve path with a fictional carrier; the reference implementation issues
no hardware commands and models no radio settings. Reader configuration, antenna geometry,
power settings and transponder selection are deployment engineering, outside the scope of
this profile.

## Handling reads safely

A read is not a resolution. Before you resolve anything, classify what the reader gave you.
[`gateway/readzone.py`](../src/sort4circ_dpp/gateway/readzone.py) shows the four cases the
profile distinguishes:

| Observation | Reason code | Why it is separate |
| --- | --- | --- |
| Nothing read | `S4C-IDENT-UNKNOWN` | A tagless item is a normal input, not a fault |
| More than one tag in the window | `S4C-IDENT-AMBIGUOUS` | Two garments in the zone; resolving either one is a guess |
| Unreadable, or not a valid identifier | `S4C-IDENT-MALFORMED` | A client or hardware defect, distinguishable from missing data |
| One well-formed identifier | — | Resolution may be attempted |

Only the last permits resolution. Each rejection carries a `safeAction` from
[`spec/reason-codes.json`](../spec/reason-codes.json) describing an **application**
response; the profile specifies no physical or industrial behaviour, and a line's response
to an ambiguous read is your engineering decision.

See [Sorting integration](sorting-integration.md).

## The `identity.epc` field

`identity.epc` is a legacy convenience denormalisation of the current primary carrier
identifier. It is a plain string, the profile does not implement or validate GS1 EPC
encoding, and the example value `urn:example:carrier:000001` is fictional. The
authoritative binding record is always the `carriers` array, which carries status, times
and an actor. See [Identifiers](identifiers.md#the-epc-field).

## What never goes on a carrier

- credentials, API keys, tokens or anything else that authorises access;
- personal data;
- internal hostnames, private endpoints or infrastructure detail;
- commercially sensitive values — a price, a cost, a customer, a production line.

A tag is printed or embedded on a physical object that leaves your control permanently and
is readable by anyone who possesses it. Treat everything you write to it as published.

## Related pages

- [Identifiers](identifiers.md) — why the carrier identifier is not the passport identifier
- [Sorting integration](sorting-integration.md) — resolving at line speed
- [Security model](security.md) — who receives what after resolution
