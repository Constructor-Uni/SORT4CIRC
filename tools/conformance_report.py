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

    report = {
        "specification": "SORT4CIRC D4.3, DPP development guidelines",
        "suiteResult": "pass" if passed else "fail",
        "automatedRows": sorted(k for k, v in rows.items() if v["decidedBy"] == "automated test"),
        "rowsRequiringHumanEvidence": sorted(REQUIRES_HUMAN_EVIDENCE),
        "rows": dict(sorted(rows.items())),
        "note": (
            "Automated rows are decided by this repository's test suite. Rows requiring "
            "human evidence are not decided here and are listed so that a conformance "
            "statement cannot omit them silently."
        ),
    }
    target = ROOT / "conformance-report.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(result.stdout[-2000:])
    print(f"wrote {target.name}: {len(report['automatedRows'])} automated rows, "
          f"{len(report['rowsRequiringHumanEvidence'])} awaiting human evidence")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
