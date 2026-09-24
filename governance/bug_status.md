# Bug status index (mechanical, re-derived)

Re-derive with `python3 scripts/bug_status.py` (source: `governance/buglog.md`).

**98 open** / 83 closed of 181 ids.
C15 append-to-handoffs required: **True** (threshold 5).

| id | title (last header) | events |
|---|---|---|
| BUG-253 | reasoning models scored 0 under a small max_tokens budget (harness artifact, NOT model failure) | 1 |
| BUG-254 | oMLX model registry is startup-cached; the fix is POST /admin/api/reload, not a GUI restart | 1 |
| BUG-255 | `POST /admin/api/reload` swaps the single resident model and silently wedges an in-flight benchmark | 1 |
| BUG-257 | the niah top tier exceeded oMLX's context window, making it unmeasurable | 2 |
| BUG-258 | model_eval_report.py counted transport errors as model failures (CORRUPTED THE DELIVERABLE TABLE) | 1 |
| BUG-259 | report tables quoted PRUNED models as if they were candidates | 1 |
| BUG-260 | pipe_s4_classify_gold scored the RAW LLM label against CANONICAL gold (S4 swap gate [[G2]] was mis-measured) | 1 |
| BUG-261 | safe_delete.py copies before deleting, so reclaiming space can FILL THE DISK | 1 |
| BUG-263 | the S2 cross-family relabel produces NOTHING when run with gpt-oss (silent, every record) | 2 |
| BUG-264 | poisoned rows survive every re-run (found by drift_monitor, 2026-09-17) | 1 |
| BUG-265 | toolcalling scored the HARNESS, not the model: native tool_calls ignored | 2 |
| BUG-266 | gpt-oss toolcalling is truncated, not incapable | 1 |
| BUG-270 | OPEN (2026-09-17) — the frontier69 audit artifact disagrees with the runtime KB on 10 of 69 objects, and two concepts exist in BOTH taxonomi | 1 |
| BUG-273 | the domains axis violates its own cardinality contract (2026-09-17) | 1 |
| BUG-274 | the `related_fbs` graph is 56.8% asymmetric (2026-09-17) | 1 |
| BUG-275 | LINK is unenforceable at retrieval, and both facets are unindexed (2026-09-17) | 1 |
| BUG-276 | the C13 safety net is DEAD, and nothing backs up the DB (2026-09-17) | 1 |
| BUG-277 | the content_type axis mixes two vocabularies, and the docs say "7 values" (2026-09-17) | 1 |
| BUG-278 | stage 5 treats "unverifiable" as "untrue", and never persists which one it was (2026-09-19) | 1 |
| BUG-279 | the production classifier is instructed to FREE-GENERATE labels, contradicting its own docstring and D316 (2026-09-19) | 1 |
| BUG-280 | `content_type` (ROLE) is functionally single-valued in production, and `depth` is undefined without it (2026-09-19) | 1 |
| BUG-281 | `noise_drop` fuses two different questions; there is no relevance axis (2026-09-19) | 1 |
| BUG-282 | the schema is 53% dead, and the dead columns are the instrumentation (2026-09-19) | 1 |
| BUG-283 | the ruler scorer accepted only integer indices and would have crashed on the first real sheet (2026-09-19) | 1 |
| BUG-284 | the tooling kept reporting a RULED question as an open defect, and the ruler validator failed a decided sheet (2026-09-19) | 1 |
| BUG-285 | the discipline/domain/depth filters do not constrain the hybrid result set (2026-09-19) | 1 |
| BUG-286 | the write guard destroys the label that D-271a ruled legal (2026-09-19) | 1 |
| BUG-287 | graph expansion re-admits the 3,250 quarantined rows it was meant to hide (2026-09-19) | 1 |
| BUG-288 | the retrieval corpus is 11.1% of the knowledge, and `source_text` is not source (2026-09-19) | 1 |
| BUG-289 | `source_diversity` counts FILENAMES, not works: 29.1% of "convergence" is duplicate ingestion (2026-09-19) | 1 |
| BUG-290 | two illegal values sit inside the retrieval facets (2026-09-19) | 1 |
| BUG-292 | `fbs_fts` has an INSERT trigger only, and nothing checks the index (2026-09-19) | 1 |
| BUG-293 | mega-merges up to 244 sources for a single FB (2026-09-19) | 1 |
| BUG-294 | the ruler's sampling frame is not crossed with `status`, so two estimands are conflated (2026-09-19) | 1 |
| BUG-295 | The ruler compares stored-label ACCURACY to a human-provenance SHARE (MEDIUM, my instrument) | 1 |
| BUG-296 | F-14 pocket retarget is statistically null; the claim is withdrawn (MEDIUM, my instrument) | 1 |
| BUG-297 | "ROLE is decorative" is INVERTED: ROLE is the only serving gate (CRITICAL, my instrument) | 1 |
| BUG-298 | No label carries human provenance; the floor gate is unsatisfiable (MEDIUM) | 1 |
| BUG-299 | The serving gate is a LABEL, not a verification verdict (CRITICAL, 2026-09-19) | 1 |
| BUG-300 | The RRF keyword leg is query-blind, insertion-ordered and weighted equally (HIGH) | 1 |
| BUG-301 | Stage 5 computes a verification tier that Stage 6 has no column for (HIGH) | 1 |
| BUG-302 | Two further status writers remain outside the serving gate (MEDIUM, 2026-09-19) | 1 |
| BUG-303 | Stored extraction_type over-claims causal_mechanism; normative_heuristic 50% mislabeled (HIGH, 2026-09-19) | 1 |
| BUG-304 | Stored content_type over-calls principle; stored discipline 47% wrong with 8 zero-agreement slots (HIGH, 2026-09-20) | 1 |
| BUG-305 | R2 definition-anchored NLI emits ~100% CONTRA on the principle class — the meter is broken (CRITICAL, 2026-09-20) | 1 |
| BUG-306 | Single-coder ceiling κ is contaminated: same-person + ruleset mismatch (HIGH, 2026-09-20) | 3 |
| BUG-312 | NEW: three divergent label snapshots (HIGH, provenance drift, 2026-09-20) | 1 |
| BUG-314 | Frozen ruler csv_sha256 provenance mismatch (MED, 2026-09-21) | 1 |
| BUG-315 | Hardcoded oMLX API key fallback (LOW-MED, C12, 2026-09-21) | 1 |
| BUG-316 | goose main-loop model is the known-bad agentic model (MED, Phase 3 risk, 2026-09-21) | 1 |
| BUG-317 | Bake-off arm layer silently ran the NLI arm on CPU (MED, own wiring, 2026-09-21) | 1 |
| BUG-318 | Bake-off: config JSON braces killed the LLM arm + non-atomic artifact (HIGH, own wiring, 2026-09-21) | 1 |
| BUG-326 | (MED - BLOCKED 2026-09-21): the repair's TARGET NUMBERS do not reproduce on the live DB | 2 |
| BUG-331 | Serving-gate write to the production DB has no R5 review on record (MED, OPEN) | 1 |
| BUG-333 | (MED - OPEN 2026-09-21): the R5 verifier (gemma-4-E4B) can return a schema-shaped rubber stamp | 2 |
| BUG-334 | (MED - OPEN 2026-09-21): a pre-registered n is not automatically the measurable n | 1 |
| BUG-336 | (MED - OPEN 2026-09-21, NEW STANDING RULE): an agent's measurement claim is not evidence | 1 |
| BUG-341 | (HIGH — OPEN 2026-09-21, regression of BUG-311): the LIVE stage5 checkpoint is absent again | 1 |
| BUG-343 | (LOW-MED — OPEN 2026-09-21) — a smoke test asserts a checkpoint that its own fixture cannot produce | 1 |
| BUG-349 | (LOW — OPEN 2026-09-21, found by the session-11 forensic audit F-A) | 1 |
| BUG-351 | (LOW-MED — OPEN 2026-09-21, found by the session-11 audit F-C) | 1 |
| BUG-352 | (MED — OPEN 2026-09-21, found by the session-11 audit F-D) | 1 |
| BUG-354 | (MED — OPEN): the shared resolver rejects the catch-all on BOTH axes | 1 |
| BUG-355 | (MED — OPEN): one surface string, two canonicals — and a dead entry in the domain block of normalization_map | 2 |
| BUG-356 | (LOW — OPEN): the repair queue's own "Next:" line is stale and hides the real next action | 1 |
| BUG-359 | (LOW — process, LOGGED 2026-09-21): a carried "pending fix" note that was never re-verified | 1 |
| BUG-360 | (LOW — process, LOGGED 2026-09-21): a second stale carried claim in one session | 1 |
| BUG-366 | (LOW - process, OPEN): an LLM coder silently under-delivered (79 of 122 rows) | 1 |
| BUG-367 | (MED - OPEN, ruler data quality, found by the F-11 worksheet 2026-09-22): the human FORM column is mostly non-canonical spellings | 1 |
| BUG-376 | (HIGH — OPEN, OWNER GATE = C-3): a completed S5 run's declared input was rewritten after the run, and the image is gone | 2 |
| BUG-377 | (LOW-MED — OPEN 2026-09-23, found by the session-18 audit): pidfiles that outlive their pid, one of them recycled | 1 |
| BUG-378 | (LOW-MED — OPEN 2026-09-23, found by the session-20 audit): repository hygiene drift | 1 |
| BUG-379 |  | 1 |
| BUG-380 |  | 1 |
| BUG-381 |  | 1 |
| BUG-382 |  | 1 |
| BUG-389 | MED - Two verdicts were derived from checks that could not resolve what they were checking (BUG-375 class), and both were WRONG: (a) 'rerank | 1 |
| BUG-390 | (LOW, OPEN) - the R2 meter cannot speak about extraction_type, so owner call 2 was unmeasurable | 3 |
| BUG-391 | (HIGH, OPEN) - the ratified abstention operating point is not reproducible on the ruler in force | 1 |
| BUG-394 | (HIGH, OPEN) - the contextual vector store is 100 percent referentially dead, and the recorded description of BUG-387 was an inference, not  | 2 |
| BUG-395 | (MED, OPEN) - a control artifact that no recipe runs, whose verdict is stale and whose premise no longer matches the configuration | 2 |
| BUG-398 | (MED, OPEN) - a receipt claimed a dated artifact that does not exist | 2 |
| BUG-399 | (MED, OPEN -> detector now wired) - a derived governance count drifted and its detector ran nowhere | 2 |
| BUG-400 | (HIGH, OPEN) - the sovereign corpus and the served store live inside a Dropbox File Provider domain (C3/C22) | 2 |
| BUG-401 | (MED, OPEN) - the disk-chore instruction handed to the owner could not execute, and it aimed at 2 percent of the deficit | 1 |
| BUG-406 | (HIGH, MITIGATED 2026-09-23) - the temp auto-purge rule had no declared-input guard: a sweep moved 35 declared inputs out of temp/ | 1 |
| BUG-411 | (LOW, OPEN) - D2577 cites D2454 as the source of the gemma-depth refutation, and D2454 says something else | 1 |
| BUG-412 | (LOW, OPEN) - the archive index declares an absolute cloud path with no guard that it still resolves | 1 |
| BUG-415 | (MED, OPEN 2026-09-23) - depth is the only production axis with NO anchor row, while D2577 plans a fine-tuned depth model that D274f says re | 1 |
| BUG-416 | (MED, OPEN 2026-09-23) - the depth axis is not a MENU: no config surface declares its 4 classes, so nothing can verify, route or pin them | 1 |
| BUG-417 | (HIGH, OPEN 2026-09-23) - the A2 corrected list's headline candidate is NOT a duplicate: `blobs/` is the target store of 14 live symlinks, a | 1 |
| BUG-420 | (MED, OPEN 2026-09-24) - the anchor family has NO fb_id bridge: its item_id is a sheet-local row label (R001...), so existing human depth wo | 2 |
| BUG-425 | (MED, OPEN 2026-09-24) - the `domains` axis is owned by a DIFFERENT cohort (intersection 2/150) and the family registry never said so | 2 |
| BUG-426 | (HIGH, OPEN - UNRESOLVED) - twice asserted "the 150's domain axis was never asked" while the owner states it WAS done. My search was methodo | 1 |
| BUG-427 | (LOW, OPEN) - the F-11 human instrument carries 4 trailing blank-`item_id` padding rows, so `len(rows)` is 154 while the anchor is 150 | 1 |
| BUG-431 | ANCHOR-4 FORM column was refreshed from ruler_raw, so the sheet's declared 1-4 menu is not what it holds (2026-09-24, MED, OPEN) | 1 |
| BUG-432 | INSTANCE 2 (2026-09-24): the tracked sheet's whole CONTEXT block is also pre-consolidation, so the | 3 |
| BUG-433 | a committed artifact was clobbered by an out-of-band writer 3 hours later, silently (2026-09-24, HIGH, OPEN) | 1 |
