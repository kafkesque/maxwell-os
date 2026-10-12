#!/usr/bin/env python3
"""T9 (BUG-705/D-B): build the blind, stratified paraphrase gold-scaffold DRAFT.

Deterministic, provenance-safe extraction of the canonical-run NEUTRAL population,
parsing the DeBERTa entail/contradiction counts out of verification_results, then a
blind stratified sample across (ent/cont bucket x discipline_macro) is emitted as a
DRAFT JSONL that a DIFFERENT-FAMILY LLM proxy labels {paraphrase_true|non_paraphrase}.

WHY THIS EXISTS (D-B): the S5 paraphrase RECALL path (pipeline/stage5_verify.py) can
flip a NEUTRAL verdict to PASS when (a) n_entail >= paraphrase_min_entail, (b) n_contra
== 0, and (c) bge-m3 STS cosine(definition, evidence) >= threshold. The threshold must
be CALIBRATED on a gold set (scripts/paraphrase_calibrate.py) before the path is
enabled. This script builds that gold set's CANDIDATE scaffold — it NEVER assigns gold
labels (R5 generator != verifier: the label must come from a model family other than
the Qwen3-Coder generator, e.g. gemma-4-E4B or Phi-4-mini).

POPULATION DECOMPOSITION (canonical run rechunk-v4-20260929, verified 2026-10-11):
    s5_reason='neutral' rows : 3142
      recoverable (ent>=1, cont==0) : 2258   -> paraphrase_true CANDIDATE pool
      ent0        (ent==0)          :  430   -> non_paraphrase control (no entailment)
      contra      (cont>0)          :  454   -> non_paraphrase control (contradicted)

STRATIFICATION (blind, deterministic):
    recoverable strata -> proportional to discipline_macro (min 1 per non-empty bucket)
    control strata     -> ent0 + contra, fixed counts
    seeded RNG (--seed) so the sample is reproducible and auditable.

OUTPUT:
    draft JSONL lines: {fb_id, definition, evidence, evidence_passages, discipline,
                        discipline_macro, ent_count, contra_count, max_ent, bucket,
                        label}  where label == "TBD" (never guessed).

    The `evidence` field is the clean-passage context (joined, truncated to
    paraphrase_max_chars) the labeller judges against `definition`. This is the SAME
    text the calibration script embeds, so label + cosine are measured on one surface.

KNOWN LIMITATION (recorded, not silently ignored): production _paraphrase_similarity
takes MAX STS cosine over up to 8 clean passages, whereas paraphrase_calibrate.py
computes a single cosine against the joined evidence string. The single-string cosine
is a LOWER BOUND on production's max, so a threshold calibrated here is conservative
(fail-closed). A later enhancement may teach paraphrase_calibrate.py to accept an
evidence_passages list and take the max — that is out of scope for this scaffold.

Usage:
    python3 scripts/t9_paraphrase_gold_scaffold.py [--out PATH] [--recoverable N]
        [--ent0 N] [--contra N] [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # scripts run as `python3 scripts/...`, so ROOT must be on path

from pipeline.pipeline_paths import DB_PATH, CANONICAL_RUN  # noqa: E402

# D-2929 lesson applied here too: no abstention bucket is ever scored as a positive
# class. discipline_macro is used ONLY for stratification balance, never as a label.
_ENT_CONT_RE = re.compile(r"ent (\d+)/(\d+), cont (\d+)/(\d+)")
_MAX_RE = re.compile(r"max=(\d+\.\d+)")

# Paraphrase evidence window — kept in sync with stage5.paraphrase_max_chars (C12
# config-first would read pipeline_config.yaml; we mirror the value and assert below).
_PARAPHRASE_MAX_CHARS = 1500


def _parse_ent_cont(detail: str) -> tuple[int, int, float] | None:
    """Parse 'NEUTRAL (ent X/Y, cont Z/W): max=M' -> (ent_count, cont_count, max_ent)."""
    m = _ENT_CONT_RE.search(detail)
    if not m:
        return None
    ent_c = int(m.group(1))
    cont_c = int(m.group(3))
    mx = _MAX_RE.search(detail)
    max_ent = float(mx.group(1)) if mx else 0.0
    return ent_c, cont_c, max_ent


def _bucket(ent_c: int, cont_c: int) -> str:
    """Classify a NEUTRAL row into the paraphrase-scaffold stratum bucket."""
    if ent_c >= 1 and cont_c == 0:
        return "recoverable"
    if cont_c > 0:
        return "contra"
    return "ent0"


def _clean_passages(evidence_passages: str | None, max_chars: int) -> list[str]:
    """Decode the JSON-array evidence_passages column into a list of non-empty strings."""
    if not evidence_passages:
        return []
    try:
        parsed = json.loads(evidence_passages)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    out: list[str] = []
    for p in parsed:
        if isinstance(p, str) and p.strip():
            out.append(p.strip()[:max_chars])
    return out


def load_canonical_neutral(db_path: Path) -> list[dict]:
    """Extract all canonical-run NEUTRAL rows with parsed ent/cont + clean passages."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(
        "SELECT fb_id, definition, evidence_passages, discipline, discipline_macro, "
        "verification_results FROM fbs WHERE s5_reason='neutral' AND pipeline_run_id=?",
        (CANONICAL_RUN,),
    )
    rows: list[dict] = []
    for r in cur.fetchall():
        detail = ""
        if r["verification_results"]:
            try:
                lst = json.loads(r["verification_results"])
            except json.JSONDecodeError:
                lst = []
            for item in lst:
                if isinstance(item, dict) and item.get("check_name") == "factual":
                    detail = item.get("detail", "")
                    break
        parsed = _parse_ent_cont(detail)
        if parsed is None:
            continue  # no factual NLI detail — not part of the NEUTRAL population
        ent_c, cont_c, max_ent = parsed
        definition = (r["definition"] or "").strip()
        passages = _clean_passages(r["evidence_passages"], _PARAPHRASE_MAX_CHARS)
        if not definition or not passages:
            continue  # no definition or no clean evidence -> cannot be judged/labelled
        macro = (r["discipline_macro"] or "").strip() or "emerging"
        rows.append(
            {
                "fb_id": r["fb_id"],
                "definition": definition,
                "evidence": "\n\n".join(passages)[:_PARAPHRASE_MAX_CHARS],
                "evidence_passages": passages,
                "discipline": r["discipline"],
                "discipline_macro": macro,
                "ent_count": ent_c,
                "cont_count": cont_c,
                "max_ent": max_ent,
                "bucket": _bucket(ent_c, cont_c),
            }
        )
    con.close()
    return rows


def stratified_sample(rows: list[dict], recoverable_n: int, ent0_n: int, contra_n: int, seed: int) -> list[dict]:
    """Deterministic blind stratified sample across bucket x discipline_macro."""
    rng = random.Random(seed)
    buckets: dict[str, list[dict]] = {"recoverable": [], "ent0": [], "contra": []}
    for r in rows:
        buckets[r["bucket"]].append(r)

    def _proportional(pool: list[dict], n: int) -> list[dict]:
        """Proportional-to-macro stratified sample, min 1 per non-empty macro bucket."""
        by_macro: dict[str, list[dict]] = {}
        for r in pool:
            by_macro.setdefault(r["discipline_macro"], []).append(r)
        if n <= 0:
            return []
        n_macro = len(by_macro)
        # allocate at least 1 per non-empty macro bucket, remainder proportional
        base = min(n, n_macro)
        alloc: dict[str, int] = {m: 1 for m in by_macro}
        remainder = n - base
        # proportional allocation of remainder by population share
        total = len(pool)
        for i, (m, group) in enumerate(sorted(by_macro.items())):
            share = int(remainder * len(group) / total)
            alloc[m] += share
        # top up any shortfall with the largest buckets
        short = n - sum(alloc.values())
        for m, _ in sorted(by_macro.items(), key=lambda kv: -len(kv[1])):
            if short <= 0:
                break
            alloc[m] += 1
            short -= 1
        out: list[dict] = []
        for m, group in by_macro.items():
            take = min(alloc.get(m, 0), len(group))
            out.extend(rng.sample(group, take))
        return out

    sample: list[dict] = []
    sample.extend(_proportional(buckets["recoverable"], recoverable_n))
    sample.extend(rng.sample(buckets["ent0"], min(ent0_n, len(buckets["ent0"]))))
    sample.extend(rng.sample(buckets["contra"], min(contra_n, len(buckets["contra"]))))
    # sort by bucket then fb_id for a stable, auditable ordering
    order = {"recoverable": 0, "ent0": 1, "contra": 2}
    sample.sort(key=lambda r: (order[r["bucket"]], r["fb_id"]))
    return sample


def emit_draft(sample: list[dict], out: Path) -> None:
    """Write the draft JSONL; label is 'TBD' (never guessed) + metadata for audit."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in sample:
            f.write(
                json.dumps(
                    {
                        "fb_id": r["fb_id"],
                        "definition": r["definition"],
                        "evidence": r["evidence"],
                        "evidence_passages": r["evidence_passages"],
                        "discipline": r["discipline"],
                        "discipline_macro": r["discipline_macro"],
                        "ent_count": r["ent_count"],
                        "cont_count": r["cont_count"],
                        "max_ent": r["max_ent"],
                        "bucket": r["bucket"],
                        "label": "TBD",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="T9 paraphrase gold-scaffold draft builder")
    ap.add_argument("--out", type=Path, default=Path("governance/t9_paraphrase_gold_draft.jsonl"))
    ap.add_argument("--recoverable", type=int, default=30, help="recoverable (paraphrase_true candidate) sample size")
    ap.add_argument("--ent0", type=int, default=10, help="ent==0 non-paraphrase control size")
    ap.add_argument("--contra", type=int, default=10, help="cont>0 non-paraphrase control size")
    ap.add_argument("--seed", type=int, default=0, help="deterministic seed (auditable)")
    args = ap.parse_args()

    rows = load_canonical_neutral(DB_PATH)
    by_bucket: dict[str, int] = {}
    by_macro: dict[str, int] = {}
    for r in rows:
        by_bucket[r["bucket"]] = by_bucket.get(r["bucket"], 0) + 1
        if r["bucket"] == "recoverable":
            by_macro[r["discipline_macro"]] = by_macro.get(r["discipline_macro"], 0) + 1

    print(f"canonical run: {CANONICAL_RUN}")
    print(f"NEUTRAL population (with definition + clean evidence): {len(rows)}")
    print("bucket census:", dict(sorted(by_bucket.items())))
    print("recoverable macro census:", dict(sorted(by_macro.items())))

    sample = stratified_sample(rows, args.recoverable, args.ent0, args.contra, args.seed)
    emit_draft(sample, args.out)
    print(f"\nwrote {len(sample)} draft rows to {args.out}")
    print("sample bucket census:", {b: sum(1 for r in sample if r["bucket"] == b) for b in ("recoverable", "ent0", "contra")})
    print("sample macro census:", dict(sorted({r["discipline_macro"]: sum(1 for s in sample if s["discipline_macro"] == r["discipline_macro"]) for r in sample}.items())))
    print("\nNEXT: label each row {paraphrase_true | non_paraphrase} with a different-family LLM proxy,")
    print("then run: python3 scripts/paraphrase_calibrate.py --gold <labelled> --decision D-XXXX")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
