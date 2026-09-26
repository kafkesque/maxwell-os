#!/usr/bin/env python3
"""Build the CLAIM-SHAPE elicitation instrument (the D1/D2 boundary) - 11 rows, bit blank, depth hidden.

WHY THIS IS NOT THE FORM AXIS
    FORM is AXIS 2 (`extraction_type`, 4 epistemic forms) and it HAS an anchor: owner ANCHOR-3, column
    `extraction_type_final`, 145/150 in governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv (config/anchor_family.yaml).
    The 4 questions below are COMPARATIVE / STATED-EXCHANGE-RATE / BOUNDARY / FALSIFIABLE - that is the
    CLAIM-SHAPE bit, the genuinely un-anchored object (D-374). Naming it FORM caused a false
    "there is NO FORM anchor" claim (BUG-459) and a namespace collision (BUG-461).

WHY BLIND TO DEPTH
    D274d forbids the S4/depth head touching this; the same logic applies here - if the elicitor can see the
    retraction verdict, the score is contaminated and measures reading comprehension of the annex instead.
    `forbid_depth_in_instrument: true` in config/claim_shape_instrument.yaml.

WHY IT REFUSES TO OVERWRITE
    The first version rebuilt the file unconditionally and, on 2026-09-25, silently DROPPED two declared
    columns (evidence_span, abstain) and renamed the gate bit. Nothing was lost only because no answer had
    been written yet. A builder that erases answers once they exist is a data-loss rail (BUG-460).

Output: config/claim_shape_instrument.yaml -> instrument.path
Exit: 0 written | 3 refusing (answered instrument, undeclared cohort, missing source text)
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
CONFIG = REPO / "config" / "claim_shape_instrument.yaml"


def read_text(path: Path) -> str:
    """Decode with the repo's declared order (the owner instruments are Mac Roman)."""
    # D-2646/BUG-516: the decode rule has ONE home. This is a delegating wrapper, not a second rule.
    return artifact_encoding.open_artifact(path, REPO).read()


def load_cfg() -> dict:
    """Load the single declaration of the instrument (paths, cohort, columns, questions)."""
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def load_texts(cfg: dict) -> dict[str, dict[str, str]]:
    """Pull name/DEFINITION/APPLICATION/MECHANISM/BOUNDARY from the two frozen artifacts.

    Raises:
        KeyError: if a declared cohort id has no source text, or the annex carries an undeclared candidate.
    """
    ins = cfg["instrument"]
    candidates = tuple(cfg["cohort"]["candidates"])
    negatives = tuple(cfg["cohort"]["negatives"])
    fields = tuple(cfg["columns"]["source_text"])
    texts: dict[str, dict[str, str]] = {}
    for row in csv.DictReader(io.StringIO(read_text(REPO / ins["source_annex"]))):
        iid = (row.get("item_id") or "").strip()
        if iid in candidates:
            texts[iid] = {k: (row.get(k) or "").strip() for k in ("name",) + fields}
    extra = set(texts) - set(candidates)
    if extra:
        raise KeyError(f"annex contains undeclared candidate ids {sorted(extra)}")
    for row in csv.DictReader(io.StringIO(read_text(REPO / ins["source_sheet"]))):
        iid = (row.get("item_id") or "").strip()
        if iid in negatives:
            texts[iid] = {k: (row.get(k) or "").strip() for k in ("name",) + fields}
    missing = [i for i in candidates + negatives if i not in texts]
    if missing:
        raise KeyError(f"no source text for {missing} - the instrument cannot be built from memory")
    return texts


def answered_cells(path: Path, answered: tuple[str, ...]) -> list[str]:
    """Return the ids of rows that already carry an answer (the non-destructive guard)."""
    if not path.exists():
        return []
    rows = list(csv.DictReader(io.StringIO(read_text(path))))
    return [r.get("item_id", "?") for r in rows
            if any((r.get(c) or "").strip() for c in answered)]


def main() -> int:
    """Write the 11-row instrument, bit blank and depth withheld; refuse if answers already exist."""
    cfg = load_cfg()
    ins = cfg["instrument"]
    out = REPO / ins["path"]
    answered_cols = tuple(cfg["columns"]["answered_cells"])
    already = answered_cells(out, answered_cols)
    if cfg["guards"]["refuse_overwrite_when_answered"] and already:
        print(f"REFUSING: {ins['path']} already carries answers in {already}.")
        print("  Rebuilding would erase them. This builder is for a BLANK instrument only.")
        return 3
    texts = load_texts(cfg)
    header = list(cfg["columns"]["identity"]) + list(cfg["columns"]["source_text"]) + list(cfg["columns"]["answers"])
    rows = []
    for iid in list(cfg["cohort"]["candidates"]) + list(cfg["cohort"]["negatives"]):
        t = texts[iid]
        rows.append({"item_id": iid, "name": t["name"],
                     **{k: t[k] for k in cfg["columns"]["source_text"]},
                     **{k: "" for k in cfg["columns"]["answers"]}})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    qfile = REPO / ins["questions_file"]
    qfile.write_text("\n".join(f"{k}: {v}" for k, v in cfg["questions"].items()) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)} ({len(rows)} rows, gate bit blank)")
    print(f"wrote {qfile.relative_to(REPO)}")
    print("DEPTH IS NOT IN THIS FILE AND MUST NOT BE - the elicitor answers the claim shape blind.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
