# SESSION HANDOFF — 2026-10-13 · D-2985 (the LIVE region is a claim surface too) + BUG-762/763/764 FIXED

**Act.** The mirror of D-2984. D-2984 policed everything BELOW the `GOV-HISTORY:START` marker; the region ABOVE it
— the part the owner actually opens — had no join at all, and it was wrong three ways at once. The one-sentence
rule: **a claim in the LIVE region joins a register too — and where the register says only the OWNER can move it,
the face says so, and says it FIRST.**

## 1. Why this act (the leverage call)

The owner's complaint, restated verbatim in this session: *"seems like the done, fixed, resolved task/bugs/decisions
are still on top so my instruction hasn't delivered"* and *"DID FUCKING MANAGE TO FIX?? in mtr and decision.log"*.
The previous session answered the HISTORY region (D-2984). The complaint was still literally true, because the
top of both files was still wrong in three independent ways, and every one of them is on the first screen:

| what the owner saw | what was actually true |
|---|---|
| `## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived 2026-10-03 — the live face; history below)` | a HAND heading, 10 days stale, claiming to be the live index while the derived block 2 lines below claimed the same title |
| R-1 / T-101 / T-103 / T-104 at the top, all `state: open` | one standing RULE that never closes, two tasks gated on an owner word, one actionable task — sorted by priority alone, so the actionable one was last |
| `CRITICAL 7 · HIGH 36 · MED 57 · LOW 30 · UNLABELLED 125 … of 185 open` | parts summing to **255** for a population of 185 (88 closed counted open, 18 open invisible), and three answers to one question: 125 / 108 / **101** |

Every other measurement in Maxwell OS is certified against the register. If the register cannot carry WHO must act,
the owner's obligations and the agent's next steps are indistinguishable — which is the complaint, mechanically.

## 2. The rule → mechanism → SEEN table

| limb | mechanism | SEEN (control) |
|---|---|---|
| (i) the live-claim LABEL has ONE home | `LIVE_LABEL_RE` widened to see a label behind a heading marker, an icon and emphasis, still requiring it to LEAD the line | `check_governance_faces --selftest` 25 → **31/31** (the new control fires on the exact heading that was invisible) |
| (ii) a file a live claim NAMES must exist | `LIVE_PATH_RE` + a resolve check over the live region | 2 named controls, both directions |
| (iii) WHO must act is DECLARED and the face LEADS with the OWNER LANE | `mover: owner\|pipeline` REQUIRED (`task_faults`, fail-closed C16); `R-` ids are `state: rule`; `state: gate` retired; `render_block`/`render_seed_status` render the lane (label declared once in `config/gov_sync.yaml`) | `gov_sync --selftest` 13 → **19 known answers**, 9 of them the register's own schema |
| (iv) one home per count, and OPEN-ness is the census's | the severity population IS the census's open ids, severity read at ANY hash depth, the parts must partition; a title/`why` may not restate a count, `evidence` must date its measurement; the census re-cut is SCOPED to the live region | 3 new mutation locks (`the_live_region_label_limb`, `the_mover_axis`, `the_census_recut_scope`), floor 34 → **37**, all three SEEN to red |

## 3. Measurement of record

- **Baseline faults:** the LIVE limbs reported **4** (one hand heading + the missing owner lane in three faces);
  the register reader **failed closed** on the new schema (1 fault: `T-113`'s undated evidence).
- **Repairs (all in place, nothing deleted):** 1 heading line; 16 register entries given a `mover`; `R-1`
  `open` → `rule`; `T-103` `gate` → `open` + `mover: owner`; 2 titles and 3 prose counts moved to the field that
  owns them; 2 SNAPSHOT lines repaired in place with the repair NAMED; 1 dangling citation corrected
  (`scripts/check_gov_sync.py` → `scripts/gov_sync.py --check`).
- **After:** `check_governance_faces` rc=0 (**31/31**, was 25) · `gov_sync --check` rc=0 (**19** named answers,
  was 13) · `check_rail_registry` rc=0 (both new pins held) · 21/21 spec contracts green ·
  faces render `OWNER LANE (3)` / `PIPELINE LANE (11)` / `STANDING RULES (1)` and
  `14 open tasks … OWNER-moved 3, pipeline-moved 11; 1 standing rule(s) never close` ·
  severity line now PARTITIONS: **CRITICAL 4 · HIGH 22 · MED 39 · LOW 19 · UNLABELLED 101 = 185** ·
  ceiling **LOWERED 125 → 101** (D-2644).
- **Register:** 1112 → **1113** decisions (stamp `a2bcb9e7201140fb`); bugs 525 → **528**, open **185**,
  closed 343; open tasks **14** + 1 standing rule.

## 4. Forensic audit (before the writes)

- **Readers of the changed surface:** `scripts/gov_sync.py` (writer + validator), `scripts/check_governance_faces.py`
  (the rail), `scripts/bug_status.py` (the bug census), `scripts/check_rail_registry.py` (the pins),
  `scripts/check_rail_mutations.py` (the locks), `scripts/recompute_decision_summary.py` (the mint),
  `scripts/check_session_plan.py` (the commit boundary). No reader parses the register-truth line's TASK half, so
  the new shape broke nothing — verified by running each rail.
- **Cascades found and handled:** (1) lowering `severity_grandfathered` touches the shrink-guard, so the new
  population was measured before the number moved; (2) retiring `state: gate` would have orphaned `T-103`, so the
  state was re-expressed (`mover: owner`) in the same change; (3) the re-cut scope fix changes what `--apply`
  writes, so it was covered by a control and a mutation before the faces were re-derived.
- **Blind spot found in the PREVIOUS act and closed here:** D-2984's label limb required the label to lead a line
  with NO heading marker — precisely the shape of the one line the owner opens the file on. Same class as the
  `DEC_ROW_RE` blind spot found in the D-2984 verification pass: the rule's SHAPE enumeration was incomplete, not
  its rule.
- **Conflicts resolved:** D-2981 ("every restatement is derived") vs the faces' declaration that everything below
  the marker is dating-only history — resolved in favour of the declaration, because the writer was making
  historical claims FALSE (R-D410). Recorded as BUG-764.
- **Deliberate non-actions:** the hand TIER sections below the marker stay (BUG-761/T-115: moving the marker would
  silence the D-2984 joins that keep those rows honest); the register's `why` field is policed only for
  census-shaped restatements (honest limit, below); no ceiling was raised anywhere.

## 5. Governance sync (the agreed order)

`config/gov_sync.yaml` declarations → `config/task_register.yaml` schema + repairs → `scripts/gov_sync.py` reader →
`scripts/check_governance_faces.py` LIVE limbs → specs + contracts → mutation locks → face repairs →
`gov_sync.py --apply` (4 faces re-derived: 1113 / 528 / 14) → buglog BUG-762/763/764 (append-only) →
`bug_status.py` (OPEN 185 / CLOSED 343 of 528) → mint D-2985 → `rail_registry` pins (`check_governance_faces`
fatal, `gov_sync --selftest` fatal) → justfile rationales → specs/README inventory (it named ONE spec while four
existed — the BUG-588 shape in the sandbox's own front door) → `CONTEXT_INDEX` §7 (the human gate register now
points at the DERIVED owner lane instead of hand-listing current obligations: two homes for one fact is D-2642,
and the hand one is the one that goes stale).

## 6. HONEST LIMITS

1. The `why` field is policed only for CENSUS-SHAPED restatements (`open = N`, `N bugs|tasks|decisions|rows`). A
   count phrased some other way in long-form prose can still go stale. The PRINTED surface (`title`, `evidence`)
   is fully covered; the register's prose is not.
2. `T-103` keeps "the label re-derivation debt" in its title, and the OWNER LANE will keep naming it until the
   owner rules. That is the lane working, not a defect.
3. The hand TIER sections inside the declared-history region are untouched (T-115).
4. Path citations in the REGISTER's own header comments are not automatically policed; this instance was repaired
   and the LIVE-region rule covers the faces, but a general register-citation join is not landed.
5. **Spec ordering:** D-2978 prefers spec-BEFORE-code. The invariant set was designed before the implementation,
   but the two spec files were WRITTEN after it, in the same act. Recorded rather than claimed.

## 7. Delegation

No ad-hoc delegate this run: the act is one rule with two writers (the register reader and the faces rail) plus
its contracts, and splitting it across delegates would have created two writers of one rule (the D-2984 lesson).
The local-LLM call owed here is the ratified **R5 review gate** on the two changed scripts
(`scripts/r5_review_gate.py --file …`), run after the rails are green.

## 8. Next critical steps (in order)

1. **T-115 (SHOULD)** — BUG-761: what a HAND TIER means inside the region the faces declare to be history
   (relabel a dated snapshot and drop it from the claim surface, or promote it into the derived block), and join
   the tier labels' counts (`## 🟢 ACTIVE — in effect (477)` vs 565 ACTIVE).
2. **T-114 (SHOULD)** — discharge the five inherited ladder faults, ceilings LOWERED, re-measured per wave.
3. **T-104 (MUST, now measurable)** — the severity backfill runs against the CORRECTED population
   (101 unlabelled of 185 open; the old "108" was one of three wrong answers).
4. **T-101 (MUST, human gate)** — unchanged and still the only unblocker that needs the owner's hand.

## 9. What ONLY THE OWNER can move (the lane this act created)

The faces now print this block first, at the top of MTR, DECISION-LOG and buglog, and `session_seed.yaml` loads it
at boot. TODAY it names three:

- **T-101 (MUST)** — sign the retrieval golden anchors: `governance/golden_reanchor_candidates_20261011.csv`,
  fill only `decision` (`keep`/`replace`/`drop`/`add`) and `owner_signature`, then `--apply` and re-run the
  benchmark. SUCCESS SIGNAL = recall@10 drops BELOW 1.000 (it is saturated today on 29 single-answer goldens).
- **T-103 (MUST)** — the owner word that licenses the store write for the label re-derivation debt.
- **T-107 (SHOULD)** — the owner word on the MCP payload schema (whether `borp_score` / `feedback_score` stay
  advertised to agents).
