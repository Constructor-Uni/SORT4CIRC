from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import sort4circ_dpp.execution_evidence as evidence
from sort4circ_dpp.execution_evidence import (
    DirtyWorkingTreeError,
    build_record,
    file_digest,
    sha256_json,
    write_record,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "evidence/schema/execution-evidence-1.0.0.schema.json").read_text(encoding="utf-8"))
RAW = ROOT / "docs/benchmarks/anchor-selftest.json"
RELEASE_DIR = ROOT / "evidence/releases/1.2.0"


def git_state(dirty=False):
    return {
        "repository": "Constructor-Uni/SORT4CIRC",
        "gitCommit": "a" * 40,
        "gitBranch": "main",
        "dirtyWorkingTree": dirty,
    }


def record(monkeypatch, *, dirty=False, release_mode=False, **overrides):
    monkeypatch.setattr(evidence, "git_metadata", lambda root: git_state(dirty))
    arguments = {
        "root": ROOT,
        "control_id": "BC-01",
        "test_name": "local evidence test",
        "command": "python -m pytest tests/test_execution_evidence.py -q",
        "tool": "tests/test_execution_evidence.py",
        "started_at": "2026-09-03T10:00:00.000Z",
        "completed_at": "2026-09-03T10:00:01.250Z",
        "exit_code": 0,
        "configuration_profile": "local-test",
        "configuration": {"workers": 1},
        "dataset": {
            "identifier": "anchor-self-test",
            "version": "1.0.0",
            "sha256": sha256_json({"fixture": "anchor"}),
            "fixtureCount": 1,
            "operationCount": 25,
            "payloadCharacteristics": {"kind": "synthetic reference record"},
        },
        "target": {"maximumFailures": 0},
        "target_unit": "failures",
        "acceptance_rule": "exit code is zero and no verification failures occur",
        "observed_result": {"failures": 0},
        "observed_unit": "failures",
        "raw_result_path": RAW,
        "summary_metrics": {"failures": 0},
        "release_mode": release_mode,
    }
    arguments.update(overrides)
    return build_record(**arguments)


def validate(value):
    errors = list(Draft202012Validator(SCHEMA).iter_errors(value))
    assert not errors, errors


def test_schema_itself_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_generated_record_matches_versioned_schema(monkeypatch):
    value = record(monkeypatch)
    validate(value)
    assert value["time"]["durationSeconds"] == 1.25
    assert value["execution"]["workingDirectory"] == "repositoryRoot"
    assert value["output"]["rawResultSha256"] == file_digest(RAW)
    assert value["artefactVersions"]["mappingPackage"]["version"] == "1.0.0"
    assert value["artefactVersions"]["ontology"]["versionIRI"].endswith("/1.0.0")
    assert value["artefactVersions"]["vocabularyRelease"]["fileCount"] > 0
    assert value["environment"]["containerImages"]["besu"]["tag"] == "26.8.1"


@pytest.mark.parametrize(
    "path",
    [
        ("source", "gitCommit"),
        ("dataset", "sha256"),
        ("configuration", "sha256"),
    ],
)
def test_required_provenance_cannot_be_omitted(monkeypatch, path):
    value = record(monkeypatch)
    del value[path[0]][path[1]]
    with pytest.raises(AssertionError):
        validate(value)


def test_target_cannot_be_substituted_for_observed_result(monkeypatch):
    value = record(monkeypatch)
    value["acceptance"]["observedResultSource"] = "declaredRequirement"
    with pytest.raises(AssertionError):
        validate(value)
    value = record(monkeypatch)
    del value["acceptance"]["observedResult"]
    with pytest.raises(AssertionError):
        validate(value)


def test_invalid_verdict_fails(monkeypatch):
    value = record(monkeypatch)
    value["acceptance"]["verdict"] = "unknown"
    with pytest.raises(AssertionError):
        validate(value)


def test_not_applicable_requires_a_reason(monkeypatch):
    with pytest.raises(ValueError, match="requires a reason"):
        record(monkeypatch, verdict="notApplicable", reason=None)


def test_dirty_worktree_is_explicitly_research_grade(monkeypatch):
    value = record(monkeypatch, dirty=True)
    assert value["acceptance"]["releaseGrade"] is False
    assert value["acceptance"]["evidenceClassification"] == "research"
    assert "dirty" in value["acceptance"]["reason"]


def test_dirty_worktree_blocks_release_mode(monkeypatch):
    with pytest.raises(DirtyWorkingTreeError):
        record(monkeypatch, dirty=True, release_mode=True)


def test_clean_release_mode_is_release_grade(monkeypatch):
    value = record(monkeypatch, release_mode=True)
    assert value["acceptance"]["releaseGrade"] is True
    assert value["acceptance"]["evidenceClassification"] == "release"


def test_sensitive_configuration_is_omitted(monkeypatch):
    value = record(
        monkeypatch,
        configuration={
            "runs": 2,
            "api_token": "do-not-copy",
            "platforms": [
                {
                    "name": "private-ledger",
                    "rpc_url": "http://10.0.0.1:8545",
                    "options": {"private_key": "do-not-copy"},
                }
            ],
        },
    )
    encoded = json.dumps(value).lower()
    assert "do-not-copy" not in encoded
    assert "10.0.0.1" not in encoded
    assert "private_key" not in encoded
    assert "api_token" not in encoded
    assert value["configuration"]["sensitiveParametersOmitted"] is True


def test_nonzero_execution_cannot_pass(monkeypatch):
    with pytest.raises(ValueError, match="non-zero"):
        record(monkeypatch, exit_code=1, verdict="pass")


def test_writer_validates_before_writing(monkeypatch, tmp_path):
    value = record(monkeypatch)
    target = tmp_path / "evidence.json"
    write_record(value, target)
    assert json.loads(target.read_text(encoding="utf-8")) == value
    invalid = copy.deepcopy(value)
    del invalid["configuration"]["sha256"]
    with pytest.raises(ValueError, match="invalid execution evidence"):
        write_record(invalid, target)


def test_package_versions_cover_every_pinned_distribution(monkeypatch):
    value = record(monkeypatch)
    pinned = {
        line.split("==", 1)[0]
        for line in (ROOT / "requirements-evidence.txt").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }
    assert pinned <= set(value["environment"]["packages"])


def test_tracked_release_evidence_is_complete_safe_and_bound_to_one_clean_commit():
    manifest = json.loads((RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sourceCommit"] == "fec8799459f66acd4e679ea5b4d08944281649f2"
    assert manifest["sourceTreeRequiredClean"] is True
    assert manifest["declaredContainerEvidencePlatform"] == "linux/amd64"
    assert manifest["executionHost"]["os"] == "Windows"
    assert manifest["executionHost"]["pythonVersion"] == "3.13.14"
    assert manifest["releaseEvidenceVersion"] == "1.2.0"
    assert len(manifest["records"]) == 5

    expected = {
        "test-suite/evidence.json",
        "fixture-validation/evidence.json",
        "mapping-conformance/evidence.json",
        "loadtest/evidence.json",
        "anchor-selftest/evidence.json",
    }
    assert {entry["record"] for entry in manifest["records"]} == expected
    expected_files = {"manifest.json", *expected}
    expected_files.update(
        Path(entry["rawResult"]["path"])
        .relative_to("evidence/releases/1.2.0")
        .as_posix()
        for entry in manifest["records"]
        if entry["rawResult"]["retention"] == "tracked-release-package"
    )
    actual_files = {
        path.relative_to(RELEASE_DIR).as_posix()
        for path in RELEASE_DIR.rglob("*")
        if path.is_file()
    }
    assert actual_files == expected_files

    for entry in manifest["records"]:
        record_path = RELEASE_DIR / entry["record"]
        record = json.loads(record_path.read_text(encoding="utf-8"))
        validate(record)
        assert file_digest(record_path) == entry["recordSha256"]
        assert record["source"]["gitCommit"] == manifest["sourceCommit"]
        assert record["source"]["dirtyWorkingTree"] is False
        assert record["acceptance"]["releaseGrade"] is True
        assert record["acceptance"]["evidenceClassification"] == "release"
        assert record["output"]["rawResultSha256"] == entry["rawResult"]["sha256"]
        assert record["output"]["rawResultBytes"] == entry["rawResult"]["bytes"]
        raw_result = entry["rawResult"]
        if raw_result["retention"] == "tracked-release-package":
            assert record["output"]["rawResultPath"] == raw_result["path"]
            raw_path = ROOT / raw_result["path"]
            assert raw_path.is_file()
            assert file_digest(raw_path) == raw_result["sha256"]
            assert raw_path.stat().st_size == raw_result["bytes"]
            assert raw_path.is_relative_to(RELEASE_DIR)
        else:
            assert raw_result["retention"] == "restrictedEvidenceLocationPending"
            assert "path" not in raw_result
            assert raw_result["reason"]
            assert (
                record["output"]["immutableResultReference"]
                == raw_result["immutableResultReference"]
            )
        encoded = json.dumps(record).lower()
        assert "private_key" not in encoded
        assert "api_token" not in encoded
        assert "password" not in encoded
        assert "http://10." not in encoded


def test_release_anchor_evidence_is_explicitly_an_in_memory_self_test():
    record = json.loads((RELEASE_DIR / "anchor-selftest/evidence.json").read_text(encoding="utf-8"))
    assert record["configuration"]["parameters"]["platforms"][0]["name"] == "in-memory-reference"
    assert "nothing about any distributed ledger" in record["acceptance"]["reason"]
    assert "--self-test" in record["execution"]["command"]


def test_historical_unreachable_load_result_is_preserved_with_its_limitation():
    manifest = json.loads((RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    historical = manifest["historicalEvidencePreserved"]
    assert historical["recordedSourceCommit"] == "d870cc9"
    assert "not reachable" in historical["provenanceLimitation"]
    original = json.loads((ROOT / historical["path"]).read_text(encoding="utf-8"))
    assert original["environment"]["commit"] == "d870cc9"
