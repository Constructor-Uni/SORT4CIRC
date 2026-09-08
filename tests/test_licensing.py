"""Regression checks for the owner-approved component licences."""
import json
import tomllib
from pathlib import Path

from tools import gen_openapi

from sort4circ_dpp.api import create_app

ROOT = Path(__file__).resolve().parents[1]
APPROVED_OPENAPI_LICENSE = {
    "name": "Creative Commons Attribution 4.0 International",
    "url": "https://creativecommons.org/licenses/by/4.0/",
}


def test_live_and_checked_in_openapi_use_approved_documentation_licence():
    assert create_app().openapi()["info"]["license"] == APPROVED_OPENAPI_LICENSE
    checked_in = json.loads((ROOT / "spec/openapi/dpp-api-v1.json").read_text())
    assert checked_in["info"]["license"] == APPROVED_OPENAPI_LICENSE


def test_generator_replaces_conflicting_metadata_and_needs_no_previous_contract(tmp_path, monkeypatch):
    target = tmp_path / "spec/openapi/dpp-api-v1.json"
    target.parent.mkdir(parents=True)
    monkeypatch.setattr(gen_openapi, "ROOT", tmp_path)
    target.write_text(json.dumps({"info": {"license": {"name": "Conflicting obsolete declaration"}}}))
    assert gen_openapi.main(["--check"]) == 1
    assert gen_openapi.main([]) == 0
    assert json.loads(target.read_text())["info"]["license"] == APPROVED_OPENAPI_LICENSE
    target.unlink()
    assert gen_openapi.main([]) == 0
    assert gen_openapi.main(["--check"]) == 0


def test_distribution_declares_both_component_licences_and_ships_the_scope_map():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["project"]["license"]["text"] == "MIT AND CC-BY-4.0"
    assert set(config["tool"]["setuptools"]["license-files"]) == {"LICENSE", "LICENSE-DOCS", "LICENSING.md"}
    assert "MIT License" in (ROOT / "LICENSE").read_text()
    assert "CC-BY-4.0" in (ROOT / "LICENSE-DOCS").read_text()
    assert "H07: CLOSED" in (ROOT / "LICENSING.md").read_text()


def test_every_public_file_has_exactly_one_documented_licence_scope():
    import fnmatch

    document = (ROOT / "LICENSING.md").read_text()
    rules = []
    current = None
    for line in document.splitlines():
        if line.startswith("## "):
            current = {"## MIT coverage": "MIT", "## CC BY 4.0 coverage": "CC-BY-4.0"}.get(line)
        if current and line.startswith("| ") and not line.startswith(("| Directory", "| ---")):
            patterns = line.split("|")[1].strip().split(", ")
            rules.extend((pattern, current) for pattern in patterns)
    policy = json.loads((ROOT / "public-release-policy.json").read_text())
    for name in policy["files"]:
        matches = [(pattern, licence) for pattern, licence in rules
                   if fnmatch.fnmatchcase(name, pattern)
                   or fnmatch.fnmatchcase(name, pattern.replace("**/", ""))]
        assert len(matches) == 1, f"public coverage needs review: {name}"
