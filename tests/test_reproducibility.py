from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "evidence/environment/reproducibility-profile-1.0.0.json"


def profile():
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def test_evidence_requirements_are_exact_and_profiled():
    lines = [
        line.strip()
        for line in (ROOT / "requirements-evidence.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines
    assert all("==" in line.split(";", 1)[0] for line in lines)
    assert all(not re.search(r"(?<![=])(?:>=|<=|~=|!=|>|<)", line.split(";", 1)[0]) for line in lines)
    document = profile()
    assert document["profileVersion"] == "1.0.0"
    assert document["pythonEvidenceRuntime"]["version"] == "3.12.3"
    assert document["pythonEvidenceRuntime"]["constraints"] == "requirements-evidence.txt"


def test_container_references_are_fixed_tags_and_immutable_digests():
    document = profile()
    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    compose = yaml.safe_load((ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8"))
    for image in document["containerImages"].values():
        assert image["platform"] == "linux/amd64"
        for field in ("indexDigest", "platformManifestDigest", "imageConfigurationDigest"):
            assert re.fullmatch(r"sha256:[0-9a-f]{64}", image[field])
        assert image["indexDigest"] != image["platformManifestDigest"]
        assert image["tag"] not in {"latest", "stable"}
    application = document["containerImages"]["applicationBase"]
    expected_from = f"FROM python:{application['tag']}@{application['platformManifestDigest']}"
    assert dockerfile.count(expected_from) == 2
    assert compose["services"]["dpp"]["platform"] == "linux/amd64"
    besu = document["containerImages"]["besu"]
    assert compose["services"]["besu"]["image"] == (
        f"hyperledger/besu:{besu['tag']}@{besu['platformManifestDigest']}"
    )
    assert compose["services"]["besu"]["platform"] == "linux/amd64"


def test_host_development_and_linux_evidence_environments_are_distinct():
    document = profile()
    assert document["pythonEvidenceRuntime"]["platform"] == "linux/amd64"
    assert document["hostDevelopmentEnvironment"]["mustMatchPythonEvidenceRuntime"] is False
    assert "not part" in document["hostDevelopmentEnvironment"]["scope"]


def test_ci_actions_are_pinned_to_recorded_commit_shas():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    document = profile()
    assert not re.search(r"uses:\s+[^\s]+@v\d+\b", workflow)
    for action, commit in document["ciActions"].items():
        name = action.split("@", 1)[0]
        assert re.fullmatch(r"[0-9a-f]{40}", commit)
        assert f"uses: {name}@{commit}" in workflow
    assert 'python-version: "3.12.3"' in workflow


def test_docker_build_uses_constraints_without_build_isolation():
    dockerfile = (ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    assert "requirements-evidence.txt" in dockerfile
    assert "--no-build-isolation" in dockerfile
    assert "--constraint=requirements-evidence.txt" in dockerfile
