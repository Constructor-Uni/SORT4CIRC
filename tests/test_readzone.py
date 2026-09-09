"""Read-zone safety.

The acceptance rule from the deliverable is zero uncontrolled sorting commands
across repeated executions of every negative case, and full agreement between
the observed reason code and the expected one.
"""

from __future__ import annotations

import itertools

import pytest

from sort4circ_dpp.gateway import ReadZone

EPC = "urn:epc:id:sgtin:0614141.112345.400"
OTHER = "urn:epc:id:sgtin:0614141.112345.401"

NEGATIVE_CASES = [
    ("empty window", [], "S4C-IDENT-UNKNOWN"),
    ("two tags", [{"epc": EPC}, {"epc": OTHER}], "S4C-IDENT-AMBIGUOUS"),
    ("three tags", [{"epc": EPC}, {"epc": OTHER}, {"epc": EPC}], "S4C-IDENT-AMBIGUOUS"),
    ("malformed", [{"epc": "not-an-epc"}], "S4C-IDENT-MALFORMED"),
    ("empty string", [{"epc": ""}], "S4C-IDENT-MALFORMED"),
    ("missing member", [{}], "S4C-IDENT-MALFORMED"),
    ("non-string", [{"epc": 12345}], "S4C-IDENT-MALFORMED"),
    ("weak signal", [{"epc": EPC, "rssiDbm": -95}], "S4C-READ-WEAK-SIGNAL"),
]

EXECUTIONS = 100


@pytest.mark.parametrize("name,reads,expected", NEGATIVE_CASES, ids=[c[0] for c in NEGATIVE_CASES])
def test_negative_case_never_permits_a_command(name, reads, expected):
    zone = ReadZone()
    commands = 0
    codes = set()
    for _ in range(EXECUTIONS):
        result = zone.evaluate(list(reads))
        codes.add(result.reason_code)
        if result.may_command:
            commands += 1
    assert commands == 0, f"{name} produced {commands} uncontrolled commands"
    assert codes == {expected}, f"{name} produced {codes}, expected {expected}"


def test_an_accepted_read_permits_exactly_one_command():
    zone = ReadZone()
    result = zone.evaluate([{"epc": EPC, "rssiDbm": -52}])
    assert result.may_command
    assert result.epc == EPC


def test_a_repeat_inside_the_window_is_suppressed_and_is_not_an_error():
    zone = ReadZone()
    assert zone.evaluate([{"epc": EPC}]).may_command
    repeat = zone.evaluate([{"epc": EPC}])
    assert not repeat.may_command
    assert repeat.reason_code == "S4C-READ-SUPPRESSED-DUPLICATE"
    assert repeat.safe_action == "noCommand", "a suppressed repeat diverts nothing"


def test_a_repeat_after_the_window_is_accepted_again():
    ticks = itertools.count(0.0, 1.0)  # one simulated second per call
    zone = ReadZone(_clock=lambda: next(ticks))
    assert zone.evaluate([{"epc": EPC}]).may_command
    assert zone.evaluate([{"epc": EPC}]).may_command


def test_ambiguity_is_not_retried_away():
    """Two tags in the zone is a state, not a transient fault.

    Repeating the evaluation must keep returning the same answer, because the
    system still does not know which garment faces the actuator.
    """
    zone = ReadZone()
    for _ in range(10):
        assert zone.evaluate([{"epc": EPC}, {"epc": OTHER}]).reason_code == "S4C-IDENT-AMBIGUOUS"


def test_every_diverting_case_is_declared_as_diverting():
    for _, _reads, expected in NEGATIVE_CASES:
        if expected == "S4C-READ-SUPPRESSED-DUPLICATE":
            continue
        assert ReadZone.diverts(expected), f"{expected} must route the garment to manual review"
