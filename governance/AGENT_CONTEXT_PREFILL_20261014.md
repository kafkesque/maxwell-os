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
