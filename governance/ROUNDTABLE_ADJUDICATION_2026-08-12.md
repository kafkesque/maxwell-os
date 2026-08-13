# Roundtable Handoff — Independent Adjudication & Aggregation (2026-08-12)

> **Adjudicator:** goose (AAIF) — senior RAG engineer / knowledge architect
> **Scope:** Kimi (kimii006), Qwen (qwen0005), ChatGPT (chatgpt006) vs. actual repo HEAD (`5c3256c` + uncommitted D2300-D2307)
> **Method:** Every proposition re-verified against `probe_output/stage{2,5}_fbs.jsonl`, `pipeline/stage5_verify.py`, `pipeline/stage4_merge.py`, `pipeline/schema_accessor.py`, `pipeline/book_metadata.py`, `config/pipeline_config.yaml`, `config/golden/stage2_fewshot_convergent.yaml`.
> **Result:** 2 of 3 evaluators are grounded and useful; 1 is ~90% hallucinated. Net signal: architecture is sound, **but the central epistemic claim (convergence = independent sources) is currently false**.

---

## 1. Evaluator reliability verdict

| Evaluator | Grounded? | Verdict |
|-----------|-----------|---------|
| **ChatGPT** | ✅ Yes | **Highest-value.** Only evaluator to find the fatal defect (duplicate-edition false convergence). Architecturally the most sophisticated (claim granularity, versioned truth, source graph). One specific error (config "0.6" — actually 0.1). |
| **Qwen** | ✅ Yes | **Solid on mechanics.** Correct FB list, correct "emerging" + confidence-formula findings. Framing slightly overstated ("mathematical collapse" — it's a design choice, not a bug). |
| **Kimi** | ❌ No | **~90% fabricated.** Task A lists 22 "Cognitive Dissonance" FBs + invented FBs that do not exist in the probe. Its "critical" C1 (confidence/status contradiction) and E1 (schema drift) are artifacts of hallucinated status values. Discard. |

---

## 2. Claim truth table (all verified against code/data)

| # | Claim | Source | Verdict |
|---|-------|--------|---------|
| 1 | Duplicate editions counted as independent sources → false convergence | ChatGPT | ✅ **CONFIRMED + deeper** (3-layer root cause, §3) |
| 2 | `discipline:"emerging"` is a garbage/default class (65%) | All 3 | ✅ **CONFIRMED** (26/40). Intentional escape-hatch (D2138) over-firing. |
| 3 | Confidence = 0.15·mech + 0.75·NLI + 0.10·enrich → 0.25 floor on quarantine | Qwen, ChatGPT | ✅ **CONFIRMED** (design flaw, not math bug) |
| 4 | "Verification paralysis" — 77.5% quarantine, R=0.556 | Qwen | ✅ **CONFIRMED** (9 PASS / 31 QUARANTINE) |
| 5 | ISOR "weak" is dead code (0/40) | Qwen, Kimi | ✅ **CONFIRMED** + root cause (broken author parse) |
| 6 | Config says threshold 0.6 | ChatGPT | ❌ **SPEC WRONG** — config says `0.1`. But stale 0.6/0.8/0.5/0.3 comments ARE present → drift is real. |
| 7 | Stage/model documentation drift | ChatGPT | ✅ **CONFIRMED** (DeBERTa/Phi-4/Gemma/ModernBERT/RoBERTa all in comments) |
| 8 | `evidence_passages` dict/list schema drift | Kimi | ❌ **REJECTED** — `list[str]` end-to-end. |
| 9 | 22 FBs from one concept (cluster splitting) | Kimi | ❌ **REJECTED** — no "Cognitive Dissonance" FBs exist. |
| 10 | Confidence/status contradiction (0.99 + QUARANTINE) | Kimi | ❌ **REJECTED** — those FBs are PASS, not QUARANTINE. |
| 11 | Claim-level granularity missing | ChatGPT | ✅ **Sound architectural gap** (FB-level NLI, max over ≤8 passages) |
| 12 | "Immutable after verification" is wrong for evolving truth | ChatGPT | ✅ **Sound** (needs supersedes/contradicts/version) |
| 13 | Retrieval representation < knowledge representation | ChatGPT | ✅ **Sound** (retrieval still FB/document-oriented) |

---

## 3. THE fatal defect — source identity is broken at 3 layers

ChatGPT found the symptom. Deep audit found the **root cause is three stacked failures**, which is why it's worse than any single evaluator stated:

**Layer 1 — Metadata normalization is inconsistent** (`pipeline/book_metadata.py::compute_source_id`)
`source_id = SHA-256(author|title)`. Same work → different IDs because stage0_5 metadata varies:
- `Safe Withdrawal Rate`: "Pieter Levels|Make Bootstrappers Handbook: Learn to build…" vs "Pieter Levels|Make Bootstrappers Handbook" → **2 IDs** (subtitle presence)
- `Transgenic Artistic Agency`: "Anthony Dunne|…" vs "Anthony Dunne, Fiona Raby|…" → **2 IDs** (co-author)
- `Black Swan`: "…|The Black Swan" vs "…|The Black SwanThe Impact…" → **2 IDs** (title+subtitle concat, missing space)

**Layer 2 — ISOR counts filenames, not canonical IDs** (`pipeline/schema_accessor.py::isor_score`)
`n_sources = len(set(source_books))` where `source_books` are raw filenames. Duplicate editions directly inflate source count even where Layer 1 is fixed.

**Layer 3 — ISOR author extraction is broken** (`_extract_author_surname`)
Expects `"Title — Author"` (em-dash). Corpus uses `"Title (Author) (z-library.sk).md"` (parenthesis). **0/268 source_books use em-dash; 268 use parenthesis.** → function returns the FULL filename as the "surname" → `n_authors == n_sources` always → `author_score = 1.0` always → "weak" rating unreachable. Plus operator-precedence bug: `n_authors>=2 or n_domains>=2 and n_sources>=2` = `n_authors>=2 or (n_domains>=2 and n_sources>=2)`.

**Consequence:** ISOR ("Maxwell's most novel contribution") is presently measuring *file count*, not *independent evidence*. `Data-driven Pipeline Processing` reports `n_authors=23` from 23 filenames. This is a false-convergence amplifier, not a guardrail.

---

## 4. New bugs (append to buglog.md)

### BUG-087 — Duplicate-edition false convergence (source identity broken, 3 layers) 🔴
- **Symptom:** `Safe Withdrawal Rate`, `Transgenic Artistic Agency`, `Black Swan` all `source_diversity:2, is_convergent:true` from two filenames of the SAME work (z-library vs liber3). `is_convergent` is false.
- **Root cause:** (1) metadata normalization inconsistent → same work → 2 canonical IDs; (2) `isor_score` counts raw filenames not canonical IDs; (3) `_extract_author_surname` em-dash heuristic never matches parenthesis corpus.
- **Fix:** D2308 + D2309.
- **Files:** `pipeline/book_metadata.py`, `pipeline/schema_accessor.py`, `pipeline/stage1_5_embed_cluster.py`
- **Source:** Roundtable adjudication — ChatGPT C1/E1, verified.

### BUG-088 — ISOR author extraction heuristic + precedence bug 🟠
- **Symptom:** 0/40 FBs rated "weak"; `n_authors == n_sources` always; author_score pinned at 1.0.
- **Root cause:** `_extract_author_surname` splits on `" — "` (never present); returns full filename. Rating condition has `and`-binds-tighter-than-`or` precedence.
- **Fix:** D2309.
- **Files:** `pipeline/schema_accessor.py`
- **Source:** Roundtable adjudication — Qwen C2 / Kimi C2, root-caused.

---

## 5. New decisions (append to decisions.yaml)

### D2308 — Source identity: work-level canonical identity (fix false convergence) — DATA
Re-normalize author/title before `compute_source_id`: strip subtitles, collapse co-author lists to primary author, normalize title+subtitle concatenation. Add `content_hash` tiebreaker. Redefine `is_convergent` on **distinct canonical works ≥ 2**, not distinct files. Scope: metadata fix (cheaper) before full Work/Edition/File graph (ChatGPT's full proposal is future work, not a prerequisite).

### D2309 — ISOR: metadata-author extraction + canonical source count — VAL
Replace `_extract_author_surname` filename parsing with `resolve_book_metadata()` author lookup. Change `n_sources = len(set(resolve_source_ids(source_books)))`. Fix rating precedence with explicit parentheses. This makes ISOR measure actual independence.

### D2310 — S5 confidence: NLI as gate, not 75% weight — QLT
Make NLI a binary gate; compute confidence from ISOR + mechanism + enrichment. Run NLI per-passage with explicit aggregation (max is opaque). Add human-adjudication path for canonical principles (fix R=0.556 false-quarantine of Progressive Disclosure / Warren Harding / True Cost Accounting).

---

## 6. Golden-set additions (from LLM feedback, cross-checked against existing 73)

**Existing blindspot:** golden set has "false convergence" + "citation echo" negatives, but NOT *bibliographic duplicate-edition*. Also golden `source_books` use `"Title — Author"` (em-dash) while production uses `"Title (Author) (source).md"` (parenthesis) — the golden set does not train on the actual format.

**Highest-value additions (fill blindspot):**
- NEG — `Safe Withdrawal Rate` (live FALSE POSITIVE: currently PASS/is_convergent=true but duplicate-edition)
- NEG — `Transgenic Artistic Agency` (duplicate-edition)

**Useful but map to existing categories (lower marginal value):**
- NEG — `Design Thinking Integration` (tautology), `Disorienting AI Era` (non-falsifiable), `High-stakes Brand Approval` (narrow→general), `Integrated Campaign Approach` (tautology), `Displacement-driven Innovation` (platitude), `Semantic Component Alignment` (circular)

**Positive additions (mostly redundant — `Progressive Disclosure` already in golden):**
- POS — `Degenerate Solution`, `Dadaist Visual-form Experimentation`, `Ethical Responsibility in Graphic Design` (all currently PASS, well-formed)

**⚠️ Scope warning:** `stage2_fewshot_convergent.yaml` is **S2-scoped** (`should_extract`). It does NOT fix S5 false-quarantine (that is D2310 — NLI gate/aggregation). Do not route S5 recall fixes through the S2 golden set.

---

## 7. Prioritized task list (most critical first)

| Rank | Task | Decision | Severity | Effort | Rationale |
|:----:|------|----------|:--------:|:------:|-----------|
| **1** | Fix source identity: metadata normalization + canonical work count | D2308 | 🔴 | 4-6h | Breaks the central `is_convergent` claim; contaminates ISOR + golden labels + DSPy |
| **2** | Fix ISOR: metadata-author + canonical source count + precedence | D2309 | 🔴 | 2-3h | ISOR (novel contribution) currently measures file count |
| **3** | Decouple NLI from confidence + per-passage aggregation + human adjudication | D2310 | 🟠 | 4-8h | Fixes 77.5% quarantine / R=0.556 paralysis |
| **4** | Fix `discipline:"emerging"` over-firing (taxonomy match confidence + rationale; split EMERGING_TRUE/UNCERTAIN) | (BUG-083 extended to discipline) | 🟠 | 4-6h | 65% of FBs land in escape hatch |
| **5** | Add 2 duplicate-edition hard negatives to golden set | — | 🟠 | 1h | Closes the golden blindspot |
| **6** | Purge stale model/threshold comments (0.6/0.8/0.5/0.3; Phi-4/Gemma/ModernBERT) | — | 🟡 | 1h | Model identity is evidence provenance |
| **7** | Freeze per-run manifest (config/model/prompt/taxonomy/threshold hashes) | — | 🟡 | 3-4h | Reproducibility; prevents future drift |
| **8** | Claim-level decomposition for S5 (atomic claim/evidence matrix) | D2285 | 🟠 | 8-12h | Already tracked (C1); ChatGPT confirms |
| **9** | Wire DSPy program into stage2 (GAP-1) | D2302 | 🟠 | 4-6h | Already tracked (N1) |
| **10** | StorageBackend protocol (stage6 SQLite) | D2300 | 🟡 | 3-4h | Last modularity gap (N8) |

> Items 1–5 are NEW from this adjudication. Items 6–10 already exist in the register; re-ranked under the new findings.

---

## 8. Governance dependency updates applied

- `governance/buglog.md` → **BUG-087, BUG-088** appended
- `config/decisions.yaml` → **D2308, D2309, D2310** appended + summary re-synced (285 total / 243 active)
- `governance/aggregated_remaining_tasks.md` → new "ROUNDTABLE ADJUDICATION" critical section
