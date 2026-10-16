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


def ask(url: str, key: str, model: str, messages: list[dict[str, Any]], max_tokens: int) -> tuple[dict, float]:
    """ONE chat completion with the tool declared. Returns (reply, wall_seconds). temperature 0.0 (R7)."""
    body = json.dumps({"model": model, "messages": messages, "tools": [TOOL],
                       "temperature": 0.0, "max_tokens": max_tokens, "stream": False}).encode()
    request = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": key})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=180) as response:
        reply = json.loads(response.read())
    return reply, time.monotonic() - started


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
            reply, wall = ask(url, key, model, messages, 256)
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
    for problem in bad:
        print(f"  FAIL control: {problem}")
    print(f"{'OK' if not bad else 'FAILED'} subagent-loop controls: {len(cases) + 1 - len(bad)}/"
          f"{len(cases) + 1} known-answer")
    return 1 if bad else 0


def main() -> int:
    """Measure every served model (or one), print the table, write the receipt."""
    parser = argparse.ArgumentParser(description="D-2549 per-model sub-agent loop measurement")
    parser.add_argument("--only", default="")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", default="")
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
