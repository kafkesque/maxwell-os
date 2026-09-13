# LLM ROUNDTABLE HANDOFF + MASTER PROMPT — S2/S4/S5 Forensic Audit & Production-Readiness Adjudication

> **Prepared:** 2026-09-13 · **Repo:** `github.com/kafkesque/maxwell-os` · **Branch:** `main`
> **Reference commit:** `6e295d4` (`git checkout 6e295d4` to reproduce the exact audited revision)
> **Auditors:** Claude, GPT, and one additional frontier model of your choice — each acting as an S-tier senior RAG engineer + knowledge architect + software engineer, working **independently**. Reconcile afterwards; do NOT let any auditor see another's answer first (shared-bias collusion — the same reason R5 mandates generator ≠ verifier).
> **Mode:** READ-ONLY forensic + market research. Do NOT mutate `knowledge pipeline/maxwell.db`, `config/*.yaml`, or any governance file.
> **Output:** `governance/ROUNDTABLE_FINDINGS_<model>_S2S4S5_FORENSIC_2026-09-13.md`

---

## ⛔ MASTER PROMPT (binding instructions to the auditor)

You are an **S-tier senior RAG engineer, knowledge architect, and software engineer** retained to perform a **forensic audit and production-readiness adjudication** of Maxwell OS v3.0's classification/extraction/verification stack (S2 → S4 → S5).

**Approach rules (non-negotiable):**

1. **Do NOT assume. Verify.** Every claim you make must be traceable to the repo. Ground truth sources (in priority order): `config/decisions.yaml` (machine source of truth, 591 decisions), `DECISION-LOG.md`, `governance/buglog.md`, `MASTER-TASK-REGISTER.md`, the actual code in `pipeline/` and `scripts/`, and the data in `knowledge pipeline/maxwell.db` + `governance/joint_vote_production_checkpoint.jsonl`. Where I give you a number, re-derive it from the repo before quoting it. Where a number is stale, flag the drift explicitly.
2. **Do not rubber-stamp.** Flag anything unsound, unverifiable, or "pass-by-accident". The project has a history of self-reported metrics that turned out to be wrong (e.g. "87.5% depth accuracy" → measured 75%; "82% confirmed principle" → corrected to 61%). Distrust every headline metric in this doc until you reproduce it.
3. **Do not run in circles.** The project has burned ~35h wall on a vote whose *outcome* is now clear. If you see a loop (re-training → same data-limit → re-training), say so and name the exit condition.
4. **Stay grounded and pragmatic.** Prefer existing, peer-reviewed, off-the-shelf solutions (with model + repo + paper) over bespoke re-invention. If a bespoke path is unavoidable, justify it against the off-the-shelf alternative.
5. **Give an ultimate, constructive solution** — not a menu. End with a single recommended end-state architecture and the minimum ordered steps to reach it, with the token/money cost of each step called out.

---

## 0. What Maxwell OS is (mission, one paragraph)

A **sovereign, local-first ($0 marginal cost) knowledge pipeline**: books/EPUB/PDF → convert → chunk → prefilter → embed/cluster → **S2 convergent extraction** → **S4 merge/classify** → **S5 verify (NLI)** → **S6 commit** (Stage 3 removed, D2120/D2198). The product is a set of **Foundation Blocks (FBs)** — transferable, ontologically-classified, evidence-verified principles consumed by an agentic RAG layer. The entire thesis is: *clean, correctly-classified, noise-free, retrievable knowledge, generated and verified entirely on local hardware, with no vendor lock-in.*

The mission fails silently if (a) noise/garbage objects are stored among principles, or (b) the ontology labels (content_type / depth / discipline / domain) are wrong — because then retrieval returns confidently-misclassified junk and the downstream agent trusts it.

---

## 1. THE NEW REVELATION (why this audit exists now)

The project ran a **full 7,966-row reliable-pair vote** (DeepSeek-v4-pro + Qwen3.8-27B, cross-family unanimity, abstain on disagreement — D2610/D2612) over `content_type` (7-way) and `depth` (4-way, principle-only). Its result **contradicts the stored database** and re-opens the question of whether S2/S4/S5 are production-ready at all.

The headline: **the production DB says 7,966/7,995 (99.6%) of stored objects are `principle`. The reliable-pair vote says only 4,920/7,966 (61.8%) actually are.** ~38% of what the system stores as "principles" are not principles — they are noise, process templates/instances, tool instructions, or unresolved.

---

## 2. VERIFIED STATE (re-derive before trusting)

### 2.1 The database — `knowledge pipeline/maxwell.db` (`fbs`, 7,995 rows)

| Axis | Stored distribution (gpt-oss / Qwen3-Coder silver) |
|---|---|
| `content_type` | **principle 7,966 (99.6%)** · noise_drop 17 · quarantine 7 · process_template 2 · tool_instruction 1 · process_instance 1 · growth_edge 1 |
| `depth` | domain 6,642 · cross-domain 716 · **specialized 557** · universal 80 |
| `discipline` | `emerging` 759 (9.5%) · empty `discipline_raw` 355 |

### 2.2 The vote — `governance/joint_vote_production_checkpoint.jsonl` (7,966 fb_ids, vote-only, DB untouched)

| Axis | Reliable-pair result |
|---|---|
| `content_type` | **principle 4,920 (61.8%)** · (abstain) 1,681 (21.1%) · **noise_drop 1,037 (13.0%)** · process_template 177 · process_instance 120 · tool_instruction 15 · growth_edge 16 |
| `depth` (among 4,920 principle) | domain 3,113 · cross-domain 733 · universal 22 · **specialized 4** · (abstain) 1,048 |
| `needs_review` | **2,729 / 7,966 (34.3%)** = honest abstain (pair disagreed) · voter_error_rows 0 |

**The discrepancies you must explain:**

1. **content_type:** DB 7,966 principle vs vote 4,920. The vote finds **1,037 noise_drop (13%)**, **177 process_template**, **120 process_instance** that the DB currently stores as `principle`. → **~38% of the "principle" store is not principle.** (Cross-check: BUG-238 measured the true non-principle rate at 12.7–16.6%, not 0.4%.)
2. **depth:** DB `specialized` = 557, but the vote found **4** specialized among 4,920 confirmed principles — a **~139× over-assignment** (consistent with D2576: "gpt-oss over-assigns the rare classes"). DB `universal` = 80 vs vote 22. The rare-class depth labels are systematically wrong.
3. **34.3% abstain** is not a bug — it is the honest epistemic-uncertainty signal. Every automated resolver tried failed (3rd-voter 44.7% = coin-flip BUG-236; bge-m3 tie-break 20% D2614; ModernBERT 27.7% top-1; Snorkel/Dawid-Skene 48.7% false-flag). There is **no automated resolver** for these rows.

### 2.3 The golden training set — `config/golden/stage4_golden_mined.yaml` (1,027 examples)

| Field | Stored |
|---|---|
| `provenance` | **None for all 1,027** (no provenance field populated) |
| `content_type` | **None = 919 (89.5%)** · principle 79 · noise_drop 17 · quarantine 7 · process_template 2 · growth_edge 1 · tool_instruction 1 · process_instance 1 |
| `depth` | domain 820 · cross-domain 137 · **specialized 52** · universal 18 |

**The corruption question (this is central):** D2613 measured the golden set's provenance as **gpt-oss 1,027 / DeepSeek 0 / human 0** — i.e. *every* golden example is unverified teacher silver. The subsequent human/DeepSeek corrections (D2603/D2605 ≈28 rows; D2612 ≈217 content_type rows; D2615's 298-row active-learning sample) have only **partially** re-verified it. And the vote now proves the *teacher* (gpt-oss) mislabels content_type at ~38% and rare-class depth at >10×. Therefore: **a large, currently-unquantified fraction of the 1,027 golden examples carry corrupted silver labels** — 89.5% have no content_type at all, and the depth labels inherit the same rare-class over-assignment (golden `specialized` = 52 vs vote's 4).

**Your job: estimate how many of the 1,027 golden examples are corrupted, and what to do about it — because this golden set is the training/eval target for every downstream classifier.**

### 2.4 The classifiers (S4 students — all data-limited, none production-enabled)

| Classifier | Result | Gate | Verdict |
|---|---|---|---|
| `discipline` (ModernBERT flat 61-way) | macro-F1 **0.20–0.29** | 0.75 | DATA-LIMITED (18/61 disciplines <10 ex) |
| `depth` (ModernBERT 4-way) | macro-F1 **0.48** (silver) / 0.34 clean | 0.85 | annotation-limited |
| `hierarchical` coarse 10-way | top-1 **54.0%**, macro-F1 0.46 | — | coarse head = keeper |
| `student_classifier` held-out | top-1 **27.7%**; cannot hit 90% precision at ANY coverage (best 75%@4%) | 0.70 | flag OFF |

### 2.5 S2 / S4 / S5 — the three stages under audit

- **S2 (extractor, Qwen3-Coder-30B-A3B):** emits name/definition/mechanism/boundary. Known issues: `route` field stale (`route="FB"` on all 2,878 — BUG-148); single-source vs singleton split (D2462); multi-turn decode collapse (DELEGATE-002). **The "everything is principle" inflation originates here and/or S4 — you must locate where.**
- **S4 (classifier/merger, gpt-oss-20b teacher):** the source of the unverified silver labels (BUG-241). Assigns content_type + depth + discipline + domain. **It is the very teacher whose labels the vote just falsified at 38%.**
- **S5 (verifier, DeBERTa-v3-large NLI, threshold 0.10):** **PASS 3,310 / QUARANTINE 4,685 (41.4%/58.6%)**, commit-with-status (D2420). S5 verifies *entailment* (evidence supports the claim), **NOT classification correctness**. A confidently-misclassified object still passes S5 if its text is self-consistent.

---

## 3. MUST-ANSWER QUESTIONS

### Q1 — Forensic: where does the rot enter, and how much is corrupted?

1. Trace the **principle-inflation** (99.6% → 61.8%) to its source: is it S2 over-extracting, S4 over-classifying, or both? Give the concrete stage/prompt/rule responsible.
2. Estimate **how many of the 1,027 golden examples are corrupted** (wrong content_type / depth / discipline / domain) as a consequence of silver-label provenance + the measured teacher error rates. State your method and confidence interval.
3. Quantify the **noise/garbage currently stored among the 7,966 "principles"** (the 1,037 noise_drop + 177 PT + 120 PI + …). Is the DB safe to serve as-is, or is it poisoning retrieval *right now*?
4. Is there **cross-axis contamination** (a label on both discipline and domain, or a domain/discipline conflation like `00631 "strategic thinking"`)? The repo reports 0 axis-leaks — verify, and check whether "0 leaks" masks **wrong-scope/granularity** errors (D2540's semantic-vs-structural split).

### Q2 — Production readiness: are S2, S4, S5 production-ready? (answer each separately)

For **each** of S2, S4, S5: (a) production-ready YES/NO; (b) if NO, the single missing capability; (c) the concrete change that closes it. Then answer the consolidation question: **should S2/S4/S5 be consolidated** (e.g. S4 classification folded into S2's single extraction pass; S5 extended to verify classification, not just entailment), or kept separate? Justify against the pipeline's own stage contract (CONSTITUTION §2) and against R5 (generator ≠ verifier).

### Q3 — Strategy: what to do *before moving forward*, to stop running in circles

1. The project has iterated P4→P5→P6 (classifier retrains) and the vote (35h) with the same conclusion every time: **data-limited, not model-limited.** Is that conclusion correct, and if so, what is the **exit condition** for the loop?
2. Given the mission (sovereign, $0 marginal, clean ontology), what is the **minimum-viable fix order** to make future batches "bulletproof"? Weigh: (a) fix S2/S4 prompt+ontology now; (b) freeze a verified golden core (human-adjudicate 149-core + the 298 active-learning sample) before any further training; (c) retire the gpt-oss teacher in favor of the reliable-pair vote / a fine-tuned local labeler.
3. **Token-waste audit:** which of the currently-planned tasks are wasteful (re-running what's already measured) and should be **cancelled or deferred**?

### Q4 — The 7,000+ objects *now*: clean, or re-derive?

The DB holds 7,995 objects (7,966 labeled principle). The vote says ~38% are mislabeled and 34.3% are unresolved. **Propose the disposition of the existing store:** (a) what can be deterministically repaired (LLM-free), (b) what needs the reliable-pair vote / a fine-tuned labeler, (c) what must go to a human review queue, (d) what should be dropped/quarantined outright. Give an ordered plan with cost (tokens / wall-time / $) and a per-step guard against re-contamination.

### Q5 — Future-proof guarantee

The user demands **no more** of: blindspot, gap, conflict, mismatch, inconsistency, bloat, risk, contamination, leak, bug, drift. For each of those 11 failure modes, name the **single structural invariant** (schema constraint, SHACL shape, contract test, cross-model cross-check, provenance stamp, hold-out guard) that *guarantees* it cannot silently recur — and state which are already present (e.g. R14 stamps, boundary hold-out guard D2609, kind-swap D2519) vs missing.

### Q6 — Market research (peer-reviewed / off-the-shelf)

Research and name concrete solutions (paper + repo + why) for the *specific* problems here:
1. **Label-noise / silver-label correction** at ~38% error — weak supervision (Snorkel), confident learning (cleanlab), Dawid-Skene, LLM-as-judge / committee voting. Which is the best *practical* fit for a fixed 61/43/4-way ontology with a cloud+local model pair?
2. **Fine-grained taxonomy classification** with a long tail (18/61 classes <10 ex) — hierarchical classification (flat vs coarse-to-fine), zero-shot NLI (DeBERTa-v3-large), setfit, modernBERT, or retrieval-augmented classification. Which reaches 0.75+ macro-F1 with the *least* new human label effort?
3. **Knowledge-graph / ontology integrity** — SHACL/OWL disjointness (the repo already plans this, D2546), RDF-star, or a lightweight SQL-level constraint. Is the repo's "SHACL hot-path + OWL periodic" (D2546) the right call, or is there a leaner off-the-shelf validator?
4. **Abstention / selective prediction** for the 34.3% unresolved — conformal prediction, SelectiveNet, Geifman & El-Yaniv, calibration. Which gives the tightest "predict-or-abstain" guarantee for the review queue?
5. For each: **is it more accurate AND cheaper** than the current reliable-pair vote on this corpus? Rank ≤6 models and ≤3 methodologies with rationale and a benchmark plan (temp=0.0, golden A/B, cache-clean).

### Q7 — The ultimate solution (mandatory deliverable)

Give the **single recommended end-state architecture** for Maxwell OS's S2→S4→S5 (and its label-quality loop) that is: (1) accurate, (2) sovereign/free long-term, (3) future-proof against the 11 failure modes, (4) with the minimum ordered steps and explicit token/$ cost to reach it. State plainly whether the gpt-oss teacher should be **retired** in favor of a fine-tuned local labeler, and if so, exactly what verified-data volume gates that retirement. If you believe my current plan is wrong, replace it — do not append to it.

---

## 4. Output contract

Write `governance/ROUNDTABLE_FINDINGS_<model>_S2S4S5_FORENSIC_2026-09-13.md` containing:

1. **Verdicts on Q1–Q7** (agree/disagree + reasoning, each ≤1 page).
2. **Corrections** to any number in §2 you could not reproduce from the repo (state what you found instead).
3. **The ultimate solution** — architecture + ordered steps + cost + the 11-mode invariant table.
4. **Top-5 constructive observations** (things I should fix that no question asked about).

Be concrete. Name files, functions, models, papers. No hand-waving.
