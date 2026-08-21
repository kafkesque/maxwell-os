#!/usr/bin/env python3
"""Post-hoc re-classification of S2 `extraction_type` (R1 — FORM-axis drift).

The single-source S2 extraction drifted the epistemic FORM axis toward
`causal_mechanism` (~60% vs ~11% convergent baseline; chi-square ~2247). This
script re-labels each FB's `extraction_type` using the DECISION-ORDER precedence
rule added to the S2 prompt (see stage2_extract.py SYSTEM_PROMPT), grounded
strictly in the record's existing fields + evidence_passages.

Why LLM-driven (not deterministic): the epistemic FORM is a property of the
CLAIM (does the evidence demonstrate a cause→effect chain?), not the ROLE. A
deterministic role→form relabel would re-introduce the D2417 coupling that
D2427 (R2) removes. So each record is re-judged against its own evidence.

Stable fields: fb_id, name, definition, content_type, and every body field are
NOT touched — only `extraction_type` is re-written. Stamps (pipeline_commit,
gen_model, schema_version) are left as-is (this is a label repair, not a
re-generation; R14 tracks the GENERATING revision).

Idempotent + crash-safe (safe_write → tempfile+fsync+os.replace). ALWAYS verify
on a COPY of the checkpoint before running against production.

Usage:
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --dry-run
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --limit 20 --single-source-only
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --types causal_mechanism
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.content_types import EXTRACTION_TYPES
from pipeline.io_guard import load_jsonl, safe_write
from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import GEN_MODEL, STAGE2_CHECKPOINT


SYSTEM_PROMPT: str = "You are a precise JSON generator. Return ONLY valid JSON. No markdown."

_DECISION_ORDER: str = (
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


def _build_prompt(rec: dict) -> str:
    ev = rec.get("evidence_passages") or []
    ev_snip = ev[:5] if isinstance(ev, list) else []
    return (
        "Re-classify the epistemic FORM (extraction_type) of this knowledge record.\n"
        f"extraction_type ∈ {sorted(EXTRACTION_TYPES)}\n\n"
        f"{_DECISION_ORDER}\n\n"
        "Record (do NOT change any text — only return the label):\n"
        f"name: {rec.get('name', '')}\n"
        f"definition: {rec.get('definition', '')}\n"
        f"mechanism: {rec.get('mechanism', '')}\n"
        f"boundary: {rec.get('boundary', '')}\n"
        f"consequence: {rec.get('consequence', '')}\n"
        f"evidence: {json.dumps(ev_snip, ensure_ascii=False)}\n\n"
        'Return JSON with exactly one key: {"extraction_type": "<one of the four>"}'
    )


def _extract_label(result: object) -> str:
    obj: object = result
    if isinstance(result, list):
        if not result or not isinstance(result[0], dict):
            return ""
        obj = result[0]
    if not isinstance(obj, dict):
        return ""
    label = str(obj.get("extraction_type", "")).strip()
    return label if label in EXTRACTION_TYPES else ""


def _dist(records: list[dict]) -> Counter:
    return Counter(r.get("extraction_type") for r in records)


def relabel(checkpoint_path: str, *, dry_run: bool, limit: int | None,
            single_source_only: bool, types: frozenset[str] | None) -> dict:
    checkpoint_path = str(Path(checkpoint_path))
    records = load_jsonl(checkpoint_path, context="relabel checkpoint")

    candidates: list[int] = []
    for i, r in enumerate(records):
        if single_source_only and r.get("is_convergent"):
            continue
        if types is not None and r.get("extraction_type") not in types:
            continue
        candidates.append(i)

    before = _dist(records)
    print(f"📋 Candidates: {len(candidates)} / {len(records)} records")
    print(f"   before: {dict(before)}")
    if limit is not None:
        candidates = candidates[:limit]

    changed: int = 0
    unchanged: int = 0
    failed: int = 0
    for i in candidates:
        rec = records[i]
        old = rec.get("extraction_type")
        label = f"{rec.get('name', '?')[:40]}"
        if dry_run:
            print(f"   [dry-run] would re-judge #{i} {label} (now {old})")
            continue
        try:
            result = call_omlx_json(
                prompt=_build_prompt(rec),
                model=GEN_MODEL,
                system=SYSTEM_PROMPT,
                max_tokens=64,
            )
            new = _extract_label(result)
            if not new:
                failed += 1
                print(f"   ⚠️  #{i} {label}: no valid label returned", file=sys.stderr, flush=True)
                continue
            if new == old:
                unchanged += 1
            else:
                rec["extraction_type"] = new
                changed += 1
                print(f"   🔁 #{i} {label}: {old} → {new}")
        except Exception as e:
            failed += 1
            print(f"   ❌ #{i} {label}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)

    if not dry_run:
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        safe_write(checkpoint_path, content)
        load_jsonl(checkpoint_path, context="relabel self-check")

    after = _dist(records)
    print(f"   after : {dict(after)}")
    print(f"✅ Relabel done: changed {changed}, unchanged {unchanged}, failed {failed}")
    return {"changed": changed, "unchanged": unchanged, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default=str(STAGE2_CHECKPOINT))
    parser.add_argument("--dry-run", action="store_true",
                        help="Report candidates without writing or calling the LLM")
    parser.add_argument("--limit", type=int, default=None,
                        help="Re-judge only the first N candidates (for testing)")
    parser.add_argument("--single-source-only", action="store_true",
                        help="Only reconsider single-source (non-convergent) records")
    parser.add_argument("--types", default=None,
                        help="Comma-separated extraction_type values to reconsider (default: all)")
    args = parser.parse_args()
    types: frozenset[str] | None = None
    if args.types:
        vals = {v.strip() for v in args.types.split(",") if v.strip()}
        bad = vals - set(EXTRACTION_TYPES)
        if bad:
            print(f"error: unknown extraction_type(s): {sorted(bad)}", file=sys.stderr)
            sys.exit(2)
        types = frozenset(vals)
    r = relabel(args.checkpoint, dry_run=args.dry_run, limit=args.limit,
                single_source_only=args.single_source_only, types=types)
    sys.exit(0 if r["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
