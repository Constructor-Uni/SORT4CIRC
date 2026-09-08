"""Shared independently fictional examples."""
import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from sort4circ_dpp.api import create_app  # noqa: E402
from sort4circ_dpp.auth import DemoAuth  # noqa: E402
from sort4circ_dpp.ledger.memory import InMemoryLedger  # noqa: E402
from sort4circ_dpp.store import PassportStore  # noqa: E402
from sort4circ_dpp.synthetic import SyntheticFixtureFactory  # noqa: E402

EPC = "urn:example:carrier:000001"
EPC_ENCODED = EPC.replace(":", "%3A")
HEADERS = {
    role: {"X-DPP-Role": role, "X-DPP-Organisation": f"urn:example:org:{org}"}
    for role, org in {
        "brand": "manufacturer-a", "externalSystem": "sorter-a",
        "sortingOperator": "sorter-a", "consumer": "consumer-a", "recycler": "recycler-a",
        "authority": "authority-a", "administrator": "admin-a",
        "integrityVerifier": "verifier-a", "collector": "collector-a",
    }.items()
}


def passport_payload(**overrides):
    payload = copy.deepcopy(SyntheticFixtureFactory().passport())
    # Runtime-created record identities are distinct from the deterministic vector.
    for name in ("dppId", "recordVersion", "createdAt", "updatedAt"):
        payload.pop(name)
    payload.update(overrides)
    return payload


@pytest.fixture
def store():
    return PassportStore()


@pytest.fixture
def ledger():
    return InMemoryLedger()


@pytest.fixture
def client(store, ledger):
    return TestClient(create_app(store=store, ledger=ledger, auth_provider=DemoAuth()))


@pytest.fixture
def dpp_id(client):
    response = client.post("/v1/dpps", json=passport_payload(), headers=HEADERS["brand"])
    response.raise_for_status()
    return response.json()["dppId"]


@pytest.fixture
def bound_dpp(client, dpp_id):
    response = client.post(
        f"/v1/dpps/{dpp_id}/carriers",
        json=SyntheticFixtureFactory().carrier(),
        headers=HEADERS["brand"],
    )
    response.raise_for_status()
    return dpp_id
