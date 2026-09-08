"""Execute public-profile checks; export only fixed identifiers and statuses."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sort4circ_dpp.public_summary import PublicConformanceSummary  # noqa: E402

TESTS = {
    "schema": ["tests/test_validation.py", "tests/test_synthetic.py"],
    "canonical": ["tests/test_canonical.py"],
    "integrity": ["tests/test_ledger_contract.py", "tests/test_evidence.py"],
    "identifier": ["tests/test_readzone.py", "tests/test_store.py"],
    "api": ["tests/test_api_contract.py", "tests/test_access.py"],
    "mapping": ["tests/test_mapping.py"],
    "publication": ["tests/test_public_release.py", "tests/test_public_summary.py", "tests/test_licensing.py"],
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="optional destination for a sanitised summary")
    args = parser.parse_args(argv)
    results = {}
    for name, paths in TESTS.items():
        # Raw output stays in this process and is not persisted or exported.
        run = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths],
            cwd=ROOT, capture_output=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        results[name] = "pass" if run.returncode == 0 else "fail"
    summary = PublicConformanceSummary.from_private_results({"results": results}).document()
    rendered = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return int("fail" in results.values())


if __name__ == "__main__":
    raise SystemExit(main())
