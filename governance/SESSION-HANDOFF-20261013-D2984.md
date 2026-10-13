# SESSION HANDOFF — 2026-10-13 · D-2984 (a claim in a face is JOINED or it DATES ITSELF) + BUG-760 FIXED

**Trigger:** the owner read `DECISION-LOG.md` and said it out loud — *"seems like the done, fixed, resolved task
bugs, decisions are still on top so my instruction haven't delivered."* Measured, the owner was right, and the
measurement was worse than the complaint: the faces had been telling the register's falsehoods to the only reader
who acts on them, while the rail that owns the faces reported agreement.

## 1. The leverage call

The top item was NOT any of the five inherited ladder faults (T-114) and NOT T-101. It was that **the artifact the
owner READS could state a false register fact and nothing joined it.** Every other measurement in Maxwell OS is
certified against the register; if the register's own face can lie, then the owner's channel to truth is
unverified — and the derived block sitting 20 lines above the lie made it *worse*, because a checked block
certifies an unchecked one by proximity. This is BUG-759 one level up: a report read as a verdict (BUG-573) became
a face read as the register. Fixed the instrument first, then the faces.

## 2. Rule → mechanism → SEEN

| # | Rule | Mechanism (ONE home) | SEEN |
|---|---|---|---|
| 1 | A live-claim LABEL has ONE home (the derived block); it must LEAD the line | `LIVE_LABEL_RE` in `scripts/check_governance_faces.py` | 2 faults (MTR:60, :77); the BUG-669 entry that merely DISCUSSES the label stays quiet |
| 2 | A LIVE census marker may not stand in a region declared "NOT a register" | same rail, no date exemption | 2 faults (MTR:61, DECISION-LOG:62) |
| 3 | A decision ROW is JOINED to `config/decisions.yaml`, or its SECTION dates itself | `DEC_ROW_RE` + `claimed_state()` (the LAST bare state cell → 3-col and 4-col forms, one parser) | 3 faults (DECISION-LOG:195, :196, :247) |
| 4 | The derived `highest OPEN` field states its moment ON ITS OWN LINE | `HIGHEST_OPEN_RE` + `MOMENT_TOKEN_RE` | 3 faults (MTR:61, MTR:2211, DECISION-LOG:3148, buglog:9244) |
| 5 | A present-tense "BUG-N is OPEN" assertion joins unless its ENTRY dates itself | `OPEN_ASSERT_RE` (adjacent id+claim) | 0 today — all 9 buglog claims sit under dated entries, so **no history byte was rewritten** |
| 6 | Every fault NAMES its repair (D-405) | the message carries the remedy | `test_every_fault_names_its_repair` |
| 7 | The rule is mutation-locked (D-2676 iv) | `a_decision_row_that_contradicts_the_register_is_load_bearing`, floor 33 → 34 | gate: 33 rules SEEN to red, 1 negative control green |

## 3. Measurement of record

- **Baseline (before):** 8 faults — DECISION-LOG 5, MASTER-TASK-REGISTER 3, buglog **0**.
- **After the repairs:** `check_governance_faces` rc=0, `--selftest` **22/22** known answers (11 new, both directions).
- **Repairs: 8 lines.** Two snapshots relabelled (they called themselves the live face), one census marker demoted
  to a dated snapshot, one section heading dated 2026-10-03 (from `git blame` of its own rows) plus an appended
  CORRECTION naming the two decisions the register has since moved to RESOLVED, one row re-cited D2537 → **D-2979**
  (the record that carries the decision), and three derived fields given the word "then".
- **The rule caught its own author:** the first draft of the BUG-760 entry quoted the defect without a moment, and
  the rail went red on it — the detector firing on the person who wrote it is the evidence that it is real.

## 4. Forensic audit before landing (blast radius)

- **Who reads these regions:** `check_governance_faces`, `bug_status.py`, `gov_sync.py`, `check_register_divergence`,
  `check_session_plan`, `recompute_decision_summary`, `verify_handoffs`, `pipeline/doc_guard`. All four re-verified rc=0
  after the edits; `verify_handoffs` still 6 paths / 13 digests / 3 revisions.
- **The derived blocks are ABOVE the marker in all three faces** — the claim surface never judges its own output.
  Now an enforced invariant (INV-8) with a test, not an assumption.
- **Cascade found and resolved (the audit paying for itself):** re-citing D2537 made
  `check_decision_membership` red — *"D2537 is pinned as a legacy orphan and DECISION-LOG.md no longer names it: a
  STALE declaration (D-405)"*. Its `id_patterns` recognise only table rows and headings, so a prose mention does
  not count. The pin's own note prescribes the shrink, and the list is shrink-only by design → D2537 retired from
  `membership.legacy_orphan_ids` with the reason recorded in the block (4 pinned orphans now, 0 faults, 12/12 controls).
- **Order is load-bearing** (INV-8): the marker must not precede the block, or the rail would fire on its own bytes.
- **buglog is append-only and needed ZERO repairs** — the scope rule (entry date for prose) is what bought that.

## 5. Governance sync (the agreed clean order)

- **Minted:** D-2984 — total **1112**, stamp `e090da935be729b6`, census `config/decisions_summary.json`. Mint file
  `governance/decisions_mint_D2984.yaml` (the record; files: 10).
- **Filed:** BUG-760 (HIGH — FIXED by D-2984) and BUG-761 (MED — OPEN, the structural residual) → bug_status
  re-derived **OPEN 185 / CLOSED 340 of 525**; a row added to the buglog OPEN — SHOULD tier and a CLOSED section
  appended (append-only preserved).
- **Task:** T-115 (SHOULD, open) — decide what a HAND TIER means inside the declared history region. Register now
  **15 open tasks** (MUST 4 / SHOULD 8 / WORTH 3; gate 1).
- **Faces re-derived:** `gov_sync.py --apply` → 4 faces equal their re-derivation (1112 decisions / 525 bugs / 15
  open tasks); `--check` rc=0.
- **Declared:** `scripts/check_governance_faces.py[: --selftest] = fatal` in `config/rail_registry.yaml`
  (rail registry rc=0: 129 invocations, 82 rails, 9 writers, guards consistent).
- **Superseded/closed bookkeeping:** BUG-760 FIXED; the D2537 legacy-orphan pin RETIRED (with reason, in place);
  T-115 opened so BUG-761 has a route; the justfile line's stub citation `D-NEW` replaced by `D-2984`.

## 6. Honest limits

1. **History is exempt by design** — a stale claim inside a dated entry is not a fault. The rule polices
   contradictions and unmoored claims, not every aged sentence.
2. **The scope rule is a declared convention** (section heading for rows, entry for prose). A face that reorganizes
   its history needs the rule updated, not silently reinterpreted.
3. **The rail cannot judge whether a dated claim was TRUE at its moment.** Unmeasured, and it stays unmeasured.
4. **BUG-761 stands:** the hand tier sections still live inside the region declared to be history (the marker sits
   after the derived block, inside the first tier), so a tier LABEL can restate a drifted count
   (`ACTIVE — in effect (477)` vs 565) — deliberately not fixed here, because moving the marker would silence the
   joins that now keep those rows honest.
5. **Two spellings of one id form** in the register (691 bare `D2622`, 420 dashed `D-2983`, 0 collisions under this
   normalisation). Canonicalising the spelling is D-2693's licence, not this decision's.
6. **No claim that the register is now true** — only that its faces may no longer assert what it does not say.

## 7. Delegation (honest)

No ad-hoc delegate: this was a single-file rule plus its spec, contract and repairs, and splitting it would have
created two writers of one rule (the D-2983 reasoning, unchanged). The ONE local-LLM call was the ratified R5
reviewer via `scripts/r5_review_gate.py --file scripts/check_governance_faces.py`, and its verdict is read in-line
below, not assumed.

## 8. Next critical step (bug / task / decision — in order)

1. **T-115** (SHOULD) — BUG-761: decide what a hand tier means inside the declared history region, and join the
   tier labels' counts. Cheap, contained, and it closes the last place a face can restate a drifted number.
2. **T-114** (SHOULD) — discharge the five recorded ladder faults, every shrink-only ceiling LOWERED, re-measuring
   after each wave so `temp/ladder_receipt.json` matches the repaired ladder.
3. **T-101** (MUST, human gate) — harden the retrieval golden set: recall@10 is saturated at 1.000, so MRR (0.919)
   is the only live gate; the anchors are owner-signed.
4. **T-104** (MUST) — 125 open bugs still carry no severity token, so the register cannot be ordered by criticality.
