# PHASE 1 — Close the Human-Review Gap (Exact Instructions)
> Scope: give every one of the 61 disciplines ≥2 **human-reviewed** examples before freezing.
> Current state (2026-09-07): 135/1027 reviewed → 44/61 classes ≥1, 32/61 ≥2. Target after Phase 1: **61/61 ≥2**.
> Generated pack: **temp/p5_phase1_review_pack.jsonl** (74 rows) — selector: `python3 temp/build_phase1_pack.py`.

---

## Why these 74 rows
- Chosen only from the 892 golden examples **outside** the review pack.
- Target classes = the 29 disciplines with <2 human-reviewed examples (17 uncovered + 12 singletons).
- Hard genre signals excluded (histories, community descriptions, book/about self-references, methodology orientations, bio artifacts, conspiracy provenance).
- Ranked by: not a self-declared non-causal mechanism → low p_mislabel → longer definition.
- Buffer: need=46 rows; pack has 74 (+1/class) so a human relabel away from silver cannot re-open a gap.
- `target_class_for_coverage` on each row tells you which class it was selected to cover.

---

## Step 1 — Open the pack
File: **`temp/p5_phase1_review_pack.jsonl`** (one JSON record per line; 74 rows).
Each record has evidence fields (name, definition, mechanism, silver_discipline, silver_domains, silver_depth, p_mislabel, tier) and **blank answer fields to fill**:
`final_discipline`, `final_domains`, `reviewer`, `confidence`, `notes`.

## Step 2 — Review each row (rules)
1. Read name + definition + mechanism. Ask: **is this a genuine principle?**
2. **If it is NOT a real principle** (historical description, community/field blurb, methodology orientation, artifact, non-falsifiable belief, provenance risk):
   - set `"final_discipline": "QUARANTINE"` and `"notes": "<reason>"`.
   - The merge tool will route it to the quarantine list, never into the master.
3. **If it IS a real principle:** set `final_discipline` to the best of the **61 canonical disciplines** (or `emerging` if truly none fit), and `final_domains` to **1–4 canonical domains only**.
   - Do NOT put discipline names in the domain list (psychology, research methodology, information security, game design, cultural design, … are disciplines, not domains).
   - Do NOT use backticks or trailing commas.
4. `reviewer` = who reviewed (e.g. `human` or `claude+human`).
5. `confidence` = `high` | `medium` | `low`. If you are guessing, write `low` and explain in notes.
6. When silver looks right → keep it (a CONFIRM is fast and valuable). Change only when genuinely wrong.
7. Reference for labels: **governance/canonical_labels_reference.md** (61 disciplines + 43 domains with definitions).

## Step 3 — Save the filled file
Save the completed records as: **`temp/p5_phase1_human_adjudication.jsonl`** (same line-JSON shape).
Tip: fill in an editor/script and keep the field names byte-identical.

## Step 4 — Validate + merge with the existing 135
```bash
python3 temp/merge_adjudications.py \
    --a temp/p5_human_adjudication.jsonl \
    --b temp/p5_phase1_human_adjudication.jsonl \
    --out temp/p5_adjudication_master.jsonl
```
- Exit 0 + report "61/61 classes with >=2 reviewed examples" → proceed.
- Any `PROBLEMS` line → fix that row in the phase-1 file and re-run (script never merges invalid rows).
- QUARANTINE rows land in **temp/p5_quarantine_list.jsonl** automatically.

## Step 5 — (Recommended) merge the previously-found hard artifacts into quarantine
Add these known noise rows to the quarantine list if you agree (or leave in the pack for later):
`S4-GOLD-MINED-00434` (reviewer bio), `S4-GOLD-MINED-00447` (publisher about-page),
`S4-GOLD-MINED-00242` (conspiracy source; also notes/field conflict), `S4-GOLD-MINED-00945` (non-falsifiable belief),
`S4-GOLD-MINED-00278` (empirical regularity, weak label). Decide: `00544` (Conspiracy Theory Fabrication).

## Step 6 — Freeze dry-run with the master adjudication
```bash
python3 scripts/freeze_gold_sets.py --size 400 \
    --adjudication temp/p5_adjudication_master.jsonl \
    --allow-soft --out temp/gold_frozen_phase1_test.yaml
```
Then check human coverage inside the frozen tiers:
```bash
python3 temp/phase1_coverage_report.py temp/gold_frozen_phase1_test.yaml temp/p5_adjudication_master.jsonl
```

## Step 7 — Governance
- Copy the final dry-run JSON block + coverage numbers into DECISION-LOG.md (D2585 P5 phase-1 note).
- Update MASTER-TASK-REGISTER.md and governance/aggregated_remaining_tasks.md.
- Only after Phase 2 (quarantine applied to the pool) and Phase 3 (freeze validator + multi-seed retrain) commit the freeze.

## Definition of done (Phase 1)
- [ ] 61/61 disciplines have ≥2 human-reviewed examples (merge report says so)
- [ ] 0 invalid disciplines / 0 invalid domains / 0 backticks in the master
- [ ] quarantine list populated and agreed
- [ ] dry-run freeze shows a large majority of CHALLENGE/GOLD-B rows are human-reviewed

---

## UPDATE 2026-09-07 (v2 — no-quarantine reality)
The phase-1 pack came back fully corrected (74 rows, no QUARANTINE) and was merged with the 135-row master.
- Merge tool upgraded to **v2** (`temp/merge_adjudications.py`): tolerantly parses the pretty-printed/hand-edited
  phase-1 format, validates discipline (61+emerging) + domains (43) + **depth (4-way)**, carries `final_depth`,
  and treats QUARANTINE as optional (0 used). It caught & we fixed: duplicated-empty `final_discipline` key
  (S4-GOLD-MINED-00418) and a discipline-as-domain (`media studies` → `media & entertainment`, S4-GOLD-MINED-00385).
- **Result:** `temp/p5_adjudication_master.jsonl` = **209 rows**, exit 0, quarantine file empty.
  Coverage = **56/61 classes ≥2 reviewed** (gaps: engineering 0; anthropology, game design, information security,
  systems engineering = 1 each — caused by reviewers relabeling rows out of their silver target class).
- Provenance note: 69/74 phase-1 rows list `reviewer: Qwen3.8` (not human). Spot-check sample:
  `temp/phase1_spotcheck_sample.csv` (12 rows). Depth-gold exists for 69/209 rows only (135 master rows have none).
- Silver-noise evidence: even the *cleanest* tranche (low p_mislabel, no genre signals) got **24 % relabeled**;
  the suspicious 135 tranche got **78 % relabeled** ⇒ treat the ~818 unreviewed silver rows as NOISY TRAIN data,
  never as eval gold. Eval (CHALLENGE/GOLD-B) must be restricted to the 209-row master.
