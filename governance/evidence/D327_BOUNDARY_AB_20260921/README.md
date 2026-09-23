# D-327 boundary A/B receipt (filed 2026-09-23)

| arm | valid JSON | n | valid_rate | avg latency |
|---|---|---|---|---|
| boundary OFF (`ab_off.json`) | 30 | 30 | 1.0 | 21.1 s |
| boundary ON (`ab_on.json`) | 0 | 30 | 0.0 | 63.5 s |

`ab_on` failures: `RuntimeError: OMLX call failed after 2 attempts: 'content missing from message (reasoning-mode…'`

This is the measurement D-327 rests on, and it is why `config/pipeline_config.yaml → stage4.boundary_inject_enabled`
must stay `false` (BUG-374: the flip never landed and the rejected block ran live for 2 days).
Do not delete, do not rewrite: `scripts/verify_evidence_manifests.py` fails loud if either hash drifts.
