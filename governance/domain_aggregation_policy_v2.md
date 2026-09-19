# Domain-Aggregation Policy v2 — exact vs union, measured (D2633 re-review)

**Date:** 2026-09-16 · **Status:** RULING UPHELD IN SCOPE, NARROWED IN GENERALITY
**Inputs:** `governance/model_eval_checkpoint.jsonl` (suite=voting, 1506 rows, 6 voters x 251 gold rows)
vs `governance/gold_4axis.jsonl` (251 human-adjudicated rows). Analyzer: `temp/_domain_policy.py`.

## 1. D2633 was not open — it was already ruled and executed

`DECISION-LOG.md` D2633 (2026-09-14, user ruling): *overlap -> union, always including DeepSeek; disjoint -> abstain*.
Executed via `scripts/aggregate_domain_votes.py`: 148/216 accepted (42 exact + 106 union) on the P1 set,
and 34/59 on the D2631 queue-59 set (`governance/*_domain_aggregation.json`). `pipeline/axis_authority.py`
admits `p5:reliable-pair-D2631-revote` into `DOM_FILL`. **The policy is live and applied — nothing to re-do.**

But D2633 was justified by *abstain rate* (exact-set unanimity over-abstains: 42/216 = 19.4%), **not by accuracy**.
The 251-row voting benchmark now lets us test accuracy directly against human labels.

## 2. Per-voter domain quality (rows where that voter emitted parseable JSON)

| voter | n | F1 | prec | rec | exact-set | mean |P| | mean |G| |
|---|---|---|---|---|---|---|---|
| **Qwen3.8-27B** | 251 (100%) | **0.693** | 0.768 | 0.652 | 0.291 | 2.08 | 2.54 |
| Ornith-1.5-35B-A3B-REAP-19B | 90 (36%) | 0.680 | 0.721 | 0.676 | 0.222 | 2.23 | 2.39 |
| Ornith-1.5-9B-OptiQ-4bit | 34 (14%) | 0.701 | 0.804 | 0.694 | 0.265 | 2.09 | 2.32 |
| gpt-oss-20b-Q8 | 127 (51%) | 0.515 | 0.478 | 0.647 | 0.087 | 4.09 | 2.43 |
| Qwen3-Coder-30B | 241 (96%) | 0.430 | 0.322 | **0.719** | 0.004 | **6.06** | 2.55 |
| gemma-4-E4B | 251 (100%) | 0.357 | 0.317 | 0.430 | 0.024 | 3.60 | 2.54 |

Two failure modes are visible: **over-labelling** (Qwen3-Coder emits 6.06 domains when humans use 2.55)
and **under-recruitment** (REAP/Ornith-9B only emit on 14-36% of rows — their high F1 is a survival effect).

## 3. Policy comparison — anchor Qwen3.8 vs each partner (rows where BOTH parsed)

| partner | n | anchor F1 | partner F1 | UNION | INTERSECT | anchor exact | union exact | mean |U| |
|---|---|---|---|---|---|---|---|---|
| gemma-4-E4B | 251 | 0.693 | 0.357 | **0.513 (-0.180)** | 0.417 | 0.291 | 0.020 | 4.68 |
| Qwen3-Coder-30B | 241 | 0.691 | 0.430 | **0.474 (-0.217)** | 0.609 | 0.290 | 0.004 | 6.55 |
| gpt-oss-20b | 127 | 0.694 | 0.515 | 0.589 (-0.105) | 0.574 | 0.299 | 0.110 | 4.74 |
| REAP-19B | 90 | 0.714 | 0.680 | 0.729 (**+0.015**) | 0.641 | 0.322 | 0.256 | 2.89 |
| Ornith-9B-4bit | 34 | 0.767 | 0.701 | 0.775 (+0.008) | 0.691 | 0.382 | 0.412 | 2.62 |

All-voter policies (n=251): anchor alone **0.693** | union-of-all-parsers **0.398** | intersection **0.319** |
majority>=50% **0.656** | majority>=2 voters **0.634**.

## 4. Verdict

1. **Union is not a policy; it is a peer-only operator.** It helps only when the partner is a peer
   (REAP: +0.015, mean |P| 2.23 vs anchor 2.08). Against an over-labeller it is catastrophic
   (Qwen3-Coder: -0.217, and union-of-all -0.295). The rule that reproduces the data:
   **union iff mean|P_partner| <= 1.3 x mean|P_anchor| AND per-voter F1 gap <= 0.10. Else take the anchor alone.**
   D2633's pair (DeepSeek-v4-pro + Qwen3.8) is a peer pair -> union was correct *there*. It must not be
   generalised to the local roster.
2. **Exact-set unanimity is dead** — the anchor itself matches the human set exactly only 29.1% of the time,
   so exact-set gating abstains on ~71% of rows that are already serviceable. D2633's abstain-rate argument holds.
3. **Majority voting is rejected for domains too** (0.656 and 0.634 < 0.693 single-best), mirroring the
   discipline finding in `voting_verdict_20260916.md`.
4. **Qwen3.8-27B is the domain decider.** Do not average it with local voters; if a domain must be
   second-sourced, REAP is the only admissible union partner, and only on the rows where it parsed.
5. **Action:** add the |P| guard to `scripts/aggregate_domain_votes.py`, or record it as the precondition for
   any FUTURE aggregation. The 148+34 already-accepted rows came from the peer pair and stay valid.