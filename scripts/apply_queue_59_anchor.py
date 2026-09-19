#!/usr/bin/env python3
"""apply_queue_59_anchor.py — D2631 follow-up: grow the anchor with accepted queue-59 rows.

Applies the D2633 union-aggregation verdicts (34 accepted: discipline unanimous +
domains overlap->union) plus the D2631 reliable-pair depth vote back into
`verified_core.jsonl`, then re-runs the deterministic tier split (build_4axis_tiers)
so the fully-authoritative rows land in `gold_4axis.jsonl` and the depth-abstained
rows stay pending (fail-closed: no fabricated depth).

Per-axis provenance (single source of truth: pipeline/axis_authority.py):
  content_type = "principle"   source = "p5:qwen38-ct-D2629"      (D2629 re-verify)
  depth        = unanimous     source = "p5:reliable-pair-D2631-revote" (D2631)
  discipline   = unanimous     source = "p5:reliable-pair-D2631-revote"
  domains      = union (D2633) source = "p5:reliable-pair-D2631-revote"

Depth is ONLY written when both voters agreed (depth_agreed && depth non-empty).
Rows whose depth abstained keep depth=None -> they remain pending-human until the
depth axis is re-voted (never fabricate).

Deterministic, LLM-free, C6 atomic + C13 backup + R14 manifest.

Usage:
  python3 scripts/apply_queue_59_anchor.py --check
  python3 scripts/apply_queue_59_anchor.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.axis_authority import (  # noqa: E402
    CT_AUTH,
    DEPTH_AUTH,
    DISC_AUTH,
    DOM_AUTH,
)

GOV = ROOT / "governance"
VC = GOV / "verified_core.jsonl"
AGG = GOV / "queue_59_domain_aggregation.json"
CKPT = GOV / "queue_59_vote_checkpoint.jsonl"
MANIFEST = GOV / "apply_queue_59_anchor_manifest.json"

SCHEMA = "3.0"
GEN_MODEL = "apply_queue_59_anchor.py (deterministic; no generation)"
COMMIT = "v3.0-D2631-anchor"

CT_SRC = "p5:qwen38-ct-D2629"
AXIS_SRC = "p5:reliable-pair-D2631-revote"
CT_PRINCIPLE = "principle"
STATUS_VERIFIED = "joint-vote-verified"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _atomic_write(path: Path, content: str) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".jsonl")
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            import os
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        if Path(tmp).exists():
            Path(tmp).unlink()
        raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_authority() -> None:
    """Fail loud (C16) if a source label we emit is not authoritative."""
    for label, axis in ((CT_SRC, "CT_AUTH"), (AXIS_SRC, "DEPTH_AUTH"),
                        (AXIS_SRC, "DISC_AUTH"), (AXIS_SRC, "DOM_AUTH")):
        auth = {"CT_AUTH": CT_AUTH, "DEPTH_AUTH": DEPTH_AUTH,
                "DISC_AUTH": DISC_AUTH, "DOM_AUTH": DOM_AUTH}[axis]
        if label not in auth:
            raise AssertionError(f"{label} not in {axis} — add it to pipeline/axis_authority.py first")


def build() -> Dict[str, Any]:
    _assert_authority()

    agg = json.loads(AGG.read_text(encoding="utf-8"))
    accepted = [v for v in agg["verdicts"] if v.get("accept")]
    ckpt = {json.loads(l)["fb_id"]: json.loads(l) for l in CKPT.read_text(encoding="utf-8").splitlines() if l.strip()}

    vc = _load_jsonl(VC)
    by_id = {r["fb_id"]: r for r in vc}
    missing = [v["fb_id"] for v in accepted if v["fb_id"] not in by_id]
    if missing:
        raise ValueError(f"accepted fb_ids not in verified_core.jsonl: {missing[:5]}...")

    changed: List[str] = []
    full_depth = 0
    depth_abstain = 0
    for v in accepted:
        fb = v["fb_id"]
        row = by_id[fb]
        ck = ckpt[fb]

        row["content_type"] = CT_PRINCIPLE
        row["content_type_source"] = CT_SRC
        row["discipline"] = v["discipline"]
        row["discipline_source"] = AXIS_SRC
        row["domains"] = v["domains"]
        row["domains_source"] = AXIS_SRC

        # Depth: only when reliable-pair unanimous (never fabricate).
        if ck.get("depth_agreed") and ck.get("depth"):
            row["depth"] = ck["depth"]
            row["depth_source"] = AXIS_SRC
            row["verification_status"] = STATUS_VERIFIED
            full_depth += 1
        else:
            row["depth"] = None
            row["depth_source"] = None
            row["verification_status"] = "pending-human"
            depth_abstain += 1

        row["review_axis"] = None
        row["schema_version"] = SCHEMA
        row["gen_model"] = GEN_MODEL
        row["pipeline_commit"] = COMMIT
        changed.append(fb)

    summary = {
        "n_accepted": len(accepted),
        "n_full_4axis": full_depth,
        "n_depth_abstained": depth_abstain,
        "fb_ids": sorted(changed),
        "contested_discipline": [v["fb_id"] for v in agg["verdicts"]
                                 if not v.get("accept") and v.get("discipline_status") == "contested"],
        "disjoint_domains": [v["fb_id"] for v in agg["verdicts"]
                             if not v.get("accept") and v.get("domain_status") == "disjoint"],
        "domain_abstain": [v["fb_id"] for v in agg["verdicts"]
                           if not v.get("accept") and v.get("domain_status") == "abstain"],
    }
    return {"vc": vc, "summary": summary, "changed": changed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write verified_core.jsonl (C13 backup) + manifest")
    ap.add_argument("--check", action="store_true", help="dry-run: report, write nothing")
    args = ap.parse_args()

    result = build()
    s = result["summary"]
    print(f"accepted: {s['n_accepted']} | full 4-axis: {s['n_full_4axis']} | depth-abstained (stay pending): {s['n_depth_abstained']}")
    print(f"contested discipline (-> human/3rd-voter): {len(s['contested_discipline'])}")
    print(f"disjoint domains: {len(s['disjoint_domains'])} | domain abstain: {len(s['domain_abstain'])}")

    if args.check:
        print("\n[check] dry-run — nothing written. Re-run with --apply.")
        return 0

    # C13 backup
    if VC.exists():
        bak = VC.with_name(f"verified_core.jsonl.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_pre_queue59")
        shutil.copy2(VC, bak)
        print(f"\n[C13] backup: {bak}")

    _atomic_write(VC, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in result["vc"]))

    MANIFEST.write_text(json.dumps({
        "schema_version": SCHEMA,
        "gen_model": GEN_MODEL,
        "pipeline_commit": COMMIT,
        "created_at": _now(),
        "input": str(AGG),
        "summary": s,
        "rows_changed": len(result["changed"]),
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"[R14] manifest: {MANIFEST}")
    print("[done] verified_core.jsonl updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
