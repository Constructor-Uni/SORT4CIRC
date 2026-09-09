"""In-memory evidence state transitions and an optional integrity worker.

Ledger submission is separated from the write response. The evidence item is created
inside the write transaction, placed in the reference implementation's process-local
in-memory outbox, and advanced by a worker, so a caller is never blocked on anchoring.

The outbox is process memory: no durable queue and no deployed network is provided here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import CANONICALISATION_PROFILE, DIGEST_ALGORITHM
from .ledger.base import LedgerAdapter, LedgerError
from .store import OutboxEntry, PassportStore, utcnow

#: Permitted transitions. Any other transition is a defect, and the worker
#: refuses it rather than recording an impossible history.
TRANSITIONS: dict[str, set[str]] = {
    "created": {"queued"},
    "queued": {"submitted", "retryableFailed", "terminalFailed"},
    "submitted": {"confirmed", "retryableFailed", "terminalFailed"},
    "retryableFailed": {"queued", "terminalFailed"},
    "confirmed": set(),
    "terminalFailed": set(),
}

TERMINAL_STATES = {"confirmed", "terminalFailed"}


class TransitionError(RuntimeError):
    pass


def transition(entry: OutboxEntry, new_state: str, *, reason_code: str | None = None) -> None:
    if new_state not in TRANSITIONS[entry.state]:
        raise TransitionError(f"{entry.state} -> {new_state} is not a permitted transition")
    entry.state = new_state
    entry.last_reason_code = reason_code
    if new_state == "submitted":
        entry.attempts += 1


def envelope_for(entry: OutboxEntry) -> dict[str, Any]:
    """Return the evidence envelope submitted to the ledger.

    The envelope carries a reference and a digest and no passport content. That
    is the only reason a mock envelope limits the data disclosed: the
    property belongs to the envelope design, not to the platform.
    """
    return {
        "evidenceId": entry.evidence_id,
        "subjectRef": entry.dpp_id,
        "subjectVersion": entry.subject_version,
        "canonicalisation": CANONICALISATION_PROFILE,
        "digestAlgorithm": DIGEST_ALGORITHM,
        "digestValue": entry.digest_value,
        "createdAt": entry.created_at,
    }


@dataclass
class EvidenceWorker:
    """Drains the outbox onto the ledger."""

    store: PassportStore
    ledger: LedgerAdapter
    max_attempts: int = 5

    def drain(self) -> dict[str, int]:
        """Process every non-terminal entry once. Returns a state histogram."""
        for entry in self.store.outbox:
            if entry.state in TERMINAL_STATES:
                continue
            self._process(entry)
        return self.histogram()

    def _process(self, entry: OutboxEntry) -> None:
        if entry.state == "retryableFailed":
            if entry.attempts >= self.max_attempts:
                transition(entry, "terminalFailed", reason_code=entry.last_reason_code)
                return
            transition(entry, "queued")

        try:
            receipt = self.ledger.submit(entry.evidence_id, envelope_for(entry))
        except LedgerError as exc:
            entry.attempts += 1
            target = "retryableFailed" if exc.retryable else "terminalFailed"
            if entry.state == "queued":
                entry.state = target
                entry.last_reason_code = exc.reason_code
            return

        transition(entry, "submitted", reason_code=None)
        entry.transaction_ref = receipt.transaction_ref
        entry.ledger_network_id = receipt.network_id
        if receipt.state == "confirmed":
            transition(entry, "confirmed")
            entry.confirmed_at = receipt.confirmed_at or utcnow()

    def reconcile(self) -> int:
        """Recover entries whose outcome was unknown after broadcast.

        Reconciliation is by evidence identifier, always before any resubmission.
        Resubmitting without it produces a second anchor for one record version,
        and the duplicate is indistinguishable from a replay afterwards.
        """
        recovered = 0
        for entry in self.store.outbox:
            if entry.state in TERMINAL_STATES:
                continue
            receipt = self.ledger.status(entry.evidence_id)
            if receipt is None:
                continue
            entry.transaction_ref = receipt.transaction_ref
            entry.ledger_network_id = receipt.network_id
            if receipt.state == "confirmed":
                if entry.state == "retryableFailed":
                    entry.state = "submitted"
                if entry.state == "queued":
                    entry.state = "submitted"
                transition(entry, "confirmed")
                entry.confirmed_at = receipt.confirmed_at or utcnow()
                recovered += 1
        return recovered

    def histogram(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.store.outbox:
            counts[entry.state] = counts.get(entry.state, 0) + 1
        return counts

    def unresolved(self) -> list[OutboxEntry]:
        return [e for e in self.store.outbox if e.state not in TERMINAL_STATES]
