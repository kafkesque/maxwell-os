# V9 Menu-Edit Spec — DRAFT for owner sign-off (2026-10-09)

Status: **DRAFT — 3 owner flags pending** (see bottom). Do NOT mutate config until flags resolved.
Source: owner-approved Layer A edits (BUG-693 menu-widening resolution) + D-2895 (color theory) + D-2896
(normalization boundary). Canonical run = `rechunk-v4-20260929` (6591 rows); t11 FOREVER excluded.

## Invariant (non-negotiable)
Merge / demote / promote mutate **canonical** (`discipline`, `discipline_macro`, `menu_hash`,
`taxonomy_version`) ONLY. `discipline_raw` / `domains_raw` stay **verbatim** on every affected row.

## Changes (disciplines 65 -> 64)

| # | Label | Rows | Action | Raw invariant | Group/macro delta |
|---|-------|------|--------|---------------|-------------------|
| 1 | `visual semiotics` | 44 | MERGE -> `semiotics` (61 -> 105) | discipline_raw stays `visual semiotics` | none (both Perception & Signal) |
| 2 | `information retrieval` | 9 | MERGE -> `information science` (122 -> 131) | discipline_raw stays `information retrieval` | **CROSS-MACRO**: AI & Computing (Technical) -> Systems & Method (Method & Business) — FLAG (b) |
| 3 | `computational theory` | 16 | DEMOTE -> `emerging` | discipline_raw stays `computational theory` | -> emerging_routing — FLAG (a) |
| 4 | `creative writing` | 14 | PROMOTE (offmenu -> canonical) | discipline_raw stays `creative writing` | new: Heterodox (Human & Design) — FLAG (c) |
| 5 | `museum studies` | 13 | PROMOTE (offmenu -> canonical) | discipline_raw stays `museum studies` | new: Systems & Method (Method & Business) — FLAG (c) |

## No change (keep distinct, D-2895 + prior rulings)
- `color theory` (14) vs `visual perception` (11) — distinct, boundary codified (D-2895).
- `design psychology` (3) vs `psychology` (618) — distinct, applied-sub-discipline boundary.
- `generative ai` / `creative coding` / `generative design` — stay as **reserved slots** (t11 future material;
  R006 lands on `generative design`).

## Post-v9 emerging = 1488
offmenu 1309 - 27 (creative writing 14 + museum studies 13) + 16 (computational theory demoted) = 1282 offmenu
+ 190 dombleed + 16 computational theory = **1488** (was 1499).

## Re-classification + re-pin sequence (after flags resolved)
1. Bump `config/version.yaml` taxonomy_version v8 -> v9.
2. Render `closed_menu_v9.json` (65 -> 64 disciplines), recompute `menu_hash` + `answer_space_hash`.
3. Re-classify 96 rows (44 + 9 + 16 + 14 + 13): update `discipline`, `discipline_macro` (1:1 with new group),
   `menu_hash`, `taxonomy_version`. Preserve `discipline_raw` verbatim.
4. `scripts/check_menu_reclass_gate.py` -> GREEN.

## Owner flags (need one-line answers)
- (a) `computational theory` -> emerging: **demote the label** (remove from menu, 16 rows -> emerging) **OR**
  **keep as reserved slot** (rows stay `computational theory`)? Literal reading of "-computation theory -
  emerging" is demote; "stays emerging" in the summary is ambiguous. Default = demote unless overridden.
- (b) IR->IS merge crosses macro groups (Technical -> Method & Business for 9 rows). Acceptable, or pin IR under
  a different group?
- (c) Approve proposed promotion groups/definitions: creative writing -> Heterodox ("The craft and study of
  composing original narrative, prose, and poetry across forms and media"); museum studies -> Systems & Method
  ("The study of museums and heritage institutions — curation, collection management, interpretation, and public
  education"). (`creative writing studies`, 1 row, resolves via alias_map, not a separate promotion.)
