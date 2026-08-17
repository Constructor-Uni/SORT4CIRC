"""SORT4CIRC Textile Digital Product Passport reference software.

This package provides reference software supporting the sanitised implementation
profile described in SORT4CIRC deliverable D4.3, "DPP Development Guidelines"
(WP4, Task 4.2, Constructor University). It is intended to be read and reused,
not a product.

The specification artefacts in ``spec/`` are normative. Where this code and the
specification disagree, the specification governs and the disagreement is a bug
in this package.
"""

from .canonical import canonicalise, digest, integrity_projection  # noqa: F401
from .config import API_MAJOR, SCHEMA_VERSION  # noqa: F401

__version__ = "1.2.0"
__all__ = ["canonicalise", "digest", "integrity_projection", "SCHEMA_VERSION", "API_MAJOR"]
