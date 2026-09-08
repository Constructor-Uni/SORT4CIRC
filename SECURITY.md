# Security

## Private reporting

GitHub Private Vulnerability Reporting is the official reporting mechanism for this public DPP repository. Use it for security vulnerabilities and suspected accidental project-data exposure.

Do not post either type of report in public GitHub issues, pull requests, discussions or comments. Public issues are only for non-sensitive bugs and feature requests.

Open this repository's **Security and quality** tab and select **Report a vulnerability**. See [GitHub's private reporting instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately). Maintainers must enable and maintain this GitHub feature separately from this policy file. If the private reporting option is unavailable, keep the report private; do not use a public issue or pull request as a fallback.

## Report contents

Use minimal, independently synthetic reproductions only, including in private reports. Describe the affected public component and version, the expected and observed behaviour, and the potential impact using fictional inputs. For suspected data exposure, describe the concern without copying the exposed material.

Do not submit real credentials, private configuration, partner data, project data, pilot data or internal endpoints. This prohibition applies to reports, attachments, screenshots, logs, code changes and follow-up messages, whether public or private. Do not include personal data, private review material or raw operational evidence.

Synthetic example. Not SORT4CIRC project data.

## Reference implementation boundary

The reference API uses PublicOnlyAuth by default. It rejects supplied demo role headers; writes need an explicitly injected authentication provider. DPP_DEMO_AUTH=1 enables a local educational stand-in that trusts X-DPP-Role and X-DPP-Organisation headers. Anyone who can reach that demo can impersonate its roles. Bind it to loopback and use synthetic data only.

The compose example exposes one API service on loopback and uses an in-memory integrity adapter. It supplies no secrets and exposes no maintenance drain endpoint. State is lost on restart. Production identity, authorisation, transport, persistence, monitoring and recovery require separate design and assessment.

The public summary exporter accepts only fixed test identifiers and result statuses. It does not export raw execution output or environment data. Automated leakage checks reduce accidental inclusion; they do not approve a public release or replace a security assessment.
