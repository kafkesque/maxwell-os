# Forensic Audit — D-NEXT-1 implementation (2026-10-06)

Scope: pre-implementation read-only audit + post-build verification of the D-NEXT-1 / D-2855 / D-2856
implementation. Verdict: **no break / cascade / drift / blindspot / gap / conflict / hidden failure /
error leak / mismatch / bloat introduced.** Three decisions minted; taxonomy_v7 built MECE-clean.

## 1. Break / cascade
- v7 is a NEW artifact (`config/taxonomy_v7.yaml`); the live `config/taxonomy_v5.yaml` is UNTOUCHED until the
  atomic apply. Nothing downstream can break from a file it does not read.
- The only canonical RENAME (`research & methodology` → `research practice`, ruled by D-2853) is scoped to the
  DOMAIN axis and will cascade into anchors/golden that reference the old label — that remap is the apply step,
  not done here, so no partial cascade.

## 2. Drift
- String-as-identity drift is eliminated at the source: every entry now carries a stable opaque `id`
  (`disc-NNN`/`dom-NNN`). Display labels can be renamed without remap drift (D-2855).
- golden_max_examples ambiguity RESOLVED: line 290 = `stage2.golden_max_examples: 5`, line 408 =
  `stage4.golden_max_examples: 7` — two DIFFERENT stages, no conflict.

## 3. Blindspot / gap
- NEW GAP (carried into apply): the 4-way management cluster still needs the discriminator-first rewrite in the
  LIVE file (v7 carries the org-theory/BA differentia already; organizational-behavior/business-operations
  domain definitions are not yet discriminator-rewritten).

## 4. Conflict / superseded
- No governance contradiction. bug_status.json OPEN 161 / CLOSED 261 / 422 is internally consistent with
  buglog.md. BUG-654 (CLOSED/superseded by 655), 655/656/657 RESOLVED, 630/648/650/658 OPEN.
- Decisions D-2852/2853/2854 RATIFIED; D-2855/2856/2857 minted this turn (registry now 987 records).

## 5. Bug / hidden failure / error leak / mismatch / bloat
- Measurement (validator): v5 debt = 107 missing ids + 178 MECE violations + 202 duplicate-raw + 1 canonical
  collision. v7 after build = **0 violations**.
- BUG-648 (menu bloat ~5k tokens/call) is addressed by D-2857 (prompt split), NOT by the v7 build itself; it
  stays OPEN until the split lands.

## 6. Next critical steps (in order)
1. **APPLY v7 atomically**: backup `taxonomy_v5.yaml` (backup_guardian.sh) → promote `taxonomy_v7.yaml` →
   bump `config/version.yaml` taxonomy_version `v5.7` → `v7` → `render_closed_menu.py --mint-version 7` →
   re-pin `config/menu_axis_hashes.yaml` (menu_axis_hashes.py) → `just health`.
2. **REMAP references** to the renamed canonical `research & methodology` → `research practice` and to stable
   ids where anchors/golden cite raw labels that moved axis (178 partition resolutions).
3. **Land D-2857 prompt split** (Call A enrichment / Call B classification) in `stage4_merged_call.py`.
4. **Rerun S4→S5→S6** (menu changed → discipline/domains stale); S1 NOT rerun (upstream/independent).
5. **Relaunch flag-ON A/B** with the v7 menu + split prompt; adopt only if kappa ≥ 0.800.
6. Close BUG-630 (after v7 apply+remap), BUG-648 (after split), BUG-658 (after no-wedge relaunch).

## 7. S4 rerun answer
YES — rerun S4→S5→S6 for every classified record whose discipline/domains were set. The menu (opaque ids,
axis-pure raw, renamed canonical) changed, so stored discipline/domains are stale. S1 (chunking) is upstream and
independent of the menu/taxonomy → **no S1 rerun**.
