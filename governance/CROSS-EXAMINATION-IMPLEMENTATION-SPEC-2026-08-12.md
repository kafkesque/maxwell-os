# Cross-Examination Implementation Spec — 2026-08-12
<!-- Authority: Four-LLM cross-examination against live Maxwell OS v3.0 codebase -->
<!-- 68 findings evaluated; 14 verified bugs; 5 P0, 6 P1, 5 P2, 7 REJECTED -->
<!-- Reference: DECISION-LOG.md §D2269–D2281 -->

## §0. Scope

This spec traces to four independent LLM audits cross-examined against the live
`kafkesque/maxwell-os` repository at commit `a533b2e` (2026-08-11):

| Auditor | File | Lines | Precision |
|---------|------|-------|-----------|
| S-Tier RAG Audit | `maxwell_os_audit.md` | 567 | 60% (missed requirements.txt, overstated math) |
| ChatGPT 0003 | `chatgpt0003.md` | 6,494 | 85% (highest precision, 14 verified bugs) |
| Qwen Audit 001 | `qwen audit001.md` | 1,649 | 55% (3 of 6 recommendations retracted) |
| Claude External | `CLAUDE-EXTERNAL-VERDICT-2026-08-11.md` | 135 | 90% (sharpest, narrowest scope) |

Every finding was cross-referenced against:
- Actual file contents at HEAD (`a533b2e`)
- `config/pipeline_config.yaml` (live config)
- `config/model_assignments.yaml` (live agent registry)
- `CONSTITUTION.md` (C1–C28 constraints)
- `governance/buglog.md` (existing bugs)
- `DECISION-LOG.md` (D2000–D2268 decisions)

---

## §1. P0 — Fix Immediately (Blocks T1.1)

### D2269 — Runner 60-min timeout kills S2
- **Bug:** BUG-080.4 — `pipeline/runner.py:284` hardcodes `timeout=3600`. S2 takes 25–40h.
- **Fix:** Add per-stage timeout to `config/pipeline_config.yaml`; S2 = `null` (unlimited).
- **Files:** `pipeline/runner.py`, `config/pipeline_config.yaml`
- **Risk if unfixed:** T1.1 killed mid-extraction → 20h of compute wasted.
- **Source:** ChatGPT F13

### D2270 — Runner docstring entrypoint mismatch
- **Bug:** BUG-080.3 — `python -m pipeline.run` imports `run.py` which doesn't exist.
  Correct command: `python pipeline/runner.py`
- **Fix:** Change docstring in runner.py header.
- **Files:** `pipeline/runner.py`
- **Risk if unfixed:** New developer/clone cannot launch pipeline from docstring.
- **Source:** ChatGPT F1

### D2271 — S5 completeness substitutes semantically different fields
- **Bug:** BUG-080.5 — `has_mechanism = bool(fb.get("mechanism") or fb.get("application"))`
  in `stage5_verify.py:321`. Application ≠ mechanism.
- **Fix:** Schema-version-specific validation. v3: strict mechanism/boundary/consequence.
  v2: legacy substitution allowed (backward compat).
- **Files:** `pipeline/stage5_verify.py`
- **Risk if unfixed:** Enrichment-only FBs get inflated completeness scores → bad FBs
  survive S5 gate.
- **Source:** ChatGPT F8

### D2272 — NLI threshold validation must be fatal
- **Bug:** BUG-080.6 — Invalid NLI thresholds only warn, pipeline continues.
- **Fix:** `raise ValueError` or `sys.exit(1)` for invalid verification config.
- **Files:** `pipeline/stage5_verify.py`, `pipeline/pipeline_paths.py`
- **Risk if unfixed:** Misconfigured verification runs silently → all FBs pass/fail
  regardless of quality.
- **Source:** ChatGPT F11

### D2273 — S5 role naming drift (runner says Gemma, config says Phi-4-mini)
- **Bug:** BUG-080.2 — runner.py:29 says "DeBERTa NLI + Gemma" but config says Phi-4-mini.
  model_assignments.yaml still says gemma for S5_FB_VERIFIER.
- **Fix:** (a) Sync model_assignments.yaml S5_FB_VERIFIER to Phi-4-mini.
  (b) Update runner.py docstring.
- **Files:** `pipeline/runner.py`, `config/model_assignments.yaml`
- **Risk if unfixed:** Agent modifying S5 reads stale docs → wrong model loaded.
- **Source:** ChatGPT F2, Claude External §6.1

---

## §2. P1 — Fix This Week (Unblocks Pipeline Quality)

### D2274 — Add dimension assertion to Ollama embedding path
- **Bug:** BUG-080.7 — MPS path has fail-fast dimension check; Ollama path silently truncates.
- **Fix:** `assert len(emb) >= S15_EMBED_DIM` before `arr[:S15_EMBED_DIM]`.
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Risk:** Theoretical (bge-m3 is stable at 1024d). Defense-in-depth.
- **Source:** Audit1 P0.1 (corrected finding)

### D2275 — Add embedding drop-rate quality gate
- **Bug:** BUG-080.8 — Dropped segments printed but not gated. 5% loss silently accepted.
- **Fix:** `if drop_rate > 0.005: raise RuntimeError(...)` and persist metric to run_meta.
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Risk:** Silent epistemic omission — convergences involving dropped segments never discovered.
- **Source:** ChatGPT F4

### D2276 — Wire Hybrid DSPy S2 to production
- **Gap:** `tools/compare_s2_methods.py` shows Hybrid 0.736 vs Traditional 0.591.
  D2251/D2252 declared hybrid "production." But `stage2_extract.py` runs traditional-only.
- **Fix:** Integrate DSPy gate logic from `tools/compare_s2_methods.py` into
  `stage2_extract.py` runtime path. Gate: if DSPy confidence ≥ 0.7, use hybrid extraction;
  else fall back to traditional.
- **Files:** `pipeline/stage2_extract.py`
- **Impact:** +0.145 quality improvement on own benchmark.
- **Source:** Claude External §3a

### D2277 — Add S4 enrichment field verification to S5
- **Gap:** S4 generates `application`, `failure_mode`, `elaboration`. S5 only verifies
  core claim (definition) against evidence. Enrichment fields are never fact-checked.
- **Fix:** Add optional S5 deep-check for enrichment fields (scored separately from
  core claim verification). Enrichment scores influence reliability but don't fail FB
  outright.
- **Files:** `pipeline/stage5_verify.py`
- **Impact:** Closes most dangerous hallucination gap — plausible-sounding, unverified
  `failure_mode` is exactly the kind of error a user trusts without checking.
- **Source:** Claude External §3b

### D2278 — Runner health check uses stress test, not just model list
- **Gap:** Runner preflight calls `omlx_watchdog.py --pre-stage` which checks
  `/v1/models`. `omlx_call.py` has `stress_test_omlx()` that sends actual completion
  requests — but runner doesn't use it.
- **Fix:** Before S2/S4/S5: model health + actual inference probe + correct model
  loaded + JSON response probe.
- **Files:** `pipeline/runner.py`
- **Source:** ChatGPT F14

### D2279 — S1.5 segment drop rate metric persisted to run_meta
- **Sub-task of D2275:** In addition to quality gate, persist `embedding_input_count`,
  `embedding_success_count`, `embedding_quarantined_count`, `embedding_drop_rate` to
  run_meta.yaml for post-run diagnostics.
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Source:** ChatGPT F4

---

## §3. P2 — Nice to Have (Post-T1.1 Polish)

### D2280 — Replace FAISS IndexFlatIP with HNSW
- **Gap:** IndexFlatIP is O(N×d) per query. HNSW is O(log N) with M=32.
  Practical impact is moderate — graph construction + Louvain, not FAISS search,
  dominates runtime at current scale (~30K segments after pre-filter).
- **Fix:** Replace with `faiss.IndexHNSWFlat(dim, M=32)`.
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Source:** Audit1 P0.2 (confirmed, down-prioritized from P0 to P2)

### D2281 — Tiered BORP per depth
- **Bug:** BORP ≥2 sources drops valuable single-source insights (designer/entrepreneur
  memoirs). Memory #18 flagged.
- **Fix:** Make BORP configurable per depth tier:
  `universal: 3, cross_domain: 2, domain: 1, specialized: 1`
- **Files:** `config/pipeline_config.yaml`
- **Source:** Audit1 P1.4

### Future — Incremental/delta processing layer
- **Gap:** Full re-run required for any new book. D2184 (S0.5 cache invalidation) is
  the only hash-based cache.
- **Design:** Per-stage content-hash checkpoints. Only re-process changed inputs.
- **Source:** Audit1 P1.2

### Future — C12 AST enforcement scan
- **Gap:** No static analysis for hardcoded model names, thresholds, paths.
- **Design:** Ruff plugin or custom AST scanner. Flag `MODEL = "..."` pattern
  unless annotated `# @constant-approved`.
- **Source:** ChatGPT F22

### Future — Cloud leakage hard enforcement
- **Gap:** No `assert_cloud_allowed()` enforcement point. Defense is config convention.
- **Design:** Data classification → provider policy → hard deny if cloud forbidden.
- **Source:** ChatGPT F16

---

## §4. REJECTED — Do NOT Implement

These recommendations from external audits were verified against the codebase
and constitution, and explicitly rejected:

| # | Recommendation | Auditor | Reason for Rejection |
|---|---------------|---------|---------------------|
| R1 | Replace FAISS+SQLite with LanceDB | Qwen | Violates C5 (zero bloat — LanceDB adds Rust runtime + Arrow Flight), C3 (single-vendor project), C4 (vendor lock-in) |
| R2 | Replace subprocess with AsyncIO | Qwen | Qwen itself retracted. Subprocess = OS-level memory fence between heterogeneous models. Critical for PyTorch+MLX coexistence. |
| R3 | Remove outlines (VRAM doubling claim) | Qwen | Qwen itself retracted. outlines uses logit bias masking, not separate model loading. |
| R4 | Replace OMLX with Ollama 0.19 MLX | Audit1 | Ollama 0.19 MLX backend is vaporware (no release). MLX-direct provider already in codebase (`mlx_provider.py`). |
| R5 | Remove post-collection Jaccard scan | Qwen | LSH is probabilistic pre-filter. Jaccard pass is precision guard. At FB scale (hundreds), O(N) is negligible. |
| R6 | json-repair pip package | Audit1 | outlines constrained decoding already prevents malformed JSON. json-repair is another heuristic — worse, not better. |
| R7 | Unify model_assignments + pipeline_config | Audit1 | They serve different purposes (agent roles vs pipeline stages). Fix desync, not merge. |

---

## §5. Implementation Order

```
DIAGNOSTIC PASSES S5 GATE (current)
    │
    ├── P0: D2269–D2273 (≤1 hour)
    │   Fix runner timeout, docstring, S5 field substitution, NLI fatal errors, role naming
    │
    ├── LAUNCH T1.1 (full 750-book run)
    │   Uses fixed runner, verified S4+S5 output from diagnostic
    │
    └── P1: D2274–D2279 (≤8 hours, post-T1.1)
        Dimension assertion, embedding gate, hybrid S2, enrichment verification,
        runner health stress test, drop rate metric
```

---

## §6. Dependency Map

```
D2269 (runner timeout) ──────────────── BLOCKS T1.1 via runner.py
D2271 (S5 field substitution) ──────── SKEWS diagnostic S5 pass rate
D2272 (NLI fatal errors) ───────────── Could silently pass all FBs
D2277 (enrichment verification) ────   Closes S4→S5 hallucination gap
D2276 (hybrid S2) ─────────────────── +0.145 quality improvement
```

---

*Spec compiled from 68 cross-examined findings across 4 independent audits.*
*All findings validated against live code at commit a533b2e.*
*7 recommendations rejected with documented rationale.*

---

## §7. ROUND 2 — 4-LLM Review Cross-Examination (2026-08-12)

### Auditors

| Auditor | File | Lines | Precision | Fabrications |
|---------|------|-------|-----------|-------------|
| ChatGPT | `temp/chatgpt005.md` | 2,579 | **90%** — 15 valid propositions | 1 (references old architecture docs) |
| Claude | `temp/claude001.md` | 69 | **100%** — 7/7 validated | 0 |
| Kimi | `temp/kimii005.md` | 171 | **62%** — 5 valid, 3 wrong | Benchmark claim (≥95% match for Qwen3.5-9B — actual: 0%), DeBERTa "outdated" |
| Qwen | `temp/qwen0004.md` | 168 | **28%** — 2 valid, 4 fabricated | Fake fb_ids, fake benchmark (≥92%), MinHash lock misdiagnosis |

### §7.1 Adopted Propositions (D2282–D2293)

| D# | Proposition | From | Priority | Effort |
|----|------------|------|----------|--------|
| D2282 | **Pipeline manifest** — machine-readable per-run config frozen at launch: git_commit, model per stage, prompt_version, schema_version, taxonomy_version. Embed hash in every checkpoint. | ChatGPT §1, Claude §1 | P0 | 1-2h |
| D2283 | **FB schema split: core vs enrichment** — definition/mechanism/boundary/consequence/evidence = irreducible knowledge object. application/failure_mode/elaboration/jargon/domains/depth/discipline = derived enrichment. Eliminates field substitution (BUG-080.5). | ChatGPT §5, §37 | P0 | 2-3h |
| D2284 | **Source independence scoring (ISOR)** — BORP ≥2 is insufficient. Track author independence, citation-chain independence, and evidence-tradition independence. Two books by same author ≠ corroboration. Two books citing same paper ≠ independent. | ChatGPT §21, Claude §6 | P0 | 4-6h |
| D2285 | **Claim decomposition for S5** — Decompose FB into mechanism/boundary/consequence claims. Verify each against its specific evidence passages before synthesis verdict. Replaces single NLI check against whole FB. | ChatGPT §18, §6 | P1 | 8-12h |
| D2286 | **Golden tiered classification** — GOLD-A (human-adjudicated, indisputable), GOLD-B (expert-agreed, minor ambiguity), CHALLENGE (adversarial/ambiguous). Never let LLM-generated+LLM-approved become GOLD-A. | ChatGPT §14 | P0 | 2h |
| D2287 | **DSPy metric with hard gates** — evidence_invalid → score=0. wrong_route → score=0. false_convergence → score=0. THEN weighted quality. Prevents scalar score hiding catastrophic failure. | ChatGPT §24 | P0 | 2-3h |
| D2288 | **Roundtable inter-rater reliability** — pairwise agreement across 4 reviewers + Fleiss' kappa. Not just ad-hoc ">1.5 spread → escalate." | Claude §7 | P1 | 1h |
| D2289 | **Author-disjoint DSPy splits extended** — add domain-stratified, mechanism-stratified, book-disjoint. No semantic near-duplicate across splits (paraphrase leakage is a real risk for extraction evaluation). | ChatGPT §26 | P1 | 3-4h |
| D2290 | **Taxonomy re-anchoring for AI/agents** — "emerging" absorbs 80.5% because domain_anchors.yaml was built 2026-06-11 for business/design corpus. Diagnostic shows #2 domain is "ai & agents" (22 FBs). Add 3-5 AI/agent-specific anchors. Fix before T1.1. | Claude §1 | P0 | 1h |
| D2291 | **S5 FLAG path audit** — 0/185 FLAGs across a 3-outcome design (PASS/FLAG/QUARANTINE) is suspiciously clean. Verify FLAG threshold condition is reachable (same shape as BUG-076: path wired to never fire). | Claude §2 | P1 | 15min |
| D2292 | **Golden depth expansion** — current: universal=1, specialized=1. Uncalibratable. Build dedicated depth benchmark: 30 universal, 40 cross-domain, 40 domain, 30 specialized, 30 hard negatives. Minimum 170 examples with deliberate minimal lexical clues. | ChatGPT §10 | P1 | 8-16h |
| D2293 | **S5 precision/recall from adjudicated sample** — 72.4% PASS is a gate statistic, not an accuracy estimate. Human-adjudicate 50 PASS + 50 QUARANTINE. Calculate precision(PASS), recall(PASS), false-positive rate, false-negative rate. | ChatGPT §19, Claude §6 | P0 | 4-8h |

### §7.2 Rejected Propositions (Round 2)

| # | Proposition | From | Why Rejected |
|---|------------|------|-------------|
| R8 | Qwen3.5-9B matches/exceeds GPT-OSS for S4 | Kimi, Qwen | Benchmarked: 0% domain agreement, 15/15 FBs → "emerging." Qwen 1.8× slower (410s vs 230s). Fabricated "≥92% match" claims. |
| R9 | Replace DeBERTa FEVER with cross-encoder | Kimi | DeBERTa FEVER passed 90/185 FBs NLI-only fast path. Working well. Don't replace proven component. |
| R10 | Purge PyTorch entirely | Qwen | No MLX DeBERTa alternative. Hybrid MLX+PyTorch is pragmatic. mlx-embeddings for S1.5 already planned (D2274). |
| R11 | Migrate to LanceDB | Kimi, Qwen | Already rejected R4. Violates C5/C3/C4. SQLite + sqlite-vec + FAISS sufficient. |
| R12 | Auto-promote S2 diagnostic FBs to golden | (user question) | Methodologically invalid. Pipeline output cannot be its own ground truth. Golden must come from cross-family annotation of raw pre-S2 clusters. |

### §7.3 Bugs Discovered (Round 2)

| Bug | Description | Status |
|-----|-------------|--------|
| BUG-081 | `evals/golden_cases.json` (52 examples) uses old v2 format — domains as comma-strings not lists, no route/mechanism/boundary/consequence fields, 0 evidence passages. Not used by DSPy but still present in repo as misleading artifact. | 🟡 Migrate or archive |
| BUG-082 | S5 FLAG path may be dead code — 0/185 FLAGs across real diagnostic sample. Same class as BUG-076. Needs grep audit on FLAG threshold condition in `stage5_verify.py`. | 🔴 Investigate |
| BUG-083 | `domain_anchors.yaml` built 2026-06-11 for old corpus; "emerging" absorbs 80.5% of diagnostic. Taxonomy predates current book selection. | 🟠 Fix before T1.1 |
| BUG-084 | `stage2_fewshot_convergent.yaml` has universal=1, specialized=1 — depth classification uncalibratable from goldens. S4 depth classifier validated at 87.5% (7/8) but 8 examples insufficient to lock ontology. | 🟠 Expand |
| BUG-085 | `hybrid_s2_extract()` exists only in `tools/compare_s2_methods.py` (benchmark harness), zero references in `pipeline/stage2_extract.py`. D2251 declared hybrid production but code is not wired. | 🔴 Wire before T1.1 |

### §7.4 Constructive Observations

1. **"emerging" at 80.5% is the single most actionable finding.** Re-anchoring the taxonomy with AI/agent domains costs 1 hour and changes the shape of everything downstream. Don't run T1.1 on 750 books with a catch-all absorbing 80%.

2. **Golden examples must be cross-family annotated, not pipeline-promoted.** The correct path: S1.5 diagnostic clusters (already computed, free) → Kimi/ChatGPT/Claude annotation (NOT Qwen, NOT GPT-OSS) → 2+ agreement → golden candidates → human adjudication → merge. This costs cluster annotation compute plus human review, not pipeline reruns.

3. **The 51 quarantine FBs are the most valuable diagnostic artifact** — not the 134 PASS. Each quarantine is a real extraction that S5 rejected. Human review of WHY (false negative vs legitimate rejection) calibrates both S5 thresholds and DSPy negative examples.

4. **Schema split is the highest-leverage architectural change.** Currently boundary/application and consequence/failure_mode are treated as interchangeable (BUG-080.5). Splitting core from enrichment eliminates an entire class of completeness-gaming bugs.

5. **Model swapping is a distraction.** The four reviews converged on: contracts > calibration > models. The pipeline works at 72.4% S5 pass with current models. Fix the contracts, then optimize.

### §7.5 DSPy Recalibration Assessment

| Question | Answer |
|----------|--------|
| Is DSPy trained? | Yes — MIPROv2 on 73 golden examples (D2248) |
| Is hybrid production? | Yes — decided (D2251), 0.736 avg, 5/6 negative rejection, 0.845 positive fidelity |
| Is it wired? | **No** — `hybrid_s2_extract()` only in benchmark harness |
| Does it need recalibration? | Yes — demo selection bias (all design-domain), 3 false-negative clusters |
| Is recalibration blocking? | No — T-007b-v2 scheduled as non-blocking overnight task |
| What's the next DSPy action? | After golden expansion (D2292), re-run MIPROv2 with 4 demos and expanded goldens |
| Is DSPy safe for production? | Yes as convergence gate only — traditional extraction retains positive fidelity. Hybrid architecture prevents DSPy errors from degrading extraction quality. |

---

## §8. AGGREGATED TASK REGISTER (Critical Path)

### P0 — Must Complete Before T1.1 (750-Book Run)

| # | D# | Task | Effort | Blocks |
|---|-----|------|--------|--------|
| 1 | D2290 | Re-anchor taxonomy for AI/agents domain (fix 80.5% "emerging") | 1h | S4 classification quality |
| 2 | D2269 | Fix runner 60-min timeout (per-stage configurable, S2=unlimited) | 10min | T1.1 via runner.py |
| 3 | D2282 | Pipeline manifest — freeze per-run config, embed in checkpoints | 1-2h | Audit trail |
| 4 | D2283 | FB schema split: core vs enrichment (fix BUG-080.5) | 2-3h | S5 completeness accuracy |
| 5 | D2284 | Source independence scoring (ISOR) — author/citation aware | 4-6h | Epistemic quality |
| 6 | D2286 | Golden tiered classification (GOLD-A/B/CHALLENGE) | 2h | DSPy training safety |
| 7 | D2287 | DSPy metric with hard gates (evidence→0, route→0, THEN quality) | 2-3h | DSPy optimization safety |
| 8 | D2293 | Human-adjudicate 100 FBs (50 PASS + 50 QUARANTINE) | 4-8h | S5 calibration |
| 9 | D2271 | S5 v3 schema strict validation (no field substitution) | 30min | S5 accuracy |
| 10 | D2276 | Wire hybrid_s2_extract() into stage2_extract.py | 4-8h | +0.145 S2 quality |
| 11 | BUG-085 | Hybrid DSPy wiring — same as D2276, redundant | — | S2 production |

### P1 — Complete Within Week of T1.1

| # | D# | Task | Effort |
|---|-----|------|--------|
| 12 | D2285 | Claim decomposition for S5 verification | 8-12h |
| 13 | D2292 | Golden depth expansion (170+ examples) | 8-16h |
| 14 | D2288 | Roundtable inter-rater reliability (Fleiss' kappa) | 1h |
| 15 | D2289 | Author-disjoint DSPy splits extended | 3-4h |
| 16 | D2291 | S5 FLAG path audit (verify reachable) | 15min |
| 17 | D2277 | S4 enrichment field verification in S5 | 2h |
| 18 | D2272 | NLI threshold validation fatal (not warn) | 5min |
| 19 | D2273 | S5 role naming sync across config files | 5min |
| 20 | D2270 | Runner docstring entrypoint fix | 1min |

### P2 — Post-T1.1 Polish

| # | D# | Task | Effort |
|---|-----|------|--------|
| 21 | D2274 | Ollama embedding path dimension assertion | 1h |
| 22 | D2275 | Embedding drop-rate quality gate | 1h |
| 23 | D2278 | Runner health check uses stress test | 2h |
| 24 | D2279 | S1.5 drop rate metrics persisted | 1h |
| 25 | D2280 | FAISS IndexFlatIP → HNSW | 2h |
| 26 | D2281 | Tiered BORP per depth | 2h |

### Rejected

| # | Task | Why |
|---|------|-----|
| — | Swap S4 classifier to Qwen3.5-9B | 0% domain agreement in benchmark |
| — | Replace DeBERTa FEVER | Working at 90/185 NLI-only passes |
| — | Purge PyTorch | No MLX DeBERTa alternative |
| — | Migrate to LanceDB | Violates C3/C4/C5 |
| — | Auto-promote diagnostic FBs to golden | Methodologically invalid (circularity) |

---

*Round 2 cross-examination: 2026-08-12. 4 LLM auditors, 23 validated propositions, 5 bugs discovered.*
*Aggregated task register: 11 P0, 9 P1, 6 P2, 5 rejected.*
