"""Staleness of the sorting projection.

These tests exist because the load campaign in ``tools/loadtest.py`` exposed a
defect that no functional test reached: the projection was refused once its
wall-clock age passed the staleness limit, whether or not the underlying record
had changed. On a line that pauses for longer than the limit, every subsequent
sorting read failed with ``S4C-DEP-UNAVAILABLE`` until the next write, which
turns an idle conveyor into an outage.

The limit exists to catch a projector that has fallen behind the source. That is
what is asserted here, and the two situations are separated: a projection that
nothing has invalidated is current, and a projector that has stopped while writes
continued is not.
"""

from __future__ import annotations

import time

import pytest

from conftest import passport_payload
from sort4circ_dpp.config import INDEX_STALENESS_LIMIT_MS
from sort4circ_dpp.index import ReadIndex
from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.store import PassportStore


def lifecycle_event() -> dict[str, object]:
    return {
        "eventId": "urn:sort4circ:event:idx0001",
        "eventType": "collection",
        "eventTime": "2026-08-10T09:00:00Z",
        "eventTimeZoneOffset": "+02:00",
        "recordedAt": "2026-08-10T09:00:01Z",
        "actorOrganisationId": "urn:sort4circ:org:collector-a",
        "sourceSystemId": "urn:sort4circ:system:gate-1",
    }


@pytest.fixture
def indexed(store: PassportStore) -> tuple[PassportStore, ReadIndex, str]:
    index = ReadIndex(store=store)
    index.attach()
    record = store.create(passport_payload(dppId="urn:sort4circ:dpp:idx0001"))
    return store, index, record["dppId"]


def test_an_unchanged_projection_is_served_however_long_the_line_has_been_quiet(indexed):
    store, index, dpp_id = indexed
    entry = index._entries[dpp_id]  # noqa: SLF001 - asserting on projector internals
    # Push the commit and its projection an hour into the past together, which
    # is what a quiet line produces: nothing has changed and nothing is late.
    quiet_ms = 3_600_000.0
    entry.committed_at_ms -= quiet_ms
    entry.generated_at_ms -= quiet_ms
    store.last_commit_ms -= quiet_ms
    index.caught_up_at_ms -= quiet_ms

    view = index.sorting_view(dpp_id)
    assert view["consistency"] == "projected"
    assert view["indexLagMs"] == 0
    assert index.backlog_ms() == 0.0


def test_a_projector_that_stopped_while_writes_continued_is_refused(indexed):
    store, index, dpp_id = indexed
    # Detach the projector, then commit. The source advances and the projection
    # does not, which is the condition the limit is for.
    store.on_commit = None
    store.append(dpp_id, "lifecycleEvents", lifecycle_event(), "eventId")
    index.caught_up_at_ms -= INDEX_STALENESS_LIMIT_MS + 1_000.0

    assert index.backlog_ms() > INDEX_STALENESS_LIMIT_MS
    with pytest.raises(DppError) as raised:
        index.sorting_view(dpp_id)
    assert raised.value.code == "S4C-DEP-UNAVAILABLE"
    assert raised.value.extra["backlogMs"] > INDEX_STALENESS_LIMIT_MS


def test_the_strong_read_is_always_available_when_the_projection_is_refused(indexed):
    store, index, dpp_id = indexed
    store.on_commit = None
    store.append(dpp_id, "lifecycleEvents", lifecycle_event(), "eventId")
    index.caught_up_at_ms -= INDEX_STALENESS_LIMIT_MS + 1_000.0

    view = index.sorting_view(dpp_id, strong=True)
    assert view["consistency"] == "strong"
    assert view["indexLagMs"] == 0
    assert view["recordVersion"] == store.get(dpp_id)["recordVersion"]


def test_the_reported_lag_carries_injected_projector_delay(indexed):
    _, index, dpp_id = indexed
    index.lag_ms = 40.0
    view = index.sorting_view(dpp_id)
    assert view["indexLagMs"] == 40


def test_a_projection_regenerated_on_commit_reports_a_lag_near_zero(indexed):
    store, index, dpp_id = indexed
    before = time.monotonic() * 1000.0
    store.append(dpp_id, "lifecycleEvents", lifecycle_event(), "eventId")
    view = index.sorting_view(dpp_id)
    assert view["indexLagMs"] < 50
    assert index._entries[dpp_id].committed_at_ms >= before  # noqa: SLF001


def test_read_index_reconstructs_from_authoritative_committed_state(store):
    first = store.create(passport_payload(dppId="urn:sort4circ:dpp:rebuild-1"))
    second = store.create(passport_payload(dppId="urn:sort4circ:dpp:rebuild-2"))
    rebuilt = ReadIndex(store=store)
    rebuilt.attach()
    assert len(rebuilt) == 2
    assert rebuilt.sorting_view(first["dppId"])["recordVersion"] == first["recordVersion"]
    assert rebuilt.sorting_view(second["dppId"])["recordVersion"] == second["recordVersion"]


def test_read_index_exposes_no_domain_write_or_identifier_creation_api(store):
    index = ReadIndex(store=store)
    forbidden = {"create", "patch", "append", "commission_carrier", "retire", "new_urn"}
    assert not forbidden.intersection(dir(index))
    record = store.create(passport_payload(dppId="urn:sort4circ:dpp:read-only-index"))
    before = (record["recordVersion"], len(store.outbox), len(store._history[record["dppId"]]))  # noqa: SLF001
    index.attach()
    index.sorting_view(record["dppId"])
    after_record = store.get(record["dppId"])
    after = (after_record["recordVersion"], len(store.outbox), len(store._history[record["dppId"]]))  # noqa: SLF001
    assert after == before, "reading or reconstructing the index must not write domain state"
