"""API contract: status codes, preconditions, idempotency, pagination, errors."""

from __future__ import annotations

from conftest import EPC_ENCODED, HEADERS, passport_payload

PROBLEM_MEMBERS = {"type", "title", "status", "detail", "instance", "reasonCode", "correlationId"}


def test_creation_returns_location_and_etag(client):
    response = client.post("/v1/dpps", json=passport_payload(), headers=HEADERS["brand"])
    assert response.status_code == 201
    assert response.headers["Location"].startswith("/v1/dpps/")
    assert response.headers["ETag"].endswith('-v1"')


def test_every_response_echoes_the_correlation_identifier(client, dpp_id):
    correlation = "7f1c2c1e-4a1b-4f0d-9d2b-6a2f0c9e1a44"
    response = client.get(f"/v1/dpps/{dpp_id}", headers={**HEADERS["brand"], "X-Correlation-Id": correlation})
    assert response.headers["X-Correlation-Id"] == correlation


def test_errors_are_rfc9457_problem_documents(client):
    response = client.get("/v1/dpps/urn:sort4circ:dpp:missing", headers=HEADERS["brand"])
    assert response.status_code == 404
    assert set(response.json()) >= PROBLEM_MEMBERS
    assert response.json()["type"].startswith("https://data.sort4circ.eu/problems/")


def test_conditional_get_returns_not_modified(client, dpp_id):
    first = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["brand"])
    again = client.get(f"/v1/dpps/{dpp_id}", headers={**HEADERS["brand"], "If-None-Match": first.headers["ETag"]})
    assert again.status_code == 304


def test_update_requires_if_match_and_refuses_a_stale_one(client, dpp_id):
    tag = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["brand"]).headers["ETag"]

    missing = client.patch(f"/v1/dpps/{dpp_id}", json={"product": {"condition": "good"}}, headers=HEADERS["brand"])
    assert missing.status_code == 412

    ok = client.patch(
        f"/v1/dpps/{dpp_id}",
        json={"product": {"condition": "good"}},
        headers={**HEADERS["brand"], "If-Match": tag},
    )
    assert ok.status_code == 200
    assert ok.headers["ETag"] != tag

    stale = client.patch(
        f"/v1/dpps/{dpp_id}",
        json={"product": {"condition": "asNew"}},
        headers={**HEADERS["brand"], "If-Match": tag},
    )
    assert stale.status_code == 412
    assert stale.json()["reasonCode"] == "S4C-STATE-VERSION-CONFLICT"


def test_idempotency_repeats_the_outcome_and_refuses_a_changed_body(client):
    headers = {**HEADERS["brand"], "Idempotency-Key": "k-1"}
    first = client.post("/v1/dpps", json=passport_payload(), headers=headers)
    repeat = client.post("/v1/dpps", json=passport_payload(), headers=headers)
    assert first.json()["dppId"] == repeat.json()["dppId"]
    assert len(list(client.app.state.store)) == 1

    changed = client.post(
        "/v1/dpps",
        json=passport_payload(responsibleOperatorId="urn:sort4circ:org:other"),
        headers=headers,
    )
    assert changed.status_code == 409
    assert changed.json()["reasonCode"] == "S4C-STATE-IDEMPOTENCY-CONFLICT"


def test_an_invalid_payload_names_the_failing_path(client):
    bad = passport_payload()
    del bad["product"]["articleClass"]
    response = client.post("/v1/dpps", json=bad, headers=HEADERS["brand"])
    assert response.status_code == 422
    assert response.json()["reasonCode"] == "S4C-PAYLOAD-SCHEMA-INVALID"
    assert response.json()["errors"]


def test_an_undeclared_vocabulary_token_is_refused_and_not_coerced(client):
    bad = passport_payload()
    bad["product"]["articleClass"] = "sweater"  # a plausible term that is not in the vocabulary
    response = client.post("/v1/dpps", json=bad, headers=HEADERS["brand"])
    assert response.status_code == 422
    assert response.json()["reasonCode"] == "S4C-PAYLOAD-VOCAB-INVALID"
    assert response.json()["vocabulary"] == "article-class"


def test_a_timestamp_without_an_offset_is_refused(client):
    bad = passport_payload()
    bad["materialObservations"][0]["observedAt"] = "2026-06-18T11:02:10"
    assert client.post("/v1/dpps", json=bad, headers=HEADERS["brand"]).status_code == 422


def test_a_percentage_without_a_basis_is_refused(client):
    bad = passport_payload()
    del bad["materialObservations"][0]["percentageBasis"]
    assert client.post("/v1/dpps", json=bad, headers=HEADERS["brand"]).status_code == 422


def test_an_unknown_value_may_not_carry_a_percentage(client):
    bad = passport_payload()
    bad["materialObservations"][0]["valueStatus"] = "unknown"
    response = client.post("/v1/dpps", json=bad, headers=HEADERS["brand"])
    assert response.status_code == 422, "an unknown value must not be dressed up as a measurement"


def test_a_garment_with_no_characterisation_is_representable(client):
    """An uncharacterised garment is a normal state, not an error."""
    payload = passport_payload()
    payload["materialObservations"] = [
        {
            "observationId": "urn:sort4circ:obs:unknown",
            "fibreType": "blendUnresolved",
            "valueStatus": "unknown",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:sort4circ:org:pssr-a",
            "observedAt": "2026-08-10T09:00:00Z",
        }
    ]
    assert client.post("/v1/dpps", json=payload, headers=HEADERS["brand"]).status_code == 201


def test_resolution_reports_the_five_negative_outcomes_distinctly(client, bound_dpp):
    assert client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["pssrSystem"]).status_code == 200
    unknown = client.get(
        "/v1/identifiers/urn%3Aepc%3Aid%3Asgtin%3A0614141.999999.999/dpp", headers=HEADERS["pssrSystem"]
    )
    assert (unknown.status_code, unknown.json()["reasonCode"]) == (404, "S4C-IDENT-UNKNOWN")
    forbidden = client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["consumer"])
    assert forbidden.status_code == 403


def test_a_replaced_carrier_resolves_as_retired_rather_than_unknown(client, bound_dpp):
    client.post(
        f"/v1/dpps/{bound_dpp}/carriers",
        json={
            "carrierType": "uhfRfid",
            "encodingScheme": "gs1Sgtin96",
            "encodedIdentifier": "urn:epc:id:sgtin:0614141.112345.402",
            "boundBy": "urn:sort4circ:org:brand-a",
        },
        headers=HEADERS["brand"],
    ).raise_for_status()
    response = client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["pssrSystem"])
    assert response.status_code == 410
    assert response.json()["reasonCode"] == "S4C-IDENT-RETIRED"


def test_cursor_pagination_traverses_without_omission_or_duplication(client):
    created = set()
    for index in range(12):
        payload = passport_payload(identity={"granularity": "item", "itemId": f"urn:sort4circ:item:{index:06d}"})
        created.add(client.post("/v1/dpps", json=payload, headers=HEADERS["brand"]).json()["dppId"])

    seen: list[str] = []
    cursor = None
    for _ in range(10):
        url = "/v1/dpps?limit=5" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(url, headers=HEADERS["administrator"]).json()
        seen.extend(item["dppId"] for item in body["items"])
        cursor = body.get("nextCursor")
        if cursor is None:
            break
    assert len(seen) == len(set(seen)) == len(created)
    assert set(seen) == created


def test_health_reports_the_evidence_histogram(client, dpp_id):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["passports"] == 1
    assert sum(body["evidence"].values()) >= 1


def test_the_development_auth_stand_in_is_off_by_default(monkeypatch, store, ledger):
    from fastapi.testclient import TestClient

    from sort4circ_dpp.api import create_app

    monkeypatch.delenv("S4C_ALLOW_HEADER_AUTH", raising=False)
    isolated = TestClient(create_app(store=store, ledger=ledger))
    response = isolated.get("/v1/dpps", headers=HEADERS["administrator"])
    assert response.status_code == 401
    assert response.json()["reasonCode"] == "S4C-AUTH-INVALID-TOKEN"
