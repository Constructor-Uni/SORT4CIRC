"""Small integration checks for the versioned public profile."""
from sort4circ_dpp.canonical import digest
from sort4circ_dpp.ledger.memory import InMemoryLedger
from sort4circ_dpp.synthetic import SyntheticFixtureFactory
from sort4circ_dpp.validation import validate_payload


def test_synthetic_profile_integrity_roundtrip():
    record = SyntheticFixtureFactory().passport()
    validate_payload(record)
    value = digest(record)
    ledger = InMemoryLedger()
    ledger.submit("urn:example:evidence:profile", {"digestValue": value})
    assert ledger.verify("urn:example:evidence:profile", value) == "match"
