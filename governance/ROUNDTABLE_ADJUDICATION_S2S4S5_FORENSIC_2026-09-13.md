# ROUNDTABLE ADJUDICATION — S2/S4/S5 Forensic Audit (2026-09-13)

> **Adjudicator:** goose (S-tier senior RAG engineer / knowledge architect / SWE)
> **Audited:** Claude, GPT, GPT-5.6-Luna, Qwen (4 frontier findings in `temp/`)
> **Cross-checked:** deterministic repo verification + Qwen3.8-27B (local OMLX) reliable-pair ruling
> **DeepSeek-v4-pro/v4-flash:** UNUSABLE for this task (reasoning-passthrough empty `content` — DELEGATE-001). Documented, not silently skipped.

---

## 1. Verification verdict — every load-bearing claim, checked against the repo

| # | Claim (author) | Verdict | Deterministic evidence |
|---|---|---|---|
| C1 | "38.2% is not measured teacher error; confirmed non-principle = 1,365/7,966 = **17.1%**; 21.1% abstain" (GPT/Claude/GPT5.6) | ✅ CORRECT | Vote: 1,037+177+120+15+16 = 1,365; +1,681 abstain = 3,046/7,966 = 38.2% |
| C2 | "`commit_non_fb_types: false` — S2 detects 1,147/8,410 (13.6%) non-principle and discards it" (Claude) | ✅ CORRECT — most important under-emphasized root cause | `config/pipeline_config.yaml:460`; `pipeline_paths.py:358`; `decisions.yaml:4979` (1147/8410 = PT 796/PI 204/TI 143/GE 4) |
| C3 | "S4 `_resolve_content_type` falls back `route=FB`→`principle`" (GPT) | ✅ CORRECT | `config/content_types.yaml:170` (`FB: principle`); BUG-148 "third drift source" |
| C4 | "convergent S2 is principle-only by design; single-source under-detects; D2589 fixed rules injection" (Claude/GPT) | ✅ CORRECT | BUG-231; `stage2_extract.py:334` SYSTEM_PROMPT "convergent principle extraction engine" |
| C5 | "golden set = 69/1,027 (6.7%) 4-axis verified; 93.3% unverified silver" (Claude/GPT) | ✅ CORRECT | BUG-241 |
| C6 | "`schemas.py` Pydantic models never instantiated at runtime" (GPT5.6) | ✅ CORRECT | `pipeline/schemas.py:35` |
| C7 | "decisions.yaml = 590 at pinned commit, not 591" (GPT/GPT5.6) | ✅ CORRECT (contextual) | `git show 6e295d4:config/decisions.yaml` = `total: 590`; my 591 = uncommitted D2615 in working tree |
| C8 | "BUG-228 dead schema fields; BUG-151 taxonomy overlap (`education` dual-listed + 267 aliases)" (Claude) | ✅ CORRECT | buglog L20, L25 |
| C9 | "BUG-238's 12.7–16.6% splices multiple rounds (12.7% CI 7.3–18.0%; 29.3% borderline; 15.7–16.6% frozen)" (Claude) | ✅ CORRECT | BUG-238 full entry |
| C10 | Qwen "golden ~38% corrupted (CI 35–42%)" | ❌ WRONG | Conflates *unverified* (93.3%) with *corrupted*. Defensible framing = "93.3% unverified; content_type sensitivity ~176–392/1,027". |
| C11 | Qwen "depth abstain = 4,094" | ⚠️ MISLEADING | 4,094 = empty-depth across ALL 7,966 rows (1,681 ct-abstain + 1,048 depth-abstain + 1,365 non-principle). The handoff's "1,048" was depth-abstain-among-principle. Different aggregation. |

**Result:** all four auditors are highly accurate on the facts; Qwen alone made two over-reaches (C10, and "retire gpt-oss immediately" / "Snorkel/Dawid-Skene" — see §2).

---

## 2. Reliable-pair ruling on the 6 disputed propositions

Qwen3.8-27B (local) ruled **GPT/Claude correct on all 6**. DeepSeek failed (DELEGATE-001). My independent judgment **concurs**, with two refinements:

| # | Dispute | Winner | Adjudicator ruling |
|---|---|---|---|
| P1 | "38% golden corrupted" vs "93.3% unverified / 176–392 sensitivity" | **GPT/Claude** | "Corrupted" requires evidence of a wrong label; 919/1,027 have `content_type=None` (unlabeled, not mislabeled). The honest number is *unverified*. |
| P2 | Retire gpt-oss **now** (Qwen) vs **gated** (GPT/Claude) | **GPT/Claude** | Immediate retirement = capability drop with no validated local replacement. Gate on a local labeler beating gpt-oss on a frozen, book/author-disjoint holdout. Until then gpt-oss = a labeled LF, not ground truth. |
| P3 | Snorkel/Dawid-Skene (Qwen) vs **cleanlab** (GPT/Claude) | **GPT/Claude** | Dawid-Skene already measured **48.7% false-flag in-repo** — recommending it again is empirically unsound. cleanlab (confident learning) is a genuinely different mechanism (single-classifier confident-joint, no multi-annotator assumption). |
| P4 | Pydantic-only (Qwen) vs SQL-CHECK-now + SHACL-periodic (GPT/Claude) | **Not a real conflict** | Pragmatic call = instantiate the Pydantic boundary + SQL CHECK constraints *today* (leak/disjointness/enum), SHACL only if/when the layer goes RDF. Do NOT add RDF just for SHACL. |
| P5 | SetFit "8–16 shot" (Qwen) vs hierarchical coarse-to-fine (GPT/Claude) | **GPT/Claude** | SetFit's few-shot claim is over-optimistic for a 61-way near-duplicate ontology. Production head = hierarchical (coarse 10-way top-1 54% already), SetFit only for the rare leaves. |
| P6 | `commit_non_fb_types:true` = single highest fix (Claude) | **Refined** | Highest-leverage *zero-cost* fix, YES — but not sufficient alone: it addresses the 13.6% discard; the 17.1% stored non-principle and the label noise need concurrent fixes. |

---

## 3. ULTIMATE SOLUTION (adjudicator's synthesis)

**North star:** a local, $0-marginal, sovereign pipeline where every stored principle is correctly content_typed, correctly depth/discipline/domain-labelled, evidence-verified, and provenance-stamped — with **no silent recurrence** of the 11 failure modes.

**Phase 0 — Stop the bleeding (0 LLM tokens, ~hours):**
1. Flip `commit_non_fb_types: true` (D2590 already *decided*, never applied — apply it).
2. Deprecate `route` as ontology carrier: missing `content_type` → **quarantine**, never `principle` (finish BUG-148's open item).
3. Apply the **1,365 vote-confirmed non-principle relabels** from `joint_vote_production_checkpoint.jsonl` to the DB (deterministic, no LLM) — demote noise_drop/PT/PI/TI/GE out of the principle index.
4. Instantiate the Pydantic boundary (make `schemas.py` runtime, not documentation).

**Phase 1 — Freeze a verified core (gates everything):**
5. Human-adjudicate the Phase-0 149-core + the D2615 298-sample (**~435 verified rows**) as the *sole* eval target. Demote the 1,027 silver golden to a "silver pool" (never used for eval).

**Phase 2 — Rebuild the label stack (local, $0):**
6. Weak-supervision label model seeded by the verified core; LFs = cleanlab + reliable-pair vote (only on flagged disagreement, NOT full-corpus) + NLI; calibrate LF reliability on the core.
7. Serve with **hierarchical local ModernBERT** (coarse 10-way gate + fine 61-way) + **SetFit** for rare classes + **conformal/selective abstention** (not raw softmax).
8. Extend **S5** (same DeBERTa) to verify **classification-entailment** ("does this FB entail being `{content_type}`/`{discipline}`?"), in addition to evidence-entailment.

**Phase 3 — Retire gpt-oss (gated, not immediate):**
9. Retire gpt-oss as production teacher only when the local labeler beats it on a frozen, book/author-disjoint holdout: macro-F1 ≥0.75, worst-class precision floor, calibrated selective risk, 2-seed stability. Until then gpt-oss = a labeled LF, never ground truth.

**Phase 4 — Rebuild the store once, then enforce invariants:**
10. Re-derive the 7,995 store **once** (never repeatedly mutate a moving ontology). Ship the 11-mode invariant table as **executable release gates**: fail-closed-to-quarantine (risk), runtime Pydantic+SQL CHECK + periodic SHACL (leak), frozen book/author-disjoint holdout (blindspot/contamination/drift), cross-family generator≠verifier (conflict), R14 provenance stamps (inconsistency), buglog + CI contract tests (bug), fingerprint manifests (mismatch/drift).

**The 11-mode guarantee, honestly stated:** the goal is *no silent recurrence*, not *impossibility* — every violation must fail the release gate or route to quarantine/human review. "Guaranteed no noise" is achievable for the *structural* modes (leak, conflict, mismatch, drift, inconsistency) via runtime constraints; the *semantic* modes (blindspot, gap, wrong-scope) require the frozen verified holdout + a live human review queue, not a magical classifier.

---

## 4. Corrective actions for the repo (from this adjudication)

1. **Commit D2615** (my active-learning sampler + decisions.yaml 591) — it is currently uncommitted, which is exactly the "decided → applied lag" the auditors flagged.
2. **Apply `commit_non_fb_types: true`** (D2590 already decided).
3. **Buglog BUG-243:** record the DeepSeek reasoning-passthrough failure on open-ended adjudication (vs the vote's tight-JSON prompt which works) — a real operational limitation, not a one-off.
4. **`route` deprecation** — close the open BUG-148 item ("content_type authoritative; missing → quarantine").
