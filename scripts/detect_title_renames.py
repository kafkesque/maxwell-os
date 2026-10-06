#!/usr/bin/env python3
"""detect_title_renames.py — READ-ONLY Broder-shingling detector for near-duplicate
book identities the canonical source_id normalization (D2176) did NOT collapse.

This is a DETECTOR, not a gate. It never merges, never writes to the pipeline, and
never changes a source_id. It only SURFACES candidate pairs (same work, near-identical
title+author strings that still hash to DIFFERENT source_ids) for owner gating.

Why it exists: `compute_source_id()` collapses edition/subtitle/case/co-author variants,
but a single typo or an unrecognized subtitle-opener yields a DIFFERENT source_id and the
book counts as two distinct works again (BUG-289 tail). Exact character k-gram resemblance
(Broder) catches those missed near-duplicates deterministically — no probabilistic linkage,
no new dependency (D-2735).

Known blindspot (documented, not silent): truly DIFFERENT titles for the same work
("Systemantics" == "The Systems Bible") share no shingles and are INVISIBLE here — that
case is the owner-curated alias map, not this detector. Ultra-short titles (< min_title_chars)
are skipped because k-gram Jaccard is unreliable on tiny strings.

Exit codes: 0 = ran clean (candidates are EXPECTED and reported, not failed);
            1 = config/cache read error (the detector could not see the corpus);
            2 = --selftest control failure (the detector's own math is broken).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402

from pipeline.book_metadata import (  # noqa: E402
    compute_source_id,
    normalize_author,
    normalize_title,
)

CONFIG_REL = "config/eval_integrity.yaml"
_DEFAULTS: dict[str, Any] = {
    "shingle_k": 3,
    "jaccard_threshold": 0.60,
    "min_title_chars": 8,
    "metadata_cache_file": "knowledge pipeline/checkpoints/book_metadata.jsonl",
    "report_file": "governance/title_rename_candidates.json",
}


def _load_config() -> dict[str, Any]:
    """Load the `title_dedup` block from eval_integrity.yaml (C12 config home)."""
    cfg_path = _PROJECT_ROOT / CONFIG_REL
    if not cfg_path.exists():
        return dict(_DEFAULTS)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    block = data.get("title_dedup") or {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in block.items() if k in _DEFAULTS})
    return merged


def shingles(text: str, k: int) -> set[str]:
    """Character k-gram set (Broder shingling)."""
    t = "".join(c for c in text if c.isalnum()).lower()
    if len(t) < k:
        return set()
    return {t[i : i + k] for i in range(len(t) - k + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    """Exact resemblance (Broder). Empty intersection guard."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


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


def _representatives(recs: list[dict[str, str]], min_chars: int) -> list[dict[str, Any]]:
    """Collapse records to one representative per DISTINCT source_id (same book, many files)."""
    by_id: dict[str, dict[str, Any]] = {}
    for r in recs:
        author = (r.get("author") or "").strip()
        title = (r.get("title") or "").strip()
        sid = compute_source_id(author, title)
        if sid not in by_id:
            by_id[sid] = {
                "source_id": sid,
                "author": author,
                "title": title,
                "norm": f"{normalize_author(author)} {normalize_title(title)}".strip(),
                "files": 1,
            }
        else:
            by_id[sid]["files"] += 1
    reps = list(by_id.values())
    return [r for r in reps if len(r["norm"]) >= min_chars]


def find_candidates(reps: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Pairwise exact-Jaccard scan over distinct source_ids. Deterministic, no approximation."""
    k = int(cfg["shingle_k"])
    threshold = float(cfg["jaccard_threshold"])
    sigs = [shingles(r["norm"], k) for r in reps]
    cands: list[dict[str, Any]] = []
    n = len(reps)
    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard(sigs[i], sigs[j])
            if sim >= threshold:
                cands.append(
                    {
                        "a_id": reps[i]["source_id"],
                        "b_id": reps[j]["source_id"],
                        "a": f"{reps[i]['author']} — {reps[i]['title']}",
                        "b": f"{reps[j]['author']} — {reps[j]['title']}",
                        "similarity": round(sim, 4),
                    }
                )
    cands.sort(key=lambda c: c["similarity"], reverse=True)
    return cands


def _crash_safe_write(path: Path, payload: dict[str, Any]) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".title_dedup_", suffix=".json")
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
    """Known-answer controls (BUG-492): the detector's math must fire correctly."""
    k = int(_DEFAULTS["shingle_k"])
    thr = float(_DEFAULTS["jaccard_threshold"])
    fails: list[str] = []

    # Control 1: a typo in the title (near-duplicate, DIFFERENT source_id) must be FLAGGED.
    a = f"{normalize_author('Brian Kernighan')} {normalize_title('The C Programming Language')}"
    b = f"{normalize_author('Brian Kernighan')} {normalize_title('The C Programmng Language')}"
    sim1 = jaccard(shingles(a, k), shingles(b, k))
    if sim1 < thr:
        fails.append(f"typo-near-duplicate not flagged: sim={sim1:.3f} < {thr}")

    # Control 2: IDENTICAL title (same source_id) must NOT be flagged as a distinct pair.
    c = f"{normalize_author('Brian Kernighan')} {normalize_title('The C Programming Language')}"
    if compute_source_id("Brian Kernighan", "The C Programming Language") != compute_source_id(
        "Brian Kernighan", "The C Programming Language"
    ):
        fails.append("identical title produced different source_ids")

    # Control 3: two CLEARLY distinct works must NOT be flagged.
    d = f"{normalize_author('Jane Austen')} {normalize_title('Pride and Prejudice')}"
    e = f"{normalize_author('Donald Knuth')} {normalize_title('The Art of Computer Programming')}"
    sim3 = jaccard(shingles(d, k), shingles(e, k))
    if sim3 >= thr:
        fails.append(f"distinct works falsely flagged: sim={sim3:.3f} >= {thr}")

    # Control 4: subtitle variant must collapse to the SAME source_id (normalization intact).
    if compute_source_id("Malcolm Gladwell", "Blink: The Power of Thinking Without Thinking") != compute_source_id(
        "Malcolm Gladwell", "Blink The Power of Thinking Without Thinking"
    ):
        fails.append("subtitle variant did not collapse to one source_id")

    if fails:
        print("FAIL detect_title_renames selftest: " + " | ".join(fails))
        return 2
    print(
        f"ok detect_title_renames selftest: 4/4 controls (typo-flagged sim={sim1:.3f}, "
        f"distinct-not-flagged sim={sim3:.3f}, subtitle-collapses, identical-stable)"
    )
    return 0


def _run(report: bool) -> int:
    cfg = _load_config()
    recs = load_metadata(cfg["metadata_cache_file"])
    reps = _representatives(recs, int(cfg["min_title_chars"]))
    cands = find_candidates(reps, cfg)
    n_files = len(recs)
    print(
        f"title_dedup scan: {n_files} metadata records -> {len(reps)} distinct source_ids "
        f"(min_title_chars={cfg['min_title_chars']}) -> {len(cands)} candidate near-duplicate pairs "
        f"(jaccard >= {cfg['jaccard_threshold']})"
    )
    if report and cands:
        report_path = _PROJECT_ROOT / cfg["report_file"]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        _crash_safe_write(
            report_path,
            {
                "schema_version": "1.0",
                "detector": "scripts/detect_title_renames.py",
                "mode": "READ-ONLY candidates — owner gate required, never auto-merge (D-2735)",
                "shingle_k": cfg["shingle_k"],
                "jaccard_threshold": cfg["jaccard_threshold"],
                "distinct_source_ids": len(reps),
                "candidate_count": len(cands),
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
