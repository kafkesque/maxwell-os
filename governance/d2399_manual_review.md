# D2399 — Manual Review Instructions (UPDATED 2026-09-05 — user decisions recorded)

> **What this is:** 292 FBs have `discipline = 'emerging'` with a *genuine* non-empty
> `discipline_raw` that does not resolve to any of the 61 canonical disciplines.
> `d2399_promotions_frozen: true` (in `config/pipeline_config.yaml`, line ~471)
> blocks auto-promotion because the D2521 auto-promote was semantically wrong.

## ⚠️ NEW REVELATION (verified 2026-09-05) — the 292 split into TWO classes

A fresh `match_to_canonical(raw, kind)` audit of the **292** gap FBs reveals the
population is NOT homogeneous. Splitting by which axis the raw label resolves on:

| Class | Count | Meaning | Correct action |
|---|---|---|---|
| **KIND-LEAK** | **42 FBs** | raw label resolves to a **DOMAIN** canonical only — it is a domain label that leaked into the `discipline_raw` slot (BUG-197) | **kind-swap** (move to domain axis, clear `discipline_raw`) — *not* a discipline gap |
| **TRUE-GAP** | **250 FBs** | raw label resolves on **neither** axis — a genuine long-tail discipline label | map / promote / leave (the A/B/C/D rules below) |

> This is why the earlier "250 D2399 gaps" figure kept coming up: **250 is the
> true-gap count.** The other 42 are kind-leaks, which were never "gaps" at all —
> they were domain labels sitting in the wrong column.

## The population (live-verified 2026-09-05)

- **292** FBs, **257** distinct raw labels.
- **42** kind-leaks (domain labels in `discipline_raw`) — 6 recurring labels.
- **250** true gaps — 18 recurring labels, 233 singletons (leave as `emerging`).

## The decision rule (one of 4 actions, per recurring label)

| # | Action | When | Where |
|---|---|---|---|
| **A** | **MAP** to an existing canonical discipline | raw label is a synonym/variant of one of the 61 canonicals | add to `config/alias_map.yaml` → `discipline_aliases` |
| **B** | **KIND-SWAP** to the domain axis | raw label is really a *domain*, not a discipline (cross-kind leak) | move the raw label to `domains_raw`; clear `discipline_raw`; `discipline` stays `emerging` (BUG-197) |
| **C** | **PROMOTE** to a new canonical discipline | ≥ 5 stable FBs **and** a clear definition **and** you confirm it is a real field not covered by an existing canonical | ⚠️ **closed-loop (D2378): promotion requires demoting the weakest canonical — cardinality stays 61.** See §Ecology below. |
| **D** | **LEAVE** as `emerging` | nothing above applies (honest "no canonical fits") | nothing — `emerging` is the open-world state, not a failure |

## ✅ YOUR FINAL DECISIONS (2026-09-05) — recorded

| Raw label | n | Class | Your decision | Action to take |
|---|---|---|---|---|
| Ecology | 5 | true-gap | **C** (promote) | ⚠️ needs closed-loop demotion — see §Ecology |
| Marketing | 4 | kind-leak | **B** (kind-swap) | move to `marketing & communications` domain, clear `discipline_raw` |
| financial engineering | 2 | kind-leak | **A** (map → `finance`) | add `discipline_aliases`; note it is *also* a domain alias → `finance & investment` (dual-axis) |
| Design Studies | 2 | kind-leak | **A** (map → `design thinking`) | add `discipline_aliases`; note it is *also* in `design strategy` domain `raw[]` (dual-axis) |
| history of philosophy | 2 | true-gap | **A** (map → `philosophy`) | add `discipline_aliases` |
| Medical Humanities | 2 | true-gap | **A** (map → `health & medicine`) | add `discipline_aliases` |
| Experimental Psychology | 2 | true-gap | **A** (map → `psychology`) | add `discipline_aliases` |
| Educational Measurement | 2 | true-gap | **A** (map → `research methodology`) | add `discipline_aliases` |
| Musicology | 4 | true-gap | **D** | leave |
| Applied Mathematics | 4 | kind-leak | **D** | leave (note: could kind-swap later) |
| audio signal processing | 3 | true-gap | **D** | leave |
| History of Technology | 3 | true-gap | **D** | leave |
| photography | 2 | kind-leak | **D** | leave (note: could kind-swap later) |
| management consulting | 2 | kind-leak | **D** | leave (note: could kind-swap later) |
| Transportation Engineering | 2 | true-gap | **D** | leave |
| Medical Imaging | 2 | true-gap | **D** | leave |
| Architectural History | 2 | true-gap | **D** | leave |
| creative industry studies / Sustainability Studies / Signal processing / Materials Science / Intelligence Studies / Creative Economy Studies / Business Administration | 2 each | true-gap | **D** | leave |

### Dual-axis notes (verified, not errors)

- **`financial engineering`** is already a *domain* alias → `finance & investment`
  (load-bearing: 11 FBs use it as a domain). Your **A** decision adds a *discipline*
  alias → `finance`. The two coexist on separate axes (a label may legitimately be
  both a sector and a field). No conflict, no breakage.
- **`Design Studies`** already appears in the `design strategy` *domain* `raw[]` list.
  Your **A** decision adds a *discipline* alias → `design thinking`. Same dual-axis
  coexistence.

## §Ecology — the one promotion (C) has a hidden prerequisite

> ✅ **RESOLVED 2026-09-05 (D2573):** user chose **option 1** — `ecology` promoted to
> canonical, `computer networking` (4 FBs) demoted to `displaced`. Cardinality
> 61→61. Applied via `scripts/apply_d2399_ecology_promotion.py` (gemma R5 APPROVE).

D2378 established a **closed-loop**: the discipline cardinality is fixed at **61**, so
promoting `ecology` requires **demoting the weakest canonical discipline**. Verified:

- Weakest canonical discipline today: **`computer networking` (4 FBs)**.
- `ecology` emerging count: **5** (raw status, `taxonomy_counts`).
- `REPLACEMENT_THRESHOLD_RATIO = 1.10` → `5 > 4 × 1.10` ⇒ `ecology` **qualifies** to displace `computer networking`.

**This demotion is NOT implied by your "C" mark** — it is a separate, consequential
decision. I have **not** demoted anything. Choose one:

1. **Approve demotion of `computer networking` (4 FBs)** — I then add `ecology`
   (definition below) to `config/taxonomy_v5.yaml`, unfreeze, apply the replacement,
   re-freeze. `computer networking` reverts to `raw` (still retrievable via the
   raw-label surface, per D2536).
2. **Pick a different demotion candidate** from the weakest list:
   `computer networking` (4), `privacy & surveillance` (5), `design psychology` (6),
   `generative design` (6), `computational theory` (6).
3. **Reject the promotion** — keep `ecology` as `emerging` (open-world), no demotion.

> Draft `ecology` definition (Qwen3.8 authoring + gemma cross-family review pending,
> same as the P1 ontology layer): *"The scientific study of the relationships between
> organisms and their physical and biological environments."* Suggested group:
> **Systems & Method** (co-located with `evolutionary biology`).

## Step-by-step (what YOU actually do)

1. **Confirm the Ecology demotion choice** above (1 / 2 / 3). Everything else is
   already implemented per your A/B decisions (see the "After you act" checklist).
2. If you chose **(1)**, I run the closed-loop promotion + demotion.
3. If you chose **(3)**, no further action — `ecology` stays `emerging`.

## What you should NOT do

- ❌ Do **not** bulk-promote the 233 singletons (honest long-tail open-world labels).
- ❌ Do **not** auto-promote on raw frequency alone (this is what D2521 got wrong).
- ❌ Do **not** create a new canonical for a label with < 5 FBs.
- ❌ Do **not** delete the raw labels — they are preserved provenance.
- ❌ Do **not** demote a canonical discipline without an explicit choice — the
  closed-loop (D2378) keeps cardinality at 61.

## After you act

- The 6 discipline aliases and the Marketing kind-swap are applied by
  `scripts/apply_d2399_user_decisions.py` (this session).
- Record each decision as a new decision (D2572+) in `config/decisions.yaml` and
  re-sync `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `agent/session_seed.yaml`.

> **Reference:** `governance/ROUNDTABLE_HANDOFF_D2569_ADJUDICATED_2026-09-05.md` §6 item 8,
> the 61 canonical disciplines in `config/taxonomy_v5.yaml`, and D2378 (closed-loop promotion).
