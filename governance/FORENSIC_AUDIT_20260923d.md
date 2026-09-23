# Forensic audit (d) - 2026-09-23 15:27 (pre-task gate for the next 6 steps)

Scope: prove nothing has broken, drifted, leaked or silently changed BEFORE doing the next six steps; then
execute only what is not owner-gated. Every claim below was re-measured on disk in this session; nothing is
quoted from a previous audit.

## Invariants (all HELD)
- I1 git: HEAD 78a20c1 at start, working tree clean (porcelain 0); production pipeline/ untouched by the audit.
- I2 config: 41 config/*.yaml parse; mtp_enabled False; stage4.boundary_inject_enabled False (D-327), flag
  registered with 3 consumers.
- I3 registry: config/decisions.yaml 31 '- id: D-' entries, 0 duplicates, loads clean, D-354 present.
- I4 artifacts: all 18 audited paths exist (audit (c), vec gate, ANCHOR-3 ruler, manifests, pins).
- I5 ledger (read-only, mode=ro): fbs 7995 rows (rowids 7997..15991); vec_fbs 15990 rows = 7995 live + 7995
  orphan, 0 fbs rows missing a vector; vec_fbs_ctx 0 live / 7995 orphan / 7995 fbs rows unreachable. Unchanged
  from audit (c) - no drift, no silent repair.
- I6 hygiene: 0 tracked __pycache__, 0 tracked temp/, 0 root .bak.
- I7 abstention: enabled False; adopted discipline 25% (gain 5.33 pp, CI [1.37,10.26]); rejected content_type
  (CI [-1.81,8.86]); coverage_sla null; extraction_type refused with a reason.
- I8 pins: 6 pinned, 0 RED.
- I9 harness: just health exit 0, all wired checks 0 RED.

## Findings
- F1 (MED, CLOSED today) - the boundary control was unwired, stale-premised and could never pass in the D-327
  state; a second defect hid in the D-318 pin assertion (stamp.py folds the rule sha only when injection is ON).
  Fixed state-conditionally and wired as the 10th control. BUG-395.
- F2 (MED, CLOSED code-side) - the S5 checkpoint mixes bool with int 0/1 for is_summary/is_convergent, which
  crashed the parquet export after the SQLite+vector write. Coercion is now explicit and fails loud. BUG-388.
- F3 (LOW, CLOSED capability) - the R2 meter could not speak about extraction_type, and its axis map fell back
  to the DOMAINS list for unlisted axes (silent wrong-definition scoring). Both fixed; BUG-390.
- F4 (LOW, OPEN) - two live defaults point at retired/absent artifacts (golden set, dspy program). BUG-397.
- F5 (CLOSED by measurement) - the ANCHOR-3 ruler IS reproducible from a clone: the consolidated ruler and all
  five declared inputs (ruler blind sheet, F-11 review sheet, owner ruling map, closed_menu_v5.json,
  f11_llm_coder.yaml) are tracked in git, as is data/anchor_inputs/LLM_LABELS_R2_ALL150.jsonl.
- F6 (MED, POINTERED) - 6 governance artifacts still cite governance/ANCHOR1_BLIND_SHEET_20260920.csv /
  ANCHOR1_KEY_20260920.json, which do not exist on disk and are not tracked. NOT a live regression: the live
  harness (scripts/r3_preflight.py, inside just health) binds source 'anchor2' + authority ANCHOR-3. The stale
  citations are historical; a pointer block was appended. Repointing or retiring the R3 result remains an owner
  call (it is a new pre-registration if it is repointed).
- F7 (CLOSED by measurement) - the two carried typos are already fixed in every live file; the only surviving
  occurrence is inside a VERBATIM historical quote in config/decisions.yaml:7582, which is append-only
  (R-D410) and must NOT be edited.
- F8 (PROCESS) - the audit's own RED counter was wrong ("WIRED" contains "RED"). The exit code is authoritative.
- F9 (SYNC) - D-354 had been minted into config/decisions.yaml + 4 governance files but NOT into
  DECISION-LOG.md, where every D-3xx entry lives (D-353 is there). Synced in this session together with D-355.

## What this audit does NOT claim
Nothing here is an absolute error floor (D-337, RELATIVE-ONLY). No new retrieval-quality number was produced
(standing rule: none on a store whose live fraction < 1.0). The vec orphans are unchanged and still the top
owner-gated item: they invalidate the RULER, not one number, because k-NN slots are diluted by dead entries.

## Method
read-only SQLite URI (mode=ro); scripts/verify_vec_integrity.py; just health; scripts/verify_recalibration_pins.py;
git ls-files --error-unmatch for tracking; yaml.safe_load over config/*.yaml; no writes to the ledger or the DB.
