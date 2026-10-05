# Forensic Audit — BUG-639 S4 delta-merge shrink-guard fix (D-2825 recovery)

- Date: 2026-10-05
- Scope: one-line fix to `pipeline/stage4_merge.py` (sidecar `safe_write(..., force_shrink=bool(cluster_ids))`) + buglog entry.
- Trigger: owner asked whether cluster_28517 could be re-extracted on S2; the recovery attempt exposed the shrink-guard false-positive.

## Verdict: SAFE to commit (R5 gemma-4-E4B-it-MLX-4bit APPROVE — 4/4 checks PASS)

## Owner question answered (D-2825)
Re-running on **S2 would NOT help**. S2 extraction for cluster_28517 was already
complete and coherent (full name/definition/mechanism/boundary/consequence/elaboration
+ 2 verbatim evidence passages). The failing `application` field is produced at **S4**
by the merged classification call (`merged_cribs_classify`, gpt-oss-20b), which
returned an empty application on the original run — a **transient** failure. A targeted
`--cluster 28517` re-run recovered it cleanly (application 178 chars, discipline
`theoretical physics`, depth `domain`, evidence `cited`, CLEAN).

## 11-category check
1. **break** — none. Full-run path (`cluster_ids is None`) → `force_shrink=False`, behavior unchanged.
2. **cascade** — none. The stale sidecar (declared 1 vs 6591 on-disk) was the cascade risk; reconciled to 0.
3. **drift** — none. Does not touch `_s2_input_fingerprint` or the full-run BUG-183 guard (still fingerprint-compares, full-run only).
4. **blindspot** — none. Delta path bypasses guard (by-design); full path retains it; no third path exists.
5. **gap** — none. Empty-list `cluster_ids` cannot occur: `main()` only sets it when `args.cluster` is truthy.
6. **conflict** — none. Completes D-2824/D-2825 delta-merge; preserves BUG-487 guard on full-run path.
7. **bug** — none introduced. `bool(cluster_ids)` (False for None/[], True for non-empty list) exactly matches the `if cluster_ids:` delta branch.
8. **hidden failure** — none. `safe_write` still does atomic tempfile→fsync→os.replace + truncation detection regardless of `force_shrink`.
9. **error leak** — none. C16 fail-loud behavior of `safe_write` unchanged.
10. **mismatch** — none. Comment matches code; buglog summary + detailed entry consistent.
11. **bloat** — none. +1 code line +10 comment lines, no dead code.

## Data recovery (gitignored, not committed)
- cluster_28517 recovered via `--cluster 28517`.
- Sidecar reconciled: `declared_failed_count` 1→0, `failed_cluster_ids` [].
- Manifest refreshed: `record_count` 6588→6591, sha256 updated.
- Preflight GREEN: boundary + sha256 + record_count 6591 + authoritative 6591.
- Invariant: on_disk 6591 + declared 0 == expected 6591. ✅
- **D-2825 disposition: RECOVERED** (not accept-as-failed). All 6,591 S4 FBs on-disk, declared 0.

## R5 cross-family review
gemma-4-E4B-it-MLX-4bit (verifier) APPROVE — `force_shrink=bool(cluster_ids)` correctly
maps delta-vs-full run and keeps the guard on the full path.
