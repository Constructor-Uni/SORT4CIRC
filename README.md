# SORT4CIRC DPP Development Guidelines

A practical technical specification and Python reference implementation for building a
textile Digital Product Passport (DPP), using the SORT4CIRC DPP implementation profile.

If you are asking *"I want to create a textile DPP for my organisation from scratch —
where do I start, what do I need to implement, and how do I test that I did it
correctly?"*, this repository is the answer to that question.

**Who this is for:** developers, software architects, integrators, technology providers,
and organisations — manufacturers, brands, collectors, sorters, recyclers — that need to
issue, exchange or consume textile product passports.

**What you get:** a versioned data model and JSON Schema, controlled vocabularies, an
RDF/OWL semantic model with JSON/XML/RDF mappings, an OpenAPI exchange contract,
identifier and data-carrier guidance, an optional integrity/anchoring profile, a runnable
Python reference service, synthetic worked examples, and a conformance test suite you can
run against your own implementation.

No prior reading is required. Everything you need is in this repository.

> **Two version numbers.**
> **Repository release: v1.3.0** · **DPP implementation profile: 1.0.0**
>
> The repository, package and documentation evolve on their own version line. The
> normative profile — schema, vocabularies, mappings, ontology, access matrix and reason
> codes — is profile 1.0.0, and `schemaVersion` in every payload is `1.0.0`. A new
> repository release does not invalidate your records.
> See [Versioning and migration](docs/versioning-and-migration.md#two-version-numbers).

---

## Start here

Prerequisites: Python 3.11 or later, and `git`. Docker is optional.

~~~sh
git clone https://github.com/Constructor-Uni/SORT4CIRC.git
cd SORT4CIRC
python -m pip install -e ".[dev]"

python -m sort4circ_dpp.cli example > my-first-dpp.json   # a valid starting record
python -m sort4circ_dpp.cli validate my-first-dpp.json    # -> VALID
python examples/worked_example.py                         # create, bind, resolve, update
python -m pytest -q                                       # the conformance suite
~~~

Then follow **[Getting started](docs/getting-started.md)** for the full local loop
(including running the HTTP service and the Docker route), and
**[Create your first DPP](docs/first-dpp.md)** for a field-by-field walkthrough.

---

## I want to…

| I want to… | Go to |
| --- | --- |
| Run this locally in five minutes | [Getting started](docs/getting-started.md) |
| Build my first DPP | [Create your first DPP](docs/first-dpp.md) |
| Understand the DPP data model | [Data model](docs/concepts.md) |
| Validate a DPP | [Validation](docs/validation.md) |
| Get identifiers right | [Identifiers](docs/identifiers.md) |
| Use the REST API | [API guide](docs/api.md) · [OpenAPI](spec/openapi/dpp-api-v1.json) |
| Record provenance properly | [Provenance](docs/provenance.md) |
| Use the controlled vocabularies | [Vocabularies](docs/vocabularies.md) |
| Add lifecycle events | [Lifecycle events](docs/lifecycle-events.md) |
| Connect QR / RFID / TTRFID | [Carrier binding](docs/carrier-binding.md) |
| Integrate ERP / MES / a database | [Enterprise integration](docs/enterprise-integration.md) |
| Integrate a sorting / PSSR system | [Sorting integration](docs/sorting-integration.md) |
| Understand the RDF/OWL semantic model | [Representations and semantics](docs/interoperability.md) |
| Add integrity evidence or blockchain anchoring | [Integrity](docs/integrity.md) |
| Apply access control and security requirements | [Security model](docs/security.md) |
| Scale it | [Scalability](docs/scalability.md) |
| Test my own implementation | [Conformance](docs/conformance.md) |
| See requirement → spec → code → test | [Traceability](docs/traceability.md) |
| Look up a term | [Glossary](docs/glossary.md) |

Full navigation: **[documentation index](docs/index.md)**.

---

## What is in this repository

The categories below are deliberately distinct. Do not read one as the other.

| Path | What it is | Status |
| --- | --- | --- |
| `spec/` | The SORT4CIRC DPP implementation profile: JSON Schema, controlled vocabularies, RDF/OWL ontology, JSON↔XML↔RDF mappings, XSD, OpenAPI contract, access matrix, reason codes | **Normative within this profile** |
| `src/sort4circ_dpp/` | A Python reference implementation of the profile | Illustrative — one way to implement it |
| `examples/` | Synthetic worked examples plus valid and deliberately invalid fixtures | Illustrative |
| `tests/`, `tools/` | Validation, contract and conformance tests, plus generators and checkers | Executable evidence |
| `docs/` | Developer guides organised around implementation questions | Explanatory |

The `spec/` directory contains the SORT4CIRC DPP implementation profile and its
machine-readable specification assets. The Python software is a **reference
implementation** demonstrating one implementation approach. Other architectures,
languages, databases and deployment technologies may be used where they preserve the
applicable requirements and interface behaviour. Nothing here requires you to use Python,
FastAPI, or an in-memory store.

### What "normative" means here

Normative statements are **normative within the SORT4CIRC DPP implementation profile**
versioned in this repository. They are normative only for conformance with the public profile defined and versioned here, and are not, and do not claim to be:

- an official European Union specification or European Commission certification;
- a CEN, CENELEC or EN standard;
- an external conformity assessment or certification scheme;
- legal advice, proof of ESPR conformity, or proof that any deployment is compliant.

This repository does not constitute an official European Union specification, European
Commission certification, CEN/CENELEC certification, legal advice, proof of ESPR conformity,
or proof that a deployment is legally compliant.

[Traceability](docs/traceability.md) records, per requirement area, whether a rule derives
from a **legal obligation**, a **standards-profile requirement**, a **SORT4CIRC
project-scope requirement**, or a **SORT4CIRC engineering/architecture decision** — and
whether it is implemented, specified, optional, deployment-dependent, or outside the scope
of the reference implementation. Determine which obligations apply to your product and
organisation independently, with appropriate expertise. See
[Regulatory context](docs/regulatory-context.md).

---

## Implementation tiers

You do not have to implement everything at once, and you should not start with
blockchain. The profile is designed to be adopted in three steps.

| Tier | Name | You implement |
| --- | --- | --- |
| **1** | Core Passport | Persistent passport identity · the DPP record · carrier binding · basic product information · material observations · provenance on every observation · controlled vocabulary values · read/resolve API · access-aware views |
| **2** | Operational Passport | Lifecycle and sorting events · write semantics and updates · idempotency and optimistic concurrency · the operational sorting view · PSSR/sorting observations · translation from enterprise systems · fuller access-control behaviour |
| **3** | Assured Passport | Deterministic canonicalisation and digest · integrity evidence records · an optional ledger adapter and anchoring · independent verification · performance, recovery, security and migration testing |

A Tier 1 passport is already useful, exchangeable and testable. Tier 3 adds assurance, not
function. These tiers are an adoption sequence defined by this profile. They are not an EU
certification scheme and confer no external status.

---

## Public data and scoping notice

All examples, fixtures and demonstration identifiers distributed in this repository are
**synthetic or demonstrative**. They exist solely to illustrate the SORT4CIRC DPP
implementation profile. They must not be interpreted as descriptions of any consortium
partner's commercial activity, material intake, production processes, operational
performance or capabilities.

No confidential partner data, personal data, credentials, API keys, private keys,
pilot-operational information, raw industrial datasets or security-sensitive deployment
configuration is intended to be distributed here. Example identifiers use the reserved
`urn:example:` and `https://example.org/` namespaces and fictional dates.
The one exception is the Annex G worked example, which keeps its published
`urn:sort4circ:` identifiers and `TXHO-WP3-B01-001` sample label so that this repository
reproduces the published reference record exactly. Those values are synthetic too.

A record that validates against this profile is a well-formed record; it is not evidence
that any claim inside it is factually true.

If you believe something confidential has been published here, do not open a public
issue — follow [SECURITY.md](SECURITY.md).

---

## Reference implementation boundary

The reference service is a teaching implementation. Specifically:

- storage is **in-process memory**; all records are lost when the process exits;
- the default integrity backend is an **in-memory mock**, not a distributed ledger. A
  reference Besu adapter ships alongside it as an **optional** example of the adapter
  contract; it is an implementation, **not the outcome of the assessment** that would
  select a ledger platform for any deployment, and no platform is ranked or recommended
  here. Nothing in the default developer path requires it, or any blockchain at all;
- the default identity provider (`PublicOnlyAuth`) grants read-only public access and
  **rejects** claimed role headers. The header-based demo identity (`DemoAuth`) is
  opt-in, is not authentication, and must never protect a deployed system;
- the test suite covers schema rules, vocabulary rules, canonical digest vectors, mock
  integrity outcomes, identifier classification, API access and mappings. It does **not**
  demonstrate physical-line behaviour, durability, industrial validation, production
  performance or comprehensive security assurance.

Replacing these components is expected, and is documented in
[Customisation](docs/customisation.md) and the [Security model](docs/security.md).

---

## Licence

This repository is licensed in two components: Apache-2.0 for software and CC BY 4.0 for
the listed documentation and specifications. It is **not** a single-licence repository.

| Component | Licence |
| --- | --- |
| Software, tests, tools, build/CI/container configuration | **Apache-2.0** — see [LICENSE](LICENSE) |
| Documentation, specifications, schemas, vocabularies, ontology, mappings, OpenAPI, JSON fixtures, repository prose and metadata | **CC BY 4.0** — see [LICENSE-DOCS](LICENSE-DOCS) |

The exact per-path coverage map is [LICENSING.md](LICENSING.md); every public file has an
explicit component scope. Package metadata declares the combined distribution as
`Apache-2.0 AND CC-BY-4.0`. Third-party dependencies retain their own licences, and this
repository neither redistributes nor relicenses any external standards document.

## Citing this work

See [CITATION.cff](CITATION.cff). A DOI can be added once the first tagged public release
is archived; see the notes in that file.

## Contributing, security and release process

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to install, test, lint, add fixtures and change
  specification assets safely, and what must never appear in a contribution.
- [SECURITY.md](SECURITY.md) — private vulnerability reporting.
- [PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md) and
  [docs/public-release.md](docs/public-release.md) — what is in scope for publication and
  how a release candidate is verified.
- [CHANGELOG.md](CHANGELOG.md) — versioned changes.

## Provenance

This repository is the public technical output of the SORT4CIRC Horizon Europe project.
The specification it publishes originates in project deliverable D4.3, *DPP Development
Guidelines*; the machine-readable profile versioned here is the authoritative form of it,
and you do not need the deliverable to use this repository. See
[CITATION.cff](CITATION.cff) for citation and [Traceability](docs/traceability.md) for
requirement-level provenance.

Attribution does not identify or validate any deployed system.
