# Forensic audit - 2026-09-23 (pre-serious-work gate)

**Scope:** F-11 anchor chain, production paths, config integrity, registry/log consistency, hygiene, contamination,
and the live stage-5 state. **Method:** mechanical (hashes, row counts, cell-level loss checks, yaml/json parse,
process + checkpoint inspection). No LLM judged anything; no artifact was written before its check passed.

## Verified clean
| check | result |
|---|---|
| production code untouched | `git diff a2b2a07^..HEAD -- pipeline/` = NONE; `config/eval_integrity.yaml` untouched before this audit |
| F-11 anchor lossless | 150 rows / 150 unique ids; 216/216 owner cells carried; per-axis raw + final + tier all populated |
| blind export uncontaminated | `F11_LLM_CODER_20260922/ROWS_BLIND.csv`: 10 cols, 0 answer-like columns, **0 ruler label values present in any row** |
| no book prose in the anchor | only item_id/name/labels - no definition/application/source-excerpt text |
| registry integrity | 705 decisions, 0 duplicate ids, 0 ids in DECISION-LOG but not the registry, `--check` in sync |
| config integrity | every `config/*.yaml` + `*.json` parses |
| ruler sheet untouched | hash-bound, read-only, never written by any script this session |
| single-writer lock | no stale `.lock` left by the stage-5 run |

## Findings (all fixed this session)
| id | severity | finding | fix |
|---|---|---|---|
| F-1 | MED | the owner's typo repairs were invisible in the note (only the canonical value showed) | alias repairs are now named verbatim in `<axis>_source_note`; raw spelling also in `<axis>_ruler_raw` |
| F-2 | **HIGH** | the anchor declared tier `human-mixed+llm-attested`, which **did not exist** in `config/eval_integrity.yaml` `provenance_tiers` - any tier-validating consumer would reject the anchor | tier registered with definition, permitted use (relative only), authority path, decisions, and the permanently-unsatisfied second-coder flag |
| F-3 | **HIGH** | the two round-2 coders had **no model identity** on disk (config said TO-BE-FILLED-AT-RUN) while D-331/D-335 claim "two independent families" - an R14 provenance gap | model/family/prompt_sha256/identity_source stamped for both, marked **owner-attested** (no API receipt) |
| F-4 | MED | `second_coder_required_before_repointing: true` read as an open TODO, conflicting with D-337 | annotated as PERMANENTLY unsatisfied -> floors stay frozen, relative use only |
| F-5 | MED | the owner's filled `F11_ANCHOR_REVIEW_20260923.csv` was **uncommitted** (primary evidence at risk) | committed |
| F-6 | LOW | 213 stray `.bak*` files (72 in `knowledge pipeline/`, 48 config, 32 governance) | moved to `archive/bak_sweep_20260923/` preserving paths; **0 deleted** (evidence) |
| F-7 | LOW | stage-5 run state was never read back | **run COMPLETED**: checkpoint 7,995 records = 1,250 verified + 6,745 remaining; lock released; no fatal error in the tail |

## Open conflict for the owner (not silently resolved)
* **C-1 (HIGH):** D-328 states abstention was **ENABLED** at p25, but `config/verify_abstention.yaml` says
  `enabled: false` with `t_low_percentile: 25 # PROPOSED`. Decision and config disagree. No production behaviour was
  changed by this audit; the owner must rule which is authoritative.

## Not fixed on purpose
* 4 owner cells hold DOMAIN values in the discipline column (`personal productivity` x3, `design strategy`):
  flagged `OFF_MENU_DOMAIN`, preserved verbatim - a declared vocabulary choice, not an error.
* `anchor1_frozen_20260920.json` byte-loss note: pre-existing, citable read-only (D-315); out of scope.
* `agent/session_seed.yaml` + `feed.opml` are dirty from the owner's own tooling - left untouched.

## Session 18 addendum (2026-09-23) - C-1 CLOSED, F-1 CLOSED, C-2 OPENED

* **C-1 CLOSED (D-338).** The conflict was NOT "which file wins": D-328 asserted an implementation
  state that no artifact ever carried. No production code reads `config/verify_abstention.yaml`
  (grep hits only in `temp/` and `archive/`), so the register claimed a protection that enforced
  nothing while D-2298 fail-closed is what runs. Resolution: D-328 superseded (never edited, R-D410),
  the config now carries `status: gated` + `consumers: []` + a four-item `activation_gate`, and
  `enabled` stays **false**. Second ground: the 0.391-vs-0.4741 delta is RELATIVE (D-329(b)/D-337),
  so it cannot be an enforced absolute door; third: a percentile threshold is not a bounded cost.
* **F-1 CLOSED.** `canon()` now reports the canonicalisation MECHANISM (verbatim / orthographic /
  alias / offmenu) and aliases are AXIS-TAGGED; R030/R063 name the owner verbatim spelling
  (`computer graphic`, `media studie`) and carry `ALIAS_CANONICALISED:owner:discipline`. Labels and
  tiers unchanged (0 diffs), 150 rows. Anchor sha256 now
  `29393d5f9d5292053a39986582578e140121d8987448648ad63f528062cd2698` (supersedes 3911eece...).
  Fixed BUG-372 en route (two wrong repair attempts, both caught by a flag guard before writing).
* **C-2 OPENED (HIGH, OWNER GATE - production behaviour).**
  `config/pipeline_config.yaml:311 stage4.boundary_inject_enabled: true` while D-327 (RESOLVED
  2026-09-21) ruled the flag back to **false** after the block failed every reading (emitted 42/60 vs
  47/60, error 0.8333 vs 0.8000, oov 18 vs 13). `git log -S` shows exactly ONE change to that string:
  commit `8de5d36` added it as true - **the flip D-327 records was never applied**. The flag IS
  consumed (`pipeline_paths.py:213` -> `stage4_merged_call.py:120`, `stamp.py:124`), so the rejected
  experiment is live in the S4 prompt. Fix is one line; it is an owner gate because the S4 prompt
  changes. Logged BUG-374.
* **New standing check (D-339).** `scripts/audit_flag_consumers.py` + `config/flag_consumer_registry.yaml`
  (wired into `just health`) turns every stateful flag into a test: STATE MISMATCH vs the cited
  decision, or an ON flag whose consumer never reads it, is RED. C-1 and C-2 were both invisible to
  every previous check because nothing compared a decision to the artifact's state.

## Session 19 addendum (2026-09-23) — 6 steps executed; 3 new defects found and 2 closed
1. **C-2 CLOSED (BUG-374).** D-327's flip had never landed (`git log -S` = exactly one commit, 8de5d36, which added
   it as true); the A/B-rejected boundary block was live in the S4 prompt for two days. Applied atomically, verified,
   `just health` RED cleared. No new decision: D-327 already ruled it.
2. **BUG-375 FIXED (audit-on-the-audit).** The new D-339 flag check reported a REGISTERED flag as unregistered
   because its scan used leaf keys while the registry uses dotted paths — the BUG-372 class inside the very check
   meant to catch it. Scan rewritten to walk the parsed document; a self-check now makes that drift RED.
3. **C-3 OPENED (BUG-376, HIGH, owner gate).** The complete 7995-verdict S5 run (`PASS 5023 / QUARANTINE 2972`)
   declares input `2f8b34fb...`, but its S4 input was rewritten 65 min after completion and that image is GONE from
   disk. `config/eval_integrity.yaml` was asserting the opposite ("live_absent_since 2026-09-21") — stale governance,
   now synced additively (`current_state_20260923`), with BUG-341's premise superseded.
4. **NEW standing check.** `scripts/verify_declared_inputs.py`: every `input_fingerprint.json` hash claim must still
   resolve; an unacknowledged move is RED. This is the class-level fix for "a completed run silently stops being
   citable". Wired into `just health`.
5. **ANCHOR-3 FROZEN.** `governance/ANCHOR_MANIFEST_20260923.json` (sha256 29393d5f..., 85811 bytes, 150x31,
   tier human-mixed+llm-attested, RELATIVE-ONLY per D-337) + `scripts/verify_anchor_manifest.py` in `just health`.
   Every arm comparison now cites a manifest, so a silent regeneration cannot change the reference.
6. **C15 OBLIGATION REPAIRED.** 71 open / 49 closed of 120 ids (mechanically re-derived, BUG-342 rule) while
   `agent/session_seed.yaml` carried ZERO bug ids. `governance/SESSION-HANDOFF-2026-09-23.md` now carries the full
   register and the seed points at it.
7. **Flag audit truth restored as a first-class refusal:** if the scan and the registry ever disagree about naming,
   the check reports RED, not warn — an integrity flag may never fire on expected behaviour.

## Session 20 addendum (2026-09-23) — 6 steps: C-3 mitigated, D-340 minted, R3 gated, hygiene logged
1. **C-3 MITIGATED (not closed):** `frozen/S5_t11_20260922/` + `governance/FROZEN_S5_T11_20260922.json` +
   `scripts/verify_frozen_pair.py` (in `just health`). S6 can cite a byte-stable pair with the mandatory qualifier;
   the owner gate (S5 REVERIFY vs cite-the-pair) is unchanged.
2. **D-340 minted (GOVERNANCE, class fix for C-3):** a declared stage input is immutable; an in-place writer must
   publish a mutation notice at the moment of change (`scripts/input_mutation_notice.py`), and
   `scripts/verify_declared_inputs.py` accepts a mismatch ONLY when a notice covers it — the exception is authored by
   the writer, never hand-edited into config afterwards. Registry now 124 ids, `--check` in sync.
3. **R3 PREFLIGHT (config-first, no invented source):** `bakeoff.anchor_ref` names ANCHOR-3 + its bound;
   `scripts/r3_preflight.py` verifies the authority's bytes, the truth source's verdict columns and the
   pre-registered n (58/58 measured) before any arm comparison runs. The truth source was NOT silently swapped —
   swapping a reference is a scientific change and needs a decision (D-337 relative-only).
4. **Flag registration proposal:** `governance/FLAG_REGISTRATION_PROPOSAL_20260923.md` — every unregistered flag with
   the files that reference it, so `REGISTER FLAGS` is a one-word call with no reading.
5. **Hygiene:** untracked root scratch archived; **BUG-378** logged (tracked root scratch files, the undeclared 95 MB
   `checkpoint_enriched_kindsafe.jsonl` sibling, stale `__pycache__`, five `.stale_*` fingerprint siblings).
6. **`just health` now runs 8 checks**, all fail-loud: guard_stacks, status, integrity --quick,
   audit_flag_consumers, verify_anchor_manifest, verify_declared_inputs, verify_frozen_pair, r3_preflight.
