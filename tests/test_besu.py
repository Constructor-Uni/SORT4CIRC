"""Fail-closed verification tests for the Besu adapter."""

from __future__ import annotations

from sort4circ_dpp.ledger.base import Receipt
from sort4circ_dpp.ledger.besu import BesuLedger

DIGEST = "dd14a3f2487f2b22deda4a7bc2b37e775f378e05d60dc1e6ad26fdf26038ae9f"


def _ledger_with_receipt(state: str) -> BesuLedger:
    ledger = BesuLedger()
    ledger._receipts["e1"] = Receipt(
        evidence_id="e1",
        transaction_ref="0xtx",
        network_id=ledger.network_id,
        state=state,
    )
    ledger._digests["e1"] = DIGEST
    return ledger


def test_besu_does_not_expose_the_locally_cached_digest():
    ledger = _ledger_with_receipt("confirmed")

    assert ledger.anchored_digest("e1") is None


def test_besu_confirmed_local_cache_is_unverifiable():
    ledger = _ledger_with_receipt("confirmed")

    assert ledger.verify("e1", DIGEST) == "unverifiable"


def test_besu_submitted_receipt_remains_unanchored(monkeypatch):
    ledger = _ledger_with_receipt("submitted")
    monkeypatch.setattr(ledger, "status", lambda evidence_id: ledger._receipts[evidence_id])

    assert ledger.verify("e1", DIGEST) == "unanchored"
