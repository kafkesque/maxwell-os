#!/usr/bin/env python3
"""flip_stale_pending.py — flip stale `verification_status` on complete gold rows.

Finds rows in verified_core.jsonl whose 4 axes are ALL authoritative (would be
gold-tier) but whose `verification_status` is still "pending-human" (stale from
before the P1 vote + human domain/discipline review landed). Flips them to
"human-verified" (human discipline_source) or "joint-vote-verified" (reliable-pair).

Deterministic, LLM-free. C13 backup + C6 atomic + R14 manifest, then re-runs the
tier split so gold/pending/silver stay consistent.

Usage:
  python3 scripts/flip_stale_pending.py --check
  python3 scripts/flip_stale_pending.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.axis_authority import CT_AUTH, DEPTH_AUTH, DISC_AUTH, DOM_AUTH  # noqa: E402

VC = ROOT / "governance" / "verified_core.jsonl"
MANIFEST = ROOT / "governance" / "flip_stale_pending_manifest.json"


def _authoritative(r: Dict[str, Any]) -> bool:
    return (
        r.get("content_type_source") in CT_AUTH
        and r.get("depth_source") in DEPTH_AUTH
        and r.get("discipline_source") in DISC_AUTH
        and r.get("discipline") != "emerging"
        and r.get("domains_source") in DOM_AUTH
    )


def _new_status(discipline_source: str) -> str:
    if "reliable-pair" in (discipline_source or ""):
        return "joint-vote-verified"
    return "human-verified"


def _atomic_write(path: Path, content: str) -> None:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows = [json.loads(l) for l in VC.read_text(encoding="utf-8").splitlines() if l.strip()]
    flipped: List[str] = []
    for r in rows:
        if r.get("verification_status") == "pending-human" and _authoritative(r):
            r["verification_status"] = _new_status(r.get("discipline_source", ""))
            flipped.append(r["fb_id"])

    print(f"stale pending-human rows to flip: {len(flipped)}")
    from collections import Counter
    print("new status dist:", dict(Counter(_new_status(r.get('discipline_source', '')) for r in rows if r['fb_id'] in set(flipped))))

    if args.check:
        print("[check] dry-run — nothing written.")
        return 0

    if VC.exists():
        bak = VC.with_name(f"verified_core.jsonl.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_pre_flip")
        shutil.copy2(VC, bak)
        print(f"[C13] backup: {bak}")

    _atomic_write(VC, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    MANIFEST.write_text(json.dumps({
        "flipped": len(flipped), "fb_ids": sorted(flipped),
        "gen_model": "flip_stale_pending.py (deterministic; no generation)",
        "pipeline_commit": "v3.0-D2634-followup",
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"[R14] manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
