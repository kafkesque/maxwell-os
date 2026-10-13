# SESSION HANDOFF — 2026-10-13 — D-2986: A HEADING IS A CLAIM (BUG-761 FIXED, T-115 done)

**Your words that produced this act:** *"I dont understand T-115 (BUG-761 and what do you mean decide what a
Hand tier"* — followed by the standing rule (highest-leverage next; senior RAG/system/ontological-architect
lens; forensic audit before implementing; delegate and verify no drift; sync governance dependencies).

**The act in one sentence.** A heading is a claim: below the history marker a heading that names a current
state must say WHAT it is (a declared hand index, never the authority) and may not carry a count — because the
sentinel's own sentence was FALSE about the twelve headings sitting under it, and two of those headings were
restating a number the register had moved on from.

**Bugs:** BUG-761 (MED) → FIXED. **Task:** T-115 → `state: done`. **Decision:** D-2986 (RESOLVED, minted,
total 1114, stamp `09e1c567a49c1ce7`).

---

## 1. THE LEVERAGE CALL — what the owner saw, and what was true

| what the face said (before) | what was true |
|---|---|
| `## 🟢 ACTIVE — in effect (477)` | the register held **565** ACTIVE — written ten days earlier, never joined |
| `## ⚪ DONE / CLOSED — bottom (97)` | **348** closed (resolved 313 + superseded 16 + archived 8 + rejected 11) — found by looking, not named in the bug |
| `<!-- GOV-HISTORY:START … everything below is DATED HISTORY: append-only, NOT a register -->` | below it sat the owner's own INDEX sections, **hand-maintained** (BUG-761 itself was appended to one of them the day the marker existed) and row-joined by the rail |
| `## 🔴 OPEN — MUST`, `## 🟠 SHOULD — open`, `## ✅ DONE — bottom`, … (12 headings) | a current-state claim inside a region every face declares makes **no live claim** — a claim with no join |

**Why this was the top item.** D-2984 policed the rows and the prose *below* the marker; D-2985 policed the
*live region above* it. The headings **between** the two were policed by nothing, and the marker's own
declaration — the sentence that tells the owner how to read the file — was the thing that was false. This is
the same class as the complaint that started the D-2984/D-2985 pair, one layer down: a face telling the owner
something untrue about the thing he is reading. It was also the last open item of that pair (BUG-761 was the
residual D-2984 recorded **on purpose**), so it closes the set rather than opening a new front.

**Rejected alternative (recorded, not silent).** BUG-761 offered a choice per face: (a) relabel a dated
snapshot, or (b) promote the tier into the derived block. **(b) is refused**: a bug's narrative has its home in
the bug's own section, so a derived table of that prose would be a SECOND home for prose (D-2642), while
OPEN-ness is already the census's. **(a) is not taken literally either**: a snapshot claims a moment it cannot
prove, and these sections are row-JOINED to the *current* register rather than frozen at a past one. So they
are declared for what they actually are: a hand index behind the derived block, and behind every join that
keeps it honest.

## 2. RULE → MECHANISM → SEEN

| rule | mechanism | SEEN (the control that fired) |
|---|---|---|
| the sentinel tells the truth about its own region | `scripts/gov_sync.py#HIS` now declares BOTH kinds of content (hand indexes: row-joined, never the authority; dated history: append-only); hand-edited into the 3 faces in the same act | `gov-sync --selftest` 19/19; `gov_sync --check` byte-compares all 4 faces |
| an index heading declares itself | `scripts/check_governance_faces.py#heading_faults`, limb 1, leading-token only | `  ok  an INDEX heading that names a current state and declares nothing must fire` (+ the D-2984 snapshot form staying quiet) |
| no count in a label | same function, limb 2 (`HEAD_COUNT_RE`) | `  ok  an INDEX heading restating a COUNT must fire (a count has one home)` |
| the rule cannot silently die | 2 entries in `config/rail_mutations.yaml`, floor 37 → 39 | `ok rail mutations: 38 declared rule(s) SEEN to red through their own control … 1 negative control(s) stayed green` |
| the rule is written down and graded | `specs/governance_faces.spec.md` INV-14 + `tests/test_governance_faces_spec.py` | 22/22 paired contracts green (governance_faces 15, task_register 7) |
| the register keeps step | `config/task_register.yaml` T-115 `done`; `scripts/recompute_decision_summary.py --mint --apply` | `merged 1 record(s): D-2986 - total=1114, stamp 09e1c567a49c1ce7` |

## 3. MEASUREMENT OF RECORD

**Baseline (measured before any write):** 12 index headings below the three markers; 2 of them carrying a
count (`(477)`, `(97)`); the sentinel's declaration false about all 12; the policy note asserting the `D2537`
spelling survived "ONCE" (it survived in four places).

**After:** `check_governance_faces` rc=0 with **38/38** controls (was 31; 7 new, both directions);
`check_buglog_tiers` rc=0; the independent pass (fresh code, importing neither the rail nor the writer) reports
**12 index headings · 0 undeclared · 0 carrying a count**, and the three derived blocks agree with the
registers: **1114 decisions · 528 bugs (184 open / 344 closed; highest OPEN = BUG-757) · 13 open tasks
(3 OWNER-moved, 10 pipeline)**. BUG-761 CLOSED → 184 open / 344 closed of 528.

## 4. FORENSIC AUDIT (before the writes)

* **Every reader of the changed surface enumerated:** `scripts/gov_sync.py` (writer + schema validator),
  `scripts/bug_status.py` (the buglog headings are its status slots), `scripts/check_governance_faces.py`
  (5 surfaces + the new one), `scripts/check_buglog_tiers` (reads the ICON — untouched), the mutation gate,
  `scripts/check_decision_membership.py`, `scripts/check_rail_registry.py`, `scripts/check_declaration_consumers.py`.
* **The marker text is pinned in one place.** Every consumer greps for the sentinel `GOV-HISTORY:START`
  (`HIST_MARKER_RE`, the two test files, the fixture), so only the explanatory tail changed — `gov_sync.HIS`
  and the 3 faces, in the same act (verified by the independent pass: the sentinel in all three faces is
  byte-equal to the writer's own constant).
* **The first run of the limb FIRED ON A GOOD FACE, and the rule was corrected — not the face.**
  `DECISION-LOG.md:205 ### Pending from registry (SNAPSHOT 2026-10-03 — … the DERIVED index at the top owns the
  current state, D-2984)` already declares, in D-2984's form. That is now a **named known answer**, and the
  declaration is a declared PATTERN accepting both true shapes.
* **A tempting over-reach was refused BY MEASUREMENT.** A word-ANYWHERE form of the rule fires on **399
  RECORD headings** in buglog.md (`## BUG-331 — … (MED, OPEN)`) — the register's own status slot. The rule
  reads the LEADING token only.
* **Nothing was deleted (R-D410).** The 12 headings were extended in place; the two counts were dropped from
  labels while the numbers remain in the registers and the derived block; BUG-761's OPEN-tier row was
  **re-tiered** into the CLOSED index rather than removed (its status slot moved into the leading parenthetical,
  the BUG-633 class); the resolution is an append to the bug's own section.
* **Cascade check.** `bug_status.py` → 184/344 (the leading parenthetical is the authoritative slot, so the
  closure took effect on the first run); `gov_sync --apply` re-cut the 4 faces; `severity_grandfathered: 101`
  is untouched and still correct (BUG-761 carried MED, so only the population moved: 4+22+38+19+101 = **184**);
  the task census dropped by exactly one (14 → 13).
* **Deliberate non-actions.** (i) The `###` sections deep inside the dated tail that name a state with no date
  (e.g. `### USearch/HNSW recall benchmark (RATIFY-2 gate #1) — STILL PENDING`) are NOT index headings and are
  not re-checked — named as a limit rather than silently left. (ii) The 8 code comments that spell the ranking
  decision `D2537` are recorded, not edited: not face claims, and they sit under a pipeline write boundary a
  governance act should not cross for a comment. (iii) No alias key was invented for `D2537` (nothing would
  read it — C19). (iv) No ceiling was raised anywhere.

## 5. GOVERNANCE SYNC ORDER (as applied)

declarations (`config/gov_sync.yaml`: the token list, the hand-index token, the declaration pattern) → the
sentinel (`gov_sync.HIS` + 3 faces) → the rail limb (`heading_faults` + 6 controls + the surface list + the
docstring) → the 12 heading repairs + the 2 count removals → spec INV-14 + the paired test (13 → 14 invariants;
INV-9's mutation count 2 → 4) → 2 mutation locks (floor 37 → 39) → the buglog (BUG-761 FIXED, resolution
appended, row re-tiered) → `bug_status.py` → the register (T-115 done) → mint D-2986 → `gov_sync --apply`
(4 faces) → `specs/README.md` inventory row → `config/decisions_policy.yaml` note CORRECTED →
`specs/retrieval_serving.spec.md` citation repaired → `governance/CONTEXT_INDEX.md` (§7 pointer + the act
record) → `justfile` rationales (the faces rail and a stale "13 block answers" → 19).

## 6. HONEST LIMITS

1. The rule covers an INDEX heading. A `###` section inside the dated tail that names a state without a date
   is not covered and is not re-checked (named in §4, in the spec, and in the buglog).
2. The hand index is a **selection**, not a partition: it lists what the author chose to list. Only the derived
   block and the registers carry the whole population. (Its rows ARE joined, so it cannot lie about a row it
   does list.)
3. The 8 code comments spelling `D2537` are recorded, not repaired.
4. The register's long-form prose is still policed only for census-shaped restatements (D-2985's limit).
5. The spec was written in the same act as the code — D-2978 prefers spec-first; the invariants were designed
   before the implementation, the file was written after it. Recorded, not claimed.
6. The derived block prints at most `face_list_limit` (12) open bugs, so it is a view, not the register — the
   full set is `scripts/bug_status.py` / `governance/bug_status.json`.

## 7. DELEGATION / VERIFICATION

No ad-hoc delegate: the act is one rule with two writers plus its contracts, and splitting it would create two
writers of one rule (the D-2984 lesson). The local-LLM call was the ratified **R5 gate**:
`scripts/r5_review_gate.py --file scripts/check_governance_faces.py` → **APPROVE** (syntax PASS, lint PASS,
C11/C12 PASS; receipt appended to `governance/r5_review_gate.jsonl`). Independent conformance pass (fresh code,
no rail, no writer) green.

## 8. NEXT CRITICAL STEPS (strategic-consequential order)

1. **T-104 (MUST, pipeline, NOW THE TOP OF THE PIPELINE LANE)** — BUG-757, the severity backfill: 101 open
   bugs carry no severity token, so the register can only be ordered by id. The derived block prints the
   severity partition (CRITICAL 4 · HIGH 22 · MED 39 · LOW 19 · UNLABELLED 101 = 184) but cannot order a
   critical list. **This is the item that makes the derived block able to answer "what is most severe" — and
   it is what the hand index was substituting for.**
2. **T-114** — discharge the five recorded ladder faults, LOWERING each shrink-only ceiling per wave (D-2644).
3. **T-105 / T-106 / T-108.** 4. **T-112** (per-process cross-encoder cold start), **T-113** (71 keys).

## 9. THE OWNER LANE — what only YOU can move

**T-101 (MUST) — harden the retrieval golden set. THE INFRASTRUCTURE EXISTS; NOTHING MUST BE BUILT.**
- The file: `governance/golden_reanchor_candidates_20261011.csv` — **150 candidate rows across 30 queries**,
  every `decision` and `owner_signature` cell EMPTY. Fill ONLY those two columns.
- `decision` ∈ {`keep`, `replace`, `drop`, `add`}; then `owner_signature` (your word, per row).
- The generator: `scripts/reanchor_retrieval_goldens.py --top 5` (re-run if you want a fresh sheet).
- Then: `python3 pipeline/retrieval_benchmark.py` before and after, and `--apply` once you are satisfied.
- **Success signal:** recall@10 drops BELOW 1.000. Today it is **1.000** (saturated) with MRR 0.919 on 29
  single-answer goldens — a perfect score on an easy ruler is the defect, not the goal (D-2939: anchors are
  owner-signed; a model may not sign one).
**T-103 (MUST) — one word: may the label re-derivation be written to the store?** (BUG-749 residual; the census
names the debt, the owner-ruled rows are store-write-owed.) Gate text: *the owner word that licenses the store
write.*
**T-107 (SHOULD) — one decision: does the MCP payload keep advertising `borp_score` / `feedback_score` to
agents?** (`borp_score` is a retired constant 0.0.) Gate text: *owner word on the payload schema.*
