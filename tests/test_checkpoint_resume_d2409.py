"""test_checkpoint_resume_d2409.py — D2409 checkpoint/resume regression tests.

Covers the T1.1 "checkpoints in each stage + pause/resumable" hardening:
  * S1.5  incremental embedding cache (fingerprint, atomic .npy, resume skip)
  * S5    intra-stage incremental checkpoint + resume skip of verified FBs

Model-free (no Ollama / no DeBERTa) — these verify the *resume decision logic*
and the crash-safe persistence primitives, not inference quality.
"""
from __future__ import annotations

import json

import numpy as np


def _valid_fb(fb_id: str, name: str = "Test Principle") -> dict:
    """Build a structurally-complete FB that passes the S5 quality pre-filters."""
    return {
        "name": name,
        "fb_id": fb_id,
        "definition": "A test definition describing a causal principle.",
        "mechanism": "x" * 200,  # passes mechanism-quality length/tautology checks
        "boundary": "Test boundary.",
        "consequence": "Test consequence.",
        "application": "A test application that is long enough to avoid enrichment noise.",
        "failure_mode": "A test failure mode that is long enough to avoid enrichment noise.",
        "source_books": ["book_a", "book_b"],
        "evidence": "cited",
        "classification_status": "OK",
        "domains": ["emerging"],
        "discipline": "emerging",
        "depth": "domain",
        "content_type": "principle",
        "extraction_type": "",
        "prerequisite_fbs": [],
        "source_principle_ids": [fb_id],
    }


# ── S1.5: embedding cache primitives (D2409) ────────────────────────────────

def test_segments_fingerprint_stable_and_drift_detecting():
    from pipeline.stage1_5_embed_cluster import _segments_fingerprint

    segs = [
        {"segment_id": "a1", "text": "hello world"},
        {"segment_id": "b2", "text": "another segment"},
    ]
    assert _segments_fingerprint(segs) == _segments_fingerprint(segs)
    # Text change → drift detected even with same segment_id
    drifted = [{"segment_id": "a1", "text": "DIFFERENT TEXT"}, segs[1]]
    assert _segments_fingerprint(drifted) != _segments_fingerprint(segs)
    # Count change → drift detected
    assert _segments_fingerprint(segs + segs) != _segments_fingerprint(segs)


def test_atomic_npy_write_roundtrip(tmp_path):
    from pipeline.stage1_5_embed_cluster import _atomic_npy_write

    arr = np.arange(12, dtype=np.float32).reshape(3, 4)
    path = tmp_path / "batch_0.npy"
    _atomic_npy_write(path, arr)
    assert np.array_equal(np.load(path), arr)


def test_write_embed_state_roundtrip(tmp_path, monkeypatch):
    from pipeline.stage1_5_embed_cluster import _embed_state_path, _write_embed_state

    monkeypatch.setattr(
        "pipeline.stage1_5_embed_cluster._embed_state_path", lambda: tmp_path / "state.json"
    )
    _write_embed_state("fp123", 100, 512, {0, 64, 128})
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["fingerprint"] == "fp123"
    assert state["total"] == 100
    assert state["dim"] == 512
    assert state["done_batches"] == [0, 64, 128]


def test_s15_embedding_resume_reebeds_missing_cache_file(monkeypatch, tmp_path):
    """A manifest "done" batch whose .npy is missing must be re-embedded, not dropped."""
    from pipeline import stage1_5_embed_cluster as s15

    cache_dir = tmp_path / "embeddings_cache"
    monkeypatch.setattr(s15, "_embed_cache_dir", lambda: cache_dir)
    monkeypatch.setattr(s15, "S15_EMBED_BACKEND", "ollama")
    monkeypatch.setattr(s15, "S15_EMBED_CHECKPOINT_ENABLED", True)
    monkeypatch.setattr(s15, "S15_EMBED_DIM", 8)
    monkeypatch.setattr(s15, "BATCH_SIZE", 2)

    segments = [{"segment_id": f"s{i}", "text": f"segment text {i}"} for i in range(4)]

    # Manifest claims batch 0 is done, but the .npy file is absent.
    cache_dir.mkdir(parents=True, exist_ok=True)
    s15._write_embed_state(s15._segments_fingerprint(segments), 4, 8, {0})

    calls: list[list[str]] = []

    def fake_batch_embed(texts, model=None):
        calls.append(list(texts))
        return [[0.1] * 8 for _ in texts]

    monkeypatch.setattr(s15, "batch_embed", fake_batch_embed)

    out_segments, embeddings = s15.embed_segments(segments, model="bge-m3")

    embedded_texts = [t for batch in calls for t in batch]
    assert "segment text 0" in embedded_texts  # missing cache → re-embedded
    assert "segment text 1" in embedded_texts
    assert embeddings.shape == (4, 8)
    assert len(out_segments) == 4


def test_s15_embedding_resume_skips_cached_batches(monkeypatch, tmp_path):
    """A mid-embedding crash must not re-embed already-completed batches.

    Pre-populates the cache for batch 0, then asserts the embedder is only asked
    for the remaining batches (batch_embed must never see cached segments).
    """
    from pipeline import stage1_5_embed_cluster as s15

    cache_dir = tmp_path / "embeddings_cache"
    monkeypatch.setattr(s15, "_embed_cache_dir", lambda: cache_dir)
    monkeypatch.setattr(s15, "S15_EMBED_BACKEND", "ollama")
    monkeypatch.setattr(s15, "S15_EMBED_CHECKPOINT_ENABLED", True)
    monkeypatch.setattr(s15, "S15_EMBED_DIM", 8)
    monkeypatch.setattr(s15, "BATCH_SIZE", 2)

    segments = [{"segment_id": f"s{i}", "text": f"segment text {i}"} for i in range(6)]

    # Pre-populate cache: batch 0 (segments 0,1) already embedded.
    cache_dir.mkdir(parents=True, exist_ok=True)
    s15._atomic_npy_write(cache_dir / "batch_0.npy", np.full((2, 8), 0.5, dtype=np.float32))
    s15._write_embed_state(s15._segments_fingerprint(segments), 6, 8, {0})

    calls: list[list[str]] = []

    def fake_batch_embed(texts, model=None):
        calls.append(list(texts))
        return [[0.1] * 8 for _ in texts]

    monkeypatch.setattr(s15, "batch_embed", fake_batch_embed)

    out_segments, embeddings = s15.embed_segments(segments, model="bge-m3")

    embedded_texts = [t for batch in calls for t in batch]
    assert "segment text 0" not in embedded_texts  # cached → skipped
    assert "segment text 1" not in embedded_texts  # cached → skipped
    assert "segment text 2" in embedded_texts
    assert "segment text 5" in embedded_texts
    assert embeddings.shape == (6, 8)
    assert len(out_segments) == 6  # no drops → segments unchanged (D2346 alignment)


# ── S5: intra-stage checkpoint + resume skip (D2409) ────────────────────────

def test_s5_resume_skips_verified_fbs(monkeypatch, tmp_path):
    """S5 must skip already-verified FBs on resume, re-verifying only the rest."""
    from pipeline import stage5_verify as s5

    ckpt = tmp_path / "verified.jsonl"
    monkeypatch.setattr(s5, "STAGE5_CHECKPOINT", ckpt)

    fbs = [_valid_fb(f"fb_{i}") for i in range(5)]

    # Simulate a prior partial run that verified fb_0 (PASS) and fb_1 (QUARANTINE).
    prior = [
        {**_valid_fb("fb_0"), "status": "PASS", "verification_results": [],
         "confidence_score": 0.9, "verifier_model": "test", "verification_method": "deberta-nli",
         "epistemic_status": "source-supported", "isor": {"score": 0.5, "rating": "medium"},
         "needs_human_review": False, "pipeline_commit": "test"},
        {**_valid_fb("fb_1"), "status": "QUARANTINE", "verification_results": [],
         "confidence_score": 0.1, "verifier_model": "test", "verification_method": "mech_quality",
         "epistemic_status": "speculative", "isor": {"score": 0.5, "rating": "medium"},
         "needs_human_review": False, "pipeline_commit": "test"},
    ]
    s5._write_s5_checkpoint(prior)

    monkeypatch.setattr(s5, "load_stage4_fbs", lambda: fbs)
    monkeypatch.setattr(s5, "_load_dual_encoders", lambda: (None, None))

    deberta_calls: list[str] = []

    def fake_deberta(fb):
        deberta_calls.append(fb["fb_id"])
        return (True, 0.9, "ok")

    monkeypatch.setattr(s5, "deberta_check", fake_deberta)
    monkeypatch.setattr(s5, "check_mechanism_quality", lambda fb: (True, 1.0, "ok"))
    monkeypatch.setattr(s5, "_check_enrichment_quality", lambda fb: (True, 1.0, "ok"))

    import pipeline.schema_accessor as schema_accessor
    monkeypatch.setattr(schema_accessor, "isor_score", lambda fb: {"score": 0.5, "rating": "medium"})

    verified = s5.run_stage5()

    # DeBERTa ran only for the not-yet-verified FBs.
    assert set(deberta_calls) == {"fb_2", "fb_3", "fb_4"}
    # Final checkpoint has all 5 (2 resumed + 3 newly verified).
    assert len(verified) == 5
    assert {v["fb_id"] for v in verified} == {f"fb_{i}" for i in range(5)}
    # The resumed statuses are preserved (not re-verified).
    by_id = {v["fb_id"]: v for v in verified}
    assert by_id["fb_0"]["status"] == "PASS"
    assert by_id["fb_1"]["status"] == "QUARANTINE"
