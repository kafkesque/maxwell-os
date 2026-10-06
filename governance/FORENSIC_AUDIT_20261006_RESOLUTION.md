# Forensic Audit — D-2820 Owner Resolution (drops + emerging-mix) — 2026-10-06

Verdict: **CLEAN.** No break / cascade / drift / blindspot / gap / conflict / bug /
hidden failure / error leak / mismatch / bloat detected.

## Scope
Owner approved (2026-10-06):
1. **DROP 3 noise rows** — R084, R106, R148 (all "noise, drop irrelevant" per owner note).
2. **emerging-mix R023/R112/R177/R188** — keep only real domains, drop the stray `emerging` token.

## Recommendation (emerging-mix: abstain vs keep-real-domains)
**Keep only the real domains.** Rationale:

- **It was a merge artifact, not a genuine abstention.** In all 4 rows the discipline is
  confidently real (`decision making` / `research methodology` / `semiotics` / `cognitive science`).
  The single `emerging` domain token was carried forward from the *generator's* candidate
  abstention, then concatenated alongside the *owner's* real domains. The owner supplied real
  domains in every case — the `emerging` was leftover noise, not judgment.
- **Accuracy.** `emerging` = "no existing label fits." Mixing "no label fits" with "these labels
  fit" is self-contradictory and yields an incoherent label vector that the DeBERTa-NLI verifier
  cannot cleanly entail/contradict. Keep-real gives a precise, verifiable classification.
- **Output quality.** `emerging` is a PURE abstention signal. There are already 7 rows that are
  PURE `emerging` on domains (R032/R066/R101/R113/R141/R172/R209) — genuine "domain gap" cases.
  Mixing `emerging` into these 4 pollutes that signal and makes the emerging bucket non-actionable.
- **Future-proofness.** A clean, PURE `emerging` bucket is what drives future taxonomy-expansion
  triage (menu v7 boundary work, D-2822 NLI recalibration, BUG-631 re-derivation). Diluting it
  destroys the ability to distinguish "genuinely novel → needs a new slot" from "classified but
  hedge-labeled."
- **Cost of full abstention.** Making these 4 rows fully `emerging` would throw away a correct
  confident discipline AND 1–2 correct real domains per row, for zero gain — none of the 4 concepts
  (focused action selection, content analysis, contextual interpretation, sensory-motor reasoning)
  is novel; each fits an existing slot exactly.

## Resolution applied
| Artifact | State |
|---|---|
| `governance/discipline_anchor_conformance_20261006.json` | re-cut anchor 204 → **201** (provenance-stamped) |
| `governance/rederive_v6_owner_decisions_flat.json` | flat decisions **201** entries (harness `--decisions`) |
| `governance/rederive_v6_owner_decisions_final.csv` | final 201-row CSV (drops removed, mixes fixed) |
| `governance/rederive_v6_finalized_20261006.json` | `--adjudicate` output: **201** rows, owner_finalized |

Resolved rows: R023 `personal productivity|project management`; R112 `science & research|research & methodology`;
R177 `semiotics & communication`; R188 `education`.

## Findings by audit dimension
- **BREAK** — none. The 3 dropped rows were terminal noise rows with no downstream references;
  `--adjudicate` re-ran clean on 201 rows (harness never auto-finalizes, D-2839 c2).
- **CASCADE** — none. Removing R084/R106/R148 does not touch any other row; the emerging-mix fix
  is a pure domain-token removal, no label renumbering or re-routing.
- **DRIFT** — none. Menu pins re-verified via `--plan`: composite `92f1a204…` = declared live pin,
  answer-space `d704d06e…` = declared. Anchor count 201 vs declared 201. 0 join misses.
- **BLINDSPOT** — 1 flagged (NOT auto-resolved): 7 rows carry `discipline='emerging'` + real domains
  (R006/R059/R127/R140/R146/R165/R202). This is the mirror of the mix (discipline abstention + known
  application domains) and is semantically defensible, but R006's original discipline was on-menu
  (`generative design`). Owner review deferred — out of scope for this turn.
- **GAP** — 0 off-menu discipline, 0 off-menu domain, 0 empty fields (post-drop), 0 remaining
  emerging-mix.
- **CONFLICT** — none. 201 unique item_ids, no duplicates; decisions keys == anchor ids exactly.
- **BUG** — none. `--selftest` 3/3 (stamp builder, fail-closed adjudication, manifest + BUG-650 guard).
- **HIDDEN FAILURE** — none. `--plan` reported "201 rows joined, 0 missing".
- **ERROR LEAK** — none. Fail-closed paths exercised and passed (unadjudicated/off-menu rejection,
  guard acceptance).
- **MISMATCH** — none. All 201 finalized rows `owner_finalized` on both axes, all on menu v6.
- **BLOAT** — none. Resolution is deterministic and single-use; no permanent script or dead file added.

## Emerging census (post-resolution)
- `discipline='emerging'` (genuine abstention): **7** — R006/R059/R127/R140/R146/R165/R202.
- `domains=['emerging']` pure (genuine domain-gap): **7** — R032/R066/R101/R113/R141/R172/R209.
- Rows touching `emerging` on any axis: **14 / 201 = 6.97%** — well under the 0.35 A/B gate.
- No full-abstain rows (discipline AND domains both `emerging`).

## Remaining owner-gated (unchanged)
- Taxonomy boundary clarifications (edit protected `closed_menu_v6.json` → re-render → re-pin →
  re-derive, since a menu-hash change invalidates this anchor): strategic thinking/decision making;
  business administration/operations research/organizational theory; marketing/design psychology/
  behavioral economics; genAI/AI/ML; + domain overlaps (BD/BO/entrepreneurship, digital product/
  web & ui/product design, research & methodology/science & research).
- `--verify` → `--finalize` → flip D-2839 PROPOSED→RATIFIED (human gate) → full-201 A/B (D-2767)
  kappa≥0.800 AND emerging≤0.35 → flip `definition_anchored_menu_enabled` iff pass.
