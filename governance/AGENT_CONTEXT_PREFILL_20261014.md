# The agent harness's context window, prefill and prefix cache — MEASURED 2026-10-14

**Authority:** D-3000 (PROPOSED) · **Contract:** `config/agent_context.yaml` · **Reading:**
`python3 scripts/agent_context_probe.py` (read-only, 12 known-answer controls, rc 2 on drift) ·
**Task:** T-132 · **Bugs found by this sweep:** BUG-788 (FIXED), BUG-789 (OPEN), BUG-790 (OPEN).

---

## 1. The one-line answer

Local agent sessions do not run out fast because of the chip or because the model is small. They run out fast
because **four numbers nobody declared together are inherited from cloud defaults**: this machine's agent loop
compacts at **26,214 tokens** (`min(0.8 x 32,768, 225,000)`) while it already **serves 131,072 and 262,144** to
two other installed models — and every compaction **rewrites the prompt**, so the next turn pays a full COLD
re-prefill. Prefill, not decode, is the cost of an agent loop, and the harness was configured to maximise it.

## 2. The four layers, measured

| Layer | Home | Measured 2026-10-14 |
|---|---|---|
| 1 served window | oMLX `/v1/models` + `~/.omlx/model_settings.json` | Phi-4-mini / gemma-4-E4B / Qwen3-Coder-30B **32768**; gpt-oss-20b-Q8 **131072**; Qwen3.8-27B **262144** |
| 2 harness declaration | goose `custom_providers/maxwell_omlx.json` | equal for those five — **but 3 declared models are not served and 3 served models are not declared** (six drifts, reported UNVERIFIABLE, never green) |
| 3 compaction trigger | `GOOSE_AUTO_COMPACT_THRESHOLD` x window, capped by `GOOSE_AUTO_COMPACT_TOKEN_LIMIT` | **both variables UNSET** in the process env and in `~/.config/goose/config.yaml` → defaults `0.8` / `225000` → local trigger **26,214**; the 225000 cap is a *cloud price-tier* artifact |
| 4 cache evidence | `~/.local/share/goose/sessions/sessions.db#usage_ledger` | 28,646 calls, 2.857 B input tokens, **2.742 B cache reads (96%)**; per model: deepseek-v4-pro 96.4%, deepseek-flash 96.1%, **gemma-4-E4B 37.4% (289 calls)**; **Qwen3-Coder-30B 0.0% over 10 single-shot calls → INCONCLUSIVE, not a measured zero**; **676 compactions** |

## 3. Why a local agent loop feels slow (the mechanism, not the vibe)

An agent turn is almost all PREFILL: the model must re-read the whole conversation before it writes the first
token. Decode (tokens/second, the number every dashboard shows) is the small half. So the cost of a session is
governed by **how much of the prompt is already in the KV cache**:

* a **stable prefix** turns the re-read into a cache read — the walkthrough's own same-session A/B measured
  **6.1 s cached vs 268 s uncached (44x)** on one model, one machine;
* a **compaction** invalidates the prefix entirely: the summary is new text, so the next turn re-prefills it cold;
* a **per-turn injection at the head** (goose's `tom` / `GOOSE_MOIM_MESSAGE_*`) makes *every* turn a miss.
  MEASURED here: neither variable is set, so this hazard is currently **ABSENT** — declared as a hazard so that
  whoever enables it puts it at the TAIL.

The repo already holds the evidence that this harness can do prefix reuse: **96% of the cloud models' input
tokens are cache reads**. Nothing about the local path is broken — **nothing measured it**.

## 4. The fix ladder (ordered; each step's home is declared, no magic numbers anywhere)

| # | Step | Where | Status |
|---|---|---|---|
| F1 | **Route agent LOOPS by window class** — `agent_loop >= 131072`, `agent_probe >= 32768` | `config/agent_context.yaml#classes` + the goose provider/model selection | **needs YOUR word** (T-132 gate) — gpt-oss-20b (131072) and Qwen3.8-27B (262144) are already served and already loadable |
| F2 | **Declare the trigger instead of inheriting it** — set `GOOSE_CONTEXT_LIMIT` per served window, and the compaction pair so ONE compaction per session is the budget (`max_compactions_per_session: 1`, `min_headroom_tokens: 2048`) | environment / harness config, values in `config/agent_context.yaml#trigger` | needs your word (behaviour-changing) |
| F3 | **Prove the cache** — the two-call A/B on one cold process; until it runs, no cache ratio may be published for the local agent loop (`cache_accounting.proof.status: not_yet_run_on_this_machine`) | `scripts/agent_context_probe.py --json` + one manual A/B | pipeline |
| F4 | **Keep the prefix stable** — nothing dynamic at the head; a per-turn block belongs at the tail; compaction is treated as a cache bomb in the trigger budget | `config/agent_context.yaml#prefix_stability` (3 declared hazards) | declaration landed |
| F5 | **Tool-output discipline** — `GOOSE_TOOL_CALL_CUTOFF` (harness) + `max_tool_result_tokens` (server, 4096 measured) — tool output is where agent context actually goes | both sides of the wire | pipeline |
| F6 | **Drift correction** — reconcile the six declared/served mismatches: either declare the three served models (they are free capacity) or stop declaring the three that are not served | goose provider vs oMLX `/v1/models` | pipeline |

**Prefill-specific levers that are ALREADY correctly declared OFF on this hardware** (do not "optimise" them on
faith): `qwen35_ane_prefill_enabled: false` (ANE prefill is an M5-class path; M1 is a wash),
`specprefill_enabled` is a **measure-gated** lever (D-332: only adopted on an A/B WIN on THIS M1 Max — D-293
already measured MTP at 0.98x neutral), `mtp_enabled: false`, `dflash_enabled: false`. KV-cache quantisation
(`turboquant_kv_enabled`) is false on the agent-loop candidates and is the top *bandwidth* lever, but it is
measure-gated too.

## 5. What is NOT proven (and must not be asserted)

1. **No local agent-loop cache ratio exists.** The harness has one for the cloud models (96%) and one for the
   local *reviewer* (37.4% over 289 calls) — which proves the local server REPORTS cached tokens, so the field is
   trustworthy — but the loop itself has never run on a local model with the ledger watched.
2. **`cache_read = 0` is UNKNOWN, never zero** (D-2957). Qwen3-Coder's 10 calls are below the declared minimum
   (20) and are reported INCONCLUSIVE. A fabricated 0 here is BUG-767's defect class.
3. **The window that *can* be served is not the window that was measured**: raising `max_context_window` on
   oMLX costs KV memory, and the agent-loop candidates are at 32768 today. Routing to a model that ALREADY
   serves 131072+ (F1) needs no memory experiment at all — which is why F1 is first.

## 6. The reading (run this, read four lines)

```bash
python3 scripts/agent_context_probe.py            # the four layers + six drifts + the trigger per model
python3 scripts/agent_context_probe.py --selftest # 12 known answers, 2 of which read the file's own bytes (C12)
```

rc 0 = the four layers agree; rc 2 = a declared fault (a drift, or a window nothing declares). The live reading
is wired into `just health` as a **tri_state** line — loud, never fatal (BUG-457) — because the remedy for a
drift is a declaration, not a broken build. The controls are `fatal`.

---

## 8. AMENDMENT (measured 2026-10-14, the same day) — the cache was RUN, the window was RE-TESTED, and LAYER 5 was added

**The two claims in sections 1-6 that the amendment replaces, stated plainly so nothing above is read as current:**

1. **"Every compaction rewrites the prompt, so the next turn pays a full cold re-prefill" is TRUE but no longer the
   point.** The point is that there is **no prefix cache at all**: twelve calls with byte-identical prefixes (and the
   probe's own `--prefill-ab`) all reported `cached_tokens = 0`, at a speedup of **1.01x / 1.04x** against a declared
   **5x** bar. Every turn pre-pays its whole prompt, so a compaction is not a special case - it is the ordinary case
   with a bigger bill (BUG-792). The declared state is `disproven`, and the single non-zero reading (a 4096-token
   block boundary after a model load) names the mechanism: a 4096-token BLOCK cache, switched OFF by the D2460
   thrash guard, which is a fail-closed rail rather than a setting.
2. **Layer 3's ranking sentence in section 5 is WITHDRAWN.** The sweep said a 131,072-token window is reachable and
   therefore better. It is reachable - **50,082 prompt tokens were accepted whole by the 20B** - and it is
   **unaffordable**: at the measured throughputs a 131,072-token turn costs ~10 minutes on the 20B and ~56 minutes on
   the 27B. The earlier "truncation at 32,026 tokens" is **RETRACTED**: the prompt WAS 32,026 tokens, and the "sent"
   figure came from a chars-per-token ESTIMATE (4.0) where the measured rate is 4.5 (BUG-794).

**LAYER 5 — THE PREFILL BILL** (the contract's new, fifth layer, and the column every routing table was missing):

| model | prefill tok/s | decode tok/s | 26,214-token turn | 32,768-token turn | verdict at a 60 s budget |
|---|---|---|---|---|---|
| gemma-4-E4B-it-MLX-4bit | 455 | 27 | **57.6 s** | 72.0 s | **agent_loop** (the only one) |
| Phi-4-mini-instruct-8bit | 394 | 40 | 66.5 s | 83.2 s | probe only — misses by 6 s |
| gpt-oss-20b-MXFP4-Q8 | 210 | 33 | 124.8 s | 156.0 s | probe only |
| Qwen3.8-27B-MLX-4bit | 39 | 1.7 | 672.2 s | 840.2 s | not a loop at any budget |
| Qwen3-Coder-30B / others | unmeasured | — | — | — | **refused a route (fail-closed)** |

**THE AMENDED F-LADDER (replaces the F1-F6 ordering in section 4, which was built on the window-first premise):**

- **F1 — DECLARE THE TRIGGER FROM THE BILL, not from the window** (owner's word; T-132). While the cache is
  disproven, `threshold <= per_turn_budget_s x measured_prefill_tps / window`. The 0.8 default is right for the
  4B **by coincidence** and wrong for every other model — on the 20B's window it resolves to **104,857 tokens, 8.3
  minutes of prefill per turn**.
- **F2 — ROUTE THE LOOP TO THE MODEL THAT CAN PAY THE BILL** (the 4B class), and keep the large-window models for
  `agent_probe` work where a 2-13 minute single answer is acceptable and a loop is not.
- **F3 — AMORTISE THE PIPELINE BY PACKING, NOT BY PROMPT LAYOUT.** With no cache, the lever is requests per unit of
  work. The precondition is verified and now railed: **10 byte-stable system prefixes** (`--prefix-audit`, AST-based,
  because a grep counts role strings and budget constants as prompts).
- **F4 — KEEP THE PREFIX STABLE ANYWAY** (a necessary condition, measured insufficient): no per-turn injection at
  the head, no timestamps or ids in the system block, same model for a run of calls.
- **F5 — PREFER A DECLARED HANDOFF OVER AN IN-PLACE COMPACTION.** A compaction rewrites the prefix (a full cold
  re-prefill of the summary) *and* is lossy; a handoff read at the head of a fresh session is a shorter, byte-stable
  prefix — cheaper and auditable (C3). The harness's compaction stays as the fallback.
- **F6 — RE-TEST THE BLOCK CACHE ONE VARIABLE AT A TIME** behind a decode-rate oracle (D2460's regression has a known
  shape: ~50 -> ~4-7 tok/s). Not a flag to flip; an experiment to declare. Owner-owed.
- **F7 — DRIFT CORRECTION** (unchanged): reconcile the declared/served model mismatches — three served models nobody
  declares, three declared models not served.

**The reading, amended:**

```bash
python3 scripts/agent_context_probe.py                 # 5 layers + parity + the prefill bill per model, rc 2 on drift
python3 scripts/agent_context_probe.py --selftest      # 17 known answers, 2 of which read the file's own bytes (C12)
python3 scripts/agent_context_probe.py --prefix-audit  # the pipeline's amortisation precondition (offline)
python3 scripts/agent_context_probe.py --prefill-ab     # SENDS 3 calls: the only certification of REUSE (off the ladder)
```
