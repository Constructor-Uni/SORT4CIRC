# Educational architecture

The local example separates an exchange API, an access policy, a memory repository, a read projection and a mock integrity interface. This is a teaching design, not a description of a project deployment.

create_app accepts a PassportStore, LedgerAdapter and AuthProvider. PassportStore retains version snapshots and append-only collection entries in process memory. ReadIndex demonstrates projected reads; an optional caller-selected lag bound can reject an outdated projection while a strong read accesses the store. No physical-line settings or latency targets are implied.

CarrierResolver classifies absent, malformed, unreadable and ambiguous observations before identifier resolution. It issues no hardware commands and models no radio settings.

LedgerAdapter separates submit, status, anchored_digest and verify. InMemoryLedger supports deterministic simulated outcomes for contract tests. EvidenceWorker demonstrates local queue processing and reconciliation in memory. There is no network topology or operational signing arrangement.

AuthProvider supplies a Principal to the access policy. PublicOnlyAuth is the default. DemoAuth accepts role headers only when explicitly selected. Replacing it requires real identity verification and a deployment-specific security assessment.

See [Customisation](customisation.md) for extension responsibilities.
