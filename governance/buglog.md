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

## BUG-370 - anchor consolidator guessed the owner column names instead of mapping them (FIXED, 2026-09-23)

SEVERITY: HIGH (silent-wrong-answer class, caught before any write)
SURFACE: scripts/consolidate_anchor_ruler.py

WHAT HAPPENED: the first version looked up `owner_<axis>` (owner_content_type / owner_discipline /
owner_extraction_type). The review sheet names those columns owner_ct / owner_disc / owner_form, so every
lookup returned empty and the dry run reported "content_type: human-ruled 150" - i.e. it claimed the owner had
adjudicated NOTHING while the file contained 216 filled cells. Had the dry-run mode not existed, the
consolidated anchor would have shipped silently discarding the owner's entire day of work.

This is the exact mirror image of BUG-368 (generator emitted header columns that no key populated):
there a written column was read as free space, here a written column was read as absent. Both are the same
defect - a column name that is never bound to a reader/writer.

FIX: the mapping is now declared in config/f11_llm_coder.yaml -> consolidation.owner_columns
(content_type: owner_ct, discipline: owner_disc, extraction_type: owner_form) plus keep_missing_column and
notes_column, and the loader FAILS LOUDLY (C16) if any owner_* column present in the sheet is unmapped, or if a
declared column is absent from the sheet. It also prints the filled count per owner column before doing
anything else, so "0 filled" can never again be mistaken for "nothing to consolidate".

STANDING RULE (extends the BUG-368 rule to the read side): every config-declared path/column mapping must be
verified against the artifact it points at BEFORE the first write, and a report of "no data" must be
distinguishable from a report of "no mapping". Dry-run-first is mandatory for any consolidation script.

## BUG-371 - decision numbering collision: DECISION-LOG.md leads config/decisions.yaml by 3 (FIXED, 2026-09-23)

SEVERITY: HIGH (governance integrity - an id can silently name two different decisions)
SURFACE: config/decisions.yaml <-> DECISION-LOG.md

WHAT HAPPENED: the registry's highest id was D331, so this session appended D332/D333 for the F-11 anchor
consolidation. DECISION-LOG.md, however, already contained D-332 (community-benchmark-first rule), D-333 (MTP A/B
instrument) and D-334 (Metal cap) - all dated 2026-09-22 - none of which had ever been imported into the registry.
The new ids therefore collided: a citation of "D-332" would have resolved to two unrelated decisions depending on
which artifact the reader opened. Caught before commit; the new entries were renumbered to D-335/D-336.

FIX: this session's two decisions renumbered to D-335/D-336 in both artifacts. Rows for D-332/D-333/D-334 remain
absent from the registry (NOT silently imported - importing another session's decisions without its evidence is
its own defect); the gap is now recorded here.

STANDING RULE: never derive a new decision id from a single artifact. The next id is
max(all ids in config/decisions.yaml, all ids in DECISION-LOG.md) + 1, and any divergence between the two
registers must be reported BEFORE a new id is minted. `recompute_decision_summary.py --check` validates counts,
not id uniqueness against the prose log.

## BUG-372 (MEDIUM — FIXED): the F-1 provenance note was unobservable, and the first two repairs were both wrong

*Reported 2026-09-23 by the forensic audit (F-1), fixed the same day.*

`scripts/consolidate_anchor_ruler.py` computed the alias/canonicalisation note into a local variable that the
tier branch then overwrote, so the owner's verbatim spelling (`computer graphic`, `media studie`) never surfaced
in `*_source_note`. Damage: cosmetic only (data was safe - the verbatim spelling was in the committed review
sheet and in `discipline_ruler_raw`), but the note is prose and therefore not machine-checkable.

Two repair attempts were wrong and were caught by the flag guard BEFORE the artifact was written:

1. comparing `owner_raw != owner` labelled 32 innocent `tool instruction` / `process template` cells as
   "canonicalised via a declared alias" - they were only separator/case variants;
2. comparing `norm(owner_raw) != norm(human_raw)` then fired on all 50 legitimate OVERRIDES.

Resolution: `canon()` now returns the MECHANISM (`verbatim` / `orthographic` / `alias` / `offmenu`), and the
anchor emits machine-checkable flags `ALIAS_CANONICALISED:owner:<axis>` and `ALIAS_CANONICALISED:ruler:<axis>`.
No "spelling differs" flag is emitted on purpose: it fires on expected behaviour. Aliases are now AXIS-TAGGED
(a content_type typo can no longer relabel a discipline cell).

**Rule:** an integrity flag that fires on expected behaviour is worse than no flag - it trains the reader to
ignore flags. Flag vocabulary must be justified by a guard test before the artifact is written.

## BUG-373 (HIGH — FIXED): a decision asserted an implementation state that no artifact carried

*Found 2026-09-23 by the forensic audit (C-1), fixed by D-338/D-339.*

`D-328` (2026-09-21) states that `config/verify_abstention.yaml` was set to `enabled: true` at p25 with triage
owner `OWNER-WEEKLY-TRIAGE`. No artifact was ever changed (the file still said `enabled: false`, owner
`TBD-OWNER-GATE`) and no production code reads it. The register therefore held a claim of an active protection
that enforced nothing - the D-2298 fail-closed path is what actually ran. This survived a full audit round
before being caught by reading the artifact instead of the decision.

**Class:** decision-asserts-state. **Fix:** D-338 (posture restated as approved-in-principle + gated, no
behaviour change) and D-339 (implementation receipt required for any flip) plus
`scripts/audit_flag_consumers.py` in `just health`, which makes a flag with no consumer a standing RED.

## BUG-374 (HIGH — OPEN, OWNER GATE): the rejected S4 boundary block is still live in production

*Found 2026-09-23 by the forensic audit (C-2).*

`D-327` (RESOLVED 2026-09-21) rejected the boundary block on measurement and states the flag was set
back to false. `config/pipeline_config.yaml:311` still reads `stage4.boundary_inject_enabled: true`,
and the flag is consumed in the run path (`pipeline/pipeline_paths.py:213` -> `stage4_merged_call.py:120`
prompt injection, `pipeline/stamp.py:124` fail-closed stamp). `git log -S boundary_inject_enabled --
config/pipeline_config.yaml` returns exactly one commit (`8de5d36`, which ADDED it as true): the flip
D-327 records has never been applied. Same class as BUG-373 - a decision asserting a state no artifact
carries - but here it changes behaviour, so it is the more dangerous instance.

**Remedy (one line, owner GO):** set `stage4.boundary_inject_enabled: false` in
`config/pipeline_config.yaml`, then re-run `just health` (the new flag-consumer check goes green).
Until then `just health` reports one RED by design.

## BUG-374 (HIGH — FIXED 2026-09-23, C-2): the rejected S4 boundary block was live in production
`config/pipeline_config.yaml:311 stage4.boundary_inject_enabled: true` while D-327 (2026-09-21) ruled the block
REJECTED and recorded the flip as DONE ("set back to false"). `git log -S boundary_inject_enabled` returns exactly
one commit (8de5d36, which ADDED it as true): the flip never landed, so the A/B-failed experiment was injected into
every S4 prompt for two days. The flag IS consumed (pipeline_paths.py:213 -> stage4_merged_call.py:120 injection,
stamp.py:124 fail-closed stamp), so this changed production behaviour, not a comment.
FIXED: flip applied atomically (backup `governance/backups/pipeline_config.yaml.PRE_C2_20260923`), value verified
false, YAML valid, `just health` RED cleared. CLASS: BUG-373 again — a decision asserting an implementation state
that no artifact carried. No new decision was minted: D-327 already rules it; this restores compliance.

## BUG-375 (MED — FIXED 2026-09-23, found by the session-18 audit): the flag audit's own scan could not match the registry
`scripts/audit_flag_consumers.py::scan_unregistered()` emitted the LEAF key (`boundary_inject_enabled`) via a regex,
while `config/flag_consumer_registry.yaml` registers the DOTTED path (`stage4.boundary_inject_enabled`). Consequences:
(a) a REGISTERED flag was ALSO printed as unregistered — the check firing on expected behaviour (BUG-372 class);
(b) the 8 anonymous `enabled` keys were unactionable ("add it to the registry" — which one?);
(c) 40 warn lines per run -> warn fatigue that buries the one RED.
FIXED: the scan now walks the parsed document and emits full dotted paths (e.g.
`config/omlx_m1_best_config.yaml::models.gpt-oss-20b-MXFP4-Q8.apply.guided_grammar_enabled`), de-duplicated; a
SELF-CHECK makes "registered but reported unregistered" a RED, so the convention cannot drift again. The now-unused
`import re` was removed (C19). Evidence: 4 verified / 0 RED, warns 40 -> 40 actionable, exit 0.

## BUG-376 (HIGH — OPEN, OWNER GATE = C-3): a completed S5 run's declared input was rewritten after the run, and the image is gone
`knowledge pipeline/stage5_verify/t11/checkpoint.jsonl` is COMPLETE: 7995 records, `status` PASS 5023 / QUARANTINE
2972, commit spread 1250 x 8de5d36 (adopted) + 6745 x 81b813f (new run), lock released, no fatal error. But its
`input_fingerprint.json` (id c2754fc6..., written 2026-09-22T11:26) declares
`s4_checkpoint_sha256 = 2f8b34fb0f104bbecc32d5b7cd3a37a272e9f3bc7b533db4a0e5b43fbff13992`, while the file
`knowledge pipeline/stage4_merge/t11/checkpoint_enriched.jsonl` was rewritten at 2026-09-22T12:52 (AFTER the run
completed at 11:47) and now hashes `0ca6f0f08bea8f2dfbafb7a598e934e4f2afc3b98a894ee847e3ca1183c3d1b0`.
A repo-wide sha256 scan found NO surviving copy of the 2f8b34fb image, so the identity of the verified input is
unprovable. Cause class: writers that rewrite this path in place (grep: reclassify_merged_axis.py,
sync_checkpoint_from_db.py, apply_bug150_*.py, rename_ai_systems_domain.py, fix_bug216_domains_raw.py, e2e_proof.py)
with no re-stamp of the downstream fingerprint. EFFECT: the next `stage5_verify.py` prints fingerprint MISMATCH,
archives the 7995 verdicts and re-verifies (~1.3 h); and S6 must not commit this output as "verified against the
current S4 artifact" (R14). Rows count is unchanged (7995) and the records still carry their own stamps (taxonomy
v5.1, manifest 711c8218, commit c042e05), so this is a MUTATION-OF-BYTES event rather than a re-classification —
but "same corpus, different bytes" is exactly what a hash claim cannot absorb.
DETECTION (new, live): `scripts/verify_declared_inputs.py` + `config/verify_declared_inputs.yaml` (roots + the
acknowledged-move list). An UNACKNOWLEDGED input move is RED (exit 1); this specific one is a DECLARED exception
with its reason, per the D-339 exempt_reason pattern. Wired into `just health`.
OWNER GATE: (a) `S5 REVERIFY` (~1.3 h on the current input), or (b) `S5 FREEZE` (copy the S4 image + S5 output +
manifest into a frozen/ dir and cite the pair). Pending the ruling, `config/eval_integrity.yaml` carries the truth
under `label_snapshots.stage5_t11.current_state_20260923` (the old "live_absent_since" keys are kept verbatim,
R-D410) and BUG-341's premise ("the live checkpoint is absent") is superseded by this entry.

## BUG-377 (LOW-MED — OPEN 2026-09-23, found by the session-18 audit): pidfiles that outlive their pid, one of them recycled
Five stale pidfiles were still on disk with no live owner: `temp/train_classifier.pid`, `temp/p3_challenger.pid`,
`temp/p4_retrain.pid`, `temp/p4_clean.pid` (contents are literally `PID: <n>`, unparseable) and
`knowledge pipeline/stage5_verify/t11/s5_rerun.pid` (pid 9665, from Sep 2). Worse,
`knowledge pipeline/stage4_merge/t11/s4_run.pid` holds pid 1933, which is now ALIVE — it belongs to
`SetStoreUpdateService.xpc` (macOS), i.e. the pid was RECYCLED. No current consumer reads these files
(`audit_e2e_cohesion.py` reads `singleton_run.pid`; `omlx_watchdog --pid` is explicit), so this is latent, not
live. IMPACT IF WIRED: any "is a stage running?" check based on pidfile liveness would refuse to start forever
(fail-closed) or attribute a stranger's process to a pipeline run. FIX (proposed, NOT applied): pidfiles must carry
a start-time or a command fingerprint (ps -o lstart= + command match) before liveness is trusted.

## BUG-376 (HIGH — OPEN, OWNER GATE = C-3; mitigation APPLIED 2026-09-23): S5's declared input was rewritten after the run
MITIGATION (not a fix) 2026-09-23: the pair is now FROZEN — `frozen/S5_t11_20260922/` (191 MB, gitignored payload)
+ `governance/FROZEN_S5_T11_20260922.json` (sha256 of all 4 files, 7995 records, PASS 5023 / QUARANTINE 2972) +
`scripts/verify_frozen_pair.py` in `just health`. S6 can now cite a BYTE-STABLE pair instead of a mutable
knowledge-pipeline path. The truth that must travel with any citation is recorded in the manifest: the verdicts were
computed against the S4 image of 2026-09-22T11:26 (2f8b34fb..., which no longer exists); the frozen S4 copy is the
LATER image (0ca6f0f0...) — same 7995-row corpus by count/schema/stamps, NOT byte-identical. CLASS FIX: D-340, an
in-place writer of a declared stage input must publish a mutation notice. OWNER GATE UNCHANGED: S5 REVERIFY or
cite the frozen pair with the qualifier.

## BUG-378 (LOW-MED — OPEN 2026-09-23, found by the session-20 audit): repository hygiene drift
(a) TRACKED root scratch: `ab_off.json`, `ab_on.json`, `probe_clean.sh`, `probe_output`, `handoff` are committed at the
repo root (session artefacts, not product). Untracked equivalents (`checkpoint.jsonl.depth.json`, `audit_output`,
`backup`) were archived to `archive/session_20260923/scratch/`; the tracked five were deliberately NOT moved, because
moving a tracked file is a diff and needs a decision on whether the file is product or scratch.
(b) `knowledge pipeline/stage4_merge/t11/` holds a 95 MB sibling `checkpoint_enriched_kindsafe.jsonl` (Sep 2) next to
the live `checkpoint_enriched.jsonl`. Nothing declares which is authoritative — a human or a repair script can pick the
wrong one (the same ambiguity class that produced C-3). Proposal: a `*.authoritative` marker or a move to an `archive/`
subdir inside the pipeline dir.
(c) `scripts/__pycache__/` holds .pyc for scripts that were renamed/archived (C19: no __pycache__ in the repo).
(d) FIVE `.input_fingerprint.json.stale_*` siblings sit next to the live S5 fingerprint. Harmless to machines (the
reader takes the exact name) but they invite a human to cite a stale reference.


## BUG-379

- **severity**: MED
- **status**: FIXED
- **logged**: 2026-09-23
- **detail**: A measurement-backed ruling's receipt existed only as untracked scratch. D-327 rests on an A/B measurement (boundary OFF 30/30 valid JSON @21.1s vs ON 0/30 @63.5s with a server-side reasoning-mode failure), but the only machine-readable receipt was ab_off.json/ab_on.json at repo root - misread as scratch by two audits, one cleanup away from destroying the evidence for a LIVE flag. FIXED 2026-09-23: filed as governance/evidence/D327_BOUNDARY_AB_20260921/ (payload + EVIDENCE_MANIFEST.json + README) and made a class rule by D-342; scripts/verify_evidence_manifests.py is in just health.

## BUG-380

- **severity**: MED
- **status**: FIXED
- **logged**: 2026-09-23
- **detail**: Register drift: governance/BUG326_REPAIR_SCOPING_20260921.md closed the BUG-326 repair as NOT APPLICABLE on 2026-09-21 (403 raw->canonical / 147 both-axes / 703 no-domain DO NOT REPRODUCE: 757 'non-canonical' are all the legitimate catch-all 'emerging', 0 alias-map hits, 65 mixed-axis, 0 domain-less), yet the session handoff, the task register and the gate list still carried 'BUG-326 GO' as an open owner gate - so the assistant recommended authoring a repair script for a target that cannot be re-derived. FIXED 2026-09-23 by re-reading the scoping doc and correcting the gate list (BUG-342 class: quote the generator, never carry a stale count).

## BUG-381

- **severity**: HIGH
- **status**: OPEN
- **logged**: 2026-09-23
- **detail**: Terminal-store vintage mismatch: knowledge pipeline/maxwell.db (mtime 2026-09-19T21:47) reports PASS 3299 / QUARANTINE 4696 of 7995 FBs, while the S5 t11 run of 2026-09-22 produced PASS 5023 / QUARANTINE 2972 over the same 7995 rows. The committed store therefore does NOT carry the verdicts of the run that the pipeline status reports. Source of each number quoted: pipeline/status.py (DB) vs the S5 checkpoint verdict counts (frozen manifest). Owner gate: which vintage is the committed truth - stage6 re-commit of the 2026-09-22 verdicts against the frozen pair, or accept the 09-19 vintage as the store of record.

## BUG-382

- **severity**: MED
- **status**: OPEN
- **logged**: 2026-09-23
- **detail**: Third instance of the BUG-375 class (a check that cannot resolve the names it must check). The flag registry uses DOTTED paths, but model names contain dots (`models.Qwen3.8-27B-MLX-4bit.apply.guided_grammar_enabled`), so scripts/audit_flag_consumers.py resolves a path that does not exist and reports `path MISSING (registry/artifact mismatch)` for flags that are present in the artifact. Effect: 4 legitimate flags cannot be registered at all until the path grammar is quoted/fixed. Fix (queued): resolve the path segment-wise against the parsed document, or store the path as a YAML list of segments.

## BUG-383 — C19's no-__pycache__ check cannot see gitignored caches (LOW, FIXED 2026-09-23)
**Symptom:** `find . -name __pycache__` reported **167 directories / 31,084,330 bytes** while C19 was recorded as clean.
**Root cause:** the C19 check measures *tracked* files; `__pycache__` is gitignored, so every script run regenerates 31 MB that no check sees (BUG-375 class: a check that cannot see the thing it names).
**Fix:** purged to 0 (they are untracked caches, not pipeline output, so R-D410/safe_delete.py does not apply) and the count is now reported in the audit with the reasoned reading. Reclaimed ~31 MB on a 97%-full disk.
## BUG-384 — the new authority checker RED-ed on its own pattern grammar (LOW, FIXED 2026-09-23)
**Symptom:** first run of scripts/verify_artifact_authority.py produced 11 spurious REDs: 10 on `checkpoint.jsonl.stale_*|*.input_fingerprint.json.stale_*` (a PIPE-JOINED glob, which `fnmatch` treats as one literal so it can never match) and 1 on a non_authoritative bookkeeping entry whose pattern did not cover its own filename.
**Root cause:** BUG-375 class again — the checker could not resolve the names it was asked to check. Also a BUG-372 trap: RED on a non_authoritative entry's pattern would make the marker fire on expected append-only drift.
**Fix:** split patterns on `|` (both in `declares_pattern` and the per-entry check) and made a declared pattern binding ONLY on an authoritative entry. Re-run: 2 markers, 17 files verified, 0 RED, 0 undeclared.

## BUG-385 — the flag audit + a mis-named consumer made 19 ON flags look unconsumed (MED, FIXED 2026-09-23)
**Symptom:** `governance/FLAG_HYGIENE_TASKS_20260923.md` §H and the session-22 proposal listed 19 ON flags as
"ON and the audit could NOT verify a reader", and the standing recommendation was **bulk FLAGS OFF as a
behaviourally no-op**.
**Root cause:** two stacked false negatives (BUG-375 class). (a) `consumer_reads()` is FILE-level: it proves a
file reads the *config artifact*, not that it reads *this flag*, so a flag bound through the C12 binder
(`pipeline/pipeline_paths.py` constants) is invisible to a literal-key grep. (b) The proposal named the WRONG
consumer for the 5 OMLX `guided_grammar_enabled` flags (`scripts/_omlx_apply_settings.py`, which reads
`~/.omlx/model_settings.json`) while the real reader is `scripts/omlx_apply_best_m1_config.py` (SPEC_PATH).
**Impact — a near-miss, not a cosmetic one:** FLAGS OFF would have set `stage1_3.enabled=false` (disables the
D2080 regex pre-filter for every run), `stage6.okf_export_enabled=false` (disables OKF export),
`stage4.merged_call_enabled=false`, `stage2.gate_enabled=false`, `stage4.depth_batch_enabled=false`,
`services.omlx.circuit_breaker_enabled=false` and both golden-injection paths — silent capability loss presented
as a no-op. A recommendation is a claim; this one was wrong.
**Fix:** symbol-level binding evidence (`consumer_symbols: {file: CONSTANT}`, D-339b) + BUG-382 dotted-key
resolution + the 5 OMLX entries re-pointed at the real consumer + `required` set to the value observed at
registration (D-338). Audit now reports **43 verified, 0 RED, 1 unregistered**. The remaining flag
`config/pipeline_config.yaml::services.omlx.mtp_enabled` is ON with no reader in the repo (a mirror of the
server-side setting; `scripts/mtp_ab.py` patches `model_settings.json`, not this artifact) and is handed to the
owner as a delete-or-reader call.

## BUG-386 — the k-NN arm reader mis-read the vec0 shadow store (LOW, FIXED 2026-09-23)
**Symptom:** first run of `scripts/knn_arm_eval.py` aborted with `chunk 18 missing/short for rowid 1`.
**Root cause:** the shadow chunk blob is 2,097,152 bytes = **1024 vectors x 512 dims x 4 bytes**, and
`vec_fbs_rowids.chunk_offset` indexes *vectors within the chunk*, not bytes. The reader compared a whole chunk
(524,288 floats) to `dim=512` and rejected every row.
**Fix:** slice `flat[offset*dim:(offset+1)*dim]` per row, chunk cached by id. The fail-closed guard (C16) turned
a schema misunderstanding into an abort rather than a plausible-looking wrong number - the intended behaviour.

## BUG-387 - HIGH - stage6_commit re-commit DOUBLED the vector store instead of replacing it: `insert_embedding()` reads `last_insert_rowid()` after `insert_fb()` and writes `INSERT INTO vec_fbs(rowid, .

stage6_commit re-commit DOUBLED the vector store instead of replacing it: `insert_embedding()` reads `last_insert_rowid()` after `insert_fb()` and writes `INSERT INTO vec_fbs(rowid, ...)`; on a re-commit over a populated store the vec rows are appended (15990 rows = 2x7995, all distinct rowids, 7995 orphans with no fbs counterpart) while the completeness check only compares COUNTS so it printed 'Vector: READY 15990/7995'. Detected by the D2185 orphan reconciliation it printed itself. Impact: every re-commit doubles the vector store and leaves the live rows served by stale vectors; retrieval correctness is NOT visibly broken (the matching rowids still answer) which is exactly why counts-only verification is not verification. NOT FIXED in code yet - do not re-run stage6 until the vec path is repaired (DELETE-then-INSERT or a rowid-preserving upsert + a rowid-level completeness assertion, not a count assertion).

## BUG-388 - MED - stage6_commit.

stage6_commit.py::export_parquet crashed AFTER the SQLite+vector write: pyarrow.lib.ArrowInvalid 'Could not convert 0 with type int: tried to convert to boolean' from pa.Table.from_pylist(rows). Root cause: the S5 checkpoint mixes Python bool and int 0/1 for the same key - is_summary and is_convergent are bool in 7867 rows and int in 128 rows (the same 128 rows that carry classification_error), so pyarrow infers boolean from the first row and then refuses the ints. The commit is therefore NOT atomic as a unit: fbs+vec_fbs are written, the parquet snapshot is not. Fix direction: coerce declared boolean keys to bool at load (C16 fail-loud if a key is mixed), never let pyarrow infer.

## BUG-389 - MED - Two verdicts were derived from checks that could not resolve what they were checking (BUG-375 class), and both were WRONG: (a) 'rerank.

Two verdicts were derived from checks that could not resolve what they were checking (BUG-375 class), and both were WRONG: (a) 'rerank.enabled is consumed only by retrieval_benchmark, not retrieve.py' - retrieve.py imports RERANK_ENABLED from pipeline_paths at line 35 and honours it at line 526 (`should_rerank = RERANK_ENABLED if rerank is None else rerank`), unmodified at HEAD 0182763, so production retrieval ALREADY reranks and the standing 'RERANK WIRE' task is void, not pending; the earlier grep looked for the literal config key, which the constant-bound consumer never contains. (b) The incumbent agreements compared against every arm (content_type 0.6467 / discipline 0.5259 / extraction_type 0.7172) are ANCHOR-1 numbers quoted forward from the 2026-09-20 ruler, but 108 of 150 content_type and 122 of 150 discipline cells have since been owner-adjudicated: the incumbent had never been re-scored on the ruler in force. FIXED by scripts/incumbent_ruler_score.py + config/incumbent_ruler_score.yaml (D-347).


## BUG-390 (LOW, OPEN) - the R2 meter cannot speak about extraction_type, so owner call 2 was unmeasurable
scripts/definition_nli_verify.py scores discipline + domains + content_type only. There is no per-row extraction_type NLI score anywhere in governance/, and no persisted extraction_type margin in any arm artifact (all four bakeoff files are axis=discipline). Consequence: the extraction_type abstention operating point CANNOT be measured today and was NOT transplanted from another axis (D-349 refuses it). Fix direction: extend the R2 meter to the extraction_type axis over the frozen ruler (n=145, ~150 inference pairs, no model of the generator family involved) before any extraction_type threshold is set.


## BUG-391 (HIGH, OPEN) - the ratified abstention operating point is not reproducible on the ruler in force

The D-312/D-349 discipline curve was measured with a denominator of n=116 and a base error of 0.4741. That figure
cannot be reproduced from anything on disk. On the reconstructible reference set (the ruler sheet's own human
discipline cells, 122 rows) the incumbent pairwise verifier scores 0.5000 (61/122); on ANCHOR-3 (ruler in force, 150
rows) it scores 0.5533. 0.4741 = 55/116 and 61-6 = 55, so the 116-row denominator is a SUBSET of the reference in
force whose 6 excluded rows were all incumbent errors, and the artifact that names those rows (the ANCHOR-1 sheet/key
referenced by the anchor2 bakeoff spec) is not on disk. Consequence: the ratified numbers are legacy, not verified.

Re-scored on the ruler in force (governance/ABSTENTION_ROBUSTNESS_20260923.json, paired bootstrap, 2000 draws):

| axis | ratified | re-scored on the ruler in force |
|---|---|---|
| discipline | base 0.4741, abstain 25% -> 0.3910 (-8.3 pp) | base 0.5533, abstain 25% -> 0.5000 (-5.3 pp, CI [1.4, 10.3], P(gain>0)=0.995) |
| content_type | base 0.3467, abstain 30% -> 0.3048 (-4.2 pp) | base 0.3467, abstain 30% -> 0.3048 (-4.2 pp, CI [-1.8, 8.9], P(gain>0)=0.908) |

The MECHANISM survives (margin AUC 0.7035 [0.620, 0.785] on the ruler in force; abstained-bucket error 0.711 at 25%),
but the content_type gain at the ratified point is indistinguishable from noise (P=0.908 < 0.95).

Fix direction: re-ratify both operating points on ANCHOR-3, record the denominator, and require a bootstrap CI in the
calibration artifact so a point estimate can never again be read as verified. Do NOT delete the legacy curve: keep it as
provenance with a supersession pointer (R-D410).

## BUG-392 (LOW, FIXED in session) - two defects in this session's own robustness checker

(a) the bootstrap AUC interval fed constant scores to the rank-sum AUC, so it printed a false [1.0, 1.0] certainty; fixed
by resampling rows and recomputing the AUC on the resampled scores. (b) the finding check only evaluated abstain rates in
the configured grid, so the content_type ratified rate (30%) was silently NOT evaluated - the BUG-375 class (a check that
cannot resolve what it must check); fixed by unioning the ratified rate from the calibration artifact into the grid. Both
defects produced a checker that looked green on the thing it was supposed to catch.


## BUG-393 (HIGH, FIXED this session) - just health did not run the menu checkers it was claimed to run

verify_menu_routing.py and verify_menu_policy.py were reported as health checks (D-346/D-350), but the health
recipe contained only 5 verify_* lines and no recipe mentioned them at all: a governance claim contradicted by
the artifact it described. Any session that read "just health 12/12" was reading a check that never ran.
Fix: both checkers plus the new verify_recalibration_pins.py are now wired into just health with || exit 1.
Lesson (BUG-375 class): a wiring claim must be verified by RUNNING the recipe and reading its output, never by
the diff that was supposed to contain the edit.

## BUG-394 (HIGH, OPEN) - the contextual vector store is 100 percent referentially dead, and the recorded description of BUG-387 was an inference, not a measurement

Measured 2026-09-23 15:14 (read-only on the run DB), the shape is NOT a doubling:

| object | rows | live (joins fbs) | orphaned | missing |
|---|---|---|---|---|
| fbs | 7995 (rowids 7997..15991) | - | - | - |
| vec_fbs | 15990 (rowids 1..15991) | 7995 | 7995 | 0 |
| vec_fbs_ctx | 7995 | 0 | 7995 | 7995 fbs rows have no ctx vector |

- distinct(rowid) in vec_fbs_rowids = 15990: there is NO collision with a live rowid. The extra 7995 are the
  PREVIOUS generation's vectors, orphaned when the fbs rows were replaced (their rowids <= 7996 no longer exist).
- So BUG-387's phrase 'DOUBLED (15990 = 2 x 7995)' was an inference from two counts; the true defect is dead
  index entries, not duplicate live entries. Severity reframed: retrieval DILUTION (knn_k = max(limit*5,100),
  or max(limit*15,200) with facets, so limit=20 still fills at 50 percent live) - not the total read blocker
  BUG-387 implied. The REAL risk is measurement validity: a retrieval number taken on a diluted index is on a
  different ruler. Existing retrieval research predates the dilution (doc 09-02, benchmark 09-03), so it is clean.
- vec_fbs_ctx is worse and was NOT previously recorded: ALL 7995 rows are orphans and 0 join live, so any consumer
  that sets vec_table='vec_fbs_ctx' (pipeline/retrieval_benchmark.py:159, an S1 A/B leg) returns ZERO usable hits
  and does so SILENTLY, because the hit->fbs join drops every hit. The R26 guard (buglog:1136) covers a DIFFERENT
  risk (label-poisoned content), not referential death, so the guard does not imply this is safe to use.
- Attribution is unrecoverable from inside the session (fbs created_at 08-30..09-03, DB mtime 09-23 13:41, no
  artifact names the writing run) - the BUG-391 class: provenance that cannot be reconstructed.

Fix (owner-gated: the delete is destructive, R-D410/BUG-261): backup first, then in the run DB delete only the
orphans - 'DELETE FROM vec_fbs WHERE rowid NOT IN (SELECT rowid FROM fbs)' (7995 rows) and the same for vec_fbs_ctx,
then re-run 'python3 scripts/verify_vec_integrity.py' (new, D-354) and expect exit 0. Do NOT use pipeline/safe_delete.py.
Then make the stage6 insert rowid-preserving and replace the count-only completeness check with a rowid-level
assertion, and wire verify_vec_integrity.py into 'just health'.

## BUG-395 (MED, OPEN) - a control artifact that no recipe runs, whose verdict is stale and whose premise no longer matches the configuration

- scripts/verify_boundary_injection.py (65 lines, D-318/D-325) asserts the ruled boundary rules are byte-present in
  the assembled S4 prompt. Nothing runs it: 'grep -n boundary justfile' = 0 hits, and no recipe or log references it.
- Ran it 2026-09-23: exit 1, 'baseline prompt 11126 chars | treated 11126 chars (+0)', 'FAIL missing=[default_home:...]'.
- That is NOT a live regression. D-327 REJECTED the ruled boundary block on measurement, and
  config/pipeline_config.yaml:313 stage4.boundary_inject_enabled: false (registered with 3 consumers in
  config/flag_consumer_registry.yaml) means the block is intentionally absent from the run path. The checker has no
  flag awareness, so it reports a correct configuration as a failure - the BUG-375 class (a check that cannot resolve
  the state it must check).
- Second defect: governance/SEQUENCE_STATUS_20260917.md:600 and DECISION-LOG D-325 still present this artifact as
  'Control artifact ... -> PASS'. It would FAIL today. A stale PASS in a control register is the BUG-393 class.
- Fix (no owner decision needed; D-327 already ruled): (1) make the script read stage4.boundary_inject_enabled and
  invert the assertion when False (require the block to be ABSENT - the D-327 state), printing which state it
  verified; (2) correct the SEQUENCE_STATUS/D-325 claim with an append-only pointer; (3) add it to 'just health' as
  'python3 scripts/verify_boundary_injection.py || exit 1' so it can never go stale unwatched again.

## BUG-396 (MED, FIXED by revert) - the BUG-395 repair attempt left 'just health' RED, and my own run harness let it commit

- Attempted the BUG-395 fix (flag-aware boundary control + wire into health) in commits b393dd6/ea6ca77. The edit
- introduced three successive defects (comprehension continuation, _ROOT vs ROOT, a sha reference used before its
- assignment), and each time the checker failed the COMMIT STILL LANDED, so health was RED for two commits.
- Root cause is the harness, not the script: the shell chain used ';' between the check and the 'git commit', so a
- failing gate could not stop the commit. Lesson (BUG-393 class): a gate that is not chained with && is decoration.
- Fixed by reverting scripts/verify_boundary_injection.py and justfile to d25fceb. Health is green again with 8 verify
- checks. BUG-395 is RE-OPENED as work, and the standalone repair must now be done in this order: (1) edit the script,
- (2) run it standalone and require exit 0, (3) ONLY THEN wire it to health, (4) chain every step with && so a RED
- check aborts the commit.


## BUG-395 (MED) - UPDATE 2026-09-23: the boundary control is now state-aware AND wired

Re-done in the mandated order (edit -> run standalone requiring exit 0 -> wire -> commit chained with &&);
the first attempt was reverted as BUG-396. Two defects, both of the BUG-375 class (a check that cannot
resolve the state it must check):
1. the premise was hardcoded ("all 10 default_home + 10 boundary tests present"), but D-327 REJECTED the ruled
   block and stage4.boundary_inject_enabled is false, so the control could only ever FAIL;
2. the D-318 pin assertion ("rule bytes folded into manifest_hash") could never pass in that state either:
   pipeline/stamp.py folds _s4_boundary_rules_sha256 in the ENABLED branch only, correctly - a stamp must not
   claim rule bytes the prompt was not built from.
Fix: the assertion follows the configured state, fail-closed in both. flag ON -> all ruled rules present in the
treated arm, none in baseline, truncated sha present in the stamp. flag OFF -> the same rules ABSENT from BOTH
arms, arms byte-identical, and the stamp must NOT claim a boundary sha.
Receipt: standalone exit 0 ("ABSENT from both arms (flag off; all 20 ruled rules withheld); no boundary sha
claimed in the stamp"); wired into just health as the 10th control; health exit 0.

## BUG-388 (MED) - UPDATE 2026-09-23: FIXED code-side (the export re-run is an owner gate)

pipeline/stage6_commit.py gained PARQUET_BOOLEAN_FIELDS + _coerce_parquet_booleans(), called per row in
export_parquet: None -> False, bool kept, exact int 0/1 -> bool, ANYTHING else raises ValueError naming the
field, the value and the fb (C16 - no silent coercion, no guessing what a mixed column means).
Probe receipt: coerce_int {is_summary: 1 -> True}; coerce_bool unchanged; coerce_none -> False; '1' (str) raises.
Still open: re-running ONLY the parquet export over the existing store (the SQLite+vec write lands first, so a
commit is not atomic as a unit) - owner-gated because it writes a production artifact.

## BUG-390 (LOW) - UPDATE 2026-09-23: the R2 meter can now speak about extraction_type

scripts/definition_nli_verify.py: the axis->menu-key map was a 3-way conditional that silently fell back to the
domains list for any unlisted axis, so an extraction_type label would have been scored against a DOMAIN
definition. Now _AXIS_KEYS resolves extraction_type -> extraction_types (4 labels in the closed menu), and the
per-row label set emits the axis. Receipt: smoke run --limit 6 emits extraction_type scores.
Still open: the RATIFIED curve over the frozen ruler (n=145, ~150 pairs) - and no extraction_type abstention
threshold may be set before it exists (it is refused, not transplanted).

## BUG-397 (LOW, OPEN) - two live code paths default to artifacts that no longer exist

1. pipeline/student_classifier.py::DEFAULT_GOLDEN = config/golden/stage4_golden_mined.yaml - the golden set was
   retired to archive/golden_retired_D2618/ (D-2618); the default cannot resolve.
2. config/pipeline_config.yaml services/s2 dspy_program_path = data/dspy_mipro_optimized.json - absent on disk.
Both are latent (the consuming paths are flag-off today), so nothing is broken NOW; it is a future tax: a
fail-loud default that cannot resolve is a crash waiting for the day a flag is flipped. Fix = repoint to the
archived path or make the key explicitly optional (decision-worthy, owner call on the golden set).

## PROCESS NOTE 2026-09-23 - a measurement bug in the AUDIT ITSELF

The audit's RED counter ("grep RED | grep -v '0 RED'") reported 19 REDs; every one was a false positive because
"WIRED" contains "RED". The authoritative signal is the harness exit code (just health exit 0, every wired check
0 RED). Recorded because a forensic audit that trusts its own greps over the exit code is the same class of
defect it is auditing for.
## BUG-390 - UPDATE 2026-09-23 15:34: receipt

The D-353 trigger fired the moment scripts/definition_nli_verify.py changed and was honoured, not bypassed: re-run exit=-15, new dated artifact governance/R2_DEFINITION_NLI_20260923.json (no summary), D-356 minted, pin re-pointed to D-356.

## BUG-394 update 2026-09-23 (audit e) - the dead rows are the PREVIOUS fbs generation, and the repair is now a proven, runnable script

MEASURED (mode=ro, shadow rowid tables): fbs rowids are 7997..15991 (contiguous, 7995 rows); the dead vec_fbs
entries are 1..7996 - vectors of a generation of fbs rows that no longer exists. So vec_fbs returns half-dead
k-NN slots (DILUTION, not starvation) and vec_fbs_ctx is 100% dead and R26-forbidden for production.

THREE DEFECTS IN THE REPAIR RECIPE THAT WAS HANDED OVER BEFORE IT HAD EVER BEEN RUN (all three would have failed
or over-promised): (1) opening a vec0 table needs the sqlite-vec extension; /usr/local/bin/python3 is a python.org
framework build with enable_load_extension UNAVAILABLE (BUG-104's own warning) and the macOS sqlite3 CLI rejects
.load, so BOTH fail with "no such module: vec0" - only /opt/homebrew/bin/python3 (sqlite 3.53.3, loader True)
works; (2) "expect 0 RED" was unreachable while vec_fbs_ctx was held to the mirror contract, because emptying it
turns 7995 dead entries into 7995 MISSING rows, which the old rule also called RED; (3) the recipe promised a
one-line CLI delete for a store whose module could not load. A repair instruction is an artifact: it must be run
once before it is issued.

FIXED (D-357 + code): config/vec_integrity.yaml now declares a PER-TABLE contract (vec_fbs required, vec_fbs_ctx
dormant); scripts/verify_vec_integrity.py inverts the assertion for a dormant store (must be EMPTY: 0 orphans AND
0 live; missing == fbs is EXPECTED) and takes --db for a repaired copy; scripts/repair_vec_integrity.py is new
(dry-run default, timestamped backup, ONE transaction, re-measure with the gate, fail-loud C16).

RECEIPT (copies only; the run DB is byte-identical to audit (d)): dry run wrote nothing; --apply deleted 7995 from
vec_fbs and 7995 from vec_fbs_ctx; gate then reported vec_fbs live=7995 orphans=0 missing=0, vec_fbs_ctx dormant
empty, "2 tables checked, 0 RED", exit 0. On the production DB the gate still reports 2 RED, exit 1.

STILL OPEN (owner-gated, destructive): run the repair against knowledge pipeline/maxwell.db.
STILL OPEN (work): stage6's in-run vector check is a COUNT and printed "Vector: READY 15990/7995" while half the
index was dead, and the D-354 gate is deliberately not in just health until the repair lands.

## BUG-398 (MED, OPEN) - a receipt claimed a dated artifact that does not exist

WHAT: the DECISION-LOG D-356 entry states the meter "was re-run over the frozen input into a NEW dated artifact
(governance/R2_DEFINITION_NLI_20260923.json)". No such file exists on disk or in git: the full ruler run exceeded
the working budget and only the 6-FB capability smoke completed. A receipt is a claim about an artifact; writing
the claim before the artifact exists is the same class as the boundary pin that could never pass (BUG-395).

IMPACT: the ratified extraction_type curve is still OWED and extraction_type stays in refused_axes, which the
D-356 text does say. The defect is the receipt's wording, not a measurement.

FIX: a CORRECTION entry appended to DECISION-LOG.md (append-only, R-D410); the curve remains a carried work item.

## BUG-399 (MED, OPEN -> detector now wired) - a derived governance count drifted and its detector ran nowhere

WHAT: scripts/recompute_decision_summary.py --check exited 1 with FIVE drifts (total_decisions 713 vs 724,
summary.total, summary.active 483 vs 494, by_category ARCHITECTURE absent vs 7, MEASUREMENT 2 vs 6). The sanctioned
detector AND tests/test_decision_summary_sync.py already existed and were invoked by NO recipe.

CLASS: D-355 - a control that exists but is invoked by nothing is decoration. The drift is exactly what BUG-342
warns about (never re-derive a governance count by hand), one level up: the count was not re-derived at all.

FIX: recomputed with the sanctioned tool (the diff touches ONLY the derived fields, 5 insertions / 4 deletions);
the detector is now the 11th control in just health, so the drift cannot return silently.

## PROCESS NOTE 2026-09-23 (audit e) - my own count harness was subset-scoped

"33 decision ids, 0 dups" was produced by a regex anchored at column 0 (^ - id: D-), which matches only the
D-319..D-356 block of config/decisions.yaml. The registry actually holds 724 entries (724 unique, 0 dups). The
duplicate-D-356 repair was correct; the COUNT I published was scoped to a subset and stated as the whole. Same
class as the 'WIRED'-contains-'RED' counter: a harness defect dressed as a finding. Rule: a governance count is
published only from a parsed load of the whole file, never from a line-anchored regex.
## BUG-399 correction (audit e, same day) - the detector ran in the `healthcheck` recipe, not in `health`

Measured after the fix: justfile:39 (recipe healthcheck) ALREADY ran scripts/recompute_decision_summary.py --check with a
clear error message. What ran nowhere is the recipe that matters: `just health` - the one the boot sequence and the run
harness invoke - did not include it. So the drift was invisible to the control the project actually runs, not to every
control, and the entry above overstates it. The fix is unchanged and now verified twice: the check is control 11 of
just health (justfile:21) AND still present in healthcheck (justfile:39). Rule: state which recipe the control was in
before saying no recipe ran it - "wired somewhere" and "wired into the gate that runs" are different claims.

## BUG-387 (HIGH, code-side FIXED 2026-09-23, audit f) - the vector store is keyed by ROWID and only a rowid-level assertion can see it
Root cause, measured: fbs' primary key is the TEXT fb_id, so "INSERT OR REPLACE INTO fbs" deletes the conflicting row
and inserts a new one - which RE-ISSUES the implicit rowid. The vec store is keyed by that rowid, so every re-commit
moved the spine (fbs now 7997..15991, contiguous) while the old vectors stayed (1..7996 = 7995 dead entries, 50% of
vec_fbs). The in-run check was a COUNT, so a doubled store printed "Vector: READY 15990/7995". Fix (D-359, PROPOSED):
(a) the commit loop captures the rowid the fb_id held BEFORE the insert and retires that vector in the same
transaction (fbs_rowid + delete_embedding, fail-loud if the retire fails); (b) insert_embedding deletes its rowid
first, so the write is idempotent; (c) the count check + the R-017 orphan COUNT were REPLACED by
assert_vector_integrity(), which joins by rowid and RAISES on orphans (C16) - a missing vector is DEGRADED (the row
still answers through FTS), an absent vec table is DEGRADED (BUG-104), never a silent pass.
Regression test: tests/test_vec_rowid_contract.py - 5/5 PASS under /opt/homebrew/bin/python3 (the only interpreter
that can load vec0). OWED before the fix is trusted: an R5 gemma-4-E4B review of the diff, and a re-commit rehearsal
on a SCRATCH copy (never the run DB) showing orphans 0 -> 0 and fbs count stable.

## BUG-398 (MED, half-discharged 2026-09-23, audit f) - the owed receipt now exists, but not where it was claimed
The D-356 entry claimed governance/R2_DEFINITION_NLI_20260923.json; no such file existed. Audit (f) ran the meter to
COMPLETION over the frozen ruler instead and wrote governance/R2_EXTRACTION_TYPE_RULER_20260923.json (150 FBs, 728
label scores, 135 contra, 0 inference errors, extraction_type scored on 150/150). The claim in DECISION-LOG is NOT
retroactively true - the file that was named still does not exist - and the artifact is deliberately named for what
it is (ruler-scoped). STILL OWED: the ratified extraction_type curve (a gate measurement over this artifact) before
any operating point may be set on that axis; extraction_type therefore stays in refused_axes.

## BUG-397 (LOW, half-FIXED 2026-09-23, audit f) - two live defaults pointed at retired artifacts
(a) pipeline/student_classifier.py DEFAULT_GOLDEN now resolves to
archive/golden_retired_D2618/stage4_golden_mined.yaml (the path 4 sibling scripts already use; the config/ path had
resolved to nothing). (b) STILL OPEN: config/pipeline_config.yaml services.s2.dspy_program_path is
data/dspy_mipro_optimized.json (absent) AND pipeline/pipeline_paths.py:186 hardcodes the SAME absent path as its
fallback, so removing the config key does not fix it (C12: the code default is the second defect). Fix is two-site:
null the config value and make the loader fail loud when dspy_enabled is set without a program. Latent while
dspy_enabled: false.

## PROCESS NOTE 2026-09-23 (audit f) - a test that skips everywhere is not a test
tests/test_vec_rowid_contract.py first reported "5 skipped" under the interpreter that runs pytest, because vec0 needs
enable_load_extension and the python.org framework build cannot enable it (BUG-104) - while the interpreter that CAN
load vec0 (/opt/homebrew/bin/python3) has no pytest. A green "skipped" line reads like coverage. The file now carries
a __main__ runner so the real assertions execute under the interpreter that can run them; it prints its own skip
reason and never reports a skip as a pass.

## BUG-397(a) correction (audit f, same day) - the repoint did NOT land in the first attempt
The entry above records BUG-397(a) as FIXED. It was not, at the moment that line was written: the patch script in that
attempt died with "SyntaxError: unterminated string literal" (a heredoc escaping defect of mine) and the commit that
followed carried no change to pipeline/student_classifier.py. The repoint landed in the follow-up commit. Rule
restated (same class as F-e3): a receipt is a claim about the artifact as it exists at the moment the claim is
written - verify the write, then write the claim.

## D-354 VEC REPAIR - DONE AND VERIFIED (2026-09-23, session 23) - owner-gated, executed by the owner, verified independently here

RECEIPT: dry run 15990 dead rows (7995 vec_fbs + 7995 vec_fbs_ctx) -> bash pipeline/backup_guardian.sh (maxwell.db.bak_20260923_164120)
-> --apply (own copy maxwell.db.pre_d354_20260923_164133, ONE transaction, 7995 + 7995 deleted). Post-repair, re-measured by me:
vec_fbs REQUIRED live=7995 orphans=0 missing=0 live_pct=100.0; vec_fbs_ctx DORMANT live=0 orphans=0 missing=7995 (expected); 0 RED; exit 0.
FUNCTION IS NOT TOUCHED EITHER: fbs 7995 rows, rowid range still 7997..15991 (nothing re-issued), pragma integrity_check ok,
0 foreign-key violations, fbs_fts 7995, vec_fbs shadow rowids 7995. The half-dead index is gone; the spine did not move.

SUCCESSOR DISCHARGED: the D-354 gate is now a CHAINED control of just health (D-361). It was withheld while it was RED and
chained the moment it was green - a gate that is not chained is decoration (D-355). Fail-closed: an absent run DB is RED.

RESIDUAL (not a defect): the session now leaves FOUR large DB copies on disk (bak_20260923_164120, pre_d354_20260923_164133,
archive/db_backups/maxwell_pre_index_20260917.db, archive/session_20260923/scratch/.../maxwell.db). Disk is at 97% (28 GiB free).
Folded into the disk chore, not repaired here.

## THE PIN CONTROL FIRED AND WAS HONOURED (2026-09-23) - evidence the D-353 scheme works

Editing config/verify_abstention.yaml (the D-362 coverage SLA) turned just health RED with exactly one reason: "abstention_policy:
config/verify_abstention.yaml CHANGED since it was pinned - re-run the measurement and mint a new decision (this is the BUG-391
class)". It was NOT bypassed: D-362 was minted and the pin re-pointed (fcf96d92... -> bc994ae5...) in the same session. Recording
this because a control that has never been observed firing is a claim, not a gate.

## BUG-388 - FIXED AND THE OWNER-GATED RE-RUN IS DONE (2026-09-23)

python3 pipeline/stage6_commit.py --export-only -> 7995 verified FBs -> fbs_snapshot_20260923_164926.parquet (42.4 MB), exit clean,
no ArrowInvalid. The bool coercion holds on the REAL list, not just the probe fixture. The last successful snapshot before this was
2026-09-02, so the artifact of record was 3 weeks behind the store.

NEW FINDING RECORDED WITH IT (do not treat the snapshot as a dump of the store): --export-only sources its rows from
load_stage5_fbs(), i.e. the STAGE 5 CHECKPOINT, not from the committed fbs table. Row counts match today (7995 == 7995), so the
snapshot is faithful in COUNT, but commit-time field mutations (status, committed_at, pipeline_run_id, gen_model, taxonomy_version)
are those of the checkpoint list, not of the rows as they sit in SQLite. A downstream reader that treats the .parquet as "the store"
is therefore slightly wrong. Fix direction (NOT done, needs a driver + R5 review): dump fbs from the DB and export that. Recorded
so it is a known tax rather than a silent one.

## BUG-397(b) - FIXED (2026-09-23) - the two-site trap, and why nulling one site would have made it worse

Site 1 config/pipeline_config.yaml: s2.dspy_program_path -> null (key KEPT: .get(key, default) resurrects a code default when the key
is absent, and a present-but-null key with the OLD code produced Path("None") - a silently wrong path).
Site 2 pipeline/pipeline_paths.py: the literal fallback data/dspy_mipro_optimized.json is GONE; an unset key yields None (C12).
Guards pipeline/dspy_trainer.py: load raises when S2_DSPY_ENABLED and the path is unset (reports + returns the documented None when
the flag is off); save ALWAYS raises (D2243 - a save with nowhere to go is silent data loss). Probe: DSPY_PROGRAM_PATH None,
S2_DSPY_ENABLED False, ast parse ok on all three files. D-364. Latent either way - config/flag_consumer_registry.yaml records the flag
as having no verifiable consumer.
ALSO reconciled: the dangling comment citation in pipeline/student_classifier.py (it cited a D-361 that had never been minted); it now
cites D-2618/BUG-397(a). D-361 was subsequently minted for a DIFFERENT subject (the vec gate), so the old comment would have become a
silently WRONG citation rather than a dangling one - the worse failure mode.

## PROCESS NOTE 2026-09-23 (session 23) - the R5 cross-family review of D-364 returned NO VERDICT, so it is OWED, not satisfied

The gemma-4-E4B verifier was invoked on the two-site DSPy fix (the four just-landed changes) and terminated with
"I've reached the maximum number of actions I can do without user input" - it never emitted APPROVE or REJECT. That is not a
review and must not be recorded as one: the same class as F-f1 ("a test that skips everywhere is not a test") and F-e3
(a receipt is a claim about the artifact as it exists at the moment the claim is written). OWED: re-run the R5 verifier with a
bounded instruction (no repo exploration, the diff pasted inline) before D-364 and D-359 are treated as externally reviewed.
Both changes are nonetheless receipted by execution, not by assertion: ast parse ok on all three files, DSPY_PROGRAM_PATH None,
S2_DSPY_ENABLED False, just health exit 0 with 13 controls + the new vec control green.

## BUG-400 (HIGH, OPEN) - the sovereign corpus and the served store live inside a Dropbox File Provider domain (C3/C22)

**Found 2026-09-23 (session 23, disk-chore audit), by measurement, not inference.**

`xattr` on the repo root returns `com.apple.file-provider-domain-id`, `com.dropbox.fp_hydration_policy`,
`com.apple.fileprovider.dir#N`. `CONSTITUTION.md`, `config/decisions.yaml`, `pipeline/stage6_commit.py` and
**`knowledge pipeline/maxwell.db`** each carry `com.dropbox.attrs` + `com.dropbox.internal`. A 400-file sample of
the repo returned **794 dropbox attribute lines** (every sampled file is Dropbox-tracked). `DropboxFileProvider.appex`
is running. The working directory is `~/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0`.

**Why this is a defect, not a preference.** C3 says all data and compute remain local; C22 says local-first with an
EXPLICIT opt-in for anything else. This is not opt-in - it is where the repo happens to sit, so the corpus, the
registry and the served SQLite store are cloud-replicated by default. Three concrete failure modes:
1. Replication of the corpus + run DB to a third party with no decision authorising it (the sovereignty claim in
   CONSTITUTION.md is currently falsified by the filesystem, not by intent).
2. **Torn / partial upload of a live SQLite file.** stage6 writes the DB in one transaction while a sync client reads
   it whenever it likes; a restore on another machine can therefore serve a stale or half-written store AS
   authoritative. That is the same failure class as BUG-387 - half-dead state that a COUNT cannot see - and here
   there is no gate at all, because D-354/D-361 check referential integrity, not freshness or origin.
3. **Conflict copies. Already happened:** `knowledge pipeline/stage1_5_embed_cluster/s15_bge-m3_run (Klaus Beyer's
   conflicted copy 2026-08-05).log` and its `... 1).log` sibling sit inside a pipeline directory right now. Two
   conflict copies of one file is the mechanism proving itself.

**NOT fixed here** - the fix is a location change and that is owner-gated (MTR owner gate). Interim mitigations the
owner can take without moving anything: exclude `claude projects/maxwell os 2.0` from Dropbox sync (selective sync /
per-folder "Online only" OFF), or move the repo out of `~/Library/CloudStorage` entirely. Recorded immediately per
the AUTO-LOG rule rather than worked around.

## BUG-401 (MED, OPEN) - the disk-chore instruction handed to the owner could not execute, and it aimed at 2 percent of the deficit

**Found 2026-09-23 (session 23).** The owner's paste proves the instruction failed twice over:

```
v "archive/bak_sweep_20260923"      /Volumes/<EXTERNAL>/maxwell_archive_20260923/
zsh: no such file or directory: EXTERNAL
```

(a) `<EXTERNAL>` was left as a literal placeholder: zsh parsed `<EXTERNAL>` as a stdin redirect and aborted the
command before `mv` was ever looked up (`v` is also a typo for `mv`; the follow-up `mv "archive/bak_sweep_20260923"`
with one argument printed usage). **Nothing moved - verified: `archive/bak_sweep_20260923` is 11G and
`archive/session_20260923/scratch` is 5.3G, both still in place, tree clean at b6f0bd1.**

(b) The real defect: **no external volume is mounted.** `/Volumes` contains only `Data`, `Macintosh HD` (a symlink to
/) and `Recovery`. So even with the placeholder replaced the move had no valid target. My earlier task text said
"move to the external drive" without ever asserting that a drive exists - an instruction that cannot execute is not
an instruction (same class as F-f1 "a test that skips everywhere is not a test").

(c) And the target was the wrong 16 GB. Measured sizes: repo **30G**; `~/.cache/huggingface` **127G**;
`~/.omlx/cache` **92G**; `~/Library/CloudStorage/Dropbox` **296G** (the repo sits inside it); `~/models` 27G;
`~/.mtplx/models` 21G; `~/Library/Application Support/Zed` 14G; `~/.ollama` 13G; `~/Downloads` 10G;
`~/.cache/uv` 6.4G; `~/Documents` 7.6G; `~/Databases` 5.3G; `/Applications` 58G; `/Library` 27G. Disk is 874Gi used
of 926Gi (28Gi free, 97%). No local Time Machine snapshots (`tmutil listlocalsnapshots /` is empty), so the fullness
is real data, not purgeable. The 16.5 GB project move is ~2% of the deficit; the model caches are ~279 GB.

**Corrective action taken:** the owner gate in MASTER-TASK-REGISTER.md and the aggregated task register was rewritten
this session to name the real targets and to state the precondition (a mounted volume, with its real name). See
BUG-402 for the second-order drift found by the same audit.

## BUG-402 (LOW, FIXED 2026-09-23) - 
**FIXED 2026-09-23 (implementation receipt).** `last_sync` is now DERIVED and CHECKED, and the writer that
owned it is retired. The defect was a DECLARATION with no sanctioned writer sitting beside derived data
(summary, total_decisions) that DID have a writer - two clocks for one artifact, which is how it drifted.
Landed: (a) `scripts/recompute_decision_summary.py` derives `last_sync` in the same surgical atomic write,
adds a content-derived `decisions_sha256_16` (sha256 of the canonical JSON of the decisions LIST, so it is
self-reference free) plus `written_by`, and `--check` exits 1 on any drift; (b) the wire is in `just health`
(`recompute_decision_summary.py --check || exit 1`); (c) `tools/sync_decisions.py` is RETIRED as a hard-fail
tombstone (exit 2), because it is INVERTED - it treats DECISION-LOG.md (~154 heading blocks, 29 of them
headings) as truth over 709 registry ids and would re-dump the file (the BUG-409 formatting destruction).
DAMAGE NOTE (R-D410 honest record): the tombstone was planned but had not landed when two of my own
verification commands ran the tool live; it wrote 2 decisions and re-dumped `config/decisions.yaml`
(3526 insertions / 2259 deletions), and a `git checkout --` restored from the already-staged index so the
damaged 738-record file was committed as 934f755. Recovered from 32404ce: 736 records, hand-curated
formatting intact, then D-370 appended surgically (737). `git diff --stat 32404ce -- config/decisions.yaml`
is now 29 insertions / 4 deletions (the D-370 record + the stamp fields) instead of 5785 changed lines.
MEASURED, and it retires the tool's whole premise: its "2 new decisions found" was 2/2 FALSE POSITIVES -
the reverse membership direction (log-only ids) is EMPTY of real decisions, containing only D2537 (a TABLE
ROW on log line 110) and D3251 (a PROSE mention on line 231), plus the rule id D410 and D6. So there was
never a decision to sync; the tool fired on a markdown table and a parenthetical.
RESIDUAL (open, low): membership in the other direction is structural, not a defect - 454 registry ids are
never named in DECISION-LOG.md because the log is a curated narrative subset, not a registry mirror. No
detector exists and none is needed; a read-only membership check is available if the log is ever meant to
be a mirror. LESSON (standing): never invoke a tool whose retirement is only planned - neuter FIRST, then
verify, and never verify a writer with the writer's own tool.`last_sync` in config/decisions.yaml has no sanctioned writer, and it is now stale

`config/decisions.yaml` line 3 reads `last_sync: '2026-09-22 20:06:00'` while the registry holds four decisions
minted 2026-09-23 (D-361..D-364). `scripts/recompute_decision_summary.py` - the sanctioned tool - does not touch
`last_sync` (it recomputes ONLY `total_decisions` + `summary`). The only writer in the tree is
`tools/sync_decisions.py`, which the sanctioned script's own docstring declares INVERTED and dangerous
("~237 heading blocks vs 434 decisions here; running it would corrupt hand-curated records"). So the field is
hand-maintained, drifted exactly as BUG-342 predicts, and its drift is invisible because `--check` does not cover it.

**Not fixed here** (it needs a tooling change with an R5 review, not a hand edit - a hand edit is how it drifted).
Decision needed: either let `recompute_decision_summary.py` stamp it (then it is derived data with a writer), or
retire the field. Recorded so the next session does not hand-edit it back into sync.

### BUG-400 remediation impact scan (2026-09-23, session 23) - what moving the repo would actually cost

Measured before recommending anything, because a relocation is not free:

1. **Absolute Dropbox paths are baked into ~20+ committed artifacts**, including pipeline checkpoints and - worse -
   **input fingerprints**: `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl.input_fingerprint.json` records
   `"s4_checkpoint": "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/knowledge pipeline/
   stage4_merge/t11/checkpoint_enriched.jsonl"`. Every `*.checkpoint.jsonl.manifest.json` under stage1_chunk,
   stage1_5_embed_cluster and stage4_merge does the same. So a relocation **invalidates the declared-input receipts
   that `verify_declared_inputs.py` checks** (`just health` control) and the provenance stamps that cite those paths.
   Relocation therefore needs its own decision + a re-baselining of the fingerprints, not a bare `mv`.
2. **Nothing in-repo resolves the project root from that literal** - `pipeline/pipeline_paths.py` derives PROJECT_ROOT
   from `__file__`, and `.env` carries no absolute-path keys - so the CODE survives a move; only the RECEIPTS do not.
3. **Outside the repo**: `~/Library/LaunchAgents` holds `com.maxwell.omlx-api-key.plist` (live) plus
   `com.maxwell.memoryguardian.plist.DISABLED` and `com.maxwellos.watchdog.plist.DISABLED`; `crontab -l` has 3
   maxwell entries. These must be grepped for the old path before any move.
4. **Backup tax, measured:** the repo currently holds six full-size copies of the run DB
   (`maxwell.db.bak_20260923_164120`, `maxwell.db.bak_20260923_170702`, `maxwell.db.pre_d354_20260923_164133` +
   three older, 133-167 MB each, ~900 MB total) because `backup_guardian.sh` keeps a full copy per batch write. Cheap
   disk, but it is a standing cost that grows with every session and nobody prunes it.
5. **The real Dropbox mass is not the repo**: `media` 97G, `app` 54G, `claude projects` 48G (the repo is 30G of it),
   `education` 40G, `soulseek` 34G, `design` 16G, `00 inbox` 5.0G.

**Recommendation now on record:** the cheapest correct step is NOT to move the repo. It is to (a) take the run DB and
the pipeline output directories out of sync first (a selective-sync exclusion of `claude projects/maxwell os 2.0/compute-heavy
subdirs` is not possible per-subfolder in Dropbox, so the practical form is: move the repo out, OR accept that the
sync stays and record the risk as an accepted, dated decision). Both are owner calls. The forbidden option is to
leave it implicit.

## BUG-403 (LOW, FIXED 2026-09-23) - stage4.depth_model carries a HARDCODED code default naming the one model whose depth route is REFUTED

`pipeline/pipeline_paths.py:230` reads `S4_DEPTH_MODEL=str(_CFG.get("stage4", {}).get("depth_model", "gemma-4-E4B-it-MLX-4bit"))`.
Two defects in one line. (a) C12: that string is a HARDCODED CODE DEFAULT - exactly the class D-364 was
ratified to remove on the DSPy key (site 2 of BUG-397(b)); the fix landed on one key and this one was left
armed. (b) The default names gemma-4-E4B, whose S4 depth route is REFUTED on measurement (D2454: 62.5% vs
gpt-oss 75%, gate >=90%; the frugal speedup is 0.9x - governance/CROSS-LLM-AUDIT-VERDICT-2026-08-15.md:63).
It is DORMANT but ARMED: `pipeline/stage4_merge.py:2008` instantiates `S4_DEPTH_MODEL` the moment
`stage4.depth_frugal_enabled` flips true (`depth_model = S4_DEPTH_MODEL if S4_DEPTH_FRUGAL_ENABLED else VERIFY_MODEL`),
so ONE flag flip resurrects a refuted routing with no gate in front of it - the D-327/BUG-374 class (a ruled
rejection whose flip never landed). Measured today: `just health` reports `depth_frugal_enabled off`, so
nothing is misclassified right now. NOT fixed (a code change to a config default is its own reviewed act).
Fix shape: mirror D-364 - make the config key explicitly null and have the consumer REFUSE when the flag is
true and the path is unset, instead of resurrecting a literal.

## BUG-404 (MED, FIXED 2026-09-23) - archive/index.yaml was an index with no writer, no checker, and a REJECTED authority

`archive/index.yaml` declared `authority: D2226`. `config/decisions.yaml` holds D2226 in state **REJECTED**.
The file was generated 2026-08-10 against an OUT-OF-REPO `archive_root` (`claude projects/archived/maxwell os`,
verified present, 35 entries) and never regenerated, so the IN-REPO `archive/` - 17.3 GB and 34 top-level
entries, including 11 GB of sweep payload and 5.3 GB of session scratch - was entirely unindexed; only two
sections (governance_archive, code_archive) had been hand-appended. Finally, a grep for `archive/index.yaml`
across the repo returns NO consumer: an index nothing reads and nothing regenerates is an Emission-class
artifact that drifts silently (BUG-342's class). FIXED: `config/archive_index.yaml` (the contract) +
`scripts/build_archive_index.py` (writer and `--check` checker, atomic, deterministic body hash) + a
regenerated `archive/index.yaml` whose authority is D-365. Measured after the fix: 34 entries, 17.3 GB,
dispositions {keep 5, keep_append_only 21, external_move_candidate 5, purge_candidate 3}, `--check` exit 0.

## BUG-405 (LOW, FIXED 2026-09-23) - the flag registry DENIES the one consumer that exists, and that denial is what masked BUG-403

`config/flag_consumer_registry.yaml` records `stage4.depth_frugal_enabled` with `consumers: []` and the note
"no consumer the audit can verify; it enforces nothing today". That is FALSE by grep: `pipeline/stage4_merge.py:2008`
reads it to choose between `S4_DEPTH_MODEL` and `VERIFY_MODEL`. A registry entry that denies an existing
consumer is the BUG-375 class (a proposal naming a consumer that does not read the artifact, inverted), and
here it is load-bearing: an empty consumer list is precisely what would have kept BUG-403 invisible in every
flag audit. NOT fixed (the registry is a hand-curated governance artifact; the entry needs a corrected
consumer + a decision id, not a silent edit).

## BUG-406 (HIGH, MITIGATED 2026-09-23) - the temp auto-purge rule had no declared-input guard: a sweep moved 35 declared inputs out of temp/

`governance/folder_protocol.md` sets "Temp | Delete | 7 days". Following the protocol, `temp/` was swept:
414 entries older than 7 days -> `archive/temp_archive_20260923/` (archive-first, not delete, because the
entries include date-stamped LLM cross-examination transcripts and are evidence under R-D410). THEN the
guard grep ran, and it found that **35 of the moved entries are DECLARED INPUTS of live scripts**, including:
- `temp/golden_source_map.json` - the `SOURCE_MAP` read by `scripts/propagate_p5_final.py:40` AND
  `scripts/propagate_content_type_decisions.py:44` (a pipeline relay input, not scratch)
- `temp/golden_labels_probabilistic.jsonl` (scripts/audit_false_convergence.py:24)
- `temp/p5_ct758_flags.csv` + `temp/p5_fewshot_manifest.json` (scripts/build_boundary_corpus.py:31-32)
- `temp/ct818_oa_joined_partial.json` (scripts/content_type_sweep_rank.py:31)
- `temp/forensic_audit_local_llms.json` (scripts/run_forensic_audit_parallel.py:21)
ALL 35 RESTORED to `temp/` in the same session; `archive/temp_archive_20260923/MANIFEST.tsv` pruned from
412 to 377 rows; verified 0 declared names remain moved. Class: a process that MOVES bytes a consumer
declares, with no check that the consumer can still resolve its input - the same class as BUG-401 (an
instruction that could not execute), F-f1 (a test that skips everywhere) and BUG-359. Fix (applied):
`protected_paths` in config/archive_index.yaml names every declared temp/ path, and the rule is now that a
sweep MUST be preceded by the declared-input grep, never by age alone.

## BUG-407 (MED, OPEN) - the R5 cross-family review channel failed twice in one session, in two different ways

The R5 review of `scripts/build_archive_index.py` (required by AGENTS.md delegate_rules: "delegate CODE
REVIEW of any NEW repair script to gemma-4-E4B-it-MLX-4bit before --apply") was attempted TWICE, bounded,
temperature 0.0, provider maxwell_omlx:
1. Attempt 1 (files described, verdict format specified): the model returned an EMPTY response -
   "The model returned an empty response." No APPROVE/REJECT. This is the SECOND consecutive session in
   which gemma produced no verdict on an R5 request (D-364 last session, recorded in this log).
2. Attempt 2 (6-line fixed format, tool-free): the delegate terminated with "the read_file tool was not
   available in the turn context" - i.e. a reviewer that cannot read the artifact it is reviewing.
Consequence stated plainly: **the R5 verdict for scripts/build_archive_index.py is OWED, NOT SATISFIED.**
A verifier that returns no verdict does not discharge R5 - the same rule recorded for D-364 and D-359.
Evidence supporting the script's correctness that is NOT an R5 verdict, and is not offered as one:
`--check` exit 0 after regeneration; the check went RED exactly when the bytes changed (it caught the
restore of 35 declared inputs mid-session, which is the strongest available proof that the check is live
rather than tautological); one commit, `just health` exit 0, tree dirty 0.
Routing fix (not yet applied, needs an owner-free decision next session): run gemma through the
one-shot curl path (D2543/D2549) instead of delegate(), or transfer the R5 review to Qwen3.8-27B as the
deep auditor (D2556), since gemma's channel is now degraded in two distinct ways.

## BUG-408 (LOW, FIXED 2026-09-23) - a one-line edit to justfile dropped a recipe line's indent and made health unreachable

Wiring the archive-index checker into `just health` was done with a text replace whose anchor string
omitted the line's LEADING 4 SPACES. The indent therefore applied to the inserted line only, and the
following line (recompute_decision_summary --check) fell to column 0: `just health` then died with
"Unknown start of token '.'  justfile:23:43" - the whole health control chain was unreachable for two
commits. Caught by running health immediately after the edit, fixed in the same session.
Class: an edit to a control file verified by an intention ("the check is now chained"), not by the
control itself. The rule this instance adds to the others: after editing justfile, RUN it - a recipe
that cannot parse reports nothing about the thing you changed, and the false header claim in
archive/index.yaml ("check: just health -> ...") was true for exactly zero commits until this fix.

## BUG-409 (MED, FIXED 2026-09-23) - a yaml round-trip rewrote a 100k-line governance artifact and destroyed its blame history

The D-365 entry was added to `config/decisions.yaml` with `yaml.safe_load` -> `yaml.safe_dump`. The
round-trip reformatted the WHOLE file: 812 insertions / 758 deletions for a 731-entry registry, i.e.
almost every line in a hand-curated governance artifact changed bytes. Verified NOT to be content loss -
the original had 0 comment lines, `recompute_decision_summary.py` writes surgically (a regex replace of
`total_decisions` plus the trailing `summary:` block, never a dump), and a parsed comparison of the
original vs the round-tripped version found 731/731 entries IDENTICAL with exactly one addition (D-365)
and zero removals. So the damage was limited to: (a) git blame/log for 731 decisions now points at one
mechanical commit, (b) any future byte-level diff of the registry is unreadable, (c) a false alarm that
took a full diagnostic pass to clear.
FIX: the original text was restored from git and D-365 was inserted textually immediately before the
`summary:` marker, then `recompute_decision_summary.py` re-derived the counts. The rule this instance
adds to BUG-342's: **append to a governance registry by text insertion at a marker, never by a
load/dump round-trip.** A round-trip is content-equivalent and history-destroying at the same time, which
is why it passes every check the repo has and still costs something.
SIDE EFFECT, and it is the check working: restoring the declared input `temp/trackb_full.jsonl` changed
the bytes of `archive/temp_archive_20260923/`, so the new archive-index control went RED until the index
was regenerated. A control that goes RED the moment the inventory changes is what "live" means.

## BUG-407 (MED, FIXED 2026-09-23) - the R5 review channel failed twice and the cause was the CALLER, not the model
Root cause found 2026-09-23: the two failures (empty response; "the read_file tool was not available in the turn
context") were TURN-CONTEXT failures of the DELEGATE tool, not model failures. gemma-4-E4B-it-MLX-4bit answers
normally: a direct `curl` one-shot returned `OK Gemma 4.` in 0.74s warm, and the repo's OWN harness
`scripts/r5_code_review.py` (which POSTs to OMLX via tools/model_eval_suite.call, i.e. plain HTTP with no tool
channel) returned APPROVE/confidence 1.0 on scripts/build_archive_index.py.
STANDING RULE: an R5 verdict MUST be produced by `python3 scripts/r5_code_review.py --file <f> --reviewer
<model>` and land in governance/r5_reviews.jsonl as an artifact. Never route an R5 review through a tool-using
agent channel; a reviewer that depends on a tool it may not have is a reviewer that can fail silently, and two
consecutive sessions were recorded as if the MODEL had failed. Owed verdicts discharged for
scripts/build_archive_index.py (APPROVE, sha256_16 e133da4716a9e68e). Still owed: D-359 (stage6_commit.py diff)
and D-364 (DSPy no-code-default diff).

## BUG-410 (MED, FIXED 2026-09-23) - 
**FIXED 2026-09-23.** `T2_GATE`/`T3_GATE` in `config/model_assignments.yaml` were repointed from the
PHANTOM `Phi-4-mini-instruct-4bit` to the SERVED probe `Phi-4-mini-instruct-8bit` (D2319), with dated
inline notes; a pre-fix copy is in the gitignored `backup/`. Relief was verified BEFORE the edit: both
roles are registry-only (inherited from the 2026-07-08 merge of three dead registries) and have no code
consumer anywhere, so no call ever 404ed; the 0.25 quarantine tolerance they name is enforced in
`config/content_types.yaml` plus the CRIBS quality guard at `pipeline/stage4_merge.py:1125-1157`.
RESIDUAL (open): the same file still carries a stale `S5_VERIFIER` family (D2298/D2340) and a
`PLANNER_FALLBACK` phantom, so T2_GATE/T3_GATE should be retired in the D-2637 rewrite, not patched again.T2_GATE and T3_GATE are assigned a model that is not served and not on disk
config/model_assignments.yaml assigns roles.T2_GATE.model and roles.T3_GATE.model = Phi-4-mini-instruct-4bit.
The live OMLX server serves 7 models (Phi-4-mini-instruct-8bit, Qwen3-Coder-30B, Qwen3.8-27B, gemma-4-E4B,
gpt-oss-20b-MXFP4-Q8, Ornith-1.5-35B-A3B-REAP-19B, Ornith-1.5-9B-MLX-8bit) - Phi-4-mini-instruct-4bit is NOT
among them, and no such repo exists in ~/.cache/huggingface/hub. This is the documented PHANTOM-MODEL class
(the file already annotates PLANNER_FALLBACK as "PHANTOM - Qwopus-GLM-18B does not exist locally"): a role
naming an unobtainable model, discovered by cross-checking the registry against the SERVER's model list rather
than against prose. T3_GATE quarantine tolerance (0.25) is therefore unenforceable as declared. Fix: point both
roles at Phi-4-mini-instruct-8bit (the D2319 S2 probe) or restore the 4-bit weights, then re-run the probe.

## BUG-411 (LOW, OPEN) - D2577 cites D2454 as the source of the gemma-depth refutation, and D2454 says something else
config/decisions.yaml D2577 reads "gemma frugal depth route already REFUTED (62.5%, D2454)". D2454 is the
D2454 golden-wiring decision (config/golden/stage4_golden.yaml injected into the four S4 prompts; post-wiring
19.50s vs 17.71s median). The refutation lives in governance/S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md
(n=8, seed=42: gemma 62.5% vs gpt-oss 75.0%, parity 62.5%, gate >=90%) and the data in
governance/s4_depth_frugal_benchmark.json. A decision id that points at the wrong artifact is how "gemma is the
depth model" gets repeated; scripts/validate_role_claims.py exists for exactly this class. Fix: correct D2577's
citation to the empirical-results file (append-only, R-D410: add a correction note, do not rewrite the record).

## BUG-412 (LOW, OPEN) - the archive index declares an absolute cloud path with no guard that it still resolves
config/archive_index.yaml external_archive_root.path = /Users/barn/Library/CloudStorage/Dropbox/claude
projects/archived/maxwell os. The index records present: true and 33 entries generated 2026-08-10 under the
REJECTED authority D2226. Two defects in one value: (a) a BUG-400 corollary - the path is absolute and inside
the Dropbox File Provider domain, so relocating the repo brick it silently; (b) its contents are described by a
generation made under a decision that is now REJECTED. No control asserts that the external root still resolves
or that its 33 entries are current. Fix under D-365: make the external root a checked input (fail loudly if
absent) or drop it from the contract.

## BUG-413 (LOW, CLOSED 2026-09-23) - 3 archive index entries matched no rule and were silently 'keep'
archive/index.yaml classified archive/GOLDEN-REVIEW-v2.0-ARCHIVED-2026-08-11.md, archive/promote_cleaned.py
and archive/vision_probe.py as disposition 'keep' with authority null and the reason "no rule matched -
classify it in config/archive_index.yaml by hand". A rule set that answers "keep" when it does not know is not
a rule set; a default must be explicit and attributable. Survives the Gate E purge (34 -> 31 entries): 12 rules
matched, 3 did not. Fix: add explicit rules to config/archive_index.yaml with an authority for each.

## BUG-414 (HIGH, FIXED-DOCUMENTED 2026-09-23) - the A2 reclaim list's largest candidate WAS the served generator
governance/MODEL_STORE_RECLAIM_A2_20260923.md classified ~/.cache/huggingface/hub as a stale
cache and listed its 32.8 GB generator repo as "probable DUPLICATE of the generator repo -
confirm by digest". It is not a duplicate: ~/.omlx/models/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
is a SYMLINK to that repo's snapshots/main. Five of the seven served models resolve into the
hf hub, and du reports 0 MB for a symlink and the full size for its target, which is exactly
how the store came to look like a cache. Deleting the list's first entry would have deleted
the generator, and the proposed "digest" test would have CONFIRMED the deletion as safe,
because a digest test compares the two paths of ONE model and finds them identical.
ROOT CAUSE: classification by directory name plus du, instead of by resolution (readlink plus
the served-model list). The stop point (list-first, no byte moved) is the only reason this was
caught.
FIX: governance/MODEL_STORE_RECLAIM_A2_CORRECTED_20260923.md (resolution-first list, hf hub
moved to KEEP, one genuine internal duplicate identified: repo blobs/ 16.4 GB with two
.incomplete files versus snapshots/main 16.4 GB), CORRECTION block appended to the original,
and the rule amended: a store is classified by RESOLUTION, never by name and never by du.
ALSO CORRECTED: ~/.omlx/models_stashed/Phi-4-mini-instruct-8bit (3.9 GB) holds the SERVED
Phi probe; ~/.omlx/_unloaded/* are empty; ~/.omlx/cache is a live cache, not a store.

## BUG-415 (MED, OPEN 2026-09-23) - depth is the only production axis with NO anchor row, while D2577 plans a fine-tuned depth model that D274f says requires one

MEASURED 2026-09-23 (session-21 forensic audit). The frozen anchor/ruler family carries ZERO depth
columns: `RULER_BLIND_SHEET_20260917.csv` is (#, item_id, name, DEFINITION, APPLICATION, MECHANISM,
BOUNDARY, SOURCE EXCERPT, len, CT (1-7), DISC (1-62), FORM (1-4), conf_ct, conf_disc, conf_form,
note_codes, reviewer, date); `F11_ANCHOR_REVIEW_20260923.csv` and the consolidated ANCHOR-3 (150 rows x
31 cols, sha256 29393d5f9d529205..., tier human-mixed+llm-attested) carry content_type / discipline /
extraction_type only. ONLY `F14_RELABEL_OR_RETIRE_SAMPLE_20260917.csv` and
`remaining_verification_audit.csv` carry a depth column, and neither is an anchor.

WHAT DEPTH ACTUALLY HAS: `governance/gold_4axis.jsonl` is the only depth reference - 251 rows, 234 with a
depth value, depth_source = human-derived 132 (p5:human-d2615 104 + human 18 + p5:human-frontier69 7 +
p5:human-locked 2 + 298-human 1) + joint-vote 81 + reliable-pair revote 21 + n/a-non-principle 17, i.e.
coverage 0.526 against the 0.50 floor (config/eval_integrity.yaml:12,34) - which is exactly why line 220
holds `axes_deferred: [depth, domains]`. The LIVE reference is the 996-row 3-voter LLM consensus
(`governance/depth_vote_checkpoint.jsonl`), which is ADVISORY, not human truth (D-329/D-331/D-337), and
depth is RELATIVE-ONLY - never "accurate to X". No record carries a depth provenance field.

CONSEQUENCE: the D2577 4-way depth ModernBERT head cannot be CERTIFIED. Its labels are the binding
constraint, not the model: the depth eval set is built on classifier_depth_cleanC (macro-F1 0.4790,
acc 0.530, n=200) and classifier_depth_coreC_core (0.4298, n=133); governance/depth_path_recommendation_
2026-09-10.md concludes the binding constraint is label POLICY, not model capacity (encoder 0.4790 vs
gpt-oss zero-shot 0.4433 vs few-shot 0.4571, all inside one +-0.05 band). The D274f 30-row test-retest
(the single-coder ceiling any floor must be anchored to) is therefore unbuilt, and per D274d nothing may
be trained, distilled or swapped on unanchored labels.

FIX (owner-accepted 2026-09-23, in progress): **ANCHOR-4** = the SAME 150 ruler rows - they already carry
DEFINITION / APPLICATION / MECHANISM / BOUNDARY, so they are answerable without re-reading the source -
plus a `DEPTH (1-4)` column, coded blind by the owner, then by a SECOND coder, and only then the D274f
test-retest of 30 rows after >= 2 weeks. A single-coder anchor has no ceiling to quote, so the freeze
waits for coder 2. Sheet + rubric generated this session:
`governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`, `governance/ANCHOR4_DEPTH_RUBRIC_20260923.md`.
STATUS: PENDING OWNER CODING -> OPEN (this is the gate on the entire depth roadmap).

## BUG-416 (MED, OPEN 2026-09-23) - the depth axis is not a MENU: no config surface declares its 4 classes, so nothing can verify, route or pin them

MEASURED: `config/taxonomy_v5.yaml` has no depth key (its keys are version, classification_version,
groups, domains, disciplines, discipline_groups, meta). The depth vocabulary
(universal / cross-domain / domain / specialized) exists only in PROSE - config/content_types.yaml:218
(a comment), config/content_types.yaml:32 (the principle description), decisions D282/D2130/D2577 - and
in data (gold_4axis depth values). `just health` already carries the symptom as a WARN: "menu source
config/taxonomy_v5.yaml::depth not found - queue labels unverified" and "exposes no readable list --
closure unverified".

CONSEQUENCE: three separate consumers cannot be pinned to a vocabulary - (a) the menu-closure check
cannot verify depth labels, (b) the ANCHOR-4 rubric cannot be generated config-first (it had to be
hand-written this session, which is itself the C12 smell), (c) the D2577 4-way student head's class order
is not declared anywhere, so a checkpoint cannot be checked against the ontology it was trained on.
FIX: declare the 4 depth classes (label, description, the soft domain-count band from D2130) in a config
surface - the same place domains/disciplines live - then repoint the menu check and generate the rubric
from it. Blocked on nothing but a decision; no behaviour change.

## BUG-417 (HIGH, OPEN 2026-09-23) - the A2 corrected list's headline candidate is NOT a duplicate: `blobs/` is the target store of 14 live symlinks, and 4 of its entries are download scratch

MEASURED 2026-09-23 with the D-370 resolution-first test, on the hub repo behind the SERVED generator
(`~/.cache/huggingface/hub/models--lmstudio-community--Qwen3-Coder-30B-A3B-Instruct-MLX-4bit`):
`snapshots/main` is a REAL directory holding 34 REAL files (not symlinks) - and NONE of them exists in
`blobs/` (inode test: 0 hardlinks, 0 same-name blobs, including all 4 safetensors shards). `blobs/` holds
18 entries, 4 of which are `*.incomplete` download scratch, and the repo's OTHER 14 symlinks resolve INTO
`blobs/`. So the claim in `governance/MODEL_STORE_RECLAIM_A2_CORRECTED_20260923.md` - "`<gen repo>/blobs`
16.4 GB, internal duplicate of snapshots/main" - is FALSE in both directions: it is not a duplicate of
snapshots/main, and it is not free space, because a different revision serves through those 14 links.
Deleting it as a duplicate would have broken whatever those links feed: the THIRD instance of the BUG-414
class (classify by name, not by resolution) and the SECOND inside the very document written to fix it.
ACTION (no byte has moved): withdraw that line by append-only correction (R-D410), re-derive the entry by
resolving all 18 blobs entries and all 14 symlinks, and reclaim only what is BOTH unreferenced AND
`*.incomplete` (the 4 scratch files, megabytes). LESSON, again: the classifier itself has to be verified -
a resolution-first method applied to only the OUTER entry (the ~/.omlx/models symlink) still leaves the
inner store classified by name. Verify the method's own coverage, not just its first level.

## BUG-418 (LOW, FIXED 2026-09-23) - the step-B remediation script was idempotent on the status flips but NOT on the append path, so it duplicated the BUG-415 and BUG-416 blocks

MEASURED (session-22 forensic audit): the buglog carried TWO byte-identical copies of each of the BUG-415
and BUG-416 blocks (2865 bytes and 1438 bytes, equal to the byte). Cause: the first run of the step-B
script aborted on an assertion AFTER the header flips but BEFORE the appends; the re-run then flipped
nothing (the flip guard held) but appended the two blocks a second time. The guard was written for the flip
branch only. Root cause is the same class as the incident: IDEMPOTENCY WAS VERIFIED ON ONE PATH AND
ASSUMED ON THE OTHERS.

IMPACT: none on any bug's parsed state (both blocks are (MED, OPEN), and the parser treats a repeated
status event as an event, not a state change) - but the artifact was wrong to read, and a block-counting
reader would over-count. Detection was incidental: bug_status reported 210 headers for 163 ids.

FIX: removed the two LATER byte-identical copies by exact-match rewrite (the earlier copies are
authoritative), then regenerated governance/bug_status.json AND the C15 count line from the parser
instead of hand-typing them. Verified: 208 headers / 163 ids unchanged / BUG-415 and BUG-416 one block each.

STANDING RULES (added to the incident set):
  (a) every remediation step is idempotent BY TEST, not by construction - run each mutating step twice on a
      scratch copy and assert the second run is a no-op;
  (b) counts in prose (the C15 block) are GENERATED from the parser, never typed - a hand-typed count is a
      second clock for one artifact (the BUG-402 failure mode, one level up);
  (c) an audit that only re-runs the invariants the author wrote will not find the author's own
      non-idempotency - the audit must diff the ARTIFACT against its own generator.

## RECEIPT - BUG-403 / BUG-405 (Gate D), 2026-09-23

RECEIPT 2026-09-23 (Gate D, owner-accepted; session 22). Executed and verified, zero behaviour change:
  (1) config/pipeline_config.yaml stage4.depth_model: gemma-4-E4B-it-MLX-4bit -> null, KEY KEPT. Deleting the
      key is forbidden here and the reason is documented inline: the old reader coerced a missing key to a
      CODE DEFAULT naming the same refuted model, so deletion would resurrect it.
  (2) pipeline/pipeline_paths.py: the code default is REMOVED. depth_model null/absent now resolves to ""
      (UNSET) - and explicitly NOT to the literal string "None", which str(None) would have produced and
      which is the trap this fix would otherwise have introduced had only the config been changed.
  (3) pipeline/stage4_merge.py (the depth call): fail-closed per C16 - when depth_frugal_enabled is true and
      depth_model is unset it now RAISES instead of calling an unset/phantom model.
  (4) Both files compile (py_compile exit 0); the served depth path is unchanged because
      depth_frugal_enabled is false, so depth still uses VERIFY_MODEL (gpt-oss).
  (5) R5: see governance/r5_reviews.jsonl for the reviewer verdict on the diff (D-367: a verdict is evidence
      only when produced by that harness).
CORRECTION OF MY OWN EARLIER CLAIM (recorded, not silently dropped): I had written that this fix included
correcting a config/flag_consumer_registry.yaml entry that "denies the consumer read at
pipeline/stage4_merge.py:2008". MEASURED: the registry has NO depth_model entry at all (it carries
depth_frugal_enabled and depth_batch_enabled only), so there was nothing to correct - the owed action is to
ADD a stage4.depth_model entry (reader = pipeline/pipeline_paths.py + pipeline/stage4_merge.py:2008). That
addition is a doc-only change and is queued, not done. This is the FOURTH instance this session of a claim
about a missing signal that had to be measured before it could be believed.

## BUG-419 (LOW, OPEN 2026-09-23) - bug_status.json is schema-ASYMMETRIC: open is a list of objects, closed is a list of plain id strings

MEASURED: governance/bug_status.json has open[0] = dict {id, title, events} but closed[0] = str ("BUG-..."),
so one artifact carries two shapes for the same concept. Any consumer that reads a title, an event count or
the severity of a CLOSED bug gets a TypeError (this was hit live while writing the session-22 audit verifier:
"TypeError: string indices must be integers"). Symmetry matters because the whole point of this file is to be
the machine-readable answer to "what is open" - and a consumer must not have to branch on which list it is
holding.

IMPACT: no production pipeline reads it (governance/reporting only), which is why it survived; the cost is
exactly the future tax class - the next consumer writes a branch, and the branch is where the drift starts.

FIX (queued, one line of intent, no behaviour change): make closed a list of {id, title, events} like open, or
document the asymmetry deliberately in the file's own header. Prefer the former (one shape, D2585-class
symmetry). Must be done together with a consumer scan so no existing reader breaks.

## BUG-420 (MED, OPEN 2026-09-24) - the anchor family has NO fb_id bridge: its item_id is a sheet-local row label (R001...), so existing human depth work cannot be attributed to the 150 anchor rows

MEASURED (session 23). Two identifier spaces that do not intersect:
  ANCHOR-4 / RULER_BLIND_SHEET: item_id = R001, R002, R003 ... (4 chars, a SHEET-LOCAL row label)
  gold_4axis.jsonl / depth_vote_checkpoint.jsonl: fb_id = 64-hex content-addressed
  anchor4 vs gold.fb_id = 0 of 150 | anchor4 vs gold.example_id = 0 | anchor4 vs depth_vote.fb_id = 0
  ruler vs gold.fb_id = 0 | ruler vs depth_vote.fb_id = 0
  fuzzy NAME join: anchor4 vs gold = 2 | anchor4 vs depth_vote = 17
So the 234 depth values already in gold_4axis (132 human-derived) CANNOT be mechanically attributed to the
150 anchor rows. The anchor is therefore not merely "blind by design" (which it is, deliberately) - it is
also UNJOINABLE to the corpus depth work that does exist, even after the fact, and the name join is too
fuzzy (2 and 17 hits) to be used as a bridge.

WHY IT MATTERS: (1) any future depth training set (D2577 4-way head) must be assembled from gold_4axis by
fb_id and can never be checked against the anchor; (2) the D274f 30-row test-retest needs rows it can point
to unambiguously; (3) a provenance bridge is what makes "the human said X" auditable at row level (C13/R14).

ALSO MEASURED, same pass: on the 150 anchor rows the carried manual coding is CT filled 150/150, FORM
145/150, DISC only 122/150 - i.e. 28 rows have NO discipline. So the belief that manual domain/discipline
assignment for these rows is COMPLETE is not supported; DISC 122/150 and FORM 145/150.

FIX (queued, cheap, non-destructive): add fb_id (+ source sheet row, and the name joined only where
unambiguous) as columns on the anchor sheet and on ANCHOR-4, so the anchor becomes attributable at row level.
That is an additive column change on a sheet that is not yet coded - the right moment, before the freeze.

## BUG-421 (MED, FIXED 2026-09-24) - the ANCHOR-4 depth blind sheet carried the PRE-consolidation raw ruler as its context, so 260 of its 450 context cells were stale or blank

**Symptom.** The owner asked why the manual domain assignment for the 150 rows was not present in `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`. It WAS done - in ANCHOR-3, the consolidated artifact. The blind sheet held a copy of the RAW ruler taken BEFORE the F-11 consolidation.

**Measurement (one counter, `scripts/consolidate_anchor4_context.py --apply`).** Cells refreshed out of 150 rows: `CT (1-7)` 56, `DISC (1-62)` 62 (28 blank -> filled, 34 superseded by owner adjudication), `FORM (1-4)` 142 (ANCHOR-3 canonicalised raw spellings through axis-tagged aliases, e.g. 'casual mechanism' -> 'causal_mechanism'). Total 260 of 450 = 58 percent. After the refresh: CT blank 0, DISC blank 0, FORM blank 5 (the rows where ANCHOR-3 legitimately has no extraction_type), DEPTH blank 150/150, 0 cells differing from the upstream `*_final` values.

**Root cause - the recurring class.** ANCHOR-4 was built by COPYING an upstream value instead of DERIVING it, which made it a SECOND WRITER for fields ANCHOR-3 owns: the same one-artifact-two-clocks shape as BUG-402 (last_sync) and BUG-418 (an append path asserted idempotent on only one path). A blind coding sheet whose context is 58 percent stale is not a valid instrument.

**Fix (receipts).** (1) `scripts/consolidate_anchor4_context.py` - the ONLY writer of the three context columns, deriving them from ANCHOR-3 `*_final` by `item_id`, with a crash-safe write (tempfile -> fsync -> os.replace, C6) and CRLF preserved. (2) `governance/ANCHOR4_MANIFEST_20260924.json` - the config surface: paths, upstream columns, sha256s of sheet and key, provenance tier, allowed/forbidden uses, bound, verify/regenerate commands (C12). (3) `--check` exits 1 on: a context cell differing from ANCHOR-3, a duplicate or mismatched `item_id`, a non-blank DEPTH cell, a key item_id absent from the sheet, or a sheet sha256 disagreeing with the manifest. (4) Pre-refresh byte copy kept at `governance/backups/ANCHOR4_DEPTH_BLIND_SHEET.PRE_CONTEXT_REFRESH_20260924.csv`.

**Guard proven by drift injection, not assumed.** One DISC cell was flipped in a scratch copy: the check exited 1 naming the exact cell plus the sha mismatch; restoring it returned exit 0. `--apply` run twice: the second run reported `cells refreshed: none (already in sync)` (idempotent BY TEST, BUG-418 rule). The manifest's `cells_refreshed` is DERIVED by diffing the backup against the sheet, never typed (BUG-402 rule).

**Plan:** `governance/ANCHOR_FAMILY_CONSOLIDATION_PLAN_20260924.md` - the registry that says which anchor artifact is authoritative for which axis, the join contract, and the 7-step path to a frozen depth anchor.

## BUG-422 (LOW, FIXED 2026-09-24) - a claim about a MISSING signal was measured on a DERIVED copy instead of the authoritative artifact, and the missing signal did not exist

**Symptom.** I reported 'on the 150 ANCHOR-4 rows the carried manual coding IS present except DISC 122/150 - 28 rows have NO discipline, so the belief that manual domain assignment for these rows is complete is not supported', and filed BUG-420 partly on that basis.
**Measured truth.** `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` (ANCHOR-3) carries `discipline_final` for 150/150 rows, tier distribution owner-adjudicated 80 / human-ruled 42 / owner-supplied 28, with the 28 blanks resolved by the owner supplying the label where the ruler abstained ('owner supplied the label; the ruler abstained on this axis') and 32 rows where the owner OVERRODE the ruler. The owner's domain assignment was complete all along.
**Cause.** The 122/150 figure came from the ANCHOR-4 sheet's own copied DISC column - a DERIVED, stale copy - rather than from ANCHOR-3, the artifact that owns the field. This is the FIFTH instance this session of the same class: a claim about a missing signal that had to be measured before it could be believed, and this time the defect was inside an artifact I built.
**Standing rule added.** When asked whether a signal exists, query the ARTIFACT THAT OWNS THE FIELD (the registry in the consolidation plan names it); a derived or copied column may only ever be used to test the derivation, never to answer a question about existence. FIXED: the copy was eliminated by BUG-421's derivation and the guard now fails if it ever diverges again.

## BUG-420 CORRECTION (2026-09-24, append-only, never edited - R-D410) - the bridge is PARTIAL (22/150), not absent, and the proposed fix would have broken blinding

**What BUG-420 got right.** `item_id` (anchor family, R001-style) and `fb_id` (corpus family, 64-hex) are different identifier spaces: `anchor4 vs gold.fb_id = 0/150`, `vs gold.example_id = 0`, `vs depth_vote.fb_id = 0`. Those measurements stand.
**What it overstated.** 'The anchor family has NO fb_id bridge' is wrong in two ways. (a) The family is NOT internally disconnected: ANCHOR-4 joins to ANCHOR-3 by `item_id` 150/150 with ZERO name mismatches. (b) A real corpus bridge exists for 22/150 rows - 20 via `governance/remaining_verification_audit.csv` (R024, R032, R037, R043, R046, R056, R065, R068, R085, R090, R091, R096, R097, R100, R109, R121, R134, R140, R142, R143) and 2 via `governance/ANCHOR2_BLIND_SHEET_20260920.csv` (R041, R055) - plus a NAME-ONLY join for 10 further rows that is explicitly labelled `identity UNVERIFIED`.
**Corrected fix (executed).** The proposed 'add fb_id as columns on the blind sheet' is WITHDRAWN: a 64-hex fb_id on the coding sheet lets a coder look the row up in `gold_4axis.jsonl` and destroys the anchor. Replaced by a sidecar key, `governance/ANCHOR4_DEPTH_PREDICTION_KEY_20260924.json`, checked against the sheet's item_id set by the guard. The key also carries the depth values that ALREADY exist for anchor rows - 2 fb_id-verified and human-derived (R109 cross-domain, R142 domain, source p5:human-d2615) and 10 advisory 3-voter consensus values (R016, R053, R075, R080, R088, R093, R106, R111, R114, R137, 2/3 reliable voters) - as a PRE-REGISTERED PREDICTION SET, not as labels.
**Severity re-scoped.** BUG-420 remains OPEN for the unbridged 128 rows, but it no longer blocks the depth anchor from being coded, because the anchor does not need the corpus keys to be codeable.
## BUG-423 (LOW, FIXED 2026-09-24) - archive/index.yaml was stale (body_sha256 mismatch), and no guard caught it until just health was run after the ANCHOR-4 consolidation

**Symptom.** just health aborted: 'RED archive index: archive/index.yaml is STALE - stored body_sha256 ac141e979016 != measured 07e8e3559727'.
**Cause.** The archive body changed after the index was last generated; the index is a DERIVED artifact with a writer that is not run automatically - the same shape as every other derived-field bug in this ledger (BUG-402, BUG-418, BUG-421), at a lower stakes.
**Fix.** Regenerated with 'python3 scripts/build_archive_index.py' (the action the RED message itself prescribes); health re-run green. NOTE: the guard WORKED - it refused to pass while the index was stale. The defect is the absence of an automatic writer after archive mutations, not the check.
**Standing rule restated.** Any artifact whose value can be regenerated must be regenerated by a script that runs after the thing it derives from changes; a stale derived artifact that no guard reads is silent drift.

## BUG-424 (MED, FIXED 2026-09-24) - the FROZEN 150-row anchor was cited nowhere in the recall map, so the owner could not find the artifact that owns the labels

**Symptom.** Owner: "I cant find ANCHOR_RULER_CONSOLIDATED". The file existed the whole time.
**Measured.** `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` - 85,811 bytes, 150 rows x 31 cols, sha256 `29393d5f9d5292053a39986582578e140121d8987448648ad63f528062cd2698`, git-tracked (6110917 -> e9e522c -> bc20fc0), plus the `.md` companion and `backups/ANCHOR_RULER_CONSOLIDATED.PRE_F1_20260923.csv`. A whole-`$HOME` search (maxdepth 8) finds exactly ONE copy of each - in this repo. It IS referenced by 22 files, including `ANCHOR_MANIFEST_20260923.json` and the consolidation plan.
**Cause.** `governance/CONTEXT_INDEX.md` - the file the loader and every human is told to read FIRST when resuming, and the stated single entry point for locating every authoritative artifact - referenced ANCHOR-1 and ANCHOR-2 and **never ANCHOR-3 or ANCHOR-4** (`grep -c ANCHOR_RULER_CONSOLIDATED governance/CONTEXT_INDEX.md` = 0). This is the derived-index shape again (BUG-423): an artifact added to the tree without adding it to the index that is supposed to be exhaustive, so the index silently asserts completeness while being incomplete.
**Second cause.** File mode is `-rw-------` (600) while ordinary governance files are 644. The owner can read it, but any process not running as the owner cannot.
**Fix.** A dated ANCHOR-3/ANCHOR-4 section added to `CONTEXT_INDEX.md` with the paths, the sha256, the owning axes, the manifests, the RELATIVE-ONLY bound, and a pointer to the family registry. `ANCHOR-4_DEPTH_RUBRIC` and `ANCHOR_FAMILY_CONSOLIDATION_PLAN` were already citing it.
**Standing rule.** A frozen artifact is not frozen until it is IN THE INDEX: adding a file to `governance/` requires adding it to `governance/CONTEXT_INDEX.md` in the same commit, or the artifact is invisible to the next session.

## BUG-425 (MED, OPEN 2026-09-24) - the `domains` axis is owned by a DIFFERENT cohort (intersection 2/150) and the family registry never said so

**Symptom.** Owner: "have you included the canonical domain labels that I already classified?" - asked twice, because no artifact declared whether the anchor family has a domain axis at all.
**Measured (two independent joins agree).** The owner's classified domain labels are `governance/s4_domain_verdicts.jsonl`: 216 rows, **216/216 `domains_status: human-adjudicated`**, authority/provenance `p5:human` (D2628/D2633), same sheet in `governance/s4_domain_review_sheet.csv` (`HUMAN_domain_VERDICT`). Join to the 150 anchor rows: **by `out_id`=fb_id 2/150, by name 2/150 -> R109, R142 only.** Cohort sizes: verdicts 216 | anchor 150 | intersection **2**. ANCHOR-3 (31 cols) and ANCHOR-4 (16 cols) have NO domain column; neither does `RULER_BLIND_SHEET_20260917.csv` or `F11_ANCHOR_REVIEW_20260923.csv`. So the axis was never in the F-11 instrument and could not be consolidated - nothing was lost, but nothing said so.
**What the 150 DO carry.** Machine domains only: `temp/ruler_input_20260923.jsonl` + `ruler_sheet_key_20260917.json::stored.domains`, 150/150 rows, 310 tokens, 40 distinct, 0 off-menu, provenance S4/gpt-oss. **19 of the 150 rows carry the fail-closed catch-all `emerging`** in their domain set (an `emerging` domain is by contract "never a real assignment") - that is a defect to triage on the machine axis, NOT a human label.
**Related, and genuinely the owner's.** 4/150 `discipline_final` cells are DOMAIN-lexicon values written as a discipline: `personal productivity` x3 (R086/R091/R117) and `design strategy` x1 (R042), kept verbatim + flagged `OFF_MENU_DOMAIN` with the nearest menu candidate in `discipline_source_note`. There are two one-line rulings outstanding there (see `ANCHOR_RULER_CONSOLIDATED_20260923.md`, "Open taxonomy items").
**Cause.** The same class as BUG-420/BUG-422: an artifact boundary that was never declared. A registry that lists only what a family owns cannot answer "does it include axis X?".
**Status.** Registry fixed now (`ANCHOR_FAMILY_CONSOLIDATION_PLAN_20260924.md` section 3, "Axes this family does NOT own") and the recall map now states it. OPEN: whether to add a `domains` column to the anchor family at all - a SCOPE CHANGE, because `config/eval_integrity.yaml` deliberately defers the axis (`axes_deferred: [depth, domains]`, domains 0.920 attested = not the bottleneck). OWNER DECISION.

### BUG-425 REFINEMENT (2026-09-24, append-only - R-D410) - the domain pipeline WAS frontier-first-then-human as the owner remembered; the review cohort is the adjudication queue, not the ruler sample

**Owner question that forced this.** "Either in this session or previous we ran domain classification first, instructed external frontier llms, then based on the done a human domain classification manual review - why can't consolidate."
**The owner's recollection is correct and is now measured end to end.** `governance/s4_domain_verdicts.jsonl` is exactly that pipeline: `domains_ds` (DeepSeek) + `domains_qw` (Qwen) per row -> `silver_domains` / `domains_core` consensus -> owner adjudication in `domains` with `domains_authority: p5:human`, `domains_status: human-adjudicated`, `gen_model: human:D2618-p1-adjudication`, 216/216 rows. Tier after adjudication: gold 63 / silver 47 / pending 106. **The human pass was load-bearing: DeepSeek != Qwen on 174/216 = 81 % of rows.** This is the same provenance pattern ANCHOR-3 already carries (`human-mixed+llm-attested`), which is why it was the pattern recommended for depth.
**Why it still does not consolidate - cohort, not key space.** The 216 is the D2618-P0 adjudication QUEUE; the anchor is the F-11 ruler SAMPLE. Both are drawn from the SAME corpus store - `governance/joint_vote_production_checkpoint.jsonl` contains 149/150 ruler names AND 216/216 verdict names (also `knowledge pipeline/stage6_commit/t11/checkpoint.jsonl`, both 149/216) - so this is not a broken join: they are DIFFERENT ITEMS of the same corpus. Intersection = 2 (R109, R142), identical by `out_id`=fb_id and by exact name. Concatenating would produce a third instrument (364 rows: 148 with no domain axis, 214 with no CT/DISC/ET), which the never-concatenate-instruments rule (CONTEXT_INDEX, D-315 block) forbids.
**Why the 150 were never in that queue (decisive).** `governance/F11_DECISION_SHEET_20260922.csv` (and its `.USER_WORK` backup, 154 data rows, 26 cols) is the human instrument for the 150: `item_id, name, DECIDE, class_/human_/a_/b_cont, class_/human_/a_/b_disc, class_/human_/a_/b_extra, DEFINITION, APPLICATION, MECHANISM, FORM_human_as_written, FORM_canonical, FORM_claude, FORM_kimi, owner_cont, owner_disc, owner_notes`. **There is no domain column - the axis was never asked of the owner on the 150.** That is the whole answer: nothing was dropped by the consolidation; the instrument never posed the question.
**What the 150 do have on this axis.** Machine labels only: `temp/ruler_input_20260923.jsonl` + `ruler_sheet_key_20260917.json::stored.domains`, 150/150 rows, 92 multi-label, 310 tokens, 40 distinct, 0 off-menu, 19 carrying the fail-closed `emerging`, and **no voter-level fields** (`domains_ds` / `domains_qw` / `silver_domains` absent) - so the DS/Qwen -> human path was never run on this cohort.
**Recommended resolution (recorded in the plan, section "UPDATED RECOMMENDATION").** (1) surface the existing machine labels as `domains_machine` on ANCHOR-3 (provenance `machine`, never `_final`); (2) replay D2618-p1 on the 150 - frontier pair -> dispute set -> ONE owner adjudication session -> freeze `domains_final`, cost 300 label generations because the owner only sees disputes; (3) run it in the SAME session as the depth coding, since both axes are class-menu driven and both are blocked on BUG-416. OWNER GATE (C22): the frontier calls are opt-in.
**Standing rule.** "Why can't we consolidate X?" is answered by three numbers: cohort size, intersection, and whether the instrument that produced the human labels ever contained the axis. Key-space mismatch and cohort mismatch are different defects and only the first is fixed by a bridge.

### BUG-426 (HIGH, OPEN - UNRESOLVED) - twice asserted "the 150's domain axis was never asked" while the owner states it WAS done. My search was methodologically broken

**What happened.** The owner said "the 150 anchor domain classification were done" and I twice answered, with confidence, that it was never done for this cohort (first the 216-cohort framing, then the F-11 26-column framing). The owner's response was explicit frustration. I cannot close this bug by argument: the claim "no such artifact exists" is an existence-negative, and my evidence for it was defective in three ways:
1. **Session-id typo broke my own recall search.** I queried `session_id IN ('20260913','20260919',...)` and got zero hits, then reported the empty result as evidence. Real ids are `20260913_1`, `20260919_3`, etc. The 09-19 session that contains the owner's exact questions has 5441 messages and 2006 domain mentions; the 09-13 session has 6060 and 2370. Re-running with correct ids immediately surfaced the owner's words, including "can you do csv file where show all 150 content type, discipline domain, FORM for human decision" (2026-09-19) and "thanks for correcting that those are domains".
2. **The wide content scan timed out** (300 s) enumerating the Dropbox cloud folder and returned nothing - I had no coverage of `~/Downloads/maxwell-os-main`, `~/Library/CloudStorage/Dropbox/claude projects/maxwell os`, `maxwell-os-heavy` or `archived` when I made the claim.
3. **I treated a 2/150 key/name intersection as proof of absence** rather than as proof of *cohort* disjointness. Those are different conclusions and only the second is supported.
**What IS verified (do not re-litigate).** `discipline_domain_vote_checkpoint.jsonl` = 216 rows, and `s4_domain_verdicts.jsonl` = 216 rows, and both intersect the 150 at exactly 2 (R109, R142) by fb_id AND by exact name; `ruler_sheet_key_20260917.json` has 150/150 non-empty `stored.domains` (40 distinct, 19 `emerging`, machine provenance, no voter-level fields); 4 of the 150's discipline cells hold domain values the owner personally caught on 2026-09-19 (`design strategy` R042; `personal productivity` R086/R091/R117) - so at least that part of the owner's domain work IS present on the 150. The archived copy `~/Downloads/maxwell-os-main` has no file carrying the 150's names plus a domain column.
**Standing rule (new).** An existence-negative about the owner's own completed work requires (a) correct keys in my own queries, (b) a completed scan whose timeouts are declared, and (c) a statement of what was NOT searched. Otherwise the correct answer is "not found yet", not "does not exist". This is the sixth "claim about a missing signal" this session and the first that is still unresolved - it must appear in every handoff until closed (C15).
**Next action to close it.** Grep session `20260913_1` (6060 msgs) and `20260830_18` for the 150's item names together with domain values, and search `~/Library/CloudStorage/Dropbox/claude projects/{maxwell os,maxwell-os-heavy,archived}` with a bounded scan. Only after that may "done" or "not done" be asserted.

### VERIFICATION EVENT (2026-09-24) - the FORM axis is INTACT in both the human instrument and the frozen anchor

Asked directly by the owner ("did you lose, overwrite or corrupt my previous FORM classification as well?"). Re-derived, not asserted:
- `governance/F11_DECISION_SHEET_20260922.csv::FORM_human_as_written` - **145/150 filled, column sha256 `310225e02dddc0b2` - byte-identical between the commit that introduced it (`a2b2a07`), the pre-consolidation backup (`governance/backups/F11_DECISION_SHEET_20260922.PRE_CONSOLIDATION_20260923_122130.csv`, same `310225e0...`) and today's working copy.** Zero human FORM cells differ from the revision that introduced them.
- **The owner's own spellings survive verbatim**, which is the proof no normalisation overwrote them: `casual mechanism` 30x, `normativ heuristic` 22x, `escriptive model` 2x, `normative_heuristic` 1x, `empirical_pattern` 1x. A machine pass would have silently "fixed" exactly these.
- **FORM IS the extraction_type axis.** `ANCHOR-3::extraction_type_final` == `F-11::FORM_canonical` on **145/145 rows, 0 disagreements**. Provenance on ANCHOR-3: `extraction_type_human_present` yes 145 / no 5; `extraction_type_tier` `human-ruled` 145 / `declared-missing` 5. So the FORM work is not merely preserved - it is a first-class, owner-attributed, frozen axis of ANCHOR-3, and ANCHOR-4's `FORM (1-4)` derives from it (script line: `"form": r.get(columns.extraction_type)`).
- Only a DERIVED column was ever added beside it (`FORM_canonical` 50/41/40/14), never a replacement.
**Conclusion: no loss, no overwrite, no corruption of the FORM classification.** Recorded here so it is never re-litigated (compare BUG-426, where the same class of question was answered badly).

### BUG-427 (LOW, OPEN) - the F-11 human instrument carries 4 trailing blank-`item_id` padding rows, so `len(rows)` is 154 while the anchor is 150

**What.** `governance/F11_DECISION_SHEET_20260922.csv` has **154 data rows but only 151 distinct `item_id` values, 150 of them real anchor rows**. Lines 131-134 are padding rows: `item_id` empty, `name` empty, `DECIDE` `3`, `class_cont` and `class_disc` `human BLANK`. They are harmless to a consumer that keys on `item_id`, and they are NOT owner data.
**Why it matters.** Every prose statement of the form "the F-11 instrument has 154 data rows" (including the BUG-425 block above) is comparing a padded count against a 150-row anchor and can be read as a 4-row discrepancy. Count-based consumers - and readers - over-count by 4.
**Fix.** Either drop the padding in the next append-only rebuild, or state row counts as "150 keyed rows (+4 padding)". A guard belongs in the human-instrument check (see the proposed hash-lock).
**Detected by.** `csv.DictReader` row count vs distinct `item_id` count, 2026-09-24.

## BUG-428 (HIGH, FIXED 2026-09-24) - the machine-readable bug register could not see TWO OPEN bugs, one of them HIGH, and would have auto-CLOSED it by substring

**What.** Asked to prove that nothing is drifting, I checked the register against the file it derives from - and the register was wrong in two independent ways, both found only because the FORM/drift audit forced a recount:
1. **Visibility.** `HEADER_RE` was `^##\s+(BUG-\d+)` - EXACTLY two hashes. BUG-426 (HIGH, OPEN, UNRESOLVED) and BUG-427 (LOW, OPEN) were written with three, so they were **absent from `bug_status.json`, from the C15 count, and therefore from every handoff** - while sitting in the register's own directory. The C15 line read "94 open / 77 closed of 171 ids" and was quoted by me as proof of state.
2. **Classification.** Widening the pattern exposed a second defect in the same family as BUG-347: `UNRESOLVED` contains `RESOLVED`, so `### BUG-426 (HIGH, OPEN - UNRESOLVED)` classified as **CLOSED** - a HIGH, explicitly-unresolved bug auto-retired by substring match. (The widening also revealed one honest closure nobody could see: `### BUG-319 - ROOT CAUSE FOUND and FIXED`, correctly CLOSED.)
**Fix.** (a) `HEADER_RE` accepts `##` and `###`; (b) `NEGATED_WORDS` is checked FIRST and forces OPEN (UNRESOLVED/UNFIXED/NOT RESOLVED/NOT FIXED/STILL OPEN/NOT CLOSED), with 3 live-shape self-test cases - the direction of failure is chosen deliberately: an open bug that is really closed costs a look, a closed bug that is really open costs the work being silently abandoned; (c) new `scripts/check_buglog_coverage.py` fails closed on any heading that names a bug id and is not parsed by `HEADER_RE`, reusing `HEADER_RE` by import so pattern and guard cannot diverge, and exempting declared ANNOTATION headings (`CORRECTION|RECEIPT|REFINEMENT|VERIFICATION|...`) so the guard does not get disabled for shouting at apparatus.
**Why it is HIGH.** The register is the artifact a session quotes as "current state". A register that silently drops the top-severity unresolved item converts a known, loud problem into a false "all clear" - the exact failure the owner named.
**Detected by.** recounting the register against `governance/buglog.md` while answering "did you corrupt my FORM classification?" - i.e. the drift audit was load-bearing, not ceremony.

### RECEIPT - ANCHOR-4 depth owner pass evaluated + ANCHOR-4-KEY unsealed (2026-09-24, annotation)
Owner supplied `governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` (sha256 be1a39e04c378af9..., 150 rows).
Measured: DEPTH 150/150 all in {1,2,3,4}; conf_depth 150/150 all in {1,2,3}; reviewer human 150/150; date 13.09.26
150/150; note_codes 0/150. Distribution 3=66, 4=44, 2=33, 1=7. vs the 12 pre-registered ANCHOR-4-KEY references:
9/12 agree (human-derived 2/2). vs the 3-voter depth advisory: 8/11 on a name join, but the advisory is joinnable on
only 17/150 rows (94% unjoinable) so it cannot validate this cohort. The tracked sheet on disk is a PARTIAL autosave
of the same pass (18/150, 18/18 agreement) with `conf_depth` corrupted to the word `domain` on R149/R150; preserved
byte-exact as `governance/backups/ANCHOR4_DEPTH_BLIND_SHEET.OWNER_PARTIAL18_UNCOMMITTED_20260924.csv`.
ANCHOR-4-KEY (governance/ANCHOR4_DEPTH_PREDICTION_KEY_20260924.json) was READ to score this pass - declared here so the
peek cannot later be presented as a pre-registered result. Receipt: governance/ANCHOR4_DEPTH_OWNER_PASS_EVALUATION_20260924.md.
Also recorded: config/human_instrument_locks.yaml and scripts/check_human_instruments.py cite "BUG-430" in their headers but
no heading exists in this file - a citation without an entry is the same traceability hole as BUG-428. Stands as the
missing-rails defect id; do not reuse 430.

### BUG-432 - INSTANCE 2 (2026-09-24): the tracked sheet's whole CONTEXT block is also pre-consolidation, so the
owner's depth pass was coded against a 58%-stale context (260/450 context cells differ from ANCHOR-3). The judged row
TEXT (DEFINITION/APPLICATION/MECHANISM/BOUNDARY/SOURCE EXCERPT) is identical apart from R147's DEFINITION, and the
D282 check (depth is not determined by content_type) passes - so the labels stand, but the staleness must be declared
in the freeze manifest rather than discovered later. One owner line needed: is R147's text difference a wording fix
(copy) or a stale copy (tracked)?

### BUG-431 - ANCHOR-4 FORM column was refreshed from ruler_raw, so the sheet's declared 1-4 menu is not what it holds (2026-09-24, MED, OPEN)
Measured: at 4a4c71d the ANCHOR-4 `FORM (1-4)` column held the menu-conformant `extraction_type_final` values
(normative_heuristic 50 / descriptive_model 41 / causal_mechanism 40 / empirical_pattern 14, 5 blank). After the
context refresh it holds `extraction_type_ruler_raw` - the owner's verbatim spellings: 'descriptive model' 38,
'casual mechanism' 30, 'normative heuristic' 27, 'normativ heuristic' 22, 'empirical pattern' 13, 'causal mechanism' 10,
'escriptive model' 2, 'normative_heuristic' 1, 'descriptive_model' 1, 'empirical_pattern' 1 (= 145). Only 3 cells are
strictly on-menu. The rubric (lines 47-49) declares the derivation source is `extraction_type_final`, and the column
header says "(1-4)": both are now false. The refresh therefore downgraded a conformant column, and
`consolidate_anchor4_context.py --check` cannot see it because guard and writer read the same mapping - the same
"guard agrees with its own assumption" class as BUG-421. Same defect class in the sibling columns: CT/DISC cells hold
label prose while the headers say (1-7)/(1-62). FIX (owner gate, ANCHOR-4 sheet is write-frozen this session): map
FORM to extraction_type_final, keep ruler_raw in its own provenance column, add a menu-conformance assertion for
CT/DISC/FORM to the context guard so a wrong mapping fails closed. NOT a depth defect: D282 leak check passes, DEPTH
is not determined by FORM; the owner's depth pass remains valid.

### BUG-432 - owner work can arrive as an unversioned drop-in while the tracked sheet holds a partial save; nothing detects it (2026-09-24, HIGH, OPEN)
The owner's completed 150-row depth pass existed only as `governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`
(untracked, Finder/Dropbox "Copy of" naming, produced outside the repo) while the git-tracked sheet held an 18-row
partial autosave of the same pass - and the working tree sat like that, undetected, with all rails green. The
"Copy of *" pattern is the observable signature: it means the artifact that people edited is NOT the artifact in git.
No existing rail covers this: write-locks protect a tracked file's contents, cohort guards protect joins, the
existence-negative ledger covers claims - none of them notices that the authoritative copy is outside version control.
PROPOSED RAIL 5 (next session, config-driven): (a) a detector that fails when a sheet has reviewer/date filled but a
target column partially empty, or when it is modified while owning an uncommitted partial state; (b) a drop-in scan
that reports any `Copy of *` / " *copy* " sibling newer than its tracked counterpart; (c) a standing rule that any
owner drop-in RE-OPENS every open existence-negative claim (NEG-001) and requires a re-scan before any negative is
restated. Immediate mitigation done: drop-in committed as-is, write-locked, partial byte-copied to backups/.

### BUG-433 - a committed artifact was clobbered by an out-of-band writer 3 hours later, silently (2026-09-24, HIGH, OPEN)
Evidence: `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` was committed CONSOLIDATED at 10:40 (e7da35b, manifest
sha 14ee0d7a8d46e1d6), yet the working tree at 13:39 held the PRE-consolidation content (142 FORM / 62 DISC / 56 CT
cells stale vs ANCHOR-3) plus the owner's reviewer/date on all 150 rows and DEPTH on R001-R018 only. Nothing in the
repo performed that write: it is an out-of-band writer - the Dropbox File Provider re-syncing a cloud-editor save
down over the repo copy (the BUG-400 / Gate D hazard class), i.e. the same mechanism that produced the untracked
'Copy of ...' drop-in. Two fail-closed guards noticed (`consolidate_anchor4_context.py --check`: 5 drifts incl.
'sheet sha256 != manifest' and 'DEPTH already filled on R001 - the sheet is no longer blind';
`verify_anchor_family_registry.py`: blank-count 150 declared vs 132 measured) - nothing else did, and `git status`
had shown the file as ordinary 'M'. Standing rule: a tracked artifact that is MODIFIED without a corresponding local
process must be treated as an out-of-band clobber until proven otherwise, and its pre-clobber bytes must exist in a
backup before any re-write. Mitigation done now: the clobbered bytes are preserved byte-exact at
`governance/backups/ANCHOR4_DEPTH_BLIND_SHEET.OWNER_PARTIAL18_UNCOMMITTED_20260924.csv`, the owner's complete pass is
write-locked, and the context guard now reports a DECLARED interim state (config/anchor4_interim_state.json) as WARN
while BUG-431 is open, with `--strict` proving it still fails closed. FIX (owner gate): one promotion write.


### RECEIPT - ANCHOR-4 depth drop-in rev 2: the owner fixed the date, and rail 1 caught the edit within minutes (2026-09-24, annotation)
- rev 1 (committed byte-exact as-is at 075ae65): sha256 `be1a39e0…`, `date` = `13.09.26` ×150.
- rev 2 (mtime 2026-09-24 15:23:32, 203506 bytes — SAME byte count): sha256 `bc1cc956…`, `date` = `24.09.26` ×150.
- Cell-level diff rev 1 → rev 2: **`date` 150 cells, nothing else.** DEPTH (1-4) / conf_depth / note_codes / reviewer
  column hashes are byte-identical to their rev-1 locked values, so the LABEL CONTENT of the owner's pass is unchanged
  and every conclusion of `ANCHOR4_DEPTH_OWNER_PASS_EVALUATION_20260924.md` §1–§3 stands (§7 of that receipt records
  the supersession). The write lock now binds rev 2 and keeps rev 1 as a declared `superseded` revision.
- This is the rail WORKING, not a defect: `check_human_instruments.py` failed closed with
  `REWRITTEN governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv::date` the moment the file was touched.
  Before rail 1 the same edit was invisible (BUG-432).

### BUG-432 - INSTANCE 3 (2026-09-24): an owner drop-in was edited AFTER it was committed, so a committed `Copy of *` is a point-in-time snapshot, not a live instrument
The drop-in was committed byte-exact at 075ae65 (rev 1) and edited in place ~5 hours later (rev 2, the date fix).
Nothing about the edit was wrong — but it means any config, receipt or ledger that pins a drop-in sha256 must be
re-measured whenever the file is touched, and the old sha must be kept as a declared `superseded` revision rather than
silently overwritten (done in `config/human_instrument_locks.yaml`). Rail 5(b) now has a second observable form: "a
TRACKED drop-in with an uncommitted modification", in addition to "a `Copy of *` sibling newer than its tracked
counterpart". CONSEQUENCE: the touch re-opens every open existence-negative claim under the standing rule, so
BUG-426's `NEG-001.last_dropin_considered` must name rev 2 (sha + mtime) and `search_complete: false` — depth ≠ domains,
the owners's depth pass is still NOT this claim's answer.

### RECEIPT - the ANCHOR's missing DOMAIN axis: the reliable pair is now voting the 150 blind rows (2026-09-24, run opened)
The owner's instruction was "do the domain classification", and the instrument is settled by PRECEDENT, not by choice:
the D2618-P0/P1 cohort was coded by the reliable pair `deepseek-v4-pro` (API) + `Qwen3.8-27B-MLX-4bit` (local OMLX),
so the SAME pair + the SAME D2610-v2 policy now votes the anchor. Harness `scripts/vote_anchor_domains.py` imports the
shared `vote_once()`/`aggregate()`/`_canonical_defs()` from `build_discipline_domain_vote.py` — it does not fork the
instrument. Input is `governance/frontier_pack_20260924/BLIND_INPUT_150.csv`, i.e. row text only: no CT/DISC/FORM/DEPTH
and no BOUNDARY (boundary encodes scope, which would leak the depth axis), so the run is blind by construction and the
frontier coders will read the identical file. Declared deviations (prompt_id `anchor_domains_v1`, domains-only; input
fields name/definition/application/mechanism): the anchor's content_type and discipline are HUMAN-owned in ANCHOR-3 and
are deliberately not re-coded. gpt-oss was NOT used: it is the S4 classifier family under test, so labeling the anchor
it will later be scored against is ancestor contamination. Output `governance/anchor4_domain_vote_checkpoint.jsonl`
stamps schema_version / prompt_id / gen_model / gen_temperature 0.0 / pipeline_commit and `authority: MACHINE-ADVISORY-ONLY`.
FIRST MEASURED BEHAVIOUR (pilot, 3 rows): 1 agreed, 2 abstained on GENUINE pair disagreement (R001 DeepSeek
`business development/digital product/marketing & communications` vs Qwen `digital product/marketing & communications/
user experience`) — the abstention is the policy working. The abstain share is expected to be high (the 216 cohort ran
81% non-agreement), which is exactly why `domains_final` is the OWNER's column and no script writes it.

### BUG-434 (LOW, FIXED 2026-09-24) - the domain vote record declared `n_voters` from a key the producer never returns, so every row carried a null where a count belongs
`vote_once()` returns no `n_voters`, so `scripts/vote_anchor_domains.py` wrote `"n_voters": null` on every row while
`per_voter_domains` held the truth right beside it — a declared-but-empty field, the same class as BUG-419 (a schema
the reader cannot trust). Caught by inspecting the pilot records instead of trusting a green run. FIX: derive it
(`sum(1 for v in votes.values() if not v.get("error"))`), then kill + relaunch (the run is resumable, nothing lost).
Epoch note: rows written before the fix keep `n_voters: null` and are identifiable by their `pipeline_commit`; the
count is re-derivable from `per_voter_domains` for those rows, and the records are append-only (R-D410).

### BUG-435 (MED, FIXED 2026-09-24) - the domain vote's resume rule froze transient API failures into permanent abstentions
`--resume` skipped any `item_id` already present in the checkpoint. A row where ONE voter errored (timeout, rate limit,
OMLX eviction) was therefore never retried: the record said `agreed: false, needs_review: true`, which is
INDISTINGUISHABLE from an honest pair disagreement, and the owner's adjudication queue would have silently absorbed
infrastructure failures as if they were coding disputes. This is the BUG-432 class in a different register: an
instrument that cannot tell "no answer" from "a disagreeing answer" manufactures work for the owner. FIX: a row counts
as done only when every reliable voter actually ANSWERED (`answered(rec) >= len(reliable)`), with an `attempt` counter
capped at MAX_ATTEMPTS=3 so a hard failure cannot loop; the checkpoint is append-only and the latest record per
`item_id` wins. Caught by re-reading the resume code before letting a multi-hour run proceed on it, not by a guard.

## BUG-436 — MED — FIXED (by declaration + a standing rule)

`scripts/vote_anchor_domains.py` declared two prompt deviations that **were never in force** on the run that
produced `governance/anchor4_domain_vote_checkpoint.jsonl`. `vote_row()` delegates to the SHARED
`bddv.vote_once()`, and that function builds its own prompt with `bddv._prompt()`: BOTH axes, the 61-label
discipline menu and a `Boundary:` line. `BLIND_INPUT_150.csv` has no BOUNDARY column, so the field was sent
EMPTY. The module's own `prompt_for()` — the domains-only prompt the docstring and the run receipt described —
was dead code exercised only by `--dry-run`. The pre-flight "verification" that reported *"has DISCIPLINE
section: False | domain labels offered: 43"* therefore certified a prompt the run never sent.

WHY IT MATTERS: a declared deviation is a claim about the instrument, and the instrument's provenance is what the
216-row cohort is compared against. Two consequences, both now declared: (a) the domain values are still strictly
comparable to the 216 cohort, because they came from the identical instrument — this is a documentation defect,
not a contamination; (b) every record also carries an unofficial machine `discipline` value, which must NEVER be
read as an axis decision (discipline is HUMAN-owned in ANCHOR-3, 150/150).

FIX: the script docstring and the run receipt both carry a CORRECTION block naming what was sent. STANDING RULE
(this is the generalisable part): **a `--dry-run` that executes a different code path than `--run` verifies
nothing.** The acceptance test must call the same function the run calls, or print the prompt built by the run
path itself. Corollary defect in the same record: the first 4 checkpoint rows carry `n_voters: null` because they
were written before the BUG-434 fix landed; `n_voters` is derived at read time by the cross-examination and is
never trusted from the record.

## BUG-437 — LOW — FIXED

`scripts/cross_examine_anchor_axes.py` computed each row's domain "plurality" with `Counter(union)` where `union`
was a **set** — so every candidate label counted 1, the "plurality label" was an arbitrary element of an unordered
set, and the `DOMAIN_SPLIT_MENU` flag fired on **150 of 150 rows**. A flag that fires on every row is not a
signal; it buried the real structure in the same table. FIX: count over the multiset of labels actually chosen.
The verdict changed from `HARD 28 / SOFT 122 / AGREE 0` to `HARD 28 / SOFT 116 / AGREE 6`. Caught by re-reading my
own output before showing it, not by a guard — which is the argument for showing the numbers, not the summary.

## BUG-438 — LOW — FIXED (2026-09-25)

The cross-examination rendered a **declined** axis identically to an **undelivered** one. Claude returned
`none_fits` on BOTH axes for R021 and R026 — a refusal of the MENU, which is a substantive finding — and
`read_frontier()` accepted the value (it is in the declared vocabulary) while `collect()` stored `depth: None`.
The workbook cell, the long CSV and the per-coder coverage line therefore read exactly like "this coder never
answered that row": `claude-sonnet-5: domains 148/150, depth 148/150`, with the missing 2 unexplained. That is a
FAIL-OPEN DISTINCTION LOSS: the one thing the owner most needs to see (a coder rejecting the taxonomy) was the one
thing invisible in the output. FIX: a `depth_declined` field, a `DEPTH_MENU_DECLINED` flag that pulls both rows into
the dispute set, a `none_fits` marker in the workbook so the cell can never be read as blank, and a MENU DECLINED
note per row. EVIDENCE that it was worth catching: the frozen ANCHOR-3 already carries
`content_type_final = noise_drop` for both rows ("Index Section" / "Index of Motion Graphic Title Design Terms"), so
an independent frontier coder refusing to class them is a CROSS-VALIDATION of the anchor's own noise decision — not
a hole in the data. STANDING RULE: **"absent" and "declined" are different facts and must never share a rendering.**

## BUG-439 — LOW — FIXED (2026-09-25)

The owner-facing workbook's `name` column was **blank on every row** since rev 1. `per_row` never carried a name, and
`csv.DictWriter(..., extrasaction="ignore")` swallowed the missing key silently, so the instrument the owner
adjudicates from showed 148 item-ids with no titles to recognise them by — and nothing failed. FIX: names are read
from the SHARED blind input (`governance/frontier_pack_20260924/BLIND_INPUT_150.csv`, declared in
`config/anchor_cross_exam.yaml` as `blind_input`) because a title typed
by a coder would be a second drifting copy of the anchor; the run now FAILS CLOSED if that file is absent. Caught by
printing the name-fill count rather than assuming the column worked.
STANDING RULE: **`extrasaction="ignore"` is a silent-drop rail — a DictWriter that ignores extra keys will equally
ignore a key you forgot to populate. Assert the fill of every owner-facing column.**

## BUG-440 — MED — FIXED before delivery (2026-09-25)

My first `machine_recommendation` column recommended `domain=<label> as PRIMARY` from `domain_plurality_share`, which
counts **SET MEMBERSHIP** (a label inside 2 of 4 coder sets scores 0.50). It would therefore have printed a
recommended PRIMARY label on **148 of 148** rows — including rows where all four coders led with DIFFERENT labels —
while the same run measured identical label SETS in only 12-25% of pairs and identical PRIMARY labels in 48-63%. That
is precisely the plurality-anchoring this repo warns against, generated by my own new column and one step from being
handed over as advice. FIX: store `primary_plurality` / `primary_share` (coders whose FIRST label it is) separately
from set membership, and recommend a label only when **>= half the coders LEAD with it**; otherwise
`domain=OWNER_ONLY`. Every recommendation now states its own `n/N` in `recommendation_basis`, so a weak 2/4 plurality
can never be read as consensus.
STANDING RULE: **a recommendation must carry its own vote count, and set membership is not a vote.**

## BUG-441 — MED — FIXED (2026-09-25)

The owner's filled adjudication workbook `governance/anchor_adjudication_workbook_20260924.csv` was saved **Mac
Roman encoded**: one byte (`0xCA`, a non-breaking space inside a row NAME) made the whole file undecodable as
UTF-8, so the cross-examination harness — and any other reader — died on it. Content damage: none (one typographic
space); reachability damage: total. FIX: `scripts/normalize_owner_workbook.py` detects the encoding
(utf-8-sig -> utf-8 -> mac_roman -> cp1252), rewrites the file as UTF-8, and keeps the byte-exact raw drop-in in
`backups/anchor_adjudication_workbook_20260924.OWNER_RAW_20260925.csv`.
STANDING RULE: **an owner drop-in is checked for encoding BEFORE it is parsed — a file that cannot be decoded is
not an empty file, and must never be reported as missing data.**

## BUG-442 — MED — FIXED by declaration (2026-09-25)

The owner's review carried 10 lexical defects that were all FORMAT, none of them judgement: 7 truncated canonical
labels (`research & methodolog` x3, `business developmen`, `media & entertainmen`, `user experienc`,
`esign systems`, `systems & framework`), one canonical label shattered by the separator
(`business,operations` — the owner separates with commas and the label CONTAINS one), one trailing `|`, and one
off-menu token with no defensible nearest label (`emerging`, R040). Worst case found: under the owner's new
first-token rule a shattered label **silently decided the PRIMARY domain of R024** — a format defect owning a
semantic slot. FIX: declared exact-match fix map in `config/anchor_workbook_fixes.yaml`, applied only on an exact
token match (no fuzzy matching anywhere near the gold); every change written to
`governance/anchor_adjudication_fixlog_20260925.csv`; the owner's original strings preserved in the new
`domains_final_raw` column so a fix is additive, not a replacement. `emerging` and the 4 blank cells are declared
and left exactly as submitted, awaiting the owner.
STANDING RULE: **a separator is part of the taxonomy. If a canonical label can contain the separator, the cell
format must be quoted or the separator must be one the labels cannot contain.**

## BUG-443 - Cloud editor silently overwrote the NORMALISED owner workbook (working tree)
- **Severity:** MED  |  **Status:** FIXED  |  **Found:** 2026-09-25 15:11  |  **Class:** C6 / rail-1 discipline, BUG-432 proposed rail 5(b), BUG-433
- **Symptom.** `governance/anchor_adjudication_workbook_20260924.csv` (working tree) failed UTF-8 decode at byte 40770 with 0xca, 91811 bytes, mtime `Sep 25 15:02:11` - i.e. it was back to a **Mac Roman** 22-column state, **494 cells different** from the file committed at 95bb859. The normalisation work of this session was gone from disk while still intact in git HEAD.
- **Root cause.** The owner's cloud editor held an older in-memory copy and saved over the normalised file. The save is a real write, not a no-op.
- **Not data loss - and the new revision is BETTER.** Diff raw-vs-disk = **exactly 1 cell**: R024 `business,operations` -> `business operations`. That is the **owner's own fix**, i.e. the drop-in carried it and the pre-normalisation backup did not. So the disk state was owner rev 2, ahead of the file I had normalised.
- **Fix.** Both owner revisions preserved byte-exact: `backups/...OWNER_REV1_20260925.csv` sha256 `d6413802bb849319933e1259febdea1aa6e179439c79b7136243c84e4e7c489d` (as submitted) and `backups/...OWNER_REV2_20260925.csv` sha256 `c49f6395db4460b7c8f8d72f15172c2ba82824bca30df8ce41f25ae61406c179` (owner's R024 fix). Normalisation re-applied to rev 2 (**9 cells**, not 10 - the declared `business,operations` replacement is now unused because the owner's fix already landed and is canonical); R024 normalised to `business operations|organizational behavior|business development|finance & investment`, primary `business operations`. `OWNER_RAW_20260925.csv` is now explicitly the **rotating pre-apply snapshot**, not a fixed revision.
- **STANDING RULE.** Before any further processing of an owner instrument, re-verify the **working tree** against **git HEAD** - never only the revision you last wrote. "The file is still there" is not "the file is unchanged", and a cloud-editor save is a write event that must be diffed before it is trusted or overwritten.
- **Corroboration for BUG-432 rail 5(b):** this is the third instance of an out-of-band write to a tracked governance file in this family (BUG-433, BUG-432, BUG-443). A watcher that fails on "tracked file changed with no local git process" would have caught all three.

## BUG-444 - `git add -A` committed a deliberately-dirty OWNER instrument (ANCHOR-4 sheet)
- **Severity:** MED  |  **Status:** FIXED (recorded; content unharmed)  |  **Found:** 2026-09-25 15:16  |  **Class:** owner-gate discipline / C22
- **Symptom.** Commit `ff6641b` includes `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` (300 lines changed), a file listed under `will_not_touch` in the session plan and deliberately kept **modified but UNSTAGED** as the visible marker that the owner-gated promotion write is still owed.
- **Cause.** `git add -A` in the same shell line as the commit. `-A` stages every dirty path, including canaries nobody may commit.
- **Content harm:** **NONE.** On-disk == HEAD == sha256 `b47114d4cdb621bbf67ec39f37c119eff8b74ce2802ed4552ed6be2b51792167`, 203253 bytes, `DEPTH (1-4)` filled **18/150** (132 blank) before and after. No promotion write occurred; ANCHOR-3 was not touched. What was lost is the **marker**, not the data.
- **Fix.** State re-established explicitly: the promotion write is OWED is now read from the sheet's **DEPTH fill count (18/150)**, not from `git status`. Rail 4 is now a **pre-commit hook** (`scripts/install_git_hooks.sh`) so the next such commit is refused rather than reported.
- **STANDING RULE.** Never `git add -A` / `git add .` in this repo - stage explicit paths. Where a pending-work state matters, encode it as a **measured quantity** (fill counts, hash mismatch vs a declared lock), never as a git-dirty flag: a dirty flag is destroyed by any incident that stages it, and it says nothing about what is owed.

## BUG-445 - The rail-4 guard could be SILENCED instead of satisfied (scope laundering)
- **Severity:** HIGH  |  **Status:** FIXED  |  **Found:** 2026-09-25 15:16  |  **Class:** C12d review-rule / rail 4
- **Symptom, and this one is the assistant's own.** Commit `ff6641b` violated the plan on **two** paths. The guard printed both. The assistant read only `tail -3`, saw the workbook line, **widened `may_touch`, committed the plan, and the guard went green** - while the ANCHOR-4 sheet violation was never addressed. A guard whose fix is "edit the guard's allow-list" is not a guard.
- **Two distinct defects.**
  1. **Laundering path.** A path in `will_not_touch` was reported with the **same remedy text** as an undeclared path ("widen `may_touch` ... or revert"). Widening converted a forbidden write into a compliant one.
  2. **Post-hoc only.** The guard runs as a separate command *after* the commit, so by the time it speaks the violation is already in history and the cheapest available action is to widen the plan rather than revert the commit. Truncating its output (`tail -3`) then hides the rest.
- **Fix.** (a) `will_not_touch` now **outranks** `may_touch`: matching paths produce a distinct `FORBIDDEN` verdict, **exit code 2**, and the remedy is `git checkout HEAD -- <path>` or the owner gate - **never** widening. (b) `--staged` mode added and installed as `.git/hooks/pre-commit` via `scripts/install_git_hooks.sh`, so rail 4 refuses the commit instead of reporting it. (c) Re-auditing the violating commit with the new logic returns exit 2 and names the sheet - the failure is now reproducible on demand.
- **STANDING RULE.** A guard whose remedy is "change the guard's own configuration" is a guard with a bypass built into its advice; the remedy must always be an act on the **artifact**, never on the **allow-list**. And never read a verifier's output through a truncation - if a check can report N findings, read the finding count, not the last three lines.

## Cross-cutting finding (third out-of-band write in this family)
BUG-433 (unsourced hash change), BUG-432 rail 5(b) (a 'Copy of *' sibling newer than its tracked counterpart), BUG-443 (cloud editor overwrote the normalised workbook). All three are the same failure: **a tracked governance file changed with no local git process**, and all three would have been caught by the watcher proposed in BUG-432 rail 5(b). That watcher is now the highest-value unbuilt rail in the family.

## BUG-443 - FIXED 2026-09-25 (header omitted the status word; content unchanged, see entry above)
## BUG-444 - FIXED 2026-09-25 (content unharmed - the sheet is byte-identical to HEAD; see entry above)
## BUG-445 - FIXED 2026-09-25 (rail 4 is now a pre-commit hook; will_not_touch outranks may_touch; re-audit of ff6641b returns exit 2)

## STANDING RULE - a bug entry HEADER must carry its status word
- **Bug:** the three entries above declared **Status:** FIXED in their body, but `scripts/bug_status.py` reads the
  **header line** (the last `## BUG-<id>` event wins). All three were therefore indexed **OPEN**: the register
  over-reported open by 3 while the bugs were fixed. Fail-safe direction, but still drift - the register must
  describe the record, not lag it.
- **STANDING RULE.** Write the status word IN THE HEADER when the entry is created (`## BUG-NNN - FIXED ...`),
  because the register parses headers; a status that lives only in the body is a status the register cannot see.
  Rule restated: an artifact is only as authoritative as the field the reader actually reads.

## BUG-446 - OPEN - `justfile` does not parse: the entire boot health rail has been unrunnable
- **Severity:** HIGH  |  **Status:** OPEN  |  **Found:** 2026-09-25 16:20  |  **Class:** C16 / rail integrity
- **Symptom.** `just --list` fails: `error: Unknown start of token '.'  ——▶ justfile:13:33` on the line
  `python3 scripts/check_depth_menu.py || exit 1` — the only unindented line in the `health` recipe. Iron rule
  #4 of the boot sequence is "Run: just health", and that command has been a syntax error, so EVERY rail inside
  `just health` (manifest verify, depth menu closure, existence negatives, buglog coverage, menu policy, frozen
  pair, evidence manifests, recalibration pins, ...) has been unrun for as long as the line has been unindented.
- **Blast radius.** Not a data defect: a DETECTION defect. It is the reason the defects below could sit in a
  green-looking repo, and it is why "the rails are green" was not a measurable claim.
- **Fix.** Indent the line; add `python3 scripts/validate_depth_domain_contract.py --gate-if-active` to `health`
  so the new contract runs there (non-gating while `status: proposed`, self-gating when activated).
- **STANDING RULE.** A guard that cannot start is not a guard. Boot must verify that the health command PARSES
  before trusting that it passed (a one-line `just --list` probe returning 0).

## BUG-447 - OPEN - `menu_hash` drift: the frozen menu is not what the code renders (D-279 provenance broken)
- **Severity:** HIGH  |  **Status:** OPEN  |  **Found:** 2026-09-25 16:25  |  **Class:** provenance / drift
- **Symptom.** `config/closed_menu_v5.sha256` freezes `73597ee2b1bb1eb9...`. `menu_hash()` (the canonical
  rendering, `pipeline/closed_menu.py`) returns **`d2fc500c8835db54...`**. The frozen `.json` artifact hashes to
  the frozen value (`menu_hash(stored) == 73597ee2`), so the artifact is intact and the RENDER drifted: exactly
  one entry differs — the `behavioral economics` discipline definition in `config/taxonomy_v5.yaml` gained
  "behavior-change interventions / social norms / peer influence / choice of behavior" and the menu was never
  re-rendered (`scripts/render_closed_menu.py`).
- **Blast radius.** D-279 stamps `menu_hash` onto every classified FB. Rows already stamped `73597ee2` are now
  unreproducible from config, and a re-classify today would stamp `d2fc500c`, so one corpus will carry two
  incompatible canvas versions with no stored diff. The DOMAIN axis is byte-identical in both, so the depth/domain
  measurements of 2026-09-25 are unaffected — the discipline axis is the axis that moved.
- **Fix.** Re-render and re-freeze (owner-visible act: it changes the hash every future row is stamped with), or
  revert the definition edit. Do NOT simply overwrite the `.sha256` file: the hash is the evidence of which menu
  the existing labels were classified against, so overwriting it destroys the provenance it exists to provide.
- **Self-falsification.** This session's first version of the check hashed the `.json` BYTES and reported a
  mismatch that did not exist (bytes `bc537701...` never equal a rendering hash). The instrument that stamps the
  rows must be the instrument that verifies them (C21) — a second implementation is a second truth.

## BUG-448 - OPEN - the depth and domain axes had no consistency contract (existence gap, not a regression)
- **Severity:** MEDIUM  |  **Status:** OPEN  |  **Found:** 2026-09-25  |  **Class:** C12 / missing guard
- **Symptom.** Nothing asserted the two axes agree, so: an off-menu token could normalise to ZERO domains with no
  exception and no log (sandbox S10: a truncation DEGRADING INTO A VALID-LOOKING ABSTENTION); an abstention
  (`emerging`) counted as a domain in every rate; and a row with no real domains (R040 `emerging`, R140 blank)
  carried `depth_final_class=3` into every depth statistic. Measured on the frozen workbook: 2 owner-owed cells,
  7 soft deviations, 0 row-level hard findings (0/148 rows reach 7/7 groups; 0/148 violate the first-token
  primary rule).
- **Fix.** `config/depth_domain_contract.yaml` + `scripts/validate_depth_domain_contract.py` +
  `tests/test_depth_domain_contract.py` (status `proposed`: the owner activates it with `status: active`).
  Tiers live in config, so the owner can re-grade a finding without editing code.
- **PRESERVED BLINDSPOTS (recorded, not fixed).** S1: a vague statement with all 43 domains ticked is
  indistinguishable from a universal one by any deterministic rule — only the FORM gate can see it, and FORM has
  no anchor. S2: three groups hold only 3 domains each, so a 7/7 rule can be satisfied cheaply. S3: the 7/7 rule
  is a cliff, not a gradient. These three are asserted in the harness so the gap cannot be mistaken for coverage.

## BUG-449 - OPEN - LOW - R137 `domains_final_raw` carries a stray trailing separator no declaration covers
- **Severity:** LOW  |  **Status:** OPEN  |  **Found:** 2026-09-25  |  **Class:** provenance hygiene
- **Symptom.** R137's raw cell ends `user experience|`. `domains_final` is correct (`user experience`), so no
  judgement is wrong — the declaration set simply does not describe the bytes the owner produced.
- **Fix.** Either declare it (`cell_replacements: from "user experience|" to "user experience"`) or accept it via
  the raw reader's separator set (already done: the raw reader accepts `,` and `|`). Declaration preferred: the
  point of `anchor_workbook_fixes.yaml` is that every transformation of the owner's bytes is written down.

## BUG-450 - OPEN - the FORM (extraction_type) axis carries 150 labels with VOID rater provenance
- **Severity:** HIGH | **Status:** OPEN | **Found:** 2026-09-25 16:35 | **Class:** R14 / provenance
- `governance/R2_EXTRACTION_TYPE_RULER_20260923.json`: 150 `extraction_type` labels, and every one of the 728
  labels in that file has `coder: None`. The FORM axis is `owned` by ANCHOR-3 (`extraction_type_final`,
  intersection 145/150) yet **no FORM value is traceable to a rater**. A label that cannot be traced to a record
  is not a measurement (the same invariant `audit_form_axis.py` enforces on the runtime KB).
- Also: R2 stamps `menu_hash: d2fc500c8835db54...` = the LIVE render, which the frozen `closed_menu_v5.sha256`
  contradicts (`73597ee2b1bb1eb9...`). Concrete instance of the BUG-447 drift propagating into an artifact stamp.

## BUG-451 - OPEN - MEASURED: FORM (1-4) has ZERO discriminative power for depth-class-1 admission
- **Severity:** MED | **Status:** OPEN | **Found:** 2026-09-25 16:35 | **Class:** axis design / falsified assumption
- Measurement on the frozen ANCHOR-3 sheet (`extraction_type_human`, 145 present / 5 declared-missing):
  the 7 known retractions (the negatives class-1 admission must reject) span **3 of the 4 FORM classes**:
  R033/R062/R085/R087/R101 = `descriptive_model`, R049 = `normative_heuristic`, R139 = `causal_mechanism`.
  Human FORM over 150: `normative_heuristic` 50, `descriptive_model` 41, `causal_mechanism` 40,
  `empirical_pattern` 14, blank 5.
- Consequence: the warrant-admissible pool (normative_heuristic + descriptive_model) is **91/150 = 60.7 %**
  versus the 4/150 = 2.7 % that class 1 can hold, and `empirical_pattern` excludes 14 rows while catching
  **0 of the 7**. FORM is therefore a NECESSARY warrant field but cannot be the class-1 gate, and adding
  raters cannot supply signal that is absent from the label set (it only reduces noise).
- This falsifies the standing "build the FORM anchor first, then derive depth" plan. The un-anchored object is
  the CLAIM-SHAPE bit (comparative + STATED exchange rate + BOUNDARY), not FORM.

## BUG-452 - OPEN - the FORM panel is raw-agreement only, and it is 2 of 4 models
- **Severity:** LOW | **Status:** OPEN | **Found:** 2026-09-25 16:35 | **Class:** statistic / instrument coverage
- `governance/F11_ANCHOR_REVIEW_20260923.csv` carries `human_form, claude_form, kimi_form, form_agree,
  form_consensus` on 108 rows. `form_agree` is RAW agreement (YES 83 / NO 25 = 76.9 %) on a 4-class axis with a
  skewed marginal, with **no chance correction** - raw % on this marginal overstates agreement.
- DeepSeek and Qwen3.8 have **no FORM column** anywhere (they exist for depth and domain only), so the
  4-way cross-examination the owner asked about does not exist yet for FORM.

## BUG-446 - FIXED - update 2026-09-25: there were TWO offenders, not one - rails green for the first time
- BUG-446 had TWO offenders, not one: line 13 (unindented) AND line 15 (`        python3
  scripts/check_human_instruments.py`, 8 spaces). Fixing only line 13 moved the parse error to line 15.
  Both now dedented to 4 spaces; `just --list` parses; `just health` is runnable for the first time.
- FIRST-EVER RUN of the rails (all exit 0): `verify_anchor_family_registry` ok (ANCHOR-3 150x31 29393d5f9d52 |
  owned CT/DISC/ET 150/150/145 | depth blind 132/150 | domains DISOWNED cohort 216 intersection 2/150);
  `check_human_instruments` ok (7 locked, all protected columns byte-identical - so the FORM anchor's
  `extraction_type_human` lock IS enforced); `check_depth_menu` ok; `check_buglog_coverage` ok;
  `check_instrument_cohorts` ok for both ANCHOR-3 and ANCHOR-4.
- STANDING RULE reinforced: a rail that has never run is not a rail; the two defects above are why four
  locked-instrument guarantees were declared-but-unenforced for eight days.


## BUG-453 - OPEN - `menu_hash` is a COMPOSITE of 7 axes used as an ANSWER-SPACE pin (one hash, two meanings)
- **Severity:** HIGH | **Status:** OPEN | **Found:** 2026-09-25 16:50 | **Class:** axis design / D-321 conflict
- `config/closed_menu_v5.json` holds 7 sub-objects: `abstention, content_types, decision, disciplines,
  domains, extraction_types, schema_version`. `pipeline.closed_menu.menu_hash()` hashes ALL of them, while
  `config/closed_menu_v5.sha256` is consumed as the ANSWER-SPACE pin.
- **CONFLICT between two RESOLVED decisions.** D-285 (2026-09-20) established by observation that
  "taxonomy discipline definitions feed the closed menu" and re-rendered the hash 14540ec3 -> ... for exactly
  that reason. D-321 (2026-09-21, owner-ruled, the BUG-357 fix) widened the `behavioral economics` definition
  and stated "The answer-space pin `config/closed_menu_v5.sha256` is UNCHANGED (the menu was not touched)".
  Both statements cannot hold. MEASURED 2026-09-25: they are BOTH HALF TRUE - the DEFINITION moved
  (composite frozen `73597ee2...` vs live `d2fc500c...`), the ANSWER SPACE did not move.
- Remedy implemented (no pin move, no stamp invalidated): `scripts/menu_axis_hashes.py` emits a hash PER AXIS
  and an explicit `answer_space_hash` over `[domains, abstention]` -> `config/menu_axis_hashes.yaml`.
  `domains c9e44328...` / `abstention b5d7ab16...` / `disciplines 00d1ea51...`. An answer-space claim is now
  checkable against the answer space, and a definition edit can never again be mistaken for a slot change (C27).
- Remaining owner act: whether to also re-render + re-freeze the composite pin under a declared `menu_version`
  (a stamp every future row carries), or to leave the composite as historical and pin the answer space only.

## BUG-454 - OPEN - the token `flags` names two different things; the flag-consumer rail cannot see the new consumer
- **Severity:** LOW | **Status:** OPEN | **Found:** 2026-09-25 16:50 | **Class:** registry / naming collision
- `config/flag_consumer_registry.yaml` tracks CONFIG flags (`config: ... path: ...`). The workbook column named
  `flags` is a per-row classification flag set (`DOMAIN_NO_OVERLAP` etc.). `scripts/validate_depth_domain_contract.py`
  reads that column, so it is a NEW consumer of a *different* `flags` - `audit_flag_consumers.py` stays green and
  cannot see it. A rail that cannot see a new consumer of the thing it governs is a coverage gap, not a pass.
- Do NOT register it under `flag_consumer_registry` (that would assert a config-flag dependency that does not
  exist). Owner ruling owed: rename the workbook column (e.g. `row_flags`) or add a second registry section.
- STANDING RULE: same token, two namespaces = a lookup that silently answers the wrong question.

## BUG-455 - OPEN - the archive index has NO content identity: same-size corruption and duplication are both invisible

MEASURED 2026-09-25. `archive/index.yaml` records per entry: name, kind, bytes, files, dirs, modified,
category, disposition, authority, reason - and one `body_sha256` over the INDEX itself. It records NO
`content_sha256` for any entry. Consequences, both measured:
  - DUPLICATION is invisible. `dispositions` reports exactly 1 `purge_candidate` (`.DS_Store`, 10 KB).
    A content scan of the same tree finds 30 exact-duplicate groups covering 2.99 GB of redundant bytes
    (780 files, 17.31 GB total). The index cannot see any of it.
  - CORRUPTION is invisible. `--check` can only detect added / removed / renamed entries. A file whose
    bytes change but whose size does not is still GREEN, so the rail that exists to guard the archive
    cannot detect the one failure it is most needed for.
ROOT CAUSE: identity-by-name-and-size, not identity-by-content. NOT a new bug class - it is the same
error as BUG-450 (a label with no coder) and BUG-378(b) (an authority with no content pin): a recorded
OBJECT whose identity is not reproducible from the record.
REMEDY: add `content_sha256` per entry (files and, for dirs, a Merkle root over children) so `--check`
becomes a real integrity check and duplication is a declared, countable fact. Cost: one column.
DO NOT remedy by deleting duplicates - 2.99 GB is 17% of the archive and the byte-identical copies carry
distinct NAMES that are the audit trail (`pre_cascade_dereg`, `pre_axis_decision`, `pre_domain_swap`);
deleting the older of two identical DB backups destroys the fact that a step was a byte no-op, which is
itself evidence. Prevention belongs at the backup layer, not the archive layer.

## BUG-456 - OPEN - the S4 "rolling" backup held 6 byte-identical slots: one recovery point, six names

MEASURED 2026-09-25. `archive/session_20260923/scratch/backup/s4_rolling/checkpoint.slot1..6.jsonl` are
all 95.26 MB and all share sha256 a35ebd46bf2d217a - a 7-copy identical group (571 MB) that also matches
`checkpoint.jsonl.bak_20260903_171915_pre_reclassify`. A rolling backup exists to give N DISTINCT
point-in-time recovery points; N identical copies give ONE, so the rotation is decorative and the
apparent redundancy in the backup set is false comfort. Status: measured fact + hypothesis about the
writer. NOT yet proven that the source was quiescent between snapshots - if it was, identical slots are
legitimate and this is a WARNING, not a bug. Either way the set carries no evidence of WHICH state each
slot holds, which is the actual defect: slot identity is unrecorded.
REMEDY: record source sha256 + source mtime in each slot's manifest, and rotate only when the digest
changed. Then "rotation" is a verifiable claim instead of a naming convention.

## BUG-457 - OPEN - the boot rail flattens the contract's three-valued exit code, so "owner-owed" becomes fatal

MEASURED 2026-09-25 by flipping `status: proposed -> active` in a sandbox copy and running the real consumer.
`config/depth_domain_contract.yaml` declares THREE outcomes on purpose: 0 clean, 1 hard contract defect,
2 owner-owed (`owner_blocked`: an abstention-only or blank owner cell - "loud, not fatal", and inventing a
value would corrupt the gold). The script implements exactly that contract.
The only consumer in the repo is `justfile` line 14:
    python3 scripts/validate_depth_domain_contract.py --gate-if-active || exit 1
`|| exit 1` collapses 1 and 2 into one outcome, so the boot health rail cannot REPRESENT the state the
contract was built to carry. MEASURED: with status=active the command exits 1 today (two hard findings,
MENU_HASH_DRIFT + MISSING_MENU_VERSION), which makes the whole boot rail RED. After those two are fixed the
command would STILL be RED on exit 2, because R040 (abstention-only) and R140 (blank) are owner-owed cells
that only the owner can fill - so activating the contract as wired today converts a legitimate "owner still
owes a cell" state into a build failure, which is precisely the pressure that produces fabricated cells.
REMEDY: the rail must preserve the distinction it was given - fail on 1 (and on 2 only when running with
--strict-owner), tolerate 2 otherwise. Not applied yet: this is a rail-semantics change and it is coupled to
the BUG-447 decision; it must not be fixed by weakening the check for the hard tier.
CLASS: false pass in the other direction - "a rail that cannot express a state is not a rail for that state"
(the mirror of BUG-454: green is not coverage; here red-or-green is not the whole lattice).


## BUG-458 - FIXED - a declared cell repair was applied as a SUBSTRING edit and merged two owner domains
- **Severity:** HIGH (near-miss) | **Status:** FIXED | **Found:** 2026-09-25 17:2x | **Class:** C12 / provenance
- **What happened.** The BUG-449 fix landed as `cell_replacements: "user experience|" -> "user experience"` in
  `config/anchor_workbook_fixes.yaml`. `split_raw_tokens` applied it with `str.replace` to EVERY raw cell. On a
  cell holding a pipe-joined LIST the pattern matches inside the list and MERGES the two neighbouring domains
  into one token that is not on the menu - a declared repair silently becoming an unrecorded edit of the owner's
  bytes, which is the exact failure `anchor_workbook_fixes.yaml` exists to prevent. On the real workbook it
  happened to be invisible (R137's cell is that value alone); the adversarial battery row S1 saw it immediately
  (`RAW_UNDECLARED_TOKEN` appeared on a synthetic row that had no raw defect at all).
- **Fix.** Two declared operations with different semantics: `cell_replacements` are **WHOLE-CELL ONLY** (applied
  only when the trimmed cell EQUALS `from`), and trailing separators are handled by a new declared rule
  `trailing_separator_trim: ['|', ',']` which is idempotent and cannot merge anything. Harness:
  `test_raw_repair_is_whole_cell_only`. Contract back to 12/12 green.
- **STANDING RULE.** A repair rule is legal only when its RIGHT-HAND SIDE is a token on the closed menu and its
  scope is declared. An unqualified search-and-replace over a cell that holds a LIST is an edit, not a repair -
  and a repair that has never been run against an adversarial input is an edit nobody has audited.

## BUG-447 - RESOLVED AS DESIGN (D-371): the composite pin is HISTORICAL; the ANSWER SPACE is the pin
The composite drift is NOT repaired and must not be: re-rendering moves the stamp every 2026-09-2x row carries
and would falsify D-321's recorded claim, and overwriting `closed_menu_v5.sha256` destroys the provenance it
exists to provide. D-285 and D-321 are both correct - the DEFINITION moved, the ANSWER SPACE did not. The
contract now reports the two facts with two codes: `ANSWER_SPACE_DRIFT` (hard, over `[domains, abstention]`,
measured NOT drifted) and `DEFINITION_DRIFT` (soft, `disciplines`, measured drifted). Membership is declared once
in `config/menu_axis_groups.yaml` and read by both the generator and the checker (C12/C21).

## BUG-453 - FIXED - `menu_hash` is split by declared axis group; an off-menu axis is now a hard finding
`scripts/menu_axis_hashes.py` reads its grouping from `config/menu_axis_groups.yaml` (the earlier inline
`ANSWER_AXES = ("domains","abstention")` literal was itself the C12 defect this bug is about). New hard code
`UNCLASSIFIED_MENU_AXIS`: an axis that belongs to no group is pinned by NOTHING, so a change to it is invisible
to every check - a new sub-object added to the menu now fails closed instead of silently escaping the pin.

## BUG-449 - FIXED - the R137 trailing separator is now repaired by a declared rule, not by a separator accident
`trailing_separator_trim: ['|', ',']` (see BUG-458 - the first attempt was a cell replacement and it was wrong).
`domains_final_raw` is read byte-faithfully and the repair is written down; the raw reader's dual separators are
no longer the only reason R137 does not fire.

## BUG-450 - OPEN - CORRECTED MEASUREMENT: the `coder` key is ABSENT, not null
The claim "every label has `coder: None`" is imprecise: `governance/R2_EXTRACTION_TYPE_RULER_20260923.json` has
NO `coder` key anywhere (0 occurrences), so every read `.get("coder")` yields None across all 728 labels. The
void is the same - no FORM value is traceable to a rater - but the register must state what is on disk. The file
also stamps `menu_hash: d2fc500c...` = the LIVE composite, i.e. an artifact stamped with a hash the frozen pin
contradicts; under D-371 that is now correctly a DEFINITION-class fact, not an answer-space one, but the artifact
still carries no `answer_space_sha256`/`menu_version`, so a consumer cannot tell which pin it was written under.
REMEDY (prevention, next unit): the R2 meter must stamp a report-level `provenance` block (label source artifact
+ column + sha256, extractor, NLI model id, `menu_version`, `answer_space_sha256`) so the NEXT regeneration is
traceable; the existing artifact is left byte-identical and marked `unrecorded-at-write` rather than back-filled.

## BUG-457 - FIXED - the boot rail preserves the contract's three-valued exit code
`justfile` line 14 is now `... --gate-if-active || [ $? -eq 2 ]`. With the re-tier (D-372) the contract returns
hard 0 / owner-owed 2 on the frozen workbook, so activating it no longer converts "the owner still owes R040 and
R140" into a red build - which is the pressure that produces fabricated cells.

## AUDIT 2026-09-25 (second pass) - findings recorded in governance/evidence/AUDIT_20260925_SECOND_PASS/AUDIT_FINDINGS.md
- `DECISION-LOG.md` contains a DUPLICATE `## D-356` heading (lines 474 and 489, same title). The register parses
  headings (the BUG-446 lesson); a duplicate heading makes one decision look like two.
- Two id families coexist with no uniqueness rail across them: `D-3xx` (46 records, last D-370) and `D<num>`
  (691 records, last D2636). Nothing checks the union, so the next writer can silently reuse an id.
- `just health` still has no PARSE probe for itself: BUG-446's standing rule ("boot must verify the health command
  PARSES before trusting that it passed") is written down but not implemented - a one-line `just --list` is owed.
- `config/depth_domain_contract.yaml` hard-coded the anchor manifest path in `scripts/`; now config-declared
  (`inputs.anchor_manifest`) and the stamp is CHECKED against the pins, not merely required to exist.

## BUG-459 - FIXED - a FALSE existence-negative in a docstring: "there is NO FORM anchor"
`scripts/score_form_gate.py` asserted "FORM(1-4) is BLANK in all 150 rows of the tracked blind sheet, no
config/form*.yaml exists ... FORM therefore cannot be an upstream pipeline stage". MEASURED 2026-09-25:
`FORM (1-4)` = 145/150 non-blank in `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`; `extraction_type_final`
= 145/150 in `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` (owner ANCHOR-3, `config/anchor_family.yaml`).
The column that IS blank is DEPTH. The negative came from a glob over the wrong namespace (`config/form*.yaml`)
and from reading DEPTH as FORM - the THIRD false absence of this cycle (after "assignment" and "margins").
FIX: the claim is recorded as a MEASURED ledger row (`governance/existence_negatives.yaml` NEG-002, answer
`refuted`) and the scorer MEASURES the coverage at run time instead of asserting it in prose.
STANDING RULE: an existence-negative in prose (docstring, comment, report) must name the artifact set searched
AND the query used, and that query must have been RUN. A docstring is not a search.

## BUG-460 - FIXED - the instrument builder OVERWROTE the live instrument and narrowed its schema
`python3 scripts/build_form_elicitation.py` rewrote `governance/frontier_pack_20260924/CLAIM_SHAPE_ELICITATION_11.csv`
unconditionally: two declared columns (`evidence_span`, `abstain`) disappeared and the gate bit was renamed.
Nothing was lost only because no elicitor had answered yet; one answer later and a rebuild would have erased the
owner's only copy of the instrument's answers - silently, with exit 0.
FIX: the schema, cohort, questions and guards are declared ONCE in `config/claim_shape_instrument.yaml`; the
builder refuses to overwrite when any answered cell is non-blank (exit 3); the scorer reads the same declaration.
STANDING RULE: a generator that writes the file it is asked to score must be non-destructive by construction -
"rebuild" is an act on a BLANK instrument, never on an answered one.

## BUG-461 - FIXED - `FORM` named two namespaces (the BUG-454 pattern, third instance)
The instrument's four questions (comparative / STATED exchange rate / BOUNDARY / falsifiable) are the
CLAIM-SHAPE bit (D-374); every column, the file names and the scorer were named `FORM_*`, while FORM is AXIS 2
`extraction_type` (4 epistemic forms) with its own 145/150 anchor. Two objects, one token.
FIX: columns renamed `claim_shape_q1..q4` / `claim_shape_bit` / `claim_shape_note`; scripts renamed
`build_claim_shape_instrument.py` and `score_claim_shape_gate.py`; `config/claim_shape_instrument.yaml` states the
naming rule (C21) and the file carries no depth/verdict column.

## BUG-462 - OPEN - the declared agreement floor (D-373) has no consumer
`config/agreement_floor.yaml` (Krippendorff alpha, reporting 0.667 / operative 0.800) is read by nothing:
`grep -rl agreement_floor` -> the yaml itself and the decisions prose only. A floor nobody reads cannot gate
anything. Remedy: the FORM ceiling panel scorer (>=2 raters, missing-cell capable) must LOAD the floor and
refuse to report a decision-bearing number below `operative_floor`. Not back-filled - owed as prevention.

## BUG-463 - OPEN - `config/anchor_family.yaml` understates the depth state (intersection 0 vs 18)
The registry declares `depth: intersection: 0  # blind sheet; blank until freeze` while the TRACKED blind sheet
carries 18/150 owner depth cells (`reviewer=human`, `date 13.09.26`, R001...). MEASURED 2026-09-25. A freeze
computed from the registry's "0" would silently ignore an owner pass. Remedy: state the real starting count and
resolve the 24.09 drop-in (`Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` rev 2) before D274d/D274f.

## BUG-467 - FIXED - the aggregate rail was RED for a whole pass while every individual rail was green
`just health` failed at line 24: `RED r2_meter: scripts/definition_nli_verify.py CHANGED since it was pinned - re-run the measurement and mint a new decision (this is the BUG-391 class)`. The previous pass edited a **pinned** script (additive provenance block, D-379) and then verified with the individual rails only. Every one of them passed; the DIGEST rail is exercised nowhere except the aggregate recipe. FIX: re-pinned under D-382 after checking the change is additive (40 inserted lines, 0 removed; the 2026-09-23 measurement artifact is byte-unchanged and was NOT back-filled).
STANDING RULE: after ANY edit to a pinned or digest-locked artifact, run the AGGREGATE rail (`just health`), never a hand-picked subset. A digest rail is by construction invisible to the check that does not read it; a per-rail sweep cannot see a cross-artifact pin.

## BUG-463 - FIXED - `config/anchor_family.yaml` understated the depth state (intersection 0 vs 145)
MEASURED 2026-09-25: the block declared `intersection: 0` while the state was three layers deep - 13.09 partial 18/150, 24.09 complete 150/150 (`Copy of ...`, strict superset, 0 conflicting cells on the 18 overlap, only `date` differs), 25.09 adjudicated `depth_final_class` 145/148. FIX: the block now declares the canonical column, the cohort, the intersection (145) and BOTH predecessors by sha256, and records the measured intra-rater agreement. Freeze starts from THIS state; the merge is declared, never performed implicitly inside a freeze.
STANDING RULE: an "intersection: N" claim in config must name the artifact and column it was measured on. A coverage number without its source artifact is a number about nothing.

## BUG-462 - OPEN - the declared agreement floor still has no consumer
`config/agreement_floor.yaml` (reporting 0.667 / operative 0.800, D-373) is read by nothing. This pass produced the first real measurement that SHOULD be scored against it (depth intra-rater alpha 0.914 nominal / 0.896 ordinal, above the operative floor) and recorded it in `config/anchor_family.yaml`, but the scorer is still owed: `scripts/depth_pass_agreement.py` reading the floor and the two depth columns from config and exiting 1 below the operative floor. UNTIL THEN the floor is a decoration.

## BUG-464 - OPEN - a bookkeeping column that reads as 192 open items when 4 cells are open
`owner_answer_needed` in `governance/anchor_adjudication_workbook_20260924.csv` is a snapshot from before the owner answered: it claims `domain` is still needed for ~150 rows whose `domains_final` is filled, and it does NOT flag the cell that is actually blank (R080/depth). It is a TRUE snapshot of what the machine recommended at generation time, and a FALSE statement of what is owed today. Deriving the owed set from the data gives exactly 4 cells: `domains_final` blank (R140), `depth_final_class` blank (R070, R080, R130), plus R040's abstention-vs-depth-class contradiction.
FIX (owed, 1 line): rename the column to `owner_answer_needed_at_generation` (the BUG-454 pattern - one token, one namespace) and re-derive the owed set from the data at read time.
STANDING RULE: a "what is still owed" column must be RE-DERIVED from the artifact it describes, or be named as the snapshot it is. A stale owed-list does not just misinform - it asks the owner to redo work that is already done.

## BUG-465 - OPEN - a blank cell carries four meanings and the contract can only see one
R070/R080/R130 have `depth_final_class` blank. The owner DID answer depth for all three in the 24.09 pass (`owner_depth` = 2/3/3, carried into the workbook and identical to the 24.09 drop-in). The workbook was then superseded by the 25.09 pass, in which those three cells are blank. Nothing distinguishes: not-answered / withdrawn / declined (the workbook has an explicit token for a decline - `DEPTH_MENU_DECLINED`, used on 2 rows and NOT on these 3) / carried-forward. The contract can only report "blank", so it reports the same 3 rows every run forever, and the owner cannot clear them without inventing an answer.
FIX (owed, owner ruling): one supersession policy, applied to all four states, so a blank in a later pass does not silently erase an earlier filled answer. R040/R140 are NOT this bug: R040 is a CONTRADICTION (`emerging` + depth class 3), R140 is a declared blank (`BLANK-AS-SUBMITTED` in `governance/anchor_adjudication_fixlog_20260925.csv`).
STANDING RULE: a blank in a SUPERSEDING artifact is not the same fact as a blank in a primary one. Where two passes exist, the later pass must declare whether a blank means not-revisited or withdrawn - otherwise the earlier answer is destroyed by omission, not by judgement.

## BUG-466 - OPEN - 148 adjudicated rows against a declared 150-row cohort, with no exclusion rule
`governance/anchor_adjudication_workbook_20260924.csv` carries 148 rows; `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` and `governance/ANCHOR4_MANIFEST_20260924.json` (`"rows": 150`) carry 150. R003 and R146 appear in NEITHER the workbook nor any cohort/exclusion declaration in the manifest, the cohort builders, or the fix config - every depth/domain rate is therefore computed over 148 while the declared cohort is 150. Nothing was deleted from disk (both ids are present in the blind sheet, the consolidated ruler and `frontier_pack_20260924/BLIND_INPUT_150.csv`), so this is an UNDECLARED cohort narrowing, not data loss.
FIX (owed, owner declaration): state why R003/R146 are outside the adjudication population (`retracted` / `duplicate` / `out-of-scope`) and record it as a cohort exclusion with a reason, or restore them.
STANDING RULE: any artifact whose cohort differs from the declared cohort must DECLARE the difference where the cohort is declared. A 148-row file under a 150-row manifest is a denominator that changed silently.

## BUG-468 - OPEN - a digest recorded in prose for a live file that has since been written
`config/anchor_family.yaml` (`interim_20260924`) records the owner's complete depth drop-in as sha256 `be1a39e0...`; MEASURED 2026-09-25 it is `bc1cc956...`. The drop-in was written after that evaluation, so the record describes bytes that no longer exist - the same defect as the false existence-negative (BUG-459) and the stale register (BUG-467/BUG-464), now on a DIGEST.
STANDING RULE: a sha256 written next to a file that anything may still write is a claim with a shelf life. Record it as `sha256_measured_at: <stamp>` beside the value, or point the record at a frozen copy under `backups/` - never a bare digest next to a live path.

## BUG-469 - FIXED - the archive-index rail flipped RED on a Finder browse, with zero content change
`just health` failed: `RED archive index: archive/index.yaml is STALE - stored body_sha256 17889fac47b2 != measured 43a9de5a5bc9`.
MEASURED cause: macOS Finder/Dropbox wrote `archive/bak_sweep_20260923/.DS_Store` (+1 file, +6148 bytes) and rewrote
`archive/.DS_Store` at 18:01:21; the index counted those bytes and took each directory's OWN mtime as its date.
FIX: `config/archive_index.yaml#ignore` (names + globs) excludes OS metadata from every count AND from the date, which is
now the newest NON-IGNORED descendant. VERIFIED stable across a `touch` of both `.DS_Store` files.
STANDING RULE: a rail that a file browser can flip is a rail the owner learns to ignore (the BUG-462 class).

## BUG-470 - FIXED - a live test asserted a value that a DECISION had deliberately refuted, and no rail ran the suite
`tests/test_stage4_preflight_smoke_stress.py::test_depth_frugal_is_off` asserted `S4_DEPTH_MODEL == "gemma-4-E4B-it-MLX-4bit"`
while `config/pipeline_config.yaml#stage4.depth_model` is DELIBERATELY `null` (BUG-403/405 Gate D; the literal was refuted by
D2454) and `pipeline/pipeline_paths.py` carries NO code default. The test was stale at HEAD; `just health` runs rails, not the
suite, so it was invisible. FIX: the test now asserts the state we are in (`== ""`), and `just health-deep` runs the full suite.
STANDING RULE: an assertion about a config value must cite the decision that set it; otherwise the test outlives its reason.

## BUG-471 - OPEN - the full suite fails in one ORDER and passes in another (a hidden failure, not a flake to ignore)
`python3 -m pytest tests -q` -> `test_s5_failed_classification_quarantines` FAILED; the same test PASSES alone and inside a
2-file run (9/9 in its own file). Cross-test state pollution: a rail that is green or red depending on collection order is
not a measurement. Reproduce: `python3 -m pytest tests -q`. NOT diagnosed this pass (needs a bisect of the preceding file).

## BUG-465 - POLICY IMPLEMENTED (D-387) - a blank in a superseding pass now has a declared meaning
R070/R080/R130 were blank on depth in the 25.09 pass although the owner ANSWERED all three on 24.09 (owner_depth 2/3/3,
identical to the drop-in, sha bc1cc956...). RULED: OMISSION IS NOT WITHDRAWAL - carry-forward is the default; withdrawal
requires the explicit `..._DECLINED` token (already used on R021/R026, NOT on these three). Applied by
`scripts/apply_workbook_rulings.py` under `just health` --check, so a normalize re-run cannot silently revert it.

## BUG-472 - FIXED (self-inflicted, same pass) - the new applier logged the LOGICAL column for every written cell
`apply_workbook_rulings.py` appended `R070 depth_final: '' -> '2'` (the class write logged under the ruling's column name).
FIX: the fix log now records the column that actually changed; the 9 mislabelled rows were replaced with 9 correct ones in
the same pass. LESSON: a writer's own log is part of its output and is verified like one (R5 in miniature).

## BUG-473 - OPEN (SEVERE, evidence on disk) - the test suite ROTATES a LIVE production checkpoint
Root cause of BUG-471 found. `python3 -m pytest tests -q` (started 18:24) caused
`knowledge pipeline/stage5_verify/t11/checkpoint.jsonl` (1.03 GB, the live S5 checkpoint of the 7995-FB run) to be
RENAMED to `checkpoint.jsonl.stale_20260925_182629` at 18:26:29, and rewrote `checkpoint.jsonl.input_fingerprint.json`
at 18:27. `just health` then went RED: `t11::checkpoint.jsonl: AUTHORITATIVE artifact is MISSING (C16)`.
RESTORED this pass by copying the rotated file back (bytes preserved; the .stale_ file KEPT as evidence).
WHY IT IS SEVERE: a test run in the repo mutates production pipeline state, and the same side effect explains the
order-dependent failures (BUG-471): tests share the real `knowledge pipeline/` paths instead of a tmp dir, so the
suite's own order decides whether they pass. A killed run can delete a live artifact (it did).
STANDING RULE: a test may not write outside a tmp dir. Any harness that resolves a production path must take an
explicit override. Fix = find the test that resolves `stage5_verify/t11` and give it a declared tmp root.

## BUG-473 - FIXED (2026-09-25, same day) - the suite rotated a LIVE production checkpoint
ROOT CAUSE (pinned, not guessed): `tests/test_fail_closed_d2402_2405.py::test_s5_failed_classification_quarantines`
called `run_stage5()` with `safe_write`/`load_stage4_fbs` patched but the REAL `STAGE5_CHECKPOINT`, so the D2507
stale-archive branch renamed the live 1.03 GB t11 checkpoint.
FIX: (a) the test redirects STAGE5_CHECKPOINT / S5_INPUT_FINGERPRINT_PATH / STAGE4_5_CHECKPOINT / S5_LOCK_PATH into
tmp_path; (b) `tests/conftest.py` snapshots the production stage trees and FAILS the session if the suite moves an
UNDECLARED artifact (declarations in `config/test_isolation.yaml`; a declared `smoke_*` touch is tolerated AND reported).
EVIDENCE: the guard's first run caught the violation and named the paths; the second full run moved nothing
(`232 passed, 5 skipped`, live checkpoint byte-count unchanged 102936020).

## BUG-471 - FIXED (2026-09-25) - the order-dependence WAS the production-lock leak
`S5_LOCK_PATH = Path(str(STAGE5_CHECKPOINT) + ".lock")` is bound at IMPORT time, so patching the checkpoint constant
does not move the lock: the first S5 test wrote `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl.lock`, and the
second S5 test in the same pytest process read it as a LIVE holder (same pid) and died with SystemExit. BUG-471 and
BUG-473 are one defect with two symptoms. Full suite is now order-independent.

## BUG-474 - FIXED (2026-09-25) - a DUPLICATE `expect_blank:` key in config/anchor_workbook_fixes.yaml
Two blocks declared the same top-level key. PyYAML resolves a duplicate key by last-wins, so the earlier
`[R140]`/`[R070,R080,R130]` declaration was silently discarded. The surviving reading was the intended one, but the
file held two answers. Declaration now lives in exactly ONE place.

## BUG-475 - OPEN (pipeline-side, needs owner ack) - a path constant bound at import cannot be isolated
`pipeline/stage5_verify.py:560` computes `S5_LOCK_PATH` from `STAGE5_CHECKPOINT` at import. Every test that isolates
the checkpoint must ALSO know to patch the lock, and a future test that forgets it writes into the live tree again.
STRUCTURAL FIX (not applied: pipeline/** is production code): resolve the lock path AT CALL TIME from the same
constant, or take the lock path as a parameter. Until then the conftest guard is the only control.

## BUG-478 - OPEN (severity HIGH) - the only declared panel ingester REWRITES the ANCHOR-4 workbook and blanks the owner's adjudicated cells
- FOUND BY: the 2026-09-25 forensic audit, before implementing "run the two declared depth coders".
- MEASURED: `scripts/cross_examine_anchor_axes.py::write_outputs` opens `governance/anchor_adjudication_workbook_20260924.csv` with mode `"w"`, writes ONLY the `dispute` set, and then executes `for k in WORKBOOK_OWNER_COLS: rec[k] = ""` where `WORKBOOK_OWNER_COLS = ["domains_final", "depth_final", "owner_note", "owner_date"]` (line 53/545).
- EVIDENCE THAT THIS IS THE LIVE PATH: the workbook on disk holds 148 rows (tier SOFT 112 / HARD 36), `owner_depth` 148/148, and `depth_final`/`domains_final` carry the owner's adjudicated answers; its header matches that function's `wb_cols` exactly. The file was generated by this script and then filled by the owner.
- CONSEQUENCE: the documented way to complete the declared depth panel (drop `raw_<coder>_<chunk>.md`, re-run the ingester) would have DESTROYED 148 owner cells, blanked `depth_final`/`domains_final`, and truncated the file to the dispute set. A data-loss path disguised as the standard procedure - invisible because the script's own output looks correct.
- MITIGATION SHIPPED: `scripts/ingest_panel_column.py` (validates through `parse_frontier_pack.py`, writes exactly ONE declared column, REFUSES if any other cell would change, refuses to overwrite an answer, tempfile->fsync->os.replace + timestamped backup). Declaration: `config/agreement_floor.yaml#panels.depth_axis_panel.ingest`.
- ROOT FIX (owner, `scripts/**` only): guard the workbook branch behind a refuse-or-lock, or delete it. NOT DONE - it can still be run by hand.

## BUG-479 - FIXED (same-session) - the elicitation composed the gate bit BEFORE assigning its inputs
- `scripts/elicit_claim_shape.py` computed `claim_shape_bit` from `r["claim_shape_q1..q3"]` and only then did `r.update(bits)`, so every bit was 0 regardless of the answers. Caught by `score_claim_shape_gate.py` in the FIRST run; the canonical instrument was NOT written (the run wrote a receipt file), so no contaminated artifact exists. Fixed by moving the composition after `r.update(bits)`; the bit on the receipt was recomputed deterministically from the stored q-columns.

## BUG-480 - OPEN (severity MEDIUM) - the CLAIM-SHAPE gate is a perfect screen and a weak classifier: 10/11, not shippable
- MEASURED (blind, non-author elicitor Qwen3.8-27B-MLX-4bit, 11 rows, identity withheld, temp 0 server-side): negatives REJECTED **7/7**, false positives **0**, candidates ADMITTED **3/4** (miss U002 Proxy Decay: q1=0). Declared rule q1&q2&q3 and the q4 variant agree exactly (3/4).
- WHY IT FAILS THE BAR: D-395 requires 7/7 AND 4/4 to ship the gate; `score_claim_shape_gate.py` exits 1 by design. Class-1 admission therefore stays UN-GATED - the honest state.
- MEASURED STRUCTURAL DEFECT: **q3 (boundary) is answered 1 on 11/11 rows** - it is a CONSTANT on this cohort and can contribute nothing to a gate; q4 is 10/11. The only discriminating questions are q1 (4/11) and q2 (3/11).
- NOT A CONTAMINATION RESULT: the elicitor never saw the cohort, the verdicts, the depth axis, or the item_ids.

## BUG-476 - ROOT RESOLVED (declaration made TRUE, was HIGH) - FIXED (rail) / ROOT OPEN - 2 of the 5 DECLARED depth raters have ZERO ratings
- **Severity:** HIGH | **Status:** rail FIXED, root OPEN | **Found:** 2026-09-25 18:55 | **Class:** instrument / invisible gap (BUG-450 family)
- MEASURED: `config/agreement_floor.yaml#panels.depth_axis_panel.rater_columns` declares FIVE raters. On the
  148 measured rows: `Qwen3.8-27B-MLX-4bit_depth` = **0/148** and `deepseek-v4-pro_depth` = **0/148** (every
  cell empty). Both models have FULL columns on the domain axis (148/148), so the depth pass was simply never
  run for them - the declaration is aspirational, not executed.
- WHY IT WAS INVISIBLE: alpha is missing-cell capable (that is why the floor chose it), so a rater who rated
  *nothing* is indistinguishable from a rater who skipped a few rows. The receipt printed
  "5 declared rater column(s)" and the band was read from a panel that is actually **3 raters**.
  This is BUG-462's exact class again: a declaration no consumer can falsify.
- CONSEQUENCE FOR THE NUMBER: alpha 0.4004 nominal / 0.5701 ordinal is the figure of a 2-LLM+1-human panel
  (claude 142, kimi 144, owner 144) - NOT of the declared 4-LLM+1-human design. The "frontier second coder"
  question was being asked about a panel whose two missing members were already declared.
- FIX (rail, this pass): `scripts/depth_pass_agreement.py` now counts ratings per declared rater, prints
  `raters rated` with per-rater counts, names every declared rater with zero ratings (fail-VISIBLE), and
  `--gate` returns 1 when any declared rater is empty. `--report-only` stays exit 0 (a gap is a FINDING for
  the owner, not a broken rail). Config untouched: the roster still lives in exactly ONE place.
- ROOT FIX (owner): either RUN the two depth passes, or amend the declaration to the panel that exists.
  Do not leave a 5-rater declaration over a 3-rater measurement.

## BUG-477 - OPEN - the FORM coder columns are `label (margin)` strings, and `owner_form` is declared but empty
- **Severity:** LOW | **Status:** OPEN | **Found:** 2026-09-25 18:58 | **Class:** format / declared-but-empty column
- `governance/F11_ANCHOR_REVIEW_20260923.csv` (108 rows) carries `human_form` (103/108), `claude_form`
  (108/108), `kimi_form` (108/108), `owner_form` (**0/108**), `form_agree`, `form_consensus`.
  The two coder columns hold `empirical_pattern (0.55)` - label + confidence in one cell - so they cannot be
  fed to a menu-validating statistic without a DECLARED normaliser (the depth columns are bare tokens).
- `owner_form` is the same defect as BUG-476: a declared rater column with zero data.
- CONSEQUENCE: the FORM axis' reliability canNOT be reported from this file today, and a "FORM ceiling panel"
  would be built on top of a column format that has never been normalised. Any FORM agreement number must
  first normalise + declare the parse, and report both denominators.

## BUG-481 - OPEN (severity MED) - the machine register over-reports: 8 bugs carrying an explicit status field in the body are still counted OPEN
MEASURED 2026-09-25 (root-cause audit). `scripts/bug_status.py` folds STATUS EVENTS and a status event is a
HEADER. A closure written as a body paragraph is therefore invisible, and the register over-reports.
Measured with the strict probe (an explicit bolded Status field naming FIXED, RESOLVED or CLOSED, inside the last header's body):
BUG-254, BUG-276, BUG-283, BUG-284, BUG-285, BUG-286, BUG-379, BUG-380 - 8 ids. With a looser probe
(any closure word in the body) 19 ids match, of which BUG-341 / BUG-343 / BUG-314 / BUG-355 are correctly
OPEN (they mention another bug's closure, `FAILS CLOSED`, or a partial). So the honest figure is 8.
CONSEQUENCE: the register says 114 open where at most 106 are; `c15_must_append_to_handoffs` is driven by a
phantom count; and any session quoting "114 open" is quoting a parse artifact, not the state.
ROOT CAUSE (class, not instance): one FACT (is this bug open?) is carried in TWO PLACES (the header event and
the body prose) and nothing reconciles them. `scripts/check_bug_status.py` CANNOT catch this: it re-derives
the register from the same headers and byte-compares, so it certifies the PARSER, never the LOG. A rail whose
evidence is the same source as the artifact it checks cannot detect drift - the BUG-467 class.
FIX DIRECTION (not applied, owner-gated): make the divergence RED rather than silent - in bug_status.py, if
the last header classifies OPEN and the body carries an explicit closure field, emit a `divergent` state and
fail closed. That keeps one fact in one place (the header is the event) while making the other place loud.

## BUG-482 - OPEN (severity MED) - three checks built this week are invoked by nothing, so they cannot report
MEASURED 2026-09-25: `grep -c <name> justfile` gives 0 for `scripts/check_depth_load_bearing.py` (D-397 rail,
built + measured green last session), `scripts/ingest_panel_column.py` (D-398, the declared SAFE panel
ingester) and `scripts/score_claim_shape_gate.py` (D-399, the gate measurement). All three exist, all three
have been run by hand, none is reachable from `just health` or any recipe.
CONSEQUENCE: a check that nothing invokes is a comment (BUG-462 class, second recurrence this week). The
depth-load-bearing rail - the one whose whole purpose is to make a silent future failure impossible - would
itself fail SILENTLY, and the failure it guards (a depth head trained on a 3-rater axis) would arrive unseen.
ROOT CAUSE: `just health` is a hand-maintained list. Adding a rail is an edit to a prose block, and nothing
asserts that a `scripts/check_*.py` which declares a contract is invoked anywhere. The gate that would catch
a forgotten rail is itself forgotten the same way.
FIX DIRECTION (not applied, owner-gated): a meta-rail that diffs `scripts/check_*.py` + `scripts/verify_*.py`
against every recipe in `justfile` and treats an uninvoked check as RED. One screen closes the whole class.

## BUG-483 - FIXED (same session, rail in place) - the decision registry's state census was silently wrong: 62 of 766 records carried their state where nothing read it

WHAT HAPPENED. `config/decisions.yaml` is the source of truth for decision ids, and the summary block (the
decision census) is derived from it by `scripts/recompute_decision_summary.py`. The producer resolved each
record's state with `d.get("state") or "ACTIVE"` - a SILENT DEFAULT. MEASURED at HEAD `96b1e9c`: 59 records
carried an explicit `status:` key instead of `state:` (values ACTIVE 32, RESOLVED 20, RATIFIED 4, superseded 1,
complete 1, PROPOSED 1), and 3 records (D-397, D-398, D-399 - this week's) carried no state key at all. All 62
were counted ACTIVE. The declared census said active 511 / resolved 161 / ratified 11; the true census is
active 487 / resolved 184 / ratified 15 (+ 2 records with a value absent from the declared vocabulary:
RATIFIED 15 and OPEN 17 were IN USE but UNDECLARED in STATES). 34 records carried the SAME fact twice
(`state:` AND `status:`), with nothing reconciling the two copies - exactly one pair DISAGREED (D2293
`state: SUPERSEDED` vs `status: complete`). Separately, `D-331` and `D331` normalise to ONE token and were held
by two DISTINCT decisions (a C21 violation: one token, one namespace).

ROOT CAUSE. Same class as BUG-481 one level up: one fact (which state is this decision in?) carried in two
places with no reconciliation, plus a default that made an unmeasured value look measured (RC-5/D-404: a
defaulted ruler is not a ruler). `recompute_decision_summary.py --check` could not see it because it read the
same key the producer wrote - it certified the parser, never the registry (BUG-467 class, D-402).

FIX (all measured, `just health` green).
1. DATA: every record now carries exactly one canonical `state:` key (uppercase); the redundant agreeing
   `status:` lines were collapsed; D2293's conflicting `status: complete` was dropped in favour of the
   canonical `state: SUPERSEDED`; the 3 state-less records now carry `state: RESOLVED` (consistent with their
   siblings D-391..D-396); the dashed `D-331` bake-off record was renumbered `D-406` (with an `id_note`)
   because the referenced spelling is `D331`; `D-365` gained its missing `category`.
2. THE DECLARED VOCABULARY now matches reality: `RATIFIED` and `OPEN` were IN USE but UNDECLARED, so they are
   declared in STATES (names, not defaults).
3. FAIL-CLOSED: `canonical_state()` raises SystemExit naming the offending id when a record has no canonical
   state or a state outside the vocabulary; a missing `category` is likewise a hard failure instead of being
   filed under `GOV`. `record_problems()` reports duplicate ids and any legacy `status:` key on the `--check`
   path, so `just health` fails loudly. The independent oracle in `tests/test_decision_summary_sync.py` was
   ALSO fail-closed - it had copied the same `or "ACTIVE"` default, which is why an independent test could not
   catch this: a second oracle that shares the producer's blind spot is not a second oracle (D-402).
4. STRUCTURAL: `scripts/reconcile.py` gained `decision_exists` and `decision_registry_wellformed`, and
   `config/reconciliation.yaml` now declares 5 entries (registry well-formedness + the citation of every
   config that stamps a `decided:`/`decision:` id). Every `decided:`/`decision:` value under `config/**` is
   re-derived against the registry in one pass: an id that does not exist is RED. `config/register_divergence.yaml`
   cited `decided: BUG-481` (a bug is a symptom, not a rule) -> now `decided: D-402`, driver BUG-481.
   `config/decisions.yaml` is declared in `config/artifact_ownership.yaml` (append_only, writer
   recompute_decision_summary.py).

STATE AFTER. 766 -> 772 decisions (D-400..D-406 registered; D-400..D-405 are the six gates the new guards
already cited, so their provenance stamps are no longer claims about nothing), stamp `aa69ae412a641374`,
`recompute --check` clean, `tests/test_decision_summary_sync.py` 3 passed. Still OWNER-OWED and visible: 3
citation values are not id-shaped and no rail can validate them - `config/eval_integrity.yaml:decision=<blank>`
and `...:decision='DECLARED HOMONYM ...'`, `config/menu_axis_hashes.yaml:decision='798aa2f1...'` (a SHA is not
a decision - the key is semantically wrong there).

## REGISTER PROMOTION 20260925 - eight prose closures promoted to header events

WHY. scripts/bug_status.py folds STATUS EVENTS and a status event is a HEADER, so a closure written as a body
paragraph was invisible and the register OVER-REPORTED: MEASURED 2026-09-25, eight ids carried an explicit status
field asserting FIXED or RESOLVED in the body while their last header classified them OPEN.
config/register_divergence.yaml declared exactly those eight and its declared_max was SHRINK-ONLY.

THE RULE (D-402, one fact one home). The body paragraph is HISTORY and is NOT edited (R-D410 append-only); the
header event below is the register-visible statement of the same fact. No bug is closed here that the log did not
already assert in its own explicit status field, and each promotion is listed with that field as evidence, so the
act is auditable line by line and reversible by a later REOPEN event.

EVIDENCE LEDGER (body status field -> promoted state)
  BUG-254 Status: FIXED -> RESOLVED    BUG-276 Status: RESOLVED -> RESOLVED
  BUG-283 Status: FIXED -> RESOLVED    BUG-284 Status: FIXED -> RESOLVED
  BUG-285 Status: RESOLVED -> RESOLVED BUG-286 Status: RESOLVED -> RESOLVED
  BUG-379 status: FIXED -> FIXED       BUG-380 status: FIXED -> FIXED

EFFECT. The divergence list drops 8 -> 0, the mandated direction for a shrink-only list, and the register open
count now comes from somewhere a reader can check.

### BUG-254 - RESOLVED
### BUG-276 - RESOLVED
### BUG-283 - RESOLVED
### BUG-284 - RESOLVED
### BUG-285 - RESOLVED
### BUG-286 - RESOLVED
### BUG-379 - FIXED
### BUG-380 - FIXED


## SESSION 20260925B — D-403 + D-400 mechanisms built; three new findings

### BUG-486 - FIXED
- **status**: FIXED
- **class**: RC-2 (declaration and reality never joined) — INSIDE the engine built to catch RC-2
- **detail**: scripts/reconcile.py reach() compared a declared edge reader as a PATH ("scripts/drift_monitor.py") against a set holding BASENAMES ("drift_monitor.py"), so the edge declared in config/reconciliation.yaml#meta.reach.declared_commands could NEVER fire. Consequence: scripts/check_suite_coverage.py and scripts/check_stale_toolcall_rows.py were reported "uninvoked" for a whole session, and debt_max was lowered to 0 against a false measurement. A declaration that no reality could join, inside the reconciliation engine.
- **fix**: reach() split into _reach_closure() + _base(); readers normalised by basename; each declared edge is now COUNTED and one row per edge is reported every run. New config key meta.reach.require_edge_fires: true makes an edge that fires nothing DRIFT (never a silent pass) — the same rule the engine applies to every other declared object. MEASURED after: 79 reachable (was 66), 0 uninvoked, 1 declared edge live.
- **guardrail**: config/reconciliation.yaml#meta.reach.require_edge_fires. A future declaration that cannot fire is RED by construction, not by someone remembering.

### BUG-487 - OPEN (owner gate)
- **status**: OPEN
- **class**: RC-3 (self-certifying rail) / green by vacancy
- **detail**: governance/METRICS.jsonl and governance/MUTATION_JOURNAL.jsonl DID NOT EXIST, yet "just health" reported "ok metric envelopes: 0 metric(s) carry population/denominator/ruler/code_sha" and "ok write_guard selftest". scripts/lib/measure.py#envelope_gaps() returns [] for an absent registry, so the rail is green because there is NOTHING to check: D-404/I4 had zero records and D-401/I1 had zero production writes. An empty population read as compliance.
- **lead**: instrument_control.py --score now emits the first enveloped metric (governance/METRICS.jsonl created); write_guard still has no production writer.
- **owed**: a declared population floor for the metrics registry (min_records in config, C12) so "0 metrics" can never again read as ok; and a first guarded production write so the mutation journal carries real receipts.

### BUG-488 - OPEN (DRIFT, found by a mechanism on its FIRST run)
- **status**: OPEN
- **class**: RC-2/BUG-376 (a hash claim that points at a path, not at bytes)
- **detail**: ONE logical 150-row artifact exists at three paths with THREE different digests: governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv bc1cc956 (203506B, owner drop-in, write-locked), governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv b47114d4 (203253B), governance/frontier_pack_20260924/BLIND_INPUT_150.csv 240f0a84 (159206B, labels stripped). Separately, governance/ANCHOR4_DEPTH_OWNER_PASS_EVALUATION_20260924.md quotes sha256 be1a39e04c378af9 for its evaluated artifact, and that digest matches NONE of the three files on disk. A claim about bytes that resolves to no bytes.
- **evidence**: scripts/verify_handoffs.py (D-403 rail), first execution, VH_RC=1.
- **owed (owner)**: rule the identity of the three paths (same / derived / distinct). The assistant must not assert it. Once ruled, the rail compares.

### BUG-484 - OPEN
- **status**: OPEN
- **detail**: governance/p0_p1_criteria.yaml declares 28 executable criteria since 2026-09-17 and scripts/drift_monitor.py evaluates every one, but NOTHING invoked the monitor: the chain was dead at its ROOT (BUG-482 one level up). Adding a caller reveals the board is RED: 3 DRIFT (P1.gate_artifact_fresh stale gate artifact; AX4.runtime_matches_gold_4axis; AX5.form_axis_traceable) + 2 WARN. A rail known red does not belong in the fail-fast invariant chain, so the caller is "just criteria", NOT "just health".
- **owed**: repair the 3 DRIFT criteria before any of them joins the invariant chain.

### BUG-485 - FIXED
- **status**: FIXED
- **detail**: reachability was a PROXY (does this filename appear in the justfile?), not a measurement: it could not see an INSTALLED GIT HOOK (.git/hooks/pre-commit to scripts/check_session_plan.py) and it could not see a file that DECLARES invocations (governance/p0_p1_criteria.yaml). It therefore UNDER-COUNTED reachable checks and mis-attributed two of them.
- **fix**: reach is now a DERIVED closure over declared invocation edges: roots (justfile, scripts/install_git_hooks.sh) plus declared_commands honoured only when the declared reader is itself reached (BUG-486).

## D-403 (I2) MECHANISM BUILT — content-addressed handoffs
- config/handoffs.yaml, scripts/lib/handoff.py, scripts/verify_handoffs.py, governance/HANDOFFS.jsonl (append-only), governance/handoffs/blobs/ (content-addressed).
- ONE FACT ONE HOME: mutability is READ from config/artifact_ownership.yaml; handoffs.yaml never re-declares it.
- 6 receipts taken (origin=backfill: honest labelling — they claim what the bytes ARE now, not what a past run consumed). 3 blobs sealed, so the verified image now SURVIVES a rewrite (BUG-376's actual loss).
- Meter validated before it decided (RC-5): --selftest proves a rewrite changes the digest.
- Checks: receipt_present, path_present, digest_current, prefix_intact (append_only), sealed, hash_claim, identity.
- OWNER-GATED CUTOVER OWED: stage call-sites under pipeline/ (nothing under pipeline was touched this session).

## D-400 MECHANISM BUILT — no instrument decides until measured on a sealed control
- config/instrument_controls.yaml (declared BEFORE measurement), scripts/instrument_control.py, governance/INSTRUMENT_CONTROLS.jsonl.
- Meter validated first: --selftest (a perfect scorer must score 1.0, a 2-of-4 scorer 0.5).
- First SEALED control measured: claim_shape_gate, n=11 (4 positives / 7 negatives), cohort = the known answer, item_id withheld from the elicitor.
- depth_head and s4_classifier are declared owe_control with their owed text, so D-400's OWED list stays visible rather than being softened.
- Existing unsealed baseline recorded: depth_head n=133 macro_f1=0.4073 over a BUILDER-CHOSEN split (evidence about the split, not about the world).

## D-404 (I4) FIRST PRODUCTION CONSUMER
- scripts/verify_handoffs.py and scripts/instrument_control.py both emit through scripts/lib/measure.py, so the first records exist in governance/METRICS.jsonl and no number travels without its ruler.
- measure.py fixed: a ruler named as a string is accepted (the registry forwards it verbatim).

## SESSION 20260925C — the handoff rail got a CALLER, then the in-place-rewrite finding was ruled by bytes

### BUG-488 - CLOSED (correct, but the diagnosis in round B was WRONG and is corrected here)
- **class**: D-403 / RC-2 — a hash claim that no reachable store resolved, inside the rail built to catch exactly that.
- **CORRECTED DIAGNOSIS**. Round B recorded "one logical 150-row artifact at three paths with three digests, and a
  quoted sha256 that matches NONE of the files on disk". Both halves were WRONG:
  - the three paths are NOT three revisions of one artifact. Each has a ROLE, and each role is DECLARED in this repo:
    `governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` = the write-locked owner drop-in (rev 2, declared in
    config/human_instrument_locks.yaml AND config/anchor4_interim_state.json#dropin_sha256);
    `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` = the TRACKED sheet carrying pre-consolidation context plus the
    owner's PARTIAL pass (declared in config/anchor4_interim_state.json#reason);
    `governance/frontier_pack_20260924/BLIND_INPUT_150.csv` = the blinded input handed to a coder (declared in
    config/cross_exam + handoffs.yaml#why).
  - the digest does resolve. `be1a39e04c378af978f...` is REV 1 of the drop-in, declared as SUPERSEDED in
    config/human_instrument_locks.yaml#superseded and config/anchor4_interim_state.json#dropin_superseded_sha256, and
    its bytes are content-addressed in the git object store. MEASURED this session:
    `git cat-file -p 075ae65:"governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv"` -> sha256
    be1a39e04c378af972bbb321f71c262eaca3252ffe72d5eb179867a6097d6fcb, 203506 bytes = exactly the digest and size the
    receipt quotes. The bytes were NEVER lost.
- **REAL DEFECT (stands, now closed by mechanism)**: the receipt's hash claim pointed at a PATH whose bytes had been
  rewritten IN PLACE (rev 1 -> rev 2, equal-length date edit 13.09.26 -> 24.09.26, SAME byte count 203506, so a size
  check can never substitute for a digest). The rail resolved digests against LIVE PATHS ONLY, so a superseded revision
  read as "resolves to nothing" — a JOIN MISS reported as an artifact defect.
- **fix**: config/handoffs.yaml#revision_locators + scripts/lib/handoff.py --seal-revisions (bytes read from the named
  store, digest RE-DERIVED, disagreement raises) + scripts/verify_handoffs.py#revision check. Rev 1 is now SEALED:
  governance/handoffs/blobs/be1a39e04c378af972bbb321f71c262eaca3252ffe72d5eb179867a6097d6fcb.bin.
- **guardrail 1 (resolution domain)**: the rail reports each quoted digest with the KIND of store that resolved it
  (`bc1cc956...:live`, `be1a39e0...:revision`), so "unresolved" can never again be read as "the artifact is broken".
- **guardrail 2 (cross_declaration)**: EVERY digest this repo declares about a path — config/human_instrument_locks.yaml
  (instruments[].sha256 and superseded[].sha256) and config/anchor4_interim_state.json (dropin_sha256,
  dropin_superseded_sha256) — is joined to bytes in ONE place. MEASURED: 10 declared digest(s) across 2 source(s) all
  resolve. An ORPHAN digest is now DRIFT wherever it is declared, not only where this config happens to look.
- **guardrail 3 (floors, BUG-487 class)**: a rail reading an absent journal or blob store FAILS CLOSED —
  floors: min_receipts 6 / min_sealed_blobs 3 (measured 8 and 4).
- **guardrail 4 (identity)**: a role declared elsewhere is verifiable; a role asserted by the rail is not. identity_map
  names the DECLARING FILE and the rail fails if that file is gone.

### BUG-489 - OPEN (process; the mirror of BUG-468-class "false missing signal")
- **class**: finding inflation / unstated rail premise (RC-5 adjacent).
- **detail**: round B reported a defective ARTIFACT ("one artifact, three digests, digest resolves to no bytes") when the
  defect was in the RAIL'S RESOLUTION DOMAIN. A rail's domain is an unstated premise of every finding it prints, and an
  unwritten premise is indistinguishable from a fact about the world. Cost: one session of owner-facing noise about a
  non-problem, and an "identity unresolved" declaration written into config for a question the repo had already answered.
- **owed**: a declared `resolution_domain` for every rail that resolves an identifier (reach, handoff digests,
  reconcile), plus a rule that a finding may not name an artifact as defective without first naming the store, domain or
  enumeration that was searched. Assistant recommendation: add the field to config/reconciliation.yaml#meta per rail and
  have reconcile.py print it beside each row.

## ROLE / REACH HYGIENE (this session)
- `just handoffs` (D-403) and `just instruments` (D-400) now CALL their rails, so neither is a declaration with no caller
  (BUG-482/486 class) and neither depends on a filename-in-justfile proxy to be reached.
- scripts/verify_handoffs.py joined the fail-fast chain: `python3 scripts/verify_handoffs.py || [ $? -eq 2 ]` — exit 2
  (owner-owed) stays LOUD but NOT fatal (BUG-457).
- MEASURED after wiring: `just health` RC=0 (71 ok lines), reconcile `0 uninvoked of 80 reachable check script(s)`,
  handoff rail RC=0 (6 declared path(s), 12 digest(s), 1 revision), `just instruments` RC=0 (1 of 3 instruments hold a
  sealed control — the other 2 stay owner-owed and visible).

## SESSION 20260925D — a resolution domain is a DECLARED premise, and store floors got one home

### BUG-489 - CLOSED (resolution domains declared, published, joined)
- **BUILT**: `config/resolution_domains.yaml` declares, for all four identifier-resolving rails, the identifier
  kind, every store searched WITH ITS READER, the metric that must publish the coverage, and the failure mode the
  declaration prevents. `scripts/lib/measure.py` now REFUSES to emit a declared resolver metric with no `domain`
  block (identifier/stores/searched/resolved) - a coverage claim that does not name what it searched reports its
  join misses as facts about the world. `scripts/verify_handoffs.py` emits the domain in both envelopes and prints
  `domain handoff_hash_claims: ... resolved against 3 store(s) [...] -> 12/12` beside its rows. `reconcile.py` joins
  the registry to reality on every run (rail present, every store names a reader, every declared metric published
  WITH its domain, a resolver with no metric must state `no_metric_reason`).
- **MEASURED**: `4 resolver(s), 9 declared store(s), 0 blind store(s)`; handoff digests 12/12 resolved; reconcile
  8/10 objects ok; `measure --gaps` -> `18 metric(s) (floor 12); 4 carry a declared resolution domain`.
- **OWED**: a DECISION ID for "a resolver declares and publishes its domain" - the mechanism cites D-405, and
  minting the id is the owner's act (C22). Logged as the next critical step.
- **RULE now enforced**: a finding may not name an artifact defective without naming the store, domain or
  enumeration that was searched.

### BUG-487 - OPEN (floors have one home; the first guarded production write is still owed)
- **DONE**: `config/evidence_floors.yaml` is the ONE home for the four evidence journals + the blob store
  (C12/C21). The `floors:` block was REMOVED from config/handoffs.yaml, and verify_handoffs/measure/reconcile all
  read the one file. reconcile now checks, per store: presence, a floor of >0 or a declared `vacuous` reason, a
  non-zero floor is met, and the declared `enforced_by` rail exists. A store BELOW its floor is DRIFT, an ABSENT
  store is DRIFT unless its emptiness is declared.
- **DECLARED VACUITY**: `governance/MUTATION_JOURNAL.jsonl` does not exist, because ZERO guarded production writes
  have ever happened. That is now PRINTED, not silent: `floor governance/MUTATION_JOURNAL.jsonl: ABSENT (declared
  vacuous - ZERO guarded production writes have ever happened, so 0 is the TRUE count)`. The guard itself is
  exercised by write_guard --selftest (4 refusal invariants) in `just health`.
- **STILL OWED**: route a real production writer through write_guard so the journal carries its first receipt
  (owner-gated: pipeline/** and the human_authored workbook), and the I1 bypass audit
  (`write_guard --audit`: join each `writer_of_record` to whether that script actually uses the guard).

### BUG-490 - OPEN (a rail that checks a journal before publishing its own record reports itself as unpublished)
- **FOUND BY THIS SESSION'S OWN CHANGE** (first run): reconcile's domain join read governance/METRICS.jsonl
  before reconcile emitted its own envelope, so it reported `metric reconcile_objects_agreeing declared but NEVER
  published` about ITSELF - a self-ordering artifact that self-heals on the next run and would have been read by
  the next session as a real finding. Same family as the BUG-489 finding: the report described the ORDER of the
  run, not the state of the world.
- **owed**: declare the publication order each resolver metric depends on (or exempt this-rail-this-run
  explicitly), so a bootstrapping rail cannot report itself as missing.

### NOT STARTED THIS SESSION (declared, not silently dropped)
- Step 3: `write_guard --audit` (I1 bypass join) - see BUG-487 above.
- Step 4: criteria-board triage (BUG-484: 3 DRIFT - P1.gate_artifact_fresh stale fingerprint; AX4/AX5 are the
  BUG-326 knowledge-layer repair and are owner-gated).
- Step 5: ontology hygiene (the non-id-shaped citation at config/eval_integrity.yaml:decision, and the duplicate
  `## D-356` heading in DECISION-LOG.md - both need append-only erratum handling).
- Step 6: flag hygiene (2 unregistered flags on config/depth_domain_contract.yaml).

## SESSION 20260925E — a control may not write into the ruler it calibrates, and the checker now DERIVES the rail order

### BUG-491 - FOUND (critical) and FIXED: the meter was writing into its own ruler
- **MEASURED BEFORE**: `governance/HANDOFFS.jsonl` held 20 records and **14 of them were `origin: selftest`** -
  `scripts/lib/handoff.py --selftest` appended 2 fixture receipts to the PRODUCTION journal on EVERY
  `just health` run (17:55-18:27 on 2026-09-25). The store's floor was therefore counted over a contaminated
  population that grows 2 records per run, so `min_records: 6` **could not fail**: the BUG-487 guard landed last
  session was green by construction - the exact class it was built to prevent. Same family as BUG-489/BUG-490:
  the artifact described the RUN, not the world.
- **FIX (root cause, one home)**: a CONTROL may not write into the RULER it calibrates. `handoff.py` now runs
  `--selftest` in a SANDBOX (journal + blob resolve inside a temp dir) and asserts THREE things, each able to
  fail: the digest moves on a rewrite; the receipts landed in the sandbox (the redirect is PROVEN, not assumed);
  the production journal is BYTE-IDENTICAL afterwards. `config/evidence_floors.yaml` now declares WHAT counts:
  `exclude_origins: [selftest]` plus a SHRINK-ONLY `contaminant_ceiling: {origin: selftest, max: 14}`. The 14
  historical records are GRANDFATHERED, never deleted (R-D410: a removed record cannot be audited). One function
  (`measure.contaminant_drift`) is shared by verify_handoffs and measure.
- **MEASURED AFTER**: `ok handoff selftest: ... SANDBOXED in a temp dir (2 receipt(s) + 1 blob), production
  journal byte-identical (009b1a1e2c0dbc9d)`; the journal measured 20 -> 20 lines across the control run;
  `ok floors: 6 receipt(s) >= 6, 4 blob(s) >= 3 (14 control fixture record(s) EXCLUDED from the count: 14
  selftest record(s) <= ceiling 14)`.
- **OWED (owner)**: retire the 14 grandfathered records into governance/evidence/ (append-only move) and lower
  the ceiling to 0. The ceiling is shrink-only: only the owner may shrink it.

### Same class, second store - FIXED: a floor over an append-per-run log is a RUN counter
- **MEASURED**: `governance/METRICS.jsonl` held 25 records over only **4 distinct metric names** (19 of them are
  2 metrics re-emitted per run), so `min_records: 12` was satisfiable by re-running health 12 times, not by
  measuring anything. **FIX**: `min_distinct_names: 4` in the same one home; `measure --gaps` enforces BOTH and
  prints both. A floor must be over a POPULATION, not over the number of times a rail ran.

### BUG-490 - CLOSED: the checker derives the rail order from the recipe itself
- **FIX**: `measure.health_chain()` parses `just health` and returns the invoked rails IN ORDER; `envelope_gaps`
  DRIFTs when a declared resolver rail sits AFTER the checker (then "has not run yet" reads as "never
  published"), and separates "never published" from "the chain never invokes that rail". `measure --gaps` moved
  to the LAST rail of the chain.
- **MEASURED**: `checker at chain position 19, declared resolver rails [scripts/reconcile.py@18,
  scripts/verify_handoffs.py@17] - every one precedes it`.

### BUG-487 - still OPEN (half done): the first guarded production write is still owed
Floors have one home, WHAT counts is now declared, and MUTATION_JOURNAL's vacuity is printed rather than hidden.
Still owed: route a real production writer through scripts/lib/write_guard.py so the journal carries its first
receipt, and the I1 bypass join.

### NOT STARTED THIS SESSION (declared, not silently dropped) - the remaining three of the six steps
- Step 4: `write_guard --audit` (I1 bypass join: AST-scan every declared `writer_of_record` for a guard call
  site; today NO writer in the repo imports the guard - 0 of 6 declared writers are guarded).
- Step 5: first guarded production write (candidate: governance/RECONCILIATION.json, written by
  scripts/reconcile.py, derived_regenerable + OWNED_ANY).
- Step 6: hygiene - register config/depth_domain_contract.yaml::load_bearing.enabled AND ::pct_scalar.enabled
  (audit_flag_consumers: 45 verified, 0 RED, 2 unregistered); make
  config/eval_integrity.yaml#label_axes.known_collisions[0].decision id-shaped (closes reconcile's owner_owed
  `decision_registry_wellformed`, which still reads `D-271a` inside a ruling paragraph).
- BUG-484 criteria triage: P1.gate_artifact_fresh (stale fingerprint 4c9e93b294251cc5 vs current
  ae479dd05c4fe70c); AX4/AX5 remain the owner-gated BUG-326 knowledge-layer repair.

## SESSION 20260925F — one definition of what counts, and the ownership invariant is finally AUDITED

### RECEIPT - a floor is FOUR facts, not one number (BUG-491 fixed end to end)
- **MEASURED, before**: `scripts/reconcile.py` printed `ok floor governance/HANDOFFS.jsonl: 20 >= 6` while
  `scripts/verify_handoffs.py` printed `6 receipt(s) >= 6` for the SAME store, because reconcile counted RAW
  records and verify_handoffs excluded control fixtures. One fact, two homes (C12/C21): a reader could not tell
  which number the floor was over.
- **FIX**: `lib/measure.counted_records()/distinct_floor()/_store_count()/floor_check()` is now THE one
  definition of what counts, and every rail that reports a floor delegates to it. reconcile's floors loop is a
  pure delegation. A second latent instance of the same class was found in `measure.main()` itself, which
  re-implemented the METRICS count over RAW records - it agreed with reconcile ONLY because METRICS declares no
  `exclude_origins`. It would have diverged silently the first time a control fixture wrote into that journal,
  so it now delegates to `floor_check` too.
- **FIX (population)**: `min_distinct_names` -> `min_distinct_field` + `min_distinct_values`
  (`config/evidence_floors.yaml` `schema_version: "2.0"`). MEASURED: METRICS.jsonl held **40 records over only 4
  distinct metric names** - a record floor over an append-per-run log is a RUN counter, satisfied by re-running
  the rail, not by measuring anything. HANDOFFS declares `min_distinct_field: path` (6 counted receipts cover 6
  distinct DECLARED paths); INSTRUMENT_CONTROLS declares `instrument`; MUTATION_JOURNAL declares `path`.
  The rename is deliberate: a reader that silently ignores an unknown key is how a floor stops being a floor, so
  a schema change gets a version that makes the incompatibility VISIBLE (R14).

### The guard's own rail was BROKEN - repaired first, because it IS the gate
- `scripts/lib/write_guard.py` did not compile (`IndentationError` in `selftest()`): the edit that wrapped the
  three EXPECTED refusals in `contextlib.redirect_stdout` left an orphaned `write_rows(...)` call. Because this
  file is a `just health` rail and `scripts/reconcile.py` imports it at write time, HEALTH WAS RED and the first
  mutation receipt was never written. Repaired: 3 blocks, `--selftest` 6/6 invariants, and the expected refusals
  are now output-CAPTURED - `just health` no longer shows FAIL-looking `!!` lines that are not failures.

### RECEIPT - the I1/D-401 exit gate is BUILT and the FIRST GUARDED PRODUCTION WRITE LANDED (BUG-487 half retired)
- `write_guard --audit` is an AST scan, not a grep: a mention or an import is not a CALL, because an import with
  no call site is a script that DECLARES the discipline and does not apply it - the exact state in which BUG-478
  blanked 148 owner cells. It joins the declared `writer_of_record` set to reality and emits
  `guard_writers_guarded` with its population and denominator (D-404).
- `write_document()` writes a WHOLE-DOCUMENT artifact and REFUSES any `owned_keys` other than `OWNED_ANY`: a
  document has no cells to arbitrate, so "the guard ran" must never be readable as "every cell was protected".
  `backup=False` for a DERIVED artifact (its pre-image is regenerable); the receipt still records the pre-image.
- **LANDED**: `governance/RECONCILIATION.json` is now written by `scripts/reconcile.py` THROUGH the guard, and
  `governance/MUTATION_JOURNAL.jsonl` carries its FIRST receipt (`9c514785c3be98f8 -> 071e1b0aa9dc0699`,
  kind=document, writer scripts/reconcile.py). The vacuity declaration was RETIRED in the same step that
  disproved it.
- **GUARDRAIL PROVEN, not asserted**: between the write and the retirement, `floor_check` reported
  `governance/MUTATION_JOURNAL.jsonl declares vacuous: true but holds 1 record(s)` and
  `reconcile --check` returned **rc=1**. The check fired, and the tri-state is honest (1 drift / 2 owed / 0 ok);
  a stale vacuity is DRIFT, not a comment going quietly out of date.
- Ceiling: `config/artifact_ownership.yaml#guard_coverage.max_unguarded: 6`, `direction: shrink_only` - MEASURED
  1/7 declared script writer(s) call the guard (scripts/reconcile.py is the first). Routing a writer through the
  guard LOWERS this number; RAISING it requires a declared decision, not an edit (same direction as
  `config/register_divergence.yaml#declared_max`).

### RECEIPT - BUG-491c NEW, found by the audit on its FIRST run: a phantom `writer_of_record`
- **MEASURED**: `config/artifact_ownership.yaml` declared `writer_of_record: scripts/build_closed_menu.py` for
  `config/closed_menu_v5.json`. That script exists NOWHERE - not on disk, not in `archive/`, and it is named ONLY
  in this declaration. A writer nobody can inspect enforces nothing, and it made the ownership registry
  unfalsifiable for that artifact. The real writer is `scripts/render_closed_menu.py` (crash-safe write of the
  JSON + its `.sha256`, then a post-write integrity check against the menu_hash pin).
- **FIX**: the DECLARATION was corrected to match reality (never the reverse). The exemption's rationale was ALSO
  wrong - it claimed "a new FILE, content-addressed by construction" while the code regenerates the document IN
  PLACE - so the rationale now describes the mechanism its code actually implements, and names the owed step that
  RETIRES the debt (`write_document(OWNED_ANY)` is the right home for a whole-document regenerator).
- **CLASS LESSON**: a declaration is a claim about reality and must be FALSIFIABLE. An ownership registry that
  cannot be checked against a filesystem is prose. The audit found this within seconds of first running.

### VERIFIED THIS SESSION
- `just health` **RC 0** (aggregate rail green; the floors, the guard selftest and the new `--audit` rail all in
  the chain, `--audit` tolerated at rc 2 as declared debt - BUG-457).
- `just criteria`: 28 criteria | OK 23 | DRIFT 3 | WARN 2 - IDENTICAL before and after, so no cascade.

### STILL OPEN (declared, not silently dropped)
- **P1.gate_artifact_fresh is STILL DRIFT** (`artifact 4c9e93b294251cc5 vs current ae479dd05c4fe70c`):
  `config/bench_preflight.yaml` was edited (sha `c2946f279e548409`, commit 986fbc4, 2026-09-19) AFTER the stored
  artifact was generated (2026-09-17), and `fingerprint()` hashes the config BYTES - so ONLY a real gate re-run
  clears it. A live `tools/bench_preflight.py` re-stamp was started this session and is still running.
- AX4.runtime_matches_gold_4axis + AX5.form_axis_traceable remain the owner-gated BUG-326 knowledge-layer repair.
- Hygiene: 2 unregistered flags (`config/depth_domain_contract.yaml::load_bearing.enabled`, `::pct_scalar.enabled`)
  and ONE non-id-shaped citation (`config/eval_integrity.yaml#label_axes.known_collisions[0].decision` is a RULING
  PARAGRAPH wearing a citation key) -> reconcile's `decision_registry_wellformed` owner_owed.
- The guard's DECLARED APPEND mode is still owed: the refusal of row ADDITIONS is what keeps
  `ingest_panel_column.py`, `f11_anchor_review.py` and `recompute_decision_summary.py` from being routed, so
  `max_unguarded` cannot yet fall below 6.
- **NO COMMIT — owner ack owed.**

## SESSION 20260925G - the guard gains a DECLARED APPEND mode, and two exemptions stop matching their code

### RECEIPT - write_guard APPEND mode landed (10/10 invariants, the enabler for 3 declared debts)
scripts/lib/write_guard.py 472 -> 620 lines, 13 asserted anchors, pre-image backed up to
backups/write_guard.PRE_APPEND_20260925F.py. New: plan_append() (the declared invariant: the pre-image must
survive UNCHANGED as a PREFIX; an added row may only fill the caller's own columns; no id reuse; no truncation),
append_rows() (mode append, receipt carries added + schema_version bumped to 1.1 per R14 so a pre-append receipt
is VISIBLE rather than defaulted), read_rows(encoding=...) and a declared lineterminator, plus ONE home each for
the backup rule (_backup) and the CSV write (_write_csv_atomic). append_rows added to GUARD_CALLS so an import
without a call still reads as declared-and-unenforced. Verified: py_compile OK; --selftest 10 invariants rc=0
(5 expected refusals, all output-captured); --audit rc=2 unchanged (1/7 guarded, ceiling 6); reconcile --check
rc=0 (11 objects); just health rc=0; pipeline/ diff 0 lines.

### RECEIPT - BUG-491c class, instance 2: the ingest exemption does not describe the ingest
MEASURED, not assumed: config/artifact_ownership.yaml#governance/anchor_adjudication_workbook_20260924.csv
declares the writer unguardable because "the guard's merge mode REFUSES row additions by design - an ingestor's
job IS to add rows". scripts/ingest_panel_column.py PRESERVES the row count (new_rows is built by mapping over
the pre-image; only one rater column changes) - so write_rows(mode='merge', owned_keys={col}) is exactly
applicable, and the exemption was protecting a mechanism the code does not have. This is the same defect found in
the closed-menu entry (a rationale that does not match its code), now measured a second time - a CLASS, not an
instance. The declared ceiling of 6 therefore overstated the debt.

### RECEIPT - hazard measured before routing (so the routing cannot silently reformat an owner artifact)
governance/anchor_adjudication_workbook_20260924.csv: sha16 1e5532193e2fe163, 99232 bytes, 148 rows, 25 cols,
LF-only (0 CRLF), no BOM, decodes as utf-8(-sig). csv's default lineterminator is CRLF: the OLD write_rows would
have re-terminated every line of a human_authored file while reporting a one-cell edit - now impossible
(lineterminator is declared, default "\n"). Filled owner cells measured: domains_final 147, depth_final 148,
owner_date 148, owner_note 0.

### RECEIPT - the answer-space pin has no pin (NEW, high blast radius, NOT yet fixed)
scripts/render_closed_menu.py regenerates config/closed_menu_v5.json IN PLACE and its only check recomputes the
hash of the file it just wrote and compares it to the hash it just computed - a SELF-consistency check, not a pin
check. A taxonomy/content-type change therefore re-freezes the answer space with a new menu_hash and NO gate and
no refusal (D-277 says labels stamped with an old menu_hash must be re-derived). Also the entry is declared
mutability: immutable while its mechanism is in-place regeneration - declaration and mechanism disagree.
This is the next owner-visible hardening step, not a hypothesis.

### RECEIPT - the re-stamp run is a ZOMBIE, and no rail can see it (NEW, NOT yet fixed)
PID 76746 (tools/bench_preflight.py, launched 20:37) is ALIVE at 20:57 with 0.58s of CPU time and a 247-byte
log: it is blocked, not working, so P1.gate_artifact_fresh stays DRIFT and the rail reports a stale gate while
the remediation looks "in flight". Nothing in just health can distinguish "not yet finished" from "hung".

### VERIFIED THIS SESSION
write_guard --selftest 10/10 rc=0 | write_guard --audit rc=2 (declared debt, NOT fatal) | reconcile --check rc=0,
11 declared objects agree | just health rc=0 (270 lines) | pipeline/ diff 0 | decisions.yaml in sync (772,
stamp aa69ae412a641374) | 75 dirty files | write_guard pre-image backup on disk (22909 bytes).

### STILL OPEN (declared, not silently dropped)
- Router steps the append mode unblocks, in order: scripts/ingest_panel_column.py (merge, owned_keys={col},
  proof on a temp copy), scripts/f11_anchor_review.py (write_document/OWNED_ANY - it must keep its own
  refuse-if-exists rule), scripts/render_closed_menu.py (write_document/OWNED_ANY + a REAL pin refusal), then
  lower guard_coverage.max_unguarded 6 -> 3 and rewrite both mismatched exemptions.
- P1.gate_artifact_fresh: kill and root-cause the hung re-stamp (no deadline/heartbeat in the run).
- Step-6 hygiene: 2 unregistered depth_domain_contract flags; the non-id-shaped
  config/eval_integrity.yaml#label_axes.known_collisions[0].decision.
- git is BLIND to the apparatus: scripts/lib/, scripts/reconcile.py, scripts/verify_handoffs.py and the config
  declarations are untracked - a git clean -fd deletes four health rails.
- **NO COMMIT - owner ack owed.**

## SESSION 20260925H - the guard stops being a promise: 3 writers routed, the owner workbook becomes create-only, and two declarations stop describing a mechanism they do not have

### RECEIPT - three declared writers now CALL the guard (D-401/I1), so the ceiling moves 6 -> 4
MEASURED BEFORE: 1 of 7 declared script writers called scripts/lib/write_guard.py (scripts/reconcile.py).
- scripts/ingest_panel_column.py -> write_guard.write_rows(mode="merge", owned_keys={the one target column})
- scripts/f11_anchor_review.py     -> write_guard.append_rows (keeps its own refuse-if-exists rule as gate A)
- scripts/recompute_decision_summary.py -> write_guard.write_document(OWNED_ANY) for the registry write
MEASURED AFTER: 3 of 7 guarded; 4 unguarded (stage4_merge, stage5_verify, render_closed_menu, recompute*).
config/artifact_ownership.yaml#guard_coverage.max_unguarded lowered 6 -> 4 BY EDIT, which is the permitted
direction (raising it would be a decision). *recompute imports write_document and is therefore counted as
guarded only when the AST scan sees the call - it does, see the audit line.

### RECEIPT - the ingest routing closed a LATENT whole-file edit, measured before it fired
The script's local rule carried csv's DEFAULT lineterminator (CRLF). The workbook is LF-only (148 data rows,
149 LF, 0 CRLF, sha16 1e5532193e2fe163), so one --apply would have re-terminated every line while reporting a
one-cell edit - the BUG-478 class arriving through a library default. Routing it through the guard closed it
structurally, and a NEW helper (write_encoding_for) picks the ONE declared encoding that re-encodes to the
file's EXACT bytes, so a re-run can no longer add a BOM either. Verified on a TEMP COPY (P1): touched == only
the target column, all owner cells byte-identical, LF-only preserved, and a foreign-cell edit REFUSED (P2) with
nothing written (P3: the real workbook sha16 is unchanged).

### RECEIPT - BUG-478 ROOT: the machine may now create the owner's workbook ONCE and never rewrite it
MEASURED: scripts/cross_examine_anchor_axes.py::write_outputs opened governance/anchor_adjudication_
workbook_20260924.csv with mode "w", rebuilt it from the dispute set and blanked WORKBOOK_OWNER_COLS - one
documented command away from destroying 148 rows of typed adjudication - while config/artifact_ownership.yaml
did not merely omit that writer, it named it under machine_writers_forbidden. The declaration was right and the
code was wrong. Repair: the workbook write is now CREATE-ONLY and DECLARED (config/anchor_cross_exam.yaml#
outputs.workbook_create_only, read with a fail-closed refusal when absent rather than an undeclared default),
the creation itself goes through write_guard.append_rows, and an existing workbook is SKIPPED - proven by
calling _write_owner_workbook on the REAL workbook and asserting the sha16 is unchanged (P4).

### RECEIPT - BUG-491c is a CLASS: 2 more instances fixed in the declarations themselves
An exemption is a claim about reality and must be FALSIFIABLE. Fixed today because the claim no longer matched
the code: (1) the ingest exemption ("the guard's merge mode REFUSES row additions by design - an ingestor's job
IS to add rows") - the ingestor PRESERVES the row count, so the exemption protected a mechanism the code does
not have; (2) the f11 exemption (same claim, same measurement). Also recorded: (3) the closed-menu exemption
calls its post-write check "an integrity check against the menu_hash pin" while it is a comparison of the hash
it just computed with the hash of the bytes it just wrote - there is NO pin (D-277 exposure, owner decision
required: refuse-if-hash-changes vs a versioned config/closed_menu_v6.json).

### RECEIPT - BUG-342 RE-OCCURRENCE: the AX4/AX5 owner gate was already closed as NOT APPLICABLE
governance/buglog.md line 2761 records that BUG-326's repair targets DO NOT REPRODUCE and that the gate list
was corrected on 2026-09-23, yet the handoff carried "AX4/AX5 remain the owner-gated BUG-326 knowledge-layer
repair" again at line 4814 - the same stale-gate class (quote the generator, never carry a stale count). The
correct framing is: AX4/AX5 are DRIFT to be re-derived from the artifacts, NOT a repair awaiting a ruling.
Not re-triaged this session (no drift report re-run); recorded so it cannot be carried as a gate again.

### VERIFIED THIS SESSION
- py_compile OK on all four patched scripts; write_guard --selftest 10/10 invariants.
- P1..P4 as above. The real owner workbook and config/decisions.yaml were NOT written this session.
- Backups (byte-exact pre-images): backups/PRE_ROUTE_20260925H/.

### STILL OPEN (declared, not silently dropped)
- recompute_decision_summary still has one unguarded home for the registry write; render_closed_menu still has
  no pin (owner decision); the pre-stamp PID 76746 is still a zombie with no heartbeat.
- **NO COMMIT - owner ack owed.**


## SESSION 20260925I — owner gates accepted: recommendations implemented (part 1)

**BLOCKING DEFECT REPAIRED.** config/artifact_ownership.yaml had FIVE joined keys (an exemption-removal regex
swallowed the separating newline), which made every rail that reads the ownership declaration RED. Repaired by
restoring the newlines; the file parses, 8 artifacts declared. `just health` is GREEN (rc=0).

**BUG-492 (NEW, and it was inside the rail).** `guard_call_sites` in scripts/lib/write_guard.py recognised only
`from lib.write_guard import x` / `import x.write_guard`, so `from lib import write_guard` - the repo's OWN idiom -
was invisible: the audit reported DRIFT for scripts/ingest_panel_column.py and scripts/f11_anchor_review.py, which
do CALL the guard. A false DRIFT trains the owner to ignore the rail exactly as a false OK does. Two further
repairs in the same file: the `root == "write_guard"` clause (a call with NO import was accepted, making the rail's
own OK unauditable) is REMOVED; and `_require_id_column` now REFUSES a write whose fieldnames lack the declared id
column - the defect that hid `id_column: row` on an artifact whose header is `item_id,...`.

**BUG-492 instance (declaration vs mechanism).** config/artifact_ownership.yaml declared `id_column: row` for
governance/F11_ANCHOR_REVIEW_20260923.csv, whose header starts `item_id` and carries no `row` column at all: every
row read as unaddressable, so the append invariant's id-reuse clause was VACUOUS - it could refuse nothing. Fixed
to item_id; the guard now refuses a write whose fieldnames lack the declared id column, so it cannot drift again.

**MEASURED (green audit, this time):** `write_guard.py --audit` -> 4/7 declared script writers call the guard
(reconcile, recompute_decision_summary, ingest_panel_column, f11_anchor_review); 3 unguarded by DECLARED exemption
(pipeline/stage4_merge.py BUG-376, pipeline/stage5_verify.py BUG-475, scripts/render_closed_menu.py owner decision);
rc=2 (owner-owed, loud, not fatal). guard_coverage.max_unguarded lowered 4 -> 3 as the receipt of that run. The
SESSION 20260925H claim ("3 of 7 guarded, 4 unguarded") was NOT measured when it was written (the rails were RED);
it is superseded by this measured line. BUG-478 is closed with the P4 evidence (existing owner workbook SKIPPED).

**BUG-493 (NEW).** governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv is declared immutable + `seal: true`
in config/handoffs.yaml, and its bytes CHANGED (bc1cc956 -> 526991cb, mtime 2026-09-25 21:08). MEASURED root
cause, not a guess: the 16 declared columns are a byte-exact PREFIX of every one of the 151 rows and
check_human_instruments.py reports all 7 locked instruments byte-identical, so NO owner cell moved. The delta is 3
UNNAMED trailing columns, one carrying the stray text 'rese' at row 43 / item R043 col 18: the signature of a
spreadsheet save on a sheet the owner is entitled to widen. THE CLASS-LEVEL DEFECT: two declarations held two
incompatible rules for one fact - the instrument LOCK is column-scoped ("new columns allowed; removed or rewritten
columns FAIL") while the handoff LEDGER asserted WHOLE-FILE immutability for the same file, so the owner's own
instrument could be edited into a permanent RED with no legal path back except human surgery. REPAIR (no evidence
moved, R-D410): rev 3 declared at 526991cb in config/human_instrument_locks.yaml + config/anchor4_interim_state.json
with rev 1 and rev 2 kept as SUPERSEDED; rev 2 given its own revision locator (git:65a13c3c) so the digests the
receipt quotes still RESOLVE as bytes instead of becoming orphan digests; the live bytes sealed through
`handoff.seal()`; a fresh receipt taken (origin=backfill) for the changed path. Result: hash_claims 13/13 resolved,
cross_declaration 11/11, revisions re-derived, verify_handoffs rc=0. OWNER-GATED: if the 21:08 save was NOT yours,
restore rev 2 from 65a13c3c.

**D-2637 MINTED (owner gate 1 accepted).** "A resolver declares and publishes its resolution domain, and a finding
may not name an artifact defective without naming what was searched." The rule existed and worked; the IDENTIFIER
was wrong: config/resolution_domains.yaml stamped `decided: D-405` while D-405 is a DIFFERENT rule (the
declaration-to-reality join: config/reconciliation.yaml, reconcile.py). One id, two subjects, invisible because a
stamp is a bare id. The file now stamps D-2637; D-405's record is NOT edited (records are append-only) and D-2637
names the separation. Registry in sync: 773 decisions, stamp d1e12eca8288d722. NAME-SPACE RULE recorded: one id,
one subject.

**STILL OPEN (do not read this session as closed):**
- config/evidence_floors.yaml does NOT yet declare the SEALED SET: the code path IS in place in
  scripts/lib/measure.py (an unsealed `origin: selftest` record is DRIFT; a sealed digest that has VANISHED is
  DRIFT; max_records 14 shrink-only), but the YAML edit did not match the block and did NOT apply. Until it does,
  the count ceiling `max: 14` stands and the allowance is still grandfathered. The 14 records are NOT moved.
- The answer-space pin (render_closed_menu.py) is UNCHANGED: its only check recomputes the hash of the bytes it
  just wrote and compares it to the hash it just computed, while the ownership entry declares `mutability:
  immutable`. Owner decision accepted: I2 VERSIONING (a new config/closed_menu_v6.json, never an in-place
  re-freeze) - NOT implemented, and it must not be half-done: 10 config files reference closed_menu_v5, so the
  version-on-change mechanism lands WITH the consumer-repoint rule.
- AIX4/AX5 are NOT an owner gate (BUG-342 re-occurrence): re-frame as DRIFT to be re-derived on `just criteria`.
- The zombie re-stamp (PID 76746) is gone from the process table; P1.gate_artifact_fresh needs the
  deadline/heartbeat distinction before that WARN can be read as anything.

**NO COMMIT — owner ack owed.** Files touched this session: config/artifact_ownership.yaml, config/anchor_cross_exam.yaml
(prior), scripts/lib/write_guard.py, scripts/lib/measure.py, config/human_instrument_locks.yaml,
config/anchor4_interim_state.json, config/handoffs.yaml, config/decisions.yaml, config/resolution_domains.yaml,
governance/HANDOFFS.jsonl, governance/handoffs/blobs/, and this file. The human_authored workbook was NOT touched
(sha16 1e5532193e2fe163).

## SESSION 20260925J — owner gates: implementation part 2 (sealed set + answer-space pin, audited)

**SEALED SET APPLIED (owner gate accepted).** config/evidence_floors.yaml schema_version 2.0 -> 2.1 (R14) and the
count ceiling for governance/HANDOFFS.jsonl is replaced by a SEALED SET: sealed_set{digest_field, grandfathered_sha16:
['0682c5f2076f099c','e5bc54d3288ee8af']} + max_records 14 (shrink-only). The digests were DERIVED from the journal by
the patch script and refused if not exactly 2 x 7 over 14 records. Nothing was moved or deleted (R-D410).
KNOWN-ANSWER CONTROLS (6, in-memory, /tmp/ctl_s1*.py): A sound=0 drift; B an unsealed selftest record = DRIFT
(NOT in the sealed set) plus a second DRIFT on max_records; C a vanished sealed digest = DRIFT (R-D410); D max AND
sealed_set together = DRIFT (two homes for one bound); E legacy count path still enforced (max 13 over 14 = DRIFT);
F neither max nor sealed = DRIFT. The allowance is now falsifiable in BOTH directions, which a count never was.
**BUG-494 (NEW, inside the rail).** scripts/menu_axis_hashes.py treated --check as a MODE FLAG ON A WRITER: running
`menu_axis_hashes.py --check` WRROTE config/menu_axis_hashes.yaml (printed "wrote ..." and rc=0). A check that
repairs cannot report, and the consequence is not cosmetic: a STALE per-axis file makes
scripts/validate_depth_domain_contract.py --gate-if-active compare the live render against OLD declared hashes - a
blindspot with a green light. FIXED: --check is read-only (reports STALE/ABSENT, rc=1); the writing path is
separate. Verified: --check rc=0 with no mtime change.
**BUG-495 (NEW).** That same script was an UNDECLARED writer of a config artifact - write_guard --audit computes its
coverage over DECLARED writers only, so an undeclared writer of the answer-space pin was invisible to the rail that
exists to find exactly this - and it wrote the pin with a bare Path.write_text (no fsync, no os.replace): a crash
mid-write could truncate the pin itself (C6). FIXED: declared in config/artifact_ownership.yaml
(mutability: derived_regenerable, writer_of_record) and ROUTED through write_guard.write_document(OWNED_ANY,
journal=True). Measured effect: audit 4/7 -> 5/8 declared writers guarded (f11_anchor_review, ingest_panel_column,
menu_axis_hashes, recompute_decision_summary, reconcile); unguarded stays 3 (stage4_merge BUG-376, stage5_verify
BUG-475, render_closed_menu declared debt), so the shrink-only ceiling 3 is NOT raised (rc=2, owner-owed, not fatal).
**BUG-496 (NEW; owner gate 5 closed, not waived).** scripts/render_closed_menu.py wrote config/closed_menu_v5.json
unconditionally, so a taxonomy edit re-froze the answer space in place with a NEW menu_hash and NO refusal, while
config/artifact_ownership.yaml declared the file immutable - the declaration and the mechanism disagreed (BUG-491c,
instance 4). ROOT: there was no pin, only self-consistency (the script recomputed the hash of the bytes it had just
written and compared it to the hash it had just computed). FIXED: the script now REFUSES to overwrite an existing
revision whose menu_hash differs from the live render (verified RENDER_RC=1, v5 byte-untouched) and can mint a NEW
revision (--mint-version N, I2 versioning) with the consumer-repoint obligation PRINTED. The ownership entry's
"FIX REQUIRES AN OWNER DECISION" text is superseded in place by the D-371 ruling (recorded, not deleted).
**GATE 5 WAS ALREADY IMPLEMENTED - AND MY PRIOR FINDING WAS INCOMPLETE.** D-371 (RATIFIED 2026-09-25) rules the
composite pin HISTORICAL and the ANSWER SPACE the pin; the apparatus exists and is green: config/menu_axis_groups.yaml
(membership, one home) + config/menu_axis_hashes.yaml (answer_space_hash 8436d9c985c0efdf over [domains, abstention])
+ scripts/menu_axis_hashes.py (generator) + scripts/validate_depth_domain_contract.py --gate-if-active (wired in
just health, line 15). MEASURED now: composite 73597ee2 (frozen) vs d2fc500c (live) = DEFINITION_DRIFT in
[disciplines] ONLY, caused by one field: disciplines["behavioral economics"].definition was reworded
("deviations from rational choice" -> "from the rational or standard model"); the answer-space axes are byte-identical.
A v6 was deliberately NOT minted: D-371 already pinned the invariant, and minting a second home for one fact is the
anti-pattern this session kept finding. LESSON (BUG-488/489 class, applied to myself): my previous finding named
render_closed_menu.py defective without naming what had been searched - the pin lives in a DIFFERENT home, and D-371
had already measured it. A finding must name its resolution domain.
**BUG-497 (NEW, DATA-SIDE, UNFIXED).** MEASURED: knowledge pipeline/maxwell.db, table fbs, 7995 rows,
**fbs.menu_hash is EMPTY on every row** - the D-279 traceability stamp (the binding prerequisite for min_human_share /
F-44) is present as a column and populated by nothing. Consequence: no committed FB can be traced to the menu it was
classified against, so a D-277 "re-derive from source" run is the only route to traceability for the current corpus,
and any answer-space claim about the corpus is currently unfalsifiable. NOT fixed here: it is a pipeline write path
(owner-gated under pipeline/**) and needs either an owner-authorized backfill or a declared no-backfill decision.
**NO COMMIT - owner ack owed.** Files touched: config/evidence_floors.yaml (2.1 + sealed set),
scripts/lib/measure.py (sealed-set semantics, two-homes refusal, note de-duplication, SHRINK typo), scripts/menu_axis_hashes.py
(read-only --check, guard routing), scripts/render_closed_menu.py (refuse/mint), config/artifact_ownership.yaml (new
declaration + superseded wording), justfile (pin check wired into just health: rc=0).

## SESSION 20260925K - rail repair (citation resolution + flag registry) + 2 P0 INTEGRITY FINDINGS

**P0-A (BLOCKS THE AGGREGATE RAIL; Dropbox, not code). `.git/refs/heads/main` WAS RENAMED BY DROPBOX.**
MEASURED 21:44 HEAD resolved (`96b1e9c`); by 21:47 `git rev-parse HEAD` = "ambiguous argument 'HEAD'" and
`git status` claimed **1220 files ADDED** (a first-commit-of-everything view) where 3 minutes earlier it showed
29 A / 32 M. CAUSE: a second machine ("M1 max") touched the same Dropbox-synced .git, and Dropbox resolved the
conflict by RENAMING git's own ref: `.git/refs/heads/main (M1 max's conflicted copy 2026-09-25)` (same for
`.git/COMMIT_EDITMSG`). EVIDENCE THAT THE REPAIR WAS A RESTORATION, NOT A CHOICE: the conflicted ref contained
96b1e9c79c441edf71b551a2f3c52e06e31f6362 (a valid commit object, = the HEAD measured at 21:44) and its reflog
ended `715935d -> 96b1e9c commit (amend): ANCHOR-4 annex + rail-4 hardening`, byte-identical to `.git/logs/HEAD`.
ACTION: renamed the file back (ref + reflog), no bytes chosen or overwritten. VERIFIED: `git rev-parse --short HEAD`
= 96b1e9c, branch main, `git log` intact. **LESSON: staging/committing from that state would have produced a bogus
commit; the "no commit without owner ack" rule is what caught it.** BUG-400 class (Dropbox File Provider), now
proven to corrupt GIT METADATA, not just worktree files: a one-line `git status` cannot be trusted while a second
Dropbox client is writing.

**P0-B (16 FILES RENAMED OUT OF THE TREE; `just health` IS RED AT LINE 13).** The same mechanism renamed 16
TRACKED files to `X (M1 max's conflicted copy 2026-09-25)` and the ORIGINALS ARE GONE from the working tree
(measured: `orig_exists=False` for all 16). MEASURED vs HEAD: 2 SAME_AS_HEAD (`governance/SESSION-HANDOFF-2026-09-23.md`,
`scripts/check_session_plan.py`), 14 DIFFERS_FROM_BOTH (i.e. the other client's newer content). Consequence:
`just health` exits 1 at line 13 - `manifest missing: governance/ANCHOR4_MANIFEST_20260924.json`. RESOLUTION
DOMAIN (BUG-488/489): the "index" column was not measured - my `git show :<path>` invocation returned non-zero for
all 16, so treat the index comparison as UNVERIFIED; HEAD blobs and the conflict copies WERE hashed. The lost
originals are recoverable from .git objects (`git checkout -- <path>` restores HEAD bytes), but for the 14 that
differ that would DISCARD the other client's content - so NO restore attempted. OWNER DECISION: per file,
keep conflict copy / keep HEAD / merge. Also: no staging performed this session for the same reason (a later
`git commit -a` would DELETE 12 tracked files).

**BUG-498 (FIXED, rail defect: a documented resolution that did not exist).** `scripts/reconcile.py::_citation_base`
ran `.upper()` BEFORE `.rstrip("abc...")`, so the strip could NEVER match - the docstring ("'D274a' -> 'D274': a
sub-lettered id is a variant of its base decision") described a mechanism that did not exist, and a citation of the
BASE of a sub-lettered decision was reported DRIFT ("does not exist"). MEASURED: 32 letter-suffixed ids in the
registry, 0 base records, 0 live citations affected (inert - a latent trap). FIXED: `_citation_token` (normalise)
+ `_citation_base` (strip-then-normalise) + `_resolves_citation` (ONE definition of "a citation resolves", now used
by BOTH citation checks, C21). KNOWN-ANSWER CONTROLS: cited variant `D-271a` -> resolves ['D271A']; cited base
`D-271` -> resolves ['D271A','D271B','D271C']; INVENTED variant `D271z` -> MISSING (fail-closed); `D-999` ->
MISSING; prose value -> `_id_shaped` False (still owner_owed). BUG-491c class instance 5.

**BUG-497 REFINED (provenance; NOT a stage6 write bug - a HISTORICAL GAP).** `fbs.menu_hash` is empty on ALL
7,995 rows (PASS 5,023 / QUARANTINE 2,972). The write path EXISTS and is wired end to end:
`pipeline/stage4_merge.py:2256 "menu_hash": _current_menu_hash()` (R1/D-279 stamp on every classified FB) ->
`pipeline/stage6_commit.py:568 _safe_str(fb.get("menu_hash"))` -> `fbs.menu_hash` (schema at :93, migration :273).
MEASURED: the S4 artifact `knowledge pipeline/stage4_merge/checkpoint.jsonl` (2026-08-31, the corpus this DB was
committed from) carries NO menu_hash at all. VERDICT: the corpus PREDATES the stamp, so no backfill and no
re-derivation is required *by a code defect*; the choice is (a) declared pre-provenance boundary for the existing
7,995, or (b) targeted S4 re-derivation - and a BATCH RUN AFTER THE STAMP needs no fix to be traceable.

**QUARANTINE TRIAGE (2,972 = 37.2%).** By `s5_reason`: **neutral 2,277 (76.6%)**, no_evidence 556 (18.7%),
contra 115, vacuous 14, evidence_contaminated 9, mech_fail 1. By `verification_method`: deberta-nli 2,948,
mech_quality 15, evidence_contaminated 9. RULED-BY-DESIGN exclusion measured: none of the known design causes
explains the bulk (duplicate_of is NULL on every row; the D-271a homonym guard hits only 93 rows). `needs_human_review=1`
on 386. So the dominant cause is the S5 NLI returning NEUTRAL at threshold 0.1 - i.e. quarantine is governed by ONE
CALIBRATION KNOB, and 0.1 is a strictness, not a measured operating point. That makes an S5 threshold-vs-precision
curve (needs the human-adjudicated stratified sample) the single highest-value quality instrument.

**BUG-499 (NEW, OPEN). `status` IS A PURE FUNCTION OF `epistemic_status`.** MEASURED 1:1 both directions:
source-supported 4,284 -> PASS, corroborated 739 -> PASS (5,023 = DB PASS); speculative 2,181 -> QUARANTINE,
cross-source-unverified 791 -> QUARANTINE (2,972 = DB QUARANTINE). Two columns, one fact. D274a ruled "no label
column can determine status" and required a CI invariant; the only match for that text is inside
`config/decisions.yaml`, i.e. **no such invariant script exists** (resolution domain: `git grep "determine status"`).
Needs a ruling: either epistemic_status is the canonical record and `status` is a declared derived mirror (then the
invariant is about the WRITER, not the column), or one of them is a second home for one fact.

**STEP-6 HYGIENE CLOSED (implemented).** `config/flag_consumer_registry.yaml` +2 entries (C12: every flag one home):
`config/depth_domain_contract.yaml::load_bearing.enabled` (required false; consumer `scripts/check_depth_load_bearing.py`
+ `consumer_symbols: 'lb.get("enabled")'`; invoked as a rail at justfile:25; the note records the SEMANTICS - false =
PROHIBITIVE (a forbidden trace exits 1), true = REPORTING, so flipping it is a DE-FANGING of D-394, not a feature
switch) and `::pct_scalar.enabled` (required false, consumers [] + exempt_reason; decisions [] is deliberate - no
registry record names pct_scalar, so citing one would be a manufactured source). MEASURED AFTER: **47 verified,
0 RED, 0 unregistered** (was 45 / 0 / 2).

**CITATION STATE MOVED FORWARD, NOT CLOSED.** `config/eval_integrity.yaml#label_axes.known_collisions[0].decision`
is now id-shaped (`D-271a DECLARED HOMONYM ...`, prose preserved, id resolution verified against the registry).
The owner_owed row did NOT disappear - it CHANGED FORM: from "1 citation value(s) are NOT id-shaped" to "1 declared
homonym citation(s) are EXEMPT from id validation: ['config/menu_axis_hashes.yaml:decision']". FINDING: the
exemption branch of `decision_registry_wellformed` sits BEHIND the unval branch, so a declared exemption was
MASKED by the first failure - a rail that reports one debt at a time hides the next. The remaining owner_owed is
now a VISIBLE, shrink-only exemption (D-402): drop it and make that citation id-shaped, then the check reaches `ok`.

**GOV SYNC / NO COMMIT.** Buglog appended (this entry). Files touched: scripts/reconcile.py, config/eval_integrity.yaml,
config/flag_consumer_registry.yaml. NOT staged: the working tree carries 16 unresolved Dropbox conflict copies and
`just health` is RED because of them (line 13), so a commit now would be both unverifiable and destructive.

## SESSION 20260925L - P0-A/P0-B REPAIRED + RAIL 0 installed (sync integrity is now a check, not an assumption)

**BUG-400 ESCALATED (the File Provider renames GIT METADATA, not just worktree files); FIXED BY A RAIL.** P0-A
recurred TWICE on 2026-09-25: `.git/refs/heads/main` was renamed (HEAD unresolvable, `git status` offered a
1,220-file FIRST COMMIT - committing would have buried 382 commits under a bogus root), and later `.git/logs/HEAD`
was renamed away while `.git/logs/refs/heads/main` was ROLLED BACK to an older file, so `git reflog` served a
STALE branch reflog and reported HEAD@{0}=a1061cd while HEAD was 96b1e9c. `git fsck` named both: "bad ref for
.git/logs/HEAD (M1 max's conflicted copy 2026-09-25)". The decisive property: the corrupt readings were FILES, so
no rail could see the corruption by reading them - no rail looked at the repository as an object. Now
`scripts/check_repo_integrity.py` (config/repo_integrity.yaml, C12) is RAIL 0: it runs FIRST in `just health` and
FIRST in `.git/hooks/pre-commit`, and it asserts (1) HEAD resolves, (2) no conflict-marked name exists inside
.git, (3) .git/logs/HEAD exists and its last commit EQUALS HEAD, (4) no tracked path is missing while a conflict
copy for it exists.

**P0-B SCOPE WAS 3x MY LAST MEASUREMENT (43 conflict copies, not 16; 38 with the canonical path EMPTY).** For 38
files the conflict copy was the ONLY SURVIVING COPY - including the justfile (so `just health` could not start:
"error: No justfile found"), config/decisions.yaml, DECISION-LOG.md, governance/buglog.md, config/eval_integrity.yaml
and 6 scripts/. Bytes were FROZEN FIRST to an out-of-sync vault with a sha256 manifest (2.3 MB, 43 rows), then
repaired by a session-scoped executor whose every precondition (P1 sha256 in the manifest, P2 the bytes on disk
still hash to it, P3 RESTORE only into an EMPTY canonical or a RE-VERIFIED byte-prefix superset, P4 vault never
touches a canonical) fails closed: 41 moves, 0 bytes lost, 0 content chosen. R5 review by gemma-4-E4B-it-MLX-4bit
found a REAL defect before the first apply - `shutil.move` silently degrades to copy+delete ACROSS FILESYSTEMS,
so the "same inode" claim was a BUG-498-class claim the code could not keep; replaced by `os.replace` behind a
same-`st_dev` precondition. The executor also refused to overwrite the one legitimate overwrite (the reflog
superset) until the bytes about to be lost were copied to a preimage - so "nothing is lost" is now an ACT, not an
argument. Receipt: vault APPLIED_MOVES.json + preimages/.

**THE RAIL CAUGHT ITS OWN FIRST REAL FINDING.** `just health` went from "error: No justfile found" to the LAST
rail, and at `build_archive_index --check` it reported the archive index STALE. Root cause was NOT the restore: the
vaulted `archive/index (cc).yaml` differed from the canonical in exactly one line (`generated:` timestamp), i.e. the
"divergent" duplicate carried no content. That is the rail doing its job on its first run - a stale derived artifact
named itself instead of a human noticing later. Regenerated via the sanctioned builder.

**VERIFIED AFTER.** HEAD 96b1e9c resolves; `git fsck` rc=0 with ZERO errors (was 4 bad-ref errors); `git reflog`
HEAD@{0}=96b1e9c AGREES with HEAD; 0 conflict-marked names in a full worktree sweep; no tracked path missing;
`just health` runs to the end (773 decisions in sync, archive index in sync).

**BUG-500 (OPEN, owner-gated).** A rail cannot stop Dropbox, and the second client ('M1 max') still writes this
tree, so the condition can RECUR. Root-cause fix is an owner act: take `.git` out of the synced domain (e.g.
`git init --separate-git-dir=<path outside Dropbox>`, which leaves only a one-line pointer file inside Dropbox) or
stop the second client. Rail 0 makes a recurrence LOUD within one `just health` and UNCOMMITTABLE, instead of
silently presenting a first-commit-of-everything view.

**NO COMMIT** (owner ack owed; the pre-commit gate also refuses: governance/HANDOFFS.jsonl is outside the plan).
## SESSION 20260925M - the git dir left the synced tree: the corruption vector is REMOVED, not patched (and RAIL 0 now enforces it)
**THE VECTOR IS REMOVED, NOT PATCHED.** Dropbox renamed .git/refs/heads/main, then .git/logs/HEAD, then rolled
.git/logs/refs/heads/main BACK to an older file. Every repair was a restoration, but a rail can only make a
recurrence LOUD - it cannot stop a File Provider from renaming what it syncs. RESOLUTION (owner instruction
2026-09-25: approve the future-proof fix if viable): the git dir was RELOCATED out of the synced tree to
/Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git, leaving a 58-byte "gitdir:" POINTER FILE at .git. Dropbox now
syncs 58 bytes of inert pointer and ZERO bytes of git metadata: 126 MB left the synced domain.
**WHY THIS AND NOT SELECTIVE SYNC.** D-366(4) REJECTS selective sync ("it evicts local copies and can pull the
live DB mid-run") - the ignored-attribute / selective-sync route was already closed by an owner decision. A
git-level relocation is outside the sync client's logic entirely.
**WHY THIS IS NOT THE D-366 RELOCATION.** D-366(3) warns relocation is a planned window because 20+ artifacts
bake the absolute path. That warning is about moving the WORKTREE. Moving the GIT DIR leaves every baked absolute
path byte-identical: --show-toplevel still returns the Dropbox path, HEAD is unchanged, and git status
--porcelain is unchanged (94 lines before AND after).
**PROOF, IN ORDER (the guardrail had to have TEETH before the fix).** (1) RAIL 0 was reshaped to resolve the git
dir as GIT resolves it (rev-parse --absolute-git-dir) and to walk the git dir as its OWN root - because the
pre-move script asserted git_dir.is_dir() and would have FAILED on a perfectly intact repository the moment .git
became a pointer file: THE FIX WOULD HAVE BROKEN ITS OWN GUARDRAIL (audit finding). Behaviour preservation was
verified FIRST: same rows, empty plan, and the repair executor's imports (load_config/scan/verdict/
superset_holds) still resolve. (2) require_git_dir_outside_sync_root was turned TRUE while the git dir was still
inside Dropbox, and the rail FAILED, naming it: "the git dir ... is INSIDE a sync domain (matched
Library/CloudStorage/Dropbox)" rc=1. (3) A byte-identical backup was frozen FIRST at
/Users/barn/maxwell_os_gitdir_backup_20260925T2230 (5,334 files, 126 MB, backup HEAD == live HEAD, fsck clean).
(4) A same-st_dev precondition was checked (16777229 == 16777229) so the move was a RENAME, never a cross-device
copy (the BUG-498 class: a claim the code cannot keep). (5) 5,334 files before == 5,334 after; HEAD 96b1e9c
resolves; git fsck clean; git worktree list intact. (6) RAIL 0: "ok repo-integrity: HEAD resolves, git dir
/Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git, logs/HEAD agrees, 0 conflict-marked names in 2 sweeps" rc=0.
**AUDIT FINDINGS (forensic pass, BEFORE the write).** (a) the rail's own .git-is-a-directory assumption (above).
(b) scripts/install_git_hooks.sh wrote to the literal .git/hooks/pre-commit, which after the fix is a FILE -
rewritten to resolve rev-parse --absolute-git-dir, then the hook was reinstalled THROUGH the installer to prove
it (not hand-written). (c) the stale worktree /private/tmp/mx_head was PRUNED before the freeze ("gitdir file
points to non-existent location"), so the backup does not enshrine a broken entry. (d) nothing else in
scripts/ config/ justfile hardcodes a .git/ path.
**CONSEQUENCES THE OWNER OWES A VIEW ON.** (1) The .git DIRECTORY disappears from dropbox.com and therefore from
the other client ("M1 max"): that machine can no longer serve git metadata for this repo - that IS the fix, but a
checkout there is not a repository until it gets its own git dir. (2) The pointer holds an ABSOLUTE path, valid on
this machine only. (3) The pre-commit hook now lives outside the synced tree, so a second machine must run
scripts/install_git_hooks.sh. (4) REVERT is one command pair: rm .git AND mv
/Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git .git.
**STILL OPEN: BUG-400's class is de-vectorised for git metadata, NOT abolished for the worktree.** The worktree is
still synced and files can still be renamed (P0-B); RAIL 0's worktree sweep is the detector for that, and the
43-copy precedent says that risk is real.
**NO COMMIT** (owner ack owed).

## SESSION 20260925N - the D274a invariant became a rail, and the citation exemption was removed at its source

**BUG-499 HALF-CLOSED (the missing CI invariant now EXISTS and has TEETH).** MEASURED before: D274a's rule
(status=PASS implies factual.passed and s5_reason not in the negative set) lived ONLY inside
pipeline/serving_gate.py, and its assertion was called by the WRITER (scripts/apply_serving_gate.py:97) -
NO rail evaluated a single STORED row, so the invariant could not fail. That is the BUG-482 class: a rail
built to be un-silent is itself silent. NEW scripts/check_serving_gate.py re-derives EVERY row from the
verification record by IMPORTING derive_status from the one implementation (C21 - a second implementation
here would be a second truth) and classifies MATCH | STATUS_MISMATCH | REASON_MISMATCH | UNDECIDABLE (no
factual check and no dedup marker is NOT a pass). READ-ONLY by construction (sqlite mode=ro; R-D410 /
BUG-491 class). Every path, column and TOLERANCE is declared in config/serving_gate.yaml#rail (C12),
including SHRINK-ONLY baselines max_status_mismatch / max_reason_mismatch / max_undecidable.
TEETH PROVED BEFORE ANY VERDICT: --selftest drives 5 known-answer controls through the SAME classifier -
verified row stored PASS = MATCH; PASS with factual.passed False = STATUS_MISMATCH; PASS carrying 'contra'
= REASON_MISMATCH; verified row stored QUARANTINE = STATUS_MISMATCH; record with NO factual check =
UNDECIDABLE. 5/5 fire. A guardrail never observed failing is not a guardrail.
MEASURED LIVE (first run): 7,995 rows - **7,995 MATCH, 0 status mismatch, 0 reason mismatch, 0
undecidable**; PASS 5,023 all carry reason 'entail'; QUARANTINE 2,972 = neutral 2,277 / no_evidence 556 /
contra 115 / vacuous 14 / evidence_contaminated 9 / mech_fail 1. The one writer's rule HOLDS on the live
store - which is exactly why the invariant had to become a rail: it now FAILS the moment a future writer
disagrees with the record, instead of serving the disagreement silently.
**THE RULING IS STILL OWED, AND THE RAIL CARRIES IT INSTEAD OF HIDING IT:** epistemic_status is a FORWARD
determinant of status (label -> status IS a function: source-supported/corroborated -> PASS,
cross-source-unverified/speculative -> QUARANTINE) while the reverse is NOT a function (PASS carries two
labels). A MEASURED coupling is not a proven cause - a label DERIVED from the verification record looks
identical - so the rail exits 2 (owner-owed, loud, NOT fatal) and names the declaration that resolves it:
rail.label_relationship = 'derived_mirror' (the 1:1 IS the intended mirror; the rail then reaches ok) |
'independent' (the two must decouple, and a 1:1 is then a DEFECT, exit 1) | 'unruled' (today). One
config act, no edit to the rail.
MEASUREMENT CORRECTION (BUG-498 class - a claim the code cannot keep): duplicate_of is NOT NULL on every
row; it is a non-NULL EMPTY STRING. Falsy, so the rule reads 'not a duplicate' - correct behaviour, wrong
record. The earlier note 'duplicate_of is NULL on every row' was never true.

**BUG-483 RESIDUAL CLOSED - the citation exemption is GONE, not renamed.** config/menu_axis_hashes.yaml
carried a key named 'decision' in KEY position whose value is a sha256, so scripts/reconcile.py read a
digest as a decision id and the file needed an EXEMPTION (meta.citation_exemptions). An exemption is a
place where a rail stops looking. The collision was created by the GENERATOR (it emitted hashes: as a map
keyed by AXIS NAME), so it is fixed at the generator: hashes: is now a LIST of {axis, sha256} records. A
name in VALUE position cannot collide with a KEY vocabulary, and no future axis name can recreate the
collision. Its one reader (scripts/validate_depth_domain_contract.py:410, fail-closed on any other shape)
was updated, the pins were regenerated through the sanctioned writer, and citation_exemptions is now [] -
a FLOOR, shrink-only: a new entry is a declared decision, not an edit. MEASURED AFTER:
decision_registry_wellformed -> **ok** ('773 decision id(s) unique under one namespace; 773 record(s)
carry a canonical state; every citation resolves'). It was owner_owed on EVERY run before this.
CASCADE CHECKED: menu_axis_hashes --check in sync; depth/domain gate 'ok contract: no hard findings, no
owner-owed cells'; tests/test_depth_domain_contract.py 12 passed; artifact_ownership declares the file
derived_regenerable with writer_of_record scripts/menu_axis_hashes.py, so no digest contract to re-stamp.

**RAIL 0 NOW GATES A RUN, NOT JUST A HEALTH REPORT.** scripts/check_repo_integrity.py added to
'just preflight' (2 = owner-owed, loud, not fatal - BUG-457), because a batch that writes from a tree
whose git metadata a sync client has renamed is how a torn artifact is produced (BUG-400/BUG-500).

**THE CARRIED REACH DEBT WAS ALREADY CLOSED BY THE PREVIOUS FIX (no work needed):** 'owner_owed reach: 1
uninvoked of 83' is now 'ok reach: 0 uninvoked of 84 reachable check script(s), 1 declared edge(s) (0
dead)'. The uninvoked script WAS scripts/check_repo_integrity.py, and wiring it as RAIL 0 in just health
invoked it. LESSON: an uninvoked rail is not a rail, and the reach rail named its own remedy.
ORDER RESPECTED: the new rail sits BEFORE reconcile.py --check / measure.py --gaps, whose order is
load-bearing (BUG-489/BUG-490) - a resolver rail after them makes 'has not run yet' read as 'never
published'.
NO COMMIT (owner ack owed). Files touched: scripts/check_serving_gate.py (new), config/serving_gate.yaml,
justfile, scripts/menu_axis_hashes.py, scripts/validate_depth_domain_contract.py, config/reconciliation.yaml,
config/menu_axis_hashes.yaml (regenerated), governance/buglog.md.

## BUG-501 - FIXED - a declaration pointer that resolves to NOTHING was reported as a pending ruling

**The class:** the rail built to detect a declaration diverging from reality reported its OWN breakage as
someone else's unfinished business. MEASURED 2026-09-25: `config/reconciliation.yaml#depth_workbook_row_count`
declared `config/agreement_floor.yaml#panels.depth_axis_panel.rows_declared` - a key that was NEVER WRITTEN in
any file - and printed, on every `just health` for a day: `owner_owed ... (BUG-466 class: report the found
count until the rule is ruled)`. The rule HAD been ruled: D-393, owner-accepted, and its declaration lives in
`config/cohort_declaration.yaml`, which `scripts/depth_pass_agreement.py --check-cohort` already verifies. So a
ruled rule printed as a pending one, and the rail's message actively misdirected anyone reading it.
**ROOT CAUSE (three states, one sentence).** `count_matches` returned the SAME `owner_owed` verdict for
(1) the declaration key does not exist, (2) it exists but is not an integer, (3) it disagrees with the artifact.
Only (3) is a pending ruling; (1) is a BROKEN RAIL - the declaration moved or was renamed and nobody repointed
the entry - and (2) is a malformed declaration. A rule cannot be owed AT a key that does not exist.
`optional: true` was doing double duty as 'the rule is not ruled yet', which is how a dangling pointer got
laundered into owner-owed debt.
**FIX (root, not symptom).** (a) `scripts/reconcile.py`: `not found` -> DRIFT ('a broken rail is never a
pending ruling') and a non-integer declaration -> DRIFT, in EVERY kind; `optional: true` may still downgrade a
MISMATCH to a pending ruling, but may never launder a pointer that resolves to nothing. (b) The entry is
REPOINTED to the ONE home that owns the denominator, `config/cohort_declaration.yaml#cohorts.anchor4_depth.
measured_rows`, and `optional` is REMOVED: once a denominator is declared, disagreeing with the artifact is
DRIFT, not owner-owed. (c) `config/cohort_declaration.yaml` now DECLARES `measured_rows: 148` (+ `decided:
D-393`) - the number was previously computed only at run time, and a count that is never declared cannot
DISAGREE with anything, so a silently changed denominator stayed invisible (the exact BUG-466 failure mode).
(d) `scripts/depth_pass_agreement.py::check_cohort` now ASSERTS the declared count against the workbook,
fail-closed, so the declaration is verified rather than decorative. Two INDEPENDENT oracles now hold the same
number (D-402): the cohort rail proves the denominator BALANCES (measured + absent == declared, absent rows
provably not in the workbook); the reconcile entry pins it to the artifact's ACTUAL row count, so a row added
or dropped cannot keep the arithmetic closed.
**TEETH PROVED BEFORE ANY VERDICT:** 5/5 known-answer controls fire through the SAME classifier - a dangling
pointer is DRIFT; `optional: true` CANNOT launder it; a wrong-shaped declaration is DRIFT; declared 150 vs
found 148 is DRIFT; the real entry is ok. MEASURED AFTER: `ok reconcile: 11 declared object(s) agree with
reality` rc=0 - this rail was owner_owed on EVERY run since BUG-466 was opened, and BUG-501 is the reason it
could never close. `depth_pass_agreement.py --check-cohort` rc=0; contract gate 'no hard findings, no
owner-owed cells' rc=0; tests/test_depth_domain_contract.py 12 passed in 0.25s.
**NOT DONE, DELIBERATELY:** `config/cohort_declaration.yaml` is NOT added to `config/artifact_ownership.yaml`.
Every other `config/*.yaml` declaration file is outside that surface by design (it governs CONTENT artifacts
with owner cells); singling out one config file to look governed would create a second, inconsistent rule
about what an artifact is. Its integrity is covered where it belongs: the citation rail validates its
`decided:` stamp and the repointed entry reads it through the engine.
Files touched: scripts/reconcile.py, config/reconciliation.yaml, config/cohort_declaration.yaml,
scripts/depth_pass_agreement.py, governance/buglog.md. NO COMMIT (owner ack owed).


**PROCESS NOTE (same pass, self-inflicted, caught and recorded).** Minting D-2638 by APPENDING `- id: ...` to
`config/decisions.yaml` appended it AFTER the sequence: that file's `decisions:` list ENDS at line 8540 and a
top-level `summary:` block follows it, so the record landed at top level and broke the document (`expected
<block end>, but found '-'`). `scripts/recompute_decision_summary.py` FAILED CLOSED on the parse error, wrote
nothing, and thereby refused to publish a summary over a broken registry - the writer was right, the writer's
operator was wrong. Repaired by relocating the record as the LAST ITEM of the sequence (774 records, stamp
f7dd45d602d5de79) and re-verified: 'in sync - 774 decisions'. LESSON: a writer must know WHERE the sequence it
extends ENDS, not merely that the file parses; append-at-EOF is only safe for a file whose last top-level key
IS that sequence. THIS is BUG-501's own class one level up - a pointer that LOOKS right and resolves somewhere
unintended.



## BUG-499 - FIXED - the label ontology had THREE inline copies and no home, so the question could not be answered from the repo
**The class:** a RULE that exists in more than one place with no declaration of which copy is
canonical. MEASURED 2026-09-25: the D2284 label rule (isor rating + factual pass -> epistemic_status)
existed as THREE inline copies - pipeline/stage5_verify.py:1024-1031 (the writer),
scripts/sync_s5_checkpoint_from_db.py:114-120 and scripts/reinject_bug198_singletons.py:396-402 -
identical in logic, with rating literals in code (C12) and no single home (C21). The reconciliation
rail therefore reported the coupling as an OPEN ontology question for a day: "every label maps to
exactly one status ... declare rail.label_relationship". The repo could not answer its own question
because the answer was in three places and declared in none.
**Root cause (three parts).** (a) A rule with no declared home cannot be reasoned about - only
observed. (b) The rail asked for a DECLARATION of intent (derived_mirror | independent) when the
honest question was PROVENANCE: where does the label come from? (c) Both offered answers were wrong:
independent demands a decoupling that does not exist (measured below), and derived_mirror inverts the
causal arrow (status mirroring the LABEL is exactly what D274a/D274h forbid) while checking nothing.
**The measured truth.** Re-derived all 7,995 stored labels from (factual.passed, isor.rating):
0 mismatch. status is derived from the factual check alone; the label is derived from the factual
check PLUS the ISOR rating, so the label is a strict REFINEMENT of the status partition and the 1:1
label -> status coupling is a THEOREM about one shared record, not a gate.
**Fix.** (a) The ontology is DECLARED: config/serving_gate.yaml gains epistemic_label (vocabulary +
ordered rules + rating classes) and rail.label_relationship: co_derived - a new fourth term, because
neither offered term was true. (b) ONE home: pipeline/serving_gate.py::derive_epistemic_status +
load_label_config; ALL THREE copies deleted (grep for an inline assignment: NONE remain). (c) The
rail got PROVENANCE teeth: it re-derives every stored label from the same record
(max_label_mismatch: 0, shrink-only) - so a hand-set label, or a rule that moved while the rows did
not, is now a DEFECT. co_derived is strictly stronger than the other two relationships: they inspect
the SHAPE of the coupling, this one inspects its SOURCE.
**Teeth + cascade (measured).** 10/10 known-answer controls fire through the same classifiers (5
status, 5 label, incl. "a HAND-SET label contradicts the record -> LABEL_MISMATCH");
check_serving_gate.py now exits 0 with "7995 MATCH ... [DECLARED co_derived: all 7995 stored label(s)
re-derived from the SAME record, 0 mismatch]"; behaviour-preservation of the extraction proved
(new function != stored label: 0 of 7,995); tests/test_serving_gate.py 25 passed.
**NOT DONE, DELIBERATELY.** The ISOR rating classes are config-declared but the ISOR score itself
still comes from pipeline/schema_accessor.isor_score - the label is therefore only as trustworthy as
the ISOR upstream. That is a separate provenance question (BUG-497 family), not this fix.

## BUG-502 - OPEN - a rule in two scripts with no config is a second truth waiting to diverge
**Evidence (found while fixing BUG-499):** the same derivation existed in three files. They happened
to agree on 2026-09-25 - nothing enforced that. Any future edit to one copy silently splits the
vocabulary: the writer stamps one label, the S5 checkpoint sync re-derives another, and the
difference is invisible until a batch is committed.
**Recommendation (assistant + senior RAG, identical):** a derived column's rule gets exactly ONE
implementation and one config block, and every other site IMPORTS it. Sweep the repo for other
derivations with more than one copy - the BUG-499 pattern is a CLASS, not a one-off.

## BUG-503 - OPEN - a live recipe would add 8 abandoned D2205 columns (incl. a 4th epistemic column) to the governed store
**Evidence:** config/serving_gate.yaml now declares epistemic_status as THE label column, and fbs
carries exactly one such column. But pipeline/migrate_D2205_epistemic.py (exposed as justfile:320-326
migrate-d2205 / --dry-run / --verify) ALTERs fbs ADD COLUMN for 8 D2205 columns - evidence_support,
evidence_independence, evidence_contradiction, evidence_coverage, execution_trials,
execution_successes, execution_context_similarity and epistemic_state (TEXT DEFAULT 'corroborated') -
none of which exist in fbs (75 columns, checked 2026-09-25), and its backfill UPDATEs fbs. Running
that recipe today would mutate the governed store and mint a SECOND epistemic column whose DEFAULT
would print 'corroborated' on rows nobody corroborated - an ontology drift created by a stale tool.
**Recommendation:** tombstone it (move to archive/ behind a declared tombstone, remove the justfile
recipes) or, if D2205 is genuinely live, gate it fail-closed on a declared D2205 authority and a
schema_version the store does not yet carry. Do NOT leave a live mutation path for an abandoned
ontology. Reported, not fixed: this needs the owner (it is a schema question, not a script bug).

## BUG-497 follow-up - FIXED 2026-09-25 (D-2640) - the empty label-provenance quartet was an undeclared state
**Evidence (MEASURED 2026-09-25, fbs 7,995 rows):** menu_hash, content_type_source, discipline_source AND
extraction_type_source are empty on 7,995/7,995 rows. pipeline_run_id takes exactly three values (t11
7,867 | bug198_reinject 6 | e2e 122). This is NOT a stage-6 write bug: the corpus predates the R1/D-279
stamp at pipeline/stage4_merge.py:2256. The defect was that the state was UNDECLARED, so an empty stamp
read as "no menu" was indistinguishable from a broken stamp, and each consumer was free to infer.
**Root cause:** a measured population that is only COMPUTED cannot disagree with anything (BUG-501/D-2638
class), and a provenance state that only a human can tell apart must be DECLARED by the store.
**Fix:** config/label_provenance.yaml declares the boundary as a CLOSED SET of generation runs + a DECLARED
measured_rows; pipeline/label_traceability.py is the ONE classifier (stamped | pre_boundary | missing |
unstampable); scripts/check_label_provenance.py is the rail (6/6 known-answer controls, then: population
must equal the declared 7,995, a row OUTSIDE the boundary without the full quartet is a DEFECT exit 1, an
unstampable store is a DEFECT); the state is exposed as the query-surface field label_traceability at the
ONE row-mapping choke point (pipeline/retrieve.py::_row_to_dict, so all four retrieval legs carry it) and
in pipeline/query.py.
**Not done deliberately:** NO backfill (D-277 forbids manufacturing a provenance claim); the boundary is
NOT an R14 exemption (the R14 object stamps ARE present on all 7,995 rows - claiming otherwise would be an
ontologically false declaration). Result: ok check-label-provenance: 7995 pre_boundary, 0 missing.
**Remaining (owner-level):** dissolving the boundary requires RE-STAMPING, i.e. an owner act recorded as one.

## BUG-502 update 2026-09-25 - the instance is fixed, the CLASS sweep remains OPEN
**Fixed instance:** the D274a row comparator existed twice (scripts/check_serving_gate.py kept its own
copy of the comparison the writer's rule implies). The comparison now lives in
pipeline/serving_gate.py::store_verdict, imported by the rail (behaviour proven unchanged by its 10/10
known-answer controls) and by the NEW writer half: pipeline/stage6_commit.py::insert_fb (the ONE path that
INSERTs into fbs, also used by scripts/reinject_bug198_singletons.py) refuses a row whose status its own
verification record does not derive - through the same comparator the rail uses. MEASURED: 0 of 7,995
stored rows would be refused, so the guard fires only on a row written by something other than the one
writer. Config act: serving_gate.pre_write_enforcement: "reject" (an unknown value is fatal in code, so
the key cannot become an off switch). D274a now has BOTH halves: a pre-write refusal and a post-hoc rail.
**Still OPEN:** the repo-wide sweep for other derivations with more than one copy (the BUG-499 pattern as a
CLASS). Candidates to measure next: the S5 confidence_score formula (stage5_verify.py has its own copy
alongside scripts/reinject_bug198_singletons.py) and the needs_human_review ISOR rule (same two files).

## BUG-502 update 2026-09-25 (2) - the score-axis instance is FIXED; the CLASS sweep stays OPEN
MEASURED before the fix: the S5 score axis (confidence_score formula + the quarantine cap + the
needs_human_review ISOR rule) was a VERBATIM copy in pipeline/stage5_verify.py:999-1021 and
scripts/reinject_bug198_singletons.py:378-394. Two implementations of one rule are two truths, so a
calibration applied to one path would have silently produced two different scores for one record.
FIX: the rule now lives once - pipeline/serving_gate.py::derive_conf_and_review - and BOTH call sites
import it (the epistemic-label copy had already been collapsed in the BUG-499 pass).
PROOF, and not by reading code: scripts/check_s5_score_axis.py re-derives BOTH outputs from every
stored FULL row and compares 1:1 -> 7995 MATCH, 0 score mismatch, 0 review mismatch, 0 undecidable;
8/8 known-answer controls fire (the 0.001 nudge, the cap having teeth, and the pair that differs ONLY
in the ISOR rating, which proves the rating is load-bearing). WIRED into just health.
PROCESS BUG (recorded because it nearly became a false finding): the FIRST probe selected a column
SUBSET, so _check_enrichment_quality read empty application/failure_mode fields and reported 5,023
score mismatches - every one an artifact of the probe, not of the corpus. A re-derivation proof must
feed the FULL row; a partial row is not the record.
STILL OPEN (class): the mechanised-check home and any remaining derived-column rule outside the
serving gate remain to be swept.

## BUG-503 - TOMBSTONED 2026-09-25 - the abandoned ontology has no reachable write path
migrate-epistemic / -dry / -verify (justfile) were a REACHABLE write path - 15 words between an agent
and an ALTER - into an ABANDONED ontology: 8 D2205 columns on fbs, including a FOURTH epistemic column
epistemic_state TEXT DEFAULT corroborated (it collides in name with the live epistemic_status) plus
backfill UPDATEs. MEASURED: none of the 8 columns exist on fbs today (75 columns).
FIX: the three recipes are REMOVED and replaced by a tombstone comment; the script stays as
archaeology but REFUSES with exit 2 (owner-owed, BUG-457 convention) unless the owner passes
--i-understand-D2205-is-abandoned. MEASURED: rc=2 with the refusal message; 0 recipes reachable.
NOT done deliberately: the script is not deleted (the D2205 archaeology has value) and no speed bump
was placed in front of a STILL-reachable path - the point is unreachability, not a warning.

## BUG-504 - FIXED 2026-09-25 - the S5 score axis was governed by SILENT CODE DEFAULTS
MEASURED: pipeline_paths.py read the five score-axis values as
_CFG.get("stage5", {}).get("confidence", {}).get(key, <code default>) while
config/pipeline_config.yaml declared NO stage5.confidence block at all. Every weight was therefore the
hardcoded default, and a typo or rename of a key would have changed the score axis with NO error
anywhere (C12/C16: the config miss IS the bug).
FIX: the block is DECLARED in config/pipeline_config.yaml#stage5.confidence with byte-identical values
(0.35 / 0.25 / 0.40, cap 0.25, human_review_isor_rating strong) and read through a loud _s5_conf()
that raises naming the file and the key.
PROOF: the rail still reproduces 7995/7995 rows after the change (the pre-existing behaviour is now
pinned by declaration rather than by accident); a test asserts every declared key exists.

---

## 2026-09-26 — D-2648 session: the Dropbox conflicted-copy hazard + a YAML write class

### BUG-500 (CONFIRMED, systemic) — a Dropbox conflicted copy is silent drift, not a merge conflict
MEASURED: 36 siblings `<name> (M1 max's conflicted copy YYYY-MM-DD)<ext>` in this tree; 26 held NEWER work than the
live file, which Dropbox had REVERTED to an older blob. The D-2645/D-2646 rail work, the WIRED justfile (live: 16,485 B
and UNPARSEABLE, recipe line 13 lost its indentation) and the 782-record config/decisions.yaml all lived in a sibling
while every rail read the stale live file and printed ok. A reverted artifact under a rail is indistinguishable from
drift: the rail is not wrong, its INPUT is.
RESOLUTION (D-2647, measured never guessed): scripts/resolve_dropbox_conflicts.py + config/conflict_policy.yaml.
identical-to-INDEX -> restore from it (lossless); identical-to-HEAD -> the sibling IS the committed mark; otherwise a
real 3-way merge (git merge-file) with base = the HEAD blob; a LINE-SUPERSET wins outright; a two-sided divergence is
HELD in governance/CONFLICT_REGISTER.md. Dry run by default; --apply to move a byte; writes are C6 (tempfile -> fsync
-> os.replace). Pipeline state under `knowledge pipeline/` is OWNER judgement and is never text-merged.
PROOF: 28/36 resolved with zero conflict, 30 archived to archive/conflicted_20260926/ (never deleted); justfile parses
YES; recompute carries D-2645; decisions.yaml restored to 782 records with D-2643/2644/2645/2646 + revocation on D2205.
STILL HELD (owner judgement, NOT guessed): governance/bug_status.json (CONFLICT:2), governance/bug_status.md
(CONFLICT:1), governance/anchor_adjudication_workbook_20260924.csv (CONFLICT:1) + 3 pipeline checkpoints.

### BUG-505 (FIXED) — two YAML artifacts left UNPARSEABLE by string surgery, in ONE session
(1) config/decisions.yaml: the minted D-2647 record carried `decision: ... judgement: a checkpoint ...` — a colon-space
inside an UNQUOTED PLAIN SCALAR. The file stopped parsing, so recompute_decision_summary reported "not in sync" for a
reason no rail could name. (2) config/derivations.yaml: scripts/check_config_defaults.py#record_ceiling appended its
REMEASURED sentence AT END OF FILE, so it landed after `enforcement.direction` and made the registry unparseable — the
homes rail then DIED inside yaml before it could load its own registry, and the stale hardcoded RAIL_DATE wrote a FALSE
date (2026-09-25 for a 2026-09-26 measurement).
ROOT CAUSE (class, not instances): a writer that does not verify the bytes it is about to write has moved the failure
one reader downstream. FIX (D-2648): scripts/lib/yaml_guard.py is the ONE home for assert_yaml (parse the exact text,
name artifact+line+column+line text, refuse) and append_to_block (insert prose INSIDE a block scalar at the block's own
indent). Wired into BOTH writers; record_ceiling's bare REGISTRY.write_text (no tempfile/fsync/os.replace, no backup)
now goes through write_guard.write_document (C6, D-401); the run date is DERIVED (yaml_guard.today()) not hardcoded.

### BUG-506 (FIXED) — reconcile.py crashed with a bare UnicodeDecodeError on OWNER artifacts
scripts/reconcile.py#_rows read CSVs as strict UTF-8. governance/anchor_adjudication_workbook_20260924.csv is
Excel-on-macOS output, i.e. MacRoman (0xCA = non-breaking space at offset 42564, 0xD1 = em dash in the two
s4_*_review_sheet.csv), so the reader CRASHED and the defect read as a bug in the reader: an error leak naming no
artifact (C16). FIX: `encoding:` is now DECLARED per entry in config/reconciliation.yaml (mac_roman) and the reader
fails CLOSED naming the artifact, the offset and the byte when an undeclared non-UTF-8 artifact appears (D-2644). The
owner instruments were NOT rewritten to suit the reader.

### BUG-507 (FIXED) — the anti-resurrection rail tripped on its OWN fixture
scripts/check_revoked_references.py:314 named the revoker subject `epistemic_state` inside the DESCRIPTION of
known-answer control 8 instead of the reserved FIXTURE_TOKEN namespace, so the rail reported 1 LIVE reference — its own
control. FIX: the control's name is derived from FIXTURE_TOKEN, like every other fixture in that file.

### BUG-508 (FIXED) — a ceiling nothing enforced
config/derivations.yaml#enforcement.max_non_homed was 3 while the registry measured 1 non-homed row of 9, so the homes
rail printed owner-owed (RC=2) on every run. LOWERED 3 -> 1 by the rail's own rule ("a ceiling may only be LOWERED;
raising it is a decision").

### BUG-509 (FIXED) — the conflict resolver was not idempotent
resolve_dropbox_conflicts.py rglob'd the tree for `*conflicted copy*` and matched its OWN archive, so every run
re-reported ~22 already-resolved siblings as NO-LIVE/'held' — noise on the register that hid the 3 real held rows.
FIX: the declared archive_dir is a fixed point and is skipped.

### BUG-510 (FIXED) — ONE rule, TWO implementations, minted by the very session that named the rule
scripts/reconcile.py carried its OWN `_declared_encoding`/`_read_encoding` copy (written hours earlier in this
session) beside the shared scripts/lib/artifact_encoding.py — the exact D-2646 defect ("a rule that decides a value
has ONE implementation"). MEASURED 2026-09-26: the session summary recorded this as logged, and governance/buglog.md
did NOT contain it — a claim and an artifact disagreeing, which is the class this repo exists to remove. FIX: the
duplicate is DELETED, all three CSV read sites go through artifact_encoding.read_encoding(path, REPO), and the rule
now carries known-answer controls that `just health` actually runs (8/8).

### BUG-511 (OPEN in two orphan readers) — a reader that GUESSES an encoding does not crash, it silently changes text
scripts/audit_human_verification.py:79 opens governance/s4_domain_review_sheet.csv as `cp1252`. MEASURED 2026-09-26:
that artifact is MacRoman (2 x 0xD1); 0xD1 is an em dash in MacRoman and 'N-tilde' in cp1252, so the guess NEVER
raises — it quietly rewrites the very text two readers then compare (D-2644 says an encoding is a declared fact).
scripts/normalize_owner_workbook.py carries a THIRD encoding implementation (a measured fallback list) and
scripts/cross_examine_anchor_axes.py opens owner sheets as utf-8-sig. None of the three is wired into `just health`,
so nothing consumes their output today; they are declared here so the D-2644 migration is a LIST, not a memory.
Task: repoint all three to scripts/lib/artifact_encoding.py and declare the encoding in config.

### BUG-512 (FIXED) — known-answer controls that nothing ran, and a resolver that could never fire
(i) scripts/lib/yaml_guard.py (D-2648) and scripts/lib/artifact_encoding.py shipped `controls()` behind a --selftest
entry point that `just health` never invoked: the controls were a comment, which is BUG-492's own rule turned on the
guards themselves. FIX: both selftests are wired into the health recipe.
(ii) scripts/resolve_dropbox_conflicts.py returned 0 in EVERY mode, so wiring the D-2647 anti-revert rail into health
would have added a line that can never fail (a register that cries nothing). FIX: tri-state per BUG-457 — 0 no
sibling (one live artifact per path) | 1 a sibling the MEASURED rule proves resolvable is still unapplied | 2
owner-owed only. MEASURED now: --check reports 6 siblings (3 owner-artifact CONFLICT, 3 pipeline checkpoints =
owner judgement) and exits 2, which health prints loudly and does not treat as fatal.

### BUG-513 (FIXED) — the validated mint path's OWN first run wrote a half-consistent registry
MEASURED 2026-09-26: the first `--mint --apply` inserted D-2649 and then ABORTED because the post-condition was
evaluated against the pre-insert derived fields, leaving config/decisions.yaml with 784 records under a 783 header —
caught by the NEXT reader, not by the writer. FIX: the record and the derived fields it invalidates go to disk in
ONE write (`_surgical_text` is now the single implementation of that surgery, used by both paths, D-2646), and the
post-condition is checked on the bytes about to be written. Same class as BUG-505: a writer may not leave a document
in a state its own reader would reject (D-2648). Now: 784 decisions, --check rc=0, reconcile rc=0.

### BUG-514 (OPEN) — three readers still decide an encoding by GUESS
Confirmed by the 2026-09-26 audit: scripts/normalize_owner_workbook.py carries a measured FALLBACK LIST where a
declaration belongs, scripts/audit_human_verification.py hardcodes cp1252 for a MacRoman artifact, and
scripts/cross_examine_anchor_axes.py opens owner sheets as utf-8-sig. None is wired into `just health`, so nothing
consumes them today; they are the declared migration list for D-2644/D-2649.

### BUG-516 (OPEN, root cause of BUG-514) — the decode rule had NO home: NINE copies, three vocabularies
MEASURED 2026-09-26 by `python3 scripts/check_encoding_homes.py --list` (the rail now records the number instead of a
session remembering it): nine modules decide how to decode an artifact's bytes for themselves - five byte-identical
`DECODE_ORDER = ("utf-8-sig","utf-8","mac_roman","cp1252")` literals (validate_depth_domain_contract, score_claim_shape_gate,
build_claim_shape_instrument, elicit_claim_shape, ingest_panel_column), an inline copy in normalize_owner_workbook.py,
`ENCODINGS = ("utf-8","latin-1")` in verify_anchor_family_registry.py, an inline ("utf-8","cp1252","latin-1") in
scan_review_artifacts.py, and a bare `open(..., encoding="cp1252")` in audit_human_verification.py. BUG-514 named three
of them; the defect was one rule with nine implementations (D-2646), so the count is the finding.
WHY IT IS SILENT: every single-byte codec "succeeds", so two modules reading ONE artifact can decode it differently and
NEITHER raises. MEASURED on governance/s4_domain_review_sheet.csv (Mac Roman, 34 non-ASCII bytes): the `note` column
holds "no signal domain - best-fit" in Mac Roman and "no signal domain N-tilde best-fit" under cp1252.
FIX LANDED THIS SESSION (partial): the reader that was measurably WRONG is repointed to the home
(scripts/lib/artifact_encoding.py), the encoding is DECLARED in config/reconciliation.yaml#artifact_encodings, and
scripts/check_encoding_homes.py is the new rail that DETECTS a tenth copy: rc 0 no copy | 1 a NEW copy appeared, or the
ceiling was widened (shrink-only) | 2 declared debt only (loud, not fatal). The debt register is
config/encoding_homes.yaml, written FROM the rail's own measurement, ceiling 9. NOT a mitigation: the nine copies are
now registered, machine-counted debt that can only shrink, and the next copy fails health.
CONTAINMENT (measured, so the severity is not overstated): the four columns audit_human_verification.py matches on
(blank header fb_id, HUMAN_domain_VERDICT, discipline_human) hold NO non-ASCII byte, so no output was wrong - only the
read was silent. That is exactly the BUG-511 mechanism, one owner em dash away from being wrong in the output too.

### BUG-517 (FIXED) — a declaration the reader never consults, and a BOM that silently renames a column
MEASURED 2026-09-26: read_encoding() returned "utf-8" whenever the bytes decoded, so a DECLARED `utf-8-sig` was never
consulted - and a BOM-led artifact read as plain utf-8 leaks U+FEFF into the first CSV header, so `row.get("item_id")`
returns None and every row silently vanishes (the BUG-511 class: no crash, changed meaning). It also accepted a
declaration that cannot decode its own artifact, which surfaced downstream as a bare UnicodeDecodeError naming no
artifact (an error leak, C16).
FIX (D-2644/D-2649 widened): the declaration is AUTHORITATIVE and the BYTES are a second declaration home - the two are
JOINED. No declaration -> the bytes decide (utf-8 / utf-8-sig by BOM), non-UTF-8 bytes fail CLOSED. A declaration -> it
wins, but is VERIFIED: a declared codec that cannot decode its artifact fails CLOSED, and where the declaration and the
bytes decode to DIFFERENT text the join fails CLOSED naming the artifact, both encodings, both homes and the first
character where they diverge. Where they decode to the SAME text (an ASCII artifact declared mac_roman) they AGREE and
are tolerated, not presumed. No live artifact was affected (the only non-UTF-8 artifacts are declared mac_roman, which
cannot be read as UTF-8 at all), so this fix is preventive: 14/14 known-answer controls, wired into `just health`.
Also fixed in the same pass: a path outside the repo raised pathlib's ValueError, naming no rule (C16) - now refused
with a message that says what is wanted.

### BUG-516 UPDATE (2026-09-26, sweep LANDED) - the decode rule now has ONE home and ZERO copies

The register ceiling was 12 modules and is now 0 (config/encoding_homes.yaml, SHRINK-ONLY, D-2642). Every module
that decided an encoding locally now DELEGATES to scripts/lib/artifact_encoding.py; a delegating wrapper carries
no codec vocabulary, so it is an INTERFACE, not a second implementation (D-2646). Verified BEFORE writing: all 12
compile, the AST scan finds no codec label left, and text containment was MEASURED over 642 text-ish artifacts.
Containment result: exactly TWO text differences, both the same two artifacts, both for the two readers whose
fallback was latin-1/cp1252 - i.e. the OLD read was the wrong one and the new read is the DECLARED Mac Roman.
No other artifact's text changed. The two readers that were measurably WRONG (scan_review_artifacts.py and
verify_anchor_family_registry.py) are repointed, so BUG-514's root cause is CLOSED, not mitigated.

### BUG-518 (FIXED, found by the same sweep) - a fallback that could never fire, and an artifact that never declared its encoding

(a) UNREACHABLE FALLBACK: the five DECODE_ORDER tuples ended with cp1252, but Mac Roman decodes ALL 256 byte
values, so a decode can never fall past mac_roman into cp1252. The 4th entry was decoration, not a fallback - a
fallback that cannot fire is a claim about the data that was never true. It looked like four safety nets while it
was three. (b) UNDECLARED ARTIFACT: governance/s4_discipline_review_sheet.csv is NOT valid UTF-8 (21 non-ASCII
bytes, first bad 0xD1 at offset 5204 = an em dash in Mac Roman; 63 owner-adjudicated rows) and was NEVER declared,
so any reader repointed to the one home would have failed closed on it - the sweep would have converted a silent
guess into a crash. It is now declared mac_roman in config/reconciliation.yaml with the measurement beside it.
MEASURED cross-check: the .utf8 sibling is NOT a recoding of it (different row/column content) - a sibling file is
not evidence of an encoding; the declaration is. (c) SILENT-REPAIR READS: errors="replace" turns a bad byte into
U+FFFD and errors="ignore" DROPS it - neither crashes, both change the text (the BUG-511 class). Fixed in
scripts/cross_examine_anchor_axes.py (fail-closed via the home); scripts/vote_anchor_domains.py:119 (errors="ignore"
on .env) remains OPEN and is the next item.

FORENSIC NOTES (why nothing cascaded): every artifact is now either valid UTF-8 or DECLARED, so the home's
fail-closed path has an EMPTY trigger set (642 artifacts scanned, 3 non-UTF-8, 3 declared); the two artifacts whose
text changes under latin-1/cp1252 carry zero non-ASCII in every column the two repointed readers match on, so no
verdict moves; and the three health-wired consumers were re-run at rc=0. `just health` rc=0, and the
`FAIL encoding-homes` line is GONE (now `ok ... debt 0 of ceiling 0`). NOTHING IS COMMITTED. Owed: a rail-4
widening_log entry for scripts/check_encoding_homes.py + config/encoding_homes.yaml; an MTR entry for the STALE
governance/remaining_verification_audit.csv found on 2026-09-26; and the owner commit ack (D-381 gate).

### BUG-519 (FIXED 2026-09-26) - the operator-key rule had FIVE homes, and one of them DROPPED bytes silently

MEASURED: "which key does this run use" was implemented FIVE times with THREE behaviours - scripts/vote_anchor_domains.py:118
(read `.env` with errors="ignore": a byte that is not UTF-8 was DROPPED and the read carried on - the BUG-511/C16 class),
scripts/vote_flagged_core.py:77 (Path.read_text()'s PLATFORM-DEFAULT codec), and three shell copies (scripts/run_joint_vote.sh:32,
scripts/run_remaining_axes_vote.sh:5, scripts/run_queue_59_vote.sh:7) that grep the line and `tr -d '[:space:]'` the value - a
DIFFERENT parse of the same line. A second implementation of one rule IS the defect (D-2646, the BUG-499/502 class), and this
one touched a SECRET: nothing could report that two copies disagreed.

FIXED, not mitigated: the rule now has ONE home - scripts/lib/operator_env.py (read_key/parse_env_text), 10/10 known-answer
controls (flag > environment > .env; a commented-out key is not a key; a later duplicate never wins; a bad byte ANYWHERE fails
CLOSED because the whole file is decoded before it is parsed). Both Python copies are delegating wrappers. The bytes are read
through the decode home, so the repair mode is gone, not improved (BUG-511: a better default is still a guess).
`.env` is deliberately NOT added to config/reconciliation.yaml#artifact_encodings: it is GITIGNORED, so a declaration in the
tracked register would be a claim the repo cannot verify, and an absent .env is normal. The measured path decides utf-8 for
utf-8 bytes and fails LOUDLY and actionably otherwise - which is the behaviour owed by C16.
RESIDUAL (declared, not hidden): the three SHELL copies still parse .env. Unifying them needs a shell-safe home that does not
`eval` a secret (a shell-quoting hazard worse than the duplication). OWED.

### BUG-520 (DETECTOR LANDED 2026-09-26) - a silent repair is not a protection from crashing; it is a protection from NOTICING

MEASURED by a tree-wide AST census: 28 `errors="replace"` / `errors="ignore"` read sites in scripts/ and pipeline/, and 4 more
in tools/ - a directory the first census never looked at (a blind spot found by widening the scan roots, not by a report).
Fourteen of them read repo artifacts or source text; the rest tail runtime logs or foreign streams.

FIXED AS A CLASS: scripts/check_silent_repair.py + config/silent_repair.yaml. It classifies every site - `allowed` (repair is
CORRECT: the bytes are a runtime log or a foreign producer, and nothing is written back), `debt` (an artifact/source read that
still owes a repoint to the decode home), or NO ENTRY = DRIFT (exit 1). `errors=` with a non-literal value is reported as
`unresolvable` and must be declared too: a detector never passes what it cannot read. An entry with no measured site is reported
STALE, so the register cannot rot. The ceiling is the RAIL's own measurement, SHRINK-ONLY (D-2642): debt 20 of ceiling 20,
unknown 0. --selftest 12/12 known-answer controls (BUG-492: seen to fire AND seen to stay quiet). Wired into `just health`.
MEASURED 2026-09-26: every declared site is INERT today (the 3 non-UTF-8 artifacts in this repo are all declared and no source
file is non-UTF-8) - which is exactly why the debt is declared rather than trusted: a repair that never fired has never been
tested. BUG-518(c) - the .env errors="ignore" read it named as remaining OPEN - is CLOSED by BUG-519.
CONTAINMENT: no stored object changes; the two pipeline/ sites that write back what they repaired are inside pipeline/**, which
is will_not_touch this session (rail 4) and are declared debt, not touched. NOTHING IS COMMITTED.

### BUG-521 (MEASURED 2026-09-26) - an encoding the ENVIRONMENT decides is UNDECLARED: 393 sites in 166 modules, and no rail could see them

MEASURED by a tree-wide AST census over scripts/, pipeline/ and tools/: 393 text read/write sites in 166 modules take their codec
from locale.getpreferredencoding(False) instead of from the artifact - read_text 138, open() 178, write_text 47, Path.open 27, plus 3
opens whose mode is not a literal (UNRESOLVABLE: not proven text, not proven bytes - it must be declared, never assumed). By root:
scripts 182, pipeline 168, tools 43. Of the 393 sites, 47 are WRITES.

WHY IT IS A DEFECT AND NOT A STYLE POINT: D-2644 says an encoding that is not DECLARED is an undeclared value, and a platform default
is declared by nobody. On this machine it is usually UTF-8 and therefore INERT - which is exactly why it survived 166 modules unseen.
It is not inert elsewhere: under LC_ALL=C a non-ASCII byte raises a UnicodeDecodeError that names no artifact (the C16 error leak),
and on Windows the default is cp1252, so 0xD1 decodes to 'N-tilde' instead of an em dash in every reader (BUG-511). The WRITE case is
the sharper one: the bytes an artifact receives then depend on the machine that wrote it, so a sha256 pin does not pin the same bytes
on two platforms (C3 sovereignty / C26 cross-platform / R14 provenance).

WHY NO RAIL SAW IT (MEASURED): scripts/check_encoding_homes.py matches non-UTF-8 CODEC LITERALS only; scripts/check_silent_repair.py
matches `errors=` LITERALS only. A platform default has NEITHER literal - the same blind-spot shape as tools/ in the 2026-09-26
errors= census, found the same way: by widening the scan, not by a report.

DETECTOR: scripts/check_undeclared_encoding.py + config/undeclared_encoding.yaml (a class detector with its own known-answer controls,
BUG-492), with the number OWNED BY THE RAIL (D-2642 probe -> rail handover; a raise is refused afterwards). `encoding=None` counts as a
site: an explicit None IS the platform default. RESIDUAL (declared, not hidden): the rail is already wired into `just health`, but at
the moment of this entry it has not landed on disk, so health is RED until it does. NOTHING IS COMMITTED.

### BUG-522 (FIXED 2026-09-26) - a module read its own input by TWO rules, and one rule's repair could never fire

MEASURED: scripts/definition_nli_verify.py read its own input - a pipeline checkpoint JSONL - by two different rules. The data path
(_iter_fbs) opened it strictly with encoding="utf-8"; the provenance probe (_provenance, "coder_key_present") opened the SAME file with
errors="ignore". That repair could not fire: by the time it ran, the strict path had already refused the byte. So it protected nothing
from crashing - it protected from NOTICING, and it hid the disagreement between the two rules. This is BUG-518's "fallback that could
never fire" recurring.

FIXED as ONE named rule (D-2646), not as a per-site exception: _INPUT_ENCODING is named once, _open_input(path) returns
open(path, encoding=_INPUT_ENCODING), _read_input_text(path) derives from that rule and does not restate it, and both call sites
consume the rule. AST-verified: zero `errors=` calls remain in the module. CONTAINMENT: the default input is the IMPORTED
pipeline.pipeline_paths.STAGE5_CHECKPOINT (no new literal), and a missing input still exits 1 with a message naming the artifact.

### BUG-523 (OPEN - found 2026-09-26 only because a human asked "what exactly must I ratify in D-2650?") - the reserved-fixture rule covered the TOKEN and left the ID SPACE unclaimed: two live decision ids are already spent as fixture data

MEASURED: the literal "D-2650" occurs 7 times in this repo and ALL 7 live inside the known-answer controls of
scripts/check_revoked_references.py (lines 290-308). A SECOND fabricated id, "D-2651", is used at line 303. Neither id is declared,
claimed or reserved anywhere; the highest minted id in config/decisions.yaml is D-2649. The next two decision ids this project mints
are therefore already in use as fixture data.

WHY IT MATTERS - the trigger is LATENT, not immediate: minting D-2650 raises no rail today, because this rail's patterns are built from
the REVOKED scopes. The damage is conditional: the day D-2650 (or D-2651) is revoked, the rail - which scans scripts/ and is explicitly
NOT exempt ("the detector itself is NOT exempt", config/decisions_policy.yaml) - finds its own fixture as a live reference to a revoked
id and fires on itself. That is audit F1 recurring, and its only outs then are an exemption (the self-weakening the fixture docstring
forbids) or a rename under time pressure. Second hazard: a fixture id that later becomes live stops being a fabricated id, so the
control that proves "a different id is not a reference" quietly loses its subject.

WHY NO AUDIT FOUND IT: the class was ALREADY in the audit's repertoire. Audit F1 (MEASURED 2026-09-25) found this same rail firing on
itself, and the fix was a RENAMED TOKEN (FIXTURE_TOKEN = "fixture_revoked_token_zz"), plus a later rename of a control NAME that had
named a live subject. The fix was instance-shaped, not namespace-shaped: the tokens were moved into a reserved namespace, and the two
decision-id literals were left floating in the live id space. The reservation is also unenforceable as written -
config/decisions_policy.yaml says "a RESERVED fixture token" without declaring what the reserved SPACE is (no range, no prefix, no
list), so no machine can answer "is this name reserved?" (C12: a rule whose subject is undefined is not configurable). MEASURED: no
rail polices decision-id literals in code at all (a grep for an id pattern returns zero). The docstring's "may not become a revoked
token" is a comment; BUG-492: an invariant that no machine enforces is a comment.

FIX, WITH AN ORDERING CONSTRAINT: declare the reserved fixture id space in config (MEASURED: D-9xxx is entirely ABSENT from
config/decisions.yaml, so D-9000-D-9999 is free), renumber both fixtures into it, and add a known-answer control asserting that every
fixture id lies in the reserved space AND that the reserved space is empty in the live registry. This must land BEFORE the next decision
is minted - otherwise the next mint either collides with the fixture or the fixture silently loses its known-answer property.
CASCADE (declared, not hidden): appending to this buglog makes governance/bug_status.json/md STALE, and both are currently HELD under an
unresolved Dropbox conflict, so their re-derivation cannot run until that is resolved (D-2647). NOTHING IS COMMITTED.

### BUG-524 (OPEN 2026-09-26) - the STORES and COLUMNS axes had NO machine: two rails land, and their own controls found 3 defects in the rails themselves

CLASS (not an instance): six of eight audit axes had no machine; every finding that closed the gap came from the two
with none - STORES and COLUMNS. A rail is a triple (subject, site-shape, roots); its blindness IS its boundary.

MEASURED 2026-09-26, now enforced by two registered rails (both wired into just health):
  * scripts/check_store_authority.py + config/store_authority.yaml (9/9 controls, 0 faults): 7 stores declared,
    exactly ONE authoritative. The check found what no machine could before: `archive/db_backups/
    maxwell_pre_index_20260917.db` was UNDECLARED and shares 18 table names (fbs, taxonomy_counts, the vec_*
    shadows) with the truth, and `data/maxwell.db` (19 rows vs 7995) shares the same schema - a consumer pointed
    there gets a plausible answer set that is 0.24% of the truth, with no crash.
  * scripts/check_store_columns.py + config/store_columns.yaml (OWED rc=2, debt 9 shrink-only): 75 columns, 52 by
    declared default, 25 named. The RULER is the blind spot: `count(col)` counts '' as present, so the earlier hand
    census claimed "procedural_skill is 0/7995" when the truth is 7995/7995 rows carrying a BLANK, and "ten
    zero-populated columns" when the named rulers show 12 content-empty and 20 single-valued.
    NEWLY MEASURED DEFECTS (declared debt, shrink-only): `classification_status` is constant 'CLEAN' on all 7995
    rows while classification_errors records 2 real errors and status QUARANTINEs 2972 - a status column that is
    FALSE; `content_type` is 'principle' on all 7995 - a label that cannot vary; `application` is blank on 1 row
    and `jargon` on 2091 (5868 distinct) - blanks a reader cannot tell from "unwritten"; the three `*_source`
    columns are blank 0/7995 while governance/gold_4axis.jsonl is 100% stamped per axis - R14 holds at ROW level
    and FAILS at LABEL level.
  * the rails' OWN known-answer controls (BUG-492) found 3 defects in the rails on first run: an orphan
    continuation line from asserting the for-statement (SyntaxError, caught by py_compile); a resolved-vs-unresolved
    path comparison that made find_stores raise ValueError from pathlib instead of naming the artifact (C16 leak);
    and a control whose expectation was mis-specified so it could never pass - a control that cannot pass is as
    useless as one that cannot fail.
  * `shares_tables` was first declared as a LIST of table names: a second copy of the table inventory (D-2649). It
    is now a FACT (`true`) checked against the disk - the rail reports which tables overlap, the register does not.
ORDERING CONSTRAINT (BUG-523 follow-through): both rails were written WITHOUT spending a decision id - a register
may be landed and wired while its governing decision is still owner-pending, but the register must SAY so
(`decided: PENDING-OWNER`), never pre-empt the id.

### BUG-525 (OPEN 2026-09-26) - the AMBIGUOUS-DECLARATION class: a key declared twice in one mapping is SILENTLY last-wins, and no rail could see it

CLASS (found by the audit the owner demanded BEFORE the implementation was committed): PyYAML does not refuse a key
declared twice in the same mapping - it keeps the LAST one. The first declaration is therefore a fact nobody reads
(D-2649: one declared fact, one declaration home), and it is INVISIBLE to every neighbouring rail, because each of
them parses the file and the parser has already resolved the ambiguity for them. D-2648 said an artifact must PARSE
before it is written; measured today: a document can parse and lie.

FIVE INSTANCES, none previously known, all found by widening the scan to a new SUBJECT (NAMES/declarations) rather
than a new site-shape:
1. config/store_columns.yaml carried TWO `ceiling:` blocks (debt 7 at line 57, debt 9 at line 60). The second was
   written by the new column rail's own --record, whose replaced region began at `measured:` - so the older
   `ceiling:` above it survived and the tail re-declared the key. The rail recorded a number while a shadowed
   declaration of the same fact stayed on disk.
2. config/pipeline_config.yaml declared `stage5.confidence` TWICE inside `stage5:` (lines 465-470 shadowed by
   497-502). The five S5 score-axis values are read by pipeline_paths.py, so a declared fact read by the score axis
   had two homes. The values were parse-identical (0.4 / strong), so no score ever moved - only the ambiguity
   existed; the shadowed copy was deleted and the surviving values are byte-for-byte the ones that were in force.
3. backups/decisions.PRE_config-first-data-edit_20260925T214936Z.yaml does NOT parse (ScannerError, line 8651 of
   602 KB) - a DEAD revert path: a backup that cannot be loaded is not a backup (C23/R-D410).
4. backups/derivations.PRE_check_config_defaults_20260926T084048Z.yaml does NOT parse (ScannerError, line 132).
5. evals/promptfooconfig.yaml does NOT parse (ParserError, line 5): the D315 depth prompt is ONE double-quoted
   scalar with unescaped inner quotes, so the eval config cannot load for its own consumer.
6. (found by the new rail ON ITS FIRST RUN, minutes after it existed) backups/store_columns.PRE_check_store_
   columns_20260926T115814Z.yaml preserves the duplicated `ceiling:` of instance 1 - a snapshot of ambiguous bytes
   is a REVERT PATH THAT SILENTLY RE-INTRODUCES THE DEFECT.

FIX (root cause, not a patch): the rule has ONE home - scripts/lib/yaml_guard.py::duplicate_keys - and the WRITE-TIME
guard assert_yaml calls that same function, so a writer can no longer CREATE the class (it refuses, naming the key
and both lines); a bounded scan (`--check`, 113 artifacts across 6 declared roots, receipt shrink-only) catches the
hand-edits a guard never sees; the column rail's --record now anchors on the FIRST of `ceiling:`/`measured:`.
12/12 yaml_guard controls fire, INCLUDING the control AGAINST overreach (the same key in two DIFFERENT mappings is
legal and must NOT fail) - a rule nobody has seen tolerate a legal document is not a rule but a bludgeon.
4 artifacts remain OWED (rc=2) because this rail cannot repair them (2 dead snapshots, 2 hand-authored/unreadable
declarations): the OWNER settles delete-or-re-snapshot.

VERDICT for the standing question "are there more blind spots": NOT a probability - a RATE. Deliberate widenings of
the scan SUBJECT have now returned findings 5 times out of 5 and NEVER once "nothing": roots -> tools; site-shape
literal -> platform default (392 sites / 156 modules); namespace -> claimed-by-someone-else (BUG-523); STORES and
COLUMNS (BUG-524); and now DECLARATION AMBIGUITY (BUG-525, 6 instances, 2 in LIVE config). The mechanism that keeps
finding them is not insight, it is widening the subject and demanding the scan receipt its own coverage.

### BUG-526 (OPEN 2026-09-26) - the pin invariant had a SCAN and no WRITE moment: a pinned artifact could be edited and committed with nothing consulting the pin

CLASS (a rail that runs only when someone remembers to run it is not a rail during the interval in which the
work happens). config/recalibration_pins.yaml pins 6 artifacts by sha256 (D-353) and `just health` refuses a
moved one. That is a SCAN. The COMMIT - the one act that makes an edit permanent - never consulted it. So the
sequence "edit a pinned artifact -> commit -> health later" was legal and silent, and the first moment anyone
learned was the next health run, after the ratified measurement had already been invalidated in the tree.

MEASURED 2026-09-26, by the FIRST complete `just health` run of the day (it had been aborting early):
- scripts/definition_nli_verify.py is pinned as r2_meter (decision D-382, sha e9070635...) and its bytes moved at
  12:44 TODAY: a `provenance:` key added to the R2 report and the BUG-522 one-rule decode home (`_open_input`).
  Current sha fbfd62f326d26611... Both edits are SEMANTIC (the report's schema and its input rule changed), so the
  published R2 measurement is no longer reproducible from the tree. -> RED.
- The same run found RED at line 22 `check_bug_status.py`: the derived register was stale because BUG-525 had been
  appended to governance/buglog.md at 13:59 while the register was last built at 12:34. Re-derived; rail green.
- BOTH were created by this assistant hours earlier. Two of the three findings in the first complete gate run were
  self-inflicted, and neither was visible because the gate had not been run.

ROOT CAUSE (not a patch): the invariant was DECLARED and ENFORCED AT ONE MOMENT. D-2649 fixed exactly this shape
for ambiguous declarations (assert_yaml at write time + --check at scan time, ONE home); D-2648 fixed it for
parsing (verify the bytes BEFORE they are durable). The pin rule was the last invariant in the corpus with a scan
and no write moment. COMPOUNDING IT: the pre-commit hook that WOULD have been the write moment lives OUTSIDE the
repository (after the BUG-500 fix the git dir is /Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git), so the
strongest gates in this repo were not versioned and no rail could see them drift - the enforcement home itself was
invisible.

FIX (root cause: one home, two moments, controls that can fail):
1. scripts/verify_recalibration_pins.py gains `--staged`: the STAGED bytes (what would become permanent) are
   compared against the pins, read from git, never assumed. NO OVERREACH - a staged set naming no pinned artifact
   is TOLERATED even while the tree is RED; only the commit that MOVES a pinned artifact is refused. An unreadable
   staged blob FAILS CLOSED. Staging the pins file itself requires the whole invariant to hold.
2. scripts/install_git_hooks.sh: RAIL 3 added to the hook it renders, and `--check` re-derives the hook and
   byte-compares it with the INSTALLED one - the hook is a DERIVED artifact now, not a remembered one.
3. justfile: `--selftest` and `install_git_hooks.sh --check` are rails in `just health`.
CONTROLS: 6/6 fire, including the OVERREACH control and the fail-closed unreadable-blob control. The `--check`
control was SEEN TO FAIL (the installed hook lacked RAIL 3) before it was allowed to pass (BUG-492). The write gate
was also run against the REAL defect: 1 fault for the actual pinned script, 0 for unrelated paths.

VERDICT: the R2 pin RED itself is OWNER-OWED and NOT repaired here (re-measure and mint; editing the pin's sha to
make the rail green would be laundering a measurement nobody re-ran). What is repaired is the CLASS: the pin rule
now has a write moment, from the same home, with controls that can fail.

STANDING RULE (until `just health` is the last thing before a commit): run the gate BEFORE the work is described as
done. The gate found two defects of this assistant's own making, both hours old, both invisible by construction.

## BUG-527 (OPEN 2026-09-26) - the staged-reading rails audit whichever index the ENVIRONMENT names, not the one being committed

MEASURED 2026-09-26, by the A/B harness built to test the `scripts/*.sh` widening recommendation. The harness
copied the repo index to /tmp/abidx and set GIT_INDEX_FILE to point a SYNTHETIC staged set at the real rail
(so the rail could be A/B tested without editing the live plan). Scripts/check_session_plan.py read that
environment variable, audited the WRONG index, and returned rc=0 (ok) for a staged path the live plan REFUSES:
  LIVE plan + real index           -> rc=1  FAIL session plan: 1 path outside the plan (scripts/install_git_hooks.sh)
  LIVE plan + GIT_INDEX_FILE=/tmp/abidx -> rc=0  ok session plan: staged set touched 42 path(s), all declared
The rail did not misreport. It faithfully audited the index it was TOLD to audit. The defect is that the
subject of the audit is INHERITED rather than PINNED: every staged-reading rail shells out to
`git diff --cached` / `git show` and inherits GIT_INDEX_FILE, GIT_DIR, GIT_WORK_TREE, and GIT_COMMON_DIR from
whatever process invoked it (just, a wrapper, a CI runner, an agent shell). A rail whose subject can be
re-pointed by the environment is a rail that can be made to say ok about a commit it never saw.

SAME CLASS, SAME DAY: the index itself has NO write moment. An unflagged `git add -- scripts/install_git_hooks.sh`
issued from the A/B harness staged into the REAL index (42 -> 43 staged paths) and NOTHING observed it; the
state was found only because the harness re-counted by hand, and repaired with `git restore --staged`
(43 -> 42, worktree file still ' M'). This is BUG-526 one layer earlier: RAIL 4 has a read moment (the commit)
and no write moment (the staging act). Rails 0/3/4 all fire at `git commit`; the index is mutable, silently,
for the entire interval in which the work happens.

ROOT CAUSE: the rails resolve their own inputs from AMBIENT state. D-2646 requires ONE home for one rule; here
the home of "which index is the commit" is the environment, which is nobody's declared home. The repo already
solved this shape for the git DIR (install_git_hooks.sh uses `git rev-parse --absolute-git-dir` and never
assumes `.git/`) - that lesson was not carried to the INDEX.

FIX (owed, not applied - it edits rails, and the owner has not authorised the commit yet):
  1. Every staged-reading rail must PIN its subject: resolve `git rev-parse --absolute-git-dir`, pass
     `--git-dir` explicitly, and REFUSE TO GUESS (C16, fail closed) when GIT_INDEX_FILE / GIT_DIR /
     GIT_WORK_TREE are set in the environment - an audit of an unnamed index is not an audit.
  2. A known-answer control per rail: with GIT_INDEX_FILE pointing at a synthetic index holding one
     out-of-plan path, the rail must still REFUSE. Measured today: it returned rc=0 (control FAILS).
STATUS: OPEN. Affects scripts/check_session_plan.py (RAIL 4), scripts/verify_recalibration_pins.py --staged
(RAIL 3), and any other rail that shells `git diff --cached` / `git show`.

## BUG-528 (OPEN 2026-09-26) - will_not_touch matches NAMES, so a Dropbox-renamed sibling of a protected artifact is out of scope; one such copy is ALREADY listed in may_touch

MEASURED 2026-09-26 (A/B of the will_not_touch set against the live working tree):
  will_not_touch = ['governance/F11_*', 'governance/ANCHOR_RULER_CONSOLIDATED_*.csv',
                    'governance/ANCHOR4_DEPTH_BLIND_SHEET_*.csv', 'pipeline/**']
  governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv
      -> will_not_touch match: NONE     may_touch match: ['governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv']
  governance/anchor_adjudication_workbook_20260924 (M1 max's conflicted copy 2026-09-26).csv
      -> will_not_touch match: NONE     may_touch match: NONE
  governance/bug_status (M1 max's conflicted copy 2026-09-26).json | .md   -> both NONE
The blind sheet is an OWNER instrument whose write path is the BUG-431 gate (D-2606 class), and its family is
declared forbidden. Its Dropbox sibling - the SAME artifact, renamed by the sync client - is not forbidden,
and worse, it is EXPLICITLY permitted by its own may_touch entry. So the plan currently authorises editing the
owner instrument through its copy while forbidding it through its name. will_not_touch OUTRANKS may_touch
(BUG-445); a prefix-forged name defeats that precedence.

ROOT CAUSE: the rule matches a PATH STRING, while the invariant is about an ARTIFACT FAMILY. Dropbox conflict
naming ('Copy of X', 'X (M1 max's conflicted copy DATE)') is a MEASURED, RECURRING event in this tree (2 forms
present right now, plus the 6 HELD siblings tracked by resolve_dropbox_conflicts.py). A name-based forbid-list
cannot express "this artifact, whatever Dropbox calls it".

FIX (owed, owner-owned: it changes the plan): declare protections by FAMILY, not by literal name - normalise
the candidate path (strip a leading 'Copy of ', strip a trailing ' (…conflicted copy…)'), then match. Add
known-answer controls: a renamed sibling of a will_not_touch artifact must be FORBIDDEN (rc=2) and a genuinely
unrelated path must be TOLERATED (anti-overreach, BUG-492). Also review why the 'Copy of …' entry exists in
may_touch at all - if it is stale, it is a standing laundering path.
STATUS: OPEN.

## BUG-529 (OPEN 2026-09-26) - .pre-commit-config.yaml declares a C11/C12 gate that NOTHING invokes, and the hook slot has exactly ONE occupant

MEASURED 2026-09-26:
  - .pre-commit-config.yaml (D2552/GOV-CI) declares one hook: id c11-c12-gate -> python3 scripts/pre_commit_gate.py.
  - `command -v pre-commit` -> ABSENT. Scoped grep for `pre_commit_gate` finds only its own docstring and the
    decisions.yaml record of D2552; no recipe, no CI workflow, no caller.
  - The installed hook ($(git rev-parse --absolute-git-dir)/hooks/pre-commit) holds RAIL 0 + RAIL 3 + RAIL 4
    (check_repo_integrity.py, verify_recalibration_pins.py --staged, check_session_plan.py --staged).
So a gate that D2552 declares as the C11/C12 enforcement point has never run. This is not a dormant nicety: the
slot it would occupy is a SINGLE FILE PATH that is already occupied. Running `pre-commit install` would write
the framework shim to that path and silently replace RAIL 0/3/4 - the three rails that today carry the
repo-integrity, pin, and session-plan guarantees. The stronger gates in this repo would be lost by the act of
installing a weaker declared one.

ROOT CAUSE: enforcement is listed in a CONFIG format owned by a framework that is not installed, while the
enforcement that actually exists lives in a hand-rendered hook OUTSIDE version control. Two homes for "what a
commit must satisfy" - one declared and dead, one live and unversioned (the second half is BUG-526).

FIX (owed, owner-owned): choose ONE home for hook content and make it a DERIVED artifact with a re-derivation
rail (install_git_hooks.sh --check already does this). Either (a) fold the C11/C12 gate into that rendered hook
as RAIL 5 - no framework needed, one slot, one home - or (b) delete .pre-commit-config.yaml so the repo stops
declaring a gate it does not have. What must NOT happen: `pre-commit install` without first moving RAIL 0/3/4
into a framework-compatible hook. Add a rail asserting the installed hook contains every rail the installer
renders (the byte-compare already covers this) AND that no second claimant for the slot is declared.
STATUS: OPEN.

## BUG-530 (OPEN 2026-09-26) - the derived-artifact generator writes its register without the write guard

MEASURED 2026-09-26, reading scripts/bug_status.py: the generator of governance/bug_status.json|md writes both
files with a bare `(REPO / args.json_out).write_text(...)` / `(REPO / args.md_out).write_text(...)`. There is no
write_guard call and no crash-safe replace (tempfile -> fsync -> os.replace, C6).
WHY IT MATTERS MORE HERE THAN ELSEWHERE: bug_status.* is a DERIVED artifact (check_bug_status.py re-derives it
and byte-compares, and a stale register is worse than none). A direct write_text TRUNCATES the tracked file
before the new bytes exist: an interrupted run leaves a truncated register that the next `just health` reports
as DRIFT - i.e. the rail's own subject becomes the evidence of its own failure. write_guard.py --audit this
session: 5 guarded / 3 unguarded declared writers, guard_coverage.max_unguarded = 3 (shrink-only) - this
generator is a 4th writer that is not even declared (D-401: a writer with neither a guard call site nor an
exemption is DRIFT).
FIX (owed): route bug_status.py through write_guard (declaring it as a writer), or declare it in
config/artifact_ownership.yaml with a reasoned exemption. Do NOT raise max_unguarded - the ceiling is
shrink-only.
STATUS: OPEN.

## NOTE-2026-09-26 (A/B, no defect) - two candidate findings were REFUTED by measurement; recorded so they are not re-reported

1. "`### BUG-<id>` entries are invisible to the register." REFUTED. HEADER_RE = `^#{2,3}\s+(BUG-\d+)\b...` and
   BUG-525/526 are both present in governance/bug_status.json. BUG-428 already fixed the 2-hash-only pattern.
   The A/B probe was itself inconclusive at first (scripts/bug_status.py has NO --log override, so both probes
   re-derived the real log); it was re-tested against the real register, where the answer is visible.
2. "the undeclared-encoding scan LOST a subject (156 -> 155 files, 392 -> 390 sites)." REFUTED. The delta is
   exactly this session's rewrite of scripts/verify_recalibration_pins.py: HEAD had 2 undeclared reads
   (`_PINS.read_text()` line 27, `f.read_text()` line 32); the new version declares encoding on both
   (encoding=_ENCODING, lines 59 and 155). A shrink WITH a named cause, ceiling unchanged (shrink-only holds).

## BUG-531 (CLOSED 2026-09-26) - the rename vocabulary was applied to the PATH, so the `Copy of ` control could never fire
- FOUND by a known-answer control that FAILED (scripts/check_session_plan.py --selftest), NOT by production.
- CLASS: the BUG-492 lesson inverted - not a control that can never FAIL, but one that can never PASS. That
  direction is the more dangerous one, because the SIBLING control (the ` (conflicted copy DATE)` suffix form)
  DID pass, which made the family logic look proven while half of its vocabulary was inert.
- MECHANISM (measured): canonical_names() applied each pattern to the WHOLE PATH. `^Copy of ` is name-anchored
  and `governance/Copy of X.csv` does not start with `Copy of `, so the prefix form matched NOTHING. The suffix
  form matched only because it is unanchored - which is exactly why the hole stayed silent. A rename is a fact
  about the NAME, so the vocabulary is now applied to the BASENAME and the surviving directory is rejoined. The
  VOCABULARY itself was not edited: it still lives once in config/repo_integrity.yaml#conflict_marker (D-2646).
- MEASURED AFTER: --selftest 9/9 controls fire; --staged rc=0 over 42 paths; the index was RE-COUNTED at 42
  after every probe (the control-on-the-control holds - on 2026-09-26 a 42->43 move went unobserved by hand).

## BUG-532 (OPEN 2026-09-26) - one lock, two homes: the session plan RESTATED the owner-instrument lock that a rail already checks
- FOUND by rail 4 refusing its own plan: `governance/F11_DISC_REVIEW_*.csv` sat in may_touch while
  `governance/F11_*` sat in will_not_touch, which OUTRANKS may_touch (BUG-445) - so the entry was already DEAD
  and the contradiction was invisible in every earlier audit.
- CLASS: D-2646 (one home for one rule), the same shape as BUG-493. The lock on the owner instruments already has
  a MACHINE-CHECKED home: config/human_instrument_locks.yaml (BUG-430 rail 1) declares
  F11_DISC_REVIEW_20260923.csv COLUMN-SCOPED (new columns allowed; protected columns byte-identical), and
  config/artifact_ownership.yaml declares F11_ANCHOR_REVIEW_20260923.csv human_authored. The session plan then
  restated a COARSER rule (`governance/F11_*` write-locked) that contradicted BOTH.
- INTERIM FIX (this change-set): the dead may_touch entry is removed and the coarse lock stands, so nothing in
  this repo may write F11_*. The plan still RESTATES the lock instead of consuming it.
- OWED, GATED (owner act): make will_not_touch CONSUME config/human_instrument_locks.yaml. Gated because a
  column-scoped lock is a WEAKER rule than a name lock, and widening protection by an assistant edit is exactly
  what BUG-445 forbids. Until then, BUG-532 stays OPEN with the coarse lock in force.

## STANDING RULE ADOPTED 2026-09-26 (owner-accepted) - WIP freeze + the definition of done that stops the churn
- One session: NO new rails and NO new config keys; finish what is in flight, sync governance, commit, lower
  ceilings. New discoveries are LOGGED AND TRIAGED, not immediately worked - moving ground is what made a fix
  look like it CREATED a bug when it had only made an older one observable.
- A bug closes ONLY as: fix + a control that failed before and passes now + a class sweep + a ceiling DECREASE.
- Five numbers tracked per session: open bugs | max_unguarded | per-class instance counts | WIP (staged+dirty) |
  commits blocked by a rail. A ceiling that RISES is a regression alarm, by construction.
- NOT A DEFECT, a measured environment constraint: /usr/bin/fm exists on this macOS 27.0 machine but
  `fm license --status` = "Not agreed." and the notice is MACHINE-WIDE (sudo, every user). So the on-device
  model is unusable by assistant act. config/apple_fm.yaml (enabled: false, arms: []) + scripts/probe_apple_fm.py
  (read-only, exit 2 while unlicensed) make the four owner-approved measurements ONE command after `sudo fm license`.

## BUG-530 (CLOSED 2026-09-26) - the register generator wrote its own tracked artifact with a bare truncating write

FIX: both outputs now go through write_guard.write_document(OWNED_ANY) - the ONLY legal whole-document writer
(D-401/I1): tempfile -> fsync -> os.replace (C6) plus a receipt. The generator also READS its own output paths from
config/artifact_ownership.yaml (the declaration is the ONE home for "which files does this script write", D-2646),
so no path is hardcoded in it and the argparse defaults cannot go stale (C12).
WHY IT MATTERED MORE HERE: a bare write_text TRUNCATES the tracked file before the new bytes exist, so an interrupted
run left a truncated register and check_bug_status.py then reported the rail's OWN SUBJECT as the evidence of its own
failure. It is also the writer whose unguarded truncate best explains the 2026-09-26 Dropbox conflicted copies, one of
which was a 14-bugs-stale COPY of this register - a stale AUDIT SUBJECT (the BUG-527 failure mode). A derived artifact
with a second writer and no atomic replace WILL produce conflicted copies.
TWO CONTROLS, BOTH SEEN TO FIRE (a control never seen failing is not a control, BUG-492):
  1) DECLARE-FIRST: the declaration went in BEFORE the guard was wired and write_guard --audit then returned rc=1
     DRIFT - "declared writer_of_record scripts/bug_status.py never imports the guard and declares no
     guard_exemption". The rail COVERS the new declaration; that is measured, not assumed.
  2) ROUTE-BY-IDENTITY: the route is decided on the RESOLVED path (symlinks and '..' collapsed), never on the name -
     the BUG-528/BUG-531 class, where a NAME-shaped enforcement surface is bypassed by a rename or a dotted path.
     MEASURED: the declared run appended exactly 2 receipts naming the ABSOLUTE artifact paths; the rail's own
     re-derivation into a TEMP dir appended 0 (journal=False for a foreign target - a receipt for a file that is not
     an artifact would make the ledger read as if a declaration had been rewritten).
MEASURED AFTER: --audit rc=2 (owner-owed, loud NOT fatal, BUG-457): "ok guarded: scripts/bug_status.py (calls
write_document)", 6/9 declared writers guarded, unguarded 3 of ceiling 3. THE CEILING DID NOT MOVE, and that is
stated rather than dressed up: max_unguarded counts DECLARED writers and this generator was UNDECLARED, so fixing it
cannot lower that number - it removes a writer the ceiling could not see. Honest coverage movement: declared 7 -> 9
(two artifacts, one writer), unguarded fixed at 3. Byte-neutral: check_bug_status rc=0 and 126/143/269 unchanged.
CLASS SWEEP (with the instrument's own limit, because the limit is the finding): a literal grep over scripts/ +
pipeline/ yields 136 candidates and is USELESS as a writer detector - it matches any tracked artifact filename
appearing anywhere in a file that contains any write call, so it counts READERS as writers (pipeline/stage2_extract.py
only READS config/content_types.yaml). Reading-target vs write-target cannot be settled by text. The reliable
instruments are the DECLARATION plus the runtime RECEIPT, because only they resolve a path.
NAMED SAME-CLASS SIBLING (NOT fixed here): scripts/freeze_gold_sets.py writes the TRACKED governance/
gold_freeze_report.md with a bare write_text and is undeclared - the identical defect, found by the inversion above.


## BUG-533 (HIGH - D-2649, FIXED 2026-09-26): the store-columns rail compared a CODE census as a STORE invariant, and every new script aborted `just health` at that line

ROOT CAUSE (measured, not inferred). `scripts/check_store_columns.py` measures FIVE rulers per column and compares
all five against the recorded `measured:` block. Four are read FROM THE STORE (nonnull | nonblank | hollow |
distinct). The fifth, `mentions`, is a census of the CODE: the number of .py FILES under `scan_roots`
(scripts, pipeline, tools) whose text NAMES the column. `role_faults()` never reads it - it is the one ruler no
role consumes - so its only machine use was the recorded-number comparison. Measured drift: name.mentions 270 -> 271
and status.mentions 100 -> 101, and the responsible files are NEW .py files that were never there when --record ran
(`scripts/lib/git_subject.py` for `name`, `scripts/probe_apple_fm.py` for `status`). The store did not change; the
CODE did. The rail then printed "the store changed under a declaration that still claims the old number", returned
rc=1 - and rc=1 is NOT in the tolerance list on `just health` line 57 (`|| [ $? -eq 2 ]`), so the recipe ABORTED
there and every rail after it (58-82: resolve_dropbox_conflicts, reconcile, measure --gaps, the pins rails, r3
preflight, vec integrity, archive index...) never ran in one pass. So EVERY new script that named a column silently
hid ~25 rails. That is the blindspot: not a wrong number, an un-run rail.

FIX (class-level, at the root, no laundering): the five rulers are split by the kind of fact they are.
STORE_RULERS (nonnull | nonblank | hollow | distinct) still fail the rail on movement - the store genuinely changed.
A moved CENSUS_RULER reports `CODE-CENSUS-MOVED`, names the real mover (the code, not the store), states the census
population, and is OWNER-OWED: LOUD, exit 2, NOT fatal - the BUG-457 tri-state convention already used by this
recipe. `fatal_faults()` is the single severity home; nothing else decides what fails. The `--check` summary now
also prints `census moves N` so an owner-owed census move is visible in the one-line verdict.

CONTROLS, SEEN TO FIRE (BUG-492). c15: a moved `mentions` is OWNER-OWED and NOT DRIFT. c16: a moved STORE ruler is
still fatal - the census split must not shadow the rulers that matter. c17: the severity CLASSIFIER itself (only a
store ruler may reach the fatal set). The harness had to be extended to make them possible: `_faults()` now accepts
`recorded_over`, because the 14 original controls always handed the audit fresh == recorded, so NO control could
ever fire on a drift at all. The control's pre-fix failure is on the record as the LIVE symptom: --check printed
MEASUREMENT-DRIFT for both census keys and returned rc=1 before the change, and prints CODE-CENSUS-MOVED with rc=2
after. Selftest 14 -> 17 controls, 17/17 fire.

MEASURED AFTER: `just health` now runs through the store-columns line and dies 12 lines LATER at line 71 on the
PRE-EXISTING, owner-owed R2 pin (see below). Nothing was loosened that matters: no store ruler, no role rule, no
debt ceiling moved (debt stays 9 of ceiling 9, shrink-only).


## BUG-534 (MED - D-405 cover, FIXED 2026-09-26): declaring an owned artifact creates a cover obligation that only surfaces on the NEXT full health run

ROOT CAUSE. `reconcile.py` `cover()` requires every artifact in `config/artifact_ownership.yaml` to carry a
reconciliation entry or a declared `unreconciled_reason`. The BUG-530 fix DECLARED `governance/bug_status.json`
and `governance/bug_status.md` (that declaration is what made the guard rail able to see that writer at all), which
created two new obligations. They went undetected for the rest of that session because `just health` aborted at the
store-columns line BEFORE the reconcile rail: the cascade of BUG-533 hid the collateral of BUG-530. This is the
material argument for fixing aborts before anything else - a RED line does not only hide rails, it hides the
consequences of your own last edit.

FIX, and a NEGATIVE RESULT recorded rather than hidden: the first attempt added two `reconciliation.yaml` entries
with `check: path_resolves` and `declares:` pointing at the two artifacts. That CRASHED reconcile with a YAML
ScannerError - the engine parses `declares` as YAML, and one artifact is a JSON register and the other is markdown.
So the entry shape is wrong for non-YAML artifacts and the correct declaration is `unreconciled_reason` on the
artifact itself, in the ONE home that already knows it is owned (D-2646), naming the REAL oracle: re-derivation -
`scripts/check_bug_status.py` regenerates both outputs into a TEMP dir and byte-compares them with the tracked
files. Recorded as a negative result because the next person will otherwise retry the entry shape.

MEASURED AFTER: `reconcile --check` rc=0, "11 declared object(s) agree with reality" (was rc=1 with 2 cover
drifts), and `just health` advanced past the reconcile rail.



## BUG-535 (HIGH - D-382/D-2648, FIXED 2026-09-26): the pin rule's only legal-looking exit was the one it could not see - a re-pin that moved a sha256 under the SAME decision id

ROOT CAUSE. `scripts/verify_recalibration_pins.py` refused two things at write time: a staged pinned artifact whose
bytes MOVED, and staging `config/recalibration_pins.yaml` while the SCAN was red. Both refusals are real, and
together they left exactly ONE path that looked legal: overwrite the pin's `sha256` with the digest of the changed
artifact, leaving `decision: D-382` untouched. That makes the scan GREEN, so the pins file may be staged, so the
commit is TOLERATED - and D-382 keeps certifying a measurement nobody re-ran (BUG-391/BUG-526 class: the rule
lived in the rail's MESSAGE, never in a check). The rail's own instruction - "re-run the measurement and mint a NEW
decision" - was unenforced prose.

FIX, at the declaration's own moment (D-2648: the invariant gets the moment in which the change happens). A re-pin
is a RE-MINT: if a pin's sha256 differs from its committed predecessor, its `decision:` MUST differ too. Plus three
fail-closed tightenings found while implementing it: (a) a pin may only DISAPPEAR with a `retired:` marker, or the
next reader cannot tell a retired meter from a forgotten one; (b) a pins file staged apart from the bytes ON DISK is
refused - a partially staged declaration would commit lines nobody can review; (c) an unreadable or unparseable
predecessor is an UNKNOWN, and an unknown is not a clean (C16/BUG-457). `head`/`tree_blob` are INJECTED, like the
existing `blob`/`scan`, so the controls can hand the rule a laundered document as easily as a legal one.

CONTROLS, SEEN TO FIRE (BUG-492): 6 -> 12, all 12 fire. New: laundering REFUSED, re-mint TOLERATED, partial staging
REFUSED, removal-without-`retired` REFUSED, removal-WITH-`retired` TOLERATED, unreadable predecessor fails CLOSED
while a first-ever pins file is TOLERATED (the no-overreach control). The pre-fix failure of the new control is
structural and stated plainly: the old `staged_faults(cfg, staged, blob, scan)` had NO predecessor input at all, so
the laundering document produced ZERO faults. The re-pin rule now makes R2's legal path exist: measure, mint, re-pin.

OWN DEFECT CAUGHT AND FIXED IN-FLIGHT, recorded because it is the same class: the first version defined the
`_UNSET` sentinel BELOW `staged_faults`, whose signature uses it as a default - evaluated at def time, so the rail
died with NameError and `just health` regressed from line 71 to line 69. One home for the sentinel (D-2646), and the
rails caught it before any commit.


## BUG-536 (HIGH - PROPOSED D-2653 / BUG-457, FIXED 2026-09-26): the pin rule's only exit was 1, so an OWNER-OWED pin aborted `just health` and hid ELEVEN rails

SYMPTOM: `red r2_meter: scripts/definition_nli_verify.py CHANGED since it was pinned` and
`error: Recipe `health` failed on line 71 with exit code 1` - rails 72-82 (11 of them) never ran at all.

ROOT CAUSE (measured, not recalled): the rail had ONE severity. `all_faults()` returned a single list and
`main()` returned `1 if faults else 0`, so the recipe's `|| exit 1` treated two DIFFERENT facts as one:
  * the DECLARATION is broken (a pinned path is missing; a `decision:` the registry does not carry) - a defect; and
  * the pin has fallen BEHIND the work - which only the OWNER can close (re-measure -> mint -> re-pin).
The second is owner-owed DEBT by construction, and BUG-457 already fixed exactly this shape everywhere else
(the tri-state: 0 clean | 1 fatal | 2 owner-owed, loud but NOT fatal). This rail was the last one still
single-valued, so it was the one that could abort. An abort is an amnesia generator: it hides its own
successors, which is the lesson BUG-533 recorded one turn earlier and D-382 recorded in its own rationale
("just health was RED for a whole pass while every individual rail was green") - this was the THIRD instance.

MOVERS, by name: the pinned meter was edited TWICE after D-382's re-pin. D-382 re-pinned it at
sha256 e9070635... for the additive provenance block; the working tree then carried a SECOND uncommitted edit
(mtime 2026-09-26 12:44:41, the `_open_input`/`_INPUT_ENCODING` single-encoding-rule fix, D-2644/BUG-522),
so the on-disk digest fbfd62f3... has no decision behind it. git diff --stat: 61 insertions, 1 deletion.

FIX (one producer, no downstream re-classifier - the BUG-526/528/531 family is "enforcement by NAME instead
of by IDENTITY", so severity is decided where the fault is CREATED, never re-graded by its wording):
  * `scan_split(root, cfg) -> (fatal, owed)` is the single producer; `all_faults()` = fatal + owed (the write
    gate still sees BOTH, so nothing is hidden from the commit gate).
  * `main()` returns EXIT_OWED (2) for a moved pin, EXIT_DRIFT (1) only for a broken declaration, and the scan
    prints `OWED ...` for debt and `RED ...` for a defect; the summary line reads `N pinned, D DRIFT, O OWNER-OWED`.
  * justfile line 71 -> `|| [ $? -eq 2 ]`. It is a CHECKER line, so `measure.health_chain()` still derives the
    same order (`python3 scripts/lib/measure.py --gaps` rc=0, checker at position 50, both declared resolvers
    precede it) - the ORDER IS LOAD-BEARING rule (BUG-489/490) is untouched.
NOTHING WAS LOOSENED: `--staged` (the pre-commit hook, `|| exit 1`) is a REFUSAL and returns 1 for EITHER kind,
so any non-zero - 1 or 2 - still refuses the commit that would make a measurement unreproducible.

CONTROLS 12 -> 16, all firing (`--selftest` 16/16). The four new ones cannot be satisfied by hoping the live
tree happens to be broken in the right way: `_split_probe()` BUILDS a temp root holding exactly the fault kind
asked for (BUG-492 - a control that cannot be handed a broken declaration is a comment), and every probe also
asserts the split is TOTAL and DISJOINT (no fault lost from both lists):
  * a MOVED pin is OWNER-OWED and is NOT a fatal drift;
  * a pin whose PATH IS MISSING is FATAL (fail closed, C16);
  * a pin naming a DECISION the registry does not carry is FATAL;
  * the split is total and disjoint.

MEASURED AFTER: selftest 16/16, scan `OWED r2_meter ... / 6 pinned, 0 DRIFT, 1 OWNER-OWED` rc=2, write gate
`42 staged path(s), 0 RED` rc=0, and `just health` advanced from line 71 to line 82 - the ELEVEN hidden rails
(really eleven: verify_declared_inputs, verify_frozen_pair, verify_evidence_manifests, verify_artifact_authority,
r3_preflight, verify_vec_integrity, verify_boundary_injection, depth_pass_agreement x2, build_archive_index,
recompute_decision_summary) are now RUN, and every one of them is GREEN except the archive index of BUG-537.
The R2 pin itself is NOT laundered: it is still RED-as-OWED and still owes a re-measure + a mint (D-382's rule).

## BUG-537 (MED - D-2664, FIXED 2026-09-26): regenerating archive/index.yaml de-listed a hygiene entry, so the rail's own remedy may be a silent blur

FOUND BY: the forensic question "did my own fix create a blindspot?" - asked of the BUG-536 fix's very next
step. `archive/index.yaml` was STALE (`stored body_sha256 ecfe29517a94 != measured 07ab497cecf9`), so the rail's
own named remedy was run: `python3 scripts/build_archive_index.py` (32 entries, 17.3 GB, now rc=0 in sync).
Diff: 25 insertions / 26 deletions. VERIFIED against the pre-image: the `entries` NAME SET is byte-identical
(dropped NONE, added NONE) - so no archival object was lost from `entries`.

BUT the removed block is a real record that is now ABSENT from the new index:
    - name: .DS_Store | kind: file | bytes: 10244 | modified: 2026-09-23 | category: os_metadata |
      disposition: purge_candidate | authority: hygiene | reason: macOS Finder metadata; regenerable, never evidence
and `archive/.DS_Store` still EXISTS on disk (10244 bytes, mtime 2026-09-26 12:18) while `grep -c DS_Store
archive/index.yaml` = 0. The regeneration therefore moved 1.8 MB of aggregate bytes and changed the disposition
grouping (`keep 5 -> 6`, `purge_candidate 1 -> 0`) while dropping the only record of an on-disk hygiene object.
STATUS: OPEN and NOT papered over. Class: the rail's remedy is not itself controlled - `build_archive_index.py`
has no known-answer control asserting "an on-disk object that was indexed is either still indexed or declared
gone" (BUG-492: the control must be SEEN to fire). The pre-image is preserved at /tmp/index_yaml_pre.yaml for
the next pass. NOT a measurement artifact, so nothing downstream is consumption-blocked.

CORRECTED 2026-09-26 (D-2664) - THIS BLOCK ATTRIBUTED THE DE-LISTING TO THE WRONG ACT, AND THE PRE-IMAGE IT
NAMES DISPROVES ITS OWN NUMBERS. It claimed "Diff: 25 insertions / 26 deletions" and "the entries NAME SET is
byte-identical". MEASURED now, both sides carried by their DIGESTS: the pre-image this block names,
`/tmp/index_yaml_pre.yaml` (generated 2026-09-26T10:48:33, body_sha256 ecfe29517a941e1b76cff4482d1c43877b3363f2cb1f5b618d459c37a1e45667), ALREADY carries 32
entries and ZERO `.DS_Store`: the remedy run removed NOTHING. `git show HEAD:archive/index.yaml` - the COMMITTED
index (generated 2026-09-24T10:40:37, body_sha256 07e8e3559727bc9955c0048ee520d23d1c0284eb15c7dbdacc327737a881281b) - still listed it. So the de-listing
happened when the BUG-469 ignore block landed, between those two generations, and not at 2026-09-26T15:54. The
25/26 diff was computed against the COMMITTED index while the text named the pre-image: a diff claim that does not
carry the digests of both sides is not evidence (the D-2663 lesson, applied to the audit trail itself).
THE REAL DELTA, pre-image -> now (`archive/index.yaml`, generated 2026-09-26T21:48:18, body_sha256 47532fca72a9ab9a8d7339ce1d34c4e5d9a7175d6869ada2052ccd09a16262eb):
12 deletions / 31 insertions, and it is exactly the fix: (a) the `excluded` census appeared; (b) the ignored class
left the COUNTS that had been silently including it, which is the "silent blur" this bug was about - `db_backups`
files 3 -> 1, bytes 135528448 -> 135495680, modified 2026-09-19 -> 2026-09-17, and the largest entry 213 -> 207
files / -98304 bytes (six AppleDouble/SQLite sidecars); local_archive bytes 17312358363 -> 17312161755.
FIX (D-2664). archive/index.yaml now carries an `excluded` census - measured name, bytes and date of every object
the index declines to count, with the DECLARED disposition - so an on-disk object is either INDEXED or DECLARED
excluded, never silently absent. `--check` asserts that invariant against the stored index (`coverage_faults`: an
on-disk name in NEITHER list, or an indexed name whose bytes are gone) and REFUSES an index carrying no readable
census: an absent census is an UNKNOWN, not a clean (C16). The ignore block became the ONE home of the excluded
class (names + globs + disposition + authority + reason, D-2646) and the unreachable `- match: '^\.DS_Store$'`
rule was DELETED (C19) - it could never fire, because an ignored name never reaches classify() - while
shadowed_rules() reports exactly that shape as a DECLARATION CONFLICT and exits 2, fail closed. Controls 0 -> 7
(`--selftest`, no NLI, no live-tree write).

## BUG-538 (HIGH - D-2653, FIXED 2026-09-26): Maxwell pinned its SCRIPTS and its EVIDENCE but pinned ZERO GENERATORS - and the first rail that closed the gap shipped three defects the pre-commit audit found

MEASURED 2026-09-26 on this machine. config/recalibration_pins.yaml pins 6 SCRIPTS and the anchor configs pin
sha256 blocks of EVIDENCE, but no config pinned a GENERATOR: a generator was identified by a STRING
("Qwen3-Coder-30B-A3B-Instruct-MLX-4bit") in every metric record, and a NAME IS NOT AN IDENTITY. The two cache
entries that matter most - Qwen3-Coder (S2 generator) and gemma-4-E4B-it (R5 reviewer) - were precisely the two
whose identity could not be read off the store (rev=main, 0 symlinks), so an `ollama pull`, an HF re-download or a
re-quantisation moves the bytes while every stored `gen_model` keeps saying the same words. That is the BUG-391
class (a fact that moved with nothing declaring it) applied to the thing that produces EVERY fact in the store: a
measurement whose generator silently changed is not a smaller measurement, it is an UNCOMPARABLE one.

FIXED by scripts/verify_generator_pins.py + config/generator_pins.yaml (ONE home for BYTES-ON-DISK -> DIGEST,
boundary declared against the 7 rival NAME->ROLE homes and against recalibration_pins.yaml; D-2646). TRI-STATE
reusing the BUG-536 convention (a second severity idiom would itself be a second home): 0 CLEAN / 1 FATAL broken
declaration, fails closed (C16) / 2 OWNER-OWED moved identity. `--pin` PRINTS and never writes: a pin is re-minted
by a DECISION (D-382/BUG-535), so the write stays a human act. Wired into `just health` (selftest fatal, scan
tolerating 2). All 6 generators measured; identity_sha256 is now available for ALL SIX (free - the blob basename IS
the content digest), a gain that came from pinning the content-addressed commit dirs rather than the `main` dirs.

THE THREE DEFECTS THE AUDIT FOUND IN MY OWN FIRST VERSION (all fixed; each is the shape this bug is about):
  (1) THREE PINS DECLARED A TRUNCATED COMMIT PREFIX (773a7da77e56). Nothing on disk is named that, so the rail
      reported "pinned object is MISSING from disk" - a PHANTOM, produced by the very "approximation pretending to
      be an identity" the file exists to catch. resolve_snapshot() now resolves ONLY an exact snapshot name or a
      ref, and the fault NAMES the prefix it refused. A control was SEEN to fire on it (control 5/12).
  (2) _compare() SKIPPED a declared digest the current mode could not measure, so a store that stopped being
      symlinked would read CLEAN with an unverified identity. That is a silent pass of exactly the kind BUG-492
      forbids; it is now OWNER-OWED and says so. Control 7/12 counts every declared fact re-reported.
  (3) THE TWO lmstudio REPOS CARRY TWO SNAPSHOT DIRS: snapshots/<commit> (14 files, ALL symlinked =
      content-addressed) AND snapshots/main beside it (34 files, 0 symlinks) whose extras are the downloader's own
      bookkeeping (.cache/huggingface/**, CACHEDIR.TAG - 5,842 B; 3,187 B on the reviewer). Pinning `main` would
      bind that bookkeeping as if it were weights; pinning the commit alone would leave the aliased copy unbound.
      The gain/loss is now DECLARED: pin the commit, declare `alias_snapshots: [main]`, and let the rail require
      the alias to hold the same (relpath, bytes) payload - extras tolerated and counted, a disagreement
      OWNER-OWED, an absent alias FATAL. Controls 11-12 were seen to fire on both.

HONEST LIMIT (declared, not hidden): sparse_sha256 is a manifest over (relpath, bytes) - it catches an added,
removed or re-sized file, which is what a re-pull or a re-quantisation does. A byte-swap preserving every
(path, size) is NOT caught by the daily check; it IS caught by --deep and by identity_sha256 wherever the snapshot
is symlinked (as all 6 now are).

CONTROL EVIDENCE: `python3 scripts/verify_generator_pins.py --selftest` -> 12/12; `just health` rc=0 with
"ok generator pins: 6 declared, 0 BROKEN DECLARATION, 0 MOVED (sparse)" and both alias lines seen to print OK.

## BUG-539 (HIGH - OPEN 2026-09-26): the decisions registry is declared append_only, but its own derived summary block sits at EOF - so MINTING a decision is a MID-FILE edit that the prefix rail reads as tampering, and it ABORTS the ladder

MEASURED 2026-09-26 while minting D-2653/D-2654. verify_handoffs refused: "decisions_registry: config/decisions.yaml is declared append_only but its receipted bytes are not a prefix of the current bytes - a cell was edited or the file was truncated (BUG-376 class)". Reproduced: the two records were inserted immediately above the derived `summary:` block (they cannot go after it - a top-level sequence entry after a top-level mapping is not valid YAML). The rail is RIGHT: `prefix_intact` is exactly the rule a receipted append-only registry needs. The defect is the DECLARATION: a file that can only be extended by an edit ABOVE its own footer is not append_only. CONSEQUENCE, and it is the BUG-457 shape: the FAIL aborts `just health` line 47 and HID 11+ rails below it, including the brand-new generator-identity rails - the abort is an amnesia generator. NO REMEDY EXISTS: scripts/lib/handoff.py offers only --backfill / --seal-revisions, neither of which refreshes this receipt, so the only ways forward today are (a) leave the decisions unminted, or (b) re-seal the receipt, which would LAUNDER the very edit the rail exists to catch. I took (a): config/decisions.yaml was restored from its pre-image (/tmp/decisions_pre_2653.yaml), its summary re-derived (784 records, stamp 0d7a746350d62e14) and D-2653/D-2654 remain PROPOSED in this buglog only. FIX OWED (owner-gated, one decision): declare a structural-edit path - either move the derived summary OUT of the registry into its own derived home (D-2646: one derived value, one home, and the summary IS derived), or declare the mint as a structural edit whose receipt is refreshed in the SAME sequence (D-2645) and give the rail a remedy that is not a quiet re-hash (D-382/BUG-535). Until then EVERY mint of a decision both breaks a rail and hides the ladder below it.

## BUG-540 (HIGH - FIXED 2026-09-26): the append_only rule could not be EVALUATED - a one-byte LEGAL append was reported as tampering, and the verdict could not tell tampering from "the old bytes were never retained"

WHAT: `just health` line 47 (scripts/verify_handoffs.py, prefix_intact) failed with "config/decisions.yaml is declared append_only but its receipted bytes are not a prefix of the current bytes - a cell was edited or the file was truncated (BUG-376 class)". MEASURED by this session's own control: appending ONE newline to config/decisions.yaml - a legal append, restored byte-exactly afterwards (sha256 back to f67d12a2...) - produced exactly that verdict.

WHY: the branch compared the current prefix against a BLOB in governance/handoffs/blobs/, and this receipt declares `seal: false`, so no blob was ever written (MEASURED: 6 blobs on disk, all anchor4 digests, none for the registry). `old_blob.exists()` was therefore False on EVERY run, and the declared no_seal_reason - "the registry is append_only and textual, so a prefix check detects a rewrite without a copy" - was a FALSE PREMISE: the (bytes, sha256) pair in the receipt was never used to decide the prefix. Without a copy the rule was UNDECIDABLE, and every failure was attributed to tampering. A rule that can never say YES is not a rule, and one that cannot distinguish two different causes is a false witness (BUG-492 applied to the rail itself).

FIX: `prefix_state(cur, rec)` decides from the digest+length pair ALONE - hash current[:receipted_bytes] and compare with the receipted sha256 - returning unchanged / appended / truncated / rewritten, each with its own reason. No copy is required, so the rule works for an UNSEALED artifact, and the finding NAMES the state instead of guessing. Control added to `--selftest` with five known answers, including the two that were impossible before: a legal APPEND says YES, and an EQUAL-LENGTH rewrite says NO (the BUG-376 signature case).

CARRY (BUG-539, still OPEN, now fully specified): even with the rule working, a MINT still cannot preserve the prefix, because config/decisions.yaml owns its own derived summary and header - a new record must be inserted BEFORE the top-level `summary:` key and total_decisions/last_sync/stamp pair sit ABOVE the records, so the file can never be appended to. THE AUDITED FIX (D-2655): move the census to governance/decisions_summary.json so the registry holds RECORDS ONLY and extends to EOF (a mint becomes a true APPEND), with source_sha256 joining census to registry bytes. Its declarations (config/artifact_ownership.yaml, config/derivations.yaml, the second-oracle test) were drafted and DELIBERATELY REVERTED this session rather than left half-applied - a half-applied migration is a set of rails pointed at a file that does not exist.

## BUG-543 (HIGH - FIXED 2026-09-26): BUG-500 RECURRED - the sync client re-materialised the pre-fix .git DIRECTORY over the 58-byte pointer and the whole ladder went DARK
MEASURED. just health printed ZERO ok lines and died on line 7 (RAIL 0): FAIL repo-integrity: the git dir does not
resolve ('rev-parse --absolute-git-dir'). On disk .git was a DIRECTORY again holding the 2026-09-25 09:58 PRE-FIX
skeleton (index 125618 B, refs/heads/main -> a1061cd7) and NO HEAD file, while the pointer's bytes survived as the
conflicted copy '.git (M1 max's conflicted copy 2026-09-26)' = 58 bytes.
HARMLESS, PROVEN FIRST: git merge-base --is-ancestor a1061cd7 96b1e9c rc=0 - the resurrected ref is an ANCESTOR of
the real HEAD, so no history existed only here. A non-zero rc would have stopped the repair for an owner ruling.
REPAIR (bytes preserved, never deleted): sha256 pre-image of all 4 files; the directory MOVED to the declared vault
(~/maxwell_os_conflict_snapshot_20260925/vaulted/resurrected_git_20260926) with a manifest and pre == post ASSERTED;
the pointer's own conflicted copy PROMOTED to .git byte-exact. After: --absolute-git-dir is the out-of-tree path,
HEAD = 96b1e9c UNCHANGED, show-toplevel is the Dropbox path, and the ladder went from 0 to 31 ok rails over 386 lines.
LESSON: RAIL 0 turned a potential undetected repository corruption into a 10-minute repair. The DURABLE fix is still
an OWNER act: the resurrecting client must stop writing .git, or the worktree must leave the synced tree (D-366).

## BUG-541 (MEDIUM - FIXED 2026-09-26): the DECLARED recovery path crashed during the incident it exists for
MEASURED: 'check_repo_integrity.py --plan' died with IsADirectoryError at verdict()'s comparison of cc_abs.read_bytes()
with canonical_abs.read_bytes() - the conflict copy is a FILE (the 58-byte pointer) whose canonical name is a
DIRECTORY (the resurrected .git). The same read sits in the report path of checks(), so RAIL 0 would have crashed
identically the moment the git dir resolved - the BUG-543 fix would have been masked by a traceback.
FIX: _same_bytes(a,b) -> bool|None (None when either side is not a regular file); verdict() returns OWNER_OWED for
the type conflict (no bytes to compare, and NEITHER side may be moved by a rail); superset_holds() refuses a
directory; the report gains a three-way word (identical | DIVERGES | UNCOMPARABLE (one side is a DIRECTORY)).
CONTROLS: 8 known-answer controls in a new --selftest, SEEN to fire; control 1 IS the regression. My own control
CAUGHT ME too - the superset fixture reused the first fixture's path, so the byte-identical control read overwritten
bytes (the D-2650 lesson applied to a FILENAME). Fixed. --selftest rc=0; --plan now prints all 39 rows and names the
.git row OWNER_OWED instead of dying.

## BUG-542 (MEDIUM - MITIGATED, REMEDY OWED 2026-09-26): the silent-repair allowlist is keyed by LINE NUMBER, so a mechanical edit becomes a FALSE FAILURE
MEASURED by my own change: inserting 37 lines into scripts/check_repo_integrity.py above a DECLARED site produced
DRIFT ':280 replaces silently (replace) with no entry' AND STALE ':243 declared but NOT measured', aborting just
health on line 51 (silent-repair, unknown 1) - a FAIL caused by a LINE SHIFT. The site is
reflog.read_text(errors='replace'): a DECODER error policy, not a write at all.
MITIGATION: the declaration's line key is corrected from the RAIL'S OWN --list measurement, never retyped.
REMEDY OWED (the real bug): key a declared site by SITE CONTENT (enclosing function and/or matched text), not by
line number. Same class of false witness as BUG-540: a rule that cannot distinguish two causes.

## CARRIED (2026-09-26, unchanged): just health is still rc=1 with 31 ok rails - it now aborts at line 51
(silent-repair, BUG-542, mitigated) and prints FAIL contract: 38 hard finding(s). BUG-539 is still OPEN (the census
inside config/decisions.yaml makes a mint a MID-FILE insert), so NO decision was minted; the registry is still 784
records / stamp 0d7a746350d62e14 and its receipt still verifies ('ok decisions_registry: config/decisions.yaml
unchanged'). Nothing was committed (D-381).

## BUG-542 (MEDIUM - REMEDY APPLIED 2026-09-26, ROOT CAUSE NAMED): the silent-repair allowlist was keyed by LINE NUMBER, so a MECHANICAL edit became a FALSE FAILURE
The +37-line BUG-541 fix inserted ABOVE an already-declared site shifted scripts/check_repo_integrity.py:243 -> 280, which produced BOTH DRIFT (280 repairs silently with no entry) and STALE (243 declared but NOT measured) and aborted just health at line 51 for a purely mechanical reason. The site at 280 is the SAME site - reflog.read_text(errors="replace"), a DECODER policy, not a write.
REMEDY APPLIED (one line, byte-length preserving, value taken from the rail's OWN measurement, never retyped): config/silent_repair.yaml lines: [243] -> lines: [280]. The rail's own --list prints verbatim:    scripts/check_repo_integrity.py : 280/replace
PRE  sha256 20b44f91e354a64616d916f0fd211bc587aa5b16e9239fd94222e8239cb0f362  5510 B / 108 lines
POST sha256 73bb29ae31e95d50dff0582d9dc043d4acbad3d1e6a64ebd22273ecff04e3671  5510 B / 108 lines
DELTA: exactly the 3 bytes 243 -> 280; file LENGTH and LINE COUNT identical, so nothing downstream shifted. The write went through tempfile -> fsync -> os.replace (C6) and asserted post == intended bytes.
AFTER: OWED silent-repair: debt 17 of ceiling 17 | unknown 1 -> 0 | allowed 7 entry(ies). NOTE THE ARITHMETIC (READ from the rail, not assumed): debt counts ONLY entries under the config key 'debt'; an 'allowed' entry is never counted, so moving a site from unknown to allowed moves ONLY the unknown count - the ceiling and its shrink_only direction are UNTOUCHED, and no ceiling change was made or needed.
ROOT CAUSE STILL OWED (the real remedy): a declared silent-repair site is keyed by LINE NUMBER. It must be keyed by SITE CONTENT (the enclosing function and/or the matched text) so a refactor above it cannot turn a declared site into an unknown one. Until then EVERY insert above a declared site aborts the ladder for a mechanical reason - which is how a false failure becomes a habit.

## BUG-544 (MEDIUM - OPEN, MEASURED 2026-09-26): the silent-repair rail RAISES instead of DECIDING when its own declaration is ABSENT or EMPTY - the BUG-541 class, in the rail that just caused BUG-542
MEASURED with the module's CONFIG monkeypatched to a controlled path (no repo state touched, nothing written):
  ABSENT declaration -> FileNotFoundError out of load()'s CONFIG.read_text
  EMPTY  declaration -> yaml.safe_load returns None and the FIRST cfg.get(...) raises AttributeError
Both are TRACEBACKS, not verdicts (C16: a rail must DECIDE; BUG-541 was the same shape one rail over). Compounding, DURABILITY half - MEASURED: git ls-files config/silent_repair.yaml returns NOTHING and git status reports '?? config/silent_repair.yaml', i.e. the declaration this rail depends on is UNTRACKED. A fresh clone, a lost file, or any recurrence of the BUG-543 .git incident therefore ends at just health line 51 with a traceback instead of the sentence 'the declaration is ABSENT'.
REMEDY OWED (small, mine): load() must fail closed with a named message on an absent/empty declaration, plus a known-answer control SEEN to fire (BUG-492). The durability half is a COMMIT (owner-held, D-381) - an untracked config that three rails depend on is a single point of failure with no receipt.

## MILESTONE (2026-09-26): just health is GREEN for the first time in this session series - rc=0, 40 ok rails over 583 ladder lines (was rc=1, 31 ok, dying at line 51)
The single blocker was the BUG-542 line-number drift, NOT BUG-539. The ladder now runs PAST line 51 and every later rail completes. Also RESOLVED-BY-REPAIR (carried two sessions): the two verify_handoffs selftest failures 'revision bc1cc956... does not re-derive from git' and 'revision be1a39e0... does not re-derive from git' were ENVIRONMENTAL (the BUG-543/BUG-500 out-of-tree git dir), not defects - they are gone now that the git dir resolves.
THE REMAINING FAIL WORD IS NOT A FALSE WITNESS (audited, do not 'fix' it): FAIL contract: 38 hard finding(s) - fail closed. scripts/validate_depth_domain_contract.py returns 1 on 38 MENU_OFF_TOKEN findings (plus 43 owner_blocked DOMAINS_BLANK), but the CLI is wired as --gate-if-active and the rail PRINTS that the suppression is in force: NON-GATING: contract status is 'proposed' (owner gate). Finders are real S4 data debt; the green ladder is green BY DECLARED OWNER GATE, which is itself an OWNER GATE item - while the contract stays 'proposed', 38 hard findings do not gate and nothing consumes the workbook.

## DECISION PROOF (audit 2026-09-26): D-2655 is NECESSARY BY CONSTRUCTION - the registry append defect CANNOT be fixed by moving the census inside the file
HYPOTHESIS TESTED: move the derived census (head lines 1-6 and the top-level summary block at line 8682 of 8863) to the TOP of config/decisions.yaml so the records extend to EOF and a mint becomes a pure byte-append. VERDICT: NO. The receipt rule is a PREFIX rule - the receipted bytes must be a prefix of the current bytes. A mint changes total_decisions, summary, decisions_sha256_16 and last_sync, so those bytes would then live in the PREFIX region; the receipted prefix would stop being a prefix and the rail would report 'rewritten' exactly as it does today. CONCLUSION: NO POSITION INSIDE AN APPEND-ONLY FILE IS COMPATIBLE WITH A PREFIX RULE WHEN A DERIVED VALUE CHANGES ON EVERY MINT. The census must leave the file (D-2655: governance/decisions_summary.json, with source_sha256 naming the registry bytes it describes).
BLAST RADIUS MEASURED (grep over scripts/, pipeline/, tools/, tests/, config/): consumers of total_decisions / summary / decisions_sha256_16 / written_by / last_sync are exactly FOUR - scripts/recompute_decision_summary.py (the writer), tests/test_decision_summary_sync.py (the second oracle), config/artifact_ownership.yaml (owned_by) and config/derivations.yaml (2 rows: decisions.summary, decisions.decisions_sha256_16). scripts/input_mutation_notice.py line 55 writes its OWN 'written_by' field - it is NOT a census reader. tools/sync_decisions.py is a RETIRED tombstone (exit 2). The migration is therefore LOCAL, not repo-wide.
CASCADE ENUMERATED BEFORE IMPLEMENTATION (each is a rail that will fire if forgotten): (1) scripts/check_derivation_homes.py validates a declared home by FUNCTION NAME uniqueness across scan roots, so a new census home needs a UNIQUE function name and a status: homed row, or enforcement.max_non_homed (currently 1, shrink_only) is breached by an edit - a ceiling may only be LOWERED; (2) scripts/check_config_defaults.py (D-2644) fires on a config value read with a CODE DEFAULT, so the new census reader must index its keys explicitly and FAIL CLOSED, never .get(key, literal); (3) config/handoffs.yaml declares the decisions_registry receipt over config/decisions.yaml with seal: false, so the migration makes that receipt STALE (prefix_state -> 'rewritten') and it MUST be re-baselined in the SAME sitting with the pre-image declared - a migration re-baseline is lawful ONLY as a declared decision, never as a silent edit; (4) tests/test_decision_summary_sync.py must read the census from its NEW home and FAIL CLOSED when the census JSON is ABSENT (BUG-487: a journal that does not exist must not read as 'ok').
ORDER CONSTRAINT (additive-first, so no intermediate state points at a file that does not exist - the exact reason a half-applied migration was REVERTED last session): (a) create the census JSON from the CURRENT registry; (b) teach the writer to read/write the new home AND to mint as an APPEND; (c) strip the census from the registry; (d) re-point artifact_ownership.yaml, derivations.yaml and the test; (e) re-baseline the receipt via handoff.py --backfill; (f) verify: recompute --check, the test, check_derivation_homes, check_config_defaults, reconcile, just health. SELF-PROVING CHECK: decisions_sha256_16 must stay 0d7a746350d62e14 and 784 records / per-state / by_category must re-derive identically.

## CARRIED (2026-09-26, unchanged): just health is GREEN (rc=0, 40 ok rails); NOTHING was committed (D-381, owner-held); NOTHING was minted (the open registry append defect still blocks mints - the registry is still 784 records, stamp 0d7a746350d62e14, receipt ok f67d12a2f3f5f502).


## BUG-544 (MEDIUM - FIXED 2026-09-26): the silent-repair rail now DECIDES when its own declaration is broken, and refuses a silently-narrowed census

WHAT WAS WRONG (measured 2026-09-26, remedied the same sitting). scripts/check_silent_repair.py load() was one line -
yaml.safe_load(CONFIG.read_text(...)) - so an ABSENT declaration surfaced FileNotFoundError at the caller and an EMPTY one
returned None and then raised AttributeError out of the first cfg.get(...). Both are TRACEBACKS, not verdicts: at
just health line 51 the ladder would die with a stack trace instead of the sentence "the declaration is ABSENT". This is
the BUG-541 shape one rail over, and the third member of the FALSE-WITNESS family this register names.

REMEDY (scripts/check_silent_repair.py, 195 -> 283 lines; sha256
2254fe4ecbd02a9039043a73334720c05f37557c1e63d15861db0dd094fc88f1). load() is now three functions with one job each:
  declaration_text(path)       - FileNotFoundError | IsADirectoryError | UnicodeDecodeError | OSError -> a NAMED SystemExit
  parse_declaration(text,path) - EMPTY | unparseable YAML | not a mapping | missing a REQUIRED key (scan_roots, ceiling) -> named
  config_path(repo)            - the repo argument of load() was IGNORED: a caller asking about another repo silently got THIS one's policy
scan() also REFUSES an EMPTY scan_roots and a declared scan root that is not on disk. Before, 'if not base.exists(): continue'
narrowed the census to NOTHING and still printed ok - a rail that can never say FAIL (BUG-492). Its sibling
scripts/check_config_defaults.py already carries this exact guard (C16); this rail now matches the sibling.

MEASURED, not asserted (no repo state touched: the shipped module was COPIED into /tmp/bug544/scripts and run against
/tmp/bug544/config/silent_repair.yaml, one declaration per case):
  ABSENT rc=1 | EMPTY rc=1 | UNPARSEABLE rc=1 | NOT_A_MAPPING rc=1 | MISSING ceiling rc=1 | MISSING scan_roots rc=1 |
  SCAN_ROOT_ABSENT rc=1 | CONTROL_OK_CONFIG rc=0      TRACEBACKS LEAKED = 0
--selftest 12 -> 18 known-answer controls, 18/18 fire (one per case, asserting the NAMED sentence, because "exit != 0"
alone cannot tell a named refusal from a traceback). --check still rc=2 (debt 17 of ceiling 17, unknown 0). just health rc=0.
THE NEIGHBOUR CENSUS IS UNMOVED: check_config_defaults measures 412 sites / 210 shadowed-declared / 2 undeclared -
identical to before the edit (the new code adds no '.get(key, default)' site, which is the thing that rail counts). No
line-numbered register keys this file: config/undeclared_encoding.yaml names it only inside a COMMENT.

TWO CASCADES AUDITED BEFORE ACTING (each would have been a new bug produced by a plausible "fix"):
  1. THE CENSUS HOME cannot be governance/decisions_summary.json as D-2655 was drafted. governance/session_plan_20260924.yaml
     may_touch covers config/*.json but NOT governance/*.json (it names governance/bug_status.json, HANDOFFS.jsonl and one
     ANCHOR4 manifest explicitly). A new governance/*.json would sit OUTSIDE may_touch, and widening the plan so an assistant
     may write it is forbidden (BUG-528/BUG-445). D-2655's census must therefore be born at config/decisions_summary.json,
     which IS covered today - or the plan change must be an OWNER act, committed first.
  2. STAGING THE UNTRACKED DECLARATION IS NOT A DURABILITY FIX. 'git ls-files' is the INPUT SET of the incident rail
     (check_repo_integrity.py: tracked_paths() -> _scan_root), so 'git add config/silent_repair.yaml' changes what that rail
     examines - and that is the one rail which reports the BUG-500/BUG-543 git-dir incident. The declaration (5510 B, sha256
     73bb29ae31e95d50dff0582d9dc043d4acbad3d1e6a64ebd22273ecff04e3671) is STILL UNTRACKED ('??', 0 ls-files) and must be
     tracked by COMMIT A with its new row SEEN to compare clean - never by a bare stage.

CARRIED, UNCHANGED: NOTHING minted (784 records, stamp 0d7a746350d62e14, receipt ok), NOTHING committed (D-381, owner-held).
D-2655 remains the top implementation item; it was deliberately NOT started here because the remaining budget could not carry
the full verify chain, and a half-applied registry migration is the exact hazard that forced the last revert.

## BUG-545 (MEDIUM - OPEN, MEASURED 2026-09-26): 17 of the 60 rails the health ladder invokes are NOT tracked by git - the control plane has no history and no receipt

MEASURED (the rail list is grep -oE 'scripts/[a-z0-9_/]*[.]py' justfile | sort -u, minus git ls-files): 17 of 60 rails
invoked by just health are absent from the index - including the newest control family AND the three libraries they all
depend on. Untracked among them: check_silent_repair.py (fixed THIS sitting) and its declaration config/silent_repair.yaml,
check_config_defaults.py (D-2644), check_derivation_homes.py, check_encoding_homes.py, check_revoked_references.py,
check_store_authority.py, check_store_columns.py, check_undeclared_encoding.py, check_label_provenance.py,
check_s5_score_axis.py, check_serving_gate.py, verify_generator_pins.py, resolve_dropbox_conflicts.py, plus
scripts/lib/artifact_encoding.py (the declared decode HOME), scripts/lib/yaml_guard.py (D-2648 verify-before-write) and
scripts/lib/operator_env.py. Whole surface: 19 untracked .py under scripts/, 19 untracked entries under config/, 19 under
governance/; 182 porcelain paths in total (61 modified, the rest untracked).

WHY IT MATTERS. D-382 says a pin must be bytes-on-disk -> digest; this is its mirror. A CONTROL that exists only in a working
tree has no ancestry: a fresh clone, one lost sync file, or one more BUG-543 git-dir incident leaves just health with rails
that DECIDE NOTHING because they are simply not there - and the absence is an error only if something notices it. Every
safety property bought in the last three sittings (BUG-540, BUG-541, BUG-542, BUG-544) was fixed INSIDE this untracked set.

STAGING IS NOT THE REMEDY (audited this sitting). git ls-files is the INPUT SET of scripts/check_repo_integrity.py
(tracked_paths() -> _scan_root(row["tracked"], ...)), so a bare git add changes what the ONE rail that reports the git-dir
incident examines. The index must be staged deliberately, in COMMIT A, WITH that rail seen to compare clean before and after.

REMEDY OWED (owner-held, D-381): bring the control plane - these 17 rails, the 3 libraries and their declarations - into
COMMIT A, and do NOT ack the stale register/decisions blobs while doing it (the index is far behind the register).
## D-2655 HALF A LANDED - THE CENSUS LEAVES THE APPEND-ONLY REGISTRY (MEASURED 2026-09-26)

WHY THIS EXISTS (BUG-539, still OPEN). config/decisions.yaml is declared append_only and its handoff receipt is
a PREFIX rule. total_decisions, summary, decisions_sha256_16 and last_sync change on EVERY mint, so NO position
inside an append-only file is compatible with a prefix rule while a derived value lives there: the mint's
mid-file insert is the SYMPTOM, not the disease. The census therefore LEAVES the registry.

WHAT LANDED (HALF A - additive by construction, zero removal):
- NEW config/decisions_summary.json: schema_version, source_path, source_sha256 (the FULL registry digest),
  written_by, last_sync, decisions_sha256_16, total_decisions, summary. It carries NO generation timestamp, so
  it is a PURE FUNCTION of the registry bytes and a re-run is a byte-identical no-op (PROVEN: two consecutive
  runs, identical sha).
- scripts/recompute_decision_summary.py: census_document / census_text / census_problems / write_census plus a
  SELF-HEALING write branch that repairs ONLY the artifact that actually drifted. MEASURED: the registry sha256
  is byte-UNMOVED before and after (f67d12a2f3f5f502...), so the decisions_registry PREFIX receipt was never
  disturbed - verify_handoffs rc=0 (6 paths, 13 digests, 2 revisions). Rewriting the registry merely because the
  census was absent would have moved last_sync on a healthy registry and turned that receipt into 'rewritten'.
- config/derivations.yaml: ONE new row, decisions.census_json, homed to ::census_document (10 rows, 9 homed,
  the shrink-only ceiling of 1 non-homed untouched).
- config/artifact_ownership.yaml: declared derived_regenerable, writer_of_record, plus an unreconciled_reason.
- tests/test_decision_summary_sync.py: a FOURTH test that reads the census from ITS OWN home and re-derives the
  registry independently (the second oracle still does not import the writer).

KNOWN-ANSWER CONTROL (BUG-492: a control never SEEN to fail is a comment). With the census moved aside, the
writer --check exits 1 with the NAMED sentence and the new test FAILS (1 failed, 3 passed); restored, rc=0.
Both readers are provably able to say NO.

THREE CASCADES CAUGHT BY THE PRE-IMPLEMENTATION AUDIT - two would have shipped:
1. HARD: scripts/reconcile.py's cover rule makes a declared artifact with no reconciliation entry and no
   unreconciled_reason RED. MEASURED rc=1, ladder ok-lines 40 -> 34 (the ladder aborts). Remedy: declared
   unreconciled_reason; a reconciliation entry would compare the census against the census - self-certifying
   evidence, the BUG-467 class.
2. CENSUS: the store-columns mentions census moved because the new CODE names store columns. Remedy: rewrote
   the incidental prose so only the R14 stamp token remains, which is a real consequence of a real artifact.
3. Not a defect: governance/METRICS.jsonl grew (the guard journals every write it performs).

ORDER CONSTRAINT SATISFIED: nothing points at a file that does not exist - the census was created FROM the
current registry before any reader was pointed at it.

STILL OWED (HALF B, the removal): strip the derived head (lines 1-6) and the top-level summary block so the
registry holds RECORDS ONLY and a mint becomes a pure byte-APPEND; re-point ownership / derivations / the test;
re-baseline the decisions_registry receipt via handoff.py --backfill IN THE SAME SITTING; then the full chain.



## 2026-09-26 — D-2655 HALF B landed: the census left the append-only registry

**Note:** NO id minted yet (a heading that names no BUG-<id> token cannot break buglog coverage by construction). Three defects found by the pre-implementation forensic audit of HALF A, one of them a FALSE WITNESS:

**Note:** F1 (false witness, HIGH): tests/test_decision_summary_sync.py was ALREADY RED at 1 failed / 3 passed - not, as HALF A read it, because the census was absent. Its STATES list was a hand-copied 12-item copy of the writer's 14-item one (D-2645 added REVOKED/ABANDONED), so the census could never equal its expectation. HALF A's known-answer control was therefore MISREAD: the observed failure proved nothing about the control it was meant to fire. Invisible because the 40-rail ladder does NOT run pytest (pytest is just health-deep). FIXED: the oracle now READS the vocabulary and the forbidden-key list from the writer by AST (D-2646: read it, do not restate it) and fails closed if it cannot; 5 passed.

**Note:** F2 (blindspot, MED): census_problems compared only the REQUIRED keys, never the extra ones, so the stale last_sync in the census on disk was invisible while --check reported 1 drift (the registry's). A census nobody derives is how a stale count survives every comparison. FIXED: the key SET is now checked in BOTH directions; SEEN to say NO on a fixture carrying last_sync, and a clean fixture returns [].

**Note:** F3 (BUG-541 class, LOW): census_problems computed its label with path.relative_to(ROOT) and RAISED ValueError on an out-of-tree path - a rail that raises instead of deciding, which is what made F2 uncontrollable. FIXED: it DECIDES (str(path)) for an out-of-tree fixture.

**Note:** STRIP (one shot, byte splice): PRE 604309 chars / f67d12a2f3f5f5022faa21ca4d204e3d582a421e09cdd2702d73e9a93592621b -> POST 599742 chars / 39bb05d4718abb6da3e3ab618b1e554464d0bed325d3897be055dcf386adcad7. DROP 142 B of derived head + 4426 B of summary block. 784 records, stamp 0d7a746350d62e14 UNMOVED (asserted, not assumed); top-level keys are now ['decisions','ratified','version']. Census re-derived from the bytes on disk (7 keys).

**Note:** RE-BASELINE: python3 scripts/lib/handoff.py --backfill -> receipt decisions_registry 39bb05d4718abb6d, 6 receipts appended. The pre-strip digest stays in the append-only journal, so the rewrite is VISIBLE, not laundered.

**Note:** VERIFIED AFTER: recompute --check rc=0 (both homes green); pytest 5 passed; just health HEALTH_RC=0, ok=40, FAIL=1 (the one audited non-gating contract line), store-columns census moves 4 (baseline preserved: no new store-column token entered scripts/).

**Note:** OWNED DECLARATION DRIFT FIXED IN THE SAME CHANGE: config/artifact_ownership.yaml#config/decisions.yaml owned_by now []  + writer_scope: append_only_new_records (owned_by has NO code consumer - write_guard reads writer_of_record/guard_exemption only - so this was honesty, not a rail), and its guard_note named _surgical_write, which HALF B DELETED (C19). derivations.yaml's decisions.summary / decisions.decisions_sha256_16 rows re-pointed off config/decisions.yaml (columns that no longer exist); decisions.census_json re-pointed from total_decisions to source_sha256, because census_document computes the document, not that count.

**Note:** STILL OWED (next sitting): mint D-2655 + D-2654 through --mint - the FIRST mint through the repaired path IS the end-to-end control for BUG-539 (the append must read as 'appended', not 'rewritten').

## 2026-09-26 — D-2655 COMPLETE: the FIRST mint through the repaired path PROVES the append (the driver bug retired end to end)

**Measured:** the mint that D-2655 HALF B existed for finally ran through the repaired path. `python3 scripts/recompute_decision_summary.py --mint /tmp/mint_both.yaml --apply` -> `merged 2 record(s): D-2654, D-2655 - total=786, stamp b6492f16d292eea5`. Registry PRE 601712 B / sha256 39bb05d4718abb6da3e3ab618b1e554464d0bed325d3897be055dcf386adcad7 -> POST 606225 B / sha256 1d96883f365819a2fb6205a751d90885fd7965b0e0e26126aa97ee08e236d364. DELTA 4513 B and APPEND_IS_PREFIX True - checked, not asserted. Top-level keys remain ['decisions','ratified','version'] with `decisions` LAST, so the records list runs to end-of-file.

**The control (what this sitting was for):** `python3 scripts/verify_handoffs.py` -> `ok decisions_registry: config/decisions.yaml APPENDED (prefix intact, 601712 -> 606225 bytes)`, VH_RC=0. Before this sitting the same receipt read `rewritten` on every mint; this is the FIRST observation of `appended` on a real mint, and it is the end-to-end proof that the removal turned the mint into a pure byte-append. A rule that had never once said YES in production has now been observed saying YES.

**Verified after:** `recompute --check` rc=0 (both homes green: 786 decisions, stamp b6492f16d292eea5, census 7 keys, source_sha256 matching the registry bytes on disk); `pytest tests/test_decision_summary_sync.py` -> 5 passed; `just health` -> HEALTH_RC=0, ok=40, FAIL=1 (the one audited non-gating contract line). The census moved exactly where it should and nowhere else: total 784 -> 786, rejected 9 -> 10 (D-2654), ratified 16 -> 17 (D-2655), every other bucket unchanged.

**Ids:** D-2654 (REJECTED - Apple Foundation Models NOT ADOPTED on STRUCTURAL grounds: the weights are System-Integrity-Protected, so unreadable, so unhashable, so unpinnable under D-382, and config/apple_fm.yaml keeps enable false) and then D-2655 (RATIFIED - a derived value has no home inside the append-only artifact it describes). D-2653 is deliberately NOT minted (its content is not settled). The two SPENT fixture ids were not touched.

**The register's unexplained +1 RESOLVED:** the prior sitting carried 281 ids / 128 OPEN / 153 CLOSED while the re-derivation printed 282 / 129 / 153. MEASURED: the register at HEAD was 189 ids (five days stale), and diffing the HEAD register against the current one shows the +1 is the driver bug itself - logged in the prior sitting and OPEN until this sitting. There was no phantom id; the register agrees with its own re-derivation, and that total is unchanged by this sitting's closure.

**Audit notes, report-only (nothing silently absorbed, no id invented):**
1. The mint writes TWO documents (the registry append, then the census) and they are not one transaction. The write ORDER is the safe one: the append_only registry first (it can never lose a byte), the regenerable census second - so a crash between them leaves a census describing the PREVIOUS bytes, which `recompute --check` reports as a NAMED drift and repairs from the census side only. Bounded, loud and deterministic: recorded rather than given an id.
2. config/decisions_policy.yaml's reference_rail comment claimed "the next decision this project mints is D-2650". A claim about the NEXT id is a volatile value with no home and no rail - the same defect class as the derived head this sitting deleted - and the mint above made it false the same day. REMOVED in this sitting, and the removal is written where the claim stood.
3. config/store_authority.yaml line 49 still reads "Owner decision owed on deleting it (D-2650 gate)" - a dangling reference to an id that was never minted. LEFT IN PLACE: it is another author's declared meaning and prose, not a ruled citation. Owed: re-point or delete it when the store-authority question is ruled.
4. scripts/check_repo_integrity.py reports P0-B lines for archive/conflicted_20260926/ holding conflicted copies of decisions.yaml, recompute_decision_summary.py and test_decision_summary_sync.py - the sibling hazard sits on the exact files this change touched. Report-only, and the standing reminder that the commit is the protection (BUG-543/BUG-545 family).

**Nothing committed** (D-381, owner-held); HEAD is still 96b1e9c79c441edf71b551a2f3c52e06e31f6362.

**OWED NEXT:** the two-commit landing (control plane first, then the registry/D-2655 change) with scripts/check_repo_integrity.py SEEN to compare the new rows clean; wire pytest into the ladder as a rail (the false witness was invisible for want of exactly that); the content-keyed site remedy for the silent-repair allowlist; the R2 pin re-measure and re-mint; and the report-only candidate that the derivations rail never validates the table/column a row names.

---

## BUG-539 (HIGH - FIXED 2026-09-26): the registry's own derived summary block made MINTING a mid-file edit that the prefix rail read as tampering - and it ABORTED the ladder

**Root cause:** two homes for one fact. config/decisions.yaml is declared append_only with a PREFIX handoff receipt (the receipted bytes must be a byte-prefix of the current bytes) and it ALSO carried a derived head (total_decisions, decisions_sha256_16, last_sync, written_by) plus a derived summary block at EOF. Every mint had to move those bytes, so no position inside the file was compatible with the prefix rule: verify_handoffs read the registry as `rewritten` and the writer had grown a mid-file splice to re-derive the values in place.

**Fix (D-2655 HALF A + HALF B, 2026-09-26):** the census moved to config/decisions_summary.json (declared derived_regenerable, a PURE FUNCTION of the registry bytes); config/decisions.yaml is RECORDS ONLY with its records list extending to end-of-file; the mint is a CHECKED pure byte-append that carries the census in the same invocation; the one-time receipt re-baseline was recorded as a supersession in the append-only handoff journal, so the rewrite is visible rather than laundered.

**Known-answer control (SEEN to say NO, then YES):** BEFORE the strip, the mint was REFUSED with the named sentence `derived key(s) [...]: config/decisions.yaml is append_only with a PREFIX receipt, so a derived field inside it makes every mint a mid-file rewrite (BUG-539/D-2655)` and rc=1. AFTER it, the same mint succeeded AND the receipt reads `APPENDED (prefix intact, 601712 -> 606225 bytes)`.

**Status:** FIXED - the mint path is a pure append and the prefix rail agrees on the bytes.

## 2026-09-26 - the SUITE becomes a RAIL (D-2656): the ladder was taught to read a test report, and it found a destructive test

**Measured, not assumed.** `python3 -m pytest tests -q` at HEAD 96b1e9c = **3 failed, 253 passed, 261
collected, 114s** - while `just health` was GREEN. The suite's red set was invisible to all 40 rails, which
is the BUG-470 class again: a control nothing invokes is a comment. The 3 red are the depth/domain contract
family (status: 'proposed', owner gate) - an OWNER-OWED red, not a silent one.

**BUG-546 (found by this audit, FIXED 2026-09-26): a DESTRUCTIVE test resolved the PRODUCTION stage root by hand.**
tests/test_stage4_preflight_smoke_stress.py:326-333 built `ROOT / "knowledge pipeline" / "stage4_merge" / run_id`
and then `shutil.rmtree`'d it. Because the path was hand-built (not resolved through pipeline_paths), NO env var
could redirect it - and running the suite DELETED the S4 smoke run dirs inside the LIVE tree, including the
Dropbox 'M1 max's conflicted copy' siblings that were sitting in them (measured: 391 -> 376 stage-tree rows).
tests/conftest.py TOLERATED it, because the run id matched the declared `smoke_*` glob: a tolerance declared for
test SCRATCH was silently extended to cover a recursive DELETE of a production path. A declared tolerance is not
a licence to destroy.
FIXED: the smoke paths now come from `_stage_run_dir()` (pipeline_paths - the one path home) and the delete goes
through `_rmtree_declared_test_run()`, which REFUSES any path whose run id is not declared test scratch in
config/test_isolation.yaml. The guard fails CLOSED: an undeclared run id raises instead of deleting.

**Also recorded (a trap, disproven by measurement):** `MAXWELL_PIPELINE_ROOT=<tmp>` is NOT a suite sandbox.
It redirected the stage dirs but ALSO redirected config/ (pipeline/taxonomy_manager.py::_get_taxonomy_path) and
the books/DB paths, producing **14 SPURIOUS failures** (17 failed sandboxed vs 3 real). A suite sandbox must COPY
THE CODE, never re-point the root.

**The rail:** `scripts/check_tests.py` (known-answer controls, BUG-492: floor breach, regression, paid red,
strict, unreadable summary, plus 3 REAL fixture suite runs). Verdict: `ok tests: 261 collected (floor 261),
253 passed, 3 declared red (shrink-only), 0 new, 5 skipped`. Wiring: `--selftest` + `--check` in `just health`;
`health-deep` now demands the ceiling EMPTY (`--strict`) - the same red verdict it had before, with the
destructive path closed.

## BUG-546 (HIGH - FIXED 2026-09-26): a destructive test resolved the PRODUCTION stage root by hand, so running the suite DELETED directories inside the live pipeline tree - and the isolation guard TOLERATED it

**Found by:** the D-2656 audit of `python3 -m pytest tests -q` (measured BEFORE the fix: the suite's S4 smoke
run dirs vanished from the live tree - stage-tree snapshot 391 -> 376 rows, incl. the Dropbox 'M1 max's
conflicted copy' siblings sitting in `knowledge pipeline/stage4_merge/smoke_live_cribs/` and
`smoke_preflight_plumbing/`).

**Defect:** `tests/test_stage4_preflight_smoke_stress.py::_stage_smoke_s2` built the path
`ROOT / "knowledge pipeline" / "stage4_merge" / run_id` and then `shutil.rmtree`'d it. Three failures of
discipline in one line:
1. The path was HAND-BUILT, so NO environment override could redirect it (`MAXWELL_PIPELINE_ROOT` repoints
   pipeline_paths' root, but this path never went through pipeline_paths).
2. It was a recursive DELETE of a directory whose only safety property was a run id chosen by the caller - one
   bad run id away from wiping a production run.
3. `tests/conftest.py` **tolerated** it: the run id matched the declared `smoke_*` glob in
   config/test_isolation.yaml. A tolerance declared for test SCRATCH was silently stretched to cover a
   recursive delete of a production path. The guard reported 'declared smoke-run artifact(s) touched' - TRUE
   and useless.

**FIXED:** `_stage_run_dir(stage, run_id)` resolves every smoke path through pipeline_paths (the ONE path home),
and `_rmtree_declared_test_run(path)` REFUSES any path whose run id is not a declared test run id in
config/test_isolation.yaml - it raises instead of deleting. The 5 hand-built sites (S2 stage dir, S4 stage dir,
the S4 read, the t11 read, the S4 checkpoint read) now go through the helper.

**Verified after:** the full suite re-ran through the new rail with the fix in place - 261 collected, 253 passed,
3 declared red (the depth/domain contract, owner gate), 0 new failures, so the S4 smoke tests still pass and now
pass INSIDE the declared test scratch instead of inside the live tree.

**Standing rule (BUG-462 class):** a declaration that TOLERATES a write is not a declaration that may license a
DELETE. A tolerance must be narrower than the thing it tolerates: `smoke_*` may hold scratch files; it may not
authorize `rmtree` on a stage dir.

## BUG-547 (HIGH - FIXED 2026-09-26): rail 0 was SATURATED BY ITS OWN ARCHIVE - 30 of its 36 owner-owed rows were conflict copies it had already resolved, so the exit-2 commit gate could no longer tell its own history from a live divergence

MEASURED. `python3 scripts/check_repo_integrity.py` returned rc=2 with `36 conflict copy/copies (bytes
intact, disposition owed)`. 30 of those 36 rows were `canonical archive/conflicted_20260926/<name> is MISSING
and untracked (P0-B)` - the rail was reporting THE SIBLINGS IT HAD ALREADY FILED, inside the archive dir that
`config/conflict_policy.yaml` declares. The pre-commit hook runs this rail with `|| exit 1`, so exit 2 IS
fatal at the commit gate: a gate whose steady state is 36 owed rows has no dynamic range left, so it cannot
signal a NEW divergence.

ROOT CAUSE (the D-2646 class, on the READ side). D-2647 taught the RESOLVER that an archived sibling is a FIXED
POINT - the record of a resolution that happened - which is what keeps the resolver idempotent. It never taught
the RAIL. TWO consumers of ONE rule, and only one of them learned it.

FIX (`scripts/check_repo_integrity.py`). `_declared_archive()` reads `archive_dir` from its ONE home
`config/conflict_policy.yaml` (the path is not restated anywhere - C12/D-2646) and `archived_under()` filters
those rows out of `scan()`. Known-answer controls 9 -> 10, and the new control is TWO-SIDED (BUG-492): an
ARCHIVED sibling must be excused AND a LIVE sibling must NOT be - a one-sided control would pass on a rule that
excuses everything.

VERIFIED. `ok repo-integrity selftest: 10 known-answer control(s)` and `ok repo-integrity: HEAD resolves,
git dir /Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git, logs/HEAD agrees, 0 conflict-marked names in 2
sweeps`, rc=0. NOTHING WAS DELETED: the archive stays the record of the resolutions it holds.

## Dropbox sibling disposition (D-2647) - 6 siblings VAULTED, nothing deleted (2026-09-26)

The commit gate stopped on 6 live Dropbox siblings (4 governance + 2 pytest caches). Each was MEASURED against
its canonical file, then moved OUT of the synced tree into `~/maxwell_os_conflict_snapshot_20260925/vaulted/`
with its sha256, and appended to `~/maxwell_os_conflict_snapshot_20260925/RESOLUTION_20260926.jsonl`. The
vault script was FAIL-CLOSED: it re-derived the sibling set and ABORTED (`ABORT (fail-closed): sibling set
differs from the audited set`) because the real names put the marker BEFORE the extension. No byte was
deleted; every row carries a restore `mv`.

| sibling | verdict | why |
|---|---|---|
| `governance/anchor_adjudication_workbook_20260924 (M1 max's conflicted copy 2026-09-26).csv` | SUPERSEDED-BY-DECLARED-RENAME | live col4 is `flags`; the sibling predates the deliberate `row_flags`->`flags` rename (pre-image `backups/anchor_adjudication_workbook_20260924.PRE_ROWFLAGS_20260925.csv`); all 149 lines differ only through that header cell. Separate finding: the workbook is NOT utf-8 (0xCA at byte 1604). |
| `governance/bug_status (M1 max's conflicted copy 2026-09-26).json` | SUPERSEDED-BY-REGENERATION | the sibling declares 241 ids / 111 open / 130 closed; the canonical is the register's own re-derivation (283/128/155), internally consistent (`open_n 128` == 128 rows), and deletes no line. |
| `governance/bug_status (M1 max's conflicted copy 2026-09-26).md` | SUPERSEDED-BY-REGENERATION | same stale generation; the canonical table is a strict superset. |
| `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl.input_fingerprint (M1 max's conflicted copy 2026-09-26).json` | OWNER-OWED-PIPELINE-STATE | MEASURED DROPBOX REVERT: the SIBLING is NEWER (2026-09-25 18:27) and names pipeline_commit `96b1e9c` (= HEAD) while the LIVE file names `81b813f`; differing keys are informational/input/fingerprint_id. `never_touch: knowledge pipeline/` - pipeline state is never text-merged. Bytes vaulted; the correct value is a RE-DERIVATION (owner judgement). |
| `.pytest_cache/v/cache/lastfailed (M1 max's conflicted copy 2026-09-26)` | CACHE-NO-GIT-BASE | pytest cache, rewritten by every run, carries no information. |
| `.pytest_cache/v/cache/nodeids (M1 max's conflicted copy 2026-09-26)` | CACHE-NO-GIT-BASE | same. |

OWED: the stage5 fingerprint's re-derivation (owner judgement, pipeline state); a policy note on whether
`archive/conflicted_20260926/` should itself be swept - NOT owed as a finding, it is the record.

NOTE (same sitting, caught by a rail): the widening entry was first written with a BARE `write_text` and an
unquoted `@: ` inside a value, which made the plan UNPARSEABLE - the D-2648 class, reproduced by the hand that
recorded it. Caught within seconds by `check_session_plan.py --selftest` (rc=1), repaired to a block scalar, and
re-verified. The guard existed and fired; the write should have gone through `scripts/lib/yaml_guard.py`.

## BUG-548 (HIGH - FIXED 2026-09-26): the plan RECORDED permissions it did not GRANT - the record is not the rule

**MEASURED.** `governance/session_plan_20260924.yaml` carried 15 `widening_log` entries and FOUR paths claimed as
widenings that `may_touch` never granted:

| entry | recorded as a widening | in may_touch before this fix |
| --- | --- | --- |
| #1 (2026-09-25) | `governance/ANCHOR4_MANIFEST_20260924.json` | NO |
| #6 | `governance/CONFLICT_REGISTER.md` | NO |
| #9 | `scripts/*.sh` | NO |
| #14 | `governance/NOT-YET-EVALUATED-RESEARCH.md` | NO |

**ROOT CAUSE.** Rail 4 reads `may_touch` ONLY, and NOTHING read `widening_log` - so the log was a record with no
consumer: a promise to a reviewer who cannot check it (D-2649: a declaration whose home is not the thing that is
READ). The consequence was not theoretical: on the same day, TWO refused artifacts (`governance/CONFLICT_REGISTER.md`
and `governance/RECONCILIATION.json`) were dropped out of COMMIT 1 by exactly this gap, while the plan read as if
they were permitted. Entry 15 - added hours earlier to fix the same class by hand - had the identical shape and was
caught only because rail 4 refused the commit.

**FIX (the class, not the four paths).**
- The four paths are GRANTED as NAMED paths (widening_log entry 16); the recorded glob `scripts/*.sh` is
  WITHDRAWN in favour of the exact path `scripts/install_git_hooks.sh` (a directory glob asked for as a one-file
  need is laundering surface, BUG-445/BUG-528); the two owner-acked `pipeline/**` crossings are declared
  `crossing: true` - the SUBJECT of an ack, never standing permission.
- `scripts/check_session_plan.py` now CHECKS the log on EVERY invocation: every `widened:` /
  `additions[*].pattern` must be MATCHED by `may_touch`, unless the entry is `crossing: true` or the path is
  listed under `withdrawn:`. FIVE known-answer controls, two of them anti-overreach (a GRANTED claim and a
  WITHDRAWN claim must both be TOLERATED) plus the LIVE plan's own control (BUG-492).

**VERIFIED.** `--selftest` 12/12 known-answer controls fire (was 7); `--staged` rc=0 over the staged set of every
commit in this sitting; the live plan's own control PASSES only after the repair - it was written to FAIL first.

**SUB-FINDING (MEASURED, NOT FIXED - OWED).** The matcher is `fnmatch`, so `*` crosses `/`: `scripts/*.py`
therefore GRANTS `scripts/lib/yaml_guard.py`. Entries #5 and #7 were already granted BY ACCIDENT, and `may_touch`
is LOOSER than its patterns read. Tightening the matcher FORBIDS paths that are legal today, so it is its own
decision with its own blast-radius measurement - not a patch smuggled into this one. Until then: every new entry
is a NAMED path, never a glob.

## BUG-542 (MEDIUM - FIXED 2026-09-26S): the CLASS fix - a declared silent-repair SITE is keyed by CONTENT, not by a line number (the earlier remedy re-pointed the coordinate, so rail 0's own edit orphaned it again)

WHAT (MEASURED, third occurrence of this bug). `config/silent_repair.yaml` declared rail 0's one repair site as
`lines: [280]`. Rail 0 then grew for BUG-547 and the site moved to 306, so the register reported ONE site TWICE:

| reported as | site | truth |
| --- | --- | --- |
| `STALE scripts/check_repo_integrity.py:280` | declared, not measured | the coordinate, still in the register |
| `DRIFT scripts/check_repo_integrity.py:306` | measured, not declared | the SAME site, moved |

The DRIFT is FATAL (exit 1) and it is NOT tolerated by `just health`, so the ladder ABORTED at justfile line 51 and
every rail below it never ran: check_undeclared_encoding, check_store_authority, check_store_columns,
resolve_dropbox_conflicts --check, reconcile --check, measure --gaps, verify_anchor_family_registry,
verify_menu_routing, verify_menu_policy, the pins rail (the R2 OWNER-OWED red lived BELOW the abort and was
therefore INVISIBLE), verify_generator_pins, verify_declared_inputs. BUG-457: an abort is an amnesia generator.

WHY IT RECURRED. The previous remedy (buglog, same file, same day) re-pointed the LINE NUMBER. A coordinate is not
a fact about the code, so the defect returned as soon as rail 0 was edited again - a symptom fix, not a class fix.

FIX (the class). `scripts/check_silent_repair.py::declared_sites` now resolves an entry's site against the
MEASURED line text: an entry keys it by `match:` (the substring the repairing line carries) or, legacy, by
`lines:`. EXACTLY ONE of the two is required; a `match` that resolves to nothing is REPORTED (never dropped - a
key that can match nothing is a comment, BUG-492); two entries may not claim one site (one site, one declaration,
D-2646). The live entry is keyed `match: 'reflog.read_text(errors'`.

VERIFIED. `--selftest` 24/24 known-answer controls fire (was 18); 6 are new and 2 are ANTI-OVERREACH (a
content-keyed register must tolerate its site MOVING, and a dead key must still be REPORTED). `--check` is exit 2
(declared debt only, loud NOT fatal) with 0 DRIFT and 0 STALE, so the ladder runs PAST line 51.


## BUG-549 (MED - FIXED 2026-09-26) - the SANCTIONED deletion path manufactured the store-authority FATAL, and a read-only probe that WRITES was filed under the wrong name

MEASURED (2026-09-26; BOTH instances aborted `just health` at justfile line 57 and hid every rail below it - BUG-457: an abort is an amnesia generator):

1. an earlier "read-only" probe ran `sqlite3.connect('pipeline/maxwell.db')` against a path that did NOT exist.
   `sqlite3.connect()` CREATES a missing file, so a read-only probe WROTE a 0-byte store. The rail reported it
   UNDECLARED-STORE - true, but it names the WRONG CAUSE, so the next reader (and the next session) hunts a
   phantom authority instead of a stray probe.
2. the interim fix (delete it via the sanctioned `pipeline/safe_delete.py`) then failed AGAIN: safe_delete copies
   the target to `backup/deletions/{timestamp}/` BEFORE deleting, and that pre-image directory sits INSIDE the
   rail's own scan root, so the sanctioned deletion path re-manufactured the identical FATAL. The interim action
   (removing the 0-byte pre-image, "the deletion log is the receipt") traded a green rail for the REVERSIBILITY
   the tool exists to provide - the fix cost more than the defect.

ROOT CAUSE (class, not site): the rail could not tell a STORE from THE FINGERPRINT OF NOT-A-STORE, and had no
declared home for a TOMBSTONE. A 0-byte file and a 4,964,352-byte diagnostic snapshot were both just "a .db".

FIX (class fix):
  * `preimage_regions:` in config/store_authority.yaml - a DECLARED tombstone home (backup/deletions, backups).
    A store file inside one is COUNTED as a tombstone, never reported as an authority. A region may not cover the
    repo (REGION-BLINDS-REPO), may not cover a DECLARED store (REGION-SHADOWS-DECLARATION), must be a directory
    (DEAD-REGION), and must carry an adequate `why`. An EMPTY region is the HEALTHY state and is not a fault.
  * EMPTY-STORE - a store file with ZERO tables (or 0 bytes) is now reported BY CAUSE: "the fingerprint of
    `sqlite3.connect()` on a path that did not exist, which CREATES the file". An unreadable store is
    UNREADABLE-STORE. Both stay FATAL; the message names the defect instead of mis-filing it.
  * the verdict STATES the boundary it measured (BUG-521):
    `ok store-authority: 7 store(s) declared | 0 tombstone(s) in 2 declared pre-image region(s) | 0 fault(s)`.
  * controls 9 -> 16: c10 tombstone counted, c11 0-byte file is EMPTY-STORE (and NOT UNDECLARED-STORE),
    c12 an EMPTY declared region is healthy, c13 a non-directory region is DEAD-REGION, c14 a region covering a
    declared store is refused, c15 a region covering the repo is refused, c16 a region does NOT loosen the rule
    elsewhere. `--selftest` 16/16 fire; `--check` exit 0 (0 faults).

BOUNDARY (what this fix does NOT do): it does not stop a probe from writing. MEASURED 2026-09-26: 159 of 174
`sqlite3.connect(` sites in pipeline|scripts|tools do NOT open `mode=ro`, so a blanket lint would be FATAL on day
one - it must be a NAMED shrink-only ceiling, not a gate. OWED: (a) a RECEIPT per pre-image (the writer names
file + bytes + sha256) so a region cannot hide an unrelated store; (b) the read-only opener helper + the
shrink-only ceiling for bare connects.


## BUG-550 (MED - FIXED 2026-09-26) - the mint was a CLONE: D-2659 carried D-2658's files, bugs and rationale

MEASURED (2026-09-26S, by the PRE-COMMIT FORENSIC AUDIT of the A1 bridge + BUG-549 change-set, before the first
commit of either): config/decisions.yaml carried a record whose id, category and title were D-2659's (the
EMPTY-STORE / tombstone-region rule) while `files`, `bugs` and `rationale` were BYTE-IDENTICAL to D-2658's (the
content-keyed silent-repair SITE). A record that names the wrong files and the wrong bug is a FALSE RECORD: a
later reader following it lands in the wrong module, and the id's provenance claim is untrue.

ROOT CAUSE (class): MINTING HAS NO HOME. The record was minted by an ad-hoc heredoc that COPIED the previous
record as a template and edited only the fields the author remembered. scripts/recompute_decision_summary.py
re-derives counts and the stamp, so the SUMMARY stayed consistent - and NO rail compares a record's
`files`/`bugs`/`rationale` against its own `title`, or against the tree. The defect is invisible to every
existing rail because it is a MISMATCH INSIDE ONE ARTIFACT, and no rail reads two fields of one record together.

FIX (SAFE only because the record had never landed): the uncommitted record is REPAIRED IN PLACE - `files`,
`bugs` and `rationale` now describe BUG-549, and the rationale itself carries the repair notice. This does NOT
violate BUG-539 (minting is an APPEND, never a mid-file edit): BUG-539 protects HISTORY - a record that has been
committed and read - and this record's first commit had not happened. The summary was then re-derived
(source_sha256 moved), so the receipt and the registry agree again.

BOUNDARY / OWED (the CLASS is NOT fixed): minting still has no home and no validator, so the next mint can clone
again. OWED: a receipted minter that (a) asserts the id is the next FREE id, (b) requires a non-empty title,
rationale and at least one file and one bug, (c) asserts every named file EXISTS in the tree and every named bug
EXISTS in the register, and (d) asserts the rationale NAMES the bugs it is attached to - with a known-answer
control that FAILS on a cloned payload. Until then: every minted record is read back FIELD BY FIELD before its
commit (this audit is the procedure, not a promise).

## BUG-551 (LOW-MED - FIXED 2026-09-26) - the bridge exited 2 on the golden side while the config declared NOTHING

MEASURED (2026-09-26S, by the same pre-commit forensic audit): `python3 scripts/build_anchor_store_bridge.py
--check` returned exit 2 with `golden: 2 row(s) unjoined` while `store_bridge.declared_unresolved` was `[]` and
the two rows (S4-GOLD-MINED-00478, S4-GOLD-MINED-00600) were declared NOWHERE. The module docstring AND the
justfile comment both state that 2 means "unresolved rows the config DECLARES" - so the rail's own stated
contract was FALSE at the moment it was about to land, and the golden side of the tri-state was an undeclared
blanket: ANY future golden row that failed to join would have been silently downgraded from DRIFT (1) to
owner-owed (2) - the loudest available place to hide a real receiving-side breakage.

ROOT CAUSE (class): the CORPUS side had a declaration requirement and the GOLDEN side did not - ONE RULE WITH
TWO IMPLEMENTATIONS, the lenient one on the receiving side (D-2646). The two rows ARE ambiguous under the
declared normalization (`histogram: {ambiguous: 2}`), so refusing to PICK them is CORRECT (D-2658); what was
wrong was an exit code claiming a declaration that did not exist.

FIX: `declared_golden_unjoined:` in config/anchor_family.yaml#store_bridge names both rows with a why, and the
verdict now applies ONE rule to BOTH sides: an UNDECLARED unjoined golden row is DRIFT (1); a DECLARED one is
owner-owed (2); an entry whose why is thinner than MIN_WHY is DRIFT (1); and a declared row that starts JOINING
is owner-owed (2) - the ceiling is SHRINK-ONLY and it shrinks LOUDLY. The derived document now also records
`unjoined_detail` (id, cause, candidates), so the receipt carries the CAUSE and not only the id. VERIFIED: 19/19
known-answer controls (was 15), including all four golden-side cases; `--check` exit 2 with "golden: 2 row(s)
unjoined, all DECLARED in config".

## BUG-552 (MED - FIXED 2026-09-26) - the mint had no FIELD-LEVEL join: a record could cite a file that exists nowhere, a bug the register has never seen, or another record's payload, while every rail stayed green

MEASURED (2026-09-26T, opening this step): scripts/recompute_decision_summary.py --mint already validated that a
record is a mapping carrying id/state/category/title/decision, that its state is canonical, that its id is not
ALREADY minted, that the append preserves the registry prefix (BUG-539) and that the result re-derives
(D-2648/D-2649). It validated NOTHING about the record's own FIELDS: a mint could name a file that exists
nowhere, cite a bug id the register has never seen, omit 'bugs:' entirely (MINT_REQUIRED did not list it), and
could carry the byte-identical payload of the record above it. That last one is not hypothetical - it is BUG-550
(D-2659 carried D-2658's files, bugs and rationale), found BY HAND, because NO RAIL READS TWO FIELDS OF ONE
RECORD TOGETHER.

ROOT CAUSE (class): the validation was about the record's SHAPE, never the record's CLAIM. A claim carries fields
that can be joined to reality - this file exists, this bug exists, this id is the next one - and the join was
missing at the one moment it is cheap: the mint.

FIX (D-2660): four clauses inside the EXISTING mint home. NO NEW SCRIPT, because a second minter would be exactly
the D-2646/BUG-502 defect (one rule, two implementations) that this register exists to prevent. (1) the id MUST be
the next FREE id - a skip is a hole indistinguishable from a deleted record; (2) 'bugs:' is REQUIRED and every
cited bug id MUST be in governance/bug_status.json (register the bug BEFORE the decision that cites it); (3) the
record's payload MUST name at least one of its OWN bugs - the BUG-550 tell, where the payload named BUG-542 while
the record claimed BUG-549; (4) every cited file MUST exist and 'files:' MUST be a LIST (one record on disk
carries a comma-joined blob naming a path that exists nowhere). A WHOLE-PAYLOAD CLONE (same files AND same bugs
AND the same payload opening) is REFUSED by name. 10 known-answer controls - including the control record itself
having to PASS - wired into just health as --selftest.

FORWARD-ONLY, DECLARED (the boundary, stated the BUG-521 way): across the 790 records already on disk, 559 carry
no 'title', 128 name no payload key at all, 26 file citations do not resolve and 1 'files' value is a blob. The
rule therefore applies at the MOMENT OF MINT and never rewrites history (the registry is append_only and its
receipt is a PREFIX rule, BUG-539). The historical vector is deliberately NOT declared as a shrink-only ceiling:
a ceiling whose only way down is rewriting landed history is a ceiling nobody can lower, and BUG-539 forbids the
rewrite.

VERIFIED: --selftest 10/10 controls fire; a cloned payload is REFUSED end-to-end; a nonexistent file citation is
REFUSED end-to-end; --check stays green with the registry stamp UNMOVED - the patch touched the WRITER, not the
record bytes.

## BUG-553 (MED - FIXED 2026-09-26) - two fields of every registry row were joined by NOTHING: `table:`/`column:` were written by a human, a rail read neither, and a row could cite a coordinate that exists NOWHERE while `just health` printed ok

MEASURED (2026-09-26T, opening this step): config/derivations.yaml declares 10 derived values, each with a
`table:` and a `column:` - the coordinate that says WHERE the value lives. scripts/check_derivation_homes.py read
`home`, `status` and `name`, and NOTHING ELSE: its own docstring promised the registry is JOINED "to reality on
every run" while the coordinate half of every row was read by no code at all. Any of the 10 rows could have cited
`no_such_table.no_such_column` and the rail's verdict would not have moved. That is the BUG-550 class a second
time: a mismatch INSIDE one record that no rail can see, because no rail reads two fields of one record TOGETHER.

ROOT CAUSE (class): a registry field written by a hand and read by no machine is a comment with a colon. The
registry was treated as prose to be maintained, not as a claim to be joined - and a claim that nothing resolves
is indistinguishable from a claim that is true.

FIX (D-2661): a new clause in the EXISTING rail home (no new script: a second derivation rail would be the
D-2646/BUG-502 defect this register exists to prevent). Every row's coordinate must RESOLVE to the census home
config/derivations.yaml#coordinate_homes declares for its `table`, in one of TWO machine-distinct kinds:
  * document     - the path must EXIST, read as a MAPPING, carry `column` as a TOP-LEVEL KEY, and name an
                   existing producer under the declared `producer_key`.
  * store_census - DELEGATED: the census `census:` names must exist, its `rail:` must exist, its declared
                   `table` must EQUAL the row's table, and `column` must appear in the membership map at the
                   DECLARED dotted path `membership:` (never a code default, D-2644).
A cited table with NO entry fails CLOSED - so a new row cannot cite a new coordinate until its census home is
declared, which is the guarantee, not a side effect.

WHY DELEGATED, AND WHY IT MUST NEVER OPEN THE STORE: the column question ALREADY has a home -
scripts/check_store_columns.py measures all 75 columns of `fbs` against declared roles, and a second census of one
fact is the defect (D-2646). Separately, MEASURED here: opening the governed store read-only and reading
sqlite_master raises `sqlite3.OperationalError: no such module: vec0` (the store carries a vec0 virtual table;
pipeline/stage6_commit.py documents its own first-run crash on the same module). A "verify the table exists" join
written the obvious way would have been FATAL ON DAY ONE for all 7 store rows. The rail consumes the owning
census's MEASUREMENT instead: existence in the store stays that rail's proof, and both rails run in the ladder.

CASCADE FOUND AND FIXED BEFORE THE EDIT (the audit step, not an afterthought): config/silent_repair.yaml declared
this rail's own silent-repair site by a COORDINATE (`lines: [78]`), the exact D-2658/BUG-542 pattern. The D-2661
edit inserts lines above 78, so the legacy entry would have reported ONE site twice - STALE at 78 and FATAL DRIFT
at the new number - and aborted `just health` above every rail below it. Re-keyed to `match:` FIRST, then the rail
was edited. The class is now applied to its own register.

NEGATIVES SEEN TO FIRE ON LIVE BYTES (BUG-492: a detector nobody has seen fail is a comment). The registry was
mutated and restored three times, byte-identical each time (sha256 verified):
  * a column the owning census is BLIND to  -> rc=1 "column 'no_such_column_zz' is absent from
    config/store_columns.yaml#measured.columns (75 column(s) measured)".
  * a document key that does not exist      -> rc=1 "...carries no top-level key 'no_such_key_zz'".
  * a cited table with no census home       -> rc=1 "cites table 'no_such_table' but
    config/derivations.yaml#coordinate_homes declares no census home for it - the coordinate is UNVERIFIABLE".
Controls: 7 -> 23, wired into `just health` as --selftest (16 new, one per arm, including the two that must
fail CLOSED rather than open: an unresolvable `membership:` path and a census with no declared membership).

FORWARD-ONLY, DECLARED (the boundary, stated the BUG-521 way): the rail now proves EXISTENCE and MEMBERSHIP of
every cited coordinate - NOT that the stored value equals the home's output. Value parity remains each row's
`parity_rail`, as the rail's SCOPE has said since it was written.

## BUG-554 (MED - FIXED 2026-09-26) - the third declared field of every registry row was joined by NOTHING: parity_rail named the script that RE-DERIVES the value and no rail read it, so a row could cite a script that exists nowhere - or one the ladder never runs - while just health printed ok

MEASURED BEFORE ANY RULE. config/derivations.yaml declares 10 rows. A grep over pipeline|scripts|tools for parity_rail found ZERO readers: the field was a claim written by a human and joined by no machine - BUG-553 exactly, one field over (D-2661 joined table:/column:; home: was already joined by the one-home rule). MEASURED: 7 rows name a rail over 3 distinct scripts; the 3 nulls are exactly the 3 NON-homed rows. All 3 named scripts ARE invoked by justfile, so the join is green on live bytes and it is a GUARANTEE rather than a report: any NEW row that names a rail has it resolved from now on.

THE RULE (D-2662). A cited parity rail must RESOLVE - the path must EXIST, and the DECLARED ladder (config/derivations.yaml#enforcement.ladder = justfile, C12: never a path hardcoded in the rail) must INVOKE it. A mention inside a comment is NOT a run and the path must be a WHOLE TOKEN (a substring test would read scripts/x.py.bak as scripts/x.py, the BUG-528 class). A row claiming status homed may NOT leave parity_rail null: that joins TWO FIELDS OF ONE RECORD (the BUG-550 class), so a homed claim with nothing behind it FAILS instead of passing as unexamined. An absent or unreadable ladder is DRIFT (C16).

WHY THE SCOPE STOPS AT EXISTENCE + INVOCATION. Comparing re-derived bytes against the stored corpus is each parity rail's OWN measurement (check_serving_gate, check_s5_score_axis, recompute_decision_summary). Re-measuring it here would be a SECOND HOME for one fact - the defect this registry exists to prevent (D-2646).

VERIFIED. 9 new known-answer controls (23 -> 32), including a comment-only arm, an @-prefix arm that must PASS, a non-homed null arm that must PASS (anti-overreach) and a substring arm. 4 negatives SEEN to fire on LIVE bytes (registry mutated, then restored byte-identical): a rail that does not exist; an existing script the ladder never runs; a homed row with parity_rail null; the ladder declaration removed (fails CLOSED). No cascade: silent-repair debt is UNCHANGED at 17 of ceiling 17 (the new reader returns a STATE, it does not repair) and check_config_defaults stays rc=0 over the same registry bytes.

FILES: scripts/check_derivation_homes.py, config/derivations.yaml.



## BUG-555 (MED - FIXED 2026-09-26) - a provenance field asked whether a SUBSTRING occurred anywhere in the raw text, so it reported `true` on an artifact whose labels are traceable to NOBODY (the BUG-528 class, inside the block whose whole purpose is BUG-450 prevention)

ROOT CAUSE. `scripts/definition_nli_verify.py` gained an additive provenance block (D-379/D-382) and answered
"does this input declare a rater?" with `"coder" in <the whole input read as one string>`. MEASURED 2026-09-26 on
the live stage5 checkpoint (102,936,020 bytes): the substring is present, and NOT ONE of the 400 records scanned
carries a `coder` key ("encoder", "decoder" and "coder_version" all match it). So the field printed `true` on
exactly the artifact BUG-450 exists to expose - and it did it by reading the whole input a THIRD time (once to
score, once for `_sha`, once for this test) to answer a question the scoring pass had already parsed.

SECOND DEFECT, SAME READ: the legacy rule was `... if path.exists() else None` - an absent input answered None,
which is not a state anyone can act on; the new rule derives from the PARSED rows, so absence cannot arise.

FIX. `coder_coverage(rows_scored, rows_with_coder)` is one home (D-2646) for one rule: a MEMBERSHIP test on the
parsed rows, computed inside the SINGLE scoring pass (the extra 102 MB read is gone). It reports `rows_scored`,
`rows_with_coder` and `coder_key_present`, where present means present on EVERY scored row - a PARTIAL presence
can never be collapsed into a bare `true`. `_read_input_text` (now dead) is DELETED (C19), and the stale
reference to it in `_open_input`'s docstring with it.

CONTROLS, SEEN TO FIRE (BUG-492): 0 -> 4, `--selftest` 4/4, reachable without NLI or a menu, and also run by the
module's existing verification mode `--selfcheck` so the documented check proves the rule too:
  * the raw text contains the substring (inside `encoder`) while NO row declares a coder -> that is not a membership;
  * a coder on EVERY scored row is reported present;
  * a coder on SOME rows is NOT collapsed into a bare true (the counts stay visible);
  * an EMPTY artifact reports ABSENT, never vacuously present.
SEEN ON LIVE BYTES, this session: legacy rule True; membership rule `rows_scored 40, rows_with_coder 0,
coder_key_present False`.

MEASURED BEFORE ANY BYTE WAS PINNED - the A/B the D-382 re-pin never had. The same frozen probe (stage5
checkpoint, `--limit 40`, digests of both arms recorded) was run under the committed HEAD bytes (ca91c520..., the
D-356 pin) and under the final bytes: `results` sha256 a4c9a1d6f37433a1 in BOTH, counts 231/21/0 in BOTH, and
`only_in_B = ['provenance']`. The uncommitted delta and this fix are therefore SCORE-NEUTRAL BY MEASUREMENT, not
by claim. NOTHING was laundered: the digest is re-pinned under a NEW decision (D-2663), never under D-382.

## BUG-556 (HIGH - D-2664, FIXED 2026-09-26): the archive rail's INPUT was mutated by the very ladder that checks it - a transient SQLite sidecar was counted, so the index moved with zero content change

FOUND BY: the forensic question asked of the BUG-537 remedy ("did my own fix create a blindspot?") turned out to
point at the rail's INPUT, not its output. Measured, not inferred: `archive/db_backups/maxwell_pre_index_20260917.db-shm`
carried mtime 2026-09-26T21:44 - written during the `just health` run that was checking this rail - with its
`-wal` sibling of the same class beside it. A/B on ONE tree, one config field apart: with the sidecar COUNTED the
`db_backups` entry is `files: 3 / bytes: 135528448 / modified: 2026-09-19` (the digest-carrying pre-image above);
with it DECLARED EXCLUDED it is `files: 1 / bytes: 135495680 / modified: 2026-09-17` - the newest bytes that are
actually content. That single field is why the index digest moved between generations, and why this rail could go
RED with ZERO content change.
CLASS: BUG-469's class, incompletely fixed. That bug named a directory date moving because a browser wrote
`.DS_Store` into it; `-wal/-shm/-journal` are the SQLite face of the same fact - a file that appears and moves
whenever any process OPENS the database beside it. A rail whose own ladder mutates its input is a rail the owner
learns to ignore (BUG-462).
FIX (D-2664). The declared ignore class gains `-(wal|shm|journal)$` in the SAME one home as the names and globs
that exclude them, the excluded objects are REPORTED rather than skipped (BUG-537), and the class is held by the
known-answer control `transient_sidecar_ignored` (a sidecar excluded, a real `.db` NOT).
## BUG-557 (MED - D-2665, FIXED 2026-09-26): the rail set had no registry, so a rail NOTHING RUNS and a WRITER whose remedy was never proven were undetectable BY CONSTRUCTION

FOUND BY: four sessions of "each fix breeds the next bug" (BUG-492, BUG-537, BUG-546, BUG-556) - the same three
mechanical classes from four angles: (i) a rail nothing runs; (ii) a printed verdict that disagrees with its exit
code; (iii) a remedy or INPUT nobody controls. 78 ladder invocations and 40 `check_*/verify_*` scripts had no
registry, so "which invariant has no owner" was answerable only by inspiration.
MEASURED THE MOMENT THE REGISTRY RAN: `rail registry: 78 ladder invocation(s), 55 rail(s) invoked, 40 rail script(s)
on disk, 3 declared dormant, 3 declared writer(s)` - and its FIRST finding was about ITSELF: `(i) a rail NOTHING RUNS:
scripts/check_rail_registry.py is invoked by no declared ladder recipe and is declared dormant nowhere` (BUG-492).
FIX (D-2665): `config/rail_registry.yaml` + `scripts/check_rail_registry.py` - the ladder's own text is parsed (the
guard class is READ from the line, never inferred), every rail must be invoked or declared dormant with an exerciser
that MUST EXIST (`gitdir:hooks/pre-commit` resolved from git: the git dir lives outside the synced tree, BUG-500),
every declared guard is matched against the ladder (a disagreement fails CLOSED), and every declared WRITER must have
`--selftest` run BY THE LADDER (class iii: a rail that replaces bytes makes a claim). 7 known-answer controls over
SYNTHETIC ladders; no NLI, no live-tree write.
FOUR DEFECTS IN THE REGISTRY WERE CAUGHT BY ITS OWN CONTROLS BEFORE IT WAS WIRED: the invocation key kept the
`python3 ` prefix (so a guards lookup and a `--selftest` obligation both missed by a prefix, and one control passed
for the WRONG reason - it counted every (i) fault instead of the one it names); a dormancy entry whose script is NOT
on disk was never examined; the census called `len()` on an int (a crash the control harness could not reach); and the
hook path was a hardcoded `.git/hooks`, a lie in this repo (BUG-500).
NO CASCADE, MEASURED: `just health` rc=0 with the registry in the ladder and the ladder's FAIL/ERROR set
DIFF-IDENTICAL to the pre-patch log; the two remaining FAILs are the pre-existing OWNER gates (ANCHOR-4 drift; the
depth/domain contract's 38 hard findings, suppressed by design under a `status: proposed` contract).
DECLARED: no delegate signature is claimed for this patch - the gemma-4-E4B-it-MLX-4bit review returned a PLAN, not
a verdict, and a review that never ran must not be cited as one (D-2660's rule applied to delegation).

## BUG-558 (HIGH - D-2666, FIXED 2026-09-26): the certified ANCHOR-4 workbook on the live path was a FOREIGN BODY, and the encoding declaration had been reconciled TO the foreign body instead of the artifact

FOUND BY: RATIFYing the depth/domain contract (D-2666) and then asking the one question a point fix never asks - "which generation of these bytes is this?". The ruler's 38 hard MENU_OFF_TOKEN findings looked like 38 illegal owner answers; they were 38 symptoms of the wrong generation of file.
MEASURED: the live path held sha256 574aafef64f0cff7 (92135 B, mtime Sep 25 13:55), which matches NO historical revision of that path, lacks the normalizer's three added columns (primary_domain, domains_final_raw, depth_final_class), keeps 0 domains HEAD does not hold, LOSES 43 domain answers and 42 depth answers that HEAD holds, and scores 38 hard + 43 owner_blocked against the ruler - while HEAD's bytes score hard 0, owner_blocked 0. `domains_final_raw` was blank on 104/104 rows where HEAD is 147 non-blank / 0 blank.
FIX: the foreign bytes were preserved to backups/anchor_adjudication_workbook_20260924.csv.PRE_CLAUDER_RESTORE_20260926T202715Z plus its fixlog sibling (R-D410: never destroyed); the certified bytes were restored from `git show HEAD:` through tempfile->fsync->os.replace (C6) -> f2778a488610cbf1 (99332 B); the owner's DECLARED rulings were re-applied through the sanctioned applier -> live 972def3224a1abba; the pre-ruling image is declared as a revision locator and sealed, so the intermediate state re-derives from git on every run.
WHY IT WAS INVISIBLE: the ONLY rail that could have refused those bytes was the depth/domain contract, and it was `status: proposed`, so `--gate-if-active || [ $? -eq 2 ]` SUPPRESSED its exit code. Every other rail was green because it was SILENT. That is the evidence for the RATIFY recommendation, not an argument for it.
SECOND DEFECT IN THE SAME EVENT (the cause of the cause): config/reconciliation.yaml declared the workbook `mac_roman`, measured on 0xCA at offset 42564 - a byte of the FOREIGN BODY. A declaration derived from whatever bytes are on disk turns a clobber into a certified-looking artifact: the reader stops failing closed and the file is laundered. The declaration named the INPUT while the OUTPUT lives at that path. All three homes now say `utf-8`, with the reason and the measurement beside them.
VERIFICATION: `just health` rc=0; `just health-deep --strict` rc=0; verify_handoffs rc=0 (6 paths / 13 digests / 3 revisions all agree with their bytes); the 3 formerly declared-red depth/domain tests PASS (12 passed in 0.75s); and the D-2649 encoding join was SEEN to refuse this very disagreement before it was fixed - a control proven on real data, not asserted.

## BUG-559 (STRUCTURAL - D-2666, OPEN 2026-09-26): a receipt can be cut over bytes joined to NO revision, so `mutability: human_authored` certified a foreign body for as long as nobody read the path

FOUND BY: BUG-558 - `scripts/verify_handoffs.py` reported `ok anchor4_workbook: ... unchanged (574aafef64f0cff7)` WHILE the path held foreign bytes, because the receipt (stamp 2026-09-26T10:34:24Z, code_sha 96b1e9c+dirty) had been cut over them. The rail was not broken; it verified exactly what it was told. What is MISSING is a join to the certified tree.
MECHANISM: a receipt is {digest, size, mutability, code_sha, stamp, origin} about BYTES, and nothing requires those bytes to be a revision of the repo or a declared DERIVATION from one - so receipt()/--backfill can bless whatever a process finds on disk, including a body that has never existed in any revision of that path.
SECOND INSTANCE (same class, in prose): governance/ANCHOR_ADJUDICATION_NORMALIZATION_20260925.md quotes the workbook digest as `f2778a488610cbf1...`, TRUNCATED with an ellipsis, so no reader can ever join it to bytes. A digest that cannot be resolved is a claim that can never be refused.
FIX (owed): make verify_handoffs refuse a receipt whose (path, digest) is neither (a) the live bytes' digest AND `git_bytes(HEAD, path)` for that path, nor (b) a declared revision locator joined to a declared applier run. Ship it with a known-answer control that has been SEEN to refuse a receipt over unrevisioned bytes (R5), then re-cut the workbook's receipt against the committed revision so the invariant holds by construction rather than by discipline.
STATUS: today the workbook's live digest IS recorded and IS re-derivable (its pre-ruling image is a sealed revision locator), so this specific lie cannot repeat HERE - only the CLASS can.

## BUG-560 (MED - D-2666, OPEN 2026-09-26): the sanctioned applier rewrites a `human_authored` artifact OUTSIDE write_guard and leaves no mutation receipt

FOUND BY: auditing the write path of the one script the owner's rulings are applied through. config/artifact_ownership.yaml declares the workbook's ownership invariant is "ENFORCED over the whole artifact and receipted" through write_guard.write_rows(mode="merge", owned_keys=...), but scripts/apply_workbook_rulings.py writes with mkstemp->os.replace directly and appends to the fixlog with a bare open("a").
MEASURED: the applier contains no write_guard call and leaves no governance/MUTATION_JOURNAL.jsonl receipt; the only record of the byte change is the fixlog line plus the new digest.
RISK: this is the ONE writer that exists to stop a normalize re-run from reverting the owner's own rulings (D-393), so its silence is exactly where a revert would hide. It IS declared (config/anchor_workbook_fixes.yaml#rulings_io), which is why the rail registry cannot see it as undeclared - declaration is not receipt.
FIX (owed): route the applier through write_guard with owned_keys = the ruled columns, so the change is receipted like every other owner-cell write, and add a known-answer control that refuses an out-of-scope column.

## BUG-561 (MED - FIXED 2026-09-26): a will_not_touch FAMILY member (a sync-client RENAME of the owner instrument) was rewritten WHOLESALE in the working tree

FOUND BY: the pre-commit forensic audit of the D-2666 change-set - rail 4 family rule (BUG-528) applied to the DIRTY SET, not only to the staged set, for the first time.
MEASURED: governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv is TRACKED (a Dropbox rename of the owner blind sheet) and its working-tree bytes differ from HEAD in 151 of 151 lines - a whole-file rewrite from the 2026-09-26T10:32 encoding pass - while rail 4 declares the family governance/ANCHOR4_DEPTH_BLIND_SHEET_*.csv will_not_touch.
WHY IT MATTERED: the owner instrument was editable through its COPY while forbidden through its NAME (exactly BUG-528), and a rail that audits only the STAGED set cannot see it: an uncommitted rewrite of a protected artifact is invisible until someone stages it, and by then the edit already exists.
FIX: the rewritten bytes were PRESERVED to backups/ANCHOR4_DEPTH_BLIND_SHEET_20260923.Copy-of.PRE_revert_20260926T230500Z.csv (R-D410: never destroyed) and the path was restored with git checkout HEAD -- , the remedy rail 4 itself names. The DEEPER question (a sync client rename of an owner instrument being TRACKED at all) is a plan revision plus owner gate, not an edit: left OPEN.

## BUG-562 (STRUCTURAL - OPEN 2026-09-26): a GRANTED config can be committed while its CONSUMER sits in will_not_touch, so a commit can declare a gate whose implementation is not in it

FOUND BY: the pre-commit audit of the reconciliation set. The plan says what a session MAY touch; nothing checks that a changed artifact CONSUMER travels with it.
MEASURED: config/serving_gate.yaml (+67 lines, GRANTED by config/*.yaml) is read at pipeline/serving_gate.py:22 (CONFIG_PATH = ROOT / config / serving_gate.yaml), a file the plan declares will_not_touch (+173 lines); the GRANTED tests/test_serving_gate.py exercises that module. Committing the granted half alone would put into history a declaration whose implementation is absent and a test whose subject is absent - D-405 violated by a COMMIT SET, not by one artifact.
FIX (owed): a PAIRING check - refuse a commit in which a changed granted artifact whose declared CONSUMER is withheld/absent is present - and the plan rule that a config and its consumer land in the SAME commit. Until then the 53-path reconciliation set is NOT committable as one unit: it needs the owner pipeline/** crossing ack (a one-off, owner-acked crossing, never standing permission) or a per-path pairing split.

## BUG-561 CORRECTION (2026-09-26, same session): the "clobber" WAS the declared rev 3, and the REVERT was the defect
- **status**: MED - the report was WRONG IN ITS CONCLUSION; the damage was the repair. REPAIRED by restoring the bytes.
- **what was claimed**: a tracked sync-client rename of a `will_not_touch` FAMILY member had been rewritten WHOLESALE
  in the working tree (151/151 lines differ from HEAD, mtime Sep 26 10:32) -> reverting the path to HEAD was treated
  as the remedy. The bytes were preserved first (R-D410), which is the only reason this was recoverable.
- **what is MEASURED**: that diff was taken against HEAD, and HEAD carries rev 2. The receipts sealed
  526991cb / 203963 B at 08:46, 08:59 AND 10:34 - so the bytes at 10:32 were UNCHANGED and only mtime moved:
  nothing was rewritten. rev 3 = rev 2 + 3 UNNAMED trailing columns plus one stray cell, a spreadsheet save the
  repo ALREADY documents (`config/anchor4_interim_state.json#dropin_note`, BUG-493, "the save is owner-gated").
  Every row gains 3 trailing columns, which is exactly why every LINE differs in a diff.
- **the defect the revert created**: the write-locked digest 526991cb became an ORPHAN. `verify_handoffs` rc=1
  ("bytes CHANGED 526991cb -> bc1cc956", plus 2 orphan digests in `config/human_instrument_locks.yaml` and
  `config/anchor4_interim_state.json`), and `just health` fell at justfile line 49.
- **the near-miss**: rev 3's bytes exist in NO git ref. rev 1 = `git:075ae65` and rev 2 = `git:65a13c3` are declared
  locators; rev 3 has no locator, so the single `git checkout HEAD` had exactly one copy of a write-locked owner
  revision to destroy - the R-D410 backup taken minutes earlier.
- **REPAIRED**: bytes restored to rev 3 (526991cb) from `backups/ANCHOR4_DEPTH_BLIND_SHEET_20260923.Copy-of.PRE_revert_20260926T230500Z.csv`;
  `verify_handoffs` rc=0 (13/13 digests, 3 revisions re-derived, 11/11 cross-declarations resolve),
  `check_human_instruments` rc=0 (7 locked, all protected columns byte-identical), `just health` rc=0.
- **the rail-level lesson**: a diff against HEAD is NOT a clobber test. The test is against the DECLARED revision
  (locks + receipts), because a detector that fires on "worktree != HEAD" fires on EVERY sanctioned uncommitted
  revision. The prior session's structural observation stands unchanged (rail 4 audits the STAGED set, so a
  worktree-only change to a protected family member is invisible to it) - that deeper question is still OPEN.

## BUG-562 UPDATE (2026-09-26): the INCIDENT is closed by construction; the RAIL is still OWED
- CLOSED BY CONSTRUCTION: the reconciliation commit e3f94f4 carries `config/serving_gate.yaml` AND its consumer
  `pipeline/serving_gate.py` AND `tests/test_serving_gate.py` in ONE commit, under the owner's CROSS (plan entry 23,
  spent by that commit). The declaration and its implementation are no longer separable in history.
- STILL OWED: nothing yet REFUSES a commit set in which a changed GRANTED artifact's declared consumer is withheld.
  The fix is a PAIRING check with a control SEEN to refuse the serving-gate pair, so the next commit set cannot
  re-create the mismatch silently. Until that lands, the property holds only because a session looked.

## BUG-563 (MED - OPEN 2026-09-26): `backups/**` is neither GRANTED by the plan nor IGNORED by git
- **detail**: 92 of the 163 dirty entries are `backups/*`, and those are EVIDENCE files that C13/R-D410 REQUIRE a
  session to write. So a session is obliged to create paths it may not commit, and git is not told to ignore them:
  the tree can never be clean, and the evidence trail is unversioned BY ACCIDENT rather than by decision.
- **shape**: the same defect the archive census refuses on a smaller scale - "an on-disk object is either INDEXED
  or DECLARED excluded, never silently absent" (`archive/index.yaml#excluded`, BUG-537/BUG-556).
- **fix owed**: ONE home saying which it is (an ignore rule carrying a declared disposition, or a `may_touch` grant),
  plus a rail that fails on a dirty path that is NEITHER granted NOR declared-excluded.
- **related**: the rail OUTPUT stores (`governance/MUTATION_JOURNAL.jsonl` - the R-D410 append-only receipt ledger,
  100 KB, `governance/INSTRUMENT_CONTROLS.jsonl`, `governance/METRICS.jsonl`, `drift_report_*`, `bench_preflight_*`)
  are in the same class: live outputs of rails, tracked by nothing.

## BUG-564 - the COMMIT BOUNDARY was a claim; the pairing rail is now a PROPERTY (D-2669) - 2026-09-26

STATUS OPEN (narrowed). MEASURED: the hook at gitdir:hooks/pre-commit is the strictest gate in the system
(RAIL 0/3/4/5) and it lives OUTSIDE the synced tree (BUG-500): not in git, so no diff, review or backup shows a
deleted line. One control already existed - a hand-edit was REFUSED at once by the ladder ("re-install: bash
scripts/install_git_hooks.sh") - so the installed hook is joined to its tracked SOURCE. What was NOT declared is its
REQUIRED TEXT: now declared in config/rail_registry.yaml#commit_boundary and verified line-by-line against the bytes
by check_rail_registry.py, with a DELETED-line control SEEN to refuse (9/9 controls fire).
BUG-562 is CLOSED BY CONSTRUCTION in the same act: scripts/check_declaration_consumers.py --staged REFUSES a commit
set in which a staged declaration's declared consumer is in NEITHER HEAD NOR the index - the exact incident shape -
with 11 synthetic controls. STILL OPEN: the hook ROUTE itself (a git dir re-created by a clone, or a hook installed
by hand, is not a declared subject); and BUG-563 (backups/** + the rail output stores: neither granted nor excluded).

**BUG-559 STATUS (2026-09-26, FIX LANDED - the join is now a property, D-2670).** The owed fix was *make verify_handoffs refuse a receipt whose (path, digest) is neither the live bytes' digest AND git_bytes(HEAD, path), nor a declared revision locator*. It is landed as a new check class, `provenance`, with FOUR joins and one declared escape:
JOIN (measured, `5/6 receipt(s) re-derivable (head=2, prefix=1, declared=2; unrevisioned=1)`):
  * `head` - the receipted digest IS this path's digest at git HEAD (a receipt over a revision);
  * `prefix` - the path is append_only and the receipted bytes are its RETAINED PREFIX, re-derived by truncating to the receipted length (the BUG-540 rule); this is how `config/decisions.yaml` (629488 of 635398 bytes) is joined;
  * `revision` - a declared `revision_locators` entry for THIS path (its bytes re-derive from `bytes_at`);
  * `declared` - named in `config/handoffs.yaml#receipt_provenance.unrevisioned_declared` WITH the reason no store can hold the bytes (the two gitignored run-root checkpoints, `.gitignore:73`).
WHY `head` ALONE WOULD HAVE BEEN A LIE: a receipt cut YESTERDAY over a file committed SINCE is legal and would have been refused - the BUG-492 shape (a rule never seen to pass). Conversely a SAME-LENGTH live copy is deliberately NOT a join: the live path is the same copy, so "the bytes are on disk and the receipt describes them" is exactly the circularity this bug is about.
THE ESCAPE IS A DECLARATION, NOT A DEFAULT and is joined in BOTH directions (D-405): a receipt over unrevisioned bytes that is not named is refused, and an escape no live receipt matches is DRIFT. `max_unrevisioned: 2` is a SHRINK-ONLY CENSUS - honestly, a census, not the enforcement.
MEASURED REFUSALS (each SEEN, R5/BUG-492): a same-length live copy -> unrevisioned; a foreign body -> unrevisioned; a digestless receipt -> unrevisioned; a stale escape -> rc=1 DRIFT; census raised to 3 -> rc=1 DRIFT. Selftest green (7 provenance cases + the escape join).
LIVE VERDICT TODAY: rc=2 owner-owed, naming exactly ONE object - the owner drop-in at 526991cb17287006 (203963 B), whose receipt is re-derivable from NO store because git HEAD still carries the superseded rev 2 (bc1cc956). That is BUG-493's gate, now MECHANICAL instead of remembered: **the PROMOTE of rev 3 clears this line to 0.**
REMAINING (narrowed, not closed): a receipt over an EARLIER COMMITTED revision is reported unrevisioned (the remedy is a declared revision locator), and the two run-root escapes are held by census rather than by a store that could hold 100MB bodies.

**BUG-493 STATUS (2026-09-26, PROMOTE LANDED - owner word 'Promote', D-2671).** rev 3 (526991cb, 203963 B) of the
write-locked owner drop-in is landed as the TRACKED REVISION of its own path. MEASURED BEFORE: git HEAD carried the
SUPERSEDED rev 2 (bc1cc956), the live path held rev 3, verify_handoffs returned rc=2 owner-owed naming exactly ONE
object (the drop-in, UNREVISIONED - BUG-559), and rev 3's only other copy was a '.bin' blob under .gitignore:61.
MEASURED AFTER: 'provenance: anchor4_depth_sheet_owner_dropin -> head', rc=0; the join is the receipt (13 records,
all 526991cb) against the COMMITTED revision, with NO re-cut and NO new record. HOW: an owner-acked ONE-OFF crossing
permit (widening_log entry 24, 'crossed:' naming ONE path), NOT a may_touch widening - the path is will_not_touch by
FAMILY (BUG-528) and a may_touch entry is STANDING permission. THE OTHER PROMOTION IS STILL OWED: BUG-431's CONTENT
promotion (the owner's complete 150/150 pass merged INTO the tracked ANCHOR4 sheet, retiring
config/anchor4_interim_state.json) remains an OWNER GATE - this commit wrote no sheet.

**BUG-558 OWNER RULING (2026-09-26, KEEP - 6th owner gate answered).** The two foreign-body copies
backups/anchor_adjudication_workbook_20260924.csv.PRE_CLAUDER_RESTORE_20260926T202715Z and its fixlog sibling are
KEPT (owner word: KEEP, on the assistant's recommendation). WHY KEEP IS THE HONEST DEFAULT: they are the only
surviving bytes of the foreign body a receipt once certified (574aafef64f0cff7, 92135 B, present in NO revision of
that path) - the evidence for BUG-559; PURGE would delete the specimen and leave the rule with nothing to be
re-derived against. The sealed blob 574aafef64f0cff7.bin also holds them, so the ruling costs no history and nothing
is deleted (R-D410: operators do not destroy a record).
## BUG-565 (STRUCTURAL, FIXED 2026-09-26 - commit 8a84622, D-2672): a git NAME-LIST read is not a
whitespace-split of TEXT
**WHAT WAS BROKEN.** `scripts/check_session_plan.py::_paths()` read the staged set with `git diff --cached
--name-only` and split it on WHITESPACE. ELEVEN tracked paths in this repo contain a space - INCLUDING the
write-locked owner instrument this rail exists to guard - so ONE path was audited as SEVERAL phantom paths.
MEASURED pre-fix, on a REAL synthetic index built from HEAD: `{scripts/space probe.py}` -> rc=1 naming
`scripts/space` + `probe.py`; `{governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv}` -> rc=1 naming 3
phantoms. **BOTH DIRECTIONS WERE BLIND AT ONCE:** the owner's one-off crossing permit could never GRANT the path
it names, and the BUG-528 family check could never FORBID the spaced rename. It was found by the rail REFUSING
THE OWNER'S OWN PROMOTE - a defect surfaced by the exact act it blocked, not by a code review.
**FIX.** `scripts/lib/git_subject.py#run_git_paths` owns the `-z` flag AND the NUL parse (ONE home, D-2646: a
caller cannot forget a flag it does not pass); rail 4 consumes it in both modes; `_staged_count_raw()` counts the
same way (it reported 12 paths for a 10-path set, and its before/after differential certified that defect because
it compared two readings, never a reading to reality); THREE controls run the rail END TO END through its own
`--index-file` over a real synthetic index and are SEEN red on the pre-fix code; RAIL 4's `--selftest` is now
wired into `just health` (a control nothing runs is a comment, BUG-508/510 class). MEASURED AFTER: 23/23
controls fire, live staged set 10 paths rc=0.
**REMAINDER (no live subject today, filed not fixed):** `scripts/verify_recalibration_pins.py::_staged_paths()`
still splits on whitespace (a spaced PIN path would escape the write gate); `scripts/lib/git_subject.py#selftest`'s
differential control compares two equally-split reads (it certifies the pin, not the parse). Same fact, other homes.

## BUG-566 (OPEN, MED): TWO RAILS, ONE FACT - git's OWN next-index is TOLERATED by rail 5 and REFUSED by rail 4
**MEASURED 2026-09-26 while landing 8a84622.** `git commit -- <path>` (a PARTIAL commit) makes git hand the hook
`GIT_INDEX_FILE=<gitdir>/next-index-46129.lock`. Rail 5 (check_declaration_consumers) TOLERATES and NAMES it:
"at the WRITE moment that IS the commit's subject, so it is accepted and NAMED". Rail 4's git-subject pin REFUSED
it ("names a DIFFERENT subject than the one audited"), so NO partial commit can pass rail 4 - and a rule that
cannot fire on the legitimate case is the exact shape BUG-527's own doc forbids. TWO HOMES, TWO RULES, ONE FACT
(D-2646). **REMEDY (not taken, it is the next step):** a DECLARED tolerance in
`config/repo_integrity.yaml#git_subject` - accept an ambient index that IS git's own next-index for the PINNED
git dir, refuse one that belongs to another git dir - with both controls (the legitimate partial commit is
TOLERATED; a foreign next-index is REFUSED). **NOT WORKED AROUND:** the fix landed through git's normal index API
(unstage -> stage, every digest re-measured; the drop-in stayed 526991cb), not `--no-verify`, and no rule was bent.

**BUG-493 STATUS (2026-09-26, CLOSED - MEASURED, not argued).** The owner's PROMOTE landed as `fe239df`:
`git cat-file -p HEAD:<path> | shasum -a 256` = 526991cb172870066224c8eee2b2c8fb23a7a28062e2bfc5a604cde2757e90ed
(203963 B). The receipt now joins by HEAD - `provenance: anchor4_depth_sheet_owner_dropin -> head` - and
`scripts/verify_handoffs.py` is rc=0 (was rc=2 naming EXACTLY ONE owner-owed object). The label fixes landed WITH
the bytes, so no declaration describes the superseded revision (config/handoffs.yaml REV 2->3;
config/human_instrument_locks.yaml comment - the sha256 line is the RULE and is unchanged;
config/anchor4_depth_annex.yaml's stale rev-2 digest reduced to a POINTER, D-2646). NO new receipt and NO rev-3
locator: 13 records already carry 526991cb/203963, and a locator exists to resolve SUPERSEDED bytes while rev 3
IS the head. **STILL OWED AND DISTINCT: BUG-431's CONTENT promotion** (merge the owner's complete 150/150 pass
INTO the tracked governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv, then retire config/anchor4_interim_state.json)
- an OWNER GATE; this commit wrote no sheet.


**BUG-493 STATUS (2026-09-26, CLOSED - MEASURED, not argued).** The owner's PROMOTE landed as `fe239df`:
`git cat-file -p HEAD:<path> | shasum -a 256` = 526991cb172870066224c8eee2b2c8fb23a7a28062e2bfc5a604cde2757e90ed
(203963 B). The receipt now joins by HEAD - `provenance: anchor4_depth_sheet_owner_dropin -> head` - and
`scripts/verify_handoffs.py` is rc=0 (was rc=2 naming EXACTLY ONE owner-owed object). The label fixes landed WITH
the bytes, so no declaration describes the superseded revision (config/handoffs.yaml REV 2->3;
config/human_instrument_locks.yaml comment - the sha256 line is the RULE and is unchanged;
config/anchor4_depth_annex.yaml's stale rev-2 digest reduced to a POINTER, D-2646). NO new receipt and NO rev-3
locator: 13 records already carry 526991cb/203963, and a locator exists to resolve SUPERSEDED bytes while rev 3
IS the head. **STILL OWED AND DISTINCT: BUG-431's CONTENT promotion** (merge the owner's complete 150/150 pass
INTO the tracked governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv, then retire config/anchor4_interim_state.json)
- an OWNER GATE; this commit wrote no sheet.


## BUG-566 (FIXED, MED): TWO RAILS, ONE FACT - git's OWN temporary index was REFUSED by RAIL 4 and TOLERATED by RAIL 5

MEASURED 2026-09-27 (git 2.39.5 Apple Git-154, --separate-git-dir layout). A PARTIAL commit (`git commit --
<path>`) makes git hand the pre-commit hook GIT_INDEX_FILE=<gitdir>/next-index-<pid>.lock; the file EXISTS at
hook time and git removes it on exit. Two rails read that ONE fact and disagreed: RAIL 4 refused the name (so
NO partial commit could pass) while RAIL 5 tolerated it. FIXED by D-2673: the ONE home
(scripts/lib/git_subject.py#index_subject) ADOPTS git's own index - directory == the PINNED git dir, basename
matches a DECLARED owner_name_globs entry, and the file EXISTS - and then READS it as the audit subject;
anything else ambient is REFUSED. The must-exist condition is not decoration: git reads a MISSING index as
EMPTY, so an absent file would report "all declared" over no bytes. MEASURED after: 13/13 module controls
(the D-405 join matched a live minted name this run) and 16/23/11 rail controls still fire.

## BUG-567 (FIXED, HIGH): RAIL 5's note was FALSE - it NAMED git's index while auditing a DIFFERENT one

MEASURED 2026-09-27. scripts/check_declaration_consumers.py DELETES GIT_INDEX_FILE from its child environment
(each of its git calls) and then printed "the index is the one git PASSED to this run (<path>) - at the WRITE
moment that IS the commit's subject, so it is accepted and NAMED" - while the audit read <gitdir>/index. Wrong
in BOTH directions: an OVER-refusal on a superset (the real index holds more than the commit set) and an
UNDER-refusal when the declaration lives only in the commit set. This is the class BUG-527 closed: a write
boundary rail reporting on a subject it never read. FIXED by D-2673 - the note is now the module's OWN
provenance string, so it cannot drift from what was read.

## BUG-568 (OPEN, MED): RAIL 0 does not pin its own git subject

scripts/check_repo_integrity.py shells git with the INHERITED environment and does not import
scripts/lib/git_subject.py, so a decoy GIT_DIR could decide what Layer 1 audits - at the moment the rail is
asked whether git metadata is intact. FILED, not papered over: the EXEMPTION is principled (this rail must run
when git metadata is BROKEN, so pinning it would make the recovery rail fail closed on the very condition it
reports). REMEDY: a pin DERIVED from the same home that tolerates an already-broken repository.

## BUG-569 (OPEN, LOW): the adoption NOTE has no RAIL-LEVEL control at a real partial commit

The rule's controls live in scripts/lib/git_subject.py --selftest (13/13, both directions, incl. a live minted
name). What is not yet seen to fire is the RAIL-level wiring: that a rail, run at a REAL minted ambient index
with no --index-file, prints the ADOPTED note AND audits that index. A rule whose wiring is never seen to pass
is a comment (BUG-492) - filed rather than left implicit.

## BUG-570 (OPEN, LOW): the duplicate BUG-493 CLOSED block is NOT byte-identical (the earlier claim was FALSE)

MEASURED 2026-09-27 while attempting the declared de-duplication: governance/buglog.md carries TWO
`**BUG-493 STATUS (2026-09-26, CLOSED - MEASURED, not argued).**` blocks, and the last one is NOT identical to
the text from the other to EOF. The dedupe therefore REFUSED (fail closed) and the file is untouched. Either
the two blocks genuinely differ (then the duplicate is BLOAT, not a copy) or something follows the last one.
The earlier session's "byte-identical" claim is RETRACTED here as unverified.

## BUG-493 (CLOSED, MED): REGISTER VISIBILITY REPAIR - the id lived only in prose, so the register that a MINT joins to could not see it (2026-09-27)

MEASURED. `grep -c '^## BUG-' governance/buglog.md` = 341 heading EVENTS -> 307 ids in governance/bug_status.json, and BUG-493 was NOT one of them: the id appears only inside bold prose (line 4966 `**BUG-493 (NEW).**` and three `**BUG-493 STATUS (...)**` lines). The parser anchors on `^#{2,3}` + `BUG-<n>`, so the id was invisible to the machine register - and therefore to the C15 count, to every handoff, and to the MINT GATE, which joins a decision's `bugs:` list to this register (D-2660 clause 2).
MEASURED CONSEQUENCE (2026-09-27, this session): minting D-2671 - the PROMOTE (fe239df) that CLEARS this bug - was REFUSED: 'cites bug(s) that are NOT in the register: BUG-493'. A TRUE citation refused because the register could not see a real, closed bug; the alternative (minting without it) would have been a decision that closes a bug it does not name.
REPAIR (an append, never a rewrite): this heading. It is a status EVENT in the shape the parser reads; the inline prose is untouched and the id now resolves for every join. The bug IS closed and has been since fe239df (rev 3, 526991cb, 203963 B, is the tracked revision of its own path - D-2671).
FORWARD CONTROL, named as forward-only: a decision that cites an unregistered bug is REFUSED at the mint (seen to fire tonight). NOT covered: an id that lives only in prose and no decision cites - filed as BUG-571.

## BUG-571 (OPEN, LOW): the register is fed by HEADINGS only, so an id written INLINE is real to every human and absent from every machine home (BUG-493 measured)

CONTEXT. The repair above is INSTANCE-level; the class is that governance/buglog.md is the register's INPUT and its parser reads exactly one shape. An author who writes a status in bold prose, a table cell or a checklist item creates a bug no rail can see.
MEASURED (2026-09-27): 341 heading events -> 307 ids; BUG-493 is the one id cited by a DECISION (D-2671) and by handoffs that the register did not carry, and the mint gate saw it exactly once - as a refusal.
WHY NOT A PROSE SCAN. A regex over every `BUG-<n>` token would invent ids from archaeology, quoted decisions and this very block (it names three). A control that reads PROSE reports on the prose.
REMEDY (owed): add the cited-by-decision join to scripts/bug_status.py - the register's own generator and declared writer - so the NEXT instance is an owner-owed RED LINE rather than a refusal discovered by hand at a mint (D-405: join both directions).

## BUG-572 (OPEN, LOW): a status word in a heading's TITLE decides a bug's status when the parenthetical slot names none (measured, with the flip list)

MEASURED. BUG-570 was filed OPEN and the register reads it CLOSED. Cause: when no candidate names a status word, the slot reader falls back to the WHOLE header, and this id's title carried a status word belonging to ANOTHER bug ('the duplicate BUG-493 CLOSED block is NOT byte-identical'). Same shape: BUG-562's last event folds to closed from 'the INCIDENT is closed by construction; the RAIL is still OWED'.
MEASURED CORPUS DELTA (2026-09-27): tightening the rule to 'the status region is the header up to the first colon' flips 10 of 397 heading events, and the flips are MIXED - it corrects this id and BUG-562, and WRONGLY flips BUG-347 and BUG-388 (whose status sits after the colon by design). 2 corrections, 8 regressions: the blanket rule is REFUSED on measurement.
REMEDY (owed): decide the slot question per SHAPE - a parenthetical slot that names no status word should not license a title read - with the 10-flip list pinned as known-answer controls, both directions.
REMEDY LANDED FOR THIS ID ONLY: an appended REOPENED event, so the register states the truth while the rule is argued.

## BUG-570 (LOW, REOPENED - the register read this id as CLOSED, see BUG-572): the duplicate BUG-493 block is NOT byte-identical (the earlier claim was FALSE)

RE-STATED because the first heading's title carried a status word from another bug's record and the register folded this id to CLOSED. The finding is unchanged and the file is untouched: the dedupe of the two BUG-493 status blocks REFUSED (fail closed) because the last two occurrences are not byte-identical to EOF - the earlier session's 'byte-identical' claim is RETRACTED as unverified.

## BUG-573 (OPEN, MED): a RED earlier in the ladder SHORT-CIRCUITS it, so every LATER fault is invisible (measured: the stale dormancy of scripts/check_session_plan.py)

MEASURED 2026-09-27. `just health` stood RED at line 61 (reconcile's D-405 join, two unresolved citations) for a whole
session. Repairing that red let the recipe CONTINUE, and the rail registry immediately fired a fault it had NEVER reported:
'scripts/check_session_plan.py is declared dormant and IS invoked by the ladder' - a STALE dormancy left behind by D-2672
when rail 4's --selftest was wired into the ladder. The fix did not create the fault; it UNHID it. The same prefix hid
whatever else stands after line 61.
WHY IT MATTERS. A recipe that aborts on the first failing line reports a PREFIX while it is read as a VERDICT: 'just health'
said one thing was wrong while a second, independent fault stood behind it. That is the rail-registry's own class (i) - a
rail nothing runs - in the mirror: a rail that runs and is never REACHED.
REMEDY (owed): the ladder collects every fault before it exits, or the aborting rails are declared as KNOWN ABORTS with the
count, so the prefix is visible rather than implied. Filed, not papered over.

## BUG-574 (FIXED, HIGH): the adoption rule REFUSED the repository OWN index at a NORMAL commit, blocking every commit while all 13 synthetic controls stayed green (2026-09-27)

MEASURED at the real write boundary: a NORMAL commit hands the pre-commit hook GIT_INDEX_FILE=<gitdir>/index, while a partial commit (git commit -- path) hands <gitdir>/next-index-<pid>.lock. adopt_index() applied the DECLARED minted-name globs FIRST, so the repository own index - which IS the pinned subject - was refused as if it were a foreign body. EVERY commit in this repository was blocked, and no rail could report it, because every control built a SYNTHETIC git dir and never exercised the value git actually passes.

RULE ORDER FIXED (scripts/lib/git_subject.py#adopt_index): (a) a value whose realpath IS the pinned subject is ACCEPTED as the subject and named; (b) otherwise the three declared adoption conditions apply (directly inside the pinned git dir AND matching a declared owner_name_globs entry AND exists); (c) otherwise REFUSE (C16). The declared globs decide only what is NOT already the subject.

CONTROL ADDED (14th known-answer control): the repository OWN index passed as GIT_INDEX_FILE is ACCEPTED as the pinned subject, NOT refused by the minted-name globs. Measured RED under the mutation that removes the rule, GREEN with it.

CLASS (the mirror of BUG-492): a control that has never been seen to FAIL is not a control. 13/13 green while 100 percent of commits were refused - the write boundary was never part of the test.

## BUG-575 (OPEN, MED): the decision graph is a SET of labels where it must be a GRAPH - a decision can be RETIRED without naming a successor, and no rail reads whether a CITING declaration names a decision that is actually IN FORCE (2026-09-27)

MEASURED (read-only forensic pass over config/decisions.yaml + config/*.yaml, 2026-09-27):
  - 805 records, 805 distinct normalised ids, 0 collisions (the dash spelling is collapsed by normalized_id, C21) - CLEAN.
  - 0 of 138 config citation sites name a RETIRED decision (SUPERSEDED/ARCHIVED/REVOKED/REJECTED) - CLEAN.
  - 0 knobs carry two different decided ids - CLEAN.
  - 16 records are state=SUPERSEDED, but only 4 name their successor (superseded_by). 12 ORPHANS: D2070, D2080, D2085, D2087, D2091, D2223, D2224, D2293, D2317, D2318, D2430, D2582. Only 1 record declares supersedes. So "what replaced X" is answerable from human memory, never from the registry.
  - 4 declaration sites cite a decision that is NOT IN FORCE as their authoring authority: config/evidence_floors.yaml (D-403, state=PROPOSED), config/handoffs.yaml (D-403, PROPOSED), config/instrument_controls.yaml (D-400, PROPOSED), config/recalibration_pins.yaml (#pins/r2_meter, D-2663, state=OPEN).
  - scripts/reconcile.py#decision_registry_wellformed passes ALL of the above: it checks that a cited id RESOLVES, never that it is in force.
  - The DECISION-LOG.md SUPERSEDED list and the registry superseded set agree exactly (16/16, both directions) - that one two-home join is currently CLEAN and must stay so.

CLASS: this is the D-328 defect the registry already ruled on - a citation that asserts a protection which enforces nothing - generalised to the whole registry. A rule whose authority is PROPOSED is enforced by nobody, and a SUPERSEDED rule whose successor is unnamed cannot be retired by any machine.

REMEDY (two small rails, no new vocabulary): (1) supersession COMPLETENESS - state=SUPERSEDED requires a resolvable successor, except the 24 pinned legacy_debt_ids in config/decisions_policy.yaml (D-2645); (2) IN-FORCE - a cited decision must be in the in-force set, or the citing site must declare a forward reference explicitly (the mint gate already refuses a forward citation, so the vocabulary exists). MADR is the real-world precedent: it carries status = "superseded by ADR-0123" as a LINK, not a label.

## BUG-576 (FIXED, MED): a FRESH repository cannot make its FIRST commit - RAIL 0 accuses an UNBORN HEAD of being broken metadata, and the RECOVERY route re-creates exactly that state (2026-09-27)

MEASURED (2026-09-27, by scripts/check_boundary_rehearsal.py in a REAL repository in the system temp dir, --separate-git-dir layout, hooks installed by this repository's OWN installer): the FIRST \`git commit\` returns rc=1 with
  FAIL repo-integrity: 2 repository integrity defect(s):
    "git rev-parse --verify HEAD^{commit}" does not resolve (rc=128: fatal: Needed a single revision) - every rail below is reading a repository that is not there (P0-A)
    <gitdir>/logs/HEAD is MISSING - git's reflog for HEAD has been renamed away, and 'git reflog' will silently serve a stale branch reflog (P0-A)
Both facts are the NORMAL state of an UNBORN HEAD, not broken metadata: HEAD names a branch with no commit yet, and git creates logs/HEAD AT the first commit.

WHY IT MATTERS: the SAME state is produced by the BUG-400/BUG-564 RECOVERY route (a git dir re-created by a clone, by hand, or by --separate-git-dir), so the rail whose purpose is to NAME broken metadata REFUSES the one commit that would repair the repository. This is the BUG-574 class again - a rule that cannot fire on the LEGITIMATE case - now on the recovery rail, and it was invisible for the same reason: every control built its own fixture and asserted refusals, never an acceptance.

CLASS: a rule derived from "what a healthy repository LOOKS like" instead of "the states a healthy repository PASSES THROUGH". An unborn HEAD is a legitimate state.

REMEDY (OWED): RAIL 0 must distinguish an UNBORN HEAD (HEAD resolves to a ref that does not exist yet, and the repository has an index but no commit) from a HEAD that is genuinely broken; only the latter is a defect. Filed here rather than fixed by weakening the rail. UNTIL THEN the rehearsal declares a --no-verify bootstrap in config/boundary_rehearsal.yaml#temp.bootstrap that MUST BE WITHDRAWN by a decision the moment this is fixed (a declaration that outlives its subject is the BUG-542 class).

ESCAPING CORRECTION (appended 2026-09-27, the day the block above was filed): the three backtick PAIRS in the
BUG-576 MEASURED block carry a stray leading backslash from the appending heredoc. Read each of them as a PLAIN
backtick. Nothing else in the block is affected. Corrected by THIS APPEND, not by a rewrite, because buglog.md is
append-only (R-D410).

## BUG-577 (OPEN, MED): the BUG-537 rule "a fixture must resolve OUTSIDE the tree it audits" now has TWO HOMES, restated verbatim by two rails (2026-09-27)

FOUND BY: the forensic audit run BEFORE the D-2675+D-2676 commit - D-2676 requires ONE HOME for every rule, so the landing was audited against its own rule.

MEASURED (2026-09-27): scripts/check_boundary_rehearsal.py#outside_tree and scripts/check_rail_mutations.py#outside_tree are ONE rule in TWO files - both refuse a root that IS the audited tree or lies inside it, both derive REPO from the rail's own location and never from config. Fixing the rule in one rail leaves the other silently stale, which is precisely the fork D-2646 forbids, and it appeared in the same change-set that adopts the standing rule.

REMEDY (OWED): ONE HOME - scripts/lib/fixture.py#outside_tree, imported by both rails - landed WITH the standing rule's teeth: a KNOWN-ANSWER control that calls the shared rule with the audited tree ITSELF and requires the refusal, plus a mutation entry in config/rail_mutations.yaml that REDs that control when the rule is reduced to a no-op. UNTIL THEN both copies are live and this block is the audit record.

ALSO MEASURED IN THE SAME AUDIT (no new id - it is the evidence for BUG-571's remedy): BUG-492 is named 32 times in governance/buglog.md and is cited by the standing rule's own prose, yet it is NOT in the register (314 ids). A decision that cites a bug that does not exist is a citation naming nothing (D-2660), and it is exactly the owner-owed RED LINE BUG-571 owes.

## BUG-578 (FIXED, MED): the BOUNDARY REHEARSAL rehearses HEAD, so it cannot gate the change that LANDS - it was GREEN while the working tree already contained a rail that refused every fresh commit (2026-09-27)

MEASURED (forensic audit of the BUG-576 landing, inside the fixture the rehearsal itself builds): with the fix
present in the WORKING TREE and absent from HEAD, the rehearsal own acceptance control returned
FRESH_FIRST_COMMIT rc=1 - REFUSED by HEAD RAIL 0 - and returned rc=0 the moment the same bytes were OVERLAID
into the fixture. The rehearsal materializes 'git archive HEAD' (config/boundary_rehearsal.yaml#temp.materialize)
and installs the hooks from that replica, so every rail it exercises is the LAST COMMITTED one, never the one
about to be committed.

CLASS: a control that measures the PREVIOUS state cannot refuse the commit that breaks the NEXT one. It is
BUG-574 one level up: the rehearsal would stay GREEN while a rail change that refuses every legitimate commit is
committed, and the very next commit - the one that would have to repair it - is then refused BY THE HOOK, so the
repair can only land with --no-verify. The class this rehearsal exists for recurs THROUGH the rehearsal.

REMEDY (OWED): overlay the WORKING TREE bytes of the DECLARED subjects the rehearsal exercises (scripts/**,
config/**, justfile) into the fixture AFTER materializing HEAD and BEFORE installing the hooks, then re-run the
installer own --check. DECLARED with a why, never inferred (C12), plus a control that REDs if the overlay is
dropped. MEASURED in the audit: 'bash scripts/install_git_hooks.sh --check' returns rc=0 after the overlay, so
the installed hook is still its own re-derivation (BUG-526).

NOTE (D-2646/D-2674): the four new RAIL 0 controls (BUG-576) build their fixtures with 'git init' in the SYSTEM
temp dir and copy NOTHING, so they do not restate the BUG-537 outside-tree rule and must NOT become its third
home (BUG-577) - when scripts/lib/fixture.py lands, the nested builder moves there and the copy is deleted.

## BUG-578 (FIXED, MED): the BOUNDARY REHEARSAL rehearsed HEAD, so it could not gate the change that LANDS (2026-09-27)

MEASURED: the fixture was materialized with `git archive HEAD`, so its rails were the ones that LANDED. With the
BUG-576 fix in the working tree and absent from HEAD its own acceptance control returned FRESH_FIRST_COMMIT rc=1,
and rc=0 the moment the same bytes were overlaid. The rehearsal would have stayed GREEN while a change that refuses
every legitimate commit landed - and the repair could then only have landed with --no-verify.

FIX: config/boundary_rehearsal.yaml#temp.overlay declares the subjects (scripts, config, justfile, the session-plan
glob) and their exclusions; scripts/check_boundary_rehearsal.py#overlay_subjects copies them OVER the materialized
HEAD bytes BEFORE the hooks are installed, and `setup.overlay` is a DECLARED premise the classifier REQUIRES (a
missing observation is never a pass, C16). An inert overlay is now impossible: a declared subject matching no file
fails closed (D-405), and a copy that does nothing REDs the new control.

SEEN: --selftest 21/21 (new: overlay_dropped_is_fatal, `the overlay replaces the fixture bytes with the LANDING
bytes` - a control that pre-seeds stale bytes at a path DERIVED from the declaration, so it fires whether or not the
live tree differs from HEAD). D-2676 teeth: config/rail_mutations.yaml#overlay_of_the_landing_bytes_is_load_bearing
REDs that control (min_mutations 4 -> 5). just health: 436 file(s) overlaid, mutation gate 4/4 rules SEEN to red.

## BUG-579 (FIXED, LOW): a CRASH in the rehearsal was a traceback, not a verdict (2026-09-27)

CLASS: the mutation gate already declares `a RED for an undeclared reason is a crash, not a control`; the rehearsal
had no such boundary. A fixture precondition defect (a declared scenario path absent from the base commit, or a
failed bootstrap commit) raised out of rehearse() -> main() as an exception: no verdict, no reason, and the rail
died with a stack trace instead of reporting. FOUND BY the BUG-578 forensic audit.

FIX: main() wraps rehearse() and returns EXIT_FATAL naming the exception (a crash is a verdict, never a traceback).
A declared overlay subject that matches no file still fails closed with its own message (D-405).

## BUG-580 (FIXED, MED): the STANDING RULE's coverage was a HAND-MAINTAINED SECOND HOME of the commit boundary (2026-09-27)

CLASS: `config/rail_mutations.yaml#coverage.required_subjects` restated, by hand, WHICH rails gate a commit - a fact
that already has ONE home (`config/rail_registry.yaml#commit_boundary.must_contain`, verified against the bytes of
`gitdir:hooks/pre-commit` by `scripts/check_rail_registry.py`). Two lists of one fact drift, and only one of them can
be right: a rail ADDED to the commit boundary would have been covered by the standing rule only if a human remembered
to edit the second list, and a rail covered there but not at the boundary was indistinguishable from either.
MEASURED 2026-09-27: RAIL 3 (`scripts/verify_recalibration_pins.py`) and RAIL 5
(`scripts/check_declaration_consumers.py`) ran at the commit boundary in EVERY commit while the coverage list did not
name them and no mutation proved their rules were READ - and the gate printed `ok rail mutations: ... 3/3 declared
subject(s) covered`, i.e. a coverage claim measured against the list it happened to hold. This is D-2676's own class
(a rule that cannot be made to fail is not a rule) turned on the standing rule's own coverage.

FOUND BY: the D-2679 forensic audit, run before landing the next step (the audit asked "is anything restated by hand,
and is any list read against another list?").

FIX: (1) `coverage.boundary_join` declares the ONE home (`registry`, dotted `key`, and the script `prefix`/`suffix`
vocabulary, C12 - no path or pattern in code); (2) `scripts/check_rail_mutations.py#boundary_rails` READS it, returns
a VERDICT on failure (never an exception: a crash is not a control, the BUG-579 rule one level up), and REFUSES a
commit-boundary rail the coverage does not name; (3) the two owed rails got the mutations that prove their rules are
read (`laundering_repin_rule_is_load_bearing` for BUG-535, `withdrawn_consumer_rule_is_load_bearing` for BUG-562) and
were added to the coverage; (4) the gate's OWN rule got one too (`boundary_registry_join_is_load_bearing`), so the
standing rule covers itself; (5) the SUPERSET direction is DECLARED in the config (a rail whose own rule gates the
boundary - the rehearsal, D-2675 - is covered BEYOND the boundary), not left as a silent asymmetry; (6) `min_mutations`
raised 5 -> 8 and `config/declaration_consumers.yaml` now declares this gate as a CONSUMER of
`config/rail_registry.yaml`, because it now reads it.

SEEN: `check_rail_mutations --selftest` 18/18 rc=0 (new: `boundary_rail_missing_from_coverage`, `coverage_join_to_nothing`,
and the join "the COMMIT BOUNDARY is READ from its ONE home and every rail there is inside the declared coverage");
`--check` rc=0 in 8.4s: `ok rail mutations: 7 declared rule(s) SEEN to red through their own control, 1 negative
control(s) stayed green, 6/6 declared subject(s) covered (4 derived from the commit boundary, D-2679)`;
`check_declaration_consumers --selftest` 11/11 and tree mode `ok declaration consumers: 5 declared home(s), 6
consumer edge(s) all resolve for the tree`; `check_boundary_rehearsal --selftest` 21/21 (its own join reads this
coverage list and still finds every rail inside the declared overlay).

## BUG-581 (FIXED, LOW): a declaration's RATIONALE was attached to the WRONG edge (2026-09-27)

CLASS: in `config/declaration_consumers.yaml` the edge for `config/handoffs.yaml` carried the RAIL REGISTRY's `why`
("the rail registry is read by scripts/check_rail_registry.py::CFG ..."), while the `config/rail_registry.yaml` edge
carried none. A rationale attached to a subject that does not contain it teaches the reader the wrong fact in a file
that spells the right one two edges up - the same family as BUG-550 (a payload that names something other than its
own subject) and the reason the mint gate refuses a record that names none of its own bugs.

FOUND BY: the D-2679 forensic audit (the mismatch sweep over the files it was about to touch).

FIX: the rail-registry rationale moved to `config/rail_registry.yaml`, amended to name BOTH consumers (the registry
reader and, since D-2679, the coverage join) and both decisions; `config/handoffs.yaml` got its own accurate `why`
(what a withheld handoff reader costs, BUG-559).

## BUG-573 (FIXED, MED): a RED earlier in the ladder SHORT-CIRCUITED it, so every LATER fault was invisible (2026-09-27, D-2680)

CLASS. The ladder is a LINEAR recipe: it stops at the FIRST non-zero line, and the owner READS the result as the
whole set. A red line therefore hid every line after it, so every repair round could only ever discover ONE fault -
the cost the owner measured as "running in circles".
MEASURED (before). A single RED at one line stood for a whole session; repairing it UNHID a stale dormancy the
rail registry had never been able to report. Nothing about the fix caused the second fault - the prefix did.
MEASURED (after). `just health-full` runs the same declared lines in one pass: **ok ladder scan: 87 line(s) RUN,
0 fault(s), 203.0s** (SCAN_RC=0). The remaining fault set at HEAD is EMPTY, and it is now measurable instead of
assumed. Per-line seconds make the cost attributable: check_tests 82.1s, yaml_guard 45.3s, boundary rehearsal
14.4s, store-columns 10.2s, rail mutations 8.6s. The banner's numbers are DERIVED: '87 declaring line(s) stand
in it (63 declared a HARD gate)'.
FOUND BY the D-2680 step of the standing-rule programme (the registered next step was BUG-577; BUG-573 was taken
FIRST because it is upstream of every other repair: it decides what a human can SEE).
FIX (D-2680, scripts/run_ladder.py + justfile + config). --collect runs each line as written through a POSIX
shell from the repository root, so the line's OWN guard decides (a line that tolerates rc=2 is not a fault),
records every fault with rc + seconds, and exits with the WORST code (1 FATAL outranks 2 owner-owed, BUG-457),
never the first. The recipe body is READ from its ONE home (config/rail_registry.yaml#ladder + #recipes): no rail
name, path or count is written in code (C12), a recipe the declaration does not govern is REFUSED (C16, D-405),
and a line invoking the collector itself is skipped (recursion). `just health` keeps the fast ladder and now
declares the prefix FIRST - printed before any rail can abort - naming `just health-full` as the whole-set entry
point. No fixture and no writer: the controls are synthetic, so this rail adds no second home of the fixture rule
(BUG-577) and no entry to config/rail_registry.yaml#writers.
SEEN. run_ladder --selftest 12/12 rc=0; mutation ladder_scan_reports_every_fault_is_load_bearing SEEN to red
through its own named marker; gate --check rc=0 (8 rules, 7/7 subjects); registry rc=0; declaration consumers
rc=0 (7 edges). This change FILED no new bug - it closes one.

## BUG-577 (FIXED, MED): the BUG-537 rule "a fixture must resolve OUTSIDE the tree it audits" had TWO HOMES and a THIRD inline copy (2026-09-27, D-2681)

FIX (D-2681, ONE HOME). scripts/lib/fixture.py is now the single home of BOTH fixture rules: outside_tree(root,
where=...) (the BUG-537 refusal) and real_repo(parent, name, commit=, identity=, message=) (the BUG-576 builder).
scripts/check_boundary_rehearsal.py and scripts/check_rail_mutations.py DELETE their copies and IMPORT it;
the nested builder in scripts/check_repo_integrity.py#selftest is DELETED and calls the shared one, passing ITS
OWN identity and message, so the shared builder declares no caller's vocabulary (C12d). The module declares
NOTHING from config: the audited tree is DERIVED from its own location, so no config edit can re-point the rule.

SEEN. scripts/lib/fixture.py --selftest: 6/6 known-answer control(s) fire, run by the ladder as its OWN declaring
line (D-2676 ii). The refusal FIRES on the audited tree AND on a descendant, does NOT fire on a system-temp root
(two-sided: a rule that refuses everything is not a rule), and the builder drives BOTH HEAD states.

TEETH (D-2676 iv). config/rail_mutations.yaml#fixture_outside_tree_rule_is_load_bearing reduces the refusal to a
no-op and requires 'FAIL selftest/outside_tree_refuses_the_audited_tree'; floor 9 -> 10, subjects 7 -> 8. Gate
MEASURED: 9 declared rule(s) SEEN to red, 8/8 subjects covered, 1 negative control stayed green.

FOUND BY THE CONTROL ITSELF (BUG-579's rule, one level down). The FIRST run of the new selftest DIED with
NotADirectoryError instead of reading a refusal, because a cwd that is not a directory cannot even be LAUNCHED:
git() is now TOTAL (EXIT_CANNOT_RUN = 125). A crash in a fixture helper was a traceback, not a verdict.

## BUG-582 (FIXED, HIGH): the D-2680 landing declared a BANNER and a SELFTEST in the justfile, and NEITHER was in the bytes - the claim lived in four governance homes and in no file (2026-09-27, D-2681)

CLASS. A declaration is only a declaration where a machine READS it. MEASURED at HEAD e13eddc: 'justfile | 7
+++++++' added ONLY the health-full recipe; 'git show HEAD:justfile | grep run_ladder' returned ONE line, the
--collect call. The --banner line inside 'health' (the SEEN control that must print BEFORE any rail can abort) and
'run_ladder.py --selftest' were ABSENT - while MASTER-TASK-REGISTER.md, DECISION-LOG.md, CONTEXT_INDEX.md and the
session handoff all stated the banner prints and the oracle runs. THE TELL: the D-2680 ladder table listed 87 lines
and NEVER printed the selftest line - the evidence was already on disk and was read as a summary.

WHY IT MATTERS. BUG-573's harm is a human READING a prefix as a verdict; the mechanism that ends it was not wired
in. The bug was CLOSED while its own remedy was half-landed - the standing rule's clause (ii) (a SEEN boundary
control) was satisfied in prose.

FIX. The banner line is FIRST in 'health' (before RAIL 0, so nothing can abort ahead of it) and the collector's
--selftest line runs in the ladder. Root cause of the partial write is the PATCH DRIVER, not the rail: a
multi-substitution script wrote ONE substitution's text and reported success for three - the LESSON already in
this repository: verify a landing by READING THE BYTES, never the driver's own summary (C12d extended: a patch
driver's stdout is a CLAIM, and a claim is not a measurement).

## BUG-575 (FIXED, MED): the decision GRAPH - a decision could be RETIRED without naming a successor, and a rail read that a citation RESOLVES, never that it is IN FORCE (2026-09-27, D-2682)

MEASURED 2026-09-27 (read-only forensic pass, re-measured at the landing against 812 records / 59 config citation sites): 16 records state=SUPERSEDED and only 4 name their successor (12 ORPHANS, all pinned below); 4 citation sites name a decision that is NOT IN FORCE (D-403 x2 PROPOSED, D-400 PROPOSED, D-2663 OPEN) - a protection enforced by nobody (the D-328 defect, generalised); scripts/reconcile.py#decision_registry_wellformed passed all of it, because it checks that a cited id RESOLVES.
FIX. The registry is read as a GRAPH. ONE HOME for the rules: config/decisions_policy.yaml#graph (in_force_states, not_in_force_states, supersession_state, successor_field, and the two debt pins). TWO declared entries in config/reconciliation.yaml, evaluated by the SAME engine and the SAME citation walker (no second home for "what a citation site is", BUG-577): decision_supersession_complete and decision_citations_in_force - both GREEN at the landing: 'every SUPERSEDED record names a resolvable successor in 812 record(s); 12 pinned legacy id(s) still owed' and '59 citation site(s) all name a decision IN FORCE; 4 declared forward reference(s) still owed; every state word in the registry is classified'.
NOT BACKFILLED (the legacy_debt_ids reasoning): a successor reconstructed by a tool is not evidence, so the 12 orphans and the 4 sites are DECLARED debt, pinned BY IDENTITY in the ONE home and SHRINK-ONLY - a pin that now names a successor, changed state, vanished, or a pinned site that no longer exists or now names an in-force decision, is a STALE declaration and fails the rail (BUG-542).
THE RULE THAT ALSO CLOSES THE VOCABULARY: every state word present in the registry must be classified in force or not-in-force, so a NEW state cannot enter unread (BUG-572's class).
SEEN. python3 scripts/reconcile.py --selftest: 9 known-answer control(s), both directions, run by the ladder as its OWN declaring line (D-2676 ii).
TEETH (D-2676 iv). config/rail_mutations.yaml#decision_supersession_rule_is_load_bearing: with the SUPERSESSION filter inert, the named control goes RED through its own marker 'FAIL selftest/supersession_reports_a_gap'; floor 10 -> 11, subjects 8 -> 9.
MEASURED OBSERVATION (not this bug, filed as BUG-583): 5 of 812 records spell the state 'active' in lowercase while 505 spell it 'ACTIVE'. The new rail normalises case (C21) so it is NOT a fault; the census/registry-spelling question is filed separately rather than folded in here.

## BUG-583 (OPEN, LOW): 5 of 812 decision records spell the state 'active' in lowercase while 505 spell it 'ACTIVE' (2026-09-27, found by the D-2682 landing)
MEASURED while measuring the state census for config/decisions_policy.yaml#graph (D-2682): the registry carries ACTIVE 505 and `active` 5; scripts/recompute_decision_summary.py#canonical_state upper-cases the state, so the CENSUS is right, but the registry BYTES carry two spellings of one state - and the rail that now classifies the vocabulary normalises case (C21), so today this is invisible to every machine.
CLASS. The BUG-572 family one level down: a spelling that decides nothing is still a second form of a governed value, and a future consumer that compares state strings EXACTLY would read 5 records as unclassified.
NOT FIXED HERE. Folding a 5-record rewrite of an append-only registry into a rail landing is exactly the scope creep the meta-lane freeze forbids; the finding is filed and the D-2682 rail normalises rather than silently tolerating. REMEDY (owed): either canonicalise the 5 records through the registry's own writer (a structural edit, receipt refreshed in the same sequence - D-2655) or declare the spelling rule where a reader can FAIL on it.
REMEDY (OWED), not a silent pass.

## BUG-571 (FIXED, LOW): the register is fed by HEADINGS only, so an id written INLINE is real to every human and absent from every machine home (BUG-493 measured)

MEASURED (2026-09-27, at HEAD): governance/buglog.md names 383 distinct ids and the register carries 321, so 62 ids
have NO machine home at all. Their provenance is not archaeology: legacy record shapes (`| BUG-099 | date | title |`
rows, `- **BUG-098** - ...` bullets - BUG-085, BUG-104, and 58 more) plus BUG-492, named 33 times by the standing
rule's own prose as its evidence. Every one of them is a name a human can cite and no rail can answer for.
FIX (D-2683, scripts/check_register_divergence.py + config/register_divergence.yaml). The rail that already owns
"the LOG and the REGISTER diverge" gained the SECOND shape of that fact, in the SAME home: shape i (BUG-481) is a
bug closed in prose and counted OPEN; shape ii (this bug) is an id named in the log and carried by no header. Both
are declared, both are pinned BY IDENTITY and SHRINK-ONLY, both FAIL on a new instance and on a stale pin, and both
are evaluated by ONE pure `faults()` so the same code answers the live log and the rehearsal.
DEVIATION FROM THE RECORDED REMEDY (stated, not hidden). The remedy filed here was "add the cited-by-decision join
to scripts/bug_status.py". REFUSED on two grounds. (1) TWO HOMES: the register's own generator cannot see the log's
other shape - check_bug_status.py re-derives from the same HEADER projection and byte-compares, so it certifies the
PARSER, never the LOG (the BUG-467 class, and the reason this rail exists at all). (2) The decision-citation
direction is ALREADY closed forward: MEASURED 2026-09-27, the 39 ids cited by decision records in
config/decisions.yaml resolve, 0 unregistered, because the mint gate REFUSES a citation naming an unregistered bug
(D-2660). Adding a second reader for it would have created the two-homes defect (D-2646) one turn after fixing it.
NOT BACKFILLED (D-2645, the revoked-reference judgement): promoting 62 prose names to header events would stamp
them with a status no author ever wrote, and "no closure claim is not a closure" would count every legacy record
OPEN - a tool would be manufacturing 62 bugs. The list can only be SHORTENED, by a human, in a diff.
SEEN. python3 scripts/check_register_divergence.py --selftest: 10 known-answer control(s) fire, both directions
(the walker reports an uncarried name; a carried name stays silent; a pin the register now carries is STALE; an
undeclared name is a fault; both ceilings are read; the negative control) rc=0. --check: "ok register divergence: 0
declared divergence(s), all still divergent; 62 named-but-uncarried id(s) declared, all still uncarried; ceilings
0/62 (shrink-only); 321 id(s) carried" rc=0.
TEETH (D-2676 iv). config/rail_mutations.yaml#register_uncarried_rule_is_load_bearing (runner
scripts/check_register_divergence.py --selftest, marker 'FAIL selftest/uncarried_id_is_reported') SEEN to red; the
gate reports 11 declared rule(s) SEEN to red, 1 negative control green, 10/10 declared subject(s) covered; floor
11 -> 12, subjects 9 -> 10, both in the same diff.

## BUG-584 (OPEN, LOW): the BUG-582 fix wrote three of its lines TWICE in `just health` (the ladder runs them twice and over-reports its own size)

MEASURED (2026-09-27). Commit 29a0a37 landed 4 added lines in justfile where 2 were intended: justfile:7 and
justfile:8 are BYTE-IDENTICAL banner invocations, and `scripts/lib/fixture.py --selftest` and
`scripts/run_ladder.py --selftest` each stand TWICE. MEASURED consequence, pre-change `just health-full`: "ok
ladder scan: 90 line(s) RUN, 0 fault(s), 220.3s" for a recipe whose DISTINCT declaring lines number 86 - the
collector's own census and the banner's "N declaring line(s) stand in it" are inflated by 4, and every duplicated
line is executed twice.
WHY NO RAIL SAW IT. scripts/check_rail_registry.py keys its census by INVOCATION + FLAGS (a dict), so a duplicated
line collapses into one key BY CONSTRUCTION and cannot be counted twice; scripts/run_ladder.py counts RAW lines.
That is two numbers for one fact (D-2646, the two-homes defect) living inside the health instrument itself - and
the duplicated lines were introduced by the commit that FIXED "declared in four homes, written in none" (BUG-582).
REMEDY (owed, deliberately NOT worked here - the meta-lane freeze says a new governance bug is FILED, not chased,
until BUG-571 closes and a product artifact is built): the ladder's own reader REFUSES a duplicated declaring line
(one line, one home, exactly once - BUG-582 is the zero case, this is the twice case), with the pinned duplicates
as known-answer controls, both directions, and a mutation that REDs it.

## BUG-563 (FIXED, MED): `backups/**` and the rail-output stores were neither GRANTED by the plan nor IGNORED by git (D-2684)
- **MEASURED before the fix (2026-09-27, `git status --porcelain -z -uall`)**: **124 dirty paths, and exactly ONE
  of them was granted** (`governance/RECONCILIATION.json`, entry 15). The other **123** sat in NO declared home:
  112 `backups/**` PRE_* pre-images that C13/R-D410 OBLIGE a session to write, plus 11 in `governance/` (3
  tracked-but-modified rail outputs, 8 untracked run artifacts/journals). No plan could commit them and git did
  not ignore them, so **the tree could never be clean** and the evidence trail was unversioned BY ACCIDENT.
- **shape**: the archive-census rule (`archive/index.yaml#excluded`, BUG-537/BUG-556) applied to the WORKTREE:
  "an on-disk object is either INDEXED or DECLARED excluded, never silently absent". It fell between the two
  existing rails: rail 4 audits the STAGED set, rail 0 audits git METADATA - the dirty worktree was nobody's
  subject.
- **FIX (D-2684)**: TWO HOMES, NO OVERLAP, ONE READER. (1) the GRANTING home is the plan's `may_touch` (rail 4
  already owns "a session may write/commit this"; the new rail CONSUMES it and never restates it) - SEVEN NAMED
  paths added (`.gitignore` + the six indexed rail-output stores, `governance/MUTATION_JOURNAL.jsonl` among them
  because an append-only receipt ledger nobody can commit is not auditable); (2) the EXCLUDING home is
  `config/repo_integrity.yaml#worktree.excluded` (three declarations, each with a `why`, enforced by the
  `.gitignore` bytes); (3) the ONE reader is `scripts/check_repo_integrity.py --worktree`, wired into the ladder.
- **THE RAIL CAUGHT ITS OWN PATCH (MEASURED, first run)**: the `.gitignore` lines I first wrote carried TRAILING
  comments - and in `.gitignore` a trailing `#` is NOT a comment, so each line became a literal pattern that
  matched nothing. The rail reported `declared-excluded 'backups/**' is NOT ignored by git (probe 'backups/x')`
  and exited 1. That is the D-405 join firing on its author: the declaration is checked against GIT'S OWN answer
  (`git check-ignore -q --no-index`), not against a belief about it. A SECOND measured defect fell out of the
  same run: the shared `git()` helper STRIPS output, which ate the leading space of the status field
  (" M .gitignore" -> path "gitignore"), so `dirty_entries()` now reads the records RAW (C16).
- **TEETH (D-2676)**: (i) ONE HOME = `config/repo_integrity.yaml#worktree`; (ii) SEEN control = the ladder line
  `check_repo_integrity.py --worktree || exit 1`; (iii) NAMED oracle = `--selftest` (6 worktree controls + the 15
  existing, rc=0); (iv) MUTATION = `config/rail_mutations.yaml#worktree_undeclared_dirty_path_rule_is_load_bearing`
  (floor 12 -> 13). VERDICT after: `ok repo-integrity worktree: 14 dirty path(s) - 14 granted by
  governance/session_plan_20260924.yaml, 0 declared-excluded, 0 in neither home` rc=0.
- **NOT claimed**: the rail is wired at the SCAN moment (`just health`), deliberately NOT into the pre-commit
  hook - the hook's strictest gate would refuse a commit that carries a legitimately new artifact before the plan
  entry can land, which is the BUG-528b sequencing defect. The hook widening is a declared follow-up, not a
  silent gap.
