# P5 Review Repair + Freeze-Readiness Audit (Addendum)
> Date: 2026-09-07 (second pass) · Working files: temp/p5_review_pack.txt (repaired), temp/p5_human_adjudication.jsonl (NEW, contract-valid), temp/p5_domain_fix_log.json, temp/p5_review_audit.csv, temp/gold_frozen_test.yaml (dry-run)
> Predecessor: governance/forensic_audit_2026-09-07.md

---

## 1. Status of requested fixes

**All 135 rows are now adjudicated, and both label axes are contract-clean:**

| check | before | after |
|---|---|---|
| rows adjudicated | 130–131 | **135/135** (added 00003, 00008, 00009, 00018 + repaired 00777 parse) |
| invalid `final_discipline` | 2 | **0** (user fixed 00242 + 00734) |
| invalid `final_domain` values | 18 | **0** |
| backtick-wrapped | 15 | **0** (74 bytes of backticks removed) |
| glued strings | ~8 | **0** (incl. `"media & entertainment,`arts & culture"`, `` `digital product`, ``, `" final_domains"` stray-space keys ×3, unbalanced `["science & research]`) |
| stray-quote-before-key corruption | 4 rows (00777, 00009, 00282, 00625) | **0** (quote repositioned) |
| notes-vs-field contradictions | 2 (00242, 00274) | still present — **flagged for your decision**, see §4 |

**File repairs applied to temp/p5_review_pack.txt** (backup: temp/p5_review_pack.txt.bak):
1. Removed all stray backticks (values were markdown-wrapped).
2. De-glued: split `media & entertainment,arts & culture`; unwrapped `` `digital product`, ``; repaired `" final_domains"` (3×) and `" final_` key spacing; balanced `["science & research],`.
3. Repositioned 4 stray quotes that had swallowed a field name's opening quote (`, "\nfinal_domains"` → `, \n"final_domains"` etc.).

**New artifact: `temp/p5_human_adjudication.jsonl`** — 135 line-delimited records in exactly the shape `freeze_gold_sets.py --adjudication` consumes (`example_id`, `final_discipline`, `final_domains`, plus reviewer/confidence/notes). Verified end-to-end with a dry-run freeze (below).

---

## 2. Cross-contamination after fixes — exact residual & how resolved

0 invalid values remain on either axis. During the repair, 11 non-canonical domain entries were resolved (log: temp/p5_domain_fix_log.json). **These were the contamination you asked about — exact ids:**

| example_id | contaminated value | what it was | resolution |
|---|---|---|---|
| S4-GOLD-MINED-00003 | `creative process` | discipline placed in domain slot | dropped (no canonical domain equivalent) |
| S4-GOLD-MINED-00009 | `generative design` | discipline placed in domain slot | → `creative technology` (notes: design+computation intersection) |
| S4-GOLD-MINED-00037 | `research methodology` | discipline (near-typo of domain) | → `research & methodology` |
| S4-GOLD-MINED-00066 | `psychology` | discipline in domain slot | → `social sciences` |
| S4-GOLD-MINED-00067 | `psychology` | discipline in domain slot | → `social sciences` |
| S4-GOLD-MINED-00163 | `information security` | discipline in domain slot | dropped (no canonical security domain) |
| S4-GOLD-MINED-00228 | `psychology` | discipline in domain slot | → `social sciences` |
| S4-GOLD-MINED-00242 | `emerging`, `privacy & surveillance` | catch-all mix + discipline in domain slot | dropped; kept `legal & public policy` (row also in quarantine list, §4) |
| S4-GOLD-MINED-00278 | `emerging` | catch-all mixed into domain list | dropped; kept `research & methodology` |
| S4-GOLD-MINED-00411 | `audio engineering` | non-canonical anywhere | dropped |
| S4-GOLD-MINED-00864 | `digital product,` | glued trailing comma | → `digital product` |

**Remaining semantic inconsistencies requiring YOUR decision (not auto-fixed):**
- **00242 Silent Weapons for Quiet Wars**: `final_discipline` now reads `psychology` but notes say "CONFIRM silver" (= political economy). Mined from an anonymous conspiracy document → my recommendation is **quarantine, not relabel**.
- **00274 Broad Audience Design Principle**: `final_discipline` = `decision making` but notes argue philosophy (design-ethics alias) — decide one.
- 00067's domain list still carries `design strategy`/`user experience` for a trauma-cognition FB (canonical but semantically odd) — your call.

---

## 3. Audit of the 892 golden examples OUTSIDE the review pack

- **Label canonicality: 100% clean** — 0/892 non-canonical silver disciplines or domains.
- **Never flagged for review**: tiers are `cleanlab_only` 539 + `neither` 353; **0 rows** with p_mislabel ≥ 0.9 (the 3-LF label model considers them label-safe — but that says nothing about genre quality).
- **Genre/noise signals live mostly OUTSIDE the review pack** (the pack was selected by label suspicion, not content genre):
  - self-declared non-causal mechanisms: **140** rows (e.g. descriptive models/empirical patterns)
  - history/origin-of-field: **19** · book/about self-reference: **17** · methodology orientation: **13** · field/community: **4** · biographical: **4** · conspiracy/covert provenance: **2**
  - **6 duplicate-suffix "(2)" names** (00096, 00130, 00357, 00649, 00806, 00928) and the exact-duplicate `Responsible AI Governance Framework` pair (00478/00600) are all outside the review pack.
- **Per-class scarcity**: 7 disciplines have <5 examples in this subset (theoretical physics 2, game design 3, …). A 61-way per-class eval cannot be built from the current reviewed set alone (only 44/61 classes have ≥1 reviewed example; 32/61 have ≥2; 17 classes have none).

---

## 4. Freeze dry-run (adjudication applied, SOFT mode)

`freeze_gold_sets.py --size 400 --adjudication temp/p5_human_adjudication.jsonl --allow-soft` → GOLD-A 281 / GOLD-B 58 / CHALLENGE 61 / TRAIN_POOL 627 (same structural result as before — adjudication overrides applied only where rows land in a tier).

**The decisive gap:** of the 400 frozen rows, only **64 are human-reviewed** (CHALLENGE 12/61 = 20 %, GOLD-B 10/58 = 17 %, GOLD-A 42/281 = 15 %). Freezing now would evaluate the classifier against **~83 % machine labels**, not human gold.

**Additional leakage observed inside the frozen protocol:** 5 eval↔train text-overlap pairs ≥ 0.5 containment (e.g. `Visual Hierarchy Through Asymmetric Balance`↔`Visual Hierarchy Through Contrast…`; `Situational Analysis…`↔`Grounded Theory Methodology (2)`), plus the duplicate-concept rows and the known giant provenance component.

---

## 4b. Ontological audit of master classifications (2026-09-07, second pass)
- **Level A — axis/taxonomy validity (100 % checkable): 0 violations across all 1027 effective labels** (discipline ∈ 61∪emerging, domains ⊆ 43, depth ∈ 4-way; no cross-axis name use; no `emerging` mixed into concrete lists).
- **Level B — discipline↔domain↔depth coherence:** 134 rare discipline–domain pairs (33 in master, 101 in unreviewed 818 — mostly benign scatter, none structurally impossible); **2 depth-coherence flags in master**: S4-GOLD-MINED-00008 (`domain` but domains span 4 groups → likely `cross-domain`) and S4-GOLD-MINED-00440 (`specialized` but 3 domain groups). 14 depth flags in the unreviewed set.
- **Level C — semantic content (only a model/human can judge): gemma-4-E4B (independent family) verifier returned OK 20/20 on the riskiest rows — but this result is NOT trustworthy evidence**: the same verifier failed the NOTAPRINCIPLE test on 3 known noise rows (00434 bio artifact, 00242 conspiracy text, 00984 community description). ⇒ Semantic 100 % validity is **not machine-certifiable with the current local verifier**; the 12-row human spot-check (temp/phase1_spotcheck_sample.csv) is the arbiter for provenance/gold promotion.

## 4c. DeepSeek frontier double-check of the 74 phase-1 rows (2026-09-07)
- Method: independent verifier via `custom_deepseek` provider (frontier, unquantized) judging final_discipline / final_domains / final_depth from def+mech text only (R5: different family from the Qwen3.8 labeler).
- Coverage: DeepSeek returned verdicts on 66/74 rows (8 rows never reached it due to payload defects: 00065, 00198, 00210, 00357, 00649, 00740, 00928, 01013).
- Result: ~55/66 (83 %) OK on all three axes. Flags raised (advisory, need human glance — several are debatable):
  - discipline CHANGE suggestions: 00087 (vs software engineering), 00184 (vs cognitive science/visual perception), 00422 (vs cognitive science), 00509 (vs psychology), 00882 (vs systems/software engineering), 00199-analog rows.
  - domains PARTIAL: 00547, 00686 (both carried `data visualization` incoherently; already cleaned in master).
  - NOTAPRINCIPLE: 00418 (contradicted by a second DeepSeek pass = model noise), 00972-analog history rows.
- Verifier reliability caveats observed: DeepSeek made 2 factually wrong notes ("computational theory/health & medicine not valid disciplines" — they ARE canonical) and contradicted itself on 00418 ⇒ treat frontier verdicts as **prioritisation signals, not proof**; humans remain the arbiter.
- ⇒ **The 74 are NOT certified 100 % valid.** Deterministic axes: yes (0 invalid). Semantic: ~83 % clean per frontier pass, ~10–15 % flagged/debatable, 8 rows unverified.

## 5. Senior-engineer recommendation (training material vs freeze readiness)

### Do we have training material?
**Yes — for training.** 3,310 PASS FBs + the 1,027-example golden pool (silver labels 100 % string-canonical, P4 label-model corrections applied to 59) are a legitimate ModernBERT fine-tune corpus. **No — not yet for a defensible frozen GOLD evaluation**, for four reasons:

1. **Human review coverage (blocker).** 135/1027 (13 %) reviewed; only ~16 % of the 400 frozen rows are human-adjudicated; 17/61 classes have zero reviewed examples. Any frozen CHALLENGE/GOLD-B today is mostly silver + label-model output, so the resulting macro-F1 would not be a human-grounded number.
2. **Quarantine policy undecided (blocker).** Hard artifacts (00434 reviewer bio, 00447 publisher about-page, 00242 conspiracy source) and ~50 genre-out-of-scope rows (histories, methodology orientations, community descriptions) are still inside the pool and can land in any tier.
3. **Leakage is bounded but real.** 5 eval↔train text pairs + duplicate concepts + single giant provenance component ⇒ the honest claim is "upper-bound estimate," not clean ΔF1.
4. **Estimator rigor.** Current ΔF1 (+0.0494) is single-seed; observed seed swing ±0.02–0.04 ⇒ needs multi-seed CI before it is decision-grade.

### Pragmatic & rigorous path (recommended order)

**Phase 1 — close the review gap (highest leverage, ~1 focused pass).**
Review a second tranche aimed at the **17 uncovered + 12 singleton classes** (≈40–60 rows from the outside-892 with strongest label-model/domain signals). Target: every class ≥ 2 human-reviewed examples ⇒ enables a truthful per-class eval. Meanwhile keep ALL 135 current rows as the core.

**Phase 2 — quarantine + genre policy.**
Decide scope: are history/methodology/community FBs in or out? Quarantine the 4 hard artifacts + 00242 (conspiracy). Apply via the existing quarantine mechanism, not deletion (C6/R-D410). Consequence: pool shrinks ~5 % — fine for training; essential for gold.

**Phase 3 — freeze protocol v1 (rigorous).**
- Restrict **CHALLENGE/GOLD-B to human-reviewed rows only**; GOLD-A + TRAIN_POOL may carry silver/label-model labels (training does not need gold purity).
- Add a **freeze-time validator** to freeze_gold_sets.py: reject any example whose adjudicated discipline ∉ 61∪emerging or domains ⊄ 43; reject backticks/control chars. (Prevents this whole class of contamination from recurring.)
- Multi-seed retrain (3–5 seeds) on the frozen split → report mean±CI macro-F1; then sha256 the frozen YAML into DECISION-LOG and treat as immutable.

**Phase 4 — honest evaluation framing.**
Report per-class macro-F1 on covered classes + group-level (9 discipline groups) as secondary; document that strict book/author-disjoint eval requires a fresh mining pass from excluded books (separate workstream).

### Bottom line
Mechanical contamination: **fixed and contract-verified** (0/0 invalid, 135/135 adjudicated, jsonl ready). Freeze mechanics: **work**. Freeze decision: **not yet** — close review coverage + quarantine + add the validator first; then the frozen number will mean something. Estimated effort: 1–2 focused sessions for Phases 1–3; Phase 4 is a standing process improvement.
