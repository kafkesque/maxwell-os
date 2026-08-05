# Maxwell v3.0 — Parser/Schema Robustness Test Set
# Tests JSON schema resilience (string vs list, dedup, nulls, type coercion)
# Generated: 2026-07-27 | 5 cases
**FB START**
**FB_ID:** a0d6587b1b3c69a4
**NAME:** Single String Discipline Bug
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** This tests whether the validation code correctly handles discipline being returned as a plain string like 'design strategy' rather than ['design strategy'].
**APPLICATION:** Normalize discipline input at the validation boundary: if isinstance(discipline, str): discipline = [discipline]. Treat single-string and single-element-list inputs identically. Test: input 'design strategy' → output 'design strategy'. Input ['design strategy'] → output 'design strategy'. Both must produce identical downstream behavior.
**FAILURE_MODE:** The validator expects discipline as a list: discipline[0]. The LLM returns a plain string. discipline[0] returns the first character 'd' instead of 'design strategy'. The FB is rejected. The fix is one line. The bug lasted 3 sprints because the test suite only used list-formatted inputs.
**ELABORATION:** LLMs are inconsistent about returning single values as strings vs single-element lists. The validation pipeline must handle both. This is a defensive coding principle: never trust the LLM's output format. Normalize at the boundary.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** design strategy
**DISCIPLINE_RAW:** design strategy
**DOMAINS:** digital product
**DOMAINS_RAW:** digital product
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
**SOURCE_TEXT:** This tests whether the validation code correctly handles discipline being returned as a plain string like 'design strategy' rather than ['design strategy'].

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
**TEST_ID:** H01_discipline_as_string_not_list
**TEST_PROPERTY:** backward compat: discipline as string
**TEST_DESCRIPTION:** LLM may return discipline as string instead of list — parser must handle
---FB END---

**FB START**
**FB_ID:** e32546c7ee8208a5
**NAME:** Dedup Domain Test
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** Simple principle about keeping things clean and organized. Duplicate entries should be removed during validation.
**APPLICATION:** Deduplicate domain lists before validation: domains = list(dict.fromkeys(domains)). Run dedup before the D150 max-5 check and before depth derivation. A list with ['engineering practice', 'engineering practice'] must be treated identically to ['engineering practice'].
**FAILURE_MODE:** The LLM returns domains with duplicates. Without dedup, the domain count is inflated. A single-domain FB with duplicates gets classified as cross-domain because count=2. The depth and all downstream derivations (difficulty, accessibility, context) are wrong because one duplicate cascaded into 4 misclassifications.
**ELABORATION:** LLMs sometimes repeat domains when the FB heavily emphasizes one domain. The repetition means this is REALLY about engineering practice — but the taxonomy doesn't have intensity, only membership. Being extra in a domain is not a thing. Dedup is the correct normalization.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** engineering practice
**DISCIPLINE_RAW:** engineering practice
**DOMAINS:** engineering practice, code & computation
**DOMAINS_RAW:** engineering practice, code & computation
**DEPTH:** domain
**EVIDENCE:** cited

# ── v1 Anytype (space routing + provenance) ──
**CONTEXT:** system
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
**SOURCE_TEXT:** Simple principle about keeping things clean and organized. Duplicate entries should be removed during validation.

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
**TEST_ID:** H02_domains_with_duplicates
**TEST_PROPERTY:** domain deduplication
**TEST_DESCRIPTION:** LLM may return duplicate domain entries
---FB END---

**FB START**
**FB_ID:** 77f0482ea6abda60
**NAME:** Extra Fields Tolerance
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** This tests whether extra JSON fields like 'confidence' or 'reasoning' or 'related_concepts' cause validation to fail or if they are gracefully ignored.
**APPLICATION:** Parse LLM classification output by extracting only known keys: discipline, domains, depth, evidence. Ignore all other fields silently. If the LLM adds confidence, reasoning, or related_concepts fields, they must not cause a parse error. Postel's Law: be conservative in what you send, liberal in what you accept.
**FAILURE_MODE:** The parser uses a strict schema rejecting JSON with unknown fields. The LLM adds a reasoning field explaining its classification. The parser rejects the entire output. The FB fails classification not because the classification was wrong, but because the parser was stricter than the contract. The contract says return JSON with these keys — it doesn't say return ONLY these keys.
**ELABORATION:** LLMs add debugging fields, confidence scores, reasoning chains. Your parser should extract what it needs and ignore everything else. Rejecting valid output because it contains bonus information is a parser bug, not an LLM bug.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** strategic thinking
**DISCIPLINE_RAW:** strategic thinking
**DOMAINS:** business operations
**DOMAINS_RAW:** business operations
**DEPTH:** domain
**EVIDENCE:** cited

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
**SOURCE_TEXT:** This tests whether extra JSON fields like 'confidence' or 'reasoning' or 'related_concepts' cause validation to fail or if they are gracefully ignored.

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
**TEST_ID:** H03_extra_json_fields
**TEST_PROPERTY:** extra JSON fields should not break validation
**TEST_DESCRIPTION:** LLM may add unexpected fields to JSON output
---FB END---

**FB START**
**FB_ID:** d668b4f81e742881
**NAME:** Null Field Handling
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** Testing null handling in classification output. Null evidence should be treated as missing and defaulted.
**APPLICATION:** Handle null classification values with conservative defaults: null evidence → 'cited'. null depth → infer from domain count (1 domain = 'domain', 2+ = 'cross-domain'). null discipline → 'emerging'. Never crash on null. Never store null where schema requires a value. Default at the boundary.
**FAILURE_MODE:** The LLM returns evidence: null. The pipeline crashes with NoneType error on the 201st FB after processing 200 successfully. The entire batch fails. The fix: evidence = llm_output.get('evidence') or 'cited'. One line prevents a full pipeline rerun.
**ELABORATION:** Null handling is the difference between a pipeline processing 99% of FBs successfully and one that crashes on edge cases. LLMs produce nulls when uncertain. That uncertainty is information — it should trigger a default, not a crash. The default should be the most conservative value.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** strategic thinking
**DISCIPLINE_RAW:** strategic thinking
**DOMAINS:** business operations
**DOMAINS_RAW:** business operations
**DEPTH:** domain
**EVIDENCE:** cited

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
**SOURCE_TEXT:** Testing null handling in classification output. Null evidence should be treated as missing and defaulted.

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
**TEST_ID:** H04_null_values
**TEST_PROPERTY:** null field handling
**TEST_DESCRIPTION:** LLM returns null for optional fields
---FB END---

**FB START**
**FB_ID:** abd4ca1281fb5745
**NAME:** Wrong Type Depth
**STATUS:** golden-test
**FB_VERSION:** 1

# ── Content (CRIBS+BORP applied) ──
**DEFINITION:** Edge case where the LLM might hallucinate a numeric depth value or boolean instead of one of the four valid string values.
**APPLICATION:** Validate depth against the literal set ['universal', 'cross-domain', 'domain', 'specialized'] before using. If the LLM returns depth: 3 (numeric) or depth: true (boolean), reject and retry with explicit instructions. Never pass unvalidated LLM output to downstream systems.
**FAILURE_MODE:** The LLM returns depth: 2 meaning cross-domain (second option in the list). The code does if depth == 'cross-domain'. The comparison fails silently — 2 != 'cross-domain'. Depth defaults to 'domain'. The wrong depth cascades into wrong difficulty_level, accessibility, and context. One type error produces 4 downstream misclassifications.
**ELABORATION:** LLMs sometimes index into enumerated lists instead of using string values. A prompt saying 1=universal, 2=cross-domain might produce '2' instead of 'cross-domain'. The fix: validate that the value IS one of the four strings. If it's not, it's not valid depth data regardless of what it means.
**KEYWORDS:** [TEST CASE]

# ── Classification (D316: singular | D150: 1–5) ──
**DISCIPLINE:** strategic thinking
**DISCIPLINE_RAW:** strategic thinking
**DOMAINS:** business operations
**DOMAINS_RAW:** business operations
**DEPTH:** domain
**EVIDENCE:** cited

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
**SOURCE_TEXT:** Edge case where the LLM might hallucinate a numeric depth value or boolean instead of one of the four valid string values.

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
**TEST_ID:** H05_wrong_type_for_depth
**TEST_PROPERTY:** wrong type coercion for depth field
**TEST_DESCRIPTION:** LLM returns depth as a number or boolean instead of string
---FB END---
