"""Optional projection lag bounds are caller-selected, with no deployment defaults."""
import pytest

from conftest import passport_payload
from sort4circ_dpp.index import ReadIndex
from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.synthetic import SyntheticFixtureFactory


def test_quiet_projection_has_no_backlog(store):
    index = ReadIndex(store=store, max_lag_ms=250)
    index.attach()
    record = store.create(passport_payload())
    index._entries[record["dppId"]].generated_at_ms -= 10000
    assert index.sorting_view(record["dppId"])["indexLagMs"] == 0

def test_stopped_projection_can_be_bounded_and_strong_read_recovers(store):
    index = ReadIndex(store=store, max_lag_ms=250)
    index.attach()
    record = store.create(passport_payload())
    store.on_commit = None
    store.append(record["dppId"], "lifecycleEvents", SyntheticFixtureFactory().event(), "eventId")
    index.caught_up_at_ms -= 500
    with pytest.raises(DppError) as raised:
        index.sorting_view(record["dppId"])
    assert raised.value.code == "S4C-DEP-UNAVAILABLE"
    assert index.sorting_view(record["dppId"], strong=True)["recordVersion"] == store.get(record["dppId"])["recordVersion"]
