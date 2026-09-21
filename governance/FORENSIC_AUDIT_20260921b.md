# FORENSIC AUDIT — 2026-09-21 (session 6: pre-"next 6 steps" gate)

Scope: repo, ontology, governance, DB, frozen artifacts, services. Read-only except the
buglog/decision/governance records this audit creates. Verdict: **no contamination, no leak, no
silent error in the assistant's own commits — but FOUR integrity defects found, two HIGH.**

## 1. Repo state

| check | result |
|---|---|
| `git status --porcelain` | 73 entries (18 modified production/script + ~23 untracked + governance/config/tests) |
| `git diff --stat HEAD -- pipeline/ tools/ scripts/` | 18 files, 418 ins / 193 del |
| `python3 -m py_compile pipeline/*.py scripts/*.py` | clean (rc=0) |
| `pytest tests/ -q` | **200 passed, 1 failed** (BUG-330, pre-existing) |
| secrets scan (18 changed + new modules) | none; `omlx_admin_session` is a 0-byte junk file |
| absolute paths `/Users/barn` in new modules | none |

## 2. Nature of the uncommitted production work (BUG-328)

The 18 modified + 2 untracked modules are ONE coherent, finished change set, not a half-edit:

- **G19/D274h serving gate** — new `pipeline/serving_gate.py` (120 L, config-driven via
  `config/serving_gate.yaml`): `derive_status()`, `derive_s5_reason()`, `negative_reasons()`,
  `assert_invariant()`. Wired into `stage5_verify.py` (status := f(verification record) + `s5_reason`
  stamp, verifier string from config not literal), `stage6_commit.py` (4 new persisted columns),
  `scripts/apply_dedup_marks.py` (status writes route through the gate).
- **R1/D-279 closed menu + traceability** — new `pipeline/closed_menu.py` (165 L) + frozen
  `config/closed_menu_v5.json` / `.sha256`; `stage4_merge.py` stamps `menu_hash` +
  `{content_type,discipline,extraction_type}_source`; `stage6_commit.py` persists them.
- **D275b/D282/D283 principle-role semantics** — `config/content_types.yaml` (ontology text),
  `pipeline/stage2_extract.py` prompt, `scripts/build_joint_vote_set.py`.
- **D-291/D-293** — `config/pipeline_config.yaml`: `pinned_version: 0.7.0.dev2`, `mtp_enabled: true`.
- retrieve/schemas: `_rank_sql`, hybrid RRF, `validate_discipline_domain` (D2620/D2626), new
  `lint_discipline_domain_vocabulary()` (730) used by the modified tests.

### Evidence that the change set is in force and self-consistent

| invariant | method | result |
|---|---|---|
| gate rule reproduces production data | `scripts/apply_serving_gate.py` dry-run over all 7,995 rows | **0 writes** — PASS 3299 / QUARANTINE 4696 identical |
| `s5_reason` partitions the corpus | SQL group-by | entail 3299 + neutral 3808 + contra 293 + no_evidence 555 + duplicate 17 + evidence_contaminated 8 + mech_fail 1 + vacuous 14 = **7995** |
| row-level rule check | 3 random rows re-derived vs stored | PASS/entail, QUARANTINE/neutral, QUARANTINE/no_evidence all **match** |
| menu hash traceability | `closed_menu.menu_hash()` vs frozen `.sha256` | **73597ee2…** both (R1/D-279 intact) |
| menu vs taxonomy | `menu_summary()` vs `config/taxonomy_v5.yaml` | 62 disciplines / 44 domains = 61 + catch-all `emerging` / 43 + catch-all — intended |
| INSERT arity | parse of `stage6_commit.py` | 75 columns / 75 placeholders — **OK** |
| retrieval against live DB | `search_keyword/fts/vector/hybrid` | all return 20 rows, no missing-column crash |

### New sub-defects (BUG-328 is wider than "18 files")

1. **Fresh checkout does not revert — it crashes.** `pipeline/serving_gate.py` and
   `pipeline/closed_menu.py` are UNTRACKED while `stage5_verify.py:50` /
   `stage4_merge.py:105` import them → one `git checkout pipeline/` yields `ModuleNotFoundError`,
   i.e. total verifier outage, not a silent behaviour change.
2. **The DB is one migration behind the code.** `fbs` has 71 columns; `content_type_source`,
   `discipline_source`, `extraction_type_source`, `menu_hash` are **absent** → the R1/D-279
   provenance stamps have **never been written to any row**; F-44 `min_human_share` still has no
   data to bind to. (The G19 columns *are* present, so that half did run.)
3. **The serving-gate write to production had no R5 review on record** (BUG-331):
   `scripts/apply_serving_gate.py` writes 7,995 statuses; the strongest available review is the
   0-change dry-run + invariant above, which is post-hoc.

## 3. FROZEN ARTIFACT DEFECT (BUG-329, HIGH) — three versions of the ruler

| version | sha256 | evidence |
|---|---|---|
| v0 — freeze-time 13:15, what the ground-truth key hashed | `4d0c856a…` | `anchor1_frozen_20260920.json:csv_sha256` |
| v1 — committed at HEAD (17.09 first pass, `date 17.09.26`) | `2d456720…` | `git show HEAD:…csv` |
| v2 — working tree (rewritten 20:33; R001 `date 20.09.26`) | `38323192…` | file on disk |

**BUG-314 concluded "zero substantive label drift" by comparing v2 against a Sep-20 12:38 backup —
it never compared against HEAD.** The HEAD→working comparison shows substantive drift, not
normalisation:

- **DISC (human discipline labels): 7 rows changed** — R024 strategic thinking→finance,
  R027 leadership→organizational theory, R057 ∅→finance, R111 emerging→typography,
  R126 emerging→cultural design, R139 emerging→psychology, R146 leadership→organizational theory.
- **CT: 41 rows changed** (R004 process instance→quarantine, R005 principle→tool instruction,
  R007 growth edge→noise drop, R049 principle→process template, …).
- **FORM: 62 rows changed** — a mix of cosmetic (`causal mechanism`→`normativ heuristic`
  spelling variants) and substantive (R006 normative_heuristic→descriptive model).
- note_codes rewritten on 149/150 rows (the reviewer's own uncertainty prose was replaced);
  `conf_*` cells filled; +4 trailing/blank lines (150 → 154 rows with one empty `item_id`).

**Impact.** The published baseline (`disc error 0.4741`, n=116) is *derivable* from the frozen key,
which embeds per-row `human`+`stored` labels — so 0.474 is not retroactively wrong. But the sheet
that grounds it is **unversioned and its freeze-time bytes (v0) exist nowhere in the repo**, so
byte-level reproducibility FAILS CLOSED and a re-measure would silently use v1, v2 or v0 depending on
checkout state. Also: `ANCHOR1_BLIND_SHEET_20260920.csv` (R3's ground truth) and
`SINGLE_CODER_CEILING_SHEET_20260920.csv` are untracked — the same class.

**Ruling:** do not commit v2 as "the ruler" without an owner decision. Owner gate added (gate 4).

## 4. R3 held-out run — blocker identified (why step 5 is not runnable as-is)

`scripts/bakeoff_typed_decision.py:_load_rows` requires `key["rows"][*]["stored"]` and the sheet
columns declared in `bakeoff.sheet_columns`. The ANCHOR-1 key is a dict keyed by `fb_id`
(`{row, stratum, max_contra, name, pipeline_discipline, pipeline_domains, pipeline_content_type}`,
**no `rows`, no `stored`**) and the ANCHOR-1 sheet uses its own columns
(`row,fb_id,name,definition,discipline_verdict,domains_verdict,content_type_verdict`). So a
config-only repoint (`bakeoff.sheet`/`bakeoff.key`) is **not sufficient** — the harness needs a
declared, pre-registered adapter for the ANCHOR-1 schema, and for R3 the "stored" side must be the
*arm prediction*, not a pipeline label. Pre-registration (D-311) must be amended to name that
adapter before any run, or the run is a post-hoc measurement.

## 5. Environment

| service | state | consequence |
|---|---|---|
| oMLX `:11435` | up, HTTP 401 unauthenticated (`sk-maxwell-local` required, from `pipeline_paths`) | qwen3coder arm requires the keyed path; my bare curl 401 is expected, not an outage |
| Ollama `:11434` (bge-m3) | **DOWN** (connection refused) | `search_vector` silently falls back to FTS — no error, degraded retrieval (C23 hidden-failure class) |
| `timeout` | absent on macOS | use `gtimeout` or none |

## 6. Not found (explicit negatives)

No human labels written into any prompt or generator input. No blind sheet or key mutated by this
session. No `pipeline/` file touched by this session's commits. No YAML/ontology version conflict
(taxonomy v5.5 across `taxonomy_v5.yaml`, `version.yaml`, `pipeline_config.yaml` ×3). No dead code
introduced; `decisions.yaml` 679 entries, `recompute_decision_summary.py --check` clean. No DB write
performed by this audit (all probes read-only; the gate dry-run reported 0 writes).
