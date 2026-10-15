# ORCHESTRATION ECONOMY — 2026-10-15

> The delegation economy, MEASURED; the route graph, DECLARED; the loops, BOUNDED. Authority:
> D-3023 (economy), D-3024 (routing), D-3025 (loops). New instrument: pipeline/delegation_economy.py
> (14/14 selftest). New home: config/delegation_economy.yaml. New bug: BUG-832.

## 1. The measurement that did not exist before this turn

| tier | calls | input tokens | output tokens | cost |
|---|---|---|---|---|
| local | 379 | 3,667,410 | 144,968 | $0.00 |
| cloud | 32,851 | 3,981,322,921 | 57,008,294 | $105.42 (estimated) |
| unclassified | 1 | 156,098,139 | 1,249,089 | $7.35 (carried_forward) |

Ledger: 33,231 rows, 2026-08-28 to 2026-10-15; 1,384 further rows carry NO cost and are counted as
UNKNOWN, never as zero (D-2957). Local share of decided input tokens: **0.09%**. Burn: ~$2.35/day.

Two facts, in this order. FIRST, sovereignty: 99.9% of the tokens left the machine while a 3-model
local fleet sat idle — a C1/C3 drift that nobody could see because nothing measured it. SECOND, money:
$105.42 lifetime is not a crisis, which is precisely why the honest recommendation is NOT to trade the
session brain down to a 4B model. The lever is the VOLUME and the ROUTING, not the unit price.

## 2. Why progress feels slow: the register, counted

* 595 bug ids: **223 open** / 372 closed. Open by severity: 7 CRIT, 39 HIGH, 82 MED, 25 LOW and
  **66 with NO severity token** — so the register still cannot answer "which is the highest leverage"
  (T-104/BUG-757). Fixing that is a precondition of every ordering claim below.
* Discovery is running at roughly the fix rate (2026-10-15: 23 opened / 13 fixed; last 12 days: 121
  opened / 97 fixed). That is not a leaking backlog — it is an instrument-driven steady state. The
  audits keep finding REAL defects: BUG-826..832 were found in two days of wiring guards.
* 60 tasks, 49 open, and **30 of them owner-gated**. The binding constraint is not model throughput:
  it is the human word plus verification capacity per change.
* The HIDDEN-bug surface, quantified: **35 of 516 python files are named by no recipe, no config and
  no governance document** (an instrument with no caller is not a guard — T-149/BUG-482); 3 of 112
  pipeline modules and **0 of 404 scripts** expose a machine-readable check verb; 176 broad excepts
  (3 bare); 24 unguarded POSIX sites and 0 platform guards (T-106).
* The honest answer to "how many hidden bugs are there": **unknown, and the reason is structural** —
  66 open bugs cannot be ordered, and the instruments that would find more are themselves unwired.
  The measured proxy is that every guard this repo has actually WIRED found defects within a day of
  being wired. Discovery rate is a function of GUARD COVERAGE, not of search effort.

## 3. The three layers this session's decisions put in place

1. **KIND** (T0): if the answer is derivable, a deterministic script does it. A model is for
   judgement, never for arithmetic on registers.
2. **CLASS**: which agent class owns the work (config/agent_context.yaml#classes) and therefore which
   harness and model (config/engine.yaml#harnesses.jobs, D-3017), measured per class (T-131).
3. **TIER** (D-3023): the cheapest tier that can do it; a cloud call is an ESCALATION with a reason
   from a declared vocabulary, held under SHRINK-ONLY ceilings.

The router (T-156) is a **declared registry plus a deterministic resolver**. An LLM may PROPOSE a
route into temp/ and may never ASSIGN one (D-3024). This does not replace anything: it COMPOSES the
joins that already exist — config/harness_policy.yaml (where a harness is worth its place),
config/declaration_consumers.yaml (declaration to reader), config/flag_consumer_registry.yaml (flag
to consumer), config/engine.yaml#harnesses.jobs (class to harness), config/model_assignments.yaml
(role to model). A route registry that restated any of those would be the C12 defect it exists to fix.

Goose recipes and skills are therefore THIN WRAPPERS over repo entrypoints: ~/.config/goose is not
versioned, not reviewed and not governed, so a capability defined only there drifts by construction.

## 4. What may be loop-engineered, and what may not (D-3025)

A loop names its TERMINAL CONDITION, its CHECKER and its BUDGET before the first iteration.

| shape | verdict | why (measured) |
|---|---|---|
| citation read-back then one retry on another family (T-155) | ADMISSIBLE | the checker is a READER of the file, not an opinion (D-3022) |
| ladder rails, doctor tri-state verdicts | ADMISSIBLE | deterministic, and their FAIL path is proven live (BUG-826) |
| retrieval then verify, classify then verify | ADMISSIBLE | the verifier is a different family (R5) and the claim is decidable |
| prompt optimization against a fixed metric (DSPy/MIPROv2/GEPA) | ADMISSIBLE | the metric is a D-400 instrument's artifact; dspy_trainer.py exists and is UNRUN |
| multi-agent debate / self-grading loops | REFUSED | tokens without a reader — BUG-721's failure mode with a larger bill |
| a workstream whose failure is not free | REFUSED | it must run through pipeline/subagent_fanout.py (T-150) |

Graph engineering is the same rule at a coarser grain: orchestrator-workers, parallelization and
evaluator-optimizer are admissible where every edge carries a checker; the FSM core already exists
(pipeline/fsm.py, with LangGraph/XState REJECTED on the record in
research/STATE_MACHINES_GUARDRAILS_20261012.md). No framework import is proposed.

## 5. Prior art: the delta, and where it lands

The intake register already exists (governance/NOT-YET-EVALUATED-RESEARCH.md, R-01..R-13). It already
holds R-02 (structured JSON output) and R-13 (token-efficient prompt patterns) — which are two of the
items below. They must be MARKED, not duplicated (T-159).

| prior art | what it gives | attaches to |
|---|---|---|
| ALCE (Gao 2023), AttrScore, AIS (Rashkin 2021) | citation precision/recall as a METRIC, not only a refutation | D-3022, T-155 |
| Reflexion (Shinn 2023), Self-Refine (Madaan 2023), CRITIC (Gou 2023) | bounded critique loops; CRITIC critiques WITH a tool | D-3025, T-155 |
| Chain-of-Verification (Dhuliawala 2023) | decompose a claim, verify each part | citation read-back, S5 rails |
| constrained decoding: Outlines, XGrammar; and the engine's OWN guided_grammar_enabled flag | malformed JSON becomes unrepresentable | pipeline/json_fixer.py is the symptom |
| prefix/KV cache: RadixAttention (SGLang 2024), Prompt Cache (Gim 2023) | prefill becomes cheap | measured cached_tokens=0; F6/BUG-792; pipeline/omlx_cache_enable.sh (dry-run by default) |
| DSPy (Khattab 2023), MIPROv2, GEPA (2025) | prompt optimization against a metric | pipeline/dspy_trainer.py (exists, unrun) |
| Self-RAG (2023), Adaptive-RAG (2024) | retrieve only when needed | T-158 context diet, T-154 budgets |
| FrugalGPT (2023), RouteLLM (2024), Hybrid LLM (ICLR 2024) | cheap-first cascade | ADOPT the ceiling idea (D-3023); REJECT a LEARNED router for assignment (D-3024) |
| Anthropic, "Building effective agents" (2024, vendor report not peer-reviewed) | the vocabulary: routing, chaining, orchestrator-workers, evaluator-optimizer | D-3024's shape; Maxwell runs 3 of the 5 and lacked the declared routing table |
| MT-Bench / LLM-as-judge bias studies (Zheng 2023) | why a judge is not a checker | R5 + D-3022 |
| NIST AI 600-1 (2024) | documented human oversight and measured deployment | the escalation receipt + the human gate register |

## 6. Cost levers, ranked by MEASURED impact

1. **Local for bulk and for verification** — free, and the fleet carried 0.09%. A local reviewer with
   a mechanical citation reader beats a paid reviewer with no reader: the local one's fabrication was
   caught in one second (BUG-827/BUG-831).
2. **The context diet (T-158)** — the boot read is 3.96 MB (~990 k tokens) across buglog.md,
   decisions.yaml, DECISION-LOG.md, MASTER-TASK-REGISTER.md and CONTEXT_INDEX.md, and a cloud turn
   averages ~92 k input tokens (32,851 calls / 3.98 B tokens).
3. **Turn the engine's block/prefix cache on under its declared protocol** — measured cached_tokens=0,
   so every local turn re-pays its whole prompt; this is what blocks local agent loops (T-153/T-145).
4. **Constrained decoding instead of repair** — the engine already declares guided_grammar_enabled;
   a repair function is a workaround for a decoder that can be constrained.
5. **Ceilings and escalation receipts (D-3023)** — accountability first; smaller is a consequence.
6. **Keep the cloud brain where it is genuinely needed, and SAY SO (BUG-832/T-157)** — for agent_loop
   long-context reasoning the local route is refuted by measurement (gemma 0.0, Qwen3-Coder 0.0; only
   Qwen3.8-27B passes at 1.0 and its 39 tok/s prefill makes a 26214-token turn 672 s). An explicit,
   ceilinged, receipted opt-in is honest; an ambient default that silently falsifies a closed bug's
   rationale is not.

## 7. Next critical steps (ordered; actor in the last column)

| # | act | actor |
|---|---|---|
| 1 | **T-157** — census the harness homes a decision names (the reading that would have caught BUG-832) | pipeline |
| 2 | **T-156** — the capability registry plus the deterministic resolver | pipeline |
| 3 | **T-154** — bound the harness the way its class declares (BUG-828) | pipeline |
| 4 | **T-104/BUG-757** — triage the 66 unlabelled open bugs, so the register can be ordered at all | pipeline + owner |
| 5 | **T-153** — measure the resident Ornith-1.5-35B at 26214 tokens; the verdict on T-145 | pipeline |
| 6 | **T-158** — the generated state digest replaces the manual boot read | pipeline |
| 7 | **T-159** — the prior-art delta into the intake register, marked where it duplicates | pipeline |
| 8 | **BUG-832** — decide the session brain; file ~/.config/goose/config.yaml line 311 | OWNER |
| 9 | **T-145** — fetch Edge0, or accept T-153 as the release test (no action keeps the deferral) | OWNER |
| 10 | **BUG-829** — Zed's agent.default_model is a cloud provider; bind it or declare the opt-in (~/.config/zed/settings.json) | OWNER |
| 11 | **T-146 residual** — open Zed's agent panel once and confirm pi-acp resolves | OWNER |
| 12 | **T-144 residual** — one write-capable harness job, read by the owner, once T-154 lands | OWNER |

## 8. Refused, with reasons (so the next session does not re-litigate)

* **LLM-as-router for assignment** — unauditable, and the measured failure mode is silent (BUG-827).
  An LLM may propose; the resolver assigns (D-3024).
* **Multi-agent debate** — tokens without a reader (D-3025).
* **Importing LangGraph/XState or any agent framework** — the repo has the primitive (pipeline/fsm.py)
  and a recorded rejection (C2/C4/C21).
* **A learned cost router (RouteLLM-style)** — the ceiling plus a receipt answers the same question
  where a learned policy would answer it unaccountably.
* **A second dashboard for cost** — pipeline/delegation_economy.py is the ONE reader (D-3023).
* **Re-optimizing the S0-S6 pipeline for cost** — it is already $0 by construction; the leak was
  never there.
