#!/usr/bin/env python3
"""P1.2 A/B: current decision ladder vs TIGHTENED ladder on human-adjudicated
records (58 disagreements, 49 with a non-NONE verdict). Measures % agreement
with the human verdict for each ladder — empirical answer to 'would tightening
the ladder help?' """
from __future__ import annotations
import json, sys, time
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import GEN_MODEL

RW = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("relabel_work")

CURRENT = (
    "DECISION ORDER (apply strictly, top-down — answer the FIRST question that matches):\n"
    "1. PRESCRIPTIVE (how-to, method, command, or \"do X to get Y\" advice)?\n"
    "   → normative_heuristic\n"
    "2. Else, evidence DEMONSTRATES a cause→effect chain (verbatim \"causes / leads to /\n"
    "   because Y\", not merely an explanation offered for an association)?\n"
    "   → causal_mechanism\n"
    "3. Else, observed co-occurrence / correlation / regularity (X goes with Y, no proven why)?\n"
    "   → empirical_pattern\n"
    "4. Else, taxonomy / typology / classification (\"categories relate as follows\")?\n"
    "   → descriptive_model\n"
    "DECOUPLING: judge from the EVIDENCE, not from the current mechanism wording. Do NOT\n"
    "upgrade association/advice/taxonomy to causal_mechanism just because the mechanism uses\n"
    "\"causes/because\". Prescriptive content is normative_heuristic even if it has an\n"
    "explanation. Return only the single most honest label."
)

TIGHTENED = (
    "DECISION ORDER (apply strictly, top-down — answer the FIRST question that matches):\n"
    "0. Is this a DEFINITION or DESCRIPTION of what something IS or HOW IT WORKS/OPERATES,\n"
    "   or a CLASSIFICATION/TAXONOMY (its categories, parts, or kinds)?\n"
    "   → descriptive_model. NEVER causal_mechanism.\n"
    "1. Is it PRESCRIPTIVE — advice, method, protocol, how-to, or \"do X to get Y\"?\n"
    "   → normative_heuristic.\n"
    "2. STRICT CAUSAL: does the EVIDENCE explicitly demonstrate a MECHANISTIC cause→effect\n"
    "   chain with specific intermediate steps (A does X, which causes B, which leads to C)?\n"
    "   A general statement that X relates to Y, an explanation of how a system works, a\n"
    "   single historical case, or a design/strategy description is NEVER causal.\n"
    "   → causal_mechanism (RAREST — the strongest claim).\n"
    "3. Else, observed co-occurrence / correlation / regularity (X goes with Y, no proven\n"
    "   why), including single historical examples and case studies → empirical_pattern.\n"
    "4. Else → descriptive_model.\n"
    "STRICT: causal_mechanism is the STRONGEST and RAREST claim. Definitions, how-systems-\n"
    "work, taxonomies, single cases, and design/strategy descriptions are NEVER causal.\n"
    "When in doubt between causal and a weaker claim, choose the WEAKER."
)

def prompt_for(rec: dict, ladder: str) -> str:
    ev = rec.get("evidence_passages") or []
    ev_snip = ev[:5] if isinstance(ev, list) else []
    return (
        "Re-classify the epistemic FORM (extraction_type) of this knowledge record.\n"
        "extraction_type ∈ [\"causal_mechanism\", \"empirical_pattern\", \"normative_heuristic\", \"descriptive_model\"]\n\n"
        f"{ladder}\n\n"
        "Record (do NOT change any text — only return the label):\n"
        f"name: {rec.get('name', '')}\n"
        f"definition: {rec.get('definition', '')}\n"
        f"mechanism: {rec.get('mechanism', '')}\n"
        f"boundary: {rec.get('boundary', '')}\n"
        f"consequence: {rec.get('consequence', '')}\n"
        f"evidence: {json.dumps(ev_snip, ensure_ascii=False)}\n\n"
        'Return JSON with exactly one key: {"extraction_type": "<one of the four>"}'
    )

def judge(prompt: str) -> str:
    res = call_omlx_json(prompt=prompt, model=GEN_MODEL,
                         system="You are a precise JSON generator. Return ONLY valid JSON. No markdown.",
                         max_tokens=64)
    obj = res[0] if isinstance(res, list) and res else res
    label = str(obj.get("extraction_type", "")).strip() if isinstance(obj, dict) else ""
    return label if label in ("causal_mechanism","empirical_pattern","normative_heuristic","descriptive_model") else ""

def main() -> None:
    verdicts = [json.loads(l) for l in open(RW / "human_review_verdicts.jsonl") if l.strip()]
    adjudicated = [v for v in verdicts if v["verdict"] != "NONE"]
    sample = [json.loads(l) for l in open(RW / "disagreement_sample.jsonl") if l.strip()]
    by_id = {s["fb_id"]: s for s in sample}
    print(f"adjudicated records: {len(adjudicated)} (of {len(verdicts)})")

    tasks = []
    for v in adjudicated:
        rec = by_id.get(v["fb_id"])
        if not rec: continue
        tasks.append((v, rec))

    results = {"current": [], "tightened": []}
    for name, ladder in (("current", CURRENT), ("tightened", TIGHTENED)):
        t0 = time.time()
        agree = 0; total = 0; empty = 0
        def one(t):
            v, rec = t
            return v["verdict"], judge(prompt_for(rec, ladder))
        with ThreadPoolExecutor(max_workers=4) as ex:
            pairs = list(ex.map(one, tasks))
        for human, model in pairs:
            if not model: empty += 1; continue
            total += 1
            if model == human: agree += 1
        results[name] = {"agree": agree, "total": total, "empty": empty,
                         "time": time.time()-t0}
        print(f"{name:10s}: {agree}/{total} = {100*agree/total if total else 0:.0f}% agree with human (empty={empty}) in {time.time()-t0:.0f}s")

    # also show human-vs-model transition for tightened vs current on same records
    print("\nper-record (human | current | tightened):")
    cur = {}; tig = {}
    # recompute needed per-record... do a quick second pass for the table (small)
    for v, rec in tasks[:30]:
        pass  # skip detailed table in background run; summary is what matters

if __name__ == "__main__":
    main()
