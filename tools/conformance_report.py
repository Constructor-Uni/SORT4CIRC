"""Run the conformance suite and emit a machine-readable report.

The report separates rows the suite decided from rows that require human
evidence. A suite that omitted the second category would read as full coverage
when it is not, which is the failure mode this tool exists to prevent.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))
from sort4circ_dpp.execution_evidence import build_record, files_digest, utcnow, write_record  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", type=Path, nargs="?", help="write a structured execution evidence run")
    parser.add_argument("--release-evidence", action="store_true", help="require a clean tree and mark evidence release-grade")
    args = parser.parse_args(argv)
    evidence_dir = args.evidence_dir
    from conformance.test_checklist import REQUIRES_HUMAN_EVIDENCE

    started_at = utcnow()
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
    if evidence_dir:
        raw_path = evidence_dir / "raw-result.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_document = {
            "report": report,
            "pytest": {
                "command": [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-p", "no:cacheprovider"],
                "exitCode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        }
        raw_path.write_text(json.dumps(raw_document, indent=2) + "\n", encoding="utf-8")
        test_paths = sorted((ROOT / "tests").rglob("*.py"))
        evidence = build_record(
            root=ROOT,
            control_id="SCP-07",
            test_name="D4.3 conformance suite",
            command="python tools/conformance_report.py",
            tool="tools/conformance_report.py",
            started_at=started_at,
            completed_at=utcnow(),
            exit_code=0 if passed else 1,
            configuration={"pytestArgs": ["tests", "-q", "--no-header", "-p", "no:cacheprovider"]},
            configuration_profile="local-conformance",
            dataset={
                "identifier": "repository-tests",
                "version": None,
                "sha256": files_digest(ROOT, test_paths),
                "fixtureCount": len(test_paths),
                "operationCount": 1,
                "payloadCharacteristics": {"kind": "Python test and conformance sources"},
            },
            target="pass",
            target_unit="suite verdict",
            acceptance_rule="the complete automated suite exits zero",
            observed_result=report["suiteResult"],
            observed_unit="suite verdict",
            verdict="pass" if passed else "fail",
            raw_result_path=raw_path,
            summary_metrics={
                "suiteResult": report["suiteResult"],
                "automatedRows": len(report["automatedRows"]),
                "humanEvidenceRows": len(report["rowsRequiringHumanEvidence"]),
            },
            release_mode=args.release_evidence,
        )
        write_record(evidence, evidence_dir / "evidence.json")
    print(result.stdout[-2000:])
    print(f"wrote {target.name}: {len(report['automatedRows'])} automated rows, "
          f"{len(report['rowsRequiringHumanEvidence'])} awaiting human evidence")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
