"""Independent fictional textile data for the public educational profile.

Synthetic example. Not SORT4CIRC project data.
No source project records or historical measurements are used by this factory.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticFixtureFactory:
    """Produce deterministic fictional woven home-textile records."""

    def passport(self, number: int = 1) -> dict:
        if not 1 <= number <= 999999:
            raise ValueError("synthetic item number outside supported range")
        suffix = f"{number:06d}"
        return {
            "dppId": f"urn:example:dpp:{suffix}",
            "schemaVersion": "2.0.0",
            "recordVersion": 1,
            "status": "active",
            "createdAt": "2042-02-11T08:00:00Z",
            "updatedAt": "2042-02-13T10:30:00Z",
            "responsibleOperatorId": "urn:example:org:manufacturer-a",
            "identity": {
                "granularity": "item",
                "itemId": f"urn:example:item:{suffix}",
                "epc": f"urn:example:carrier:{suffix}",
                "sampleId": f"SYNTH-{number:04d}",
            },
            "product": {
                "articleClass": "homeTextileFlat",
                "fabricConstruction": "woven",
                "colourPrimary": "light",
                "technicalFlags": [],
            },
            "materialObservations": [
                {
                    "observationId": f"urn:example:observation:{suffix}-cotton",
                    "fibreType": "cotton",
                    "percentage": 62,
                    "percentageBasis": "declaredLabel",
                    "valueStatus": "supplied",
                    "method": "supplierDeclaration",
                    "sourceOrganisationId": "urn:example:org:manufacturer-a",
                    "observedAt": "2042-02-12T09:00:00Z",
                },
                {
                    "observationId": f"urn:example:observation:{suffix}-flax",
                    "fibreType": "flax",
                    "percentage": 38,
                    "percentageBasis": "declaredLabel",
                    "valueStatus": "supplied",
                    "method": "supplierDeclaration",
                    "sourceOrganisationId": "urn:example:org:manufacturer-a",
                    "observedAt": "2042-02-12T09:00:00Z",
                },
            ],
        }

    def carrier(self, number: int = 1) -> dict:
        return {
            "carrierType": "qrCode",
            "encodingScheme": "exampleUri",
            "encodedIdentifier": f"urn:example:carrier:{number:06d}",
            "resolverUri": f"https://example.org/dpp/{number:06d}",
            "boundBy": "urn:example:org:manufacturer-a",
        }

    def observation(self, number: int = 1) -> dict:
        return {
            "observationId": f"urn:example:observation:inspection-{number:06d}",
            "fibreType": "cotton",
            "percentage": 58,
            "percentageBasis": "declaredLabel",
            "valueStatus": "supplied",
            "method": "labelDeclaration",
            "sourceOrganisationId": "urn:example:org:collector-a",
            "observedAt": "2043-07-09T16:45:00Z",
        }

    def event(self, number: int = 1) -> dict:
        return {
            "eventId": f"urn:example:event:{number:06d}",
            "eventType": "collection",
            "eventTime": "2043-07-10T12:00:00Z",
            "eventTimeZoneOffset": "+00:00",
            "recordedAt": "2043-07-10T12:05:00Z",
            "actorOrganisationId": "urn:example:org:collector-a",
            "sourceSystemId": "urn:example:system:educational-client",
            "facilityId": "urn:example:facility:collection-site-a",
        }

    def fixtures(self) -> dict[str, dict]:
        base = self.passport()
        result = {
            "valid-minimum.json": copy.deepcopy(base),
            "valid-synthetic-textile.json": copy.deepcopy(base),
        }
        disagreement = copy.deepcopy(base)
        disagreement["materialObservations"].append(self.observation())
        result["valid-two-technologies-disagree.json"] = disagreement
        unknown = copy.deepcopy(base)
        unknown["materialObservations"] = [{
            "observationId": "urn:example:observation:unknown",
            "fibreType": "blendUnresolved",
            "valueStatus": "notMeasured",
            "method": "manualInspection",
            "sourceOrganisationId": "urn:example:org:sorter-a",
            "observedAt": "2044-01-16T09:00:00Z",
        }]
        result["valid-uncharacterised-garment.json"] = unknown
        variants = [
            ("invalid-article-class-token", "vocab"),
            ("invalid-composition-above-one-hundred", "schema"),
            ("invalid-confidence-without-scale", "schema"),
            ("invalid-fibre-token", "vocab"),
            ("invalid-item-without-item-id", "schema"),
            ("invalid-no-material-observation", "schema"),
            ("invalid-observation-without-method", "schema"),
            ("invalid-percentage-without-basis", "schema"),
            ("invalid-timestamp-without-offset", "schema"),
            ("invalid-unknown-carrying-a-value", "schema"),
        ]
        for name, kind in variants:
            record = copy.deepcopy(base)
            observation = record["materialObservations"][0]
            if name == "invalid-article-class-token":
                record["product"]["articleClass"] = "fictionalUndeclaredClass"
            elif name == "invalid-composition-above-one-hundred":
                for item in record["materialObservations"]:
                    item["percentageBasis"] = "mass"
                    item["percentage"] = 72
            elif name == "invalid-confidence-without-scale":
                observation["confidence"] = {"value": 0.41}
            elif name == "invalid-fibre-token":
                observation["fibreType"] = "fictionalUndeclaredFibre"
            elif name == "invalid-item-without-item-id":
                del record["identity"]["itemId"]
            elif name == "invalid-no-material-observation":
                record["materialObservations"] = []
            elif name == "invalid-observation-without-method":
                del observation["method"]
            elif name == "invalid-percentage-without-basis":
                del observation["percentageBasis"]
            elif name == "invalid-timestamp-without-offset":
                record["updatedAt"] = "2042-02-13T10:30:00"
            elif name == "invalid-unknown-carrying-a-value":
                observation["valueStatus"] = "unknown"
            record["$expect"] = "S4C-PAYLOAD-" + ("VOCAB" if kind == "vocab" else "SCHEMA") + "-INVALID"
            result[name + ".json"] = record
        return result
