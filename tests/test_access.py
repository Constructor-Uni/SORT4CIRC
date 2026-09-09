"""Access-control enforcement.

The pass criterion is zero unauthorised disclosures and zero denials of a
permitted operation. The denied set deliberately includes requests that succeed
for an adjacent role, so a policy that grants too broadly is detected rather
than assumed absent.
"""

from __future__ import annotations

import pytest

from conftest import EPC_ENCODED, HEADERS
from sort4circ_dpp.access import Principal, matrix, resolve_view

COMMERCIAL_MEMBERS = {"responsibleOperatorId", "registryIdentifier", "environmentalValues"}


def test_an_unauthenticated_caller_receives_the_public_view(client, dpp_id):
    response = client.get(f"/v1/dpps/{dpp_id}")
    assert response.status_code == 200
    assert response.json()["view"] == "public"


def test_the_public_view_carries_no_commercial_members(client, dpp_id):
    body = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["consumer"]).json()
    assert COMMERCIAL_MEMBERS.isdisjoint(body)
    assert "epc" not in body["identity"], "the public view does not expose the operational identifier"


def test_a_consumer_cannot_reach_the_sorting_view(client, dpp_id):
    response = client.get(f"/v1/dpps/{dpp_id}/sorting-view", headers=HEADERS["consumer"])
    assert response.status_code == 403
    assert response.json()["reasonCode"] == "S4C-AUTHZ-OPERATION-FORBIDDEN"


def test_the_same_request_succeeds_for_the_adjacent_role(client, dpp_id):
    """The denial above must come from the policy, not from a broken endpoint."""
    assert client.get(f"/v1/dpps/{dpp_id}/sorting-view", headers=HEADERS["sortingOperator"]).status_code == 200


def test_a_request_for_a_wider_view_is_narrowed_rather_than_refused(client, dpp_id):
    body = client.get(f"/v1/dpps/{dpp_id}?view=full", headers=HEADERS["consumer"]).json()
    assert body["view"] == "public", "a tightening policy returns less, it does not break the integration"


def test_a_external_system_cannot_create_a_passport(client):
    from conftest import passport_payload

    response = client.post("/v1/dpps", json=passport_payload(), headers=HEADERS["pssrSystem"])
    assert response.status_code == 403


def test_a_external_system_may_submit_an_observation(client, dpp_id):
    response = client.post(
        f"/v1/dpps/{dpp_id}/observations",
        headers=HEADERS["pssrSystem"],
        json={
            "observationId": "urn:example:obs:000200",
            "fibreType": "cotton",
            "percentage": 58.25,
            "percentageBasis": "mass",
            "valueStatus": "supplied",
            "method": "nirSpectroscopy",
            "sourceOrganisationId": "urn:example:org:sorter-a",
            "observedAt": "2041-03-05T14:20:00Z",
            "confidence": {"value": 0.73, "scale": "unitInterval"},
        },
    )
    assert response.status_code == 201


def test_the_integrity_verifier_receives_no_product_content(client, dpp_id):
    body = client.get(f"/v1/dpps/{dpp_id}?view=integrityOnly", headers=HEADERS["integrityVerifier"]).json()
    assert set(body) == {"dppId", "schemaVersion", "recordVersion", "accessPolicyVersion", "view", "integrity"}
    assert "product" not in body, "delegated verification must not require disclosure"


def test_the_integrity_verifier_cannot_widen_the_view(client, dpp_id):
    response = client.get(f"/v1/dpps/{dpp_id}?view=sorting", headers=HEADERS["integrityVerifier"])
    assert response.status_code == 403
    assert response.json()["reasonCode"] == "S4C-AUTHZ-VIEW-FORBIDDEN"


def test_the_partner_view_shows_only_the_callers_own_events(client, dpp_id):
    for organisation, event_id in (("urn:example:org:collector-a", "urn:example:event:own"), ("urn:example:org:collector-b", "urn:example:event:other")):
        client.post(
            f"/v1/dpps/{dpp_id}/events",
            headers={"X-DPP-Role": "administrator", "X-DPP-Organisation": organisation},
            json={
                "eventId": event_id,
                "eventType": "collection",
                "eventTime": "2041-03-05T14:20:00Z",
                "eventTimeZoneOffset": "+02:00",
                "actorOrganisationId": organisation,
                "sourceSystemId": "urn:example:system:simulator-a",
            },
        ).raise_for_status()

    body = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["collector"]).json()
    assert [e["eventId"] for e in body["lifecycleEvents"]] == ["urn:example:event:own"]


def test_a_forbidden_read_is_indistinguishable_from_an_unknown_identifier(client):
    """The endpoint must not become an enumeration oracle."""
    unknown = client.get("/v1/identifiers/urn%3Aexample%3Acarrier%3Aunknown/dpp", headers=HEADERS["pssrSystem"])
    forbidden = client.get(f"/v1/identifiers/{EPC_ENCODED}/dpp", headers=HEADERS["consumer"])
    assert unknown.status_code == 404
    assert forbidden.status_code == 403
    assert set(forbidden.json()) >= {"type", "title", "status", "detail", "instance", "reasonCode"}
    assert set(unknown.json()) >= {"type", "title", "status", "detail", "instance", "reasonCode"}
    assert "dppId" not in forbidden.json(), "a refusal reveals nothing about existence"


@pytest.mark.parametrize("role", sorted(matrix()["roles"]))
def test_every_declared_role_resolves_to_a_declared_view(role):
    principal = Principal(subject="t", role=role)
    assert resolve_view(principal, None) in matrix()["views"]


def test_no_role_may_rewrite_an_append_only_collection(client, dpp_id):
    etag = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["administrator"]).headers["ETag"]
    response = client.patch(
        f"/v1/dpps/{dpp_id}",
        headers={**HEADERS["administrator"], "If-Match": etag},
        json={"materialObservations": []},
    )
    assert response.status_code == 422
    assert response.json()["reasonCode"] == "S4C-STATE-APPEND-ONLY-VIOLATION"


def test_the_brand_role_cannot_write_outside_its_permitted_members(client, dpp_id):
    etag = client.get(f"/v1/dpps/{dpp_id}", headers=HEADERS["brand"]).headers["ETag"]
    response = client.patch(
        f"/v1/dpps/{dpp_id}",
        headers={**HEADERS["brand"], "If-Match": etag},
        json={"status": "retired"},
    )
    assert response.status_code == 403
    assert response.json()["errors"] == [{"path": "status"}]
