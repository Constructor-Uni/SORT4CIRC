"""Shared fixtures.

Every test builds its own service instance. State is never shared between
tests, so a failure is always attributable to the test that produced it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("S4C_ALLOW_HEADER_AUTH", "1")

from fastapi.testclient import TestClient  # noqa: E402

from sort4circ_dpp.api import create_app  # noqa: E402
from sort4circ_dpp.ledger.memory import InMemoryLedger  # noqa: E402
from sort4circ_dpp.store import PassportStore  # noqa: E402

EPC = "urn:epc:id:sgtin:0614141.112345.400"
EPC_ENCODED = EPC.replace(":", "%3A")

HEADERS = {
    "brand": {"X-S4C-Role": "brand", "X-S4C-Organisation": "urn:sort4circ:org:brand-a"},
    "pssrSystem": {"X-S4C-Role": "pssrSystem", "X-S4C-Organisation": "urn:sort4circ:org:pssr-a"},
    "sortingOperator": {"X-S4C-Role": "sortingOperator"},
    "consumer": {"X-S4C-Role": "consumer"},
    "recycler": {"X-S4C-Role": "recycler"},
    "authority": {"X-S4C-Role": "authority"},
    "administrator": {"X-S4C-Role": "administrator"},
    "integrityVerifier": {"X-S4C-Role": "integrityVerifier"},
    "collector": {"X-S4C-Role": "collector", "X-S4C-Organisation": "urn:sort4circ:org:collector-a"},
}


def passport_payload(**overrides):
    payload = {
        "schemaVersion": "1.0.0",
        "identity": {
            "granularity": "item",
            "itemId": "urn:sort4circ:item:000001",
            "sampleId": "TXHO-WP3-B01-001",
        },
        "product": {
            "articleClass": "upperBodyKnitwear",
            "fabricConstruction": "knitted",
            "colourPrimary": "dark",
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
        "responsibleOperatorId": "urn:sort4circ:org:brand-a",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def store() -> PassportStore:
    return PassportStore()


@pytest.fixture
def ledger() -> InMemoryLedger:
    return InMemoryLedger()


@pytest.fixture
def client(store, ledger) -> TestClient:
    return TestClient(create_app(store=store, ledger=ledger))


@pytest.fixture
def dpp_id(client) -> str:
    response = client.post("/v1/dpps", json=passport_payload(), headers=HEADERS["brand"])
    assert response.status_code == 201
    return response.json()["dppId"]


@pytest.fixture
def bound_dpp(client, dpp_id) -> str:
    client.post(
        f"/v1/dpps/{dpp_id}/carriers",
        json={
            "carrierType": "uhfRfid",
            "encodingScheme": "gs1Sgtin96",
            "encodedIdentifier": EPC,
            "boundBy": "urn:sort4circ:org:brand-a",
        },
        headers=HEADERS["brand"],
    ).raise_for_status()
    return dpp_id
