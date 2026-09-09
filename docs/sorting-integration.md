# Sorting integration

Tier 2. How a sorting or post-consumer textile identification system — a PSSR-class
installation, an optical or NIR line, a manual grading station — reads from and writes to a
passport.

Everything here is generic. The profile specifies application behaviour only; it issues no
hardware commands, models no radio or optical settings, and prescribes no line behaviour.
What a machine physically does with a classification is your engineering decision.

## The loop

~~~
read carrier
  → classify the read (readable? single? well-formed?)
  → resolve identifier → dppId
  → GET sorting-view
  → run your rule set
  → POST observation(s)      — what you measured
  → POST event / record decision — what you did about it
~~~

Every step has a defined failure mode. The four that matter most are read classification
failures, and they are covered first because getting them wrong is how a line produces
confident wrong answers.

## Step 1 — Classify the read before resolving

A read is not a resolution. Ask three questions in order, and the answers are different
conditions with different remedies:

| Situation | Reason code | Safe action | Correct handling |
| --- | --- | --- | --- |
| Nothing was read | `S4C-IDENT-UNKNOWN` | `divert` | Normal input. Untagged items exist. Route to your no-passport path. |
| More than one tag in the read window | `S4C-IDENT-AMBIGUOUS` | `divert` | Two items in the zone. Resolving either is a guess. Do not resolve, and do not retry — retrying consumes the remaining budget without adding information. |
| Read failed, or the value is not a well-formed EPC | `S4C-IDENT-MALFORMED` | `divert` | A hardware or client defect. Distinguishable from missing data, and worth alerting on. |
| Read below the confidence floor | `S4C-READ-WEAK-SIGNAL` | `divert` | An unreliable read. Treat as unidentified rather than acting on a guess. |
| Repeat read inside the suppression window | `S4C-READ-SUPPRESSED-DUPLICATE` | `noCommand` | The same item seen twice. Not an error: issue no new command. |
| Exactly one well-formed, strong, unsuppressed read | — | — | Resolution may be attempted |

The reference implementation of this classification is
[`gateway/readzone.py`](../src/sort4circ_dpp/gateway/readzone.py), tested in
`tests/test_readzone.py`. It is about forty lines and worth reproducing in any language:

~~~python
from sort4circ_dpp.gateway.readzone import ReadZone

zone = ReadZone()                      # suppression window and signal floor are configurable

# one entry per tag detected in the read window
result = zone.evaluate([{"epc": tag_value, "rssiDbm": rssi}])
if result.may_command:
    passport = resolve(result.epc)
else:
    handle(result.reason_code, result.safe_action)   # e.g. "divert", "noCommand"
~~~

`ReadZone.diverts(code)` tells you whether a code's safe action stops the item rather than
routing it (`divert`, `divertAndAlert`, `retryOnceThenDivert`). A gateway that receives any
of those must not publish a category-specific command.

Why keep them separate? Collapsing all three into "no passport" means an antenna
misalignment producing thousands of malformed reads looks identical to a genuine stream of
untagged garments — and you will not notice for weeks. Collapsing ambiguity into "pick the
first" means two garments in the zone are silently attributed to one passport.

Each reason code carries a `safeAction` from
[`spec/reason-codes.json`](../spec/reason-codes.json). The profile defines these so that a
gateway maps every failure to a defined outcome *before* any command reaches an actuator:
`divert` and `divertAndAlert` stop the item, `noCommand` issues nothing, `quarantine` holds
a record for review, and `noEffectOnSorting` marks a condition that must not change routing
at all. Which physical behaviour implements a safe action is yours to define; that every
code has one is not optional.

## Step 2 — Resolve

~~~sh
curl -s "http://127.0.0.1:8000/v1/identifiers/urn%3Aexample%3Acarrier%3A000001/dpp" \
  -H "X-DPP-Role: sortingOperator"
~~~

Two more conditions to handle, distinct from the read failures above:

- `S4C-IDENT-RETIRED` (410) — the identifier belongs to a closed binding. A superseding
  record is supplied where one is known. Follow it, or route to review.
- `S4C-IDENT-DUPLICATE-BINDING` (409) — the identifier resolves to two active passports.
  This means a cloned or misassigned tag. Never guess; route to manual review.

## Step 3 — Get the sorting view

~~~sh
curl -s "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/sorting-view?consistency=strong" \
  -H "X-DPP-Role: sortingOperator"
~~~

~~~json
{
  "dppId": "urn:example:dpp:000001",
  "recordVersion": 4,
  "generatedAt": "2044-01-16T09:00:00Z",
  "product": {
    "articleClass": "homeTextileFlat",
    "fabricConstruction": "woven",
    "colourPrimary": "light",
    "technicalFlags": []
  },
  "materialSummary": [
    { "observationId": "urn:example:observation:000001-cotton",
      "fibreType": "cotton", "percentage": 62, "percentageBasis": "declaredLabel",
      "valueStatus": "supplied", "method": "supplierDeclaration" }
  ],
  "priorDecision": null,
  "indexLagMs": 0,
  "consistency": "projected"
}
~~~

This is deliberately the minimum a sorting decision consumes. It is not a reduced-fidelity
copy of the passport: it is the subset that a routing decision actually uses, which keeps
the payload small at line speed and keeps commercially irrelevant content out of an
operational system.

Note what is retained and why:

- **`method` on every entry in `materialSummary`.** A `labelDeclaration` and a
  `labQuantitativeIso1833` claim are not equally trustworthy inputs to a routing rule, and
  the summary would be useless without the distinction.
- **`technicalFlags`.** A metal hard point or a carbon-black pigment changes what your line
  can do with the item, and frequently changes what your own sensor can see.
- **`recordVersion` and `generatedAt`.** So the decision can be replayed against the exact
  content that produced it.
- **`priorDecision`.** So a re-presented item is recognised rather than re-decided from
  scratch.

### Consistency

`consistency=projected` (default) reads a maintained projection and reports `indexLagMs`.
`consistency=strong` bypasses it and reads the store.

Choose per decision, not globally. A high-throughput routing decision on a conveyor
tolerates a few milliseconds of lag; a decision that commits an item irreversibly — bale
composition, a chemical recycling feed — should be strong. Because the view carries its
`recordVersion`, you can always record which state you decided on. See
[Scalability](scalability.md).

## Step 4 — Submit what you measured

Your classification result is an **observation**, with the same provenance obligations as
any other:

~~~sh
curl -s -X POST "http://127.0.0.1:8000/v1/dpps/urn:example:dpp:000001/observations" \
  -H "Content-Type: application/json" \
  -H "X-DPP-Role: pssrSystem" \
  -H "X-DPP-Organisation: urn:example:org:sorter-a" \
  -H "Idempotency-Key: line-a-scan-000918273" \
  -d '{"fibreType":"polyester","percentage":93.4,"percentageBasis":"mass",
       "valueStatus":"supplied","method":"nirSpectroscopy",
       "sourceOrganisationId":"urn:example:org:sorter-a",
       "sourceSystemId":"urn:example:system:nir-line",
       "confidence":{"value":0.86,"scale":"unitInterval"},
       "observedAt":"2044-01-16T09:03:00Z"}'
~~~

Three rules that sorting integrations get wrong:

1. **Do not overwrite the existing composition.** Append. Your NIR reading and a
   laboratory result are two attributed claims, and both are true statements about what
   each party observed. The composition rule applies within an observation set, never
   across sets, so a disagreement is not a validation error. See
   [Provenance](provenance.md).
2. **Always send `confidence` with its `scale`** when your technology produces one. A
   downstream consumer weighing your claim against another needs it, and an unlabelled
   confidence number is ambiguous (`unitInterval` vs `percent`).
3. **When you could not determine the material, say so** — `valueStatus: notMeasured` or
   `unknown`, and no percentage. The schema forbids a percentage on a non-`supplied`
   status. An unclassifiable item is a real and useful fact; a fabricated composition is
   not.

Use an `Idempotency-Key` derived from your line's own scan identifier, so a retried upload
after a network blip does not create a duplicate observation.

## Step 5 — Record the decision

A sorting decision goes into `sortingDecisions` and carries the context needed to replay
it:

~~~json
{
  "decisionId": "urn:example:decision:000918273",
  "basedOnObservations": ["urn:example:observation:nir-000918273"],
  "basedOnRecordVersion": 4,
  "ruleSetId": "urn:example:ruleset:line-a",
  "ruleSetVersion": "1.2.0",
  "sortingCategory": "mechanicalRecyclingFibre",
  "route": "line-a-chute-3",
  "decidedAt": "2044-01-16T09:03:20Z",
  "decidedBy": "urn:example:org:sorter-a",
  "outcomeStatus": "issued"
}
~~~

`basedOnObservations` and `ruleSetVersion` are mandatory. Six months later, when someone
asks why an item went to chemical recycling, "rule set 1.2.0 applied to observation X at
record version 4" is an answer; "the line decided" is not. `basedOnRecordVersion` pins the
record state as well.

`outcomeStatus` progresses `issued` → `confirmed` | `rejected` | `overridden`. An
`overridden` decision must carry an `overrideReason`. Record overrides: they are your
feedback signal about where the rule set is wrong, and discarding them discards the only
evidence you have of systematic misclassification.

Where the occurrence itself matters — a specific read point, a specific facility — also
append a lifecycle event with `eventType: sortingDecision` or `identification`. See
[Lifecycle events](lifecycle-events.md).

## The sorting categories

`reuseGradeA`, `reuseGradeB`, `repair`, `mechanicalRecyclingFibre`,
`chemicalRecyclingPolyester`, `chemicalRecyclingCellulosic`, `wiper`, `insulationFill`,
`residualWaste`, `manualReview`.

`manualReview` is normative within this profile: **every rule set must be able to produce
it**. A rule set with no "I do not know" outcome is a rule set that produces confident
wrong answers on the inputs it was not designed for, and the items it is wrong about are
exactly the ones worth a human look. `tests/test_vocab.py` asserts the token's presence for
this reason.

`article-class` has the same property: `unclassified` is a valid outcome, not an error.

## Roles and permissions

| Role | Scopes | Default view | Typical user |
| --- | --- | --- | --- |
| `sortingOperator` | `dpp.read`, `dpp.event`, `dpp.resolve`, `sorting.read` | `sorting` | An operator or station |
| `pssrSystem` | `dpp.read`, `dpp.resolve`, `sorting.read`, `observation.write`, `dpp.event` | `sorting` | An automated line or instrument |

Note the asymmetry: `pssrSystem` may write observations but may **not** create or
patch passports; `sortingOperator` may append events but not observations. Grant the
narrower role that fits. Neither can read the `full` view, so an operational integration
never receives commercial or environmental content it does not need. The policy is data:
[`spec/access-matrix.json`](../spec/access-matrix.json).

## Operating without a passport

Plan for it, because it will be the majority of your input for years. An item may arrive
with no carrier, an unreadable carrier, or an identifier that resolves to nothing.

- Your rule set must run on sensor data alone, and produce a category — possibly
  `manualReview`.
- Do **not** fabricate a passport to make the pipeline uniform. If you create one, it must
  be an honest record: `granularity` matching what you actually identified, and
  observations carrying your own method and organisation as the source.
- Keep your own operational record of unresolved items. It is the measure of how well
  carrier deployment upstream is working.

## Resilience

A sorting line cannot stop because a passport service is slow. Design for degradation:

- **Time out fast** and fall back to sensor-only classification. Record which mode produced
  each decision.
- **Queue writes locally** and replay them with stable idempotency keys. Observations and
  events are append-only, so a delayed write is still correct — this is precisely why
  `observedAt` and `recordedAt` are separate fields.
- **Cache resolutions**, not passport content. An identifier→`dppId` mapping is stable; the
  passport behind it is not.
- **Treat `S4C-RATE-LIMITED` and `S4C-DEP-UNAVAILABLE` as back-off conditions**, not
  failures. See [Scalability](scalability.md).

## Related pages

- [Carrier binding](carrier-binding.md) — what is on the tag and how it resolves
- [Identifiers](identifiers.md) — identifier failure modes in full
- [Provenance](provenance.md) — why your classification needs a method and a confidence
- [Lifecycle events](lifecycle-events.md) — decisions and occurrences
- [API guide](api.md) — the endpoints used above
