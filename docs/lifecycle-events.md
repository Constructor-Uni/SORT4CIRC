# Lifecycle events

Tier 2. Recording what happened to an item, when it happened, and who says so — without
losing the ability to reconstruct what was known at any earlier moment.

Material observations say *what the item is*. Lifecycle events say *what happened to it*.
Keep them separate: a collection event is not a claim about composition, and an
observation is not an occurrence.

## The event object

Seven mandatory members:

~~~json
{
  "eventId": "urn:example:event:000001",
  "eventType": "collection",
  "eventTime": "2043-07-10T12:00:00Z",
  "eventTimeZoneOffset": "+00:00",
  "recordedAt": "2043-07-10T12:05:00Z",
  "actorOrganisationId": "urn:example:org:collector-a",
  "sourceSystemId": "urn:example:system:collection-client",
  "facilityId": "urn:example:facility:collection-site-a",
  "readPointId": "urn:example:readpoint:gate-2"
}
~~~

| Member | Required | Meaning |
| --- | --- | --- |
| `eventId` | ● | URI. Identifies this occurrence, so it can be cited and corrected |
| `eventType` | ● | `event-type` vocabulary token |
| `eventTime` | ● | When it happened |
| `eventTimeZoneOffset` | ● | The local offset at the place it happened |
| `recordedAt` | ● | When the system was told |
| `actorOrganisationId` | ● | Who performed it |
| `sourceSystemId` | ● | Which system reported it |
| `facilityId` | | Where |
| `readPointId` | | The specific read point |
| `bizStep`, `disposition` | | Business-process context, for alignment with event-standard vocabularies you already use |
| `inputRefs`, `outputRefs` | conditional | Required for `transformation` |
| `correctsEventId` | | This event corrects an earlier one |
| `evidenceRef` | | Supporting record |

## Event time is not recorded time

This is the distinction implementations most often erase, and it is unrecoverable once
erased.

- `eventTime` — when the occurrence took place.
- `recordedAt` — when your system learned about it.

They diverge routinely: a handheld reader works offline in a warehouse and uploads two
hours later; a laboratory result is keyed in the next morning; a batch file arrives
nightly. If you store one timestamp, you cannot answer "what did we know at 14:00?", which
is precisely the question every audit, dispute and incident review asks.

`eventTimeZoneOffset` is carried **separately** from `eventTime` even though `eventTime`
already includes an offset. The reason is operational: a shift boundary, an opening hour
and a working day are local facts. Normalising everything to UTC and discarding the local
frame makes "the night shift on the 14th" unreconstructable.

## The event types

| Token | Occurrence |
| --- | --- |
| `production` | Manufacture of the product |
| `collection` | Entry into a post-consumer collection stream |
| `transfer` | Change of custody without transformation |
| `receipt` | Receipt at a facility |
| `identification` | Capture of the identifier at a read point |
| `inspection` | Human or instrumented examination |
| `materialObservation` | A material observation was recorded |
| `sortingDecision` | A sorting outcome was issued or confirmed |
| `reusePreparation` | Preparation for reuse |
| `resale` | Sale on a secondary market |
| `recyclingInput` | Entry into a recycling process |
| `transformation` | Inputs consumed, distinct outputs produced |
| `retirement` | The product left the tracked system |

Note that `materialObservation` and `sortingDecision` exist as event types **in addition
to** the `materialObservations` and `sortingDecisions` arrays. The array holds the content
of the claim or decision; the event records that it occurred, by whom, where and when. Use
both when the occurrence itself is operationally meaningful — for instance when a scan
happened at a specific read point that the observation record does not carry.

## Transformations

A `transformation` event requires `inputRefs` and `outputRefs`. The schema enforces it,
because a transformation that does not say what went in and what came out is not
traceable — and transformation is exactly where traceability chains normally break.

~~~json
{
  "eventId": "urn:example:event:000410",
  "eventType": "transformation",
  "eventTime": "2044-03-02T08:30:00Z",
  "eventTimeZoneOffset": "+01:00",
  "recordedAt": "2044-03-02T08:31:12Z",
  "actorOrganisationId": "urn:example:org:recycler-a",
  "sourceSystemId": "urn:example:system:mes-line-3",
  "inputRefs": ["urn:example:item:000001", "urn:example:item:000002"],
  "outputRefs": ["urn:example:batch:fibre-0007"]
}
~~~

Inputs and outputs are identifiers of subjects, which lets a consumer walk the chain in
either direction across passports. This is a many-to-many relation: garments become a
fibre batch, and a fibre batch becomes many new items.

## Append-only, and corrections

`lifecycleEvents` is append-only. The reference implementation rejects any `PATCH` that
touches it with `S4C-STATE-APPEND-ONLY-VIOLATION`.

To correct an event, append a new one with `correctsEventId` pointing at the original:

~~~json
{
  "eventId": "urn:example:event:000412",
  "eventType": "receipt",
  "correctsEventId": "urn:example:event:000411",
  "eventTime": "2044-03-01T16:05:00Z",
  "eventTimeZoneOffset": "+01:00",
  "recordedAt": "2044-03-02T09:00:00Z",
  "actorOrganisationId": "urn:example:org:sorter-a",
  "sourceSystemId": "urn:example:system:wms"
}
~~~

Both events remain. A consumer sees that a correction was made, when, and by whom. Deleting
the original would destroy the fact that the record once said something else — which is
usually the most important fact in a dispute.

## Appending an event

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/events" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: collector" \
  -H "X-DPP-Organisation: urn:example:org:collector-a" \
  -H "Idempotency-Key: gate2-scan-2043-07-10-000001" \
  -d '{"eventType":"collection","eventTime":"2043-07-10T12:00:00Z",
       "eventTimeZoneOffset":"+00:00","recordedAt":"2043-07-10T12:05:00Z",
       "actorOrganisationId":"urn:example:org:collector-a",
       "sourceSystemId":"urn:example:system:collection-client",
       "facilityId":"urn:example:facility:collection-site-a"}'
~~~

`201`, returning `eventId`, `dppId` and the new `recordVersion`. Appending an event
advances the record version and preserves every earlier version.

Omitted `eventId`, `recordedAt` and `actorOrganisationId` are defaulted from the request
and the caller's identity. Supply them explicitly wherever you can: the defaults describe
the moment the server was told, not the moment the thing happened, and for an offline
reader those are hours apart.

Use `Idempotency-Key` derived from the real-world occurrence — a scan identifier, a
work-order line — so that a retried upload does not create a duplicate event. The key is
scoped to caller, organisation, role, operation and resource. See
[API guide](api.md#idempotency).

## Which roles may append events

`dpp.event` is held by `brand`, `collector`, `sortingOperator`, `pssrSystem`,
`recycler` and `administrator`. `public`, `consumer`, `authority` and `integrityVerifier`
may not append events. See [Security model](security.md).

Note who *reads* them: the `partner` view returns only the events in which the caller's own
organisation participated, so a collector sees its own custody chain and not a
competitor's. The `authority` and `full` views return all events.

## Sorting decisions

Sorting outcomes are a separate array, `sortingDecisions`, because a decision has different
mandatory context from an event — specifically, what it was based on:

~~~json
{
  "decisionId": "urn:example:decision:000001",
  "basedOnObservations": ["urn:example:observation:000001-cotton"],
  "basedOnRecordVersion": 4,
  "ruleSetId": "urn:example:ruleset:line-a",
  "ruleSetVersion": "1.2.0",
  "sortingCategory": "mechanicalRecyclingFibre",
  "route": "line-a-chute-3",
  "decidedAt": "2044-01-16T09:04:00Z",
  "decidedBy": "urn:example:org:sorter-a",
  "outcomeStatus": "issued"
}
~~~

`basedOnObservations` and `ruleSetVersion` are mandatory so that a decision can be
**replayed**: you can see which claims and which rule release produced it. Without them,
"why was this routed to chemical recycling?" is unanswerable six months later, when the
rule set has changed twice.

`outcomeStatus` is `issued`, `confirmed`, `rejected` or `overridden`, and an `overridden`
decision must carry an `overrideReason`. Overrides are normal and worth recording: they are
the feedback signal that tells you where the rule set is wrong.

See [Sorting integration](sorting-integration.md).

## Related pages

- [Data model](concepts.md) · [Provenance](provenance.md)
- [Sorting integration](sorting-integration.md) — events from a sorting line
- [Enterprise integration](enterprise-integration.md) — deriving events from ERP/MES
  transactions
- [Integrity](integrity.md) — anchoring a specific record version
