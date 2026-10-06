# Maxwell OS — Anchor Classification Audit (ADVISORY)

## Your role
You are an **independent classification auditor**. You will classify a set of knowledge
"anchors" (short, self-contained epistemic claims) on up to three axes.

Your output is **ADVISORY** — a hypothesis for a human adjudicator, never a final verdict.
You are one of three independent models (Claude, GPT, Kimi) run on the same input; you have
not seen the others' outputs and must classify from the text alone.

## Input
Attached CSV: `cells_to_classify.csv` — 150 rows, one anchor each. Columns:

| column | meaning |
|---|---|
| `item_id` | the anchor's stable id (R001…R150) |
| `name`, `definition`, `application`, `boundary`, `mechanism` | the anchor text you classify from |
| `axes_in_scope` | which axes you MUST classify for this row (semicolon-separated, e.g. `CT;FORM`) |
| `ct_candidate`, `disc_candidate`, `form_candidate` | the human's current leaning — **advisory context only**; may be informal or typo'd; you are NOT bound by it |

## The three axes and their CLOSED menus

### Axis 1 — `content_type` (CT): functional ROLE — what kind of object is this?
Pick EXACTLY ONE of these 5 roles:
- **principle** — a single self-contained epistemic claim you KNOW/APPLY; a transferable filter (any scope). Settled knowledge, not an open question.
- **process_template** — a procedure you EXECUTE: trigger + ordered steps (≥2) + a done-condition/gate.
- **process_instance** — a concrete case study of a procedure actually executed (proof it works).
- **tool_instruction** — tool/software-specific command, syntax, or feature.
- **growth_edge** — speculative insight that articulates an OPEN TENSION or an UNVERIFIED CORRELATION.

These two are **DISPOSITIONS, not content types** — never return them as a CT answer; they flag a no-clean-role object:
- **noise_drop** — bare fact / descriptive summary with no prescriptive filter, no method, no transferable value.
- **quarantine** — carries some value but no clean role (ambiguous) → hold, do not force.

Key discriminator: **procedural INTENT + done-condition** (EXECUTE vs KNOW/APPLY), NOT step count.
Scope (universal / cross-domain / domain / specialized) is the SEPARATE depth axis and must NEVER influence the CT choice.

### Axis 2 — `discipline` (DISC): the field the claim belongs to
Pick EXACTLY ONE from this closed list (61). Do not invent, merge, or re-word.

visual perception, visual semiotics, cultural design, semiotics, typography, color theory, motion & time, design psychology, creative process, cognitive science, behavioral economics, organizational theory, decision making, psychology, linguistics, strategic thinking, risk management, systems thinking, complex adaptive systems, systems engineering, research methodology, operations research, machine learning, generative ai, software engineering, creative coding, generative design, computational physics & simulation, computational geometry, game design, political economy, privacy & surveillance, philosophy, artificial intelligence, communication theory, human-computer interaction, interdisciplinary studies, information science, finance, economics, sociology, anthropology, cultural studies, theoretical physics, aesthetics, media studies, computer graphics, law, information security, ecology, evolutionary biology, social network analysis, neuroscience, robotics, health & medicine, performing arts, literary theory, engineering, design thinking, information retrieval, computational theory

### Axis 3 — `extraction_type` (FORM): epistemic FORM — how the claim is justified
Pick EXACTLY ONE of these 4:
- **causal_mechanism** — X→Y because Z (a verified cause→effect chain).
- **descriptive_model** — a taxonomy/classification of WHAT categories exist and how they relate.
- **normative_heuristic** — a practical rule of thumb with clear steps / a widely-applicable heuristic.
- **empirical_pattern** — a strong correlation WITHOUT a proven causal chain (speculative).

## Hard rules
1. Use ONLY the canonical labels above, spelled exactly. Never invent, abbreviate, or re-word a label.
2. `uncertain` is a valid answer when the text genuinely does not determine an axis. Prefer a best answer at low confidence over abstaining, but never guess when the text gives zero signal.
3. The `*_candidate` columns are the human's leaning — context only. If you disagree, say so explicitly in the matching `*_why` field.
4. Advisory only. Do not assert your label as fact; phrase rationales as your reading of the text.
5. Classify EVERY in-scope axis for EVERY row. Leave out-of-scope axes blank.
6. Depth is NOT in scope for this pass — do not output a depth column.
7. Do not add columns, headers, or prose outside the output CSV.

## Output
Return a single CSV block with this exact header, one row per `item_id` (150 rows), preserving input order:

```
item_id, ct, ct_conf, ct_why, disc, disc_conf, disc_why, form, form_conf, form_why
```

- `ct` / `disc` / `form` = canonical label (or `uncertain`).
- `*_conf` = `high` | `medium` | `low`.
- `*_why` = ≤ 20 words, stating your reading and (if relevant) why you depart from the candidate.
- Leave an axis blank where it is not in `axes_in_scope`.
