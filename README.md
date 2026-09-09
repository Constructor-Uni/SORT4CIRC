# SORT4CIRC DPP Development Guidelines

A technical specification and implementation toolkit for developing interoperable textile
Digital Product Passports. The repository provides machine-readable schemas, controlled
vocabularies, semantic models, interoperability mappings, API specifications, validation
resources, conformance tests, and implementation guidance.

<p align="center">
  <img src="docs/assets/sort4circ-hero-dark.svg"
       alt="SORT4CIRC textile Digital Product Passport workflow: a garment enters a conveyor, pauses beneath a UHF RFID read zone for one EPC capture, resolves to a passport record holding independently retained laboratory and near-infrared observations, passes a versioned routing decision into fibre sorting, and is anchored asynchronously for integrity."
       width="100%">
</p>

## Purpose

The repository covers textile Digital Product Passport implementation from data modelling
and validation through system integration, lifecycle exchange, sorting interoperability,
semantic interoperability, and integrity verification.

The repository includes a Python-based implementation for executing and testing the
published profile. The profile itself is technology-neutral: other architectures,
languages, databases and deployment technologies may be used where the applicable
requirements and interface behaviour are preserved.

---

## Implementation pathways

| Task | Resource |
| --- | --- |
| Create and validate an initial DPP | [First DPP walkthrough](docs/first-dpp.md) · [Validation](docs/validation.md) |
| Understand the data model | [Data model](docs/concepts.md) |
| Implement identifiers and carrier binding | [Identifiers](docs/identifiers.md) · [Carrier binding](docs/carrier-binding.md) |
| Integrate the REST API | [API guide](docs/api.md) · [OpenAPI contract](spec/openapi/dpp-api-v1.json) |
| Record provenance on observations | [Provenance](docs/provenance.md) |
| Apply controlled vocabularies | [Vocabularies](docs/vocabularies.md) |
| Record lifecycle events | [Lifecycle events](docs/lifecycle-events.md) |
| Integrate ERP and MES systems | [Enterprise integration](docs/enterprise-integration.md) |
| Integrate sorting and PSSR systems | [Sorting integration](docs/sorting-integration.md) |
| Implement RDF/OWL interoperability | [Representations and semantics](docs/interoperability.md) |
| Verify record integrity | [Integrity](docs/integrity.md) |
| Apply access control and security requirements | [Security model](docs/security.md) |
| Address scalability | [Scalability](docs/scalability.md) |
| Run conformance tests | [Conformance](docs/conformance.md) |
| Trace requirements to specification, implementation and tests | [Traceability](docs/traceability.md) |
| Consult terminology | [Glossary](docs/glossary.md) |

Complete navigation is provided in the [documentation index](docs/index.md).

---

## Quick start

Prerequisites: Python 3.11 or later and `git`. Docker is optional.

~~~sh
git clone https://github.com/Constructor-Uni/SORT4CIRC.git
cd SORT4CIRC
python -m pip install -e ".[dev]"

python -m sort4circ_dpp.cli example > my-first-dpp.json   # a valid starting record
python -m sort4circ_dpp.cli validate my-first-dpp.json    # -> VALID
python examples/worked_example.py                         # create, bind, resolve, update
python -m pytest -q                                       # the conformance suite
~~~

[Getting started](docs/getting-started.md) documents the full local procedure, including
the HTTP service and the Docker route. The [first DPP walkthrough](docs/first-dpp.md)
covers the record field by field.

---

## Versioning

**Repository release:** v1.3.0<br>
**DPP implementation profile:** 1.0.0

Individual specification assets may carry compatible patch versions.

See [Versioning and migration](docs/versioning-and-migration.md).

---

## Repository contents

The following categories are distinct and should not be conflated.

| Path | Contents | Status |
| --- | --- | --- |
| `spec/` | The SORT4CIRC DPP implementation profile: JSON Schema, controlled vocabularies, RDF/OWL ontology, JSON/XML/RDF mappings, XSD, OpenAPI contract, SPARQL conformance queries, governance schemas, access matrix, reason codes | **Normative within this profile** |
| `src/sort4circ_dpp/` | Reference software implementing the profile | Illustrative: one implementation approach |
| `examples/` | Synthetic worked examples with valid and deliberately invalid fixtures | Illustrative |
| `tests/`, `tools/` | Validation, contract and conformance resources, with generators and checkers | Executable evidence |
| `docs/` | Implementation guidance organised by implementation task | Explanatory |

The `spec/` directory holds the machine-readable specification assets. The accompanying
software is reference software demonstrating one implementation approach; it does not
constrain the implementation technology of an adopting system.

### Normative scope

Normative statements are normative **within the SORT4CIRC DPP implementation profile**
versioned in this repository. They apply only to conformance with that profile, and are
not, and do not claim to be:

- an official European Union specification or European Commission certification;
- a CEN, CENELEC or EN standard;
- an external conformity assessment or certification scheme;
- legal advice, proof of ESPR conformity, or proof that a deployment is compliant.

[Traceability](docs/traceability.md) records, for each requirement area, whether a rule
derives from a legal obligation, a standards-profile requirement, a SORT4CIRC
project-scope requirement, or a SORT4CIRC engineering decision, together with its status:
implemented, specified, optional, deployment-dependent, or outside the scope of the
reference software. Determining which obligations apply to a given product and
organisation requires independent assessment with appropriate expertise. See
[Regulatory context](docs/regulatory-context.md).

---

## Implementation tiers

The profile is designed for incremental adoption in three stages. Integrity anchoring is
not a prerequisite for a conformant passport.

| Tier | Name | Scope |
| --- | --- | --- |
| **1** | Core Passport | Persistent passport identity; the DPP record; carrier binding; basic product information; material observations; provenance on every observation; controlled vocabulary values; read and resolve API; access-aware views |
| **2** | Operational Passport | Lifecycle and sorting events; write semantics and updates; idempotency and optimistic concurrency; the operational sorting view; PSSR and sorting observations; translation from enterprise systems; fuller access-control behaviour |
| **3** | Assured Passport | Deterministic canonicalisation and digest; integrity evidence records; an optional ledger adapter and anchoring; independent verification; performance, recovery, security and migration testing |

A Tier 1 passport is exchangeable and testable in its own right. Tier 3 adds assurance
rather than function. The tiers are an adoption sequence defined by this profile; they are
not a certification scheme and confer no external status.

---

## Reference software boundary

The reference service is intended for study and testing. Specifically:

- storage is **in-process memory**; records do not survive process exit;
- the default integrity backend is an **in-memory mock**, not a distributed ledger. A
  reference Besu adapter is provided as an **optional** example of the adapter contract.
  It is an implementation, **not the outcome of the assessment** that would select a
  ledger platform for a deployment, and no platform is ranked or recommended here. The
  default path requires neither that adapter nor any distributed ledger;
- the default identity provider (`PublicOnlyAuth`) grants read-only public access and
  **rejects** claimed role headers. The header-based demonstration identity (`DemoAuth`)
  is opt-in, does not constitute authentication, and must not protect a deployed system;
- the test suite covers schema rules, vocabulary rules, canonical digest vectors, mock
  integrity outcomes, identifier classification, API access behaviour, and representation
  mappings. It does **not** demonstrate physical-line behaviour, durability, industrial
  validation, production performance, or security assurance.

Replacement of these components is expected and is documented in
[Customisation](docs/customisation.md) and the [Security model](docs/security.md).

---

## Data scope

Examples, fixtures, and demonstration identifiers in this repository are synthetic or
demonstrative unless explicitly identified otherwise. They are included for specification,
validation, interoperability, and conformance purposes.

Confidential partner data, personal data, credentials, private keys, pilot-operational
information, raw industrial datasets, and security-sensitive deployment configuration are
outside the repository scope. The Annex G reference example retains its published synthetic
identifiers for reproducibility.

The full disclosure boundary is defined in
[PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md), and the verification applied to a
release candidate is described in [release verification](docs/public-release.md).
Suspected disclosure of confidential material should be reported through the private
channel described in [SECURITY.md](SECURITY.md).

---

## Licence

The repository is licensed in two components: Apache-2.0 for software, and CC BY 4.0 for
the documentation and specification assets listed below. It is **not** a single-licence
repository.

| Component | Licence |
| --- | --- |
| Software, tests, tools, build, CI and container configuration | **Apache-2.0**, see [LICENSE](LICENSE) |
| Documentation, specifications, schemas, vocabularies, ontology, mappings, OpenAPI, JSON fixtures, repository prose and metadata | **CC BY 4.0**, see [LICENSE-DOCS](LICENSE-DOCS) |

The per-path coverage map is [LICENSING.md](LICENSING.md); every published file has an
explicit component scope. Package metadata declares the combined distribution as
`Apache-2.0 AND CC-BY-4.0`. Third-party dependencies retain their own licences. This
repository neither redistributes nor relicenses any external standards document.

## Citation

See [CITATION.cff](CITATION.cff). A DOI may be added once a tagged release is archived;
the required steps are recorded in that file.

## Contributing, security and release process

- [CONTRIBUTING.md](CONTRIBUTING.md): installation, testing, linting, fixture addition,
  safe modification of specification assets, and material that must not appear in a
  contribution.
- [SECURITY.md](SECURITY.md): private vulnerability reporting.
- [PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md) and
  [docs/public-release.md](docs/public-release.md): publication scope, and the
  verification applied to a release candidate.
- [CHANGELOG.md](CHANGELOG.md): versioned changes.

## Provenance

This repository is the technical output of the SORT4CIRC Horizon Europe project. The
specification it publishes originates in project deliverable D4.3, *DPP Development
Guidelines*; the machine-readable profile versioned in this repository is its
authoritative form, and the deliverable document is not required in order to use the
repository. See [CITATION.cff](CITATION.cff) for citation and
[Traceability](docs/traceability.md) for requirement-level provenance.

Attribution does not identify or validate any deployed system.
