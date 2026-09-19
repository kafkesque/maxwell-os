# MARKET RESEARCH — 2026-09-17

> **CONTEXT (read `governance/CONTEXT_INDEX.md` first).** Part of the 2026-09-17 report set:
> priority -> `PRIORITY_DECISION_20260917.md` | findings -> `FORENSIC_AUDIT_20260917.md` |
> external methods -> `MARKET_RESEARCH_20260917.md` | plan -> `STRATEGIC_PLAN_20260917.md` |
> execution + **human gates** -> `SEQUENCE_STATUS_20260917.md`. Floors + provenance vocabulary:
> `config/eval_integrity.yaml`. Axis values: `config/content_types.yaml`.
> **Do not restate a config value in this file - cite the path.**


**Question:** which peer-reviewed methods, tools, repos and stacks should S0–S6 adopt, reference
or integrate to improve reliability, accuracy and knowledge recall — on both the input and the
output side — without violating C1 ($0 marginal), C2/C4 (no lock-in) or C3 (sovereignty)?

**Method.** `feed.opml` (36 sources: arXiv cs.RO/CC/DS/FL/CL-adjacent RSS, GitHub topics for
vector-search/faiss/RAG/embeddings/clustering/hnsw/MLX/Apple-silicon) + **live** arXiv API
queries (18 queries, sorted by relevance and by submission date), the HuggingFace model API and
PyPI for versions. Every ID below was returned by a live query today.

**Reading discipline (stated up front).** These are *title/abstract-level* signal, not verified
reviews. Each ADOPT row therefore names the artifact in this repo it would change and the
measurement that decides whether it helped. A recommendation that cannot be falsified locally in
one session is marked REFERENCE.

---

## A. ADOPT — highest leverage first

### A1. Statistical power and stop rules for small-n suites
**2607.08522** *Stop Guessing When to Stop Testing: Efficient Model Evaluation with Just Enough Data*
(2026-07-09) · **2605.11209** *Measuring Five-Nines Reliability: Sample-Efficient LLM Evaluation in
Saturated Benchmarks* (2026-05-11) · **2608.09622** *Adaptive Sequential Test Planning for
Multi-Mechanism Reliability Qualification* (2026-08-10).
**Why it matters here, concretely:** this project decided the tool-calling role on **n=20**, the
planner on **n=24**, reviewing on **n=6**, and once on **n=4** (REAP 1.00, which died at n=20).
Today's P1 swap rests on a **2-item** margin (14/20 vs 12/20) and the planner retention on a
**1-item** band. Those decisions are currently governed by a hand-written tie rule, not by an
interval.
**Adopt:** a per-suite `n_min` table in `config/` + a sequential stop rule (stop when the
confidence interval is tighter than the decision margin). Then "no role may be decided on a suite
with n < n_min" becomes a checkable criterion instead of a convention.
**Cost:** $0, no model time (analysis only). **Decided by:** does any planned role flip when the
interval is used instead of the tie rule?

### A2. The right agreement metric for each axis (this is the "spotless" measurement problem)
**2603.06865** *Counting on Consensus: Selecting the Right Inter-Annotator Agreement Metric for NLP
Annotation and Evaluation* (2026-03-06).
**Why:** the project already discovered empirically that exact-set unanimity is the wrong operator
for the multi-label **domain** axis (D2633: 42/216 = 19.4% unanimous, which over-abstains) and the
right one for the singular **discipline** axis. That is precisely the paper's subject. Today's
190-row vote adds the same evidence in the other direction: 6/190 rows agreed on all three axes.
**Adopt:** report **Krippendorff's α** per axis over `gold_4axis` (nominal for
content_type/discipline/depth, multi-label/unitising for domains), and define the tier boundary as
α ≥ threshold rather than "the models agreed". Replace "spotless" with a number.
**Cost:** $0. **Decided by:** whether α moves when the disputed rows are removed — i.e. whether the
anchor is stable or just small.

### A3. Judge datasheets — stop trusting a judge because it is a different model
**2606.15610** *LLM Judges Have Dark Current: A Psychometric Datasheet for LLM-as-a-Judge
Evaluation* (2026-06-14) · **2510.11822** *Beyond Consensus: Mitigating the Agreeableness Bias in
LLM Judge Evaluations* (2025-10-13) · **2406.07791** *Judging the Judges: A Systematic Study of
Position Bias in LLM-as-a-Judge* (2024-06-12).
**Why:** today's P0 result is exactly a judge-datasheet finding — gemma reproduces the stored FORM
label 97% within family, gpt-oss only 53% across families, and the 2023-era human adjudication had
gemma overruling Qwen 36/49 times ("agreeableness"/self-preference class).
**Adopt:** one CSV/JSON row per judge model, produced by a script, carrying: within-family
reproducibility, cross-family agreement, abstain rate, position-swap sensitivity, verbosity
correlation. Bind it to the role registry so no judging role can be assigned without one.
**Cost:** the P0 run already produced the first two numbers; ~0 extra model time.

### A4. Harness sensitivity as a first-class eval axis (the BUG-262..266 citation)
**2605.26731** *It's Not the Capability: Harness Sensitivity Is Non-Monotone Across LLM Agent Tiers*
(2026-05-26) · **2606.04056** *Token Budgets: An Empirical Catalog of 63 LLM-Agent Budget-Overrun
Incidents* (2026-06-02) · **2609.17306** *Mo' Models, Mo' Problems: How to best select model pools
when designing Multi-Agent Systems* (2026-09-15).
**Why:** BUG-262/263/264/265/266 are a textbook instance of the first two; the project's own
Layer-C voting analysis (majority 0.656/0.634 < single-best 0.693) is an instance of the third —
error-correlated voters cannot be averaged into accuracy.
**Adopt:** cite these in `governance/p0_p1_contract.md` §mechanisms; use 2609.17306's pool-selection
method to compute the error-correlation matrix the Layer-C plan already specifies, and keep the
voting ensemble limited to the unanimity gate.

### A5. End the domain-axis pain with a training-free taxonomy matcher (a 3-way bake-off)
**D2634/D2636 already proved**: a 43-way sigmoid head is starved (macro-F1 0.009) and the
cross-encoder reranker collapses across 43 classes at every threshold (macro-F1 0.0). Buyers:
`MoritzLaurer/bge-m3-zeroshot-v2.0` (122k downloads, ONNX-capable, still unbenchmarked here),
`BAAI/bge-m3` + taxonomy-definition cosine (already in production feeding `taxonomy_match_method`),
and a **hierarchical route** (top-8 parents → children) whose motivation is in the retrieval
literature on granularity (**2609.18099** *When Is Graph Structure Worth Its Cost?* argues for
pricing structure rather than assuming it).
**Adopt:** a 1-hour, 3-way bake-off on the 251 gold rows using existing scripts, judged by
macro-F1 and coverage@precision. **Decided by:** does any path beat the current
`taxonomy_match` baseline? If yes, retire the domain head entirely.

### A6. Retrieval-side diagnostic decomposition (the recall measurement the project never had)
**2408.08067** *RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation*
· **2309.15217** *Ragas* (PyPI `ragas` **0.4.3**) · **2311.09476** *ARES* · **2607.07302**
*Evaluating RAG Metrics in Applied Contexts* (2026-07-08, includes limitations).
**Why:** the pipeline measures classification accuracy and NLI entailment, but has no
claim-level decomposition (context recall vs claim recall vs faithfulness vs noise sensitivity).
`governance/retrieval_hyde_ab.log` exists; a metric *framework* does not.
**Adopt:** Ragas as the *trend line* only, with gemma-4-E4B as the local judge (never a frontier
API — C1/C3), and record that its scores are relative, not ground truth. Pair it with a gold
query set (25 queries in `config/golden/retrieval_queries.yaml`). This is the missing link between
"the KB has 7995 FBs" and "the KB answers questions".

### A7. A real annotation tool for the 169-row hard tail
`label-studio` **1.23.0**, `argilla` **2.8.0** (both open source, self-hosted, C2/C3-clean).
**Why:** the hard tail is the single blocker on "spotless", and today's evidence (F-04: 3.2% full
agreement from the best model pair) says no model vote will close it. The project's answer so far
has been hand-written markdown review sheets, which is exactly what makes adjudication feel
"unbounded" and therefore deferred.
**Adopt:** stand up Argilla (or Label Studio) locally, import `pending_4axis.jsonl` (169 rows) with
4 axes + a confidence field, and compute α live. A resumable annotation job with a progress bar
converts an unbounded fear into ~169 bounded decisions.
**Cost:** $0 marginal, one install, local only.

### A8. Contamination and provenance/lineage as mechanical checks
**2502.14425** *A Survey on Data Contamination for LLMs* · **2407.08716** *A Taxonomy for Data
Contamination* · **2510.09259** *Detecting Data Contamination from RL Post-training*.
**Adopt:** today's ad-hoc leak test becomes `scripts/audit_eval_train_contamination.py`
(text-shingle overlap between the training pool and any eval anchor), wired into the criteria file
and reported in every eval artifact. For lineage, the finding is F-02 (provenance was dropped on
4057 rows) — the paper-side answer is that lineage must be stamped at write time; there is no
retrofit.

### A9. Response-normalisation as one shared, tested component
**2606.04056 / 2605.26731** (above) motivate it; the concrete defect is F-11.
**Adopt:** a single `read_response(msg)` in `pipeline/omlx_call.py` that normalises
`content` / `tool_calls` / `reasoning_content` and treats `''` as retryable, plus the harness
contract test from F-06. This is the cheapest permanent fix for the whole BUG-26x class.

### A10. Quantization A/B with an instrument, not a vibe
**2609.18005** *A Calibrated Instrument for Measuring How Inference Optimizations Affect Output
Quality* (2026-09-16) · **2607.21063** *QuantiBias: Benchmarking Quantization-Induced Bias in LLMs*
(2026-07-23).
**Why:** the planned Ornith 9B 4-bit vs 8-bit A/B (benchmark_plan_v2 §5) is currently specified as
"settles it empirically" without saying what to measure beyond accuracy.
**Adopt:** measure accuracy **and** bias/flip-rate per item, report intervals (A1), and keep the
mixed-precision tensor layout on the record. NOTE: `MoritzLaurer/DeBERTa-v3-large-mnli-...`
(last modified 2024-04) and `BAAI/bge-m3` (2024-07) are both frozen and stable — do not churn the
embedder/verifier mid-program.

### A11. DSPy re-open discipline
`dspy-ai` is at **3.3.1**; **2507.03620** *Is It Time To Treat Prompts As Code?*; **2412.15298**
*Comparative Study of DSPy Teleprompter Algorithms*.
**Adopt:** before re-opening DSPy (gated by D2592/D2594: Tier1 + Tier2 + Tier3), pin the version,
version the compiled program as an artifact, and require a before/after measurement on the frozen
gold — exactly the treatment the project already applies to models.

### A12. Give the FORM axis a verification consumer (closes the W5 drift)
**2609.16816** *ImpossibleRubrics: Stress-Testing Generated Rubrics as Reward Signals* (2026-09-15) ·
**2408.08067 RAGChecker** (claim-level decomposition) · **2606.15610** judge datasheets (A3).
**Why:** `config/content_types.yaml` already defines a per-FORM verification standard
("causal_mechanism → evidence must show the causal chain", "descriptive_model → categories complete
+ mutually exclusive", "empirical_pattern → correlation only, do not assert causation"). Nothing
consumes it: S5 runs NLI on the definition, not on the FORM rubric, and the anchor has zero FORM
labels (F-15). A storage axis with no verifier is decorative — and it is also how 4,054 rows kept a
pre-repair FORM label through a S6 commit without anything failing.
**Adopt:** turn each FORM's `verification_standard` into a claim-level entailment target for S5
(causal_mechanism requires the evidence to entail the X→Y-because-Z chain; empirical_pattern must
*not* entail causation), and stress-test those rubrics before trusting them (ImpossibleRubrics is
the cautionary method). **Cost:** the S5 rubric strings are already written; the work is wiring +
one calibration run on the FORM anchor.

---

## B. REFERENCE — worth reading, do not integrate yet

| Item | Why reference, not adopt |
|---|---|
| **2605.26252** *Is Agent Memory a Database?* | argues for explicit data-model contracts over ad-hoc agent memory — supports the existing sqlite-vec + typed-schema choice; no code change |
| **2603.22812** semantic entropy, adaptive Bayesian | a second uncertainty signal for the abstain gate; needs a GPU-ish budget and its own calibration; revisit after A1/A2 give a measurement frame |
| **2609.17012** ORDER (task-conditioned routing), **2609.16816** ImpossibleRubrics | routing and rubric-validity ideas relevant to Layer C/D; read before designing the next suite |
| **2604.05253** Spike Hijacking in Late-Interaction Retrieval | security angle if late interaction is ever reconsidered (it was rejected for index churn) |
| **2609.18099** structure pricing | use as the cost/benefit frame if GraphRAG-style expansion is proposed; the FB graph is currently flat and cheap — keep it that way until a measured gain appears |
| **2609.12464** hierarchical context-aware GraphRAG vs standard RAG | enterprise code case study; read for granularity ideas, not for adoption |
| `trulens` 2.14.0 / `opik` 2.2.66 / `deepeval` 4.2.3 / `promptfoo` | trace/eval dashboards; adopt only if the artifact-based `drift_monitor` proves insufficient. Adding a SaaS-shaped dependency for a $0-marginal local system is a future tax |

---

## C. REJECT (with the reason, so it is not re-proposed)

- **Training a 43-way domain head** — measured dead (macro-F1 0.009; D2636). Use A5.
- **Majority voting over local models for discipline/domain** — measured worse than the best single
  model (0.656/0.634 vs 0.693; `voting_verdict_20260916.md`). 2609.17306 says why: correlated errors.
- **Exact-set unanimity as the acceptance operator** — 29.1% agreement even for the anchor itself;
  use α (A2).
- **Any frontier-API judge or cloud eval SaaS** — violates C1/C3; the local roster suffices for
  every measurement listed above.
- **Heavy index churn (late interaction / GraphRAG expansion) before retrieval metrics exist** —
  you cannot price the gain without A6.
- **`mmlu_pro`-style general-knowledge suites** — knowledge lives in the graph, not the weights
  (already noted in benchmark_plan_v2 §1).

---

## D. What this research does NOT establish

I did not read full papers; the IDs/titles/dates came from live queries and the claims above are
domain-standard interpretations plus the project's own measurements. Anything marked ADOPT should
be read (abstract + method section) before it changes a threshold. Two specific caveats: the
Krippendorff-α multi-label estimator must be chosen deliberately (there are several), and Ragas'
LLM-judged metrics inherit every judge bias documented in A3.
