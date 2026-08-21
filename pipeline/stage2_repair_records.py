#!/usr/bin/env python3
"""Post-hoc repair of specific broken S2 records (P0-4 / BUG-158).

Fills MISSING type-specific body fields on records where the single-source
extraction produced a complete shared core_body but left the role-specific
fields empty, and fixes wrong extraction_type labels on tool_instruction
records (BUG-145/147 residual — procedural tools labelled causal_mechanism).

Grounding rule (same as the elaboration backfill): repairs derive ONLY from the
record's existing extracted fields (name/definition/mechanism/boundary/
consequence[/elaboration]) + evidence_passages. No re-extraction, no new factual
claims. No content_type/name/definition changes (fb_id stays stable).

Idempotent + resumable + crash-safe (safe_write → tempfile+fsync+os.replace).

Usage:
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_repair_records.py --checkpoint PATH
    python3 -u pipeline/stage2_repair_records.py --checkpoint PATH --dry-run
    python3 -u pipeline/stage2_repair_records.py --checkpoint PATH --limit 2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write
from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import GEN_MODEL, STAGE2_CHECKPOINT


SYSTEM_PROMPT: str = "You are a precise JSON generator. Return ONLY valid JSON. No markdown."

# ── Deterministic (no-LLM) label fixes: tool_instruction wrongly labelled ──
#    causal_mechanism → normative_heuristic (procedural how-to, not X→Y mechanism).
TI_RELABEL: dict[str, str] = {
    "4ee95da6258223a25d0fdaf79e38e2fe498ed5e0eb6df86fd7a040b5c0605090": "normative_heuristic",
    "cef07fb894cfcc466705399bb1800cbfb89f741d6929ea6e97e8956f053e7333": "normative_heuristic",
    "a1afbbc71b88fb65435ff9d1a4e8dd5a27261c0b0d4b47c1d687bb61079050a6": "normative_heuristic",
}

# ── LLM body-field repairs: (fb_id, list of field names to (re)fill). ─────
#    Field types: steps/actors are JSON string-arrays; actionable is bool; the
#    rest are strings. A field is only regenerated if currently empty.
LLM_REPAIRS: list[tuple[str, list[str]]] = [
    # PT Render Queue Workflow (convergent, old run) — all 5 body fields None
    ("189508a2c387d9a843f3e46483ed6e25439f66a65fe47f019c4cb5d1d6ada7c8",
     ["trigger", "prerequisite", "steps", "done_condition", "failure_mode"]),
    # PT Personal Business Model Methodology — all 5 body fields None
    ("2dfb15aa45764c6af692362b5b3a7ef4495f0c814dd3123263b81e93cf651621",
     ["trigger", "prerequisite", "steps", "done_condition", "failure_mode"]),
    # PT Pilot Memory Protocol — only prerequisite None
    ("40e03ac11b4072f863930b76c8bacf9791f02ff1c655defb32696f7cb6cb2b23",
     ["prerequisite"]),
    # PI A/B Test — all 5 PI body fields None
    ("8b4c49076f2e535f1e092f8996098a838dec92273012d77039d4ec80cfc36caf",
     ["instance_text", "actors", "outcome_metric", "outcome_qualitative", "domain_context"]),
    # GE Filostrato's Vision — all 5 GE body fields None
    ("f825a77a691babacabd403e436c505347e1c21693c3cdf62c4767898fcb8f968",
     ["body", "category", "actionable", "status", "priority"]),
]

_ARRAY_FIELDS: frozenset[str] = frozenset({"steps", "actors", "parameters"})
_BOOL_FIELDS: frozenset[str] = frozenset({"actionable"})


def _is_empty(val: object) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return not val.strip()
    if isinstance(val, (list, dict)):
        return len(val) == 0
    return False


def _build_prompt(rec: dict, fields: list[str]) -> str:
    """Build a grounded repair prompt for the missing fields."""
    type_hint: str = ""
    for f in fields:
        if f in _ARRAY_FIELDS:
            type_hint += f"- {f}: JSON array of strings\n"
        elif f in _BOOL_FIELDS:
            type_hint += f"- {f}: boolean (true/false)\n"
        else:
            type_hint += f"- {f}: string\n"
    return (
        f"This record (content_type={rec.get('content_type')}) is missing body fields. "
        f"Produce ONLY the following missing fields:\n{type_hint}"
        "Ground them strictly in the fields and evidence below; do NOT invent new facts, "
        "people, numbers, or sources. If evidence is genuinely silent on a field, use your "
        "best conservative inference from the provided fields and keep it short.\n"
        "Return JSON with exactly these keys.\n\n"
        f"name: {rec.get('name', '')}\n"
        f"definition: {rec.get('definition', '')}\n"
        f"mechanism: {rec.get('mechanism', '')}\n"
        f"boundary: {rec.get('boundary', '')}\n"
        f"consequence: {rec.get('consequence', '')}\n"
        f"elaboration: {rec.get('elaboration', '')}\n"
        f"evidence: {json.dumps(rec.get('evidence_passages', [])[:5], ensure_ascii=False)}\n"
    )


def _extract_fields(result: object, fields: list[str]) -> dict[str, object]:
    """Pull the requested fields from an LLM result (dict, possibly list-wrapped)."""
    out: dict[str, object] = {}
    obj: object = result
    if isinstance(result, list):
        if not result or not isinstance(result[0], dict):
            return out
        obj = result[0]
    if not isinstance(obj, dict):
        return out
    for f in fields:
        if f in obj:
            v = obj[f]
            if f in _ARRAY_FIELDS:
                if isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v):
                    out[f] = v
            elif f in _BOOL_FIELDS:
                if isinstance(v, bool):
                    out[f] = v
            else:
                if isinstance(v, str) and v.strip():
                    out[f] = v.strip()
    return out


def repair(checkpoint_path: str, dry_run: bool, limit: int | None) -> dict:
    checkpoint_path = str(Path(checkpoint_path))
    records = load_jsonl(checkpoint_path, context="repair checkpoint")
    by_id: dict[str, int] = {r["fb_id"]: i for i, r in enumerate(records)}

    # Phase 1: deterministic TI relabels
    relabeled: int = 0
    for fid, new_et in TI_RELABEL.items():
        if fid in by_id:
            rec = records[by_id[fid]]
            if rec.get("content_type") == "tool_instruction" and rec.get("extraction_type") == "causal_mechanism":
                if not dry_run:
                    rec["extraction_type"] = new_et
                relabeled += 1
    print(f"🏷️  TI relabels (causal_mechanism→normative_heuristic): {relabeled}")

    # Phase 2: LLM body-field repairs
    llm_jobs: list[tuple[str, list[str], int]] = []
    for fid, fields in LLM_REPAIRS:
        if fid in by_id:
            idx = by_id[fid]
            missing = [f for f in fields if _is_empty(records[idx].get(f))]
            if missing:
                llm_jobs.append((fid, missing, idx))
    print(f"🎯 LLM repairs: {len(llm_jobs)} record(s) needing {sum(len(j[1]) for j in llm_jobs)} field(s)")
    if limit is not None:
        llm_jobs = llm_jobs[:limit]

    filled: int = 0
    failed: int = 0
    for fid, missing, idx in llm_jobs:
        rec = records[idx]
        label = f"{rec.get('name', '?')[:40]}"
        if dry_run:
            print(f"   [dry-run] would fill {missing} on {label}")
            continue
        try:
            result = call_omlx_json(
                prompt=_build_prompt(rec, missing),
                model=GEN_MODEL,
                system=SYSTEM_PROMPT,
                max_tokens=1024,
            )
            got = _extract_fields(result, missing)
            for f, v in got.items():
                rec[f] = v
            filled += len(got)
            still = [f for f in missing if f not in got]
            if still:
                failed += 1
                print(f"   ⚠️  {fid[:12]} {label}: could not fill {still}", file=sys.stderr, flush=True)
            else:
                print(f"   ✅ {fid[:12]} {label}: filled {missing}")
        except Exception as e:
            failed += 1
            print(f"   ❌ {fid[:12]} {label}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)

    if not dry_run:
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        safe_write(checkpoint_path, content)
        load_jsonl(checkpoint_path, context="repair self-check")

    print(f"✅ Repair complete: relabeled {relabeled}, filled {filled} field(s), "
          f"failed {failed} record(s)")
    return {"relabeled": relabeled, "filled": filled, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default=str(STAGE2_CHECKPOINT))
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing or calling the LLM")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only repair the first N LLM records (for testing)")
    args = parser.parse_args()
    r = repair(args.checkpoint, args.dry_run, args.limit)
    sys.exit(0 if r["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
