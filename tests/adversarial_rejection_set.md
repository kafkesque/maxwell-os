# Maxwell v3.0 — Adversarial Rejection Test Set
# Tests that classifier rejects vacuous/empty/tautological inputs
# Generated: 2026-07-27 | 2 cases
**FB START**
**FB_ID:** 6e52364d9aeafb83
**NAME:** Things Change Over Time
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** All systems, organisms, and organizations undergo change as time progresses. Understanding that change is inevitable allows for better preparation and adaptation strategies in any context.
**APPLICATION:** Build change detection into every long-term plan. Schedule a quarterly assumption review: list the 3 core assumptions underlying your strategy. Score each 1-5 on confidence. Any assumption below 3 triggers a contingency plan. The plan that doesn't account for its own assumptions being wrong is a wish, not a plan.
**FAILURE_MODE:** The executive team writes a 5-year strategy assuming stable market conditions. Year 2: a competitor launches a category-defining product. Year 3: a regulatory change invalidates the pricing model. The strategy is abandoned. No contingency plans exist because the assumptions were never explicit. The failure wasn't that things changed — it was that the strategy assumed they wouldn't.
**ELABORATION:** Things change is true and useless. The value is in operationalizing it: which things might change, how fast, what's the detection mechanism, what's the response. Without specificity, embrace change is a bumper sticker. With specificity, it's a risk management framework. The difference is the difference between a fortune cookie and a strategy.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** strategic thinking
**DISCIPLINE_RAW:** strategic thinking
**DOMAINS:** business operations
**DOMAINS_RAW:** business operations
**DEPTH:** universal
**EVIDENCE:** axiomatic

# ── v1 Anytype (space routing + provenance) ──
**CONTEXT:** business
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
**SOURCE_TEXT:** All systems, organisms, and organizations undergo change as time progresses. Understanding that change is inevitable allows for better preparation and adaptation strategies in any context.

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
**TEST_ID:** F01_overly_generic_principle
**TEST_PROPERTY:** overly generic principle — should still classify
**TEST_DESCRIPTION:** FB is so generic it could fit almost anywhere
---FB END---

**FB START**
**FB_ID:** b91550cdc514f74b
**NAME:** The Undefined Principle
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** 
**APPLICATION:** ⚠️ TEST CASE — no definition exists. In production: if a definition is empty after extraction, mark the FB as needs_human_review and skip classification. Never classify an undefined concept. The absence of content is information about pipeline health, not a content failure.
**FAILURE_MODE:** The pipeline classifies an FB with an empty definition. The classifier hallucinates a discipline based on the name alone. The Undefined Principle gets classified as strategic thinking because the name sounds strategic. The classification is plausible and completely wrong. An empty definition should produce no classification — fail closed.
**ELABORATION:** This is a pipeline robustness test. Real pipelines encounter empty fields from parsing errors or upstream failures. Correct behavior: fail-closed — if content is missing, don't guess. Mark for review. Incorrect behavior: fail-open — classify anyway and produce plausible-sounding but groundless output.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** emerging
**DISCIPLINE_RAW:** emerging
**DOMAINS:** emerging
**DOMAINS_RAW:** emerging
**DEPTH:** domain
**EVIDENCE:** axiomatic

# ── v1 Anytype (space routing + provenance) ──
**CONTEXT:** personal
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
**SOURCE_TEXT:** 

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
**TEST_ID:** J04_definition_is_empty
**TEST_PROPERTY:** empty definition
**TEST_DESCRIPTION:** FB has name but definition is empty — undefined concept
---FB END---
