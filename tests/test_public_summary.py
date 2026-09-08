"""Public output cannot inherit free text from private records."""
import json

import pytest

from sort4circ_dpp.public_summary import PublicConformanceSummary


def test_export_uses_only_known_identifiers_statuses_and_fixed_metadata():
    sentinel = "fictional-private-machine-Z"
    raw = {"results": {"schema": "pass", sentinel: "pass"},
           "environment": {"TOKEN": sentinel}, "path": sentinel,
           "username": sentinel, "digest": sentinel, "limitations": sentinel}
    result = PublicConformanceSummary.from_private_results(raw).document()
    assert sentinel not in json.dumps(result)
    assert set(result) == {"publicProfileVersion", "specificationVersion",
                           "publicImplementationVersion", "syntheticDataset", "results", "limitations"}

@pytest.mark.parametrize("value", ["fictional-secret", {}, [], None])
def test_arbitrary_status_is_rejected(value):
    with pytest.raises(ValueError):
        PublicConformanceSummary.from_private_results({"results": {"api": value}})

def test_unknown_or_duplicate_test_identifier_is_rejected():
    with pytest.raises(ValueError):
        PublicConformanceSummary((("unknown", "pass"),))
    with pytest.raises(ValueError):
        PublicConformanceSummary((("api", "pass"), ("api", "fail")))
