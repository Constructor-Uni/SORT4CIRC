"""Validate every fixture, positive and negative.

A negative fixture that fails to fail is a silent gap in the schema, so the
expected reason code is asserted rather than merely the absence of success.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sort4circ_dpp.reasons import DppError  # noqa: E402
from sort4circ_dpp.validation import validate_payload  # noqa: E402

FIXTURES = ROOT / "examples" / "fixtures"


def main() -> int:
    failures = 0
    checked = 0
    for path in sorted(FIXTURES.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        expected = document.pop("$expect", None)
        checked += 1
        try:
            validate_payload(document)
            actual = None
        except DppError as exc:
            actual = exc.code
        if actual != expected:
            failures += 1
            print(f"FAIL {path.name}: expected {expected or 'valid'}, got {actual or 'valid'}")
        else:
            print(f"ok   {path.name}: {expected or 'valid'}")
    print(f"\n{checked - failures}/{checked} fixtures behaved as declared")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
