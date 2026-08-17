"""Runtime configuration and repository layout."""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]


def _child(root: Any, name: str) -> Any:
    return root / name if isinstance(root, Path) else root.joinpath(name)


_override = os.environ.get("S4C_SPEC_DIR")
if _override is not None:
    SPEC_DIR = Path(_override)
    if not _override or not SPEC_DIR.is_dir():
        raise FileNotFoundError(f"S4C_SPEC_DIR does not name a directory: {SPEC_DIR}")
elif (REPO_ROOT / "spec").is_dir():
    SPEC_DIR = REPO_ROOT / "spec"
else:
    SPEC_DIR = files("sort4circ_dpp").joinpath("_spec")

SCHEMA_DIR = _child(SPEC_DIR, "schemas")
VOCAB_DIR = _child(SPEC_DIR, "vocabularies")
ONTOLOGY_DIR = _child(SPEC_DIR, "ontology")

SCHEMA_VERSION = "1.0.0"
ONTOLOGY_VERSION = "1.0.1"
ACCESS_POLICY_VERSION = "1.0.0"
API_MAJOR = "v1"
API_CONTRACT_VERSION = "1.1.0"

#: Ledger network identifier reported in evidence records.
LEDGER_NETWORK_ID = os.environ.get("S4C_LEDGER_NETWORK", "s4c-reference")

#: Window during which an idempotency key is honoured, in seconds.
IDEMPOTENCY_WINDOW_SECONDS = int(os.environ.get("S4C_IDEMPOTENCY_WINDOW", "86400"))

#: Duplicate-read suppression window applied at the edge gateway, in milliseconds.
#: Derived from the reference line configuration in D4.3.
READ_SUPPRESSION_WINDOW_MS = int(os.environ.get("S4C_READ_SUPPRESSION_MS", "60"))

#: Software budget for the time-critical path, in milliseconds. Derived in D4.3
#: from a 1.5 m/s conveyor and a 2.40 m read-to-actuator distance. An implementer
#: substitutes the measured parameters of the installed line.
SOFTWARE_BUDGET_MS = int(os.environ.get("S4C_SOFTWARE_BUDGET_MS", "920"))

#: Target percentiles for the server-side resolve path, in milliseconds.
LOOKUP_TARGETS_MS = {"p50": 25, "p95": 80, "p99": 150, "max": 300}

#: Maximum age of the read-index projection that may serve a sorting decision
#: without revalidation, in milliseconds.
INDEX_STALENESS_LIMIT_MS = int(os.environ.get("S4C_INDEX_STALENESS_MS", "30000"))

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
