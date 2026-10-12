#!/usr/bin/env python3
"""T9 (BUG-705): label the paraphrase gold draft with a different-family LLM proxy.

Reads governance/t9_paraphrase_gold_draft.jsonl (seeded blind-stratified NEUTRAL rows,
label='TBD') and labels each row {paraphrase_true|non_paraphrase} using a NON-generator
model family (gemma-4-E4B-it-MLX-4bit). This enforces R5 (generator != verifier): the
generator is Qwen3-Coder-30B, the labeller is gemma-4-E4B — a different family.

The judgement is a strict paraphrase/NLI-recall question: does the EVIDENCE restate or
directly support the DEFINITION's claim (=> paraphrase_true, the strict NLI NEUTRAL should
be recovered), or not (=> non_paraphrase, the NEUTRAL is correct). Output is provenance-
preserving: every input field is carried through, only label flips from 'TBD' to the verdict.

Fail-closed (C16): any row whose verdict cannot be unambiguously parsed is recorded with
label='ERROR:<reason>' and reported; it is NEVER guessed. temp=0.0 via call_omlx (R7).

Usage:
    python3 scripts/t9_paraphrase_label.py \
        --in governance/t9_paraphrase_gold_draft.jsonl \
        --out governance/t9_paraphrase_gold_labelled.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx  # noqa: E402
from pipeline.pipeline_paths import PROJECT_ROOT  # noqa: E402

LABEL_MODEL = "gemma-4-E4B-it-MLX-4bit"
SCHEMA_VERSION = "1.0"
VALID_LABELS = ("paraphrase_true", "non_paraphrase")
_MAX_TOKENS = 32
_DELAY_SECONDS = 0.2


def _pipeline_commit() -> str:
    """Return the current git HEAD short hash, or 'unknown' if unavailable."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), capture_output=True, text=True, check=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


_PROMPT_TEMPLATE = (
    "You are a strict paraphrase annotator for a knowledge pipeline.\n"
    "A DEFINITION is the claim to be verified. An EVIDENCE passage is source text.\n"
    "Judge whether the EVIDENCE is a genuine PARAPHRASE of the DEFINITION: it restates "
    "or directly supports the same specific claim in different words, such that a strict "
    "NLI gate that marked it NEUTRAL should instead recover it as SUPPORTED.\n"
    "Reply with EXACTLY ONE token and nothing else.\n\n"
    "DEFINITION: {definition}\n\n"
    "EVIDENCE: {evidence}\n\n"
    "Verdict (paraphrase_true or non_paraphrase):"
)


def _parse_verdict(text: str) -> str:
    """Parse the model's verdict fail-closed. Never guesses."""
    lowered = text.strip().lower()
    hits = [label for label in VALID_LABELS if label in lowered]
    if not hits:
        return "ERROR:no_verdict"
    # Models occasionally restate the prompt then answer; take the LAST explicit verdict.
    return hits[-1]


def _label_row(row: dict) -> dict:
    """Label one row with gemma-4-E4B (different family). Returns a provenance-preserved row."""
    prompt = _PROMPT_TEMPLATE.format(
        definition=row["definition"], evidence=row["evidence"],
    )
    try:
        raw = call_omlx(
            prompt,
            model=LABEL_MODEL,
            system=None,
            max_tokens=_MAX_TOKENS,
        )
    except Exception as exc:  # noqa: BLE001 — C16: log AND surface, never swallow
        verdict = f"ERROR:call_failed:{type(exc).__name__}"
        print(f"[FAIL] fb_id={row.get('fb_id')}: {verdict}", file=sys.stderr)
    else:
        verdict = _parse_verdict(raw)

    labelled = dict(row)
    labelled["label"] = verdict
    labelled["label_model"] = LABEL_MODEL
    labelled["schema_version"] = SCHEMA_VERSION
    labelled["pipeline_commit"] = _pipeline_commit()
    return labelled


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    if not in_path.is_absolute():
        in_path = PROJECT_ROOT / in_path
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path

    rows = [json.loads(line) for line in in_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Labelling {len(rows)} rows with {LABEL_MODEL} (temp=0.0, R5 different-family)")

    labelled: list[dict] = []
    errors: list[dict] = []
    for i, row in enumerate(rows, start=1):
        out = _label_row(row)
        if out["label"].startswith("ERROR"):
            errors.append(out)
        labelled.append(out)
        print(f"[{i}/{len(rows)}] fb_id={row.get('fb_id')} bucket={row.get('bucket')} -> {out['label']}")
        time.sleep(_DELAY_SECONDS)

    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in labelled) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {len(labelled)} rows to {out_path}")

    n_err = len(errors)
    n_ok = len(labelled) - n_err
    print(f"SUMMARY: {n_ok} labelled OK, {n_err} fail-closed (NOT guessed)")
    if n_err:
        print("FAIL-CLOSED ROWS (re-run manually / inspect):")
        for e in errors:
            print(f"  fb_id={e.get('fb_id')} bucket={e.get('bucket')} -> {e['label']}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
