"""Read-optimised projection for the time-critical sorting path.

The index is generated from the managed passport source and is never an
independent authoritative record. It publishes its own lag rather than
concealing it, so a sorting controller can decide deliberately whether to accept
a projection of that age or pay for a strongly consistent read.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .config import INDEX_STALENESS_LIMIT_MS
from .reasons import DppError
from .store import PassportStore


@dataclass
class _Entry:
    record_version: int
    generated_at_ms: float
    payload: dict[str, Any]


@dataclass
class ReadIndex:
    """A compact operational view keyed by passport identifier."""

    store: PassportStore
    lag_ms: float = 0.0
    _entries: dict[str, _Entry] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def attach(self) -> None:
        """Regenerate the projection whenever the authoritative record changes."""
        self.store.on_commit = self._on_commit
        for record in self.store:
            self._project(record)

    def _on_commit(self, dpp_id: str, _version: int) -> None:
        self._project(self.store._records[dpp_id])  # noqa: SLF001 - same module boundary

    def _project(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._entries[record["dppId"]] = _Entry(
                record_version=record["recordVersion"],
                generated_at_ms=time.monotonic() * 1000.0,
                payload=sorting_view(record),
            )

    def sorting_view(self, dpp_id: str, *, strong: bool = False) -> dict[str, Any]:
        """Return the sorting projection with its measured lag.

        ``strong`` bypasses the projection and reads the authoritative record,
        which costs the latency of the authoritative path. An entry older than
        the configured limit is refused rather than served silently, because a
        stale routing decision cannot be detected downstream.
        """
        if strong:
            view = sorting_view(self.store.get(dpp_id))
            view["indexLagMs"] = 0
            view["consistency"] = "strong"
            return view

        with self._lock:
            entry = self._entries.get(dpp_id)
        if entry is None:
            return self.sorting_view(dpp_id, strong=True)

        age_ms = (time.monotonic() * 1000.0) - entry.generated_at_ms + self.lag_ms
        if age_ms > INDEX_STALENESS_LIMIT_MS:
            raise DppError(
                "S4C-DEP-UNAVAILABLE",
                f"projection is {age_ms:.0f} ms old, beyond the {INDEX_STALENESS_LIMIT_MS} ms limit",
                extra={"indexLagMs": round(age_ms)},
            )
        view = dict(entry.payload)
        view["indexLagMs"] = round(age_ms)
        view["consistency"] = "projected"
        return view

    def __len__(self) -> int:
        return len(self._entries)


def sorting_view(record: dict[str, Any]) -> dict[str, Any]:
    """Return the minimum information a sorting decision consumes."""
    product = record.get("product", {})
    prior = record.get("sortingDecisions") or []
    return {
        "dppId": record["dppId"],
        "recordVersion": record["recordVersion"],
        "generatedAt": record["updatedAt"],
        "product": {
            key: product[key]
            for key in ("articleClass", "fabricConstruction", "colourPrimary", "condition", "technicalFlags")
            if key in product
        },
        "materialSummary": [
            {
                key: observation[key]
                for key in (
                    "observationId",
                    "fibreType",
                    "percentage",
                    "percentageBasis",
                    "valueStatus",
                    "method",
                    "confidence",
                )
                if key in observation
            }
            for observation in record.get("materialObservations", [])
        ],
        "priorDecision": prior[-1] if prior else None,
    }
