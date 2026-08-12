"""Run the conformance suite and emit a machine-readable report.

The report separates rows the suite decided from rows that require human
evidence. A suite that omitted the second category would read as full coverage
when it is not, which is the failure mode this tool exists to prevent.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))


def build_report(
    rows: dict[str, dict[str, str]],
    human_evidence: dict[str, str],
    passed: bool,
) -> dict[str, object]:
    """Build a report without attributing a suite failure to individual rows."""
    automated_rows = sorted(k for k, v in rows.items() if v["decidedBy"] == "automated test")
    return {
        "specification": "SORT4CIRC D4.3, DPP development guidelines",
        "suiteResult": "pass" if passed else "fail",
        "automatedRows": automated_rows,
        "automatedRowsPassed": automated_rows if passed else None,
        "rowsRequiringHumanEvidence": sorted(human_evidence),
        "rows": dict(sorted(rows.items())),
        "note": (
            "automatedRows identifies rows that have automated tests, not their individual outcomes. "
            "When the full suite passes, automatedRowsPassed lists those rows. When the suite fails, "
            "automatedRowsPassed is null because this suite-level report does not attribute the failure "
            "to individual rows. Rows requiring human evidence remain listed so that a conformance "
            "statement cannot omit them silently."
        ),
    }


def main() -> int:
    from conformance.test_checklist import REQUIRES_HUMAN_EVIDENCE

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    passed = result.returncode == 0

    rows: dict[str, dict[str, str]] = {}
    for path in (ROOT / "tests" / "conformance").glob("test_*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("@pytest.mark.checklist("):
                inner = stripped[len("@pytest.mark.checklist(") : -1]
                identifier, tier = (part.strip().strip('"') for part in inner.split(","))
                rows[identifier] = {"tier": tier, "decidedBy": "automated test"}

    for identifier, evidence in REQUIRES_HUMAN_EVIDENCE.items():
        rows.setdefault(identifier, {"tier": "", "decidedBy": "human evidence"})
        rows[identifier]["outstandingEvidence"] = evidence

    report = build_report(rows, REQUIRES_HUMAN_EVIDENCE, passed)
    target = ROOT / "conformance-report.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(result.stdout[-2000:])
    print(f"wrote {target.name}: {len(report['automatedRows'])} automated rows, "
          f"{len(report['rowsRequiringHumanEvidence'])} awaiting human evidence")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
