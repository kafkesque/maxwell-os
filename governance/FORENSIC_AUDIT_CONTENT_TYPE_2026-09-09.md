# Forensic Audit — Content-Type Golden Set + Classification Logic
> **Date:** 2026-09-09 | **Author:** goose | **Trigger:** user "in-depth forensic audit … everything align, no mismatch/blindspot/gap/conflict/hidden error/leak/bloat/future tax"
> **Method:** cross-referenced ledger ↔ backlog ↔ final_adjudication ↔ actual FB export (parquet) ↔ source-segment store; Qwen3.8-27B local second-opinion on the 6 contested non-principle objects.

---

## Verdict up front

The **governance bookkeeping is internally consistent** (ledger 84 ↔ final_adjudication 69 ↔ backlog rank-6 97 = 84+13). But the **adjudication is INERT** — it never reaches the pipeline data, and the **"clean non-principle" pool for task (a) does not exist**. Task (a) as scoped is **BLOCKED by data quality**, not by missing effort. Details below.

---

## CRITICAL findings (cascading / block progress)

### C1 — Content-type adjudication never propagates to pipeline data
The 97 human-confirmed content_type decisions live ONLY in review-tracking artifacts:
- `governance/content_type_human_decisions.jsonl` (84)
- `config/golden/d2587_boundary_corpus.yaml` (13)
- `governance/content_type_verification_backlog.json` (97 = 84+13)

None of them are written back to the objects the pipeline actually consumes. Evidence:
- The S4 export `knowledge pipeline/parquet/fbs_export_20260902_final.jsonl` still shows **`content_type: principle`** for all 4 objects the human adjudicated to non-principle (00177→TI, 00547→PT, 00650→PT, 00934→TI).
- `config/golden/gold_frozen.yaml` and `stage4_golden_mined.yaml` have **no `content_type` field at all**.
- `scripts/apply_content_type_human_decisions.py` writes ONLY ledger + backlog (its own docstring: "Deterministic, **no DB mutation**").
- S4 routing (`pipeline/stage4_merge.py:_resolve_content_type`) reads `fb.get("content_type")` from the record itself — **not** the backlog/ledger.

**Consequence:** the next pipeline run will STILL classify everything `principle`. The entire D2587/D2596 adjudication effort is a review artifact with no runtime effect until a propagation step is built. This is the single highest-risk gap.

### C2 — No clean, genuinely-convergent non-principle positive exists to mine (task (a) is blocked)
Triangulated verdicts (human vs DeepSeek vs Qwen3.8-27B local):

| example_id | human | DeepSeek | Qwen3.8 | convergence | verdict |
|---|---|---|---|---|---|
| 00177 Basic Auth | tool_instruction | noise_drop | **tool_instruction** (high) | ⚠️ FALSE (2 files = same Parandeh book) | defensible role, broken convergence |
| 00547 OSINT Enumeration | process_template | process_template | **principle** (med) | convergent | re-adjudicate — no explicit step sequence |
| 00650 Metafont Evolution | process_template | process_template | **principle** (med) | convergent | self-identifies as "principle" in its own definition |
| 00934 Coordinate System | tool_instruction | noise_drop | **noise_drop** (high) | convergent | MISCLASSIFIED — conceptual, not a tool |
| 00668 Hetionet (PI) | process_instance | — | **process_instance** (high) | ❌ SINGLETON (origin=singleton) | clean role, wrong tier |
| 00006 Golden Ratio (GE) | growth_edge | — | **growth_edge** (high) | convergent (2 distinct books) | clean, but GE is speculative — semantic mismatch for "convergent positive" |

**Conclusion:** the two "process_template" examples are actually **principle** (Qwen3.8 + definition analysis agree). The one defensible tool_instruction (00177) is a **false-convergence**. The clean non-principle positives are either singleton (00668) or speculative (00006). **There is no clean convergent PT/TI example to inject into `stage2_fewshot_convergent.yaml`.**

---

## HIGH findings

### H1 — False-convergence bug (systematic risk)
`S4-GOLD-MINED-00177` has `is_convergent: 1`, `source_diversity: 2`, but both `source_books` are **the same book** — Alireza Parandeh, *Building Generative AI Services with FastAPI*, two file editions (z-lib + Anna's Archive). The diversity metric counts **files, not distinct works**. This is a citation-echo leak that the convergent few-shot is explicitly meant to reject (`citation_echo_detection`, `same_author_echo_negative`). Needs a distinct-author dedup in the source-diversity computation.

### H2 — Invalid `content_type: "noise"` (FIXED this session)
Two backlog rows (`00522`, `00809`) carried the non-canonical value `noise`. Root cause: S4 classifier emitted `"noise"` (model-vocabulary leak) recorded verbatim in `temp/ct818_oa_joined_partial.json`; `build_fewshot_manifest.py` also mapped `'NOISE'→'noise'`. **Fixed:** normalized → `noise_drop` in backlog (2 rows), ct818 root (2 rows), and the build script norm mapping. Backlog now has zero invalid values.

### H3 — Governance split-brain (two canonical sources, un-merged)
`human_confirmed` in the backlog = 97, but = 84 (ledger) + 13 (boundary corpus). The 13 boundary-corpus cases carry `reason: "human/adjudicator settled"` and are **not** in the append-only ledger, despite the ledger being documented as the "canonical append-only human verdicts" source. Two independent canonical truths for the same axis — a future merge/conflict hazard.

### H4 — Stale silver labels never back-propagated
`gold_frozen.yaml` for `00547` still carries `expected_classification.discipline = "information security"` (silver), while frontier Qwen3.8 adjudicated `privacy & surveillance` (high confidence, with a detailed override note). The frontier depth/discipline/domain corrections live in `p5_phase1_human_adjudication.jsonl` / `frontier69_final_adjudication.json` but were **not** written back to `gold_frozen.yaml` / `stage4_golden_mined.yaml`. Same class of gap as C1, on the depth/domain/discipline axis.

### H5 — 00934 contradictory status
Export `status: QUARANTINE` vs human `tool_instruction` vs Qwen3.8/DeepSeek `noise_drop`. Three mutually exclusive signals for one object.

---

## MEDIUM findings

### M1 — 00650 self-contradictory definition
Definition text: *"…The principle describes how a typeface can be systematically reimagined…"* — literally labels itself "principle" while adjudicated `process_template`. Qwen3.8 flagged this exact contradiction.

### M2 — 00547 over-merge (188 source segments)
The OSINT object pulls 188 segments across 4 books — a possible over-merge. Convergent FBs should come from 2+ focused clusters, not a broad topic sweep. Not fatal, but inflates the few-shot's source-noise.

---

## Verified-consistent (no action)

- Ledger (84, last-wins) ↔ `frontier69_final_adjudication.json` (69): **0 missing, 0 content_type mismatch.**
- BUG-230 re-classification (00334/00385/00495/00882 growth_edge→noise_drop) correctly recorded as 2nd ledger entries (last-wins).
- `content_types.yaml` D2587 rules + BUG-230 criterion are coherent and parse clean.
- Backlog counts recomputed consistently (97/332/13/341/26/1/217 = 1027).

---

## Fixes applied this session

1. `noise` → `noise_drop` normalization (backlog 2 rows + ct818 root + `build_fewshot_manifest.py` norm).
2. Captured Qwen3.8-27B second-opinion → `governance/qwen38_contenttype_second_opinion_2026-09-09.json`.

## NOT applied (need user decision — see instructions)

- Re-adjudication of 00547/00650 (PT→principle) and 00934 (TI→noise_drop).
- Propagation script (human decisions → FB records / gold_frozen / few-shot).
- Any few-shot injection (blocked by C2).
