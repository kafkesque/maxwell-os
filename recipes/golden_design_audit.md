# Golden PT: Design Audit
# Authority: tests/golden_pt_body.md (Canonical PT Body Format — May 19 AGREED-TEMPLATES)
#            handoff/MAXWELL-OS-SKILL-ORCHESTRATION-SPEC-v1-2026-07-04.md §5.4 (PI Schema)
# Updated: D782-T5 — realigned to canonical ZONE format + Decision Matrices + PI execution fields
**Type:** Goose Recipe (P4-T5, D782)
**Status:** SCAFFOLD — awaiting Maxwell D-5 design input
**Purpose:** First end-to-end skill orchestration proof: PT → FB retrieval → execution → log

---

ZONE 1 - RELATIONS

status: draft
discipline: Design Strategy
evidence: cited
depth: domain
domains: graphic design, UI/UX, brand identity
source: (pending — Maxwell D-5 input)
fb_query_domain: graphic design, UI/UX, brand identity
fb_query_intent: design principles; heuristic evaluation; accessibility audit; brand consistency; visual hierarchy; color theory; typography

---

ZONE 2 - BODY

🔥 TRIGGER
  When a design asset (URL, screenshot, or description) is submitted for audit, and the agent is invoked manually or on a recurring schedule.

🔧 PREREQUISITE
  Design asset accessible (URL, screenshot, or detailed description). FB index pre-built for target domains (graphic design, UI/UX, brand identity). `tools/mcp_fb_server.py` running with loaded index.

📋 PHASES

  Phase 1: Intent Extraction

    Step 1 [Required] Parse the design asset to identify design principles in play (typography, color, layout, hierarchy, accessibility, brand consistency).
      → Grounded in: FB retrieved by intent "design principles typography color layout hierarchy"
      → Gate: At least 3 design principles identified from the asset

    Step 2 [Required] For each identified principle, formulate an intent_text for FB retrieval.
      → Grounded in: FB retrieved by intent "design principle intent formulation"
      → Gate: Each principle → one intent_text, min 3 intent_texts

    🚧 GATE → Phase 2
      Decision Matrix:
      ┌──────────────────────────────────────────┬──────┬──────┐
      │ Criterion                                │ Pass │ Fail │
      ├──────────────────────────────────────────┼──────┼──────┤
      │ ≥3 design principles identified          │  ✅  │      │
      │ Each principle → intent_text             │  ✅  │      │
      │ FB retrieval domain specified            │  ✅  │      │
      ├──────────────────────────────────────────┼──────┼──────┤
      │ Overall                                  │ PASS │      │
      └──────────────────────────────────────────┴──────┴──────┘

  Phase 2: FB Retrieval

    Step 3 [Required] For each intent_text, query FBs from the knowledge base.
      → Grounded in: FB retrieved by intent from mcp_fb_server.py (fb_query_domain scoped)
      → Gate: All intent_texts return ≥1 FB each (min 3 FBs total)

    Step 4 [Required] For each retrieved FB, apply the principle to the design asset.
      → Grounded in: FB principles from Phase 2 retrieval
      → Gate: Every FB either confirmed, violated, or skipped with reason

    🚧 GATE → Phase 3
      Decision Matrix:
      ┌──────────────────────────────────────────┬──────┬──────┐
      │ Criterion                                │ Pass │ Fail │
      ├──────────────────────────────────────────┼──────┼──────┤
      │ All intent_texts returned FBs            │  ✅  │      │
      │ Each FB outcome logged                   │  ✅  │      │
      │ No unhandled intent_texts                 │  ✅  │      │
      ├──────────────────────────────────────────┼──────┼──────┤
      │ Overall                                  │ PASS │      │
      └──────────────────────────────────────────┴──────┴──────┘

  Phase 3: Report Generation

    Step 5 [Required] Aggregate all FB execution logs into a structured audit report.
      → Grounded in: FB retrieval + outcome logs from Phase 2
      → Gate: Report contains applied principles, violated principles, and recommendations

    Step 6 [Optional] Generate visual summary (pass/fail heatmap by design dimension).
      → Gate: Visual generated OR skip logged

    🚧 GATE → DONE
      Decision Matrix:
      ┌──────────────────────────────────────────┬──────┬──────┐
      │ Criterion                                │ Pass │ Fail │
      ├──────────────────────────────────────────┼──────┼──────┤
      │ Report generated                         │  ✅  │      │
      │ Applied principles with citations        │  ✅  │      │
      │ Violated principles with evidence        │  ✅  │      │
      │ Recommendations documented               │  ✅  │      │
      ├──────────────────────────────────────────┼──────┼──────┤
      │ Overall                                  │ PASS │      │
      └──────────────────────────────────────────┴──────┴──────┘

---

ZONE 3 - DONE

📦 OUTPUT
  Structured audit report containing: (a) design principles identified with FB citations, (b) principles confirmed in the design, (c) principles violated with specific evidence, (d) actionable recommendations grouped by severity/domain.

✅ DONE CONDITION
  Audit report generated with ≥3 principles checked, each with confirmed/violated outcome and FB citation. Report includes recommendations section.

🔍 EVIDENCE ATTRIBUTION (PI failure analysis — maps to fb_executions.attribution)
  - context_mismatch: FB principle applies to different design domain than current asset (e.g., typography principle used for layout audit)
  - evidence_degradation: FB source evidence outdated for current design medium (e.g., print design principle for digital asset)
  - synthesis_failure: Multiple FBs returned for same principle, cannot be coherently combined
  - model_error: LLM failed in principle extraction, FB retrieval, or gate evaluation

📊 PI RELIABILITY (maps to fb_executions table — SPEC §5.4)
  Each FB consultation logs: fb_canonical, pt_name="Design Audit", pi_id=<UUID>, step_order, outcome, attribution, agent_notes
  Outcome enum: FB_VALID | FB_IRRELEVANT | FB_CONTRADICTED | FB_INSUFFICIENT | MODEL_ERROR
  Reliability score = valid_count / total_executions per FB (auto-computed)

---

## Test Case
**Input:** Screenshot of a landing page
**Expected:** 5-10 design principles identified, each matched to 1-3 FBs, audit report generated

## TODO (Maxwell D-5)
- [ ] Select specific design audit type (heuristic, accessibility, brand consistency?)
- [ ] Define output format (markdown report, Anytype page, both?)
- [ ] Determine if this should be a recurring PT or one-shot
- [ ] Wire into Goose recipe system if different from manual invocation
