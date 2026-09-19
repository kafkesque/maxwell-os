#!/usr/bin/env python3
"""Settle "harness artifact or capability limit?" for any (model, suite) cell.

WHY: the BUG-253 class - a score that looks identical across models of wildly different ability
is a harness signal, not a model result. Before writing a model off for a suite, vary the ONE
harness knob that plausibly explains it (output budget) and the ONE environmental factor (a cold
model reload returning empty), and record what actually comes back. This is the check that must
precede any statement of the form 'model X cannot do suite Y'.

    python3 scripts/suite_budget_probe.py --suite toolcalling --model gpt-oss-20b-MXFP4-Q8 --budgets 200,512,1024,2048
    python3 scripts/suite_budget_probe.py --suite toolcalling --model gemma-4-E4B-it-MLX-4bit --budgets 200 --attempts 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from model_eval_suite import SUITES, call  # noqa: E402

REPORT_DIR: Path = REPO / "governance"


def _json_ok(text: str) -> bool:
    """True when the brace-delimited part of the response parses as JSON."""
    head, tail = text.find("{"), text.rfind("}")
    if head < 0 or tail <= head:
        return False
    try:
        json.loads(text[head:tail + 1])
        return True
    except Exception:
        return False


def probe(suite: str, model: str, budget: int, attempts: int) -> dict[str, Any]:
    """Try one cell at one budget, up to `attempts` times, and report what came back."""
    items = SUITES[suite]()
    item = items[0]
    grader = item.get("grader")
    out: dict[str, Any] = {"suite": suite, "model": model, "budget": budget,
                          "item_id": item.get("id"), "attempts": []}
    for attempt in range(attempts):
        t0 = time.time()
        row: dict[str, Any] = {"attempt": attempt + 1}
        try:
            content = call(model, item["system"], item["user"], budget) or ""
            row["chars"] = len(content)
            row["json_ok"] = _json_ok(content)
            row["head"] = content.strip().replace(chr(10), " ")[:70]
            try:
                verdict = grader(content) if callable(grader) else None
                row["grader"] = str(verdict)
            except Exception as exc:
                row["grader"] = "raised " + type(exc).__name__
        except Exception as exc:
            row["chars"] = 0
            row["json_ok"] = False
            row["head"] = ""
            row["grader"] = "CALL FAILED " + type(exc).__name__ + ": " + str(exc)[:90]
        row["secs"] = round(time.time() - t0, 2)
        out["attempts"].append(row)
        print("  budget=" + str(budget).ljust(6) + "try=" + str(attempt + 1).ljust(3)
              + "chars=" + str(row["chars"]).ljust(7) + "json=" + str(row["json_ok"]).ljust(7)
              + str(row["secs"]).ljust(8) + str(row["head"])[:60], flush=True)
    return out


def main() -> int:
    """Run the probe matrix and write the artifact. Returns the exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--budgets", default="200,512,1024")
    ap.add_argument("--attempts", type=int, default=1)
    args = ap.parse_args()

    if args.suite not in SUITES:
        print("unknown suite: " + args.suite)
        return 2
    budgets = [int(b) for b in args.budgets.split(",") if b.strip()]
    print("=" * 92)
    print("SUITE BUDGET PROBE   suite=" + args.suite + "  model=" + args.model)
    print("=" * 92)
    results = [probe(args.suite, args.model, b, args.attempts) for b in budgets]

    print("")
    best = [r for r in results if any(a["json_ok"] for a in r["attempts"])]
    if best:
        print("  VERDICT: budget-dependent, NOT a capability limit. Smallest working budget = "
              + str(min(r["budget"] for r in best)))
    else:
        print("  VERDICT: no budget in the probe produced a gradable answer")
    payload = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "suite": args.suite,
               "model": args.model, "budgets": budgets, "results": results,
               "budget_dependent": bool(best)}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / ("suite_budget_probe_" + args.suite + "_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    print("  artifact: " + str(path.relative_to(REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
