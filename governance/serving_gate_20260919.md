# Serving gate — 0a / G17 (D274a) — before/after snapshot

Generated: 2026-09-19T14:31:25.925060+00:00
DB: `knowledge pipeline/maxwell.db` (7995 rows)
Backup: `maxwell.db.bak_20260919_163125_pre_serving_gate`

## Status distribution

| status | before | after |
|---|---|---|
| PASS | 3310 | 3299 |
| QUARANTINE | 4685 | 4696 |

- de-served (PASS → QUARANTINE): **11**
- restored (QUARANTINE → PASS): **0**

## Typed s5_reason distribution (after)

| reason | rows |
|---|---|
| neutral | 3808 |
| entail | 3299 |
| no_evidence | 555 |
| contra | 293 |
| duplicate | 17 |
| vacuous | 14 |
| evidence_contaminated | 8 |
| mech_fail | 1 |

Rule: status = PASS iff `verification_results[factual].passed`, else QUARANTINE.
CI invariant: PASS ⟹ factual.passed and reason ∉ {contra, no_evidence, mech_fail, vacuous, evidence_contaminated}.
