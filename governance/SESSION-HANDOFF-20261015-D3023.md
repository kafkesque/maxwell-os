# SESSION HANDOFF — 2026-10-15 — D-3023/D-3024/D-3025: the delegation economy, measured

> Continues governance/SESSION-HANDOFF-20261015-D3022.md. Commits: cffa063 (this turn), 969ab99 (the plan
> widening), on top of 1dcc655. Faces at close: 1153 decisions / 596 bugs (223 open) / 50 open tasks.

## 1. Why THIS and not the declared next step (T-154)

The owner asked a strategic question — how to make delegation, harnesses, skills and scripts cheaper, more
reliable and more reusable, what may be loop- or graph-engineered, and what prior art applies. The highest
consequential act was not another fix: it was that **nothing in this repository measured the delegation
economy at all**, so "cut cloud cost" and "route to local models" were both unanswerable claims. That gap is
now closed with an instrument, and the answer it produced is sharper than the question expected.

MEASURED (pipeline/delegation_economy.py, new, 14/14 selftest):

| tier | calls | input tokens | output | cost |
|---|---|---|---|---|
| local | 379 | 3,667,410 | 144,968 | $0.00 |
| cloud | 32,851 | 3,981,322,921 | 57,008,294 | $105.42 (estimated) |
| unclassified | 1 | 156,098,139 | 1,249,089 | $7.35 (carried_forward) |

The local fleet carried **0.09%** of the input tokens while it sat idle. The cloud burn is **~$2.35/day**.
That reframes the whole question: the money is small, so trading the session brain down to a small local
model to "save cost" would be the wrong trade. The real leaks are (a) sovereignty — 99.9% of the tokens leave
a machine with a served local fleet (C1/C3), and (b) VOLUME: ~92k input tokens per cloud call, mostly
re-reading registers (the declared knowledge sources total 3.96 MB, ~990k tokens if read whole).

## 2. What landed

| object | witness |
|---|---|
| config/delegation_economy.yaml (new home) | ceilings, tier vocabulary, escalation reasons, homes it reads |
| pipeline/delegation_economy.py (new instrument, the ONLY reader) | --selftest 14/14; 12 known-answer controls; --check rc 0 |
| justfile: economy recipe + two health rails | the selftest and the gate are CALLED, not declared (BUG-482) |
| config/declaration_consumers.yaml: the new declaration names its reader | the join resolves for the commit set (BUG-562 shape) |
| D-3023 (economy, ceilings, SHRINK-ONLY) | ACTIVE, cites BUG-832 |
| D-3024 (route graph declared, deterministic; the LLM PROPOSES) | ACTIVE, cites BUG-482/BUG-827 |
| D-3025 (a loop names its terminal condition and its CHECKER) | ACTIVE, cites BUG-721/BUG-827 |
| governance/ORCHESTRATION_ECONOMY_20261015.md | the analysis, the loop verdicts, the prior-art delta |
| BUG-832, BUG-833, BUG-834 | filed with MEASURED / ROOT / REMEDY / EVIDENCE |
| T-156..T-160 | filed MUST/MUST/SHOULD/WORTH/MUST |

## 3. The three structural answers (short form)

1. **Route by KIND and TIER before model choice** (D-3023): T0 deterministic script, T1 local engine, T2
   cloud; a cloud call is an ESCALATION with a reason and a SHRINK-ONLY ceiling. Money is the SECOND fact.
2. **The route graph is DECLARED and DETERMINISTIC (D-3024)**: a capability registry (kind, entrypoint,
   CHECK, cost tier, receipt) with a resolver that COMPOSES the joins that already exist
   (declaration_consumers, flag_consumer_registry, harness_policy, engine.yaml#harnesses.jobs,
   model_assignments). An LLM may propose into temp/ and never assign — D-2898/D-2941 applied to tools.
   Goose recipes and skills are THIN WRAPPERS over repo entrypoints: ~/.config/goose is not versioned.
3. **A loop names its terminal condition, its checker and its budget before it runs (D-3025)**: admissible
   where the checker is a READER; refused where the checker is the generator (multi-agent debate,
   self-grading loops).

## 4. Forensic audit — what verifies what

* config_audit --check-unchecked --strict: rc 0 (the three rc constants are registered with a reason).
* just preflight: PASSES end to end (config audit, duplicate keys 135/135, doctor, stress test).
* gov_sync --apply: 4 face(s) equal their re-derivation (1153 / 596 / 50).
* The commit set passed all three write gates: recalibration pins 16 staged / 0 RED; declaration consumers
  10 homes / 13 edges resolve; session plan 16 paths all declared.
* The instrument reads the engine's model registry as the LOCAL set via the home
  config/agent_context.yaml#homes.served_window (12 models) — no list of local models is written down.
* NOT verified (declared, not implied): the R5 cross-family review of the new instrument DID NOT HAPPEN —
  it was blocked by BUG-833 (see 5). The instrument has been read by nobody but its author. Its selftest is
  strong and its refusals are pinned, and that is not the same as an independent read.

## 5. The two delegation paths both failed this turn, and both failures are filed

* the DURABLE path (pipeline/research_run.py -> pi -> the local engine) ran a workstream with an ABSENT
  prompt: pi was launched with an empty -p, exited 0, wrote 0 bytes, and the ENGINE WAS NEVER CALLED
  (witness chat_completions 232 -> 232 where the two prior jobs moved it 223 -> 226 and 226 -> 232). The
  grader's verdict was honest (EMPTY) and its rc was a lie (0). Filed as BUG-833, tasked as T-160.
* the IN-PROCESS path (the delegate tool) returned a handle that did not resolve ("Task '20261015_13' not
  found"), so the deliverable was unretrievable in the turn that needed it. Filed as BUG-834.
* Consequence to carry forward: the standing rule "delegate to the most reliable local LLM" needs the durable
  path to be TRUSTWORTHY first. T-160 is therefore on the critical path of every future delegation.

## 6. C15 — the open register this handoff must carry (>= 5 unresolved)

223 open bugs. The ones a delegation-heavy session must not lose: BUG-833/834 (this turn's), BUG-832 (the
session brain), BUG-828 (the harness is not bounded by its class's budgets), BUG-721/827/831 (fabricated
verdicts; now mechanically detectable), BUG-829 (Zed's cloud default model), BUG-817 (a failed edit read as a
success), BUG-815 (a headless run not bound to the engine), BUG-811 (an instrument that lied three times),
BUG-803 (the pool is a mutex), BUG-400 (sovereign store inside a Dropbox File Provider domain), BUG-705,
BUG-700/701, BUG-711, BUG-749, BUG-766/767, plus the 66 UNLABELLED open bugs whose severity nobody has
triaged (T-104/BUG-757) — which is why "how many hidden bugs are there" is currently unanswerable.

## 7. Ordered next steps

| # | act | actor |
|---|---|---|
| 1 | **T-160** — refuse a workstream with no prompt; the exit code follows the STATE | pipeline |
| 2 | **T-157** — census the harness homes a decision names (the reading that would have caught BUG-832) | pipeline |
| 3 | **T-156** — the capability registry + the deterministic resolver | pipeline |
| 4 | **T-154** — bound the harness the way its class declares (BUG-828); then re-run the R5 review of delegation_economy.py | pipeline |
| 5 | **T-104/BUG-757** — triage the 66 unlabelled open bugs so the register can be ordered at all | pipeline + owner |
| 6 | **T-153** — measure the resident Ornith-1.5-35B at 26214 tokens; the verdict on T-145 | pipeline |
| 7 | **T-158 / T-159** — the context diet; the prior-art delta into the intake register | pipeline |
| 8 | **BUG-832** — decide the session brain (D-295 vs an amended, ceilinged opt-in) | OWNER |
| 9 | **T-145** — fetch Edge0, or accept T-153 as the release test (no action keeps the deferral) | OWNER |
| 10 | **BUG-829 / T-146 residual / T-144 residual** — Zed's default model; one panel look; one write-capable harness job | OWNER |

## 8. Owner manual acts, with their exact files

| act | file |
|---|---|
| decide the session brain (D-295's remedy is not in force; BUG-243's close rationale is false) | ~/.config/goose/config.yaml line 311 (active_provider) and lines 273-276 (providers.custom_deepseek) |
| bind Zed's agent panel locally, or record the cloud default as an explicit OPT-IN (C22) | ~/.config/zed/settings.json (agent.default_model) |
| T-145: fetch Edge0, or accept T-153 as the release test | no file needed; one word |
| raise a ceiling (only if the work genuinely needs to leave the machine) | config/delegation_economy.yaml#ceiling — an edit is NOT the mechanism; the word is |

## 9. Honest delegation account

Delegated this turn: one in-process delegate (returned a handle that did not resolve — BUG-834) and one
durable harness job (ran with an empty prompt — BUG-833). Both were supposed to be the R5 read of the new
instrument; both failed, and both failures became filed defects. Everything else — the reconnaissance, the
instrument, the config, the decisions, the register edits — was done by this session. The measured reason the
local fleet carried 0.09% is therefore not that nobody tried: it is that the two delegation paths are each
one control short of trustworthy, which is exactly what T-156 and T-160 exist to fix.
