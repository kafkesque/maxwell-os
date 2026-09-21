#!/usr/bin/env python3
"""Fetch and FREEZE standard public benchmark subsets to local JSONL.

Why freeze: the eval run must not drift if a dataset is updated mid-run, and it
must not need the network while oMLX is holding the single resident model. One
fetch -> immutable JSONL under governance/evalsets/ -> harness reads only those.

Standards pulled (small, deterministic-gradable subsets):
  gsm8k          grade-school math reasoning        (numeric exact match)
  mmlu_pro       broad knowledge + reasoning        (multiple choice)
  math500        hard competition math              (numeric exact match)
  humaneval      code generation, light             (unit tests)
  mbpp           code generation, light             (unit tests)
  ifeval         instruction following              (rule-based verifiers)
  hotpot_qa      multi-hop research/synthesis       (answer exact match)

Usage:
  python3 tools/fetch_evalsets.py --n 25
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "governance" / "evalsets"
SEED = 20260915


def _write(name: str, rows: list[dict]) -> None:
    """Write rows to governance/evalsets/<name>.jsonl atomically-ish."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / (name + ".jsonl")
    p.write_text("".join(json.dumps(r) + chr(10) for r in rows), encoding="utf-8")
    print("  wrote " + str(len(rows)) + " rows -> " + p.name)


def fetch_gsm8k(n: int) -> list[dict]:
    """GSM8K test split -> {id, question, answer_final}."""
    from datasets import load_dataset
    ds = load_dataset("openai/gsm8k", "main", split="test")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    out = []
    for i in idx:
        r = ds[i]
        gold = r["answer"].split("####")[-1].strip().replace(",", "")
        out.append({"id": "gsm8k-" + str(i), "question": r["question"], "answer": gold})
    return out


def fetch_math500(n: int) -> list[dict]:
    """MATH-500 -> {id, problem, answer}."""
    from datasets import load_dataset
    ds = load_dataset("HuggingFaceH4/MATH-500", split="test")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    return [{"id": "math500-" + str(i), "problem": ds[i]["problem"], "answer": ds[i]["answer"]} for i in idx]


def fetch_mmlu_pro(n: int) -> list[dict]:
    """MMLU-Pro test split -> {id, question, options, answer_letter}."""
    from datasets import load_dataset
    ds = load_dataset("TIGER-Lab/MMLU-Pro", split="test")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    out = []
    for i in idx:
        r = ds[i]
        out.append({
            "id": "mmlupro-" + str(i),
            "question": r["question"],
            "options": list(r["options"]),
            "answer": str(r["answer"]).strip().upper(),
            "category": r.get("category", ""),
        })
    return out


def fetch_humaneval(n: int) -> list[dict]:
    """OpenAI HumanEval -> {id, prompt, test, entry_point}."""
    from datasets import load_dataset
    ds = load_dataset("openai/openai_humaneval", split="test")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    return [{
        "id": ds[i]["task_id"], "prompt": ds[i]["prompt"],
        "test": ds[i]["test"], "entry_point": ds[i]["entry_point"],
    } for i in idx]


def fetch_mbpp(n: int) -> list[dict]:
    """MBPP sanitized -> {id, prompt, test_list}."""
    from datasets import load_dataset
    ds = load_dataset("google-research-datasets/mbpp", "sanitized", split="test")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    return [{
        "id": "mbpp-" + str(i), "prompt": ds[i]["prompt"],
        "test_list": list(ds[i]["test_list"]),
    } for i in idx]


def fetch_ifeval(n: int) -> list[dict]:
    """IFEval -> {id, prompt, instruction_ids} (graded by the official verifiers)."""
    from datasets import load_dataset
    ds = load_dataset("google/IFEval", split="train")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    return [{
        "id": "ifeval-" + str(i), "prompt": ds[i]["prompt"],
        "instruction_ids": list(ds[i]["instruction_id_list"]),
        "kwargs": [k for k in ds[i]["kwargs"]],
    } for i in idx]


def fetch_hotpot(n: int) -> list[dict]:
    """HotpotQA distractor validation -> {id, question, context, answer} (multi-hop)."""
    from datasets import load_dataset
    ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split="validation")
    rng = random.Random(SEED)
    idx = rng.sample(range(len(ds)), min(n, len(ds)))
    out = []
    for i in idx:
        r = ds[i]
        ctx = []
        for title, sents in zip(r["context"]["title"], r["context"]["sentences"]):
            ctx.append(title + ": " + " ".join(sents))
        out.append({
            "id": "hotpot-" + str(i), "question": r["question"],
            "context": chr(10).join(ctx)[:12000], "answer": r["answer"],
        })
    return out


FETCHERS = {
    "gsm8k": fetch_gsm8k,
    "math500": fetch_math500,
    "mmlu_pro": fetch_mmlu_pro,
    "humaneval": fetch_humaneval,
    "mbpp": fetch_mbpp,
    "ifeval": fetch_ifeval,
    "hotpot_qa": fetch_hotpot,
}


def main() -> int:
    """Fetch every configured standard benchmark subset and freeze it to JSONL."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="items per benchmark")
    ap.add_argument("--only", nargs="*", default=None, help="subset of suite names")
    args = ap.parse_args()

    names = args.only or list(FETCHERS)
    failures = []
    for name in names:
        fn = FETCHERS.get(name)
        if fn is None:
            print("unknown suite: " + name)
            continue
        print("== " + name)
        try:
            rows = fn(args.n)
            _write(name, rows)
        except Exception as exc:
            print("  FAILED " + type(exc).__name__ + ": " + str(exc)[:200])
            failures.append(name)

    print(chr(10) + "done. failures: " + (", ".join(failures) if failures else "none"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
