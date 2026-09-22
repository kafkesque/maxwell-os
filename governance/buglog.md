# Maxwell OS v3.0 — BUG LOG (tiered)

> **Updated:** 2026-09-20 | **Archive (full history):** `archive/governance_pre_tiered_2026-09-03/buglog.md`
>
> **Convention (standing rule):** OPEN bugs at the TOP (most critical first, MUST→SHOULD→WORTH); CLOSED/RESOLVED at the BOTTOM. Protocol: `governance/buglog_protocol.md`.

---

## 🔴 OPEN — MUST (data integrity / correctness / safety)

| Bug | Date | Issue |
|---|---|---|
| BUG-267 | 2026-09-17 | **The `min_human_share` floor metric is a substring classifier, and "human" provenance is semantically ambiguous — so the floors are measured against an UNKNOWN denominator.** `scripts/audit_eval_integrity.py::_tier()` returns HUMAN when the source string contains `human` OR `locked`, and checks that BEFORE `frontier`. Therefore `p5:human-frontier69` (48 cells across the anchor, incl. 7 content_type + 16 domains) is counted as a HUMAN label although its own name says *frontier*. Separately, the operator confirms that some labels recorded as `p5:human-*` were produced by *reviewing a frontier model's suggestion* (kimi / deepseek / claude), not by independent blind human adjudication — i.e. the source string cannot distinguish **human-decided** from **human-ratified-a-model-output**. CONSEQUENCE: the published human shares (content_type 0.116, discipline 0.347, depth 0.526, domains 0.920) are UPPER BOUNDS, and the anchoring bias of see-then-confirm makes the true figure plausibly lower still. Blast radius: the floor gate `AXB.axis_human_share` and the priority decision that rests on it. FIX: (a) make `_tier()` an exact-match allow-list read from config (no substring tests); (b) split provenance into `human-blind` vs `human-ratified-model` and count only the former as HUMAN; (c) re-measure the floors; (d) all FUTURE human adjudication must be **blind** — the model's proposed label is hidden until the human verdict is recorded. See F-16. | |
| BUG-243 | 2026-09-13 | **DeepSeek-v4-pro / v4-flash return empty `content` on open-ended adjudication prompts (reasoning-passthrough bug — DELEGATE-001 family).** During the S2/S4/S5 forensic audit adjudication, DeepSeek-v4-pro repeatedly returned `finish_reason=stop` with `content_len=0` and only `reasoning_content` (31,176 chars) on the 6-proposition verification prompt; v4-flash returned `finish_reason=length` with empty content. A tiny probe (`Reply with exactly: OK`) works and returns `OK`, proving the failure is tied to long open-ended prompts (the reasoning model emits CoT into `reasoning_content` and never finalizes `content`), not auth. Balance dropped $9.44→$9.34 across the failed attempts. **MITIGATION:** DeepSeek is UNUSABLE for open-ended adjudication/fact-finding; use the local Qwen3.8-27B (OMLX) for reliable-pair rulings and deterministic repo checks as gold standard. The tight-JSON joint-vote prompt (`response_format: json_object` + short answer) still works (D2612/D2616 vote completed with 0 voter errors). | |
| BUG-241 | 2026-09-11 | **"Golden" set is unverified silver — no ground truth for any semantic axis.** All 1,027 examples in `stage4_golden_mined.yaml` carry rationale "gpt-oss teacher labels (discipline/domains/depth). Silver-standard — NOT hand-reviewed" (provenance: gpt-oss 1027 / DeepSeek 0 / human 0). The 4-axis (content_type+depth+domain+discipline) human/DeepSeek-verified core is only **69 examples (frontier69) = 6.7%**. Every prior classifier/weak-supervision eval (0.18–0.29 macro-F1) is therefore silver-auditing-silver — the measured "data limitation" is a verified-label limitation, not model-selection. Fix = D2613 Phase 0: freeze a human+DeepSeek-verified core (69→~150, stratified) as the sole eval target before any further classification; demote the 1,027 to a silver candidate pool. | **CLOSED D2617 (2026-09-13):** `scripts/build_verified_core.py` froze `governance/verified_core.jsonl` = 443 unique rows (149-core + 298-sample; 4 fb_id overlap) as the sole eval target — R14-stamped, `verification_status` human-verified 28 / joint-vote-verified 121 / pending-human 294. The 1,027 `stage4_golden_mined.yaml` is demoted to a silver candidate pool (BUG-241 retired at the DATA level). Remaining honest gap: 294 pending-human rows + domain/discipline have never been DeepSeek+Qwen-voted (only 209/1,027 non-silver). |

## 🟠 OPEN — SHOULD

| Bug | Date | Issue |
|---|---|---|
| BUG-242 | 2026-09-11 | **frontier69_v2 + extension80 audit outputs carry 2 data-quality defects.** (1) The `*_verdict` fields (depth/discipline/domains) are LLM SELF-REPORTS, not computed comparisons — they claim `override` even when the audit value equals silver (e.g. `S4-GOLD-MINED-00005` domains identical yet `domains_verdict=override`), so the cited "57.5% domain-override" and "80 flagged" figures are inflated. (2) Non-principle content_type rows (noise_drop/tool_instruction/process_template/process_instance/growth_edge) carry a spurious 4-way depth label, violating D2612 (depth only for principle). FIX (applied in `scripts/build_phase0_adjudication_form.py`): agreement recomputed deterministically (`differs` flag) + depth marked N/A for non-principle. REMAINS: recompute the override figures from the audit values (deterministic), and re-run the audit to null depth on non-principle if the raw artifacts are kept. |
| BUG-228 | 2026-09-08 | **Dead/aspirational schema fields — 0 code references.** `parent_pt_id` (process_instance's tether to a template), `promoted_to_type`/`promoted_to_id`/`parent_fb_ids` (growth_edge promotion), MCP `annotations` (`readOnlyHint`/`destructiveHint`/`idempotentHint`), `consulted_fbs`/`template_source` — all declared in `content_types.yaml`, all 0 refs in `pipeline/`+`scripts/`. Consequence: `process_instance` is indistinguishable from an unlinked anecdote; `growth_edge` is a dead-end bucket with a staging-area description; MCP-promotion aspiration is unbacked. False affordances for future retrieval code. Fix = prune or ship; backfill `parent_pt_id` when a PT exists (§1.3.2 of the adjudication doc). |
| BUG-231 | 2026-09-08 | **Convergent extraction path is principle-only BY DESIGN — refines the "vacuous 100%-principle" root cause.** `stage2_extract.py:build_convergent_prompt` emits "Extract the convergent principle(s)" + `route: FB|NULL` + a principle-only body schema (no `steps`/`trigger`/`done_condition`), so the convergent path CANNOT emit non-principle — and that is correct architecture (multi-source synthesis → Foundation Blocks). The convergent SYSTEM_PROMPT item 9 (listing all 5 roles) was therefore vestigial and contradicted its own user prompt. Refined root cause of 7,995/7,995 `principle`: (1) convergent = principle-only by design; (2) single-source path IS role-balanced (3/2/7/1/1 golden) but UNDER-detects non-principle (~15% per 818-row triage) because its prompt had only vague role definitions, not the D2587 Q1/Q2/Q3 rules; (3) detected non-principle (13.6% = 1,147/8,410) is never committed (`commit_non_fb_types: false`, D2418/D2467). **FIXED in D2589:** item 9 clarified + D2587 rules injected into SINGLE_SOURCE/SINGLETON prompts. REMAINS: `commit_non_fb_types` decision (P1) + whether convergent should ever emit non-principle (design question, P1). | **D2589:** item 9 clarified + rules injected into single-source/singleton. Remaining: `commit_non_fb_types` decision (D2590) + convergent-emits-non-principle design question.
| BUG-232 | 2026-09-09 | **False convergence — 96/1012 golden FBs (~9.5%) are same-author echoes.** `source_diversity>=2` but <2 distinct authors (John Gall 22, "Rob Thomas et al." 15, Anne Miller 11, Gunther Kress 10, Parandeh 5, Harvard Business Review 5...). Root cause: source_diversity counts distinct source_ids (content hashes), so 2 editions/chapters/files of the SAME author/work register as "diverse" — violating the ≥2-INDEPENDENT-source convergence bar that the convergent few-shot explicitly rejects (`same_author_echo_negative` / `citation_echo_detection`). `scripts/audit_false_convergence.py` → `governance/false_convergence_echoes.json` (96). Fix = recompute source_diversity as distinct PRIMARY WORK (author+title dedup, not file/hash) + re-tier echoes → single-source + add CI gate. | **FIXED 2026-09-09:** `scripts/fix_false_convergence.py` (Qwen3.8-27B R5 code-review APPROVE) re-tiered all 96 echoes → `is_convergent=0` + `source_diversity=1` (author-floored) in `maxwell.db` (C13 backup `maxwell.db.bak_20260909_162749_pre_falseconv`; integrity ok). Manifest `governance/false_convergence_fix_manifest.{json,md}`. **REMAINS (CORRECTED 2026-09-14):** the source_diversity recompute is **ALREADY DONE** — D2176 made `resolve_source_id` = `sha256(author|title)` (not content hash), verified 2026-09-14 (`compute_source_id` same-work collision test passes). The buglog's "recompute as distinct primary works" is SUPERSEDED. Only genuinely remaining = **CI gate** that fails if a convergent golden FB has <2 distinct authors. |
| BUG-224 | 2026-09-05 | OMLX server wedges under sustained load on Qwen3.8-27B: large-output calls (>~1200 tokens) hang BEYOND the requests timeout (call_omlx timeout not respected), then the server needs ~15-60s to recover before even tiny requests respond. Reproduced repeatedly during D2576 depth audit (single-FB calls OK ~7s, but batched/long-output calls wedge every ~6-12 requests). This blocked the delegated Qwen3.8 market research (D2576) and forced the audit to fall back to `delegate(custom_deepseek)` for the bulk + a small direct-OMLX overlap. Extends BUG-220/DELEGATE-001 (Qwen direct-call workaround itself is now flaky). Likely cause: 27B 4-bit model + concurrent/unreleased context on 64GB. **MITIGATION APPLIED (D2581, 2026-09-05):** `services.omlx.read_timeout=60` + `services.omlx.wedge_recovery_sleep=20` (config); `call_omlx` now uses `timeout=(connect, read)` so a mid-response stall trips fast, and distinguishes `ReadTimeout` (wedge) → 20s recovery sleep before retry instead of the 3s hammering. Remaining workload-shaping guidance: 3-model vote should still process Qwen3.8 in small single-FB calls. UNVERIFIED under a live sustained-load wedge (needs a re-run of the Qwen3.8 bulk audit to confirm). |
| BUG-222 | 2026-09-04 | goose runtime drift: `active_provider=custom_deepseek` (deepseek-v4-pro) + `GOOSE_THINKING_EFFORT=high`. CORRECTION (2026-09-04, D2560 re-verify): DeepSeek is NOT dead — it is LIVE+AUTHENTICATED via macOS Keychain internet-password (`srvr=https://api.deepseek.com/v1`, `acct=Bearer`); prior "HTTP 401 / no credentials" was an ERROR (probed without key + wrong keychain service names). Real issue = remote CLOUD → C1 ($0, all generation local) + C3 (sovereignty) violation BY DESIGN. Fix = set `active_provider=maxwell_omlx` (user decision, affects goose runtime). D2560. |
| BUG-151 | 2026-08-20 | taxonomy structural overlap (`education` dual-listed + 267 raw aliases) |
| BUG-148 | 2026-08-20 | S2 `route` field stale/uniform (`route="FB"` on all 2,878). **THIRD DRIFT SOURCE (2026-09-08):** `config/pipeline_config.yaml:250` gates S2 route to `[FB, NULL]` but `route_to_content_type` maps 5 values (FB/PT/PI/GE/TI), and `stage4_merge.py:_resolve_content_type` falls back `ROUTE_TO_CONTENT_TYPE.get(route, "principle")` — so a record with a stale/missing content_type is silently forced to `principle`, bypassing D2587. Fix = deprecate route as ontology carrier; ABSTAIN → growth_edge/quarantine on missing content_type (§5.2.5). | **CLOSED D2616 (2026-09-13, Phase 0):** `_resolve_content_type` now returns `QUARANTINE_CONTENT_TYPE` ("quarantine") on missing content_type — route is fully deprecated as ontology carrier, never forced to principle. `quarantined` list + `S4_QUARANTINE_OUTPUT` (`quarantined.jsonl`) sidecar persist the held records (C16, no silent drop). Tests `test_resolve_content_type_route_deprecated` / `test_resolve_content_type_default_quarantine` assert the new behavior. |
| BUG-182 | 2026-08-27 | 48 singleton empty-shells deterministically re-return empty after S2 rerun |
| BUG-170 | 2026-08-24 | non-principle types (PT/PI/TI/GE) routed but NOT classified/enriched |
| BUG-159 | 2026-08-21 | prompt-injection contamination (cluster_11649, 0.007%) |
| BUG-168 | 2026-08-24 | `pipeline/dspy_trainer.py` exists but NOT wired to any stage (built-not-wired, same pattern as BUG-085) — wire OR archive | **ARCHIVED D2592 (2026-09-08) + gate REVISED D2594 (2026-09-09):** wire-or-archive resolved → ARCHIVE (defer). DSPy optimizes on labels; golden content_type labels not yet spotless (286 unlabeled + 701 model-only of 1027), so wiring now = training on noise. **RE-OPEN GATE (tier-based, NOT all-1027):** re-open DSPy when the golden set is spotless under the 3-tier architecture (D2594) — Tier1 few-shot fully human-verified (content_type + extraction_type, 0 unlabeled + 0 model-only) + Tier2 training corpus statistically cleaned (label model + P4 + cleanlab) + Tier3 boundary corpus ≥150 cases 2-of-3 adjudicated. |
| BUG-160 | 2026-08-21 | evidence-passage topical relevance not verified (1/30 drift sample cites carbon passage for maternal-health FB) |

## 🟡 OPEN — WORTH

| Bug | Date | Issue |
|---|---|---|
| BUG-229 | 2026-09-08 | **Stale `content_types.py` docstring** (lines 12-17): claims convergent S2 "emits `content_type: principle`… golden file reflects this: 75/75 principle" — numerically wrong (actual = 59 principle / 61 positives) AND architecturally misleading (prompt item 9 offers all 5 roles; the 100%-principle skew is few-shot bias, not design). Risks a future engineer concluding the vacuous axis is invariant-by-design. Fix = correct docstring. **RESOLVED 2026-09-10:** docstring corrected — stage2_fewshot_convergent.yaml holds 84 examples / 61 should_extract with NO top-level content_type field; the all-principle skew is few-shot bias, not an invariant. |
| BUG-230 | 2026-09-08 | **`growth_edge` lacks a positive entry criterion → catch-all migration risk.** Under D2587 Q3 (single prescriptive claims funneled to `principle`) + Q1 (single tool steps → `tool_instruction`), the residual ambiguity gets dumped into `growth_edge`, recreating the vacuous-axis failure mode one bucket over. Fix = add positive definition ("MUST contain an articulated open tension or unverified correlation; NOT a dump for failed depth-tests") (§5.2.8). | **OBSERVED 2026-09-09 (D2596):** 4 golden objects (00334/00385/00495/00882) were assigned growth_edge with rationale "utilizable fact" — the exact catch-all pattern. **RESOLVED option-1:** re-classified all 4 → noise_drop (established facts/trends, no prescriptive claim); growth_edge kept narrow. **REMAINS:** codify the positive entry criterion in content_types.yaml to prevent recurrence. **RESOLVED 2026-09-10:** criterion codified in config/content_types.yaml `growth_edge.description` (OPEN TENSION / UNVERIFIED CORRELATION; NOT a dump for failed depth-tests, NOT a bare 'utilizable fact'). |
| BUG-223 | 2026-09-05 | `'[]'` literal-array hygiene: 54 `emerging` FBs store `discipline_raw = '[]'` (JSON-empty-array string) instead of `''`/NULL. Queries testing `discipline_raw != ''` will wrongly count these as "has raw". Correct empty-test = `(discipline_raw IS NULL OR TRIM(discipline_raw)='' OR discipline_raw='[]')`. Minor (all 54 are legitimately `emerging`); normalize `'[]'`→`''` or add a shared empty-check helper in `pipeline/schemas.py`. D2569. |
| BUG-169 | 2026-08-24 | TI `parameters` empty on 31/143 single-source + 100/307 singleton TI — ontology nuance (technique-type vs API TI); verify at rerun |
| BUG-099 | 2026-08-13 | Model registry drift: gpt-oss/Phi misnamed "verifier" (rename deferred) |
| BUG-238 | 2026-09-10 | **`fbs.content_type` is a VACUOUS axis — "99.6% principle" is unverified and materially wrong.** All 7,995 rows carry `gen_model = Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` (the model that matches the reliable-pair depth consensus only 44.7%), commits bae6662/24d2690, taxonomy v5.5 — and the field was NEVER human-verified. Two independent measurements put the true non-principle rate far above the stored 29/7,995 (0.4%): (1) the D2587/D2596 ledger `governance/content_type_human_decisions.jsonl` = 35/114 = **30.7%** non-principle; (2) a random 23-row read of `principle`-labelled rows (2026-09-10) found ~8-9 noise_drop / tool_instruction / methodology rows (~35%). `governance/content_type_verification_backlog.json` shows 217/1,027 UNLABELED + 341 medium + 332 high (all model-proposed). CONSEQUENCE: depth (D2610/D2611) is DOWNSTREAM of content_type — a depth label on a noise_drop history-summary is meaningless — so the 7,995-row depth rerun is BLOCKED until content_type is verified. FIX: verify content_type on the 1,027 golden backlog (rank unlabeled → low → medium → reswept → high), extrapolate a CI-tight non-principle rate from a >=150 random sample, then relabel depth only on the confirmed-principle subset. **REFINED 2026-09-10 (150-row audit, `governance/content_type_sample_audit_2026-09-10.json`): 19/150 clear non-principle (12.7%, 95% CI 7.3-18.0%) + 25 borderline = 29.3% (95% CI 22.0-36.6%) — uniform across extraction_type. So the corpus is ~13-29% non-principle, not 0.4%. **217 UNLABELED SLICE ADJUDICATED 2026-09-11 (D2612):** human + DeepSeek-v4-pro second-opinion → 201/217 = 92.6% agreement; frozen non-principle 15.7-16.6% (confirmed-principle 178/217 = 82.0%); 16 contested → `governance/content_type_contested_16_form.md`. REMAINING bands: model_low 13 + model_medium 341 + model_high 332. |
| BUG-234 | 2026-09-10 | **`governance/depth_vote_checkpoint.jsonl` contains duplicate records:** 1780 lines for 996 unique FBs (784 dupes) because `--retry-failures` APPENDS a re-voted record instead of upserting. The builder's resume path keys by `fb_id` so labels are correct, but the artifact is ambiguous and 1.8× bloated, and any naive line-based consumer double-counts — measured: a naive list read inflated the 200-row held-out test to n=363 and skewed the DS↔Qwen3.8 agreement estimate. Fix = compact/upsert on retry (D2577). **RESOLVED 2026-09-10 (D2610):** save_checkpoint() upserts - the checkpoint is rewritten one line per fb_id after every run and via --compact; 1780 lines / 996 unique -> 996. |
| BUG-235 | 2026-09-10 | **Depth fail-closed fabricates a label:** when no voter majority exists (1-1-1 split), `build_depth_vote_set.py` coerces the FB to `depth: domain` (81/996 = 8.1% of the clean set). This injects error straight into the default class — the D2577 encoder scores 0.300 accuracy on those 20 held-out rows vs 0.556 on vote-agreed rows. Fix = emit `depth_confidence: low` + `needs_review` instead of a fabricated label (never re-brand an abstention as `domain`). **RESOLVED 2026-09-10 (D2610):** the fail-closed-domain path is REMOVED - aggregate() abstains (depth empty, confidence low, needs_review) and the row goes to governance/depth_review_queue.yaml (318 records). |
| BUG-236 | 2026-09-10 | **Qwen3-Coder-30B is an unreliable depth voter used as the tie-breaker.** It matches the DeepSeek+Qwen3.8 consensus on only **303/678 = 44.7%** of FBs; because 2-of-3 wins, it never overturns the reliable pair but it *decides* the 304 rows where DS≠Q38 — i.e. the hardest 31% — so those 2/3 "majorities" (612/996 of the clean set) are coin flips. Real reliable-pair agreement = **69.0%**, not the 91.9% the 3-voter unanimity rate implies; only 303/996 (30.4%) are unanimous. Every downstream depth number inherits this ceiling (D2577). **RESOLVED 2026-09-10 (D2610):** Qwen3-Coder-30B is demoted to label_vote.advisory_voters - recorded, never decisive; the label now requires reliable-pair unanimity and disagreement abstains instead of being coin-flipped. |
| BUG-237 | 2026-09-10 | **Production `fbs.depth` is unverified silver presented as a semantic field.** On the 996 FBs the vote audited, the DB depth column is 100% identical to the raw gpt-oss silver label and agrees with the 3-model vote only **458/996 = 46.0%**; all 7995 rows are `gen_model = Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` (commit bae6662/24d2690, pre-BUG-185 prompt era). Depth is the only S4 semantic field with no independent verification (S5 NLI does not cover it) and it feeds `S4_DIFFICULTY_MAP` → difficulty (D2410). Fix = relabel under the vote policy + add a depth contract test (D2577). **PARTIALLY ADDRESSED 2026-09-10 (D2610/D2611):** label policy + serving path decided; the 7995 production rows are still pre-BUG-185 silver and unverified - relabelling under D2610 is the open action. |

---

## ✅ CLOSED / RESOLVED — bottom (recent)
- **BUG-240** — **Joint-vote script had NO DeepSeek retry → transient empty-content errors became PERMANENT abstains.** The 200-row D2612 pilot produced 6/200 rows (3.0%) with `DeepSeek returned empty content (truncated reasoning?)` — the v4-pro reasoner occasionally returns `reasoning_content` with an empty final `content` under `response_format: json_object` (DELEGATE-001 trap). `vote_once` swallowed the exception, checkpointed the error vote, and the resume path skips done rows — so those 6 rows were unrecoverable (extrapolated ≈ 240/7,966 over the full run). Also: bare `json.loads` (no fence/repair handling) and per-row R14 stamps missing. FIXED D2612 (2026-09-11): `_call_deepseek` retries with backoff (empty-content / 429 / 5xx / network, 3 attempts) and falls back to free-JSON via `parse_json_robust`; added `--retry-failures` (re-vote only errored voters) + `_all_voters_ok`; per-row `schema_version`/`gen_model`/`pipeline_commit`/`created_at` stamps (R14); `--preflight` (DeepSeek probe + OMLX cache-gate D2460 + Qwen3.8 live stress + population count); `--checkpoint` override so pilot vs production artifacts never clobber. Verified end-to-end: 5-row smoke (0 voter errors, R14 stamps present) + full preflight PASS (OMLX stress verdict=SLOW — see BUG-224 memory pressure note). ✅ (2026-09-11)
- **BUG-239** — content-type adjudication form generator dropped the `boundary` field on 217/217 rows and truncated `mechanism` at 400 chars on 185/217 (median 87 chars lost, max 314) — the human adjudicated on degraded inputs. FIXED D2612 (2026-09-11): `scripts/content_type_human_review_form.py` now emits full `mechanism` + `boundary`; `temp/_build_form.py` truncation removed. Impact measured: after showing DeepSeek the full text (incl. boundary), the 16 remaining contested rows are exactly the boundary-sensitive cases. ✅ (2026-09-11)
- **BUG-233** — CHALLENGE boundary corpus 150/150 overlaps Tier2 training golden (latent eval contamination). RESOLVED D2609 (option b+): ruled RULES-REGRESSION-ONLY content_type eval (NOT model-eval); 150 example_ids declared HELD-OUT from future content_type training. (a) rejected — cross-task overlap (discipline/domain training vs content_type eval), content_type rules-based today → zero contamination, and excluding 150 IDs would starve the data-limited discipline classifier. Plain (b) rejected as prose latent-trap. FIX: `eval_scope=rules_regression_only` + `held_out_from_training=true` schema fields + `pipeline/boundary_holdout_guard.py`. ✅ (2026-09-09)

- **BUG-225** — D2587 rules dormant (content_type_rules + min_steps, 0 code consumers). FIXED D2589: `pipeline/content_types.py` loads CONTENT_TYPE_RULES + PROCESS_TEMPLATE_MIN_STEPS; `scripts/audit_content_type_contract.py` enforces `len(steps)>=min_steps` via `_check_d2587_rules` (wired into audit_s2 + audit_s4). ✅ (2026-09-08)
- **BUG-226** — silent empty-extraction_type default. FIXED D2590: `_extraction_type_defaulted:true` + `_extraction_type_default_reason:empty_form` stamped on the repair; counter reported in both run summaries; explicit `normative_heuristic` never overwritten. ✅ (2026-09-08)
- **BUG-227** — dedup asymmetry (semantic near-dup principle-only). FIXED D2590: `dedup_fbs_by_cosine` now runs on PT/PI/GE/TI write paths before the exact `fb_id` loop. ✅ (2026-09-08)
- **BUG-150** — S4 discipline `emerging` regression 38.4% (vs 15.5% canary) RESOLVED via D2566 (deterministic −354) + D2567 (Track B slim −478 / raw −981 / domain-axis −846) + D2568 (kind-swap 1,235 + deterministic promotion 54 + LLM promotion 24). Net discipline=emerging **1,842→927** (11.6%). Remaining 250 genuine taxonomy gaps (Ecology/Musicology/History of Technology/audio signal processing + 221 tail) → D2399 candidates (frozen). ✅ (2026-09-04)
- **BUG-221** — retrieval 0.000 recall RESOLVED: (1) FTS5 implicit-AND fixed via `_fts_query()` stopword-stripped OR/prefix terms → FTS recall@k **0.000→0.667** (D2554); (2) vector leg unblocked by Homebrew Python → **1.000** (BUG-104/D2556). Remaining FTS gaps are synonym/abstract queries, now served by the vector leg. ✅ (2026-09-04)
- **BUG-104** — sqlite-vec `load_extension` missing on python.org Framework Python 3.12.1. VERIFIED FIX: run retrieval/vector ops under **Homebrew Python** (`/opt/homebrew/bin/python3`, 3.14 — has `enable_load_extension` + `sqlite_vec` 0.1.9). Result: vector leg recall@k **0.000→1.000**, hybrid 0.900 ✅ (2026-09-04)
- **BUG-098** — `psutil` declared in `requirements.txt` (already `psutil>=6.0` per D2341; C11/C24 satisfied — verified this session) ✅ (2026-09-04)
- **BUG-220** — `delegate()` broken for Qwen models STANDARDIZED on direct one-shot OMLX curl (D2543/D2549): live-verified Qwen3-Coder one-shot code-gen; goose provider `maxwell_omlx.json` synced (+`gpt-oss-20b-MXFP4-Q4`); `just oneshot` recipe added ✅ (2026-09-04)
- **BUG-220-MCP** — MCP `delegate_local` hardened: model allowlist + system cap + file-count cap + path-containment (config `mcp.delegate_local`); gemma-4-E4B code review 6/6 PASS ✅ (2026-09-04)
- **F-03** — MCP `depth` enum fixed → canonical 4 values (`universal|cross-domain|domain|specialized`) ✅ (2026-09-04)
- **BUG-215** — 1,097 empty `discipline_raw` REPAIRED: Track B (1,172 classified → 419 resolved + 753 raw-corrected) + T-311 (311 metadata-copy) + kind-swap (62 domain recovered). 0 empty `discipline_raw` remaining ✅ (2026-09-04). RESIDUAL (2026-09-05, D2569): 66 non-emerging FBs re-gained empty raw via D2568 promotion (raw cleared + stale `emerging_real`); `scripts/fix_bug215_residual.py` restored raw (24 alias) + reverted 42 unverified promotions to emerging ✅
- **BUG-219** — integrity-check #4 FP FIXED (`unicodedata`/`heapq` → STDLIB_MODULES; `scripts`/`audit_evidence_cleanliness` → LOCAL_MODULES) ✅ (2026-09-03)
- **BUG-216** — 28 FBs `domains_raw` backfilled from `checkpoint_enriched_kindsafe.jsonl` via `scripts/fix_bug216_domains_raw.py`; 1 genuine empty `emerging` accepted ✅ (2026-09-03)
- **BUG-217** — `taxonomy_version` unified v5.1→v5.5 (DB + `config/version.yaml`); `pipeline_commit`/`manifest_hash` kept as per-record provenance ✅ (2026-09-03)
- **BUG-218** — 9 sidecar empty-shells ACCEPTED (gemma cross-exam already ran; `body_incomplete_reason` set; `outcome_metric`/`syntax`/`parameters` genuinely absent from source — BUG-182 model-level gap) ✅ (2026-09-03)
- **BUG-214** — taxonomy hook tuple row_factory (D2527) ✅
- **BUG-193** — CircuitOpenError import (D2525) ✅
- **BUG-196** — name truncation (D2517) ✅
- **BUG-197** — domain-not-discipline (D2510 prompt + D2519 kind-swap) ✅
- **BUG-198** — 6 dropped singleton principles (D2519) ✅
- **BUG-205** — a/an book-dedup false-merge (D2510) ✅
- **BUG-200/BUG-199** — cross-kind contamination (D2500) ✅
- **BUG-188** — S4 2GB checkpoint truncation (D2487) ✅
- **BUG-195** — fb_id collision (D2499 dedup) ✅
- **+ 78 older CLOSED** — full list in `archive/governance_pre_tiered_2026-09-03/buglog.md` (🟢 markers, 87 total).

> Full bug history (217 distinct BUG-IDs): `archive/governance_pre_tiered_2026-09-03/buglog.md`.

## BUG-253 — reasoning models scored 0 under a small max_tokens budget (harness artifact, NOT model failure)

**Discovered:** 2026-09-16 00:05 during the voting suite run.

**Symptom:** Ornith-1.5-35B-A3B-REAP-19B and gpt-oss-20b-MXFP4-Q8 both scored `0.000` on all 251 voting rows, with pairwise agreement of exactly `1.000` between them. Identical empty/ungradable output is the fingerprint of a harness artifact, not two models failing the same way.

**Root cause:** the voting suite used `max_tokens=120`. Both models are reasoning models: they emit a thinking trace first and never reach the JSON before the budget is exhausted. Their `pred` fields contained prose ("Let me analyze this principle carefully...", "We need to classify the principle...") and the grader reported `no json`.

**Fix:** raised the voting suite budget to `max_tokens=512`. Non-reasoning models finish well below 120 tokens, so their results were unaffected and remain comparable.

**Recurrence:** this is the **third** instance of the same failure class:
1. ARM-2 — gpt-oss returned empty `content` under `response_format=json_object`.
2. ARM-4 — Ornith-1.5-9B returned 0/6 with a thinking trace consuming the whole budget; fixed with `enable_thinking=False`.
3. Voting — REAP + gpt-oss truncated at 120 tokens.

**Standing rule:** any suite that grades strict JSON must either raise the budget for reasoning models or suppress reasoning explicitly. A `0.000` score with high cross-model agreement on identical output must always be investigated as a harness bug before it is reported as a model result.

## BUG-254 — oMLX model registry is startup-cached; the fix is POST /admin/api/reload, not a GUI restart
**Found:** 2026-09-16 · **Severity:** medium (operational, cost hours) · **Status:** FIXED

Symptom: a model symlinked into `~/.omlx/models/` never appears in `/v1/models` or the GUI
(Ornith-1.5-35B-A3B-REAP-19B scored 0.0 on 43/43 calls with HTTP 404); a deleted model still
appears listed. Root cause: the registry is scanned **only at app start**.

Four wrong fixes were attempted before the right one: the control socket at
`~/Library/Application Support/oMLX/control.sock` is stale (`ConnectionRefusedError`); AppleScript
`quit` is blocked (`-128 User cancelled`); System Events is blocked by macOS accessibility
(`-1728`); `omlx-cli restart` drives a SEPARATE managed server and is the documented
D2455/D2456 duplicate-install trap.

Correct fix (C12 — API over GUI): `POST /admin/api/login {"api_key":...}` for an
`omlx_admin_session` cookie, then `POST /admin/api/reload {}` -> "Re-discovered 10 models".
Wrapped as `scripts/omlx_reload.py`. Also activates pending `settings.json` /
`model_settings.json` edits (the 2026-09-15 decoder changes: prefix cache ON, server temp 0.0,
grammar flags) with no duplicate server and no app restart. Verified 9 -> 10 models.

Standing rule: **never quit/reopen oMLX to register a model.** Run `scripts/omlx_reload.py`.

## BUG-255 — `POST /admin/api/reload` swaps the single resident model and silently wedges an in-flight benchmark
**Found:** 2026-09-16 · **Severity:** medium (silent stall, no server-side trace) · **Status:** mitigated

Symptom: the Ornith 4bit/8bit A/B wrote 0 checkpoint rows for 38 minutes while its process stayed alive.
`/health` showed `loaded_count: 1`, and `/admin/api/activity` showed **`active_requests: 0`, `idle_seconds: 2298`**
— i.e. the server had nothing in flight, so this was NOT a slow generation and NOT a model hang.

Root cause: `POST /admin/api/reload` is documented as *'re-read model settings, re-discover models, **preload
pinned**'*. `Phi-4-mini-instruct-8bit` is pinned (`pinned: true`), so the reload loaded it and — because oMLX
serves ONE resident model — evicted the Ornith-9B-8bit the benchmark was mid-run on. The harness's next request
was never accepted; it wedged client-side, and its 900 s client timeout did not surface an error row.

Two lessons, both now standing rules:
1. **Never run `scripts/omlx_reload.py` (or any model swap) while a benchmark is in flight.** Single-resident
   oMLX means a reload is a model eviction. Reload between runs, never during one.
2. **Diagnosing a stall:** a live process + `active_requests: 0` + growing `idle_seconds` means the harness is
   wedged, not busy. Do not wait it out. Check `active_requests` before assuming a slow model.

Recovery: `kill <harness>` then relaunch the same command — the per-item checkpoint resumes (the 36 rows
already written are skipped, the hung item is retried). Verified: 2740 -> 2746 rows within 75 s of relaunch,
planning completed for both variants.

## BUG-256 — RETRACTED: the 'empty GSM8K gold' was my display truncation, not a harness defect
**Raised:** 2026-09-16 · **Retracted:** 2026-09-16 (same day) · **Severity:** none · **Status:** retracted

**What I claimed:** a GSM8K row had an empty reference answer (`pred=284 gold=`), which would fail every
model unconditionally and inflate the error rate by up to 4 points.

**What was actually true:** the observation came from an ad-hoc diagnostic that printed
`str(r['detail'])[:14]`. The real detail string is `pred=284 gold=284` — 17 characters. The cutoff landed
exactly after `gold=`, manufacturing the appearance of an empty gold. Verification: scanning every
`gsm8k`/`math500` row for a detail ending in `gold=` returns **0 rows**, and the dataset guard below
drops **0 of 25** items in both frozen sets. There was no bug.

**Kept anyway (defensive, not a fix):** `_usable_numeric_gold()` and `_usable_letter_gold()` in
`tools/model_eval_suite.py` now drop ungradable rows at load time for gsm8k / math500 / mmlu_pro.
`grade_numeric()` falls back to `g = gold` when the reference yields no number, so such a row *would*
silently fail every model — the guard makes that impossible by construction instead of relying on the
frozen sets happening to be clean. Verified non-destructive: 25/25/25 items still load.

**Lesson:** apply BUG-253's rule to myself — before logging a suspected harness artifact, verify it against
the raw record, not against a truncated rendering of it. One `[:14]` produced a false bug report in a
governance log; the same class of unchecked inference is exactly what this benchmark effort exists to
eliminate. RETRACTED, with the entry kept rather than deleted so the register stays auditable.

## BUG-257 — the niah top tier exceeded oMLX's context window, making it unmeasurable
**Found:** 2026-09-16 · **Severity:** medium (silent unmeasurable tier) · **Status:** FIXED

Symptom: Run B's long-context suite produced `HTTPError 400 Bad Request` on every model at the
top tier — 6 failures for Qwen3-Coder alone — while the lower tiers succeeded.

Root cause: `suite_niah()` targeted `(4000, 16000, 32000)` prompt **tokens**, but oMLX runs with
`max_context_window: 32768`. A 32000-token prompt plus `max_tokens` plus chat-template overhead
exceeds the window, so the server rejects the request before inference. The tier could never have
produced a result for any model, at any quantisation — it was a configuration defect, not a model
failure. Same class as BUG-253 (budget) and BUG-256 (my own truncation): **a score that is identical
across models of wildly different ability is a harness signal.**

Fix: top tier `32000 -> 24000` (with 12000 mid; 24000 + 40 output ~= 24.5k < 32768).

Note: a 400 returns immediately, so the wasted wall-clock was negligible; the rows remain in the
checkpoint as transport errors and are retried automatically (`_done_keys` skips errored rows), so the
missing tier is recovered by the next run rather than lost.

Related: `max_context_window: 32768` in `~/.omlx/settings.json` is itself a candidate to raise
(the models advertise 131k-262k), but that requires a reload — and reloading during a run is BUG-255.
Deferred deliberately.

## BUG-258 — model_eval_report.py counted transport errors as model failures (CORRUPTED THE DELIVERABLE TABLE)
**Severity:** high (it is the artifact the portfolio decisions are read off) — **Found:** 2026-09-16, during the final-chain run
**Symptom:** `tools/model_eval_report.py` scored every checkpoint row with `1 if r.get("ok") else 0`,
including rows whose `err` field was set (404/400/timeout). A row with an error is a measurement we
never took, so scoring it 0 silently *drags down any model that was unlucky enough to be running
during an oMLX outage*. `model_eval_suite._done_keys()` already excluded those rows; the report did not.
**Impact measured (before -> after fix):**
- REAP-19B toolcalling 0.50 -> **1.00** (4 real passes distorted by 4 stale 404s)
- REAP-19B planning 0.50 -> **1.00**
- REAP-19B reviewing 0.417 -> **0.833**
- REAP-19B stability 0.10 -> **0.20** (still the weakest, and now an honest number)
- Qwen3-Coder niah 0.50 -> **1.00**
- gemma-4-E4B niah 0.667 -> **1.00**
The REAP toolcalling/planning cells are load-bearing: REAP is the recommended tool-caller, and the
corrupted table would have ranked it mid-pack and likely reversed that decision. Same class as
BUG-253: an implausible score is a harness signal before it is a model result.
**Fix:** `if r.get("err"): errs[model] += 1; continue` before any accuracy/latency accumulation.
Error counts are still reported per model, in their own column.
**Restart needed?** No. The report is invoked once, at the very end of the chain, and re-reads the
checkpoint, so the correction applies retroactively to every already-measured model.
**Related fix (same file, same cause):** the long-context table pooled suites. Keyed on
(model, ctx_tokens) only, it averaged niah (needle retrieval) with lc_reasoning (multi-hop reasoning)
at the same token size and printed Qwen3-Coder 16000tok = 0.38 — which is neither a real niah score
(3/3 = 1.00) nor a real lc_reasoning score (0/5 = 0.00). Now emitted per suite with explicit n.

## BUG-259 — report tables quoted PRUNED models as if they were candidates
**Severity:** medium (misleads consolidation docs) — **Found:** 2026-09-16
**Symptom:** the checkpoint is an append-only log, so pruned models keep their rows. After Prune #3/#4
the aggregate table still listed granite-4.2-8b (116 rows), gemma-4-12B (122 rows) and
Ornith-1.5-9B-OptiQ-4bit (206 rows) alongside the live portfolio, and a deleted model's 404s read as
model failures. Any of those numbers could have been quoted into the frozen stack as a candidate.
**Fix:** `PRUNED_MODELS` list in the report; pruned models are excluded from the decision table and
emitted in a separate "PRUNED — historical rows only, NOT in the portfolio" section with row counts.
**Restart needed?** No.
**Also:** `scripts/audit_final_chain.py` added — verifies the ARTIFACT of every chain step instead of
trusting the log line, because `run_final_chain.sh` has no `set -e` and `model_eval_suite.py` prints
`done in 0s, 0 new results` both for a genuine no-op and for a silent failure.

## BUG-257 CORRECTION — the 32000 tier is a per-template ceiling, not a global one
**Found:** 2026-09-16, from the report's long-context breakdown.
BUG-257 claimed the top niah tier exceeded oMLX's window "for EVERY model". Measured: false.
At ctx=32000, **Qwen3.8-27B graded 3/3 and REAP-19B graded 3/3**, while Qwen3-Coder (400 on all 3 ids)
and gemma-4-E4B (400 on all 3) failed. It is a per-chat-template overhead ceiling at the same nominal
token count, not a global window overflow. The tier fix (4000/12000/24000) is still the right
conservative choice, but the causal claim was too broad and is retracted here.
**Operational note (not a bug):** the in-flight Run B read `governance/eval_models_longctx.txt` at
process start (v2), so it is sweeping the DELETED Ornith-1.5-9B-OptiQ-4bit (all requests 404, fail
fast) and does not cover the keeper Ornith-1.5-9B-MLX-8bit. Harmless but incomplete: the queued
`scripts/rerun_niah_fixed.sh` reads the file at its own start (v3, keepers only) and closes the gap.

## BUG-260 — pipe_s4_classify_gold scored the RAW LLM label against CANONICAL gold (S4 swap gate [[G2]] was mis-measured)
**Severity:** high (it is the number the S4 model-swap decision was to be taken on) — **Found:** 2026-09-16, on the step-3 results
**Symptom:** the step-3 production table read `gpt-oss 0.200 / Qwen3.8 0.217 / gemma 0.150` discipline and
`domF1 0.097 / 0.109 / 0.060` — implausibly low next to the 0.709 benchmark-prompt headline, i.e. a BUG-253-class
harness signal (not a model result).
**Root cause:** `merged_cribs_classify()` returns a **RAW** scientific label **by design** (D2138 two-stage: the raw
label captures what the principle IS; the canonical label is assigned afterwards by
`map_to_canonical_with_fallback` in `stage4_merge`). The scoring script compared that raw label directly to the
human-adjudicated **canonical** gold, so every model was scored for failing a mapping step it was never asked to
perform. Example: pred `cognitive linguistics` vs gold `linguistics`; pred domains `brand storytelling /
narrative design` vs gold `arts & culture / semiotics & communication`.
**Fix:** the scorer now replicates the production mapping (synonym index → kind-constrained index → D2515 compound
split → emerging) and scores the MAPPED labels, printing the unmapped numbers alongside as `raw_*`. Scores are
recomputed from the stored raw predictions, so all 180 already-measured rows are corrected without re-running any
model. No restart needed; step 6 (OptiQ) picks the patch up automatically because the chain launches it fresh.
**Corrected step-3 table (60 gold rows each, same rows, same seed):**
| model | raw disc | **mapped disc** | raw domF1 | **mapped domF1** | med_s |
|---|---|---|---|---|---|
| gpt-oss-20b-MXFP4-Q8 (incumbent) | 0.200 | **0.350** | 0.097 | **0.320** | 17.2 |
| Qwen3.8-27B-MLX-4bit | 0.217 | **0.350** | 0.109 | **0.335** | 82.2 |
| gemma-4-E4B-it-MLX-4bit | 0.150 | **0.300** | 0.060 | **0.220** | 9.9 |
**Decision consequence:** the benchmark-prompt gap (Qwen3.8 0.709 vs gpt-oss 0.339) does **not** reproduce on the
production prompt — the incumbent is dead level on discipline (+0.000) and +0.015 behind on domain F1, at 17.2s vs
82.2s per row (4.8x). A swap is not justified, so [[D3]]'s conditional R5 exception is **not** triggered and the S4
stage stays R5-clean.
**OPEN, DISCLOSED:** the replicated mapping is weaker than whatever produced the stored DB values (it reproduces
production's own `domains_raw` → `domains` pairs only 32.5%, and leaves 54% emerging on DB raw labels, against
9.6% emerging actually stored across all 7,995 FBs). So the mapped column is the best same-scorer comparison
available, not a reproduction of the production scorer; the true absolute accuracy is >= 0.350. The **relative**
comparison — the thing the swap decision rests on — is unaffected. Settling the absolute number needs the real
mapping function, not a replica.

## BUG-261 — safe_delete.py copies before deleting, so reclaiming space can FILL THE DISK
**Severity:** critical (near-miss: got to 1.7 GB free on a 926 GB volume, 100% used, during a routine
reclaim) — **Found:** 2026-09-17 10:22, while retiring Qwen3.8-27B-OptiQ-4bit
**Symptom:** the reclaim was launched to free 19 GB. Free space went 24 GB -> 3.9 GB -> 1.7 GB, i.e.
it consumed ~22 GB to delete 19 GB. `pipeline/safe_delete.py` copies the target into
`backup/deletions/{timestamp}/` **before** deleting, so the operation needs roughly 2x the target
size free. On a volume with 24 GB free and a 19 GB target there is no headroom: the partial copy
plus the still-present original crossed the line.
**Risk:** a full disk corrupts whatever is writing at that moment — maxwell.db, the eval
checkpoints, Parquet exports. This was one `shutil.copytree` away from damaging the knowledge DB.
**Recovery:** killed safe_delete mid-copy (PID 64437), removed the partial backup copy
(`backup/deletions/20260917_102216`), then deleted the HF cache directly with `rm -rf`.
Verified after: `maxwell.db` PRAGMA integrity_check = ok, 7,995 FBs, eval checkpoints 0 unparseable
rows (4,132 + 180). Free space recovered to 48 GB. No data lost.
**Fix (applied):**
1. Free-space pre-flight in `backup_then_delete()`: refuse when the target exceeds ~half of free
   space, with an explicit `MAXWELL_SAFE_DELETE_LARGE=1` escape hatch.
2. `scripts/reclaim_optiq.sh` now deletes weights directly with `rm -rf` and says why: R-D410
   protects pipeline OUTPUT, and model weights are not output. Deleting weights must not need space.
**Standing rule:** anything larger than free space / 2 does NOT go through safe_delete.py. Weights,
model caches and anything reproducible from a hash are direct deletes with the reason logged.

## BUG-263 — the S2 cross-family relabel produces NOTHING when run with gpt-oss (silent, every record)
**Severity:** critical (the R5 control for FORM drift has been silently doing nothing) — **Found:** 2026-09-17, from a failing stage probe
**Symptom:** `scripts/pipe_stage_probe.py` measured S2 relabel on 12 real FBs: 12/12 errors,
`RuntimeError: OMLX call failed after 2 attempts: 'content missing from message (reasoning-...)'`.
**Verified cause (raw payload test, 2026-09-17, gpt-oss-20b-MXFP4-Q8, temp 0.0):**

| max_tokens | reasoning-off prefix | reasoning_content | content |
|---|---|---|---|
| 64 | no | 274 chars | **0 chars** |
| 64 | yes | 276 chars | **0 chars** |
| 256 | no | 1097 chars | **0 chars** |
| 256 | yes | 0 chars | **0 chars** |
| 1024 | no | 1967 chars | 29 chars -> JSON |
| 1024 | yes | 1132 chars | 42 chars -> JSON |

gpt-oss is a Harmony reasoning model: it emits reasoning first and only emits `content` when the
budget is large enough to get past it. `stage2_relabel_extraction_type._judge()` calls
`call_omlx_json(..., max_tokens=64)`, so the model spends the whole budget on reasoning and returns
**no content**; `_extract_label()` then returns "", which the caller treats as "no valid label".
Net effect: with `stage2.relabel_cross_family_model = gpt-oss-20b-MXFP4-Q8`, the cross-family
relabel that exists to undo single-source FORM drift (~60% causal_mechanism vs ~11% baseline,
chi-square ~2247) labels **nothing**, silently, for every record.
**Note:** the reasoning-off prefix does NOT fix it (0 content at 64 and 256, and at 1024 reasoning
still ran 1132 chars). Raising the budget does. `pipeline/omlx_call.py` already documents the class
("xgrammar ... returns EMPTY content for Harmony reasoning models") — this path was not covered.
**Fix (required, not yet applied):** make the relabel judge's output budget config-driven and large
enough (>=1024) for reasoning models, and assert non-empty content per call so an empty label can
never be mistaken for "no label needed" (C16: no silent errors).
**Related sweep:** see the same-turn audit of every `call_omlx_json` call site for max_tokens < 512
with a reasoning model — the same failure mode applies anywhere gpt-oss/Qwen reasoning models are
asked for a small JSON answer.

---

## BUG-263 — CORRECTION (2026-09-17) — latent, NOT past damage

**What I previously claimed:** "S2 relabel silently labels NOTHING for every record" — implying
the FORM-drift repair never happened and hours were burned for nothing.

**What the artifacts actually show (verified, not asserted):**
- `relabel_work/relabel_gemma_sweep_resume2.log`: `changed 3412, unchanged 1348, failed 1`
- `relabel_work/relabel_sweep.log`: `changed 2491, unchanged 3270, failed 0`
- `checkpoint_gemma.jsonl` after-dist: causal_mechanism 489/8410; production checkpoint today:
  488/8402 (5.8%). The single-source before-dist was causal_mechanism 3771/5761 (~65%).
- `relabel_flag` count across all 8402 production records: **0**. Logs containing
  'cross-family judge failed': **0**. Neither log contains cross-family counters at all.

**Conclusion:** the FORM-drift repair (causal_mechanism ~65% -> 5.8%) was REAL, SUCCESSFUL work
by the gemma judge on 2026-08-23, with 1 failure. The logs predate the cross-family layer, so the
R5 cross-family FLAG judge has **never executed in production even once**. BUG-263 is therefore a
**latent** defect — it would have silently produced zero flags on its first real run, and zero
flags reads as "no disagreement", i.e. a clean bill of health for labels nobody checked.

**Status: FIXED** (code) — `max_tokens` 64 -> `stage2.relabel_judge_max_tokens: 1024` (config, C12);
reasoning-off prefix applied for gpt-oss; `_judge()` raises `JudgeEmptyResponse` carrying model +
budget + parsed length instead of returning ""; fail-closed guard aborts the run when EVERY
cross-family call in a chunk fails (`"0 disagreements is NOT a result"`). Verified by measurement
to be FAILED: budget 64/256 -> content 0c; 1024 -> JSON parses.
**Run artifact pending** — the 200-record cross-family pass is the outstanding evidence.
Retraction note: the earlier "wasted the whole run" framing in this session was wrong and is
withdrawn here.

## BUG-264 — poisoned rows survive every re-run (found by drift_monitor, 2026-09-17)

`tools/model_eval_suite._done_keys()` skips any (model, suite, id) already present in the
checkpoint without `err`. So a row measured while the HARNESS was broken is never re-measured:
re-running the suite prints `done in 0s, 0 new results` and reads as success while the model keeps
a score it never earned.

Evidence: 20 gpt-oss toolcalling rows with `detail="no json"` (the BUG-262 missing-prefix run)
still present in a 4164-row checkpoint. gpt-oss's toolcalling cell would report 0.00 forever.

Guards added: `scripts/check_stale_toolcall_rows.py` (markers in `config/bench_preflight.yaml`,
C12), criterion `P1.no_stale_gptoss_toolcall_rows` in `governance/p0_p1_criteria.yaml`, and
`scripts/purge_stale_rows.py` which ARCHIVES the original before rewriting (crash-safe, verified).

## Process fixes this session (the meta-bug behind all of the above)

- `tools/bench_preflight.py` + `config/bench_preflight.yaml` — M1 gate: probes every (model, suite)
  cell with the REAL call path and the REAL budget before scoring. NA is not 0.
- `tools/model_eval_suite.py` now calls `_cell_status()` per cell and records `na_reason`;
  `tools/model_eval_report.py` excludes NA rows and discloses the count.
- `governance/p0_p1_contract.md` (frozen acceptance criteria) + `governance/p0_p1_criteria.yaml`
  (executable form) + `scripts/drift_monitor.py` (20 criteria, re-derived from the filesystem).

## BUG-265 — toolcalling scored the HARNESS, not the model: native tool_calls ignored

**Found:** 2026-09-17 by `scripts/omlx_raw_dump.py` (new). **Severity: high — it corrupted a
model role.**

`tools/model_eval_suite.call()` reads only `response.choices[0].message.content`. A model that
answers with NATIVE tool calling puts the answer in `message.tool_calls` and leaves `content`
EMPTY, so the harness records a failure.

Measured on toolcalling item `tool-0` ("Find the three most recent log files under /var/log."):

| model | finish_reason | content chars | tool_calls | verdict |
|---|---|---|---|---|
| gemma-4-E4B | `tool_calls` | 0 | 1 (`search_files {query: log, path: /var/log}`) | **CORRECT ANSWER, scored as failure** |
| gpt-oss-20b | `length` | 0 | 0 (805 reasoning chars) | truncated mid-reasoning |
| Qwen3-Coder | `stop` | 112 (JSON) | 0 | graded normally |

Consequence: gemma-4-E4B is published at toolcalling 0.55 while making well-formed native tool
calls. It was a candidate for the tool-calling role and lost on that number. Four consecutive
0-character responses in 1.8s (far too fast to be thinking) were the tell that an answer was
arriving in a field nobody read.

**Root cause class:** identical to BUG-262/263/264 — the harness cannot distinguish 'the model
failed' from 'the harness did not read the answer'. A stress test on ONE live response before
committing the suite would have caught it; that test is now `scripts/omlx_raw_dump.py` plus
`tools/bench_preflight.py --selftest`.

**Fix:** normalise `message.tool_calls` into a graded JSON form when `content` is empty, so every
model is graded on the same rule (tool name + argument containment).

## BUG-266 — gpt-oss toolcalling is truncated, not incapable

Same probe: gpt-oss returned `finish_reason=length` with 805 characters of `reasoning_content`
and zero content at max_tokens=200. At 1024/2048 it emits ~1433 characters of prose and never the
requested JSON. So two distinct defects were being collapsed into one 'gpt-oss scores 0.00':
(a) the answer arrives after the budget expires (`length`), (b) the instruction 'Reply ONLY with
JSON' is not followed for this prompt. Correct statement: **gpt-oss did not emit the required JSON
at 200/1024/2048 on this prompt** — a prompt/format result, not a capability claim.

## BUG-265 — MAGNITUDE CORRECTION (2026-09-17). The bug is real; my impact claim was overstated.

I stated that gemma's toolcalling 0.55 "was measuring the harness, not gemma" and that it was
"making correct tool calls and being scored 0.55 for it". Both are overstated. The archived
pre-purge rows (`backup/deletions/model_eval_checkpoint_pre_bug262_20260917_115539.jsonl`) show
what the blinded harness actually recorded for gemma-4-E4B toolcalling, n=20:

    {'ok': 11, 'bad json': 3, 'no json': 2, 'arg to=None': 2, 'arg query=*': 1, 'arg assignee=None': 1}

11 of 20 were ALREADY CORRECT. gemma emits native `tool_calls` only for some items - item tool-0
("find the three most recent log files") is one of them, which is the item I happened to dump, so a
single-item probe made the effect look total. Measured impact of the fix: 0.55 -> 0.60, i.e. **+1 item**.

Lesson for the record: a one-item probe establishes that a defect CLASS exists; it does not
establish its magnitude. Magnitude requires the stored per-row details, which were available the
whole time in the archived artifact. Fix the classification, then measure the blast radius before
quoting it.

The defect itself stands and is fixed: `call()` read `content` only and never `tool_calls`.
Blast radius confirmed by dumping all 7 models: gemma only (6 others returned content JSON).

## BUG-268 — RESOLVED (2026-09-17) — the human-gate sheets shipped UNANSWERABLE, and leaked the labels they were meant to test

**Class:** artifact contract violated + blindness leak in an evidence-collection instrument. Caught
before the human work started; no labels were wasted.

**What happened.** `F14_RELABEL_OR_RETIRE_SAMPLE_20260917.csv` and
`JUDGE_CALIBRATION_SHEET_20260917.csv` were generated with a row-selection and a JSON dump, and were
then verified only for **row count** — never for **answerability**. Three defects:

1. **G2 had no body text at all.** The sheet carried name / labels / `text_chars` but not
   `definition`, `application` or `source_text`. The question it asks ("is this a legitimate
   knowledge object?") is unanswerable from a name.
2. **G3 truncated every input to 300 characters**, and `T2_suffix_merge` rendered only two
   *names* — so "are these the same object?" had no text to compare. `T3_content_type` carried no
   definition either (the source artifact has none; it needed a DB join).
3. **Blindness leak.** T3's rendered row included `d2615_content_type` and `disagreement_pair` —
   i.e. the *prior human label* and the *two competing labels* — and T6 carried its own claimed
   labels. A judgment sheet that shows the answer being tested measures **obedience**, not accuracy,
   which is precisely the failure mode the calibration exists to detect.

**Cost had it shipped:** ~80 minutes of human labelling producing unscoreable data, a false
calibration verdict, and possibly the wrong substitute judge adopted for ~650 verification calls.

**Fix.** Both sheets regenerated with DB joins (`expansion_queue_108.jsonl` / `gold_4axis.jsonl`
`example_id -> fb_id`, and direct `fbs` lookups for T2's base/dup and T6's source text); prior
labels stripped from T3/T6; text-first column ordering so labels cannot anchor the verdict; and a
**pre-flight assert**: no row may ship with < 200 characters of input text. Verified: 0 such rows in
both sheets. Scoring vocabulary frozen in `governance/HUMAN_GATE_RUBRIC_20260917.md`.

**Process fix (the generalisable part).** An artifact intended for human labelling must assert its
own answerability and its own blindness before it is handed over. Row count is not a contract. This
is the same root cause as BUG-262..266: **the instrument was never tested, only produced.**

## BUG-269 — RESOLVED (2026-09-17) — G3 judge calibration: on 3 of the 4 testable decision tasks NO cross-family judge beats a constant answer

**Measured** (`governance/judge_calibration_20260917.md`, 72 calls, blind human labels from
`JUDGE_CALIBRATION_SHEET_20260917.csv`):

| task | n | constant-answer baseline | gemma-4-E4B | gpt-oss-20b | verdict |
|---|---|---|---|---|---|
| T1 dedup | 7 | 0.571 (`same`) | **1.000** (lift +0.43) | 0.571 (lift 0.00) | ADOPT gemma |
| T2 suffix-merge | 8 | 0.875 (`merge`) | 0.875 (lift 0.00) | 0.750 (lift −0.12) | **degenerate** |
| T3 content_type 7-way | 9 | 0.778 (`principle`) | 0.222 (lift −0.56) | 0.333 (lift −0.44) | **degenerate / worse than constant** |
| T6 frontier69 justification | 9 | 0.778 (`justified`) | 0.778 (lift 0.00) | 0.778 (lift 0.00) | **degenerate** |

**What this invalidates.** The plan assumed the F-10 R5/C8 violation could be fixed by swapping in a
different-family judge (~770 calls, later ~650 once T4/T5 were found to have no source artifact).
The calibration says that substitution buys **no information** for T2, T3 and T6: gemma and gpt-oss
match or under-perform "always answer the most common label". Spending the calls would produce a
*second uninformative opinion* and would look like verification while being none — the same failure
mode as the same-family judges it was meant to replace, only harder to notice.

**Root causes, per task (each has a different real fix).**
- **T2 is not a judgement at all.** "Is the candidate the base name + a suffix?" is a *string
  operation*. It only needed a model because the original code path used one. → re-implement
  deterministically: 0 calls, 100% precision. **A verifier that cannot be wrong by opinion.**
- **T3's ontology boundary is not operationalised.** The human answered `principle` 7/9 while both
  models leaned `process_template`/`growth_edge`; the human's own note codes say so ("I feel this a
  principle than process template … BUT IT STILL INCLUDES SOME STEPS"). D2587 defines the boundary
  (single prescriptive instruction = principle; >=2 steps = process_template) but no consumer
  applies it. → mechanise the step-count/verb test first, then judge only the residue.
- **T6 is unanswerable as posed.** Both models returned `justified` for all 9 rows — a yes-bias. "Is
  the label justified by the source text?" is a global judgement with no evidence requirement;
  `config/content_types.yaml` already specifies a per-FORM `verification_standard`. → wire that in
  (finding F-15) and re-pose the question as that specific check.

**Meta-rule adopted (the reusable part).** Accuracy must ALWAYS be reported against the
**majority-class baseline**. A bare accuracy column made 0.778 look acceptable on T6 and 0.875 look
excellent on T2, while both were exactly the constant answer. Now enforced in
`scripts/judge_calibration.py` with `min_margin_over_baseline` in
`config/eval_integrity.yaml::judge_calibration`; `--rescore` re-scores stored answers after any rule
change without re-calling a model.

**Caveat stated in the artifact:** n is 7-9 decisive rows per task. Enough to *reject* a judge that
does not beat the constant; not enough to *certify* one. The proper instrument (Krippendorff alpha +
a per-task n_min) remains unbuilt (market research A1/A2).

## BUG-270 — OPEN (2026-09-17) — the frontier69 audit artifact disagrees with the runtime KB on 10 of 69 objects, and two concepts exist in BOTH taxonomies

Both found from the operator's G3 answer for T6-01, whose note read: *"DISCIPLINE IS MISSING,
RESEARCH METHODOLOGY IS DISCIPLINE NOT DOMAIN BUT LABELLED AS DOMAIN."*

**(a) artifact/DB divergence.** `governance/frontier_qwen38_69_objects.json` disagrees with
`fbs.discipline` for **10 of the 69 objects** (9 with a *different* discipline, 1 with an empty one
where the DB has a value). The differences are not granularity arguments — e.g.
`S4-GOLD-MINED-00096` is `cognitive science` in the artifact and `visual semiotics` in the DB;
`S4-GOLD-MINED-00097` is `computational geometry` vs `aesthetics`. All 69 resolve to a DB row, so
this is a straight disagreement about the same objects, not a join failure. The frontier69 artifact
is one of the six same-family decision lists (task T6) and it informed the anchor, so its divergence
propagates wherever those labels were used.

**(b) taxonomy seam.** Normalised name comparison across the two taxonomies finds **two concepts
present in both**: `research methodology` (a discipline) vs `research & methodology` (a domain,
carried by **648 rows**), and `emerging`. Because the collision is only visible after normalising
`&`/spacing, the earlier exact-match contamination check missed it — that check was too weak.

**Not yet decided:** whether (a) the artifact or the DB holds the intended label, and (b) whether
`research & methodology` belongs in the domains taxonomy at all, which would move 648 rows.

## BUG-271 — RESOLVED (2026-09-17) — the discipline<->domain guard validated MEMBERSHIP, not DISJOINTNESS, so the "enforced" rule was violated undetected on 909 rows

**The rule** (D2620/BUG-197): the 61 disciplines and 43 domains are DISJOINT vocabularies; crossing
them is a hard error, fail-closed. `pipeline/schemas.py::validate_discipline_domain()` said so,
`tests/test_taxonomy_disjointness.py` tested it, and the function was wired into S4 merge, S6 commit
and the 4-axis merge — three write paths. It looked enforced.

**Why it failed anyway.** The guard only fired when a label was ABSENT from its own vocabulary
(`x not in CANONICAL_DISCIPLINES`). A label that legitimately exists in **both** vocabularies passed
clean. And the test asserted the claim with **exact string comparison**. So when the taxonomy
contained `research methodology` as a DISCIPLINE and `research & methodology` as a DOMAIN — the same
concept, differing only by punctuation, definitions near-identical — **909 live rows carried the
collision while every check reported OK.** The function's docstring asserted an invariant that
nothing verified, and the assertion was false.

**Fix (three layers, so a docstring can never be the only guardian again):**
1. The guard now compares labels **NORMALISED** (case + punctuation insensitive) and treats an
   undeclared cross-axis collision as a hard error. Declared collisions are still reported.
2. `config/eval_integrity.yaml::label_axes` makes the claim **data**: `shared_labels` (the
   documented `emerging` catch-all, legitimately on both axes) and `known_collisions` (recorded
   debt with row counts and a decision reference). A missing/unreadable contract fails toward
   STRICTER, never toward a silent pass.
3. `scripts/audit_taxonomy_disjointness.py` + criterion **`AXC.taxonomy_disjoint`** (fail) check the
   taxonomy AND all 7,995 runtime rows, and print the debt on every run. A new normalised test
   (`test_vocabularies_disjoint_under_normalisation`) locks it. Verified: taxonomy 0 undeclared,
   runtime 0 undeclared, 742 rows on declared debt, exit 0.

**Also required by this fix:** `pipeline/schemas.py::parse_domains()`. Hand-written domain parsing
(`strip("[]").replace("'", "")`) stripped PYTHON repr quotes while the column stores JSON with
DOUBLE quotes, so every domain looked non-canonical — 17,247 false flags on the audit's first run.
One shared parser now, because the same mistake appeared in more than one place.

**Open:** the 909 rows (`research methodology` 261 as discipline / `research & methodology` 648 as
domain) still carry the collision. It is DECLARED, counted and printed, but a ruling is required on
which side is authoritative.

---

## BUG-272 — RESOLVED (2026-09-17) — T2 suffix-merge was mis-classified as a deterministic task; measurement shows NO signal separates the classes

**My claim, which was wrong:** "is name B just name A + a suffix?" is a string operation, therefore
T2 can be solved deterministically at 0 model calls with exact accuracy (BUG-269's remedy). Blind
human labels falsified it, in four steps:

| approach | result |
|---|---|
| name-only rule | MERGE **32/32** — a 100% bias, i.e. the exact degeneracy this script was built to replace |
| name + character-shingle body check | 0/8 vs the human labels (40-char shingles cannot see paraphrase in a 300-char text) |
| name + token-Jaccard | merge range **0.037-0.211**, keep **0.167** — OVERLAPPING, not separable |
| name + provenance overlap | a merge pair shares **0** source ids; the keep pair shares **2** — no signal |

The distinguishing question is semantic ("do these two propositions assert the same thing?"), and it
is not recoverable from the name, the text overlap, or the provenance. The human's own answer
proves the point: `Social Proof Bias` vs `Social Proof Bias (2)` is **keep** — a name collision
between two different objects — while six other `(N)` pairs are merges.

**Corrected design.** `scripts/t2_suffix_verifier.py` now does DETECTION + TRIAGE only and
**abstains** on every verdict (38 items: 32 marker pairs + 6 name collisions). Every abstention is a
human decision. 8 of the 32 pairs were already decided during the G3 calibration, so ~24 remain
(~25 min). A forced guess would score 0.000 against the 0.875 constant-answer baseline, which is
precisely why it abstains.

**The generalisable law (third instance this session).** "This task is deterministic" is itself a
**measurable claim**, and it must be measured before it is asserted. F-03's remedy, the
membership-vs-disjointness guard, and this — all three were plausible, all three were wrong.

---

---

## BUG-273 — the domains axis violates its own cardinality contract (2026-09-17)

**Severity:** medium. **Status:** OPEN.

`config/content_types.yaml` / `canonical_labels_reference.md` define `domains` as **multi-label 1..3**.
Measured on 7,995 rows: histogram `{1: 2648, 2: 2776, 3: 1569, 4: 732, 5: 214, 6: 50, 7: 6}` —
**1,002 rows carry more than 3 domains**, maximum **7**. 2.16 labels/row.

Why it matters: the domain facet is the axis that fans out in retrieval, so its cardinality is exactly the
thing that decides fan-out cost, and the documented contract understates it by 2.3x at the tail. Nothing
enforces the contract at write time.

Fix: enforce the bound in `pipeline/schemas.py` at commit, with the bound in config, and either raise the
documented contract to the measured reality or adjudicate the 1,002 rows down. Do not silently widen the
docs — that is drift (anti-drift rule 8).

---

## BUG-274 — the `related_fbs` graph is 56.8% asymmetric (2026-09-17)

**Severity:** low-medium. **Status:** OPEN.

Measured: 156,190 directed edges (dict-parsed `{"fb_id","relationships"}`), **0 dangling**.
A→B implies B→A in only 43.2% of cases: **88,592 one-way edges**. Also **7 self-references**.
Relationship types: source_crossover 132,723 | domain_overlap 64,493 | discipline_overlap 35,644 |
semantic_near 4,985. 13 of 7,995 rows are isolated.

Why it matters: graph expansion (`--graph-aware`) traverses this set, so a one-way edge is a
reachability hole that depends on which node you start from. It also means a rename applied to only one
side of an edge pair creates a hole that no symmetry check would catch.

Fix: decide whether the relation is intended to be symmetric (`domain_overlap`, `discipline_overlap` look
symmetric by nature; `source_crossover` may not be); normalise the symmetric subset, and drop self-references.

---

## BUG-275 — LINK is unenforceable at retrieval, and both facets are unindexed (2026-09-17)

**Severity:** medium. **Status:** OPEN.

Three related facts:
1. `pipeline/retrieve.py` **never references `duplicate_of`** (grep: 0 hits). D2627 defined `duplicate_of` as the
   canonical pointer of a dedup row and "NEVER delete", but the retrieval path returns those rows, so the
   decided policy is decorative (F-15 pattern: a field with no consumer).
2. `sqlite_master` holds **no index on `fbs(discipline)` or `fbs(domains)`** — both facet filters full-scan.
   Fine at 7,995 rows, not future-proof.
3. `domains LIKE '%label%'` is **not sargable** and over-matches on a *partial* label
   (`%research%` → 768 rows vs 648 for the canonical label). Measured **0** false positives with a FULL
   canonical label, and **0** substring-containment pairs among the 44 domain labels — so the operator is
   safe today only because the vocabulary happens to have no substring pairs. That is luck, not a guard.

Fix (D-271d, no human needed): add `duplicate_of IS NULL` to the retrieval predicate behind config, replace
the substring match with JSON-aware membership (`pipeline/schemas.py::parse_domains`), add the two indexes.

### CORRECTION to BUG-275 §1 (same day, measured)

The claim "the retrieval path returns duplicate rows" is **WRONG for the 17 linked rows and I withdraw it.**
Measured: all 17 rows carrying `duplicate_of` are `status='QUARANTINE'`, and `search_keyword` defaults to
`status='PASS'` (quarantine only enters when `include_quarantine=True`). LINK-before-MERGE is therefore
**already enforced end-to-end for the 17 rows** — via the quarantine status, not via `duplicate_of`.

What survives is narrower and precise:
- `duplicate_of` itself has **no reader anywhere** in `pipeline/` (0 references in `retrieve.py`, `query.py`,
  `schemas.py`; only the commit path writes it). It is a **provenance pointer, not a retrieval guard** — an
  F-15-class field with no consumer. That is fine for traceability but it means **LINK must always set
  `status='QUARANTINE'`**, otherwise the row re-enters default retrieval. Encode that pairing in config.
- The 662-row flagged set is **not yet linked**, so the §1 risk is *prospective*, not live: if those rows are
  linked without quarantine, 389 extra rows enter retrieval.
- The **index gap is real and unchanged** (see §2). That alone justifies D-271d.

**Meta:** this is the fourth instance this session of a plausible claim that measurement refused.

---

## BUG-276 — the C13 safety net is DEAD, and nothing backs up the DB (2026-09-17)

**Severity:** HIGH. **Status:** RESOLVED 2026-09-19.

**RESOLVED:** `pipeline/backup_guardian.sh` repointed at the SQLite DB — consistent `.backup` (WAL-safe)
+ `PRAGMA integrity_check` on the copy, fail-closed. Verified live (backup written + integrity ok).

Discovered while trying to satisfy C13 ("backups after batch writes") after the D-271d index write.

`bash pipeline/backup_guardian.sh` fails on every invocation: `❌ backup_guardian: Source not found:
<root>/knowledge pipeline/output/5.generated`. Measured: `knowledge pipeline/output` **does not exist at
all**, so both SOURCE and TARGET (`.../output/5.backup`) are dangling, and there is no `backups/` directory
anywhere in the repo.

Two defects, the second worse than the first:
1. **The C13 backup path has been non-functional**, and its failure was only ever a printed ❌ on a manual
   invocation — no criterion, no test, no alert. An iron rule with no check is a habit, not a guarantee.
2. **It never backed up the database.** It is an `rsync` of a Markdown output tree. The KB (`maxwell.db`:
   7,995 rows, 164,202 identity-keyed edges, the entire label asset) has **no automated backup at all** —
   its only protection is third-party folder sync, which F-09 already flags as a hazard.

**Consequence for the plan:** the two largest planned operations — the D-271c identity migration (re-keying
164,202 edges) and the F-14 FORM re-derivation (3,348 relabels) — are **bulk writes with no safety net**.
Today the first DB backup was created by hand (`archive/db_backups/maxwell_pre_index_20260917.db`, 135.5 MB,
verified openable, 7,995 rows) using `sqlite3.Connection.backup`, the crash-safe API.

**Fix (no human needed):** replace or repoint `backup_guardian.sh`; add a DB backup via `sqlite3 .backup`
(never a raw file copy of an open WAL database); a retention policy that respects the F-08 disk floor
(46 GiB free vs floor 150 GiB — rotate, do not accumulate); and a drift criterion (`C13.db_backup_fresh`) so
a dead backup path can never again be silent.

**Bonus defect:** the file-count counter is computed by a `find` over the missing source, so even a
"successful" run reports `0 files synced` — the counter would have masked the empty source.

---

## BUG-277 — the content_type axis mixes two vocabularies, and the docs say "7 values" (2026-09-17)

**Severity:** LOW (documentation / consumer hazard; no live validator defect found). **Status:** OPEN.

Found while building the G4 ruler sheet. Measured:

- `pipeline/content_types.py::CONTENT_TYPES_ALL` = all **7** values (correct).
- `config/content_types.yaml::content_types` = **5 ROLES** (principle, process_template, process_instance,
  tool_instruction, growth_edge).
- `config/content_types.yaml::dispositions` = **3** (classified, noise_drop, quarantine), where `classified`
  means "has one of the 5 roles" and is not an answerable value.
- The DB `content_type` column stores **7** values: every DB value is in `CONTENT_TYPES_ALL`
  (**no live validator defect** — checked explicitly before writing this entry).
- But 2 DB values (`noise_drop`, `quarantine`) are **absent from the yaml `content_types` key**, so any
  consumer that reads only that key sees a 5-way axis while **1,090 rows** (noise_drop 1,055 + quarantine 35)
  use the missing values.

**Measured consequence (the reason this is logged):** a menu built from `content_types` alone made **15 of the
150 ruler-sheet rows unanswerable** (6 quarantine + 9 noise_drop) and capped validation at 1–5 while the KB
uses 7. Fixed in `scripts/build_ruler_sheet.py::vocab()` (roles + dispositions, sourced from config).

**Why keep it in the register:** the axis is ONE column holding TWO vocabularies (a role says what the object
IS; a disposition says it carries no role). `AGENTS.md` describes the axis as "7 values"; the config describes
it as 5 roles + 3 dispositions. Both are right about different things, and a reader cannot tell which source
is authoritative for a menu, a validator or a relabel. Suggested fix: one YAML key that lists all answerable
values with its kind, so no consumer has to guess. Until then, `pipeline/content_types.py::CONTENT_TYPES_ALL`
is the authority and the yaml key is not.

**Meta:** this is the fifth instance this session where a plausible claim (mine) was refused by measurement —
and the first where the measurement *exonerated* the code and convicted the tooling.

---

## BUG-278 — stage 5 treats "unverifiable" as "untrue", and never persists which one it was (2026-09-19)

**Severity:** HIGH (largest single recall loss in the system). **Status:** OPEN. Found by the blind ruler + DB audit.

`pipeline/stage5_verify.py` is fail-closed by design (D2093): `ENTAIL ≥ 0.10 → PASS`, `NEUTRAL (unverifiable)
→ QUARANTINE`, `CONTRA → QUARANTINE`. Measured in the live KB:

- `status`: **PASS 4,745 (59.3%) · QUARANTINE 3,250 (40.7%)**.
- `pipeline/retrieve.py` defaults the keyword search to `status='PASS'` → **40.7% of the KB is invisible**.
- Of the 3,250 hidden rows, **1,780 are labelled `principle`** and **2,940 carry a real, non-`emerging`
  discipline**. 2,744 sit at the `confidence_score` cap (0.25, D2310).
- `contradicts_fbs` is **NULL for 100% of rows**, so **NEUTRAL and CONTRA are indistinguishable in the store**:
  the distinction the fail-closed rule depends on is thrown away at write time.
- `verification_results` holds one check (`mechanism_quality`) plus NLI scores; it does not record the NEUTRAL
  vs CONTRA verdict in a queryable form.

**Why this is a defect and not a policy choice:** "I could not verify this" and "the evidence contradicts this"
are different claims about the world. Collapsing them means the KB cannot distinguish *unproven* from *disproven*,
which (a) hides 22% of its principles from retrieval and (b) makes the S5 threshold untunable, because raising or
lowering it moves two different populations at once. Peer-reviewed support that NLI-based consistency is a
weak-correlation signal with known blind spots (so a NEUTRAL verdict must never be read as FALSE):
Honovich et al., TRUE, NAACL 2022, DOI 10.18653/v1/2022.naacl-main.287.

**Fix (proposed R3):** split the enum into `UNVERIFIED` vs `CONTRADICTED`, persist the S5 verdict, and let retrieval
include `UNVERIFIED` at a lower evidence tier (R14) rather than hiding it. Human ruling required.

---

## BUG-279 — the production classifier is instructed to FREE-GENERATE labels, contradicting its own docstring and D316 (2026-09-19)

**Severity:** HIGH (root cause of the classification drift). **Status:** OPEN.

`pipeline/stage4_merge.py`:

- line **13** (module docstring): *"Classification: single-pass prompt lists all valid labels inline (D316:
  discipline singular, domains multi-label)"*.
- line **341** (`CLASSIFY_SYSTEM_PROMPT`): *"CRITICAL: Classify based on what the principle IS, **not what label
  fits best from a predefined list**. Use precise, scientifically accurate names. If the principle is about
  'neuroaesthetics', say 'neuroaesthetics' — do not round it off to 'design psychology'."*
- line **472** (`build_classify_prompt`): *"Build a FREE scientific classification prompt — **no canonical lists**."*
- line **500**: *"(Use the most precise discipline name you know — not generic buckets)"*.

The implementation is the opposite of the documented contract, and it is deliberate (D2138 "classify freely, then
map"). Measured consequences over 7,995 rows:

- `taxonomy_match_method`: **synonym 3,990 (49.9%) · exact 2,127 (26.6%) · emerging_real 1,181 (14.8%) · alias 697 (8.7%)**.
  Only **26.6%** of labels were correct on the first attempt.
- Human agreement by method (blind ruler, 150 rows): **exact 0.61 · synonym 0.49 · emerging_real 0.33** — monotone.
  The measured **ceiling of the current design is ≈0.61, i.e. AT the 0.60 floor.**
- Raw label space: **1,089** distinct raw disciplines → 61 slots (17.9:1); **4,982** distinct raw domain members
  → 43 slots (**115.9:1**), of which only **31 are canonical** and **61% are hapax** (appear once).

**Consequence:** the free-generation instruction is the mechanism that produced the 999-rule `config/alias_map.yaml`
(362 discipline + 637 domain aliases = 14.8:1 for domains). The alias map is a **compensating control for a prompt
defect**, not a synonym list. Adding more rules cannot fix it: even a perfect lookup on a free-generated string is
bounded by the string.

**Fix (proposed R1):** present the closed menu **with each label's definition** and require one of N or an explicit
`none`; keep logging the raw answer alongside for drift measurement. Then the alias map can be retired.

---

## BUG-280 — `content_type` (ROLE) is functionally single-valued in production, and `depth` is undefined without it (2026-09-19)

**Severity:** HIGH (an entire axis is decorative). **Status:** OPEN.

Measured, live KB:

| content_type | rows | of which PASS |
|---|---|---|
| principle | 6,525 | **4,745** |
| noise_drop | 1,055 | **0** |
| process_template | 188 | **0** |
| process_instance | 139 | **0** |
| quarantine | 35 | **0** |
| growth_edge | 30 | **0** |
| tool_instruction | 23 | **0** |

- **`status='PASS'` ⟺ `content_type='principle'`, exactly** (4,745 = 4,745; **zero** non-principle rows pass).
  In the retrieval-visible KB the 5-role ontology has **one effective value**.
- **All 1,470 non-principle rows have an EMPTY `depth`** — `depth` is defined only for `principle`. So `depth`
  is not an independent facet: it is coupled to ROLE, and `depth = ?` in retrieval can only ever match principles.
- Blind ruler (stratum A, n=100): ROLE accuracy **0.740** against a constant-answer baseline of **0.750**
  (`principle`), i.e. **lift −0.010** — no better than answering "principle" every time. Stratum B per-class:
  `tool_instruction` 3/3, `noise_drop` 2/3, `process_template` 2/3, `process_instance` 1/2, `quarantine` 1/4,
  `growth_edge` 0/1.
- The reviewer, sampling stored `noise_drop` and `quarantine` rows, re-classified several as `principle`
  → the disposition bin is contaminated in the direction of *discarding real content*.

**Consequence:** the KB presents a 5-role ontology, an axis with 7 values, and a `depth` facet. In production:
one role, coupled depth, and a disposition bin that is partly wrong. Any downstream consumer (Anytype export,
retrieval, navigation) that trusts ROLE is trusting a constant.

**Fix:** decide whether ROLE is (a) repaired to carry signal (it can, once BUG-279 is fixed, because the role
question is currently asked in the same free-generation prompt), or (b) reduced to `principle | not-principle`
and replaced by the verification status (BUG-278). Human ruling required.

---

## BUG-281 — `noise_drop` fuses two different questions; there is no relevance axis (2026-09-19)

**Severity:** HIGH (the schema cannot express what the user actually asked for). **Status:** OPEN.

`noise_drop` (1,055 rows) is used for both:
1. **ontological** rejection — "there is no extractable object here" (TOC, index, gazetteer), and
2. **relational** judgement — "this is true, but irrelevant to me".

The blind reviewer stated (2) explicitly, repeatedly, unprompted: *"it's a valid fact but irrelevant … too niche,
nothing to do with any of my interest (design, business, personal improvement) so closer to noise drop"*;
*"valid fact but irrelevant"*; *"CRT is already outdated so it could also be quarantine, but since I'm interested
in old tech it can be still relevant"*; *"does not provide any exact utilizable instruction, serves more like a
SUMMARY even though random is important"*. Open verdicts recorded on 29 discipline cells and 22 FORM cells.

Peer-reviewed basis for why these are different axes: relevance is **relational** — it exists between a
document, a user and a goal, not as an intrinsic property of text (Saracevic, JASIST 2007, DOI 10.1002/asi.20682).
An intrinsic content type can therefore never express it, and a user-relative judgement cannot be stored in a
column that also means "unesxtractable".

**Consequence:** (a) the disposition bin is contaminated in both directions; (b) the KB cannot be *personalised*
without re-running a classifier; (c) "irrelevant" content is being deleted from view rather than ranked, so a
change of interest is unrecoverable (the reviewer's "old tech" case).

**Fix (proposed R4):** add a **relevance/utility axis** — explicit named criteria (mission fit, actionability,
personal utility), rated on a sample, with a local judge (the QuRating pattern, arXiv 2402.09739; FineWeb-Edu
pattern, arXiv 2406.17557), kept **revisable and dated** so a later interest change can re-rank without a
re-extraction. Human ruling required.

---

## BUG-282 — the schema is 53% dead, and the dead columns are the instrumentation (2026-09-19)

**Severity:** HIGH (this is *why* failures stay invisible). **Status:** OPEN.

Audited all 45 non-provenance attribute columns for degeneracy (>90% one value). **24 are dead or near-dead.**
R14 *stamps* (`schema_version`, `gen_model`, `verifier_model`, `taxonomy_version`, `fb_version`, `pipeline_commit`,
`pipeline_run_id`) are correctly constant and are **not** counted as defects. The genuine ones:

| field | value | consequence |
|---|---|---|
| `contradicts_fbs` | NULL **100%** | contradiction detection has **no implementation**; NEUTRAL/CONTRA indistinguishable (BUG-278) |
| `classification_status` | `CLEAN` **100%** | the write-boundary validator has **never** reported anything |
| `classification_errors` | `None` ×7,993 | the **1,002** domains-contract violations (BUG-273) were never recorded |
| `classification_error` | `''` 100% | same |
| `provenance` | `llm_extracted_from_source` **100%** | the F-02 evidence-tier system is **not in use**; `eval_integrity.yaml`'s fail-closed tier gate is vacuous against the live KB |
| `prerequisite_fbs` | `[]` 100% | no prerequisite graph |
| `procedural_skill` | `''` 100% | never populated |
| `usage_count` / `last_retrieved_at` | `0` / `''` 100% | **no retrieval telemetry at all** — the system does not know which rows were ever used |
| `feedback_score` / `feedback_count` | `None` / `0` 100% | no feedback loop |
| `borp_score` | `0.0` 100% | dead |
| `is_summary` | `0` 100% | correct by construction (gated clusters never become FBs — 158 gated ids in `t11/checkpoint.jsonl.gated_ids`) but leaves **no drop ledger** |
| `evidence` | `cited` 95.5% | near-dead |
| `depth` | `''` for all 1,470 non-principle rows | facet undefined for 18.4% of the KB (BUG-280) |

**Consequence:** a reader inspecting the schema sees a system with contradiction detection, evidence tiers,
feedback, usage tracking and a self-reporting validator. None of them have data. **This is the mechanism behind
"a new weak point appears every day" — the instrumentation reports health, so defects stay invisible until a human
samples the rows.** The G4 ruler found in 150 rows what 24 green columns had been reporting as fine.

**Fix:** either populate or retire each field (C19 — no dead code). Retiring is the cheaper honest option for
`borp_score`, `feedback_*`, `procedural_skill`. `usage_count`/`last_retrieved_at` must be **populated**, because
without them "is the KB good?" can only be answered by a hand-run ruler.

---

## BUG-283 — the ruler scorer accepted only integer indices and would have crashed on the first real sheet (2026-09-19)

**Severity:** MEDIUM (tooling; found and fixed same day, before the loss). **Status:** FIXED.

`scripts/score_ruler_labels.py` read answers as `menu[int(str(r[col])) - 1]`. The first reviewer filled the sheet
by **name** (`Causal Mechanism`, `descriptive model`, `noise_drop`), not by index, and left 51 cells blank.
Running the scorer on the real sheet raised, and `--validate` reported **450 FAILs** of the form
`CT (1-7)='principle' out of range 1-7`.

Fixed in `resolve_answer()`: accepts a 1-based index OR a label in any casing/spacing/punctuation, plus a
0.85-ratio fuzzy match for typos, and **itemises every non-exact resolution in the output** (C16 — nothing silent).
The real sheet contained 31 typo'd answers (`casual mechanism`→`causal_mechanism` ×15, `normativ heuristic`→
`normative_heuristic` ×11, `escriptive model`→`descriptive_model` ×5) and 2 answers using a label that does not
exist (`leadership`, R027/R146). All are now reported individually. The scorer also now reports **per-axis blank
counts** as a datum (a reviewer holding the full menu and abstaining is evidence about the vocabulary, not a gap).

**Meta:** the tooling was validated against an *idealised* sheet (indices, complete) and not against a *real* one.
The lesson is recorded in the measurement report: validate instruments against the worst realistic input, not the
best.

---

## BUG-284 — the tooling kept reporting a RULED question as an open defect, and the ruler validator failed a decided sheet (2026-09-19)

**Severity:** MEDIUM (instrument vs ruling divergence; FIXED same day). **Status:** FIXED.

Class of defect: **the guard, the validator and the docs disagreed with the ruling for two days after the
ruling.** Three faces of one problem:

1. `pipeline/schemas.py::validate_discipline_domain` emitted
   `declared-axis-collision: … (known debt, decision pending)` for the `research methodology` /
   `research & methodology` pair — but D-271a had already RULED it a **DECLARED HOMONYM** ("change nothing").
   The guard was reporting a decided question as open work.
2. `scripts/build_ruler_sheet.py --validate` treated the same declared pair as a **FAIL**, so a correctly
   filled sheet could never validate; and it read answer cells as integers only, so the real sheet produced
   **450 spurious failures** (see BUG-283).
3. `governance/CONTEXT_INDEX.md` carried the same "decision pending" framing.

**Fix (all three):**
- the guard now emits `DECLARED: declared-axis-collision: … (<ruling text read from config>)`. The wording is
  read from `config/eval_integrity.yaml::label_axes.known_collisions[].decision` (C12 — the ruling is the single
  source, so the guard can never again paraphrase it wrongly by hand). The returned list stays **non-empty**, so
  every fail-closed call site still fails closed; the `DECLARED: ` prefix is what lets a caller distinguish a
  RULING from a DEFECT.
- the ruler validator now separates `problems` from `notes`: a declared collision is a **NOTE**, blanks are
  **ABSTENTIONS** (a datum about the vocabulary, excluded from both sides of the accuracy denominator), and
  typos are itemised. Result on the real sheet: **2 problems** (both `leadership`, a genuine vocabulary gap the
  reviewer hit at R027/R146), 6 declared notes, 51 abstentions, 31 typo resolutions.
- `resolve_answer()` moved to a **single definition** in the sheet builder (which owns the menus); the scorer
  imports it, so the validator and the scorer can never again disagree about what an answer means.

Verification: `tests/test_taxonomy_disjointness.py` updated for the new prefix and **205/205 tests pass**;
scorer output is byte-identical to before the refactor (regression-checked).

**Why this entry matters beyond the fix:** it is the **third** instance this session of the same failure class —
*an instrument asserting something the architecture had already decided* (BUG-275's withdrawn "66% noise" claim,
BUG-277's menu built from the wrong key, and now a guard contradicting its own ruling). The meta-lesson is
recorded in the forensic report: **when a ruling lands, the guards, validators, menus and docs that encode the
old state must be updated in the same commit** — otherwise the system spends the next days re-litigating itself.

---

## BUG-285 — the discipline/domain/depth filters do not constrain the hybrid result set (2026-09-19)

**Severity:** CRITICAL (silent retrieval-correctness defect; independent of label quality). **Status:** RESOLVED 2026-09-19 (0b/G12).

**RESOLVED:** facet predicate pushed into every leg (FTS, vector, keyword) via shared `_facet_conditions` +
asserted on the fused pool via `_matches_facet` (`pipeline/retrieve.py`). Constraint-violation rate
**0.5911 → 0.0000** over 470 probes (`scripts/measure_constraint_violation.py`).

`pipeline/retrieve.py::search_hybrid` (line 329) fuses three legs and applies the facet filters to **only one**:

| leg | facet params accepted |
|---|---|
| `search_fts(conn, query, limit, exclude_summaries, include_quarantine)` | **none** |
| `search_vector(conn, query, limit, …, vec_table)` | **none** |
| `search_keyword(conn, domain, discipline, depth, …)` | **all** — and it is called **only when a filter is present** (D2511) |

Then `results = [fb_map[fid] for fid in ranked_ids[:limit]]` — **no post-filter anywhere**. The optional
cross-encoder rerank (`BAAI/bge-reranker-v2-m3`, local CPU) reorders a `min(max(limit*5,20),100)` pool by query
relevance and **cannot restore the facet**, so it can promote a filter-violating row into the top-k.

**Measured on the live DB** (FTS + filtered-keyword legs, production RRF formula, k=60):

```
query='visual hierarchy design'   filter: discipline='typography'
  FTS leg      n=50   disciplines present: cultural design, decision making, design thinking, emerging,
                      human-computer interaction, information science, motion & time, psychology
  keyword leg  n=50   disciplines present: typography
  RRF top-10   -> 2 of 10 rows have discipline != 'typography'
```

The unfiltered vector leg makes the real ratio worse. Same defect on the `search_graph` path
(`retrieve.py:668` passes `discipline=discipline` straight into `search_hybrid`).

**Consequence:** `discipline=`, `domain=` and `depth=` are **advisory, not constraining**. Every filter-shaped
claim in this project — the 261/648 homonym row counts, the 907/1538 facet maxima, "discipline is the primary
exact-match facet" — describes a **label distribution**, never a **result set**. This also means the D-272b
axis-inversion premise had to be re-stated: discipline is not "an exact filter on an unreliable label", it is
"a nudge applied to one of three legs".

**Fix:** apply the facet predicate to **all** legs, or post-filter the fused pool before truncating to `limit`;
then re-run `pipeline/retrieval_benchmark.py`. **Adding legs to RRF before this fix amplifies the leak.**

---

## BUG-286 — the write guard destroys the label that D-271a ruled legal (2026-09-19)

**Severity:** CRITICAL (data-destroying; blocks repair R1). **Status:** RESOLVED 2026-09-19 (0c/G18).

**RESOLVED:** write guard split (`pipeline/schemas.py`) — `validate_discipline_domain()` (row guard, fails
closed on illegal labels only) vs `lint_discipline_domain_vocabulary()` (reports DECLARED collisions, never
rejects). `validate_discipline_domain('research methodology', …)` now returns `[]`; the 261 rows write clean.

`validate_discipline_domain` fires on the **discipline alone**, independent of the row's domains:

```
validate_discipline_domain('research methodology', ['brand identity']) -> non-empty
validate_discipline_domain('research methodology', None)               -> non-empty
```

It is enforced as a hard error at both write points: `stage4_merge.py:823` appends the flag to `errors` (the row
is **quarantined**), and `stage6_commit.py:402` returns False (the row is **REJECTED**, never inserted).

**D-271a ruled the opposite**: the research-methodology collision is a DECLARED HOMONYM, both labels stay
canonical, **change nothing**. So every *new* row classified `research methodology` dies at the write boundary.
The 261 rows in the DB predate the guard (D2620/D2626, 2026-09-17). **The ruling is not in force in code.**

**Why it is critical, not cosmetic:** `research methodology` is the **6th most reliable** label in the taxonomy
(0.83 human agreement). Proposed repair **R1** (closed-menu classification) offers the 61 canonical disciplines
including this one — so **R1 as specified would have every correct answer destroyed at the write boundary**, a new
silent failure mode introduced by a repair. R1 cannot ship without a config-driven exemption for declared
collisions. Human-owned: one line.

---

## BUG-287 — graph expansion re-admits the 3,250 quarantined rows it was meant to hide (2026-09-19)

**Severity:** HIGH. **Status:** OPEN.

```
graph_expand(): "SELECT fb_id, related_fbs, contradicts_fbs, prerequisite_fbs FROM fbs WHERE fb_id = ?"
                "SELECT fb_id, name, definition, domains, borp_score FROM fbs WHERE fb_id = ?"
```

**No `status` predicate on either query**, and `search_graph` passes `include_contradictions=True,
include_prerequisites=True` by default. Seeds are PASS-only; neighbours are not.

Because the edges were built from `discipline_overlap` / `domain_overlap` / `source_crossover` — i.e. **from labels
that were ~50% wrong during the generation window** — expansion simultaneously leaks NLI-unverified content into
the answer set and **propagates label error structurally**.

**This corrects BUG-278's framing:** the 40.7% is not "invisible", it is **inconsistently visible** (present iff a
PASS row points at it). The repair (R3) must therefore fix the *expansion* path too, or splitting the enum only
moves the inconsistency.

**Fix:** propagate the seed's status/verification policy into expansion, and return neighbours carrying an
explicit verification tier instead of silently mixing them.

---

## BUG-288 — the retrieval corpus is 11.1% of the knowledge, and `source_text` is not source (2026-09-19)

**Severity:** HIGH. **Status:** OPEN.

| what is searchable | chars | share of FB body |
|---|---|---|
| `definition` — the **only** text the 512d vector leg embeds | 1,765,980 | **11.1%** |
| mechanism + boundary + application + failure_mode + consequence + elaboration — **no vector, no FTS** | **14,152,908** | **88.9%** |
| `evidence_passages` — verbatim source, ≤5 quotes/FB, 7,990 distinct — **indexed by NOTHING** | 4,802,857 | — |

`fbs_fts` = `(name, definition, keywords, jargon)`. So the vector leg is blind to **88.9%** of every FB —
including `mechanism`, the field the entire FORM axis is *about* — and **4.8M chars of real source text are
unsearchable**.

`source_text` is **misnamed and misleading**: **100% of the 7,995 rows** contain
`"[book.md] " + definition` (median **300 chars**, min 138, max 695). It is the LLM synthesis again, prefixed with
a filename. No column at FB level holds source text.

**Fix:** (a) add the un-indexed body fields to FTS; (b) embed the full body rather than `definition` alone;
(c) index `evidence_passages` as a fourth RRF leg — all three recover text **already in the DB**.

---

## BUG-289 — `source_diversity` counts FILENAMES, not works: 29.1% of "convergence" is duplicate ingestion (2026-09-19)

**Severity:** MEDIUM-HIGH (it feeds the merge decision at stage 1.5). **Status:** OPEN.

Of the **2,597** rows with `source_diversity ≥ 2`, **757 (29.1%)** collapse to fewer distinct works once filenames
are normalised. The corpus carries **1,300 distinct book filenames** but **369 work-identities have more than one
filename** — e.g. `About Face The Essentials of Interaction Des…` vs `About Face. The Essentials of Interaction
Des…`; `Design The Key Concepts (D. J. Huppatz) (z-library.sk…)` vs `Design The Key Concepts (D. J. Huppatz).md`;
`Logo Design Love …` (two casings); `The impact of perceived complexity, deviation and co…` (twice).

**Why it matters:** `source_diversity` is the **merge criterion at stage 1.5**, and `is_convergent` (2,603 rows) is
the corpus's **headline quality claim**. Both are inflated by double-ingested books, so the pipeline merges on a
signal contaminated by the ingestion layer. Work-identity dedup is a **prerequisite** that no label repair touches.

---

## BUG-290 — two illegal values sit inside the retrieval facets (2026-09-19)

**Severity:** MEDIUM. **Status:** OPEN.

- **`emerging` is used as a DOMAIN on 744 rows and is NOT one of the 43 canonical domains.** The `domains` column
  holds 44 distinct values, **1 of which is not canonical** — the same class as BUG-273, and it sits inside a facet
  filter.
- **`discipline='emerging'` on 447 rows with `status='PASS'`** (757 rows total). The fallback value is therefore a
  member of the *exact-match* facet: `discipline='emerging'` returns 447 rows of "we don't know". The human
  reviewer also reached for `emerging` 9 times, so the fallback and the answer space are the **same string**.

**Fix:** `emerging` must be a *status*, not a facet value (or a declared, non-filterable sentinel).

---

## BUG-291 — a label-prefixed embedding table sits one argument from production (2026-09-19)

**Severity:** MEDIUM (latent; would create a self-reinforcing loop). **Status:** OPEN.

`contextual_embed.enabled: False`, so **production vectors are not label-poisoned** (hypothesis tested and
refuted). But the backfill has **already run**: the live DB contains `vec_fbs_ctx` (**7,995 rows**) holding
embeddings of `discipline | domains | name . definition`, and `pipeline/retrieval_benchmark.py:159` fuses it:

```
vec = search_vector(conn, query, limit=pool, vec_table="vec_fbs_ctx")
```

With labels at ~0.5 accuracy, pointing production at that table creates the loop: **wrong label → label-prefixed
embedding → retrieval prefers rows sharing the wrong label → the error is confirmed by retrieval and becomes
invisible.**

**Fix:** a guard that production may not use `vec_fbs_ctx` while any label axis is below its floor; and note that
re-embedding is mandatory after R1/R5 land regardless.

---

## BUG-292 — `fbs_fts` has an INSERT trigger only, and nothing checks the index (2026-09-19)

**Severity:** LOW (latent; hypothesis tested). **Status:** OPEN.

`sqlite_master` holds exactly one trigger: **`fbs_ai`**. An external-content FTS5 table (`content='fbs'`) needs the
insert **+ update + delete** trio, and the codebase does issue `UPDATE fbs` (`reclassify_merged_axis.py:314`,
`feedback.py:140/237`) and `INSERT OR REPLACE INTO fbs` (= delete + insert, `stage6_commit.py:409`).

**I predicted a stale index and measured it — the hypothesis was WRONG.** On a throwaway copy,
`INSERT INTO fbs_fts(fbs_fts) VALUES('integrity-check')` **PASSED**; row counts match (7,995 / 7,995 / 7,995) and
sampled FTS hits land on the correct rowids. Stage 6 rebuilds the index (`stage6_commit.py:239`), which is why.

Kept in the register because the *invariant is one line and missing*: nothing in the pipeline **detects** staleness,
so a future `UPDATE` outside stage 6 would corrupt keyword search silently. **Fix:** add the update/delete triggers
and run `integrity-check` at the end of stage 6.

---

## BUG-293 — mega-merges up to 244 sources for a single FB (2026-09-19)

**Severity:** LOW (no measurable label impact; merge-sanity risk). **Status:** OPEN.

883 rows carry >10 sources, **558 >20, 65 >50**, maximum **244**. Examples (all `status='PASS'`,
`origin='convergent'`): "Visual Data Structuring" (60 sources), "Brand As Reputation and Identity" (69),
"Typeface As Communicative Medium" (84), and a 244-source row. A claim that 244 books converge is almost certainly
an over-merge, and its `source_segments` list runs to 952 entries.

**Measured impact on labels: NONE detectable** — the ruler sheet contains only 8 rows at 21+ sources.
**Refuted hypothesis, recorded so it is not re-run:** I proposed that over-merged FBs become *unlabelable*. The
opposite holds — discipline-blank rate by source diversity: 1 source **24.1%**, 2 → 9.5%, 3–5 → 0%, 6–10 → 0%,
11–20 → 0%, 21+ → 12.5%; and `is_convergent` rows are 7% blank vs 24% for non-convergent. **Singletons are ~3×
more likely to be unlabelable** — which is consistent with the untraceable pocket being *exactly* the singleton
population (all 83 sheet rows flagged untraceable have `source_diversity = 1`).

---

## BUG-294 — the ruler's sampling frame is not crossed with `status`, so two estimands are conflated (2026-09-19)

**Severity:** MEDIUM (estimator validity). **Status:** OPEN.

The sheet sampled the **full KB** — 47.3% PASS rows in the sheet vs 59.3% in the KB — so stratum A mixes
retrievable and hidden rows. Re-measured restricted to `status='PASS'`:

| axis | all stratum A | PASS only | QUARANTINE only |
|---|---|---|---|
| content_type | 0.740, lift −0.010 | **0.891, baseline 0.891, lift +0.000** | 0.472, lift −0.028 |
| discipline | 0.494, lift +0.412 | 0.492, lift +0.393 | 0.500, lift +0.375 |
| extraction_type | 0.831, lift +0.472 | 0.852, lift +0.426 | 0.786, lift +0.321 |

Two different questions — *"is the stored label trustworthy across the KB?"* and *"is what I retrieve correctly
labelled?"* — are being answered by one number. **Fix:** cross the ruler strata with `status` and report both
frames; the scorer must never quote a single frame as if it were the answer.

## BUG-295 — The ruler compares stored-label ACCURACY to a human-provenance SHARE (MEDIUM, my instrument)

config/eval_integrity.yaml defines the floor as: *"Minimum share of labels that must come from a
HUMAN-authoritative source before the axis may be used as ground truth for a MODEL comparison...
A floor is a gate for the retrain, not a blocker for reading the axis."*

scripts/score_ruler_labels.py:136 reads that same key — floors = cfg.get("min_human_share") — and
line 184 uses it as the accuracy floor. The published FLOOR table therefore compares an ACCURACY
(0.506, 0.831, 0.740) against a PROVENANCE SHARE (0.60). Two estimands, one number.

Consequence: the STOPPED: decisive / CONTINUE: inside the margin verdicts and the 0.60 floor are
**void as stated**; verdict: FLOOR_UNRESOLVED for discipline is meaningless. What survives is the lift
over the constant-answer baseline (BUG-269, the project's own rule): content_type -0.010, discipline
+0.422, extraction_type +0.472.

Found by an external reviewer (temp/claude0080.md Q5); confirmed in source. Fix: report the
constant-baseline lift plus coverage and abstention bounds; express the floor separately as a per-axis
provenance share, computed from a provenance column that does not yet exist (BUG-298).

## BUG-296 — F-14 pocket retarget is statistically null; the claim is withdrawn (MEDIUM, my instrument)

D272g retargeted F-14 to ROLE on the strength of a pocket contrast (content_type 0.667 untraceable vs
0.816 traceable; extraction_type 0.860 vs 0.804). Re-measured with Wilson intervals:
content_type 47/83 = 0.566 [0.459, 0.668] vs 46/67 = 0.687 [0.568, 0.785]; extraction_type 55/67 =
0.821 [0.713, 0.894] vs 48/61 = 0.787 [0.669, 0.871]. **Neither contrast is significant** — the
intervals overlap heavily in both directions.

The action survives (do not re-derive FORM on 3,348 rows) but for a different reason: FORM is already
the best-measured axis, not because the pocket is clean. D272g must be restated, not silently kept.

## BUG-297 — "ROLE is decorative" is INVERTED: ROLE is the only serving gate (CRITICAL, my instrument)

BUG-280 / D6 / D272g all assert that content_type influences nothing. The opposite is true — see BUG-299.

## BUG-298 — No label carries human provenance; the floor gate is unsatisfiable (MEDIUM)

min_human_share cannot be evaluated on any axis because there is no provenance column: the fbs table
has primary_source (a book field) and NO content_type_source / discipline_source. The ruler key renders
those fields as null because the columns are absent, not because they are empty.

So by the config's own rule, **no axis is currently eligible as ground truth for a model comparison** —
exactly the state the config predicted ("the floor documents the target, not the state"). Direct
consequence for the fine-tuning question: S2/S4 must not be trained, distilled or swapped on the current
labels. A model fitted here would learn the script's gate (BUG-299) and the verdict of a verifier whose
own calibration record is P=0.647 R=0.386 F1=0.484 on 466 pairs.

## BUG-299 — The serving gate is a LABEL, not a verification verdict (CRITICAL, 2026-09-19)

scripts/apply_phase1_finalize.py:18

    status = 'PASS' if content_type == 'principle' else 'QUARANTINE'

and :163 writes it: UPDATE fbs SET content_type=?, depth=?, status=?, needs_human_review=?

The live DB matches that rule with 100% fidelity: **4,745/4,745 PASS rows are content_type='principle'
and 0/1,470 non-principle rows are PASS.** Nothing in pipeline/ links PASS to content_type — the gate was
established, and is still moved, outside the pipeline (apply_phase1_adjudication.py: "principle -> keep
principle, un-quarantine (status=PASS)"; repass_pair_agreed.py also un-quarantines on label agreement).

Measured against the persisted verification_results (populated on 7,995/7,995 rows):

| measurement | value |
|---|---|
| status disagrees with verification_results[factual].passed | **2,447 (30.6%)** |
| PASS rows whose own verification says passed=False | **1,941** |
| — NLI CONTRA majority (contradicted, served) | **138** |
| — NLI NEUTRAL (unverified, served) | **1,514** |
| — all evidence flagged non-evidence fragments (served) | **278** |
| — mechanism-quality FAIL (served) | 9 |
| — BUG-181#1 conversion artifacts (served) | 2 |
| QUARANTINE rows that are NLI ENTAIL majority (verified, hidden) | **506** |
| honest gate ablation (status := factual.passed) | PASS **4,745 -> 3,310** (net -1,435) |

The axis that decides what is retrievable is the axis with **lift -0.010 over a constant answer**, and
81.6% of the KB carries the gate value, so the gate admits almost everything and refuses nothing. None of
the three external reviews found this; Claude stopped one step short (it marked "where a non-principle
role becomes QUARANTINE" as UNVERIFIED). Human gate G17.

**RESOLVED 2026-09-19 (0a / G17):** `scripts/apply_serving_gate.py` is now the single writer for `status`,
derived from `verification_results[factual].passed` plus a typed `s5_reason` (entail | neutral | contra |
no_evidence | mech_fail | vacuous | evidence_contaminated), persisted in a new `fbs.s5_reason` column.
The four label scripts (apply_phase1_finalize, apply_phase1_adjudication, apply_phase0_relabels,
repass_pair_agreed) no longer write `status`. Rule + vocabulary live in `config/serving_gate.yaml` (C12);
CI invariant in `pipeline/serving_gate.py` + `tests/test_serving_gate.py` (14 tests). Applied in one
transaction (C6) with C13 backup + R14 manifest: PASS 4,745 → 3,310 (de-served 1,941; restored 506);
integrity_check ok; invariant 0 violations on the live DB.

## BUG-300 — The RRF keyword leg is query-blind, insertion-ordered and weighted equally (HIGH)

pipeline/retrieve.py:123-134: search_keyword accepts domain/discipline/depth/status/limit and **no query
text**. :363-370: it is called only when a facet is present. With borp_score at 0.0 for all 7,995 rows and
ranking.quality_score_enabled: false, its ORDER BY collapses to rowid order. :355-390 credits each of its
rows 1/(60+rank) — **equal weight to the best FTS match and the best vector match**. So a facet-bearing
query is answered in part by the first-N-inserted rows that carry the facet, and :411-415 then cuts the
rerank pool from that fused list, so a violator can be promoted. Found by temp/claude0080.md (D11,
"confirmed, worse"); verified in source. Fix is inside D273a (programme step 0b).

**RESOLVED 2026-09-19 (0b/G12):** `search_keyword` is now query-aware (accepts `query` and matches it
against name/definition/keywords) and the facet predicate is asserted on every leg + the fused pool.

## BUG-301 — Stage 5 computes a verification tier that Stage 6 has no column for (HIGH)

pipeline/stage5_verify.py computes epistemic_status in {corroborated, source-supported,
cross-source-unverified, speculative}, plus isor and verification_method. The live DB has **no
epistemic_status, no isor, no verification_method column** — stage6_commit.py's fixed column list drops
them. The tier vocabulary that R3/D272d asks for already exists and is discarded at the write boundary.
Also :898 stamps a literal — vfb["verifier_model"] = "DeBERTa-v3-large (D2322 calibrated, threshold
0.10)" — a C12/R14 violation that lies after any config change.

**RESOLVED 2026-09-19 (G19):** `pipeline/stage6_commit.py` now persists all four S5 tier fields —
`s5_reason`, `epistemic_status`, `verification_method`, `isor` — added to CREATE TABLE, the
`_migrate_add_column` list, and the INSERT (columns + placeholders + bound values). The live DB got the
3 missing columns via idempotent migration (71 columns, s5_reason already present from 0a). `verifier_model`
is now derived from config: `f"{S5_NLI_MODEL_LARGE} (threshold {S5_NLI_PASS_THRESHOLD})"` (C12).
`pipeline/schemas.py` VerifiedFB model gained the 4 fields. integrity-check CHECK 8 passes (71=71);
15 serving-gate tests green. This also fixed the latent 0a drift where `s5_reason` existed in the DB but
not in stage6's CREATE TABLE/INSERT.


## BUG-302 — Two further status writers remain outside the serving gate (MEDIUM, 2026-09-19)

D274h rules exactly one writer for `status`. After 0a/G17 (BUG-299), two scripts still write `status`
directly and are not routed through `pipeline/serving_gate.py`:

  1. `scripts/apply_dedup_marks.py:116` — sets `status='QUARANTINE'` for `duplicate_of` rows. This is a
     legitimate NON-label reason (dedup), but an ungoverned writer under D274h.
  2. `scripts/reinject_bug198_singletons.py:368` — `status = "PASS" if fact_passed else "QUARANTINE"`, a
     second copy of the serving-gate rule that can drift from the canonical implementation.

Also `pipeline/stage5_verify.py` writes `status` at the verification boundary (the canonical producer);
it should call `pipeline/serving_gate.derive_status()` so the rule has one implementation. Fix: route all
three through `pipeline/serving_gate.py` (declare the dedup rule in config), then extend the CI invariant
to assert no `UPDATE fbs ... SET status=...` outside that module.

**RESOLVED 2026-09-19:** all three now call `pipeline/serving_gate.derive_status()`; `apply_dedup_marks.py`
declares the `duplicate` reason in `config/serving_gate.yaml` and writes `s5_reason='duplicate'`; the
serving gate hard-quarantines `duplicate_of IS NOT NULL` rows (11 duplicates flipped back to QUARANTINE).

## BUG-303 — Stored extraction_type over-claims causal_mechanism; normative_heuristic 50% mislabeled (HIGH, 2026-09-19)

Inverted-key re-score (`scripts/rescore_ruler_inverted.py`, D-275a) over the reviewer's UPDATED FORM
labels (stratum A, n=99): the stored FORM labels are **25.3% wrong** [0.177, 0.346] — worse than the
16.9% error the old "0.831 accuracy" implied, because the reviewer's re-examination caught more errors.
Per-class stored reliability: descriptive_model 0.033, empirical_pattern 0.100, causal_mechanism 0.217,
**normative_heuristic 0.500**. The stored labels mislabel normative content as causal_mechanism (9 rows)
and descriptive_model (6 rows) — the S2 causal-overclaim bias (documented in RULER_MENUS AXIS 3) is now
measured in the stored labels, not just the prompt. Also: the reviewer's FORM update wrote "irrelevant"
in 4 cells (incl. 1 corrupted merge "descripirrelevanttive model") — a relevance judgement smuggled into
the FORM axis, concrete evidence for the missing relevance axis (R4 / F-E). Report:
`governance/ruler_form_inverted_20260919.md`. Action: do NOT re-derive FORM corpus-wide on these labels
(F-14 retarget withdrawn, BUG-296); the stored FORM error is a data defect resolved by R1/R2
re-classification, not a re-run of the current prompt.

## BUG-304 — Stored content_type over-calls principle; stored discipline 47% wrong with 8 zero-agreement slots (HIGH, 2026-09-20)

Full inverted-key re-score (`scripts/rescore_ruler_inverted.py --axis all`, D-276) over the reviewer's
FINAL labels (CT + DISC + FORM all now locked). Stored-label error rates: **content_type 0.353**
[0.281, 0.433], **discipline 0.474** [0.386, 0.564], **extraction_type 0.283** [0.216, 0.361].

- **CT:** the old classifier treats `principle` as the default — it under-calls `quarantine`
  (human 18 → stored 6) and `process_template` (human 16 → stored 9), pushing both into `principle`.
  This is the measured signature of the D-275b guardrail gap (step-count, not procedural intent).
- **DISC:** 8 slots have ZERO stored agreement (n≥2): design psychology 0/5, cultural studies 0/4,
  risk management 0/4, privacy & surveillance, political economy, visual perception, finance,
  cultural design. The old alias-map extraction silently discards this content into `emerging`.
  Group-level near-miss: exact-canonical 0.430 → same-group 0.271 (29 labels in a different group).

Artifacts: `governance/ruler_inverted_20260920.{md,json}`, `governance/anchor1_frozen_20260920.{md,json}`.
Action: do NOT re-run the current S2/S4 prompt to "fix" these labels — the defect is the free-generation
prompt + alias map (root cause stage4_merge.py:345/468/500, ONTOLOGY_FORENSIC §). Fix is R5 (re-derive +
bound weak slots — D-277, never demote first) → R1 (closed menu + menu_hash) → R2 (definition NLI).
Provenance columns (`*_source`) must
exist before any corpus-wide re-classification so `min_human_share` is satisfiable.

## BUG-305 — R2 definition-anchored NLI emits ~100% CONTRA on the principle class — the meter is broken (CRITICAL, 2026-09-20)

Exposed while testing the D-282 depth-vs-role fix (user asked: "test that specialized/domain-depth
principles won't drift"). Ran the actual R2 NLI (`_nli_pair_scores`, DeBERTa-v3-large, MPS) with
premise = each object's DEFINITION and hypothesis = the label's CLOSED-MENU definition, over all 30
ceiling-sheet rows + 3 synthetic pure-specialized principles ("In chess, control the center…",
"typography leading ≈1.2–1.5× font size", "a rule-of-thumb is still a principle at any scope").

Result: the `principle` hypothesis returned **entail 0.00–0.05 / contra 0.97–0.99 on every object**,
including the synthetic specialized principles. ROOT CAUSE: the content_type hypothesis is a
CATEGORY META-DEFINITION ("a PRINCIPLE is a single self-contained epistemic claim you KNOW/APPLY…"),
and NLI entailment cannot test category membership — a specific rule's definition never *entails*
the meta-definition of its own category (register mismatch: instance vs category). This is a D-281
design flaw, NOT a D-282 regression.

CONSEQUENCE: `_CONTRA_DOMINANT_THRESHOLD = 0.5` (scripts/definition_nli_verify.py) would flag ~100%
of principles as "hard mislabel"; the pending R2 corpus NLI run would be a broken meter (universal
false contra). Do NOT run R2 corpus-wide until fixed. The discipline/domain axes may partially
survive (their taxonomy `definition`s are closer to content-paraphrases), but content_type cannot.

FIX DIRECTION: (a) role classification must use Mechanism A (content_type_decision_procedure), not
NLI; or (b) replace the hypothesis with a PARAPHRASEABLE CONTENT CLAIM per role (e.g. "This text
describes a reusable rule that can be applied across situations" for principle) so a genuine
instance ENTails it; or (c) restrict R2 NLI to discipline/domains and drop content_type from the
NLI axes. Decision pending (D-281 revision).

**RESOLVED (2026-09-20, D-283 + D-284):** the universal-contra was NOT fundamental — it was the OLD
principle meta-definition's self-negating phrasing ("NOT a procedure you EXECUTE") tripping contra on
imperative-form principles. The new r5 principle definition (D-283) dropped principle-class false-contra
~1.0 → 0.27 (3/11). The A/B harness (D-284) then showed paraphrase (arm C) is the better mislabel
detector (91% vs 55% wrong-contra) with comparable false-contra (0.233 vs 0.267). Verdict: KEEP NLI on
content_type (reject drop-CT), adopt paraphrase (arm C), and further sharpen growth_edge (0.40
false-contra in both arms). Adoption = rewrite definition_nli_verify.py hypothesis construction + stamp
an r5 hash on the R2 report (BUG-307).

## BUG-306 — Single-coder ceiling κ is contaminated: same-person + ruleset mismatch (HIGH, 2026-09-20)

The 30-row second pass is complete, but the κ is NOT a clean human-vs-human ceiling. κ(coder1,
coder2): **CT 0.333 (16/30), DISC 1.000 (23/23), FORM 1.000 (26/26)**. Three contaminations:

1. **Same person** — both sheets are stamped `reviewer=human`. D-280 requires a second INDEPENDENT
   human; what was measured is intra-rater test-retest, an UPPER bound on the inter-rater ceiling.
2. **Ruleset mismatch** — coder 1 (RULER_BLIND_SHEET, 2026-09-17) predates D-275b/D-282; coder 2
   (2026-09-20) used the D-275b procedure. The CT κ partly measures a RULES CHANGE, not rater noise.
3. **Coder-1 bug leakage** — coder 1's 12/30 quarantine labels likely encode the pre-fix "3+ domains"
   conflation (R147 "Randomness in Data Measurement" and R148 "Professional Development Through
   Studio Experience" — the latter's own definition literally opens "A principle…"). Coder 2 re-labels
   them principle / noise_drop.

Additional signal: **17/30 rows carry "not sure if…" uncertainty notes** — direct evidence the CT axis
(esp. principle ↔ growth_edge ↔ process_template) is under-specified in the menu, independent of the
depth fix. CT drift signature: principle→growth_edge ×4, principle→process_template ×2,
quarantine→process_template ×2; only 1 principle→quarantine (R133, borderline). The depth axis is NOT
the source of CT disagreement.

FIX: re-measure the ceiling with (a) a genuinely different second human, (b) BOTH coders bound by the
post-D-282 menu, (c) coder 1 re-scored on the 30 rows under D-275b/D-282 first. Until then treat
κ=0.333 as a LOWER bound on CT ceiling and do NOT quote it as the human ceiling.

## BUG-307 — R2 verification provenance gap: r5 override set is unstamped; closed_menu.py has a dead constant (HIGH, 2026-09-20)

Forensic audit of the R2/R5/R1 chain found two coupled issues:

1. **`pipeline/closed_menu.py:29` declares `_R5_REPAIR_PATH` but never uses it** — a dead constant
   (C19). The header comment in `config/r5_slot_repair.yaml` claimed "closed_menu.py (R1) and
   definition_nli_verify.py (R2) consume it", but closed_menu.py does NOT read r5_slot_repair.yaml;
   only definition_nli_verify.py does (via `_load_r5_definitions`). Header comment fixed; the dead
   constant remains (remove or wire it).
2. **`menu_hash` does NOT include the r5 overrides**, and the R2 report (`r2_definition_nli_20260920.json`)
   does not stamp WHICH r5 override set produced its hypotheses. Consequence: an FB verified under the
   D-283 sharpened definitions (principle false-contra 0.27) is indistinguishable, by provenance, from
   one verified under the pre-sharpening definitions (false-contra ~1.0). This is a future-tax /
   provenance gap: the r5 overrides change verification behaviour but leave no hash trail.

FIX: (a) stamp an `r5_hash` (sha256 of the r5 override set) on the R2 report alongside `menu_hash`;
(b) once the user ratifies the D-283 boundaries, FOLD the principle/growth_edge/quarantine/process_template
overrides into config/content_types.yaml so they become part of `menu_hash` and the override layer collapses;
(c) remove the dead `_R5_REPAIR_PATH` constant from closed_menu.py.

## BUG-308 — D-282's "3+ domains" fix was incompletely applied: the role test persisted in 8 more files (HIGH, 2026-09-20)

The user re-flagged that the quarantine exclude still carried a "3+ domains" reference, and a full-repo
sweep proved the D-282 role-conflation fix had been applied ONLY to `config/r5_slot_repair.yaml` +
`config/content_types.yaml`, leaving the "a filter across 3+ domains" role test live in the PROMPT and
FORM layer (a second, independent source of the same drift):

- `pipeline/stage2_extract.py` (Q3 prompt), `scripts/build_ruler_sheet.py` (ruler "trap" text),
  `scripts/build_joint_vote_set.py`, `scripts/deepseek_frontier_audit.py`, `scripts/reverify_content_type_108.py`
- `governance/RULER_MENUS_20260917.md`, `content_type_adjudication_form_unlabeled_217.md`,
  `content_type_frontier69_remaining52_form.md`, `content_type_human_review_FORM.md`,
  `content_type_frontier69_form.md`
- plus a leftover "(1/2/3+ domains)" parenthetical in the r5 quarantine + principle definitions, and the
  dead `depth_test_domains_threshold: 3` field (nothing reads it).

FIXED: every instance rewritten to "a self-contained transferable filter at ANY scope (depth is the
separate axis, never a role test)"; `depth_test_domains_threshold: 3` removed. The only remaining
"3+ domains" occurrences are DEPTH-axis and correct (schemas.py:442 depth hierarchy, schema_accessor.py:476
source-diversity score, stage6b_anytype_push.py:593 cross-domain folder).

LESSON: a config-level fix is not complete until the SAME rule is swept out of every prompt string and
form doc that re-encodes it. The prompt/doc layer was a second source of the identical drift D-282 fixed
in config only.

## BUG-309 — 11 NON-core raw-alias cross-listings remain (MEDIUM, 2026-09-20)

After D-285's alias-conflict fix (scripts/fix_d285_alias_conflicts.py) resolved every cross-listing
among the 5 core disciplines, a full-sweep found 11 residual cross-listings OUTSIDE the D-285 scope.
A raw alias must map to AT MOST ONE canonical (schemas.py synonym index is last-write-wins → ordering-
dependent drift). The 11:

  color psychology                -> [color theory, visual perception]
  computational models of social life -> [complex adaptive systems, computational physics & simulation]
  computer vision                 -> [machine learning, visual perception]
  decision science                -> [decision making, operations research]
  economic theory                 -> [economics, political economy]
  large language models           -> [generative ai, machine learning]
  microeconomics                  -> [economics, political economy]
  simulation                      -> [computational physics & simulation, operations research]
  software architecture           -> [software engineering, systems engineering]
  strategic decision making       -> [decision making, strategic thinking]
  systems design                  -> [systems engineering, systems thinking]

Plus 2 adjacent misplacements (not cross-listings, but wrong per D-285):
  - rhetoric / Rhetoric          in behavioral economics (persuasion-flavored → recommend design
    psychology, but alias_map.yaml routes "rhetorical studies"/"rhetorical theory" -> communication
    theory — needs a decision)
  - behavioural economics+persuasion  compound raw string in behavioral economics (head-wins? split?)

NOT fixed by fiat: several are legitimate subsumption (computer vision spans ML + visual perception;
political economy legitimately studies economic theory). Needs a dedicated batch-ratification.

## BUG-307 — RESOLVED 2026-09-20

The dead `_R5_REPAIR_PATH` constant in pipeline/closed_menu.py was removed, and the R2 report now
stamps BOTH `menu_hash` and `r5_hash` (sha256 of the full r5 override set) alongside the per-FB scores
(D-286). An FB's R2 verification is now traceable to the exact override set that produced its hypotheses.

## BUG-308 — follow-up (second instance found + fixed 2026-09-20)

The BUG-308 sweep (config fix not propagated to every layer) found a SECOND instance: the D-283
principle fix removed the "NOT a procedure you EXECUTE" self-negating phrase from r5_slot_repair.yaml
but NOT from content_types.yaml's principle.description — which feeds the closed MENU. A naive fold
would have re-introduced BUG-305 universal-contra. Fixed: content_types.yaml principle description now
uses the epistemic STATUS discriminator ("SETTLED knowledge — not an open question or unverified
correlation"). This is exactly the BUG-308 lesson: a config fix is not complete until the same rule is
swept out of every layer that re-encodes it (r5 override + canonical config + prompt + form).

## BUG-309 — UPDATE 2026-09-20 (7/11 unambiguous resolved; 4 ambiguous + 2 misplacements → batch)

The BUG-309 sweep resolved the 7 unambiguous non-core cross-listings via `scripts/fix_bug309_unambiguous.py`
(economic theory + microeconomics → economics; software architecture → software engineering; systems design →
systems engineering; strategic decision making → strategic thinking; large language models → generative ai;
computer vision → machine learning). 4 genuinely-ambiguous cross-listings (color psychology, computational
models of social life, decision science, simulation) + 2 misplacements (rhetoric, behavioural
economics+persuasion) are left for human batch-ratification → `governance/bug309_batch_ratification.md`.
Flagged: `macroeconomics` sits ONLY under political economy (not cross-listed) — same exclude-logic → economics.

## Arm C adopted (D-284) 2026-09-20

`scripts/definition_nli_verify.py` now builds the content_type hypothesis from a per-role PARAPHRASE content-
claim, sourced from `config/content_types.yaml` `nli_paraphrase` (single source; `r2_ab_harness.py` reads the
same block — no second hardcoded copy). discipline/domains keep the definition hypothesis. The R2 report
stamps `content_type_hypothesis: paraphrase` + `menu_hash` + `r5_hash`. FUTURE-TAX: the r5 content_type
`definition` overrides (principle/growth_edge/process_template/quarantine) are now UNUSED for the content_type
hypothesis (arm C bypasses them) — they remain only for r5_hash provenance; collapse in the full-r5 fold.

## BUG-306 — re-measurement prepared 2026-09-20

Fresh blind sheet `governance/CEILING_REMEASURE_BLIND_SHEET_20260920.csv` (labels blanked) + protocol
`governance/bug306_remeasure_protocol.md`. Blocked on a genuinely different second human coder (not "human",
not the first-session reviewer). κ CT 0.333 remains a LOWER bound until re-measured.

## BUG-309 — RESOLVED 2026-09-20 (M1 rulings applied; discipline raw-alias cross-listings → 0)

User M1 batch-ratification applied via `scripts/fix_m1_rulings.py`:
  A1 Color Psychology → color theory (drop from visual perception)
  A2 Computational Models of Social Life → complex adaptive systems (drop from comp phys & sim)
  A3 Decision Science → decision making (drop from operations research)
  A4 Simulation → computational physics & simulation (drop from operations research)
  B1 Rhetoric/rhetoric → linguistics (drop from behavioral economics)
  B2 persuasion is design psychology → split 'behavioural economics+persuasion' compound (keep
     'behavioural economics' head in behavioral economics; persuasion already in design psychology)
  C  macroeconomics → economics (drop from political economy)
Result: **0 raw-alias cross-listings remain in the discipline axis.**

## BUG-306 — BLOCKED (no second human) 2026-09-20

The re-measurement is impossible: the user is the only human ("there are just me, no second person").
A second pass by the same person reproduces the same labels (intra-rater, not inter-rater), so κ CT
0.333 stays a CONTAMINATED intra-rater upper bound — there is no way to measure a true human ceiling.
CONSEQUENCE: pivot from "inter-rater κ" to "pipeline-vs-user agreement" (the user's own labels ARE the
single ground truth). The R2 meter + per-slot κ vs ANCHOR-1 can still run — they measure whether the
pipeline agrees with the user, which is the meaningful question for a solo project.

## BUG-310 — NEW: 37 DOMAIN raw-alias cross-listings (MEDIUM, 2026-09-20)

The BUG-309 sweep covered only the DISCIPLINE axis. A follow-up sweep of the DOMAIN axis found 37
raw-alias cross-listings (a raw string listed under 2+ domains). The discipline exclude-list signal
does NOT transfer cleanly to domains (e.g. it would wrongly route 'programming' → engineering practice
when it is clearly code & computation). Full list + recommendations → `governance/bug310_domain_crosslistings.md`.
Needs batch-ratification (same as M1). alias_map.yaml verified: 0 non-canonical targets.

## BUG-310 — RESOLVED 2026-09-20 (all 37 domain cross-listings applied → both axes 0)

User "approve all". `scripts/fix_bug310_domains.py` removed each cross-listed raw alias from its drop
domain (surgical, section-aware, case-insensitive). A dedup bug (kept case-variants) was caught by the
post-write verification and fixed; re-run confirmed. **Result: 0 raw-alias cross-listings on BOTH the
discipline AND domain axes.** The synonym index is now conflict-free.

## R2 arm C smoke-tested 2026-09-20 (works; full corpus run blocked on a missing checkpoint)

`scripts/definition_nli_verify.py --input probe_output/stage5_fbs.jsonl` ran clean: 40 FBs, 95 label
pairs scored, 14 contra, 0 inference errors; report stamps `content_type_hypothesis: paraphrase` +
`menu_hash cac6e695…` + `r5_hash 04fe615a…`. DeBERTa-v3-large loads on MPS. CAVEAT: the probe corpus has
**0 content_type labels** (all `None`) and 26/40 `discipline: emerging`, so the run exercised only the
DOMAIN definition arm — the content_type paraphrase arm is code-correct (unit-verified) but not yet
corpus-validated.

## BUG-311 — NEW: the full stage5 checkpoint is MISSING (HIGH, 2026-09-20)

`pipeline_paths.STAGE5_CHECKPOINT` = `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl` — the file
does NOT exist. Only 12 `.bak_*` backups remain (~100 MB each, Sep 3–4, most recent
`checkpoint.jsonl.bak_20260904_152319`). The R2 corpus NLI run cannot run against the full corpus until
the checkpoint is restored from backup (or stage5 is re-run to produce a fresh one with content_type
labels). This is a data-integrity gap: the live corpus checkpoint was lost, leaving only pre-step backups.

## BUG-311 — RESOLVED (checkpoint restored) 2026-09-20

The live stage5 checkpoint was missing. Restored crash-safe (tempfile → fsync → os.replace, C6) from
`checkpoint.jsonl.bak_20260904_152319` (sha256 2c206a255a41eb8fa42122cb8c68e0e0b5395da280c1d9c840be8e6a06188d43,
7995 FBs, 0 malformed lines). `--selfcheck` clean (menu 62 disc / 44 domains / 8 ct; r5 4 ct + 9 disc; 7 paraphrase).
⚠️ CAVEAT: the restored checkpoint is STALE — see BUG-312.

## BUG-312 — NEW: three divergent label snapshots (HIGH, provenance drift, 2026-09-20)

The committed state has diverged into THREE label snapshots with no single JSONL source of truth:
- stage5 checkpoint (Sep 4, restored) — STALEST
- stage4 checkpoint (Sep 11) — 1112/7995 (13.9%) discipline + 2395/7995 (30.0%) domain diffs vs stage5
- maxwell.db (Sep 19 21:47) — FRESHEST; 231/7995 (2.9%) discipline + 353/7995 (4.4%) domain diffs vs stage4
The DB reflects the post-repair taxonomy (M1/D-285/BUG-309/BUG-310 re-derivations); both checkpoints carry
pre-repair labels. No JSONL checkpoint matches the DB. Consequence: R2 corpus NLI runs on stage4 (option B)
≈ 97%/96% aligned with the DB, but a DB→JSONL export + re-meter is required for exactness. Forensic-audit
findings (2026-09-20): compile 0 fails; YAML 0 fails; menu_hash MATCH cac6e695…; 0 cross-listings (both axes);
nli_paraphrase single-source; no secret leak (sk-maxwell-local is a local placeholder); config-code drift 0.
Future-tax: (a) r5 content_type overrides (4) now dead — bypassed by arm C paraphrase; (b) 12 .sh + 1 tool
carry hardcoded paths (integrity_check #14 FAIL, pre-existing).

## R2 corpus NLI — DONE 2026-09-20 (arm C, full corpus, option B)

Ran `definition_nli_verify.py` over the stage4 checkpoint (7995 FBs) in ~27 min (19 pairs/s on MPS):
**31,525 label-definition pairs scored, 5,438 contra (17.3%), 0 inference errors.** Per-axis contra:
discipline 657/7234 (9%), domains 3059/16296 (18%), content_type principle 1722/7995 (21%). Stamps
correct (menu_hash cac6e695…, r5_hash 04fe615a…, content_type_hypothesis=paraphrase). Output →
`governance/r2_definition_nli_20260920.json`. See BUG-313 for the headline anomaly.

## BUG-313 — NEW: cognitive science 94% contra (126/133) after D-285 sharpening (HIGH, 2026-09-20)

The R2 arm-C meter found the D-285 cognitive-science definition ("HOW the mind works … as pure cognition,
with NO design, persuasion, or economic-application intent") **contradicts 126/133 (94%) of the FBs still
labelled cognitive science**. The contradicted FBs are design/learning/creativity-applied content (e.g.
"Catholic Reading for Design Inspiration", "Extended Skill Acquisition Investment", "Affordance As Action
Potential", "Reframing Creative Constraints") — NOT pure cognition. The definition moved (D-285) but the
corpus labels did not, so these 133 are now mislabelled under the sharpened definition. The OTHER core
disciplines are clean (psychology 0/906, behavioral economics 12/238 = 5%, design thinking 31/246 = 12%),
so this is a SPECIFIC cognitive-science definition-vs-corpus mismatch, not a general D-285 failure. Needs a
human decision: widen the cognitive-science definition (re-admit applied cognition/learning) OR re-label the
133 FBs (→ design cognition / psychology / design psychology). → D-289.

## BUG-313 — RESOLVED (Option A: definition de-negated) 2026-09-20

User chose Option A (widen the definition). `config/r5_slot_repair.yaml` + `config/taxonomy_v5.yaml` cognitive-science definitions de-negated in lockstep: removed "with NO design, persuasion, or economic-application intent" + "as pure cognition … in itself", keeping the positive boundary "how the mind works — perception, memory, attention, reasoning, language, and learning". Menu re-rendered (menu_hash cac6e695→73597ee2). Targeted re-score: **cognitive science contra 126/133 (94%) → 6/133 (4%)** — confirms the negative clause was the root cause (NLI-negation artifact, same class as BUG-305), not genuine mislabeling. Full r5 collapse also executed: 4 non-core discipline defs folded into taxonomy_v5.yaml; dead r5 content_type overrides dropped.

Full R2 v2 re-run (post-fix, 2026-09-20): 7995 FBs, 31,525 pairs, **5,318 contra (was 5,438)**, 0 errors — the 120-contra drop is exactly the cognitive-science fix. Per-axis: discipline 537/7234 (7%), domains 3059/16296 (18%), content_type 1722/7995 (21%). Core disciplines: cognitive science 6/133 (4%), psychology 0/906 (0%), behavioral economics 12/238 (5%), design thinking 31/246 (12%). ⚠️ design psychology 5/6 (83%) — tiny sample (only 6 FBs via the new persuasion→design-psychology alias); watch once the slot grows. → governance/r2_definition_nli_20260920_v2.json.

## BUG-314 - Frozen ruler csv_sha256 provenance mismatch (MED, 2026-09-21)

governance/anchor1_frozen_20260920.json declares csv_sha256=4d0c856a... (hash of
RULER_BLIND_SHEET_20260917.csv at freeze time 13:15). The live sheet - and its Sep-20 12:38 backup,
byte-identical - now hash to 38323192...: the sheet was rewritten at 20:33, i.e. reverted to the
pre-freeze serialisation. Row-level audit of all 150 item_ids: **zero substantive label drift** -
every apparent difference is normalisation ("tool instruction" vs tool_instruction: 43 ct + 147 form
space/underscore diffs; casual->causal, normativ->normative; blank cell vs null on the 34 unlabelled
discipline rows). Net: cosmetic drift, but byte-level verification of the frozen artifact now FAILS
CLOSED, so any consumer that hash-checks the sheet before scoring aborts. Fix: re-stamp csv_sha256
from current bytes (or freeze the normalised projection) + ship the normalisation map. Label impact: none.

## BUG-315 - Hardcoded oMLX API key fallback (LOW-MED, C12, 2026-09-21)

pipeline/model_lazyload.py:50 hardcodes OMLX_API_KEY = "sk-maxwell-local", duplicating the single
source owned by pipeline/pipeline_paths.py (D2552) that unloader.py / dspy_trainer.py already import.
Fix: import from pipeline.pipeline_paths.

## BUG-316 - goose main-loop model is the known-bad agentic model (MED, Phase 3 risk, 2026-09-21)

After the D-297 provider switch, ~/.config/goose/config.yaml providers.maxwell_omlx.model is
Qwen3-Coder-30B-A3B-Instruct-MLX-4bit - the model driving goose MAIN loop. DELEGATE-002 documents
this model as single-shot-only (monotonic decode collapse ~6.8 -> 0.4 tok/s as context grows;
~50-token stubs). D-295 asked for the provider switch + temp 0.0, not a collapse-prone code model as
the driver. Not changed unilaterally (it would swap the running session driver) -> D-299.

## ANCHOR-1 note (not a bug): out-of-vocabulary human tokens are normalisation debt only

3 human tokens miss config/taxonomy_v5.yaml: media & entertainmen, product desig, business operation
(truncation / singular). emerging (rows 17, 19, 43) is NOT one of them - it is the documented
catch-all (taxonomy meta.catch_all_discipline) and is used on both sides, so it is legal.
## BUG-317 - Bake-off arm layer silently ran the NLI arm on CPU (MED, own wiring, 2026-09-21)

First run of the DeBERTa arm measured 24.5 s/row (61 slots) -> 61 min for 150 rows, because
_nli_scores never moved the model/inputs to an accelerator. After adding config-driven device
selection (bakeoff.device: auto = mps > cuda > cpu, C24) and padded batches (bakeoff.nli_batch_size),
the same arm runs at 0.40 s per 16 hypotheses: 5 rows in 7.1 s -> ~3.6 min for the full 150 rows
(17x faster). Lesson: an arm that silently degrades to CPU is a HIDDEN FAILURE - it does not error, it
just makes the benchmark look prohibitively expensive. Device is now declared in config, not implicit.
## BUG-318 - Bake-off: config JSON braces killed the LLM arm + non-atomic artifact (HIGH, own wiring, 2026-09-21)

Two coupled defects surfaced when the qwen3coder arm started: (a) the config prompt template contains a
literal JSON example ({"choice": ...}) and was rendered with str.format(), which read {"choice"} as a
format field -> KeyError: '"choice"' -> the arm died instantly; (b) the artifact was written once, AFTER
the whole arm loop, so the crash also DISCARDED the completed DeBERTa arm (150/150 rows, ~4 min of
compute) and left only the stale constant-arm artifact on disk. Fix: named-token render() (no
str.format on config text) + per-arm checkpoint write. Lesson (C23 resilient-by-design): a benchmark
harness that loses finished work to a later crash is a hidden failure, not an inconvenience.
## BUG-319 - qwen3coder arm abstains 116/116 (HIGH, hidden failure, 2026-09-21)

The LLM arm decided zero rows: abstain_rate 1.0, error_rate undefined. Any parse failure that is
converted into an abstention is INDISTINGUISHABLE from a legitimate "I don't know" - the arm looks
honest while being dead. Report layer now marks it INVALID (decided < 50%), but the parser must
separate "model abstained" from "we failed to read the model". Fix pending: inspect raw responses.

## BUG-320 - No degenerate-arm guard: a collapsed arm could be read as a tie (HIGH, fixed 2026-09-21)

Nothing in the harness flagged an arm that reproduces the baseline. The DeBERTa zero-shot menu arm
scored error 0.931 - numerically identical to the constant baseline (108/116 errors, error-set
Jaccard 0.862), i.e. F-17 in its strongest form: on this framing the incumbent adds no signal.
Fixed by scripts/bakeoff_report.py (local recomputation + DEGENERATE flag + live-vs-baseline verdict).

## BUG-321 - Harness persisted labels only, discarding per-row margins (MED, fixed 2026-09-21)

main() wrote res["predictions"] = {k: v[0]} - the confidence margin was thrown away, so no calibrated
abstention curve and no failure audit could be derived from the artifact. Fixed: margins persisted.
## BUG-322 - Report verdict compared every arm to the CONSTANT floor, so the incumbent "passed" (MED, fixed 2026-09-21)

v1 of the report layer measured candidates against the constant baseline only. That made the incumbent
itself report "ADOPT (gain 45.7 pp)" - vacuous, because the incumbent IS the deployed configuration.
Fixed: D-300 v2 compares candidates against the incumbent arm (config: bakeoff.report.incumbent_arm),
with the constant baseline demoted to a triviality floor. Lesson: a metric whose reference is not the
deployed configuration can only ever produce flattering verdicts.
### BUG-319 - ROOT CAUSE FOUND and FIXED (2026-09-21, HIGH -> CLOSED)

The 116/116 abstention was NOT a parse problem and NOT the model refusing: the arm built
OMLX_URL + "/chat/completions" while OMLX_URL = http://localhost:11435 (no /v1), so every call returned
HTTP 404 and the exception handler recorded an abstention. After adding the diagnostic reasons
(ok / model_abstained / unresolved_choice / parse_error / http_error) the first re-run printed
[[http_error_404, 60]] - one line replacing a mystery. Fixed config-first: bakeoff.omlx_path = /v1/chat/completions.
Audit: every production caller (pipeline/omlx_call.py, model_lazyload.py, omlx_wired_stress.py,
dspy_trainer.py, scripts/arm4_omlx.py, benchmark_s4_quant_ab.py) already uses /v1 - the defect was
contained to the harness, no production cascade. Proof after fix: 10/10 rows decide ("ok"), labels
e.g. computational geometry, design thinking.
## BUG-323 - Harness overwrote its artifact, silently destroying an arm already measured (MED, fixed 2026-09-21)

main() wrote a single artifact per run, so running --arm pairwise after --arm qwen3coder erased the LLM
arm; the report then saw no incumbent and fell back to the CONSTANT floor, re-printing a flattering
"ADOPT". Two holes, one cause. Fixed: (a) merge-at-write in the harness (earlier arms survive), and
(b) the report now WARNS loudly when the incumbent arm is absent instead of quietly re-basing the verdict.
## BUG-324 - Arbitration script counted UNLABELLED rows as errors (MED, fixed within minutes 2026-09-21)

First run reported incumbent error 0.593 instead of the known 0.474 because the loop iterated every row of
the frozen key - the 34 rows with no human discipline label satisfied "pred != None" and were silently
counted as failures. A 25% inflation of the error rate, produced by a missing guard rather than a missing
label. Fixed: only rows carrying a human label may enter an error count. Lesson: every error metric needs an
explicit "is this row scoreable?" predicate; absence of truth is not evidence of error.

## BUG-325 (MED — FIXED 2026-09-21): normalisation map leaked across axes. `load_vocab()` merged the owner-approved DOMAIN surface variants (config/normalization_map.yaml, D-307) into the SHARED alias dict used to normalise every axis, so a domain entry (`human-computer interaction` -> `human computer interaction`) also rewrote DISCIPLINE cells on rows 25/46 and depressed discipline kappa from 0.4395 to 0.4051 for a purely cosmetic reason. Caught by the ablation audit (S2), not by any test. Fix: separate `dom_alias` used only for domain tokens; discipline axis is provably unchanged (re-ran: 0.4395 / error 0.5254). Guard for the future: the map is domain-keyed, so it must never be applied to a vocabulary that shares token space with another axis.

## BUG-326 (MED - BLOCKED 2026-09-21): the repair's TARGET NUMBERS do not reproduce on the live DB
Whole-corpus deterministic meter (`scripts/audit_full_corpus_labels.py`, knowledge pipeline/maxwell.db, 7,995 rows):
403 FBs whose `discipline_raw` has a canonical-equivalent but no mapping (BUG-150 class taxonomy gap), 354 emerging
FBs with EMPTY `discipline_raw` (reclass targets), 1 canonical + empty raw (D2378), 147 FBs with the SAME label on
both axes (most: design studies 41, visual communication 12, business strategy 10 - D2422/BUG-197 disjointness),
703 FBs with no/emerging-only domain, 0 unknown labels. Separately: the record-level claim "the pipeline never emits
ai & agents / brand identity / ..." was FALSE and came from the 60-row contra sample; corrected in D-308/D-310 and
recorded here as a process bug (no whole-corpus measurement before a decision claim). Fix order: raw->canonical
coverage, then both-axes, then the 703 domain-less rows; all three are deterministic repairs gated on a gemma-4-E4B
review of the repair script first (R5).

## BUG-327 (LOW - CLOSED INVALID 2026-09-21): "per-row margins are not persisted" was a probe error, not a defect
The pairwise arm DOES persist predictions[fb_id] = [label, margin] (harness line 80: entailment - contradiction); the
earlier probe returned 0 rows because it looked for dicts instead of 2-element lists (same shape in both arms). The
calibrated-abstention curve was therefore re-derived from the frozen artifact without re-running a model. Lesson: print
the artifact shape before declaring a signal missing - this is the second false "missing signal" claim this session
(the first was the assignment claim, D-310). Both are now recorded as process bugs.

## BUG-328 (HIGH - CLOSED 2026-09-21, landed 32cb9fa): 18 production/script files were modified-but-UNCOMMITTED vs HEAD (silent-revert risk)
`git diff --stat HEAD -- pipeline/ tools/ scripts/` = 18 files, 418 insertions / 193 deletions, none of it committed:
pipeline/retrieve.py (+167), pipeline/schemas.py (+117), pipeline/stage6_commit.py (+36), pipeline/stage4_merge.py (+21),
pipeline/stage5_verify.py (+15), pipeline/backup_guardian.sh, scripts/repass_pair_agreed.py, the apply_* relabel scripts, ...
The stage5 hunk is BEHAVIOURAL, not cosmetic: status is now produced by `pipeline/serving_gate.derive_status` (D274h
"single serving-gate rule") and a new `s5_reason` is stamped, replacing the inline `fact_passed -> PASS/QUARANTINE`
branch. So the RUNNING verifier does not match a fresh checkout of HEAD: any `git checkout`/`stash`/`reset` of these
paths silently reverts the serving-gate rule (and the retrieve/schema work) while the DB keeps the labels that were
produced under it -> hidden divergence between code and corpus. The 4,696 QUARANTINE rows reported in D-310 were
produced under the uncommitted rule.
FIX: review + commit (or explicitly park behind a feature flag) these 18 files BEFORE any run that writes to
maxwell.db, and do not run `git checkout` on pipeline/ until then. Same failure class as the taxonomy state fixed by
D-309 (uncommitted semantic change + committed-looking governance).


## BUG-328 — UPDATE (HIGH, 2026-09-21, session-6 forensic audit): it is worse than "uncommitted"

The 18 modified files are accompanied by **untracked modules that the modified files import**:
`pipeline/serving_gate.py` (imported by `stage5_verify.py:50` + `scripts/apply_dedup_marks.py:34`)
and `pipeline/closed_menu.py` (imported by `stage4_merge.py:105`). A fresh checkout therefore does
not *silently revert* — it **raises ModuleNotFoundError at import**, i.e. a total S5/S4 outage, while
the DB keeps the 4,696 QUARANTINE rows that the same rule produced. Second new sub-defect: the live
`fbs` table has 71 columns and is **one migration behind the code** — `content_type_source`,
`discipline_source`, `extraction_type_source`, `menu_hash` are absent, so the R1/D-279 provenance
stamps have never been written to a single row (F-44 `min_human_share` still has no data to bind to).
The G19 columns (`s5_reason`, `epistemic_status`, `verification_method`, `isor`) ARE present.
Evidence of coherence (why landing it is correct, not risky): `py_compile` clean; `pytest` 200 passed
/ 1 pre-existing failure (BUG-330); `menu_hash` 73597ee2 matches the frozen `.sha256`;
`scripts/apply_serving_gate.py` dry-run over all 7,995 rows reports **0 writes** (the rule exactly
reproduces the stored PASS 3299 / QUARANTINE 4696 and the s5_reason partition sums to 7,995);
`retrieve` smoke-tested against the live DB (keyword/fts/vector/hybrid all return rows).
Resolution: landed as one reviewed commit (production + config + tests), see D-313 log entry.

## BUG-329 — BUG-314 CORRECTION: the frozen ruler exists in THREE versions and the drift is SUBSTANTIVE (HIGH, 2026-09-21)

BUG-314 ("zero substantive label drift") was reached by comparing the live sheet against its own
Sep-20 12:38 backup and **never against HEAD**. Comparing working tree vs `HEAD` shows real label
movement, not normalisation:

- hash triple: freeze-time `csv_sha256=4d0c856a…` (what `anchor1_frozen_20260920.json` hashed, bytes
  existing NOWHERE in the repo) vs HEAD `2d456720…` vs working `38323192…`.
- **DISC (human labels): 7 rows** — R024 strategic thinking→finance, R027 leadership→organizational
  theory, R057 ∅→finance, R111 emerging→typography, R126 emerging→cultural design,
  R139 emerging→psychology, R146 leadership→organizational theory.
- **CT: 41 rows** (R004 process instance→quarantine, R005 principle→tool instruction, R007 growth
  edge→noise drop, R049 principle→process template, R125 process template→principle, …).
- **FORM: 62 rows**, mixed cosmetic (spelling) and substantive (R006 normative_heuristic→descriptive
  model, R062 empirical pattern→descriptive model).
- `note_codes` rewritten on 149/150 rows (the reviewer's uncertainty prose was replaced); `conf_*`
  filled; "+4 trailing/blank lines" → 154 rows with one empty `item_id`.

Impact: the published baseline (disc error 0.4741, n=116) remains *derivable* because the frozen key
embeds per-row `human`+`stored` labels — but the grounding CSV is unversioned and its freeze-time
bytes are lost, so byte-level verification fails closed and a re-measure would silently use v0, v1 or
v2 depending on checkout state. Same class (untracked, unversioned human artifacts that ground
published numbers): `ANCHOR1_BLIND_SHEET_20260920.csv`, `SINGLE_CODER_CEILING_SHEET_20260920.csv`.
Rule added → D-313. Action: **OWNER GATE 4** — name the canonical ruler version before any re-measure.

## BUG-330 — Stale smoke assertion: test expects a word the pipeline no longer prints (LOW, OPEN, pre-existing)

`tests/test_stage4_preflight_smoke_stress.py:381` asserts `"QUARANTINED" in stdout+stderr`. The
D2196 message prints "…documents quarantined…" (lowercase). The string is absent from **HEAD's**
`stage4_merge.py` too, and the uncommitted stage4 diff does not touch that code path, so the failure
is PRE-EXISTING and independent of BUG-328 (a `git worktree` of HEAD could not settle it: the smoke
fixture `knowledge pipeline/stage2_extract/t11/checkpoint.jsonl` is untracked and absent there).
Fix: assert on the D2196 phrasing or on the quarantine count.

## BUG-331 — Serving-gate write to the production DB has no R5 review on record (MED, OPEN)

`scripts/apply_serving_gate.py --apply` rewrote statuses across all 7,995 rows; `stage5_verify.py`
now derives status from `derive_status()`. R5 (generator != verifier) is not documented for either
artifact — the strongest available evidence is post-hoc (the 0-change dry-run + the row-level matches
in this audit). Retrofit the review (gemma-4-E4B, D2549 routing) and record the verdict in
`governance/serving_gate_20260919.md`. No data risk identified: the rule is idempotent and its output
is exactly the stored state.

<!-- s7-sync 2026-09-21 -->

## BUG-328 — CLOSURE EVIDENCE (2026-09-21, session 7)
Landed in `32cb9fa` (18 modified + 2 new modules + configs + tests). Closure evidence, all re-run after the
landing: (1) `scripts/apply_serving_gate.py` dry-run over all 7,995 rows writes **0** rows and reproduces the
stored PASS 3299 / QUARANTINE 4696 exactly; (2) row-level re-derivation of `s5_reason` matches the DB;
(3) `menu_hash` from code == the frozen `config/closed_menu_v5.sha256`; (4) `pytest`: 200 passed / 1 pre-existing
failure (BUG-330); (5) `pipeline/` diff vs HEAD is now empty. An OPEN HIGH that is actually landed is worse
than no entry: it hides the next genuine HIGH.

## BUG-332 (LOW - FIXED 2026-09-21, found by audit F-01): the bake-off artifact merge did not check the SOURCE
The BUG-323 "merge at write" fix kept previously measured arms, but never checked that they came from the same
label SOURCE. The first ANCHOR-1 (R3 held-out) run would therefore have merged the ruler arms into the held-out
artifact — silent provenance contamination of a number used for a deploy decision. Fix: the artifact now
carries `source` + the full resolved `spec` + `menu_hash`, and a merge whose `source` differs is refused with a
warning (no silent cross-source mixing). Verified by re-running `--arm constant` on both sources.

## BUG-333 (MED - OPEN 2026-09-21): the R5 verifier (gemma-4-E4B) can return a schema-shaped rubber stamp
Asked to review the R3 adapter adversarially, the model answered in the exact requested format while replying
"yes" to inverted-polarity questions ("any way to widen the row set silently?" -> ROW_SET: yes) and `NONE` to
every blocker line. A pro-forma review would have "closed" a HIGH-severity gate (see also BUG-331). Standing
rule adopted: **R5 evidence for a measurement adapter must include a MECHANICAL channel** (here: a
truth-blinding re-run), and an LLM review that answers a polarity question without evidence must be recorded
as INSUFFICIENT, not as a pass. Fix path: add a polarity-consistency check to `scripts/r5_review_*.py` prompt
scaffolding (ask for a quoted line per answer) and re-review BUG-331 under the new rule.

## BUG-334 (MED - OPEN 2026-09-21): a pre-registered n is not automatically the measurable n
D-311 pre-registered 58 held-out rows; one of them (sheet row 15, fb_id `38c529d5…`) carries an EMPTY human
verdict, so the measurable set is n_scored = 57. Every published statement must declare the effective n, or
the denominator silently flatters the result. Guard: `bakeoff.sources.<name>.exclude_rows_without_truth` now
makes the drop explicit and the loader PRINTS `truth=` / `unlabelled_excluded=` on every run.

## BUG-335 (LOW - FIXED 2026-09-21, audit F-04): a lost comment line in config/eval_integrity.yaml
The per-pair scoring note ("padded forward batches (per-pair scoring was ~1 s/pair)") had been glued onto the
`abstain_sweep` key instead of `nli_batch_size` by an earlier careless edit. Comment restored where it belongs.

## BUG-326 — UPDATE (2026-09-21, session 7): the repair is BLOCKED, its target set is not re-derivable
Re-measured read-only against `knowledge pipeline/maxwell.db` (7,995 rows) in the session that was about to act
on it: non-canonical `discipline` = **757, and every single one is the string `emerging`** — the taxonomy's
DECLARED CATCH-ALL (`meta.catch_all_discipline`), i.e. a legitimate label, not a mis-canonicalisation.
`config/alias_map.yaml` yields **0** hits for them. Both-axes rows = **65** (not 147); rows with an empty
`domains` field = **0** (not 703); empty `discipline_raw` = **355** (not 354). A naive "raw→canonical" sweep
would therefore have rewritten 757 legitimate catch-all labels. **No write was made (0 rows changed).** The
residual real gaps are (a) 355 rows whose `discipline_raw` was never persisted (a C29/F-44 provenance gap, not a
taxonomy defect) and (b) 65 rows where a discipline token also appears among the domains — both need owner
intent, not a script. Scope doc: `governance/BUG326_REPAIR_SCOPING_20260921.md`.

## BUG-336 (MED - OPEN 2026-09-21, NEW STANDING RULE): an agent's measurement claim is not evidence
Third instance in two sessions (see also the retracted "assignment missing" and "margins not persisted" claims):
a count or defect claim was carried forward across sessions and used to plan a mass write, without being
re-derived in the session that acts on it. **Rule: before any repair/backfill/mass-write, every target number
must be re-derived READ-ONLY from the live store in the same session, and the re-derivation must be recorded with
the query's row count; a number that does not reproduce cancels the write.** Corollary already in force: a
`--apply` path is only allowed once the dry-run counts match the re-derived counts exactly.

## BUG-337 — Name collision: two different human instruments both called "ANCHOR-1" (MED, FIXED 2026-09-21)

`ANCHOR1_BLIND_SHEET_20260920.csv` (60 rows, contra-stratified, menu 73597ee2) and
`anchor1_frozen_20260920.json` (150 rows, stratified, menu cac6e695) shared the ANCHOR-1 name while
overlapping on only 2 fb_ids, and D-274f reserved ANCHOR-1 for the 150-row set. Consequence: "which ruler?"
was undecidable from filenames, and a reader could merge or substitute the wrong instrument.

FIX: 60-row set renamed ANCHOR-2 (sheet, key, menu reference, held-out set, kappa/triage/bakeoff artifacts,
scripts `anchor2_kappa.py` / `anchor2_repair_triage.py`); config source `bakeoff.sources.anchor1` ->
`anchor2` with `legacy_names: [anchor1]`; bytes unchanged so all sha256 citations remain valid;
`governance/ARTIFACT_REGISTRY.md` is the single name map + pooling rules. Also renamed
`anchor1_arbitration_*` -> `ruler_arbitration_in_sample_*` (it was measured on the 150-row ruler, n=116).
Verified: YAML loads, py_compile clean, anchor2 source resolves 57/58 rows with pipeline labels intact.

## BUG-329 — CLOSED BY RULING 2026-09-21 (was HIGH): the frozen ruler exists in THREE versions
Owner ratified D-315 ("go with the recommendation"). Disposition of all three, so no future session re-derives it:

| version | sha256 | where | status |
|---|---|---|---|
| v0 — freeze-time | `4d0c856a…` | only inside `anchor1_frozen_20260920.json:csv_sha256` | **byte-lost**: exists in no repo version and no backup. Answered by explicit ruling, not by a D-313 abort. |
| v1 — draft at commit `986fbc4` | `2d456720…` | `git show 986fbc4:governance/RULER_BLIND_SHEET_20260917.csv` | **superseded draft**: 41 CT + 7 substantive DISC + 82 FORM label diffs vs the authority. Adopting it would silently move 48 human labels and re-baseline every floor. Retained as the annotation record (its note_codes are the reviewer's original prose, mean 30 chars vs 129). |
| v2 — the measured label set | `38323192…` | workspace = HEAD (committed in 85c8081) | **label-equivalent to the authority** (0 CT, 0 substantive DISC/FORM diffs). This is the set every published number was measured on. |

RULING (D-315): the authority is `governance/anchor1_frozen_20260920.json` (`0ec321a7…`) — committed, immutable,
sha256-cited, carrying human+stored+agree per row for 3 axes plus stratum and fb_id. The CSV is the human editing
workspace, never the answer key. Verification: re-scoring from the authority reproduces the published numbers
EXACTLY (CT 0.3533 / DISC 0.4741 / FORM 0.2828), so the ruling moves no published number.

## BUG-338 (MED — FIXED 2026-09-21, audit F-02): the authority stores a SCORER SENTINEL in a label field
`anchor1_frozen_20260920.json` carries `stored.discipline = "emerging_dump"` on 13 of 150 rows. That token exists in
neither `config/taxonomy_v5.yaml` (61 canonicals) nor the live DB, and is not in the key's own declared
`vocabularies.discipline`. It is the scorer's internal sentinel (`resolve_disc_stored`): `emerging` on the STORED
side is a dump bucket = a stored-label FAILURE, deliberately asymmetric with the human side where `emerging` IS an
abstention. Consequences: (a) 13/150 stored values do not reproduce from the DB (which holds `emerging`), so a
future consumer joining stored labels to the DB silently sees a different value; (b) the artifact is an evaluation
OUTPUT wearing the shape of a label record.
**NOT fixed by editing the authority** — rewriting an immutable, sha256-cited artifact to fix cosmetics is exactly
the sin D-313 exists to prevent. Fixed by (i) making the resolver idempotent over the sentinel, (ii) declaring the
mapping in `config/eval_integrity.yaml:ruler_authority.abstention` and in `governance/ARTIFACT_REGISTRY.md`, so
`emerging` (pipeline) -> `emerging_dump` (scored) is read through a documented rule instead of a hidden one.

## BUG-339 (HIGH — FIXED 2026-09-21, audit F-01): the config that DECLARES "error rate, never accuracy" carried accuracy
`config/eval_integrity.yaml:ruler_measurement.measured` still held the CORRUPT pre-correction figures
(content_type 0.740 / discipline 0.506 / extraction_type 0.831) presented as `accuracy`, with
`verdict: PASS_DECISIVE` anchored to them and `sheet:` pointing at the workspace rather than the authority. Those
figures treat the STORED label as the answer key — precisely what D-275a forbids, in the file that carries the rule,
and the machine-readable surface an agent reads before touching a floor. A live conflict: two answers to the same
question, one of them wrong, with no deprecation marker.
FIX: `measured_error_rate` now reports stored-label ERROR RATE vs the blind human, with the effective n
(CT 150 / DISC 116 / FORM 145) and Wilson intervals, sourced from the authority's `summary_error_rates`. The corrupt
block is RETAINED as `superseded_measured:` — deleting a published number is not a correction (R-D410). `sheet:`
now points at the workspace explicitly and a new `authority:` key points at the JSON. Plus a new
`ruler_authority:` block declaring authority/workspace/superseded/lost hashes, menu hash, truth_source and pooling rule.

## BUG-337 FOLLOW-UP (LOW — FIXED 2026-09-21): one dangling citation survived the rename
D-314's `evidence:` cited `bakeoff_typed_decision_anchor1_20260921.json`, which no longer exists after the
ANCHOR-1/ANCHOR-2 split. A decision record whose evidence path cannot be opened is not evidence. Repointed to
`bakeoff_typed_decision_anchor2_20260921.json`. (Rule: a rename is not complete until every citation resolves.)

## C15 STATUS (2026-09-21, session 8) — 17 unresolved bugs, therefore listed here
HIGH: BUG-311 (stage5 checkpoint missing), BUG-313 (cognitive science 94% contra, 126/133), BUG-319 (qwen3coder arm
abstains 116/116). MED: BUG-310, BUG-312, BUG-315, BUG-316, BUG-317, BUG-326 (BLOCKED), BUG-330 (LOW), BUG-331,
BUG-333, BUG-334, BUG-336 (standing rule). Closed this session: BUG-329, BUG-338, BUG-339, BUG-337 follow-up.
NOTHING on the ruler may be re-measured before the second-coder gap (F-11) is addressed for anything that
repoints a FLOOR; re-measurement for diagnosis is now unblocked and read from the authority.

## BUG-340 (MED — FIXED 2026-09-21, audit F-02): the canonical ruler cannot express an ABSTENTION REASON
D-315 made anchor1_frozen_20260920.json the answer key. Its `human` side stores an abstention as JSON
`null`, so `blank` (a datum, D-275a never-imputed) and `emerging` (an explicit abstention) are
INDISTINGUISHABLE in the authority alone: 34 DISC nulls = 28 blank + 6 emerging. Consequence: a re-run of
the repointed scorer from the authority collapsed the DISC annotation line from `{blank: 28,
abstain-emerging: 6}` to `{blank: 34}` and rewrote `human_raw` with canonicalised labels — i.e. the
committed ruler_inverted artifact was generated by the WORKSPACE path while the config declares the
authority (stale-by-method, not stale-by-number). FIX: `overlay_annotation_from_workspace()` restores the
REASON from the human workspace ONLY where the authority cell is empty, behind the workspace sha256 pin
(drift = FAIL-CLOSED, C16/D-313); the answer key stays the authority (C21). Verified: error rates
unchanged (CT 0.3533 / DISC 0.4741 / FORM 0.2828), scored_n unchanged (150/116/145), 6 cells overlaid,
blinding self-test PASS, drift guard PASS. Declared in config/eval_integrity.yaml:annotation_source.

## BUG-341 (HIGH — OPEN 2026-09-21, regression of BUG-311): the LIVE stage5 checkpoint is absent again
BUG-311 was closed 2026-09-20 as "checkpoint restored" (sha256 2c206a25…). It is not durable: at
2026-09-21 18:59:42 stage5 rotated the live file to `checkpoint.jsonl.stale_20260921_185942` because its
input fingerprint moved (S4 checkpoint sha 2f8b34fb…, taxonomy v5.5, commit f5ec415), and NO completing
re-run followed (s5_rerun.pid is from Sep 2; no stage5 process is alive; the Sep-2 logs are the only
ones at that path). So the "RESOLVED" state of BUG-311 is CONDITIONAL on an input fingerprint that has
since moved — the lesson is that a rotation-guarded artifact must never be recorded as durably restored.
NO DATA LOSS: the surviving file is byte-identical to the declared restore (2c206a25…, 7995 FBs) and is
declared in config/eval_integrity.yaml:label_snapshots.stage5_t11. Deliberately NOT copied back to the
live path: that would re-arm a silent resume from PRE-REPAIR labels (the very contamination the
rotator prevents). Fix = re-run stage5 on the current S4 input (hours, out of this budget) — until then
the R2 corpus meter is pinned to the Sep-4 snapshot and must be cited that way.

## BUG-330 (LOW — FIXED 2026-09-21, session 9) — the smoke assertion probed a CASING, not the intent
The test required the literal "QUARANTINED" while D2196 prints "...documents quarantined..." (lowercase). The fix
asserts the INTENT case-insensitively. After it, the file has ONE remaining failure, which is a different defect
(BUG-343).

## BUG-342 (MED — FIXED 2026-09-21) — the C15 count was not re-derivable, and the quoted number was wrong
C15 ("5+ unresolved -> append to every handoff") was enforced by a hand-maintained count. Mechanically re-derived
from governance/buglog.md (scripts/bug_status.py, status = the last "## BUG-<id>" header event, REOPEN beats a
later CLOSED): **60 open / 29 closed of 89 ids** — not 17. The old count counted only the ids a human remembered;
it also still listed BUG-311/313 as unresolved while BUG-311 had regressed out of sight. The index is now a
generated artifact (governance/bug_status.json/.md) and the count is quoted from it, never from prose.

## BUG-343 (LOW-MED — OPEN 2026-09-21) — a smoke test asserts a checkpoint that its own fixture cannot produce
tests/test_stage4_preflight_smoke_stress.py::test_smoke_diverse_batch_writes_checkpoint_and_routes asserts
"knowledge pipeline/stage4_merge/smoke_preflight_plumbing/checkpoint.jsonl" exists after an LLM-off run. It does
not, in this working copy (the same untracked-fixture class as BUG-330). Either the fixture input is absent or the
run exits before the atomic write; both need the run log, which is not captured by the test. Not fixed here: it
needs the subprocess stderr, and a test that cannot show its own failure output is a second defect.

## C15 STATUS (2026-09-21, session 9) — MECHANICAL, supersedes the session-8 prose count
Source of truth: governance/bug_status.json (re-derive: python3 scripts/bug_status.py). **60 open / 29 closed of 89 ids** -> the append-to-handoffs threshold is EXCEEDED: every handoff must carry this list. The session-8 claim
of "17 unresolved" is RETRACTED as a hand-count (BUG-342).


## BUG-344 (HIGH — FIXED 2026-09-21, audit F-17): the declared ruler pins were never enforced in the run path
`config/eval_integrity.yaml:ruler_authority` declares authority_sha256 / workspace_sha256_at_head /
annotation_sha256 / key_sha256 — but `authority_paths()` read only the paths, `truth_source` and `menu_hash`.
So the annotation drift guard built for BUG-340 received an EMPTY declared hash, `if declared_sha and ...`
short-circuited, and the guard could never fire in a real run — while the committed artifact cited
`annotation_sha256: ""`, a D-313 provenance failure (an artifact grounding a published number must cite its
source by sha256). The guard appeared verified only because a unit call passed the hash by hand.
FIX: `verify_declared_pin()` enforces the declared pin BEFORE the artifact is read (FAIL-CLOSED, C16/D-313;
`--allow-pin-drift` is the loud override); the workspace pin is enforced on the legacy `--truth-source sheet`
path; `paths["key"]` replaces the hardcoded KEY constant; the artifact now records the hash ACTUALLY consumed
(`annotation_sha256`) beside the declared pins (`annotation_pin_declared`, `authority_pin_declared`).
VERIFIED: PIN OK on both paths; 4750 result leaves identical to HEAD; scored_n 150/116/145; 6 cells overlaid.

## BUG-345 (HIGH — FIXED 2026-09-21, found BY the BUG-344 fix): the declared ruler pin was TYPO'd
The newly-enforced pin failed on its very first run: config declared
`0ec321a7761d03a9277372051cef867e15d32d438ebb51fefdaf39d4159a54cf` while the artifact is
`...cef867e15e32d438...` — ONE character, index 34 (`d` for `e`). It survived two sessions because every prior
"pin verified" check compared a 16-char PREFIX, and the typo sits past that window. A prefix comparison is not
a verification; a control that cannot fail is not a control. ZERO measurement impact (nothing was ever
decisioned on it — it only ever mis-reported agreement with a hash it never compared).
FIX: pin corrected; `scripts/pin_audit.py` byte-compares EVERY declared pin (explicit pin→file pairs, never
inferred by proximity) and exits non-zero on drift. Now: 5 pins checked, 0 failing.

## BUG-346 (MED — FIXED 2026-09-21): a second ruler scorer could still be woken up
`scripts/score_ruler_labels.py` treated the STORED label as the answer key (agreement-with-corruption) and
refused only because the workspace CSV carries 4 trailing EMPTY rows — an accidental guard, not a designed one.
Retired as a SECOND TRUTH PATH (C21/D-315/D-316): it now exits 2 with a pointer to the canonical artifact and
scorer unless `--legacy-sheet-truth` is passed explicitly. Kept in-tree so the historic `verification:`
citations in config/decisions.yaml still resolve.

## BUG-333 (PARTIALLY FIXED 2026-09-21) — the R5 verifier returned a rubber stamp
`scripts/r5_review_r3_adapter.py` now (a) runs a MECHANICAL leak precheck that does not depend on the model
(any reference to the answer key in the adapter BLOCKS the review), (b) requires QUOTED EVIDENCE for all six
number-deciding questions, and (c) stamps VERDICT: PASS / INSUFFICIENT / BLOCKED and exits 2 unless PASS.
Unit-verified: the prior rubber stamp now scores 6/6 unsupported → INSUFFICIENT. BUG-331 stays OPEN until the
hardened review is actually run against the adapter.

## BUG-347 (MED — FIXED 2026-09-21): the C15 classifier treated "PARTIALLY FIXED" as CLOSED
`scripts/bug_status.py` matched close-words as SUBSTRINGS, so the new header
`## BUG-333 (PARTIALLY FIXED 2026-09-21)` classified as CLOSED and a LIVE bug silently left the open count
(60 -> 59). A partial fix is an OPEN bug with progress attached; the substring rule turned a status word into a
verdict. This is the second defect in three sessions that the mechanical index caught in ITS OWN output -- which
is the argument for machine-derived C15 counts (BUG-342) rather than hand counts.
FIX: `PARTIAL_WORDS` (PARTIAL / MITIGATED / IN PROGRESS) is classified OPEN and outranks the close words;
precedence is opened > partial > closed > open. A `self_test()` with six registered edge cases now runs on every
invocation and aborts FAIL-CLOSED if the classifier regresses.
CORRECTION (audit trail, and a bug in its own right): TWO commits (6c36bec, 550cee4) announced BUG-347 as fixed
in their messages while the code was NOT patched -- the first patch aborted on an anchor assertion, the second on a
SyntaxError, and in both cases the commit still went through. The fix is carried by the third commit only, and the
status count is quotable only once `bug_status.py` runs its `self_test()` without aborting. This is the same class
as BUG-345 (a claim that was never mechanically checked) and it is the reason the standing rule is: fix -> verify
-> THEN claim. The two premature commit messages stand uncorrected in history (R-D410); this paragraph is the
authoritative record.

## C15 STATUS (2026-09-21, session 10) — MECHANICAL, supersedes every earlier count
Source of truth: `governance/bug_status.json` (generated by `scripts/bug_status.py`, which now self-tests its
classifier before emitting anything). **61 open / 32 closed of 93 ids.**
Corrections recorded rather than hidden: commit 8e7724b's message quoted "59 open / 33 closed" (the numbers printed
by a run whose verification assertion had aborted for an unrelated reason — `open` is a list of dicts, not ids);
the counts above are authoritative. BUG-333 is OPEN (partially fixed, not closed) — BUG-347's whole point.
Session-10 additions: BUG-344 (pins not enforced), BUG-345 (pin typo), BUG-346 (second scorer retired),
BUG-347 (classifier false-close) — all FIXED; BUG-333 stays open pending a real hardened review run.

## BUG-348 (MED - OPEN 2026-09-21, found by the senior-ontology review of MENU_REPAIR_WORKSHEET_20260921.md)

**Symptom.** PART 1 of the worksheet asks the owner to rule "A = ADD it to the menu / B = do NOT add" on 13
"domain slots the pipeline NEVER emits". But `config/closed_menu_v5.json` ALREADY CONTAINS all 13:
9 exactly (`systems & frameworks`, `web & ui`, `illustration`, `marketing & communications`, `leadership`,
`code & computation`, `environmental design`, `motion design`, `design systems`) and 4 as trivial string
variants of existing slots (`social science` <- `social sciences`; `media & entertainmen` <- `media &
entertainment`; `product desig` <- `product design`; `business operation` <- `business operations`).
For 9 rows "A" is a no-op and "B" is already true; for 4 rows the human cell is a TYPO/near-miss.

**Cause.** `scripts/menu_repair_worksheet.py` builds the "never emitted" set from the human's FREE-TEXT
`domains_verdict` normalised by `.lower()` only -- no strip of quote characters, no typo/near-match
resolution against the menu. Any human typo therefore becomes a phantom "missing ontology slot", and any
*unemitted but existing* slot is mislabelled as a missing one. A coverage defect (the classifier never
reaches 9 of its own 44 domain slots) is presented as an ontology gap -- two different bugs, one checkbox.

**Impact.** 4 phantom ontology gaps; the owner is asked to expand a menu that does not need expanding;
if "A" is taken literally, a TRUNCATED TYPO (`product desig`) can be canonised into the frozen menu.
Measurement impact today: NONE on the ruled numbers (RULER-150/ANCHOR-1 under menu cac6e695 does not score
the domain axis; this worksheet is built from ANCHOR-2, menu 73597ee2b1bb1eb9 -- NEVER pooled, D-315).

**Fix (not yet applied).** Normalise the human cell before set-membership (strip quotes/whitespace, case),
and resolve near-matches against the menu (difflib >= 0.9) into either the existing slot or an explicit
"NOVEL" bucket; report the two classes separately: `UNEMITTED_EXISTING` (coverage bug) vs `NOVEL` (ontology
gap). Gate: a menu addition must name a slot that is ABSENT from the menu, hash-checked at generation time.

**Related, same review.** PART 2 row 15 (`behavioral economics` vs stored `emerging`) is not a boundary
disagreement at all: `emerging` is `taxonomy_v5.yaml::catch_all_domain/catch_all_discipline`, so that row is
a CATCH-ALL FALLBACK (a pipeline failure) misclassified as a menu-boundary question.


## C15 STATUS (2026-09-21T19:21:57Z) — MECHANICAL, supersedes every earlier C15 block in this file

Source of truth: `governance/bug_status.json` + `governance/bug_status.md`, regenerated by
`python3 scripts/bug_status.py` at 2026-09-21T19:21:57Z. **65 open / 34 closed of 99 ids** (re-derived AFTER the entries below; C15 threshold 5 -> append-to-handoffs required: true).
Do NOT restate this number anywhere else — cite the artifact (BUG-349: the previous C15 block hardcoded 61/32/93 and
was stale within the same day, because a hand-copied derived number cannot track its own source).

## BUG-349 (LOW — OPEN 2026-09-21, found by the session-11 forensic audit F-A)

**Symptom.** The C15 status block in this file states "61 open / 32 closed of 93 ids" and calls itself mechanical and
authoritative, while the live re-derivation produced 62 open / 32 closed of 94 ids (BUG-348 had been appended after the
block was written). A "supersedes every earlier count" claim was itself already wrong.

**Cause.** A DERIVED number was hand-restated into a handoff instead of citing the generated artifact + stamp.

**Fix (applied here).** The C15 block now names its generator and its generation stamp. Standing rule (C12 applied to
governance): a handoff cites `governance/bug_status.json`, it does not restate the count.

## BUG-350 (MED — FIXED 2026-09-21, found by the session-11 forensic audit F-B)

**Symptom.** BUG-347 was still classified OPEN although its header says FIXED: the classifier scanned the WHOLE header
line, and BUG-347's own title quotes the phrase "PARTIALLY FIXED" as the thing it fixed.

**Cause.** `scripts/bug_status.py::classify()` received the full header text (title included), so any title that names a
status word decided the status. A false OPEN is a live bug that looks unclosed; the inverse (a title that says CLOSED
while the status slot says OPEN) would silently retire a bug.

**Fix (applied).** New `status_slot()` reads only the parenthetical that follows the bug id (falling back to the text
before the first colon, then the whole header) after dropping double-quoted spans. Self-test extended with the two live
header shapes. Dry-run over all 94 ids: exactly one delta (BUG-347 open -> closed) and no other movement; the count is
now 61 open / 33 closed of 94.

## BUG-351 (LOW-MED — OPEN 2026-09-21, found by the session-11 audit F-C)

**Symptom.** `config/closed_menu_v5.sha256` does not contain the sha256 of the file it names. It holds
`73597ee2b1bb1eb9…`, which is `menu_hash = sha256(canonical_json(menu))`; the file's BYTES hash to `bc53770103595f2a…`.
A byte-level check (`shasum -a 256`), i.e. exactly the check D-318 says a pin must survive "in the run path", FAILS.

**Cause.** Pin file named after an algorithm it does not use. No drift: verified that pin == menu_hash(current file) ==
`ANCHOR2_KEY_20260920.json::menu_hash` (all `73597ee2…`) and `pin_audit.py` reports 5/5 PASS.

**Fix (not applied — rename needs one decision).** Rename to `closed_menu_v5.menu_hash` (or add a first line naming the
derivation), and state the derivation next to `menu_hash` in `config/eval_integrity.yaml`. Until then: anyone who
byte-compares this pin will raise a false alarm, and "fixing" that alarm would overwrite the true provenance hash.

## BUG-352 (MED — OPEN 2026-09-21, found by the session-11 audit F-D)

**Symptom.** After the ANCHOR-1 -> ANCHOR-2 rename (D-311), at least 12 artifacts still record the PRE-RENAME PATHS.
Example: `governance/bakeoff_typed_decision_anchor2_20260921.json` records
`sheet: governance/ANCHOR1_BLIND_SHEET_20260920.csv` and `key: governance/ANCHOR1_KEY_20260920.json` — neither file
exists on disk. Its recorded `menu_hash` (`73597ee2…`) is the ANCHOR-2 one, so the CONTENT is correctly identified while
the POINTER is not.

**Cause.** The rename map lives in `governance/ARTIFACT_REGISTRY.md`, but nothing in the run path consults it, and
artifacts record a path without the bytes' sha256.

**Impact.** A reader that resolves the stale path fails loudly today (safe), but if a file is ever re-created under the
legacy name `ANCHOR1_*` meaning the 150-row ruler, the same path would silently resolve to the WRONG instrument — a D-315
class pooling hazard.

**Fix (not applied).** (1) Every artifact records canonical name + sha256 per input, not a path alone. (2) A shared
legacy-name resolver/guard, or a hash assertion, in the loader. (3) Never re-create a file under a legacy name. The
~12 citing files on disk are NOT rewritten (published evidence, R-D410); the registry is the single name map.

## BUG-353 (MED — OPEN 2026-09-21, found by the session-11 audit F-H)

**Symptom.** `python3 pipeline/integrity_check.py --quick` is RED: 9/10 checks pass; check [14] "Hardcoded paths (C12)"
lists `scripts/next_critical_queue.sh:14`, `queue_after_chain.sh:15`, `reclaim_optiq.sh:12`,
`rerun_niah_fixed.sh:9`, `run_completeness.sh:8`, `run_completeness_tier2.sh:7`, `run_final_chain.sh:10`,
`run_qwen38_quant_ab.sh:7`, `run_remaining_chain.sh:6`, `run_s4_gemma.sh:9`, `run_vision_probe.sh:6`,
`tools/model_eval_suite.py:303`, `tools/model_eval_suite.py:308`.

**Cause.** Paths written into scripts instead of `config/*.yaml` (C12), never logged, so the integrity gate has been red
and unnoticed.

**Fix (not applied).** Extract to config, or mark each with an explicit, reasoned C12 exemption; then the gate returns
green. Until then, "integrity: PASS" is a claim that cannot be made.

## BUG-348 (MED — FIXED 2026-09-21): the menu-repair worksheet grew a SECOND, weaker matcher and reported sheet artifacts as menu gaps

Cause: `scripts/menu_repair_worksheet.py` compared the human `domains_verdict` cell to the pipeline's
emitted domains with a bare `.lower()` — no quote/whitespace hygiene, no consultation of the alias
layer that already exists (`config/taxonomy_v5.yaml` `raw` via `pipeline.schemas.match_to_canonical`,
plus owner-approved `config/normalization_map.yaml`, D-307) — and then printed `most_common(16)` of
that raw counter. This is the BUG-346 "two truth paths" class: a second matching path, weaker than
the one the pipeline uses, deciding what the owner is shown.

Impact (the owner was asked to rule on a wrong list): PART 1 showed 13 rows; on inspection they were
2 sheet artifacts (a stray quote: `marketing & communications"`, `"leadership"`), 4 surface variants
(`social science`, `media & entertainmen`, `product desig`, `business operation`) that resolve onto
slots the pipeline DID emit, and 7 genuinely unemitted slots. It also truncated PART 2 at 16 rows when
the disagreement list is 26 pairs / 31 rows — so 10 pairs were never shown, and the excerpt column was
empty because the generator read `row`/`name` but never the `definition` column.

Fix: one resolver (`match_to_canonical`, kind-aware D2133) + `normalization_map.yaml`; quote/whitespace
hygiene on every cell token; five explicit buckets (ARTIFACT / ALIAS_RESOLVED / UNEMITTED_EXISTING /
NOVEL / NEAR_MISS); a near-match is REPORTED, never silently resolved (D2422 spirit); all 26 pairs with
their `definition` excerpt; and the output is stamped with the sha256 of every input it read (D-318).
The ruled worksheet is NOT regenerated — the corrected reading is a new artifact
(`governance/PART1_PART2_REISSUE_20260921.md`), because a published artifact the owner has written on
is evidence (R-D410).

Result: ARTIFACT=2, ALIAS_RESOLVED=5 uses/4 distinct, UNEMITTED_EXISTING=7 slots/11 uses,
**NOVEL=0**, NEAR_MISS=0, PART2=26 pairs/31 rows. NOVEL=0 is the load-bearing number: the human labels
introduce NO domain concept absent from the menu. The ANCHOR-2 domain disagreement is 100% emission
coverage + surface spelling, not an ontology gap.

R5: `gemma-4-E4B-it-MLX-4bit` (maxwell_omlx), 6-question adversarial pass — BLOCKING ISSUES: none.
Caveat recorded honestly: its evidence for the C16/no-silent-fallback question was asserted from the
`try/except` "implied by context" rather than read off the file, so that item is a weak (unearned) PASS.
The other five items were answered from the code.

## BUG-354 (MED — OPEN): the shared resolver rejects the catch-all on BOTH axes

`pipeline.schemas.match_to_canonical("emerging", "domain")` returns `None`, and so does
`("emerging", "discipline")`. `load_taxonomy()` appends `emerging` to BOTH canonical lists, so the
opposite-axis guard added for BUG-200/D2422 ("a label canonical on the opposite axis must never resolve
on this axis") fires on the one string that is legitimately canonical on both. Verified live:
`domain emerging -> None | discipline emerging -> None`.

Impact: any consumer that uses the shared resolver to validate or map the catch-all silently gets
`None` instead of `emerging`. Today the blast radius is small (stage4_merge has its own `emerging`
fallback path), which is exactly why it went unnoticed. It is a latent trap: a future caller that
treats `None` as "unmappable" would drop or re-mint the catch-all, corrupting the taxonomy-expansion
signal (`s3_original_domain`) that the catch-all exists to preserve.

Fix (not applied — touches the D2422 guard): exempt `meta.catch_all_domain`/`catch_all_discipline` from
the opposite-axis guard, and add a regression test asserting `match_to_canonical(catch_all, k) == catch_all`
for both k.

## BUG-355 (MED — OPEN): one surface string, two canonicals — and a dead entry in the domain block of normalization_map

(a) `match_to_canonical("social science", "domain")` -> `social sciences` but
`match_to_canonical("social science", "discipline")` -> `sociology`. That is kind-scoping working as
designed (D2133), and it is RIGHT for the axes. But `get_synonym_index(None)` (the FLAT index, still a
public entry point and still the fallback in `match_to_canonical`) makes the winner depend on build
order, so the same string can map to two different canonicals depending on which consumer asks. Any
caller that passes no kind gets an arbitrary answer.

(b) `config/normalization_map.yaml` has 7 entries under its `domains:` block. Six map a variant onto a
canonical DOMAIN. The seventh is `human-computer interaction -> human computer interaction`, where the
KEY is a canonical DISCIPLINE and the TARGET is not in the domain vocabulary nor the discipline
vocabulary. Verified: `target_in_domains=False target_in_disciplines=False key_is_discipline=True`.
So the entry can never produce a valid domain token; its only possible effect is to turn a legitimate
`human-computer interaction` domain cell into a guaranteed mismatch. Same family as BUG-325 (the map was
already found rewriting DISCIPLINE tokens), but this one survived because it is not a real discipline
alias either.

Fix (not applied — config/*.yaml is owner-owned and C12-protected): delete that one entry from the
`domains:` block (the canonical spelling is `human-computer interaction`, which `normalize_label`'s
dash-fold already reaches); and make the flat index either private or kind-required.

## BUG-356 (LOW — OPEN): the repair queue's own "Next:" line is stale and hides the real next action

`governance/MENU_REPAIR_QUEUE_20260921.md:54` says "Next: wire config/normalization_map.yaml into the
comparison layer, then re-measure kappa." That is already done: `scripts/anchor2_kappa.py:56` reads the
map (D-307), the domain agreement moved 0.3938 -> 0.4385, and the queue's items 2-16 are already marked
SETTLED. Impact: the instrument of record tells the next session to do a finished task, which is how a
queue quietly stops being read. Also: the queue holds 26 pairs while only 16 have a drafted test — the
10 without one are drafted in `governance/BOUNDARY_DISCRIMINATORS_20260921.md`.

Fix (partially applied): a CORRECTION block is appended to the queue (append-only, R-D410); the queue
file itself is not rewritten.

## C15 STATUS (2026-09-21T21:40Z) — MECHANICAL, supersedes every earlier C15 block in this file

Generated by `scripts/bug_status.py` over this file; do not restate this number anywhere —
cite `governance/bug_status.json` instead (BUG-349). C15 threshold 5 -> append-to-handoffs required: true.

## BUG-355 (MED — PARTIALLY FIXED; (b) CLOSED by the owner prune, (a) still OPEN): one surface string, two canonicals

**(b) CLOSED.** The owner pruned the dead entry `human-computer interaction: human computer interaction`
from the `domains:` block of `config/normalization_map.yaml`. Verified after the prune: the remaining 6
entries each map a surface variant onto an **existing canonical domain**, and re-running
`scripts/anchor2_kappa.py` produces a **byte-identical** `governance/anchor2_kappa_20260921.json` — domain
observed agreement 0.4385, `macro_kappa_active` 0.4906, jaccard 0.4426, active_domains 39, all unchanged.
So the dead entry was **inert**: removing it moves no published number, it only removes a latent trap (a
key that would have rewritten a legitimate `human-computer interaction` domain cell into a guaranteed
mismatch). Recorded deliberately, because "the fix moved nothing" is evidence about the entry, not a
failure of the fix.

**(a) still OPEN** — `get_synonym_index(None)` (the FLAT index) makes the winner order-dependent: the same
surface string resolves to two different canonicals depending on build order. Fix (not applied): make the
flat index private, or make `kind` required.

## BUG-357 (MED — OPEN): the `behavioral economics` definition is narrower than its operational denotation

`config/taxonomy_v5.yaml` defines behavioral economics as deviations "in **economic decision-making and
market behavior**" (object requirement R1). But on the frozen 60-row sheet, **row 60** *Same-age Peer
Modeling* — "influence" by age-matched models on "a behaviour or attitude change", with no price, purchase,
demand or incentive in the sentence — is labelled **behavioral economics** by the owner, while the pipeline
answered `psychology`, which is what the definition string read literally licenses.

Impact (this is the load-bearing half): a classifier whose only evidence for BE is the definition string
will **reproduce** the pipeline's error. Boundary rules cannot repair it — the definition is upstream of
the boundary. It also means BE does not currently cover the nudge / social-norms / peer-influence family at
all, which is a *coverage* hole of the same shape as the emission holes measured in D-319.

Fix (owner gate, denotation not spelling — no menu slot moves): (i) widen the `definition:` string to name
the mechanism class (heuristics, framing, affect, social norms, peer influence) and the second object class
(behaviour-change interventions), keeping "describes the bias; does not exploit it" and all five excludes
— **recommended**; or (ii) keep the definition and re-label row 60 `psychology`. Drafted as items 24′/26′
of `governance/BOUNDARY_DISCRIMINATORS_20260921.md` Part D. Nothing applied.

## BUG-358 (LOW — OPEN): `config/verify_abstention.yaml` cites a repair queue that does not exist

`config/verify_abstention.yaml:9` declares `repair_queue: governance/REPAIR_QUEUE.md`. The path does not
exist and has never existed (`grep` over `config/ governance/ pipeline/ scripts/ tools/` finds the
citation and nothing else). The file is currently harmless only because the whole config is **inert**
(`enabled: false`, no production reader), i.e. the citation cannot fail yet — a latent trap, not a live
error.

Two further facts make "just create the file" the wrong fix: (1) the queue's **only** writer is the
abstention rule (`margin < t_low`), which does not exist, so a file created today is a queue that can
never receive a row — an **Emission-class artifact** (a slot that exists and is never written), the exact
failure mode this session measured on the ANCHOR-2 domains; (2) an empty queue file asserts "no repairs
pending", which is a false statement about the world. `governance/ABSTENTION_DESIGN_20260921.md` also
names the real missing dependency, which is not a path: *"repair-queue capacity + routing owner"* (its
open item 2), plus the de-dup key `fb_id` for the arbitration overlap (open item 3).

Fix (recommended, one config line): keep the key but declare it as **not materialised** and name the
contract — write-path + `fb_id` de-dup key + owner — rather than pointing at a document. Do **not** create
an empty queue file, and do **not** repoint to `MENU_REPAIR_QUEUE_20260921.md`, which is a one-off
taxonomy worksheet, not a row queue.

## C15 STATUS (2026-09-21T19:54Z) — MECHANICAL, supersedes every earlier C15 block in this file

Generated by `scripts/bug_status.py` over this file; do not restate this number anywhere — cite
`governance/bug_status.json` instead (BUG-349). C15 threshold 5 -> append-to-handoffs required: true.

## BUG-357 (MED — FIXED 2026-09-21): `behavioral economics` definition was narrower than its operational denotation

Owner ruled **(i) widen the definition**. Applied to `config/taxonomy_v5.yaml` (`definition:` only):
the mechanism class (heuristics, framing, affect, **social norms and peer influence**) and the second object
class (**behaviour-change interventions**) are now named; the "describes the bias; does not exploit it to
design persuasion" clause and all five `exclude` entries are unchanged; the `raw` list is untouched.

Consequence recorded deliberately (this is a **denotation** change, not spelling): the file's bytes moved
`8d3c90e9…` -> `994e056b5e04ef1f37d350c0faae87e344da5cf85da2e405a8825d1f8f840312`, and because the
classifier reads the definition, two emission behaviours would otherwise carry ONE stamp (R14). Therefore
`version`/`classification_version` -> **v5.6** and `taxonomy_version: v5.5 -> v5.6` was synced in
`config/version.yaml` (1) and `config/pipeline_config.yaml` (3), so the stamped `TAXONOMY_VERSION` now
distinguishes them (verified: it resolves to v5.6). Slots added: **0** (43 domains / 61 disciplines
unchanged) — unlike D-309, so this bump is not a phantom version.

Still OPEN as a consequence: this fix takes effect only when the boundary wiring + an S4 run happen, so its
effect on row 60 is **predicted, not measured**.

## BUG-358 (LOW — CLOSED 2026-09-21): the abstention config cited a repair queue that never existed

Owner approved the recommendation. `config/verify_abstention.yaml` no longer cites a nonexistent document:
`repair_queue: null` (NOT MATERIALISED) plus `repair_queue_contract` (write_path, jsonl, append_only,
`dedup_key: fb_id`, `owner: TBD-OWNER-GATE`). No empty queue file was created — an empty queue would assert
"no repairs pending", and the write path cannot receive a row until the abstention rule is enabled. The
config still ships `enabled: false` and no production code reads it.

## NOTE (same session): the taxonomy sha256 pin move is a CONTROL, not drift

`config/closed_menu_v5.sha256` (the answer-space pin, canonical-JSON `menu_hash`) is **unchanged**: the
menu was not touched. The *taxonomy* sha256 moved only because of BUG-357. Artifacts that cite the old
`8d3c90e9…` remain historically accurate for the day they were written (D-318/D-315: a provenance stamp is
not retro-editable); new artifacts must cite `994e056b…` + `taxonomy_version v5.6`.

## NOTE (session 13c): Part C ruled — `default_home` + escape is the discriminator of record

Part B items 17-23 and 25 accepted; items 24/26 remain REJECTED and superseded by 24'/26' (definition-anchored,
now backed by the v5.6 BE definition, D-321). Nothing wired into the prompt yet.

## BUG-359 (LOW — process, LOGGED 2026-09-21): a carried "pending fix" note that was never re-verified
The justfile preflight path ('names scripts/config_audit.py, should be pipeline/config_audit.py') was carried
across at least three sessions as an open task. Re-checked today: justfile:24 and justfile:255 ALREADY read
`pipeline/config_audit.py`. The note was stale from the moment the file moved, and re-deferring it cost
sessions of attention. Standing rule: a pending-task note is not evidence - re-run the check before
re-deferring it, and delete the note the moment it passes.

## BUG-353 (MED → FIXED 2026-09-21, D-326): integrity check [14] Hardcoded paths (C12), 13 hits
(1) 11 shell scripts (next_critical_queue, queue_after_chain, reclaim_optiq, rerun_niah_fixed,
run_completeness, run_completeness_tier2, run_final_chain, run_qwen38_quant_ab, run_remaining_chain,
run_s4_gemma, run_vision_probe) each began with `cd '<abs repo path>' || exit 1` → replaced with a
self-locating `cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` (no path stored anywhere).
(2) tools/model_eval_suite.py:303,308 → synthetic tool-calling EVAL FIXTURES ("/home/dana/notes"), not our
environment. Exempted with the explicit marker C12-FIXTURE: on the line; check 14 now REPORTS the exemption
count in its PASS message so the exemption surface is visible and countable, never a silent hole.
(3) The detector's own regex literal was then flagged by itself → same marker applied.
Gate: python3 pipeline/integrity_check.py --quick → 10/10 PASS.

## BUG-360 (LOW — process, LOGGED 2026-09-21): a second stale carried claim in one session
The carried RED "BUG-341: stage-5 Verify = 0" is stale. Running pipeline/stage5_verify.py (2026-09-21) reports
"S5 resuming: 550 FBs already verified -> 7445 remaining": the checkpoint holds 550 verified FBs and the
verification pass is now re-running over the remainder. Two stale carried claims were found in one session
(this and BUG-359 justfile path). Standing rule: a carried claim is re-verified before it is re-reported as RED.

## BUG-357 follow-up (2026-09-21, D-327): the row-60 prediction is NOT CONFIRMED
The widened definition (v5.6) plus the ruled boundary block did not move row 60 to the human slot; the whole
treatment arm was WORSE than baseline (emission 70.0% vs 78.3%, error 0.8333 vs 0.8000, oov 18 vs 13). The
ontology fix stays (it is correct at the definition level and BUG-357 was a real denotation defect), but the
prompt-level boundary rules are REJECTED as an intervention on this instrument. The dominant defect is now
measurable and different: 13-18 of 60 rows emit a label OUTSIDE the closed menu (out-of-vocab), and only ~20%
of rows agree with the human slot. That is a MENU-COMPLIANCE (emission) problem, not a boundary problem.

## BUG-361 (HIGH - resilience/concurrency, OPEN): two S5 writers on one checkpoint; S5 has no single-writer lock
Evidence (exact byte arithmetic, 2026-09-21 23:01). Run A (pid 30050, started 23:00:40) resumed at 550 records
and died at its first incremental write (i=50) with `SHRINK GUARD: checkpoint.jsonl would shrink 12305321 ->
10632913 bytes (13.6%)`. Cumulative line sums of the current t11/checkpoint.jsonl settle the attribution:
line 601 = 10,632,913 bytes (run A = 550 resumed + 50 new = 600 records) and line 651 = 12,304,671 ~= the
12,305,321 bytes on disk (the other writer's 650 = 550 + 100). Run B - the owner's foreground run - kept
writing to 1,250 records (550 + 700) at 23:04:45 and then stopped. Two processes wrote one checkpoint; the
guard prevented a REAL 50-row rollback and killed run A (correct fail-closed behaviour, wrong root cause).
IMPACT: wasted GPU work, a run that looked "frozen", an aborted stage, and a checkpoint whose provenance
mixes two processes. FIX (proposed, NOT applied): an O_EXCL pidfile lock taken in run_stage5 BEFORE the resume
read; a live pid => refuse to start (C16 fail-closed); release on exit including SIGINT.

## BUG-362 (HIGH - future tax, OPEN): an S5 checkpoint is discarded by ANY commit, including governance-only ones
D2485 fingerprints the S5 input with pipeline_commit=get_pipeline_commit() (which returns HEAD) and
manifest_hash. Observed 2026-09-21: HEAD moved 8de5d36 -> 249c9d1 at 23:01:28 (a governance/config commit) and
the D-327 config flip changed manifest_hash 0a974d60 -> bc567ad8, while s4_checkpoint_sha256 (2f8b34fb...),
taxonomy v5.6, nli_model and schema_version were ALL unchanged. Current fp id 9eb47b31... != stored 63f823bd...
=> the next `python3 pipeline/stage5_verify.py` prints "fingerprint MISMATCH", archives the 1,250-record
checkpoint and re-verifies all 7,995 FBs (~1.3 h of DeBERTa). Standing consequence: while a long stage is in
flight, no commit of any kind can be made without throwing that stage's progress away. FIX (proposed, NOT
applied): fingerprint the S5-relevant code only (last commit touching pipeline/stage5_verify.py + its imports)
rather than a global HEAD, and scope manifest_hash to the S4 keys S5 actually consumes. Owner decision needed
first (see the session handover: re-stamp with a declared note vs accept the re-verify).

## BUG-363 (MED - measurement integrity, OPEN): the ruler sheet is FILLED and 28/150 rows are INCOMPLETE; G4 still describes it as blank
G4_RULER_INSTRUCTIONS.md section 3 claims the sheet carries "zero stored-label columns" and that one human pass
turns the 150 rows into the first `human-blind` tier. Re-read against the bytes today: all 150 rows carry
reviewer='human' + a date + CT/DISC/FORM answers - so the single-coder pass HAPPENED, and that is the attested
set F-11 refers to (not evidence of independent human truth). (a) 28 of 150 rows are missing at least one axis
(measured by scripts/f11_llm_coder.py --export; the item_ids are recorded in MANIFEST.json) so
score_ruler_labels.py refuses the entire sheet and the ruler cannot be scored at all until those rows are
answered or deleted. (b) the coder's FORM answers include non-menu spellings: 'casual mechanism' (30 rows) and
'normativ heuristic' - out-of-vocabulary AS WRITTEN; they are declared as aliases in config/f11_llm_coder.yaml
and reported, never merged silently (C12d). (c) note_codes holds free text, not the 0-2 numbered codes the
rubric requires. PROCESS: a "blind/blank sheet" claim is verified against the file bytes before it is
re-reported (the BUG-359/BUG-360 standing rule). G4 section 3 needs a one-line correction.

## BUG-364 (MED - R14 provenance, OPEN): laya weights are on disk while bakeoff_laya.yaml still says PIN-AT-INSTALL / licence UNVERIFIED
temp/laya_download.log: "Fetching 5 files: 100% ... loaded in 87.5 s" (2026-09-21 23:02) - the sandbox weights
are local now. config/bakeoff_laya.yaml still carries revision: PIN-AT-INSTALL, sha256: PIN-AT-INSTALL and
licence.checkpoint: UNVERIFIED. R14 forbids a measured use before revision + sha256 + checkpoint licence are
recorded, and the menu_hash must be recorded per run. FIX: pin revision and sha256 of the fetched files and
record the checkpoint licence before ANY laya advisory run.

## BUG-365 (LOW - harness defect in this session's new code, FIXED 2026-09-22): f11_llm_coder.py crashed on a relative coder path
`--score "temp/claude sonnet labels.jsonl"` raised ValueError: '...' is not in the subpath of '<repo>' from
`llm_path.relative_to(PROJECT_ROOT)` because the CLI path was never resolved. FIXED in-session: cmd_score now
resolves the path and falls back to recording it ABSOLUTELY when the coder file lives outside the repo.
Third defect found in the F-11 harness's first hour (after the conf_ct/conf_extr key mismatch and the stale
150-row prompt text) - all three found by USING it, none by reading it. Standing note: a new harness is
exercised with a real input before its output is believed.

## BUG-366 (LOW - process, OPEN): an LLM coder silently under-delivered (79 of 122 rows)
temp/kimi3 labels.md contains 79 valid JSONL rows; 43 rows (R101, R103-R110, ...) were never answered, and the
file is named .md although it is JSONL. The harness refuses a partial coder by default, so nothing was scored
on a wrong denominator (the --partial run DECLARED n=79 and recorded the missing ids in the artifact). Ask the
coder for the remaining 43 rows, or record the shortfall permanently.

## BUG-367 (MED - OPEN, ruler data quality, found by the F-11 worksheet 2026-09-22): the human FORM column is mostly non-canonical spellings
RULER_BLIND_SHEET_20260917.csv FORM (1-4) tally: 'descriptive model' 38, 'casual mechanism' 30, 'normative heuristic' 27,
'normativ heuristic' 22, 'empirical pattern' 13, 'causal mechanism' 10, 'escriptive model' 2, 'normative_heuristic' 1,
'empirical_pattern' 1, 'descriptive_model' 1. The MISSPELLED variants dominate the canonical ones (57 of 150 cells = 38%
are not the canonical menu string; the canonical 'causal mechanism' appears only 10 times against 30 'casual mechanism').
config/f11_llm_coder.yaml declares the aliases, so SCORING is unaffected - but any consumer that reads the raw column
(filters, GROUP BY, the F-14 4054 pre-repair FORM rows) sees out-of-vocabulary values. This is direct corroboration of
the F-14 concern and a repair target: canonicalise the sheet in place (append a repaired column, R-D410) or repair at read.

## BUG-361 (MED - FIXED 2026-09-22, D-330): no single-writer lock on the S5 checkpoint
Two runs wrote one checkpoint within 4 minutes on 2026-09-21 (mine archived by the shrink guard; the user's Ctrl-C left
1,250 records from the other writer). FIXED: pipeline/stage5_verify.py acquires <checkpoint>.lock (pid + timestamp,
O_EXCL-style create, atexit release) before ANY checkpoint decision; a LIVE holder makes the second run refuse
(fail-closed, C16) and a dead pid's lock is reclaimed with a printed warning. PROVEN live: a second
`stage5_verify.py` while pid 4194 held the lock printed the refusal and exited. Config gate: stage5.single_writer_lock.

## BUG-362 (HIGH - FIXED 2026-09-22, D-330): any commit discarded a live S5 checkpoint
_s5_input_fingerprint() bound `pipeline_commit` (GLOBAL HEAD) and the whole-config `manifest_hash`, so a governance-only
commit invalidated a live checkpoint and re-verified 7,995 rows. FIXED: the fingerprint now binds the S4 checkpoint
content, schema/taxonomy versions, the model lineup, the S5-relevant source files (config list:
stage5.fingerprint_files = stage5_verify.py, serving_gate.py, io_guard.py) and the stage5 config slice. `pipeline_commit`
and `manifest_hash` are still recorded, under `informational`, but are NOT part of the identity. Migration is explicit:
`stage5_verify.py --adopt-fingerprint` re-stamps ONLY if all 7 substantive inputs are identical (it refuses otherwise).
EVIDENCE: old id 63f823bd1175b97f → new id c2754fc63f8450; changed keys were exactly the informational/scheme ones
(manifest_hash, pipeline_commit, s5_code_sha256, s5_config_sha256); all 7 substantive inputs identical. The 1,250
verified records survived: resume printed "1250 FBs already verified -> 6745 remaining".

## BUG-368 (HIGH - OWNER-FACING DATA TRAP, FIXED 2026-09-22): the decision sheet emitted 4 EMPTY columns because the FORM axis was written to the wrong keys - and the owner wrote his rulings into one of them

HOW: scripts/f11_decision_sheet.py built the axis keys as `f"{ax[:4]}"` -> 'cont', 'disc' and **'extr'** for
`extraction_type`, while the emitted header said `class_extra` / `human_extra` / `a_extra` / `b_extra`. The FORM
axis was therefore written to `human_extr`/`a_extr`/`b_extr` (keys no column reads) and the four header columns
shipped EMPTY. It was the same class of defect as the earlier conf-column mismatch (`conf_cont` vs `conf_ct`).

EFFECT: the owner, told to record his content-type/discipline rulings in `human_extra`, wrote 81 cells into a
column that is NAMED for the FORM axis but was empty and looked like free space. Nothing was overwritten (it
really was empty) and the data survived - but the record was semantically wrong, and no FORM data exists in
v1 of the sheet at all.

FIX (all non-destructive, R-D410): scripts/f11_decision_sheet_v2.py rebuilds the sheet APPEND-ONLY.
  * A..R (item_id..MECHANISM) are copied byte-for-byte and asserted identical before any write; the owner's 81
    ruling cells in `human_extra` remain VERBATIM. A..R sha256 = 05cb48630c3dfa15... (recorded in the stamp).
  * the missing FORM axis is appended: S=FORM_human_as_written (verbatim), T=FORM_canonical, U/V=the two coders.
  * a BLANK SEPARATOR column (W) then X=owner_cont, Y=owner_disc, Z=owner_notes. A blank column can no longer be
    mistaken for free space, because the only blank column now has a header that says what it is.
  * `owner_cont`/`owner_disc` are re-derived from the owner's raw cell through a declared, validated split
    (two-value cells split; typos fixed; every token checked against config/closed_menu_v5.json); the audit trail
    is governance/F11_OWNER_RULING_MAP_20260922.csv.
  * a backup of the owner's working file is kept at governance/backups/F11_DECISION_SHEET_20260922.USER_WORK_*.csv

REGRESSION RULE: a column-emission bug must be caught by asserting that every emitted column header has a
populating key. A generator that writes keys a header does not read MUST fail loudly (C16).

## BUG-364 (MED - R14 provenance, FIXED 2026-09-22): laya pins recorded; the repo ids in the config were wrong

The pre-existing `weights:` block named repos `aac6fef/laya-mlx` and `aac6fef/laya-multilingual-mlx` with
`revision: PIN-AT-INSTALL`. Neither is what the installed package fetches: laya_mlx/router.py resolves
`convaiinnovations/laya` (bundle), `/laya-multilingual`, `/laya-typed-decisions`.

RECORDED (owner-approved; NO run performed, adoption stays false, `enabled: false`):
  revision 1c5edc17a7acd8701df6fc341c0d179f1c62c982, 5 files re-hashed from disk, payload 846,195,574 bytes
  (model.safetensors 842,609,210 B - consistent with the ~421M-param ModernBERT-large in router.py).
  licence.checkpoint: benchmark-only-advisory (was UNVERIFIED). scope: never feeds the pipeline, never
  unfreezes F-11 / D-300 (D-275c/D-322).
NOTE: a `stat`-based size probe in this session first reported these files as tens of BYTES; that reading was
wrong (it measured symlink metadata, not content). The corrected hash pass is the recorded one. Lesson: never
size a hash-pinned artifact without reading it.

## BUG-363 (MED - measurement integrity) - STATUS 2026-09-22: owner chose option (b)

The 28 rows the human left unanswered are NOT gap-filled by hand. Round 2 of the F-11 export
(governance/F11_LLM_CODER_20260922/, PROMPT.md sha256 578eaee8f60d97f7...) exports ALL 150 ruler rows -
`n_rows: 150`, `n_excluded_incomplete_rows: 0`, `partial: false` - so the same coders adjudicate the blanks.
The blind CSV carries a final empty fence column so the BUG-368 collision cannot recur.

## BUG-369 (HIGH - MEASUREMENT INTEGRITY, FIXED 2026-09-22): blank human cells were scored as coder disagreements

HOW: scripts/f11_llm_coder.py cmd_score built `pairs.append((_canon(human_cell), _canon(llm_axis)))` for every
row in the sheet, unconditionally. `_canon("")` is `""`, so each row where the human never answered that axis
became the pair `("", <real label>)` - a guaranteed mismatch. The 28 DISC blanks, 5 FORM blanks and (in the
150-row set) 0 CT blanks were therefore counted as the coder being WRONG.

EFFECT: round-2 DISC agreement read 37.3% / k=0.360 instead of 45.9% / k=0.445, and the round-2 numbers were
not comparable with round 1 (whose human cells were all filled by construction). A silent, directional skew
that penalised the coders by exactly the blank share.

FIX: blank-aware pairing. If either side of a pair is empty after canonicalisation, the row is EXCLUDED from
that axis's pair set and counted in `n_excluded_human_blank` / `n_excluded_llm_blank` with the item_ids listed
in the artifact. An unanswered cell is not an answer and not an error.

STANDING RULE: any agreement/kappa/accuracy computation must state, per axis, how many rows were EXCLUDED and
why. `n` alone is not sufficient provenance (C12d/C16).

## BUG-363 (MED - CLOSED 2026-09-22, resolved as two different things, not one)
Round 2 measured the abstentions instead of guessing at them (governance/F11_R2_MEASUREMENT_20260923.md):
* the 5 blank FORM cells are NOT ambiguous - both independent families agree 5/5 (k=1.0)
* the 28 blank DISC cells ARE genuinely contested - the coders agree only 18/28 (64%, k=0.623) vs 0.682 on
  the rows the human did label
Disposition: the 28 DISC blanks stay MISSING (declared UNCERTIFIABLE, never back-filled with a consensus that
does not exist); the 5 FORM blanks are flagged for the owner's own adjudication. No row was padded, no row
was silently imputed.
