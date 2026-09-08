"""Synthetic example. Not SORT4CIRC project data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient  # noqa: E402

from sort4circ_dpp.api import create_app  # noqa: E402
from sort4circ_dpp.auth import DemoAuth  # noqa: E402
from sort4circ_dpp.synthetic import SyntheticFixtureFactory  # noqa: E402
from sort4circ_dpp.validation import validate_payload  # noqa: E402


def main():
    factory = SyntheticFixtureFactory()
    validate_payload(factory.passport())
    app = create_app(auth_provider=DemoAuth())
    client = TestClient(app)
    manufacturer = {"X-DPP-Role": "brand", "X-DPP-Organisation": "urn:example:org:manufacturer-a"}
    collector = {"X-DPP-Role": "collector", "X-DPP-Organisation": "urn:example:org:collector-a"}
    record = client.post("/v1/dpps", json=factory.passport(), headers=manufacturer)
    record.raise_for_status()
    identifier = record.json()["dppId"]
    client.post(f"/v1/dpps/{identifier}/carriers", json=factory.carrier(), headers=manufacturer).raise_for_status()
    resolved = client.get("/v1/identifiers/urn%3Aexample%3Acarrier%3A000001/dpp", headers=manufacturer)
    resolved.raise_for_status()
    assert resolved.json()["dppId"] == identifier
    client.post(f"/v1/dpps/{identifier}/events", json=factory.event(), headers=collector).raise_for_status()
    client.post(f"/v1/dpps/{identifier}/observations", json=factory.observation(), headers=manufacturer).raise_for_status()
    # Local worker operation, deliberately absent from the exchange API.
    app.state.worker.drain()
    evidence_id = app.state.store.outbox[-1].evidence_id
    result = client.post(f"/v1/dpps/{identifier}/integrity/verify",
                         json={"evidenceId": evidence_id}, headers={"X-DPP-Role": "integrityVerifier"})
    result.raise_for_status()
    assert result.json()["verdict"] == "match"
    print("Synthetic example. Not SORT4CIRC project data.")
    print("Created, validated, resolved and updated a fictional passport; mock integrity verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
