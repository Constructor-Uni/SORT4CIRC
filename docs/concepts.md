# Concepts, identifiers and provenance

Synthetic example. Not SORT4CIRC project data.

A passport is a versioned JSON record. identity identifies an item or a batch; product describes article class, construction and optional characteristics. materialObservations is a sequence of attributed claims, not an inferred universal composition. Each observation records a value status, method, source organisation and time. Keep conflicting observations separate.

The fixture describes a fictional woven home textile with declared cotton and flax values. A later fictional label observation is independent. These declarations are illustrative, not laboratory evidence.

A DPP identifier names the record. An item identifier names its subject. A carrier encodes an identifier which may resolve to a record. These are different responsibilities. Examples use urn:example: and https://example.org/. The legacy identity.epc field carries a fictional URI in this profile; the example does not implement EPC encoding or identify physical equipment.

Lifecycle events have their own identifier, event time, recorded time, actor and source. Appending events retains earlier records and advances the reference record version. Observed time and recorded time represent different facts. The memory implementation loses all records when the process exits.

The JSON schema constrains structure; validation adds controlled vocabulary and cross-field rules. A valid record is not proof that a claim is factually accurate. See [Mappings](interoperability.md) for representations and [API](api.md) for exchange behaviour.
