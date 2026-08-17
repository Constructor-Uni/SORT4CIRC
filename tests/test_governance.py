"""D4.3 environmental-selection and EN 18223 deviation gates."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from sort4circ_dpp.governance import validate_en18223_deviation, validate_environmental_selection

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "spec" / "governance"


def person(identifier: str, role: str, coordinator: bool = False) -> dict:
    return {"individualId": identifier, "name": identifier, "role": role, "isProjectCoordinator": coordinator}


def environmental_record() -> dict:
    return {
        "recordType": "environmentalPlatformSelection", "recordVersion": "1.0.0",
        "preparationDate": "2026-08-01", "preparedBy": person("cu-a", "CU WP4 team preparer"),
        "resultReporterOrRecommender": person("cu-b", "CU recommender"),
        "limitApprover": person("cu-c", "CU T1.4 approver", True), "approvalDate": "2026-08-02",
        "acceptancePlan": [{
            "evidencePath": "projectMetered", "environmentalMetric": "kWhPer10000AcceptedSubmissions",
            "systemBoundary": "named nodes and adapter above matched idle baseline",
            "evidenceSource": "meter export and dated electricity factor", "maximumAcceptableResult": 10,
            "rationale": "synthetic validator fixture only; not a project threshold",
        }],
        "candidates": [{
            "candidateId": "synthetic-a", "projectOperated": True, "evidencePath": "projectMetered",
            "environmentalMetric": "kWhPer10000AcceptedSubmissions",
            "systemBoundary": "named nodes and adapter above matched idle baseline",
            "evidenceSource": "synthetic validator fixture", "evidenceSufficiency": "sufficient",
            "measuredResult": 9, "passAgainstFrozenMaximum": True, "selected": False,
        }],
        "deploymentAuthorization": "demonstratorDeployment",
    }


def test_environmental_template_contains_no_invented_completed_evidence():
    template = json.loads((GOV / "environmental-selection-template.json").read_text(encoding="utf-8"))
    assert template["deploymentAuthorization"] == "architectureAndMigrationPlanningOnly"
    assert template["candidates"][0]["evidenceSufficiency"] == "pending"
    assert template["candidates"][0]["measuredResult"] is None
    assert validate_environmental_selection(template), "an unpopulated template must not validate as a decision"


def test_environmental_record_requires_separation_of_duties():
    record = environmental_record()
    record["limitApprover"] = deepcopy(record["preparedBy"])
    assert any("different named CU individual" in error for error in validate_environmental_selection(record))


def test_project_coordinator_may_approve_only_when_not_preparer_or_reporter():
    record = environmental_record()
    assert not validate_environmental_selection(record)
    record["preparedBy"] = deepcopy(record["limitApprover"])
    assert validate_environmental_selection(record)


def test_candidate_exceeding_frozen_maximum_cannot_pass_or_be_selected():
    record = environmental_record()
    candidate = record["candidates"][0]
    candidate.update({"measuredResult": 11, "passAgainstFrozenMaximum": True, "selected": True})
    errors = validate_environmental_selection(record)
    assert any("pass/fail" in error for error in errors)
    assert any("cannot be selected" in error for error in errors)


def test_no_eligible_project_candidate_forces_planning_only():
    record = environmental_record()
    record["candidates"][0].update({"evidenceSufficiency": "pending", "measuredResult": None, "passAgainstFrozenMaximum": None})
    errors = validate_environmental_selection(record)
    assert any("only architecture and migration planning" in error for error in errors)
    record["deploymentAuthorization"] = "architectureAndMigrationPlanningOnly"
    assert not validate_environmental_selection(record)


def test_en18223_template_is_open_and_cannot_be_mistaken_for_closed():
    template = json.loads((GOV / "en18223-deviation-open-template.json").read_text(encoding="utf-8"))
    assert template["status"] == "open"
    assert template["approvedBy"] is None and template["decisionDate"] is None
    assert set(template["affectedClauses"]) == {"Clause 5", "Annex A", "Annex B"}
    assert validate_en18223_deviation(template), "the unpopulated open template is not completed evidence"


def test_en18223_closed_record_requires_different_approver_and_closure_evidence():
    template = json.loads((GOV / "en18223-deviation-open-template.json").read_text(encoding="utf-8"))
    template.update({
        "fieldLevelMapping": [{"sort4circField": "dppId", "en18223DataElement": "synthetic-test"}],
        "preparedBy": {"individualId": "cu-a", "name": "cu-a", "role": "CU WP4 preparer"},
        "recommendation": "synthetic test recommendation", "status": "closed",
        "approvedBy": {"individualId": "cu-a", "name": "cu-a", "role": "CU approver"},
        "decisionDate": "2026-08-03", "closureEvidence": ["synthetic test artefact"],
        "notification": {"recipient": "TXHO D5.2 lead", "notifiedAt": "2026-08-04"},
    })
    assert any("different named CU individual" in error for error in validate_en18223_deviation(template))
