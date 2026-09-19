#!/usr/bin/env python3
"""Merge all human 4-axis adjudication sources into verified_core.jsonl (D2618 P1 + D2619).

Deterministic, LLM-free (C12/C16). Writes verified_core.jsonl with C13 backup + R14
manifest, emits the 108 d2615-principle rows as a SEPARATE expansion queue (never
folded into the frozen 216 anchor), applies the user-locked discipline rulings as
final overrides, then re-runs the tier split.

Precedence per axis (most-human-authoritative wins):
    content_type:  frontier69 > p5 > d2615 > existing {human, joint-vote, 298-human}
    depth:         frontier69 > d2615 > existing {human, joint-vote, 298-human, n/a}
    discipline:    locked-ruling > P1-human > P1-reliable-pair > frontier69 > p5 > existing
    domains:       P1-human > frontier69 > p5 > existing

D2619 anchor rule: content_type "principle" is ONLY assigned to rows already in the
216-anchor (content_type == "principle"). Rows that d2615 labels "principle" but that
are NOT already principle are emitted to the expansion queue (content_type re-verify
first; a ~10% sample shows methods/case-studies mislabeled principle).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.axis_authority import (  # noqa: E402  (D2626: single source of truth)
    CT_ORIG,
    DP_ORIG,
    DISC_ORIG,
    DOM_ORIG,
    CT_FILL,
    DP_FILL,
    DISC_FILL,
    DOM_FILL,
)

GOV = Path("governance")
VC = GOV / "verified_core.jsonl"
D2615 = GOV / "d2615_human_adjudication.jsonl"
F69 = GOV / "frontier69_final_adjudication.json"
P5 = GOV / "p5_adjudication_final.json"
DISC_V = GOV / "s4_discipline_verdicts.jsonl"
DOM_V = GOV / "s4_domain_verdicts.jsonl"
VOTE = GOV / "discipline_domain_vote_checkpoint.jsonl"
LOCKED = GOV / "locked_discipline_rulings.jsonl"
QUEUE = GOV / "expansion_queue_108.jsonl"
MANIFEST = GOV / "merge_4axis_adjudication_manifest.json"

SCHEMA = "3.0"
GEN_MODEL = "merge_4axis_adjudication.py (deterministic; no generation)"
COMMIT = "v3.0-D2619-anchor"

# ── Authoritative source sets ───────────────────────────────────────────────
# "Spotless" = a source in the post-merge authoritative set. Used both as the
# don't-overwrite guard (idempotent) and the final spotless check.
# D2626: imported from pipeline.axis_authority (single source of truth — no drift).

# Post-merge spotless sets (authoritative):
CT_SPOT = CT_ORIG | CT_FILL
DP_SPOT = DP_ORIG | DP_FILL
DISC_SPOT = DISC_ORIG | DISC_FILL
DOM_SPOT = DOM_ORIG | DOM_FILL

# Non-principle content_type labels that d2615 may legitimately assign to a
# currently-unclassified (None) row:
NON_PRINCIPLE_CT = frozenset({
    "quarantine", "process_instance", "growth_edge", "process_template",
    "tool_instruction", "noise_drop",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(p: Path) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text())


def _atomic_write(path: Path, content: str) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _set_axis(r: Dict[str, Any], axis: str, label: Any, src: str) -> bool:
    """Set an axis label + provenance, returning True if a change occurred."""
    key = axis if axis in ("content_type", "depth", "discipline", "domains") else None
    if key is None:
        raise ValueError(f"unknown axis: {axis}")
    if r.get(key) != label or r.get(f"{key}_source") != src:
        r[key] = label
        r[f"{key}_source"] = src
        return True
    return False


def build(apply: bool) -> None:
    vc = _load_jsonl(VC)
    d2615 = _load_jsonl(D2615)
    f69 = _load_json(F69)
    p5 = _load_json(P5)
    dv = {r["out_id"]: r for r in _load_jsonl(DISC_V)}
    dov = {r["out_id"]: r for r in _load_jsonl(DOM_V)}
    ck = {r["fb_id"]: r for r in _load_jsonl(VOTE) if r.get("fb_id")}
    locked = _load_jsonl(LOCKED)

    fb2ex = {r["fb_id"]: r.get("example_id") for r in vc}
    d2: Dict[str, Dict[str, str]] = {}
    for x in d2615:
        d2.setdefault(x["fb_id"], {})[x["axis"]] = x["label"]

    changed: Dict[str, List[str]] = {}
    queue: List[Dict[str, Any]] = []

    def fill(r: Dict[str, Any], axis: str, label: Any, src: str) -> None:
        if _set_axis(r, axis, label, src):
            changed.setdefault(r["fb_id"], []).append(axis)

    for r in vc:
        fb = r["fb_id"]
        ex = fb2ex.get(fb)
        f = f69.get(ex) if ex else None

        # ---- content_type (D2619: never promote a non-principle row to principle)
        if r.get("content_type_source") not in CT_SPOT:
            incoming: Optional[str] = None
            src: Optional[str] = None
            if f and f.get("content_type"):
                incoming, src = f["content_type"], "p5:human-frontier69"
            elif ex and ex in p5.get("content_type", {}):
                incoming, src = p5["content_type"][ex], "p5:human"
            elif d2.get(fb, {}).get("content_type"):
                incoming, src = d2[fb]["content_type"], "p5:human-d2615"

            if incoming is not None:
                if r.get("content_type") == "principle" or incoming in NON_PRINCIPLE_CT:
                    fill(r, "content_type", incoming, src)
                elif incoming == "principle":
                    # d2615 says principle, but this row is not in the 216 anchor
                    # → expansion queue (content_type re-verify later).
                    queue.append(dict(r))
                    queue[-1]["d2615_content_type"] = incoming

        # ---- depth
        if r.get("depth_source") not in DP_SPOT:
            if f and f.get("final_depth"):
                fill(r, "depth", f["final_depth"], "p5:human-frontier69")
            elif d2.get(fb, {}).get("depth"):
                fill(r, "depth", d2[fb]["depth"], "p5:human-d2615")

        # ---- discipline
        if r.get("discipline_source") not in DISC_SPOT:
            if fb in dv:
                st = dv[fb]["discipline_status"]
                if st == "human-adjudicated":
                    fill(r, "discipline", dv[fb]["discipline"], "p5:human-D2618p1")
                elif st == "emerging-taxonomy-gap":
                    fill(r, "discipline", "emerging", "p5:human-emerging-gap")
            elif fb in ck and ck[fb].get("discipline_agreed") is True:
                fill(r, "discipline", ck[fb].get("discipline"), "p5:reliable-pair-D2618p1")
            elif f and f.get("final_discipline"):
                fill(r, "discipline", f["final_discipline"], "p5:human-frontier69")
            elif ex and ex in p5.get("discipline", {}):
                fill(r, "discipline", p5["discipline"][ex], "p5:human")

        # ---- domains
        if r.get("domains_source") not in DOM_SPOT:
            if fb in dov:
                fill(r, "domains", dov[fb]["domains"], "p5:human-D2618p1")
            elif f and f.get("final_domains"):
                fill(r, "domains", f["final_domains"], "p5:human-frontier69")
            elif ex and ex in p5.get("domains", {}):
                fill(r, "domains", p5["domains"][ex], "p5:human")

    # ---- locked rulings (final override) -----------------------------------
    locked_overrides: List[str] = []
    for ruling in locked:
        r = next((x for x in vc if x["fb_id"] == ruling["fb_id"]), None)
        if r is None:
            print(f"[warn] locked ruling fb_id not in verified_core: {ruling['fb_id']}")
            continue
        if ruling.get("merge_into"):
            r["duplicate_of"] = ruling["merge_into"]
            changed.setdefault(r["fb_id"], []).append("duplicate_of")
        elif ruling.get("discipline"):
            _set_axis(r, "discipline", ruling["discipline"], "p5:human-locked")
            changed.setdefault(r["fb_id"], []).append("discipline")
            locked_overrides.append(f"  {r.get('name','')[:48]:50} -> discipline={ruling['discipline']}")
        elif ruling.get("depth"):
            _set_axis(r, "depth", ruling["depth"], "p5:human-locked")
            changed.setdefault(r["fb_id"], []).append("depth")
            locked_overrides.append(f"  {r.get('name','')[:48]:50} -> depth={ruling['depth']}")

    # ---- D2620 fail-closed: no discipline<->domain contamination may be written
    from pipeline.schemas import validate_discipline_domain

    contaminated = []
    for r in vc:
        flags = validate_discipline_domain(r.get("discipline"), r.get("domains"))
        if flags:
            contaminated.append((r["fb_id"], r.get("name"), flags))
    if contaminated:
        for fb, nm, fl in contaminated:
            print(f"[D2620 CONTAMINATION] {str(nm)[:50]:52} {fl}")
        raise RuntimeError(
            f"D2620 guard: {len(contaminated)} rows have discipline<->domain "
            "contamination — refusing to write (fail-closed)"
        )

    # ---- stamp changed rows (R14) -------------------------------------------
    for r in vc:
        if r["fb_id"] in changed:
            r["schema_version"] = SCHEMA
            r["pipeline_commit"] = COMMIT
            r["merged_adjudication"] = True

    # ---- report -------------------------------------------------------------
    princ = [r for r in vc
             if r.get("content_type") == "principle" and not r.get("duplicate_of")]

    def spotless(r: Dict[str, Any]) -> bool:
        return (
            r.get("content_type_source") in CT_SPOT
            and r.get("depth_source") in DP_SPOT
            and r.get("discipline_source") in DISC_SPOT
            and r.get("domains_source") in DOM_SPOT
            and r.get("discipline") != "emerging"
            and not r.get("duplicate_of")
        )

    spot = [r for r in princ if spotless(r)]
    stragglers = [r for r in princ if not spotless(r)]

    print(f"verified_core rows: {len(vc)}")
    print(f"rows changed by merge: {len(changed)}")
    axis_totals: Dict[str, int] = {}
    for axes in changed.values():
        for a in axes:
            axis_totals[a] = axis_totals.get(a, 0) + 1
    print(f"per-axis changes: {axis_totals}")
    print(f"\nlocked discipline overrides applied: {len(locked_overrides)}")
    for s in locked_overrides:
        print(s)
    print(f"\nprinciple rows (non-duplicate): {len(princ)}")
    print(f"4-axis spotless (canonical, non-emerging): {len(spot)}")
    print(f"stragglers: {len(stragglers)}")
    for r in stragglers:
        miss = []
        if r.get("content_type_source") not in CT_SPOT:
            miss.append(f"ct={r.get('content_type_source')}")
        if r.get("depth_source") not in DP_SPOT:
            miss.append(f"depth={r.get('depth_source')}")
        if r.get("discipline_source") not in DISC_SPOT:
            miss.append(f"disc={r.get('discipline_source')}")
        if r.get("domains_source") not in DOM_SPOT:
            miss.append(f"dom={r.get('domains_source')}")
        if r.get("discipline") == "emerging":
            miss.append("disc=emerging")
        if r.get("duplicate_of"):
            miss.append("duplicate")
        print(f"   {str(r.get('name',''))[:46]:48} {', '.join(miss)}")
    print(f"\nexpansion queue (d2615-principle, not in 216 anchor): {len(queue)}")

    if not apply:
        print("\n[check] dry-run — nothing written. Re-run with --apply.")
        return

    # ---- C13 backup ---------------------------------------------------------
    if VC.exists():
        bak = VC.with_name(f"verified_core.jsonl.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_pre_merge")
        shutil.copy2(VC, bak)
        print(f"\n[C13] backup: {bak}")

    _atomic_write(VC, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in vc))
    if queue:
        _atomic_write(QUEUE, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in queue))
        print(f"[queue] wrote {len(queue)} rows -> {QUEUE}")

    MANIFEST.write_text(json.dumps({
        "schema_version": SCHEMA,
        "gen_model": GEN_MODEL,
        "pipeline_commit": COMMIT,
        "created_at": _now(),
        "input_sources": [str(p) for p in (VC, D2615, F69, P5, DISC_V, DOM_V, VOTE, LOCKED)],
        "rows_changed": len(changed),
        "per_axis_changes": axis_totals,
        "locked_overrides": len(locked_overrides),
        "spotless_principle": len(spot),
        "straggler_fb_ids": [r["fb_id"] for r in stragglers],
        "expansion_queue_rows": len(queue),
        "expansion_queue_fb_ids": [r["fb_id"] for r in queue],
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"[R14] manifest: {MANIFEST}")
    print("[done] verified_core.jsonl merged + stamped")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Merge all human 4-axis adjudication into verified_core.jsonl (D2618 P1 + D2619).")
    ap.add_argument("--apply", action="store_true", help="write verified_core.jsonl (C13 backup) + queue + manifest")
    args = ap.parse_args()
    build(apply=args.apply)
