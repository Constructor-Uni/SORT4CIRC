# Conformance

## What may be claimed

A conformance statement names a tier, the specification version, the artefact
versions, and every checklist row not passed. A statement that names no tier is
not a conformance statement, and a statement that omits a failed row is not a
redaction but a misstatement.

Alignment with a harmonised standard is not conformity assessment. Citing
EN 18219 means the identifier profile follows that standard's method; it does
not mean a notified body has assessed anything, and presumption of conformity
extends only to the requirements the cited standard actually covers.

Referencing ISO/IEC 27001 is not certification. Certification is claimed only
where a valid certificate exists.

## The tiers

Tiers are cumulative. Tier 2 includes every tier 1 control; tier 3 includes
every tier 2 control.

**Tier 1, Core passport.** A persistent record at one declared granularity, a
carrier bound to it, the mandatory field set, explicit unknown-value states,
provenance on every observation, and an authenticated read API returning the
public and partner views.

**Tier 2, Operational passport.** Adds lifecycle and sorting events, the write
path with idempotency and optimistic concurrency, the sorting projection, the
observation interface, the translation layer with per-batch reconciliation, and
the full access matrix.

**Tier 3, Assured passport.** Adds deterministic digests, ledger anchoring
through a replaceable adapter, independent verification of an altered record,
the measured performance and recovery campaign, and the change and migration
regime.

## Running the checks

```bash
make conformance
```

This produces `conformance-report.json`, which separates rows decided by the
test suite from rows that require human evidence. The second list is published
deliberately. A suite that quietly omitted those rows would read as full
coverage when it is not.

## Rows this repository cannot decide

Many checklist rows need something a test cannot produce: a metered
energy measurement, an executed load campaign against real hardware, a signed
scope decision, a security scan of a deployed configuration, an
industrial-security zone assessment, or the blockchain benchmark itself. Each is
listed in `tests/conformance/test_checklist.py` together with the evidence that
would decide it.

## Evidence discipline

Three evidence types carry different weight and are never conflated.

**Executed test.** A result produced by running the named artefact in the named
configuration against the named dataset. Only this type supports a performance
or correctness claim.

**Inspection.** A recorded examination of a configuration, document or code path
by a named reviewer. Supports a structural claim such as "no credential appears
in the logs". Does not support a performance claim.

**Documentary.** A statement by a supplier or a published specification.
Supports an applicability decision such as which consensus mechanism a platform
uses. Supports nothing about the behaviour of a deployed system.

The exclusion-gate assessment of EBSI, Algorand, IOTA and Ethereum in D4.3 is
documentary. The latency figures are targets awaiting executed tests. Recording
either as an executed test would misrepresent the state of the work, and an
assessor is entitled to treat such a misrecording as a finding in itself.
