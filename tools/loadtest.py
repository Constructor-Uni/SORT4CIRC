"""Load campaign against the reference DPP service.

Purpose
-------
Deliverable D4.3 derives a software budget of 920 ms for the sorting path from
the conveyor geometry: 2.40 m of instrumented transit at 1.5 m/s leaves 1600 ms
between the read and the diverter, of which the read zone, the network and the
actuator claim the remainder. This script measures how much of that budget the
reference service actually consumes, so the budget stops being an assertion.

What is measured
----------------
Four request classes, each at several concurrency levels:

``resolve``       GET /v1/identifiers/{epc}/dpp?view=sorting
                  The time-critical path. A carrier identifier arrives from the
                  read zone and a sorting projection must come back.
``sortingView``   GET /v1/dpps/{id}/sorting-view
                  The same projection reached by passport identifier.
``observation``   POST /v1/dpps/{id}/observations
                  The write path: schema validation, vocabulary validation,
                  composition checking, version increment, digest calculation
                  and an outbox entry, committed together.
``search``        GET /v1/dpps?limit=50
                  Cursor pagination over the collection.

What is not measured
--------------------
The reference store is in-memory with a snapshot option, so no database round
trip, no disk flush and no replication delay appears in these figures. The
numbers are therefore a floor for the service logic, not a forecast of a
production deployment. A deployment that substitutes a relational store must
re-run this script and add the storage cost to the observed figures before
claiming the budget is met. The same applies to the ledger: the outbox is
drained against the in-memory adapter, which measures the outbox machinery and
nothing about any chain.

Requests are issued over a real HTTP socket to a uvicorn server, not through the
in-process test client, so serialisation, routing, header handling and the
socket are all inside the measurement.

Usage
-----
    python tools/loadtest.py                       # default campaign
    python tools/loadtest.py --passports 500 --requests 3000 --concurrency 1,2,4,8
    python tools/loadtest.py --json results.json   # machine-readable output

Exit status is non-zero when any request class reports an error, so the script
can be wired into a pipeline.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("S4C_ALLOW_HEADER_AUTH", "1")

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from sort4circ_dpp.api import create_app  # noqa: E402

BRAND = {
    "X-S4C-Role": "brand",
    "X-S4C-Subject": "load-brand",
    "X-S4C-Organisation": "urn:sort4circ:org:brand-a",
}
PSSR = {
    "X-S4C-Role": "pssrSystem",
    "X-S4C-Subject": "load-nir",
    "X-S4C-Organisation": "urn:sort4circ:org:pssr-partner-a",
}
SORTER = {"X-S4C-Role": "sortingOperator", "X-S4C-Subject": "load-sorter"}
ADMIN = {"X-S4C-Role": "administrator", "X-S4C-Subject": "load-ops"}

#: Software budget for the sorting path, deliverable D4.3, latency derivation.
SOFTWARE_BUDGET_MS = 920.0


# --------------------------------------------------------------------- server


class _Server(uvicorn.Server):
    def install_signal_handlers(self) -> None:  # the server runs in a thread
        return


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_server(port: int, workers_note: str) -> tuple[_Server, threading.Thread]:
    config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
        workers=1,
    )
    server = _Server(config)
    thread = threading.Thread(target=server.run, name=workers_note, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30.0
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("server did not start within 30 s")
        time.sleep(0.02)
    return server, thread


# ---------------------------------------------------------------- environment


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def memory_gib() -> float:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal"):
                return round(int(line.split()[1]) / (1024.0 * 1024.0), 1)
    except Exception:
        pass
    return 0.0


def environment() -> dict[str, Any]:
    return {
        "cpuModel": cpu_model(),
        "cpuCount": os.cpu_count(),
        "memoryGiB": memory_gib(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "commit": git_commit(),
        "serverProcesses": 1,
        "storeBacking": "in-memory reference store, no database round trip",
        "ledgerAdapter": "in-memory, no chain interaction",
        "capturedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ------------------------------------------------------------------- fixtures


def epc_for(index: int) -> str:
    return f"urn:epc:id:sgtin:0614141.112345.{index:06d}"


def passport_payload(index: int) -> dict[str, Any]:
    return {
        "dppId": f"urn:sort4circ:dpp:load{index:06d}",
        "schemaVersion": "1.0.0",
        "identity": {
            "granularity": "item",
            "itemId": f"urn:sort4circ:item:load{index:06d}",
            "modelId": "MOD-SW-2026-0042",
        },
        "product": {
            "articleClass": "upperBodyKnitwear",
            "fabricConstruction": "knitted",
            "colourPrimary": "dark",
            "technicalFlags": ["carbonBlackPresent", "hardPointZipMetal"],
        },
        "materialObservations": [
            {
                "observationId": f"urn:sort4circ:obs:load{index:06d}a",
                "fibreType": "polyester",
                "percentage": 95,
                "percentageBasis": "mass",
                "valueStatus": "supplied",
                "method": "labQuantitativeIso1833",
                "sourceOrganisationId": "urn:sort4circ:org:txho",
                "observedAt": "2026-06-18T11:02:10Z",
            },
            {
                "observationId": f"urn:sort4circ:obs:load{index:06d}b",
                "fibreType": "elastane",
                "percentage": 5,
                "percentageBasis": "mass",
                "valueStatus": "supplied",
                "method": "labQuantitativeIso1833",
                "sourceOrganisationId": "urn:sort4circ:org:txho",
                "observedAt": "2026-06-18T11:02:10Z",
            },
        ],
        "responsibleOperatorId": "urn:sort4circ:org:brand-a",
    }


def carrier_payload(index: int) -> dict[str, Any]:
    return {
        "carrierType": "uhfRfid",
        "encodingScheme": "gs1Sgtin96",
        "encodedIdentifier": epc_for(index),
        "resolverUri": f"https://id.sort4circ.eu/01/00614141123456/21/{index:06d}",
        "placement": "sideSeamInternal",
        "boundBy": "urn:sort4circ:org:brand-a",
    }


def observation_payload(index: int, sequence: int) -> dict[str, Any]:
    """A near-infrared reading that disagrees with the laboratory figure.

    Each generated observation carries a distinct ``observedAt``, so each one
    forms its own observation set. That matters: the composition rule applies
    per set, and repeating one instant would correctly be refused as a set whose
    supplied mass fractions exceed 100 percent.
    """
    minute, second = divmod(sequence, 60)
    hour, minute = divmod(minute, 60)
    return {
        "observationId": f"urn:sort4circ:obs:load{index:06d}n{sequence:07d}",
        "fibreType": "polyester",
        "percentage": 93.4,
        "percentageBasis": "mass",
        "valueStatus": "supplied",
        "method": "nirSpectroscopy",
        "sourceOrganisationId": "urn:sort4circ:org:pssr-partner-a",
        "sourceSystemId": "urn:sort4circ:system:nir-line-2",
        "observedAt": f"2026-08-10T{hour % 24:02d}:{minute:02d}:{second:02d}.000Z",
        "confidence": {"value": 0.87, "scale": "unitInterval"},
    }


def seed(base: str, count: int) -> list[str]:
    """Create ``count`` passports, each with one commissioned carrier."""
    identifiers: list[str] = []
    with httpx.Client(base_url=base, timeout=60.0) as client:
        for index in range(count):
            created = client.post("/v1/dpps", headers=BRAND, json=passport_payload(index))
            created.raise_for_status()
            dpp_id = created.json()["dppId"]
            commissioned = client.post(
                f"/v1/dpps/{dpp_id}/carriers", headers=BRAND, json=carrier_payload(index)
            )
            commissioned.raise_for_status()
            identifiers.append(dpp_id)
    return identifiers


# ----------------------------------------------------------------- statistics


def percentile(ordered: list[float], fraction: float) -> float:
    """Nearest-rank percentile over an already sorted sample."""
    if not ordered:
        return float("nan")
    rank = max(1, min(len(ordered), int(round(fraction * len(ordered) + 0.5))))
    return ordered[rank - 1]


@dataclass
class Outcome:
    latencies_ms: list[float] = field(default_factory=list)
    statuses: dict[int, int] = field(default_factory=dict)
    wall_seconds: float = 0.0

    def summary(self) -> dict[str, Any]:
        ordered = sorted(self.latencies_ms)
        errors = sum(count for status, count in self.statuses.items() if status >= 400 or status == 0)
        return {
            "requests": len(ordered),
            "errors": errors,
            "statuses": {str(k): v for k, v in sorted(self.statuses.items())},
            "wallSeconds": round(self.wall_seconds, 3),
            "throughputPerSecond": round(len(ordered) / self.wall_seconds, 1) if self.wall_seconds else 0.0,
            "meanMs": round(statistics.fmean(ordered), 3) if ordered else None,
            "p50Ms": round(percentile(ordered, 0.50), 3),
            "p90Ms": round(percentile(ordered, 0.90), 3),
            "p95Ms": round(percentile(ordered, 0.95), 3),
            "p99Ms": round(percentile(ordered, 0.99), 3),
            "maxMs": round(ordered[-1], 3) if ordered else None,
        }


def drive(
    base: str,
    call: Callable[[httpx.Client, int], httpx.Response],
    total: int,
    concurrency: int,
) -> Outcome:
    """Issue ``total`` requests spread over ``concurrency`` client threads."""
    outcome = Outcome()
    lock = threading.Lock()
    per_thread = total // concurrency
    start_barrier = threading.Barrier(concurrency + 1)

    def worker(worker_index: int) -> None:
        local_latencies: list[float] = []
        local_statuses: dict[int, int] = {}
        with httpx.Client(base_url=base, timeout=60.0) as client:
            # One untimed request warms the connection so that TCP setup does
            # not land inside the first measured sample. Its outcome is
            # deliberately ignored: it is not part of the sample.
            with contextlib.suppress(Exception):
                call(client, worker_index * per_thread)
            start_barrier.wait()
            for step in range(per_thread):
                index = worker_index * per_thread + step
                began = time.perf_counter()
                try:
                    response = call(client, index)
                    status = response.status_code
                except Exception:
                    status = 0
                elapsed = (time.perf_counter() - began) * 1000.0
                local_latencies.append(elapsed)
                local_statuses[status] = local_statuses.get(status, 0) + 1
        with lock:
            outcome.latencies_ms.extend(local_latencies)
            for status, count in local_statuses.items():
                outcome.statuses[status] = outcome.statuses.get(status, 0) + count

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(concurrency)]
    for thread in threads:
        thread.start()
    start_barrier.wait()
    began = time.perf_counter()
    for thread in threads:
        thread.join()
    outcome.wall_seconds = time.perf_counter() - began
    return outcome


# ------------------------------------------------------------------ scenarios


def scenarios(identifiers: list[str], passports: int) -> dict[str, Callable[[httpx.Client, int], httpx.Response]]:
    count = len(identifiers)
    write_sequence = iter(range(10_000_000))
    sequence_lock = threading.Lock()

    def next_sequence() -> int:
        with sequence_lock:
            return next(write_sequence)

    def resolve(client: httpx.Client, index: int) -> httpx.Response:
        encoded = epc_for(index % passports).replace(":", "%3A")
        return client.get(f"/v1/identifiers/{encoded}/dpp?view=sorting", headers=PSSR)

    def sorting_view(client: httpx.Client, index: int) -> httpx.Response:
        return client.get(f"/v1/dpps/{identifiers[index % count]}/sorting-view", headers=SORTER)

    def observation(client: httpx.Client, index: int) -> httpx.Response:
        target = index % count
        return client.post(
            f"/v1/dpps/{identifiers[target]}/observations",
            headers=PSSR,
            json=observation_payload(target, next_sequence()),
        )

    def search(client: httpx.Client, index: int) -> httpx.Response:
        return client.get("/v1/dpps?limit=50", headers=ADMIN)

    return {
        "resolve": resolve,
        "sortingView": sorting_view,
        "observation": observation,
        "search": search,
    }


def drain_outbox(base: str) -> dict[str, Any]:
    """Drain the evidence outbox once and report the cost of the machinery.

    Every accepted write commits an outbox entry in the same transaction as the
    passport update, so by this point the queue holds one entry per version
    produced during the campaign. The first drain does the work; a second drain
    is timed as well, because entries in a terminal state are skipped and the
    difference shows the cost of the scan by itself.
    """
    with httpx.Client(base_url=base, timeout=600.0) as client:
        began = time.perf_counter()
        first = client.post("/v1/internal/evidence/drain", headers=ADMIN)
        first_ms = (time.perf_counter() - began) * 1000.0
        began = time.perf_counter()
        client.post("/v1/internal/evidence/drain", headers=ADMIN)
        second_ms = (time.perf_counter() - began) * 1000.0
    states = first.json().get("states", {}) if first.status_code < 400 else {}
    entries = sum(states.values())
    return {
        "status": first.status_code,
        "states": states,
        "entries": entries,
        "wallMs": round(first_ms, 3),
        "perEntryMs": round(first_ms / entries, 4) if entries else None,
        "rescanMs": round(second_ms, 3),
        "confirmed": states.get("confirmed", 0),
        "note": "in-memory ledger adapter; measures the outbox, not any chain",
    }


# --------------------------------------------------------------------- report


def render(results: dict[str, Any]) -> str:
    lines: list[str] = []
    env = results["environment"]
    lines.append("SORT4CIRC reference DPP service, load campaign")
    lines.append("=" * 78)
    lines.append(f"host        {env['cpuModel']}, {env['cpuCount']} cores, {env['memoryGiB']} GiB")
    lines.append(f"runtime     Python {env['python']} on {env['platform']}")
    lines.append(f"revision    {env['commit']}   captured {env['capturedAt']}")
    lines.append(f"store       {env['storeBacking']}")
    lines.append(f"ledger      {env['ledgerAdapter']}")
    lines.append(f"seeded      {results['seed']['passports']} passports, "
                 f"{results['seed']['wallSeconds']} s, "
                 f"{results['seed']['perPassportMs']} ms per passport")
    lines.append("")
    header = f"{'class':<13}{'conc':>5}{'reqs':>7}{'err':>5}{'req/s':>10}{'p50':>9}{'p95':>9}{'p99':>9}{'max':>9}"
    lines.append(header)
    lines.append("-" * len(header))
    for name, by_concurrency in results["scenarios"].items():
        for concurrency, summary in by_concurrency.items():
            lines.append(
                f"{name:<13}{concurrency:>5}{summary['requests']:>7}{summary['errors']:>5}"
                f"{summary['throughputPerSecond']:>10.1f}{summary['p50Ms']:>9.2f}"
                f"{summary['p95Ms']:>9.2f}{summary['p99Ms']:>9.2f}{summary['maxMs']:>9.2f}"
            )
    lines.append("")
    lines.append("latency in milliseconds, measured at the client over a loopback socket")
    lines.append("")
    verdict = results["budget"]
    lines.append(f"software budget for the sorting path: {verdict['budgetMs']} ms")
    lines.append(
        f"resolve p99 at concurrency {verdict['atConcurrency']}: {verdict['observedP99Ms']} ms, "
        f"{verdict['headroomPercent']} percent of the budget unused"
    )
    lines.append("")
    drain = results["outboxDrain"]
    lines.append(
        f"outbox drain: {drain['entries']} entries in {drain['wallMs']} ms "
        f"({drain['perEntryMs']} ms per entry), {drain['confirmed']} confirmed; "
        f"rescan of the drained queue {drain['rescanMs']} ms"
    )
    lines.append(f"             {drain['note']}")
    return "\n".join(lines)


# ----------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--passports", type=int, default=200, help="passports to seed (default 200)")
    parser.add_argument("--requests", type=int, default=2000, help="requests per class per level (default 2000)")
    parser.add_argument("--concurrency", default="1,2,4,8", help="comma-separated levels (default 1,2,4,8)")
    parser.add_argument("--json", dest="json_path", default=None, help="write the full result document here")
    args = parser.parse_args(argv)

    levels = [int(value) for value in args.concurrency.split(",") if value.strip()]
    port = free_port()
    server, thread = start_server(port, "s4c-loadtest")
    base = f"http://127.0.0.1:{port}"

    try:
        began = time.perf_counter()
        identifiers = seed(base, args.passports)
        seed_seconds = time.perf_counter() - began

        cases = scenarios(identifiers, args.passports)
        results: dict[str, Any] = {
            "environment": environment(),
            "seed": {
                "passports": len(identifiers),
                "wallSeconds": round(seed_seconds, 3),
                "perPassportMs": round(seed_seconds * 1000.0 / max(1, len(identifiers)), 3),
            },
            "scenarios": {},
        }

        for name, call in cases.items():
            results["scenarios"][name] = {}
            for level in levels:
                total = (args.requests // level) * level
                outcome = drive(base, call, total, level)
                results["scenarios"][name][level] = outcome.summary()

        results["outboxDrain"] = drain_outbox(base)

        reference_level = levels[0]
        observed = results["scenarios"]["resolve"][reference_level]["p99Ms"]
        results["budget"] = {
            "budgetMs": SOFTWARE_BUDGET_MS,
            "atConcurrency": reference_level,
            "observedP99Ms": observed,
            "headroomPercent": round(100.0 * (SOFTWARE_BUDGET_MS - observed) / SOFTWARE_BUDGET_MS, 2),
            "caveat": (
                "in-memory store and loopback network; a deployment with a database, "
                "a real network and a hardware read zone must repeat this measurement"
            ),
        }

        report = render(results)
        print(report)
        if args.json_path:
            Path(args.json_path).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
            print(f"\nwrote {args.json_path}")

        failures = sum(
            summary["errors"]
            for by_level in results["scenarios"].values()
            for summary in by_level.values()
        )
        return 1 if failures else 0
    finally:
        server.should_exit = True
        thread.join(timeout=15)


if __name__ == "__main__":
    raise SystemExit(main())
