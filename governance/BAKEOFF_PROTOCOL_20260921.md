# BAKE-OFF PROTOCOL (pre-registered) - typed-decision heads vs incumbent
> Status: **PROPOSED (D-300)** - pre-registration exists so the result cannot be fitted after the fact.
> Applies to: S5 / decision layer. Harness: `scripts/bakeoff_typed_decision.py` (measurement),
> `scripts/bakeoff_report.py` (report + validity guards). Artifact: `governance/bakeoff_typed_decision_*.json`.

## Gate 0 - paper audit BEFORE any install (per candidate, 30-60 min)
1. Licence (unlicensed => do not vendor: `daseinlabs/open-jev` is REJECT on licence alone).
2. Weights: downloadable, pinnable revision, hash recorded (no floating `main` - C2).
3. Native output schema: size + granularity; can it be *projected* onto our 61-slot menu or is it scalar-only?
4. Tokenizer/coverage: our corpus is multilingual with British/American spelling drift.
5. Runtime: MLX or GGUF available locally (C1/C3: must run on this machine at $0 marginal cost).
6. Training-data provenance + licence of that data (contamination risk against our anchors).

## Candidate matrix (Gate-0 outcome decides entry)
| candidate | role it may play | verdict now |
|---|---|---|
| `mizorewww/laya-mlx` (ModernBERT + decision head, MLX) | labeler, projected onto our menu | **champion** - architecture-matched to incumbent, MLX-native |
| `Zefan-Cai/Open-Jev` (LoRA + single scalar head) | **score only** - abstention/rerank on the incumbent's output | second, complementary; never a label source |
| `bnsd55/jevmlx` (restricted-softmax, JSON) | labeler if its schema is menu-shaped | third; JSON-validity is not an accuracy lever |
| `daseinlabs/open-jev` | none | **REJECT** (unlicensed) |

## Arm matrix v2 (role-matched - v1 was a strawman)
v1 compared arms in a role the incumbent does not occupy (DeBERTa as a 61-way zero-shot ranker). Result:
**the DeBERTa arm tied the constant baseline exactly (error 0.931, 108/116 errors, error-set Jaccard 0.862)**
while Qwen3-Coder abstained 116/116 (parse masking). v2 must include, per role:
- **Labeler role:** S4 classifier / Phi-4-mini probe / candidate typed head - closed-menu ranking, constant baseline.
- **Verifier role (the incumbent's real job):** pairwise NLI of a *stored* label vs its definition -> contra rate.
- **Calibration role:** any scalar head as an abstention score on a produced label.
Primary metric = **error rate** (D-275a: never accuracy). Secondary = abstain rate, macro-kappa over active
classes, per-stratum (contra/clean), **error-set Jaccard vs baseline** (complementarity => arbitration layer
beats a swap), seconds/row and peak RAM (55 GB guard / 48 GB wall).

## Deploy rule (pre-registered, D-300)
Deploy only if the frozen-ruler error rate improves by **>= 5.0 absolute pp** at equal-or-lower abstention,
deterministic decode, same menu, same rows, same abstention definition. Otherwise **REJECT and document**.
An arm that abstains on >50% of rows is **INVALID**, not a win (guarded in code).

## Validity guards (in `scripts/bakeoff_report.py`, enforced)
- Locally recomputes every metric from per-row predictions and prints it beside the harness's own number.
- Flags an arm as DEGENERATE when its error set is identical to the baseline's.
- Refuses to emit a verdict when decided rows < 50%.

## Label-semantics freeze (C4)
A head may only be **projected** onto our menu, or used as a **score**. Replacing the schema invalidates the
D-285/D-289 boundary repairs and the kappa reference frame, and must be a separate, later decision.

---

## Gate-0 RESULT - laya-mlx (2026-09-21)

| check | result |
|---|---|
| licence | **Apache-2.0** (repo); MIT for jevmlx / Open-Jev; daseinlabs/open-jev unlicensed => REJECT |
| distribution | `pip install laya-mlx`; MLX-native, no PyTorch / no Transformers runtime (C1/C3 clean) |
| weights | HF `aac6fef/laya-mlx` (421M) and `aac6fef/laya-multilingual-mlx` (322M) - pin the revision; check the HF checkpoint licence separately |
| schema | **caller-supplied criteria**: predict(text, {field: {type: choice, criteria: [...]}}) => we pass OUR 61-label menu; no projection layer, no label-semantics conflict (C4 risk largely dissolves) |
| output | choice only, 0 output tokens, deterministic |
| footprint | peak ~944 MiB (421M) / ~688 MiB (322M) - trivial against the 55 GB guard |
| env | Apple Silicon, Python 3.11+, macOS 14+, MLX 0.32.2 - verify against the local interpreter before install |

**Residual risks before the A/B:** (1) a 61-way criteria list is far larger than the documented few-way
examples - degradation with a big menu is untested; (2) the multilingual checkpoint must be used (multilingual
corpus); (3) HF revision + checkpoint licence must be recorded (R14 provenance).

**Remaining Gate-0 for jevmlx:** read ARCHITECTURE.md / PROMPT_PROTOCOL.md to confirm whether its schema is
menu-shaped (labeler) or scalar (score-only).

## Gate-0 completion (2026-09-21, exec D-305) - paper audit CLOSED, install NOT performed

* **laya-mlx** - licence Apache-2.0; `pip install laya-mlx`; MLX-native (no PyTorch/Transformers); weights
  `aac6fef/laya-mlx` (421M) + `aac6fef/laya-multilingual-mlx` (322M); schema is **caller-supplied `criteria`**, so
  our 61-label menu is passed directly (no projection layer -> the C4 label-semantics risk largely dissolves);
  0 output tokens; ~690-945 MiB peak. **Residual:** 61-way criteria untested at scale; multilingual checkpoint
  required for our corpus; HF revision + checkpoint licence must be pinned in config (R14) before first use.
* **jevmlx** - schema check still OPEN (no reliable public schema statement found); cannot be armed until it is.
* **Install ask (owner decision, C2/C3 - sovereignty is the owner's call):** installing laya-mlx means a new local
  runtime (`pip install laya-mlx`, MLX) and pinned HF weights. Nothing about it is required for the current
  production path, nothing is adopted, and the frozen-ruler bar (D-300: >= 5.0 pp better at equal-or-lower
  abstention) still decides. Recommended: approve the install as **benchmark-only**, in an isolated venv
  (`python3 -m venv .venv_laya`), with the revision pinned in config before any measurement.
* Until the owner approves, `arm_typed_head` stays a stub and the bake-off verdict is unchanged:
  incumbent `pairwise` error 0.474, `qwen3coder` 0.526 (REJECT), R3 held-out test pre-registered
  (governance/R3_HELDOUT_PREREG_20260921.md).
