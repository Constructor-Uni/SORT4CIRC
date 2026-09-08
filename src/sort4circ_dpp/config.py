"""Layout and versions for the generic public profile."""
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
SPEC_DIR = Path(os.environ.get("DPP_SPEC_DIR", PACKAGE_DIR / "spec" if (PACKAGE_DIR / "spec").exists() else REPO_ROOT / "spec"))
SCHEMA_DIR = SPEC_DIR / "schemas"
VOCAB_DIR = SPEC_DIR / "vocabularies"
ONTOLOGY_DIR = SPEC_DIR / "ontology"
SCHEMA_VERSION = "2.0.0"
ONTOLOGY_VERSION = "2.0.0"
ACCESS_POLICY_VERSION = "2.0.0"
API_MAJOR = "v1"
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
