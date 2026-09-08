"""In-memory projection example with optional caller-supplied freshness policy."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .reasons import DppError
from .store import PassportStore


@dataclass
class _Entry:
    record_version: int
    committed_at_ms: float
    generated_at_ms: float
    payload: dict[str, Any]


@dataclass
class ReadIndex:
    """A compact operational view keyed by passport identifier."""

    store: PassportStore
    max_lag_ms: float | None = None
    lag_ms: float = 0.0
    _entries: dict[str, _Entry] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    #: Monotonic milliseconds at which the projector last caught up with the
    #: source. Compared against ``store.last_commit_ms`` to detect a projector
    #: that has stopped while writes continued.
    caught_up_at_ms: float = 0.0

    def attach(self) -> None:
        """Regenerate the projection whenever the authoritative record changes."""
        self.store.on_commit = self._on_commit
        for record in self.store:
            self._project(record, committed_at_ms=self.store.last_commit_ms)
        self.caught_up_at_ms = max(self.caught_up_at_ms, self.store.last_commit_ms)

    def _on_commit(self, dpp_id: str, _version: int) -> None:
        self._project(
            self.store._records[dpp_id],  # noqa: SLF001 - same module boundary
            committed_at_ms=self.store.last_commit_ms,
        )

    def _project(self, record: dict[str, Any], *, committed_at_ms: float) -> None:
        generated_at_ms = time.monotonic() * 1000.0
        with self._lock:
            self._entries[record["dppId"]] = _Entry(
                record_version=record["recordVersion"],
                committed_at_ms=committed_at_ms or generated_at_ms,
                generated_at_ms=generated_at_ms,
                payload=sorting_view(record),
            )
            self.caught_up_at_ms = max(self.caught_up_at_ms, committed_at_ms)

    def backlog_ms(self) -> float:
        """Milliseconds by which the projector trails the source.

        Zero when the projector has processed every commit, whatever the wall
        clock says. This is the quantity the staleness limit bounds.
        """
        return max(0.0, self.store.last_commit_ms - self.caught_up_at_ms)

    def sorting_view(self, dpp_id: str, *, strong: bool = False) -> dict[str, Any]:
        """Return the sorting projection with its measured lag.

        ``strong`` bypasses the projection and reads the authoritative record,
        which costs the latency of the authoritative path.

        The lag reported and bounded here is the interval between the commit
        that produced a value and the regeneration of the projection carrying
        it, plus any backlog the projector is currently carrying. It is not the
        wall-clock age of the projection. The distinction decides how the
        service behaves on a quiet line: a projection generated an hour ago from
        a record that has not changed since is current, not stale, and refusing
        it would stop a sorting line for a condition that is not an error. What
        does warrant refusal is a projector that has fallen behind the source,
        and that condition is visible in ``backlog_ms``.
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

        lag = max(0.0, entry.generated_at_ms - entry.committed_at_ms) + self.backlog_ms() + self.lag_ms
        if self.max_lag_ms is not None and lag > self.max_lag_ms:
            raise DppError(
                "S4C-DEP-UNAVAILABLE",
                f"projection trails the source by {lag:.0f} ms, beyond the "
                f"{self.max_lag_ms} ms limit",
                extra={"indexLagMs": round(lag), "backlogMs": round(self.backlog_ms())},
            )
        view = dict(entry.payload)
        view["indexLagMs"] = round(lag)
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
