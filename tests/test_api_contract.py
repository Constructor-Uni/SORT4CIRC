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


def test_an_unsupplied_correlation_identifier_is_generated_once_and_reused(client, monkeypatch):
    generated = []

    def fake_uuid4():
        value = f"generated-{len(generated) + 1}"
        generated.append(value)
        return value

    monkeypatch.setattr("sort4circ_dpp.api.uuid.uuid4", fake_uuid4)
    response = client.get("/v1/dpps/urn:sort4circ:dpp:missing", headers=HEADERS["brand"])

    assert generated == ["generated-1"]
    assert response.headers["X-Correlation-Id"] == "generated-1"
    assert response.json()["correlationId"] == "generated-1"


def test_errors_are_rfc9457_problem_documents(client):
    response = client.get("/v1/dpps/urn:example:dpp:missing", headers=HEADERS["brand"])
    assert response.status_code == 404
    assert set(response.json()) >= PROBLEM_MEMBERS
    assert response.json()["type"].startswith("https://data.sort4circ.eu/problems/")


def test_malformed_json_body_uses_the_payload_problem_contract(client):
    response = client.post(
        "/v1/dpps",
        content="{",
        headers={**HEADERS["brand"], "Content-Type": "application/json"},
    )
    body = response.json()

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert body["reasonCode"] == "S4C-PAYLOAD-SCHEMA-INVALID"
    assert body["status"] == 422
    assert body["errors"] == [{"path": "body"}]
    assert body["correlationId"] == response.headers["X-Correlation-Id"]


def test_missing_body_uses_the_payload_problem_contract(client):
    response = client.post("/v1/dpps", headers=HEADERS["brand"])
    body = response.json()

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert body["reasonCode"] == "S4C-PAYLOAD-SCHEMA-INVALID"
    assert body["status"] == 422
    assert body["errors"] == [{"path": "body"}]
    assert body["correlationId"] == response.headers["X-Correlation-Id"]


def test_invalid_query_parameter_keeps_fastapi_validation_behavior(client):
    response = client.get("/v1/dpps?limit=not-an-int")
    body = response.json()

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    assert "reasonCode" not in body
    assert "correlationId" not in body
    assert body["detail"][0]["loc"] == ["query", "limit"]


def test_empty_object_remains_application_schema_validation(client):
    response = client.post("/v1/dpps", json={}, headers=HEADERS["brand"])
    body = response.json()

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert body["reasonCode"] == "S4C-PAYLOAD-SCHEMA-INVALID"
    assert body["errors"]
    assert body["correlationId"] == response.headers["X-Correlation-Id"]


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
        json=passport_payload(responsibleOperatorId="urn:example:org:sorter-a"),
        headers=headers,
    )
    assert changed.status_code == 409
    assert changed.json()["reasonCode"] == "S4C-STATE-IDEMPOTENCY-CONFLICT"


def test_idempotency_same_key_is_independent_per_dpp_for_events(client, dpp_id):
    second_dpp = client.post(
        "/v1/dpps", json=passport_payload(identity={"granularity": "item", "itemId": "urn:sort4circ:item:000002"}), headers=HEADERS["brand"]
    ).json()["dppId"]
    event = {
        "eventType": "collection",
        "eventTime": "2026-08-10T09:00:00Z",
        "eventTimeZoneOffset": "+02:00",
        "sourceSystemId": "urn:sort4circ:system:depot",
    }
    headers = {**HEADERS["collector"], "Idempotency-Key": "same-event-key"}

    first = client.post(f"/v1/dpps/{dpp_id}/events", json=event, headers=headers)
    second = client.post(f"/v1/dpps/{second_dpp}/events", json=event, headers=headers)

    assert first.status_code == second.status_code == 201
    assert first.json()["dppId"] == dpp_id
    assert second.json()["dppId"] == second_dpp


def test_idempotency_same_key_does_not_cross_replay_between_operations(client, dpp_id):
    headers = {**HEADERS["brand"], "Idempotency-Key": "operation-key"}
    event = {
        "eventType": "collection",
        "eventTime": "2026-08-10T09:00:00Z",
        "eventTimeZoneOffset": "+02:00",
        "sourceSystemId": "urn:sort4circ:system:depot",
    }
    observation = {
        "observationId": "urn:sort4circ:obs:cross-operation",
        "fibreType": "polyester",
        "percentage": 100,
        "percentageBasis": "mass",
        "valueStatus": "supplied",
        "method": "nirSpectroscopy",
        "sourceOrganisationId": "urn:sort4circ:org:brand-a",
        "observedAt": "2026-08-10T09:14:01.902Z",
        "confidence": {"value": 0.87, "scale": "unitInterval"},
    }

    event_response = client.post(f"/v1/dpps/{dpp_id}/events", json=event, headers=headers)
    observation_response = client.post(
        f"/v1/dpps/{dpp_id}/observations", json=observation, headers=headers
    )

    assert event_response.status_code == observation_response.status_code == 201
    assert "eventId" in event_response.json()
    assert "observationId" in observation_response.json()


def test_idempotency_same_key_does_not_cross_replay_create_and_resource_operation(client, dpp_id):
    key = "create-and-event-key"
    created = client.post(
        "/v1/dpps",
        json=passport_payload(identity={"granularity": "item", "itemId": "urn:sort4circ:item:000003"}),
        headers={**HEADERS["brand"], "Idempotency-Key": key},
    )
    event = {
        "eventType": "collection",
        "eventTime": "2026-08-10T09:00:00Z",
        "eventTimeZoneOffset": "+02:00",
        "sourceSystemId": "urn:sort4circ:system:depot",
    }
    event_response = client.post(
        f"/v1/dpps/{dpp_id}/events",
        json=event,
        headers={**HEADERS["collector"], "Idempotency-Key": key},
    )

    assert created.status_code == 201
    assert event_response.status_code == 201
    assert event_response.json()["dppId"] == dpp_id


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
    bad["materialObservations"][0]["observedAt"] = "2044-05-17T13:15:00"
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
            "observationId": "urn:example:obs:unknown",
            "fibreType": "blendUnresolved",
            "valueStatus": "unknown",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:example:org:sorter-a",
            "observedAt": "2041-03-05T14:20:00Z",
        }
    ]
    assert client.post("/v1/dpps", json=payload, headers=HEADERS["brand"]).status_code == 201


def test_resolution_reports_the_five_negative_outcomes_distinctly(client, bound_dpp):
    assert client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["pssrSystem"]).status_code == 200
    unknown = client.get(
        "/v1/identifiers/urn%3Aexample%3Acarrier%3Aunknown/dpp", headers=HEADERS["pssrSystem"]
    )
    assert (unknown.status_code, unknown.json()["reasonCode"]) == (404, "S4C-IDENT-UNKNOWN")
    forbidden = client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["consumer"])
    assert forbidden.status_code == 403


def test_a_replaced_carrier_resolves_as_retired_rather_than_unknown(client, bound_dpp):
    client.post(
        f"/v1/dpps/{bound_dpp}/carriers",
        json={
            "carrierType": "qrCode",
            "encodingScheme": "proprietary",
            "encodedIdentifier": "urn:example:carrier:000002",
            "boundBy": "urn:example:org:manufacturer-a",
        },
        headers=HEADERS["brand"],
    ).raise_for_status()
    response = client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["pssrSystem"])
    assert response.status_code == 410
    assert response.json()["reasonCode"] == "S4C-IDENT-RETIRED"


def test_cursor_pagination_traverses_without_omission_or_duplication(client):
    created = set()
    for index in range(12):
        payload = passport_payload(identity={"granularity": "item", "itemId": f"urn:example:item:{index:06d}"})
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


def test_health_returns_only_public_status(client):
    assert client.get("/health").json() == {"status": "ok", "schemaVersion": "1.0.0"}


def test_the_development_auth_stand_in_is_off_by_default(monkeypatch, store, ledger):
    from fastapi.testclient import TestClient

    from sort4circ_dpp.api import create_app

    monkeypatch.delenv("DPP_DEMO_AUTH", raising=False)
    isolated = TestClient(create_app(store=store, ledger=ledger))
    response = isolated.get("/v1/dpps", headers=HEADERS["administrator"])
    assert response.status_code == 401
    assert response.json()["reasonCode"] == "S4C-AUTH-INVALID-TOKEN"


def test_verification_rejects_evidence_belonging_to_another_passport(client, dpp_id):
    from sort4circ_dpp.synthetic import SyntheticFixtureFactory
    other = client.post("/v1/dpps", headers=HEADERS["brand"],
                        json=SyntheticFixtureFactory().passport(2))
    other.raise_for_status()
    entry = next(e for e in client.app.state.store.outbox if e.dpp_id == dpp_id)
    response = client.post(f"/v1/dpps/{other.json()['dppId']}/integrity/verify",
                           headers=HEADERS["integrityVerifier"], json={"evidenceId": entry.evidence_id})
    assert response.status_code == 404


def test_same_idempotency_key_does_not_cross_caller_boundaries(client):
    from sort4circ_dpp.synthetic import SyntheticFixtureFactory
    first = client.post("/v1/dpps", headers={**HEADERS["brand"], "Idempotency-Key": "synthetic-shared-key"},
                        json=SyntheticFixtureFactory().passport(3))
    second = client.post("/v1/dpps", headers={**HEADERS["brand"], "X-DPP-Subject": "synthetic-other-caller",
                                             "Idempotency-Key": "synthetic-shared-key"},
                         json=SyntheticFixtureFactory().passport(4))
    assert first.status_code == second.status_code == 201
    assert first.json()["dppId"] != second.json()["dppId"]
