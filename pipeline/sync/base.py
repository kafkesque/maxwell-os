"""pipeline/sync/base.py — SyncProvider protocol (STUB).

Authority: CONSTITUTION.md C21, D2063.
Ratified: 2026-07-22.

Multi-machine knowledge base synchronization. Not yet implemented — protocol stub
defined now to prevent future lock-in. Full implementation: Phase 3.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class SyncProvider(Protocol):
    """Protocol for cross-machine KB synchronization.

    NOT YET IMPLEMENTED. Protocol defined for future use (C27: Zero Future Tax).
    """

    @abstractmethod
    def sync_push(self, source_path: str, remote_id: str) -> bool:
        """Push local KB to remote."""
        ...

    @abstractmethod
    def sync_pull(self, remote_id: str, target_path: str) -> bool:
        """Pull remote KB to local."""
        ...

    @abstractmethod
    def resolve_conflicts(self, local_path: str, remote_id: str) -> list[str]:
        """Detect and report conflicts. Returns list of conflicting FB IDs."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable sync provider identifier."""
        ...

