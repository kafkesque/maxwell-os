#!/usr/bin/env python3
"""P1.3 — cross-family disagreement sample on the relabeled output (D2431).

Runs a cross-family judge (gemma-4-E4B — Google family, vs the Qwen3 relabel
generator — Alibaba family) over a sample of relabeled single-source records
using the SAME decision ladder, then reports agreement and writes a review
queue. R5 satisfied: judge family != generator family.

NOTE: gpt-oss-20b (VERIFY_MODEL) was the original choice but cold-reloads
every call in the current 7-model pool and returns empty content (D2408 not
effective for a 20B model that can't stay resident) — gemma-4-E4B is confirmed
working (~2s/call) and cross-family.

Usage:
    MAXWELL_RUN_ID=t11 python3 -u pipeline/disagreement_sample.py \
        --checkpoint "relabel_work/checkpoint.jsonl" --sample 100
"""
from __future__ import annotations
import argparse, json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write
from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import STAGE2_CHECKPOINT, S4_DEPTH_MODEL
from pipeline.stage2_relabel_extraction_type import _build_prompt, _extract_label

SYSTEM = "You are a precise JSON generator. Return ONLY valid JSON. No markdown."
JUDGE_MODEL = S4_DEPTH_MODEL  # gemma-4-E4B-it-MLX-4bit (default S4 depth model)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=str(STAGE2_CHECKPOINT))
    ap.add_argument("--sample", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--convergent-only", action="store_true",
                    help="Sample convergent (multi-source) records instead of single-source")
    ap.add_argument("--out", default=None, help="Output path override")
    args = ap.parse_args()

    records = load_jsonl(args.checkpoint, context="relabeled checkpoint")
    ss = [r for r in records if (r.get("is_convergent") if args.convergent_only else not r.get("is_convergent")) and r.get("evidence_passages")]
    random.seed(args.seed)
    sample = random.sample(ss, min(args.sample, len(ss)))

    print(f"cross-family disagreement sample: {len(sample)} records ({JUDGE_MODEL} vs Qwen3 relabel)")
    rows = []
    agree = disagree = empty = 0
    t0 = time.time()
    for i, rec in enumerate(sample):
        qwen = rec.get("extraction_type")
        try:
            res = call_omlx_json(
                prompt=_build_prompt(rec),
                model=JUDGE_MODEL,
                system=SYSTEM,
                max_tokens=64,
            )
            gpt = _extract_label(res)
        except Exception as e:
            gpt = ""
            print(f"   WARN {rec.get('name','?')[:40]}: {type(e).__name__}", file=sys.stderr, flush=True)
        if not gpt:
            empty += 1
        elif gpt == qwen:
            agree += 1
        else:
            disagree += 1
        rows.append({
            "fb_id": rec.get("fb_id"), "name": rec.get("name"),
            "content_type": rec.get("content_type"),
            "qwen_relabeled": qwen, "judge": gpt, "judge_model": JUDGE_MODEL,
            "agree": bool(gpt and gpt == qwen),
            "definition": (rec.get("definition") or "")[:400],
            "evidence": [e[:300] for e in (rec.get("evidence_passages") or [])][:3],
        })
        if (i + 1) % 25 == 0:
            print(f"   {i+1}/{len(sample)} done ({time.time()-t0:.0f}s)")

    out_path = args.out or str(Path(args.checkpoint).with_name(
        "disagreement_sample_convergent.jsonl" if args.convergent_only else "disagreement_sample.jsonl"))
    safe_write(out_path, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    n = len(sample)
    print(f"\nDONE in {time.time()-t0:.0f}s — sample {n}")
    print(f"   agree   : {agree} ({100*agree/n:.0f}%)")
    print(f"   disagree: {disagree} ({100*disagree/n:.0f}%)")
    print(f"   empty   : {empty}")
    print(f"   review queue: {out_path}")

if __name__ == "__main__":
    main()
