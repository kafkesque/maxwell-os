#!/usr/bin/env python3
"""fix_singleton_48_posthoc.py — BUG-182/169 deterministic post-hoc sweep (2026-08-27).

Forensic follow-up to the D2479 targeted rerun. Re-running the same extractor at
temp=0.0 provably reproduces the same empty output, so the 48 residual empty-shell
singletons are repaired DETERMINISTICALLY (no LLM, no re-extraction):

  1. BUG-169  — stamp `parameter_origin` on every tool_instruction:
        parameters non-empty                → "api"
        parameters empty + syntax non-empty → "technique"  (code/DSL snippet,
                                                 formal params do not apply — D2471)
        parameters empty + syntax empty     → absent        (unresolved)
     This mirrors the builder-boundary derivation now in stage2_extract.py
     `_capture_type_specific_fields`, so the on-disk corpus matches what future
     batches emit. No more unpromoted `.fixed.jsonl` flag (the D2472 loss).

  2. BUG-182  — flag content-empty non-principle shells with `body_incomplete=true`
     (accept-and-flag per D2470 sidecar-first): empty-steps process_template,
     empty-actors process_instance, and unresolved (no syntax) tool_instruction.
     These are NOT reclassified — the deterministic guards already did their job
     (all 11 empty PT carry step-language → genuinely-fragmented, keep PT).

  3. BUG-182  — quarantine 2 evidence-topic-MISMATCH tool_instructions whose
     evidence passage is about a different subject than the name/definition
     (BUG-160 relevance class). They are written to an external quarantine
     manifest (the established severe_evidence_quarantine.jsonl pattern) and left
     flagged in the corpus (R-D410: never delete pipeline output).

Crash-safe (tempfile → fsync → os.replace), idempotent, dry-run capable. R14
stamps are NOT re-stamped (repair, not re-generation). A timestamped backup copy
is written next to the canonical file before replace (C13).

Usage:
    python3 scripts/fix_singleton_48_posthoc.py --dry-run
    python3 scripts/fix_singleton_48_posthoc.py
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SINGLETON = "knowledge pipeline/stage2_extract/t11/singleton_fbs.jsonl"
QUARANTINE_MANIFEST = "temp/evidence_mismatch_quarantine.jsonl"

# BUG-182 forensic findings (2026-08-27): the 2 evidence-topic-MISMATCH TIs.
# The evidence_passages[0] of each is about a different subject than the
# name/definition (verified record-by-record), so the extraction is unreliable.
_QUARANTINE: dict[str, str] = {
    "864472a9c2db49f0a030ab23a0e1a481f29a87a646b3790f73b1a1dacf6f9a68": "evidence about Monster.com job-search recruiting; name/definition claim SPSS scale-entry",
    "a49ae885654d94d0a31207410361b70311c622b46f8307ebd8950cffec87c487": "evidence about RGBA pixel→3D-point transform; name/definition claim openFrameworks folder/file structure",
}


def load_jsonl_any(path: str) -> list[dict]:
    """Load JSONL that may be compact or pretty-printed (multi-line objects)."""
    text = Path(path).read_text(encoding="utf-8")
    dec = json.JSONDecoder()
    recs: list[dict] = []
    idx = 0
    n = len(text)
    while idx < n:
        while idx < n and text[idx] in " \n\r\t,":
            idx += 1
        if idx >= n:
            break
        obj, end = dec.raw_decode(text, idx)
        recs.append(obj)
        idx = end
    return recs


def _empty(v) -> bool:
    return v is None or (isinstance(v, (list, str, dict)) and len(v) == 0)


def _derive_parameter_origin(rec: dict) -> str | None:
    """Mirror stage2_extract._capture_type_specific_fields (BUG-169)."""
    if rec.get("content_type") != "tool_instruction":
        return None
    if rec.get("parameters"):
        return "api"
    if rec.get("syntax"):
        return "technique"
    return None


def _empty_shell(rec: dict) -> bool:
    ct = rec.get("content_type")
    if ct == "process_template":
        return not (rec.get("steps") or rec.get("trigger") or rec.get("prerequisite")
                    or rec.get("done_condition") or rec.get("failure_mode"))
    if ct == "process_instance":
        return not (rec.get("instance_text") or rec.get("actors")
                    or rec.get("outcome_metric") or rec.get("outcome_qualitative"))
    if ct == "tool_instruction":
        # "unresolved" TI = no parameters AND no syntax (not the technique class)
        return not (rec.get("parameters") or rec.get("syntax"))
    if ct == "growth_edge":
        return not (rec.get("body") or rec.get("category")
                    or rec.get("actionable") or rec.get("status") or rec.get("priority"))
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--input", default=SINGLETON)
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"❌ {src} not found", file=sys.stderr)
        return 2

    records = load_jsonl_any(str(src))

    stamped_api = 0
    stamped_technique = 0
    unresolved_ti = 0
    flagged_incomplete = 0
    quarantined = 0

    for rec in records:
        # 1. BUG-169: parameter_origin stamp (mirrors builder derivation)
        if rec.get("content_type") == "tool_instruction":
            po = _derive_parameter_origin(rec)
            if po == "api":
                stamped_api += 1
                rec["parameter_origin"] = "api"
            elif po == "technique":
                stamped_technique += 1
                rec["parameter_origin"] = "technique"
            else:
                unresolved_ti += 1
                rec.pop("parameter_origin", None)  # absent = unresolved

        # 2. BUG-182: flag content-empty non-principle shells (accept-and-flag)
        if _empty_shell(rec) and rec.get("content_type") in (
                "process_template", "process_instance", "tool_instruction",
                "growth_edge"):
            rec["body_incomplete"] = True
            flagged_incomplete += 1

    # 3. BUG-182: quarantine the 2 evidence-mismatch TIs (external manifest)
    quarantine_out: list[dict] = []
    for rec in records:
        if rec.get("fb_id") in _QUARANTINE:
            quarantined += 1
            rec["evidence_quarantine"] = True
            rec["quarantine_reason"] = _QUARANTINE[rec["fb_id"]]
            quarantine_out.append({
                "fb_id": rec["fb_id"],
                "name": rec.get("name", ""),
                "content_type": rec.get("content_type", ""),
                "reason": _QUARANTINE[rec["fb_id"]],
                "evidence_head": (rec.get("evidence_passages") or [""])[0][:200],
            })

    print("Records:", len(records))
    print("  BUG-169 parameter_origin=api:      ", stamped_api)
    print("  BUG-169 parameter_origin=technique:", stamped_technique)
    print("  BUG-169 unresolved TI (absent):    ", unresolved_ti)
    print("  BUG-182 body_incomplete flagged:   ", flagged_incomplete)
    print("  BUG-182 evidence-mismatch quarantined:", quarantined)

    if args.dry_run:
        print("DRY-RUN — no write.")
        return 0

    # Backup first (C13), then crash-safe in-place write (C6).
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = src.with_name(src.name + f".pre_fix48_{ts}")
    shutil.copy2(src, backup)

    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    fd, tmp = tempfile.mkstemp(dir=src.parent, prefix=src.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, src)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    # Quarantine manifest (compact JSONL, crash-safe)
    if quarantine_out:
        qp = Path(QUARANTINE_MANIFEST)
        qcontent = "\n".join(json.dumps(q, ensure_ascii=False) for q in quarantine_out) + "\n"
        qfd, qtmp = tempfile.mkstemp(dir=qp.parent, prefix=qp.name + ".", suffix=".tmp")
        try:
            with os.fdopen(qfd, "w", encoding="utf-8") as f:
                f.write(qcontent)
                f.flush()
                os.fsync(f.fileno())
            os.replace(qtmp, qp)
        except BaseException:
            try:
                os.unlink(qtmp)
            except OSError:
                pass
            raise

    print(f"WROTE {src}  (backup: {backup.name})")
    if quarantine_out:
        print(f"WROTE {QUARANTINE_MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
