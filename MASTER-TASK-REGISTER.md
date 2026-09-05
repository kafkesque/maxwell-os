# Maxwell OS v3.0 — MASTER TASK REGISTER (tiered)

> **Updated:** 2026-09-04 | **Archive (full history):** `archive/governance_pre_tiered_2026-09-03/MASTER-TASK-REGISTER.md`
> **Companion:** `governance/aggregated_remaining_tasks.md` (archived copy in same folder)
>
> **Convention (standing rule):** unresolved/undone tasks at the TOP (most critical first, MUST→SHOULD→WORTH); resolved/done at the BOTTOM.

---

## 🔴 MUST — open (strategic-consequential order)

**CLEARED 2026-09-04** — all 9 prior MUST items resolved this session. No open MUST.

---

## 🟠 SHOULD — open

1. **CLASSIFIER** — TRAINING SCRIPT WRITTEN (D2571: `scripts/train_discipline_classifier.py`, deberta-v3-base + LoRA + 2 heads softmax-61 discipline + sigmoid-43 domain + abstain→emerging, fail-loud <100 golden). CORRECTED PLAN 2026-09-05: depth is NOT a classifier target — drop depth stratification. Mine ~750–1000 CONVERGENT FBs stratified by discipline (min 10/max 30, all 61 covered) + domain coverage. Use `is_convergent` as a soft quality signal, backfill single-source only if a discipline has <10 convergent. NEXT: (a) mine the stratified convergent set; (b) fix label-map padding fragility; (c) train. Target macro-F1 ≥ 0.75.
2. **DEPTH-ACCURACY AUDIT** — investigate whether S4 depth classification (universal/cross-domain/domain/specialized) is ACCURATE or hallucinated. Concern: depth distribution domain 83% / cross-domain 9% / specialized 7% / universal 1% — possible residual collapse-to-domain bias (D2451/D2482 history). Method: cross-family re-label audit of a stratified sample (esp. the 81 universal + 713 cross-domain FBs); compare gpt-oss depth labels vs Qwen3.8 + gemma independent depth judgments; measure agreement and flag systematic under/over-labeling. NOT a classifier blocker (depth is not a classifier head) but needed before trusting depth as a retrieval/ranking signal.
3. **D2547** — GATE SCRIPT WRITTEN (D2571: `scripts/apply_cost_weighted_thresholds.py`, cost = n/median). REMAINING: (a) domain-axis frequencies (script queries `discipline` only → domain labels get n=0); (b) cost-model calibration (policy decision); (c) re-derive per-label rates with definition-bearing hypotheses (D2571 finding).
4. **D2548** — grammar-constrained decoding pilot on S4 enums. Outlines/XGrammar NOT installed; gate added (`stage4.grammar_decoding_enabled=false`, D2556). BLOCKED on dependency.
5. **T-OWL** — OWL/SKOS axiom spec for 105 canonicals (D2541).
6. **D2399 (BUG-150 tail)** — FULLY ADJUDICATED 2026-09-05 (D2572+D2573+D2574). 292 gaps = 42 kind-leaks + 250 true-gaps. APPLIED: 6 discipline aliases (12 FBs, D2572); Marketing kind-swap (5 FBs, D2572); **Ecology promoted** + `computer networking` displaced (5+4 FBs, D2573, closed-loop 61→61); **33 kind-leaks cleaned** (D2574). REMAINING: **241 true-gaps** (long-tail open-world labels) — leave as `emerging` unless a label accumulates ≥5 stable FBs for a future closed-loop promotion.
7. **BUG-151** — taxonomy structural overlap (177 raw-alias cross-axis; kind-safe-guarded).
8. **BUG-148** — S2 `route` field stale (`route="FB"` on all 2,878).
9. **BUG-182** — 48 singleton empty-shells deterministic.
10. **BUG-170** — non-principle types (PT/PI/TI/GE) not classified/enriched.
11. **BUG-159** — prompt-injection contamination (cluster_11649, 0.007%).
12. **GOV-GOLDEN** — archive 8/9 versioned `MASTER-ROUNDTABLE-EVAL-PROMPT-*` + 2 dead golden files.
13. **D2462** — unify single-source + singleton S2 into one extractor.
14. **D2345** — single-source non-type second pass.
15. **BUG-168** — `dspy_trainer.py` built-not-wired: wire OR archive (P2 dead code).
16. **BUG-195-code** — S4 cross-cluster dedup + S6 duplicate-fb_id fail-loud guard (post-hoc done; CODE fix for future batches).
17. **C12-ROUTE** — extract `route.py` hardcoded 10%/5% promotion thresholds → config (C12).
18. **P1-6** — config-read fallbacks promote from log to raise (C16 observability).
19. **FINGERPRINT** — S5 input fingerprint load/write fail-closed (P1-1/P1-2).
20. **DEEPSEEK-PROVIDER** — goose `active_provider=custom_deepseek` (deepseek-v4-pro) is LIVE+AUTHENTICATED (Keychain internet-password `https://api.deepseek.com/v1`; live `goose serve → api.deepseek.com:443` connection). NOT dead (D2560 CORRECTED 2026-09-04). Real issue = remote CLOUD API → C1 ($0) + C3 (sovereignty) violation BY DESIGN. Switch `active_provider` → `maxwell_omlx` in `~/.config/goose/config.yaml` (user decision — affects the goose runtime itself).

---

21. **D2440** — S5 verifier calibration experiment (AlignScore 355M + MiniCheck EMNLP-2024 vs DeBERTa-v3-large via `pipeline/calibrate.py` + `nli_calibrate.py`). BLOCKED: `evals/nli_golden.jsonl` not committed → threshold non-reproducible. Adopt only if F1 materially > 0.484 AND fail-closed (D2093) preserved.

## 🟡 WORTH — open (later / after measurement)

22. **T-S1** — S1 contextual embeddings adopt-vs-gate decision.
23. **T-S3** — S3 HyDE A/B run.
24. **D2399** — domain promote/demote (frozen — reopen post-reclass).
25. **D2164/D2165/D2166** — sparse architectural planning (see DECISION-LOG reference links).
26. **D2009…D2084** — 15 legacy DEFERRED infra/CLS items (see DECISION-LOG reference links).
27. **BUG-160** — systematic evidence-passage topical-relevance pass (log-only today).
28. **BUG-169** — verify TI `parameters` at rerun (technique-type vs API TI ontology nuance).
29. **TEST-CLEANUP** — gut/rename `tests/test_stage4_d2138.py` + `test_stage4_exhaustive.py` (0 `test_*` fns).
30. **T-STS** — tautological-mechanism STS (def↔mech cosine; weak signal measured).
31. **T-015/D2292** — golden depth expansion ≥5 universal + ≥5 specialized (BUG-083/084).
32. **BUG-081** — `evals/golden_cases.json` v2 format migration.
33. **BUG-073** — CONV-035/037 false convergence (D2232).
34. **GAP-2** — remove stale Stage 3a artifacts (`prompts/s3a_*.txt`).
35. **SLA** — end-to-end latency SLA (D2305).
36. **B15/D2341** — schema corrections: TI class, three-axis `status`, typed edges, feedback→YAML.
37. **T2.x** — Business PI, atomic evidence, trust state machine.

---

## ✅ DONE — bottom (recent, resolved this/prior sessions)

- **DEF-BEARING-NLI control (D2571)** — `pipeline/nli_definition_control.py` (500-FB sample): definition-bearing hypothesis is a LABEL-SPECIFIC confound fix, not uniform (anthropology 0.004→0.44, evolutionary biology 0.024→0.41, cognitive science 0.01→0.31; overall mean entail flat 0.27→0.24, pass rate up 0.37→0.42). Per-label rates must be re-derived with definitions, not blanket-switched ✅ (2026-09-05)
- **Cleanlab Confident Learning (D2571)** — `scripts/cleanlab_label_audit.py` (TF-IDF + 5-fold CV-LR): 3424/7026 flagged (48.7%; top behavioral economics 150, philosophy 133). Third instrument wired. CAVEAT: TF-IDF weak — bge-m3 embeddings upgrade = follow-up ✅ (2026-09-05)
- **P1 ontology definition layer (D2570)** — added `definition`+`exclude` to all 104 canonicals (43 domains + 61 disciplines) in `config/taxonomy_v5.yaml`; authored by Qwen3.8-27B (single-shot, temp 0), cross-family verified by gemma-4-E4B (0/25 flagged wrong), applied additively via ruamel round-trip (canonical/group/raw/meta byte-identical; 199/199 tests green). Unblocks the definition-bearing NLI hypothesis control (anomaly C). ✅ (2026-09-05)
- **C12-CHUNK (D2570)** — `pipeline/reclassify_merged_axis.py` `CHUNK_SIZE_DEFAULT=200` hardcode → config `stage4.reclassify_chunk_size=200` + `CONFIG_TO_CODE` registry entry; `config_audit.py --check-unchecked --strict` now clean ✅ (2026-09-05)
- **C16 review_aliases (D2570)** — `scripts/review_aliases.py` `_load_checkpoint` silent `except (json.JSONDecodeError, KeyError, ValueError)` → logs to stderr + continue (matches `nli_label_audit.py` pattern) ✅ (2026-09-05)
- **per_label round-trip test (D2570)** — `tests/test_per_label_threshold_contract.py` (5 tests) guards the 96-entry `per_label` block: canonical keys only, numeric [0,1], 43/43 domains present, YAML round-trip type-safe ✅ (2026-09-05)
- **Forensic audit + integrity (D2570)** — integrity 18/18, config-audit clean, decision-sync 545→546, DB integrity ok / 0 FK / 0 non-canonical / 0 null R14; 199/199 tests green ✅ (2026-09-05)
- **D2569 baseline committed+pushed** — `2c866c3` (14 files + corrected handoff v2) ✅ (2026-09-05)
- **BUG-223 logged (D2570)** — 54 `emerging` FBs store `discipline_raw='[]'` literal-array instead of `''`/NULL (minor hygiene; empty-test must handle `'[]'`) ✅ (2026-09-05)
- **Governance drift sync (D2569)** — removed D2544/D2545 double-listing from DECISION-LOG OPEN section; re-surfaced D2440 into MTR SHOULD #20; flipped D2454/D2483 ACTIVE→RESOLVED ✅ (2026-09-05)
- **BUG-215 residual fix (D2569)** — `scripts/fix_bug215_residual.py --apply`: 66 FBs (discipline≠emerging + empty raw + stale `emerging_real`) → **24 verified alias restore** (Information Systems/Health Informatics → information science) + **42 reverted to emerging** (raw label doesn't resolve to the assigned discipline — `Marketing`→finance, `music education`→psychology, `Applied Mathematics`→theoretical physics, plus an information-science catch-all over-assignment). NET discipline=emerging 927→969; 0 residual; integrity ok, 0 FK ✅ (2026-09-05)
- **P0 #2 NLI full population (D2569)** — `pipeline/nli_label_audit.py` now persists `results` (23,364 full-population records) alongside the flagged contradicts/weak lists → downstream stats are full-population means, not flag-rate proxies ✅ (2026-09-05)
- **P0 #1 contradict/weak split (D2569)** — `scripts/build_mislabel_triage.py` outputs `nli_total`/`nli_contradict`/`nli_weak` (no conflated union); `scripts/populate_semantic_error_thresholds.py` uses `nli_contradict` + made idempotent → **project management 0.9425→0.3914** (true contradiction 245/626, not the 590/626 flag union) ✅ (2026-09-05)

- **Cascade deregistration (D2568)** — `scripts/cascade_deregister_domains.py --apply`: 615 FB domain deregistrations across the 3 SYSTEMATIC catch-all domains (project management 257 / business operations 202 / legal & public policy 156) from the k-NN∩T-NLI flagged set; 75 single-domain FBs → honest "emerging"; counts 879/1756/806 → 622/1554/650. Fixed a double-flag overwrite bug (24 FBs) by unioning all flagged catch-all domains per FB. C13 backup + integrity gate + atomic + recount ✅ (2026-09-04)
- **Alias review + correction (D2568)** — `scripts/review_aliases.py` (Qwen3.8-27B re-reviewed 927 single-value aliases → 76 flags) + DeepSeek-v4-pro cross-family verify → `scripts/apply_alias_corrections.py --apply`: **66 corrections** (49 domain + 17 discipline), 9 kept, 1 no-op. Protected D2567 corpus-dependent fixes (`video production`→motion design, `statistics & data science`→data visualization) ✅ (2026-09-04)
- **BUG-150 promotion (D2568)** — (a) `bug197_kind_swap.py` re-run: 1,235 FBs (56 discipline + 140 domain recovered); (b) `scripts/resolve_emerging_promotion.py`: 54 FBs deterministic (suffix-strip + compound-split, curated exclusion of `graph theory`→data-viz false-positives); (c) LLM promotion 24 FBs (`Information Systems` + `Health Informatics` → `information science` discipline, Qwen3.8×DeepSeek agreement). NET discipline=emerging **1,010→927** (−83), domains∋emerging 716→772 ✅ (2026-09-04)
- **Re-audit (D2568)** — re-ran k-NN + T-NLI after mass reclassification: k-NN mean agreement **41.2%→40.7%** (FLAT — the metric tracks topical diversity, not label accuracy; audited pairs 12,667→14,334 as more FBs gained canonicals); T-NLI contradict rate **21.5%→19.9%** (−1.6pp) + domain mean entail **0.248→0.265** (improved). `build_mislabel_triage.py` → 526 calibration rows + 2,142 triage FBs ✅ (2026-09-04)
- **Per-label thresholds (D2568)** — `scripts/populate_semantic_error_thresholds.py --apply`: 96 per-label NLI-contradiction rates → `taxonomy.semantic_error_rate_max.per_label` (flag-rate proxy; cost-weighting + gate consumer pending) ✅ (2026-09-04)
- **D2544 k-NN audit** — full 7,995-FB run executed (k=10): mean neighbor-label agreement **41.2%**, 6,211 low-agreement pairings (49.03%) → `governance/knn_label_disagreement.json`. First fixed a latent domain-comparison bug (`.split("|")[0]` on JSON column) → JSON-parse + set-intersection (D2557) ✅ (2026-09-04)
- **T-NLI audit** — `pipeline/nli_label_audit.py` created (D2542 target, was never written) + Qwen3.8-27B-reviewed (APPROVE); full run COMPLETE: 20,929 pairings, mean entail 0.332/0.248, **4,497 contradict-label** (21.5%), 8,978 weak (D2558) ✅ (2026-09-04)
- **C16 search_fts** — silent `sqlite3.OperationalError`→LIKE fallback now logs loudly (D2559) ✅ (2026-09-04)
- **DeepSeek API verify** — `custom_deepseek` is LIVE+auth (Keychain `https://api.deepseek.com/v1`; live conn to api.deepseek.com:443), NOT dead; remote-cloud → C1/C3 violation → recommend `maxwell_omlx` (D2560, CORRECTED 2026-09-04) ✅ (2026-09-04)
- **D2547 calibration** — `scripts/build_mislabel_triage.py` → `governance/d2547_calibration.json` (440 per-label entail/agreement stats) (D2561) ✅ (2026-09-04)
- **Mislabel triage queue** — 1,989 FBs flagged by BOTH k-NN (6,211) + T-NLI (4,497), ranked by contra−entail gap → `governance/mislabel_triage.json/.md` (D2561) ✅ (2026-09-04)
- **Forensic audit + fixes** — Qwen3.8-27B + DeepSeek cross-verify: 6 real C6/C12/C16 findings FIXED (knn safe_write+config constants, nli log+fsync, retrieve stopwords→config), 2 false-positives rejected (D2562) ✅ (2026-09-04)
- **Relabel plan built** — human-review marks (64 FBs / 8 labels) → `governance/relabel_plan.json/.md` (PLAN-ONLY): 3 systematic (project management/business operations/legal & public policy), 5 retarget + 40 deregister + 14 keep + 5 unreviewed (D2563) ✅ (2026-09-04)
- **Enrichment plan** — cross-disciplinary retrievability: 11 FBs classified (1 enrich + 4 retarget + 6 deregister); backlog 1,926 immediate-enrich + 3,177 Track-B-emerging → `governance/enrichment_plan.md` (D2564) ✅ (2026-09-04)
- **Phase 1 relabel applied** — 8 human-review FBs (1 enrich + 4 retarget + 3 deregister) via `scripts/apply_relabel_plan.py` (C13 backup + atomic) (D2565) ✅ (2026-09-04)
- **Phase 2a enrichment applied** — 75 safe cross-domain additions via `scripts/apply_enrichment.py` (non-catch-all); mapping gap found: 2,139 unmapped raw labels → ~1,850 FBs still blocked (D2565) ✅ (2026-09-04)
- **Alias extension (D2566)** — `scripts/extend_alias_index.py`: deterministic (self/fold/compound/suffix) + LLM bulk-map (Qwen3.8 generator × gpt-oss verifier, cross-family R5, agreement-only) → **618 domain + 151 discipline aliases** added to `config/alias_map.yaml` (add-only; 201 existing preserved). Wired alias_map.yaml into `pipeline/schemas.py` synonym index (step 3) ✅ (2026-09-04)
- **Phase 2b enrichment re-run (D2566)** — `scripts/apply_enrichment.py` rewritten (full domain index: taxonomy + synonym_map SYNONYMS-only + alias_map + canonical-self + compound split; keywords excluded) → **727 FBs enriched** (vs 75 in Phase 2a) ✅ (2026-09-04)
- **Deterministic emerging resolution (D2566)** — `scripts/resolve_emerging_deterministic.py`: **354 emerging FBs → canonical discipline** (no LLM, kind-safe) ✅ (2026-09-04)
- **Track B slim re-classification (D2567)** — `pipeline/reclassify_merged_axis.py --slim --apply`: 1,488 discipline=emerging FBs → **478 resolved + 981 raw-corrected** (~1.4s/FB); harvested `temp/trackb_slim.jsonl`; checkpoints re-synced ✅ (2026-09-04)
- **Domain-axis emerging resolution (D2567)** — `scripts/resolve_domains_emerging.py --apply`: **846 FBs with domains ∋ emerging → real domains** ✅ (2026-09-04)
- **Alias quality correction (D2567)** — 7 wrong LLM aliases fixed (`video analytics`→data viz, `scientific research`→science & research, …) + 1 reverted; `scripts/correct_wrong_enrichments.py` fixed 19 inherited wrong domains. Net emerging: discipline 1,842→1,010, domains∋emerging 1,562→716 ✅ (2026-09-04)
- **BUG-104** — sqlite-vec unblocked: Homebrew Python (`/opt/homebrew/bin/python3`) → vector leg recall@k **1.000**, hybrid 0.900 (D2556) ✅ (2026-09-04)
- **D2547 config** — `taxonomy.semantic_error_rate_max` (default 0.05, per_axis, per_label) added (D2556) ✅ (2026-09-04)
- **D2548 gate** — `stage4.grammar_decoding_enabled=false` added; Outlines/XGrammar not installed (D2556) ✅ (2026-09-04)
- **Code-review benchmark** — all 4 local models 5/5, 0 hallucination (gemma not inferior; D2556) ✅ (2026-09-04)
- **Qwen3.8 forensic audit** — verdict CONCERNS, 8 legit C12/C20 findings fixed (D2556) ✅ (2026-09-04)
- **BUG-221** — FTS5 OR/prefix tokenization fix (D2554): recall@k **0.000→0.667** verified ✅ (2026-09-04)
- **D2546** — SHACL formalization of 104 canonicals → `config/taxonomy_shacl.ttl` (D2555) ✅ (2026-09-04)
- **MEASURE-DEBERTA follow-up** — S5_NLI char caps 256→1500/500 (D2554); re-measured 0% truncation ✅ (2026-09-04)
- **D2544 script** — k-NN audit script written + smoke-tested (D2555) ✅ (2026-09-04)
- **MEASURE-DEBERTA** — DeBERTa 512-token exposure measured: 0% exceed window (max 498 tokens) ✅ (2026-09-04)
- **GOV-SKILL** — `agent/skills/maxwell-os-SKILL.md` v3.0 regenerated (6/6 dead paths fixed) ✅ (2026-09-04)
- **GOV-TURBO** — `turbovec_backend.py` archived; `mlx_provider.py` KEPT + flagged UNUSED ✅ (2026-09-04)
- **GOV-SQLITE** — `storage/base.py` docstring fixed (false "Default: sqlite_backend.py" removed) ✅ (2026-09-04)
- **GOV-CI** — `.pre-commit-config.yaml` + `scripts/pre_commit_gate.py` (C11+C12) added ✅ (2026-09-04)
- **GOV-VERSION** — `classification_version` v5.0.1→v5.5; filename = major-version marker ✅ (2026-09-04)
- **GOV-SENTINEL** — `sk-maxwell-local` consolidated 6 code copies → `OMLX_API_KEY` ✅ (2026-09-04)
- **GOV-HEADINGS** — DECISION-LOG heading convention codified ✅ (2026-09-04)
- **BUG-098** — `psutil>=6.0` confirmed declared in `requirements.txt` ✅ (2026-09-04)
- **BUG-220** — `delegate()` Qwen breakage standardized on one-shot OMLX curl (D2543/D2549) ✅ (2026-09-04)
- **BUG-220-MCP** — MCP `delegate_local` hardened (model allowlist + caps + path-containment) ✅ (2026-09-04)
- **F-03** — MCP `depth` enum fixed → canonical 4 values ✅ (2026-09-04)
- **MEASURE-DIM** — bge-m3 512-d contract VERIFIED ✅ (2026-09-04)
- **BUG-215** — 1,097 empty `discipline_raw` repaired (Track B + T-311 + kind-swap) ✅ (2026-09-04)
- **T-311** — 311-row deterministic repair ✅ (2026-09-04)
- **T-TRACKB** — Track B reclassification complete: 1,172/1,172 ✅ (2026-09-03)
- **kind-swap re-run** — BUG-197 post-TrackB: 544 FBs ✅ (2026-09-04)
- **FTS rebuild** — `fbs_fts` rebuilt (7,995 rows) ✅ (2026-09-04)
- **BUG-219** — integrity-check #4 FP fixed ✅
- **BUG-216** — 28 FBs `domains_raw` backfilled ✅
- **BUG-217** — `taxonomy_version` unified v5.1→v5.5 ✅
- **BUG-218** — 9 sidecar empty-shells ACCEPTED ✅
- **D2545** — C12 config-first de-hardcoding + CONSTITUTION taxonomy ✅
- **D2399 human review** — both candidates REJECTED + promotions frozen.
- **S2 rerank enable** — ENABLED (`rerank.enabled: true`).
- **S3 HyDE harness** — implemented (`--hyde`).
- **BUG-198** — 6 singleton principles re-injected.
- **BUG-197** — deterministic kind-swap (3,694 FBs; 0 residual axis leaks).
- **Checkpoint drift** — S4 checkpoint re-synced (7,873, 0 drift).
- **Forensic audit** — clean (0 null/empty/leak/invalid).

> Full task history: `archive/governance_pre_tiered_2026-09-03/MASTER-TASK-REGISTER.md` + `…/aggregated_remaining_tasks.md`.
