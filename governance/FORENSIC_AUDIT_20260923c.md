# FORENSIC AUDIT (c) — 2026-09-23 15:14 (pre-serious-task gate)

Trigger: owner asked for a forensic audit before any serious task: nothing broken, drifted, blind, gapped,
conflicting, mismatched; no hidden contamination, leak, error, failure, or future tax; then sync governance deps.

Method: every claim below was RE-RUN or RE-MEASURED in this session (D-347 spirit: never quote, always re-score).
Nothing was accepted from a prior summary. Where a number could not be reproduced, that is stated as a finding.

## Invariants (all held)

| # | invariant | evidence | verdict |
|---|---|---|---|
| I1 | no production code changed | 'git status --porcelain' empty; commits 88ee83e/5c934d1/510026c touch 0 files under pipeline/ | HELD |
| I2 | no LLM run, no inference, no label/menu/definition change | no model process started this session; the only new script is read-only | HELD |
| I3 | no DB row written | opened read-only (mode=ro) for every measurement | HELD |
| I4 | no destructive operation | no delete, no safe_delete.py (BUG-261), no stage6 re-run | HELD |
| I5 | gates still green | 'just health' exit 0; 8 verify checks wired; 0 nonzero RED; 1 named WARN | HELD |
| I6 | recalibration pins | 6 pinned, 0 RED | HELD |
| I7 | governance registries consistent | 30 decision ids, no duplicates, all YAML loads | HELD |
| I8 | hygiene | __pycache__ on disk but untracked/ignored (C19 clean); no .bak/.tmp in root | HELD |

## Findings

| # | sev | finding | status |
|---|---|---|---|
| F1 | INFO | Health is honest: 8 verify checks wired (anchor_manifest, declared_inputs, frozen_pair, evidence_manifests, artifact_authority, menu_routing, menu_policy, recalibration_pins). BUG-393 (the false wiring claim) stays fixed: the wired set == the on-disk set minus one. | VERIFIED |
| F2 | INFO | Governance sync from D-352/D-353 intact: decisions.yaml D-352 + D-353 present; DECISION-LOG has both headings; buglog has BUG-387/388/391/392/393; addenda present in CONTEXT_INDEX, aggregated_remaining_tasks, SEQUENCE_STATUS. | VERIFIED |
| F3 | HIGH | NEW: the contextual vector store 'vec_fbs_ctx' is 100 percent REFERENTIALLY DEAD. Measured: 7995 rows, 7995 orphans, 0 rows join to a live fbs row. | OPEN (BUG-394) |
| F4 | HIGH | BUG-387's own description is an INFERENCE, not a measurement. It says the store was DOUBLED (15990 = 2 x 7995). Measured shape is different (see F5). | CORRECTED (BUG-394) |
| F5 | MED | Measured vec-store shape: fbs = 7995 rows at rowids 7997..15991; vec_fbs_rowids = 15990 rows spanning 1..15991 = 7995 LIVE + 7995 ORPHANED (rowids <= 7996 whose fbs rows were deleted/replaced). distinct(rowid) = 15990, so there is NO live-rowid collision. Retrieval impact is DILUTION, not starvation: retrieve.py over-fetches knn_k = max(limit*5, 100), or max(limit*15, 200) with facets, so a 50 percent live index still fills limit=20. | OPEN (BUG-394) |
| F6 | MED | Nothing in the repo asserts referential integrity of the vec0 stores. The only completeness check counted ROWS (carried record: stage6 printed 'Vector: READY 15990/7995'), which is exactly the measurement that cannot see an orphan. | CLOSED by new gate (see Fix below) |
| F7 | MED | NEW: 'scripts/verify_boundary_injection.py' exists, NO recipe runs it (grep 'boundary' in justfile = 0 hits), and it exits 1 TODAY: 'baseline prompt 11126 chars | treated 11126 chars (+0)' then 'FAIL missing=[default_home:...]'. | OPEN (BUG-395) |
| F8 | MED | F7 is NOT a live regression and NOT a lost pin: D-327 rejected the ruled boundary block ON MEASUREMENT (frozen 60-row ANCHOR-2 A/B, error 0.800 vs 0.800-adjacent), and config/pipeline_config.yaml:313 stage4.boundary_inject_enabled: false is registered with 3 consumers in config/flag_consumer_registry.yaml. The block is ABSENT because it was REJECTED. So the defect is the CHECKER (it has no flag awareness — BUG-375 class) plus a stale governance claim ('SEQUENCE_STATUS:600 control artifact -> PASS'). | OPEN (BUG-395) |
| F9 | MED | Attribution of the orphans is UNDETERMINED from inside this session and cannot be recovered: fbs created_at spans 2026-08-30..2026-09-03 (so no live fbs row was created on 09-23), the DB mtime is 2026-09-23 13:41, and no artifact names the writing run. Same class as BUG-391: an unreconstructible provenance. | OPEN |
| F10 | LOW | The D-353 block 're_ratification_20260923' has no 'status' key while its sibling 're_measurement_20260923' does (status: ratified_rescored). No consumer reads it, so this is cosmetic. NOT edited: config/verify_abstention.yaml is digest-pinned (abstention_policy pin) and the D-353 rule says any change to a pinned artifact needs a decision. Recorded so it is not mistaken for a missing block. | ACCEPTED (cosmetic) |
| F11 | LOW | 'recalibration_pins' reverts to RED on ANY future edit of a pinned file by design. This is the gate working. Operator note: after an authorised re-measurement you MUST refresh the pin sha in the same commit as the decision, or health goes RED. | EXPECTED |
| F12 | INFO | Disk 97 percent used, 29 GiB free (926Gi/873Gi, /dev/disk3s5). Still owner-only chore; checkpoints + archive/ are the safe order; NEVER safe_delete.py (BUG-261). | OPEN (owner) |
| F13 | INFO | Carried and unchanged: 5 stale citations of the superseded 0.4741/116; ANCHOR-1 blind sheet/key missing (0 files match governance/ANCHOR1*); temp/ holds 509 files with 0 tracked in git; BUG-388 and BUG-390 open. | OPEN (carried) |

## The one measurement-validity consequence (read this before quoting retrieval numbers)

The vector leg used by production is vec_fbs (live fraction 0.50). Any retrieval-quality measurement taken on a
diluted index is measured on a DIFFERENT ruler than one taken on a whole index: same query, same k, half the
candidate pool. Existing retrieval research is NOT contaminated by this: governance/RETRIEVAL-RESEARCH-2026-09-02.md
is dated 2026-09-02 and pipeline/retrieval_benchmark.py is dated 2026-09-03, both BEFORE the fbs rowid generation
was replaced. Standing rule from this audit: no NEW retrieval-quality number may be produced until F4/F5 are repaired.

## Fix specified for F6 (implemented this session, deliberately not yet wired)

config/vec_integrity.yaml + scripts/verify_vec_integrity.py: per vec0 table, resolve the shadow rowid table,
count live / orphaned / missing, and exit 1 if live != fbs count or orphans > 0. It exits 1 TODAY, correctly.
It is NOT wired into 'just health' yet ON PURPOSE: health must not be left permanently RED by a defect whose repair
is destructive and owner-gated. The wiring is the last step of the F4/F5 repair, together with the repair receipt.

## What is NOT claimed

- NOT claimed: that the pipeline is broken for reads. fbs -> vec_fbs coverage is complete (0 fbs rows lack a vector).
- NOT claimed: that any label, menu, definition, or ruler changed. None did.
- NOT claimed: that the 7995 orphans are duplicate CONTENT. Only their rowids are orphaned; content was not compared.
- NOT claimed: that D-327 is wrong. The block is rejected by measurement; only its control script is stale.
- NOT claimed: that the audit found nothing in the abstention work. D-352/D-353 were verified as still consistent.

## Method (commands actually run)

1. git rev-parse/status/log/rev-list; git show --stat for the 3 commits (pipeline/ file count = 0 each).
2. just health (exit 0), scripts/verify_recalibration_pins.py (6 pinned, 0 RED), verify_anchor_manifest, verify_menu_policy.
3. scripts/abstention_robustness.py (exit 2 by design, 3 findings, reproduced_legacy: False).
4. sqlite3 read-only on 'knowledge pipeline/maxwell.db': counts, distinct rowids, orphan joins for vec_fbs and vec_fbs_ctx.
5. grep for boundary wiring across justfile/recipes; ran scripts/verify_boundary_injection.py (exit 1, captured).
6. wired-vs-on-disk comparison of every scripts/verify_*.py; justfile path existence check (0 dangling).
7. decision-id duplicate check; pycache/temp tracking counts; df.

D-354 (referential integrity of the vector stores is a gate) is minted with this audit so the fix has an id and the
pin/trigger culture extends to the vec store. No other decision id is minted: no artifact's meaning changed here.
