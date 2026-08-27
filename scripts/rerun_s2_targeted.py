#!/usr/bin/env python3
"""rerun_s2_targeted.py — identify + prepare a TARGETED S2 re-extraction (D2475/D2474).

Forensic audit (stress_test_s2_exhaustive) surfaced 451 records needing S2
re-extraction; post-hoc fixes (fix_s2_posthoc.py) resolved 191 of them, leaving
260 LLM-required records. This script enumerates those and (optionally) prepares
the resume paths so a subsequent `stage2_extract.py` run re-extracts ONLY those
records — not the whole corpus.

Target classes (260 hard-gap issues across 260 records — post-hoc fixes applied):
  1. 229 singleton empty-shell   — 70 PT empty-steps, 48 PI empty-actors,
                                   111 TI empty-parameters (in singleton_fbs.jsonl).
  2.  31 single-source stale     — missing parameters (is_convergent=False, TI).
  3.   0 convergent PT anomaly   — BUG-166 already post-hoc blanked.

Mechanism (reuses existing resume logic — no new LLM surface):
  * Singleton:  drop the `singleton_*` segids + FBs → `--only-singletons` resume
                re-extracts exactly those (D2453 resume).
  * Single-source/convergent:  drop the `cluster_*` segids + FBs → `--only-single-source`
                resume re-extracts exactly those (run_stage2 resume, D2154).

Safety (C6 + R-D410):
  * MUTATION IS OPT-IN via `--apply`. Default is `--manifest` (no writes).
  * Before mutating, each touched file is backed up to <file>.pre_rerun_<ts> via
    shutil.copy2 (never deletes pipeline output in place without a backup).
  * Writes use tempfile → fsync → os.replace (crash-safe).

Modes:
  --manifest PATH   (default) write the 260-record manifest JSONL, no mutation.
  --dry-run         print what WOULD be cleared, no mutation.
  --apply           clear segids + drop FBs (backs up first).
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

REPO_ROOT = Path(__file__).resolve().parent.parent
T11 = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11"

# D2478/D2479: target CANONICAL files only. The `.deduped`/`.final`/`.fixed`
# sibling variants are dead-ends — writing to them drifts canonical and the S2
# resume reads canonical (`checkpoint.jsonl` + `singleton_fbs.jsonl`), so a drop
# against a sibling would silently leave stale FBs and produce duplicates.
CONVERGENT_CKPT = T11 / "checkpoint.jsonl"
CONVERGENT_SEGIDS = T11 / "checkpoint.jsonl.segids"
SINGLETON_FBS = T11 / "singleton_fbs.jsonl"
SINGLETON_SEGIDS = T11 / "singleton.segids"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    try:
        return [json.loads(l) for l in raw.splitlines() if l.strip()]
    except json.JSONDecodeError:
        try:
            d = json.loads(raw)
            return d if isinstance(d, list) else [d]
        except json.JSONDecodeError:
            return []


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def _identify_singletons(recs: list[dict]) -> list[dict]:
    out = []
    for r in recs:
        ct = r.get("content_type")
        reason = None
        if ct == "process_template" and not (r.get("steps") or []):
            reason = "empty-steps"
        elif ct == "process_instance" and not (r.get("actors") or []):
            reason = "empty-actors"
        elif ct == "tool_instruction" and not (r.get("parameters") or []):
            reason = "empty-parameters"
        if reason:
            out.append({
                "kind": "singleton",
                "content_type": ct,
                "reason": reason,
                "cluster_id": r.get("source_cluster") or r.get("cluster_id") or r.get("fb_id"),
                "fb_id": r.get("fb_id"),
            })
    return out


def _identify_single_source(recs: list[dict]) -> list[dict]:
    out = []
    for r in recs:
        ct = r.get("content_type")
        if ct == "principle":
            continue
        if r.get("is_convergent"):
            continue  # convergent handled separately (_identify_convergent_pt)
        reasons = []
        if _nonempty(r.get("elaboration")):
            reasons.append("elaboration-nonempty")
        if ct == "process_instance" and "outcome_metric" not in r:
            reasons.append("missing-outcome_metric")
        if ct == "tool_instruction" and "parameters" not in r:
            reasons.append("missing-parameters")
        if reasons:
            out.append({
                "kind": "single_source",
                "content_type": ct,
                "reason": "+".join(reasons),
                "cluster_id": r.get("source_cluster") or r.get("cluster_id") or r.get("fb_id"),
                "fb_id": r.get("fb_id"),
            })
    return out


def _identify_convergent_pt(recs: list[dict]) -> list[dict]:
    # BUG-166: a convergent cluster that produced a process_template WITH non-empty
    # elaboration (elaboration is PRINCIPLE-ONLY). After the post-hoc elaboration
    # blank, it conforms — so only flag it if elaboration is still non-empty.
    return [
        {
            "kind": "convergent",
            "content_type": r.get("content_type"),
            "reason": "BUG-166-elaboration-nonempty",
            "cluster_id": r.get("source_cluster") or r.get("cluster_id") or r.get("fb_id"),
            "fb_id": r.get("fb_id"),
        }
        for r in recs
        if r.get("is_convergent") and r.get("content_type") == "process_template"
        and _nonempty(r.get("elaboration"))
    ]


def _identify() -> tuple[list[dict], list[dict], list[dict]]:
    sing = _identify_singletons(_load_jsonl(SINGLETON_FBS))
    conv_recs = _load_jsonl(CONVERGENT_CKPT)
    ss = _identify_single_source(conv_recs)
    conv_pt = _identify_convergent_pt(conv_recs)
    return sing, ss, conv_pt


def _write_manifest(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


def _backup(path: Path) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.pre_rerun_{ts}")
    shutil.copy2(path, bak)
    return bak


def _atomic_write(path: Path, content: str) -> None:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".tmp", delete=False, dir=str(path.parent))
    try:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def _apply(sing: list[dict], ss: list[dict], conv_pt: list[dict]) -> None:
    # ── Singleton path ──
    singleton_cids = {r["cluster_id"] for r in sing}
    if singleton_cids:
        if SINGLETON_FBS.exists():
            _backup(SINGLETON_FBS)
        if SINGLETON_SEGIDS.exists():
            _backup(SINGLETON_SEGIDS)
        fbs = [r for r in _load_jsonl(SINGLETON_FBS)
               if (r.get("source_cluster") or r.get("cluster_id") or r.get("fb_id")) not in singleton_cids]
        _atomic_write(SINGLETON_FBS,
                      "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fbs))
        if SINGLETON_SEGIDS.exists():
            segids = json.loads(SINGLETON_SEGIDS.read_text(encoding="utf-8"))
            segids = [s for s in segids if s not in singleton_cids]
            _atomic_write(SINGLETON_SEGIDS, json.dumps(segids))
        print(f"✅ Singleton: dropped {len(singleton_cids)} FBs + segids (→ {len(fbs)} remain)")

    # ── Single-source + convergent path ──
    ss_cids = {r["cluster_id"] for r in ss} | {r["cluster_id"] for r in conv_pt}
    if ss_cids:
        if CONVERGENT_CKPT.exists():
            _backup(CONVERGENT_CKPT)
        if CONVERGENT_SEGIDS.exists():
            _backup(CONVERGENT_SEGIDS)
        fbs = [r for r in _load_jsonl(CONVERGENT_CKPT)
               if (r.get("source_cluster") or r.get("cluster_id") or r.get("fb_id")) not in ss_cids]
        _atomic_write(CONVERGENT_CKPT,
                      "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fbs))
        if CONVERGENT_SEGIDS.exists():
            segids = json.loads(CONVERGENT_SEGIDS.read_text(encoding="utf-8"))
            segids = [s for s in segids if s not in ss_cids]
            _atomic_write(CONVERGENT_SEGIDS, json.dumps(segids))
        print(f"✅ Single-source/convergent: dropped {len(ss_cids)} FBs + segids (→ {len(fbs)} remain)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=T11 / "rerun_targets.jsonl",
                    help="manifest output path")
    ap.add_argument("--apply", action="store_true", help="clear segids + drop FBs (backs up first)")
    ap.add_argument("--dry-run", action="store_true", help="print what WOULD be cleared")
    args = ap.parse_args()

    sing, ss, conv_pt = _identify()
    records = sing + ss + conv_pt
    print(f"📊 Identified {len(records)} records for targeted S2 re-extraction:")
    print(f"   singleton empty-shell: {len(sing)}  (PT/PI/TI empty steps/actors/parameters)")
    print(f"   single-source stale:   {len(ss)}  (elaboration-nonempty + missing params/outcome_metric)")
    print(f"   convergent PT anomaly: {len(conv_pt)}  (BUG-166)")
    print()

    if args.dry_run:
        print("── WOULD CLEAR (segids + FBs) ──")
        for r in records:
            print(f"   {r['kind']:13s} {r['content_type']:18s} {r['cluster_id']:24s} {r['reason']}")
        return 0

    _write_manifest(records, args.manifest)
    print(f"📄 Manifest written: {args.manifest}")

    if args.apply:
        _apply(sing, ss, conv_pt)
        print("\n✅ Prepared. Now run (in order):")
        print("   just s2-singletons            # re-extract 229 singleton empty-shell (resume)")
        print("   just s2-single-source-rerun   # re-extract 222 single-source/convergent")
        print("\n⚠️  NOTE: s2-single-source-rerun uses --reset-single-source, which re-extracts")
        print("   ALL single-source clusters — use --only-single-source (resume) instead for the")
        print("   TARGETED 222:  MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-single-source")
    else:
        print("\n💡 To PREPARE the targeted rerun (clear segids + drop FBs), re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
