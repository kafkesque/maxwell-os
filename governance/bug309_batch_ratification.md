# BUG-309 — Batch ratification: 4 ambiguous cross-listings + 2 misplacements

**Date:** 2026-09-20 · **Decision:** D-286 (execution) · **State:** awaiting human batch-ratification

The D-285 discipline-boundary fix + the BUG-309 unambiguous pass resolved **all** raw-alias
cross-listings among the 5 core disciplines **and** 7 of the 11 non-core cross-listings. The
following **4 genuinely-ambiguous cross-listings** and **2 misplacements** remain. They are
left here — NOT fixed by fiat — because each is a legitimate subsumption question where two
disciplines both plausibly own the term.

## A. Ambiguous cross-listings (a raw alias listed under 2 disciplines)

| # | raw alias (exact case) | current owners | recommendation | rationale |
|---|---|---|---|---|
| 1 | `Color Psychology` | `color theory`, `visual perception` | **color theory** (drop from visual perception) | color theory's definition already includes "their psychological impact on design"; visual perception is about *perception*, not *affect*. |
| 2 | `Computational Models of Social Life` | `complex adaptive systems`, `computational physics & simulation` | **complex adaptive systems** (drop from computational physics & simulation) | it is computational *social* science; `complex adaptive systems` already owns `Computational Social Science`; "physics & simulation" is the wrong home for *social life*. |
| 3 | `Decision Science` | `decision making`, `operations research` | **decision making** (drop from operations research) | decision science ≈ the interdisciplinary study of choice; `decision making` is the nearer home; `operations research` = analytical methods for optimization, a *tool* not the *subject*. |
| 4 | `Simulation` | `computational physics & simulation`, `operations research` | **computational physics & simulation** (drop from operations research) | "simulation" is a generic method; keep it only where it is *definitional* (it is literally in the discipline name); ORS uses simulation as one of many techniques. |

## B. Misplacements (D-285: persuasion → design psychology)

| # | raw alias | current home | recommendation | rationale |
|---|---|---|---|---|
| 5 | `Rhetoric` / `rhetoric` | `behavioral economics` | **design psychology** — OR **communication theory** | rhetoric = persuasion-by-language; per D-285 persuasion is design psychology. BUT `alias_map.yaml` routes "rhetorical studies/theory" → communication theory, so this needs your call: is rhetoric *exploitation-of-bias* (design psychology) or *the craft of communication* (communication theory)? |
| 6 | `behavioural economics+persuasion` | `behavioral economics` | **keep in behavioral economics (head-wins)** — OR **split** | a compound raw string; head term is "behavioural economics" (correct), the "+persuasion" suffix is a D-285 leak. Either (a) keep whole (document head-wins rule), or (b) drop the compound so "persuasion" never rides into behavioral economics. |

## How to ratify

For each row, write **KEEP-IN** / **DROP-FROM** (or a new target). Example:

> A1: color psychology → keep `color theory`, drop `visual perception`. ✅
> A5: rhetoric → `communication theory` (not design psychology). ✅

Then I fold the rulings into `config/taxonomy_v5.yaml` and re-render the menu.

## Note (additional flag, not a cross-listing)

`macroeconomics` is currently listed **only** under `political economy` (line 1569) — not
cross-listed, but by the same exclude-logic (political economy's `exclude` names `economics`)
it belongs in `economics`. Flagged for the same batch.
