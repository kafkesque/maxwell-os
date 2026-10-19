#!/usr/bin/env python3
"""apply_gold_reattach.py — apply the owner-adjudicated D-3106/D-3107 re-attachment (Option A).

Reads the PROPOSED semantic re-attachment map (governance/gold_reattach_map.jsonl — one-to-one, injective
after the D-3107 uniqueness pass in build_anchor_reattach_map.py), the delta adjudication
(governance/gold_reattach_adjudication.jsonl — owner "Option A" for low-confidence anchors), and writes the
result into the golden anchor (governance/gold_4axis.jsonl):

  * every anchor gains `invariant_key = sha256(normalized name)` — the D-3107 generation-invariant identity;
  * map anchors gain `live_fb_id` + `reattach_tier` + `reattach_similarity` (semantic re-attachment);
  * low-confidence delta anchors gain `disposition: dead` + `dead_reason` (owner Option A);
  * many-to-one delta anchors gain `reattach_pending: "many-to-one"` — they are NOT attached here (BUG-946:
    refuse, not record). The owner adjudicates each SAME/DIFFERENT via
    gold_reattach_many_to_one_ADJUDICATION.csv + resolve_merge_adjudication.py.

FAIL-CLOSED (D-3106 / BUG-946 root cause): refuses to write when
  (1) map + delta do not partition the anchors exactly,
  (2) the map is NOT one-to-one (a live_fb_id claimed by 2+ anchors) — a non-injective map means the
      uniqueness pass did not run, so the many-to-one would be silently merged instead of surfaced,
  (3) a low-confidence delta anchor has no Option-A adjudication (or an adjudication has no such anchor),
  (4) a live_fb_id is absent from the runtime KB.

Atomic write (tempfile -> fsync -> os.replace, C6). Deterministic and re-runnable: it always recomputes
from map+delta+adjudication, never from an already-augmented gold file.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "governance" / "gold_4axis.jsonl"
MAP = REPO / "governance" / "gold_reattach_map.jsonl"
DELTA = REPO / "governance" / "gold_reattach_delta.jsonl"
ADJUD = REPO / "governance" / "gold_reattach_adjudication.jsonl"
DB = REPO / "knowledge pipeline" / "maxwell.db"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        print(f"FAIL missing input: {path}", file=sys.stderr)
        sys.exit(2)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm_name(name: object) -> str:
    """Normalize a concept name the same way build_anchor_reattach_map.py does (case-fold + whitespace)."""
    return " ".join(str(name).lower().split())


def invariant_key(name: object) -> str:
    """D-3107 generation-invariant identity: sha256 of the normalized name (stable across generations)."""
    return hashlib.sha256(norm_name(name).encode("utf-8")).hexdigest()


def main() -> int:
    gold = load_jsonl(GOLD)
    re_map = load_jsonl(MAP)
    delta = load_jsonl(DELTA)
    adjud = load_jsonl(ADJUD)

    # (1) exact partition of the anchors by map + delta.
    gold_ids = {r["fb_id"] for r in gold}
    map_ids = {r["old_fb_id"] for r in re_map}
    delta_ids = {r["old_fb_id"] for r in delta}
    if len(gold_ids) != len(gold):
        print("FAIL: duplicate fb_id inside gold_4axis.jsonl", file=sys.stderr)
        return 2
    if map_ids & delta_ids:
        print(f"FAIL: {len(map_ids & delta_ids)} old_fb_id(s) appear in BOTH map and delta", file=sys.stderr)
        return 2
    if gold_ids != (map_ids | delta_ids):
        missing = sorted(gold_ids - (map_ids | delta_ids))
        extra = sorted((map_ids | delta_ids) - gold_ids)
        print(f"FAIL: map+delta do not partition the {len(gold_ids)} anchors — "
              f"missing {len(missing)} ({missing[:5]}...), extra {len(extra)} ({extra[:5]}...)",
              file=sys.stderr)
        return 2

    # (2) the PROPOSED map MUST be one-to-one (BUG-946 root cause). A live_fb_id claimed by 2+ anchors is a
    # many-to-one that the uniqueness pass failed to demote — refuse rather than silently merge distinct ideas.
    by_live: dict[str, int] = {}
    for r in re_map:
        by_live[r["live_fb_id"]] = by_live.get(r["live_fb_id"], 0) + 1
    mult = {lid: n for lid, n in by_live.items() if n > 1}
    if mult:
        print(f"FAIL: map is NOT one-to-one — {len(mult)} live_fb_id(s) claimed by 2+ anchors "
              f"(e.g. {sorted(mult.items())[:3]}). Re-run build_anchor_reattach_map.py "
              f"(one-to-one uniqueness pass) first.", file=sys.stderr)
        return 2

    # (3) every LOW-confidence delta anchor is Option-A adjudicated; many-to-one delta anchors are NOT
    # Option-A — they are adjudicated separately by the owner's SAME/DIFFERENT CSV.
    delta_by_id = {r["old_fb_id"]: r for r in delta}
    low_delta = {oid for oid, r in delta_by_id.items() if r.get("tier") != "many-to-one"}
    many_delta = {oid for oid, r in delta_by_id.items() if r.get("tier") == "many-to-one"}
    adjud_ids = {r["old_fb_id"] for r in adjud}
    if adjud_ids != low_delta:
        print(f"FAIL: Option-A adjudication does not cover the low-confidence delta exactly — "
              f"low-delta {len(low_delta)} vs adjudicated {len(adjud_ids)} "
              f"(many-to-one delta {len(many_delta)} is adjudicated via the CSV flow)", file=sys.stderr)
        return 2
    adjud_by_id = {r["old_fb_id"]: r for r in adjud}

    # (4) every map live_fb_id resolves in the runtime KB.
    con = sqlite3.connect(str(DB))
    live_ids = [r["live_fb_id"] for r in re_map]
    ph = ",".join("?" for _ in live_ids)
    present = {row[0] for row in con.execute(f"select fb_id from fbs where fb_id in ({ph})", live_ids)}
    con.close()
    absent = [lid for lid in live_ids if lid not in present]
    if absent:
        print(f"FAIL: {len(absent)} live_fb_id(s) absent from runtime KB "
              f"(e.g. {absent[:3]}) — refuse", file=sys.stderr)
        return 2

    reattach_by_id = {r["old_fb_id"]: r for r in re_map}
    out: list[dict] = []
    invariant_collisions: dict[str, list[str]] = {}
    for row in gold:
        row = dict(row)
        row["invariant_key"] = invariant_key(row["name"])
        ikey = row["invariant_key"]
        invariant_collisions.setdefault(ikey, []).append(row["name"])
        oid = row["fb_id"]
        if oid in reattach_by_id:
            m = reattach_by_id[oid]
            row["live_fb_id"] = m["live_fb_id"]
            row["reattach_tier"] = m["tier"]
            row["reattach_similarity"] = m["similarity"]
            row.pop("reattach_pending", None)
        else:
            d = delta_by_id[oid]
            if d.get("tier") == "many-to-one":
                # Owner-adjudicated fusion candidate: NOT attached here (BUG-946 — refuse, not record).
                row["reattach_pending"] = "many-to-one"
                for k in ("live_fb_id", "reattach_tier", "reattach_similarity",
                          "disposition", "dead_reason"):
                    row.pop(k, None)
            else:
                a = adjud_by_id[oid]
                row["disposition"] = a["disposition"]
                row["dead_reason"] = a["dead_reason"]
                row.pop("reattach_pending", None)
        out.append(row)

    dupes = {k: v for k, v in invariant_collisions.items() if len(v) > 1}
    if dupes:
        print(f"NOTE: {len(dupes)} normalized-name collision(s) share an invariant_key "
              f"(e.g. {list(dupes.items())[:3]})", file=sys.stderr)

    fd, tmp = tempfile.mkstemp(dir=GOLD.parent, prefix=".gold_4axis.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for row in out:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, GOLD)
    except Exception:
        os.unlink(tmp)
        raise

    dead = sum(1 for r in out if r.get("disposition") == "dead")
    reattached = sum(1 for r in out if "live_fb_id" in r)
    pending = sum(1 for r in out if r.get("reattach_pending") == "many-to-one")
    print(f"applied: {len(out)} anchors -> {reattached} re-attached, {dead} dead, "
          f"{pending} many-to-one pending (owner CSV); invariant_key written to all {len(out)}; "
          f"wrote {GOLD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
