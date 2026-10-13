# Maxwell OS v3.0 — justfile
# Authority: CONSTITUTION.md §6

# ── Health ───────────────────────────────────────────────────
health:
    @echo "=== Maxwell OS v3.0 Health Check ==="
    python3 scripts/run_ladder.py --banner health --full health-full   # D-2680/BUG-573/BUG-582: the ladder reports a PREFIX (it stops at the first non-zero line) - declared HERE, before any rail can abort, with the entry point that reports the whole set
    python3 scripts/check_repo_integrity.py || [ $? -eq 2 ]   # RAIL 0: 0 git metadata intact | 1 repository defect (P0-A/P0-B, BUG-400) | 2 owner-owed
    python3 scripts/check_repo_integrity.py --worktree || exit 1   # BUG-563: every DIRTY path must be GRANTED by the plan's may_touch or DECLARED-EXCLUDED (joined to git's own ignore verdict); neither = FATAL
    python3 scripts/check_commit_frontier.py || exit 1   # D-2860: anti-circle - refuse to proceed with uncommitted ratified governance state (commit first)
    @just --list >/dev/null || { echo "FAIL justfile does not parse - the health rail cannot verify itself"; exit 1; }
    python3 scripts/guard_stacks_single_source.py || exit 1
    python3 pipeline/status.py
    python3 pipeline/integrity_check.py --quick
    python3 scripts/audit_flag_consumers.py || exit 1
    python3 scripts/verify_anchor_manifest.py || exit 1
    python3 scripts/verify_split_manifest.py --selftest || exit 1   # D-2733: golden/eval split leakage rail controls (BUG-492)
    python3 scripts/verify_split_manifest.py || exit 1   # D-2733/BUG-603: a golden id re-entering eval FAILS (208->162 invariant)
    python3 scripts/verify_source_identity.py --selftest || exit 1   # D-2734/BUG-289: canonical source_id controls — a control nothing runs is a comment (BUG-492)
    python3 scripts/verify_source_identity.py || exit 1   # D-2734/BUG-289: source_diversity counts canonical source_ids, NOT filenames (20+ duplicate-book-source fix must hold)
    python3 scripts/detect_title_renames.py --selftest || exit 1   # D-2735: near-duplicate detector controls (a control nothing runs is a comment, BUG-492)
    python3 scripts/detect_title_renames.py || exit 1   # D-2735: READ-ONLY candidate report — surfaces near-dup pairs for OWNER gating, never auto-merge
    python3 scripts/detect_same_work_content.py --selftest || exit 1   # D-2737: full-text content dedup controls (a control nothing runs is a comment, BUG-492); LIVE scan is opt-in (--report, ~2min)
    python3 scripts/gate_duplicate_candidates.py --selftest || exit 1   # D-2738: owner-gate ledger generator controls (a control nothing runs is a comment, BUG-492)
    python3 scripts/verify_duplicate_gate.py --selftest || exit 1   # D-2738: fail-closed dedup-gate rail controls (BUG-492)
    python3 scripts/verify_duplicate_gate.py || exit 1   # D-2738: owner-gate ledger structural check — never auto-merge; --gate is POST-RUN apply only
    python3 scripts/consolidate_anchor4_context.py --check || exit 1
    python3 scripts/check_depth_menu.py || exit 1
    python3 scripts/menu_axis_hashes.py --check || exit 1   # the answer-space pin must not be STALE (D-371/BUG-453)
    python3 scripts/validate_depth_domain_contract.py --gate-if-active || [ $? -eq 2 ]   # 2 = owner-owed: loud, NOT fatal (BUG-457)
    python3 scripts/check_human_instruments.py || exit 1
    python3 scripts/check_instrument_cohorts.py governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv || exit 1
    python3 scripts/check_existence_negatives.py || exit 1
    python3 scripts/check_buglog_coverage.py --selftest || exit 1   # BUG-570/BUG-492: the buglog BLOAT rail's own controls - a byte-identical COPY must fire and two DIFFERENT blocks must not
    python3 scripts/check_buglog_coverage.py || exit 1   # BUG-570: no block may be a byte-identical copy of another (the earlier 'not identical' refusal compared an occurrence to EOF - length-dependent, always unequal)
    python3 scripts/r5_review_gate.py --selftest || exit 1   # D-2962/BUG-738: the R5 code-review gate's known-answer controls (a TRUNCATED file MUST fail the syntax layer, scripts/* MUST resolve to a declared tier, the Qwen-lineage model MUST stay declared not-a-candidate) - a control nothing runs is a comment (BUG-492)
    python3 scripts/restamp_content_type_adjudications.py --selftest || exit 1   # BUG-712/BUG-741/BUG-742: the re-stamp gate's OWN decisions (a MOVED pre-state MUST be refused, a DISPOSITION MUST never be written as a content_type, an undeclared destination MUST fail closed, the authorship sentinel MUST keep --apply closed)
    python3 pipeline/stage6_commit.py --selftest || exit 1   # D-2965/BUG-712: the WHOLE write path's leaf-label gate - a BLANK and a DISPOSITION must BOTH be refused BEFORE the DB is touched, every declared ROLE must be admitted, the verdict must follow the DECLARATION (not a constant), and a MISSING declaration must fail closed at load (a control nothing runs is a comment, BUG-492)
    python3 pipeline/integrity_check.py --selftest || exit 1   # BUG-739: C11's OWN classifier, BOTH directions - an undeclared third-party import MUST still be flagged (a rail that accepts everything is not a rail) and the stdlib names it once misread MUST NOT be
    python3 scripts/check_bug_status.py || exit 1
    python3 scripts/check_governance_faces.py --selftest || exit 1   # SEVENTH rail - governance FACES must not contradict the register (BUG-588/D-2692); controls must fire (a control nothing runs is a comment, BUG-492)
    python3 scripts/gov_sync.py --selftest || exit 1   # D-2981/BUG-492: the FACE writer own known-answer controls (a STALE block MUST be seen to differ from its re-derivation)
    python3 scripts/gov_sync.py || exit 1   # D-2981: every user-facing face must EQUAL its re-derivation from the registers (derived index block + census restatement lines + session_seed derived fields)
    python3 scripts/check_governance_faces.py || exit 1   # D-NEW: bug-status table rows + header census in DECISION-LOG/MTR must agree with bug_status.json / decisions_summary.json
    python3 scripts/check_register_divergence.py --selftest || exit 1   # BUG-571/D-2683: BOTH divergence shapes must be SEEN to fire on synthetic logs (a control nothing runs is a comment, BUG-492)
    python3 scripts/check_register_divergence.py || exit 1
    python3 scripts/check_freeze_window.py --selftest || exit 1   # D-2688: the freeze WINDOW's declared EXIT must be SEEN to fire (a control nothing runs is a comment, BUG-492)
    python3 scripts/check_freeze_window.py || [ $? -eq 2 ]        # D-2688: a freeze is a WINDOW - the parked set is COUNTED and the exit is DECLARED; 2 = OWNER-OWED (exit MET -> close it, or horizon PASSED -> re-rule it), loud NOT fatal (BUG-457)
    python3 scripts/apply_owner_domain_review.py --selftest || exit 1   # BUG-492: the OWNER-RULING applier's known-answer controls (drop-not-anchor, drop-without-ledger, abstention-for-drop, the BUG-679 PARTITION invariant, declared-drop-with-upstream-residue, primary!=domains[0], off-menu-domain, undeclared-sheet-fragment, cross-face divergence) - a control nothing runs is a comment
    python3 scripts/apply_owner_domain_review.py --check || exit 1   # BUG-678/BUG-679: the owner-derived axis authority must be RE-DERIVABLE byte-identically from the pinned owner sheet, and every anchor row must be either axis-bearing or a declared noise_drop (this rail was referenced in the decision log for two rounds and RUN BY NOTHING)
    python3 scripts/apply_owner_domain_review.py --check-faces || [ $? -eq 2 ]   # BUG-682: a ruling that lands in the owner-derived authority but NOT in the face the pipeline reads is an error leak; 2 = measured, SHRINK-ONLY declared ceiling (BUG-457 tri-state, loud NOT fatal)
    python3 scripts/check_anchor_axis_consistency.py --selftest || exit 1   # D-2811/BUG-628: the ANCHOR five-axis propagation control must be SEEN to fire (a control nothing runs is a comment, BUG-492)
    python3 scripts/apply_anchor_axis_authority.py --selftest || exit 1   # D-2812/BUG-628: the authority PROPAGATOR must be SEEN to fire before it rewrites an artifact (BUG-492)
    python3 scripts/check_anchor_axis_consistency.py || [ $? -eq 2 ]        # D-2811/BUG-628: every ANCHOR consumer must agree with the ONE declared authority per axis; 2 = declared owner-owed debt, ceiling SHRINK-ONLY (BUG-457)
    python3 scripts/lib/write_guard.py --selftest || exit 1
    python3 scripts/lib/yaml_guard.py --selftest || exit 1       # D-2648 controls: a guard whose controls nothing runs is a comment (BUG-492)
    python3 scripts/lib/yaml_guard.py --check || [ $? -eq 2 ]    # BUG-525/D-2649: a key declared TWICE in one mapping is SILENTLY last-wins; 2 = owner-owed artifacts
    python3 scripts/lib/artifact_encoding.py --selftest || exit 1
    python3 scripts/lib/operator_env.py --selftest || exit 1    # BUG-519: the operator-key rule has ONE home; its controls never print the value
    python3 scripts/check_encoding_homes.py --selftest || exit 1  # BUG-492 controls for the D-2646 decode-home rail  # D-2644/D-2649: declared-encoding controls - a guess at an owner artifact is measured, not assumed
    python3 scripts/lib/write_guard.py --audit || [ $? -eq 2 ]   # 2 = declared unguarded writers: loud, NOT fatal (BUG-457); D-401/I1
    python3 scripts/apply_workbook_rulings.py --selftest || exit 1   # BUG-560/D-2685: the applier's known-answer controls (scope join, header join, out-of-scope refusal) - a control nothing runs is a comment (BUG-492)
    python3 scripts/apply_workbook_rulings.py --check || exit 1   # BUG-560: the anti-REVERT rail - DECLARED in three homes since D-387 and RUN in none until now; a normalize re-run must never revert an owner ruling silently
    python3 scripts/check_depth_load_bearing.py || exit 1
    python3 scripts/check_serving_gate.py --selftest || exit 1   # the D274a invariant's known-answer controls (a guardrail never seen failing is not a guardrail)
    python3 scripts/check_serving_gate.py || [ $? -eq 2 ]        # D274a CI invariant over every stored row: 1 defect | 2 owner-owed label/status ontology (BUG-499), loud NOT fatal
    python3 scripts/check_label_provenance.py --selftest || exit 1   # the BUG-497 boundary classifier's known-answer controls
    python3 scripts/check_label_provenance.py || exit 1   # BUG-497/D-2640: a row OUTSIDE the declared boundary without the R1 stamp is a DEFECT - a broken stamp must not hide behind the boundary
    python3 scripts/check_menu_reclass_gate.py --selftest || exit 1   # BUG-747/BUG-492: the menu-identity gate's arms must be SEEN to fire (a control nothing runs is a comment)
    python3 scripts/check_menu_reclass_gate.py || [ $? -eq 2 ]        # D-2894/D-2928/BUG-693: a run's menu identity is the ANSWER SPACE (D-371); 2 = OWNER-OWED (a wording-only composite move owes the AUDIT, never a provenance rewrite)
    # ^ this comment was found DISPLACED onto the check_config_defaults line on 2026-09-26 (three comments on one
    #   line after a merge): a comment that documents another rail is a declaration with the wrong home (D-2649).
    python3 scripts/check_s5_score_axis.py --selftest || exit 1   # BUG-502: the score axis' known-answer controls
    python3 scripts/check_s5_score_axis.py || exit 1   # BUG-502: the ONE score-axis home must reproduce the stored corpus
    python3 scripts/check_revoked_references.py --selftest || exit 1   # D-2645: the anti-resurrection rail known-answer controls
    python3 scripts/check_revoked_references.py || [ $? -eq 2 ]        # D-2645: a revoked SCOPE may be named by NO live file; 2 = owner-owed, loud NOT fatal
    python3 scripts/check_derivation_homes.py --selftest || exit 1     # D-2646: ONE DERIVED VALUE, ONE HOME - the known-answer controls
    python3 scripts/check_derivation_homes.py || [ $? -eq 2 ]          # D-2646: a rival definition of a registered home is the BUG-499/BUG-502 class
    python3 scripts/build_anchor_store_bridge.py --selftest || exit 1   # BUG-420: the anchor<->corpus bridge known-answer controls
    python3 scripts/build_anchor_store_bridge.py --check || [ $? -eq 2 ]   # BUG-420/BUG-551: the join is keyed by CONTENT (D-2658); 2 = owner-owed (a SAFE ambiguous refusal, or a row the config DECLARES), 1 = a BRIDGE GAP (the D-2618 retired golden is recorded, never gated)
    python3 scripts/check_config_defaults.py --selftest || exit 1      # D-2644: the undeclared-default census known-answer controls
    python3 scripts/check_config_defaults.py --check || [ $? -eq 2 ]   # D-2644: a config value read with a code default is UNDECLARED; 2 = the declared ceiling is stale (read-only; re-record via --record)
    python3 scripts/check_config_duplicate_keys.py --selftest || exit 1   # BUG-730/BUG-492: the duplicate-config-key detector must be SEEN to fire
    python3 scripts/check_config_duplicate_keys.py || exit 1  # BUG-730/C16: a duplicate config key REPLACES its twin SILENTLY (PyYAML last-wins) - one such key emptied ti_to_pt_keywords and killed a routing tier with every other rail green
    python3 scripts/lib/handoff.py --selftest || exit 1
    python3 scripts/verify_handoffs.py --check || [ $? -eq 2 ]      # 2 = owner-owed: loud, NOT fatal (BUG-457); D-403; read-only (publish via --record)
    python3 scripts/resolve_dropbox_conflicts.py --selftest || exit 1     # D-2647 tri-state controls (BUG-492)
    python3 scripts/check_encoding_homes.py --check || [ $? -eq 2 ]   # D-2646: a second decode implementation is DETECTED, not remembered; 2 = declared debt
    python3 scripts/check_silent_repair.py --selftest || exit 1     # BUG-492: the C16 silent-repair detector must be SEEN to fire
    python3 scripts/check_silent_repair.py --check || [ $? -eq 2 ]   # C16/BUG-511: no reader may silently repair bytes; 2 = declared debt, SHRINK-ONLY
    python3 scripts/check_undeclared_encoding.py --selftest || exit 1   # BUG-492: the undeclared-codec detector must be SEEN to fire
    python3 scripts/check_undeclared_encoding.py --check || [ $? -eq 2 ]  # D-2644/BUG-521: an encoding the ENVIRONMENT decides is UNDECLARED; 2 = declared class, SHRINK-ONLY
    python3 scripts/check_store_authority.py --selftest || exit 1  # BUG-492: the store-authority detector must be SEEN to fire
    python3 scripts/check_store_authority.py --check || exit 1     # BUG-524/STORES: exactly ONE authoritative store; a shared table name fails closed
    python3 scripts/check_store_columns.py --selftest || exit 1    # BUG-492: the column-lifecycle detector must be SEEN to fire
    python3 scripts/check_store_columns.py --check || [ $? -eq 2 ]  # BUG-524/COLUMNS: a label that cannot vary, a blank a count(col) cannot see; 2 = declared debt
    python3 scripts/check_domain_cardinality.py || [ $? -eq 2 ]   # D-2838/BUG-631: reader-limb re-measures the committed store for over-cap FBs; 1 = over-cap (historical re-derivation owed), 2 = parse-defect
    python3 scripts/resolve_dropbox_conflicts.py --check || [ $? -eq 2 ]  # D-2647: a Dropbox-reverted artifact must never pass silently; 2 = siblings only the owner can settle
    python3 scripts/reconcile.py --selftest || exit 1  # BUG-575/D-2682: the decision-graph rules (succession + force) must be SEEN to fire (a control nothing runs is a comment, BUG-492)
    python3 scripts/reconcile.py --check || [ $? -eq 2 ]    # 2 = owner-owed debt: loud, NOT fatal (BUG-457)
    python3 scripts/lib/measure.py --gaps || exit 1
    # ^ ORDER IS LOAD-BEARING (BUG-489/BUG-490): every resolver rail runs BEFORE these two checker rails.
    #   reconcile joins each DECLARED resolution domain to the record its rail has just published; measure
    #   --gaps then checks the journals - and it DERIVES this order from this recipe (measure.health_chain)
    #   and DRIFTs if a declared resolver rail sits AFTER it, because then "has not run yet" would read as
    #   "never published" (which is how reconcile once reported ITSELF as an unpublished metric).
    python3 scripts/verify_anchor_family_registry.py || exit 1
    python3 scripts/verify_menu_routing.py || exit 1
    python3 scripts/verify_menu_policy.py || exit 1
    python3 scripts/verify_recalibration_pins.py --selftest || exit 1   # BUG-526/BUG-492: the pin rule's WRITE-time controls, incl. the OVERREACH control (an unrelated commit must be TOLERATED)
    bash scripts/install_git_hooks.sh --check || exit 1   # BUG-526: the pre-commit hook is a DERIVED artifact living outside version control; it must equal its own re-derivation, not be remembered
    python3 scripts/verify_recalibration_pins.py || [ $? -eq 2 ]   # BUG-536: 2 = a MOVED pin the OWNER owes a re-mint; loud, NOT fatal,
    #   so an owner-owed pin cannot ABORT the ladder and hide the rails below it (BUG-457 tri-state; the hook still refuses any non-zero).
    python3 scripts/verify_generator_pins.py --selftest || exit 1   # BUG-538/D-2653: the GENERATOR-identity rail's known-answer controls (12: incl. that a TRUNCATED revision is FATAL, and that a declared-but-unmeasurable fact is OWNER-OWED, never a silent pass - BUG-492)
    python3 scripts/verify_generator_pins.py || [ $? -eq 2 ]   # BUG-538/D-2653: WHO PRODUCED THE NUMBERS. 0 = every declared generator matches the bytes on disk; 1 = broken declaration, fails CLOSED (C16); 2 = a MOVED generator (or an alias that disagrees) the OWNER owes a re-mint - a pin is re-minted by a DECISION (D-382/BUG-535), never by a quiet re-hash
    python3 scripts/verify_declared_inputs.py || exit 1
    python3 scripts/verify_frozen_pair.py || exit 1
    python3 scripts/verify_evidence_manifests.py || exit 1
    python3 scripts/verify_artifact_authority.py || exit 1
    python3 scripts/r3_preflight.py || exit 1
    python3 scripts/verify_vec_integrity.py || exit 1
    python3 scripts/verify_boundary_injection.py || exit 1
    python3 scripts/depth_pass_agreement.py --report-only
    python3 scripts/depth_pass_agreement.py --check-cohort || exit 1
    python3 scripts/build_archive_index.py --selftest || exit 1   # BUG-537/BUG-556/BUG-492: the archive rail's own decisions (a silent de-listing, a shadowed rule, a transient input) must be SEEN to fire
    python3 scripts/build_archive_index.py --check || exit 1
    python3 scripts/check_rail_registry.py --selftest || exit 1   # D-2665/BUG-492: the registry's OWN decisions (an unowned rail, a stale dormancy, a guard the ladder contradicts, a writer with no proven remedy) must be SEEN to fire
    python3 scripts/check_rail_registry.py || exit 1   # D-2665: the rail set had NO registry - classes (i) a rail nothing runs, (ii) a printed verdict that disagrees with its exit code, (iii) a remedy or INPUT nobody controls (BUG-537/BUG-556)
    python3 scripts/recompute_decision_summary.py --selftest || exit 1  # D-2660/BUG-492: the MINT gate's own controls - a record is joined to the tree BEFORE a byte is written
    python3 scripts/recompute_decision_summary.py --check || exit 1
    python3 scripts/check_decision_membership.py --selftest || exit 1  # BUG-587/BUG-492: the MEMBERSHIP rail's own known-answer controls (the ABSORBED-mint shape, a STALE pin) - a control nothing runs is a comment
    python3 scripts/check_decision_membership.py || exit 1             # BUG-587/D-2690: an id NAMED in DECISION-LOG.md must name a TOP-LEVEL record in config/decisions.yaml - the oracle the BUG-402 tombstone names and no file implemented
    python3 scripts/check_tests.py --selftest || exit 1   # BUG-492: the suite rail's OWN decisions (floor breach, regression, paid red, strict) must be SEEN to fire
    python3 scripts/check_tests.py --check || exit 1      # D-2656: the SUITE is a RAIL - a failing test no rail runs is a control that never fires (BUG-470 class). 3 failures are DECLARED red and SHRINK-ONLY (the depth/domain contract is 'proposed'/owner gate); a 4th is FATAL, 0 collected is FATAL, a paid red is OWNER-OWED (2)

    python3 scripts/check_declaration_consumers.py --selftest || exit 1   # D-2669/BUG-492: the CONSUMER JOIN's own decisions (a withheld consumer in the commit set, an over-reaching census, an unreadable registry) must be SEEN to fire
    python3 scripts/check_session_plan.py --selftest || exit 1   # BUG-565/BUG-492: RAIL 4's OWN controls, incl. that a path containing a SPACE is ONE path (fourth hardening); wired here because a control nothing runs is a comment
    python3 scripts/check_boundary_rehearsal.py --selftest || exit 1     # D-2675: the boundary's own 13 controls
    python3 scripts/check_boundary_rehearsal.py || [ $? -eq 2 ]           # D-2675: the write boundary at a REAL commit
    python3 scripts/check_rail_mutations.py --selftest || exit 1          # D-2676: the standing rule's own teeth (a gate never seen to PASS is not a gate)
    python3 scripts/check_rail_mutations.py || [ $? -eq 2 ]               # D-2676: every declared rule SEEN to red through its own named control at a MUTATION
    python3 scripts/lib/fixture.py --selftest || exit 1                   # BUG-577: the shared fixture rules own known-answer controls (ONE home; a control nothing runs is a comment, BUG-492)
    python3 scripts/run_ladder.py --selftest || exit 1                    # D-2680/BUG-582: the ladder collector own known-answer controls (a control nothing runs is a comment, BUG-492)
    python3 scripts/check_declaration_consumers.py || exit 1              # D-2669: no declaration without its reader - BUG-562 landed the pair in one commit; this makes the JOIN a property, not an act
    python3 scripts/run_ladder.py --receipt-check || [ $? -eq 2 ]         # D-2983/BUG-759: the last FULL scan is a MEASUREMENT with a COVERAGE and an AGE - 1 (a red RECORDED under exactly this coverage) is FATAL, 2 (UNKNOWN: never measured here, measured against a different ladder, or older than the declared budget) is OWNER-OWED, loud, never fatal. Declared in config/rail_registry.yaml#ladder_receipt. It stands LAST on purpose: a whole-set report placed early would hide every line it speaks for

healthcheck: health

# D-2680/BUG-573: the WHOLE fault set in ONE run. `health` above is the fast, human-readable ladder and it
# reports a PREFIX - a red line hides every line after it, which is why each repair round used to cost a new
# session to discover the next fault. This recipe runs the same declared lines through the same guards and
# reports EVERY fault with its own rc and seconds, exiting with the WORST code, never the first.
health-full:
    python3 scripts/run_ladder.py --collect health

# ── One-panel inference stack monitor (D2456): versions + drift + single-source ──
stacks:
    @python3 scripts/monitor_stacks.py

preflight:
    @echo "=== Maxwell OS Preflight ==="
    @python3 scripts/check_repo_integrity.py || [ $? -eq 2 ]   # RAIL 0 also gates a RUN: a conflicted/git-renamed tree must not be the tree a batch writes from (BUG-400/BUG-500)
    @python3 scripts/monitor_stacks.py || exit 1
    @python3 -c "from pipeline.pipeline_paths import ensure_dirs; ensure_dirs(); print('✅ Directories OK')"
    @python3 -c "from pipeline.pipeline_paths import check_books_source; ok, msg = check_books_source(); print(msg); exit(0 if ok else 1)"
    @python3 -c "from pipeline.pipeline_paths import check_pipeline_state; print(check_pipeline_state())"
    @python3 tools/verify_golden_hash.py || { echo "  ❌ Golden hash mismatch — golden set changed without re-stamping .golden_meta.json (D2367)"; exit 1; }
    @python3 pipeline/config_audit.py --check-unchecked --strict || { echo "  ❌ Config drift or unchecked hardcoded values — fix before continuing"; exit 1; }
    @python3 -c "from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES; print(f'✅ Taxonomy: {len(CANONICAL_DOMAINS)} domains, {len(CANONICAL_DISCIPLINES)} disciplines')"
    @python3 -c "from pipeline.omlx_call import check_omlx_health; ok = check_omlx_health(); print('✅ OMLX UP' if ok else '❌ OMLX DOWN')"
    @python3 scripts/recompute_decision_summary.py --check || { echo "  ❌ Decision summary drift — run scripts/recompute_decision_summary.py"; exit 1; }
    @echo "  🔍 Dependency check..."
    @pip3 check 2>&1 || echo "    ⚠️  Dependency conflicts found (non-blocking — see above)"
    @echo "    📦 Outdated packages:"
    @pip3 list --outdated --format=columns 2>/dev/null | wc -l | xargs -I{} echo "      {} total (run 'pip3 list --outdated' for details)"
    @echo "  🖥️  Hardware-model fit..."
    @llmfit 2>&1 | head -5 || echo "    ⚠️  llmfit unavailable"
    just integrity-quick
    just stress

# ── Stress-test OMLX chat (catches the 'health endpoint lies' bug) ──
stress:
    @echo "=== Pre-flight: Memory ==="
    PYTHONPATH=. python3 pipeline/memory_guard.py --min-gb 6 || exit 1
    @echo "=== OMLX Chat Stress Test ==="
    PYTHONPATH=. python3 pipeline/stress_test.py

# ── G10: OMLX wired-memory leak stress test (D2020 Layer 1, pre-26h-run gate) ──
wired-stress:
    PYTHONPATH=. python3 pipeline/omlx_wired_stress.py

# ── Pipeline ──────────────────────────────────────────────────
status:
    python3 pipeline/status.py

# v3.0 cluster-before-extract pipeline (D2115: updated stage order)
triad:
    @echo "=== v3.0 Pipeline Run (cluster-before-extract) ==="
    python3 pipeline/stage0_convert.py
    python3 pipeline/stage0_5_extract_metadata.py
    python3 pipeline/stage1_chunk.py
    python3 pipeline/stage1_3_prefilter.py
    python3 pipeline/stage1_5_embed_cluster.py
    python3 pipeline/stage2_extract.py
    python3 pipeline/stage4_merge.py
    python3 scripts/dedup_fb_id.py
    python3 scripts/remap_emerging.py
    python3 scripts/gate_emerging_rate.py || exit 1
    python3 scripts/audit_s4_final.py || exit 1
    python3 pipeline/stage5_verify.py
    python3 pipeline/stage6_commit.py
    python3 pipeline/status.py

# ── Delegate Safety Check (DELEGATE-001) ──────────────────────────
delegate-check:
    python3 tools/delegate_safe.py

delegate-fix:
    python3 tools/delegate_safe.py --fix

# ── Standardized one-shot local-LLM delegation (BUG-220 / D2543) ──
# Qwen3-Coder single-shot code gen ONLY — never multi-turn (DELEGATE-002).
oneshot model prompt:
    python3 pipeline/omlx_delegate.py --model "{{model}}" --prompt "{{prompt}}"

# ── Two-tier Smoke Tests (D2120) ────────────────────────────────────────

# Tier 1: Plumbing smoke — no LLM, validates pipeline plumbing (<30s)
smoke-plumbing:
    @echo "=== Plumbing Smoke (no LLM, <30s) ==="
    MAXWELL_RUN_ID=smoke MAXWELL_SKIP_LLM=1 python3 pipeline/stage0_convert.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_chunk.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_3_prefilter.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_5_embed_cluster.py
    @echo "✅ Plumbing smoke complete (LLM stages skipped)."

# Tier 2: Fast smoke — Phi-4-mini, skip Gemma deep check (<2min)
smoke-fast:
    @echo "=== Fast Smoke (Phi-4-mini, <2min) ==="
    MAXWELL_RUN_ID=smoke python3 pipeline/stage0_convert.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_chunk.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_3_prefilter.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage1_5_embed_cluster.py
    MAXWELL_RUN_ID=smoke MAXWELL_FAST_MODEL=Phi-4-mini-instruct-8bit python3 pipeline/stage2_extract.py
    MAXWELL_RUN_ID=smoke MAXWELL_SKIP_GEMMA=1 python3 pipeline/stage5_verify.py
    MAXWELL_RUN_ID=smoke python3 pipeline/stage6_commit.py
    @echo "✅ Fast smoke complete. Check output in stage6_commit/smoke/"

# Full smoke: default models (Qwen3-Coder-30B + gpt-oss-20b, ~5min)
smoke: smoke-fast
    @echo "ℹ️  For plumbing-only (<30s no LLM): just smoke-plumbing"

# ── E2E test (P1.5) ───────────────────────────────────────────
e2e-test:
    python3 pipeline/e2e_test.py "$@"

e2e-test-fast:
    python3 pipeline/e2e_test.py --quality fast "$@"

e2e-test-dry:
    python3 pipeline/e2e_test.py --dry-run "$@"

# Alias: full pipeline evaluation (end-to-end validation)
eval: e2e-test

# ── MLX direct inference (2-3× faster, needs OMLX stopped) ─────
mlx-smoke:
    MAXWELL_INFERENCE_BACKEND=mlx just smoke-fast

mlx-e2e:
    MAXWELL_INFERENCE_BACKEND=mlx just e2e-test

# ── Individual stages ─────────────────────────────────────────
stage0:
    python3 pipeline/stage0_convert.py
stage0_5:
    python3 pipeline/stage0_5_extract_metadata.py
stage1:
    python3 pipeline/stage1_chunk.py
stage1_3:
    python3 pipeline/stage1_3_prefilter.py
stage1_5:
    python3 pipeline/stage1_5_embed_cluster.py
stage2:
    python3 pipeline/stage2_extract.py

# P2-1 / BUG-152 (2026-08-21): re-extract the t11 single-source clusters with the
# balanced golden + per-type body schemas, skipping the already-correct convergent
# FBs. S2 ONLY — stops before S4/S5/S6 so the single-source output can be visually
# inspected before any classification/verification/commit. Logs to
# knowledge pipeline/stage2_extract/t11/single_source_rerun.log AND stdout (tee).
s2-single-source-rerun:
    @echo "=== S2 single-source rerun (t11, P2-1/BUG-152) — convergent skipped ==="
    @mkdir -p "knowledge pipeline/stage2_extract/t11"
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-single-source --reset-single-source 2>&1 | tee "knowledge pipeline/stage2_extract/t11/single_source_rerun.log"

# Tail the live S2 single-source rerun log (progress tracker).
s2-single-source-status:
    @tail -n 60 -f "knowledge pipeline/stage2_extract/t11/single_source_rerun.log"

# Resume the t11 single-source rerun from its checkpoint. NO --reset-single-source:
# keeps the already-extracted single-source FBs (incl. backfilled elaboration) and
# continues the remaining clusters with the FIXED elaboration-required prompt.
s2-single-source-resume:
    @echo "=== S2 single-source RESUME (t11) — continues from checkpoint, fixed prompt ==="
    @mkdir -p "knowledge pipeline/stage2_extract/t11"
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-single-source 2>&1 | tee "knowledge pipeline/stage2_extract/t11/single_source_rerun_resume.log"

# Tail the elaboration-backfill log (BUG-155 post-hoc fix, ~1760 records).
s2-backfill-status:
    @tail -n 40 -f "knowledge pipeline/stage2_extract/t11/backfill_elaboration.log"

# D2437/D2452: deterministic pre-LLM singleton gate (EXTRACT/SKIP verdicts, model-free).
# Produces singletons.prefiltered.jsonl consumed by s2-singletons below. Re-run only
# when singletons.jsonl or config/filtering.yaml changes.
s2-singletons-prefilter:
    python3 scripts/prefilter_clusters.py \
        --clusters "knowledge pipeline/stage1_5_embed_cluster/t11/singletons.jsonl" \
        --chunks "knowledge pipeline/stage1_chunk/t11/checkpoint.jsonl" \
        --config config/filtering.yaml \
        --out "knowledge pipeline/stage1_5_embed_cluster/t11/singletons.prefiltered.jsonl"

# D2452/D2453: singleton extraction — gated by singletons.prefiltered.jsonl (EXTRACT only).
# --only-singletons skips run_stage2 (single-source/convergent already extracted +
# post-hoc filtered). Skips the 28,805 SKIP (noise/junk) singletons, extracts only the
# ~6,317 EXTRACT. Crash-safe + resumable (D2453 checkpoint/resume). Stops before S4/S5/S6.
s2-singletons:
    @echo "=== S2 singleton extraction (t11, prefilter-gated, resumable) ==="
    @python3 -c "from pipeline.omlx_call import assert_omlx_no_cache; assert_omlx_no_cache()"
    @mkdir -p "knowledge pipeline/stage2_extract/t11"
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_extract.py --only-singletons 2>&1 | tee "knowledge pipeline/stage2_extract/t11/singleton_run.log"

# D2177: stage3 removed (D2120) — redirects to runner
stage4:
    @python3 -c "from pipeline.omlx_call import assert_omlx_no_cache; assert_omlx_no_cache()"
    python3 pipeline/stage4_merge.py
stage5:
    @python3 -c "from pipeline.omlx_call import assert_omlx_no_cache; assert_omlx_no_cache()"
    python3 pipeline/stage5_verify.py
# D2505: pre-S6 commit gate — verify S5 checkpoint (count/uniqueness/contamination)
# before S6's INSERT OR REPLACE. Fail-closed; run before `just stage6`.
pre-s6:
    python3 scripts/pre_s6_gate.py

stage6:
    python3 pipeline/stage6_commit.py

# D2485 (D2491): post-S4 emerging-rate gate (BUG-150) — fail-closed between S4 and S5.
# Measures discipline/domain/unmapped emerging rates; exit 1 if any exceed config
# thresholds (config/pipeline_config.yaml → taxonomy.*). Never promote stale labels.
gate-emerging:
    python3 scripts/gate_emerging_rate.py

# BUG-150 recurrence guard: post-S4 fb_id collision dedup (D2350/D2069). Merges
# true duplicates that collided on fb_id so S6's INSERT OR REPLACE never silently
# drops rows. Runs before remap/gate/S5/S6.
dedup-fb-id:
    python3 scripts/dedup_fb_id.py

# BUG-150 recurrence guard: Phase 0a (Unicode fold) + Phase 0b (alias map) remap
# of emerging discipline/domains to existing canonicals. Reduces the raw emerging
# rate (36.2% → ~25%) so the gate passes without blind promotion. Alias-only: does
# NOT bump taxonomy_version; raw labels preserved verbatim.
remap-emerging:
    python3 scripts/remap_emerging.py

# Pre-S5 deterministic forensic audit (completeness / uniqueness / ontology /
# stamps / raw-preserve / provenance / drift). Fail-closed; no LLM. Default gate
# between S4 and S5 — do NOT advance to S5 on a non-zero exit.
audit-s4:
    python3 scripts/audit_s4_final.py

# BUG-150 recurrence guard: crash-safe, idempotent S4-completion handler.
# Waits for S4, validates, backs up, then runs dedup → remap → gate. Stops before
# S5/S6 (review the gate first). Unattended:
#   nohup python3 scripts/s4_post_finish.py --watch > logs/s4_post_finish.log 2>&1 &
post-s4:
    python3 scripts/s4_post_finish.py --watch

# ── Export & Backup ───────────────────────────────────────────
export:
    python3 pipeline/query.py --export > data/fbs_export.jsonl
    @echo "✅ Exported to data/fbs_export.jsonl"

backup:
    bash pipeline/backup_guardian.sh

# ── Integrity — 17 automated checks (D2203) ──────────────────
integrity:
    @echo "=== Maxwell OS Integrity Check (D2203) ==="
    python3 pipeline/integrity_check.py

integrity-quick:
    python3 pipeline/integrity_check.py --quick

# ── Full audit: config drift + integrity + lint + delegate safety ──
audit:
    @echo "=== Maxwell OS Full Audit ==="
    python3 pipeline/config_audit.py --check-unchecked --strict || { echo "  ❌ Config drift or hardcoded values — fix before continuing"; exit 1; }
    python3 pipeline/integrity_check.py --quick
    @python3 -m ruff check pipeline/ 2>&1 | tail -5
    python3 tools/delegate_safe.py
    @echo "✅ Audit complete"

# ── D2205 Retrieval Tools ─────────────────────────────────────
# Graph-aware retrieval (FTS + vector + keyword + graph expansion)
retrieve-graph query:
    python3 pipeline/retrieve.py --graph-aware "{{query}}" --limit 15

# Agentic retrieval (iterative with critique loop)
retrieve-agentic query:
    python3 pipeline/retrieve.py --agentic "{{query}}" --limit 15

# Retrieval evaluator — test critique on current DB
retrieve-eval query fb_ids:
    python3 pipeline/retrieval_evaluator.py --critique-only --fb-ids "{{fb_ids}}"

# D2205 Migration — TOMBSTONED 2026-09-25 (BUG-503)
# The three recipes that used to live here (migrate-epistemic / -dry / -verify) were a REACHABLE
# write path into an ABANDONED ontology: they ALTER fbs with 8 D2205 columns, one of which is
# epistemic_state TEXT DEFAULT 'corroborated' - it would stamp "corroborated" on rows nobody
# corroborated. Removed deliberately: an abandoned ontology must not have a reachable write path.
# The script remains for the archaeology and now REFUSES (exit 2 = owner-owed) unless the owner
# passes --i-understand-D2205-is-abandoned. Reviving D2205 is an OWNER decision.

# MCP Server — start Maxwell knowledge server for agents
mcp-server:
    @echo "=== Maxwell MCP Knowledge Server ==="
    @echo "Starting... Register with Claude Desktop or Goose."
    @echo "Config: { 'mcpServers': { 'maxwell': {"
    @echo "  'command': 'python3',"
    @echo "  'args': ['maxwell_mcp_server.py'] } } }"
    python3 maxwell_mcp_server.py

mcp-test:
    python3 maxwell_mcp_server.py --test

# ── Vibecheck — Ruff + format on changed files (D2109) ───────
vibecheck:
    @echo "=== Vibecheck ==="
    @python3 -m ruff check --fix pipeline/ 2>&1 | tail -3
    @python3 -m ruff format --check pipeline/ 2>&1 | tail -1
    @echo "✅ Vibecheck complete"

vibecheck-full:
    @echo "=== Full Vibecheck (all checks) ==="
    python3 -m ruff check pipeline/
    python3 -m ruff format --check pipeline/
    @echo "=== Syntax check on all pipeline .py files ==="
    @for f in pipeline/*.py; do python3 -c "compile(open('$$f').read(), '$$f', 'exec')" && echo "✅ $$f" || echo "❌ $$f"; done
    @echo "✅ Full vibecheck complete"

# ── Deep rail (D-390) ─────────────────────────────────────────────
# WHY THIS EXISTS: `just health` runs RAILS, not the SUITE. A stale assertion in tests/ is
# invisible to every rail — BUG-470 (`test_depth_frugal_is_off` asserted a literal D2454 had
# refuted) sat undetected at HEAD for exactly that reason, and D-390 states the split.
# health-deep = the aggregate rail PLUS the full test suite in STRICT mode: the declared red
# ceiling must be EMPTY, i.e. the suite must be fully green.
# SAFE TO RUN since BUG-473/BUG-546: conftest.py fails the session if the suite moves a
# production artifact, and the smoke tests now resolve their stage dirs through pipeline_paths
# and REFUSE to delete an undeclared run id.
health-deep: health
    @echo "=== deep rail: full test suite, strict (D-390/D-2656) ==="
    python3 scripts/check_tests.py --check --strict

# ── Cleanup ───────────────────────────────────────────────────
clean:
    @echo "Use pipeline/safe_delete.py for safe deletion"
    @echo "  python3 pipeline/safe_delete.py data/checkpoints/ --reason 'reset pipeline'"

# -- Handoffs (D-403): a stage handoff is a RECEIPT, not a path -----------------
# WHY: a stage that declares an input PATH cannot prove which BYTES it consumed, and a producer that rewrites
# that path later invalidates every downstream claim while nothing fails (BUG-376; BUG-488 found the same
# defect inside the receipt itself: a quoted digest whose bytes no live path held). scripts/lib/handoff.py
# takes a receipt (digest, bytes, mutability, code_sha, stamp); scripts/verify_handoffs.py compares BYTES.
# This recipe is the rail's CALLER, so a verify_* script is not a declaration with no caller (BUG-482/486).
handoffs:
    @echo "=== handoffs (D-403): every claim re-derived from bytes ==="
    python3 scripts/lib/handoff.py --selftest
    python3 scripts/verify_handoffs.py --record

# -- Instrument controls (D-400): no instrument decides before a sealed control ---
# WHY: an instrument measured only on rows its own builder chose is not evidence (BUG-480). config/
# instrument_controls.yaml declares every instrument BEFORE it is measured, so the number cannot pick its own
# falsification; scripts/instrument_control.py scores it against a control whose answer was withheld.
# NOT in the health recipe: 2 of 3 declared instruments still hold NO sealed control - owner-owed, not fatal.
instruments:
    @echo "=== instrument controls (D-400): a confusion matrix before any decision ==="
    python3 scripts/instrument_control.py --selftest
    python3 scripts/instrument_control.py --report

# -- Criteria board (BUG-482/BUG-484) ------------------------------------------
# WHY: governance/p0_p1_criteria.yaml has declared 28 executable criteria since 2026-09-17 and
# scripts/drift_monitor.py evaluates every one of them - but NOTHING invoked the monitor, so 28 declarations
# (two of them check_*.py rails) were reachable only by hand. That is BUG-482 one level up: a declaration with
# no caller. This recipe is the caller, and scripts/reconcile.py derives reach through it, not from a filename.
# NOT in the health recipe: 3 of the 28 criteria are DRIFT (real, open findings - BUG-484). A rail known to be
# red does not belong in the fail-fast invariant chain; it belongs where its redness is visible and declared.
criteria:
    @echo "=== criteria board: governance/p0_p1_criteria.yaml (drift_monitor) ==="
    python3 scripts/drift_monitor.py
