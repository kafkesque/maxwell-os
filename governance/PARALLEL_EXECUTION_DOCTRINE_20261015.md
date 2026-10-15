# PARALLEL EXECUTION DOCTRINE (2026-10-15)

> Where parallelism wins, where it is forbidden, and what the resource actually is.
> Sources: D-3005, D-3011, D-3015, BUG-803, BUG-809, BUG-816, BUG-817, BUG-818.
> Every number below was MEASURED on this machine.

## 1. The resource is not the model, it is the POOL

The engine declares `model_count 9 / loaded 3 / final_ceiling 56.6 GB` (measured 2026-10-15 16:1x).
There is ONE resident set. A fan-out of three one-shot calls is safe; a fan-out of nine schedules an
eviction, and an eviction mid-turn is what destroyed an agent-loop budget in BUG-803. So:

| class | who | cap | why |
|---|---|---|---|
| ENGINE_POOL | anything that calls a model | `engine.fanout.max_parallel` = 3 | one resident set; every load changes every other job |
| CPU_IO | grep, census, hashing, file verification | core count | no shared mutable state |
| WRITE | governance/, config/, registers, DECISION-LOG | 1 (serial, land script) | two writers on one register is data loss (BUG-817) |
| DOWNLOAD | HF fetch of one repo | 1 per repo | overlapping attempts leave `.incomplete` fragments no tool can assemble (T-141, measured 4.0 GB of them) |

## 2. Where fan-out is worth it (and what the unit is)

The unit is an ARTEFACT, never a topic: one task, one file it reads, one file it writes, one question,
one variable changed. That is what makes a report survive a cancelled child (BUG-809).

| layer | fan-out verdict | unit | example |
|---|---|---|---|
| L1 pipeline S0-S6 | SUBPROCESS, not LLM | stage/shard | `pipeline/parallel.py`; deterministic, R7 temp 0.0 |
| L2 governance rails | AUDIT ONLY, read-only | register x question | drift sweep: every DECIDED item vs what the code does |
| L3 intake / curator | YES, per SOURCE | one source = one class | the `class` column IS the partition (config/intake_sources.yaml) |
| L4 dev tooling | YES, per FILE/QUESTION | one artefact | audits, lint/type sweeps, "which config declares X", test design |
| L5 human gate | NEVER | - | a machine may not hold the pen that ratifies (D-3011) |
| L6 unattended ops | YES, scheduled | one sweep = one receipt | nightly census, cache A/B, bench matrix |

## 3. Where fan-out is FORBIDDEN

1. **Two writers on one governed home.** Land scripts append; the second writer loses the first.
2. **Multi-turn agentic loops on the coder model.** DELEGATE-002: its decode collapses as context grows.
3. **Verification as a parallel peer.** The verifier runs AFTER the generator, from a different family (R5).
4. **Anything that loads a fourth model while a benchmark runs** (BUG-803).
5. **Two fetches of one repo.** See the `.incomplete` fingerprint.
6. **A question whose premise is absent.** The planner refuses it before a model is called (D-3012): a
   correct NO EVIDENCE must never be mistaken for a model failure (BUG-816).

## 4. Measuring whether a fan-out helped

A fan-out is worth it only if it beats the serial alternative on the SAME instrument:
`wall_clock`, `terminal_count`, `report_bytes`, and `engine_requests_delta`. The 2026-10-15 run:
w1c 6.1s, w2b 2.1s, w3 20.2s, w4b 245s - all terminal, all with a file. In-session sub-agent one-shot:
0.4s. Harness invocation: ~104s (Claude Code) or ~28s (Pi). Those three numbers decide when a harness is
worth a human being present at all.

## 5. What the ambition adds (and what it costs)

Maxwell OS wants an always-on curator, a gated pipeline and a self-auditing governance layer. That is a
JOB QUEUE, not more sub-agents: every job declares its resource class, its artefact, its budget and its
receipt; the scheduler admits a job only if its class has a free permit. The pool is the mutex of record,
and the governed homes stay single-writer for as long as they are registers.


## HARNESS DEPLOYMENT — where a harness beats goose, and where it is a regression (D-3017)

A harness is not a faster goose. Measured per invocation 2026-10-15: goose one-shot **0.4 s**,
`pi` **28.2 s**, `claude` **104.7 s**. That single row decides the whole policy:

| job class (`config/agent_context.yaml#classes`) | harness | why |
|---|---|---|
| `agent_loop` | **pi** (fallback `claude`) | a loop with a human inside it: the only class where a harness's context management and multi-file edits pay for 28 s |
| `agent_probe` | **none** | one question, one answer: `pipeline/oneshot_ask.py` answers in 0.4 s |
| `pipeline_batch` | **none** | unattended; a harness holds no governed pen (D-3016) |

The decision lives in `config/engine.yaml#harnesses.jobs` and is READ
(`python3 pipeline/harness_env.py --job CLASS`), not remembered. `harness: null` is a decision, not an
omission: it says the harness LOSES for that class. A class the file does not know is FATAL, because a
job that cannot decide must say so and stop (D-3015).

Two rules that bind a fan-out to its resource class (D-3015) still hold inside a harness: ONE harness
on the pool at a time, and a harness's output is a PROPOSAL in `temp/`, never a verification (R5, D-3011).
