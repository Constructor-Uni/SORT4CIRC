# Customisation

The three components the reference implementation expects you to replace, and what each
replacement must preserve.

~~~python
from sort4circ_dpp.api import create_app

app = create_app(
    store=MyDurableStore(),
    ledger=MyLedgerAdapter(),      # optional; only needed for Tier 3
    auth_provider=MyAuth(),
)
~~~

All three are injected. Nothing else in the application holds state.

## 1. `AuthProvider` — required before any deployment

Implement `authenticate(headers) -> Principal`, returning a **verified** principal or
raising.

~~~python
from collections.abc import Mapping
from sort4circ_dpp.access import Principal
from sort4circ_dpp.reasons import DppError

class MyAuth:
    def authenticate(self, headers: Mapping[str, str]) -> Principal:
        token = headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not token:
            raise DppError("S4C-AUTH-MISSING-TOKEN")
        claims = verify_token(token)          # signature, expiry, audience, issuer
        return Principal(
            subject=claims["sub"],
            role=map_to_profile_role(claims),  # must exist in the access matrix
            organisation_id=claims.get("org"),
        )
~~~

Must preserve:

- **actual verification.** `DemoAuth` verifies nothing; that is its entire deficiency and
  the reason it must never protect a deployed system.
- **a role from the access matrix.** An unrecognised role has no scopes and no view.
- **a correct `organisation_id`.** The `partner` view's isolation depends on it; a wrong
  value discloses another organisation's lifecycle events.
- **distinct auth failures.** `S4C-AUTH-MISSING-TOKEN`, `S4C-AUTH-INVALID-TOKEN` and
  `S4C-AUTH-EXPIRED-TOKEN` have different client remedies.

Keep `tests/test_access.py` passing, and add tests for **your** provider's failure cases:
expired, malformed, replayed, wrong audience, absent. Those cases are not testable from
this repository. See [Security model](security.md).

## 2. `PassportStore` — required for anything durable

The in-memory store is a reference for the required *semantics*, not a database
abstraction. A replacement must provide:

| Semantic | Requirement |
| --- | --- |
| Versioning | `recordVersion` advances on every committed change; earlier versions remain retrievable by version |
| Append-only | `materialObservations`, `lifecycleEvents`, `sortingDecisions` and `integrity` entries are never modified or removed |
| Uniqueness | A `dppId` is created once; an encoded carrier identifier binds to at most one active passport |
| Retirement | A retired carrier identifier is never reassigned to a different product |
| Idempotency | A key scoped to caller, organisation, role, operation and resource returns the original result for the same body, and conflicts for a different one |
| Conditional update | `If-Match` against the current `ETag`, with `S4C-STATE-VERSION-CONFLICT` on a mismatch |
| Atomic carrier commissioning | Either binding, encoded value and status are all created, or none are |
| Commit notification | Something equivalent to `on_commit`, so projections can be maintained |

Two consequences to plan for:

- **Version retention interacts with integrity.** If you anchor a digest of version 4 and
  later prune version 4, verification returns `unverifiable`. Decide the retention window
  and the anchoring policy together. See [Integrity](integrity.md).
- **Transactionality is yours.** The memory store uses a process lock. A distributed store
  needs real transactions or a documented consistency model, and the append-only and
  uniqueness guarantees above must survive concurrent writers.

`python -m pytest tests/test_store.py -q` is the semantic contract; run it against your
implementation if you can adapt it, and reproduce its assertions if you cannot.

## 3. `LedgerAdapter` — only if you need Tier 3

Implement four methods (`submit`, `status`, `anchored_digest`, `verify`) from
[`ledger/base.py`](../src/sort4circ_dpp/ledger/base.py). `verify` has a default
implementation deriving the four verdicts from `status` and `anchored_digest`, so most
adapters implement three.

~~~sh
python -m pytest tests/test_ledger_contract.py -q
~~~

The contract tests run against **any** adapter. Beyond them, you need private tests for
provider-specific behaviour, retention, key management and recovery — none of which this
repository supplies a recipe for.

Any platform is acceptable — permissioned or public ledger, notary, transparency log,
internal append-only store, signed timestamp — provided idempotent submission, retrievable
receipts, a retrievable anchored digest and the four verdicts are preserved. Keep passport
content out of the envelope.

## 4. Adapting the specification assets

If your products or processes need different terms or fields, change the assets — but
change them **together**, or the representations diverge.

1. **Schema** — [`spec/schemas/dpp-1.0.0.schema.json`](../spec/schemas/dpp-1.0.0.schema.json)
2. **Vocabularies** — add terms rather than redefining existing ones; retire with
   `deprecated` + `replacedBy`; bind new coded fields in `FIELD_VOCABULARIES`
3. **XSD** — [`spec/mappings/dpp-1.0.0.xsd`](../spec/mappings/dpp-1.0.0.xsd)
4. **Ontology** — [`spec/ontology/sort4circ-1.0.0.ttl`](../spec/ontology/sort4circ-1.0.0.ttl)
5. **Mapping** — a row per new exchange path in
   [`spec/mappings/dpp-mapping-1.0.0.json`](../spec/mappings/dpp-mapping-1.0.0.json), then
   regenerate the CSV
6. **Access matrix** — if a new field needs a view decision, make it explicitly
7. **Fixtures** — a positive fixture for the new behaviour and a negative fixture proving
   the invalid case is still rejected
8. **Version everything** — treat it as a new profile release, and construct synthetic
   migration examples

~~~sh
python -m pytest -q
python tools/gen_mapping_csv.py
python tools/gen_openapi.py
python tools/validate_fixtures.py
~~~

If you add public files, list them in `public-release-policy.json`, give them licence
coverage in `LICENSING.md`, and regenerate the manifests with `python verify_files.py
--write`. See [CONTRIBUTING.md](../CONTRIBUTING.md) and
[Versioning and migration](versioning-and-migration.md).

## What customisation does not give you

Validation against your adapted profile establishes that records fit **your** profile. It
does not establish regulatory compliance, and it does not make a claim in a record true.
Review product-specific obligations with appropriate expertise; see
[Regulatory context](regulatory-context.md).

## Related pages

- [Security model](security.md) · [Scalability](scalability.md) · [Integrity](integrity.md)
- [Architecture](architecture.md) — where each component sits
- [Traceability](traceability.md) — which rows are Engineering decisions you may replace
