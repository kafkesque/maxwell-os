# Depth path — pragmatic recommendation (2026-09-10, D2577 follow-up)

**Question put to me:** re-scope the 0.85 gate for the standalone 4-way depth encoder, or
use the clean vote set as eval reference + few-shot exemplars for the S4 generative depth
call? Which is more future-proof, and *why* — verified pragmatically.

**Short answer:** neither change is where the quality is. All three labelers measured
today land inside the same ±0.05 band; the binding constraint is **label policy**, not
model capacity or prompt engineering. Ship the generative call as **labeler of record**
(ontology-versioned), the encoder as a **disposable serving cache** (sovereign, 3 500×
cheaper), and spend the next effort on the vote's decision rules.

---

## 1. Measurements (all on the SAME held-out data, temp=0.0 / temp-equivalent)

### Arm A — 4-way depth, 200 held-out FBs, gold = 3-voter clean labels
(`governance/depth_clean_test.yaml`, identical rows the encoder was evaluated on)

| path | macro-F1 | accuracy | s/FB | family |
|---|---|---|---|---|
| encoder `classifier_depth_cleanC` (139M) | **0.4790** | 0.530 | ~0.0006 | ModernBERT-base, trained on clean labels |
| gpt-oss-20b zero-shot (production batch depth call, `v3_contrastive`) | 0.4433 | **0.580** | 2.15 | OMLX (already wired in S4) |
| gpt-oss-20b + 3 few-shot exemplars/class from the clean train split | 0.4571 | 0.550 | 3.02 | D2454-style exemplar injection |

Few-shot moved macro-F1 by **+0.014** (inside noise) and doubled latency: it traded
domain recall for universal recall (domain tp 69→59, universal tp 1→3). It re-balances the
boundary, it does not fix it.

### Arm B — collapse to 2-way scope (broad = universal+cross-domain, narrow = domain+specialized)
Same 200 rows, derived from each arm's confusion matrix:

| path | 2-way accuracy | 2-way macro-F1 |
|---|---|---|
| encoder cleanC | 0.645 | 0.638 |
| gpt-oss-20b zero-shot | **0.690** | **0.680** |
| gpt-oss-20b few-shot | 0.660 | 0.656 |

4-way costs ~10-13 accuracy points versus the honest coarse signal. If the consumer
(`S4_DIFFICULTY_MAP`, D2410) only needs scope, the 4-way label is mostly noise.

### Arm C — label POLICY, evaluated on the 133-row reliable-pair consensus slice
(`governance/depth_core_test.yaml`; identical eval rows for all three, none of them in any train split)

| training labels | train rows | macro-F1 on the consensus slice |
|---|---|---|
| gpt-oss silver (no vote) | 796 | 0.3437 |
| 3-voter majority (with Qwen3-Coder tie-breaks) | 796 | 0.4073 |
| **reliable-pair consensus only (DeepSeek == Qwen3.8)** | **545** | **0.4298** |

Cleaning the label policy bought **+0.0225 macro-F1 with 251 FEWER training rows**. That is
the only lever measured today that improved quality without adding cost.

### Arm D — the label ceiling (why no model can reach 0.85)
From `governance/depth_vote_checkpoint.jsonl` (996 FBs, deduplicated):

- unanimous 3/3: **303 / 996 (30.4 %)** · 2/3 majority: **612 (61.4 %)** · no majority → force-`domain`: **81 (8.1 %)**
- DeepSeek-v4-pro vs Qwen3.8-27B agree on **678 / 982 = 69.0 %** of co-voted FBs
- Qwen3-Coder-30B matches that reliable-pair consensus only **303 / 678 = 44.7 %** — and because 2-of-3 wins it never overturns the pair, it only *decides* the 304 rows where the pair disagrees (the hardest 31 %). Those 612 "2/3 majorities" are therefore partly coin flips.
- disagreement is concentrated: cross-domain↔domain = 174 / 304 (57 %), domain↔specialized = 75, universal↔cross-domain = 42
- the encoder's worst slice is exactly the fail-closed bucket: acc **0.300** on the 20 held-out no-majority rows vs **0.556** on vote-agreed rows
- encoder κ = **0.224** (4-way, chance level 0.394) — accuracy 0.53 is not interpretable without it

### Arm E — production drift
`fbs.depth` in `knowledge pipeline/maxwell.db` (7 995 rows, all `gen_model = Qwen3-Coder-30B…`, commits bae6662/24d2690):

- 100 % identical to the raw gpt-oss silver label — **never independently verified**; S5 NLI does not cover depth
- agrees with the 3-model vote on only **458 / 996 = 46.0 %**
- on the audited 996 FBs, DB distribution is cross-domain 716 / universal 80 / domain 100 / specialized 100 versus the vote's cross-domain 384 / domain 501 / universal 65 / specialized 46 — the stored field is gpt-oss's prior, not a measured property

---

## 2. Recommendation

**Two-tier, generative-as-truth, encoder-as-cache — plus a label-contract fix that comes first.**

1. **Labeler of record = the S4 generative depth call (option b).** Keep depth a
   prompt-versioned LLM step with the exemplars, *not* because it is more accurate today
   (it is 0.036 macro-F1 behind the encoder) but because the ontology is the artifact that
   keeps moving (D2577 changed it), and prompt+YAML re-versioning re-labels all 7 995 FBs
   in ~1.2 h (batch 4, 2.15 s/FB) with zero re-annotation and zero retraining. It is
   already wired with batching, retry, serial fallback, fail-closed and checkpointing.
2. **Serving path = the encoder, treated as a distilled cache.** 3 500× cheaper (0.6 ms vs
   2.15 s/FB), offline, deterministic, no cloud (C1/C3), and statistically
   indistinguishable from the 20B call (0.479 vs 0.443 macro-F1). Re-train whenever the
   labels move — 9 min for 796 rows on MPS, measured today. Never promote it to source of
   truth while the ontology is still churning.
3. **Retire the 0.85 gate.** It is unreachable by construction: the labels agree with each
   other only 69 %, and only 30 % are unanimous. Replace it with (a) Cohen's κ against the
   frozen consensus core (encoder today κ=0.224 4-way / ~0.36 2-way), (b) an
   abstention + low-confidence rate, (c) the 133-row consensus core as a fixed regression
   slice in CI.
4. **Fix the label contract before anything else** (highest measured ROI):
   - fail-closed must abstain, never fabricate `domain` (BUG-235: 8.1 % of rows)
   - drop Qwen3-Coder as tie-breaker; use the 2 reliable voters, and on disagreement emit
     `depth_confidence: low` instead of a 2/3 majority that is a coin flip (BUG-236)
   - write explicit decision rules for the two endemic boundaries: cross-domain↔domain
     (57 % of disagreements) and domain↔specialized — the D2483 contrastive anchors are
     the right instrument, they just need to cover these two cases
   - compact the vote checkpoint (BUG-234: 1 780 lines / 996 unique FBs)
5. **Serve what was actually measured.** Publish `depth_scope: broad|narrow` (0.690 acc on
   gpt-oss, 0.645 encoder) for anything that gates retrieval/difficulty, and keep the 4-way
   `depth` as a stored annotation only, so it can be re-derived when the ontology changes.
6. **Eval hygiene.** 200 rows with 13 universal / 9 specialized cannot support a ±0.05
   decision. Grow the reference to ≥100 rows/class and report κ + per-class n, never bare
   accuracy on a 50 %-prior class.

## 3. Why this is the future-proof answer
Ontology churn invalidates *weights*, not *prompts*: a 5th depth class costs a prompt
version bump plus a relabel pass, versus re-annotation plus retraining plus re-gating for a
fixed 4-way head. But weights are what buys sovereignty, determinism and $0 marginal cost
at 8 000 FBs and beyond. Owning both — generative as the moving source of truth, encoder as
a regenerable cache — is strictly dominant over either alone. If forced to keep only one,
keep the generative labeler: the cache can always be rebuilt from it, never the reverse.

## 4. What would change this recommendation
- reliable-pair agreement rising above ~85 % after the boundary rules land (then the
  encoder becomes the labeler of record and depth stops being an LLM cost at all)
- an ontology freeze declared (same effect, immediately)
- a downstream consumer that needs `universal` specifically: today no model recovers it
  (F1 0.087 gpt-oss / 0.193 few-shot / 0.348 encoder on 13 rows; 0.0 on the 3-row core
  slice) — that class is currently unmeasurable and should not gate anything.

## Artifacts
- `governance/depth_path_probe.json` — the two gpt-oss arms (per-class F1, confusion, latency)
- `governance/depth_path_evidence_2026-09-10.json` — consolidated tables above (4-way, 2-way collapse, κ, core slice)
- `governance/depth_eval_classifier_depth_cleanC_core.json`, `…_silverC_core.json`, `governance/depth_eval_coreC_core.json`
- `governance/depth_core_train.yaml` (545) / `governance/depth_core_test.yaml` (133) — the consensus-core splits
- `temp/depth_path_probe.py`, `temp/depth_encoder_preds.py` — probe scripts (temp/ scratch)
- buglog BUG-234…237
