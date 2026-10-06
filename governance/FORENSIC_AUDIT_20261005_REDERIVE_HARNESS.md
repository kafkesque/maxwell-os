# FORENSIC AUDIT — D-2820 re-derivation harness (rederive_anchor_axes_v6.py)

**Date:** 2026-10-05 · **Scope:** scripts/rederive_anchor_axes_v6.py + config/pipeline_config.yaml (3 keys) + tests/test_rederive_anchor_axes_v6.py
**Verdict:** NO BREAK, NO CASCADE, NO DRIFT. Additive, owner-gated, fail-closed. Two decisions resolved (depth unguarded; generator==verifier refused).

## F-01 — BREAK (does it break the pipeline?) — NO
The harness is a standalone script; it imports `pipeline.closed_menu`, `pipeline.anchor_menu_guard`, and (only in `--generate/--verify`) `pipeline.omlx_call` / `pipeline.stage5_verify`. It writes nothing to the DB or the store. The 3 config keys are additive under `stage4:` and read by nothing except this script. `--plan`/`--selftest` exercise no inference and no DB write.

## F-02 — CASCADE (does a change ripple?) — NO
`load_pins()` re-derives the live composite from `render_closed_menu()` and refuses on drift (D-277), so a future taxonomy edit cannot silently re-certify a stale anchor. The config keys have no other consumers (verified: only this script reads `anchor_rederive_*`).

## F-03 — DRIFT (does provenance drift?) — NO
Menu v6 is reproducible: `render_closed_menu()` == `closed_menu_v6.json` == composite pin `92f1a204…`; answer-space pin `d704d06e…` reproduces from the 5-axis value set. `taxonomy_version` is read from `taxonomy_v5.yaml` (`v5.7`), never hardcoded.

## F-04 — BLINDSPOT — NONE REMAINING
The circular-kappa blindspot (BUG-650) was closed last turn by `anchor_menu_guard.py`. This harness closes the *production* blindspot: it stamps `menu_hash` + `answer_space_hash` (live v6) so its output passes the guard, and refuses off-menu labels (`validate_on_menu`, C16).

## F-05 — GAP — ONE resolved (depth), ONE documented (R5-family)
- **Depth axis** intentionally NOT re-derived: menu v6 changed discipline/domain slots + abstention, not the 4-way depth axis (D-2820). Documented in manifest `depth_axis_untouched`.
- **R5 family guard** added: `generator == second_coder` → refuse (generator `gpt-oss-20b`, second coder `gemma-4-E4B` — distinct families).

## F-06 — CONFLICT — NONE
Config keys use existing model names already in `pipeline_config.yaml` (`discipline_model`). No key collides. The guard reads pins from `config/menu_axis_hashes.yaml` (single source, C12) — no second pin definition.

## F-07 — BUG — ONE FOUND + FIXED (mine)
`_classify_prompt` f-string had a `single '}'` SyntaxError (JSON brace inside f-string). Fixed by building the JSON instruction with string concat, not f-string. Selftest also initially asserted guard-acceptance with FAKE pins — the guard (correctly) rejected them; fixed to use `load_pins()` (real pins), which *proves* the guard fires on non-live stamps.

## F-08 — HIDDEN FAILURE — NONE
Every failure path raises `SystemExit`/`RuntimeError` (C16): missing pins, drift, empty menu, label-without-definition, unjoinable name, unadjudicated row, off-menu label, generator==verifier, no-JSON from classifier. No `except: pass`.

## F-09 — ERROR LEAK — NONE
`_nli_pair_scores(..., raise_on_error=True)` surfaces NLI errors into `_crosscheck.nli.verdict` as `nli-error:` — never a silent `(0,0,0)`.

## F-10 — MISMATCH — NONE
`join_text` mirrors `discipline_conformance_gate.load_anchor` exactly (collapse-whitespace name → fbs); verified 204/204 join, 0 missing. Stamp fields match D-274d exactly (anchor_version/menu_hash/taxonomy_version/coder/date/abstention).

## F-11 — BLOAT — NONE
6 pure functions + 5 CLI stages, each < 40 lines of logic. No dead branches; `_classify_prompt` is shared by `--generate` and `--verify` (no second prompt copy).

## Controls (green)
- `--selftest`: stamp builder, adjudication fail-closed (unadjudicated/off-menu), manifest + BUG-650 guard acceptance.
- `--plan`: 204 rows joined / 0 missing; menu v6 64 disciplines + 43 domains; pins verified.
- pytest: **6 passed** (incl. guard-acceptance with real pins).

## Remaining (owner/human-gated — NOT implementable by the agent)
1. `--generate` (LLM candidates) → owner adjudicates → `--adjudicate` → `--verify` (second-coder + DeBERTa NLI) → `--finalize`.
2. Flip D-2839 PROPOSED → RATIFIED (owner sign-off).
3. Full-204 A/B (D-2767) → flag flip iff kappa ≥ 0.800 AND emerging ≤ 0.35.
