# Synthetic examples

Synthetic example. Not SORT4CIRC project data.

SyntheticFixtureFactory independently invents woven home-textile records, fictional organisations, carrier URIs, declarations and a collection event. Its deterministic values support reproducible tests. The factory has no dependency on source project records.

fixtures contains positive and deliberately invalid examples. Negative examples carry a test-only $expect reason code, removed before validation by tools/validate_fixtures.py. worked_example.py creates, resolves and updates a fictional passport and verifies mock integrity through an in-process API client.

Run python examples/worked_example.py after installing the development dependencies. No external service or hardware is contacted.
