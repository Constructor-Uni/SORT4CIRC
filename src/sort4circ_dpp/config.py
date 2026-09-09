"""Layout, and the versions of the normative profile artefacts this code implements.

The versions below are the **SORT4CIRC DPP implementation profile** versions of the
schema, ontology and access matrix. They are deliberately separate from the version of
this repository and Python package (see ``sort4circ_dpp.__version__``): the software and
its documentation evolve without redefining the normative profile.
"""
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
SPEC_DIR = Path(os.environ.get("DPP_SPEC_DIR", PACKAGE_DIR / "spec" if (PACKAGE_DIR / "spec").exists() else REPO_ROOT / "spec"))
SCHEMA_DIR = SPEC_DIR / "schemas"
VOCAB_DIR = SPEC_DIR / "vocabularies"
ONTOLOGY_DIR = SPEC_DIR / "ontology"

#: Version of this repository, package and GitHub release.
RELEASE_VERSION = "1.2.0"

#: Versions of the normative profile artefacts, not of this package.
PROFILE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
ONTOLOGY_VERSION = "1.0.0"
ACCESS_POLICY_VERSION = "1.0.0"
API_MAJOR = "v1"

#: Duplicate-read suppression window applied at the edge gateway, in milliseconds.
#: A deployment substitutes the measured parameters of its own installation.
READ_SUPPRESSION_WINDOW_MS = int(os.environ.get("DPP_READ_SUPPRESSION_MS", "60"))

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
