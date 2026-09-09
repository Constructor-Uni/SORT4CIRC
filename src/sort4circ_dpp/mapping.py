"""RDF projection and access to the term-level mapping package 1.0.0.

JSON is the normative exchange representation. The mapping package
``spec/mappings/dpp-mapping-1.0.0.json`` is the normative term-level mapping: one row
per schema-defined path, giving the JSON path, the XML path and the RDF property.

There is one XML serialiser, not two. ``json_to_xml`` and ``xml_to_json`` delegate to
:mod:`sort4circ_dpp.exchange`, which implements the published XML profile in the
``https://data.sort4circ.eu/vocabulary/`` namespace and validates against the released
XSD 1.1. This module owns the RDF projection: ontology-backed semantic triples plus a
canonical ``rdf:JSON`` snapshot for lossless transport reversal. The snapshot is not a
direct semantic mapping and is classified separately by the mapping package.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

from .config import MAPPING_DIR, SCHEMA_DIR
from .validation import validate_payload

SCHEMA_PATH = SCHEMA_DIR / "dpp-1.0.0.schema.json"
MAPPING_PATH = MAPPING_DIR / "dpp-mapping-1.0.0.json"

#: One namespace for both XML and RDF, as published.
XML_NAMESPACE = "https://data.sort4circ.eu/vocabulary/"
RDF_NAMESPACE = "https://data.sort4circ.eu/vocabulary/"

ARRAY_ITEM_NAMES = {
    "carriers": "carrier",
    "technicalFlags": "technicalFlag",
    "materialObservations": "materialObservation",
    "components": "component",
    "materialObservationRefs": "materialObservationRef",
    "lifecycleEvents": "lifecycleEvent",
    "inputRefs": "inputRef",
    "outputRefs": "outputRef",
    "sortingDecisions": "sortingDecision",
    "basedOnObservations": "observationRef",
    "environmentalValues": "environmentalValue",
    "integrity": "integrityEntry",
}


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _resolve(node: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        node = schema["$defs"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    return str(value)


def _encode_xml(parent: ET.Element, value: Any, node: dict[str, Any], schema: dict[str, Any]) -> None:
    node = _resolve(node, schema)
    if node.get("type") == "object":
        properties = node.get("properties", {})
        for name in properties:
            if name not in value:
                continue
            child = ET.SubElement(parent, f"{{{XML_NAMESPACE}}}{name}")
            _encode_xml(child, value[name], properties[name], schema)
        return
    if node.get("type") == "array":
        item_name = ARRAY_ITEM_NAMES.get(parent.tag.rsplit("}", 1)[-1], "item")
        for item in value:
            child = ET.SubElement(parent, f"{{{XML_NAMESPACE}}}{item_name}")
            _encode_xml(child, item, node["items"], schema)
        return
    parent.text = _text(value)


def mapping_package() -> dict[str, Any]:
    """The normative term-level mapping package."""
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def json_to_xml(payload: dict[str, Any]) -> bytes:
    """Serialise to the published XML profile. Single serialiser: see ``exchange``."""
    from .exchange import to_xml

    return to_xml(payload)


def xml_to_json(document: bytes | str) -> dict[str, Any]:
    """Parse the published XML profile back to canonical JSON."""
    from .exchange import from_xml

    return from_xml(document)


def _uri(namespace: str, token: str):
    from rdflib import URIRef

    return URIRef(f"{RDF_NAMESPACE}{namespace}/{token}")


def json_to_rdf(payload: dict[str, Any]):
    """Return an RDF graph with semantic triples and a lossless RDF/JSON snapshot."""
    from rdflib import Graph, Literal, Namespace, URIRef
    from rdflib.namespace import RDF, XSD

    validate_payload(payload)
    graph = Graph()
    s4c = Namespace(RDF_NAMESPACE)
    graph.bind("s4c", s4c)
    subject = URIRef(payload["dppId"])
    graph.add((subject, RDF.type, s4c.DigitalProductPassport))
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    graph.add((subject, RDF.value, Literal(canonical, datatype=RDF.JSON)))
    graph.add((subject, s4c.schemaVersion, Literal(payload["schemaVersion"], datatype=XSD.string)))
    graph.add((subject, s4c.recordVersion, Literal(payload["recordVersion"], datatype=XSD.integer)))
    if "supersededBy" in payload:
        graph.add((subject, s4c.supersededBy, URIRef(payload["supersededBy"])))

    identity = payload["identity"]
    identity_id = identity.get("itemId") or identity.get("batchId") or identity.get("modelId")
    entity = URIRef(identity_id) if identity_id else _uri("entity", payload["dppId"])
    graph.add((subject, s4c.describes, entity))
    graph.add((entity, RDF.type, s4c.TextileEntity))
    graph.add((entity, s4c.articleClass, _uri("article-class", payload["product"]["articleClass"])))
    mass = payload["product"].get("mass")
    if mass:
        graph.add((entity, s4c.massValue, Literal(str(mass["value"]), datatype=XSD.decimal)))
        graph.add((entity, s4c.massUnit, Literal(mass["unit"], datatype=XSD.string)))

    for observation in payload["materialObservations"]:
        node = URIRef(observation["observationId"])
        graph.add((entity, s4c.hasObservation, node))
        graph.add((node, RDF.type, s4c.MaterialObservation))
        graph.add((node, s4c.fibreType, _uri("fibre-type", observation["fibreType"])))
        graph.add((node, s4c.valueStatus, Literal(observation["valueStatus"], datatype=XSD.string)))
        graph.add((node, s4c.usedMethod, _uri("method", observation["method"])))
        graph.add((node, s4c.observedBy, URIRef(observation["sourceOrganisationId"])))
        graph.add((node, s4c.observedAt, Literal(observation["observedAt"], datatype=XSD.dateTime)))
        if "sourceSystemId" in observation:
            graph.add((node, s4c.producedBySystem, URIRef(observation["sourceSystemId"])))
        if "percentage" in observation:
            graph.add((node, s4c.percentage, Literal(str(observation["percentage"]), datatype=XSD.decimal)))
            graph.add((node, s4c.percentageBasis, Literal(observation["percentageBasis"], datatype=XSD.string)))
        confidence = observation.get("confidence")
        if confidence:
            graph.add((node, s4c.confidenceValue, Literal(str(confidence["value"]), datatype=XSD.decimal)))
            graph.add((node, s4c.confidenceScale, Literal(confidence["scale"], datatype=XSD.string)))
    return graph


def rdf_to_json(graph, dpp_id: str | None = None) -> dict[str, Any]:
    """Recover the normative JSON carried by :func:`json_to_rdf`."""
    from rdflib import Namespace, URIRef
    from rdflib.namespace import RDF

    s4c = Namespace(RDF_NAMESPACE)
    if dpp_id is None:
        subjects = list(graph.subjects(RDF.type, s4c.DigitalProductPassport))
        if len(subjects) != 1:
            raise ValueError("RDF graph must contain exactly one DPP subject")
        subject = subjects[0]
    else:
        subject = URIRef(dpp_id)
    snapshot = graph.value(subject, RDF.value)
    if snapshot is None or snapshot.datatype != RDF.JSON:
        raise ValueError("RDF graph has no reversible rdf:JSON DPP snapshot")
    result = json.loads(str(snapshot))
    validate_payload(result)
    return result
