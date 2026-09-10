"""Regression checks for the two-component licence split: Apache-2.0 software, CC BY 4.0 docs/spec."""
import json
import tomllib
from pathlib import Path

from tools import gen_openapi

from sort4circ_dpp.api import create_app

ROOT = Path(__file__).resolve().parents[1]
SPEC_LICENSE = {
    "name": "Creative Commons Attribution 4.0 International",
    "url": "https://creativecommons.org/licenses/by/4.0/",
}


def test_live_and_checked_in_openapi_use_the_specification_licence():
    assert create_app().openapi()["info"]["license"] == SPEC_LICENSE
    checked_in = json.loads((ROOT / "spec/openapi/dpp-api-v1.json").read_text())
    assert checked_in["info"]["license"] == SPEC_LICENSE


def test_generator_replaces_conflicting_metadata_and_needs_no_previous_contract(tmp_path, monkeypatch):
    target = tmp_path / "spec/openapi/dpp-api-v1.json"
    target.parent.mkdir(parents=True)
    monkeypatch.setattr(gen_openapi, "ROOT", tmp_path)
    target.write_text(json.dumps({"info": {"license": {"name": "Conflicting obsolete declaration"}}}))
    assert gen_openapi.main(["--check"]) == 1
    assert gen_openapi.main([]) == 0
    assert json.loads(target.read_text())["info"]["license"] == SPEC_LICENSE
    target.unlink()
    assert gen_openapi.main([]) == 0
    assert gen_openapi.main(["--check"]) == 0


def test_distribution_declares_both_component_licences_and_ships_the_scope_map():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["project"]["license"]["text"] == "Apache-2.0 AND CC-BY-4.0"
    assert "Apache Software License" in config["project"]["classifiers"][2]
    assert set(config["tool"]["setuptools"]["license-files"]) == {"LICENSE", "LICENSE-DOCS", "LICENSING.md"}
    assert "Apache License" in (ROOT / "LICENSE").read_text()
    assert "MIT" not in (ROOT / "LICENSE").read_text(), "the unrecorded MIT change must stay reverted"
    assert "CC-BY-4.0" in (ROOT / "LICENSE-DOCS").read_text()


def test_every_public_file_has_exactly_one_documented_licence_scope():
    import fnmatch

    scopes = {
        "## Apache-2.0 coverage": "Apache-2.0",
        "## CC BY 4.0 coverage": "CC-BY-4.0",
        "## Reserved-rights material": "reserved",
    }
    document = (ROOT / "LICENSING.md").read_text()
    rules = []
    current = None
    for line in document.splitlines():
        if line.startswith("## "):
            current = scopes.get(line)
        if current and line.startswith("| ") and not line.startswith(("| Directory", "| ---")):
            patterns = line.split("|")[1].strip().split(", ")
            rules.extend((pattern, current) for pattern in patterns)
    policy = json.loads((ROOT / "public-release-policy.json").read_text())
    for name in policy["files"]:
        matches = [(pattern, licence) for pattern, licence in rules
                   if fnmatch.fnmatchcase(name, pattern)
                   or fnmatch.fnmatchcase(name, pattern.replace("**/", ""))]
        # A row naming one exact path overrides the directory patterns that also cover it, so
        # reserved-rights material keeps its own terms rather than inheriting the grant of the
        # directory it sits in. Everything else must match exactly one scope and no more.
        named = [match for match in matches if "*" not in match[0]]
        assert len(named or matches) == 1, f"public coverage needs review: {name}"


def test_the_eu_emblem_is_not_claimed_under_either_component_grant():
    """The emblem is EU-owned; neither Apache-2.0 nor CC BY 4.0 may be asserted over it."""
    emblem = ROOT / "docs/assets/eu-emblem.svg"
    assert emblem.exists(), "the funding acknowledgement requires the emblem file"
    coverage = (ROOT / "LICENSING.md").read_text()
    row = next(line for line in coverage.splitlines() if line.startswith("| docs/assets/eu-emblem.svg |"))
    assert "Emblem of the European Union" in row
    assert "**not** by this repository's Apache-2.0 or CC BY 4.0 grants" in row
    assert "docs/assets/eu-emblem.svg" in json.loads((ROOT / "public-release-policy.json").read_text())["files"]
