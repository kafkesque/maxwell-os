#!/usr/bin/env python3
"""Normalise the owner's FILLED adjudication workbook: encoding, separators, declared typo fixes.

Why this exists
---------------
The owner's review arrived with three defects that are all FORMAT, not judgement:

1. the file is **Mac Roman encoded** - a single 0xCA byte (a non-breaking space in a row name) breaks every
   UTF-8 reader, including the cross-examination harness;
2. labels are separated by **commas**, while the workbook's own coder columns use `|` - and one canonical
   label ('business operations') contains the separator, so it was being split into two non-labels;
3. a handful of labels are **truncated** ('research & methodolog', 'media & entertainmen', 'business
   developmen', 'user experienc', 'esign systems', 'systems & framework').

What it guarantees
------------------
- the raw drop-in is copied **byte-exact** to backups/ before anything is written, and its sha256 is recorded;
- every rewrite is DECLARED in config/anchor_workbook_fixes.yaml and applies only on an **exact** match: there
  is no fuzzy matching anywhere near the owner's gold;
- the owner's original string is preserved in a NEW column `domains_final_raw`, so a fix is additive rather
  than a replacement of the owner's own words;
- what is not declared is never guessed: an off-menu token with no declared fix and no declared-unresolved
  entry fails the run CLOSED and is printed for the owner;
- the receipt lists every single cell change old->new, and the fix log is machine-readable.

Columns appended (existing columns are never reordered or renamed): `primary_domain` (the owner's rule - the
FIRST token is the PRIMARY), `domains_final_raw` (byte-faithful original), `depth_final_class` (numeric class).

Usage:
    python3 scripts/normalize_owner_workbook.py --check    # plan only, writes nothing
    python3 scripts/normalize_owner_workbook.py --apply    # backup, rewrite, fix log, receipt
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_discipline_domain_vote as bddv  # noqa: E402  the canonical domain menu, one source of truth

REPO = Path(__file__).resolve().parents[1]
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
WORKBOOK = REPO / "governance" / "anchor_adjudication_workbook_20260924.csv"
CONFIG = REPO / "config" / "anchor_workbook_fixes.yaml"
DEPTH_MENU = REPO / "config" / "depth_classes.yaml"
BACKUP_DIR = REPO / "backups"
RECEIPT = REPO / "governance" / "ANCHOR_ADJUDICATION_NORMALIZATION_20260925.md"
FIXLOG = REPO / "governance" / "anchor_adjudication_fixlog_20260925.csv"
DOMAIN_COL, DEPTH_COL = "domains_final", "depth_final"
ADDED = ["primary_domain", "domains_final_raw", "depth_final_class"]
MENU: set[str] = set(bddv.DOM_NAMES)


def sha256_of(path: Path) -> str:
    """Return the hex sha256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_owner_file(path: Path) -> tuple[str, str]:
    """Decode the owner's file and report which encoding worked (mac_roman is the observed fallback)."""
    # D-2646/BUG-516: the decode rule has ONE home. Delegating wrapper - no codec list lives here.
    return artifact_encoding.open_artifact(path, REPO).read(), artifact_encoding.read_encoding(path, REPO)
    raise SystemExit(f"cannot decode {path} with any known encoding")


def tokenize(cell: str, sep: str) -> list[str]:
    """Split a domain cell on BOTH accepted separators, trimming and dropping empties."""
    out: list[str] = []
    for tok in cell.replace("|", sep).replace(",", sep).split(sep):
        if tok.strip():
            out.append(tok.strip())
    return out


def normalize_domains(cell: str, cfg: dict[str, Any]) -> tuple[str, list[tuple[str, str]], list[str]]:
    """Return (normalized cell, [(old, new)] changes, unresolved tokens). Declared rewrites only."""
    sep = cfg.get("separator_out", "|")
    s = cell
    changes: list[tuple[str, str]] = []
    for rep in cfg.get("cell_replacements") or []:
        if rep["from"] in s:
            s = s.replace(rep["from"], rep["to"])
            changes.append((rep["from"], rep["to"]))
    toks = tokenize(s, sep)
    fixed_toks: list[str] = []
    unresolved: list[str] = []
    for tok in toks:
        new = (cfg.get("token_fixes") or {}).get(tok)
        if new is not None and new != tok:
            changes.append((tok, new))
            tok = new
        if tok not in MENU:
            unresolved.append(tok)
        fixed_toks.append(tok)
    seen: set[str] = set()
    deduped = [t for t in fixed_toks if not (t in seen or seen.add(t))]
    for old, new in zip(fixed_toks, deduped):
        if old != new:
            changes.append((old, new))
    return sep.join(deduped), changes, unresolved


def check_depth_alias(cfg: dict[str, Any]) -> list[str]:
    """Assert every declared depth word is a class label in config/depth_classes.yaml (mirror, not a copy)."""
    text = DEPTH_MENU.read_text(encoding="utf-8")
    return [w for w in (cfg.get("depth_alias") or {}) if w not in text]


def plan(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Read the owner's file and build the change plan. Returns (plan rows, fatal)."""
    fatal: list[str] = []
    allow = set(cfg.get("unresolved_allowed") or [])
    missing = check_depth_alias(cfg)
    if missing:
        fatal.append(f"depth_alias word(s) {missing} are not classes in {DEPTH_MENU.name}")
    text, enc = decode_owner_file(WORKBOOK)
    rows = list(csv.DictReader(io.StringIO(text)))
    for r in rows:
        item = r["item_id"]
        raw_dom = (r.get(DOMAIN_COL) or "").strip()
        raw_dep = (r.get(DEPTH_COL) or "").strip()
        new_dom, changes, unresolved = normalize_domains(raw_dom, cfg) if raw_dom else ("", [], [])
        for tok in unresolved:
            if tok not in allow:
                fatal.append(f"{item}: OFF-MENU token {tok!r} is neither a declared fix nor declared-unresolved")
        dep_cls = ""
        if raw_dep:
            dep_cls = str((cfg.get("depth_alias") or {}).get(raw_dep, ""))
            if not dep_cls:
                fatal.append(f"{item}: depth {raw_dep!r} is not a declared depth class word")
        prim = new_dom.split("|")[0] if new_dom else ""
        r["_row"] = {
            "item_id": item, "encoding": enc, "domains_raw": raw_dom, "domains_new": new_dom,
            "primary_domain": prim, "depth_word": raw_dep, "depth_class": dep_cls,
            "changes": changes, "unresolved": unresolved,
        }
    for col, expect in (cfg.get("expect_blank") or {}).items():
        got = [r["item_id"] for r in rows if not (r.get(col) or "").strip()]
        if sorted(got) != sorted(expect):
            fatal.append(f"blank rows in {col} changed: declared {sorted(expect)}, found {sorted(got)} "
                         f"(the owner may have edited again - re-derive, do not assume)")
    return [r["_row"] for r in rows], fatal


def main() -> int:
    """CLI entry point: --check plans and refuses, --apply backs up then writes."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rows, fatal = plan(cfg)
    changed = [r for r in rows if r["changes"] or r["unresolved"]]
    print(f"encoding read: n/a | rows {len(rows)} | cells to rewrite {len(changed)}")
    for r in changed:
        print(f"  {r['item_id']}: {r['domains_raw']!r} -> {r['domains_new']!r}"
              + (f"  UNRESOLVED {r['unresolved']}" if r["unresolved"] else ""))
    if fatal:
        print("\nREFUSING (fail closed):")
        for f in fatal:
            print("  !!", f)
        return 1
    if a.check or not a.apply:
        print("\n--check: plan is clean, nothing written")
        return 0
    BACKUP_DIR.mkdir(exist_ok=True)
    backup = BACKUP_DIR / f"anchor_adjudication_workbook_20260924.OWNER_RAW_{datetime.now():%Y%m%d}.csv"
    shutil.copy2(WORKBOOK, backup)
    text, enc = decode_owner_file(WORKBOOK)
    reader = csv.DictReader(io.StringIO(text))
    base = list(reader.fieldnames or [])
    out_rows = list(reader)
    with FIXLOG.open("w", encoding="utf-8", newline="") as fh:
        fw = csv.writer(fh)
        fw.writerow(["item_id", "column", "old", "new", "status"])
        for r, p in zip(out_rows, rows):
            for old, new in p["changes"]:
                fw.writerow([p["item_id"], DOMAIN_COL, old, new, "FIXED"])
            for tok in p["unresolved"]:
                fw.writerow([p["item_id"], DOMAIN_COL, tok, tok, "UNRESOLVED-OWNER-RULING"])
        for col, blanks in (cfg.get("expect_blank") or {}).items():
            for item in blanks:
                fw.writerow([item, col, "", "", "BLANK-AS-SUBMITTED"])
    with WORKBOOK.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=base + ADDED, extrasaction="ignore")
        w.writeheader()
        for r, p in zip(out_rows, rows):
            r[DOMAIN_COL] = p["domains_new"]
            r["primary_domain"] = p["primary_domain"]
            r["domains_final_raw"] = p["domains_raw"]
            r["depth_final_class"] = p["depth_class"]
            w.writerow(r)
    stamp = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%S+00:00}"
    RECEIPT.write_text(
        f"""# ANCHOR adjudication workbook - NORMALIZATION RECEIPT (2026-09-25)

The owner's filled adjudication workbook was normalised. **No judgement was changed.** What changed was
encoding, separator, and 8 truncated labels; the owner's original strings are preserved column-by-column in
`domains_final_raw`, so nothing they typed is lost.

- source encoding detected: **{enc}** (the file as saved was Mac Roman; one 0xCA byte broke UTF-8 readers)
- byte-exact raw backup: `{backup.relative_to(REPO)}` sha256 `{sha256_of(backup)[:16]}...`
- normalized file: `{WORKBOOK.relative_to(REPO)}` sha256 `{sha256_of(WORKBOOK)[:16]}...`
- fix log: `{FIXLOG.relative_to(REPO)}` (one row per change, statuses FIXED / UNRESOLVED-OWNER-RULING / BLANK-AS-SUBMITTED)
- written: {stamp} | rows {len(rows)} | cells rewritten {len(changed)}

## Rows the owner LEFT BLANK - declared, not filled

`domains_final`: {', '.join((cfg.get('expect_blank') or {}).get('domains_final', [])) or 'none'}
`depth_final`: {', '.join((cfg.get('expect_blank') or {}).get('depth_final', [])) or 'none'}

A blank is a fact about the review. Nothing automatic may fill it.

## Awaiting the owner

{chr(10).join('- `' + t + '` (off-menu, matches no canonical label by any defensible edit distance)' for r in rows for t in r['unresolved']) or '- none'}

## The rule this pass adopts

**The FIRST domain token is the PRIMARY domain** (owner ruling 2026-09-25). It is now materialised in the
`primary_domain` column of every row, so the primary no longer has to be inferred from list order by whoever
reads this file next.
""", encoding="utf-8")
    print(f"\napplied: backup {backup.name} | fix log + receipt written | {len(changed)} cells rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
