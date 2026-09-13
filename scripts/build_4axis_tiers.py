#!/usr/bin/env python3
"""build_4axis_tiers.py — D2618 P0.1: split verified_core.jsonl into immutable tiers.

Splits the 443-row verified core into THREE provenance tiers that must never be
re-merged (GPT's contract-first authority model):

  - gold_4axis.jsonl    = all 4 axes authoritative (non-silver, non-None)
  - pending_4axis.jsonl = verification_status == pending-human (the 294 sample)
  - silver_4axis.jsonl  = human/joint-vote verified on ct+depth but >=1 axis still
                          golden-silver (or a non-authoritative ct source)

Authoritative per axis (fail-closed: anything ambiguous -> silver, never gold):
  - content_type: source in {human, joint-vote, 298-human}
  - depth:        source in {human, joint-vote, n/a-non-principle, 298-human}
  - discipline:   source is p5:* (NOT golden-silver, NOT None)
  - domains:      source is p5:* (NOT golden-silver, NOT None)

Also defensively normalizes the p5:* provenance typo variants (D2618 P0.2) on read:
  p5:claud+human / p5:claude+guman / p5:claude+juman  ->  p5:claude+human

Deterministic, LLM-free. C6 atomic writes, R14 stamps, C16 fail-loud.

Usage:
  python3 scripts/build_4axis_tiers.py            # build all 3 tiers + manifest
  python3 scripts/build_4axis_tiers.py --check    # dry-run: report counts, write nothing
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── C12/C20: named constants (no magic strings) ────────────────────────────
GOV_DIR = "governance"
IN_CORE = os.path.join(GOV_DIR, "verified_core.jsonl")
OUT_GOLD = os.path.join(GOV_DIR, "gold_4axis.jsonl")
OUT_PENDING = os.path.join(GOV_DIR, "pending_4axis.jsonl")
OUT_SILVER = os.path.join(GOV_DIR, "silver_4axis.jsonl")
OUT_MANIFEST = os.path.join(GOV_DIR, "tier_split_manifest.json")

SCHEMA_VERSION = "3.0"
GEN_MODEL = "build_4axis_tiers.py (deterministic; no generation)"
PIPELINE_COMMIT = "v3.0-D2618-p0"

STATUS_PENDING = "pending-human"

SILVER = "golden-silver"
CT_AUTH = frozenset({"human", "joint-vote", "298-human"})
DEPTH_AUTH = frozenset({"human", "joint-vote", "n/a-non-principle", "298-human"})

# D2618 P0.2: non-canonical provenance typos -> canonical p5:claude+human.
PROVENANCE_TYPOS: Dict[str, str] = {
    "p5:claud+human": "p5:claude+human",
    "p5:claude+guman": "p5:claude+human",
    "p5:claude+juman": "p5:claude+human",
}


def _norm(src: Optional[str]) -> Optional[str]:
    """Normalize a provenance string to its canonical form (P0.2)."""
    if src is None:
        return None
    return PROVENANCE_TYPOS.get(src, src)


def _discdom_authoritative(src: Optional[str]) -> bool:
    """True iff a discipline/domain source is non-silver and non-None."""
    s = _norm(src)
    return isinstance(s, str) and s != SILVER and s.startswith("p5:")


def _tier(row: Dict[str, Any]) -> str:
    """Classify one verified-core row into gold / pending / silver."""
    if row.get("verification_status") == STATUS_PENDING:
        return "pending"
    ct_ok = row.get("content_type_source") in CT_AUTH
    dp_ok = row.get("depth_source") in DEPTH_AUTH
    di_ok = _discdom_authoritative(row.get("discipline_source"))
    do_ok = _discdom_authoritative(row.get("domains_source"))
    return "gold" if (ct_ok and dp_ok and di_ok and do_ok) else "silver"


def _load(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp(row: Dict[str, Any], tier: str) -> Dict[str, Any]:
    """Attach R14 provenance stamp + tier marker to a tier row."""
    row["tier"] = tier
    row["schema_version"] = SCHEMA_VERSION
    row["gen_model"] = GEN_MODEL
    row["pipeline_commit"] = PIPELINE_COMMIT
    row["created_at"] = _now_iso()
    # Normalize provenance strings in the emitted row (P0.2).
    for ax in ("content_type_source", "depth_source", "discipline_source", "domains_source"):
        row[ax] = _norm(row.get(ax))
    return row


def _atomic_write(path: str, content: str) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".jsonl")
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


def _jsonl(rows: List[Dict[str, Any]]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)


def build(check: bool) -> None:
    rows = _load(IN_CORE)
    gold = sorted([r for r in rows if _tier(r) == "gold"], key=lambda r: r["fb_id"])
    pending = sorted([r for r in rows if _tier(r) == "pending"], key=lambda r: r["fb_id"])
    silver = sorted([r for r in rows if _tier(r) == "silver"], key=lambda r: r["fb_id"])

    assert len(gold) + len(pending) + len(silver) == len(rows), "tier partition is not exhaustive"
    assert len({r["fb_id"] for r in rows}) == len(rows), "duplicate fb_id in verified_core"

    print(f"verified_core rows: {len(rows)}")
    print(f"  gold_4axis:    {len(gold)}")
    print(f"  pending_4axis: {len(pending)}")
    print(f"  silver_4axis:  {len(silver)}")
    ct = Counter(r["content_type"] for r in gold)
    print(f"  gold content_type: {dict(ct)}")

    if check:
        print("[check] dry-run — nothing written")
        return

    _atomic_write(OUT_GOLD, _jsonl([_stamp(r, "gold_4axis") for r in gold]))
    _atomic_write(OUT_PENDING, _jsonl([_stamp(r, "pending_4axis") for r in pending]))
    _atomic_write(OUT_SILVER, _jsonl([_stamp(r, "silver_4axis") for r in silver]))

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": _now_iso(),
        "input": IN_CORE,
        "input_rows": len(rows),
        "tier_counts": {"gold_4axis": len(gold), "pending_4axis": len(pending), "silver_4axis": len(silver)},
        "gold_content_type_distribution": dict(Counter(r["content_type"] for r in gold)),
        "silver_axis_breakdown": _silver_breakdown(silver),
        "provenance_normalization": PROVENANCE_TYPOS,
    }
    _atomic_write(OUT_MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT_GOLD}, {OUT_PENDING}, {OUT_SILVER}, {OUT_MANIFEST}")


def _silver_breakdown(silver: List[Dict[str, Any]]) -> Dict[str, int]:
    """Why is each silver row silver? (ct/depth/disc/dom flags)."""
    c: Counter = Counter()
    for r in silver:
        flags = []
        if r.get("content_type_source") not in CT_AUTH:
            flags.append(f"ct:{r.get('content_type_source')}")
        if r.get("depth_source") not in DEPTH_AUTH:
            flags.append(f"depth:{r.get('depth_source')}")
        if not _discdom_authoritative(r.get("discipline_source")):
            flags.append(f"disc:{_norm(r.get('discipline_source'))}")
        if not _discdom_authoritative(r.get("domains_source")):
            flags.append(f"dom:{_norm(r.get('domains_source'))}")
        c[" + ".join(sorted(flags))] += 1
    return dict(c)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Split verified_core.jsonl into 4-axis provenance tiers (D2618 P0.1).")
    ap.add_argument("--check", action="store_true", help="dry-run, write nothing")
    args = ap.parse_args()
    build(check=args.check)
