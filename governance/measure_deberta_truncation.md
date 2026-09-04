# MEASURE-DEBERTA — 512-token truncation exposure (D2553)

**Corpus:** 7995 FBs (maxwell.db) · **Tokenizer:** DeBERTa-v3-large · **Window:** 512 tokens
**Current char-truncation:** premise=1500 chars, hypothesis=500 chars
**Malformed evidence rows (C16-reported):** 0

## Definition (hypothesis)
| Metric | Value |
|---|---|
| Over 500-char truncation | 0 (0.0%) |
| Over 512 tokens (would exceed DeBERTa alone) | 0 (0.0%) |
| Token length median / p90 / p95 / max | 33 / 51 / 55 / 85 |

## Evidence (max single passage)
| Metric | Value |
|---|---|
| Over 1500-char truncation | 3 (0.04%) |
| Over 512 tokens | 0 (0.0%) |
| Token length median / p90 / p95 / max | 87 / 117 / 128 / 470 |

## Combined (premise + hypothesis) — DeBERTa window binding
| Metric | Value |
|---|---|
| Over 512 tokens | 0 (0.0%) |
| Token length median / p90 / max | 119 / 147 / 498 |

## Verdict
The binding constraint is the **256-char truncation**, not DeBERTa's 512-token
window: 0.0% of definitions exceed 256 chars (content lost),
but only 0.0% would exceed 512 tokens if untruncated.
