# Maxwell OS v3.0 — Schema & Pipeline-State Audit Prompt
## For Frontier LLM Evaluators (S-tier, cross-family red-team)

**Authority:** D2334–D2336 (commits `9295ce0`, `14a9efa`) · D2323 content-type ontology
**Date:** 2026-08-13
**Requested by:** human operator — wants an independent, adversarial audit before any schema is integrated into `config/content_types.yaml` + `pipeline/schemas.py`.
**You are being asked to verify, not to agree.** Do not rubber-stamp.

---

## ⚠️ EPISTEMIC DISCIPLINE (non-negotiable — read this first)

You are an **S-tier senior RAG engineer, software engineer, knowledge architect, and agentic engineer** — four hats, one critical review.

1. **Do NOT assume. VERIFY.** Every factual claim you make MUST be traceable to a file you actually read (cite `file:line` or `file → section`).
2. **Do NOT invent.** If a file does not support a claim, write **`UNVERIFIED`** and stop. A plausible-sounding assertion with no source is a failure, not a finding.
3. **Be meticulous.** Distinguish what you *verified* from what you *inferred*. Mark every inference `[inferred]`.
4. **If a file is missing or you cannot resolve a reference, say so explicitly.** Do not paper over gaps.
5. **Mention your own uncertainty.** Where a judgment is architectural (not checkable), label it `[judgment]` and give your reasoning, not a bare verdict.
6. **No hallucinated benchmarks.** When comparing to a peer solution, you may only assert facts about that solution you can defend; if you do not know its exact schema/version, say `UNKNOWN-version` and argue from its *documented public* properties only.

---

## TOKEN-EFFICIENT READ MAP (read ONLY these, in this order)

Do NOT read the whole repo. The repo has ~7,300+ lines of pipeline code and a 697KB archived decision log. Reading broadly wastes your context and is explicitly discouraged.

**READ (in order):**

1. `CONSTITUTION.md` — single source of truth (§2 pipeline, iron rules C1–C28, R5/R7/R14).
2. `MISSION.md` — mission, ambition, purpose, 4 layers, competitive moat, kill criteria.
3. `config/content_types.yaml` — D2323 ontology (the file this audit will change). **Read in full.**
4. `config/taxonomy_v5.yaml` — canonical domain/discipline labels (skim the enum lists only).
5. `config/pipeline_config.yaml` — thresholds, model routing, `run_id`, `convergent_ratio`.
6. `config/model_assignments.yaml` — generator vs verifier routing (R5).
7. `pipeline/schemas.py` — all Pydantic contracts (the other file this audit will change). **Read in full.**
8. `pipeline/content_types.py` — how config enums are loaded into code (verify C12 config-first).
9. `pipeline/stage2_extract.py` — read **only** the fail-closed block (~lines 1580–1603) and the few-shot `format_golden_fewshot()`.
10. `pipeline/stage4_merge.py` — S4 classification/routing (who writes `content_type`, `route`, `intimacy_boundary`).
11. `pipeline/stage5_verify.py` — S5 verification (BORP + NLI + LLM) → `verification_status`.
12. `pipeline/stage6_commit.py` — SQLite/Parquet commit + `pipeline_run_id` scoping.
13. `pipeline/feedback.py` — the feedback loop primitive (`FeedbackRecord`).
14. `pipeline/stamp.py` — R14 provenance stamps + `get_pipeline_run_id()`.
15. `governance/buglog.md` — open bugs (BUG-094, BUG-053, DELEGATE-001, etc.).
16. `governance/domain_labelling.md` — raw-label preservation (G9).
17. `DECISION-LOG.md` — **grep only** for: `D2323`, `D2128`, `D2150`, `D2334`, `D2335`, `D2336`. Do NOT read the whole file.

**FOR v1/Anytype/MOC parity (archive — only if you need historical evidence):**

18. `archived/maxwell os/archive/moc-template-locked-v2.md` — MOC template v2.2 + status/zone semantics.
19. `maxwell os/tools/render_zone.py` — Zone 1/2/3 body renderer + `_evidence_display()` mapping.
20. `maxwell os/tools/push_anytype.py` — v1 Anytype property surface (status/depth/evidence/intimacy/subtype/layer).
21. `maxwell os/tools/schemas.py` — v1 `FoundationBlock` (29-field) schema.

**DO NOT READ / SKIP:** `probe_output/`, `temp/`, `data/`, `archive/` (except the 4 files above), `books/`, `.mypy_cache/`, any `*.bak`, `knowledge pipeline/` checkpoints, old `quarantine/` FBs, `logs/`.

---

## GROUND TRUTH A — MISSION & AMBITION (condensed, verify against MISSION.md)

- **Why it exists:** "a sovereign system that extracts convergent, verified knowledge from the world's best books, tests every principle against reality through real execution, and renders that knowledge as executable skills that cite their sources."
- **Four layers:** L0 Pipeline (built) → L1 Knowledge (in progress) → **L2 Orchestration (the product: FB→PT→PI→Recipe→Trust Ledger)** → L3 Business Ops.
- **The one thing that matters:** Layer 2 is the product. ~7,300 lines produce FBs; 0 lines turn FBs into executable skills. "Build the bridge."
- **Five competitive moats:** (1) convergent extraction (BORP + clustering), (2) execution-based reliability (`fb_reliability`), (3) sovereign stack ($0 marginal, local-only), (4) self-evolving taxonomy, (5) dogfooding.
- **Non-negotiable constraints:** C1 $0 marginal · C3 sovereign · C2/C4 future-proof · R5 generator≠verifier · R7 temp=0.0 · R14 every object stamped.

---

## GROUND TRUTH B — CURRENT PIPELINE STATE (the audit target)

**Pipeline (8 stages — stage3/HDBSCAN removed per D2120/D2198):**

```
S0 convert → S0.5 metadata → S1 chunk → S1.3 prefilter → S1.5 embed+cluster
→ S2 extract (Qwen3-Coder) → S4 merge+classify (GPT-OSS) → S5 verify (DeBERTa NLI) → S6 commit (SQLite+Parquet)
```

**Latest e2e result (verify `/tmp/e2e_run2.log` if available, else `governance/SESSION-HANDOFF-2026-08-13-FINAL.md`):**

```
✅ S0→S1.5 all pass (847s)
❌ S2 extract — 2502s, rc=1 — D2331 fail-closed: failed_clusters/total > S2_MAX_FAILED_RATIO
   (87 FBs extracted before OMLX cluster-call failures near end of run)
⛔ halted at S2. 8/9 stages passed.
```

**Known open defects (verify against buglog):** `route:"FB"` vs `content_type:"process_template"` contradiction (D2128 gap) · `ToolInstruction` has a D2323 contract but **no Pydantic class** · PT/TI emitted as raw S2 dicts missing per-type fields + classification + linkage · `pipeline_run_id` lineage was fixed (D2335) but S2 OMLX reliability is the active blocker.

**Models (local):** generator `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit`, verifier `gpt-oss-20b-MXFP4-Q8`, NLI `DeBERTa-v3-large`, embeddings `bge-m3`.

---

## GROUND TRUTH C — PROPOSED SCHEMA (the evaluation target)

This is the **trimmed** schema from the operator's prior analysis. It is the candidate for integration. Evaluate it as-is.

### C.1 Shared core (all 6 types: principle, process_template, process_instance, tool_instruction, growth_edge, moc)

```yaml
identity:      [id, name, content_type, extraction_type, object_version]
stamps (R14):  [schema_version, gen_model, pipeline_commit, pipeline_run_id, created_at, updated_at]
classification:[domains[], discipline, depth, evidence(cited|axiomatic|experiential), domains_raw[], discipline_raw]
lifecycle:     [status(draft|stable|deprecated), superseded_by, last_verified]   # is_active = derived, not stored
routing:       [intimacy_boundary, accessibility, context]
feedback:      [usage_count, last_retrieved_at, feedback_score, feedback_count]
graph:         [prerequisite_ids[], contradicts_ids[], related_ids[]]            # no per-edge scores (recomputed)
verification:  [verification_status, needs_human_review, verifier_model, confidence_score]
```

### C.2 Per-type extensions

| Type | Extension fields |
|---|---|
| **principle (FB)** | definition, application, failure_mode, elaboration, keywords, jargon, source_text, difficulty_level, temporal_scope, procedural_skill |
| **process_template (PT)** | steps, trigger, prerequisite, done_condition, failure_mode, template_source, consulted_fbs[], fb_query_domain, fb_query_intent, parent_project |
| **process_instance (PI)** | parent_pt_id, instance_text, actors, outcome_metric, outcome_qualitative, domain_context |
| **tool_instruction (TI)** | tool_name, platform, description, syntax, parameters[], output, example, annotations, caveats, version, source, alternatives[], prerequisite_fbs[] |
| **growth_edge (GE)** | body, source, category, actionable, workflow_status(open→…→archived), parent_fb_ids[], parent_pt_id, promoted_to_type/id/at, tags[], priority |
| **moc** | moc_type, skill_id, discipline, framework, cluster, triggers[], key_failure_modes[], foundation_blocks[], contains_units[], fb_count, status |

### C.3 Key design decisions baked into this schema (challenge each one)

1. **Lifecycle `status` is 3-state** (`draft/stable/deprecated`); `active` is **derived** (`usage_count ≥ threshold`) not stored.
2. **`evidence` restores the 3rd tier `experiential`** (v1 had cited/axiomatic/experiential; current v3 code dropped it to cited/axiomatic).
3. **`intimacy_boundary` moves to shared core** (currently FB-only; PT/PI/GE/TI lack it; GE is user-created → private-by-default).
4. **`ToolInstruction` needs a Pydantic class** (contract exists in D2323, class does not).
5. **`subtype`, `domain_knowledge`, `classification_version/method` are deliberately NOT restored** (superseded by `content_type`, `depth`/`discipline`, and R14 stamps respectively).
6. **MOC is a derived navigation hub** (store spine: skill_id/triggers/foundation_blocks/contains_units; render prose on demand, drop `### Phase N:` heading parsing).
7. **Feedback → status promotion is deterministic** (no LLM at runtime): feedback_score + feedback_count + usage_count + verification_status → draft/stable/deprecated.

---

## VALIDATION INSTRUMENT — Constitution-Gated Checklist

Before judging the schema on the SMART rubric, run it through this deterministic checklist (each row = read the cited rule, check the schema, record PASS/FAIL/UNVERIFIED):

| # | Gate | Check | Evidence source |
|---|---|---|---|
| 1 | C12 config-first | Every new enum/threshold lives in `config/*.yaml`, never hardcoded in `pipeline/*.py` | `config/content_types.yaml`, `pipeline/content_types.py` |
| 2 | R14 lineage | Every type stamped `schema_version/gen_model/pipeline_commit/pipeline_run_id` | `pipeline/schemas.py`, `pipeline/stamp.py` |
| 3 | C3/C22 sovereignty | `intimacy_boundary` on ALL types; GE private-by-default; no field forces cloud/API | `MISSION.md`, `config/pipeline_config.yaml` |
| 4 | C10 structural validity | All status/enum values are Pydantic `Literal`, not free strings | `pipeline/schemas.py` |
| 5 | R5 cross-family | Verifier (gpt-oss) ≠ generator (Qwen3-Coder) for the fields that need verification | `config/model_assignments.yaml` |
| 6 | D2323 two-axis | content_type (role) ≠ extraction_type (form); no re-conflation | `config/content_types.yaml` |
| 7 | D2128 route gap | `route` → `content_type` mapping closed; no `route:"FB"` + `content_type:"process_template"` contradiction | `config/content_types.yaml` §route_to_content_type |

---

## EVALUATION RUBRIC — SMART

For **each** of the 6 dimensions below, produce a SMART verdict. SMART = **S**pecific claim, **M**easurable threshold, **A**chievable with the cited evidence, **R**elevant to Maxwell OS mission, **T**ime-bound to commit `14a9efa` (2026-08-13). Do not write a generic essay — fill in each element.

### 1. VALID — is the schema internally correct?
- **Specific:** no field contradictions; all enums closed and match config literals; every type Pydantic-representable; D2323 two-axis preserved; route→content_type gap closed.
- **Measurable:** 0 contradictions found · 100% enum values in `config/content_types.yaml` · every new type constructible by its Pydantic class (or a missing class explicitly flagged) · D2128 mapping yields no contradiction on real S2 output.
- **Achievable:** diff proposed fields vs `pipeline/schemas.py` + `config/content_types.yaml`; inspect actual `knowledge pipeline/stage4_merge/*.jsonl` for the `route`/`content_type` contradiction.
- **Relevant:** an invalid schema breaks S4/S5/S6 silently.
- **Time-bound:** against the schema as written above, commit `14a9efa`.

### 2. VIABLE — can it be built on the current stack?
- **Specific:** every new field has a producer stage (S2/S4/S5/S6) and a consumer; no field requires non-local capability; feedback→status promotion is deterministic (no runtime LLM).
- **Measurable:** 100% of new fields mapped to an existing stage + script · 0 new external dependencies · promotion rule expressible in pure Python/SQL.
- **Achievable:** map each C.2 field to the stage that emits it (e.g., `intimacy_boundary` → S4, `last_verified` → S5, `feedback_score` → `pipeline/feedback.py`).
- **Relevant:** an unviable schema is dead weight (the prior `ProcessInstance` class is already dead — no emitter).
- **Time-bound:** implementable in the current codebase without new infra.

### 3. DESIRABLE — does it advance the mission?
- **Specific:** each decision advances ≥1 moat (BORP-verified, fb_reliability, sovereign, self-evolving taxonomy, executable skills).
- **Measurable:** score coverage 0–1: map each of the 7 C.3 decisions to the moat(s) it serves; flag any decision serving none.
- **Achievable:** moats are enumerated in `MISSION.md`; decisions are enumerated in C.3.
- **Relevant:** Layer 2 (bridge knowledge→action) is the product filter — judge especially whether lifecycle status + intimacy + TI class *enable the bridge*.
- **Time-bound:** against `MISSION.md` Phase 0–1 success criteria (e.g., "PT cites ≥5 verified FBs", "fb_reliability updates after PI execution").

### 4. RESILIENT — does it survive failure without data loss?
- **Specific:** no new silent-error path (C16); promotion idempotent + re-runnable; feedback ledger append-only + crash-safe (C6); lineage survives partial run.
- **Measurable:** 0 new `except: pass` · status promotion is monotonic-safe + re-runnable · feedback writes via tempfile→fsync→`os.replace` · no field whose loss breaks R14 lineage.
- **Achievable:** compare against `pipeline/io_guard.py`, `pipeline/stamp.py`, and the C6/C16/C23 rules.
- **Relevant:** resilience is a moat claim; the live failure is S2/OMLX reliability — state whether the schema makes that better/worse/neutral.
- **Time-bound:** under documented failure modes (OMLX timeout, OOM, partial checkpoint).

### 5. FUTURE-PROOF — swappable, no lock-in, no dead ends?
- **Specific:** every new field survives model/vendor/OS swap; open formats (SQLite+Parquet); enums in YAML; protocol-first; migration path exists.
- **Measurable:** 0 vendor-specific types/values · 100% storage in SQLite+Parquet · 0 hardcoded thresholds in code · each field has a documented replacement path (see MISSION.md swappable-layers table).
- **Achievable:** check C2/C4/C21/C22/C27 + the swappable-layers table.
- **Relevant:** future-proofing is the structural moat.
- **Time-bound:** no new field that hard-codes a provider or model family.

### 6. COMPETITIVE — does it hold up vs S-tier / peer-reviewed solutions?
- **Specific:** compare the schema against solutions with a similar use case (verified knowledge extraction + executable skills + sovereign agent memory). Candidate targets: **Microsoft GraphRAG**, **OpenSPG/KAG**, **LlamaIndex + RAGAS**, **MemGPT/Letta**, **Zep**, **mem0**, **W3C PROV-O** (provenance), **SKOS/OWL** (taxonomy), **MCP** (tool-instruction contract), **Anytype/Obsidian/Notion/Tana/Logseq** (PKM object models), **Zettelkasten/PARA/MOC** (navigation).
- **Measurable:** for each target, rate **weaker / parity / stronger** on ≥3 axes (grounding, reliability feedback, sovereignty, schema strictness). **Every comparison must be sourced or marked `UNKNOWN-version`** — no unsourced superiority.
- **Achievable:** argue from each target's *documented public* schema only; flag where you lack the exact spec.
- **Relevant:** competitiveness is the go/no-go (MISSION.md kill criteria: "would you pay £500+?").
- **Time-bound:** competitive as of 2026-08-13; note if a target's current version is unknown to you.

---

## HARD CONSTRAINTS (from CONSTITUTION.md — verify, then honor)

- **C1** $0 marginal cost — all generation local. **C3** sovereign — no cloud, no egress. **C22** API opt-in explicit, `verify_always_local` constitutional.
- **R5** Generator ≠ Verifier (different model family). **R7** temp=0.0. **R14** every persistent object stamped.
- **C12** config-first — no magic values in code. **C16** no silent errors. **C6** crash-safe writes. **C21** swappable infra behind protocols. **C23** resilient by design. **C27** zero future tax.

---

## OUTPUT FORMAT (required)

Produce, in this exact order:

1. **VERIFICATION LOG** — a table of every ground-truth claim you checked: `claim | verdict (VERIFIED / UNVERIFIED / CONTRADICTED) | evidence (file:line)`. If >30% of your checked claims are UNVERIFIED, say so and explain why (you may have been pointed at a wrong path — report that back).

2. **CONSTITUTION-GATED CHECKLIST** — the 7-row table above, each row PASS/FAIL/UNVERIFIED + one-line evidence.

3. **SMART RUBRIC** — 6 dimensions, each with the 5 SMART elements filled in and a single **PASS / FAIL / REVISE** verdict.

4. **TOP FINDINGS** — the 5 highest-signal issues (bugs, contradictions, overengineering, or gaps), ranked by risk, each with evidence.

5. **RECOMMENDATION** — one of: **INTEGRATE AS-IS / INTEGRATE WITH CHANGES (list them) / DO NOT INTEGRATE (why)**. Be explicit about what you would change and what you would delete as overengineering.

6. **UNKNOWN / RISK REGISTER** — everything you could not verify and everything you believe the schema still gets wrong.

**Length discipline:** favor evidence density over prose. Tables over paragraphs. If a claim is not verifiable, it is cheaper to write `UNVERIFIED` than to speculate.
