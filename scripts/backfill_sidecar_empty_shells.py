#!/usr/bin/env python3
"""
backfill_sidecar_empty_shells.py — D2518 (BUG-181#2 / D2470 / D2474 residual)

Cross-examination backfill of the 25 non-principle sidecar "empty-shell" records
(10 PT / 5 PI / 6 GE / 4 TI) whose type-specific S2 body fields are empty
(`body_incomplete: true`). Per D2470/D2474 this is a CROSS-FAMILY single-field
fill via gemma (Generator != Verifier, R5), NOT a same-extractor rerun
(temp=0.0 would deterministically re-return empty — BUG-182).

Content-type body fields are read from config/content_types.yaml → `s2_body_fields`
(C12, single source of truth), NOT hardcoded. Only EMPTY type-specific fields are
filled; `elaboration`/`mechanism`/`boundary`/`consequence` are PRINCIPLE-ONLY
(D2475) and left untouched for PT/PI/GE/TI.

Safety (C6/C13/R-D410):
  * MUTATION IS OPT-IN via `--apply`; default is `--manifest` (read-only).
  * `--apply` backs up each sidecar file first (shutil.copy2 → timestamped).
  * Writes use tempfile → fsync → os.replace (crash-safe).
  * A gemma JSON-parse failure on any record aborts loudly (C16) — no partial fill.

Run:
  /usr/local/bin/python3 scripts/backfill_sidecar_empty_shells.py --manifest
  /usr/local/bin/python3 scripts/backfill_sidecar_empty_shells.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

T11 = REPO / "knowledge pipeline" / "stage4_merge" / "t11"
FILL_MODEL = "gemma-4-E4B-it-MLX-4bit"  # cross-family fill (R5)

SIDECARS = {
    "process_template": "process_templates.jsonl",
    "process_instance": "process_instances.jsonl",
    "growth_edge": "growth_edges.jsonl",
    "tool_instruction": "tool_instructions.jsonl",
}

# type-specific body fields that S2 must emit (read from content_types.yaml, C12)
def _s2_body_fields() -> dict[str, list[str]]:
    with open(REPO / "config" / "content_types.yaml") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("s2_body_fields", {})


S2_BODY_FIELDS = _s2_body_fields()


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _find_empty_shells() -> list[tuple[str, Path, dict]]:
    """Return [(content_type, file_path, record)] for every body_incomplete record."""
    found = []
    for ctype, fname in SIDECARS.items():
        path = T11 / fname
        if not path.exists():
            continue
        for rec in _load_jsonl(path):
            if rec.get("body_incomplete"):
                found.append((ctype, path, rec))
    return found


def _fill_record(ctype: str, rec: dict) -> dict:
    from pipeline.omlx_call import call_omlx_json  # local import: heavy deps

    fields = S2_BODY_FIELDS.get(ctype, [])
    missing = [f for f in fields if rec.get(f) in (None, "", [], {}, "None")]
    if not missing:
        return rec

    name = rec.get("name", "")
    definition = rec.get("definition", "")
    mechanism = rec.get("mechanism", "")
    consequence = rec.get("consequence", "")
    evidence = json.dumps(rec.get("evidence_passages", []), ensure_ascii=False)[:2000]

    prompt = (
        f"You are filling the missing type-specific body fields of a '{ctype}' knowledge object "
        f"that was extracted from source text but whose body came back empty.\n\n"
        f"content_type: {ctype}\n"
        f"name: {name}\n"
        f"definition: {definition}\n"
        f"mechanism: {mechanism}\n"
        f"consequence: {consequence}\n"
        f"evidence passages (verbatim source, ground all answers in these):\n{evidence}\n\n"
        f"Fill ONLY these missing fields (leave others alone): {json.dumps(missing)}\n\n"
        f"Field contracts (from content_types.yaml):\n"
        f"  steps      → JSON array of ordered step strings\n"
        f"  actors     → JSON array of actor/role strings\n"
        f"  parameters → JSON array of {{name, type, description}} objects\n"
        f"  all others → plain strings\n\n"
        f"Rules: ground every answer in the evidence passages (do NOT invent tool syntax or "
        f"steps not supported by the source). Be concrete and specific to THIS record. "
        f"Return ONLY a JSON object with exactly these keys: {json.dumps(missing)}"
    )

    result = call_omlx_json(
        prompt,
        model=FILL_MODEL,
        system="You are a precise cross-examination filler. Return ONLY valid JSON, no markdown.",
        max_tokens=1200,
        timeout=120,
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            f"C16: gemma fill for {rec.get('fb_id', '?')[:12]} ({ctype}) returned "
            f"non-dict {type(result).__name__} — aborting, no partial fill"
        )

    # Apply ONLY the fields we asked for; validate array-typed fields.
    for k in missing:
        v = result.get(k)
        if k in ("steps", "actors") and not isinstance(v, list):
            v = [v] if isinstance(v, str) and v.strip() else []
        if k == "parameters" and not isinstance(v, list):
            v = []
        rec[k] = v

    # Only clear the empty-shell flag when EVERY requested field is now non-empty.
    # (BUG-182 is a model-level extraction gap: some fields — e.g. a quantitative
    # outcome_metric, or tool syntax — are genuinely absent from the source text,
    # so gemma cannot fill them without hallucinating. Those stay body_incomplete.)
    still_empty = [k for k in missing if rec.get(k) in (None, "", [], {}, "None")]
    rec["body_filled_by"] = FILL_MODEL
    rec["body_filled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if still_empty:
        rec["body_incomplete"] = True
        rec["body_incomplete_reason"] = (
            f"cross-exam fill (gemma) left unfillable from source: {still_empty}"
        )
    else:
        rec["body_incomplete"] = False
    return rec


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """C6 crash-safe write: tempfile → fsync → os.replace."""
    import os

    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp_path = Path(tmp)
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill 25 non-principle sidecar empty-shells (D2518)")
    ap.add_argument("--manifest", action="store_true", help="list the empty-shell records (read-only)")
    ap.add_argument("--apply", action="store_true", help="fill via gemma + write back (backs up first)")
    args = ap.parse_args()

    shells = _find_empty_shells()
    print(f"📋 {len(shells)} empty-shell sidecar record(s) found:")
    for ctype, path, rec in shells:
        missing = [f for f in S2_BODY_FIELDS.get(ctype, []) if rec.get(f) in (None, "", [], {}, "None")]
        print(f"  [{ctype:<16}] {rec.get('fb_id', '?')[:12]}  {rec.get('name', '')[:40]:40}  missing={missing}")

    if args.manifest or not args.apply:
        return 0

    # Backup (C13) then fill per-file.
    ts = time.strftime("%Y%m%d_%H%M%S")
    by_file: dict[Path, list[dict]] = {}
    for ctype, path, rec in shells:
        by_file.setdefault(path, (ctype, []))[1].append(rec)

    for path, (ctype, recs) in by_file.items():
        backup = path.with_name(path.name + f".pre_shellfill_{ts}.bak")
        shutil.copy2(path, backup)
        print(f"\n💾 backed up {path.name} -> {backup.name}")

    updated: dict[Path, list[dict]] = {}
    for ctype, path, rec in shells:
        filled = _fill_record(ctype, rec)
        updated.setdefault(path, []).append(filled)
        print(f"  ✅ filled [{ctype}] {rec.get('fb_id', '')[:12]} {rec.get('name', '')[:40]}")

    for path, recs in updated.items():
        all_recs = _load_jsonl(path)
        by_id = {r["fb_id"]: r for r in recs}
        out = []
        for r in all_recs:
            out.append(by_id.get(r["fb_id"], r))
        _write_jsonl(path, out)
        print(f"  💾 wrote {len(out)} records -> {path.name} ({len(recs)} filled)")

    print("\n✅ sidecar empty-shell backfill complete (D2518).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
