# BORP + `feedback_score` — the archaeology, the measurement, and the senior-engineer recommendation

**Date:** 2026-10-13 · **Authority:** this is the EVIDENCE for T-107; the RULE is `config/served_fields.yaml`
**Owner question (verbatim):** *"what were the original concept behind BORP and lead for drop besides there are no
current infrastructure/logic behind it? DON'T drop till I don't clear explanation and if it can be revitalized with
real scoring logic and feedback score keep how will exactly works and how will it be scored how will the logic will
look like gave an stier senior system engineer recommendation for both"*

**Verdict in one line:** the CONCEPT (BORP) is alive, load-bearing and **under-served** (only 21% of served rows
satisfy it); the COLUMN `borp_score` is a dead fossil that 3 export surfaces still publish as a trust metric; the
REAL scoring logic the owner is asking about **already exists in the repo** (`isor`, D2284/D2309) and is simply not
served; `feedback_score` must be **kept** — it is a cache whose ledger has never been used, and the correct act is to
declare it and prove it reproducible, not to delete a contract for a primitive the mission needs.

---

## 1. What BORP was — recovered, not remembered

| item | value |
|---|---|
| name | **BORP = Book of Record Principle** (`governance/master_evaluation_prompt.md:36`) |
| the principle | *"≥2 independent sources for convergence"* — a corroboration guard: a claim may only become a Foundation Block if independent works agree on it |
| why it existed | single-source FBs are the slop/echo failure mode ($1 book, 1 passage → "principle"). BORP was the anti-slop gate that made the corpus structural, not just semantic |
| the original implementation | `git show c95f7ff:pipeline/stage5_verify.py` → `def check_borp(fb)`, lines 105-115 |
| the formula as written | `distinct = len(set(source_books))` · `score = min(distinct / BORP_MIN_SOURCES, 1.0)` · `passed = distinct >= BORP_MIN_SOURCES` · `detail = f"{distinct} distinct sources (need ≥{BORP_MIN_SOURCES})"` |
| where it is today | `pipeline/stage5_verify.py:20` — *"DELETED (dead checks): BORP (S1.5 guarantees ≥2 sources), Completeness (S4 fills all fields)"*; `:554` — *"check_borp: BORP guarantee now provided by S1.5 (≥2 sources enforced at cluster level)"* |

### 1.1 The lead for the drop — five findings, in order of strength

**(a) THE FORMULA WAS DEGENERATE BY CONSTRUCTION — this is a proof, not a preference.**
`min(distinct / 2, 1.0)` with the pass bar at `distinct >= 2`: on the *admitted* population (the rows the gate let
through) the score is **exactly 1.0 for every row**. A ratio whose numerator floor equals its denominator, clamped
at 1.0, cannot vary over the population it admits. `borp_score` was never a score — it was a **boolean wearing a
ratio's name**. Reviving it verbatim would reproduce a constant.

**(b) THE PRODUCER WAS DELETED, and the guarantee it moved upstream does not reach every route.**
The check was removed in the name of "S1.5 guarantees ≥2 sources" — true for the **cluster** route
(`S15_MIN_SOURCE_DIVERSITY = 2`), and **false for the singleton route**: singletons by construction have exactly one
source and were never re-checked at S5 once the check was gone. Measured below: **5,198 of 6,591 verified rows
(78.9%) carry ONE source work.** The deletion did not create the single-source rows; it removed the last per-row
assertion of the principle that would have flagged them.

**(c) THE STORED VALUE IS A FALSE ABSENCE (D-2957) THAT TWO CODE PATHS READ DIFFERENTLY.**
`borp_score` is **non-NULL `0.0` on all 7,640 rows** while *nothing writes it* — `pipeline/stage6_commit.py:910`
default-injects `fb.get("borp_score", 0.0)` for every row (the BUG-511 family: a value nothing writes). And inside
the SAME function (`pipeline/retrieve.py` graph-aware search) the two paths disagree about what `0.0` means:

```
SQL     : COALESCE(borp_score, 0.5)      -> 0.0   (0.0 is a VALUE, so the ORDER BY degenerates to rowid order)
Python  : fb.get("borp_score", 0.5) or 0.5 -> 0.5 (0.0 is ABSENT, so the factor is neutral)
```

Measured 2026-10-13 on the live store: `sqlite3 → 0.0 | 0.5`, `python → 0.5 | 0.5`. **One field, one function, two
answers.** That ambiguity is exactly what D-2537/D-2979 had to repair by flipping `ranking.quality_score_enabled`
to `true`, i.e. by *not reading the column at all*.

**(d) THE RANKING REPAIR MADE THE COLUMN READ BY NOTHING — that is the actual "lead for drop".**
The drop was led by the **ranking fix, not by a decision to abandon corroboration**: D-2979 (gate flipped
2026-10-13) + D-2980 (the CLI's second dead `ORDER BY borp_score DESC` copy repointed to the ONE home
`_rank_sql()`). With the flag true, `_quality_field()` returns `confidence_score` and `borp_score` left the ranking
path. What remained were the **surfaces**: the MCP payload and three exports, i.e. the residue D-2980 recorded as
*"NOT DONE, DELIBERATELY: the MCP query_knowledge payload still EXPOSES borp_score and feedback_score
(retired/derived fields). Changing an MCP output schema is a contract change and needs its own owner-gated
decision."*

**(e) IT IS STILL PUBLISHED AS A TRUST METRIC — with outward harm.** `borp_score = 0.0` is written into the OKF
export (`pipeline/stage6_okf_export.py:128-130` emits the line `borp_score: 0.0`), pushed to the Anytype store
(`pipeline/stage6b_anytype_push.py:336,466`), averaged into run metrics (`pipeline/run_monitor.py:162`:
`avg_borp_score`), and printed by the CLI/evaluator. An agent — or a future human reading an exported artifact —
reads **0.0 as "this FB has no corroboration"**, which is a fabricated measurement in the opposite direction of the
truth (the row may be `strong`, `n_sources = 21`). No home and no parity rail exist for it
(`config/derivations.yaml`: `home: null`, `parity_rail: null`, `status: dead_but_read`).

---

## 2. The measurement of record (store: `knowledge pipeline/maxwell.db`, 2026-10-13)

The store holds ONE run: `rechunk-v4-20260929`, 7,640 rows. Population definitions are stated so the numbers are
reproducible.

### 2.1 The dead column and the empty column

| column | non-null | distinct | verdict |
|---|---|---|---|
| `borp_score` | **7,640 / 7,640** | **1** (`0.0`) | a constant that nothing writes — `config/derivations.yaml`: `home: null`, `parity_rail: null`, `dead_but_read` |
| `feedback_score` | **0 / 7,640** | 0 | `declared_but_empty` — but its registry row **names a WRITER**: `pipeline/feedback.py::_update_fb_aggregates` |
| `feedback_count` | 7,640 / 7,640 | 1 (`0`) | the loop has never recorded an event (`fb_feedback` table does not exist in the store yet) |

### 2.2 The real corroboration signal — already computed, already stored, NOT served

| signal | populated | distribution |
|---|---|---|
| `source_ids` (canonical works, D2185/D2309) | 7,640 / 7,640 | 1 source → 6,247 rows · 2 → 893 · 3 → 89 · ≥4 → 411 |
| `is_convergent` | 7,640 / 7,640 | **1,393** rows (identical to the `source_ids ≥ 2` count — an exact identity, measured) |
| `isor` (D2284 ISOR: Independence of Source — author independence × domain diversity × source count) | **6,591 / 7,640** (the S5-verified tier) | `weak` 5,212 · `medium` 969 · `strong` 410 · NULL 1,049 (the D-2590 sidecar tier) |
| `source_diversity` | 7,640 / 7,640 | 1 → 6,247 · 2 → 893 · 3 → 89 · 4 → 27 · 5 → 13 · up to 21 |

`isor` scores by rating: weak 0.731 · medium 0.790 · strong 0.884 (avg `n_sources` 1.01 / 3.9 / 31.9).

### 2.3 The principle's satisfaction rate — the finding that matters

```
status        is_convergent    rows     of which ≥2 source works
PASS               0           3,565            0
PASS               1             938          938
QUARANTINE         0           2,682            0
QUARANTINE         1             455          455
```

**The served population (`status='PASS'`, 4,503 rows) satisfies the Book of Record Principle on 938 rows = 20.8%.**
79.2% of what the system will answer with is single-source, while the payload advertises a trust metric named after
the principle. BORP is not dead — **its measurement is missing from the served surface and its enforcement is
partial by route.**

---

## 3. Recommendation — BORP

### 3.1 `borp_score` (the column and the name): RETIRE from every served surface

Four independent reasons, each already evidenced above: the producer is gone (b); the formula is degenerate (a);
the stored value is a false absence read two ways (c); it is published to agents and to three export artifacts with
no home and no parity rail (d, e). **The name is not reusable**: a `borp_score` that suddenly means ISOR would
silently change the semantics of every consumer — the name is a claim and this one claims the retired ratio.

Disposition: delete the three payload keys (`maxwell_mcp_server.py:136`, `:195`, `:246`), then the OKF/Anytype
publishers (the exports are separate surfaces and must move in the same change-set or the fabricated `0.0` keeps
leaving the machine), then leave the column as **SQL NULL** so the absence is TRUE (D-2957) — a retired column that
holds a value is a lie about absence. `config/derivations.yaml` already declares it `dead_but_read`; the drop turns
`config/served_fields.yaml`'s declared debt from 3 to 2 and the column can then be dropped from the schema in a
schema-version bump, never before.

### 3.2 The principle: ALIVE — and it needs a ruling, not a column

**Revitalization is possible and it is NOT new code.** The real corroboration score already exists:

* `pipeline/schema_accessor.py::isor_score(fb) -> {score, rating, n_sources, n_authors, n_domains, detail}` (D2284),
  canonicalized by `resolve_source_ids` (D2309) over `source_ids` (D2185), with the declared scale
  `strong ≥2 authors ≥2 domains ≥3 sources` / `medium ≥2 of either, ≥2 sources` / `weak` single author or source.
* Its output is already persisted per row (`fbs.isor`, 6,591 rows) and already consumed by the quarantine triage
  and the S5 score axis — it is simply **not advertised**.

**Recommended served shape** (replaces `borp_score`, one owner word, no new logic):

```json
"corroboration": {
  "sources": 3,                       // json_array_length(source_ids) — canonical works, not filenames
  "convergent": true,                 // is_convergent
  "independence": "medium",           // isor.rating
  "independence_score": 0.79,         // isor.score
  "home": "pipeline/schema_accessor.py::isor_score"
}
```

**And the question that is genuinely the owner's** (filed as **T-118**, MUST, owner): 79.2% of served rows are
single-source. May a single-source row be served as if it were corroborated, must it carry a declared
`corroboration.tier = "single_source"`, or must it be withheld from the default answer path? That is a POLICY
ruling — it changes what the system is allowed to say — and no agent may take it (D-2898).

---

## 4. Recommendation — `feedback_score`

### 4.1 The ontology (this is why the first recommendation was wrong)

Two different things were being conflated:

| layer | object | kind | home |
|---|---|---|---|
| the LEDGER | `fb_feedback` (id, fb_id, agent_id, task_id, rating CHECK 0..1, was_correct, was_actionable, was_timely, notes, created_at) | an EVENT RECORD — the truth | `pipeline/feedback.py::record_feedback` (the writer) |
| the CACHE | `fbs.feedback_score` / `fbs.feedback_count` | `derived_regenerable` — a DENORMALIZATION | `pipeline/feedback.py::_update_fb_aggregates` |

**You never drop a cache whose ledger you intend to fill; you declare it and prove it reproducible.** Dropping
`feedback_score` would delete the served contract for the exact primitive the mission needs (a corpus that learns
from *utilisation*, not only from extraction) and would make re-adding it a breaking change for every agent. Its
`config/derivations.yaml` row is already the right shape — `declared_but_empty` with a **named writer** — and its one
missing piece is `parity_rail: null`.

### 4.2 How it works, exactly (as built)

```
agent uses an FB
  → record_feedback(fb_id, rating=0.85, was_correct=…, was_actionable=…, was_timely=…)
      INSERT INTO fb_feedback (…, rating, …)                     # the ledger; rating clipped 0..1 by CHECK
      _update_fb_aggregates(fb_id)
          UPDATE fbs SET feedback_score = round(AVG(rating), 3),
                         feedback_count = COUNT(*)               # the cache; home = the ledger
  → serving (pipeline/retrieve.py graph_aware_search):
      _graph_score = quality * (1.0 + COALESCE(feedback_score, prior)) * graph_boost
      → a row at feedback 1.0 is worth 2× a row at 0.0; the neutral prior silently grants 1.5× to un-fedback rows
  → agents (MCP payload): feedback_score / feedback_count advertised on three surfaces
  → thresholds (reported, not enforced): needs_retirement = count ≥ 5 and avg < 0.3 · needs_boost = count ≥ 3 and avg ≥ 0.8
```

Absence today is **ambiguous on the wire**: the payload publishes a bare `"feedback_score": null` with no state, so
an agent cannot distinguish "no feedback yet" from "score 0.0" (= maximally bad). That ambiguity — not the null — is
the defect.

### 4.3 How it SHOULD be scored — the formula (senior recommendation)

```
effective(n, mean) = (n * mean + k * prior) / (n + k)         # shrunk mean; k = prior_weight, prior = 0.5

n = feedback_count, mean = feedback_score, k = prior_weight (config)
k = 0  → the plain mean, i.e. EXACTLY today's behaviour (byte-identical, no recalibration)
k = 3  → recommended once the loop has traffic: one 1.0 rating no longer outranks twenty 0.9s
```

Three reasons this is the right shape: (1) a mean over one event is not evidence; shrinkage is how a feedback loop
avoids being captured by its first reviewer; (2) the shrink constants become **declared** values instead of code
literals (C12); (3) the serving prior stops being a literal in SQL *and* in Python and gets ONE home.

**Recommended served shape** (absence made explicit, D-2957 extended to the wire):

```json
"feedback": {"score": null, "count": 0, "state": "no_feedback", "prior": 0.5, "effective": 0.5}
```

### 4.4 The completion change-set (declared now, applied under the owner's one word)

| # | defect | fix | where |
|---|---|---|---|
| 1 | thresholds hardcoded in code (`RETIREMENT_THRESHOLD 0.3`, `RETIREMENT_MIN_FEEDBACKS 5`, `BOOST_THRESHOLD 0.8`, and the literal `count >= 3`) | read `config/feedback.yaml` **fail-closed** (no code default) | `pipeline/feedback.py` — **done in this act** |
| 2 | the prior `0.5` is a literal in 4 places inside one function (SQL ×2, Python ×2) | ONE declared value `serving.neutral_prior` | `pipeline/retrieve.py:1070,1071,1090,1091` — **owed (T-107)** |
| 3 | the aggregate has no parity rail (D-2642) | `scripts/check_feedback_parity.py` — recompute from the ledger, known-answer controls — **done in this act** | new rail |
| 4 | absence is ambiguous on the wire | the `feedback` block above | `maxwell_mcp_server.py` — **owed (T-107)** |
| 5 | `needs_boost` is computed and **nothing consumes it** (C19: a declaration nothing reads) | wire it (a retrieval-policy ruling) or retire the flag | owed — named |
| 6 | `get_fb_feedback_stats` swallows an exception and returns "healthy" (C16: no silent errors) | return a tri-state `state: "unmeasured"` / `needs_retirement: None` — never a silent False | `pipeline/feedback.py` — **done in this act** |

---

## 5. What this act changed, and what awaits the owner's word

**Applied (additive instruments, no store write, no payload change):**
`config/served_fields.yaml` (the ONE home of the declared disposition + the owner word) ·
`scripts/check_served_fields.py` (the rail: advertised field joined to the registers that own its truth, shrink-only
debt) · `scripts/check_feedback_parity.py` (the ledger→cache parity rail D-2642 was missing) ·
`config/feedback.yaml` (C12: thresholds, prior, formula) · `pipeline/feedback.py` (config-driven, tri-state, no
behaviour change) · `specs/served_fields.spec.md` + `tests/test_served_fields_spec.py` (INV-1..INV-9, paired 1:1).

**NOT applied — owner-gated (T-107):** the three payload keys, the OKF/Anytype publishers, the prior's move out of
`retrieve.py`, the `feedback` block, and the `corroboration` block. The rail MEASURES the debt today (3 → 2 when
`borp_score` leaves) so the owner's word is a config edit plus a named code edit, and the rail refuses a
half-move (a declaration without the code change, or a code change without the declaration — BUG-548: the record is
not the rule).

**Also filed:** **BUG-767** (the retired trust metric still published by 3 export/package surfaces) and **BUG-768**
(the S5 BORP deletion left the singleton route unguarded: 5,198 of 6,591 verified rows are single-source).

**Next critical step:** T-104/BUG-757 (101 of 185 open bugs carry no severity token — the bug axis of the same
partition defect D-2987 settled on the decisions axis). Owner lane, ready now: T-107 (one word per field),
T-117 (one word per unit), T-118 (the single-source trust tier), T-101 (30 `anchor` cells).
