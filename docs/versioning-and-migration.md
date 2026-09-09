# Versioning and migration

What is versioned, what a version change means for a consumer, and how to migrate.

## Two version numbers

The most common source of confusion. These are deliberately independent:

| | Version | What it means |
| --- | --- | --- |
| **Normative profile** | **1.0.0** | The SORT4CIRC DPP implementation profile: schema, vocabularies, mappings, ontology, access matrix and reason codes. Changing it changes what a conformant record *is*. |
| **This repository and package** | **1.3.0** | The reference implementation, its documentation and its tooling. Changing it does not redefine the profile. |

Repository release v1.3.0 implements DPP implementation profile 1.0.0. A new repository release does
**not** mean your records need revalidating; a new *profile* version would.

## What carries a version

| Thing | Current | Notes |
| --- | --- | --- |
| Profile: schema, vocabularies, mappings, ontology, access matrix, reason codes | **1.0.0** | Versioned together. A change to one is a change to the profile. |
| Repository, Python package, GitHub release | **1.3.0** | `sort4circ_dpp.__version__`. Independent of the profile. |
| API route prefix | **`/v1`** | An independently versioned exchange-route major. Route shape changes far less often than payload content. |
| `schemaVersion` in every payload | **1.0.0** | Lets a consumer decide how to read the document |
| `accessPolicyVersion` | **1.0.0** | Which access-matrix release applied when the projection was produced |
| `recordVersion` | per record | A monotonic integer, advanced by every committed change |
| Mapping rows | `mappingVersion` per row | Rows are individually versioned within the mapping package |

The specification assets are versioned **together** on purpose. A vocabulary token added
without a corresponding XSD, ontology and mapping update produces representations that
disagree, and `tests/test_mapping.py` is designed to catch exactly that.

## Record versions

`recordVersion` advances on every committed change: a `PATCH`, an appended observation, an
appended event, a commissioned carrier. Earlier versions are retained.

That retention is not optional if you use integrity evidence. Verification recomputes the
digest from the record **at the anchored `subjectVersion`**; if that version is gone, the
verdict is `unverifiable`. Decide your retention window and your anchoring policy together.
See [Integrity](integrity.md).

`ETag` reflects the current version and drives conditional reads (`If-None-Match` → `304`)
and optimistic concurrency (`If-Match`, else `412 S4C-STATE-VERSION-CONFLICT`).

## Superseding a record

Records are superseded, not deleted:

- set `status` to `superseded`;
- set `supersededBy` to the replacement's `dppId`;
- the physical subject is unchanged, so the new record keeps the same `identity`.

Resolution of a carrier identifier bound to a closed binding returns `410`
`S4C-IDENT-RETIRED`, carrying the superseding record where one is known — so an old tag
still leads a reader somewhere useful.

The same principle applies to lifecycle events: correct with `correctsEventId`, never by
deletion. Deleting destroys the fact that the record once said something else, which is
usually the most important fact in a dispute.

## What repository release 1.3.0 changed

Release 1.3.0 changes the **software, documentation and tooling**, not the normative
profile. The implementation profile stays at 1.0.0, so records valid under v1.1.1 remain valid and
**no migration is required**:

- developer-oriented documentation: a task-based README, a quickstart, a first-DPP
  walkthrough, and guides for identifiers, validation, provenance, vocabularies, lifecycle
  events, carrier binding, enterprise and sorting integration, security and scalability;
- implementation tiers, so the profile can be adopted incrementally rather than at once;
- an explicit public-file policy with generated manifests and checksums;
- a fail-closed demo identity default, opt-in via `DPP_DEMO_AUTH=1`;
- removal of the reference implementation's local evidence-drain route from the **public**
  OpenAPI contract. This was never part of the interoperability surface: it is
  implementation administration, and its absence does not change the profile.

Digests, canonical vectors, vocabularies, namespaces and the access matrix are unchanged
from profile 1.0.0. The canonical reference digest remains the published Annex G value.

## Versioning your own extensions

If you adapt the profile, version your adaptation. The rules that matter:

1. **Add rather than redefine.** Changing what an existing token or field means invalidates
   every record already using it, retroactively and silently.
2. **Retire with `deprecated` and `replacedBy`** instead of deleting. Deleting makes
   historical records unvalidatable.
3. **Change every representation together** — schema, vocabularies, XSD, ontology, mapping,
   access matrix.
4. **Add fixtures with the change**, positive and negative, and construct synthetic
   migration examples.
5. **Record which version produced a record.** For an ERP or MES pipeline this includes the
   mapping-table version; see
   [Enterprise integration](enterprise-integration.md#version-your-mapping).

`python -m pytest -q` plus `python tools/gen_mapping_csv.py --check` and
`python tools/gen_openapi.py --check` will tell you whether the assets have drifted apart.
See [Customisation](customisation.md).

## Licensing across versions

The component split is MIT for software and CC BY 4.0 for documentation and specifications.
[LICENSING.md](../LICENSING.md) records the exact per-path coverage, and a new public file
must be assigned an explicit component scope when it is added.

## Related pages

- [Data model](concepts.md) — where the version fields live
- [Conformance](conformance.md) — version and migration compatibility checks
- [Customisation](customisation.md) — adapting the assets safely
