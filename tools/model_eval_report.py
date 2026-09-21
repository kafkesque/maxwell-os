#!/usr/bin/env python3
"""Aggregate governance/model_eval_checkpoint.jsonl into a model x suite table.

Reports, per (model, suite): accuracy, n graded, parse/transport failures, and
median latency. Also emits the long-context breakdown by context size and the
stability self-agreement rate (how often a model gave the same answer 3x).

Usage:
  python3 tools/model_eval_report.py
  python3 tools/model_eval_report.py --md governance/model_eval_report.md
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CKPT = ROOT / "governance" / "model_eval_checkpoint.jsonl"

SUITE_ORDER = ["stability", "toolcalling", "planning", "reviewing", "hardcode",
               "mbpp", "humaneval", "mmlu_pro", "gsm8k", "math500", "ifeval",
               "hotpot_qa", "lc_reasoning", "niah"]

# Models pruned from the portfolio. Their checkpoint rows are historical and are kept
# (append-only log), but they MUST NOT appear in the decision table: a pruned model
# still shows numbers, and those numbers get quoted into consolidation docs as if the
# model were still a candidate (and a pruned model's 404s read as model failures —
# BUG-253 class). They are reported in a separate PRUNED section instead.
PRUNED_MODELS = [
    "granite-4.2-8b-MLX-8bit",
    "gemma-4-12B-it-qat-OptiQ-4bit",
    "Ornith-1.5-9B-OptiQ-4bit",           # lost the 4bit/8bit A/B, Prune #4
    "Qwen3.8-27B-OptiQ-4bit",            # 31% 'no json' output-contract failure + 4.6x slower, 2026-09-16
]

# Individual ITEMS that were later found invalid. Their checkpoint rows are kept (append-only
# record of the mistake) but must not enter any accuracy figure, or a bad item silently lowers
# every model's score — the exact way a harness defect becomes a "model result" (BUG-253/258).
# plan-* : 17 hand-written planning items, 13 of them failed by all 7 models; the gold answers
# were typed and wrong (crew 8 not 6, parallel 9 not 6, mix 50 not 8, deadline 0 not 5). Replaced
# by tools/plan_cases_generated.py with computed answers (plangen-*).
INVALID_ITEM_IDS = {
    "plan-cans", "plan-batch", "plan-crew", "plan-overlap", "plan-queue", "plan-prior",
    "plan-cache", "plan-retry", "plan-route", "plan-split", "plan-budget2", "plan-mix",
    "plan-deadline", "plan-alloc", "plan-tradeoff", "plan-shift", "plan-parallel",
}


def load() -> list[dict]:
    """Load all checkpoint rows, skipping malformed lines."""
    if not CKPT.exists():
        return []
    rows = []
    for line in CKPT.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def main() -> int:
    """Print (and optionally write) the aggregated evaluation report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=None, help="also write a markdown report here")
    args = ap.parse_args()

    rows = load()
    if not rows:
        print("no checkpoint rows yet")
        return 0

    acc: dict[tuple[str, str], list[int]] = defaultdict(list)
    lat: dict[tuple[str, str], list[float]] = defaultdict(list)
    errs: dict[str, int] = defaultdict(int)
    na: dict[str, int] = defaultdict(int)
    invalid = 0
    for r in rows:
        # A row with err set is a measurement we never took (404, 400, timeout), NOT a
        # model failure. Counting it as 0 corrupts the accuracy of every model that was
        # unlucky enough to be running during an oMLX outage — REAP's 43 stale 404s
        # would drag its toolcalling from 1.00 to 0.50 and its planning from 1.00 to
        # 0.50, which is precisely the kind of phantom that drives a wrong portfolio
        # decision (BUG-253 class: identical scores across different-ability models are
        # a harness signal). Same rule as model_eval_suite._done_keys().
        # A preflight-invalid cell (na: True) is a measurement the harness could NOT TAKE --
        # the BUG-257/262/263 class. It is Not Applicable: excluded from accuracy and never
        # scored as 0, because a 0 here silently becomes a "finding" about the model.
        if r.get("na"):
            na[r["model"]] = na.get(r["model"], 0) + 1
            continue
        if r.get("err"):
            errs[r["model"]] += 1
            continue
        if r.get("id") in INVALID_ITEM_IDS:
            invalid += 1
            continue
        k = (r["model"], r["suite"])
        acc[k].append(1 if r.get("ok") else 0)
        if r.get("secs"):
            lat[k].append(float(r["secs"]))

    all_models = sorted({r["model"] for r in rows})
    models = [m for m in all_models if m not in PRUNED_MODELS]
    pruned = [m for m in all_models if m in PRUNED_MODELS]
    suites = [s for s in SUITE_ORDER if any(k[1] == s for k in acc)]
    lines: list[str] = []
    lines.append("MODEL EVALUATION — oMLX, temperature 0.0, identical system prompts")
    if invalid:
        lines.append("  (" + str(invalid) + " checkpoint rows excluded as INVALID ITEMS — "
                     "bad gold, see INVALID_ITEM_IDS / BUG-253)")
    if na:
        lines.append("  (" + str(sum(na.values())) + " cell(s) NA — harness-invalid, excluded "
                     "from accuracy, never scored as 0; see tools/bench_preflight.py)")
    lines.append("")

    hdr = "model".ljust(36) + "".join(s[:9].rjust(10) for s in suites)
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for m in models:
        cells = ""
        for s in suites:
            v = acc.get((m, s))
            cells += ("--" if not v else str(round(sum(v) / len(v), 2))).rjust(10)
        lines.append(m[:35].ljust(36) + cells)

    lines.append("")
    lines.append("Per-suite detail (n, median latency s, transport errors)")
    lines.append("-" * 78)
    for m in models:
        for s in suites:
            v = acc.get((m, s))
            if not v:
                continue
            med = round(statistics.median(lat[(m, s)]), 1) if lat.get((m, s)) else 0.0
            lines.append("  " + m[:34].ljust(34) + " " + s.ljust(13) + " acc="
                         + str(round(sum(v) / len(v), 3)).ljust(6) + " n=" + str(len(v)).ljust(4)
                         + " med=" + str(med).ljust(7) + "s")

    # Long-context breakdown. err rows are excluded for the same reason as the main
    # table: a 400 at 32000 tokens is a context-ceiling observation (BUG-257: the top
    # tier sits above oMLX's 32768 window once the chat template is added, so it 400s
    # for some templates and grades fine for others), never a model miss. Counting it
    # as 0 is how a dead tier becomes a phantom "long-context failure".
    # Split BY SUITE: niah (needle retrieval) and lc_reasoning (multi-hop reasoning at
    # length) are different tasks that happen to share a token size. Pooling them
    # averages a 3/3 with a 0/5 and reports a meaningless 0.38.
    for suite in ("niah", "lc_reasoning"):
        lc = [r for r in rows if r.get("suite") == suite
              and r.get("ctx_tokens") and not r.get("err")]
        if not lc:
            continue
        lines.append("")
        lines.append("Long-context — " + suite + " (by prompt size; n in brackets; errors excluded)")
        lines.append("-" * 78)
        by: dict[tuple[str, int], list[int]] = defaultdict(list)
        for r in lc:
            by[(r["model"], int(r["ctx_tokens"]))].append(1 if r.get("ok") else 0)
        sizes = sorted({int(r["ctx_tokens"]) for r in lc})
        head = "model".ljust(34) + "".join((str(s) + "tok").rjust(14) for s in sizes)
        lines.append(head)
        lines.append("-" * len(head))
        for m in models:
            cells = ""
            for s in sizes:
                v = by.get((m, s))
                cells += ("--".rjust(14) if not v
                          else (str(round(sum(v) / len(v), 2)) + " (" + str(len(v)) + ")").rjust(14))
            if cells.strip("- "):
                lines.append(m[:33].ljust(34) + cells)

    # Stability: how often a model repeated the same answer across 3 reps
    stab = [r for r in rows if r.get("stab_key") and r.get("pred")]
    if stab:
        lines.append("")
        lines.append("Stability — self-agreement across 3 identical repeats")
        lines.append("-" * 78)
        for m in models:
            groups: dict[str, list[str]] = defaultdict(list)
            for r in stab:
                if r["model"] == m:
                    groups[r["stab_key"]].append(str(r["pred"])[:60].lower())
            if not groups:
                continue
            agree = sum(1 for v in groups.values() if len(set(v)) == 1)
            lines.append("  " + m[:34].ljust(34) + " unanimous " + str(agree) + "/" + str(len(groups)))

    # Pruned models: historical rows only. Never quote these as candidates.
    if pruned:
        lines.append("")
        lines.append("PRUNED — historical rows only, NOT in the portfolio (do not quote as a candidate)")
        lines.append("-" * 78)
        for m in pruned:
            covered = [s for s in suites if acc.get((m, s))]
            n = sum(len(acc[(m, s)]) for s in covered)
            lines.append("  " + m[:34].ljust(34) + " rows=" + str(n).ljust(5)
                         + " transport_err=" + str(errs.get(m, 0)).ljust(4)
                         + " suites=" + ",".join(covered))

    text = chr(10).join(lines)
    print(text)
    if args.md:
        Path(args.md).write_text("# " + text + chr(10), encoding="utf-8")
        print(chr(10) + "wrote " + args.md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
