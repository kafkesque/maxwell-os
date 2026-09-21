# ARTIFACT REGISTRY — evaluation instruments (name-collision fix, 2026-09-21)

**Why this file exists.** Two different human-labelled instruments were both called "ANCHOR-1".
That made "which ruler?" undecidable from a filename. This registry is the single name map.

## The two instruments (never merge the files)

| canonical ID | rows | sampling | menu it was answered under | authority artifact | role |
|---|---|---|---|---|---|
| **RULER-150** | 150 (100 proportional + 50 forced-minority) | stratified, population-proportional | `cac6e695` (CT = 7 classes, no `none`) | `governance/anchor1_frozen_20260920.json` (`0ec321a7…`) | **calibration**: error rates, floors, abstention operating point, D-300 bar |
| **ANCHOR-2** (was "ANCHOR-1") | 60 (58 after removing 2 ruler overlaps) | contra-stratified hard rows (boundary pairs, quarantine-heavy) | `73597ee2` (CT = 8 incl. `none`, de-negated cognitive science) | pair: `governance/ANCHOR2_BLIND_SHEET_20260920.csv` (human truth) + `governance/ANCHOR2_KEY_20260920.json` (pipeline labels) | **adjudication / repair queue / held-out validation** (R3) |

Legacy naming, recorded (do not rewrite history): D-274f defined **ANCHOR-1 = the frozen 150-row set**
(hence `anchor1_frozen_20260920.json`, correct as named); D-298/D-310 used "ANCHOR-1" for the **60-row**
set (now ANCHOR-2). 2 `fb_id`s overlap between the two instruments.

## Rename map (2026-09-21, bytes unchanged — sha256 citations stay valid)

| old | new |
|---|---|
| `governance/ANCHOR1_BLIND_SHEET_20260920.csv` | `governance/ANCHOR2_BLIND_SHEET_20260920.csv` |
| `governance/ANCHOR1_KEY_20260920.json` | `governance/ANCHOR2_KEY_20260920.json` |
| `governance/ANCHOR1_MENU_REFERENCE_20260920.md` | `governance/ANCHOR2_MENU_REFERENCE_20260920.md` |
| `governance/ANCHOR1_HELDOUT_SET_20260921.json` | `governance/ANCHOR2_HELDOUT_SET_20260921.json` |
| `governance/bakeoff_typed_decision_anchor1_20260921.json` | `governance/bakeoff_typed_decision_anchor2_20260921.json` |
| `governance/anchor1_kappa_20260921.{json,md}` | `governance/anchor2_kappa_20260921.{json,md}` |
| `governance/anchor1_repair_triage_20260921.md` | `governance/anchor2_repair_triage_20260921.md` |
| `scripts/anchor1_kappa.py` | `scripts/anchor2_kappa.py` |
| `scripts/anchor1_repair_triage.py` | `scripts/anchor2_repair_triage.py` |
| `config bakeoff.sources.anchor1` | `config bakeoff.sources.anchor2` (`legacy_names: [anchor1]`) |

**Correction found while renaming:** `anchor1_arbitration_20260921.json` was NOT ANCHOR-1/2 — it was an
in-sample derivation on the **116 RULER-150 rows** (script read `anchor1_frozen_20260920.json`). Renamed
`governance/ruler_arbitration_in_sample_20260921.json`; script renamed
`scripts/ruler_arbitration_in_sample.py` (superseded by `scripts/r3_heldout_eval.py`).

## Rules

1. **Never concatenate the instruments into one file.** Two sampling designs cannot be pooled by appending.
2. **Never pool across menus.** Any quoted number must carry the `menu_hash` it was judged under.
3. If a single headline is ever needed: pool **at read time** by post-stratifying RULER-150 to the corpus
   distribution, with per-set `menu_hash` + `n_effective` (D-275a/BUG-334) — never by editing artifacts.
4. Held-out rows (ANCHOR-2) must stay held out: they are the only set that can falsify an in-sample gain (D-311).
5. Ruler authority is the **frozen key**, not the CSV: the CSV is a human editing workspace (D-313).

---

## D-315 RULING (2026-09-21, owner-ratified) — WHICH ONE IS THE RULER

**Canonical ruler = `governance/anchor1_frozen_20260920.json`** (`sha256 0ec321a7…`). It is the authority for the
150 blind **human labels** *and* for the **measurement** (per-row human/stored/agree x 3 axes + stratum + fb_id).

| role | artifact | sha256 | why |
|---|---|---|---|
| **AUTHORITY** | `anchor1_frozen_20260920.json` | `0ec321a7…` | committed, immutable, sha256-cited, D-313-satisfying |
| workspace | `RULER_BLIND_SHEET_20260917.csv` | `38323192…` | the human edits it; also the ONLY record of WHY a cell abstained |
| superseded draft | commit `986fbc4` version | `2d456720…` | adopting it moves 41 CT + 7 DISC human labels and re-baselines every floor |
| byte-lost | freeze-time | `4d0c856a…` | in no repo version, no backup; label-verified-identical -> ruled, not aborted |

Evidence that the ruling moves nothing: re-scoring from the authority reproduces the published numbers EXACTLY —
CT 0.3533 / DISC 0.4741 / FORM 0.2828 (and the authority's own `summary_error_rates`). All paths, hashes, the menu
hash, `truth_source: key` and the pooling rule are declared in `config/eval_integrity.yaml:ruler_authority`.

### Read the stored side through this mapping (BUG-338)
The authority's `stored.discipline` field is a *scoring view*, not a pure label: `emerging_dump` (13 rows) is the
scorer's sentinel for the pipeline's catch-all dump. `emerging` (pipeline/DB) -> `emerging_dump` (scored) = a
stored-label **FAILURE**. On the **human** side `emerging` is an **abstention**. The two are deliberately asymmetric;
never compare the strings naively. The authority was NOT edited to "fix" this — rewriting an immutable, sha256-cited
artifact is the D-313 sin.

### Effective n (BUG-334) — publish it or the denominator flatters you
CT 150/150 · DISC **116**/150 (28 blank + 6 `emerging` cannot be scored) · FORM 145/150.

### HUMAN ATTESTATION — **UNSIGNED (open owner gate)**
The human fields are the reviewer's blind verdicts by construction, and the label conversion is verifiable
(0 CT diffs, 0 substantive DISC/FORM diffs vs the workspace). What does NOT yet exist is a **signed statement**
converting that inference into evidence. This line is reserved for it:

> `human_attestation: ""` — owner, please sign: *"these 150 labels are mine, made blind to pipeline output."*

Until it is signed, treat "human-anchored" as *verified-by-reconstruction*, not *attested*.
