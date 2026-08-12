"""Hyperledger Besu adapter for a permissioned reference network.

The adapter speaks JSON-RPC to a Besu node and stores the evidence digest in an
anchoring contract. It is written to the same contract as every other adapter,
so the DPP service and the public API are unchanged when this adapter replaces
the reference one.

Configuration is read from the environment, never from source. The private key
is never logged, never returned in a response and never written to a passport.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .base import LedgerAdapter, LedgerError, Receipt

# keccak256("anchor(bytes32,bytes32)")[:4]
ANCHOR_SELECTOR = "0x6b2b8b1a"


@dataclass
class BesuLedger(LedgerAdapter):
    """Anchor digests on a permissioned Besu network.

    This adapter is provided so the anchoring path can be exercised against a
    real node. It performs no key management of its own: signing is delegated to
    the node or to an external signer identified by ``from_address``, which is
    the arrangement the security guideline requires.
    """

    rpc_url: str = field(default_factory=lambda: os.environ.get("S4C_BESU_RPC", "http://localhost:8545"))
    contract_address: str = field(default_factory=lambda: os.environ.get("S4C_BESU_CONTRACT", ""))
    from_address: str = field(default_factory=lambda: os.environ.get("S4C_BESU_FROM", ""))
    network_id: str = field(default_factory=lambda: os.environ.get("S4C_LEDGER_NETWORK", "s4c-besu-ref"))
    timeout_seconds: float = 10.0
    _receipts: dict[str, Receipt] = field(default_factory=dict)
    _digests: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ rpc

    def _rpc(self, method: str, params: list[Any]) -> Any:
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        try:
            req = urllib.request.Request(
                self.rpc_url, data=request, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read())
        except Exception as exc:  # noqa: BLE001 - surfaced as a reason code
            raise LedgerError("S4C-LEDGER-UNAVAILABLE", f"{method} failed: {exc}", retryable=True) from exc
        if "error" in body:
            raise LedgerError(
                "S4C-LEDGER-SUBMIT-REJECTED",
                f"{method} rejected: {body['error'].get('message', 'unknown')}",
                retryable=False,
            )
        return body["result"]

    # -------------------------------------------------------------- contract

    def submit(self, evidence_id: str, envelope: dict[str, Any]) -> Receipt:
        if evidence_id in self._receipts:
            return self._receipts[evidence_id]
        if not self.contract_address or not self.from_address:
            raise LedgerError(
                "S4C-LEDGER-UNAVAILABLE",
                "S4C_BESU_CONTRACT and S4C_BESU_FROM must be configured",
                retryable=False,
            )

        evidence_key = _bytes32(evidence_id)
        digest_word = envelope["digestValue"]
        data = ANCHOR_SELECTOR + evidence_key + digest_word

        try:
            tx_hash = self._rpc(
                "eth_sendTransaction",
                [{"from": self.from_address, "to": self.contract_address, "data": data}],
            )
        except LedgerError as exc:
            if exc.reason_code == "S4C-LEDGER-UNAVAILABLE":
                # The transaction may already be in flight. Reconciliation by
                # evidence identifier must run before any resubmission.
                raise LedgerError(
                    "S4C-LEDGER-TIMEOUT-AFTER-BROADCAST",
                    "submission outcome unknown; reconcile by evidence identifier",
                    retryable=True,
                ) from exc
            raise

        receipt = Receipt(
            evidence_id=evidence_id,
            transaction_ref=tx_hash,
            network_id=self.network_id,
            state="submitted",
        )
        self._receipts[evidence_id] = receipt
        self._digests[evidence_id] = digest_word
        return receipt

    def status(self, evidence_id: str) -> Receipt | None:
        receipt = self._receipts.get(evidence_id)
        if receipt is None or receipt.state == "confirmed":
            return receipt
        result = self._rpc("eth_getTransactionReceipt", [receipt.transaction_ref])
        if not result:
            return receipt
        if result.get("status") != "0x1":
            raise LedgerError("S4C-LEDGER-SUBMIT-REJECTED", "transaction reverted", retryable=False)
        confirmed = Receipt(
            evidence_id=receipt.evidence_id,
            transaction_ref=receipt.transaction_ref,
            network_id=receipt.network_id,
            state="confirmed",
            block_ref=result.get("blockNumber"),
            raw={"gasUsed": result.get("gasUsed")},
        )
        self._receipts[evidence_id] = confirmed
        return confirmed

    def anchored_digest(self, evidence_id: str) -> str | None:
        # The submitted digest is only a local cache; without independent
        # contract readback it cannot support an integrity verdict.
        return None


def _bytes32(value: str) -> str:
    """Pack an evidence identifier into a 32-byte word."""
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
