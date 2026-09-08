# Getting started

Synthetic example. Not SORT4CIRC project data.

1. **Understand a DPP.** A passport connects an identifier to structured product information, observations and lifecycle records. See [Concepts](concepts.md).
2. **Understand the public profile.** Version 2.0.0 defines required fields, controlled terms and exchange behaviour. Its normative rules apply only to this public profile.
3. **Create a synthetic passport.** Install locally with python -m pip install -e ".[dev]". Run python -m sort4circ_dpp.cli example to inspect the deterministic example. In Python, call SyntheticFixtureFactory().passport(); its returned dict can be written as UTF-8 JSON.
4. **Validate it.** Run python -m sort4circ_dpp.cli validate examples/fixtures/valid-synthetic-textile.json. Negative fixtures include a test-only $expect member which the fixture runner removes. Run python tools/validate_fixtures.py to check both positive and negative cases.
5. **Resolve and retrieve it.** Run python examples/worked_example.py. This uses an in-process API client, explicitly opts into demo identities, creates a passport and binds a fictional carrier before resolving it. For an interactive local server use the compose example or set DPP_DEMO_AUTH=1 explicitly and run python -m uvicorn sort4circ_dpp.api:app --host 127.0.0.1 --port 8000. View http://127.0.0.1:8000/docs locally.
6. **Record provenance and lifecycle information.** The worked example appends an attributed observation and a collection event. Each has an independent identifier and timestamp. See [Concepts](concepts.md).
7. **Try optional integrity.** The example drains the local in-memory worker through Python and verifies the resulting digest. This is a mock correctness exercise. See [Integrity](integrity.md).
8. **Run public-profile tests.** Run python -m pytest -q and python tools/conformance_report.py. The latter emits an allowlisted summary; it does not publish raw test output.
9. **Replace demo components.** Implement AuthProvider, replace PassportStore as needed and supply a LedgerAdapter to create_app. Review access scopes and recovery semantics. See [Customisation](customisation.md).
10. **Adapt responsibly.** Identify your product and organisational needs independently, version any profile changes and obtain appropriate regulatory and security review. This repository provides no legal conformity assessment.
