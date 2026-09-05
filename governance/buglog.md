# Maxwell OS v3.0 — BUG LOG (tiered)

> **Updated:** 2026-09-04 | **Archive (full history):** `archive/governance_pre_tiered_2026-09-03/buglog.md`
>
> **Convention (standing rule):** OPEN bugs at the TOP (most critical first, MUST→SHOULD→WORTH); CLOSED/RESOLVED at the BOTTOM. Protocol: `governance/buglog_protocol.md`.

---

## 🔴 OPEN — MUST (data integrity / correctness / safety)

_None open_ — BUG-098 (the last MUST) resolved 2026-09-04 (`psutil` declared).

## 🟠 OPEN — SHOULD

| Bug | Date | Issue |
|---|---|---|
| BUG-222 | 2026-09-04 | goose runtime drift: `active_provider=custom_deepseek` (deepseek-v4-pro) + `GOOSE_THINKING_EFFORT=high`. CORRECTION (2026-09-04, D2560 re-verify): DeepSeek is NOT dead — it is LIVE+AUTHENTICATED via macOS Keychain internet-password (`srvr=https://api.deepseek.com/v1`, `acct=Bearer`); prior "HTTP 401 / no credentials" was an ERROR (probed without key + wrong keychain service names). Real issue = remote CLOUD → C1 ($0, all generation local) + C3 (sovereignty) violation BY DESIGN. Fix = set `active_provider=maxwell_omlx` (user decision, affects goose runtime). D2560. |
| BUG-151 | 2026-08-20 | taxonomy structural overlap (`education` dual-listed + 267 raw aliases) |
| BUG-148 | 2026-08-20 | S2 `route` field stale/uniform (`route="FB"` on all 2,878) |
| BUG-182 | 2026-08-27 | 48 singleton empty-shells deterministically re-return empty after S2 rerun |
| BUG-170 | 2026-08-24 | non-principle types (PT/PI/TI/GE) routed but NOT classified/enriched |
| BUG-159 | 2026-08-21 | prompt-injection contamination (cluster_11649, 0.007%) |
| BUG-168 | 2026-08-24 | `pipeline/dspy_trainer.py` exists but NOT wired to any stage (built-not-wired, same pattern as BUG-085) — wire OR archive |
| BUG-160 | 2026-08-21 | evidence-passage topical relevance not verified (1/30 drift sample cites carbon passage for maternal-health FB) |

## 🟡 OPEN — WORTH

| Bug | Date | Issue |
|---|---|---|
| BUG-223 | 2026-09-05 | `'[]'` literal-array hygiene: 54 `emerging` FBs store `discipline_raw = '[]'` (JSON-empty-array string) instead of `''`/NULL. Queries testing `discipline_raw != ''` will wrongly count these as "has raw". Correct empty-test = `(discipline_raw IS NULL OR TRIM(discipline_raw)='' OR discipline_raw='[]')`. Minor (all 54 are legitimately `emerging`); normalize `'[]'`→`''` or add a shared empty-check helper in `pipeline/schemas.py`. D2569. |
| BUG-169 | 2026-08-24 | TI `parameters` empty on 31/143 single-source + 100/307 singleton TI — ontology nuance (technique-type vs API TI); verify at rerun |
| BUG-099 | 2026-08-13 | Model registry drift: gpt-oss/Phi misnamed "verifier" (rename deferred) |

---

## ✅ CLOSED / RESOLVED — bottom (recent)

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
