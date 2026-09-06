# ROUNDTABLE ADJUDICATION — Vote-Model Selection (post-D2584)

> **Adjudicator:** goose (senior RAG/systems/ML synthesis) · **Date:** 2026-09-06
> **Auditors reconciled:** Claude (Sonnet 5), ChatGPT (GPT-5-class), Qwen3.8-27B — independent, read-only, at pinned commit `436fabc`.
> **Method:** every correction below was re-verified against the repo *by the adjudicator* before acceptance (not assumed). See "Verification log".

---

## 0. Verification log (adjudicator re-checked each auditor claim against source)

| # | Auditor claim | Verified? | Evidence |
|---|---|---|---|
| 1 | Pinned models = **Phi-4-mini only (3.80 GB)**, not "Phi + gemma ~8 GB" (handoff copied the stale docstring) | ✅ TRUE | `pipeline/model_lazyload.py:59` `PINNED_MODELS = {"Phi-4-mini-instruct-8bit"}`; `:63` `MODEL_SIZES[Phi]=3.80, gemma-4-E4B=6.36` (not pinned) |
| 2 | **k-NN DEPRECATED** as a mislabel detector (D2575, 2026-09-05 — one day before the handoff) | ✅ TRUE | `scripts/knn_label_disagreement.py` header "⚠️ DEPRECATED… measures TOPICAL COHERENCE, NOT label CORRECTNESS"; `decisions.yaml` D2575 |
| 3 | Kernel panic = **D2243** (ACTIVE), not D2317 (a superseded empty stub) | ✅ TRUE | `decisions.yaml` D2243 "Kernel panic: IOGPUMemory… dual GPU clients… Gemma-4-31B"; D2317 = `**Category:** BUGFIX` stub, state SUPERSEDED |
| 4 | `run_wall_budget=48 GB` lives in **AGENTS.md D2496**, not `session_seed.yaml` (which has `memory_limit_gb: 24`, the OMLX RSS restart threshold) | ✅ TRUE | `AGENTS.md:90-93`; `agent/session_seed.yaml` |
| 5 | "decode ~6.8→0.4 tok/s" is **DELEGATE-002 (Qwen3-Coder-30B)**, not BUG-224 (Qwen3.8-27B = OMLX large-output wedge) | ✅ TRUE | `AGENTS.md` DELEGATE-002 vs `governance/buglog.md` BUG-224 |
| 6 | `gemma-4-26B-A4B-it-OptiQ-4bit` = **18.36 GB** (already in MODEL_SIZES, no download) | ✅ TRUE | `model_lazyload.py:70` |
| 7 | D2578 run #1 = **discipline macro-F1 0.2621**, domain ~0.0000 (data-limited, not model-limited) | ✅ TRUE | `decisions.yaml` D2578 |
| 8 | D2244: **Gemma-4-31B depth 50%**, **Phi-4-mini 37.5%**, both fail cross-domain 0/3 | ✅ TRUE | `decisions.yaml` D2244 |
| 9 | Cleanlab flags **48.7%** (3,424/7,026); T-NLI contradict **21.5%** (4,497/20,929) | ✅ TRUE | `agent/session_seed.yaml` (D2571/D2569) |

**Conclusion: all three auditors are correct on substance; the handoff's 5 factual errors are real and are corrected in the source handoff (see companion edit).**

---

## 1. Convergence on P1–P5

| Proposition | Claude | ChatGPT | Qwen | **Adjudicated** |
|---|---|---|---|---|
| P1 vote = stopgap, classifier = destination | AGREE | AGREE (+correction) | AGREE (strong) | **ACCEPT** |
| P2 gate with k-NN + NLI | DISAGREE | DISAGREE | PARTIAL (correct the gate) | **REJECT k-NN; use T-NLI ∩ cleanlab** |
| P3 sequential + lazy-load = safe | Arithmetic ok, 2 inputs wrong; residency unverified | DISAGREE (calls ≠ residency) | AGREE (corrected envelope) | **ACCEPT w/ mandatory residency fix** |
| P4 replace small voters with bigger | AGREE conditional | REJECT as strategy | AGREE (specific lineup) | **REFER — wrong layer** |
| P5 2 generative + DeBERTa NLI | DISAGREE | NOT PROVEN | PARTIAL (NLI = gate, not voter) | **REJECT as voter; keep NLI as gate** |
| Q6 better methodologies | weak-supervision #1 | weak-supervision #1 | Snorkel label model #1 | **ADOPT weak supervision** |

---

## 2. Ultimate recommendation (cherry-picked, senior synthesis)

**Verdict: do NOT run the 3-model vote across 1,027 FBs. The vote is one weak labeling function, not an oracle, and it must be retired after a single targeted pass.** The binding problem is *noisy silver labels* (cleanlab flags 48.7%), and the repo already owns three independent detectors for that noise. The durable architecture is:

```
gpt-oss teacher → { T-NLI + cleanlab + (limited generative challengers) }  ← labeling functions
                          ↓
            weak-supervision label model (Snorkel/Dawid-Skene)             ← calibrated, probabilistic
                          ↓
              human adjudication on high-disagreement subset (GOLD-A/B/C)   ← the true benchmark
                          ↓
            ModernBERT-base classifier (train → temperature-scale → conformal abstain)
```

**Cherry-picked actions, in priority order:**

1. **Correct the record** (5 handoff errors — already fixed in the companion edit). 30 min.
2. **Train the classifier NOW** (`scripts/train_discipline_classifier.py` on the 1,027 set) → baseline macro-F1 + **confusion matrix** that names which 61 disciplines need more data. *(Qwen's P0 — the critical path; D2578 already showed 0.2621 is data-limited.)* 2–4 h.
3. **Build the weak-supervision label model** over already-computed signals: LF-1 T-NLI (per-label thresholds already in `taxonomy.semantic_error_rate_max.per_label`, 96 entries), LF-2 cleanlab, LF-3 (optional) a generative challenger on the flagged subset only. Dawid-Skene/Snorkel estimates per-LF accuracy + correlation → probabilistic labels. *(ChatGPT + Qwen + Claude's #1; the repo's per-label NLI thresholds are already a proto-label-model.)* 4–6 h.
4. **Freeze GOLD-A / GOLD-B / CHALLENGE** (300–500 stratified, class-oversampled, book/author-disjoint) as the *true* eval target — measure against adjudicated gold, **never against gpt-oss agreement**. *(ChatGPT; D2286 already mandates this.)*
5. **Re-train ModernBERT on cleaned labels; temperature-scale; add conformal/selective abstention** on top of the existing `ABSTAIN_THRESHOLD=0.35` / `fail_closed_discipline: emerging` pattern. Evaluate vs GOLD-A (macro-F1, per-class F1, rare-class recall, calibration error, coverage curve). *(ChatGPT + Claude.)*
6. **Retire `label_vote.py`** to rare spot-checks once the classifier clears the bar. *(All three.)*

**If a generative challenger is used in step 3 at all — the only place the vote survives:**
- Target **only the ~100–200 FBs flagged by cleanlab ∩ T-NLI** (not 1,027).
- Corrected memory: pinned floor is **3.80 GB** (not 8 GB) → ~31 GB headroom; but **sequential *calls* ≠ sequential *residency*** — nothing currently unloads voter N before voter N+1 loads. First run the 20-min empirical test (`label_vote.py` on 5 FBs while polling `model_lazyload.py --status`), then wire `model_lazyload.py --unload` into `vote_one_fb()` if needed. *(Claude's gap — the one cheap fix everything else depends on.)*
- Voters: keep `Qwen3.8-27B`; swap `gemma-4-E4B` → `gemma-4-26B-A4B` (18.36 GB, already sized — **no download**); a third family (Mistral Small 24B-class) only if a clean MLX quant exists. Do **not** add a 2nd Qwen/3rd Gemma.

**Explicitly rejected:** running the current vote on all 1,027 FBs; treating k-NN as an uncertainty oracle; treating NLI entailment as ground truth; claiming ModernBERT will *automatically* beat the teacher (D2578 refuted that without label cleaning); spending this cycle downloading three larger LLMs.

---

## 3. Why this guarantees long-term value

The vote was a *means* (lift label quality), and the three auditors — independently, from three different model families — all identified the same failure: it was being promoted to an *end*. The durable value is not "a better trio of judges" but **a self-improving label substrate**: weak supervision turns every existing signal (NLI, cleanlab, the per-label thresholds, the occasional generative challenger) into *calibrated training labels*, and the ModernBERT student + conformal abstention turns those labels into a *fast, cheap, auditable* classifier that never asks a 27B model to disambiguate 61 labels at inference time. That is the architecture that survives, regardless of which generation of local model comes next.

---

## 4. Companion correction (handoff fact-check)

The source `ROUNDTABLE_HANDOFF_VOTE-MODELS_2026-09-06.md` has been corrected for the 5 verified errors (pinned 3.8 GB, k-NN deprecated, D2243 not D2317, run_wall_budget source, BUG-224/DELEGATE-002 split) so future auditors inherit a clean record — per the very lesson this roundtable re-proved: **a handoff is a summary, and summaries drift; verify against source before trusting.**
