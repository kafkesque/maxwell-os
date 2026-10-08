#!/usr/bin/env python3
"""fix_anchor2_content_type_v8.py — split ANCHOR-2 content_type kind axis from disposition.

WHY (owner-gated Option 2, D-2871). The 60-row ANCHOR-2 sheet's content_type_verdict
column (col 6) conflated two orthogonal axes — the 5-role KIND axis (principle /
process_template / process_instance / tool_instruction / growth_edge) and the DISPOSITION
axis (classified / quarantine / noise_drop, already declared in config/content_types.yaml
as NOT-content-types). The pipeline emits `principle` 60/60 (correct: kind axis is closed);
the human column recorded dispositions into the kind axis, producing 10 distinct labels and
kappa 0.0 (BUG-238 hybrid-axis conflation).

TRANSFORM (deterministic, LLM-free — a data transform, not generation; R5 not implicated):
  1. Collapse surface-variant typos on the kind axis:
       'growth edge' -> 'growth_edge', 'process template' -> 'process_template'
  2. Relabel the 8 'quarantine' rows to kind 'principle' (they ARE extractable principles;
     their uncertainty is preserved on the disposition axis, never discarded).
  3. Move the 2 noise_drop rows out of the kind axis (kind = '' — no clean extractable
     principle) and record their disposition.
  4. Add a `disposition_verdict` column (classified | quarantine | noise_drop) so the
     human's uncertainty signal is preserved on the correct axis, not laundered into the
     closed kind vocabulary.

The disposition vocabulary is read from config/content_types.yaml#dispositions (C12:
never hardcoded). The kind vocabulary is the closed 5-role set from the same file.

OUTPUT (crash-safe; original untouched):
  governance/ANCHOR2_BLIND_SHEET_V8_CTFIX_20261008.csv

VERIFY (--check): 60 rows, kind in {5 closed roles, ''}, disposition in the declared
dispositions, exactly 8 quarantine + 2 noise_drop dispositions, zero typos survive.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

SHEET = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_V8_20261007.csv"
TAXONOMY = ROOT / "config" / "content_types.yaml"
OUT = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_V8_CTFIX_20261008.csv"

# Surface-variant typo collapse on the KIND axis (data hygiene, not vocabulary change).
# The canonical forms are the closed 5-role keys in config/content_types.yaml.
KIND_TYPO = {
    "growth edge": "growth_edge",
    "process template": "process_template",
}


def _norm(s: str) -> str:
    return (s or "").strip()


def load_ontology() -> tuple[set[str], set[str]]:
    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    kinds = set(tax["content_types"].keys())
    dispositions = set(tax["dispositions"].keys())
    return kinds, dispositions


def transform(rows: list[list[str]], kinds: set[str]) -> tuple[list[list[str]], dict]:
    """Apply the kind/disposition split. Returns (new_rows, stats)."""
    header = rows[0]
    # insert disposition_verdict right after content_type_verdict (col 6 -> col 7)
    new_header = list(header)
    # header is: row, fb_id, name, definition, discipline_verdict, domains_verdict,
    #            content_type_verdict, '', '', '', ''
    # make col 7 a named disposition_verdict, keep remaining note cols
    if len(new_header) <= 7:
        new_header += [""] * (8 - len(new_header))
    new_header[7] = "disposition_verdict"

    out = [new_header]
    stats = {"quarantine_relabeled": 0, "noise_drop_moved": 0, "typos_fixed": 0}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        new = list(r)
        while len(new) < len(new_header):
            new.append("")
        raw = _norm(new[6]) if len(new) > 6 else ""
        # kind-axis normalization
        if raw in KIND_TYPO:
            stats["typos_fixed"] += 1
            raw = KIND_TYPO[raw]
        disposition = "classified"
        if raw == "quarantine":
            raw = "principle"          # owner Option 2: quarantine is a disposition, not a kind
            disposition = "quarantine"
            stats["quarantine_relabeled"] += 1
        elif raw in ("noise drop", "noise_drop"):
            raw = ""                    # no clean extractable principle -> empty kind
            disposition = "noise_drop"
            stats["noise_drop_moved"] += 1
        new[6] = raw
        new[7] = disposition
        out.append(new[: len(new_header)])
    return out, stats


def _crash_safe_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main() -> int:
    check = "--check" in sys.argv
    kinds, dispositions = load_ontology()
    rows = list(csv.reader(SHEET.read_text(encoding="utf-8").splitlines()))
    out, stats = transform(rows, kinds)

    # validation
    errs: list[str] = []
    n = 0
    q = nd = 0
    for r in out[1:]:
        if not r or not r[0].strip():
            continue
        n += 1
        kind = _norm(r[6]) if len(r) > 6 else ""
        disp = _norm(r[7]) if len(r) > 7 else ""
        if kind and kind not in kinds:
            errs.append(f"row {r[0]} OOV kind: {kind!r}")
        if disp not in dispositions:
            errs.append(f"row {r[0]} OOV disposition: {disp!r}")
        if disp == "quarantine":
            q += 1
        elif disp == "noise_drop":
            nd += 1

    # assemble CSV text
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(out)
    text = buf.getvalue()

    print(f"CHECK: rows={n} quarantine_disposition={q} noise_drop_disposition={nd} "
          f"stats={stats} OOV={len(errs)}")
    for e in errs:
        print("  OOV: " + e)
    ok = (not errs) and n == 60 and q == 8 and nd == 2 and stats["typos_fixed"] == 9
    print("CHECK " + ("PASS" if ok else "FAIL"))
    if check:
        return 0 if ok else 1

    _crash_safe_write(OUT, text)
    print(f"wrote {OUT.relative_to(ROOT)} ({n} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
