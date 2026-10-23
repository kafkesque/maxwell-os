#!/usr/bin/env python3
"""rule_content_type_census.py — noob-proof OWNER ruling of the BUG-977 census rows (D-3100).

WHY THIS EXISTS. Ten rows in the store carry a DISPOSITION ('noise_drop' | 'quarantine') where a ROLE belongs,
six of them in the DEFAULT ANSWER PATH (BUG-977). No script may rule them: a content_type is a curation
judgement (D-2898: never auto-certified), and the vocabulary split says a disposition is not a role (BUG-741).
So the ruling is the owner's, and this tool exists because the LAST hand-off of this shape ("append a line to a
JSONL") ended with the owner pasting JSON into zsh and getting `zsh: command not found` (BUG-588's shape applied
to an instruction — the reason scripts/rule_tier_b.py exists).

WHAT IT DOES. It asks the ONE question the store cannot answer — "what ROLE does this row carry?" — one row at a
time, and appends the answer to the OWNER'S OWN adjudication map (governance/content_type_adjudication.json), the
warrant home the re-stamp gate already reads (config/content_types.yaml#adjudication_map). It never writes the
store: after the rulings land, the gate is re-run and `--apply` does the write with provenance `human_verbatim`.

Each row offers exactly three kinds of answer:
  * a ROLE (principle | process_template | process_instance | tool_instruction | growth_edge) — the row STAYS and
    is re-labelled;
  * a DISPOSITION (noise_drop | quarantine) — the row is NOT knowledge: the store keeps it out of the served path
    through the declared act (config/content_type_restamp.yaml#dispositions.act_for_stored_row);
  * skip — no ruling yet; the row stays in the debt and the census keeps reporting it (never a silent default).

Safety (D-3034 / C6 / C16): every append is atomic (tempfile -> fsync -> os.replace); a duplicate (fb_id) ruling
is REFUSED, not doubled; the `current` label is read from the STORE at ruling time so a stale premise cannot be
written; an unknown answer refuses loudly and nothing is written. No LLM anywhere (D-343) — deterministic.

usage:  python3 scripts/rule_content_type_census.py            # dry-run: show the sheet only
        python3 scripts/rule_content_type_census.py --apply    # walk the rows, write the rulings
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MAP_PATH = PROJECT_ROOT / "governance" / "content_type_adjudication.json"
DB_DEFAULT = "knowledge pipeline/maxwell.db"


def load_vocab() -> tuple[list[str], list[str]]:
    """Return (roles, dispositions) READ from their one home — never restated here (C12/D-2646)."""
    import yaml

    doc = yaml.safe_load((PROJECT_ROOT / "config" / "content_types.yaml").read_text(encoding="utf-8")) or {}
    roles = [str(k) for k in (doc.get("content_types") or {})]
    dispositions = [str(k) for k in (doc.get("dispositions") or {})]
    if not roles or not dispositions:
        raise SystemExit(
            f"FAIL-CLOSED: config/content_types.yaml yielded roles={roles} dispositions={dispositions}"
        )
    return roles, dispositions


def census_rows(db: Path) -> list[dict[str, str]]:
    """The rows the census says owe a ruling, with their LIVE label (the warrant's pre-state)."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return [
            {"fb_id": str(fid), "name": str(name or ""), "current": str(ct or "").strip(),
             "status": str(st or "")}
            for fid, name, ct, st in conn.execute(
                "select fb_id, name, content_type, status from fbs order by content_type, name"
            )
        ]
    finally:
        conn.close()


def owing(rows: list[dict[str, str]], roles: list[str], dispositions: list[str]) -> list[dict[str, str]]:
    """A row OWES a ruling when its label is not a declared ROLE (disposition, undeclared, or blank)."""
    return [r for r in rows if r["current"] not in roles]


def merge_rulings(existing: list[dict], answers: list[dict]) -> list[dict]:
    """Append rulings, refusing a duplicate fb_id (never a silent second opinion)."""
    seen = {str(r.get("fb_id")) for r in existing}
    clash = [a["fb_id"] for a in answers if a["fb_id"] in seen]
    if clash:
        raise SystemExit(f"REFUSED: these fb_id(s) already carry a ruling in the map: {clash[:5]} - edit that "
                         f"row's reason instead of adding a second opinion")
    return existing + answers


def write_atomic(path: Path, payload: dict) -> None:
    """tempfile -> fsync -> os.replace (C6): a half-written warrant map is worse than no map."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".adjudication_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def ask(row: dict[str, str], roles: list[str], dispositions: list[str]) -> dict | None:
    """Ask the ONE question for one row; return the map row, or None to skip."""
    served = "IN THE ANSWER PATH" if row["status"] == "PASS" else "held (not served)"
    print("\n" + "-" * 78)
    print(f"{row['name']!r}")
    print(f"  stored label : {row['current']!r}   [{served}]   fb_id {row['fb_id'][:16]}...")
    print("  ROLE         : " + " | ".join(roles))
    print("  DISPOSITION  : " + " | ".join(dispositions) + "   (not knowledge — row leaves the served path)")
    print("  or: skip (no ruling yet)")
    answer = input("  > ").strip().lower()
    if answer in ("", "s", "skip"):
        return None
    if answer not in roles and answer not in dispositions:
        print(f"  ✗ {answer!r} is not in either declared vocabulary — nothing written for this row")
        return None
    reason = input("  one-line reason (optional): ").strip()
    entry: dict[str, str] = {"fb_id": row["fb_id"], "current": row["current"],
                             "confidence": "high", "reason": reason or "owner ruling (BUG-977 census)"}
    if answer in roles:
        entry["proposed_content_type"] = answer
    else:
        entry["proposed_disposition"] = answer
    print(f"  ✓ ruled: {row['current']!r} -> {answer!r}")
    return entry


def main() -> int:
    ap = argparse.ArgumentParser(description="The OWNER's ruling walker for the BUG-977 census rows.")
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--apply", action="store_true", help="walk the rows and WRITE the rulings (default: show the sheet)")
    args = ap.parse_args()

    roles, dispositions = load_vocab()
    db = PROJECT_ROOT / args.db
    if not db.exists():
        raise SystemExit(f"FAIL-CLOSED: store not found at {db}")
    owed = owing(census_rows(db), roles, dispositions)
    print(f"BUG-977 census: {len(owed)} row(s) owe a ruling "
          f"({sum(1 for r in owed if r['status'] == 'PASS')} of them in the answer path)")
    if not owed:
        print("nothing owed — every stored content_type is a declared ROLE.")
        return 0
    if not args.apply:
        for r in owed:
            print(f"  {r['current']:12} status={r['status']:10} {r['name'][:70]!r}")
        print("\n[dry-run] rerun with --apply to walk them one at a time and write the rulings.")
        return 0

    answers = [a for a in (ask(r, roles, dispositions) for r in owed) if a is not None]
    if not answers:
        print("\nnothing ruled — the map is unchanged, and the census keeps reporting every row.")
        return 0
    payload = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    key = "rows"
    existing = payload.get(key)
    if not isinstance(existing, list):
        raise SystemExit(f"FAIL-CLOSED: {MAP_PATH.relative_to(PROJECT_ROOT)}#{key} is not a list")
    payload[key] = merge_rulings(existing, answers)
    write_atomic(MAP_PATH, payload)
    print(f"\nwrote {len(answers)} ruling(s) -> {MAP_PATH.relative_to(PROJECT_ROOT)} "
          f"(map now {len(payload[key])} rows)")
    print("NEXT: python3 scripts/restamp_content_type_adjudications.py          # dry-run: the write set appears")
    print("      python3 scripts/restamp_content_type_adjudications.py --apply # writes the labels + human_verbatim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
