# Assignment-path diagnosis - why the pipeline "never selects" tail slots (2026-09-21, D-310)

**Verdict: the premise was false. There is no global assignment/emission failure.** The claim came from the
contra-stratified 60-row ANCHOR-1 sample and does not survive a whole-corpus measurement. What IS real:
extreme concentration plus a very long tail, and a quarantine rate that dominates the corpus.

## Measurement (read-only, `knowledge pipeline/maxwell.db`, 7,995 rows, `provenance=llm_extracted_from_source`)

| axis | slots in menu | slots emitted | min rows | median rows | slots < 20 rows |
|---|---|---|---|---|---|
| discipline | 61 | 61 | 6 (`ecology`, `robotics`, `computational theory`) | 85 | 13 |
| domains | 43 | 43 | 28 (`design systems`) | - | 0 |

* Top-6 disciplines hold **38.2%** of the corpus: psychology 907, emerging 757, strategic thinking 445,
  human-computer interaction 353, software engineering 314, cultural design 281.
* Top domains: business operations 1,538, marketing & communications 1,381, digital product 804.
* **Long tail (discipline < 20 rows):** ecology 6, robotics 6, computational theory 6, privacy & surveillance 8,
  color theory 9, design psychology 9, generative design 10, creative coding 12, game design 12, generative ai 13.
* `status`: QUARANTINE 4,696 (58.7%) / PASS 3,299 (41.3%).
* ANCHOR-1 60-row sample covers only **23/61 disciplines** and **33/43 domains** -> 39 disciplines and 11 domains
  absent *in the sample*. That sample deliberately over-selects boundary/contradiction rows, so its sparsity is
  expected and must not be read as pipeline behaviour.

## Mechanism (what the code actually does)

1. Production classification does **not** use a top-k candidate shortlist. `pipeline/closed_menu.py` renders the
   complete closed menu (61 disciplines / 43 domains / 8 content types) from config; `stage4_merge.py` only imports
   it for the `menu_hash` traceability stamp (R1/D-279) and the LLM labels against the full vocabulary.
2. `config/pipeline_config.yaml` `retrieval_benchmark.top_k: 10 / candidate_pool: 30` belongs to
   `pipeline/retrieval_benchmark.py` (a retrieval benchmark), **not** to the classification path - a plausible but
   wrong suspect for the earlier hypothesis.
3. Labels are post-mapped deterministically (`match_to_canonical`, both axes) - see
   `scripts/audit_full_corpus_labels.py` - so tail sparsity cannot come from alias resolution either.

=> The tail is a **model-prior + slot-definition-similarity** effect (the LLM prefers broad, well-described slots),
not a truncation, retrieval or mapping defect. Any future fix is a *menu-description / calibration* change, not a
code-path fix, and must be validated against the frozen ruler (D-300 bar) before it is adopted.

## Consequences for the open items

* **No taxonomy re-basing is needed** for assignment reasons (D-307 already established v6 added zero slots).
* Repair priority should follow *measurement*, not the sample: (a) the 4,696 QUARANTINE rows, (b) the 13
  sub-20-row discipline slots (candidate boundary re-derivations in the D-285/D-289 style), (c) concentration
  (top-6 = 38.2%) as a calibration question.
* Any claim of the form "the pipeline never emits X" must be re-measured on the whole corpus before it enters a
  decision record. This is now the standing rule (D-310).
