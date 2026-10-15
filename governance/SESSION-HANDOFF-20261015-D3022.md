# SESSION HANDOFF — 2026-10-15 — T-144, T-146, T-149, and the guard that read nothing

**Task order this session:** DO T-144 (route the first harness job) · DO T-146 (Zed) · explain T-145 and decide
defer-vs-fetch · look at the general state · then take the highest-leverage next step. Decision minted: **D-3022**.

---

## 1. The leverage call

The owner's standing rule selects the most consequential next move. Three things were true at once:

- **T-144 was the only task that could produce a MEASUREMENT**, and the measurement it produces is the one the
  whole delegation priority rests on: does the deployed `agent_loop` model actually do work, bound to the
  sovereign engine? It had never been run. Routing existed; the first job did not.
- **T-149 was one line of work that makes two existing guards real** — and it is the direct descendant of the
  owner's rule that a guard which is never called is not a guard.
- **T-146 was mechanical** (a symlink plus two questions that had been left unverified for a day).

So: run T-144, wire T-149, close T-146, and let whatever the first real job exposed decide what came next.
It exposed a great deal.

## 2. What landed

| # | Act | Result |
|---|---|---|
| T-144 | **The first harness job ran**, detached, read-only, with the engine log as witness | `agent_loop` → `pi` → `gemma-4-E4B-it-MLX-4bit`; 3 engine turns; 75 s of a declared 300 s; graded DONE — **and the deliverable was refuted** (BUG-827) |
| T-146 | Zed CLI on PATH + both owed questions answered from the installed artifact | `~/.local/bin/zed` → Zed 1.9.0; **reads AGENTS.md: yes**; **hosts external agents: yes (ACP)**, and the owner's own settings already declare `pi-acp`; **finding: its own agent defaults to a cloud provider** (BUG-829) |
| T-149 | Both existing guards wired into `just preflight` | duplicate-keys 135/135, doctor green; preflight now reaches them and continues — **verified inside the real recipe** |
| BUG-826 | **The delegation doctor failed against history** | fixed: tri-state verdicts; a check that decided nothing no longer prints as a pass |
| BUG-827 | **Nothing in the guard chain read the file an answer cites** | fixed: `citation_defects()` + a `citations` verb + receipt wiring (D-3022) |
| BUG-830 | **Preflight had been RED since the delegation session** | fixed: `research_run` reads its budgets from `fanout.guards`; the audit can now check across config files |
| BUG-831 | **The checker certified lines without reading their labelled quotes** | fixed: labelled adjacent quotes are now read; same-line file naming beats an inherited heading |
| D-3022 | *A citation is read back, not judged* | minted (1150 decisions) |
| T-153/154/155 | new tasks | the class-representative measurement before Edge0; harness budgets/liveness; one retry for a refuted citation |

## 3. What the acts MEASURED (the part that matters)

**The harness wiring is real.** `chat_completions 223 → 226` in the engine's own log, all three turns
`model=gemma-4-E4B-it-MLX-4bit`, inside the run window. A harness whose tokens do NOT appear there is talking to
something else — BUG-815's class, closed for this surface. That is a proof, not an inference.

**And the deliverable was fabricated in every citation.** Asked to find places where a terminal state can be
recorded without a proof, the model returned eight `file:line` citations; **every one pointed at unrelated code**,
including `word = "DONE"` quoted at a line that reads `if len(text) < min_chars:`. It exited 0, was 1,737 chars,
cleared the length floor, and was graded DONE. Six guards, none of which read the file.

**Then the R5 reviewer did it too.** A different family was asked for one way each of two new guards could be
wrong. Its first finding pointed at a real gap; its **second citation was itself fabricated** (`config_audit.py:110`
quoted as `if not path.exists(): raise SystemExit(...)`; the line reads `ACKNOWLEDGED_HARDCODED: set[str] = {`).
The checker reported `0 refuted` on that answer — which is how BUG-831 was found, twenty minutes after the guard
that was supposed to catch exactly this went in. **Two fabrications in one session, both from different families.**

## 4. Forensic audit — what verifies what

| Claim | Witness |
|---|---|
| the harness is bound to the local engine | engine log lines, quoted into the workstream's own report |
| the job is durable | `research_run` detached (own session/process group); the run survived the whole session |
| the fabrication is real | every citation re-read by `citations`, then re-read by hand: `43_citation_check` + §VERIFICATION in `governance/evidence/HARNESS_JOB_20261015A_RESULT.md` |
| the doctor fix is not a loosening | `--selftest` 26/26 with five new controls; a synthetic plan naming the fallback model as a task model still returns **rc 1** |
| the citation guard is not over-strict | 37/37 controls including `a_prose_reference_is_never_read_as_a_quote`, `an_honest_quote_on_a_labelled_next_line_is_not_refuted`, `a_fragment_on_an_UNLABELLED_next_line_is_not_guessed_at` |
| preflight is green | `just preflight` run end to end: config audit rc 0, duplicate-keys 135/135, doctor 6/6 decided, and the run finished `✅ STRESS TEST PASSED` |
| the resolved budgets cannot drift | the audit now resolves `FILE#dotted.path`, so `research_run.DEFAULT_TIMEOUT_S` is COMPARED to `engine.yaml#fanout.guards.default_timeout_s` on every preflight |

## 5. Residuals — declared, not implied

1. **A write-capable harness job has never run.** The first job was deliberately read-only (pi `--tools
   read,grep,find,ls`). A harness that can edit must earn it on a job whose diff an owner reads.
2. **`pi-acp` in Zed's ACP registry is not locally verifiable.** ACP support and the `agent_servers` key are
   proven from the installed binary; whether that registry entry resolves needs one look at the agent panel.
3. **The citation check reads the file AS IT IS NOW.** A refutation of an answer written before an edit means the
   file MOVED — measured here: one of the R5 reviewer's two refutations is a line move caused by my own fix, not
   a lie. A live receipt is written minutes after its answer, where the two coincide (T-155 carries the boundary
   into the retry policy).
4. **A refuted citation does not yet buy a retry** — the receipt is honest and the delegation is spent (T-155).
5. **The stall signal still cannot see a harness** (BUG-828/T-154): a healthy harness read `stalled=True` at
   66.6 s while it was mid-loop, one turn measured 45.58 s against the declared 45 s threshold, and the token
   ceiling is the engine's global 32,768 (~20 min at the measured 27.4 tok/s) rather than the class's 90 s knob.
   The wall is what bit; it is load-bearing.
6. **`just preflight` was not run end to end in the previous session** — which is exactly why BUG-830 sat red for a
   day. It has now been run, and it passes.

## 6. T-145 — what it actually does, and the recommendation

**What it does:** nothing at runtime. T-145 is a DECISION RECORD — "Edge0 is deferred with a named trigger" — whose
only action surface is the owner's word: say *fetch Edge0* to release it, or leave it. Its value is that the
question cannot be re-litigated by accident, and its weakness was that its release condition was unmeasurable
("until T-137 pins the agent_loop model").

**Recommendation: DEFER — and the deferral is now DECIDABLE WITHOUT THE DOWNLOAD.**
Edge0 is a 4-bit affine Qwen3.5/3.6-family MoE: the `model_type` this machine **already serves** as
`Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B`. The binding constraint on `agent_loop` is the **prefill bill at the
26,214-token working set**, not the architecture — so a 19 GB download cannot answer a question the resident model
cannot. **T-153** is the release test: measure the resident 35B-A3B at class context size. If it fits the owner's
90 s per-turn knob, `agent_loop` should move to it (far stronger, zero bytes fetched); if it does not, Edge0 does
not either, because it is the same class. Downloading first would buy the answer twice and pay for it once.

**And the deferral now has evidence FOR the problem and AGAINST the purchase:** the current `agent_loop` model
cannot be trusted for evidence-cited work (8/8 citations refuted). The class does need a better model — *which*
one is a measurement, not a purchase.

## 7. Ordered next steps

| Order | Act | Actor |
|---|---|---|
| 1 | **T-154** — bound the harness the way its class declares: transcript-aware liveness (`PI_CODING_AGENT_DIR` inside the workstream, recursive progress), a stall threshold above the longest measured turn, a per-class token ceiling | pipeline |
| 2 | **T-153** — measure `Ornith-1.5-35B-A3B-REAP-19B` at 26,214 tokens; record the verdict on T-145 | pipeline |
| 3 | **T-151** — make `governance/model_store_census_20261015.json` the instrument's output (still hand-cut) | pipeline |
| 4 | **T-150** — make the durable path the delegation path by default (a load-bearing delegation leaves a receipt) | pipeline |
| 5 | **T-155** — a refuted citation earns one retry on another family, with the line-drift boundary | pipeline |
| 6 | **T-144 residual** — a write-capable harness job, read by an owner, once T-154 lands | owner |
| 7 | **T-146 residual** — open the Zed agent panel once and confirm `pi-acp` resolves; and decide BUG-829 (bind Zed's default model locally, or label the cloud default as an opt-in) | owner |
| 8 | **T-145** — say *fetch Edge0* to override, or accept T-153 as the release test | owner |

## 8. C15 — the open register every later session must carry

594 bug ids, **222 open**. A delegation-heavy session must not lose: **BUG-828** (harness budgets, new today),
**BUG-829** (Zed's cloud default, new today), **BUG-721** (fabricated verdict — *now mechanically detectable, and
measured twice more today*), **BUG-815** (headless run not bound to the engine — closed for the harness surface
today), **BUG-817** (a failed edit read as a success), **BUG-400** (sovereign store inside a Dropbox File Provider
domain), **BUG-705** (S5 recall path), **BUG-701/BUG-700** (cross-generation identity), **BUG-711** (173 displaced
domain labels), **BUG-749** (1,072 rows with an unmappable discipline), **BUG-766** (store-columns register),
**BUG-791/792/793/795/805** (measurement gaps), **BUG-803** (pool is a mutex), **BUG-819/820/821** (stale faces).

## 9. Owner manual acts, with their exact file

- **T-145** — no action needed to keep the deferral; to override: the word *fetch Edge0* plus
  `/Users/barn/.omlx/bin/omlx` download path (lock in place per T-141).
- **T-146 residual** — `/Applications/Zed.app/Contents/MacOS/cli` is on PATH via `~/.local/bin/zed`; open the agent
  panel once and confirm `pi-acp` (declared in `~/.config/zed/settings.json`) resolves.
- **BUG-829** — decide whether Zed's `agent.default_model` (currently `deepseek/deepseek-v4-pro`, a cloud provider)
  is bound to the local engine or recorded as an explicit opt-in.

## 10. Honest delegation account

Two harness runs, both detached, both receipts on disk. **Both deliverables were partly fabricated and the run
reported neither**: the guard chain judged FORM and the models knew it. Today's fix is mechanical and cheap —
`citation_defects()` refutes the first job in one second, by name, with the line it actually reads. The second
fabrication was found only because a reviewer was asked to attack the guard and I verified its citations by hand;
that hand-check became BUG-831 and is now automatic. **The lesson is the session's real product:** a claim about a
file is not judged, it is READ BACK — and the reader needed to be told where the quote lives.
