"""Controlled-vocabulary loading and validation.

Vocabulary membership is checked separately from JSON Schema validation. A token
that is structurally a string but absent from the declared vocabulary version is
rejected with ``S4C-PAYLOAD-VOCAB-INVALID`` and never coerced to a default. That
separation is deliberate: schema validation answers whether the payload has the
right shape, vocabulary validation answers whether the values mean anything.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache, lru_cache
from typing import Any

from .config import VOCAB_DIR
from .reasons import DppError


@dataclass(frozen=True)
class Vocabulary:
    name: str
    version: str
    tokens: frozenset[str]
    deprecated: frozenset[str]
    replacements: dict[str, str | None]

    def validate(self, token: str, path: str) -> None:
        if token not in self.tokens:
            raise DppError(
                "S4C-PAYLOAD-VOCAB-INVALID",
                f"{token!r} is not in vocabulary {self.name} version {self.version}",
                fields=[path],
                extra={"vocabulary": self.name, "vocabularyVersion": self.version},
            )


@cache
def load(name: str) -> Vocabulary:
    path = VOCAB_DIR.joinpath(f"{name}.json")
    if not path.exists():
        raise KeyError(f"vocabulary {name!r} is not published")
    doc = json.loads(path.read_text(encoding="utf-8"))
    terms = doc["terms"]
    return Vocabulary(
        name=doc["name"],
        version=doc["version"],
        tokens=frozenset(term["token"] for term in terms),
        deprecated=frozenset(term["token"] for term in terms if term.get("deprecated")),
        replacements={term["token"]: term.get("replacedBy") for term in terms},
    )


@lru_cache(maxsize=1)
def published() -> tuple[str, ...]:
    return tuple(sorted(p.name.removesuffix(".json") for p in VOCAB_DIR.iterdir() if p.name.endswith(".json")))


#: Field path to vocabulary name. Every coded field in the profile appears here;
#: a coded field absent from this table would be accepted unchecked, so the
#: conformance suite asserts the table covers the schema.
FIELD_VOCABULARIES: dict[str, str] = {
    "status": "passport-status",
    "identity.granularity": "",  # constrained by the schema enum, not a vocabulary
    "product.articleClass": "article-class",
    "product.fabricConstruction": "fabric-construction",
    "product.colourPrimary": "colour-family",
    "product.condition": "condition",
    "product.technicalFlags[]": "technical-flag",
    "materialObservations[].fibreType": "fibre-type",
    "materialObservations[].method": "method",
    "materialObservations[].valueStatus": "value-status",
    "materialObservations[].percentageBasis": "percentage-basis",
    "materialObservations[].confidence.scale": "confidence-scale",
    "components[].componentType": "component-type",
    "lifecycleEvents[].eventType": "event-type",
    "sortingDecisions[].sortingCategory": "sorting-category",
    "carriers[].carrierType": "carrier-type",
    "carriers[].encodingScheme": "encoding-scheme",
    "carriers[].bindingStatus": "binding-status",
    "integrity[].evidenceState": "evidence-state",
}


def _check(container: dict[str, Any], key: str, vocabulary: str, path: str) -> None:
    value = container.get(key)
    if value is None:
        return
    load(vocabulary).validate(value, path)


def validate_record(record: dict[str, Any]) -> None:
    """Validate every coded value in a passport record.

    Raises the first ``DppError`` encountered. The failing path is reported so
    that the caller can correct the specific member.
    """
    _check(record, "status", "passport-status", "status")

    product = record.get("product") or {}
    _check(product, "articleClass", "article-class", "product.articleClass")
    _check(product, "fabricConstruction", "fabric-construction", "product.fabricConstruction")
    _check(product, "colourPrimary", "colour-family", "product.colourPrimary")
    _check(product, "condition", "condition", "product.condition")
    flags = load("technical-flag")
    for index, flag in enumerate(product.get("technicalFlags") or []):
        flags.validate(flag, f"product.technicalFlags[{index}]")

    for index, observation in enumerate(record.get("materialObservations") or []):
        base = f"materialObservations[{index}]"
        _check(observation, "fibreType", "fibre-type", f"{base}.fibreType")
        _check(observation, "method", "method", f"{base}.method")
        _check(observation, "valueStatus", "value-status", f"{base}.valueStatus")
        _check(observation, "percentageBasis", "percentage-basis", f"{base}.percentageBasis")
        confidence = observation.get("confidence")
        if confidence:
            _check(confidence, "scale", "confidence-scale", f"{base}.confidence.scale")

    for index, component in enumerate(record.get("components") or []):
        _check(component, "componentType", "component-type", f"components[{index}].componentType")

    for index, event in enumerate(record.get("lifecycleEvents") or []):
        _check(event, "eventType", "event-type", f"lifecycleEvents[{index}].eventType")

    for index, decision in enumerate(record.get("sortingDecisions") or []):
        _check(decision, "sortingCategory", "sorting-category", f"sortingDecisions[{index}].sortingCategory")

    for index, carrier in enumerate(record.get("carriers") or []):
        base = f"carriers[{index}]"
        _check(carrier, "carrierType", "carrier-type", f"{base}.carrierType")
        _check(carrier, "encodingScheme", "encoding-scheme", f"{base}.encodingScheme")
        _check(carrier, "bindingStatus", "binding-status", f"{base}.bindingStatus")

    for index, entry in enumerate(record.get("integrity") or []):
        _check(entry, "evidenceState", "evidence-state", f"integrity[{index}].evidenceState")


def evidence_weight(method: str) -> int:
    """Return the declared evidence weight of an observation method.

    Used by consuming rule sets to decide which observation governs when two
    methods disagree. The weight is a property of the method, not of the
    passport, and a rule set is free to apply a different ordering provided the
    ordering is versioned with the rule set.
    """
    doc = json.loads(VOCAB_DIR.joinpath("method.json").read_text(encoding="utf-8"))
    for term in doc["terms"]:
        if term["token"] == method:
            return int(term.get("evidenceWeight", 0))
    raise KeyError(method)
