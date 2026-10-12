# D-B — S5 Paraphrase-Aware Grounding (BUG-705) — Design Spec
Decision: D-2921 / D-B (owner-approved). Status: DRAFT for gemma review (R5) before any code write.

## Objective (RECALL fix, complementary to D-2822 precision fix)
Recover the 2,258 NEUTRAL rows that are `ent≥1 AND contra=0` (faithful reworded-true claims) without
weakening the fail-closed guarantee. D-2822/or-entail already handles PRECISION on the entail path at
threshold 0.5; it cannot reach these rows because their max entail is 0.13–0.46 (< 0.5).

## Design
A parallel SECOND signal, gated so it can only FLIP a NEUTRAL to PASS, never downgrade a PASS:
  1. NLI aggregation returns NEUTRAL (not passed), AND
  2. `n_entail >= paraphrase_min_entail` (default 1), AND
  3. `n_contra == 0` (paraphrase_require_no_contra, fail-closed), AND
  4. STS cosine similarity(definition, best evidence passage) >= threshold.
Only then → PASS with `s5_reason = "paraphrase"`.

Similarity primitive: `pipeline.embeddings.embed_texts_bge_m3` (bge-m3 → 512d L2-normalized, already the
repo embedding; C21 swappable via `paraphrase_model`). cosine = dot of L2-normalized vectors; take max
over clean evidence passages (same passages that passed `_is_garbage_passage`).

## Config (config/pipeline_config.yaml, stage5.* — C12, nothing hardcoded)
```yaml
  paraphrase_path_enabled: false        # flip ONLY after threshold is calibrated (D-2858-style)
  paraphrase_similarity_threshold: 0.85 # cosine (bge-m3 512d) — CALIBRATE before enabling
  paraphrase_model: bge-m3              # C21 swappable; must return L2-normalized vectors
  paraphrase_min_entail: 1              # require >=1 entailing passage before similarity can flip
  paraphrase_require_no_contra: true    # fail-closed: any contra vetoes the flip
  paraphrase_max_chars: 1500            # truncation for the similarity pass
  paraphrase_calibration:               # D-2858-style stamp (mirror of nli_calibration)
    decision: null
    threshold: null
```

## Code (pipeline/stage5_verify.py)
1. Module constants after the NLI_AGGREGATION block (~line 576), mirroring the D-2858 guard:
   read `paraphrase_*` keys; if `paraphrase_path_enabled` and no `paraphrase_calibration` stamp
   {decision, threshold}, raise C16 (fail-loud, same idiom as D-2858).
2. New primitive `_paraphrase_similarity(definition, evidence_passages) -> float`:
   embed definition + passages via bge-m3, cosine over L2-normalized vectors, return max.
3. In `deberta_check`, AFTER `_aggregate_verdict` returns (line ~393): if `not passed` and enabled,
   compute `n_entail`/`n_contra` from the already-collected `_entail_scores/_contra_scores/_neutral_scores`,
   and if the gate passes, return `(True, sim, f"PARAPHRASE (STS {sim:.3f} >= {threshold}): faithful
   reworded-true claim")`. Else return the original `(passed, score, detail)`.

## Reason vocabulary (config/serving_gate.yaml — one home, C21)
```yaml
  reason_vocabulary:
    paraphrase:
      passed: true
      negative: false
      meaning: "D-B: NLI neutral (ent>=1, contra=0) + high STS similarity — faithful reworded-true claim"
  detail_rules:
    - {prefix: "PARAPHRASE", reason: paraphrase}   # first-match-wins; no prefix collision
```
`derive_status` maps detail "PARAPHRASE…" → reason `paraphrase` (passed=true), invariant holds
(status=PASS ⟹ factual.passed and reason not negative).

## Calibration (scripts/paraphrase_calibrate.py — analog of nli_calibrate.py)
Input: a gold set of (definition, evidence, label ∈ {paraphrase_true, non_paraphrase}) pairs, seeded from
the 2,258 recoverable neutral rows + a matching PASS/contra control. Sweep threshold, report P/R/F1, and
mint `paraphrase_calibration` {decision, threshold} ONLY when a threshold meets the ship bar (~0.85 P,
match D-2822's precision 0.852 bar). Threshold is then written to config — never guessed.

## Rollout (fail-closed, no cascade)
  1. Add config keys (enabled=false) + serving_gate reason + detail rule → inert.
  2. `paraphrase_calibrate.py` mints a threshold under a NEW decision id.
  3. gemma-4-E4B reviews the stage5_verify diff (R5: generator ≠ verifier).
  4. Set threshold + `enabled=true`; re-verify the 6,591 rows (post-hoc); re-commit via stage6_commit.
  5. Re-run the D274a serving rail to prove 0 invariant violations.

## Not done here (separate steps)
- Re-author 7 golden examples under D-C (macro + ranked discipline) — D-C facet migration.
- Commit+index PT/PI/GE (Stage R retrieval surface) — independent of S5.
- Condition C macro re-classifier (BUG-706) — independent of S5.
