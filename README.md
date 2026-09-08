# Public Digital Product Passport reference profile

This repository provides a generic public Digital Product Passport reference profile, educational Python implementation, synthetic examples and interoperability/conformance tooling. It was developed as a reusable knowledge output associated with the SORT4CIRC Horizon Europe project.

The public material excludes the project's production or demonstrator deployment, operational architecture, partner integrations, production configuration, project or partner datasets, pilot data and security-sensitive implementation details. See [Publication boundary](PUBLICATION_BOUNDARY.md).

"Normative" means normative only for conformance with the public profile defined and versioned in this repository. This repository does not constitute an official European Union specification, European Commission certification, CEN/CENELEC certification, legal advice, proof of ESPR conformity, or proof that a deployment is legally compliant.

## Start here

Synthetic example. Not SORT4CIRC project data.

Use Python 3.11 or later. In your own development environment:

~~~sh
python -m pip install -e ".[dev]"
python -m sort4circ_dpp.cli validate examples/fixtures/valid-synthetic-textile.json
python examples/worked_example.py
python -m pytest -q
python tools/conformance_report.py
~~~

Follow [Getting started](docs/getting-started.md) for creation, resolution, provenance, integrity and adaptation. Browse the [documentation index](docs/index.md), [API contract](spec/openapi/dpp-api-v1.json), [schema](spec/schemas/dpp-2.0.0.schema.json) and [mapping contract](spec/mappings/README.md).

## Scope and limitations

The memory repository, mock integrity adapter and optional header-based demo identity are teaching components. Tests cover schema rules, canonical vectors, mock integrity outcomes, carrier classification, API access and mappings. They do not demonstrate physical-line behaviour, durability, industrial validation, production performance or comprehensive security assurance.

Profile 2.0.0 introduces fictional namespaces and independently generated examples. Existing package and code identifiers retain project attribution; they do not identify a deployment.

## Publication review

Use the explicit allowlist in public-release-policy.json and the [release workflow](docs/public-release.md). A working checkout can hold excluded local material; publish only a verified export. Passing automated checks does not approve Git history or publication.

The owner-approved split is **MIT for software** and **CC BY 4.0 for the listed documentation and specifications**, including generated OpenAPI. See [LICENSE](LICENSE), [LICENSE-DOCS](LICENSE-DOCS) and the explicit [coverage map](LICENSING.md). Root prose and non-code documentation/metadata are CC BY 4.0; CI, build, automation and container configuration are MIT. All current public files have explicit coverage. Third-party components retain their own licences.

See [Security](SECURITY.md) and [Contributing](CONTRIBUTING.md).
