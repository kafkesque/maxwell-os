# Root cause, not symptoms — and the architecture that makes the classes unrepresentable

**Date:** 2026-09-25 · **Scope:** read-only audit of the bug register + the code behind it.
**Trigger (owner):** "investigate all critical bugs, examine the root cause, not just mitigate or patch them,
and give your senior software-engineer recommendation how to go forward" — and: from now on, be
situation-aware and drift-aware rather than patch-driven.
**Production code touched by this audit:** none. `pipeline/**` and `scripts/**` unmodified. Two register
entries were appended (BUG-481, BUG-482) and `governance/bug_status.{json,md}` regenerated.
**Nothing committed** (standing rule: no commit without the owner's ack).

---

## 0. What was measured, and what was not

| measured | how |
|---|---|
| register state | `governance/bug_status.json` (authoritative machine register), 116 open / 110 closed of 226 after this audit |
| register PARSER | `scripts/bug_status.py` read in full; `scripts/check_bug_status.py` read in full |
| closure claims the parser cannot see | independent scan of the log, two probes (strict explicit-status probe, loose closure-word probe) |
| destructive-write surface | repo-wide scan for `open(...,'w')`, `write_text(`, `truncate(`, `unlink(`, `shutil.move/rmtree` filtered to governance / gold / workbook / checkpoint / sheet targets |
| rail wiring | `just health` block read in full; every `scripts/check_*` + `scripts/verify_*` cross-checked against recipe invocations |
| the 24 CRITICAL/HIGH/structural entries | full body text read, not the titles |

Not done, and stated so this does not become a false existence-negative (BUG-422/BUG-426 standing rule):
no `pytest` run in this pass (the last full-suite green was the pre-edit control, 232 passed / 5 skipped);
no re-measurement of the archived corpus; no attempt to re-derive the BUG-391 denominators.

---

## 1. The five root-cause families

The register is 226 ids. Almost every open entry is an instance of one of five classes. The instances share
a mechanism, and the mechanism — not the instance — is what keeps regenerating them.

### RC-1 — One artifact, many writers, no ownership partition
**Mechanism.** An artifact holds cells/keys with *different* owners (machine-derived vs human-authored), and
every writer that regenerates the machine part rewrites the whole file. The human part is collateral.

**Instances.** BUG-478 (the declared panel ingester truncates the ANCHOR-4 workbook to the dispute set and
blanked 148 owner cells) · BUG-443 (cloud editor overwrote the normalised owner workbook) · BUG-433 (a
committed artifact clobbered 3 h later, silently) · BUG-376 (the S4 checkpoint was rewritten *after* the S5
run that declared it — the verified input image no longer exists anywhere on disk) · BUG-341 (same class,
regression) · BUG-460 (an instrument builder overwrote the live instrument and narrowed its schema) ·
BUG-409 (a YAML round-trip rewrote a 100k-line governance artifact and destroyed its blame history) ·
BUG-261 (`safe_delete` copied before deleting and could fill the disk) · BUG-406 (a temp sweep moved **35
declared inputs** out of `temp/`) · BUG-394 (7995 orphaned vectors, 0 live, while a COUNT check printed
"READY").

**Why patching fails.** BUG-478's mitigation (a new safe ingester) is correct and shipped — and the class
still stands, because the *next* script that regenerates that workbook will not know. The decisive evidence
is in the repo: exactly two scripts implement the correct discipline
(`scripts/ingest_panel_column.py`: refuse if any non-owned cell would change; `scripts/normalize_owner_workbook.py`:
byte-exact backup, fail closed on blank-row drift, atomic replace). 156 of 274 scripts under `scripts/`
contain a `'w'` write. So the discipline exists as a *habit in two places*, not as an *invariant*.

### RC-2 — Declarations and reality are never joined in one place
**Mechanism.** A YAML file declares something about the world; the world diverges; nothing compares the two.
The declaration keeps being quoted as if it were a measurement.

**Instances.** BUG-476 (five declared depth raters, three ever ran — alpha's missing-cell capability made an
*empty column* indistinguishable from a *skipped row*) · BUG-462 (a declared agreement floor with no
consumer) · BUG-463 (the family registry understated the depth state, 0 vs 145) · BUG-466 (148 adjudicated
rows against a declared 150-row cohort, no exclusion rule) · BUG-464 (a column that reads as 192 open items
when 4 cells are open) · BUG-465 (a blank carries four meanings and the contract sees one) · BUG-450 (`coder`
ABSENT, not null) · BUG-454/BUG-461 (one token, two namespaces — the same defect three times) · BUG-459 (a
false existence-negative in a docstring) · BUG-468 (a digest recorded in prose for a live file that has since
been written) · BUG-448 (an existence gap, not a regression) · BUG-455/BUG-456 (no content identity: 6
byte-identical backup slots = one recovery point with six names) · BUG-412 (an absolute path nobody resolves).

**Why patching fails.** ~30 `verify_*`/`check_*` scripts already exist. Each checks one declaration against
one artifact, each was written ad hoc, each had to be *remembered*. That is why the same class arrived 30
times under 30 names.

### RC-3 — Self-certifying rails: green means "my parser agrees with my parser"
**Mechanism.** A rail whose evidence is the same source as the artifact it checks cannot detect drift.

**Instances.** `check_bug_status.py` re-derives the register **from the same headers** and byte-compares —
it certifies the parser, never the log (proof in §2.1). BUG-467 (the aggregate rail was RED for a whole pass
while every individual rail was green). BUG-445 (the guard could be *silenced* instead of satisfied). BUG-399
(a derived count drifted and its detector ran nowhere). BUG-390 (dead rows). BUG-447/BUG-453 (one
`menu_hash` with two meanings; a composite used as an answer-space pin). BUG-284 (tooling kept reporting a
ruled question as an open defect). And D-390: the aggregate rail runs **rails, not the suite**.

### RC-4 — Numbers travel without their ruler
**Mechanism.** A figure is quoted without its population, denominator, artifact hash, and generator. It is
then indistinguishable from a measurement.

**Instances.** BUG-391 (the *ratified* abstention operating point — 0.4741 on n=116 — is not reproducible
from anything on disk; on the ruler in force it is 0.5533, and the artifact naming the 6 excluded rows does
not exist) · BUG-334 (a pre-registered n is not automatically the measurable n) · BUG-336 (an agent's
measurement claim is not evidence) · BUG-422/BUG-426 (a claim about a missing signal measured on a *derived
copy*; the signal existed) · BUG-306 (the single-coder ceiling κ=0.333 is contaminated by same-person +
ruleset mismatch — and, decisively, there **is no second human available**) · BUG-295/BUG-296/BUG-389/BUG-357/
BUG-359/BUG-360.

### RC-5 — The meter is unvalidated before it decides
**Mechanism.** A classifier, gate or NLI is used to decide labels before its own discriminative power has
been measured on a known-answer set.

**Instances.** BUG-305 (the definition-anchored NLI emitted ~100% CONTRA on the principle class — the
hypothesis was a *category meta-definition*, and NLI cannot test category membership: a register mismatch,
instance vs category) · BUG-297/BUG-299 (the serving gate was a *label* — `status = 'PASS' if
content_type == 'principle'` — with 1,941 PASS rows whose own verification says `passed=False`, and 506
verified rows quarantined) · BUG-303/BUG-304 (stored labels 25–47% wrong per axis) · BUG-283 (the ruler
scorer only accepted integer indices and would have crashed on the first real sheet) · BUG-260 (the raw LLM
label scored against canonical gold) · BUG-318/BUG-319 (harness wiring killed an arm; an arm abstained
116/116 and read as normal) · BUG-480 (this week: the claim-shape gate is a perfect *screen* — 0 false
positives — and a weak *classifier*, because q3 is a constant at 11/11).

**Why this family is the most expensive.** It is the only one whose defects propagate into the *labels*.
RC-1..RC-4 cost work; RC-5 corrupts the foundation others build on.

---

## 2. Two findings produced by this audit (both new, both logged)

### 2.1 BUG-481 — the register over-reports: 8 ids carry an explicit closure the parser cannot see
`bug_status.py` folds **header** events (last wins). A closure written as a body paragraph is not an event.
Strict probe (`**Status:** FIXED|RESOLVED|CLOSED` inside the last header's body): **BUG-254, BUG-276,
BUG-283, BUG-284, BUG-285, BUG-286, BUG-379, BUG-380** — 8 ids. Loose probe (any closure word): 19, of which
BUG-341 / BUG-343 / BUG-314 / BUG-355 are correctly OPEN (they mention another bug's closure, `FAILS CLOSED`,
or a partial). **Register over-reports by 8 (114 → ≤106 at audit time)**, which inflates the C15
handoff rule and makes "114 open" a parse artifact rather than a state.

This is RC-2 and RC-3 in one object: one fact (is it open?) carried in two places, and a rail that compares
the register to its own generator. **It is the register's own instance of the disease the register exists to
catch.**

### 2.2 BUG-482 — three checks built this week are invoked by nothing
`grep -c <name> justfile` = **0** for `scripts/check_depth_load_bearing.py` (D-397), `scripts/ingest_panel_column.py`
(D-398), `scripts/score_claim_shape_gate.py` (D-399). All three exist, all three were run by hand, none is
reachable from any recipe. §5 of the D-397 work made "the depth axis is NOT load-bearing" a *rail* precisely
so it could not fail silently — and that rail is now itself silent. `just health` is a hand-maintained list;
nothing asserts that a check which declares a contract is invoked anywhere.

---

## 3. The systemic root, in three primitives

Stripped of instance names, the five families are all one of three missing primitives:

1. **No owner-of-record per artifact.** Nothing in the system can answer "who may write which cells of this
   file, and what must happen if the answer is 'not me'?" (§ RC-1)
2. **No content-addressed handoff.** Stage inputs/outputs are *mutable paths*. A path can be rewritten by
   anyone at any time, so a hash claim about it can be invalidated without any transaction failing. (§ RC-1,
   BUG-376)
3. **No reconciliation surface.** Declaration and reality are joined only where someone wrote a bespoke
   check. There is no place where "for every declared object: does a consumer exist, does the artifact
   match, is the digest current, does every declared path resolve" is answered for *all* declared objects at
   once. (§ RC-2, RC-3, and the fact that the newest work already reproduced the class)

And one instance of #1 that no code guard can see: **BUG-400 — the entire repo, including
`knowledge pipeline/maxwell.db`, sits inside a Dropbox File Provider domain.** `com.dropbox.attrs` is on
`CONSTITUTION.md`, `config/decisions.yaml` and the served SQLite store; two conflict copies of a stage log
already sit in a pipeline directory. C3 ("all data and compute remain local") is currently falsified by the
filesystem, not by intent — and out-of-band sync is a writer-of-record violation at the OS level, which also
explains BUG-443. This is the highest structural risk in the register and it is not a code bug.

---

## 4. Recommendation — four invariants, introduced at the point of use

Ordered by leverage per unit of change. Each is an *invariant + one engine*, never a per-bug patch.

**I1 — Writer-of-record with an ownership partition.**
Declare `config/artifact_ownership.yaml`: per artifact — path (RELATIVE-ONLY, D-337), mutability class
(`immutable` | `append-only` | `derived_regenerable` | `human_authored`), the **owned** key/column set, the
writer-of-record, backup policy. Then ONE library, `scripts/lib/write_guard.py`, with a single entry point
(`write_artifact(path, rows, owned_keys, mode)`) that: backs up byte-exact → refuses if any **non-owned**
cell would change → `tempfile`→`fsync`→`os.replace` → re-measures post-write → appends to a mutation journal.
The two correct scripts already in the repo become the *specification*, not the exception.
Migration is **shrink-only**: a checked-in `grandfathered_writers` list (the 156) that may only shrink; a new
writer that does not use the guard is RED. This makes BUG-478/443/433/406/460 unrepresentable rather than
policed.
*Immediate use:* the BUG-326 repair (403 + 147 + 703 cells) is exactly this shape — it should be the first
script to adopt I1, which also discharges the standing "R5 review before `--apply`" rule.

**I2 — Fingerprint the handoff, not the path.**
Stage handoffs become content-addressed: each stage writes `objects/<sha256>` plus a pointer; consumers read
the pointer and *assert* the sha. In-place mutation then cannot happen silently — it produces a new object
and an un-moved pointer, which is detectable. Same rule for derived stores: `vec_*` carries a **generation
id**, and the completeness check becomes a rowid-level join invariant, not a COUNT (BUG-394's root; a count
printed READY while half the index was dead).
*Immediate use:* before the S5 re-verify decision (BUG-376) and before the next `stage6` write.

**I3 — One reconciliation engine (the drift-aware surface).**
Declare `config/reconciliation.yaml`: for each declared object, `{declares: <yaml path#key>, about:
<artifact>, checks: [consumer_exists, count_matches, enum_matches, digest_current, key_present, no_orphan,
path_resolves]}`. ONE engine, `scripts/reconcile.py`, evaluates each check by re-deriving from the
declaration **and** the artifact independently — never from another rail's output — and emits
`governance/RECONCILIATION.json` with a tri-state per object (`ok` / `drift` / `owner_owed`), following the
BUG-457 convention (2 = owner-owed is loud, not fatal).
Two meta-rails make it self-enforcing:
- **cover:** every declared object that lacks a reconciliation entry is RED;
- **reach:** every `scripts/check_*.py` / `verify_*.py` that declares a contract but is invoked by no recipe
  is RED (this closes BUG-482 today and the class permanently).
This is the single artifact that makes the system *situation-aware*: one command answers "where does
declaration disagree with reality, right now?", instead of thirty scripts answering thirty questions if
someone remembers to run them.

**I4 — Evidence envelope for every number, and a known-answer control for every instrument.**
`scripts/lib/measure.py::emit_metric(name, value, population, denominator, ruler_sha, code_sha, ci=None)`.
A number without an envelope is not a measurement; a rail rejects an un-enveloped figure in a governance
document. And, generalising the D-374 bar that was applied to the claim-shape gate: **no instrument may
produce a verdict until it has a confusion matrix on a sealed known-answer control set** (positive *and*
negative items, declared *before* the run). That single rule is what would have stopped BUG-305, BUG-299 and
BUG-480 at the door, and it is precisely what makes a label *citable* — the precondition for the knowledge
layer being a pillar.
*Immediate use:* the R3 held-out run is an adoption decision. Under I4 it cannot be decided by a bare number.

**Register hygiene (small, urgent, and cheap).** Make a divergence between the last header's state and an
explicit body `Status:` field **RED**, not silent — one fact in one place, with the other place made loud.
Closes BUG-481 and prevents its recurrence. Under I3 this is simply another reconciliation entry.

---

## 5. How this serves the short-term session goals and the long-term mission

**Short-term (session):** three touchpoints, no big-bang refactor.
1. **BUG-326 repair** → adopt I1 for that one script. The repair becomes auditable, and the R5 review rule
   gets teeth.
2. **R3 held-out run** → adopt I4 for its numbers. An adoption decision is exactly the case where a bare
   number must not be able to decide.
3. **Depth panel (D-397/D-396)** → adopt I3's entry for the depth panel + wire BUG-482's meta-rail. "5
   declared raters, 3 run" becomes permanently visible instead of arriving as BUG-476.
None of these blocks the other work, and each retires a bug class at the moment that class is touched.

**Long-term (mission).** The mission needs labels that are *foundations* — citable by skills, orchestration
and later products. Three properties are prerequisites, and they map one-to-one onto I1/I3/I4:
- **Q1 Citable** — every label carries provenance (ruler, generation, instrument) and the instrument has a
  measured known-answer performance. → I2 + I4.
- **Q2 Sovereign** — the store is local, single-writer, and no out-of-band writer can alter it. Today this is
  false at the filesystem level (BUG-400). → I1 + the Dropbox owner gate.
- **Q3 Drift-proof** — "declaration vs reality" is a standing, regenerated, machine-readable answer rather
  than a hope. → I3.

RC-5 is the one that must be fixed *first* in spirit, because it is the only family that corrupts the
foundation itself. RC-1..RC-4 lose work; RC-5 ships wrong knowledge with a green rail attached.

---

## 6. What could go wrong with this recommendation (stated honestly)

- **The 31st bespoke script.** If `reconciliation.yaml` is hand-maintained per object, I3 becomes another
  thing to remember. Its entries must be **generated** from the declarations themselves, with
  `config/reconciliation.yaml` holding only the *check kinds* and exceptions.
- **Shrink-only lists rot.** `grandfathered_writers` must have a rail that fails if it grows and reports its
  size every run; otherwise it is a permanent amnesty.
- **Adoption cost is real.** I1 touches 156 scripts eventually. That is why migration must be shrink-only and
  driven by the point of use, never by a sweep.
- **I4 will invalidate numbers already in use.** Some ratified figures are legacy (BUG-391). The envelope
  makes that visible, which is the point — but it will feel like regression for a pass.
- **Everything above is a design, not a measurement.** I have not run any of it. The one thing measured this
  pass is the audit itself: 8 phantom-open ids, 3 unwired checks, 156 write-sites, and a rail that certifies
  its own parser.

---

## 7. Next critical steps

**Bugs**
1. BUG-482 (MED) — one meta-rail: uninvoked `check_*`/`verify_*` → RED. Closes the class, wires the D-397 rail.
2. BUG-481 (MED) — header/body closure divergence → RED. Restores the register as a signal (116 → ≤108).
3. BUG-478 root (HIGH, `scripts/**`, owner-gated) — guard or delete the workbook-write branch in
   `cross_examine_anchor_axes.py`; the class fix is I1.
4. BUG-400 (HIGH — not a code bug) — the repo is Dropbox-replicated, C3 falsified by the filesystem, conflict
   copies already present. Owner gate: exclude from sync or move out of `~/Library/CloudStorage`.
5. BUG-376 / BUG-341 / BUG-433 — the mutable-declared-input class; root fix is I2.

**Tasks**
1. Re-run `just health-deep` as the post-edit control (D-390: the aggregate rail runs rails, not the suite).
2. Adopt I1 in the BUG-326 repair, I4 for the R3 numbers, I3 for the depth panel (three touchpoints).
3. BUG-451/BUG-452 buglog status updates to reflect D-395/D-399 (FORM demoted, catch rate 1/7; FORM
   agreement not reportable from F11 without a declared parse — BUG-477).

**Decisions**
1. D-400 — "no instrument may decide until it has a confusion matrix on a sealed known-answer control"
   (generalises D-374; the RC-5 gate).
2. D-401 — "every artifact has a declared owner-of-record, and a writer may not change a cell it does not
   own" (the RC-1 gate).
3. D-402 — "a rail may not take its evidence from the same source as the artifact it checks" (the RC-3 gate).
4. D-403 — "stage handoffs are content-addressed; a hash claim never points at a mutable path" (the RC-2/
   BUG-376 gate).
