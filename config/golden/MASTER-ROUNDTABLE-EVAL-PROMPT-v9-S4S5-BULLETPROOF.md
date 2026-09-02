# MASTER ROUNDTABLE EVAL PROMPT — v9 (S4 + S5 bulletproof audit)

> Copy this verbatim into Claude AND ChatGPT (and any third family you trust).
> Do NOT give them your local runtime; give them the FILE LIST + the questions.
> Ask each model independently; diff their answers; treat only *intersection*
> of confirmed findings as actionable.

---

## ROLE

You are a **senior RAG / systems / software principal engineer** performing a
hostile, forensic, red-team audit of a local-first knowledge pipeline called
**Maxwell OS v3.0** (a sovereign, multi-model, cluster-before-extract RAG that
converts EPUBs → MD → chunks → semantic clusters → extracted FBs → classified →
NLI-verified → SQLite + Parquet).

Your ONLY deliverable is a verdict on this question:

> **Are Stage 4 (S4 classification) and Stage 5 (S5 NLI verification) "bulletproof"
> — i.e. free of hidden/silent errors, contamination, leaks, cascading effects,
> bugs, drift, mismatches, blind spots, gaps, conflicts, threats, and risks —
> and is every element (golden examples, config files, scripts, decisions)
> internally consistent, future-tax-proof, and low-tax-proof?**

If the answer is NOT bulletproof, enumerate every residual risk with its
severity (BLOCKER / P1 / P2 / OBSERVATION), the exact file + line/field, and a
constructive remediation instruction. Do NOT soften findings.

---

## REPO LAYOUT (what to check — each of these exists in the repo)

```
CONSTITUTION.md, DECISION-LOG.md, MASTER-TASK-REGISTER.md, AGENTS.md
config/
  taxonomy_v5.yaml          # canonical domains (35) + disciplines (75) + raw aliases
  synonym_map.yaml          # domain synonyms + keywords (kind-scoped)
  alias_map.yaml            # discipline aliases (Phase 0b curated remap, 215 entries)
  content_types.yaml        # principle/PT/PI/GE/TI + extraction_type + body fields
  pipeline_config.yaml      # all thresholds/model names/golden wiring (C12 source)
  decisions.yaml            # machine-readable decision registry
  golden/
    stage4_golden.yaml      # S4 CLASSIFICATION few-shot (5 examples) — INJECTED
    stage2_fewshot_convergent.yaml          # S2 extraction few-shot (84)
    stage2_fewshot_convergent_nontype.yaml  # (75)
    stage2_fewshot_single_source.yaml       # (21)
    stage2_fewshot_trimmed_12.yaml          # (12)
pipeline/
  schemas.py                # CANONICAL_DOMAINS/DISCIPLINES + synonym index + match_to_canonical
  stage4_merge.py           # S4: CRIBS + classification + map_to_canonical_with_fallback
  stage4_merged_call.py     # S4 classifier prompt (open-set) + golden injection
  stage5_verify.py          # S5: DeBERTa-v3-large NLI only (fail-closed)
  taxonomy_manager.py       # D2399 dynamic promote/demote (update_counts/check_for_replacements)
  s4_golden.py              # stage4_golden loader/formatter (fail-closed D2454)
tests/
  test_taxonomy_disjointness.py   # cross-kind kind-safety CI (4 tests)
  test_stage4_golden_contract.py  # golden ↔ canonical ontology conformance
```

---

## AUDIT DIMENSIONS — check EVERY one against the repo

For each dimension, state **CONFIRMED CLEAN** or **FAIL** with evidence:

1. **Contamination (cross-kind)** — Does any *domain* label equal a canonical
   *discipline* (or vice-versa), in: the canonical lists, the raw-alias lists,
   the synonym/keyword/alias maps, the golden `domain`/`discipline` fields, the
   S4 `domains_raw`/`discipline_raw` outputs, and the D2399 promotion path?
2. **Leak** — Any local path, API key, source title, or PII that should not ship?
3. **Cascading effect** — If S4 emits a wrong-axis label, does it survive to
   SQLite, to D2399 promotion, to golden re-training, to retrieval? Trace the
   blast radius.
4. **Bug / silent error** — Any `except: pass`, silent fallback to a hardcoded
   default, `[:N]` truncation, or `.get()` default that hides a real failure?
   (C16: every except must log AND raise.)
5. **Drift** — Do config values, golden counts, decision summaries, and code
   disagree? (e.g. `golden_max_examples` vs `meta.total_examples`; benchmark n
   vs production n; stale hashes/commits in `.golden_meta.json`.)
6. **Mismatch / inconsistency** — Golden labels vs `CANONICAL_DOMAINS/DISCIPLINES`;
   prompt vocabulary vs schema vocabulary; `ai systems` vs `ai & agents`
   (near-duplicate canonical domains taught as two labels).
7. **Blind spot** — A field/label that is *written* but never *validated* or
   never *consumed* (e.g. stage2 golden `domain`/`discipline` metadata that no
   formatter emits and no test enforces).
8. **Gap** — A missing guard: no CI test for X, no fail-closed for Y, a file
   referenced by code but untracked in git (e.g. `alias_map.yaml`).
9. **Conflict** — Two decisions/specs that contradict; a test that asserts
   canonical disjointness while a prompt remains open-set.
10. **Threat / risk** — What is the highest-probability × highest-impact failure
    if S4 and S5 run unattended tonight, and what is the cheapest mitigation?

---

## SPECIFIC VERIFICATION TASKS (do these, cite file:line)

1. **Golden ↔ taxonomy consistency.** Load `config/golden/stage4_golden.yaml`
   and every `stage2_fewshot_*.yaml`. For every `discipline`, `domains`,
   `domain`, `accept_any_of_discipline` value: is it a canonical label, and is
   it on the CORRECT axis? Report every cross-kind and every non-canonical
   label, per example id. Distinguish "INJECTED into a prompt" vs "dormant
   metadata" and judge severity accordingly.
2. **S4 classification prompt.** Read `stage4_merged_call.py` classification
   prompts. Is the output vocabulary closed (enumerated) or open-set? Does the
   prompt enforce domain/discipline disjointness? Does it match the golden's
   contract? Where could a wrong-axis label be emitted?
3. **S5 verification.** Read `stage5_verify.py`. Confirm: single NLI model,
   fail-closed (QUARANTINE on any failure), no silent PASS, threshold from
   config. What does S5 *not* verify (e.g. non-principle sidecar bodies, raw
   label axes)? State the residual surface explicitly.
4. **D2399 promotion.** Read `taxonomy_manager.py`. Confirm the cross-kind guard
   (`_is_opposite_kind`) is wired into BOTH the long-tail count path and the
   challenger path. Is there a free-slot path, or does it always demote the
   weakest even when under cap? Is promotion human-gated?
5. **Kind-safe matcher.** Read `schemas.py`. Confirm `match_to_canonical` and
   `map_to_canonical_with_fallback` short-circuit opposite-axis canonicals, and
   `_build_synonym_index` excludes opposite-kind aliases. Is there ANY path that
   still coerces a discipline label into a domain canonical?
6. **Stamps + raw preservation.** Confirm `*_raw` fields survive S4→S5→S6 and
   that `schema_version`/`gen_model`/`pipeline_commit` are stamped on every
   persistent object (R14).
7. **Readiness verdict.** Given all of the above, is it safe to run S5 tonight?
   Give a GO / NO-GO / CONDITIONAL-GO with the conditions.

---

## OUTPUT FORMAT

```
VERDICT: S4 bulletproof?  [YES/NO]
VERDICT: S5 bulletproof?  [YES/NO]
READINESS: [GO / NO-GO / CONDITIONAL-GO]  (conditions if conditional)

BLOCKERS (list, file:line, remediation):
P1 (list):
P2 (list):
OBSERVATIONS (list):

TOP-3 cheapest highest-value hardening actions:
```

Be specific. Every claim must cite a file and a line or field. Prefer falsifiable
statements ("X is enforced at stage4_merge.py:NNN") over adjectives ("robust").
