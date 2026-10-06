# FORENSIC AUDIT — D-2837e adoption recommendation + D-2838 writer-limb (2026-10-05)

## Verdict
**NO BREAK, NO CASCADE.** One concrete enforcement gap found and fixed (F-01, the D-2816
writer-limb). One strategic reorder required (F-03: D-2820 anchor re-derivation must precede
the full-204 A/B or the kappa is circular). Governance census GREEN. Flag OFF, uncommitted.

## Scope
Pre-implementation audit before committing the D-2814 definition-anchored menu work and the
adoption recommendation (D-2837). Checked for break / cascade / drift / blindspot / gap /
conflict / bug / hidden failure / error leak / mismatch / bloat.

## Findings

### F-01 (GAP + HIDDEN FAILURE — FIXED): `max_domains_per_fb=5` is DETECTED but NOT ENFORCED at the write
`validate_classification()` (pipeline/stage4_merge.py) emits "Too many domains: N > 5" but the
write-path salvage block drops only NON-canonical labels — so a row carrying 6-7 VALID domains
was written unchanged, `classification_status=CLEAN`. This is exactly BUG-631 (52 FBs, 0.65%,
every one CLEAN). The rail was a "comment", not a rail (D-2816 verification requirement).
**FIX (D-2838):** `_enforce_domain_cardinality()` truncates deterministically to the cap (keep
model first-5, preserve order) and records a receipt in `classification_error`, degrading
CLEAN → FALLBACK. Wired into the single salvage chokepoint so it covers ALL three S4 paths
(merged / batch / direct). Control test `tests/test_domain_cardinality_rail.py` proves it fires.
**Residual:** the 52 historical over-cap FBs are NOT yet re-derived — that is the post-replay
re-measure (`scripts/check_domain_cardinality.py`), BUG-631 stays OPEN for that.

### F-02 (ALIGNMENT — CLEAN): on-menu validation is single-sourced and aligned with menu v6
`pipeline/schemas.py::load_taxonomy()` and `pipeline/closed_menu.py::render_closed_menu()` BOTH
derive from `config/taxonomy_v5.yaml` (v5.7: 64 disciplines incl. the 3 B&M slots, 43 domains),
each adding `emerging`. `is_valid_discipline`/`is_valid_domain` therefore already accept the
B&M labels AND `emerging`. `config/closed_menu_v6.json` (65 disc / 44 dom) matches the rendered
menu. `config/taxonomy_shacl.ttl` is at v5.7 (BUG-641). No conflict between the D-2814 menu and
the D-2620 non-contamination guard (both read the same canonicals).

### F-03 (STRATEGIC REORDER — the D-2820 circularity): the A/B referee is frozen-invalid
D-2820 ruled the 204-gold discipline/domain axis FROZEN-INVALID until re-derived against the
post-D-2814/2815 menu, because it was adjudicated against the PRE-D-2814 free-gen menu. Therefore
running the full-204 A/B (T-1) NOW would measure the definition-anchored classifier against an
anchor that is a function of the OLD classifier — circular. **D-2820 anchor re-derivation must
PRECEDE the A/B.** This reorders the pending strategic sequence (see BUGS/TASKS/DECISIONS below).

### F-04 (TOOLING GAP — DEFERRED): pySHACL not installed
`pyshacl` is not importable (rdflib 7.1.4 is present). The pySHACL limb of D-2816 (validate the
MENU structure on a bump) requires `pip install pyshacl` (Apache-2.0, offline OK, C1). The WRITER
limb (F-01) is independent and is now done. Menu-bump pySHACL stays a follow-on.

### F-05 (GOVERNANCE — GREEN): decisions registry + census aligned
`recompute_decision_summary.py --check` GREEN: 966 decisions, records-only (D-2655), summary
describes exact bytes (source_sha256 6e829d7b8f1601cc). `bug_status.json/md` are mechanically
derived from buglog.md.

## Checks run
- `py_compile` on closed_menu.py / stage4_merged_call.py / stage4_merge.py / pipeline_paths.py: OK.
- `pytest tests/test_domain_cardinality_rail.py tests/test_depth_domain_contract.py`: 17 passed.
- `render_closed_menu()` block renders 15,099 chars; B&M disciplines + `emerging` present on both axes.
- Flag-off baseline: `definition_anchored_menu_enabled` / `discipline_closed_menu_enabled` absent
  from config → both default False (no prompt swap at runtime).
- D-2833 mutual-exclusion guard: present at module scope in stage4_merged_call.py (C16).

## Recommendations (see D-2837)
ADOPT the definition-anchored closed-menu architecture (ontologically correct, future-proof via
hash-stamped menu provenance). Gate the flag flip on the empirical full-204 A/B (kappa ≥ 0.800,
emerging ≤ 0.35) measured against a RE-DERIVED anchor (D-2820 first). Enforce quality at three
layers: prompt (D-2814), write-time rail (D-2816/D-2838), verification (D-2822 S5).
