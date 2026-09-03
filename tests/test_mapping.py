from __future__ import annotations

import copy
import csv
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import xmlschema
from jsonschema import Draft202012Validator
from rdflib import Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD

from sort4circ_dpp.mapping import (
    RDF_NAMESPACE,
    json_to_rdf,
    json_to_xml,
    rdf_to_json,
    xml_to_json,
)
from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.validation import validate_payload

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "spec/mappings/dpp-mapping-1.0.0.json"
MAPPING_SCHEMA_PATH = ROOT / "spec/mappings/dpp-mapping-1.0.0.schema.json"
JSON_SCHEMA_PATH = ROOT / "spec/schemas/dpp-1.0.0.schema.json"
ONTOLOGY_PATH = ROOT / "spec/ontology/sort4circ-1.0.0.ttl"
VALID_FIXTURES = sorted((ROOT / "examples/fixtures").glob("valid-*.json"))
S4C = Namespace(RDF_NAMESPACE)
XML_NS = {"dpp": "https://data.sort4circ.eu/dpp/1.0.0"}
XSD11 = xmlschema.XMLSchema11(ROOT / "spec/mappings/dpp-1.0.0.xsd")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mapping():
    return load(MAPPING_PATH)


def resolve(node, schema):
    while "$ref" in node:
        node = schema["$defs"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def schema_paths(node, schema, prefix=""):
    node = resolve(node, schema)
    result = set()
    if node.get("type") != "object":
        return result
    for name, child in node.get("properties", {}).items():
        child = resolve(child, schema)
        path = f"{prefix}.{name}" if prefix else name
        if child.get("type") == "array":
            path += "[]"
            result.add(path)
            item = resolve(child["items"], schema)
            if item.get("type") == "object":
                result |= schema_paths(item, schema, path)
        else:
            result.add(path)
            if child.get("type") == "object":
                result |= schema_paths(child, schema, path)
    return result


def test_mapping_document_is_versioned_and_schema_valid():
    document = mapping()
    mapping_schema = load(MAPPING_SCHEMA_PATH)
    Draft202012Validator.check_schema(mapping_schema)
    errors = list(Draft202012Validator(mapping_schema).iter_errors(document))
    assert not errors, errors
    assert document["mappingVersion"] == "1.0.0"
    assert all(row["mappingVersion"] == document["mappingVersion"] for row in document["rows"])


def test_all_schema_exchange_paths_have_exactly_one_mapping():
    schema = load(JSON_SCHEMA_PATH)
    expected = schema_paths(schema, schema)
    paths = [row["jsonPath"] for row in mapping()["rows"]]
    assert len(paths) == len(set(paths))
    assert set(paths) == expected
    assert len(expected) == 124
    assert len(set(paths) & expected) / len(expected) == 1.0


def test_csv_is_an_exact_generated_projection():
    result = subprocess.run(
        [sys.executable, "tools/gen_mapping_csv.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    with (ROOT / "spec/mappings/dpp-mapping-1.0.0.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert [row["mappingId"] for row in csv_rows] == [row["mappingId"] for row in mapping()["rows"]]


def test_every_rdf_binding_resolves_to_the_ontology_or_a_declared_rdf_construct():
    graph = __import__("rdflib").Graph().parse(ONTOLOGY_PATH, format="turtle")
    classes = {str(subject) for subject in graph.subjects(RDF.type, OWL.Class)}
    properties = {
        str(subject)
        for kind in (OWL.ObjectProperty, OWL.DatatypeProperty)
        for subject in graph.subjects(RDF.type, kind)
    }
    for row in mapping()["rows"]:
        subject_iri = row["rdfSubjectType"].replace("s4c:", RDF_NAMESPACE)
        assert subject_iri in classes
        if row["rdfMappingStatus"] == "direct":
            assert row["rdfProperty"].replace("s4c:", RDF_NAMESPACE) in properties
            assert row["rdfConstruct"] is None
        elif row["rdfMappingStatus"] == "subjectIdentifier":
            assert row["rdfConstruct"] == "rdf:subject"
        else:
            assert row["rdfMappingStatus"] in {"notApplicable", "unresolved"}
            assert row["rdfConstruct"] == "rdf:value/rdf:JSON"
            assert row["rdfMappingReason"]


def test_rdf_coverage_classification_does_not_count_transport_snapshots_as_semantics():
    rows = mapping()["rows"]
    counts = {
        status: sum(row["rdfMappingStatus"] == status for row in rows)
        for status in ("direct", "subjectIdentifier", "notApplicable", "unresolved")
    }
    assert counts == {"direct": 111, "subjectIdentifier": 7, "notApplicable": 6, "unresolved": 0}
    assert all(row["rdfMappingStatus"] != "direct" for row in rows if row["rdfConstruct"] == "rdf:value/rdf:JSON")
    assert counts["direct"] / len(rows) == pytest.approx(111 / 124)


def test_every_controlled_vocabulary_reference_resolves():
    vocabularies = {path.stem: load(path) for path in (ROOT / "spec/vocabularies").glob("*.json")}
    for row in mapping()["rows"]:
        name = row["controlledVocabulary"]
        if name is not None:
            assert name in vocabularies
            assert vocabularies[name]["version"]
            assert vocabularies[name]["terms"]


def test_xsd_is_versioned_and_declares_every_mapped_xml_element():
    root = ET.parse(ROOT / "spec/mappings/dpp-1.0.0.xsd").getroot()
    assert root.attrib["version"] == "1.0.0"
    declared = {
        element.attrib["name"]
        for element in root.iter("{http://www.w3.org/2001/XMLSchema}element")
        if "name" in element.attrib
    }
    for row in mapping()["rows"]:
        names = [part.removeprefix("dpp:") for part in row["xmlXPath"].split("/") if part][1:]
        assert names
        assert all(name in declared for name in names)
    assert XSD11.XSD_VERSION == "1.1"


@pytest.mark.parametrize("fixture", VALID_FIXTURES, ids=lambda path: path.stem)
def test_xsd_11_accepts_every_valid_xml_projection(fixture):
    assert XSD11.is_valid(json_to_xml(load(fixture)))


def _payload_with_conditional_sections():
    payload = copy.deepcopy(load(ROOT / "examples/fixtures/valid-annex-g-garment.json"))
    payload["carriers"] = [
        {
            "carrierId": "urn:sort4circ:carrier:1",
            "carrierType": "qrCode",
            "encodingScheme": "gs1DigitalLink",
            "encodedIdentifier": "https://example.test/01/1",
            "bindingStatus": "commissioned",
            "boundAt": "2026-08-10T09:12:44Z",
            "boundBy": "urn:sort4circ:org:brand-a",
        }
    ]
    payload["lifecycleEvents"] = [
        {
            "eventId": "urn:sort4circ:event:1",
            "eventType": "transformation",
            "eventTime": "2026-08-10T09:12:44Z",
            "eventTimeZoneOffset": "+00:00",
            "recordedAt": "2026-08-10T09:12:45Z",
            "actorOrganisationId": "urn:sort4circ:org:brand-a",
            "sourceSystemId": "urn:sort4circ:system:1",
            "inputRefs": [payload["identity"]["itemId"]],
            "outputRefs": ["urn:sort4circ:item:output-1"],
        }
    ]
    payload["sortingDecisions"] = [
        {
            "decisionId": "urn:sort4circ:decision:1",
            "basedOnObservations": [payload["materialObservations"][0]["observationId"]],
            "ruleSetId": "urn:sort4circ:ruleset:1",
            "ruleSetVersion": "1.0.0",
            "sortingCategory": "manualReview",
            "decidedAt": "2026-08-10T09:12:46Z",
            "decidedBy": "urn:sort4circ:org:sorter-a",
            "outcomeStatus": "overridden",
            "overrideReason": "manual inspection",
        }
    ]
    return payload


def test_xsd_11_enforces_identity_granularity_identifier():
    root = ET.fromstring(json_to_xml(load(ROOT / "examples/fixtures/valid-annex-g-garment.json")))
    identity = root.find("dpp:identity", XML_NS)
    identity.remove(identity.find("dpp:itemId", XML_NS))
    assert not XSD11.is_valid(root)


def test_xsd_11_enforces_carrier_closure():
    root = ET.fromstring(json_to_xml(_payload_with_conditional_sections()))
    root.find("dpp:carriers/dpp:carrier/dpp:bindingStatus", XML_NS).text = "retired"
    assert not XSD11.is_valid(root)


def test_xsd_11_enforces_observation_percentage_rules():
    root = ET.fromstring(json_to_xml(_payload_with_conditional_sections()))
    observation = root.find("dpp:materialObservations/dpp:materialObservation", XML_NS)
    observation.remove(observation.find("dpp:percentageBasis", XML_NS))
    assert not XSD11.is_valid(root)

    root = ET.fromstring(json_to_xml(_payload_with_conditional_sections()))
    root.find("dpp:materialObservations/dpp:materialObservation/dpp:valueStatus", XML_NS).text = "unknown"
    assert not XSD11.is_valid(root)


def test_xsd_11_enforces_transformation_references():
    root = ET.fromstring(json_to_xml(_payload_with_conditional_sections()))
    event = root.find("dpp:lifecycleEvents/dpp:lifecycleEvent", XML_NS)
    event.remove(event.find("dpp:inputRefs", XML_NS))
    assert not XSD11.is_valid(root)


def test_xsd_11_enforces_sorting_override_reason():
    root = ET.fromstring(json_to_xml(_payload_with_conditional_sections()))
    decision = root.find("dpp:sortingDecisions/dpp:sortingDecision", XML_NS)
    decision.remove(decision.find("dpp:overrideReason", XML_NS))
    assert not XSD11.is_valid(root)


@pytest.mark.parametrize("fixture", VALID_FIXTURES, ids=lambda path: path.stem)
def test_json_xml_json_round_trip_has_zero_information_loss(fixture):
    payload = load(fixture)
    document = json_to_xml(payload)
    assert xml_to_json(document) == payload


@pytest.mark.parametrize("fixture", VALID_FIXTURES, ids=lambda path: path.stem)
def test_json_rdf_json_round_trip_has_zero_information_loss(fixture):
    payload = load(fixture)
    graph = json_to_rdf(payload)
    assert rdf_to_json(graph, payload["dppId"]) == payload


def test_rdf_projection_preserves_identifiers_datatypes_provenance_and_relationships():
    payload = load(ROOT / "examples/fixtures/valid-two-technologies-disagree.json")
    graph = json_to_rdf(payload)
    passport = URIRef(payload["dppId"])
    entity = URIRef(payload["identity"]["itemId"])
    assert (passport, RDF.type, S4C.DigitalProductPassport) in graph
    assert (passport, S4C.describes, entity) in graph
    observations = set(graph.objects(entity, S4C.hasObservation))
    assert observations == {URIRef(item["observationId"]) for item in payload["materialObservations"]}
    for item in payload["materialObservations"]:
        node = URIRef(item["observationId"])
        assert (node, S4C.observedBy, URIRef(item["sourceOrganisationId"])) in graph
        assert graph.value(node, S4C.observedAt).datatype == XSD.dateTime
        assert graph.value(node, S4C.percentage).datatype == XSD.decimal
        assert graph.value(node, S4C.usedMethod) is not None


@pytest.mark.parametrize("status", ["unknown", "notMeasured", "notApplicable", "withheld"])
def test_absence_states_never_become_zero_or_empty(status):
    payload = load(ROOT / "examples/fixtures/valid-uncharacterised-garment.json")
    payload["materialObservations"][0]["valueStatus"] = status
    payload["materialObservations"][0].pop("percentage", None)
    payload["materialObservations"][0].pop("percentageBasis", None)
    validate_payload(payload)
    xml_result = xml_to_json(json_to_xml(payload))
    rdf_result = rdf_to_json(json_to_rdf(payload), payload["dppId"])
    for result in (xml_result, rdf_result):
        observation = result["materialObservations"][0]
        assert observation["valueStatus"] == status
        assert "percentage" not in observation
        assert 0 not in observation.values()
        assert "" not in observation.values()


def test_unmapped_controlled_value_fails_before_serialisation():
    payload = load(ROOT / "examples/fixtures/valid-minimum.json")
    payload["product"]["articleClass"] = "not-in-the-controlled-vocabulary"
    with pytest.raises(DppError):
        json_to_xml(payload)
    with pytest.raises(DppError):
        json_to_rdf(payload)


def test_multiple_methods_remain_separate_observations():
    payload = load(ROOT / "examples/fixtures/valid-two-technologies-disagree.json")
    assert len({item["method"] for item in payload["materialObservations"]}) > 1
    graph = json_to_rdf(payload)
    entity = URIRef(payload["identity"]["itemId"])
    nodes = list(graph.objects(entity, S4C.hasObservation))
    assert len(nodes) == len(payload["materialObservations"])
    assert len(set(nodes)) == len(nodes)


def test_mandatory_information_loss_count_is_zero():
    payload = load(ROOT / "examples/fixtures/valid-annex-g-garment.json")
    schema = load(JSON_SCHEMA_PATH)
    required = set(schema["required"])
    for result in (xml_to_json(json_to_xml(payload)), rdf_to_json(json_to_rdf(payload))):
        assert sum(result.get(key) != payload[key] for key in required) == 0
