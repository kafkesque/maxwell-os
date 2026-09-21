# BUG-310 — Batch ratification: 37 DOMAIN raw-alias cross-listings

**Date:** 2026-09-20 · **Discovered:** follow-up sweep after BUG-309 resolved the discipline axis.
**Rule:** a raw alias must map to AT MOST ONE domain. Here each string is listed under 2 domains.
**`keep X, drop Y`** means: keep it in domain X's raw list, remove it from domain Y's raw list.

The discipline exclude-signal does **not** transfer cleanly to domains (it would wrongly route
`programming` → engineering practice), so I did **not** auto-fix — all 37 are for your judgment.

## Recommended rulings (approve / override per row)

| # | raw string | currently in both | keep → | drop from |
|---|---|---|---|---|
| 1 | `creative technology` | code & computation + creative technology | **creative technology** (literal canonical name) | code & computation | approve
| 2 | `design system` | design systems + digital product | **design systems** | digital product | approve
| 3 | `advertising` | editorial & advertising + marketing & communications | **editorial & advertising** | marketing & communications | approve
| 4 | `art education` | arts & culture + education | **education** | arts & culture | approve
| 5 | `brand strategy` | brand identity + marketing & communications | **brand identity** | marketing & communications | approve
| 6 | `control systems engineering` | engineering & infrastructure + engineering practice | **engineering practice** | engineering & infrastructure | approve
| 7 | `design operations` | design systems + digital product | **design systems** | digital product | approve
| 8 | `design research` | design strategy + digital product | **design strategy** | digital product | approve
| 9 | `design research investigation` | design strategy + digital product | **design strategy** | digital product | approve
| 10 | `e-commerce` | finance & investment + marketing & communications | **marketing & communications** | finance & investment | approve
| 11 | `front-end` | creative technology + web & ui | **web & ui** | creative technology | approve
| 12 | `human resources` | business operations + leadership | **business operations** | leadership | approve
| 13 | `information design` | data visualization + information architecture | **information architecture** | data visualization | approve
| 14 | `interaction design` | digital product + user experience | **user experience** | digital product | approve
| 15 | `market research` | marketing & communications + research & methodology | **marketing & communications** | research & methodology | approve
| 16 | `marketing strategy` | business development + marketing & communications | **marketing & communications** | business development | approve
| 17 | `network engineering` | engineering & infrastructure + engineering practice | **engineering practice** | engineering & infrastructure | approve
| 18 | `operations management` | business operations + project management | **business operations** | project management | approve
| 19 | `organizational design` | leadership + organizational behavior | **organizational behavior** | leadership | approve
| 20 | `organizational leadership` | leadership + organizational behavior | **leadership** | organizational behavior | approve
| 21 | `personal development` | business operations + personal productivity | **personal productivity** | business operations | approve
| 22 | `phenomenology` | research & methodology + semiotics & communication | **research & methodology** | semiotics & communication | approve
| 23 | `product development` | digital product + project management | **digital product** | project management | approve
| 24 | `product management` | digital product + project management | **digital product** | project management | approve
| 25 | `product strategy` | business operations + design strategy | **design strategy** | business operations | approve
| 26 | `programming` | code & computation + engineering practice | **code & computation** | engineering practice | approve
| 27 | `sales` | business development + marketing & communications | **business development** | marketing & communications | approve
| 28 | `sales communication` | business development + marketing & communications | **business development** | marketing & communications | approve
| 29 | `sales psychology` | business development + marketing & communications | **business development** | marketing & communications | approve
| 30 | `service design` | digital product + user experience | **user experience** | digital product | approve
| 31 | `software development` | code & computation + engineering practice | **code & computation** | engineering practice | approve
| 32 | `team dynamics` | leadership + organizational behavior | **organizational behavior** | leadership | approve
| 33 | `ui design` | digital product + user experience | **user experience** | digital product | approve
| 34 | `ui/ux` | digital product + user experience | **user experience** | digital product | approve
| 35 | `ux design` | digital product + user experience | **user experience** | digital product | approve
| 36 | `web design` | digital product + web & ui | **web & ui** | digital product | approve
| 37 | `web navigation` | information architecture + web & ui | **information architecture** | web & ui | approve

## How to ratify (fast)

Either "approve all 37" (I apply the table as-is), or reply with only the rows you disagree with, e.g.:

> M1b: approve all except #16 → keep `business development` (not marketing & communications); #22 → `semiotics & communication`.

A raw alias left in two places is a silent last-write-wins hazard in the synonym index — so the goal
is to make each of these 37 live under exactly one domain.
