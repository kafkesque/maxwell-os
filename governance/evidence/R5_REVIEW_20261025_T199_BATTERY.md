# R5 REVIEW — the T-199 loop battery (`scripts/measure_subagent_loop.py`)

**Written** 2026-10-25 by the generator (assistant), AFTER the reviewers returned. It records what each reviewer
said, what was accepted, what was refused, and — because it turned out to matter more — what the instrument's own
first runs found that no reviewer did (R5: generator != verifier).

## The three review runs (each journaled BEFORE the call, D-3036)

| # | reviewer (family) | journal id | wall | what came back |
|---|---|---|---|---|
| 1 | `gemma-4-E4B-it-MLX-4bit` | `DJ-20261025T135556Z-29f8` | 76.7 s | **68 completion tokens**, six answers of "no case found", NO line quoted. |
| 2 | `Qwen3.8-27B-MLX-4bit` | `DJ-20261025T135720Z-fc63` | ~9 min | Q1–Q3 answered with the deciding guards quoted; hit `max_tokens` before Q4–Q6. |
| 3 | `gpt-oss-20b-MXFP4-Q8` | (delta re-review) | 27 s | **empty content**: 897 of 900 completion tokens spent in `reasoning_content`, `finish_reason=length`. |

**Run 1 was REJECTED as a review, and the rejection is the finding.** A 68-token "all clear" over a 466-line
adversarial brief, naming no line, is a stamp — and this OS accepts a finding only after re-measuring it, so a
finding of "nothing" is the one answer that cannot be checked at all. Its transcript is kept
(`temp/r5_review_t199_raw.md`) because it is a measured fact about that model on THAT task: gemma reviewed short
diffs usefully in earlier sessions (0.48 s, T-311) and produced a vacuous pass on a long one. R5 is satisfied by a
reviewer that read the code; it is not satisfied by a reviewer that agreed.

**Run 3 was UNMEASURED, not negative.** `gpt-oss-20b` answered inside `reasoning_content` and returned no
`content` at all. That is a property of the allowance, not of the model — and it is exactly the hole the download
below records in the instrument (finding 5).

## Findings ACCEPTED from run 2 (Qwen3.8 — quoted guards)

1. **No grader can PASS with zero tool calls.** It quoted all four first guards: `if len(counted) <
   derived["named"]:`, `if state["parallel_max"] < 2:`, `if not field_calls:`, `if derived["mode"] not in modes:`.
2. **No expected value is typed.** It quoted all four derivations (`sum(BATTERY_GEOMETRY["manifest"])`,
   `left + right`, `records[str(seed)]`, `len(set(values))`).
3. **All four traps are genuinely two-sided** — the wrong answer is reachable: `report.txt` publishes the stale
   total, `mode 'count'` returns the row count, the decoy tool takes `id`, and a serialised pair passes the
   answer while failing the format.

## Findings ACCEPTED from the generator's own audit and from the instrument's OWN runs

4. **A tool ATTEMPT was counted as a measurement.** `grade_distractor` counted calls, so three `count_lines`
   calls on wrong paths (three error payloads) plus a guessed total could PASS. FIX: the driver records a tool in
   `state["ok"]` only when the payload does not start with `error:`, and the grader counts successes. Control
   added (`three count_lines ATTEMPTS that all returned an error payload must FAIL`).
5. **A reasoning model's spent allowance was read as "never called a tool".** MEASURED via run 3: 897/900 tokens
   of reasoning, empty content. FIX: a declared `BATTERY_MAX_TOKENS` (1024) for the battery only, plus an
   `UNMEASURED` verdict when the allowance is consumed and `finish_reason=length` — an instrument that blames the
   model for its own allowance is the BUG-375 shape one layer in. FIX DIRECTION (not applied, owner act): the
   allowance belongs in a ratified knob, as `per_turn_budget_s` does.
6. **A reply with no `choices` would raise instead of being graded.** FIX: the driver reads `choices` defensively
   and reports `engine returned no choice`.
7. **The `argname` fixture carried a SECOND axis and failed everyone.** MEASURED on the battery's first run: with
   record keys shaped `r-<n>` and a prompt that names no format, all eight models answered `unknown record id 4`.
   A trap that fails every model measures nothing — the fix removes the second axis (the key IS the line count)
   rather than spelling the format out. This is the finding a review could not produce: it took running the
   fixture against a real roster to see that the failure had no variance.
8. **`carries()` rejected a sentence-final number.** MEASURED by a real answer: Qwen3-Coder replied "The total
   number of lines in both files is 14." and the guard `(?![\d.])` refused the full stop, grading a CORRECT answer
   as a formatting failure. FIX: the guard now refuses a following digit and a following DECIMAL point only
   (`(?!\d)(?!\.\d)`), with controls for `14.`, `9.0` and `19`.
9. **An ENGINE refusal was graded as a model failure.** An `HTTP 500` on one fixture would have read as "Qwen3-Coder
   failed the enum trap". FIX: transport/engine errors are `UNMEASURED` with the error quoted; only a transport
   TIMEOUT (the instrument's own 180 s bound) stays a FAIL.

## Findings REFUSED

None. No reviewer finding was rejected on re-measurement; run 1 produced no finding to reject.

## What this review actually establishes

The two-sidedness of the instrument is now carried by **39 known-answer controls** (`--selftest`, no model is
called) rather than by a reviewer's reading; the reviewers established that the graders cannot be passed by a
fabricated answer, and the instrument's own runs established four defects that reading could not — one of which
(finding 8) had already produced a FALSE NEGATIVE on a real model before it was fixed.
