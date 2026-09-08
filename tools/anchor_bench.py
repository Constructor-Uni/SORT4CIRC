"""Exercise the mock integrity contract using independently fictional data.

This is a correctness exercise, not a deployed-network benchmark.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sort4circ_dpp.canonical import digest  # noqa: E402
from sort4circ_dpp.ledger.memory import InMemoryLedger  # noqa: E402
from sort4circ_dpp.synthetic import SyntheticFixtureFactory  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args(argv)
    if not 1 <= args.runs <= 10000:
        parser.error("run count outside the example range")
    backend = InMemoryLedger()
    for number in range(1, args.runs + 1):
        record = SyntheticFixtureFactory().passport(number)
        value = digest(record)
        identifier = f"urn:example:integrity:{number:06d}"
        backend.submit(identifier, {
            "evidenceId": identifier, "subjectRef": record["dppId"],
            "subjectVersion": record["recordVersion"], "digestValue": value,
            "createdAt": record["updatedAt"],
        })
        if backend.verify(identifier, value) != "match":
            return 1
    print("Synthetic mock integrity checks passed; no external service was contacted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
