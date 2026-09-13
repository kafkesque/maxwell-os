# Joint vote — preflight & hardening (2026-09-11, D2612)

**Decision:** go with **B — two-tier hybrid** (generative reliable-pair as labeler of
record; encoder as regenerable serving cache). Before launching the full run, the joint
vote path was audited for mismatch / hidden failure / contamination / cascade, and hardened.

## Audit findings (all confirmed, not hypothetical)

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | **No DeepSeek retry** — `_call_deepseek` had zero backoff; 6/200 pilot rows (3.0%) hit `empty content (truncated reasoning?)`, were checkpointed with an error vote, and the resume path skips done rows → permanent poison (≈240/7,966 extrapolated). | 🔴 critical | ✅ fixed (BUG-240) |
| 2 | **Bare `json.loads`** on DeepSeek content (no fence/repair/truncation handling), unlike the OMLX path which uses `parse_json_robust`. | 🟠 | ✅ fixed |
| 3 | **R14 violation** — checkpoint rows carried no `schema_version`/`gen_model`/`pipeline_commit` (only the summary evidence file did). | 🟠 | ✅ fixed |
| 4 | **Missing `--retry-failures` + `_all_voters_ok`** — the reference `build_depth_vote_set.py` has them; the joint script lost them. | 🟠 | ✅ fixed |
| 5 | **No preflight** — a DeepSeek 402/balance failure or a wedged OMLX would only surface mid-run, poisoning every subsequent row. | 🟠 | ✅ added |
| 6 | **Pilot/production artifact collision** — evidence file overwrote on every run; checkpoint shared. | 🟡 | ✅ fixed (`--checkpoint` + evidence named after checkpoint) |
| 7 | **8 models resident in OMLX** (Phi-4-mini, Qwen3-Coder-30B, gemma-4×2, gpt-oss-20b×2, Qwen3.5-9B, Qwen3.8-27B) = 19.4GB RSS; the vote needs only Qwen3.8-27B. | 🟡 | ⚠️ documented (lazy-load step below) |
| 8 | **No `caffeinate`** on the ~11h run (sleep would stall the batch). | 🟡 | ✅ added |

## Hardening applied (`scripts/build_joint_vote_set.py`)

- `_call_deepseek`: 3-attempt retry with backoff on empty-content / 408/429/5xx / network /
  SSL; final attempt falls back to free-JSON parsed via `parse_json_robust` (handles fences,
  trailing commas, truncation).
- `vote_once`: accepts `prior_votes` (re-vote only errored voters, never re-pay a valid vote).
- `_all_voters_ok` + `--retry-failures`: recover any already-poisoned rows.
- R14 per-row stamps: `schema_version`, `gen_model`, `pipeline_commit`, `created_at`.
- `--preflight`: DeepSeek probe (model + balance + JSON), OMLX cache-gate (D2460), OMLX
  health + live Qwen3.8 stress (`stress_test_omlx`), target-population count.
- `--checkpoint`: separate pilot vs production artifacts; evidence file is named from the
  checkpoint so nothing clobbers.

## Preflight result (live, 2026-09-11)

```
✅ DeepSeek reachable + model 'deepseek-v4-pro' accepted + JSON parse OK
✅ OMLX cache gate: --no-cache verified (D2460)
✅ OMLX stress (Qwen3.8-27B): 50→1.5s / 2K→12.4s / 6K→35.2s — verdict=SLOW (healthy)
✅ target population: 7,966 principle-labelled rows with definition
```

The **SLOW** verdict (35.2s on a 6K prompt) is the BUG-224 memory-pressure signal, not a
failure — consistent with 8 resident models. Unloading the 7 unused models is recommended
before the run (see below).

## Launch (caffeinate + lazy-load + resumable)

```bash
# 1. (optional, recommended) lazy-load: restart OMLX so ONLY Qwen3.8 loads on first call,
#    freeing ~4GB against the 55GB ceiling and lifting the SLOW stress verdict.
# 2. launch detached:
nohup scripts/run_joint_vote.sh > governance/joint_vote_production.log 2>&1 & disown
# 3. resume after any interruption: run the SAME command — idempotent (checkpoint upsert).
```

`scripts/run_joint_vote.sh` wraps `caffeinate -disu` (no sleep) + `--reliable-only`
(advisory Qwen3-Coder skipped → lazy-load) + `--preflight --run` + a dedicated
`governance/joint_vote_production_checkpoint.jsonl`.

## Remaining pre-launch decision (user)

- **Full run scope** = 7,966 principle-labelled rows (the 29 stored-non-principle rows are
  excluded — they are a separate, tiny re-verify). ~11h at 3 workers.
- The 200-row pilot stays a frozen reference (`governance/joint_vote_checkpoint.jsonl`) for
  the A/B depth-degradation check; production uses its own checkpoint.
