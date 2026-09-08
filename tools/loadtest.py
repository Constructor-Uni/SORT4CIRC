"""Run a synthetic local workload; results belong to the caller, never a project.

Use --output outside the public candidate if a private measurement file is needed.
This harness measures the in-process HTTP test client, not a network deployment.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient  # noqa: E402

from sort4circ_dpp.api import create_app  # noqa: E402
from sort4circ_dpp.auth import DemoAuth  # noqa: E402
from sort4circ_dpp.synthetic import SyntheticFixtureFactory  # noqa: E402


def percentile(samples, fraction):
    return sorted(samples)[max(0, math.ceil(len(samples) * fraction) - 1)]


def measure(requests):
    factory = SyntheticFixtureFactory()
    client = TestClient(create_app(auth_provider=DemoAuth()))
    headers = {"X-DPP-Role": "brand", "X-DPP-Organisation": "urn:example:org:manufacturer-a"}
    record = client.post("/v1/dpps", json=factory.passport(), headers=headers)
    record.raise_for_status()
    identifier = record.json()["dppId"]
    client.post(f"/v1/dpps/{identifier}/carriers", json=factory.carrier(), headers=headers).raise_for_status()
    samples, failures = [], 0
    for _ in range(requests):
        start = time.perf_counter()
        response = client.get(f"/v1/dpps/{identifier}", headers=headers)
        samples.append((time.perf_counter() - start) * 1000)
        failures += response.status_code != 200
    return {
        "scope": "User-run synthetic in-process reference measurement; no project or deployment result",
        "dataset": "synthetic-public-fixtures",
        "requests": requests, "failures": failures,
        "p50Ms": percentile(samples, 0.5), "p99Ms": percentile(samples, 0.99),
        "targetMs": None,
        "limitations": "No network, persistence, hardware, authentication service or external integrity cost.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.requests <= 100000:
        parser.error("request count outside the example range")
    result = measure(args.requests)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Synthetic workload completed; results are private unless separately reviewed.")
    return int(result["failures"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
