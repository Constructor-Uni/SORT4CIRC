"""Generate the owner-approved CC BY 4.0 OpenAPI specification from the app."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sort4circ_dpp.api import create_app  # noqa: E402


def document():
    """Use the application contract, without inheriting previous licence metadata."""
    return create_app().openapi()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    target = ROOT / "spec/openapi/dpp-api-v1.json"
    value = document()
    if args.check:
        return int(json.loads(target.read_text(encoding="utf-8")) != value)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("Public OpenAPI generated with the approved CC BY 4.0 licence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
