# Forensic Audit — BUG-637 delta-aware `.expected_count.json` merge (D-2824/D-2825)

**Date:** 2026-10-05
**Scope:** `pipeline/stage4_merge.py` write-path change making the S4 `.expected_count.json`
sidecar write DELTA-AWARE for `--cluster` runs, plus one-time legacy-sidecar migration and
the D2338 gate-denominator move. Enables safe T2 delta recovery.
**Owner decisions:** D-2824 = dedup-accept (phantoms 3776/26074 stay dedup'd); D-2825 = pending
(lean accept-as-failed for cluster_28517).

## Verdict
SAFE to commit. R5 cross-family review (gemma-4-E4B-it-MLX-4bit) APPROVE on all 11 categories.

## Findings by category

1. **break** — Full-run path (`cluster_ids=None`) is byte-identical: same payload, same write.
   The `if cluster_ids:` branch is new and only fires on `--cluster`. NO break.
2. **cascade** — Sidecar still satisfies D-2817 `on_disk + declared == expected`. Post-T2:
   on-disk 6590 + declared 1 == expected 6591 (verified by simulation). S5 preflight
   (`--declared-failed`) and S6 gate both read `declared_failed_count` from the sidecar — intact.
3. **drift** — `total_clusters` moved to before the `--cluster` filter (and before D2120 dedup).
   Full-run denominator shifts by ~2 (phantoms) at threshold 0.0 — immaterial. The move ALIGNS
   code with the existing D2370 comment ("captured BEFORE filtering"), fixing a latent drift.
4. **blindspot** — Closed: legacy sidecar (declares failures but no `failed_cluster_ids` receipt)
   now REFUSES the delta merge with `sys.exit(1)` instead of silently overwriting. Corpus-change
   drift is also refused via `s2_input_fingerprint` mismatch.
5. **gap** — `failed_cluster_ids` is a `list[dict]` with `cluster_id` key throughout the loop
   (lines 1870/1878/1890/1901/2243). `_retained` filters `isinstance(r, dict)` — no KeyError.
6. **conflict** — `sys.exit(1)` on legacy/corrupt sidecar is intentional fail-closed (C16), not a
   conflict. It is the explicit pre-condition the migration removes.
7. **bug** — `_retained` + `failed_cluster_ids` concatenation verified correct: recovers 40300+26828
   → retained {28517}, declared 3→1; a 28517-only run keeps declared at 3.
8. **hidden failure** — `json.load` of a corrupt prior sidecar is caught (`except Exception`) and
   logged with type+message before `sys.exit(1)`. NOT swallowed.
9. **error leak** — every refusal path prints `❌` + reason and exits non-zero (C16 loud).
10. **mismatch** — delta branch uses PRIOR `expected_fb_count` (full corpus), NOT the subset-
    computed value at line ~1399. Verified the only other consumer of `expected_fb_count` is this
    sidecar write.
11. **bloat** — +46 lines, no new files/deps. The `total_clusters` progress print (line 1706) now
    shows full-corpus denominator during a `--cluster` run — cosmetic, interrupt-only, negligible.

## One-time data migration (not committed — gitignored data file)
`checkpoint.jsonl.expected_count.json` gained `failed_cluster_ids` (the 3 declared-failed clusters,
from BUG-635/BUG-637 audit trail): cluster_40300 "empty_domains", cluster_26828 "empty_domains",
cluster_28517 "empty_application". Written crash-safe (tempfile→fsync→os.replace, C6).

## Next critical steps (ordered)
- **T2 recovery** (needs OMLX): `python pipeline/stage4_merge.py --cluster 40300,26828` → recovers
  2, leaves 28517 failed (pending D-2825). Verify sidecar → expected 6591 / declared 1 / on-disk 6590.
- **D-2825** owner disposition for cluster_28517 (lean accept-as-failed).
- **BUG-638**: governance/METRICS.jsonl truncation guard.
- **T4**: menu v6 D-2814/D-2815/D-2816 (definition-anchored closed menu + Business & Management).
- **T6**: re-run S4→S5→S6 after BUG-637 + menu v6.
- **T9**: D-2822 Gate A(d) S5 aggregation.
- **T8**: owner-adjudicate R040/R053/R080/R091.
