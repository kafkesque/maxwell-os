# ANCHOR domain axis — run receipt (2026-09-24)

**Instruction:** "do the domain classification" (owner, 2026-09-24), on the anchor family.

## Instrument — settled by PRECEDENT, not preference
The 216-row domain cohort (D2618-P0/P1) was coded by the reliable pair **`deepseek-v4-pro` (API) + `Qwen3.8-27B-MLX-4bit`
(local OMLX)**. The same pair, the same D2610-v2 policy and the same config-loaded vocabulary now vote the anchor, so the
two cohorts stay comparable. Harness: `scripts/vote_anchor_domains.py` — it **imports** `vote_once()` / `aggregate()` /
`_canonical_defs()` from `scripts/build_discipline_domain_vote.py`; the instrument is not forked.
**gpt-oss was NOT used:** it is the S4 classifier family under test, so labeling the anchor it will be scored against is
ancestor contamination. "Qwen3.8" in the owner's question = Qwen3.8-27B, the local half of the pair.

## Blinding + declared deviations
Input: `governance/frontier_pack_20260924/BLIND_INPUT_150.csv` — row text only, **no CT/DISC/FORM/DEPTH/conf_depth and
no BOUNDARY** (boundary encodes scope, which would leak the depth axis). The frontier coders will read the identical file.
`prompt_id: anchor_domains_v1` is **domains-only**: the anchor's content_type and discipline are HUMAN-owned in ANCHOR-3
and are deliberately not re-coded. The vocabulary is read from config (C12); the prompt ships the 43 canonical domains
only (an earlier draft shipped both menus — caught at dry-run, fixed before any spend).

## Output + authority
`governance/anchor4_domain_vote_checkpoint.jsonl`, append-only, resumable. Stamped per record: `schema_version`,
`prompt_id`, `gen_model`, `gen_temperature: 0.0`, `pipeline_commit`, `attempt`, and `authority: MACHINE-ADVISORY-ONLY`.
**No script writes `domains_final`.** D2610-v2: unanimous domain SET -> `agreed`; any disagreement or missing voter ->
ABSTAIN + `needs_review`. A missing answer is never treated as a disagreeing answer (BUG-435).

## Status at this receipt (commit 51d905c)
- rows voted: **7/150** | pair agreed: **2** | abstain/needs-review: **5**
- ETA ~1–2 h at 6 workers; resumable — rerun the same command and it continues, retrying only rows with an errored voter
- monitor: `python3 scripts/vote_anchor_domains.py --report` | finish: `--run --workers 6 --allow-api`

## First measured behaviour
Abstentions are GENUINE pair disagreement (R001: DeepSeek `business development / digital product / marketing &
communications` vs Qwen `digital product / marketing & communications / user experience`), not parse failures. A high
abstain share is expected — the 216 cohort ran ~81% non-agreement — which is exactly why adjudication is the owner's.

## Where the axis lands (drift guard)
The anchor's DOMAIN column belongs to **ANCHOR-3** (`governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv`), which is
FROZEN: adding `domains_machine` (machine provenance, never `_final`) or `domains_final` (owner) is an **owner-gated
append**, BUG-425. This run does NOT touch ANCHOR-3, ANCHOR-4 or any F-11 instrument.

## Sequence
1. finish the run -> 2. dispute set (abstains + rows where the pair differs from the owner's expectation) ->
3. ONE owner adjudication session -> `domains_final` -> 4. THEN the promotion write (owner depth -> ANCHOR-4, clears
BUG-431/432/433) -> 5. frontier pack once on Claude + Kimi for the depth second coder.
