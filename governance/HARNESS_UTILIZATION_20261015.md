# HARNESSES: what they are for, and which one Maxwell OS should actually run
Measured 2026-10-15 from the live install. This answers the question that was left open: can Codex,
Claude Code, Pi, DeepSeek Harness, OpenClaw/Hermes be used for Maxwell OS work - debugging, coding,
everyday scaffolding and instructions?

## 1. THE STRUCTURAL ANSWER FIRST
They are CLIENTS of one local server, not alternatives to it. The engine is oMLX on 127.0.0.1:11435;
every harness is a driver that speaks to that URL. Measured evidence: the engine ships a wiring
module per tool - `Resources/omlx/integrations/{claude,codex,codex_app,copilot,dsh,hermes,openclaw,opencode,pi}.py` -
and `omlx launch <tool>` runs the tool with that wiring. For `claude` the module sets
`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`,
`ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` and `CLAUDE_CODE_AUTO_COMPACT_WINDOW`.

Consequence (C21/C25): NO HARNESS MAY BE LOAD-BEARING. Any of them can be replaced by another, or
by `curl`, without touching the pipeline.

## 2. WHAT IS INSTALLED, AND WHAT CAN BE DRIVEN UNATTENDED (measured)
| tool | installed | headless evidence | verdict |
|---|---|---|---|
| claude (Claude Code) | yes | `--print` | USABLE for scripted, non-interactive runs |
| pi | yes | `--print`, `--prompt` | USABLE for scripted runs |
| goose (this harness) | yes (1.54.0) | `goose run -t/--recipe` | the automation substrate Maxwell OS already has |
| codex, codex_app, opencode, openclaw, hermes, copilot, dsh | no | - | one `omlx launch <tool>` away; install on demand only (C28) |

## 3. THE RECOMMENDATION, BY JOB
| job | use | model | why |
|---|---|---|---|
| unattended, parallel workstreams | `pipeline/research_run.py` + a script, or `goose run -t` detached | the script's own / gemma-4-E4B for judgement | survives cancellation; the only substrate that does |
| single-shot code generation | curl one-shot, or `goose run -t` one turn | Qwen3-Coder-30B-A3B (ONE shot) | DELEGATE-002: its decode collapses on long agent contexts |
| code review / short agent loop | `goose run -t`, or `omlx launch claude --print` | gemma-4-E4B | the only model this repo measured ROUTABLE for agent_loop (54.7s vs 60s) |
| classification / S4 discipline | pipeline subprocess | gpt-oss-20b-MXFP4-Q8 | D2249 routing rule |
| verifier | pipeline (S5) | DeBERTa-v3-large NLI | R5: generator != verifier |
| human-in-the-loop coding, debugging, scaffolding | an interactive harness: claude, pi (installed), or codex/openclaw/hermes once installed via `omlx launch` | a model the pool can afford | the human supplies the loop; the harness supplies the ergonomics |

## 4. THE CONSTRAINT NOBODY SHOULD SKIP
More harnesses do NOT buy more throughput. The engine pool is the serial resource: 8 models served,
46.88 GB resident against a 55 GB guard, with adaptive eviction that has already evicted a model
mid-request (BUG-803). Running five agent harnesses at once means five agents queueing on the same
pool - and the pool is what is slow, not the number of shells.

Route by job, not by fashion: a long interactive session needs a model whose DECODE holds up over a
long context. Ours says the 30B coder does not (DELEGATE-002) and the 4B does. So an interactive
coding session on this machine is honest work only while the context stays short, or after the model
is pinned and the cache is proven (T-137).

## 5. WHAT WOULD CHANGE THIS
1. A PINNED pool (`is_pinned` exists in the engine: "Never evict if True") so a long session's
   model cannot be evicted mid-turn. The admin page manages pinning; the engine's own status
   endpoint reports the flag per model.
2. The tiered cache proven by an A/B (T-137), so prefill stops being the wall.
3. Only then does the number of harnesses stop mattering to latency.

## 6. MEASURED, NOT ASSUMED: three headless probes (2026-10-15, run as detached workstreams)
| probe | command | result | wall clock | did the traffic land on the LOCAL engine? |
|---|---|---|---|---|
| Claude Code | omlx launch claude --model MiniCPM5-2B-MLX -p  (piped prompt) | PONG, rc=0 | **104.7s** | YES - the engine's chat counter rose 153 -> 154 |
| Pi | omlx launch pi --model MiniCPM5-2B-MLX | rc=0 | **28.2s** | YES - counter rose 153 -> 154 |
| goose (headless) | goose run -t 'Reply with exactly: PONG' | PONG, rc=0 | ~28s | **NO - total_requests stayed at 52** |

### What those three numbers decide
1. **A harness CAN be driven unattended against the local engine, and the engine's own wiring is what
   makes it local.** omlx launch sets ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN and disables the
   non-essential traffic (CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC, the autoupdater, telemetry).
   Probes 1 and 2 prove it on this machine.
2. **The overhead is ~104s for Claude Code and ~28s for Pi, per invocation, before any work happens.**
   For unattended work that is ~250x the cost of a direct one-shot call (pipeline/oneshot_ask.py: 0.4s
   on the same prompt, measured earlier today). A harness is therefore worth its place where a HUMAN is
   watching - interactive editing, exploration, debugging a hypothesis - and is waste where a script can
   ask one question and write one file.
3. **goose run did NOT use the local engine.** This is the T-132 / D-3003 lesson wearing a new coat: a
   provider that is *declared* in ~/.config/goose/config.yaml (maxwell_omlx, model Qwen3-Coder-30B) is
   not *bound* in the process environment, and two other providers are also enabled: true. The run
   answered PONG while the local engine's request counter did not move - it went somewhere else, which
   C1/C3 do not allow. Fixed the same way as the context contract: the provider and the model are BOUND
   by pipeline/harness_env.py, and the model is resolved by POINTER from the single home that owns it,
   so no model name is restated (C12).

## 7. THE FAN-OUT EXECUTOR, MEASURED - AND A CORRECTION (2026-10-15, the same day)
First run: two independent questions over two files, one fast model (MiniCPM5-2B-MLX), detached workstreams.
Both reached TERMINAL in **23.9s and 24.0s**, each writing its own answer file, under the declared cap - the
MECHANISM works.

One answer looked wrong: task 2 reported that config/engine.yaml contains no fanout.max_parallel. **It was
right.** The block had never landed - an edit that answered "No match found" had been read as a success - while
pipeline/subagent_fanout.py, oneshot_ask.py and hf_fetch_model.py all silently fell back to their own hardcoded
defaults (BUG-817). After the block was actually written, the SAME task on the SAME model produced the correct
answer (max_parallel: 3, with the reason quoted) in **8.1s**.

The lesson is the design change: a fan-out verifies ANSWERS; nothing in it verified the PREMISE of a question.
pipeline/subagent_fanout.py now refuses a task whose declared `expect: REGEX` is absent from its own files,
before any model is called - measured working: "premise ok: task fanout_cfg expect='max_parallel' found in
['config/engine.yaml']". And every instrument now FAILS when its config home is missing rather than inventing a
value (C12/C16). Two bugs, one of them a retraction: BUG-816 (retracted) and BUG-817 (the real one).


## 8. THE INTERSECTION, DECIDED (2026-10-16, T-138) — and the one thing goose does NOT have

The owner asked which client is lightest, which is most versatile, which fits everyday scaffolding, and whether
the CHOICE should be left to the decision model at task time. They are answered as readings; the full matrix and
the decision rule now live in `config/harness_policy.yaml#harness_matrix` (one home, C12).

**1. LIGHTEST (client cost, measured 11:50 today).** The three installed clients are ALL small next to the pool:
claude is a 192 MB native binary with no node runtime, pi a 162 MB node package, goose a 267 MB binary whose CLI
process held 712 MB RSS in the same minute its desktop renderer held **4,736 MB**. The number that decides
anything is the last one: a GUI webview is 6.6x its own CLI, so memory/CPU friendliness is an argument for the
HEADLESS form of a client, not for a different client. The pool (8 served, 46.88 GB, 55 GB guard) remains the
only server-side cost, and every client queues on it.

**2. MOST VERSATILE — goose, measured, not asserted.** 27 extensions declared in the live config (MCP:
filesystem, developer, orchestrator, scheduler, skills, analyze, docguard, summon …), recipes + subrecipes, a
delegate/subagent tool, SKILL.md skills, sessions with boot rules, 10 declared providers. No other client on this
machine can be handed a REPOSITORY RECIPE. That is the versatility that matters here, because Maxwell OS's work
is expressed as recipes, rails and registers.

**3. EVERYDAY SCAFFOLDING — goose, in its headless CLI form.** It is the control plane the work already lives in,
it is provider-agnostic, and it is the only installed client whose adoption costs nothing new.

**4. LEAVE THE CHOICE TO THE MODEL AT TASK TIME? NO — and this is the decisive answer.** A harness chosen by an
LLM per task is a non-deterministic dependency nobody can verify, which is exactly what C25/C27/D-3036 forbid. The
correct shape is the one every other route in this repository already uses: a DECLARED table plus a decider that
may only SELECT A ROW. Rows may be added only by the five-step procedure in `agent/adapters/CONTRACT.md`.

**5. IS GOOSE ENOUGH? Almost — and its three gaps are all MEASURED, not felt.**
- **(a) Sovereignty in the everyday path.** `maxwell_omlx` is declared and enabled, but the process that runs the
  harness carries no `GOOSE_PROVIDER` while `active_provider` is `custom_deepseek` — a provider DELEGATE-001
  records as unusable and C1/C3 do not allow as a default. The 2026-10-15 probe measured the consequence: PONG
  came back with the local engine's counter unmoved. **BUG-849 / T-174**, with the remedy already in the repo
  (`pipeline/harness_env.py --exec`).
- **(b) The trace is a discipline, not a mechanism.** Nothing auto-journals a delegated run; **T-171** must fire
  it AT this boundary. This is the ONLY functional gap in goose that another client plausibly closes, and it is
  the entire reason `claude` is SECOND rather than merely optional: a pre-tool hook surface is the candidate
  mechanism — a hypothesis with a red loop owed, not a reading.
- **(c) The GUI costs 4.7 GB.** Not a defect, a decision: use the CLI form for driving, the app for watching.

**What would change this verdict** (each one a reading, none a preference): a verified hook surface in claude that
journals a delegate automatically (then claude becomes the interactive default); the goose provider BOUND in the
app process with the counter moving (then (a) closes); a pinned pool plus a proven tiered cache (T-137), after
which the client's own latency stops being the binding constraint. Until then: **goose headless is the default,
pi is the cheap loop, claude is the second for hook-shaped work, and the other six clients are one command away
and are adopted ONLY against a named job — which is T-138's own gate, now with a measured matrix behind it.**
