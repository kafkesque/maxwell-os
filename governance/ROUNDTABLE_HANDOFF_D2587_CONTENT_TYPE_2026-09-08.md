# LLM ROUNDTABLE HANDOFF — D2587 CONTENT-TYPE CLASSIFICATION LOGIC

> **Prepared:** 2026-09-08 · **Repo:** `github.com/kafkesque/maxwell-os` · **Branch:** `main`
> **Audience:** Claude + ChatGPT, each as an independent **S-tier senior knowledge-architecture + RAG engineer**.
> **Mandate:** Do NOT rubber-stamp. The change below is a foundational ontology edit that governs
> the classification of **~10,000 extracted objects**. Evaluate whether the applied changes are
> reasonable and valid; whether they carry **future tax**; whether the logic has **blindspots, gaps,
> or conflicts**; and whether there is **object-type drift risk** (labels silently migrating between
> content-type buckets). Provide constructive observations and recommendations.
> **Reference commit:** pushed with this file. Ground truth = `config/content_types.yaml`,
> `config/decisions.yaml` (D2587), `pipeline/content_types.py`, `pipeline/stage2_extract.py`,
> `pipeline/stage4_merge.py`.

---

## 0. What Maxwell OS is (one paragraph)

A sovereign, local-first ($0 marginal cost) knowledge pipeline: books → Foundation Blocks (FBs) →
verified, retrievable principles for agentic RAG. 8 stages: `0 Convert → 0.5 Metadata → 1 Chunk →
1.3 Prefilter → 1.5 Embed/Cluster → 2 Convergent Extract → 4 Merge/Classify → 5 Verify → 6 Commit`
(Stage 3 removed, D2120/D2198). ~7,995 FBs committed.

**The problem being fixed:** every FB in the DB carries `content_type='principle'` (7,995/7,995 —
a **vacuous axis**). Measurement (2026-09-08, full 818-row frontier triage) found the *true*
non-principle rate is ~15–19%: the S2 extractor's few-shot set contained **zero** non-principle
examples (`config/golden/stage2_fewshot_convergent.yaml`, 84 examples: 59 `principle`, 23
hard-negatives, 0 PT/PI/GE/TI), so the model defaulted everything to `principle`. This is a
supervision-gap, not an extraction-quality defect — the repair is label-level, not a re-extraction.

---

## 1. The applied change (D2587) — what was edited

Three user-clarified classification rules, encoded in `config/content_types.yaml` as a new
`content_type_rules` block + two description annotations + `process_template.min_steps: 2`:

**Q1 — process_template is a SEQUENCE, never a single step.**
> A process_template requires **≥2 steps** (phases + at least one gate or a done condition).
> A single step/instruction is NOT a template. Single-step resolution:
> - tool/software-specific → `tool_instruction`
> - transferable (passes the depth test: one sentence, acts as a filter across 3+ domains) → `principle`
> - method/domain-bound step → an inline step (fragment), never a standalone object

**Q2 — a decision matrix is NEVER a standalone content type.**
> - specific scoring grid for one gate → inline content in a PT's gate (the `steps`/decision field)
> - reusable matrix methodology → `principle` or `process_template` by the depth/sequence test

**Q3 — instruction-vs-principle is decided by the depth test, not by whether the text prescribes.**
> A single transferable prescriptive claim (a normative heuristic that can be stated in one sentence
> and act as a filter across 3+ domains) is a **PRINCIPLE** (`extraction_type` stays
> `normative_heuristic`), NOT a process_template. This reverses the burden: the original sweep
> defaulted "prescriptive → template", which over-assigned `process_template`.

**Measured consequence of the change** (re-triage of the 65 affected rows with the D2587 rules in
the prompt): **31 of 51 process_template flags flipped back to `principle`**; 1 → `process_instance`;
the 818-pool non-principle rate corrected from 19.0% → **14.9%**. It also flipped 8 of the 14
human-calibrated `process_template` few-shot rows to `principle` (including 4 the human had earlier
personally re-typed to PT: 00548, 00668, 00971 → principle; 00713 → growth_edge) — a direct
collision with prior human disposition, flagged for re-confirmation, NOT silently overwritten.

---

## 2. Questions for the auditors

Answer each with: **Verdict** (sound / partially-sound / unsound + confidence), **findings**
(numbered, severity-tagged 🔴/🟠/🟡, each with the repo file that would confirm it), and
**constructive recommendations**.

### Q2.1 — Are the three rules (Q1/Q2/Q3) reasonable and valid?
- Is "≥2 steps" the right boundary for process_template, or does it introduce a new ambiguity
  (e.g. a 2-step micro-method vs a genuine multi-phase procedure)? Is the step-count the right
  discriminator, or is the *gate/done-condition* the real signal?
- Is the depth test ("one sentence + filter across 3+ domains") a sound discriminator between
  principle and process_template, or does "3+ domains" collapse for genuinely single-domain
  knowledge (e.g. a medical principle that only applies in health & medicine)?
- Is "decision matrix = inline, never standalone" consistent with the rest of the ontology, or does
  it create an orphan (a reusable matrix methodology that is neither cleanly PT nor principle)?

### Q2.2 — Future tax?
- The new `content_type_rules` block and `process_template.min_steps` are **currently dormant**:
  no code reads them (`pipeline/content_types.py` loads only `content_types`, `extraction_types`,
  `route_to_content_type`, `content_to_extraction_type`, `dropped_content_types`,
  `s2_body_fields`). Is a config-only rule that no validator enforces a future-tax (the rule and
  the enforcement drift apart), or is config-as-documentation acceptable here?
- The D2587 Q3 rule says a `normative_heuristic` can be a `principle`, but
  `content_to_extraction_type.principle = descriptive_model` (the weakest-honest default, D2417)
  pins principle to `descriptive_model` only. **Is this a live conflict** (the two sources of truth
  disagree), or is the `content_to_extraction_type` map only a conflation-rescue default that does
  not constrain the Q3 case?

### Q2.3 — Blindspots, gaps, conflicts in the logic?
- The 5 content-type roles (principle / process_template / process_instance / tool_instruction /
  growth_edge) vs the 4 extraction_type forms (causal_mechanism / descriptive_model /
  normative_heuristic / empirical_pattern) are declared orthogonal (D2323), but
  `content_to_extraction_type` is a many-to-one default map. Where does the orthogonality actually
  break, and which content_type×extraction_type cells are unassigned or contradictory?
- BUG-148: the S2 `route` field is stale/uniform `'FB'` on ALL 2,878 records, and
  `pipeline/pipeline_paths.py` gates S2 route values to `["FB","NULL"]` — but
  `route_to_content_type` maps 5 values (FB/PT/PI/GE/TI). Is this a hidden third source of drift
  (the route gate, the route→type map, and the content_type rules now disagree about what S2 can emit)?
- Is `growth_edge` (the empirical-pattern / speculative bucket) correctly bounded, given Q3 now
  funnels single prescriptive claims into `principle`? Is there a risk of *growth_edge* becoming the
  new "everything that isn't obviously a clean principle" catch-all (the same failure mode that made
  `principle` vacuous)?

### Q2.4 — Object-type drift risk?
- With 3 rules now (step-count, depth-test, matrix-inline) and no enforcement code, what is the
  concrete failure mode where labels silently migrate bucket→bucket over future re-runs?
- Does the D2587 re-triage (31 PT→principle flips) signal that the *frontier classifier itself*
  needs the rules embedded in its prompt (rather than relying on a human to re-adjudicate each time)?
- What guardrail (validator, freeze-time schema check, prompt-injection of the rules) would you
  put in place to make the classification stable and non-drifting?

### Q2.5 — Constructive recommendations
- Ranked, concrete: (a) should the dormant rules be wired into a validator, and where
  (`pipeline/content_types.py` loader + `audit_content_type_contract.py`)? (b) should
  `content_to_extraction_type` be widened to a many-to-many map (or explicitly re-scoped as
  "rescue-default only") to resolve the Q3 conflict? (c) how should the 4 colliding human
  dispositions (00548/00668/00971/00713) be adjudicated under the new rules?

---

## 3. Known drift I self-corrected before this handoff (transparency)

During this session's edits, `config/decisions.yaml` was initially re-serialized with
`yaml.safe_dump`, which reflowed the whole file (4,899 → 7,043 lines) and changed `last_sync` from
ISO `'2026-09-06T09:16:00Z'` to a bare date. This was reverted and D2587 was re-applied as a
surgical 13-line append; `last_sync` restored to ISO format; `total_decisions` + `summary` block
re-synced via `scripts/recompute_decision_summary.py`. The auditors are asked to confirm the final
state is drift-free (run `scripts/recompute_decision_summary.py` and
`scripts/audit_content_type_contract.py`).

---

## 4. Deliverable format (required)

For each of Q2.1–Q2.5 return:
1. **Verdict** (one line + confidence).
2. **Findings** (numbered, 🔴/🟠/🟡, each citing the confirming repo file).
3. **Recommendations** (ranked, concrete, with the exact file/field to change).

Keep it under ~2,500 words. Prefer falsifiable claims ("the rule breaks for X because the file Y
says Z") over generalities.
