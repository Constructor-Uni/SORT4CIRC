"""Generic DPP educational implementation associated with SORT4CIRC.

Normative requirements apply only to this repository's public profile.
"""
from .canonical import canonicalise, digest, integrity_projection
from .config import API_MAJOR, SCHEMA_VERSION

__version__ = "2.0.0"
__all__ = ["canonicalise", "digest", "integrity_projection", "SCHEMA_VERSION", "API_MAJOR"]
