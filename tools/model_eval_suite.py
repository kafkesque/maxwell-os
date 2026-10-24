#!/usr/bin/env python3
"""Model evaluation suite — standard benchmarks + capability suites, all via oMLX.

Two layers, one harness, one table:

  STANDARD (frozen in governance/evalsets/*.jsonl, fetched by tools/fetch_evalsets.py)
    gsm8k        grade-school math reasoning        numeric exact match
    math500      hard competition math              numeric exact match
    mmlu_pro     broad knowledge + reasoning        multiple choice
    humaneval    code generation, light             unit tests
    mbpp         code generation, light             unit tests
    ifeval       instruction following              rule-based verifiers
    hotpot_qa    multi-hop research/synthesis       answer containment

  CAPABILITY (generated deterministically in-process, seed-fixed)
    niah          long-context retrieval @ 4k/16k/32k   needle exact match
    lc_reasoning  reasoning with facts buried at 16k    numeric exact match
    toolcalling   multi-turn tool use w/ JSON schemas   tool + arg match
    planning      strategic constraint planning        numeric exact match
    hardcode      algorithmic coding w/ hidden tests    unit tests
    reviewing     seeded-bug + false-claim detection    keyword match
    stability     same 10 items x3                      self-agreement

Every call goes through oMLX HTTP at temperature 0.0 with a per-suite system
prompt that is byte-identical across models (fairness). Results append to a
checkpoint JSONL so the run is resumable after any crash.

Usage:
  python3 tools/model_eval_suite.py --models M1 M2 --suites gsm8k mbpp
  python3 tools/model_eval_suite.py --models-file governance/eval_models.txt
"""
from __future__ import annotations

import argparse
import ast
import json
import random
import sqlite3
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import requests

ROOT = Path(__file__).resolve().parent.parent
EVALSETS = ROOT / "governance" / "evalsets"
CKPT = ROOT / "governance" / "model_eval_checkpoint.jsonl"

URL = "http://127.0.0.1:11435/v1/chat/completions"
KEY = "sk-maxwell-local"
SEED = 20260915
CODE_TIMEOUT_S = 12

NO_COT = "Be precise and concise. Do not narrate your reasoning."
COT = "Think step by step, then give the final answer clearly marked."


def call(model: str, system: str, user: str, max_tokens: int = 512, timeout: int = 900) -> str:
    """POST one chat completion to oMLX and return the assistant text (stripped).

    BUG-262 (2026-09-17): the production path suppresses reasoning for gpt-oss via
    VERIFY_REASONING_OFF_PREFIX ('Reasoning: low'). This harness did not, so on the n=20
    tool-calling run gpt-oss spent its 200-token budget on Harmony reasoning and produced
    ZERO parseable JSON in 20/20 rows — a format artifact scored as a model failure, the same
    class as the OptiQ 'no json' rows. The prefix is now applied here so the eval prompt matches
    the production prompt for the models the config declares reasoning-off.
    """
    try:
        from pipeline.pipeline_paths import (  # config-driven, never hardcoded
            VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX,
        )
        if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
            system = VERIFY_REASONING_OFF_PREFIX + chr(10) + chr(10) + system
    except Exception:  # noqa: BLE001 — harness must run even if config is unavailable
        pass
    r = requests.post(
        URL,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    # BUG-265: content alone is not enough — a native tool call carries content="" .
    return _normalise_message(msg)


def _normalise_message(msg: dict) -> str:
    """Return gradable text from an assistant message, INCLUDING native tool calls (BUG-265).

    WHY: this harness read only message['content']. A model that answers with native tool calling
    puts the answer in message['tool_calls'] and leaves content EMPTY, so the harness recorded a
    failure. Measured: gemma-4-E4B returned finish_reason='tool_calls', content='', and one
    well-formed call — search_files {query: log, path: /var/log} — for a request it was then
    scored 0.55 on. The tool call is rendered into the same {"tool":..., "args":{...}} form the
    suite grader already expects, so every model is graded on one rule. Only the first call is
    rendered: every toolcalling item expects exactly one tool.

    Order matters: content, then tool_calls, then reasoning_content. The reasoning fallback is
    LAST because a reasoning model that never reaches its answer (finish_reason='length') returns
    its thinking, which is not an answer.

    Args:
        msg: the assistant message object from the chat completion response.

    Returns:
        Gradable text, or '' when the model produced no answer.
    """
    text = (msg.get("content") or "").strip()
    if text:
        return text
    calls = msg.get("tool_calls") or []
    if calls:
        call0 = calls[0] or {}
        fn = call0.get("function") or {}
        name = fn.get("name") or call0.get("name") or ""
        raw_args: Any = fn.get("arguments")
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except Exception:
                raw_args = {}
        return json.dumps({"tool": name, "args": raw_args if isinstance(raw_args, dict) else {}},
                          ensure_ascii=False)
    return (msg.get("reasoning_content") or "").strip()


NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def _last_number(text: str) -> str | None:
    """Return the last number appearing in text, normalised (commas stripped)."""
    hits = NUM_RE.findall(text)
    if not hits:
        return None
    return hits[-1].replace(",", "").rstrip(".")


def grade_numeric(pred: str, gold: str) -> tuple[bool, str]:
    """Grade by comparing the last number in pred against gold."""
    p = _last_number(pred)
    g = _last_number(gold) or gold
    if p is None:
        return False, "no number in output"
    try:
        ok = abs(float(p) - float(g)) < 1e-6
    except ValueError:
        ok = p == g
    return ok, "pred=" + str(p) + " gold=" + str(g)


def grade_letter(pred: str, gold: str) -> tuple[bool, str]:
    """Grade a multiple-choice answer by extracting the leading option letter."""
    m = re.search(r"\b([A-J])\b", pred.upper())
    got = m.group(1) if m else "?"
    return got == gold.upper(), "pred=" + got + " gold=" + gold.upper()


def grade_contains(pred: str, gold: str) -> tuple[bool, str]:
    """Grade by case-insensitive containment of gold in pred."""
    ok = gold.strip().lower() in pred.strip().lower()
    return ok, "gold=" + gold[:40]


def run_code_tests(source: str, tests: list[str]) -> tuple[bool, str]:
    """Execute generated code against tests in a sandboxed subprocess."""
    body = source + chr(10) + chr(10) + chr(10).join(tests) + chr(10) + "print('__OK__')" + chr(10)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(body)
        path = f.name
    try:
        p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=CODE_TIMEOUT_S)
        if "__OK__" in p.stdout and p.returncode == 0:
            return True, "pass"
        err = (p.stderr or p.stdout).strip().splitlines()
        return False, (err[-1][:120] if err else "fail")
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as exc:
        return False, type(exc).__name__
    finally:
        Path(path).unlink(missing_ok=True)


def extract_code(text: str) -> str:
    """Pull the first fenced code block out of a model response."""
    m = re.search(r"(?:```|~~~)(?:python)?\s*(.*?)(?:```|~~~)", text, re.S)
    return (m.group(1) if m else text).strip()


def grade_code(pred: str, tests: list[str]) -> tuple[bool, str]:
    """Extract code from pred and run the tests."""
    src = extract_code(pred)
    if not src:
        return False, "no code"
    return run_code_tests(src, tests)


def grade_ifeval(pred: str, instruction_ids: list[str], kwargs: list[Any]) -> tuple[bool, str]:
    """Grade instruction-following with rule-based checks (IFEval-style)."""
    fails: list[str] = []
    for iid, kw in zip(instruction_ids, kwargs):
        name = str(iid)
        k = kw if isinstance(kw, dict) else {}
        if "length_constraints:number_words" in name:
            lo = k.get("num_words")
            rel = k.get("relation", "at least")
            if isinstance(lo, int):
                n = len(pred.split())
                if rel == "at least" and n < lo:
                    fails.append("words<" + str(lo))
                if rel == "less than" and n >= lo:
                    fails.append("words>=" + str(lo))
        elif "length_constraints:number_sentences" in name:
            lo = k.get("num_sentences")
            if isinstance(lo, int):
                n = len([s for s in re.split(r"[.!?]+", pred) if s.strip()])
                if n > lo:
                    fails.append("sentences>" + str(lo))
        elif "change_case:english_lowercase" in name:
            if pred != pred.lower():
                fails.append("not lowercase")
        elif "change_case:english_capital" in name:
            if pred != pred.upper():
                fails.append("not uppercase")
        elif "startend:end_checker" in name:
            end = k.get("end_phrase", "")
            if end and not pred.strip().rstrip(char_quote).endswith(end):
                fails.append("missing end phrase")
        elif "punctuation:no_comma" in name:
            if "," in pred:
                fails.append("has comma")
        elif "keywords:existence" in name:
            for word in (k.get("keywords") or []):
                if word.lower() not in pred.lower():
                    fails.append("missing " + word)
        elif "detectable_format:number_bullet_lists" in name:
            want = k.get("num_bullets")
            got = len(re.findall(r"^\s*[*-]\s", pred, re.M))
            if isinstance(want, int) and got != want:
                fails.append("bullets " + str(got) + "!=" + str(want))
    return (not fails), ("ok" if not fails else ";".join(fails[:3]))


char_quote = "\"'"


FILLER = (
    "The archive records describe routine administrative procedure in measured prose. "
    "Conditions were noted, deviations were logged, and the record was countersigned at the end of each period. "
)


def build_niah(target_tokens: int, rng: random.Random) -> tuple[str, str]:
    """Return (prompt, needle) for a needle-in-a-haystack item of about target_tokens."""
    needle = "MAGNOLIA-" + str(rng.randint(10000, 99999))
    sents = [FILLER for _ in range(max(4, target_tokens // 22))]
    pos = rng.randint(len(sents) // 5, len(sents) - len(sents) // 5)
    sents.insert(pos, " The verification token for this record is " + needle + ". ")
    body = "".join(sents)
    prompt = ("The following is a long archive dump. Read it and answer." + chr(10) + chr(10) + body +
              chr(10) + chr(10) + "Question: What is the verification token stated in the record? Reply with the token only.")
    return prompt, needle


def build_lc_reasoning(target_tokens: int, rng: random.Random) -> tuple[str, str, str]:
    """Return (prompt, question, answer) requiring aggregation of numbers buried in a long doc."""
    nums = [rng.randint(10, 99) * 3 for _ in range(6)]
    ans = str(sum(nums[:3]) - nums[3] + nums[4] * nums[5] % 97)
    sents = [FILLER for _ in range(max(4, target_tokens // 22))]
    for k, v in enumerate(nums):
        sents.insert((k + 1) * len(sents) // 8, " Ledger entry " + chr(65 + k) + " carries the value " + str(v) + ". ")
    body = "".join(sents)
    q = "Total the first three ledger values, subtract entry D, then add (entry E times entry F modulo 97)."
    prompt = "Long ledger dump:" + chr(10) + chr(10) + body + chr(10) + chr(10) + "Question: " + q + " End with a single number after ANSWER:."
    return prompt, q, ans


TOOLS_SPEC = [
    {"name": "search_files", "args": {"query": "string", "path": "string", "max_results": "integer"}},
    {"name": "read_file", "args": {"path": "string", "start_line": "integer", "end_line": "integer"}},
    {"name": "send_email", "args": {"to": "string", "subject": "string", "body": "string"}},
    {"name": "create_ticket", "args": {"title": "string", "priority": "string", "assignee": "string"}},
]

TOOL_CASES = [
    ("Find the three most recent log files under /var/log.", "search_files", {"query": "log", "path": "/var/log"}),
    ("Read lines 40 to 80 of /etc/app/config.yaml.", "read_file", {"path": "/etc/app/config.yaml"}),
    ("Email ops@example.com about the outage with subject Outage resolved.", "send_email", {"to": "ops@example.com", "subject": "Outage resolved"}),
    ("Open a high priority ticket titled Disk full assigned to mira.", "create_ticket", {"title": "Disk full", "priority": "high", "assignee": "mira"}),
    # ── extended 2026-09-16: tool calling rested on n=4, which is not enough to assign a role.
    # Target n>=20 so one item cannot move the ranking. Same grader (tool name + arg containment).
    ("Find configuration files under /srv/app.", "search_files", {"query": "config", "path": "/srv/app"}),
    ("List every markdown note in /home/dana/notes.", "search_files", {"query": "markdown", "path": "/home/dana/notes"}),  # C12-FIXTURE: synthetic eval path, not a repo/env path
    ("Search /data/raw for parquet files.", "search_files", {"query": "parquet", "path": "/data/raw"}),
    ("Locate backup archives under /mnt/archive.", "search_files", {"query": "backup", "path": "/mnt/archive"}),
    ("Read the first 25 lines of /srv/app/main.py.", "read_file", {"path": "/srv/app/main.py", "start_line": "1", "end_line": "25"}),
    ("Show lines 100 to 140 of /var/log/nginx/error.log.", "read_file", {"path": "/var/log/nginx/error.log", "start_line": "100", "end_line": "140"}),
    ("Open /home/dana/notes/plan.md.", "read_file", {"path": "/home/dana/notes/plan.md"}),  # C12-FIXTURE: synthetic eval path, not a repo/env path
    ("Read lines 7 to 9 of /etc/hosts.", "read_file", {"path": "/etc/hosts", "start_line": "7", "end_line": "9"}),
    ("Email the security team at security@example.com with subject Rotate keys.", "send_email", {"to": "security@example.com", "subject": "Rotate keys"}),
    ("Send a message to ana@example.com titled Weekly digest confirming the report.", "send_email", {"to": "ana@example.com", "subject": "Weekly digest"}),
    ("Notify billing@example.com that invoice 4471 is paid, subject Invoice paid.", "send_email", {"to": "billing@example.com", "subject": "Invoice paid"}),
    ("Mail legal@example.com about the trademark filing with subject Trademark filing.", "send_email", {"to": "legal@example.com", "subject": "Trademark filing"}),
    ("Open a low priority ticket called Update runbook for omar.", "create_ticket", {"title": "Update runbook", "priority": "low", "assignee": "omar"}),
    ("Create a critical ticket named API timeout assigned to jules.", "create_ticket", {"title": "API timeout", "priority": "critical", "assignee": "jules"}),
    ("File a medium priority ticket titled Add dark mode for sara.", "create_ticket", {"title": "Add dark mode", "priority": "medium", "assignee": "sara"}),
    ("Raise a high priority ticket about backup failures assigned to leo.", "create_ticket", {"title": "backup failures", "priority": "high", "assignee": "leo"}),
]

PLAN_CASES = [
    {"id": "plan-schedule", "answer": "30",
     "text": ("Three jobs on ONE machine, each 10 minutes, dependencies: C requires B; B requires A. "
              "A cannot start before t=0. What is the earliest finish time of C, in minutes?")},
    {"id": "plan-budget", "answer": "2",
     "text": ("You have 100 units of budget. Task X costs 40 and unlocks task Y (cost 30). Task Z costs 50 and "
              "cannot be done with Y (mutually exclusive). Maximise the number of completed tasks. How many tasks finish?")},
    {"id": "plan-order", "answer": "5",
     "text": ("Five steps must run in an order where: 3 is before 1; 4 is after 1; 5 is before 3; 2 is last. "
              "Which step runs first?")},
    # ── INVALIDATED 2026-09-17: 17 hand-written items were deleted here. 13 of them were
    # failed by EVERY model (0/7) — a harness signal, not a model result — and auditing the
    # gold answers confirmed they were simply wrong (crew 8 not 6, parallel 9 not 6, mix 50
    # not 8, deadline 0 not 5, tradeoff 1 not 3). Typed gold is drift. Their checkpoint rows
    # remain as a recorded mistake and are excluded from scoring by INVALID_ITEM_IDS in
    # tools/model_eval_report.py. Replacements come from tools/plan_cases_generated.py.
    # (3 original items remain above: plan-schedule, plan-budget, plan-order.)
]

HARDCODE = [
    {"id": "hc-lru",
     "prompt": "Implement LRUCache(capacity) with get(key) and put(key, value), both O(1). Return the class only.",
     "tests": ["c = LRUCache(2)", "c.put(1,1); c.put(2,2)", "assert c.get(1) == 1", "c.put(3,3)",
               "assert c.get(2) == -1", "c.put(4,4)", "assert c.get(1) == -1",
               "assert c.get(3) == 3", "assert c.get(4) == 4"]},
    {"id": "hc-parse",
     "prompt": ("Write parse_kv(s) that parses semicolon-separated key=value pairs, ignores empty segments, "
                "strips whitespace, and returns a dict. Values may contain the = character."),
     "tests": ["assert parse_kv('a=1; b = 2 ;; c=x=y') == {'a':'1','b':'2','c':'x=y'}",
               "assert parse_kv('') == {}", "assert parse_kv(' ; ') == {}"]},
    {"id": "hc-topo",
     "prompt": "Write topo_sort(n, edges) returning a valid topological order of nodes 0..n-1, or [] if a cycle exists.",
     "tests": ["assert topo_sort(3, [(0,1),(1,2)]) == [0,1,2]", "assert topo_sort(3, [(0,1),(1,0)]) == []",
               "assert len(topo_sort(4, [(0,1),(2,3)])) == 4"]},
    {"id": "hc-dp",
     "prompt": "Write min_coins(coins, amount) returning the minimum number of coins to make amount, or -1 if impossible.",
     "tests": ["assert min_coins([1,2,5], 11) == 3", "assert min_coins([2], 3) == -1", "assert min_coins([1], 0) == 0"]},
]

REVIEW_CASES = [
    {"id": "rv-zerodiv", "want": ["zero", "empty"],
     "text": "def avg(xs):" + chr(10) + "    return sum(xs) / len(xs)" + chr(10) + chr(10) + "What single bug makes this fail, and on what input?"},
    {"id": "rv-offbyone", "want": ["index", "out of range", "len(xs)-1"],
     "text": "def last(xs):" + chr(10) + "    return xs[len(xs)]" + chr(10) + chr(10) + "What is wrong?"},
    {"id": "rv-mutation", "want": ["shared", "mutable default", "both"],
     "text": ("def add_item(x, item, acc=[]):" + chr(10) + "    acc.append(item)" + chr(10) + "    return acc" +
              chr(10) + chr(10) + "What does the second call return? Explain why in one line.")},
    {"id": "rv-falseclaim", "want": ["false"],
     "text": "Claim: In Python, the expression 1.0 plus 2 == 3 evaluates to False because of float promotion. True or false? Answer with one word."},
    {"id": "rv-falseclaim2", "want": ["false"],
     "text": "Claim: HTTP 301 and 302 are semantically identical. True or false? Answer with one word."},
    {"id": "rv-shadow", "want": ["attribute", "dict", "shadow", "error"],
     "text": ("import json" + chr(10) + "json = {}" + chr(10) + "print(json.dumps({}))" + chr(10) + chr(10) + "What happens and why?")},
    {"id": "rv-emptyindex", "want": ["empty", "index"],
     "text": "def head(xs):" + chr(10) + "    return xs[0]" + chr(10) + chr(10) + "On what input does this raise an error?"},
    {"id": "rv-float", "want": ["false"],
     "text": "Claim: In Python, 0.1 + 0.2 == 0.3 evaluates to True. True or false? Answer with one word."},
    {"id": "rv-unbound", "want": ["unbound", "local", "before assignment"],
     "text": ("x = 5" + chr(10) + "def f():" + chr(10) + "    x = x + 1" + chr(10) + chr(10) + "What happens when f() is called, and why?")},
    {"id": "rv-sortnone", "want": ["none", "in place", "returns none"],
     "text": "def sort_list(xs):" + chr(10) + "    return xs.sort()" + chr(10) + chr(10) + "What does sort_list([3, 1, 2]) actually return? Answer with one word."},
]

STABILITY_ITEMS = [
    ("Classify the discipline: Attention is a limited resource allocated across competing tasks.", "cognitive psychology"),
    ("Classify the discipline: Firms internalise externalities when transaction costs are low.", "economics"),
    ("Classify the discipline: The meaning of a symbol depends on its relation to other symbols.", "semiotics"),
    ("Classify the discipline: Sparse representations reduce interference in associative memory.", "neuroscience"),
    ("Classify the discipline: Legibility of a typeface depends on x-height and contrast.", "typography"),
    ("Classify the discipline: Feedback loops with delay produce oscillation.", "systems thinking"),
    ("Classify the discipline: Framing effects alter choice under uncertainty.", "behavioural economics"),
    ("Classify the discipline: Compression is prediction and prediction is modelling.", "information theory"),
    ("Classify the discipline: A ritual stabilises group identity across generations.", "anthropology"),
    ("Classify the discipline: Cache locality dominates constant factors in runtime.", "computer architecture"),
]


def _load_jsonl(name: str) -> list[dict]:
    """Load a frozen eval-set JSONL."""
    p = EVALSETS / (name + ".jsonl")
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _usable_numeric_gold(answer: object) -> bool:
    """True when a frozen dataset row yields a parseable numeric gold (BUG-256).

    A row whose reference answer carries no number can never be graded correctly —
    it failed every model automatically and silently inflated the error rate.
    Drop such rows at load time (fail-closed on the DATASET, not on the model).
    """
    return _last_number(str(answer or "")) is not None


def _usable_letter_gold(answer: object, keys: str = "ABCDEFGHIJ") -> bool:
    """True when a frozen dataset row yields a single multiple-choice letter (BUG-256)."""
    a = str(answer or "").strip().upper()
    return len(a) == 1 and a in keys


def suite_gsm8k() -> list[dict]:
    return [{"id": r["id"], "system": COT, "max_tokens": 1200,
             "user": r["question"] + chr(10) + chr(10) + "End with ANSWER: followed by the number.",
             "grader": lambda pred, r=r: grade_numeric(pred, r["answer"])}
            for r in _load_jsonl("gsm8k") if _usable_numeric_gold(r.get("answer"))]


def suite_math500() -> list[dict]:
    return [{"id": r["id"], "system": COT, "max_tokens": 1600,
             "user": r["problem"] + chr(10) + chr(10) + "End with ANSWER: followed by the value.",
             "grader": lambda pred, r=r: grade_numeric(pred, r["answer"])}
            for r in _load_jsonl("math500") if _usable_numeric_gold(r.get("answer"))]


def suite_mmlu_pro() -> list[dict]:
    out = []
    for r in [x for x in _load_jsonl("mmlu_pro") if _usable_letter_gold(x.get("answer"))]:
        opts = chr(10).join("ABCDEFGHIJ"[i] + ". " + o for i, o in enumerate(r["options"]))
        out.append({"id": r["id"], "system": COT, "max_tokens": 800,
                    "user": r["question"] + chr(10) + opts + chr(10) + "Answer with the single letter.",
                    "grader": lambda pred, r=r: grade_letter(pred, r["answer"])})
    return out


def suite_humaneval() -> list[dict]:
    out = []
    for r in _load_jsonl("humaneval"):
        tests = [r["test"], "check(" + r["entry_point"] + ")"]
        out.append({"id": r["id"], "system": NO_COT, "max_tokens": 700,
                    "user": "Complete this Python function. Return only the code in one fenced block." + chr(10) + chr(10) + r["prompt"],
                    "grader": lambda pred, t=tests: grade_code(pred, t)})
    return out


_BUILTINS = {"print", "len", "sum", "range", "list", "dict", "set", "tuple", "round", "abs", "sorted",
             "max", "min", "int", "str", "float", "bool", "assert", "in", "is", "not", "and", "or", "all", "any",
             "enumerate", "zip", "map", "filter", "type", "isinstance", "reversed"}


def mbpp_entry_point(test_list: list[str]) -> str | None:
    """Infer the function name an MBPP test expects.

    MBPP-sanitized prompts never state the function name, yet its tests call one
    by name — so without this every row fails regardless of model quality. Pick
    the most frequently called identifier in the tests that is not a builtin.
    """
    counts: dict[str, int] = {}
    for t in test_list:
        for name in re.findall(r"([A-Za-z_]\w*)\s*\(", t):
            if name not in _BUILTINS:
                counts[name] = counts.get(name, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def suite_mbpp() -> list[dict]:
    out = []
    for r in _load_jsonl("mbpp"):
        name = mbpp_entry_point(list(r["test_list"]))
        if not name:
            continue
        out.append({"id": r["id"], "system": NO_COT, "max_tokens": 700,
                    "user": ("Write Python code solving this. Return only the code in one fenced block."
                             + chr(10) + chr(10) + r["prompt"]
                             + chr(10) + chr(10) + "Your function MUST be named exactly " + name + "."),
                    "grader": lambda pred, r=r, n=name: grade_code(pred, [n + " = " + n] + list(r["test_list"]))})
    return out


def suite_ifeval() -> list[dict]:
    return [{"id": r["id"], "system": NO_COT, "max_tokens": 700, "user": r["prompt"],
             "grader": lambda pred, r=r: grade_ifeval(pred, r["instruction_ids"], r["kwargs"])}
            for r in _load_jsonl("ifeval")]


def suite_hotpot() -> list[dict]:
    return [{"id": r["id"], "system": NO_COT, "max_tokens": 200,
             "user": "Answer the question using the passages. Give the shortest exact answer." + chr(10) + chr(10)
                     + r["context"] + chr(10) + chr(10) + "Question: " + r["question"],
             "grader": lambda pred, r=r: grade_contains(pred, r["answer"])} for r in _load_jsonl("hotpot_qa")]


def suite_niah() -> list[dict]:
    rng = random.Random(SEED)
    out = []
    # BUG-257: the top tier must stay inside the server's context window. oMLX runs with
    # max_context_window = 32768; a 32000-token prompt + max_tokens + chat-template overhead
    # returned HTTP 400 "Bad Request" for EVERY model, so that tier was unmeasurable (it is a
    # harness/config defect, not a model failure — same class as BUG-253/256).
    # 24000 + 40 output + overhead ~= 24.5k < 32768.
    for target in (4000, 12000, 24000):
        for k in range(3):
            prompt, needle = build_niah(target, rng)
            out.append({"id": "niah-" + str(target) + "-" + str(k), "system": NO_COT, "max_tokens": 40,
                        "user": prompt, "ctx_tokens": target,
                        "grader": lambda pred, n=needle: (n.lower() in pred.lower(), "needle=" + n)})
    return out


def suite_lc_reasoning() -> list[dict]:
    rng = random.Random(SEED + 1)
    out = []
    for k in range(6):
        prompt, _q, ans = build_lc_reasoning(16000, rng)
        out.append({"id": "lcr-" + str(k), "system": NO_COT, "max_tokens": 300, "ctx_tokens": 16000,
                    "user": prompt, "grader": lambda pred, a=ans: grade_numeric(pred, a)})
    return out


def suite_toolcalling() -> list[dict]:
    spec = chr(10).join("  " + t["name"] + ": " + json.dumps(t["args"]) for t in TOOLS_SPEC)
    sysmsg = ("You call tools. Reply ONLY with JSON of the form tool and args. Do not explain."
              + chr(10) + chr(10) + "Available tools:" + chr(10) + spec)

    def make_grader(tool: str, args: dict) -> Callable[[str], tuple[bool, str]]:
        def g(pred: str) -> tuple[bool, str]:
            m = re.search(r"\{.*\}", pred, re.S)
            if not m:
                return False, "no json"
            try:
                d = json.loads(m.group(0))
            except Exception:
                return False, "bad json"
            name = d.get("tool") or d.get("name") or d.get("function")
            if name in (None, "") and len(d) == 1:
                name = next(iter(d))
            if str(name).strip() != tool:
                return False, "tool=" + str(name)
            got = d.get("args") or d.get("arguments") or d.get("parameters")
            if not isinstance(got, dict):
                got = {k: v for k, v in d.items() if k not in ("tool", "name", "function")}
            for key, val in args.items():
                if str(val).lower() not in str(got.get(key, "")).lower():
                    return False, "arg " + key + "=" + str(got.get(key))
            return True, "ok"
        return g

    return [{"id": "tool-" + str(k), "system": sysmsg, "max_tokens": 200, "user": "Request: " + req,
             "grader": make_grader(tool, args)} for k, (req, tool, args) in enumerate(TOOL_CASES)]


def suite_planning() -> list[dict]:
    # The 17 hand-written items added 2026-09-16 were INVALIDATED: 13 of them were failed by every
    # model (0/7), which is a harness signal, not a model result — the gold answers were typed and
    # several were simply wrong (crew 8 not 6, parallel 9 not 6, mix 50 not 8, deadline 0 not 5).
    # tools/plan_cases_generated.py generates items whose answers are computed at build time by
    # Dijkstra / brute force / simulation, so they cannot be wrong without the generator being wrong.
    try:
        from plan_cases_generated import build as _build_generated      # run as a script
    except ImportError:                                                  # run as a module
        from tools.plan_cases_generated import build as _build_generated

    cases = list(PLAN_CASES) + _build_generated()
    return [{"id": c["id"], "system": COT, "max_tokens": 900,
             "user": c["text"] + chr(10) + chr(10) + "End with ANSWER: followed by the number.",
             "grader": lambda pred, c=c: grade_numeric(pred, c["answer"])} for c in cases]


def suite_hardcode() -> list[dict]:
    return [{"id": c["id"], "system": NO_COT, "max_tokens": 900,
             "user": c["prompt"] + " Return only the code in one fenced block.",
             "grader": lambda pred, c=c: grade_code(pred, list(c["tests"]))} for c in HARDCODE]


def suite_reviewing() -> list[dict]:
    def make_grader(want: list[str]) -> Callable[[str], tuple[bool, str]]:
        def g(pred: str) -> tuple[bool, str]:
            low = pred.lower()
            return (any(w.lower() in low for w in want), "want=" + str(want[:3]))
        return g

    return [{"id": c["id"], "system": NO_COT, "max_tokens": 200, "user": c["text"] + chr(10) + chr(10) + "Be brief.",
             "grader": make_grader(c["want"])} for c in REVIEW_CASES]


def suite_stability() -> list[dict]:
    out = []
    for rep in range(3):
        for k, (q, gold) in enumerate(STABILITY_ITEMS):
            out.append({"id": "stab-" + str(k) + "-r" + str(rep), "system": NO_COT, "max_tokens": 30,
                        "user": q + chr(10) + chr(10) + "Answer with the discipline name only.",
                        "grader": (lambda g: (lambda pred: (g in pred.lower(), "gold=" + g)))(gold),
                        "stab_key": "stab-" + str(k)})
    return out



# -- Extractive-summarisation drift suite: condense a passage to its central finding. --
# The gemma drift eval's "20 summ" leg (BUG-832 gate 3). Ground truth is DETERMINISTIC and
# non-LLM: each case carries one gold fact (must appear in the summary) and incidental
# distractors (must NOT appear — a model that "summarises" by echoing the passage leaks them).
# Recall + precision in one deterministic grader: no second LLM judge, so the grader cannot drift.
SUMM_CASES = [
    {"id": "summ-0", "gold": "daily coffee cut stroke risk by 12 percent",
     "distractors": ["42,000", "trade group"],
     "text": "A nine-year cohort study followed 42,000 adults. The work was partly funded by a beverage trade group. The central finding was that daily coffee cut stroke risk by 12 percent. Participants were recruited across northern Europe."},
    {"id": "summ-1", "gold": "green roofs lowered cooling costs by 18 percent",
     "distractors": ["Chicago", "500 buildings"],
     "text": "Researchers surveyed 500 buildings in Chicago. The study ran over three summers. The headline result was that green roofs lowered cooling costs by 18 percent. Several buildings used a new lightweight substrate."},
    {"id": "summ-2", "gold": "the vaccine reduced severe illness by 91 percent",
     "distractors": ["two-dose", "placebo"],
     "text": "A two-dose regimen was tested in a placebo-controlled trial. The trial enrolled participants across four countries. The key result was that the vaccine reduced severe illness by 91 percent. Follow-up lasted twelve months."},
    {"id": "summ-3", "gold": "model compression cut inference latency by 60 percent",
     "distractors": ["30 billion", "4-bit"],
     "text": "The authors compressed a 30 billion parameter model. The weights were quantized to 4-bit. The central finding was that model compression cut inference latency by 60 percent. The work was done in a university lab."},
    {"id": "summ-4", "gold": "an afternoon nap improved recall by 20 percent",
     "distractors": ["40 minutes", "university students"],
     "text": "Forty university students were tested after a 40 minute nap. The study controlled for caffeine intake. The main finding was that an afternoon nap improved recall by 20 percent. All sessions ran on weekdays."},
    {"id": "summ-5", "gold": "drip irrigation raised crop yields by 34 percent",
     "distractors": ["drought", "subsidized"],
     "text": "The trial covered a drought-prone region. Farmers were subsidized to install new equipment. The key result was that drip irrigation raised crop yields by 34 percent. Measurements spanned two growing seasons."},
    {"id": "summ-6", "gold": "hybrid work raised productivity by 13 percent",
     "distractors": ["2,000 employees", "tech firms"],
     "text": "A survey of 2,000 employees at tech firms compared three schedules. The data was gathered over one year. The central finding was that hybrid work raised productivity by 13 percent. Attrition was measured separately."},
    {"id": "summ-7", "gold": "the solid-state cell doubled driving range",
     "distractors": ["500 charge cycles", "prototype"],
     "text": "The prototype cell survived 500 charge cycles in testing. A ceramic separator replaced the liquid electrolyte. The headline result was that the solid-state cell doubled driving range. Manufacturing cost was not disclosed."},
    {"id": "summ-8", "gold": "walking three times a week cut depression risk by 26 percent",
     "distractors": ["older adults", "observational"],
     "text": "An observational study followed older adults for six years. Participants reported their habits on questionnaires. The main finding was that walking three times a week cut depression risk by 26 percent. Diet was not adjusted for."},
    {"id": "summ-9", "gold": "a 4096-token block cache gave a 22x speedup",
     "distractors": ["kernel", "five months"],
     "text": "The engineer worked on the change for five months. The change touched a low-level kernel path. The central result was that a 4096-token block cache gave a 22x speedup. Benchmarking used a fixed prefix."},
    {"id": "summ-10", "gold": "class size reduction lifted graduation rates by 7 points",
     "distractors": ["Tennessee", "kindergarten"],
     "text": "The study re-examined a Tennessee kindergarten cohort. Classrooms were assigned by lottery. The key finding was that class size reduction lifted graduation rates by 7 points. College enrollment was tracked as a secondary outcome."},
    {"id": "summ-11", "gold": "prefetching cut page-load latency by 41 percent",
     "distractors": ["beta", "mobile browsers"],
     "text": "The feature shipped to a beta group first. Tests ran on mobile browsers under simulated network conditions. The main result was that prefetching cut page-load latency by 41 percent. Cache size was increased too."},
    {"id": "summ-12", "gold": "solar panels paid back their energy cost in 1.2 years",
     "distractors": ["Germany", "rooftop"],
     "text": "The analysis covered rooftop arrays in Germany. Manufacturing and transport were included in the accounting. The headline finding was that solar panels paid back their energy cost in 1.2 years. Panel lifetime was assumed at 25 years."},
    {"id": "summ-13", "gold": "the revised algorithm solved 99.7 percent of instances",
     "distractors": ["C++", "open-source"],
     "text": "The solver was rewritten in C++ and released open-source. It was tested on a standard benchmark suite. The central finding was that the revised algorithm solved 99.7 percent of instances. Runtime was reduced as well."},
    {"id": "summ-14", "gold": "antibiotic overuse dropped by 30 percent after the audit",
     "distractors": ["rural clinics", "six months"],
     "text": "The audit was rolled out across rural clinics. Prescribers received feedback over six months. The key result was that antibiotic overuse dropped by 30 percent after the audit. Patient outcomes did not worsen."},
    {"id": "summ-15", "gold": "tree cover cooled summer streets by 4 degrees",
     "distractors": ["drones", "ten cities"],
     "text": "Researchers used drones to map ten cities. Measurements were taken at midday in summer. The main finding was that tree cover cooled summer streets by 4 degrees. Humidity was recorded alongside temperature."},
    {"id": "summ-16", "gold": "the new scheduler raised CPU utilization by 9 percent",
     "distractors": ["datacenter", "weekend"],
     "text": "The scheduler was tested in a datacenter over a weekend. Load came from production traffic. The central result was that the new scheduler raised CPU utilization by 9 percent. Tail latency stayed flat."},
    {"id": "summ-17", "gold": "early screening reduced mortality by 40 percent",
     "distractors": ["national registry", "15,000 patients"],
     "text": "The study drew on a national registry of 15,000 patients. Follow-up data was complete for most subjects. The headline finding was that early screening reduced mortality by 40 percent. Treatment costs were also compared."},
    {"id": "summ-18", "gold": "the fine-tuned model gained 11 points on the benchmark",
     "distractors": ["one hour", "single GPU"],
     "text": "Fine-tuning took under one hour on a single GPU. The dataset contained only a few thousand examples. The key result was that the fine-tuned model gained 11 points on the benchmark. General capability was unchanged."},
    {"id": "summ-19", "gold": "reduced meetings freed 7 hours per worker per week",
     "distractors": ["calendar data", "30 teams"],
     "text": "The analysis mined calendar data from 30 teams. The intervention removed recurring status meetings. The central finding was that reduced meetings freed 7 hours per worker per week. Deep-work time rose accordingly."},
]


# The DRIFT rubric: a summary drifts when it states the WRONG number or the WRONG topic, NOT when it
# paraphrases the right one. So grade on the two irreducible facts (the signal number + the concept noun),
# paraphrase-tolerant and deterministically anti-slop. Exact-phrase matching (the first draft) scored gemma
# 1/20 while its summaries were substantively correct — the grader, not the model, had drifted.
SUMM_KEYS = {
    "summ-0": ["12 percent", "stroke"], "summ-1": ["18 percent", "cooling"],
    "summ-2": ["91 percent", "illness"], "summ-3": ["60 percent", "latency"],
    "summ-4": ["20 percent", "recall"], "summ-5": ["34 percent", "yield"],
    "summ-6": ["13 percent", "productivity"], "summ-7": ["doubled", "range"],
    "summ-8": ["26 percent", "depression"], "summ-9": ["22x", "speedup"],
    "summ-10": ["7 points", "graduation"], "summ-11": ["41 percent", "latency"],
    "summ-12": ["1.2 years", "energy"], "summ-13": ["99.7 percent", "solved"],
    "summ-14": ["30 percent", "overuse"], "summ-15": ["4 degrees", "cool"],
    "summ-16": ["9 percent", "utilization"], "summ-17": ["40 percent", "mortality"],
    "summ-18": ["11 points", "benchmark"], "summ-19": ["7 hours", "freed"],
}


def suite_summ_extractive() -> list[dict]:
    def make_grader(c: dict):
        keys = [k.lower() for k in SUMM_KEYS.get(c["id"], [])]

        def g(pred: str) -> tuple[bool, str]:
            low = pred.lower()
            missing = [k for k in keys if k not in low]
            return (not missing, "ok" if not missing else "missing=" + str(missing))

        return g

    return [{"id": c["id"], "system": NO_COT, "max_tokens": 80,
             "user": c["text"] + chr(10) + chr(10) + "Summarize the single central finding in one sentence.",
             "grader": make_grader(c)} for c in SUMM_CASES]


# -- Delegation suite: faithfully implement a spec authored by a frontier model --
# The dominant real workload: a frontier model hands over a multi-clause spec with
# hard constraints and a local model must implement it without drift. Graded by
# AST + execution, not by vibes.

def _find_func(src: str, name: str) -> ast.AST | None:
    """Return the FunctionDef node with the given name, or None if absent/unparseable."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _has_import(src: str, module: str) -> bool:
    """True if src imports the given top-level module."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == module for a in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == module:
            return True
    return False


def _max_line_len(src: str) -> int:
    """Length of the longest line in src."""
    return max((len(l) for l in src.splitlines()), default=0)


def make_delegation_grader(fn: str, checks: list, run_tests: list) -> Callable[[str], tuple[bool, str]]:
    """Build a grader that verifies every clause of a delegated spec."""
    def g(pred: str) -> tuple[bool, str]:
        src = extract_code(pred)
        if not src:
            return False, "no code"
        failed: list[str] = []
        node = _find_func(src, fn)
        if node is None:
            return False, "missing function " + fn
        if "docstring" in checks and not ast.get_docstring(node):
            failed.append("no docstring")
        for c in checks:
            if c.startswith("no_import:") and _has_import(src, c.split(":", 1)[1]):
                failed.append("forbidden import " + c.split(":", 1)[1])
            if c.startswith("max_line_len:") and _max_line_len(src) > int(c.split(":", 1)[1]):
                failed.append("line too long")
            if c.startswith("max_lines:") and len(src.splitlines()) > int(c.split(":", 1)[1]):
                failed.append("too many lines")
        if run_tests:
            ok, detail = run_code_tests(src, run_tests)
            if not ok:
                failed.append("behaviour: " + str(detail)[:80])
        return (not failed), ("ok" if not failed else ";".join(failed[:4]))
    return g


DELEGATION_SPECS = [
    {"id": "dl-norm", "fn": "norm", "checks": ["no_import:numpy", "docstring", "max_line_len:100"],
     "spec": ("Implement exactly one function named norm taking a single argument xs. It must return a list "
              "of floats min-max normalised into [0,1], or [] for an empty input. Constraints: standard "
              "library only, do NOT import numpy, include a docstring, no line may exceed 100 characters."),
     "tests": ["assert norm([]) == []", "assert norm([5]) == [0.0]", "assert norm([0,10]) == [0.0,1.0]",
               "assert len(norm([1,2,3])) == 3"]},
    {"id": "dl-chunk", "fn": "chunk", "checks": ["docstring"],
     "spec": ("Implement exactly one function named chunk taking (seq, n) and returning a list of consecutive "
              "sublists of length n, with a final shorter sublist if not divisible. It must return [] when n "
              "is 0 or negative, and [] for an empty seq. Include a docstring."),
     "tests": ["assert chunk([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]", "assert chunk([], 3) == []",
               "assert chunk([1,2], 0) == []", "assert chunk([1], 1) == [[1]]"]},
    {"id": "dl-flatten", "fn": "flatten", "checks": ["no_import:itertools"],
     "spec": ("Implement exactly one function named flatten that recursively flattens arbitrarily nested "
              "lists and tuples into a single flat list of leaves. Standard library only; do NOT import "
              "itertools."),
     "tests": ["assert flatten([1,[2,[3,(4,)]]]) == [1,2,3,4]", "assert flatten([]) == []",
               "assert flatten([[],[[],1]]) == [1]"]},
    {"id": "dl-toint", "fn": "to_int", "checks": ["docstring"],
     "spec": ("Implement exactly one function named to_int that converts a string to int and returns the "
              "default value 0 instead of raising for any invalid input, including None. Use str methods "
              "only - do NOT use a bare except clause. Include a docstring."),
     "tests": ["assert to_int('42') == 42", "assert to_int('x') == 0", "assert to_int(None) == 0",
               "assert to_int(' 7 ') == 7"]},
    {"id": "dl-json", "fn": None, "checks": [], "tests": [],
     "spec": ("Return ONLY a JSON object, no prose and no code fence. The object must have exactly the keys "
              "status, count, items. status is the string ok. count is the integer 3. items is a list of "
              "exactly three strings. No extra keys are permitted.")},
    {"id": "dl-tabular", "fn": None, "checks": [], "tests": [],
     "spec": ("Return ONLY a JSON array of exactly 2 objects, no prose and no code fence. Each object must "
              "have exactly the keys name and score. score must be a number. No extra keys.")},
]


def _grade_dl_json(pred: str, keys: list, n_items: int | None) -> tuple[bool, str]:
    """Grade a strict JSON delegation: exact key set, no prose, optional item count."""
    t = pred.strip()
    if not (t.startswith("{") or t.startswith("[")):
        return False, "prose or code fence present"
    try:
        d = json.loads(t)
    except Exception:
        m = re.search(r"[\{\[].*[\}\]]", t, re.S)
        if not m:
            return False, "not json"
        try:
            d = json.loads(m.group(0))
        except Exception:
            return False, "not json"
    if isinstance(d, list):
        if n_items is not None and len(d) != n_items:
            return False, "want " + str(n_items) + " items got " + str(len(d))
        obj = d[0] if d else {}
    else:
        obj = d
    if not isinstance(obj, dict):
        return False, "not an object"
    if set(obj.keys()) != set(keys):
        return False, "keys " + str(sorted(obj.keys())) + " want " + str(sorted(keys))
    return True, "ok"


def suite_delegation() -> list[dict]:
    """Build the delegated-spec-implementation suite."""
    out = []
    for spec in DELEGATION_SPECS:
        if spec["fn"]:
            g = make_delegation_grader(spec["fn"], list(spec["checks"]), list(spec["tests"]))
        elif spec["id"] == "dl-json":
            g = lambda pred: _grade_dl_json(pred, ["status", "count", "items"], None)
        else:
            g = lambda pred: _grade_dl_json(pred, ["name", "score"], 2)
        out.append({"id": spec["id"], "system": NO_COT, "max_tokens": 600,
                    "user": "Implement this specification exactly. Return only the code in one fenced block, "
                            "or only JSON when the spec asks for JSON." + chr(10) + chr(10) + spec["spec"],
                    "grader": g})
    return out


# -- Voting suite: classify the 251 gold rows with every candidate voter --
# Purpose: build the AGREEMENT and ERROR-CORRELATION matrix among LOCAL models so we
# can decide (a) which model is the most accurate/reliable classifier, (b) whether a
# voting ensemble beats the best single model, and (c) which voters to use.
#
# Gold caveat (see tools/vote_analysis.py): 164/251 discipline labels were produced by
# the reliable pair AGREEING (circular), and the remaining 87 are the pairs HARD
# disagreements (selection bias). So absolute accuracy here is only meaningful for
# models that never participated in producing the gold -- which is exactly the local
# candidates. Agreement/correlation is valid regardless.

_DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
_GOLD_PATH = ROOT / "governance" / "gold_4axis.jsonl"
_TAX_PATH = ROOT / "config" / "taxonomy.yaml"


def _voting_taxonomy() -> tuple[list, list]:
    """Return (disciplines, domains) canonical names from taxonomy.yaml."""
    import yaml  # local import: optional dependency for this suite only
    t = yaml.safe_load(_TAX_PATH.read_text(encoding="utf-8"))
    cand = lambda v: v["canonical"] if isinstance(v, dict) else v
    return [cand(x) for x in t["disciplines"]], [cand(x) for x in t["domains"]]


def _voting_texts(fb_ids: list) -> dict:
    """Fetch the FB text (name/definition/mechanism/boundary) from the SQLite DB."""
    db = sqlite3.connect(str(_DB_PATH))
    db.row_factory = sqlite3.Row
    q = "SELECT fb_id, name, definition, mechanism, boundary FROM fbs WHERE fb_id IN (%s)" % (
        ",".join("?" * len(fb_ids)))
    out: dict = {}
    for r in db.execute(q, fb_ids):
        parts = [p for p in (r["name"], r["definition"], r["mechanism"], r["boundary"]) if p]
        out[r["fb_id"]] = " ".join(parts)[:2048]
    db.close()
    return out


def suite_voting() -> list[dict]:
    """Build one classification item per gold row, using the production-style prompt."""
    rows = [json.loads(l) for l in _GOLD_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("discipline") and r.get("domains")]
    discs, doms = _voting_taxonomy()
    texts = _voting_texts([r["fb_id"] for r in rows])
    if not texts:
        # BUG-942: fail loud, not opaque. 0 gold fb_ids resolve in the live DB — the anchor
        # was built against a superseded corpus generation (fb_id = sha256(name|definition)
        # is generation-sensitive, F-19/D-2949). Do NOT re-point ids; rebuild the anchor.
        raise RuntimeError(
            "gold anchor orphaned: 0/" + str(len(rows)) + " gold fb_ids resolve in the live DB "
            + "(" + str(_DB_PATH) + "). Anchor built against a superseded corpus generation "
            + "(fb_id = sha256(name|definition) is generation-sensitive). Rebuild the anchor "
            + "against the live generation (owner-gated) — do NOT re-point ids.")
    out = []
    for r in rows:
        text = texts.get(r["fb_id"]) or ""
        if not text:
            continue
        gold_d = str(r["discipline"]).strip().lower()
        gold_dom = frozenset(str(x).strip().lower() for x in r["domains"])

        def grader(pred: str, gd: str = gold_d, gdom: frozenset = gold_dom) -> tuple[bool, str]:
            m = re.search(r"\{.*\}", pred, re.S)
            if not m:
                return False, "no json"
            try:
                d = json.loads(m.group(0))
            except Exception:
                return False, "bad json"
            pd = str(d.get("discipline", "")).strip().lower()
            pdom = frozenset(str(x).strip().lower() for x in (d.get("domains") or []))
            exact = 1 if pd == gd else 0
            tp = len(gdom & pdom)
            p = tp / len(pdom) if pdom else 0.0
            rc = tp / len(gdom) if gdom else 0.0
            f1 = 0.0 if (p + rc) == 0 else 2 * p * rc / (p + rc)
            return bool(exact), "disc=" + str(exact) + " dom_f1=" + format(f1, ".3f")

        prompt = ("Classify this principle into exactly ONE discipline and ONE OR MORE domains."
                  + chr(10) + "Disciplines: " + ", ".join(discs)
                  + chr(10) + "Domains: " + ", ".join(doms)
                  + chr(10) + chr(10) + "Principle: " + text + chr(10) + chr(10)
                  + chr(39) + "Return ONLY JSON: {\"discipline\": \"<one>\", \"domains\": [\"<d1>\", ...]}" + chr(39))
        # max_tokens 512: reasoning models (gpt-oss, Ornith MoE) emit a thinking trace
        # first. At 120 they were truncated to prose and scored 0 -- a harness artifact,
        # not a model failure. Non-reasoning models finish far below this, so their
        # results are unaffected by the bump.
        # Uniform reasoning suppression for EVERY voter. Reasoning models (gpt-oss,
        # Ornith MoE) otherwise emit a thinking trace and never reach the JSON, which
        # measures truncation rather than classification. Production applies the same
        # idea (config: verifier.reasoning_off_prefix = "Reasoning: low", plus explicit
        # "No reasoning." directives in the depth prompts). Applied uniformly so the
        # agreement/correlation matrix stays comparable.
        # "Reasoning: low" is the production prefix (config: verifier.reasoning_off_prefix).
        # Verified empirically 2026-09-16: with the full 61-discipline taxonomy in the
        # prompt, reasoning models (gpt-oss, Ornith MoE) otherwise deliberate past the
        # budget and emit prose instead of JSON. The prefix restores strict JSON AND
        # roughly halves latency (gpt-oss 16s -> 9s). Applied uniformly to every voter.
        out.append({"id": r["fb_id"], "system": "You are a precise taxonomy classifier.",
                    "user": "Reasoning: low" + chr(10) + chr(10) + prompt,
                    "max_tokens": 512, "grader": grader})
    return out


ABSTAIN_SYSTEM = (
    "You decide whether a candidate is TRANSFERABLE KNOWLEDGE (a principle) or must be "
    "REFUSED. Reply with JSON only, no prose: "
    '{"content_type": "<one of: principle, process_template, process_instance, '
    'tool_instruction, noise_drop, growth_edge>", "reason": "<short>"}. '
    "Choose a non-principle label whenever the candidate is a repeatable how-to recipe, "
    "a tool invocation, a single one-off event, or noise. Never call something a "
    "principle just to be helpful."
)


def _abstain_verdict(pred: str) -> str | None:
    """Extract the binarised verdict from a reply; None when unparseable (D-2637)."""
    m = re.search(r'\{.*\}', pred or '', re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    ct = str(d.get('content_type', '')).strip().lower()
    if not ct:
        return None
    return 'principle' if ct == 'principle' else 'not_principle'


def grade_abstain(pred: str, gold: str) -> tuple[bool, str]:
    """Grade fail-closed behaviour: principle vs not-principle (D-2637).

    gold is 'principle' or 'not_principle'. A model is CORRECT when it refuses a
    non-principle (abstains) and when it accepts a real principle. It fails by
    fabricating a principle from a process template, tool instruction or noise —
    the exact failure mode the pipeline's fail-closed validators exist to prevent.
    """
    v = _abstain_verdict(pred)
    if v is None:
        return False, 'unparseable (no content_type)'
    return v == gold, 'pred=' + str(v) + ' gold=' + str(gold)


def suite_abstain() -> list[dict]:
    """Fail-closed suite: does the model refuse to fabricate a principle?"""
    return [{'id': r['id'], 'system': ABSTAIN_SYSTEM, 'max_tokens': 300,
             'user': r['text'] + chr(10) + chr(10) + 'Classify.',
             'grader': lambda pred, r=r: grade_abstain(pred, r['answer'])}
            for r in _load_jsonl('abstain')]

SUITES: dict[str, Callable[[], list[dict]]] = {
    "gsm8k": suite_gsm8k, "math500": suite_math500, "mmlu_pro": suite_mmlu_pro,
    "humaneval": suite_humaneval, "mbpp": suite_mbpp, "ifeval": suite_ifeval,
    "hotpot_qa": suite_hotpot, "niah": suite_niah, "lc_reasoning": suite_lc_reasoning,
    "toolcalling": suite_toolcalling, "planning": suite_planning,
    "hardcode": suite_hardcode, "reviewing": suite_reviewing, "stability": suite_stability,
    "delegation": suite_delegation, "voting": suite_voting, "abstain": suite_abstain,
    "summ_extractive": suite_summ_extractive,
}


# RETIRED MODELS (D-2637 gate [[G3]], retired 2026-09-16). A retired model is not in the oMLX
# registry, so every request 404s: that burns wall-clock AND writes rows that read as model
# failures (BUG-253 class). Enforcing retirement HERE means the decision cannot be silently
# un-made by a stale models-file. Measured basis for OptiQ: 40 of 128 voting rows came back
# 'no json' (it reasons first, hits max_tokens=512, and the JSON is truncated mid-string) vs
# 0 format failures for the uniform 4-bit, at 75.9s vs 16.5s per row — a 31% output-contract
# failure, which is disqualifying for a fail-closed pipeline regardless of raw accuracy.
RETIRED_MODELS: set[str] = {"Qwen3.8-27B-OptiQ-4bit", "Ornith-1.5-9B-OptiQ-4bit"}


def _done_keys() -> set[str]:
    """Return the model|suite|id keys that count as DONE.

    Only rows with NO transport error count. A row whose err field is set (404,
    ConnectionError, timeout -- e.g. because oMLX was restarting mid-run) is a
    measurement we never took, so it must be retried on resume. Without this a
    transient outage gets baked in as a permanent model failure.
    """
    if not CKPT.exists():
        return set()
    keys = set()
    for line in CKPT.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("err"):
            continue
        keys.add(str(d.get("model")) + "|" + str(d.get("suite")) + "|" + str(d.get("id")))
    return keys


_CELL_STATUS: dict[str, str] = {}


def _cell_status(model: str, suite: str, items: list[dict]) -> str:
    """Pre-flight one (model, suite) cell with the suite's real budget (mechanism M1).

    WHY: this harness sends a request and grades the RESPONSE. It could not tell "the model is
    bad" from "the harness asked something the model could not answer", so an ungradable response
    was recorded as a wrong answer. BUG-262 (gpt-oss 0.00 toolcalling = missing reasoning-off
    prefix), BUG-263 (judge max_tokens=64 vs a reasoning model), BUG-257 (400 at ctx 32000 scored
    as 0) and the OptiQ run (31% "no json") are all that one bug. A cell that fails this probe is
    NA: it is skipped, never scored as 0.

    Args:
        model: model id as served by oMLX.
        suite: suite name.
        items: the built suite items (the first item supplies the real max_tokens/ctx_tokens).

    Returns:
        'VALID' when the cell can produce a gradable answer, else the failure classification.

    Raises:
        RuntimeError: the gate itself is unusable — a missing gate must not pass silently (C16).
    """
    key = model + "|" + suite
    if key in _CELL_STATUS:
        return _CELL_STATUS[key]
    try:
        import bench_preflight as bp

        cfg = bp.load_config()
        item = dict(items[0])
        item.setdefault("max_tokens", 512)
        status = str(bp.probe_cell(cfg, model, suite, item, call)["status"])
    except Exception as exc:
        raise RuntimeError("preflight gate unusable for " + key + ": " + type(exc).__name__ + " " + str(exc)[:120]) from exc
    _CELL_STATUS[key] = status
    return status


def main() -> int:
    """Run the selected suites across the selected models, checkpointing each result."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--models-file", default=None)
    ap.add_argument("--suites", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=0, help="cap items per suite (0 = all)")
    args = ap.parse_args()

    models = list(args.models or [])
    if args.models_file:
        models += [l.strip() for l in Path(args.models_file).read_text(encoding='utf-8').splitlines()
                   if l.strip() and not l.strip().startswith("#")]
    if not models:
        print("no models given")
        return 2

    retired = [m for m in models if m in RETIRED_MODELS]
    if retired:
        models = [m for m in models if m not in RETIRED_MODELS]
        print("SKIP retired models: " + ", ".join(retired), flush=True)
    if not models:
        print("all requested models are retired — nothing to do")
        return 0

    # M1 environment gate: an unsafe environment invalidates the whole run (disk floor,
    # registry drift, or another benchmark holding the single resident model — BUG-255).
    try:
        import bench_preflight as bp

        _cfg = bp.load_config()
        _findings, _unsafe = bp.check_environment(_cfg, models, full=True)
        if _unsafe:
            for _f in _findings:
                if not _f["ok"]:
                    print("PREFLIGHT ENV FAIL " + str(_f["check"]) + ": " + str(_f["detail"]), flush=True)
            print("refusing to run: environment unsafe (see tools/bench_preflight.py)", flush=True)
            return 2
    except Exception as exc:
        print("PREFLIGHT GATE UNUSABLE: " + type(exc).__name__ + " " + str(exc)[:140], flush=True)
        return 2

    suites = args.suites or list(SUITES)
    done = _done_keys()
    build_failures: list[str] = []
    total = 0
    t0 = time.time()

    for suite in suites:
        try:
            items = SUITES[suite]()
        except Exception as exc:
            # C16 — no silent errors. A suite that fails to BUILD used to print one line and be
            # skipped, so a broken builder looked like a completed run ("done in 0s, 0 new
            # results"). That is how the invalid planning items survived a whole night. Record it
            # and make main() exit non-zero.
            print("SUITE BUILD FAILED " + suite + ": " + type(exc).__name__ + " " + str(exc)[:140], flush=True)
            build_failures.append(suite)
            continue
        if args.limit:
            items = items[:args.limit]
        print(chr(10) + "=== " + suite + " (" + str(len(items)) + " items)", flush=True)

        for model in models:
            try:
                status = _cell_status(model, suite, items)
            except Exception as exc:
                print("PREFLIGHT GATE FAILED: " + type(exc).__name__ + " " + str(exc)[:160], flush=True)
                return 2
            if status != "VALID":
                rec = {"model": model, "suite": suite, "id": "__preflight__", "ok": False,
                       "na": True, "na_reason": status, "detail": "harness-invalid cell: " + status,
                       "secs": 0, "err": None, "ctx_tokens": None, "stab_key": None, "pred": ""}
                with CKPT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + chr(10))
                print("  " + model[:40].ljust(40) + " " + suite.ljust(13)
                      + " NA (harness-invalid: " + status + ") — NOT scored as 0", flush=True)
                continue
            passes = fails = skips = 0
            for it in items:
                key = model + "|" + suite + "|" + str(it["id"])
                if key in done:
                    skips += 1
                    continue
                t = time.time()
                try:
                    pred = call(model, it["system"], it["user"], it.get("max_tokens", 512))
                    ok, detail = it["grader"](pred)
                    err = None
                except Exception as exc:
                    pred, ok, detail, err = "", False, "call failed", type(exc).__name__ + " " + str(exc)[:140]
                dur = round(time.time() - t, 1)
                rec = {"model": model, "suite": suite, "id": it["id"], "ok": bool(ok), "detail": detail,
                       "secs": dur, "err": err, "ctx_tokens": it.get("ctx_tokens"),
                       "stab_key": it.get("stab_key"), "pred": pred[:400]}
                with CKPT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + chr(10))
                passes += 1 if ok else 0
                fails += 0 if ok else 1
                total += 1
            acc = round(passes / max(passes + fails, 1), 3)
            print("  " + model[:40].ljust(40) + " " + suite.ljust(13) + " acc=" + str(acc)
                  + "  n=" + str(passes + fails) + ("  skipped=" + str(skips) if skips else ""), flush=True)

    print(chr(10) + "done in " + str(round(time.time() - t0)) + "s, " + str(total) + " new results")
    if build_failures:
        print("FAILED TO BUILD: " + ", ".join(build_failures) + " — run is INCOMPLETE")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
