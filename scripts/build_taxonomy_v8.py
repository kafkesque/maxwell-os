#!/usr/bin/env python3
"""build_taxonomy_v8.py — apply the owner-approved A/B/C taxonomy fixes (D-2865).

Deterministic, review-then-apply. This does NOT touch the live file; it writes
config/taxonomy_v8.yaml + governance/taxonomy_v8_migration.json. After
scripts/validate_taxonomy_partition.py reports CLEAN on the v8 output, a SEPARATE
apply step backs up v5/v7, promotes v8, bumps config/version.yaml, mints
config/closed_menu_v8.json, re-pins config/menu_axis_hashes.yaml, and regenerates
config/taxonomy_shacl.ttl.

Transforms (owner-ratified, each documented in the migration report):

  A. MERGE   — dom-031 'science & research' -> dom-025 'research practice'.
               raw lists are unioned (case/punct-insensitive dedup, first kept),
               excludes unioned minus the self-reference 'science research',
               definition rewritten to the scholarly+scientific research practice.
  B. DEMOTE  — dom-035 'social sciences' is demoted: its raw synonyms fold into the
               merged dom-025 'research practice'; the canonical label is removed
               (no new canonical label). Recorded in meta.displaced_canonicals.
  C. DEDUP   — raw 'user experience design' is dropped from disc-036
               'human-computer interaction' (it stays under dom-010 'user experience'),
               resolving the cross-axis MECE violation (D-2856 stale after 65339ae).

NOT touched (owner ruled): disc-021 'research methodology', disc-022 'operations
research', dom-016 'organizational behavior'.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "config" / "taxonomy.yaml"   # LIVE source (renderer + validator read it)
OUT = ROOT / "config" / "taxonomy_v8.yaml"
MIG = ROOT / "governance" / "taxonomy_v8_migration.json"

MERGE_SRC_ID = "dom-031"          # science & research
MERGE_DST_ID = "dom-025"          # research practice
DEMOTE_ID = "dom-035"             # social sciences
HCI_ID = "disc-036"               # human-computer interaction
DEDUP_RAW = "user experience design"

MERGE_DST_DEFINITION = (
    "The professional activity of conducting, publishing, and applying scholarly "
    "and scientific research."
)
# Self-reference to drop from the unioned exclude: 'science research' no longer exists
# as a domain after the merge (its denotation is now inside research practice).
SELF_REF_EXCLUDE = "science research"


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _dedup(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in seq:
        key = _norm(s)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def build_v8(tax: dict) -> tuple[dict, dict]:
    """Return (tax_v8, migration_report). Mutates a deep copy of tax, never the input."""
    import copy

    tax = copy.deepcopy(tax)
    report: dict = {
        "source": str(SRC.relative_to(ROOT)),
        "version_before": tax.get("version"),
        "version_after": "v8",
        "merge": {},
        "demote": {},
        "raw_dedup": {},
    }

    domains = tax["domains"]
    dst = next((e for e in domains if e.get("id") == MERGE_DST_ID), None)
    src = next((e for e in domains if e.get("id") == MERGE_SRC_ID), None)
    dem = next((e for e in domains if e.get("id") == DEMOTE_ID), None)
    if dst is None or src is None or dem is None:
        raise SystemExit(f"missing entries: dst={dst}, src={src}, dem={dem}")

    # A. merge dom-031 into dom-025
    report["merge"] = {
        "from": f"{src['id']}:{src['canonical']}",
        "into": f"{dst['id']}:{dst['canonical']}",
        "raw_src_count": len(src["raw"]),
        "raw_dst_before": len(dst["raw"]),
        "exclude_src": src["exclude"],
        "exclude_dst_before": dst["exclude"],
        "definition_before": dst["definition"],
    }
    dst["raw"] = _dedup(dst["raw"] + src["raw"])
    dst["exclude"] = _dedup(
        [x for x in (dst["exclude"] + src["exclude"]) if _norm(x) != _norm(SELF_REF_EXCLUDE)]
    )
    dst["definition"] = MERGE_DST_DEFINITION
    report["merge"]["raw_dst_after"] = len(dst["raw"])
    report["merge"]["exclude_dst_after"] = dst["exclude"]
    report["merge"]["definition_after"] = dst["definition"]

    # B. demote dom-035 -> fold raw into dom-025, remove the canonical entry
    report["demote"] = {
        "id": dem["id"],
        "canonical": dem["canonical"],
        "raw": dem["raw"],
        "raw_dst_before_fold": len(dst["raw"]),
    }
    dst["raw"] = _dedup(dst["raw"] + dem["raw"])
    report["demote"]["raw_dst_after_fold"] = len(dst["raw"])
    domains[:] = [e for e in domains if e.get("id") not in (MERGE_SRC_ID, DEMOTE_ID)]

    # C. drop 'user experience design' from disc-036
    hci = next((e for e in tax["disciplines"] if e.get("id") == HCI_ID), None)
    if hci is None:
        raise SystemExit(f"missing discipline {HCI_ID}")
    before = len(hci["raw"])
    hci["raw"] = [r for r in hci["raw"] if _norm(r) != _norm(DEDUP_RAW)]
    report["raw_dedup"] = {
        "discipline": f"{hci['id']}:{hci['canonical']}",
        "dropped_raw": DEDUP_RAW,
        "kept_in": "dom-010:user experience",
        "raw_before": before,
        "raw_after": len(hci["raw"]),
    }

    # version + displaced canonicals traceability
    tax["version"] = "v8"
    tax["classification_version"] = "v8"
    meta = tax.setdefault("meta", {})
    displaced = meta.setdefault("displaced_canonicals", [])
    for c in (src["canonical"], dem["canonical"]):
        if c not in displaced:
            displaced.append(c)
    report["displaced_canonicals"] = displaced

    report["counts"] = {
        "domains": len(tax["domains"]),
        "disciplines": len(tax["disciplines"]),
    }
    return tax, report


def _write_atomic(path: Path, text: str) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
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
    tax = load(SRC)
    tax_v8, report = build_v8(tax)
    yaml_out = yaml.safe_dump(tax_v8, sort_keys=False, allow_unicode=True, width=1000)
    _write_atomic(OUT, yaml_out)
    _write_atomic(MIG, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}  (domains={report['counts']['domains']} "
          f"disciplines={report['counts']['disciplines']})")
    print(f"wrote {MIG.relative_to(ROOT)}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
