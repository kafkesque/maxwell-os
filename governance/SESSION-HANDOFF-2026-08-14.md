# Session Handoff — 2026-08-14 (Canary Deep-Audit: D2349/D2350)

> **State at handoff:** T1.1 canary ran green; a deep audit surfaced identity/provenance
> drift + taxonomy misclassification; both fixed and validated. Rerun decision pending
> external roundtable.

---

## 1. What this session accomplished

### Fix A — D2349: field taxonomy (body / classification / metadata)
`config/content_types.yaml` was drifted — `core_body` contained non-body fields. Now three
orthogonal buckets:

| Bucket | Fields |
|---|---|
| **core_body** (readable knowledge) | `name, definition, mechanism, boundary, consequence, elaboration, jargon` (jargon AFTER elaboration) |
| **classification** (labels/flags) | `content_type, extraction_type, is_summary, domains, discipline, depth, evidence, domains_raw, discipline_raw` |
| **metadata** | `stamps` (R14), `provenance` (`source_books, source_clusters, source_segments, evidence_passages`), `discovery` (`keywords`), `versioning`, `runtime` |

Key clarifications adjudicated with the user:
- **jargon** is **body** (after elaboration), NOT metadata/property.
- **keywords** is **metadata.discovery** (search/retrieval labels), moved OUT of `principle.extension_fields`.
- **evidence** (flag `cited|axiomatic`) ≠ **evidence_passages** (verbatim quotes). `evidence` → classification; `evidence_passages` → `metadata.provenance`.

### Fix B — D2350: S4 identity/provenance integrity (`pipeline/stage4_merge.py`)
1. **fb_id drift** — was re-hashing `make_hash_id(name, definition)` AFTER title-casing →
   73/279 FBs would change identity S2→S4. Now `fb_data.get("fb_id") or make_hash_id(...)`.
2. **source_clusters semantic drift** — was using fb_id as `cluster_id`. Now `fb.get("source_cluster")` (both convergent + singleton paths).
3. **name-collision pollution** — raw 64-char hash suffix → short numeric probe suffix `(2)`, `(3)`, ….

### Governance docs updated
- `DECISION-LOG.md` — D2349 + D2350 added.
- `config/decisions.yaml` — 339 decisions, counts reconciled (verified sums match).
- `MASTER-TASK-REGISTER.md` — 3rd audit adjudication section (B19/B20).
- `governance/buglog.md` — D2350 (fixed) + BUG-107 (single-source leak) added.
- `governance/aggregated_remaining_tasks.md` — header sync.
- `governance/T1.1_ROUNDTABLE_AUDIT_PROMPT_D2349_D2350.md` — NEW roundtable prompt.

---

## 2. Validation results (all green)

| Check | Result |
|---|---|
| `config_audit.py --check-unchecked --strict` | ✅ no drift |
| `just integrity` | ✅ 17/17 |
| `just healthcheck` | ✅ 10/10 |
| `just preflight` (stress + memory + FAISS + SQLite/FTS5) | ✅ ALL_PASS |
| `stage4_merge.py` ast parse | ✅ OK |
| `content_types.yaml` / `decisions.yaml` parse | ✅ OK |
| D2350 comment re-tag (D2349→D2350 in stage4_merge.py) | ✅ 4 refs, 0 stray D2349 |

---

## 3. Remaining OPEN items (not blockers for a canary RE-RUN, but track)

| ID | Severity | Item | Owner |
|---|---|---|---|
| BUG-106 | 🟠 | S2 checkpoint mixed JSONL + pretty-print (102 bad lines). Main writer is JSONL; a second path at `stage2_extract.py:685` uses `indent=2`. Verify the pretty-print path can't reach `STAGE2_CHECKPOINT`. | next session |
| BUG-107 | 🟠 | 2 single-source FBs leaked into DB (`Hybrid Sorting Algorithm`, `Price Reduction Profit Maximization`) despite `--only-convergent`. Root-cause in S2 split-probe k-means. | next session |
| BUG-104 | 🟠 | sqlite-vec `load_extension` missing on python.org Python 3.12.1. FTS fallback works; wire FAISS/TurboVec or switch to Homebrew/conda Python. | env |
| — | 🟠 | S4 speed ~3.5 FBs/min (62h full-run). S4 batch loop is sequential; consider ordered parallelization. | perf |

---

## 4. Next steps (in order)

1. **Run the roundtable** — paste `governance/T1.1_ROUNDTABLE_AUDIT_PROMPT_D2349_D2350.md`
   into 2–4 external LLMs (different families). Triage findings ≥ HIGH before re-run.
2. **Fix BUG-106** (checkpoint writer path) and **BUG-107** (single-source leak) if the
   roundtable flags them.
3. **Re-run canary** (`MAXWELL_RUN_ID=canary`) after fixes; re-verify:
   - fb_id stable S2→S4→S6 (no drift)
   - `source_clusters` = real cluster ids
   - `jargon` non-empty in DB, and in **body** (not metadata)
   - `keywords` in `metadata.discovery`, persisted in SQLite `keywords` column
4. **Re-run checks**: `config_audit --strict`, `just integrity`, `just healthcheck`, `just preflight`.
5. **Commit + push** (see §5).

---

## 5. Commit state

Uncommitted working tree (to review before push):

```
 M DECISION-LOG.md
 M MASTER-TASK-REGISTER.md
 M agent/session_seed.yaml
 M config/content_types.yaml
 M config/decisions.yaml
 M config/pipeline_config.yaml
 M governance/aggregated_remaining_tasks.md
 M governance/buglog.md
 M pipeline/e2e_test.py
 M pipeline/ollama_embed.py
 M pipeline/pipeline_paths.py
 M pipeline/stage1_5_embed_cluster.py
 M pipeline/stage4_merge.py
?? governance/T1.1_ROUNDTABLE_AUDIT_PROMPT_D2349_D2350.md
?? governance/SESSION-HANDOFF-2026-08-14.md
```

Note: `agent/session_seed.yaml`, `config/pipeline_config.yaml`, `pipeline/e2e_test.py`,
`pipeline/ollama_embed.py`, `pipeline/pipeline_paths.py`, `pipeline/stage1_5_embed_cluster.py`
were modified in the PRIOR session (D2346/D2347/D2348 — BUG-102/103/105 fixes). Include them
in the same push or commit them separately with a clear message.

Suggested commit message:
```
fix(canary): D2349 taxonomy separation + D2350 S4 identity/provenance integrity
```

---

## 6. Key files to read first on resume

- `config/content_types.yaml` — the corrected ontology (single source of truth).
- `pipeline/stage4_merge.py` — D2350 fixes (grep `D2350`).
- `governance/buglog.md` — BUG-106/107/104 status.
- `governance/T1.1_ROUNDTABLE_AUDIT_PROMPT_D2349_D2350.md` — the roundtable question set.
