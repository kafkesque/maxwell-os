# Roundtable Audit — P0–P2 Surgical Fixes + Golden Depth Expansion (2026-08-20)

> **Purpose:** Independent cross-examination (Claude + ChatGPT) of THIS session's
> surgical changes. Verify the pipeline is intact — no hidden failure, error,
> contamination, leak, blindspot, gap, conflict, bug, drift, risk, or mismatch
> between pipeline scripts, configs, and dependencies.
>
> **Baseline:** T1.1 run-id `t11`; S2 FAILED (183/13,899 > 1%), S4 2,830 FBs,
> S5 2,830 (2,483 PASS / 347 QUARANTINE). **S6 deliberately HELD** (D2420).
> Prior session decisions D2417–D2422 locked. Full test suite green (57 passed).

---

## 1. Changes under review (this session)

### A. P0 — unblock re-extraction (stage2_extract.py)
- **D2421 `--reprocess-gated`**: new `reprocess_gated` param + `.gated_ids`
  sidecar (atomic write alongside `.segids`). On `--reprocess-gated` resume,
  gated cluster IDs are subtracted from `processed_ids` so the 9,842 summary-gated
  clusters re-enter extraction under the content_type-aware gate (D2417).
- `gated_ids.add(cid)` on `_gate`; final atomic write after the loop (incremental
  write fires only every 5 clusters).

### B. P1 — quality fixes
- **P1-2 (BUG-149/C12):** `fb_name_max_words: 8` in `config/pipeline_config.yaml`
  → `FB_NAME_MAX_WORDS` in `pipeline_paths.py` → `normalize_fb_name(name, max_words=FB_NAME_MAX_WORDS)`
  (kills hardcoded `max_words=5`).
- **P1-3 (D2418):** added `elaboration` to SINGLE_SOURCE_SYSTEM + SINGLETON_SYSTEM key lists.
- **P1-4 (BUG-147):** added PT-vs-TI contrastive disambiguation to both prompts
  ("a repeatable human method = process_template; a command/API/algorithm = tool_instruction").
- **P1-6 (BUG-151/D2422):** removed `education` from disciplines (kept in domains);
  `max_disciplines` 72→71; new CI test `tests/test_taxonomy_disjointness.py`
  (domain∩discipline == ∅ modulo "emerging").

### C. Golden depth expansion (T-015 / D2292 / BUG-084)
- Added 4 convergent golden examples: CONV-059 (feedback loop, universal),
  CONV-060 (normal distribution, universal), CONV-061 (Nyquist, specialized),
  CONV-062 (double-entry, specialized). All verbatim-mined from the S1.5 chunk
  checkpoint (2 distinct books each). depth: universal 3→5, specialized 3→5.
- Re-stamped `.golden_meta.json` sha256. `verify_golden_hash` PASS,
  `golden_validate` PASS (84 examples).

### D. Dependencies (C11)
- Added `pypandoc>=1.13` to `requirements.txt` (unguarded top-level import in
  `batch_convert_epubs.py` + `fix_remaining.py`).

### E. NOT changed (verified already-done or deferred)
- **P0-1/D2420 quarantine policy:** already implemented (retrieve.py
  `_status_predicate(include_quarantine)`, stage6b `--all-statuses`, insert_fb
  persists `status` + `needs_human_review`). Verified, not re-changed.
- **P1-1 (176 truncated names), P1-5 (discipline promotion), P2-1/P2-2/P2-3:** deferred.

---

## 2. Evaluation checklist (score each: PASS / FAIL / CONCERN, with evidence)

1. **No hidden failure / error** — do the 5 edited .py files still import + compile?
2. **No contamination** — golden set: are the 4 new examples' evidence_passages
   verbatim substrings of cluster_segments? Are depth labels honest?
3. **No leak** — domain/discipline disjointness (education); quarantine status filter.
4. **No blindspot / gap** — is `--reprocess-gated` resume logic correct (gated IDs
   NOT in processed_ids, re-extracted, no duplicate FBs)?
5. **No conflict** — `fb_name_max_words` in config ↔ `FB_NAME_MAX_WORDS` in paths
   ↔ `normalize_fb_name` call site agree?
6. **No bug** — does `max_disciplines: 71` match the actual discipline count after
   removing education?
7. **No drift** — config keys consumed by code actually exist; no dead config.
8. **No risk** — does `.gated_ids` sidecar write respect crash-safe (tempfile→fsync→os.replace)?
9. **No mismatch/inconsistency** — pipeline scripts ↔ configs ↔ requirements.txt (C11).

## 3. Verification commands (reproduce before judging)

```bash
python3 -m pytest tests/ -q                       # expect 57 passed
python3 pipeline/golden_validate.py               # expect PASS (84 examples)
python3 tools/verify_golden_hash.py               # expect PASS
python3 -m py_compile pipeline/stage2_extract.py pipeline/stage4_merge.py pipeline/pipeline_paths.py
python3 -c "from pipeline.pipeline_paths import FB_NAME_MAX_WORDS; from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES; print(FB_NAME_MAX_WORDS, set(CANONICAL_DOMAINS)&set(CANONICAL_DISCIPLINES))"
```

## 4. Files touched (for direct inspection)

```
config/pipeline_config.yaml        config/taxonomy_v5.yaml
config/golden/stage2_fewshot_convergent.yaml   config/golden/.golden_meta.json
pipeline/pipeline_paths.py         pipeline/stage2_extract.py
pipeline/stage4_merge.py           requirements.txt
tests/test_taxonomy_disjointness.py
```
