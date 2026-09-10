# Forensic Audit — P5 Review Contamination, Golden Purity & Noise Scan
> Date: 2026-09-07 | Auditor: goose | Scope: temp/p5_review_pack.txt (human adjudication), config/golden/stage4_golden_mined.yaml (1027), knowledge pipeline/maxwell.db fbs (7995)
> Artifacts: temp/forensic_merged.json (135 joined rows) · temp/p5_review_audit.csv (per-row audit) · temp/forensic_fixlist.json (29 rows needing repair) · temp/forensic_*.json (intermediate scans)

---

## 1. TL;DR — Red flags

1. **The P5 adjudication file itself introduced domain/discipline contamination.** 29 of 130 adjudicated rows have defects: 18 domain slots contain **discipline names or junk** (psychology ×3, interdisciplinary studies ×5, complex adaptive systems, research methodology, information security, game design, cultural design, 'audio engineering', ',' , glued strings), 2 discipline slots are invalid (**00734 used the *domain* `design strategy` as a discipline**; 00242 has a trailing-comma artifact `interdisciplinary studies,`), 15 rows are backtick-wrapped, and 2 rows have **notes-vs-field internal contradictions** (00242, 00274). Root cause: challenger models propose non-canonical domain values and reviewers copied them through without a canonical filter. **These would corrupt gold_frozen.yaml if not cleaned.**
2. **The silver golden set is syntactically 100 % clean** — 0/1027 non-canonical disciplines, 0 non-canonical domains, no discipline↔domain name collisions. Cross-contamination at the *text* level is minimal (1 exact-name pair, 5 near-dup pairs, only 1 cross-discipline). But 100 % *semantic* purity cannot be certified by any automated check — see §3 for the residual risks that remain.
3. **Your "noise / not-a-real-principle" claim is VALID and undercounts.** Within the 135-row review pack I find **7–10 defensible non-principle rows** (you flagged 5–6). Across the wider golden pool the genre problem is bigger: ~50/1027 (4.9 %) probable non-principle genre (histories-of-fields, community/field descriptions, methodology orientations, book/about self-references), plus ≥4 hard artifacts and 6 duplicate-suffix "(2)" names.
4. **Your scoring is mostly sound but not freeze-ready** — 4 rows are missing entirely, ~10 % of decisions are genuine coin-flips on borderline content (your low confidence is warranted there), and the file's formatting/label-axis errors (§2) are the main blocker, not your semantic judgments (sample verdicts §5).

---

## 2. Domain/discipline contamination in the P5 review

Coverage: txt contains 131 of the 135 rows. **4 rows are absent from the file entirely (first rows of the pack): S4-GOLD-MINED-00003, 00008, 00009, 00018** (Strategic Experimentation Framework, Hierarchical Spatial Organization, Parametric Design System, Form-function Integration in Constructivist Design). 00777 is present and adjudicated (research methodology) — my first parser misread a stray quote.

### 2.1 Invalid disciplines in final_discipline (2)
| row | value | problem |
|---|---|---|
| S4-GOLD-MINED-00734 (Contrast-driven Design Strategy) | `design strategy` | **A canonical DOMAIN used as a DISCIPLINE** (axis error). Challenger consensus was `design psychology`; silver `cultural design`. Needs a real discipline (candidate: visual perception, aesthetics). |
| S4-GOLD-MINED-00242 (Silent Weapons for Quiet Wars) | `interdisciplinary studies,` | Trailing comma + wrapped in backticks (data-entry artifact). Worse: notes say "CONFIRM silver" (= political economy) while the field says interdisciplinary studies — **internal contradiction**. Provenance = anonymous conspiracy document (see §4). |

### 2.2 Invalid values inside final_domains (18 occurrences across 16 rows)
All are **discipline names or junk placed in the domain axis**:
- discipline-in-domain: `interdisciplinary studies` (5×: 00294, 00525, 00932, 00939, 00955), `psychology` (3×: 00066, 00067, 00228), `complex adaptive systems` (00252), `research methodology` (00037), `information security` (00163), `game design` (00963), `cultural design` (01017)
- junk/format: `,` (00242), `audio engineering` (00411, not canonical anywhere), `emerging` (00278 — catch-all discipline mixed into a domain list), glued `media & entertainment,\`arts & culture` (00482), glued `` `digital product`, `` (00864)
Root cause: challenger domain proposals are not constrained to the 43 canonical domains (they freely emit discipline names like psychology/interdisciplinary studies), and the adjudicator copied them.

### 2.3 Formatting defects
- 15 rows with markdown backticks around values (00199, 00242, 00274, 00278, 00314, 00343, 00420, 00482, 00525, 00602, 00606, 00722, 00734, 00795, 00864).
- 4 rows with **no notes** (00199, 00606, 00624, 00864); 00624's notes were overwritten by your annotation and its `confidence` field is broken (`, `).
- Reviewer strings with typos: `claude+guman` (00156), `claude+juman`, `claud+human`, `human, `.

**Bottom line: 29/130 adjudicated rows (22 %) need a mechanical clean-up pass before freeze.** Full list: temp/forensic_fixlist.json.

---

## 3. Forensic check: are the golden samples themselves cross-contaminated?

What was verified (all 1027 golden examples, `stage4_golden_mined.yaml`):
- **Label string purity: 100 %.** 0 non-canonical silver disciplines (61-way), 0 non-canonical domains (43-way), 0 discipline↔domain name collisions in the taxonomy. The pipeline's silver labels never cross the axis.
- **Exact-text duplication: 1 pair.** `Responsible AI Governance Framework` exists twice (00478 depth=domain, domains=[organizational behavior]; 00600 depth=cross-domain, domains=[ai & agents, legal & public policy, organizational behavior]) — same concept mined from two different source FBs (distinct 64-hex ids). Same discipline, but **duplicate concept → count inflation + self-similarity in the eval pool**.
- **Near-duplicate text (name+definition+mechanism, containment ≥0.55): 5 pairs.** 4 are same-discipline (typography optical spacing pair; complex-adaptive-systems chaos pair; computational-geometry golden-ratio pair; systems-thinking pair). 1 is cross-discipline: `Layer Ordering and Z-index Management` [00421 → computer graphics] vs `Layer Stacking and Visibility in Motion Design` [01025 → motion & time] — the D2576 boundary-collapse signature, not textual plagiarism.
- **Semantic purity cannot be "100 % verified"** by any automated method (it is an open-set judgment). Residual risks: (a) the provenance graph is one giant component (book/author disjointness infeasible — already known), so eval/train *source* separation is impossible; (b) concept-level re-mining duplicates exist (see the six "(2)"-suffixed names in §4) and are invisible to string dedup; (c) genre contamination (§4) means many rows share cross-book boilerplate, not text.

**Verdict: the golden set is string-clean and text-distinct, but it is NOT proven semantically pure; the P4/P5 classifier numbers therefore remain upper-bound estimates until a strict, freshly-mined disjoint eval pool exists.**

---

## 4. Garbage & noise among the principles (all-FB scan)

DB: 7,995 FBs total (3,310 PASS / 4,685 QUARANTINE; all content_type='principle').

### 4.1 Hard artifacts found in the golden 1027 (your "garbage" instinct, confirmed)
| row | name | why it is junk |
|---|---|---|
| 00434 | Technical Reviewer Identity | **Extraction artifact from book front matter/acknowledgments** (Shiffman, *The Nature of Code*). Text literally discusses a reviewer's "chicken care, caffeine consumption". Not a principle. |
| 00447 | Sage Publishing Mission and Structure | **Publisher about-page blurb** ("founder retains majority ownership… charitable trust after her passing") mined as a principle. |
| 00242 | Silent Weapons for Quiet Wars | Mined from an **anonymous conspiracy document** (Z-Library). Mechanism: "descriptive model… not a causal mechanism". Provenance/trust red flag regardless of label. |
| 00806 + 5 more | Grounded Theory Methodology (2), Visual Metaphor in Advertising (2), Figure-ground Relationship (2), User-centered Design Process (2), Strategic Relationship Building (2), Nonlinear System Behavior (2) | **"(2)" = dedup-suffix renames**, i.e. the same concept was mined ≥2× from the corpus. Concept-level duplication survived string dedup. |
| 00945 | Angelic Assistance in Creative Work | Non-falsifiable spiritual-belief content ("higher intelligences assist creativity") — genre out-of-scope for a principle library. |

### 4.2 Genre-mismatch signal scan (1027 golden; name+definition+mechanism regex)
| signal | count | example |
|---|---|---|
| self-declared non-causal mechanism ("empirical pattern/not a causal mechanism…") | 156 (15.2 %) | 00278 Stigler's Law of Eponymy; 00091 Math-abstraction pattern |
| history/origin/evolution of a field | 24 | 00972 Semiotic Evolution Through Philosophical Ages; 00693 Cultural Typographic Revolution; 00800 Simultaneity in Media Evolution |
| book/about/self-reference ("this book", "the author", "you will learn") | 20 | 00447 Sage Publishing; 00622 Emergent Properties in Design |
| research-methodology orientation | 15 | 00995 Critical Research and Social Justice; 00806 Grounded Theory Methodology (2); 00976 Field Notes Methodology |
| field/community description | 8 | 00984 Creative Coding Community; 00809 Neural Art Community and Practices |
| biographical/personal-identity | 5 | 00434; 00944 Authorial Identity in Design Practice; 00755 Creative Identity Through Constraint |
| conspiracy/covert-control provenance | 3 | 00242; 00544 Conspiracy Theory Fabrication |
| **any signal (union)** | **215 (20.9 %)** | |
| **conservative probable non-principle genre (history ∪ community ∪ self-ref)** | **50 (4.9 %)** | |

Note: the 156 "non-causal" rows are not all junk — normative design heuristics legitimately self-describe as patterns. The *floor* estimate for genre-out-of-scope content in the golden pool is therefore **≈50 rows (5 %), plausibly up to ~10 %** with a full manual pass; hard extraction artifacts are ≥4 certain + 6 "(2)" duplicates. **Your review-pack finding (~5 in 135 ≈ 4 %) extrapolates to roughly 40–100 rows across the 1027 — consistent with this scan.**

### 4.3 The 135-row review pack specifically (verdict on each of your flags)
| row | your flag | audit verdict |
|---|---|---|
| 00434 Technical Reviewer Identity | "GARBAGE… NOT REAL PRINCIPLE" | **VALID — true extraction artifact**, should be dropped, not labeled. |
| 00624 Feminist Data Visualization | "process instance… vague application of data visualization" | **MOSTLY VALID** — it is a normative heuristic/approach orientation, not a causal principle; "case study" is imprecise, but the noise call holds. |
| 00972 Semiotic Evolution | "historical description" | **VALID** — history of semiotic theory, not a principle. (Label 3/3 → semiotics is genre-correct but the row shouldn't be a principle at all.) |
| 00984 Creative Coding Community | "about collaboration" | **VALID** — field/community description, not a principle. |
| 00995 Critical Research and Social Justice | "woke principle" | **VALID on genre** (research-paradigm description, mined from a methods textbook); "woke" is a political framing, but the content is a methodology orientation, out-of-scope for a principle base. |
| 00278 Stigler's Law | "Not sure if this is a real principle" | **YOUR INSTINCT IS RIGHT** — an empirical regularity about science credit, explicitly "not a causal mechanism". Also: final `cultural studies` is a poor fit (nearest honest label ≈ sociology of science, which doesn't exist in the taxonomy). |
| 00945 Angelic Assistance | (in notes, low confidence) | Non-falsifiable belief content → quarantine candidate. |
| 00242 Silent Weapons | (low confidence) | Provenance red flag (conspiracy doc) → quarantine candidate regardless of label. |

---

## 5. Evaluation of your scoring (temp/p5_review_pack.txt)

Provenance: 105 rows `claude`, 17 `claude+human`, 4 `human`, 4 typo'd reviewer strings. Decision mix: 52 OVERRIDE / 46 ACCEPT / 22 CONFIRM / 2 REJECT / 8 unmarked. Vs the 66 rows with a real 2/3 challenger consensus you agree in 53 (80 %) and disagree in 13 — and most disagreements are **correct rejections of challenger axis errors** (e.g. 00156: consensus `urban planning` is a domain, you correctly chose `sociology`; 00790/00374: keeping `philosophy` over challengers' design-psychology/AI is defensible).

**Quality verdicts on the highest-risk rows (independent read):**
- 00199 Survey Design Complexity → `strategic thinking` (high conf, no notes): **likely WRONG** — both silver and 2/3 consensus say research methodology; survey-design is methodology content. Fix.
- 00726 Internal Voice Critique → `psychology`: **RIGHT** (consensus `design psychology` is challenger design-bias; content has no design context).
- 00506 Design tokens → `systems engineering` (kept silver): **RIGHT**; consensus `design thinking` is off.
- 00862 Japanese Graphic Style / 00971 Perspective framework → `cultural design` kept: **RIGHT** over `visual semiotics`.
- 00606 Variation Decomposition (ANOVA) → kept `operations research`: **DEBATABLE, leans wrong** — content is statistics/research methodology (2/3 consensus), not OR.
- 00602/00440 generative art/music → `generative design`: **fine** (procedural generation, not ML 'generative ai').
- 00239 Modular Grid → `visual perception`: **weak/debatable** (a layout-structure principle; taxonomy gap for graphic-design-as-discipline pushes these to perception).
- 00274 Broad Audience Design: **internal contradiction** — notes argue philosophy, field says `decision making`. Fix.
- 00242 Silent Weapons: **internal contradiction** — notes say CONFIRM political economy, field says `interdisciplinary studies,`. Fix (or drop for provenance).

**Your low confidence is justified in ~8–12 % of rows** — those are genuinely borderline FBs (00807 vague "neural processing", 00945 spiritual, 00434 garbage, 00278 regularity, 00972 history). For the bulk you/Claude made defensible calls. The **blockers to freeze are not semantic — they are the 29-row mechanical/axis defect list in §2 and the 4 missing rows.** Nothing here should be fed to freeze_gold_sets.py until those are resolved.

---

## 6. Recommended next actions (P5 gate)

1. **Repair pass (mechanical):** apply temp/forensic_fixlist.json — strip backticks, fix 00242 & 00734 disciplines, purge the 18 discipline-in-domain values (replace with real domains or drop), repair 00624 confidence/notes, normalize reviewer strings, add missing justification notes to the 4 empty-note rows.
2. **Adjudicate the 4 missing rows** (00003, 00008, 00009, 00018).
3. **Quarantine decision (semantic):** mark 00434, 00447(if in scope), 00242, 00624, 00972, 00984, 00995, 00278, 00945 (+ full genre-signal list in temp/forensic_genre_signals.json) as NON-PRINCIPLE; decide library scope policy for history/methodology/community genres.
4. **Root-cause fix in tooling:** constrain challenger prompts + reviewer UI to the 43 canonical domains and 61 disciplines (reject axis violations), and add a **freeze-time schema validator** (final_discipline ∈ 61 ∪ emerging; final_domains ⊆ 43; no backticks/control chars) inside freeze_gold_sets.py so contamination can never enter gold_frozen.yaml again.
5. **Eval-pool hygiene:** de-duplicate the "(2)" concepts and the Responsible-AI-Governance pair before any strict freeze; the honest D2585 number still requires a fresh book/author-disjoint pool.
6. All 4 of your audit questions answered; artifacts regenerable via: python3 temp/forensic_merge_v3.py && python3 temp/forensic_parse.py (deprecated — v3 is authoritative).
