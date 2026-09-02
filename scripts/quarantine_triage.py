#!/usr/bin/env python3
"""D2506: Stratified quarantine triage sampler.

Deterministic (seeded) stratified sample of S5 QUARANTINE records for human review.
Does NOT sweep — samples the highest-signal buckets only, so a human can triage
~50 records instead of 2,793.

Sample spec (senior-RAG heuristic):
    20  strong-ISOR  NEUTRAL   (NLI failed to entail a well-corroborated fact — highest recovery value)
    15  medium-ISOR  NEUTRAL
    10  weak-ISOR    NEUTRAL   (single-source tail — likely evidence-side, not FB-side)
     5  CONTRA       (strong/medium preferred — direct contradiction is the most actionable)

Output: CSV for spreadsheet review + per-record summary to stdout.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "knowledge pipeline" / "stage5_verify" / "t11" / "checkpoint.jsonl"
OUT_CSV = ROOT / "knowledge pipeline" / "stage5_verify" / "t11" / "quarantine_triage_sample.csv"

SEED = 2505  # deterministic (R7: temp=0.0 spirit)
SAMPLE_SPEC: list[tuple[str, str, int]] = [
    ("strong", "NEUTRAL", 20),
    ("medium", "NEUTRAL", 15),
    ("weak", "NEUTRAL", 10),
    ("strong", "CONTRA", 3),   # all strong CONTRA (most actionable contradictions)
    ("medium", "CONTRA", 2),   # + 2 medium CONTRA
]


def _nli_label(verification_results: list[dict]) -> str:
    for c in verification_results or []:
        if c.get("check_name") == "factual":
            detail = c.get("detail", "")
            if "ENTAIL" in detail:
                return "ENTAIL"
            if "NEUTRAL" in detail:
                return "NEUTRAL"
            if "CONTRA" in detail:
                return "CONTRA"
            return "OTHER"
    return "OTHER"


def _nli_score(verification_results: list[dict]) -> float | None:
    for c in verification_results or []:
        if c.get("check_name") == "factual":
            return c.get("score")
    return None


def load_buckets() -> dict[tuple[str, str], list[dict]]:
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with CHECKPOINT.open() as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("status") != "QUARANTINE":
                continue
            rating = (d.get("isor") or {}).get("rating")
            if rating not in ("strong", "medium", "weak"):
                continue
            label = _nli_label(d.get("verification_results") or [])
            if label not in ("NEUTRAL", "CONTRA"):
                continue
            buckets[(rating, label)].append(d)
    # sort deterministically by fb_id for reproducible selection
    for k in buckets:
        buckets[k].sort(key=lambda r: r.get("fb_id", ""))
    return buckets


def sample_records(buckets: dict[tuple[str, str], list[dict]]) -> list[dict]:
    rng = random.Random(SEED)
    picked: list[dict] = []
    for rating, label, n in SAMPLE_SPEC:
        pool = buckets[(rating, label)]
        # prefer deterministic spread: shuffle with fixed seed then take n
        idx = list(range(len(pool)))
        rng.shuffle(idx)
        take = idx[:n]
        picked.extend(pool[i] for i in take)
    return picked


def _short(rec: dict, key: str, n: int = 90) -> str:
    v = rec.get(key)
    if v is None:
        return ""
    s = str(v)
    return s if len(s) <= n else s[: n - 3] + "..."


def write_csv(records: list[dict]) -> Path:
    cols = [
        "fb_id", "name", "isor_rating", "isor_score", "nli_label", "nli_score",
        "evidence", "source_diversity", "classification_status", "taxonomy_match_method",
        "discipline_raw", "domains_raw", "definition", "mechanism", "source_books",
        "evidence_passages",
    ]
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            isor = r.get("isor") or {}
            w.writerow({
                "fb_id": r.get("fb_id"),
                "name": r.get("name"),
                "isor_rating": isor.get("rating"),
                "isor_score": isor.get("score"),
                "nli_label": _nli_label(r.get("verification_results") or []),
                "nli_score": _nli_score(r.get("verification_results") or []),
                "evidence": r.get("evidence"),
                "source_diversity": r.get("source_diversity"),
                "classification_status": r.get("classification_status"),
                "taxonomy_match_method": r.get("taxonomy_match_method"),
                "discipline_raw": r.get("discipline_raw"),
                "domains_raw": " | ".join(r.get("domains_raw") or []),
                "definition": r.get("definition"),
                "mechanism": r.get("mechanism"),
                "source_books": " | ".join(r.get("source_books") or []),
                # D2506: frontier-model reviews (claude0041/chatgpt0041) flagged that
                # EVIDENCE-GARBAGE / TRUE-CONTRADICTION / OK-RELEASABLE are unadjudicatable
                # without the passage text — include evidence_passages verbatim.
                "evidence_passages": " ␟ ".join(str(p) for p in (r.get("evidence_passages") or [])),
            })
    return OUT_CSV


def main() -> int:
    buckets = load_buckets()
    print("Bucket pool sizes (available -> requested):")
    for rating, label, n in SAMPLE_SPEC:
        avail = len(buckets[(rating, label)])
        print(f"  {rating:6s} {label:8s}: {avail:4d} available -> {n} requested  {'✅' if avail >= n else '⚠️ UNDER'}")
    print()

    records = sample_records(buckets)
    out = write_csv(records)
    print(f"Sampled {len(records)} records -> {out}")
    print()
    for r in records:
        isor = r.get("isor") or {}
        print("=" * 100)
        print(f"[{isor.get('rating')}/{_nli_label(r.get('verification_results') or [])}] "
              f"isor={isor.get('score')} nli={_nli_score(r.get('verification_results') or [])} "
              f"ev={r.get('evidence')} src_div={r.get('source_diversity')} "
              f"class={r.get('classification_status')} method={r.get('taxonomy_match_method')}")
        print(f"  NAME: {r.get('name')}")
        print(f"  DEF : {_short(r, 'definition', 160)}")
        print(f"  MECH: {_short(r, 'mechanism', 160)}")
        print(f"  SRC : {_short(r, 'source_books', 120)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
