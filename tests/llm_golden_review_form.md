# Maxwell v3.0 — LLM Golden Sample Review Form

**Purpose:** Scientifically and pragmatically evaluate every golden FB for content accuracy, ontological correctness, and classification precision. This form is designed to be filled by an LLM (or human) with full context provided.

**Target file:** `tests/golden_classification_edge_cases.md` — 70 FBs, 42 properties each.

---

## Instructions for the Reviewing LLM

For each of the 70 golden FBs, evaluate ALL fields below. Score each on a 0-5 scale:
- **5** = Perfect. No improvement possible.
- **4** = Good. Minor wording issues, no factual errors.
- **3** = Adequate. Correct core claim but imprecise or missing nuance.
- **2** = Problematic. Contains a factual error, ontological misclassification, or missing key constraint.
- **1** = Wrong. Core claim is incorrect, classification is wrong, or field is actively misleading.
- **0** = Missing/placeholder. Field is `[TEST CASE]` or `NULL` where content is expected.

After scoring each FB individually, complete the Aggregate Analysis section.

---

## Complete Taxonomy Reference

### Disciplines (48 — pick EXACTLY ONE per FB, D316)

```
agentic architecture, behavioral economics, cognitive science, color theory,
complex adaptive systems, composition & layout, computational geometry,
computational physics & simulation, creative coding, creative process,
cultural design, decision making, design psychology, design strategy,
design systems, emerging, game design, generative ai, generative design,
geometry & proportion, iconography, information architecture, leadership,
linguistics, machine learning, marketing, motion & time, multimodal metaphor,
narrative design, operations research, personal productivity, philosophy,
political economy, privacy & surveillance, project management,
prompt engineering, psychology, research methodology, risk management,
semiotics, social engineering, software engineering, strategic thinking,
systems engineering, systems thinking, typography, visual perception,
visual semiotics
```

### Domains (27 — pick 1-5 per FB, D150)

```
ai & agents, ml systems & infrastructure, brand identity, business development,
business operations, code & computation, computational art,
computational science & physics, creative technology, data visualization,
digital product, editorial & advertising, emerging, engineering practice,
entrepreneurship, environmental design, graphic design, illustration,
motion design, organizational behavior, packaging, research & methodology,
semiotics & communication, systems & frameworks, user experience, web & ui
```

### Depth (D2024)
```
universal    = applies everywhere, ≥3 unrelated domains
cross-domain = spans 2+ domains, bridges fields
domain       = specific to one discipline/domain
specialized  = narrow sub-field within one domain
```

### Evidence
```
cited     = grounded in source text, empirically testable
axiomatic = self-evident truth, follows from definitions
```

### Context (derived from domain signals — can be multi-select, comma-separated)
```
business  = business operations, business development, entrepreneurship, organizational behavior
design    = graphic design, brand identity, editorial & advertising, motion design, environmental design,
            digital product, illustration, packaging, web & ui, user experience, creative technology,
            data visualization
system    = systems & frameworks, code & computation, engineering practice, ai & agents, ml systems & infrastructure,
            computational science & physics, software engineering
academic  = research & methodology, semiotics & communication, computational art, philosophy
personal  = fallback when no other context matches
```

### Accessibility
```
self-evident  = immediately graspable without prerequisites
prerequisite  = requires prior concept knowledge or expert-level familiarity
```
**Derivation rule:** `prerequisite` if FB has prerequisite_fbs OR difficulty_level=expert. Otherwise `self-evident`.

### Intimacy Boundary (space routing)
```
public    = general knowledge, safe for public knowledge base
selective = requires domain literacy to apply correctly
private   = personal/confidential context (deathpectation)
```

### Provenance (C29)
```
human_verbatim            = exact human-authored text from source
llm_extracted_from_source = LLM synthesized from source material
llm_hypothesis            = LLM-generated conjecture without direct source grounding
```

---

## Classification Decision Rules (from stage4_merge.py)

### Depth ↔ Domain Count Validation
| Depth | Required Domains | Warning Trigger |
|-------|-----------------|-----------------|
| universal | ≥ 3 unrelated domains | n_domains < 3 |
| cross-domain | ≥ 2 domains | n_domains < 2 |
| domain | 1 domain | — |
| specialized | 1 domain, narrow scope | — |

### Context Auto-Derivation
Context is derived from domain membership:
- Any domain in business_signals → add "business"
- Any domain in design_signals → add "design"
- Any domain in system_signals → add "system"
- Any domain in academic_signals → add "academic"
- If no match → "personal"

### Difficulty Level
| Depth | Domain Count | Difficulty |
|-------|-------------|------------|
| specialized | any | expert |
| universal | any | beginner |
| domain | 1 | expert |
| domain | >1 | intermediate |
| cross-domain | any | intermediate |

### Accessibility
| Condition | Accessibility |
|-----------|--------------|
| Has prerequisite_fbs | prerequisite |
| difficulty_level = expert | prerequisite |
| Otherwise | self-evident |

---

## FB Review Template (copy for each of the 70 FBs)

```markdown
### FB: [TEST_ID] — [NAME]
**Group:** [L/A/B/C/D/E/F/G/H/I/J/K] | **Discipline:** [value] | **Domains:** [values]
**Depth:** [value] | **Evidence:** [value] | **Context:** [value]

---

#### A. CONTENT ACCURACY (per-field, 0-5 each)

**A1. Definition** | Score: __/5
- Core mechanism claim: [accurate/inaccurate/partially accurate]
- Is this genuinely a reusable principle, or a tool-specific instruction / fact / observation?
- Missing constraints? Overclaimed scope?
- Issues: [list or "none"]

**A2. Application** | Score: __/5
- Actionable? Would following this instruction produce the claimed outcome?
- Does the action match the mechanism described in the definition?
- Concrete enough to execute? (CRIBS: boring→concrete stake)
- Issues: [list or "none"]

**A3. Failure Mode** | Score: __/5
- Genuine failure mode or just a restatement of the definition inverted?
- Identifies a specific scenario where the principle breaks?
- Mentions tangible cost of failure? (CRIBS: boring→concrete stake)
- Issues: [list or "none"]

**A4. Elaboration** | Score: __/5
- Adds depth beyond the definition, or just rephrases?
- Edge cases covered? Unexpected implications surfaced?
- Analogies correct and illuminating? (CRIBS: confusing→analogy)
- Issues: [list or "none"]

**A5. Jargon** | Score: __/5 (N/A if NULL)
- Each term correctly defined? Any definition factually wrong?
- Are there terms in the definition/elaboration that NEED jargon entries but are missing?
- Is jargon a proper term→explanation dict, or comma-separated keywords? (ANTI-PATTERN check)
- Issues: [list or "none"]

**A6. Keywords** | Score: __/5
- Do keywords match the core concepts? Any missing key terms?
- Any keywords that are NOT actually in the FB content?
- Issues: [list or "none"]

**A7. CRIBS Gate Check**
- C (Confusing→analogy): [pass/fail/na] — [note]
- R (Repetitive→cut): [pass/fail/na] — [note]
- I (Interesting→extend only if retention): [pass/fail/na] — [note]
- B (Boring→concrete stake): [pass/fail/na] — [note]
- S (Surprising→ship): [pass/fail/na] — [note]

---

#### B. CLASSIFICATION ACCURACY (per-field, 0-5 each)

**B1. Discipline** | Score: __/5
- Assigned: [value]
- Is this the SINGLE best discipline from the 48-discipline taxonomy?
- Alternative discipline that could also fit: [value or "none"]
- Would another discipline be STRICTLY better? If yes, which and why?
- Category error? (e.g., a tool instruction classified as a principle's discipline)
- Issues: [list or "none"]

**B2. Domains** | Score: __/5
- Assigned: [values]
- Are all assigned domains genuinely spanned by this FB?
- Any domains MISSING that this FB clearly applies to?
- Any domains INCLUDED that this FB does NOT actually span?
- Domain count violates D150 (1-5 max)? [yes/no]
- Issues: [list or "none"]

**B3. Depth** | Score: __/5
- Assigned: [value]
- Domain count: [n]. Does this satisfy depth validation rules?
  - universal requires ≥3 domains. Has [n]. [pass/fail]
  - cross-domain requires ≥2 domains. Has [n]. [pass/fail]
- Is the actual conceptual scope wider or narrower than assigned?
- Issues: [list or "none"]

**B4. Evidence** | Score: __/5
- Assigned: [value]
- If "cited": does the FB reference or depend on empirical source material?
- If "axiomatic": is this genuinely self-evident from first principles?
- Edge case: could this be argued either way? [yes/no]
- Issues: [list or "none"]

**B5. Context** | Score: __/5
- Assigned: [value]
- Does context match the domain→context derivation rules?
- Any context signal missing? Any incorrectly included?
- Issues: [list or "none"]

**B6. Accessibility** | Score: __/5
- Assigned: [value]
- Can a non-expert understand and apply this FB?
- Are there genuine prerequisite concepts needed?
- Issues: [list or "none"]

**B7. Intimacy Boundary** | Score: __/5
- Assigned: [value]
- Is "public" correct, or does this require domain literacy (selective)?
- Does this contain personal/confidential material (private)?
- Issues: [list or "none"]

**B8. Provenance** | Score: __/5
- Assigned: [value]
- Is this verifiable as llm_extracted_from_source, or does it appear synthetic?
- Any signs this is llm_hypothesis (unsupported conjecture)?
- Issues: [list or "none"]

---

#### C. ONTOLOGICAL REVIEW

**C1. Is this a genuine Foundation Block?** [yes/borderline/no]
- A genuine FB describes a REUSABLE PRINCIPLE — a "what/why/when" pattern that transfers across contexts.
- NOT a tool instruction, NOT a fact, NOT an observation, NOT syntax documentation.
- If borderline: what would need to change to make it a genuine FB?

**C2. Content Type Check**
- Could this be better classified as: [FB / PT (process template) / PI (process instance) / TI (tool instruction) / GE (growth edge) / fact / meta]?
- Why?

**C3. Taxonomy Fit**
- Does this FB's discipline exist in the 48-discipline taxonomy? [yes/no]
- If "emerging": does this genuinely NOT fit any existing discipline, or is there a better match?
- Would adding a new discipline to the taxonomy be warranted for this FB?

**C4. Scope Creep Check**
- Does the definition claim universality where only domain-specific evidence exists?
- Does the application prescribe action beyond what the mechanism supports?
- Cut: what sentence or claim would you remove to tighten scope?

---

#### D. OVERALL FB SCORE

| Category | Score |
|----------|-------|
| A. Content Accuracy (avg A1-A6) | __/5 |
| B. Classification Accuracy (avg B1-B8) | __/5 |
| C. Ontological Soundness | __/5 |
| **FB TOTAL** | __/5 |

**Verdict:** [✓ ACCEPT / ⚠️ REFINE / ✗ REJECT]
- If REFINE: [specific actionable changes]
- If REJECT: [reason — wrong type, wrong classification, factual error]

---
```

---

## Aggregate Analysis (after reviewing ALL 70 FBs)

```markdown
### OVERALL STATISTICS

| Metric | Value |
|--------|-------|
| Total FBs reviewed | 70 |
| ACCEPT (score ≥ 4.0) | __ |
| REFINE (score 2.5-3.9) | __ |
| REJECT (score < 2.5) | __ |
| Mean Content Score | __/5 |
| Mean Classification Score | __/5 |
| Mean Ontological Score | __/5 |
| Mean FB Total | __/5 |

---

### CONTENT ISSUES BY FREQUENCY

| Issue Pattern | Count | Example FB IDs |
|---------------|-------|----------------|
| Definition overclaims scope | __ | |
| Application not actionable | __ | |
| Failure mode is inverted definition | __ | |
| Elaboration adds no depth | __ | |
| Jargon missing needed entries | __ | |
| Jargon contains comma-separated keywords (ANTI-PATTERN) | __ | |
| Keywords don't match content | __ | |
| CRIBS violation (specify which letter) | __ | |

---

### CLASSIFICATION ISSUES BY FREQUENCY

| Issue Pattern | Count | Example FB IDs |
|---------------|-------|----------------|
| Wrong discipline assigned | __ | |
| Better alternative discipline exists | __ | |
| Missing domain(s) | __ | |
| Extraneous domain(s) | __ | |
| Depth doesn't match domain count | __ | |
| Evidence misclassified (cited vs axiomatic) | __ | |
| Context doesn't match domain signals | __ | |
| Accessibility incorrect per derivation rules | __ | |
| Intimacy boundary too restrictive/permissive | __ | |

---

### ONTOLOGICAL ISSUES

| Issue Pattern | Count | Example FB IDs |
|---------------|-------|----------------|
| Not a genuine FB (tool instruction / fact / observation) | __ | |
| Should be PT (process template) instead of FB | __ | |
| Should be PI (process instance) instead of FB | __ | |
| "Emerging" discipline where canonical exists | __ | |
| Taxonomy gap — new discipline needed | __ | |
| Scope creep — claims universality on domain evidence | __ | |

---

### CROSS-FB ANALYSIS

**Potential duplicates** (FBs with overlapping claims):
| FB1 ID | FB2 ID | Overlap Description |
|--------|--------|---------------------|
| | | |

**Contradictory FBs** (claims that conflict):
| FB1 ID | FB2 ID | Conflict Description |
|--------|--------|---------------------|
| | | |

**Missing FBs** (concepts that SHOULD be in the golden set but aren't):
| Missing Concept | Why Important |
|----------------|---------------|
| | |

---

### TOP 10 REFINEMENTS NEEDED (prioritized by impact)

1. [FB ID] — [issue] — [proposed fix]
2. ...
10. ...

---

### TAXONOMY RECOMMENDATIONS

- Disciplines to add: [list]
- Disciplines to merge/split: [list]
- Domains to add: [list]
- Classification rules to adjust: [list]

---

### VERIFICATION PIPELINE IMPACT ASSESSMENT

After applying the refinements above:
- How many FBs would change classification? __
- How many FBs would change content? __
- Estimated Stage 5 verification pass rate improvement: __%

---

**Review completed by:** [LLM model name]
**Date:** [YYYY-MM-DD]
**Total review time:** [estimate]
```

---

## How to Use This Form

1. **Load the golden file** (`tests/golden_classification_edge_cases.md`) into context alongside this form.
2. **For each FB**, copy the review template section and fill all fields.
3. **Be specific** in issues — cite exact phrases, suggest exact replacements.
4. **Use the taxonomy reference** above for all classification judgments.
5. **Use the decision rules** above for depth/context/accessibility validation.
6. **Complete the aggregate analysis** after all 70 FBs are reviewed.
7. **Prioritize refinements** by: factual errors > ontological errors > classification errors > wording issues.

---

## Quick Reference: Most Common Errors to Catch

| Error | Example | Fix |
|-------|---------|-----|
| Tool instruction as FB | "Use Figma Auto Layout for responsive components" | Reclassify as TI or rewrite as principle |
| Fact as FB | "The sky is blue due to Rayleigh scattering" | This is a fact, not a reusable principle — REJECT |
| Jargon = keywords | `Jargon: loss aversion, prospect theory` | Must be `{"loss aversion": "explanation.", "prospect theory": "explanation."}` |
| Depth universal with 1 domain | depth=universal, domains=["code & computation"] | Either expand domains or change depth to domain |
| Cross-domain with 1 domain | depth=cross-domain, domains=["graphic design"] | Need ≥2 domains for cross-domain |
| Wrong discipline family | Software design FB classified as "design strategy" | Should be "software engineering" or "systems engineering" |
| Missing prerequisite FB | FB about "Gradient Boosting" without listing "Decision Trees" as prerequisite | Add prerequisite_fbs |
| Evidence cited without source | evidence=cited but source_books=["Golden Test Set"] | Either mark as axiomatic or provide real source |
| Context mismatch | domains=["code & computation"] but context="design" | Should be context="system" per derivation rules |
