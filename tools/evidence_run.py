"""Execute a local validation profile and emit a structured evidence record."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sort4circ_dpp.execution_evidence import (  # noqa: E402
    build_record,
    files_digest,
    utcnow,
    write_record,
)


@dataclass(frozen=True)
class Profile:
    control_id: str
    test_name: str
    arguments: tuple[str, ...]
    dataset_paths: tuple[str, ...]


PROFILES = {
    "tests": Profile(
        "TEST-ALL",
        "normal test suite",
        ("-m", "pytest", "-q"),
        ("tests",),
    ),
    "fixtures": Profile(
        "FIXTURE-VALIDATION",
        "fixture and schema validation",
        ("tools/validate_fixtures.py",),
        ("examples/fixtures", "spec/schemas", "spec/vocabularies"),
    ),
    "mapping": Profile(
        "MAPPING-CONFORMANCE",
        "JSON XML RDF mapping conformance",
        ("-m", "pytest", "tests/test_mapping.py", "-q"),
        ("tests/test_mapping.py", "spec/mappings", "examples/fixtures"),
    ),
}


def files_for(profile: Profile) -> list[Path]:
    paths: list[Path] = []
    for relative in profile.dataset_paths:
        path = ROOT / relative
        if path.is_file():
            paths.append(path)
        else:
            paths.extend(item for item in path.rglob("*") if item.is_file())
    return sorted(set(paths))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=sorted(PROFILES))
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--release-evidence", action="store_true")
    args = parser.parse_args(argv)

    profile = PROFILES[args.profile]
    command = [sys.executable, *profile.arguments]
    started_at = utcnow()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    completed_at = utcnow()

    raw_path = args.evidence_dir / "raw-result.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_document = {
        "profile": args.profile,
        "command": ["python", *profile.arguments],
        "exitCode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    raw_path.write_text(json.dumps(raw_document, indent=2) + "\n", encoding="utf-8")

    dataset_paths = files_for(profile)
    evidence_record = build_record(
        root=ROOT,
        control_id=profile.control_id,
        test_name=profile.test_name,
        command=" ".join(["python", *profile.arguments]),
        tool="tools/evidence_run.py",
        started_at=started_at,
        completed_at=completed_at,
        exit_code=result.returncode,
        configuration_profile=f"local-{args.profile}",
        configuration={"profile": args.profile, "arguments": list(profile.arguments)},
        dataset={
            "identifier": f"repository-{args.profile}-inputs",
            "version": None,
            "sha256": files_digest(ROOT, dataset_paths),
            "fixtureCount": len(dataset_paths),
            "operationCount": 1,
            "payloadCharacteristics": {
                "sourcePaths": list(profile.dataset_paths),
                "capturedFileCount": len(dataset_paths),
            },
        },
        target=0,
        target_unit="exit code",
        acceptance_rule="the configured validation command exits zero",
        observed_result=result.returncode,
        observed_unit="exit code",
        verdict="pass" if result.returncode == 0 else "fail",
        raw_result_path=raw_path,
        summary_metrics={
            "exitCode": result.returncode,
            "stdoutLineCount": len(result.stdout.splitlines()),
            "stderrLineCount": len(result.stderr.splitlines()),
        },
        release_mode=args.release_evidence,
    )
    write_record(evidence_record, args.evidence_dir / "evidence.json")
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    print(f"wrote {args.evidence_dir / 'evidence.json'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
