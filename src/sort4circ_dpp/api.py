"""The /v1 exchange API of the SORT4CIRC DPP implementation profile.

Every response carries a correlation identifier and the record version it was produced
from. Application errors and body-level request-validation errors both use RFC 9457
problem details with a released reason code; non-body validation and routing responses
keep their FastAPI/Starlette behaviour.

Identity is confined to :mod:`sort4circ_dpp.auth`, so a deployment replaces one provider
and changes nothing else. The default provider is fail-closed: it grants read-only public
access and refuses claimed role headers. The header-based demo identity is opt-in through
``DPP_DEMO_AUTH=1`` and is not authentication.

JSON is the normative representation. XML is offered by content negotiation and is
produced and parsed by :mod:`sort4circ_dpp.exchange`.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import canonical
from .access import Principal, check_patch_paths, project, require_scope, resolve_view
from .auth import AuthProvider, DemoAuth, PublicOnlyAuth
from .config import API_CONTRACT_VERSION, API_MAJOR, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, SCHEMA_VERSION
from .evidence import EvidenceWorker
from .exchange import from_xml, to_xml
from .index import ReadIndex
from .ledger.base import LedgerAdapter
from .ledger.memory import InMemoryLedger
from .reasons import DppError
from .store import PassportStore, etag, new_urn, utcnow

BASE = f"/{API_MAJOR}"


def _correlation(supplied: str | None) -> str:
    return supplied or str(uuid.uuid4())


def _request_correlation(request: Request) -> str:
    """Reuse the identifier the middleware minted, so one request has exactly one."""
    existing = getattr(request.state, "correlation_id", None)
    return existing or _correlation(request.headers.get("x-correlation-id"))


def _scoped_key(principal: Principal, key: str | None, operation: str, resource: str) -> str | None:
    if key is None:
        return None
    return json.dumps([principal.subject, principal.organisation_id, principal.role, operation, resource, key])


def create_app(
    store: PassportStore | None = None,
    ledger: LedgerAdapter | None = None,
    auth_provider: AuthProvider | None = None,
) -> FastAPI:
    store = store or PassportStore()
    ledger = ledger or InMemoryLedger()
    index = ReadIndex(store=store)
    index.attach()
    worker = EvidenceWorker(store=store, ledger=ledger)

    app = FastAPI(
        title="SORT4CIRC Digital Product Passport API",
        version=API_CONTRACT_VERSION,
        license_info={
            "name": "Creative Commons Attribution 4.0 International",
            "url": "https://creativecommons.org/licenses/by/4.0/",
        },
        description=(
            "The /v1 exchange API of the SORT4CIRC DPP implementation profile. Application "
            "and body-validation errors use RFC 9457 problem details with a reason code from "
            "spec/reason-codes.json. Examples are synthetic; no deployment or legal conformity "
            "is represented."
        ),
    )
    provider = auth_provider or (DemoAuth() if os.environ.get("DPP_DEMO_AUTH") == "1" else PublicOnlyAuth())

    app.state.store = store
    app.state.ledger = ledger
    app.state.index = index
    app.state.worker = worker

    # ------------------------------------------------------------- plumbing

    @app.exception_handler(DppError)
    async def _dpp_error_handler(request: Request, exc: DppError) -> JSONResponse:
        correlation = _request_correlation(request)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.problem(instance=str(request.url.path), correlation_id=correlation),
            media_type="application/problem+json",
            headers={"X-Correlation-Id": correlation},
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation_error_handler(request: Request, exc: RequestValidationError) -> Response:
        """Body-level validation failures use the profile's problem format, not FastAPI's.

        Path, query and header validation keep framework behaviour: only a malformed or
        schema-invalid *body* is a profile payload error.
        """
        errors = exc.errors()
        if not errors or any(not error.get("loc") or error["loc"][0] != "body" for error in errors):
            return await request_validation_exception_handler(request, exc)
        correlation = _request_correlation(request)
        problem = DppError(
            "S4C-PAYLOAD-SCHEMA-INVALID",
            "request body failed schema validation",
            fields=["body"],
        ).problem(instance=str(request.url.path), correlation_id=correlation)
        return JSONResponse(
            status_code=422,
            content=problem,
            media_type="application/problem+json",
            headers={"X-Correlation-Id": correlation},
        )

    @app.middleware("http")
    async def _correlate(request: Request, call_next: Callable) -> Response:
        correlation = _correlation(request.headers.get("x-correlation-id"))
        request.state.correlation_id = correlation

        # XML in: validate against the released XSD, then hand JSON to the route.
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() == "application/xml":
            try:
                payload = from_xml(await request.body())
            except Exception as exc:  # XSD/profile failures use the stable payload contract
                problem = DppError(
                    "S4C-PAYLOAD-SCHEMA-INVALID",
                    f"XML request failed XSD or profile validation: {exc}",
                    fields=["body"],
                ).problem(instance=str(request.url.path), correlation_id=correlation)
                return JSONResponse(
                    status_code=422,
                    content=problem,
                    media_type="application/problem+json",
                    headers={"X-Correlation-Id": correlation},
                )
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            request._body = body  # noqa: SLF001 - normalise XML before FastAPI body parsing
            request.scope["headers"] = [
                (name, value)
                for name, value in request.scope["headers"]
                if name not in {b"content-type", b"content-length"}
            ] + [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]

        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation

        # XML out: only for a whole passport record, never for a projection or problem.
        accept = request.headers.get("accept", "").lower()
        if (
            "application/xml" in accept
            and 200 <= response.status_code < 300
            and response.headers.get("content-type", "").startswith("application/json")
        ):
            body = b"".join([chunk async for chunk in response.body_iterator])
            document = json.loads(body)
            required = {
                "dppId", "schemaVersion", "recordVersion", "status", "createdAt", "updatedAt",
                "responsibleOperatorId", "identity", "product", "materialObservations",
            }
            if required <= document.keys():
                headers = dict(response.headers)
                headers.pop("content-length", None)
                headers.pop("content-type", None)
                headers["Vary"] = "Accept"
                return Response(
                    content=to_xml(document),
                    status_code=response.status_code,
                    headers=headers,
                    media_type="application/xml",
                )
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        return response

    def principal_from_request(request: Request) -> Principal:
        return provider.authenticate(request.headers)

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
        idempotency_key = _scoped_key(principal, idempotency_key, "create", "")
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
        entry = next((e for e in store.outbox if e.evidence_id == evidence_id and e.dpp_id == dpp_id), None)
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
        idempotency_key = _scoped_key(principal, idempotency_key, "event", dpp_id)
        cached = store.idempotent(idempotency_key, payload)
        if cached is not None:
            return cached
        event = dict(payload)
        event.setdefault("eventId", new_urn("event"))
        event.setdefault("recordedAt", utcnow())
        event.setdefault("actorOrganisationId", principal.organisation_id or f"urn:example:org:{principal.role}")
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
        idempotency_key = _scoped_key(principal, idempotency_key, "observation", dpp_id)
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
        idempotency_key = _scoped_key(principal, idempotency_key, "carrier", dpp_id)
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

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "schemaVersion": SCHEMA_VERSION}


    return app


app = create_app()
