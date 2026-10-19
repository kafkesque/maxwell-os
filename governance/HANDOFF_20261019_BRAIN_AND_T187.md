# HANDOFF 2026-10-19 — BRAIN VERDICT, T-187 BUILT, ORNITH DECODE CORRECTED

> Written for a NEW goose session (the user will start one to pick up GOOSE_AUTO_COMPACT_THRESHOLD=0.94 and
> the deepseek planner window — env knobs are read at session BIRTH, so this session cannot show them).
> Everything below is the operative state to continue from. Read `governance/CONTEXT_INDEX.md` first for
> where the long-lived registers live; this file is the session-scoped delta.

## WHAT JUST LANDED THIS TURN (commit follows this file)

1. **T-187 instrument BUILT** in `scripts/measure_subagent_loop.py` — the two-step / two-tool / distractor /
   dependent-steps fixture that is the ONLY gate for promoting `AGENT_LOOP_FAST` / `AGENT_LOOP_WORKHORSE`
   (D-3058). New surface: `--two-step` flag, `TOKEN_TOOL` (`lookup_token`), `make_two_step_fixture`,
   `grade_two_step`, `run_two_step_model`. Selftest **13/13** green; ruff clean. The receipt carries per-step
   TTFT + decode rate from the engine's own counters.
   - **RED-LOOP RECEIPT (D-3036):** `python3 scripts/measure_subagent_loop.py --two-step --only MiniCPM5-2B-MLX`
     → PASS, read_lines x2 + lookup_token key=7, answer "token-7", slowest 4.9 s. Receipt at
     `temp/subagent_loop_two_step_receipt_20261019.json`.
   - The default (no flag) path is UNCHANGED — `llm_candidate_probe.py` / `model_oracles.yaml` still see the
     single-tool 3-call fixture as the promotion rail.

2. **`scripts/measure_prefill.py` gained `--max-tokens`** (default 1 = prefill receipt, unchanged). This is
   the durable instrument for the decode benchmark D-3102 said was "owed first".

3. **The owed >=128-token decode benchmark is DELIVERED.** `--model Ornith-1.5-35B-A3B-REAP-19B --tokens 4000
   --max-tokens 128` → **decode 39.14 tok/s**, TTFT 0.25 s, model load 6.24 s (rc1). This CORRECTS the D-3102
   A/B decode column: the 96.91→222.13 tok/s was a single-token artifact (`max_tokens=1`); the real Ornith
   REAP-19B decode is **~39 tok/s**.

4. **Persisted** to `config/agent_context.yaml` as `measured_engine_ab_20261019` (decode 39.14 + a note that
   the cold prefill counter 19.88 on the same call is load-contaminated and does NOT supersede
   `measured_prefill_20261016`'s 155.1 warm reading).

## THE FOUR ANSWERS (grounded, this turn)

1. **Root cause of the 2026-10-18 governance drift** = derived-data staleness from a 4-step manual chain with
   no single atomic target: append RESOLVED heading → `bug_status.py` → `gov_sync.py --apply` → drop stale
   hand-index row. Step 1 ran, steps 2–4 didn't. **NOT gemma** (it was the R5 code-review verifier, never a
   governance writer) and **NOT the guardrails** (they are what CAUGHT it). **Structural fix (recommend, not
   yet built):** one `just gov-sync` recipe that runs the chain in order and refuses exit 0 while any face is
   stale. Do not over-engineer beyond that.

2. **The brain** = ONE orchestrator model (goose's main loop is single-model) that delegates heavy sub-roles to
   best-in-role locals (already measured in D-2549). **Dispositive fact = BUG-832 (OPEN):** the local brain
   route is REFUTED BY MEASUREMENT — gemma-4-E4B and Qwen3-Coder-30B-A3B both score **0.0 on
   `long_context_reasoning_16k`**. The #1 *unmeasured* local brain candidate is **gpt-oss-20b-MXFP4-Q8**
   (131072 window, 41.7 tok/s decode, 12.1 GB) — it has NOT been scored on the long-context gate; measure it
   next. **Switch back from deepseek ONLY when a local candidate is GREEN on all three gates simultaneously:**
   (a) long_context_reasoning_16k non-zero/non-slop, (b) T-187 two-step loop PASS, (c) gemma drift eval
   (20 class + 20 summ + 10 code-review, ground-truth). Until then deepseek stays — the alternative is a
   measured downgrade. Current config (deepseek brain + local delegates) is the best AVAILABLE temporary state,
   not the target (C1/C3 sovereignty).

3. **D-3101 cloud-ceiling SPLIT** = split the ONE lifetime cloud counter into (1) pipeline-ingestion (batch
   document processing, windowed burn-rate) and (2) harness-metering (interactive deepseek brain). Discriminator
   already corrected to LEDGER realpath (D-3034). **The single remaining owner word = the burn-rate WINDOW
   length.** Recommendation: trailing-30-day window, per-day threshold = ceiling ÷ 30.

4. **BUG-941** — CONFIRMED: keep `qwen35_ane_prefill_enabled=false` on M1 Max (Code=47 ANE warmup crash; the
   workaround IS the fix). Stays OPEN as a logged reason, no action needed.

## OWNER-WORD BLOCKERS (pending the owner — cannot be done by an agent)

- **D-3101:** state the pipeline-ingestion burn-rate window length (recommend 30 days).
- **BUG-941:** (already confirmed "keep" this turn — nothing to do).
- **New session:** start `goose run` fresh to pick up GOOSE_AUTO_COMPACT_THRESHOLD=0.94 and open the deepseek
  planner window (GOOSE_PLANNER_PROVIDER=custom_deepseek, GOOSE_PLANNER_MODEL=deepseek-v4-pro).

## NEXT CRITICAL STEPS (consequential order — highest leverage first)

1. **Run T-187 against the full served set** — `python3 scripts/measure_subagent_loop.py --two-step` (8 models).
   This is the gate that decides whether MiniCPM5-2B / Ornith-1.5-9B can be promoted to AGENT_LOOP_FAST /
   AGENT_LOOP_WORKHORSE. Highest leverage because it unblocks model promotion AND the Splash A/B (already
   approved, gated on T-187).
2. **Score gpt-oss-20b-MXFP4-Q8 on `long_context_reasoning_16k`** (the BUG-832 gate only tested gemma +
   Qwen3-Coder). If it clears, it becomes the local brain candidate.
3. **gemma drift eval** (20+20+10 ground-truth) during the deepseek window — this is the slop-proof gate for
   the eventual local-brain switch-back.
4. **Gov sync** — confirm `check_bug_status.py`, `check_governance_faces.py`, `gov_sync.py --check` are all
   green after this turn's edits (the edits did not touch any register, but verify).
5. **Eject the oMLX DMG** from /Volumes (A/B is complete) and clean the phantom Qwen3.6-35B-A3B-4bit from
   ~/.omlx/model_settings.json.

## FORENSIC-AUDIT NOTE (before any further serious implementation)

The T-187 build is self-contained: it ADDS a fixture path and leaves the existing default path byte-compatible
(the `llm_candidate_probe.py` / `model_oracles.yaml` consumers are unaffected). `measure_prefill.py`'s
`--max-tokens` defaults to 1, so existing callers are unaffected. No register, buglog, or decision file was
edited this turn — only scripts + `config/agent_context.yaml` (a measurement table). So no governance
re-derivation is required; run the health ladder once in the new session to confirm.


---

## SESSION DELTA 2026-10-19 (resume) — T-187 LANDED, DRIFT CAUGHT+FIXED, lc_reasoning IN FLIGHT

### 1. SESSION-PURPOSE VERDICT: the env-knob purpose was NOT achieved
The prior handoff's reason for a new session was to pick up `GOOSE_AUTO_COMPACT_THRESHOLD=0.94` + the
deepseek planner window (`GOOSE_PLANNER_PROVIDER=custom_deepseek`, `GOOSE_PLANNER_MODEL=deepseek-v4-pro`),
env knobs read at session BIRTH. MEASURED this session: `GOOSE_AUTO_COMPACT_THRESHOLD=0.8` and NO
`GOOSE_PLANNER_*` present. So the new session did NOT inherit the declared knobs. The config's OWN home
(`config/agent_context.yaml#ratified.knobs.trigger`) declares `GOOSE_AUTO_COMPACT_THRESHOLD: 0.94` +
`GOOSE_AUTO_COMPACT_TOKEN_LIMIT: 32768` + `GOOSE_CONTEXT_LIMIT: 32768` — the gap is between that
DECLARATION and the launched process env. OWNER must relaunch (see manual block).

### 2. T-187 FULL SERVED SET — RUN (8/8 measured, receipt temp/subagent_loop_two_step_full_20261019.json)
`python3 scripts/measure_subagent_loop.py --two-step` → **6/8 PASS** (per-turn budget 90 s):

| verdict | model | slowest turn | decode tok/s |
|---|---|---|---|
| PASS | MiniCPM5-2B-MLX | **1.2 s** | 81–84 |
| PASS | Ornith-1.5-35B-A3B-REAP-19B | 2.9 s | 39–41 |
| PASS | Ornith-1.5-9B-MLX-8bit | 13.5 s | 18–19 |
| PASS | Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | 17.2 s | 41–47 |
| PASS | Qwen3.8-27B-MLX-4bit | 39.8 s | 6–8 |
| PASS | gpt-oss-20b-MXFP4-Q8 | 35.3 s | 42 |
| FAIL | Phi-4-mini-instruct-8bit | — | 0 tool calls (BUG-053 shape confirmed) |
| FAIL | gemma-4-E4B-it-MLX-4bit | 12.1 s | read=1, lookup=0 (no step 2) |

**Two findings that CONTRADICT existing governance (must be re-ruled, not silently applied):**
- **gpt-oss-20b PASSES the two-step/two-tool loop** (42 tok/s) — contradicts `config/harness_policy.yaml`
  `tool_calling.never = {gpt-oss-20b, 0.0, "a 0.0 tool-caller must never drive a tool loop"}`. The 0.0 came
  from `suite_toolcalling()` (raw-JSON tool format); T-187 uses the ENGINE's native `tool_calls`, which it
  CAN drive. Two DIFFERENT tool-calling forms — the harness/delegate path uses the native one.
- **gemma-4-E4B FAILS the two-step loop** (reads seed, never does the dependent lookup) — it is the model
  `harness_policy` still labels "the only agent_loop-routable model" (latency). Its loop CAPABILITY is now
  contradicted for a dependent 2-step shape.

### 3. DRIFT CAUGHT + FIXED (preflight doing its job)
`tools/model_eval_suite.py` preflight refused: `portfolio_exact` — live registry has 8 models but
`config/bench_preflight.yaml#environment.expected_models` listed 7 (MiniCPM5-2B-MLX, the engine's own
`default_model`, was served but never added to the benchmark portfolio). FIXED by adding `MiniCPM5-2B-MLX`
to `expected_models` (atomic edit). This is the same derived-data-staleness class as the 2026-10-18 drift.

### 4. lc_reasoning ON gpt-oss-20b — IN FLIGHT (the BUG-832 long-context gate)
`python3 tools/model_eval_suite.py --models gpt-oss-20b-MXFP4-Q8 --suites lc_reasoning` launched (PID 76429);
writes to `governance/model_eval_checkpoint.jsonl` + `temp/lc_reasoning_gptoss_20261019.log`. RESULT PENDING
at this handoff. If gpt-oss clears lc_reasoning (non-zero), it becomes the #1 local-brain candidate (the
BUG-832 gate previously only tested gemma + Qwen3-Coder, both 0.0).

### 5. MANUAL OWNER INSTRUCTIONS (copy-paste)
1. **Relaunch with the declared env knobs** (the purpose this session missed):
   ```sh
   GOOSE_AUTO_COMPACT_THRESHOLD=0.94 \
   GOOSE_AUTO_COMPACT_TOKEN_LIMIT=32768 \
   GOOSE_CONTEXT_LIMIT=32768 \
   goose run
   ```
   Expected: `env | grep GOOSE_AUTO_COMPACT` prints `0.94` INSIDE the new session. If it prints `0.8`,
   the knobs were not exported in the shell that spawned goose — export them in `~/.zshrc` (or the launch
   wrapper) and retry. The planner window (deepseek brain) is a SEPARATE word: BUG-832 remedy #2 says
   DECIDE the brain explicitly — do NOT assume the planner knobs without resolving BUG-832 first.
2. **Clean the phantom model** (DMG already ejected — /Volumes has no oMLX mount; A/B complete):
   `Qwen3.6-35B-A3B-4bit` is still a key in `~/.omlx/model_settings.json`. Its `_unloaded` symlink is
   BROKEN (bytes gone, BUG-808). Remove the key ONLY while oMLX-server is STOPPED (editing live settings
   drifts the running engine): quit oMLX, delete the `Qwen3.6-35B-A3B-4bit` entry, relaunch.

### 6. NEXT CRITICAL STEPS (consequential order)
1. Read `lc_reasoning` result (in flight) → if gpt-oss clears it, it clears 2 of 3 local-brain gates
   (tool-loop PASS + long-context); the 3rd is the gemma drift eval.
2. Re-rule the two harness_policy contradictions (gpt-oss tool-calling, gemma loop capability) — a D-decision,
   NOT a silent edit (D-3038: rejected/contradicted findings are registered with their reason).
3. gemma drift eval (20 class + 20 summ + 10 code-review) — the slop-proof gate for switch-back.
4. `just gov-sync` / health ladder after the preflight config edit (confirm faces still equal).
