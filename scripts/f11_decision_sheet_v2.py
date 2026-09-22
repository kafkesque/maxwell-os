#!/usr/bin/env python3
"""Rebuild the F-11 owner decision sheet APPEND-ONLY (BUG-368 / BUG-367).

WHY THIS EXISTS
    The v1 builder (scripts/f11_decision_sheet.py) wrote the FORM axis under the keys
    ``human_extr`` / ``a_extr`` / ``b_extr`` (from ``ax[:4]`` of ``extraction_type``) while
    the emitted header says ``human_extra`` / ``a_extra`` / ``b_extra``. Four columns were
    therefore emitted EMPTY and looked like free space; the owner wrote his 2026-09-22
    rulings into ``human_extra``. Nothing was overwritten (that column was genuinely empty),
    but the ruling was recorded in a column whose name says 'FORM', and the FORM axis itself
    is missing from the sheet.

WHAT THIS DOES (all four steps are non-destructive)
    1. Columns A..R are copied byte-for-byte from the existing sheet. The owner's ruling
       cells in ``human_extra`` are PRESERVED VERBATIM and never rewritten (R-D410).
    2. The missing FORM axis is appended: S=FORM_human_as_written (verbatim from the ruler
       sheet), T=FORM_canonical (declared aliases applied, originals kept), U/V=the two
       LLM coders' FORM answers.
    3. A blank separator column (W) is appended, then the owner input columns X=owner_cont,
       Y=owner_disc, Z=owner_notes. The separator exists so that a blank column can never
       again be mistaken for an answer column (BUG-368).
    4. ``owner_cont`` / ``owner_disc`` are re-derived from the owner's raw cell through an
       explicit, config-declared split (two-value cells are split, typos fixed, every token
       validated against config/closed_menu_v5.json). An audit trail is written to
       ``ruling_map_out``.

READ-ONLY unless ``--apply``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import yaml  # noqa: E402
from f11_llm_coder import _canon  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config/f11_llm_coder.yaml"


def _read_csv(path: pathlib.Path) -> tuple[list[str], list[list[str]]]:
    """Read a CSV file into (header, rows), preserving every cell verbatim."""
    with path.open(newline="", encoding="utf-8") as fh:
        recs = list(csv.reader(fh))
    return recs[0], [r for r in recs[1:] if any(c.strip() for c in r)]


def _read_jsonl(path: pathlib.Path) -> dict[str, dict]:
    """Read a coder answer file (JSONL; a .md extension is tolerated)."""
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("{"):
            obj = json.loads(line)
            out[str(obj["item_id"])] = obj
    return out


def _menu_keys(menu_path: pathlib.Path, aliases: dict[str, str]) -> dict[str, set[str]]:
    """Normalised key sets for the closed menus (config/closed_menu_v5.json, C12)."""
    menu = json.loads(menu_path.read_text(encoding="utf-8"))
    return {
        section: {_canon(item["value"], aliases) for item in menu[section]}
        for section in ("content_types", "disciplines", "extraction_types")
    }


def _split_ruling(raw: str, keys: dict[str, set[str]], aliases: dict[str, str]) -> tuple[str, str, str]:
    """Split one owner ruling cell into (owner_cont, owner_disc, status).

    A cell may hold one token ('strategic thinking'), two ('principle, cultural design') or a
    declared typo ('priniple'). Each token is validated against the closed menus; a token that
    is in neither menu is kept (so the owner's intent is never silently dropped) and flagged.

    Args:
        raw: the owner's cell, verbatim.
        keys: normalised menu key sets.
        aliases: declared as-written -> canonical aliases.

    Returns:
        (owner_cont, owner_disc, status) - pipe-joined canonical tokens and a ';'-joined flag list.
    """
    status: set[str] = set()
    cont: list[str] = []
    disc: list[str] = []
    tokens = [t.strip() for t in str(raw or "").split(",")]
    if any(not t.strip() for t in tokens) and any(t.strip() for t in tokens):
        status.add("EMPTY_TOKEN")  # e.g. 'principle, ' - a dangling comma, not an empty cell
    if len([t for t in tokens if t]) > 1:
        status.add("SPLIT")
    for token in tokens:
        if not token:
            continue
        key = _canon(token, aliases)
        if key != _canon(token, {}):
            status.add("TYPO_FIXED")
        if key in keys["content_types"]:
            cont.append(key)
        elif key in keys["disciplines"]:
            disc.append(key)
            if key == "emerging":
                status.add("CATCHALL_SLOT_62")
        else:
            disc.append(key)  # the owner's DISC intent, kept verbatim-but-normalised
            status.add("NOT_IN_MENU")
    return "|".join(cont), "|".join(disc), ";".join(sorted(status))


def _sha256_text(text: str) -> str:
    """Return the sha256 hex digest of a string (R14 stamping)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str]) -> int:
    """Rebuild the decision sheet; write only with --apply."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the rebuilt sheet")
    args = parser.parse_args(argv[1:])

    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    ds = cfg["decision_sheet"]
    aliases = {_canon(a["as_written"], {}): _canon(a["canonical"], {}) for a in cfg["declared_aliases"]}
    keys = _menu_keys(ROOT / ds["menu"], aliases)

    base_path = ROOT / ds["base"]
    header, rows = _read_csv(base_path)
    if header[: len(ds["base_header"])] != list(ds["base_header"]):
        raise SystemExit(f"REFUSING: {base_path} does not start with the declared A..R header (C16)")
    n_base = len(ds["base_header"])
    if any(len(r) < n_base for r in rows):
        raise SystemExit("REFUSING: a base row is shorter than the A..R block (C16)")

    i_owner = header.index(ds["owner_input_column"])
    item_col = header.index("item_id")

    ruler_header, ruler_rows = _read_csv(ROOT / cfg["sheet"])
    form_col = ruler_header.index(ds["form_source_column"])
    ruler_item_col = ruler_header.index("item_id")  # NOT column 0: the ruler sheet starts with '#'
    human_form = {r[ruler_item_col]: r[form_col].strip() for r in ruler_rows}

    coder_a = _read_jsonl(ROOT / ds["coder_a_raw"])
    coder_b = _read_jsonl(ROOT / ds["coder_b_raw"])

    new_owner = [ds["form_header"], [ds["separator_header"]], ds["owner_header"]]
    out_header = list(header[:n_base]) + ds["form_header"] + [ds["separator_header"]] + ds["owner_header"]
    out_rows: list[list[str]] = []
    audit: list[list[str]] = []
    flags: dict[str, list[str]] = {}
    form_counts: dict[str, int] = {}

    for row in rows:
        item = row[item_col]
        prefix = list(row[:n_base])  # A..R, verbatim - the owner's work
        raw_ruling = row[i_owner]
        cont, disc, status = _split_ruling(raw_ruling, keys, aliases)
        if status:
            for flag in status.split(";"):
                flags.setdefault(flag, []).append(item)
        f_raw = human_form.get(item, "")
        f_canon = _canon(f_raw, aliases)
        f_a = _canon(coder_a.get(item, {}).get("extraction_type", ""), aliases)
        f_b = _canon(coder_b.get(item, {}).get("extraction_type", ""), aliases)
        if f_raw:
            form_counts[f_raw] = form_counts.get(f_raw, 0) + 1
        out_rows.append(prefix + [f_raw, f_canon, f_a, f_b, "", cont, disc, ""])
        if raw_ruling.strip():
            audit.append([item, raw_ruling, cont, disc, status])

    body = io.StringIO()
    writer = csv.writer(body, lineterminator="\n")
    writer.writerow(out_header)
    writer.writerows(out_rows)
    text = body.getvalue()

    # ── proof: A..R is untouched ──
    before = "\n".join(",".join(r[:n_base]) for r in rows)
    after = "\n".join(",".join(r[:n_base]) for r in out_rows)
    if before != after:
        raise SystemExit("REFUSING: the A..R block changed - aborting (owner work would be at risk)")

    map_body = io.StringIO()
    mw = csv.writer(map_body, lineterminator="\n")
    mw.writerow(["item_id", "human_extra_verbatim", "owner_cont", "owner_disc", "status"])
    mw.writerows(sorted(audit))

    print(f"sheet      : {ds['out']}  ({len(out_rows)} rows x {len(out_header)} cols)")
    print(f"A..R       : byte-identical to the input sheet (sha256 {_sha256_text(before)[:16]})")
    print("header     :")
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for k, name in enumerate(out_header):
        print(f"   {letters[k]}{k + 1:<3} {name}")
    print(f"\nowner cells parsed        : {len(audit)}")
    print(f"  owner_cont filled       : {sum(1 for r in out_rows if r[n_base + 5])}")
    print(f"  owner_disc filled       : {sum(1 for r in out_rows if r[n_base + 6])}")
    print(f"  owner_notes filled      : {sum(1 for r in out_rows if r[n_base + 7])} (blank by design - the owner's free-text column)")
    print(f"  FORM_canonical filled   : {sum(1 for r in out_rows if r[n_base + 1])}/{sum(1 for r in out_rows if r[n_base])} human FORM cells")
    print(f"  FORM_canonical all in menu: {all(not r[n_base + 1] or r[n_base + 1] in keys['extraction_types'] for r in out_rows)}")
    print("\nFORM as-written -> canonical (BUG-367 repair, originals kept in column S):")
    for raw, n in sorted(form_counts.items(), key=lambda kv: -kv[1]):
        canon = _canon(raw, aliases)
        flag = "" if raw == canon.replace("_", " ") or _canon(raw, {}) == canon else "  <- TYPO FIXED"
        print(f"   {n:>4}x  {raw!r:24s} -> {canon}{flag}")
    print("\nflag summary:")
    for flag, items in sorted(flags.items()):
        print(f"   {flag:20s} {len(items):>3}  {', '.join(sorted(items)[:12])}{' ...' if len(items) > 12 else ''}")

    if not args.apply:
        print("\n(dry-run - re-run with --apply)")
        return 0

    safe_write(base_path, text)
    safe_write(ROOT / ds["ruling_map_out"], map_body.getvalue())
    stamp = {
        "schema_version": "1.0",
        "decision": "BUG-368 / BUG-367",
        "created_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "out": ds["out"],
        "sha256": _sha256_text(text),
        "rows": len(out_rows),
        "cols": len(out_header),
        "a_to_r_sha256": _sha256_text(before),
        "owner_cells_parsed": len(audit),
        "flags": {k: len(v) for k, v in flags.items()},
        "gen_model": "none (deterministic rebuild)",
    }
    safe_write(ROOT / "governance/F11_DECISION_SHEET_20260922.stamp.json", json.dumps(stamp, indent=2) + "\n")
    print(f"\n✅ wrote {ds['out']} + {ds['ruling_map_out']} (sha256 {stamp['sha256'][:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
