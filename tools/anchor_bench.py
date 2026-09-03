"""Anchoring benchmark across ledger platforms.

Purpose
-------
Deliverable D4.3 states anchoring targets without stating measured values,
because the measurement depends on credentials, network placement and, for
energy, on a physical meter. This harness performs the measurement. It is
written against the adapter contract in ``sort4circ_dpp.ledger.base``, so a
platform is added by writing an adapter and one configuration entry, not by
editing this file.

The harness reports only what it observed. A platform that is not reachable, or
for which credentials are absent, is reported as ``notReached`` and contributes
no figures. There is no modelled fallback, no published-average substitution and
no extrapolation from another network. A benchmark that fills gaps with
literature values cannot be told apart from one that measured them, and the
distinction is the entire value of the exercise.

Configuration
-------------
A JSON document listing the platforms to measure::

    {
      "runs": 50,
      "confirmationTimeoutSeconds": 300,
      "pollIntervalSeconds": 1.0,
      "platforms": [
        {
          "name": "besu-permissioned",
          "adapter": "sort4circ_dpp.ledger.besu:BesuLedger",
          "options": {"rpc_url": "http://besu-node:8545"},
          "finality": "deterministic",
          "notes": "four validator IBFT 2.0 network, WP4 reference deployment"
        },
        {
          "name": "ethereum-sepolia",
          "adapter": "consortium_adapters.ethereum:EthereumLedger",
          "options": {},
          "finality": "probabilistic",
          "confirmationDepth": 12
        },
        {"name": "algorand-testnet",  "adapter": "consortium_adapters.algorand:AlgorandLedger"},
        {"name": "iota-testnet",      "adapter": "consortium_adapters.iota:IotaLedger"},
        {"name": "ebsi-pilot",        "adapter": "consortium_adapters.ebsi:EbsiLedger"}
      ]
    }

Usage
-----
    python tools/anchor_bench.py --self-test
        Runs the whole harness against the in-memory adapter. This proves the
        harness works; it says nothing about any chain, and the output is
        labelled accordingly.

    python tools/anchor_bench.py --config anchor-targets.json --json out.json

    python tools/anchor_bench.py --config anchor-targets.json \
        --energy-csv meter.csv --energy-idle-csv idle.csv

Energy
------
Energy per anchored record is computed from a meter log, never from a model. The
meter log is a two-column CSV of ``timestamp_iso8601,watts`` sampled at a stated
rate. An idle log recorded over the same hardware with the service stopped is
required, because the quantity of interest is the marginal energy of anchoring
and not the standing draw of the machine. Without both logs the energy section
reports ``notMeasured`` and the reason.

For a public permissionless network the meter measures the submitting node only.
Network-wide energy per transaction is not measurable from a client and is not
reported here; a claim about it belongs to a study with access to the validator
set, and citing one of those studies is a literature statement, not a result of
this harness.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import platform
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sort4circ_dpp.canonical import canonical_bytes, digest  # noqa: E402
from sort4circ_dpp.execution_evidence import build_record, sha256_json, utcnow, write_record  # noqa: E402
from sort4circ_dpp.ledger.base import LedgerAdapter, LedgerError, Receipt  # noqa: E402

#: The reference record whose projection is anchored, so that every platform
#: anchors an identical payload of identical length. Taken from D4.3 Annex G.
REFERENCE_RECORD: dict[str, Any] = {
    "dppId": "urn:sort4circ:dpp:000001",
    "recordVersion": 7,
    "updatedAt": "2026-08-10T09:12:44Z",
    "identity": {
        "granularity": "item",
        "itemId": "urn:sort4circ:item:000001",
        "epc": "urn:epc:id:sgtin:0614141.112345.400",
    },
    "product": {
        "articleClass": "upperBodyKnitwear",
        "fabricConstruction": "knitted",
        "technicalFlags": ["carbonBlackPresent", "hardPointZipMetal"],
    },
    "materialObservations": [
        {
            "observationId": "urn:sort4circ:obs:000001",
            "fibreType": "polyester",
            "percentage": 95,
            "percentageBasis": "mass",
            "valueStatus": "supplied",
            "method": "labQuantitativeIso1833",
            "sourceOrganisationId": "urn:sort4circ:org:txho",
            "observedAt": "2026-06-18T11:02:10Z",
        },
        {
            "observationId": "urn:sort4circ:obs:000002",
            "fibreType": "elastane",
            "percentage": 5,
            "percentageBasis": "mass",
            "valueStatus": "supplied",
            "method": "labQuantitativeIso1833",
            "sourceOrganisationId": "urn:sort4circ:org:txho",
            "observedAt": "2026-06-18T11:02:10Z",
        },
    ],
}


# --------------------------------------------------------------------- helpers


def percentile(ordered: list[float], fraction: float) -> float | None:
    if not ordered:
        return None
    rank = max(1, min(len(ordered), int(round(fraction * len(ordered) + 0.5))))
    return ordered[rank - 1]


def summarise(samples: list[float]) -> dict[str, Any]:
    ordered = sorted(samples)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "meanMs": round(statistics.fmean(ordered), 2),
        "p50Ms": round(percentile(ordered, 0.50), 2),
        "p95Ms": round(percentile(ordered, 0.95), 2),
        "p99Ms": round(percentile(ordered, 0.99), 2),
        "maxMs": round(ordered[-1], 2),
    }


def load_adapter(spec: str, options: dict[str, Any]) -> LedgerAdapter:
    """Instantiate ``module:Class`` with keyword ``options``."""
    module_name, _, class_name = spec.partition(":")
    if not class_name:
        raise ValueError(f"adapter spec must be 'module:Class', got {spec!r}")
    module = importlib.import_module(module_name)
    return getattr(module, class_name)(**options)


def envelope(evidence_id: str, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidenceId": evidence_id,
        "digestAlgorithm": "sha-256",
        "canonicalisation": "rfc8785",
        "digestValue": digest(record),
        "subjectVersion": record["recordVersion"],
        "payloadBytes": len(canonical_bytes(record)),
    }


# ------------------------------------------------------------------ per platform


@dataclass
class PlatformResult:
    name: str
    status: str = "notReached"
    reason: str | None = None
    network_id: str | None = None
    finality: str | None = None
    submit_ms: list[float] = field(default_factory=list)
    confirm_ms: list[float] = field(default_factory=list)
    failures: dict[str, int] = field(default_factory=dict)
    fees: list[float] = field(default_factory=list)
    fee_unit: str | None = None
    unconfirmed: int = 0

    def document(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "platform": self.name,
            "status": self.status,
            "networkId": self.network_id,
            "finality": self.finality,
        }
        if self.status != "measured":
            # A platform that answered the preflight but refused every
            # submission is unreached for a different reason from one that never
            # answered at all, and the recorded reason codes are the difference.
            if self.failures:
                doc["failures"] = self.failures
                worst = max(self.failures.items(), key=lambda item: item[1])
                doc["reason"] = self.reason or f"every submission failed, most often {worst[0]} ({worst[1]} times)"
            else:
                doc["reason"] = self.reason or "no submission was attempted and no reason was recorded"
            return doc
        if self.reason:
            doc["reason"] = self.reason
        doc["submitLatency"] = summarise(self.submit_ms)
        doc["timeToConfirmation"] = summarise(self.confirm_ms)
        doc["submitSamplesMs"] = [round(value, 6) for value in self.submit_ms]
        doc["confirmationSamplesMs"] = [round(value, 6) for value in self.confirm_ms]
        doc["unconfirmedAtTimeout"] = self.unconfirmed
        doc["failures"] = self.failures
        if self.fees:
            doc["fee"] = {
                "unit": self.fee_unit,
                "mean": round(statistics.fmean(self.fees), 12),
                "total": round(sum(self.fees), 12),
                "n": len(self.fees),
            }
        else:
            doc["fee"] = {"status": "notCaptured", "reason": "the adapter receipt carried no fee field"}
        return doc


def fee_from(receipt: Receipt) -> tuple[float | None, str | None]:
    """Extract a fee from the adapter's raw receipt when one is present."""
    raw = receipt.raw or {}
    for key, unit in (
        ("feePaid", "native"),
        ("fee", "native"),
        ("effectiveGasPrice", "wei"),
        ("gasUsed", "gas"),
    ):
        value = raw.get(key)
        if value is None:
            continue
        try:
            return (float(int(value, 16)) if isinstance(value, str) and value.startswith("0x") else float(value)), unit
        except (TypeError, ValueError):
            continue
    return None, None


def measure(
    name: str,
    adapter: LedgerAdapter,
    runs: int,
    timeout_seconds: float,
    poll_seconds: float,
    finality: str | None,
) -> PlatformResult:
    result = PlatformResult(name=name, finality=finality)
    result.network_id = getattr(adapter, "network_id", None)

    # Preflight. A platform that cannot answer a status query for an identifier
    # it has never seen is not measured; it is reported as unreachable.
    try:
        adapter.status(f"urn:sort4circ:evidence:preflight:{uuid.uuid4()}")
    except LedgerError as exc:
        result.reason = f"preflight failed: {exc.reason_code}: {exc}"
        return result
    except Exception as exc:  # noqa: BLE001
        result.reason = f"preflight raised {type(exc).__name__}: {exc}"
        return result

    for index in range(runs):
        record = dict(REFERENCE_RECORD)
        record["recordVersion"] = 7 + index
        evidence_id = f"urn:sort4circ:evidence:{uuid.uuid4()}"
        payload = envelope(evidence_id, record)

        began = time.perf_counter()
        try:
            receipt = adapter.submit(evidence_id, payload)
        except LedgerError as exc:
            result.failures[exc.reason_code] = result.failures.get(exc.reason_code, 0) + 1
            continue
        except Exception as exc:  # noqa: BLE001
            key = f"unhandled:{type(exc).__name__}"
            result.failures[key] = result.failures.get(key, 0) + 1
            continue
        result.submit_ms.append((time.perf_counter() - began) * 1000.0)
        result.status = "measured"

        deadline = began + timeout_seconds
        confirmed = receipt.state == "confirmed"
        while not confirmed and time.perf_counter() < deadline:
            time.sleep(poll_seconds)
            try:
                current = adapter.status(evidence_id)
            except LedgerError:
                continue
            if current is not None and current.state == "confirmed":
                receipt = current
                confirmed = True
        if confirmed:
            result.confirm_ms.append((time.perf_counter() - began) * 1000.0)
            value, unit = fee_from(receipt)
            if value is not None:
                result.fees.append(value)
                result.fee_unit = unit
        else:
            result.unconfirmed += 1

        # An anchor is only useful if it verifies. A platform that confirms but
        # returns a different digest is a failure, not a fast platform.
        if confirmed:
            verdict = adapter.verify(evidence_id, payload["digestValue"])
            if verdict != "match":
                result.failures[f"verify:{verdict}"] = result.failures.get(f"verify:{verdict}", 0) + 1

    return result


# ---------------------------------------------------------------------- energy


def read_meter(path: Path) -> list[tuple[float, float]]:
    """Read ``timestamp_iso8601,watts`` samples."""
    samples: list[tuple[float, float]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row or row[0].lower().startswith(("timestamp", "#")):
                continue
            stamp = time.mktime(time.strptime(row[0].split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S"))
            samples.append((stamp, float(row[1])))
    return sorted(samples)


def integrate_wh(samples: list[tuple[float, float]]) -> tuple[float, float]:
    """Return energy in watt hours and the covered duration in seconds."""
    if len(samples) < 2:
        return 0.0, 0.0
    joules = 0.0
    for (t0, w0), (t1, w1) in zip(samples, samples[1:], strict=False):
        joules += (w0 + w1) / 2.0 * (t1 - t0)
    return joules / 3600.0, samples[-1][0] - samples[0][0]


def energy_section(meter: Path | None, idle: Path | None, anchored: int) -> dict[str, Any]:
    if meter is None or idle is None:
        return {
            "status": "notMeasured",
            "reason": (
                "an energy figure requires a meter log of the campaign and an idle log of the "
                "same hardware with the service stopped; one or both were not supplied"
            ),
        }
    campaign, campaign_seconds = integrate_wh(read_meter(meter))
    idle_wh, idle_seconds = integrate_wh(read_meter(idle))
    if campaign_seconds <= 0 or idle_seconds <= 0:
        return {"status": "notMeasured", "reason": "a meter log covered no measurable interval"}
    idle_rate_w = idle_wh * 3600.0 / idle_seconds
    baseline_wh = idle_rate_w * campaign_seconds / 3600.0
    marginal_wh = campaign - baseline_wh
    return {
        "status": "measured",
        "campaignWh": round(campaign, 4),
        "campaignSeconds": round(campaign_seconds, 1),
        "idleDrawW": round(idle_rate_w, 2),
        "baselineWh": round(baseline_wh, 4),
        "marginalWh": round(marginal_wh, 4),
        "anchoredRecords": anchored,
        "marginalWhPerRecord": round(marginal_wh / anchored, 6) if anchored else None,
        "scope": (
            "the submitting node only; validator-side and network-wide energy are outside "
            "what a client can meter and are not reported"
        ),
    }


# ---------------------------------------------------------------------- report


def render(document: dict[str, Any]) -> str:
    lines = ["SORT4CIRC anchoring benchmark", "=" * 78]
    env = document["environment"]
    lines.append(f"host      {env['platform']}, Python {env['python']}")
    lines.append(f"captured  {env['capturedAt']}   runs per platform {document['runs']}")
    lines.append(f"payload   {document['payloadBytes']} bytes canonical, digest {document['digest'][:16]}...")
    lines.append("")
    header = f"{'platform':<24}{'status':<12}{'sub p50':>10}{'conf p50':>11}{'conf p95':>11}{'fail':>7}"
    lines.append(header)
    lines.append("-" * len(header))
    for entry in document["platforms"]:
        if entry["status"] != "measured":
            lines.append(f"{entry['platform']:<24}{entry['status']:<12}{'-':>10}{'-':>11}{'-':>11}{'-':>7}")
            lines.append(f"    {entry.get('reason', 'no reason recorded')}")
            continue
        sub = entry["submitLatency"]
        con = entry["timeToConfirmation"]
        fails = sum(entry["failures"].values())
        lines.append(
            f"{entry['platform']:<24}{entry['status']:<12}"
            f"{sub.get('p50Ms', 0):>10.1f}{con.get('p50Ms') or 0:>11.1f}"
            f"{con.get('p95Ms') or 0:>11.1f}{fails:>7}"
        )
    lines.append("")
    lines.append("latency in milliseconds; time to confirmation is measured from submission")
    lines.append("")
    energy = document["energy"]
    if energy["status"] == "measured":
        lines.append(
            f"energy: {energy['marginalWhPerRecord']} Wh per anchored record, "
            f"marginal over a {energy['idleDrawW']} W idle baseline"
        )
        lines.append(f"        scope: {energy['scope']}")
    else:
        lines.append(f"energy: not measured. {energy['reason']}")
    return "\n".join(lines)


# ------------------------------------------------------------------------ main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=None, help="platform configuration document")
    parser.add_argument("--self-test", action="store_true", help="exercise the harness against the in-memory adapter")
    parser.add_argument("--runs", type=int, default=None, help="override the configured run count")
    parser.add_argument("--json", dest="json_path", type=Path, default=None)
    parser.add_argument("--evidence-dir", type=Path, default=None, help="write a structured evidence envelope and raw result")
    parser.add_argument("--release-evidence", action="store_true", help="require a clean tree and mark evidence release-grade")
    parser.add_argument("--energy-csv", type=Path, default=None, help="meter log of the campaign")
    parser.add_argument("--energy-idle-csv", type=Path, default=None, help="meter log of the idle machine")
    args = parser.parse_args(argv)

    if not args.config and not args.self_test:
        parser.error("supply --config, or --self-test to exercise the harness")

    started_at = utcnow()
    if args.self_test:
        config = {
            "runs": args.runs or 25,
            "confirmationTimeoutSeconds": 10,
            "pollIntervalSeconds": 0.05,
            "platforms": [
                {
                    "name": "in-memory-reference",
                    "adapter": "sort4circ_dpp.ledger.memory:InMemoryLedger",
                    "finality": "not applicable, no network",
                }
            ],
        }
    else:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if args.runs:
            config["runs"] = args.runs

    runs = int(config.get("runs", 50))
    timeout_seconds = float(config.get("confirmationTimeoutSeconds", 300))
    poll_seconds = float(config.get("pollIntervalSeconds", 1.0))

    results: list[PlatformResult] = []
    for entry in config["platforms"]:
        name = entry["name"]
        try:
            adapter = load_adapter(entry["adapter"], entry.get("options") or {})
        except Exception as exc:  # noqa: BLE001
            result = PlatformResult(name=name, finality=entry.get("finality"))
            result.reason = f"adapter could not be loaded: {type(exc).__name__}: {exc}"
            results.append(result)
            continue
        results.append(
            measure(name, adapter, runs, timeout_seconds, poll_seconds, entry.get("finality"))
        )

    anchored = sum(len(r.confirm_ms) for r in results)
    document = {
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "capturedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "harness": "tools/anchor_bench.py",
            "selfTest": bool(args.self_test),
        },
        "runs": runs,
        "digest": digest(REFERENCE_RECORD),
        "payloadBytes": len(canonical_bytes(REFERENCE_RECORD)),
        "platforms": [r.document() for r in results],
        "energy": energy_section(args.energy_csv, args.energy_idle_csv, anchored),
    }
    if args.self_test:
        document["caveat"] = (
            "self test against the in-memory adapter; these figures describe this process "
            "and nothing about any distributed ledger"
        )

    print(render(document))
    if args.self_test:
        print("\n" + document["caveat"])
    if args.json_path:
        args.json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json_path}")
    if args.evidence_dir:
        raw_path = args.evidence_dir / "raw-result.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        failures = sum(sum(result.failures.values()) + result.unconfirmed for result in results)
        measured = sum(result.status == "measured" for result in results)
        evidence_verdict = "pass" if failures == 0 and measured == len(results) else "fail"
        evidence = build_record(
            root=ROOT,
            control_id="BC-01",
            test_name="ledger anchoring benchmark" if not args.self_test else "ledger adapter self-test",
            command="python " + " ".join(["tools/anchor_bench.py", *(argv or sys.argv[1:])]),
            tool="tools/anchor_bench.py",
            started_at=started_at,
            completed_at=utcnow(),
            exit_code=0,
            configuration=config,
            configuration_profile="local-in-memory-anchor-self-test" if args.self_test else "configured-ledger-anchor",
            dataset={
                "identifier": "annex-g-reference-record",
                "version": "1.0.0",
                "sha256": sha256_json(REFERENCE_RECORD),
                "fixtureCount": 1,
                "operationCount": runs * len(results),
                "payloadCharacteristics": {
                    "payloadBytes": len(canonical_bytes(REFERENCE_RECORD)),
                    "runsPerPlatform": runs,
                    "platformCount": len(results),
                },
            },
            target=0,
            target_unit="verification failures or unconfirmed submissions",
            acceptance_rule="all configured platforms are measured and every confirmed digest verifies",
            observed_result=failures,
            observed_unit="verification failures or unconfirmed submissions",
            verdict=evidence_verdict,
            raw_result_path=raw_path,
            reason=document.get("caveat") if args.self_test else None,
            summary_metrics={
                "configuredPlatforms": len(results),
                "measuredPlatforms": measured,
                "anchoredRecords": anchored,
                "failuresOrUnconfirmed": failures,
            },
            release_mode=args.release_evidence,
        )
        write_record(evidence, args.evidence_dir / "evidence.json")
        print(f"wrote {args.evidence_dir / 'evidence.json'}")

    unreached = [r.name for r in results if r.status != "measured"]
    if unreached and not args.self_test:
        print("\nnot measured: " + ", ".join(unreached))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
