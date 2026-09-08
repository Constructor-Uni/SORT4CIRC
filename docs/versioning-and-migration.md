# Versioning and migration

Public profile, schema, mapping, ontology and implementation are versioned as 2.0.0. API routes retain /v1 as an independent exchange-route major.

This candidate changes namespaces to fictional URIs, replaces source fixtures with independently invented records, removes project-coupled adapters and local maintenance routes, renames the external-system role and adopts X-DPP demo headers. Treat it as a breaking profile release.

A consumer must review its schema, vocabulary, namespace and access assumptions. Revalidate records and round-trip supported mappings. Do not relabel private records as synthetic or use this release as an automatic project-data migration. The new fixed digest vector applies only to the new fictional input; previous digests cannot be reused.

The owner-approved software/specification split is MIT and CC BY 4.0. See [LICENSING.md](../LICENSING.md) for exact paths, bundled specifications and the approved documentation/metadata and software/configuration scopes.
