"""Layout, and the versions of the normative profile artefacts this code implements.

The versions below are the **SORT4CIRC DPP implementation profile** versions of the
schema, ontology, vocabularies and access matrix. They are deliberately separate from the
version of this repository and Python package (see ``sort4circ_dpp.__version__``): the
software and its documentation evolve without redefining the normative profile, and
individual specification assets may carry different versions from one another.
"""

from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]


def _child(root: Any, name: str) -> Any:
    return root / name if isinstance(root, Path) else root.joinpath(name)


#: ``DPP_SPEC_DIR`` is the current name; ``S4C_SPEC_DIR`` stays accepted because it was
#: published in an earlier release. A source checkout uses ``spec/``; an installed wheel
#: falls back to the specification resources packaged inside the distribution.
_override_name = next((n for n in ("DPP_SPEC_DIR", "S4C_SPEC_DIR") if n in os.environ), None)
_override = os.environ.get(_override_name) if _override_name else None
if _override_name is not None:
    # An override that does not resolve is an error, never a silent fallback: a service
    # must not quietly load a different specification than the one it was pointed at.
    SPEC_DIR = Path(_override or "")
    if not _override or not SPEC_DIR.is_dir():
        raise FileNotFoundError(f"{_override_name} does not name a directory: {SPEC_DIR}")
elif (REPO_ROOT / "spec").is_dir():
    SPEC_DIR = REPO_ROOT / "spec"
else:
    SPEC_DIR = files("sort4circ_dpp").joinpath("_spec")

SCHEMA_DIR = _child(SPEC_DIR, "schemas")
VOCAB_DIR = _child(SPEC_DIR, "vocabularies")
ONTOLOGY_DIR = _child(SPEC_DIR, "ontology")
MAPPING_DIR = _child(SPEC_DIR, "mappings")
QUERY_DIR = _child(SPEC_DIR, "queries")
GOVERNANCE_DIR = _child(SPEC_DIR, "governance")

#: Version of this repository, package and GitHub release.
RELEASE_VERSION = "1.3.0"

#: Versions of the normative profile artefacts, not of this package. These are versioned
#: per asset: the ontology carries an additive patch the other assets do not share.
PROFILE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
ONTOLOGY_VERSION = "1.0.1"
VOCABULARY_VERSION = "1.0.0"
ACCESS_POLICY_VERSION = "1.0.0"
MAPPING_VERSION = "1.0.0"
QUERY_PROFILE_VERSION = "1.0.0"

#: Version of the published OpenAPI exchange contract, versioned independently.
API_CONTRACT_VERSION = "1.1.0"
API_MAJOR = "v1"

#: Maximum age of the read-index projection, in milliseconds, that may still serve a
#: projected read. The limit catches a projector that has fallen behind its source; it is
#: measured against the source, not against wall-clock age, so an idle service does not
#: turn into an outage. A deployment substitutes its own figure.
INDEX_STALENESS_LIMIT_MS = int(os.environ.get("DPP_INDEX_STALENESS_MS", "30000"))

#: Duplicate-read suppression window applied at the edge gateway, in milliseconds.
#: A deployment substitutes the measured parameters of its own installation.
READ_SUPPRESSION_WINDOW_MS = int(os.environ.get("DPP_READ_SUPPRESSION_MS", "60"))

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
