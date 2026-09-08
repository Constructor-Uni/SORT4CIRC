"""Public-profile reason codes and problem details; actions are conceptual only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .config import SPEC_DIR


@dataclass(frozen=True)
class ReasonCode:
    code: str
    http_status: int
    condition: str
    safe_action: str
    type_uri: str


class DppError(Exception):
    """An error carrying a released reason code.

    ``fields`` carries field-level paths for payload failures so that a client
    can correct the request without guessing which member failed.
    """

    def __init__(
        self,
        code: str,
        detail: str | None = None,
        *,
        fields: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.reason = catalogue().get(code)
        if self.reason is None:
            raise KeyError(f"{code} is not a released reason code")
        self.code = code
        self.detail = detail or self.reason.condition
        self.fields = fields or []
        self.extra = extra or {}
        super().__init__(f"{code}: {self.detail}")

    @property
    def http_status(self) -> int:
        return self.reason.http_status

    def problem(self, instance: str, correlation_id: str) -> dict[str, Any]:
        """Return an RFC 9457 problem-details document."""
        body: dict[str, Any] = {
            "type": self.reason.type_uri,
            "title": self.reason.condition,
            "status": self.reason.http_status,
            "detail": self.detail,
            "instance": instance,
            "reasonCode": self.code,
            "safeAction": self.reason.safe_action,
            "correlationId": correlation_id,
        }
        if self.fields:
            body["errors"] = [{"path": path} for path in self.fields]
        body.update(self.extra)
        return body


@lru_cache(maxsize=1)
def _document() -> dict[str, Any]:
    return json.loads((SPEC_DIR / "reason-codes.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def catalogue() -> dict[str, ReasonCode]:
    """Return the released reason codes, keyed by code."""
    return {
        entry["code"]: ReasonCode(
            code=entry["code"],
            http_status=entry["httpStatus"],
            condition=entry["condition"],
            safe_action=entry["safeAction"],
            type_uri=entry["type"],
        )
        for entry in _document()["codes"]
    }


def safe_action(code: str) -> str:
    """Return the public-profile application action for ``code``."""
    return catalogue()[code].safe_action


def safe_action_description(action: str) -> str:
    return _document()["safeActions"][action]


def released_codes() -> list[str]:
    return sorted(catalogue())
