"""pipeline/storage/base.py — StorageBackend protocol.

Authority: CONSTITUTION.md C21, D2056.
Ratified: 2026-07-22.

Swap SQLite -> PostgreSQL -> LanceDB -> JSON files by changing ONE config line.

NOTE (D2552): no `sqlite_backend.py` concrete class exists — this Protocol has
no default implementation. SQLite storage is inlined in `retrieve.py` (FTS5),
`stage6_commit.py` (write), and `backfill_embeddings.py` (sqlite-vec), bypassing
the abstraction. Do not cite `sqlite_backend.py` as a live file; it is a future
refactor target (D2056).
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for knowledge base storage backends.

    Must support: CRUD for FBs, FTS5 full-text search, vector similarity search,
    schema migration, and Parquet export.
    """

    @abstractmethod
    def init_db(self, db_path: str) -> object:
        """Initialize storage. Returns connection/handle."""
        ...

    @abstractmethod
    def insert_fb(self, conn, fb: dict) -> str:
        """Insert or update a Foundation Block. Returns fb_id."""
        ...

    @abstractmethod
    def search_fts(self, conn, query: str, top_k: int = 10) -> list[dict]:
        """Full-text search via FTS5 or equivalent."""
        ...

    @abstractmethod
    def search_vector(self, conn, query_embedding: list[float], top_k: int = 10) -> list[dict]:
        """Vector similarity search."""
        ...

    @abstractmethod
    def export_parquet(self, conn, path: str) -> None:
        """Export all FBs to Parquet snapshot."""
        ...

    @abstractmethod
    def migrate_schema(self, conn, from_version: str, to_version: str) -> None:
        """Run versioned schema migrations."""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend identifier."""
        ...

