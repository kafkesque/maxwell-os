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
| BUG-875 | FIXED | **A first-party import name resolved OUTSIDE the tree.** `import scripts` landed in `site-packages/scripts/__init__.py` (a top-level REGULAR package installed by **skillopt-0.1.0**), because PEP 420 consults a namespace portion only when no regular package of that name exists anywhere on the path — so `sys.path.insert(0, REPO_ROOT)` could not win. `python3 scripts/delegate_journal.py --selftest` (a **fatal** rail on the ladder) exited 1 on the interpreter an agent session uses and 0 under another: **one command, two verdicts**, and the ONE record a delegated run leaves behind could not be written. Fix: `scripts/__init__.py` + a RAIL 0 clause that DERIVES the first-party names, fails closed on any that resolve outside, and **NAMES the capturing distribution** (RED naming skillopt, then GREEN). 16 import sites repaired; 14/14 tests now pass. |
| BUG-873 · limb (b) | MEASURED | The fresh-session test the owner ran: the `youtubetranscript` namespace **IS** in this session's surface (all four tools) and `getTranscript` on `hJz7zi17mXA` returned the real video. Two-point reading with the resumed session's 40-functions-and-no-YouTube-tool: the fault is in the **surface a session receives**, not the extension/server/PATH. Candidates (a) and (b) both survive; (c) is not this instance's cause. **The resumed half is still the owner's to measure.** See §6.1. |

## 1a. SPINE UPDATE — 2026-10-16, SECOND SITTING (append-only; nothing above is rewritten)

**1. The trace can be kept again, and that came first for a reason.** `scripts/delegate_journal.py` — the ONE
command the standing delegation rule requires before and after any delegated run — **could not run at all** on
`python3` as an agent session finds it (BUG-875, fixed). Every delegation in this repository was therefore
unreceipted by construction: `status` reported `4 row(s), 2 run(s), 0 open` while the writer was dead, and the
same declared command read GREEN under `/usr/local/bin/python3` because that interpreter had no `skillopt`
package capturing the name `scripts`. **This was not a detour from NEXT STEP 1; it was its precondition** — the
parity correction below is a sequence of *delegated measurements*, and none of them could be recorded.

**2. What the rule now is when you delegate.** Ask for the **ready receipt**: if the task has a declared home for
its evidence, name THAT file as the artifact (the R5 review's receipt is `governance/r5_review_gate.jsonl`,
written by the declared gate — not a new transcript-shaped file in `temp/`). Declare `--may-write` as the
receipt's real home, or `none` when the receipt already had a home before the run.

**3. The delegated-routing question the owner asked, answered with evidence rather than prose.**
`config/model_assignments.yaml` is **NOT** the right home for "which local LLM for which task", and neither is
the `delegate_rules` block in the agent file. On disk today the fact already lives in three declared places, and
`config/capability_registry.yaml` says so in its own header: *"Who runs what therefore lived in prose (a
CLAUDE.md delegate_rules block, ADVISORY)"*. The homes are: (i) **which MODEL for which AXIS** →
`config/model_assignments.yaml#harness_roles` (already there: model + basis + never_for); (ii) **which ROUTE for
which TASK, at which cost tier** → `config/capability_registry.yaml` (D-3024/T-156) with
`scripts/resolve_route.py` as its ONE deterministic reader; (iii) **the tier vocabulary** →
`config/delegation_economy.yaml` (T0 script / T1 local / T2 cloud, escalation reasons). Adding a fourth list to
`model_assignments.yaml` would create the second home C12 forbids. **The open work is a face, not a list:** render
the delegate table FROM those three declarations and have `resolve_route.py --check` refuse an unroutable
pairing — after the parity in NEXT STEP 1 makes "SERVED" true again.

---

## 1b. SPINE UPDATE — 2026-10-17, THIRD SITTING (append-only; nothing above is rewritten)

**BUG-873 LIMB (b) IS CLOSED BY MEASUREMENT, FROM BYTES, WITH NO OWNER STEP** — and the answer is neither
candidate as filed. Full reading in the buglog; the load-bearing facts:

| what | reading |
|---|---|
| the store | `~/.local/share/goose/sessions/sessions.db` — one row per session; `sessions.extension_data` = the surface THAT session was given; VERIFIED enabled-only (`pdfreader: enabled:false` is absent from it, every enabled extension present) |
| the long session `20261012_1` | born 10-12 11:22 local, 13,036 msgs, **last written 10-16 23:32 local** — snapshot carries NO youtube extension (instr 0), and its own reasoning at 10-16 23:08:13 local says *"this session's tool surface includes `Fetch.fetch`, but NO youtubetranscript tool, even though the extension is ON in the app config"* |
| the fresh session `20261016_10` | born 10-16 23:42 local — extension in snapshot at byte 2244, all four tools bound |
| the transition | every session born from **10-13 11:31 local** onward carries it; no earlier one does |
| candidate (a) "predates the 13:16 write" | **DISPROVEN.** The `extensions:` block is BYTE-IDENTICAL to the **10-15 21:08** backup (`diff` empty; declared there, absent from the 09-21 backup). The write that landed at 13:16 changed exactly one key: `GOOSE_THINKING_EFFORT: high → medium`. |
| candidate (b) "a resumed session keeps its surface" | **PROVEN.** The long session lived ACROSS the enabling write, was still being written 10 min before this sitting, and never gained the tool. |
| still owed | the second limb: break `cmd` deliberately and confirm the fault is REPORTED rather than silent. |
| **second limb — MEASURED 2026-10-17, two-sided, sandboxed** | `goose run --with-extension '/nonexistent/uvx ...'` (local model, live config untouched): the harness **DOES** name the failure — `Warning: Failed to start extension 'uvx' (IO error: No such file or directory (os error 2)), continuing without it` + a debug hint — so "silent failure" is **DISPROVEN as stated** and replaced by the proven narrower one: **the report goes to a terminal banner at session start; the SESSION is never told, and "continuing without it" presents the loss as normal operation.** |
| a LIVE instance, same run | the control run exposed the **Reddit** extension failing in every session today (`ModuleNotFoundError: An HTTP transport library needs to be installed.`) while `reddit` is `enabled: true` (config line 253) and present in the snapshot: surface promised it, tools absent, one scroll-away line as the only report. |
| surface parity, whole set | 19 extensions `enabled: true`; 18 in the current snapshot; **`scheduler` absent — NAMED, not judged** (a non-tool extension need not appear; one check owed). |

**THE RULE THIS BUYS — and it belongs in the loader, not in prose: a config write is NOT LIVE until a NEW
session starts.** A resumed or continued session keeps the surface it was born with. Nothing in the harness
says so, which is why the owner had to ask three times.

**BUG-874's PROBE IS NOW RUN (this handoff's NEXT STEP 1 said "probe first"), measured 2026-10-17:**

| set | members |
|---|---|
| **SERVED** — engine pool on `:11435` (authenticated) | Phi-4-mini-instruct-8bit · Qwen3-Coder-30B-A3B-Instruct-MLX-4bit · Qwen3.8-27B-MLX-4bit · gemma-4-E4B-it-MLX-4bit · gpt-oss-20b-MXFP4-Q8 · **MiniCPM5-2B-MLX** · **Ornith-1.5-35B-A3B-REAP-19B** · **Ornith-1.5-9B-MLX-8bit** |
| **GOOSE-TOLD** — `custom_providers/maxwell_omlx.json` | Phi-4-mini · Qwen3-Coder-30B · Qwen3.8-27B · gemma-4-E4B · gpt-oss-20b-Q8 · **gpt-oss-20b-MXFP4-Q4** · **Qwen3.5-9B-4bit** · **gemma-4-31B-it-MLX-8bit** |
| the diff | **3 served-but-never-offered** (MiniCPM5-2B — the engine's own `default_model` — plus both Ornith models) vs **3 offered-but-never-served** (a delegate pointed at gpt-oss-20b-Q4, Qwen3.5-9B-4bit or gemma-4-31B-8bit asks a server that cannot answer). Engine pool at reading: `model_count 8, loaded_count 6, current 48.6 GB / ceiling 65.2 GB`. |

NEXT STEP 1's probe half is therefore **DONE**: the correction is now a pure config act (REMOVE the 3 ghosts,
ADD the 3 invisible), deterministic and LLM-free, and `harness_roles` must be re-read against the SERVED list
rather than against prose. NEXT STEP 2 (T-131 prefill-bill with a slope) is untouched.

**THE KNOWLEDGE LAYER, MEASURED — and the one gap that blocks "advisory by default".** The corpus is real and
queryable: `knowledge pipeline/maxwell.db` (209 MB, the DECLARED live run DB — `config/db_torn_upload_guard.yaml`,
`#anchor_family.store`, `capability_registry`) holds **7,640 FBs** with FTS (`fbs_fts`) AND sqlite-vec
(`vec_fbs`, `vec_fbs_ctx`). Entrypoints exist: `pipeline/retrieve.py` (69 KB) with benchmark + evaluator +
goldens (`pipeline/retrieval_benchmark.py`, `pipeline/retrieval_evaluator.py`, `governance/golden_reanchor_*`)
and `pipeline/query.py` (read / --stats / --by-macro). **THE GAP: `just ask` IS NOT GROUNDED.** It runs
`pipeline/oneshot_ask.py` (102 lines) — a bare one-shot model call that imports only `OMLX_API_KEY`, touches no
DB and calls no retriever. Until `ask` retrieves, cites and REFUSES when the corpus is silent, no everyday
decision can be grounded in the knowledge layer, and a recipe that cites no FB is prose. Also named:
`data/maxwell.db` (128 KB, 19 July-era FBs) is a stray second home that no declaration names.

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

## 1c. SPINE UPDATE - 2026-10-17, FOURTH SITTING (append-only; nothing above is rewritten)

**THE THREE MANUAL STEPS ARE DONE, and each one left a reading.**
1. **BUG-874's parity act, executed through MEASUREMENT, not through a typed list.**
   `scripts/agent_context_probe.py` read `FAIL agent-context: 6 declared fault(s)` (3 served-but-undeclared:
   MiniCPM5-2B-MLX, Ornith-1.5-35B-A3B-REAP-19B, Ornith-1.5-9B-MLX-8bit; 3 declared-but-never-served:
   Qwen3.5-9B-4bit, gemma-4-31B-it-MLX-8bit, gpt-oss-20b-MXFP4-Q4). The goose provider file's `#models` was then
   RE-DERIVED from the live `/v1/models` reading and now holds exactly the EIGHT SERVED models with their served
   windows; the SAME probe prints `ok agent-context: the four layers agree`. **None of the three ghost models is
   present on this machine** (no `~/.omlx/models` directory, no hub repo; `Qwen3.5-9B-4bit` exists only as
   `Qwen3.5-9B-MLX-4bit/-8bit`, downloaded and never served). Backups: `maxwell_omlx.json.bak.20261017003537`.
   The residual is NAMED: the model list has no declared writer (`apply_provider_flip.py` binds the provider and
   the agent-loop model but does not render `#models`), so a writer is owed and the probe is the current guard.
2. **AGENTS.md now carries the two harness facts** (measured, with the reading that re-takes each) plus the rule
   that an agent must read the session's own surface instead of assuming it: a config write is not live until a
   NEW session starts; a dead extension reports to the terminal and never to the session.
3. **The extension sweep, whole set** (receipt `temp/plugin_health_20261017.md/.json`): 26 declared, 19 enabled,
   **18 WORKING / 3 DEAD / 4 NOT-A-TOOL-EXTENSION / 1 UNTESTABLE**. Both repairs were MEASURED before being
   written: `reddit` needs `--with httpx` (2 tools), `pdfreader` needs `--with mcp<2` (1 tool, left DISABLED -
   available on demand, not resident). `scheduler` is the third dead one and the worst kind: an ENABLED bundled
   platform extension that contributes ZERO tools and emits NO error, absent from the surface in 12/12 sessions -
   NAMED, not flipped, because what it could contribute to a CLI harness is unmeasured.

**THE D-2549 MEASUREMENT EXISTS AND IT REFUTED TWO DECLARED BASES.** `scripts/measure_subagent_loop.py` (new;
served set, base_url, key and the 90 s per-turn budget all read from their declared homes) runs ONE fixed 3-call
tool loop against EVERY served model: **7/8 PASS** (MiniCPM5-2B 2.1 s | Ornith-35B 8.3 s | Ornith-9B 11.5 s |
gemma-4-E4B 14.3 s | gpt-oss-20b-Q8 18.5 s | Qwen3.8-27B 50.2 s | Qwen3-Coder-30B 79.9 s slowest turn, budget
90 s). `Phi-4-mini-instruct-8bit` FAILS with ZERO tool calls (it answered from memory - BUG-053's shape, now
measured on a loop). Consequence: two `never_for` strings in model_assignments.yaml were FALSE as written and are
corrected (gpt-oss-20b drove a loop correctly; Phi-4 must never drive one). This retires the claim that only
gemma-4-E4B can drive a loop.

**THE APPROVED RECIPE VOCABULARY IS DECLARED AND ITS RUNNER REFUSES THE DANGEROUS SHAPE.**
`config/engine.yaml#fanout.task_recipes` declares six recipes (review-artifact, read-and-report,
summarize-with-source, draft-then-verify, measure-two-point, grind-a-register), each with a shape, a model ROLE
(pointer, never a name) and a DONE CHECK. `pipeline/subagent_recipe.py --list` resolves all six; the two whose
decider does not exist yet are marked `human_free: false` with what they OWE named - and the runner REFUSES
`human_free: true` with no done_check, because an LLM judging an LLM is not a verifier (R5). Controls: 6/6 and
5/5 known-answer; ruff clean.

**BUG-773 LIMB (b), TERMINATED BY TEST.** On a temp DB built from the LIVE `fbs` DDL: `INSERT OR REPLACE`
destroys the body (ROUTE 1, reproduced on demand), the S5-scoped `UPDATE` preserves it (ROUTE 2), and the live
`update_s5_provenance()` refused a diverged row aloud (ROUTE 3). Live `commit_scope` reads
**verification_scoped**, so **the contradiction is NOT LIVE**. What remains is real and narrower: `full_upsert` is
an unguarded escape route, and `content_basis` still has no writer.

**THE SIX OWNER-LANE ROWS ARE MOVED, WITH THE WORD RECORDED HERE.** T-181 (a note is a first-class kind with a
declared share of the ONE corpus root), T-183 (the applier as declared), T-180 (limbs 1-2, incl. the inbox pen),
T-176 (accept the 122 ELIGIBLE rows), T-179 (the corpus is the direction of truth; retire the library .md twins),
T-182 (register the legacy vocabulary SUPERSEDED) - all six now carry `mover: pipeline` and a gate that states the
pipeline-side act, and the disposition word given on 2026-10-17 is recorded in `governance/session_plan_20260924.yaml`'s
widening_log (owner_ack verbatim). `check_governance_faces` confirms 0 owner-moved rows remain.

**MARKET SWEEP (read-only, 23 searches, every third-party claim carrying its URL):**
`temp/PLUGIN_SURVEY_20261017.md` (20.6 KB). ADOPT: ruff+mypy as the rail C17 has never had. TRIAL: `ripwire`
(pinned, read-only - aimed at the MEASURED weakness in `engine.yaml#fanout.excerpt_bytes`, a byte budget rather
than a relevance choice) and the goose catalog's own PDF Reader. REFUSE: the whole document-conversion and
ebook/bibliography plugin classes (a second home beside S0's pandoc+Docling), the byte-equality dedupers (the
wrong operator for T-179's 727 drifted works), and every local memory/knowledge MCP (a second home beside the
knowledge layer). The gap honestly named: NO plugin covers the real work - the retriever wired into `just ask` is
WIRING, not a download.

### 1d. FORENSIC AUDIT OF THIS SITTING (rc, per rail - nothing here is asserted)

| rail | rc | reading |
|---|---|---|
| `scripts/check_repo_integrity.py` | **0** | HEAD resolves, logs/HEAD agrees, 0 conflict-marked names; the two notes about `pipeline`/`tools` being NAMESPACE roots are BUG-875's open half, unchanged by this sitting |
| `scripts/agent_context_probe.py` | **0** | `the four layers agree, and nothing measured was written` (was FAIL 6 before the parity act) |
| `check_buglog_coverage.py` | **0** | 878 blocks, every bug-id heading parsed, no byte-identical copy |
| `check_governance_faces.py --check` | **0** | faces agree with the register; **0 owner-moved task(s)** |
| `pipeline/subagent_fanout.py --selftest` | **0** | 66/66 known-answer |
| `scripts/measure_subagent_loop.py --selftest` | **0** | 6/6; `pipeline/subagent_recipe.py --selftest` 5/5; ruff clean on both |
| `check_session_plan.py --staged` | **0** | 0 undeclared path |
| `pipeline/harness_contract.py --check` | **2** | PRE-EXISTING, owner-owed (C1/C22): the harness will use its own cloud-price-tier defaults for the contract names instead of the declared ones; no act this sitting made or unmade it |
| `scripts/check_config_defaults.py --check` | **1** | PRE-EXISTING (stated, not hidden): config values read with a code default have no home in config |
| `scripts/resolve_route.py --check` | **1** | **CAUSED BY THIS SITTING, and expected: routing debt 224 -> 225.** Flipping four rows into the PIPELINE lane obliges the route graph to resolve a capability for them, and T-181/T-183's commands (the note-home declaration, the admit applier) do not exist yet. Remedy, in order: declare the T-181 note-home lane, then T-183's applier lane. A mover flip that costs one debt unit is the honest price of a row that no longer reads as a pending question |

**THE OWNER'S NEXT WORD (measured draft, nothing applied):** `apply_provider_flip.py` DRY-RUN on
`~/.config/goose/config.yaml` reads *1 edit to apply (flip `active_provider` to the declared `maxwell_omlx`),
3 already applied* - and `check_harness_homes.py` independently reports the same CONFLICT (`custom_deepseek` in the
home vs `maxwell_omlx` in the declaration). That flip binds the everyday path to the engine that owns the models
(T-174) and it is owner-worded; it is NOT applied here.

**NEXT CRITICAL STEPS, consequential order (each one unblocked unless marked):**
1. **T-181 limb 2 - the note's home** (the highest-leverage word now given): declare `journals:notes`' share of the
   ONE corpus root so `admits_to` stops being `null` and the 621 files refused for "no declared corpus home"
   acquire one; the declaration must state that ADMISSION IS NOT CONVERSION.
2. **The BUG-773 red loop** (a rail, not a reminder): RED when `stage6.commit_scope` is `full_upsert` while
   `never_at_commit` is true, with ROUTE 1/2 (measured this sitting) as its fixtures.
3. **The provider-list writer** (BUG-874's residual) so the next model-set drift is a RED rail, not a hand fix.
4. **T-183's applier**, then T-180's four limbs, then T-176's accepted 122 rows, T-179's retirement, T-182's
   accepted negative.
5. **`just ask` grounded in the retriever** (the measured gap): retrieve -> cite FB ids -> REFUSE when the corpus
   is silent -> a receipt; no plugin is required for this, it is wiring.
6. **The `scheduler` reading** (what a bundled platform extension could contribute) and the `orchestrator`
   declaration, so the last two declarations in the extension set are true by measurement.

## §1e — FIFTH SITTING (2026-10-17, afternoon): extension rot answered at the policy layer, the BUG-773 red loop landed, three decisions minted

**THE OWNER'S FOUR QUESTIONS, ANSWERED WITH RECEIPTS.**
1. *Can a goose extension be switched on only when it is needed?* YES — and two-sided measured:
   `goose run --no-profile --with-builtin developer` starts clean, while a bogus name prints
   `Warning: Failed to start extension ... continuing without it`. What was missing was POLICY, now
   `config/extension_profiles.yaml` + `scripts/goose_profile.py` (D-3056). The measured tax is CONTEXT, not RSS:
   ~7,909 tokens/request of stdio schema (≈24% of gemma-4-E4B's window) against 649 MB of live RSS.
2. *Are the plugin recommendations approved?* Approved and REGISTERED as verdicts (D-3057): adopt two, trial two,
   refuse six classes — each refusal carrying its reason so it is a re-ask, not a discovery (D-3038).
3. *Does Qwen 3.5 have any use, or is it bloat?* No measured use (0% domain agreement on S4, 1.8× slower, never
   served); the NAME is retired everywhere, the two hub copies are the owner's to delete (D-3058).
4. *Is gemma the only local model that can tool-call?* NO. 7 of 8 served models drove a fixed 3-call loop; only
   Phi-4-mini failed (0 calls). Fastest is MiniCPM5-2B (2.1 s), best window is Ornith-1.5-9B (262k). Neither is
   promoted until the two-step test lands (T-187) — one trivial read does not rank a model.

**WHAT MOVED (files).** `config/extension_profiles.yaml`, `scripts/goose_profile.py` (selftest 13/13),
`scripts/measure_extension_cost.py` (selftest 6/6), `scripts/check_commit_scope_guard.py` (selftest 9/9),
`governance/evidence/EXTENSION_COST_20261017.json`, four guard entries in `config/rail_registry.yaml`, five ladder
lines + three recipes in `justfile`, decisions D-3056..D-3058, tasks T-186..T-188.

**FORENSIC AUDIT — rc by rc.** `check_commit_scope_guard` 0 (live: rule holds on the route that runs) ·
`goose_profile --check` 2 OWNER-OWED (9 residents against policy — the honest state, not a fault) ·
`measure_extension_cost --selftest` 0 · `goose_profile --selftest` 0 · `gov_sync` 0 (4 faces equal, 1185 decisions)
· `recompute_decision_summary --check` 0 · `check_governance_faces --check` 0 (1 owner-moved task: T-186) ·
`check_repo_integrity` 0 · ruff clean on all three new scripts.

**THE OWNER'S NEXT WORD (unchanged, now with one more).** (a) T-186: apply the residency flips (`just
extension-profile workshop` prints them; nothing is written for you); (b) the provider flip T-174 (dry-run: 1 edit);
(c) META-LANE-FREEZE-1 is expired — re-rule or close; (d) T-181 limb 2 (the note's declared share of the ONE corpus
root) is still the highest-leverage ontology word.

**NEXT CRITICAL STEPS IN CONSEQUENTIAL ORDER.** 1) T-187 the two-step loop discrimination (unblocks any model
promotion) · 2) the provider-list WRITER (BUG-874's residual: the probe is the only guard) · 3) `just ask` grounded in
the retriever (the measured product gap, D-3057) · 4) T-188 the mypy rail · 5) T-183 → T-180 → T-176 → T-179 → T-182
· 6) the scheduler/orchestrator readings.

## §1f — SIXTH SITTING (2026-10-17, late morning): T-186 APPLIED GREEN, residency codified as a two-switch model, the oracle ladder declared

**WHAT THE OWNER ASKED.** (1) Codify: a new extension, created or downloaded, must register itself automatically in
`config/extension_profiles.yaml`. (2) Will the switch happen AUTOMATICALLY when the agent/subagent needs it and off
when it does not? (3) Do the T-186 manual step 2. (4) Extensive research on Qwen3-Coder-class local models, better
tool-calling subagent candidates, and whether a CAPABILITY oracle exists; from now on, research on a model ALWAYS
runs llmfit and adds any oracle found. (5) Check the script/skill graph and whether tasks/decisions are subagent-proof.
(6) Are we ready for loop-agent debugging given the bug count, and what can be delegated to speed the backlog?
(7) Explain T-174 / META-LANE-FREEZE-1 / T-181 limb 2 and recommend. (8) Check the last four sittings for unregistered
revelations. (9) State, then the next critical step in consequential order, then gov sync, then this handoff.

**COMMITS.** `55562b1` plan widening (D-2860, with the ORDER BREACH recorded rather than hidden: the widening was
written after the edits because the owner's message arrived as one block) · `d627f48` the work: D-3060, D-3061,
T-186 applied, the two new scripts, the two new tasks, BUG-053's missing header, BUG-876.

### 1. T-186 IS DONE, AND IT IS GREEN
The seven declared flips (`apps`, `chatrecall`, `code_execution`, `reddit`, `scheduler`, `tom`, `youtubetranscript`)
were written into `~/.config/goose/config.yaml` LINE-LEVEL (tempfile → fsync → os.replace; backup
`config.yaml.bak-20261017114041-t186`), with an invariant check proving every non-target body and the
`extensionmanager` entry byte-identical. `just extensions-check`: **rc 0 — 26 declared, 12 enabled, exactly the
workshop profile** (was rc 2 with 7 residents). Freed: ≈1.5k tokens/request of measured schema, two MEASURED 0-tool
processes, and three platform residents. **The session that applied it keeps the surface it was born with** — the
change is live in the NEXT session.

### 2. THE SWITCH: TWO MECHANISMS, ONE RAIL (D-3060)
- **BIRTH-TIME (the rail, deterministic):** `--no-profile --with-builtin … --with-extension '…'` per session, or the
  `enabled:` flag persistently (live at the next session's birth, NEVER in the running one).
- **RUNTIME (judgement, not a control):** `extensionmanager` exposes a ManageExtensions tool (`action` + `name`) —
  read from the goose 1.39.0 binary (`The extension '<name>' has been disabled successfully`), NOT handshaken,
  because a platform extension is not exposed by `goose mcp` (only memory, computercontroller, autovisualiser are).
  It CAN change a running session's surface. **Bound to `on_demand` only; `always`/`never`/`quarantined` are
  untouchable; `not_a_rail: true`.**
- **So the honest answer to "will it switch automatically when needed": NO — not by itself.** The harness has no
  demand-driven loading. What exists is (a) a deterministic surface chosen at birth, (b) a model-judged toggle that
  can strand a task mid-flight, and (c) the delegate's own `extensions:` list. The reliable design is (a)+(c), with
  (b) as convenience. A session that crosses task classes should be REBORN, not mutated.
- **ADOPTION ON ARRIVAL (codified):** `just extensions-adopt` registers any extension the harness declares but no
  class carries into `quarantine` with a dated `seen:` stamp — granted NOTHING, refused by every profile, reported
  rc 2 (loud, not fatal). An ARRIVAL IS NOT A DECISION; the registration is automatic, the grant is not.
- **SUBAGENT SURFACE (codified):** `just extensions-delegate <class>` prints the exact `extensions:` list —
  `review` = developer+analyze+skills (a judged output must be able to load the house rules), `sweep`, `extract`;
  `research` is REFUSED as a class. Every name is resolved against the harness or the render REFUSES.
- **KNOWN GAPS, RECORDED NOT PRETENDED:** no read-only surface exists (T-189) and a mid-session surface change
  leaves no receipt anywhere (T-190).

### 3. THE RESEARCH: NOTHING TO DOWNLOAD, AND THE ORACLE QUESTION IS ANSWERED (D-3061)
- No drop-in FASTER model in the Qwen3-Coder class here: Qwen3-30B-A3B-Instruct-2507 is the same 30.5B MoE and
  llmfit estimates the IDENTICAL 59.3 tok/s (at an 8192-token cap) for a model that measured **79.9 s** on a 3-call
  loop. Speed is a property of the SHAPE (3B active), and the shapes that beat it are already served
  (MiniCPM5-2B 2.1 s, Ornith-9B 11.5 s).
- The catalogue's own top-50 of `tool_use` + fits + ≤40B = **32 families in 50 rows, 20 distills, and FIVE
  quantisations of the same #1 — DeepSeek-R1-0528-Qwen3-8B, a REASONER**, the worst loop shape. Not a shortlist.
- **llmfit's coverage is 4/8 of this roster** and its tags are dropped by quantisation — D-3058's evidence is
  CORRECTED in the research register (conclusion survives).
- **ORACLE LADDER (declared in `config/model_oracles.yaml`, mechanised by `scripts/llm_candidate_probe.py`):**
  fit (llmfit) → named external prior (BFCL / τ²-bench / SWE-bench Verified) → **the MEASURED loop is the only
  gate**. Refused as evidence, with reasons: parameter count, catalogue tags, card prose, vendor demos,
  estimated_tps-as-loop-time.

### 4. THE STATE: FOURTEEN REDS, AND THEY ARE THE FIRST READING ANYONE HAS HAD
`scripts/run_ladder.py --collect health` ran all **181** declaring lines in 909 s (a normal `just health` stops at
the first failure — BUG-573's shape). **14 reds, none new** (all five residency lines added this sitting read `ok`):
`check_bug_recall` · `resolve_route` (225 unrouted vs the 222 SHRINK-ONLY ceiling) · `check_bug_status` (fixed) ·
`check_register_divergence` (fixed: BUG-053 got its missing HEADER, BUG-492 was CLAIMED by D-3059 and is now only
cited) · `build_anchor_store_bridge` · `check_config_defaults` (debt GREW: 595 sites / 594 modules) ·
`lib/handoff --selftest` (**BUG-876**, a real defect: no receipted post-image exists for `decisions.yaml` and
`--backfill` skips it) · `check_silent_repair` · `check_undeclared_encoding` · `check_store_columns` · `reconcile` ·
`verify_generator_pins` · `check_tests` (the 4th fatal) · `check_rail_mutations`. Fault set now RECORDED, not unknown.

### 5. LOOP-AGENT READINESS: NOT YET, AND THE BLOCKER IS NOT THE BUG COUNT
The register holds 231 open bugs, but a loop agent is not blocked by a backlog — it is blocked by not being able to
tell a good run from a bad one. What is MISSING is small and named: (a) T-187's two-step/two-tool fixture, without
which no model may be promoted into the loop; (b) BUG-876, because a loop's whole output is claims about governed
files and the attribution control that would check them cannot go green; (c) T-190, because a loop that can change
its own tool surface mid-run leaves no trace. Three acts, not three hundred. **Verdict: loop-agent debugging may
start on READ-ONLY and measurement tasks now (they need none of the three); it may not adjudicate a governed write
until (b) lands.**

### 6. WHAT TO DELEGATE (the fast track), AND WHAT NEVER
- **Delegate now (read-only, no writes):** repo sweeps for the 14 reds — each is a file:line reading
  (`sweep` profile: developer+analyze+filesystem); the 225 unrouted bugs → capability proposals (`sweep`, never
  applied — D-2898 forbids an LLM deciding a promotion); research digests WITH source text in hand (`extract`).
- **Never delegate:** open-ended research (BUG-053), a canonical promotion, a governed write, or anything whose
  failure would not be visible (D-3020: the durable path is the delegation path).
- **The graph findings.** Script graph: 417 scripts / 74 `just` recipes — a STAR (just → scripts), with most
  scripts unreachable from any recipe (T-165's class), and `pipeline/`+`tools/` still PEP-420 namespace roots
  (BUG-875, CAPTURABLE BY CONSTRUCTION on every run). Route graph: 22 capabilities + lanes, 640 findings routed,
  225 with no capability at all. Skill graph: TWO in-repo skills (`agent/skills/`) — and a delegate inherits none
  of them unless `skills` is in its `extensions:` list, which is why `review` now carries it. **Subagent-proofing
  verdict: the DECISIONS are (each has a home and a rail); the TASKS are not yet (59 open, 57 pipeline, no
  delegation surface per task); the SKILLS are thin (2 for a 417-script OS).**

### 7. THE OWNER'S THREE WORDS, ANSWERED
- **(b) T-174, the provider flip — what and why.** The harness config says `active_provider: custom_deepseek`,
  while the declaration says `maxwell_omlx`. `agent/adapters/goose/apply_provider_flip.py` is the ONE writer that can
  make the live home agree with the declaration: dry-run today = **1 edit to apply, 3 already applied**. Why it
  matters: every session is one mis-click away from routing to a provider the OS does not declare (and
  `custom_deepseek` is the one with the reasoning-passthrough defect, DELEGATE-001). **Recommendation: APPLY IT**
  (`python3 agent/adapters/goose/apply_provider_flip.py --apply`), then start a new session — it is a one-line flip,
  it is reversible (the script has `--rollback`), and every day it stays unapplied is a day the declaration and the
  home disagree. It does NOT render the model list (BUG-874's residual), which stays owed.
- **(c) META-LANE-FREEZE-1 — what and why.** It is a freeze on the GOVERNANCE MACHINERY: a new governance bug may
  be FILED but not WORKED while it is open (opened 2026-09-27 because ~37 of the last 40 bugs were about the
  machinery). Its own stated precondition was that the ladder report its WHOLE fault set in one pass. **That is now
  MEASURED TRUE: 181 lines, one pass, 14 faults named, receipt on disk.** The window's `review_by` has passed with
  its exit UNMET (2 still parked). **Recommendation: CLOSE IT**, on its own precondition, and let the 2 remaining
  held ids (BUG-568, BUG-559) enter T-114's discharge order as ordinary rows. Keeping an expired window open makes
  every governance act argued rather than ruled, which is the drift it was built to stop.
- **(d) T-181 limb 2 — what and why.** One corpus root admits books but the notes share is still NULL, so 621 files
  are refused for "no declared corpus home". **Recommendation: declare the notes share** with ADMISSION IS NOT
  CONVERSION stated in the same word — it is the highest-leverage ontology decision outstanding, and it unblocks
  T-180 and T-183 in one move.

### 8. NEXT CRITICAL STEPS, IN CONSEQUENTIAL ORDER
1. **Start a new session** (the only way to see the new 12-extension surface) and read `just extensions-check`.
2. **T-114's first three**: the `check_config_defaults` growth (debt GREW — never re-record upward), the
   `build_anchor_store_bridge` re-derive, and `handoff.py`'s attribution control (BUG-876).
3. **T-187** the two-step/two-tool loop discrimination — still the only gate for a model promotion.
4. **T-188** mypy as a rail (C17 half-runner) and **T-189/T-190** (read-only reviewer; a receipt for a surface change).
5. **The provider-list writer** (BUG-874's residual), then grounded `just ask`, then the owner lane T-183 → T-180 →
   T-176 → T-179 → T-182.

---

## 1e. SPINE UPDATE — 2026-10-17, FOURTH SITTING (append-only; nothing above is rewritten)

**0. THE OWNER'S FOUR WORDS, ANSWERED WITH BYTES.** (a) the extension model was EXAMINED, not re-decided;
(b) T-174 was RE-BOUND and its command corrected; (c) META-LANE-FREEZE-1 was CLOSED by its own terms;
(d) T-181 limb 2 — the NOTE'S HOME — was DECLARED, and the reader that would have got it wrong was fixed with it.
One new bug filed (BUG-877), two decisions minted (D-3062, D-3063), one rail message made true.

| item | before | after | how it was measured |
|---|---|---|---|
| `just extensions-check` | rc 2 (9 residents vs policy) six days ago; **rc 0** this sitting | **rc 0**, 26 declared / 12 enabled = workshop | `scripts/goose_profile.py --check` |
| harness homes | rc 2, `active_provider` CONFLICT (custom_deepseek) | **5 bound / 0 conflicting**, rc 0 | backup `config.yaml.bak.20261017121710`, file read back |
| META-LANE-FREEZE-1 | state open, day 20 of 14, exit UNMET, rc 2 | **state closed, BOTH clauses MET, rc 0** | `check_freeze_window.py`, 15/15 controls |
| T-181 limb 2 | `admits_to: null`, 621 rows refused | **declared**, no-home refusals **621 → 0**, candidates **244 → 479** | `plan_admission.py --brief`, 19/19 controls |
| routing debt | 225 vs ceiling 222 (filed by the third sitting) | **225** — this sitting did NOT make it worse (BUG-877 routes) | `resolve_route.py --check` |

**1. THE EXTENSION QUESTION, ANSWERED BY ONE MEASURED ASYMMETRY — mid-session switching is a ONE-WAY DOOR.**
The policy already declares two switches (`config/extension_profiles.yaml#residency`), and they are not equivalent:
`enabled:` is read **at BIRTH** (BUG-873 limb b: a resumed session keeps the surface it was born with, proven from
`sessions.db`), and the runtime switch (`extensionmanager.manage_extensions`) advertises **`disable` and `install`** —
it can REMOVE a tool, it cannot ADD one the session was not born with. So "switch the profile mid-session" is not a
design choice we are free to make: **you can only shed, never gain.** The reliable architecture is therefore the one
already declared — **a task-labels the session, and the profile is chosen at birth** — with the runtime switch kept
for what it honestly is: a way to drop a heavy extension once its work is done, decided by a MODEL and therefore
never a rail (`judged_by: model`, `not_a_rail: true`).

**2. DOES THAT COST CONTINUITY? NO — BECAUSE THIS OS'S MEMORY IS NOT THE TRANSCRIPT.** A task-labelled session loses
nothing that matters if it leaves a receipt: the durable layers are `memory` (always resident), `chatrecall`
(on_demand, for "what did we decide in a past session" from the harness store), and — decisively — the FILE SYSTEM:
`governance/buglog.md`, `config/task_register.yaml`, `config/decisions.yaml`, the handoff this line is written in,
and `scripts/delegate_journal.py`. That is why task sessions are not a regression here: **the OS already refuses to
treat a transcript as a record** (D-3036, "an act that leaves no trace did not happen"). The one real cost is
re-establishing context, and that cost is MEASURED and low: the prefix cache returns 25.01x on a byte-stable prefix
(BUG-872), so a NEW session is cheap precisely when its opening bytes are stable.

**3. THE PROFILES THAT MATCH THE ACTS WE ACTUALLY PERFORM** (all declared; nothing new invented): `workshop`
(repo engineering — the current default), `core` (**added this sitting as a DECLARATION, not applied**), `research`
(finding something out), `documents` (read one PDF in place), `recall` (past-session questions), `web`, `sandbox`,
`everything` (measurement only). Delegates already have their own three (`review` = developer+analyze+**skills**,
`sweep` = developer+analyze+filesystem, `extract` = developer+summarize) — and a delegate is a SESSION, so the same
birth-time rule applies to it.

**4. THE ONE LEVER STILL ON THE TABLE, PRICED.** `workshop` adds the two largest schemas in the set — `filesystem`
(14 tools / 3,727 tok) and `gitmcp-mcp` (12 tools / 1,906 tok) = **5,633 of the ~7,909 tok/request** the stdio set
ships — and both duplicate `developer.shell` at zero schema cost. `core` is now declared so that paying it is a
NAMED decision. **Switching it is an OWNER act** (two flips in the harness home + `default_profile: core`) and it
takes effect in the NEXT session only. `python3 scripts/goose_profile.py --render core` prints the exact commands.

**5. R5 RAN, AND IT SAID REJECT — RECORDED, THEN ADJUDICATED.** gemma-4-E4B reviewed the `plan_admission.py` change
(`DJ-20261017T101927Z-7c80`, journaled BEFORE the call) and returned REJECT on two objections. Both were answered
with a measurement rather than a green: (i) "a file outside its kind folder may resolve wrongly" — that IS the
declared, counted `refused_not_in_its_kind_folder` class (52 rows, unchanged before and after); (ii) "the corpus-key
test precedes the admission tests" — that is the D-3045 identity rule, held by the control
`a_work_the_corpus_holds_by_KEY_is_NOT_an_admission_candidate`. **No code changed for the rejection**; the
adjudication is D-3063's consequence, and a reviewer disagreeing is information, not a verdict.

**6. WHAT THE NOTE'S DECLARATION ACTUALLY CHANGED IN THE TREE'S OWN TAXONOMY.** Declaring `admits_to` alone would
have been WRONG: the reader derived every target as `corpus_home/(path below the root's KIND folder)`, and a
domain-axis root has no kind folder — so the fallback proposed **every note at the corpus ROOT**, beside the DOMAIN
trees, where the domain vocabulary (read from the corpus's own immediate subdirectories) would have claimed it as a
new DOMAIN. That is the drift class this reading exists to prevent, found by measuring before writing. Fixed by
deriving the path from the DECLARED AXIS, and the rule is now ENFORCED as a refusal
(`refused_domain_not_a_corpus_domain`, 0 on today's library — printed as a zero, never omitted).

**7. BUG-877 — A GOVERNED WRITE THAT DOES NOT SURVIVE.** T-174's gate recorded BOUND on 2026-10-16; today the home
read `custom_deepseek` again and **no backup beside it carries the flipped value** (13:16, 00:35, 11:40×2 all read
custom_deepseek). Something rewrote the owner home without a backup; the candidate (the client rewrites its own
config) is a HYPOTHESIS. The rail that measures it is right and is in the ladder — and the sixth sitting's 14-red
reading did not include it, which is recorded as an open question, not a verdict.

### NEXT CRITICAL STEPS, consequential order (each unblocked unless marked)
1. **T-183's applier** — the last limb of THE ADMISSION. 479 candidates now have a declared home and a derived target;
   nothing may move until a plan-keyed, dry-run-default, crash-safe writer exists.
2. **The BUG-877 red loop** — a two-point reading either side of a client restart, naming what rewrites the home.
   The reading is one command; the missing thing is a SCHEDULE, not an instrument.
3. **BUG-876** — the attribution control; still the one thing that blocks a loop agent from adjudicating a governed
   write (the sixth sitting's verdict stands).
4. **`just ask` grounded in the retriever** — the measured gap; a diff to one script plus a refuse-when-silent clause.
5. **T-187** — the two-step/two-tool fixture; still the only gate for a model promotion (and the ONLY gate for the
   2507-class candidate recorded in D-3061).
6. **The routing debt 225 vs 222** — pre-existing, and its SHAPE is now measured: **223 of the 225 name NO artifact
   in their title at all** (`no_artifact_named`). The metric is measuring bug-TITLE hygiene more than routing; a
   disposition or a title rule is the honest fix, not 223 capability declarations.

---

## 1f. SPINE UPDATE — 2026-10-17, FIFTH SITTING (append-only; nothing above is rewritten)

**0. THE OWNER'S QUESTION WAS "HOW DO I ACTUALLY USE THIS?", AND THE ANSWER WAS A MISSING MECHANISM, NOT A MISSING
PARAGRAPH.** The residency policy (D-3056) could RENDER a profile and nothing could PERFORM one, so every session was
still born from the harness default and the policy described a road nobody drove. This sitting made the birth a
command (D-3064), made a dead member refuse the birth, added the read-back that answers *what was this session given*,
declared the capability the whole lane was missing, and — behind the launcher — found and measured a real defect in the
one guard that matters most for governed writes (BUG-878).

### 1. THE THREE REFERENCES, EXAMINED (adapt / reference / refuse — each with a measurement)

| reference | what it is | verdict |
|---|---|---|
| `youtube.com/watch?v=UXcMa3fOHXk` | the **pstack** explainer (19:01, unofficial): playbooks, principles, `poteto-mode`, overnight/handoff contract, deslop/unslop, benchmark-checklist | **NOT the source — the same thing as the next row.** Kept as a REFERENCE for the *reading order* of its playbooks, not as a dependency. |
| `github.com/cursor/plugins/tree/main/pstack` | 54 skills + 2 agents + 23 playbooks, MIT, `plugin.json` on `agent-plugins.org` schema | **PARTIALLY ADAPTABLE, and NOT as a bundle.** MEASURED: installing it wholesale costs **2,676 description tokens per request** (54 × their frontmatter descriptions; content is 48,269 tokens on demand). That is half the price of the entire extension tax we just removed. **REFUSED wholesale**; the four ideas worth porting are named in §3. |
| `goose-docs.ai/extensions/` | the harness's extension directory (client-rendered; read instead from `docs/getting-started/using-extensions`) | **REFERENCE, already implemented.** It documents built-in vs platform vs stdio extensions and the toggles we already encode. One thing it documents that we had not used: **plugins** (`plugin.json` + `skills/` + `hooks/`, Open Plugins or Gemini-extension format, `goose plugin install <git-url>`, discovered from `~/.agents/plugins/`). |

**What the harness already offers and this repo did not use (MEASURED 2026-10-17, not read from a card):**
- `goose plugin install <git-url>` + `goose skills list` — a plugin is a *distribution* container for skills and hooks.
- **`SessionStart` / `SessionEnd` / `PreToolUse` / `PostToolUse` hooks** — the missing trigger for T-190's receipt: a
  mid-session surface change and a session BIRTH can both leave a record without a new store (see §5, next steps).
- `goose local-models search "<query>"` — a **live HuggingFace search for GGUF *and* MLX** repos (see §4).

### 2. THE OPERATING PROTOCOL — how a profile is chosen, and what happens when a session needs more

1. **You never switch a profile. You NAME the session.** `just session <profile>` births it (`--no-profile` + the
   explicit set). The profile name IS the task label — deliberately, because a second vocabulary
   (task-class → profile) would be a mapping layer that drifts (C12).
2. **Which one — one line each, priced by the MEASURED schema cost it adds per request**
   (`just extension-profile <name>` prints the exact command and the flips):

   | profile | the act it is for | added cost/turn |
   |---|---|---|
   | `core` | read a few files, answer, write ONE governed document | **+0** (cheapest birth this OS can offer) |
   | `workshop` | repository work: sweeps, history, moves | **+5,633** (filesystem 3,727 + gitmcp-mcp 1,906) |
   | `research` | finding something out | **+1,517** (transcripts 1,168 + reddit 349) |
   | `documents` | read one PDF in place | **+350** |
   | `web` | drive a browser | **+1,834** (puppeteer 834 + transcripts 1,168) |
   | `recall` | "what did we decide in a past session" | +0 measured (platform tool, unmeasured — D-2957) |
   | `sandbox` | run code with NO shell | +0 measured (platform tool) |
   | `everything` | the audit profile — used to MEASURE, never as a default | +7,909 |

3. **You know afterwards, not from memory:** `just born 5` reads the harness's own record and prints, per session, the
   surface it was GIVEN and the profile that surface EQUALS (or that it equals none).
4. **A mid-session need has exactly three honest answers, and none of them is "switch":**
   (a) **SHED** — `extensionmanager` can `disable` and `install`, i.e. a ONE-WAY DOOR: a session can drop a heavy tool,
   never gain one it was not born with (BUG-873 limb b). Model-judged, convenience only, never a rail;
   (b) **BE REBORN** — start a sister session with the right profile (cheap: the prefix is byte-identical, 25.01x warm
   cache, BUG-872) and hand it a written intent, because this OS's memory is the registers and receipts, not the transcript;
   (c) **DELEGATE** — a subagent is its own session and takes an explicit `extensions:` list
   (`just extensions-delegate review|sweep|extract`), which is the per-session form applied to a bounded task.
   A session that crosses task classes should be REBORN or DELEGATE, **never mutated**.

### 3. WHAT IS WORTH TAKING FROM pstack, AND WHAT IS ALREADY BETTER HERE

Take (as OUR OWN skills, one at a time, never the bundle): **(i)** `prove-it-works` — an artefact must be demonstrated,
not asserted (we already have this as the receipt rule; pstack's phrasing is a better *prompt*, and the shape is
"run the thing, show the output"); **(ii)** `benchmark-checklist` — vet a number (limiter, repeats, end-to-end) — this
is D-3061's oracle ladder in plain words, and the 79.9 s / 59.3 tok/s surprise is exactly its case; **(iii)**
`deslop`/`unslop` — a diff-cleanliness pass, which is C12/C19/C20 as a *procedure*; **(iv)** `interrogate` — N models
try to break a diff, which is R5 done properly (we ran R5 this sitting and it ACCEPTed; the disagreement is the value).
Refuse: the 23-playbook router (`poteto-mode`) — a second routing surface beside `resolve_route`/`capability_registry`
would be two homes for one decision; the agent/automation fleet (Cursor-specific, C25); and the whole-bundle install
(2,676 tok/request for skills we would then have to keep in sync with our own decisions).

### 4. llmfit vs the harness's own model instruments — "can it check all of HuggingFace?" NO, and it does not need to

- **llmfit is a hardware-FIT oracle with a bundled catalogue**, not a HuggingFace crawler: it carries 5,103 models,
  refreshes with `llmfit update`, and can query HF with `llmfit hf-search` — for **GGUF (llama.cpp)** only. Its
  capability tags are measured INVERTED on this roster and its `estimated_tps` is computed at an 8,192-token cap
  (D-3061). Its coverage of the eight models this machine SERVES is **4/8**.
- **The harness has a better instrument for *discovery*, and this repo had not used it:**
  `goose local-models search "<query>"` returns **live HuggingFace results for GGUF *and* MLX** (`mlx-safetensors`),
  which is the format this machine actually serves. MEASURED 2026-10-17: it returned eight MLX repos for
  "Qwen3-30B-A3B MLX 4bit", including **`Qwen3-30B-A3B-Instruct-2507-MLX-4bit` (lmstudio-community)** and
  `mlx-community/Qwen3-30B-A3B-Instruct-2507-4bit` — the D-3061 candidate, available, nothing downloaded.
  Its own output carries the honest caveat `MLX support was not compiled in`: it can **FIND** MLX repos but this build
  cannot **download** them (`goose local-models download` is GGUF-only), so a fetch stays `huggingface-cli`/`hf`.
- **What OMLX itself offers:** the served-side facts the OS already reads — `GET /v1/models` (`max_model_len`, the
  served window), `~/.omlx/model_settings.json`, `~/.omlx/stats.json#total_requests` (the engine's own request
  counter, the only witness that a run was served BY THIS MACHINE). It is a SERVING surface, not a discovery one:
  nothing in OMLX knows what is on HuggingFace.
- **Therefore the market-research procedure is four steps, and each has an owner**: discover (`goose local-models
  search` / `llmfit hf-search`) → FIT (`llmfit`, this machine, tags ignored) → PRIOR (BFCL / τ²-bench / SWE-bench,
  `machine_truthful: false`) → **MEASURE THE LOOP** (`scripts/measure_subagent_loop.py`, the only gate). A fifth
  tool would not add evidence; it would add a fourth opinion.

### 5. WHAT LANDED THIS SITTING

| item | before | after | how it was measured |
|---|---|---|---|
| a session's birth surface | RENDERED only; every session inherited the config default | **`just session <profile>`** executes the per-session form; an undeclared profile is refused; a member that would start DEAD refuses the birth | selftest **22 → 31** controls; live refusal from `/tmp` (rc 1, no session started) |
| "what was this session given?" | unanswerable (a transcript is not a surface) | **`just born [N]`** reads `enabled_extensions.v0` and names the profile the surface EQUALS | live read of the last sessions; `NOT RECORDED` when the key is absent |
| the write gate | born DEAD from any cwd but the repo root, silently, rc 0 | **BUG-878 filed** (the gate reads the TERMINAL, never the session) | two-sided: repo root starts, `/tmp` warns and continues, exit 0 |
| the residency lane's route | **no capability owned it** (`extension_profiles.yaml`, `goose_profile.py` unowned) | **`extension_residency`** declared (owns the policy, the reader, and `mcp_doc_guard.py`) | `resolve_route.py --check`: debt **226 → 225**, BUG-878 `routed` |
| the bug census title | a fixed `rest[:140]` slice severed a token, so a heading naming `mcp_doc_guard.py` read **`mcp_do`** and the item counted as `no_artifact_named` | cut at a WORD boundary (`TITLE_MAX` named, C20) | the same item now resolves to its capability |
| decisions / bugs / faces | 1188 / 643 / 59 — and the 1188 was **STALE**: the registry already held D-3062 and D-3063 | **1191** / 643 / 59, four faces equal their re-derivation | `recompute_decision_summary.py`, then `gov_sync.py --apply`, `check_governance_faces.py` rc 0 |

**AND THE STALENESS IS ITSELF A READING (BUG-573, third observed instance).** `recompute_decision_summary.py
--check` IS a fatal rail (justfile:183 and :231) — but `just health` reports a PREFIX and stops at the FIRST non-zero
line, and `route_graph` is red ahead of it, so the census was never re-derived while two decisions sat uncounted. The
four faces then agreed with each other and with a stale census, which is green because two derived things agree, not
because either is true. **The honest reading of this ladder is `just health-full`**, and the census must be recomputed
as part of any act that MINTS a decision — not left to a rail that an earlier red can hide.

**R5 (generator ≠ verifier), run as a journaled delegate** (`DJ-20261017T104719Z-50e5`, gemma-4-E4B, 127.4 s, wall
measured from the journal's own rows): verdict **ACCEPT** with three objections, each adjudicated on evidence and none
of them turned into a silent change — (1) `unresolvable` relies on `profile_members` refusing first: **the call order
in `launch()` IS the guarantee** (`birth_argv` runs before it), and a direct call refusing is the correct answer;
(2) a path on a cloud mount can flake: **the failure direction is fail-closed** (the birth is refused, not born dead);
(3) `SystemExit` "makes debugging harder": **the message names the member AND the path that does not resolve** — that
is the debugging.

### 6. NEXT CRITICAL STEPS, consequential order (each unblocked unless marked)

1. **BUG-878's remedy is an OWNER ACT** — one line in the harness home:
   `docguard.args: ['/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/mcp_doc_guard.py']`,
   backup beside the home + read-back (the T-186 form). Until then every session NOT launched by `just session`
   may be running without the D824 write gate and cannot tell.
2. **T-183's applier** — the last limb of THE ADMISSION: 479 candidates have a declared home and a derived target and
   nothing may move until a plan-keyed, dry-run-default, crash-safe writer exists. It is the pipeline lane's #1.
3. **T-190's remaining half** — the `extensionmanager` toggle still leaves no trace; the harness now offers
   `PreToolUse`/`PostToolUse` hooks, which is the trigger the row said was missing.
4. **BUG-876** (the attribution control) — still the one thing blocking a loop agent from adjudicating a governed write.
5. **T-187** — the two-step/two-tool fixture; still the only gate for any model promotion.
6. **The routing debt 225 vs 222** — its shape is now measured twice: 223 of 225 name no artifact, and the census title
   was itself SEVERING artifacts at char 140 (fixed this sitting). Re-read the census before adding 223 declarations.

## §1g — SPINE UPDATE, 2026-10-17 (SIXTH SITTING): THE PROFILE IS RESOLVED, NOT CHOSEN

### a. The question, answered in one paragraph
"Who switches the extension profile — the agent or me?" **Neither, and no session needs a profile label a human
maintains.** A session's guest list is fixed at the door (BUG-873: `enabled:` is read at BIRTH; the runtime switch
can only SHED). So the only lever is *how the session is born*. `just go` — no argument — resolves the profile
deterministically (`MAXWELL_PROFILE` if set, otherwise `default_profile`), prints WHY, refuses to be born with a dead
member, and starts. Naming a profile (`just session research`) survives as the OVERRIDE, not the routine. Depth comes
from WORKERS: a subagent is its own session with an explicit extension list (`just extensions-delegate review|sweep|
extract`), which is exactly the separation Claude Code documents as "specific tool access". A profile is therefore
something a worker carries, not something you keep in your head.

### b. What landed (before → after)
| thing | before | after | receipt |
|---|---|---|---|
| choosing a profile | the human must remember one of 8 names | **`just go`** resolves one and prints `(MAXWELL_PROFILE=… / default_profile=…)`; an unknown name is a REFUSAL, never a fallback | `resolve_profile()`, selftest 31 → **37/37** |
| a declared script argument | resolved against the CALLER's cwd — the defect BUG-878 actually was | resolved in the **DECLARATION's** `cwd` first, then the birth dir; inlined ABSOLUTE and quoted | `_abs_script()`, `_quoted()` |
| `docguard` in the harness home | `args: [mcp_doc_guard.py]`, dependent on a CloudStorage `cwd` being mounted | **absolute**, one line changed, all other keys byte-identical, backup `config.yaml.bak.20261017131255.bug878-abs` | `/tmp` birth → 0 warnings (`20261017_12`) |
| llmfit | cited as a discovery + capability oracle | **FIT ARITHMETIC ONLY**; discovery = `goose local-models search` (GGUF **and** MLX, live) | D-3066, `model_oracles.yaml` |
| `scripts/evaluate_model.py` | an orphan that `pip install`s llmfit at runtime | **archived** (`archive/evaluate_model.py.archived-2026-10-17`), index regenerated (45 entries) | `build_archive_index.py --check` rc 0 |

### c. BUG-878 was RE-SCOPED, not merely patched — read this before trusting the old text
The filed claim ("a session started outside the repo is born without the write gate") was true of the route it was
measured on and **false of the config**: from `/tmp`, `goose run` was born with 12 workshop extensions and ZERO start
warnings, because the harness honours a config-declared `cwd`. The thing that died was `--with-extension '<cmd>
<args>'` — the form `just session` emits — which carries no cwd. So the defect was **resolution in the caller's
context**, and the launcher was its only live route. Forensic sweep: of 26 declared extensions, exactly one carried a
relative script argument; it is now absolute. R5 (gemma-4-E4B, `DJ-20261017T111319Z-082b`, 74.8 s) returned ACCEPT
with one objection (a wrong declared cwd could win silently) — adjudicated on evidence: that IS the harness's order, so
mirroring it is the faithful reading, and the case is unreachable today because the sweep leaves one absolute argument.

### d. Peer cross-examination (why this shape and not another)
Refused: a **keyword router** over the task text (a second routing surface, the reason pstack's playbook router was
refused) and an **LLM router at birth** (a model call plus a hallucination surface at the one step with no measurement
to check it against; D-2898/D-2941). Adopted: the peer consensus that capability should NOT be paid for upfront —
Anthropic preloads a name+description index and reads bodies on demand; Claude Code caps subagent **descriptions** at
15k tokens before warning, and gives each subagent its own tool access; Gemini CLI and goose plugins are distribution
containers, never residency. The one peer feature we do NOT yet have is true progressive disclosure: MCP tool schemas
are static per session in goose, so "`core` at birth + delegate for depth" is our faithful approximation.

### e. NEXT CRITICAL STEPS (consequential)
1. **OWNER, one line (task B, now unblocked):** `default_profile: workshop` → `core` in `config/extension_profiles.yaml`,
   then flip `enabled: false` for `filesystem` and `gitmcp-mcp` in the harness home. Worth **5,633 tok/request**; takes
   effect only in the NEXT birth, and `just go` already routes through it. `--check` must then read rc 0.
2. **T-183's applier** — pipeline lane #1, untouched: 479 admission candidates have a home and a target and may not
   move until a plan-keyed, dry-run-default, crash-safe, receipted writer exists.
3. **T-190's toggle half** — `PreToolUse`/`PostToolUse` hooks are the measured trigger; still unbuilt.
4. **T-187** — the two-step/two-tool loop fixture; still the only gate for any model promotion.
5. Pre-existing reds unchanged: `route_graph` (225 vs 222), `check_rail_mutations`, `check_config_defaults`, BUG-876.

## §1h — SEVENTH SITTING (2026-10-17, afternoon): TASK B APPLIED AND PROVEN BY BIRTH, the cascade it exposed FIXED, the three owner acts VERIFIED

### a. What the owner asked (verbatim, trimmed)
"do B and and do the 3 manual task ... after this queiry you finished I will open a new session so again provide a
handoff with ll required context so we can continue the conversation from where we finished in this session ...
first look in general maxwell os current state, continue with the next critical step starting with the highest
leverage step". Standing rules restated by the owner: senior RAG/systems/ontological lens; clear manual instructions;
delegate to the right local LLMs and check none drifted; forensic audit BEFORE any serious implementation; list the
next critical step; sync the governance dependencies so nothing conflicts and nothing superseded stays open.

### b. STATE AT CLOSE (numbers, not impressions)
| thing | reading |
|---|---|
| decisions | **1,194** (D-3067 minted ACTIVE) |
| bugs | **644** — 234 OPEN / 410 CLOSED (BUG-879 filed, routed) |
| open tasks | 59 |
| `goose_profile --check` | **rc 0** — 26 declared extensions / 8 profiles, policy == live state |
| `goose_profile --selftest` | **38/38** |
| `check_governance_faces --check` | **rc 0** (644 bug ids, 0 owner-moved tasks) |
| `gov_sync --apply` | 4 faces equal their re-derivation |
| `check_freeze_window` | **rc 0** — META-LANE-FREEZE-1 CLOSED, exit MET, parked 12, still OPEN 0 |
| `resolve_route --check` | **RED (pre-existing)** 225 unrouted bugs vs ceiling 222 — this sitting added a ROUTED bug, so the debt did not grow |
| `harness_env --check` | **rc 2 OWNER-OWED, by design** — five names unbound in THIS shell; see §h for the correct instruction |
| pipeline | OMLX + Ollama up; 7,640 FBs (4,503 PASS / 3,137 QUARANTINE); no stage touched this sitting |

### c. TASK B — what landed (before → after → the receipt that decides it)
| thing | before | after | receipt |
|---|---|---|---|
| `default_profile` | `workshop` | **`core`** | `config/extension_profiles.yaml`; resolver prints `('core','default_profile=core')` |
| `filesystem` | enabled | **disabled** | harness home, 2 lines changed, backup `config.yaml.bak.20261017134734.taskB-core`, revert-and-compare proof that every other key is byte-identical |
| `gitmcp-mcp` | enabled | **disabled** | same write, same proof |
| the birth | 12 extensions, ≈6,392 tok/request | **10 extensions, ≈759 tok/request** | `cd /tmp && goose run --max-turns 1` → rc 0, stderr 0 B, **0 warnings**, session **20261017_14**, surface read from `enabled_extensions.v0`: DocGuard, Extension Manager, Fetch, analyze, developer, memory, skills, summarize, summon, todo |
| the escape hatch | asserted | **PROVEN** | the rendered per-session workshop command, run from `/tmp` → rc 0, 0 warnings, session **20261017_17**, 11 recorded members incl. `npx` — while `filesystem` is DISABLED in the config |
| `delegate_profiles.sweep` | `[developer, analyze, filesystem]` | **`[developer, analyze]`** | the cascade below: the name stopped resolving the moment the default changed |
| `--check` | did not see delegate profiles | **reports any delegate profile naming a DISABLED extension as OWNER-OWED** | known-answer control that FAILS if the branch is removed (selftest 38/38) |

**What this buys, stated in the currencies it is actually paid in:** the 5,633 tok/request of `filesystem` (3,727) +
`gitmcp-mcp` (1,906) is no longer paid by a session that did not ask for it; two subprocesses a `core` session no
longer starts are the memory half. It is live only at the NEXT birth (BUG-873 limb b) — the session that applied it
still runs the old surface, by construction.

### d. THE CASCADE THE FORENSIC AUDIT FOUND — and it is fixed here, not deferred
The audit asked the one question that mattered: *who already depended on the surface being switched off?* Answer:
the declared subagent profiles. `enabled:` is **not** merely "the session default" — it is a **gate on named
provisioning**, measured two-sided: a delegate given `extensions: ["developer","filesystem"]` while `filesystem` was
disabled was born with **`developer` alone** (session `20261017_15`); the same mechanism given
`["analyze","memory"]` while both were enabled was born with **exactly those two** (`20261017_16`). So `sweep`, which
named `filesystem`, had silently become a declaration with no referent (D-3034). Two acts, both landed: the profile
drops the name (`developer.shell` reads files at ZERO schema cost), and `--check` now makes the shape loud.
**Consumer sweep before either act:** of every `.py`, `.md`, `.yaml` and justfile recipe in the repo, NONE names a
`filesystem` or `gitmcp-mcp` tool — the only hit is the policy's own prose.

### e. THE THREE MANUAL ACTS — VERIFIED BY THEIR OWN RAILS, none redone on faith
| act | how it was verified this sitting | reading |
|---|---|---|
| **T-186 residency flips** (the 7 extensions switched off, 12 left resident) | the flip receipt `temp/t186_flip_20261017.json` **and** the live comparison `goose_profile --check` (policy vs harness state) | 7 disabled / 12 enabled at the time; today **rc 0** against `core`, and the receipt backup is named |
| **T-174 provider flip** | the writer's own dry run, `apply_provider_flip.py --dry-run` | **`0 edit(s) to apply, 4 already applied`** — the pointer-resolved values equal the bytes in the home |
| **META-LANE-FREEZE-1** (re-rule or close) | `scripts/check_freeze_window.py` | **rc 0**, `state=closed`, `closed_by: the owner 2026-10-17`, exit MET on both clauses, parked 12 (ceiling 12), **still OPEN 0**, released 3 |
They were already discharged; re-doing them would have been theatre. What was owed was a READING, and each now has one.

### f. NEW HARNESS FACTS (each with the reading that re-takes it; also written into AGENTS.md)
1. **`enabled:` is a gate on named provisioning.** Delegate lists are filtered by it, silently. Re-take: the child's
   own `enabled_extensions.v0` row (`20261017_15` vs `20261017_16`) — never the child's report of its tools.
2. **The per-session form does not consult `enabled:`.** `--with-extension '<cmd> <args>'` starts a DISABLED
   declaration (20261017_17). That asymmetry is the whole lever the extension policy rests on: a disabled declaration
   is available ON DEMAND, and never through a subagent's name list.
3. **The birth record names a stdio member by its COMMAND.** Four stdio members were supplied and the record holds
   three names (`python3`, `npx`, `uvx`), so two `uvx` members collapse into one row — BUG-879, and the reason an old
   record can show a "member" called `python3`, which is what made BUG-878 read wrong the first time.

### g. ONE GOVERNANCE CORRECTION (a live instruction that would have re-created a fixed bug)
BUG-854's residual sentence said the missing environment binding is "the one line for the owner's shell profile".
`pipeline/harness_env.py --print` refuses that in its own header: `# scope: agent_loop - bound FOR this class; never
place these lines in a login profile (BUG-871)`. A global cap + the 4B model in a login profile IS BUG-871. The entry
now carries a dated CORRECTION with the correct form (below), so the next reader is not led into it.

### h. WHAT THE OWNER STILL OWNS (exact command, no ambiguity)
1. **Bind the harness contract in the shell that LAUNCHES goose** (not a login profile, see §g). One line:
   ```
   eval "$(python3 pipeline/harness_env.py --print --scope agent_loop)"
   ```
   Reading after it, in that same shell: `python3 pipeline/harness_env.py --check` → rc 0 (it is rc 2 now: five names
   UNBOUND, which is the DECLARED-not-BOUND state, loud and not fatal, BUG-457).
2. **Nothing else.** `just go` needs no argument, no profile name, no per-session choice: it resolves `core`.
   `just session workshop` is the whole of the escape hatch when bulk file tools are wanted.

### i. NEXT CRITICAL STEPS, consequential order (each unblocked unless marked)
1. **T-183's applier** — pipeline lane #1, still untouched: 479 admission candidates have a corpus home and a derived
   target under the D-3062 share rule; nothing may move until a plan-keyed, dry-run-default, crash-safe
   (tempfile→fsync→os.replace), receipted writer exists that refuses a row absent from the signed plan, an existing
   target, or a run while the rename has not ridden.
2. **T-187** — the two-step/two-tool loop fixture: still the ONLY gate for any model promotion (and for the
   Qwen3-30B-A3B-Instruct-2507 candidate).
3. **T-190's toggle half** — `extensionmanager` still leaves no trace; the measured trigger is goose hooks
   `PreToolUse`/`PostToolUse`, with `SessionStart` as the birth receipt. `PreToolUse` is also where a "you are using a
   tool from an extension you are about to disable" guard would live.
4. **BUG-879** (new, LOW) — record the declared NAME as the member identity and keep `cmd` in its own field, so a birth
   can be audited member-by-member. Acceptance reading is written in the bug.
5. **BUG-876** — the attribution control cannot go green on `config/decisions.yaml` (no receipted post-image); still
   the one blocker preventing a loop agent from adjudicating a governed write.
6. **The four pstack ideas to port as OUR OWN single skills** (never the bundle): `prove-it-works`,
   `benchmark-checklist`, `deslop`/`unslop`, `interrogate`.
7. **The verified-but-unbuilt peer gap**: true progressive disclosure is impossible with static MCP schemas in goose,
   so `core` + delegate is the faithful approximation. Any future work on dynamic tool surfaces must NAME the gap
   rather than assume it closed.
8. **Pre-existing reds, unchanged this sitting:** `route_graph` 225 vs 222 (SHRINK-ONLY), `check_rail_mutations`,
   `check_config_defaults`, `check_bug_recall` (owner-owed class ceiling), `lib/handoff --selftest`,
   `check_silent_repair`, `check_undeclared_encoding`, `check_store_columns`, `reconcile`, `verify_generator_pins`,
   `check_tests`, `build_anchor_store_bridge`, BUG-875 (`pipeline`/`tools` remain PEP-420 namespace roots).

### j. HOW TO RESUME IN A FRESH SESSION (the read order, in this order)
1. `python3 scripts/goose_profile.py --check` → expect **rc 0**; `--render core` prints the realised surface. This is
   now the cheapest possible reading of "what my session is": ten extensions, ≈759 tok/request of measured schema.
2. `python3 scripts/check_freeze_window.py` and `python3 scripts/check_governance_faces.py --check` → both rc 0.
3. `just health` → ONE known red (`route graph`, 225 vs 222) plus the `harness_env` rc 2 until the owner runs §h.1.
4. Read D-3065 → D-3067 in `config/decisions.yaml` (the profile is RESOLVED; the default is `core`; the gate on named
   provisioning), then `config/extension_profiles.yaml` (policy) — never the handoff prose INSTEAD of them.
5. Then start at §i.1. Delegation remains: `sweep` (read-only repositories), `review` (judge one artefact),
   `extract` (summarise WITH source). Never: open-ended research, promotions, governed writes.

## §1i — EIGHTH SITTING (2026-10-17, afternoon): T-183's APPLIER IS BUILT (and decides nothing), the ONE DOOR BINDS ITS OWN CONTRACT, and the plan on disk was STALE

### a. What the owner asked (verbatim, trimmed)
"continue from previous session … So for clarification we don't need filesystem nor mcp git extension because
developer extension holds both? Or why is it disabled? And from now whenever I start a new session those 2 will be
disabled by default And I have to switch on when I want them — reliable intuitive solution … And since I don't know
how to implement do this: In the shell where you launch goose — not in ~/.zshrc: eval … first look in general maxwell
os current state, continue with the next critical step starting with the highest leverage step."

### b. THE THREE ANSWERS (the part the owner asked for in plain words)

**1. "Do we need filesystem / git MCP if developer holds both?" — No, and that is the measured reason they are off.**
`developer` gives `shell` (which runs `git` and reads any file), `write`, `edit`, `tree`. `filesystem` re-implements
read/write/search through a second server (**14 tools / 3,727 tok per request**) and `gitmcp-mcp` re-implements git
through a server (**12 tools / 1,906 tok**). Neither does anything `developer.shell` cannot do, and both are paid for
**on every request of every session**. D-3067 switched them off; **they were not deleted** — they are `on_demand`, they
still carry their `why:`, and the `workshop` profile still names them.

**2. "So from now a new session has them off and I turn them on when I want." — Yes, exactly, and it is ONE word.**
A new session is born `core`: ten extensions, **≈759 tok/request** instead of ≈6,392. When you want bulk file tools:
`just session workshop`. That is the whole escape hatch. If you want a narrower one: `just session research`,
`documents`, `web`, `recall`, `sandbox` (each adds only its own set). Nothing to edit, no config to remember. The two
things that DO NOT work, both measured: editing `enabled:` **inside** a running session (no effect until the next
birth — BUG-873), and expecting a subagent to receive a disabled extension by naming it (a child asked for
`[developer, filesystem]` was born with `developer` alone, session `20261017_15`).

**3. "How do I do the `eval` line?" — You no longer have to.** `just go` now binds the declared `agent_loop` contract
**for the child process it starts** and the binding dies with the session (D-3069). Proof, run this sitting with a
stand-in harness on PATH: `goose_profile.py --launch` printed `harness: 4 agent_loop name(s) bound for THIS process
only`, and the child read `GOOSE_MODEL=gemma-4-E4B-it-MLX-4bit GOOSE_CONTEXT_LIMIT=32768
GOOSE_PROVIDER=maxwell_omlx`. In a session born that way, `python3 pipeline/harness_env.py --check` reads **rc 0**.
If you ever launch `goose` **by hand** instead of through `just go`, that shell is unbound and `--check` correctly reads
rc 2 — the manual form (never in `~/.zshrc`, see BUG-871) is
`eval "$(python3 pipeline/harness_env.py --print --scope agent_loop)"`.
A shell that contradicts the declaration (`GOOSE_MODEL=something-else`) now **refuses the birth** instead of being
silently out-voted.

### c. STATE AT CLOSE (numbers, not impressions)
| thing | reading |
|---|---|
| decisions | **1,196** (D-3068 applier contract; D-3069 the door binds its child) |
| bugs | **645** — 234 OPEN / 411 CLOSED (BUG-880 filed **and fixed** this sitting) |
| open tasks | 59 |
| `goose_profile --check` | **rc 0**; `--selftest` **41/41** (3 new controls: the door binds; a contradiction refuses; an equal value is not a conflict) |
| `apply_admission --selftest` | **14/14** |
| `apply_admission` dry run | **479 rows / 8,271.5 MiB**, rc **2** (no signature yet — by design) |
| `plan_admission` (live re-derivation) | 2,811 files; 1,697 seen; **479 candidates**; 0 unresolved-home; 389 container-no-stage; 194 name-repair-first; 52 out-of-kind |
| `resolve_route --selftest` | **19/19** (new: a parametrised recipe header parses) |
| `resolve_route --check` | **RED (pre-existing only)**: routing debt 225 vs 222. No lane fault. |
| `gov_sync` / `check_governance_faces` | 4 faces equal their re-derivation; faces **rc 0** (1,196 decisions / 645 bugs) |
| `check_freeze_window` | **rc 0** — CLOSED, both exit clauses MET |
| `check_repo_integrity --worktree` | **rc 0** — 21 dirty paths, 21 granted by the session plan |
| R5 | gemma-4-E4B-it-MLX-4bit **APPROVE** on `scripts/apply_admission.py`, receipt `governance/r5_reviews.jsonl`, journal `DJ-20261017T122451Z-ec88` (39.2 s, 0 open) |

### d. WHAT LANDED
| thing | before → after | receipt |
|---|---|---|
| T-183's writer | did not exist → **`scripts/apply_admission.py`** | 14/14 controls; R5 APPROVE; `just admit-apply --dry-run` / `--limit N` / `--apply` |
| the authority | the plan alone → **plan + a SIGNED acceptance** (`governance/ADMISSION_ACCEPTED_<date>.yaml`) that pins the plan's **sha256** and names the rows (`mode: all\|listed`) | a digest mismatch is FATAL; a listed row the plan does not hold is FATAL |
| the plan artifact | **STALE**: `ADMISSION_PLAN_20261016` held the pre-D-3062 derivation (**244** rows, notes root with no home) | re-derived → `ADMISSION_PLAN_20261017.{json,md}` (479 rows) |
| the copy | — | C6 `tempfile → fsync → os.replace` **in the target dir**; never `--force` on S0 (force DISCARDS the stage0 checkpoint) |
| the trace | — | one fsync'd JSON line per row: source, both targets, key, source/md digests, plan+accept digests, `pipeline_commit`, `schema_version`, `gen_model` |
| the door | `just go` did not bind the contract | `just go` binds `agent_loop` for the CHILD (D-3069); refuses a contradictory shell value |
| the lane reader | `^name:` could not see `admit-apply *ARGS:` → **a live recipe read as absent** | BUG-880 fixed + control; lane `admit-apply` registered in `config/capability_registry.yaml` |
| harness checks | 38/38 | **41/41** |

**The applier refuses, by construction:** a row absent from the signed set; a target that exists unless a receipt
accounts for **that digest**; a source whose byte count moved; a name a declared defect pattern still matches (T-176
rides first); a path resolving outside the corpus home; a sheet with less free space than the batch needs. Dry run is
the default; `--dry-run` wins from the same door so a preview costs one word.

### e. THE FORENSIC AUDIT — what it found, in the order it found it
1. **THE PLAN WAS STALE, AND THAT WAS INVISIBLE.** The handoff said "479 rows"; the artifact on disk said 244 (derived
   2026-10-16, before the notes root declared a home). Both numbers were true of *different trees*. The applier is
   therefore **per-row verifying**: it re-derives the classification and refuses any accepted row that no longer reads
   `admit_candidate` with the same key. A stale plan cannot walk through it — and the artifact is now re-derived.
2. **THE COST IS REAL AND WAS NEVER ON SCREEN: 8,271.5 MiB** copied into the corpus (the library keeps its original;
   T-179's arrangement reading counts a same-work pair with EQUAL bytes as AGREEMENT, not drift, so this adds no
   drift — it adds storage). Hence `--limit N` tranches and the free-space guard.
3. **S0's `--force` WOULD HAVE ERASED THE CONVERSION LEDGER.** `run_stage0` sets `existing = {}` under force and
   rewrites the checkpoint from that empty set. The applier never passes `--force`; it uses the single-book path and
   refuses a filename collision instead (the door's key is a prefix of the name, so two rows cannot share a
   checkpoint key without sharing a key — which the reader already refuses upstream).
4. **A LANE CAN BE UNREADABLE WHILE ITS RECIPE RUNS.** BUG-880: `just --list` showed `admit-apply`, `just --show`
   printed the body, and the route graph said "the ladder file declares no such recipe". The parser, not the recipe,
   was wrong. Fixed with a control rather than by renaming the lane.
5. **A NAMED MIS-ATTRIBUTION OF MY OWN (D-3036): the R5 receipt.** The journal run above declared the artifact as
   `governance/r5_review_gate.jsonl` (this file's §1a.2 advice); the gate that actually ran,
   `scripts/r5_code_review.py`, writes **`governance/r5_reviews.jsonl`** (14:25). The presence check passed because the
   OTHER file exists — which is exactly the "an artifact it claimed but did not leave" shape. Recorded here, not
   papered over: **§1a.2's sentence is corrected in this paragraph** — `r5_code_review.py` → `r5_reviews.jsonl`;
   `r5_review_gate.jsonl` belongs to the tiered gate (syntax/lint/C11 layers), not to this one.
6. **Consumer sweep:** every touched consumer was re-read. `capability_registry.owns` gained the new script; the lane
   names the ACT (`--apply`) so it cannot collide with the health line's `--selftest` (the overlap check is substring-
   based and was right to fire); the session plan grants the two new plan artifacts **by name** (BUG-548: a widening
   that is only recorded is not granted).

### f. WHAT THE OWNER STILL OWNS (exact commands, no ambiguity)
1. **Nothing, for the harness.** Launch with `just go`. (Manual alternative, not in `~/.zshrc`:
   `eval "$(python3 pipeline/harness_env.py --print --scope agent_loop)"`.)
2. **Nothing, for the extensions.** `just session workshop` when bulk file tools are wanted; `just go` otherwise.
3. **T-183's rows — ONE file, and then one command.** The 2026-10-17 GO approved the **applier**, not the rows. To
   authorise a tranche, write `governance/ADMISSION_ACCEPTED_20261017.yaml`:
   ```yaml
   schema_version: "1.0"
   plan: governance/ADMISSION_PLAN_20261017.json
   plan_sha256: 2cc698921a64f605ba3e5cc5cc72d0e5d7fdde2fc7778732724e2c530895ea10
   accepted_by: barn
   accepted_on: "2026-10-17"
   mode: listed          # or: all
   rows:                 # `rel` labels exactly as the plan prints them (mode: listed only)
     - books/epub/DOMAIN 2 Design/communication+design/The Design of Everyday Things Revised and Expanded Edition.epub
   ```
   then `just admit-apply --limit 10` (preview first: `just admit-apply --dry-run`). The digest above is the one
   measured this sitting — **re-take it with `shasum -a 256 governance/ADMISSION_PLAN_20261017.json`** before signing
   if the plan is regenerated (a signature pins bytes, not a filename).

### g. NEXT CRITICAL STEPS, in consequential order (each unblocked unless marked)
1. **T-183, the owner's signature** — the writer is done; what remains is the word. A 10-row tranche proves
   S0 → S0.5 → S1 end to end for a few files, and the receipt turns the remaining 469 into a count.
2. **T-187 — the two-step / two-tool loop fixture**: still the ONLY gate for any model promotion (and for the
   Qwen3-30B-A3B-Instruct-2507 candidate). One tool cannot distinguish "drives a loop" from "calls once and guesses".
3. **BUG-876 — the attribution control** on `config/decisions.yaml`: still the one blocker preventing a loop agent from
   adjudicating a governed write (no receipted post-image).
4. **T-190's toggle half** — `extensionmanager` still leaves no trace; the measured trigger is goose
   `PreToolUse`/`PostToolUse` hooks, with `SessionStart` as the birth receipt.
5. **BUG-879** — the birth record names a stdio member by its COMMAND. It is a **harness-side** defect (the store is
   written by goose, not by this repo): the local half is `--born`'s mapping, the real fix needs the upstream record.
   Named as harness-side rather than promised here.
6. **The four pstack ideas as OUR OWN single skills** (never the bundle): `prove-it-works`, `benchmark-checklist`,
   `deslop`/`unslop`, `interrogate`.
7. **Pre-existing reds, unchanged this sitting:** `route_graph` 225 vs 222 (SHRINK-ONLY), `check_rail_mutations`,
   `check_config_defaults`, `check_bug_recall` (owner-owed class ceiling), `lib/handoff --selftest`,
   `check_silent_repair`, `check_undeclared_encoding`, `check_store_columns`, `reconcile`, `verify_generator_pins`,
   `check_tests`, `build_anchor_store_bridge`, BUG-875 (`pipeline`/`tools` remain PEP-420 namespace roots).

### h. HOW TO RESUME IN A FRESH SESSION (read order)
1. `python3 scripts/goose_profile.py --check` → rc 0; `just go` → the door binds its child (msg on stderr).
2. `python3 scripts/check_freeze_window.py` and `python3 scripts/check_governance_faces.py --check` → rc 0.
3. `just health` → ONE known red (`route graph`, 225 vs 222) and nothing else.
4. Read **D-3068 → D-3069** in `config/decisions.yaml`, then `config/ingest_identity_gate.yaml#source_library.admission.applier`
   (the contract), never this prose INSTEAD of them.
5. Then start at §g.1. Delegation unchanged: `sweep` (read-only), `review` (judge one artefact), `extract`
   (summarise WITH source). Never: open-ended research, promotions, governed writes.

### i. ADDENDUM (same sitting, after the first commit): A RAIL CAUGHT WHAT THE REVIEW DID NOT

`check_agent_surface.py` went RED on the FIRST draft of D-3069's controls: the selftest named a client variable
literally (`"GOOSE_MODEL"`) as a fixture, which is a **binding site outside an adapter root** — the exact class
BUG-845/D-3042 exists to refuse. R5 had already APPROVED that file; the rail was the verifier that noticed. Fixed at
the DECLARATION (the probe name is now READ from `pipeline.harness_env.declared()`), not by declaring an exception:
`check_agent_surface` rc 0, `goose_profile --selftest` 41/41. Recorded because it is the argument for keeping the
rails rather than trusting a review: a reviewer judges prose, a rail reads bytes.

### j. ADDENDUM 2: THE SIGNATURE IS PRINTED, NOT TYPED (same sitting)

The step most likely to fail was the human one: copying a 64-character digest into a YAML file. `--template` now
prints a ready-to-sign acceptance with the **LIVE** digest already pinned, so signing is one redirect plus a name:

```bash
python3 scripts/apply_admission.py --template > governance/ADMISSION_ACCEPTED_20261017.yaml
# edit accepted_by; optionally set mode: listed and the rel labels for a tranche
just admit-apply --dry-run     # price it: rows + GiB, writes nothing
just admit-apply --limit 10    # the first tranche
```

A control (`the_acceptance_template_parses_and_pins_the_live_digest`, 15/15) fails if the printed signature ever
stops matching the plan it names. §f.3's hand-written template is therefore **SUPERSEDED by this paragraph** — it
still works, but the printed one cannot be mistyped.

---

## §1j — NINTH SITTING (2026-10-17, 14:46): THE FIRST REAL RUN OF THE APPLIER FOUND FOUR DEFECTS (all fixed, all controlled), ONE OF THEM HIGH — and the SITTING'S BIGGEST FINDING IS THAT THE HOUSE'S OWN "only gemma can do multi-turn" RULE NO LONGER HOLDS

Append-only. Nothing above is rewritten; where this section contradicts an earlier one, THIS section is the reading,
and the earlier one stays visible as the history of how the belief was formed.

### a. WHAT THE OWNER'S COMMAND ACTUALLY DID

`just admit-apply --dry-run` — the first run of the applier with a (unsigned) acceptance on disk — printed
`TypeError: 'str' object is not callable`. That single command then produced four bugs, one of them HIGH. None of the
four was findable by reading the file: each fell out of RUNNING THE DOOR THE OPERATOR RUNS.

| bug | severity | what it was | state |
|---|---|---|---|
| BUG-881 | MED | a local `stamp = <str>` binding in `run()` shadowed the module's own `stamp()`, and all 15 controls called `stamp()` directly — they tested the UNIT, the crash lived in the COMPOSITION | FIXED + 2 controls (planted shadow found; this file's own bytes clean) |
| BUG-882 | MED | the DRY RUN hashed every source: 8,271.5 MiB read to PRICE the plan, >300 s stall on one unmaterialised Dropbox PDF (row 309). The price is now `stat` only, 17 s | FIXED + 2 controls (dry run leaves the digest EMPTY; the ACT takes it) |
| BUG-883 | **HIGH** | the door's key was NOT NFC-normalised: the corpus held `Galič` precomposed (U+010D), the library held `c`+U+030C for the SAME work, so ONE work had TWO identities | FIXED at the one producer, D-3070 |
| BUG-884 | LOW | a governed refusal crashed while reporting itself: `int(exc.code)` on a SystemExit whose code was the MESSAGE → `ValueError` instead of "the acceptance pins digest X but Y hashes to Z" | FIXED + 2 controls (message → RC_FATAL, integer kept) |

### b. WHY BUG-883 IS THE ONE TO REMEMBER

It is the first defect in this sitting that would have produced **silent duplicate knowledge**, not a missing step:

1. the reader called a work the corpus HELD a NEW admission candidate (479 instead of 477) — so the owner's signature
   would have covered a row that must refuse;
2. `refused_name_repair_first` over-counted (194 vs 179) — a *name defect* class absorbing names that were merely
   spelled differently, which is the wrong ontology for T-176;
3. **macOS hid it.** Its lookup is normalisation-insensitive, so the applier's `target.exists()` caught the collision
   and refused. On Linux — C26 names it as a target platform — that same check is FALSE and the applier would have
   **created the twin**, with the ingest door keying the two copies apart forever.

The cure is one line at the ONE producer (`pipeline/book_metadata.sanitize_source_book`), chosen for IDEMPOTENCE: NFC
leaves every already-NFC name's key untouched, so nothing persisted is re-keyed and no migration is owed. Rejected:
a casefolded/accent-stripped comparison (it MERGES different works), normalising at each comparison site (a second
home for the rule), and renaming the files now (that is the owner-gated `normalise_corpus_names`, and it fixes the
FILES while leaving the IDENTITY rule broken for the next arrival).

The 14 measured NFD names (6 corpus, 8 ingest-cache) now resolve. Renaming the 6 corpus files is still the owner's.

### c. THE FINDING THAT CHANGES POLICY — the "only gemma" rule is a measurement artefact, not a capability

The standing sentence, in `AGENTS.md` and in `DELEGATE-002`, is: *Qwen3-Coder's multi-turn decode collapses (~6.8 →
0.4 tok/s) as agent context grows; gemma-4-E4B is the only confirmed multi-turn model.* MEASURED TODAY, on this
machine, one command each:

```
Qwen3-Coder-30B-A3B-Instruct-MLX-4bit   5,900-token prompt   ttft 0.58 s   cached 5,888/5,894
gemma-4-E4B-it-MLX-4bit                 5,896-token prompt   ttft 0.50 s   cached 5,893/5,896 (after a 11.8 s load)
```

**The prefix cache is WARM.** BUG-792 recorded `cached_tokens = 0` on every call on 2026-10-14 and declared the
question `disproven`; that state does not reproduce. A 6k-token agent turn costs ~0.5-1.9 s of prefill, not a full
re-read — which is the whole mechanism the "collapse" story blamed.

And the capability question, asked directly (2 tools, 1 dependent instruction, same prompt to four served models):

| model | prompt | ttft | decode | tool call |
|---|---|---|---|---|
| Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | 5,900 | 1.87 s | 34.5 tok/s | `read_file{"path":"governance/buglog.md"}` |
| gemma-4-E4B-it-MLX-4bit | 5,901 | 0.77 s | 30.8 tok/s | same |
| Ornith-1.5-35B-A3B-REAP-19B | 5,902 | 42.9 s (LOAD) | **210.6 tok/s** | same |
| Qwen3.8-27B-MLX-4bit | 5,904 | 134.3 s (LOAD) | 8.2 tok/s | same |

Four of four emitted a correct tool call with the correct argument. That is ONE probe and it promotes NOTHING —
T-187 (two tools with a distractor, two DEPENDENT steps, an answer only the second tool's output can produce) remains
the only gate. But it does dispose of "the rest are useless": what was measured before was a COLD MODEL LOAD
(42 s, 134 s) plus a cold prefix, and a delegate that hits a cold load looks exactly like a model that cannot think.
The correct state word for the other three is **UNMEASURED**, and BUG-885 holds the reading.

**So: is there no reliable candidate on HuggingFace?** No — that conclusion was never measured. What exists and is
MLX-convertible at a size this machine can hold (all confirmed present on the hub today): **Qwen3-30B-A3B-Instruct-
2507** (the INSTRUCT refresh, not the coder variant that collapsed; 3B active params), **Devstral-Small-2507** (24B,
built for agentic coding loops), **Hermes-4-14B** (function-calling tuned), **granite-4.0-h-small** (compact, tool-
trained), and **GLM-4.5-Air** (106B — outside the 24 GB delegate budget; do not). The house already serves a 19B-class
MoE at 210 tok/s. The missing thing is not a model. It is the fixture that decides between them, which is T-187.

### d. THE THREE SOURCES THE OWNER ASKED ABOUT — what to borrow, what to refuse

**leanrea (`github.com/aicodeking/leanrea`) — ADOPT THE PATTERN, not the package.** It is ONE 8 KB `SKILL.md` that
replaces an MCP server's 207 tool definitions. Measured on 4 RE tasks × 3 reps: 34.5k tokens of context vs 400.7k
with every tool loaded, 38% less wall time, 56% fewer turns, **same accuracy (74/75 vs 75/75)**. That is the same
finding this house already paid for twice — filesystem + gitmcp-mcp cost 5,633 tokens on EVERY request (T-186/D-3067)
— and it is the exact shape the four pstack skills should take: a decision table, ready-to-paste commands, and the
traps. Never a tool schema. No third-party integration is needed or wanted: the artifact is a paragraph of Markdown.

**vibe-kanban (BloopAI, 28.4k stars; `vibekanban.com`) — BORROW TWO IDEAS, refuse the product.** Its thesis is "the
bottleneck moved from writing to planning and reviewing". Its mechanics: one **git worktree per card** (parallel
agents cannot collide), a **card state machine** (todo → in-progress → review → done), and **agents as swappable
executors**. Maxwell OS already owns all three in different homes — `worktree` isolation is BUG-563's grant/exclude
machinery, the state machine is the task register's `mover:` field, the executor swap is the route graph. What is
missing is the ONE VIEW: a read-only board that shows, per open row, which agent holds it, what it has written, and
what is waiting for the owner. That is a projection over `config/task_register.yaml` + `delegate_journal status` +
lane receipts, i.e. a `just board` — no server, no MCP, no new state.

**`github.com/topics/agent-orchestration` — almost nothing is worth porting.** The recurring patterns are supervisor/
worker, blackboard, event bus, durable checkpointing and human-in-the-loop gates. This house already has a stricter
version of each: routes (capability → script), the registers (blackboard), receipts + journal (durable checkpointing,
fsync'd), and rc 2 = OWNER-OWED (the gate). The gap the topic exposes is the same one as above: **observability of
live subagents**, and the cheapest honest answer is the journal plus the board — not an orchestrator. Porting a
framework here would buy schemas, not capability, and would violate C1/C3/C4 in one move.

### e. WHAT THE OWNER OWNS NOW (exact)

1. **T-183, one file and one command.** `governance/ADMISSION_ACCEPTED_20261017.yaml` was RE-PRINTED from
   `--template` (the old file pinned the pre-fix digest and is now refused BY DESIGN). Set `accepted_by: <name>`,
   then:
   ```
   just admit-apply --dry-run          # 477 would_apply, 0 refusals, rc 0   (MEASURED, 17 s)
   just admit-apply --limit 10         # the first tranche, one receipt line per row
   ```
   For a tranche that is NOT the first 10, set `mode: listed` and copy the `rel` labels exactly as the plan prints
   them. If the plan is ever re-derived, re-print the signature — a signature for different bytes is refused, which
   is the point.
2. **The 6 NFD corpus names** are read correctly now; renaming the FILES is the owner-gated path
   (`python3 scripts/normalise_corpus_names.py --census`, T-130). Nothing is renamed automatically.
3. **Nothing else.** Launch with `just go`; `just session workshop` is the whole escape hatch.

### f. NEXT CRITICAL STEPS, in consequential order

1. **T-183's first tranche** (`--limit 10`) — the only remaining act, and it exercises S0 → S0.5 → S1 before scale.
2. **T-187** — now the highest-leverage build in the house, because BUG-885 turned "which model" from a preference
   into a measurable question and the fixture is what measures it. Two tools with a DISTRACTOR, two DEPENDENT steps,
   an expected answer only the second tool's output can produce, same served set, a receipt; and it must report
   DECODE RATE and TTFT per step (the numbers in §1j.c are the baseline it has to beat).
3. **BUG-885's owed close** — re-run BUG-792's declared protocol; either close it with today's reading or name the
   variable that changed. Until then `AGENTS.md`'s DELEGATE-002 sentence is a claim the machine no longer supports,
   and `AGENTS.md` is PROTECTED: revising it is the owner's edit, and this section is the evidence for it.
4. **BUG-876** (attribution control cannot go green on `config/decisions.yaml`) then **T-190's toggle half**
   (`PreToolUse`/`PostToolUse` hooks) then **BUG-879**.
5. The four pstack skills, in leanrea's shape (one SKILL.md each, zero tools): `prove-it-works`,
   `benchmark-checklist`, `deslop`/`unslop`, `interrogate`.

### g. STATE AT CLOSE

`apply_admission --selftest` **22/22**; `plan_admission --selftest` **20/20**; census 18/18; plan_source_rename
11/11; normalise_corpus_names 10/10; ingest_identity_gate 20/20; book_metadata pytest 9/9; R5 APPROVE on both
changed files (gemma-4-E4B-it-MLX-4bit). Plan: **477 rows**, sha256 `191a13e3498f5f4d92e683b03370d3148ae76635972fbe
b41b033c260ef2c17d`. Decisions 1,196 → 1,197 (D-3070). Bugs 645 → 650 (881-884 FIXED, 885 OPEN).
Dry run: 477 would_apply / 0 refusals / rc 0 / 17 s.
