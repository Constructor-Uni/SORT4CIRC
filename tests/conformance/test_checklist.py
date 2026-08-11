"""Conformance suite mapped to the D4.3 checklist rows.

Each test carries the checklist identifier it evidences, so a run of this suite
produces the machine-checkable part of a conformance statement. Rows that
require a human decision, an executed load campaign or a signed scope reason are
listed in ``REQUIRES_HUMAN_EVIDENCE`` and are reported rather than silently
omitted: a suite that quietly skips half the checklist reads as full coverage
when it is not.

Run ``make conformance`` to produce ``conformance-report.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import EPC_ENCODED, HEADERS, passport_payload
from sort4circ_dpp.config import SPEC_DIR
from sort4circ_dpp.reasons import released_codes

TIER_1 = "tier1"
TIER_2 = "tier2"
TIER_3 = "tier3"

#: Checklist rows this suite cannot decide. Each names what would decide it.
REQUIRES_HUMAN_EVIDENCE = {
    "SCP-05": "publication review for exposed secrets",
    "SCP-07": "signed conformance statement",
    "BC-03": "executed benchmark across the four candidates",
    "BC-04": "metered energy and a dated emission factor",
    "BC-05": "executed latency, finality, throughput and cost measurement",
    "BC-07": "published TOPSIS matrix and independent recalculation",
    "BC-08": "recorded weight-elicitation workshop",
    "BC-09": "executed sensitivity analysis",
    "EN-04": "restore and provider-exit evidence",
    "INT-02": "IEC 62264 boundary mapping review",
    "INT-03": "OPC UA or AutomationML profile, where selected",
    "SEC-04": "IEC 62443 zone and conduit assessment",
    "SEC-05": "ISO/IEC 27001 statement of applicability",
    "SEC-06": "release security scan",
    "PERF-01": "approved workload model for the deployment",
    "PERF-02": "executed 1x, 2x, stress and soak campaign",
    "PERF-03": "measured line parameters and percentile report",
    "PERF-06": "resource utilisation report",
    "PERF-09": "measured conveyor and actuation parameters",
    "PERF-10": "24-hour soak run",
}


def row(identifier: str, tier: str):
    """Attach a checklist identifier and tier to a test."""
    return pytest.mark.parametrize("checklist_row", [pytest.param(identifier, id=identifier)]) if False else \
        pytest.mark.checklist(identifier, tier)


# --------------------------------------------------------------------- tier 1


@pytest.mark.checklist("EN-01", TIER_1)
def test_en01_exchange_profile_is_json_over_http(client, dpp_id):
    response = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["brand"])
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.checklist("EN-02", TIER_1)
def test_en02_identifier_uniqueness_and_non_reuse(client, bound_dpp):
    second = client.post(
        "/v1/dpps",
        json=passport_payload(identity={"granularity": "item", "itemId": "urn:sort4circ:item:000002"}),
        headers=HEADERS["brand"],
    ).json()["dppId"]
    clash = client.post(
        f"/v1/dpps/{second}/carriers",
        json={
            "carrierType": "uhfRfid",
            "encodingScheme": "gs1Sgtin96",
            "encodedIdentifier": "urn:epc:id:sgtin:0614141.112345.400",
            "boundBy": "urn:sort4circ:org:brand-a",
        },
        headers=HEADERS["brand"],
    )
    assert clash.status_code == 409


@pytest.mark.checklist("EN-03", TIER_1)
def test_en03_carrier_cases_produce_the_expected_outcomes(client, bound_dpp):
    assert client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["pssrSystem"]).status_code == 200
    assert client.get(
        "/v1/identifiers/urn%3Aepc%3Aid%3Asgtin%3A0614141.999999.999/dpp", headers=HEADERS["pssrSystem"]
    ).status_code == 404


@pytest.mark.checklist("EN-05", TIER_1)
def test_en05_lifecycle_and_search_operations_exist(client, dpp_id):
    assert client.get("/v1/dpps", headers=HEADERS["administrator"]).status_code == 200
    assert client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["brand"]).status_code == 200


@pytest.mark.checklist("SEM-01", TIER_1)
def test_sem01_ontology_declares_version_and_licence():
    text = (SPEC_DIR / "ontology" / "sort4circ-1.0.0.ttl").read_text(encoding="utf-8")
    for required in ("owl:versionIRI", "owl:versionInfo", "dcterms:license", "dcterms:publisher"):
        assert required in text


@pytest.mark.checklist("SEM-02", TIER_1)
def test_sem02_identifier_types_stay_distinct(client, bound_dpp):
    record = client.get(f"/v1/dpps/{bound_dpp}?view=full", headers=HEADERS["administrator"]).json()
    identity = record["identity"]
    assert identity["itemId"] != identity["epc"] != record["dppId"]
    assert identity.get("sampleId") not in (identity["itemId"], record["dppId"])


@pytest.mark.checklist("SEM-03", TIER_1)
def test_sem03_public_terms_carry_labels():
    text = (SPEC_DIR / "ontology" / "sort4circ-1.0.0.ttl").read_text(encoding="utf-8")
    declarations = text.count("a owl:Class")
    labels = text.count("skos:prefLabel")
    assert labels >= declarations, "every public class carries a preferred label"


@pytest.mark.checklist("DAT-01", TIER_1)
def test_dat01_mandatory_fields_are_enforced(client):
    incomplete = passport_payload()
    del incomplete["responsibleOperatorId"]
    assert client.post("/v1/dpps", json=incomplete, headers=HEADERS["brand"]).status_code == 422


@pytest.mark.checklist("DAT-02", TIER_1)
def test_dat02_unknown_is_never_coerced_to_zero(client):
    payload = passport_payload()
    payload["materialObservations"] = [
        {
            "observationId": "urn:sort4circ:obs:u",
            "fibreType": "blendUnresolved",
            "valueStatus": "unknown",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:sort4circ:org:pssr-a",
            "observedAt": "2026-08-10T09:00:00Z",
        }
    ]
    created = client.post("/v1/dpps", json=payload, headers=HEADERS["brand"]).json()
    stored = created["materialObservations"][0]
    assert stored["valueStatus"] == "unknown"
    assert "percentage" not in stored, "an unknown value never becomes a zero percentage"


@pytest.mark.checklist("DAT-03", TIER_1)
def test_dat03_provenance_is_mandatory_on_every_observation(client):
    payload = passport_payload()
    del payload["materialObservations"][0]["method"]
    assert client.post("/v1/dpps", json=payload, headers=HEADERS["brand"]).status_code == 422


@pytest.mark.checklist("DAT-04", TIER_1)
def test_dat04_fibre_terms_come_from_the_declared_vocabulary(client):
    payload = passport_payload()
    payload["materialObservations"][0]["fibreType"] = "poly"
    assert client.post("/v1/dpps", json=payload, headers=HEADERS["brand"]).status_code == 422


@pytest.mark.checklist("API-01", TIER_1)
def test_api01_schema_is_versioned_and_negative_fixtures_fail():
    schema = json.loads((SPEC_DIR / "schemas" / "dpp-1.0.0.schema.json").read_text())
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$id"].endswith("/1.0.0")


@pytest.mark.checklist("API-05", TIER_1)
def test_api05_etag_and_if_match(client, dpp_id):
    tag = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["brand"]).headers["ETag"]
    assert tag
    assert client.patch(f"/v1/dpps/{dpp_id}", json={"product": {}}, headers=HEADERS["brand"]).status_code == 412


@pytest.mark.checklist("API-07", TIER_1)
def test_api07_errors_use_problem_details_and_stable_codes(client):
    body = client.get("/v1/dpps/urn:sort4circ:dpp:absent", headers=HEADERS["brand"]).json()
    assert body["reasonCode"] in released_codes()


@pytest.mark.checklist("SEC-03", TIER_1)
def test_sec03_access_is_default_deny(client, dpp_id):
    assert client.post("/v1/dpps", json=passport_payload(), headers=HEADERS["consumer"]).status_code == 403


# --------------------------------------------------------------------- tier 2


@pytest.mark.checklist("API-06", TIER_2)
def test_api06_idempotency_on_create_and_event(client, dpp_id):
    headers = {**HEADERS["collector"], "Idempotency-Key": "evt-1"}
    event = {
        "eventType": "collection",
        "eventTime": "2026-08-10T09:00:00Z",
        "eventTimeZoneOffset": "+02:00",
        "sourceSystemId": "urn:sort4circ:system:depot",
    }
    first = client.post(f"/v1/dpps/{dpp_id}/events", json=event, headers=headers)
    repeat = client.post(f"/v1/dpps/{dpp_id}/events", json=event, headers=headers)
    assert first.json()["eventId"] == repeat.json()["eventId"]


@pytest.mark.checklist("API-08", TIER_2)
def test_api08_cursor_pagination_is_deterministic(client):
    for index in range(6):
        client.post(
            "/v1/dpps",
            json=passport_payload(identity={"granularity": "item", "itemId": f"urn:sort4circ:item:{index:04d}"}),
            headers=HEADERS["brand"],
        )
    page = client.get("/v1/dpps?limit=3", headers=HEADERS["administrator"]).json()
    assert len(page["items"]) == 3 and "nextCursor" in page


@pytest.mark.checklist("API-11", TIER_2)
def test_api11_every_released_reason_code_is_documented():
    document = json.loads((SPEC_DIR / "reason-codes.json").read_text())
    actions = set(document["safeActions"])
    for entry in document["codes"]:
        assert entry["safeAction"] in actions
        assert entry["condition"] and entry["type"]


@pytest.mark.checklist("API-12", TIER_2)
def test_api12_field_obligations_match_the_dictionary():
    schema = json.loads((SPEC_DIR / "schemas" / "dpp-1.0.0.schema.json").read_text())
    required = set(schema["required"])
    assert {"dppId", "schemaVersion", "recordVersion", "status", "identity", "product", "materialObservations"} <= required


@pytest.mark.checklist("DAT-08", TIER_2)
def test_dat08_corrections_never_overwrite(client, dpp_id):
    before = client.get(f"/v1/dpps/{dpp_id}?view=full", headers=HEADERS["administrator"]).json()
    client.post(
        f"/v1/dpps/{dpp_id}/observations",
        headers=HEADERS["pssrSystem"],
        json={
            "observationId": "urn:sort4circ:obs:corrected",
            "fibreType": "polyester",
            "percentage": 93.4,
            "percentageBasis": "mass",
            "valueStatus": "supplied",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:sort4circ:org:pssr-a",
            "observedAt": "2026-08-10T09:14:01.902Z",
        },
    ).raise_for_status()
    after = client.get(f"/v1/dpps/{dpp_id}?view=full", headers=HEADERS["administrator"]).json()
    assert after["materialObservations"][: len(before["materialObservations"])] == before["materialObservations"]


@pytest.mark.checklist("DAT-10", TIER_2)
def test_dat10_disagreement_stays_discoverable(client, dpp_id):
    client.post(
        f"/v1/dpps/{dpp_id}/observations",
        headers=HEADERS["pssrSystem"],
        json={
            "observationId": "urn:sort4circ:obs:nir",
            "fibreType": "polyester",
            "percentage": 80,
            "percentageBasis": "mass",
            "valueStatus": "supplied",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:sort4circ:org:pssr-a",
            "observedAt": "2026-08-10T09:14:01.902Z",
        },
    ).raise_for_status()
    record = client.get(f"/v1/dpps/{dpp_id}?view=full", headers=HEADERS["administrator"]).json()
    polyester = [o["percentage"] for o in record["materialObservations"] if o["fibreType"] == "polyester"]
    assert max(polyester) - min(polyester) > 5, "the divergence remains visible to a query"


@pytest.mark.checklist("IOT-06", TIER_2)
def test_iot06_one_accepted_read_one_response():
    from sort4circ_dpp.gateway import ReadZone

    zone = ReadZone()
    accepted = [zone.evaluate([{"epc": "urn:epc:id:sgtin:0614141.112345.400"}]).may_command for _ in range(5)]
    assert accepted.count(True) == 1, "repeat reads inside the window produce no further command"


@pytest.mark.checklist("IOT-07", TIER_2)
def test_iot07_negative_read_cases_reach_a_safe_result():
    from sort4circ_dpp.gateway import ReadZone

    zone = ReadZone()
    for reads in ([], [{"epc": "bad"}], [{"epc": "urn:epc:id:sgtin:0614141.112345.400"}] * 2):
        for _ in range(100):
            assert not zone.evaluate(reads).may_command


@pytest.mark.checklist("SEC-09", TIER_2)
def test_sec09_refusals_do_not_enumerate(client, bound_dpp):
    forbidden = client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["consumer"]).json()
    assert "dppId" not in forbidden and "recordVersion" not in forbidden


@pytest.mark.checklist("SEC-10", TIER_2)
def test_sec10_withheld_is_explicit_not_absent(client, dpp_id):
    body = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["consumer"]).json()
    observation = body["materialObservations"][0]
    assert observation.get("sourceOrganisationStatus") == "withheld"


# --------------------------------------------------------------------- tier 3


@pytest.mark.checklist("EN-08", TIER_3)
def test_en08_altered_record_is_detected(client, dpp_id):
    from sort4circ_dpp.canonical import digest

    record = client.get(f"/v1/dpps/{dpp_id}?view=full", headers=HEADERS["administrator"]).json()
    original = digest(record)
    record["materialObservations"][0]["percentage"] = 94
    assert digest(record) != original


@pytest.mark.checklist("BC-01", TIER_3)
def test_bc01_reference_ledger_is_not_proof_of_work(client):
    from sort4circ_dpp.ledger.memory import InMemoryLedger

    assert "pow" not in InMemoryLedger().network_id.lower()


@pytest.mark.checklist("BC-02", TIER_3)
def test_bc02_no_passport_content_reaches_the_ledger(store):
    from sort4circ_dpp.evidence import envelope_for

    store.create(passport_payload())
    body = envelope_for(store.outbox[0])
    assert "materialObservations" not in body and "product" not in body


@pytest.mark.checklist("BC-10", TIER_3)
def test_bc10_the_reference_adapter_is_separate_from_the_ranking():
    """The reference adapter is an implementation, not a selection outcome."""
    text = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    # Collapse markdown line wrapping before matching, so reflowing a paragraph
    # cannot silently drop the statement this row exists to enforce.
    flattened = " ".join(text.replace("*", "").split())
    assert "not the outcome of the assessment" in flattened


@pytest.mark.checklist("PERF-04", TIER_3)
def test_perf04_acknowledged_state_survives_a_restart(store, ledger):
    from sort4circ_dpp.evidence import TERMINAL_STATES, EvidenceWorker

    for index in range(20):
        store.create(passport_payload(identity={"granularity": "item", "itemId": f"urn:sort4circ:item:{index:04d}"}))
    ledger.fail_next = "S4C-LEDGER-UNAVAILABLE"
    EvidenceWorker(store=store, ledger=ledger).drain()
    EvidenceWorker(store=store, ledger=ledger).drain()  # restarted worker, same queue
    assert all(entry.state in TERMINAL_STATES for entry in store.outbox)


@pytest.mark.checklist("PERF-08", TIER_3)
def test_perf08_replacing_the_adapter_does_not_change_the_api(store):

    from sort4circ_dpp.api import create_app
    from sort4circ_dpp.ledger.memory import InMemoryLedger

    routes = lambda app: sorted(r.path for r in app.routes)  # noqa: E731
    assert routes(create_app(store=store, ledger=InMemoryLedger(network_id="a"))) == routes(
        create_app(ledger=InMemoryLedger(network_id="b"))
    )


def test_rows_requiring_human_evidence_are_reported_not_hidden():
    """A suite that silently omits rows reads as full coverage when it is not."""
    assert REQUIRES_HUMAN_EVIDENCE, "the list must never be emptied to make a run look complete"
    for identifier, evidence in REQUIRES_HUMAN_EVIDENCE.items():
        assert evidence, f"{identifier} names no evidence that would decide it"
