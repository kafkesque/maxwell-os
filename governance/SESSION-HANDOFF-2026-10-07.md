# SESSION HANDOFF — 2026-10-07 (D-2860: commit-frontier gate landed)

> **Resume:** say `continue` — this file + `governance/CONTEXT_INDEX.md` (D-2860 entry) are the entry points.
> The session_resume skill reads this first.

## STATE VERIFIED AT END OF SITTING (measured, not assumed)

- git HEAD **`bb72985`** (`D-2860: commit-frontier gate (anti-circle rail) + governance sync`); porcelain **0** dirty.
- `config/decisions.yaml` **990 records** (D-2860 = last, state **ACTIVE**, owner ratification owed), stamp
  `baf75ed10a9988ca`, `recompute_decision_summary.py --check` clean, source_sha256 `ae262fed97333a92`.
- Bug register **422** (161 open / 261 closed; highest OPEN = BUG-658) — UNCHANGED this sitting (no bug filed).
- Rails GREEN: `check_decision_membership` (0 fault), `check_bug_status` (register = re-derivation),
  `check_commit_frontier --selftest` + `--check` both clean.

## WHAT LANDED THIS SITTING

**`scripts/check_commit_frontier.py` + `config/commit_frontier.yaml`** (wired into `just health`) — the missing
anti-circle rail. Fails closed (rc=1) when (a) any governance-critical file is dirty, or (b) a
RATIFIED/ACTIVE/RESOLVED decision exists in the worktree but not HEAD. Demonstrated: RED before commit
(`D-2860 (ACTIVE) … NOT committed to HEAD`), GREEN after. This closes the 2-week-circle root cause (34 decisions
sat uncommitted because NOTHING compared worktree-accepted vs HEAD-committed).

## GROUNDED RECOMMENDATION (the answer to "stop going in circles")

Maxwell OS already has ~80% of the requested auto-registration/conflict system (`scripts/reconcile.py` declarative
engine + `derivations.yaml` + `decisions_policy.yaml` + `write_guard.py` + 4 pre-commit rails + 76 guardrail
scripts). Four gaps remain, in consequence order:

1. ~~Commit-frontier gate~~ — **DONE (D-2860).**
2. **Cross-entity correlation is data, not validated** — `decisions.yaml` carries `bugs`(176)/`supersedes`/`superseded_by`/
   `related` but no rail verifies they resolve, are acyclic, or propagate state.
3. **Bugs + tasks are Markdown-first** (`buglog.md`→`bug_status.json` parser-derived; task register has no
   structured store) → blocks auto-register/correlate/update.
4. **`decisions.yaml` is free-form** (34 heterogeneous keys, no enforced schema).

**Safety boundary (non-negotiable):** STRUCTURAL conflict (dangling id, supersession cycle, missing bug ref,
stale derived file) = automate. SEMANTIC conflict ("does D-A *mean* the opposite of D-B") = keep human-gated —
BUG-053 (Phi hallucination) + DELEGATE-002 (Qwen collapse) prove local LLMs can't be trusted for it.

**Peer-reviewed precedents to adapt:** SHACL (W3C, already `taxonomy_shacl.ttl` unenforced), PROV-O/PROV-DM,
Pydantic v2 / JSON Schema, Datomic/Datalog (supersession + acyclicity), Bazel/Nix derivation tracking (already used).

## NEXT CRITICAL STEPS (in consequence order)

- **OWNER-GATE (unchanged, do NOT cross unilaterally):** confirm referee =
  `governance/discipline_anchor_rederived_v6_20261006d.json` + approve 28-row `research & methodology → research practice`
  remap → then finish D-2853 (shacl.ttl line 39 + ~19 config refs).
- **D-2860 ratification:** flip ACTIVE→RATIFIED (or say "warn-only") after owner reads.
- **Phase 2 [D-2861]:** canonical `config/bugs.yaml` + `config/tasks.yaml`, render MD as DERIVED (re-derive+byte-compare, C13 backup first).
- **Phase 3 [D-2862]:** cross-entity invariants as new `reconciliation.yaml` entries + 2-3 check kinds in `reconcile.py`
  (decision.bugs ⊆ buglog; supersedes acyclic + target SUPERSEDED; bug resolved_by D-x ⇒ bug CLOSED; task.implements/fixes ref-integrity).
- **Phase 4 [D-2863]:** enforce decisions.yaml shape via Pydantic/JSON Schema (C12 config-first).
- **Still-open pipeline work (from D-2859):** menu 65/44 vs taxonomy 64/43 off-by-one; D-2857 split; D-2858
  recalibrate+flip; new A/B (adopt iff kappa ≥ 0.800); golden coverage for business-administration + entrepreneurship-studies.

## GOV DEPENDENCIES SYNCED THIS SITTING

`config/decisions.yaml` (D-2860) · `config/decisions_summary.json` (census 990) · `DECISION-LOG.md` (D-2860 entry) ·
`governance/CONTEXT_INDEX.md` (D-2860 entry) · `MASTER-TASK-REGISTER.md` (990 decisions) · `agent/session_seed.yaml`
(decisions 990) · `governance/MUTATION_JOURNAL.jsonl` (census receipt) · `justfile` (health line) · this handoff.
