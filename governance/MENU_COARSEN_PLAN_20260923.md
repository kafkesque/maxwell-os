# MENU COARSEN — execution plan (owner ruling 2026-09-23, D-346, executes D-343)

The last cheap hope for a better classifier is gone (D-345: the k-NN arm loses on all three
routed axes; challenger −8.77 pp; content_type lift over the constant −0.010 / F-17).
What remains is making the MENU honest about what the representation can carry.

## The contract

| axis | route | evidence (lift over null / kNN vs constant) | pipeline behaviour |
|---|---|---|---|
| domains | `classify` | +22.64 pp; 0.3095 vs 0.0879 | keep — this is the axis that works |
| discipline | `classify` | +22.54 pp; 0.2652 vs 0.1134 | keep the labeler, coarsen the tail |
| extraction_type | `coarsen_or_classify_with_calibrated_abstention` | +14.89 pp; 0.4165 vs 0.3265 | never a silent point label; abstain below a calibrated threshold |
| content_type | `constant_plus_human_queue` | +10.28 pp; **0.7863 ≤ 0.8161** | emit `principle` + queue the rest |
| depth | `constant_plus_human_queue` | +19.71 pp; **0.6540 ≤ 0.8193** | emit `domain` + queue the rest |

The rule is a conjunction, and the constant test dominates: a high lift over the permutation
null is **not** sufficient when the modal label already beats the neighbourhood.

## Enforced, not asserted

- `config/menu_routing.yaml` — the routing table as config (C12), with the measured numbers
  quoted from the sweep artifact (BUG-342) and the label-level coarsen/queue list.
- `scripts/verify_menu_routing.py` — fail-closed (C16) checker wired into `just health`:
  re-derives each route from the measured numbers and the pre-registered thresholds, asserts
  the quoted numbers still equal the artifact, asserts the declared constant equals the
  measured modal label, asserts every queued label is in the artifact's worst-label list and
  owned by a menu source, and asserts the contract's declared consumer symbol exists
  (D-339b — the BUG-385 guard). Current run: **5 axes, 23 queued labels, 0 RED, 1 warn.**
- Residual warn: `config/taxonomy_v5.yaml` exposes no machine-readable `depth` list, so the
  3 depth queue labels are existence-unverified. Named here rather than hidden.

## What this plan deliberately does NOT do

- It does **not** rewrite the taxonomy. Merging `risk management` into a parent changes what a
  published label MEANS and must be a versioned menu change (v5.6 → v6) with the labeler
  re-run and the ruler re-scored. The queue is a proposal with per-label measured evidence.
- It does **not** change any stored label. Coarsening applies on the next S4 run.
- It does **not** claim accuracy. Everything here is RELATIVE (D-337).

## Owner calls left

1. Ratify the merge map for the 10 discipline tail labels (which parent owns each).
2. Choose the extraction_type abstention operating point (t_low=p25 is currently proposed and
   `enabled: false`).
3. Decide whether `noise_drop` (kNN 0.258) and `process_template` (0.1846) are retired or kept
   as human-only labels in the content_type queue.
