# SESSION HANDOFF — 2026-10-13 · D-2992 (the corpus lifecycle: three times, one head, one vocabulary)

## §1 The leverage call

The owner asked a question that is not a bug and not a task: **what happens to a claim when the world around it
changes** — a later source that corroborates it, a richer text that restates it, a new MEDIUM that carries it, and
a role that evolves. Every one of those has an answer in the tree today, and none of them is the answer the
pipeline thinks it gives. Answering it decides whether the next programme (internet intake) is safe, and it is
the second half of the BORP question the same owner asked one act earlier (D-2990: the principle vs the score).

## §2 What was found (each with its home)

| finding | the home | the consequence |
|---|---|---|
| a row has THREE times and they move independently | `pipeline/schemas.py:175` (`fb_id = SHA-256(name+definition)`), `pipeline/book_metadata.py::compute_source_id`, `pipeline/stage1_5_embed_cluster.py` (`is_convergent` = ≥2 canonical sources in ONE cluster of ONE RUN) | corroboration is a property of the RUN, not of the row |
| the instrument built for the collision cannot see the BORP case | `pipeline/dedup_identity.py` (GROUPING key = `(normalize_name, source_id)` = SAME WORK), `pipeline/dedup_gate.py:211` (`would` = `link_duplicate｜supersede_review｜insert`, `mode: report`) | "a different work asserting the same claim" is invisible to the dedup path |
| the declared rule and the live path disagree | `config/dedup_identity.yaml` → `never_at_commit: true  # D-2933 rule V: a commit may never rewrite an existing row's body` vs `pipeline/stage6_commit.py:764` `INSERT OR REPLACE INTO fbs` (77 columns) | a same-definition re-read REPLACES the prior reading (C6); a one-character definition move FORKS a twin row; `content_basis` is reserved with NO writer, so neither case is visible |
| the intake plan's blocker is identity, not conversion | `pipeline/stage0_convert.py` (`{.epub,.pdf,.md}`), `compute_source_id`'s filename fallback, `config/eval_integrity.yaml` (`max_both_unknown_ratio: 0.0`) + `scripts/verify_source_identity.py` (docstring: 29.1% of convergence was the same book twice) | a transcript/podcast/thread lands on the closed defect class the corpus spent BUG-289/D2176/D-2308 removing |

## §3 What landed

- `governance/CORPUS_LIFECYCLE_20261013.md` — the seven answers, the three-times ontology, the recommendation per
  question with the rejected option, the five axis-drift failure modes and their existing controls, and the
  verified external precedents (PROV-O revision terms; Kimball SCD-2; Fowler event sourcing; NISO RP-8-2008's
  SEVEN article versions; Crossref relation types; Crossmark; COPE; OpenAlex work types).
- `governance/OWNER_LANE_BATCH_20261013.md` — the batch sheet: T-101 `set`, T-107 `retire` + `promote
  corroboration` / `keep-and-repair`, T-118 `tier`, T-117 per cause-group, each with the consequence of the other
  choices and the file the word goes into.
- BUG-772, BUG-773, BUG-774 — filed, none closed (this act fixes the DESIGN GAP, not the code).
- T-120 (the absorption path / derived corroboration) and T-121 (source-kind axis + per-kind identity +
  re-publication collapse).
- D-2992 — the ruling (`governance/decisions_mint_D2992.yaml`).

## §4 Forensic audit (before committing)

- **No store write, no payload change, no export change, no axis label moved, no golden applied.** The act is
  documentation + register rows + two task rows.
- **No silent normalisation**: the one typographic error in this act's own draft (a malformed transliteration in
  the OpenAlex type list) was corrected in place and the correction is recorded here rather than hidden.
- **Citations verified before use** (D-2660): one delegate, read-only, 23 turns, 7 claims, 5m. It returned THREE
  corrections, all KEPT: `isRetractedBy` is NOT a Crossref relation type (retraction is Crossmark update
  metadata); NISO RP-8-2008 JAV defines SEVEN version terms, not four/five; and PROV-O states exactly THREE
  subproperties of `prov:wasDerivedFrom` (`wasQuotedFrom`, `wasRevisionOf`, `hadPrimarySource`) — not all five
  terms as first drafted. A citation that is smoothed over is a claim nobody can audit.
- **Cascade check**: the new bug ids (772–774) and task ids (T-120, T-121) were taken from the census's own next
  free values; `governance/bug_status.json` was re-derived BEFORE gov_sync so the faces cannot cite a stale
  census; every file this act cites existed at the moment of mint.
- **Bloat check**: two new governance documents, both answering asked questions; no new module, no new rail, no
  new config key. The recommendations that DO need machinery (T-120, T-121) are filed as tasks, not smuggled in.

## §5 Delegation

One read-only delegate (`20261013_6`) for the EXTERNAL claim set only. No repository write, no design work, no
local-LLM generation was delegated — the design is a judgment about this tree and is not delegable (D-2898).

## §6 Residuals (declared, not hidden)

1. `is_convergent` is still an INPUT until T-120 lands.
2. `content_basis` still has no writer (BUG-773 open).
3. The source-kind axis does not exist; no non-book source has been ingested (BUG-774 is preventive).
4. T-101 is still blocked on one word (`set｜single`); the golden set is unchanged.
5. `isor` is still advertised by nothing (T-107's surface change is still owed).
6. The bug axis still cannot be ordered by severity (T-104/BUG-757).

## §7 Next critical step

**Pipeline lane:** T-104/BUG-757 — the severity backfill (it is what makes "highest leverage" answerable for
everything above), then T-120 step 0 (locate the S1 segment store; read-only), then BUG-771's stale-premise stamp.
**Owner lane:** the four words in `governance/OWNER_LANE_BATCH_20261013.md`.
