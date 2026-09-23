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
