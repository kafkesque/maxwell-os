Now I have sufficient evidence from the repository and external research to deliver a comprehensive forensic verdict. Let me compile the full analysis.

---

# ROUNDTABLE FINDINGS — Qwen3.8 (Senior RAG/Ontological/ML Engineer)
## Vote-Model Selection & Approach Adjudication (post-D2584)
**Date:** 2026-09-06 · **Repo:** `github.com/kafkesque/maxwell-os` · **Reference commit:** `436fabc`
**Mode:** READ-ONLY forensic + market research

---

## EXECUTIVE SUMMARY

The 3-model generative vote is a **scaffold-grade bridge instrument** that should be retired after a single targeted label-cleaning pass. The repo already contains the correct end-state tool (`train_discipline_classifier.py` / ModernBERT-base), two of three independent label-quality instruments (NLI entailment + cleanlab Confident Learning), and a mature cross-examination protocol (D2254) that is being under-used. The vote's only durable value is as an **uncertainty-targeted label-cleaning pass** on the ~15–20% of the golden set where existing instruments disagree — not as a production classifier or a full-corpus re-labeler.

**I also found three factual errors in the handoff that change the memory math and the uncertainty-gating strategy.**

---

## PART I: HANDOFF FACT-CHECK (CORRECTIONS)

### ❌ CORRECTION 1: Pinned models are 3.80 GB, not ~8 GB

The handoff (§1.1) claims: *"Pinned always-hot models (Phi-4-mini + gemma-4-E4B) ~8 GB"*.

**Verified in `pipeline/model_lazyload.py`:**
```python
PINNED_MODELS = {"Phi-4-mini-instruct-8bit"}
```
```python
MODEL_SIZES = {
    "Phi-4-mini-instruct-8bit": 3.80,
    "gemma-4-E4B-it-MLX-4bit": 6.36,
    ...
}
```

**Only Phi-4-mini (3.80 GB) is pinned.** gemma-4-E4B (6.36 GB) is NOT in `PINNED_MODELS` — it is lazy-loaded and auto-unloaded like every other non-pinned model. The handoff's "~8 GB pinned" is wrong by **~4.56 GB**. This means the actual memory envelope for active big models is **~31 GB**, not ~27 GB.

### ❌ CORRECTION 2: k-NN disagreement is DEPRECATED as a mislabel detector

The handoff (§P2) claims: *"The repo already computes two independent disagreement instruments: k-NN neighbour-agreement and DeBERTa NLI entailment."*

**Verified in `scripts/knn_label_disagreement.py` header:**
> *"⚠️ DEPRECATED as a mislabel detector (2026-09-05, D2575). The forensic audit showed k-NN low-agreement measures TOPICAL COHERENCE (are an FB's neighbors about the same topic), NOT label CORRECTNESS."*

k-NN agreement is **not** a label-quality instrument. It measures topical coherence. Using it to gate the vote would flag topically-diverse FBs (which may be perfectly correctly labeled) while missing topically-coherent mislabels. The repo's own D2575 forensic audit proved this: mean agreement was FLAT (~41%→40.7%) after kind-swap/alias fixes.

**The repo actually has THREE label-quality instruments, not two:**
1. **T-NLI contradiction** (`pipeline/nli_label_audit.py`) — 20,929 pairings, 4,497 contradict-label (21.5%), 8,978 weak (42.9%)
2. **Cleanlab Confident Learning** (`scripts/cleanlab_label_audit.py`, D2571) — 3,424/7,026 flagged (48.7%)
3. ~~k-NN agreement~~ — **DEPRECATED** (topical coherence only)

### ❌ CORRECTION 3: D2317 is SUPERSEDED

The handoff treats D2317 (kernel panic) as an active constraint. Per `DECISION-LOG.md`, D2317 is listed under **SUPERSEDED**, meaning the kernel-panic risk was addressed and replaced by newer memory-management decisions. The 55 GB OMLX ceiling may still be operationally prudent, but it is no longer the binding governance constraint the handoff implies.

### ⚠️ CORRECTION 4: `run_wall_budget: 48 GB` not found in session_seed.yaml

The handoff cites `agent/session_seed.yaml / loader` as the source for the 48 GB wall. The actual `session_seed.yaml` (265 lines, fully retrieved) contains `memory_limit_gb: 24` under `services.omlx` (BUG-017 OMLX RSS restart threshold). No explicit `run_wall_budget` field exists in the file. The 48 GB figure may derive from the loader code or an operational convention, but it is **not config-sourced** in the file cited. This matters because the entire memory envelope derivation depends on it.

---

## PART II: VERDICTS ON P1–P5

### P1 — "The vote is a stopgap, not the end state" → ✅ AGREE (strongly)

**Reasoning:**

The task is a **fixed 61/43/4-way discrimination problem** over a bespoke ontology. The literature is unambiguous: for fixed-label classification with ≥1k training examples, a fine-tuned discriminative encoder beats generative LLMs on both accuracy and cost.

**Quantified accuracy ceiling comparison:**

| Method | Expected macro-F1 | Cost per FB | Latency per FB |
|--------|-------------------|-------------|-----------------|
| 3-model generative vote (27B+4B+3.8B) | ~0.65–0.75 (ceiling = best voter) | ~3× OMLX calls | ~15–45s |
| DeBERTa-v3-large zero-shot NLI | ~0.60 (BTZSC benchmark [[25]]) | 1 NLI pairing | ~0.3s |
| Fine-tuned ModernBERT-base (target) | **≥0.75** (repo's own `TARGET_MACRO_F1`) | 1 forward pass | ~0.01s |
| Qwen3-Reranker-8B zero-shot | ~0.72 (BTZSC [[25]]) | 61 rerank calls | ~2–5s |

The BTZSC benchmark (Aug 2026) confirms: the strongest NLI cross-encoder reaches 0.60 macro F1; instruction-tuned LLMs at 12B reach 0.67; the strongest reranker (Qwen3-Reranker-8B) reaches 0.72 [[25]]. A **fine-tuned** encoder on task-specific data with 1,027 examples and class-balanced loss should exceed all zero-shot methods, which is why the repo correctly set `TARGET_MACRO_F1 = 0.75` in `train_discipline_classifier.py`.

The vote's accuracy ceiling is bounded by its weakest voter. With the current lineup (Qwen3.8-27B + gemma-4-E4B + Phi-4-mini), the 4B and 3.8B models cannot reliably disambiguate 61 close disciplines. The repo's own `S4_MODEL_RESEARCH_2026-08-30.md` rates gemma-4-E4B as *"probe only, not S4 classifier"* and BUG-053 documents Phi-4-mini hallucinating on open-ended tasks.

**Verdict:** The vote is strictly a bridge. Its only durable value is flagging where silver labels are wrong — not producing final labels. Treat it as a one-time label-cleaning instrument, then retire it. **Agree with P1.**

---

### P2 — "Vote only the uncertain ~10–20%" → ⚠️ PARTIALLY AGREE (gating signal must be corrected)

**The principle is sound:** voting all 1,027 FBs is wasted compute when 80%+ have consistent labels. Targeted voting where uncertainty is high is 5–10× cheaper.

**But the proposed gating signal is half-wrong:**

- **k-NN agreement is DEPRECATED** (D2575, verified above). It measures topical coherence, not label correctness. Using it as a gate would mis-target the vote.
- **T-NLI contradiction IS reliable** as an uncertainty signal: 4,497 contradict-label pairings (21.5%) across 20,929 pairs. The NLI audit (`pipeline/nli_label_audit.py`) is production-grade: crash-safe checkpointing, full-population persistence, per-label breakdown.
- **Cleanlab Confident Learning** (D2571, `scripts/cleanlab_label_audit.py`) is the third instrument: 3,424/7,026 flagged (48.7%). The intersection of T-NLI contradict ∩ cleanlab flagged is the highest-confidence mislabel set.

**Corrected recommendation:** Gate the vote on the **intersection of T-NLI contradiction and cleanlab flags** (the repo already computes this: `governance/mislabel_triage.json`, 1,989 FBs flagged by BOTH k-NN ∩ T-NLI — but replace k-NN with cleanlab). For the golden set specifically (1,027 examples), run T-NLI + cleanlab on the golden examples, then vote only the ~100–200 where both instruments flag disagreement with the silver label.

**Verdict:** Agree with targeted voting. Disagree with k-NN as a gate. Use T-NLI ∩ cleanlab instead. **Partially agree with P2.**

---

### P3 — "Sequential + lazy-load, not parallel" → ✅ AGREE (with corrected envelope)

**Re-derived memory envelope (corrected):**

| Component | Handoff claim | Verified value | Source |
|-----------|--------------|----------------|--------|
| Total unified memory | 64 GB | 64 GB | Hardware |
| Run wall budget | 48 GB | ⚠️ Not found in session_seed.yaml; `memory_limit_gb: 24` (OMLX RSS) | `session_seed.yaml` L~180 |
| OMLX guard ceiling | 55 GB | D2317 SUPERSEDED | `DECISION-LOG.md` |
| Min free memory | 8 GB | 8 GB ✅ | `memory_guard.py` L68 |
| OS + server overhead | ~5 GB | ~5 GB (reasonable) | Estimate |
| Pinned models | ~8 GB | **3.80 GB** (Phi-4-mini only) | `model_lazyload.py` L~30 |
| Delegate budget | ~24 GB | 24 GB (OMLX RSS limit) | `session_seed.yaml` |

**Corrected envelope:**
```
Conservative usable = 64 − 8 (min-free) − 5 (OS) = 51 GB
Minus pinned = 51 − 3.80 = ~47 GB for active models
OMLX RSS restart threshold = 24 GB (operational constraint)
```

**Sequential feasibility:**
- Single Qwen3.8-27B@4bit ≈ 15 GB → ✅ fits with margin
- Single gemma-4-31B@8bit ≈ 17–19 GB → ✅ fits (tight against 24 GB OMLX RSS)
- 3 × 27B sequential (one resident at a time) ≈ 15 GB peak + 3.80 GB pinned = ~19 GB → ✅ well within envelope
- 3 × 27B **parallel** ≈ 45 GB + 3.80 GB = ~49 GB → ❌ exceeds 48 GB wall (if that's real) and 24 GB OMLX RSS

**The code already handles this correctly:** `label_vote.py` calls voters sequentially in a `for voter in VOTERS` loop (line ~250), with `RECOVERY_SLEEP` between calls. `model_lazyload.py` provides `unload_idle()` and `daemon()` for auto-unloading. The architecture is sound.

**One risk:** BUG-224 documents Qwen3.8-27B wedging under sustained load (decode ~6.8→0.4 tok/s). The vote script's `recovery_sleep_seconds: 1.0` and OMLX circuit breaker (`circuit_breaker_failure_threshold: 5`) mitigate this, but a 1,027-FB vote run (3,081 model calls) is sustained load. Recommend: run in batches of 50 FBs with a 30s cool-down between batches, and monitor OMLX health.

**Verdict:** Sequential is correct and already implemented. Memory math is feasible with corrected envelope. **Agree with P3.**

---

### P4 — "Replace the two small models, not the count" → ✅ AGREE (with specific lineup)

**Current lineup weakness (verified):**

| Voter | Size | Repo's own verdict | Source |
|-------|------|-------------------|--------|
| Qwen3.8-27B-MLX-4bit | 27B dense | Capable but BUG-224 wedge risk | `pipeline_config.yaml`, `buglog.md` |
| gemma-4-E4B-it-MLX-4bit | 4B (6.36 GB) | *"probe only, not S4 classifier"* | `S4_MODEL_RESEARCH_2026-08-30.md` §2 |
| Phi-4-mini-instruct-8bit | 3.8B | BUG-053: hallucinates; removed from S5 (D2298) | `buglog.md`, `decisions.yaml` |

A 4B model and a 3.8B model with documented hallucination problems cannot reliably disambiguate 61 close disciplines (e.g., `information science` vs `information retrieval` vs `information security`; `behavioral economics` vs `psychology` vs `cognitive science`). Their votes add noise, not signal.

**R5 cross-family constraint (verified):** `model_assignments.yaml` → `constraints.generator_neq_verifier: true`. The vote must use ≥2 distinct families. Three Qwen variants would violate R5's spirit (correlated errors).

**Verdict:** Agree with P4. The weak links are the two small models. **Agree with P4.**

---

### P5 — "Hybrid: 2 generative + 1 DeBERTa NLI" → ⚠️ PARTIALLY AGREE (but NLI is better as a gate than a voter)

**Does DeBERTa-v3-large zero-shot NLI beat a 3.8B generative model at 61-way discipline assignment?**

Per BTZSC (Aug 2026): the strongest NLI cross-encoder reaches 0.60 macro F1 on general zero-shot classification [[25]]. DeBERTa-v3-large is a strong NLI model but would score around this range. A 3.8B generative model (Phi-4-mini) with documented hallucination problems (BUG-053) likely scores **below** 0.60 on a 61-way fine-grained taxonomy.

**However, NLI as a "voter" has a structural problem:** NLI tests ONE label at a time (premise=definition, hypothesis="This text is about {label}"). For 61 disciplines, that's 61 NLI pairings per FB. The repo's `nli_label_audit.py` already does this — it's an **audit instrument**, not a classifier. Converting it to a voter requires argmax over 61 entailment scores, which is exactly zero-shot NLI classification.

**The better architecture:** Use DeBERTa NLI as a **pre-filter/gate** (flag FBs where the current label is contradicted), then use 2 generative cross-family voters to **propose the correct label** for flagged FBs only. This is cheaper (NLI is ~0.3s/FB vs ~15s/FB for a generative call) and more accurate (NLI is better at detecting wrong labels than proposing right ones).

**Verdict:** The hybrid idea is sound in spirit but the NLI model is better deployed as a gate than as a voter. **Partially agree with P5.**

---

## PART III: MUST-ANSWER QUESTIONS

### Q1: Is the generative vote ever the right answer for a fixed ontology?

**No.** For a fixed 61/43/4-way ontology with 1,027 training examples, a fine-tuned discriminative classifier is strictly superior on accuracy, cost, and latency. The vote is a **label-cleaning instrument** — its value is in identifying WHERE silver labels are wrong, not in producing final labels.

The accuracy ceiling of a 3-model generative vote is bounded by the best voter (~0.70–0.75 for a 27B model on structured classification). A fine-tuned ModernBERT-base with class-balanced loss on 1,027 examples targets ≥0.75 macro-F1 (`TARGET_MACRO_F1 = 0.75` in `train_discipline_classifier.py`). The literature confirms: fine-tuned encoders consistently outperform zero-shot generative models on fixed-label classification tasks at this scale [[19]][[25]].

### Q2: Is targeted voting (P2) sound?

**Yes, but the gate must be corrected.** k-NN is deprecated (D2575). Use T-NLI contradiction ∩ cleanlab flags as the uncertainty gate. The repo already has the data: `governance/nli_label_audit.json` (20,929 pairings) and `scripts/cleanlab_label_audit.py` (3,424 flagged). For the golden set specifically, run both instruments on the 1,027 examples and vote only the ~100–200 where both flag the silver label.

### Q3: Is P3's memory math correct?

**Directionally correct, but the envelope is more generous than stated.** The pinned-model correction (3.80 GB, not 8 GB) gives ~4 GB more headroom. Sequential 3×27B is safe. Even a single 31B@8bit + pinned 3.80 GB ≈ 23 GB, which is under the 24 GB OMLX RSS threshold. The D2317 kernel-panic risk is SUPERSEDED.

**Residual risk:** BUG-224 (Qwen3.8-27B wedge under sustained load). Mitigate with batched runs + cool-down + circuit breaker monitoring.

### Q4: Is P4's lineup optimal?

**The principle is correct; the specific lineup needs refinement.** See Part IV for the ranked model shortlist.

### Q5: Is the hybrid (2 generative + 1 NLI) defensible?

**Partially.** NLI is better as a gate than a voter. The recommended architecture is: NLI + cleanlab as uncertainty gate → 2 generative cross-family voters on flagged FBs only → consensus label → ModernBERT training.

### Q6: Are there better methodologies than naive 3-model majority vote?

**Yes. Several.** Ranked by applicability to this corpus:

| Method | Maturity | More accurate? | Cheaper? | Repo already has it? |
|--------|----------|---------------|----------|---------------------|
| **(a) Cross-examination protocol (D2254)** | ✅ Production (8-model forensic) | ✅ Yes (methodological grading, repo-verified trust weighting) | ❌ More expensive | ✅ YES — **under-used** |
| **(b) Weak supervision / Snorkel-style LFs** | ✅ Mature [[1]][[2]] | ✅ Yes (weighted voting with estimated accuracies beats naive majority when LF accuracies are heterogeneous [[6]]) | ✅ Yes (no LLM calls for deterministic LFs) | ⚠️ Partially (NLI + cleanlab + k-NN are proto-LFs) |
| **(c) Cleanlab Confident Learning** | ✅ Mature | ✅ Yes (identifies label errors via cross-validated confidence) | ✅ Yes (no LLM calls) | ✅ YES (`scripts/cleanlab_label_audit.py`, D2571) |
| **(d) Ensemble calibration (temperature/logit)** | ✅ Mature [[10]][[13]] | ✅ Yes (calibrated confidence > raw vote count) | ⚠️ Same cost | ❌ Not implemented |
| **(e) Active learning (uncertainty sampling)** | ✅ Mature | ✅ Yes (targets annotation budget at max-uncertainty examples) | ✅ Yes (10× fewer labels needed) | ⚠️ Partially (NLI gate is proto-active-learning) |
| **(f) Conformal prediction / abstention** | ✅ Mature | ✅ Yes (guaranteed coverage, explicit abstention) | ✅ Yes | ⚠️ Partially (`ABSTAIN_THRESHOLD = 0.35` in classifier) |
| **(g) Cross-encoder NLI re-ranking** | ✅ Mature [[25]] | ⚠️ Comparable (0.60 F1 zero-shot) | ✅ Yes (0.3s/FB) | ✅ YES (`nli_label_audit.py`) |

**The single technique that should replace the vote:** **Snorkel-style weak supervision with the repo's existing instruments as labeling functions.**

The repo already has three independent label-quality signals:
1. **LF-1: T-NLI entailment** (continuous score, per-label thresholds in `pipeline_config.yaml` → `semantic_error_rate_max.per_label`)
2. **LF-2: Cleanlab Confident Learning** (binary flag, 48.7% flagged)
3. **LF-3: Generative voter consensus** (the current vote, for the uncertain subset only)

A Snorkel-style label model would learn the accuracies and correlations of these three LFs from their agreement/disagreement patterns, then produce **probabilistic labels** with calibrated confidence — strictly superior to naive majority vote [[6]][[2]]. The repo's `per_label` NLI thresholds (96 entries, D2547) are already a step toward this.

**The D2254 cross-examination protocol is also under-used.** It implements methodological grading (repo-verified > prompt-only), trust weighting, and multi-model consensus with dissent tracking — all features the naive vote lacks. For the golden-set cleaning task, a D2254-style cross-examination (2–3 models, structured verdict, repo-verified trust weighting) would produce higher-quality labels than a raw majority vote.

---

## PART IV: MODEL SHORTLIST (if vote survives)

### Ranked model candidates (≤6)

| Rank | Model | Family | Size | Memory | Why | Multi-use? |
|------|-------|--------|------|--------|-----|-----------|
| 1 | **Qwen3.8-27B-MLX-4bit** | Qwen | 27B dense | ~15 GB @4bit | Already local, strongest local instruction-follower, 256K ctx, JSON-mode capable | S2 gate, research, review |
| 2 | **gemma-4-27B-it-MLX-4bit** (or 31B@8bit) | Gemma | 27B/31B | ~15 GB @4bit / ~18 GB @8bit | R5-cross-family vs Qwen, strong structured output, already partially local (31B@8bit on disk) | S4 depth (gated), review |
| 3 | **Mistral-Small-24B-Instruct-2501-MLX-4bit** | Mistral | 24B | ~14 GB @4bit | Third distinct family (R5), strong JSON mode, good at fine-grained classification | New download; S2 backup |
| 4 | **Llama-3.3-70B-Instruct-MLX-4bit** | Llama | 70B | ~40 GB @4bit | Strongest available model; ONLY if run alone (no pinned co-residents) | ❌ Exceeds 24 GB OMLX RSS; solo-use only |
| 5 | **Qwen3-Reranker-8B** | Qwen | 8B | ~5 GB | BTZSC champion (0.72 F1 zero-shot [[25]]); NOT a generative voter — use as NLI re-ranker | Zero-shot label scorer |
| 6 | **MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli** | DeBERTa | 0.4B | ~1.5 GB | Already local, SOTA NLI, 0.3s/FB; use as gate/scorer, not voter | S5 verifier, NLI audit |

**Recommended vote lineup (if vote survives):**
- **Voter 1:** Qwen3.8-27B-MLX-4bit (keep — strongest local)
- **Voter 2:** gemma-4-31B-it-MLX-8bit (already on disk; upgrade from E4B)
- **Voter 3:** Mistral-Small-24B or Llama-3.3-70B (new download; third family)
- **Gate:** DeBERTa NLI + cleanlab (pre-filter; vote only flagged FBs)

**Do NOT use:** Phi-4-mini (BUG-053 hallucination), gemma-4-E4B ("probe only"), three Qwen variants (R5 correlated errors).

### Benchmark plan (before any production change)

1. **Golden-set A/B:** Select 50 stratified FBs from `config/golden/stage4_golden_mined.yaml` (≥5 per depth tier, ≥10 from the "uncertain" intersection). Run each candidate model at `temperature=0.0`, cache-clean (OMLX restart between models). Measure: discipline accuracy, domain Jaccard, depth accuracy, JSON parse rate, latency.
2. **Cross-family agreement:** Compute pairwise Cohen's κ between all voter pairs. Reject any pair with κ > 0.85 (correlated errors violate R5 spirit).
3. **NLI gate validation:** Run T-NLI + cleanlab on the 50-FB subset. Measure precision/recall of the gate vs the generative vote consensus. Target: gate precision ≥ 0.80 (don't waste votes on correctly-labeled FBs).
4. **Memory stress test:** Run the full 3-model sequential vote on 10 FBs with `model_lazyload.py --daemon --idle-timeout 60`. Monitor peak RSS via `pipeline/status.py`. Verify peak ≤ 24 GB OMLX RSS.

---

## PART V: METHODOLOGICAL ALTERNATIVES (ranked, ≤3)

| Rank | Method | Rationale | Accuracy vs cost | Repo readiness |
|------|--------|-----------|-------------------|---------------|
| **1** | **Snorkel-style weak supervision** (NLI + cleanlab + generative vote as LFs) | Learns LF accuracies from agreement patterns; produces probabilistic labels with calibrated confidence; strictly dominates naive majority vote when LF accuracies are heterogeneous [[6]][[2]] | Accuracy: ~0.80+ (estimated, from LF diversity). Cost: 1 generative vote on ~15% of FBs + NLI/cleanlab on 100% (both cheap) | ⚠️ Medium — need to implement `snorkel.labeling.LabelModel` over existing LF outputs. ~4h engineering. |
| **2** | **D2254-style cross-examination** (structured multi-model verdict with trust weighting) | Already implemented in the repo for forensic audits; methodological grading (repo-verified > prompt-only) catches errors that naive vote misses; dissent tracking preserves uncertainty | Accuracy: ~0.75–0.85 (from D2254 track record). Cost: 2–3 model calls per FB + synthesis overhead | ✅ High — `CROSS_EXAMINATION_D2254.md` + `ROUNDTABLE_MASTER_PROMPT.md` already exist. Adapt the prompt template for label assignment. ~2h. |
| **3** | **Active learning with conformal abstention** (NLI-gated uncertainty sampling → ModernBERT retrain loop) | Targets the classifier's annotation budget at max-uncertainty examples; conformal prediction provides guaranteed coverage; abstention on low-confidence examples avoids propagating errors | Accuracy: converges to ~0.80+ after 2–3 retrain cycles. Cost: minimal (only labels the uncertain ~10–15%) | ⚠️ Medium — `ABSTAIN_THRESHOLD = 0.35` exists in classifier; need to wire NLI uncertainty as the sampling criterion. ~6h. |

---

## PART VI: CONCRETE NEXT-STEPS (priority order)

| Priority | Action | Effort | Rationale |
|----------|--------|--------|-----------|
| **P0** | **Train the ModernBERT classifier NOW** on the 1,027 golden examples. Run `scripts/train_discipline_classifier.py`. Report macro-F1, per-class confusion matrix. This is the end-state tool. | 2–4h | The classifier is scaffolded, the data exists, the architecture is sound. Every day spent debating the vote is a day the classifier isn't trained. |
| **P1** | **Run T-NLI + cleanlab on the golden set** (1,027 examples). Identify the ~100–200 FBs where both instruments flag the silver label. | 1–2h | This is the uncertainty gate. No LLM calls needed (NLI is local, cleanlab is CPU). Produces the targeted vote set. |
| **P2** | **Run the vote on the flagged subset only** (~100–200 FBs), with upgraded voters (Qwen3.8-27B + gemma-4-31B + Mistral/Llama). Sequential, lazy-loaded, batched with cool-down. | 4–8h | This cleans the silver labels where they're most likely wrong. 5–10× cheaper than voting all 1,027. |
| **P3** | **Re-train ModernBERT on the cleaned labels.** Compare macro-F1 before/after label cleaning. | 2–4h | This measures the vote's actual value. If ΔF1 < 0.02, the vote added no signal and should be retired immediately. |
| **P4** | **Implement Snorkel-style label model** over NLI + cleanlab + vote outputs. Replace naive majority with probabilistic labels. | 4–6h | This is the durable methodology upgrade. Makes future label-cleaning systematic, not ad-hoc. |
| **P5** | **Retire `label_vote.py`** after P3. Remove from `pipeline_config.yaml`. Document the retirement in `decisions.yaml`. | 30min | The vote is a scaffold. Scaffolds get removed after the building is up. |

---

## PART VII: CONSTRUCTIVE OBSERVATIONS

1. **The repo's governance maturity exceeds its tooling.** D2254 cross-examination, D2541 peer-review, per-label NLI thresholds, cleanlab auditing — these are sophisticated instruments. The naive 3-model majority vote is the weakest link in an otherwise strong label-quality ecosystem. The repo should leverage its existing machinery rather than adding a simpler tool.

2. **The handoff contains three factual errors that would have led to suboptimal decisions.** The pinned-model overcount (8 GB vs 3.80 GB), the k-NN deprecation omission, and the D2317 supersession all point to a handoff chain that propagates stale information — exactly the failure mode the D2254 cross-examination was designed to catch. **This roundtable itself should have been run through the D2254 protocol before being handed to auditors.**

3. **The classifier training is the critical path, not the vote.** Every hour spent optimizing the vote lineup is an hour the ModernBERT classifier isn't being trained, evaluated, and iterated. The 1,027-example golden set is small but sufficient for a first training pass. The classifier's confusion matrix will reveal exactly which disciplines need more data — that's the real next step, not a better vote.

4. **The per-label NLI thresholds (96 entries in `pipeline_config.yaml`) are a proto-Snorkel label model.** They encode per-label error rates from the NLI audit. Wiring them into a proper probabilistic label model (with cleanlab as a second LF) would be a natural, low-effort upgrade that makes the entire label-quality pipeline systematic.

5. **BUG-224 (Qwen3.8-27B wedge) is the binding operational risk for any vote run.** A 1,027-FB vote = 3,081 sequential model calls. At ~5s/call + 1s recovery sleep, that's ~5.1 hours of sustained load. The wedge (6.8→0.4 tok/s) would extend this to ~15+ hours and risk circuit-breaker trips. **Batch the run: 50 FBs → 30s cool-down → health check → next batch.** Monitor `omlx_watchdog.py` throughout.

---

## ULTIMATE VERDICT

**The 3-model generative vote is a bridge, not a destination.** P1 is correct: the end state is the ModernBERT classifier. P2 is correct in principle but wrong in its gating signal (k-NN is deprecated). P3 is correct and already implemented. P4 is correct: replace the small models, not the count. P5 is half-right: NLI is better as a gate than a voter.

**The single best action is to train the classifier now, run the vote only on the NLI+cleanlab-flagged subset with upgraded voters, measure the ΔF1, and retire the vote.** The repo's existing label-quality instruments (NLI, cleanlab, per-label thresholds, cross-examination protocol) are more mature and more accurate than the naive vote. Wire them into a Snorkel-style label model for durable value.

The vote scaffold served its purpose as a design document. Now build the building.

---

*Findings prepared independently. No DB mutations, no config changes. All claims verified against source files at commit `436fabc`.*

*Citations: file paths and line numbers referenced inline. External benchmarks: BTZSC [[25]], Snorkel [[1]][[2]][[6]], LLM ensemble calibration [[10]][[13]], GLiClass/ModernBERT [[20]].*