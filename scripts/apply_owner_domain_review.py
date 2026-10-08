#!/usr/bin/env python3
"""apply_owner_domain_review.py — re-derive and verify the frozen DOMAIN ruler from the OWNER's review sheet.

WHY (BUG-674 / BUG-675 / BUG-678 / BUG-679 / BUG-682). The frozen domain ruler
(governance/DOMAIN_RULER_FROZEN_*.json) is the ONE artifact in which EVERY owner ruling on the
discipline / domain / primary_domain axis is materialized and re-derivable. Two earlier sweeps were
applied by hand-scripts held in /tmp (volatile, unreproducible) and the derived review CSV was a
lossy, self-contradictory face (0/46 oov_domains cells, 8 vs 11 owner_notes, 42/201 contradicted
rows) - so a future agent re-deriving from it would SILENTLY lose them (BUG-678).

THE RULE (measured against the frozen artifact, not invented):
    base        = the consolidated anchor's domain cell, in cell order (abstention token dropped)
    additions   = the OWNER sheet's oov_domains cell, in CELL ORDER, each token alias-resolved
    removals    = owner directives from config (remove_domains)
    cap         = pipeline_config.max_domains_per_fb, applied LAST and REPORTED, never silently
    primary     = the owner override, MOVED TO FRONT; otherwise base[0]
    abstain     = rows the owner CONFIRMED as abstentions carry discipline='' + a declared id in
                  discipline_abstention (BUG-676: 'emerging' is an axis-level verdict, not a menu
                  value; on the DISCIPLINE axis the abstention is an ABSENCE, not a token)
    drop        = rows the owner declared noise_drop (config#noise_drop_excluded) are REMOVED from
                  the axis-bearing ruler, even when an upstream face still carries a pre-drop
                  residue, and MUST be accounted for in the soft-quarantine ledger (BUG-679)
    reinstate   = rows the owner KEPT that have no domain cell in the sheet (config#reinstated_rows);
                  declared as data, never special-cased in code
    partition   = n_anchor_rows == n_ruler_rows + len(declared drops), EXACTLY. This is the rail that
                  would have caught BUG-679 on the day it was created: a row may be axis-bearing or a
                  declared drop, never neither and never both.

MODES:
  --export-source   .numbers -> faithful 9-column CSV + sha256 pin (the durable face of the owner sheet)
  --check           re-derive in memory; assert the ruler ON DISK is canonical-byte-identical (no drift)
  --apply           re-derive and write crash-safe (tempfile -> fsync -> os.replace), re-stamping sha256
  --check-faces     tri-state: do the declared downstream faces carry the ruler's axis values? A ruling
                    that lands here but not in the face the pipeline reads is an error leak (BUG-682)
  --selftest        known-answer controls for every guard above (a control nothing runs is a comment, BUG-492)

Deterministic data transform, LLM-free (R5 not implicated) - same class as scripts/remint_anchor2_v8.py.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import hashlib
import io
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
#: A cell that is equal to the declared abstention token is an ABSENCE, not a value (BUG-676).
AXIS_COLUMNS = ("discipline", "domains", "primary_domain")


def _cfg(rulings: Path | None = None) -> dict[str, Any]:
    """Load the owner rulings config (all rulings are data, never code — C12c)."""
    return yaml.safe_load((rulings or RULINGS).read_text(encoding="utf-8"))


def assert_notes_accounted(cfg: dict[str, Any], src: dict[str, dict[str, str]]) -> None:
    """Every owner_notes cell must be a DECLARED directive, or the run fails CLOSED.

    This is the guard that would have caught BUG-675 at commit time: R141 carried 'discipline is machine
    learning' in free text that NO config column carried, so the ruling was silently unapplied for a round.
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


def _drop_ids(cfg: dict[str, Any]) -> list[str]:
    """The declared noise_drop set, in declaration order, deduped."""
    return list(dict.fromkeys(str(i) for i in (cfg.get("noise_drop_excluded") or [])))


def assert_drop_ledger(cfg: dict[str, Any], drops: list[str], cons_ids: set[str]) -> None:
    """Every declared drop must name a real anchor row AND land in the soft-quarantine ledger.

    Two ways this guard earns its keep: a typo'd id would silently drop nothing (the BUG-679 shape one
    level down), and a drop with no ledger entry is a HARD delete dressed as a soft one - the policy is
    quarantine, never delete (D-2711), so an unledgered drop is a policy violation, not a bookkeeping gap.
    """
    unknown = [i for i in drops if i not in cons_ids]
    if unknown:
        raise SystemExit("FAIL-CLOSED: declared noise_drop row(s) are not anchor rows: " + ", ".join(unknown)
                         + " - a drop that names nothing drops nothing")
    rel = (cfg.get("source") or {}).get("quarantine_ledger")
    if not rel:
        raise SystemExit("FAIL-CLOSED: config#source.quarantine_ledger is not declared "
                         "(a soft drop with no audit trail is a hard delete)")
    path = ROOT / rel
    if not path.exists():
        raise SystemExit("FAIL-CLOSED: declared soft-quarantine ledger is missing: " + str(rel))
    entries = json.loads(path.read_text(encoding="utf-8")).get("entries") or []
    ledgered = {str(e.get("anchor_id")) for e in entries if e.get("anchor_id")}
    unledgered = [i for i in drops if i not in ledgered]
    if unledgered:
        raise SystemExit("FAIL-CLOSED: declared noise_drop row(s) have no soft-quarantine ledger entry in "
                         + str(rel) + ": " + ", ".join(unledgered) + " (D-2711: quarantine is reversible, "
                         "deletion is not)")


def assert_partition(cons_ids: list[str], out: list[dict[str, Any]], drops: list[str]) -> None:
    """Every anchor row is EXACTLY one of: axis-bearing, or declared noise_drop (BUG-679's rail).

    A row that is neither is an unaccounted row (a silent skip); a row that is both is a contradiction. This
    invariant is what turns "the drop reached some of the rows" from an invisible state into a hard failure.
    """
    in_ruler = {r["item_id"] for r in out}
    drop_set = set(drops)
    both = sorted(in_ruler & drop_set)
    if both:
        raise SystemExit("FAIL-CLOSED: row(s) are BOTH axis-bearing and declared noise_drop: " + ", ".join(both))
    neither = sorted(set(cons_ids) - in_ruler - drop_set)
    if neither:
        raise SystemExit("FAIL-CLOSED: anchor row(s) are NEITHER axis-bearing NOR declared noise_drop: "
                         + ", ".join(neither) + " - every anchor row must be accounted for exactly once "
                         "(this is the BUG-679 invariant)")


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
    for dom in long_first:  # longest-first fallback for no-separator runs
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


def build_reinstated(cfg: dict[str, Any], dom_set: set[str], disc_set: set[str], cap: int,
                     abstained: set[str], cons_ids: set[str], present: set[str]) -> list[dict[str, Any]]:
    """Build the rows the owner KEPT that have no domain cell in the sheet (config#reinstated_rows).

    Fail-closed on every way a reinstatement could invent a label: an off-menu domain, an over-cap
    cardinality, a primary that is not domains[0], a discipline that is neither on the closed menu nor a
    DECLARED abstention, an unknown anchor row, or a row that is already axis-bearing.
    """
    out: list[dict[str, Any]] = []
    norm: dict[str, str] = cfg.get("normalize") or {}
    for item, spec in (cfg.get("reinstated_rows") or {}).items():
        item = str(item)
        if item not in cons_ids:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item + " is not an anchor row")
        if item in present:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item + " is already axis-bearing")
        doms = [norm.get(d, d) for d in (spec.get("domains") or [])]
        if not doms:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item + " declares no domain")
        bad = [d for d in doms if d not in dom_set]
        if bad:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item + " carries non-canonical domain(s): "
                             + ", ".join(bad))
        if len(doms) > cap:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item + " exceeds the D150 cap " + str(cap))
        primary = str(spec.get("primary_domain") or doms[0])
        if primary != doms[0]:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item + " primary " + primary
                             + " != domains[0] " + doms[0] + " (OntoClean: primary IS the first role)")
        # ONE home for every discipline ruling: config#discipline_override decides, and a reinstatement may
        # only carry the value as a redundant echo (BUG-675's lesson: a ruling in a second place is a ruling
        # that will disagree with itself).
        disc = str((cfg.get("discipline_override") or {}).get(item) or spec.get("discipline") or "")
        if spec.get("abstain_discipline"):
            if disc:
                raise SystemExit("FAIL-CLOSED: reinstated row " + item
                                 + " declares abstain_discipline AND a discipline")
            if item not in abstained:
                raise SystemExit("FAIL-CLOSED: reinstated row " + item + " abstains its discipline but is not "
                                 "declared in discipline_abstention")
        elif disc not in disc_set:
            raise SystemExit("FAIL-CLOSED: reinstated row " + item
                             + " discipline is off the closed menu: " + repr(disc))
        out.append({"item_id": item, "name": str(spec.get("name") or ""), "discipline": disc,
                    "domains": doms, "primary_domain": primary})
    return out


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
    drops = _drop_ids(cfg)
    cons_ids = [str(r["item_id"]) for r in cons]
    assert_drop_ledger(cfg, drops, set(cons_ids))
    abstained: set[str] = {str(i) for i in (cfg.get("discipline_abstention") or [])}
    drop_set = set(drops)
    warnings: list[str] = []
    out: list[dict[str, Any]] = []
    for row in cons:
        item = row["item_id"]
        if item in drop_set:
            continue  # BUG-679: a declared drop is removed even when the upstream face still carries residue
        raw_base = [t.strip().lower() for t in (row.get("domain") or "").split("|") if t.strip()]
        if not raw_base:
            continue  # no domain cell and not a declared drop -> the partition guard below must catch it
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
    # reinstated rows: kept by the owner, no domain cell in the sheet -> inserted at their item_id position so
    # the artifact's existing order is preserved byte-for-byte.
    for extra in build_reinstated(cfg, dom_set, disc_set, cap, abstained, set(cons_ids),
                                  {r["item_id"] for r in out}):
        at = next((n for n, r in enumerate(out) if r["item_id"] > extra["item_id"]), len(out))
        out.insert(at, extra)
        warnings.append("REINSTATED(owner-kept): " + extra["item_id"] + " " + "|".join(extra["domains"])
                        + " (primary " + extra["primary_domain"] + ")")
    for item in drops:
        if item in {r["item_id"] for r in out}:
            raise SystemExit("FAIL-CLOSED: declared noise_drop row " + item + " is axis-bearing (BUG-679)")
        warnings.append("DECLARED-DROP: " + item + " owner noise_drop (domains do not apply, D-2813)")
    absent = sorted(abstained - {r["item_id"] for r in out})
    if absent:
        raise SystemExit("FAIL-CLOSED: config declares discipline_abstention for row(s) that are NOT in the "
                         "ruler: " + ", ".join(absent) + " - an abstention for a dropped row is a category error")
    # ...and the OTHER direction (BUG-676's principle applied to the declaration itself): a row declared as an
    # abstention must actually carry no discipline. Without this, a stale declaration survives a ruling that
    # later NAMES the discipline - the config would say "abstained" while the authority says "systems thinking",
    # and a reader would trust whichever file it opened (the BUG-682 shape, one level down).
    ruled = {r["item_id"]: r["discipline"] for r in out}
    misdeclared = sorted(i for i in abstained if ruled.get(i))
    if misdeclared:
        raise SystemExit("FAIL-CLOSED: row(s) are declared in discipline_abstention but the ruler carries a "
                         "discipline for them: " + ", ".join(misdeclared))
    assert_partition(cons_ids, out, drops)
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
        derived = {r["item_id"]: r for r in rows}
        changed = [i for i, r in derived.items() if _canonical(r) != _canonical(dr.get(i, {}))]
        removed = [i for i in dr if i not in derived]
        detail = ("changed: " + ", ".join(sorted(changed)[:10])) if changed else ""
        detail += (" | REMOVED (declared drop): " + ", ".join(sorted(removed)[:20])) if removed else ""
        print("FAIL: re-derivation does not reproduce the frozen ruler; " + (detail or "no row-level detail"))
        return 1
    print("ok apply_owner_domain_review: the ruler IS re-derivable from the pinned owner sheet ("
          + str(len(rows)) + " rows, sha256 " + str(disk.get("sha256"))[:16] + "); "
          + str(len(warnings)) + " declared warning(s)")
    for w in warnings:
        print("   " + w)
    return 0


def check_faces(rulings: Path | None = None) -> int:
    """Tri-state cross-face rail (BUG-682): do the declared downstream faces carry the ruler's values?

    exit 0  every declared face agrees on every axis cell, and no declared drop carries a residue
    exit 2  divergence/drop-residue exists but is within the declared, SHRINK-ONLY ceiling (owner-owed)
    exit 1  an UNDECLARED divergence: a ruling that landed here and not in the face the pipeline reads.

    This rail exists because the axis had TWO homes and nothing asserted they agreed: the owner's rulings
    were materialized here while the declared authority of record still carried the pre-ruling values, and
    the ladder's axis rail compared that authority against its own downstream copy - a control that cannot
    fire (BUG-492 class). The declared ceiling therefore starts at the measured gap and may only SHRINK.
    """
    return _check_faces_impl(_cfg(rulings))


def apply(rulings: Path | None = None) -> int:
    """Re-derive and write the ruler crash-safe, re-stamping the sha256."""
    cfg = _cfg(rulings)
    rows, warnings = derive_rows(cfg)
    path = ROOT / cfg["source"]["ruler"]
    art = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cons = json.loads((ROOT / cfg["source"]["consolidated"]).read_text(encoding="utf-8"))["rows"]
    drops = _drop_ids(cfg)
    art.update({
        "n_anchor_rows": len(cons), "n_ruler_rows": len(rows), "n_noise_drop": len(drops),
        "n_reinstated": len(cfg.get("reinstated_rows") or {}),
        "partition": "n_anchor_rows == n_ruler_rows + n_noise_drop (BUG-679 invariant)",
        "rows": rows, "sha256": _sha(rows),
        "note": ("re-derived from the 2026-10-08 owner review sheet "
                 "(governance/OWNER_DOMAIN_REVIEW_SOURCE_20261008.csv, sha256-pinned) + the owner's round-2 "
                 "answers (governance/OWNER_CONFIRMATION_SHEET_20261008.csv, sha256-pinned) + the owner's "
                 "round-3 rulings (governance/OWNER_RULINGS_ROUND3_20261008.md); declared owner noise_drop "
                 "rows " + "/".join(drops) + " are REMOVED (the RATIFY-3 DROP(13) now reaches 13/13 + R040, "
                 "BUG-679); owner-kept row(s) " + "/".join(sorted(cfg.get("reinstated_rows") or {}))
                 + " reinstated by declaration; owner-confirmed discipline abstentions declare discipline='' "
                   "(BUG-676 fix, now asserted in BOTH directions); the R158 domain drop is "
                   "APPLICABILITY-ranked (D-2878), never positional, and R158's PRIMARY (design strategy) was "
                   "ratified FINAL by the owner on 2026-10-08 (round 4) - not re-openable by inference; R091's "
                   "discipline = systems thinking (round-4 owner-approved senior ruling, not an abstention); "
                   "verify with: python3 scripts/apply_owner_domain_review.py --check"),
    })
    art.pop("n_skipped_empty", None)  # superseded by the partition invariant (a skip is no longer a category)
    _crash_safe_write(path, json.dumps(art, indent=2, ensure_ascii=False) + "\n")
    print("wrote " + cfg["source"]["ruler"] + " (" + str(len(rows)) + " rows, sha256 " + art["sha256"] + ")")
    for w in warnings:
        print("   " + w)
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
        print("FAIL-CLOSED: sheet is missing column(s): " + ", ".join(missing)
              + " (header: " + ", ".join(header) + ")")
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


def _selftest_fixture(tmp: Path) -> dict[str, Any]:
    """Write a minimal, self-consistent owner-ruling fixture and return the cfg that reads it."""
    cons = {"rows": [
        {"item_id": "AX1", "name": "Alpha", "discipline": "design thinking",
         "domain": "graphic design|user experience", "primary_domain": "graphic design"},
        {"item_id": "AX2", "name": "Beta", "discipline": "emerging", "domain": None, "primary_domain": None},
        {"item_id": "AX3", "name": "Gamma", "discipline": "cultural studies",
         "domain": "arts & culture", "primary_domain": "arts & culture"},
    ]}
    (tmp / "cons.json").write_text(json.dumps(cons), encoding="utf-8")
    ledger = {"entries": [{"anchor_id": "AX2", "kind": "anchor"}, {"anchor_id": "AX3", "kind": "anchor"}]}
    (tmp / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    (tmp / "sheet.csv").write_text(",".join(COLUMNS) + "\n", encoding="utf-8")
    face = {"rows": [
        {"item_id": "AX1", "discipline": "design thinking", "domain": "graphic design|user experience",
         "primary_domain": "graphic design"},
        {"item_id": "AX3", "discipline": "cultural studies", "domain": "arts & culture",
         "primary_domain": "arts & culture"},
    ]}
    (tmp / "face.json").write_text(json.dumps(face), encoding="utf-8")
    return {
        "abstention": "emerging",
        "normalize": {},
        "token_alias": {},
        "ignored_sheet_fragments": ["emerging", "development"],
        "owner_notes_accounted": {},
        "discipline_abstention": [],
        "noise_drop_excluded": ["AX2", "AX3"],
        "reinstated_rows": {},
        "declared_cap_drops": {},
        "pending_owner_rows": {},
        "source": {"consolidated": str(tmp / "cons.json"), "export_csv": str(tmp / "sheet.csv"),
                   "quarantine_ledger": str(tmp / "ledger.json")},
        "faces": {"ceiling_divergence": 0, "ceiling_drop_residue": 0,
                  "must_follow": [{"name": "synthetic-face", "file": str(tmp / "face.json"),
                                   "rows_key": "rows",
                                   "columns": {"discipline": "discipline", "domains": "domain",
                                               "primary_domain": "primary_domain"}}]},
        "_schema_version": "selftest",
    }


def _must_fire(label: str, cfg: dict[str, Any], mode: str) -> str | None:
    """Run one control; return an error string if the guard did NOT fire."""
    try:
        if mode == "derive":
            derive_rows(cfg)
        else:
            if _check_faces_impl(cfg) == 0:
                return "control " + label + " did NOT fire (exit 0)"
            return None
    except SystemExit as exc:
        if "FAIL-CLOSED" in str(exc) or "must be accounted" in str(exc):
            return None
        return "control " + label + " fired with an unexpected message: " + str(exc)
    return "control " + label + " did NOT fire"


def selftest() -> int:
    """Known-answer controls: every guard must be SEEN to fire (a control nothing runs is a comment, BUG-492)."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        base = _selftest_fixture(tmp)
        rows, _ = derive_rows(base)
        if [r["item_id"] for r in rows] != ["AX1"]:
            failures.append("baseline: expected only AX1 axis-bearing, got "
                            + str([r["item_id"] for r in rows]))
        baseline_face = Path(base["faces"]["must_follow"][0]["file"]).read_text(encoding="utf-8")
        # 1. a declared drop that names no anchor row must fire
        c = copy.deepcopy(base); c["noise_drop_excluded"] = ["AX2", "AX3", "ZZ9"]
        failures.append(_must_fire("drop-not-an-anchor-row", c, "derive") or "")
        # 2. a declared drop with no ledger entry must fire
        c = copy.deepcopy(base)
        (tmp / "ledger2.json").write_text(json.dumps({"entries": [{"anchor_id": "AX2"}]}), encoding="utf-8")
        c["source"]["quarantine_ledger"] = str(tmp / "ledger2.json")
        failures.append(_must_fire("drop-without-ledger-entry", c, "derive") or "")
        # 3. an abstention declared for a DROPPED row is a category error -> must fire
        c = copy.deepcopy(base); c["discipline_abstention"] = ["AX3"]
        failures.append(_must_fire("abstention-for-a-dropped-row", c, "derive") or "")
        # 4. the PARTITION invariant: an anchor row neither axis-bearing nor dropped must fire (BUG-679)
        c = copy.deepcopy(base); c["noise_drop_excluded"] = ["AX3"]
        failures.append(_must_fire("partition-break-unaccounted-anchor-row", c, "derive") or "")
        # 5. POSITIVE control: a declared drop that still carries a full upstream residue must NOT leak
        #    into the ruler (this is the BUG-679 propagation rule; AX3 has 3 populated axis cells upstream).
        if "AX3" in {row["item_id"] for row in rows}:
            failures.append("control declared-drop-with-upstream-residue leaked into the ruler")
        # 6. a reinstatement with primary != domains[0] must fire
        c = copy.deepcopy(base)
        c["reinstated_rows"] = {"AX2": {"name": "Beta", "domains": ["education", "design strategy"],
                                        "primary_domain": "design strategy", "discipline": "",
                                        "abstain_discipline": True}}
        c["discipline_abstention"] = ["AX2"]
        failures.append(_must_fire("reinstatement-primary-not-domains0", c, "derive") or "")
        # 7. a reinstatement with an off-menu domain must fire
        c = copy.deepcopy(base)
        c["reinstated_rows"] = {"AX2": {"name": "Beta", "domains": ["autopoiesis studies"],
                                        "primary_domain": "autopoiesis studies", "discipline": "",
                                        "abstain_discipline": True}}
        c["discipline_abstention"] = ["AX2"]
        failures.append(_must_fire("reinstatement-off-menu-domain", c, "derive") or "")
        # 8. an undeclared sheet fragment must fire
        c = copy.deepcopy(base)
        (tmp / "sheet2.csv").write_text(",".join(COLUMNS) + "\nAX1,Alpha,,,,,,,\"zzz\"\n", encoding="utf-8")
        c["source"]["export_csv"] = str(tmp / "sheet2.csv")
        failures.append(_must_fire("undeclared-sheet-fragment", c, "derive") or "")
        # 9. the cross-face rail: a face carrying a stale value must be SEEN and the run must be non-zero
        c = copy.deepcopy(base)
        stale = json.loads(baseline_face)
        stale["rows"][0]["discipline"] = "cultural studies"
        (tmp / "face_stale.json").write_text(json.dumps(stale), encoding="utf-8")
        c["faces"]["must_follow"][0]["file"] = str(tmp / "face_stale.json")
        c["faces"]["ceiling_divergence"] = 0
        c["faces"]["ceiling_drop_residue"] = 0
        with contextlib.redirect_stdout(io.StringIO()):
            face_rc = _check_faces_impl(c)
        if face_rc == 0:
            failures.append("control face-divergence did NOT fire (exit 0)")
    failures = [f for f in failures if f]
    if failures:
        for f in failures:
            print("  FAIL  " + f)
        return 1
    print("  ok  apply_owner_domain_review --selftest: 9 controls fired (drop-not-anchor, "
          "drop-without-ledger, abstention-for-drop, partition-break, declared-drop-with-upstream-residue, "
          "primary!=domains[0], off-menu-domain, undeclared-fragment, face-divergence)")
    return 0


def _check_faces_impl(cfg: dict[str, Any]) -> int:
    """The body of the cross-face rail, taking cfg explicitly so it is testable."""
    rows, _ = derive_rows(cfg)
    abst = cfg["abstention"]
    drops = set(_drop_ids(cfg))
    spec = cfg.get("faces") or {}
    ruler = {r["item_id"]: r for r in rows}
    ruler_pipe = {i: "|".join(r["domains"]) for i, r in ruler.items()}
    total_div = 0
    total_res = 0
    for face in spec.get("must_follow") or []:
        path = Path(face["file"]) if Path(face["file"]).is_absolute() else ROOT / face["file"]
        if not path.exists():
            print("FAIL-CLOSED: declared face is missing: " + str(face["file"]))
            return 1
        payload = json.loads(path.read_text(encoding="utf-8"))
        frows = {str(r["item_id"]): r for r in payload.get(face.get("rows_key") or "rows", [])}
        cols = face["columns"]
        divs: list[str] = []
        for iid, r in ruler.items():
            f = frows.get(iid)
            if f is None:
                continue
            want = {"discipline": r["discipline"], "domains": ruler_pipe[iid],
                    "primary_domain": r["primary_domain"]}
            for axis, column in cols.items():
                got = " ".join(str(f.get(column) or "").split())
                if axis == "discipline" and got == abst:
                    got = ""
                if got != want[axis]:
                    divs.append(axis + " " + iid + " face=" + repr(got) + " ruler=" + repr(want[axis]))
        residues: list[str] = []
        for iid in sorted(drops):
            f = frows.get(iid)
            if f is None:
                continue
            for axis, column in cols.items():
                got = " ".join(str(f.get(column) or "").split())
                if got and got != abst:
                    residues.append(axis + " " + iid + " face=" + repr(got))
        total_div += len(divs)
        total_res += len(residues)
        print("  " + face["name"] + ": " + str(len(divs)) + " divergent cell(s), "
              + str(len(residues)) + " drop-residue cell(s)")
        for line in (divs + residues)[:10]:
            print("      " + line)
        if len(divs) + len(residues) > 10:
            print("      ... " + str(len(divs) + len(residues) - 10) + " more")
    ceil_div = int(spec.get("ceiling_divergence", 0))
    ceil_res = int(spec.get("ceiling_drop_residue", 0))
    print("check_faces: " + str(total_div) + " divergent / " + str(total_res)
          + " residual cell(s); declared ceiling " + str(ceil_div) + " / " + str(ceil_res) + " (SHRINK-ONLY)")
    if total_div == 0 and total_res == 0:
        print("  ok  every declared face carries the ruler's axis values (BUG-682 closed)")
        return 0
    if total_div > ceil_div or total_res > ceil_res:
        print("  FAIL  divergence EXCEEDS the declared ceiling - an UNDECLARED propagation failure "
              "(a ruling landed in the ruler and not in the face the pipeline reads)")
        return 1
    if total_div < ceil_div or total_res < ceil_res:
        print("  SHRINK  divergence is BELOW the declared ceiling - lower it in "
              "config/owner_domain_rulings_20261008.yaml#faces")
    else:
        print("  LOUD  owner-owed (BUG-682): the declared authority of record has not yet received the "
              "owner's rulings - the projection is Stage 2 of this decision")
    return 2


def main() -> int:
    """CLI entry point: --export-source | --check | --apply | --check-faces | --selftest."""
    ap = argparse.ArgumentParser(description="re-derive/verify the frozen DOMAIN ruler from the owner review sheet")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--export-source", action="store_true", help=".numbers -> pinned 9-column CSV")
    g.add_argument("--check", action="store_true", help="assert the ruler on disk is re-derivable (no write)")
    g.add_argument("--apply", action="store_true", help="re-derive and write (crash-safe)")
    g.add_argument("--check-faces", action="store_true", help="cross-face divergence rail (BUG-682)")
    g.add_argument("--selftest", action="store_true", help="known-answer controls for every guard")
    ap.add_argument("--rulings", type=Path, default=None,
                    help="owner rulings YAML (default: config/owner_domain_rulings_20261008.yaml)")
    args = ap.parse_args()
    if args.export_source:
        return export_source(args.rulings)
    if args.selftest:
        return selftest()
    if args.check_faces:
        return check_faces(args.rulings)
    return check(args.rulings) if args.check else apply(args.rulings)


if __name__ == "__main__":
    sys.exit(main())
