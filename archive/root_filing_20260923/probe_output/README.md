# Maxwell OS Probe — S2→S4→S5 Output
> **Generated:** 2026-08-12 | **Pipeline:** v3.0-D2298 | **Clusters:** 300 (200 convergent + 100 single-source)
> **Models:** S2=Qwen3-Coder-30B | S4=GPT-OSS-20B | S5=DeBERTa-v3-large (435M, no OMLX)
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (P=1.000, R=0.556), ISOR scoring, enrichment verification

## Stage Checkpoints

| Stage | File | Description |
|-------|------|-------------|
| **S2** | `stage2_fbs.jsonl` | Raw extraction FBs from convergent extraction (+ hybrid gate). Schema: name, definition, mechanism, boundary, consequence, evidence_passages, extraction_type, source_books |
| **S4** | `stage4_fbs.jsonl` | Classified + enriched FBs with CRIBS fields. Schema adds: application, failure_mode, elaboration, depth, discipline, domains, keywords, jargon |
| **S5** | `stage5_fbs.jsonl` | Verified FBs with epistemic status. Schema adds: verification_status (PASS/QUARANTINE), epistemic_status (corroborated/source-supported/speculative), ISOR rating, confidence_score, enrichment_warnings |

## Schema Reference (for frontier LLM evaluation)

### Core Fields (S2 output)
- `name` — FB name (short label)
- `definition` — What the principle IS (1-3 sentences)
- `mechanism` — HOW it works (causal chain)
- `boundary` — WHEN it fails (limits, conditions)
- `consequence` — WHAT happens (downstream effects)
- `evidence_passages` — Verbatim source quotes supporting the claim
- `extraction_type` — causal_mechanism / empirical_pattern / normative_heuristic / descriptive_model
- `source_books` — Source book identifiers
- `source_diversity` — Number of distinct sources (BORP)

### Enrichment Fields (S4 output)
- `application` — WHEN to use this principle (prescriptive)
- `failure_mode` — HOW it fails (specific failure mode)
- `elaboration` — Non-obvious implications, edge cases
- `depth` — universal / cross_domain / domain / specialized
- `discipline` — Academic discipline
- `domains` — Application domains

### Verification Fields (S5 output)
- `verification_status` — PASS (DeBERTa NLI entailment ≥ 0.10) or QUARANTINE
- `epistemic_status` — corroborated (strong ISOR + PASS), source-supported (PASS only), cross-source-unverified (ISOR only), speculative (neither)
- `isor_rating` — strong / medium / weak (author independence, domain diversity, source count)
- `isor_score` — 0.0–1.0 composite score
- `confidence_score` — Weighted: mechanism 15% + DeBERTa NLI 75% + enrichment 10%
- `nli_entailment_score` — Raw DeBERTa entailment score (0.0–1.0)
- `enrichment_warnings` — Quality flags (ENRICH-SHORT-APP, ENRICH-FM-ECHO, etc.)

## Evaluation Criteria (for frontier LLMs: Kimi, Claude, DeepSeek, Qwen)

### Quality Dimensions (rate each FB 1-5):
1. **Definition clarity**: Is the definition precise, non-redundant, and standalone? (not just "X is when Y")
2. **Mechanism quality**: Does it explain HOW with a causal chain? (not just "because it's important")
3. **Boundary specificity**: Are the limits concrete and falsifiable? (not "sometimes" or "it depends")
4. **Evidence fidelity**: Does the definition match the source passages? (verify against evidence_passages)
5. **Uniqueness**: Is this genuinely convergent across sources? Or could it come from one book?

### Red Flag Patterns:
- Definition repeats mechanism (e.g., "X occurs because X happens")
- Mechanism is tautological ("works because it's effective")
- No falsifiable boundary ("can fail under certain conditions")
- Single-source echo (all evidence from one author/book)
- Obvious/trivial principle ("good design is important")
