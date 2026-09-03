"""Check a SORT4CIRC checkout against MANIFEST.sha256, or regenerate it.

Run from the repository root, with MANIFEST.sha256 in the same folder:

    python verify_files.py            # verify the tree against the manifest
    python verify_files.py --write    # regenerate the manifest from the tree

Reports missing files, extra files and content mismatches. Exit code 0 means
the checkout is byte-for-byte identical to what was delivered.

Lines in the manifest that begin with "#" are header comments and are skipped.

Verification and regeneration both go through ``scan``, so the two cannot
disagree about which files the manifest covers. A file excluded from the scan
is excluded from the written manifest by the same rule that excludes it from
the comparison.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

MANIFEST_NAME = "MANIFEST.sha256"

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "htmlcov",
}
# An editable install writes <package>.egg-info next to the sources, and CI does
# exactly that before running the suite. It is a build output, not a delivered
# file, so it is excluded by suffix rather than by an exact directory name.
IGNORE_DIR_SUFFIXES = (".egg-info",)
# MANIFEST.sha256 cannot list its own digest: writing the digest in would change
# the bytes it describes. It is the one delivered file the manifest cannot cover.
IGNORE_NAMES = {MANIFEST_NAME, "conformance-report.json", ".coverage"}
IGNORE_PREFIXES = ("evidence/runs/",)

HEADER = (
    "# SORT4CIRC textile Digital Product Passport, deliverable D4.3",
    "# Release 1.1.1, see tag v1.1.1",
    "# sha256 of every delivered file, paths relative to the repository root.",
    "# Verify with: python verify_files.py, regenerate with: python verify_files.py --write",
    "# MANIFEST.sha256 itself is not listed: it cannot contain its own digest.",
)


def scan(root: pathlib.Path) -> dict[str, str]:
    """Return {path relative to root: sha256} for every delivered file.

    This is the single definition of what the manifest covers. Both the
    verifier and ``--write`` call it.
    """
    found = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        if any(part.endswith(IGNORE_DIR_SUFFIXES) for part in p.parts[:-1]):
            continue
        rel = p.relative_to(root).as_posix()
        if rel in IGNORE_NAMES or rel.endswith(".pyc") or rel.startswith(IGNORE_PREFIXES):
            continue
        found[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return found


def read_manifest(path: pathlib.Path) -> dict[str, str]:
    """Parse a manifest into {path: sha256}, skipping header comments."""
    expected = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, rel = line.split("  ", 1)
            expected[rel] = digest
    return expected


def compare(
    expected: dict[str, str], present: dict[str, str]
) -> tuple[list[str], list[str], list[str]]:
    """Return (missing, changed, extra), each a sorted list of paths."""
    missing = sorted(set(expected) - set(present))
    extra = sorted(set(present) - set(expected))
    changed = sorted(k for k in set(expected) & set(present) if expected[k] != present[k])
    return missing, changed, extra


def render(entries: dict[str, str]) -> bytes:
    """Render a manifest. Always LF, so the bytes do not depend on the platform."""
    lines = list(HEADER) + [f"{entries[k]}  {k}" for k in sorted(entries)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def write(root: pathlib.Path) -> dict[str, str]:
    entries = scan(root)
    (root / MANIFEST_NAME).write_bytes(render(entries))
    return entries


def main(argv: list[str]) -> int:
    root = pathlib.Path(".").resolve()
    manifest = root / MANIFEST_NAME

    unknown = [a for a in argv if a != "--write"]
    if unknown:
        print(f"unrecognised argument: {unknown[0]}")
        print("usage: python verify_files.py [--write]")
        return 2

    if "--write" in argv:
        entries = write(root)
        print(f"wrote {MANIFEST_NAME}, {len(entries)} files covered")
        return 0

    if not manifest.exists():
        print(f"{MANIFEST_NAME} not found. Run this from the repository root.")
        return 2

    expected = read_manifest(manifest)
    present = scan(root)
    missing, changed, extra = compare(expected, present)

    for label, items in (("MISSING", missing), ("CHANGED", changed), ("EXTRA", extra)):
        if items:
            print(f"\n{label} ({len(items)}):")
            for item in items:
                print(f"  {item}")

    ok = not missing and not changed
    print(f"\n{len(expected)} expected, {len(present)} found, "
          f"{len(missing)} missing, {len(changed)} changed, {len(extra)} extra")
    print("RESULT:", "identical to the delivered files" if ok else "does not match")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
