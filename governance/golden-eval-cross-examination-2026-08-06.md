# Golden Set Evaluation — Cross-Examination & Pragmatic Verdict (D2205)

**Date:** 2026-08-06
**Subject:** Three LLM evaluations of `config/golden/stage2_fewshot_convergent.yaml` (v3.0, 25 examples)
**Evaluators:** Kimi (`temp/kimi  gold eval2.md`), Qwen (`temp/qwen golden eval2.md`), DeepSeek (`temp/deepseek  golden eval2.md`)
**Method:** Every claim from each evaluator independently re-verified against the actual YAML (structural parse, raw-text grep, verbatim substring checks, source-independence review). No claim accepted on faith.

---

## 1. Evaluator Verdicts

| Evaluator | Verdict | Critical | High | Strengths | Weaknesses |
|-----------|---------|----------|------|-----------|------------|
| **Kimi** | **BROKEN** (mechanically broken, conceptually salvageable) | 4 | 6 | Best structural framing; caught NEG-001 Graham fabrication; caught CONV-003/012/017 verbatim violations; caught CONV-006 schema deviation accurately | Missed CONV-003 fabricated source (a POSITIVE — the worst contamination in the set); missed CONV-012 Russell pseudo-independence; missed CONV-020 Lewis secondary source; rated property coverage PASS despite bimodal distribution; over-rated NEG-001/NEG-002 as CRITICAL |
| **Qwen** | **NEEDS-FIXES** (bordering BROKEN) | 2 | 6 | Best factual-check coverage (CONV-003 fabrication, CONV-012 Russell, CONV-020 Lewis — all unique catches); caught ID gaps; correct severity on NEG routes | 3 FALSE claims: "CONV-006 invalid YAML duplicate keys" (file is valid YAML list), "ra tionale" typos (absent), "mor e"/"T his" typos (absent — those were in the generator's error state, not the final YAML) |
| **DeepSeek** | **NEEDS-FIXES** | 1 | 3 | Caught CONV-007 Parrish secondary-source issue (unique); correct calibration-ratio analysis | Too lenient: only caught NEG-001 of the 4 route contradictions; missed ALL verbatim violations; rated Dimension 9 (hallucination) PASS while Qwen + this audit found a fabricated POSITIVE source; counted 19 positives (actual 18) |

**Consensus:** All three independently converge on "**not calibratable as-is**" — structural negatives broken, missing edge cases. No evaluator rated it READY. This tri-party agreement is itself the strongest signal: the D2204 expansion shipped with fixable but real defects.

---

## 2. Claim-by-Claim Verification (ground truth)

### ✅ CONFIRMED TRUE (17 claims)

| # | Claim | Evaulator(s) | Ground truth |
|---|-------|--------------|--------------|
| 1 | NEG-001..004 use `route: FB` with fully-populated `expected_fb` despite `should_extract: false` | Kimi (4×CRIT), Qwen (4×CRIT), DeepSeek (1×CRIT) | **CONFIRMED — all 4.** NEG-001 "Patient Investment Recovery", NEG-002 "Systems Beat Goals", NEG-003 "Market Disruption…", NEG-004 "Build-Measure-Learn Loop" all `route: FB` + filled fields. Self-contradictory vs NEG-CONV-001..003 (`route: NULL`, empty). Teaches model to emit FBs for rejected clusters. |
| 2 | Meta counts wrong: claims 20 positives / 5 negatives | Kimi, Qwen | **CONFIRMED.** Actual: `is_convergent: 20` (18 should_extract + 2 convergent-but-rejected NEG-CONV-002/003), `should_extract: true = 18`, negatives = **7** (NEG-CONV-001..003 + NEG-001..004). Meta says 20/5. |
| 3 | Meta notes say "6 hard negatives" but only list 4 categories | Qwen | **CONFIRMED.** Notes enumerate 4 categories, claim 6. There are 7 negatives in 4 categories. |
| 4 | Jargon-echo negative MISSING | Kimi, Qwen, DeepSeek | **CONFIRMED.** No example where shared technical vocabulary masks divergent mechanisms. |
| 5 | Boundary-violation negative MISSING | Kimi, Qwen, DeepSeek | **CONFIRMED.** No example where a scoped principle is claimed universal. |
| 6 | CONV-006 `expected_fb` is a list of 2 FBs (schema deviation) | Kimi (accurate), DeepSeek (partly) | **CONFIRMED** — valid YAML list `[FB1, FB2]`; schema defines single object. Deviation is real; **Qwen's "invalid YAML duplicate keys" is FALSE** (raw YAML parses cleanly, verified). |
| 7 | CONV-006 FB1 (Default Inertia) ≈ CONV-020 (Default Stickiness) near-duplicate | Kimi, Qwen | **CONFIRMED.** Same principle (default effects), overlapping sources (Kahneman + Thaler), same organ-donation + retirement-savings evidence. Double-extraction risk. |
| 8 | `evidence_passages` not verbatim | Kimi (3), Qwen (2) | **CONFIRMED — actually 4 violations.** CONV-003 (`[...]` elision), CONV-012 (drops "Reinforcement learning from human feedback"), CONV-013 (**missed by all three** — drops middle clause "revealing more only on demand" from Norman segment), CONV-017 (`...` sentence bridge). Automatable via substring check. |
| 9 | Property distribution bimodal — CONV-001..007 have ZERO optional props; CONV-011..021 have 10-11 | Qwen, DeepSeek | **CONFIRMED.** 0 vs 10-11 per example. Model may learn "early FBs don't need properties". |
| 10 | Domain skew — Business & Strategy overrepresented | Kimi (~60%), Qwen (8+) | **CONFIRMED** (exact: 13/25 business-adjacent ≈ 52%; Kimi slightly overstated, Qwen understated). Visual/AI/UX/Illustration/Computational-Art = 1 each. |
| 11 | CONV-003 source "Finding the Tipping Point — Visual Metaphor in Advertising" likely fabricated | Qwen (HIGH), DeepSeek (WARN) | **CONFIRMED — most severe issue in the set.** No such book exists in advertising/visual-communication literature (real work: McQuarrie & Mick 1999; Phillips & McQuarrie 2004). It is a CONVERGENT POSITIVE: fabricated source contaminates the positive corpus AND the provenance ledger. Kimi missed this. |
| 12 | NEG-001 Graham quote fabricated/misattributed | Kimi (CRIT), Qwen (MED) | **CONFIRMED.** "The intelligent investor is never wrong for long. Even a very bad investment will eventually recover…" contradicts Graham's margin-of-safety / permanent-capital-loss doctrine. Not from *The Intelligent Investor*. |
| 13 | NEG-002 Duhigg segment is paraphrase, not verbatim | Kimi (CRIT) | **CONFIRMED (severity downgraded).** Clear's "You do not rise to the level of your goals…" is real; Duhigg's "Habits are powerful forces…" is a generic paraphrase. Real issue but the platitude lesson survives — HIGH not CRITICAL. |
| 14 | CONV-012 pseudo-independence — Russell in 2 of 3 sources | Qwen (HIGH) | **CONFIRMED.** AIMA (Russell & Norvig) + Human Compatible (Russell) share lead author. Only Christian is truly independent. |
| 15 | CONV-020 Lewis is secondary source describing Kahneman | Qwen (HIGH) | **CONFIRMED.** *The Undoing Project* is a biography of Kahneman/Tversky; Lewis adds no independent evidence. Compounds the CONV-006/020 duplicate issue. |
| 16 | CONV-007 Parrish secondary/synthesis source | DeepSeek | **CONFIRMED (LOW-MED).** *Great Mental Models* is derivative synthesis; BORP still satisfied via Christian/Griffiths + Dixit/Nalebuff. Document, don't remove. |
| 17 | Stray fields + typos: `consequence_2: ''` (CONV-011), `source_book_2: ''` (CONV-015), `opptimization` (CONV-012), `afntifragility` (CONV-014); ID gaps CONV-008..010 | Kimi, Qwen, DeepSeek (partial) | **CONFIRMED all.** Lines 688, 1084, 787, 1039. IDs jump CONV-007 → CONV-011. |

### ❌ CONFIRMED FALSE (3 claims — all Qwen)

| # | Claim | Ground truth |
|---|-------|--------------|
| 1 | "CONV-006 invalid YAML — duplicate keys, parser will error" | **FALSE.** Raw YAML is a proper list (`expected_fb:\n  - is_summary: false …\n  - is_summary: false …`). Parses cleanly (verified via `yaml.safe_load`). Correct framing: Kimi's "schema deviation" (list vs single-object schema). |
| 2 | "`ra tionale` typo in NEG-CONV-002/003" | **FALSE.** Case-insensitive grep of the entire file: zero hits. |
| 3 | "`mor e` / `T his` typos in CONV-006 FB2" | **FALSE.** Zero hits in file. (These appeared in the *generator's* error state, D2204 — never committed to final YAML.) |

### ⚠️ Severity disagreements (arbitrated)

| Dispute | Kimi | Qwen | DeepSeek | **Arbitration** |
|---------|------|------|----------|-----------------|
| NEG-001 fabricated quote | CRITICAL | MED | — | **HIGH.** Negative-set contamination ≠ positive-set poisoning. The rejection lesson survives; source-veracity principle (BORP lineage) is violated. Fix, but don't block everything on it. |
| NEG-002 Duhigg paraphrase | CRITICAL | — | — | **HIGH** (as above). |
| Negative ordering | (n/a) | Current ordering fine | Interleave negatives throughout | **Qwen's view correct.** Negatives already sit in 2 blocks (6-8, 17-20) — sufficient to prevent positional overfitting. DeepSeek's 1:1 interleave is over-engineering for a 25-example set. |
| Ratio 18:7 | Add 2 positives → 20:7 | Same | Acceptable | **Fix the real problem first:** dedupe single-source negatives (NEG-CONV-001 + NEG-001 redundant) → 6 negatives; add 2 missing edge-case negatives → 18:8; then add 2 positives (AI/Visual domains — fixes ratio AND skew simultaneously) → 20:8 = 2.5:1 acceptable for few-shot. |

---

## 3. Evaluator Quality Assessment (meta-verdict)

| Dimension | Kimi | Qwen | DeepSeek |
|-----------|------|------|----------|
| Structural audit | **A** — precise, complete on routes/schema | B+ — complete but 1 false structural claim | C+ — caught only NEG-001 |
| Fact-checking | B — caught Graham/Duhigg, missed CONV-003 | **A** — only evaluator to catch CONV-003 positive fabrication + Russell + Lewis | C — rated hallucination PASS with a fabricated positive in the set |
| Verbatim audit | A- (3/4) | B (2/4) | F (0/4) |
| Distribution analysis | B (missed property bimodality) | **A** | A- |
| Calibration judgment | B+ — right call, right reasons | **A** — best overall call | B — right call, wrong counts |
| False positives | 0 | **3** | 1 (counted 19 positives) |
| **Overall** | Strong structuralist, weak fact-checker | **Strongest overall** (best fact-check, fewest blind spots; 3 false micro-claims) | Most lenient (dangerous — declared hallucination PASS on a contaminated set) |

**Meta-observation:** No single evaluator is sufficient — Kimi caught structural issues Qwen's false-positive noise would drown; Qwen caught factual issues Kimi's structure-first lens missed; DeepSeek's leniency would have let a contaminated set calibrate. **Three-evaluator consensus is required to converge on truth; the pattern mirrors Maxwell OS's own R5 rule (generator ≠ verifier, cross-family verification).** The golden-set eval loop is itself a miniature BORP instance.

---

## 4. Pragmatic Verdict

### On the golden set: **NEEDS-FIXES** (NOT BROKEN)

Kimi's BROKEN is too harsh; DeepSeek's lenient PASS-adjacent read is dangerous. The set is:

- **Positive corpus (CONV-001..007, 011..021): S-tier.** Deep causal mechanisms, specific boundaries, genuine multi-source convergence, excellent property depth in CONV-011..021. This is the competitive asset.
- **Negative block: F-tier.** 4 of 7 negatives structurally teach the wrong behavior (emit FB for rejected cluster). 2 of 6 required edge-case categories missing. 2 negatives have source-veracity problems.
- **Metadata layer: F-tier.** Wrong counts, bimodal property distribution, near-duplicate pairs, 4 verbatim violations, 1 fabricated positive source.

**Consequence:** `calibration_status: needs_review` is correct — **do NOT calibrate S2 on this file as-is.** The defects are all mechanical (structure, counts, verbatim, provenance) — NOT architectural. None requires re-expanding the corpus from scratch.

### On the evaluation process: **sound, with verified value**

- 3 independent evaluators × 10 dimensions × graded verdicts produced ~20 genuine findings, of which **17 verified true, 3 verified false, 2 re-graded**.
- The eval prompt (GOLDEN-EVALUATION-PROMPT.md v2.0) worked: it elicited exactly the dimensions needed (structural, BORP, verbatim, provenance, distribution).
- **Gap in the prompt itself:** none of the three evaluators ran an automated verbatim-substring check (only 2/4 violations found), and none verified sources against external bibliographic reality (only Qwen caught the fabricated book). **v2.1 should mandate:** (a) programmatic substring verification of all evidence_passages, (b) external source-existence verification for every source_book.

---

## 5. Required Fix Pass (pre-calibration gate — aggregated from all three evals + this audit)

### P0 — structural (blocks calibration)
1. **NEG-001..004 → NEG-CONV pattern**: `route: NULL`, empty `expected_fb` fields, keep rationale. (Dedupe: NEG-CONV-001 + NEG-001 are both single-source — keep NEG-CONV-001, fold NEG-001's finance framing into it or keep as second instance.)
2. **CONV-006 schema**: formalize `expected_fb: FB | List[FB]` in `schemas.py` (1:N extraction is a real pipeline capability) — or split into CONV-006A/B. Prefer schema update: 1:N extraction is a documented pipeline feature (meta `one_to_n_extraction`).
3. **CONV-003 source replacement**: swap fabricated "Finding the Tipping Point" for a verifiable source (e.g., McQuarrie & Mick 1999 *Visual Rhetoric in Advertising*; Phillips & McQuarrie 2004 typology). Verify Mostafa citation exists or replace with a checkable paper.
4. **Meta header**: `convergent_positives: 18`, `hard_negatives: 7`, correct notes.
5. **Add NEG-005 (jargon echo) + NEG-006 (boundary violation)** — as designed by all three evals.

### P1 — quality
6. **Repair 4 verbatim violations** (CONV-003, 012, 013, 017) to exact substrings; add a **generator-side assertion** in `expand_golden_v2.py` that every evidence passage is a whitespace-normalized substring of a cluster segment.
7. **CONV-006/020 merge**: replace CONV-020 with a distinct behavioral-economics principle (framing effects, endowment, sunk cost) OR merge into one canonical default-effect FB. Prefer: keep CONV-006 FB1 canonical, replace CONV-020 with **framing effects** (Kahneman/Tversky + Ariely/Lichtenstein — distinct sources).
8. **CONV-012 source fix**: replace one Russell source with an independent AI-safety text (Bostrom *Superintelligence* or Gabriel et al.).
9. **CONV-020 (if kept) / replacement source fix**: no secondary-source authors (drop Lewis pattern).
10. **Property distribution**: backfill 3-4 optional props into CONV-001..007 (start with depth/evidence/jargon/keywords per Qwen's suggestion).
11. **Domain rebalance**: convert 2 business examples to AI/Visual/Interactive domains (also serves ratio fix).
12. **Fix stray fields + typos** (consequence_2, source_book_2, opptimization, afntifragility); renumber CONV-008..010 or document removal.
13. **NEG-001/NEG-002 source segments**: replace with verified excerpts (Graham margin-of-safety chapter; real Duhigg cue-routine-reward prose).

### P2 — process hardening
14. **GOLDEN-EVALUATION-PROMPT.md v2.1**: add mandatory programmatic verbatim check + external source-existence check to Dimension 9.
15. **Add author-overlap + secondary-source detector** to golden-set validation (would have caught CONV-012/020 automatically).
16. **Add route-vs-should_extract consistency validator** to integrity_check.py (new check #18).

---

## 6. Bottom Line

- **The three evals are worth more than the sum of their parts**: 17/20 verified findings, zero dangerous false negatives from the consensus (only individual gaps).
- **Set verdict: NEEDS-FIXES.** Calibration gated on fix pass above (est. 1 working session).
- **Evaluator verdict: Qwen strongest overall, Kimi strongest on structure, DeepSeek most lenient.** None is trusted alone — tri-party verification mirrors Maxwell OS's R5/BORP philosophy.
- **The eval loop worked as designed.** The process (expand → 3-LLM eval → cross-examine → fix → re-eval) is now the permanent golden-set lifecycle. Iterate: fix P0/P1 → re-run eval prompt with 3 LLMs → calibrate → set `calibration_status: calibrated`.
