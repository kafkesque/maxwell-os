# ROUNDTABLE ADJUDICATION + MARKET RESEARCH — D2587 CONTENT-TYPE ONTOLOGY

> **Prepared:** 2026-09-08 · **Repo:** `github.com/kafkesque/maxwell-os` · **Branch:** `main`
> **Adjudicator:** goose (S-tier senior RAG engineer). **Second validator:** Qwen3.8-27B-MLX-4bit (temp=0.0, one-shot).
> **Inputs:** `temp/claude0060.md`, `temp/qwen0060.md`, `temp/chatgpt0060.md` (3 independent auditors),
> `governance/ROUNDTABLE_HANDOFF_D2587_CONTENT_TYPE_2026-09-08.md` (the handoff).
> **Method:** every material claim was re-verified against the live code by the adjudicator — **not assumed**.
> Follows the D2569 adjudicated-handoff convention (valid-claims table, corrections, rejected-claims).

---

## 0. Executive verdict (one paragraph)

**The 5-type ontology is ontologically grounded and directionally correct; the wiring is half-built, and the
D2587 rules are currently paper-only.** Four of the five types map almost 1:1 onto a mature OASIS standard
(DITA Concept/Task/Reference) and a 4th onto BPMN/Case-Based Reasoning — that is real external grounding, not
self-consistency. The defect being fixed (a vacuous `principle` axis) is real and correctly diagnosed as a
**supervision gap**, not an extraction-quality defect. But the three D2587 rules exist only as YAML comments
and a decision-log entry: **no code reads `content_type_rules` or `min_steps`, the convergent SYSTEM_PROMPT's
content_type instruction is one line with zero rule text, and the few-shot set has 0 non-principle positives.**
The next Stage-2 rerun will therefore reproduce the exact bug D2587 was written to fix. Two of the three rules
are right as stated (Q1 floor + Q2 inline); Q3's "3+ domains" hard gate must be **demoted to positive evidence**.
One type (`growth_edge`) is a staging-area description without a staging-area implementation, and two types
(`process_instance`, `growth_edge`) are missing the one field each that would make their separateness real
rather than nominal. **Verdict: merge the ontology; before touching the ~10k population, promote D2587 from
"classification guidance" to an executable, regression-tested constraint contract.**

---

## 1. Adjudication of the three LLM reviews

### 1.1 Convergent claims — all three agree, and I verified them TRUE against code

| # | Claim | Verification (adjudicator) | Verdict |
|---|---|---|---|
| C1 | `content_type_rules` + `min_steps` are dormant — no code reads them | `grep -r content_type_rules\|min_steps --include=*.py` → **0 matches**. `pipeline/content_types.py` loads only `content_types`, `extraction_types`, `route_to_content_type`, `content_to_extraction_type`, `dropped_content_types`, `s2_body_fields` | ✅ TRUE |
| C2 | Convergent SYSTEM_PROMPT content_type instruction is one line, no rule text | `stage2_extract.py:400-402` — item 9 lists 5 values + 3-word parentheticals. No step-count/depth/matrix language | ✅ TRUE |
| C3 | Convergent few-shot has 0 non-principle positives | `stage2_fewshot_convergent.yaml` = 84 ex: 59 `principle` + 2 unspecified among 61 positives, 23 hard-negatives | ✅ TRUE |
| C4 | S2 route gate `[FB, NULL]` vs 5-value `route_to_content_type` mismatch | `pipeline_config.yaml:250` `route_values: [FB, NULL]`; `stage4_merge.py:228-246` `_resolve_content_type` falls back to `ROUTE_TO_CONTENT_TYPE.get(route, "principle")` | ✅ TRUE (BUG-148 third drift source) |
| C5 | `content_to_extraction_type.principle = descriptive_model` conflicts with Q3 (normative_heuristic → principle) | Verified map value + `_normalize_role_fields()` empty-field branch (see §1.2 D1) | ⚠️ PARTIALLY TRUE — see D1 |
| C6 | Dedup is asymmetric: cosine dedup principle-only; PT/PI/GE/TI exact-`fb_id` only | `stage4_merge.py:681` `dedup_fbs_by_cosine` (embedding) called only on the FB stream; `:2202-2247` PT/PI/GE/TI write paths dedup via `seen_X: set()` on `fb_id` | ✅ TRUE |
| C7 | Dead fields: `parent_pt_id`, `promoted_to_type/id`, `parent_fb_ids`, MCP `annotations`, `consulted_fbs`, `template_source` → 0 refs | `grep` each field in `pipeline/`+`scripts/` → **all 0** | ✅ TRUE |
| C8 | `audit_content_type_contract.py` checks `steps` non-empty, not `len>=2` | `:87-88` `REQUIRED_NONEMPTY_ARRAYS = {"process_template": ["steps"]}` with `_nonempty = len(v) > 0` | ✅ TRUE |
| C9 | `min_steps=2` is necessary-not-sufficient; gate/done_condition is the real signal | Schema already carries `trigger`/`done_condition`/`failure_mode`; rule text already says "phases + a gate" | ✅ TRUE (adopt as floor + gate) |
| C10 | "3+ domains" is too brittle as a hard principle gate | `stage4_merge.py` already distinguishes single-domain depth from breadth; golden set has `hard_science_positive`/`medicine_positive`/`law_positive` single-domain principles | ✅ TRUE — demote to evidence |

### 1.2 Divergent claims — the auditors disagreed, and I resolved each by inspection

| # | Disagreement | Claude | Qwen0060 | ChatGPT | Adjudicator resolution (code-verified) |
|---|---|---|---|---|---|
| D1 | Is `content_to_extraction_type` a live Q3 conflict? | "Blanket empty-field default (BUG-181#3), bigger blast radius than conflation, no log flag" | "Only fires on empty/confounded — no live conflict, relies on LLM not omitting" | "Conflation-repair fallback, not a legal matrix — runtime-compatible, but dangerously named" | **Claude is most correct.** `stage2_extract.py:272-280`: `if not extraction_type: extraction_type = CONTENT_TO_EXTRACTION_TYPE.get(ctype, "descriptive_model")`. It does **not** overwrite an explicit `normative_heuristic` (Qwen/ChatGPT right on that narrow point), **but** it silently defaults *any* empty/missing form — with **zero `_defaulted` marker, log, or counter** — so a Q3-valid normative principle whose form field is omitted/truncated becomes `descriptive_model` silently. Net: not a "live conflict that always fires," but a **silent fail-open default with no audit trail**. Fix = flag+log, or fail-closed/quarantine, not widen to many-to-many. |
| D2 | Is the docstring "convergent = principle by architecture" true? | "False — prompt item 9 offers all 5; skew is few-shot bias, not design; also '75/75' is wrong (59/61)" | (not addressed) | (not addressed) | **Claude correct.** `content_types.py:12-17` docstring says "emits `content_type: principle`... 75/75" — numerically wrong and architecturally misleading (BUG-229). |
| D3 | growth_edge: demote to status flag or keep as type? | "Demote to status flag OR build promotion pipeline — pick one" | "Bound with negative definition (catch-all risk)" | "Add positive evidence criterion; do NOT define by failure to qualify" | **Keep as 5th type** (Qwen3.8 agrees; a speculative/upstream role is genuinely retrieval-relevant and distinct from `principle.status`), but (a) add a *positive* entry criterion, and (b) **delete or wire** the dead promotion fields. Claude's structural observation is correct: as-is it is a dead-end bucket with a staging-area description. |
| D4 | Route fallback fix | (reconcile comment vs gate) | "Deprecate route fallback; default to growth_edge on missing content_type" | "Make content_type authoritative; derive route mechanically" | **ChatGPT's architecture is right.** `content_type` = source of truth; `route` = legacy transport; on missing content_type **abstain → growth_edge/quarantine**, never silently `principle`. |
| D5 | `_normalize_role_fields` naming | (not raised) | (not raised) | "Rename `CONTENT_TO_EXTRACTION_TYPE` → `CONTENT_TYPE_CONFLATION_REPAIR_DEFAULT`" | **Adopt.** The name invites misuse as a legal matrix; the map is a repair default only. |

### 1.3 Rejected claims / over-reach (where an auditor went further than the data supports)

1. **Qwen3.8 (second validator) on D1** claimed the default "overrides the LLM's explicit `normative_heuristic`… forcing them into `descriptive_model`." **REJECTED** — the code only fires on *empty/missing* form, never overwrites an explicit value. This is itself a useful meta-lesson: **double-validation models disagree with each other AND with the code; direct inspection is the ground truth.** The adjudicator's grep is authoritative over any single model's paraphrase.
2. **Claude on `process_instance`** framed "PI indistinguishable from an unlinked anecdote without `parent_pt_id`" as near-fatal. **PARTIALLY REJECTED** — a case study can legitimately be *upstream* of a crystallized template (evidence FOR a future PT), so a mandatory tether is too strong. The correct fix is: make `parent_pt_id` an *optional but wired* link (backfill when a PT exists), and re-scope PI's definition to "episodic case study (which may instantiate a known PT or precede one)" — not "must reference a PT."
3. **Qwen0060** asserted `content_to_extraction_type` "does NOT overwrite a valid `normative_heuristic`… thus no live conflict exists." **REJECTED as insufficient** — true for the *valid-value* case, but it elides the empty-field branch's silent downgrade (D1). The conflict is real in the fail-open path.

### 1.4 Claims I add (beyond the three auditors)

1. **ABSTAIN is the missing safety valve.** No auditor proposed it as a first-class outcome; ChatGPT came closest (". Otherwise → reject / NULL"). The 5-bucket ontology currently *forces* every object into a bucket. A 6th outcome "insufficient evidence / unclassified → human triage" is the single cheapest noise-mitigation lever and is the natural fail-closed complement to S5's NLI gate. It prevents the next vacuous axis.
2. **The three auditors all treat `content_type` as a single-shot LLM decision; the durable fix is to persist the intermediate features** (`sequence`, `repeatable`, `transferability`, `epistemic_status`, `tool_specificity`) and *derive* `content_type` — this is the OntoClean/CQ lesson and directly kills the "prescriptive → PT" bias at the source rather than patching it with more prose.
3. **The "alpha-principle not noise" goal is served by three levers already in the system** (depth-test-as-evidence, ABSTAIN, S5 fail-closed NLI) plus one missing one (symmetric semantic dedup). The auditors found the dedup gap (C6) but did not connect it to the alpha-goal: a false-split PT is a *duplicate* that becomes retrieval noise.

---

## 2. Qwen3.8 double-validation (second opinion, temp=0.0)

Prompted with the 6 verified facts (F1–F6, §1) and asked for independent judgment. Summary:

| Question | Qwen3.8 verdict | Adjudicator concurrence |
|---|---|---|
| content_to_extraction_type | "live conflict… overrides explicit normative_heuristic" | ⚠️ Over-stated (see §1.3.1) — but agrees the silent default must go |
| "3+ domains" | "demote to positive evidence" | ✅ agree |
| growth_edge | "keep as 5th content_type (distinct epistemic state)" | ✅ agree (with positive-definition + dead-field fix) |
| route | "real drift; align gate or handle NULL explicitly; remove implicit principle default" | ✅ agree |
| top fixes | (1) remove silent extraction_type default; (2) align route gate; (3) add non-principle few-shots | ✅ agree, ordered differently (see §5) |

Net: Qwen3.8 independently confirms the three auditors' core direction. Its one material error (D1) is itself instructive and is logged above.

---

## 3. Market research — peer-reviewed / industry analogues

The three auditors cited DITA, BPMN, CBR (Aamodt & Plaza), SHACL, OQuaRE, OntoClean, CQ4OE, Zettelkasten, FRBR/ODP, OBO Foundry, PWO, GTD. I confirmed these are all real, established references and added the ones in **bold**.

### 3.1 Object-type grounding (what validates each Maxwell type)

| Maxwell type | Closest established analog | Fit | What to adapt |
|---|---|---|---|
| `principle` | **DITA Concept topic** (OASIS); **Anderson & Krathwohl (2001) revised Bloom "conceptual knowledge"** | Strong, near word-for-word | DITA's discipline: one topic = one subject = one purpose. Adopt "don't proliferate types" (DITA converged on 3 core; Maxwell's `dropped_content_types` killing `fact` is the same correct instinct) |
| `process_template` | **DITA Task topic**; **BPMN 2.0 process definition**; **PWO workflow** | Strong | BPMN: a definition is `reusable + ordered + termination condition`. Adopt gate/done-condition as the *semantic* discriminator, step-count as floor |
| `process_instance` | **BPMN process instance**; **Case-Based Reasoning "case"** (Aamodt & Plaza 1994) | Strong on paper; **parent_pt_id unwired** (C7) | Wire the definition↔instance link (optional but real), or re-scope as "episodic case study" — §1.3.2 |
| `tool_instruction` | **DITA Reference topic** ("quick-lookup, command syntax, looked up not memorized") | Strong on paper; MCP `annotations` dead (C7) | Prune or ship the 3 dead MCP fields; the 10 core fields are genuinely populated |
| `growth_edge` | **Zettelkasten "fleeting note"** (Luhmann); **GTD inbox**; **IBIS issue** | Weak as a *peer content type* — fleeting notes are a *pre-processing state*, not a peer category | The cautionary lesson: keep GE only if it has (a) positive entry criterion + (b) a real promotion path; otherwise it is a `status` flag, not a type |

**Additional analogues I add:**
- **FRBR WEMI (IFLA) + Description-Observation ODP** — the cleanest formal model for `content_type` (role) × `extraction_type` (form) orthogonality. Adopt FRBR's "one work → many expressions" framing for FB variants (same principle, multiple formulations).
- **DOLCE / BFO upper ontologies** — `principle` ≈ endurant (enduring truth), `process_template`/`process_instance` ≈ perdurant (occurring over time). Confirms the two axes are not arbitrary.
- **PROV-O (W3C)** — Entity/Activity/Agent; the model for the provenance stamping already in R14.
- **Nanopublications / SPAR (2014)** — minimal citable assertion + provenance; the model for "atomic FB with provenance," directly relevant to the alpha-principle goal.
- **SKOS** — broader/narrower/related; the model for `related_fbs` edges.
- **GraphRAG (Microsoft, 2024)** — "atomic facts" + community summarization; the closest *commercial* analogue to "extract only alpha facts, not noise" — worth benchmarking retrieval noise against.
- **PKM supertag tools (Tana/Notion/Logseq/Roam)** — the "human self-learning digestible" requirement maps to these; their lesson is that *types must stay human-legible and few* (Tana's supertags vs Notion's free-form = the same "typed vs catch-all" tension Maxwell is navigating).

### 3.2 Architecture-level analogues (what validates the *fix*, not just the types)

| Analog | Lesson for Maxwell | Adopt? |
|---|---|---|
| **SHACL (W3C)** — shapes/constraints separate ontology from conformance, produce explicit PASS/FAIL results | The #1 architectural adoption: turn `content_type_rules` into machine-readable constraints + a deterministic validator emitting PASS/FAIL/ABSTAIN. Do **not** duplicate rules in Python — read from YAML (C12) | ✅ ADOPT — this is the "promote D2587 to executable contract" move |
| **OntoClean (Guarino & Welty)** — annotate meta-properties, check taxonomy consistency | Persist the latent adjudication dimensions (§1.4.2) and derive `content_type`, rather than a one-shot prose→label jump | ✅ ADOPT |
| **Competency Questions / CQ4OE** — requirements → testable criteria; 3-expert adjudication, 2-of-3 agreement, rationale | Freeze a ~150–250 *adversarial boundary* corpus (1-step heuristic, 2-step method, domain-specific principle, matrix, case study, speculative) with 3 adjudicators + rationale fields. This is the only way D2587 becomes *falsifiable* rather than a "more plausible distribution" | ✅ ADOPT — GOLD-B/CHALLENGE per D2286 |
| **OQuaRE** — ontology quality as measured characteristics (structural, functional, transferability, maintainability) | Add `PT structural-violation rate`, `GE catch-all rate`, `principle false-positive rate`, `label-stability across models/prompts` as *measured* metrics | ✅ ADOPT (cheap, high signal) |
| **BPMN 2.0 spec (OMG) + DITA migration guides** | Direct reference reads to sanity-check the PT/PI definition↔instance split | 📖 Reference |

---

## 4. Ontological validation of Maxwell's 5×4 schema

**Is the 5-type × 4-form orthogonal axis sound? Yes — 4 of 5 types sit on two independently-converged axes** (general↔specific, conceptual↔procedural) that DITA and Bloom's taxonomy both reach. The 5×4 = 20-cell product is a *legal matrix*, not a 5→1 mapping — the `content_to_extraction_type` table is a **repair default, not the law** (rename it per §1.2 D5).

**The three structural gaps (all code-verified, all fixable):**
1. **`growth_edge` = staging area without a promotion pipeline.** `promoted_to_type`/`promoted_to_id`/`parent_fb_ids` are 0-ref schema. Fix: keep the type but (a) positive entry criterion, (b) delete or wire the promotion fields, (c) lifecycle (open→investigating→promoted|archived) either becomes real code or is removed from the description.
2. **`process_instance` = case study without its tether.** `parent_pt_id` is 0-ref. Fix: optional-but-wired link (backfill at S4 via cosine/model against known PTs) + re-scoped definition (§1.3.2).
3. **`tool_instruction` = 3 of 13 declared fields are decorative.** MCP `annotations` (readOnlyHint/destructiveHint/idempotentHint) are 0-ref. Fix: prune or ship.

**On "alpha principles, not noise":** the noise-mitigation stack is (in order of leverage) — (1) depth-test-as-evidence (not gate) to stop misrouting single-domain depth; (2) ABSTAIN outcome to stop force-bucketing; (3) symmetric semantic dedup so a false-split method/tool is not emitted twice; (4) positive definitions on every bucket so none is "everything else"; (5) S5 fail-closed NLI already in place. No new type is needed — the auditors all agree, and DITA's own history supports "don't proliferate."

---

## 5. Ultimate verdict + ranked fixes

### 5.1 Verdict on D2587

| Rule | Verdict |
|---|---|
| Q1 — PT = ≥2 steps (+ gate/done condition) | **SOUND as a necessary floor, not a sufficient definition.** Adopt "repeatable + ordered ≥2 actions + (gate OR done_condition)". `min_steps=2` = structural floor; gate/done = semantic test. |
| Q2 — matrix never standalone | **SOUND.** Matrix = representation, not role. Classify semantic role; store inline with the owning principle/PT. No orphan if the depth/sequence test routes it. |
| Q3 — depth test decides instruction-vs-principle | **DIRECTION CORRECT, FORM TOO BRITTLE.** "Single transferable prescriptive claim = principle, not PT" is the most important fix (reverses prescriptive→template). But **"3+ domains" must be demoted from hard gate to positive evidence**: transferability = "proposition survives substitution across materially different contexts/instances," cross-domain evidence preferred, not required. |

### 5.2 Ranked fixes (P0 → P2, exact targets)

**P0 — make the rules executable before any rerun.**
1. **Inject the D2587 decision procedure into the S2 classifier prompt** — `pipeline/stage2_extract.py` SYSTEM_PROMPT item 9. Add the ordered precedence (tool-specific → TI; concrete case → PI; unresolved/speculative → GE; repeatable ordered ≥2 + gate/done → PT; reusable proposition/heuristic → principle; else → ABSTAIN). Mirror the item-8 (extraction_type) pattern that demonstrably works.
2. **Add 2–4 non-principle positive few-shots** to `config/golden/stage2_fewshot_convergent.yaml` (port the *pattern* from `stage2_fewshot_single_source.yaml`, which is correctly role-balanced at 3/2/1/7/1).
3. **Wire `content_type_rules` + `min_steps` into a deterministic validator** — `pipeline/content_types.py` loader (expose `CONTENT_TYPE_RULES`, `PROCESS_TEMPLATE_MIN_STEPS`) + `scripts/audit_content_type_contract.py` (`len(steps) >= 2` for PT). Read from YAML, never duplicate in Python (C12). This is the SHACL move.

**P1 — close the silent-failure paths (data integrity).**
4. **Fix the silent empty-extraction_type default** — `stage2_extract.py:_normalize_role_fields` BUG-181#3 branch: add `_extraction_type_defaulted: true` marker + counter, or fail-closed/quarantine for `principle` with empty form. Rename `CONTENT_TO_EXTRACTION_TYPE` → `CONTENT_TYPE_CONFLATION_REPAIR_DEFAULT`.
5. **Deprecate `route` as an ontology carrier** — `stage4_merge.py:_resolve_content_type`: `content_type` authoritative; on missing, **ABSTAIN → growth_edge/quarantine**, not `principle`. Reconcile `route_values:[FB,NULL]` vs the 5-value map (BUG-148 third source).
6. **Extend semantic dedup to PT/PI/GE/TI** — `stage4_merge.py`: dedup non-principle types by embedding cosine (or equivalent), not exact `fb_id` only.

**P2 — make it falsifiable + human-legible (long-term).**
7. **Freeze a ~150–250 adversarial boundary corpus** with 3 adjudicators + rationale (CQ4OE pattern; GOLD-B/CHALLENGE per D2286). Regression-fail CI if labels change unexpectedly.
8. **Bound `growth_edge` with a positive definition** ("MUST contain an articulated open tension or unverified correlation; NOT a dump for failed depth-tests").
9. **Prune or ship the 6 dead fields** (`parent_pt_id`, `promoted_to_type/id`, `parent_fb_ids`, MCP `annotations`, `consulted_fbs`, `template_source`); **backfill `parent_pt_id`** when a PT exists.
10. **Fix the stale docstring** (`content_types.py:12-17`): "75/75 principle" → actual 59/61, and "convergent = principle by architecture" → "few-shot bias, fixable".

### 5.3 The four collision rows (00548 / 00668 / 00971 / 00713)

Do **not** auto-accept the D2587 flips and do **not** auto-restore the prior human labels. Re-adjudicate each with the *final* decision procedure (not majority vote), recording four features — `sequence_present`, `repeatable_method`, `transferability`, `epistemic_status` — then derive the type. **00713 (→ growth_edge) gets special scrutiny**: it moved *across* the epistemic axis, not just the role axis. Freeze the result as a regression fixture (§5.2.7).

### 5.4 What NOT to do

- **Do not bulk-reclassify the ~10k population yet.** The rules are not yet executable, and 14.9% is a *corrected* prior, not ground truth.
- **Do not widen `content_to_extraction_type` to many-to-many.** That would re-conflate axes the ontology deliberately separates. Re-scope it as "repair default only."
- **Do not add a 6th content type.** The gap is implementation, not ontology surface area.

---

## 6. Governance updates made (this session)

- **Buglog** — 6 new bugs (BUG-225…230) + BUG-148 annotated with the route-map third-drift finding.
- **Decisions** — D2588 appended (adjudication verdict + P0/P1/P2 plan); summary re-synced.
- **Task register** — P0/P1/P2 tasks appended under a dated section.
