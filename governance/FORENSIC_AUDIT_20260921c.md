# FORENSIC AUDIT — session 8 (2026-09-21, D-315 ruling batch)

Scope: breakage, drift, blindspot, gap, conflict, mismatch, bug, hidden contamination, leak, error, failure,
future tax — **before** any serious task, per standing instruction. Everything below was re-derived read-only in
this session (BUG-336 standing rule: a carried-forward number is not evidence).

## Verdict
No breakage, no drift, no contamination, no leak. **Two real defects found and fixed** (BUG-338, BUG-339),
**one dangling citation** repaired, **one methodological gap** opened as explicit debt (F-11), **one housekeeping
debt** carried (F-10). The ruler ruling was executed and verified to move zero published numbers.

## F-01 (HIGH, FIXED — BUG-339) The config that declares "error rate, never accuracy" carried accuracy
`config/eval_integrity.yaml:ruler_measurement.measured` still held the **corrupt pre-correction** figures
(content_type **0.740** / discipline **0.506** / extraction_type **0.831**) as `accuracy`, with
`verdict: PASS_DECISIVE` anchored to them and `sheet:` pointing at the workspace, not the authority. Those figures
treat the STORED label as the answer key — exactly what D-275a forbids — in the file that carries the rule, and on
the machine-readable surface an agent reads before touching a floor. A live conflict: two answers, one wrong, with
no deprecation marker. **FIX:** honest `measured_error_rate` (CT 0.3533 / DISC 0.4741 / FORM 0.2828 with effective n
and Wilson intervals), the corrupt block retained as `superseded_measured:` (R-D410: deleting a published number is
not a correction), and a new `ruler_authority:` block carrying authority/workspace/superseded/lost hashes, the menu
hash, `truth_source` and the pooling rule.

## F-02 (MED, FIXED — BUG-338) The authority stores a scorer SENTINEL in a label field
`anchor1_frozen_20260920.json` carries `stored.discipline = "emerging_dump"` on **13 of 150 rows** — a token in
neither `config/taxonomy_v5.yaml` (61 canonicals) nor the live DB, and absent from the key's own declared
`vocabularies.discipline`. It is the scorer's internal sentinel: `emerging` on the STORED side is a dump = a
stored-label FAILURE, deliberately asymmetric with the human side where `emerging` IS an abstention. Consequence:
13/150 stored values do not reproduce from the DB (which says `emerging`), so a future consumer joining stored
labels to the DB silently gets a different value. **FIX:** the resolver is now idempotent over the sentinel and the
mapping is declared in config + registry. **The authority was deliberately NOT edited** — rewriting an immutable,
sha256-cited artifact to fix cosmetics is precisely the D-313 sin (that is how this whole defect class started).

## F-03 (CLEAR) No stored-label drift since the freeze
Live DB mtime `2026-09-19T21:47` predates the `2026-09-20 13:15` freeze; 7,995 fbs. All **150/150** frozen `fb_id`s
resolve in the live DB, and `stored.content_type` reproduces **150/150** and `stored.extraction_type` **150/150**
exactly. The only `stored` discrepancy is the F-02 sentinel rename. The ruler's object-under-test side is
reproducible from the live store.

## F-04 (CLEAR, fixed) C21 debt: both sheet-reading scorers
`rescore_ruler_inverted.py` read its reference from the CSV workspace and `score_ruler_labels.py` from the legacy
sheet/key pair — two sources of truth for one question. The scorer now takes truth from the authority
(`--truth-source key`, the config default) through **one** resolution path (canonical labels re-resolve to
themselves), with `sheet` retained only as a cross-check.

## F-05 (CLEAR, fixed) Mismatch: one dangling citation survived the ANCHOR rename
D-314's `evidence:` cited `bakeoff_typed_decision_anchor1_20260921.json`, which no longer exists after the
ANCHOR-1/ANCHOR-2 split. A decision record whose evidence path cannot be opened is not evidence. Repointed.
Rule: a rename is not complete until every citation resolves.

## F-06 (CLEAR) No hidden contamination
`scripts/audit_eval_integrity.py`: DISJOINTNESS ok — train-pool x anchor overlap **0 / 1027** (limit 0). The
HUMAN SHARE WARN is the known BUG-267 state, not a new finding; no eval row is in the training pool.

## F-07 (CLEAR) No production drift, no breakage
`pipeline/` diff vs HEAD = **0 files**. `compileall pipeline scripts` rc=0. Every touched YAML loads. No
`__pycache__`/dead code added; the 4 stale `anchor1_*` .pyc were removed in the rename commit.

## F-08 (CLEAR) Ruler integrity and the ruling's blast radius
Authority keys ↔ workspace rows are **1:1 on all 150 `item_id`s** (the workspace carries 4 structural blank rows
that are not items). Re-scoring from the authority reproduces the published numbers **exactly**
(CT 0.3533 / DISC 0.4741 / FORM 0.2828) and equals the authority's own `summary_error_rates` — so **D-315 moves
zero published numbers**. Verified both directions (`--truth-source key` == `--truth-source sheet`).

## F-09 (CLEAR) Truth-blinding self-test: PASS 3/3
`--self-test-blinding` replaces every stored label with a fixed wrong value and asserts the reference side is
invariant: scored_n, abstentions, per-class reference counts, the scored row set and the human labels all unchanged;
blinded agreement 0 on every axis. This is the mechanical channel because the LLM reviewer returned a schema-shaped
rubber stamp (BUG-333). Ruler-path leak: **none**.
Declared diagnostic loss: the authority keeps no raw cell, so the abstention REASON survives only in the workspace
(DISC abstentions read as `blank 34` from the key vs `blank 28 + abstain-emerging 6` from the sheet — same
denominator, same estimand, less colour).

## F-10 (LOW, OPEN — carried, not dropped) Housekeeping debt
46 gitignored `config/*.bak_*` (one is named `.bak_fix`, not date-stamped) + `governance/buglog.md.bak_20260921_anchor1`.
They cannot be committed (`.gitignore:101 *.bak_*`) so they cannot cause a revert, but a stale `decisions.yaml.bak_*`
sitting beside the live one is a real read-the-wrong-file hazard. Not removed this pass: they are the only recovery
copies of files whose history matters. Belongs to a cleanup pass with the owner.

## F-11 (GAP, OPEN — methodological, the largest one) No second coder
`config/eval_integrity.yaml` declares `second_coder_required_before_repointing: true`. No second coder exists, so
**every floor in this repo is single-coder**. Diagnosis and re-measurement are unblocked; **repointing a floor is
not**, and no gate can waive it. Until then every published error rate carries unmeasured inter-coder variance.

## F-12 (FUTURE TAX, declared) Two known dead ends
(a) The ruler's content_type axis is dead under menu `cac6e695` (CT = 7 classes, **no `none`**; content_type kappa
0.0, DEGENERATE/F-17). Any CT work must use ANCHOR-2's `73597ee2`. (b) Never pool RULER-150 with ANCHOR-2: two
sampling designs and two menus; pooling is legal only at read time with weights. Both are now written into
`ARTIFACT_REGISTRY.md` and `ruler_authority.pooling`, so the next session cannot rediscover them by accident.

## C15 — unresolved bug register (17 items, listed because the threshold is exceeded)
HIGH: BUG-311 (stage5 checkpoint missing), BUG-313 (cognitive science 94% contra 126/133), BUG-319 (qwen3coder arm
abstains 116/116). MED: BUG-310, BUG-312, BUG-315, BUG-316, BUG-317, BUG-326 (BLOCKED), BUG-331, BUG-333,
BUG-334, BUG-336. LOW: BUG-330. Closed this session: BUG-329 (by ruling), BUG-338, BUG-339, BUG-337 follow-up.

## Verification run (all green)
```
YAML OK | COMPILE OK
axis  | WORKSPACE(sheet)  | AUTHORITY(key)    | frozen summary | match
ct    | n=150 err=0.3533  | n=150 err=0.3533  | n=150 0.3533   | OK
disc  | n=116 err=0.4741  | n=116 err=0.4741  | n=116 0.4741   | OK
form  | n=145 err=0.2828  | n=145 err=0.2828  | n=145 0.2828   | OK
BLINDING SELF-TEST: PASS (ct/disc/form: reference invariant, blinded_agrees=0)
decisions.yaml: total=682, summary in sync (--check clean)
```
