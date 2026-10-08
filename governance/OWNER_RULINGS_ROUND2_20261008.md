# OWNER RULINGS — ROUND 2 (2026-10-08) — DOMAIN / DISCIPLINE AXIS

Authority: the OWNER's own answers, written by the owner into
`governance/OWNER_CONFIRMATION_SHEET_20261008.csv` (sha256 `8e02e65cc5708d5545b76f326221f98b0dcf06376176eb04f1a78a144f2a6d1b`,
pinned in `config/owner_domain_rulings_20261008.yaml#answers_sheet` and asserted FAIL-CLOSED on every run).
Machine effect: `governance/DOMAIN_RULER_FROZEN_20261008.json`
sha256 `b766ae912401d7da3f5e1bff3c4ddc1515696a11174e0f2adafe0277ea6ed569`
       -> `5fcde5619e04fbdaebeb02270ca9a189e13e903ad2cf61318fb75285fed5e22c`
9 rows changed, 15 declared warnings, byte-identical re-derivation (`--check`).

## 1. The owner's verbatim answers -> the machine ruling

| Rows | Owner answer (verbatim) | Machine ruling |
|---|---|---|
| R006 R059 R127 R140 R146 R165 R183 R202 | `abstain` | `discipline_abstention` -> ruler `discipline: ""` (BUG-676 FIXED) |
| R080 | `noise drop` | already owner-RATIFIED (D-2711/D-2719 RATIFY-3 DROP(13)); no axis in the ruler -> no change |
| R040 R091 | `noise drop` (provisional; owner then: "I don't know the principle name I cant decide") | **HELD for the owner** - evidence + recommendation below |
| R158 | `drop but those domain that the least applicable this principle` | `remove_domains: [editorial & advertising, motion design]` - **applicability-ranked, NOT positional** |
| R005 | `I asked if the primary domain is not engineering practice` | **NO** - high conviction is not available; primary stays `data visualization`, information architecture NOT added |
| R113 | `which of those 3 are the primary domain, the rest if you have high confidence keep as additional` | primary `engineering practice`; `computational science & physics` KEPT; `systems & frameworks` EXCLUDED |
| BUG-667 | `ok approve` | owner approval RECORDED (the t11 authority re-mint under D-2862); no code action |

## 2. R040 / R080 / R091 - the owner asked for the current status first

All three are `content_type = principle` in the live committed store (`knowledge pipeline/maxwell.db`), so
**content type does not discriminate** here. What the owner could not see was the *name*: these three rows are
ABSENT from the review sheet (201/208 - the ruler skipped every row whose domain cell was empty), which is
exactly why the sheet could not be answered. Status, from the store:

| id | name | content_type | extraction_type | discipline (store) | domains (store) | status | epistemic |
|---|---|---|---|---|---|---|---|
| R040 | Commercial Advertising Souring of Artistic Vision | principle | causal_mechanism | media studies | arts & culture | PASS | source-supported |
| R080 | Information Design Community Networks | principle | descriptive_model | information science | digital product, information architecture, design strategy, personal productivity | PASS | source-supported |
| R091 | Autopoesis in Design Education | principle | causal_mechanism | **emerging** (raw `creative education`, OFF-MENU) | design strategy, personal productivity | PASS | source-supported |

**Recommendation (senior RAG / ontology):**
- **R080 - noise_drop CONFIRMED, and it is not even a new ruling**: it is on the owner-RATIFIED RATIFY-3
  DROP(13) list (D-2711/D-2719). Its store axes are a *pre-drop residue*, not truth (BUG-679).
- **R040 - noise_drop (recommended).** It is a NAMED PHENOMENON (an artist's career pivot under commercial
  pressure), i.e. a case description in the same family as two rows the owner already dropped: R084 (a named
  researcher's lab leadership) and R148 (a designer's career development). Its own store `domains_raw`
  (creative industries, artistic practice, cultural criticism) is narrative vocabulary, and its "application"
  is career advice - not a mechanism a practitioner applies to design work. Keep-DROP is class-consistent.
- **R091 - KEEP (recommended, i.e. NOT noise_drop).** It asserts a transferable THEORY-IMPORT mechanism
  (autopoiesis / self-reference) with a prescriptive application ("embed reflective-practice modules"). That is
  a principle, not a description of a case. Its abstention is a **CLASSIFICATION GAP, not noise**: the raw
  discipline `creative education` is not on the 64-discipline menu, and its domain canonicalisation dropped
  `education` (raw list: design education, curriculum design, creative arts education) - and `education`
  (taxonomy: "the design of instructional strategies, academic policy, and learning environments") is the
  single best-fitting domain. Proposed fill if the owner keeps it: domains `[education, design strategy]`,
  primary `education`; discipline = declared abstention OR an owner-named canonical
  (`design thinking` / `systems thinking` / `complex adaptive systems` are the defensible ones).
- **R140 conflict (declared, needs one owner word):** the owner answered `abstain`, but R140 is ALSO on the
  owner-RATIFIED DROP(13) list. Round 2 implements the owner's latest written word (`discipline: ""`) and holds
  the *drop* for the owner - see BUG-679. An abstention is the reversible half; it removes the out-of-menu token
  without deciding the harder disposition.

## 3. R158 "Duality in Design" - the applicability ranking (cap = 7 of 9)

The FB (store): discipline `cultural design`; definition = duality as the tension between opposing forces that
lets a thing manifest as `other`; application names **product, artwork, user experience** and the vocabulary
**light vs dark, motion vs stillness, simplicity vs complexity**; source = *Decoding Design: Understanding and
Using Symbols in Visual Communication*. Test applied: **a domain is applicable only if a practitioner of that
domain could use this principle as guidance**, ranked by directness. Precedence respected: the sheet's
`domains` column is the base and is NEVER overridden by the `oov_domains` candidates, so the two dropped are
drawn from the owner's own added candidates, and the owner-agreed primary (`design strategy`, empty
`owner_review` = agreement) is untouched.

| rank | domain | verdict | why |
|---|---|---|---|
| 1 | graphic design | KEEP (**re-instated**) | contrast/composition IS this FB's core vocabulary; the previous positional cap-drop was mis-ranked |
| 2 | semiotics & communication | KEEP | "signs, symbols, visual rhetoric" - meaning-through-opposition is the mechanism's home; the source book is symbols in visual communication |
| 3 | arts & culture | KEEP | the application names "artwork" |
| 4 | user experience | KEEP | named in the application + "motion vs stillness" |
| 5 | illustration | KEEP | static visual artwork = the FB's own medium |
| 6 | motion design | **DROP** | a time-based sub-modality; "motion vs stillness" is one surface example already carried by UX + graphic design |
| 7 | design systems | keep (base column) | contrast pairs are a design-language concern, but the FB is not a systems construct |
| 8 | design strategy | keep (base column, **primary**) | protected owner-agreed value; weak on intrinsic applicability - flagged, not silently changed |
| 9 | editorial & advertising | **DROP** | a production/channel domain; the FB is neither a publication nor an advertising practice |

## 4. R005 "Graphics Algebra Cross Operator" - can `engineering practice` be primary with high conviction?

**NO.** The item is a construct of a graphics algebra whose sole use is to combine variables so a composite
graphic can be rendered (source: Wilkinson's *Grammar of Graphics*). `data visualization` (taxonomy: "the
graphical representation of quantitative data to facilitate understanding and analysis") is the role it fills;
`engineering practice` ("the application of software architecture, programming languages, and development
methodologies") is at most the implementation meta-domain, never the application role. Independent corroboration:
its own `domains_raw` = data visualization, interactive graphics, scientific visualization (all visualization),
`status = QUARANTINE`, `epistemic_status = speculative`, and its factual NLI check is NEUTRAL/FAIL (0.032) -
so even the item's own support is weak. `information architecture` is also NOT added: it is "the structural
organisation of information for websites and digital interfaces", i.e. a different role from a rendering
operator. **Ruling: primary stays `data visualization`; no domain added.**

## 5. R113 "Traveling Salesman Problem Computational Complexity" - which of the three is primary?

Store: `extraction_type = causal_mechanism`, `status = QUARANTINE`, factual NLI **CONTRA** (0.0002),
`epistemic_status = speculative`, depth `domain`. Taxonomy definitions used as the test:

- **engineering practice - PRIMARY.** Its taxonomy raw includes `Computer Science`; the FB's own application is an
  algorithm-selection decision ("consider the factorial growth and use approximation or heuristic methods"), i.e.
  the role is exercised by the practitioner who builds the solution. It is also the owner's previously ruled
  primary, so no mutation.
- **computational science & physics - KEPT as additional.** Complexity bounds are foundational to scientific
  computing (raw: scientific computing, numerical methods); a genuine second, weaker application role.
- **systems & frameworks - EXCLUDED.** "The theoretical analysis and design of complex interconnected systems"
  is general systems theory; a complexity bound on one problem's solution space is not a systems-theory
  construct. No high confidence -> not assigned (per the owner's own condition).

**Declared divergence (not silently changed):** the live store carries `discipline = operations research` and
domains `[code & computation, education]` for R113, while the ruler's owner-finalized discipline is
`computational theory`. The ruler stands; the store divergence is reported for a future S4 re-derivation.

## 6. Open gates (owner)

1. **BUG-679** - propagate the ratified DROP(13) uniformly, or keep those 8 rows live in the ruler? (Affects
   ruler coverage 201 -> 193 and, with it, whether the owner's own earlier ratification is reflected at all.)
2. **R040 / R091** - accept the recommendations in section 2 (one line each).
3. **R140** - ratified `noise_drop` or the round-2 `abstain`?
4. **R158** - the primary `design strategy` ranks 8/9 on intrinsic applicability; move it (e.g. to
   `graphic design` or `semiotics & communication`)? Needs one owner word - an agreed primary is not changed by
   inference.
