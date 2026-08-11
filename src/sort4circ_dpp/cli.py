"""Command line entry points.

Four commands cover the operations an implementer needs outside a service:
validate a record, compute a digest, verify a digest against an expected value,
and print the derived latency budget for a line configuration.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, digest, integrity_projection
from .config import SOFTWARE_BUDGET_MS
from .reasons import DppError, catalogue
from .validation import validate_payload


def _load(path: str) -> dict[str, Any]:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_validate(args: argparse.Namespace) -> int:
    record = _load(args.file)
    try:
        validate_payload(record)
    except DppError as exc:
        print(f"INVALID {exc.code}: {exc.detail}", file=sys.stderr)
        for path in exc.fields:
            print(f"  at {path}", file=sys.stderr)
        return 1
    print("VALID")
    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    record = _load(args.file)
    projection = integrity_projection(record)
    if args.show_projection:
        print(canonical_bytes(record).decode("utf-8"))
    print(f"bytes  {len(canonical_bytes(record))}")
    print(f"sha256 {digest(record)}")
    if args.expect:
        matched = digest(record) == args.expect.lower()
        print(f"verdict {'match' if matched else 'mismatch'}")
        return 0 if matched else 2
    _ = projection
    return 0


def cmd_budget(args: argparse.Namespace) -> int:
    """Derive the software budget from a line configuration.

    Every number a deployment publishes should come out of this calculation
    rather than out of a generic claim.
    """
    transit_ms = (args.distance_m / args.speed_mps) * 1000.0
    margin_ms = transit_ms * (args.margin_percent / 100.0)
    overheads = args.reader_ms + args.gateway_settle_ms + args.network_ms + args.controller_ms
    budget = transit_ms - overheads - margin_ms
    print(f"transit           {transit_ms:8.0f} ms   ({args.distance_m} m at {args.speed_mps} m/s)")
    print(f"reader decode     {args.reader_ms:8.0f} ms")
    print(f"gateway settle    {args.gateway_settle_ms:8.0f} ms")
    print(f"OT network        {args.network_ms:8.0f} ms")
    print(f"controller        {args.controller_ms:8.0f} ms")
    print(f"safety margin     {margin_ms:8.0f} ms   ({args.margin_percent} percent of transit)")
    print(f"software budget   {budget:8.0f} ms")
    if budget <= 0:
        print("the line leaves no software budget; the read point must move upstream", file=sys.stderr)
        return 1
    print(f"reference budget  {SOFTWARE_BUDGET_MS:8.0f} ms   (D4.3 reference configuration)")
    return 0


def cmd_codes(args: argparse.Namespace) -> int:
    for code, entry in sorted(catalogue().items()):
        print(f"{code:<38} {entry.http_status:>3}  {entry.safe_action:<24} {entry.condition}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="s4c-dpp", description="SORT4CIRC Digital Product Passport tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate a passport record against the schema and vocabularies")
    p.add_argument("file", help="path to a JSON record, or - for standard input")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("digest", help="compute the integrity digest of a passport record")
    p.add_argument("file", help="path to a JSON record, or - for standard input")
    p.add_argument("--expect", help="compare against this digest and report a verdict")
    p.add_argument("--show-projection", action="store_true", help="print the canonical byte sequence")
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("budget", help="derive the software latency budget for a sorting line")
    p.add_argument("--speed-mps", type=float, default=1.5)
    p.add_argument("--distance-m", type=float, default=2.40)
    p.add_argument("--reader-ms", type=float, default=150)
    p.add_argument("--gateway-settle-ms", type=float, default=60)
    p.add_argument("--network-ms", type=float, default=30)
    p.add_argument("--controller-ms", type=float, default=120)
    p.add_argument("--margin-percent", type=float, default=20)
    p.set_defaults(func=cmd_budget)

    p = sub.add_parser("codes", help="list the released reason codes and their safe actions")
    p.set_defaults(func=cmd_codes)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
