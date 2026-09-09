# Representations and the semantic model

The same passport in three representations — JSON, XML and RDF — and how the profile keeps
them meaning the same thing.

**Read this when you need it.** JSON is the practical exchange representation and is all
you need for Tier 1. XML matters when a partner's exchange stack requires it. RDF/OWL
matters when you need to link passport data to other datasets, reason over it, or federate
across organisations. None of them is a prerequisite for creating a working DPP.

## The three representations

| | Purpose | Asset | Validated by |
| --- | --- | --- | --- |
| **JSON** | The primary exchange representation | [`spec/schemas/dpp-1.0.0.schema.json`](../spec/schemas/dpp-1.0.0.schema.json) | JSON Schema 2020-12, plus vocabulary and cross-field rules |
| **XML** | Exchange with XML-native stacks | [`spec/schemas/dpp-1.0.0.xsd`](../spec/schemas/dpp-1.0.0.xsd) | XSD 1.1, including assertions |
| **RDF/OWL** | The shared semantic model | [`spec/ontology/sort4circ-1.0.1.ttl`](../spec/ontology/sort4circ-1.0.1.ttl) | The ontology, checked with `rdflib` |

JSON Schema remains the normative JSON validation path. The XSD is a projection of it, not
a second source of truth: where they could disagree, the JSON Schema wins.

## The mapping contract

[`spec/mappings/dpp-mapping-1.0.0.json`](../spec/mappings/dpp-mapping-1.0.0.json) is the
authoritative correspondence between the three, with 124 rows covering every
schema-defined exchange field. Each row records:

| Column | Meaning |
| --- | --- |
| `mappingId`, `mappingVersion` | Stable identity of the row |
| `jsonPath`, `xmlXPath` | Where the field lives in JSON and XML |
| `rdfSubjectType`, `rdfProperty`, `rdfConstruct` | The RDF class and property, or the construct used instead |
| `rdfMappingStatus`, `rdfMappingReason` | `direct`, `subjectIdentifier` or `notApplicable`, with the reason |
| `datatype`, `cardinality`, `obligation` | Type, multiplicity and whether the field is mandatory, conditional or optional |
| `controlledVocabulary`, `unitRule` | Which vocabulary and unit rule apply |
| `semanticMeaning`, `notes` | What the field means, and any limitation |

`dpp-mapping-1.0.0.csv` is **generated** from the JSON, never edited by hand:

~~~sh
python tools/gen_mapping_csv.py --check    # fails if the CSV has drifted
python tools/gen_mapping_csv.py            # regenerate
~~~

The `rdfMappingStatus` column exists so that a consumer is never misled about coverage.
111 rows map directly to an ontology property, 7 contribute the subject identifier, and 6
are recorded as `notApplicable` with an explicit reason. An exchange must not imply a
lossless semantic mapping where a field has none, and the mapping table is where that
honesty is recorded and tested.

## XML

Namespace `https://data.sort4circ.eu/dpp/1.0.0`, XSD 1.1 with `vc:minVersion="1.1"`.

XSD 1.1 is required because the profile's conditional rules are assertions, not structural
constraints. The XSD enforces the same conditions the JSON Schema does:

- `granularity` requires the matching identifier;
- a non-`commissioned` carrier binding requires `closedAt`;
- `percentage` requires `percentageBasis`, and a non-`supplied` `valueStatus` forbids
  `percentage`;
- a `transformation` event requires inputs and outputs;
- an `overridden` sorting decision requires an override reason.

~~~python
from sort4circ_dpp.mapping import json_to_xml, xml_to_json

document = json_to_xml(passport)     # validates before serialising
recovered = xml_to_json(document)    # validates the result
assert recovered == passport         # round trip, zero information loss
~~~

Round-trip fidelity is asserted for every shipped fixture in `tests/test_mapping.py`. A
representation that silently drops an optional member is a data-loss bug, and the tests
treat it as one.

## RDF and OWL

Namespace `https://data.sort4circ.eu/vocabulary/`, ontology version IRI
`https://data.sort4circ.eu/vocabulary/1.0.0`. The declared profile is **OWL 2 DL**; the EL subset
is explicitly excluded because it cannot express the disjointness and asymmetry axioms the
model relies on. That statement is in the ontology header — the profile records the
deviation rather than claiming a subset it does not satisfy.

33 classes, 32 object properties and 74 datatype properties. The class structure follows
the data model:

- `DigitalProductPassport` — the record;
- `TextileEntity` and its subclasses `Garment`, `Fabric`, `Yarn`, `Filament`, `Fibre`,
  `Component`, `HardPoint` — the containment chain from garment down to fibre;
- `Observation` and its subclasses `MaterialObservation`, `ConditionObservation`,
  `SensorObservation`, `EnvironmentalValue`;
- `LifecycleEvent` and its subclasses (`ProductionEvent`, `CollectionEvent`,
  `TransferEvent`, `IdentificationEvent`, `InspectionEvent`, `SortingEvent`,
  `TransformationEvent`);
- `SortingDecision`, `RuleSet`, `SortingCategory`, `Method`;
- `DataCarrier`, `CarrierBinding`;
- `Organisation`, `Facility`, `ReadPoint`, `SourceSystem`;
- `IntegrityEvidence`.

### Axioms that carry the model's commitments

The ontology is not a class list. Five axiom groups encode the same rules the JSON Schema
enforces, in a form a reasoner can check:

~~~turtle
# An observation is never the thing described. This is what allows two
# technologies to disagree about one garment without either corrupting it.
[] a owl:AllDisjointClasses ;
   owl:members ( s4c:Observation s4c:TextileEntity s4c:LifecycleEvent ) .

# A methodless or sourceless observation is inconsistent, not merely incomplete.
s4c:Observation rdfs:subClassOf
    [ a owl:Restriction ; owl:onProperty s4c:usedMethod ;  owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
    [ a owl:Restriction ; owl:onProperty s4c:observedBy ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] .
~~~

Plus: a `SortingDecision` must cite at least one observation; a `TransformationEvent` must
consume an input and produce an output; a `DigitalProductPassport` describes at most one
product. `partOf` is transitive, irreflexive and asymmetric, so a component cannot contain
itself. `supersededBy` is asymmetric and irreflexive.

The result is that the provenance rules from [Provenance](provenance.md) are not merely a
convention enforced by one validator — they are properties of the model, checkable by any
OWL reasoner.

### Producing RDF

~~~python
from sort4circ_dpp.mapping import json_to_rdf, rdf_to_json

graph = json_to_rdf(passport)                 # validates first
print(graph.serialize(format="turtle"))
assert rdf_to_json(graph) == passport         # round trip
~~~

Two things happen in the graph, and it is important to understand why both:

1. **Semantic triples.** The passport becomes an `s4c:DigitalProductPassport` subject
   identified by its `dppId`; it `s4c:describes` a `TextileEntity` identified by the
   item, batch or model identifier; observations become `MaterialObservation` nodes linked
   by `s4c:hasObservation`, with `s4c:usedMethod`, `s4c:observedBy`, `s4c:observedAt` and
   the rest. Controlled tokens for `articleClass`, `fibreType` and `method` become IRIs
   under the vocabulary namespace (for example
   `https://data.sort4circ.eu/vocabulary/fibre-type/cotton`), so they can be referenced and
   aligned across datasets rather than compared as strings.
2. **A lossless `rdf:JSON` snapshot.** The canonical JSON is also attached as an
   `rdf:value` literal. This is a **transport** device, not semantics — it guarantees the
   round trip is lossless even for fields with no direct semantic property. The mapping
   table's `rdfMappingStatus` column deliberately does **not** count the snapshot as
   semantic coverage, and `tests/test_mapping.py` asserts that it does not.

The distinction matters: without it, an implementation could claim complete RDF coverage
while actually carrying a JSON blob with a class attached to it.

## Preservation of meaning across representations

The commitments checked by `tests/test_mapping.py`:

- every schema-defined exchange path has **exactly one** mapping row — no gaps, no
  duplicates;
- JSON → XML → JSON is lossless for every fixture;
- JSON → RDF → JSON is lossless for every fixture;
- every RDF binding resolves to a property that exists in the ontology, or to a declared
  RDF construct;
- every `controlledVocabulary` reference resolves to a published vocabulary;
- the XSD declares every mapped XML element;
- **absence states never become zero or empty** — `notMeasured`, `unknown`,
  `notApplicable` and `withheld` survive every representation as themselves;
- multiple methods remain separate observations, in every representation;
- the count of mandatory-field information loss is zero.

The absence-state rule is the one worth dwelling on. A representation that turns "not
measured" into `0`, or into a missing element, has converted an honest statement of
ignorance into a false statement of fact. That is a data-integrity failure, not a
formatting detail, and it is asserted per status token.

## Running the checks

~~~sh
python -m pytest tests/test_mapping.py -q
python tools/gen_mapping_csv.py --check
~~~

Both need the development extras (`pip install -e ".[dev]"`) for `rdflib`, `xmlschema` and
`pyyaml`.

These verify the local mapping contract, XML validation, ontology property resolution and
the round trips covered by the suite. They do **not** certify interoperability with any
external partner, service or standard. Alignment with an external vocabulary — a GS1
identifier scheme, an EPCIS-style event vocabulary, a European DPP registry model — is a
mapping you would define and test yourself against that specification.

## Choosing a representation

| Need | Use |
| --- | --- |
| Web API exchange, mobile, most integrations | JSON |
| A partner whose stack is XML-native, or an XSD-based validation gate | XML |
| Linking passports to other datasets, federation, reasoning, SPARQL | RDF |
| Aligning your own extensions with the model's semantics | The ontology |

You do not have to choose one. The mapping contract exists so that you can serve JSON to
an API consumer and RDF to a knowledge graph from the same record, with a tested guarantee
that they say the same thing.

## Related pages

- [Data model](concepts.md) — the JSON structure these representations project
- [Vocabularies](vocabularies.md) — the token sets, and updating all representations together
- [Validation](validation.md) — validating each representation
- [Enterprise integration](enterprise-integration.md) — mapping discipline applied to your
  own source systems
- [Mapping contract README](../spec/mappings/README.md)
