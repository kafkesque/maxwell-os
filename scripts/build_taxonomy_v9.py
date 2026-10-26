#!/usr/bin/env python3
"""build_taxonomy_v9.py — apply the owner-ratified v9 menu-edit flags (D-2897).

Deterministic, review-then-apply. This does NOT touch the live file; it writes
config/taxonomy_v9.yaml + governance/taxonomy_v9_migration.json. After
scripts/validate_taxonomy_partition.py reports CLEAN on the v9 output, a SEPARATE
apply step promotes v9, bumps config/version.yaml v8->v9, mints config/closed_menu_v9.json,
re-pins config/menu_axis_hashes.yaml, drops stale per_label weights, and re-classifies the
96 (+1 alias) directly-affected canonical rows.

Transforms (D-2897, owner-ratified 2026-10-09; each documented in the migration report):

  A. MERGE   — disc-002 'visual semiotics' -> disc-004 'semiotics' (both Perception & Signal).
               raw unioned (case/punct-insensitive dedup, first kept); exclude unioned minus
               the now-self-referential 'visual semiotics'.
  B. MERGE   — disc-060 'information retrieval' -> disc-038 'information science'. CROSS-MACRO
               (D-2897b): the IR canonical is removed; its raw folds into IS (group stays
               Systems & Method, macro Method & Business). Exclude unioned minus self-refs
               ('information retrieval', 'information science').
  C. DEMOTE  — disc-061 'computational theory' -> 'emerging' (D-2897a). Canonical removed,
               raw synonyms retired with it. Recorded in meta.displaced_canonicals.
  D. PROMOTE — 'creative writing' (new disc-065, Heterodox) + 'museum studies' (new disc-066,
               Heterodox) become canonical disciplines (D-2897c). Raw includes the alias
               'creative writing studies' so the 1 alias row canonicalises deterministically.
  E. RE-HOME — raw 'museum studies' moves from domain dom-'arts & culture' into the new
               discipline disc-066. REQUIRED by the MECE partition (validate_taxonomy_partition):
               a raw synonym may map to exactly ONE (axis,id), and D-2897c promotes museum
               studies to a DISCIPLINE, so it cannot remain a domain raw synonym too.
  F. GROUPS  — superseded discipline_groups mapping kept consistent: drop 'visual semiotics',
               'information retrieval', 'computational theory'; add 'creative writing' ->
               communication & media and 'museum studies' -> human & behavioral science.
               (discipline_groups is superseded by disciplines[].group + discipline_macro_groups.yaml,
               but is still read by rescore_ruler_inverted.py / train_hierarchical_classifier.py.)

NOT touched (owner ruled): 'color theory' (D-2895), 'design psychology', 'generative ai' /
'creative coding' / 'generative design' (reserved slots). 'writing studies' (7 rows) is a
DISTINCT discipline and stays off-menu.
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "config" / "taxonomy_v8.yaml"   # BUILT v8 source (already validated + live)
OUT = ROOT / "config" / "taxonomy_v9.yaml"
MIG = ROOT / "governance" / "taxonomy_v9_migration.json"

MERGE_VS_ID = "disc-002"        # visual semiotics
MERGE_VS_DST = "disc-004"       # semiotics
MERGE_IR_ID = "disc-060"        # information retrieval
MERGE_IR_DST = "disc-038"       # information science
DEMOTE_ID = "disc-061"          # computational theory
ARTS_CULTURE_DOM = "arts & culture"  # domain whose raw 'museum studies' must be re-homed

NEW_CREATIVE_WRITING = {
    "id": "disc-065",
    "canonical": "creative writing",
    "group": "Heterodox",
    "raw": ["creative writing", "creative writing studies"],
    "definition": "The craft and study of composing original narrative, prose, and poetry across forms and media.",
    "exclude": [],
}
NEW_MUSEUM_STUDIES = {
    "id": "disc-066",
    "canonical": "museum studies",
    "group": "Heterodox",
    "raw": ["museum studies"],
    "definition": "The study of museums and heritage institutions — curation, collection management, interpretation, and public education.",
    "exclude": [],
}


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


def _union_minus(excludes: list[str], self_refs: list[str]) -> list[str]:
    """Union two exclude lists (already concatenated), dropping normalized self-refs."""
    refs = {_norm(r) for r in self_refs}
    return _dedup([x for x in excludes if _norm(x) not in refs])


def build_v9(tax: dict) -> tuple[dict, dict]:
    """Return (tax_v9, migration_report). Mutates a deep copy of tax, never the input."""
    tax = copy.deepcopy(tax)
    report: dict = {
        "source": str(SRC.relative_to(ROOT)),
        "decision": "D-2897",
        "version_before": tax.get("version"),
        "version_after": "v9",
        "merge": [],
        "demote": [],
        "promote": [],
        "rehome_raw": [],
        "discipline_groups": {},
    }

    disc = tax["disciplines"]
    by_id = {e["id"]: e for e in disc}

    def _must(did: str, what: str) -> dict:
        e = by_id.get(did)
        if e is None:
            raise SystemExit(f"missing {what} {did}")
        return e

    # A. visual semiotics -> semiotics
    src, dst = _must(MERGE_VS_ID, "merge-src"), _must(MERGE_VS_DST, "merge-dst")
    report["merge"].append({
        "from": f"{src['id']}:{src['canonical']}",
        "into": f"{dst['id']}:{dst['canonical']}",
        "raw_src_count": len(src["raw"]),
        "raw_dst_before": len(dst["raw"]),
    })
    dst["raw"] = _dedup(dst["raw"] + src["raw"])
    dst["exclude"] = _union_minus(dst["exclude"] + src["exclude"], [src["canonical"]])
    report["merge"][-1]["raw_dst_after"] = len(dst["raw"])

    # B. information retrieval -> information science (cross-macro)
    src2, dst2 = _must(MERGE_IR_ID, "merge-src"), _must(MERGE_IR_DST, "merge-dst")
    report["merge"].append({
        "from": f"{src2['id']}:{src2['canonical']}",
        "into": f"{dst2['id']}:{dst2['canonical']}",
        "cross_macro": True,
        "raw_src_count": len(src2["raw"]),
        "raw_dst_before": len(dst2["raw"]),
    })
    dst2["raw"] = _dedup(dst2["raw"] + src2["raw"])
    dst2["exclude"] = _union_minus(dst2["exclude"] + src2["exclude"], [src2["canonical"], dst2["canonical"]])
    report["merge"][-1]["raw_dst_after"] = len(dst2["raw"])

    # C. computational theory -> emerging
    dem = _must(DEMOTE_ID, "demote")
    report["demote"].append({
        "id": dem["id"],
        "canonical": dem["canonical"],
        "raw": dem["raw"],
        "routing": "emerging",
    })

    removed_ids = {MERGE_VS_ID, MERGE_IR_ID, DEMOTE_ID}
    displaced = [e["canonical"] for e in disc if e["id"] in removed_ids]

    # D. promote creative writing + museum studies (Heterodox)
    for ne in (NEW_CREATIVE_WRITING, NEW_MUSEUM_STUDIES):
        if ne["id"] in by_id:
            raise SystemExit(f"id collision: {ne['id']} already present")
        disc.append(ne)
        report["promote"].append({
            "id": ne["id"],
            "canonical": ne["canonical"],
            "group": ne["group"],
            "raw": ne["raw"],
        })

    # remove merged/demoted entries (AFTER promotes, so removal is by id not index)
    tax["disciplines"] = [e for e in disc if e["id"] not in removed_ids]

    # E. re-home raw 'museum studies' from domain arts & culture -> new discipline (MECE)
    dom = tax["domains"]
    ac = next((e for e in dom if e["canonical"] == ARTS_CULTURE_DOM), None)
    if ac is None:
        raise SystemExit(f"missing domain {ARTS_CULTURE_DOM}")
    before = len(ac["raw"])
    removed_raw = [r for r in ac["raw"] if _norm(r) == _norm("museum studies")]
    ac["raw"] = [r for r in ac["raw"] if _norm(r) != _norm("museum studies")]
    report["rehome_raw"].append({
        "from_domain": ac["canonical"],
        "raw_removed": removed_raw,
        "raw_before": before,
        "raw_after": len(ac["raw"]),
        "reason": "D-2897c promotes museum studies to a discipline; MECE forbids a raw synonym on two axes",
    })

    # F. discipline_groups (superseded but read by legacy scripts) kept consistent
    dg = tax.setdefault("discipline_groups", {})
    remove_map = {
        "visual semiotics": "design & visual arts",
        "information retrieval": "computing, ai & information",
        "computational theory": "engineering, math & physics",
    }
    add_map = {
        "creative writing": "communication & media",
        "museum studies": "human & behavioral science",
    }
    for label, cat in remove_map.items():
        members = dg.get(cat)
        if members is not None and label in members:
            members.remove(label)
            report["discipline_groups"].setdefault("removed", []).append(f"{label} <- {cat}")
    for label, cat in add_map.items():
        members = dg.setdefault(cat, [])
        if label not in members:
            members.append(label)
            report["discipline_groups"].setdefault("added", []).append(f"{label} -> {cat}")

    # version + displaced canonicals traceability
    tax["version"] = "v9"
    tax["classification_version"] = "v9"
    meta = tax.setdefault("meta", {})
    disp = meta.setdefault("displaced_canonicals", [])
    for c in displaced:
        if c not in disp:
            disp.append(c)
    report["displaced_canonicals"] = displaced

    report["counts"] = {
        "domains": len(tax["domains"]),
        "disciplines": len(tax["disciplines"]),
    }
    return tax, report


def _write_atomic(path: Path, text: str) -> None:
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
    tax_v9, report = build_v9(tax)
    yaml_out = yaml.safe_dump(tax_v9, sort_keys=False, allow_unicode=True, width=1000)
    _write_atomic(OUT, yaml_out)
    _write_atomic(MIG, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}  (domains={report['counts']['domains']} "
          f"disciplines={report['counts']['disciplines']})")
    print(f"wrote {MIG.relative_to(ROOT)}")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
