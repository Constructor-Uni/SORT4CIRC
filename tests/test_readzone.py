"""Carrier classification only; no hardware or physical control claims."""
import pytest

from sort4circ_dpp.gateway import CarrierResolver, ReadObservation


@pytest.mark.parametrize("reads,code", [
    ([], "S4C-IDENT-UNKNOWN"),
    ([ReadObservation("urn:example:carrier:a"), ReadObservation("urn:example:carrier:b")], "S4C-IDENT-AMBIGUOUS"),
    ([ReadObservation(None)], "S4C-IDENT-MALFORMED"),
    ([ReadObservation("not a uri")], "S4C-IDENT-MALFORMED"),
    ([ReadObservation("https://[broken")], "S4C-IDENT-MALFORMED"),
    ([ReadObservation("urn:example:carrier:a", readable=False)], "S4C-IDENT-MALFORMED"),
])
def test_rejected_observation_never_resolves(reads, code):
    result = CarrierResolver().evaluate(reads)
    assert not result.may_resolve
    assert result.reason_code == code

def test_readable_identifier_can_be_resolved():
    value = "urn:example:carrier:fictional"
    assert CarrierResolver().evaluate([ReadObservation(value)]).identifier == value
    assert CarrierResolver().evaluate([ReadObservation(value)]).may_resolve
