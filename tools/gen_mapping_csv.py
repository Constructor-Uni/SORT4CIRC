"""Generate or verify the CSV projection of the authoritative mapping JSON."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "spec" / "mappings" / "dpp-mapping-1.0.0.json"
TARGET = ROOT / "spec" / "mappings" / "dpp-mapping-1.0.0.csv"
FIELDS = (
    "mappingId", "mappingVersion", "jsonPath", "xmlXPath", "rdfSubjectType",
    "rdfProperty", "rdfConstruct", "rdfMappingStatus", "rdfMappingReason",
    "datatype", "cardinality", "obligation",
    "controlledVocabulary", "unitRule", "source", "semanticMeaning", "notes",
)


def render() -> str:
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in document["rows"]:
        writer.writerow(
            {field: row.get(field) if row.get(field) is not None else "" for field in FIELDS}
            | {"mappingVersion": document["mappingVersion"]}
        )
    return handle.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the checked-in CSV is stale")
    args = parser.parse_args(argv)
    rendered = render()
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding="utf-8") != rendered:
            print(f"{TARGET.relative_to(ROOT)} is stale; run {Path(__file__).relative_to(ROOT)}")
            return 1
        print(f"{TARGET.relative_to(ROOT)} matches the authoritative mapping")
        return 0
    TARGET.write_text(rendered, encoding="utf-8", newline="")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
