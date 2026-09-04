#!/usr/bin/env python3
"""scripts/measure_deberta_truncation.py — MEASURE-DEBERTA (D2553).

Quantify DeBERTa-v3-large 512-token truncation exposure across the FB corpus.

Context: stage5_verify.py truncates premise (evidence passage) and hypothesis
(definition) to S5_NLI_MAX_PREMISE_CHARS / S5_NLI_MAX_HYPOTHESIS_CHARS
(default 256 chars each) BEFORE the HF pipeline, which itself truncates to
DeBERTa's 512-token window. This script measures how much content is lost to
the char-truncation and how often the 512-token window would bind if the
char-truncation were removed.

Outputs:
  - governance/measure_deberta_truncation.json (raw numbers)
  - governance/measure_deberta_truncation.md   (human report)

Uses only the tokenizer (fast, cached), not the full model.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    S5_NLI_MAX_HYPOTHESIS_CHARS,
    S5_NLI_MAX_PREMISE_CHARS,
    S5_NLI_MODEL_LARGE,
)

DEBERTA_MODEL = S5_NLI_MODEL_LARGE  # C12: config models.nli_large (single source)
DEBERTA_MAX_TOKENS = 512  # fixed model-architecture limit (C20 named constant, not config)
MAX_EVIDENCE_PASSAGES = 8  # mirrors stage5_verify.py _eps[:8] (pre-existing constant)


def _pct(num: int, den: int) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


def _percentile(sorted_vals: list[int], p: float) -> int:
    if not sorted_vals:
        return 0
    idx = int(round((p / 100.0) * (len(sorted_vals) - 1)))
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure DeBERTa 512-token truncation exposure.")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to maxwell.db")
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(DEBERTA_MODEL)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute("SELECT fb_id, definition, evidence_passages FROM fbs"))
    conn.close()

    n = len(rows)
    definitions: list[str] = []
    evidence_passages: list[list[str]] = []
    malformed_evidence: int = 0  # C16: never silently drop malformed evidence
    for r in rows:
        definitions.append(r["definition"] or "")
        raw = r["evidence_passages"] or "[]"
        try:
            eps = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            malformed_evidence += 1
            eps = []
        if not isinstance(eps, list):
            malformed_evidence += 1
            eps = []
        evidence_passages.append([str(e) for e in eps[:MAX_EVIDENCE_PASSAGES] if str(e).strip()])

    # Tokenize definitions in batch.
    def_enc = tok(definitions, add_special_tokens=True, truncation=False)
    def_tokens = [len(ids) for ids in def_enc["input_ids"]]
    def_chars = [len(d) for d in definitions]

    # Tokenize evidence passages (flattened), track per-FB max passage tokens.
    flat_eps: list[str] = []
    fb_ep_idx: list[list[int]] = []
    for eps in evidence_passages:
        idxs: list[int] = []
        for ep in eps:
            idxs.append(len(flat_eps))
            flat_eps.append(ep)
        fb_ep_idx.append(idxs)

    ep_enc = tok(flat_eps, add_special_tokens=True, truncation=False) if flat_eps else {"input_ids": []}
    ep_tokens = [len(ids) for ids in ep_enc["input_ids"]]

    max_passage_tokens: list[int] = []
    max_passage_chars: list[int] = []
    for idxs in fb_ep_idx:
        if idxs:
            max_passage_tokens.append(max(ep_tokens[i] for i in idxs))
            max_passage_chars.append(max(len(flat_eps[i]) for i in idxs))
        else:
            max_passage_tokens.append(0)
            max_passage_chars.append(0)

    # Combined premise+hypothesis (DeBERTa window binding).
    combined = [d + m for d, m in zip(def_tokens, max_passage_tokens)]

    def_tokens_sorted = sorted(def_tokens)
    max_pass_sorted = sorted(max_passage_tokens)
    combined_sorted = sorted(combined)

    stats = {
        "total_fbs": n,
        "malformed_evidence_rows": malformed_evidence,
        "char_limits": {"premise_chars": S5_NLI_MAX_PREMISE_CHARS, "hypothesis_chars": S5_NLI_MAX_HYPOTHESIS_CHARS},
        "definition": {
            "over_hyp_chars": sum(1 for c in def_chars if c > S5_NLI_MAX_HYPOTHESIS_CHARS),
            "pct_over_hyp_chars": _pct(sum(1 for c in def_chars if c > S5_NLI_MAX_HYPOTHESIS_CHARS), n),
            "over_512_tokens": sum(1 for t in def_tokens if t > DEBERTA_MAX_TOKENS),
            "pct_over_512_tokens": _pct(sum(1 for t in def_tokens if t > DEBERTA_MAX_TOKENS), n),
            "median_tokens": _percentile(def_tokens_sorted, 50),
            "p90_tokens": _percentile(def_tokens_sorted, 90),
            "p95_tokens": _percentile(def_tokens_sorted, 95),
            "max_tokens": def_tokens_sorted[-1] if def_tokens_sorted else 0,
        },
        "evidence_max_passage": {
            "over_premise_chars": sum(1 for c in max_passage_chars if c > S5_NLI_MAX_PREMISE_CHARS),
            "pct_over_premise_chars": _pct(sum(1 for c in max_passage_chars if c > S5_NLI_MAX_PREMISE_CHARS), n),
            "over_512_tokens": sum(1 for t in max_passage_tokens if t > DEBERTA_MAX_TOKENS),
            "pct_over_512_tokens": _pct(sum(1 for t in max_passage_tokens if t > DEBERTA_MAX_TOKENS), n),
            "median_tokens": _percentile(max_pass_sorted, 50),
            "p90_tokens": _percentile(max_pass_sorted, 90),
            "p95_tokens": _percentile(max_pass_sorted, 95),
            "max_tokens": max_pass_sorted[-1] if max_pass_sorted else 0,
        },
        "combined_premise_hypothesis": {
            "over_512_tokens": sum(1 for t in combined if t > DEBERTA_MAX_TOKENS),
            "pct_over_512_tokens": _pct(sum(1 for t in combined if t > DEBERTA_MAX_TOKENS), n),
            "median_tokens": _percentile(combined_sorted, 50),
            "p90_tokens": _percentile(combined_sorted, 90),
            "max_tokens": combined_sorted[-1] if combined_sorted else 0,
        },
    }

    gov_dir = _ROOT / "governance"
    gov_dir.mkdir(parents=True, exist_ok=True)
    (gov_dir / "measure_deberta_truncation.json").write_text(json.dumps(stats, indent=2) + "\n")

    d = stats["definition"]
    e = stats["evidence_max_passage"]
    c = stats["combined_premise_hypothesis"]
    md = f"""# MEASURE-DEBERTA — 512-token truncation exposure (D2553)

**Corpus:** {n} FBs (maxwell.db) · **Tokenizer:** DeBERTa-v3-large · **Window:** 512 tokens
**Current char-truncation:** premise={S5_NLI_MAX_PREMISE_CHARS} chars, hypothesis={S5_NLI_MAX_HYPOTHESIS_CHARS} chars
**Malformed evidence rows (C16-reported):** {stats['malformed_evidence_rows']}

## Definition (hypothesis)
| Metric | Value |
|---|---|
| Over {S5_NLI_MAX_HYPOTHESIS_CHARS}-char truncation | {d['over_hyp_chars']} ({d['pct_over_hyp_chars']}%) |
| Over 512 tokens (would exceed DeBERTa alone) | {d['over_512_tokens']} ({d['pct_over_512_tokens']}%) |
| Token length median / p90 / p95 / max | {d['median_tokens']} / {d['p90_tokens']} / {d['p95_tokens']} / {d['max_tokens']} |

## Evidence (max single passage)
| Metric | Value |
|---|---|
| Over {S5_NLI_MAX_PREMISE_CHARS}-char truncation | {e['over_premise_chars']} ({e['pct_over_premise_chars']}%) |
| Over 512 tokens | {e['over_512_tokens']} ({e['pct_over_512_tokens']}%) |
| Token length median / p90 / p95 / max | {e['median_tokens']} / {e['p90_tokens']} / {e['p95_tokens']} / {e['max_tokens']} |

## Combined (premise + hypothesis) — DeBERTa window binding
| Metric | Value |
|---|---|
| Over 512 tokens | {c['over_512_tokens']} ({c['pct_over_512_tokens']}%) |
| Token length median / p90 / max | {c['median_tokens']} / {c['p90_tokens']} / {c['max_tokens']} |

## Verdict
The binding constraint is the **256-char truncation**, not DeBERTa's 512-token
window: {d['pct_over_hyp_chars']}% of definitions exceed 256 chars (content lost),
but only {d['pct_over_512_tokens']}% would exceed 512 tokens if untruncated.
"""
    (gov_dir / "measure_deberta_truncation.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
