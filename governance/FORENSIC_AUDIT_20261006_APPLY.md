# Forensic Audit + Apply — taxonomy v7 promotion (2026-10-06)

Scope: pre-apply read-only audit + atomic apply of the D-NEXT-1 / D-2853 / D-2855 / D-2856 /
D-2857 chain. Verdict: apply is functionally CLEAN (partition 0 violations; disjointness 0
undeclared / 0 debt rows). One governance conflict surfaced and resolved; one pre-existing
health rail (BUG-563) remains and is NOT caused by this apply.

## 1. Conflict / superseded decision (FOUND + RESOLVED)
- **D-2853 (rename `research & methodology` → `research practice`) SUPERSEDES D-271a
  ("DECLARED HOMONYM — CHANGE NOTHING").** D-271a was load-bearing: enforced by
  `scripts/audit_taxonomy_disjointness.py` via `config/eval_integrity.yaml::label_axes.known_collisions`
  and documented in `governance/DECISION_D271_IDENTITY_20260917.md`.
- Resolved by: promoting v7 (rename) + deterministic DB relabel + marking the
  `known_collisions` entry `resolved_by: D-2853` (retained for audit-trail; remove after
  S4→S5→S6 rerun confirms no residual debt).

## 2. Blast radius (measured, larger than prior estimate)
- Config/golden live refs remapped: **96** (pipeline_config 3, gold_frozen 91,
  stage2_fewshot_convergent 2).
- DB relabel: **875** `fbs.domains` rows + **1** `taxonomy_counts.label` row
  (`research & methodology` → `research practice`). 0 remaining.
- The `domains` column is NOT FTS/vec-indexed (fbs_fts indexes name/definition/keywords/jargon;
  fbs_ai trigger is AFTER INSERT only) → deterministic UPDATE is index-safe (no desync).

## 3. Applied (atomic sequence, all verified)
1. DB backup: `backup_guardian.sh --tag pre_taxonomy_v7_apply` (integrity ok).
2. Promote `taxonomy_v7.yaml` → live `taxonomy_v5.yaml` (version v7).
3. DB relabel (875 + 1) — deterministic, LLM-free.
4. Config/golden remap (96 refs) — crash-safe writes.
5. `eval_integrity.yaml` known_collisions → `resolved_by: D-2853`.
6. `version.yaml` taxonomy_version `v5.7` → `v7`.
7. `render_closed_menu.py --mint-version 7` → `closed_menu_v7.json` (menu_hash 407f3dd45d9c766a).
8. `menu_axis_groups.yaml` source → `closed_menu_v7.json`.
9. `menu_axis_hashes.py` repointed MENU/source → v7, regenerated: answer_space drift **none**,
   answer_space_hash 6d7c08ded68fbb10.

## 4. Verification
- `validate_taxonomy_partition.py config/taxonomy_v5.yaml` → disciplines=64 domains=43 **violations=0**.
- `audit_taxonomy_disjointness.py` → normalised collisions undeclared **0**, runtime undeclared flags **0**,
  rows on declared debt **0**.

## 5. Health rail (PRE-EXISTING, not this apply)
- `just health` FAILS on **BUG-563** (repo-integrity worktree): 40 dirty paths have no declared home
  (mostly prior-session rederive_v6_* / d2767_ab_* artifacts). This apply ADDS `closed_menu_v7.json`
  + `closed_menu_v7.sha256` + `taxonomy_v7_migration.json` which still need a declared home (plan
  may_touch grant or repo_integrity exclusion) — same BUG-563 class, not a new break.

## 6. Next critical steps (bug / task / decision)
- TASK: declare new v7 artifacts in `governance/session_plan_20260924.yaml` may_touch (or
  `config/repo_integrity.yaml` excluded) → clears BUG-563 for the v7 files; separately triage the
  37 pre-existing dirty paths.
- TASK (D-2857): split S4 in `pipeline/stage4_merged_call.py` — Call A CRIBS enrichment on
  Qwen3-Coder-30B (no menu preamble); Call B classification {discipline,domains} on
  gpt-oss-20b-MXFP4-Q8 (definition-anchored menu). Repoint rederive scripts
  (rederive_anchor_axes_v6.py / rederive_csv_to_decisions.py / rederive_worklist_to_csv.py) from
  `closed_menu_v6.json` → `closed_menu_v7.json` (they now fail-closed on the stale v6 pin).
- TASK: discriminator-first rewrite of remaining 4-way management-cluster domain definitions
  (organizational behavior, business operations) in live taxonomy.
- TASK: rerun S4→S5→S6 for every classified record (menu changed → discipline/domains stale);
  **no S1 rerun** (upstream/independent).
- TASK: relaunch flag-ON A/B (D-2767) with v7 menu + split prompt + root-fixed OMLX client;
  adopt only if kappa ≥ 0.800.
- DECISION: after rerun, remove `eval_integrity.yaml::known_collisions` entry (clears declared_debt).
- BUG: close BUG-630 after the cross-axis guard code is aligned to the v7 MECE/opaque-id partition;
  close BUG-648 after D-2857 split lands; close BUG-658 after no-wedge relaunch; BUG-650 PARTIAL
  (fail-closed guard for frozen-invalid anchors still open).

## 7. S4 rerun answer
YES — rerun S4→S5→S6. The menu (opaque ids, axis-pure raw, renamed canonical, org-theory/BA
discriminators) changed, so stored discipline/domains are stale. The rename itself is already applied
deterministically (875 rows); the rerun re-derives labels against the new closed menu. S1 is upstream
and independent → no S1 rerun.
