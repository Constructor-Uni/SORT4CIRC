"""Versioned, machine-readable provenance envelopes for new executions."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import uuid
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

EVIDENCE_RECORD_VERSION = "1.0.0"
CANONICAL_JSON_PROFILE = "json-sorted-keys-utf8-1.0.0"
SENSITIVE_KEY_PARTS = {
    "address",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "host",
    "options",
    "password",
    "privatekey",
    "rpcurl",
    "secret",
    "token",
}


class DirtyWorkingTreeError(RuntimeError):
    """Raised when release evidence is requested from a dirty checkout."""


def utcnow() -> str:
    from datetime import UTC

    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def file_digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def files_digest(root: Path, paths: list[Path]) -> str:
    """Hash sorted relative names and file bytes, excluding filesystem metadata."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(root: Path, *arguments: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *arguments],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_metadata(root: Path) -> dict[str, Any]:
    commit = _git(root, "rev-parse", "HEAD")
    if not commit:
        raise RuntimeError("a Git commit is required for execution evidence")
    status = _git(root, "status", "--porcelain", "--untracked-files=normal")
    return {
        "repository": "Constructor-Uni/SORT4CIRC",
        "gitCommit": commit,
        "gitBranch": _git(root, "branch", "--show-current") or None,
        "dirtyWorkingTree": bool(status),
    }


def _constraint_names(root: Path) -> list[str]:
    names = ["sort4circ-dpp"]
    path = root / "requirements-evidence.txt"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            name = re.split(r"==|;", stripped, maxsplit=1)[0].strip()
            if name and name not in names:
                names.append(name)
    return names


def package_versions(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in _constraint_names(root):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "notInstalled"
    return dict(sorted(result.items()))


def _memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, OSError, ValueError):
        return None


def _profile(root: Path) -> dict[str, Any]:
    path = root / "evidence/environment/reproducibility-profile-1.0.0.json"
    if not path.is_file():
        return {"profileVersion": "unavailable", "containerImages": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def environment_metadata(root: Path) -> dict[str, Any]:
    profile_document = _profile(root)
    return {
        "pythonImplementation": platform.python_implementation(),
        "pythonVersion": platform.python_version(),
        "os": platform.system(),
        "platform": platform.platform(),
        "architecture": platform.machine() or "notAvailable",
        "cpu": {
            "model": platform.processor() or "notAvailable",
            "logicalCount": os.cpu_count(),
        },
        "memory": {"totalBytes": _memory_bytes()},
        "packages": package_versions(root),
        "containerImages": profile_document.get("containerImages", {}),
        "reproducibilityProfileVersion": profile_document.get("profileVersion", "unavailable"),
    }


def _artefact(path: Path, root: Path, *, version_value: str | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "version": version_value,
        "sha256": file_digest(path),
    }


def artefact_versions(root: Path) -> dict[str, Any]:
    json_schema_path = root / "spec/schemas/dpp-1.0.0.schema.json"
    json_schema = json.loads(json_schema_path.read_text(encoding="utf-8"))
    ontology_path = root / "spec/ontology/sort4circ-1.0.0.ttl"
    ontology_text = ontology_path.read_text(encoding="utf-8")
    version_match = re.search(r"owl:versionIRI\s+<([^>]+)>", ontology_text)
    mapping_path = root / "spec/mappings/dpp-mapping-1.0.0.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    openapi_path = root / "spec/openapi/dpp-api-v1.json"
    openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
    vocab_paths = sorted((root / "spec/vocabularies").glob("*.json"))
    vocabs = [json.loads(path.read_text(encoding="utf-8")) for path in vocab_paths]
    application_version = package_versions(root).get("sort4circ-dpp", "notInstalled")
    return {
        "jsonSchema": _artefact(
            json_schema_path,
            root,
            version_value=json_schema["$id"].rstrip("/").rsplit("/", 1)[-1],
        ),
        "ontology": {
            **_artefact(ontology_path, root, version_value="1.0.0"),
            "versionIRI": version_match.group(1) if version_match else None,
        },
        "mappingPackage": _artefact(
            mapping_path,
            root,
            version_value=mapping["mappingVersion"],
        ),
        "openapi": _artefact(
            openapi_path,
            root,
            version_value=openapi["info"]["version"],
        ),
        "vocabularyRelease": {
            "path": "spec/vocabularies",
            "version": sorted({vocab["version"] for vocab in vocabs}),
            "released": sorted({vocab["released"] for vocab in vocabs}),
            "sha256": files_digest(root, vocab_paths),
            "fileCount": len(vocab_paths),
        },
        "ledgerAdapter": {
            "implementation": "sort4circ-dpp ledger adapter interface",
            "version": application_version,
        },
        "evidenceSerialization": {
            "version": EVIDENCE_RECORD_VERSION,
            "canonicalisation": CANONICAL_JSON_PROFILE,
            "digestAlgorithm": "sha-256",
        },
    }


def _sensitive_key(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def sanitize_parameters(value: Any) -> tuple[Any, bool]:
    """Remove secret-bearing and private-network configuration fields."""
    omitted = False
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, child in value.items():
            if _sensitive_key(str(key)):
                omitted = True
                continue
            cleaned, child_omitted = sanitize_parameters(child)
            clean[str(key)] = cleaned
            omitted = omitted or child_omitted
        return clean, omitted
    if isinstance(value, list):
        clean_list = []
        for child in value:
            cleaned, child_omitted = sanitize_parameters(child)
            clean_list.append(cleaned)
            omitted = omitted or child_omitted
        return clean_list, omitted
    return value, False


def _duration_seconds(started_at: str, completed_at: str) -> float:
    def parse(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    duration = (parse(completed_at) - parse(started_at)).total_seconds()
    if duration < 0:
        raise ValueError("completedAt precedes startedAt")
    return round(duration, 6)


def _safe_raw_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def build_record(
    *,
    root: Path,
    control_id: str,
    test_name: str,
    command: str,
    tool: str,
    started_at: str,
    completed_at: str,
    exit_code: int,
    configuration: dict[str, Any],
    dataset: dict[str, Any],
    target: Any,
    observed_result: Any,
    raw_result_path: Path,
    configuration_profile: str = "local",
    target_unit: str | None = None,
    acceptance_rule: str = "command exits zero",
    observed_unit: str | None = None,
    verdict: str | None = None,
    evidence_type: str = "executedTest",
    reason: str | None = None,
    summary_metrics: dict[str, Any] | None = None,
    release_mode: bool = False,
) -> dict[str, Any]:
    git = git_metadata(root)
    if release_mode and git["dirtyWorkingTree"]:
        raise DirtyWorkingTreeError("release evidence requires a clean working tree")

    clean_configuration, omitted = sanitize_parameters(configuration)
    dataset_record = {
        "identifier": dataset["identifier"],
        "version": dataset.get("version"),
        "sha256": dataset.get("sha256") or sha256_json(dataset),
        "fixtureCount": dataset.get("fixtureCount", 0),
        "operationCount": dataset.get("operationCount", 0),
        "payloadCharacteristics": dataset.get("payloadCharacteristics", {}),
    }
    actual_verdict = verdict or ("pass" if exit_code == 0 else "fail")
    if actual_verdict == "pass" and exit_code != 0:
        raise ValueError("a non-zero execution cannot produce a pass verdict")
    if actual_verdict == "notApplicable" and not reason:
        raise ValueError("notApplicable evidence requires a reason")

    packages = package_versions(root)
    release_grade = bool(release_mode and not git["dirtyWorkingTree"])
    acceptance_reason = reason
    if git["dirtyWorkingTree"]:
        acceptance_reason = "working tree was dirty during execution"
    record = {
        "evidenceRecordVersion": EVIDENCE_RECORD_VERSION,
        "evidenceId": f"urn:sort4circ:evidence-run:{uuid.uuid4()}",
        "evidenceType": evidence_type,
        "controlIdentifier": control_id,
        "testName": test_name,
        "source": {
            **git,
            "applicationVersion": packages.get("sort4circ-dpp", "notInstalled"),
        },
        "time": {
            "startedAt": started_at,
            "completedAt": completed_at,
            "durationSeconds": _duration_seconds(started_at, completed_at),
        },
        "execution": {
            "command": command,
            "tool": tool,
            "workingDirectory": "repositoryRoot",
            "exitCode": exit_code,
        },
        "environment": environment_metadata(root),
        "configuration": {
            "profile": configuration_profile,
            "parameters": clean_configuration,
            "sha256": sha256_json(clean_configuration),
            "sensitiveParametersOmitted": omitted,
        },
        "dataset": dataset_record,
        "artefactVersions": artefact_versions(root),
        "acceptance": {
            "target": target,
            "targetSource": "declaredRequirement",
            "targetUnit": target_unit,
            "acceptanceRule": acceptance_rule,
            "observedResult": observed_result,
            "observedResultSource": "rawResult",
            "observedUnit": observed_unit,
            "verdict": actual_verdict,
            "releaseGrade": release_grade,
            "evidenceClassification": "release" if release_grade else "research",
        },
        "output": {
            "rawResultPath": _safe_raw_path(root, raw_result_path),
            "rawResultSha256": file_digest(raw_result_path),
            "rawResultBytes": raw_result_path.stat().st_size,
            "mediaType": "application/json",
            "summaryMetrics": summary_metrics or {},
        },
    }
    if acceptance_reason:
        record["acceptance"]["reason"] = acceptance_reason
    return record


def validate_record(record: dict[str, Any], root: Path) -> None:
    schema_path = root / "evidence/schema/execution-evidence-1.0.0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        message = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"invalid execution evidence: {message}")


def write_record(record: dict[str, Any], target: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    validate_record(record, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
