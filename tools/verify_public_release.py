"""Verify/export an exact public file set; diagnostics never echo matched content."""
from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def distribution_version() -> str:
    """The packaged release version, read from pyproject so it cannot go stale."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not match:
        raise ReleaseError("package version not declared")
    return match.group(1)


POLICY_NAME = "public-release-policy.json"
MANIFEST_NAME = "MANIFEST.sha256"
LOCAL_DIRS = {".git", ".vscode", ".pytest_cache", ".ruff_cache", "__pycache__", ".venv",
              "venv", "build", "dist", "htmlcov", "evidence"}
LOCAL_FILES = {"PUBLIC_RELEASE_AUDIT.md", "PUBLIC_RELEASE_REMEDIATION_BRIEF.md", ".coverage"}
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", "keystores", ".git"}
FORBIDDEN_NAMES = LOCAL_FILES | {".env"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pem", ".key", ".p12", ".pfx", ".jks", ".log",
                      ".zip", ".gz", ".tar", ".whl"}

class ReleaseError(ValueError):
    """A category-only diagnostic suitable for a public terminal."""

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def valid_name(name: str) -> bool:
    parts = PurePosixPath(name).parts
    return bool(parts) and "\\" not in name and ":" not in name and not name.startswith("/") and all(
        p not in {"", ".", ".."} for p in parts) and "//" not in name

def forbidden(name: str) -> bool:
    path = PurePosixPath(name)
    return (not valid_name(name) or any(p.casefold() in FORBIDDEN_PARTS for p in path.parts)
            or path.name in FORBIDDEN_NAMES or path.name.startswith(".env.")
            or path.suffix.casefold() in FORBIDDEN_SUFFIXES
            or name.startswith("evidence/")
            or any(p.endswith(".egg-info") for p in path.parts))

def load_policy(root: Path = ROOT) -> dict:
    policy = json.loads((root / POLICY_NAME).read_text(encoding="utf-8"))
    paths = policy["files"]
    if not isinstance(paths, list) or len(paths) != len(set(paths)):
        raise ReleaseError("invalid public file policy")
    if any(not isinstance(p, str) or forbidden(p) for p in paths):
        raise ReleaseError("forbidden policy entry")
    if POLICY_NAME not in paths or MANIFEST_NAME not in paths:
        raise ReleaseError("incomplete public file policy")
    return policy

def with_private_rules(path: Path, policy: dict | None = None) -> dict:
    """Load confidential scan rules into memory; never copy them to an export."""
    path = path.resolve()
    if path == ROOT or ROOT in path.parents:
        raise ReleaseError("private scan rules must stay outside the checkout")
    rules = json.loads(path.read_text(encoding="utf-8"))
    signatures = rules["indicatorTokenHashes"]
    if not signatures or any(not isinstance(x, str) or not re.fullmatch(r"[a-f0-9]{64}", x) for x in signatures):
        raise ReleaseError("invalid private indicator rules")
    maximum = rules.get("maxIndicatorTokens", 6)
    if type(maximum) is not int or not 1 <= maximum <= 32:
        raise ReleaseError("invalid private indicator length")
    result = dict(policy or load_policy())
    result.update({"indicatorTokenHashes": signatures,
                   "attributionAllowlist": rules.get("attributionAllowlist", []),
                   "maxIndicatorTokens": maximum})
    for exception in result["attributionAllowlist"]:
        if exception["path"] not in result["files"] or not all(
            re.fullmatch(r"[a-f0-9]{64}", exception[key]) for key in ("lineHash", "indicatorHash")
        ):
            raise ReleaseError("invalid private attribution exception")
    return result


def leakage(name: str, data: bytes, policy: dict) -> None:
    try:
        content = data.decode("utf-8")
    except UnicodeError as exc:
        raise ReleaseError("unexpected binary content") from exc
    signatures = set(policy.get("indicatorTokenHashes", []))
    exceptions = {(x["path"], x["lineHash"], x["indicatorHash"])
                  for x in policy.get("attributionAllowlist", [])}
    for line in content.splitlines():
        words = re.findall(r"[a-z0-9]+", line.casefold())
        for size in range(1, policy.get("maxIndicatorTokens", 6) + 1):
            for start in range(len(words) - size + 1):
                token_hash = sha(" ".join(words[start:start + size]).encode())
                if token_hash in signatures and (name, sha(line.encode()), token_hash) not in exceptions:
                    raise ReleaseError("project indicator requires review")
        if re.search(r"-----BEGIN (?:[A-Z]+ )?" + "PRIVATE KEY-----", line):
            raise ReleaseError("private key content")
    # Policy hashes and independent synthetic test digests are not secrets.

def file_set(root: Path, *, workspace: bool, allowed_dirs: set[str] | None = None) -> set[str]:
    found = set()
    for directory, dirs, names in os.walk(root):
        base = Path(directory)
        kept = []
        for name in dirs:
            path = base / name
            if workspace and (name in LOCAL_DIRS or name.endswith(".egg-info")):
                continue
            if allowed_dirs is not None and path.relative_to(root).as_posix() not in allowed_dirs:
                raise ReleaseError("unexpected public directory")
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise ReleaseError("linked directory")
            kept.append(name)
        dirs[:] = kept
        for name in names:
            path = base / name
            relative = path.relative_to(root).as_posix()
            if workspace and (relative in LOCAL_FILES or name.endswith((".pyc", ".pyo"))):
                continue
            if path.is_symlink():
                raise ReleaseError("linked file")
            found.add(relative)
    return found

def verify_tree(root: Path, *, workspace: bool = False, check_manifest: bool = True,
                policy: dict | None = None) -> int:
    root = root.resolve()
    policy = policy or load_policy(root)
    expected = set(policy["files"])
    allowed_dirs = {parent.as_posix() for name in expected for parent in PurePosixPath(name).parents
                    if parent.as_posix() != "."}
    present = file_set(root, workspace=workspace, allowed_dirs=allowed_dirs)
    if present != expected:
        raise ReleaseError(f"file policy mismatch: missing={len(expected-present)}, unexpected={len(present-expected)}")
    for name in sorted(expected):
        if forbidden(name):
            raise ReleaseError("forbidden public file")
        leakage(name, (root / name).read_bytes(), policy)
    if check_manifest:
        lines = (root / MANIFEST_NAME).read_text(encoding="utf-8").splitlines()
        entries = {}
        for line in lines:
            value, name = line.split("  ", 1)
            if name in entries or not re.fullmatch(r"[a-f0-9]{64}", value):
                raise ReleaseError("invalid manifest")
            entries[name] = value
        if set(entries) != expected - {MANIFEST_NAME}:
            raise ReleaseError("manifest file policy mismatch")
        if any(sha((root / name).read_bytes()) != value for name, value in entries.items()):
            raise ReleaseError("manifest digest mismatch")
    return len(expected)

def write_manifests(root: Path = ROOT) -> None:
    policy = load_policy(root)
    # This operation can change digests, never the allowed public file list.
    verify_tree(root, workspace=True, check_manifest=False, policy=policy)
    source = "# Exact public source inclusion policy; generated by verify_files.py --write.\n"
    source += "global-exclude *\n" + "".join("include " + name + "\n" for name in sorted(policy["files"]))
    (root / "MANIFEST.in").write_text(source, encoding="utf-8", newline="\n")
    entries = "".join(sha((root / name).read_bytes()) + "  " + name + "\n"
                      for name in sorted(policy["files"]) if name != MANIFEST_NAME)
    (root / MANIFEST_NAME).write_text(entries, encoding="utf-8", newline="\n")

def export_tree(target: Path, root: Path = ROOT, policy: dict | None = None) -> int:
    policy = policy or load_policy(root)
    verify_tree(root, workspace=True, policy=policy)
    target = target.resolve()
    if target == root.resolve() or root.resolve() in target.parents or target.exists():
        raise ReleaseError("export requires a new directory outside the source checkout")
    target.mkdir(parents=True)
    for name in policy["files"]:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    return verify_tree(target, policy=policy)

def normalise_source_archive(path: Path) -> None:
    """Remove local owner, time and extra header metadata from generated tarballs."""
    output = io.BytesIO()
    with (
        tarfile.open(path) as source,
        gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as target,
    ):
        for original in sorted(source.getmembers(), key=lambda entry: entry.name):
            if not valid_name(original.name.rstrip("/")) or not (original.isfile() or original.isdir()):
                raise ReleaseError("unsafe generated archive entry")
            entry = tarfile.TarInfo(original.name)
            entry.type = tarfile.DIRTYPE if original.isdir() else tarfile.REGTYPE
            entry.mode = 0o755 if original.isdir() else 0o644
            entry.size = original.size if original.isfile() else 0
            entry.uid = entry.gid = entry.mtime = 0
            entry.uname = entry.gname = ""
            target.addfile(entry, source.extractfile(original) if original.isfile() else None)
    path.write_bytes(output.getvalue())


def verify_archive(path: Path, policy: dict | None = None) -> int:
    policy = policy or load_policy()
    verify_tree(ROOT, workspace=True, policy=policy)
    members = {}
    directories = set()
    total_size = 0
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            if archive.comment:
                raise ReleaseError("archive environment metadata")
            for entry in archive.infolist():
                if entry.extra or entry.comment:
                    raise ReleaseError("archive environment metadata")
                if entry.is_dir():
                    if not valid_name(entry.filename.rstrip("/")):
                        raise ReleaseError("unsafe archive directory")
                    directories.add(entry.filename.rstrip("/"))
                    continue
                if ((entry.external_attr >> 16) & 0o170000) == 0o120000:
                    raise ReleaseError("archive link")
                total_size += entry.file_size
                if entry.filename in members or entry.file_size > 5_000_000 or total_size > 20_000_000:
                    raise ReleaseError("duplicate or oversized archive entry")
                members[entry.filename] = archive.read(entry)
    else:
        with path.open("rb") as stream:
            header = stream.read(10)
        if header[:2] == b"\x1f\x8b" and (header[3] != 0 or int.from_bytes(header[4:8], "little") != 0):
            raise ReleaseError("archive environment metadata")
        with tarfile.open(path) as archive:
            for entry in archive:
                if entry.uname or entry.gname or entry.uid or entry.gid or entry.mtime or entry.pax_headers:
                    raise ReleaseError("archive environment metadata")
                if not valid_name(entry.name.rstrip("/")):
                    raise ReleaseError("unsafe archive path")
                if entry.isdir():
                    directories.add(entry.name.rstrip("/"))
                    continue
                total_size += entry.size
                if not entry.isfile() or entry.name in members or entry.size > 5_000_000 or total_size > 20_000_000:
                    raise ReleaseError("unsafe archive entry")
                members[entry.name] = archive.extractfile(entry).read()
    if not members or len(members) > 2000:
        raise ReleaseError("invalid archive size")
    member_parents = {parent.as_posix() for name in members for parent in PurePosixPath(name).parents
                      if parent.as_posix() != "."}
    if not directories <= member_parents:
        raise ReleaseError("unexpected archive directory")
    wheel = path.suffix == ".whl"
    root_prefixes = {name.split("/")[0] for name in members}
    version = distribution_version()
    if not wheel and (len(root_prefixes) != 1 or not root_prefixes <= {
        "public-profile", f"sort4circ-dpp-{version}", f"sort4circ_dpp-{version}"
    }):
        raise ReleaseError("unexpected source archive root")
    expected = set(policy["files"])
    seen = set()
    metadata = set()
    for name, data in members.items():
        if not valid_name(name):
            raise ReleaseError("unsafe archive path")
        relative = name if wheel else name.split("/", 1)[-1]
        mapped = relative
        if wheel:
            if relative.startswith("sort4circ_dpp/spec/"):
                mapped = "spec/" + relative[len("sort4circ_dpp/spec/"):]
            elif relative.startswith("sort4circ_dpp/"):
                mapped = "src/" + relative
            elif ".dist-info/" in relative:
                prefix, meta = relative.split(".dist-info/", 1)
                if prefix != f"sort4circ_dpp-{version}" or meta not in {
                    "METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt",
                    "licenses/LICENSE", "licenses/LICENSE-DOCS", "licenses/LICENSING.md", "LICENSE", "LICENSE-DOCS", "LICENSING.md"}:
                    raise ReleaseError("unexpected wheel metadata")
                if meta.split("/")[-1] in {"LICENSE", "LICENSE-DOCS", "LICENSING.md"}:
                    license_name = meta.split("/")[-1]
                    if data != (ROOT / license_name).read_bytes():
                        raise ReleaseError("changed licence metadata")
                    leakage(license_name, data, policy)
                else:
                    leakage(relative, data, policy)
                metadata.add(meta)
                continue
        elif relative == "PKG-INFO" or relative == "setup.cfg" or relative.startswith("src/sort4circ_dpp.egg-info/"):
            allowed = {"PKG-INFO", "setup.cfg", "src/sort4circ_dpp.egg-info/PKG-INFO",
                       "src/sort4circ_dpp.egg-info/SOURCES.txt", "src/sort4circ_dpp.egg-info/dependency_links.txt",
                       "src/sort4circ_dpp.egg-info/entry_points.txt", "src/sort4circ_dpp.egg-info/requires.txt",
                       "src/sort4circ_dpp.egg-info/top_level.txt"}
            if relative not in allowed:
                raise ReleaseError("unexpected source metadata")
            leakage(relative, data, policy)
            metadata.add(relative)
            continue
        if mapped not in expected or forbidden(mapped) or mapped in seen:
            raise ReleaseError("unexpected archive content")
        leakage(mapped, data, policy)
        if data != (ROOT / mapped).read_bytes():
            raise ReleaseError("archive differs from public candidate")
        seen.add(mapped)
    required = ({p for p in expected if p.startswith(("src/sort4circ_dpp/", "spec/"))}
                if wheel else expected)
    if seen != required:
        raise ReleaseError("archive public file policy mismatch")
    if wheel and not {"METADATA", "WHEEL", "RECORD"} <= metadata:
        raise ReleaseError("incomplete wheel metadata")
    return len(members)

def docker_context_files(root: Path = ROOT) -> set[str]:
    patterns = (root / ".dockerignore").read_text().splitlines()
    selected = set()
    for name in load_policy(root)["files"]:
        included = True
        for pattern in patterns:
            if not pattern or pattern.startswith("#"):
                continue
            negate = pattern.startswith("!")
            test = pattern[1:] if negate else pattern
            if any(fnmatch.fnmatchcase(candidate, test) for candidate in
                   [name, *(parent.as_posix() for parent in PurePosixPath(name).parents if parent.as_posix() != ".")]):
                included = negate
        if included:
            selected.add(name)
    if patterns[0] != "**":
        raise ReleaseError("Docker context must start deny-all")
    wanted = set(load_policy(root)["dockerFiles"])
    if selected != wanted:
        raise ReleaseError("Docker context policy mismatch")
    # Only literal file exceptions and required parent directory exceptions are allowed.
    allowed_rules = {"**"} | {"!" + p for p in wanted}
    for p in wanted:
        for parent in PurePosixPath(p).parents:
            if parent.as_posix() != ".":
                allowed_rules |= {"!" + parent.as_posix(), parent.as_posix() + "/**"}
                opening = "!" + parent.as_posix()
                if opening not in patterns or patterns[patterns.index(opening) + 1:patterns.index(opening) + 2] != [parent.as_posix() + "/**"]:
                    raise ReleaseError("Docker directory exception must re-exclude descendants")
    if any(p not in allowed_rules for p in patterns):
        raise ReleaseError("unexpected Docker context rule")
    return selected

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--export", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--private-rules", type=Path)
    mode.add_argument("--files-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.private_rules and not args.files_only:
            raise ReleaseError("private indicator review required")
        policy = with_private_rules(args.private_rules) if args.private_rules else load_policy()
        if args.archive:
            count = verify_archive(args.archive, policy=policy)
        elif args.export:
            count = export_tree(args.export, policy=policy)
        else:
            count = verify_tree(args.candidate or ROOT, workspace=args.candidate is None, policy=policy)
            docker_context_files(args.candidate or ROOT)
        if args.files_only:
            print(f"Public file policy PASS ({count} files); private indicator scan NOT RUN.")
        else:
            print(f"Public release verification PASS ({count} files); human review remains required.")
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, tarfile.TarError, zipfile.BadZipFile):
        print("Public release verification FAIL: content or policy requires private review.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
