"""Check a SORT4CIRC checkout against MANIFEST.sha256.

Run from the repository root, with MANIFEST.sha256 in the same folder:

    python verify_files.py

Reports missing files, extra files and content mismatches. Exit code 0 means
the checkout is byte-for-byte identical to what was delivered.

Lines in the manifest that begin with "#" are header comments and are skipped.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

IGNORE_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv", "node_modules"}
# MANIFEST.sha256 cannot list its own digest: writing the digest in would change
# the bytes it describes. It is the one delivered file the manifest cannot cover.
IGNORE_NAMES = {"MANIFEST.sha256", "conformance-report.json"}


def main() -> int:
    root = pathlib.Path(".").resolve()
    manifest = root / "MANIFEST.sha256"
    if not manifest.exists():
        print("MANIFEST.sha256 not found. Run this from the repository root.")
        return 2

    expected = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, path = line.split("  ", 1)
            expected[path] = digest

    present = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        if rel in IGNORE_NAMES or rel.endswith(".pyc"):
            continue
        present[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

    missing = sorted(set(expected) - set(present))
    extra = sorted(set(present) - set(expected))
    changed = sorted(k for k in set(expected) & set(present) if expected[k] != present[k])

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
    sys.exit(main())
