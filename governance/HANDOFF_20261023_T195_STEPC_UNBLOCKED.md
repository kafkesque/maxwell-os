# HANDOFF — 2026-10-23 (T-195 step (c) UNBLOCKED; BUG-974 closed)

> To continue: say **"continue"**. Every number below was READ from disk on 2026-10-23 ~15:45 +02:00.

## THE ONE THING YOU MUST KNOW

Your `just`/`--build-golden --apply` + `--check` run **did NOT rule anything** — it only refreshed the
`pipeline_commit` stamp. The 45 tier-B candidates were still `PROPOSED-but-unruled` (0 MATCH, 0 NONE).

Worse: **step (c) was not actually executable as written.** The old instruction said "rule MATCH and it folds
through the same rail", but the rail (`read_certifications`) demanded a `owner_ruling_fb_id` that RESOLVES in the
store — and **0 of 45** tier-B candidates have a store fb_id (they are concepts the extractor OMITTED). So a MATCH
could not fold. This was **BUG-974**, discovered and fixed this session.

## WHAT LANDED THIS SESSION

- `config/extraction_recall.yaml#golden.tier_b_ruling_sheet` → `governance/EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl` (C12).
- `scripts/check_extraction_recall.py`: `load_tier_b_rulings()` reads owner MATCH/NONE rulings; `build_golden`
  folds MATCHed candidates into the **floored** set keyed by `(source_id, concept_key)` (D-3129) with an **empty**
  `fb_id_pointer` (no store row required — D-3130). `evaluate` reports `tier_b_matched` / `tier_b_ruled_none`.
- Selftest case 8 + a live smoke test proved the red loop: one MATCH on "The Kernel of Strategy" flipped the rail
  **44/44 → RED (44/45)**; reverting restored CLEAN.
- `governance/buglog.md` BUG-974 (MED, FIXED) + `bug_status` + `gov_sync --apply` re-cut (739 bugs / 58 open tasks).

## ⚠️ OWNER-ONLY MANUAL TASK (D-3100) — rule the 45 tier-B candidates

The ruling sheet is currently EMPTY (inert). To rule, you append one JSON line per candidate you decide.
A MATCH folds it in and, because the store omits it, the rail goes **RED** until that concept is EXTRACTED —
that RED is the completeness signal, not a failure.

### 1. Read the 45 candidates

```bash
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
python3 -c "
import json
rows = [json.loads(l) for l in open('governance/EXTRACTION_RECALL_TIER_B_20261023.jsonl')]
for i, r in enumerate(rows, 1):
    print(f\"{i:2}. [{r['source_id'][:8]}] {r['name']}  —  {r.get('rationale','')[:70]}\")
"
```
*Expected:* 45 lines. `f8f802e878304781` = Infante (LangChain/LangGraph/MCP), `b51204ce6c6a9950` = Rumelt
(Good Strategy/Bad Strategy), `f988150fe424aa75` = Levin+Brain (Code as Creative Medium).

### 2. Rule each candidate

Append one line per ruling to `governance/EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl`. Two forms:

```bash
# MATCH  -> this concept genuinely exists in that source; fold it in as a floor
echo '{"source_id": "b51204ce6c6a9950", "name": "The Kernel of Strategy", "owner_ruling_note": "MATCH"}' \
  >> governance/EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl

# NONE   -> reject it; keep it out of the golden
echo '{"source_id": "f8f802e878304781", "name": "LLM-Based Application Patterns", "owner_ruling_note": "NONE"}' \
  >> governance/EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl
```

*Exact rules:* `source_id` and `name` must match a proposed candidate; `owner_ruling_note` must be `MATCH` or
`NONE` (else the rail FAIL-CLOSES). Omit a candidate entirely = leave it advisory (still reported, not floored).

### 3. Rebuild + re-check

```bash
python3 scripts/check_extraction_recall.py --build-golden --apply   # MATCHed count folds in; expect 45 -> 45+N
python3 scripts/check_extraction_recall.py --check                  # RED if a MATCHed concept is still omitted
python3 scripts/gov_sync.py --check                                 # expect green
```

**Expected after your ruling:** `tier_b_matched` = your MATCH count; `tier_b_ruled_none` = your NONE count;
concept/expectation recall DROPS below 1.0 for every MATCHed concept the store still lacks (→ RED, by design).

## NEXT CRITICAL STEPS (strategic-leverage order)

1. **Owner rules the 45** (above). Unblocks the completeness claim (D-3130); turns omission into a measured loss.
2. **Extract any MATCHed-but-omitted concepts** into the store (S2 targeting those source_ids) so the rail returns
   to CLEAN — this is the "nothing lost" loop closing, not a rail defect.
3. **The 4 open CRITICAL bugs** (predate T-195): **BUG-709** (S5 stale S4 labels), **BUG-710** (D2511 retrieval gate
   inert), **BUG-712** (content_type routing collapse), **BUG-713** (superseded runs still in store/KNN) — each a
   red-loop-first (D-3036) job.
4. **BUG-972** (LOW, deterministic) — `r5_code_review.py --out <outside-repo>` traceback; cheap red-loop.

## HIDDEN CONFLICTS / FUTURE TAX (carried forward)

1. **`pipeline_commit` stamp churn**: `--check` re-stamps the report to current HEAD every run → tree dirties every
   recall check. Provenance-only; settle by pinning the stamp to the commit that produced the DATA (a decision, not
   a patch).
2. **BUG-709 dual heading** (OPEN then CLOSED in append-only buglog) → census counts it CRITICAL-open via its FIRST
   heading. A buglog-status-flag act, not a silent edit.
3. **Tier-B MATCH → RED is intentional**, but it means the rail is RED until extraction lands. Do not read a RED
   tier-B rail as a regression of the certified tier-A core (tier-A stays 44/44 = 1.0).
