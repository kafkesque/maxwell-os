# OWNER RULINGS — ROUND 3 (2026-10-08) — DOMAIN / DISCIPLINE AXIS + THE DROP PROPAGATION

Authority: the OWNER's own words, this round (verbatim, reproduced below).
Machine effect: `governance/DOMAIN_RULER_FROZEN_20261008.json`
sha256 `5fcde5619e04fbdaebeb02270ca9a189e13e903ad2cf61318fb75285fed5e22c`
       -> `d867ce5e059ac25d6d71d904cbc481a128599bac8ab3cf880be2071a21c05f4c`
201 rows -> **194 rows**; 1 row changed (R091) + 8 rows removed (declared drops); 22 declared warnings;
byte-identical re-derivation (`--check`); partition EXACT (208 = 194 + 14).

## 1. The owner's verbatim words -> the machine ruling

| Owner wrote (verbatim) | Machine ruling |
|---|---|
| `ok I accpet your recommendations R40,R80,R91` | R040 -> **noise_drop**; R080 -> **noise_drop** (already ratified, D-2711/D-2719); R091 -> **KEEP** (see §3) |
| `R140 drop` | R140 -> **noise_drop**; its round-2 abstention is REMOVED (an abstention for a dropped row is a category error, asserted fail-closed) |
| `BUG 679 those are noise drop` | the RATIFY-3 DROP(13) is **propagated uniformly** (see §2) — no re-litigation of the ratified drop |
| (round 2, still standing) `R005` / `R113` / `R158` | unchanged: primary `data visualization`; primary `engineering practice`; R158 applicability-ranked drop (`design strategy` kept as primary, the intrinsic-applicability question carried in §5) |

## 2. The DROP(13) propagation — BUG-679 FIXED, and the invariant is now a RAIL

The owner-ratified RATIFY-3 DROP(13) (D-2711/D-2719) had reached **4 of 13** rows in the owner-derived
authority; 8 dropped anchors were still LIVE rows with full discipline + domains, contradicting D-2813
("for a noise_drop row depth and discipline do NOT apply"). Consequence: round 2 asked the owner to confirm
axis values for rows the owner had already dropped.

| set | rows |
|---|---|
| already removed before this round | R021 R084 R106 R148 |
| REMOVED this round (the 8 residues) | R012 R026 R034 R082 R140 R180 R182 R200 |
| round-3 addition (owner-accepted) | R040 |
| **declared drops = 14** | R012 R021 R026 R034 R040 R080 R082 R084 R106 R140 R148 R180 R182 R200 |

**Arithmetic, exact and asserted:** `n_anchor_rows == n_ruler_rows + n_noise_drop` -> **208 == 194 + 14**.

Every declared drop must (a) name a real anchor row and (b) carry a soft-quarantine ledger entry, or the run
fails closed. That guard **fired on its first run** (R040 had no entry) — which is why R040 was recorded in
`governance/frontier_audit/noise_drop_quarantine.json` *before* the ruler was re-stamped, together with the
propagation record (13 propagated + 1 addition, ref D-2879). Soft quarantine intact: dropped from the axis
authority, **never deleted** (D-2711).

## 3. R091 "Autopoesis in Design Education" — REINSTATED, with a declared divergence

The owner accepted the recommendation to KEEP it. It has **no domain cell** in the owner sheet, so it cannot
be re-derived — the reinstatement is therefore **data** (`config#reinstated_rows`), never a special case in
code, and the script validates it fail-closed (canonical domains, D150 cap, `primary == domains[0]`,
discipline either on the 64-menu or a declared abstention, real anchor row, not already axis-bearing).

* domains **`[education, design strategy]`**, primary **`education`** (owner-accepted).
* discipline = **declared abstention**. The upstream raw value is `creative education`, which is **off** the
  64-discipline menu; naming a discipline without an owner word would be a generator-synthesized label
  (D-2813). **One optional micro-word from the owner upgrades this** (see §5).
* **DECLARED DIVERGENCE:** the owner's own sheet CELL said `noise drop` for R091; the owner then accepted the
  KEEP recommendation in writing. The later written word governs, and the divergence is recorded here rather
  than silently resolved — an owner-facing sheet and the authority must never quietly disagree.

## 4. BUG-682 — the defect BEHIND BUG-679: the axis had TWO homes (MEASURED, now railed)

| face | divergent cells vs the ruler | drop-residue cells |
|---|---|---|
| `discipline_anchor_rederived_v8_20261007.json` (declared authority, D-2868) | 45 | 23 |
| `ANCHOR_208_CONSOLIDATED_20261007.json` | 47 | 23 |
| **total** | **92** | **46** |

The owner's round-2/round-3 rulings exist **only** in the owner-sheet-derived ruler; the face the pipeline
reads still carries the pre-ruling values. So "what is the domain of anchor Rxxx?" depended on **which file
the reader opened** — an error leak, not a cosmetic drift.

WHY NOTHING SAID SO (four compounding limbs, three fixed this round):

1. **The ladder's axis rail compared the authority with its own copy.** `config/anchor_axis_authority.yaml`
   declares authority = `rederived_v8`, consumer = `ANCHOR_208_CONSOLIDATED` — and CONSOLIDATED is
   **regenerated from** rederived_v8 (`scripts/regenerate_anchor_208_v8.py`, D-2867). The rail is green by
   construction and **cannot fire** on an authority/ruler divergence (BUG-492 class).
   **FIXED:** a new tri-state **cross-face rail** (`--check-faces`) is **wired into the ladder**, with the
   measured, **SHRINK-ONLY** ceiling (92 / 46) declared in `config#faces`: 0 = agree, 2 = declared owner-owed
   (loud, not fatal — the BUG-457 pattern), 1 = **UNDECLARED** propagation failure.
2. **Two writers, one artifact.** `build_domain_ruler.py` derived the ruler from the stale CONSOLIDATED face;
   `apply_owner_domain_review.py` derives it from the pinned owner sheet. A re-run of the first would have
   **silently reverted every owner ruling** (the D-387 anti-REVERT class).
   **FIXED:** retired as a writer — it now **refuses** (rc=1) and names the ONE derivation.
3. **A guard read a column name as a literal.** The D-2870 catch-all guard read `r.get("domain")`; the day the
   declared authority's column changes (the ruler's is `domains`), it would scan **zero** rows and print a green
   line — a control that cannot fire, the worst kind of green. **FIXED:** the column name now comes from the
   declared authority (C12); behaviour on today's declaration is byte-identical.
4. The guard covered the AUTHORITY but not the owner-derived ruler. Now covered transitively: the ruler has
   **0 co-tokens in 194 rows** by construction (BUG-676).

**NEXT (Stage 2 — ONE projection, then the ceiling goes to 0):** project the ruler onto `rederived_v8`
(discipline / domain / primary_domain; the 14 dropped rows cleared on all three axes + stamped
`noise_drop`; the abstained rows stamped `discipline: ""` + `discipline_status: abstained` +
`discipline_source: owner_abstained`), regenerate `ANCHOR_208_CONSOLIDATED` + the five-axis views from it,
**flip the axis registry** so the owner-derived ruler is the DOMAIN-axis authority and every lineage face is a
consumer, then lower `ceiling_divergence` / `ceiling_drop_residue` to **0**. That single projection closes
BUG-682, BUG-680 and BUG-683 together (BUG-683: `apply_owner_domain_rulings_v8.py` is a rival authority
writer whose input contract no longer exists — it would raise `KeyError` and nothing runs it).

## 5. What remains with the OWNER (nothing blocking)

1. **R091 discipline — one optional word.** Either name a canonical discipline from the 64-menu
   (`design thinking` / `systems thinking` / `complex adaptive systems` are the defensible ones for an
   autopoiesis/self-reference principle in design education) **or** confirm the abstention. Until then the
   authority carries the declared abstention — never a synthesized label (D-2813).
2. **R158 primary — carried, not changed.** The owner-agreed primary `design strategy` ranks **8/9** on
   intrinsic applicability for that principle while `graphic design` / `semiotics & communication` rank
   higher. An agreed primary is **not** changed by inference; one word moves it.
3. **BUG-681(b) — the ladder BLOCKER.** `check_encoding_homes --check` is rc=1 (a DRIFT, not the tolerated
   owner-owed rc=2), so `just health` **stops there** and everything below it is invisible in the prefix
   report (BUG-573's exact failure mode). Offender diagnosed with a line number:
   `scripts/remap_referee_v7_28rows.py` **line 69** opens the owner remap CSV with a local
   `encoding="utf-8-sig"` instead of delegating to the ONE declared decode home
   (`scripts/lib/artifact_encoding.py`, D-2644/D-2646). The honest fix needs a **declaration** for that CSV;
   queued as the next critical step rather than improvised.

## 6. Verification (measured, this round)

`apply_owner_domain_review --selftest` = **9 known-answer controls fired** (drop-not-anchor,
drop-without-ledger, abstention-for-drop, **partition-break**, declared-drop-with-upstream-residue,
primary!=domains[0], off-menu-domain, undeclared-sheet-fragment, face-divergence) ·
`--check` = PASS (194 rows, re-derived byte-identically) · `--check-faces` = 92/46 within the declared
ceiling (rc=2, owner-owed) · `check_buglog_coverage` GREEN (596 blocks) · `check_bug_status` GREEN ·
`check_anchor_axis_consistency` GREEN (ceiling 0 holds) · `check_rail_registry` GREEN ·
`check_derivation_homes` GREEN · `check_repo_integrity --worktree` GREEN · `check_commit_frontier` GREEN.

## 7. Independent verification (R5: a DIFFERENT model family — gemma-4-E4B-it-MLX-4bit), and where it DRIFTED

Two independent delegates ran against embedded source (they have no filesystem access, so the excerpts were injected —
the first attempt, which asked them to READ files, returned nothing useful and was discarded rather than counted).

**Code review (adversarial, 6 questions).** Verdict reported as "6 PASS" — but the verdict LABELS were unreliable and are
recorded as such, not as corroboration:

* it marked the ledger guard "FAIL" while its own quoted line proves the guard FIRES ("If a drop exists but has no
  corresponding entry ... it raises") — a labelling error, and the guard's behaviour was independently SEEN empirically
  on its first run (R040 had no entry). Recorded as VERIFIER ERROR.
* it flagged "hardcoded thresholds: D-2711, BUG-679, D150" — REJECTED as a misapplied finding: those are decision ids
  quoted inside error messages (provenance citations), not configurable values; moving them to config would let the code
  cite the WRONG policy with no failure. The C12 rule this round did catch a real instance of the defect it names: the
  D150 cap was declared TWICE (an unread `cap_domains_per_fb` in this config vs the ONE home
  `config/pipeline_config.yaml#max_domains_per_fb` that the applier actually reads) — the rival declaration is REMOVED
  and replaced by a pointer comment (D-2646/D-2649: one derived value, one home).
* it confirmed the scope checks in `build_reinstated` are exhaustive, and that no selftest control is tautological.

**Ontology adjudication (3 rulings, blind-ish).** AGREE on all three (R040 95, R091 90, R158 100) — and it VOLUNTEERED
that the framing pushed it toward agreement ("presenting the rulings as established facts ... biases the verification
toward confirmation"). Its RULING C verdict (confidence 100, "None" as the counterargument, reasoning: "the primary
domain was agreed upon by an owner, so my role is to uphold the consensus, not overturn it") is DEFERENCE, not
verification: recorded as a **verifier-drift signal** and NOT averaged into consensus — exactly the shape the round-2
verifier showed when it anchored on the protected-primary hint.

The two SUBSTANTIVE counterarguments it produced are kept as caveats on the record:
1. **R040** — the drop rests on the item being a case description; if the item's analysis of WHY the souring happens is
   present, it could carry a transferable mechanism. This is why the drop is a SOFT quarantine with `recheck_due`
   2026-11-07 (D-2711): a false drop is reversible by construction, never a deletion.
2. **R091** — the abstention is "a procedural constraint failure, not a conceptual one". Correct, and the design already
   treats it that way: the abstention is DECLARED (config#discipline_abstention), it warns on every run, and the owner
   holds a one-word upgrade (§5.1). No synthesized label was written (D-2813).
