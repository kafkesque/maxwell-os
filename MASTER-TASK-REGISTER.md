# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-09-01 | **Decisions:** D2000-D2499
> **D2499 (this session, Phase 0 BUG-150 recurrence guard):** post-S4 forensic audit (6,715 FBs) → BUG-195 (fb_id collision → S6 `INSERT OR REPLACE` silent 5-row loss) + BUG-196 (name truncation @8-word cap) + BUG-197 (domain-not-discipline). **Post-hoc (NO S4 rerun — checkpoint is raw/immutable):** `dedup_fb_id.py` (merge collisions) + `remap_emerging.py` (Phase 0a Unicode fold + 0b alias map; emerging 36.2%→25.5%) + `audit_s4_final.py` (pre-S5 deterministic forensic gate) + `s4_post_finish.py` (unattended orchestrator) + `alias_map.yaml` (215 validated aliases). **Default S4→S5 chain = stage4 → dedup → remap → gate → audit → S5 → S6.** BUG-188/D2487 truncation fix CONFIRMED already applied.
> **D2462 (this session, S2 architecture):** single-source + singleton S2 extraction unified into ONE extractor (2 passes, not 3) — keep convergent separate; `is_singleton_fb` becomes a provenance flag. PLANNED post-S2. See DECISION-LOG + `governance/aggregated_remaining_tasks.md`.
> **D2429 (this session, R1.1 ensemble adjudication):** Claude+ChatGPT cross-review of n=30 CONFIRMS the drift — judges independently downgrade ~40-50% of sampled causal_mechanism labels (matching the ~43% pre-score). FORM-axis ambiguity validated (D2427); consensus is silver-standard, not golden — third independent pass needed before trusting a 2-way majority. Human-review queue narrowed to 10 records (1,2,9,11,12,15,25,26,27,30). ChatGPT hand-tally arithmetic error noted (13/8/7/2 vs 12/9/6/3). Files: temp/chatgpt0020.md, temp/claude 0020.md.
> **D2427/D2428 (this session, R1 extraction_type drift):** ontological audit found the FORM axis is a non-partitioning 4-way flattening of three cuts (justification-strength / modality / structure) + two role↔form routing tables (D2150/D2417) violating the D2323 "orthogonal axes" contract. Drift confirmed: causal_mechanism 11%→60% single-source; n=30 sample ~43% mislabeled (7/18 causal over-claimed + under-labeling). R1 committed (df1fbfd): strict DECISION-ORDER precedence tree + DECOUPLING rule in S2 prompt + `pipeline/stage2_relabel_extraction_type.py` (LLM-driven relabel, fb_id-stable, copy-first, NOT yet run). D2427 (R2): split FORM into justification × modality facets after S4-S6 sign-off. BUG-160 evidence-relevance logged. Relabel sweep + P1 review are the next tasks.
> **D2423-D2426 (this session, P0 remediation):** S2 single-source run COMPLETE — 8,410 FBs, 13,895 clusters. P0 fixes: BUG-155 elaboration backfill (0 empty), BUG-156 final segids write (segids 13,895 complete, 0 orphan FB clusters), BUG-157 non-object guard + single-failure collapse (recovered cluster_37967 → +1 FB), BUG-158 record repair (6 broken body fields + 3 TI relabels, verified on copy then production). BUG-159 prompt-injection contamination (cluster_11649, 1 cluster = 0.007%) documented skip. Batched singleton extraction committed (d627f35) but NOT run. STOP before S4/S5/S6 for visual inspection.
> **D2420-D2422 (this session, 13:14):** Quarantine policy DECIDED (commit-with-status + retrieval-time filter, D2420); mixed remediation strategy DECIDED (re-extract gated+failed vs post-hoc fix names/route/discipline/PT-TI, D2421); domain/discipline disjointness audit (1 canonical overlap `education` + 267 raw-alias overlaps, mapping already kind-aware via D2133/D2394 — D2422). BUG-151 logged.
> **D2417/D2418 (this session):** S2 content-type conflation rescue (`_normalize_role_fields`) + content_type-aware summary gate — FIXED in code (8 tests), NOT re-run against t11 (checkpoint predates commit). Senior audit of t11 checkpoint found: BUG-147 (PT/TI role-label precision — 39/40 non-principle are process_template, ~25 are actually code snippets), BUG-148 (stale `route="FB"` on all 2,878 records), elaboration absent on ALL 229 single-source FBs, S4/S6 non-FB dead-end confirmed. Summary gate value audit: ~35-40% of gated clusters carry genuine objects.
> **D2409/D2410 (prior session):** S1.5 embedding cache + S5 incremental checkpoint/resume (crash recovery, 6 tests) — DONE. S4 metadata derivation audit fixes: temporal_scope boundary-match + no stopword "all" + contemporary-first, difficulty_map → live config (C12, 0/279 behavior drift), context "general" schema-legal (66/279 rows) — 7 tests → 47-test suite green. T1.1 stage PREPARED (caffeinate active, OMLX lazy-load 2/7 models, preflight clean).
> **F1/D2401 (this session):** post-S4 enrichment `pipeline/stage4_5_enrich.py` implemented — produces `prerequisite_fbs`/`contradicts_fbs`/`procedural_skill` (gated `stage4_5.enabled: false` for T1.1).
> **D2406/D2407 (this session):** session_seed.yaml YAML parse break fixed (boot/integrity); `run_production.py` dead code archived (C19); fail-closed regression tests added (`tests/test_fail_closed_d2402_2405.py`, 9 tests).
> **D2408 + R3 canary rerun (this session):** `response_format=json_object` forced xgrammar constrained decoding → empty gpt-oss-20b content (Harmony conflict, same family as D2392) — now skipped for reasoning-off models (config-first). **R3 canary S4→S6 rerun COMPLETE (19:22:39): S4 279/279 FBs (0 failed) → S5 236 PASS / 43 QUARANTINE / 0 FLAG → S6 279 committed (`pipeline_run_id=canary`) + Parquet, ~87 min — no regression vs 235/43.**
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (D2298). Final. No ongoing human adjudication.
> **Active Models:** Qwen3-Coder-30B (S2), GPT-OSS-20B (S4 classifier), DeBERTa-v3-large (S5 verifier), bge-m3 (Emb)
> **Redundant/Removed:** RoBERTa-large, Phi-4-mini (S5), all Gemma variants
> **Diagnostic:** 188 FBs, 72.4% S5 pass rate → T1.1 authorized (CONDITIONAL-GO — see B1-B15)
> **Detailed tasks:** `governance/aggregated_remaining_tasks.md`
> **Buglog:** `governance/buglog.md`

---

# 🔴 CURRENT SESSION (2026-09-01) — Post-S4 task queue (BUG-150 recurrence guard)

> **Live:** S4 at ~84% (PID 1933); watcher `s4_post_finish.py` live (PID 45537). Default S4→S5 chain = stage4 → dedup → remap → gate → audit → S5 → S6.

| # | Pri | Task | Where | Status |
|---|-----|------|-------|--------|
| 1 | P0 | Build + stress-test Phase 0 scripts (dedup / remap / orchestrator / audit / alias map) | `scripts/` + `config/alias_map.yaml` | ✅ DONE (idempotent + fail-closed verified) |
| 2 | P0 | Log BUG-195 (fb_id collision) + BUG-196 (name truncation) + BUG-197 (domain-not-discipline) + D2499 | buglog + DECISION-LOG | ✅ DONE |
| 3 | P0 | Unattended watcher monitoring S4 finish | `s4_post_finish.py --watch` (PID 45537) | ✅ LIVE |
| 4 | P1 | **At S4 completion (auto):** backup → dedup → remap → gate → audit → report | orchestrator | ⏳ awaiting S4 |
| 5 | P1 | **Human review before S5:** verify the 4 dedup merges (9→4), gate result (emerging ~25%), audit PASS | `checkpoint_deduped.jsonl` + `s4_post_finish_report.json` | ⏳ |
| 6 | P2 | Authorize S5 (only after audit PASS) → S6 | `just stage5` / `just stage6` | ⏳ |
| 7 | P3 | S4 code fix: cross-cluster dedup + S6 duplicate-fb_id fail-loud guard (BUG-195) | `stage4_merge.py` / `stage6_commit.py` | future batch |
| 8 | P3 | S4 code fix: name truncation — raise `fb_name_max_words` / ellipsis / concise generator (BUG-196) | `stage4_merge.py` / config | future batch |
| 9 | P3 | S4 classifier fix: enforce domain/discipline disjointness D2422 (BUG-197) | `stage4_merged_call.py` prompt + golden | future batch |
| 10 | P3 | C12: extract route.py hardcoded 10%/5% promotion thresholds → config | `pipeline/route.py` | post-S4 |
| 11 | P3 | D2399 dynamic promote/demote human review (organizational behavior, graphic design) — do NOT blind-promote | taxonomy hooks | post-S6 |
| 12 | P1 | Recover 6 dropped principles (`application:'None'`, BUG-198) — targeted backfill + re-inject pre-S5 | `rerun_s2_targeted.py` on 6 fb_ids | ⏳ before S5 |
| 13 | P2 | Backfill 25 sidecar empty shells (10 PT / 5 PI / 6 GE / 4 TI, body_incomplete) via cross-examination (D2470/D2474) — NOT same-extractor rerun (temp=0.0 no-op) | recipe-builder cross-exam | post-S5 |
| 14 | P0 | `audit_s4_final.py` sidecar sweep (body_incomplete + ontology + wrong_ct) | `scripts/audit_s4_final.py` | ✅ DONE (WARN default / `--strict-sidecars` FAIL) |
| 15 | P0 | Fix BUG-200 static-taxonomy cross-kind coercion (kind-safe `match_to_canonical` + `map_to_canonical_with_fallback` + CI guard) | `schemas.py` + `stage4_merge.py` + `test_taxonomy_disjointness.py` | ✅ DONE (4/4 green) |
| 16 | P0 | Fix BUG-199 D2399 promotion cross-kind guard | `taxonomy_manager.py` (`_is_opposite_kind`) | ✅ DONE |
| 17 | P1 | Post-hoc re-derive `domains` from raw (kind-safe) — 2,007 records fixed | `scripts/rederive_kindsafe_domains.py` | ✅ DONE + PROMOTED to `checkpoint_enriched.jsonl` (backup `backup_pre_kindsafe_promote_20260902_005603`) |
| 18 | P0 | Config cleanup — remove cross-kind aliases from `taxonomy_v5.yaml` (63) + `synonym_map.yaml` (18); `alias_map.yaml` verified clean (no change) | config/*.yaml (backed up `.bak_20260902_005929`) | ✅ DONE (all 3 configs 0 cross-kind) |
| 19 | P0 | Golden/few-shot forensic audit — S4 golden CLEAN; **BUG-201 `golden_max_examples=4` dropped S4-GOLD-005** → bump 4→5 + CI guard | `config/pipeline_config.yaml` + `tests/test_stage4_golden_contract.py` | ✅ DONE (D2501; 21/21 tests green) |
| 20 | P1 | Write S4/S5 bulletproof roundtable master prompt (Claude+ChatGPT) | `config/golden/MASTER-ROUNDTABLE-EVAL-PROMPT-v9-S4S5-BULLETPROOF.md` | ✅ DONE |
| 21 | P2 | stage2 golden `domain`/`discipline` metadata drift (~108 cross-kind/non-canonical labels, dormant) — migrate to canonical OR deprecate fields | `stage2_fewshot_*.yaml` | ⏳ future (not consumed — zero runtime impact) |
| 22 | P2 | Commit `config/alias_map.yaml` (was untracked) + `.gitignore` the `.bak_*` config backups | git | ✅ DONE (committed in D2501 push) |
| 23 | P3 | Taxonomy semantic near-duplicate: `ai systems` vs `ai & agents` (both canonical, both taught by golden) | `taxonomy_v5.yaml` | ⏳ future (needs D2399 human review, not this session) |
| 24 | P0 | Fix BUG-202 `_evidence_cleanliness_gate` fail-open (`return set()` → fail-closed) — the one near-blocker from roundtable | `stage5_verify.py:559` | ⏳ next (mitigated tonight by standalone `audit_evidence_cleanliness.py` gate) |
| 25 | P1 | Fix BUG-203 S5 `FLAG` dead code — wire it or delete it (reporting layer currently lies) | `stage5_verify.py` + `status.py` | ⏳ |
| 26 | P1 | Fix BUG-204 stale `TAXONOMY_MAX_DISCIPLINES` 72→75 (+ drop unused `_max_count`) | `pipeline_paths.py` / `taxonomy_manager.py` | ⏳ |
| 27 | P1 | S5 weak max-entailment rule (ChatGPT B2) — add contradiction veto + coverage + re-calibrate | `stage5_verify.py` `deberta_check` | ⏳ (conservative today: recall 0.386 → QUARANTINE-leaning) |
| 28 | P2 | De-overlap `ai systems`/`ai & agents` raw aliases ("AI Systems" in both) + rename `ai systems` for clarity; then D2399 human review | `taxonomy_v5.yaml` | ⏳ (do NOT merge — distinct) |
| 29 | P2 | Regenerate stale `.golden_meta.json` (hash/commit/count) + CI assert meta==actual | `config/golden/.golden_meta.json` | ⏳ |
| 30 | P2 | Rename/gut `tests/test_stage4_d2138.py` + `tests/test_stage4_exhaustive.py` (0 `test_*` functions — inflate coverage) | `tests/` | ⏳ |

---

# 🔴 NEW THIS SESSION — Frontier T1.1 Audit (4b55797) — 4 blockers found + fixed (D2402-D2405)

> **Three frontier LLMs (claude0015 / chatgpt0015 / kimi0015) audited HEAD 4b55797 against code.
> 4 launch-blockers converged + independently re-verified. All fail-closed/state-machine fixes — no redesign.**

| # | Priority | Finding | Fix | Status |
|---|----------|---------|-----|--------|
| 1 | P1 | S4 runner timeout '4': 3600 (1h) vs multi-hour full-corpus | '4': null (unlimited, like S2) | ✅ D2402 |
| 2 | P2 | S2 schema-invalid output rebranded as NULL + permanently processed | 3-state FB/NULL/FAILED; schema failure = failed_clusters | ✅ D2403 |
| 3 | P3 | S4 classification-failed clusters unrecoverable on resume | exclude FAILED clusters from processed_ids | ✅ D2404 |
| 4 | P4 | S4 fabricates evidence="cited" + S5 can PASS classification_status=FAILED | remove cited; S5 gates FAILED→QUARANTINE | ✅ D2405 |

**Also worth doing now (DONE in D2402-D2405 session):** vectorize compute_fb_relationships (O(n²)→matmul); S5 mechanism thresholds → config (C12).
**Post-fix integrity audit (D2406/D2407, 2026-08-17):** session_seed.yaml YAML parse break fixed → integrity 10/10, 12/12 YAML parse;
`run_production.py` dead code archived (C19); 9 fail-closed regression tests added → 34-test suite green.
**R3 canary S4→S6 rerun (2026-08-17, 19:22:39):** COMPLETE — S4 279/279 FBs (0 failed clusters, 52911 edges, 0 isolated) → S5 236 PASS / 43 QUARANTINE / 0 FLAG → S6 279 committed (`pipeline_run_id=canary`), FTS 279, Parquet `fbs_snapshot_20260817_192235.parquet` (4482.4 KB). ~87 min. D2408 validated live; 236/43 ≈ 235/43 → no regression from D2402–D2405. Failure-injection kill/restart in-vivo still pending (canary had 0 failures) — unit-tested only (D2407).
**Post-T1.1 hardening (logged, not blocking):** MPS renormalization, K-means degraded-marker, probe-cache fingerprint,
canonical source_id grouping, verbatim evidence verification, S4.5 runner registration, NLI calibration-data commit.
# 🔴 NEW THIS SESSION — 5-LLM Verification Round (D2367) — preflight/registry sync

> **Five independent LLM audits (claude0014/deepseek0013/kimi0013/qwen0013/chatgpt0014) cross-examined
> against HEAD `786e92f`; every claim re-verified against code. T1.1 = CONDITIONAL GO — data path is
> fail-closed + canary-green; remaining blockers are release hygiene, not pipeline correctness.**

| # | Type | Item | Status |
|---|------|------|--------|
| V1 | Bug | **BUG-132**: `thinking_budget` was a GLOBAL key shared by merged+depth calls | ✅ DONE (D2368) — per-call threading + `depth_thinking_budget` config key |
| V2 | Gov | Golden hash → `just preflight` hard gate (`verify_golden_hash.py`) | ✅ DONE (this session) |
| V3 | Gov | `decisions.yaml` reconcile to D2367 (+ fix `sync_decisions.py` broken description generator) | ✅ DONE (this session) |
| V4 | Gov | Purge stale "98%"/"160-200h" from MTR/ROUNDTABLE/S4_BOTTLENECK_ANALYSIS | ✅ DONE (this session) |
| V5 | Gov | `pipeline_commit` → v3.0-D2367; buglog 18 header/body emoji align | ✅ DONE (this session) |
| V6 | Bug | `apply_depth_relabel.py:53` list-form silent-drop (CONV-037/039) | ✅ DONE (this session) |
| V7 | Gov | DECISION-LOG.md D2351–D2363 gap (IDs lived only in decisions.yaml/buglog) | ✅ DONE (D2368) — backfilled 12 entries; D2363 dedup'd |
| V8 | Data | Golden depth imbalance: universal=1, specialized=1 (23 `None` are NEGATIVE route=NULL examples, NOT gaps) | ✅ DONE-partial (D2369) — CONV-054 (universal) + CONV-055 (specialized) added with genuine 2-book convergence; universal 1→2, specialized 1→2; hash re-stamped. Full ≥5/≥5 = T-015 remainder |
| V9 | Ops | Kill/restart resume test before the 39h run | ✅ DONE (D2370) — root cause: runner resume is STAGE-granular + SIGINT-only (no SIGTERM handler, no process group); S4 (the 39h stage) had NO intra-stage checkpoint. FIXED: S4 now checkpoints every 5 clusters (`.segids`/`.state.json`) + skip-on-resume. Live `kill -9` + resume verified on 20-cluster subset. The `kill -TERM` procedure was WRONG (orphans child, never writes marker) — superseded |

> **Refuted false alarms (verified):** Qwen "D2229 sqlite-vec 1024→512 → S6 crash" is FALSE (code reads
> `S15_EMBED_DIM`; only the log status string was stale). DeepSeek/Qwen "CONV-037/039 missing depth" is FALSE
> (both list-form with `depth: domain`). "~90h"/"160-200h" are stale denominators — correct is ~39h.

### T-015 — Golden depth expansion (universal/specialized) — SPEC
- **Goal:** positive-set universal 1 → ≥5, specialized 1 → ≥5 (currently 37 cross-domain + 11 domain dominate).
- **Progress (D2369):** universal 1→2 (CONV-054 Price of Anarchy), specialized 1→2 (CONV-055 Crypto One-Way Hashing). Both genuine 2-book convergence, verbatim evidence, hash re-stamped.
- **Correction:** the 23 `depth: null` examples are **NEGATIVE** (route=NULL: platitudes, echoes, non-falsifiable), NOT gaps — do not "label" them.
- **Corpus candidates (verbatim counts):** universal — network effect (221), natural selection (326), power law/Pareto (161), prisoner's dilemma (65), second law/entropy (49); specialized — kerning (488), color space (332), double-entry (17), Nyquist (25), B-tree (9), cryptographic hash (8).
- **Procedure:** (1) grep `knowledge pipeline/stage1_chunk/latest/checkpoint.jsonl`; (2) confirm the passage states a principle + mechanism + boundary/consequence; (3) extract verbatim `evidence_passage` + `source_book` + `segment_id`; (4) write name/definition/mechanism/boundary/consequence/discipline/domains/depth; (5) re-stamp `.golden_meta.json` (verify_golden_hash.py now hard-gates preflight); (6) re-run depth benchmark to confirm no classifier regression.

### V9 — Kill/restart resume test — SUPERSEDED by D2370 (S4 intra-stage checkpoint)
- **Finding (D2370):** the runner's resume marker is **stage-granular** and **SIGINT-only** — there is no SIGTERM
  handler and `subprocess.run(..., capture_output=False)` launches S4 with no process group. So the old procedure
  (`kill -TERM <runner_pid>`) would (a) never write the paused marker and (b) orphan the S4 child to keep running.
  The correct interrupt is SIGINT (Ctrl+C / `kill -INT`), but even that only marks the STAGE, not progress within S4.
- **Fix shipped (D2370):** S4 now writes an intra-stage incremental checkpoint every `stage4.checkpoint_interval`
  (5) clusters — atomic `.segids` (processed IDs) + `.state.json` (counters) — and resumes from it on re-entry,
  independent of the runner's signal handler. **Survives `kill -9`** up to the last checkpoint.
- **Verified live:** `run_id=s4-restest`, 20-cluster subset — checkpoint fired at 5 clusters, hard `kill -9`, re-run
  printed `S4 resuming: 5 FBs ... — 15 remaining` and resumed from cluster #6 (skipped the 5 checkpointed).
- Remaining pre-launch op (optional): re-run the full canary slice to confirm no `fb_id` dup/skip after a live resume.

---

# 🔴 NEW THIS SESSION — 4th Audit Adjudication (BUG-108…119, D2351–D2355, 2026-08-14)

> **4-LLM audit (`chatgpt0010.md`, `claude0010.md`) × independent code re-verification.** S4 depth fail-open + provenance/schema gaps + singleton index + S4 bottleneck. Must/Should/Worth tiers → `governance/T1.1_CANARY_READINESS_MUST_SHOULD_WORTH.md`. Two ChatGPT errors corrected.

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **M1** | D2351 | S4 depth fail-closed — no silent `"domain"` (BUG-108) | 0.5h | ✅ DONE |
| **M2** | D2351 | `depth_max_tokens` 512 → 1024 (BUG-109) | 0.25h | ✅ DONE |
| **M3** | D2352 | Carry `source_segments` through S4→S6 (BUG-110) | 1h | ✅ DONE |
| **M4** | D2352 | Persist `is_summary` end-to-end (BUG-112) | 0.5h | ✅ DONE |
| **S1** | D2352 | Persist `evidence_passages` to SQLite (BUG-111) | 1h | ✅ DONE |
| **S2** | D2353 | Singleton S2→S4 index fix (BUG-113) | 1h | ✅ DONE |
| **S3** | D2354 | S4 bottleneck resolution — batch focused depth (BUG-114) | 2–3h | ❌ REJECTED (D2366) — batch 66.7% vs 84.4% seq (n=45), parity 60% |
| **S4** | D2355 | Batch missing-output fail-closed (BUG-115) | 0.5h | ✅ DONE |
| **S5** | D2351 | Depth benchmark authority (BUG-115) | 1h | ✅ DONE |
| **W1–W7** | D2355+ | Hygiene: dead `s3_original_domain`, secondary writers, `jargon`-FTS (BUG-116…119 + drift) | 3h | 🟡 OPEN (W7 `deathpectation` ✅ RESOLVED 2026-08-15 — private Anytype space name) |

> **Verdict (re-verified 2026-08-15, D2367):** M1/M2/S1-S5 were **all implemented** (D2351-D2355) — the prior
> "OPEN" statuses were stale. S3 (batch depth) is **REJECTED** by D2366. S4 speed is NOT a correctness gate —
> T1.1 is **~39h** (not 142h, D2365/D2366). Remaining T1.1 blockers are **governance/release hygiene**, not pipeline code.

---

# 🔴 NEW THIS SESSION — 3rd Audit Adjudication (D2349–D2350, 2026-08-14)

> **Deep audit of T1.1 canary + taxonomy adjudication.** User rejected several prior audit conclusions and
> clarified schema/taxonomy definitions. Fixed surgically in strategic order:

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B19** | D2349 | content-type field taxonomy: separate core_body / classification / metadata; jargon→body (after elaboration); keywords→metadata.discovery; evidence_passages→metadata.provenance (verbatim quotes, NOT body) | 0.5h | ✅ DONE |
| **B20** | D2350 | S4 identity/provenance: preserve S2 fb_id (no rehash after title-case; 73 records were drifting); preserve real source_cluster id (was overwritten with fb_id); short numeric name-collision suffix (was 64-char hash) | 1h | ✅ DONE |

> **Validation:** `config_audit --check-unchecked --strict` ✅ · `just integrity` 17/17 ✅ · `just healthcheck` 10/10 ✅ ·
> `just preflight` stress ALL_PASS ✅. **Remaining open (as of this session):** BUG-106 (S2 checkpoint pretty-print corruption), BUG-104
> (sqlite-vec load_extension), 2 single-source FBs leaked (`Hybrid Sorting Algorithm`, `Price Reduction Profit Maximization`),
> S4 speed (~3.5 FBs/min). **Subsequently resolved:** BUG-106 ✅ FIXED 2026-08-14 (self-verifying writer); the 2 leaked
> single-source FBs ✅ FIXED 2026-08-14 (BUG-107 split-probe drops single-source); S4 speed → ~39h not a correctness gate (D2365/D2366).
> BUG-104 remains 🟠 env-only (FTS fallback, non-blocking).

# 🔴 NEW THIS SESSION — 2nd Audit Adjudication (D2345–D2347, 2026-08-13)

> **ChatGPT/Qwen audit of `T1.1_ROUNDTABLE_AUDIT_PROMPT.md` (post-D2344).** Two new code-verified blockers
> surfaced that the B1–B15 set did not cover — both hit the **principle** path, not just the non-type pass.

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B16** | D2346 | S1.5 embedding-drop index alignment — return `(filtered_segments, embeddings)` + `len` assert + drop tests | 1h | ✅ DONE |
| **B17** | D2347 | e2e convergence metric → `sum(c["is_convergent"])` (canonical IDs), filename-diversity as diagnostic | 0.5h | ✅ DONE |
| **B18** | D2348 | embedding reliability — `embed_timeout: 180` + `embed_keep_alive: -1` (config-driven, BUG-105) | 0.5h | ✅ DONE |

> **✅ T1.1 CANARY GREEN (2026-08-14).** 25K segments → S1.5(2255 clusters/207 conv) → S2(280 FBs) → S4(279 FBs)
> → S5(239 PASS/40 QUAR) → S6(279 committed). V1–V6 all pass. **S4 speed gate resolved:** full-run is **~39h
> (D2365/D2366, ~3,556 principle FBs)** — not 142h (that was a cluster-vs-FB denominator error). BUG-105
> (embedding instability) found+fixed mid-canary via D2348.

> **D2345 (non-type second pass):** DECIDED as principle-first + separate single-source `stage2_extract_nontype.py`
> (post-T1.1). NOT a T1.1 blocker. Whether convergent PT/PI/GE/TI even occur = UNKNOWN; measure offline first.
> **B16/B17 IMPLEMENTED** (`just integrity` 17/17, `just preflight` stress PASS). **BUG-104** (sqlite-vec
> `load_extension` missing on python.org Python 3.12.1) discovered — non-blocking (FTS fallback), environmental.

# 🔴 NEW THIS SESSION — 4-LLM Audit Adjudication (D2337–D2341, 2026-08-13)

> **4 external LLM audits** of `governance/SCHEMA_PIPELINE_STATE_AUDIT_PROMPT.md` were adjudicated.
> Kimi/DeepSeek = repo-blocked (correctly refused to fabricate; zero signal). Qwen = repo-blocked but rated the prompt's
> own claims as VERIFIED (epistemically unsound; PASS verdicts discarded). ChatGPT = only repo-reading audit;
> independently re-verified here. **Findings surfaced 5 new blockers (B11–B15) on top of the B1–B10 set**, the most
> serious of which is NOT the S2/OMLX reliability I'd been focused on, but a **Stage 6 SQLite data-loss bug** (D2337).

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B11** | D2337 | S6 persist `content_type`/`extraction_type`/`mechanism`/`boundary`/`consequence` + round-trip test | 2h | ✅ DONE |
| **B12** | D2338 | S4/S6 fail-closed — `failure_ratio > max → exit 1`, `>0 → exit 2`, no COMPLETE manifest | 1.5h | ✅ DONE |
| **B13** | D2339 | runner `--run-id` import-ordering — pre-parse args before run-scoped imports | 1h | ✅ DONE |
| **B14** | D2340 | model-registry drift — session_seed renamed; config/path rename deferred (post-T1.1) | 0.5h | 🟠 PARTIAL |
| **B15** | D2341 | schema corrections — three-axis `status`, keep typed edges, add TI class, feedback→YAML (P2) | 3h | 🟡 DEFERRED |

> **Ordering:** B11→B12 first (S6 data loss + fail-open = silent permanent corruption of the first canonical corpus).
> B13→B14 are config/run-scoping correctness. B15 is schema contract work deferred to P2. NOTE: ChatGPT's "enable hybrid
> gate" recommendation is **REJECTED** — BUG-085 A/B test already proved the heuristic HybridGate is net-negative
> (4.3% negative rejection); run traditional-only. **B11–B14 now IMPLEMENTED; B14 config/path rename + B15 deferred post-T1.1.**

---

# 🔴 NEW THIS SESSION — T1.1 Roundtable Audit (D2324–D2332, 2026-08-13)

> **CONDITIONAL-GO.** 3-LLM adversarial roundtable (kimii/chatgpt/qwen) independently verified against the code.
> **A second independent code sweep (2026-08-13) added B1 — the S2 checkpoint format/resume coupling** (D2332, not in the
> original 7). Blocker ordering below is **data-flow + dependency aware** (upstream integrity → correctness → verification truth),
> NOT by auditor source. See D2324 for the roundtable verification record (kimii's findings rejected as fabricated; qwen's
> "0.65 threshold" rejected).

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B1** | D2332 | S2 checkpoint fail-closed `load_jsonl` at every reader + resume | 1h | ✅ DONE (D2343) |
| **B2** | D2329 | Resume-validity manifest — checkpoint sidecar (run_id/schema/count/COMPLETE) | 2h | ✅ DONE |
| **B3** | D2326 | S0 fail-closed + tri-state quality check (C16) | 1h | ✅ DONE |
| **B4** | D2323 | Content-type golden fix → 5-role ontology | 0.5h | ✅ DONE |
| **B5** | D2323 | Content-type enum wiring + `route_values` config-driven (C12) | 2h | ✅ DONE (D2343) |
| **B6** | D2327 | S1.3 prefilter `--in-place` in runner + e2e | 0.5h | ✅ DONE (D2343) |
| **B7** | D2331 | S2 silent-skip fail-closed (`S2_MAX_FAILED_RATIO`) | 2h | ✅ DONE |
| **B8** | D2328 | S5 calibration truth (P=0.647/R=0.386/F1=0.484) + runner desc + audit prompt | 0.5h | ✅ DONE |
| **B9** | D2325 | S6 provenance per-FB `INSERTED/FAILED/SKIPPED` | 1h | ✅ DONE |
| **B10** | D2330 | e2e run-scoping + quarantine retrieval contract test | 1.5h | ✅ DONE |

> **Ordering rationale:** B1→B2 first (checkpoint format + resume coupling is the only pair that can silently corrupt the
> *entire* run). B3 before B4–B7 (garbage-in). B4 before B5 (labels before enum). B5 before B7 (S2 must emit correct types
> before S4 can route). B8–B9 last (verification/commit truthfulness — corrupts claims, not data). **All B1–B10 IMPLEMENTED.**

---

# 🔴 NEW THIS SESSION — Content-Type Ontology Consolidation (D2323, 2026-08-13)

> **The #1 pre-T1.1 architectural fix.** Content-type taxonomy was fractured across 4 places (S2 flat label, S4 dead schema classes, stale golden few-shot vocabulary, v1 ZONE templates). Verified findings this session:
> 1. **Orphaned non-principle FBs (BUG-093)** — S2 extracted 3 `process_template` + 1 `tool_instruction`; silently dropped at S2→S4 (never reached S4/S5; separate output files absent).
> 2. **Dead schema code** — `ProcessTemplate` (24 fields) / `ProcessInstance` (16 fields) / `GrowthEdge` classes never instantiated; S4 writes raw S2 dicts.
> 3. **Stale golden vocabulary** — `stage2_fewshot_convergent.yaml` uses `content_type: model/heuristic/pattern` (extraction_type values) — contamination under temp=0.0.
> 4. **`fact`/`meta` vestigial** enum values (schemas.py docstring only) — dropped.
>
> **Resolution (D2323):** `config/content_types.yaml` — single config-driven registry. Two orthogonal axes: `content_type` (5) × `extraction_type` (4). Core body + per-type extension delta. 13-field `tool_instruction`. D2150 + D2128 mappings. **Contract frozen; code wiring + golden-example fix = NEXT SESSION (before T1.1 full run).**
>
> **Files:** `config/content_types.yaml` (NEW) → wire into `pipeline/schemas.py`, `pipeline/stage2_extract.py`, `pipeline/stage4_merge.py`, `config/golden/stage2_fewshot_convergent.yaml`

# 🔴 CRITICAL — BLOCKING T1.1

> ⚠️ **SUPERSEDED (2026-08-15, D2367):** this section predates the 5-LLM verification round. P0.1 (hybrid gate) is
> **REJECTED** (BUG-085 A/B net-negative); P0.7 (BUG-001) and P0.8 (BUG-014) are **RESOLVED** (see "Older BUG-001/011/012/013/014…
> resolved in prior sessions"); P0.2-P0.6 (manifest/schema-split/ISOR/golden-tier/DSPy-metric) were **implemented or logged** in
> D2282-D2287 and do NOT block T1.1. T1.1 = **CONDITIONAL GO**. See D2367/D2369 and the top of this register.

| # | Decision | Task | Effort | Bug |
|---|----------|------|--------|-----|
| **P0.1** | D2276 | **Wire hybrid S2 to production** — move hybrid_s2_extract() into stage2_extract.py. DSPy gate + traditional extraction. +0.145 quality (0.736 vs 0.591). | 4-8h | BUG-085 |
| **P0.2** | D2282 | **Pipeline manifest** — frozen per-run config: git_commit, model/prompt/schema/taxonomy versions. Embed hash in every checkpoint. | 1-2h | — |
| **P0.3** | D2283 | **FB schema split** — core vs enrichment contract. S5 verifies core only. Fixes BUG-080.5 field substitution. | 2-3h | BUG-080.5 |
| **P0.4** | D2284 | **ISOR source independence scoring** — author/citation-chain/evidence-tradition independence beyond BORP≥2. | 4-6h | — |
| **P0.5** | D2286 | **Golden tiered classification** — GOLD-A (train DSPy), GOLD-B (evaluate), CHALLENGE (test). DSPy training safety. | 2h | — |
| **P0.6** | D2287 | **DSPy metric with hard gates** — evidence_invalid→0, wrong_route→0, false_convergence→0. THEN weighted quality. | 2-3h | — |
| **P0.7** | BUG-001 | **Empty pass loop** — verification checks random principles. Phase 0, P0.8. | ? | BUG-001 |
| **P0.8** | BUG-014 | **Cloud burst code violates C1/C3** — constitutional violation. Phase 0, P0.13. | ? | BUG-014 |

---

# 🟠 HIGH — COMPLETE WITHIN WEEK OF T1.1

| # | Decision | Task | Effort | Bug |
|---|----------|------|--------|-----|
| **P1.1** | D2285 | **Claim decomposition for S5** — per-claim NLI before synthesis verdict. Highest S5 accuracy lever. | 8-12h | — |
| **P1.2** | D2292 | **Golden depth expansion** — 170+ examples (30 universal, 40 cross-domain, 40 domain, 30 specialized, 30 hard negatives). | 8-16h | BUG-084 |
| **P1.3** | D2277 | **S4 enrichment verification in S5** — fact-check application/failure_mode/elaboration. Most dangerous hallucination gap. | 2h | — |
| **P1.4** | D2289 | **Author-disjoint DSPy splits extended** — domain/book/paraphrase-aware. | 3-4h | — |
| **P1.5** | D2288 | **Roundtable Fleiss' kappa** — inter-rater reliability statistic. | 1h | — |
| **P1.6** | D2272 | **NLI threshold validation fatal** — raise ValueError, not warn. | 5min | BUG-080.6 |
| **P1.7** | D2274 | **Ollama embedding dimension assertion** — MPS path has it, Ollama path doesn't. | 1h | BUG-080.7 |
| **P1.8** | D2275 | **Embedding drop-rate quality gate** — fail stage if drop_rate > 0.005. | 1h | BUG-080.8 |
| **P1.9** | D2271 | **S5 v3 schema strict validation** — no mechanism↔application substitution. | 30min | BUG-080.5 |
| **P1.10** | BUG-013 | **OMLX guard uses pkill -f** — kills pipeline itself. Phase 0, P0.12. | ? | BUG-013 |
| **P1.11** | BUG-012 | **sqlite-vec not loaded before CREATE VIRTUAL TABLE**. Phase 0, P0.11. | ? | BUG-012 |
| **P1.12** | BUG-055 | **related_fbs vs related_blocks field name mismatch** — blocks delegation. | ? | BUG-055 |
| **P1.13** | — | **FAISS threshold mismatch** — pipeline_config.yaml:0.75 vs session_seed.yaml:0.70. | 0.5h | — |
| **P1.14** | — | **AGENTS.md stage count** — still says "9-stage" despite Stage 3 removal. | 0.5h | — |
| **P1.15** | — | **Ruff lint auto-fix** — 322 auto-fixable in pipeline/. | 1h | — |

---

# 🟠 HIGH — PIPELINE EXECUTION

| # | Task | Effort | Notes |
|---|------|--------|-------|
| **T1.1** | **Full S1.3→S6 run on 12,964 clusters** | **~39h** (D2365/D2366) | Batch-resume capable. S4 serial ~39h on ~3,556 principle FBs (2,634 convergent × 1.35). ⚠️ "160-200h" (D2363) and "~21-26h" (D2253) both stale |
| **T1.2** | **Yield crisis diagnostic** — re-measure on full run output. 14 FBs / 852 books = 0.004% was v2.0. | 2h | Post-T1.1 |
| **T-007b-v2** | **Re-optimize MIPROv2 with 3 demos** (overnight) — close DSPy gate FN gap. | 1h setup + overnight | Optional polish |
| **T-015** | **Extraction type expansion** — 4→12-15 per type + depth class balance. Fixes golden pool imbalance. | 2d | — |

---

# 🟠 HIGH — NLI + VERIFICATION CALIBRATION

| # | Task | Effort | Notes |
|---|------|--------|-------|
| **NLI-1** | **NLI calibration on real data** — validate DeBERTa threshold on larger sample post-T1.1. | 2h | Already calibrated at 0.10 on 12 FBs |
| **NLI-2** | **LLM eval on golden set** (25 ex, 2+ LLMs) | 2h | Golden set is `needs_review` |
| **NLI-3** | **Cross-encoder reranker gate** — bge-reranker-v2-m3 ONNX between S2 and S5. | 1d | 1.2GB VRAM trade-off |
| **NLI-4** | **Source-independence graph** — model citation chains, effective_source_count. | 1d | — |

---

# 🟡 MEDIUM — NEXT SPRINT

| # | Task | Effort | Source |
|---|------|--------|--------|
| **T2.1** | Execute ONE business PI with existing FBs — existential test | 2h | Qwen, Kimi |
| **T2.2** | Atomic evidence schema — per-passage NLI, not majority vote | 2d | ChatGPT C9 |
| **T2.3** | Monotonic trust state machine — DB-level transition constraints | 2d | ChatGPT C7 |
| **T2.4** | Surface reliability scores in Zone 3 — context-conditioned | 1d | DeepSeek, Kimi |
| **T2.5** | skill.md standard (Layer 2 MVP) — IBM progressive disclosure | 4h | aggregated |
| **T2.6** | Hardware probe (C24) — auto-detect RAM, select model quant | 3h | aggregated |
| **T2.7** | 20-book E2E test — validate v3.0 at scale | 3h | aggregated |
| **T2.8** | Integration test suite — `just test` golden-file regression | 4h | aggregated |
| **T2.9** | Adversarial golden set — contradiction, false convergence tests | 2d | ChatGPT §41 |
| **T2.10** | RAGTruth hallucination suite — 10 adversarial test types | 1d | ChatGPT §14 |
| **T2.11** | ARES component evaluation — per-component metrics | 1d | ChatGPT §40 |
| **T2.12** | One pipeline authority — canonical DAG → generated docs | 1d | ChatGPT §3 |
| **T2.13** | Split config into active/archived/experiments | 1d | ChatGPT C13 |
| **T2.14** | Collapse config authority — one canonical YAML per domain | 1d | ChatGPT C15 |
| **T2.15** | Prompt lineage stamping — prompt_id, prompt_hash, prompt_version | 1d | ChatGPT C16 |
| **T2.16** | Move taxonomy from hardcoded Literal to YAML-driven | 2d | DeepSeek D5 |
| **T2.17** | Pydantic FB fields — mechanism/boundary/consequence in Pydantic model | 0.5d | N2 |
| **T2.18** | Actionability field — descriptive/prescriptive/diagnostic | 0.5d | N3 |
| **T2.19** | D2278 — Runner health check uses stress test | 2h | P2 |
| **T2.20** | D2279 — S1.5 drop rate metrics persisted to run_meta | 1h | P2 |
| **T2.21** | D2280 — FAISS IndexFlatIP → HNSW | 2h | P2 |
| **T2.22** | D2281 — Tiered BORP per depth | 2h | P2 |
| **T2.23** | gov-sync — decisions.yaml missing D2210/D2212/D2233-D2239 etc. (DECISION-LOG gap) | 4h | Historical |

---

## ⚪ LOW — BACKLOG

| # | Task | Effort | Source |
|---|------|--------|--------|
| T3.1 | USearch vs FAISS benchmark | 2h | aggregated |
| T3.2 | MeshRAG hash-driven clustering eval | 1d | DeepSeek |
| T3.3 | Leiden clustering via python-igraph | 2h | Qwen |
| T3.4 | Schema migration scripts — v2.x → v3.0 | 3h | aggregated |
| T3.5 | HyDE for abstract queries | 1d | ChatGPT §20 |
| T3.6 | Multi-perspective retrieval (STORM-inspired) | 1d | ChatGPT §32 |
| T3.7 | ColBERT benchmark on Maxwell corpus | 1d | ChatGPT §22 |
| T3.8 | Pydantic AI harness for agent orchestration | 1w | Kimi |
| T3.9 | Agent execution safety boundary | 3d | ChatGPT C14 |
| T3.10 | Dry-run mode on all stages | 4h | aggregated |
| T3.11 | Modularize stage2_extract (1,480 lines) + stage4_merge (1,260 lines) | 3d | Kimi |

---

## 🔵 TIER 4 — RESEARCH (Ongoing)

| # | Foundation | Status |
|---|-----------|--------|
| R1 | Typed Graph Storage — Zep/Graphiti eval | ⬜ DEFERRED |
| R2 | Edge Type Ontology — 10-15 types | ⬜ DEFERRED |
| R3 | Skill Subgraph Templates — graduate at 50+ skills | ⬜ DEFERRED |
| R4 | Constitutional Constraint Graph — C1-C28 as graph invariants | ⬜ DEFERRED |
| R5 | Self-Observation Protocol — agent queries own graph | ⬜ DEFERRED |
| R6 | IBM course transcript for Layer 2 | ⬜ DEFERRED |
| R7 | GAAMA 4-node memory | ⬜ DEFERRED |
| R8 | awesome-agent-skills repo eval | ⬜ DEFERRED |
| R9 | caveman prompt framework — local-first S2 prompts | ⬜ DEFERRED |
| R10 | vLLM-mlx for multi-agent | ⬜ DEFERRED |
| R11 | LanceDB unified store | ⬜ DEFERRED |
| R12 | ONNX runtime for NLI | ⬜ DEFERRED |

---

## 🟠 OPEN / PARTIAL BUGS (current — 2026-08-15)

> Older BUG-001/011/012/013/014/045/050/051/054/055/085 resolved in prior sessions (see buglog.md SESSION RESOLUTIONS). None block T1.1.

| Bug ID | Severity | Description |
|--------|----------|-------------|
| BUG-063 | 🟡 PARTIAL | `delegate()` sandbox has no filesystem access (architectural); workaround `pipeline/omlx_delegate.py` is first-class (D2344). NOT a T1.1 pipeline blocker |
| BUG-098 | 🟡 PARTIAL | `psutil` in requirements.txt done; integrity-check whitelist→requirements refactor deferred |
| BUG-099 | 🟡 PARTIAL | model-registry rename — session_seed done; config/path rename deferred post-T1.1 |

### ⏳ DEFERRED (post-T1.1)

| Bug ID | Description |
|--------|-------------|
| BUG-083 | `domain_anchors.yaml` predates corpus (80.5% "emerging") — D2292 golden depth expansion |
| BUG-084 | Golden depth calibration — was universal=1/specialized=1; now 2/2 (D2369); full ≥5/≥5 = T-015 |
| BUG-081 | `evals/golden_cases.json` v2 format migration |
| BUG-073 | CONV-035/037 false convergence — D2232 |

### ✅ RESOLVED BUGS (this + recent sessions)

| Bug ID | Description | Resolution |
|--------|-------------|------------|
| BUG-080 | call_omlx_json returns list/str — S4 crashes | ✅ FIXED (guards applied) |
| BUG-080.1 | _save_diag_state flush/fsync outside with block | ✅ FIXED |
| BUG-080.9 | S5 method tag dict missing "nli+LLM-echo" | ✅ FIXED |
| BUG-080.10 | S5 method tag dict missing "mech_quality" | ✅ FIXED |
| BUG-082 | S5 FLAG path practically unreachable (0/185) | ✅ CONFIRMED — FLAG path deleted (D2298) |
| BUG-076 | S5 NLI config overrides DeBERTa FEVER | ✅ FIXED (D2255) |
| BUG-077 | stage5_verify.py docstring triple-stale | ✅ FIXED (D2256) |
| BUG-078 | Stale classify_model in v2.3 checkpoint | ✅ FIXED (D2258) |
| BUG-079 | HANDOFF claims Phi-4-mini for S5 verify/gates | ✅ FIXED (D2260) |
| BUG-053 | Phi-4-mini hallucinates on open-ended research | ✅ MITIGATED (D2268); removed from S5 (D2298) |
| D2299 | 4-value unpack bug in deberta_check call site | ✅ FIXED (2026-08-12) |

---

## ✅ DONE — D2298-D2299 S5 FINAL ARCHITECTURE (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2298 | **DeBERTa-only NLI** — RoBERTa removed. Threshold 0.10. Single encoder. No human adjudication needed. ⚠️ Calibration superseded by D2322: honest P=0.647/R=0.386/F1=0.484 (D2293's P=1.000 was on the broken pre-BUG-092 call). | ✅ DONE |
| D2299 | **4-value unpack bug fixed** — deberta_check call site updated to 3-value unpack. Docstrings updated to DeBERTa-only. | ✅ DONE |
| — | RoBERTa-large removed from S5 (zero signal on paraphrase evidence, D2227) | ✅ DONE |
| — | Phi-4-mini removed from S5 (67% acc, hallucination risk) | ✅ DONE |
| — | BORP check deleted (S1.5 guarantees ≥2 sources) | ✅ DONE |
| — | Completeness check deleted (S4 always fills all fields) | ✅ DONE |
| — | FLAG path deleted (0/185, confirmed unreachable) | ✅ DONE |
| — | Gemma models deleted from OMLX | ✅ DONE |

---

## ✅ DONE — D2294-D2297 DUAL-ENCODER S5 + CRIBS GUARD (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2294 | Dual-encoder S5: DeBERTa-large + RoBERTa-large replace Phi-4-mini | ✅ DONE (superseded by D2298) |
| D2295 | CRIBS quality guard in S4 — post-generation validation | ✅ DONE |
| D2296 | D2293 scaled down — calibration tool built | ✅ DONE (superseded by D2298) |
| D2297 | Gemma models deleted from OMLX configs | ✅ DONE |

---

## ✅ DONE — ROUND 2 CROSS-EXAMINATION P0 (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2290 | Re-anchor taxonomy for AI/agents — fix 80.5% "emerging" catch-all | ✅ DONE |
| D2293 | Human-adjudicate FBs → S5 calibration | ✅ DONE (completed via D2298) |
| D2291 | S5 FLAG path audit — confirmed 0/185, FLAG deleted | ✅ DONE |
| D2269 | Runner 60-min timeout per-stage configurable | ✅ DONE |
| D2270 | Runner docstring fix | ✅ DONE |
| D2273 | S5 role naming sync — model_assignments | ✅ DONE |
| G1-G9 | Governance audit fixes (CONSTITUTION, AGENTS, model_assignments, etc.) | ✅ DONE |

---

## ✅ DONE — D2255-D2262 P0 AUDIT FIXES (2026-08-11)

| # | Task | Decision | Status |
|---|------|----------|--------|
| P0.1 | Swap S5 NLI to DeBERTa FEVER | D2255 | ✅ FIXED |
| P0.3 | Archive GOLDEN-REVIEW.md v2.0 | D2259 | ✅ DONE |
| P0.4 | Fix golden YAML meta count (36→55) | D2257 | ✅ FIXED |
| P0.5 | Fix stage5_verify.py docstring | D2256 | ✅ FIXED |
| P0.6 | Remove stale classify_model from config | D2258 | ✅ FIXED |
| P0.7 | Goose MacWebContentsOcclusion | D2262 | ✅ DOCUMENTED |
| P0.8 | Fix HANDOFF model registry | D2260 | ✅ FIXED |

---

## ✅ DONE — D2265-D2268 BOTTLENECK + GUARD FIXES (2026-08-11)

| # | Task | Decision | Status |
|---|------|----------|--------|
| P1.1 | Batch classification for S4 | D2265 | ✅ DONE |
| P1.2 | Process guard (PID file) | D2266 | ✅ DONE |
| P1.3 | Laptop sleep prevention | D2267 | ✅ DONE |
| P1.4 | BUG-053 mitigation | D2268 | ✅ DONE |
| P1.5 | Disk + memory pre-flight checks | — | ✅ DONE |
| P1.6 | Roundtable eval prompt v3.0 | — | ✅ DONE |
| P1.7 | Stale Gemma references purged | — | ✅ DONE |
| P1.8 | S5 model pre-warming | — | ✅ DONE |

---

## ✅ DONE — D2250-D2252 S4 CHAIN + HYBRID S2 (2026-08-10)

| Task | Result |
|------|--------|
| BUG-075 — Cross-domain depth 0% | ✅ FIXED (87.5%) |
| D2249 — S4 classifier swap Phi→GPT-OSS | ✅ DONE |
| T-007b — S2 positive-fidelity gap | ✅ Hybrid DSPy 0.736 (not wired — see P0.1) |
| Golden audit | ✅ 0 quality gaps |
| DSPy validation report | ✅ Hybrid approved |
| Cost model | ✅ T1.1 ~39h (D2365/D2366 corrected the D2362 ~110-140h and D2253 ~21-26h cluster-vs-FB denominator errors) |

---

## ✅ DONE — EARLIER SESSIONS

| Session | Tasks |
|---------|-------|
| D2211 (2026-08-08) | 13 P0 circuit breaker + error propagation fixes |
| D2212 (2026-08-08) | MinHash race condition + SentenceTransformer cache |
| D2195-D2204 (2026-08-05/06) | Zero-vector fallback, LICENSE, config sync, 49→48 col fix, golden expansion 10→25 |
| D2184-D2186 (2026-08-05) | 14 hardcoded values → config, bare except fixes |
| Phase 0-1.5 (2026-07-26/28) | Schema accessor, runner, Stage 3 removal, smoke, parallel, golden set, Matryoshka 512d |

---

## ❌ REJECTED — Will Not Implement

| Proposal | Reason |
|----------|--------|
| Cloud burst (GPT-4o-mini) | C1/C3 violation |
| LangChain dependency | C2 vendor lock-in |
| Microsoft GraphRAG | Heavy, cloud-native |
| LanceDB/DuckDB storage | SQLite adequate (C5) |
| Dagster/Prefect orchestration | PipelineRunner <300 LOC |
| Full Pydantic migration | Schema accessors sufficient |
| Leiden algorithm | Louvain adequate at current scale |
| OpenFActScore | Overengineered |
| Self-RAG reflection token training | C1 cost + R7 temp=0.0 |
| CRAG web search fallback | C3 sovereignty |
| ColBERT late interaction | M1 Max memory |
| Multi-agent swarm | 39-70% coordination tax |
| Neo4j graph database | C3 external service |

---

## 🔗 NEXT EXECUTION ORDER

```
1. ✅ B1-B10 (D2325-D2332) → pre-T1.1 blockers — ALL IMPLEMENTED (9295ce0 + D2343)
2. ✅ B11-B14 (D2337-D2340) → S6 data-loss / fail-closed / run-id / registry — IMPLEMENTED (B14 config rename deferred)
3. ❌ P0.1 (D2276) hybrid gate → REJECTED for T1.1 (BUG-085 A/B net-negative 4.3% rejection) — run traditional-only
4. ⏳ B15 (D2341) schema corrections (TI class, three-axis status, typed edges, feedback→YAML) → DEFERRED P2
5. 🚀 T1.1 → Launch full run (canary first, then full corpus)
6. T1.2 → Yield diagnostic on full run output
7. P1.x → Claim decomposition, golden expansion, enrichment verification (post-T1.1)
8. T2.x → Business PI, atomic evidence, trust state machine
```

## 🧭 HANDOFF POINTER

```
1. Verify OMLX health: curl -s localhost:11435/health
2. Active S5: DeBERTa-only, threshold 0.10 (honest cal D2322: P=0.647/R=0.386/F1=0.484), stage5_verify.py clean
3. Config: verifier=DeBERTa-v3-large, classifier=gpt-oss-20b-MXFP4-Q8, generator=Qwen3-Coder-30B
4. Hybrid gate REJECTED for T1.1 (BUG-085) — run traditional-only: python3 pipeline/runner.py
5. D2298 marks S5 architecture final — no ongoing human adjudication
```

---

## ✅ DONE — D2300-D2307 SENIOR RAG AUDIT (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2300 | Modularity gaps documented (InferenceProvider/EmbeddingProvider/StorageBackend unimplemented) | ✅ LOGGED |
| D2301 | Cold-reload recovery — `cold_reload_delay` 45s (content=None) | ✅ DONE |
| D2302 | DSPy 3 gaps logged (not-wired / stale Stage 3a / random split) | ✅ LOGGED |
| D2303 | CRIBS bottleneck — batch CRIBS selected + wiring fixed | ✅ DONE |
| D2304 | DSPy tier-aware split (GOLD-A→train/B→dev/CHALLENGE→test) + `load_optimized_program()` | ✅ DONE |
| D2305 | Pipeline audit revelation — recall + latency SLA blindspots | ✅ LOGGED |
| D2306 | InferenceProvider + EmbeddingProvider protocol implemented (OMLX + Ollama) | ✅ DONE |
| D2307 | Recall measurement — `pipeline/recall_measure.py` | ✅ DONE |

### ⏳ DEFERRED — POST-T1.1 (from D2300-D2307)

| # | Task | Source |
|---|------|--------|
| GAP-1 | Wire DSPy trained program into stage2_extract.py | D2302 |
| GAP-2 | Remove stale Stage 3a artifacts (prompts/s3a_*.txt) | D2302 |
| SLA | End-to-end latency SLA | D2305 |
| SB | StorageBackend protocol (stage6 SQLite) | D2300 |

---

# 🔴 NEW THIS SESSION — Qwen3.8 + Local-LLM Harness + S4 Speed (2026-08-14)

> **Research (goose):** Qwen3.8-27B availability, local-LLM delegation fix, S4 speed unblock.
> Full findings: `governance/MARKET-RESEARCH-QWEN3.8-HARNESS-2026-08-14.md`.
> **FOR EVALUATION** — none committed yet; all items below are recommendations awaiting decision.

## S4 SPEED UNBLOCK (D2354 follow-up — root cause confirmed)
Root cause: `gpt-oss-20b-MXFP4-Q8` is a reasoning model → emits `reasoning_content` (CoT) on EVERY call
even with `Reasoning: none` (OMLX ignores it). S4 makes 2 GPT-OSS calls/FB: batch CRIBS (~15.3s) + SEQUENTIAL
focused-depth (~10s) that redundantly recomputes a `depth` the batch already returned. Total ~25s/FB.

| # | Item | Evidence | Recommendation | Effort | Status |
|---|------|----------|----------------|--------|--------|
| S4-A | Batch the focused-depth call | A/B (D2354): 8.4s→4.3s/FB (1.9×), accuracy 75%==75% (gate mis-set to A↔B parity, not golden) | Adopt batching; re-gate on golden-parity | 0.5h | 🟡 FOR EVAL |
| S4-B | FrugalGPT: route depth → gemma-4-E4B | gemma depth correct @ 5s, zero CoT, R5-clean 3rd family | Enable `depth_frugal_enabled` after benchmark ≥90% | 1h | 🟡 FOR EVAL |
| S4-C | Distill gpt-oss → 3-4B non-reasoning | Hinton distillation (post-T1.1) | defer | 4h | ⏳ P2 |

## LOCAL-LLM HARNESS (FOR EVALUATION)
| # | Item | Recommendation |
|---|------|----------------|
| H1 | Qwen3.8-27B-MLX-4bit (16.08 GB, 262K ctx, VLM, agentic) | Adopt for LONG_CONTEXT / AGENT_ORCHESTRATOR (R5-safe: verifier stays gpt-oss/gemma/DeBERTa). Download in progress. |
| H2 | goose `active_provider: custom_deepseek` | Switch → `maxwell_omlx` to cut DeepSeek cost (C1). Planner already local. |
| H3 | BUG-063 delegation | `filesystem` MCP does NOT fix it (subagent = Deno sandbox). Use `omlx_delegate.py` in-process. |
| H4 | MCP exposure (C25) | `delegate_local` tool ADDED to maxwell_mcp_server.py (this session). |
| H5 | Coding TUI | Aider (`--openai-api-base` → OMLX :11435) over Zed for autonomous local-model refactors. |

## PLUGINS (goose) — CORRECTED 2026-08-15 (was FOR EVALUATION)
> **Prior table contradicted this session's findings.** Re-verified against the live
> `Extensionmanager.searchAvailableExtensions()` registry.
| Plugin | Current | Recommendation |
|--------|---------|----------------|
| orchestrator | ⛔ phantom | **DO NOT ENABLE** — not in the real registry; stale `config.yaml` entry only (refuted 2026-08-14) |
| memory / chatrecall / summarize | disabled | Optional — revisit after H2 (provider switch); not required for core pipeline |
| filesystem | disabled | Optional — redundant with `developer` (shell); does NOT fix delegate subagents (BUG-063) |
| fetch (`mcp-server-fetch`) | disabled | **Enable** — web research; use this, NOT `puppeteer` (Chromium dep, "failed to add") |
| puppeteer | ⛔ failed | **DO NOT USE** — `npx @modelcontextprotocol/server-puppeteer` fails to add; `fetch` substitutes |
| tom / gitmcp-mcp / nvidia | enabled | **Disable** — `tom` injects unused `GOOSE_MOIM_*` env; `gitmcp-mcp` redundant w/ developer; `nvidia`=cloud (violates C1) |


---

# 🔴 UPDATE — S4 Empirical Validation + OMLX context (2026-08-14 18:12)

> Ran `tools/benchmark_s4_depth_frugal.py` (production path). Full: `governance/S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md` + `s4_depth_frugal_benchmark.json`.

| # | Item | Empirical result | Verdict |
|---|------|------------------|---------|
| S4-A | Batch focused-depth | 1.9x (8.4->4.3s), accuracy 75%==75% (D2354 A/B) | ✅ ADOPT |
| S4-B | FrugalGPT gemma depth | gemma 62.5% acc / 62.5% parity (gate 90%) | ❌ REJECT — do NOT enable |
| S4-B' | gpt-oss depth baseline | 75% acc (NOT the 87.5% governance claim) | ⚠️ depth accuracy weak |
| S4-C | Distill gpt-oss -> 3-4B | not yet run | ⏳ only real path to big speedup |

## OMLX context window (verified via `/v1/models`)
| Model | max_model_len |
|---|---|
| Qwen3-Coder-30B-A3B (generator) | 32,768 (32K) — native 256K, OMLX-capped |
| gpt-oss-20b (classifier) | 131,072 (128K) |
| Phi-4-mini / gemma-4-E4B / Qwen2.5-3B | 32,768 (32K) |
| Qwen3.5-9B / gemma-4-31B | 262,144 (256K) |


---

# 🔴 NEW — CROSS-LLM AUDIT 2026-08-15 (gemini003 / claude0013 / chatgpt0013)

> **Independent code re-verification of 3 external LLM S4/context verdicts.** Full audit:
> `governance/CROSS-LLM-AUDIT-VERDICT-2026-08-15.md`. Headline: Claude0013 & ChatGPT0013
> high-signal & materially accurate; Gemini003 low-signal (1 real catch + 3 fabrications).
> Five drift/contamination issues surfaced that **all three LLMs missed**.

| # | Severity | Task (verified) | Effort | Status |
|---|----------|-----------------|--------|--------|
| X1 | 🔴 | **D2363 golden-relabel circularity** — 3-model vote included gpt-oss (the classifier graded); relabel direction (domain→cross-domain) = gpt-oss's known bias. Verify vote independence (R5). | 1h | ✅ RESOLVED (D2365) — NOT contaminated; cross-model consensus; gpt-oss tie-break in only 3/13 (paired w/ qwen), never sole driver. |
| X2 | 🟠 | **Depth accuracy 72% (n=50), not 75%/90%** — incumbent gpt-oss depth path has NO gate; quality gap > speed gap. Root-cause before speed work. | 2h | ✅ RESOLVED (D2365/D2366) — 72% was pre-relabel-gold artifact; fresh n=45 post-relabel run = **~84% (38/45)**, systematic gpt-oss over-assignment of `cross-domain`. No quality *crisis*, but NOT 98%. |
| X3 | 🟠 | **MTR PLUGINS drift** — `orchestrator` phantom, `puppeteer` fails; table now corrected (§above). | 0.25h | ✅ DONE |
| X4 | 🟠 | **S4-B refutation cold-load-skewed** — gemma first-call 65.6s unisolated → speed half unmeasured. Re-run w/ warmup. | 0.5h | ✅ DONE (D2366) — gemma warmed (2.0s, no cold skew); still 62.5% acc, 4.5× faster → FAILS 90% gate. gemma-4-E4B was NOT actually deleted (weights+registration intact; D2297 removed only the goose-provider entry). |
| X5 | 🟠 | **142h denominator** — 12,964 = clusters, not FBs (35,239 singletons; T1.1 principle-only). Compute real FB count. | 0.5h | ✅ RESOLVED (D2365) — 2,634 convergent × 1.35 yield ≈ 3,556 FBs → ~39h, not 142h. |
| X6 | 🟠 | **S4-A n=8, 2 decision flips** — speedup 1.9× verified, semantic equivalence NOT. Re-verify n≥30. | 1h | ✅ DONE (D2366) — n=45: batch 66.7% vs sequential 84.4%, parity 60%, 1.7×. Batching DECISIVELY rejected (degrades accuracy 17.7pt). |
| X7 | 🟡 | **C12 hardcoded sets** — `business/design/system/academic_signals` + `temporal_scope` + `universal_signals` → YAML (Gemini catch). | 1h | ✅ DONE (D2364) — extracted to config; verified + local-LLM review PASS. |
| X8 | 🟡 | **`thinking_budget` sweep** on merged call (null/256/384/512) — config wired, unmeasured. | 0.5h | ✅ DONE (D2366) — **budget=256 → 1.8× (40s→22s); budget=128 → 1.9× (17.6s), both valid JSON.** Sole viable speedup; gated on merged-call accuracy check before adopting. |
| X9 | 🟡 | **Concurrency benchmark** (1/2/3 workers) — zero parallelism verified in `stage4_merge.py`; OMLX may serialize. | 1h | ✅ DONE (D2366) — 43.3s/41.3s/42.2s (flat) → **OMLX serializes; concurrency gives no speedup.** ThreadPool would add risk for zero benefit. |
| X10 | 🟡 | **Remove `depth` from merged call** — gated parity test + fix `:1257-1258` fallback coupling. | 0.5h | 🟠 PARTIAL (D2365) — fallback coupling made explicit in code; `depth` removal itself gated (attention-redistribution unmeasured). |

> **Video (Prime Agent):** adopt skills-as-code + state-survives-compaction patterns for the
> post-T1.1 skill orchestrator; REJECT RLM training (30.2% official vs 95.5% self-reported).
> See `governance/CROSS-LLM-AUDIT-VERDICT-2026-08-15.md` §3.

> **🔁 RE-ADJUDICATED 2026-08-15 (this session):** X1/X2/X5 resolved in Maxwell's favour (D2365);
> X7 implemented (D2364). **Headline correction: depth is ~84% (n=45) against post-relabel gold
> (not 72%, NOR the earlier 98% over-correction), and T1.1 S4 is ~39h (not 142h).** X4/X6/X8/X9
> done (D2366, only `thinking_budget=256` survives — gated + BUG-132); X10 partially done (fallback
> coupling made explicit, `depth` removal gated). Details: `DECISION-LOG.md` D2364-D2367,
> `governance/buglog.md` top.
