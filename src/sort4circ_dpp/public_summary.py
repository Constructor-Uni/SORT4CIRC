"""Strict public summaries; never a pipeline for publishing raw execution evidence."""
from dataclasses import dataclass

TEST_CATEGORIES = {
    "schema": "validation", "canonical": "integrity", "integrity": "integrity",
    "identifier": "identifiers", "api": "exchange", "mapping": "interoperability",
    "publication": "publication",
}
STATUSES = frozenset({"pass", "fail", "not-applicable"})
LIMITATIONS = "Synthetic public-profile checks only; no deployment or legal conformity assessment."


@dataclass(frozen=True)
class PublicConformanceSummary:
    results: tuple[tuple[str, str], ...]

    def __post_init__(self):
        if type(self.results) is not tuple or any(
            type(entry) is not tuple or len(entry) != 2
            or any(type(value) is not str for value in entry) for entry in self.results
        ):
            raise ValueError("invalid public result structure")
        identifiers = [name for name, _ in self.results]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate public test identifier")
        if not self.results or any(name not in TEST_CATEGORIES or status not in STATUSES for name, status in self.results):
            raise ValueError("invalid public test result")

    @classmethod
    def from_private_results(cls, raw: dict) -> "PublicConformanceSummary":
        """Select fixed identifiers/statuses only; never copy arbitrary fields."""
        if not isinstance(raw, dict) or not isinstance(raw.get("results"), dict):
            raise ValueError("public test results required")
        results = raw["results"]
        selected = tuple(sorted((name, results[name]) for name in TEST_CATEGORIES if name in results))
        if any(not isinstance(status, str) for _, status in selected):
            raise ValueError("invalid public test status")
        return cls(selected)

    def document(self) -> dict:
        return {
            "publicProfileVersion": "2.0.0",
            "specificationVersion": "2.0.0",
            "publicImplementationVersion": "2.0.0",
            "syntheticDataset": "synthetic-public-fixtures",
            "results": [
                {"testIdentifier": name, "category": TEST_CATEGORIES[name], "status": status}
                for name, status in self.results
            ],
            "limitations": LIMITATIONS,
        }
