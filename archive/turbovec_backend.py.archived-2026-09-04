"""
turbovec_backend.py — TurboVec quantized vector storage backend (P1.2).
=======================================================================
Authority: D2120 Phase 1.2 | CONSTITUTION.md C21 (swappable infrastructure)

Provides a drop-in vector storage backend using TurboVec's TurboQuantIndex
with 4-bit quantization. Replaces sqlite-vec for persistent FB embeddings
with ~4-8x lower memory footprint and Metal SIMD acceleration on Apple Silicon.

Use this when:
  - You have 500+ FBs and want fast semantic search
  - Memory is constrained (4-bit quantized = 4-8x smaller than float32)
  - You want Metal SIMD acceleration on Apple Silicon (C24: hardware-adaptive)

Usage:
    from pipeline.storage.turbovec_backend import TurboVecStore

    store = TurboVecStore(dim=1024)
    store.add_batch(fb_ids, embeddings)
    store.save("knowledge pipeline/fb_vectors.turbovec")

    results = store.search(query_embedding, k=10)

Architecture:
    This implements the swappable StorageBackend protocol (D2056).
    Swap between TurbovecStore and SQLiteVecStore via config:
        vector_backend: turbovec  # or sqlite_vec
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import turbovec


class TurboVecStore:
    """Quantized vector storage backend using TurboVec TurboQuantIndex.

    Vectors are stored with 4-bit quantization by default (configurable
    to 2, 4, or 8 bits). The index supports add, search, remove, and
    persistent save/load.

    Attributes:
        dim: Vector dimensionality.
        bit_width: Quantization bit width (2, 4, or 8).
        _index: The underlying TurboQuantIndex.
        _id_to_pos: Maps FB IDs to index positions.
        _pos_to_id: Maps index positions to FB IDs.
    """

    def __init__(
        self,
        dim: int = 1024,
        bit_width: int = 4,
    ) -> None:
        """Initialize the TurboVec store.

        Args:
            dim: Vector dimensionality (default 1024 for bge-m3).
            bit_width: Quantization width — 2, 4, or 8 bits.
                Lower = smaller memory, slightly reduced precision.
                4-bit is the recommended default (8x smaller than float32).
        """
        if bit_width not in (2, 4, 8):
            raise ValueError(f"bit_width must be 2, 4, or 8, got {bit_width}")

        self.dim: int = dim
        self.bit_width: int = bit_width
        self._index: turbovec.TurboQuantIndex = turbovec.TurboQuantIndex(
            dim=dim, bit_width=bit_width
        )
        self._id_to_pos: dict[str, int] = {}
        self._pos_to_id: dict[int, str] = {}
        self._count: int = 0

    # ── CRUD ──────────────────────────────────────────────────────────

    def add(self, fb_id: str, vector: np.ndarray) -> None:
        """Add a single vector to the index.

        Args:
            fb_id: Foundation Block ID (maps to index position).
            vector: Float32 numpy array of shape (dim,). Must match self.dim.
        """
        vector = np.asarray(vector, dtype=np.float32)
        if vector.shape != (self.dim,):
            raise ValueError(
                f"Vector shape {vector.shape} != ({self.dim},)"
            )

        self._index.add(vector.reshape(1, self.dim))
        pos = self._count
        self._id_to_pos[fb_id] = pos
        self._pos_to_id[pos] = fb_id
        self._count += 1

    def add_batch(
        self,
        fb_ids: list[str],
        vectors: np.ndarray,
    ) -> None:
        """Add multiple vectors in batch (more efficient than individual adds).

        Args:
            fb_ids: List of FB IDs, one per vector.
            vectors: Float32 array of shape (n, dim).
        """
        vectors = np.asarray(vectors, dtype=np.float32)
        n, dim = vectors.shape
        if dim != self.dim:
            raise ValueError(f"Vector dim {dim} != {self.dim}")
        if len(fb_ids) != n:
            raise ValueError(f"Got {len(fb_ids)} IDs for {n} vectors")

        self._index.add(vectors)
        for i, fb_id in enumerate(fb_ids):
            pos = self._count + i
            self._id_to_pos[fb_id] = pos
            self._pos_to_id[pos] = fb_id
        self._count += n

    def search(
        self,
        query: np.ndarray,
        k: int = 10,
        *,
        mask: np.ndarray | None = None,
    ) -> list[tuple[str, float]]:
        """Search for k nearest neighbors.

        Args:
            query: Float32 array of shape (dim,) or (1, dim).
            k: Number of results to return.
            mask: Optional boolean mask of active indices.

        Returns:
            List of (fb_id, similarity_score) tuples, sorted by descending similarity.
        """
        query = np.asarray(query, dtype=np.float32).reshape(1, self.dim)
        results = self._index.search(query, k=k, mask=mask)

        # TurboVec returns (distances, indices) — each shape (1, k)
        # indices[0] are the k nearest positions, distances[0] are the scores
        if isinstance(results, tuple) and len(results) == 2:
            distances_arr, indices_arr = results
            indices = indices_arr.flatten()
            distances = distances_arr.flatten()
        elif hasattr(results, "indices"):
            indices = results.indices.flatten()
            distances = (
                results.distances.flatten()
                if hasattr(results, "distances")
                else np.ones(k)
            )
        else:
            indices = np.asarray(results).flatten()
            distances = np.ones(len(indices))

        output: list[tuple[str, float]] = []
        for idx, dist in zip(indices, distances, strict=False):
            idx_i = int(idx)
            if idx_i in self._pos_to_id:
                # Convert distance to similarity score
                # For cosine distance: sim = 1 - distance
                sim = float(1.0 - float(dist))
                output.append((self._pos_to_id[idx_i], sim))

        return output

    def remove(self, fb_id: str) -> bool:
        """Remove a vector by FB ID (O(1) via swap_remove).

        Args:
            fb_id: FB ID to remove.

        Returns:
            True if removed, False if not found.
        """
        if fb_id not in self._id_to_pos:
            return False

        pos = self._id_to_pos[fb_id]
        self._index.swap_remove(pos)
        self._count -= 1

        # Update position mappings
        del self._id_to_pos[fb_id]
        del self._pos_to_id[pos]

        # If the swapped-in element was at the end, update its position
        if pos < self._count:
            moved_id = self._pos_to_id.pop(self._count, None)
            if moved_id:
                self._pos_to_id[pos] = moved_id
                self._id_to_pos[moved_id] = pos

        return True

    def prepare(self) -> None:
        """Warm up search caches (rotation matrix, centroids, SIMD layout).

        Call before first search to avoid one-time initialization cost.
        """
        self._index.prepare()

    # ── Persistence ───────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        """Persist the index and ID mappings to disk.

        Args:
            path: File path for the TurboVec index (.turbovec suffix recommended).
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save the vector index
        self._index.write(str(path))

        # Save ID mappings alongside
        meta_path = path.with_suffix(".meta.json")
        meta: dict[str, Any] = {
            "dim": self.dim,
            "bit_width": self.bit_width,
            "count": self._count,
            "id_to_pos": self._id_to_pos,
            "pos_to_id": {str(k): v for k, v in self._pos_to_id.items()},
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f)

    @classmethod
    def load(cls, path: str | Path) -> TurboVecStore:
        """Load a persisted TurboVec index.

        Args:
            path: Path to the saved .turbovec file.

        Returns:
            TurboVecStore with all vectors and ID mappings restored.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"No index at {path}")

        # Load metadata
        meta_path = path.with_suffix(".meta.json")
        with open(meta_path) as f:
            meta = json.load(f)

        store = cls(dim=meta["dim"], bit_width=meta["bit_width"])
        store._id_to_pos = meta["id_to_pos"]
        store._pos_to_id = {int(k): v for k, v in meta["pos_to_id"].items()}
        store._count = meta["count"]

        # Load the vector index
        store._index = turbovec.TurboQuantIndex.load(str(path))

        return store

    # ── Properties ────────────────────────────────────────────────────

    def __len__(self) -> int:
        return self._count

    @property
    def memory_estimate_mb(self) -> float:
        """Estimated memory usage in MB (vectors only, 4-bit quantized)."""
        bytes_per_vector = self.dim * self.bit_width / 8
        total_bytes = bytes_per_vector * self._count
        return total_bytes / (1024 * 1024)

    @property
    def fb_ids(self) -> list[str]:
        """All FB IDs in the index."""
        return list(self._id_to_pos.keys())
