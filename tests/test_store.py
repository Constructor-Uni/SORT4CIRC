"""Repository invariants: versioning, append-only collections and bindings."""

from __future__ import annotations

import pytest

from conftest import EPC, passport_payload
from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.store import PassportStore, etag


def carrier(encoded=EPC):
    return {
        "carrierType": "qrCode",
        "encodingScheme": "proprietary",
        "encodedIdentifier": encoded,
        "boundBy": "urn:example:org:manufacturer-a",
    }


def test_create_starts_at_version_one_and_queues_evidence(store: PassportStore):
    record = store.create(passport_payload())
    assert record["recordVersion"] == 1
    assert len(store.outbox) == 1
    assert store.outbox[0].subject_version == 1
    assert store.outbox[0].state == "queued", "the write and its evidence entry commit together"


def test_every_write_increments_the_version_and_retains_history(store: PassportStore):
    record = store.create(passport_payload())
    store.patch(record["dppId"], {"product": {"condition": "wornUsable"}}, etag(record))
    history = store.history(record["dppId"])
    assert [h["recordVersion"] for h in history] == [1, 2]
    assert history[0]["product"].get("condition") is None, "the earlier version is unchanged"


def test_stale_if_match_is_refused(store: PassportStore):
    record = store.create(passport_payload())
    stale = etag(record)
    store.patch(record["dppId"], {"product": {"condition": "good"}}, stale)
    with pytest.raises(DppError) as excinfo:
        store.patch(record["dppId"], {"product": {"condition": "asNew"}}, stale)
    assert excinfo.value.code == "S4C-STATE-VERSION-CONFLICT"


def test_missing_if_match_is_refused(store: PassportStore):
    record = store.create(passport_payload())
    with pytest.raises(DppError) as excinfo:
        store.patch(record["dppId"], {"product": {"condition": "good"}}, None)
    assert excinfo.value.code == "S4C-STATE-VERSION-CONFLICT"


def test_observations_cannot_be_removed_or_rewritten(store: PassportStore):
    record = store.create(passport_payload())
    shortened = record["materialObservations"][:1]
    with pytest.raises(DppError) as excinfo:
        store.patch(record["dppId"], {"materialObservations": shortened}, etag(record))
    assert excinfo.value.code == "S4C-STATE-APPEND-ONLY-VIOLATION"

    rewritten = [dict(record["materialObservations"][0], percentage=50), record["materialObservations"][1]]
    with pytest.raises(DppError) as excinfo:
        store.patch(record["dppId"], {"materialObservations": rewritten}, etag(record))
    assert excinfo.value.code == "S4C-STATE-APPEND-ONLY-VIOLATION"


def test_appending_the_same_event_twice_is_idempotent(store: PassportStore):
    record = store.create(passport_payload())
    event = {
        "eventId": "urn:uuid:e1",
        "eventType": "collection",
        "eventTime": "2041-03-05T14:20:00Z",
        "eventTimeZoneOffset": "+02:00",
        "recordedAt": "2041-03-05T14:20:00Z",
        "actorOrganisationId": "urn:example:org:sorter-a",
        "sourceSystemId": "urn:example:system:simulator-a",
    }
    first = store.append(record["dppId"], "lifecycleEvents", event, "eventId")
    second = store.append(record["dppId"], "lifecycleEvents", event, "eventId")
    assert len(second["lifecycleEvents"]) == 1
    assert second["recordVersion"] == first["recordVersion"], "a retry creates no second state change"


def test_only_one_binding_is_commissioned_at_a_time(store: PassportStore):
    record = store.create(passport_payload())
    store.commission_carrier(record["dppId"], carrier())
    updated = store.commission_carrier(record["dppId"], carrier("urn:example:carrier:000002"))
    states = [c["bindingStatus"] for c in updated["carriers"]]
    assert states.count("commissioned") == 1
    assert "replaced" in states
    assert all("closedAt" in c for c in updated["carriers"] if c["bindingStatus"] != "commissioned")


def test_an_identifier_is_never_bound_to_two_products(store: PassportStore):
    first = store.create(passport_payload())
    second = store.create(passport_payload(identity={"granularity": "item", "itemId": "urn:example:item:000002"}))
    store.commission_carrier(first["dppId"], carrier())
    with pytest.raises(DppError) as excinfo:
        store.commission_carrier(second["dppId"], carrier())
    assert excinfo.value.code == "S4C-IDENT-DUPLICATE-BINDING"


def test_a_retired_identifier_is_not_reassigned(store: PassportStore):
    first = store.create(passport_payload())
    store.commission_carrier(first["dppId"], carrier())
    store.commission_carrier(first["dppId"], carrier("urn:example:carrier:000001"))
    second = store.create(passport_payload(identity={"granularity": "item", "itemId": "urn:example:item:000003"}))
    with pytest.raises(DppError) as excinfo:
        store.commission_carrier(second["dppId"], carrier())
    assert excinfo.value.code == "S4C-IDENT-DUPLICATE-BINDING"


def test_resolution_of_an_unknown_identifier(store: PassportStore):
    with pytest.raises(DppError) as excinfo:
        store.resolve_carrier("urn:example:carrier:unknown")
    assert excinfo.value.code == "S4C-IDENT-UNKNOWN"


def test_every_version_stays_retrievable_for_verification(store: PassportStore):
    record = store.create(passport_payload())
    store.patch(record["dppId"], {"product": {"condition": "good"}}, etag(record))
    assert store.get_version(record["dppId"], 1)["recordVersion"] == 1
    with pytest.raises(DppError):
        store.get_version(record["dppId"], 99)
