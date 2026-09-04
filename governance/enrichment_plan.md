# ENRICHMENT ACTION PLAN — cross-disciplinary FB retrievability

> **Principle (from retrieval architecture):** retrieval is semantic-first
> (FTS + vector on definition/keywords), and `domains` is a JSON **array** so one
> FB can live in multiple scopes. A cross-disciplinary FB must therefore carry
> **all** the canonical domains it genuinely serves — otherwise facet-filtered
> retrieval misses it. Enrichment = ADD missing domains (keep existing), never
> collapse a multi-scope FB to one bucket.

## Backlog (measured 2026-09-04)

| Group | Count | Status |
|---|---|---|
| Human-review cross-disciplinary (relabel plan) | 11 FBs | classified below |
| Single concrete domain + 2+ raw labels (immediate enrich) | **1,926 FBs** | needs raw→canonical re-map |
| `discipline == emerging` | 1,842 FBs | Track B resolve first |
| `domains` contains `emerging` | 1,562 FBs | Track B resolve first |

---

## Phase 1 — the 11 human-review FBs (concrete actions)

### Enrich (add missing scope, keep existing)
| FB | add | keep |
|---|---|---|
| Color As Cultural and Emotional Marker | `social sciences` | graphic design, brand identity, marketing & communications | add

### Retarget (replace a wrong domain)
| FB | remove | add | keep |
|---|---|---|---|
| Structural Theory Foundation | business operations | `design strategy` | product design | add
| Community Mapping Project Coordination | legal & public policy | `project management` | health & wellness, urban planning | add
| Figma Ai Development Tools | project management; user experience | `web & ui` | digital product | add
| Figma Hamburger Icon Creation | user experience | `web & ui` | graphic design, digital product, design systems | add

### Deregister (remove wrong catch-all only)
| FB | remove |
|---|---|
| Project Structure in Motion Design | editorial & advertising | keep
| Visual Builder Layer for Agentic Ai | project management | remove
| Apple Design Philosophy | business operations, project management | remove
| Toxic Material Embedding in Electronics | legal & public policy, project management | remove
| Logo Design Evaluation Criteria | editorial & advertising | keep
| Job-to-be-done Framework | project management | keep

---

## Phase 2 — systematic enrichment (1,926 FBs)

1,926 FBs have **one concrete domain but 2+ raw labels** — the canonicalizer
collapsed a multi-scope FB to a single primary domain. Example: `Home Page
Syndrome` → `web & ui` only, but raw = web design / mobile app / UX research.

**Action:** build a raw-label → canonical-domain mapping (from `taxonomy_v5.yaml`
aliases) and ADD the missing canonical domains. This is the core enrichment
operation and directly answers "how do cross-domain FBs stay retrievable".

## Phase 3 — Track B emerging resolution (3,177 FBs), then enrich

`discipline == emerging` (1,842) and `domains ∋ emerging` (1,562) are **unresolved**
— they must go through Track B reclassification (already planned, ~3.5h batch)
to get concrete labels, *then* the same enrichment applies.

---

## Execution order

1. **Phase 1** — apply the 11 concrete enrich/retarget/deregister actions (C13 backup → integrity gate → atomic txn).
2. **Phase 2** — implement the raw→canonical re-map + batch add (1,926 FBs), behind a dry-run.
3. **Phase 3** — Track B `--apply` (resolves `emerging`), then enrich the resolved FBs.
4. Re-run k-NN + T-NLI audits after each phase to confirm the mislabel signal drops.
