# DECISION — D-271a / D-271b / D-271c: identity, authority control, and LINK vs MERGE

**Status:** RULED 2026-09-17. Evidence: `scripts/identity_tax_ab_test.py` (R5 gemma-4-E4B **APPROVE**,
digest `d89a44a21a1a8295`) + the measurements below. Read with `CONTEXT_INDEX.md` §8.

**The question asked:** which axis matters more in RETRIEVAL — domain or discipline — and does that make
D-271a (the `research methodology` collision) viable? Does D-271b (LINK instead of MERGE) create duplicates?
And: test the future-tax-minimising solution separately and in combination.

---

## 1. WHICH AXIS CARRIES RETRIEVAL (measured, 7,995 rows)

| property | discipline | domains |
|---|---|---|
| labels per row | **1.00** | 2.16 (max **7**, contract says 1..3) |
| classes | 62 | 44 |
| coverage | **100%** | 100% |
| largest class | 907 | 1538 |
| classes < 20 rows | 13 | 0 |
| filter operator in `pipeline/retrieve.py` | `discipline = ?` (**exact**) | `domains LIKE '%x%'` (**substring**) |
| index | **none** | **none** |
| feeds another axis | **YES — `depth: cross-domain` is DEFINED as "bridges 2+ distinct DISCIPLINES"** (789 rows) | no |

**Ruling: in retrieval, DISCIPLINE is the primary facet and domains is a secondary recall-broadener.**
The reason is not taste: discipline is single-valued, exactly filterable and *load-bearing for a second axis*
(depth), while domains fan out across 1..7 buckets per row. A partition key that also decides another axis
cannot be dissolved to resolve a label collision.

**Self-correction (do not quote the earlier claim):** an intermediate probe reported the `domains LIKE`
filter as "66% noise" for `research & methodology`. That probe used a *partial* string (`%research%`).
With a **full canonical label the LIKE filter is exact** — measured 0 false positives, and 0
substring-containment pairs among the 44 domain labels. The real defects are that it is **not sargable**
(full scan), that a partial query silently over-matches, and that the discipline column has 5 substring
pairs (safe only because it uses `=`). Logged as BUG-275. The retracted claim is barred in `CONTEXT_INDEX.md` §9.

---

## 2. D-271a — the collision, and why collapsing either side is the wrong fix (SUPERSEDED by section 2a)

Population of the collision: **742 rows** = 94 discipline-only + **167 BOTH (the genuinely ambiguous set)** + 481 domain-only.

| option | rows migrated | rows relabelled | what breaks | reversible? |
|---|---|---|---|---|
| **A. two concepts** (sharpen both definitions + add each to the other's `exclude`) | **0** | **167** (the BOTH set only) | nothing; classes stay 62/44 | **yes — 1 alias row under D-271c** |
| B. collapse the DISCIPLINE into the domain | 261 | 261 | 94 rows lose every fallback signal → forced into the `emerging` fail-closed catch-all; 62 → 61 discipline classes; the exact-match key disappears for those rows; a re-label runs on the **weakest-provenance axis** (human share 0.347) | no |
| C. collapse the DOMAIN into the discipline | 648 | 648 | 648 rows of domain recall lost; **150 rows left with ZERO domains**; 44 → 43 classes | no |

**Original ruling (SUPERSEDED by section 2a): OPTION A.** Two concepts, both defined sharply, each listed in the other's `exclude`;
both labels stay canonical as-is (revised 2026-09-17, see section 2a — the 167 rows need no adjudication). Do NOT collapse either side: B costs 94 rows a
fail-closed label *and* destroys an exact filter key, C costs 648 rows of recall and leaves 150 rows
domain-less, and both are one-way doors.

---

## 2a. REVISION (2026-09-17, later the same day) — DECLARED HOMONYM, CHANGE NOTHING

The correction is upheld and it supersedes the earlier "sharpen both + adjudicate 167" remedy:
**if discipline carries retrieval primacy, then the discipline label `research methodology` is the more
important of the two — and since neither label is broken, the correct action is to change nothing.**

- **No rename, no merge, no migration, no relabel, no 167-row adjudication.** The 167 rows carrying both
  are *coherent*: a research-methodology object that sits in the research & methodology domain.
- **They do not contaminate; they are homonyms across two namespaces.** A discipline is not a domain, and
  sharing a name is harmless *as long as nothing joins on a bare normalised name*.
- **Verified that this holds today:** `config/taxonomy_v5.yaml` keeps `disciplines` and `domains` as
  **separate top-level keys** (no flat combined vocabulary), and `scripts/audit_taxonomy_disjointness.py`
  reports **0 undeclared normalised collisions across 7,995 rows**.
- **Retrieval precedence is now explicit rather than implicit** — and it is the *reverse* of a
  "keep the larger bucket" heuristic, which counted rows (648 vs 261) instead of weighing the axis:
  **discipline wins for partitioning** (single-valued, exact `=`, 100% coverage, load-bearing for
  `depth: cross-domain` on 789 rows); **domains wins for recall** (a 1..7-label broadener).
- **G8 downgraded:** from "adjudicate 167 rows" to "**ratify this declaration**" — minutes, not hours.
- **Required so it stays true:** (1) namespace enforced on write (guard + criterion AXC); (2) no
  normalised union of the vocabularies may ever fuse them; (3) cross-taxonomy set operations must be
  namespace-qualified (`discipline:X` != `domain:X`). Under D-271c each label also gets its own
  `concept_id`, making the separation **mechanical** instead of conventional.

**Why this is strategically superior:** it is the only option with zero migration cost *and* zero residual
risk, because the "collision" was never a data defect — it was a missing *declaration*. The earlier remedy
would have spent 167 human adjudications fixing something that is not broken.

## 3. D-271b — LINK DOES NOT CREATE "A BUNCH OF DUPLICATES"

| population | groups | member rows | a MERGE would DELETE |
|---|---|---|---|
| name-identical (production rule) | 6 | 12 = **0.15% of the KB** | 6 |
| semantically flagged (`dedup_candidates.jsonl`, UNVERIFIED) | 273 | 662 = 8.28% of the KB | **389** |

**Ruling D-271b: LINK supersedes MERGE — confirm.**
- The fear is mis-scaled: the *only* duplicate population the production identity rule can even express is
  **12 rows (0.15%)**. The 662 rows are *algorithmically flagged*, never verified (the T1 judge was measured
  on 7 decisive rows — BUG-269).
- **LINK is already the ratified policy** — D2627 defines `duplicate_of` as "canonical fb_id when this row is a
  dedup; NEVER delete". D-271b is not a new policy, it is *enforcement of a decision that was never wired up*.
- Duplicates in **retrieval** are zero: with `duplicate_of IS NULL` the KB returns the same 273 representatives
  a merge would have left — while retaining 389 rows of evidence. Each member appears in exactly 1 group, so
  there is no double counting.
- The asymmetry is decisive: LINK under an unverified judge is **reversible**; MERGE under an unverified judge
  destroys 389 rows permanently. **A destructive operation may never be gated by a judge that ties the
  constant-answer baseline.**

---

## 4. THE SOLUTION, TESTED SEPARATELY AND IN COMBINATION

Executed by `scripts/identity_tax_ab_test.py` against the live KB (SELECT-only). Failure modes are sized,
not assumed.

| component | test result | verdict |
|---|---|---|
| **S1 `concept_id` alone** | 164,202 edges still store the old content hash | **FAILS ALONE** — an id that nothing points at fixes nothing |
| **S1 + edges re-keyed to `concept_id`** | 164,202 edges addressed by a stable pointer; rename breaks **0** | PASSES |
| **S2 authority control alone** (label-keyed alias table) | **5** labels map to >1 concept → unresolvable without an id | **FAILS ALONE** |
| **S1 + S2** | renames = 1 prefLabel update + 1 alias insert; old label survives as altLabel; ambiguity **0** | PASSES |
| **S3 LINK alone** | 0 rows lost; 662 rows retained vs 389 deleted; retrieval dedupe via `duplicate_of` | PASSES (reversibility) |
| **S1 + S2 + S3** | 0 broken edges, 0 rows lost, 0 ambiguous labels, label distributions untouched | **RECOMMENDED** |

**The measured cost of doing nothing:** renaming the highest-degree marked object
(`Typography As Visual Communication (2)`) changes its `fb_id` and orphans **320 edges in one operation**.
Multiplied over the 41 marker-named rows this is the future tax; today the graph happens to be intact
(0 dangling of 164,202), so the entire cost is *latent* and lands the moment anyone renames or edits a definition.

**Peer-reviewed mapping (the design is not novel, which is the point):** stable surrogate identity +
prefLabel/altLabel = IFLA/VIAF **authority control** and **SKOS** `prefLabel`/`altLabel`; the surrogate id =
**persistent identifiers** (ARK/DOI/QID); partitioning by facet = **MeSH / ACM CCS / IEEE Thesaurus** faceted
classification; LINK + duplicate flag + clerical-review band = **Fellegi-Sunter** probabilistic record linkage
(Splink, UK MoJ) where linkage *never* destroys a record; the destructive path it replaces is precisely the
weakness of naive record merging. **git** has the same trade-off and resolves it the same way: content-hash
addressing + a separate rename-inference path, never a rewrite of history.

---

## 5. ULTIMATE SOLUTION (bulletproof form)

1. **`concept_id` minted once, never recomputed** from name/definition (`config/identity.yaml`).
2. **`fb_id` demoted to an alias**; every input path still accepts it (no caller breaks on day one).
3. **Authority control**: one `pref_label` per concept, all historical/variant labels as `alt_label`.
4. **Edges store `concept_id`** (`related_fbs`, `source_principle_ids`, `duplicate_of`) — this is what actually
   removes the tax; the id without the re-key is decorative (proved by the S1-alone failure).
5. **LINK, never MERGE**; `duplicate_of` + quarantine; deletion only via `pipeline/safe_delete.py` (R-D410).
6. **LINK always sets `status='QUARANTINE'`.** Measured 2026-09-17: that — not `duplicate_of` — is what already
   keeps the 17 linked rows out of default retrieval (`search_keyword` defaults to `status='PASS'`).
   `duplicate_of` has **no reader** in `pipeline/`: it is a provenance pointer, so the pairing must be
   enforced in config, not assumed. Facet indexes applied (BUG-275 §2).
7. **Rename freeze until (1)-(4) land** — the interim rule that costs nothing and prevents the only
   irreversible event.

**Why this is the future-proof one:** it converts every remaining open taxonomy question from a
*migration* into an *alias edit*. Concretely, if the D-271a ruling is later reversed, the cost is
**1 alias row instead of a 742-row relabel** — and the 167-row adjudication is never wasted, because those
labels survive as altLabels.

---

## 6. WHAT IS STILL HUMAN, AND WHAT IS NOT

| item | who | why |
|---|---|---|
| **G8** ratify the homonym declaration (was: adjudicate 167 rows) | **HUMAN** | governance renders the ruling; the data needs no work |
| ratify §2 / §3 / §4 rulings | **HUMAN** | governance |
| D-271d: enforce the LINK=`QUARANTINE` pairing in config + add the facet indexes | no human | deterministic code, R5-reviewed (gemma APPROVE) |
| implement `config/identity.yaml` (migration + alias backfill) | no human, **gated on G8** | must not migrate before the collision ruling lands |
| 41 marker names → prefLabel + altLabel | no human | deterministic, defined in config |
