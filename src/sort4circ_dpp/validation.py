"""Schema and vocabulary validation, in that order.

Structure is checked first because a vocabulary check on a malformed document
reports the wrong failure. The two checks return distinct reason codes so a
client can tell a shape problem from a meaning problem.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator

from .config import SCHEMA_DIR
from .reasons import DppError
from .vocab import validate_record


@lru_cache(maxsize=1)
def schema() -> dict[str, Any]:
    return json.loads(SCHEMA_DIR.joinpath("dpp-1.0.0.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def validator() -> Draft202012Validator:
    return Draft202012Validator(schema())


def validate_schema(record: dict[str, Any]) -> None:
    errors = sorted(validator().iter_errors(record), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    paths = [
        ".".join(str(part) for part in error.absolute_path) or "<root>"
        for error in errors
    ]
    raise DppError(
        "S4C-PAYLOAD-SCHEMA-INVALID",
        errors[0].message,
        fields=paths,
    )


def validate_payload(record: dict[str, Any]) -> None:
    validate_schema(record)
    validate_record(record)
    check_composition(record)


def observation_sets(record: dict[str, Any]) -> dict[tuple[str, str, str, str], list[dict[str, Any]]]:
    """Group material observations by the measurement occasion that produced them.

    A set is identified by source organisation, source system, method and
    observation time. Two technologies observing the same garment produce two
    sets, and the composition rule applies within a set and never across sets.
    """
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for observation in record.get("materialObservations") or []:
        key = (
            observation.get("sourceOrganisationId", ""),
            observation.get("sourceSystemId", ""),
            observation.get("method", ""),
            observation.get("observedAt", ""),
        )
        groups.setdefault(key, []).append(observation)
    return groups


def check_composition(record: dict[str, Any]) -> None:
    """Apply the profile composition rule, within an observation set.

    Two rules, and the difference between them matters.

    A set of supplied mass fractions may not exceed 100 plus the tolerance.
    Exceeding it means double counting, a wrong basis, or two measurement
    occasions wrongly merged into one, and all three are errors.

    A set summing to less than 100 is accepted. A partial characterisation is a
    normal state: an instrument that identifies the majority fibre and reports
    nothing else has made a true statement about what it found. Requiring the
    sum to reach 100 would force an implementation to fabricate a residual, and
    a fabricated residual is indistinguishable from a measurement afterwards.

    The rule is applied per observation set rather than across the whole array.
    Summing across sets would make a second opinion look like a contradiction:
    a laboratory result of 95 polyester and 5 elastane, plus a later
    near-infrared result of 93.4 polyester, sums to 193.4 and is entirely
    correct. Retaining both is the point of the append-only model.
    """
    for key, observations in observation_sets(record).items():
        supplied = [
            o
            for o in observations
            if o.get("valueStatus") == "supplied" and o.get("percentageBasis") == "mass"
        ]
        if not supplied:
            continue
        total = sum(float(o.get("percentage", 0)) for o in supplied)
        if total > 100.0 + COMPOSITION_TOLERANCE:
            raise DppError(
                "S4C-PAYLOAD-SCHEMA-INVALID",
                f"supplied mass fractions in observation set {key[2]}@{key[3]} sum to "
                f"{total:g}, above 100 plus the {COMPOSITION_TOLERANCE:g} tolerance",
                fields=["materialObservations"],
            )


#: Percentage points by which a set of supplied mass fractions may exceed 100.
#: Recorded in the profile configuration, not hard-coded policy.
COMPOSITION_TOLERANCE = 0.5
