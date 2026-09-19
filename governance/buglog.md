# Maxwell OS v3.0 — BUG LOG (tiered)

> **Updated:** 2026-09-13 | **Archive (full history):** `archive/governance_pre_tiered_2026-09-03/buglog.md`
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

**Severity:** HIGH. **Status:** OPEN.

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

**Severity:** CRITICAL (silent retrieval-correctness defect; independent of label quality). **Status:** OPEN.

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

**Severity:** CRITICAL (data-destroying; blocks repair R1). **Status:** OPEN.

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
