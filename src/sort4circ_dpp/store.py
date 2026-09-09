"""In-memory passport versions, append-only records and a simulated outbox.

The reference store is process-local and in-memory. It is deliberately simple
so the invariants stay visible; a production deployment replaces it with a
durable database while keeping the same invariants, which are:

* every accepted write increments ``recordVersion`` and retains the prior version;
* material observations, lifecycle events, sorting decisions and integrity
  entries are append only;
* at most one carrier binding per passport is in the ``commissioned`` state;
* an identifier is never reassigned to a different product;
* the passport update and its evidence-queue entry commit together, through the
  transactional outbox, or neither commits.

No durable storage or restart recovery is provided here, and no deployment is modelled.
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from . import canonical
from .config import ACCESS_POLICY_VERSION, SCHEMA_VERSION
from .reasons import DppError
from .validation import validate_payload


def utcnow() -> str:
    """Return the current instant as RFC 3339 with an explicit offset."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_urn(kind: str) -> str:
    return f"urn:example:{kind}:{uuid.uuid4()}"


@dataclass
class OutboxEntry:
    """A unit of work committed atomically with the passport write."""

    evidence_id: str
    dpp_id: str
    subject_version: int
    digest_value: str
    canonicalisation: str
    digest_algorithm: str
    created_at: str
    state: str = "created"
    attempts: int = 0
    transaction_ref: str | None = None
    ledger_network_id: str | None = None
    confirmed_at: str | None = None
    last_reason_code: str | None = None

    def as_integrity_entry(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "evidenceId": self.evidence_id,
            "subjectRef": self.dpp_id,
            "subjectVersion": self.subject_version,
            "canonicalisation": self.canonicalisation,
            "digestAlgorithm": self.digest_algorithm,
            "digestValue": self.digest_value,
            "evidenceState": self.state,
            "createdAt": self.created_at,
            "attempts": self.attempts,
        }
        for key, value in (
            ("ledgerNetworkId", self.ledger_network_id),
            ("transactionRef", self.transaction_ref),
            ("confirmedAt", self.confirmed_at),
            ("lastReasonCode", self.last_reason_code),
        ):
            if value is not None:
                entry[key] = value
        return entry


@dataclass
class _IdempotencyRecord:
    request_digest: str
    response: Any
    created_at: str


@dataclass
class PassportStore:
    """Authoritative passport records and their history."""

    _records: dict[str, dict[str, Any]] = field(default_factory=dict)
    _history: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    _carrier_index: dict[str, str] = field(default_factory=dict)
    _retired_carriers: dict[str, str] = field(default_factory=dict)
    _idempotency: dict[str, _IdempotencyRecord] = field(default_factory=dict)
    outbox: list[OutboxEntry] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    on_commit: Callable[[str, int], None] | None = None
    #: Monotonic milliseconds at the most recent commit, recorded before any
    #: projector is notified. A projector compares this against the moment it
    #: last caught up, which is how a projector that has stopped is told apart
    #: from a line on which nothing has happened.
    last_commit_ms: float = 0.0

    # ---------------------------------------------------------------- helpers

    def _require(self, dpp_id: str) -> dict[str, Any]:
        record = self._records.get(dpp_id)
        if record is None:
            raise DppError("S4C-STATE-NOT-FOUND", f"{dpp_id} does not exist")
        return record

    def idempotent(self, key: str | None, payload: Any) -> Any | None:
        """Return the stored response for ``key``, or None on first use.

        Reuse with an identical body repeats the original outcome. Reuse with a
        different body is a client defect and is refused.
        """
        if key is None:
            return None
        digest_value = canonical.canonicalise(payload)
        existing = self._idempotency.get(key)
        if existing is None:
            return None
        if existing.request_digest != digest_value:
            raise DppError(
                "S4C-STATE-IDEMPOTENCY-CONFLICT",
                "idempotency key reused with a different request body",
            )
        return existing.response

    def remember(self, key: str | None, payload: Any, response: Any) -> None:
        if key is None:
            return
        self._idempotency[key] = _IdempotencyRecord(
            request_digest=canonical.canonicalise(payload),
            response=copy.deepcopy(response),
            created_at=utcnow(),
        )

    # ----------------------------------------------------------------- writes

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = copy.deepcopy(payload)
            record.setdefault("dppId", new_urn("dpp"))
            record.setdefault("schemaVersion", SCHEMA_VERSION)
            record.setdefault("status", "active")
            record.setdefault("accessPolicyVersion", ACCESS_POLICY_VERSION)
            record.setdefault("carriers", [])
            record.setdefault("lifecycleEvents", [])
            record.setdefault("sortingDecisions", [])
            record.setdefault("integrity", [])
            now = utcnow()
            record["recordVersion"] = 1
            record["createdAt"] = record.get("createdAt", now)
            record["updatedAt"] = now

            if record["dppId"] in self._records:
                raise DppError("S4C-IDENT-DUPLICATE-BINDING", f"{record['dppId']} already exists")

            validate_payload(record)
            self._commit(record)
            return copy.deepcopy(record)

    def patch(self, dpp_id: str, patch: dict[str, Any], if_match: str | None) -> dict[str, Any]:
        with self._lock:
            record = self._require(dpp_id)
            self._check_precondition(record, if_match)
            updated = copy.deepcopy(record)
            for key, value in patch.items():
                if value is None:
                    updated.pop(key, None)
                elif isinstance(value, dict) and isinstance(updated.get(key), dict):
                    updated[key] = {**updated[key], **value}
                else:
                    updated[key] = value
            self._guard_append_only(record, updated)
            updated["recordVersion"] = record["recordVersion"] + 1
            updated["updatedAt"] = utcnow()
            validate_payload(updated)
            self._commit(updated)
            return copy.deepcopy(updated)

    def append(self, dpp_id: str, collection: str, entry: dict[str, Any], id_field: str) -> dict[str, Any]:
        """Append to an append-only collection, idempotently by ``id_field``."""
        with self._lock:
            record = self._require(dpp_id)
            existing = record.get(collection, [])
            for item in existing:
                if item.get(id_field) == entry.get(id_field):
                    # A repeated submission of the same entry returns the
                    # original outcome; it does not create a second event or a
                    # second business decision.
                    return copy.deepcopy(record)
            updated = copy.deepcopy(record)
            updated.setdefault(collection, []).append(copy.deepcopy(entry))
            updated["recordVersion"] = record["recordVersion"] + 1
            updated["updatedAt"] = utcnow()
            validate_payload(updated)
            self._commit(updated)
            return copy.deepcopy(updated)

    def commission_carrier(self, dpp_id: str, carrier: dict[str, Any]) -> dict[str, Any]:
        """Bind a carrier atomically.

        Either the binding, the encoded value and the status are all created, or
        nothing is. A failed attempt never leaves two commissioned bindings, and
        a previously used identifier is never reassigned to another product.
        """
        with self._lock:
            record = self._require(dpp_id)
            encoded = carrier["encodedIdentifier"]

            owner = self._carrier_index.get(encoded)
            if owner is not None and owner != dpp_id:
                raise DppError(
                    "S4C-IDENT-DUPLICATE-BINDING",
                    f"{encoded} is already bound to {owner}",
                )
            retired_owner = self._retired_carriers.get(encoded)
            if retired_owner is not None and retired_owner != dpp_id:
                raise DppError(
                    "S4C-IDENT-DUPLICATE-BINDING",
                    f"{encoded} was previously bound to {retired_owner} and is not reusable",
                )

            updated = copy.deepcopy(record)
            for existing in updated.get("carriers", []):
                if existing.get("bindingStatus") == "commissioned":
                    existing["bindingStatus"] = "replaced"
                    existing["closedAt"] = utcnow()
                    self._carrier_index.pop(existing["encodedIdentifier"], None)
                    self._retired_carriers[existing["encodedIdentifier"]] = dpp_id

            entry = {
                "carrierId": carrier.get("carrierId", new_urn("carrier")),
                "carrierType": carrier["carrierType"],
                "encodingScheme": carrier["encodingScheme"],
                "encodedIdentifier": encoded,
                "bindingStatus": "commissioned",
                "boundAt": carrier.get("boundAt", utcnow()),
                "boundBy": carrier["boundBy"],
            }
            for optional in ("resolverUri", "placement"):
                if optional in carrier:
                    entry[optional] = carrier[optional]

            updated.setdefault("carriers", []).append(entry)
            updated.setdefault("identity", {})["epc"] = encoded
            updated["recordVersion"] = record["recordVersion"] + 1
            updated["updatedAt"] = utcnow()

            validate_payload(updated)
            self._commit(updated)
            self._carrier_index[encoded] = dpp_id
            return copy.deepcopy(updated)

    # ------------------------------------------------------------------ reads

    def get(self, dpp_id: str) -> dict[str, Any]:
        record = self._require(dpp_id)
        if record["status"] == "retired":
            raise DppError(
                "S4C-IDENT-RETIRED",
                f"{dpp_id} is retired",
                extra={"supersededBy": record.get("supersededBy")},
            )
        return copy.deepcopy(record)

    def get_version(self, dpp_id: str, version: int) -> dict[str, Any]:
        for candidate in self._history.get(dpp_id, []):
            if candidate["recordVersion"] == version:
                return copy.deepcopy(candidate)
        raise DppError(
            "S4C-STATE-NOT-FOUND",
            f"version {version} of {dpp_id} is not retrievable",
        )

    def resolve_carrier(self, encoded: str) -> dict[str, Any]:
        dpp_id = self._carrier_index.get(encoded)
        if dpp_id is None:
            retired = self._retired_carriers.get(encoded)
            if retired is not None:
                record = self._records[retired]
                raise DppError(
                    "S4C-IDENT-RETIRED",
                    f"{encoded} is bound to a closed carrier binding",
                    extra={"supersededBy": record.get("supersededBy"), "dppId": retired},
                )
            raise DppError("S4C-IDENT-UNKNOWN", f"{encoded} resolves to no passport")
        return self.get(dpp_id)

    def history(self, dpp_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(v) for v in self._history.get(dpp_id, [])]

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(copy.deepcopy(list(self._records.values())))

    def __len__(self) -> int:
        return len(self._records)

    # ------------------------------------------------------------- invariants

    @staticmethod
    def _check_precondition(record: dict[str, Any], if_match: str | None) -> None:
        if if_match is None:
            raise DppError("S4C-STATE-VERSION-CONFLICT", "If-Match is required for an update")
        expected = etag(record)
        if if_match.strip('"') not in (expected.strip('"'), "*"):
            raise DppError(
                "S4C-STATE-VERSION-CONFLICT",
                f"If-Match {if_match} does not match current version {record['recordVersion']}",
            )

    @staticmethod
    def _guard_append_only(before: dict[str, Any], after: dict[str, Any]) -> None:
        for collection in ("materialObservations", "lifecycleEvents", "sortingDecisions", "integrity"):
            old = before.get(collection, [])
            new = after.get(collection, [])
            if len(new) < len(old):
                raise DppError(
                    "S4C-STATE-APPEND-ONLY-VIOLATION",
                    f"{collection} is append only; the update would remove {len(old) - len(new)} entries",
                    fields=[collection],
                )
            if new[: len(old)] != old:
                raise DppError(
                    "S4C-STATE-APPEND-ONLY-VIOLATION",
                    f"{collection} is append only; existing entries cannot be modified",
                    fields=[collection],
                )

    def _commit(self, record: dict[str, Any]) -> None:
        """Commit the record and its outbox entry as one logical operation."""
        entry = OutboxEntry(
            evidence_id=new_urn("evidence"),
            dpp_id=record["dppId"],
            subject_version=record["recordVersion"],
            digest_value=canonical.digest(record),
            canonicalisation=canonical.CANONICALISATION_PROFILE,
            digest_algorithm=canonical.DIGEST_ALGORITHM,
            created_at=utcnow(),
        )
        # Both mutations happen under one lock and neither can fail after the
        # other has succeeded, which is the property the transactional outbox
        # exists to provide.
        self._records[record["dppId"]] = record
        self._history.setdefault(record["dppId"], []).append(copy.deepcopy(record))
        entry.state = "queued"
        self.outbox.append(entry)
        self.last_commit_ms = time.monotonic() * 1000.0
        if self.on_commit is not None:
            self.on_commit(record["dppId"], record["recordVersion"])


def etag(record: dict[str, Any]) -> str:
    """Return the entity tag carrying the record version."""
    short = record["dppId"].rsplit(":", 1)[-1]
    return f'"dpp-{short}-v{record["recordVersion"]}"'
