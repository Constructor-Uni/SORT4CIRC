"""Fail closed on unlisted distributable material and leakage markers."""
import io
import json
import tarfile
import zipfile

import pytest
from tools.verify_public_release import (
    ROOT,
    ReleaseError,
    docker_context_files,
    export_tree,
    leakage,
    load_policy,
    normalise_source_archive,
    sha,
    verify_archive,
    verify_tree,
)


@pytest.mark.parametrize("name", [
    "PUBLIC_RELEASE_AUDIT.md", "PUBLIC_RELEASE_REMEDIATION_BRIEF.md",
    "evidence/runs/raw.json", "evidence/releases/result.json", "__pycache__/x.pyc",
    ".pytest_cache/state", ".ruff_cache/state", ".env", ".env.local",
    "identity.key", "keystores/account.json", "raw-test.log", "extra.zip", "deployment.yml",
])
def test_final_candidate_rejects_unexpected_files(tmp_path, name):
    candidate = tmp_path / "candidate"
    export_tree(candidate)
    target = candidate / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("fictional private sentinel")
    with pytest.raises(ReleaseError):
        verify_tree(candidate)

def test_known_content_change_fails_manifest(tmp_path):
    candidate = tmp_path / "candidate"
    export_tree(candidate)
    (candidate / "README.md").write_text("changed")
    with pytest.raises(ReleaseError):
        verify_tree(candidate)

def test_targeted_scanner_has_exact_attribution_exceptions():
    line = "Attribution to Fictional Partner Zebra"
    signature = sha(b"fictional partner zebra")
    policy = {"indicatorTokenHashes": [signature], "attributionAllowlist": []}
    with pytest.raises(ReleaseError):
        leakage("README.md", line.encode(), policy)
    policy["attributionAllowlist"] = [{"path": "README.md", "lineHash": sha(line.encode()), "indicatorHash": signature}]
    leakage("README.md", line.encode(), policy)
    with pytest.raises(ReleaseError):
        leakage("config.json", line.encode(), policy)
    with pytest.raises(ReleaseError):
        leakage("README.md", (line + " deployment").encode(), policy)
    leakage("README.md", b"SORT4CIRC DPP blockchain RFID JSON RDF OWL API", policy)

@pytest.mark.parametrize("name", ["../outside", "root/../outside", "/absolute", "root/.env"])
def test_archive_rejects_unsafe_or_private_members(tmp_path, name):
    archive = tmp_path / "candidate.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        entry = tarfile.TarInfo(name)
        entry.size = 1
        handle.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises(ReleaseError):
        verify_archive(archive)

def test_source_archive_contains_exact_verified_files(tmp_path):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        for name in load_policy()["files"]:
            handle.add(ROOT / name, arcname="public-profile/" + name, recursive=False)
    normalise_source_archive(archive)
    assert verify_archive(archive) == len(load_policy()["files"])

def test_wheel_rejects_unexpected_payload(tmp_path):
    archive = tmp_path / "fake.whl"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("sort4circ_dpp/private.json", "{}")
    with pytest.raises(ReleaseError):
        verify_archive(archive)

def test_docker_context_has_only_allowed_public_files():
    selected = docker_context_files()
    assert selected == set(load_policy()["dockerFiles"])
    assert not any(p.startswith(("evidence/", "tests/")) for p in selected)

def test_openapi_has_no_maintenance_operations():
    document = json.loads((ROOT / "spec/openapi/dpp-api-v1.json").read_text())
    assert not any("/internal/" in path for path in document["paths"])

def test_public_docs_link_only_existing_local_files():
    import re
    for name in load_policy()["files"]:
        if not name.endswith(".md"):
            continue
        path = ROOT / name
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            assert (path.parent / target.split("#")[0]).resolve().is_file()

def test_documentation_states_profile_scope_and_owner_actions():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "normative only for conformance with the public profile" in readme
    assert "does not constitute an official European Union specification" in readme
    assert "MIT for software" in readme
    assert "CC BY 4.0" in readme
    assert "GitHub Private Vulnerability Reporting is the official reporting mechanism" in (ROOT / "SECURITY.md").read_text()
    for name in ("examples/README.md", "examples/fixtures/README.md"):
        assert "Synthetic example. Not SORT4CIRC project data." in (ROOT / name).read_text()

def test_full_release_cli_requires_private_rules(capsys):
    from tools.verify_public_release import main
    assert main([]) == 1
    assert "PASS" not in capsys.readouterr().out


def test_docker_parent_exceptions_reexclude_unlisted_descendants():
    import fnmatch
    from pathlib import PurePosixPath
    patterns = (ROOT / ".dockerignore").read_text().splitlines()
    for name in ("src/private.json", "src/sort4circ_dpp/private.json", "spec/private.yml", "tools/raw.log"):
        included = True
        candidates = [name, *(p.as_posix() for p in PurePosixPath(name).parents if p.as_posix() != ".")]
        for rule in patterns:
            negate = rule.startswith("!")
            pattern = rule[1:] if negate else rule
            if any(fnmatch.fnmatchcase(candidate, pattern) for candidate in candidates):
                included = negate
        assert not included


def test_empty_private_directory_is_rejected(tmp_path):
    candidate = tmp_path / "candidate"
    export_tree(candidate)
    (candidate / "evidence" / "runs").mkdir(parents=True)
    with pytest.raises(ReleaseError):
        verify_tree(candidate)


def test_archive_rejects_an_unlisted_empty_directory(tmp_path):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        for name in load_policy()["files"]:
            handle.add(ROOT / name, arcname="public-profile/" + name, recursive=False)
        entry = tarfile.TarInfo("public-profile/private-directory")
        entry.type = tarfile.DIRTYPE
        handle.addfile(entry)
    normalise_source_archive(archive)
    with pytest.raises(ReleaseError):
        verify_archive(archive)


def test_generated_source_metadata_is_neutral(tmp_path):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        entry = tarfile.TarInfo("public-profile/README.md")
        entry.uname = "fictional-local-owner"
        entry.gname = "fictional-local-group"
        entry.uid = 42
        entry.mtime = 123456
        entry.size = 1
        handle.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises(ReleaseError, match="archive environment metadata"):
        verify_archive(archive)
    normalise_source_archive(archive)
    with tarfile.open(archive) as handle:
        entry = handle.getmembers()[0]
        assert (entry.uid, entry.gid, entry.uname, entry.gname, entry.mtime, entry.pax_headers) == (0, 0, "", "", 0, {})
        assert handle.extractfile(entry).read() == b"x"
