# SESSION HANDOFF — 2026-10-15 — T-154 (the harness is bounded the way its CLASS declares)

> For the next agent. Read this, then `governance/CONTEXT_INDEX.md`, then the registers. Commit: **93a86f9**
> (previous: 3bc0720 / T-160). Registers after this session: **1155 decisions / 599 bugs (225 open) / 51 open tasks**.

## 1. WHAT LANDED (all green, committed)

| object | state |
|---|---|
| **T-154** — bound the harness the way its class declares | **done / closed 2026-10-15** |
| **BUG-828** — the deployed harness was not bounded by its declared budgets | **CLOSED 2026-10-15** (part 3 has a named residual: T-161) |
| **D-3027** — the budget is DERIVED, the class may be PROPOSED | **ACTIVE** (minted this session) |
| **BUG-835** — the engine's chunk keepalive is read as the model's final answer | **OPEN, HIGH — this is the blocker** |
| **BUG-836** — no usable R5 review from either local verifier | **OPEN, MED** |
| **T-161 / T-162 / T-163** | new tasks (owner / owner / pipeline) |

**The code:** `pipeline/research_run.py` (class resolution, class env, recursive self-excluding liveness,
two fail-closed refusals, `--check`), `pipeline/subagent_fanout.py` (`mode: harness`, class-scoped budgets,
doctor reads the class bounds), `config/agent_context.yaml` (`classes.*` gained
`workstream_class/max_turns/stall_s/timeout_guard/transcript_in_ws/env/evidence`; new `workstreams:` and
`turn_budget:` blocks), `config/engine.yaml` (`harnesses.jobs.agent_loop.args` + `stdout_noise_regex`),
`justfile` (the class-bound check, rc 2 tolerated as OWNER-OWED).

**Gates:** research_run **38/38** (7 known-answer controls on the derived bounds), fanout **43/43**,
config_audit `--strict`, duplicate keys, decisions `--check`, probe **17/17**, harness_env **14/14**,
session plan / declaration consumers / recalibration pins (0 DRIFT) / repo integrity.

**The live proof (do not re-litigate this):** `temp/runs/harness_20261015c/fan_h1` — pi ran a healthy tool
loop, the runner saw it BUSY (`idle 0.9–17.7 s`, `stalled=False`, `stall_s=120`) with its transcript growing
**inside** the workstream (`agent/sessions/**.jsonl`, 113,306 → 114,750 B). BUG-828's false stall is gone.

## 2. THE BLOCKER THE PROOF FOUND (owner act, in this order)

**BUG-835 / T-162 — the harness cannot finish a turn.** pi's last transcript record is
`content: [], output: 0, stopReason: stop, responseModel: "keepalive"`; the engine log agrees
(`0 tokens ... finish_reason=stop`). Cause, read from the engine's own source: `sse_keepalive_mode: "chunk"`
emits a frame shaped exactly like a completion chunk (`model:"keepalive"`), and pi takes it as the answer.
The engine's own function documents the hazard and offers `comment` (a true no-op) and `off`.

```bash
# 1. back up the live home, then set the no-op frame
cp ~/.omlx/settings.json ~/.omlx/settings.json.bak-$(date +%Y%m%d%H%M%S)
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home()/".omlx/settings.json"
d = json.loads(p.read_text()); d["server"]["sse_keepalive_mode"] = "comment"
p.write_text(json.dumps(d, indent=2) + "\n"); print("sse_keepalive_mode ->", d["server"]["sse_keepalive_mode"])
PY
# 2. the server holds its settings object from start-up, so restart the engine (the owner's act), then:
python3 pipeline/subagent_fanout.py run --tasks temp/t154_harness_proof.yaml --run t137_preflight
#    PASS = 98_receipt.json reads DONE for the task. FAIL = still EMPTY (try "off", then re-measure).
```

**T-161 — bind the derived ceiling (3,266 tokens) in the engine's own per-model home.** Optional in
principle, but it is the difference between a declared bound and a bound: today `pi` inherits 32768 (~20 min
at 27.4 tok/s). `python3 pipeline/research_run.py --check` reads the binding and prints OWNER-OWED (rc 2)
while it is absent. Add `models.<model>.max_tokens` to `~/.omlx/model_settings.json`, then verify
**functionally** (the engine log line for a pi turn must show the derived ceiling, not 32768): the per-model
accessor goes through the server's `ModelSettingsManager` and its reload semantics were NOT verified here.

## 3. SEQUENCING (unchanged shape, one new prerequisite in front)

```
BUG-835 fix (T-162)  ->  re-run the T-154 proof (both T-137 preconditions MET)  ->  T-137 A/B
                     ->  python3 pipeline/apply_provider_flip.py --apply-flip  ->  BUG-832 closes
T-156 (capability registry)  <- BUG-836 gives it a MEASURED negative to encode
T-163 (an answer's SHAPE)    <- fixes the instrument that let BUG-836 through
T-158 (context diet)         <- unchanged, SHOULD
```

**`config/ab_harness_t137.yaml#preconditions` is the gate for T-137:** P1 (a harness finishes a turn) and P2
(`--check` rc 0). Both arms drive the same harness class, so running them before P1 is met measures the
keepalive, not the model.

## 4. THE POLICY THIS SESSION SEALED (D-3027) — the short version

A model may PROPOSE a task class (a declared label, with abstention, never auto-applied). A model never sets
a BUDGET: the budget is derived from the owner's knob × measured rates, because a budget a model can raise is
not a bound, and because **this session measured the cost of an undeclared one** (an undeclared ceiling let a
turn run 20 minutes against a 90 s knob). Escalation spends more only on MEASURED evidence (refuted
citation, empty answer, spent retry). laya-mlx/jevmlx/gpt-oss-20b may become PROPOSERS only after they are
routable slots with a measured agreement floor — and BUG-836 shows why the eligibility bar is not academic.

## 5. NEXT CRITICAL STEP

Owner: **T-162 (BUG-835)** — the engine's keepalive mode — then re-run `temp/t154_harness_proof.yaml`.
Pipeline, in parallel and independent of the owner: **T-163** (check an answer's SHAPE, not its length) and
**T-156** (the registry that must refuse a 4B model a 22 KB review).
