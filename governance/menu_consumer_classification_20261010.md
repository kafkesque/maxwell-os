# Menu-Consumer Classification — 3-Way Serving / Frozen / Builder (2026-10-10)

> **Purpose.** Every script that names `closed_menu_v<N>.json` (or its `.sha256`) must have a
> KNOWN role, so the next menu revision (v9 → v10) cannot silently leave a stale reader behind.
> This manifest corrects an earlier working note that called ~22 such scripts "dead" — that was
> a **blindspot**. All 23 are either live or the documented provenance of a specific frozen/build
> artifact. **Zero are truly dead**; blind-archiving any of them would have broken live config
> rails (config/artifact_ownership.yaml, config/f11_llm_coder.yaml, config/silent_repair.yaml)
> and the test suite.

## The three roles

| Role | Definition | Keep or archive |
|---|---|---|
| **serving-path** | reads the LIVE menu (`live_menu_path()` / `render_closed_menu()`) to classify or verify the live corpus | keep, repoint to `live_menu_path()` |
| **frozen-validator** | deliberately reads `closed_menu_v5.json` because the artifact it validates was classified in the v5 era | keep, pin-document (never "fix") |
| **builder** | mints / repoints a specific `closed_menu_v<N>` revision | keep (provenance of the live taxonomy) |

## Bucket A — serving-path (live execution)

| script | menu reference | status |
|---|---|---|
| `scripts/menu_axis_hashes.py` | `closed_menu_v5.sha256`/`.json` | **live rail** (justfile). v5 refs are EXPLICITLY HISTORICAL composite pin (D-371, never re-rendered) — correct by design. |
| `scripts/render_closed_menu.py` | `closed_menu_v5.json` default | **live freezer**. v5 default is fail-closed (REFUSES + directs to `--mint-version N`) — correct. |
| `scripts/definition_nli_verify.py` | `closed_menu_v5.json`/`.sha256` in `_provenance()` | **FIXED this session** — see BUG-694 residual below. |

## Bucket B — frozen-artifact validators (pinned by design, do NOT repoint)

| script | validates | why v5 is correct |
|---|---|---|
| `scripts/verify_menu_policy.py` | `config/menu_v6_merge_map.yaml` | v5→v6 merge map is a FROZEN artifact (pinned 2026-10-09, BUG-694) |
| `scripts/verify_anchor_family_registry.py` | `config/anchor_family.yaml` | anchor family was classified against v5 (pinned 2026-10-09, BUG-694) |
| `scripts/parse_frontier_pack.py` | frontier domain/depth pack | the frontier pack (`BLIND_INPUT_150.csv`) is a v5-era instrument |
| `scripts/f11_anchor_review.py` | F-11 anchor review sheet | declared `writer_of_record` (artifact_ownership.yaml:126); v5-era ruler |
| `scripts/discipline_knn_ab.py` | 204 gold-anchor A/B | gold anchors finalized against v5 |
| `scripts/normalize_anchor_discipline.py` | ANCHOR-208 discipline axis | v5 label space |
| `scripts/build_discipline_ceiling_sample.py` | BUG-622 ceiling sample | v5 anchor |
| `scripts/build_discipline_review_queue.py` | ANCHOR-208 discipline review | v5 label space |
| `scripts/menu_repair_worksheet.py` | BUG-348 repair re-issue | v5-era sheet |
| `scripts/f11_decision_sheet_v2.py` | F-11 decision sheet | v5-era sheet (BUG-368) |

## Bucket C — builders (mint / repoint a specific revision)

| script | builds | status |
|---|---|---|
| `scripts/build_taxonomy_v7.py` | `closed_menu_v7.json` | superseded lineage (v8 → v9 landed) |
| `scripts/build_taxonomy_v8.py` | `closed_menu_v8.json` | lineage (D-2865) |
| `scripts/build_taxonomy_v9.py` | `closed_menu_v9.json` | lineage (D-2897, live) |
| `scripts/apply_taxonomy_v8.py` | repoint v7→v8 | one-shot apply (run) |
| `scripts/apply_taxonomy_v9.py` | repoint v8→v9 | one-shot apply (run) |
| `scripts/rederive_anchor_axes_v6.py` (+ 2 helpers) | D-2820 anchor re-derivation | live config (pipeline_config.yaml:438) + tests |
| `scripts/remap_referee_v7_28rows.py` | v7 A/B referee | one-shot (D-2853) |
| `scripts/d2767_ab_eval.py` | D-2767 A/B harness | live test (`tests/test_d2767_coarse_kappa.py`) |

## BUG-694 residual — fixed this session

`scripts/definition_nli_verify.py::_provenance()` scored against the LIVE menu
(`render_closed_menu()`, v9 content) but stamped `menu_version: closed_menu_v5` and read
`closed_menu_v5.sha256` as `closed_menu_sha256_pin`. `menu_hash_rendered` and
`answer_space_sha256` were already live — only those two fields lagged the v5→v9 revision
(an error leak: a report that claims a v5 menu it did not score against).

**Fix (2026-10-10):** repointed both fields to `live_menu_path()` (`config/version.yaml#closed_menu`).
Selftest 4/4 controls fire; compile clean.

## Verdict on archiving

**Do not blind-archive.** The 23 scripts split 3 serving-path / 10 frozen-validator /
10 builder. The only candidates that are one-shot *and* unreferenced-by-live-rail are
`menu_repair_worksheet.py` and `f11_decision_sheet_v2.py` (both referenced only from
`governance/buglog.md` as the provenance of BUG-348/BUG-368 fixes) — and even those are
auditable provenance, so archiving them is cosmetic, not corrective. Any future archival
must (a) run `scripts/build_archive_index.py` to regenerate `archive/index.yaml`, and (b)
pass the full forensic ladder first.
