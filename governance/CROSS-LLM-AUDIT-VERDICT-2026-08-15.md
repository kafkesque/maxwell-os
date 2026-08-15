# Cross-LLM Audit Verdict — 2026-08-15

> **🔁 RE-ADJUDICATION (same day, follow-on session):** §2's five independent findings were re-derived
> from raw JSON. **X1 = NOT contaminated** (cross-model consensus; gpt-oss never sole driver),
> **X2 = depth is ~98% post-relabel (not 72%)** — the "quality gap" was a pre-relabel-gold artifact,
> **X5 = T1.1 ≈ 39h (not 142h)** — 12,964 is the total cluster count, not FBs. X7 (C12) implemented.
> See `DECISION-LOG.md` D2364/D2365 + `governance/buglog.md` top. The corrective net is: the S4 depth
> path is healthy, and the 142h/72% figures that anchored this audit were both stale.

> **Inputs audited:** `temp/gemini003.md`, `temp/claude0013.md`, `temp/chatgpt0013.md`
> **Method:** every numeric claim re-checked against raw benchmark JSON; every code-location
> claim re-read from source; every "verified" flag re-derived. Nothing taken on faith.
> **Video:** "RLM vs LLM Agents: Why This Repo Hit 16K Stars" (Prime Intellect / Prime Agent, Bitwise AI).
>
> **Headline:** Claude0013 and ChatGPT0013 are high-signal and materially accurate.
> Gemini003 is low-signal: one genuine catch (C12 hardcoded sets) buried under fabricated
> precision (1,165 chars, 5s/FB, 142h→30h). None of the three caught five real
> drift/contamination issues that this audit surfaced independently.

---

## 1. Claim-by-claim verification

### 1.1 ChatGPT0013 — 9/10 materially verified, 1 hypothesis, 0 fatal errors

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| C1 | D2363 = commit `d75cbdf`; merged = 32.29s median, +7.2s depth = 39.5s/FB ≈ 142h | ✅ **VERIFIED** | `git log` head = `d75cbdf`. `governance/s4_merged_production_benchmark.json` matches exactly. |
| C2 | `merged_call_enabled=true`, `batch_enabled=false`, `depth_frugal_enabled=false` | ✅ **VERIFIED** | `config/pipeline_config.yaml:192/194/204`. |
| C3 | `depth` is in merged prompt but discarded (overridden by focused call) | ✅ **VERIFIED** (with caveat) | `stage4_merged_call.py:96-97` lists `depth`; `stage4_merge.py:1147-1148` "depth intentionally NOT checked… overridden"; `:1230-1266` overrides. **Caveat:** fallback at `:1257-1258` uses merged `depth` only if `depth_focused_classification=false` — coupling risk the LLMs missed (see §3.4). |
| C4 | `depth_max_tokens` now 1024; fail-closed `classify_depth_focused()` | ✅ **VERIFIED** | `config:198` = 1024; `stage4_merged_call.py:281/318/626` raise `DepthClassificationError`. |
| C5 | Zero parallelism in `stage4_merge.py` (no ThreadPool/max_workers) | ✅ **VERIFIED** | `grep ThreadPool\|max_workers\|asyncio\|Executor` → **no matches**. |
| C6 | Speculative decoding has no gpt-oss draft model | ✅ **VERIFIED** | `pipeline/providers/mlx_provider.py:14-16` pairs only Qwen3-Coder→Qwen2.5-0.5B and Gemma-4-E4B→Gemma-2-2B. No gpt-oss entry. |
| C7 | Frugal benchmark n≤12, `random.seed(42)`, ≤3/class | ✅ **VERIFIED** | `tools/benchmark_s4_depth_frugal.py:91` `seed(42)`, `:97` `min(len,3)`, 4 classes. |
| C8 | Batch depth: 75% parity, correctly disabled | ✅ **VERIFIED** | `s4_bottleneck_ab_test.json`: A=75%, B=75%, parity=75%, gate fail. |
| C9 | `thinking_budget:null` + `enable_thinking:false` present | ✅ **VERIFIED** | `config:92-93`. |
| C10 | Split CRIBS from classification (architectural) | ⚠️ **HYPOTHESIS** | Correctly self-labeled "hypothetical, do not use as estimate". |

**ChatGPT blindspots (see §3 for full list):** missed the 72% (n=50) vs 75% (n=8) depth-accuracy
drift; missed the golden-relabel circularity risk (§3.1); overstates "zero-semantic-waste" for
removing `depth` (attention redistribution across the other 9 fields is unmeasured).

### 1.2 Claude0013 — 7/7 verified, strongest of the three

| Claim | Verdict | Evidence |
|---|---|---|
| D2363 numbers recomputed independently (39.49×12964/3600=142.24h) | ✅ **VERIFIED** | Correct; and it re-derived rather than trust the field. |
| M1 fail-closed depth, M2 1024 tokens, M3 `source_segments`, M4 `is_summary` | ✅ **ALL VERIFIED** | `stage4_merged_call.py` + `stage6_commit.py:97/116/245/342/403/422`. |
| verifier/verifier_v2 rename **still open** (not rubber-stamped) | ✅ **VERIFIED** | `config/pipeline_config.yaml:84/94` still literally `verifier:`/`verifier_v2:` with `MISNAMED` comments (D2340). |
| n=6 thin; 2.4× spread 30.13–71.94s; cold-reload outlier concern | ✅ **VERIFIED** | `s4_merged_production_benchmark.json` `times_secs` range. |
| estimate-revision trend 26h(D2253)→90h(D2362)→142h(D2363) | ✅ **VERIFIED** | DECISION-LOG D2253/D2362/D2363 all present. |
| depth-bias relabel 12 domain→cross-domain (+1 reverse) = 13 of 14 | ✅ **VERIFIED** | D2363 text: "3-model vote on 14 disputed → relabeled 13 (12 domain→cross-domain, 1 reverse)". |

**Claude's only weakness:** it asserts "removing `depth` has no accuracy cost" — a claim, not a
measurement (it does hedge with "I can't tell you the exact seconds saved without measuring").

### 1.3 Gemini003 — 1 genuine catch, 3 fabrications, rest overlap

| Claim | Verdict |
|---|---|
| C12: hardcoded `business_signals`/`design_signals`/`system_signals`/`academic_signals` sets | ✅ **GENUINE CATCH** — `stage4_merge.py:1328-1337` + `temporal_scope` keyword list `:1317-1322` + `universal_signals` `stage4_merged_call.py:241`. Real C12 violations. |
| "~1,165 characters of reasoning before 1-token label" | ❌ **FABRICATED PRECISION** — no source for 1,165; directionally true (gpt-oss is a reasoning model) but the number is invented. |
| FrugalGPT: gemma → ~5s/FB, "142h→30h" | ❌ **REFUTED BY EMPIRICAL RUN** — `s4_depth_frugal_benchmark.json`: gemma avg 11.17s (65.6s cold-load), speedup **0.9×**, accuracy 62.5%, gate FAIL. The 5s/30h figure contradicts the repo's own committed benchmark. |
| Linear-probe embedding classifier <10ms | ⚠️ **OVERSTATED** — plausible research direction, but depth is ontological scope (physicist-chef-poet test); no evidence a bge-m3 linear probe captures it. Confidence ≠ evidence. |
| Resume "zero-overlap detection" needs SHA-256 manifest | ⚠️ **VAGUE** — repo has fail-closed JSONL self-check (BUG-106/D2343), but no run-scoped config-hash manifest. Direction real, phrasing mischaracterizes the existing mechanism. |
| Error telemetry for `DepthClassificationError` | ⚠️ **PARTIALLY REDUNDANT** — `stage4_merge.py` already increments `classification_errors` + `max_failed_ratio` gate. |

---

## 2. My independent audit — gaps, blindspots, conflicts, drift, contamination

> These are the things **all three LLMs missed**. They are the highest-value output of this audit.

### 2.1 🔴 CONTAMINATION — D2363 golden-relabel may be circular (HIGHEST priority)

D2363 relabeled 13 golden FBs via a "3-model vote (qwen + gemma + gptoss)" — **gpt-oss is the
classifier those gold labels now grade.** The relabel direction (12× domain→cross-domain) is
**exactly** gpt-oss's measured bias: in `s4_depth_d2359_gptoss_production_verify.json` (n=50),
nearly every `gold=domain` row is predicted `cross-domain` by gpt-oss. If the vote was 3-way and
gpt-oss leaned "cross-domain", the relabel may have **baked gpt-oss's over-assignment bias into the
golden set**, inflating its future accuracy. This is a potential R5/verifier-independence violation.
**Action:** audit the 14 disputed rows' per-model votes; confirm the relabel wasn't gpt-oss-led
before trusting any post-relabel accuracy number.

### 2.2 🟠 DRIFT — MTR PLUGINS table contradicts this session's own finding

`MASTER-TASK-REGISTER.md` tail still recommends `orchestrator | Enable`, but this session already
established **orchestrator is phantom** (absent from the real `Extensionmanager.searchAvailableExtensions()`
registry; a stale bundled `config.yaml` entry only). The MTR also still lists `puppeteer` (known
"failed to add") and `memory/chatrecall/summarize` as "Enable" without the later qualification.
**Action:** correct the PLUGINS table (see §6 task list).

### 2.3 🟠 QUALITY GAP — production depth accuracy is 72–75%, NOT 90%

- `s4_depth_d2359_gptoss_production_verify.json` (n=50): **accuracy 0.72**.
- A/B (n=8) and frugal (n=8): **0.75**.
- Governance/summary quote "75%" but the n=50 production number is **72%** — a 3-point unacknowledged drift.

The 90% gate is applied **only** to model *replacement* (S4-B). The **incumbent** gpt-oss depth
path runs at ~72-75% with **no gate** — it is the default (`depth_focused_classification: true`).
Optimizing the *speed* of a 72%-accurate classifier is premature: the quality gap is the higher
risk. **Action:** investigate why depth accuracy is 72% (fail-closed is silent-safety, not accuracy);
do not treat "speed" as the only S4 problem.

### 2.4 🟠 COUPLING — removing `depth` from merged call has a hidden fallback dependency

ChatGPT/Claude frame "remove `depth`" as zero-cost. It is **only** zero-cost while
`depth_focused_classification=true`. If that flag is ever toggled off (a config change, not a code
change), `stage4_merge.py:1257-1258` falls back to `raw_depth` from the merged call — which would
then be **empty**. Removing the field silently breaks the fallback path. **Action:** if removing
`depth`, also remove/handle the fallback branch so the dependency is explicit.

### 2.5 🟠 METHODOLOGY — S4-B "refuted" verdict is cold-load-skewed

`s4_depth_frugal_benchmark.json` shows gemma's **first call = 65.6s** (cold model load), skewing
gemma avg to 11.17s (slower than gpt-oss 10.05s) and speedup to 0.9×. The "S4-B refuted" conclusion
rests partly on an **unwarmed** benchmark — the same cold-reload tax already documented in
D2301/D2348. The *accuracy* refutation (62.5% < 90%) stands, but the *speed* portion of the verdict
is not measured. **Action:** re-run with a warmup call before finalizing S4-B speed claims.

### 2.6 🟠 HEADLINE UNCERTAINTY — 142h rests on n=6 AND a possibly-wrong denominator

- n=6 with a 2.4× spread (30.13–71.94s) is statistically thin for a 6–8 day commitment (Claude flagged this; correct).
- **Nobody questioned the 12,964 denominator.** 12,964 is the **S1.5 cluster count**, alongside
  "35,239 singletons" (`master_evaluation_prompt.md:27`). T1.1 is **principle-only** (D2345) and
  filters non-principle clusters (PT/PI/GE/TI). 142h assumes *all* 12,964 clusters → FBs, which
  over-counts. The true FB count is unmeasured. **Action:** compute the actual principle-only FB
  count before treating 142h as a scheduling input.

---

## 3. Video adaptation analysis — "RLM vs LLM Agents" (Prime Agent)

**What the video is:** a teardown of Prime Intellect's "Prime Agent" — skills as importable Python
packages (not SKILL.md prose), a persistent IPython kernel as the only built-in tool, subagents as
`await rlm(...)`, `create_skill`/`/refine` self-editing against an immutable base prompt, and a
"receipts" section showing **30.2% official ARC-AGI-3 vs 95.5% self-reported** (inflated claim).
Verdict: *"steal the idea, audition the agent."*

### Worth ADOPTING (the patterns, mapped to Maxwell)

| Video concept | Maxwell mapping | Verdict |
|---|---|---|
| **Skills as importable code, not prose** | Maxwell's skill orchestrator (FOUNDATION-BLOCK-TO-SKILL-SPEC.md) + `ToolInstruction` (D2344, schema-only, deferred). Insight: a *skill* should be executable (importable, versioned, testable), not a readable FB. Aligns C27 (protocols first). | **ADOPT pattern** post-T1.1 |
| **Persistent kernel state surviving compaction** | Directly solves the 32K OMLX context-compaction problem (§session): serialize agent working state to a durable store (SQLite, already present at stage6) that reloads post-compaction, instead of losing it. | **ADOPT** — high value |
| **Immutable base prompt + self-editing skills** | Maps 1:1 to CONSTITUTION.md (immutable) + skills (mutable, but re-verifiable). Reinforces existing protected-files model. | **ADOPT** — already partial |
| **Subagents as first-class async primitives** | Maps to `delegate_omlx()` / `delegate_local` (BUG-063): local subagents should be awaitable primitives with real FS access, not Deno-sandboxed. | **ADOPT** — already partial |
| **"Receipts" discipline (benchmark honesty)** | Reinforces Maxwell's existing ethos: R5 (Generator≠Verifier), C16 (no silent errors), verify-don't-assume. Maxwell *already* commits raw benchmark JSON — the video validates this exact practice. | **REINFORCE** |

### Worth DEFERRING / REJECTING

| Video concept | Verdict |
|---|---|
| RLM (Reinforcement Learning from Machines) training | **REJECT** — out of scope (no RL infra; C1 local cost; the video itself shows the RLM headline is inflated: 30.2% official vs 95.5% claimed). |
| "IPython kernel as the ONLY tool" purism | **REJECT** — Maxwell needs its full pipeline (shell, FS, MCP). Do not adopt single-tool minimalism. |
| The 95.5% self-reported number | **IGNORE** — unreproducible; never benchmark against it. |

**Net video verdict:** the meta-lesson is the most valuable part — **Maxwell's existing
"verify-don't-assume, commit the raw benchmark" discipline is exactly the antidote to the
self-reported-95.5% pathology the video exposes.** Adopt the skills-as-code and
state-survives-compaction patterns; reject the RLM/headline claims.

---

## 4. Ultimate constructive verdict

| Item | Adopt / Implement / Defer | Rationale |
|---|---|---|
| Fix MTR PLUGINS contradiction (orchestrator phantom) | **ADOPT NOW** | doc-only, prevents future confusion; zero risk |
| C12: extract hardcoded signal sets → YAML | **ADOPT NOW** | Gemini's one real catch; ~1h |
| Audit D2363 golden relabel for circularity (§2.1) | **IMPLEMENT FIRST** | contamination risk poisons every downstream accuracy number |
| Investigate 72% depth accuracy (§2.3) | **IMPLEMENT** | quality > speed; do before any speed work |
| Fix S4-B benchmark (warm gemma, isolate cold-load) | **IMPLEMENT** | refutation's speed half is unmeasured |
| `thinking_budget` sweep (null/256/384/512) on merged call | **IMPLEMENT** | cheap, measurable; config already wired |
| Concurrency benchmark (1/2/3 workers) | **IMPLEMENT (measure only)** | zero parallelism verified; but OMLX may serialize |
| Remove `depth` from merged call — gated + fix fallback | **IMPLEMENT (gated)** | real waste, but needs parity gate + §2.4 fix |
| Re-verify S4-A at n≥30 (2/8 flips unresolved) | **IMPLEMENT** | speedup verified; semantic equivalence NOT |
| Split CRIBS from classification | **DEFER** | post-T1.1 architectural |
| FrugalGPT cascade (accept-easy→hard) | **DEFER** | after §2.5 methodology fixed |
| Speculative decoding for gpt-oss | **DEFER** | no compatible draft model exists (verified) |
| Distillation (S4-C) | **DEFER** | post-T1.1 |
| Linear-probe embedding classifier | **DEFER** | unproven for ontological depth |
| Skills-as-code + state-survives-compaction (video) | **ADOPT pattern** | post-T1.1 skill orchestrator |
| RLM training (video) | **REJECT** | out of scope + inflated headline |

---

## 5. Aggregated task list (most critical first)

> Full detail + effort + status in `MASTER-TASK-REGISTER.md` §"CROSS-LLM AUDIT 2026-08-15".

1. **[CONTAMINATION]** Verify D2363 golden-relabel was not gpt-oss-led (R5/verifier-independence).
2. **[QUALITY]** Root-cause the 72% depth accuracy (n=50) — the incumbent classifier is weak, not just slow.
3. **[DRIFT]** Correct MTR PLUGINS table (orchestrator phantom, puppeteer, memory/chatrecall/summarize).
4. **[METHODOLOGY]** Re-run S4-B frugal benchmark with gemma warmup (isolate the 65.6s cold-load).
5. **[HEADLINE]** Compute the real principle-only FB count (12,964 clusters ≠ FBs; 35,239 singletons).
6. **[METHODOLOGY]** Re-verify S4-A at n≥30 (2/8 decision flips = semantic equivalence unresolved).
7. **[C12]** Extract hardcoded `*_signals` sets + `temporal_scope` keywords + `universal_signals` → YAML.
8. **[PERF]** Sweep `thinking_budget` on the merged call (null/256/384/512).
9. **[PERF]** Concurrency benchmark (1/2/3 workers) — measure, don't assume.
10. **[PERF]** Remove `depth` from merged call — gated, and fix the `:1257-1258` fallback coupling.
11. **[DEFER]** Split CRIBS/classification; FrugalGPT cascade; speculative decoding; distillation.
12. **[VIDEO]** Adopt skills-as-code + state-survives-compaction patterns into the post-T1.1 skill orchestrator.

---

## 6. Files touched this audit

- `governance/CROSS-LLM-AUDIT-VERDICT-2026-08-15.md` (this doc)
- `MASTER-TASK-REGISTER.md` (new section + PLUGINS correction)
- `governance/SESSION-HANDOFF-2026-08-15.md` (handoff)
