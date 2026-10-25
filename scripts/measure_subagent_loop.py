#!/usr/bin/env python3
"""measure_subagent_loop.py - D-2549/T-131/T-185: THE PER-MODEL SUB-AGENT LOOP MEASUREMENT.

WHY THIS EXISTS (measured, not asserted). T-131 rests on ONE reading of ONE model: gemma-4-E4B-it-MLX-4bit
answered an interactive loop in 54.7 s against a 60 s budget, so config/model_assignments.yaml#harness_roles
calls it "the only served model ROUTABLE for agent_loop". One model and one reading are not a portfolio, and a
model that has never been asked to drive a loop must not be assumed able to. This script asks EVERY served model
the SAME fixed question and records the three things a sub-agent must do:

    (1) CALL a tool, (2) call it AGAIN on what it learned, (3) ANSWER with the right value inside the declared
    per-turn budget. Pass requires ALL THREE. A model that answers correctly without calling the tool FAILS:
    it is a chat model, and delegating a loop to it would be a silent capability lie (BUG-873's shape).

NO VALUE LIVES HERE (C12). The served set, the base_url and the key are read from the harness's own declaration
(config/agent_context.yaml#homes.declaration -> the goose custom-provider file); the per-turn budget is read from
ratified.knobs.per_turn_budget_s; the fixture is GENERATED (three files of 3/4/5 lines) so no expected answer is
typed anywhere. The only file written is the receipt.

Usage:
  python3 scripts/measure_subagent_loop.py                    # every served model + a receipt
  python3 scripts/measure_subagent_loop.py --only MODEL       # one model
  python3 scripts/measure_subagent_loop.py --selftest         # known-answer controls; NO model is called
Exit: 0 every model measured and passed | 2 at least one model FAILED (reported, never fatal - BUG-457).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIG = ROOT / "config/agent_context.yaml"

def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Read one declared YAML file (the repository's own idiom: a local import, no helper invented)."""
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

MAX_TURNS = 5
FIXTURE_LINES = (3, 4, 5)


def declaration() -> dict[str, Any]:
    """The harness's own declaration of what is served and where (no path is constructed here, C12)."""
    decl = _yaml(CONFIG)
    path = pathlib.Path(str(decl["homes"]["declaration"]).replace("~", str(pathlib.Path.home())))
    return json.loads(path.read_text(encoding="utf-8"))


def budget_s() -> float:
    """The owner's per-turn budget, from its ONE home (a missing value is FATAL, never a default: C16)."""
    decl = _yaml(CONFIG)
    value = decl["ratified"]["knobs"].get("per_turn_budget_s")
    if not isinstance(value, (int, float)):
        raise SystemExit("FATAL: config/agent_context.yaml#ratified.knobs.per_turn_budget_s is absent - "
                         "refusing to invent a budget (C16/C12)")
    return float(value)


def make_fixture(root: pathlib.Path) -> tuple[pathlib.Path, int]:
    """Write the generated fixture and return (dir, expected total lines). Generated, so nothing is a constant."""
    root.mkdir(parents=True, exist_ok=True)
    total = 0
    for index, lines in enumerate(FIXTURE_LINES):
        name = f"{chr(ord('a') + index)}.txt"
        (root / name).write_text("".join(f"line {n}\n" for n in range(1, lines + 1)), encoding="utf-8")
        total += lines
    return root, total


TOOL = {
    "type": "function",
    "function": {
        "name": "read_lines",
        "description": "Return the number of lines in one file of the fixture directory.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"]},
    },
}


def ask(url: str, key: str, model: str, messages: list[dict[str, Any]], max_tokens: int,
        tools: list[dict[str, Any]] | None = None) -> tuple[dict, float, dict]:
    """ONE chat completion with the tools declared. Returns (reply, wall_seconds, usage).
    usage carries the engine's own counters (TTFT, decode rate) for the T-187 per-step receipt. R7."""
    body = json.dumps({"model": model, "messages": messages, "tools": tools or [TOOL],
                       "temperature": 0.0, "max_tokens": max_tokens, "stream": False}).encode()
    request = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": key})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=180) as response:
        reply = json.loads(response.read())
    return reply, time.monotonic() - started, reply.get("usage") or {}


def grade(calls: int, answer: str, expected: int, walls: list[float], budget: float) -> tuple[str, str]:
    """The PURE verdict. Two-sided by construction: it refuses a right answer with no tool call."""
    if calls < len(FIXTURE_LINES):
        return "FAIL", f"called the tool {calls}x, wanted >= {len(FIXTURE_LINES)} (an agent loop must USE a tool)"
    if str(expected) not in answer:
        return "FAIL", f"final answer does not carry {expected}: {answer.strip()[:80]!r}"
    over = [round(w, 1) for w in walls if w > budget]
    if over:
        return "FAIL", f"turn(s) over the declared budget {budget:g}s: {over}"
    return "PASS", f"{calls} tool call(s), answer carries {expected}, slowest turn {max(walls):.1f}s"


def run_model(decl: dict[str, Any], model: str, budget: float, workdir: pathlib.Path) -> dict[str, Any]:
    """Drive the fixed loop against ONE model and return its receipt row."""
    url = str(decl["base_url"]).rstrip("/") + "/chat/completions"
    key = str((decl.get("headers") or {}).get("Authorization", ""))
    fixture, expected = make_fixture(workdir)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are a sub-agent. You MUST use the provided tool; never guess a count."},
        {"role": "user", "content": "Call read_lines once for each of a.txt, b.txt and c.txt in "
                                    f"{fixture}. Then answer with the TOTAL number of lines as a single integer."},
    ]
    calls, walls, answer, error = 0, [], "", ""
    for _ in range(MAX_TURNS):
        try:
            reply, wall, _ = ask(url, key, model, messages, 256)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            break
        walls.append(wall)
        message = reply["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            answer = str(message.get("content") or "")
            break
        messages.append(message)
        for call in tool_calls:
            calls += 1
            try:
                path = json.loads(call["function"]["arguments"]).get("path", "")
                count = len(pathlib.Path(path).read_text(encoding="utf-8").splitlines())
                payload = str(count)
            except (ValueError, OSError, KeyError) as exc:
                payload = f"error: {type(exc).__name__}"
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": payload})
    if error:
        verdict, detail = "FAIL", error
    else:
        verdict, detail = grade(calls, answer, expected, walls, budget)
    return {"model": model, "verdict": verdict, "detail": detail, "tool_calls": calls,
            "slowest_turn_s": round(max(walls), 1) if walls else None,
            "turns": len(walls), "answer": answer.strip()[:60]}


# ── T-187: THE TWO-STEP / TWO-TOOL FIXTURE ──────────────────────────────────────────────────────────
# A single trivial read cannot distinguish "drives a loop" from "calls a tool once and guesses": the fixed
# 3-call fixture passed 7 of 8 served models yet answered one number a 2B model can read. This fixture asks
# for TWO DEPENDENT steps across TWO tools with a DISTRACTOR, and an expected answer only the SECOND tool's
# output can produce. Promotion of AGENT_LOOP_FAST / AGENT_LOOP_WORKHORSE is gated on it (D-3058/T-187).

TOKEN_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_token",
        "description": "Return the token value stored under a numeric key in the fixture's token map.",
        "parameters": {"type": "object", "properties": {"key": {"type": "string"}},
                       "required": ["key"]},
    },
}

# The fixture shape (the same category as FIXTURE_LINES above: the generated fixture's declared geometry,
# never a typed answer — the expected value is DERIVED from the files, C12).
TWO_STEP_SEED_LINES = 7
TWO_STEP_DECOY_LINES = 3
TWO_STEP_TOKEN_KEYS = 11


def make_two_step_fixture(root: pathlib.Path) -> tuple[pathlib.Path, str, str]:
    """Write the T-187 fixture and return (dir, expected_key, expected_value).
    seed.txt holds K lines; decoy.txt holds J lines (a VALID key, so a sloppy read yields a plausible wrong
    answer); tokens.json is the key->value map the lookup tool reads. The expected answer is derived, never
    typed (C12)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "seed.txt").write_text(
        "".join(f"line {n}\n" for n in range(1, TWO_STEP_SEED_LINES + 1)), encoding="utf-8")
    (root / "decoy.txt").write_text(
        "".join(f"line {n}\n" for n in range(1, TWO_STEP_DECOY_LINES + 1)), encoding="utf-8")
    token_map = {str(i): f"token-{i}" for i in range(1, TWO_STEP_TOKEN_KEYS + 1)}
    (root / "tokens.json").write_text(json.dumps(token_map), encoding="utf-8")
    return root, str(TWO_STEP_SEED_LINES), token_map[str(TWO_STEP_SEED_LINES)]


def grade_two_step(calls_read: int, calls_lookup: int, lookup_keys: list[str], answer: str,
                   expected: str, expected_key: str, walls: list[float], budget: float) -> tuple[str, str]:
    """The T-187 PURE verdict. Two dependent steps must BOTH happen, the second must key off the first's
    output, and the answer must carry what only the second tool's output can produce."""
    if calls_read < 1:
        return "FAIL", "never called read_lines (step 1) - a loop must read before it can key"
    if calls_lookup < 1:
        return "FAIL", "never called lookup_token (step 2) - an answer without step 2 is a guess"
    if expected_key not in lookup_keys:
        return "FAIL", f"lookup_token keys {lookup_keys} never used the seed-derived key {expected_key!r}"
    if expected not in answer:
        return "FAIL", f"final answer does not carry {expected}: {answer.strip()[:80]!r}"
    over = [round(w, 1) for w in walls if w > budget]
    if over:
        return "FAIL", f"turn(s) over the declared budget {budget:g}s: {over}"
    return "PASS", (f"read_lines x{calls_read}, lookup_token x{calls_lookup} (key {expected_key}), "
                    f"answer carries {expected}, slowest turn {max(walls):.1f}s")


def run_two_step_model(decl: dict[str, Any], model: str, budget: float, workdir: pathlib.Path) -> dict[str, Any]:
    """Drive the T-187 two-step loop against ONE model and return its receipt row (TTFT + decode rate per
    step, from the engine's own counters)."""
    url = str(decl["base_url"]).rstrip("/") + "/chat/completions"
    key = str((decl.get("headers") or {}).get("Authorization", ""))
    fixture, expected_key, expected = make_two_step_fixture(workdir)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are a sub-agent. You MUST use the provided tools; never guess a "
                                      "value. Step 1: call read_lines on seed.txt to learn its line count. "
                                      "Step 2: call lookup_token with that line count as the key. Then answer "
                                      "with the returned token as a single word. Ignore decoy.txt."},
        {"role": "user", "content": f"Find the token whose key equals the number of lines in {fixture}/seed.txt."},
    ]
    calls_read, calls_lookup, lookup_keys, answer, error = 0, 0, [], "", ""
    walls: list[float] = []
    steps: list[dict[str, Any]] = []
    token_map = json.loads((fixture / "tokens.json").read_text(encoding="utf-8"))
    for _ in range(MAX_TURNS):
        try:
            reply, wall, usage = ask(url, key, model, messages, 256, tools=[TOOL, TOKEN_TOOL])
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            error = f"{type(exc).__name__}: {exc}"
            break
        walls.append(wall)
        steps.append({"wall_s": round(wall, 2), "ttft_s": usage.get("time_to_first_token"),
                      "decode_tps": usage.get("generation_tokens_per_second"),
                      "prompt_tps": usage.get("prompt_tokens_per_second")})
        message = reply["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            answer = str(message.get("content") or "")
            break
        messages.append(message)
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except ValueError:
                args = {}
            if name == "read_lines":
                calls_read += 1
                try:
                    payload = str(len(pathlib.Path(args.get("path", "")).read_text(encoding="utf-8").splitlines()))
                except (OSError, KeyError) as exc:
                    payload = f"error: {type(exc).__name__}"
            elif name == "lookup_token":
                calls_lookup += 1
                lookup_keys.append(str(args.get("key", "")))
                payload = str(token_map.get(str(args.get("key", "")), "error: unknown key"))
            else:
                payload = f"error: undeclared tool {name!r}"
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": payload})
    if error:
        verdict, detail = "FAIL", error
    else:
        verdict, detail = grade_two_step(calls_read, calls_lookup, lookup_keys, answer,
                                         expected, expected_key, walls, budget)
    return {"model": model, "verdict": verdict, "detail": detail, "calls_read": calls_read,
            "calls_lookup": calls_lookup, "lookup_keys": lookup_keys,
            "slowest_turn_s": round(max(walls), 1) if walls else None,
            "turns": len(walls), "steps": steps, "answer": answer.strip()[:60]}


# ── T-199: THE LOOP BATTERY — one fixture ADMITS a model, a battery RANKS one ───────────────────────
# The two-step fixture above proves a model can CHAIN two dependent calls. It cannot see four failure
# classes that decide whether a loop is safe to delegate to, and R-15 recorded why one fixture is not
# enough: a 1-task instrument cannot resolve a 3-point gap on 120 tasks. Each fixture below DERIVES its
# expected answer from generated files (C12: no expected value is typed), names the failure it measures,
# and carries a two-sided known-answer control in --selftest. Nothing is downloaded: the population is
# the roster that is ALREADY served (0 GB), and every call is temperature 0 (R7).

# MEASURED 2026-10-25: at the 256-token allowance the older fixtures use, gpt-oss-20b-MXFP4-Q8 spent 897 of 900
# completion tokens on `reasoning_content` and returned NO content at all - so a 256-token battery would have read
# "never called a tool" for a model whose loop the T-187 fixture PASSED. The allowance is raised for the battery
# ONLY, and the driver below reports UNMEASURED when even this is consumed, because an instrument that blames the
# model for its own allowance is the BUG-375 shape one layer in (fix direction: the allowance belongs in a
# ratified knob, which is an owner act - config/agent_context.yaml#ratified.knobs holds per_turn_budget_s and no
# token allowance yet).
BATTERY_MAX_TOKENS = 1024

BATTERY_GEOMETRY = {
    "manifest": (2, 3, 4),                      # files the manifest NAMES -> expected 9
    "stale": (5, 6),                            # files it does NOT name -> the stale summary's 11
    "parallel": (6, 8),                         # two independent files -> expected 14
    "seed": 4,                                  # argname: seed.txt lines -> the record id r-4
    "column": ("a", "b", "a", "c", "b", "d"),   # 6 rows, 4 distinct: two DIFFERENT true numbers
}
ENUM_MODES = ["count", "distinct"]

COUNT_LINES_SPEC = {
    "type": "function",
    "function": {
        "name": "count_lines",
        "description": "Return the number of lines in one file of the fixture directory.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"]},
    },
}
READ_FILE_SPEC = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Return the first 200 characters of one file of the fixture directory.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"]},
    },
}
FETCH_FIELD_SPEC = {
    "type": "function",
    "function": {
        "name": "fetch_field",
        "description": "Return one field of one record. The record id is passed as record_id.",
        "parameters": {"type": "object", "properties": {"record_id": {"type": "string"}},
                       "required": ["record_id"]},
    },
}
FETCH_ROW_DECOY_SPEC = {
    "type": "function",
    "function": {
        "name": "fetch_row",
        "description": "Legacy row lookup by id. No rows are indexed in this fixture.",
        "parameters": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    },
}
SUMMARIZE_SPEC = {
    "type": "function",
    "function": {
        "name": "summarize_column",
        "description": "Summarise one column: mode 'count' returns the number of rows, mode 'distinct' "
                       "returns the number of distinct values.",
        "parameters": {"type": "object",
                       "properties": {"column": {"type": "string"},
                                      "mode": {"type": "string", "enum": ENUM_MODES}},
                       "required": ["column", "mode"]},
    },
}


def _written(path: pathlib.Path, lines: int) -> None:
    """Write one generated file of `lines` lines (the fixture's declared geometry, never an answer)."""
    path.write_text("".join(f"line {n}\n" for n in range(1, lines + 1)), encoding="utf-8")


def build_distractor(root: pathlib.Path) -> dict[str, Any]:
    """DISTRACTOR: a stale summary states a number that is TRUE of a different set of files. The manifest
    names the files that matter; the summary is a valid answer to the WRONG question, so a model that
    answers it has read the wrong thing - the failure mode a single-file fixture cannot produce."""
    root.mkdir(parents=True, exist_ok=True)
    named = [f"m{index}.txt" for index in range(len(BATTERY_GEOMETRY["manifest"]))]
    for index, lines in enumerate(BATTERY_GEOMETRY["manifest"]):
        _written(root / named[index], lines)
    stray = [f"s{index}.txt" for index in range(len(BATTERY_GEOMETRY["stale"]))]
    for index, lines in enumerate(BATTERY_GEOMETRY["stale"]):
        _written(root / stray[index], lines)
    (root / "manifest.txt").write_text("\n".join(named) + "\n", encoding="utf-8")
    expected, stale = sum(BATTERY_GEOMETRY["manifest"]), sum(BATTERY_GEOMETRY["stale"])
    (root / "report.txt").write_text(f"TOTAL LINES: {stale}\n(written before the last ingest; not re-run)\n",
                                     encoding="utf-8")
    return {"expected": expected, "stale": stale, "named": len(named)}


def build_parallel(root: pathlib.Path) -> dict[str, Any]:
    """PARALLEL-CALL FORMATTING: two INDEPENDENT reads that must arrive as two tool calls in ONE assistant
    message, each with its own id. A model that serialises them is not wrong about the answer - it is
    wrong about the format, which is what a serving stack has to parse."""
    root.mkdir(parents=True, exist_ok=True)
    left, right = BATTERY_GEOMETRY["parallel"]
    _written(root / "left.txt", left)
    _written(root / "right.txt", right)
    return {"expected": left + right, "paths": [str(root / "left.txt"), str(root / "right.txt")]}


def build_argname(root: pathlib.Path) -> dict[str, Any]:
    """ARGUMENT-NAME TRAP: the tool's id parameter is named `record_id`, while a DECOY tool takes `id`.
    The Flint failure (r14) was exactly this shape - a call that looks right and addresses nothing.
    ONE AXIS ONLY: the record key IS the line count, so the fixture cannot also be failed by an unguessable key
    format. MEASURED 2026-10-25 on the first run: with keys shaped `r-<n>` and a prompt that names no format, all
    eight models answered `unknown record id 4` - a trap that fails EVERYONE measures nothing, and the fix is to
    remove the second axis rather than to spell the format out."""
    root.mkdir(parents=True, exist_ok=True)
    seed = BATTERY_GEOMETRY["seed"]
    _written(root / "seed.txt", seed)
    records = {str(index): f"rec-{index}" for index in range(1, seed + 3)}
    (root / "records.json").write_text(json.dumps(records), encoding="utf-8")
    return {"expected": records[str(seed)], "param": "record_id", "records": records,
            "tool": "fetch_field"}


def build_enum(root: pathlib.Path) -> dict[str, Any]:
    """ENUM-ARGUMENT TRAP: the mode must be one of the DECLARED enum values, exactly. The column holds 6
    rows and 4 distinct values, so 'count' (6) is a TRUE number for the wrong question."""
    root.mkdir(parents=True, exist_ok=True)
    values = list(BATTERY_GEOMETRY["column"])
    (root / "column.json").write_text(json.dumps({"column": "grade", "values": values}), encoding="utf-8")
    return {"expected": len(set(values)), "rows": len(values), "enum": ENUM_MODES, "values": values,
            "mode": "distinct"}


def _exec_tool(name: str, args: Any, derived: dict[str, Any]) -> str:
    """Execute ONE declared tool against a generated fixture. A bad argument is a MEASURED failure, so it is
    returned to the model as an error payload the grader can NAME - never raised (C16: reported, not silent)."""
    if not isinstance(args, dict):
        return "error: arguments were not a JSON object"
    if name in ("count_lines", "read_file"):
        raw = str(args.get("path", ""))
        try:
            text = pathlib.Path(raw).read_text(encoding="utf-8")
        except (OSError, ValueError) as exc:
            return f"error: {type(exc).__name__} on {raw!r}"
        return str(len(text.splitlines())) if name == "count_lines" else text[:200]
    if name == "fetch_field":
        got = str(args.get(derived["param"], ""))
        return derived["records"].get(got, f"error: unknown record id {got!r}")
    if name == "fetch_row":
        return "error: no rows are indexed in this fixture - use fetch_field"
    if name == "summarize_column":
        mode = str(args.get("mode", ""))
        if mode not in derived["enum"]:
            return f"error: mode {mode!r} is not one of {derived['enum']} (exact, case-sensitive)"
        return str(len(derived["values"]) if mode == "count" else len(set(derived["values"])))
    return f"error: undeclared tool {name!r}"


def carries(answer: str, number: int) -> bool:
    r"""A number counts only as a WHOLE token: '19' and '9.0' do not carry '9', but a SENTENCE-FINAL '14.' does.
    MEASURED 2026-10-25 by a real model: the first pattern (`(?![\d.])`) refused the trailing full stop, so
    Qwen3-Coder's correct "The total number of lines in both files is 14." was graded as not carrying 14 - a
    FALSE NEGATIVE that would have been read as a formatting failure. The guard now refuses a following digit and
    a following DECIMAL point only. DECLARED LIMIT: a whole token inside a PATH would still count ('.../m9.txt'),
    so the generated names stay below the geometry that could spell an expected value."""
    return re.search(rf"(?<![\d.]){number}(?![\d])(?!\.\d)", answer) is not None


def turn_unmeasured(message: dict[str, Any], finish_reason: str) -> str:
    """PURE: did this turn spend its whole allowance without saying anything? A reasoning model that answers in
    `reasoning_content` returns an EMPTY content and no tool calls, and that is NOT a tool-calling verdict - it is
    an unmeasured model (reported, never graded: C16/BUG-375, a probe's limit is not a fact about its subject)."""
    if str(message.get("content") or "").strip():
        return ""
    if str(finish_reason or "") != "length":
        return ""
    return ("the turn spent its whole token allowance (finish_reason=length) and returned no content - the "
            "instrument cannot see this model at this allowance, so this is UNMEASURED, not a FAIL")


def _budget_gate(walls: list[float], budget: float) -> tuple[str, str]:
    """The shared tail of every battery verdict: a correct answer produced over the declared turn budget is
    still a failure, because the budget is what makes a loop usable inside a pipeline."""
    over = [round(wall, 1) for wall in walls if wall > budget]
    if over:
        return "FAIL", f"turn(s) over the declared budget {budget:g}s: {over}"
    return "PASS", ""


def grade_distractor(state: dict[str, Any], derived: dict[str, Any], budget: float) -> tuple[str, str]:
    """DISTRACTOR verdict: every named file must be counted, and the stale summary's number must not be the
    answer. Answering the stale number is a FAIL even though the number itself is TRUE of something."""
    counted = [name for name in state["ok"] if name == "count_lines"]
    if len(counted) < derived["named"]:
        return "FAIL", (f"count_lines SUCCEEDED {len(counted)}x of the {derived['named']} file(s) manifest.txt "
                        f"names (an error payload is not a measurement)")
    answer = state["answer"]
    if carries(answer, derived["stale"]) and not carries(answer, derived["expected"]):
        return "FAIL", (f"answered the STALE summary's {derived['stale']} - a TRUE number about the files "
                        f"manifest.txt does NOT name (a valid answer to the wrong question)")
    if not carries(answer, derived["expected"]):
        return "FAIL", f"final answer does not carry {derived['expected']}: {answer.strip()[:80]!r}"
    verdict, detail = _budget_gate(state["walls"], budget)
    if verdict == "FAIL":
        return verdict, detail
    return "PASS", (f"counted {len(counted)} manifest file(s), answer carries {derived['expected']}, "
                    f"slowest turn {max(state['walls']):.1f}s")


def grade_parallel(state: dict[str, Any], derived: dict[str, Any], budget: float) -> tuple[str, str]:
    """PARALLEL verdict: one assistant message must carry BOTH calls and every call its own id. A serialised
    loop is FAIL - the fixture asks for a parallel reply because a serving stack parses that shape."""
    if state["parallel_max"] < 2:
        return "FAIL", (f"no assistant message carried two tool calls (max {state['parallel_max']} in one "
                        f"message) - the fixture asks for ONE parallel reply, not two turns")
    ids = [call_id for call_id in state["ids"] if call_id]
    if len(set(ids)) != len(ids):
        return "FAIL", f"tool_call ids were {ids} - each result must be addressable by its OWN id"
    if not carries(state["answer"], derived["expected"]):
        return "FAIL", f"final answer does not carry {derived['expected']}: {state['answer'].strip()[:80]!r}"
    verdict, detail = _budget_gate(state["walls"], budget)
    if verdict == "FAIL":
        return verdict, detail
    return "PASS", (f"2 calls in ONE message, {len(ids)} distinct id(s), answer carries "
                    f"{derived['expected']}, slowest turn {max(state['walls']):.1f}s")


def grade_argname(state: dict[str, Any], derived: dict[str, Any], budget: float) -> tuple[str, str]:
    """ARGUMENT-NAME verdict: the declared tool must be called AND its declared parameter name used. A call
    that reaches the right tool with `id` instead of `record_id` is name-drift, not a near miss."""
    field_calls = [args for name, args in state["calls"] if name == derived["tool"]]
    if not field_calls:
        used = sorted({name for name, _ in state["calls"]})
        return "FAIL", (f"never called {derived['tool']} (called {used}) - the decoy tool is a valid shape "
                        f"and the wrong address")
    if not any(isinstance(args, dict) and derived["param"] in args for args in field_calls):
        shapes = [sorted(args) if isinstance(args, dict) else args for args in field_calls]
        return "FAIL", (f"{derived['tool']} argument NAMES {shapes} never used the declared "
                        f"{derived['param']!r} - a call that looks right and addresses nothing (R-14 Flint)")
    if derived["expected"] not in state["answer"]:
        return "FAIL", (f"final answer does not carry {derived['expected']}: "
                        f"{state['answer'].strip()[:80]!r}")
    verdict, detail = _budget_gate(state["walls"], budget)
    if verdict == "FAIL":
        return verdict, detail
    return "PASS", (f"{derived['tool']}.{derived['param']} used, answer carries {derived['expected']}, "
                    f"slowest turn {max(state['walls']):.1f}s")


def grade_enum(state: dict[str, Any], derived: dict[str, Any], budget: float) -> tuple[str, str]:
    """ENUM-ARGUMENT verdict: the mode must be the DECLARED enum value exactly, and the answer must be the
    distinct count - not the row count, which is a TRUE number for the other question."""
    modes = [args.get("mode") for name, args in state["calls"] if name == "summarize_column"
             and isinstance(args, dict)]
    if derived["mode"] not in modes:
        return "FAIL", (f"mode values attempted {modes} never the declared {derived['mode']!r} "
                        f"(enum {derived['enum']}, exact and case-sensitive)")
    answer = state["answer"]
    if carries(answer, derived["rows"]) and not carries(answer, derived["expected"]):
        return "FAIL", (f"answered the ROW count {derived['rows']} - true for mode 'count', which is not "
                        f"what was asked (distinct)")
    if not carries(answer, derived["expected"]):
        return "FAIL", f"final answer does not carry {derived['expected']}: {answer.strip()[:80]!r}"
    verdict, detail = _budget_gate(state["walls"], budget)
    if verdict == "FAIL":
        return verdict, detail
    return "PASS", (f"mode {derived['mode']!r}, answer carries {derived['expected']} distinct, "
                    f"slowest turn {max(state['walls']):.1f}s")


BATTERY_FIXTURES: list[dict[str, Any]] = [
    {"name": "distractor", "tools": [COUNT_LINES_SPEC, READ_FILE_SPEC], "build": build_distractor,
     "grade": grade_distractor,
     "why": "a valid answer to the WRONG question (a stale summary of files the manifest does not name)",
     "system": "You are a sub-agent. Use the tools; never guess a count. Some files in the directory are "
               "irrelevant to the question, and one of them states a total that is TRUE of the wrong set.",
     "prompt": lambda derived, root: (
         f"{root}/report.txt is a summary written BEFORE the last ingest, so its number is stale for this "
         f"question. Count the lines of exactly the files listed in {root}/manifest.txt, then answer with "
         f"that total as a single integer.")},
    {"name": "parallel", "tools": [COUNT_LINES_SPEC], "build": build_parallel, "grade": grade_parallel,
     "why": "parallel-call FORMATTING: two independent reads must be two tool calls in ONE assistant message",
     "system": "You are a sub-agent. You MUST use the provided tool; never guess a count.",
     "prompt": lambda derived, root: (
         f"Call count_lines for {derived['paths'][0]} AND for {derived['paths'][1]} in the SAME assistant "
         f"message - two tool calls in one reply, not one call per turn. Then answer with their total as a "
         f"single integer.")},
    {"name": "argname", "tools": [FETCH_FIELD_SPEC, FETCH_ROW_DECOY_SPEC, COUNT_LINES_SPEC],
     "build": build_argname, "grade": grade_argname,
     "why": "argument-NAME trap: the id parameter is `record_id` while a decoy tool takes `id` (R-14's shape)",
     "system": "You are a sub-agent. Use the tools; never guess a value. Call the tool whose declaration "
               "matches the value you need, and use the parameter names the declaration gives.",
     "prompt": lambda derived, root: (
         f"How many lines does {root}/seed.txt have? Use that count as the record id, call fetch_field "
         f"(NOT fetch_row), and answer with the field value it returns, as a single word.")},
    {"name": "enum", "tools": [SUMMARIZE_SPEC], "build": build_enum, "grade": grade_enum,
     "why": "ENUM-argument trap: mode must be the declared enum value, and 'count' gives a TRUE wrong answer",
     "system": "You are a sub-agent. Use the tools; never guess a value. The tool declares which values an "
               "argument accepts - use one of them exactly.",
     "prompt": lambda derived, root: (
         f"Using {root}/column.json, report how many DISTINCT values the column holds. Answer with that "
         f"number only.")},
]


def run_battery_fixture(decl: dict[str, Any], model: str, budget: float, fixture: dict[str, Any],
                        workdir: pathlib.Path) -> dict[str, Any]:
    """Drive ONE battery fixture against ONE model and return its receipt row. The loop is written once for
    all four fixtures: the fixture supplies the tools, the prompt and the PURE grader, so a new failure class
    is a spec, not a fifth copy of this loop."""
    url = str(decl["base_url"]).rstrip("/") + "/chat/completions"
    key = str((decl.get("headers") or {}).get("Authorization", ""))
    derived = fixture["build"](workdir)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": fixture["system"]},
        {"role": "user", "content": fixture["prompt"](derived, workdir)},
    ]
    state: dict[str, Any] = {"calls": [], "ids": [], "ok": [], "parallel_max": 0, "answer": "",
                             "walls": [], "unmeasured": ""}
    error, transport = "", ""
    for _ in range(MAX_TURNS):
        try:
            reply, wall, _usage = ask(url, key, model, messages, BATTERY_MAX_TOKENS, tools=fixture["tools"])
        except TimeoutError as exc:
            error = f"{type(exc).__name__}: {exc}"
            break
        except (urllib.error.URLError, OSError, ValueError) as exc:
            transport = f"{type(exc).__name__}: {exc}"
            break
        state["walls"].append(wall)
        choices = reply.get("choices") or []
        if not choices:
            error = f"engine returned no choice: {str(reply)[:120]}"
            break
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            state["answer"] = str(message.get("content") or "")
            state["unmeasured"] = turn_unmeasured(message, choices[0].get("finish_reason", ""))
            break
        state["parallel_max"] = max(state["parallel_max"], len(tool_calls))
        messages.append(message)
        for call in tool_calls:
            function = call.get("function", {})
            name = function.get("name", "")
            try:
                args = json.loads(function.get("arguments") or "{}")
            except ValueError:
                args = {}
            payload = _exec_tool(name, args, derived)
            state["calls"].append((name, args))
            state["ids"].append(str(call.get("id") or ""))
            if not payload.startswith("error:"):
                state["ok"].append(name)
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": payload})
    if error:
        verdict, detail = "FAIL", error
    elif transport:
        verdict, detail = "UNMEASURED", (f"the ENGINE refused the turn ({transport}) - a transport failure is "
                                         f"not a fact about the model, so this row is not a verdict")
    elif state["unmeasured"]:
        verdict, detail = "UNMEASURED", state["unmeasured"]
    else:
        verdict, detail = fixture["grade"](state, derived, budget)
    return {"model": model, "fixture": fixture["name"], "why": fixture["why"], "verdict": verdict,
            "detail": detail, "tools_called": [name for name, _ in state["calls"]],
            "turn_calls": state["parallel_max"], "turns": len(state["walls"]),
            "slowest_turn_s": round(max(state["walls"]), 1) if state["walls"] else None,
            "answer": state["answer"].strip()[:200]}


def rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The RANKING a battery exists for (T-199): fixtures passed first, then the WARM turn, then the model NAME
    as a stable tie-break so two identical receipts cannot print in two orders.

    WHY WARM AND NOT THE SLOWEST TURN. MEASURED 2026-10-25 on this battery's own first receipt: the first fixture
    of a model pays the ENGINE LOAD (MiniCPM5-2B: 33.5 s on fixture 1, 1.0-1.5 s on the rest), so a ranking on the
    raw slowest turn put Ornith-9B (28.6 s) above MiniCPM5 (33.5 s) while MiniCPM5 is ten times faster once warm.
    A load is a property of the engine's pool, not of the model's loop, so it is REPORTED separately and never
    ranked on. The first fixture's slowest turn is recorded as `load_paid_s`."""
    models = sorted({row["model"] for row in rows})
    table = []
    for model in models:
        mine = [row for row in rows if row["model"] == model]
        after_first = mine[1:] or mine
        table.append({"model": model,
                      "passed": sum(1 for row in mine if row["verdict"] == "PASS"),
                      "of": len(mine),
                      "failed": [row["fixture"] for row in mine if row["verdict"] == "FAIL"],
                      "unmeasured": [row["fixture"] for row in mine if row["verdict"] == "UNMEASURED"],
                      "warm_turn_s": max((row["slowest_turn_s"] or 0.0) for row in after_first),
                      "load_paid_s": mine[0]["slowest_turn_s"]})
    table.sort(key=lambda item: (-item["passed"], item["warm_turn_s"], item["model"]))
    return table


def selftest() -> int:
    """Known-answer controls on the PURE grader - no model is called (a control that needs a model is a bill)."""
    bad = []
    cases = [((0, "12", 12, [1.0], 60.0), "FAIL", "the right answer with NO tool call must FAIL"),
             ((3, "12", 12, [1.0], 60.0), "PASS", "3 calls + the right answer inside budget must PASS"),
             ((3, "11", 12, [1.0], 60.0), "FAIL", "3 calls + the wrong answer must FAIL"),
             ((3, "12", 12, [90.0], 60.0), "FAIL", "a turn over the declared budget must FAIL"),
             ((2, "12", 12, [1.0], 60.0), "FAIL", "too few tool calls must FAIL")]
    for args, want, label in cases:
        got = grade(*args)[0]
        if got != want:
            bad.append(f"{label}: got {got}")
    if make_fixture(pathlib.Path("temp/_subagent_loop_fixture_selftest"))[1] != sum(FIXTURE_LINES):
        bad.append("the generated fixture does not total its own lines")
    ts_cases = [((1, 1, ["7"], "token-7", "token-7", "7", [1.0], 60.0), "PASS", "read + keyed lookup + right answer must PASS"),
                ((1, 1, ["3"], "token-3", "token-7", "7", [1.0], 60.0), "FAIL", "the distractor key (decoy) must FAIL"),
                ((0, 1, ["7"], "token-7", "token-7", "7", [1.0], 60.0), "FAIL", "no read_lines (step 1) must FAIL"),
                ((1, 0, [], "token-7", "token-7", "7", [1.0], 60.0), "FAIL", "no lookup_token (step 2) must FAIL"),
                ((1, 1, ["7"], "token-9", "token-7", "7", [1.0], 60.0), "FAIL", "the wrong token value must FAIL"),
                ((1, 1, ["7"], "token-7", "token-7", "7", [90.0], 60.0), "FAIL", "a turn over budget must FAIL")]
    for args, want, label in ts_cases:
        got = grade_two_step(*args)[0]
        if got != want:
            bad.append(f"{label}: got {got}")
    fixture = make_two_step_fixture(pathlib.Path("temp/_subagent_loop_two_step_selftest"))
    if fixture[1:] != ("7", "token-7"):
        bad.append(f"the two-step fixture derives the wrong expected pair: {fixture[1:]}")

    # ── T-199 battery controls: the fixture GEOMETRY is re-derived, then each PURE grader is asked both ways.
    def state_of(calls: list[tuple[str, Any]], answer: str, parallel_max: int = 1,
                 walls: tuple[float, ...] = (1.0,), ok: list[str] | None = None) -> dict[str, Any]:
        """One synthetic loop state, so a grader can be asked without a model (the bill this avoids)."""
        return {"calls": calls, "ids": [f"call-{index}" for index in range(len(calls))],
                "ok": [name for name, _ in calls] if ok is None else ok,
                "parallel_max": parallel_max, "answer": answer, "walls": list(walls)}

    base = pathlib.Path("temp/_subagent_loop_battery_selftest")
    d_derived = build_distractor(base / "distractor")
    p_derived = build_parallel(base / "parallel")
    a_derived = build_argname(base / "argname")
    e_derived = build_enum(base / "enum")
    if d_derived["expected"] != sum(BATTERY_GEOMETRY["manifest"]) or d_derived["stale"] != sum(
            BATTERY_GEOMETRY["stale"]):
        bad.append(f"the distractor derives the wrong pair: {d_derived['expected']}/{d_derived['stale']}")
    if p_derived["expected"] != sum(BATTERY_GEOMETRY["parallel"]):
        bad.append(f"the parallel fixture derives the wrong total: {p_derived['expected']}")
    if a_derived["expected"] != f"rec-{BATTERY_GEOMETRY['seed']}":
        bad.append(f"the argname fixture derives the wrong record: {a_derived['expected']}")
    if e_derived["expected"] == e_derived["rows"]:
        bad.append("the enum fixture's distinct count equals its row count - the trap needs two DIFFERENT numbers")

    counted = [("count_lines", {"path": "x"})] * d_derived["named"]
    seed_key = str(BATTERY_GEOMETRY["seed"])
    battery_cases = [
        (grade_distractor, state_of(counted, str(d_derived["expected"])), d_derived, "PASS",
         "counting every named file and answering the manifest total must PASS"),
        (grade_distractor, state_of(counted, str(d_derived["stale"])), d_derived, "FAIL",
         "the stale summary's number must FAIL even though it is TRUE of the files the manifest omits"),
        (grade_distractor, state_of(counted[:1], str(d_derived["expected"])), d_derived, "FAIL",
         "one counted file out of three must FAIL"),
        (grade_distractor, state_of(counted, f"1{d_derived['expected']}"), d_derived, "FAIL",
         "a number that merely CONTAINS the expected digits must not count as carrying it"),
        (grade_distractor, state_of(counted, str(d_derived["expected"]), walls=(90.0,)), d_derived, "FAIL",
         "a right answer over the declared turn budget must FAIL"),
        (grade_parallel, state_of([("count_lines", {}), ("count_lines", {})], str(p_derived["expected"]),
                                  parallel_max=2), p_derived, "PASS",
         "two calls in ONE message with distinct ids and the right total must PASS"),
        (grade_parallel, state_of([("count_lines", {}), ("count_lines", {})], str(p_derived["expected"])),
         p_derived, "FAIL", "a SERIALISED pair (one call per message) must FAIL the formatting fixture"),
        (grade_enum, state_of([("summarize_column", {"column": "grade", "mode": e_derived["mode"]})],
                              str(e_derived["expected"])), e_derived, "PASS",
         "the declared enum value with the distinct count must PASS"),
        (grade_enum, state_of([("summarize_column", {"column": "grade", "mode": "count"})],
                              str(e_derived["rows"])), e_derived, "FAIL",
         "the ROW count under mode 'count' must FAIL - a true number for the wrong question"),
        (grade_enum, state_of([("summarize_column", {"column": "grade", "mode": "DISTINCT"})],
                              str(e_derived["expected"])), e_derived, "FAIL",
         "an enum value in the wrong CASE must FAIL (the declaration is exact)"),
        (grade_argname, state_of([("fetch_field", {a_derived["param"]: seed_key})], a_derived["expected"]),
         a_derived, "PASS", "the declared parameter name with the derived record must PASS"),
        (grade_argname, state_of([("fetch_field", {"id": seed_key})], a_derived["expected"]), a_derived, "FAIL",
         "the familiar name 'id' instead of the declared 'record_id' must FAIL (name-drift, R-14)"),
        (grade_argname, state_of([("fetch_row", {"id": seed_key})], a_derived["expected"]), a_derived, "FAIL",
         "calling the DECOY tool must FAIL even with the right value"),
        (grade_argname, state_of([("fetch_field", {a_derived["param"]: seed_key})], "rec-999"), a_derived,
         "FAIL", "the right call with the wrong answer value must FAIL"),
        (grade_distractor, state_of(counted, str(d_derived["expected"]), ok=[]), d_derived, "FAIL",
         "three count_lines ATTEMPTS that all returned an error payload must FAIL (an error is not a reading)"),
    ]
    duplicate_ids = state_of([("count_lines", {}), ("count_lines", {})], str(p_derived["expected"]),
                             parallel_max=2)
    duplicate_ids["ids"] = ["same", "same"]
    battery_cases.append((grade_parallel, duplicate_ids, p_derived, "FAIL",
                          "two tool calls sharing ONE id must FAIL - a result must be addressable"))
    for grader, state, derived, want, label in battery_cases:
        got = grader(state, derived, budget=60.0)[0]
        if got != want:
            bad.append(f"{label}: got {got}")

    if not carries("The total number of lines in both files is 14.", 14):
        bad.append("a SENTENCE-FINAL '14.' must carry 14 (measured false negative on Qwen3-Coder)")
    if carries("The value is 9.0 units", 9):
        bad.append("a DECIMAL '9.0' must not carry 9")
    if carries("there are 19 files", 9):
        bad.append("'19' must not carry 9 (a number inside a number)")
    if turn_unmeasured({"content": ""}, "length") == "":
        bad.append("an EMPTY content with finish_reason=length must read UNMEASURED, not measured")
    if turn_unmeasured({"content": "the token is token-7"}, "length") != "":
        bad.append("a turn that DID answer must not read UNMEASURED (two-sidedness)")
    if turn_unmeasured({"content": ""}, "stop") != "":
        bad.append("an empty content with finish_reason=stop is a real non-answer, never UNMEASURED")
    for problem in bad:
        print(f"  FAIL control: {problem}")
    total = len(cases) + 1 + len(ts_cases) + 1 + len(battery_cases) + 4 + 6
    print(f"{'OK' if not bad else 'FAILED'} subagent-loop controls: {total - len(bad)}/{total} known-answer")
    return 1 if bad else 0


def main() -> int:
    """Measure every served model (or one), print the table, write the receipt."""
    parser = argparse.ArgumentParser(description="D-2549 per-model sub-agent loop measurement")
    parser.add_argument("--only", default="")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--two-step", action="store_true",
                        help="run the T-187 two-step / two-tool / distractor / dependent-steps fixture")
    parser.add_argument("--battery", action="store_true",
                        help="T-199: run the FOUR-fixture battery and RANK the served roster")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    decl = declaration()
    budget = budget_s()
    served = [m["name"] for m in decl["models"]]
    models = [args.only] if args.only else served
    unknown = [m for m in models if m not in served]
    if unknown:
        raise SystemExit(f"FATAL: {unknown} is not DECLARED to the harness (the parity rail's job, BUG-874)")
    if args.battery:
        out = pathlib.Path(args.out or f"temp/subagent_loop_battery_receipt_{time.strftime('%Y%m%d')}.json")
        rows: list[dict[str, Any]] = []

        def flush(reason: str) -> None:
            """The receipt is rewritten after EVERY model: a run that dies at model 6 must still leave the five
            it measured (D-3036/BUG-844 - an act that leaves no trace did not happen)."""
            out.write_text(json.dumps(
                {"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "fixture": "T-199 loop battery",
                 "state": reason, "per_turn_budget_s": budget, "served": served,
                 "fixtures": [{"name": f["name"], "why": f["why"]} for f in BATTERY_FIXTURES],
                 "rows": rows, "ranking": rank(rows)}, indent=2) + "\n", encoding="utf-8")

        print(f"T-199 battery | per-turn budget {budget:g}s | served {len(served)} | "
              f"measured {len(models)} model(s) x {len(BATTERY_FIXTURES)} fixtures")
        for fixture in BATTERY_FIXTURES:
            print(f"  fixture {fixture['name']:11} {fixture['why']}")
        for model in models:
            for fixture in BATTERY_FIXTURES:
                rows.append(run_battery_fixture(decl, model, budget, fixture,
                                                pathlib.Path("temp/_subagent_loop_battery") / fixture["name"]))
            mine = [row for row in rows if row["model"] == model]
            passed = sum(1 for row in mine if row["verdict"] == "PASS")
            print(f"  {model:38} {passed}/{len(mine)}  "
                  + " ".join(f"{row['fixture']}={row['verdict']}" for row in mine))
            for row in mine:
                if row["verdict"] != "PASS":
                    print(f"      {row['fixture']:11} {row['detail']}")
            flush("running")
        flush("complete")
        print("RANKED (a battery RANKS a model; one fixture only ADMITS one) - fixtures passed, then "
              "slowest turn:")
        for position, item in enumerate(rank(rows), 1):
            failed = f" failed={item['failed']}" if item["failed"] else ""
            unmeasured = f" UNMEASURED={item['unmeasured']}" if item["unmeasured"] else ""
            print(f"  {position}. {item['model']:38} {item['passed']}/{item['of']}"
                  f" warm={item['warm_turn_s']}s load={item['load_paid_s']}s{failed}{unmeasured}")
        print(f"receipt {out}")
        return 0 if all(row["verdict"] == "PASS" for row in rows) else 2
    if args.two_step:
        rows = [run_two_step_model(decl, model, budget, pathlib.Path("temp/_subagent_loop_two_step_fixture"))
                for model in models]
        print(f"T-187 two-step | per-turn budget {budget:g}s | served {len(served)} | measured {len(rows)}")
        for row in rows:
            print(f"  {row['verdict']:4} {row['model']:38} read={row['calls_read']} "
                  f"lookup={row['calls_lookup']} slowest={row['slowest_turn_s']}s  {row['detail']}")
        passed = sum(1 for r in rows if r["verdict"] == "PASS")
        out = pathlib.Path(args.out or f"temp/subagent_loop_two_step_receipt_{time.strftime('%Y%m%d')}.json")
        out.write_text(json.dumps({"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "fixture": "T-187 two-step",
                                   "per_turn_budget_s": budget, "served": served, "rows": rows}, indent=2) + "\n",
                       encoding="utf-8")
        print(f"{passed}/{len(rows)} PASS | receipt {out}")
        return 0 if passed == len(rows) else 2
    rows = [run_model(decl, model, budget, pathlib.Path("temp/_subagent_loop_fixture")) for model in models]
    print(f"per-turn budget {budget:g}s | served {len(served)} | measured {len(rows)}")
    for row in rows:
        print(f"  {row['verdict']:4} {row['model']:38} calls={row['tool_calls']} slowest={row['slowest_turn_s']}s  {row['detail']}")
    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    out = pathlib.Path(args.out or f"temp/subagent_loop_receipt_{time.strftime('%Y%m%d')}.json")
    out.write_text(json.dumps({"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                               "per_turn_budget_s": budget, "served": served, "rows": rows}, indent=2) + "\n",
                   encoding="utf-8")
    print(f"{passed}/{len(rows)} PASS | receipt {out}")
    return 0 if passed == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
