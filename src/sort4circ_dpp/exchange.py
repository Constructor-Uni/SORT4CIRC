"""D4.3 JSON/XML exchange and RDF projection helpers.

JSON remains the service's internal representation. XML is validated against
the released XSD before conversion, and accepted records are validated again
with the canonical JSON Schema and vocabulary rules. RDF is always derived
from an accepted record; RDF input is not an exchange/write format.
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from typing import Any
from xml.etree import ElementTree as ET

import xmlschema
from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

from .config import SCHEMA_DIR
from .validation import validate_payload

NS = "https://data.sort4circ.eu/vocabulary/"
S4C = Namespace(NS)
ET.register_namespace("s4c", NS)

ROOT_SCALARS = {
    "RecordVersion": ("recordVersion", int),
    "Status": ("status", str),
    "SupersededBy": ("supersededBy", str),
    "CreatedAt": ("createdAt", str),
    "UpdatedAt": ("updatedAt", str),
    "ResponsibleOperatorId": ("responsibleOperatorId", str),
    "RegistryIdentifier": ("registryIdentifier", str),
    "AccessPolicyVersion": ("accessPolicyVersion", str),
}

OBJECTS = {
    "identity": ("Identity", None),
    "product": ("Product", None),
}

ARRAYS = {
    "carriers": ("Carriers", "Carrier"),
    "materialObservations": ("MaterialObservations", "MaterialObservation"),
    "components": ("Components", "Component"),
    "lifecycleEvents": ("LifecycleEvents", "LifecycleEvent"),
    "sortingDecisions": ("SortingDecisions", "SortingDecision"),
    "environmentalValues": ("EnvironmentalValues", "EnvironmentalValue"),
    "integrity": ("Integrity", "IntegrityEntry"),
}

LIST_ITEMS = {
    "technicalFlags": "TechnicalFlag",
    "materialObservationRefs": "MaterialObservationRef",
    "basedOnObservations": "ObservationRef",
    "inputRefs": "InputRef",
    "outputRefs": "OutputRef",
}

INTEGER_FIELDS = {"recordVersion", "basedOnRecordVersion", "subjectVersion", "attempts"}
DECIMAL_FIELDS = {"percentage", "value"}
BOOLEAN_FIELDS = {"separable"}


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def _pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def _camel(name: str) -> str:
    return name[:1].lower() + name[1:]


@lru_cache(maxsize=1)
def xsd() -> xmlschema.XMLSchema11:
    """Load the local XSD 1.1 profile without fetching remote resources."""
    return xmlschema.XMLSchema11(str(SCHEMA_DIR / "dpp-1.0.0.xsd"), allow="local")


def validate_xml(data: bytes | str) -> None:
    """Validate an XML DPP and reject DTD/entity declarations up front."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("DTD and entity declarations are forbidden")
    xsd().validate(raw)


def _write_value(parent: ET.Element, key: str, value: Any) -> None:
    element = ET.SubElement(parent, _tag(_pascal(key)))
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            _write_value(element, child_key, child_value)
    elif isinstance(value, list):
        item_name = LIST_ITEMS.get(key, "Value")
        for item in value:
            item_element = ET.SubElement(element, _tag(item_name))
            if isinstance(item, dict):
                for child_key, child_value in item.items():
                    _write_value(item_element, child_key, child_value)
            else:
                item_element.text = str(item).lower() if isinstance(item, bool) else str(item)
    else:
        element.text = str(value).lower() if isinstance(value, bool) else str(value)


def to_xml(record: dict[str, Any], *, validate: bool = True) -> bytes:
    """Serialise one complete canonical JSON DPP to the D4.3 XML profile."""
    validate_payload(record)
    root = ET.Element(
        _tag("DigitalProductPassport"),
        {"schemaVersion": record["schemaVersion"], "dppId": record["dppId"]},
    )
    for xml_name, (json_name, _coerce) in ROOT_SCALARS.items():
        if json_name in record:
            element = ET.SubElement(root, _tag(xml_name))
            element.text = str(record[json_name])
    def write_object(json_name: str) -> None:
        xml_name, _item = OBJECTS[json_name]
        wrapper = ET.SubElement(root, _tag(xml_name))
        for key, value in record[json_name].items():
            _write_value(wrapper, key, value)

    def write_array(json_name: str) -> None:
        if not record.get(json_name):
            return
        wrapper_name, item_name = ARRAYS[json_name]
        wrapper = ET.SubElement(root, _tag(wrapper_name))
        for item in record[json_name]:
            child = ET.SubElement(wrapper, _tag(item_name))
            for key, value in item.items():
                _write_value(child, key, value)

    write_object("identity")
    write_array("carriers")
    write_object("product")
    for json_name in ("materialObservations", "components", "lifecycleEvents", "sortingDecisions", "environmentalValues", "integrity"):
        write_array(json_name)
    payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if validate:
        validate_xml(payload)
    return payload


def _parse_scalar(key: str, text: str) -> Any:
    if key in INTEGER_FIELDS:
        return int(text)
    if key in DECIMAL_FIELDS:
        value = Decimal(text)
        return int(value) if value == value.to_integral_value() else float(value)
    if key in BOOLEAN_FIELDS:
        return text == "true"
    return text


def _read_value(element: ET.Element) -> Any:
    children = list(element)
    key = _camel(element.tag.rsplit("}", 1)[-1])
    if not children:
        return _parse_scalar(key, element.text or "")
    child_names = [child.tag.rsplit("}", 1)[-1] for child in children]
    if key in LIST_ITEMS or len(set(child_names)) < len(child_names):
        return [_read_value(child) for child in children]
    return {_camel(name): _read_value(child) for name, child in zip(child_names, children, strict=True)}


def from_xml(data: bytes | str) -> dict[str, Any]:
    """Validate and convert one D4.3 XML DPP into canonical JSON data."""
    validate_xml(data)
    raw = data.encode("utf-8") if isinstance(data, str) else data
    root = ET.fromstring(raw)
    record: dict[str, Any] = {
        "dppId": root.attrib["dppId"],
        "schemaVersion": root.attrib["schemaVersion"],
    }
    root_lookup = dict(ROOT_SCALARS)
    object_lookup = {xml: json_name for json_name, (xml, _item) in OBJECTS.items()}
    array_lookup = {xml: json_name for json_name, (xml, _item) in ARRAYS.items()}
    for element in root:
        name = element.tag.rsplit("}", 1)[-1]
        if name in root_lookup:
            json_name, coerce = root_lookup[name]
            record[json_name] = coerce(element.text or "")
        elif name in object_lookup:
            record[object_lookup[name]] = {
                _camel(child.tag.rsplit("}", 1)[-1]): _read_value(child) for child in element
            }
        elif name in array_lookup:
            record[array_lookup[name]] = [
                {_camel(child.tag.rsplit("}", 1)[-1]): _read_value(child) for child in item}
                for item in element
            ]
    validate_payload(record)
    return record


def to_rdf(record: dict[str, Any]) -> Graph:
    """Derive the core RDF/OWL graph from an accepted DPP record."""
    validate_payload(record)
    graph = Graph()
    graph.bind("s4c", S4C)
    dpp = URIRef(record["dppId"])
    graph.add((dpp, RDF.type, S4C.DigitalProductPassport))
    graph.add((dpp, S4C.schemaVersion, Literal(record["schemaVersion"])))
    graph.add((dpp, S4C.recordVersion, Literal(record["recordVersion"], datatype=XSD.integer)))
    graph.add((dpp, S4C.status, Literal(record["status"])))
    graph.add((dpp, S4C.createdAt, Literal(record["createdAt"], datatype=XSD.dateTime)))
    graph.add((dpp, S4C.updatedAt, Literal(record["updatedAt"], datatype=XSD.dateTime)))
    graph.add((dpp, S4C.responsibleOperator, URIRef(record["responsibleOperatorId"])))
    identity = record["identity"]
    subject_id = identity.get("itemId") or identity.get("batchId") or identity.get("modelId")
    garment = URIRef(subject_id)
    graph.add((dpp, S4C.describes, garment))
    graph.add((garment, RDF.type, S4C.Garment))
    graph.add((garment, S4C.granularity, Literal(identity["granularity"])))
    graph.add((garment, S4C.productIdentifier, Literal(subject_id)))
    graph.add((garment, S4C.articleClass, S4C[record["product"]["articleClass"]]))

    for carrier in record.get("carriers", []):
        binding = URIRef(carrier["carrierId"])
        carrier_node = URIRef(f"{carrier['carrierId']}:carrier")
        graph.add((dpp, S4C.hasCarrierBinding, binding))
        graph.add((binding, RDF.type, S4C.CarrierBinding))
        graph.add((binding, S4C.bindsCarrier, carrier_node))
        graph.add((binding, S4C.bindingStatus, Literal(carrier["bindingStatus"])))
        graph.add((carrier_node, RDF.type, S4C.DataCarrier))
        graph.add((carrier_node, S4C.encodedIdentifier, Literal(carrier["encodedIdentifier"])))

    for observation in record["materialObservations"]:
        node = URIRef(observation["observationId"])
        graph.add((garment, S4C.hasObservation, node))
        graph.add((node, RDF.type, S4C.MaterialObservation))
        graph.add((node, S4C.fibreType, S4C[observation["fibreType"]]))
        graph.add((node, S4C.valueStatus, Literal(observation["valueStatus"])))
        graph.add((node, S4C.usedMethod, S4C[observation["method"]]))
        graph.add((node, S4C.observedBy, URIRef(observation["sourceOrganisationId"])))
        graph.add((node, S4C.observedAt, Literal(observation["observedAt"], datatype=XSD.dateTime)))
        if "percentage" in observation:
            graph.add((node, S4C.percentage, Literal(Decimal(str(observation["percentage"])), datatype=XSD.decimal)))
            graph.add((node, S4C.percentageBasis, Literal(observation["percentageBasis"])))

    for component in record.get("components", []):
        node = URIRef(component["componentId"])
        graph.add((garment, S4C.hasComponent, node))
        graph.add((node, RDF.type, S4C.Component))
        graph.add((node, S4C.componentType, Literal(component["componentType"])))
        if component.get("parentComponentId"):
            graph.add((node, S4C.partOf, URIRef(component["parentComponentId"])))

    for event in record.get("lifecycleEvents", []):
        node = URIRef(event["eventId"])
        graph.add((dpp, S4C.hasLifecycleEvent, node))
        graph.add((node, RDF.type, S4C.LifecycleEvent))
        graph.add((node, S4C.eventType, Literal(event["eventType"])))
        graph.add((node, S4C.recordedAt, Literal(event["recordedAt"], datatype=XSD.dateTime)))
        graph.add((node, S4C.performedBy, URIRef(event["actorOrganisationId"])))

    for decision in record.get("sortingDecisions", []):
        node = URIRef(decision["decisionId"])
        graph.add((dpp, S4C.hasSortingDecision, node))
        graph.add((node, RDF.type, S4C.SortingDecision))
        graph.add((node, S4C.sortingCategoryValue, Literal(decision["sortingCategory"])))
        for observation_ref in decision["basedOnObservations"]:
            graph.add((node, S4C.basedOnObservation, URIRef(observation_ref)))

    for index, value in enumerate(record.get("environmentalValues", []), start=1):
        node = URIRef(f"{record['dppId']}:environmental:{index}")
        graph.add((garment, S4C.hasObservation, node))
        graph.add((node, RDF.type, S4C.EnvironmentalValue))
        graph.add((node, S4C.metricType, Literal(value["metricType"])))
        graph.add((node, S4C.systemBoundary, Literal(value["systemBoundary"])))
    return graph


def json_bytes(record: dict[str, Any]) -> bytes:
    """Return the UTF-8 operational JSON representation after validation."""
    validate_payload(record)
    return json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
