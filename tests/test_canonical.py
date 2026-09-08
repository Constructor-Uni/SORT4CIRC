"""Independent synthetic canonical reference vector; no project records."""
from __future__ import annotations

import json

import pytest

from sort4circ_dpp.canonical import (
    CanonicalisationError,
    canonical_bytes,
    canonicalise,
    digest,
    integrity_projection,
    verify_digest,
)

REFERENCE = {'dppId': 'urn:example:dpp:000001', 'schemaVersion': '2.0.0', 'recordVersion': 1, 'status': 'active', 'createdAt': '2042-02-11T08:00:00Z', 'updatedAt': '2042-02-13T10:30:00Z', 'responsibleOperatorId': 'urn:example:org:manufacturer-a', 'identity': {'granularity': 'item', 'itemId': 'urn:example:item:000001', 'epc': 'urn:example:carrier:000001', 'sampleId': 'SYNTH-0001'}, 'product': {'articleClass': 'homeTextileFlat', 'fabricConstruction': 'woven', 'colourPrimary': 'light', 'technicalFlags': []}, 'materialObservations': [{'observationId': 'urn:example:observation:000001-cotton', 'fibreType': 'cotton', 'percentage': 62, 'percentageBasis': 'declaredLabel', 'valueStatus': 'supplied', 'method': 'supplierDeclaration', 'sourceOrganisationId': 'urn:example:org:manufacturer-a', 'observedAt': '2042-02-12T09:00:00Z'}, {'observationId': 'urn:example:observation:000001-flax', 'fibreType': 'flax', 'percentage': 38, 'percentageBasis': 'declaredLabel', 'valueStatus': 'supplied', 'method': 'supplierDeclaration', 'sourceOrganisationId': 'urn:example:org:manufacturer-a', 'observedAt': '2042-02-12T09:00:00Z'}]}
PUBLISHED_DIGEST = "c99a12da1b69a0acce1b3f7f3dca0a6af740ebc7cdd80ab08060e908986da715"
ALTERED_DIGEST = "9d7655e4bd291c2755a81e996da7877dfca1bad46ed82a6f099379b4550a4b7d"
PUBLISHED_LENGTH = 860


def test_independent_synthetic_reference_vector():
    assert len(canonical_bytes(REFERENCE)) == PUBLISHED_LENGTH
    assert digest(REFERENCE) == PUBLISHED_DIGEST


def test_single_digit_change_produces_a_different_digest():
    altered = json.loads(json.dumps(REFERENCE))
    altered["materialObservations"][0]["percentage"] = 61
    assert digest(altered) == ALTERED_DIGEST
    assert digest(altered) != PUBLISHED_DIGEST


def test_verify_digest_accepts_and_rejects():
    assert verify_digest(REFERENCE, PUBLISHED_DIGEST)
    assert verify_digest(REFERENCE, PUBLISHED_DIGEST.upper())
    assert not verify_digest(REFERENCE, ALTERED_DIGEST)


def test_projection_excludes_access_and_integrity_members():
    noisy = json.loads(json.dumps(REFERENCE))
    noisy["integrity"] = [{"evidenceId": "urn:example:evidence:1"}]
    noisy["accessPolicyVersion"] = "9.9.9"
    noisy["status"] = "active"
    assert digest(noisy) == PUBLISHED_DIGEST, "the digest must not depend on who asked or on anchoring state"


def test_member_order_does_not_change_the_digest():
    reordered = {k: REFERENCE[k] for k in reversed(list(REFERENCE))}
    assert digest(reordered) == PUBLISHED_DIGEST


def test_array_order_does_change_the_digest():
    swapped = json.loads(json.dumps(REFERENCE))
    swapped["materialObservations"].reverse()
    assert digest(swapped) != PUBLISHED_DIGEST, "observation order is meaningful and is preserved"


@pytest.mark.parametrize(
    "value,expected",
    [
        (1, "1"),
        (62, "62"),
        (58.25, "58.25"),
        (0.5, "0.5"),
        (-2, "-2"),
        (True, "true"),
        (None, "null"),
        ("a\"b", '"a\\"b"'),
        ({"b": 1, "a": 2}, '{"a":2,"b":1}'),
        ([3, 1, 2], "[3,1,2]"),
    ],
)
def test_scalar_serialisation(value, expected):
    assert canonicalise(value) == expected


def test_non_finite_numbers_are_refused():
    with pytest.raises(CanonicalisationError):
        canonicalise(float("inf"))
    with pytest.raises(CanonicalisationError):
        canonicalise(float("nan"))


def test_projection_is_a_subset():
    projection = integrity_projection(REFERENCE)
    assert set(projection) <= {"dppId", "recordVersion", "updatedAt", "identity", "product", "materialObservations"}
