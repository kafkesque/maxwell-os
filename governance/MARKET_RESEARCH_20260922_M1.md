# Market Research — M1 Silicon Reality Check + On-Device Engine Scan (2026-09-22)

**Scope:** (1) Does `mlx-dspark` work on M1 at all? (2) Is any on-device inference engine / model
designed for M1 silicon better than the current oMLX baseline? (3) Establish the standing rule that
**community benchmark results outrank vendor claims**.

**Hardware anchor:** MacBookPro18,2 · Apple **M1 Max** (24-core GPU) · 64 GB · 400 GB/s ·
macOS 26.x/27 · **Metal 3** (no NAX, no per-GPU neural accelerator, no M5 TensorOps).

> Do not restate a config value here — cite the path. Feed source of truth: `feed.opml`.
> Decisions: `config/decisions.yaml` (D-332), `DECISION-LOG.md`.

---

## 1. Does mlx-dspark work on M1? — YES it runs; NO it does not help.

**Verdict: it runs, but speculative decoding is a NET LOSS on M1 Max.**

Definitive community evidence — `ARahim3/mlx-dspark#38` (open, 2026-09-16), on the **exact same
hardware as Maxwell** (M1 Max 64 GB, 24-core GPU):

| mode / cap | decode tok/s | round cost vs 1 step | speedup |
|---|---|---|---|
| baseline (plain greedy) | 10.2 | 1.00× | 1.00× |
| DFlash 2 · cap 1 (auto-picked) | 9.5 | 1.84× | 0.93× |
| DFlash 2 · cap 7 | 7.7 | 3.89× | 0.75× |
| DFlash 2 · cap 7 · small-M **off** | 5.6 | 5.40× | **0.55×** |
| DSpark · cap 2 | 9.3 | 2.39× | **0.91×** (best) |

- **Not a calibration bug.** The auto-calibration correctly settled on `cap 1`; the manual sweep
  confirms the optimum is still < 1.0×. `mlx-dspark doctor` passes clean. mlx 0.32.2 supports M1.
- **Root cause (hypothesis, consistent with Maxwell's own D-3251/D2460 findings):** M1 Max baseline
  decode is **bandwidth-bound** (400 GB/s → 10.2 tok/s, *faster* than the M4 Pro's 8.4 baseline),
  while the multi-token verify + drafter forward is **compute-bound on the old GPU** (no NAX, no
  per-GPU neural accelerator). Round cost ≈ 2.4× a decode step; break-even acceptance is never met.
- **This matches the flags already in `feed.opml`:** MTPLX "M1 Max hardware acceleration confirmed:
  false"; CIDER "INT8 TensorOps only compile on M5+ (M1 gets SDPA only ~1.0-1.1×)".

**Consequence for Maxwell (important):** oMLX's Lightning MTP (D-293) is the *same class* of
speculative decode. The vendor claim "+34–58% decode on Qwen3/DeepSeek/GLM" is measured on M4/M5.
On M1 Max, D-293 must be a **before/after measurement, not a blind enable** — expect neutral-to-worse.

---

## 2. On-device topic scan — no M1 engine beats oMLX

Swept `github.com/topics/on-device-ai` and `on-device-llm`. The overwhelming majority of top repos are
**mobile/embedded** (Android, iOS, Qualcomm NPU, Raspberry Pi, wearables), not M1-Max desktop servers.
The M1-relevant candidates, and why none displaces oMLX:

| Repo | What it is | Verdict for Maxwell |
|---|---|---|
| `mit-han-lab/TinyChatEngine` (967⭐, C++) | AWQ/SmoothQuant C++ engine, explicit M1/M2 **Metal** support, MLSys 2024 Best Paper. Real M1-optimized. | **REFERENCE.** Research-tier: AWQ-only model zoo (LLaMA-3-8B, VILA-7B), no OpenAI API server, no continuous batching, no grammar/guided decode. Not a drop-in for a 5-model RAG pipeline. |
| `google-ai-edge/LiteRT-LM` (6,495⭐, C++) | Cross-platform (Android/iOS/Web/Desktop), GPU/NPU delegates; macOS Swift "early preview". | **WATCH.** Mobile-first; macOS support is early-preview, not an M1-Max desktop server. YNNPACK delegate is linux-arm64 only. |
| `cactus-compute/needle` (12,169⭐) + `cactus` (6,045⭐) | 121M-param foundation model (8–29 MB) specialized for **tool-calls / structured extraction / embedding**. | **WATCH (model, not engine).** Different tier entirely — trades general chat for tool-call+extraction accuracy. Interesting as a *specialized S2 probe / structured-extraction head*, not a Qwen3-Coder-30B replacement. |
| `Helldez/BigMoeOnEdge` (587⭐, C++) | MoE-on-edge inference. | **WATCH.** Unverified M1 numbers. |
| `PrismML Bonsai` (ternary 2-bit) | Ternary edge models. | **REJECT.** mlx-dspark's own table shows only 1.13× — edge ternary doesn't beat M1 bandwidth either. |

**Bottom line:** there is no inference engine in the on-device topics that beats oMLX on M1 Max.
The community data converges on one conclusion: **M1 Max is a bandwidth-bound regime** where the
M5-era optimizations (speculative decode/MTP, INT8 TensorOps, block-diffusion drafters) are a wash
or a loss. oMLX stays.

---

## 3. New standing rule — community benchmarks outrank vendor claims

**Rule (D-332):** for every speed/latency/quantization claim, weight **community benchmark results on
matching hardware above vendor claims on newer hardware**. Use both, but vendor numbers measured on
M4/M5 do **not** transfer to M1 Max. Canonical community sources (already in `feed.opml`):

- `maziyarpanahi/whichllm` (⭐6,019) — real community-tested tok/s rankings ("measures, doesn't estimate").
- `kennss/SiliconScope` (⭐802) — native Apple Silicon monitor (bandwidth/ANE/thermal) for before/after measurement.
- LM Studio community benchmarks + engine-repo issues (e.g. `mlx-dspark#38`) as primary per-hardware evidence.

**Consequence for the M1 Max optimization plan:** re-rank the levers. Bandwidth-side wins dominate:
1. **Quantization that shrinks memory traffic** (oQ4e/oQe A/B = D-294, KV-cache int8) — highest value.
2. **Cache correctness** (D-292: kill the D2460 SSD-thrash flags) — protects the bandwidth we have.
3. **MTP/speculative decode** (D-293) — re-scope to *measure-don't-assume*; likely neutral on M1 Max.

---

## 4. Recommendation (strategic, sequenced)

1. **KEEP oMLX.** Confirmed by community data; no on-device engine out-serves it on M1 Max.
2. **D-293 re-scope:** turn "enable MTP" into "A/B MTP on a frozen S2 batch, expect ≤1.0× on M1 Max;
   adopt only if measured faster" (community-benchmark-first rule, D-332).
3. **Prioritize D-294 (oQ4e/oQe quant A/B) and D-292 (cache fix)** — the bandwidth-side levers that
   actually move M1 Max throughput.
4. **WATCH** `needle`/`cactus` as a possible *specialized* tool-calling/extraction model for S2 probing
   (not a generator swap), and `LiteRT-LM` only if a desktop-Metal path matures.
5. **REFERENCE** TinyChatEngine's AWQ+Metal kernel work as design notes for any future custom quant.
