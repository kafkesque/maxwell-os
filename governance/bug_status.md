# Bug status index (mechanical, re-derived)

Re-derive with `python3 scripts/bug_status.py` (source: `governance/buglog.md`).

**272 open** / 585 closed of 857 ids.
C15 append-to-handoffs required: **True** (threshold 5).

**DIVERGENT 0** open id(s) whose OWN last paragraph claims a
closure that no header event records (BUG-481). They stay counted OPEN - the header is the event
(D-2642) - so nothing is closed by a paragraph and nothing is hidden by one either.

| id | title (last header) | events |
|---|---|---|
| BUG-099 | (MED, OPEN, 2026-08-13) — Model registry (`config/engine.yaml`) drift: gpt-oss/Phi misnamed 'verifier' (rename deferred) | 1 |
| BUG-151 | (MED, OPEN, 2026-08-20) — taxonomy structural overlap (education dual-listed + 267 raw aliases) | 1 |
| BUG-159 | (CRITICAL, OPEN, 2026-08-21) — prompt-injection contamination (cluster_11649, 0.007%) | 1 |
| BUG-160 | (MED, OPEN, 2026-08-21) — evidence-passage topical relevance not verified | 1 |
| BUG-169 | (MED, OPEN, 2026-08-24) — TI parameters empty on 31/143 single-source + 100/307 singleton | 1 |
| BUG-182 | (MED, OPEN, 2026-08-27) — 48 singleton empty-shells re-return empty after S2 rerun | 1 |
| BUG-222 | (CRITICAL, OPEN, 2026-09-04) — goose runtime drift: active_provider=custom_deepseek (C1/C3 violation) | 1 |
| BUG-223 | (MED, OPEN, 2026-09-05) — '[]' literal-array hygiene (54 emerging FBs) | 1 |
| BUG-224 | (HIGH, OPEN, 2026-09-05) — OMLX server wedges under sustained load (MITIGATED D2581) | 1 |
| BUG-228 | (LOW, OPEN, 2026-09-08) — Dead/aspirational schema fields — 0 code references | 1 |
| BUG-237 | (MED, OPEN, 2026-09-10) — production fbs.depth unverified silver (PARTIALLY ADDRESSED D2610/D2611) | 1 |
| BUG-238 | (MED, OPEN, 2026-09-10) — content_type is a VACUOUS axis (99.6% principle unverified) | 1 |
| BUG-242 | (MED, OPEN, 2026-09-11) — frontier69_v2 data-quality defects — override figures still to recompute | 1 |
| BUG-253 | (MED) — reasoning models scored 0 under a small max_tokens budget (harness artifact, NOT model failure) | 1 |
| BUG-255 | (MED) — `POST /admin/api/reload` swaps the single resident model and silently wedges an in-flight benchmark | 1 |
| BUG-257 | (MED) — the niah top tier exceeded oMLX's context window, making it unmeasurable | 2 |
| BUG-258 | (HIGH) — model_eval_report.py counted transport errors as model failures (CORRUPTED THE DELIVERABLE TABLE) | 1 |
| BUG-259 | (MED) — report tables quoted PRUNED models as if they were candidates | 1 |
| BUG-260 | (HIGH) — pipe_s4_classify_gold scored the RAW LLM label against CANONICAL gold (S4 swap gate [[G2]] was mis-measured) | 1 |
| BUG-261 | (CRITICAL) — safe_delete.py copies before deleting, so reclaiming space can FILL THE DISK | 1 |
| BUG-263 | (CRITICAL) — the S2 cross-family relabel produces NOTHING when run with gpt-oss (silent, every record) | 3 |
| BUG-264 | (CRITICAL) — poisoned rows survive every re-run (found by drift_monitor, 2026-09-17) | 1 |
| BUG-265 | (HIGH) — toolcalling scored the HARNESS, not the model: native tool_calls ignored | 2 |
| BUG-266 | (HIGH) — gpt-oss toolcalling is truncated, not incapable | 1 |
| BUG-267 | (MED, OPEN, 2026-09-17) — min_human_share floor is a substring classifier (F-16) | 1 |
| BUG-270 | (HIGH) — OPEN (2026-09-17) — the frontier69 audit artifact disagrees with the runtime KB on 10 of 69 objects, and two concepts exist in | 1 |
| BUG-273 | (MED) — the domains axis violates its own cardinality contract (2026-09-17) | 1 |
| BUG-275 | (MED) — LINK is unenforceable at retrieval, and both facets are unindexed (2026-09-17) | 1 |
| BUG-277 | (LOW) — the content_type axis mixes two vocabularies, and the docs say "7 values" (2026-09-17) | 1 |
| BUG-278 | (HIGH) — stage 5 treats "unverifiable" as "untrue", and never persists which one it was (2026-09-19) | 1 |
| BUG-279 | (HIGH) — the production classifier is instructed to FREE-GENERATE labels, contradicting its own docstring and D316 (2026-09-19) | 1 |
| BUG-280 | (HIGH) — `content_type` (ROLE) is functionally single-valued in production, and `depth` is undefined without it (2026-09-19) | 1 |
| BUG-281 | (HIGH) — `noise_drop` fuses two different questions; there is no relevance axis (2026-09-19) | 1 |
| BUG-282 | (HIGH) — the schema is 53% dead, and the dead columns are the instrumentation (2026-09-19) | 1 |
| BUG-287 | (HIGH) — graph expansion re-admits the 3,250 quarantined rows it was meant to hide (2026-09-19) | 1 |
| BUG-288 | (HIGH) — the retrieval corpus is 11.1% of the knowledge, and `source_text` is not source (2026-09-19) | 1 |
| BUG-289 | (MED) — `source_diversity` counts FILENAMES, not works: 29.1% of "convergence" is duplicate ingestion (2026-09-19) | 1 |
| BUG-290 | (MED) — two illegal values sit inside the retrieval facets (2026-09-19) | 1 |
| BUG-292 | (LOW) — `fbs_fts` has an INSERT trigger only, and nothing checks the index (2026-09-19) | 1 |
| BUG-293 | (LOW) — mega-merges up to 244 sources for a single FB (2026-09-19) | 1 |
| BUG-294 | (MED) — the ruler's sampling frame is not crossed with `status`, so two estimands are conflated (2026-09-19) | 1 |
| BUG-295 | The ruler compares stored-label ACCURACY to a human-provenance SHARE (HIGH, gemma advisory overrides MEDIUM) | 1 |
| BUG-296 | F-14 pocket retarget is statistically null; the claim is withdrawn (MED, my instrument) | 1 |
| BUG-298 | No label carries human provenance; the floor gate is unsatisfiable (MED) | 1 |
| BUG-303 | Stored extraction_type over-claims causal_mechanism; normative_heuristic 50% mislabeled (HIGH, 2026-09-19) | 1 |
| BUG-304 | Stored content_type over-calls principle; stored discipline 47% wrong with 8 zero-agreement slots (HIGH, 2026-09-20) | 1 |
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
| BUG-377 | (LOW-MED — OPEN 2026-09-23, found by the session-18 audit): pidfiles that outlive their pid, one of them recycled | 1 |
| BUG-378 | (LOW-MED — OPEN 2026-09-23, found by the session-20 audit): repository hygiene drift | 1 |
| BUG-381 | (HIGH) | 1 |
| BUG-382 | (MED) | 1 |
| BUG-389 | MED - Two verdicts were derived from checks that could not resolve what they were checking (BUG-375 class), and both were WRONG: (a) | 1 |
| BUG-391 | (HIGH, OPEN) - the ratified abstention operating point is not reproducible on the ruler in force | 1 |
| BUG-395 | (MED, OPEN) - a control artifact that no recipe runs, whose verdict is stale and whose premise no longer matches the configuration | 2 |
| BUG-398 | (MED, OPEN) - a receipt claimed a dated artifact that does not exist | 2 |
| BUG-399 | (MED, OPEN -> detector now wired) - a derived governance count drifted and its detector ran nowhere | 2 |
| BUG-400 | (HIGH, OPEN) - the sovereign corpus and the served store live inside a Dropbox File Provider domain (C3/C22) | 2 |
| BUG-401 | (MED, OPEN) - the disk-chore instruction handed to the owner could not execute, and it aimed at 2 percent of the deficit | 1 |
| BUG-406 | (HIGH, MITIGATED 2026-09-23) - the temp auto-purge rule had no declared-input guard: a sweep moved 35 declared inputs out of temp/ | 1 |
| BUG-411 | (LOW, OPEN) - D2577 cites D2454 as the source of the gemma-depth refutation, and D2454 says something else | 1 |
| BUG-412 | (LOW, OPEN) - the archive index declares an absolute cloud path with no guard that it still resolves | 1 |
| BUG-415 | (MED, OPEN 2026-09-23) - depth is the only production axis with NO anchor row, while D2577 plans a fine-tuned depth model that D274f says | 1 |
| BUG-416 | (MED, OPEN 2026-09-23) - the depth axis is not a MENU: no config surface declares its 4 classes, so nothing can verify, route or pin them | 1 |
| BUG-417 | (HIGH, OPEN 2026-09-23) - the A2 corrected list's headline candidate is NOT a duplicate: `blobs/` is the target store of 14 live symlinks, | 1 |
| BUG-419 | (LOW, OPEN 2026-09-23) - bug_status.json is schema-ASYMMETRIC: open is a list of objects, closed is a list of plain id strings | 1 |
| BUG-420 | (MED, OPEN 2026-09-24) - the anchor family has NO fb_id bridge: its item_id is a sheet-local row label (R001...), so existing human depth | 2 |
| BUG-425 | (MED, OPEN 2026-09-24) - the `domains` axis is owned by a DIFFERENT cohort (intersection 2/150) and the family registry never said so | 2 |
| BUG-426 | (HIGH, OPEN - UNRESOLVED) - twice asserted "the 150's domain axis was never asked" while the owner states it WAS done. My search was | 1 |
| BUG-427 | (LOW, OPEN) - the F-11 human instrument carries 4 trailing blank-`item_id` padding rows, so `len(rows)` is 154 while the anchor is 150 | 1 |
| BUG-431 | ANCHOR-4 FORM column was refreshed from ruler_raw, so the sheet's declared 1-4 menu is not what it holds (2026-09-24, MED, OPEN) | 1 |
| BUG-432 | (MED) - INSTANCE 2 (2026-09-24): the tracked sheet's whole CONTEXT block is also pre-consolidation, so the | 3 |
| BUG-433 | a committed artifact was clobbered by an out-of-band writer 3 hours later, silently (2026-09-24, HIGH, OPEN) | 1 |
| BUG-448 | (MED) - OPEN - the depth and domain axes had no consistency contract (existence gap, not a regression) | 1 |
| BUG-450 | (HIGH) - OPEN - the FORM (extraction_type) axis carries 150 labels with VOID rater provenance | 2 |
| BUG-451 | (MED) - OPEN - MEASURED: FORM (1-4) has ZERO discriminative power for depth-class-1 admission | 1 |
| BUG-452 | (LOW) - OPEN - the FORM panel is raw-agreement only, and it is 2 of 4 models | 1 |
| BUG-454 | (LOW) - OPEN - the token `flags` names two different things; the flag-consumer rail cannot see the new consumer | 1 |
| BUG-455 | (CRITICAL) - OPEN - the archive index has NO content identity: same-size corruption and duplication are both invisible | 1 |
| BUG-456 | (MED) - OPEN - the S4 "rolling" backup held 6 byte-identical slots: one recovery point, six names | 1 |
| BUG-462 | (CRITICAL) - OPEN - the declared agreement floor (D-373) has no consumer | 2 |
| BUG-464 | (CRITICAL) - OPEN - a bookkeeping column that reads as 192 open items when 4 cells are open | 1 |
| BUG-465 | (CRITICAL) - OPEN - a blank cell carries four meanings and the contract can only see one | 2 |
| BUG-466 | (HIGH) - OPEN - 148 adjudicated rows against a declared 150-row cohort, with no exclusion rule | 1 |
| BUG-468 | (CRITICAL) - OPEN - a digest recorded in prose for a live file that has since been written | 1 |
| BUG-475 | (CRITICAL) - OPEN (pipeline-side, needs owner ack) - a path constant bound at import cannot be isolated | 1 |
| BUG-477 | (LOW) - OPEN - the FORM coder columns are `label (margin)` strings, and `owner_form` is declared but empty | 1 |
| BUG-478 | OPEN (severity HIGH) - the only declared panel ingester REWRITES the ANCHOR-4 workbook and blanks the owner's adjudicated cells | 1 |
| BUG-480 | OPEN (severity MED) - the CLAIM-SHAPE gate is a perfect screen and a weak classifier: 10/11, not shippable | 1 |
| BUG-482 | OPEN (severity MED) - three checks built this week are invoked by nothing, so they cannot report | 1 |
| BUG-484 | (CRITICAL) - OPEN | 1 |
| BUG-487 | (MED) - OPEN (owner gate) | 3 |
| BUG-500 | (CRITICAL, CONFIRMED, systemic) — a Dropbox conflicted copy is silent drift, not a merge conflict | 1 |
| BUG-511 | (CRITICAL, OPEN in two orphan readers) — a reader that GUESSES an encoding does not crash, it silently changes text | 1 |
| BUG-514 | (CRITICAL, OPEN) — three readers still decide an encoding by GUESS | 1 |
| BUG-520 | (MED, DETECTOR LANDED 2026-09-26) - a silent repair is not a protection from crashing; it is a protection from NOTICING | 2 |
| BUG-521 | (CRITICAL, MEASURED 2026-09-26) - an encoding the ENVIRONMENT decides is UNDECLARED: 393 sites in 166 modules, and no rail could see them | 1 |
| BUG-523 | (CRITICAL, OPEN - found 2026-09-26 only because a human asked "what exactly must I ratify in D-2650?") - the reserved-fixture rule covered | 1 |
| BUG-524 | (CRITICAL, OPEN 2026-09-26) - the STORES and COLUMNS axes had NO machine: two rails land, and their own controls found 3 defects in the | 1 |
| BUG-525 | (CRITICAL, OPEN 2026-09-26) - the AMBIGUOUS-DECLARATION class: a key declared twice in one mapping is SILENTLY last-wins, and no rail could | 1 |
| BUG-526 | (CRITICAL, OPEN 2026-09-26) - the pin invariant had a SCAN and no WRITE moment: a pinned artifact could be edited and committed with | 1 |
| BUG-527 | (CRITICAL, OPEN 2026-09-26) - the staged-reading rails audit whichever index the ENVIRONMENT names, not the one being committed | 1 |
| BUG-529 | (HIGH, OPEN 2026-09-26) - .pre-commit-config.yaml declares a C11/C12 gate that NOTHING invokes, and the hook slot has exactly ONE occupant | 1 |
| BUG-532 | (MED, OPEN 2026-09-26) - one lock, two homes: the session plan RESTATED the owner-instrument lock that a rail already checks | 1 |
| BUG-545 | (MED - OPEN, MEASURED 2026-09-26): 17 of the 60 rails the health ladder invokes are NOT tracked by git - the control plane has no history | 1 |
| BUG-559 | (CRITICAL, STRUCTURAL - D-2666, OPEN 2026-09-26): a receipt can be cut over bytes joined to NO revision, so `mutability: human_authored` | 1 |
| BUG-593 | (OPEN, MED - the MUTATION GATE's fixture carries ONE commit, so a rule whose oracle joins GIT HISTORY cannot satisfy limb (iv) - FILED | 1 |
| BUG-594 | (MED, OPEN, 2026-09-29, D-2706) — chunker structural heading-splitting is DEAD (clean_markdown strips `#` before split_on_headings) | 1 |
| BUG-595 | (HIGH, OPEN, 2026-09-29, D-2706) — clean_markdown() never applies _CLEAN_SUBS (D2471); Pandoc/calibre residue in 41.4% of S1 bodies | 1 |
| BUG-604 | (HIGH, OPEN, 2026-09-30) — stage0_5 metadata extractor mis-splits "liber3.md" filenames, leaking title words into the author field (split | 1 |
| BUG-629 | (HIGH, OPEN, 2026-10-04) — S4 discipline=emerging regression 26.9% on the v4 re-chunk corpus (above the 15% threshold); 1,253 DEMOTIONS | 1 |
| BUG-630 | (MED, OPEN, 2026-10-04) — the cross-axis guard is TOO BLUNT: a raw label that is canonical on the OPPOSITE axis is forced to 'emerging' | 1 |
| BUG-632 | (CRITICAL, OPEN, 2026-10-04) — the D2496 "authoritative expected FB count" gate CANNOT DISTINGUISH a DECLARED failure from a SILENT drop, | 1 |
| BUG-635 | (HIGH, OPEN, 2026-10-04) — merged-call sparse classification is quarantined under D2371 as "empty application", masking the true failure | 1 |
| BUG-636 | (CRITICAL, OPEN, 2026-10-04) — S4 exit-2 clears the resume sidecars before the failure check, so the documented "re-run to retry failed | 1 |
| BUG-638 | (CRITICAL, OPEN, 2026-10-05) — governance/METRICS.jsonl append-only journal truncated 817→70 lines (747 samples lost); root cause | 1 |
| BUG-640 | (MED, IN PROGRESS, 2026-10-05) — D-2815 B&M discipline slot "entrepreneurship" string-collides with existing DOMAIN; owner ruling D-2829 | 1 |
| BUG-642 | (CRITICAL, OPEN, 2026-10-05) — alias_map.yaml retirement (D-2814) cascade: 14 consumers (pipeline/schemas.py + 13 scripts) | 1 |
| BUG-643 | (MED, IN PROGRESS, 2026-10-05) — dual abstention token 'none' (_ABSTENTION_VALUE) vs 'emerging' (catch_all); owner ruling D-2830 | 1 |
| BUG-648 | (MED, OPEN, 2026-10-05) — definition-anchored menu ~5k tokens/call bloat (prefix-cache amortization) | 1 |
| BUG-650 | (CRITICAL, PARTIAL, 2026-10-05) — full-204 A/B (D-2767) has no fail-closed guard against a frozen-invalid anchor; a pre-D-2820 kappa is | 1 |
| BUG-651 | (CRITICAL, PARTIAL, 2026-10-05) — S5 majority NLI aggregation hides supported claims + passes contradictory claims (D-2822 Gate A(d)) | 1 |
| BUG-677 | (CRITICAL, OPEN, 2026-10-08) — two owner-facing truths for the SAME 60 items (ANCHOR-2 sheet vs frozen ruler) | 1 |
| BUG-680 | (MED, OPEN, 2026-10-08) — the upstream anchor faces still encode discipline abstention as the out-of-menu token 'emerging' (BUG-676 | 2 |
| BUG-698 | (HIGH, OPEN, 2026-10-10) — v8→v9 discipline-anchor off-menu rows are 22 in THREE categories, not the "7 delta rows" assumed in GATE-2; | 1 |
| BUG-700 | (HIGH - OPEN 2026-10-10): cross-generation entity identity gap (root cause of the dual-generation store) | 1 |
| BUG-701 | (HIGH - OPEN 2026-10-10): the anchor-store bridge binds 193/208 rows to the NO-LONGER-SERVED generation | 1 |
| BUG-702 | (MED - OPEN 2026-10-10): S5 `practicality` is STORED but was not a first-class retrieval facet | 1 |
| BUG-703 | (MED - OPEN 2026-10-10): 190/6,591 v9 rows have EMPTY `discipline_raw` while `discipline` is populated | 1 |
| BUG-704 | (MED - OPEN 2026-10-10): S4 taxonomy scatter — engineering/agentic principles misclassified into Human&Design / Method&Business / emerging | 1 |
| BUG-705 | (HIGH - OPEN 2026-10-10): the S5 recall path is still-pending code — and 2,258 neutral rows are recoverable | 1 |
| BUG-706 | (MED - OPEN 2026-10-10): the macro re-classify gate needs a v9-stamped referee | 1 |
| BUG-711 | (HIGH — OPEN): 173 canonical rows still carry a DISPLACED canonical domain label in the STORE | 1 |
| BUG-719 | (MED - OPEN 2026-10-12): the non-principle sidecars are not content-type pure, and the "81 tool_instruction remaining" figure was an | 1 |
| BUG-720 | (LOW - OPEN 2026-10-12): the S4 sidecar reconciliation tolerates a magic 7 instead of reconciling exactly | 1 |
| BUG-721 | (HIGH - OPEN 2026-10-12): a DELEGATE returned a FABRICATED code-review verdict without reading the code (false assurance) | 1 |
| BUG-723 | (MED - OPEN 2026-10-12): t11-unique corpus coverage debt after the superseded-run purge | 1 |
| BUG-728 | (LOW - OPEN 2026-10-12) — `source_authors` (FILE layer) repeats one source: 31 rows literally, 90 by carrier key | 1 |
| BUG-731 | (MED - OPEN 2026-10-12) — the undeclared-default census is 12 over its ceiling (PRE-EXISTING), and the rail's receiver list cannot see | 2 |
| BUG-736 | (MED - OPEN 2026-10-12) — the verifier instruments, measured: the R5 reviewer is uninformative ~40-50% of the time and the S5 NLI's edge is | 5 |
| BUG-737 | (MED - OPEN 2026-10-12) — the store's ABSENT SHAPE is `''` on 20 of 78 columns while the code declares `None` | 5 |
| BUG-738 | (MED - OPEN 2026-10-12) - R5 code review had NO deterministic layer: 7 of 43 verdicts were not decisions, and the deep auditor was the | 2 |
| BUG-743 | (LOW - OPEN 2026-10-12) - a DELEGATED reviewer's verdict is not re-readable after the fact, so a receipt that cites it must CAPTURE THE | 1 |
| BUG-748 | (MED - OPEN 2026-10-13) - D-2928's definition re-scope left 177 canonical rows ON the moved boundary, and the audit D-2905's precedent | 5 |
| BUG-749 | (HIGH - OPEN 2026-10-13) - 1,072 in-subject rows (16.3%) carry a discipline the live production mapper does NOT reproduce from their own | 5 |
| BUG-750 | (LOW - OPEN 2026-10-13) - a GENERATED artifact can go stale behind its own generator and no rail sees it: the canonical-labels reference | 1 |
| BUG-757 | (MED - OPEN, found 2026-10-13 while auditing the user-facing faces) - 125 open bugs carry NO severity token, so the open register cannot be | 1 |
| BUG-767 | (HIGH - OPEN 2026-10-13) - the RETIRED trust metric still leaves the machine, published to agents and written into two exports | 1 |
| BUG-768 | (HIGH - OPEN 2026-10-13) - BORP is satisfied by a MINORITY of the served corpus: the deleted per-row check left the SINGLETON route | 1 |
| BUG-771 | (MED - OPEN 2026-10-13) - the review sheet compared every candidate against a golden state that no longer existed | 1 |
| BUG-772 | (HIGH - OPEN 2026-10-13) - corroboration is frozen by ONE run's clustering, so a later independent source can never raise a row's tier | 1 |
| BUG-773 | (HIGH - OPEN 2026-10-13) - the declared rule "a commit may never rewrite an existing row's body" is contradicted by the live upsert | 3 |
| BUG-774 | (MED - OPEN 2026-10-13, PREVENTIVE) - the planned non-book intake has no identity, and the branch it would fall to is the one a closed | 1 |
| BUG-775 | (MED - OPEN 2026-10-14) - ONE BIT IN THREE COLUMNS: the corroboration the store advertises is a derivation nothing declares | 1 |
| BUG-780 | (HIGH - OPEN 2026-10-14) - WORK IDENTITY COLLAPSE: 84 work-pairs are ONE TEXT under TWO NAMES, so 530 "corroborated" rows (369 of them | 1 |
| BUG-781 | (HIGH - OPEN 2026-10-14) - THE IDENTITY MACHINERY HAD NO ENFORCEMENT POINT: the owner ledger sat 59 pairs PENDING for a fortnight while the | 1 |
| BUG-789 | (MED — OPEN) — the local model server's app config carries a Hugging Face token in plaintext | 1 |
| BUG-790 | (LOW — OPEN) — the ingest door's refusal names the WRONG TASK | 1 |
| BUG-793 | (MED — OPEN 2026-10-14) — Qwen3.8-27B prefills at 39 tok/s, four times worse than its parameter ratio predicts | 1 |
| BUG-795 | (LOW — OPEN 2026-10-14) — one ledger row carries a NULL model and 156,098,139 input tokens | 1 |
| BUG-796 | (MED — OPEN 2026-10-14) — a decision written outside the receipting writer leaves the attribution control red | 1 |
| BUG-797 | (MED — OPEN 2026-10-15) — the `llmfit` preflight cell is a control that CANNOT FAIL | 1 |
| BUG-800 | (LOW — OPEN 2026-10-15) — the approved corpus-name rename is a CASCADE until it rides a re-ingest | 1 |
| BUG-802 | (MED — OPEN 2026-10-15) — the $0 local engine does not survive a reboot, and nothing starts it | 1 |
| BUG-803 | (MED — OPEN 2026-10-15) — a prefill reading without the POOL STATE it was taken at is not comparable either | 1 |
| BUG-805 | (MED — OPEN 2026-10-15) — decode is a function of CONTEXT LENGTH: the decode axis was measured on tiny prompts | 1 |
| BUG-806 | (LOW - OPEN 2026-10-15) - my bench wrote its receipt only on the SUCCESS path, so the two REFUSALS were not persisted | 1 |
| BUG-810 | (MED - OPEN 2026-10-15) - a YAML insert that re-parents a mapping passes every parse check and is caught only by the consumer | 1 |
| BUG-811 | (HIGH - OPEN 2026-10-15) - a new instrument told three lies before its own selftest was written | 1 |
| BUG-812 | (MED - OPEN 2026-10-15) - a comment inserted into a plist silently broke the XML, and launchd reported only "Input/output error" | 1 |
| BUG-813 | (MED - OPEN 2026-10-15) - the cache was enabled before its baseline was taken | 1 |
| BUG-815 | (HIGH - OPEN 2026-10-15) - `goose run` was not bound to the local engine, so a headless agent run went elsewhere | 1 |
| BUG-817 | (HIGH - OPEN 2026-10-15) - a failed edit was read as a success, so two declared config blocks never existed while three instruments | 2 |
| BUG-818 | (MED - OPEN 2026-10-15) - the retire tool's dry run promises a park and its code performs a delete; and safe_delete would copy model | 1 |
| BUG-819 | (MED - OPEN 2026-10-15) - a face that says "generated from the live oMLX registry" was hand-copied and had drifted | 1 |
| BUG-820 | (MED - OPEN 2026-10-15) - a guard artifact rewritten by a generic YAML dumper loses the comments that ARE the guard | 1 |
| BUG-821 | (MED - OPEN 2026-10-15) - the census could not count 16 records because the mint path was bypassed, so four faces quoted a stale total for | 1 |
| BUG-829 | (MED - OPEN 2026-10-15) - the review surface's own agent panel defaults to a CLOUD provider | 1 |
| BUG-832 | (MED - OPEN 2026-10-15) — the session brain is the provider a CLOSED bug banned, and nothing in the repo can see it change | 3 |
| BUG-834 | (MED - OPEN 2026-10-15) — a delegate's handle did not resolve, so the deliverable of an in-process delegation was unretrievable in the same | 1 |
| BUG-836 | (MED - OPEN 2026-10-15) - the R5 cross-family review route produced NO usable review from either local verifier, and one of the two | 1 |
| BUG-846 | (LOW - OPEN 2026-10-16) - governance/buglog.md is a REGISTER while the intake assessment is only a DOCUMENT: a rejected research finding | 1 |
| BUG-857 | (MED — OPEN 2026-10-16) — governance/buglog.md could be APPENDED TO and never QUERIED: no artifact computed which findings share a shape, | 1 |
| BUG-858 | (MED — OPEN 2026-10-16) — governance/buglog.md carries NO entry for BUG-492, the most-cited rule in this repository: 128 files cite it (53 | 1 |
| BUG-862 | (MED — OPEN 2026-10-16) — scripts/census_source_names.py now measures TWO MATERIALISATIONS of one work and config/ingest_identity_gate.yaml | 1 |
| BUG-867 | (LOW — OPEN 2026-10-16) — scripts/census_source_names.py never compares a file's own CONTAINER to the KIND folder its declared axis orders | 1 |
| BUG-869 | (MED — OPEN 2026-10-16) — pipeline/subagent_fanout.py delivered an `async: true` delegate as a FOREGROUND run that BLOCKED its parent, and | 1 |
| BUG-875 | (HIGH, OPEN) — A FIRST-PARTY IMPORT NAME RESOLVES OUTSIDE THE TREE, so the delegated-run journal and 16 import sites read ANOTHER PROJECT'S | 1 |
| BUG-876 | (MED, OPEN 2026-10-17) — THE ATTRIBUTION CONTROL CANNOT GO GREEN ON THE REGISTRY IT MEASURES | 1 |
| BUG-877 | (MED, OPEN 2026-10-17) — A GOVERNED WRITE TO THE HARNESS HOME DOES NOT SURVIVE: scripts/check_harness_homes.py reads CONFLICT again, and no | 1 |
| BUG-879 | (LOW, OPEN 2026-10-17) — THE BIRTH RECORD NAMES A STDIO MEMBER BY ITS COMMAND, SO `scripts/goose_profile.py --born` CANNOT DISTINGUISH TWO | 1 |
| BUG-889 | (MED, OPEN 2026-10-17) — `scripts/normalise_corpus_names.py --census` CANNOT SEE THE 6 NFD NAMES IT EXISTS TO CURE: ITS DEFECT CLASSES ARE | 1 |
| BUG-890 | (MED, ADDRESSED 2026-10-17) — `AGENTS.md#delegate_rules` STILL CARRIES DELEGATE-002's "SINGLE-SHOT ONLY / 6.8→0.4 tok/s COLLAPSE", A CLAIM | 1 |
| BUG-891 | (MED, OPEN 2026-10-17) — `config/agent_surface.yaml`'s SWAP CHECKLIST NAMES A RENDER SOURCE THAT DOES NOT EXIST, SO EVERY CORRECTION TO | 1 |
| BUG-899 | (MED — OPEN 2026-10-17) — `pipeline/stage0_convert.py` — `--book` CAN SILENTLY SKIP A WORK WHOSE NAME IT HAS SEEN BEFORE | 1 |
| BUG-900 | (MED — OPEN 2026-10-17) — A BOOK CAN PASS EVERY CONTAINER PROBE IN `pipeline/container_integrity.py` AND STILL BE UNCONVERTIBLE, AND THIS | 2 |
| BUG-901 | (MED — OPEN 2026-10-17) — `pipeline/ingest_gate.py` — THE INGEST DOOR COUNTS A WORK'S OWN CONVERSION AS A DUPLICATE OF ITSELF | 2 |
| BUG-902 | (MED — OPEN 2026-10-17) — THE ROUTE-GRAPH DEBT WAS OVER ITS SHRINK-ONLY CEILING IN `config/capability_registry.yaml` BEFORE TODAY'S FINDINGS | 1 |
| BUG-905 | (MED — OPEN 2026-10-17) — THE KINDLE ENGINE EXISTS AND STILL CANNOT BE USED: config/ingest_identity_gate.yaml DECLARES A KIND FOLDER THAT | 1 |
| BUG-906 | (LOW — OPEN 2026-10-17) — A READ-ONLY DELEGATE RUN CANNOT BE CLOSED AS `done`: scripts/delegate_journal.py REFUSES `--artifact none` | 1 |
| BUG-909 | (HIGH — OPEN 2026-10-17) — THE ONLY SHADOW RUNG THAT WORKS IS A SINGLE POINT OF FAILURE: EVERY LibGen FRONT ANSWERS `500 | 2 |
| BUG-911 | (MED — OPEN 2026-10-17) — THE ONLY ROUTE INTO ANNA'S ARCHIVE IS A HEADED BROWSER WINDOW | 3 |
| BUG-912 | (LOW — OPEN 2026-10-17) — An `open_access` ROUTE CAN DELIVER AN HTML LANDING PAGE FOR A DOI | 1 |
| BUG-914 | (MED — OPEN 2026-10-17) — THE LANE RECORDS DELIVERY AND NEVER CUSTODY, SO IT PAID THE SHADOW PRICE FOR A WORK THE CORPUS ALREADY HELD | 1 |
| BUG-915 | (MED — OPEN 2026-10-17) — THE DOCLING BUDGET'S DECLARED BASIS IS **BYTES**, AND BYTES DO NOT PREDICT CONVERSION COST (MEASURED r = −0.131) | 1 |
| BUG-919 | (MED, OPEN 2026-10-18) — A SECOND ARTEFACT DEFECT: WHITESPACE PADDING, AND ARTEFACTS NO ENGINE PRODUCED | 1 |
| BUG-921 | (MED, OPEN 2026-10-18) — 19 DUPLICATE STEMS (38 FILES) IN THE CORPUS MD FROM FILENAME PUNCTUATION DRIFT; NO PER-WORK DEDUP KEY | 3 |
| BUG-948 | (MED, OPEN 2026-10-19) — owner_marks.rule_digest is a whole-file sha256; any append to the rule file stale-ifies the pair object | 1 |
| BUG-949 | (HIGH, OPEN 2026-10-20) — pipeline cloud spend is UNMETERED while the routing table still declares cloud routes | 1 |
| BUG-950 | (HIGH, OPEN 2026-10-20) — THE HARNESS ABORTS A LOCAL-MODEL REQUEST AT ~120 s AND REPORTS IT AS "Failed to read response body: error | 2 |
| BUG-951 | (HIGH, OPEN 2026-10-20) — gpt-oss-20b-MXFP4-Q8 (`GOOSE_PLANNER_MODEL`) EMITS A MALFORMED HARMONY HEADER, SO TOOL NAMES ARRIVE AS | 5 |
| BUG-964 | (LOW, OPEN 2026-10-22) — gpt-oss-20b same-row verdict flip: NONE(0.1) -> MATCH(0.85) on R111 (determinism unverified) | 2 |
| BUG-967 | (LOW, OPEN 2026-10-23) — the Phase 0 receipt reports S0.5 as "identical" over two EMPTY sets | 1 |
| BUG-972 | (LOW, OPEN 2026-10-23) — `r5_code_review.py --out <a path outside the repo>` writes the verdict, then DIES with a traceback | 1 |
| BUG-992 | (HIGH — OPEN 2026-10-24) — the S4 writer derives classification_status from failure_mode LENGTH, not from status, so a long-fm row | 1 |
| BUG-999 | (MED — OPEN 2026-10-24) — the store mutated at 19:07:30 with NO MUTATION_JOURNAL entry: the single-concept write path bypasses the | 1 |
| BUG-1001 | (LOW, OPEN 2026-10-25) — `guard_stacks_single_source.py` went RED once on a transient engine blip, so a flaky live-dependency can write a | 2 |
| BUG-1002 | (LOW - OPEN 2026-10-25) - the delegate journal's END vocabulary cannot express a READ-ONLY run: `done` demands an artifact, and | 1 |
| BUG-1024 | (MED - OPEN, OWNER-OWED 2026-10-26) - the oMLX Hugging Face token has NO Settings surface: two instructions named a door that does not | 1 |
| BUG-1028 | (LOW - OPEN 2026-10-26, RE-SCOPED out of BUG-1020 limb 2) - a delegate failure is reported as the word `Other`: the harness names no cause, | 1 |
| BUG-1030 | (MED, OPEN 2026-10-26) — the governance rail surface accreted five hidden couplings, so any consolidation is a non-atomic cascade (future | 1 |
| BUG-1033 | (MED, OPEN 2026-10-26) - market research had NO reference-class obligation, so a 2x throughput gap to a rival RUNTIME sat undetected across | 1 |
| BUG-1034 | (HIGH, OPEN 2026-10-26) - the execute_javascript bridge ran each tools.call TWICE, so one append landed TWO identical blocks in AGENTS.md | 1 |
| BUG-1035 | (MED, OPEN 2026-10-26) - the decision register has NO governed append route, so every hand append leaves its bytes attributable to no | 1 |
| BUG-1036 | (MED, OPEN 2026-10-26) - DECISION-LOG's tier tables lag the register by 22 records and NO rail can tell that from curation: the face | 1 |
| BUG-1041 | (MED, OPEN) - a reviewer's stability cannot be re-measured: model_eval_suite has no re-run channel | 1 |
| BUG-1048 | (MED, OPEN 2026-10-27) - R5 review coverage silently depends on FILE LENGTH: gpt-oss returns UNPARSED on a 26 KB script at both output | 1 |
| BUG-1049 | (LOW, OPEN 2026-10-27) - the severity vocabulary is DECLARED as MED and WRITTEN as MEDIUM: 20 headings use the undeclared word, and a bug | 1 |
| BUG-1050 | (HIGH, OPEN 2026-10-27) - `hf cache prune` names the SERVED snapshot of a live model as "detached", and `du -shL` reports 48G for a 16G | 1 |
| BUG-1051 | (HIGH, OPEN 2026-10-27) - oMLX 0.7.3rc1 makes the RATIFIED advisory best-arm UNLOADABLE (pplx-decider -> HTTP 409 on both endpoints), and | 1 |
| BUG-1052 | (MED, OPEN 2026-10-27) - rc1 ships `specprefill_enabled: true` on three models whose prompts never reach its 8192-token trigger: a | 1 |
| BUG-1053 | (MED, OPEN 2026-10-27) - the documented §7.1 re-baseline command cannot run on this host: bare `python3` is /usr/bin/python3, which has no | 1 |
| BUG-1054 | (MED, OPEN 2026-10-27) - the delete-safety test has TWO more holes: the served portfolio spans 3 roots, and the engine's pool (17 ids) is | 1 |
| BUG-1055 | (MED, OPEN 2026-10-27) - `plan` and `analyze` are assigned on SPEED alone: a REAP-pruned 19B now holds both over a 27B, and nothing | 1 |
| BUG-1056 | (MED, OPEN 2026-10-27) - the handover was UNRUNNABLE AS WRITTEN: interactive zsh does not treat `#` as a comment, so the verification line | 1 |
| BUG-1057 | (MED, OPEN 2026-10-27) - after the bytes were deleted the engine still ADVERTISED the model and kept its full flag set: a declaration with | 1 |
| BUG-1058 | (MED, OPEN 2026-10-27) - `hf cache delete` reported "freed 24.1G" with no measured counterpart: the cache arithmetic accounts for the 14G | 1 |
| BUG-1059 | (MED, OPEN 2026-10-27) - the inventory has a reference axis no check follows: one model's weight shards are symlinks INTO another model's | 1 |
| BUG-1064 | (MED, OPEN 2026-10-27, root cause MEASURED and named) - a reasoning model cannot emit a verdict at the declared budget: | 1 |
| BUG-1069 | (MED, OPEN 2026-10-27) - the store census partitions the HUB, so a store the engine also writes is outside every class it can report - and | 1 |
| BUG-1074 | (LOW, OPEN 2026-10-27) - the delegate journal's `--model` is a CALLER'S DECLARATION and nothing compares it to the model that did the work, | 1 |
| BUG-1076 | (MED, OPEN 2026-10-27) - "unverifiable" is ONE word for a harmless duplicate id and for a role model that cannot be reached, and nothing | 1 |
| BUG-1077 | (MED, OPEN 2026-10-27) - THE RECEIPT LEDGER HAS NO WRITER: `governance/calibration_receipts.jsonl` is declared append-only, 36 rows rest on | 1 |
| BUG-1083 | (MED, OPEN 2026-10-27) — the SUITE rail is RED on a census receipt mismatch, and the ladder's own comment still declares three reds that no | 1 |
| BUG-1084 | (MED, OPEN 2026-10-27) — `config/model_assignments.yaml#roles` IS A 24-ENTRY SECOND HOME THAT NO CODE RESOLVES, AND ONE OF ITS ENTRIES | 1 |
| BUG-1088 | (MED, OPEN 2026-10-27) — THE ONESHOT PATH CARRIES THE SAME TYPED WALL BUG-1085 JUST REMOVED: `timeout + 20` | 1 |
| BUG-1090 | (MED, OPEN 2026-10-27) — A ROLE WHOSE NAME PROMISES LONG-FORM OUTPUT IS BOUND TO THE SLOWEST SERVED MODEL, AND ITS HONEST GRANT IS 675 | 1 |
| BUG-1091 | (HIGH, OPEN 2026-10-27) - THE ALLOWANCE IS PRICED FOR A FIXTURE TURN: decode is paid out of the WHOLE budget and the PREFILL BILL is | 2 |
| BUG-1092 | (LOW, OPEN 2026-10-27) - 34 of the 269 OPEN ids have no section in the append-only register: a COUNT with no evidence BODY | 1 |
| BUG-1093 | (LOW, OPEN 2026-10-27) - A SUPERLATIVE OVER A COMPLEMENT SET READS AS A GLOBAL CLAIM: "worst measured non-27B decode (13.4 tok/s)" produced | 1 |
