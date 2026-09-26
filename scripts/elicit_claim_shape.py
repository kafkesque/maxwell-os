#!/usr/bin/env python3
"""Elicit the D-374 CLAIM-SHAPE bit blind, with a NON-AUTHOR elicitor (D-395).

WHY A NON-AUTHOR, AND WHY THAT IS NOT A FORMALITY
    The gate rule was DERIVED from the same 11 rows it is supposed to explain (4 universal candidates,
    7 class-1 calls the owner RETRACTED). A reading produced by the rule's author is the rule restated,
    not evidence about the rule, so `guards.refuse_elicitor: [assistant]` makes the author's own answer a
    REFUSAL, not a weaker score. This script is the only path that produces a legitimate column: the
    judgment comes from a declared LOCAL model that has no access to the cohort, the retraction verdicts,
    or the depth axis.

WHY THE `item_id` IS WITHHELD (blind_identity)
    The instrument's ids are `U001..U004` and `R033..R139`. A coder that sees `U` may infer "candidate",
    which is the outcome. The prompt therefore carries a NEUTRAL row counter; the item_id is re-attached
    by this script, locally, after the answer exists. Blindness that is not enforced by the code is a
    claim, not a property (the BUG-476 class: a declaration no consumer can falsify).

WHY IT WRITES ATOMICALLY AND REFUSES TO OVERWRITE
    An elicitation that can be silently re-run is an elicitation that can be silently tuned. Every cell is
    written through tempfile -> fsync -> os.replace (C6), and a file that already holds an answer is
    refused (config: guards.refuse_overwrite_when_answered).

Usage:
    python3 scripts/elicit_claim_shape.py --model Qwen3.8-27B-MLX-4bit [--out <csv>] [--dry-run]
Exit: 0 all rows elicited and written | 1 a row could not be elicited (fail closed, nothing written)
      | 3 refusing (no model declared / file already answered / no non-author elicitor)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
if str(REPO) not in sys.path:  # the repo root is not on sys.path when a script is run by path
    sys.path.insert(0, str(REPO))
CONFIG = REPO / "config" / "claim_shape_instrument.yaml"
JSON_RE = re.compile(r"\{.*\}", re.S)


class ElicitError(RuntimeError):
    """A row that could not be elicited. Never swallowed (C16)."""


def read_text(path: Path) -> str:
    """Decode with the repo's declared order (the pack holds mac_roman-era bytes)."""
    # D-2646/BUG-516: the decode rule has ONE home. This is a delegating wrapper, not a second rule.
    return artifact_encoding.open_artifact(path, REPO).read()


def write_atomic(path: Path, text: str) -> None:
    """Write through tempfile -> fsync -> os.replace so a crash cannot leave a half instrument (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_config() -> dict:
    """Load the instrument declaration; a missing elicitor block is a configuration defect, not a default."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if not cfg.get("elicitors"):
        raise ElicitError("config/claim_shape_instrument.yaml has no `elicitors` block - refusing to invent one")
    return cfg


def build_prompt(cfg: dict, questions: dict[str, str], row: dict[str, str], slot: int) -> str:
    """Build the blind prompt: declared blind columns only, neutral row label, no cohort, no verdict."""
    cols = list(cfg["elicitors"]["blind_columns"])
    missing = [c for c in cols if c not in row]
    if missing:
        raise ElicitError(f"instrument row lacks declared blind column(s) {missing}")
    body = "\n".join(f"{c}: {row[c]}" for c in cols if c not in ("item_id",) and (row.get(c) or "").strip())
    qs = "\n".join(f"  q{i}: {questions[k]}" for i, k in enumerate(sorted(questions), start=1))
    return (f"ROW {slot} (identity withheld on purpose - judge the text, not the row number)\n{body}\n\n"
            f"QUESTIONS (answer each with 1 = yes, 0 = no, null = cannot be determined from the text):\n{qs}\n\n"
            "Return ONLY a JSON object with keys q1..q4, each 0 or 1 or null, plus "
            "\"evidence_span\" (a VERBATIM span copied from the text above that decides q1) and "
            "\"note\" (one short sentence naming which question you found hardest and why). "
            "No prose outside the JSON.")


def ask(model: str, prompt: str, cfg: dict) -> dict:
    """Ask one declared elicitor for one row's bits. Strict parse: an unparsable answer is a refusal."""
    from pipeline.omlx_call import call_omlx  # imported late so --dry-run needs no backend

    system = ("You are a taxonomy coder applying four questions to a short text. You are blind to what the "
              "answers will be used for. Answer from the text given; do not consult outside knowledge.")
    raw = call_omlx(prompt, model=model, system=system,
                    max_tokens=int(cfg["elicitors"]["max_tokens"]),
                    timeout=int(cfg["elicitors"]["timeout_s"]))
    m = JSON_RE.search(raw or "")
    if not m:
        raise ElicitError(f"{model}: no JSON object in reply: {(raw or '')[:160]!r}")
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ElicitError(f"{model}: reply is not valid JSON: {exc}") from exc
    return obj


def main() -> int:
    """Run every declared elicitor over every row and write one instrument per elicitor."""
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="declared elicitor (default: elicitors.primary)")
    ap.add_argument("--out", type=Path, default=None, help="output CSV (default: instrument.path)")
    ap.add_argument("--force", action="store_true", help="allow overwriting an ANSWERED instrument")
    ap.add_argument("--limit", type=int, default=0, help="elicit only the first N rows (dry inspection)")
    args = ap.parse_args()
    elicitors = cfg["elicitors"]
    model = args.model or elicitors.get("primary")
    declared = list(elicitors.get("declared") or [])
    if not model:
        print("REFUSING: no elicitor declared (elicitors.primary) and none passed")
        return 3
    if model not in declared:
        print(f"REFUSING: {model!r} is not a declared elicitor {declared} - an undeclared elicitor is an "
              "undeclared instrument")
        return 3
    if model.lower() in {str(x).lower() for x in cfg["guards"]["refuse_elicitor"]}:
        print(f"REFUSING: {model!r} is the rule's author (guards.refuse_elicitor) - a restatement is not evidence")
        return 3
    questions = cfg["questions"]
    src = REPO / cfg["instrument"]["path"]
    out = args.out or src
    rows = list(csv.DictReader(io.StringIO(read_text(src))))
    fieldnames = list(rows[0].keys())
    answered = [c for c in cfg["columns"]["answered_cells"] if c in fieldnames]
    if out.exists() and not args.force:
        prev = list(csv.DictReader(io.StringIO(read_text(out))))
        filled = [r["item_id"] for r in prev if any((r.get(c) or "").strip() for c in answered)]
        if filled:
            print(f"REFUSING: {out} already holds answers ({len(filled)} row(s): {filled[:4]}) - "
                  "guards.refuse_overwrite_when_answered")
            return 3
    todo = rows[: args.limit] if args.limit else rows
    print(f"elicitor {model}  rows {len(todo)}  blind columns {elicitors['blind_columns']}  "
          f"identity withheld {bool(elicitors.get('blind_identity'))}")
    for slot, r in enumerate(todo, start=1):
        prompt = build_prompt(cfg, questions, r, slot)
        if args.out is None and slot == 1:
            print("--- first prompt (verbatim) ---")
            print(prompt[:700])
            print("--- end ---")
        obj = ask(model, prompt, cfg)
        bits = {}
        for i in range(1, 5):
            v = obj.get(f"q{i}")
            if v not in (0, 1):
                raise ElicitError(f"{model}: row {slot} q{i}={v!r} is not 0/1 - a null is not an answer")
            bits[f"claim_shape_q{i}"] = str(int(v))
        r.update(bits)
        required = list(cfg["bit_rule"]["required"])
        r["claim_shape_bit"] = "1" if all(r[k] == "1" for k in required) else "0"
        span = str(obj.get("evidence_span") or "").strip()
        hay = " ".join((r.get(c) or "") for c in elicitors["blind_columns"])
        note = str(obj.get("note") or "").strip()
        if span and span.split(" ")[0][:24] not in hay:
            note = (note + " | evidence_span_not_verbatim").strip(" |")
        r["evidence_span"] = span
        r["abstain"] = "0"
        r["claim_shape_note"] = note
        r["elicitor"] = model
        r["date"] = date.today().isoformat()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    write_atomic(out, buf.getvalue())
    ones = sum(1 for r in rows if r.get("claim_shape_bit") == "1")
    print(f"ok wrote {out.resolve().relative_to(REPO)} - {len(rows)} row(s), bit=1 on {ones}, "
          "elicitor recorded per row")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ElicitError as exc:
        print(f"FAIL elicitation: {exc}")
        sys.exit(1)
