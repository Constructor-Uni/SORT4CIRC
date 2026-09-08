"""Synthetic example. Not SORT4CIRC project data."""
import json
from pathlib import Path

import pytest

from sort4circ_dpp.reasons import DppError
from sort4circ_dpp.synthetic import SyntheticFixtureFactory
from sort4circ_dpp.validation import validate_payload


@pytest.mark.parametrize("name,document", list(SyntheticFixtureFactory().fixtures().items()))
def test_generated_fixture_matches_file_and_expected_validation(name, document):
    root = Path(__file__).resolve().parents[1]
    assert json.loads((root / "examples" / "fixtures" / name).read_text()) == document
    payload = dict(document)
    expected = payload.pop("$expect", None)
    if expected:
        with pytest.raises(DppError) as raised:
            validate_payload(payload)
        assert raised.value.code == expected
    else:
        validate_payload(payload)

def test_factory_is_deterministic_and_returns_independent_records():
    factory = SyntheticFixtureFactory()
    first = factory.passport()
    first["materialObservations"].clear()
    assert factory.passport() == factory.passport()
    assert len(factory.passport()["materialObservations"]) == 2
    assert factory.passport(2)["identity"]["itemId"] != factory.passport(1)["identity"]["itemId"]
