# Master Prompt — Exhaustive S2 Drift Audit, Solution Adversarial Review, S2 Label/Body Audit, S4/S5 Acceleration, and Market Research

> **Purpose:** This document is a self-contained brief for an external LLM (Claude, ChatGPT, or a
> third independent model) to **independently scrutinize** the Maxwell OS v3.0 `extraction_type`
> drift remediation. It contains the verified findings, the proposed "ultimate solution," a raw S2
> data audit, the S4/S5 acceleration question, and market-research leads. **Do not assume any
> conclusion below is correct — challenge it.**
>
> **Ground rule:** answer from the *evidence* (the numbers, the prompt text, the golden files, the
> data), not from the framing. If a claim is unverifiable or overstated, say so.

---

## 0. System context (read first)

Maxwell OS is a local-first, sovereign knowledge pipeline (`$0` marginal cost, C1/C3). Eight stages:

```
S0 convert → S0.5 metadata → S1 chunk → S1.3 prefilter → S1.5 embed+cluster
→ S2 extract (LLM) → S4 merge/classify (LLM) → S5 verify (DeBERTa NLI) → S6 commit (SQLite+Parquet)
```

Models: S2 generator = **Qwen3-Coder-30B-A3B-Instruct-MLX-4bit** (`qwen` family); S4 classifier =
**gpt-oss-20b-MXFP4-Q8**; S5 verifier = **DeBERTa-v3-large NLI** (local); embeddings = **bge-m3**.
`temp=0.0` enforced. **R5 (Generator ≠ Verifier):** verification/gate roles must use a *different
model family* than the generator.

Each S2 knowledge object carries **two orthogonal labels** (decision D2323):

- **`content_type`** (functional ROLE, 5 values): `principle`, `process_template` (PT),
  `process_instance` (PI), `tool_instruction` (TI), `growth_edge` (GE).
- **`extraction_type`** (epistemic FORM, 4 values): `causal_mechanism`, `empirical_pattern`,
  `normative_heuristic`, `descriptive_model`.

The two are **supposed to be independent** (orthogonal axes). The bug being audited is that they
became entangled.

---

## 1. The problem

The `extraction_type` (FORM) label **drifted** between the two S2 extraction paths on the T1.1 run
(`knowledge pipeline/stage2_extract/t11/checkpoint.jsonl`, 8,410 records):

| Path | Records | causal | empirical | normative | descriptive |
|---|---|---|---|---|---|
| **convergent** (multi-source clusters) | 2,649 | **11%** | 21% | 30% | 37% |
| **single-source** (single/singleton) | 5,761 | **60%** | 19% | 13% | 8% |

An n=30 sample audit estimated **~43% mislabel rate**; an external 2-LLM ensemble (Claude+ChatGPT)
confirmed **~40–50% of sampled causal labels are over-claimed**.

---

## 2. Verified findings (to be independently re-examined)

### F1 — The R1 prompt fix was applied to only ONE of four prompts (primary causal-drift cause)

Commit `df1fbfd` added a "DECISION ORDER + DECOUPLING RULE + ~1/3-causal CALIBRATION" block to the
**convergent** `SYSTEM_PROMPT` only. The three prompts that actually produced the single-source
drift were **not** updated:

| Prompt string | Has decision-order? | Feeds |
|---|---|---|
| `SYSTEM_PROMPT` (convergent) | ✅ | 2,649 records → 11% causal |
| `SINGLE_SOURCE_SYSTEM` | ❌ | 5,761 records → 60% causal |
| `SINGLETON_SYSTEM` | ❌ | (singletons) |
| `SINGLETON_BATCH_SYSTEM` | ❌ (inherits SINGLETON via `.replace`) | (batched singletons) |

**Claim to verify:** the 60% vs 11% inversion is driven by this prompt asymmetry, not by data
differences between the paths.

### F2 — The golden few-shot is NOT causally over-weighted (earlier "51–75%" was a miscount)

Positive-only `extraction_type` distribution in the golden few-shot files:

| File | positives | causal | empirical | normative | descriptive |
|---|---|---|---|---|---|
| `config/golden/stage2_fewshot_convergent.yaml` | 61 | **33%** | 14 | 14 | 14 |
| `..._convergent_nontype.yaml` | 52 | **33%** | 12 | 12 | 12 |
| `..._trimmed_12.yaml` | 6 | 50% | 1 | 1 | 1 |
| `..._single_source.yaml` | 6 | **17%** | 1 | 1 | **50%** |

The earlier "44/86=51%, 41/77=53%, 9/12=75% causal" figures **included hard negatives** (which all
carry a bogus `causal_mechanism` label). The real positive pools are ~33% causal, matching the
prompt's own "~1 in 3" calibration.

### F3 — The single-source golden few-shot has a REAL descriptive bias (a genuine mislabel source)

`config/golden/stage2_fewshot_single_source.yaml` labels **both `tool_instruction` examples as
`descriptive_model`**:

- `FAISS read_index` → `descriptive_model`
- `Depth-First Search Traversal` → `descriptive_model`

These are **prescriptive commands/algorithms** → should be `normative_heuristic`. This **directly
contradicts** `config/content_types.yaml` (D2417: `tool_instruction → normative_heuristic`). The
single-source golden is 50% descriptive, teaching the model "methods/instructions → descriptive."

### F4 — Golden hygiene defect: hard negatives carry bogus causal labels

`convergent` (23), `convergent_nontype` (23), `trimmed_12` (6) hard negatives all have
`extraction_type: causal_mechanism` in `expected_fb`, despite being rejection examples
(`route=NULL`). They don't leak into the prompt today (negatives are formatted as rejection *text*),
but they corrupt distribution audits and are latent contamination.

### F5 — Config↔golden↔prompt conflict (role↔form coupling)

- Config D2417 `content_to_extraction_type`: `tool_instruction → normative_heuristic`.
- Golden single-source: `tool_instruction → descriptive_model`.
- `SINGLETON_SYSTEM` prompt still embeds "MAPPING RULES" (`empirical→growth_edge`,
  `normative→process_template`) — the role↔form coupling that D2427 (R2) says to delete.

These three disagree. **Question:** which is the source of truth, and should the coupling be
removed entirely (R2) rather than patched per-row?

### F6 — The relabel script is an R5 violation + no safety gate

`pipeline/stage2_relabel_extraction_type.py` re-labels using `GEN_MODEL` = Qwen3-Coder — the **same
model family** that caused the drift. A smoke test (`--limit 8`) showed it can introduce a **new
descriptive drift** (`Fundraiser Welcome Protocol`→descriptive, `Extreme Customer Research Method`→
descriptive). It has no `--verify-sample` gate and is O(n) single LLM calls (no batching).

---

## 3. The proposed "ultimate solution" (scrutinize this hard)

> **Fix the generator, don't re-label the output.** Post-hoc relabeling t11 fixes the symptom; the
> drift recurs on the next S2 run while the single-source prompt + golden remain broken.

1. Port the R1 decision-order + decoupling + calibration to `SINGLE_SOURCE_SYSTEM`,
   `SINGLETON_SYSTEM`, `SINGLETON_BATCH_SYSTEM`.
2. Fix the golden: relabel the 2 TI examples → `normative_heuristic`, rebalance away from 50%
   descriptive, strip bogus labels from all hard negatives.
3. Re-run S2 (single-source path) on a copy; confirm causal drops toward ~20–33%.
4. Deterministic **rule-certain** relabel of t11 only for mechanically-decidable cases (e.g.
   `syndrome`→descriptive, `method/technique/function`→normative); leave ambiguous records flagged
   for human review. **No blind LLM relabel of 5,761 records.**
5. Verify on a fixed holdout before touching production.

**Adversarial questions (answer explicitly):**
- Is "fix the generator" actually sufficient, or is the R2 axis refactor (`justification × modality`)
  required first? Would fixing the prompt alone just relocate the drift?
- Is the deterministic rule-certain pass safe, or does it risk its own new drift (e.g. mis-tagging
  a causal claim that uses "leads to" as normative)?
- Is there a *better* option I have not listed (e.g. a small fine-tune, a constrained-decode enum
  gate, a second-pass cross-family judge, dropping the FORM axis entirely at S2 and deriving it at
  S4 from richer context)?
- Have I exhausted the option space, or is there a cheaper/safer alternative?

---

## 4. S2 data audit (raw findings — re-verify and extend)

8,410 records. See `knowledge pipeline/stage2_extract/t11/checkpoint.jsonl`.

### 4.1 Label distribution

| content_type | count | share |
|---|---|---|
| principle | 7,263 | 86.4% |
| process_template | 796 | 9.5% |
| process_instance | 204 | 2.4% |
| tool_instruction | 143 | 1.7% |
| growth_edge | **4** | **0.05%** |

| extraction_type | count | share |
|---|---|---|
| causal_mechanism | 3,771 | 44.8% |
| empirical_pattern | 1,630 | 19.4% |
| normative_heuristic | 1,562 | 18.6% |
| descriptive_model | 1,447 | 17.2% |

### 4.2 Label-correctness cross-tab (`extraction_type` × `content_type`)

| content_type | causal | empirical | normative | descriptive |
|---|---|---|---|---|
| principle | 3,539 | 1,504 | 1,068 | 1,152 |
| process_template | **194** | 59 | 491 | 52 |
| process_instance | 38 | 63 | 0 | 103 |
| tool_instruction | 0 | 0 | **3** | **140** |
| growth_edge | 0 | 4 | 0 | 0 |

**Red flags to assess:**
- `tool_instruction` → `descriptive_model` **140 / 143 (98%)** — but config says TI→normative. This
  is the single strongest signal of the golden/config conflict (F3/F5).
- `process_template` → `causal_mechanism` **194 / 796 (24%)** — a repeatable *method* should be
  `normative_heuristic`, not causal.
- `growth_edge` → only **4 records** — GE is the correct home for speculative/empirical-only
  insight; its near-extinction is itself a content_type drift signal.

### 4.3 Body-field completeness (missing / empty)

| content_type (n) | elaboration missing | other gaps |
|---|---|---|
| principle (7,263) | 0 | — |
| process_template (796) | **699 (88%)** | — |
| process_instance (204) | **157 (77%)** | `outcome_metric` 45 (22%) |
| tool_instruction (143) | **140 (98%)** | `parameters` 31 (22%) |
| growth_edge (4) | 1 | — |

**Question:** `elaboration` is a required shared core field per `content_types.yaml`, and the
convergent prompt enforces "never empty" — but the single-source prompt does **not** enforce it.
Is this a schema violation, a prompt gap, or a legitimate per-type difference? Should TI/PI/PT
*require* elaboration at S2, or is it correctly deferred to S4 (which has its own elaboration
step)?

### 4.4 Metadata / provenance (these are COMPLETE)

- Stamps (`schema_version`, `gen_model`, `pipeline_commit`, `created_at`): **0 missing**.
- Provenance (`source_books`, `evidence_passages`, `source_ids`): **0 missing**.
- Classification (`domains`, `discipline`, `depth`, `evidence`): **all 8,410 missing** — expected,
  because depth/domains/discipline are S4's job (D2138/D2139). Confirm this deferral is correct.

---

## 5. S4 / S5 acceleration question

Current: S4 = gpt-oss-20b CRIBS classification (merge + depth/domain/discipline + routing);
S5 = DeBERTa-v3-large NLI verification; S6 = SQLite (sqlite-vec) + Parquet. Prior canary: S4→S5→S6
≈ 87 min for 279 FBs; S4 is the known bottleneck (batch depth classification A/B failed parity at
75%).

**Ask the external LLM:** how can S4 and S5 be made faster **without quality loss, accuracy loss,
or classification-quality degradation**? Specifically evaluate:

1. **S4 (gpt-oss-20b)**: continuous batching vs per-call; prompt-cache reuse across the CRIBS
   calls; KV-cache quantization; `thinking_budget` tuning (already 256/128 — is there headroom?);
   classifying depth+domain+discipline in ONE call vs split calls; routing `principle`-only fast-path
   vs full CRIBS for all types; deferring non-essential enrichment to S4.5.
2. **S5 (DeBERTa)**: batch NLI inference; GPU/Metal offload vs CPU; early-exit on high-confidence;
   threshold tuning (currently 0.10); whether premise/hypothesis pairing can be pruned.
3. **S6**: incremental commit vs full rebuild; sqlite-vec index build cost.
4. **Cross-stage**: can S4/S5 be made incremental/resumable so a re-run only touches changed FBs
   (the current checkpoint is 8,410 FBs, ~30× the canary)?

**Constraint (non-negotiable):** the acceleration must not reduce label accuracy, NLI verification
strength, or provenance integrity. Cite *specific* levers with expected speedup and the
quality-preservation argument for each.

---

## 6. Market research (from `feed.opml` — evaluate fit, not just existence)

The feed already flags candidate accelerators. Assess each against **C1 ($0 marginal cost), C3
(sovereign/local-only), C4 (no vendor lock-in)** and the M1 Max hardware (no M5 TensorOps):

**Inference engines (S2/S4 speed):**
- **Rapid-MLX (vLLM-MLX)** — 2–4× vs Ollama, continuous batching, prompt cache, KV int4/int8.
  ⚠️ v0.11 pulls models from HF network → violates C1/C3. Is a cache-respecting release worth adopting?
- **MTPLX** — native MTP speculative decoding 1.6–2.24×. ⚠️ M5 TensorOps required; M1 Max "hardware
  acceleration: false". Value at temp=0.0?
- **CIDER** — W8A8/W4A8 INT8 TensorOps 1.2–1.9× SDPA. ⚠️ M5+ only.
- **mlx-serve** — no-Python, same MLX backend, no perf advantage.

**Vector search / clustering (S1.5 + FB retrieval):**
- **USearch** — 10× HNSW vs FAISS, NEON SIMD for Apple Silicon. Candidate for S1.5 replacement?
- **TurboVec** — 2–4-bit quantized, 4–8× faster, Metal SIMD. **Already installed (v0.8.0).**
- **LEANN** — 97% storage savings RAG (MLsys2026), FAISS internally.
- **zvec** (Alibaba) / **sqlite-vss** — embedded vector stores vs current sqlite-vec.
- **LightRAG** — graph-based RAG (entity-relation + graph traversal) for FB retrieval quality.

**Model fit:** `llmfit` (adopted) + `whichllm` for hardware-fit checks on any new judge model.

**Question:** which (if any) of these are *actually* worth adopting for the S4/S5 acceleration in
§5, given the hardware + sovereignty constraints? Distinguish "worth evaluating now" from "monitor
only."

---

## 7. Requested deliverables from the reviewing LLM

Return a structured verdict on:

1. **Root-cause correctness** — is F1 (prompt asymmetry) the primary cause? Is F3 (golden
   descriptive bias) real? Any error in F2/F4/F5/F6?
2. **Solution exhaustiveness** — is the §3 "ultimate solution" correct and complete? What option
   is missing or strictly better? Is fixing-the-generator alone sufficient, or is R2 required first?
3. **S2 audit** — confirm or correct the §4 findings. Are the `tool_instruction→descriptive_model`
   (98%) and `elaboration` gaps real defects or acceptable per-type behavior? Any additional
   mislabel / missing-body / metadata defect I missed?
4. **S4/S5 acceleration** — concrete, quality-preserving speedup levers (with expected speedup and
   the quality-preservation argument).
5. **Market research** — adopt / evaluate / monitor verdict for each §6 item.
6. **Blind spots** — any drift, bug, conflict, hidden failure, contamination, leak, or bleed that
   the above analysis has *not* already surfaced.

Be specific, cite the evidence, and flag anything in this brief that is itself wrong or overstated.
