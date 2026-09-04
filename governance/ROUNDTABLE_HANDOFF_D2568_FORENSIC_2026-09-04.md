# LLM ROUNDTABLE HANDOFF — Forensic Audit: S4 Taxonomy Labelling (post-D2568)

> **Prepared:** 2026-09-04 · **Repo:** `github.com/kafkesque/maxwell-os` · **Branch:** `main`
> **Reference commit:** see `git log -1 --oneline` after the D2568 push (this file is committed at the same HEAD as everything it references).
> **Auditors:** Claude + GPT (independent), as senior RAG engineers. Reconcile afterwards; do **not** let either see the other's answer first (avoids shared-bias collusion — same reason R5 demands generator ≠ verifier).
> **Mode:** READ-ONLY forensic. Do not mutate `knowledge pipeline/maxwell.db`, `config/*.yaml`, or any governance file. Write findings to a new `governance/ROUNDTABLE_FINDINGS_<model>_2026-09-04.md`.

---

## 0. What this is

Maxwell OS is a local-first knowledge pipeline: EPUB/PDF → extract → chunk → cluster → **S4 classify** → verify (NLI) → commit (SQLite). S4 assigns every extracted "fact-block" (FB) two orthogonal labels: a `discipline` (single-valued, e.g. `behavioral economics`) and `domains` (JSON array, e.g. `["design strategy","user experience"]`). Unclassifiable FBs fall into a catch-all `emerging` on either axis.

A sustained multi-week effort (D2516→D2568) has been reducing the `emerging` population and correcting mislabels. **The remaining problem is now a *measurement* and *label-semantics* problem, not a plumbing problem.** This handoff asks you to adjudicate whether the two audit instruments (k-NN neighbour-agreement and DeBERTa NLI entailment) are actually measuring what we think they are — and, if not, what the correct mitigation is.

---

## 1. Verified state snapshot (facts, not claims)

| Fact | Value | Source |
|---|---|---|
| Total FBs | 7,995 | `maxwell.db` (SQLite) |
| `discipline = 'emerging'` | 927 (11.6%) | DB |
| … of which `discipline_raw` empty | 677 | DB |
| … of which `discipline_raw` non-empty (unmapped) | **250** | DB |
| `domains` containing `emerging` | 772 | DB |
| Canonical domains | 43 | `config/taxonomy_v5.yaml` |
| Canonical disciplines | 61 | `config/taxonomy_v5.yaml` |
| Embeddings | bge-m3, 512d Matryoshka (Ollama) | `pipeline/embeddings.py` |
| NLI verifier | `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` (local) | `pipeline/nli_label_audit.py` |
| k-NN audit | k=10, agreement ≤ 0.3 = "low" | `scripts/knn_label_disagreement.py` |

### Audit metrics (post-D2568 re-audit)

| Instrument | Metric | Value | Delta vs pre-D2568 |
|---|---|---|---|
| k-NN | mean neighbour-label agreement | 40.7% | 41.2% → 40.7% (FLAT) |
| k-NN | FBs ≤ 30% agreement | 7,041 (49.1%) | — |
| k-NN | audited pairs | 14,334 | 12,667 → 14,334 |
| T-NLI | contradict-label | 4,640 | 21.5% → 19.9% |
| T-NLI | weak support (entail < 0.1) | 10,071 | — |
| T-NLI | domain mean entail | 0.2646 | 0.248 → 0.265 |
| T-NLI | discipline mean entail | 0.3273 | — |

---

## 2. The four open anomalies (must-answer)

### A. `project management` still shows **94% NLI contradiction** — and the two audits *disagree*

Calibration row (`governance/d2547_calibration.json`):

```
axis=domain, label="project management"
  nli_flagged=590, mean_entail=0.0058, mean_contra=0.4389
  knn_low_agreement=9, mean_agreement=0.178
```

- **k-NN says it's fine** (only 9 low-agreement FBs — neighbours agree with the label).
- **NLI says it's broken** (590 contradiction-flagged, and the *mean entailment over all 626 FBs is 0.58%* — the model essentially **never** entails "This text is about project management").

This is not a threshold artifact. After `cascade_deregister_domains.py` removed `project management` from the 257 k-NN∩NLI-flagged FBs, ~622 FBs still carry it as a domain, and NLI still contradicts 590 of them. **Either the label is a semantically-vacuous catch-all, or the NLI instrument is miscalibrated for this label — or both.** Adjudicate which.

### B. k-NN did not improve (41.2% → 40.7%)

The k-NN audit was *designed* to replace a "centroid-outlier" audit (D2544, Bahri 2020). After mass reclassification, the number of audited pairs grew 12,667 → 14,334 (more FBs gained canonical labels → more pairings), yet mean agreement is flat and slightly down. Hypothesis to test: **k-NN neighbour-label agreement measures topical *neighbourhood coherence*, not label *correctness*.** A cross-disciplinary FB with 3–4 domains will, by construction, share <50% of its k=10 neighbours' labels. If true, k-NN is the wrong instrument for the mislabel problem and its 49% "low-agreement" rate is a *corpus-diversity property*, not a defect to fix.

### C. Near-zero `mean_entail` across **all** top labels (0.003–0.03)

Top-15 by contradiction rate (`config/pipeline_config.yaml` → `taxonomy.semantic_error_rate_max.per_label`):

```
project management 0.9425 · anthropology 0.9358 · theoretical physics 0.9310
operations research 0.9236 · industrial design 0.9023 · media studies 0.9007
packaging 0.9000 · legal & public policy 0.8838 · interdisciplinary studies 0.8800
editorial & advertising 0.8600 · political economy 0.8587 · evolutionary biology 0.8485
digital product 0.8466 · education 0.8446 · behavioral economics 0.8390
```

`mean_entail` for these labels is uniformly **0.003–0.03** — i.e. the NLI model almost never produces entailment > 0.5 for *any* FB carrying these labels. That is a bimodal signal: either (a) these are all systematically mislabelled catch-alls (real), or (b) zero-shot DeBERTa + the template `"This text is about {label}."` is **under-entailing by default** on loose topic-membership predicates (measurement confound). The truncation audit (`governance/measure_deberta_truncation.md`) already rules out 512-token truncation (0.0% exceed). **This is the highest-leverage question in the whole handoff**: is the 94%-contradiction number a *mislabel rate* or an *NLI-calibration rate*? The relative ordering (typography 0.023, visual perception 0.054 at the bottom vs the catch-alls at the top) suggests the signal is *directionally real but absolutely inflated*.

### D. 677 empty-raw vs 250 unmapped-raw emerging

- **677 FBs** have `discipline='emerging'` with an *empty* `discipline_raw` — the extractor genuinely produced no discipline. These are *not* taxonomy gaps; they are single-source / cross-disciplinary FBs where "no single discipline fits" is the honest answer.
- **250 FBs** have `discipline='emerging'` with a *non-empty* `discipline_raw` — these are genuine **taxonomy gaps** (real raw labels with no canonical target). Top recurring: Ecology (5), Musicology (4), History of Technology (3), audio signal processing (3) + 221 long-tail singletons. These are the **D2399 candidates**, currently frozen.

---

## 3. Forensic brief — ten lenses

For each lens, cite file + line and give a verdict: **REAL / CONFOUND / BY-DESIGN / UNKNOWN**. Do not hand-wave.

1. **Gap** — what the two audits *cannot* see. e.g. NLI audits label *consistency* but not label *coverage*: is there a class of FBs that is consistently under-labelled (empty domains) and invisible to both audits?
2. **Conflict** — the k-NN ↔ NLI divergence on `project management` (A). Which instrument is right, and why? Does the divergence itself indicate the two instruments measure orthogonal things?
3. **Blind spot** — `mean_entail ≈ 0` for all top labels (C). Is the hypothesis template (`"This text is about {label}."`) or the premise (definition truncated to 1500 chars) systematically under-informative? Compare against a *definition-bearing* hypothesis (use the canonical label's own definition as the hypothesis text) as a control.
4. **Hidden / silent failure** — grep the new scripts (`scripts/*.py` from this session, list in §7) for `except:` clauses that swallow errors, and for `fetchone()` calls on a connection without `row_factory = sqlite3.Row` (this bit us once — see D2568 note on `cascade_deregister_domains.py`).
5. **Error propagation** — `scripts/populate_semantic_error_thresholds.py` splits a multi-domain label's `nli_flagged` count *evenly* across its constituent domains (`share = flagged / len(parts)`). Is even-splitting a defensible estimator, or does it distort per-label rates for the 772 FBs carrying `emerging` in their domain array?
6. **Contamination** — `resolve_emerging_promotion.py` and `classify_promotion_labels.py` used Qwen3.8-27B proposals with DeepSeek-v4-pro agreement. Were any *rejected* proposals (the 9 DeepSeek disagreements) accidentally applied? Cross-check `config/alias_map.yaml` `Information Systems → information science` / `Health Informatics → information science` against the alias-review record.
7. **Leak / mismatch** — script ↔ config ↔ golden ↔ decision. §4 gives the specific matrix. Verify the 96 `per_label` values match `governance/d2547_calibration.json`; verify `config/decisions.yaml` D2568 description matches `governance/buglog.md` BUG-150 and `agent/session_seed.yaml`.
8. **Logic** — is "remove the catch-all domain from k-NN∩NLI-flagged FBs" (cascade deregistration) the right *operator*? It only touches the *intersection*. The NLI-only flag set is ~10× larger for some labels. Should the trigger be NLI-only, not intersection?
9. **Test results** — `tests/test_decision_summary_sync.py`, `scripts/recompute_decision_summary.py --check`, and `integrity_check.py` are the only sync gates. Are they sufficient, or is the 96-entry `per_label` block (and its YAML round-trip) unguarded?
10. **Decision coherence** — DECISION-LOG lists D2544 as "✅ DONE" inside the "🔴 OPEN / PENDING" section *and* in the RESOLVED list at the bottom (double-listing). Is this a real tiering bug or harmless? Flag every other such inconsistency.

---

## 4. Script ↔ config ↔ golden ↔ decision mismatch matrix

Cross-check these concrete pairings and report drift:

| # | Artefact A | Artefact B | Expected invariant |
|---|---|---|---|
| 1 | `scripts/populate_semantic_error_thresholds.py` | `config/pipeline_config.yaml` → `taxonomy.semantic_error_rate_max.per_label` | 96 entries; values == `nli_flagged/total` from `governance/d2547_calibration.json` |
| 2 | `governance/d2547_calibration.json` (526 rows) | `governance/nli_label_audit.json` (4,640 contradicts) | per-label `nli_flagged` sums ≈ 4,640 |
| 3 | `config/alias_map.yaml` (`domain_aliases` 618 / `discipline_aliases` 357) | `scripts/apply_alias_corrections.py` `_AGREE`/`_DISAGREE` frozensets | 66 applied, 9 rejected, 1 no-op |
| 4 | `config/decisions.yaml` (total 544, D2568) | `DECISION-LOG.md` (544 decisions, D2568 RESOLVED) | `scripts/recompute_decision_summary.py --check` passes |
| 5 | `MASTER-TASK-REGISTER.md` SHOULD #1 (D2547) | `DECISION-LOG.md` D2547 state=PENDING | both agree "per-label populated, consumer pending" |
| 6 | `config/taxonomy_v5.yaml` `meta.catch_all_domain='emerging'` | `scripts/cascade_deregister_domains.py` `_AXIS_PREFIX` | dereg only strips systematic *domain* catch-alls, never disciplines |
| 7 | `pipeline/schemas.py` `_build_synonym_index` | `config/alias_map.yaml` | kind-safety: domain aliases never leak into discipline axis |

---

## 5. Mitigation research brief (peer-reviewed + tools)

Do market research and cite *specific* papers/repos (not generic advice):

1. **Zero-shot NLI label calibration.** Is raw DeBERTa `entail/contradict` a valid label-correctness signal, or do we need **NLI calibration** (temperature/scaling) or a **NLI-based label model** (e.g. `setfit` / `sentence-transformers` zero-shot classification with label definitions) instead of a single `"is about"` hypothesis? Look at: Yin et al. 2019 (MNLI), `MoritzLaurer/DeBERTa` zero-shot classification docs, and `setfit` (Tunstall et al. 2022) for few-shot alternatives.
2. **Catch-all label detection.** Is there a peer-reviewed method for detecting **over-broad / vacuous labels** in a flat taxonomy (vs. the hierarchical LSHTC / Wikipedia-category literature)? Search "label granularity", "label distribution shift", "taxonomy reconciliation".
3. **k-NN label agreement as an audit.** Bahri et al. 2020 (`Data Maps`-adjacent; "estimating example difficulty via neighbor agreement") is the cited basis. Is neighbour-label agreement actually *validated* for this purpose, or is **training-dynamics / prediction-depth / AUM** (Pleiss et al. 2020) the better mislabel detector? What does the **`cleanlab`** family (Confident Learning, Northcutt et al.) prescribe — this is the canonical mislabel-detection toolkit and may be the single most relevant adoption.
4. **Emerging/unmapped-label handling.** For the 250 genuine gaps: is the right move **canonical expansion (D2399)**, **hierarchical fallback**, or **open-set / OOD detection**? Search "open-world classification", "reject option", "out-of-vocabulary taxonomy".
5. **Tooling/repos to evaluate:** `cleanlab`, `setfit`, `sentence-transformers` (zero-shot), `argilla`/`rubrix` (human-in-the-loop relabeling), `spacy` `spancat`/`textcat` for a trained classifier, `prodigy` (annotation), and `datasets`-based labelling workflows. Assess which would slot into an S4 *discriminative classifier* (already floated in D2483) to replace/adjunct the generative LLM classifier.

---

## 6. Hugging Face finetune candidates

1. **Existing finetuned models for taxonomy/label classification:** search HF for models finetuned on (a) zero-shot text classification with label definitions, (b) hierarchical taxonomy classification (e.g. `MoritzLaurer/*` NLI family is the current S4 NLI backbone — are there better-calibrated NLI models for *short definition* entailment?), (c) `setfit`-trained few-shot classifiers.
2. **Candidate base models to finetune on the 7,995-FB labelled corpus** (local-first, MLX-compatible → C1/C3): a small encoder (DeBERTa-v3 / MiniLM / bge-m3) trained as a **discriminative discipline+domain classifier** (multi-label for domains, multi-class for discipline) would be cheaper, faster, and *measurably calibrated* (outputs a real probability) than the current generative LLM + NLI combo. Assess: `microsoft/deberta-v3-base`, `microsoft/deberta-v3-large`, `sentence-transformers/all-MiniLM-L6-v2`, `BAAI/bge-m3` (already the embedding), and `MoritzLaurer/DeBERTa-v3-large-...` as a starting checkpoint. Weigh MLX finetuning support (does `mlx-lm` cover these archs?) vs `transformers` + `peft` (LoRA) on Homebrew Python.
3. **Recommend a concrete candidate + training recipe** (LoRA rank, epochs, class-balanced loss given the long tail, label-smoothing for the 43-domain multi-label head, and a held-out `golden` set as eval) — with a measurable target (e.g. per-label macro-F1 ≥ X on the golden set, replacing the uncalibrated 5% global gate).

---

## 7. The 250 gaps / D2399 — what they are, what to do

- **What they are:** 250 FBs with `discipline='emerging'` and a *non-empty* `discipline_raw` — real raw labels that have no canonical discipline. Top: Ecology (5), Musicology (4), History of Technology (3), audio signal processing (3) + 221 singletons.
- **Why frozen:** `config/taxonomy_v5.yaml` → `taxonomy.d2399_promotions_frozen: true`. This was set after the user **REJECTED** two prior D2399 auto-promotion candidates (D2516/D2517/D2521) as semantically invalid — the auto-promotion mechanism (promote the most-frequent unmapped label, displace the weakest canonical) was found to be **not trustworthy** on this corpus.
- **What to do (instruction):** do **not** bulk-promote. For each recurring label (Ecology, Musicology, History of Technology, audio signal processing), decide *manually*: (a) map to an existing canonical via `config/alias_map.yaml` (e.g. is "audio signal processing" already `signal processing`? is "History of Technology" → `history`/`technology & society`?); (b) promote to a *new* canonical discipline (only if it has ≥5 stable FBs and a clear definition); or (c) leave as `emerging` (honest "no canonical fits"). The 221 singletons stay `emerging`. Re-run `scripts/recompute_decision_summary.py` + recount `taxonomy_counts` after any change.
- **D2399 mechanism fix (separate):** the auto-promotion should require **NLI-calibrated** evidence of a genuine gap (see §5.1) before it is ever un-frozen — it currently promotes on raw frequency alone.

---

## 8. Deliverables per auditor

Write to `governance/ROUNDTABLE_FINDINGS_<claude|gpt>_2026-09-04.md`:

1. Verdict on each of the four anomalies (A–D), each tagged REAL / CONFOUND / BY-DESIGN / UNKNOWN with evidence.
2. The ten-lens findings (one line each, with the most important three expanded).
3. The §4 mismatch matrix, filled in (DRIFT / CLEAN / UNKNOWN per row).
4. Top 5 concrete mitigations, ranked by (impact ÷ effort), each with the specific file/step.
5. HF finetune recommendation (model + recipe + target metric).
6. Anything the two audits are *both* blind to (one paragraph).

Reconcile the two, then a human (the operator) adjudicates any disagreement.

---

## 9. Reference files (all at HEAD of `main`)

**Code (this session):**
- `scripts/cascade_deregister_domains.py`, `scripts/review_aliases.py`, `scripts/apply_alias_corrections.py`, `scripts/resolve_emerging_promotion.py`, `scripts/classify_promotion_labels.py`, `scripts/populate_semantic_error_thresholds.py`, `scripts/knn_label_disagreement.py`, `scripts/build_mislabel_triage.py`, `scripts/measure_deberta_truncation.py`, `pipeline/nli_label_audit.py`, `pipeline/reclassify_merged_axis.py`, `scripts/resolve_emerging_deterministic.py`, `scripts/extend_alias_index.py`.

**Config:** `config/taxonomy_v5.yaml`, `config/alias_map.yaml`, `config/pipeline_config.yaml` (→ `taxonomy.semantic_error_rate_max.per_label`), `config/decisions.yaml`.

**Audit artefacts:** `governance/d2547_calibration.json`, `governance/mislabel_triage.json`/`.md`, `governance/nli_label_audit.json`/`.md`, `governance/knn_label_disagreement.json`, `governance/measure_deberta_truncation.md`, `governance/relabel_plan.json`/`.md`.

**Governance:** `MASTER-TASK-REGISTER.md`, `DECISION-LOG.md`, `governance/buglog.md`, `agent/session_seed.yaml`.
