"""Packaging parity and specification-resource resolution tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sort4circ_dpp.access import matrix
from sort4circ_dpp.reasons import released_codes
from sort4circ_dpp.validation import schema
from sort4circ_dpp.vocab import load, published

ROOT = Path(__file__).resolve().parents[1]
AUTHORITATIVE = ROOT / "spec"
PACKAGED = ROOT / "src" / "sort4circ_dpp" / "_spec"


def _runtime_files(root: Path) -> set[Path]:
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_packaged_runtime_resources_match_authoritative_spec():
    expected = {
        Path("access-matrix.json"),
        Path("reason-codes.json"),
        Path("schemas/dpp-1.0.0.schema.json"),
        Path("schemas/dpp-1.0.0.xsd"),
        *(Path("vocabularies") / path.name for path in (AUTHORITATIVE / "vocabularies").glob("*.json")),
    }
    assert _runtime_files(PACKAGED) == expected
    for relative in sorted(expected):
        assert (PACKAGED / relative).read_bytes() == (AUTHORITATIVE / relative).read_bytes(), relative


def test_source_checkout_uses_authoritative_resources():
    from sort4circ_dpp.config import REPO_ROOT, SPEC_DIR

    assert SPEC_DIR == REPO_ROOT / "spec"


def test_runtime_spec_consumers_load_from_source_checkout():
    assert released_codes()
    assert matrix()["roles"]
    assert schema()["$schema"]
    assert "article-class" in published()
    assert load("article-class").validate("upperBodyKnitwear", "product.articleClass") is None


def test_invalid_explicit_spec_override_fails_without_fallback(tmp_path):
    environment = os.environ.copy()
    environment["S4C_SPEC_DIR"] = str(tmp_path / "does-not-exist")
    result = subprocess.run(
        [sys.executable, "-c", "import sort4circ_dpp.config"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "S4C_SPEC_DIR does not name a directory" in result.stderr


@pytest.mark.parametrize("resource", ["access-matrix.json", "reason-codes.json", "schemas/dpp-1.0.0.schema.json", "schemas/dpp-1.0.0.xsd"])
def test_packaged_resource_is_included_in_package_tree(resource):
    assert (PACKAGED / resource).is_file()
