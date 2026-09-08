"""Composition and payload rules."""

from __future__ import annotations

import pytest

from conftest import passport_payload
from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.validation import check_composition, observation_sets


def observation(fibre, percentage, method="labQuantitativeIso1833", at="2041-03-05T14:20:00Z", source="urn:example:org:sorter-a"):
    return {
        "observationId": f"urn:example:obs:{fibre}-{percentage}-{method}",
        "fibreType": fibre,
        "percentage": percentage,
        "percentageBasis": "mass",
        "valueStatus": "supplied",
        "method": method,
        "sourceOrganisationId": source,
        "observedAt": at,
    }


def test_a_complete_set_summing_to_one_hundred_is_accepted():
    record = passport_payload()
    check_composition(record)


def test_a_set_exceeding_one_hundred_is_refused():
    record = passport_payload()
    record["materialObservations"] = [observation("polyester", 95), observation("elastane", 20)]
    with pytest.raises(DppError):
        check_composition(record)


def test_a_partial_set_is_accepted_without_a_fabricated_residual():
    """An instrument that finds only the majority fibre has made a true statement."""
    record = passport_payload()
    record["materialObservations"] = [observation("polyester", 58.25, method="nirSpectroscopy")]
    check_composition(record)


def test_two_technologies_disagreeing_do_not_sum_together():
    """The append-only model exists so a second opinion can be retained.

    A laboratory set of 95 plus 5 and a later near-infrared set of 58.25 sums to
    158.25 across the array and is entirely correct. Applying the rule across
    sets would make a second opinion look like a contradiction.
    """
    record = passport_payload()
    record["materialObservations"].append(
        observation("polyester", 58.25, method="nirSpectroscopy", at="2041-03-05T14:20:00Z",
                    source="urn:example:org:sorter-a")
    )
    check_composition(record)
    assert len(observation_sets(record)) == 2


def test_a_declared_set_is_not_confused_with_a_measured_one():
    record = passport_payload()
    record["materialObservations"] = [
        observation("cotton", 100, method="labelDeclaration"),
        observation("cotton", 97.2, method="labQuantitativeIso1833"),
    ]
    check_composition(record)
    assert len(observation_sets(record)) == 2
