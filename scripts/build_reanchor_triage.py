#!/usr/bin/env python3
"""build_reanchor_triage.py — triage the T-191 re-anchor candidate sheet (D-3116).

WHY. The 195 dangling ruler names each carry 5 name-cosine candidates
(governance/ANCHOR_208_REANCHOR_CANDIDATES_<date>.csv), but the NAME-only bge-m3
cosine is not discriminative enough to batch-rule NONE vs MATCH (measured
2026-10-22: 9 rows >=0.85, 9 rows <=0.65, 177 in the muddy middle). The store's
`definition` column IS decisive — a glance at the definition makes same-vs-
different obvious. This script produces a TRIAGE sheet that (a) sorts the rows
by best_cos, (b) pulls each candidate's definition preview inline, and (c) tags
an ADVISORY bucket (confirm / read / likely-none). It NEVER picks: the owner's
ruling in owner_ruling_fb_id remains authoritative (R5 / D-2898 / D-3116).

WHAT IT PRODUCES. governance/ANCHOR_208_REANCHOR_TRIAGE_<date>.csv — a fillable
sheet with definition previews and an advisory bucket. The owner fills
owner_ruling_fb_id (a cand* fb_id, or NONE) exactly as on the candidate sheet.

FAIL-VISIBLE (C16). A missing candidate sheet, store, or definition column
raises (no silent half-sheet). Crash-safe write (C6). Read-only over the store.

Usage:
    python3 scripts/build_reanchor_triage.py [--sheet PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from scripts.lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home

REGISTRY = ROOT / "config" / "anchor_family.yaml"


def load_config() -> dict:
    """Return the reanchor_triage block (C12: no path/rule lives in this file)."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    cfg = (data or {}).get("reanchor_triage")
    if not isinstance(cfg, dict):
        raise SystemExit(f"{REGISTRY} carries no reanchor_triage block")
    return cfg


def read_store(cfg: dict) -> dict[str, tuple[str, str]]:
    """Return {fb_id: (name, definition)} READ-ONLY over the live corpus."""
    con = sqlite3.connect(f"file:{ROOT / cfg['store']}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out: dict[str, tuple[str, str]] = {}
    sql = (
        f"SELECT {cfg['store_key']}, {cfg['store_name_column']}, "
        f"{cfg['store_definition_column']} FROM {cfg['store_table']}"
    )
    for r in con.execute(sql):
        fid = str(r[cfg["store_key"]]).strip()
        out[fid] = (r[cfg["store_name_column"]] or "", r[cfg["store_definition_column"]] or "")
    con.close()
    return out


def bucket_for(best_cos: float, confirm: float, none: float) -> str:
    """ADVISORY bucket label; never a ruling (R5)."""
    if best_cos >= confirm:
        return "A-confirm"
    if best_cos <= none:
        return "C-likely-none"
    return "B-read"


def suggest_for(bucket: str, cand1_fb_id: str) -> str:
    """ADVISORY pre-fill hint; the owner's write is the only authority."""
    return {
        "A-confirm": f"likely {cand1_fb_id[:12]}… (verify)",
        "C-likely-none": "likely NONE (verify no store row describes it)",
        "B-read": "",
    }[bucket]


def build(cfg: dict, source_sheet: Path, out_path: Path) -> int:
    """Read the candidate sheet + store, write the sorted triage sheet."""
    with artifact_encoding.open_artifact(source_sheet, ROOT) as fh:  # D-2646: declared encoding (BOM stripped), never a guess
        reader = csv.DictReader(fh)
        # The candidate sheet carries a leading space on the first header field;
        # normalize ALL fieldnames so column access is whitespace-stable.
        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]
        rows = [{k.strip(): v for k, v in row.items()} for row in reader]
    if not rows or "item_id" not in fieldnames:
        raise SystemExit(f"{source_sheet} is empty or missing item_id column")

    store = read_store(cfg)
    confirm = float(cfg["confirm_cos"])
    none = float(cfg["none_cos"])
    chars = int(cfg["definition_chars"])

    fieldnames = [
        "bucket", "item_id", "ruler_name", "best_cos", "gap12",
        "cand1_name", "cand1_fb_id", "cand1_cos", "cand1_def",
        "cand2_name", "cand2_fb_id", "cand2_cos", "cand2_def",
        "cand3_name", "cand3_fb_id", "cand3_cos", "cand3_def",
        "suggest", "owner_ruling_fb_id", "owner_ruling_note",
    ]

    triaged: list[dict[str, str]] = []
    for r in rows:
        best = float(r["best_cos"])
        gap12 = float(r["cand1_cos"]) - float(r["cand2_cos"])
        bkt = bucket_for(best, confirm, none)
        cand1_fid = (r.get("cand1_fb_id") or "").strip()

        def cand(n: int) -> tuple[str, str, str, str]:
            name = (r.get(f"cand{n}_name") or "").strip()
            fid = (r.get(f"cand{n}_fb_id") or "").strip()
            cos = (r.get(f"cand{n}_cos") or "").strip()
            sn, sd = store.get(fid, ("", ""))
            prev = " ".join(sd.split())[:chars]
            return name or sn, fid, cos, prev

        c1n, c1f, c1c, c1d = cand(1)
        c2n, c2f, c2c, c2d = cand(2)
        c3n, c3f, c3c, c3d = cand(3)

        triaged.append({
            "bucket": bkt,
            "item_id": r["item_id"],
            "ruler_name": r["ruler_name"],
            "best_cos": f"{best:.3f}",
            "gap12": f"{gap12:.3f}",
            "cand1_name": c1n, "cand1_fb_id": c1f, "cand1_cos": c1c, "cand1_def": c1d,
            "cand2_name": c2n, "cand2_fb_id": c2f, "cand2_cos": c2c, "cand2_def": c2d,
            "cand3_name": c3n, "cand3_fb_id": c3f, "cand3_cos": c3c, "cand3_def": c3d,
            "suggest": suggest_for(bkt, c1f),
            "owner_ruling_fb_id": "",
            "owner_ruling_note": "",
        })

    # Sort so the owner reads confirm-bucket first, likely-none last.
    order = {"A-confirm": 0, "B-read": 1, "C-likely-none": 2}
    triaged.sort(key=lambda d: (order[d["bucket"]], -float(d["best_cos"])))

    # Crash-safe write (C6): tempfile -> fsync -> os.replace.
    fd, tmp = tempfile.mkstemp(dir=out_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(triaged)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, out_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    counts = {b: sum(1 for d in triaged if d["bucket"] == b) for b in order}
    print(
        f"triage wrote {len(triaged)} rows -> {out_path} "
        f"(A-confirm {counts['A-confirm']}, B-read {counts['B-read']}, "
        f"C-likely-none {counts['C-likely-none']})"
    )
    return 0


def main() -> int:
    cfg = load_config()
    ap = argparse.ArgumentParser(description="Triage the T-191 re-anchor candidate sheet")
    ap.add_argument("--sheet", default=None, help="candidate sheet (default: config source_sheet)")
    ap.add_argument("--out", default=None, help="output path (default: config out)")
    args = ap.parse_args()

    source_sheet = ROOT / (args.sheet or cfg["source_sheet"])
    out_path = ROOT / (args.out or cfg["out"])
    return build(cfg, source_sheet, out_path)


if __name__ == "__main__":
    raise SystemExit(main())
