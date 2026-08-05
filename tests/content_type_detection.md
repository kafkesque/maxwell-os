# Maxwell v3.0 — Content-Type Detection Test Set
# Tests that the classifier correctly identifies PT, TI, PI (not FBs)
# Generated: 2026-07-27 | 3 cases
**FB START**
**FB_ID:** 8b4ce9e0e87503ac
**NAME:** Five-Step Design Sprint Protocol
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** Execute a design sprint in five days: Monday-map the problem, Tuesday-sketch solutions, Wednesday-decide on approach, Thursday-prototype, Friday-test with users. Each day has specific activities and timeboxes that must be followed for the sprint to produce valid results.
**APPLICATION:** ⚠️ PROCESS TEMPLATE, NOT FB. Use the 5-day sprint protocol when solving a defined problem with a cross-functional team. Day 1: map the problem. Day 2: sketch solutions. Day 3: decide on approach. Day 4: prototype. Day 5: test with users. Each day's output is the next day's input — don't compress. Don't skip days.
**FAILURE_MODE:** ⚠️ PT, not FB. The team compresses the sprint into 2 days by combining mapping and sketching. The map is shallow. The sketches are obvious. The decision is premature. The prototype tests the wrong assumption. The sprint produces a validated solution to the wrong problem. The 5-day structure exists because each step requires incubation time between sessions.
**ELABORATION:** ⚠️ PT, not FB. This is a Process Template: a repeatable HOW-TO method. PTs answer how do I execute this process? FBs answer what principle governs this domain? The Design Sprint is a method for applying design principles. It is not itself a principle. The test case exists to verify the classifier routes PTs to process_template, not FB.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** design strategy
**DISCIPLINE_RAW:** design strategy
**DOMAINS:** digital product, user experience
**DOMAINS_RAW:** digital product, user experience
**DEPTH:** domain
**EVIDENCE:** cited

# ── v1 Anytype (space routing + provenance) ──
**CONTEXT:** design
**ACCESSIBILITY:** self-evident
**INTIMACY_BOUNDARY:** public
**PROVENANCE:** llm_extracted_from_source

# ── Agentic Metadata (D2130) ──
**DIFFICULTY_LEVEL:** intermediate
**TEMPORAL_SCOPE:** timeless
**PREREQUISITE_FBS:** []
**PROCEDURAL_SKILL:** NULL
**CONTRADICTS_FBS:** []
**RELATED_FBS:** []

# ── Verification (Stage 5) ──
**CONFIDENCE_SCORE:** [TEST CASE]
**CLASSIFICATION_ERRORS:** NULL

# ── Source Provenance ──
**SOURCE_CLUSTERS:** ["golden-test"]
**SOURCE_BOOKS:** ["Golden Test Set"]
**SOURCE_PRINCIPLE_IDS:** []
**SOURCE_TEXT:** Execute a design sprint in five days: Monday-map the problem, Tuesday-sketch solutions, Wednesday-decide on approach, Thursday-prototype, Friday-test with users. Each day has specific activities and timeboxes that must be followed for the sprint to produce valid results.

# ── Jargon (term→explanation, NEVER comma-separated keywords) ──
**JARGON:** NULL

# ── Utilization ──
**USAGE_COUNT:** 0
**FEEDBACK_SCORE:** NULL
**FEEDBACK_COUNT:** 0

# ── Stamps (R14) ──
**SCHEMA_VERSION:** 2026-07-27.D2131
**GEN_MODEL:** gemma-4-E4B-it-MLX-4bit+CRIBS
**PIPELINE_COMMIT:** golden-test-set-cribs
**TAXONOMY_VERSION:** v3.0-golden

# ── Test Metadata ──
**TEST_ID:** G01_process_template_type
**TEST_PROPERTY:** process template (HOW-TO) classified correctly
**TEST_DESCRIPTION:** FB is a HOW-TO process, not a principle
---FB END---

**FB START**
**FB_ID:** 389e4e5952c99656
**NAME:** Figma Auto-Layout Nesting Strategy
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** Figma's auto-layout can be nested up to 5 levels deep to create responsive components that adapt to content changes. The key pattern is: outermost frame for page structure, middle frames for sections, innermost frames for individual UI elements with hug contents enabled.
**APPLICATION:** ⚠️ TOOL INSTRUCTION, NOT FB. In Figma, nest auto-layout up to 5 levels deep: outermost for page structure, middle for sections, innermost for content. Beyond 5 levels, Figma performance degrades. Use absolute positioning sparingly within auto-layout frames — it breaks the responsive flow.
**FAILURE_MODE:** ⚠️ TI, not FB. The designer nests auto-layout 8 levels deep. Figma's renderer chokes — the component takes 3 seconds per change. The designer blames Figma. Every additional auto-layout level adds a layout recalculation pass. 5 levels = 5 passes. 8 levels = 8 passes. The tool documented the limit. The designer exceeded it.
**ELABORATION:** ⚠️ TI, not FB. This describes HOW to use a specific tool feature (Figma auto-layout). Tool instructions belong in documentation, not a knowledge base. The test case verifies the classifier correctly identifies TIs and routes them to tool_instruction content_type, not FB.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** graphic design
**DISCIPLINE_RAW:** graphic design
**DOMAINS:** digital product, creative technology
**DOMAINS_RAW:** digital product, creative technology
**DEPTH:** specialized
**EVIDENCE:** cited

# ── v1 Anytype (space routing + provenance) ──
**CONTEXT:** design
**ACCESSIBILITY:** self-evident
**INTIMACY_BOUNDARY:** public
**PROVENANCE:** llm_extracted_from_source

# ── Agentic Metadata (D2130) ──
**DIFFICULTY_LEVEL:** expert
**TEMPORAL_SCOPE:** timeless
**PREREQUISITE_FBS:** []
**PROCEDURAL_SKILL:** NULL
**CONTRADICTS_FBS:** []
**RELATED_FBS:** []

# ── Verification (Stage 5) ──
**CONFIDENCE_SCORE:** [TEST CASE]
**CLASSIFICATION_ERRORS:** NULL

# ── Source Provenance ──
**SOURCE_CLUSTERS:** ["golden-test"]
**SOURCE_BOOKS:** ["Golden Test Set"]
**SOURCE_PRINCIPLE_IDS:** []
**SOURCE_TEXT:** Figma's auto-layout can be nested up to 5 levels deep to create responsive components that adapt to content changes. The key pattern is: outermost frame for page structure, middle frames for sections, innermost frames for individual UI elements with hug contents enabled.

# ── Jargon (term→explanation, NEVER comma-separated keywords) ──
**JARGON:** NULL

# ── Utilization ──
**USAGE_COUNT:** 0
**FEEDBACK_SCORE:** NULL
**FEEDBACK_COUNT:** 0

# ── Stamps (R14) ──
**SCHEMA_VERSION:** 2026-07-27.D2131
**GEN_MODEL:** gemma-4-E4B-it-MLX-4bit+CRIBS
**PIPELINE_COMMIT:** golden-test-set-cribs
**TAXONOMY_VERSION:** v3.0-golden

# ── Test Metadata ──
**TEST_ID:** G02_tool_specific_instruction
**TEST_PROPERTY:** tool-specific instruction — still classifiable
**TEST_DESCRIPTION:** FB describes a specific tool feature, not a general principle
---FB END---

**FB START**
**FB_ID:** ffa3431ff51ea401
**NAME:** Netflix Personalization at Scale
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** Netflix's recommendation engine processes 100M+ user profiles using collaborative filtering combined with content-based features. The key architectural insight: thumbnail personalization (showing different artwork to different users for the same title) drove more engagement improvement than algorithm accuracy gains.
**APPLICATION:** ⚠️ PROCESS INSTANCE, NOT FB. Study Netflix's personalization architecture as a case study: 1) Collaborative filtering for taste clustering. 2) Content-based features for cold start. 3) Thumbnail personalization for engagement lift. Apply the architecture pattern (not the specific implementation) to any recommendation system with >1M users.
**FAILURE_MODE:** ⚠️ PI, not FB. A startup copies Netflix's exact architecture for their 50,000-user app. The infrastructure cost exceeds their entire engineering budget. Netflix's architecture is optimized for 100M users — the distributed systems overhead negligible at that scale dominates at startup scale. Copying the implementation without understanding scale assumptions is the failure mode.
**ELABORATION:** ⚠️ PI, not FB. This is a Process Instance: a concrete case study. PIs ground FBs in real-world evidence. The FB would be Personalization Architecture Scales with User Base — the principle Netflix's case demonstrates. The PI is the evidence. The FB is the principle. Confusing them means treating one company's implementation as a universal pattern.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** ai engineering
**DISCIPLINE_RAW:** ai engineering
**DOMAINS:** ai & agents, digital product, user experience
**DOMAINS_RAW:** ai & agents, digital product, user experience
**DEPTH:** domain
**EVIDENCE:** cited

# ── v1 Anytype (space routing + provenance) ──
**CONTEXT:** design, system
**ACCESSIBILITY:** self-evident
**INTIMACY_BOUNDARY:** public
**PROVENANCE:** llm_extracted_from_source

# ── Agentic Metadata (D2130) ──
**DIFFICULTY_LEVEL:** intermediate
**TEMPORAL_SCOPE:** timeless
**PREREQUISITE_FBS:** []
**PROCEDURAL_SKILL:** NULL
**CONTRADICTS_FBS:** []
**RELATED_FBS:** []

# ── Verification (Stage 5) ──
**CONFIDENCE_SCORE:** [TEST CASE]
**CLASSIFICATION_ERRORS:** NULL

# ── Source Provenance ──
**SOURCE_CLUSTERS:** ["golden-test"]
**SOURCE_BOOKS:** ["Golden Test Set"]
**SOURCE_PRINCIPLE_IDS:** []
**SOURCE_TEXT:** Netflix's recommendation engine processes 100M+ user profiles using collaborative filtering combined with content-based features. The key architectural insight: thumbnail personalization (showing different artwork to different users for the same title) drove more engagement improvement than algorithm accuracy gains.

# ── Jargon (term→explanation, NEVER comma-separated keywords) ──
**JARGON:** NULL

# ── Utilization ──
**USAGE_COUNT:** 0
**FEEDBACK_SCORE:** NULL
**FEEDBACK_COUNT:** 0

# ── Stamps (R14) ──
**SCHEMA_VERSION:** 2026-07-27.D2131
**GEN_MODEL:** gemma-4-E4B-it-MLX-4bit+CRIBS
**PIPELINE_COMMIT:** golden-test-set-cribs
**TAXONOMY_VERSION:** v3.0-golden

# ── Test Metadata ──
**TEST_ID:** G03_case_study_narrative
**TEST_PROPERTY:** case study with embedded principle
**TEST_DESCRIPTION:** FB is primarily a case study with embedded principle
---FB END---
