#!/usr/bin/env python3
"""remap_referee_v7_28rows.py — D-2853 close-out: re-mint the A/B referee to menu v7.

[COMPLETE 2026-10-10 (D-2916)] — one-shot done; v7 referee is minted + frozen. Do NOT
re-run: it would re-mint under the SAME id (D-353: re-mint under a NEW id, never re-hash).

WHY. D-2853 renamed the canonical DOMAIN ``research & methodology`` -> ``research practice``
(discipline ``research methodology`` is UNCHANGED). The D-2767 A/B referee
(``discipline_anchor_rederived_v6_20261006d.json``) was finalized against menu v6 and still
carries 28 rows whose ``domains`` list the stale v6 label. A v7-menu classifier cannot be
A/B-scored against a v6-label referee, so this remap blocks both the A/B and the S4 rerun.

WHAT (deterministic, LLM-free). For exactly the 28 owner-approved rows (owner_decision ==
``research practice`` in ``governance/rederive_v6_referee_28row_remap_20261007.csv``):
  (1) replace ``research & methodology`` -> ``research practice`` in ``domains``;
  (2) re-stamp the WHOLE manifest to menu v7 (menu_hash/answer_space_hash read from
      config/menu_axis_hashes.yaml, never hardcoded — C12), taxonomy_version -> v7,
      anchor_version -> v7.

D-353: a pin change is a RE-MINT under a NEW id, never a quiet re-hash. This writes a NEW
artifact (``discipline_anchor_rederived_v7_20261007.json``) and leaves the v6 manifest
untouched as the historical D-2820/D-2839 record.

SAFETY (fail-closed): the script aborts unless (a) the CSV carries exactly 28 rows and every
one has owner_decision == ``research practice``; (b) the manifest carries exactly 28 stale
rows and their item_ids match the CSV 1:1; (c) after rename every row is ON the v7 menu.
Writes are crash-safe (C6: tempfile -> fsync -> os.replace) and back up any pre-existing
target (C13).
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lib import artifact_encoding  # noqa: E402 - D-2644/D-2646: the decode rule has ONE home
SRC_MANIFEST = ROOT / "governance" / "discipline_anchor_rederived_v6_20261006d.json"
CSV = ROOT / "governance" / "rederive_v6_referee_28row_remap_20261007.csv"
PINS_YAML = ROOT / "config" / "menu_axis_hashes.yaml"
V7_MENU = ROOT / "config" / "closed_menu_v7.json"
OUT = ROOT / "governance" / "discipline_anchor_rederived_v7_20261007.json"

OLD_LABEL = "research & methodology"
NEW_LABEL = "research practice"
ABSTENTION = "emerging"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_pins() -> dict[str, str]:
    """Read the live menu-v7 pins from config (C12). Never hardcode a hash."""
    import yaml

    pins = yaml.safe_load(PINS_YAML.read_text(encoding="utf-8")) or {}
    composite = str(pins.get("composite_hash_live") or "").strip()
    answer = str(pins.get("answer_space_hash") or "").strip()
    if not composite or not answer:
        raise SystemExit(f"FAIL: {PINS_YAML.name} missing composite_hash_live/answer_space_hash (C16)")
    return {"composite": composite, "answer_space": answer}


def load_csv() -> list[dict[str, str]]:
    """Load the 28-row owner review; every row must be owner-approved (fail-closed)."""
    rows: list[dict[str, str]] = []
    # D-2644/D-2646: the decode rule has exactly ONE home. A local encoding= here is a SECOND implementation
    # of that rule (the class this rail exists to remove), and a GUESSED encoding does not crash - it silently
    # changes text two readers then compare (BUG-511). The CSV is plain valid UTF-8 (measured), so the home
    # returns utf-8 and this read is byte-for-byte the same rows as the retired utf-8-sig literal.
    with artifact_encoding.open_artifact(CSV, ROOT) as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    if len(rows) != 28:
        raise SystemExit(f"FAIL: CSV has {len(rows)} rows, expected 28 (C16)")
    unapproved = [r["item_id"] for r in rows if (r.get("owner_decision") or "").strip() != NEW_LABEL]
    if unapproved:
        raise SystemExit(f"FAIL: {len(unapproved)} rows not owner-approved as {NEW_LABEL!r}: {unapproved[:6]}")
    for r in rows:
        if (r.get("current_domain") or "").strip() != OLD_LABEL:
            raise SystemExit(f"FAIL: CSV row {r['item_id']} current_domain != {OLD_LABEL!r} (C16)")
        if (r.get("proposed_domain") or "").strip() != NEW_LABEL:
            raise SystemExit(f"FAIL: CSV row {r['item_id']} proposed_domain != {NEW_LABEL!r} (C16)")
    return rows


def build_menu_sets() -> tuple[set[str], set[str]]:
    menu = json.loads(V7_MENU.read_text(encoding="utf-8"))
    discs = {e["value"] for e in menu["disciplines"]} | {ABSTENTION}
    doms = {e["value"] for e in menu["domains"]} | {ABSTENTION}
    if not discs or not doms:
        raise SystemExit(f"FAIL: {V7_MENU.name} empty menu (C16)")
    return discs, doms


def crash_safe_write(path: Path, payload: dict) -> None:
    """Crash-safe JSON write (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main() -> int:
    # COMPLETE (D-2916): one-shot already landed; re-running would re-mint under the SAME
    # id (D-353 violation). Fail closed instead of silently re-hashing frozen provenance.
    raise SystemExit(
        "D-2853 close-out is COMPLETE — governance/discipline_anchor_rederived_v7_20261007.json "
        "is already minted and frozen. Re-running would re-mint under the SAME id (D-353). "
        "Refusing (C16)."
    )
    manifest = json.loads(SRC_MANIFEST.read_text(encoding="utf-8"))
    rows = manifest["rows"]
    pins = load_pins()
    discs, doms = build_menu_sets()
    approved = {r["item_id"] for r in load_csv()}

    # (a) exactly 28 stale rows, 1:1 with the CSV.
    stale = [r for r in rows if OLD_LABEL in r["domains"]]
    stale_ids = {r["item_id"] for r in stale}
    if len(stale) != 28:
        raise SystemExit(f"FAIL: manifest has {len(stale)} stale rows, expected 28 (C16)")
    if stale_ids != approved:
        raise SystemExit(f"FAIL: stale/CSV mismatch: only-manifest={sorted(stale_ids-approved)[:6]} "
                         f"only-csv={sorted(approved-stale_ids)[:6]} (C16)")

    # (b) rename + validate on-menu (fail-closed).
    remapped = 0
    for r in rows:
        if r["item_id"] in approved:
            before = list(r["domains"])
            r["domains"] = [NEW_LABEL if d == OLD_LABEL else d for d in r["domains"]]
            if r["domains"] != before:
                remapped += 1
        off_disc = [r["discipline"]] if r["discipline"] not in discs else []
        off_dom = [d for d in r["domains"] if d not in doms]
        if off_disc or off_dom:
            raise SystemExit(f"FAIL: row {r['item_id']} OFF v7 menu: disc={off_disc} dom={off_dom} (C16)")
    if remapped != 28:
        raise SystemExit(f"FAIL: renamed {remapped} rows, expected 28 (C16)")

    # (c) re-stamp the whole manifest to v7 (D-353 re-mint, new artifact id).
    date = _now()
    for r in rows:
        r["_stamp"]["menu_hash"] = pins["composite"]
        r["_stamp"]["answer_space_hash"] = pins["answer_space"]
        r["_stamp"]["taxonomy_version"] = "v7"
        r["_stamp"]["anchor_version"] = "v7"
        r["_stamp"]["date"] = date

    manifest["artifact_id"] = "discipline_anchor_rederived_v7_20261007"
    manifest["menu_hash"] = pins["composite"]
    manifest["answer_space_hash"] = pins["answer_space"]
    manifest["taxonomy_version"] = "v7"
    manifest["anchor_version"] = "v7"
    manifest["_provenance"]["decision"] = "D-2864"
    manifest["_provenance"]["generated_by"] = "scripts/remap_referee_v7_28rows.py (D-2853 close-out remap)"
    manifest["_provenance"]["gen_model"] = "human_owner (adjudicated) + deterministic label remap (no LLM)"
    manifest["_provenance"]["date"] = date

    # (d) back up any existing target, then write crash-safely (C6/C13).
    if OUT.exists():
        bak = OUT.with_suffix(OUT.suffix + f".bak_{int(datetime.now().timestamp())}")
        shutil.copy2(OUT, bak)

    crash_safe_write(OUT, manifest)

    h = hashlib.sha256(json.dumps(manifest["rows"], sort_keys=True).encode("utf-8")).hexdigest()
    print(f"WROTE {OUT.name}")
    print(f"  rows={len(rows)} remapped={remapped}")
    print(f"  menu_hash={pins['composite'][:16]}  answer_space_hash={pins['answer_space'][:16]}")
    print(f"  rows_sha256={h[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
