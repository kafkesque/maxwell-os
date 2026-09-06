# LLM ROUNDTABLE HANDOFF — Vote-Model Selection & Approach Adjudication (post-D2584)

> **Prepared:** 2026-09-06 · **Repo:** `github.com/kafkesque/maxwell-os` · **Branch:** `main`
> **Reference commit:** `436fabc1d41635a2d429dc10efdf487c38589c88` (`main`). Check out with `git checkout 436fabc` to reproduce the exact audited revision.
> **Auditors:** Claude + GPT + one additional frontier model of your choice, as senior RAG/systems/ML engineers, working **independently**. Reconcile afterwards; do **not** let any auditor see another's answer first (shared-bias collusion — the same reason R5 demands generator ≠ verifier).
> **Mode:** READ-ONLY forensic + market research. Do not mutate `knowledge pipeline/maxwell.db`, `config/*.yaml`, or any governance file. Write findings to `governance/ROUNDTABLE_FINDINGS_<model>_VOTE-MODELS_2026-09-06.md`.
>
> **⚠️ CORRIGENDUM (2026-09-06):** the three auditors independently caught 5 factual errors in the original §1.1–§1.2 (pinned-model floor, k-NN deprecation, kernel-panic decision ID, `run_wall_budget` source, BUG-224/DELEGATE-002 conflation). All five were re-verified by the adjudicator and corrected below. See `governance/ROUNDTABLE_ADJUDICATION_VOTE-MODELS_2026-09-06.md` for the verification log.

---

## 0. What this is

Maxwell OS is a local-first knowledge pipeline: EPUB/PDF → extract → chunk → cluster → **S4 classify** → verify (NLI) → commit. S4 (currently `gpt-oss-20b-MXFP4-Q8`) assigns each Foundation Block (FB) two orthogonal labels: `discipline` (single-valued, 61-way) and `domains` (JSON array, 43-way), plus a 4-way `depth`.

The **auto-sorter** program (D2577→D2584) aims to replace the generative S4 teacher with a trained **ModernBERT-base discriminative classifier**. Its training set (`config/golden/stage4_golden_mined.yaml`, 1,027 examples) carries **silver labels** from the gpt-oss teacher (~75–90% accurate). To lift label quality before re-training, D2582 scaffolded a **3-model generative label vote** (`scripts/label_vote.py`).

**The question put to you:** is the 3-model generative vote the *best available ultimate solution* for this task, and if so, **which three models**? — or is there a better path with superior long-term value? This is a *strategy + model-selection* adjudication, not a plumbing audit.

---

## 1. Verified facts (not claims)

### 1.1 Hardware / memory budget (the binding constraint)

| Fact | Value | Source |
|---|---|---|
| Hardware | Apple M1 Max, **64 GB unified memory** | `governance/S4_MODEL_RESEARCH_2026-08-30.md` |
| Pipeline run hard wall (`run_wall_budget`) | **48 GB** | `AGENTS.md` (D2496 memory-budget labels) |
| OMLX memory-guard ceiling | 55 GB | `config/decisions.yaml` D2208 (D1804) |
| Min free memory (`memory_guard.py`) | 8 GB | `pipeline/memory_guard.py` |
| **Delegate model budget** (all delegate-served models combined) | **~24 GB** | `pipeline/model_lazyload.py` L58 |
| Pinned always-hot model (Phi-4-mini **only** — gemma-4-E4B is lazy-loaded, not pinned) | ~3.8 GB | `pipeline/model_lazyload.py:59` `PINNED_MODELS` |
| Kernel-panic history (dual GPU clients + Gemma-4-31B) | yes | `config/decisions.yaml` **D2243** (D2317 is a superseded stub) |

**Memory envelope derived (auditors re-verified with corrections):**
- Usable for models during a run ≈ 48 (wall) − 8 (min-free) − ~5 (OS+server) ≈ **35 GB**.
- Minus pinned ~3.8 GB → **~31 GB for the active big model(s)**.
- Single 27B@4-bit ≈ 15 GB ✅ · single 31B@8-bit ≈ 17–19 GB ✅ (tight) · 70B@4-bit ≈ 40 GB ❌.
- **3 × 27B in parallel ≈ 45 GB ❌** (exceeds the 48 GB wall → kernel-panic risk per D2243).
- 3 × 12B@4-bit in parallel ≈ 21 GB + 3.8 GB pinned ≈ 25 GB — under the wall but **over the 24 GB delegate budget**.

### 1.2 Current vote lineup (`config/pipeline_config.yaml` → `label_vote.models`)

| Voter | Size | Family | Repo's own verdict |
|---|---|---|---|
| `Qwen3.8-27B-MLX-4bit` | 27B dense | Qwen | Capable, but **BUG-224**: OMLX wedges on large-output calls (>~1200 tokens) under sustained load (mitigated D2581, unverified). *(The ~6.8→0.4 tok/s decode-collapse is DELEGATE-002 on Qwen3-Coder-30B — a different model.)* |
| `gemma-4-E4B-it-MLX-4bit` | **4B** | Gemma | `S4_MODEL_RESEARCH`: "probe only, **not S4 classifier**" |
| `Phi-4-mini-instruct-8bit` | **3.8B** | Phi | BUG-053: hallucinates on open-ended; removed from S5 (D2298) |

### 1.3 Models already on disk (local HF cache, 168 GB total)

| Model | Family | Notes |
|---|---|---|
| `Qwen3.8-27B-MLX-4bit` | Qwen | current voter 1 |
| `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` | Qwen | MoE (30B/3B active); S2 generator |
| `gemma-4-31B-it-MLX-8bit` | Gemma | downloaded; **kernel-panic source** (D2243) |
| `gemma-4-E4B-it-MLX-4bit` | Gemma | current voter 2 |
| `gpt-oss-20b-MXFP4-Q8` (+Q4) | OpenAI | S4 teacher (EXCLUDED from vote — circular) |
| `Phi-4-mini-instruct-8bit` | Phi | current voter 3 |
| `Qwen3.5-9B-4bit` | Qwen | partial download |
| `Qwen2.5-7B` / `Qwen2.5-Coder-7B` | Qwen | older |
| `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` | (NLI) | SOTA zero-shot NLI — **already local** |
| `answerdotai/ModernBERT-base` | (encoder) | the classifier student |

### 1.4 Task characteristics

- **61-way single-label** discipline + **43-way multi-label** domain + **4-way** depth — a *fixed, bespoke ontology*.
- This is a **discrimination** problem, not a generation problem.
- Live HF query (2026-09-06) for `pipeline_tag=text-classification` and `zero-shot-classification`: top results are sentiment (FinBERT, SST-2), rerankers (bge), prompt-guard — **zero public models fine-tuned for a 61-way design-principle taxonomy** (consistent with `S4_MODEL_RESEARCH_2026-08-30.md` §3).
- The **correct long-term tool** is the already-scaffolded `scripts/train_discipline_classifier.py` (ModernBERT-base, ~1 GB, fast).

---

## 2. The initiating engineer's propositions (to be challenged, not rubber-stamped)

**P1 — The 3-model generative vote is a stopgap, not the end state.** For a fixed 61/43/4-way ontology, a trained discriminative classifier will beat any generative model on accuracy *and* cost. The vote's only durable value is *flagging where the silver labels are wrong* — not producing final labels. **Recommend: treat the vote as a one-time label-cleaning instrument, then retire it.**

**P2 — If the vote is kept, do NOT run it on all 1,027 FBs.** [CORRIGENDUM: the original cited k-NN agreement as a disagreement instrument, but k-NN was **deprecated 2026-09-05 (D2575)** — it measures topical coherence, not label correctness.] The repo's two *live* mislabel instruments are **T-NLI contradiction** (`pipeline/nli_label_audit.py`) and **cleanlab Confident Learning** (`scripts/cleanlab_label_audit.py`). **Recommend: gate the vote on the T-NLI ∩ cleanlab intersection (~10–20% of FBs), not on k-NN**, so effort targets real mislabel risk.

**P3 — The memory answer is "sequential + lazy-load", not "parallel".** 3 × 27B in parallel is infeasible (≈45 GB > 48 GB wall). But `label_vote.py` already calls voters **sequentially**, and `model_lazyload.py` unloads idle big models — so only ONE big model needs to be resident at a time (peak ≈ 23 GB). **Recommend: 3 bigger voters are feasible *sequentially*, but require a lazy-load daemon with a short idle-timeout so models never co-reside.**

**P4 — If bigger voters are wanted, the weak links are the two small models (4B + 3.8B), not the count.** A 4B/3.8B model cannot reliably disambiguate 61 close disciplines. **Recommend: replace them with 12–31B models from *different* families** (cross-family is R5-mandatory), e.g. Qwen3.8-27B + gemma-4-27B/31B + a Llama/Mistral ~12–24B. **Do not** use three Qwen variants (correlated errors).

**P5 — No public model is "fine-tuned for this task"; the only such model is one we train.** The strongest *off-the-shelf* classification tool is zero-shot NLI (DeBERTa-v3-large, already local) — and it may be a *better and cheaper "third opinion"* than a 3.8B generative voter. **Recommend: consider a hybrid vote = 2 generative cross-family voters + 1 DeBERTa-NLI zero-shot classifier** (also satisfies R5 cross-family).

---

## 3. Must-answer questions

1. **Is P1 correct?** Is the generative vote ever the *right* answer for a fixed ontology, or is it strictly a bridge to the discriminative classifier? Quantify the accuracy ceiling of a 3-model generative vote vs a fine-tuned ModernBERT on ~1k examples.
2. **Is P2 (targeted voting) sound?** Are k-NN agreement and NLI entailment reliable enough as the "uncertainty" signal to gate the vote, or do they over/under-flag?
3. **Is P3's memory math correct?** Re-derive the envelope. Is 3 × 27B *sequential* truly safe on this hardware (given the D2243 kernel panic), or is even a single 31B@8-bit + pinned ~3.8 GB too close to the 55 GB guard?
4. **Is P4's lineup optimal?** If voting is kept, what is the *strongest* 3-model cross-family set that (a) fits the memory envelope, (b) is available as MLX/GGUF, (c) is best at fine-grained structured classification?
5. **Is P5's hybrid (2 generative + 1 NLI) defensible?** Does DeBERTa-v3-large zero-shot NLI actually beat a 3.8B generative model at 61-way discipline assignment on this corpus? (Repo has NLI audit data you can reason over.)
6. **Are there existing peer-review / label-quality methodologies — in-repo or in the literature — that already solve this better than a naive 3-model majority vote?** Specifically investigate: (a) the repo's own **cross-examination protocol (D2254)** and **peer-review methodology (D2541)** — are they being under-used here?; (b) **LLM-as-judge / pairwise-preference evaluation** (MT-Bench / AlpacaEval style); (c) **weak-supervision / programmatic labeling** (Snorkel-style label functions, majority/weighted voting with estimated accuracies); (d) **ensemble calibration** (temperature/logit-based, not raw vote-count); (e) **active learning** (uncertainty sampling gated by T-NLI contradiction + cleanlab, not k-NN — which is deprecated); (f) **conformal prediction / abstention** for label confidence; (g) **cross-encoder NLI re-ranking** as a label scorer. For each: is it more accurate *and* cheaper than the vote on this corpus? Which single technique, if any, should replace the vote?

---

## 4. Market-research brief (do this *only* if you agree the vote approach survives)

Search Hugging Face (and Ollama / LM Studio / OMLX MLX-community hubs) for the **strongest local, cross-family, memory-feasible** models for **fine-grained structured classification**. Constraints:

- **Memory:** must fit the §1.1 envelope (single model ≤ ~20 GB @4-bit; 70B+ is out unless it runs *alone* with no pinned co-residents).
- **Family diversity (R5):** need ≥3 distinct families (Qwen / Gemma / Llama / Mistral / Phi / DeepSeek-local / GLM-small / gpt-oss).
- **Task fit:** instruction-following + reliable JSON/enum output (or a classifier/NLI head). Prefer models with strong structured-output or `json-mode` support.
- **Format:** MLX (`mlx-community`/`lmstudio-community`) or GGUF (Ollama) — must be runnable on M1 Max.
- **Long-term value:** prefer models that also serve other pipeline roles (S2 generation, S4 teacher, review) so the download earns its disk cost.
- **Check specifically for:** any model fine-tuned for **taxonomy/ontology classification**, **hierarchical classification**, or **zero-shot NLI** that beats `DeBERTa-v3-large` for this corpus.
- **Also research *methodologies* (not just models):** label-quality verification and fine-grained taxonomy classification techniques — LLM-as-judge, weak supervision (Snorkel), programmatic label functions, ensemble/committee calibration, active learning, conformal abstention, cross-encoder NLI re-ranking. Note which are mature/off-the-shelf vs bespoke, and which the repo's own D2254/D2541 machinery already partially implements.

Deliverable: a ranked shortlist of ≤6 model candidates *and* a ranked shortlist of ≤3 methodological alternatives to the vote, each with: rationale, accuracy-vs-cost estimate on this corpus, and a benchmark plan (golden-set A/B, temp=0.0, cache-clean) before any production change.

---

## 5. Output contract

Write findings to `governance/ROUNDTABLE_FINDINGS_<model>_VOTE-MODELS_2026-09-06.md` with:
1. Verdict on P1–P5 (agree / disagree + reasoning).
2. Any *better* approach I missed (be specific — architecture, not hand-waving).
3. If vote survives: the ranked model shortlist + benchmark plan.
4. Concrete next-step list, in priority order, with effort estimate.

Do not mutate the DB or configs. Cite file paths/line numbers for every factual claim you verify.

---

## 6. Reference files

- `scripts/label_vote.py` — the vote (sequential voters, majority/fail-closed, flags).
- `scripts/train_discipline_classifier.py` — the ModernBERT classifier student.
- `scripts/mine_classifier_golden.py` + `config/golden/stage4_golden_mined.yaml` — training set.
- `pipeline/model_lazyload.py` — lazy-load + ~24 GB budget + pinned ~3.8 GB (Phi-4-mini only).
- `pipeline/memory_guard.py` — min_free_gb=8.
- `governance/S4_MODEL_RESEARCH_2026-08-30.md` — prior model research (frontier too big; no bespoke classifier).
- `governance/CROSS_EXAMINATION_D2254.md`, `CROSS_EXAMINATION_V2_D2254.md`, `CROSS-EXAMINATION-IMPLEMENTATION-SPEC-2026-08-12.md`, `CROSS-LLM-AUDIT-VERDICT-2026-08-15.md`, `ROUNDTABLE_MASTER_PROMPT.md` — the repo's existing peer-review / cross-examination machinery (check whether it is being under-used here).
- `config/model_assignments.yaml` — role→model registry + R5 constraints.
- `config/decisions.yaml` D2317 (kernel panic), D2580/D2582 (vote design), D2584 (data-absent fix).
- `governance/buglog.md` BUG-224 (Qwen wedge), BUG-053 (Phi hallucination).
- `governance/SESSION-HANDOFF-2026-09-06.md` — current state.
