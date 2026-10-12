# FORENSIC AUDIT — 2026-10-11 (BUG-698 gate state + R5 drift-audit + strategic order)

Scope: pre-implementation forensic audit of the unblocked critical path after owner approvals
D-2924 / D-2884(a) / D-2923. Senior RAG/ontological/system-engineer lens. Objective: prove nothing
breaks/cascades/drifts before any serious implementation, and surface every blindspot/gap/conflict/
hidden-failure/error-leak/mismatch/bloat.

## F1. Runtime (verified live, not assumed)
- OMLX UP on 11435: /health = healthy, engine_pool model_count=8, loaded_count=2.
  Catalog (auth `sk-maxwell-local`) lists all 8: Phi-4-mini-instruct-8bit,
  Qwen3-Coder-30B-A3B-Instruct-MLX-4bit, Qwen3.8-27B-MLX-4bit, gemma-4-E4B-it-MLX-4bit,
  gpt-oss-20b-MXFP4-Q8, Ornith-1.5-35B-A3B-REAP-19B, Ornith-1.5-9B-MLX-8bit, gemma-4-12B-it-qat-OptiQ-4bit.
- Ollama UP on 11434 (bge-m3 embeddings present). R5 review path + S4 classifier path unblocked.

## F2. BUG-698 --generate is COMPLETE and clean (verified against v9 menu)
- `governance/rederive_v6_worklist_20261010.json`: 194 rows, 194 unique item_ids, 0 missing fields.
- 47 distinct candidate disciplines — **0 off-menu** vs `config/closed_menu_v9.json` (64 disciplines).
- 0 off-menu candidate domains (42-domain menu).
- 163 distinct source documents; generator = gpt-oss-20b-MXFP4-Q8 (≠ second coder gemma, R5 holds).
- The "menu v6" prose in the script is vestigial: `render_menu_v6()` renders v9 via version.yaml pointer.
  Output is v9-stamped-correct; no drift in the artifact.

## F3. R5 DRIFT-AUDIT (gemma-4-E4B-it-MLX-4bit, verifier ≠ generator) — ACTIONABLE FINDING
Sampled 14 rows (6 emerging + 8 spread). Verdict:
- Non-abstention classifications: **8/8 OK** — no slope in assigned discipline/domain.
- Abstention ("emerging") behaviour: **5/6 FLAGGED as likely over-abstained**:
  - R059 → `entrepreneurship studies` (on-menu, conf .95) — structured product-launch process.
  - R061 → `organizational theory` (on-menu, conf .9) — org focus/boundary principle.
  - R127 → `design thinking` (on-menu, conf .8) — holistic design education model.
  - R051 → `urban planning` — **MENU GAP**: v9 has NO architecture/urban-planning discipline
    (closest domains only: environmental design). Legitimately `emerging` OR menu-extension candidate.
  - R067 → `interactive media` — **MENU GAP**: v9 has NO installation/interactive-media discipline
    (closest: game design / creative coding / media studies / performing arts). Same call.
- R144 → `emerging` correctly abstained (self-contained non-standard taxonomy).

Interpretation (senior lens): the classifier is NOT drifting on assigned labels; it is OVER-ABSTAINING
to `emerging`. That is a precision-preserving but recall-hurting slope: every wrongly-abstained principle
loses its canonical discipline routing facet (unretrievable under any specific discipline). Two distinct
root causes — (a) genuine fit exists but was missed (R059/R061/R127), (b) genuine MENU GAP (R051/R067).
These MUST be resolved by the OWNER at adjudication (never auto-decided, D-2839 c2).

## F4. Config consistency (no mismatch found)
- `stage4.discipline_anchor_path` STILL points at `governance/DOMAIN_RULER_FROZEN_20261008.json`
  (un-stamped DOMAIN ruler) — a KNOWN mis-pointing to revert AFTER BUG-698 --finalize. Not a new defect.
- `stage5`: nli_aggregation=or_entail_and_no_contra @ 0.5; paraphrase_path_enabled=False;
  paraphrase_entail_threshold=0.1 (D-2925, < 0.5 guard holds); paraphrase_calibration={null,null}
  (correctly fail-closed — cannot flip on until a threshold is measured).
- `config/decisions.yaml` synced: 1053 decisions under `decisions:`, no dupes (was stale at D-2916;
  D-2917..D-2925 now present).

## F5. Blindspot / circularity flag (BUG-705 gold seeding) — senior-engineer caution
The D-B spec seeds the paraphrase gold set as: recoverable-neutral (ent≥1 contra=0) → `paraphrase_true`,
PASS/contra → `non_paraphrase`. That is a NLI-structure-derived proxy, NOT independent ground truth: the
calibration then measures how well STS cosine *agrees with the NLI entail signal it is meant to correct*.
This is a mild circularity — it validates "STS correlates with NLI-entail" but does NOT independently
confirm the flipped rows are TRUE claims. Mitigation (recommended, cheap): the gold set must include a
human/LLM-labelled SAMPLE (e.g. 40–60 rows) judged on the definition↔evidence relationship itself,
not on NLI scores. Flag for the BUG-705 implementation, do NOT block the re-derive.

## F6. Hygiene flag (uncommitted deletions)
Git shows DELETED (unstaged): `governance/discipline_anchor_rederived_v6_20261006*.json` (4) and
`governance/d2767_ab_*.json` (4). These are superseded reference artifacts (v8/v9 exist). C19 requires
superseded files → `archive/`, not hard delete. Verify intent before the next commit; do not lose them.

## F7. BLOCKER map
- BUG-698: **at OWNER ADJUDICATION human gate** (--generate done). Downstream --adjudicate/--verify/
  --finalize all gated on owner decisions JSON.
- BUG-706 (3-way macro gate) + stage4 anchor re-point: BLOCKED on BUG-698 --finalize.
- BUG-701: BLOCKED on BUG-700 stable identity (owner-gated on live population).
- UNBLOCKED now: BUG-705 re-derive + calibrate; D-2924 GE gold + enforce; Stage R PT/PI/GE/TI;
  D-2923 retrieval wiring; SHACL taxonomy gate; BUG-703 discipline_raw backfill.

## STRATEGIC ORDER (next critical steps — bug/task/decision)
1. [OWNER GATE] BUG-698: adjudicate 194 rows (use F3 aid) → `--adjudicate --decisions` →
   `--verify` (second coder + DeBERTa) → `--finalize` → mint v9-stamped discipline anchor.
2. [BLOCKED on 1] BUG-706: `discipline_macro_classify.py --gate` on the v9 referee; ship 3-way macro
   iff kappa ≥ ~0.65; demote 62-way fine discipline to advisory. Then re-point
   `stage4.discipline_anchor_path` off DOMAIN_RULER_FROZEN.
3. [UNBLOCKED] BUG-705: re-derive recoverable neutral under or_entail (v9 slice) → seed gold (with the
   F5 independent sample) → `paraphrase_calibrate.py --decision D-29xx` → flip enabled → re-verify 6,591
   → re-commit → D274a serving rail (0 invariant violations).
4. [UNBLOCKED] D-2924 GE calibration: mint `config/golden/ge_category_gold.yaml`, stamp
   `calibration_decision`, flip `gate_mode` advisory→enforcing before Stage R GE volume.
5. [UNBLOCKED] Stage R: surgical typed extraction to emit PT/PI/GE/TI in volume (currently 0/0/0/14);
   gate GE emission through D-2924 loader.
6. [UNBLOCKED] D-2923 retrieval wiring: `content_type` first-class facet + per-type keys (PT=trigger+
   done_condition+fb_query_*, PI=parent_pt_id, GE=body+status, TI=tool_name+description; NEVER
   discipline/domain) + commit/index all 5 content types.
7. [BLOCKED on BUG-700] BUG-701: re-derive anchor-store bridge by source identity (not folded name).
8. [TAIL, parallel-safe] SHACL taxonomy validation gate; mission_relevance facet; BUG-703 backfill
   of 190 empty discipline_raw (deterministic, LLM-free).
