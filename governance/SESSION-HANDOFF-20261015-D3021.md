# SESSION HANDOFF — D-3020/D-3021: delegation made durable, and the six defects its acceptance run dragged into the light

**Date:** 2026-10-15 · **Commit:** `d5aae94` + `5efb97f` · **Authority:** D-3020, D-3021 · **Owner demand:** *"SEEMS LIKE DELEGATION DOESNT WORK … can you fix BUG 809 and make delegation durable and having proper guards to prevent timeout and other blindspot, gap, conflict, cascading issues, hidden error, failure"*

## 1. The leverage call

The owner's standing rule is to delegate to save tokens and parallelise. On 2026-10-15 that advice produced
**two more failed delegate calls in one session** (one empty response, one cancelled) while "running for so long
without any result". BUG-809 had already been filed for exactly this — and its remedy was a **rule a human had to
remember** (write the report first, summarise in chat). A rule that must be remembered is not a fix: it failed
again 8 days later. So the highest-leverage act was not another rule. It was to make the delegation path
**prove its own health**, and then to RUN it, because an instrument that has never been exercised is a hypothesis.

The measurement changed the shape of the answer three times (see §3): the executor built to enforce the earlier
rule was itself lying about success, the pool cap was silently stranding a task, and the deletion batch that had
landed minutes before was overstating its own reclaim by 2.07x.

## 2. What the fix IS (three layers, all landed and exercised)

| layer | home | what it guarantees |
|---|---|---|
| DURABILITY | `pipeline/research_run.py` | a task runs **detached** (own session, own process group), so no user message, cancelled turn or compaction can reach it; the deliverable is a **file**, never a return value |
| GUARDS | `pipeline/subagent_fanout.py` | one front door `run`: plan → start under the pool cap → reap to a declared deadline → ONE retry by a **different** model → receipt. `doctor` refuses to start an unsound run (missing guards, an unserved model, a retry target that is the failing model, a RUNNING row with a dead process). Exit codes are honest: 0 all DONE, 2 still running at the deadline, 1 a task failed |
| LIVENESS + BUDGETS | `config/engine.yaml#fanout.guards` + `research_run watch` | 120 s for a oneshot (measured answers land in **0.4–17 s**), 600 s for an agent loop, a **900 s run deadline**, a 45 s stall threshold, a per-task `timeout_s`; a **reaper** enforces the budgets with nobody polling — the defect behind "it seems stuck" |

The owner's rule — *if a task can be answered faster than the old blanket 1800 s, budget it that way* — is why the
oneshot budget is 120 s and not 1800 s, and why a task may declare a tighter budget of its own.

## 3. What the acceptance run exposed (six defects, all measured, all fixed)

One live run (`temp/runs/fanout_20261015i`, **3/3 DONE, rc=0, 65 s**, one task deliberately given a 1 s budget:
reaped at 2.2 s → retried on gemma-4-E4B → receipt carries both attempts) exposed four lies in the instrument
itself, and two more in the deletion batch that had landed minutes earlier:

| # | defect | class |
|---|---|---|
| 1 | every planned command ended `TERMINAL: DONE - oneshot rc=$?` — a oneshot that exited 1 was recorded as **DONE** | BUG-824 / BUG-817 class: a failed answer read as a success, inside the instrument that reports delegation health |
| 2 | no reaper: `timeout_s` was consulted only if somebody happened to call `status()` | BUG-824 — "runs so long without any result" |
| 3 | no liveness: a hung child and a working child read identically | BUG-824 — fixed by measured `idle_s` vs declared `stall_s` |
| 4 | `started + _running(run_id) >= cap` counted each launch twice → the third of three tasks was **never started**; the receipt printed `2/4 usable` for a run that answered everything | BUG-824 — a silent gap, and a receipt that under-reports success |
| 5 | a terminal record never stamped `t1`, so its `elapsed_s` kept growing after the process died (`55.1 s` for a task that stopped at 2.2 s) | BUG-824 — a lie about duration |
| 6 | the deletion receipt summed `st_size` over a recursive walk, counting a hub **blob** and its **snapshot hardlink** as two files: claimed **30.66 GB freed**, `du` showed **14.83 GiB** (calibration on surviving repos: factor **exactly 2.000**); and the batch read the census's documented `rc=2` (orphan proposals) as "the census did not re-run", **printed a warning and exited 0** while the census face never moved | BUG-825 / BUG-807 / BUG-819 class |

## 4. Forensic audit (run BEFORE the acts, and with them)

| check | result |
|---|---|
| D-3013: does an engine entry resolve INTO a swept repo? (a name pointing at nothing) | **CLEAN** — 8 entries in `~/.omlx/models`, 1 in `_unloaded`, 1 in `models_stashed`, none targets a swept repo |
| is the phase-B safety guard satisfied? | it **REFUSED** the first attempt on `scripts/benchmark_domain_taxonomy_match.py:120`, which genuinely LOADS `MoritzLaurer/bge-m3-zeroshot-v2.0`. The guard was right and the audit was wrong: that repo moved SWEEP → **KEEP-pending** (its D2613 comparison is not yet recorded; D-3014 makes a model deletable only after its comparison IS) |
| duplicate keys in config | **16 scopes** in `config/engine.yaml` (`model_store`, `harnesses.jobs`, `hf.lock_dir/lock_suffix/duplicate_fragments`), all from one anchor insert applied twice by *my own* phase-A landing. De-duplicated; the checker now reports **135/135 clean** |
| a governed config that does not parse | `config/intake_sources.yaml` failed to load (21 rows written as `- class: video {…}`) **and nothing in the repo reads it** — a declaration that could not fail loudly (BUG-823) |
| census face movement across a 14.83 GiB deletion | **did not move at all** (byte-identical to HEAD; `hub_bytes` 0.15 GiB) → T-151 |
| disk truth | `du` 153.50 → 138.67 GiB. Free space on `/` went 230 → **244 Gi** (+14.8 GiB) — the honest number confirmed by a witness outside the receipt |

## 5. Residuals (declared, not implied)

- **An in-process harness subagent is still cancellable by the next user message.** That is the harness's own
  contract and not something this repo can patch. What changed is that **no load-bearing delegation depends on it
  any more** (T-150); it is allowed only for work whose loss costs nothing.
- **`kill_on_stall: false` by default.** A stalled task is *reported*, not killed on suspicion, because a slow
  local model is not a failure — the declared `timeout_s` is what kills it. Set per task if a stricter policy is
  wanted.
- **The census face is still hand-cut** (`governance/model_store_census_20261015.json`). Phase b now RAISES if it
  does not move, so the batch cannot lie — but the face itself must be made the instrument's output (T-151).
- **Hardlink-aware measurement is not universal.** `physical_bytes()` lives in the land script; any other
  instrument that sums file sizes over a hub repo inherits the same 2x overstatement.
- **BUG-721's other half.** That bug records a delegate that *returned a FABRICATED verdict without reading the
  code*. Durability does not fix trustworthiness: the guards here (a graded answer, a premise gate `expect:`, and a
  cross-family verifier that never sees the generator's reasoning) make fabrication **detectable**, and R5 makes
  the generator its own checker nowhere. It does not make it impossible.

## 6. Delegation (honest account)

- The **R5 review was itself run through the durable path**: two review tasks handed to `gemma-4-E4B-it-MLX-4bit`
  (a different family from the author) as detached workstreams while the parent kept working → **2/2 DONE**
  (`temp/runs/fanout_20261015j/98_receipt.json`). This is the doctrine's rule that a subagent's output is a
  **PROPOSAL in temp/, never a verification** (D-3011).
- **The reviewer earned its keep**: it found that a task whose process exited non-zero while holding a perfectly
  **usable** answer was still buying a retry. **ACTED ON** — `retry()` now refuses to re-ask a task that already
  has a usable answer, because judging a usable-but-odd answer is the verifier's job, not the pool's
  (`--selftest` 21/21).
- **Rejected, with the reason**: the reviewer also asserted that `answer_verdict()` is checked before `rc`, i.e.
  that a failure could still read as success. Its own quotation of the code contradicts it — `grade()` sets DONE
  only when `ok **and** rc == 0`. Rejected on the text, not on the authority.

## 7. Next critical steps (ordered, with the actor)

| # | step | actor | why now |
|---|---|---|---|
| 1 | **T-149** wire the two guards that already exist into `just preflight` (`scripts/check_config_duplicate_keys.py` + `subagent_fanout.py doctor`) | pipeline | both 2026-10-15 defects were catchable by instruments that existed and were never called |
| 2 | **T-150** make `subagent_fanout.py run` the default for anything whose failure is not free | pipeline | completes the BUG-809 fix: the durable path must be the path |
| 3 | **T-151** make the census face the instrument's output | pipeline | a face that does not move is a face that lies (BUG-819) |
| 4 | **T-144** route the first harness job (`eval "$(python3 pipeline/harness_env.py --print)"` then `omlx launch pi`) | **owner** | one line; D-3017 declares `agent_loop → pi` and nothing has run it |
| 5 | **T-145** override DEFER on Edge0 by saying so, or leave the named trigger in place | **owner** | a DEFER with a named trigger needs no action |
| 6 | **T-146** put the Zed CLI on PATH (`ln -s /Applications/Zed.app/Contents/MacOS/cli ~/.local/bin/zed`) and use it as the review surface | **owner** | Zed is a review surface, not a delegate target (D-3019) |
| 7 | **T-152** give `config/intake_sources.yaml` a reader, or mark it proposal-only | pipeline | it now parses, but nothing loads it |
| 8 | **T-148 / BUG-821b** make `scripts/recompute_decision_summary.py` the ONLY census writer | pipeline | the mint in `temp/` and the declared home in `scripts/` each report the other as the drift |

## 8. C15 — the register's open population (220 open, 368 closed; threshold 5, append to handoffs)

The 25 HIGH bugs are the live risk surface. The ones a delegation-heavy session must not lose sight of:
`BUG-721` (a delegate fabricated a code-review verdict), `BUG-815` (a headless agent run was not bound to the local
engine and went elsewhere), `BUG-817` (a failed edit read as a success — the class this session found three more
instances of), `BUG-400` (the sovereign store lives inside a Dropbox File Provider domain, C3/C22), `BUG-705`
(S5 recall path still pending code, 2,258 neutral rows recoverable), `BUG-701`/`BUG-700` (cross-generation identity
gap), `BUG-711` (173 canonical rows carry a displaced domain label), `BUG-749` (1,072 rows carry a discipline the
live mapper does not produce), `BUG-766` (the store-columns register holds two defects the ladder is RED on),
`BUG-391` (the ratified abstention operating point is not reproducible on the ruler in force).

**One line for the owner:** `eval "$(python3 pipeline/harness_env.py --print)" && /Users/barn/.omlx/bin/omlx launch pi`
