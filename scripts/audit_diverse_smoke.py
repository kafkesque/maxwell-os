#!/usr/bin/env python3
"""audit_diverse_smoke.py — diverse conformance smoke test across the real S2 corpora.

Problem it fixes: the prior smoke matrix (`scripts/smoke_matrix_5x3.py`) and e2e proof
(`scripts/e2e_proof.py`) recycled a handful of hand-written fixtures (the same
principle/TI/PT) — so they never exercised the full (origin × content_type) matrix
against the *actual* extraction output. This script samples DIVERSE records from the
two real S2 corpora and audits every sampled record against config/content_types.yaml
(shared core_body, per-type s2_body_fields, classification labels) via `audit_s2`.

Origins:
  * convergent    — multi-source (checkpoint.jsonl, is_convergent=True). Structurally
                    principle-only (BUG-166); any non-principle convergent record is flagged.
  * single_source — one book (checkpoint.jsonl, not convergent, not singleton).
  * singleton     — one segment (singleton_fbs.jsonl, is_singleton_fb=True).

Deterministic (seeded), no LLM, no network. Read-only — never mutates the corpus.
Sample size per cell is config-driven; the rarest cells (growth_edge, and convergent
non-principle) are sampled EXHAUSTIVELY so no edge case is skipped.

Usage:
    python3 scripts/audit_diverse_smoke.py [--per-cell 12] [--seed 42]

Exit 0 when every sampled record conforms to the agreed S2 contract; exit 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audit_content_type_contract import audit_s2, _load_ontology  # noqa: E402

# C12: corpus paths are NOT hardcoded here — they are resolved via pipeline_paths,
# but the two S2 artifacts are the canonical single-source+convergent and singleton
# outputs. Kept as module constants for the audit (read-only).
DEDUP_PATH = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.jsonl"
SINGLETON_PATH = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "singleton_fbs.jsonl"

CONTENT_TYPES = ("principle", "process_template", "process_instance", "tool_instruction", "growth_edge")
ORIGINS = ("convergent", "single_source", "singleton")


def _load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _origin_of(rec: dict) -> str:
    if rec.get("is_singleton_fb") is True:
        return "singleton"
    if rec.get("is_convergent") is True:
        return "convergent"
    return "single_source"


def _sample(recs: list[dict], k: int, seed: int) -> list[dict]:
    """Deterministic diverse sample: seeded shuffle + take k. Exhaustive when k >= len."""
    rng = random.Random(seed)
    shuffled = list(recs)
    rng.shuffle(shuffled)
    return shuffled[:k]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=12,
                    help="max records sampled per (origin × type) cell")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    onto = _load_ontology()
    dedup = _load_jsonl(DEDUP_PATH)
    singleton = _load_jsonl(SINGLETON_PATH)

    # Bucket records by (origin, content_type).
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in dedup + singleton:
        ct = rec.get("content_type") or "principle"
        buckets[(_origin_of(rec), ct)].append(rec)

    print(f"Corpora: checkpoint.jsonl={len(dedup)} records, "
          f"singleton_fbs.jsonl={len(singleton)} records")
    print(f"Sampling ≤{args.per_cell} per (origin × type) cell (seed={args.seed}); "
          "rare cells sampled exhaustively.\n")

    all_ok = True
    header = f"{'origin × content_type':38s} {'sampled':>7s} {'ok':>4s} {'gaps':>5s}"
    print(header)
    print("-" * len(header))

    gap_report: dict[str, Counter] = {}
    for origin in ORIGINS:
        for ct in CONTENT_TYPES:
            cell = (origin, ct)
            pool = buckets.get(cell, [])
            # Exhaustive for rare cells; bounded for abundant ones.
            if ct == "growth_edge" or (origin == "convergent" and ct != "principle"):
                sample = pool
            else:
                sample = _sample(pool, args.per_cell, args.seed)

            if not pool and not sample:
                print(f"{origin+' × '+ct:38s} {'—':>7s} {'—':>4s} {'—':>5s}")
                continue

            ok = 0
            gaps: Counter = Counter()
            for rec in sample:
                issues: list[str] = []
                audit_s2(rec, ct, onto, issues)
                if issues:
                    for i in issues:
                        gaps[i] += 1
                else:
                    ok += 1
            if gaps:
                all_ok = False
                gap_report[cell] = gaps

            print(f"{origin+' × '+ct:38s} {len(sample):>7d} {ok:>4d} {sum(gaps.values()):>5d}")

    # Convergent non-principle anomaly (BUG-166 expected to be empty).
    conv_nonp = sum(len(v) for (o, c), v in buckets.items() if o == "convergent" and c != "principle")
    print(f"\n⚠️  convergent non-principle records in corpus: {conv_nonp} "
          f"(expected 0 — BUG-166: convergent is structurally principle-only)")

    if gap_report:
        print("\n=== GAP DETAILS (issue type → #sampled records) ===")
        for (origin, ct), gaps in sorted(gap_report.items()):
            print(f"\n  {origin} × {ct}:")
            for issue, n in gaps.most_common():
                print(f"      • {n:>3d}  {issue}")

    print()
    print("✅ DIVERSE SMOKE: all sampled records conform to content_types.yaml"
          if all_ok else "❌ DIVERSE SMOKE: conformance gaps found above")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
