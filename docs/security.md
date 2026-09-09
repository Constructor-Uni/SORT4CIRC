# Security model

The access model the profile defines, the secure defaults the reference implementation
ships with, and what you must replace before anything goes near a real deployment.

To **report** a vulnerability, see [SECURITY.md](../SECURITY.md). This page is about
implementing the model.

## The starting point: this is not a production security configuration

Say it plainly. The reference implementation:

- stores everything in process memory;
- ships a mock integrity backend;
- has **no** credential validation of any kind;
- offers a header-based demo identity that is **not authentication**.

It is a teaching implementation of an access *model*. The model is the part worth adopting;
the identity mechanism must be replaced entirely.

## Secure defaults

The default identity provider is `PublicOnlyAuth`. It:

- returns the anonymous public principal;
- grants `dpp.read` only, with the `public` view;
- **rejects** any request carrying an `X-DPP-Role` header, with
  `S4C-AUTH-INVALID-TOKEN`.

That last behaviour is the point. A service running with the default configuration does not
quietly ignore a claimed role — it refuses the request, so a misconfiguration is loud.

`DemoAuth` is opt-in through `DPP_DEMO_AUTH=1`, and the Docker compose example defaults it
to `0` (`DPP_DEMO_AUTH: "${DPP_DEMO_AUTH:-0}"`). To use the write examples locally you set
the variable explicitly:

~~~sh
# sh/bash
DPP_DEMO_AUTH=1 python -m uvicorn sort4circ_dpp.api:app --host 127.0.0.1 --port 8000
DPP_DEMO_AUTH=1 docker compose -f docker/compose.example.yml up --build

# PowerShell
$env:DPP_DEMO_AUTH = "1"; python -m uvicorn sort4circ_dpp.api:app --host 127.0.0.1 --port 8000
~~~

**Anyone who can reach a service with `DPP_DEMO_AUTH=1` can assert any role, including
`administrator`.** Bind it to loopback, use synthetic records only, and never expose it.

The compose example also runs the container read-only, drops all capabilities, sets
`no-new-privileges`, publishes only on `127.0.0.1`, and ships no secrets. It is a
reasonable local demo, not a hardened deployment.

## The access model

Three layers, and all three apply to every request. This is the part to reproduce in your
own implementation.

~~~
identity (who)  →  scope (may they perform this operation)  →  view (what do they receive)
~~~

The policy is **data**, not code: [`spec/access-matrix.json`](../spec/access-matrix.json),
version 1.0.0, `"policy": "defaultDeny"`.

### Roles and scopes

| Role | Scopes | Default view |
| --- | --- | --- |
| `public` | `dpp.read` | `public` |
| `consumer` | `dpp.read` | `public` |
| `brand` | `dpp.read`, `dpp.write`, `dpp.event`, `dpp.resolve`, `observation.write`, `integrity.read` | `full` |
| `collector` | `dpp.read`, `dpp.event`, `dpp.resolve` | `partner` |
| `sortingOperator` | `dpp.read`, `dpp.event`, `dpp.resolve`, `sorting.read` | `sorting` |
| `pssrSystem` | `dpp.read`, `dpp.resolve`, `sorting.read`, `observation.write`, `dpp.event` | `sorting` |
| `recycler` | `dpp.read`, `dpp.event`, `dpp.resolve` | `recycler` |
| `authority` | `dpp.read`, `integrity.read`, `integrity.verify` | `authority` |
| `integrityVerifier` | `dpp.read`, `integrity.read`, `integrity.verify` | `integrityOnly` |
| `administrator` | all, plus `admin` | `full` |

### Views

Ordered narrowest to widest:

`integrityOnly` → `public` → `partner` → `sorting` → `recycler` → `authority` → `full`

| View | Contains |
| --- | --- |
| `integrityOnly` | `dppId` and the integrity array. Nothing about the product. |
| `public` | Status, granularity, article class, construction, technical flags, material observations — with the source organisation withheld |
| `partner` | Public, plus model and batch identifiers, plus **only the caller's own** lifecycle events |
| `sorting` | Public, plus item and carrier identifiers, colour, condition, sorting decisions and active carrier bindings |
| `recycler` | Sorting, plus components and mass |
| `authority` | Sorting and recycler, plus all lifecycle events, integrity, full identity, carriers and environmental values |
| `full` | Everything |

### Three behaviours worth copying

**Holding a scope is necessary and never sufficient.** The scope decides whether the
operation is permitted; the view decides what comes back. A caller with `dpp.read` and a
caller with `dpp.read` can receive very different documents.

**Narrow rather than refuse.** A caller requesting a view *wider* than their default
receives their default, not an error. A tightening policy therefore returns less instead of
breaking a working integration. The exception is `integrityVerifier`, which may only ever
receive `integrityOnly` and gets an explicit `S4C-AUTHZ-VIEW-FORBIDDEN` otherwise.

**Mark withheld fields; do not drop them.** Where a role may know a field exists but not
read its value, the projection returns an explicit marker rather than omitting the member.
The public view of an observation replaces `sourceOrganisationId` with
`"sourceOrganisationStatus": "withheld"`. Silently omitting it would let a consumer
conclude the data was never collected — which is a different and false statement. This is
why `withheld` is a `value-status` token and not just an access-layer artefact.

### Organisation scoping

The `partner` view filters `lifecycleEvents` by the principal's `organisation_id`: a
collector sees the events its own organisation participated in and none of a competitor's.
A `partner` principal with no organisation receives an empty event list, not everything.

### Write-path restrictions

`WRITABLE_PATHS` ([`access.py`](../src/sort4circ_dpp/access.py)) limits what `PATCH` may
touch:

- `brand`: `product`, `identity.sourceRecordId`, `registryIdentifier`,
  `environmentalValues`;
- `administrator`: everything;
- every other role: nothing — `S4C-AUTHZ-OPERATION-FORBIDDEN`.

Separately, `materialObservations`, `lifecycleEvents`, `sortingDecisions` and `integrity`
are append-only and are refused on `PATCH` with `S4C-STATE-APPEND-ONLY-VIOLATION`
regardless of role. Refused paths are named in the error rather than silently dropped, so
an integration learns which member was rejected instead of guessing why its update had no
effect.

## Replacing the identity provider

This is required before any deployment. Implement the `AuthProvider` protocol:

~~~python
from collections.abc import Mapping
from sort4circ_dpp.access import Principal
from sort4circ_dpp.reasons import DppError

class MyAuth:
    def authenticate(self, headers: Mapping[str, str]) -> Principal:
        token = headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not token:
            raise DppError("S4C-AUTH-MISSING-TOKEN")
        claims = verify_token(token)          # real signature and expiry verification
        return Principal(
            subject=claims["sub"],
            role=map_to_profile_role(claims),  # must be a role in the access matrix
            organisation_id=claims.get("org"),
        )

app = create_app(auth_provider=MyAuth())
~~~

Requirements:

- **verify** the credential — signature, expiry, audience, issuer. `DemoAuth` performs no
  verification whatsoever; that is its entire deficiency.
- map external claims to a role in the access matrix. Do not invent roles at runtime; an
  unknown role has no scopes and no view.
- set `organisation_id` correctly — the `partner` view's isolation depends on it, and a
  wrong value discloses another organisation's events.
- raise `S4C-AUTH-MISSING-TOKEN`, `S4C-AUTH-INVALID-TOKEN` or `S4C-AUTH-EXPIRED-TOKEN` as
  appropriate; these are distinct conditions with distinct client remedies.
- keep the access-policy tests passing, and add tests for **your** provider's failure
  cases: expired, wrong audience, replayed, malformed, absent.

`DemoAuth` must never become a production identity mechanism, and no configuration should
make it reachable from anywhere but loopback.

## Deployment concerns the profile does not solve

These are outside the reference implementation, and each needs its own design and
assessment:

| Concern | Note |
| --- | --- |
| Transport security | TLS termination, certificate management, HSTS |
| Credential issuance | Token lifetimes, rotation, revocation, key management |
| Rate limiting | `S4C-RATE-LIMITED` exists as a reason code; no limiter is implemented |
| Audit logging | Log the principal, operation, resource and correlation identifier — never the credential |
| Durable storage | The memory store has no persistence, backup or recovery |
| Secrets management | No secret store, no key material, nothing to configure here |
| Network exposure | The compose example is loopback-only by design |
| Monitoring and alerting | Not provided |
| Data protection | If any deployment field could hold personal data, that is a legal assessment you must make |

`X-Correlation-Id` is echoed on every response and included in every problem document. Use
it. Do not log request bodies wholesale — passports can carry commercially sensitive
content.

## Things not to put in a passport

The record is exchanged across organisational boundaries and projected to roles you do not
control. Do not place in any field — including identifiers, `sourceSystemId`,
`evidenceRef`, `resolverUri` or `placement`:

- credentials, API keys, tokens or private keys;
- personal data;
- internal hostnames, private endpoints or infrastructure detail;
- commercially sensitive values a partner or public view might expose.

Identifiers are the trap: they travel further than the data behind them, they are printed
on physical objects, and they are rarely reviewed. See
[Carrier binding](carrier-binding.md#what-never-goes-on-a-carrier).

## Testing the access model

~~~sh
python -m pytest tests/test_access.py tests/test_api_contract.py -q
~~~

These check default-deny, scope enforcement, view narrowing, the withheld marker,
organisation scoping, append-only refusal and the `PATCH` path restrictions. They test the
**model**; they cannot test your identity provider, your transport, or your deployment.
See [Conformance](conformance.md) for what is and is not machine-testable.

## Related pages

- [Customisation](customisation.md) — replacing storage, identity and the ledger adapter
- [API guide](api.md) — where scopes and views apply per endpoint
- [Integrity](integrity.md) — the verifier role and evidence access
- [SECURITY.md](../SECURITY.md) — reporting a vulnerability privately
