# D2191 — Golden Set Validation (v2 — Post-Fix, 2026-08-06 10:20)

> **Status:** ✅ ALL 4 FIXES APPLIED | **Examples:** 9 (7 positive, 2 negative)
> **Decision:** D2191, D2191a | **File:** config/golden/stage2_fewshot_convergent.yaml
> **Pipeline gate:** READY FOR S2 FULL RUN

---

## FIXES APPLIED (D2191a)

| # | Fix | Before | After |
|---|-----|--------|-------|
| 1 | YAML duplicate keys | 3 pairs `is_convergent`/`should_extract` per example | 1 pair each — clean YAML |
| 2 | 1:N extraction example | 0 examples with 2+ FBs | CONV-006: "Explore-Exploit Exploration Bonus" + "Loss-Aversion Endowment Gap" from 3 books |
| 3 | STEM domain example | 0 STEM examples | CONV-007: "Keynesian Recursive Expectation" (economics/game theory, 3 books, real cluster_90 data) |
| 4 | NEG-CONV-002 rationale | Missing Collins context | Added NOTE explaining "First Who" IS a real principle, but EXCERPTS lack mechanism |

## POST-FIX QUALITY SCORES

| ID | Name | Books | Cross-Source | Mechanism | Boundary | Consequence |
|----|------|-------|-------------|-----------|----------|-------------|
| CONV-001 | Asymmetric Dominance Decoy | 3 | A | A | A | A |
| CONV-002 | Implementation Intention | 2 | A | A | A | A |
| CONV-003 | Metaphor Complexity Inverted-U | 2 | A | A | A | B+ |
| CONV-004 | Similarity-Weighted Social Proof | 2 | B+ | A- | B+ | B+ |
| CONV-005 | Value-First Demonstration | 2 | B+ | B | B | A- |
| **CONV-006** | **Explore-Exploit + Endowment Gap** | **3** | **A** | **A** | **A** | **A** |
| **CONV-007** | **Keynesian Recursive Expectation** | **3** | **A** | **A** | **A** | **A** |
| NEG-CONV-001 | Anchoring (single-source reject) | 1 | — | — | — | — |
| NEG-CONV-002 | People Are Important (platitude) | 2 | — | — | — | — |

## DOMAIN COVERAGE (post-expansion)

| Domain | Before | After |
|--------|--------|-------|
| pricing | 1 | 1 |
| behavioral_change | 1 | 1 |
| advertising | 1 | 1 |
| persuasion | 1 | 1 |
| marketing | 1 | 1 |
| **economics** | **0** | **2** ✨ |
| business | 1 | 1 |
| **TOTAL** | **7** | **9** |

## 1:N EXTRACTION READINESS

| Capability | Before | After |
|-----------|--------|-------|
| Single-FB extraction | 5 examples | 6 examples (CONV-001–005, 007) |
| Multi-FB extraction (1:N) | 0 examples | 1 example (CONV-006: 2 FBs) |
| NULL rejection | 2 examples | 2 examples (unchanged) |

CONV-006 models the EXACT format the LLM must use for 1:N: `expected_fb` as a **YAML list** of FB dicts. The `format_golden_fewshot()` function in stage2_extract.py already handles list-format expected_fb (line 592+), so no code changes needed.

## FINAL VERDICT

| Check | Status |
|-------|--------|
| YAML parses cleanly | ✅ |
| No duplicate keys | ✅ (9 pairs for 9 examples) |
| All FBs have mechanism/boundary/consequence | ✅ |
| All evidence passages exist | ✅ |
| 1:N extraction modeled | ✅ CONV-006 |
| STEM domain covered | ✅ CONV-007 (economics) |
| Negative examples correct | ✅ |
| Domain diversity | ✅ 7 domains, 17 unique sources |
| Golden loader works | ✅ `load_golden_parity()` samples correctly |

**GATE: ✅ PASS — Golden set is ready for S2 full run (2,634 convergent clusters).**
