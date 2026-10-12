#!/usr/bin/env python3
"""remint_anchor2_v8.py — deterministic ANCHOR-2 v8 re-mint (F2, owner-gated).

WHY (Follow-through 4/5 close-out, D-2865/D-2866). ANCHOR-2 (the 60-row R2 annotation
kappas referee) still carries the frozen v5 menu stamp (menu_hash 73597ee2...) and
pre-v8 domain tokens ('research & methodology' / 'social sciences' / 'science & research'
+ data-quality typos). menu v8 (D-2865) merged/demoted those domains and promoted to live
`config/taxonomy.yaml`, so the BUG-650 referee guard (pipeline/anchor_menu_guard.py)
refuses ANCHOR-2 as a kappa referee until it is re-derived against v8 AND owner-signed.

This script applies the owner-gated decisions banked in
`governance/ANCHOR2_V8_REMINT_TRIAGE_20261007.csv` (38 action rows) and re-stamps the KEY
with the LIVE v8 menu pins read from `config/menu_axis_hashes.yaml` (C12: never hardcoded).

TRANSFORM (deterministic, LLM-free — a data transform, not generation; R5 not implicated):
  domain axis, per row:
    - if the row carries ANY OWNER_APPLY action, the final domains are the OWNER target
      (pipe-split, primary-first) — FULL REPLACE. The owner re-adjudicated the applied
      domain CONTENT-DRIVEN (Guarino & Welty 2002 rigidity / OntoClean); the target IS the
      complete answer and supersedes every prior token (incl. 'emerging' abstention).
    - else apply AUTO_RENAME ('research & methodology' -> 'research practice') and AUTO_FIX
      (typos 'media & entertainmen'/'product desig'/'business operation') in place.
  discipline axis:
    - SHEET row 15 empty discipline -> 'emerging' (OFFMENU_ADJUDICATE, abstention).
    - KEY pipeline_discipline already valid v8 (verified; unchanged).
  provenance:
    - every OWNER_APPLY row records its raw (stale) token + original domains in a remap log
      (FAIR R1.2 / SKOS altLabel — recoverable, never silently discarded).

OUTPUTS (originals untouched — immutable provenance):
  governance/ANCHOR2_KEY_V8_20261007.json
  governance/ANCHOR2_BLIND_SHEET_V8_20261007.csv

VERIFY (--check): 0 out-of-vocabulary domains/disciplines (vs v8 canonicals + 'emerging'),
60 rows in each artifact, and the KEY passes `assert_referee_menu_current` (BUG-650).
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

KEY = ROOT / "governance" / "ANCHOR2_KEY_20260920.json"
SHEET = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_20260920.csv"
TRIAGE = ROOT / "governance" / "ANCHOR2_V8_REMINT_TRIAGE_20261007.csv"
HASHES = ROOT / "config" / "menu_axis_hashes.yaml"
TAXONOMY = ROOT / "config" / "taxonomy_v8.yaml"
OUT_KEY = ROOT / "governance" / "ANCHOR2_KEY_V8_20261007.json"
OUT_SHEET = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_V8_20261007.csv"

RENAME = {"research & methodology": "research practice"}
FIX = {
    "media & entertainmen": "media & entertainment",
    "product desig": "product design",
    "business operation": "business operations",
}
# Stale epistemic catch-alls removed in v8 (A-merge / B-demote, D-2865). Their OWNER_APPLY
# target is the content-driven replacement; the raw token is preserved in the remap log.
STALE = {"social sciences", "social science", "science & research"}
ABSTENTION = "emerging"
_MARKER = "(sole-domain after drop)"  # informational triage marker, never a real token


def _norm(s: str) -> str:
    return (s or "").strip().strip('"').strip()


def _split_owner_target(target: str) -> list[str]:
    """Split a pipe-joined OWNER target into an ordered, primary-first, deduped list."""
    out: list[str] = []
    for t in (target or "").split("|"):
        t = _norm(t)
        if t and t not in out:
            out.append(t)
    return out


def load_vocab() -> tuple[set[str], set[str]]:
    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    doms = {d["canonical"] for d in tax["domains"]}
    disc = {d["canonical"] for d in tax["disciplines"]}
    return doms, disc


def load_triage() -> dict[tuple[str, int], dict]:
    """Return {(source, row): {'owner_target': str|None, 'renames': dict, 'fixes': dict,
    'discipline_owner': str|None}}."""
    rows = list(csv.DictReader(TRIAGE.read_text(encoding="utf-8").splitlines()))
    out: dict[tuple[str, int], dict] = {}
    for r in rows:
        key = (r["source"].strip(), int(r["row"]))
        e = out.setdefault(key, {"owner_target": None, "renames": {}, "fixes": {},
                                 "discipline_owner": None})
        axis = r["axis"].strip()
        dec = r["decision"].strip()
        old = _norm(r["old_token"])
        tgt = (r["owner_decision"].strip() or r["proposed_v8_target"].strip())
        if axis == "domain":
            if dec == "OWNER_APPLY" and old != _MARKER:
                e["owner_target"] = tgt
            elif dec == "AUTO_RENAME":
                e["renames"][old] = tgt
            elif dec == "AUTO_FIX":
                e["fixes"][old] = tgt
        elif axis == "discipline" and dec == "OFFMENU_ADJUDICATE":
            e["discipline_owner"] = tgt
    return out


def _apply_domains(tokens: list[str], act: dict) -> tuple[list[str], str]:
    """Transform a domain list per the triage action. Returns (new_list, mode)."""
    if act.get("owner_target"):
        return _split_owner_target(act["owner_target"]), "OWNER_APPLY"
    # token-level: rename/fix in place, drop nothing (stale tokens absent here by construction)
    out: list[str] = []
    renames = act.get("renames", {})
    fixes = act.get("fixes", {})
    for t in tokens:
        t = _norm(t)
        if not t:
            continue
        new = renames.get(t, fixes.get(t, t))
        if new not in out:
            out.append(new)
    return out, "AUTO_RENAME/AUTO_FIX"


def _crash_safe_write_text(path: Path, text: str) -> None:
    import os
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def build_key(triage: dict, doms_vocab: set[str], disc_vocab: set[str]) -> tuple[dict, list]:
    src = json.loads(KEY.read_text(encoding="utf-8"))
    h = yaml.safe_load(HASHES.read_text(encoding="utf-8"))
    remap_log: list[dict] = []
    for fb, e in src["key"].items():
        row = int(e["row"])
        act = triage.get(("KEY", row), {})
        old = list(e["pipeline_domains"])
        new_doms, mode = _apply_domains(old, act)
        if new_doms != old:
            remap_log.append({"row": row, "fb_id": fb, "name": e["name"],
                              "old_domains": old, "new_domains": new_doms, "mode": mode})
        e["pipeline_domains"] = new_doms
    # discipline axis: KEY pipeline_discipline is already v8 (no OFFMENU on KEY); verified.
    src["menu_hash"] = h["composite_hash_live"]
    src["answer_space_hash"] = h["answer_space_hash"]
    src["taxonomy_version"] = "v8"
    src["_provenance"] = {
        "schema_version": "1.0",
        "generated_by": "scripts/remint_anchor2_v8.py (F2 owner-gated v8 re-mint)",
        "gen_model": "none",
        "decision": "Follow-through 5 (D-2865/D-2866 F2 close-out)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "key_source": str(KEY.relative_to(ROOT)),
            "sheet_source": str(SHEET.relative_to(ROOT)),
            "triage": str(TRIAGE.relative_to(ROOT)),
        },
        "frozen_menu_hash_v5": "73597ee2b1bb1eb92edb08e743ffa0654c1e5994edcd3535d814c7942a89df6f",
        "remap_log": remap_log,
    }
    return src, remap_log


def build_sheet(triage: dict) -> tuple[list[list[str]], dict]:
    """Return (new sheet rows incl. header, discipline_log)."""
    raw = list(csv.reader(SHEET.read_text(encoding="utf-8").splitlines()))
    header = raw[0]
    out = [header]
    disc_log: dict[int, str] = {}
    for r in raw[1:]:
        if not r or not r[0].strip():
            continue
        row = int(r[0])
        act = triage.get(("SHEET", row), {})
        # columns: 0 row, 1 fb_id, 2 name, 3 definition, 4 discipline, 5 domains, 6 content_type, 7+ notes
        new = list(r)
        # pad to header length for safety (notes columns)
        while len(new) < len(header):
            new.append("")
        # domain axis
        toks = [t for t in (r[5].split(",") if len(r) > 5 and r[5] else [])]
        new_doms, _ = _apply_domains(toks, act)
        new[5] = ", ".join(new_doms)
        # discipline axis
        if act.get("discipline_owner") is not None:
            disc_log[row] = new[4]
            new[4] = act["discipline_owner"]
        out.append(new[: len(header)])
    return out, disc_log


def _validate(src: dict, sheet_rows: list[list[str]], doms_vocab, disc_vocab) -> list[str]:
    errs: list[str] = []
    doms_ok = doms_vocab | {ABSTENTION}
    disc_ok = disc_vocab | {ABSTENTION}
    for fb, e in src["key"].items():
        for d in e["pipeline_domains"]:
            if d not in doms_ok:
                errs.append(f"KEY row {e['row']} OOV domain: {d!r}")
        if e["pipeline_discipline"] not in disc_ok:
            errs.append(f"KEY row {e['row']} OOV discipline: {e['pipeline_discipline']!r}")
    header = sheet_rows[0]
    for r in sheet_rows[1:]:
        if not r or not r[0].strip():
            continue
        row = int(r[0])
        for d in [t for t in (r[5].split(",") if len(r) > 5 and r[5] else [])]:
            d = _norm(d)
            if d and d not in doms_ok:
                errs.append(f"SHEET row {row} OOV domain: {d!r}")
        disc = _norm(r[4]) if len(r) > 4 else ""
        if disc and disc not in disc_ok:
            errs.append(f"SHEET row {row} OOV discipline: {disc!r}")
    return errs


def main() -> int:
    check = "--check" in sys.argv
    doms_vocab, disc_vocab = load_vocab()
    triage = load_triage()

    src, remap_log = build_key(triage, doms_vocab, disc_vocab)
    sheet_rows, disc_log = build_sheet(triage)

    # assemble sheet CSV text with correct quoting
    import io
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(sheet_rows)
    sheet_text = buf.getvalue()

    errs = _validate(src, sheet_rows, doms_vocab, disc_vocab)

    # guard (BUG-650): the re-stamped KEY must be a valid menu-v8 referee
    from pipeline.anchor_menu_guard import referee_menu_current_verdict
    verdict = referee_menu_current_verdict(src, label=OUT_KEY.name, axis="discipline")

    n_key = len(src["key"])
    n_sheet = len([r for r in sheet_rows[1:] if r and r[0].strip()])

    print(f"CHECK: KEY rows={n_key} SHEET rows={n_sheet} remap_log={len(remap_log)} "
          f"disc_log={len(disc_log)} OOV={len(errs)}")
    for e in errs:
        print("  OOV: " + e)
    print(f"GUARD: ok={verdict['ok']} reason={verdict['reason']}")

    ok = (not errs) and n_key == 60 and n_sheet == 60 and verdict["ok"]
    print("CHECK " + ("PASS" if ok else "FAIL"))
    if check:
        return 0 if ok else 1

    _crash_safe_write_text(OUT_KEY, json.dumps(src, ensure_ascii=False, indent=2))
    _crash_safe_write_text(OUT_SHEET, sheet_text)
    print(f"wrote {OUT_KEY.relative_to(ROOT)} ({n_key} keys, "
          f"menu_hash={src['menu_hash'][:16]}... answer_space_hash={src['answer_space_hash'][:16]}...)")
    print(f"wrote {OUT_SHEET.relative_to(ROOT)} ({n_sheet} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
