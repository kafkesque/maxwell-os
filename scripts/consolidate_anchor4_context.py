#!/usr/bin/env python3
"""ANCHOR-4 context consolidation - DERIVE the CT/DISC/FORM context columns of the ANCHOR-4
depth blind sheet from ANCHOR-3 instead of copying the pre-consolidation raw ruler.

Why (BUG-421): ANCHOR-4 was built by copying the RAW ruler columns (RULER_BLIND_SHEET_20260917)
before the F-11 consolidation produced the *_final values in ANCHOR-3. Result: 56/150 content_type,
34/150 discipline and 142/150 extraction_type cells in the blind sheet were SUPERSEDED, and 28 DISC
plus 5 FORM cells were blank although ANCHOR-3 carries a value for every row. A blind coding sheet
whose context is more than half stale is not a valid instrument.

One artifact, one writer (the BUG-402 lesson): ANCHOR-3 OWNS content_type/discipline/extraction_type;
ANCHOR-4 DERIVES the three context columns, and this script is their only writer.

Usage:
  python3 scripts/consolidate_anchor4_context.py --apply    # backup, refresh, write key + manifest
  python3 scripts/consolidate_anchor4_context.py --check    # exit 1 on any drift (wire into just health)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
from collections import Counter
from typing import Dict, List, Tuple

REPO = pathlib.Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO / "governance" / "ANCHOR4_MANIFEST_20260924.json"
EXIT_DRIFT = 1
CONTEXT_COLUMNS = (("CT (1-7)", "ct"), ("DISC (1-62)", "disc"), ("FORM (1-4)", "form"))


def norm_name(value: str) -> str:
    """Normalise a row name for a name join: casefold, strip punctuation runs, collapse spaces."""
    import re
    import unicodedata

    s = unicodedata.normalize("NFKD", value or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def diff_against_backup(man: dict) -> Dict[str, int]:
    """Count the context cells that differ between the pre-refresh backup and the live sheet.

    This makes the change record a DERIVATION from the artefacts rather than a hand-typed count
    (a hand-typed count is a second clock for one artifact - the BUG-402 / BUG-418 rule).
    """
    backup = REPO / man["sheet"]["backup"]
    if not backup.exists():
        return {}
    sheet_path = REPO / man["sheet"]["path"]
    enc = man["sheet"]["encoding"]
    with open(backup, newline="", encoding=enc) as fh:
        before = {r[0].strip(): r for r in list(csv.reader(fh))[1:] if r and r[0].strip()}
    with open(sheet_path, newline="", encoding=enc) as fh:
        rows = list(csv.reader(fh))
    idx = {name: i for i, name in enumerate(rows[0])}
    changed: Counter = Counter()
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        old = before.get(r[0].strip())
        if not old:
            continue
        for col, _ in CONTEXT_COLUMNS:
            if old[idx[col]].strip() != r[idx[col]].strip():
                changed[col] += 1
    return dict(changed)


def sha256_file(path: pathlib.Path) -> str:
    """Return the hex sha256 of a file, read in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: pathlib.Path, encoding: str = "utf-8") -> List[Dict[str, str]]:
    """Read a CSV into a list of dicts, tolerating the family's mixed encodings."""
    with open(path, newline="", encoding=encoding) as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def load_manifest() -> dict:
    """Load the ANCHOR-4 manifest - the config surface for every path this script touches (C12)."""
    if not MANIFEST_PATH.exists():
        raise SystemExit("manifest missing: %s" % MANIFEST_PATH.relative_to(REPO))
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def upstream_finals(man: dict) -> Dict[str, Dict[str, str]]:
    """Return item_id -> {ct,disc,form} taken from ANCHOR-3's *_final columns."""
    m = man["upstream"]
    out: Dict[str, Dict[str, str]] = {}
    for r in read_csv(REPO / m["path"]):
        out[r["item_id"].strip()] = {
            "ct": (r.get(m["columns"]["content_type"]) or "").strip(),
            "disc": (r.get(m["columns"]["discipline"]) or "").strip(),
            "form": (r.get(m["columns"]["extraction_type"]) or "").strip(),
        }
    return out


def refresh_cells(
    man: dict, ups: Dict[str, Dict[str, str]]
) -> Tuple[List[List[str]], Dict[str, int], List[str]]:
    """Return the sheet rows with the three context cells refreshed, change counts and problems."""
    sheet_path = REPO / man["sheet"]["path"]
    with open(sheet_path, newline="", encoding=man["sheet"]["encoding"]) as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    body = [r for r in rows[1:] if r and r[0].strip() != ""]
    idx = {name: i for i, name in enumerate(header)}
    changed: Counter = Counter()
    problems: List[str] = []
    for r in body:
        item = r[idx["item_id"]].strip()
        if item not in ups:
            problems.append("sheet item_id not in upstream: %s" % item)
            continue
        for col, key in CONTEXT_COLUMNS:
            new = ups[item][key]
            if new != r[idx[col]].strip():
                changed[col] += 1
                r[idx[col]] = new
    return [header] + body, dict(changed), problems


def write_csv(path: pathlib.Path, rows: List[List[str]], lineterminator: str) -> None:
    """Crash-safe CSV write: tempfile -> fsync -> os.replace (C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".anchor4_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh, lineterminator=lineterminator).writerows(rows)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def build_key(man: dict, names: Dict[str, str]) -> dict:
    """Build the sidecar prediction key: item_id -> corpus fb_id bridge plus depth values that
    ALREADY exist in the reference artefacts. Never shown to a coder (rubric blinding rule)."""
    gold = {
        json.loads(l)["fb_id"]: json.loads(l)
        for l in open(REPO / man["key"]["gold"], encoding="utf-8")
        if l.strip()
    }
    dvote = {
        json.loads(l)["fb_id"]: json.loads(l)
        for l in open(REPO / man["key"]["depth_vote"], encoding="utf-8")
        if l.strip()
    }
    by_name: Dict[str, str] = {v.strip().lower(): k for k, v in names.items()}
    by_norm: Dict[str, List[str]] = {}
    for fb, rec in list(gold.items()) + list(dvote.items()):
        by_norm.setdefault(norm_name(rec.get("name", "")), []).append(fb)
    bridge: Dict[str, dict] = {}
    for carrier in man["key"]["carriers"]:
        for r in read_csv(REPO / carrier["path"], carrier.get("encoding", "utf-8")):
            fb = (r.get("fb_id") or "").strip()
            if not fb:
                continue
            item = (r.get("item_id") or "").strip()
            src = carrier["path"]
            if item in names:
                bridge.setdefault(item, {"fb_id": fb, "fb_id_source": src})
                continue
            hit = by_name.get((r.get("name") or "").strip().lower())
            if hit:
                bridge.setdefault(hit, {"fb_id": fb, "fb_id_source": src + " (name join)"})
    entries: Dict[str, dict] = {}
    for iid, nm in names.items():
        rec = {"name": nm}
        rec.update(bridge.get(iid, {}))
        fb = rec.get("fb_id")
        if fb and fb in gold and (gold[fb].get("depth") or "").strip():
            src = str(gold[fb].get("depth_source"))
            rec["depth_ref"] = gold[fb]["depth"]
            rec["depth_ref_source"] = "gold_4axis:" + src
            rec["depth_ref_tier"] = "human-derived" if "human" in src else "llm-advisory"
        elif fb and fb in dvote and (dvote[fb].get("depth") or "").strip():
            rec["depth_ref"] = dvote[fb]["depth"]
            rec["depth_ref_source"] = "depth_vote:consensus(%s/%s reliable)" % (
                dvote[fb].get("n_reliable_ok"),
                dvote[fb].get("n_voters"),
            )
            rec["depth_ref_tier"] = "llm-advisory"
        # A weaker, clearly-labelled join: the reference artefact keyed by NAME only. Identity is NOT
        # verified for these rows, so they are recorded separately and never mixed with the fb_id join.
        if not rec.get("depth_ref"):
            for label, src_map, src_name in (
                ("gold_4axis", gold, "gold_4axis:name join (identity UNVERIFIED)"),
                ("depth_vote", dvote, "depth_vote:name join (identity UNVERIFIED)"),
            ):
                cand = by_norm.get(norm_name(nm), [])
                if cand and cand[0] in src_map and (src_map[cand[0]].get("depth") or "").strip():
                    ref = src_map[cand[0]]
                    rec["depth_ref_namejoin"] = ref["depth"]
                    rec["depth_ref_namejoin_source"] = src_name + ":" + str(
                        ref.get("depth_source") or ref.get("consensus")
                    )
                    rec["depth_ref_namejoin_tier"] = (
                        "human-derived" if "human" in str(ref.get("depth_source")) else "llm-advisory"
                    )
                    break
        if rec.get("depth_ref") or rec.get("depth_ref_namejoin") or fb:
            entries[iid] = rec
    return {
        "schema_version": "1.0",
        "artifact_id": "ANCHOR-4-KEY",
        "blinding": (
            "DO NOT SHOW THIS FILE TO A CODER. It carries the corpus fb_id bridge and the depth values "
            "that already exist in gold_4axis / depth_vote_checkpoint. Its purpose is a PRE-REGISTERED "
            "prediction check: after the blind coding freezes, compare the coder output against depth_ref "
            "to measure the advisory references' error rate on this row family. Consulting it during "
            "coding destroys the anchor (rubric blinding rule)."
        ),
        "primary_key": "item_id (anchor family); fb_id (corpus family)",
        "rows_in_sheet": len(names),
        "rows_with_fb_id": sum(1 for v in entries.values() if v.get("fb_id")),
        "rows_with_depth_ref": sum(1 for v in entries.values() if v.get("depth_ref")),
        "rows_with_depth_ref_namejoin": sum(1 for v in entries.values() if v.get("depth_ref_namejoin")),
        "entries": entries,
    }


def check(man: dict, ups: Dict[str, Dict[str, str]]) -> int:
    """Exit 1 on any drift: context cells, item_id set, key set, manifest digest, depth still blind."""
    problems: List[str] = []
    _, changed, issues = refresh_cells(man, ups)
    problems += issues
    for col, n in changed.items():
        problems.append("DRIFT: %d %s cell(s) differ from upstream %s" % (n, col, man["upstream"]["path"]))
    sheet = read_csv(REPO / man["sheet"]["path"], man["sheet"]["encoding"])
    items = [r["item_id"].strip() for r in sheet]
    if len(items) != len(set(items)):
        problems.append("DRIFT: duplicate item_id in the sheet")
    if set(items) != set(ups):
        problems.append(
            "DRIFT: sheet item_id set != upstream item_id set (%d vs %d)"
            % (len(set(items)), len(set(ups)))
        )
    for r in sheet:
        if (r.get("DEPTH (1-4)") or "").strip():
            problems.append("DRIFT: DEPTH already filled on %s - the sheet is no longer blind" % r["item_id"])
            break
    key_path = REPO / man["key"]["path"]
    if not key_path.exists():
        problems.append("DRIFT: key file missing: %s" % man["key"]["path"])
    else:
        with open(key_path, encoding="utf-8") as fh:
            key = json.load(fh)
        if set(key.get("entries", {})) - set(items):
            problems.append("DRIFT: key carries item_ids that are not in the sheet")
    digest = sha256_file(REPO / man["sheet"]["path"])
    if digest != man["sheet"]["sha256"]:
        problems.append("DRIFT: sheet sha256 %s != manifest %s" % (digest[:16], man["sheet"]["sha256"][:16]))
    if problems:
        print("ANCHOR-4 context DRIFT - %d problem(s):" % len(problems))
        for p in problems:
            print("  -", p)
        return EXIT_DRIFT
    print(
        "ANCHOR-4 context in sync - %d rows, CT/DISC/FORM derived from %s, sha256 %s"
        % (len(items), man["upstream"]["path"], digest[:16])
    )
    return 0


def apply(man: dict, ups: Dict[str, Dict[str, str]]) -> dict:
    """Write the backup, the refreshed sheet, the key and the manifest. Idempotent by test."""
    sheet_path = REPO / man["sheet"]["path"]
    before_digest = sha256_file(sheet_path)
    backup = REPO / man["sheet"]["backup"]
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(sheet_path, backup)
    rows, changed, issues = refresh_cells(man, ups)
    if issues:
        raise SystemExit("refusing to write - upstream/sheet mismatch: %s" % issues[:5])
    term = "\r\n" if b"\r\n" in sheet_path.read_bytes() else "\n"
    write_csv(sheet_path, rows, term)
    names = {r[1].strip(): r[2].strip() for r in rows[1:]}
    key = build_key(man, names)
    with open(REPO / man["key"]["path"], "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    man["sheet"]["sha256"] = sha256_file(sheet_path)
    man["sheet"]["bytes"] = sheet_path.stat().st_size
    man["sheet"]["rows"] = len(rows) - 1
    man["sheet"]["columns"] = len(rows[0])
    man["key"]["sha256"] = sha256_file(REPO / man["key"]["path"])
    prior = man.get("context_refresh")
    recorded = diff_against_backup(man) or changed
    if recorded:
        man["context_refresh"] = {
            "date": "2026-09-24",
            "upstream": man["upstream"]["path"],
            "reason": (
                "BUG-421: the sheet carried the PRE-consolidation raw ruler columns; a blind sheet whose "
                "context is more than half stale is not a valid instrument"
            ),
            "cells_refreshed": recorded,
            "from_sha256": sha256_file(backup) if backup.exists() else before_digest,
            "to_sha256": man["sheet"]["sha256"],
            "writer": "scripts/consolidate_anchor4_context.py",
            "note": "cells_refreshed is DERIVED by diffing the backup against the sheet, and a later "
                    "no-op re-run must not erase it (the BUG-418 idempotency rule)",
        }
        if prior and prior.get("from_sha256") and not backup.exists():
            man["context_refresh"]["from_sha256"] = prior["from_sha256"]
    with open(MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("refreshed %s (%d rows, %d cols)" % (man["sheet"]["path"], len(rows) - 1, len(rows[0])))
    print("cells refreshed:", changed if changed else "none (already in sync)")
    print(
        "key: %s | rows_with_fb_id=%d rows_with_depth_ref=%d"
        % (man["key"]["path"], key["rows_with_fb_id"], key["rows_with_depth_ref"])
    )
    return changed


INTERIM_PATH = REPO / "config" / "anchor4_interim_state.json"


def interim_exemption() -> str:
    """Return a reason string if config/ declares an interim state whose bug is still OPEN.

    Fail-closed on purpose: the declaration is honoured ONLY when the named bug exists and is OPEN in the
    machine register, so the guard cannot be silenced by editing config alone (BUG-433). An unreadable or
    malformed declaration is treated as NO exemption.
    """
    if not INTERIM_PATH.exists():
        return ""
    try:
        cfg = json.loads(INTERIM_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        print("interim state file unreadable (%s) - no exemption" % exc)
        return ""
    bug = str(cfg.get("bug") or "")
    try:
        reg = json.loads((REPO / "governance" / "bug_status.json").read_text(encoding="utf-8"))
        open_ids = {b["id"] if isinstance(b, dict) else b for b in (reg.get("open") or [])}
    except Exception:
        return ""
    if bug and bug in open_ids:
        return "%s declared pending owner gate (%s is OPEN)" % (cfg.get("state"), bug)
    return ""


def main() -> int:
    """Parse args and run --apply or --check."""
    ap = argparse.ArgumentParser(description="ANCHOR-4 context consolidation (BUG-421)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true", help="refresh context columns, write key + manifest")
    g.add_argument("--check", action="store_true", help="exit 1 if the sheet drifted from ANCHOR-3")
    ap.add_argument("--strict", action="store_true", help="ignore any declared interim state (fail-closed test)")
    a = ap.parse_args()
    man = load_manifest()
    ups = upstream_finals(man)
    if a.apply:
        apply(man, ups)
        return 0
    code = check(man, ups)
    if code and not a.strict:
        reason = interim_exemption()
        if reason:
            print("WARN ANCHOR-4 context: %s" % reason)
            print("     drift is EXPECTED here; the one-time fix is the owner-gated promotion of the locked drop-in")
            print("     receipt: governance/ANCHOR4_DEPTH_OWNER_PASS_EVALUATION_20260924.md")
            return 0
    return code


if __name__ == "__main__":
    sys.exit(main())
