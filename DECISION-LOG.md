# Maxwell OS v3.0 — DECISION LOG (tiered)

> **Updated:** 2026-09-04 | **Machine source of truth:** `config/decisions.yaml` (544 decisions)
> **Archive (full append-only history):** `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md`
>
> **Convention (standing rule):** OPEN/PENDING at the top (most critical first) → ACTIVE in-effect → DONE/CLOSED at the bottom. A decision is "done" only when its `state` is RESOLVED/SUPERSEDED/ARCHIVED/REJECTED.
>
> **Heading convention (D2552):** tier sections are `## 🔴 OPEN / PENDING`, `## 🟢 ACTIVE`, `## ⚪ DONE / CLOSED`. Entries use `| ID | State | Decision |` table rows. Historical `### D#### — Title` / bare `## D####` formats remain as-is (append-only history); NEW entries MUST use the table format. Reconcile `DECISION-LOG.md` ↔ `config/decisions.yaml` via `scripts/recompute_decision_summary.py`.

---

## 🔴 OPEN / PENDING — highest priority first

### New from cross-model adjudication (2026-09-03)
| ID | State | Decision |
|---|---|---|
| D2544 | ✅ DONE | Replace centroid-outlier semantic audit with **k-NN label-disagreement** (Bahri 2020) on the same bge-m3 embeddings. EXECUTED 2026-09-04 (D2557): mean neighbor-label agreement 41.2% over 7,995 FBs. |
| D2546 | PENDING | **SHACL hot-path + OWL periodic** (not OWL-DL everywhere). Formalize 105 canonicals as `sh:disjoint`/`sh:closed`/`sh:in` before Track B. |
| D2547 | PENDING | **Per-label/per-axis cost-weighted thresholds** — retire the global 5% semantic-error rule. Calibration measurement DONE (D2561): 440 labels → `governance/d2547_calibration.json`; remaining = populate per-label thresholds. |
| D2548 | PENDING | **Grammar-constrained decoding pilot** on S4 discipline/domain enums (Outlines/XGrammar) — latency A/B before adoption. |
| D2545 | ✅ DONE | C12 config-first de-hardcoding: `EVIDENCE_CONTAMINATION_RATIO`→`stage5.evidence_contamination_ratio`; circuit-breaker `max(…,25)`→`circuit_breaker_failure_threshold_floor`. Also fixed CONSTITUTION taxonomy drift (35/72→43/61), PII path, MASTERPROMPT golden staleness. |

### Pending from registry
| ID | State | Decision |
|---|---|---|
| D2345 | DRAFT | Single-source non-type second pass (`stage2_extract_nontype.py`). |
| D2399 | DEFERRED | Domain promote/demote — **FROZEN** (`d2399_promotions_frozen: true`); reopen only on full-corpus post-reclass counts. |
| D2462 | PLANNED | Unify single-source + singleton S2 into ONE extractor (2 passes). |
| D2084 | DEFERRED | PI/TI/GE/PT written to jsonl in S4 but never committed to DB (→ BUG-170). Registry has full description. |

### Sparse decisions — thin/empty descriptions in registry (reference links to full text)

`config/decisions.yaml` carries `description: "No description extracted"` for the DEFERRED INF/CLS batch (sync defect) and only a `summary` for D2164-D2166. Full decision text lives in the archived log — full path with line number:

| ID | State | Recovered title | Full path |
|---|---|---|---|
| D2164 | PLANNED | Claim-Level Verification: FActScore-style atomic claim decomposition | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:5725` |
| D2165 | PLANNED | Principle-Recall Benchmark: mandatory evaluation harness | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:5733` |
| D2166 | PLANNED | Semantic Chunking: rolling-window coherence detection (S1.1) | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:5739` |
| D2009 | DEFERRED | Confidence Formula deferred to empirical validation | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3216` |
| D2014 | DEFERRED | Phase 1.5: Modular Architecture | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3305` |
| D2015 | DEFERRED | Layer 2 Orchestration Spec validated, deferred to Phase 2 | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3324` |
| D2016 | DEFERRED | Lifetime License Model adopted | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3340` |
| D2049 | DEFERRED | Layer 2 Orchestration Spec (registered) | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3744` |
| D2050 | DEFERRED | Lifetime License Model (registered) | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3754` |
| D2056 | DEFERRED | Swappable Storage Backend Protocol | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3829` |
| D2057 | DEFERRED | Cross-Platform Memory + Process Protocol | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3836` |
| D2063 | DEFERRED | Hybrid Sync Protocol Stub | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3876` |
| D2064 | DEFERRED | Quality Tier System | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3883` |
| D2065 | DEFERRED | Current Architecture Future-Tax Assessment | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3889` |

---

## 🟢 ACTIVE — in effect (460)

The 460 ACTIVE decisions are canonical rules in force (not "pending work"). **Machine list: `config/decisions.yaml`.** Recent critical ACTIVE decisions:

| ID | Decision |
|---|---|
| D2549 | Local-LLM delegation routing (task-type → model, enforced going forward): data-repair code-review → gemma-4-E4B-it-MLX-4bit (R5); classification → gpt-oss-20b-MXFP4-Q8; code-gen → Qwen3-Coder-30B one-shot; research → shell/curl. |
| D2540 | Measure-first verdict: REJECT full 7,995-FB reclassification; 0 axis leaks = structural proof only; semantic correctness is the unmeasured gap. |
| D2541 | Peer-review adoption + S4 integration (source_text/evidence injection, precision rules, batch 2×, thinking_budget 1.8×). |
| D2542 | Delegation boundary: Qwen3.8 = R5 auditor/2nd review; Qwen3-Coder = single-shot code-gen only; research NOT delegatable. |
| D2543 | Qwen3.8-27B = default research/spec/2nd-review model; invoke via **direct one-shot curl** (BUG-220: `delegate()` broken). |
| D2537 | Ranking fix + raw-label facet (opt-in). |
| D2532/D2533 | BUG-197 reclassification prep + corpus-aware pass-rate opt-in. |

> Full ACTIVE set (455 others) lives in `config/decisions.yaml` — read fresh, do not trust any snapshot.

---

## ⚪ DONE / CLOSED — bottom (62)

**RESOLVED:** D2032, D2351, D2352, D2353, D2355, D2356, D2357, D2358, D2359, D2361, D2544, D2545, D2550, D2551, D2552, D2553, D2554, D2555, D2556, D2557, D2558, D2559, D2560, D2561, D2562, D2563, D2564, D2565, D2566, D2567, D2568
**SUPERSEDED:** D2070, D2080, D2085, D2087, D2091, D2100, D2223, D2224, D2253, D2293, D2294, D2296, D2317, D2318, D2430
**ARCHIVED:** D2000, D2001, D2002, D2034, D2052, D2195, D2196, D2204
**REJECTED:** D2005, D2008, D2010, D2028, D2074, D2221, D2226, D2383

> Full titles/descriptions for all 59 are in `config/decisions.yaml` (state ∈ {RESOLVED, SUPERSEDED, ARCHIVED, REJECTED}).
