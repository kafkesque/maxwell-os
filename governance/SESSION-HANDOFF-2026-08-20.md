# Session Handoff — 2026-08-20 (T1.1 S2→S5 post-mortem audit + P0-P3 prioritization)

> **State at handoff:** T1.1 run (run-id `t11`) progressed past S2 into S4 and S5.
> S2 finished with 183 failures → runner FAILED → pipeline stopped (per D2331).
> S4 and S5 were then run **manually** (not via runner). S4 = 2,830 FBs. S5 = 2,830 records
> (2,483 PASS / 347 QUARANTINE / 0 FLAG). **S6 has NOT been run — deliberately held.**
>
> **Continue from here in a new chat:** read this file + `DECISION-LOG.md` D2417-D2422 +
> `governance/buglog.md` BUG-145..BUG-151, then pick up §3 P0/P1 list. Git working tree has
> 6 modified governance files uncommitted (see §5).

---

## 0. Decisions LOCKED this turn (2026-08-20 13:14 — D2420/D2421/D2422)

- **D2420 — Quarantine policy DECIDED:** commit-with-status + retrieval-time filter
  (options 1+3 composed). Commit ALL S5 records with explicit `status` + `needs_human_review`;
  retrieval/export defaults to `status='PASS'`, explicit `include_quarantine` opt-in.
  Rejected: exclude-from-commit (silent loss) and separate-table (premature).
- **D2421 — Re-extract APPROVED (`ok apply`):** implement `--reprocess-gated` + `.gated_ids`
  sidecar. **New finding:** gate results are NOT persisted; `processed_ids − checkpoint_FB_ids`
  = 10,834 mixes gated+NULL+dedup. Derive the current gated-ID list once from
  `runner_t11_v3.log`; verify S4 merge/resume over new S2 FBs before re-run.
- **D2422 — Domain/discipline disjointness:** 1 canonical overlap (`education` in both lists)
  + 267 raw-alias overlaps; mapping already kind-aware (D2133/D2394). 38.4% `emerging` is a
  MISS not a leak. Fix = remove `education` from one list + CI disjointness test + expand
  discipline aliases + re-classify-on-domain-only-raw validation.
- **BUG-151 logged** (structural overlap, distinct from BUG-150's emerging miss).

---

## 1. Exact current pipeline state (verified, not assumed)

| Stage | Count | Status |
|---|---|---|
| S2 extract | 2,878 FBs (checkpoint mtime **Aug 19 15:56**) | FAILED (183/13,899 > 1%). **Pre-D2417-fix data.** |
| S4 merge | 2,830 FBs + `process_templates.jsonl`(39) + `tool_instructions.jsonl`(1) | DONE (mtime Aug 20 10:27) |
| S5 verify | 2,830 (2,483 PASS / 347 QUARANTINE) | DONE (mtime Aug 20 10:40) |
| S6 commit | **0 — NOT RUN (held)** | — |

- **D2417 timing fact (critical):** S2 checkpoint mtime `15:56` predates the D2417 commit
  (`17:20`). So the 2,878 S2 FBs were produced by the **old content_type-blind gate** — the
  fix is in the code but has never touched this data.
- **Gated clusters are in `processed_ids`:** `checkpoint.jsonl.segids` = 13,712 processed /
  187 unprocessed. A naive `--resume-from 2` silently skips all **9,842 gated clusters**
  (~5,500–6,000 genuine objects). Needs a `--reprocess-gated` flag to un-mark them.

## 2. Four senior-audit findings (D2418/D2419 — all verified against live artifacts)

1. **PT/TI role-label conflation (BUG-147).** 39/40 non-principle FBs are `process_template`,
   only 1 is `tool_instruction` — but ~25 of the 39 are *code/API/algorithm descriptions*
   (DFS traversal, Point Class Constructor, Matrix Reshaping, Closure State Management).
   Root cause: golden few-shot is **100% `principle`** (82/82 expected FBs) and injected
   **convergent-only** (`few_shot=few_shot_text if few_shot_text and is_conv else None`).
2. **`route="FB"` on all 2,878 records (BUG-148)** — vestigial field; D2128 mapping never exercised.
3. **`elaboration` absent on ALL 229 single-source FBs** — single-source prompt omits field 6.
4. **Name truncation (BUG-149).** `normalize_fb_name(max_words=5)` hardcoded → 176 names
   truncated ("Perceived Complexity and Deviation in Metaphor" → "…and Deviation in").
   `fb_name_max_chars: 200` in config is dead (only `retrieval_evaluator.py` reads it).
   Full names recoverable from S2 checkpoint (verified intact).

## 3. Priority task list (P0-P3)

**P0 (before any S6 commit):**
1. **Hold S6.** `stage6_commit.py` `insert_fb()` has no `status` filter → all 347 QUARANTINE
   commit to SQLite at confidence 0.25 mixed with PASS. Running S6 freezes 183-failed +
   9,842-gated + 347-quarantine + 176-truncated-names + 38%-emerging into the DB with no cheap undo.
2. ~~Decide quarantine policy~~ **DONE → D2420** (commit-with-status + retrieval-time filter).
3. **Implement `--reprocess-gated`** (APPROVED) in `stage2_extract.py` + `.gated_ids` sidecar
   (un-mark gated cluster IDs from `processed_ids`) → re-extract 183 failed + 9,842 gated with
   D2417 code. Do NOT re-run the 2,878 already-extracted FBs, do NOT touch 35,122 singletons.
   **First derive the gated-ID list from `runner_t11_v3.log`; verify S4 merge/resume.**

**P1:**
4. Restore 176 truncated names from S2 checkpoint (script; patch S4+S5 checkpoints; no re-run).
5. Wire `fb_name_max_chars` into `normalize_fb_name` (kill hardcoded `max_words=5`) — C12.
6. Add `elaboration` to single-source + singleton prompts.
7. Add PT-vs-TI contrastive few-shot (positive+negative) to **single-source/singleton** prompts.
8. Promote missing disciplines in `taxonomy_v5.yaml`: `graphic design`, `data visualization`,
   `organizational behavior`, `design thinking`, `product design`, `ux design` (+ their aliases)
   → re-measure `emerging` (target ~15% from 38.4%).

**P2:**
9. Fix S4/S6 non-FB path (make PT/TI NLI-verified + retrievable, or document JSONL-only).
10. Resolve `route` field (remove or compute from content_type).
11. Adopt "3 retrieval buckets, 5 promotable shapes"; PI → `process_template.examples[]`,
    TI → optional `tool_binding`.

**P3:** defer 35,122 singletons (T1.2 priority-aware: tools/procedures first).

## 4. Ontology findings (discipline/domain) — see handoff §4 detail

- 35 canonical domains (all 35 used) / 72 disciplines (62 used, 10 never used).
- `education` is duplicated in BOTH lists (only overlap).
- `synonym_map.yaml` = 25 entries, **all domain aliases, zero discipline aliases** → discipline
  `emerging` 38.4% (graphic design 92×, data visualization 27×, design thinking 18× fall back).
- Domain `emerging` present on 90.2% of FBs.
- **Senior ontological recommendation:** model discipline/domain as ONE concept list with a
  `kind` bitmask (can_be_domain/can_be_discipline) instead of two disjoint lists; move discipline
  clusters (`social sciences`, `arts & culture`, `science & research`, `engineering & infrastructure`)
  out of `domains`; resolve the `education` duplication. Full derivation deferred — fix the
  unambiguous errors + add missing synonyms now.

## 5. Git working tree (uncommitted — do NOT lose on new chat)

```
 M DECISION-LOG.md            (added D2417/D2418/D2419/D2420/D2421/D2422)
 M MASTER-TASK-REGISTER.md    (header synced to D2422)
 M config/decisions.yaml      (added D2420/D2421/D2422; total 410; YAML parses clean)
 M governance/buglog.md       (added BUG-147/148/149/150/151; BUG-146 updated)
 M agent/session_seed.yaml    (header → D2422)
?? governance/SESSION-HANDOFF-2026-08-20.md
```

## 6. Key config/files to re-read on resume

- `pipeline/stage2_extract.py` — gate (line ~1625), `normalize_fb_name` is in stage4, single-source prompt (~564)
- `pipeline/stage4_merge.py` — `normalize_fb_name` (~672), routing (~1128), name normalize call (~1470)
- `pipeline/stage5_verify.py` — confidence cap (~538), NLI factual check (~145-195)
- `pipeline/stage6_commit.py` — `insert_fb` (no status filter ~350), run_stage6 (~532)
- `config/taxonomy_v5.yaml` — 35 domains / 72 disciplines / catch_all=emerging
- `config/synonym_map.yaml` — 25 domain aliases only
- `config/golden/stage2_fewshot_convergent.yaml` — 80 examples, 100% principle, convergent-only
- `config/pipeline_config.yaml` — `stage5.confidence` weights + `quarantine_cap: 0.25`, `stage6.commit_non_fb_types: false`

## 7. Models + env (unchanged)

- Generator Qwen3-Coder-30B (S2), Classifier gpt-oss-20b (S4), NLI DeBERTa-v3-large (S5, thresh 0.10),
  Embeddings bge-m3 (512d). OMLX lazy-load. caffeinate active. S6 held.
