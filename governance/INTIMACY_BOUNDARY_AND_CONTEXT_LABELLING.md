# Intimacy Boundary + Context Labelling — Logic Audit (old agreement vs current)

> **Date:** 2026-08-14 · **Scope:** `intimacy_boundary` (public/selective/private) and the
> related `context` property-labelling logic. **Method:** compare current code against the
> v2.0 "old library" (`pipeline/_schemas_OLD.py` + `config/pipeline_config.yaml` @ c95f7ff).

---

## 1. The field, today

`intimacy_boundary` is a **space-routing** field (which Anytype *space* an FB lands in):

| Value | Meaning |
|---|---|
| `public` | Knowledge base (Anytype `non_private` space) |
| `selective` | (intermediate tier) — routes to private space |
| `private` | the user's private Anytype space, whose **literal space name is `"deathpectation"`** (RESOLVED 2026-08-15) |

`context` is a **property label** (routing hint), per `schemas.py:652`:
> "Comma-separated multi-select: business, design, system, academic, personal. Never free text."

---

## 2. Current implementation (the problem)

`pipeline/stage4_merge.py:1349-1350`:
```python
# intimacy_boundary: default public for pipeline FBs (user can override)
intimacy_val = "public"
```

Every pipeline FB is hardcoded to **`public`**. The old public/private/selective routing
logic is **not applied** — it was dropped during the v2→v3 refactor.

`context` is now derived by a **heuristic domain-set intersection**
(`stage4_merge.py:1309-1333`), NOT by the old multi-select classification:
- `business_signals`, `design_signals`, `system_signals`, `academic_signals` sets
  intersected against `class_data["domains"]` → `business|design|system|academic`,
  default `personal`.

So both fields exist in the schema and are persisted, but their **derivation logic** is
either hardcoded (`intimacy_boundary`) or heuristic (`context`), not the old rule set.

---

## 3. The "old agreement" (v2.0) — what used to be applied

Recovered from the initial commit `c95f7ff` (v2.0). The logic lives in
`config/pipeline_config.yaml` under `properties.routing`:

### 3a. `content_based` routing (discipline → intimacy)
```yaml
content_based:
  personal_disciplines:
    - personal productivity
    - psychology
    - cognitive science
    - decision making
    - behavioral economics
  design_business_domains:
    - graphic design
    - brand identity
    - … (design + business domains)
  rule: If discipline in personal_disciplines AND no design_business_domains -> Private
```

### 3b. `label_based` routing (label → intimacy)
```yaml
label_based:
  d383: PERSONAL in context (solo or mixed) -> Private
  intimacy: private or selective -> Private
  default: public -> Non-Private
```

### 3c. Combined effect (old)
An FB was **Private** if **any** of:
1. `discipline ∈ personal_disciplines` AND `domains ∩ design_business_domains == ∅`, **or**
2. `context` label contains `PERSONAL` (solo or mixed), **or**
3. an explicit `intimacy` label was `private` or `selective`.

Otherwise → **public** (Non-Private).

### 3d. The old library (`pipeline/_schemas_OLD.py`)
- `class IntimacyBoundary(str, Enum)`: `public | selective | private` (identical to today's
  `INTIMACY_LITERAL`).
- `_classified_intimacy`, `_classified_context`, `_classified_accessibility`,
  `_classified_evidence` were **bridge-classified fields — deterministic, no LLM**
  (annotated `D1058`). i.e. the old system derived these via *rules*, not a model.

---

## 4. Gap summary

| Field | Old (v2.0) | Current (v3.0) | Drift? |
|---|---|---|---|
| `intimacy_boundary` | rule-derived (`personal_disciplines` + context `PERSONAL` + explicit label) → public/private/selective | **hardcoded `"public"`** | **YES — routing logic lost** |
| `context` | classified multi-select `business, design, system, academic, personal` (bridge, deterministic) | heuristic domain-set intersection → business/design/system/academic, default `personal` | **PARTIAL — semantics preserved, mechanism changed** |
| `accessibility` | `self-evident | prerequisite` (bridge) | derived: prereqs OR (expert AND def>200) → `prerequisite`, else `self-evident` | approx. parity |

---

## 5. The "deathpectation" term — RESOLVED

`"deathpectation"` is the **user's own name for their private Anytype space** (confirmed
2026-08-15). It is not a garbled/personal term or a v1 artifact — it is the literal
Anytype *space* name that the `private` intimacy tier routes into. `config/intimacy_policy.yaml`
**does exist on disk** (created 2026-08-14 by D2356) and its `space_routing:` block maps
`private`/`selective` → the private space; `public` → `non_private`.

**Status:** ✅ RESOLVED — `"deathpectation"` = private Anytype space name. It is an
operational identifier (the user's space), not a schema enum value. `schemas.py`/`schema_accessor.py`
correctly keep the generic `"private space"` description (the literal space name is an
Anytype-side concern, not a pipeline taxonomy term).

---

## 6. Recommendation (what to restore, what to leave)

1. **Restore the `intimacy_boundary` rule** as a config-driven routing function
   (C12: move `personal_disciplines` / `design_business_domains` / label rules into
   `config/*.yaml`, not code). Default remains `public`; only discipline/context hits flip
   it to `private`/`selective`.
2. **Keep `context` heuristic** but document it as the successor to the old bridge
   classification (or restore the bridge if deterministic parity is required).
3. ~~Define or drop `"deathpectation"`~~ → **RESOLVED (2026-08-15):** it is the user's private
   Anytype space name, an operational identifier, not a taxonomy enum value.
4. `intimacy_boundary` must remain a **metadata/property** field (not body), consistent with
   D2349 — it is routing, not readable knowledge.
