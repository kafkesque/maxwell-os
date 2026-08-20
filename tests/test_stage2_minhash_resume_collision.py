"""CI test: MinHash LSH signature collision on resume (BUG-154).

The D2382 resume rebuild inserts the checkpoint FBs' stored `minhash_signature`
keys ("mh_0"…"mh_N") into a fresh LSH. When those keys have a GAP (a near-dup/
other FB consumed a slot without persisting), the old counter scheme
`f"mh_{len(minhash_cache)}"` collided with an already-occupied index → datasketch
raised "The given key already exists" for every FB-producing cluster (run-killer).

`is_near_duplicate` must find the next FREE index, never reuse an occupied key.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage2_extract import is_near_duplicate, make_minhash


def _fresh_lsh():
    from datasketch import MinHashLSH
    return MinHashLSH(threshold=0.9, num_perm=128)


def test_gapped_cache_assigns_collision_free_sig() -> None:
    """A gapped cache (missing mh_2) must NOT collide — the new sig is a free slot."""
    lsh = _fresh_lsh()
    cache: dict = {}
    # Insert keys with a gap at mh_2 (simulating a consumed-but-unpersisted slot).
    for key in ("mh_0", "mh_1", "mh_3"):
        mh = make_minhash(f"unrelated sentence one {key}")
        lsh.insert(key, mh)
        cache[key] = (f"x {key}", mh)
    pre_existing = set(cache)

    _, sig = is_near_duplicate("a wholly distinct new phrase", lsh, cache)
    assert sig is not None
    # is_near_duplicate mutates cache (adds the new sig); the important invariant is
    # that the assigned sig was NOT one of the pre-existing keys (which would have
    # made lsh.insert raise "The given key already exists").
    assert sig not in pre_existing, f"collision: {sig} was an occupied key"


def test_no_lsh_insert_collision_after_resume_gap() -> None:
    """Simulate the real t11 resume gap (max index 2642, 2641 keys): the counter
    lands on an occupied index, and the fix must skip to a free one without
    raising 'The given key already exists'."""
    lsh = _fresh_lsh()
    cache: dict = {}
    keys = [f"mh_{i}" for i in range(6)] + ["mh_7"]  # gap at mh_6
    for key in keys:
        mh = make_minhash(f"resume rebuild text for slot {key}")
        lsh.insert(key, mh)
        cache[key] = (f"y {key}", mh)
    pre_existing = set(cache)

    # len(cache)=7 → the old scheme computed "mh_7" (occupied). The fix must avoid it.
    _, sig = is_near_duplicate("a brand new totally different passage", lsh, cache)
    assert sig is not None
    assert sig not in pre_existing, f"collision: {sig} was an occupied key"


if __name__ == "__main__":
    test_gapped_cache_assigns_collision_free_sig()
    test_no_lsh_insert_collision_after_resume_gap()
    print("BUG-154 minhash collision tests OK")
