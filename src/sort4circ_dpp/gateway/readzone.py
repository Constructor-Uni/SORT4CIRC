"""Read-zone controls applied before any sorting command is issued.

The controls run at the edge, before the passport service is called. Two tags in
the zone means the system does not know which garment is in front of the
actuator; calling the service first and deciding afterwards would consume the
latency budget to reach a conclusion that was already available locally.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import READ_SUPPRESSION_WINDOW_MS
from ..reasons import diverts, safe_action

#: EPC URN form accepted by the reference profile. A carrier value that does not
#: match is malformed and is rejected without a service call.
EPC_PATTERN = re.compile(r"^urn:epc:id:sgtin:\d{6,12}\.\d{1,12}\.\d{1,20}$")

#: Received signal strength below which a read is treated as unreliable.
WEAK_SIGNAL_DBM = -70


@dataclass(frozen=True)
class ReadZoneResult:
    """The outcome of applying the controls to one read window."""

    accepted: bool
    epc: str | None
    reason_code: str | None
    safe_action: str | None

    @property
    def may_command(self) -> bool:
        """True only when a category-specific actuator command is permitted."""
        return self.accepted and self.reason_code is None


@dataclass
class ReadZone:
    """Applies duplicate suppression, ambiguity and signal controls."""

    suppression_window_ms: int = READ_SUPPRESSION_WINDOW_MS
    weak_signal_dbm: int = WEAK_SIGNAL_DBM
    _last_seen: dict[str, float] = field(default_factory=dict)
    _clock: Any = time.monotonic

    def evaluate(self, reads: list[dict[str, Any]]) -> ReadZoneResult:
        """Evaluate the tags observed within one read window.

        ``reads`` carries one entry per tag detected in the window, each with an
        ``epc`` and optionally an ``rssiDbm``.
        """
        if not reads:
            return self._reject("S4C-IDENT-UNKNOWN", None)

        if len(reads) > 1:
            # Not a transient fault. Retrying resolves nothing and consumes the
            # remaining budget; the only correct outcome is diversion.
            return self._reject("S4C-IDENT-AMBIGUOUS", None)

        read = reads[0]
        epc = read.get("epc")
        if not isinstance(epc, str) or not EPC_PATTERN.match(epc):
            return self._reject("S4C-IDENT-MALFORMED", epc if isinstance(epc, str) else None)

        rssi = read.get("rssiDbm")
        if rssi is not None and rssi < self.weak_signal_dbm:
            return self._reject("S4C-READ-WEAK-SIGNAL", epc)

        now_ms = self._clock() * 1000.0
        previous = self._last_seen.get(epc)
        if previous is not None and (now_ms - previous) < self.suppression_window_ms:
            # A suppressed repeat is not an error and produces no new command.
            return ReadZoneResult(False, epc, "S4C-READ-SUPPRESSED-DUPLICATE",
                                  safe_action("S4C-READ-SUPPRESSED-DUPLICATE"))
        self._last_seen[epc] = now_ms
        return ReadZoneResult(True, epc, None, None)

    @staticmethod
    def _reject(code: str, epc: str | None) -> ReadZoneResult:
        return ReadZoneResult(False, epc, code, safe_action(code))

    @staticmethod
    def diverts(code: str) -> bool:
        return diverts(code)
