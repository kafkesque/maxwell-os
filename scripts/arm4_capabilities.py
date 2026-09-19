#!/usr/bin/env python3
"""ARM-4b — role-based capability benchmark (coding / reasoning / orchestrating / reviewing / analysing).

Two deterministic checkable tasks per capability, run against the models that hold
current roles (Phi-4-mini, gemma-4-E4B, gpt-oss-20b-Q8) plus the ARM-4 candidates
(Ornith-1.5-9B, gemma-4-12B, Ornith-35B-REAP) and the llmfit pick (DeepSeek-R1-8B).

Read-only, deterministic (temp 0 via greedy decode). Reasoning models get
enable_thinking=False (else the trace eats the budget — see D2635 follow-up).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import optiq  # noqa: F401
from mlx_lm import load  # noqa: E402

from arm4_benchmark import gen_chat, parse_json  # noqa: E402


def _has(pat):
    return lambda o: bool(re.search(pat, o, re.I))


def _json_ok(fn):
    def check(o):
        p = parse_json(o)
        try:
            return bool(fn(p))
        except Exception:
            return False
    return check


TASKS = [
    # ---- CODING ----
    ("coding", "c_fib", "You write Python code only.",
     "Write a Python function `fib(n)` returning the nth Fibonacci number (fib(0)=0, fib(1)=1). Output ONLY the code, no explanation.",
     _has(r"def\s+fib") ),
    ("coding", "c_fix", "You write Python code only.",
     "This function is buggy: `def add(a, b): return a - b`. It should return the sum. Output ONLY the corrected one-line function.",
     _has(r"a\s*\+\s*b")),
    # ---- REASONING ----
    ("reasoning", "r_syllogism", "Answer precisely.",
     "If all bloops are razzies, and all razzies are lazzies, are all bloops lazzies? Answer with only YES or NO.",
     _has(r"\byes\b")),
    ("reasoning", "r_batball", "Answer precisely.",
     "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost? Answer with only the dollar amount.",
     _has(r"0?\.05|5\s*cents|\$\s*0?\.05")),
    # ---- ORCHESTRATING ----
    ("orchestrating", "o_plan", "Return only JSON.",
     'Return a JSON object with 3 ordered steps to build a REST API: {"steps": ["...", "...", "..."]}',
     _json_ok(lambda p: isinstance(p, dict) and len(p.get("steps", [])) == 3)),
    ("orchestrating", "o_tools", "Return only JSON.",
     'Available tools: search, read_file, write_file. Return JSON of tool calls to find and then update a config file: {"calls": [{"tool": "<name>"}, ...]}',
     _json_ok(lambda p: isinstance(p, dict) and bool(p.get("calls")) and all(
         isinstance(c, dict) and c.get("tool") in ("search", "read_file", "write_file")
         for c in p.get("calls", [])))),
    # ---- REVIEWING ----
    ("reviewing", "v_bug", "You are a senior code reviewer. Be concise.",
     "Find the bug: `def avg(xs): return sum(xs)/len(xs)` when called with an empty list. Answer in one sentence.",
     _has(r"empty|zero|len\(xs\)|division|ZeroDivision")),
    ("reviewing", "v_claim", "Answer precisely.",
     "Claim: 'The function always returns a positive number.' Function: `def f(x): return x * 2`. Is the claim SUPPORTED or CONTRADICTED? Answer with only one word.",
     _has(r"contradict")),
    # ---- ANALYSING ----
    ("analysing", "a_summary", "Summarize concisely.",
     "Summarize in at most 20 words: 'Cluster analysis groups similar text segments so that shared principles can be extracted once, reducing duplication and improving the quality of the resulting knowledge base.' Answer with only the summary.",
     lambda o: 0 < len(o.split()) <= 20),
    ("analysing", "a_extract", "Return only JSON.",
     'Extract as JSON: \'The meeting is on Tuesday at 3pm in Room 5.\' Format: {"day": "<day>", "time": "<time>", "room": "<room>"}',
     _json_ok(lambda p: isinstance(p, dict) and "tues" in str(p.get("day", "")).lower()
              and "3" in str(p.get("time", "")) and "5" in str(p.get("room", "")))),
]

MODELS = [
    # candidates
    "mlx-community/gemma-4-12B-it-qat-OptiQ-4bit",
    "mlx-community/Ornith-1.5-9B-OptiQ-4bit",
    "mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B",
    # current assignments
    "mlx-community/gpt-oss-20b-MXFP4-Q8",              # S4 classifier (teacher)
    "lmstudio-community/gemma-4-E4B-it-MLX-4bit",      # REVIEWER / RESIDENT_BRAIN
    "mlx-community/Phi-4-mini-instruct-8bit",          # ORCHESTRATOR / CODING_DRAFT / gates
    "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit",  # GENERATOR / CODING_CLEAN / PLANNER
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--out", default=str(ROOT / "governance" / "arm4_capabilities.json"))
    args = ap.parse_args()

    results: dict[str, dict] = {}
    for m in args.models:
        print(f"\n{'='*66}\nMODEL: {m}\n{'='*66}", flush=True)
        try:
            model, tok = load(m)
        except Exception as e:
            print(f"  LOAD FAILED: {e}", flush=True)
            results[m] = {"load_error": str(e)[:160]}
            continue
        per_cap: dict[str, list] = {}
        for cap, tid, system, user, check in TASKS:
            try:
                out = gen_chat(model, tok, system, user, 512)
                ok = check(out)
            except Exception as e:
                out, ok = f"ERR {e}", False
            per_cap.setdefault(cap, []).append(1 if ok else 0)
            print(f"  [{'PASS' if ok else 'FAIL'}] {cap:14s} {tid:12s} {repr(out[:70])}", flush=True)
        results[m] = {cap: round(sum(v) / len(v), 3) for cap, v in per_cap.items()}
        results[m]["_overall"] = round(
            sum(sum(v) for v in per_cap.values()) / sum(len(v) for v in per_cap.values()), 3)
        del model, tok

    Path(args.out).write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
