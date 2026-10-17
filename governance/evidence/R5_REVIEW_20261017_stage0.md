# R5 VERIFIER RECEIPT — the Stage-0 budget / failure-class fix

- **date:** 2026-10-17
- **generator (this agent):** the BUG-897/896/898 patch to `pipeline/stage0_convert.py`, `pipeline/pipeline_paths.py`,
  `config/pipeline_config.yaml`, `scripts/apply_admission.py`
- **verifier (R5: a DIFFERENT model family):** `gemma-4-E4B-it-MLX-4bit` (OMLX), temperature 0.0, single-shot
- **journal:** `DJ-20261017T154522Z-c2c8` (opened BEFORE the call; `may-write: none`)
- **subject:** `git diff` of the four files (459 lines)

## The questions put to the verifier

1. Does any code path still return a bool where the dict with `ok/failure_class/meaning/detail` is expected?
2. Can `docling_budget_s` return 0, negative, or crash on a 0-byte or missing file?
3. Is any exception swallowed silently (an except branch that neither raises nor becomes a `failure_class`)?
4. Can the failure-ledger append truncate or corrupt the checkpoint file?
5. Name at most 3 REAL defects, or write `NO DEFECTS FOUND`.

## The verifier's answer (verbatim)

> 1. No. Both `convert_epub` and `convert_pdf` now return a structured dictionary (`dict[str, Any]`) upon
>    completion, replacing the previous boolean return type.
> 2. The function reads configuration values. If the configuration values (`S0_DOCLING_FLOOR_S`, etc.) are set to
>    zero or negative, the function will return that value, but it will not crash on a missing file, as it only
>    reads configuration parameters, not the file itself.
> 3. No. The changes introduce `_failure()` which forces a structured return or raises a `RuntimeError` for
>    unhandled configuration issues, ensuring exceptions are accounted for.
> 4. No. The failure ledger uses a sidecar `.failures.jsonl` file, which is designed for append-only logging,
>    mitigating corruption risk to the main checkpoint.
> 5. NO DEFECTS FOUND.

## What the review CHANGED (a verifier is only worth its findings)

Answer **2** named a real hole the generator had left: a declared `0` was honoured literally, which would turn
every work into an instant `budget_expired`. `pipeline/pipeline_paths.py::_s0_budget` now refuses a value `<= 0`
at import, so a budget that permits no work cannot be declared at all.

## What the review did NOT cover (stated, not implied)

The verifier was asked defect questions, not conformance questions. It did not check C12/C17/C18, the fingerprint
semantics, or the applier's row-state machine. Those were checked separately and are receipted here:

- **fingerprint (BUG-614):** `data/checkpoints/stage0_convert.jsonl` carries **no `.code_fingerprint` sidecar** (it
  is a Jul-19 legacy checkpoint), and `check_stage_code_fingerprint` explicitly permits a legacy checkpoint with
  no sidecar. Editing `stage0_convert.py` therefore cannot fire a mismatch on the next apply; the new code stamps
  the sidecar on its first run and guards every edit after that.
- **cascade:** `pipeline/pipeline_paths.py` appears in NO stage's `fingerprint_files`, so editing it cannot make
  another stage refuse to resume. Verified by grep over `config/pipeline_config.yaml`.
- **departure from the plan:** `scripts/apply_admission.py:572` held `timeout=1800`, a THIRD magic ceiling between
  acceptance and admission, and the real outer wall. It now reads the declared `stage0.conversion_budget.stage_timeout_s`;
  `pipeline_paths` asserts at import that this value strictly EXCEEDS `docling_ceiling_s` (D-3034 — a ceiling the
  outer wall can never reach is a declaration with no referent).

## Known-answer controls run against this change (not the verifier's)

| control | expected | observed |
|---|---|---|
| epub with a case-only spine mismatch (HBR) | `container_unreadable` | `container_unreadable` — `Pandoc rc=64 … No entry on path: OEBPS/cover.xhtml` |
| epub whose content.opf has no manifest (Generating Sound) | `container_unreadable` | `container_unreadable` — `Pandoc rc=64 … Unable to find element: QName … manifest` |
| the PDF that failed inside the live apply (FULLTEXT01, 0.6 MiB) | converts | `ok` in **28.5 s** under a **323 s** declared budget |
| the same PDF with the ceiling forced to 1 s | `budget_expired` | `budget_expired`, naming the floor/per-MiB/ceiling arithmetic |
| a failure class nobody declared | refused | `ValueError` — FATAL |
| a declared budget of 0 | refused | `RuntimeError` at import (added AFTER this review) |
