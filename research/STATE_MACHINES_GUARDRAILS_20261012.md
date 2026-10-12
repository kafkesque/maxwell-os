# State Machines as the Maxwell OS Determinism Backbone

**Status:** RECOMMENDATION (owner gate) · 2026-10-12
**Authority lineage:** D-2947 (deterministic provenance), D-343 (content_type never LLM-classified), R5 (generator ≠ verifier), C12 (config-first), C28 (quality-tiered).

## Verdict

**YES — adopt explicit state machines, but as the determinism *core* the repo already embodies, not as a new dependency.** The thesis the user surfaced (XState/Stately, "determinism in the core, non-determinism at the edges") is precisely what Maxwell OS has been converging on: closed-vocabulary ontologies, deterministic routers, known-answer control rails. This recommendation *formalizes and names* the pattern; it does not re-platform.

## Market grounding (2026-10-12)

| Source | Thesis | Maxwell OS mapping |
|---|---|---|
| David Khourshid (XState/Stately), Agent Conf 2026 | "Determinism in the core, non-determinism at the edges." A state machine is *mathematically* incapable of an invalid state/transition. Every agentic loop fits the `while not done: event → next_state → effect` pattern. Actor model + state machines are the two principles everything reduces to. | The whole pipeline + serving gate + MCP harness are already this loop. |
| "Constrained Agency" (zomeru.dev, 2026) | Deterministic state machines govern high-level flow; LLM does reasoning *within* a step. | stage0→6 = deterministic flow; stage2/stage5 LLM = reasoning within steps. |
| Five deterministic rings (pablogodoy.com, 2026) | flow, MCP contract, ownership gates, a **pure state machine**, idempotent writes — between an LLM and real money. | MCP surface (4 tools), D-2898 owner gate, serving_gate pure functions, atomic writes (C6). |
| OWASP 2026 Agent Control Standard | "Deterministic authorization for consequential agent action" — not "what did the model say" but "what did the system allow." | serving_gate derive_status/derive_epistemic_status is already deterministic authorization. |
| Code-level guardrails (n1n.ai, 2026) | System prompts fail to prevent hallucinated task completion; code-level pre-delivery checks succeed. | BUG-721/BUG-333: LLM code-review verdicts rubber-stamp/fabricate → must be replaced by deterministic diff-citation guard. |

## What to actually do (C12, C21, C28 — config-first, swappable, no bloat)

Do **NOT** import XState/LangGraph (wrong stack: JS/vendor-lock, violates C2/C4/C21). Maxwell already has the correct primitive: **pure-function decision procedures + YAML transition/closed-vocabulary tables + known-answer controls** (`check_*.py --selftest`). Formalize into a tiny `pipeline/fsm.py`:

1. `pipeline/fsm.py` — a ~50-line deterministic FSM core: `next_state(state, event, table) -> state` as a pure function, transition tables read from `config/*.yaml` (C12), invalid event → defined `reject`/`compensate` state (never silent, C16).
2. Re-express the existing decision procedures as *declared* FSMs (no behavior change, pure naming/visibility): `serving_gate.derive_status/derive_epistemic_status`, `content_types.reroute_content_type`, `content_type_decision_procedure`, pending `pipeline/lifecycle.py` (A3 promote/retire/stable).
3. **Sandbox-before-real** (the user's ask): every new decision rule ships as `config/<rule>.yaml` transition table + `check_<rule>.py --selftest` known-answer controls **before** it is wired into any real script/config path. LLM output is *advisory only* and only accepted if it passes the deterministic table (this is already the R5 + BUG-721 pattern; make it structural).

## Where it pays off (ranked by drift/slop risk)

1. **Serving gate / epistemic status** — already deterministic; declare it (highest correctness surface).
2. **Code-review + MCP `delegate_local`** — BUG-721 guard: reject any LLM review verdict that does not cite the diff/file hash (deterministic). **This is the single highest-value place; gemma/Qwen reviews are guardrail-shaped failures, not model-shaped.**
3. **A3 lifecycle gate** — promote/retire/stable as deterministic proposal engine (rank-with-interval), owner-gated per D-2898.
4. **Skill orchestration / cross-examination fusion** — Layer-2 bridge (actor model = skills/agents; state machine = orchestration).
5. **Retro re-stamp + provenance stamping** — deterministic `reroute_content_type` + `traceability_of` already FSMs.

## Cost conclusion

Determinism **is** better than any local LLM *for closed-rule decisions* (D-343 already measured −2.98pp vs baseline for deterministic content_type). The LLM remains necessary only at the *edges* (extraction, probe, summarization-with-source). "Try a better local LLM" (option a) is **not** the fix because the observed failures are guardrail-shaped (BUG-333 rubber-stamp, BUG-721 fabricated verdict), not model-shaped. **Recommendation: (c) both, with determinism as the acceptance gate and LLM as advisory — and now formalize the determinism as explicit state machines.**

## Next critical steps (unblocked, ordered)

1. Commit the BUG-712 CSV fix (already written, verified 147 rows, proper quoting).
2. `pipeline/fsm.py` + re-declare the 3 existing decision procedures as FSMs (no behavior change) — seed of the formalization.
3. Deterministic BUG-721 diff-citation guard on `delegate_local`/review path.
4. A1 `compile_context` (pydantic compiled payload) → A3 lifecycle deterministic engine.
5. D-2924 growth_edge calibration (mint golden, measure kappa on 25 GE rows).
