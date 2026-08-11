# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub's security advisory
form on this repository, or by contacting the work package 4 lead at
Constructor University. Do not open a public issue for an unpatched
vulnerability.

Expect an acknowledgement within five working days and an assessment within
fifteen. Reports that concern the reference implementation and reports that
concern the specification are handled differently: a defect in `spec/` may
affect every implementation of it and is disclosed with more notice.

## Scope

In scope: the reference service in `src/`, the specification artefacts in
`spec/`, and the container definitions in `docker/`.

Out of scope: the development authentication stand-in in `api.py`, which is
disabled unless `S4C_ALLOW_HEADER_AUTH` is set and is documented as a stand-in
for an OAuth 2.0 or OIDC profile. Deployments replace it. Reporting it as a
vulnerability is not useful.

## Deployment expectations

The reference implementation is not hardened for production. A deployment is
expected to supply, at minimum:

- token validation verifying issuer, audience, signature, expiry, not-before
  time and authorised party;
- TLS on every non-local connection, and mutual TLS on industrial and privileged
  boundaries;
- key custody outside application configuration, with signing restricted to a
  named service identity;
- a durable store in place of the in-memory one;
- log review confirming no credential, private key or complete confidential
  payload is recorded.

## Known limitations of the reference implementation

- Storage is in-memory and is lost on restart. The recovery tests exercise the
  outbox invariants, not durable persistence.
- The canonicalisation implements RFC 8785 for the value space the profile uses.
  Numbers requiring exponential notation are refused rather than serialised in a
  form another implementation might not reproduce.
- Rate limiting is declared in the reason-code catalogue but is not implemented.
