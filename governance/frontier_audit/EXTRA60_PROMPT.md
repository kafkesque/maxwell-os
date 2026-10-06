# Maxwell OS — Extra-60 Anchor Classification (ADVISORY)

## Your role
You are an **independent classification auditor**. You classify 60 extra knowledge anchors
(R151…R210) on FOUR axes. Your output is **ADVISORY** — a hypothesis for a human
adjudicator, never a final verdict. You are one of three independent models (Claude, GPT,
Kimi); classify from the text alone.

## Input
Attached CSV: `extra60_cells_to_classify.csv` — 60 rows. Columns:

| column | meaning |
|---|---|
| `item_id` | stable id (R151…R210) |
| `name`, `definition`, `application`, `boundary`, `mechanism` | the anchor text |
| `axes_in_scope` | always `CT;DISC;FORM;DOMAIN` |
| `ct_candidate`, `disc_candidate`, `form_candidate`, `domain_candidate` | the human's current leaning — **advisory context only**; may be informal or typo'd; you are NOT bound by it |

## The four axes and their CLOSED menus

### Axis 1 — `content_type` (CT): functional ROLE — what kind of object is this?
Pick EXACTLY ONE of these 5 roles:
- **principle** — a single self-contained epistemic claim you KNOW/APPLY; a transferable filter (any scope).
- **process_template** — a procedure you EXECUTE: trigger + ordered steps (≥2) + a done-condition/gate.
- **process_instance** — a concrete case study of a procedure actually executed.
- **tool_instruction** — tool/software-specific command, syntax, or feature.
- **growth_edge** — speculative insight articulating an OPEN TENSION or UNVERIFIED CORRELATION.

These two are **DISPOSITIONS, not content types** — NEVER return them as a CT answer; if you
believe an object has no clean role, say so in `ct_why` (e.g. "disposition=noise_drop") and
put `uncertain` in `ct`:
- **noise_drop** — bare fact / descriptive summary, no prescriptive filter, no method.
- **quarantine** — carries SOME value but no clean role (ambiguous) → hold.

### Axis 2 — `discipline` (DISC): the field the claim belongs to
Pick EXACTLY ONE from this closed list (61), spelled exactly:

visual perception, visual semiotics, cultural design, semiotics, typography, color theory, motion & time, design psychology, creative process, cognitive science, behavioral economics, organizational theory, decision making, psychology, linguistics, strategic thinking, risk management, systems thinking, complex adaptive systems, systems engineering, research methodology, operations research, machine learning, generative ai, software engineering, creative coding, generative design, computational physics & simulation, computational geometry, game design, political economy, privacy & surveillance, philosophy, artificial intelligence, communication theory, human-computer interaction, interdisciplinary studies, information science, finance, economics, sociology, anthropology, cultural studies, theoretical physics, aesthetics, media studies, computer graphics, law, information security, ecology, evolutionary biology, social network analysis, neuroscience, robotics, health & medicine, performing arts, literary theory, engineering, design thinking, information retrieval, computational theory

### Axis 3 — `extraction_type` (FORM): epistemic FORM — how the claim is justified
Pick EXACTLY ONE of these 4:
- **causal_mechanism** — X→Y because Z (a verified cause→effect chain).
- **descriptive_model** — a taxonomy/classification of WHAT categories exist and how they relate.
- **normative_heuristic** — a practical rule of thumb with clear steps / a widely-applicable heuristic.
- **empirical_pattern** — a strong correlation WITHOUT a proven causal chain (speculative).

### Axis 4 — `primary_domain` (DOMAIN): the single primary application domain
Propose ONE primary domain. Prefer a name already present in `domain_candidate` (the human's
tags, comma-separated) where it fits; if none fits, propose a short canonical name. This axis
is advisory-only — the human will finalize the canonical domain vocabulary.

## Hard rules
1. Use ONLY the canonical CT/DISC/FORM labels above, spelled exactly. Do not invent or re-word.
2. `uncertain` is valid when the text gives zero signal. Prefer a low-confidence best answer over abstaining.
3. `*_candidate` columns are the human's leaning — context only. If you disagree, say so in the matching `*_why`.
4. Advisory only. Classify EVERY axis for EVERY row (60 rows), preserving order.
5. Do not add columns, headers, or prose outside the output CSV.

## Output
Return a single CSV block with this exact header, one row per `item_id` (60 rows):

```
item_id, ct, ct_conf, ct_why, disc, disc_conf, disc_why, form, form_conf, form_why, primary_domain, domain_conf, domain_why
```

- `ct`/`disc`/`form` = canonical label (or `uncertain`); `primary_domain` = short canonical domain name.
- `*_conf` = `high` | `medium` | `low`.
- `*_why` = ≤ 20 words.
