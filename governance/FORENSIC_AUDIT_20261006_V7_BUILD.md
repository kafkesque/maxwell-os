# Forensic Audit — v7 Build Readiness + Governance Sync (2026-10-06)

Pre-implementation audit (D-2853 = "build closed_menu_v7.json"). Goal: find anything that
would break / cascade / drift / blindspot / gap / conflict / bug / hidden-fail / error-leak /
mismatch / bloat BEFORE touching the taxonomy.

## 0. Headline finding — the menu is DERIVED, not hand-edited
`config/closed_menu_v6.json` is a FROZEN SNAPSHOT. The LIVE source of truth is
`config/taxonomy_v5.yaml` (+ `config/content_types.yaml`), rendered by
`pipeline/closed_menu.py::render_closed_menu()` on every pipeline call
(`stage4_merged_call.py`, `stage4_merge.py`). The answer-space pin lives in
`config/menu_axis_hashes.yaml#answer_space_hash`.

**Consequence:** editing `taxonomy_v5.yaml` changes the live answer space IMMEDIATELY.
Building v7 is therefore INSEPARABLE from the remap — a partial edit = silent drift (the
exact failure mode the owner flagged). The v7 build is an ATOMIC unit:

```
edit taxonomy_v5.yaml (merge + rename + discriminator)
  -> render_closed_menu.py --mint-version 7   (mint closed_menu_v7.json + .sha256)
  -> scripts/menu_axis_hashes.py               (re-pin answer_space_hash)
  -> REMAP anchors/golden/configs/scripts       (drift guard)
  -> re-run A/B on v7                           (adopt only if kappa -> >= 0.800)
```

## 1. Forensic findings (11 dimensions)

| dim | finding |
|---|---|
| **break** | `taxonomy_v5.yaml` entries already carry `raw` (synonym→canonical) + `exclude` (near-dup discriminator). Removing a canonical removes its `raw` routing — merged labels' `raw` MUST be folded into the survivor or classification of those strings breaks. |
| **cascade** | 7 merge clusters + 7 cross-axis renames ripple into `menu_axis_hashes.yaml`, `menu_axis_groups.yaml`, anchor manifests, golden examples, `alias_map`/`domain_disciplines` maps, and any script string-comparing labels. |
| **drift** | Unremapped anchors/golden keep stale label strings → A/B on v7 would count a correct merge as a "disagreement". Remap is a hard prerequisite. |
| **blindspot** | The disagreement data shows the classifier has TWO catch-all labels — `design psychology` (14 predictions) and `business administration` (11) — that together absorb **25/111 (22%)** of disagreements. NEITHER is in D-2853's merge list. |
| **gap** | D-2853's merge clusters are drawn from the audit's *near-synonym inventory*, not the *disagreement data*. Cluster 1 (ML/genai/AI) touches only ~2–3 disagreements; cluster 3 (psychology family) touches ~10. Merge impact is uneven. |
| **conflict** | D-2853 lists 6 cross-axis renames; the AB_VERDICT audit lists 7 (adds `engineering ↔ engineering & infrastructure / engineering practice`). Minor scope mismatch to resolve. |
| **bug** | BUG-658 (client wedge) ROOT-FIXED this turn; stays OPEN until relaunch reproduces no-wedge. BUG-630 (cross-axis guard too blunt) stays OPEN until v7 lands. |
| **hidden-failure** | `semiotics` appears in BOTH a merge cluster (→ `visual perception`) AND cross-axis rename #6 (↔ `semiotics & communication`). Merging it into `visual perception` is semantically wrong (general sign-theory ≠ biological vision). Cluster #4 needs a judgment call, not a literal merge. |
| **error-leak** | none found this turn (root fix `_post_with_wall_clock` raises WallClockTimeout cleanly; retry path logs + sleeps). |
| **mismatch** | `config/version.yaml` still reads `taxonomy_version: v5.7`; after the v7 taxonomy edit it must bump (else the version gate disagrees with the menu). |
| **bloat** | 65 disciplines + 44 domains = 109 labels with heavy overlap (7 near-synonym families, 7 cross-axis near-twins). Merging is the de-bloat; do it via `raw` folding, not label deletion (provenance). |

## 2. Concrete v7 consolidation map (proposed)

### 2a. MERGE (within-axis) — survivor keeps `value`; merged labels removed, `raw` folded into survivor
| axis | merged → survivor | disagreement impact |
|---|---|---|
| discipline | `machine learning`, `generative ai` → `artificial intelligence` | low (~2) |
| discipline | `systems engineering`, `complex adaptive systems` → `systems thinking` | low |
| discipline | `cognitive science`, `decision making`, `behavioral economics` → `psychology` | **high (~10)** |
| discipline | `visual semiotics` → `visual perception` (KEEP `semiotics` distinct) | medium |
| domain | `computational art`, `creative technology` → `code & computation` | low |
| domain | `product design`, `web & ui`, `user experience`, `information architecture` → `digital product` | low |
| domain | `business operations`, `organizational behavior` → `business development` | medium |

### 2b. RENAME (cross-axis near-twins) — sharpen definitions + cross-link `exclude`
Strings already differ; the fix is axis-scoped DISCRIMINATORS, not literal renames:
`artificial intelligence`↔`ai & agents`; `finance`↔`finance & investment`;
`marketing`↔`marketing & communications`; `entrepreneurship studies`↔`entrepreneurship`;
`research methodology`↔`research & methodology`; `semiotics`↔`semiotics & communication`;
`engineering`↔`engineering & infrastructure`/`engineering practice`.

### 2c. DISCRIMINATOR (higher kappa impact than most merges) — sharpen the catch-alls
- `design psychology` (14 over-pred): definition already "cognitive-bias exploitation in
  design"; ADD a one-line scope: "applies ONLY when the principle is a named bias/heuristic
  exploited in a design artifact — NOT general mind/behavior, NOT perception."
- `business administration` (11 over-pred): add scope vs `finance`/`marketing`/`operations
  research` (org structure/coordination only).
- `information science` (10 over-pred): add scope vs `research methodology`/`information
  retrieval` (collection/organization of information, NOT research method design).

## 3. Next critical steps (strategic order)
**DECISIONS (owner):**
- **D-NEXT-1**: confirm v7 map refinements — (a) discriminator-first for the 3 catch-all
  labels, (b) keep `semiotics` distinct (do NOT fold into `visual perception`), (c) include
  the 7th cross-axis pair (`engineering`). If owner wants D-2853 verbatim (no refinements),
  that is also a decision.

**BUGS:**
- BUG-658 (OPEN) — root-fixed (D-2854); closes only on relaunch reproducing no-wedge.
- BUG-630 (OPEN) — closes when v7 lands + remap done.

**TASKS (in order):**
1. **[GATED — owner "relaunch"]** relaunch flag-ON A/B → confirm preflight + no wedge +
   reproduce kappa 0.4313 → close BUG-658.
2. Apply §2 map to `taxonomy_v5.yaml` (merge via `raw`-folding, sharpen discriminators).
3. `render_closed_menu.py --mint-version 7` → `closed_menu_v7.json` + `.sha256`.
4. Re-pin `menu_axis_hashes.yaml`; bump `config/version.yaml#taxonomy_version`.
5. **Remap** all anchor/golden/config/script label references to v7 (drift guard).
6. Re-run A/B on v7 → adopt only if kappa improves toward >= 0.800.

## 4. Governance sync performed this turn
- `governance/buglog.md` BUG-658 heading: "pending owner ack" → "ROOT-FIXED (D-2854)".
- `governance/bug_status.md` + `.json` regenerated (`scripts/bug_status.py`): OPEN 161 /
  CLOSED 261 of 422; BUG-658 + BUG-630 correctly still OPEN.
- No contradictions remaining: DECISION-LOG D-2852/D-2853/D-2854 ↔ MTR ↔ session_seed ↔
  decisions.yaml ↔ buglog are consistent (D-A verdict, taxonomy C, D-B root fix all landed).
