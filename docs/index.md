# SORT4CIRC DPP documentation

Developer documentation for the SORT4CIRC Digital Product Passport implementation
profile and its Python reference implementation. Pages are organised around the questions
you hit while implementing, not around specification section numbers.

New here? Start with [Getting started](getting-started.md), then
[Create your first DPP](first-dpp.md).

## The developer journey

Work through these in order. Each step is useful on its own, and nothing later is a
prerequisite for anything earlier.

| # | Step | Page | Tier |
| --- | --- | --- | --- |
| 1 | Understand what this repository provides | [README](../README.md) · [Architecture](architecture.md) | — |
| 2 | Run the reference implementation locally | [Getting started](getting-started.md) | 1 |
| 3 | Create your first DPP | [Create your first DPP](first-dpp.md) | 1 |
| 4 | Validate a DPP against the schema | [Validation](validation.md) | 1 |
| 5 | Understand product, passport and carrier identifiers | [Identifiers](identifiers.md) | 1 |
| 6 | Retrieve and update a DPP through the API | [API guide](api.md) | 1–2 |
| 7 | Add provenance correctly | [Provenance](provenance.md) | 1 |
| 8 | Use controlled vocabularies | [Vocabularies](vocabularies.md) | 1 |
| 9 | Add lifecycle and sorting events | [Lifecycle events](lifecycle-events.md) | 2 |
| 10 | Bind QR, RFID, TTRFID or another carrier | [Carrier binding](carrier-binding.md) | 1–2 |
| 11 | Integrate ERP, MES or another source system | [Enterprise integration](enterprise-integration.md) | 2 |
| 12 | Integrate a sorting / PSSR system | [Sorting integration](sorting-integration.md) | 2 |
| 13 | Understand RDF/OWL semantic interoperability | [Representations and semantics](interoperability.md) | 2 |
| 14 | Add integrity evidence, and anchoring if you need it | [Integrity](integrity.md) | 3 |
| 15 | Apply access, security and scalability requirements | [Security model](security.md) · [Scalability](scalability.md) | 2–3 |
| 16 | Run conformance tests against your own implementation | [Conformance](conformance.md) | 1–3 |

Blockchain anchoring is step 14 on purpose. A Tier 1 passport is complete, exchangeable
and testable without it. RDF/OWL is step 13 for the same reason: JSON is the practical
exchange representation, and the semantic model exists to preserve meaning across
representations rather than to gate adoption.

## Reference

| Page | Contents |
| --- | --- |
| [Data model](concepts.md) | Record structure, granularity, observations, events, versioning |
| [Identifiers](identifiers.md) | DPP ID, item ID, carrier ID, EPC, resolver URI, sample ID |
| [Provenance](provenance.md) | Method, source, time, value status, conflicting observations |
| [Vocabularies](vocabularies.md) | All 18 controlled vocabularies and how to extend them |
| [Validation](validation.md) | Schema, vocabulary and cross-field rules; valid and invalid fixtures |
| [API guide](api.md) | Request flows, views, concurrency, idempotency, error responses |
| [Lifecycle events](lifecycle-events.md) | Event types, event time vs recorded time, corrections |
| [Carrier binding](carrier-binding.md) | QR, NFC, UHF RFID and TTRFID; resolution over embedding |
| [Enterprise integration](enterprise-integration.md) | Mapping ERP/MES fields into the profile |
| [Sorting integration](sorting-integration.md) | Sorting view, observations, decisions, unsafe reads |
| [Representations and semantics](interoperability.md) | JSON, XML and RDF/OWL; the mapping contract |
| [Integrity](integrity.md) | Canonicalisation, digest, evidence envelope, optional anchoring |
| [Security model](security.md) | Roles, scopes, views, identity replacement, secure defaults |
| [Scalability](scalability.md) | Pagination, projections, consistency, caching, load testing |
| [Conformance](conformance.md) | What is machine-testable and how to test your implementation |
| [Traceability](traceability.md) | Requirement → specification asset → implementation → test |
| [Architecture](architecture.md) | Component responsibilities of the reference service |
| [Customisation](customisation.md) | Replacing storage, identity and the ledger adapter |
| [Versioning and migration](versioning-and-migration.md) | How versions change and what breaks |
| [Testing methodology](testing-methodology.md) | Measuring your own deployment honestly |
| [Regulatory context](regulatory-context.md) | The limits of this profile |
| [Release verification](public-release.md) | How a publishable candidate is checked |
| [Glossary](glossary.md) | Terms used across these pages |

## Public data and scoping notice

All examples, fixtures and demonstration identifiers distributed in this repository are
synthetic or demonstrative, and exist solely to illustrate the SORT4CIRC DPP
implementation profile. They must not be interpreted as descriptions of any consortium
partner's commercial activity, material intake, production processes, operational
performance or capabilities. No confidential partner data, personal data, credentials,
private keys, pilot-operational information or security-sensitive deployment
configuration is intended to be distributed here.

Example identifiers use the reserved `urn:example:` and `https://example.org/` namespaces
and fictional dates. The one exception is the Annex G worked example, which keeps its
published `urn:sort4circ:` identifiers and `TXHO-WP3-B01-001` sample label so that this
repository reproduces the published reference record exactly. Those values are synthetic
too.
[PUBLICATION_BOUNDARY.md](../PUBLICATION_BOUNDARY.md) defines included and excluded
material.

## Normative scope

"Normative" here means normative **within the SORT4CIRC DPP implementation profile**
versioned in this repository. It does not mean an EU specification, a CEN/CENELEC
standard, an external certification, or legal conformity.
[Regulatory context](regulatory-context.md) states the limits;
[Traceability](traceability.md) separates legal obligations from standards-profile
requirements, project-scope requirements and engineering decisions.

## Funding

Funded by the European Union under Grant Agreement No 101181988. Views and opinions
expressed are however those of the author(s) only and do not necessarily reflect those of
the European Union or the European Research Executive Agency (REA). Neither the European
Union nor the granting authority can be held responsible for them.
