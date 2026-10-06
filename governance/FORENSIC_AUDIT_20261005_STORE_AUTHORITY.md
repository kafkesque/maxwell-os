# FORENSIC AUDIT — STORE-AUTHORITY RECONCILIATION (2026-10-05)

Scope: `config/store_authority.yaml` declaration sync to match the post-bloat (2026-09-29) disk state.
Trigger: `scripts/check_store_authority.py --check` was FAILING with 2 faults — a live governance drift.

## Findings (break / cascade / drift / blindspot / gap / conflict / bug / hidden-failure / error-leak / mismatch / bloat)

- **F-01 BREAK — NONE.** Declaration-only edit; no data, no model, no store writes. YAML re-validated, rail re-ran 0 faults.
- **F-02 CASCADE — NONE introduced; one reconciled.** The 2026-09-29 bloat cleanup moved files but left the register stale; this reconciles that cascade. The register's only consumer is `check_store_authority.py`.
- **F-03 DRIFT (found + fixed) — two live faults, both from the bloat cleanup:**
  - (a) `knowledge pipeline/diagnostic_diagnostic_20260811_232853.db` declared `derived` but ABSENT (moved to `backup/deletions/…` tombstone) → **STALE**. FIX: removed the declaration; the tombstone is already covered by `preimage_regions`.
  - (b) `archive/bloat_20260929/knowledge pipeline/parquet` (22 old snapshots) **UNDECLARED**. FIX: added an `archive` declaration.
- **F-04 BLINDSPOT — NONE introduced.** The rail's depth bound (`max_depth: 4`) now sees the archived collection; it was previously invisible only because the collection did not exist before the bloat move.
- **F-05 GAP — CLOSED.** The register now declares every store the rail can see (7 stores + 1 tombstone + 22 archived snapshots).
- **F-06 CONFLICT — NONE.** Exactly one `authoritative` store (`knowledge pipeline/maxwell.db`); status vocabulary respected.
- **F-07 BUG — NONE.** No code changed; rail exit semantics unchanged.
- **F-08 HIDDEN-FAILURE — NONE.** Fail-closed preserved: a fresh `--check` exits 0 with 0 faults.
- **F-09 ERROR-LEAK — NONE.** No silent default; every edit is an explicit declaration.
- **F-10 MISMATCH (found + fixed)** — the F-09 carried over from the D-2843 audit:
  - authoritative `why` declared **7,995 fbs**; store now holds **14,574** (rechunk-v4-20260929). FIX: 7,995 → 14,574 (75 columns confirmed unchanged).
  - `knowledge pipeline/parquet` declared "25 parquet snapshots"; now **4 snapshots + 1 diagnostic subdir**. FIX applied.
- **F-11 BLOAT — NONE added.** 2 declaration lines removed (diagnostic db); net register size stable (7 stores).

## Verdict

**NO BREAK · NO CASCADE · NO DRIFT introduced.** Reconciliation-only: the store-authority rail is restored to
0 faults, and the authoritative store's row-count declaration is accurate again.

Rail re-verified: `ok store-authority: 7 store(s) declared | 1 tombstone(s) | 0 fault(s)` (exit 0).

## Note (not fixed — pre-existing, harmless)

The tombstone `backup/deletions/20260929_233442/diagnostic_diagnostic_20260811_232853.db` carries `-shm`/`-wal`
sidecar files regenerated at read time (sqlite WAL) — expected for a WAL-mode db opened by the rail. Not a defect.
