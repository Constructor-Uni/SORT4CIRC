# Customisation

Implement AuthProvider.authenticate to return a verified Principal or reject a request. Preserve the access-policy tests and add tests for your identity provider's failure cases. DemoAuth must not become a production identity mechanism.

Replace PassportStore with storage that provides the required version, append, uniqueness, idempotency and conditional-update semantics. The memory implementation is a reference API, not a durable database abstraction with transactional guarantees.

Implement LedgerAdapter only if your application needs an integrity backend. Exercise the generic contract tests plus provider-specific integration, retention and recovery tests in your own private environment. No deployed backend recipe is supplied.

Adapt schemas, vocabularies and mappings together. Version changes explicitly and construct new synthetic migration examples. Review product-specific obligations with suitable expertise; validation here does not establish compliance.
