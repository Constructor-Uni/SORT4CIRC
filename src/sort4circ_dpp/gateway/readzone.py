"""Classify fictional carrier observations, without hardware or control settings."""
from dataclasses import dataclass
from urllib.parse import urlsplit

from ..reasons import safe_action


@dataclass(frozen=True)
class ReadObservation:
    identifier: str | None
    readable: bool = True


@dataclass(frozen=True)
class ReadZoneResult:
    accepted: bool
    identifier: str | None
    reason_code: str | None
    safe_action: str | None

    @property
    def may_resolve(self) -> bool:
        """Whether identifier resolution may be attempted; no physical action."""
        return self.accepted and self.reason_code is None


class CarrierResolver:
    """Separate readable, absent, malformed and ambiguous observations."""

    def evaluate(self, observations: list[ReadObservation]) -> ReadZoneResult:
        if not observations:
            return self._reject("S4C-IDENT-UNKNOWN")
        if len(observations) != 1:
            return self._reject("S4C-IDENT-AMBIGUOUS")
        observation = observations[0]
        if not observation.readable or not isinstance(observation.identifier, str):
            return self._reject("S4C-IDENT-MALFORMED")
        value = observation.identifier
        try:
            scheme = urlsplit(value).scheme
        except ValueError:
            scheme = None
        if not value or not scheme or any(c.isspace() for c in value):
            return self._reject("S4C-IDENT-MALFORMED")
        return ReadZoneResult(True, value, None, None)

    @staticmethod
    def _reject(code: str) -> ReadZoneResult:
        return ReadZoneResult(False, None, code, safe_action(code))
