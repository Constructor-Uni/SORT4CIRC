"""Generate the CC BY 4.0 OpenAPI specification from the application definition."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from sort4circ_dpp.api import create_app  # noqa: E402
from sort4circ_dpp.config import API_MAJOR  # noqa: E402


def document():
    """Build the contract from the application, without inheriting previous metadata.

    FastAPI models the JSON request and response bodies. The profile additionally offers
    the same complete passport record as ``application/xml``, validated against the
    released XSD before conversion, so that negotiated representation is added here. It
    is added only where a whole record is exchanged, never for a partial or projected
    payload.
    """
    doc = create_app().openapi()
    doc["externalDocs"] = {
        "description": "SORT4CIRC DPP Development Guidelines",
        "url": "https://github.com/Constructor-Uni/SORT4CIRC",
    }
    create = doc["paths"][f"/{API_MAJOR}/dpps"]["post"]
    record_schema = create["requestBody"]["content"]["application/json"]["schema"]
    create["requestBody"]["content"]["application/xml"] = {"schema": record_schema}
    create["responses"]["201"]["content"]["application/xml"] = {"schema": record_schema}
    read = doc["paths"][f"/{API_MAJOR}/dpps/{{dpp_id}}"]["get"]
    read["responses"]["200"]["content"]["application/xml"] = {"schema": record_schema}
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    target = ROOT / "spec/openapi/dpp-api-v1.json"
    value = document()
    if args.check:
        return int(json.loads(target.read_text(encoding="utf-8")) != value)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("Public OpenAPI generated with the CC BY 4.0 specification licence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
