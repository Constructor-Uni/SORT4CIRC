"""Repository-wide regression guards for the final D4.3 terminology/profile."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".json", ".md", ".toml", ".yml", ".yaml", ".ttl", ".rq", ".csv", ".xsd", ".xml"}
IGNORED = {".git", ".venv", "build", "__pycache__", ".pytest_cache", ".ruff_cache"}


def repository_text() -> str:
    chunks = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and not IGNORED.intersection(path.parts):
            chunks.append(path.read_text(encoding="utf-8", errors="ignore").lower())
    return "\n".join(chunks)


def test_no_unselected_semantic_serialisation_profile_is_present():
    text = repository_text()
    prohibited = ["sha" + "cl", "json" + "-ld", "ld" + "+json", "@con" + "text"]
    assert not [token for token in prohibited if token in text]


def test_superseded_exchange_names_and_tokens_do_not_reappear():
    text = repository_text()
    superseded = [
        "upper_body_" + "knitwear", "upper_body" + "knit", "labquantitative" + "iso-1833",
        "percentage_" + "base", "value" + "state", "materialobservation" + "id",
    ]
    assert not [token for token in superseded if token in text]


def test_public_docs_keep_selection_validation_and_kpis_pending():
    text = (ROOT / "README.md").read_text(encoding="utf-8") + (ROOT / "docs" / "governance.md").read_text(encoding="utf-8")
    flattened = " ".join(text.lower().split())
    assert "not the outcome of the assessment" in flattened
    assert "full en 18223 conformity" in flattened and "not claimed" in flattened
    assert "architectureandmigrationplanningonly" not in flattened  # prose must explain the state, not masquerade as a record
