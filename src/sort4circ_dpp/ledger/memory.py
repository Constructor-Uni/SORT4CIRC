"""Reference ledger adapter.

Deterministic and dependency-free, so the conformance suite can exercise the
whole evidence path without a network. Confirmation is simulated by an explicit
call rather than by elapsed time, which keeps the tests reproducible.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from ..canonical import canonicalise
from .base import LedgerAdapter, LedgerError, Receipt


@dataclass
class InMemoryLedger(LedgerAdapter):
    network_id: str = "example-memory"
    auto_confirm: bool = True
    fail_next: str | None = None
    _receipts: dict[str, Receipt] = field(default_factory=dict)
    _digests: dict[str, str] = field(default_factory=dict)

    def submit(self, evidence_id: str, envelope: dict[str, Any]) -> Receipt:
        if evidence_id in self._receipts:
            return self._receipts[evidence_id]

        if self.fail_next is not None:
            code, self.fail_next = self.fail_next, None
            retryable = code != "S4C-LEDGER-SUBMIT-REJECTED"
            if code == "S4C-LEDGER-TIMEOUT-AFTER-BROADCAST":
                # The transaction may have succeeded. Record it as broadcast so
                # that reconciliation by evidence identifier can find it, and
                # never resubmit blind.
                self._store(evidence_id, envelope, state="submitted")
            raise LedgerError(code, f"{code} raised by the reference adapter", retryable=retryable)

        return self._store(evidence_id, envelope, state="confirmed" if self.auto_confirm else "submitted")

    def _store(self, evidence_id: str, envelope: dict[str, Any], *, state: str) -> Receipt:
        payload = canonicalise(envelope).encode("utf-8")
        tx = "0x" + hashlib.sha256(payload + evidence_id.encode()).hexdigest()
        receipt = Receipt(
            evidence_id=evidence_id,
            transaction_ref=tx,
            network_id=self.network_id,
            state=state,
            confirmed_at=envelope.get("createdAt") if state == "confirmed" else None,
            block_ref=f"block-{len(self._receipts) + 1}",
            raw={"envelopeBytes": len(payload)},
        )
        self._receipts[evidence_id] = receipt
        self._digests[evidence_id] = envelope["digestValue"]
        return receipt

    def confirm(self, evidence_id: str, confirmed_at: str) -> Receipt:
        """Move a broadcast transaction to confirmed."""
        receipt = self._receipts[evidence_id]
        confirmed = Receipt(
            evidence_id=receipt.evidence_id,
            transaction_ref=receipt.transaction_ref,
            network_id=receipt.network_id,
            state="confirmed",
            confirmed_at=confirmed_at,
            block_ref=receipt.block_ref,
            raw=receipt.raw,
        )
        self._receipts[evidence_id] = confirmed
        return confirmed

    def status(self, evidence_id: str) -> Receipt | None:
        return self._receipts.get(evidence_id)

    def anchored_digest(self, evidence_id: str) -> str | None:
        return self._digests.get(evidence_id)
