"""RESTful passport API.

Implements the interface contract of D4.3 Annex B. Every response carries the
correlation identifier the caller supplied, every error is an RFC 9457 problem
document carrying a released reason code, and every representation carries the
record version it was produced from.

Authentication here is a header-based stand-in for the OAuth 2.0 or OIDC profile
the security guideline requires. It is confined to :func:`principal_from_request`
so that a deployment replaces one function and changes nothing else. The
stand-in is refused when ``S4C_ALLOW_HEADER_AUTH`` is not set, so it cannot be
enabled by accident outside development.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from . import canonical
from .access import Principal, check_patch_paths, project, require_scope, resolve_view
from .config import API_MAJOR, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, SCHEMA_VERSION
from .evidence import EvidenceWorker
from .index import ReadIndex
from .ledger.base import LedgerAdapter
from .ledger.memory import InMemoryLedger
from .reasons import DppError
from .store import PassportStore, etag, new_urn, utcnow

BASE = f"/{API_MAJOR}"


def _correlation(supplied: str | None) -> str:
    return supplied or str(uuid.uuid4())


def create_app(
    store: PassportStore | None = None,
    ledger: LedgerAdapter | None = None,
) -> FastAPI:
    store = store or PassportStore()
    ledger = ledger or InMemoryLedger()
    index = ReadIndex(store=store)
    index.attach()
    worker = EvidenceWorker(store=store, ledger=ledger)

    app = FastAPI(
        title="SORT4CIRC Digital Product Passport API",
        version=SCHEMA_VERSION,
        description=(
            "Reference implementation of the API requirements developed under "
            "SORT4CIRC Task 4.2 and published in deliverable D4.3. Errors use "
            "RFC 9457 problem details and carry a reason code from the released "
            "catalogue in spec/reason-codes.json."
        ),
    )
    app.state.store = store
    app.state.ledger = ledger
    app.state.index = index
    app.state.worker = worker

    # ------------------------------------------------------------- plumbing

    @app.exception_handler(DppError)
    async def _dpp_error_handler(request: Request, exc: DppError) -> JSONResponse:
        correlation = _correlation(request.headers.get("x-correlation-id"))
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.problem(instance=str(request.url.path), correlation_id=correlation),
            media_type="application/problem+json",
            headers={"X-Correlation-Id": correlation},
        )

    @app.middleware("http")
    async def _correlate(request: Request, call_next: Callable) -> Response:
        correlation = _correlation(request.headers.get("x-correlation-id"))
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation
        return response

    def principal_from_request(
        x_s4c_role: str | None = Header(default=None),
        x_s4c_subject: str | None = Header(default=None),
        x_s4c_organisation: str | None = Header(default=None),
    ) -> Principal:
        """Resolve the caller.

        Replace this function with token validation that verifies issuer,
        audience, signature, expiry, not-before time and authorised party. The
        rest of the service depends only on the returned Principal.
        """
        if x_s4c_role is None:
            return Principal(subject="anonymous", role="public")
        if not os.environ.get("S4C_ALLOW_HEADER_AUTH"):
            raise DppError(
                "S4C-AUTH-INVALID-TOKEN",
                "header authentication is disabled; set S4C_ALLOW_HEADER_AUTH for development use",
            )
        from .access import matrix

        if x_s4c_role not in matrix()["roles"]:
            raise DppError("S4C-AUTH-INVALID-TOKEN", f"unknown role {x_s4c_role!r}")
        return Principal(
            subject=x_s4c_subject or "unknown",
            role=x_s4c_role,
            organisation_id=x_s4c_organisation,
        )

    Caller = Depends(principal_from_request)

    def _respond(record: dict[str, Any], view: str, principal: Principal, response: Response) -> dict[str, Any]:
        response.headers["ETag"] = etag(record)
        response.headers["Cache-Control"] = "no-store"
        return project(record, view, principal)

    # -------------------------------------------------------------- lifecycle

    @app.post(f"{BASE}/dpps", status_code=201)
    def create_dpp(
        payload: dict[str, Any],
        response: Response,
        principal: Principal = Caller,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        require_scope(principal, "dpp.write")
        cached = store.idempotent(idempotency_key, payload)
        if cached is not None:
            response.status_code = 201
            response.headers["Location"] = f"{BASE}/dpps/{cached['dppId']}"
            return cached
        record = store.create(payload)
        result = project(record, "full", principal)
        store.remember(idempotency_key, payload, result)
        response.headers["Location"] = f"{BASE}/dpps/{record['dppId']}"
        response.headers["ETag"] = etag(record)
        return result

    @app.get(f"{BASE}/dpps/{{dpp_id:path}}/sorting-view")
    def sorting_view(
        dpp_id: str,
        response: Response,
        consistency: str = Query(default="projected", pattern="^(projected|strong)$"),
        principal: Principal = Caller,
    ) -> dict[str, Any]:
        require_scope(principal, "sorting.read")
        view = index.sorting_view(dpp_id, strong=consistency == "strong")
        response.headers["Cache-Control"] = "no-store"
        return view

    @app.get(f"{BASE}/dpps/{{dpp_id:path}}/integrity")
    def integrity(dpp_id: str, principal: Principal = Caller) -> dict[str, Any]:
        require_scope(principal, "integrity.read")
        record = store.get(dpp_id)
        return {
            "dppId": record["dppId"],
            "recordVersion": record["recordVersion"],
            "integrity": [entry.as_integrity_entry() for entry in store.outbox if entry.dpp_id == dpp_id],
        }

    @app.post(f"{BASE}/dpps/{{dpp_id:path}}/integrity/verify")
    def verify(dpp_id: str, body: dict[str, Any], principal: Principal = Caller) -> dict[str, Any]:
        require_scope(principal, "integrity.verify")
        evidence_id = body.get("evidenceId")
        entry = next((e for e in store.outbox if e.evidence_id == evidence_id), None)
        if entry is None:
            raise DppError("S4C-STATE-NOT-FOUND", f"{evidence_id} is not a known evidence identifier")

        try:
            subject = store.get_version(entry.dpp_id, entry.subject_version)
        except DppError:
            return {
                "evidenceId": evidence_id,
                "subjectRef": entry.dpp_id,
                "subjectVersion": entry.subject_version,
                "verdict": "unverifiable",
                "reasonCode": "S4C-STATE-NOT-FOUND",
            }

        recomputed = canonical.digest(subject)
        verdict = ledger.verify(evidence_id, recomputed)
        result: dict[str, Any] = {
            "evidenceId": evidence_id,
            "subjectRef": entry.dpp_id,
            "subjectVersion": entry.subject_version,
            "canonicalisation": entry.canonicalisation,
            "digestAlgorithm": entry.digest_algorithm,
            "recomputedDigest": recomputed,
            "anchoredDigest": ledger.anchored_digest(evidence_id),
            "ledgerNetworkId": entry.ledger_network_id,
            "transactionRef": entry.transaction_ref,
            "confirmedAt": entry.confirmed_at,
            "verdict": verdict,
        }
        if verdict == "mismatch":
            result["reasonCode"] = "S4C-LEDGER-DIGEST-MISMATCH"
        return result

    @app.post(f"{BASE}/dpps/{{dpp_id:path}}/events", status_code=201)
    def add_event(
        dpp_id: str,
        payload: dict[str, Any],
        response: Response,
        principal: Principal = Caller,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        require_scope(principal, "dpp.event")
        cached = store.idempotent(idempotency_key, payload)
        if cached is not None:
            return cached
        event = dict(payload)
        event.setdefault("eventId", new_urn("event"))
        event.setdefault("recordedAt", utcnow())
        event.setdefault("actorOrganisationId", principal.organisation_id or f"urn:sort4circ:org:{principal.role}")
        record = store.append(dpp_id, "lifecycleEvents", event, "eventId")
        result = {"eventId": event["eventId"], "dppId": dpp_id, "recordVersion": record["recordVersion"]}
        store.remember(idempotency_key, payload, result)
        response.headers["Location"] = f"{BASE}/dpps/{dpp_id}/events/{event['eventId']}"
        response.headers["ETag"] = etag(record)
        return result

    @app.post(f"{BASE}/dpps/{{dpp_id:path}}/observations", status_code=201)
    def add_observation(
        dpp_id: str,
        payload: dict[str, Any],
        response: Response,
        principal: Principal = Caller,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        require_scope(principal, "observation.write")
        cached = store.idempotent(idempotency_key, payload)
        if cached is not None:
            return cached
        observation = {k: v for k, v in payload.items() if k not in ("observationType", "basedOnRecordVersion", "schemaVersion")}
        observation.setdefault("observationId", new_urn("obs"))
        record = store.append(dpp_id, "materialObservations", observation, "observationId")
        result = {
            "observationId": observation["observationId"],
            "dppId": dpp_id,
            "recordVersion": record["recordVersion"],
        }
        store.remember(idempotency_key, payload, result)
        response.headers["Location"] = f"{BASE}/dpps/{dpp_id}/observations/{observation['observationId']}"
        response.headers["ETag"] = etag(record)
        return result

    @app.post(f"{BASE}/dpps/{{dpp_id:path}}/carriers", status_code=201)
    def commission(
        dpp_id: str,
        payload: dict[str, Any],
        response: Response,
        principal: Principal = Caller,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        require_scope(principal, "dpp.write")
        cached = store.idempotent(idempotency_key, payload)
        if cached is not None:
            return cached
        record = store.commission_carrier(dpp_id, payload)
        result = {
            "dppId": dpp_id,
            "recordVersion": record["recordVersion"],
            "carriers": record["carriers"],
        }
        store.remember(idempotency_key, payload, result)
        response.headers["ETag"] = etag(record)
        return result

    @app.get(f"{BASE}/identifiers/{{carrier_id:path}}/dpp")
    def resolve(
        carrier_id: str,
        response: Response,
        view: str | None = Query(default=None),
        principal: Principal = Caller,
    ) -> dict[str, Any]:
        require_scope(principal, "dpp.resolve")
        record = store.resolve_carrier(unquote(carrier_id))
        selected = resolve_view(principal, view or "sorting")
        return _respond(record, selected, principal, response)

    @app.get(f"{BASE}/dpps")
    def search(
        response: Response,
        cursor: str | None = Query(default=None),
        limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
        principal: Principal = Caller,
    ) -> dict[str, Any]:
        require_scope(principal, "dpp.read")
        # Deterministic order on (updatedAt, dppId). Offset pagination is not
        # offered because it omits or duplicates records when the collection
        # changes during traversal, and a passport collection changes
        # continuously.
        records = sorted(store, key=lambda r: (r["updatedAt"], r["dppId"]))
        start = 0
        if cursor:
            for position, record in enumerate(records):
                if record["dppId"] == cursor:
                    start = position + 1
                    break
        page = records[start : start + limit]
        view = principal.default_view
        body: dict[str, Any] = {"items": [project(r, view, principal) for r in page]}
        if start + limit < len(records):
            body["nextCursor"] = page[-1]["dppId"]
        return body

    @app.get(f"{BASE}/dpps/{{dpp_id:path}}")
    def get_dpp(
        dpp_id: str,
        response: Response,
        view: str | None = Query(default=None),
        principal: Principal = Caller,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ) -> Any:
        require_scope(principal, "dpp.read")
        record = store.get(dpp_id)
        current = etag(record)
        if if_none_match and if_none_match.strip('"') == current.strip('"'):
            return Response(status_code=304, headers={"ETag": current})
        return _respond(record, resolve_view(principal, view), principal, response)

    @app.patch(f"{BASE}/dpps/{{dpp_id:path}}")
    def patch_dpp(
        dpp_id: str,
        payload: dict[str, Any],
        response: Response,
        principal: Principal = Caller,
        if_match: str | None = Header(default=None, alias="If-Match"),
    ) -> dict[str, Any]:
        require_scope(principal, "dpp.write")
        check_patch_paths(principal, payload)
        record = store.patch(dpp_id, payload, if_match)
        return _respond(record, "full", principal, response)

    # -------------------------------------------------------------- operations

    @app.post(f"{BASE}/internal/evidence/drain")
    def drain(principal: Principal = Caller) -> dict[str, Any]:
        require_scope(principal, "admin")
        return {"states": worker.drain()}

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "schemaVersion": SCHEMA_VERSION,
            "passports": len(store),
            "indexed": len(index),
            "evidence": worker.histogram(),
        }

    return app


app = create_app()
