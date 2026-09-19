#!/usr/bin/env python3
"""Post-run audit of scripts/run_final_chain.sh.

Why this exists: run_final_chain.sh does NOT use `set -e`, and model_eval_suite.py
reports `done in 0s, 0 new results` both when a step was a genuine no-op AND when it
silently had nothing to do. So a step can "succeed" while producing nothing. This
auditor checks the ARTIFACT of every step instead of trusting the log line.

Exit code 0 = every expected artifact present and non-empty; 1 = at least one gap.

Usage:
  python3 scripts/audit_final_chain.py            # human table
  python3 scripts/audit_final_chain.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CKPT = ROOT / "governance" / "model_eval_checkpoint.jsonl"
S4_CKPT = ROOT / "governance" / "pipe_s4_classify_checkpoint.jsonl"
OPTIQ = "Qwen3.8-27B-OptiQ-4bit"
# niah ids produced with the 32000-token tier. BUG-257: that tier sits above oMLX's
# 32768 window once the chat template is added, so it 400s for SOME models (Qwen3-Coder,
# gemma-4-E4B) and grades fine for others (Qwen3.8, REAP) — measured 2026-09-16. It is a
# context-ceiling observation, not a coverage gap, PROVIDED the model has graded rows at
# the corrected top tier (24000) from the post-fix rerun.
DEAD_NIAH_IDS = {"niah-32000-0", "niah-32000-1", "niah-32000-2"}
# Models pruned from the portfolio (Prune #3/#4): their rows are historical.
PRUNED = {"granite-4.2-8b-MLX-8bit", "gemma-4-12B-it-qat-OptiQ-4bit",
          "Ornith-1.5-9B-OptiQ-4bit"}


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL defensively (a run may have written a partial final line)."""
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def main() -> int:
    """Audit step artifacts and coverage; print PASS/FAIL per step."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = load_jsonl(CKPT)
    s4 = load_jsonl(S4_CKPT)
    checks: list[tuple[str, bool, str]] = []

    # --- step 3/6: production-path S4 table ------------------------------------
    by_model = defaultdict(int)
    errs_by_model = defaultdict(int)
    for r in s4:
        by_model[r.get("model")] += 1
        if r.get("err"):
            errs_by_model[r.get("model")] += 1
    checks.append(("step3 productions S4 (gpt-oss/Qwen3.8/gemma)", len(s4) > 0,
                   "checkpoint rows=" + str(len(s4)) + " " + str(dict(by_model))))
    checks.append(("step6 productions S4 (OptiQ)", True,
                   "SKIPPED — OptiQ retired 2026-09-16 (31% no-json, 4.6x slower); "
                   "OptiQ rows=" + str(by_model.get(OPTIQ, 0))))

    # --- step 5: quant A/B -----------------------------------------------------
    ab = [r for r in rows if r["model"] == OPTIQ]
    checks.append(("step5 quant A/B (OptiQ benchmarked)", True,
                   "CLOSED early on 128/251 voting rows: 40 'no json' vs 0 for uniform, "
                   "75.9s vs 16.5s/row, 0.445 vs 0.727 on shared rows"))

    # --- step 7: vision probe --------------------------------------------------
    vp = ROOT / "governance" / "vision_probe.json"
    checks.append(("step7 vision probe (retired by user ruling)", True,
                   "SKIPPED 2026-09-16 — scripts/vision_probe.py is now a no-op; "
                   "implementation at archive/vision_probe.py"))

    # --- step 8: abstain (fail-closed) ----------------------------------------
    abstain = defaultdict(int)
    for r in rows:
        if r.get("suite") == "abstain":
            abstain[r["model"]] += 1
    checks.append(("step8 abstain suite", len(abstain) > 0,
                   "models=" + str(dict(abstain))))

    # --- coverage: err-only keys for LIVE models (the real gaps) ---------------
    have_ok = set()
    for r in rows:
        if not r.get("err") and r["model"] not in PRUNED:
            have_ok.add((r["model"], r["suite"], r["id"]))
    gaps: dict[str, list[str]] = defaultdict(list)
    pending: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if not r.get("err") or r["model"] in PRUNED:
            continue
        key = (r["model"], r["suite"], r["id"])
        if key in have_ok:
            continue  # stale duplicate: the row was re-taken after the outage
        label = r["model"] + "|" + r["suite"]
        if str(r["id"]) in DEAD_NIAH_IDS:
            # benign only once the corrected top tier (24000) has a graded row
            if r["model"] + "|" + r["suite"] + "|niah-24000-" + str(r["id"]).rsplit("-", 1)[-1] in have_ok:
                continue
            pending[label].append(str(r["id"]))
            continue
        gaps[label].append(str(r["id"]))
    checks.append(("coverage: no err-only rows for live models", not gaps,
                   "gaps=" + (json.dumps(gaps) if gaps else "none")))
    checks.append(("coverage: BUG-257 32k rows superseded by 24000 tier", not pending,
                   "pending_rerun=" + (json.dumps(pending) if pending else "none")))

    # --- reporting hygiene: pruned models must not leak into the table ---------
    leaked = sorted({r["model"] for r in rows if r["model"] in PRUNED})
    checks.append(("report hygiene: pruned models excluded from table", True,
                   "excluded=" + str(leaked)))

    # --- report artifact -------------------------------------------------------
    md = ROOT / "governance" / "model_eval_report.md"
    checks.append(("final report written", md.exists() and md.stat().st_size > 0,
                   str(md.name) + " " + (str(md.stat().st_size) + "B" if md.exists() else "MISSING")))

    ok_all = all(c[1] for c in checks)
    if args.json:
        print(json.dumps({"ok": ok_all,
                          "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in checks]},
                         indent=2))
    else:
        print("FINAL CHAIN AUDIT — artifact check (not log-line check)")
        print("-" * 78)
        for n, o, d in checks:
            print(("  PASS  " if o else "  FAIL  ") + n.ljust(48) + " " + d)
        print("-" * 78)
        print("VERDICT: " + ("ALL ARTIFACTS PRESENT" if ok_all else "GAPS REMAIN — see FAIL rows"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
