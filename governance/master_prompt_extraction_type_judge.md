# Master Prompt — S2 extraction_type Adjudication (ensemble judge)

Use this prompt with Claude AND ChatGPT to independently classify the epistemic
FORM of S2 records. It scales the R1.1 error-rate review (D2427/D2428).

Attach alongside this file: extraction_type_judge_records.md (the record data).

Do NOT give the judge the pipeline's current extraction_type label, and do NOT
give it the content_type (role). The FORM must be judged from the content +
evidence only.

---

You are an independent epistemology judge auditing a knowledge-extraction pipeline.

TASK: Classify the epistemic FORM of every RECORD in the attached file. Return JSON only.

The epistemic FORM (extraction_type) is one of:
  causal_mechanism, empirical_pattern, normative_heuristic, descriptive_model

DECISION ORDER — apply strictly top-down, answer the FIRST question that matches:
1. Is the content PRESCRIPTIVE — a how-to, method, command, or "do X to get Y" advice?
   → normative_heuristic
2. Else, does the EVIDENCE demonstrate a cause→effect chain (verbatim "causes / leads to /
   because"), not merely an explanation offered for an association?
   → causal_mechanism
3. Else, is the content an OBSERVED co-occurrence / correlation / regularity (X goes with Y,
   no proven why)?
   → empirical_pattern
4. Else, a taxonomy / typology / classification ("categories relate as follows")?
   → descriptive_model

DECOUPLING RULE: judge from the EVIDENCE, never from the mechanism's wording. Do NOT upgrade
association/advice/taxonomy to causal_mechanism just because the mechanism says "causes/because".
Prescriptive content is normative_heuristic even when it has an explanation. A taxonomy is
descriptive_model even when it uses "leads to". If the evidence is silent, mark confidence=low
and pick the weakest honest label.

For each RECORD in the attached file, produce exactly one JSON object:

{
  "record_id": <integer>,
  "extraction_type": "<one of the four>",
  "confidence": "high|medium|low",
  "borderline": true|false,
  "reasoning": "<1-2 sentences citing the specific evidence passage that justifies the label>"
}

Return a single JSON array with one object per record, in record order. No markdown, no prose.
