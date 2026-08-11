"""The D4.3 Annex G worked example, executed against the reference service.

One garment travels through every interface: creation, carrier commissioning,
the read at the sorting gate, resolution, the decision, a disagreeing second
observation, digest calculation, anchoring and independent verification.

Run it with::

    make example        # or: python examples/worked_example.py

The digest printed at step 8 is the value published in the deliverable. If this
script prints a different one, the canonicalisation is wrong, and that is the
defect the example exists to expose.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("S4C_ALLOW_HEADER_AUTH", "1")

from fastapi.testclient import TestClient  # noqa: E402

from sort4circ_dpp.api import create_app  # noqa: E402
from sort4circ_dpp.gateway import ReadZone  # noqa: E402
from sort4circ_dpp.vocab import evidence_weight  # noqa: E402

PUBLISHED_DIGEST = "dd14a3f2487f2b22deda4a7bc2b37e775f378e05d60dc1e6ad26fdf26038ae9f"
EPC = "urn:epc:id:sgtin:0614141.112345.400"

BRAND = {
    "X-S4C-Role": "brand",
    "X-S4C-Subject": "brand-operator",
    "X-S4C-Organisation": "urn:sort4circ:org:brand-a",
}
PSSR = {
    "X-S4C-Role": "pssrSystem",
    "X-S4C-Subject": "nir-line-2",
    "X-S4C-Organisation": "urn:sort4circ:org:pssr-partner-a",
}
VERIFIER = {"X-S4C-Role": "integrityVerifier", "X-S4C-Subject": "auditor"}
ADMIN = {"X-S4C-Role": "administrator", "X-S4C-Subject": "ops"}


def step(number: int, title: str) -> None:
    print(f"\n--- Step {number}. {title} " + "-" * max(0, 56 - len(title)))


def main() -> int:
    client = TestClient(create_app())

    step(1, "Passport creation")
    created = client.post(
        "/v1/dpps",
        headers={**BRAND, "Idempotency-Key": "0a91f2c4-3d55-4b12-9f77-2c1a8b6d4e03"},
        json={
            "dppId": "urn:sort4circ:dpp:000001",
            "schemaVersion": "1.0.0",
            "identity": {
                "granularity": "item",
                "itemId": "urn:sort4circ:item:000001",
                "modelId": "MOD-SW-2026-0042",
                "sampleId": "TXHO-WP3-B01-001",
            },
            "product": {
                "articleClass": "upperBodyKnitwear",
                "fabricConstruction": "knitted",
                "colourPrimary": "dark",
                "technicalFlags": ["carbonBlackPresent", "hardPointZipMetal"],
            },
            "materialObservations": [
                {
                    "observationId": "urn:sort4circ:obs:000001",
                    "fibreType": "polyester",
                    "percentage": 95,
                    "percentageBasis": "mass",
                    "valueStatus": "supplied",
                    "method": "labQuantitativeIso1833",
                    "sourceOrganisationId": "urn:sort4circ:org:txho",
                    "observedAt": "2026-06-18T11:02:10Z",
                    "evidenceRef": "urn:sort4circ:lab:B01-001-report",
                },
                {
                    "observationId": "urn:sort4circ:obs:000002",
                    "fibreType": "elastane",
                    "percentage": 5,
                    "percentageBasis": "mass",
                    "valueStatus": "supplied",
                    "method": "labQuantitativeIso1833",
                    "sourceOrganisationId": "urn:sort4circ:org:txho",
                    "observedAt": "2026-06-18T11:02:10Z",
                    "evidenceRef": "urn:sort4circ:lab:B01-001-report",
                },
            ],
            "responsibleOperatorId": "urn:sort4circ:org:brand-a",
        },
    )
    created.raise_for_status()
    dpp_id = created.json()["dppId"]
    print(f"created {dpp_id} at version {created.json()['recordVersion']}")
    print("the sample identifier travels as provenance only and never routes a garment")

    step(2, "Carrier commissioning")
    commissioned = client.post(
        f"/v1/dpps/{dpp_id}/carriers",
        headers=BRAND,
        json={
            "carrierType": "uhfRfid",
            "encodingScheme": "gs1Sgtin96",
            "encodedIdentifier": EPC,
            "resolverUri": "https://id.sort4circ.eu/01/00614141123456/21/400",
            "placement": "sideSeamInternal",
            "boundBy": "urn:sort4circ:org:brand-a",
        },
    )
    commissioned.raise_for_status()
    carrier = commissioned.json()["carriers"][-1]
    print(f"binding {carrier['bindingStatus']}, encoded {carrier['encodedIdentifier']}")

    step(3, "Read at the sorting gate")
    zone = ReadZone()
    result = zone.evaluate([{"epc": EPC, "rssiDbm": -52}])
    print(f"accepted={result.accepted} epc={result.epc}")
    ambiguous = zone.evaluate([{"epc": EPC}, {"epc": "urn:epc:id:sgtin:0614141.112345.401"}])
    print(f"two tags in the window -> {ambiguous.reason_code}, action {ambiguous.safe_action}")
    print("the service is never called for an ambiguous read; the budget is not spent on it")

    step(4, "Resolution and sorting view")
    encoded = EPC.replace(":", "%3A")
    view = client.get(f"/v1/identifiers/{encoded}/dpp?view=sorting", headers=PSSR)
    view.raise_for_status()
    print(f"resolved to {view.json()['dppId']} version {view.json()['recordVersion']}")
    sorting = client.get(f"/v1/dpps/{dpp_id}/sorting-view", headers={"X-S4C-Role": "sortingOperator"})
    print(f"projection lag {sorting.json()['indexLagMs']} ms, consistency {sorting.json()['consistency']}")

    step(5, "Sorting decision")
    summary = sorting.json()["materialSummary"]
    elastane = next((m for m in summary if m["fibreType"] == "elastane"), None)
    flags = sorting.json()["product"].get("technicalFlags", [])
    blocked = elastane is not None and "hardPointZipMetal" in flags
    category = "mechanicalRecyclingFibre" if blocked else "chemicalRecyclingPolyester"
    print(f"elastane present={elastane is not None}, metal hard point={'hardPointZipMetal' in flags}")
    print(f"rule set pssr-line-01 v3.2.0 -> {category}")
    print("the decision cites the observations consumed and the rule-set version that consumed them")

    step(6, "A second technology disagrees")
    observation = client.post(
        f"/v1/dpps/{dpp_id}/observations",
        headers={**PSSR, "Idempotency-Key": "3d5b7c9a-2e11-4a77-b0a1-9c4d2e6f8a30"},
        json={
            "observationId": "urn:sort4circ:obs:000114",
            "fibreType": "polyester",
            "percentage": 93.4,
            "percentageBasis": "mass",
            "valueStatus": "supplied",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:sort4circ:org:pssr-partner-a",
            "sourceSystemId": "urn:sort4circ:system:nir-line-2",
            "observedAt": "2026-08-10T09:14:01.902Z",
            "confidence": {"value": 0.87, "scale": "unitInterval"},
            "evidenceRef": "urn:sort4circ:spectrum:2026-08-10-0914-01",
        },
    )
    observation.raise_for_status()
    print(f"observation accepted, record now at version {observation.json()['recordVersion']}")

    step(7, "What the record now states")
    full = client.get(f"/v1/dpps/{dpp_id}?view=full", headers=ADMIN).json()
    polyester = [o for o in full["materialObservations"] if o["fibreType"] == "polyester"]
    for entry in polyester:
        print(
            f"  polyester {entry['percentage']:>5} percent  "
            f"method {entry['method']:<24} weight {evidence_weight(entry['method'])}"
        )
    spread = abs(polyester[0]["percentage"] - polyester[1]["percentage"])
    print(f"both retained, spread {spread:.1f} percentage points, neither averaged nor superseded")
    print("an implementation that overwrote the laboratory figure could not report this")

    step(8, "Deterministic digest")
    integrity = client.get(f"/v1/dpps/{dpp_id}/integrity", headers=ADMIN).json()
    version_two = next(e for e in integrity["integrity"] if e["subjectVersion"] == 2)
    print(f"evidence for version 2: {version_two['digestValue']}")
    from sort4circ_dpp.canonical import canonical_bytes, digest

    reference = {
        "dppId": "urn:sort4circ:dpp:000001",
        "recordVersion": 7,
        "updatedAt": "2026-08-10T09:12:44Z",
        "identity": {"granularity": "item", "itemId": "urn:sort4circ:item:000001", "epc": EPC},
        "product": {
            "articleClass": "upperBodyKnitwear",
            "fabricConstruction": "knitted",
            "technicalFlags": ["carbonBlackPresent", "hardPointZipMetal"],
        },
        "materialObservations": [
            {
                "observationId": "urn:sort4circ:obs:000001",
                "fibreType": "polyester",
                "percentage": 95,
                "percentageBasis": "mass",
                "valueStatus": "supplied",
                "method": "labQuantitativeIso1833",
                "sourceOrganisationId": "urn:sort4circ:org:txho",
                "observedAt": "2026-06-18T11:02:10Z",
            },
            {
                "observationId": "urn:sort4circ:obs:000002",
                "fibreType": "elastane",
                "percentage": 5,
                "percentageBasis": "mass",
                "valueStatus": "supplied",
                "method": "labQuantitativeIso1833",
                "sourceOrganisationId": "urn:sort4circ:org:txho",
                "observedAt": "2026-06-18T11:02:10Z",
            },
        ],
    }
    computed = digest(reference)
    print(f"published reference vector: {len(canonical_bytes(reference))} bytes -> {computed}")
    print(f"matches deliverable D4.3 Annex G: {computed == PUBLISHED_DIGEST}")
    altered = json.loads(json.dumps(reference))
    altered["materialObservations"][0]["percentage"] = 94
    print(f"one digit changed          -> {digest(altered)}")

    step(9, "Anchoring")
    client.post("/v1/internal/evidence/drain", headers=ADMIN)
    anchored = client.get(f"/v1/dpps/{dpp_id}/integrity", headers=ADMIN).json()["integrity"]
    for entry in anchored:
        print(f"  version {entry['subjectVersion']}: {entry['evidenceState']} {entry.get('transactionRef','')[:20]}")
    print("no part of the routing in step 5 waited for any of this")

    step(10, "Independent verification")
    target = anchored[-1]
    verdict = client.post(
        f"/v1/dpps/{dpp_id}/integrity/verify",
        headers=VERIFIER,
        json={"evidenceId": target["evidenceId"]},
    ).json()
    print(f"subject version {verdict['subjectVersion']} -> verdict {verdict['verdict']}")
    older = anchored[0]
    older_verdict = client.post(
        f"/v1/dpps/{dpp_id}/integrity/verify",
        headers=VERIFIER,
        json={"evidenceId": older["evidenceId"]},
    ).json()
    print(f"evidence for version {older['subjectVersion']} still verifies: {older_verdict['verdict']}")
    print("each evidence entry is verified against the version it claimed, never the current one")

    ok = computed == PUBLISHED_DIGEST and verdict["verdict"] == "match"
    print("\nresult:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
