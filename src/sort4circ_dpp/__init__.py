"""Reference implementation of the SORT4CIRC DPP implementation profile.

Two version numbers matter here and they are not the same thing:

``__version__``
    the version of this repository, package and GitHub release.
``sort4circ_dpp.config.PROFILE_VERSION``
    the version of the normative DPP implementation profile this code implements.
    Individual specification assets are versioned per asset; see ``config``.

Normative requirements apply only within that published profile. The specification
originates in SORT4CIRC deliverable D4.3, "DPP Development Guidelines".
"""

from .canonical import canonicalise, digest, integrity_projection
from .config import API_MAJOR, ONTOLOGY_VERSION, PROFILE_VERSION, RELEASE_VERSION, SCHEMA_VERSION

#: Repository / package / release version. Not the normative profile version.
__version__ = RELEASE_VERSION

__all__ = [
    "canonicalise",
    "digest",
    "integrity_projection",
    "PROFILE_VERSION",
    "SCHEMA_VERSION",
    "ONTOLOGY_VERSION",
    "API_MAJOR",
    "__version__",
]
