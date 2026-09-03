# Master Roundtable Evaluation Prompt — v10.0
## ONTOLOGICAL INTEGRITY + AGENTIC-DEPLOYMENT READINESS + BOTTLENECK AUDIT

**Authority:** D2000–D2543 | BUG-053–BUG-220 | Maxwell OS v3.0
**Audience:** S-tier senior ontological engineer AND RAG engineer — independent evaluators (Claude, ChatGPT)
**Repo:** `github.com/kafkesque/maxwell-os` (all changes pushed; ground truth = `DECISION-LOG.md`, `config/decisions.yaml`, `governance/buglog.md`)
**Date:** 2026-09-03
**Mandate:** Do NOT rubber-stamp. Flag anything unsound, unverifiable, or "pass-by-accident". Answer every question with concrete, prioritized, actionable findings.

---

## §0. WHAT MAXWELL OS IS

A sovereign, local-first ($0 marginal cost) knowledge pipeline that converts books → Foundation Blocks (FBs) → verified, retrievable principles for agentic RAG. 8 stages: `0 Convert → 0.5 Metadata → 1 Chunk → 1.3 Prefilter → 1.5 Embed/Cluster → 2 Convergent Extract → 4 Merge/Classify → 5 Verify → 6 Commit` (Stage 3 removed, D2120/D2198).

**Active models (all local):**
| Role | Model |
|------|-------|
| S2 Generator | Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (MoE) |
| S4 Classifier | gpt-oss-20b-MXFP4-Q8 (reasoning MoE) |
| S5 Verifier | MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (NLI, threshold 0.10) |
| Embeddings | bge-m3 (512-d Matryoshka) |
| S2 probe | Phi-4-mini-instruct-8bit |
| Auditor (R5) | Qwen3.8-27B-MLX-4bit (256K, dense) |

**Retrieval stack:** SQLite FTS5 + sqlite-vec (bge-m3) + Reciprocal Rank Fusion (RRF) + cross-encoder rerank (S2 rerank ENABLED, D2521). HyDE and contextual-embedding REJECTED (D2522).

---

## §1. GROUND TRUTH — VERIFIED 2026-09-03 (do not trust stale numbers)

| Metric | Value |
|--------|-------|
| Total FBs | **7,995** |
| S5 status | **PASS 3,310 (41.4%) / QUARANTINE 4,685 (58.6%)** — commit-with-status (D2420) |
| discipline = `emerging` | **2,262 (28.3%)**; canonical = 5,733 (71.7%) |
| Canonical taxonomy | **61 disciplines + 44 domains = 105 labels** |
| Raw vocabulary | **1,391 discipline_raw + 5,162 domains_raw = 6,553 labels** (by-design keep-unique) |
| Cross-contamination (axis leaks) | **0** (a label on BOTH discipline+domain axes) |
| Unknown/invalid labels | **0** |
| Empty `discipline_raw` | **1,485** (311 canonical + 1,174 emerging) |
| Empty `domains_raw` | **29**; empty canonical `domains` = 0 |
| Both-axes singletons | **8** |

**Open bugs (current):** BUG-216 (27 empty domains_raw), BUG-217 (mixed checkpoint stamps v5.1/v5.5 — taxonomy_match_method + manifest_hash not synced), BUG-218 (9 sidecar empty-shells), BUG-219 (integrity-checker false-positives on stdlib imports), BUG-220 (`delegate()` to Qwen models fails "error decoding response body"; direct one-shot OMLX curl works).

---

## §2. QUESTION 1 — ONTOLOGICAL INTEGRITY (issues + cross-contamination fix + Track B)

**Context — what was just done:**
- **BUG-197 / D2422 / D2500** — the discipline-vs-domain axis leak (a label appearing on both axes). Fixed two ways: (a) disjointness rules in the S4 classify prompt ("a branding principle → `brand identity`, NOT `marketing`"); (b) **D2519 deterministic kind-swap** — `scripts/bug197_kind_swap.py`, LLM-free, field-scoped UPDATE of 3,694 FBs (598 disciplines recovered, 1,830 redundant leaks dropped, 374 domains recovered) → **0 residual axis leaks**.
- **BUG-150** — 2 approved canonical swaps (computational theory↔agentic architecture, computer networking↔prompt engineering) + 14-label axis decisions (5 domain aliases, 5 discipline aliases, 3 keep-unique, human-factors-engineering KEPT UNIQUE after definition review). Canonical discipline count flat at 61.
- **D2540** — the latest verdict: split "structural correctness" (leaks/unknown/empty — deterministic, SOLVED: 0 leaks) from "semantic correctness" (right label vs definition — LLM/NLI-dependent, UNMEASURED). REJECT full reclassification (~24–28h, regression risk); ADOPT measure-first (repair 1,485 known-broken + NLI/embedding audit + human sample).
- **Track B reclassification** — `pipeline/reclassify_merged_axis.py` re-decides DISCIPLINE ONLY for ~2,343 `discipline='emerging'` FBs (domains preserved — re-classifying domains REGRESSED valid canonicals). Preflight: 8/8 classified, 10.6s/FB, resolution ~25% (2/8). **Critical finding:** the corrected prompt WORKS (produces `data science`, `human factors engineering`, `design theory`, `financial technology`) but these are MISSING from the 61-entry `CANONICAL_DISCIPLINES` → they still map to `emerging`. So reclassification alone resolves only ~25–37%; the majority are BUG-150 label-promotion gaps, not classifier errors.

**Answer:**
1. Is the two-axis discipline-vs-domain model sound, or is there a better decomposition? (Reference ACM CCS 2012's "computing discipline" vs "Applied computing → domain" + cross-cutting node as the canonical pattern.)
2. Is "0 axis leaks" the right success metric, or does it mask granularity/hierarchy/specificity errors (a label that is *technically* correct but *wrongly scoped*, e.g. `Tesla`→`vehicle`)?
3. The `emerging` placeholder (28.3% of FBs) + keep-unique raw labels + closed-loop swap-only promotion (cap 64 discipline / 48 domain) — is this design sound? What breaks first?
4. Is D2540's semantic-vs-structural decomposition + measure-first verdict correct? Where does it go wrong?

---

## §3. QUESTION 2 — IS THE FB OUTPUT READY FOR AGENTIC DEPLOYMENT?

**Context — the real quality numbers:**
- 41.4% PASS / 58.6% QUARANTINE (DeBERTa NLI, threshold 0.10, commit-with-status). QUARANTINE FBs are committed but filtered at retrieval-time.
- 28.3% `emerging` discipline (no canonical discipline yet).
- 1,485 empty raw-discipline (of which 1,174 are emerging-empty-raw → need LLM re-decision).
- 0 axis leaks, 0 unknown labels, 0 empty canonical domains.
- e2e run: convergent FBs pass at 31.1% (19/61), single-source at 27.4% (17/62) — NOT 80% (D2531 corrects D2528).

**Answer:**
1. Is 41.4% PASS / 58.6% QUARANTINE "ready for agentic deployment"? Frame the honest answer: is QUARANTINE = "retrieval-filtered, acceptable" or "quality signal that blocks deployment"?
2. What is the minimum bar for agentic deployment, and which specific fields/FB-classes currently fail it?
3. Does the 58.6% quarantine rate indicate a *verification* problem (NLI too strict / evidence too weak) or a *generation* problem (S2/S4 quality)? How would you disambiguate?
4. Is the emerging (28.3%) + empty-raw (18.6%) backlog a deployment blocker or a recoverable backlog? Give the priority order.

---

## §4. QUESTION 3 — BOTTLENECK IMPROVEMENT

**Context — the measured bottlenecks:**
- **S4 classification:** ~7–12s/FB. OMLX is **serialized** (single model in VRAM; concurrency benchmark 1/2/3 workers = flat 43s/41s/42s → no speedup, D2366/X9). `thinking_budget=256` = 1.8× (D2366/X8, gated on accuracy). Batch mode = 2× (D2532). Full reclassification of 7,995 ≈ 24–28h sequential.
- **S2 extraction:** bounded by the 30B-MoE decode ceiling (~50 tok/s, D2459); ~100 FBs/hr; more workers DEGRADE the 128-expert MoE.
- **Delegate harness:** `delegate()` to Qwen models fails (BUG-220); direct one-shot works but is not batched/streamed.

**Answer:**
1. What is the single highest-leverage bottleneck fix? (Consider: model swap for S4, prompt compaction, batching strategy, embedding/NLI caching, speculative decoding, offloading classification to a cheaper model with gpt-oss only on disagreement.)
2. Is the gpt-oss-20b (classifier) vs Qwen3-Coder-30B (generator) split optimal, or is there a faster local classifier with acceptable quality?
3. Is OMLX serialization a hard ceiling, or can model offload/quantization (e.g. Q4 vs Q8) recover throughput?
4. Where would YOU spend the next 20 engineer-hours for the most throughput gain?

---

## §5. QUESTION 5 — EVALUATE THE TOP-CRITICAL-PRIORITY PLAN (is it the right way, or is there better?)

**The plan under evaluation (D2540 "measure-first" + this session's top priorities), in execution order:**

1. **311-row deterministic repair** — `discipline_raw = discipline`, `taxonomy_match_method='exact'` for the 311 canonical-empty-raw FBs (no LLM, seconds, behind C13 backup + integrity gate).
2. **Track B reclassification** — re-decide DISCIPLINE ONLY for 1,174 emerging-empty-raw FBs (`reclassify_merged_axis.py --apply --batch`), ~3.5h; harvest raw labels for BUG-150 promotion.
3. **Two-tier semantic audit** — (a) bge-m3 embedding-outlier detection (flag FBs far from their label centroid), then (b) DeBERTa-v3 NLI entailment on the flagged set, then (c) human review of the residue.
4. **Formalize the 105 canonical labels** as OWL/SKOS → SHACL constraint shapes (disjointness `discipline ⊓ domain ⊑ ⊥` + allowed-label closure) — a declarative, deterministic cross-contamination guard.
5. **Sample-size decision** for human review: n≈367 (±5% @95% CI) vs n≈941 (±3%) vs flag-and-review-all (no sampling, since the pre-filter is cheap).
6. **Post-apply sweep** — re-run `bug197_kind_swap` to route domain-topic raw labels to the domain axis.
7. **Close BUG-217** (checkpoint sync: add `taxonomy_match_method` + recompute `manifest_hash`).

**Deliberately REJECTED:** full 4-field reclassification of all 7,995 FBs (~24–28h sequential, regression risk on 6,510 clean FBs, does not remove LLM dependency or the need for axiom checks).

**Answer:**
1. Is this the right ORDER? Where would you reorder, parallelize, or skip?
2. Is "measure-first, reclassify-only-if-error>5%" the right decision rule, or is there a better trigger (per-axis/per-label thresholds, cost-asymmetric, etc.)?
3. Is the split — deterministic repair (step 1) + LLM redecision (step 2) — right, or should BOTH go through the LLM / BOTH be deterministic?
4. Would YOU do a full reclassification instead? If yes, under what conditions and at what cost threshold?
5. Give your own revised priority list (numbered) if you disagree.

## §6. QUESTION 4 — MARKET RESEARCH (tools / stack / LLMs / repos)

**Answer with concrete, name-able recommendations (model + repo + why):**
1. **Ontology constraint validation:** SHACL (pySHACL) vs OWL2/DL reasoners (HermiT/ELK/owlready2) — which is right for a 105-label flat taxonomy with a disjointness + closure requirement (NOT full subsumption reasoning)?
2. **Label-correctness audit:** NLI entailment (DeBERTa-v3) vs embedding-outlier detection (bge-m3 centroids) vs hierarchical text classification (HiAGM/HiMatch/HiTIN) — which combination is cheapest at highest recall, given bge-m3 embeddings already exist locally?
3. **Taxonomy alignment / alias-swap decisions:** OAEI/LogMap/AML vs SKOS exactMatch/closeMatch vs a lightweight matcher — what to adopt?
4. **RAG evaluation:** RAGAS/ragas vs the existing golden-set recall@k/MRR harness — what's missing?
5. **LLM lineup:** is gpt-oss-20b-Q8 + Qwen3-Coder-30B-A3B + DeBERTa-v3-large + bge-m3 the right local stack for classification+verification+retrieval, or is there a strictly better local model (Qwen3.8-27B for classification? ModernBERT-nli? a reranker)?

---

## §7. DELIVERABLE FORMAT (required)

For EACH of the 5 questions return:
1. **Verdict** (one line: sound / partially-sound / unsound, with confidence).
2. **Top findings** (numbered, severity-tagged 🔴/🟠/🟡, each with the evidence or repo file that would confirm it).
3. **GO / NO-GO** for agentic deployment (Q2 only) + the single highest-leverage next action (Q3 only).
4. **Market-research picks** (Q4 only) — a ranked "adopt / evaluate / skip" table.
5. **Plan critique** (Q5 only) — your revised priority order if you disagree, or "plan is correct" with justification.

Keep it under ~2,500 words. Prefer concrete, falsifiable claims over generalities.
