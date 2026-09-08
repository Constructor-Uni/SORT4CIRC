# Integrity

The public implementation projects selected passport members, canonicalises them and computes SHA-256. The canonical tests contain a new fixed vector derived from SyntheticFixtureFactory, including a changed-value vector. Array order is significant; unrelated access and receipt fields are excluded from the integrity projection.

Synthetic example. Not SORT4CIRC project data.

The canonicaliser implements the restricted numeric and Unicode behaviour documented in its code and tests. It is not a general certification of every possible RFC 8785 input.

LedgerAdapter is a replaceable interface; InMemoryLedger is the only supplied implementation. Receipts represent simulated submission outcomes. match and mismatch compare digests; unanchored and unverifiable distinguish missing confirmation or unavailable evidence.

EvidenceWorker can be drained locally through Python. There is no public maintenance route. Memory state has no restart durability, external anchoring, operational finality or retention assurance. Hash agreement establishes byte-level agreement for the selected projection, not truth of product claims or legal conformity.
