# Contributing

Contribute generic DPP concepts, corrections and independently synthetic examples.

## Choose the reporting channel

Public GitHub issues are only for non-sensitive bugs and feature requests, including public-profile documentation and specification improvements.

Security vulnerabilities and suspected accidental project-data exposure must not be posted in public issues, pull requests, discussions or comments. Report them through GitHub Private Vulnerability Reporting, the official mechanism for this repository, following [SECURITY.md](SECURITY.md). If private reporting is unavailable, keep the report private rather than opening a public report.

## Synthetic material only

Use minimal, independently synthetic reproductions for every contribution and report, including private security reports. Generate fictional inputs with SyntheticFixtureFactory and describe the behaviour being tested.

Do not submit real credentials, private configuration, partner data, project data, pilot data or internal endpoints. This applies to payloads, code, attachments, screenshots, logs and follow-up messages. Also exclude personal data, real sample histories, project deployment details, private review material and raw operational evidence. Describe suspected exposure without reproducing the exposed content.

Synthetic example. Not SORT4CIRC project data.

## Changes and validation

Describe the public-profile rule affected, the behaviour before and after, and the tests performed. Do not claim legal conformity, certification or production assurance from these checks. New schema or API behaviour needs tests.

Run python -m pytest -q, python -m ruff check src tests tools examples, fixture validation, mapping/OpenAPI checks and the public-release verifier. Deliberately review new files for the exact public allowlist, then regenerate MANIFEST.in and MANIFEST.sha256 with the documented tools. A manifest update must not silently expand the allowed content.

Follow the owner-approved component split in [LICENSING.md](LICENSING.md): MIT for software/configuration and CC BY 4.0 for documentation/specifications and non-code metadata. Retain third-party notices and explicitly classify new public files.
