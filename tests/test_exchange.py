"""JSON/XML/RDF exchange alignment required by D4.3."""

from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

import pytest
import xmlschema
from rdflib import Graph

from sort4circ_dpp.exchange import from_xml, to_rdf, to_xml, validate_xml

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "fixtures" / "valid-annex-g-garment.json"
DIVERGENCE_FIXTURE = ROOT / "examples" / "fixtures" / "valid-two-technologies-disagree.json"
XML_FIXTURE = ROOT / "examples" / "fixtures" / "xml" / "valid-annex-g-garment.xml"
QUERIES = ROOT / "spec" / "queries"


def load_record() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_divergence_record() -> dict:
    return json.loads(DIVERGENCE_FIXTURE.read_text(encoding="utf-8"))


def complete_record() -> dict:
    record = load_divergence_record()
    record["carriers"] = [{
        "carrierId": "urn:sort4circ:binding:000001", "carrierType": "uhfRfid",
        "encodingScheme": "gs1Sgtin96", "encodedIdentifier": record["identity"]["epc"],
        "bindingStatus": "commissioned", "boundAt": "2026-08-10T09:00:00Z",
        "boundBy": "urn:sort4circ:org:brand-a",
    }]
    record["components"] = [{"componentId": "urn:sort4circ:component:zip", "componentType": "zip", "separable": True}]
    record["lifecycleEvents"] = [{
        "eventId": "urn:sort4circ:event:collection", "eventType": "collection",
        "eventTime": "2026-08-10T09:00:00Z", "eventTimeZoneOffset": "+02:00",
        "recordedAt": "2026-08-10T09:00:01Z", "actorOrganisationId": "urn:sort4circ:org:collector",
        "sourceSystemId": "urn:sort4circ:system:gate",
    }]
    record["sortingDecisions"] = [{
        "decisionId": "urn:sort4circ:decision:1", "basedOnObservations": ["urn:sort4circ:obs:000001"],
        "basedOnRecordVersion": 1, "ruleSetId": "urn:sort4circ:rules:1", "ruleSetVersion": "1.0.0",
        "sortingCategory": "mechanicalRecyclingFibre", "decidedAt": "2026-08-10T09:00:02Z",
        "decidedBy": "urn:sort4circ:system:sorter", "outcomeStatus": "issued",
    }]
    record["environmentalValues"] = [{
        "metricType": "globalWarmingPotential", "quantity": {"value": 1.2, "unit": "kgCO2e"},
        "functionalUnit": "one garment", "systemBoundary": "cradleToGate", "processStage": "production",
        "geography": "EU", "periodStart": "2026-01-01", "periodEnd": "2026-12-31",
        "method": "iso14067ProductCarbonFootprint", "allocationRule": "mass",
        "factorSource": "synthetic contract fixture", "factorVersion": "fixture-1",
        "responsibleOrganisationId": "urn:sort4circ:org:brand-a",
    }]
    return record


def test_xsd_accepts_valid_and_rejects_invalid_xml():
    validate_xml(XML_FIXTURE.read_bytes())
    invalid = ROOT / "examples" / "fixtures" / "xml" / "invalid-observation-without-method.xml"
    with pytest.raises(xmlschema.XMLSchemaValidationError):
        validate_xml(invalid.read_bytes())


def test_json_xml_round_trip_has_zero_mandatory_information_loss():
    record = load_record()
    assert from_xml(to_xml(record)) == record
    assert from_xml(XML_FIXTURE.read_bytes()) == record


def test_xml_parser_refuses_doctype_and_entities():
    hostile = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY x "secret">]><x>&x;</x>'
    with pytest.raises(ValueError, match="forbidden"):
        validate_xml(hostile)


def test_mapping_covers_every_mandatory_leaf_field():
    with (ROOT / "spec" / "mappings" / "dpp-json-xml-rdf-1.0.0.csv").open(encoding="utf-8", newline="") as stream:
        paths = {row["jsonPath"] for row in csv.DictReader(stream)}
    required = {
        "dppId", "schemaVersion", "recordVersion", "status", "createdAt", "updatedAt",
        "responsibleOperatorId", "identity.granularity", "product.articleClass",
        "materialObservations[].observationId", "materialObservations[].fibreType",
        "materialObservations[].valueStatus", "materialObservations[].method",
        "materialObservations[].sourceOrganisationId", "materialObservations[].observedAt",
    }
    assert required <= paths


def test_released_sparql_query_set_matches_expected_results():
    record = complete_record()
    graph = to_rdf(record)
    expected = json.loads((QUERIES / "expected-results-1.0.0.json").read_text(encoding="utf-8"))
    for path in sorted(QUERIES.glob("*.rq")):
        result = graph.query(path.read_text(encoding="utf-8"))
        wanted = expected[path.name]
        if isinstance(wanted, bool):
            assert bool(result) is wanted, path.name
        else:
            assert len(list(result)) == wanted["rowCount"], path.name

    annex = to_rdf(load_divergence_record())
    divergence = annex.query((QUERIES / "material-divergence-1.0.0.rq").read_text(encoding="utf-8"))
    rows = list(divergence)
    assert len(rows) == 1
    assert {float(rows[0].pctA), float(rows[0].pctB)} == {95.0, 93.4}
    assert {str(rows[0].methodA), str(rows[0].methodB)} == {
        "https://data.sort4circ.eu/vocabulary/labQuantitativeIso1833",
        "https://data.sort4circ.eu/vocabulary/nirSpectroscopy",
    }


def test_rdf_is_derived_from_accepted_json_and_parses_as_turtle():
    graph = to_rdf(complete_record())
    serialised = graph.serialize(format="turtle")
    reparsed = Graph().parse(data=serialised, format="turtle")
    assert len(reparsed) == len(graph)


def test_api_negotiates_complete_dpp_xml(client):
    response = client.post(
        "/v1/dpps",
        content=XML_FIXTURE.read_bytes(),
        headers={"X-S4C-Role": "brand", "Content-Type": "application/xml", "Accept": "application/xml"},
    )
    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/xml")
    assert from_xml(response.content)["product"]["articleClass"] == "upperBodyKnitwear"


def test_openapi_declares_json_and_xml_for_complete_dpp_exchange():
    document = json.loads((ROOT / "spec" / "openapi" / "dpp-api-v1.json").read_text(encoding="utf-8"))
    assert document["info"]["version"] == "1.1.0"
    content = document["paths"]["/v1/dpps"]["post"]["requestBody"]["content"]
    assert {"application/json", "application/xml"} <= content.keys()


def test_semantic_fixture_keeps_canonical_terms():
    record = complete_record()
    assert record["product"]["articleClass"] == "upperBodyKnitwear"
    assert record["materialObservations"][0]["method"] == "labQuantitativeIso1833"
    assert {"observationId", "percentageBasis", "valueStatus"} <= record["materialObservations"][0].keys()


def test_round_trip_does_not_mutate_the_source_record():
    record = complete_record()
    before = deepcopy(record)
    from_xml(to_xml(record))
    assert record == before
