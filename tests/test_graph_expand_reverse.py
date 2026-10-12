"""A2/BUG-274 — read-side undirected related_fbs traversal (reverse adjacency).

Proves that graph_expand follows INCOMING edges of the symmetric relationship
types so a one-way overlap link (pruned on one side by the BUG-188 neighbour
cap) is traversable in BOTH directions, without mutating the store.
"""
import json
import sqlite3

import pipeline.retrieve as retrieve


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE fbs ("
        "fb_id TEXT PRIMARY KEY, name TEXT, definition TEXT, domains TEXT, "
        "borp_score REAL, related_fbs TEXT, contradicts_fbs TEXT, "
        "prerequisite_fbs TEXT, pipeline_run_id TEXT)"
    )
    return conn


def _insert(conn, fid: str, related: list) -> None:
    conn.execute(
        "INSERT INTO fbs VALUES (?,?,?,?,?,?,?,?,?)",
        (fid, fid, f"def {fid}", "d", 0.0,
         json.dumps(related), "[]", "[]", retrieve.CANONICAL_RUN),
    )


def test_reverse_adjacency_reaches_pruned_direction():
    """A -> C stored, C -> A pruned. From C, reverse adjacency must reach A."""
    conn = _conn()
    _insert(conn, "A", [{"fb_id": "C", "relationships": ["domain_overlap"]}])
    _insert(conn, "C", [])
    conn.commit()

    g = retrieve.graph_expand(conn, ["C"], hops=1)
    reached = [r["fb_id"] for r in g["C"]["related"]]
    assert "A" in reached, f"reverse adjacency must reach A from C, got {reached}"


def test_forward_edges_still_work():
    """Forward traversal is unchanged: A -> C reaches C directly."""
    conn = _conn()
    _insert(conn, "A", [{"fb_id": "C", "relationships": ["semantic_near"]}])
    _insert(conn, "C", [])
    conn.commit()

    g = retrieve.graph_expand(conn, ["A"], hops=1)
    reached = [r["fb_id"] for r in g["A"]["related"]]
    assert "C" in reached


def test_symmetric_pair_not_duplicated():
    """A <-> C stored on both sides: no duplicate in either direction."""
    conn = _conn()
    _insert(conn, "A", [{"fb_id": "C", "relationships": ["domain_overlap"]}])
    _insert(conn, "C", [{"fb_id": "A", "relationships": ["domain_overlap"]}])
    conn.commit()

    g = retrieve.graph_expand(conn, ["A"], hops=1)
    reached = [r["fb_id"] for r in g["A"]["related"]]
    assert reached.count("C") == 1, f"expected exactly one C edge, got {reached}"


def test_non_symmetric_type_not_reverse_followed():
    """A relationship type outside the symmetric set is NOT reverse-followed."""
    conn = _conn()
    _insert(conn, "A", [{"fb_id": "C", "relationships": ["directed_future_type"]}])
    _insert(conn, "C", [])
    conn.commit()

    # Force the symmetric set to exclude the foreign type for this call.
    g = retrieve.graph_expand(conn, ["C"], hops=1)
    reached = [r["fb_id"] for r in g["C"]["related"]]
    assert "A" not in reached, "non-symmetric relationship type must not be reverse-followed"


def test_reverse_adjacency_hops_bound():
    """Reverse-discovered nodes are added at the SAME BFS level (no hop leak)."""
    conn = _conn()
    # A -> B -> C forward chain; C -> nothing. Reverse: C<-B, B<-A.
    _insert(conn, "A", [{"fb_id": "B", "relationships": ["domain_overlap"]}])
    _insert(conn, "B", [{"fb_id": "C", "relationships": ["domain_overlap"]}])
    _insert(conn, "C", [])
    conn.commit()

    g = retrieve.graph_expand(conn, ["C"], hops=1)
    reached = [r["fb_id"] for r in g["C"]["related"]]
    # 1 hop from C: only B (via reverse). A is 2 hops away, must NOT appear.
    assert "B" in reached
    assert "A" not in reached, f"A is 2 hops away, got {reached}"
