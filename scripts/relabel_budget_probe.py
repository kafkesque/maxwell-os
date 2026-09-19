#!/usr/bin/env python3
"""Budget probe for the S2 FORM judge (BUG-263 evidence).

WHY: the defect was a token budget (max_tokens=64) that a Harmony reasoning model cannot answer
inside, and the failure was invisible because call_omlx_json() returns [] instead of raising.
This probe shows, on the SAME prompt and the SAME records, what the judge actually emits at each
budget: raw content characters, JSON parseability, label, latency. It is the artifact that makes
'budget 1024 works' a measurement instead of an assertion.

Read-only: it never writes a checkpoint. All numbers are raw model output, not labels applied.

    python3 scripts/relabel_budget_probe.py --limit 5 --model gpt-oss-20b-MXFP4-Q8
    python3 scripts/relabel_budget_probe.py --limit 5 --budgets 64,256,1024,2048 --prefix auto
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.omlx_call import call_omlx, parse_json_robust  # noqa: E402
from pipeline.pipeline_paths import (  # noqa: E402
    RELABEL_JUDGE_MAX_TOKENS,
    STAGE2_CHECKPOINT,
    VERIFY_REASONING_OFF_MODELS,
    VERIFY_REASONING_OFF_PREFIX,
)
from pipeline.stage2_relabel_extraction_type import (  # noqa: E402
    SYSTEM_PROMPT,
    _build_prompt,
    _extract_label,
)

REPORT_DIR: Path = REPO / "governance"
JOIN: str = chr(10)


def _system_for(model: str, prefix_mode: str) -> tuple[str, bool]:
    """Return (system prompt, prefix_applied) for the requested prefix mode."""
    applies = model in VERIFY_REASONING_OFF_MODELS and bool(VERIFY_REASONING_OFF_PREFIX)
    if prefix_mode == "on":
        applies = True
    elif prefix_mode == "off":
        applies = False
    return (VERIFY_REASONING_OFF_PREFIX + JOIN + JOIN + SYSTEM_PROMPT if applies else SYSTEM_PROMPT), applies


def probe(records: list[dict[str, Any]], model: str, budget: int, prefix_mode: str) -> list[dict[str, Any]]:
    """Call the real judge prompt at one budget and record what came back."""
    system, applied = _system_for(model, prefix_mode)
    out: list[dict[str, Any]] = []
    for rec in records:
        t0 = time.time()
        row: dict[str, Any] = {"budget": budget, "prefix": applied, "model": model,
                              "name": str(rec.get("name", "?"))[:44],
                              "stored_label": rec.get("extraction_type")}
        try:
            # Same backend call the production path makes; response_format is skipped for
            # reasoning-off models (D2408) which is exactly what call_omlx_json does.
            raw = call_omlx(prompt=_build_prompt(rec), model=model, system=system,
                            max_tokens=budget, response_format=None)
            parsed = parse_json_robust(raw)
            row["raw_chars"] = len(raw or "")
            row["label"] = _extract_label(parsed)
            row["json_ok"] = bool(_extract_label(parsed))
            row["error"] = None
        except Exception as exc:
            row["raw_chars"] = 0
            row["label"] = ""
            row["json_ok"] = False
            row["error"] = type(exc).__name__ + ": " + str(exc)[:160]
        row["secs"] = round(time.time() - t0, 2)
        out.append(row)
        print("  budget=" + str(budget).ljust(5) + " prefix=" + str(applied).ljust(6)
              + " raw=" + str(row["raw_chars"]).ljust(6) + " json=" + str(row["json_ok"]).ljust(6)
              + " " + str(row["secs"]).ljust(7) + " " + str(row["label"] or row["error"])[:56],
              flush=True)
    return out


def write_report(payload: dict[str, Any]) -> Path:
    """Persist the probe artifact atomically (M2: evidence is a file, not a log line)."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / ("relabel_budget_probe_" + time.strftime("%Y%m%d_%H%M%S") + ".json")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


def main() -> int:
    """Probe each budget and summarise. Returns the exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=5, help="records to probe per budget")
    ap.add_argument("--model", default="gpt-oss-20b-MXFP4-Q8")
    ap.add_argument("--budgets", default="64," + str(RELABEL_JUDGE_MAX_TOKENS),
                    help="comma list; default = the old hardcoded value and the configured one")
    ap.add_argument("--prefix", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--checkpoint", default=str(STAGE2_CHECKPOINT))
    args = ap.parse_args()

    records = [json.loads(l) for l in Path(args.checkpoint).read_text(encoding="utf-8").splitlines() if l.strip()]
    single = [r for r in records if not r.get("is_convergent")][:args.limit]
    budgets = [int(b) for b in args.budgets.split(",") if b.strip()]
    print("=" * 92)
    print("RELABEL BUDGET PROBE   model=" + args.model + "   records=" + str(len(single)))
    print("  configured budget: " + str(RELABEL_JUDGE_MAX_TOKENS))
    print("=" * 92)

    rows: list[dict[str, Any]] = []
    for budget in budgets:
        rows += probe(single, args.model, budget, args.prefix)

    summary: list[dict[str, Any]] = []
    print("\n  budget   json_ok   median_raw_chars   median_s")
    for budget in budgets:
        sub = [r for r in rows if r["budget"] == budget]
        ok = sum(1 for r in sub if r["json_ok"])
        med_raw = round(statistics.median([r["raw_chars"] for r in sub]), 1) if sub else 0
        med_s = round(statistics.median([r["secs"] for r in sub]), 1) if sub else 0
        summary.append({"budget": budget, "json_ok": ok, "n": len(sub),
                        "median_raw_chars": med_raw, "median_secs": med_s})
        print("  " + str(budget).ljust(8) + str(ok) + "/" + str(len(sub)).ljust(5)
              + "  " + str(med_raw).ljust(18) + "  " + str(med_s))

    payload = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": args.model,
               "prefix_mode": args.prefix, "configured_budget": RELABEL_JUDGE_MAX_TOKENS,
               "n_records": len(single), "summary": summary, "rows": rows}
    path = write_report(payload)
    print("\n  artifact: " + str(path.relative_to(REPO)))
    worst = [s for s in summary if s["budget"] < RELABEL_JUDGE_MAX_TOKENS and s["json_ok"] == 0]
    if worst:
        print("  confirmed: budget " + ",".join(str(s["budget"]) for s in worst)
              + " yields NO usable label (BUG-263); configured budget does.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
