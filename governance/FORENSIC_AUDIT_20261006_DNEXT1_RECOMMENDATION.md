# FORENSIC AUDIT — D-NEXT-1 (a,b,c) recommendation + two systemic root-causes

Date: 2026-10-06 · Auditor: goose (senior RAG + ontological systems review)
Scope: pre-implementation audit BEFORE any edit to `config/taxonomy_v5.yaml` or minting of `closed_menu_v7.json`.
Status: ADVISORY — awaits owner ratification of D-NEXT-1 + the two new findings below.

---

## Headline (the reframe that changes the plan)

Two previously under-weighted findings mean **D-2853's v7 consolidation plan solves the
wrong-sized problem**. Fix the taxonomy alone and the gate will re-FAIL for the wrong reason.

1. **The production flag-ON path is ATTENTION-OVERLOADED, not mis-taxonomized.**
   Same menu, two prompts: the focused rederive path scored kappa **0.7794**; the
   production multi-task path scored **0.4313**. The 0.35 gap is prompt architecture
   (CRIBS enrichment + 10-field JSON + 7 golden few-shot + ~5k-token menu in ONE call),
   NOT the taxonomy. `BUG-648` (menu ≈ 14,889 chars ≈ 5k tokens) is now implicated as a
   **correctness** contributor, not just cost.

2. **The discipline/domain axis boundary is violated 177 times at the raw-string level.**
   `config/taxonomy_v5.yaml` has 815 unique raw synonym strings; **177 of them map to BOTH
   a discipline AND a domain**. This is the quantitative scope of `BUG-630` (cross-axis
   guard too blunt). D-2853's within-axis merge list touches only **2** exact-string
   within-axis collisions — ~1% of the structural ambiguity.

---

## Finding 1 — cross-axis polysemy (177 raw strings straddle the axis boundary)

Measurement (deterministic, `taxonomy_v5.yaml`):
- 815 unique raw strings; 177 cross-axis (→ both discipline and domain); 2 within-axis.
- Evidence samples:
  - `aerospace engineering` → discipline `engineering` **and** domain `engineering & infrastructure`
  - `computer science` → discipline `software engineering` **and** domain `engineering practice`
  - `control systems engineering` → discipline `engineering`, domain `engineering practice`, **and** discipline `systems engineering`
  - `peircean semiotics` / `biosemiotics` / `cognitive semiotics` / `social semiotics` / `sociosemiotics` / `media semiotics` → discipline `semiotics` **and** domain `semiotics & communication`
  - `business management` → discipline `business administration` **and** domain `business operations`
  - `data management` / `data governance` → discipline `information science` **and** domain `engineering & infrastructure` **and** domain `business operations`
  - `innovation management` → discipline `creative process`, discipline `entrepreneurship studies`, **and** domain `business operations` (the only 3-way)

Consequence: `map_to_canonical_with_fallback` is per-axis so remapping is technically
deterministic, BUT the classifier's D2422 "never mix axes" rule is unenforceable when the
menu itself presents the same source term on both axes. This is the ontological root of both
(i) broad-label over-prediction (design psychology 14, psychology 14, business administration
11, information science 10) and (ii) anchor/referee drift (an anchor about "mechanical
engineering" can be homed on either axis, then remap unambiguously fails).

**Fix**: an axis-purity pass — every raw string gets exactly one home `(axis, canonical)`;
genuinely dual terms are the rare exception and must be explicitly declared + documented.

---

## Finding 2 — prompt architecture dominates the 0.4313 gate failure

Three prompt paths (BUG-655/656 already RESOLVED — the measurement is settled):
- flag-OFF free-gen cribs → **0.3181** (free-gen labels remapped to canonical)
- rederive flag-ON (FOCUSED 2-field classify + menu only) → **0.7794**
- production flag-ON (CRIBS + 10 fields + 7 golden few-shot + menu, one call) → **0.4313**

The rederive `_classify_prompt` (scripts/rederive_anchor_axes_v6.py:391) returns ONLY
`{discipline, domains}`. The production `MERGED_CRIBS_CLASSIFY_SYSTEM` returns 10 fields AND
carries CRIBS enrichment instructions AND 7 injected golden examples. **The menu is byte-
identical in both.** Therefore the 0.35 kappa collapse is attributable to the multi-task
prompt, not the taxonomy.

**Implication**: v7 taxonomy fixes are necessary but NOT sufficient to pass the >= 0.800 gate.
The classifier-of-record must either (i) classify discipline/domains in a focused call separate
from CRIBS enrichment, or (ii) the focused path must be measured against 0.800 before the
multi-task path is accepted as the gate arm.

---

## D-NEXT-1 recommendation (decisive)

**(a) discriminator-first for design psychology / business administration / information science — ADOPT, generalized.**
The three are over-predicted because their discriminators vs. nearest neighbors are thin AND the
multi-task prompt favors salient/broad labels. Add a structured `differentia` (genus = broader
class; differentia = what distinguishes from the nearest 1–2 neighbors) to **every** entry, not
just these three. For the three: make "when-in-doubt → abstain (`emerging`)" binding — emit the
broad label only on positive differentia evidence.
- `design psychology`: differentia = a designed ARTIFACT/decision being optimized. Absent an artifact → psychology / cognitive science / behavioral economics.
- `business administration`: differentia = the academic discipline of org governance; move applied raw (`management science`, `business management`) to domains.
- `information science`: differentia = the discipline of organizing/retrieving/curating information; its raw is a grab-bag (`knowledge management`, `data management`, `data governance` also sit on domains — reassign).

**(b) keep semiotics distinct — ADOPT, with the correct sub-action.** Do NOT fold semiotics into
visual perception (that is a double category error: sign-interpretation vs perceptual-processing,
and genus vs species). Semiotics (general sign theory) is the PARENT of visual semiotics. Correct
action: keep `semiotics` (discipline); fold `visual semiotics` → **into semiotics**; resolve the
`semiotics` ↔ `semiotics & communication` cross-axis duplicate by keeping academic sign-theory raw
terms on the discipline only, leaving the domain with applied/industry terms (communication
design/strategy, business/nonverbal communication).

**(c) include the 7th pair engineering ↔ engineering & infrastructure / engineering practice — ADOPT.**
This is the clearest instance of Finding 1. Keep `engineering` (discipline) = academic fields;
rename/drop the academic fields from `engineering & infrastructure` (domain), keeping applied
(cloud computing, cybersecurity, IT operations, infrastructure); scope `engineering practice`
(domain) = software-engineering-as-practice.

## Future-proofing principle (the structural no-more-drift fix)

1. **Stable IDs, mutable labels.** Every entry gets an immutable opaque `id`; `canonical` becomes
   display-only. Anchors/golden/config/scripts reference `id`, not raw strings — renames cost zero remap.
2. **MECE partition enforced by a build-time validator.** Every raw synonym → exactly one
   `(axis, id)`; fail-closed on violation. Mechanical enforcement of D2422 that the YAML currently
   violates 177×.
3. **Discriminator-first definitions.** genus + differentia + nearest-neighbor exclude for every entry.
4. **Prompt-architecture decision first** (Finding 2) — else the gate re-fails for the wrong reason.

---

## Next critical steps (strategic order)

### Decisions (owner ratification required)
- **D-NEXT-1**: ratify (a) discriminator-first generalized, (b) keep semiotics + fold visual semiotics into semiotics, (c) include the engineering 7th pair.
- **D-2855** (new): adopt future-proofing — stable IDs + MECE partition validator + discriminator-first; freeze the ID space in v7.
- **D-2856** (new): prompt-architecture root-cause — split S4 discipline/domains classification from CRIBS enrichment (or measure the focused path vs 0.800) BEFORE treating the multi-task path as classifier-of-record.

### Bugs
- **BUG-630** (OPEN): scope now quantified at 177 cross-axis raw strings; v7 must resolve via axis-purity, not blunt `emerging` fall-through.
- **BUG-648** (OPEN/cost): 5k-token menu preamble now also a CORRECTNESS (attention-dilution) finding.
- **BUG-658** (OPEN): awaiting harness relaunch to close (root fix D-2854 landed).
- **BUG-NEW** (proposed): production flag-ON conflates CRIBS enrichment with menu classification → attention dilution; propose splitting the discipline/domains call.

### Tasks (post-ratification, atomic order)
1. Add `config/taxonomy_invariants` validator (MECE: 1 raw → 1 (axis,id); no dup canonical; all have genus+differentia).
2. Apply v7 map to `taxonomy_v5.yaml` WITH stable IDs + axis-purity (177) + discriminator-first.
3. Extend renderer to emit `id`; `render_closed_menu.py --mint-version 7`.
4. Re-pin `config/menu_axis_hashes.yaml` + bump `config/version.yaml taxonomy_version`.
5. Remap anchors/golden/config/scripts to stable IDs (or canonical + migration table).
6. Re-run A/B on v7 — only meaningful after D-2856 (prompt split) is decided, else re-FAIL for the wrong reason.

---

## Governance sync (done this turn)
- Confirmed BUG-655/656 RESOLVED; BUG-658 ROOT-FIXED (D-2854) and stays OPEN until relaunch.
- No contradiction found among D-2852/D-2853/D-2854 (registry next-free id = 2855, count 984).
- This audit records 2 NEW findings (cross-axis 177; prompt-arch 0.4313 vs 0.7794) — recommend
  folding into D-2853 scope or minting D-2855/D-2856 on ratification.
- `config/taxonomy_v5.yaml` NOT edited this turn (blocked on owner ratification).
