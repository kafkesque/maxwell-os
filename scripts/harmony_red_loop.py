#!/usr/bin/env python3
"""harmony_red_loop.py - T-213/BUG-951: THE RED LOOP THE BUG OWED, and the reason its verdict is not a tick.

WHY THIS EXISTS (measured, not asserted). BUG-951 (HIGH, OPEN 2026-10-20) records two symptoms of ONE cause: a
tool NAME arriving with a harmony channel marker glued into it (`"name":"shell<|channel|>commentary"`, 6 of ~30
calls), and FOUR CONSECUTIVE DROPPED CALLS that never reached the harness (engine log: `Error parsing tool calls
from tokens: unexpected tokens remaining in message header`). It was never reproduced in isolation, and the only
probe that ever looked lived in `/tmp` and is gone - so the claim could not be re-tested by anyone (BUG-406's
sweep class, and D-3036's rule that no theory may be formed before an instrument can go RED on the defect).

WHAT THIS INSTRUMENT IS, AND WHAT IT IS NOT. It is NOT a capability battery: it does not rank models, and its
verdicts are RED / UNMEASURED_WITH_BOUND / UNMEASURED - there is no PASS, because "no defect observed" in 30
calls is a BOUND (rule of three: <= 1 in 10) and a defect observed at 1 in 5 in production cannot be retired by
it. A green tick from a fixture that cannot fail is the BUG-797 class.

TWO AXES AND THEIR CONTROL, ONE PER RUN (a run that changed two conditions would not know which one moved the
result):
  --mode replay    THE GATE'S OWN AXIS (T-213 clause 1): ONE corrupted `read_index<|channel|><tail>` exchange is
                   SEEDED into the history before the first real call, then N real calls are issued. The bug's
                   own candidate trigger is "a prior corrupted name echoed back in history"; seeding it up front
                   gives every one of the N calls maximum exposure instead of a mid-run change of conditions.
  --mode clean     THE CONTROL AND THE POINT OF THE PAIR: the same channel, the same tool, the same N, with the
                   seeded exchange REMOVED. Replay alone cannot say whether the model corrupted its names because
                   the transcript taught it or because it does that on its own; the two runs differ by exactly two
                   messages, so the difference is the attribution (the build_argname lesson: a trap that fails
                   EVERYONE measures nothing).
  --mode parallel  THE AXIS THAT ACTUALLY REPRODUCED (2026-10-27, this machine): a turn that must emit TWO tool
                   calls in ONE assistant message is where gpt-oss-20b degenerates into `to=<name>` plus garbage
                   and the parser refuses the header. Declared as a third axis because a fixture that tests
                   only the unproven trigger would report clean on the proven one, and because the two SYMPTOMS
                   of BUG-951 do not co-occur: replay produces corrupted NAMES, parallel produces PARSER DROPS.
  --mode blank-echo  THE ATTRIBUTION SPLIT OF THE SEEDED PAIR (T-215 limb 1, 2026-10-27). `replay` seeds TWO
                   things at once - the corrupted assistant `tool_call` AND the harness's
                   `error: tool '<corrupted>' does not exist` echo - so a copy rate of 14-in-30 says the PAIR
                   teaches, and production cannot fix a pair it cannot name. This axis holds the seeded
                   assistant turn BYTE-IDENTICAL and changes exactly ONE string: the echoed error carries no
                   name (`error: tool not found`). The tool message still EXISTS, so the transcript stays legal
                   and a transport refusal cannot masquerade as a reading; and the same name-free echo is used
                   for every DEFECT the loop itself provokes, so the axis tests the mitigation for the whole
                   run rather than only at the seed. Outcome decides WHICH mitigation is entitled to be built:
                   copy rate COLLAPSES -> the verbatim name in the echo is the teaching event, so the harness
                   must stop quoting raw names back (no model change, no retry); copy rate HOLDS -> the
                   assistant turn alone suffices, and sanitising the echo buys nothing, so the fix belongs at
                   emission/retry instead (T-215 limb 2).

THE THREE COUNTERS (counted SEPARATELY, never summed into one number):
  malformed_names  a tool call ARRIVED, but its `function.name` is not a declared tool - either harmony-
                   contaminated (a special token leaked into an identifier field) or merely undeclared.
  dropped_calls    a call was OWED (the previous tool payload named the next index) and NOTHING arrived.
  engine_parse_errors  the ENGINE's own log said it refused a tool header in that turn's byte window. This is the
                   witness the API response cannot provide, and it is why a drop is never inferred: a turn with
                   empty content and finish_reason=length is what a LOST CALL and a SPENT ALLOWANCE BOTH look like
                   from outside, and only the log separates them (it separates them here because the battery read
                   exactly that shape as "the instrument cannot see this model" on 2026-10-27 16:10 and 16:12).

ATTRIBUTION GUARD (BUG-950 mechanism A). An engine eviction in a turn's window is a SECOND, sufficient cause for
a dropped call (two resident models thrash, the engine deep-resets, the stream dies). When a drop coincides with
an eviction the verdict is UNMEASURED, never RED: the instrument must not charge the model for the pool. A
malformed NAME is exempt from that guard - a leaked special token in an identifier cannot be produced by an
eviction.

NO VALUE LIVES HERE (C12). The served set, base_url and key come from the harness's own declaration; the turn
budget from ratified.knobs.per_turn_budget_s; the engine identity, the log path and every log marker from
config/engine.yaml; the SUBJECT from the role the bug damages (config/model_assignments.yaml#harness_roles.
AGENT_LOOP_SHORT.model - a fixture whose subject is typed here would drift the moment a role is reassigned).
The fixture's geometry (N, the three observed channel tails, the markers) is declared below and cited.

Usage:
  python3 scripts/harmony_red_loop.py --selftest                 # known-answer controls; NO model is called
  python3 scripts/harmony_red_loop.py --calls 3 --mode replay    # smoke: does the engine carry a corrupted name?
  python3 scripts/harmony_red_loop.py --mode replay              # the gate: N=30, the bug's subject
  python3 scripts/harmony_red_loop.py --mode clean               # the control for that same run
  python3 scripts/harmony_red_loop.py --mode parallel --only MODEL
Exit: 0 UNMEASURED_WITH_BOUND (a bound, never "fixed") | 2 RED (the defect fired) | 1 UNMEASURED (the
      instrument could not see: transport refusal, spent allowance, eviction-contaminated drop, or N below 30).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# REUSE, NEVER COPY (C19/the drift class): the HTTP call, the declaration reader, the budget and the engine
# identity already exist in the loop instrument, and a second copy of any of them is how two receipts start
# disagreeing about one machine. `_yaml` is imported with its underscore because it IS this repo's one loader.
from measure_subagent_loop import (  # noqa: E402  (path is set above, deliberately)
    BATTERY_MAX_TOKENS,
    _yaml,
    ask,
    budget_s,
    classify_turn,
    declaration,
    engine_block,
    engine_facts,
    log_offset,
    log_since,
    window,
)

ENGINE = ROOT / "config/engine.yaml"
ASSIGNMENTS = ROOT / "config/model_assignments.yaml"

# ── THE FIXTURE'S GEOMETRY (declared, cited, never guessed) ─────────────────────────────────────────────
MIN_BOUND_CALLS = 30
# T-213's gate: "N >= 30 real tool calls". Below 30 a clean run is not a bound (rule of three needs the N to
# state the rate), so a short run can never return UNMEASURED_WITH_BOUND - the gate is enforced in code.
RULE_OF_THREE = 3.0
# 0 events in n trials bounds the rate at <= 3/n with 95% confidence. Stated as "1 in n/3".
DROP_CEILING = 3
# A run that has already dropped this many calls is RED and cannot become anything else, so continuing to spend
# 25 s per degenerate turn buys no knowledge. Declared here, reported in the receipt as the stop reason.
TURN_HEADROOM = 2
# Turns allowed BEYOND the call target and the drop ceiling before the loop is declared stuck: a drop costs one
# turn and earns one nudge, and a model that answers nothing more than this many times is not being measured.
# (R5 review 2026-10-27: this was a bare `+ 2` in the loop condition - the one real C20 finding of that pass.)
TOOL_NAME = "read_index"
RETRY_CEILING = 2
# T-215 limb 2: how many times ONE owed call may be re-issued after the engine's own parser ate it. Two, because
# a loss is ~1 in 5 and two consecutive losses is ~1 in 25: a third retry buys almost nothing and would let a
# guard paper over a model that cannot emit the header at all. Counted PER OWED CALL (the streak resets the
# moment a call arrives), so the bound is on the repair, never on the run.
RETRY_BUDGET = 12
# The total retries a run may spend. At the measured ~1-in-5 loss over 30 calls the expectation is <= 6, so 12 is
# two-fold headroom: a run that needs more is not being measured by this guard, it is being rescued by it, and
# the receipt must say so rather than quietly keep going.
RETRY_NUDGE = ("Your previous tool call did not arrive - it was lost, not declined. Re-issue the call for the next "
               "index with {tool}; do not answer in words.")
# The re-issue's BODY, and it is load-bearing rather than polite: at temperature=0.0 an identical prompt is an
# identical replay, so a retry that repeats the request byte-for-byte recovers NOTHING (measured 2026-10-27: 0 of 6
# re-issues recovered 0 of 3 lost calls for 100.9 s). The nudge is the smallest prompt change that can change the
# generation, and it NAMES the failure so the model does not have to re-derive it - the blank-echo axis showed what
# an error carrying no name costs.
CORRUPT_TAILS = ("commentary", "json", "analysis")
# BUG-951 measured these three tails glued onto REAL tool names: `shell<|channel|>commentary`,
# `shell<|channel|>json`, `tree<|channel|>analysis`. One tail per run (--replay-tail) so the run has ONE axis.
HARMONY_MARKERS = ("<|channel|>", "<|start|>", "<|message|>", "<|constrain|>", "<|end|>", "<|return|>")
# Any of these inside a `function.name` means a SPECIAL TOKEN leaked into an identifier field. The tuple is the
# harmony vocabulary seen in the bug's own log lines, not a general tokenizer list.
REPLAY_ID = "replay-corrupt-1"
ECHO_QUOTED = "quoted"
ECHO_BLANK = "blank"
# WHICH ERROR THE HARNESS RETURNS FOR AN UNKNOWN TOOL (T-215 limb 1). `quoted` is what production does today and
# what `replay` has always seeded: `error: tool 'read_index<|channel|>commentary' does not exist` - the corrupted
# identifier, repeated back, in the position the model conditions on next. `blank` is the SAME message with the
# name removed: same role, same count, same position, one string fewer. Declared as a closed vocabulary because a
# free-form echo would make the axis unreproducible, and a THIRD spelling would be a different experiment.
ECHO_BLANK_TEXT = "error: tool not found"

RECEIPT_SCHEMA_VERSION = "1.0"


def script_digest() -> str:
    """sha256 (truncated) of THIS file: the receipt's own build identity (R14). A verdict is a statement about a
    build, and a receipt that cannot name the code that produced it cannot be compared with a later one."""
    return hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]


READ_INDEX_SPEC = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Register one index of the run. Returns the next index to register.",
        "parameters": {"type": "object", "properties": {"index": {"type": "string"}},
                       "required": ["index"]},
    },
}


# ── THE ENGINE'S OWN WITNESS now lives in the BASE instrument (BUG-1079, 2026-10-27) ─────────────────
# engine_facts / log_offset / log_since / window / classify_turn are IMPORTED from measure_subagent_loop and
# never copied: the T-199 battery had to read the same log window under the same attribution rule, and two copies
# of "what the engine said" is exactly how two receipts start disagreeing about one machine. D-3200 clause 2
# required the helper to be SHARED when BUG-1079 was fixed - this is that fix. The import direction is unchanged
# (this file already imported the base instrument), so there is no cycle: measure_subagent_loop knows nothing
# about this gate.


# ── THE PURE CLASSIFIERS (the only place a verdict is decided; --selftest asks each one both ways) ──────
def classify_name(name: str, declared: set[str]) -> str:
    """PURE: '' for a declared tool name, else the DEFECT CLASS. Two classes because they are different faults:
    'harmony_contaminated' means a special token leaked into an identifier (BUG-951 symptom 1, and the engine
    cannot be blamed on the model's behalf); 'undeclared' means a clean name that no declaration backs (the
    R-14 Flint shape). Both are malformed for the counter, and the receipt keeps the breakdown."""
    if any(marker in name for marker in HARMONY_MARKERS):
        return "harmony_contaminated"
    if name not in declared:
        return "undeclared"
    return ""


def exec_read_index(args: Any, total: int) -> str:
    """Execute the fixture's ONE tool. A bad argument is returned to the model as an error payload (a measured
    failure the grader can NAME), never raised (C16)."""
    if not isinstance(args, dict):
        return "error: arguments were not a JSON object"
    raw = str(args.get("index", "")).strip()
    if not raw.isdigit():
        return f"error: index {raw!r} is not a number"
    index = int(raw)
    if index < 1 or index > total:
        return f"error: index {index} is outside 1..{total}"
    if index >= total:
        return f"registered {index} of {total}. That was the LAST index. Answer with the single word FINISHED."
    return f"registered {index} of {total}. NEXT: call {TOOL_NAME} with index={index + 1}."


def may_retry(kind: str, streak: int, guard_on: bool, retries_used: int) -> bool:
    """PURE: T-215 limb 2's guard decision - may THIS turn be re-issued?

    Only a LOST CALL is retryable, and only a lost call is attributable: `engine_parse_error` means the engine's own
    log refused the header inside this turn's byte window, i.e. the model emitted a call and the parser ate it
    (BUG-1079's attribution, and the reason the guard is not a guess). Everything else is REFUSED, deliberately:
      allowance    the model spent the allowance the ROLE grants - retrying re-buys the same wall, and calling that
                   a lost call is exactly the misattribution BUG-1079 fixed one layer up;
      silent_stop / answered   the model did not emit a call and the engine did not eat one: that is a DECLINED
                   call, and a guard that retried it would inflate the call count with calls the model never made.
    Both ceilings are checked here so the bound cannot be forgotten at the call site, and `guard_on` is a parameter
    rather than a global so the same function answers both sides of the control."""
    if not guard_on or kind != "engine_parse_error":
        return False
    return streak < RETRY_CEILING and retries_used < RETRY_BUDGET


def verdict(state: dict[str, Any], target: int) -> tuple[str, str]:
    """PURE: the three-verdict rule from T-213's gate, plus the attribution guard. No PASS exists here.

    RED                a malformed name arrived, a call was dropped with no eviction in the window, or the
                       engine's parser refused a header in the window (the symptom without the loss).
    UNMEASURED         the instrument could not see: a transport refusal, a spent allowance, N below the gate's
                       30, or a drop that coincides with an engine eviction (BUG-950 mechanism A is a second,
                       sufficient cause - the pool must not be charged to the model). Only reachable when
                       NOTHING was observed: a malformed name is read off the response body and outranks it.
    UNMEASURED_WITH_BOUND  both counts zero over >= 30 calls: the rate is bounded at <= 1 in target/3, which does
                       NOT retire a defect seen at 1 in 5, so it may never be reported as "fixed".
    """
    malformed = len(state["contaminated"]) + len(state["undeclared"])
    drops = state["drops"]
    # A MALFORMED NAME OUTRANKS AN UNMEASURED RUN (T-215 limb 1, 2026-10-27 - found by its own first receipt).
    # A malformed name is read off the RESPONSE BODY, so no attribution question can touch it: it does not depend
    # on the engine log, on an eviction, or on a foreign client. A run that OBSERVED the defect and then could not
    # continue has therefore still observed the defect, and reporting it as UNMEASURED would delete a positive
    # reading on the strength of a later limit - "changing what counts", the inverted BUG-1079 shape. The detail
    # keeps the truncation, because a rate computed from a short run is a FLOOR and must be read as one.
    if malformed:
        tail = (f" [run then stopped early at {state['attempts']} call(s): {state['unmeasured_reason']} - so this "
                f"rate is a FLOOR, not a measured rate]") if state["unmeasured_reason"] else ""
        return "RED", (f"{malformed} MALFORMED NAME(S) in {state['attempts']} call(s): "
                       f"contaminated={state['contaminated'][:3]} undeclared={state['undeclared'][:3]} "
                       f"- a call to a tool that does not exist (BUG-951 symptom 1){tail}")
    if state["unmeasured_reason"]:
        return "UNMEASURED", state["unmeasured_reason"]
    if drops and state["evictions"]:
        return "UNMEASURED", (f"{len(drops)} call(s) went unanswered AND {state['evictions']} engine eviction(s) "
                              f"fired in the same window (BUG-950 mechanism A) - two sufficient causes, so no "
                              f"verdict may be charged to this model")
    if drops:
        first = drops[0]
        return "RED", (f"{len(drops)} DROPPED CALL(S) in {state['attempts']} call(s); first at turn {first['turn']} "
                       f"({first['kind']}: {first['detail']}) - BUG-951 symptom 2")
    if state["parse_errors"]:
        # A REPAIR IS NOT HEALTH (T-215 limb 2). The parser still refused the header; what changed is that the
        # caller no longer loses the call. The detail must say WHICH of the two happened, because "every call
        # arrived" is true both for a lucky run and for a guarded one, and only one of them is fixed.
        if state.get("retry_guard") and state.get("retries"):
            retry_wall = sum(step["wall_s"] for step in state["steps"] if step.get("retried"))
            return "RED", (f"the engine's parser refused {state['parse_errors']} tool header(s) in this run's "
                           f"windows; {state['retries']} re-issue(s) recovered {state['recovered']} of them "
                           f"at {retry_wall:.1f}s of extra wall time - the DEFECT still fires, so this is a "
                           f"REPAIR, not health (D-3200 clause 1)")
        return "RED", (f"the engine's parser refused {state['parse_errors']} tool header(s) in this run's windows "
                       f"and every call still arrived - symptom without loss (it is luck, not health)")
    if state["attempts"] < target:
        return "UNMEASURED", (f"the loop ended at {state['attempts']} of {target} call(s) with no defect counted "
                              f"- a short run is not a bound")
    if state["attempts"] < MIN_BOUND_CALLS:
        return "UNMEASURED", (f"{state['attempts']} call(s) is below the gate's {MIN_BOUND_CALLS} - no bound may "
                              f"be claimed from it (T-213 clause 3)")
    bound = state["attempts"] / RULE_OF_THREE
    return "UNMEASURED_WITH_BOUND", (f"0 malformed, 0 dropped, 0 parse errors in {state['attempts']} call(s): "
                                     f"the rate is bounded at <= 1 in {bound:.0f} (rule of three, 95%) - which "
                                     f"cannot retire a defect observed at ~1 in 5, so this is NOT 'fixed'")


# ── THE RUN ────────────────────────────────────────────────────────────────────────────────────────────
def default_subject() -> str:
    """The model the defect DAMAGES, read from the role declaration (D-3034: a value that merely mentions a
    model declares nothing; this resolves the role's model)."""
    roles = (_yaml(ASSIGNMENTS).get("harness_roles") or {})
    model = str((roles.get("AGENT_LOOP_SHORT") or {}).get("model") or "")
    if not model:
        raise SystemExit("FATAL: config/model_assignments.yaml#harness_roles.AGENT_LOOP_SHORT.model is absent - "
                         "refusing to type a subject here (C12/C16)")
    return model


def echo_for(name: str, echo_variant: str) -> str:
    """PURE: the harness's reply to a tool call it cannot execute, in the declared variant. This is the ONE place
    the echo's wording is decided, so the seed and the loop's own defect path cannot disagree - a fixture half of
    whose echoes quote the name would be measuring the mitigation with the mitigation switched off."""
    if echo_variant == ECHO_QUOTED:
        return f"error: tool {name!r} does not exist"
    if echo_variant == ECHO_BLANK:
        return ECHO_BLANK_TEXT
    raise SystemExit(f"FATAL: echo_variant {echo_variant!r} is not in the declared vocabulary "
                     f"({ECHO_QUOTED!r}, {ECHO_BLANK!r}) - refusing to guess what the harness would have said (C16)")


def seed_history(total: int, tail: str, seed: bool, echo_variant: str = ECHO_QUOTED) -> list[dict[str, Any]]:
    """The prompt, plus - when `seed` - the SEEDED CORRUPTION: one assistant tool call whose name is a real tool
    with a harmony channel tail glued on (BUG-951's verbatim shape), and the error payload a harness would return
    for it. Nothing here warns the model that the name is corrupted: the axis under test is whether a corrupted
    name in history POISONS the next call, and a fixture that warns its subject is measuring politeness.

    `seed=False` is the CONTROL, and it exists because of the build_argname lesson (a trap that fails EVERYONE
    measures nothing): two runs that differ ONLY by these two messages separate "this model corrupts names on
    its own" from "the transcript taught it to". Without that pair the 14-in-30 reading has no attribution.

    `echo_variant` is T-215 limb 1's SECOND split of the same pair: the assistant turn is byte-identical in both
    variants and only the tool echo's content differs, so the difference between `quoted` and `blank` is the
    attribution of the copy to the verbatim name rather than to the seeded turn (which both variants carry)."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are a sub-agent. You MUST use the provided tool; never guess a value."},
        {"role": "user", "content": (f"Call {TOOL_NAME} once per assistant message, for index 1 up to {total}, in "
                                     f"order. After index {total} has been registered, answer with the single "
                                     f"word FINISHED.")},
    ]
    if not seed:
        return messages
    corrupted = f"{TOOL_NAME}<|channel|>{tail}"
    messages += [
        {"role": "assistant", "content": "", "tool_calls": [{
            "id": REPLAY_ID, "type": "function",
            "function": {"name": corrupted, "arguments": json.dumps({"index": "1"})}}]},
        {"role": "tool", "tool_call_id": REPLAY_ID, "content": echo_for(corrupted, echo_variant)},
    ]
    return messages


def run_model(decl: dict[str, Any], model: str, total: int, mode: str, tail: str,
              facts: dict[str, Any], echo_variant: str = ECHO_QUOTED,
              retry_guard: bool = False) -> dict[str, Any]:
    """Drive the red loop against ONE model and return its receipt row. The receipt carries the ENGINE identity
    (D-3152 limb 2: a verdict is a statement about a BUILD), the exact malformed names, and every turn's window."""
    url = str(decl["base_url"]).rstrip("/") + "/chat/completions"
    key = str((decl.get("headers") or {}).get("Authorization", ""))
    markers = facts["markers"]
    messages = (seed_history(total, tail, mode in ("replay", "blank-echo"), echo_variant)
                if mode in ("replay", "clean", "blank-echo") else
                [{"role": "system", "content": "You are a sub-agent. You MUST use the provided tool; never "
                                               "guess a value."},
                 {"role": "user", "content": (f"In EACH assistant message call {TOOL_NAME} TWICE, two tool calls "
                                              f"in one reply, walking indices 1..{total} in order. After index "
                                              f"{total} has been registered, answer with the single word "
                                              f"FINISHED.")}])
    declared = {TOOL_NAME}
    state: dict[str, Any] = {"attempts": 0, "clean": 0, "contaminated": [], "undeclared": [], "drops": [],
                             "evictions": 0, "parse_errors": 0, "args_unparsable": 0, "turns": 0,
                             "nudges": 0, "parallel_max": 0, "walls": [], "steps": [],
                             "retries": 0, "retry_streak": 0, "recovered": 0, "retry_guard": retry_guard,
                             "retry_bound_hits": 0,
                             "unmeasured_reason": "", "stop_reason": ""}
    while state["attempts"] < total and len(state["drops"]) < DROP_CEILING:
        if state["turns"] >= total + DROP_CEILING + TURN_HEADROOM + (RETRY_BUDGET if retry_guard else 0):
            state["stop_reason"] = "turn ceiling reached (a loop that spends turns without issuing calls)"
            break
        offset = log_offset(facts["log"])
        try:
            reply, wall, usage = ask(url, key, model, messages, BATTERY_MAX_TOKENS, tools=[READ_INDEX_SPEC])
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:300]
            except OSError:                                   # pragma: no cover - body already gone
                body = "<unreadable>"
            state["unmeasured_reason"] = (f"the ENGINE refused the request (HTTP {exc.code}: {body}) - a "
                                          f"transport refusal is not a fact about the model")
            break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            state["unmeasured_reason"] = f"the turn did not complete ({type(exc).__name__}: {exc})"
            break
        lines = log_since(facts["log"], offset)
        win = window(lines, markers, model)
        state["turns"] += 1
        state["evictions"] += win["evictions"]
        state["parse_errors"] += win["parse_errors"]
        state["walls"].append(wall)
        state["steps"].append({"turn": state["turns"], "wall_s": round(wall, 2),
                              "ttft_s": (usage or {}).get("time_to_first_token"),
                              "decode_tps": (usage or {}).get("generation_tokens_per_second"),
                              "parse_errors": win["parse_errors"], "evictions": win["evictions"],
                              "foreign_completions": win["foreign_completions"],
                              "evidence": win["evidence"][:2]})
        if win["foreign_completions"]:
            state["unmeasured_reason"] = (f"another client's completion line appeared in this turn's window "
                                          f"({win['foreign_completions']}) - the counts are not attributable")
            break
        choice = (reply.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            kind, detail = classify_turn(message, choice.get("finish_reason", ""), win)
            state["steps"][-1]["drop"] = kind
            if kind == "allowance":
                state["unmeasured_reason"] = detail
                break
            if may_retry(kind, state["retry_streak"], retry_guard, state["retries"]):
                # THE GUARD (T-215 limb 2), AND THE SHAPE ITS FIRST RECEIPT FORCED. MEASURED 2026-10-27 19:04: SIX
                # byte-identical re-issues recovered ZERO of 3 lost calls and cost 100.9 s - because R7 makes every
                # generation temperature=0.0, so re-sending the same messages is a DETERMINISTIC REPLAY of the same
                # refused header, not a retry. A retry can only differ if the PROMPT differs, so the re-issue carries
                # a nudge naming what went missing (the same lever the drop path already uses, and the reason the
                # replay run reached N with two losses). Recorded as a REPAIR, never as a silent success.
                state["retries"] += 1
                state["retry_streak"] += 1
                state["steps"][-1]["retried"] = True
                state["steps"][-1]["retry_detail"] = detail
                messages.append({"role": "user", "content": RETRY_NUDGE.format(tool=TOOL_NAME)})
                continue
            else:
                state["retry_streak"] = 0
                if retry_guard and kind == "engine_parse_error":
                    # R5 FINDING, ACCEPTED (gemma-4-E4B-it-MLX-4bit, 2026-10-27): a lost call that the guard could not
                    # repair was recorded EXACTLY like a lost call in a run with the guard switched off, so the receipt
                    # could not answer "did the guard try?" - and a repair that silently became a decline is the same
                    # drift as a repair reported as health (D-3201 decision 3). Only the CEILING lands here: every
                    # other reason may_retry says no is the kind test, which is the guard working, not the guard being
                    # blocked.
                    state["steps"][-1]["retry_refused"] = "bound reached (per-call ceiling or run budget)"
                    state["retry_bound_hits"] += 1
                state["drops"].append({"turn": state["turns"], "kind": kind, "detail": detail})
            state["nudges"] += 1
            messages.append({"role": "user", "content": (f"Continue: call {TOOL_NAME} with the next index. Use the "
                                                         f"tool, do not answer in words.")})
            continue
        if state["retry_streak"]:
            state["recovered"] += 1          # the retried turn finally produced the call it owed
            state["retry_streak"] = 0
        state["parallel_max"] = max(state["parallel_max"], len(tool_calls))
        state["steps"][-1]["names"] = [str((call.get("function") or {}).get("name") or "")
                                       for call in tool_calls]
        messages.append({"role": "assistant", "content": message.get("content") or "",
                         "tool_calls": tool_calls})
        for call in tool_calls:
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            raw_args = function.get("arguments")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except ValueError:
                args = {}
                state["args_unparsable"] += 1
            state["attempts"] += 1
            defect = classify_name(name, declared)
            if defect == "harmony_contaminated":
                state["contaminated"].append(name)
            elif defect == "undeclared":
                state["undeclared"].append(name)
            else:
                state["clean"] += 1
            payload = (echo_for(name, echo_variant) if defect else exec_read_index(args, total))
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": payload})
    if not state["stop_reason"]:
        # THE STOP REASON MUST NAME THE EXIT THAT ACTUALLY HAPPENED (T-215 limb 1, 2026-10-27): the first
        # blank-echo run ended on a SPENT ALLOWANCE and this line still claimed "stopped after 0 dropped call(s)
        # (the verdict is already RED)" - a receipt whose own account of why it stopped is false is drift, because
        # an auditor reads the stop line before the verdict.
        state["stop_reason"] = ("reached N" if state["attempts"] >= total else
                                (f"stopped early: {state['unmeasured_reason']}" if state["unmeasured_reason"] else
                                 f"stopped after {len(state['drops'])} dropped call(s) (the verdict is already RED "
                                 f"and cannot change)"))
    got, detail = verdict(state, total)
    return {"model": model, "mode": mode, "replay_tail": tail if mode in ("replay", "blank-echo") else None,
            "echo_variant": echo_variant,
            "calls_target": total, "attempts": state["attempts"], "clean_calls": state["clean"],
            "malformed_names": len(state["contaminated"]) + len(state["undeclared"]),
            "contaminated": state["contaminated"], "undeclared": state["undeclared"],
            "dropped_calls": len(state["drops"]), "drops": state["drops"],
            "engine_parse_errors": state["parse_errors"], "evictions": state["evictions"],
            "args_unparsable": state["args_unparsable"], "parallel_max": state["parallel_max"],
            "turns": state["turns"], "nudges": state["nudges"], "stop_reason": state["stop_reason"],
            "retry_guard": retry_guard, "retries": state["retries"], "recovered_calls": state["recovered"],
            "retry_bound_hits": state["retry_bound_hits"],
            "retry_wall_s": round(sum(s["wall_s"] for s in state["steps"] if s.get("retried")), 1),
            "slowest_turn_s": round(max(state["walls"]), 1) if state["walls"] else None,
            "verdict": got, "detail": detail, "steps": state["steps"]}


# ── SELFTEST: every classifier asked both ways (a control that needs a model is a bill) ────────────────
def selftest() -> int:
    """Known-answer controls on the PURE surface. Two-sided by construction: each rule is asked once with the
    defect present and once with it absent, because a one-sided control passes for a function that always says
    the same word."""
    bad: list[str] = []
    declared = {TOOL_NAME}

    name_cases = [
        (TOOL_NAME, "", "a declared tool name must not be malformed"),
        (f"{TOOL_NAME}<|channel|>commentary", "harmony_contaminated",
         "BUG-951's verbatim shape must read as contaminated"),
        (f"{TOOL_NAME}<|channel|>json", "harmony_contaminated", "the <|channel|>json form must read contaminated"),
        (f"{TOOL_NAME}<|channel|>analysis", "harmony_contaminated", "the analysis form must read contaminated"),
        (f"{TOOL_NAME}<|start|>assistant", "harmony_contaminated", "a leaked <|start|> must read contaminated"),
        ("read_idx", "undeclared", "a clean but undeclared name must read undeclared, NOT contaminated"),
        ("", "undeclared", "an empty name must read undeclared (both classes must stay distinguishable)"),
    ]
    for name, want, label in name_cases:
        got = classify_name(name, declared)
        if got != want:
            bad.append(f"{label}: got {got!r}")

    clean = {"parse_errors": 0, "evictions": 0}
    parsed = {"parse_errors": 1, "evictions": 0}
    turn_cases = [
        ({"content": ""}, "length", parsed, "engine_parse_error",
         "empty content + finish=length + a parse error in the window is a LOST CALL, not an allowance"),
        ({"content": ""}, "length", clean, "allowance",
         "the same shape with NO parse error is the instrument's own limit (UNMEASURED)"),
        ({"content": "I cannot proceed."}, "stop", clean, "answered", "words where a call was owed is a drop"),
        ({"content": ""}, "stop", clean, "silent_stop", "an empty stop with no parse error is a real non-answer"),
        ({"content": "done"}, "length", parsed, "engine_parse_error",
         "a parse error outranks content: the parser refused the header regardless of what text came with it"),
    ]
    for message, finish, win, want, label in turn_cases:
        got = classify_turn(message, finish, win)[0]
        if got != want:
            bad.append(f"{label}: got {got!r}")

    def fresh(**over: Any) -> dict[str, Any]:
        """One synthetic run state so the verdict can be asked without a model."""
        state = {"attempts": MIN_BOUND_CALLS, "clean": MIN_BOUND_CALLS, "contaminated": [], "undeclared": [],
                 "drops": [], "evictions": 0, "parse_errors": 0, "args_unparsable": 0, "turns": MIN_BOUND_CALLS,
                 "nudges": 0, "parallel_max": 1, "walls": [1.0], "steps": [], "unmeasured_reason": "",
                 "stop_reason": "reached N"}
        state.update(over)
        return state

    drop = {"turn": 7, "kind": "engine_parse_error", "detail": "lost"}
    verdict_cases = [
        (fresh(), "UNMEASURED_WITH_BOUND", "30 clean calls must return a BOUND, never a PASS"),
        (fresh(contaminated=[f"{TOOL_NAME}<|channel|>commentary"]), "RED",
         "one contaminated name must be RED"),
        (fresh(undeclared=["read_idx"]), "RED", "one undeclared name must be RED"),
        (fresh(drops=[drop]), "RED", "one unanswered call with no eviction must be RED"),
        (fresh(drops=[drop], evictions=1), "UNMEASURED",
         "a drop coinciding with an eviction must be UNMEASURED (BUG-950 mechanism A is a second cause)"),
        (fresh(parse_errors=2), "RED", "a refused header with no lost call is still the defect (symptom without loss)"),
        (fresh(attempts=12, clean=12), "UNMEASURED", "12 clean calls is below the gate's 30 - no bound may be claimed"),
        (fresh(unmeasured_reason="HTTP 400: bad history"), "UNMEASURED",
         "an engine refusal must be UNMEASURED, never RED"),
        (fresh(attempts=3, clean=3), "UNMEASURED", "a loop that stopped short with no defect is not a bound"),
        (fresh(attempts=2, contaminated=["read_index<|channel|>commentary"], unmeasured_reason="an allowance ran out"),
         "RED", "an OBSERVED malformed name outranks a later allowance: a body-side fact cannot be un-observed"),
        (fresh(attempts=2, unmeasured_reason="an allowance ran out"), "UNMEASURED",
         "the same truncation with NOTHING observed stays UNMEASURED (the ordering must be two-sided)"),
    ]
    for state, want, label in verdict_cases:
        got = verdict(state, MIN_BOUND_CALLS)[0]
        if got != want:
            bad.append(f"{label}: got {got!r}")

    # ── A REPAIR MUST READ AS A REPAIR, NOT AS LUCK (T-215 limb 2, 2026-10-27) ────────────────────────
    # MEASURED shape of the guard's first successful run: 2 headers refused, 2 recovered, 0 lost. The receipt
    # printed "it is luck, not health" because verdict() read a state key run_model never set - so the branch is
    # now asserted BOTH WAYS, and the count of controls is what makes the assertion visible.
    repaired = fresh(parse_errors=2, retry_guard=True, retries=2, recovered=2,
                     steps=[{"wall_s": 12.4, "retried": True}, {"wall_s": 12.4, "retried": True}])
    word, detail = verdict(repaired, MIN_BOUND_CALLS)
    if word != "RED" or "REPAIR" not in detail:
        bad.append(f"a guarded run that recovered its losses must read RED and say REPAIR, got {word!r}: {detail[:70]!r}")
    if "luck" not in verdict(fresh(parse_errors=2), MIN_BOUND_CALLS)[1]:
        bad.append("the SAME counters with NO guard must read 'luck' (the control for the branch above)")

    tool_cases = [
        ({"index": "1"}, 2, "NEXT: call read_index with index=2.", "a mid-run index must name the next one"),
        ({"index": "2"}, 2, "FINISHED", "the last index must release the loop to answer"),
        ({"index": "9"}, 2, "outside 1..2", "an out-of-range index must be an error the grader can NAME"),
        ({"index": "x"}, 2, "not a number", "a non-numeric index must be an error, never a silent pass"),
    ]
    for args, total, needle, label in tool_cases:
        payload = exec_read_index(args, total)
        if needle not in payload:
            bad.append(f"{label}: got {payload!r}")

    synthetic = [
        "2026-10-27 16:10:26,795 - omlx.adapter.harmony - WARNING - [-] - Error parsing tool calls from tokens: "
        "Unexpected EOS while waiting for message header to complete",
        "2026-10-27 16:10:26,798 - omlx.server - INFO - [-] - Chat completion: model=gpt-oss-20b-MXFP4-Q8, "
        "1024 tokens in 25.28s (40.5 tok/s), prompt: 410, finish_reason=length, max_tokens=1024",
        "2026-10-27 16:02:40,779 - omlx.scheduler - INFO - [-] - Evicting idle model 'gpt-oss-20b-MXFP4-Q8' for "
        "prefill headroom",
        "2026-10-27 16:02:41,000 - omlx.server - INFO - [-] - Chat completion: model=gemma-4-E4B-it-MLX-4bit, "
        "12 tokens in 0.4s (30.0 tok/s), prompt: 100, finish_reason=stop",
    ]
    markers = _yaml(ENGINE)["engine"]["log_markers"]
    win = window(synthetic, markers, "gpt-oss-20b-MXFP4-Q8")
    if win["parse_errors"] != 1:
        bad.append(f"the log witness must count ONE parse error, got {win['parse_errors']}")
    if win["evictions"] != 1:
        bad.append(f"the log witness must count ONE eviction, got {win['evictions']}")
    if win["foreign_completions"] != 1:
        bad.append(f"a second client's completion must be reported as foreign, got {win['foreign_completions']}")
    if not win["evidence"]:
        bad.append("the evidence lines must be kept (a counter without its line is not auditable)")

    seeded = seed_history(5, "commentary", True)
    seeded_name = seeded[2]["tool_calls"][0]["function"]["name"]
    if classify_name(seeded_name, declared) != "harmony_contaminated":
        bad.append(f"the seeded history must carry a contaminated name, got {seeded_name!r}")
    if seeded[3].get("tool_call_id") != seeded[2]["tool_calls"][0]["id"]:
        bad.append("the seeded tool result must answer the seeded call id, or the history is malformed")
    unseeded = seed_history(5, "commentary", False)
    if len(unseeded) != 2 or any(message["role"] == "tool" for message in unseeded):
        bad.append("the CONTROL history must be the two prompt messages alone (the pair's only difference)")

    # ── T-215 limb 1: the echo axis must change ONE string and nothing else ──────────────────────────
    quoted = seed_history(5, "commentary", True, ECHO_QUOTED)
    blank = seed_history(5, "commentary", True, ECHO_BLANK)
    corrupted = f"{TOOL_NAME}<|channel|>commentary"
    if len(quoted) != len(blank):
        bad.append(f"the echo variant must not change the transcript's LENGTH ({len(quoted)} vs {len(blank)}): a "
                   f"structural change would confound the axis with the seeded turn")
    if quoted[2] != blank[2]:
        bad.append("the seeded assistant turn must be BYTE-IDENTICAL across echo variants - it is the half held "
                   "constant, and a difference there would make the axis unreadable")
    if corrupted not in quoted[3]["content"]:
        bad.append("the QUOTED echo must repeat the corrupted name verbatim (that is production's shape)")
    if corrupted in blank[3]["content"] or "commentary" in blank[3]["content"]:
        bad.append(f"the BLANK echo must not carry the name or its tail, got {blank[3]['content']!r}")
    if quoted[3]["role"] != blank[3]["role"] or quoted[3]["tool_call_id"] != blank[3]["tool_call_id"]:
        bad.append("both variants must keep the echo's role and call id (same message, different content)")
    if len(seed_history(5, "commentary", False, ECHO_BLANK)) != 2:
        bad.append("the CONTROL must be untouched by the echo variant (no seed, no echo, either way)")
    if echo_for(TOOL_NAME, ECHO_QUOTED) == echo_for(TOOL_NAME, ECHO_BLANK):
        bad.append("echo_for must differ between variants, or the axis is cosmetic")
    try:
        echo_for(TOOL_NAME, "invented")
        bad.append("an undeclared echo variant must be refused, never guessed (C16)")
    except SystemExit:
        pass

    # ── T-215 limb 2: the guard may retry ONE shape and no other (both sides asked) ──────────────────
    retry_cases = [
        ("engine_parse_error", 0, True, 0, True, "a LOST call with the guard on must be re-issued"),
        ("engine_parse_error", 0, False, 0, False, "the guard OFF must never retry - that is the BEFORE reading"),
        ("allowance", 0, True, 0, False,
         "a spent allowance must NEVER be retried (it re-buys the same wall; BUG-1079's misattribution)"),
        ("silent_stop", 0, True, 0, False, "a declined call must never be retried (that would invent calls)"),
        ("answered", 0, True, 0, False, "words where a call was owed must never be retried"),
        ("engine_parse_error", RETRY_CEILING, True, 0, False, "the per-call ceiling must bind"),
        ("engine_parse_error", 0, True, RETRY_BUDGET, False, "the run budget must bind"),
    ]
    for kind, streak, guard_on, used, want, label in retry_cases:
        if may_retry(kind, streak, guard_on, used) != want:
            bad.append(f"may_retry: {label}")

    total = len(name_cases) + len(turn_cases) + len(verdict_cases) + len(tool_cases) + len(retry_cases) + 17
    for problem in bad:
        print(f"  FAIL control: {problem}")
    print(f"{'OK' if not bad else 'FAILED'} harmony-red-loop --selftest: {total - len(bad)}/{total} "
          f"known-answer control(s) green")
    return 1 if bad else 0


def main() -> int:
    """Run the red loop against ONE model (or a named model), print the counters, write the receipt."""
    parser = argparse.ArgumentParser(description="T-213/BUG-951 harmony red loop")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--mode", choices=("replay", "clean", "parallel", "blank-echo"), default="replay")
    parser.add_argument("--calls", type=int, default=MIN_BOUND_CALLS)
    parser.add_argument("--only", default="")
    parser.add_argument("--replay-tail", choices=CORRUPT_TAILS, default=CORRUPT_TAILS[0])
    parser.add_argument("--retry-guard", action="store_true",
                        help="T-215 limb 2: re-issue a turn whose owed call the engine's parser ate (bounded)")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    decl = declaration()
    served = [m["name"] for m in decl["models"]]
    model = args.only or default_subject()
    if model not in served:
        raise SystemExit(f"FATAL: {model!r} is not DECLARED to the harness (the parity rail's job, BUG-874); "
                         f"declared: {served}")
    facts = engine_facts()
    if not facts["log"].exists():
        raise SystemExit(f"FATAL: the engine log {facts['log']} does not exist - a drop could not be attributed, "
                         f"so this fixture refuses to run (C16)")
    budget = budget_s()
    out = pathlib.Path(args.out or f"temp/harmony_red_loop_receipt_{time.strftime('%Y%m%d')}.json")
    # floor of one call: a zero target would make every run "reached N" without issuing anything, so this is a
    # guard, not a tunable.
    row = run_model(decl, model, max(1, args.calls), args.mode, args.replay_tail, facts,
                    ECHO_BLANK if args.mode == "blank-echo" else ECHO_QUOTED, args.retry_guard)
    receipt = {"schema_version": RECEIPT_SCHEMA_VERSION,
               "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "fixture": "T-213 harmony red loop",
               "fixture_script": "scripts/harmony_red_loop.py", "script_sha256": script_digest(),
               "axis": {"replay": "a corrupted name seeded into history, then N real calls",
                        "clean": "the CONTROL: the same N calls with NO seeded corruption (the pair attributes "
                                 "a defect to the transcript rather than to the model's own habit)",
                        "parallel": "two tool calls demanded in ONE assistant message",
                        "blank-echo": "T-215 limb 1: the `replay` seed with the echoed error stripped of the "
                                      "name (`error: tool not found`, same message, same position) and the same "
                                      "name-free echo used for every defect the loop provokes - so the "
                                      "difference against `replay` is the verbatim NAME in the echo, not the "
                                      "presence of an echo and not the seeded assistant turn (both carry it)"
                        }[args.mode],
               "engine": engine_block(), "engine_log": str(facts["log"]),
               "per_turn_budget_s": budget, "declared_served": served,
               "min_bound_calls": MIN_BOUND_CALLS, "drop_ceiling": DROP_CEILING,
               "retry_guard": {"on": args.retry_guard, "per_call_ceiling": RETRY_CEILING,
                               "run_budget": RETRY_BUDGET,
                               "rule": "a turn whose owed call the engine's parser ate is RE-ISSUED byte-identically; "
                                       "an allowance, a silent stop or a declined call is NEVER retried"},
               "not_tested": ["enable_thinking=False on a harmony model that emits an analysis channel anyway "
                              "(a server-side setting this fixture never changes)",
                              "the <|channel|>json where <|constrain|>json belongs token confusion: the marker is "
                              "REPLAYED as a name tail, never produced by the model under observation",
                              "which HALF of the seeded pair teaches the copy: `blank-echo` now separates the "
                              "verbatim NAME in the echo from the seeded assistant turn, but the FULLY "
                              "UNBALANCED transcript (an assistant tool_call with NO tool response at all) is a "
                              "different axis - it changes structure as well as content, and an engine that "
                              "refuses it would return a transport error, not a reading"],
               "rows": [row]}
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"T-213 harmony red loop | axis {args.mode} | engine {receipt['engine'].get('app_version')} "
          f"({receipt['engine'].get('mlx_lm')}) | subject {model} | N={row['calls_target']}")
    print(f"  attempts={row['attempts']} clean={row['clean_calls']} malformed={row['malformed_names']} "
          f"dropped={row['dropped_calls']} engine_parse_errors={row['engine_parse_errors']} "
          f"evictions={row['evictions']} turns={row['turns']} slowest={row['slowest_turn_s']}s")
    print(f"  stop: {row['stop_reason']}")
    if row["retry_guard"]:
        print(f"  guard: retries={row['retries']} recovered={row['recovered_calls']} "
              f"retry_wall={row['retry_wall_s']}s")
    for item in row["drops"]:
        print(f"  DROP turn {item['turn']}: {item['kind']} - {item['detail']}")
    for name in row["contaminated"] + row["undeclared"]:
        print(f"  MALFORMED NAME: {name!r}")
    print(f"  VERDICT {row['verdict']}: {row['detail']}")
    print(f"  receipt {out}")
    return {"UNMEASURED_WITH_BOUND": 0, "UNMEASURED": 1}.get(row["verdict"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
