"""Canonicalisation and digest.

The reference vector is the published value from deliverable D4.3, Annex G. It
is reproduced here rather than imported, so that a change to the projection code
cannot silently change the expectation as well.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sort4circ_dpp.canonical import (
    CanonicalisationError,
    canonical_bytes,
    canonicalise,
    digest,
    integrity_projection,
    verify_digest,
)

PUBLISHED_DIGEST = "dd14a3f2487f2b22deda4a7bc2b37e775f378e05d60dc1e6ad26fdf26038ae9f"
ALTERED_DIGEST = "270e6f8790eebae533171aa62635a96c7a8e7e4366b9a9c1593262d857069f3b"
PUBLISHED_LENGTH = 871

INLINE_REFERENCE = {
    "dppId": "urn:sort4circ:dpp:000001",
    "recordVersion": 7,
    "updatedAt": "2026-08-10T09:12:44Z",
    "identity": {
        "granularity": "item",
        "itemId": "urn:sort4circ:item:000001",
        "epc": "urn:epc:id:sgtin:0614141.112345.400",
    },
    "product": {
        "articleClass": "upperBodyKnitwear",
        "fabricConstruction": "knitted",
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
}

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "valid-annex-g-garment.json"


def reference_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_reference_vector_matches_the_deliverable():
    REFERENCE = reference_fixture()
    assert len(canonical_bytes(REFERENCE)) == PUBLISHED_LENGTH
    assert digest(REFERENCE) == PUBLISHED_DIGEST


def test_single_digit_change_produces_a_different_digest():
    REFERENCE = reference_fixture()
    altered = json.loads(json.dumps(REFERENCE))
    altered["materialObservations"][0]["percentage"] = 94
    assert digest(altered) == ALTERED_DIGEST
    assert digest(altered) != PUBLISHED_DIGEST


def test_verify_digest_accepts_and_rejects():
    REFERENCE = reference_fixture()
    assert verify_digest(REFERENCE, PUBLISHED_DIGEST)
    assert verify_digest(REFERENCE, PUBLISHED_DIGEST.upper())
    assert not verify_digest(REFERENCE, ALTERED_DIGEST)


def test_projection_excludes_access_and_integrity_members():
    REFERENCE = reference_fixture()
    noisy = json.loads(json.dumps(REFERENCE))
    noisy["integrity"] = [{"evidenceId": "urn:sort4circ:evidence:1"}]
    noisy["accessPolicyVersion"] = "9.9.9"
    noisy["status"] = "active"
    assert digest(noisy) == PUBLISHED_DIGEST, "the digest must not depend on who asked or on anchoring state"


def test_member_order_does_not_change_the_digest():
    REFERENCE = reference_fixture()
    reordered = {k: REFERENCE[k] for k in reversed(list(REFERENCE))}
    assert digest(reordered) == PUBLISHED_DIGEST


def test_array_order_does_change_the_digest():
    REFERENCE = reference_fixture()
    swapped = json.loads(json.dumps(REFERENCE))
    swapped["materialObservations"].reverse()
    assert digest(swapped) != PUBLISHED_DIGEST, "observation order is meaningful and is preserved"


@pytest.mark.parametrize(
    "value,expected",
    [
        (1, "1"),
        (95, "95"),
        (93.4, "93.4"),
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
    REFERENCE = reference_fixture()
    projection = integrity_projection(REFERENCE)
    assert set(projection) <= {"dppId", "recordVersion", "updatedAt", "identity", "product", "materialObservations"}
