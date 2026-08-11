"""The common ledger adapter contract.

Every adapter implements submit, status, receipt and verify. A new adapter
passes the full contract-test set in ``tests/test_ledger_contract.py`` before
activation; the same tests run against every adapter, so a platform change is a
configuration change rather than a rewrite.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Receipt:
    """A platform-independent submission receipt."""

    evidence_id: str
    transaction_ref: str
    network_id: str
    state: str
    confirmed_at: str | None = None
    block_ref: str | None = None
    raw: dict[str, Any] | None = None


class LedgerError(RuntimeError):
    """Adapter failure carrying the reason code the service should record."""

    def __init__(self, reason_code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.retryable = retryable


class LedgerAdapter(abc.ABC):
    """Interface every ledger implementation satisfies."""

    network_id: str

    @abc.abstractmethod
    def submit(self, evidence_id: str, envelope: dict[str, Any]) -> Receipt:
        """Broadcast an evidence envelope.

        Submitting the same ``evidence_id`` twice returns the original receipt
        rather than creating a second anchor. A retry after an ambiguous outcome
        therefore cannot produce a duplicate that is indistinguishable from a
        replay afterwards.
        """

    @abc.abstractmethod
    def status(self, evidence_id: str) -> Receipt | None:
        """Return the current receipt, or None when the evidence is unknown."""

    @abc.abstractmethod
    def anchored_digest(self, evidence_id: str) -> str | None:
        """Return the digest recorded on the ledger for ``evidence_id``."""

    def verify(self, evidence_id: str, recomputed_digest: str) -> str:
        """Return a verdict for ``recomputed_digest`` against the anchor.

        Four verdicts are distinguished because they call for different actions.
        ``match`` and ``mismatch`` are integrity statements. ``unanchored`` is an
        operational condition, not a tampering indication. ``unverifiable``
        signals a retention defect. Collapsing the last two into ``mismatch``
        would misattribute an availability problem to an integrity failure.
        """
        receipt = self.status(evidence_id)
        if receipt is None:
            return "unverifiable"
        if receipt.state != "confirmed":
            return "unanchored"
        anchored = self.anchored_digest(evidence_id)
        if anchored is None:
            return "unverifiable"
        return "match" if anchored == recomputed_digest else "mismatch"
