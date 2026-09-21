# FORENSIC AUDIT — 2026-09-21c (session 7: R3 held-out run)

Scope: audit the repo BEFORE this session's changes, then re-verify AFTER them. Seven axes: broken, drifted,
blindspot, gap, conflict, mismatch, bug, hidden contamination, leak, error, failure, future tax.
Baseline: `c76bd6a` (governance sync of session 6) + 17 dirty paths (frozen sheets / agent state).

## 1. New findings (found by this audit; none were visible before)
- **F-01 (HIGH, fixed): cross-SOURCE artifact merge hazard.** The bake-off harness merges a previously
  written artifact into the new one (`BUG-323` fix). Nothing checked that the previous artifact belonged to
  the SAME label source, so the first ANCHOR-1 run would have swallowed the ruler arms into the held-out
  artifact — silent provenance contamination of a published number. Fixed: the artifact now carries
  `source` + a full `spec` + `menu_hash`, and the merge is refused across sources (logged as BUG-332).
- **F-02 (MED, open → BUG-333): the R5 verifier can rubber-stamp.** gemma-4-E4B answered the adapter review
  in the exact requested schema while answering **"yes" to inverted-polarity questions** and `NONE` to every
  blocker line. An LLM self-report is therefore NOT sufficient R5 evidence for a measurement adapter; a
  mechanical channel (truth-blinding re-run) is now required and was used here. This also retroactively
  weakens BUG-331's "missing R5 review" closure path: a pro-forma review would not have closed it.
- **F-03 (MED, open → BUG-334): the pre-registered n is not the measurable n.** One held-out row carries an
  empty human verdict, so D-311's "58-row" set yields **n_scored = 57**. The effective n must be declared in
  every published statement or the denominator silently flatters the result.
- **F-04 (LOW, open → BUG-335): `config/eval_integrity.yaml` lost a comment line.** The per-pair scoring
  note ("padded forward batches (per-pair scoring was ~1 s/pair)") is glued to `abstain_sweep` instead of
  `nli_batch_size` — a previous careless edit. Cosmetic but it is exactly the class C12 REVIEW-RULE exists
  to catch; fixed in this session's config edit.
- **F-05 (LOW): `bakeoff` was a single-source block with no way to name a source.** Any second label source
  had to be hardcoded in a script (which `scripts/anchor1_arbitration.py` did, while claiming config-first).
  Fixed by `bakeoff.active_source` + `bakeoff.sources.<name>` (D-312).

## 2. Governance drift found and corrected
- **`governance/buglog.md` still said BUG-328 HIGH-OPEN** although the change set was landed in `32cb9fa`
  and the working tree has no `pipeline/` diff. Status corrected to CLOSED (evidence: dry-run 0 writes,
  pytest 200/201, DB does not move) — a real drift, not a bookkeeping nicety: an OPEN HIGH bug that is
  actually landed hides the next genuine HIGH.
- Housekeeping scan: 20 `.bak*` files and 5 `__pycache__` dirs remain **but are gitignored** (`.gitignore`
  lines 12, 101) → NOT a C19 violation in the repo; no action taken (no destructive cleanup of anything
  that is not regenerable).
- No pipeline is running (checked `ps`) → all measurements and file edits above were race-free.

## 3. Explicit negatives (checked, nothing found)
- **No contamination/leak in the measurement**: truth-blinding test = 0 label diffs; pairwise abstains
  entirely without the stored label; no human label enters any prompt or key the arms read.
- **No DB write, no pipeline write, no ontology write** by this session; `pipeline/` diff vs HEAD is empty
  for this session's work (the session-6 landing is the only production change, already committed).
- **No YAML/ontology conflict**: taxonomy v5.5 coherent across config + code + menu artifact; the frozen
  `config/closed_menu_v5.sha256` still equals `pipeline/closed_menu.menu_hash()` and the ANCHOR-1 key's
  `menu_hash` — three-way agreement, so the held-out run used the same closed menu as production.
- **No silent error introduced**: the new loader raises on an unresolvable HUMAN verdict and prints, rather
  than swallowing, an unresolvable STORED label (which becomes an honest abstention, per D-275c).
- **No removal or deletion of any pipeline output, artifact or sheet.**
- **No environment outcry misread**: oMLX :11435 answering 401 without a key is expected (bakeoff sends
  `sk-maxwell-local`); Ollama :11434 DOWN only degrades `search_vector` to FTS and is pre-existing.

## 4. Explicit risks NOT closed (carried, with owners)
1. BUG-329 (HIGH) — the ruler exists in three versions (freeze 4d0c856a / HEAD 2d456720 / working 38323192);
   no re-measure on the ruler is valid until the owner names the canonical version (**GATE 4**).
2. BUG-326 (MED) — corpus assignment/emission defects (403 raw→canonical, 147 both-axes, 703 no-domain)
   are still unrepaired; the repair is deterministic and LLM-free but must not be applied until the R5
   channel is fixed (F-02) or the script is verified mechanically.
3. BUG-330 (LOW) — stale smoke assertion in `tests/test_stage4_preflight_smoke_stress.py` (200/201).
4. BUG-331 (MED) — serving-gate DB write still holds no credible R5 record.
5. `agent/session_seed.yaml` and the frozen sheets remain dirty **by design** (other-session work / owner
   gate); this session did not touch them.

## 5. Machine-written evidence block
See `## Evidence` appended at the end of `governance/R3_HELDOUT_RESULT_20260921.md` (artifact/sheet/key
sha256 + menu_hash + command line), written programmatically so no hash is transcribed by hand.
