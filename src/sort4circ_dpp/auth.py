"""Replaceable identity providers for local education."""
from collections.abc import Mapping
from typing import Protocol

from .access import PUBLIC, Principal, known_roles
from .reasons import DppError


class AuthProvider(Protocol):
    def authenticate(self, headers: Mapping[str, str]) -> Principal: ...


class PublicOnlyAuth:
    """No write privileges, regardless of claimed identity."""

    def authenticate(self, headers: Mapping[str, str]) -> Principal:
        if headers.get("x-dpp-role"):
            raise DppError("S4C-AUTH-INVALID-TOKEN", "development identity provider is disabled")
        return PUBLIC


class DemoAuth:
    """Explicitly selected, local-only synthetic identity stand-in.

    This is not credential validation and must never protect a deployed system.
    """

    def authenticate(self, headers: Mapping[str, str]) -> Principal:
        role = headers.get("x-dpp-role")
        if role is None:
            return PUBLIC
        if role not in known_roles():
            raise DppError("S4C-AUTH-INVALID-TOKEN", "unknown example role")
        return Principal(
            subject=headers.get("x-dpp-subject", "synthetic-client"),
            role=role,
            organisation_id=headers.get("x-dpp-organisation"),
        )
