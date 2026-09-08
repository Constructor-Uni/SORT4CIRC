"""Validate, digest and inspect synthetic public-profile records."""
import argparse
import json
from pathlib import Path

from .canonical import canonical_bytes, digest
from .reasons import DppError
from .synthetic import SyntheticFixtureFactory
from .validation import validate_payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("example", help="print an independently synthetic passport")
    for name in ("validate", "digest"):
        command = sub.add_parser(name)
        command.add_argument("file", type=Path)
        if name == "digest":
            command.add_argument("--show-projection", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "example":
        print(json.dumps(SyntheticFixtureFactory().passport(), indent=2))
        return 0
    document = json.loads(args.file.read_text(encoding="utf-8"))
    try:
        validate_payload(document)
    except DppError as exc:
        print("INVALID", exc.code)
        return 1
    if args.command == "validate":
        print("VALID")
    else:
        if args.show_projection:
            print(canonical_bytes(document).decode("utf-8"))
        print(digest(document))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
