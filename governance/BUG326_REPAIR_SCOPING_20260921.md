# BUG-326 REPAIR SCOPING — 2026-09-21 (read-only; NOTHING WAS APPLIED)

Status: **REPAIR BLOCKED.** The repair plan's target numbers (403 raw→canonical, 147 both-axes, 703
no-domain) **do not reproduce** against the live database. A repair must never be applied to a target set
that cannot be re-derived, so no write was made (0 rows changed).

## What was measured (source: `knowledge pipeline/maxwell.db`, table `fbs`, 7,995 rows, read-only)
| BUG-326 claim | Live measurement | Verdict |
|---|---|---|
| 403 FBs with a raw label that canonicalises | **757** non-canonical `discipline` values — and **all 757 are the single string `emerging`** | claim does not reproduce |
| the same 757 reparable via `config/alias_map.yaml` | **0** alias-map hits | no deterministic mapping exists |
| 354 empty `discipline_raw` | **355** | off by one / stale |
| 147 rows where both axes carry the same label | **65** rows where `discipline` also appears in `domains`; of these, **0** are legal on exactly one axis and **0** are legal on both | claim does not reproduce |
| 703 domain-less rows | **0** rows with an empty/unparseable `domains` field | claim does not reproduce |
| "pipeline never emits X" measurement claim | already retracted in BUG-326 | same defect class |

## Why this matters more than the repair itself
1. **`emerging` is NOT a mis-canonicalised label.** It is the taxonomy's *declared catch-all*
   (`config/taxonomy_v5.yaml` → `meta.catch_all_discipline: emerging`, 61 canonical disciplines + the
   catch-all = the 62-slot closed menu, `menu_hash 73597ee2…`). So the largest single "defect" bucket is not
   a defect at all — it is the catch-all doing its job. A naive "raw→canonical" sweep would have rewritten
   757 legitimate labels.
2. **The residual real gaps are different and smaller**: 355 rows with EMPTY `discipline_raw` (a provenance
   gap: the raw model output was never persisted, so those rows cannot be audited back to their source — an
   F-44 `min_human_share` / C29 provenance concern, not a taxonomy concern), and 65 rows where a discipline
   token also appears among the domains (menu disjointness holds for CANONICAL menus, so these need a
   case-by-case look, not a rule).
3. **This is the third stale-measurement claim in two sessions** (after "assignment missing" and "margins not
   persisted", both already logged as process bugs). The pattern is now explicit: *a measurement claim made by
   an agent is not evidence until it is re-derived from the live store in the same session that acts on it.*
   Standing rule added (see buglog BUG-336).

## Consequence for the plan
- Step 6 ("BUG-326 deterministic repair") is **closed as NOT APPLICABLE**: there is no reproducible
  deterministic repair target. What remains is (a) a provenance backfill question for the 355 empty
  `discipline_raw` rows and (b) the 65 mixed-axis rows — both need an owner decision on intent, not a script.
- No R5 review of a repair script was performed, because there is no valid repair script to review. (The
  gemma-4-E4B R5 channel is in any case flagged degraded — BUG-333.)
- The numbers above come from a READ-ONLY inline query against the live DB (no writes, no `--apply` path
  exists yet); `knowledge pipeline/maxwell.db` mtime was verified unchanged afterwards.
