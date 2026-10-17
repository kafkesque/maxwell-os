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
    python3 scripts/check_commit_scope_guard.py --selftest || exit 1   # BUG-773/D-2933 rule V controls (D-3036: the red loop this bug owed)
    python3 scripts/check_commit_scope_guard.py || exit 1   # BUG-773: the declared rule holds on the route that WILL run - knob AND branch
    python3 scripts/goose_profile.py --selftest || exit 1   # T-186/D-3056: extension RESIDENCY policy controls (extension rot)
    python3 scripts/goose_profile.py --check || [ $? -eq 2 ]   # T-186: policy vs live state - 2 = owner-owed (resident against policy), LOUD not fatal
    python3 scripts/measure_extension_cost.py --selftest || exit 1   # T-186: the cost measurement own arithmetic
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
    python3 scripts/check_ingest_identity_gate.py --selftest || exit 1   # D-2997/BUG-781: the INGEST DOOR's known-answer controls (the delta rule, a byte twin under a new name, an undeclared ledger verdict, a blind door, and — D-3040/T-130 option B — the DECLARED canonical lookup, its precedence, the cascade rule that must use the same resolution, and the refusals that keep an accepted debt a WORD rather than a default) — a control nothing runs is a comment (BUG-492)
    python3 scripts/check_ingest_identity_gate.py || [ $? -eq 2 ]   # D-2997/BUG-781: the identity the INGEST PATH never read — the D-2738 ledger held 59 adjudicable pairs, `adjudicated: 0`, from 2026-09-30 while BUG-780 measured the cost (530 rows certified by ONE voice under TWO names, 369 served). 2 = OWNER-OWED (a pair with no owner word; a name-defect class DECLARED owner_owed), loud NOT fatal (BUG-457). D-3040/T-130 option B and T-173/D-3043: every counted name class is DECLARED — printed, counted, with its row and its owner word — so no class is an rc 2 trigger unless the register says so. The SAME rc REFUSES at the ingest step — a DECLARED difference (config/ingest_identity_gate.yaml#door.ingest_reading), which is why the two readings are two declared lines and not one. MEASURED 2026-10-16: accepting the 459-stem marker class made the ingest reading rc 0 (0 delta candidates pending), and BUG-851 records the conflation that made that move invisible
    python3 scripts/check_agent_surface.py --selftest || exit 1   # T-169/BUG-845/D-3042: the ADAPTER SURFACE's known-answer controls, both directions (an undeclared client binding OUTSIDE the declared roots is a fault, the same binding INSIDE an adapter root is not, a declared site that owes a remedy is loud and not fatal, an owed site with no named row is a fault, a site class outside the declared vocabulary is a fault, a declared site that no longer carries a shape is a fault, a declared site that does not exist is a fault, an owed site naming a row that does not exist is a fault, the register may not grow past its shrink-only ceiling, a site declared owed whose shape lives only in PROSE is a fault and a site declared a citation whose CODE carries the shape is a fault (the class is MEASURED, D-3046), a portable artifact naming a client is a fault, a declared glob matching no file is a fault, an external root written inside the repo is a fault, an in-repo root that does not resolve is a fault, a cited decision the register does not carry is a fault, a journal reader that names no home is a fault, and an absent required key is FATAL rather than defaulted) — a control nothing runs is a comment (BUG-492)
    python3 scripts/check_agent_surface.py || [ $? -eq 2 ]   # T-169/BUG-845: the adapter surface's live reading. 2 = LOUD (a DECLARED site owes a remedy — MEASURED 2026-10-16: NONE, after the three hand-bound couplings were routed, T-175/D-3046), never fatal (BUG-457); 1 = an undeclared client binding in code, a stale declaration, a root that does not resolve, or an absent required key, and that IS fatal. It reads ONE home (config/agent_surface.yaml) and the two registers, and it writes nothing
    python3 scripts/check_bug_recall.py --selftest || exit 1   # D-3047: THE REGISTER'S RECALL - its known-answer controls on a FIXTURE register (a closed finding that names no trace reads UNTRACED and one that names a control or a ruling does not, a finding at or above the declared heading-event threshold reads CHRONIC and one below it does not, a named artifact that does not RESOLVE is reported and never counted as a trace (D-3034), a named ruling the declared home does not carry is reported, a citation to a sibling the register lacks is reported, recall names the finding that shares a reference and never a stranger, recall joins a cited artifact to the capability that declares it OWNS, a debt above its declared ceiling is LOUD and NOT fatal, an absent declaration key is FATAL and never defaulted, the reader names no declared path/pattern/threshold/ceiling of its own (proved by reading its own bytes, C12), a census face that disagrees with the register's own fold is FATAL and a matching one is not, a reference cited by more findings than the declared ceiling is EXCLUDED as common substrate AND counted, a finding related only by a sibling citation is not a neighbour, and a neighbour sharing fewer references than the declared minimum is not a relation) - a control nothing runs is a comment (BUG-492)
    python3 scripts/check_bug_recall.py || [ $? -eq 2 ]   # D-3047: the register's live recall - 0 every reading within its declared ceiling | 2 a class ABOVE it (DEBT: closed findings that left no trace, findings that have absorbed N amendments without closing, cited references that resolve against nothing), loud NOT fatal (BUG-457) so the ladder keeps running and the debt gets a row. It reads the register, the census face, the ruling home and the capability registry, folds headings through the ONE declared parser (D-2646, never a second implementation), and WRITES NOTHING: `--recall BUG-NNN` is the RETRIEVE step - the neighbours, the rulings it cites that resolve, and the rails that own what it names
    python3 scripts/census_source_names.py --brief || [ $? -eq 2 ]   # T-180/D-3049: THE NOTIFY, in ONE LINE, on every health run - the arrival pens and their oldest file, the misplaced count inside the declared roots, and the folders the declaration does not cover. It walks the owner library (MEASURED 2026-10-16: about 1 s for 2,530 files plus 1,741 in the pens), it MOVES NOTHING, and rc 2 is the owner-owed reading rather than a fault (BUG-457), which is why it carries the tri-state guard rather than the fatal one
    python3 scripts/census_source_names.py --selftest || exit 1   # D-3045/BUG-861: the SOURCE-LIBRARY reader's known-answer controls - a mirror-marker name is counted in the marker class and a truncated name is not, an unreadable root is FATAL and never a zero, a name the cache resolves is counted as ingest-coupled, the reader names no root path of its own (C12), a work in two homes with DIFFERENT bytes of the SAME kind is DRIFT while one in two CONTAINERS is not, a work in one home only is never drift, one work as two files of one kind is counted (that is what a topic COPY creates), and drift ABOVE the declared shrink-only ceiling is FATAL while a reading within it is loud and NOT fatal (BUG-457) - MEASURED 2026-10-16: these controls ran in NO ladder line until now, which is BUG-492 in the smallest possible form
    python3 scripts/plan_admission.py --brief || [ $? -eq 2 ]   # T-181/D-3051: THE ADMISSION NOTIFY, ONE line, on every health run: how many works in the declared kind roots the pipeline has never seen by the DOOR's own key, how many are admission candidates, and every refusal class with its count. It resolves the declaration's own homes (config/ingest_identity_gate.yaml#source_library.roots[].admits_to) and MOVES NOTHING; rc 2 is the owner-owed reading (rows waiting for the owner's word), loud never fatal (BUG-457). MEASURED 2026-10-16, first live run: 2,811 files, 1,697 seen, 1,114 never seen in 1,029 keys, 244 candidates, 870 refused (name repair first 188, container no stage reads 9, no declared corpus home 621, not in its kind folder 52)
    python3 scripts/plan_admission.py --selftest || exit 1   # T-181/D-3051: the ADMISSION PLAN's known-answer controls - a work the corpus holds by key is not a candidate while a work only an ingest record names is SEEN, a never-seen work is a candidate with a DERIVED target below the corpus home, a container no stage reads and a root with no declared corpus home and a file out of its kind folder are each REFUSED and COUNTED, a defective name is refused as repair-first, an absent root and an absent declaration key and an unresolvable corpus home are FATAL and never a zero (D-795), an axis outside the declared vocabulary is FATAL and a home whose axis is NOT the kind is never refused for its folder, the declared containers EQUAL the conversion stage's own constant, the key IS the door's own key, a bare run writes NOTHING (proved by reading its own bytes) and the reader names no path of its own (C12), and the ONE-line brief carries the reading's own numbers (a control nothing runs is a comment, BUG-492)
    python3 scripts/plan_source_rename.py --selftest || exit 1   # T-176/D-3048: the OWNER-LANE RENAME PLAN's known-answer controls - a marker-named file carrying author/title/year of its own is planned in the owner's format, a name the cache resolves is REFUSED as the T-172 cascade, a file with no author or no title in any declared source is refused and never named from its filename, an author that is a tool or a scanner is refused, a proposed name already taken is refused, a kind with no declared metadata source is refused by name, an absent year omits the segment and is counted, a bare run writes NOTHING (the single write call site sits behind --plan, proved by reading its own bytes), the sanitiser decodes an entity and trims a dangling separator, the planner names no path/template/pattern of its own (C12), and its FREE/COUPLED split equals the census reader's over the same library (a control nothing runs is a comment, BUG-492)
    python3 scripts/normalise_corpus_names.py --selftest || exit 1   # T-130 (owner word 2026-10-15): the CORPUS-NAME rename's controls - the whitespace transform must leave the DOOR's own _key() IDENTICAL, a rename onto an existing file is refused, a rename that changed one byte is rolled back, a CONTENT reference inside a derived artifact is counted (a filename-only census read a false green - BUG-798), and an untouched cache record must never be reformatted (D-2642)
    python3 scripts/normalise_corpus_names.py --census || [ $? -eq 2 ]   # T-130: the standing corpus-name debt + the CASCADE census. 2 = OWNER-OWED, loud not fatal (BUG-457). MEASURED 2026-10-15: 37 stems, each referenced ~80 times INSIDE 13 derived run-receipt artifacts (2,952 content refs; the parquet export alone holds 2,419), so the approved rename REFUSES to apply until it rides a re-ingest - a rename that leaves a dangling reference is a cascade (BUG-800)
    python3 scripts/owner_marks.py --selftest || exit 1
    python3 pipeline/harness_contract.py --selftest || exit 1   # T-132/D-3000: the harness context contract must BIND, not merely be declared - MEASURED 2026-10-15 the probe still read the trigger and the cap 'from default' while config/agent_context.yaml#ratified declared them, because a YAML declaration is not an environment variable; the module restates no declared value (C12)
    python3 pipeline/harness_contract.py --check || [ $? -eq 2 ]   # T-132: the contract's ONE reading of the RUNNING env. 2 = OWNER-OWED (unbound: the harness will use its own cloud price-tier defaults) - loud, NOT fatal (BUG-457); 1 = an env value CONTRADICTS the declaration, which is a drift and IS fatal
    python3 pipeline/harness_env.py --selftest || exit 1   # T-132/D-3003: the declared contract must have a working EXECUTOR, not only a reader - a declaration that never reaches the environment is a comment; T-175/D-3046 adds the READER for the names a pipeline WORKER must not inherit (config/agent_context.yaml#worker_env.strip), which is the declaration pipeline/parallel.py now reads instead of two literal client names
    python3 pipeline/harness_env.py --check || [ $? -eq 2 ]   # T-132: 2 = OWNER-OWED (the harness was started outside the executor); 1 = an env value CONTRADICTS the declaration and that is fatal
    python3 pipeline/delegation_economy.py --selftest || exit 1   # D-3023: the economy instrument's known-answer controls (local-only ledger, a cloud row over the ceiling, an absent ledger read as UNMEASURED and never as zero, a local model whose NAME carries a cloud marker still reading LOCAL, an unrecognised model joining neither tier, a row with no cost counted as UNKNOWN, a ratio below the declared floor reading INCONCLUSIVE, a ledger missing a declared column FATAL, and the module naming no ceiling of its own - proved by reading its own bytes, C12) - a control nothing runs is a comment (BUG-492)
    python3 pipeline/delegation_economy.py --check || [ $? -eq 2 ]   # D-3023/BUG-832: a cloud token is an ESCALATION, so the lifetime ceilings are SHRINK-ONLY. 1 = a ceiling is EXCEEDED (the only fatal reading: route the work to T0/T1, or the OWNER raises the ceiling with a reason); 2 = UNMEASURED, loud, NOT fatal (BUG-457)
    python3 pipeline/model_store_census.py --selftest || exit 1   # D-3033/BUG-838 + T-142/D-3034: the census's known-answer controls - the partition's DOMAIN is DECLARED and read, so a dataset repo and the store's own machinery can never reach ORPHAN (the only class a deletion may come from, D-3004(3)); an entry of no declared kind is a FAULT; a SENTENCE that mentions a model does NOT declare it while a value that IS the reference does (BUG-840); a path that does not resolve is not a claim (D-405); the reader's own file cannot declare a byte; a same-name copy is offered ONLY when its WEIGHTS are proved the same BY CONTENT and the files that differ are NAMED (T-167/BUG-843 - an inventory equality a hub snapshot can never reach was calling a byte-identical copy unique); LIVE needs its own subject, so a namesake served from elsewhere is not these bytes (BUG-841); the deletion floor is READ, never restated (D-3018); and measure_twice is proved to flag a moving store and not a still one (BUG-807) - a control nothing runs is a comment (BUG-492)
    python3 pipeline/model_store_sweep.py --selftest || exit 1   # T-167/D-3035: the ROUTE's known-answer controls - a batch with no owner word is refused, a word naming no record is refused, a receipt that exists is never overwritten, a receipt path no declaration owns is refused with the line to add, a NAME that is not a symlink is refused rather than followed, absent bytes are refused rather than claimed, ONE differing weight digest refuses the WHOLE batch, a valid batch removes the NAME before the BYTES and leaves the twin intact, and a declared order or copy policy this reader cannot honour is FATAL (a control nothing runs is a comment, BUG-492)
    python3 pipeline/model_store_sweep.py --plan || [ $? -eq 2 ]   # T-167/D-3035: the live reading - 0 nothing owed | 2 bytes an owner must dispose of (a PROVED redundant copy or a candidate above the floor). It PROPOSES and never deletes (R-D410); the act is --apply --owner-word <D-id> and it writes a receipt
    python3 pipeline/model_store_census.py || [ $? -eq 2 ]   # BUG-804/808/838: 2 = bytes only an owner disposes of (a candidate ABOVE config/engine.yaml#model_store.deletion_floor_bytes, D-3018) or an engine entry whose target is ABSENT; 1 = a FAULT (a hub entry of no declared kind); the census PROPOSES and never deletes (R-D410)
    python3 scripts/delegate_journal.py --selftest || exit 1   # T-168/BUG-844/D-3036: the DELEGATED-RUN TRACE's known-answer controls - a row with no purpose, no model or no budget is refused; a claim that resolves OUTSIDE the tree is refused; a claim ANOTHER OPEN RUN holds (by equality or by CONTAINMENT) is refused before either runs (C21/C23); a reused run id is refused; an end with no start, a second end and an undeclared state word are refused; a 'done' whose artifact is ABSENT is REFUSED and the row STAYS OPEN, so a false success has no home in the file; and the reader's own decisions - a fault outranks a budget, 90s past a 60s budget reads OVERDUE, a line that is not a row is a fault and not a shorter history (C16) - a control nothing runs is a comment (BUG-492)
    python3 scripts/delegate_journal.py status || [ $? -eq 2 ]   # T-168/BUG-844: the live reading - 0 nothing is open | 1 a JOURNAL FAULT (an unreadable line, a duplicate start, an end with no start) | 2 an OPEN run past its DECLARED budget, OWNER-OWED, loud and NOT fatal (BUG-457). MEASURED 2026-10-16: three delegates were reported cancelled, ONE had already written its artifact (6,573 B) and NOTHING ON DISK distinguished it from the two that had written nothing - a stall, a kill and a success were one observation to every later reader, which made the standing delegation rule unverifiable
    python3 pipeline/engine_boot_report.py || [ $? -eq 2 ]   # BUG-802: the $0 engine's survival - the ladder REPORTS the engine's own state (and whether a boot agent exists) instead of discovering it as a per-request failure hours later. 2 = OWNER-OWED (engine down, or nothing starts it after a reboot)
    python3 scripts/ingest_relabel_rulings.py --selftest || exit 1   # BUG-785: the T-117 READER's known-answer controls (a word outside the DECLARED vocabulary, a CORRECT with no home, a home no taxonomy canonical declares, an inert owner_canonical on a non-CORRECT row, the write keyed by unit_key and never by the ordinal, an applied receipt surviving a re-ingest, and the declared vocabulary staying a SUBSET of the applier's ACTIONS) — a control nothing runs is a comment (BUG-492)   # BUG-782: the OWNER-WORD INTAKE's known-answer controls (an unknown word, an unsigned tier, a withheld word, a transitivity conflict, a stale sheet, a dropped owner word, an unparseable predicate, a stale pair object) — a control nothing runs is a comment (BUG-492)
    python3 scripts/owner_marks.py --check || [ $? -eq 2 ]   # BUG-782: the owner lane's ONE reading — 2 = words still OWED (loud, NOT fatal, BUG-457); 1 = the words CONTRADICT each other or a sheet out of phase with its own measurement (the 42-vs-37 class). Fatal, because a resolved contradiction is a minted label (D-2898)
    python3 scripts/agent_context_probe.py --selftest || exit 1   # T-132/D-3000: the AGENT CONTEXT PROBE's known-answer controls (the trigger is the EARLIER of the percentage and the cap, a served window below the declaration is a TRUNCATION RISK, the reverse is a WASTED WINDOW, a model with no served window is UNVERIFIABLE, the route is the most capable class the window satisfies, a cache field that carries no value is UNKNOWN and never a measured zero (D-2957), the PREFILL BILL refuses a model that cannot pay for the working set, the working set is divided and never the window, a measured cache failure reads as DISPROVEN and never as unknown, a prompt size that was ESTIMATED is refused as a measurement (BUG-794), and the report path names no path, host or baseline number of its own — proved by reading its own bytes, C12) — a control nothing runs is a comment (BUG-492)
    python3 scripts/agent_context_probe.py --prefix-audit || exit 1   # T-132: the PIPELINE's amortisation precondition — every stage's system prefix must be a byte-stable module constant, because (MEASURED 2026-10-14) nothing reuses a prefix on this machine, so a stable prefix is the ONLY thing that can be amortised by packing requests. A prefix built per call is unique per call and no amount of batching can pay for it
    python3 scripts/agent_context_probe.py || [ $? -eq 2 ]   # T-132/D-3000: the HARNESS CONTEXT CONTRACT's live reading. 2 = a declared fault that is OWNER-OWED (a model the harness DECLARES and the server does not serve, or a window the server serves and no declaration names), loud NOT fatal (BUG-457). MEASURED 2026-10-14: six such drifts, and the local agent-loop trigger resolving to 80% of a 32768-token window on hardware that already serves 262144 to two other models
    python3 scripts/check_harness_homes.py --selftest || exit 1   # T-157/D-3044: the HARNESS HOMES' known-answer controls (a matching home reads BOUND; a reversal reads CONFLICT and NAMES the decision and row that own it; a fact with no declared expectation is WAITING-ON-A-HUMAN-WORD; an absent home, an absent key and an unresolvable pointer are FATAL and never BOUND — D-795; and the rail names no home path, key or provider of its own — proved by reading its own bytes, C12) — a control nothing runs is a comment (BUG-492)
    python3 scripts/check_harness_homes.py || [ $? -eq 2 ]   # T-157/D-3044: the harness homes a DECISION names, read back. 2 = CONFLICT (the home says something else: the D-295/BUG-243 reversal) or WAITING-ON-A-HUMAN-WORD, loud NOT fatal (BUG-457); 1 = a home or key that cannot be read. MEASURED 2026-10-16: before the binding this line read rc 2 on TWO facts (active_provider and the model pin) and printed the engine's own counter standing still at 594833 through a headless run; after `agent/adapters/goose/apply_provider_flip.py --apply-flip` all three facts read BOUND, rc 0, and the SAME run moved the counter 594833 -> 594835 — the everyday path no longer leaves the machine (T-174/BUG-849). RE-MEASURED 2026-10-17: this line read rc 2 AGAIN (active_provider back to custom_deepseek, no backup beside the home carrying the flipped value), so a governed write to the owner home does not survive whatever rewrites it - BUG-877; ONE --apply-flip restored 5/5 BOUND
    python3 agent/adapters/goose/apply_provider_flip.py --selftest || exit 1   # T-175/BUG-850: the harness-home WRITER's known-answer controls (an already-applied edit is NOT drift — the fault measured 2026-10-16, when the writer refused a home that was already in the state it produces; an ambiguous anchor and a file in neither state refuse the write; the backup precedes the first byte; a rollback restores it; the written home is READ BACK and the assignment must be in effect — D-3034; and the writer restates no provider or model name, proved against the LIVE declarations by reading its own bytes, C12) — a control nothing runs is a comment (BUG-492)
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
    python3 scripts/resolve_route.py --selftest || exit 1   # T-156/D-3024: the ROUTE GRAPH's own controls - a capability must resolve its entrypoint, its check, its receipt and its tier; a declared route whose entrypoint is ABSENT is refused; a lane whose recipe or command is gone is refused, and so is a lane command a GOVERNED recipe also runs (T-164); an open item whose MOVER nobody dispositioned is refused; a stale unrouted declaration is refused; routing debt above its shrink-only ceiling is refused; and the report is byte-stable (BUG-492: a control nothing runs is a comment)
    python3 scripts/resolve_route.py --check || exit 1   # T-156/D-3024: the live graph - every open task and bug ROUTES to a declared capability or carries a DECLARED reason, and the routing debt cannot grow past the ceiling it was measured at
    python3 pipeline/subagent_fanout.py --selftest || exit 1   # T-163/BUG-836: the DELEGATION executor's own controls - an answer's SHAPE is read and not only its LENGTH (a citation list with no finding is NOT an answer; a finding must cite the artefact under review AND state a defect; a finding whose location does not exist is not a finding; a description of what a line DOES is not a finding; the same answer passes ungated and FAILS once a shape is declared; an undeclared shape is refused and never invented; and the MEASURED 2,294-char gemma citation list - the DECLARED frozen control at governance/evidence/BUG836_gemma_citation_list.md, whose 82 citations ALL resolve - still reads as NOT AN ANSWER) - a control nothing runs is a comment (BUG-492)
    python3 scripts/check_bug_status.py || exit 1
    python3 scripts/check_governance_faces.py --selftest || exit 1   # SEVENTH rail - governance FACES must not contradict the register (BUG-588/D-2692); controls must fire (a control nothing runs is a comment, BUG-492)
    python3 scripts/gov_sync.py --selftest || exit 1   # D-2981/BUG-492/D-2985/D-2986/D-2987: the FACE writer's own controls - 21 named known answers (the block answers + the register schema, the OWNER LANE ordering, the re-cut SCOPE). A STALE block MUST be seen to differ from its re-derivation, and an entry that does not say WHO must move it MUST be refused (C16) - the register's schema validation uses the same function (task_faults), so this is where the rule is SEEN to hold
    python3 scripts/gov_sync.py || exit 1   # D-2981/D-2985: every user-facing face must EQUAL its re-derivation from the registers (derived index block + census restatement lines + session_seed derived fields), and the census re-cut is SCOPED to the live region - history is never rewritten (R-D410)
    python3 scripts/check_governance_faces.py || exit 1   # D-2984/D-2985/D-2986/D-2987: the FOUR CLAIM SURFACES of each face - the declared history region (a live-claim label, a live census marker, a decision ROW, a present-tense "BUG-N is OPEN" assertion are joined to the register, or they declare the moment they speak about), the LIVE region above the marker (one live label, citations that resolve, the OWNER LANE leading), the index HEADINGS between them (a heading that names a state says WHAT it is - a declared hand index, never the authority - and carries no count) and the STATES themselves (every DECLARED state carries a sign the authority renders, and the declared decision buckets PARTITION the register - a state the census counts that no bucket holds is a state the face does not show). Before D-2984, DECISION-LOG listed `| D2622 | ACTIVE |` under "OPEN / PENDING" while the register said RESOLVED; before D-2985 the owner's first screen led with work he could not move; before D-2986 twelve headings claimed a current state inside a region every face declares makes no live claim, two of them restating a drifted count; before D-2987 the authority printed every state as a bare word while the NON-authoritative index carried the colour, and the decisions line summed to 981 of 1114 - and the rail was green on all four
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
    python3 scripts/apply_relabel_store_write.py --selftest || exit 1  # T-103/D-2988: the LICENSED store write's known-answer controls (a writer's remedy must be SEEN)
    python3 scripts/check_served_fields.py --selftest || exit 1    # D-2989: the advertised-field rail's known-answer controls (a control nothing runs is a comment, BUG-492)
    python3 scripts/check_served_fields.py || [ $? -eq 2 ]          # D-2989: an advertised field is a CLAIM - live, declared-absent with an owed word, or refused; 2 = the OWNER WORD is owed (T-107), ceiling SHRINK-ONLY
    python3 scripts/check_feedback_parity.py --selftest || exit 1  # D-2989/D-2642: the ledger->cache parity controls must be SEEN to fire
    python3 scripts/check_feedback_parity.py || exit 1             # D-2989: the feedback cache must equal what its ledger recomputes through the declared formula (ONE home)
    python3 scripts/check_corroboration_bit.py --selftest || exit 1  # D-2993/BUG-775: the corroboration parity rail's known-answer controls (a drifted bit, a drifted count, an unreadable evidence set) must be SEEN to fire
    python3 scripts/check_corroboration_bit.py || exit 1             # D-2993: is_convergent/source_diversity must EQUAL what the row's OWN source_ids re-derive (ONE home: build_clusters). FATAL: a stored corroboration that disagrees with its re-derivation is a WRONG VALUE, not a debt - nothing about it is the owner's to decide (D-2642)
    python3 scripts/check_retired_names.py --selftest || exit 1    # D-2995/BUG-776: the retired-name rail's known-answer controls (an inline string IS a reference, a comment/docstring is archaeology, an undeclared reader FIRES, a STALE allowance FIRES) - a control nothing runs is a comment (BUG-492)
    python3 scripts/check_retired_names.py || exit 1               # D-2995: no live code path may READ a retired name, and no allowance may outlive its reason (both directions). FATAL: the wire-only retirement of D-2994 left the MACHINE reading borp_score (a rank fallback, two SELECTs, a monitor metric, an evaluator line, a pydantic default) - a value nothing writes, read as a measurement, is the BUG-511 class. The reference rule has ONE implementation, shared with the anti-resurrection rail (D-2642)
    python3 scripts/reanchor_retrieval_goldens.py --selftest || exit 1  # D-2991: the reviewed-sheet judgment's known-answer controls. `--check`/`--apply` need a REVIEWED SHEET and a draft that only exist at a review sitting, so the ladder pins the CONTROLS; the judgment they prove is the same one both modes call (INV-6)
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

# ── The delegation economy (D-3023): what leaves the machine, what stays, and the ceiling ──
economy:
    @python3 pipeline/delegation_economy.py

economy-json:
    @python3 pipeline/delegation_economy.py --json

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
    @python3 scripts/check_config_duplicate_keys.py || { echo "  ❌ A config key is being silently lost to a duplicate scope (BUG-822) — an instrument that is never called is not a guard (T-149)"; exit 1; }
    @python3 pipeline/subagent_fanout.py doctor || { echo "  ❌ The delegation guards cannot decide — a delegation would start unsound (BUG-809/BUG-826, D-3020)"; exit 1; }
    @python3 pipeline/research_run.py --check || [ $? -eq 2 ]   # T-154/BUG-828: every class bound is RECOMPUTED from its declared sources (the owner's per-turn knob, the measured decode rate, the class's longest measured turn). 2 = OWNER-OWED: the harness class ceiling is declared and NOT bound in the engine's own home, which is the owner's act and is therefore loud, not fatal
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
    python3 scripts/check_ingest_identity_gate.py --gate || exit 1   # D-2997/BUG-781: the door's INGEST reading — rc 2 here REFUSES (identity unresolved: a run would mint the corroboration claim its own evidence contradicts), rc 1 = a BLIND door (C16). Release = the owner words (T-129/T-131)
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
# --- 2026-10-15: durable research runs and engine lifecycle (T-137/T-138) ---
research-selftest:
    python3 pipeline/research_run.py --selftest

research-status:
    python3 pipeline/research_run.py status

model-loadability:
    python3 pipeline/model_loadability_probe.py || [ $? -eq 2 ]   # 2 = the engine refused a candidate; 1 = no oracle or an unreadable hub (fatal)

engine-guard:
    bash pipeline/omlx_engine_guard.sh   # 0 = the engine answers; it starts nothing when it already does (D-3007)

cache-dry:
    bash pipeline/omlx_cache_enable.sh   # apply with --confirm; --rollback is the A/B instrument (D-3008)
# --- 2026-10-15: fan-out delegation and model retirement (T-139/T-140) ---
fanout:
    @echo "fanout: plan --tasks TASKS.yaml --run ID | start --run ID | status --run ID | verify --run ID --model M --out S.md"
    python3 pipeline/subagent_fanout.py status --run $(RUN) || true

ask:
    python3 pipeline/oneshot_ask.py --model $(MODEL) --prompt "$(Q)" --out temp/ask.md

retire-dry:
    bash pipeline/omlx_retire_model.sh --model $(MODEL)   # --confirm parks it; the bytes need safe_delete (R-D410)

# T-168/BUG-844/D-3039: WHO IS RUNNING - the delegated-run journal, one word for the owner.
# 0 nothing is open | 1 a journal fault | 2 an OPEN run past its DECLARED budget (loud, not fatal, BUG-457).
delegates:
    @python3 scripts/delegate_journal.py status --all

# --- 2026-10-16: the SOURCE LIBRARY (T-176/D-3048) and the harness-home WRITER ---
# The writer's home MOVED in T-175/D-3046 (agent/adapters/goose/) and the ladder comment that taught the old
# path kept teaching it, so the owner's command failed with `No such file or directory` (BUG-861). A command a
# human is told to run belongs in an OPERATOR LANE, where scripts/resolve_route.py CHECKS it against the recipe
# so a stale path is a fault and never a surprise (T-164/BUG-837). Dry-run is the default: this writes nothing.
provider-flip:
    python3 agent/adapters/goose/apply_provider_flip.py --dry-run

# What the OWNER's library holds and costs: the name classes, the FREE/COUPLED split (T-176). READ-ONLY.
source-names:
    python3 scripts/census_source_names.py --census || [ $? -eq 2 ]   # BUG-863: rc 2 here is the DECLARED contract (name debt is OWNER-OWED, loud, never fatal - BUG-457), and just(1) was printing "error: Recipe ... failed" for it, so the owner read a working reading as a broken command. Same form as the harness-homes lane above

# ONE WORK, HOW MANY MATERIALISATIONS: the two homes, their drift and their one-sided counts (D-3048).
arrangement:
    python3 scripts/census_source_names.py --arrangement || [ $? -eq 2 ]   # BUG-863: drift WITHIN the declared shrink-only ceiling is owner-owed (loud), never a failed command

# The RENAME PLAN the owner's word asked for: writes governance/SOURCE_RENAME_PLAN_<date>.md (+ .json).
# It renames NOTHING; the act that applies it is separate and owner-worded (T-176).
rename-plan:
    python3 scripts/plan_source_rename.py --plan || [ $? -eq 2 ]   # BUG-863: a plan carrying refused rows is the OWNER-OWED outcome, not a failure - and it renames nothing
# THE ADMISSION PLAN the flow's fifth transition asks for: what the pipeline has never seen, by the door's own
# key, and where each candidate's corpus copy would land. It writes governance/ADMISSION_PLAN_<date>.md (+ .json)
# and admits NOTHING - the act that admits a work is separate and owner-worded (T-183).
recipes:                                             # the DECLARED sub-agent recipe vocabulary (config/engine.yaml#fanout.task_recipes): what to delegate, which AXIS model, and the DETERMINISTIC done-check that decides whether a human may be left out. Read-only.
    python3 pipeline/subagent_recipe.py --list
recipe-plan name *set:                               # render ONE declared recipe into a fan-out task file under temp/recipe_<name>_<ts>/ - STARTS NOTHING
    python3 pipeline/subagent_recipe.py --plan {{name}} {{set}}
subagent-loop-measure:                               # D-2549/T-131: the PER-MODEL sub-agent loop measurement - one fixed 3-call task, every SERVED model, one receipt per run
    python3 scripts/measure_subagent_loop.py
extensions:                                          # T-186/D-3056: what each declared extension COSTS while resident - schema bytes/tokens shipped PER REQUEST, measured by spawning it
    python3 scripts/measure_extension_cost.py

extension-profile name:                              # T-186/D-3056: the two realisations of ONE profile (config flips + the --no-profile command). Writes nothing.
    python3 scripts/goose_profile.py --render {{name}}

session profile:                                     # D-3064: BIRTH a task-labelled session with one profile - the surface is EXPLICIT, never inherited, and a birth that would be dead is REFUSED
    python3 scripts/goose_profile.py --launch {{profile}}

born n="5":                                          # D-3064: what each of the last N sessions was GIVEN at birth, read from the harness's own store (never from a transcript)
    python3 scripts/goose_profile.py --born {{n}}

extensions-check:                                    # T-186/D-3056: residency policy vs live harness state - tri-state (0 agree | 1 fault | 2 owner-owed)
    python3 scripts/goose_profile.py --check

extensions-adopt:                                    # D-3060: register extensions that ARRIVED with no decision - into QUARANTINE, granting nothing
    python3 scripts/goose_profile.py --adopt

extensions-delegate profile:                         # D-3060: the smallest extension set a delegate of this class is born with
    python3 scripts/goose_profile.py --delegate {{profile}}

admit-plan:
    python3 scripts/plan_admission.py --plan || [ $? -eq 2 ]   # BUG-863: rows waiting for the owner's word ARE the OWNER-OWED outcome, not a failed command - and it moves nothing
placement:
    python3 scripts/census_source_names.py --placement || [ $? -eq 2 ]   # T-180/D-3049: WHERE things are, against where the declaration says they belong - the misplaced kinds, the loose files, the undeclared subfolders, and what is waiting in each declared ARRIVAL PEN (how old, and how much of it the pipeline has never seen). READ-ONLY; the repair is T-180, owner-worded
