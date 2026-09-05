# LLM ROUNDTABLE HANDOFF v2 — Post-Adjudication Corrected Reference (D2569)

> **Supersedes:** `governance/ROUNDTABLE_HANDOFF_D2568_FORENSIC_2026-09-04.md` — that document contains 6+ material errors, all corrected below. Treat this file as the single correct reference.
> **Prepared:** 2026-09-05 · **Repo:** `github.com/kafkesque/maxwell-os` · **Branch:** `main`
> **Reference commit:** `7350507` (last pushed). ⚠️ **The D2569 work (14 files) is UNCOMMITTED at the time of writing.** Commit and push before any auditor clones, so they get a stable, corrected revision. Suggested message: `D2569: BUG-215 residual fix + P0 full-population NLI + contradict/weak split + governance sync + corrected handoff`.
> **Purpose:** context continuity for the next operator session / audit round. This is a **corrected + adjudicated state**, not a fresh question set. Read §2 (corrections) and §3 (adjudication) first.

---

## 0. TL;DR — what changed since the D2568 handoff

Three P0 findings resolved, six errors corrected:

1. **"94% contradiction" was a flag-rate, not a true contradiction rate.** The 590 NLI flags on `project management` = 245 contradicts + 345 weak-support. True contradiction = 245/626 = **39.14%** (now `0.3914` in config). P0 #1 split contradict/weak. ✅
2. **Full-population NLI stats.** `nli_label_audit.json` now persists all 23,364 `results` (not only the flagged subsets), so per-label rates are population means, not flag-subset proxies. P0 #2. ✅
3. **BUG-215 residual (66 FBs) fixed.** FBs with `discipline != 'emerging'` + empty `discipline_raw` + stale `taxonomy_match_method='emerging_real'`. Raw recovered from timestamp-sorted backups; 24 alias-verified kept, 42 unverified reverted to `emerging`. `emerging` 927 → 969. ✅

---

## 1. Corrected state snapshot (live-verified 2026-09-05)

| Fact | Value | Notes |
|---|---|---|
| Total FBs | 7,995 | |
| `discipline = 'emerging'` | **969** | 12.1% |
| … of which raw empty/whitespace/NULL | 623 | genuinely no label |
| … of which raw is literal `'[]'` | 54 | **minor hygiene bug** — serialized empty array instead of `''` (see §4) |
| … of which genuine unmapped raw | **292** | 250 original D2399 gaps + 42 recovered BUG-215 |
| Residual non-emerging + empty raw | **0** | BUG-215 fixed |
| Canonical domains / disciplines | 43 / 61 | `config/taxonomy_v5.yaml` |
| `nli_label_audit.json` | summary + results (23,364) + contradicts_label (4,640) + weak_support (10,071) | full population |
| `project management` NLI | nli_total 626, nli_contradict 245, nli_weak 345 → **0.3914** | `config/pipeline_config.yaml` line 569 |
| k-NN audit | k=10, mean agreement 40.7%, low-agreement 7,041 (49.1%) | measures topical coherence, not correctness |

---

## 2. Corrections to the D2568 handoff (mandatory)

| # | D2568 claim | Corrected |
|---|---|---|
| 1 | "94% NLI contradiction" on `project management` | 590 flags = 245 contradicts + 345 weak. True contradiction 41.5% (245/590); as a **population** rate 39.14% (245/626). |
| 2 | "user REJECTED two prior D2399 candidates (D2516/D2517/D2521)" | **History inverted.** D2516 (organizational theory) and D2517 (urban planning) were **APPROVED + applied**. Only D2521's two candidates (organizational change, entrepreneurial management) were **REJECTED** + promotions frozen. |
| 3 | freeze flag in `config/taxonomy_v5.yaml` | It lives in `config/pipeline_config.yaml` → `taxonomy.d2399_promotions_frozen: true` (line 471). |
| 4 | Bahri 2020 "Data Maps"-adjacent | Bahri et al. ICML 2020 is **"Deep k-NN for Noisy Labels"**. "Data Maps" is Swayamdipta et al. EMNLP 2020 (Dataset Cartography) — a *different* paper. |
| 5 | k-NN multi-domain dilution hypothesis (§2.B) | **Refuted.** Single-domain FBs dominate domain low-agreement (58.2%); the single-valued discipline axis has *more* low-agreement (4,796) than the multi-valued domain axis (2,245). |
| 6 | §4 row 2: per-label `nli_flagged` sums ≈ 4,640 | `nli_flagged` was union(contradict+weak) = 4,640 + 10,071 = **14,711**. Correct invariant: `nli_contradict` sums to 4,640; `nli_weak` sums to 10,071. |

---

## 3. Adjudication of the four anomalies (A–D)

### A. `project management` still "94% contradiction" → **CONFOUND + PARTIALLY REAL**
The 94% figure was a flag-rate (contradict ∪ weak). Corrected to 39.14% true contradiction. But 39% is *still* high — either the label is an over-broad catch-all (D2513 demoted `project management` to a **domain**, so it is inherently multi-discipline topical), or the NLI instrument under-entails on broad topic-membership predicates. The resolution is the P1 definition-bearing hypothesis control (§6 task #1). Do **not** conclude "mislabel" until that control runs.

### B. k-NN did not improve (41.2% → 40.7%) → **BY-DESIGN (instrument mismatch)**
k-NN neighbour-label agreement measures **topical neighbourhood coherence**, not label **correctness**. Its 49% "low-agreement" rate is a corpus-diversity property, not a defect to fix. **Decision: retire k-NN as a mislabel detector** and adopt `cleanlab` Confident Learning (Northcutt et al. JAIR 2021) as the third independent instrument.

### C. Near-zero `mean_entail` across all top labels → **CONFOUND (template under-entailment)**
The hypothesis template `"This text is about {label}."` under-entails on loose topic-membership predicates. `config/taxonomy_v5.yaml` has **no `definition` field** for any canonical — the roundtable's "use the canonical's own definition as hypothesis" fix is valid but *un-implementable without an ontology definition layer* (which is P1). The truncation audit already rules out 512-token truncation (0.0% exceed).

### D. 677 empty vs 250 unmapped emerging → **REAL, now superseded by the 969 split**
After BUG-215 fix: 969 emerging = 623 empty + 54 `'[]'` + 292 genuine unmapped. The 292 genuine gaps are the D2399 candidates (frozen). Never bulk-promote.

---

## 4. New finding (this session): `'[]'` literal-array hygiene bug

54 `emerging` FBs store `discipline_raw = '[]'` (a JSON-empty-array string) instead of `''`/NULL. Two consequences:
- Any query that tests `discipline_raw != ''` will **wrongly** count these 54 as "has raw label".
- Correct empty-test is `(discipline_raw IS NULL OR TRIM(discipline_raw) = '' OR discipline_raw = '[]')`.

This is a minor data-normalization bug (not a correctness bug — all 54 are legitimately `emerging`). Log as a hygiene item; fix by normalizing `'[]'` → `''` in a surgical, backed-up patch, or by adding a canonical empty-check helper to `pipeline/schemas.py` so all callers use one predicate.

---

## 5. Valid roundtable claims — incorporated

Adjudicated as **valid** and folded into the plan:

| Source | Valid claim | Status |
|---|---|---|
| Claude | 590 = 245 contradicts + 345 weak; only 41.5% true contradiction | ✅ incorporated (P0 #1) |
| Claude | calibration was flag-rate selection-biased, not full-population | ✅ incorporated (P0 #2) |
| Claude | k-NN multi-domain dilution refuted | ✅ incorporated (retire k-NN) |
| Claude | D2399 history inverted | ✅ corrected (§2 row 2) |
| Claude | Bahri = "Deep k-NN", not "Data Maps" | ✅ corrected (§2 row 4) |
| Claude | MLX has no mature sequence-classification head; use transformers+peft on Homebrew Python | ✅ adopted for classifier plan |
| ChatGPT | positional `_AGREE`/`_DISAGREE` index literals in alias application are a provenance risk | ✅ accepted (provenance gap; add explicit evidence checkpoint) |
| ChatGPT | S5 golden set only 7 examples → statistically underpowered | ✅ accepted (expand to stratified 750–1200) |
| ChatGPT / Claude | no ontology `definition` field → NLI can't use definition-bearing hypothesis | ✅ accepted (P1 task #1) |
| Qwen | verdicts A CONFOUND / B BY-DESIGN / C CONFOUND / D REAL | ✅ consistent with final adjudication |

Adjudicated as **invalid** (rejected):

| Source | Invalid claim | Why rejected |
|---|---|---|
| Qwen | "stage5_verify mirrors the definition fix" | Mischaracterized: stage5 uses evidence → **FB's own definition** as hypothesis, not the canonical label's definition. |
| Qwen | missed the 66-FB BUG-215 residual | It answered on stale snapshot; the residual is real and now fixed. |
| ChatGPT | "677 is stale, don't trust it" | The 677 was live-correct; the *actual* bug was the 66 non-emerging empty-raw FBs. |

---

## 6. Next priority tasks (ordered, strategically consequential first)

1. **Commit + push** the 14 uncommitted files + this handoff → stable auditor reference. *(dependency for everything below — do this now)*
2. **P1 — ontology definition layer.** Add `definition` / `include` / `exclude` / `siblings` to every canonical entry in `config/taxonomy_v5.yaml` (currently absent). Then run the **definition-bearing NLI hypothesis** as a control against the flat `"is about {label}."` template. This is the single highest-leverage step: it resolves anomaly C and is the prerequisite for trusting the per-label thresholds and the D2547 consumer.
3. **Fix C16 silent except** in `scripts/review_aliases.py:101` — `except (json.JSONDecodeError, KeyError, ValueError): continue` swallows errors. Log and re-raise.
4. **Round-trip test** for the 96-entry `per_label` block in `config/pipeline_config.yaml` (mirror `tests/test_decision_summary_sync.py`) — the block is currently unguarded.
5. **Adopt cleanlab Confident Learning** as a third instrument; **retire `scripts/knn_label_disagreement.py`** as a mislabel detector (keep its output for topical-coherence analysis only).
6. **Expand S4 golden set** 7 → stratified 750–1200 (prereq for classifier training).
7. **Train discriminative classifier** `microsoft/deberta-v3-base` + LoRA (rank 16) + 2 heads (softmax-61 discipline, sigmoid-43 domain), class-balanced loss, target macro-F1 ≥ 0.75 on held-out pre-mutation gold; add calibrated reject/abstain so `emerging` = open-world state.
8. **D2399 manual review** of the recurring 292 gaps (Ecology, Musicology, History of Technology, audio signal processing, Applied Mathematics, etc.) — map to existing canonicals via `config/alias_map.yaml` or leave `emerging`; **never bulk-promote**.
9. **D2547 consumer** (cost-weighting model + gate) after the definition-layer control calibrates the per-label rates.

---

## 7. Reference files

**This session:** `scripts/fix_bug215_residual.py` (new), `pipeline/nli_label_audit.py`, `scripts/build_mislabel_triage.py`, `scripts/populate_semantic_error_thresholds.py`.

**Config:** `config/taxonomy_v5.yaml`, `config/pipeline_config.yaml` (→ `taxonomy.semantic_error_rate_max.per_label`, `taxonomy.d2399_promotions_frozen`), `config/decisions.yaml`.

**Artefacts:** `governance/nli_label_audit.json` (now full-population), `governance/d2547_calibration.json`, `governance/mislabel_triage.json`/`.md`, `governance/knn_label_disagreement.json`.

**Governance:** `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `governance/buglog.md`, `agent/session_seed.yaml` (all updated for D2569).

**Roundtable inputs:** `temp/ROUNDTABLE_FINDINGS_claude_2026-09-04.md`, `temp/chatgpt0050.md`, `temp/QWEN0050.md`.
