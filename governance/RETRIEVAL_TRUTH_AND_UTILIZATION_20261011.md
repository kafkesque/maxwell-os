# RETRIEVAL TRUTH AUDIT — why the 6,500 principles "cannot be recalled", and what principles are FOR
**Date:** 2026-10-11 · **Scope:** served corpus (canonical run `rechunk-v4-20260929`) · **Authority:** D-2881 (run pin), D2511 (benchmark), D-2724 (production method), C16, R-D410
**Verdict up front:** retrieval is *not* broken. The measuring instrument was anchored to a run that is no longer served. Two real defects sit underneath: the superseded run is still physically indexed (scope is enforced by a WHERE clause, not by the index), and 37.6% of the served PASS rows carry unverified NLI confidence yet still rank at the top.

---

## §1 — "Why are you still using the old t11?"

**Serving does not use t11.** `pipeline/retrieve.py` pins *every* leg — `search_keyword`, `search_fts`, `search_vector`, `search_hybrid`, `graph_expand`, `agentic_search` — with `canonical_run_clause()` (D-2881): `AND f.pipeline_run_id = ?` bound to `CANONICAL_RUN` = **`rechunk-v4-20260929`**. Verified live on 2026-10-11: the production path returns **0 t11 rows**.

t11 is nevertheless still present in **three** places, and that is what made it look like it was in use:

| Where t11 still lives | Size | Served? | Effect |
|---|---|---|---|
| `fbs` rows | 7,855 of 14,574 (54.0%) | no (run-pinned) | inflates every census; the "14,574 FB" figure is **2.2×** the served corpus |
| `vec_fbs` entries | 7,855 of 14,574 (53.9%) | no — but they occupy KNN slots *before* the pin is applied | candidate-pool dilution (§2.3) |
| `config/golden/retrieval_queries.yaml` | **30 of 30** expected ids | yes — this file *is* the instrument | recall@k 0.000 for every leg (§2.1) |

Rows for other dead runs: `e2e` 122, `bug198_reinject` 6. Total dead weight **7,983 / 14,574 = 54.8%**.

---

## §2 — Why retrieval cannot recall them

### 2.1 The goldens are structurally unreturnable (primary cause)
Every expected id in the golden set belongs to the t11 run (`run=t11`), while serving is pinned to `rechunk-v4-20260929`. Measured: **0 / 30** expected ids live in the served run, and **2 of the 30 are QUARANTINE even in t11** (`cd98caf61c6ab956` SRE Principles, `1939bc62db425c8d` Collaborative Knowledge Construction) — they could never be returned by a PASS-filtered serving path under any run.

### 2.2 It is not a name-recovery problem either
fb_id is a content hash, so a reprocess cannot preserve it — but name-based re-anchoring also fails: **0 / 30 golden NAMES exist in the served run**. The reprocess produced different convergences, so the answer *objects* are not the same objects. The golden set therefore cannot be repaired mechanically; it must be **semantically re-signed by the owner** (§7, `scripts/reanchor_retrieval_goldens.py`).

### 2.3 Index dilution (real, measured, secondary)
sqlite-vec computes the KNN **before** the run/status filter, so superseded rows consume candidate slots:

| query | vec_fbs top-100 composition | survives run-pin + PASS |
|---|---|---|
| how do organizations recover from a major crisis | t11/PASS 31 · t11/QUAR 29 · canonical/PASS 26 · canonical/QUAR 13 · e2e 1 | **26 / 100** |
| why do feedback loops stabilize a system | t11/PASS 35 · t11/QUAR 26 · canonical/PASS 20 · canonical/QUAR 16 · e2e 3 | **20 / 100** |
| how does retrieval augmented generation keep answers coherent | t11/PASS 45 · t11/QUAR 22 · canonical/PASS 19 · canonical/QUAR 8 · e2e 6 | **19 / 100** |

Honest A/B (20 served PASS rows, query = name, no run filter): k=100 → hit@10 **17/20**, hit-anywhere 18/20; k=1000 → hit@10 **17/20**, hit-anywhere 19/20. So the dilution is a **4× smaller effective pool and +1 recoverable rank on hard rows — not a measured hit@10 loss on easy prose queries**. It is a latent risk and an honesty problem (54% of the index is dead), not the cause of the 0.000.

### 2.4 The served corpus is half-unverified and the ranking ignores that
Canonical run, PASS rows (4,503): `confidence_score` → **≥0.9: 2,025 · 0.8–0.9: 772 · 0.5–0.8: 11 · <0.5: 1,695 (37.6%)**. `source_diversity` → sd1: 3,565 (79.2%) · sd2–4: 693 · sd5+: 245; convergent PASS: 938 (20.8%).
Because `ranking.quality_score_enabled: false`, `_rank_sql()` returns `ORDER BY borp_score DESC` — and `borp_score` is ≈0.0 for every row, i.e. **a constant ORDER BY**, so low-confidence rows compete at rank 1–2. Observed live: `Load-shedding Mechanism` (conf **0.25**) at rank 2, `Failure Definition As Problem Finding` (conf **0.25**) at **rank 1**, `Principle Consistency Over Time` (conf 0.25) at rank 2.

### 2.5 The harness does not measure the shipped path
`retrieval_benchmark.py` benches `fts` / `vector` / `hybrid(RRF)`. Production is `retrieval.method: vector` **with `rerank.enabled: true`** (D-2724 = `vector+rerank`). The A/B legs and the production path are different pipelines, so the harness cannot certify the thing it ships. (Production path tested directly: 6/6 name-paraphrase probes land in the top-3.)

---

## §3 — The 14,574 vs 6,591 counting error (your point, confirmed)

Every "across the corpus" number I reported was computed DB-wide and therefore counted the retired run:

| metric | DB-wide (wrong) | served run (truth) |
|---|---|---|
| rows | 14,574 | **6,591** |
| PASS / QUARANTINE | 9,522 / 5,052 | **4,503 / 2,088** |
| content_type | principle 14,560 · tool_instruction 14 | **principle 6,577 · tool_instruction 14** |
| runs present | 4 | 1 |

The **content_type collapse (BUG-712) is real but its magnitude changes**: on the served run it is 6,577 principle / 14 tool_instruction / 0 process_template / 0 process_instance / 0 growth_edge. The 14 tool_instruction rows are *already* in the canonical run — they are not t11 residue.

---

## §4 — Can retrieval recall NON-principle content? (tested)

Yes — with two structural caveats.

* **Positive control:** the 3 PASS `tool_instruction` rows are recalled by all three legs (`Chat Completions Request Pattern`, `Adapter Pattern for Square Peg…`, `Protein-disease Association Query Pattern` → fts ✓ vec ✓ hybrid ✓). Non-principle retrieval is mechanically fine.
* **Caveat 1 — quarantine:** the other 11 of 14 are QUARANTINE and are unreachable by design (`include_quarantine=False`). "Cannot find it" and "refuses to serve it" look identical to a caller.
* **Caveat 2 — nothing to retrieve:** `process_template`, `process_instance`, `growth_edge` = **0 rows** in the served run. That is not a retrieval failure; the primitives do not exist. BUG-712 is upstream of retrieval.
* **New ontological defect (BUG-714):** those 14 rows are *code/API snippets lifted from books* (`Flask Methodview Endpoint Pattern`, `Redis Stream Task Queue Pattern`, `Triangle Depth Calculation`). `content_type='tool_instruction'` is being used for "a code excerpt", not "an instruction for how an agent should use a tool". The one primitive that *could* feed the agent harness is populated with material that means something else.

---

## §5 — What principles are FOR in Maxwell OS (exactly)

Probe: the served corpus through the **production** path (`search()` → vector + cross-encoder rerank), 6 Maxwell-OS surfaces:

| Maxwell OS surface | probe | returned principle (served run) |
|---|---|---|
| pipeline reliability / fail-fast | "keep an automated pipeline from silently failing" | `Conditional Edge Fail-fast Safety Pattern` (software eng, sd2, conf 0.93) · `Proactive Maintenance Overcomes Degradation` (systems eng, sd2, conf 0.80) · `Load-shedding Mechanism` (conf 0.25 — should be demoted) |
| agent harness / context budget | "give an agent enough context without overwhelming it" | `Multi-step Agent Planning and Execution` (AI, **sd42**, conf 0.96) · `Tool-driven Agent Execution` (AI, **sd32**, conf 0.93) · `Optimal Table Information Density` (info sci, sd2) |
| skill / work orchestration | "keep many parallel workers from drifting off task" | `Strategic Work Optimization` (OR, **sd38**, conf 0.96) · `Three-focus Rule` · `Layered Information Hierarchy Framework` |
| ontology / classification stability | "why categories drift and how to keep them stable" | `Categorization Pathology in Human Judgment` (cognitive sci, conf 0.87) · `Principle Consistency Over Time` · `Statistical Drift Detection in Continuous…` |
| verification gates (R5) | "why two independent reviewers catch what one misses" | weak — `Mistake Recognition Bias` (sd2, conf 0.93) is the only defensible hit |
| everyday scaffolding | "a daily routine that compounds small gains" | `Extra Effort Acceleration Principle` (conf 0.93) · `Sweet Spot Discovery Method` |

**Concretely, principles are usable for exactly five things — all of them internal, none of them decorative:**
1. **Agent-harness behaviour** — inject `Multi-step Agent Planning`, `Tool-driven Agent Execution`, `Optimal Table Information Density` into delegate/recipe context so orchestration decisions are sourced, not improvised.
2. **Pipeline design rules** — `Conditional Edge Fail-fast Safety Pattern` + `Proactive Maintenance Overcomes Degradation` are the corpus' own statement of C16/C23 (fail loud, degrade good): usable as the *rationale* attached to stage contracts.
3. **Ontology discipline** — `Categorization Pathology in Human Judgment` + `Principle Consistency Over Time` + `Statistical Drift Detection` are directly actionable guards for S4 (they name the failure modes the taxonomy guards already fight, e.g. BUG-711/BUG-712).
4. **Retrieval/ranking policy** — the corpus' principles about information density and learning curves are the *grounded source* for tie-break policy; today that policy is a dead `borp_score` constant (§2.4).
5. **Scaffolding** — `Extra Effort Acceleration Principle`/`Sweet Spot Discovery Method` back the session-seed/bootstrap design.

**What blocks utilization today:** the corpus expresses these as *principles* (content_type=principle) — declarative claims — while every adoption path above needs an **executable** primitive (`process_template` for pipeline/skill steps, a correctly-scoped `tool_instruction` for the harness). Those are the two primitives that are 0 and mis-populated. So the utilization blocker is **BUG-712 + BUG-714**, not retrieval.

---

## §6 — Forensic cascade audit of the t11 exclusion (this is where it got interesting)

Checked before proposing any deletion:

* **0 id collisions** — t11 ∩ canonical fb_ids = **0** (fb_id is a content hash; the reprocess cannot reproduce it).
* **0 dangling graph edges** — canonical rows referencing t11 in `prerequisite_fbs` / `related_fbs` / `contradicts_fbs` / `source_principle_ids` = **0 / 0 / 0 / 0**.
* **FTS hazard** — `fbs_fts` is an EXTERNAL-CONTENT fts5 table with **only an AFTER INSERT trigger**; deleting `fbs` rows leaves stale index entries until `INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild')`. Any purge must do that **inside the same transaction** (implemented).
* **Latent defect found** — `vec_fbs_ctx` is **EMPTY (0 rows)**. The S1 contextual index does not exist, so every `--contextual` A/B leg is inert.
* 🚩 **BLOCKER — hard-deleting t11 is NOT safe yet:** t11 is not a coverage duplicate. Against the 939 corpus `.md` files: **t11 uniquely covers 232 files; the canonical run uniquely covers 33.** t11 is a superseded *method* over a *partially reprocessed corpus*, so a hard purge would silently destroy the only committed extraction for ~25% of the corpus (≈232 books). The "exclude t11" ruling is correct for **serving and counting** and *not yet* correct for **deletion**.
* Census/taxonomy dependencies (`taxonomy_counts`, `governance/bug_status.json`, parquet exports) must be re-derived after any row removal.

**Therefore the exclusion is two-phase:**
* **Phase 1 (safe now, reversible):** scope enforcement — remove superseded runs from the **vector index only** (`--index-only`). Knowledge rows survive; the vectors are a deterministic derived artefact rebuildable by `pipeline/backfill_embeddings.py`; the KNN pool stops being diluted.
* **Phase 2 (after the 232 files are reprocessed into the canonical run):** archive → delete → FTS rebuild → verify.

### 6.1 End-to-end verification on a store copy (both modes)
`scripts/purge_superseded_runs.py` was exercised on two throwaway copies of the live store (the live store was **not** touched):

| mode | fbs before → after | vec deleted | fbs_fts | integrity | residual | FTS parity | live smoke test |
|---|---|---|---|---|---|---|---|
| full purge | 14,574 → **6,591** | 7,983 | rebuilt | ok | 0 | ✅ 6,591 == 6,591 | 10 hits, 0 purged runs leaked |
| `--index-only` | 14,574 → **14,574** (untouched) | 7,983 | untouched | ok | 7,983 (by design) | ✅ | 10 hits, 0 purged runs leaked |

Archive: 7,983 rows, `sha256 1f5ba4b1cddc79f4…` (written before any deletion). This also **empirically refutes** an R5 nit that the FTS rebuild is missing — it runs inside the same transaction, and FTS parity is asserted post-apply.

### 6.2 What Phase 1 buys, measured
vec_fbs top-100 composition for the same three queries, before → after index scoping:

| query | survivors (run-pin + PASS) | after index scoping |
|---|---|---|
| how do organizations recover from a major crisis | 26 / 100 | **75 / 100** (all canonical; 25 QUAR = correct) |
| why do feedback loops stabilize a system | 20 / 100 | **58 / 100** |
| how does retrieval augmented generation keep answers coherent | 19 / 100 | **60 / 100** |

**2.6–3.9× more usable candidates**, with the remaining QUARANTINE share being a legitimate server-side policy decision rather than dead slots from a retired run.

---

## §7 — Implemented this turn

| artifact | what it does | state |
|---|---|---|
| `config/pipeline_config.yaml` → `serving:` block | `index_scope: canonical_run`, `superseded_runs: [t11, e2e, bug198_reinject]`, `require_resolvable_goldens: true` (C12 — no hardcoded run list) | live |
| `scripts/purge_superseded_runs.py` | archive-first exclusion: inventory → 0-inbound-ref precondition → C13 backup → archive JSONL+sha256 → one transaction (vec0 ×2, fbs, FTS rebuild) → post-verify (residual/integrity/orphans/FTS parity/live smoke test). Dry-run default; `--index-only` for the reversible half. Dry-run: **7,983 rows (54.8%), 0 inbound refs, refs clean**. Both modes verified end-to-end on store copies (§6.1) | verified (e2e) |
| `pipeline/retrieval_benchmark.py` → `_resolvability()` + gate | BUG-710 fix: the harness now REFUSES (exit 2) to print recall when any golden is unreturnable, naming run/status/name per id, unless `--allow-unresolvable` / `--serving-scope all_runs` | live — now prints `measurable goldens: 0/30` instead of `0.000 recall` |
| `scripts/reanchor_retrieval_goldens.py` | runs each golden query through the served path, emits 150 candidate rows (CSV, owner signature column) + a PROPOSED golden YAML. Never edits the live golden set (D-2898) | dry-run verified |
| `governance/golden_reanchor_candidates_20261011.csv` / `…proposed_20261011.yaml` | the owner-review artifacts | awaiting signature |

R5 independent verification of the two code changes: delegate `20261011_12` (gemma-4-E4B, cross-family).

---

## §8 — Next critical steps, in consequential order

| # | step | blocked by | class |
|---|---|---|---|
| 1 | Owner signs the 30-row golden candidate table → replace `config/golden/retrieval_queries.yaml` → the harness reports a **real** recall@k baseline | owner signature only | decision |
| 2 | Apply `scripts/purge_superseded_runs.py --index-only --apply --confirm t11,e2e,bug198_reinject` (reversible; de-dilutes KNN by 54%) | nothing (owner may veto) | task (D-2936) |
| 3 | **BUG-712 root-cause: why S4 emits 0 process_template / 0 process_instance / 0 growth_edge** — highest mission value (it is the utilization blocker, §5) | nothing | bug |
| 4 | **BUG-714: retype the 14 mislabelled `tool_instruction` rows** (code snippets ≠ tool instructions) and decide the real `tool_instruction` contract for the agent harness | owner on the contract | bug/decision |
| 5 | **BUG-713: purge Phase 2** — reprocess the 232 t11-unique corpus files into the canonical run, then archive+delete t11 | Phase 2 backfill | bug/task |
| 6 | Add the **production path** (`vector+rerank`) as a leg in `retrieval_benchmark.py` so the harness measures what ships (§2.5) | #1 | task |
| 7 | Enable `ranking.quality_score_enabled` (D2537) and A/B against the re-anchored goldens — demotes the 1,695 conf<0.5 PASS rows (§2.4) | #1 (needs a live instrument) | task |
| 8 | Register the future-proof index design: **vec0 `partition key` on `pipeline_run_id`** so scope filtering happens inside the KNN — no dilution, no deletion, multi-run queryable | decision mint (rail) | decision |
| 9 | `vec_fbs_ctx` is empty — rebuild or retire the S1 contextual leg (§6) | nothing | task |
| 10 | Owner commits the ratified governance backlog (D-2900…D-2932) so `check_commit_frontier.py` clears | owner commit | decision |

---

## §9 — Decisions to mint (blocked by the D-2860 commit-frontier rail)

* **D-2936 — Serving index scope.** Scope MUST be enforced by the index, not only by a WHERE clause. `serving.index_scope: canonical_run`; target implementation = vec0 **partition key on `pipeline_run_id`** so the filter is applied inside KNN. Interim: index-only scoping. *Basis:* §2.3 (19–26/100 survivors), §6.
* **D-2937 — Superseded-run exclusion policy.** Archive-first (R-D410), dry-run default, C13 backup, 0-inbound-ref precondition, FTS rebuild inside the transaction, and a **coverage-gap guard**: a run may not be hard-deleted while it uniquely covers corpus files the canonical run has not reprocessed (232 files today). *Basis:* §6.
* **D-2938 — Golden sets are run-bound artifacts.** A retrieval golden set must declare the `pipeline_run_id` it was verified against; a harness must fail loud when its goldens fall outside `serving.index_scope` (C16). Re-anchoring is a semantic, owner-signed act (D-2898), never an id rewrite. *Basis:* §2.1–2.2, §7.

**Not minted** — `scripts/check_commit_frontier.py` is still FATAL on the uncommitted ratified backlog (same rail that blocked D-2933/2934/2935).

---

## §10 — BUG-712 ROOT CAUSE FOUND (content_type routing collapse): the corrected role is computed and then discarded

**Symptom:** served run has 0 `process_template`, 0 `process_instance`, 0 `growth_edge` over 6,591 rows.

**Determination (deterministic, no model calls).** The convergent S2 path is *instructed* to emit `"principle"` — `pipeline/stage2_extract.py:414` item 9: *"this CONVERGENT path synthesizes Foundation Blocks, so emit \"principle\" … The non-principle roles (process_template / process_instance / growth_edge / tool_instruction) are classified by the SINGLE-SOURCE / singleton paths, not here."* That alone would explain a collapse, but it is **not** the root cause, because a deterministic corrector exists: `reroute_content_type` (D-2747) → `_principle_form_violation` (D-275b), pure regex, no LLM (D-343 forbids LLM-classified content_type).

**Replaying that corrector over the served run:**

| `reroute_content_type` output on the 6,591 canonical rows | count |
|---|---|
| principle (unchanged) | 6,490 |
| **growth_edge** (`_OPEN_TENSION` fired) | **100** |
| **process_template** (`_PROCEDURE_STEPS` + `_DONE_CONDITION` fired) | **1** |
| quarantine (`_DEFINITIONAL_START` without prescriptive language) | 1 |
| **rows whose stored role is wrong** | **115** |

The store contains **0 growth_edge and 0 process_template** — i.e. the corrected role is never persisted.

**The defect is one line.** `pipeline/stage4_merge.py`:

* line **2325** computes the corrected role and uses it *only* for the applicability axis:
  `_applicability_val, _applicability_source = derive_applicability(fb_data, _resolve_content_type(fb_data))`
* line **2352** persists the **raw** S2 value instead:
  `"content_type": (fb_data.get("content_type") or DEFAULT_CONTENT_TYPE).strip()`

So D-2747/D-275b correction is evaluated and thrown away on the convergent path. It is a **wiring bug, not a classifier-capability gap** — the pipeline already knows, deterministically, that 100 of its rows are growth edges and 1 is a process template.

**Why I did not apply the one-line fix in this turn (and why nobody should, unreviewed):** `content_type` is an **S4-owned ontology column** (D-2933: S6 and any agent must not rewrite S4 ontology), and the raw value feeds other decisions in the same module (per-cluster splitting at :1806, the `== DEFAULT_CONTENT_TYPE` checks at :1486/:1730, applicability derivation, and the Layer-2 FB→PT→PI→Recipe chain). Changing the writer without re-running/re-validating those consumers would be exactly the "silent cascade" class this review exists to prevent. Correct route: owner-ratified change + a governed re-stamp or an S2→S6 re-run, then re-measure.

**Calibration note (separate, smaller):** 937 served rows contain procedure-signal vocabulary (`step N|workflow|procedure|checklist|template|process`) but only 1 satisfies the PT detector's `_PROCEDURE_STEPS` **+** `_DONE_CONDITION` conjunction. The 100-row growth_edge leak is a wiring bug; the PT detector's conservatism is a separate calibration question that should be answered after the wiring is fixed, not together with it.



---

## §11 EXECUTED 2026-10-11 21:35–22:25 (post-audit actions)

| # | Action | State | Evidence |
|---|---|---|---|
| 1 | t11 + e2e + bug198_reinject excluded from the **KNN index** | ✅ APPLIED | 7,983 vectors deleted; integrity ok; orphans 0; smoke leaked_runs=[] |
| 2 | Backup (C13) + archive before delete (R-D410) | ✅ | backup sha256 9777da1413a713a7…; archive 7,983 rows sha256 1f5ba4b1cddc79f4… |
| 3 | Full row-deleting purge | ⏸ DEFERRED | preserves the old-id evidence the owner needs to sign the golden re-anchor |
| 4 | BUG-712 producer fix (persist resolved content_type) | ✅ APPLIED (code) | `stage4.persist_resolved_content_type: true`; counter in run summary; next run only |
| 5 | Retro re-stamp of the 6,591 rows | ⏸ OWNER-GATED | S4-owned ontology (D-2933); 102–115 rows would change role |
| 6 | purge verifier made mode-correct | ✅ FIXED (BUG-716) | index-only guard proven `bad=False` on the live store |
| 7 | Layer-2 sidecar truthfulness rail | ✅ NEW | `scripts/audit_sidecar_commit.py` — exit 2 on any unexplained drop |
| 8 | BUG-715 registered (7-record unexplained drop) | ✅ | rail output above |

## §12 CORRECTIONS TO THIS REPORT

1. **"232 t11-unique files / 25% of the corpus" was WRONG** (filename-normalisation artefact).
   Correct: 224 exact set-difference → 129 name variants → **95 distinct**, of which **86 are covered by
   the canonical run** and **9 remain unresolved** (8 junk/variant + 1 file not re-chunked). The t11
   hold-back rationale is therefore **evidence preservation for the golden re-anchor**, not coverage
   protection. §6's "🚩 BLOCKER" is DOWNGRADED to a sequencing note.
2. **The non-principle recall question is now answered with the artifact seam**: PT 774 / PI 156 / GE 27
   extracted at S2, routed by S4 into sidecars, **0 committed**; TI 109 → 14 committed + 95 sidecar.
   Retrieval cannot recall what was never committed — and this is decision **D2590's** open scoped-S6
   build, not a retrieval defect.
3. **Non-principle retrieval contract is already RATIFIED**: D-2922/D-2923 (`research/LAYER2_RETRIEVAL_
   CONTRACT_20261011.md`) — principle = discipline/domain/depth/status keyed; PT/PI/GE/TI = intent+linkage
   keyed, NEVER discipline/domain; `content_type` must become a FIRST-CLASS FACET in `retrieve.py`
   (today there is no content_type facet at all). The 3 indistinguishable TI "hits" observed earlier are
   accidental (the vector is of `definition`, not of `description`).

---

## §13 CORRECTIONS AND MEASUREMENTS 2026-10-11 22:27 (GOLDEN-ANCHOR PASS — supersedes §6's owner action)

**13.1 The 150-row re-anchor table must NOT be signed (BUG-717).** It was screened on the
legacy RRF leg while production is vector+rerank (D-2724). One query, two legs, two different
"rank 1": hybrid -> "Golden Goose System Creation", vector -> "Zapatista Power Dispersion
Network", for *how to build resilient distributed systems*. The table has been REGENERATED on
the production leg; row content is now evidence, not a proposal, and every row is judged on
the answer NAME (+ a 220-char definition snippet), never on an fb_id.

**13.2 D-2898 does not require the owner to sign content hashes.** fb_id is a content hash of
the verified input, so it changes on every reprocess — which is why the hand-signed golden set
rotted in one pass (0/30 ids, 0/30 names). The owner gate is on the LABEL (the query + the
answer NAME); the fb_id is a POINTER and is resolved mechanically per run by the new
`pipeline/golden.py`. An unresolved name is reported and EXCLUDED, never scored 0.

**13.3 A label-free slice now exists, so "no baseline" is no longer the only true statement.**
`pipeline/retrieval_benchmark.py --self-retrieval` (query = a served FB's own name) mints no
label and therefore crosses no owner gate. n=30, k=10, run rechunk-v4-20260929:
fts 1.000/1.000 · vector 0.767/0.617 · vector+rerank 0.800/0.646 · hybrid 0.900/0.770 ·
hybrid+rerank 0.867/0.677 (recall@10 / MRR). It is a REGRESSION rail: a name query is lexical,
so it must never be quoted as retrieval quality for abstract questions, and FTS's 1.000 is a
property of the fixture, not a result.

**13.4 The reranker is uncalibrated — a proposed absolute gate was discarded.** Known-positive
pairs score -6.76 against -11.05 for unrelated ones (ordering is real) while the known-positive
distribution spans -6.01..+8.63 (absolute value is not). Any rule of the form "top-1 score < 0
=> the corpus cannot answer this" would have been a fabricated gate. Scores are stored as
evidence only.

**13.5 Non-principle recall remains a COMMIT gap, not a retrieval gap** (§6 unchanged): PT 774,
PI 156, GE 27 extracted and 0 committed; TI 109 -> 14 committed + 95 in sidecar (D2590's
scoped-S6 build is the unblock).

**13.6 R5 review of this pass (delegate, maxwell_omlx/gemma-4-E4B-it, temp 0.0).** I3 (no absolute score gate), I4 (label-free slice writes nothing) and I5 (loud failures) were confirmed. I6 was NOT: the acceptance path was an unguarded `cp` of the draft over the live golden file, so a human could apply an unreviewed artifact. APPLIED: `reanchor_retrieval_goldens.py --apply` is now the only path — it refuses unless every query has exactly one CSV row marked `decision: anchor`, that chosen NAME resolves in the serving scope, and a C13 backup is taken. Queries marked retire/rewrite are dropped on purpose and reported; a query with no verdict fails the apply instead of being guessed.
