# HANDOFF — 2026-10-23 (T-195 step (b) landed; owner word consumed; next = rule 45 tier-B candidates)

> To continue: say **"continue"** (or paste the `## CONTINUE HERE` block).
> Every number below was READ from disk on 2026-10-23 ~15:25 +02:00 — not remembered.

## STATE (resolved from disk)

- **HEAD** `8d2a0c2` — `chore(gov): sync T-195 step (b) landing into task register + derived faces`. Tree **clean**.
- `gov_sync --check`: **GREEN** — `ok gov-sync: 4 face(s) equal (1259 decisions / 738 bugs / 58 open tasks)`.
- Bugs: **OPEN 258 / CLOSED 480 of 738** (CRITICAL 4 · HIGH 40 · MED 82 · LOW 31 · UNLABELLED 101).
- Recall rail: tier-A **CLEAN** (44/44, 418/418) · tier-B **45 proposed / 0 present** (advisory, never floored, never auto-certified).
- T-195 register entry now leads with `STEP (b) DONE` (owner word consumed); next owner act = rule MATCH/NONE.

## WHAT LANDED THIS SESSION (3 commits)

| commit | what |
|---|---|
| `4c9d805` | **T-195 step (b)** — `scripts/propose_tier_b.py` (reuses `pipeline/dedup_identity.concept_key` + `book_metadata.compute_source_id`; crash-safe JSONL; `--selftest`/`--dry-run`/run), `config/extraction_recall.yaml` proposer block (pilot_sources, `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` generator, window bounds), `governance/EXTRACTION_RECALL_TIER_B_20261023.jsonl` (45 advisory candidates = 15/source), regenerated golden + report, and the session-plan `may_touch` grant for the tier-B sheet path (D-342 / BUG-548: the record is not the rule). |
| `41e1197` | Report `pipeline_commit` stamp refreshed post-land (provenance points at `4c9d805`). |
| `8d2a0c2` | Task-register sync: T-195 `evidence` + `gate` updated; `gov_sync --apply` re-cut the MTR/DECISION-LOG/buglog census lines + MUTATION_JOURNAL receipts. |

## ⚠️ OWNER-ONLY MANUAL TASK (D-3100) — rule the 45 tier-B candidates

The proposer emitted **45 advisory candidate concepts** into `governance/EXTRACTION_RECALL_TIER_B_20261023.jsonl`
(one JSON line each: `source_id`, `name`, `rationale`). They are **advisory only** — never floored, never
auto-certified (D-2898). Your whole word is a MATCH/NONE ruling per candidate.

### 1. Read the candidates

```bash
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
python3 -c "
import json
rows = [json.loads(l) for l in open('governance/EXTRACTION_RECALL_TIER_B_20261023.jsonl')]
for i, r in enumerate(rows, 1):
    print(f\"{i:2}. [{r['source_id']}] {r['name']}  —  {r.get('rationale','')[:80]}\")
print('total', len(rows))
"
```
*Expected:* 45 lines (15 each for `f8f802e878304781` Infante / `b51204ce6c6a9950` Rumelt / `f988150fe424aa75` Levin+Brain).
*If it errors:* the file is committed; `git show HEAD:governance/EXTRACTION_RECALL_TIER_B_20261023.jsonl` re-reads it.

### 2. Rule each candidate MATCH / NONE

Tier-B rows that you rule **MATCH** enter the **same** golden through the **same** rail — there is no second
instrument. The rail keys on `(source_id, concept_key)`; `concept_key = sha256(sorted stopword-filtered tokens of
folded name)` is already minted per row by `scripts/propose_tier_b.py`, so a MATCH you record by `(source_id, name)`
will fold to the same key. Record your rulings in whatever sheet you prefer (the same vocabulary the 208-row
re-anchor used: `suggested_*` advisory, `owner_ruling_*` authoritative, D-2658). **Nothing is certified until you
rule it.**

### 3. After ruling, fold certified tier-B rows into the golden and re-check

```bash
python3 scripts/check_extraction_recall.py --build-golden --apply   # expect tier_b_rows to move 0 -> MATCHed count
python3 scripts/check_extraction_recall.py --check                  # expect tier-A still CLEAN; tier-B present-count rises
python3 scripts/gov_sync.py --check                                 # expect green
```

## NEXT CRITICAL STEPS (in strategic-leverage order)

1. **T-195 step (c) — OWNER ruling of the 45 tier-B candidates** (manual, above). Highest leverage: it is the only
   thing standing between the loss rail (T-194) and a measurable *completeness* claim (D-3130). Until then tier-B
   stays `45 proposed / 0 present` and the rail correctly reports omissions as advisory, never as loss.
2. **The 4 open CRITICAL bugs** (agent-side, in the register as the top severity bucket): **BUG-709** (S5 checkpoint
   S4-derived labels stale → silent REGRESS of ratified labels on commit), **BUG-710** (D2511 retrieval gate INERT —
   golden anchored to superseded run, missing fail-loud precondition), **BUG-712** (content_type routing collapse —
   6/8 declared primitives produce ZERO output), **BUG-713** (superseded runs still in store AND KNN index). These are
   the real correctness- and recall-bearing work; they predate T-195 and are each a red-loop-first (D-3036) job.
3. **BUG-972 (LOW)** — `r5_code_review.py --out <path outside repo>` writes the verdict then dies with a traceback.
   Same deterministic-fix shape as BUG-965 proved; cheap red-loop (`--selftest` first, D-3036).
4. **BUG-967 (LOW)** — Phase 0 receipt reports S0.5 `identical: True` over two EMPTY sets (vacuous pass). Fix at the
   instrument's next run, NOT by re-running `--all` (would overwrite the arms — BUG-966's second harm).
5. **BUG-964 (LOW)** — gpt-oss-20b same-row verdict flip (R111): the flip is real but rare (1/40 = 2.5%); the actual
   unverified defect is candidate-set identity between the two runs.

## HIDDEN CONFLICTS / FUTURE TAX (verified this session, carried forward)

1. **`pipeline_commit` stamp churn on the derived report.** `check_extraction_recall.py --check` writes the report
   with `pipeline_commit` = current HEAD, so the report is always one commit "stale" relative to the commit that
   contains it. Harmless (not validated by `just health`; provenance-only), but every recall `--check` dirties the
   tree. If it ever wants to settle, the stamp should be pinned to the commit that produced the *data* (golden + DB),
   not re-stamped on every read — a decision, not a patch.
2. **T-195(b) model is recorded, not a new decision.** Qwen3-Coder-30B is the established generator family (MODELS
   block + `stage2_extract`), and the proposer is single-shot advisory generation (D-2549 generator routing), so no
   decision mint was required — the name lives in `config/extraction_recall.yaml#proposer.model` (C12), never hardcoded.
3. **BUG-709 dual heading (OPEN then CLOSED) in the append-only buglog** means the census counts it as CRITICAL-open
   via its FIRST heading. This is the append-only-log status-ambiguity class; if the owner wants the register to read
   it as closed, that is a buglog-status-flag act, not a silent edit.

## CONTINUE HERE

```bash
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
git log --oneline -1                     # expect 8d2a0c2
python3 scripts/gov_sync.py --check      # expect "ok gov-sync: ... 4 face(s) equal"
python3 scripts/check_extraction_recall.py --check   # expect tier-A CLEAN 44/44, 418/418; tier-B 45 proposed / 0 present
```
Then either (a) the owner rules the 45 candidates (T-195 step c, §OWNER-ONLY above), or (b) begin **BUG-709/710/712/713**
or the deterministic **BUG-972** (red-loop → fix → selftest → R5 gemma review → gov sync → commit).
