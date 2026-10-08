#!/usr/bin/env python3
"""build_depth_anchor_conformance.py — build the human-provenanced depth anchor.

WHAT THIS PRODUCES
------------------
`governance/depth_anchor_conformance_<date>.json` — the first DURABLE, HUMAN-OWNER
depth ground truth (fixes the BUG-617 gap: "depth axis lacks human-provenanced
ground truth"). It is a CONFORMANCE set (D-274f), NOT a training set and NOT a
few-shot injection: "the first thing NOT to do with the anchor is fine-tune on it."

JOIN (deterministic, no LLM)
----------------------------
Three inputs, joined by item_id under the declared `collapse_whitespace`
normalization (D-2658 — join is by content, never by position):
  1. governance/ANCHOR_208_DEPTH_CORRECTED_20261002.json  (owner-finalized depth, D-2760)
  2. governance/ANCHOR_STORE_BRIDGE_20260926.json          (item_id -> fb_id, 197/208 joined)
  3. knowledge pipeline/maxwell.db  table fbs              (full FB text by fb_id)

EXCLUSIONS (both ledgered in `excluded`, never silently dropped)
----------------------------------------------------------------
  * 14 owner noise_drop rows (D-2760 `depth_source == "owner_finalized_noise_drop"`
    sentinel, depth_label now null; D-2813: depth does not apply to a noise_drop row).
    Checked BOTH forms (depth_label == "noise_drop" OR the depth_source sentinel) so a
    stale face still carrying the old label form is also caught — the consolidate /
    regenerate idiom.
  * 11 ambiguous-join rows (D-2658 name-collision refusals) declared by the bridge's
    `join.ambiguous`: two corpus rows share the folded name, so the join refuses to pick
    one. They are OWED an explicit fb_id — a SEPARATE owner decision, NOT part of this
    build. The builder fail-closes if the rows actually missing from the bridge do not
    EXACTLY equal the bridge's declared ambiguous set (C16 — no silent drift).

The 58 formerly-mapped extras are now owner-adjudicated and folded (D-2785) and ARE
emitted when the bridge joins them.

Every output row is provenance-stamped (schema_version, gen_model, source sha256)
per R14.

Usage:
    python3 scripts/build_depth_anchor_conformance.py [--out PATH]
    python3 scripts/build_depth_anchor_conformance.py --check   # byte-re-derivability rail
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEPTH_MAP = REPO / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
STORE_BRIDGE = REPO / "governance" / "ANCHOR_STORE_BRIDGE_20260926.json"
STORE = REPO / "knowledge pipeline" / "maxwell.db"

DEPTH_LABELS = ("universal", "cross-domain", "domain", "specialized")

# The canonical provenance sentinel (D-2760): a noise_drop row carries
# depth_source == "owner_finalized_noise_drop" and depth_label == None.
NOISE_DROP_SENTINEL = "owner_finalized_noise_drop"

# Fields that are compared byte-for-byte by --check. `created_at` is a wall-clock
# stamp and `_noise_drop_clear` is a one-time surgical ledger (superseded by the
# canonical `excluded` list), so neither is part of the reproducibility contract.
_CHECK_FIELDS = ("schema_version", "artifact_id", "depth_labels", "examples", "counts", "excluded")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _collapse(s: str) -> str:
    """collapse_whitespace per the declared store-bridge normalization (D-2658)."""
    return " ".join((s or "").split())


def _is_noise_drop(rec: dict) -> bool:
    """True if the row is an owner-declared noise_drop.

    D-2760 moved the sentinel from depth_label == "noise_drop" (old form) to
    depth_source == "owner_finalized_noise_drop" (new form; depth_label is now null).
    Check BOTH forms — the consolidate/regenerate idiom — so a stale face still
    carrying the old label form is caught too.
    """
    return rec.get("depth_label") == "noise_drop" or "noise_drop" in str(
        rec.get("depth_source", "")
    )


def build(out: Path) -> dict:
    depth_map = json.loads(DEPTH_MAP.read_text(encoding="utf-8"))
    bridge = json.loads(STORE_BRIDGE.read_text(encoding="utf-8"))
    by_id = {r["item_id"]: r for r in depth_map}

    bridge_entries = bridge.get("entries", {})
    bridge_ids = {v["item_id"] for v in bridge_entries.values()}

    # D-2658: ambiguous name-collision refusals, DECLARED by the bridge builder.
    ambiguous = bridge.get("join", {}).get("ambiguous", [])
    ambiguous_ids = {a["item_id"] for a in ambiguous}

    # Fail-closed (C16): every golden row missing from the bridge must be a DECLARED
    # ambiguous refusal. Any other gap is unannounced drift and must stop the build.
    noise_drop_ids = {r["item_id"] for r in depth_map if _is_noise_drop(r)}
    golden_ids = {r["item_id"] for r in depth_map if r["item_id"] not in noise_drop_ids}
    missing = golden_ids - bridge_ids
    if missing != ambiguous_ids:
        raise SystemExit(
            "FAIL-CLOSED: golden rows missing from the bridge ("
            + ", ".join(sorted(missing))
            + ") do not equal the bridge's declared ambiguous set ("
            + ", ".join(sorted(ambiguous_ids))
            + ")"
        )

    db = sqlite3.connect(str(STORE))
    cur = db.cursor()

    examples: list[dict] = []
    excluded: list[dict] = []
    name_normalized: list[str] = []  # (item_id) — whitespace-only diffs are expected

    for fb_id, entry in bridge_entries.items():
        item_id = entry["item_id"]
        rec = by_id.get(item_id)
        if rec is None:
            raise SystemExit(f"FAIL: bridge item_id {item_id} missing from depth map")
        if _is_noise_drop(rec):
            excluded.append(
                {
                    "item_id": item_id,
                    "reason": "owner noise_drop (D-2760 depth_source sentinel; D-2813: depth does not apply)",
                }
            )
            continue
        cur.execute(
            "SELECT name, definition, mechanism, boundary, extraction_type FROM fbs WHERE fb_id=?",
            (fb_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise SystemExit(f"FAIL: fb_id {fb_id} (item {item_id}) not in store")
        name, definition, mechanism, boundary, extraction_type = row
        if _collapse(name) != _collapse(rec.get("name", "")):
            name_normalized.append(item_id)
        examples.append(
            {
                "item_id": item_id,
                "name": name,
                "definition": definition or "",
                "mechanism": mechanism or "",
                "boundary": boundary or "",
                "extraction_type": extraction_type or "",
                "depth": rec.get("depth"),
                "depth_label": rec.get("depth_label"),
                "depth_source": rec.get("depth_source"),
                "fb_id": fb_id,
            }
        )

    db.close()

    # Ledger the ambiguous (D-2658) refusals explicitly — never silently dropped.
    # Order follows the bridge's declared list for determinism.
    for a in ambiguous:
        excluded.append(
            {
                "item_id": a["item_id"],
                "reason": "ambiguous join (D-2658 name-collision refusal, "
                + str(len(a.get("candidates") or []))
                + " candidates) — OWED explicit fb_id (separate owner decision)",
            }
        )

    # integrity: exactly the joinable golden rows (golden ∩ bridge), all labels on-menu
    expected = len(golden_ids & bridge_ids)
    if len(examples) != expected:
        raise SystemExit(f"FAIL: expected {expected} golden rows, got {len(examples)}")
    off = [e["item_id"] for e in examples if e["depth_label"] not in DEPTH_LABELS]
    if off:
        raise SystemExit(f"FAIL: off-menu depth labels: {off}")

    by_label: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for e in examples:
        by_label[e["depth_label"]] = by_label.get(e["depth_label"], 0) + 1
        by_source[e["depth_source"]] = by_source.get(e["depth_source"], 0) + 1

    # pipeline stamp (R14) — read live, never hardcode
    try:
        from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: F401
        commit = PIPELINE_COMMIT
        schema_version = SCHEMA_VERSION
    except Exception:
        commit = "unknown"
        schema_version = "unknown"

    doc = {
        "schema_version": "1.0",
        "artifact_id": "DEPTH_ANCHOR_CONFORMANCE",
        "generated_by": "scripts/build_depth_anchor_conformance.py",
        "gen_model": "none (deterministic join; no LLM)",
        "pipeline_commit": commit,
        "maxwell_schema_version": schema_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authority": [
            "D-2760 (owner finalized 42 depth mismatches; corrected depth map)",
            "D-274f (anchor is a conformance set, NOT a training set)",
            "D-2611 (report chance-corrected kappa, never bare accuracy)",
            "D-2658 (join by content, never by position; ambiguous = refuse, declare, never pick)",
            "D-2813 (depth does not apply to a noise_drop row)",
            "config/agreement_floor.yaml (operative floor 0.800)",
        ],
        "inputs": {
            "depth_map": {"path": str(DEPTH_MAP), "sha256": _sha256(DEPTH_MAP)},
            "store_bridge": {"path": str(STORE_BRIDGE), "sha256": _sha256(STORE_BRIDGE)},
            "store": {"path": str(STORE), "table": "fbs"},
        },
        "join": {"key": "item_id", "normalization": "collapse_whitespace"},
        "counts": {
            "total": len(examples),
            "by_depth_label": by_label,
            "by_depth_source": by_source,
            "name_normalized": name_normalized,
            "excluded_noise_drop": len(noise_drop_ids),
            "excluded_ambiguous": len(ambiguous_ids),
        },
        "depth_labels": list(DEPTH_LABELS),
        "excluded": excluded,
        "examples": examples,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def check(out: Path) -> int:
    """Verify the committed artifact is byte-re-derivable from the builder (modulo
    the wall-clock `created_at` and the superseded `_noise_drop_clear` ledger)."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, dir=out.parent) as tf:
        tmp = Path(tf.name)
    try:
        doc = build(tmp)
        committed = json.loads(out.read_text(encoding="utf-8"))
        diffs = [f for f in _CHECK_FIELDS if doc.get(f) != committed.get(f)]
        if diffs:
            print("FAIL: committed conformance is NOT byte-re-derivable. drift in: " + ", ".join(diffs))
            return 1
        print(
            f"OK: committed conformance byte-re-derivable "
            f"({len(doc['examples'])} examples, {len(doc['excluded'])} excluded)"
        )
        return 0
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(REPO / "governance" / "depth_anchor_conformance_20261002.json"),
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifact is byte-re-derivable (modulo created_at)",
    )
    args = ap.parse_args()
    out = Path(args.out)
    if args.check:
        return check(out)
    doc = build(out)
    print(f"wrote {args.out}")
    print(f"  total owner rows: {doc['counts']['total']}")
    print(f"  by_depth_label: {doc['counts']['by_depth_label']}")
    print(f"  excluded: {len(doc['excluded'])} "
          f"(noise_drop {doc['counts']['excluded_noise_drop']} + "
          f"ambiguous {doc['counts']['excluded_ambiguous']})")
    print(f"  name_normalized (whitespace-only): {doc['counts']['name_normalized']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
