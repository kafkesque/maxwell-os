# ROUNDTABLE FINDINGS — Claude — Vote-Model Selection & Approach Adjudication

> **Auditor:** Claude (Sonnet 5) · **Method:** `git clone` of `github.com/kafkesque/maxwell-os`, checked out at the pinned commit, then every factual claim below was verified against actual file content — not inferred from the handoff text. Where the handoff's own citation was wrong, I traced the correct one. Read-only: no DB, config, or existing governance file was touched.
> **Commit verified:** `436fabc1d41635a2d429dc10efdf487c38589c88` (exact match confirmed via `git rev-parse HEAD`).

---

## 0. Why this document leads with corrections, not verdicts

D2254's own cross-examination record (`governance/CROSS_EXAMINATION_D2254.md`) already proved this once: the four models that cloned the repo caught material errors in the handoff prompt; the four that reasoned from the prompt text alone reproduced those errors. That finding is the whole reason to distrust a document until it's checked — including this one. So before P1–P5, here is what didn't hold up.

### 0.1 Factual corrections to the handoff itself

| # | Handoff claim | What the repo actually shows | Where |
|---|---|---|---|
| 1 | "Kernel-panic history... `config/decisions.yaml` **D2317**" (cited 4×, including as the safety basis for §1.1's memory math) | **D2317 is the wrong ID.** The real entry is **`- id: D2243`**, `category: OPS`, description: *"Kernel panic: IOGPUMemory completeMemory prepare count underflow. Caused by dual GPU clients (mlx_lm direct load of Gemma-4-31B while OMLX serving Qwen3-Coder+Phi)."* `D2317` is a near-empty, `state: SUPERSEDED`, `champion: auto-sync` stub whose entire description is the literal string `'**Category:** BUGFIX'` — it has nothing to do with memory or kernel panics. My best guess: whoever assembled the handoff conflated a *file line number* (the kernel-panic text happens to sit at line 2317) with the decision *ID*. | `config/decisions.yaml:2243` (real), `:2923` (the empty D2317 stub) |
| 2 | "Pinned always-hot models (Phi-4-mini + gemma-4-E4B) \| ~8 GB \| `pipeline/model_lazyload.py`" | The file's own **executable code** disagrees with its **own docstring**. `PINNED_MODELS = {"Phi-4-mini-instruct-8bit"}` — one entry, ~3.80 GB per the file's own `MODEL_SIZES` table. The top-of-file "Architecture" comment says "Pinned models (Phi-4-mini, gemma-4-E4B)," but that's stale relative to the code beneath it, which explicitly comments "T1.1: Phi-4-mini is the small probe model — stays hot (~3.8GB)." The handoff copied the stale comment. Net effect: the real pinned floor is ~3.8 GB, not ~8 GB — about 4 GB *more* headroom exists than §1.1 computes. | `pipeline/model_lazyload.py:20-22` (docstring) vs. `:59` (code) |
| 3 | "run_wall_budget \| 48 GB \| `agent/session_seed.yaml` / loader" | `session_seed.yaml` never defines this value — I grepped it directly. The actual, correctly-labeled source is `AGENTS.md`'s D2496 memory-budget-labels block, which explicitly warns against exactly this kind of conflation: *"Memory budget labels (THREE distinct concepts — do not conflate, D2496): `delegate_model_budget` = ~24GB... `omlx_guard_ceiling` = 55GB (D1804/D2208)... `run_wall_budget` = 48GB — user hard wall..."* — and a prior forensic audit already flagged the *same* three-way conflation risk the handoff just fell into: `scripts/run_forensic_audit_parallel.py:53`, *"MEMORY BUDGET documented three ways: AGENTS.md:83 '~24GB'; decisions.yaml D2208 'OMLX memory guard ceiling 55GB'; user-stated wall 48GB... not clearly labeled."* | `AGENTS.md:83-86`, `scripts/run_forensic_audit_parallel.py:53` |
| 4 | "OMLX memory-guard ceiling \| 55 GB \| `config/decisions.yaml` D2317" | Same D2317 mix-up as #1. The ceiling's actual provenance is **D2208** (`N1 Yield Diagnostic Pass... OMLX memory guard ceiling`) plus a second confirming mention inside the real D2243 kernel-panic entry ("memory guard 55GB"). Not a contradiction, just the wrong pointer. | `config/decisions.yaml:2073-2078` (D2208) |
| 5 | "BUG-224: wedges under sustained load (decode ~6.8→0.4 tok/s)" attributed to **Qwen3.8-27B** | That decode-collapse figure belongs to a **different bug on a different model**: `AGENTS.md:79`, DELEGATE-002, describes **Qwen3-Coder-30B**'s multi-turn agentic decode collapsing "~6.8→0.4 tok/s" as context grows. BUG-224 itself (`governance/buglog.md:17`) describes something else on Qwen3.8-27B: OMLX hanging past its read-timeout on large-output calls (>~1200 tokens), needing 15-60s to recover — already mitigated in D2581 (`services.omlx.read_timeout=60`, wedge-recovery sleep), one day before this handoff, and explicitly flagged **"UNVERIFIED under a live sustained-load wedge."** The handoff's risk characterization of the current Qwen voter is real but describes the wrong failure mode. | `governance/buglog.md:17` (BUG-224), `AGENTS.md:79` (DELEGATE-002) |
| 6 | "`governance/buglog.md` BUG-053 (Phi hallucination)" | `buglog.md` is a **tiered** log — "OPEN at top, CLOSED at bottom," current file only. BUG-053 was retired long ago and lives in `archive/governance_pre_tiered_2026-09-03/buglog.md`, not the path cited. The underlying fact (Phi-4-mini hallucinates on open-ended tasks) is real and extensively corroborated elsewhere (`AGENTS.md:80`, `config/decisions.yaml` D2298, `pipeline/book_metadata.py:182`) — only the specific file pointer is stale. | `governance/buglog.md:1-4` (tiering note) |

None of these change the *substance* the handoff is worried about (the kernel panic is real; Phi does hallucinate; the memory wall is real) — but #1 and #2 both bear directly on the safety math in Must-Answer Q3, so they get corrected before I answer it, not after.

---

## 1. Verdicts on P1–P5

### P1 — "The vote is a stopgap, not the end state." **AGREE.**

For a *closed*, fixed ontology (61-way single-label + 43-way multi-label + 4-way depth), a trained discriminative head will beat any zero/few-shot generative ensemble on accuracy *and* cost once trained on clean labels — that's not a hedge, it's what happens whenever a fixed-taxonomy classification task has enough per-class examples for a small encoder to learn direct decision boundaries instead of relying on emergent generalization from a prompt. The repo doesn't even need a new experiment to see the ceiling on the generative side: `config/decisions.yaml` D2244 already benchmarked Gemma-4-31B at 50% and Phi-4-mini at 37.5% depth accuracy on this exact task family (both "fail cross-domain 0/3"), and Phi is independently documented to hallucinate on open-ended classification. A majority vote where two of three voters have *documented, non-trivial, correlated-with-task-type* failure modes has a real ceiling somewhere in the 60-80% range, not higher — correlated errors don't average out. A ModernBERT-base classifier trained on ≥1,000 *correct* examples across 61 classes is a realistically 80-90%+ target once the label-cleaning problem (see P2) is actually solved. The vote's only durable job is producing those clean labels once — not running forever.

### P2 — "Vote only the ~10-20% uncertain FBs, gated by k-NN + NLI." **DISAGREE, on both the mechanism and the assumed scope.**

Two independent problems, both verifiable in-repo:

**(a) One of the two proposed gates is already dead.** `scripts/knn_label_disagreement.py`'s own docstring, dated **one day before this handoff** (D2575, 2026-09-05): *"⚠️ DEPRECATED as a mislabel detector... k-NN low-agreement measures TOPICAL COHERENCE... NOT label CORRECTNESS... Keep this script ONLY for topical-coherence analysis. For mislabel detection use T-NLI contradiction... and cleanlab Confident Learning instead."* The handoff's own reference-files list (§6) cites this script as one of "two independent disagreement instruments" without registering that it was retired for exactly this purpose 24 hours earlier. Whoever assembled the handoff was working from a slightly stale mental model of the repo, not the repo itself.

**(b) The scope estimate is off by 2-5x, and the remaining gate isn't obviously trustworthy either.** I read the actual outputs that already exist on disk — this isn't a hypothetical:

| Instrument | Universe | Flagged | Rate |
|---|---|---|---|
| `governance/nli_label_audit.md` | 23,364 discipline+domain pairings | 10,071 "weak support" (entail<0.10) | ~43% |
| same | same | 4,640 "contradicts own label" | ~20% |
| `governance/cleanlab_label_audit.md` | 7,026 FBs / 61 labels | 3,424 flagged | **48.7%** |

That is nowhere near "10-20% uncertain." Either the silver labels really are wrong on roughly half the corpus (which would be the single most important fact in this whole brief, and worth its own investigation before anything else), or — more likely, given the repo's own prior diagnosis — these instruments are systematically over-flagging. D2298 already root-caused the same failure mode for RoBERTa in S5: *"evidence passages are LLM paraphrases, not verbatim — RoBERTa cannot differentiate paraphrase from contradiction."* `nli_label_audit.py`'s premise is the FB *definition* — itself an LLM-synthesized paraphrase, not source text — so the identical failure mode is a live, well-grounded hypothesis for why entailment scores are running this low. I haven't run new calibration myself, so I'm flagging this as a strong hypothesis, not a confirmed result.

**What I'd do instead:** before setting any vote-scope threshold, sample ~40-60 FBs stratified across (NLI-contradiction / NLI-weak / cleanlab-flagged / cleanlab-clean) and adjudicate ground truth by hand or by the single highest-trust model. That tells you the *precision* of each instrument at catching real mislabels — which is the number P2 actually needs and doesn't have yet.

### P3 — Memory math. **Arithmetic is fine; two of its inputs were wrong (see §0); the safety conclusion needs one more real check before it's trustworthy.**

With the corrections from §0 applied: real pinned floor is ~3.8 GB (not ~8 GB), so the active-model budget is closer to ~31 GB than ~27 GB. That's a small amount of *extra* slack, not less — it doesn't change the bottom line that 3×27B concurrently (~45 GB of model weights alone) still doesn't fit.

On "is sequential truly safe": I read `scripts/label_vote.py:282-296` (`vote_one_fb`) directly. It **is** a plain, synchronous `for voter in VOTERS:` loop calling `call_omlx_json()` once per voter with a `time.sleep(RECOVERY_SLEEP)` between calls — P3 is right that the *calls* are sequential. But P3's proposed fix ("requires a lazy-load daemon with a short idle-timeout") is not just a nice-to-have — **it doesn't currently exist in this script's execution path.** I grepped `label_vote.py` for any reference to lazyload/unload/daemon: zero hits. I grepped `justfile` and `pipeline/runner.py` for any reference to `label_vote.py` or `model_lazyload.py --daemon`: zero hits in both. `label_vote.py` is a fully standalone script — nothing tells OMLX to unload voter N before voter N+1 loads.

That matters because sequential *requests* only guarantee sequential *memory residency* if OMLX itself evicts the previous model on demand — and that's third-party server behavior this codebase doesn't control and I can't verify by reading the repo. Given BUG-224 already shows the *current single 27B voter alone* wedging OMLX under sustained load, and D2243's real kernel panic was specifically triggered by concurrent multi-model residency, "the calls happen one after another" is not the same claim as "only one model is ever resident" — and right now nothing in this codebase enforces the second claim.

**This is the one gap in the whole brief I'd fix before touching anything else**, because it's cheap to check and everything else (P4's bigger-model recommendation especially) depends on the answer: run `label_vote.py` on 5 FBs while polling `python3 pipeline/model_lazyload.py --status` between each voter call, and watch whether the previous model's RSS actually drops before the next one loads. Twenty minutes of work resolves whether P3's daemon requirement is theoretical or urgent.

### P4 — Cross-family lineup if voting continues. **AGREE with the shape (drop the two weak small models, keep dense-vs-dense diversity, no 3×same-family), conditional on P3's gap being closed first.** Ranked lineup below (§3).

### P5 — Hybrid (2 generative + 1 DeBERTa-NLI). **DISAGREE as proposed, for a specific and checkable reason.**

The already-computed `nli_label_audit.md` numbers above are the same numbers that would make DeBERTa a *third vote*: mean entailment 0.33 (discipline) / 0.26 (domain), with ~43% weak-support and ~20% contradiction against the corpus's own *current* labels. That's not "a cheap accurate third opinion" — it's a noisy signal being asked to arbitrate, on a task where its own house style (definition-as-premise, single-hypothesis entailment) has already been shown (D2298, on RoBERTa, same underlying mechanism) to confuse paraphrase for contradiction. Folding an uncalibrated noisy vote into a 2-of-3 majority can make the ensemble *worse*, not better.

If the roundtable wants a genuine NLI-based vote, it needs to be a different construction than what's already built: run entailment against **all 61 candidate discipline labels** per FB and take the argmax (the standard `facebook/bart-large-mnli`-style zero-shot classification pattern), not a single premise/hypothesis check against the FB's *current* label. That's a label-*proposal* mechanism; `nli_label_audit.py` is a label-*verification* mechanism — they are not interchangeable, and only the first one is a legitimate "vote." Benchmark that construction against the golden set before trusting it either way; right now P5's core empirical claim (does DeBERTa beat a 3.8B generative voter at this task) is **unproven in either direction** — the data that exists answers a different question.

---

## 2. Must-answer questions — direct answers

**1. Is P1 correct? Quantify the ceiling.** Yes (see P1 above). Generative-vote ceiling: ~60-80%, bounded by Gemma/Phi's own documented benchmarks (D2244) and correlated failure modes. ModernBERT-on-clean-labels target: ~80-90%+, standard for fixed 61-way classification with ≥1,000 examples once labels are actually clean — the open problem is the labels, not the model choice.

**2. Is P2 sound?** No, not as stated — see above. k-NN is deprecated for this purpose as of the day before the handoff was written; NLI's current construction over-flags at a rate (~20-43%) that's either a bombshell finding about the corpus or (more likely, per the repo's own D2298 precedent) evidence the instrument itself needs calibration before it's trusted to gate anything.

**3. Is P3's memory math correct?** Arithmetic yes, two input citations no (D2317→D2243; pinned floor 8GB→3.8GB) — corrected math gives slightly *more* headroom, not less. The open, unverified question is whether sequential OMLX calls actually guarantee sequential *residency* — nothing in the codebase currently enforces that, and it's a 20-minute empirical check away from being resolved.

**4. Optimal 3-model lineup if voting is kept?** See ranked shortlist, §3. Short answer: keep Qwen3.8-27B, upgrade Gemma-4-E4B → gemma-4-26B-A4B (already locally sized, no new download), replace Phi-4-mini with a genuine cross-family option (Mistral Small 24B-class, pending MLX quant availability).

**5. Is P5's hybrid defensible?** Not as currently constructed — see above. Unproven either way; the existing NLI artifacts answer a different question (verification, not classification) than the one P5 is asking.

**6. Underused methodologies?**

- **D2254 cross-examination / D2541 peer-review machinery:** D2541 (OWL2/DL disjointness, NLI reuse, ACM CCS two-axis model, OAEI/LogMap matcher, Fleiss κ) went **ACTIVE on 2026-09-03** — two days before D2580/D2582 scaffolded the 3-model vote. That's a short enough gap that these look like two threads that haven't been reconciled with each other, not two deliberately complementary systems. Worth a single pass to check for overlap/redundancy before investing further in either.
- **Weak supervision (Snorkel-style):** genuinely underused, and unusually cheap to adopt here, because the raw material already exists as computed artifacts (`governance/nli_label_audit.json`, `cleanlab_label_audit.json`, the vote's own majority output, plus the deterministic `config/alias_map.yaml` canonicalization used in D2584) — a proper label model (e.g., Dawid-Skene / Snorkel's generative model) learns *per-source accuracy* from agreement patterns alone, which both correctly demotes k-NN (already known to be a topical-coherence signal, not a correctness signal) *without discarding it entirely*, and gives calibrated labels instead of a flat 2-of-3 rule. This is the highest-leverage recommendation in this document.
- **LLM-as-judge/pairwise (MT-Bench style):** low relevance — built for open-ended generation quality, not discrete fixed-taxonomy labeling.
- **Conformal prediction/abstention:** high relevance, natural fit once the ModernBERT classifier exists — its `fail_closed_discipline: emerging` pattern (already in `config/pipeline_config.yaml:153`) is exactly the shape a conformal-coverage guarantee would formalize, better than an ad hoc vote-threshold.
- **Cross-encoder NLI re-ranking:** same family as current DeBERTa usage; the P5 recalibration above is the prerequisite, not a separate technique.

---

## 3. Market research — ranked shortlists

*(current landscape, verified via web search since this touches releases after my training cutoff)*

### Model candidates (≤6), IF the one-time vote is kept for label cleaning

| Rank | Model | Family | Why | Caveat |
|---|---|---|---|---|
| 1 | `Qwen3.8-27B-MLX-4bit` | Qwen | Keep — already local, dense, proven, R5-clean vs. gpt-oss | Community-reported (Aug 2026) tendency to "overthink"/verbose CoT; cap with `thinking_budget` as already done elsewhere in this pipeline (D2541 merged-call pattern) |
| 2 | `gemma-4-26B-A4B` | Gemma | Real capability upgrade over E4B ("probe only, not S4 classifier" per your own research doc); **already in `model_lazyload.py`'s `MODEL_SIZES` table at 18.36 GB — no new download needed** | MoE, 4B active — verify its structured-output reliability isn't worse than the dense 31B variant before committing |
| 3 | Mistral Small (24B class, 2026 release) | Mistral | Genuine third family (not Qwen/Gemma/gpt-oss), Apache 2.0, native JSON/structured-output support per its own model card, sized to fit a 64GB M1 Max at 4-bit | Needs an MLX quant to exist on `mlx-community` — check before committing; if unavailable, fall back to #4 |
| 4 | GLM-5.x "small" tier | ZAI | Your own `S4_MODEL_RESEARCH_2026-08-30.md` already names this as the R5-clean fallback if a swap is ever forced | Not yet benchmarked on this task by anyone in-repo |
| 5 | DeBERTa-v3-large, **recalibrated as argmax-over-labels zero-shot classifier** | (NLI) | Worth benchmarking as a genuinely independent signal — but only in this reconstructed form, not its current verification-only usage | Not a drop-in third vote as P5 proposes; needs the re-architecture described above first |
| 6 | `ModernBERT-base` | (encoder) | The actual end state, not a vote candidate — listed for completeness | N/A |

**Do not** add a second Qwen or third Gemma variant (P4 is right about this — correlated errors within a family defeat the point of voting). **Do not** re-add `gpt-oss-20b` (correctly excluded already — it's the teacher being verified).

### Methodological alternatives (≤3), ranked

1. **Weak-supervision label model** over the already-computed signals (majority vote + NLI + cleanlab, with k-NN correctly demoted to a topical-coherence-only input) → calibrated training labels for ModernBERT. Highest leverage, lowest new cost (no new inference calls — the data already exists on disk).
2. **Conformal prediction / abstention** wrapper on the trained ModernBERT classifier, calibrated on a held-out golden slice → replaces the ad hoc vote-threshold fail-close with a statistically-guaranteed coverage rate.
3. **Recalibrated DeBERTa argmax-over-labels zero-shot classifier**, benchmarked head-to-head against the generative voters on the golden set — resolves the actually-unproven core claim in P5.

**Benchmark plan for any of the above:** golden-set A/B, `temp=0.0`, cache-clean — same protocol already used in `scripts/benchmark_s4_quant_ab.py` and `scripts/benchmark_s4_ab.py`. Don't invent a new evaluation harness; this repo already has one that works.

---

## 4. Next steps, in priority order

| # | Action | Effort | Why first |
|---|---|---|---|
| 1 | Fix the two internal contradictions this audit surfaced: reconcile `model_lazyload.py`'s docstring vs. its `PINNED_MODELS` constant (pick one truth); correct the D2317→D2243 citation wherever it's propagated | 30 min | Cheap, prevents the next auditor from chasing an empty stub |
| 2 | **Empirically test OMLX residency**: run `label_vote.py` on 5 FBs while polling `model_lazyload.py --status` between voter calls; confirm whether the previous model's RSS actually drops before the next loads | 20-30 min | Everything about P3/P4 depends on this answer, and it's unverified right now — highest-value cheap check in this whole brief |
| 3 | Calibration study: sample ~40-60 FBs stratified across the NLI/cleanlab flag buckets, adjudicate ground truth, measure precision of each instrument | 2-4 hrs | Determines the real "uncertain fraction" for P2 instead of assuming 10-20% against measured 20-49% |
| 4 | If step 2 shows models don't auto-evict: wire `model_lazyload.py --unload <model>` into `vote_one_fb()` after each voter call | ~half day | Small, surgical patch — consistent with this project's own "minimum code that solves the spec" rule |
| 5 | If P4's lineup is adopted: source/verify an MLX quant for Mistral Small 24B-class, download, run the standard golden-set A/B before wiring into `label_vote.models` | ~1 day | Standard process already used for every other model swap in this repo |
| 6 | Build the weak-supervision label model over the already-computed signals to produce corrected golden-set labels | 1-2 days | This is P1's actual "durable value" of the vote, buildable entirely from artifacts that already exist on disk |
| 7 | Re-run `scripts/train_discipline_classifier.py` on the corrected golden set; evaluate against a held-out split; retire the 3-model vote to rare spot-checks once it clears the bar | ongoing | The actual end state everyone in this brief already agrees on |

---

## 5. One meta-observation

This handoff's own §0 instructs auditors not to let each other's answers cross-contaminate, for the same reason R5 mandates generator≠verifier. The gap between what the handoff *says* the repo contains and what the repo *actually* contains (§0 above) is the same gap D2254 already found and named: **a handoff document is a summary, and summaries drift from source between the moment they're written and the moment they're read — even by a few days, as the k-NN deprecation shows.** The fix isn't a better summary; it's what this document did: clone, checkout the pinned commit, and grep before trusting.
