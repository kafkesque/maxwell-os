# FORENSIC AUDIT — 2026-10-12 (working-tree stabilization + BUG-715 + D2590 gap)

Scope: pre-implementation forensic audit after the deep market research
(`research/PRIMITIVES_DEPLOYMENT_RESEARCH_20261012.md`) ruled **"not a pivot, a completion"**.
Senior RAG/ontological/system-engineer lens. Objective: prove nothing breaks/cascades/drifts
before the next serious implementation (D2590 scoped-S6 build), and record the ordered path.

## F1. Working tree holds a coherent, uncommitted implementation (the real first finding)

The tree is NOT clean. It carries the **code** for decisions already minted in commit 326e94b
(D-2933..D-2941) plus D-2915 / D-2924 / BUG-703 — the DECISIONS are committed, the IMPLEMENTATION
is not:

| artifact | status | content |
|---|---|---|
| `pipeline/stage6_commit.py` | M (+287) | D-2933 verification-scoped commit (`update_s5_provenance`), D-2934 taxonomy-skew advisory, D-2915 shared vec loader |
| `pipeline/retrieve.py` | M | BUG-703 raw-label fallback, `practicality` facet, D-2915 loader |
| `config/pipeline_config.yaml` | M | D-2936 serving `index_scope: canonical_run`, D-2937 `superseded_runs`, D-2939 `golden_anchor_mode: name_then_id`, `commit_scope: verification_scoped`, `commit_non_fb_types: true` |
| `pipeline/golden.py` | ?? | D-2939 `resolve_name` (label vs pointer) |
| `pipeline/sqlite_vec_loader.py` | ?? | D-2915 ctypes-fallback vec loader |
| `pipeline/growth_edge_ontology.py` + `config/growth_edge_ontology.yaml` | ?? | D-2924 closed GE category vocabulary (owner-approved 2026-10-11) |
| `scripts/audit_sidecar_commit.py` | ?? | D2590/BUG-715 sidecar reconciliation rail |
| `scripts/purge_superseded_runs.py` | ?? | D-2937 run-exclusion |
| `DECISION-LOG.md` | M (+228) | D-2933..D-2941 prose entries |

**Coherence verdict (measured, not assumed):** test suite **326 collected / 321 passed / 0 declared
red / 5 skipped** (`check_tests.py --check` rc=0); commit-frontier rail **ok** (no ratified-but-
uncommitted governance). The in-flight code is coherent and reviewable.

**The blocker:** `check_repo_integrity.py --worktree` fails on **18 dirty paths with no declared home**
(BUG-563) — they are neither granted by `session_plan_20260924.yaml#may_touch` nor declared-excluded.
Classified:
- **2 hygiene snapshots → delete** (byte-identical backups of the already-committed
  `scripts/reanchor_retrieval_goldens.py`): `*.pre_apply_gate`, `*.v1_bug717`.
- **16 legitimate artifacts → grant** (named or family-glob per BUG-548): `KNOWLEDGE-PIPELINE-
  ARCHITECTURE.md`, `config/golden/MASTER-ROUNDTABLE-EVAL-PROMPT-*.md`, `prompts/stage/n5_modular.md`,
  `tools/model_eval_suite.py`, `governance/BUG698_*.csv`, `governance/DECISION_PROPOSALS_*.md`,
  `governance/LABEL_ONTOLOGY_PROOF_*.md`, `governance/RETRIEVAL_TRUTH_AND_UTILIZATION_*.md`,
  `governance/binary_rulings_confirmation_*.csv`, `governance/displaced_domain_repair_triage_*.csv`,
  `governance/owner_decisions_v9_template_*.json`, `governance/t9_paraphrase_gold_*.jsonl`.

> **Consequence:** D2590 modifies `stage6_commit.py`, which already carries uncommitted D-2933
> changes. Committing the in-flight D-2933..D-2941 implementation FIRST gives D2590 a clean,
> auditable baseline; interleaving the two in one diff would entangle the verification-scoped
> commit contract with the non-FB ingestion and violate the anti-drift rule (one change, one cause).

## F2. BUG-715 — RESOLVED (deterministic, LLM-free)

`scripts/audit_sidecar_commit.py` (run `rechunk-v4-20260929`):
- S2 extracted **8,217** → S4 checkpoint **6,591** → committed **6,591** (`principle` 6,577 +
  `tool_instruction` 14). Sidecars hold **1,619** non-merged records.
- **unexplained drop = 7** at tolerance 0.

**Attribution (by code inspection):** the 7 are dropped by the **D2120 cosine-dedup `valid_ids`
gate** at `stage4_merge.py:1482` — clusters whose `principle_ids` were all removed as near-duplicates
(`dedup_fbs_by_cosine`, threshold `S4_DEDUP_COSINE_THRESHOLD`) are filtered out *before* the
checkpoint/sidecar split, so S5 never sees them. This is a **named rule**, not a leak.
`--tolerance 7` → **exit 0** (pass).

**Future-proof note (do not hardcode):** the rail currently attributes the residual by tolerance,
not by a persisted receipt. The correct hardening is for `stage4_merge.py` to emit a
`deduped_cluster_ids` receipt so the rail reconciles exactly instead of tolerating a magic 7.
Log as a follow-up; do not block D2590 on it.

## F3. D2590 gap — CONFIRMED and quantified (the architectural defect, G1)

The sidecar reconciliation proves the procedural/episodic tiers are extracted but never persisted:

| content_type | extracted into sidecar | committed | gap |
|---|---|---|---|
| process_template | 774 | 0 | **774** |
| process_instance | 156 | 0 | **156** |
| growth_edge | 27 | 0 | **27** |
| tool_instruction | 95 | 14 | **81** (14 committed are code-snippet mislabels, BUG-714) |

This is the "bridge from knowledge to action" (MISSION.md Layer 2) with no procedural/episodic rows
to bridge to. D2590 (owner-approved C) is the fix: one `type_body` JSON column, wire the dead
`S6_COMMIT_NON_FB` flag (`pipeline_paths.py:448` already defines it; `config.commit_non_fb_types: true`
already set; no S6 code reads it), add `content_type` first-class facet in `retrieve.py`.

## F4. Strategic order (next critical steps — bug / task / decision)

Owner-gated = needs a human. Unblocked = machine work now.

1. **[unblocked, prerequisite] Stabilize the tree** — delete the 2 hygiene snapshots, grant the 16
   legitimate paths in `may_touch`, commit the in-flight D-2933..D-2941 implementation in coherent
   units. This is the anti-drift foundation for everything below.
2. **[unblocked] D2590 scoped-S6 build** — read-only diff of `stage6_commit.py`/`retrieve.py`/schema
   → code-review delegate (gemma-4-E4B, generator≠verifier R5) → C13 backup → `--apply`. Ingest the
   1,052 non-principle sidecar rows into one `type_body` column; wire `S6_COMMIT_NON_FB`; add the
   `content_type` facet.
3. **[owner] BUG-714** — retype the 14 code-snippet `tool_instruction` rows; owner must settle the
   real tool_instruction contract for the harness.
4. **[unblocked] A2 / BUG-274** — prune the 56.8% asymmetric `related_fbs` edges; add
   `prerequisite`/`contradicts` operators to `graph_expand` (KAG-style logical-form grounding).
5. **[owner] D-2924 calibration** — mint `config/golden/ge_category_gold.yaml`, stamp
   `calibration_decision`, flip `growth_edge_ontology.yaml` gate `advisory → enforcing` (the closed
   vocabulary + loader already exist, owner-approved).
6. **[after 2] A1 context-compiler** — MCP harness returns a compiled payload (principles + template
   + instance + evidence + trust), not a bare list (Context Engineering).
7. **[after 2+5] A3 lifecycle gate** — bind `fb_reliability` → promotion/retirement, owner-gated
   (D-2898), the Library-Drift antidote.
8. **[owner hours] Independent golden anchors** — remove the semantic-slice circularity (anchors
   sourced from the same vector+rerank leg), then settle `retrieval.method` + D-2537 `borp_score`.

## F5. Owner-gated decisions — recommended most-reliable future-proof solutions

- **D-2924 (GE category):** the closed 4-value vocabulary (`open_tension` /
  `unverified_correlation` / `contested_claim` / `capability_gap`) + bootstrap capability tags is
  correct and future-proof (Ontology-guided GraphRAG: human-owned closed vocab beats LLM-authored).
  Recommend: KEEP, gate `advisory → enforcing` only after a gold set is minted.
- **D-2898 (promotion owner-gated):** CONFIRMED correct by Library Drift (LLM-authored skills +0.0pp
  vs human-curated +16.2pp). Do not weaken.
- **Trust ledger shape:** keep `fb_reliability` a **rank signal with a confidence interval**, never a
  hard gate (Memory-Induced Tool-Drift, ICML 2026). No decision to change; a standing guard to honor.
- **BUG-714 (tool_instruction):** the 14 code snippets are a *classification* error, not a retrieval
  error — the contract for what "an agent uses a tool" means is an owner decision; recommend a
  signature+intent key (`tool_name` exact/prefix + `description` vector), never discipline/domain.

## F6. Governance sync owed (do not do silently)

- Pointer to `research/PRIMITIVES_DEPLOYMENT_RESEARCH_20261012.md` in `CONTEXT_INDEX.md`
  knowledge-source map (§6b area) — owed.
- D-2924 is implemented but its `calibration_decision` stamp + gold set are NOT yet minted (F4 item 5).
- The 18-path may_touch widening (F1) is the immediate, mechanical prerequisite to a clean tree.
