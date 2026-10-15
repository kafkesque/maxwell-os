# DURABLE PARALLEL RESEARCH - why the last batch stuck, and the infrastructure that ends it
Measured 2026-10-15. Every number below was observed in this session; nothing is estimated.

## 1. WHAT ACTUALLY WENT WRONG (four causes, all structural)
| # | cause | evidence |
|---|---|---|
| 1 | A goose subagent is a CHILD of the session: a new user message cancels every in-flight child | 6 of 7 delegated runs were cancelled mid-flight; the message was "was cancelled before it finished and will not run again" |
| 2 | Only 3 of 4 reports survived, and the 4th survived as CHAT TEXT | temp/research_engine_20261015.md, research_intake_20261015.md, research_methodology_20261015.md exist on disk; the model-research run hit "max turns reached" and its answer lived only in the transcript, so the compaction took it |
| 3 | A finished deliverable was still WAITED ON | one report's sections were complete while its process kept running: there was no way to say "this is over" |
| 4 | Open-ended web research was delegated to a browsing agent | each fetch is slow, the turn budget is finite, and the answer needed 4 deterministic curl calls, not judgement |

## 2. THE FIX (pipeline/research_run.py - infrastructure, not a rule)
A workstream is a command that runs DETACHED (`start_new_session=True`) in its own run directory,
writes an append-only report, and declares its own end with a `TERMINAL:` line. The runner polls
state, not process liveness, and returns the moment the marker appears.

    python3 pipeline/research_run.py new     --run ID --brief-text "..."
    python3 pipeline/research_run.py start   --run ID --ws NAME --cmd-file CMD.sh --timeout 900
    python3 pipeline/research_run.py collect --run ID --timeout 400      # returns on the marker
    python3 pipeline/research_run.py status  [--run ID]

* DETACHED: nothing the harness does can cancel a workstream. A compaction cannot either.
* EARLY RETURN: measured - a workstream that declared DONE at t=0.2s in a 25s process made
  `collect` return in ~2s, while the process stayed alive (selftest control
  `collect_returns_on_the_TERMINAL_marker_not_on_process_exit`).
* FAIL-CLOSED STATE: a process that dies without a marker is FAILED, not DONE; exceeding the
  declared budget is TIMEOUT and the group is signalled (SIGTERM, then SIGKILL).
* ws: a workstream is handed `$WS_REPORT`, `$WS_DIR`, `$RUN_DIR` so it never guesses a path.

## 3. THE RUN THAT PROVED IT (run `verify_20261015`, 6 workstreams, one collect)
| workstream | state | wall clock | what it produced |
|---|---|---|---|
| w1c_models | DONE | 6.1s | the engine-verified loadability table (8 candidates) |
| w2b_census | DONE | 2.1s | "has this model already been measured?" - all 8 candidates: NO |
| w3_harness | DONE | 20.2s | the 9 integrations, what is installed, what has a headless mode |
| w4b_adopt | DONE | ~60s | MiniCPM5-2B-MLX fetched, discovered by the engine, loaded, measured, unloaded |
| w1_models / w1b_models | FAILED | <5s | the failures that FOUND the two probe defects (silent fetch, oracle path) |
The three first attempts failed fast and loudly, which is the point: a wrong instrument reports
its own wrongness instead of publishing eight "EMPTY_REPO" verdicts.

## 4. THE DEFECTS ITS OWN SELFTEST CAUGHT (filed as BUG-811)
`python3 pipeline/research_run.py --selftest` -> **11/11**. Reaching that took five real fixes:
1. a ZOMBIE answers `kill(pid, 0)`: a dead detached child read as alive forever, so no workstream
   was ever noticed to be over;
2. the state was INFERRED from the string "DONE" instead of read from the marker word, so a
   TIMEOUT was recorded as FAILED;
3. a stale report made every control lie (a previous run's marker was read as this run's end);
4. a workstream's relative path wrote into the repository root (the report path is now injected);
5. the runner's own "no engine constant" control contained the literals it forbade.

## 5. RULES THAT COME WITH IT
* A RESEARCH DELEGATE'S FIRST ACT is to create its report file and append. Its chat answer is <=15
  lines naming the file. The load-bearing numbers are re-measured by the parent (BUG-809).
* IMPLEMENTATION IS NEVER SEQUENCED BEHIND A DELEGATE. A delegate may inform a decision; it may
  not gate one.
* A workstream that CANNOT decide must say so: the probe returns FETCH_FAILED (fatal) rather than
  converting an unreadable hub into a model verdict.
* Parallelism comes from partitioning WORKSTREAMS, never from running many harnesses at one
  engine: the model pool is the serial resource (8 served, 46.88 GB resident, 55 GB ceiling).

## 6. HONEST LIMITS
This makes a finished workstream stop being waited on, and a cancelled one lose nothing. It does
NOT make a slow workstream fast: a 40-minute download is still 40 minutes - it just stops being
40 minutes of a session's attention.
