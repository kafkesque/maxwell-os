# SESSION HANDOFF — 2026-10-13 — D-2980 (retrieval serving: ONE dispatch point, DECLARED and MEASURED)

Commits: 3998844 (inherited) · bd2f71c (impl D-2980) · e67742f (gov D-2980)
Working tree: CLEAN (repo-integrity worktree rc=0, 0 dirty paths). Register: 1108 decisions / 520 bugs (185 open / 335 closed).

## 1. WHAT LANDED (and why it was the highest-leverage next step)

The served retrieval surface had no SINGLE declared entry point, so neither the adoption of vector+rerank
(D-2724) nor its own audit claim could be checked. Three defects shared that one cause:

1. BUG-753 (CLOSED) — D-2724 named THREE call sites repointed off search_hybrid(); TWO production surfaces
   were missed and stayed on the superseded RRF path for two weeks with every rail green:
   maxwell_mcp_server.py::_tool_query_knowledge (the graph_aware=false branch — an agent's plain search) and
   pipeline/retrieve.py::main (the CLI default query path). Both now dispatch through search().
2. The call-site matrix gets a home — config/serving_call_sites.yaml declares 4 production call sites + 7 leg
   callers (each with a reason; scope is a file GLOB). tests/test_retrieval_serving_spec.py (INV-5) asserts BOTH
   directions by AST: routing (a serving surface must call the dispatcher) and inventory (every leg call is
   declared, every declaration is live). The matrix is joined to its reader in config/declaration_consumers.yaml,
   so a staged matrix with a withheld reader is refused at commit time (the BUG-562 shape).
3. BUG-710 (CLOSED) — goldens re-anchored (D-2939, earlier today) + the ranking gate enabled (D-2979) + the
   harness now BENCHES THE SERVED PATH (new "production" leg = the dispatcher) + the pool policy has ONE config
   home (serving.pool) and ONE code home (_rerank_pool_size / _rrf_leg_pool_size, read fail-closed with NO code
   default). pipeline/query.py's second, un-gated dead borp_score clause is repointed to the ONE ranking home,
   and an OR/AND precedence bug that let its name-LIKE branch ignore the canonical-run pin (D-2881) is fixed.

### MEASURED (the number the decision rests on)
D2511 benchmark, 29 owner-anchored goldens, k=10, pool=50 (= the served pool):
    production  1.000 recall@10   0.919 MRR   0.100 P@k     <- the SERVED path (vector + cross-encoder rerank)
    hybrid      0.931             0.601       0.093
    vector      0.862             0.417       0.086
    fts         0.655             0.351       0.066
NAMED LIMIT: recall@10 is SATURATED at 1.000. A saturated metric cannot gate an improvement: the next retrieval
change must be judged on MRR (0.919) and the GOLDEN SET is the thing to harden (harder/abstract queries), not the
pipeline.

## 2. THE INHERITED DEFECT THIS SESSION FOUND AND REPAIRED (own it, name it)

The previous session inserted D-2978/D-2979 at the HEAD of config/decisions.yaml instead of APPENDING
(D-2655 half B) — a BUG-376-class in-place rewrite of the receipted region, committed as 3998844, with the census
never re-derived. Consequences, all measured: verify_handoffs --check red (unattributed rewrite),
check_governance_faces red (faces restated 1105/516 vs 1108/519), and 4 suite failures that no declared red set
covered (BUG-755).
REPAIRED: the census was re-derived (1105 -> 1107 -> 1108), the registry was written through the GOVERNED mint (a
MUTATION_JOURNAL receipt now has the live bytes as its post-image), and the receipt was re-cut with the D-2971 act
(--rebaseline decisions_registry --because D-2980 --commit 3998844 --commit bd2f71c --apply; supersedes
2d0fce3a, and those superseded bytes still re-derive from git:659cecdc). BUG-755 CLOSED ON MEASURED EVIDENCE: the
4 tests went 4 failed -> 11 passed, and the suite rail went rc=1 (448 passed / 4 failed) -> rc=0 (452 passed /
0 declared red). No ceiling was widened and no test was edited.

## 3. RAIL STATE AFTER THIS SESSION (measured, not asserted)

GREEN: check_tests --check (457 collected / 452 passed / 0 declared red / 5 skipped) ·
check_declaration_consumers (7 homes, 9 edges) · check_governance_faces (1108 / 520) · check_bug_status ·
check_buglog_coverage (738 blocks) · recompute_decision_summary --check (records-only, stamp 0e8a8bdb996a4e20) ·
verify_handoffs --check (6 paths, 13 digests, 3 revisions) · config_audit --check-unchecked --strict ·
check_repo_integrity --worktree.

RED / OWED, each NAMED:
1. BUG-754 (MED, OPEN) — check_config_defaults --check rc=1: 241 shadowed-declared against a shrink-only ceiling
   of 229. A/B proven pre-existing (byte-identical measurement with and without this session's config).
   Attribution: 7 config leaf names added after the ceiling commit 2b7958c reclassify existing default-reads
   (commit_scope, dedup_gate, require_both, s5_owned_columns, serving, symmetric_relationship_types,
   taxonomy_dependent_columns) plus code-side sites added since. THE LADDER IS RED ON THIS LINE: read every other
   green line as "green after this one", because the ladder reports a PREFIX (D-2680/BUG-573).
2. R5 cross-family review OWED — the OMLX server is DOWN (only Ollama :11434 answers), so neither the repo gate's
   reviewer (r5_review_gate.py) nor a delegate review could run; one delegate attempt failed with
   "error decoding response body". The DETERMINISTIC layers WERE measured on all 5 changed files: C11/C12 PASS
   (imports are a subset of requirements), and the lint I001 finding is PRE-EXISTING at 3998844 (measured on
   baseline copies) and was deliberately NOT reformatted — ruff's fix merges the annotated import lines and would
   delete the provenance comments. Re-run when OMLX is up: python3 scripts/r5_review_gate.py --file pipeline/retrieve.py
   (and the other four changed files).
3. BUG-756 (LOW, OPEN) — the census restatement has NO tracked writer (its only "sync" is the session scratch file
   temp/sync2690.py), so the two face lines had to be re-cut by a DERIVED substitution. Remedy owed: land the sync
   as a tracked writer invoked by the ladder next to check_governance_faces.
4. Named residuals in specs/retrieval_serving.spec.md — the MCP payload still EXPOSES borp_score / feedback_score
   (retired/derived fields; an MCP output-schema change needs its own owner-gated decision), and
   serving.superseded_runs still lists the purged runs (inert for serving; it is the restore-path declaration).

## 4. NEXT CRITICAL STEPS (strategically ordered)

1. HARDEN THE GOLDEN SET (now the highest-leverage retrieval act): recall@10 is saturated at 1.000, so the gate
   cannot see an improvement. Add harder/abstract and adversarial goldens (owner-signed anchors, D-2898/D-2939)
   and re-run the production leg; MRR is the metric to move.
2. BUG-754: remove the code defaults on the 7 named keys (the rail's own remedy) or rule a ceiling raise that
   records the increase as a RECLASSIFICATION of existing debt. Until then the ladder is red at that line.
3. R5 review of D-2980 when OMLX is up (the deterministic layers are already measured).
4. BUG-749 residual (457 rows): 103 LATE-HOME + 60 ABSTAIN are OWNER-RULED and recorded as OWED store writes
   (D-2898 gate); 173 alias-layer-retired rows await evidence or owner eyes; the D-2974 re-scope audit keeps
   feeding queue A. This is the largest remaining ontology-accuracy item on the SERVED labels.
5. BUG-756: land the tracked census-restatement writer.
6. P4 queue (user-standing): mine DEVONthink 3 (related-document ranking — the replacement candidate for the
   retired borp_score) and Cursor (derived code index) with REA; open-source targets are read directly:
   LlamaIndex content+config cache invalidation, Instructor typed response contract, Docling layout/table
   recovery, RAGChecker / Ragas / BGE-M3 retrieval-quality baseline.

## 5. OPEN-BUG LIST CARRIED FORWARD (C15: 5+ unresolved -> appended to the handoff)

Session-touched: BUG-754 (config-defaults ceiling, MED) · BUG-756 (census-restatement writer, LOW).
Highest-priority others from the register (185 open): BUG-749 (HIGH, re-derivation gap, 457 rows) · BUG-748 (MED,
re-scope sweep + the rail that holds its ceiling) · BUG-712 (content_type routing debt, residuals named) ·
BUG-714 (tool_instruction rows are code snippets — blocks the harness-facing primitive) · BUG-711 (173 displaced
canonical domains). CLOSED today or earlier: BUG-710, BUG-713, BUG-745, BUG-752, BUG-755.


---

# ADDENDUM 2026-10-13 (later) — D-2981: the user-facing faces are DERIVED, JOINED and ORDERED

Commits: 0d653d7 (gov D-2981). Register after the change: 1109 decisions / 521 bugs (185 open) / 12 open tasks.

## THE COUNTS (the answer to "exactly how many", derived, therefore not stale)

| axis | total | open / needing action | ordering home |
|---|---|---|---|
| decisions | 1109 | 67 NEED ACTION (open 32, proposed 14, draft 1, deferred 14, planned 6); in effect 565; closed 308 resolved / 16 superseded / 8 archived / 11 rejected | config/decisions_summary.json |
| bugs | 521 | 185 OPEN (335 closed); severity distribution printed from the heading population; 125 open headings carry NO severity token (BUG-757) | governance/bug_status.json |
| tasks | 12 open | MUST 5 - SHOULD 4 - WORTH 3, of which 1 is OWNER-GATED | config/task_register.yaml (NEW: the missing register) |

The MUST list, in strategic-consequential order (now live in every face):
T-101 harden the retrieval golden set (recall@10 is saturated) - T-102 BUG-754 (the ladder is RED on
check_config_defaults) - T-103 BUG-749 residual (163 owner-ruled rows, store-write-owed) - T-104 BUG-757
(the severity gap) - R-1 the standing rule that the faces are derived and never hand-appended at the top.

## WHAT WAS MEASURED AS WRONG WITH THE FACES (before this change)

1. agent/session_seed.yaml is LOADED AT BOOT and was SEVEN DAYS STALE: pipeline_commit v3.0-D2370 against the
   manifest v3.0-D2485, status dated 2026-10-06. Drift in a boot file propagates into every session that reads
   it - the highest-leverage defect found in this audit.
2. MASTER-TASK-REGISTER.md and DECISION-LOG.md headers said 2026-10-07; MTR's live index appeared THREE times
   inside the same file (2026-10-12 / 2026-10-07 / undated) and 240 lines of prose sat where a register should be.
3. No machine-readable task register existed: "how many tasks are open" had NO answer.
4. The census restatement had no tracked writer (BUG-756); its only sync was a session scratch file in temp/.

## THE FIX (one writer, one check, both in the ladder)

* config/task_register.yaml — the missing register: id, priority (MUST/SHOULD/WORTH), state (open/blocked/gate/
  done/superseded), source, evidence, gate. It carries the modularity (C21) + cross-OS (C26) roadmap items as
  T-106 and the REA/open-source queue as T-105.
* config/gov_sync.yaml — the DECLARED joins: register to face, the sentinel-delimited index block, the history
  boundary, the derived scalar fields, the OPEN decision states, the severity/task vocabularies, and the two
  shrink-only severity ceilings (125 heading / 108 title, BUG-757).
* scripts/gov_sync.py — the ONE writer. Renders GOV-INDEX into the three MD faces from the registers, re-cuts
  EVERY census restatement line (both the stamped and the pre-D-2981 stamp-less shape — that is what retires
  BUG-756), and derives session_seed pipeline_commit and status. Its default mode is --check and it
  BYTE-COMPARES the block in the file against its re-derivation, so a hand edit is DETECTABLE. 9 known-answer
  controls (--selftest), including a STALE block that MUST be seen to differ.
* justfile + config/rail_registry.yaml + config/artifact_ownership.yaml — the writer is declared (the four faces
  are derived_regenerable), and the ladder runs --selftest then the check.
* The append convention, ENFORCED: everything below the GOV-HISTORY-START sentinel is DATED HISTORY (append-only,
  never a register, never re-counted). NOTHING WAS DELETED — the old prose index was declared history by placing
  the marker above it. New work enters at its register, never at the top of a face.

## MEASURED RAIL STATE AFTER D-2981

GREEN: scripts/gov_sync.py --check rc=0 (4 faces equal their re-derivation; --selftest 9/9) - check_governance_faces
(1109 / 521) - check_bug_status - check_buglog_coverage (740 blocks) - check_rail_registry (every rail invoked or
declared dormant; every declared writer's remedy proven by the ladder) - check_declaration_consumers (8 homes,
10 edges) - recompute_decision_summary --check. R5 cross-family review of ALL FIVE D-2980 files: APPROVE (the
review owed last turn was discharged: OMLX WAS listening on :11435 - the earlier "server down" reading came from
probing the wrong port; the deterministic layers report C11/C12 PASS and a PRE-EXISTING lint I001).
RED (pre-existing, filed): BUG-754 - check_config_defaults --check rc=1 (241 measured against a shrink-only
ceiling of 229).
OWED/UNVERIFIED: the FULL suite rail did not complete inside this session window (two of this session's own
background runs contended for the machine). The focused subset that covers this change -
test_decision_summary_sync, test_handoff_obligation, test_retrieval_serving_spec - passes 19/19. First act of the
next session: run python3 scripts/check_tests.py --check (last full-suite GREEN measured today: 457 collected /
452 passed / 0 declared red).

## NEW / CLOSED REGISTER ITEMS

BUG-756 CLOSED (the restatement has a tracked writer, in the ladder) - BUG-757 FILED (125 open headings without a
severity token; a NEW heading without one is now REFUSED) - D-2981 MINTED (1109 decisions). Prior art assessed for
the owner: pbakaus/impeccable and shadcn-ui/lint are frontend/design-system tools and are NOT adoptable here (no UI
surface); two mechanisms are borrowed into specs/README.md (a bounded set of deterministic detectors with the LLM
strictly advisory; diagnostics that name the DERIVED remedy) and logged in NOT-YET-EVALUATED-RESEARCH.md.
