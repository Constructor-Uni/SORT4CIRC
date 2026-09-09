"""Cross-record validation for D4.3 governance templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_DIR = ROOT / "spec" / "governance"


def _schema(name: str) -> dict[str, Any]:
    return json.loads((GOVERNANCE_DIR / name).read_text(encoding="utf-8"))


def _schema_errors(document: dict[str, Any], name: str) -> list[str]:
    validator = Draft202012Validator(_schema(name), format_checker=FormatChecker())
    return [error.message for error in sorted(validator.iter_errors(document), key=lambda error: list(error.path))]


def validate_environmental_selection(document: dict[str, Any]) -> list[str]:
    errors = _schema_errors(document, "environmental-selection.schema.json")
    if errors:
        return errors
    preparer = document["preparedBy"]["individualId"]
    reporter = document["resultReporterOrRecommender"]["individualId"]
    approver = document["limitApprover"]["individualId"]
    if approver in {preparer, reporter}:
        errors.append("limit approver must be a different named individual from the preparer and the reporter/recommender")

    plans = {(item["evidencePath"], item["environmentalMetric"]): item for item in document["acceptancePlan"]}
    eligible_project_candidate = False
    for candidate in document["candidates"]:
        key = (candidate["evidencePath"], candidate["environmentalMetric"])
        plan = plans.get(key)
        if plan is None:
            errors.append(f"{candidate['candidateId']}: no frozen acceptance-plan item for evidence path and metric")
            continue
        if candidate["systemBoundary"] != plan["systemBoundary"]:
            errors.append(f"{candidate['candidateId']}: candidate and frozen-limit system boundaries differ")
        result = candidate["measuredResult"]
        passed = candidate["passAgainstFrozenMaximum"]
        if result is not None:
            expected = result <= plan["maximumAcceptableResult"]
            if passed is not expected:
                errors.append(f"{candidate['candidateId']}: pass/fail does not match the frozen maximum")
        if candidate["selected"] and (
            candidate["evidenceSufficiency"] != "sufficient"
            or passed is not True
            or (result is not None and not expected)
        ):
            errors.append(f"{candidate['candidateId']}: an insufficient, pending, or failing candidate cannot be selected")
        eligible_project_candidate |= (
            candidate["projectOperated"]
            and candidate["evidenceSufficiency"] == "sufficient"
            and passed is True
        )
    if not eligible_project_candidate and document["deploymentAuthorization"] != "architectureAndMigrationPlanningOnly":
        errors.append("without an evidenced acceptable project-operated candidate, only architecture and migration planning is authorised")
    return errors


def validate_en18223_deviation(document: dict[str, Any]) -> list[str]:
    errors = _schema_errors(document, "en18223-deviation.schema.json")
    if errors:
        return errors
    if set(document["affectedClauses"]) != {"Clause 5", "Annex A", "Annex B"}:
        errors.append("affected clauses must include Clause 5 and Annex A/B")
    approver = document["approvedBy"]
    if approver is not None and approver["individualId"] == document["preparedBy"]["individualId"]:
        errors.append("deviation approver must be a different named individual from the preparer")
    if document["status"] == "closed" and not document["fieldLevelMapping"]:
        errors.append("the deviation cannot close without the validated field-level mapping")
    return errors
