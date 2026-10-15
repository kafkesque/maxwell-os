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

## 7. THE FAN-OUT EXECUTOR, MEASURED ON ITS FIRST REAL RUN (2026-10-15)
Two independent questions over two files, one fast model (MiniCPM5-2B-MLX), run as detached workstreams:
both reached TERMINAL in **23.9s and 24.0s**, each writing its own answer file, started under the declared cap
(engine.fanout.max_parallel = 3) - the MECHANISM works.

The ANSWERS did not: task 1 found the right function (refresh) and the right expression but was cut off by its
220-token budget, and task 2 claimed that config/engine.yaml contains no fanout.max_parallel - which is FALSE:
a grep finds it in the file the model was handed. A 2B model is a fast READER, not a reliable one, and its
failure is silent unless a second model checks it. That is why:
  * the model is declared PER TASK in the task file (D-3011: a slot names an axis), and
  * the cross-family verify pass is MANDATORY, not optional (R5) - it is what turns a fast wrong answer into a
    caught one (the verdict is in temp/runs/fanout_20261015/99_verify.md).
Filed as BUG-816.
