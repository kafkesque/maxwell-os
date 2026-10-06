# Maxwell OS — Extra-60 PRIMARY DOMAIN (ADVISORY, domain-only)

## Why this re-run exists
Your previous 60-anchor pass returned `primary_domain` values that **drifted out of menu**:
DeepSeek wrote *discipline* labels (`research methodology`, `finance`), Claude invented
capitalized ad-hoc names (`Survey Research Methods`), and GPT leaked its own reasoning
text (`"not a causal explanation."`) into the domain column. This pass is **domain-only**
and locked to a closed menu so that cannot happen.

## Your role
You are an **independent domain auditor**. You assign ONE primary application domain per
anchor from a CLOSED menu. Output is **ADVISORY** — a hypothesis for a human adjudicator,
never a final verdict. You are one of three independent models (Claude, GPT, DeepSeek);
classify from the text alone.

## Input
Attached CSV: `extra60_domain_cells.csv` — 60 rows (R151…R210). Columns:

| column | meaning |
|---|---|
| `item_id` | stable id (R151…R210) |
| `name`, `definition`, `application`, `boundary`, `mechanism` | the anchor text |
| `domain_candidate` | the human's prior tags (already canonicalized) — **context only, not binding** |

## The CLOSED primary_domain menu (44 values — pick EXACTLY ONE, spelled exactly)
ai & agents · arts & culture · brand identity · business development · business operations ·
code & computation · computational art · computational science & physics · creative technology ·
data visualization · design strategy · design systems · digital product · editorial & advertising ·
education · engineering & infrastructure · engineering practice · entrepreneurship · environmental design ·
finance & investment · graphic design · health & wellness · illustration · industrial design ·
information architecture · leadership · legal & public policy · marketing & communications · media & entertainment ·
motion design · organizational behavior · packaging · personal productivity · product design · project management ·
research & methodology · science & research · semiotics & communication · social sciences · systems & frameworks ·
urban planning · user experience · web & ui · emerging

`emerging` = none of the 43 canonical domains fits (use it only as a last resort; then explain in `domain_why`).

## Hard rules (anti-drift / anti-leak)
1. Return a `primary_domain` that is **one of the 44 values above, spelled character-for-character**.
2. NEVER return a discipline (e.g. `cognitive science`, `psychology`, `research methodology` is a domain but `research methodology` the discipline is different — if unsure, it must still be one of the 44). If the text is about cognition, the *domain* is likely `user experience` or `health & wellness` or `education`, NOT `cognitive science`.
3. NEVER paste reasoning, clauses, or sentence fragments into `primary_domain`. That field is a single menu token only.
4. `domain_candidate` is context. You may differ from it; say why in `domain_why`.
5. Classify ALL 60 rows, preserving order.
6. No columns, headers, or prose outside the output CSV.
7. `domain_conf` = `high` | `medium` | `low`. `domain_why` = ≤ 15 words.

## Output
Return a single CSV block with this exact header, one row per `item_id` (60 rows):

```
item_id, primary_domain, domain_conf, domain_why
```
