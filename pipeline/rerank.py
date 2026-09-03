#!/usr/bin/env python3
"""
pipeline/rerank.py — Cross-encoder rerank (S2, D2511).
=======================================================
Authority: CONSTITUTION §2.3 (retrieval), D2205 (RAG roadmap), D2511 (S2 gate).

S2 is a cross-encoder rerank over the hybrid (RRF) candidate pool: for each
(query, definition) pair the cross-encoder emits a single relevance logit —
strictly more expressive than the dual-encoder cosine used by vec_fbs — so it
re-orders the top-k candidates and recovers synonyms/paraphrases the vector leg
misses.

Model: BAAI/bge-reranker-v2-m3 (already cached + verified working at D2511;
newer and stronger than bge-reranker-large). Gated OFF by default (C5/C28:
bloat is opt-in) until retrieval_benchmark --rerank shows it beats hybrid.

C16: no silent errors — a rerank failure RAISES so the caller degrades loudly,
never returns an unfused list that looks ranked.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
with open(_PROJECT_ROOT / "config" / "pipeline_config.yaml") as _f:
    _CFG = yaml.safe_load(_f) or {}
_RERANK = _CFG.get("rerank", {})

RERANK_MODEL: str = _RERANK.get("model", "BAAI/bge-reranker-v2-m3")
RERANK_DEVICE: str = _RERANK.get("device", "cpu")
RERANK_MAX_LENGTH: int = int(_RERANK.get("max_length", 512))
RERANK_BATCH_SIZE: int = int(_RERANK.get("batch_size", 8))

_model: Any = None
_tokenizer: Any = None


def _load() -> tuple[Any, Any]:
    """Load the cross-encoder once (lazy, cached). Raises if unavailable."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as e:  # C16: loud
        raise RuntimeError(
            f"rerank: transformers not installed ({e}); rerank is opt-in (C28)"
        ) from e
    import torch  # noqa: F401  (torch import validates the runtime)

    _tokenizer = AutoTokenizer.from_pretrained(RERANK_MODEL)
    _model = AutoModelForSequenceClassification.from_pretrained(RERANK_MODEL)
    _model.eval()
    if RERANK_DEVICE == "mps" and torch.backends.mps.is_available():
        _model = _model.to("mps")
    return _model, _tokenizer


def rerank_candidates(
    query: str,
    candidates: list[dict],
    top_k: int = 10,
    definition_field: str = "definition",
) -> list[dict]:
    """Re-rank candidates by cross-encoder relevance to the query.

    Args:
        query: natural-language query.
        candidates: list of FB dicts (must carry `definition_field`).
        top_k: number of re-ranked results to return.
        definition_field: dict key holding the FB definition text.

    Returns:
        candidates re-ordered by descending relevance score, each with an
        added `_rerank_score` float field. Length == min(top_k, len(candidates)).
    """
    if not candidates:
        return []

    model, tokenizer = _load()
    import torch

    pairs: list[tuple[str, str]] = [
        (query, c.get(definition_field) or "") for c in candidates
    ]

    scores: list[float] = []
    with torch.no_grad():
        for i in range(0, len(pairs), RERANK_BATCH_SIZE):
            batch = pairs[i : i + RERANK_BATCH_SIZE]
            inputs = tokenizer(
                batch, padding=True, truncation=True,
                return_tensors="pt", max_length=RERANK_MAX_LENGTH,
            )
            if RERANK_DEVICE == "mps" and torch.backends.mps.is_available():
                inputs = {k: v.to("mps") for k, v in inputs.items()}
            logits = model(**inputs, return_dict=True).logits.view(-1,).float()
            scores.extend(logits.tolist())

    ranked = sorted(zip(candidates, scores), key=lambda t: t[1], reverse=True)
    out: list[dict] = []
    for c, s in ranked[:top_k]:
        c2 = dict(c)
        c2["_rerank_score"] = round(float(s), 6)
        out.append(c2)
    return out


if __name__ == "__main__":
    # Smoke test: verify the model loads and ranks a synthetic pair.
    query = "how do organizations recover from a major crisis"
    cands = [
        {"fb_id": "a", "definition": "Collective intelligence recovers after crisis through shared sense-making."},
        {"fb_id": "b", "definition": "High contrast visual design uses strong value differences between elements."},
        {"fb_id": "c", "definition": "Time is a finite fungible resource treated as a commodity."},
    ]
    out = rerank_candidates(query, cands, top_k=3)
    for r in out:
        print(f"  {r['fb_id']}: {r['_rerank_score']} — {r['definition'][:60]}")
