#!/usr/bin/env python3
"""detect_same_work_content.py — READ-ONLY full-text content dedup (Option B, D-2737).

Complements scripts/detect_title_renames.py. The title-level detector only sees
near-duplicates that SHARE title shingles (typos, subtitle variants, BUG-604 mis-splits).
This detector catches the OTHER class: the SAME work under DIFFERENT titles that share
zero title characters ("Systemantics" == "The Systems Bible") — by shingling the FULL
DOCUMENT TEXT, not the title. Same author + near-identical content => same work.

Sovereign (C2/C3/C22): reads only local MD files via source_path, no network, no new
dependency (numpy only, already in the pipeline). Deterministic (seeded MinHash +
blake2b shingle hash) so results do not drift run-to-run.

DETECTOR, not a gate: never merges, never writes to the pipeline. Surfaces candidate
pairs for owner gating. Candidate generation uses MinHash (128 hashes, recall-oriented
low threshold so no false negatives), then EXACT Jaccard on the full (capped) shingle
sets for the few flagged pairs.

Exit codes: 0 = ran clean (candidates are expected, reported not failed);
            1 = config/cache read error; 2 = --selftest control failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from pipeline.book_metadata import compute_source_id  # noqa: E402

CONFIG_REL = "config/eval_integrity.yaml"
_DEFAULTS: dict[str, Any] = {
    "shingle_k": 5,
    "num_hashes": 128,
    "recall_threshold": 0.30,
    "report_threshold": 0.50,
    "max_shingles_per_doc": 100000,
    "min_words": 200,
    "seed": 20260930,
    "metadata_cache_file": "knowledge pipeline/checkpoints/book_metadata.jsonl",
    "report_file": "governance/same_work_content_candidates.json",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _load_config() -> dict[str, Any]:
    """Load the `same_work_content` block from eval_integrity.yaml (C12 config home)."""
    cfg_path = _PROJECT_ROOT / CONFIG_REL
    if not cfg_path.exists():
        return dict(_DEFAULTS)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    block = data.get("same_work_content") or {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in block.items() if k in _DEFAULTS})
    return merged


def _shingle_hash(shingle: str) -> int:
    """Stable 64-bit hash (blake2b) — deterministic across runs/processes."""
    return int.from_bytes(hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest(), "big")


def word_shingles(text: str, k: int) -> set[str]:
    """Word k-gram set over lowercase alnum tokens."""
    words = _WORD_RE.findall(text.lower())
    if len(words) < k:
        return set()
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def minhash_signature(shingle_hashes: np.ndarray, num: int, seed: int) -> np.ndarray:
    """MinHash signature: h_i(x) = (a_i * x + b_i) mod 2^64, min over all shingle hashes."""
    rng = np.random.default_rng(seed)
    a = rng.integers(1, 2**63, size=num, dtype=np.uint64)
    b = rng.integers(0, 2**63, size=num, dtype=np.uint64)
    x = shingle_hashes.astype(np.uint64)
    # (num, len(x)) broadcast; uint64 wraps mod 2^64 exactly as intended.
    h = (a[:, None] * x[None, :] + b[:, None])
    return h.min(axis=1)


def _estimate_jaccard(sa: np.ndarray, sb: np.ndarray) -> float:
    return float((sa == sb).sum()) / len(sa)


def _exact_jaccard(ha: np.ndarray, hb: np.ndarray) -> float:
    inter = np.intersect1d(ha, hb, assume_unique=True)
    return float(inter.size) / float(ha.size + hb.size - inter.size)


def load_metadata(cache_rel: str) -> list[dict[str, str]]:
    """Read the metadata cache (JSONL). Raises on missing/unreadable corpus."""
    cache_path = _PROJECT_ROOT / cache_rel
    if not cache_path.exists():
        raise FileNotFoundError(f"metadata cache not found: {cache_path}")
    recs: list[dict[str, str]] = []
    with cache_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def _representatives(recs: list[dict[str, str]]) -> tuple[list[dict[str, Any]], int]:
    """One representative per distinct source_id, with an EXISTING local source_path."""
    by_id: dict[str, dict[str, Any]] = {}
    for r in recs:
        author = (r.get("author") or "").strip()
        title = (r.get("title") or "").strip()
        sp = (r.get("source_path") or "").strip()
        sid = compute_source_id(author, title)
        if sid not in by_id:
            by_id[sid] = {"source_id": sid, "author": author, "title": title, "path": sp}
        elif sp and not by_id[sid]["path"]:
            by_id[sid]["path"] = sp
    reps: list[dict[str, Any]] = []
    missing = 0
    for r in by_id.values():
        if r["path"] and os.path.exists(r["path"]):
            reps.append(r)
        else:
            missing += 1
    return reps, missing


def _full_text_hashes(path: str, cfg: dict[str, Any]) -> np.ndarray:
    """Read MD file -> word shingles -> sorted unique int64 hashes (capped)."""
    k = int(cfg["shingle_k"])
    cap = int(cfg["max_shingles_per_doc"])
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    sh = word_shingles(text, k)
    if not sh:
        return np.array([], dtype=np.uint64)
    hashes = np.array([_shingle_hash(s) for s in sh], dtype=np.uint64)
    if hashes.size > cap:
        rng = np.random.default_rng(int(cfg["seed"]))
        hashes = rng.choice(hashes, size=cap, replace=False)
    return np.unique(hashes)


def run_scan(cfg: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """MinHash candidate generation + exact-Jaccard verification over distinct works."""
    recs = load_metadata(cfg["metadata_cache_file"])
    reps, missing = _representatives(recs)
    num = int(cfg["num_hashes"])
    seed = int(cfg["seed"])
    recall = float(cfg["recall_threshold"])
    report_thr = float(cfg["report_threshold"])
    min_words = int(cfg["min_words"])

    sigs: list[np.ndarray] = []
    full: list[np.ndarray] = []
    skipped = 0
    for r in reps:
        hashes = _full_text_hashes(r["path"], cfg)
        # min_words gate: a near-empty doc cannot support content resemblance
        if hashes.size < min_words:
            skipped += 1
            sigs.append(None)  # type: ignore[arg-type]
            full.append(hashes)
            continue
        full.append(hashes)
        sigs.append(minhash_signature(hashes, num, seed))

    candidates: list[dict[str, Any]] = []
    n = len(reps)
    for i in range(n):
        if sigs[i] is None:
            continue
        for j in range(i + 1, n):
            if sigs[j] is None:
                continue
            est = _estimate_jaccard(sigs[i], sigs[j])
            if est >= recall:
                exact = _exact_jaccard(full[i], full[j])
                if exact >= report_thr:
                    candidates.append(
                        {
                            "a_id": reps[i]["source_id"],
                            "b_id": reps[j]["source_id"],
                            "a": f"{reps[i]['author']} — {reps[i]['title']}",
                            "b": f"{reps[j]['author']} — {reps[j]['title']}",
                            "similarity": round(exact, 4),
                        }
                    )
    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    summary = {
        "records": len(recs),
        "distinct_works": n,
        "full_text_resolved": len(reps),
        "missing_source_path": missing,
        "skipped_short_docs": skipped,
        "candidate_count": len(candidates),
    }
    return summary, candidates


def _crash_safe_write(path: Path, payload: dict[str, Any]) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".same_work_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _selftest() -> int:
    """Known-answer controls (BUG-492): the shingling+MinHash math must fire correctly."""
    k = int(_DEFAULTS["shingle_k"])
    num = int(_DEFAULTS["num_hashes"])
    seed = int(_DEFAULTS["seed"])
    fails: list[str] = []

    # Control 1: SAME work, DIFFERENT titles (shared body, different title line) -> FLAGGED.
    body = " ".join(f"the system is governed by a set of laws that interact in nonlinear ways {i}" for i in range(500))
    t_a = f"Systemantics {body}"
    t_b = f"The Systems Bible {body}"
    ha = np.array([_shingle_hash(s) for s in word_shingles(t_a, k)], dtype=np.uint64)
    hb = np.array([_shingle_hash(s) for s in word_shingles(t_b, k)], dtype=np.uint64)
    sig_a = minhash_signature(ha, num, seed)
    sig_b = minhash_signature(hb, num, seed)
    est = _estimate_jaccard(sig_a, sig_b)
    if est < _DEFAULTS["recall_threshold"]:
        fails.append(f"same-work-different-title not flagged: est={est:.3f}")

    # Control 2: two CLEARLY distinct works -> NOT flagged.
    t_c = " ".join(f"a history of the roman empire and its legions across europe {i}" for i in range(500))
    hc = np.array([_shingle_hash(s) for s in word_shingles(t_c, k)], dtype=np.uint64)
    sig_c = minhash_signature(hc, num, seed)
    est2 = _estimate_jaccard(sig_a, sig_c)
    if est2 >= _DEFAULTS["recall_threshold"]:
        fails.append(f"distinct works falsely flagged: est={est2:.3f}")

    # Control 3: identical text -> ~1.0 resemblance.
    est3 = _estimate_jaccard(sig_a, sig_a)
    if est3 < 0.999:
        fails.append(f"identical text resemblance not 1.0: {est3:.3f}")

    if fails:
        print("FAIL detect_same_work_content selftest: " + " | ".join(fails))
        return 2
    print(
        f"ok detect_same_work_content selftest: 3/3 (same-work-diff-title est={est:.3f}, "
        f"distinct est={est2:.3f}, identical={est3:.3f})"
    )
    return 0


def _run(report: bool) -> int:
    cfg = _load_config()
    summary, cands = run_scan(cfg)
    print(
        f"same_work_content scan: {summary['records']} records -> {summary['distinct_works']} distinct works "
        f"({summary['full_text_resolved']} full-text resolved, {summary['missing_source_path']} missing path, "
        f"{summary['skipped_short_docs']} short-doc skipped) -> {summary['candidate_count']} candidate pairs "
        f"(exact Jaccard >= {cfg['report_threshold']})"
    )
    if report and cands:
        report_path = _PROJECT_ROOT / cfg["report_file"]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        _crash_safe_write(
            report_path,
            {
                "schema_version": "1.0",
                "detector": "scripts/detect_same_work_content.py",
                "mode": "READ-ONLY candidates — owner gate required, never auto-merge (D-2737)",
                "shingle_k": cfg["shingle_k"],
                "num_hashes": cfg["num_hashes"],
                "report_threshold": cfg["report_threshold"],
                **summary,
                "candidates": cands,
            },
        )
        print(f"wrote {report_path} ({len(cands)} candidates)")
        for c in cands[:20]:
            print(f"  {c['similarity']:.3f}  {c['a']}  <=>  {c['b']}")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    return _run(report="--report" in argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
