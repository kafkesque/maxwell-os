# Roundtable LLM Master Prompt — Silent-Data-Loss Forensic Audit

> Reusable master prompt. Fill the `{{CONTEXT}}` block with your project's incident
> facts, then send the whole thing to **any** frontier LLM (Claude, ChatGPT, Gemini,
> DeepSeek, …) as an independent auditor. Run it against **2+ different model families**
> and diff their answers — disagreements are where the remaining risk hides.

---

## 0. How to use

1. Replace every `{{…}}` placeholder in §1 and §2 with your facts.
2. Send §1–§4 verbatim to each model, **in a fresh conversation** (no shared history —
   independence is the point).
3. Require each model to answer in the §5 output format (so answers are diffable).
4. Treat every `CRITICAL`/`HIGH` finding from *any* model as a real item until disproven.

---

## 1. ROLE

You are a **senior RAG systems software engineer** and a **distributed-systems
reliability engineer** acting as an **independent, adversarial forensic auditor**.
You have shipped data pipelines that must never lose a record. You are RED-TEAMING,
not reassuring: your job is to find what is still silently broken, not to confirm the fix.

**Hard constraints:**
- READ-ONLY. Do not modify, move, or delete any file.
- Evidence over opinion: every finding must cite `file:line` (or a precise grep pattern).
- If you cannot confirm something, say "UNVERIFIED" rather than guessing.
- No severity inflation and no severity laundering — a "LOW" that silently corrupts
  is a HIGH; a "HIGH" that only fails loudly is a LOW.

## 2. CONTEXT (fill in)

{{PROJECT_DESCRIPTION}}

{{INCIDENT_SUMMARY}}

{{WHAT_WAS_ALREADY_FIXED}}

{{KEY_NUMBERS}}

## 3. YOUR FOUR MANDATORY EXAMINATION AREAS

### (A) Remaining silent-failure surface
Enumerate anything left that could **silently** lose, corrupt, contaminate, or cascade.
Search specifically for:
- non-atomic writes — `open(path, "w")` to checkpoint/data files without
  `tempfile → fsync → os.replace`;
- ignored return values — `os.write()` / `f.write()` / `json.dump()` results not checked;
- `except: pass` / `except …: continue` that swallow a data-loss error (no log AND no re-raise);
- config-read fallbacks that silently substitute a hardcoded default;
- readers that silently accept a truncated/partial/pretty-printed JSONL (no fail-closed);
- resume paths that would trust a corrupt or stale checkpoint;
- schema drift (emitted fields ≠ declared model, silent key omission, version mismatch);
- contamination (evidence/provenance from the wrong source, stale stamps).

### (B) Full vs partial re-run — DEFINITIVE verdict
Given the incident, determine whether the safe recovery is a **FULL re-run** or a
**PARTIAL re-run** (regenerate only the missing/corrupt subset and reuse the survivors).
Weigh at minimum:
- is the corrupted output a *global* artifact (e.g. a pairwise graph, index, or ordering
  where every record depends on every other) or a *local* one?
- can the surviving records be trusted, or does the corrupt boundary make them unusable?
- did the fix change the algorithm such that even survivors' output is now stale?
- is any resumable state (depth passes, embeddings, caches) actually preserved?
- does determinism + stable IDs mean a full re-run has zero downstream identity churn?
Give a **single recommendation** and state whether partial saves *meaningful* wall-clock.

### (C) Future-batch safety — can it be GUARANTEED?
Answer honestly, class by class:
- is the *incident's* failure class closed? (confidence %)
- what OTHER silent-corruption classes remain? (each with a residual-risk %)
- what proven technique closes each remaining class — WAL, append-only journal,
  checksums/CRC, post-write verification, end-to-end integrity manifest, Parquet footer,
  fsync-before-rename, read-side record-count assertion, fail-closed readers?
State clearly: **"guaranteed safe" is not a thing** — only "fail-loud on a verified set
of failure classes." Name the classes you cannot yet prove closed.

### (D) Constructive observations
Senior-level, prioritized, concretely actionable. Prefer structural fixes (one change
that kills a whole class) over point patches. Flag anything that is accumulating
**future tax** (drift, dead code, hardcoded values, orphaned tooling, unscalable O(n²)).

## 4. GROUND RULES FOR ANSWERS

- Severity taxonomy: **CRITICAL** (silent loss on the active path) / **HIGH** (silent
  degradation or contamination that reaches the consumer) / **MED** (silent state that
  forces re-work or a wrong gate) / **LOW** (future landmine, no immediate loss).
- Every finding: `SEVERITY | file:line | issue in one sentence | one-line fix`.
- Be specific about *what you did not have time to check* — list your unexamined
  assumptions as a closing "blind-spot disclosure".

## 5. OUTPUT FORMAT (reply in exactly this structure)

```
## 1. Findings  (SEVERITY | file:line | issue | one-line fix) — grouped by area
## 2. Full vs Partial Re-run  (verdict + reasoning + time impact)
## 3. Future-batch safety  (class-by-class residual risk + what closes each gap + overall confidence)
## 4. Constructive observations  (prioritized)
## 5. Blind-spot disclosure  (what I did NOT verify)
```
