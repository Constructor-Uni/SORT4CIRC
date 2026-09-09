# Glossary

Terms as this profile uses them. Where a term is used differently elsewhere, the definition
here is the one the specification assets follow.

| Term | Definition |
| --- | --- |
| **DPP** | Digital Product Passport: a structured, versioned product record reachable through an identifier. |
| **Passport identifier** (`dppId`) | Identifies the **record**. Stable for the record's life. Not the same as the item identifier. |
| **Item / batch / model identifier** | Identifies the **subject** the record is about, at the declared granularity. |
| **Granularity** | Whether the record describes a design (`model`), a lot (`batch`) or one physical unit (`item`). |
| **Carrier** | A physical representation of an identifier: a QR code, Data Matrix, NFC tag or UHF RFID transponder. |
| **Carrier binding** | The versioned record that a specific carrier instance was bound to a passport, with status, times and an actor. |
| **Encoded identifier** | The value actually written on a carrier and read back. Resolves to a passport; is not the passport identifier. |
| **Resolver URI** | The address at which a reader can look a passport up. Deployment infrastructure, not identity. |
| **Observation** | An attributed claim, carrying a method, a value status, a source organisation and an observation time. |
| **Observation set** | Observations sharing source organisation, source system, method and time — one measurement occasion. The composition rule applies within a set, never across sets. |
| **Value status** | Whether a value is `supplied`, `notMeasured`, `unknown`, `notApplicable` or `withheld`. Keeps absence honest. |
| **Method** | How a claim was produced — a declaration, a human inspection, or a named measurement technology. |
| **Provenance** | Who claimed something, on what basis, and when. Distinct from integrity. |
| **Lifecycle event** | An attributed occurrence, recorded separately from product characteristics, with event time and recorded time as different facts. |
| **Event time vs recorded time** | When the thing happened, versus when the system was told. They diverge routinely, and both are kept. |
| **Sorting decision** | An outcome citing the observations and the rule-set version that produced it, so it can be replayed. |
| **View** | A projection of a record selected by the caller's role: `integrityOnly`, `public`, `partner`, `sorting`, `recycler`, `authority`, `full`. |
| **Scope** | Permission to perform an operation. Necessary and never sufficient — the view decides what comes back. |
| **Projection** | A derived, narrower representation of a record. Never mutates the source, and always carries the `recordVersion` it came from. |
| **Withheld** | A field the caller may know exists but not read. Marked explicitly rather than omitted, because omission would falsely imply the data was never collected. |
| **Append-only** | Collections that are added to and never edited: material observations, lifecycle events, sorting decisions, integrity entries. |
| **Canonicalisation** | Producing a deterministic byte representation, here RFC 8785 over an explicit field projection. |
| **Integrity projection** | The explicit subset of fields the digest covers. Excludes access, view and integrity members so the digest does not depend on who is asking. |
| **Digest** | SHA-256 of the canonical bytes, lower-case hexadecimal. |
| **Evidence envelope** | What is submitted for anchoring: identifiers and a digest, never passport content. |
| **Integrity receipt** | A backend's submission-status record. The only supplied backend is a mock. |
| **Anchoring** | Recording a digest with an external party so a third party can later check it. Optional, Tier 3. |
| **Verdict** | The result of verification: `match`, `mismatch`, `unanchored` (no confirmation yet) or `unverifiable` (a retention defect). |
| **Reason code** | A released, catalogued error identity (`S4C-…`) with an HTTP status and a safe action. Clients branch on it rather than on the status alone. |
| **Safe action** | The defined response a reason code requires before any command is issued — `divert`, `divertAndAlert`, `noCommand`, `quarantine`, `retryOnceThenDivert`, `noEffectOnSorting` and others. The profile fixes *which* outcome applies; how a deployment realises it is deployment-specific. |
| **Controlled vocabulary** | A published, versioned set of tokens with definitions. Unknown tokens are rejected, never coerced. |
| **Implementation tier** | The adoption sequence: 1 Core Passport, 2 Operational Passport, 3 Assured Passport. Not a certification scheme. |
| **Profile conformance** | Agreement with this repository's versioned rules. Distinct from legal or regulatory conformity, and not certified by anyone. |
| **Normative (here)** | Normative within the SORT4CIRC DPP implementation profile versioned in this repository — not an EU specification, a CEN/CENELEC standard, or a certification. |
| **Reference implementation** | The Python software in `src/`. One way to implement the profile, not the only one. |
| **Synthetic example** | Invented, demonstrative data. Never a description of any organisation's real activity, data or performance. |

## Related pages

- [Data model](concepts.md) · [Identifiers](identifiers.md) · [Provenance](provenance.md)
- [Regulatory context](regulatory-context.md) — the limits of "normative" and "conformance"
