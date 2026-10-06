# MARKET RESEARCH — 2026-10-02: Inference engines (M1) + S4 classifier candidates

> Research-only (fact-finding via HF/GitHub API + local probe). No pipeline wiring done. Supersedes nothing.
> Machine: Apple M1 Max (Apple7 GPU), 32-core GPU, 64 GB, Metal 4.

## 0. "llm fit" interpretation
No `llm` CLI is installed on this machine (`which llm` → not found; no `fit` subcommand). Interpreted as
**LLM-as-judge head-to-head model-FIT evaluation** on Maxwell's human gold (149 depth + 204 discipline), the only
measurement that can answer "faster AND more accurate" (see §3 recommendation). This is recorded as D-2767.

## 1. Inference engines for Apple Silicon (M1 Max / Apple7)
| Engine | M1 support | Status here | Notes |
|---|---|---|---|
| **MLX / MLX-LM** (Apple) | ✅ native | **installed** (python `mlx`), used via OMLX | current Generator/Classifier/Probe server |
| **Ollama** | ✅ (llama.cpp backend) | **installed** | serves bge-m3 + qwen3-embedding + small LLMs |
| **llama.cpp** (llama-server/cli) | ✅ Metal | not in PATH (installable) | mature GGUF runner |
| **Splash** (incoai) | ✅ M3+ only | n/a (needs M3) | 2× decode / 4× parallel (see prior turn) |
| **Splash-M1 backport** (paperniuk 1.1.0-m1) | ✅ Apple7/8 | installable | EXACTLY our chip; #95 validated on M1 Max 32/64; #131 native kernels; still open/young |
| **llamafile** (Mozilla) | ✅ Metal | not installed | single-file binary |
| **MLC-LLM** | ⚠️ stale | not installed | TVM; less active |
| **vLLM / SGLang / TensorRT-LLM** | ❌ | — | CUDA/ROCm only, NO Apple support |

**Verdict:** the relevant trio is **MLX (current) + Ollama (current) + Splash-M1 (eval pending)**. No engine is
missing that blocks the pipeline; Splash is the only one with a credible 2×+ speed claim worth an A/B.

## 2. Component-by-component serving options
| Component | Current | Alternatives | Recommendation |
|---|---|---|---|
| Generator Qwen3-Coder-30B-A3B (MLX-4bit) | OMLX/MLX | GGUF via Splash/llama.cpp | keep MLX; Splash A/B optional (DELEGATE-002 long-context) |
| Classifier gpt-oss-20b (MXFP4-Q8) | OMLX/MLX | GGUF via Splash | MLX MXFP4-Q8 already near-optimal; Splash A/B optional |
| Embeddings bge-m3 | Ollama | sentence_transformers (**installed**, in-process); qwen3-embedding (Ollama has it, newer) | keep Ollama bge-m3; qwen3-embedding is a drop-in candidate to eval |
| NLI DeBERTa-v3-large | transformers (MPS) | **ONNX Runtime (installed)**; CoreML EP not available (coremltools absent) | ONNX Runtime is a low-risk speedup worth eval for the 435M verifier |

## 3. S4 classifier candidates (faster AND more accurate than gpt-oss-20b)
**Constraint R5:** the classifier must stay a DISTINCT family from the Generator (Qwen3) and Probe (Phi) and NLI
(DeBERTa) to preserve measurement independence. Therefore **Qwen3-\* is disfavored for S4** (same family as the
Qwen3-Coder generator).

| Candidate | Family | Active params | Gated | Speed vs gpt-oss | Accuracy outlook |
|---|---|---|---|---|---|
| gpt-oss-20b (baseline) | GPT-OSS | 3.6B (MoE) | no | — | strong, chosen but never head-to-head-verified |
| **Mistral-Small-3.1-24B-Instruct** | Mistral | ~4B (MoE) | no | ≈ same | **top candidate** — newer, strong instr-follow |
| Gemma-3-12b-it | Gemma | 12B (dense) | yes | slower | strong, but dense→likely slower |
| Gemma-3-27b-it | Gemma | 27B (dense) | yes | much slower | most accurate of the lot |
| Llama-3.1-8B-Instruct | Llama | 8B (dense) | yes | slower | older |
| Qwen3-8B / 14B / 30B-A3B | Qwen3 | 8/14/3B-active | no | varies | **R5-excluded** (generator family) |

**Honest finding:** there is **no free lunch**. gpt-oss-20b (3.6B-active MoE) is already a strong speed/accuracy
Pareto point. No paper benchmark can *guarantee* "faster AND more accurate". The only way to know is a head-to-head
fit eval (§4). The single most promising candidate on paper is **Mistral-Small-3.1-24B** (≈same speed, newer,
non-gated).

## 4. Recommendation (D-2767)
1. **No S4 classifier swap** without a head-to-head FIT eval on the human gold (149 depth + 204 discipline), measuring
   **Cohen's kappa** (never bare accuracy, D-2611) + **tok/s**, temp=0.0 (R7).
2. **Swap gate:** a candidate must be BOTH faster AND kappa ≥ 0.800 AND ≥ gpt-oss-20b's measured kappa.
3. **Shortlist:** Mistral-Small-3.1-24B (primary), Gemma-3-12b-it (secondary). Qwen3-* excluded by R5.
4. **Inference A/B (separate from classifier swap):** Splash-M1 backport vs OMLX on the actual S4 batch workload.
5. **Low-risk quick wins worth eval first:** ONNX Runtime for DeBERTa-v3 NLI; qwen3-embedding vs bge-m3.

## 5. CORRECTION — D-2768 (2026-10-02): Splash is model-scoped, NOT a general GGUF runner
The Splash applicability in §1/§2/§4 was overstated. Splash is "built around the model" with a hardcoded
`families.FAMILIES` registry; each supported architecture pairs a TRAINED DFlash2 draft. Supported architectures are
EXACTLY: **Qwen3.8-27B, Qwen3.6-35B-A3B, Prism Ternary Bonsai 2**. Model identity = architecture signature
(repository names / model-card `base_model` play no part); an MLX target must declare affine 4-bit group-64 quantization.

- **Qwen3-Coder-30B-A3B (generator): NOT supported** — no matching draft; coder weights differ from the Qwen3.6-35B-A3B family.
- **gpt-oss-20b (classifier): NOT supported** — different architecture, no catalog entry.

**Consequence:** the Splash-vs-OMLX A/B (D-2767 step 5) is **MOOT** for the current model stack. Splash applicability to
Maxwell = **NONE today**. It only becomes relevant if Maxwell ADOPTS Qwen3.8-27B / Qwen3.6-35B-A3B as a role — which R5
disfavors for S4 (generator is Qwen3 lineage) and which would regress the code-tuned generator.

## 6. ADDENDUM — D-2771 (2026-10-02): Prism Ternary Bonsai 2 — NOT worth testing for S4 or S2
Owner follow-up asked whether the Splash-supported **Prism Ternary Bonsai 2** is worth an A/B against gpt-oss-20b
for S4, or against Qwen3-Coder-30B for S2. Ruling: **NO for both** (see D-2771).

- **R5 is NOT the blocker.** Prism is a distinct family from Qwen3-Coder (S2 generator), Phi-4 (probe) and DeBERTa
  (NLI), so generator≠verifier independence is preserved. The iron rule permits either test.
- **Quality rationale fails.** Bonsai 2 is a small ternary *speed-optimized* model. The S4 classifier-of-record already
  only reaches kappa ~0.45 on the 49-class discipline task (BUG-622); a much smaller ternary model is near-certain to
  score lower and would fail the D-2767 swap gate (kappa ≥ 0.800 AND ≥ gpt-oss). For S2, convergent extraction needs
  strong reasoning — swapping Qwen3-Coder-30B for a small ternary model would degrade extraction with no parity evidence.
- **Splash cannot even serve the targets.** DFlash2 drafts are per-architecture (D-2768); none exists for gpt-oss or
  Qwen3-Coder, so Splash offers no acceleration for the current roster.
- **Verdict:** marginal value ≈ 0. The real S4 lever is BUG-622 (discipline non-conformance) + BUG-621 (fit eval), not a
  new speculative-decode model.
