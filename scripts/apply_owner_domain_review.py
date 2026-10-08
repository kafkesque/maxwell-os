#!/usr/bin/env python3
"""apply_owner_domain_review.py — re-derive and verify the frozen DOMAIN ruler from the OWNER's review sheet.

WHY (BUG-674 / BUG-675 / BUG-678). The frozen domain ruler (governance/DOMAIN_RULER_FROZEN_*.json) is an
ONTOLOGY AUTHORITY: discipline = rigid kind, domain = anti-rigid application role (OntoClean, Guarino & Welty
2002); primary_domain MUST be domains[0]; per-FB cardinality is capped (D150). Two owner-gated sweeps were
applied to it by hand-scripts held in /tmp (volatile, unreproducible): 86 domain assignments merged from the
owner's Numbers review sheet (BUG-674) and the R141/R159 discipline rulings (BUG-675). Nothing in the repo
could re-derive either, so a future agent re-deriving from the DERIVED review CSV would SILENTLY lose them:
governance/DOMAIN_RULER_REVIEW_*.csv carries 0/46 oov_domains cells, 8 vs 11 owner_notes, and a domains
column that contradicts the ruler on 42/201 rows (BUG-678).

THE RULE (measured against the frozen artifact, not invented):
    base      = the consolidated anchor's domain cell, in cell order (abstention token dropped)
    additions = the OWNER sheet's oov_domains cell, in CELL ORDER, each token alias-resolved
                (exact -> surface alias -> unique prefix -> art. split -> longest-first greedy fallback)
    removals  = owner directives from config (remove_domains)
    cap       = pipeline_config.max_domains_per_fb, applied LAST and REPORTED, never silently
    primary   = the owner override, MOVED TO FRONT; otherwise base[0]
    drops     = explicit owner-directed removals (remove_domains) - since D-2878 EVERY cap overshoot is
                resolved by an APPLICABILITY-RANKED removal, never by positional (tail) truncation
    abstain   = rows the owner CONFIRMED as abstentions carry discipline='' + a declared id in
                discipline_abstention (BUG-676: 'emerging' is an axis-level verdict, not a menu value)
The owner's owner_notes column is NOT a domain source: it carries the owner's directives (primary /
removal / discipline) and open QUESTIONS (R005, R113) which were deliberately NOT assigned.

MODES:
  --export-source   .numbers -> faithful 9-column CSV + sha256 pin (the durable face of the owner sheet)
  --check           re-derive in memory; assert the ruler ON DISK is canonical-byte-identical (no drift)
  --apply           re-derive and write crash-safe (tempfile -> fsync -> os.replace), re-stamping sha256

Deterministic data transform, LLM-free (R5 not implicated) — same class as scripts/remint_anchor2_v8.py.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULINGS = ROOT / "config" / "owner_domain_rulings_20261008.yaml"
PIPELINE_CONFIG = ROOT / "config" / "pipeline_config.yaml"
COLUMNS = ("item_id", "name", "discipline", "n_domains", "domains", "primary_domain",
           "oov_domains", "owner_review", "owner_notes")
#: The owner sheet is a Numbers export: cells wrap, so multi-domain runs appear separated by '|', ',' or a
#: line-wrap artefact (' i '). Splitting on all three is what makes the cell order recoverable.
CELL_SPLIT = re.compile(r"\s*[|,;]\s*|\s+i\s+")
MIN_PREFIX = 5


def _cfg(rulings: Path | None = None) -> dict[str, Any]:
    """Load the owner rulings config (all rulings are data, never code — C12c)."""
    return yaml.safe_load((rulings or RULINGS).read_text(encoding="utf-8"))


def assert_notes_accounted(cfg: dict[str, Any], src: dict[str, dict[str, str]]) -> None:
    """Every owner_notes cell must be a DECLARED directive or a declared question.

    This is the guard that would have caught BUG-675 at commit time: R141 carried 'discipline is machine
    learning' in free text that NO config column carried, so the ruling was silently unapplied for a round.
    A sheet that grows a new unaccounted note now fails CLOSED instead of being quietly ignored (C16).
    """
    declared = set(cfg.get("owner_notes_accounted") or {})
    present = {i for i, r in src.items() if (r.get("owner_notes") or "").strip()}
    missing = sorted(present - declared)
    if missing:
        raise SystemExit("FAIL-CLOSED: owner_notes cell(s) carry no declared directive in "
                         "config/owner_domain_rulings_*.yaml#owner_notes_accounted: " + ", ".join(missing))
    stale = sorted(declared - present)
    if stale:
        raise SystemExit("FAIL-CLOSED: config declares owner_notes for row(s) that carry none: " + ", ".join(stale))


def assert_answers_pin(cfg: dict[str, Any]) -> None:
    """Fail-closed on the owner's round-2 answers sheet drifting from its recorded sha256.

    The sheet is an AUTHORITY (the round-2 adjudications are derived FROM it), so an edit-after-the-fact is a
    hard failure rather than a silent re-interpretation of what the owner approved.
    """
    spec = cfg.get("answers_sheet") or {}
    rel, want = spec.get("file"), spec.get("sha256")
    if not rel or not want:
        return
    got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    if got != want:
        raise SystemExit("FAIL-CLOSED: owner answers sheet " + str(rel) + " sha256 " + got[:16]
                         + " != recorded " + str(want)[:16] + " - the owner's answers were edited after "
                         "the rulings were derived from them")


def _canonical(payload: Any) -> str:
    """Canonical JSON of a payload: the exact form the artifact sha256 is taken over."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _sha(payload: Any) -> str:
    """sha256 of the canonical JSON of a payload."""
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def load_vocab() -> tuple[list[str], set[str], set[str]]:
    """Return (domain canonicals long-first, domain set, discipline set) from the live taxonomy."""
    tax = yaml.safe_load((ROOT / "config" / "taxonomy_v8.yaml").read_text(encoding="utf-8"))
    doms = [d["canonical"] for d in tax["domains"]]
    disc = {d["canonical"] for d in tax["disciplines"]}
    return sorted(doms, key=len, reverse=True), set(doms), disc


def cap_domains() -> int:
    """Read the per-FB domain cardinality cap from the declared knob (C12: never hardcoded)."""
    cfg = yaml.safe_load(PIPELINE_CONFIG.read_text(encoding="utf-8"))
    for section in cfg.values():
        if isinstance(section, dict) and "max_domains_per_fb" in section:
            return int(section["max_domains_per_fb"])
    raise SystemExit("FAIL-CLOSED: config/pipeline_config.yaml declares no max_domains_per_fb (D150 cap)")


def resolve_token(raw: str, long_first: list[str], canon: set[str], alias: dict[str, str]) -> list[str]:
    """Resolve ONE sheet cell fragment to canonical domain(s). NEVER silently drops an unknown token."""
    token = re.sub(r"\s+", " ", raw.strip().strip(".").strip()).lower()
    if not token:
        return []
    token = re.sub(r"^i\s+", "", token)
    if token in canon:
        return [token]
    if token in alias:
        return [alias[token]]
    prefixed = [c for c in canon if c.startswith(token) and len(token) >= MIN_PREFIX]
    if len(prefixed) == 1:
        return prefixed[0:1]
    found: list[str] = []
    hay = token
    for dom in long_first:  # longest-first fallback for no-separator runs ('business development entrepreneurship')
        if dom in hay:
            found.append(dom)
            hay = hay.replace(dom, " ")
    return found


def parse_cell(cell: str, long_first: list[str], canon: set[str], alias: dict[str, str]) -> list[str]:
    """Parse an owner-sheet odometer cell into canonical domains, preserving CELL ORDER, deduped."""
    out: list[str] = []
    for raw in CELL_SPLIT.split(cell or ""):
        for dom in resolve_token(raw, long_first, canon, alias):
            if dom not in out:
                out.append(dom)
    return out


def export_source(rulings: Path | None = None) -> int:
    """Export the owner's .numbers sheet to a faithful 9-column CSV and pin its sha256."""
    from numbers_parser import Document

    cfg = _cfg(rulings)
    src = ROOT / cfg["source"]["numbers"]
    out = ROOT / cfg["source"]["export_csv"]
    raw_sha = hashlib.sha256(src.read_bytes()).hexdigest()
    if raw_sha != cfg["source"]["numbers_sha256"]:
        print("FAIL-CLOSED: .numbers sha256 moved: " + raw_sha + " != " + cfg["source"]["numbers_sha256"])
        return 1
    doc = Document(str(src))
    table = doc.sheets[0].tables[0]
    rows = [[c.value for c in r] for r in table.rows()]
    header = [str(v) if v is not None else "" for v in rows[0]]
    idx = {h: i for i, h in enumerate(header)}
    missing = [c for c in COLUMNS if c not in idx]
    if missing:
        print("FAIL-CLOSED: sheet is missing column(s): " + ", ".join(missing) + " (header: " + ", ".join(header) + ")")
        return 1
    body: list[list[str]] = []
    for r in rows[1:]:
        if not r[0]:
            continue
        body.append(["" if r[idx[c]] is None else str(r[idx[c]]).strip() for c in COLUMNS])
    text = "\n".join([",".join(COLUMNS)] + [",".join(_csv_cell(c) for c in b) for b in body]) + "\n"
    _crash_safe_write(out, text)
    payload = [dict(zip(COLUMNS, b)) for b in body]
    print("exported " + str(len(body)) + " rows -> " + str(out.relative_to(ROOT)))
    print("  oov_domains cells: " + str(sum(1 for p in payload if p["oov_domains"]))
          + " | owner_notes cells: " + str(sum(1 for p in payload if p["owner_notes"])))
    print("  sha256(csv)=" + hashlib.sha256(text.encode()).hexdigest())
    print("  sha256(numbers)=" + raw_sha + " (pinned)")
    return 0


def _csv_cell(value: str) -> str:
    """Minimal RFC4180 quoting for a CSV cell."""
    if any(ch in value for ch in [',', '"', "\n"]):
        return '"' + value.replace('"', '""') + '"'
    return value


def _crash_safe_write(path: Path, text: str) -> None:
    """Write atomically: tempfile in the same directory -> fsync -> os.replace (C6)."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_source(cfg: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Read the durable machine face of the owner sheet, keyed by item_id."""
    rows = list(csv.DictReader((ROOT / cfg["source"]["export_csv"]).read_text(encoding="utf-8").splitlines()))
    return {r["item_id"]: r for r in rows if r.get("item_id")}


def derive_rows(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Re-derive the ruler rows from the consolidated anchor + the pinned owner review sheet."""
    long_first, dom_set, disc_set = load_vocab()
    norm: dict[str, str] = cfg.get("normalize") or {}
    alias: dict[str, str] = cfg.get("token_alias") or {}
    abst: str = cfg["abstention"]
    cap: int = cap_domains()
    cons = json.loads((ROOT / cfg["source"]["consolidated"]).read_text(encoding="utf-8"))["rows"]
    src = read_source(cfg)
    assert_notes_accounted(cfg, src)
    assert_answers_pin(cfg)
    abstained: set[str] = {str(i) for i in (cfg.get("discipline_abstention") or [])}
    warnings: list[str] = []
    out: list[dict[str, Any]] = []
    for row in cons:
        item = row["item_id"]
        raw_base = [t.strip().lower() for t in (row.get("domain") or "").split("|") if t.strip()]
        if not raw_base:
            continue  # no domain cell -> not a domain-axis row (the ruler is 201/208 by construction)
        base = [norm.get(d, d) for d in raw_base if d != abst]
        sheet = src.get(item, {})
        cell = sheet.get("oov_domains") or ""
        ignored = {t.lower() for t in (cfg.get("ignored_sheet_fragments") or [])}
        undeclared = [t.strip().lower() for t in CELL_SPLIT.split(cell)
                      if t.strip() and not resolve_token(t, long_first, dom_set, alias)
                      and t.strip().lower() not in ignored]
        if undeclared:
            raise SystemExit("FAIL-CLOSED: " + item + " owner-sheet cell carries UNDECLARED fragment(s) "
                             + ", ".join(repr(t) for t in undeclared)
                             + " - declare them in ignored_sheet_fragments or map them in token_alias")
        adds = [norm.get(d, d) for d in parse_cell(cell, long_first, dom_set, alias) if d != abst]
        merged = [d for d in dict.fromkeys(base + adds) if d != abst]
        for drop in (cfg.get("remove_domains") or {}).get(item, []):
            merged = [d for d in merged if d != drop]
        if len(merged) > cap:
            dropped = merged[cap:]
            if item in (cfg.get("declared_cap_drops") or {}):
                warnings.append("CAP-DROP(declared): " + item + " " + str(len(merged)) + " -> " + str(cap)
                                + " dropped: " + ", ".join(dropped))
            else:
                warnings.append("CAP-DROP(NEW/UNDECLARED): " + item + " " + str(len(merged)) + " -> " + str(cap)
                                + " dropped: " + ", ".join(dropped))
            merged = merged[:cap]
        bad = [d for d in merged if d not in dom_set]
        if bad:
            raise SystemExit("FAIL-CLOSED: " + item + " carries non-canonical domain(s): " + ", ".join(bad))
        override = (cfg.get("primary_override") or {}).get(item)
        if override:
            if override not in merged:
                raise SystemExit("FAIL-CLOSED: " + item + " primary " + override + " is not among its domains")
            merged = [override] + [d for d in merged if d != override]
        primary = merged[0] if merged else ""
        disc = (cfg.get("discipline_override") or {}).get(item) or (row.get("discipline") or "")
        if item in abstained:
            disc = ""  # BUG-676 fix: the owner CONFIRMED abstention -> the token never reaches the authority
        if disc == abst:
            raise SystemExit("FAIL-CLOSED: " + item + " discipline carries the out-of-menu abstention token '"
                             + abst + "' - declare the row in discipline_abstention (owner-confirmed) or give "
                             "it an owner discipline_override")
        if disc and disc not in disc_set:
            raise SystemExit("FAIL-CLOSED: " + item + " discipline off the closed menu: " + disc)
        if item in abstained:
            warnings.append("ABSTENTION(declared): " + item + " discipline='' (owner-confirmed abstain, BUG-676)")
        out.append({"item_id": item, "name": row["name"], "discipline": disc,
                    "domains": merged, "primary_domain": primary})
    for item in cfg.get("noise_drop_excluded") or []:
        if item not in {r["item_id"] for r in out}:
            warnings.append("DECLARED-DROP: " + item + " owner noise_drop (domains do not apply)")
    absent = sorted(abstained - {r["item_id"] for r in out})
    if absent:
        raise SystemExit("FAIL-CLOSED: config declares discipline_abstention for row(s) that are NOT in the "
                         "ruler: " + ", ".join(absent) + " - an abstention for a dropped row is a category error")
    for item, why in (cfg.get("pending_owner_rows") or {}).items():
        warnings.append("PENDING-OWNER: " + str(item) + " " + " ".join(str(why).split())[:190])
    return out, warnings


def check(rulings: Path | None = None) -> int:
    """Re-derive in memory and assert the ruler on disk is canonical-byte-identical (drift detector)."""
    cfg = _cfg(rulings)
    rows, warnings = derive_rows(cfg)
    disk = json.loads((ROOT / cfg["source"]["ruler"]).read_text(encoding="utf-8"))
    if disk.get("sha256") != _sha(disk.get("rows") or []):
        print("FAIL: the on-disk ruler sha256 is stale vs its own rows (tamper or unstamped edit)")
        return 1
    if _canonical(rows) != _canonical(disk.get("rows") or []):
        dr = {r["item_id"]: r for r in disk.get("rows") or []}
        diffs = [r["item_id"] for r in rows if _canonical(r) != _canonical(dr.get(r["item_id"], {}))]
        print("FAIL: re-derivation does not reproduce the frozen ruler; differing rows: " + ", ".join(diffs[:10]))
        return 1
    print("ok apply_owner_domain_review: the ruler IS re-derivable from the pinned owner sheet ("
          + str(len(rows)) + " rows, sha256 " + str(disk.get("sha256"))[:16] + "); "
          + str(len(warnings)) + " declared warning(s)")
    for w in warnings:
        print("   " + w)
    return 0


def apply(rulings: Path | None = None) -> int:
    """Re-derive and write the ruler crash-safe, re-stamping the sha256."""
    cfg = _cfg(rulings)
    rows, warnings = derive_rows(cfg)
    path = ROOT / cfg["source"]["ruler"]
    art = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cons = json.loads((ROOT / cfg["source"]["consolidated"]).read_text(encoding="utf-8"))["rows"]
    art.update({
        "n_anchor_rows": len(cons), "n_ruler_rows": len(rows), "n_skipped_empty": len(cons) - len(rows),
        "rows": rows, "sha256": _sha(rows),
        "note": ("re-derived from the 2026-10-08 owner review sheet "
                 "(governance/OWNER_DOMAIN_REVIEW_SOURCE_20261008.csv, sha256-pinned) + the owner's round-2 "
                 "answers (governance/OWNER_CONFIRMATION_SHEET_20261008.csv, sha256-pinned) + owner "
                 "discipline rulings (R141->machine learning, R159->risk management); declared drops: owner "
                 "noise_drop rows " + "/".join(cfg.get("noise_drop_excluded") or []) + "; owner-confirmed "
                 "discipline abstentions declare discipline='' (BUG-676 fix); the R158 domain drop is "
                 "APPLICABILITY-ranked (D-2878), never positional; rows still pending the owner: "
                 + ", ".join(sorted(cfg.get("pending_owner_rows") or {}))
                 + " (see governance/OWNER_RULINGS_ROUND2_20261008.md); verify with: "
                   "python3 scripts/apply_owner_domain_review.py --check"),
    })
    _crash_safe_write(path, json.dumps(art, indent=2, ensure_ascii=False) + "\n")
    print("wrote " + cfg["source"]["ruler"] + " (" + str(len(rows)) + " rows, sha256 " + art["sha256"] + ")")
    for w in warnings:
        print("   " + w)
    return 0


def main() -> int:
    """CLI entry point: --export-source | --check | --apply."""
    ap = argparse.ArgumentParser(description="re-derive/verify the frozen DOMAIN ruler from the owner review sheet")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--export-source", action="store_true", help=".numbers -> pinned 9-column CSV")
    g.add_argument("--check", action="store_true", help="assert the ruler on disk is re-derivable (no write)")
    g.add_argument("--apply", action="store_true", help="re-derive and write (crash-safe)")
    ap.add_argument("--rulings", type=Path, default=None,
                    help="owner rulings YAML (default: config/owner_domain_rulings_20261008.yaml)")
    args = ap.parse_args()
    if args.export_source:
        return export_source(args.rulings)
    return check(args.rulings) if args.check else apply(args.rulings)


if __name__ == "__main__":
    sys.exit(main())
