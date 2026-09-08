"""Deterministic serialisation and integrity projection for the public profile.

Supported values are intentionally restricted; a vector is an example, not
comprehensive proof of a standard or deployed-system correctness."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from collections.abc import Iterable
from typing import Any

CANONICALISATION_PROFILE = "rfc8785"
DIGEST_ALGORITHM = "sha-256"

#: Fields covered by this public profile.
#: Fields carrying access decisions, view artefacts and the integrity array are
#: excluded, because including them would make the digest depend on the identity
#: of the requester.
PROJECTION_TOP_LEVEL: tuple[str, ...] = ("dppId", "recordVersion", "updatedAt")
PROJECTION_IDENTITY: tuple[str, ...] = ("granularity", "itemId", "epc")
PROJECTION_PRODUCT: tuple[str, ...] = ("articleClass", "fabricConstruction", "technicalFlags")
PROJECTION_OBSERVATION: tuple[str, ...] = (
    "observationId",
    "fibreType",
    "percentage",
    "percentageBasis",
    "valueStatus",
    "method",
    "sourceOrganisationId",
    "observedAt",
)


class CanonicalisationError(ValueError):
    """Raised when a value cannot be serialised deterministically."""


def _number(value: int | float) -> str:
    """Serialise a number the way ECMAScript ``Number.prototype.toString`` does.

    RFC 8785 defers to the ECMAScript algorithm. For integers and for decimals
    with a short round-trip representation, which is the whole of the public
    profile, Python's shortest round-trip float repr agrees with it. Values
    outside that range are rejected rather than silently serialised in a form
    another implementation would not reproduce.
    """
    if isinstance(value, bool):  # bool is a subclass of int; guard first
        raise CanonicalisationError("boolean passed to number serialiser")
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        raise CanonicalisationError(f"non-finite number cannot be canonicalised: {value!r}")
    if value == int(value) and abs(value) < 1e21:
        return str(int(value))
    text = repr(value)
    if "e" in text or "E" in text:
        raise CanonicalisationError(
            f"number {value!r} requires exponential notation; the profile restricts "
            "quantities to values with a plain decimal representation"
        )
    return text


def _string(value: str) -> str:
    # json.dumps with ensure_ascii=False applies exactly the escape set that
    # RFC 8785 inherits from ECMAScript JSON.stringify.
    return json.dumps(value, ensure_ascii=False)


def canonicalise(value: Any) -> str:
    """Return the RFC 8785 canonical JSON text for ``value``."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonicalise(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalisationError(f"object key must be a string, got {type(key).__name__}")
        # RFC 8785 sorts by UTF-16 code units. Python sorts str by code point.
        # The two orders differ only where a supplementary-plane character is
        # compared against a code point in U+E000..U+FFFF, so encode explicitly
        # rather than relying on the default comparison.
        items = sorted(value.items(), key=lambda kv: kv[0].encode("utf-16-be"))
        return "{" + ",".join(f"{_string(k)}:{canonicalise(v)}" for k, v in items) + "}"
    raise CanonicalisationError(f"type {type(value).__name__} is not serialisable")


def _pick(source: dict[str, Any] | None, keys: Iterable[str]) -> dict[str, Any]:
    if not source:
        return {}
    return {key: source[key] for key in keys if key in source and source[key] is not None}


def integrity_projection(record: dict[str, Any]) -> dict[str, Any]:
    """Return the explicit field subset of ``record`` that the digest covers."""
    projection: dict[str, Any] = _pick(record, PROJECTION_TOP_LEVEL)

    identity = _pick(record.get("identity"), PROJECTION_IDENTITY)
    if identity:
        projection["identity"] = identity

    product = _pick(record.get("product"), PROJECTION_PRODUCT)
    if product:
        projection["product"] = product

    observations = record.get("materialObservations") or []
    if observations:
        projection["materialObservations"] = [
            _pick(observation, PROJECTION_OBSERVATION) for observation in observations
        ]

    return projection


def canonical_bytes(record: dict[str, Any]) -> bytes:
    """Return the canonical byte sequence digested for ``record``."""
    return canonicalise(integrity_projection(record)).encode("utf-8")


def digest(record: dict[str, Any]) -> str:
    """Return the lower-case hexadecimal SHA-256 digest of the projection."""
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def verify_digest(record: dict[str, Any], expected: str) -> bool:
    """Return True when ``record`` reproduces ``expected``.

    A mismatch means the stored record changed after anchoring. It does not mean
    the ledger is wrong, and the two conditions are reported separately.
    """
    return hmac.compare_digest(digest(record), expected.lower())
