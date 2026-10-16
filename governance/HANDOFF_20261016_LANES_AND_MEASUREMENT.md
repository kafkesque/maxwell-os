# SESSION HANDOFF — 2026-10-16 · LANES, PREFILL, AND MODEL PARITY

**Read this file first if you are resuming.** Registers first, then this narrative.

## 1. WHAT IS CLOSED (do not re-open)

| id | state | one line |
|---|---|---|
| BUG-870 | RETRACTED | A FALSE POSITIVE filed by the assistant. `config/gov_sync.yaml` ALREADY declares the four decision-state buckets; the census script filtered on `endswith('_decision_states')` and matched only ONE of four keys. **The bug was in the diagnostic, not the config.** `check_governance_faces.py --check` rc=0. **D-3055 is MOOT and must NOT be executed** (`temp/NEXT_ACT_20261016r.md` is banner-marked). |
| BUG-871 | FIXED | `harness_env.py --print` refused to name a scope; `bind_harness_env.sh` no-arg EVALED the exports — how a global 32k cap and the 4B subagent model could land in the owner's login profile. Now `--scope <declared class>` is mandatory and the no-arg eval is gone. Selftest 18/18. R5 APPROVE on final digests (`harness_env.py 7737bbb0f21425a3`, `bind_harness_env.sh e9b84dc75c1099ba`). **Residual:** only `agent_loop` EARNS a harness (`agent_probe`/`pipeline_batch` rows declare `harness: null`), and one `GOOSE_MODEL` is emitted for all three because no class→role home exists. Not guessed; needs a declared home. |
| BUG-872 | FIXED | A two-day-old **stale disproof** was carrying a whole doctrine. The prefix cache is LIVE: `cached 2613/2616`, **speedup 25.01x** vs a 5.0x bar, independently confirmed by `agent_context_probe --prefill-ab` at 26,240 tokens (**23.35x**) — and that artifact, `governance/bench_preflight_latest.json`, had been sitting there since **Sep 26**, three weeks BEFORE the disproof was written. Doctrine corrected in `agent_context.yaml`; the 2026-10-14 text is preserved, `superseded_by` points at the new block. |
| BUG-873 | OPEN | An enabled extension contributing ZERO tools raises nothing. `youtubetranscript` is `enabled: true`; the server is HEALTHY (driven directly it returned the 14,162-char transcript of `hJz7zi17mXA`); `list_functions` shows 40 functions and NOT ONE YouTube tool. **Root cause UNVERIFIED** — a PATH hypothesis was tested and DISPROVEN. Red loop named in the bug. |
| BUG-874 | OPEN | Three model sets, three answers. See §3. |
| AnyJev | REFUSED | Revised DOWN from "deferred to a sandbox arm" after READING an independent replication. The **order-rotation probe** is the token adopted; the method is not. See §5. |

## 2. THE TWO MEASUREMENTS THAT MATTER MOST

**a. Prefill is now nearly free on a warm prefix.** Byte-identical 2,616-token prefix, gemma-4-E4B:
cold 6.90 s -> warm **0.16–0.39 s**, `cached 2613/2616`, **25.01x**. The 27B is the trap: 81.0 s then
**111.1 s on the SECOND IDENTICAL CALL** (reload/swap thrash), 24–32 tok/s, and for `agent_loop`'s 26,214-token
working set it needs **672.2 s against a 60 s budget -> `prefill_bill`, NOT routable**. **"A bigger model is
faster" is FALSE here.** Prefill cost tracks **ACTIVE** parameters: 30B-A3B decodes 49.5 tok/s against the 4B
dense's 36.3, at 6.8 GB vs 17.2 GB.

**b. The 4.9 tok/s complaint was never a throughput problem.** It was a blended rate on a COLD prefill. And the
32k cap made it worse through ONE mechanism, not two: the cap forced compactions, each compaction REPLACED the
history, and each replacement re-prefilled the summary cold — throwing away a prefix ~25x cheaper to reuse.
Now in the config as the hazard `compaction_destroys_a_live_cache`.

## 3. THE PARITY BREAK (BUG-874) — three homes, three answers

- **SERVED (authoritative):** Phi-4-mini 32768 · Qwen3-Coder-30B-A3B 32768 · Qwen3.8-27B 262144 ·
  gemma-4-E4B 32768 · gpt-oss-20b-Q8 131072 · MiniCPM5-2B 131072 · Ornith-1.5-35B-A3B-REAP-19B 262144 ·
  Ornith-1.5-9B 262144
- **GOOSE is told:** Phi-4-mini · gemma-4-E4B · Qwen3-Coder-30B · gpt-oss-20b-Q8 · **gpt-oss-20b-Q4** ·
  **Qwen3.5-9B-4bit** · Qwen3.8-27B · **gemma-4-31B-it-MLX-8bit**
- **EXPOSED BUT NOT SERVED (3):** gpt-oss-20b-Q4, Qwen3.5-9B-4bit, gemma-4-31B — **goose can pick a model that
  will FAIL the request.** This is the dangerous direction.
- **SERVED BUT NOT EXPOSED (3):** MiniCPM5-2B (the declared **LIGHTWEIGHT_PROBE** role's model!), the two
  Orniths — served capacity no session can reach.
- The union IS the probe's six faults: `FAIL agent-context: 6 declared fault(s)` / `fault_rc: 2`. **RED today.**
- `agent_context.yaml` itself asserts the opposite: `served:` lists FIVE models and `declared_equal: true`.

**TWO NEW FINDINGS (measured today):**
1. **The cache is PER-MODEL, not global.** Second identical call: cached 2560–2675 on five models, and
   **cached = 0 on BOTH Orniths** (warm wall 10.53 s / 23.45 s). Two of eight served models can never benefit
   from prefix stability. `cache_accounting` calls prefix reuse a property of the MACHINE; it is the MODEL's.
   Block granularity also moved: 2616−2560 = 56 tail tokens -> ~2560 blocks, not the 4096 seen on 2026-10-14.
2. **The 2,000-token "comparable reading" floor is DISPROVEN.** gpt-oss-20b-Q8: **71.3 tok/s @ 2,677** vs
   **210 tok/s @ 50,082** — same model, 2.9x, BOTH above the floor. A single reading above a floor cannot
   serve a 26,214-token bill; it needs a two-point SLOPE like the decode axis already uses.

## 4. NEXT 3 CRITICAL STEPS (consequential order — this is the spine)

1. **CORRECT THE PARITY, PROBE FIRST.** Do NOT hand-add every local model to
   `~/.config/goose/custom_providers/maxwell_omlx.json`. The provider file is not a catalogue: every entry is a
   model an agent may ROUTE TO plus a `context_limit` the harness will TRUST for compaction. Adding an
   unmeasured model exposes an unmeasured capability and a silently-trusted window. Order: run
   `agent_context_probe` -> decide, per model, whether it is SERVED (so an entry is honest), UNEXPOSED (so the
   entries for unserved models are REMOVED), or settings-only. Then fix `served:` and `declared_equal`.
2. **T-131's prefill-bill cell, with a SLOPE.** One size-declared reading cannot bill a class. Take two points
   per model (~2.6k and ~26k) and interpolate; that is what makes a route defensible. This is also what
   un-refuses `Qwen3-Coder-30B-A3B` a route.
3. **T-185 — the derived wall, the heartbeat, and the ARTIFACT CONTRACT.** Timeouts derived from
   `config/agent_context.yaml#turn_budget`; heartbeat before/after the call; journal start row BEFORE the call;
   and a subagent that returns **path + sha256 + one decision line**, never a transcript. That is the durable
   fix for "stuck 10–30 min": the 30-minute run was a prefill-bound 4B asked to reproduce ~200 lines of stdout
   VERBATIM (BUG-869) — a task-design fault paid at hardware prices.

**Queued behind them:** BUG-873's red loop · the order-rotation probe (permute options, count flips) ·
BUG-871's residual class→role home · a `market-research` recipe (assembly, not invention: declared sources from
`config/intake_sources.yaml`, fetch ladder RSS -> Data API -> transcript, provenance-stamped table, `UNVERIFIED`
where unreachable, artifact-not-transcript) · the class→role binding.

## 5. THE VIDEO, AND WHY THE ANYJEV VERDICT FLIPPED

Video `hJz7zi17mXA` ("Nokia Just Released a Free Jev Alternative"), transcript obtained by driving the MCP
server directly. Independent replication on Qwen ~8B: **order-flip rate raw = 4% (20/500), L0 = 0** — the
position-bias claim REPLICATED completely (one headline read 1% satire one way, 99.8% the reverse). But:
**accuracy ~12 points BEHIND the hosted Jev**; the **sequential round lost outright (AnyJev 60% vs raw 80%)**;
**L0 does not calibrate** (error 0.3 ~ raw) and the calibrating levels need hundreds of LABELLED examples; and
the disqualifier — **the correction is estimated FROM THE BATCH, so removing a lean OVERSHOOTS when the answer
MIX changes.** A labeller whose answer depends on the surrounding batch DRIFTS BY CONSTRUCTION, which is
exactly what this project forbids. **Adopted: the order-rotation PROBE as a rail. Refused: the method.**

## 6. MANUAL STEPS FOR THE OWNER

1. **Restart Goose into a FRESH session (not a resumed one).** It is the test for BUG-873 limb (b): if the
   YouTube tools appear in a fresh session and never in a resumed one, the cause is the resumed surface.
2. **Do NOT bulk-add local models to the goose provider file.** See NEXT STEP 1 — parity is fixed by REMOVING
   dishonest entries as much as by adding honest ones.
3. `~/.profile` is FINE (a hypothesis was raised and then disproved — no edit needed).
4. **When delegating, ask for a receipt file, not a transcript** — path + digest + the one decision line.

## 7. COMMITS

`7d83b04` BUG-870 retracted + BUG-871 filed · `1b5dfee` BUG-871 fixed · `3dbff10` D-3038 register (AnyJev +
title + Hermes) · `75ea576` BUG-872 fixed + doctrine corrected · `b461306`/`3f39dcd` receipts ·
`67adf87` AnyJev revised + BUG-873 filed · plus the BUG-874 act.
