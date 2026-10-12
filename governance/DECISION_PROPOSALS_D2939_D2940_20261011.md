# DECISION PROPOSALS — D-2939, D-2940 (text only; NOT minted)
generated 20261011T203828Z by agent/session_20261011_golden_anchor
Minting is blocked by `scripts/check_commit_frontier.py` (D-2860 rail is FATAL on the
uncommitted ratified backlog). Mint these in the same pass as D-2933/34/35 and D-2936/37/38.

## D-2939 — Golden anchors separate the LABEL (owner-owned) from the POINTER (mechanical)
**State:** PROPOSED (implementation landed, reversible, non-destructive).
**Context:** BUG-710. `config/golden/retrieval_queries.yaml` pinned `expected` fb_ids; fb_id is
a content hash of the verified input (D-2898), so a corpus reprocess mints new ids and the
hand-signed golden set rots in one pass — measured 0/30 ids AND 0/30 names re-anchorable after
rechunk-v4, after which the harness reported recall@k = 0.000, a number that measured the
golden set rather than retrieval. D-2898's "no agent auto-mints a golden" was being read as
"the owner must sign content hashes", which is neither possible nor meaningful.
**Decision:** the golden set is `(query, query_type, expected_names)` — the owner approves the
query and the human-readable NAME of the correct answer. `expected` (ids) remains as a legacy
fallback and as a resolved snapshot. `pipeline/golden.py` resolves names -> fb_ids in the
serving scope per run.
**Rails:** a name resolving to 0 PASS rows -> UNRESOLVED (reported); to >1 row -> AMBIGUOUS
(refused, never guessed); a query with no resolvable anchor is EXCLUDED from the denominator
and the exclusion is printed. Config: `serving.golden_anchor_mode: name_then_id`.
**Why future-proof:** the owner's signature is valid across reprocesses; drift becomes visible
as an UNRESOLVED line instead of as a silent recall collapse.
**Blast radius:** read-only resolver + benchmark loader path. No store write. No migration.

## D-2940 — Two-slice retrieval measurement: a label-free regression rail + the owner-signed semantic slice
**State:** PROPOSED (implementation landed).
**Context:** the semantic slice cannot be re-signed on every reprocess (D-2939 fixes that), and
for months no measurement existed at all. Meanwhile nothing guarded the index against silent
regression.
**Decision:** (a) the SEMANTIC slice = the owner-approved abstract queries (quality claims may
only be made here); (b) the LABEL-FREE slice = `retrieval_benchmark.py --self-retrieval`, which
queries each sampled FB by its own NAME. Because no label is minted, (b) crosses no owner gate
(D-2898 governs LABELS) and is always runnable.
**Constraint (anti-slope):** a name query is lexical, so FTS/hybrid are flattered by
construction; (b) is a regression rail and MUST NOT be quoted as retrieval quality for abstract
queries. Legs, sample size and sample order are config-owned (`retrieval_benchmark.self_retrieval`).
**Measured today (n=30, k=10):** fts 1.000 · vector 0.767 · vector+rerank 0.800 · hybrid 0.900
· hybrid+rerank 0.867 (recall), MRR 1.000/0.617/0.646/0.770/0.677.
**Blast radius:** additive CLI flag + a new read-only sample query.


## D-2941 — Owner gates carry INTENT and POLICY only; derived data is applied by a verified script
**State:** PROPOSED (this is the anti-loop rule; text only, not minted).
**Diagnosis (measured this session):** every gate in the current backlog asks the owner to sign a
DERIVED quantity — an fb_id (a content hash), a label cell, a candidate rank. The pipeline recomputes
derived quantities, so each reprocess invalidates the previous signature, mints a new gate, and the
sequence re-enters the same argument. Sites: golden anchors (BUG-710 -> BUG-717), status/label
backfills (D-2933/D-2934/D-2935), quarantine cells (BUG-711), the re-anchor table itself.
**Decision:** an owner gate may decide only what a machine cannot derive —
  (1) INTENT: the query set, the target names, the ontology choice, the method choice;
  (2) POLICY: a threshold, a floor, a scope, a vocabulary;
  (3) ADJUDICATION of a genuine tie (two rows share a name; two candidates are equally right).
Everything derived from those must be produced by a deterministic script that: prints its evidence,
refuses incomplete or ambiguous input (C16), takes a C13 backup, is reversible, and writes one audit
line naming the gate, the leg/instrument, and the run it was verified against.
**Corollary (instrument rule):** no metric may be quoted after its instrument has been invalidated.
Every reported number carries (instrument, date, scope). A recall number whose anchor is not in the
serving scope is not a number (already railed: BUG-710 + D-2939).
**Why future-proof:** the owner's signature becomes valid across reprocesses, so the same gate cannot
re-open; and drift shows up as an UNRESOLVED/REFUSED line instead of as a silent zero.
**Blast radius:** none by itself — it re-scopes existing gates. Applied to the golden path this pass.

