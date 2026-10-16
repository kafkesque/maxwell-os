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
