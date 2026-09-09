# Traceability

Requirement area → specification asset → reference implementation → test. Use this page to
answer three questions about any part of the profile:

1. **Where is it defined?** Which machine-readable asset is authoritative.
2. **Is it implemented, or only specified?** Whether the reference implementation actually
   does it.
3. **Where does the requirement come from?** Whether it reflects a legal obligation, a
   standards-profile requirement, a project-scope requirement, or an engineering decision.

## Requirement origin

The profile mixes rules of very different authority, and conflating them is how a
specification ends up overclaiming. Four origins are distinguished throughout this page:

| Origin | Meaning |
| --- | --- |
| **Legal** | Derives from a legal obligation. **No row in this repository is classified this way**, because determining which obligations apply to a given product and organisation is outside what this profile can do. See [Regulatory context](regulatory-context.md). |
| **Standards** | Follows an external technical specification the profile adopts — JSON Schema 2020-12, RFC 3339, RFC 8785, RFC 9457, XSD 1.1, OWL 2 DL, SHA-256. |
| **Project scope** | Chosen because SORT4CIRC's use cases (textile sorting, reuse and recycling) require it. |
| **Engineering** | An architecture or design decision made in this profile. Another architecture may satisfy the same need differently. |

The distinction is practical: a **Standards** row constrains you if you claim to use that
standard; a **Project scope** row is a modelling choice you should evaluate against your
own use case; an **Engineering** row is one you may legitimately replace, provided the
external behaviour is preserved.

## Implementation status

| Status | Meaning |
| --- | --- |
| **Implemented** | The reference implementation does this, and tests exercise it |
| **Specified** | Defined in a specification asset; implementers must provide it |
| **Optional** | Part of the profile, not required for a valid passport |
| **Deployment-specific** | Deliberately left to the adopting organisation |
| **Out of scope** | Explicitly not part of the reference implementation |

## The map

### Identity and identifiers

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Passport identifier distinct from subject identifier | Engineering | `spec/schemas/dpp-1.0.0.schema.json` (`dppId`, `identity`) | `store.py` | `test_store.py` | Implemented |
| Absolute-URI form for URI-typed identifiers | Standards | schema `$defs.uri` | `validation.py` | `test_validation.py` | Implemented |
| Granularity requires the matching identifier | Project scope | schema `identity.allOf` | `validation.py` | `test_validation.py`, fixture `invalid-item-without-item-id` | Implemented |
| Identifier failure classification (unknown / malformed / ambiguous) | Engineering | `spec/reason-codes.json` | `gateway/readzone.py` | `test_readzone.py` | Implemented |
| Duplicate and retired binding refusal | Engineering | `spec/reason-codes.json` | `store.py` | `test_store.py` | Implemented |
| Your own URI namespace | — | — | — | — | Deployment-specific |
| GS1 EPC / Digital Link construction and check characters | Standards (external) | `encoding-scheme` vocabulary names the schemes | not implemented | — | Out of scope — follow the GS1 specifications directly |

Guide: [Identifiers](identifiers.md)

### Data model and validation

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Record structure, required members, closed objects | Engineering | `spec/schemas/dpp-1.0.0.schema.json` | `validation.py` | `test_validation.py` | Implemented |
| JSON Schema 2020-12 as the normative JSON validation path | Standards | the schema's `$schema` | `validation.py` (`jsonschema`) | `test_validation.py` | Implemented |
| RFC 3339 timestamps with a mandatory offset | Standards | schema `$defs.timestamp` | schema pattern | fixture `invalid-timestamp-without-offset` | Implemented |
| Quantity is `{value, unit}`; a bare number is never a quantity | Engineering | schema `$defs.quantity` | schema | `test_validation.py` | Implemented |
| Confidence requires an explicit scale | Engineering | schema `$defs.confidence` | schema | fixture `invalid-confidence-without-scale` | Implemented |
| Composition tolerance applied **within** an observation set | Project scope | documented in `validation.py` | `check_composition()`, `observation_sets()` | `test_validation.py`, fixture `invalid-composition-above-one-hundred` | Implemented |
| Absence states never coerced to zero or omission | Engineering | `value-status` vocabulary | `validation.py`, `mapping.py` | `test_mapping.py` | Implemented |
| Unit conversion between source and profile units | — | `S4C-MAP-UNIT-CONVERSION-FAILED` reserved | not implemented | — | Deployment-specific |

Guides: [Data model](concepts.md) · [Validation](validation.md)

### Provenance

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Every observation carries method, source and time | Project scope | schema `$defs.materialObservation.required` | `validation.py` | `test_validation.py`, fixture `invalid-observation-without-method` | Implemented |
| A non-`supplied` value status forbids a percentage | Engineering | schema `materialObservation.allOf` | schema | fixture `invalid-unknown-carrying-a-value` | Implemented |
| Percentage requires an explicit basis | Engineering | schema `materialObservation.allOf` | schema | fixture `invalid-percentage-without-basis` | Implemented |
| Conflicting observations retained, never merged | Project scope | schema (array) + `observation_sets()` | `store.py` append semantics | `test_mapping.py`, fixture `valid-two-technologies-disagree` | Implemented |
| A methodless or sourceless observation is inconsistent | Engineering | `spec/ontology/sort4circ-1.0.1.ttl` OWL restriction | ontology axiom | `test_mapping.py` | Specified |

Guide: [Provenance](provenance.md)

### Controlled vocabularies

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| 18 versioned vocabularies with per-term definitions | Project scope | `spec/vocabularies/*.json` | `vocab.py` | `test_vocab.py` | Implemented |
| Unknown token rejected, never coerced | Engineering | — | `Vocabulary.validate()` | `test_vocab.py`, fixtures `invalid-fibre-token`, `invalid-article-class-token` | Implemented |
| Vocabulary check separate from schema check, distinct codes | Engineering | `spec/reason-codes.json` | `validation.py` | `test_vocab.py` | Implemented |
| Every coded field bound to a vocabulary | Engineering | `FIELD_VOCABULARIES` | `vocab.py` | `test_vocab.py` | Implemented |
| Deprecation via `deprecated` + `replacedBy` | Engineering | vocabulary file format | `vocab.py` | `test_vocab.py` | Implemented |
| `manualReview` available in every sorting rule set | Project scope | `sorting-category` vocabulary | — | `test_vocab.py` | Specified |
| Domain terms outside textiles | — | — | — | — | Deployment-specific |

Guide: [Vocabularies](vocabularies.md)

### Data carriers

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Carrier binding as a first-class record with a lifecycle | Engineering | schema `carriers[]` | `store.commission_carrier()` | `test_store.py` | Implemented |
| `closedAt` required on a non-`commissioned` binding | Engineering | schema `carriers.allOf` | schema | `test_mapping.py` (XSD assertion) | Implemented |
| Atomic commissioning | Engineering | — | `store.py` | `test_store.py` | Implemented |
| Resolution endpoint, carrier → passport | Engineering | `spec/openapi/dpp-api-v1.json` | `api.py` | `test_api_contract.py` | Implemented |
| Carrier resolves; it does not embed the passport | Engineering | — | — | — | Specified |
| Reader configuration, antennae, power, transponder selection | — | — | — | — | Out of scope |
| TTRFID / sensing readings as attributed observations or events | Project scope | schema (`materialObservations`, `lifecycleEvents`) | — | — | Specified |

Guide: [Carrier binding](carrier-binding.md)

### Exchange API

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Route set and status codes | Engineering | `spec/openapi/dpp-api-v1.json` | `api.py` | `test_api_contract.py` | Implemented |
| RFC 9457 problem details with a reason code | Standards | `spec/reason-codes.json` | `reasons.py` | `test_api_contract.py` | Implemented |
| Reason-code catalogue with HTTP status and safe action | Engineering | `spec/reason-codes.json` | `reasons.py` | `test_api_contract.py` | Implemented |
| Optimistic concurrency (`If-Match` / `412`) | Standards | OpenAPI | `store._check_precondition()` | `test_api_contract.py` | Implemented |
| Conditional read (`If-None-Match` / `304`) | Standards | OpenAPI | `api.py` | `test_api_contract.py` | Implemented |
| Idempotency scoped to caller, org, role, operation, resource | Engineering | OpenAPI | `api._scoped_key()`, `store.idempotent()` | `test_api_contract.py` | Implemented |
| Cursor pagination, deterministic order, capped limit | Engineering | OpenAPI, `config.py` | `api.py` | `test_api_contract.py` | Implemented |
| Correlation identifier on every response | Engineering | — | `api.py` middleware | `test_api_contract.py` | Implemented |
| OpenAPI generated from the application, drift-checked | Engineering | `tools/gen_openapi.py` | — | `test_licensing.py`, CI | Implemented |
| Administrative endpoints in the exchange contract | Engineering | — | none by design | — | Out of scope — worker draining is a Python operation, not an HTTP route |
| Rate limiting | — | `S4C-RATE-LIMITED` reserved | not implemented | — | Deployment-specific |

Guide: [API guide](api.md)

### Access and security

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Default-deny role/scope/view matrix | Engineering | `spec/access-matrix.json` | `access.py` | `test_access.py` | Implemented |
| Scope necessary, never sufficient | Engineering | access matrix `note` | `require_scope()` + `project()` | `test_access.py` | Implemented |
| Too-wide view narrowed rather than refused | Engineering | — | `resolve_view()` | `test_access.py` | Implemented |
| Withheld fields marked, not dropped | Engineering | `value-status` vocabulary | `_observation_for()` | `test_access.py` | Implemented |
| `partner` view scoped to the caller's organisation | Engineering | access matrix `views.partner` | `project()` | `test_access.py` | Implemented |
| Append-only members refused on `PATCH` | Engineering | `spec/reason-codes.json` | `check_patch_paths()`, `store._guard_append_only()` | `test_access.py`, `test_store.py` | Implemented |
| Fail-closed default identity (`PublicOnlyAuth`) | Engineering | — | `auth.py`, `api.py` | `test_api_contract.py` | Implemented |
| Header demo identity opt-in only | Engineering | — | `DPP_DEMO_AUTH`, `docker/compose.example.yml` | `test_api_contract.py` | Implemented |
| Real credential verification | — | `AuthProvider` protocol | not implemented — `DemoAuth` verifies nothing | — | Deployment-specific |
| Transport security, secrets, key management, audit logging, monitoring | — | — | — | — | Out of scope |

Guides: [Security model](security.md) · [Customisation](customisation.md)

### Representations and semantics

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| One mapping row per schema-defined exchange path | Engineering | `spec/mappings/dpp-mapping-1.0.0.json` | `mapping.py` | `test_mapping.py` | Implemented |
| Generated CSV rendering, drift-checked | Engineering | `tools/gen_mapping_csv.py` | — | `test_mapping.py` | Implemented |
| XSD 1.1 projection with conditional assertions | Standards | `spec/schemas/dpp-1.0.0.xsd` | `exchange.py` | `test_mapping.py`, `test_exchange.py` | Implemented |
| One XML serialiser, not two | Engineering | mapping contract | `exchange.py`; `mapping.py` delegates | `test_mapping.py` | Implemented |
| XML content negotiation on the exchange API | Engineering | `spec/openapi/dpp-api-v1.json` | `api.py` | `test_exchange.py` | Implemented |
| JSON ↔ XML round trip without information loss | Engineering | mapping contract | `json_to_xml`, `xml_to_json` | `test_mapping.py` | Implemented |
| OWL 2 DL ontology; EL subset explicitly excluded | Standards | `spec/ontology/sort4circ-1.0.1.ttl` header | — | `test_mapping.py` | Specified — the deviation is recorded, not hidden |
| RDF projection resolves to ontology terms | Engineering | ontology + mapping rows | `mapping.py` (`json_to_rdf`) | `test_mapping.py` | Implemented |
| SPARQL conformance queries with expected results | Engineering | `spec/queries/*.rq`, `expected-results-1.0.0.json` | — | `test_exchange.py` | Implemented |
| Governance record schemas for selection and deviation | Project scope | `spec/governance/*.schema.json` | `governance.py` | `test_governance.py` | Implemented — templates ship unpopulated; the records themselves are deployment-dependent |
| Specification resources available from an installed distribution | Engineering | `src/sort4circ_dpp/_spec/**` | `config.py` | `test_packaged_resources.py` | Implemented |
| JSON ↔ RDF round trip without information loss | Engineering | mapping contract | `json_to_rdf`, `rdf_to_json` | `test_mapping.py` | Implemented |
| Transport snapshot not counted as semantic coverage | Engineering | `rdfMappingStatus` column | `mapping.py` | `test_mapping.py` | Implemented |
| Alignment with external vocabularies (GS1, event standards, EU registries) | — | — | not implemented | — | Out of scope — define and test your own alignment |

Guide: [Representations and semantics](interoperability.md)

### Lifecycle and sorting

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Event time separate from recorded time | Project scope | schema `$defs.lifecycleEvent` | `api.py`, `store.py` | `test_api_contract.py` | Implemented |
| Local offset carried separately | Project scope | schema `eventTimeZoneOffset` | schema | `test_mapping.py` | Implemented |
| Transformation requires inputs and outputs | Project scope | schema + ontology restriction | schema, XSD assertion | `test_mapping.py` | Implemented |
| Corrections by `correctsEventId`, never deletion | Engineering | schema | append-only store | `test_store.py` | Implemented |
| Decision cites observations and rule-set version | Project scope | schema `$defs.sortingDecision` | schema | `test_mapping.py` | Implemented |
| Override requires a reason | Project scope | schema `sortingDecision.allOf` | schema, XSD assertion | `test_mapping.py` | Implemented |
| Sorting view as an operational projection | Engineering | OpenAPI | `index.py` | `test_index_staleness.py` | Implemented |
| Caller-selected consistency with reported lag | Engineering | OpenAPI | `index.py` | `test_index_staleness.py` | Implemented |
| Physical line behaviour, routing hardware, safety interlocks | — | — | — | — | Out of scope |

Guides: [Lifecycle events](lifecycle-events.md) · [Sorting integration](sorting-integration.md)

### Integrity

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Explicit digest field projection | Engineering | `canonical.py` constants | `integrity_projection()` | `test_canonical.py` | Implemented |
| RFC 8785 canonicalisation (restricted input set) | Standards | `canonical.py` | `canonicalise()` | `test_canonical.py` | Implemented — restricted, not a general RFC 8785 certification |
| SHA-256 digest, lower-case hex | Standards | schema `integrityEntry.digestValue` | `digest()` | `test_canonical.py` | Implemented |
| Evidence envelope carries no passport content | Engineering | — | `envelope_for()` | `test_evidence.py` | Implemented |
| Evidence state machine with validated transitions | Engineering | `evidence-state` vocabulary | `evidence.py` | `test_evidence.py` | Implemented |
| Ledger adapter contract, idempotent submit | Engineering | `ledger/base.py` | `InMemoryLedger` | `test_ledger_contract.py` | Implemented (mock adapter only) |
| Four distinct verdicts | Engineering | `ledger/base.py` | `LedgerAdapter.verify()` | `test_ledger_contract.py` | Implemented |
| Asynchronous anchoring off the write path | Engineering | — | `EvidenceWorker` | `test_evidence.py` | Implemented |
| A deployed ledger, network, account, keys or contract | — | — | none supplied | — | Out of scope — deliberate publication boundary |
| Retention sufficient for later verification | — | — | — | — | Deployment-specific |

Guide: [Integrity](integrity.md)

### Scalability, durability, operations

| Requirement | Origin | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- | --- |
| Cursor pagination with deterministic ordering | Engineering | OpenAPI | `api.py` | `test_api_contract.py` | Implemented |
| Optional projection lag bound, caller-selected | Engineering | — | `ReadIndex.max_lag_ms` | `test_index_staleness.py` | Implemented — no deployment default is supplied |
| Durable storage | — | `PassportStore` interface | in-memory only | `test_store.py` | Deployment-specific |
| Horizontal scaling, load balancing, backpressure, archival, recovery | — | — | — | — | Deployment-specific |
| Performance targets | — | — | none | — | Out of scope — this repository records no results and sets no target |

Guides: [Scalability](scalability.md) · [Testing methodology](testing-methodology.md)

### Publication and licensing

These rows concern this repository's own release process rather than the DPP profile. They
are listed so nothing in the tree is unaccounted for.

| Requirement | Specification asset | Implementation | Test | Status |
| --- | --- | --- | --- | --- |
| Explicit public file allowlist | `public-release-policy.json` | `tools/verify_public_release.py` | `test_public_release.py`, `test_manifest.py` | Implemented |
| Generated manifests and checksums | `MANIFEST.in`, `MANIFEST.sha256` | `verify_files.py` | `test_manifest.py` | Implemented |
| Component licence coverage for every public file | `LICENSING.md` | — | `test_licensing.py` | Implemented |
| Allowlisted conformance summary export | — | `public_summary.py` | `test_public_summary.py` | Implemented |
| Human publication review | — | — | — | Deployment-specific |

Guide: [Release verification](public-release.md)

## How to use this page

- **Adopting the profile?** Read the Origin column. **Engineering** rows are decisions you
  may replace if you preserve the external behaviour. **Project scope** rows are modelling
  choices to evaluate against your use case. **Standards** rows constrain you if you claim
  the standard.
- **Assessing coverage?** Read the Status column. *Implemented* has a test; *Specified*
  means you must supply it; *Deployment-specific* and *Out of scope* mean this repository
  deliberately does not.
- **Extending the profile?** Add a row. A new requirement with no specification asset and
  no test is not yet part of the profile.

## Related pages

- [Conformance](conformance.md) — how to exercise each area
- [Regulatory context](regulatory-context.md) — why no row is classified as legal
- [Customisation](customisation.md) — replacing the Engineering rows
