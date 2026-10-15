# T-144 - THE FIRST HARNESS JOB, AND WHAT IT MEASURED (2026-10-15)

Brief: `governance/evidence/HARNESS_JOB_20261015A.yaml`. Runs: `temp/runs/harness_20261015a` (the job) and
`temp/runs/harness_20261015b` (an R5 review of the guard the job produced). Kept here because `temp/runs/` is not
tracked: an evidence directory that disappears in a temp sweep is not evidence.

class `agent_loop` -> harness `pi` via `omlx launch pi` -> model `gemma-4-E4B-it-MLX-4bit`
(homes: config/agent_context.yaml#classes, config/engine.yaml#harnesses.jobs,
config/model_assignments.yaml#harness_roles).

| | job A (the review) | job B (the R5 review of the checker) |
|---|---|---|
| wall | 75 s of a declared 300 s | 109.5 s of a declared 300 s |
| engine turns | 3 (prompt 4162 -> 8295 -> 12438, finish_reason=stop) | 6 (chat_completions 226 -> 232) |
| graded | TERMINAL: DONE - rc=0, ok, 1737 chars | TERMINAL: DONE - rc=0, ok, 2130 chars |
| citation check | 8 checked, **13 refuted claims** | 2 checked, **2 refuted claims** |
| verdict | wiring PROVEN, deliverable REFUTED | one finding real, one citation fabricated |

## BINDING WITNESS (the BUG-815 class, closed for this surface)

## job A report, including the engine witness

```
# workstream ws_guard_review (run harness_20261015a) note: T-144 first harness job: pi read-only agent_loop (D-3017)
ENGINE_WITNESS: chat_completions 223 -> 226
2026-10-15 17:46:12,889 - omlx.server - INFO - [-] - Chat completion: model=gemma-4-E4B-it-MLX-4bit, 18 tokens in 18.62s (29.2 tok/s), prompt: 8295, finish_reason=tool_calls, max_tokens=32768, request_max_tokens=None, stream_model_ttft=18.01s, stream_visible_ttft=18.62s
2026-10-15 17:46:58,615 - omlx.server - INFO - [-] - Chat completion: model=gemma-4-E4B-it-MLX-4bit, 521 tokens in 45.58s (27.4 tok/s), prompt: 12438, finish_reason=stop, max_tokens=32768, request_max_tokens=None, stream_model_ttft=26.59s, stream_visible_ttft=26.59s
PI_RC=0
TERMINAL: DONE - rc=0, ok, 1737 chars
```

## job A answer (graded DONE, then refuted)

```
The analysis of `pipeline/subagent_fanout.py` and `pipeline/research_run.py` for unproven assertions regarding `TERMINAL` states or `RECEIPT` counts is as follows:

**pipeline/subagent_fanout.py**
*   Line 111: `word = "DONE"` - Asserts `DONE` based on `rc == 0` and `ok`, but this is the *grader's* conclusion, not a computed fact from the evidence alone.
*   Line 113: `word = "EMPTY"` - Asserts `EMPTY` based on `why` string matching, which is a heuristic interpretation of the answer file's lack of content.
*   Line 115: `word = "FAILED"` - Asserts `FAILED` based on the failure of the answer verification (`ok` is False and not empty/no file).

**pipeline/research_run.py**
*   Line 101: `TERMINAL_WORDS = ("DONE", "FAILED", "TIMEOUT", "STOPPED", "STALLED", "EMPTY")` - This list *defines* the possible states, but the logic that maps a process exit/report to these words is where the assertion happens.
*   Line 149: `word = "DONE"` - Asserts `DONE` if `ok` is true and `rc == 0`, which is a direct mapping of the grader's success criteria.
*   Line 151: `word = "EMPTY"` - Asserts `EMPTY` if the answer verification fails due to lack of content.
*   Line 119: `rec["state"] = "TIMEOUT"` - Asserts `TIMEOUT` if `elapsed_s > timeout_s`, which is a time-based judgment, not a content-derived verdict.
*   Line 124: `rec["state"] = "STALLED"` - Asserts `STALLED` if `idle_s > stall_s` and `kill_on_stall` is true, which is a time-based judgment.

**Summary:** The code bases are heavily reliant on the *grader's* interpretation (`_grade` in `subagent_fanout.py`) or time-based thresholds (`research_run.py`) to assign the final `TERMINAL` word, which constitutes an assertion rather than a purely computed fact from the raw evidence.
```

## job A citation check

```
REFUTED  pipeline/subagent_fanout.py:111 is quoted as `word = "DONE"` but that line reads: if len(text) < min_chars:
  REFUTED  pipeline/subagent_fanout.py:111 is quoted as `rc == 0` but that line reads: if len(text) < min_chars:
  REFUTED  pipeline/subagent_fanout.py:113 is quoted as `word = "EMPTY"` but that line reads: return True, f"ok, {len(text)} chars"
  REFUTED  pipeline/subagent_fanout.py:115 is quoted as `word = "FAILED"` but that line reads: (blank)
  REFUTED  pipeline/research_run.py:101 is quoted as `TERMINAL_WORDS = ("DONE", "FAILED", "TIMEOUT", "STOPPED", "STALLED", "EMPTY")` but that line reads: """Append one line to an append-only report (fsync'd - a report is evidence)."""
  REFUTED  pipeline/research_run.py:149 is quoted as `word = "DONE"` but that line reads: if not pid_alive(pid):
  REFUTED  pipeline/research_run.py:149 is quoted as `rc == 0` but that line reads: if not pid_alive(pid):
  REFUTED  pipeline/research_run.py:151 is quoted as `word = "EMPTY"` but that line reads: time.sleep(0.25)
  REFUTED  pipeline/research_run.py:119 is quoted as `rec["state"] = "TIMEOUT"` but that line reads: os.kill(pid, 0)
  REFUTED  pipeline/research_run.py:119 is quoted as `elapsed_s > timeout_s` but that line reads: os.kill(pid, 0)
  REFUTED  pipeline/research_run.py:124 is quoted as `rec["state"] = "STALLED"` but that line reads: try:
  REFUTED  pipeline/research_run.py:124 is quoted as `idle_s > stall_s` but that line reads: try:
  REFUTED  pipeline/research_run.py:124 is quoted as `kill_on_stall` but that line reads: try:
citations: 8 citation(s) checked, 13 refuted claim(s)
(exit code 1 = refuted. Produced by: python3 pipeline/subagent_fanout.py citations --answer <this answer>)
```

## job B (R5) answer

```
The analysis of the two files is as follows:

### 1. `pipeline/subagent_fanout.py` (`citation_defects`)

**Concrete Way to Produce a WRONG Verdict (False Refutation):**
The function checks if a quoted fragment from the answer matches the actual text on the cited line. If the answer quotes a word that is present on the line but not surrounded by the specific punctuation/contextual markers (`CODEY` regex), it flags a defect.

*   **File:line:** `pipeline/subagent_fanout.py` (line 171)
*   **Exact Code:** `if quote and quote not in actual:`
*   **Scenario:** The answer quotes a word (`quote`) that is present in the line (`actual`), but the quote is not surrounded by the specific punctuation/contextual markers (`CODEY` regex) used to trigger the check, leading the code to believe the quote is missing, thus flagging a defect when the information is present.

### 2. `pipeline/config_audit.py` (`other_home`/`get_config_value`)

**Concrete Way to Produce a WRONG Verdict (False Pass):**
The system allows a registry entry to point to a configuration file (`FILE#dotted.path`) that might not exist or might be loaded incorrectly, yet the audit proceeds as if the value was successfully retrieved from the *other home*.

*   **File:line:** `pipeline/config_audit.py` (line 110)
*   **Exact Code:** `if not path.exists(): raise SystemExit(...)` (This line is *not* the issue, but the subsequent logic relies on the existence check being sufficient.)
*   **Scenario:** If `other_home(name)` is called for a file that does not exist, it raises a `SystemExit`. However, if the audit logic *reaches* the point where it uses the loaded data structure (`_OTHER_HOMES[name]`) without re-validating the file's existence or integrity upon subsequent reads, it might proceed with an empty or partially loaded structure, leading to a "pass" when the referenced file was never truly available or was transiently unavailable during the audit run. (The code snippet provided shows the existence check happens *before* the return, but the risk lies in the *assumption* that the loaded data is the ground truth for the entire audit lifecycle.)
```

## VERIFICATION OF JOB B (done by hand, after the fact)

- `pipeline/subagent_fanout.py:171` = `if quote and quote not in actual:` - **accurate when written**. It is
  reported refuted now only because the BUG-831 fix added lines above it: a MOVE, not a lie.
- `pipeline/config_audit.py:110` = `ACKNOWLEDGED_HARDCODED: set[str] = {` - the reviewer's `**Exact Code:**`
  quote for that line was **FABRICATED**, and the checker missed it until BUG-831 was fixed. Both facts are in
  governance/buglog.md.
