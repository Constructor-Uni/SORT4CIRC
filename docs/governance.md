# Selection and standards-deviation records

The repository contains templates, not completed decisions, under
`spec/governance/`. Empty names, dates, limits and results are intentional: no
person, approval, threshold, measurement or signature is inferred by the public
reference implementation.

The environmental-selection schema records a frozen acceptance plan separately
from later candidate results. Validation rejects a selected candidate whose
evidence is pending or insufficient, a candidate that exceeds its frozen
maximum, and demonstrator deployment where no project-operated candidate has
sufficient evidence and a passing result. The limit approver must be a different
individual from both the preparer and the result reporter or recommender.

The EN 18223 deviation template remains **open**. The native SORT4CIRC JSON and XML
profiles do not implement EN 18223 Clause 5, Annex A expanded JSON, or Annex B
compressed XML. Full EN 18223 conformity, and presumption of conformity through
EN 18223, are therefore **not claimed** anywhere in this repository.

Closing that deviation is a governance action for the adopting organisation, and
the schema records what it requires: a validated field-level mapping, the Clause 5
and Annex A/B artefacts, a recommendation, an approval by a different named
individual from the preparer and the recommender, and a dated decision. Those
fields are **deployment-dependent** and **require external validation**; the
repository ships the schema and an empty template, never a decision.

If you need EN 18223 conformity today, treat this as an open item and rely on the
documented SORT4CIRC mapping for interoperability in the meantime.
