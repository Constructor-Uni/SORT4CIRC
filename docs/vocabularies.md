# Controlled vocabularies

Every coded field in the profile draws from a published, versioned vocabulary. This page
lists them, explains how validation treats them, and describes how to extend or replace
them for your own domain.

The vocabulary files are in `spec/vocabularies/`; each is linked individually in the
table below.

## Why not free text

A free-text field is a field nobody downstream can act on. `"Polyester"`, `"polyester"`,
`"PES"` and `"100% Poly"` are four values a sorter cannot compare, and any normalisation
you apply afterwards is a guess made without the original context.

Two consequences follow, and both are enforced:

1. **A value outside the vocabulary is rejected, never coerced.** Coercing an unknown token
   to a default would silently convert an integration defect into wrong data. The reason
   code is `S4C-PAYLOAD-VOCAB-INVALID`.
2. **Vocabulary validation is separate from schema validation.** Schema validation answers
   "does this payload have the right shape"; vocabulary validation answers "do these values
   mean anything". They return different reason codes so a client can tell the two apart.

## The vocabularies

All at version 1.0.0, matching the DPP implementation profile release.

| Vocabulary | Terms | Used for |
| --- | --- | --- |
| [`article-class`](../spec/vocabularies/article-class.json) | 14 | `product.articleClass` |
| [`fabric-construction`](../spec/vocabularies/fabric-construction.json) | 7 | `product.fabricConstruction` |
| [`colour-family`](../spec/vocabularies/colour-family.json) | 7 | `product.colourPrimary` |
| [`condition`](../spec/vocabularies/condition.json) | 6 | `product.condition` |
| [`technical-flag`](../spec/vocabularies/technical-flag.json) | 14 | `product.technicalFlags[]` |
| [`fibre-type`](../spec/vocabularies/fibre-type.json) | 23 | `materialObservations[].fibreType` |
| [`method`](../spec/vocabularies/method.json) | 8 | `materialObservations[].method` |
| [`value-status`](../spec/vocabularies/value-status.json) | 5 | `materialObservations[].valueStatus` |
| [`percentage-basis`](../spec/vocabularies/percentage-basis.json) | 2 | `materialObservations[].percentageBasis` |
| [`confidence-scale`](../spec/vocabularies/confidence-scale.json) | 2 | `materialObservations[].confidence.scale` |
| [`component-type`](../spec/vocabularies/component-type.json) | 11 | `components[].componentType` |
| [`event-type`](../spec/vocabularies/event-type.json) | 13 | `lifecycleEvents[].eventType` |
| [`sorting-category`](../spec/vocabularies/sorting-category.json) | 10 | `sortingDecisions[].sortingCategory` |
| [`carrier-type`](../spec/vocabularies/carrier-type.json) | 4 | `carriers[].carrierType` |
| [`encoding-scheme`](../spec/vocabularies/encoding-scheme.json) | 4 | `carriers[].encodingScheme` |
| [`binding-status`](../spec/vocabularies/binding-status.json) | 4 | `carriers[].bindingStatus` |
| [`passport-status`](../spec/vocabularies/passport-status.json) | 4 | `status` |
| [`evidence-state`](../spec/vocabularies/evidence-state.json) | 6 | `integrity[].evidenceState` |

`identity.granularity` is the one coded field that is **not** vocabulary-driven: it is a
closed enum in the JSON Schema itself (`model`, `batch`, `item`), because its three values
define the schema's conditional requirements and cannot vary independently of the schema.

## File format

~~~json
{
  "$id": "https://data.sort4circ.eu/vocabulary/method/1.0.0",
  "name": "method",
  "version": "1.0.0",
  "released": "2026-09-08",
  "owner": "Public profile maintainers",
  "terms": [
    {
      "token": "labelDeclaration",
      "definition": "Read from the sewn-in label. A declaration, not a measurement.",
      "deprecated": false,
      "replacedBy": null
    }
  ]
}
~~~

Every term carries a **definition**. A token list without definitions is not a vocabulary;
it is a spelling convention, and two implementations will interpret it differently.

`deprecated` and `replacedBy` let a term be retired without breaking existing records: the
token stays valid, and `replacedBy` tells a consumer what to migrate to.

## How validation works

Field-to-vocabulary bindings are declared in `FIELD_VOCABULARIES` in
[`vocab.py`](../src/sort4circ_dpp/vocab.py). The table is exhaustive by design: a coded
field missing from it would be accepted unchecked, so the conformance suite asserts that
the table covers every coded field in the schema (`tests/test_vocab.py`).

Failures identify the exact path and the vocabulary version, so a client can fix the
specific member:

~~~
S4C-PAYLOAD-VOCAB-INVALID
  detail: 'bamboo' is not in vocabulary fibre-type version 1.0.0
  fields: ["materialObservations[0].fibreType"]
  extra:  {"vocabulary": "fibre-type", "vocabularyVersion": "1.0.0"}
~~~

Check a document:

~~~sh
python -m sort4circ_dpp.cli validate my-dpp.json
python -m pytest tests/test_vocab.py -q
~~~

Or from Python:

~~~python
from sort4circ_dpp.vocab import load, published

print(published())                       # every vocabulary name
fibres = load("fibre-type")
print(sorted(fibres.tokens))
print(fibres.deprecated, fibres.replacements)
~~~

## Choosing the right token

A few distinctions that implementations regularly get wrong:

- **`blendUnresolved` vs `otherDeclared`.** `blendUnresolved` means a blend was detected but
  not separated into constituents. `otherDeclared` means a specific fibre was declared that
  the vocabulary does not enumerate. They are different epistemic states.
- **`labelDeclaration` vs `supplierDeclaration`.** The first was read off the garment; the
  second was asserted by an upstream party. Both are declarations, and their failure modes
  differ.
- **`unknownColour` and `unknownConstruction`.** Present in `colour-family` and
  `fabric-construction` so you can state that the property was not determined, instead of
  omitting the field and leaving the consumer to guess whether it was never collected.
- **`manualReview` in `sorting-category`.** A legitimate outcome. A sorting system that
  must guess rather than defer is a system that produces confident wrong answers.

## Extending or replacing a vocabulary

The published vocabularies are scoped to the textile use cases this profile addresses.
Adapting them is expected. Do it deliberately:

1. **Add terms; do not silently redefine existing ones.** Changing what an existing token
   means invalidates every record already using it.
2. **Version the vocabulary and the profile together.** A new token set is a new
   `version`, and consumers must be able to tell which release a record was validated
   against.
3. **Retire with `deprecated` and `replacedBy`,** rather than deleting a token. Deleting
   makes historical records unvalidatable.
4. **Update every representation.** A token added to a vocabulary must also appear in the
   [XSD](../spec/schemas/dpp-1.0.0.xsd), the
   [ontology](../spec/ontology/sort4circ-1.0.1.ttl) and the
   [mapping table](../spec/mappings/dpp-mapping-1.0.0.json) where relevant, or the
   representations diverge. `python -m pytest tests/test_mapping.py -q` checks this.
5. **Add fixtures.** A positive fixture using the new token and a negative fixture proving
   the old invalid value is still rejected.
6. **Add the file to the release policy.** New public files must be listed in
   `public-release-policy.json`, given licence coverage in `LICENSING.md`, and the
   manifests regenerated. See [CONTRIBUTING.md](../CONTRIBUTING.md).

If you need domain terms outside textiles, prefer a new vocabulary file over overloading an
existing one. `FIELD_VOCABULARIES` is where you bind it to a field.

## Mapping external terminology in

You will usually be importing values that are not in these vocabularies — an ERP material
code, a supplier's fibre abbreviation, a regulatory label term. Map them explicitly, and
keep the mapping outside the passport:

- record the original value in `sourceRecordId` or `evidenceRef` so the source can be
  traced;
- version the mapping table itself, and record which version produced a record;
- when a source value has **no** target token, do not guess. Reject or quarantine the row
  and report it — `S4C-MAP-VOCAB-UNMAPPED` exists for this condition.

Full treatment: [Enterprise integration](enterprise-integration.md).

## Related pages

- [Data model](concepts.md) · [Provenance](provenance.md) · [Validation](validation.md)
- [Representations and semantics](interoperability.md) — how tokens appear in XML and RDF
