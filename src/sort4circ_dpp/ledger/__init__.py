"""Ledger adapters behind one contract.

Platform-specific addresses, transaction formats and signing procedures stay
inside an adapter. The receipt returned to the DPP service uses a common
structure, so a partner API does not change when the ledger profile changes.
"""

from .base import LedgerAdapter, Receipt  # noqa: F401
from .memory import InMemoryLedger  # noqa: F401

__all__ = ["LedgerAdapter", "Receipt", "InMemoryLedger"]
