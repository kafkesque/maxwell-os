# HANDOFF — 2026-10-23 (session 2: BUG-966 closed; T-195 manual task un-blocked)

> To continue in a fresh session: say **"continue"** (or paste the `## CONTINUE HERE` block).
> Every number below was READ from disk on 2026-10-23 ~15:10 +02:00 — not remembered.

## STATE (resolved from disk)

- **HEAD** `a6b3d06` — `chore(admission): track evidence receipts from the 2026-10-23 13:06 admission apply`
  (parent `8541358` = `fix(BUG-966)`). Working tree **clean**.
- `gov_sync --check`: **GREEN** — `ok gov-sync: 4 face(s) equal (1259 decisions / 738 bugs / 58 open tasks)`.
- Bugs: **OPEN 258 / CLOSED 480 of 738** (BUG-966 flipped MED→closed this session).
- Recall rail: **CLEAN** — concept 44/44 = 1.0, expectation 418/418 = 1.0, tier B 0 proposed.
- Commit gates all green (repo-integrity, recalibration pins 0 RED, declaration consumers 11/14, session plan declared).

## WHAT LANDED THIS SESSION (2 commits)

| commit | what |
|---|---|
| `8541358` | **BUG-966 CLOSED** — the two governance faces that asserted `phase0_idempotency.py --all` was "unexecuted" were ALREADY corrected by append (the BUG-966 buglog entry + the MARKET_RESEARCH `CORRECTION 2026-10-23` block). The only remaining action was the status flip `OPEN→FIXED`, done here. A forensic sweep for the defect class (false "not executed"/"unexecuted" claims) found **no other live face** needing correction. Regenerated `bug_status.md/.json` + `gov_sync --apply`. |
| `a6b3d06` | Tracked two untracked admission evidence receipts (`ADMISSION_APPLIED/DISPOSITION_20261023T130635Z.jsonl`): a single `Proposal.docx` row that FAILED S0 conversion (markdown below the 100-byte floor) and was quarantined. |

## ⚠️ OWNER-ONLY MANUAL TASKS (D-3100) — the two open owner-lane tasks, now with a WORKING command

### 1. T-195 — pick the pilot sources (the ONLY blocking owner word)

**The handoff you got before had a BROKEN command** (`r['source_id']` → `KeyError`). The golden's rows key on
`sources` (a **list** per row), not a flat `source_id`. The corrected command that WORKS:

```bash
python3 -c "import json; d=json.load(open('governance/EXTRACTION_RECALL_GOLDEN_20261023.json')); print(len({s for r in d['rows'] for s in r['sources']})), 'sources'; print('\n'.join(sorted({s for r in d['rows'] for s in r['sources']})))"
```
*Expected:* `338 sources` then 338 hex ids. *If it errors:* re-run `python3 scripts/check_extraction_recall.py --build-golden --apply` first.

**But you don't need to read 338 hex ids.** A title map was built this session (335/338 mapped). The top sources
by certified-concept density (3 concepts each) are, with a **recommended diverse pilot set of 3**:

| pick? | source_id | author | title | certified concepts |
|---|---|---|---|---|
| ✅ rec | `f8f802e878304781` | Roberto Infante | AI Agents and Applications With LangChain, LangGraph, and MCP | 3 |
| ✅ rec | `b51204ce6c6a9950` | Richard Rumelt | Good Strategy/Bad Strategy | 3 |
| ✅ rec | `f988150fe424aa75` | Golan Levin, Tega Brain | Code as Creative Medium | 3 |
| alt | `26d9bd396aa6df4a` | Rob Thomas et al. | AI Value Creators | 3 |
| alt | `f75496d7c480ea49` | Lakshmanan & Hapke | Generative AI Design Patterns | 3 |

**Your whole "word" is one reply**: either *"use your 3 recommended sources"* or a list of 2–5 source_ids from the
table above. Nothing else is required.

After you give the word, the agent writes **T-195 step (b)** — the proposer: a local model emits ADVISORY candidate
concepts per source into the `tier_b_sheet` JSONL. You then rule each candidate MATCH/NONE. **Tier B is never
auto-certified** (D-2898).

### 2. T-183 — the next admission cycle (recurring)

The evidence committed in `a6b3d06` shows an admission apply already ran (13:06) and quarantined one `Proposal.docx`.
Confirm whether you still need another tranche, and if so run (in order):

```bash
just admit-plan                       # expect "candidates N"
just admit-sign "<your name>"         # expect a NEW ADMISSION_ACCEPTED_<ts>.yaml
just admit-apply --limit 10           # expect "DECIDED … applied" and no traceback
```

## NEXT CRITICAL STEPS (agent-side, in leverage order)

1. **T-195 step (b)** — the tier-B proposer script. **Blocked only on the owner word in §1.** Once you have it, this
   is the highest-leverage unblocked work (it activates the recall-completeness arm).
2. **BUG-972 (LOW)** — `r5_code_review.py --out <path outside repo>` writes the verdict then dies with a traceback.
   Same deterministic-fix shape as BUG-965 proved; cheap red-loop (`--selftest` first, D-3036).
3. **BUG-967 (LOW)** — the Phase 0 receipt reports S0.5 "identical: True" over two EMPTY sets (vacuous pass). Fix at
   the instrument's next run, NOT by re-running `--all` (would overwrite the arms — BUG-966's second harm).
4. **BUG-964 (LOW)** — gpt-oss-20b same-row verdict flip (R111): the flip is REAL but RARE (1/40 = 2.5%), gpt-oss
   against ITSELF. Candidate-set identity between the two runs is the actual unverified defect.

## HIDDEN CONFLICTS / FUTURE TAX (found this session, flagged for the next implementer)

1. **T-195(b) concept-key folding MUST reuse `pipeline/dedup_identity.py`.** The golden keys on
   `concept_key = sha256(sorted stopword-filtered tokens of folded name)` (D-3118 Phase A). If the proposer hashes a
   raw `name` with a naive sha256, the concept_key won't match the golden and the rail reports false "omitted"
   concepts. **Do not re-implement folding** — import it.
2. **T-195(b) model choice is a decision, not a default.** The proposer is advisory open-ended generation (D-2898:
   no LLM auto-certification). Per D-2549 routing, open-ended generation is NOT a delegate loop — use a single-shot
   local model (Qwen3-Coder-30B via curl one-shot, or the OMLX classifier for a constrained candidate list). Decide
   and record it in `config/extraction_recall.yaml` (C12: no hardcoded model name in the script).
3. **BUG-966 residual (accepted, not a defect):** the false claim in `buglog.md` BUG-956 UPDATE #4 (`…has NOT been
   executed`) is corrected by the later BUG-966 entry, NOT in place — buglog is append-only by convention. A reader
   landing on that one line is still potentially misled. If the owner wants a local strike-through pointer, that is
   an owner decision to relax append-only; the correction itself is already recorded.

## CONTINUE HERE

```bash
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
git log --oneline -1                     # expect a6b3d06
python3 scripts/gov_sync.py --check      # expect "ok gov-sync: ... 4 face(s) equal"
python3 scripts/check_extraction_recall.py --check   # expect CLEAN 44/44, 418/418
```
Then either (a) begin **T-195 step (b)** if the owner gave the pilot-source word in §1, or (b) begin **BUG-972**
(red-loop → fix → selftest → R5 gemma review → gov sync → commit).
