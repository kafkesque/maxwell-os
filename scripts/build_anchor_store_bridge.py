#!/usr/bin/env python3
"""build_anchor_store_bridge.py - the anchor-family <-> corpus BRIDGE, keyed by CONTENT (BUG-420 / D-2658).

WHY. The anchor family is keyed by `item_id` (R001..., a SHEET-LOCAL row label) and the corpus by `fb_id` (a
64-hex content address). Two identifier spaces that never intersect, so a human ruling inside the anchor cannot be
attributed to a corpus row and a corpus measurement cannot be graded against the anchor (BUG-420; MEASURED
2026-09-24: anchor4 vs gold.fb_id = 0/150). This script derives the bridge ONCE, deterministically, and RECORDS
how each row was joined. A name matching two corpus rows is AMBIGUOUS and is recorded, never picked: the bridge
never guesses (D-2658: a declared SITE is keyed by CONTENT, never by a line number).

WHAT IT IS NOT. It copies NO stored value - only the JOIN, the METHOD and the input DIGESTS. Every axis value stays
owned by ANCHOR-3 (the ruler) and by the store; a second copy of a value is the BUG-402 class.

TRI-STATE (BUG-457): 0 clean | 1 drift (ambiguity, undeclared unresolved row, stale artifact) | 2 owner-owed
(rows the config DECLARES). A row that does not join is NEVER silently downgraded to owner-owed: the GOLDEN side
obeys the SAME rule as the corpus side (BUG-551) - an UNDECLARED unjoined golden row is DRIFT (1), a DECLARED one
is owner-owed (2), a declaration with no adequate why is DRIFT (1), and a declaration whose row now JOINS is
owner-owed (2): the ceiling shrinks LOUDLY, it never silently stops applying.

Usage: python3 scripts/build_anchor_store_bridge.py [--check|--selftest|--print-config]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "config" / "anchor_family.yaml"
PREFIX = "bridge"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
GEN_MODEL = "none (deterministic join; no LLM)"
JSON_INDENT = 2
MIN_WHY = 20  # BUG-551: a declaration without a why is a permission slip, not a declaration (the store rail's floor)


def load_config() -> dict:
    """Load the store_bridge block of the anchor-family registry (C12: no path or rule lives in this file)."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    cfg = (data or {}).get("store_bridge")
    if not isinstance(cfg, dict):
        raise KeyError(f"{REGISTRY} carries no store_bridge block - the bridge has no declared configuration")
    return cfg


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file, streamed so a 156 MB store never has to fit in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Return the hex sha256 of a text value (the content key of a joined row)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm_name(value: str, mode: str) -> str:
    """Normalise a NAME for joining. Declared, never implicit: 'collapse_whitespace' folds whitespace runs and
    case; any other mode is a defect rather than a silent pass-through."""
    if mode != "collapse_whitespace":
        raise ValueError(f"unsupported normalization {mode!r} - declared modes are the only ones allowed")
    return " ".join(value.split()).casefold()


def read_ruler(cfg: dict) -> List[Dict[str, str]]:
    """Read the anchor ruler sheet (its own encoding is declared: utf-8-sig, the F-1 re-issue)."""
    with open(ROOT / cfg["ruler_sheet"], newline="", encoding=cfg["ruler_encoding"]) as fh:
        return [r for r in csv.DictReader(fh) if (r.get(cfg["item_key"]) or "").strip()]


def read_store(cfg: dict) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Read the corpus READ-ONLY and return (fb_id -> raw name, normalised name -> [fb_id]). Writes nothing."""
    con = sqlite3.connect(f"file:{ROOT / cfg['store']}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        sql = f'SELECT {cfg["store_key"]}, {cfg["store_name_column"]} FROM {cfg["store_table"]}'
        names: Dict[str, str] = {}
        index: Dict[str, List[str]] = {}
        for r in con.execute(sql):
            fid = str(r[cfg["store_key"]]).strip()
            raw = str(r[cfg["store_name_column"]] or "")
            names[fid] = raw
            index.setdefault(norm_name(raw, cfg["normalization"]), []).append(fid)
        return names, index
    finally:
        con.close()


def resolve(ruler: List[Dict[str, str]], index: Dict[str, List[str]], cfg: dict,
            raw_names: Dict[str, str]) -> dict:
    """Resolve every ruler row to a corpus fb_id by CONTENT. Pure over its inputs so the known-answer controls can
    drive it with synthetic rows. Exact before normalised; >=2 candidates is AMBIGUOUS (recorded, never picked);
    zero candidates is UNRESOLVED."""
    mode, item_key = cfg["normalization"], cfg["item_key"]
    entries: Dict[str, dict] = {}
    ambiguous: List[dict] = []
    unresolved: List[str] = []
    exact_n = normalised_n = 0
    for r in ruler:
        item = (r.get(item_key) or "").strip()
        name = (r.get("name") or "").strip()
        cands = index.get(norm_name(name, mode), [])
        if len(cands) > 1:
            ambiguous.append({"item_id": item, "name": name, "candidates": sorted(cands)})
            continue
        if not cands:
            unresolved.append(item)
            continue
        fid = cands[0]
        exact = name == raw_names.get(fid, "")
        exact_n += 1 if exact else 0
        normalised_n += 0 if exact else 1
        entries[fid] = {"item_id": item, "name": name, "name_sha256": sha256_text(name),
                        "join": "exact" if exact else "normalized",
                        "join_note": "byte-identical name" if exact else f"matched after {mode}"}
    return {"entries": entries, "ambiguous": sorted(ambiguous, key=lambda a: a["item_id"]),
            "unresolved": sorted(unresolved),
            "counts": {"rows": len(ruler), "joined": len(entries), "exact": exact_n, "normalized": normalised_n,
                       "ambiguous": len(ambiguous), "unresolved": len(unresolved)}}


def read_golden(cfg: dict, index: Dict[str, List[str]]) -> dict:
    """Join the retired training golden to the corpus with the SAME rule. Returns the join only: the golden's
    labels stay where they are (this script is not their home)."""
    g = cfg.get("golden") or {}
    path = ROOT / g["path"]
    rows = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("examples") or []
    joined: Dict[str, str] = {}
    hist: Dict[str, int] = {}
    unjoined: List[str] = []
    detail: List[dict] = []  # BUG-551: the receipt carries the CAUSE, not only the id
    for e in rows:
        node: Any = e
        for part in g["name_path"].split("."):
            node = (node or {}).get(part) if isinstance(node, dict) else None
        cands = index.get(norm_name(str(node or "").strip(), cfg["normalization"]), [])
        if len(cands) == 1:
            joined[str(e.get(g["id_key"]))] = cands[0]
            hist["joined"] = hist.get("joined", 0) + 1
        else:
            uid = str(e.get(g["id_key"]))
            unjoined.append(uid)
            key = "ambiguous" if cands else "unresolved"
            hist[key] = hist.get(key, 0) + 1
            detail.append({"id": uid, "cause": key, "name": str(node or "").strip(),
                           "candidates": sorted(cands)})
    return {"path": g["path"], "sha256": sha256_file(path), "rows": len(rows), "joined": len(joined),
            "histogram": hist, "unjoined": unjoined, "unjoined_detail": detail, "id_to_fb_id": joined}


def build(cfg: dict) -> dict:
    """Derive the whole bridge document from the declared inputs."""
    ruler = read_ruler(cfg)
    raw_names, index = read_store(cfg)
    res = resolve(ruler, index, cfg, raw_names)
    return {
        "schema_version": "1.0",
        "artifact_id": cfg["artifact_id"],
        "generated_by": "scripts/build_anchor_store_bridge.py",
        "gen_model": GEN_MODEL,
        "pipeline_commit": os.environ.get("MAXWELL_COMMIT", "uncommitted"),
        "inputs": {
            "ruler_sheet": {"path": cfg["ruler_sheet"], "sha256": sha256_file(ROOT / cfg["ruler_sheet"]),
                            "rows": len(ruler)},
            "store": {"path": cfg["store"], "sha256": sha256_file(ROOT / cfg["store"]),
                      "table": cfg["store_table"], "rows": len(raw_names)},
        },
        "join": {"key": "content_name", "normalization": cfg["normalization"], "counts": res["counts"],
                 "ambiguous": res["ambiguous"], "unresolved": res["unresolved"]},
        "entries": res["entries"],
        "golden_join": read_golden(cfg, index),
        "declared_unresolved": cfg.get("declared_unresolved") or [],
        "declared_golden_unjoined": cfg.get("declared_golden_unjoined") or [],
    }


def strip_volatile(doc: dict) -> dict:
    """Drop the fields that legitimately change between two derivations (a commit stamp, a digest of a LIVE file)
    so --check compares DECISIONS, not noise."""
    clone = json.loads(json.dumps(doc))
    clone.pop("pipeline_commit", None)
    clone.get("inputs", {}).get("store", {}).pop("sha256", None)
    return clone


def verdict(doc: dict, cfg: dict) -> Tuple[int, str]:
    """Tri-state verdict for a freshly derived document."""
    c, j = doc["join"]["counts"], doc["join"]
    if c["ambiguous"]:
        return EXIT_DRIFT, f"{c['ambiguous']} AMBIGUOUS row(s) - a name matching two corpus rows is never picked"
    extra = sorted(set(j["unresolved"]) - set(cfg.get("declared_unresolved") or []))
    if extra:
        return EXIT_DRIFT, f"{len(extra)} UNDECLARED unresolved row(s): {extra[:8]}"
    if j["unresolved"]:
        return EXIT_OWED, f"{len(j['unresolved'])} unresolved row(s), all DECLARED in config"
    # GOLDEN side - the SAME rule as the corpus side (BUG-551). Before the declared ceiling existed, ANY unjoined
    # golden row exited 2 while the config declared nothing: the verdict claimed a declaration nobody made and a
    # real receiving-side breakage would have been filed as owner-owed instead of DRIFT.
    gdecl = [d for d in (cfg.get("declared_golden_unjoined") or []) if isinstance(d, dict)]
    gthin = [str(d.get("id")) for d in gdecl if len(str(d.get("why") or "").strip()) < MIN_WHY]
    if gthin:
        return EXIT_DRIFT, f"declared_golden_unjoined entr(y/ies) carry no adequate why: {gthin[:4]}"
    gdecl_ids = {str(d.get("id")) for d in gdecl}
    gunjoined = list(doc["golden_join"]["unjoined"])
    gundeclared = sorted(set(gunjoined) - gdecl_ids)
    if gundeclared:
        return EXIT_DRIFT, (f"golden: {len(gundeclared)} UNDECLARED unjoined row(s): {gundeclared[:8]} - an "
                            f"unjoined golden row is a BRIDGE GAP (BUG-551), not owner-owed until config declares it")
    gstale = sorted(gdecl_ids - set(gunjoined))
    if gstale:
        return EXIT_OWED, (f"golden: declared_golden_unjoined names {len(gstale)} row(s) that now JOIN "
                           f"({gstale[:4]}) - a declaration that no longer applies is OWNER-OWED; shrink the ceiling")
    if gunjoined:
        return EXIT_OWED, f"golden: {len(gunjoined)} row(s) unjoined, all DECLARED in config ({gunjoined[:4]})"
    return EXIT_CLEAN, (f"{c['joined']}/{c['rows']} anchor rows bridged (exact {c['exact']}, "
                        f"normalised {c['normalized']}); golden {doc['golden_join']['joined']}/"
                        f"{doc['golden_join']['rows']} joined")


def write_doc(path: Path, doc: dict) -> None:
    """Crash-safe write (C6): tempfile -> fsync -> os.replace."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{PREFIX}_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=JSON_INDENT, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def selftest() -> int:
    """Known-answer controls: every rule the join depends on gets a case that FAILS if the rule is inverted."""
    cfg = {"normalization": "collapse_whitespace", "item_key": "item_id", "store_name_column": "name"}
    ruler = [{"item_id": "R001", "name": "Alpha"}, {"item_id": "R002", "name": "Beta Gamma"},
             {"item_id": "R003", "name": "Delta"}, {"item_id": "R004", "name": "Ghost"}]
    index = {"alpha": ["F1"], "beta gamma": ["F2"], "delta": ["F3", "F3b"]}
    raw = {"F1": "Alpha", "F2": "Beta  Gamma", "F3": "Delta", "F3b": "Delta"}
    res = resolve(ruler, index, cfg, raw)
    c = res["counts"]
    clean = {"join": {"counts": dict(c, joined=3, exact=3, normalized=0, ambiguous=0, unresolved=0), "unresolved": []},
             "golden_join": {"unjoined": [], "joined": 1, "rows": 1}}
    un = json.loads(json.dumps(clean)); un["join"]["unresolved"] = ["R004"]
    amb = json.loads(json.dumps(clean)); amb["join"]["counts"]["ambiguous"] = 1
    g_un = json.loads(json.dumps(clean)); g_un["golden_join"]["unjoined"] = ["G9"]
    g_decl = {"declared_golden_unjoined": [{"id": "G9", "why": "declared: the name matches two corpus rows, so the bridge refuses to pick (owner-owed)"}]}
    g_thin = {"declared_golden_unjoined": [{"id": "G9", "why": "declared"}]}
    cases: List[Tuple[str, Any, Any]] = [
        ("exact join counted", c["exact"], 1),
        ("normalised join counted", c["normalized"], 1),
        ("ambiguity RECORDED, never picked", c["ambiguous"], 1),
        ("unresolved counted", c["unresolved"], 1),
        ("entries exclude ambiguous+unresolved", c["joined"], 2),
        ("join is by content, not position", res["entries"]["F1"]["item_id"], "R001"),
        ("ambiguity lists candidates", res["ambiguous"][0]["candidates"], ["F3", "F3b"]),
        ("norm folds whitespace", norm_name("a  b\tc", "collapse_whitespace"), "a b c"),
        ("norm folds case", norm_name("Alpha", "collapse_whitespace"), "alpha"),
        ("clean exits 0", verdict(clean, {})[0], EXIT_CLEAN),
        ("undeclared unresolved exits 1", verdict(un, {})[0], EXIT_DRIFT),
        ("DECLARED unresolved exits 2", verdict(un, {"declared_unresolved": ["R004"]})[0], EXIT_OWED),
        ("ambiguity exits 1", verdict(amb, {})[0], EXIT_DRIFT),
        ("golden unjoined UNDECLARED exits 1", verdict(g_un, {})[0], EXIT_DRIFT),
        ("golden unjoined DECLARED exits 2", verdict(g_un, g_decl)[0], EXIT_OWED),
        ("a declaration without an adequate why exits 1", verdict(g_un, g_thin)[0], EXIT_DRIFT),
        ("a declaration whose row now JOINS is owner-owed (shrink-only)", verdict(clean, g_decl)[0], EXIT_OWED),
        ("volatile stamp ignored", "pipeline_commit" in strip_volatile({"pipeline_commit": "a", "inputs": {}}), False),
    ]
    bad = 0
    for label, got, want in cases:
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            bad += 1
    try:
        norm_name("x", "invent_a_mode")
        print("  FAIL an undeclared normalization mode was accepted")
        bad += 1
    except ValueError:
        pass
    print(f"{PREFIX} selftest: {len(cases) + 1 - bad}/{len(cases) + 1} controls passed")
    return EXIT_CLEAN if bad == 0 else EXIT_DRIFT


def main(argv: Optional[List[str]] = None) -> int:
    """CLI: build (default) | --check | --selftest | --print-config."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="anchor-family <-> corpus bridge (BUG-420)")
    ap.add_argument("--check", action="store_true", help="re-derive and compare against the committed artifact")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls and exit")
    ap.add_argument("--print-config", action="store_true", help="print the declared configuration and exit")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    cfg = load_config()
    if args.print_config:
        print(yaml.safe_dump(cfg, sort_keys=True))
        return EXIT_CLEAN
    doc = build(cfg)
    code, why = verdict(doc, cfg)
    path = ROOT / cfg["artifact"]
    if args.check:
        if not path.exists():
            print(f"{PREFIX}: DRIFT - {cfg['artifact']} does not exist; run without --check to derive it")
            return EXIT_DRIFT
        if strip_volatile(json.loads(path.read_text(encoding="utf-8"))) != strip_volatile(doc):
            print(f"{PREFIX}: DRIFT - the committed bridge no longer re-derives (a join, a name or an input moved)")
            return EXIT_DRIFT
        print(f"{PREFIX}: ok {why}")
        return code
    write_doc(path, doc)
    print(f"{PREFIX}: wrote {cfg['artifact']} - {why}")
    return code


if __name__ == "__main__":
    sys.exit(main())
