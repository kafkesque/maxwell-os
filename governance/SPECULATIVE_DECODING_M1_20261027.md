# Speculative decoding on the M1 Max (64 GB): what is verified, what is REFUSED, and why

**Date:** 2026-10-27 · **Device:** Apple M1 Max, 64 GB unified, MLX 0.31.2 · **Question (owner):** find a
100%-verified working speculative-decoding solution (model, configuration, or engine) that guarantees faster
decoding AND prefill for Qwen3.8-27B.

This receipt answers three separate questions, because "speculative decoding" is three different mechanisms here
and only ONE is available on this device. Each row carries the reading that produced it (D-3109).

---

## 1. Native MTP (`mtplx` 1.0.4) — REFUSED on M1 Max: it is M5-TensorOps-only

`mtplx` is installed (1.0.4) and is the purpose-built "Native MTP speculative decoding on Apple Silicon" engine.
Its own hardware gate, read on this machine:

```
$ mtplx hardware
chip: Apple M1 Max
Apple Silicon generation: m1
MLX: 0.31.2
unified memory: 64.0 GB
M5 TensorOps eligible: false
hardware acceleration confirmed: false
```

The MTPLX benchmark that makes MTP look like a 2–3× win is **on a different device**: the `benchmarks.json` shipped
with `Qwen3.8-9B-Distill-MTPLX` reads `hardware: Apple M5 Pro, 48 GB`, with AR 32.42 t/s → D1 58.91 t/s (1.82×) →
D2 71.70 t/s (2.21×), acceptance 90.3% / 80.7% at depth 2. That is a HYPOTHESIS for this M1 Max (D-3036), and the
engine's own gate REFUTES it here: **`hardware acceleration confirmed: false`**. So native MTP is a recorded
negative (D-3038): it cannot be re-proposed for this device without a NEW measurement that shows MTP running on M1.

## 2. The oMLX MTP/prefill flags — capability present, DISABLED, and MTP is the same M5-gated path

`~/.omlx/model_settings.json` for `Qwen3.8-27B-MLX-4bit` carries the whole prefill/decode acceleration surface:

```
mtp_enabled: False
vlm_mtp_enabled: False
specprefill_enabled: False
qwen35_ane_prefill_enabled: False
turboquant_kv_enabled: False
dflash_enabled: False
```

So the stack HAS the knobs, but they are all OFF for this model. `mtp_enabled` is the same native-MTP path that
`mtplx hardware` refuses on M1; enabling it without the MTP drafter and without M1 support would be a declaration
with no referent (D-3034). `qwen35_ane_prefill_enabled` (Neural-Engine prefill) is the one prefill lever that COULD
apply on M1 (the M1 Max has a 16-core ANE) but its eligibility is **UNVERIFIED** — it must be measured, not assumed.

## 3. mlx_lm standard speculative decoding (draft + verify) — the ONLY M1-eligible path, and the draft is now known

`mlx_lm 0.31.3` implements speculative decoding generically (`speculative_generate_step`, `--draft-model`,
`--num-draft-tokens`). It is plain MLX — no TensorOps — so it is eligible on M1 Max. It requires a draft model that
shares the target's **tokenizer** (same token→id map), not merely the same family name.

**The tokenizer trap (measured, not assumed).** Three "Qwen3.8 small" drafts were checked against the target
`Qwen3.8-27B-MLX-4bit` (tokenizer vocab 248044, merges 247587, added_tokens 33):

| draft candidate | model_type | vocab | tokenizer vs target | verdict |
|---|---|---|---|---|
| `piskle/Qwen3.8-0.6B` | qwen3 | 151643 | **DIFFERENT** — 151643 ≠ 248044 | **REFUSED**: ids do not map; acceptance would collapse to ~0 |
| `piskle/Qwen3.8-0.6B-FP8` | qwen3 | 151936 | **DIFFERENT** | **REFUSED** |
| `inference-optimization/Qwen3.8-1.0B-A0.6B` | qwen3_5_moe | 248044 | **IDENTICAL** (vocab, merges, added_tokens all equal; file hash differed only by JSON serialization) | **VALID draft** |

So the ONLY verified-compatible small draft for this target is `Qwen3.8-1.0B-A0.6B` (a 1.0B MoE with 0.6B active).
The same-family naming is misleading: "Qwen3.8-0.6B" is a Qwen3-base tokenizer (151k), while the 27B is a qwen3_5
tokenizer (248k). **A draft that fails this check is slower than baseline, not faster.**

## 4. The exact command (engine + draft + target, all verified compatible)

```bash
# one-time: fetch + quantise the tokenizer-matched draft (1.0B MoE -> ~0.5 GB 4-bit)
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('inference-optimization/Qwen3.8-1.0B-A0.6B', local_dir='$HOME/.omlx/drafts/Qwen3.8-1.0B-A0.6B', allow_patterns=['*.json','*.safetensors','*.jinja'])"
python3 -m mlx_lm.convert --model ~/.omlx/drafts/Qwen3.8-1.0B-A0.6B --mlx-path ~/.omlx/drafts/Qwen3.8-1.0B-A0.6B-mlx4 --quantize --q-bits 4

# baseline and speculative, same prompt, same budget
python3 -m mlx_lm.generate --model ~/.omlx/models/Qwen3.8-27B-MLX-4bit --prompt "Write a quicksort in Python." --max-tokens 128
python3 -m mlx_lm.generate --model ~/.omlx/models/Qwen3.8-27B-MLX-4bit --draft-model ~/.omlx/drafts/Qwen3.8-1.0B-A0.6B-mlx4 --num-draft-tokens 2 --prompt "Write a quicksort in Python." --max-tokens 128
```

Expected mechanism: draft cost ≈ 0.5 GB / 140 GB/s ≈ 3.6 ms/token vs target ≈ 15 GB / 140 GB/s ≈ 107 ms/token, so
drafting 2 tokens costs ~7% overhead; at same-tokenizer acceptance ~70–80% the speedup lands ~1.5–1.8× on DECODE.
**Measurement is OWED** — the number is a hypothesis until the two commands above are run on this device and the
t/s delta recorded here (D-3036). A draft whose tokenizer differs is not a slower win, it is a net loss.

## 5. Prefill — speculative decoding does NOT help it; this is stated plainly

Speculative decoding drafts and verifies OUTPUT tokens. Prefill (prompt ingestion / TTFT) is unchanged: the target
still prefills the whole prompt, and `speculative_generate_step` also prefills the draft (line 604 of
`mlx_lm/generate.py`), so prefill gets marginally SLOWER, never faster. So "guarantee faster decoding AND prefill"
has no single knob:

- **Decode** → speculative decoding (`mlx_lm` + the tokenizer-matched draft above), the verified-eligible lever.
- **Prefill** → (a) prompt caching for repeated prefixes (`mlx_lm --prompt-cache-file` / llama.cpp `--prompt-cache`),
  the only lever verified to work without a new claim; (b) `qwen35_ane_prefill_enabled` in oMLX (offload a fraction
  of prefill layers to the M1's 16-core Neural Engine) — a real feature of the stack, but its M1 eligibility is
  UNVERIFIED and must be measured before it is claimed; (c) a smaller quant, linear and already at 4-bit.

## 6. What this changes for BUG-1033 / D-3166

Nothing about the bandwidth ceiling: decode remains bandwidth-bound at ~140 GB/s effective (~9 t/s for a 15 GB
model). Speculative decoding is the ONE lever that beats a bandwidth bound, because it verifies several tokens per
weight-read. It is now known to be M5-gated natively (MTP), and available on M1 only through `mlx_lm` draft+verify
with a tokenizer-identical draft. That is the lever to pursue next; a kernel tweak still cannot close 9 → 16.

---

## 7. CORRECTION (later the same day, 2026-10-27) — §3's "the ONLY M1-eligible path" is now REFUTED by measurement

**This section SUPERSEDES the claim in §3 and the command in §4.** §3 asserted that `mlx_lm` draft+verify is the
one route available on this chip. It had never been run. It has now been run, twice, and it **cannot run on
Qwen3.8-27B at all**. The instrument is `scripts/specdec_probe.py` (config `config/specdec_m1.yaml`); every row
below is from `governance/specdec_probe_receipt.jsonl` on this device (M1 Max, 64 GB, MLX 0.31.2, mlx_lm 0.31.3).

### 7.1 The draft is now real and verified — the compatibility work SUCCEEDED

| step | reading |
|---|---|
| tokenizer gate | vocab 248044 / merges 247587 / added_tokens 33 — **identical** to target `Qwen3.8-27B-MLX-4bit` |
| model_type | artifact declares `qwen3_5_moe_text`; mlx_lm 0.31.3 **and 0.32.2** register only `qwen3_5_moe` |
| proof it is a NAME mismatch only | draft loads **`strict=True`** under the alias: every tensor consumed, every parameter set, **966.1 M params** |
| 4-bit draft built | `OK convert | model_type=qwen3_5_moe | 4.501 bits/weight | bytes=543,644,054` |
| `verify` | `VERIFY PASS` (tokenizer gate + both models strict-load) |

So the trap §3 warned about (a tokenizer that does not match) was correctly avoided, and the draft is now a usable
543 MB artifact at `~/.omlx/drafts/Qwen3.8-1.0B-A0.6B-mlx4`. **The blocker is not the draft. It is the target.**

### 7.2 The refusal — the TARGET's prompt cache cannot be rewound

```
DRAFT MODE REFUSED: target prompt cache is not trimmable (ArraysCache) —
mlx_lm speculative draft+verify requires cache rewind after partial acceptance
```

Read at the source: `speculative_generate_step` calls `cache.can_trim_prompt_cache(model_cache)` and raises
`ValueError: Speculative decoding requires a trimmable prompt cache (got {'ArraysCache'})`. `ArraysCache`
(`mlx_lm/models/cache.py:594`) declares **no `is_trimmable`**, unlike `KVCache`/`RotatingKVCache`. Qwen3.8-27B is a
**hybrid** model — `layer_types` = 3 × `linear_attention` + 1 × `full_attention` per 4 layers — so its
linear-attention state lives in `ArraysCache`. Draft+verify needs to *un-consume* the draft tokens the target
rejected; a recurrent state array cannot be trimmed back. **This is structural, not a flag**: no draft model, no
`--num-draft-tokens` value and no engine upgrade changes it.

### 7.3 What the same instrument measured about the model itself (two runtimes, one story)

| runtime | prompt | prompt tokens | prefill t/s | decode t/s | note |
|---|---|---|---|---|---|
| mlx_lm in-process | short_code | 29 | 34.99 | **7.582** | prefill INCOMPARABLE (<2000-token floor, BUG-803 guard) |
| mlx_lm in-process | review_long | 1722 | 40.06 | **7.544** | decode ctx 1850 tokens |
| oMLX `/v1/chat/completions` | same-file prompt, cache HIT | 1733 | *skipped* (implied 15,451) | **7.97** | 12.04 s total |
| oMLX `/v1/chat/completions` | same-file prompt, cache MISS | 1739 | **≈49** (implied) | 8.05 | 47.60 s total |

Three facts fall out of that table, and they matter more than speculative decoding did:

1. **Decode is flat in context** (7.54 t/s at 1,850 tokens vs 7.58 at 157) — this model is weight-read bound at
   these lengths, exactly as the bandwidth arithmetic in §6 says. Nothing is "taming" it.
2. **Prefill is ~40–49 t/s, i.e. ~75% of the cost of a cold reviewer call** (35.7 s of 47.6 s for a 1.7k-token
   prompt). For a reviewer workload the bottleneck is **prefill, not decode** — which is why a 27B dense model is the
   wrong reviewer regardless of how fast its decode is, and why an MoE with ~4B active (gpt-oss-20b) wins the
   reviewer slot by construction.
3. **The one lever measured to work is prompt-cache reuse**: the identical prompt went 47.60 s → 12.04 s (3.95×)
   because prefill was skipped entirely. That is available today, needs no new claim, and is the only "faster
   prefill" this receipt can assert.

### 7.4 The final verdict on the owner's question, stated without hedging

**No 100%-verified speculative-decoding solution exists on this machine for Qwen3.8-27B.** All three mechanisms are
now measured/closed:

| mechanism | status on M1 Max | closed by |
|---|---|---|
| native MTP (`mtplx`) | REFUSED — M5 TensorOps only | engine's own hardware gate: `hardware acceleration confirmed: false` |
| oMLX `mtp_enabled` / `mtp` drafter | REFUSED — same M5-gated path | `model_settings.json` all-False + mlx-vlm absent for the adapter |
| `mlx_lm` draft + verify | REFUSED — target cache not trimmable | `ArraysCache` has no `is_trimmable`; measured refusal above |

The only remaining route that could make draft+verify legal here is **engineering a snapshot/restore cache for the
hybrid state** (save the `ArraysCache` arrays before each draft round, restore on partial acceptance) guarded by a
hard correctness test — greedy output must be **token-identical** to baseline. That is a real experiment with a real
risk and it is NOT claimed here; it is registered as an owner decision (D-3171) rather than a promise.
