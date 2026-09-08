"""Generic backend behaviour exercised against the educational memory adapter."""

from __future__ import annotations

import pytest

from sort4circ_dpp.ledger.base import LedgerError
from sort4circ_dpp.ledger.memory import InMemoryLedger

DIGEST = "c99a12da1b69a0acce1b3f7f3dca0a6af740ebc7cdd80ab08060e908986da715"


def envelope(evidence_id="urn:example:evidence:1", digest=DIGEST):
    return {
        "evidenceId": evidence_id,
        "subjectRef": "urn:example:dpp:000001",
        "subjectVersion": 1,
        "canonicalisation": "rfc8785",
        "digestAlgorithm": "sha-256",
        "digestValue": digest,
        "createdAt": "2042-02-13T10:30:00Z",
    }


@pytest.fixture(params=[InMemoryLedger], ids=["memory"])
def adapter(request):
    return request.param()


def test_submission_returns_a_receipt(adapter):
    receipt = adapter.submit("e1", envelope())
    assert receipt.transaction_ref
    assert receipt.network_id == adapter.network_id
    assert receipt.state in {"submitted", "confirmed"}


def test_resubmitting_the_same_evidence_returns_the_original_receipt(adapter):
    first = adapter.submit("e1", envelope())
    second = adapter.submit("e1", envelope())
    assert first.transaction_ref == second.transaction_ref, "a retry must not create a second anchor"


def test_status_of_unknown_evidence_is_none(adapter):
    assert adapter.status("never-submitted") is None


def test_verify_distinguishes_four_verdicts(adapter):
    adapter.submit("e1", envelope())
    assert adapter.verify("e1", DIGEST) == "match"
    assert adapter.verify("e1", "0" * 64) == "mismatch"
    assert adapter.verify("unknown", DIGEST) == "unverifiable"

    pending = InMemoryLedger(auto_confirm=False)
    pending.submit("e2", envelope("urn:example:evidence:2"))
    assert pending.verify("e2", DIGEST) == "unanchored", "a pending anchor is not a tampering indication"


def test_a_rejected_submission_is_not_retryable(adapter):
    adapter.fail_next = "S4C-LEDGER-SUBMIT-REJECTED"
    with pytest.raises(LedgerError) as excinfo:
        adapter.submit("e1", envelope())
    assert excinfo.value.reason_code == "S4C-LEDGER-SUBMIT-REJECTED"
    assert excinfo.value.retryable is False


def test_an_unavailable_network_is_retryable(adapter):
    adapter.fail_next = "S4C-LEDGER-UNAVAILABLE"
    with pytest.raises(LedgerError) as excinfo:
        adapter.submit("e1", envelope())
    assert excinfo.value.retryable is True


def test_a_timeout_after_broadcast_leaves_the_transaction_findable(adapter):
    """The transaction may have succeeded, so it must remain reconcilable."""
    adapter.fail_next = "S4C-LEDGER-TIMEOUT-AFTER-BROADCAST"
    with pytest.raises(LedgerError):
        adapter.submit("e1", envelope())
    assert adapter.status("e1") is not None, "reconciliation by evidence identifier must be possible"
