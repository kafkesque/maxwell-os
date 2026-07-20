# Domain Labelling — Governance (D1055-FIX)

> **Status:** V1 REFERENCE — principles preserved, scripts differ in v2 | **Schema version:** 2026-07-16.D834 | **Last verified:** 2026-07-17
>
> **⚠️ V2 NOTE (2026-07-19):** This document describes v1's field structure and script registry. v2 implements the SAME PRINCIPLES (raw preservation, canonical matching, folder routing priority chain, contamination prevention) but with different fields and scripts:
> - v1: `domain` / `domain_canonical` / `domain_raw` (single strings) → v2: `domains` / `domains_raw` (lists), `discipline` / `discipline_raw` (strings)
> - v1 scripts (s3_converge_local.py, s5_bridge.py, classify_domains.py, etc.) → v2: single-pass SALSA in `stage4_merge.py`, synonym matching in `schemas.py`
> - v1 folder routing (scattered across 8 files) → v2: consolidated in `pipeline/route.py` (140 lines)
> - P1.5-A/B/C/E implemented all core guarantees in v2. See `MASTER-TASK-REGISTER.md` §P1.5.
>
> Single source of truth for domain/discipline field semantics, depth-based rules,
> folder routing, contamination prevention, and script responsibilities.

---

## 1. Field Semantics

| Field | Type | Set by | Semantics | Immutable? |
|-------|------|--------|-----------|------------|
| `domain` | string | LLM (S3a) | Model's raw domain classification output. **Never overwritten.** | After S3a, yes |
| `domain_canonical` | string | `_validate_principle_schema()` | Validated taxonomy domain, or `"emerging"` if no canonical match | After S3a, yes |
| `domain_raw` | string | `_validate_principle_schema()` + `init` backfill | Model's original label when non-canonical. Used for folder grouping. | After S3a, yes |
| `domain_canonical_multi` | string | `classify_domains_multi.py` (legacy) | Comma-separated canonical domains for cross-domain/universal FBs. Capped at 3. | Set during classification |
| `discipline` | string | LLM (S3a) | Model's raw discipline classification. **Never overwritten.** | After S3a, yes |
| `discipline_canonical` | string | `_validate_principle_schema()` | Validated taxonomy discipline, or `"emerging"` | After S3a, yes |
| `discipline_raw` | string | `_validate_principle_schema()` | Model's original label when non-canonical | After S3a, yes |
| `s3_original_domain` | string | `_add_stamps()` in S3a | **Crawl provenance** — the pipeline cluster domain (e.g., `"domain_5_self_help"`). Immutable. | **YES** |
| `depth` | enum | LLM (S3a) | `"domain"` \| `"specialized"` \| `"cross-domain"` \| `"universal"` | After S3a, yes |

### Key principle

**`s3_original_domain` is crawl provenance, NOT classification.** It answers "which pipeline cluster did this come from?", not "what domain does this principle belong to?". It is never used for folder routing or domain labelling. It is never overwritten with classification labels.

---

## 2. Canonical Taxonomy

Source: `config/taxonomy_v5.yaml`

- **25 canonical domains** (architecture, art, biology, business, chemistry, computer science, design, economics, education, engineering, entrepreneurship, finance, history, law, linguistics, literature, mathematics, medicine, music, philosophy, physics, political science, psychology, self-help, sociology)
- **47 canonical disciplines** (accounting through zoology, see taxonomy_v5.yaml)
- **Special labels**: `"emerging"` (non-canonical, valid as canonical fallback), `"unclassified"` (not yet classified)

---

## 3. Data Flow

```
S3a LLM output (raw domain/discipline)
        │
        ▼
_validate_principle_schema()
  ├─ domain is non-canonical? → domain_raw = domain, domain_canonical = "emerging"
  ├─ domain is canonical?     → domain_canonical = domain.lower()
  ├─ domain is empty/emerging? → domain_canonical = "emerging"
  └─ domain field NEVER overwritten
        │
        ▼
init_classification_fields.py (post-hoc / re-init)
  ├─ Seeds domain_canonical if missing
  ├─ Backfills domain_raw from domain when canonical="emerging"
  ├─ NEVER overwrites s3_original_domain
  └─ Cleans stale domain_canonical_multi (non-canonical → "emerging")
        │
        ▼
S5 Bridge: _build_multi_domain() + _build_metadata()
  ├─ depth=domain/specialized → DOMAINS = domain_canonical (single)
  ├─ depth=cross-domain/universal → DOMAINS = domain_canonical_multi (capped 5, universal min 3)
  └─ Embed [DOMAIN_RAW], [DOMAIN_CANONICAL] in metadata
        │
        ▼
S5 Generate / S6 Pipeline / S6 Export → Folder routing
  └─ Priority: domain_canonical (if valid) → domain_raw → domain or "emerging"
```

---

## 4. Depth-Based Domain Rules

| Depth | DOMAINS source | Multi-domain? | Cap |
|-------|---------------|---------------|-----|
| `domain` | `domain_canonical` | **No** — single label | 1 |
| `specialized` | `domain_canonical` | **No** — single label | 1 |
| `cross-domain` | `domain_canonical_multi` | **Yes** — when populated (≥2) | 5 |
| `universal` | `domain_canonical_multi` | **Yes** — when populated (≥3) | 5 |

**Critical rule**: `domain` and `specialized` depth FBs **always** use single domain. Even if `domain_canonical_multi` is populated, it is **ignored** by `_build_multi_domain()`.

**Fallback**: When `domain_canonical_multi` is empty, stale, or "emerging", cross-domain/universal FBs fall back to the primary `domain_canonical` as single domain.

---

## 5. Folder Routing

All output stages (S5 generate, S6 pipeline, S6 export resume, preflight D799, pipeline gate) use the **same priority chain**:

```
1. domain_canonical    (if valid canonical — not "emerging", not "unclassified")
2. domain_raw          (model's original label — preserved for semantic grouping)
3. domain              (model output — fallback)
4. "emerging"          (last resort)
```

`s3_original_domain` is **never used** for folder routing.

### Guarantee

When `domain_canonical = "emerging"`, `domain_raw` is **always populated** (set by `_validate_principle_schema()` or backfilled by `init_classification_fields.py`). The folder chain always finds a semantic label before reaching "emerging". This is verified on live data (0/214 failures on domain_5_self_help).

### Example

```
FB: "Memory emerges from neural network connections..."
  domain = "neuroscience"          (model output, preserved)
  domain_canonical = "emerging"    (not in canonical taxonomy)
  domain_raw = "neuroscience"      (preserved for folder)

  Folder: 5.generated/neuroscience/{slug}-fbs.md  ✓
  NOT:    5.generated/emerging/{slug}-fbs.md      ✗
```

---

## 6. Contamination Prevention

Three channels were identified and eliminated:

| Channel | Cause | Fix | Verified |
|---------|-------|-----|----------|
| **A: Asymmetrical discipline pre-filtering** | `_get_domain_disciplines()` filtered disciplines by crawl domain name coincidence | Always pass all 47 canonical disciplines | ✅ |
| **B: Silent schema validation erasing labels** | `_validate_principle_schema()` overwrote `domain` to "emerging" | Preserve `domain`, set separate `domain_canonical` | ✅ |
| **C: D1056 overwriting provenance** | `init_classification_fields.py` overwrote `s3_original_domain` with discipline | Remove overwrite; preserve crawl provenance | ✅ |

### Validation results

- **Sandbox**: 12/12 edge cases passed; 6/6 cross-cutting guarantees verified
- **Live data** (domain_5_self_help, 214 principles): 0 contamination, 0 emerging-without-raw failures, 0 s3_original=discipline

---

## 7. Script Registry

| Script | Reads | Writes | Responsibility |
|--------|-------|--------|----------------|
| `s3_converge_local.py` | domain, discipline | domain_canonical, domain_raw, discipline_canonical, discipline_raw | Primary validation during S3a |
| `init_classification_fields.py` | all fields | domain_canonical, domain_raw (backfill) | Post-hoc field seeding + backfill |
| `s5_bridge.py` | domain_canonical, domain_raw, depth | metadata + top-level keys | Bridge to S5; depth-based multi-domain |
| `s5_generate_local.py` | domain_canonical, domain_raw | folder routing | FB generation + folder output |
| `s6_pipeline.py` | domain_canonical, domain_raw | folder routing | T2/T3 eval + S7 export |
| `s6_export_resume.py` | domain_canonical, domain_raw | folder routing | Resume export |
| `schemas.py` | — | FB schema | Schema definition with new fields |
| `normalize_casing.py` | domain_canonical, domain_raw, discipline_canonical, discipline_raw | same (lowercased) | Casing normalization |
| `build_knowledge_db.py` | domain_canonical, domain_raw, s3_original_domain | SQLite DB | Knowledge DB storage |
| `pipeline_gate.py` | domain_canonical, domain_raw | — | G7/G0 folder validation |
| `preflight.py` | domain_canonical, domain_raw | — | D799 folder validation |
| `validate_pipeline.py` | domain_canonical, domain_canonical_multi | — | Label validation |
| `eval_loop.py` G16 | domain_canonical, DOMAINS | — | Domain label integrity check |
| `classify_domains.py` | domain_canonical | domain_canonical | Domain classification (existing) |
| `classify_disciplines.py` | domain_canonical | discipline_canonical | Discipline classification |
| `fix_domain_discipline.py` | domain_canonical, discipline_canonical | domain_canonical, discipline_canonical | Constraint-based fixes |

---

## 8. Guarantees (Verified)

| # | Guarantee | Sandbox | Live Data | Mechanism |
|---|-----------|---------|-----------|-----------|
| 1 | `domain_raw` always populated when `dc="emerging"` | ✅ | ✅ 0/214 failures | `_validate_principle_schema` + init backfill |
| 2 | `domain` field never overwritten | ✅ | ✅ preserved | Schema validation preserves original |
| 3 | Domain-depth FBs → single domain | ✅ | ✅ | `_build_multi_domain` ignores multi for domain/specialized |
| 4 | Cross-domain/universal → multi (when populated) | ✅ | ✅ | `_build_multi_domain` reads `domain_canonical_multi` |
| 5 | Folder: canonical → raw → fallback | ✅ | ✅ 0 "emerging" folders | Consistent across all 3 routing points |
| 6 | `s3_original_domain` = immutable crawl provenance | ✅ | ✅ 0 overwrites | Never set to classification label |
| 7 | No canonical labels leak into `domain_raw` | ✅ | ✅ | Non-canonical check in `_validate_principle_schema` |
| 8 | Multi capped at 5, universal ≥3 | ✅ | ✅ | `_build_multi_domain` slices `parts[:5]` + gate enforces |

---

## 9. Decision History

| Decision | Date | Summary |
|----------|------|---------|
| D1051 | 2026-07-13 | Established `s3_original_domain` as crawl provenance |
| D1055-FIX | 2026-07-17 | Three-channel contamination fix + new field structure |
| D1056 | 2026-07-16 | Redefined `s3_original_domain` as classification → **superseded by D1055-FIX** |

---

## 10. Related Documents

- `CONSTITUTION.md` — R5 (Generator ≠ Verifier), R7 (temp=0.0), R14 (stamping)
- `config/taxonomy_v5.yaml` — canonical domains and disciplines
- `DECISION-LOG.md` — full decision history
- `tools/sandbox/sandbox_depth_domain_guarantee.py` — validation test suite
