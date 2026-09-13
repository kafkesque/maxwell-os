#!/usr/bin/env python3
"""Bidirectional golden<->production sync (D2616 Phase 1, user-directed).

Two directions, both non-corrupting and provenance-tracked:

  DIRECTION A  production DB  <-  golden/p5 (discipline + domains)
      For each golden example whose source FB is in the production store,
      adopt the REVIEWED p5 discipline/domains when they differ from the
      production (gpt-oss silver) value. Golden SILVER is NOT written (it is
      the same teacher that already produced the production label -> no-op,
      never overwrites). Only the 209-row p5 master (claude/Qwen3.8/human
      reviewed) is authoritative enough to overwrite.

  DIRECTION B  golden  <-  298-human + joint_vote (depth + content_type)
      Emit a merged 4-axis golden dataset where each example's depth and
      content_type come from the strongest available source:
          depth:        298-human > joint_vote(DeepSeek+Qwen) > golden silver
          content_type: 298-human > joint_vote                > golden (often None)
      discipline/domains stay golden (p5 where reviewed). Written as a NEW
      file — the original stage4_golden_mined.yaml is never mutated.

Safety (mirrors apply_phase0_relabels.py):
  - C13: timestamped DB backup BEFORE any production write.
  - C6:  single transaction; rolls back on failure.
  - R14 manifest for the production write.
  - --check (default): dry-run, writes nothing.
  - --apply: back up + apply production write + write merged golden JSONL.

Outputs:
  governance/golden_synced_4axis.jsonl   (1,027 rows, 4 axes + provenance)
  governance/sync_golden_bidirectional_manifest.jsonl  (production writes, R14)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.io_guard import safe_write  # noqa: E402  C6 atomic write

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
P5 = ROOT / "temp" / "p5_adjudication_master.jsonl"
ADJ = ROOT / "governance" / "d2615_human_adjudication.jsonl"
JV = ROOT / "governance" / "joint_vote_production_checkpoint.jsonl"
OUT_MERGED = ROOT / "governance" / "golden_synced_4axis.jsonl"
MANIFEST = ROOT / "governance" / "sync_golden_bidirectional_manifest.jsonl"

SCHEMA_VERSION = "3.0"
GEN_MODEL = "python"  # deterministic merge; no generative model involved
PIPELINE_COMMIT = "v3.0-D2616-phase1"


def _load():
    golden = []
    g = yaml.safe_load(GOLDEN.open())
    for e in g["examples"]:
        m = re.search(r"[0-9a-f]{64}", str(e.get("rationale", "")))
        golden.append({
            "id": e["id"],
            "fb": m.group(0) if m else None,
            "name": e.get("input_fb", {}).get("name"),
            "depth": e.get("depth"),
            "content_type": e.get("content_type"),
            "discipline": (e.get("expected_classification") or {}).get("discipline"),
            "domains": (e.get("expected_classification") or {}).get("domains"),
        })

    p5 = {}
    for line in P5.open():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        p5[r["example_id"]] = r

    adj = {}
    for line in ADJ.open():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        adj[r["fb_id"]] = r

    jv = {}
    for line in JV.open():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        jv[r["fb_id"]] = r

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    fbs = {r["fb_id"]: dict(r) for r in conn.execute(
        "SELECT fb_id, discipline, domains, content_type, depth FROM fbs")}
    conn.close()

    return golden, p5, adj, jv, fbs


def _domains_set(x) -> frozenset:
    if x is None:
        return frozenset()
    if isinstance(x, str):
        try:
            x = json.loads(x)
        except Exception:
            return frozenset(d.strip() for d in x.split(",") if d.strip())
    if isinstance(x, list):
        return frozenset(str(d).strip() for d in x if str(d).strip())
    return frozenset()


def _plan_production(golden, p5, fbs):
    """DIRECTION A: production discipline/domains updates from p5 (reviewed only)."""
    changes = []
    for x in golden:
        fb = x["fb"]
        if not fb or fb not in fbs:
            continue
        pr = p5.get(x["id"])
        if not pr:
            continue
        prod = fbs[fb]
        nd = pr.get("final_discipline")
        ndom = pr.get("final_domains")
        if nd and nd != prod["discipline"]:
            changes.append({
                "fb_id": fb, "field": "discipline",
                "old": prod["discipline"], "new": nd,
                "golden_id": x["id"], "reviewer": pr.get("reviewer"),
            })
        if ndom and _domains_set(ndom) != _domains_set(prod["domains"]):
            changes.append({
                "fb_id": fb, "field": "domains",
                "old": prod["domains"], "new": sorted(ndom),
                "golden_id": x["id"], "reviewer": pr.get("reviewer"),
            })
    return changes


NON_PRINCIPLE = frozenset({
    "noise_drop", "process_template", "process_instance",
    "tool_instruction", "growth_edge", "quarantine",
})


def _merged_golden(golden, p5, adj, jv):
    """DIRECTION B: merged 4-axis golden with provenance.

    Order of authority (strongest first):
      content_type: 298-human > joint_vote (unanimous) > golden
      depth:        298-human > joint_vote           > golden silver
                    (depth is N/A when content_type is non-principle)
      discipline:   p5 (reviewed) > golden silver
      domains:      p5 (reviewed) > golden silver
    """
    out = []
    for x in golden:
        fb = x["fb"]
        # discipline/domains: p5 reviewed > golden silver
        disc = x["discipline"]; dsrc = "golden-silver"
        dom = x["domains"]; domsrc = "golden-silver"
        if x["id"] in p5:
            pr = p5[x["id"]]
            if pr.get("final_discipline"):
                disc = pr["final_discipline"]; dsrc = f"p5:{pr.get('reviewer')}"
            if pr.get("final_domains"):
                dom = pr["final_domains"]; domsrc = f"p5:{pr.get('reviewer')}"
        # content_type: 298-human > joint_vote (unanimous only) > golden
        ct = x["content_type"]; ctsrc = "golden" if ct else "none"
        if fb and fb in adj and adj[fb]["axis"] == "content_type":
            ct = adj[fb]["label"]; ctsrc = "298-human"
        elif fb and fb in jv and jv[fb].get("content_type") and jv[fb].get("content_type_agreed"):
            ct = jv[fb]["content_type"]; ctsrc = "joint-vote"
        # depth: N/A for non-principle, else 298-human > joint_vote > golden silver
        if ct in NON_PRINCIPLE:
            depth = None; dsrc2 = "n/a-non-principle"
        else:
            depth = x["depth"]; dsrc2 = "golden-silver"
            if fb and fb in adj and adj[fb]["axis"] == "depth":
                depth = adj[fb]["label"]; dsrc2 = "298-human"
            elif fb and fb in jv and jv[fb].get("depth"):
                depth = jv[fb]["depth"]; dsrc2 = "joint-vote"
        out.append({
            "id": x["id"], "fb_id": fb, "name": x["name"],
            "discipline": disc, "discipline_source": dsrc,
            "domains": dom, "domains_source": domsrc,
            "depth": depth, "depth_source": dsrc2,
            "content_type": ct, "content_type_source": ctsrc,
        })
    return out


def _apply_production(changes):
    bak = DB_PATH.with_name(
        f"maxwell.db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_golden_sync")
    shutil.copy2(DB_PATH, bak)
    print(f"  🔒 C13 backup: {bak}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        # group by fb to apply discipline+domains in one UPDATE per fb
        byfb = {}
        for c in changes:
            byfb.setdefault(c["fb_id"], {})[c["field"]] = c["new"]
        for fb, fields in byfb.items():
            if "discipline" in fields and "domains" in fields:
                conn.execute("UPDATE fbs SET discipline=?, domains=? WHERE fb_id=?",
                             (fields["discipline"], json.dumps(fields["domains"]), fb))
            elif "discipline" in fields:
                conn.execute("UPDATE fbs SET discipline=? WHERE fb_id=?",
                             (fields["discipline"], fb))
            elif "domains" in fields:
                conn.execute("UPDATE fbs SET domains=? WHERE fb_id=?",
                             (json.dumps(fields["domains"]), fb))
        conn.commit()
    except Exception as e:
        conn.rollback(); conn.close()
        print(f"❌ production apply failed, rolled back: {e}", file=sys.stderr)
        raise
    conn.close()

    now = datetime.now(timezone.utc).isoformat()
    lines = []
    for c in changes:
        rec = dict(c)
        rec.update({"schema_version": SCHEMA_VERSION, "gen_model": GEN_MODEL,
                    "pipeline_commit": PIPELINE_COMMIT, "created_at": now})
        lines.append(json.dumps(rec, ensure_ascii=False))
    safe_write(MANIFEST, "\n".join(lines) + "\n")

    conn = sqlite3.connect(DB_PATH)
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    print(f"  ✅ integrity_check: {ok}")


def main(argv):
    ap = argparse.ArgumentParser(description="golden<->production bidirectional sync (D2616)")
    ap.add_argument("--apply", action="store_true", help="back up + apply (default: dry-run)")
    args = ap.parse_args(argv)

    golden, p5, adj, jv, fbs = _load()
    prod_changes = _plan_production(golden, p5, fbs)
    merged = _merged_golden(golden, p5, adj, jv)

    print("🧭 golden<->production bidirectional sync (D2616 Phase 1)")
    print(f"   golden examples: {len(golden)}  |  p5 reviewed: {len(p5)}  |  298: {len(adj)}  |  joint-vote: {len(jv)}")
    print(f"\n   DIRECTION A (p5 discipline/domains -> production):")
    print(f"     production field updates: {len(prod_changes)}")
    print(f"       discipline: {sum(1 for c in prod_changes if c['field']=='discipline')}")
    print(f"       domains:    {sum(1 for c in prod_changes if c['field']=='domains')}")

    print(f"\n   DIRECTION B (merged 4-axis golden, sources):")
    for axis in ("depth", "content_type", "discipline", "domains"):
        c = Counter(m[f"{axis}_source"] for m in merged)
        print(f"       {axis:12s}: {dict(c)}")

    if not args.apply:
        print("\n   (dry-run) pass --apply to back up + write.")
        return 0

    if prod_changes:
        _apply_production(prod_changes)
        print(f"   ✅ applied {len(prod_changes)} production field updates. Manifest: {MANIFEST}")
    else:
        print("   ✅ no production field updates needed.")

    now = datetime.now(timezone.utc).isoformat()
    lines = []
    for m in merged:
        m = dict(m)
        m.update({"schema_version": SCHEMA_VERSION, "gen_model": GEN_MODEL,
                  "pipeline_commit": PIPELINE_COMMIT, "created_at": now})
        lines.append(json.dumps(m, ensure_ascii=False))
    safe_write(OUT_MERGED, "\n".join(lines) + "\n")
    print(f"   ✅ wrote merged 4-axis golden: {OUT_MERGED} ({len(merged)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
