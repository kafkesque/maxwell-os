# MASTER REVIEW PROMPT — S2 Content-Type Strategy (3-Bucket Collapse)

> **Purpose:** This is a self-contained brief you (the reviewing LLM) are asked to
> evaluate. Paste the ENTIRE document into any capable LLM (Claude, ChatGPT, Gemini,
> etc.). Do not truncate. The proposition under review is stated in §5; the context
> needed to judge it is §1–§4. Your instructions are §6.

---

## §1 — WHAT MAXWELL OS IS (context you must hold while judging)

Maxwell OS is a **sovereign knowledge operating system**. It runs entirely on local
hardware (an M1 Max 64GB), uses local LLMs, costs $0 marginal, and never sends data to
the cloud. Its stated mission (MISSION.md):

> "AI agents are everywhere — but they're ungrounded. They hallucinate. They can't cite
> sources. Maxwell OS exists to solve this: **a sovereign system that extracts
> convergent, verified knowledge from the world's best books, tests every principle
> against reality through real execution, and renders that knowledge as executable
> skills that cite their sources.**"

**The four layers:**

| Layer | Name | Status |
|-------|------|--------|
| L0 | Pipeline — 8-stage extraction (books → principles → FBs → SQLite) | built |
| L1 | Knowledge — SQLite + Parquet + FTS5 + hybrid search + reliability scores | in progress |
| L2 | Orchestration — FB → PT → PI → Recipe → Trust Ledger (**"THE PRODUCT"**) | not built |
| L3 | Business ops — automated trigger→retrieve→execute→verify loops | future |

**The critical product thesis (verbatim from MISSION.md):**

> "Layer 2 is the product. ~7,300 lines of pipeline code produce FBs. 0 lines of
> agentic orchestration code turn FBs into executable skills. The bridge from knowledge
> to action IS the product."

**Non-negotiable constraints (CONSTITUTION §0):** $0 marginal cost (C1); sovereign,
no cloud (C3); no vendor lock-in, open formats, multiple model families (C2/C4);
Generator ≠ Verifier, different model families (R5); temp=0.0 on all generation (R7);
every object stamped with schema_version/gen_model/pipeline_commit (R14); NEVER
hardcode any value — config-first (C12); swappable infrastructure behind protocols
(C21); zero future tax — every decision leaves a migration path (C27); lightweight by
default, bloat is opt-in (C28).

**The FB → PT → PI → Recipe chain (D2072, the Layer-2 spine):**

| Object | Definition |
|--------|-----------|
| **FB** (Foundation Block) | atomic verified principle — "why/when something works" |
| **PT** (Process Template) | repeatable how-to method with steps, citing FBs as ground truth |
| **PI** (Process Instance) | one execution of a PT — evidence "has this worked?" |
| **Recipe/Skill** | PT + cited FBs → executable agent skill |

---

## §2 — THE ONTOLOGY UNDER REVIEW (D2323, D2072)

The system formalized a **two-axis** content taxonomy (D2323, `config/content_types.yaml`):

- **content_type** = functional ROLE — 5 values:
  `principle`, `process_template`, `process_instance`, `tool_instruction`, `growth_edge`
- **extraction_type** = epistemic FORM — 4 values:
  `causal_mechanism`, `empirical_pattern`, `normative_heuristic`, `descriptive_model`

Each content_type has a rich, type-specific schema in `config/content_types.yaml`
(extension_fields) AND a matching Pydantic model in `pipeline/schemas.py`:

- **principle**: application, failure_mode, procedural_skill, prerequisite_fbs,
  contradicts_fbs, related_fbs, context, accessibility, intimacy_boundary, provenance,
  source_text, difficulty_level, temporal_scope, confidence_score
- **process_template**: steps, trigger, prerequisite, done_condition, failure_mode,
  template_source, consulted_fbs, fb_query_domain, fb_query_intent
- **process_instance**: parent_pt_id, instance_text, actors, outcome_metric,
  outcome_qualitative, domain_context
- **tool_instruction**: 13-field MCP/JSON-Schema/OpenAPI/man-page-grounded schema
  (tool_name, platform, description, syntax, parameters, output, example, annotations,
  caveats, version, source, alternatives)
- **growth_edge**: body, source, category, actionable, status, parent_fb_ids,
  parent_pt_id, promoted_to_type, promoted_to_id, promoted_at, tags, priority

The shared core body (all types) is: name, definition, mechanism, boundary,
consequence, elaboration (+ S4-appended application/failure_mode/jargon).

---

## §3 — THE GROUND-TRUTH FINDING (verified against real code + a real run)

A full 940-book run (run-id `t11`) completed Stage 2 extraction over **13,899
clusters** in ~32h. The accounting:

| Population | Count |
|---|---|
| FBs extracted | 2,878 |
| Summary-gated (discarded) | 9,950 (9,900 single-source + 50 convergent) |
| Schema-failed | 183 (100% single-source; 0 convergent) |
| NULL | 888 |
| Singletons (never processed) | 35,122 viable |

Three concrete findings were verified directly:

1. **The 5 type-specific schemas are NEVER populated by any pipeline stage.** A grep
   across every pipeline file for `ProcessTemplate(`, `ToolInstruction(`, `.steps`,
   `.syntax`, `.parameters`, `parent_pt_id`, `outcome_metric`, `done_condition` returns
   **zero hits outside `schemas.py` itself**. The Pydantic models exist; nothing
   instantiates them. S2 emits the SAME generic FB body (name/definition/mechanism/
   boundary/consequence/elaboration) for all 5 content_types, differing only in the
   `content_type` label string.

2. **Summary-gate blindness (BUG-146).** 71.6% of all targets were discarded by a gate
   `if is_summary and gate_enabled: skip`. The `is_summary` flag was defined for the
   CONVERGENT tier as "true only if you can only restate without a convergent
   mechanism" — but single-source clusters *by construction* have no convergent
   mechanism, so the model honestly flags `is_summary=true` and the gate discards
   genuine single-source principles, methods, tool commands, and case studies.

3. **Taxonomy conflation (BUG-145).** 180 of the 183 failures were the model writing a
   content_type value (`tool_instruction`, `process_template`) into the extraction_type
   field, which fail-closed validation correctly rejected.

A sampled audit of the 9,900 gated single-source clusters found ~35% held genuine
principles, ~20% held process templates/tool instructions/case studies, and only
~35–40% were correctly skippable factual description.

---

## §4 — THE DATA-CORPUS REALITY

The corpus is **predominantly conceptual/design/psychology/philosophy**, NOT tool
documentation. The highest-volume source books in the gated population are: *The Black
Swan*, *Gödel Escher Bach*, *Antifragile*, *No Logo*, *Meggs' History of Graphic
Design*, *Maps of Meaning*, *Man and His Symbols*, *The Gutenberg Galaxy*. Tool/
software-command content is a thin tail.

---

## §5 — THE PROPOSITION UNDER REVIEW

A single architect proposed the following recovery strategy for the single-source +
singleton tail of the run:

**A. Collapse 5 content types → 3 buckets (one extractor, one pass):**

| Bucket | Keep? | Rationale |
|--------|-------|-----------|
| **principle** | ✅ ship | core product, corpus's strength |
| **process_template** | ✅ ship | subsumes `tool_instruction` (a TI is a PT scoped to one tool); adds ONE free-text `steps` field + an `example` field |
| **growth_edge** | ✅ ship | speculation quarantine, cheap |
| ~~process_instance~~ | ❌ demote | fold into PT as `example` evidence, not a standalone indexed object |
| ~~tool_instruction~~ | ❌ subsume | into process_template; strict 13-field MCP schema deferred to Layer 2 |

**B. The soft schema:** shared body (name/definition/mechanism/boundary/consequence/
elaboration + extraction_type + content_type) plus exactly ONE bucket-specific free-text
field per non-principle type. No strict parameter/outputSchema — those are Layer-2
tool-binding concerns, not Layer-1 knowledge-retrieval concerns.

**C. Fix `elaboration`:** the single-source prompt currently omits `elaboration` (only
the convergent prompt asks for it). Add it.

**D. Fix the gate:** `is_summary` redefined for single-source ("true only if pure
factual description with no extractable object of any kind") + content_type-aware gate.

**E. Targeted rerun:** re-extract the 183 failed (auto via resume) + the ~9,900 gated
(via a `--reprocess-gated` flag) + skip NULL + **defer the 35,122 singletons to a
separate T1.2 tail pass**. Bump `max_workers` 3→6 (LLM-bound, 36GB free).

**F. Claimed net effect:** instead of 5 hollow types, 3 full ones; every object carries
a complete body + the one bucket-specific field that makes it retrieval-useful.
`process_instance`/`tool_instruction` become evidence inside `process_template`, not
orphaned labels.

---

## §6 — YOUR REVIEW INSTRUCTIONS

Evaluate §5 strictly and adversarially. You are a **senior systems architect, RAG
engineer, and software engineer**. Address ALL of the following:

1. **Logic & correctness.** Is the collapse 5→3 logically sound? Are there errors or
   unsupported leaps in the reasoning chain from §3's findings to §5's proposal?

2. **RAG value.** For a *knowledge-retrieval* product (Layer 1), are principle /
   process_template / growth_edge the right retrieval units? Is demoting
   process_instance to "evidence" and subsuming tool_instruction into process_template
   defensible, or does it lose retrieval-relevant information?

3. **Alignment with Maxwell OS's purpose, ambition, and goal.** Does §5 advance or
   undermine the stated product thesis — "Layer 2 (FB → PT → PI → Recipe) is THE
   product"? Specifically: does deferring the strict PT/PI/TI schemas to Layer 2
   *contradict* D2072/D2323, or *correctly sequence* them?

4. **Future-proofing (C27 "zero future tax").** Does the 3-bucket soft schema leave a
   clean migration path to the full 5-type strict schema later, or does it paint into a
   corner (e.g., lose the PI→PT link, or make TI un-promotable to MCP tools)? Is there a
   risk that re-extraction under a 3-bucket prompt makes the corpus IRRECOVERABLE if the
   strict 5-type ontology is later wanted?

5. **Constitutional compliance.** Does §5 violate any constraint in §1 — especially
   C12 (config-first), C27 (zero future tax), C28 (lightweight default), C21
   (swappable infrastructure), R5 (Generator≠Verifier), R14 (stamping)?

6. **The singleton deferral.** Is deferring 35,122 singletons to a separate pass sound,
   given they are the highest tool-command density but lowest per-object value? Or is
   that a loss that should not be deferred?

7. **What would you change?** Give a concrete, ranked list of (a) things you'd keep,
   (b) things you'd change, and (c) risks/edge cases the proposition missed.

**Format:** Verdict first (APPROVE / APPROVE-WITH-CHANGES / REJECT), then answers to
1–7. Be concrete and cite which part of the proposition each judgment refers to. If you
reject, state the minimal alternative that would earn approval.
