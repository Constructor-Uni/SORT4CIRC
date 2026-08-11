"""Role, scope and view enforcement.

Access is default deny. Holding a scope is necessary and never sufficient: the
matrix additionally determines which view the caller receives, and a caller
entitled to a narrower view receives that narrower view instead of an error, so
a partner integration does not break when the policy tightens.

Where a role may know that a field exists but not read the value, the field is
returned with ``valueStatus`` withheld. Omitting it silently would let a
consumer conclude the data was never collected, which is a different and false
statement.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .config import ACCESS_POLICY_VERSION, SPEC_DIR
from .reasons import DppError


@dataclass(frozen=True)
class Principal:
    """An authenticated caller.

    ``organisation_id`` scopes the partner view: a partner sees the lifecycle
    events in which the same organisation participated and no others.
    """

    subject: str
    role: str
    organisation_id: str | None = None

    @property
    def scopes(self) -> frozenset[str]:
        return frozenset(matrix()["roles"][self.role]["scopes"])

    @property
    def default_view(self) -> str:
        return matrix()["roles"][self.role]["defaultView"]


PUBLIC = Principal(subject="anonymous", role="public")

#: Views ordered from narrowest to widest. A caller requesting a view wider than
#: the default receives the default instead of an error.
VIEW_RANK = {
    "integrityOnly": 0,
    "public": 1,
    "partner": 2,
    "sorting": 3,
    "recycler": 4,
    "authority": 5,
    "full": 6,
}


@lru_cache(maxsize=1)
def matrix() -> dict[str, Any]:
    return json.loads((SPEC_DIR / "access-matrix.json").read_text(encoding="utf-8"))


def known_roles() -> list[str]:
    return sorted(matrix()["roles"])


def require_scope(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise DppError(
            "S4C-AUTHZ-OPERATION-FORBIDDEN",
            f"role {principal.role!r} does not hold scope {scope!r}",
        )


def resolve_view(principal: Principal, requested: str | None) -> str:
    """Return the view the caller actually receives."""
    default = principal.default_view
    if requested is None:
        return default
    if requested not in VIEW_RANK:
        raise DppError("S4C-AUTHZ-VIEW-FORBIDDEN", f"unknown view {requested!r}")
    if principal.role == "integrityVerifier" and requested != "integrityOnly":
        raise DppError("S4C-AUTHZ-VIEW-FORBIDDEN", "this role receives the integrity view only")
    if VIEW_RANK[requested] > VIEW_RANK[default]:
        # Narrow rather than refuse. A tightening policy must not break a
        # working integration; it must return less.
        return default
    return requested


_PUBLIC_PRODUCT = ("articleClass", "fabricConstruction", "technicalFlags")
_SORTING_PRODUCT = _PUBLIC_PRODUCT + ("colourPrimary", "condition", "mass")
_WITHHELD_MARKER = {"valueStatus": "withheld"}


def _observation_for(view: str, observation: dict[str, Any]) -> dict[str, Any]:
    keep = ["observationId", "fibreType", "valueStatus", "method", "observedAt"]
    if view in ("sorting", "recycler", "authority", "full"):
        keep += ["percentage", "percentageBasis", "confidence", "sourceOrganisationId", "sourceSystemId", "evidenceRef"]
    else:
        # The public view states the composition but not who measured it, and
        # marks the withheld members explicitly rather than dropping them.
        keep += ["percentage", "percentageBasis"]
    projected = {key: observation[key] for key in keep if key in observation}
    if view == "public":
        projected["sourceOrganisationId"] = _WITHHELD_MARKER["valueStatus"]
        projected["sourceOrganisationStatus"] = "withheld"
        projected.pop("sourceOrganisationId", None)
    return projected


def project(record: dict[str, Any], view: str, principal: Principal) -> dict[str, Any]:
    """Return the caller's view of ``record``.

    The projection never mutates the stored record and always carries the
    ``recordVersion`` it was produced from, so a decision taken on a view can be
    replayed later against the exact content that produced it.
    """
    if view == "full":
        return copy.deepcopy(record)

    out: dict[str, Any] = {
        "dppId": record["dppId"],
        "schemaVersion": record["schemaVersion"],
        "recordVersion": record["recordVersion"],
        "accessPolicyVersion": record.get("accessPolicyVersion", ACCESS_POLICY_VERSION),
        "view": view,
    }

    if view == "integrityOnly":
        out["integrity"] = copy.deepcopy(record.get("integrity", []))
        return out

    out["status"] = record["status"]
    identity = record.get("identity", {})
    out["identity"] = {"granularity": identity.get("granularity")}
    product = record.get("product", {})
    fields = _PUBLIC_PRODUCT if view == "public" else _SORTING_PRODUCT
    out["product"] = {key: product[key] for key in fields if key in product}
    out["materialObservations"] = [
        _observation_for(view, observation) for observation in record.get("materialObservations", [])
    ]

    if view == "partner":
        if principal.organisation_id is None:
            out["lifecycleEvents"] = []
        else:
            out["lifecycleEvents"] = [
                copy.deepcopy(event)
                for event in record.get("lifecycleEvents", [])
                if event.get("actorOrganisationId") == principal.organisation_id
            ]
        for key in ("modelId", "batchId"):
            if key in identity:
                out["identity"][key] = identity[key]

    if view in ("sorting", "recycler", "authority"):
        for key in ("itemId", "epc"):
            if key in identity:
                out["identity"][key] = identity[key]
        out["sortingDecisions"] = copy.deepcopy(record.get("sortingDecisions", []))
        out["carriers"] = [
            copy.deepcopy(carrier)
            for carrier in record.get("carriers", [])
            if carrier.get("bindingStatus") == "commissioned"
        ]

    if view in ("recycler", "authority"):
        out["components"] = copy.deepcopy(record.get("components", []))

    if view == "authority":
        out["lifecycleEvents"] = copy.deepcopy(record.get("lifecycleEvents", []))
        out["integrity"] = copy.deepcopy(record.get("integrity", []))
        out["identity"] = copy.deepcopy(identity)
        out["environmentalValues"] = copy.deepcopy(record.get("environmentalValues", []))

    return out


#: Members a non-administrative caller may modify through PATCH. Any other path
#: is refused by name, so the caller learns which member was rejected.
WRITABLE_PATHS = {
    "brand": {"product", "identity.sourceRecordId", "registryIdentifier", "environmentalValues"},
    "administrator": {"*"},
}


def check_patch_paths(principal: Principal, patch: dict[str, Any]) -> None:
    allowed = WRITABLE_PATHS.get(principal.role, set())
    if "*" in allowed:
        return
    if not allowed:
        raise DppError("S4C-AUTHZ-OPERATION-FORBIDDEN", f"role {principal.role!r} may not update a passport")
    for key in patch:
        if key in ("materialObservations", "lifecycleEvents", "integrity", "sortingDecisions"):
            raise DppError(
                "S4C-STATE-APPEND-ONLY-VIOLATION",
                f"{key} is append only and cannot be modified through PATCH",
                fields=[key],
            )
        if key not in {path.split(".")[0] for path in allowed}:
            raise DppError(
                "S4C-AUTHZ-OPERATION-FORBIDDEN",
                f"role {principal.role!r} may not write {key!r}",
                fields=[key],
            )
