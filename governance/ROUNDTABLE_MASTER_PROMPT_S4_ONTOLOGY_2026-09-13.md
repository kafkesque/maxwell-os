# Master Roundtable Evaluation Prompt — S4 Ontology End-State
## Verified-Core Fragmentation + Encoder-Classifier Proposition

**Authority:** D2613–D2617 | **Cross-examination:** ChatGPT + Claude (independent suggestions, then cross-examination)
**Audience:** S-tier senior RAG / knowledge engineers
**Date:** 2026-09-13

---

## §0. WHY THIS ROUNDTABLE EXISTS (the clusterfuck, stated plainly)

Maxwell OS v3.0 has a 4-axis ontology per stored Foundation Block (FB):

- **content_type** — 7-way (principle, process_template, process_instance, tool_instruction, growth_edge, noise_drop, quarantine)
- **depth** — 4-way (universal, cross-domain, domain, specialized; N/A for non-principle)
- **domain** — 43-way
- **discipline** — 61-way

The classification stage (S4) is supposed to label these. After 4 days of decisions (D2613–D2617), the honest state is a **fragmented clusterfuck**:

### §0.1 — No single authority has ever verified all 4 axes

| Tier | Definition | Count (of 1,027 golden) |
|---|---|---|
| content_type + depth verified | joint-vote / human / 298-human | **702** (561 principle + 141 non-principle) |
| all 4 non-silver | + discipline/domain non-gpt-oss | **153** (111 + 42) |
| all 4 human-verified | disc/dom from `p5:human*` | **21** |
| all 4 DeepSeek+Qwen verified | — | **0** |

**DeepSeek + Qwen3.8 have only ever voted content_type + depth** (the checkpoint `votes` dict contains literally `{content_type, depth}`). Discipline/domain labels are 93.3% gpt-oss silver (818/1027) + 209 non-silver (p5: claude 106 / Qwen3.8 69 / human combos). **"4-axis DeepSeek-approved" is unclaimable today.**

### §0.2 — The same concept ("needs review") lives in 4 non-reconciled places

| Artifact | Count | Notes |
|---|---|---|
| DB `needs_human_review` flag | 589 rows | stale |
| joint-vote checkpoint `needs_review` | 2,762 rows | the honest abstains |
| `s4_review_queue.jsonl` + `s4_active_learning_sample.jsonl` | 2,431 + 298 = 2,729 | D2615 stratification |
| `golden_synced_4axis.jsonl` + `verified_core.jsonl` | 1,027 + 443 | the "golden" layer |

### §0.3 — A concrete data bug (verified 2026-09-13)

Of 2,996 `principle/QUARANTINE/needs_review=0` rows, only a minority actually need review:

| subgroup | count | truth |
|---|---|---|
| pair **agreed** + depth confidence **high** | **1,750** | clean — should be **PASS**, wrongly dumped to QUARANTINE |
| pair **abstained content_type** | 860 | genuine review |
| pair **abstained depth** | 386 | genuine review |

The 1,246 genuine abstains are already covered by the review queue (0 fell through) — the "2,996 backlog" is mostly a flag-sync bug (1,750 clean rows mislabeled QUARANTINE).

### §0.4 — Root causes

1. **Decided → applied lag** (the auditors already flagged this in D2616): decisions made, then applied late, each time via a *new* artifact instead of reconciling the old one.
2. **Axis-split verification**: content_type reviewed by humans, depth by the pair, discipline/domain by gpt-oss — so no single row was ever verified end-to-end by one authority.
3. **7 disconnected sources of truth** (§0.2) with no reconciliation pass.

---

## §1. CURRENT S4 ARCHITECTURE (verified from code)

| S4 task | Model | Type |
|---|---|---|
| Merge clusters → FB | Qwen3-Coder-30B (generator) | generative |
| CRIBS enrichment (application, failure_mode, elaboration, keywords, jargon) | gpt-oss-20b (VERIFY_MODEL) | **generative** |
| Classification (discipline, domains, depth, is_specialized) | gpt-oss-20b (same merged call, D2224) | classification |
| Depth (FrugalGPT cascade) | gemma-4-E4B (flag OFF, default gpt-oss) | classification |
| Student pre-classifier | ModernBERT (flag OFF, D2607) | classification |

Relevant config: `config/pipeline_config.yaml` (`models.classifier`, `stage4.*`, `classifier_training.*`), `pipeline/pipeline_paths.py` (`VERIFY_MODEL`, `S4_DEPTH_MODEL`, `S4_STUDENT_PRECLASSIFIER_*`).

---

## §2. MY PROPOSITION (to be cross-examined)

**Split S4 into two planes by task type, and retire gpt-oss in two separate, independently-gated steps:**

### Plane A — Classification (encoder, not generative)
- **content_type** → **deterministic** at S2 (D2587 rules), S4 trusts, missing → quarantine (already applied D2616).
- **depth + discipline + domain** → **fine-tuned ModernBERT-base (139M)**, hierarchical: coarse 10-way gate + fine 61-way + 43-way domain, **+ SetFit** for rare leaves, **+ conformal/selective abstention** (never raw softmax).
- Extended S5 DeBERTa does **classification-entailment** ("does this FB entail `{discipline}`?") as an independent correctness check.

### Plane B — CRIBS enrichment (generative, not encoder)
- CRIBS (application/failure_mode/elaboration/keywords/jargon) stays generative. **Open question: migrate to local Qwen3-Coder-30B vs keep gpt-oss for CRIBS only.** This is the gap my encoder plan does NOT answer.

### Label source (weak supervision, seeded by a spotless golden)
- **LFs** = cleanlab (error-detection on silver) + reliable-pair vote (**on disagreement only, not full-corpus**) + NLI. **Calibrated on the verified core.**
- **Active-learning loop**: spotless golden → train classifier → auto-resolve the easy abstains → human-review only the residual → add rulings back to golden → retrain.

### The spotless golden (the prerequisite, currently missing)
Requirements: (1) **one authority per row across all 4 axes**, (2) **stratified** (all 7 ct × 4 depth × 43 domain × 61 discipline), (3) disc/dom must be non-gpt-oss (pair-vote or human), (4) **frozen + R14-stamped + demote everything else to silver pool**.

### Immediate deterministic fixes (0 LLM)
1. Re-PASS the 1,750 clean rows wrongly quarantined.
2. Collapse the 4-way review accounting into one source of truth.
3. Run DeepSeek+Qwen3.8 domain/discipline vote on the 443-core (the only axis never voted).

---

## §3. QUESTIONS FOR EACH EVALUATOR

**Q1 — Is this the best available, viable, feasible, most reliable, most future-proof, and most accurate solution?** If not, what single change moves it closest to that?

**Q2 — Does this guarantee the closest-to-100% ontological accuracy on all 4 axes (content_type, depth, domain, discipline)?** Be explicit: no system guarantees 100%; what is the honest ceiling, and where does accuracy *necessarily* fall to a fail-closed-to-quarantine + human-review floor instead of a classifier?

**Q3 — Who does CRIBS in the encoder world?** An encoder cannot generate `application`/`failure_mode`/`elaboration`. Is "CRIBS stays generative" correct? Should CRIBS move to local Qwen3-Coder-30B (same family as the generator — R5 concern?) or stay gpt-oss? Is CRIBS even necessary, or is it scope-creep that should be dropped/deferred?

**Q4 — Examine the dependencies.** Trace the decision chain (D2610–D2617), the scripts (`build_verified_core.py`, `apply_phase1_finalize.py`, `apply_phase0_relabels.py`, `train_hierarchical_classifier.py`, `build_active_learning_sample.py`), the configs (`pipeline_config.yaml`, `decisions.yaml`, `s4_active_learning.yaml`), and the checkpoints (`joint_vote_production_checkpoint.jsonl`, `verified_core.jsonl`). Find contradictions, dead paths, and where the "single source of truth" is violated.

**Q5 — Independent suggestion.** Each of you gives ONE independent end-state suggestion for S4 (different from mine where justified), then cross-examines my §2 proposition against yours, specifically on: (a) the encoder-vs-generative split, (b) the weak-supervision seeding, (c) the spotless-golden requirements, (d) the CRIBS gap.

**Deliverable:** a unified, drift-proof, senior-RAG-engineer-level ultimate solution, with the 4-axis guarantee honestly bounded (what is guaranteed vs what fails-closed vs what needs a live human queue).

---

## §4. FILES TO EXAMINE (read-only)

- `config/pipeline_config.yaml`, `config/decisions.yaml`, `config/content_types.yaml`, `config/s4_active_learning.yaml`
- `pipeline/stage4_merge.py`, `pipeline/stage4_merged_call.py`, `pipeline/pipeline_paths.py`, `pipeline/schemas.py`, `pipeline/stage6_commit.py`
- `scripts/build_verified_core.py`, `scripts/apply_phase1_finalize.py`, `scripts/apply_phase0_relabels.py`, `scripts/train_hierarchical_classifier.py`, `scripts/build_active_learning_sample.py`, `scripts/vote_flagged_core.py`
- `governance/joint_vote_production_checkpoint.jsonl`, `governance/verified_core.jsonl`, `governance/golden_synced_4axis.jsonl`, `governance/phase0_adjudication_ledger.jsonl`, `governance/s4_review_queue.jsonl`, `governance/s4_active_learning_sample.jsonl`
- `governance/ROUNDTABLE_ADJUDICATION_S2S4S5_FORENSIC_2026-09-13.md` (the prior adjudication), `DECISION-LOG.md`, `governance/buglog.md`

---

## §5. DEPENDENCIES (trace map — what depends on what)

### Decision → config → script → artifact chain

| Decision | Config | Script | Artifact / effect |
|---|---|---|---|
| D2610 (reliable-pair label policy) | — | `scripts/build_joint_vote_set.py` | `governance/joint_vote_production_checkpoint.jsonl` (7,991 votes: `{content_type, depth}` only) |
| D2613 (freeze verified core) | — | `scripts/build_verified_core.py` | `governance/verified_core.jsonl` (443 rows) |
| D2615 (active-learning stratification) | `config/s4_active_learning.yaml` | `scripts/build_active_learning_sample.py` | `s4_active_learning_sample.jsonl` (298) + `s4_review_queue.jsonl` (2,431) |
| D2616 Phase 0 (stop bleeding) | `config/pipeline_config.yaml` (`commit_non_fb_types`, `stage4.*`) | `scripts/apply_phase0_relabels.py` | `maxwell.db` — 1,365 non-principle demoted → QUARANTINE |
| D2616 Phase 1 (finalize) | — | `scripts/apply_phase1_finalize.py` | `maxwell.db` — 88 state changes (149-core) |
| D2617 (freeze) | `config/decisions.yaml` | `scripts/build_verified_core.py` | `verified_core.jsonl` + `verified_core_manifest.json` |
| D2571/D2609 (hierarchical classifier) | `config/pipeline_config.yaml` (`classifier_training.*`, `stage4.student_preclassifier_*`) | `scripts/train_hierarchical_classifier.py` | checkpoint `classifier_modernbert_p5final` (ModernBERT coarse 10 + fine 61 + domain 43) |
| D2607 (student pre-classifier) | `stage4.student_preclassifier_enabled=false` | `pipeline/stage4_merge.py` | hybrid ModernBERT + gpt-oss fallback (OFF) |

### Runtime model dependencies (all local, $0)

| Role | Model | Where |
|---|---|---|
| S2/S4 merge (generator) | Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | OMLX |
| S4 CRIBS + classify | gpt-oss-20b-MXFP4-Q8 | OMLX |
| S4 depth (optional) | gemma-4-E4B-it-MLX-4bit | OMLX |
| S4 student (optional) | answerdotai/ModernBERT-base | local checkpoint |
| Embeddings | bge-m3 (512d) | Ollama |
| S5 NLI verify | DeBERTa-v3-large | local |

### Key dependency risks the evaluators should probe

1. **R5 (generator ≠ classifier)** vs my §2 "CRIBS → Qwen3-Coder" suggestion: CRIBS is enrichment, not classification — does R5 even bind it, or would moving CRIBS to the generator's family break the cross-family check?
2. **The student checkpoint points at `classifier_modernbert_p5final`** (config `checkpoint_dir`) while the training default once wrote `classifier_modernbert` — a drift the config already notes. Is the checkpoint/config coupling still fragile?
3. **`verified_core.jsonl` is not yet referenced by any code** — the "sole eval target" is currently a governance file, not wired into `train_*.py`/`student_classifier.py`. Until it is, the silver set remains the *de facto* eval source (the exact drift BUG-241 was meant to kill).
