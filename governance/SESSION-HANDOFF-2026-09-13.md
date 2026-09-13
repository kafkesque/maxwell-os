# SESSION-HANDOFF-2026-09-13 — Joint Vote Finish, Recovery, Phase-0 Adjudication, S4 Rerun Plan

> **Date:** 2026-09-13 | **Author:** goose | **Supersedes:** SESSION-HANDOFF-2026-09-06.md
> **Primary artifact:** `governance/joint_vote_production_checkpoint.jsonl` (7,966 rows, vote-only, NOT merged to DB)

---

## 0. TL;DR — what this session resolved

1. **Joint vote PRODUCTION run finished + hardened.** 7,966 unique `fb_id`s voted on content_type (7-way) + depth (4-way, principle-only) under D2612 reliable-pair unanimity (DeepSeek-v4-pro + Qwen3.8-27B must agree; else abstain).
2. **Post-run recovery executed (user-approved):** 21 DeepSeek empty-content rows re-voted via `--retry-failures` → **voter_error_rows = 0**; checkpoint compacted **9,555 → 7,966 lines** (one per fb_id, last-wins, atomic tempfile+fsync+os.replace).
3. **bge-m3 deterministic depth tie-breaker REJECTED (D2614)** — calibrated, non-discriminative (see §4).
4. **Phase-0 149-core adjudication workflow built (D2613).**
5. **BUG-242** (audit `*_verdict` self-report defect) logged + deterministically fixed in the form builder.
6. **Governance synced** + MTR SHOULD→DONE cleanup + this handoff.

---

## 1. Current state — the checkpoint (READ THIS FIRST)

`governance/joint_vote_production_checkpoint.jsonl` — **7,966 lines / 7,966 unique fb_ids, 0 parse errors, 0 voter-error rows.**

Distribution (post-recovery, `governance/joint_vote_production_evidence.json`):

| Axis | Values |
|---|---|
| content_type | principle **4,920** · (abstain) **1,681** · noise_drop **1,037** · process_template **177** · process_instance **120** · tool_instruction **15** · growth_edge **16** |
| depth (among 4,920 principle) | domain **3,113** · cross-domain **733** · universal **22** · specialized **4** · (abstain) **1,048** |
| **needs_review** | **2,729 / 7,966 (34.3%)** |
| **voter_error_rows** | **0** |

Cross-model agreement: content_type **78.9%** / depth **78.4%** (DeepSeek-v4-pro vs Qwen3.8-27B). Disagreement is real epistemic uncertainty → abstain, NOT a defect.

**Backups (all verified byte-identical):**
- `governance/backups/joint_vote_checkpoint_FINAL_20260913_100459.jsonl` (pre-recovery, 14.8 MB)
- `governance/backups/joint_vote_checkpoint_PRE_RETRY21_20260913_102512.jsonl` (pre-retry)
- `governance/backups/joint_vote_checkpoint_FINAL_POST_RETRY_20260913_103244.jsonl` + evidence (post-recovery, 12.2 MB, **current**)
- `google/knowledge pipeline/` → actually `knowledge pipeline/maxwell.db.bak_20260913_100459` (DB, 135,495,680 bytes)

**DB state:** UNTOUCHED. The vote is vote-only; nothing was merged into `knowledge pipeline/maxwell.db`.

---

## 2. What was executed (verify, don't trust)

```bash
# DeepSeek balance check: $9.89 (topped up; was $2.51 mid-run)
curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer $KEY"

# Pre-retry backup + verify identical
cp governance/joint_vote_production_checkpoint.jsonl governance/backups/joint_vote_checkpoint_PRE_RETRY21_$(date +%Y%m%d_%H%M%S).jsonl

# Retry 21 DeepSeek error rows (DeepSeek-only; Qwen3.8 valid votes skipped)
python3 scripts/build_joint_vote_set.py --run --retry-failures --reliable-only \
    --limit 7966 --seed 0 --workers 2 \
    --checkpoint governance/joint_vote_production_checkpoint.jsonl

# 1 row (9d5e48de…) still empty after 3 attempts → 1 more targeted retry → resolved
# (content_type=principle, depth-abstain; moved from ct-abstain to ct-principle)

# Compact 9,576 → 7,966 lines (one per fb_id, last-wins, atomic)
python3 scripts/compact_checkpoint_lastwins.py \
    --in governance/joint_vote_production_checkpoint.jsonl \
    --out governance/joint_vote_production_checkpoint.jsonl --key fb_id
```

`scripts/compact_checkpoint_lastwins.py` is a NEW reusable, C6-compliant compactor (tempfile + fsync + os.replace; idempotent; matches `_load_checkpoint()` last-wins exactly).

---

## 3. Answers to the open questions (senior-engineer rulings)

### Q1 — the 2,729 needs_review rows: manual, or better?

**They are NOT errors — they are the honest abstain signal.** Each is a row where DeepSeek-v4-pro and Qwen3.8-27B DISAGREED, so D2610/D2612 correctly abstained rather than coin-flipping. **Do not force a label on them.**

Already tried and MEASURED (all insufficient — no automated resolver exists):
- 3rd-voter tie-break (Qwen3-Coder-30B): matches consensus **44.7%** → coin-flip (BUG-236).
- v3 deterministic depth-derivation: 66% review.
- bge-m3 domain-cosine tie-break: **20% accuracy** (worse than random) (D2614).
- ModernBERT encoder: 27.7% top-1 (data-limited).
- Snorkel/Dawid-Skene: uncalibrated, 48.7% false flag.

**Best available solution = active learning + stratified human sampling (peer-reviewed: Settles "Active Learning"; Geifman & El-Yaniv "SelectiveNet" selective-abstention):**
1. Stratify the 2,729 by content_type × depth-disagreement pair; sample ~200–400 boundary rows (the most information-dense disagreements).
2. Human adjudicates that stratified sample (same form surface as Phase-0).
3. Use the sample to calibrate the abstention threshold and, optionally, fine-tune a better abstention signal.
4. Remainder **stay abstain** and route to a persistent review queue — no label is fabricated.

**Do NOT bulk-manual-review all 2,729** — that is the expensive anti-pattern active learning exists to avoid.

### Q2 — S4 domain/discipline rerun scope, method, timing, CRIBS

**Scope: principles only (4,920), NOT all 7,966.** domain/discipline is a *principle* axis (43 domains / 61 disciplines). noise_drop is dropped; process_template/process_instance/tool_instruction/growth_edge use their own axes, not domain/discipline.

**Method — NOT gpt-oss, NOT the fine-tuned encoder.**
- **gpt-oss-20b is the unverified teacher** whose silver labels we are checking (BUG-241). Re-running it reproduces the same unverified labels — it cannot verify itself.
- **ModernBERT fine-tune is data-limited** (macro-F1 0.20–0.29; 27.7% top-1; 18/61 disciplines <10 ex). Cannot reach quality now.
- **Best available = the same reliable-pair vote that just worked (D2611 "generative LLM as labeler of record"):** DeepSeek-v4-pro + Qwen3.8-27B, cross-family unanimity, abstain on disagreement. This is the proven method, not an assumption.

**Timing (estimate, to be measured not trusted):** the 7,966-row content_type+depth vote took ~35h wall. A domain+discipline vote on the 4,920 principles has a richer prompt (104 labels vs 11) → expect **~15–25h wall** for a combined 2-axis prompt, dominated by serial Qwen3.8 (~7s/FB × 4,920 ≈ 9.5h) with DeepSeek parallelized. **Cost: ~$10–15 DeepSeek** (balance $9.89 — likely needs a small top-up).

**CRIBS: NO rerun now.** CRIBS (application / failure_mode / elaboration / keywords / jargon) is **retrieval enrichment**, not a truth-critical label axis. It is lower priority than domain/discipline correctness. Rerun CRIBS only if the D2293 quality gate (`_validate_cribs_quality`) shows a systematic failure mode.

### Q3 — task sharing (Qwen3-Coder / Qwen3.8 / DeepSeek)

| Model | Provider | Role (D2549/D2496 routing) |
|---|---|---|
| **Qwen3-Coder-30B-A3B** | local OMLX | **Single-shot code generation ONLY** (curl/one-shot). NEVER multi-turn — decode collapses (DELEGATE-002). Advisory voter (recorded, never decides — BUG-236). |
| **Qwen3.8-27B-MLX-4bit** | local OMLX | **Reliable voter #1** + code review. 0 errors across the vote. Serialized by the single OMLX server → keep single-FB calls. |
| **DeepSeek-v4-pro** | cloud (C22 opt-in) | **Reliable voter #2** (frontier reasoning). Parallelizable (network-bound). Costs money. |
| gpt-oss-20b | local OMLX | **NOT a voter** — the teacher whose silver labels the vote verifies. |

**Efficiency split for the S4 rerun:** DeepSeek parallel (workers=3) + Qwen3.8 serial (workers drain into OMLX), Qwen3-Coder one-shot to write the rerun script, gpt-oss excluded from the vote.

---

## 4. D2614 (REJECTED) — why the deterministic tie-breaker is dead

`scripts/calibrate_depth_tiebreak.py` measured the bge-m3 domain-definition cosine signal on the 149-core with golden definitions:
- 43 domain-definition embeddings are ~equidistant from every FB: max cosine **~0.54–0.58**, top1-top2 gap **~0.02** across all 4 depth classes.
- count-above-threshold accuracy **~20%** (worse than 25% random); collapses **145/148** objects → `universal` at every threshold 0.35–0.60.
- top-5 domain recall only **59.7%** vs the Qwen3.8 audit.

**Consequence:** depth abstain is the honest epistemic-uncertainty signal, not a prompt bug. No deterministic hack resolves it; the fix is human adjudication (Phase-0). This ALSO means domain/discipline cannot be a pure deterministic bge-m3-to-taxonomy match — needs LLM re-ranking or human verification.

---

## 5. Files created/modified this session

**New:**
- `scripts/compact_checkpoint_lastwins.py` (reusable C6 compactor)
- `scripts/calibrate_depth_tiebreak.py` (D2614 evidence)
- `scripts/build_phase0_adjudication_form.py`
- `governance/phase0_149core_adjudication_form.md` (100 flagged / 49 clean)
- `governance/phase0_adjudication_ledger.jsonl` (149 rows, R14-stamped)
- `governance/joint_vote_retry21_2026-09-13.log`

**Modified:** `DECISION-LOG.md` (D2614 + header 590), `config/decisions.yaml` (D2614), `governance/buglog.md` (BUG-242 + date), `MASTER-TASK-REGISTER.md` (DONE entries + BUG-168 moved + date).

**Protected, untouched:** `CONSTITUTION.md`, `.env`, `knowledge pipeline/maxwell.db`.

---

## 6. Pending tasks (next session, in priority order)

1. **Adjudicate the Phase-0 149-core** (fill `governance/phase0_adjudication_ledger.jsonl` human verdict fields). This is the D2613 ground-truth core — everything downstream is gated on it.
2. **Apply the filled ledger** → `config/golden/stage4_golden_mined.yaml` + `knowledge pipeline/maxwell.db` (C13 backup + atomic write; DB currently untouched).
3. **Design + run the domain/discipline reliable-pair vote** on the 4,920 confirmed-principle rows (per Q2). Requires a likely small DeepSeek top-up and a new vote-set builder (Qwen3-Coder one-shot).
4. **Active-learning workflow** for the 2,729 needs_review rows (stratified human sample on boundary; remainder stay abstain in review queue).
5. **Compact/backup hygiene** already done this session; nothing pending on the checkpoint itself.

---

## 7. Safety invariants preserved

- Vote is **vote-only** — DB untouched (35+ hours of work intact).
- All writes atomic (tempfile + fsync + os.replace); all backups byte-verified before proceeding.
- No hardcoded values added (paths/thresholds come from CLI args or existing config).
- temp=0.0 preserved on all generation; generator ≠ verifier (DeepSeek votes, Qwen3.8 votes, neither trusts the other's self-report — BUG-242 fixed deterministically).
