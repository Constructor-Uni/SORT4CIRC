# Glossary

**Carrier binding.** The time-bounded association between a physical data
carrier and a passport. At most one binding per passport is commissioned at a
time; earlier ones are retained with a closing timestamp.

**Conformance tier.** One of three cumulative, testable states an
implementation can reach. Tier 1 core, tier 2 operational, tier 3 assured.

**DPP.** Digital Product Passport. The digital record describing one product at
one declared granularity.

**EPC.** Electronic Product Code. The identifier encoded on a UHF RFID carrier.
Distinct from the item identifier, which survives carrier replacement.

**Evidence envelope.** The object submitted to a ledger: a reference and a
digest, never passport content.

**Granularity.** Whether a passport describes a model, a batch or an item. Fixed
at creation; changing it requires a new passport.

**Holonic structure.** The containment chain garment, fabric, yarn, filament,
fibre, with material types classifying the fibre level and environmental values
attaching at the level to which the measurement applies.

**Integrity projection.** The explicit subset of a record the digest covers.
Held in the profile configuration and versioned with it, so a digest stays
reproducible when unrelated fields are added.

**Observation set.** The observations produced by one measurement occasion,
identified by source organisation, source system, method and observation time.
The composition rule applies within a set and never across sets.

**PSFS.** Pre-Sorting and facilitating Fine Sorting.

**PSSR.** Pre-Sorting and Sorting for Recycling.

**Reason code.** A stable string identifying a condition. Never reworded or
renumbered once released, because clients dispatch on it.

**Safe action.** The normative edge-gateway response to a reason code. Where it
reads divert, the garment goes to manual review and no category-specific
actuator is engaged.

**Software budget.** The interval available to the gateway, the passport service
and decision publication for one garment, derived from conveyor speed, actuator
distance and the fixed overheads.

**Transactional outbox.** The mechanism by which a passport write and its
evidence-queue entry commit as one logical operation.

**TVC.** Textile Value Chain.

**Value status.** Whether a value is supplied, not measured, unknown, not
applicable or withheld. An unknown value is never written as zero.

**View.** The projection of a record a given role receives. Requesting a wider
view than permitted returns the permitted one, not an error.
