# FORENSIC AUDIT — Menu v6 (D-2814/2815/2816) + Gate A(d) (D-2822) implementation gate

**Date:** 2026-10-05 11:17 +02:00
**Trigger:** Owner approved T4 (ship menu v6 bundle) and T9 (ship Gate A(d)). Per standing rule,
this 11-category audit runs BEFORE any serious implementation commit.
**Scope:** the exact change surface of D-2814 + D-2815 + D-2816 + D-2822 against the live tree.
**Verdict:** **BLOCKED — do not implement yet.** Four findings require resolution first (CF1,
B1/MI2, C1, BL1). Two of them (CF1 slot disambiguation, BL1 abstention token) need an owner
decision; two (B1/MI2, C1) are deterministic re-generation/migration work the assistant can do.

---

## 1. BREAK (breaking changes)

- **B1 — SHACL version pin is STALE and will reject every FB.** `config/taxonomy_shacl.ttl`
  hardcodes `sh:in ( "v5.5" )` on `maxwell:taxonomy_version`, but the live pin is
  `taxonomy_version: v5.6` (config/pipeline_config.yaml lines 10, 206, 799). Wiring pySHACL
  (D-2816) against the existing ttl makes **every** FB stamped v5.6 fail the contract.
- **B2 — `sh:closed true` ordering hazard.** The ttl's `CanonicalDomainShape` /
  `CanonicalDisciplineShape` are `sh:closed true` with `sh:in` lists of 43 domains / 61
  disciplines. If the B&M group (D-2815) is added to the menu WITHOUT regenerating the ttl,
  pySHACL rejects the new menu. Ordering is mandatory: **menu bump → regenerate ttl
  (`scripts/generate_taxonomy_shacl.py`) → bump the version pin → wire enforcement**, all in
  one atomic commit.

## 2. CASCADE

- **C1 — alias_map retirement has 14 consumers.** D-2814 retires `config/alias_map.yaml`
  (999 rules), but `pipeline/schemas.py` (`get_synonym_index`) and 13 scripts consume it:
  `apply_alias_corrections.py`, `demote_disciplines_to_domains.py`, `resolve_domains_emerging.py`,
  `resolve_data_absent_domains.py`, `rederive_kindsafe_domains.py`, `extend_alias_index.py`,
  `consolidate_anchor_ruler.py`, `remap_emerging.py`, `revote_queue_59.py`,
  `build_discipline_domain_vote.py`, `review_aliases.py`, `resolve_emerging_deterministic.py`,
  `apply_enrichment.py`. Retirement must be **shrink-then-remove with consumer migration**, never
  a delete.
- **C2 — "menu v6" name collides with the reverted "v6.0" marker.** D-2814/2815/2816 call the
  target "menu v6", but `governance/TAXONOMY_v6_MIGRATION_20260921.md` records a "v6.0" audit
  marker that was **reverted by D-309** (`meta.menu_repair_20260921_result` = "no-op … version is
  NOT bumped"). `taxonomy_v5.yaml` is at `v5.6`. The new menu needs a non-colliding version string
  (e.g. `v5.7`) or an explicit D-reference, or the provenance layer confuses two different "v6"s.

## 3. DRIFT

- **DR1 — taxonomy_version already drifted ttl(v5.5) vs config(v5.6)** (same root as B1).
- **DR2 — per-axis hash drift already recurred once.** `config/menu_axis_hashes.yaml`
  `composite_hash_frozen_pin` (73597ee2…) ≠ `composite_hash_live` (99e1df82…) — documented
  historical (D-371). MTR 2026-10-03 records the file was ALREADY regenerated once after going
  stale. The menu bump MUST re-run `scripts/menu_axis_hashes.py` atomically with the menu edit,
  or the pins silently stale a second time.

## 4. BLINDSPOT

- **BL1 — TWO abstention tokens: "none" vs "emerging".** `pipeline/closed_menu.py` uses
  `_ABSTENTION_VALUE = "none"` (D-275b/D-277). `config/closed_menu_v5.json` uses `emerging` as the
  first-class catch-all (`meta.catch_all_discipline` / `catch_all_domain`), and the classify prompt
  FORBIDS "emerging" ("the pipeline decides that, not you"). D-2814 says "explicit **none**". The
  27.2% emerging defect (BUG-629) is measured on "emerging"; `emerging_discipline_rate_max 0.35` is
  defined on "emerging". The menu v6 must fix ONE abstention token (and reconcile the drift metric),
  else the emerging-rate gate breaks or silently re-targets.
- **BL2 — anchor re-derivation referee is un-specified.** D-2820 freezes the anchor
  domain/discipline axis until menu v6 lands, but the re-derivation procedure (which post-menu-v6
  artifact, which coder/verifier) is not yet owner-ratified. No blocker to shipping the menu; a
  blocker to the POST-hook re-map.

## 5. GAP

- **G1 — D-2817 (BUG-632 declared-failure count gate) still PROPOSED.** Prerequisite for the
  D-2703 full re-run. Current S4 run has `declared_failed_count 0` so it does NOT block the current
  baseline, but it must land before the re-run.
- **G2 — BUG-630 same-axis fall-through not yet implemented.** `map_to_canonical_with_fallback`
  returns "emerging" for opposite-axis canonicals with no same-axis retry (~45 tokens rescuable,
  zero new labels). In D-2814 scope; not yet coded.

## 6. CONFLICT

- **CF1 (BLOCKER) — D-2815 slot "entrepreneurship" string-collides with the existing DOMAIN.**
  Measured: proposed B&M discipline slots {marketing, management, entrepreneurship}; `entrepreneurship`
  is ALREADY a canonical domain (`config/closed_menu_v5.json` domains, group "Business & Strategy").
  Two independent rails reject it: (a) D-2500 `owl:disjointWith` requires domain/discipline canonicals
  DISJOINT — and D-2816 is about to ENFORCE that disjointness; (b)
  `map_to_canonical_with_fallback`'s opposite-axis guard (BUG-200/D2422) returns "emerging" for a raw
  label canonical on the opposite axis, so a discipline "entrepreneurship" would be **unreachable /
  dead on arrival**. "marketing" vs domain "marketing & communications" and "management" vs
  "project management" are near-collisions (advisory, not exact). **Resolution (recommended):** rename
  the slots to discipline-scoped forms — e.g. JEL M "business administration", "marketing", and
  "entrepreneurship studies" (or drop the third slot and keep 2: marketing + management + business
  administration). Owner decision required.

## 7. BUG

- Live, already-filed: BUG-629 (27.2% emerging, root evidence), BUG-630 (over-blunt cross-axis guard),
  BUG-631 (unenforced max_domains_per_fb), BUG-632 (declared-failure gate). Recently closed: BUG-633/634
  (parser), BUG-637/638/639.
- **New from this audit → file:** BUG-640 (CF1 slot collision), BUG-641 (B1/MI2 stale SHACL v5.5 pin),
  BUG-642 (C1 alias_map 14-consumer retirement cascade), BUG-643 (BL1 dual abstention token).

## 8. HIDDEN FAILURE

- **HF1 — the active S5 re-run has NO usable log capture.** `run_s5_110440.log` is 32 bytes
  ("bash: setsid: command not found") — the `nohup … > $LOG` redirect captured the earlier `setsid`
  error and the real run's stdout went elsewhere/lost. The process (PID 91019) is HEALTHY (checkpoint
  `checkpoint.jsonl` growing: 2900/6591 at 11:17), but if it fails there is no log to diagnose.
  **Monitoring must key on `checkpoint.jsonl` line count, not the log.**
- **HF2 — epoch-split risk (D-2814).** "A mid-run menu edit splits the corpus into two epochs." S4 is
  idle now (only S5 downstream is running), so it is SAFE — but the audit re-asserts: verify S4 idle
  immediately before ANY menu/taxonomy edit, and never while S4 runs.

## 9. ERROR LEAK

- **EL1 — silent "emerging" fall-through on synonym-index removal.** If the alias layer is retired
  before `get_synonym_index` consumers migrate, the index returns nothing and the mapper silently
  falls through to "emerging" (mislabel without a log). D-2814's same-axis fall-through must also
  LOG each recovery for drift measurement (C16: no silent errors).
- **EL2 — opposite-axis guard is a silent mapping loss (BUG-630).** Raw labels force-emerged by the
  guard are not logged; drift measurement can't see them.

## 10. MISMATCH

- **MI1 — TWO hash sources of truth.** `pipeline/closed_menu.py` builds `menu_hash` from
  `config/taxonomy_v5.yaml`; `config/menu_axis_hashes.yaml` hashes `config/closed_menu_v5.json`. They
  can (and have) diverged. The menu bump must update taxonomy_v5.yaml → regenerate closed_menu_v5.json
  → re-run menu_axis_hashes.py, atomically.
- **MI2 — three-way version/label mismatch.** ttl header "43 domains + 61 disciplines (v5.5)" vs live
  menu "44 + 62 (incl. `emerging` catch-all)" vs pipeline_config "v5.6". The 44/62-vs-43/61 delta is
  fully explained by the `emerging` first-class abstention (NOT a real taxonomy drift) — but the
  version string is genuinely stale in the ttl.

## 11. BLOAT

- **BL1 — dirty tree already large.** ~40 tracked + ~45 untracked files modified. menu v6 adds more;
  the commit must bundle with S5/S6, never standalone.
- **BL2 — ~9.7G archivable bloat** catalogued in `governance/FORENSIC_AUDIT_BLOAT_20260929.md` remains
  unarchived.

---

## Ordered resolution plan (post-audit)

1. Owner: adjudicate **CF1** (B&M slot names) and **BL1** (abstention token) — the only two that
   need a human ruling.
2. Assistant (deterministic, no owner input): regenerate taxonomy_shacl.ttl against v5.6/v5.7 (B1/MI2),
   migrate alias_map consumers shrink-then-remove (C1), reconcile abstention token once BL1 ruled.
3. Then (and only then) implement D-2814 → D-2815 → D-2816 as one atomic commit, with R5
   (gemma-4-E4B generator≠verifier) review.
4. Gate A(d) (D-2822) ships after menu v6, decoupled, with nli_calibrate.py re-run against the new
   OR-entail + AND-no-contra semantics.
