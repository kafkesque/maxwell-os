#!/usr/bin/env python3
"""resolve_merge_adjudication.py — apply the owner's 20-merge ruling (BUG-946) to gold_4axis.jsonl.

Authoritative sources (read, never re-inferred — D-3109/D-3034):
  1. governance/gold_reattach_many_to_one_ADJUDICATION.csv  — the OWNER's per-anchor SAME/DIFFERENT mark.
  2. governance/gold_reattach_many_to_one.jsonl             — the 20 many-to-one collisions (live + anchors).
  3. The owner's 2026-10-19 re-statement: the two pairs
       {Metaphorical Conceptualization From Cultural Traces, Metaphorical Cognitive Mapping}
       {Natural Pattern Recognition, Symbolic Pattern Recognition}
     are NEAR-SAME (slightly different category) -> keep BOTH; everything else is DIFFERENT.

Disposition policy (deterministic, LLM-free, fail-closed C16):
  * NEAR-SAME live row (Metaphorical Conceptualization / Gestalt Pattern Recognition): keep BOTH anchors
    (true convergence; the category nuance stays fail-closed-skipped for owner re-word, never force-merged).
  * Every other merge: honour the CSV mark per anchor —
        SAME     -> attach to the live row (writes live_fb_id; a no-op if already attached).
        DIFFERENT-> detach (disposition:dead, drop live_fb_id/reattach_* and any pending marker).
  This uses the OWNER's marks, NOT a similarity/discipline heuristic. A similarity heuristic reversed 6 of the
  owner's marks in the prior version (kept the anchor the owner called DIFFERENT, killed the one called SAME).

Writes on --apply: gold_4axis.jsonl (C6 atomic, C13 backup first) + governance/gold_reattach_merge_resolution.jsonl.
"""
from __future__ import annotations
import argparse, csv, json, os, shutil, tempfile, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "governance" / "gold_4axis.jsonl"
MERGES = REPO / "governance" / "gold_reattach_many_to_one.jsonl"
CSV = REPO / "governance" / "gold_reattach_many_to_one_ADJUDICATION.csv"
OUT = REPO / "governance" / "gold_reattach_merge_resolution.jsonl"
BACKUP = REPO / "backup" / "deletions"

# Owner 2026-10-19: these two LIVE rows are near-same merges -> keep both anchors.
NEAR = frozenset({"Metaphorical Conceptualization", "Gestalt Pattern Recognition"})


def norm(s: str) -> str:
    return " ".join(str(s).lower().split())


def load_csv_verdicts() -> dict[str, str]:
    """Map normalized old-idea name -> SAME|DIFFERENT from the owner's CSV (fail-closed on ambiguity)."""
    verdicts: dict[str, str] = {}
    with CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        name = norm(r["Old idea that got glued to it"])
        mark = str(r["Same idea?"]).strip().upper()
        if mark not in ("SAME", "DIFFERENT"):
            raise SystemExit(f"CSV mark not SAME/DIFFERENT: {r!r}")
        if name in verdicts and verdicts[name] != mark:
            raise SystemExit(f"CSV has conflicting marks for {name!r}: {verdicts[name]} vs {mark}")
        verdicts[name] = mark
    return verdicts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    verdicts = load_csv_verdicts()
    gold = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    merges = [json.loads(l) for l in MERGES.read_text(encoding="utf-8").splitlines() if l.strip()]

    dead: dict[str, tuple[str, str, str, object]] = {}   # old_fb_id -> (live_fb_id, live_name, anchor_name, sim)
    kept: dict[str, tuple[str, str, str, object]] = {}   # old_fb_id -> (live_fb_id, live_name, anchor_name, sim)
    near: dict[str, tuple[str, str, str, object]] = {}   # old_fb_id -> (live_fb_id, live_name, anchor_name, sim)

    for m in merges:
        live_name = m["live_name"]
        live_fb_id = m["live_fb_id"]
        for x in m["anchors"]:
            oid, nm = x["old_fb_id"], x["name"]
            sim = x.get("similarity")
            if live_name in NEAR:
                near[oid] = (live_fb_id, live_name, nm, sim)
                continue
            mark = verdicts.get(norm(nm))
            if mark is None:
                raise SystemExit(f"anchor {nm!r} has no CSV verdict — refusing to guess (fail-closed)")
            if mark == "SAME":
                kept[oid] = (live_fb_id, live_name, nm, sim)
            else:
                dead[oid] = (live_fb_id, live_name, nm, sim)

    n_total = len(gold)
    print(f"merges: {len(merges)}  anchors: {len(merges)*2}")
    print(f"NEAR-SAME kept: {len(near)} | SAME kept: {len(kept)} | DIFFERENT dead: {len(dead)}")
    print(f"total kept {len(near)+len(kept)} + dead {len(dead)} = {len(near)+len(kept)+len(dead)}")
    print("\n-- DIFFERENT -> dead --")
    for oid, (_lfid, lv, nm, _sim) in sorted(dead.items(), key=lambda t: t[1][1]):
        print(f"  DEAD  {nm[:52]:52} <- {lv[:34]}")
    print("\n-- SAME -> attach (no-op if already attached) --")
    for oid, (_lfid, lv, nm, _sim) in sorted(kept.items(), key=lambda t: t[1][1]):
        print(f"  KEEP  {nm[:52]:52} -> {lv[:34]}")
    print("\n-- NEAR-SAME -> attach both (category nuance owner-gated) --")
    for oid, (_lfid, lv, nm, _sim) in sorted(near.items(), key=lambda t: t[1][1]):
        print(f"  NEAR  {nm[:52]:52} -> {lv[:34]}")

    if not a.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return 0

    # C13 backup first.
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = BACKUP / stamp
    bdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GOLD, bdir / GOLD.name)

    # C6 atomic write.
    changed = 0
    for r in gold:
        oid = r.get("fb_id")
        if oid in dead:
            _lfid, lv, nm, _sim = dead[oid]
            r["disposition"] = "dead"
            r["dead_reason"] = (
                f"owner-adjudicated false many-to-one re-attachment (DIFFERENT): '{nm}' is a distinct idea "
                f"from live row '{lv}'"
            )
            for k in ("live_fb_id", "reattach_tier", "reattach_similarity",
                      "reattach_pending", "reattach_candidate_fb_id"):
                r.pop(k, None)
            changed += 1
        elif oid in kept or oid in near:
            lfid, lv, nm, sim = kept.get(oid) or near.get(oid)
            if "live_fb_id" not in r:
                # attach a SAME/NEAR-SAME anchor that apply left pending (BUG-946: owner attach, not silent merge)
                r["live_fb_id"] = lfid
                r["reattach_tier"] = "high"
                r["reattach_similarity"] = sim
                r.pop("reattach_pending", None)
                r.pop("reattach_candidate_fb_id", None)
                changed += 1
    fd, tmp = tempfile.mkstemp(dir=GOLD.parent, prefix=".gold4.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in gold:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, GOLD)

    records = (
        [{"verdict": "DEAD", "old_fb_id": o, "anchor_name": nm, "live_name": lv} for o, (lv, nm) in dead.items()]
        + [{"verdict": "SAME", "old_fb_id": o, "anchor_name": nm, "live_name": lv} for o, (lv, nm) in kept.items()]
        + [{"verdict": "NEAR-SAME", "old_fb_id": o, "anchor_name": nm, "live_name": lv} for o, (lv, nm) in near.items()]
    )
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records) + "\n", encoding="utf-8")

    print(f"\nC13 backup: {bdir / GOLD.name}")
    print(f"wrote {GOLD.name} ({changed} anchors updated: dead/attached) + {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
