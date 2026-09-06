# Session Handoff — 2026-09-06 (data-absent resolved + vote-model verdict + label-model path)

> **Phase:** v3.0 auto-sorter (discipline/domain classifier) + label-quality pipeline
> **Current time:** 2026-09-06 ~11:16 +02:00
> **Supersedes:** SESSION-HANDOFF-2026-09-05.md
> **Decision state:** 561 total / 460 active / 48 resolved (recompute clean)

---

## 0. TL;DR — where we are

The three "next critical steps" from 2026-09-05 were picked up **and then re-scoped by a
roundtable verdict**:

1. **`bug197_kind_swap` — DONE.** 400 FBs (2 discipline + 35 domain recovered). Net emerging 761→759.
2. **3 data-absent disciplines — DONE via D2584.** Not missing content — unresolved domain axes.
   Fixed deterministically (19 aliases + `resolve_data_absent_domains.py`); 61/61 trainable.
3. **3-model vote — RE-SCOPED (D2585).** The roundtable (3 auditors + adjudication + 2nd-round
   peer review) **rejected the full-corpus vote as the ultimate solution** and adopted a
   weak-supervision label model. The vote survives only as a *targeted generative challenger*
   (LF-3) on ~100–200 cleanlab∩T-NLI-flagged FBs.

---

## 1. What was done (this session)

| Item | State | What |
|---|---|---|
| bug197_kind_swap | ✅ APPLIED | 400 FBs (2 discipline + 35 domain recovered). Backup `maxwell.db.bak_20260906_080236`. |
| **D2584** | RESOLVED | Domain-axis re-derivation for data-absent disciplines. 19 aliases + `resolve_data_absent_domains.py`. Golden 1026→1027, 61/61 trainable. |
| **D2585** | ACTIVE | **Label-quality architecture final verdict.** Retire full-corpus vote (D2582→SUPERSEDED); adopt weak-supervision label model + ModernBERT + calibrate + conformal abstention; MANDATORY LF-audit gate before `build_label_model.py`. |
| Roundtable | ✅ COMPLETE | Handoff brief (`436fabc`), 3 auditor findings (Claude/ChatGPT/Qwen) → `governance/ROUNDTABLE_FINDINGS_*`, adjudication → `ROUNDTABLE_ADJUDICATION_*`; 5 handoff factual errors corrected (corrigendum); pushed `ec175d2`/`b6e9030`. 2nd-round peer review (`chatgpt0052`, `QWEN0052`) folded into D2585. |
| Governance | ✅ SYNCED | `decisions.yaml` 560→561 (D2585 + D2582 superseded); DECISION-LOG + MTR + buglog reconciled. |

---

## 2. Current system state (verified ~11:16)

- **DB:** `pipeline/maxwell.db` — 7,995 FBs; discipline=emerging **759**.
- **Golden set:** `config/golden/stage4_golden_mined.yaml` — **1,027** examples, 61/61 trainable (≥5).
- **Decisions:** total **561**, active 460, resolved 48 — `recompute_decision_summary.py --check` exit 0.
- **OMLX:** **DOWN** (port 11435 not listening). Needed for any generative pass.
- **Cleanlab:** 3,424/7,026 flagged (48.7%). **T-NLI:** 4,497/20,929 contradict (21.5%); per-label thresholds live in `taxonomy.semantic_error_rate_max.per_label` (96 entries).

---

## 3. Next critical steps (priority order — see D2585)

- ~~**P0 — train ModernBERT baseline NOW**~~ ✅ **DONE (2026-09-06).** macro-F1 **0.1845** (target 0.75),
  loss 4.71→3.08 over 3 epochs (still decreasing → data-limited, not model-limited). Confusion matrix
  + per-class F1 saved to `knowledge pipeline/classifier_modernbert/` (`confusion_matrix.npy`, `metrics.yaml`).
  **28/61 disciplines have F1>0**; 33 are data-starved (F1=0). Note: macro-F1 DROPPED from D2578's 0.2621
  → 0.1845 because 61/61 are now trainable — the 11 newly-resolved rare classes (5 ex each) drag the macro
  average. The nonzero-class mean is 0.402, confirming the classes WITH data learn. → P4 retrain is the fix path.
- ~~**P1 — LF-audit / dependency analysis**~~ ✅ **DONE (2026-09-06).** `scripts/lf_dependency_audit.py` →
  `governance/lf_dependency_audit.{json,md}`. **T-NLI-contradiction vs cleanlab are near-INDEPENDENT**
  (phi=0.093, kappa=0.062): both-flag=532, cleanlab-only=2,890, NLI-only=342, neither=3,278 (n=7,042).
  cleanlab = broad flagger (48.7%), T-NLI-contra = narrow (12.4%). Intersection = **532 FBs** (the P3
  challenger target, larger than the ~100–200 estimate). **Design implication for P2:** Dawid-Skene's
  independence assumption is NOT grossly violated (phi≪0.5), so either estimator is defensible — but
  cleanlab's 48.7% flag is a high-recall *uncalibrated* signal (weight it, do NOT treat it as a
  mislabel probability). alias-canonicalization remains preprocessing, NOT a voter.
- ~~**P2 — `scripts/build_label_model.py`**~~ ✅ **DONE (2026-09-06).** Regularized Dawid-Skene EM over the 2
  near-independent LFs → `governance/label_model_output.{json,md}` + `temp/golden_labels_probabilistic.jsonl`.
  π=0.785 (P label correct); T-NLI θ=0.057/ψ=0.364 (precision), cleanlab θ=0.410/ψ=0.701 (recall). **135
  high-suspicion golden FBs** (101 both-flag + 34 NLI-only) = the challenger/GOLD-A seed; mean P(mislabel) 0.236.
- ~~**P3 — targeted generative challenger**~~ ✅ **PREP DONE (2026-09-06).** Residency fix (unload non-pinned
  voter after each vote in `label_vote.py` — Claude finding) + `--high-suspicion` filter (135 FBs) + gemma-4-E4B
  re-classification path validated live. **FULL 135-FB run PENDING** (OMLX up; BUG-224-monitored; ~135×3 voters).
- **P4 — retrain ModernBERT on cleaned labels + temperature-scale + conformal/selective abstention.**
- **P5 — freeze GOLD-A/B/CHALLENGE** (300–500 stratified, book/author-disjoint) as the true eval target.
- **P6 — retire `label_vote.py`** to rare spot-checks.

---

## 4. Open items / notes

- **BUG-224** — OMLX wedge-recovery (D2581) still UNVERIFIED under live sustained load; P3 is the test.
- **D2582 TODO(1)** — missing-close-domain flag still "any-absent" (embedding-similarity upgrade open).
- **Latent (2026-09-05 §5)** — kind-swap/demotion clears `discipline_raw` without resetting
  `taxonomy_match_method` → `emerging_unmapped`; low-severity fix + regression check pending.
- **`bug197_kind_swap.py`** — docstring says `--apply` but code applies by default (no flag); fix CLI.
- **Residency gap (Claude finding)** — sequential *calls* ≠ sequential *residency*: `label_vote.py`
  never unloads voter N before N+1 loads. Wire `model_lazyload.py --unload` before any multi-model run.
- **Depth training-set vote (D2577)** — separate, still-relevant use of the vote (81 universal + 713
  cross-domain + controls → depth classifier). The same weak-supervision principle should eventually
  apply, but no T-NLI/cleanlab detector exists for the depth axis yet.

---

## 5. Working tree

Committed at `b6e9030` (roundtable adjudication). This session's governance edits (D2585, D2582
supersession, DECISION-LOG/MTR/handoff sync) are **uncommitted** — push after review.
