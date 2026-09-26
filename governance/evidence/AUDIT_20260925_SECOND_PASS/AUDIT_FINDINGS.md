# AUDIT 2026-09-25 (second pass) - forensic findings, owner gates, next steps

Scope: the working tree at HEAD `96b1e9c` + 22 changed/new paths. Read-only probes; every claim below is a
measurement with the command that produced it. Nothing is committed by the assistant.

## FIXED this pass

| id | finding | measurement | fix |
|---|---|---|---|
| F-01 | **the claim-shape instrument builder OVERWRITES the live instrument** (drops `evidence_span` + `abstain`, renames the gate bit) | running `build_form_elicitation.py` rewrote `CLAIM_SHAPE_ELICITATION_11.csv` and removed 2 declared columns | config-declared schema + `refuse_overwrite_when_answered: true` (exit 3); one execution showed no answer existed, so nothing was lost |
| F-02 | **a FALSE existence-negative in a docstring**: "There is NO FORM anchor (FORM(1-4) is BLANK in all 150 rows)" | FORM(1-4) = **145/150 non-blank**; `extraction_type_final` = **145/150**; the blank column is DEPTH (18/150) | recorded as `NEG-002` (answer: refuted) + the scorer now MEASURES the coverage at run time |
| F-03 | **namespace collision**: the 4 questions are the CLAIM-SHAPE bit, every column was named `FORM_*` | questions q1-q4 = comparative / stated exchange rate / boundary / falsifiable | renamed `claim_shape_*`; scripts renamed `build_claim_shape_instrument.py` / `score_claim_shape_gate.py`; cohort + columns declared ONCE in `config/claim_shape_instrument.yaml` |
| F-04 | **dangling reference**: the buglog's audit line cited `governance/AUDIT_20260925_SECOND_PASS.md`, which did not exist | `ls` -> No such file | this directory is that receipt; the buglog line now points here |
| F-05 | **widening log incomplete**: 4 self-added `may_touch` patterns declared, but `governance/ANCHOR4_MANIFEST_20260924.json` was a 5th path outside `may_touch` with no entry | coverage check over `git status` vs `may_touch` | 5th pattern added with its why (stamped because the contract verifies the stamp) |
| F-06 | **register drift**: `governance/bug_status.json\|md` sat 13 ids behind the buglog (98/91 vs 105/97) while `just health` was green | re-derivation | new `scripts/check_bug_status.py`, wired into `just health`; register regenerated |
| F-07 | **a rail that never ran**: BUG-446's owed self-parse probe - `just --list` was never part of `just health` | `grep` over the recipe | `@just --list` is now the FIRST line of `just health` |
| F-08 | two id families with no uniqueness rail; `DECISION-LOG.md` duplicate `## D-356` heading | 743 records / 0 dup ids in the registry; log has `D-`52 vs `D`691 and one repeated heading (lines 474, 489) | recorded (F-08/F-11); a cross-family uniqueness rail is owed |

## RECORDED, not fixed (owner act or a later unit)

- **F-09 `config/anchor_family.yaml` understates the depth state**: it declares `depth: intersection: 0` while the
  TRACKED blind sheet carries **18/150** owner depth cells (`reviewer=human`, `date 13.09.26`, R001...). The freeze
  must start from 18 + the 24.09 owner pass, not 0. Owner question below.
- **F-10 the declared agreement floor has NO consumer**: `grep -rl agreement_floor` -> only the yaml and the
  decisions prose. D-373's floor is a decoration until a >=2-rater scorer reads it.
- **F-11 the contract no-ops today**: `--gate-if-active` with `status: proposed` prints NON-GATING and returns 0.
  By design (C22 owner gate) - but it means the depth/domain contract is not yet a rail.
- **F-12 the whole depth/domain contract stack is UNCOMMITTED** (22 paths, untracked). It exists only in the
  working tree; the D-372 ruling cites files that no commit contains.
- **F-13 C15**: the register says 105 open / 97 closed, so "append unresolved to all handoffs" is triggered; the
  newest handoff on disk is 2026-09-23.

## CLEAN (checked, no defect)

- `pipeline/**` untouched (`git status` filter empty); blind sheet + consolidated ruler **byte-identical to HEAD**
  (no owner-instrument contamination); no tracked `__pycache__` (gitignored); no `_OLD` outside `archive/`; no
  `.env` tracked; `git grep` for key patterns -> none; every `config/*.yaml` parses; the instrument carries NO
  depth/verdict column (contamination guard holds); `discipline`/`answer_space` drift unchanged (definitions only).

## OWNER GATES (blocked on a human decision - each is one edit or one word)

1. **Pin ruling -> activate the contract** (one edit, C22 owner act): `config/depth_domain_contract.yaml`,
   `status: proposed` -> `active`. Effect: `just health` starts gating; hard findings exit 1; owner-owed stays 2.
2. **R040 / R140** (`ABSTENTION_ONLY`, `DOMAINS_BLANK`): one word - declare `abstained_owner_owed` (recommended;
   parity removes them from numerator AND denominator) or supply the cell.
3. **R070 / R080 / R130**: supply depth, or declare permanently unavailable.
4. **BUG-454**: rename the workbook's per-row `flags` COLUMN to `row_flags` (recommended) - touches the owner's
   workbook, so it is an owner edit, not an assistant edit.
5. **D1/D2 FORM rule**: KEEP or amend (recommendation: KEEP - the amendment is falsified by measurement).
6. **`extraction_type` as a consumed axis**: yes/no (recommendation: NO, not now - wire it into S5 as a REPORTED
   field first).
7. **The 24.09 owner depth drop-in** (F-09): confirm which artifact is canonical - the tracked 18/150 pass
   (13.09.26) or `Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` rev 2 (24.09.26) - so the freeze and the D274f
   test-retest clock start from a stated state.
8. **Widening ack**: say so in the commit message (D-376; the log now has 5 patterns, not 4).
9. **Commit**: rail 4 permits it; HEAD `96b1e9c`; the assistant does not commit.

## NEXT CONSEQUENTIAL STEPS (ordered, after the gates)

1. BUG-450 prevention: make `scripts/definition_nli_verify.py` stamp a report-level provenance block
   (label source artifact + column + sha256, extractor, NLI model id, menu_version, answer_space_sha256).
2. Rename the workbook column (gate 4) -> then BUG-426: find/bind the owner's 150-row DOMAIN pass.
3. CLAIM-SHAPE run with a NON-AUTHOR elicitor (the instrument is now non-destructively rebuildable).
4. FORM ceiling panel (DeepSeek + Qwen3.8, one-shot temp 0) + Krippendorff alpha at the declared 0.800.
5. Wire `extraction_type` into S5 as a REPORTED field; measure; only then decide consumption.
6. Depth freeze (from the stated state) -> D274f 30-row test-retest -> D274d.
7. BUG-455/456 archive integrity (content_sha256 + backup rotation manifest); DISC<->domain bridge.
8. A cross-family decision-id uniqueness rail; the `## D-356` duplicate heading correction.
