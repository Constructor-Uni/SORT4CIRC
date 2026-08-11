"""Evidence state machine, retries and recovery."""

from __future__ import annotations

import pytest

from conftest import passport_payload
from sort4circ_dpp.evidence import TERMINAL_STATES, EvidenceWorker, TransitionError, envelope_for, transition
from sort4circ_dpp.ledger.memory import InMemoryLedger
from sort4circ_dpp.store import PassportStore


def build(**ledger_kwargs):
    store = PassportStore()
    store.create(passport_payload())
    return store, EvidenceWorker(store=store, ledger=InMemoryLedger(**ledger_kwargs))


def test_the_envelope_carries_a_reference_and_a_digest_and_nothing_else():
    store, worker = build()
    body = envelope_for(store.outbox[0])
    assert set(body) == {
        "evidenceId", "subjectRef", "subjectVersion",
        "canonicalisation", "digestAlgorithm", "digestValue", "createdAt",
    }
    serialised = str(body)
    assert "polyester" not in serialised and "TXHO" not in serialised, "no passport content reaches the ledger"


def test_a_clean_drain_confirms_every_entry():
    store, worker = build()
    assert worker.drain() == {"confirmed": 1}
    assert worker.unresolved() == []


def test_an_impossible_transition_is_refused():
    store, worker = build()
    entry = store.outbox[0]
    with pytest.raises(TransitionError):
        transition(entry, "confirmed")


def test_a_retryable_failure_reuses_the_same_evidence_identifier():
    store, worker = build()
    entry = store.outbox[0]
    original_id, original_digest = entry.evidence_id, entry.digest_value
    worker.ledger.fail_next = "S4C-LEDGER-UNAVAILABLE"
    worker.drain()
    assert entry.state == "retryableFailed"
    assert entry.last_reason_code == "S4C-LEDGER-UNAVAILABLE"
    worker.drain()
    assert entry.state == "confirmed"
    assert entry.evidence_id == original_id and entry.digest_value == original_digest


def test_repeated_failure_reaches_a_terminal_state_rather_than_looping():
    store, worker = build()
    worker.max_attempts = 2
    for _ in range(6):
        worker.ledger.fail_next = "S4C-LEDGER-UNAVAILABLE"
        worker.drain()
    assert store.outbox[0].state in TERMINAL_STATES


def test_reconciliation_recovers_an_ambiguous_outcome_without_a_second_anchor():
    store, worker = build()
    entry = store.outbox[0]
    worker.ledger.fail_next = "S4C-LEDGER-TIMEOUT-AFTER-BROADCAST"
    worker.drain()
    assert entry.state == "retryableFailed"

    # The transaction did reach the ledger. Reconciliation by evidence
    # identifier finds it; resubmitting blind would anchor the same version
    # twice and the duplicate would be indistinguishable from a replay.
    worker.ledger.confirm(entry.evidence_id, "2026-08-10T09:14:19.004Z")
    assert worker.reconcile() == 1
    assert entry.state == "confirmed"
    assert len({e.transaction_ref for e in store.outbox if e.transaction_ref}) == 1


def test_every_accepted_write_reaches_a_terminal_state_after_an_outage():
    """Recovery target from the deliverable: no accepted evidence is lost."""
    store = PassportStore()
    for index in range(25):
        store.create(passport_payload(identity={"granularity": "item", "itemId": f"urn:sort4circ:item:{index:06d}"}))
    ledger = InMemoryLedger()
    worker = EvidenceWorker(store=store, ledger=ledger)

    ledger.fail_next = "S4C-LEDGER-UNAVAILABLE"
    worker.drain()

    # The dependency returns and a restarted worker drains the same queue.
    restarted = EvidenceWorker(store=store, ledger=ledger)
    restarted.drain()
    restarted.reconcile()

    accepted = len(store.outbox)
    terminal = sum(1 for e in store.outbox if e.state in TERMINAL_STATES)
    assert accepted == 25
    assert terminal == accepted, "100 percent of accepted evidence reaches a terminal state"


def test_sorting_never_waits_for_the_ledger():
    """An unavailable ledger must not stop the line."""
    store, worker = build()
    worker.ledger.fail_next = "S4C-LEDGER-UNAVAILABLE"
    worker.drain()
    record = next(iter(store))
    assert record["recordVersion"] == 1, "the passport is readable while evidence is still queued"
    assert store.outbox[0].state == "retryableFailed"
