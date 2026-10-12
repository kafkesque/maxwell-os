# FORENSIC AUDIT — D2590 scoped-S6 build (pre-implementation)

Date 2026-10-12 (session continues `FORENSIC_AUDIT_20261012.md`). Lens: senior RAG / system /
ontological-knowledge architect. Question: *before committing the D2590 implementation, prove
nothing breaks, cascades, drifts, or hides a failure — and measure the real object being written.*

Instrument note (D-2941 corollary): every number below is quoted with its source. The registry rail
(`scripts/audit_sidecar_commit.py`), the live store, and the S4 sidecar bytes are the three
instruments; no number here is inherited from prose.

## F0. The tree is already stabilized (audit predecessor assumption is STALE)

`FORENSIC_AUDIT_20261012.md` F1 assumed the D-2933..D-2941 implementation was uncommitted. It is
NOT: commit **0e28cff** landed it (145 files) together with the tree stabilization (16 may_touch
grants, 2 hygiene snapshots dropped, `.goose/` ignored). Working tree at audit time: 3 paths —
`M governance/buglog.md` (BUG-713 resolution), `M scripts/definition_nli_verify.py` (owner-owed R2
pin D-2903, **do not commit**), `?? governance/SESSION-HANDOFF-20261012.md`. **F4 item 1 of the
predecessor audit is therefore DONE**; the next unblocked critical step is D2590.

## F1. The D2590 target set, measured (not quoted)

`scripts/audit_sidecar_commit.py --tolerance 7`, run `rechunk-v4-20260929`, rc=0:

| sidecar file | records | content_type inside it |
|---|---|---|
| `process_templates.jsonl` | 817 | process_template **774**, tool_instruction 34, principle 9 |
| `process_instances.jsonl` | 157 | process_instance **156**, tool_instruction 1 |
| `growth_edges.jsonl` | 212 | principle 187, growth_edge **25** |
| `tool_instructions.jsonl` | 59 | tool_instruction **59** |
| `quarantined.jsonl` | 374 | principle 372, growth_edge 1, tool_instruction 1 |
| **total** | **1619** | |

Cross-checks (deterministic, this session):
- **zero** fb_id overlap between any sidecar record and the 6,591 stored rows;
- **zero** duplicate fb_id *across* sidecars;
- therefore every sidecar record is uncommitted and ingestable exactly once.

**F1a (BUG-719) — the "81 TI remaining" figure is arithmetically wrong.** The handoff and today's
audit both wrote `TI 95 extracted − 14 committed = 81 remaining`. The 14 committed `tool_instruction`
rows came from **checkpoint.jsonl** (the S5-verified leg), not from a sidecar; subtracting across two
disjoint populations is a category error. The ingestable TI population is **94** (34 + 1 + 59; the
95th sits in `quarantined.jsonl`). Correct D2590 non-FB ingest set = **774 + 156 + 94 + 25 = 1,049**.

## F2. THE HIDDEN DEPENDENCY (the finding that would have broken the build)

A naive D2590 lands **zero rows and rolls the store back**. `insert_fb` refuses any row the serving
gate cannot derive (`pipeline/serving_gate.py::pre_write_verdict`, `pre_write_enforcement: reject`):

```
store_verdict(None) -> UNDECIDABLE, "no factual check in verification_results and no dedup marker"
```

Non-FB rows have **no verification record** (1,593 of 1,619 carry no `status` at all; 26 carry the
GE *epistemic* status). So all 1,049 rows would be refused → `failed/len(fbs) = 100% >
stage6.max_failed_ratio (0.0)` → **BUG-708 rollback**. The guard is working exactly as designed; the
defect is that D2590's spec never named the disposition of a row whose role carries no NLI claim.

**Ruling (minted as D-2942, assistant-proposed, owner review requested).** S5 verifies **truth
claims**; a process template's steps or a tool's syntax are not truth claims, so an absent record
means **not-applicable**, not *undecidable*. The disposition is:
- **status stays `QUARANTINE`** — no third status value, no `_status_predicate` change, no
  serving-surface change, and the existing contract test
  (`tests/test_retrieval_quarantine_contract.py`) stays true. Blast radius: **zero**;
- the **typed reason** carries the distinction: `s5_not_applicable` (added to the governed
  `reason_vocabulary`, `negative: false`). This is the mechanism the file already declares exists for
  exactly this job ("the vocabulary is persisted so the QUARANTINE split (G9/D272d) becomes a wiring
  job, not modelling");
- **row-deterministic**: the rule reads the row's own `content_type` against a declared config list,
  so the writer (S6) and the rail (`check_serving_gate.py`) derive the same value from the same bytes;
- **never PASS**: promoting unverified rows would manufacture trust and break R5/D2298 fail-closed.

Consequence, stated plainly for the owner: **D2590 makes procedural/episodic knowledge PERSISTENT and
EXPLICITLY retrievable, not default-served.** Serving them by default is a **verification-design**
question (how *is* a tool instruction or a process template verified?) — BUG-714's contract question,
and A1/A3 territory. It is NOT flipped here.

## F3. The `type_body` contract already exists (no new ontology was needed)

`config/content_types.yaml` already declares, per role, `s2_body_fields`:

| content_type | s2_body_fields (declared) | measured presence in the sidecars |
|---|---|---|
| process_template | trigger, prerequisite, steps, done_condition, failure_mode | 774/774 on all five |
| process_instance | instance_text, actors, outcome_metric, outcome_qualitative, domain_context | 156/156 on all five |
| tool_instruction | tool_name, platform, description, syntax, parameters, output, example, caveats | 95/95 on all eight |
| growth_edge | body, category, actionable, status, priority | 26/26 on all five |

So `type_body` = `{f: rec[f] for f in s2_body_fields[ct] if f in rec and f not in core_body}`:
- the field list is **read from the ontology** (C12 / single home) — **no new config, no literal list**;
- `core_body` (name, definition, mechanism, boundary, consequence, elaboration, application,
  failure_mode, jargon) is excluded because those fields **already have first-class columns** — the
  column is their home, a JSON copy would be a second source of truth (bloat + drift);
- the result reproduces D2590's spec field-by-field (PT 4, PI 5, GE 5, TI 8) — independent
  confirmation that the intended contract is the ontology, not a new invention.

**Namespace collision, resolved explicitly.** `growth_edge.status` (open / speculative / conceptual —
an epistemic state of the *tension*) collides by NAME with `fbs.status` (the governed verification
status, S5-owned per D-2933). Resolution: the S5-owned column set is **never** written from a sidecar
row (the gate alone writes it), and the GE status survives **namespaced inside `type_body`**. The
ingestion asserts this (no type_body key may be promoted to a governed column) and the receipt
declares it.

## F4. Blast-radius inventory (what the change touches, and what it must not)

| surface | change | guarded by |
|---|---|---|
| `fbs` schema | +1 nullable TEXT column `type_body` (DDL + `_migrate_add_column`, the existing auto-heal idiom) | additive; all 6,591 rows stay NULL |
| `insert_fb` | +1 column in the INSERT list/values | pre-write verdict unchanged |
| S6 ingestion | NEW, flag-gated by `S6_COMMIT_NON_FB` (**DEAD config until now**) | flag False ⇒ byte-identical to today |
| vector store | each ingested row must embed (`assert_vector_integrity` is a rowid-level contract) | 1,049 local bge-m3 calls, $0 |
| Parquet | snapshot grows by the same rows (`type_body` serialised as JSON text, like other JSON columns) | pyarrow type inference — one type per column |
| `retrieve.py` | `content_type` facet on **every** leg (D273a/G12: a facet not asserted on every generator is not a filter) | additive; default `None` = today's behaviour |
| serving gate | one NEW declared reason + one declared config list; `derive_status`/`store_verdict` gain a keyword arg defaulting to today's path | `tests/test_serving_gate.py` must stay green |
| `audit_sidecar_commit` | declares the residuals so nothing is silent | `--strict` becomes satisfiable |

**Not touched (deliberately):** `related_fbs` asymmetry (A2/BUG-274, step 4), GE calibration stamp
(D-2924, owner), the non-principle cross-ref producer (`consulted_fbs`/`parent_pt_id` — deferred by
D2590 itself), `retrieval.method` (owner-owed).

## F5. Declared residuals after the build (BUG-719 / BUG-720)

1. **196 principle-typed rows sit in the non-principle sidecars** (187 GE + 9 PT). They are excluded
   by `content_type` (they are not non-FB objects) and are NOT committed. They are a **classification
   drift** artifact, not a routing bug — same class as BUG-712 and the D-2916 mislabel triage.
   Declared loudly in the rail + receipt; repair is a separate item.
2. **374 quarantined.jsonl rows** (D2616 disposition) stay uncommitted by design. Declared.
3. **7 unexplained drops** attributed to the D2120 cosine-dedup `valid_ids` gate (predecessor audit
   F2). The rail tolerates them; the future-proof fix is a `deduped_cluster_ids` receipt emitted by
   `stage4_merge.py` — logged as **BUG-720**, not blocking.
4. **14 already-committed `tool_instruction` rows carry `type_body = NULL`** (they predate the
   column). They are the BUG-714 mislabels (code snippets ≠ tool instructions) and are slated for
   retype; back-filling them here would entangle this change with that decision. Declared in the
   receipt with its count, so the gap is visible and attributable, not silent.

## F6. Ordered plan (anti-drift: one change, one cause; verify before applying)

1. mint D-2942/D-2943/D-2944 (registry rail `recompute_decision_summary.py --mint`), log BUG-719/720;
2. serving-gate disposition (config + `serving_gate.py` + rail thread-through) — F2;
3. S6: `type_body` column + `build_type_body` + sidecar loader + flag wiring + receipt — F3;
4. `content_type` facet on all legs — F4;
5. rails: `pre_s6_gate.py` (validate the ingest set), `audit_sidecar_commit.py` (residuals);
6. tests (incl. negative controls), then `pre-s6` → **read-only dry-run** → delegate code review
   (gemma-4-E4B, R5 generator≠verifier) → C13 backup → `--apply`;
7. verify: ingestion counts, `check_serving_gate.py` rail = 0 mismatch, `assert_vector_integrity`,
   `audit_sidecar_commit.py --strict`, a retrieval smoke on `content_type`;
8. governance sync + handoff.

**Owner gates untouched by this build:** R2 pin re-measure (D-2903), BUG-712 restamp, BUG-714
contract, D-2924 GE calibration stamp, independent golden anchors.

---

## OUTCOME (appended 2026-10-12 after the apply — measured, not asserted)

**LANDED.** `just pre-s6` PASSED (including the new check 6) then `python3 pipeline/stage6_commit.py` (C13 backup
`knowledge pipeline/maxwell.db.bak_20261012_115824` taken first):

| measurement | before | after |
|---|---|---|
| rows (ONE run, `rechunk-v4-20260929`) | 6,591 | **7,640** |
| content_type | principle 6,577 / tool_instruction 14 | principle 6,577 / process_template 774 / process_instance 156 / tool_instruction 108 / growth_edge 25 |
| status | PASS 4,503 / QUARANTINE 2,088 | PASS **4,503 (unchanged)** / QUARANTINE 3,137 |
| `s5_reason` | 8 values, no `s5_not_applicable` | + `s5_not_applicable` = **1,049** (the rule's own output) |
| `type_body` | column absent | 1,049 non-NULL; NULL only for the 6,577 principles (no declared body) and the 14 legacy mislabels (declared, BUG-714) |
| vector index | — | 7,640/7,640 rowid-verified (0 gap for the new tier) |
| `check_serving_gate.py` | 6,591 MATCH / 0 mismatch | **7,640 MATCH / 0 mismatch / 0 undecidable** |
| `audit_sidecar_commit.py --strict` | rc=2 (declared types never committed) | **rc=0** |
| `check_tests.py --check` | 326 collected | **344 collected / 339 passed / 0 declared red** |
| `integrity_check.py --quick` | — | **10/10 PASS** (incl. C12 hardcoded paths, C16 silent exceptions) |
| `check_repo_integrity --worktree` / `config_audit` / `check_governance_faces` | — | **rc=0 / no drift / rc=0** |

**Dry run, twice, in a sandboxed store copy** (`temp/dryrun_d2590.py`): pass 1 inserts 1,049; pass 2 inserts
**0** (idempotent, C23); the S6 checkpoint holds 7,640 records on BOTH passes (`{UPDATED: 6,591,
ALREADY_STORED: 1,049}`) — which is how the run-vs-history defect (BUG-722) surfaced and was fixed instead of
being force-flagged past the io_guard shrink guard.

**Retrieval proof (post-apply):** `--content-type process_template --status QUARANTINE` → 4/4 process_templates;
`--content-type principle --status QUARANTINE` → 4/4 principles; `--content-type growth_edge` → 4/4 growth_edges;
the default query (no facet, status=PASS) → principles with `entail` only, i.e. **the served surface is
unchanged**.

**F5 residuals after the build, re-measured:** 196 principle-typed rows sit in the non-principle sidecars and are
excluded by the row's own content_type (BUG-719, and the "81 TI remaining" figure was an arithmetic error — the
sidecar TI population is 94); 374 records remain on the D2616 hold shelf; 7 unattributed S2 records are
attributed to the D2120 `valid_ids` gate (BUG-715 → CLOSED, hardening is BUG-720); 14 legacy
`tool_instruction` rows carry no `type_body` (BUG-714 owns them).

**D-2924 evidence, measured:** **25/25 growth_edge categories in the ingest set are OFF the closed vocabulary**
(`open_tension` / `unverified_correlation` / `contested_claim` / `capability_gap`), so flipping
`growth_edge_ontology.yaml` advisory → enforcing today would reject 100% of the committed GE corpus. Nothing was
normalised at commit time (that is an owner-gated ontology act, D-2898); the counts are in the receipt.

**New defect found by this audit's own verification step:** **BUG-721** — a delegate returned a FABRICATED code
review (it stated it could not read the files, then "simulated" the review and returned a verdict). The apply was
therefore gated on DETERMINISTIC instruments (the exhaustive scoping test, the AST column/placeholder/value
alignment check, the two-pass sandbox dry run, and three live rails), not on a delegate verdict.
