# HANDOFF — 2026-10-18 (23:36 +02:00) — WINDOW-RISE · SPLASH A/B · CLOUD CEILING · REGISTRY SYNC

> Continuity handoff. A NEW SESSION IS REQUIRED to make the window-rise live:
> harness fact #1 — config/harness knobs are read at session BIRTH; this session can never show them.
> The `strategy: declared_handoff_first` knob is exactly this document's job.

## STATE AT HANDOFF
- Repo: `/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0`
- This session made ZERO protected-file mutations (all four items were owner-gated — deliberate).
- Context was `/compact`-ed once already; this file is the durable record. Open a NEW session after landing.

## FOUR DECISIONS — status + recommendation
1. **WINDOW-RISE (post-BUG-885)** — RECOMMEND **A**: flip `cache_conditional.measured_state`
   `cache_disproven → cache_proven`; `GOOSE_AUTO_COMPACT_THRESHOLD 0.8 → 0.94` (= (32768−2048)/32768).
   Do NOT raise the window; keep `min_headroom_tokens: 2048`. **OWNER WORD: PENDING.**
2. **SPLASH A/B** — **OWNER = APPROVED TO OPEN.** Gate = T-187 two-step/two-tool fixture, Splash-ON vs OFF
   on the already-served `Qwen3.8-27B-MLX-4bit` (today 8.2 tok/s decode / 39 prefill). No wiring, no
   D-2768/D-2771 edit before the receipt. Supersession (Splash M1 overturns D-2768's M3 gate) is RECORDED as
   superseded; ADOPTION is gated separately.
3. **CLOUD CEILING (BUG-917, OPEN HIGH)** — RECOMMEND **SPLIT-counters** (durable) + **RAISE-with-reason**
   (interim, D-3023). Reject KEEP-RED (a permanently-red register is invisible = slop). **OWNER WORD: PENDING.**
4. **REGISTRY SYNC** — RECOMMEND **SYNC**. **OWNER WORD: PENDING.**

## CORRECTED DRIFT FINDING (measured 2026-10-18 — supersedes the earlier "mint backlog" framing)
- `config/decisions.yaml` is the RECORDS-ONLY registry (source of truth) and IS CURRENT to **D-3100**.
- `DECISION-LOG.md` (append-only narrative) LAGS: highest minted = **D-3051**.
- **10 entries missing** from DECISION-LOG.md: D-3058, D-3071, D-3072, D-3073, D-3086, D-3092, D-3095,
  D-3097, D-3099, D-3100.
- These are **NOT unminted** — they exist as records in `config/decisions.yaml`. The fix is a SYNC of
  DECISION-LOG.md FROM decisions.yaml, NOT a fresh mint (fabrication would violate D-3034).
- Counter discrepancy to resolve during SYNC: loader says `decisions.yaml = 475`, HANDOFF_20261016 says
  "Decisions 1,200", DECISION-LOG stops at D-3051. Pick ONE source of truth (`decisions.yaml`) and let the
  derived census (`config/decisions_summary.json`, via `scripts/recompute_decision_summary.py`) carry the total.

## VERIFY-DRIFT (exact, copy-paste — no mutation)
    cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
    grep -oE "D-[0-9]{3,5}" DECISION-LOG.md | sort -t- -k2 -n | tail -3   # expect D-3051 until synced
    for d in D-3058 D-3071 D-3072 D-3073 D-3086 D-3092 D-3095 D-3097 D-3099 D-3100; do
      printf "%s: " "$d"; grep -c "$d" DECISION-LOG.md; done               # expect 0 until synced

## LANDING STEPS (after owner word) — copy-paste
1. Window-rise (config/agent_context.yaml, owner-gated):
   - `cache_conditional.measured_state: cache_disproven → cache_proven`
   - `GOOSE_AUTO_COMPACT_THRESHOLD: 0.8 → 0.94`
   - re-prove: `python3 scripts/agent_context_probe.py --prefill-ab`
2. Registry sync (after owner word): reconcile DECISION-LOG.md from decisions.yaml via
   `scripts/gov_sync.py` OR docguard `safe_append` on DECISION-LOG.md (append_only) — confirm which at
   execution; the VERIFY-DRIFT grep above is the receipt that the gap closed.
3. Cloud ceiling (after owner word): edit `config/delegation_economy.yaml` ceiling — shrink-only (D-3023).
4. Splash A/B (APPROVED): run T-187 fixture, Splash ON vs OFF, on Qwen3.8-27B-MLX-4bit.

## CACHE / MEMORY POLICY FOR THE NEW SESSION
- Do NOT clear memory: it holds sovereign decisions + drift guardrails (C1/C3). Clearing = deleting the guardrails.
- Do NOT clear model/prefix cache: BUG-885 proved the prefix cache is the CHEAP asset; a cold model reload
  costs 42–134 s TTFT.
- Clear ONLY stale `temp/*_bak` via `pipeline/safe_delete.py` (never `rm` pipeline output — R-D410).

## NEXT CRITICAL (consequential order, post-word)
1. Window-rise land (pending A) → 2. BUG-917 cloud ceiling (pending) → 3. Splash A/B (APPROVED, gated by T-187)
→ 4. T-129 identity collapse (is_convergent 1393→896; the "advertised corroborated ≤123" voice-axis target is
re-scoped OUT of T-129 into owner decision #3) → 5. BUG-918 S0 PDF image-dump → 6. Registry sync (pending).


---

## LANDED 2026-10-18 (owner word received — all four items)

### 1. temp/*_bak — CLEARED
`safe_delete.py` ran on all five `temp/*_bak` files; backup preserved at `backup/deletions/20261018_235150/`. Sovereign memory + model/prefix cache left untouched (per policy).

### 2. WINDOW-RISE — A, LANDED + RE-PROVEN
- `config/agent_context.yaml`: `cache_conditional.measured_state: cache_disproven → cache_proven`.
- `GOOSE_AUTO_COMPACT_THRESHOLD: 0.8 → 0.94` (= (32768−2048)/32768), `min_headroom_tokens: 2048` unchanged.
- Re-proof `python3 scripts/agent_context_probe.py --prefill-ab`: **96.54x against the 5.0x bar → proven** (call1 125.5s cold / call2 1.3s warm, cached 26,237/26,240). Stronger than BUG-885's 22.2x.
- ⚠️ **NEW SESSION REQUIRED**: harness knobs are read at session BIRTH — this session can never show 0.94.

### 3. CLOUD CEILING — RAISE landed, SPLIT deferred with reason
- `config/delegation_economy.yaml`: `cloud_calls 37,000 → 50,000` (owner word, D-3023, reason recorded inline). Clears the BUG-917 calls breach.
- **NEW REVELATION (surfaced by the re-run)**: the instrument now shows a SECOND breach — `cloud_input_tokens 4,641,939,479 > ceiling 4,600,000,000`. This is a lifetime-counter fact that BUG-917's calls-only framing hid; the token counter grew past its ceiling since the 2026-10-15 baseline. **Owner word still owed**: raise-with-reason (interim) vs SPLIT (durable) applies to the TOKEN ceiling too, not just calls.
- SPLIT is **not a YAML edit**: `usage_ledger` has no declared pipeline-vs-harness classifier column (`session_id` + `is_compaction` exist, but the tier is decided by model family only). A durable SPLIT needs a NEW declared resolution (which session_ids are pipeline workers) — a decision, not an edit (D-3034). Filed as follow-up.

### 4. REGISTRY — ALREADY IN SYNC (the "10-entry gap" was a misreading)
- `gov_sync.py --check` = **OK** (4 faces equal re-derivation: **1227 decisions** / 704 bugs / 58 open tasks).
- `config/decisions.yaml` holds **1227 unique records, D-2978…D-3100**; `decisions_summary.json` census total = 1227, sha matches.
- The earlier "DECISION-LOG.md stops at D-3051 / 10 entries missing" measured the NARRATIVE-HISTORY section below the GOV-HISTORY sentinel — which is **dated history, no live claim** by design (D-2981/D-2986). The derived GOV-INDEX block already reflects all 1227. **Nothing to sync.** No D-numbers were fabricated.

## VERIFY (copy-paste, post-landing)
    cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
    grep -n "measured_state\|GOOSE_AUTO_COMPACT_THRESHOLD" config/agent_context.yaml | head -4
    python3 scripts/gov_sync.py --check           # expect: ok, 1227 decisions
    python3 pipeline/delegation_economy.py --check # expect: rc 1, TOKEN breach (still open — owner word owed)

## NEXT OWNER WORD (the only open item)
- **Cloud TOKEN ceiling** (4.64B > 4.6B): raise-with-reason to ~5.0B, or SPLIT first (declared pipeline-session classifier). Recommend RAISE-with-reason now + SPLIT as a decision.


---

## LANDED 2026-10-19 (00:00 +02:00) — TOKEN CEILING · SPLASH VERDICT · REGISTRY SYNC

### 1. Cloud TOKEN ceiling — RAISED to 5.0B (owner word received)
- `config/delegation_economy.yaml`: `cloud_input_tokens: 4,600,000,000 → 5,000,000,000`, reason recorded inline (owner word 2026-10-19, D-3023 raise-with-reason; lifetime counter 4,642,796,210 breached the 4.6B ceiling sized against the 3,981,322,921 baseline). `updated` bumped 2026-10-15 → 2026-10-19.
- Receipt: `python3 pipeline/delegation_economy.py --check` → **rc 0, no BREACH** (ceiling now reads 5,000,000,000.00).
- The SPLIT (durable) remains owed as a DECISION, not an edit: `usage_ledger` still has no declared pipeline-vs-harness session classifier. The counter has already grown ~500k tokens since the 2026-10-18 handoff, confirming a lifetime counter always re-breaches any flat number.

### 2. SPLASH A/B — DEFERRED with reason (NOT run; nothing proven)
- **No A/B receipt exists.** The gate it was "approved to open" behind is T-187 (the two-tool/two-step fixture), which is **unbuilt** — `scripts/measure_subagent_loop.py` still carries only the single-tool 3-call fixture (FIXTURE_LINES 3/4/5, one read tool); the T-187 two-tool/distractor/dependent-steps shape does not exist. Nothing was measured.
- **D-2768 remains RESOLVED and dispositive** (no supersession record exists in `config/decisions.yaml` — verified). Splash's supported architectures are EXACTLY Qwen3.8-27B / Qwen3.6-35B-A3B / Prism Bonsai 2. Maxwell's generator (Qwen3-Coder-30B-A3B) and classifier (gpt-oss-20b) are NOT in the registry, so Splash cannot accelerate either. A positive A/B on Qwen3.8-27B (a model Maxwell serves but does not use in any role) would still buy ZERO pipeline value.
- **Ontology correction (drift flagged):** the prior handoff's "Splash M1 overturns D-2768's M3 gate" conflates TWO distinct gates. The M1 backport (paperniuk 1.1.0-m1) overturns only **D-406's HARDWARE gate** ("M3 or newer" excludes M1 Max). It does NOT overturn **D-2768's model-scoping gate**, which is the dispositive one. D-2768/D-2771 already register the rejection with reason (D-3038 satisfied — no new decision minted; a redundant one would be bloat).
- **Re-open trigger (only):** if Maxwell later ADOPTS Qwen3.6-35B-A3B or Qwen3.8-27B as a role (a model-adoption decision, not a Splash decision) AND OMLX ≥0.7.1 stable lands (installed = 0.7.0), THEN a decode-speed A/B on that model is worth running. Until then: Splash applicability = NONE (D-2768).

### 3. REGISTRY — SYNCED
- `gov_sync.py --apply` re-cut the GOV-INDEX census lines in all 4 faces (write_guard; 3+3+3+0 lines) and cleared the 4 join faults that had accumulated from the prior session's late bug/task closures (BUG-918/934-938, T-129).
- Receipt: `python3 scripts/gov_sync.py --check` → **rc 0, 4 faces equal** (1227 decisions / 704 bugs / 58 open tasks). `--selftest` 26/26 before apply (incl. the BUG-937 "history region stays byte-identical" guard).

### 4. NEXT CRITICAL (consequential order, post-session)
1. **T-183 — THE ADMIT APPLIER** — the ONLY open owner-mover task: owner signs the admission plan (`just admit-sign "<name>"`, D-3072) to admit library works through the crash-safe applier (dry-run prices the 479-row plan at 8,271.5 MiB). **Manual owner act — see instructions below.**
2. **Cloud-ceiling SPLIT** (durable fix for both calls and token counters): declare a pipeline-vs-harness session classifier for `usage_ledger` — a DECISION (D-3034), not a YAML edit.
3. **Splash** — nothing to do until the re-open trigger above fires.

### MANUAL OWNER STEP (T-183) — copy-paste
    cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
    just admit-sign "governance/ADMISSION_PLAN_20261017.json"   # signs the accepted plan (D-3072)
    # expected: a signed disposition + the applier's dry-run price (~8,271.5 MiB) printed, nothing copied yet.
    # if it differs: re-read T-183's gate (scripts/apply_admission.py refuses unsigned rows / existing targets / pre-rename).


## CORRECTION 2026-10-19 (00:08 +02:00) — SPLASH "APPLICABILITY = NONE" WAS OVERCLAIMED (Qwen3.8-27B IS a role)

The LANDED 2026-10-19 §2 above (and the re-open trigger in the line 110 block) contain a factual error, found
by re-reading `config/model_assignments.yaml#harness_roles` (dated 2026-10-15, T-138):

- **Qwen3.8-27B-MLX-4bit is ALREADY a Maxwell role** — `AGENT_EDIT_LONG_CONTEXT`, basis *"lc_reason 1.0,
  niah 1.0, reviewing 1.0, humaneval 0.96, ifeval 1.0 — the strongest axis set in the portfolio"*.
  Therefore the phrase *"a model Maxwell serves but does not use in any role"* is FALSE, and the re-open
  trigger *"if Maxwell later ADOPTS Qwen3.8-27B as a role"* has **ALREADY FIRED**.

- **The CORRECTED verdict — still DEFER Splash, but for the right reasons:**
  1. Splash is an ENGINE SWAP (`incoai/splash`: proprietary package format = C2, "no config" = C12/C21/C24),
     not a speed toggle. The M1 backport (`paperniuk 1.1.0-m1`) overturns only D-406's HARDWARE gate, not C2/C12.
  2. The speedup itself is obtainable WITHOUT Splash [D]: the drafter is published separately
     (`incoai/Qwen3.8-27B-DFlash2`) and runs via `mlx-dspark` (MIT, same MLX foundation, no engine swap);
     oMLX 0.7 already ships lossless speculative decode (Lightning MTP, +34–58% decode). [K] the actual
     DFlash2-on-27B speedup is NOT measured on this machine.
  3. The binding constraint on Qwen3.8-27B is PREFILL, not decode: BUG-793 measures 39 tok/s (672 s per
     26,214-token turn). Speculative decode accelerates DECODE only, so Splash/DFlash2 does NOT touch the
     blocker. The real lever is BUG-793's declared remedy (`specprefill_enabled: False` on this model,
     `memory_guard_tier: aggressive`), not a new engine.

- **Net:** no governance decision changes — D-2768 (model-scoping), D-2771 (Prism rejection), D-406 (hardware
  gate) all stand. Only the handoff's "NONE applicability" phrasing is corrected. Splash ENGINE adoption
  remains NO. A DFlash2 DECODE A/B on Qwen3.8-27B is worth running ONLY after BUG-793 is diagnosed (it
  measures decode, not the prefill that blocks the role).


## SESSION 2026-10-19 (00:17 +02:00) — STATE, ADMIT-APPLY RESULT, AND THE COMMIT-FIRST BLOCK

### What landed this session
- BUG-563 FIXED: `governance/session_plan_20260924.yaml` may_touch gained `governance/HANDOFF_*.md`; `check_repo_integrity --worktree` now green (16 dirty → 16 granted). The prior CORRECTION-append had left the handoff file ungranted, which red'd `just health`.

### admit-apply (T-183) — the owner's run DID work: 1 applied, 2 failed fail-closed (not a bug)
- `already_applied` 1: `Semiotics-the-Basics.pdf` (markdown already on disk, receipt accounts for it).
- `failed` 2, both caught by the S0 100-byte floor (honest, never a silent empty):
  - `Proposal.docx` → 54-byte markdown. Root cause: near-empty STUB (word/document.xml 4,048 bytes, no `media/`). No content to extract — exclude, or replace with the real doc.
  - `pre-hire.pdf` → 62-byte markdown. Root cause: Docling limitation (8-page PDF; `pdftotext` extracts real text, Docling stops at the header). Content EXISTS — retry via a pdftotext/OCR path before excluding.
  - Both quarantined to `admission_quarantine/20261018T221225Z/` (fail-closed worked exactly as designed).

### DeBERTa as a "decision model": VALIDATES the existing architecture — no change
Red Hat's A/B (the linked short): a ~200M-param DeBERTa classifier ≈ Qwen-35B (89.01% vs 89.31%) at ~54 ms on a laptop CPU, beating "decision models" (TypeShift Jev). Maxwell already runs DeBERTa-v3-large as the S5 NLI verifier (D-2298, fail-closed). Verdict: NO Jev-style decision model; DeBERTa IS the decision model, and it is already the right one. Keep S4=gpt-oss (open classification), S5=DeBERTa (binary entailment).

### Cloud-ceiling SPLIT — DRAFTED as D-3101, gated on COMMIT-FIRST (D-2860)
D-3101 PROPOSED: split the lifetime `cloud_input_tokens`/`cloud_calls` ceilings into two classes — pipeline-ingestion (batch/bounded) vs harness-metering (ongoing escalation) — each a windowed/burn-rate ceiling, NOT a raised flat number (a lifetime counter re-breaches any flat number — BUG-917). Discriminator MUST RESOLVE (D-3034): `model` ∈ declared `cloud_model_families` + `cost_source`, never a sentence. NOT yet minted: the commit frontier refuses new decisions while governance state sits uncommitted.

### IMMEDIATE NEXT (BLOCKING): commit the governance backlog
`check_commit_frontier` (D-2860, anti-circle) refuses to proceed while FOUR governance files are UNCOMMITTED (re-cut by the prior `gov_sync --apply`, never committed): `governance/buglog.md`, `governance/bug_status.json`, `MASTER-TASK-REGISTER.md`, `agent/session_seed.yaml`. Commit these FIRST → then D-3101 can be minted → then BUG-793 measurement.

### BUG-793 status (Qwen3.8-27B prefill 39 tok/s) — already at best config; measurement-gated
The model's own `~/.omlx/model_settings.json` already has every speculative/prefill lever OFF (`specprefill`, `dflash`, `mtp`, `qwen35_ane_prefill`, `turboquant_kv` all false). So BUG-793 is NOT a config-flip. The remaining untried levers are `turboquant_kv_enabled: true` (KV 4-bit quant — the "KV memory pressure" candidate) and the `sudo sysctl iogpu.wired_limit_mb=57344` system lever (D-334). Both are MEASUREMENT-gated (D-332, never vibe-set). Resolution = a red/green prefill A/B at the class context size (26,214 tokens), not more speculation.


## SESSION 2026-10-19 (00:27 +02:00) — D-3101 MINTED, DUST REJECTED, TREE CLEAN
- **Commit verified**: `dbf80ff` (owner commit) landed; commit-frontier rail GREEN.
- **Second batch committed**: `8184df8` — T-129 identity collapse applied (62 source_ids collapsed, 893 rows repointed, is_convergent 1393→896, 0 deleted), BUG-885 prefix cache PROVEN (threshold 0.8→0.94, `cache_proven`), cloud ceiling 4.6B→5.0B owner-raised, admission plan 20261018.
- **D-3101 MINTED (PROPOSED)**: cloud-ceiling SPLIT — pipeline-ingestion vs harness-metering are two metering classes, not one lifetime counter. Discriminator must RESOLVE via model ∈ cloud_model_families + cost_source (D-3034). Cites BUG-917. Committed `a75ffeb`; census re-derived (1228 decisions). **Not yet ratified** — PROPOSED, awaiting owner word.
- **dust (qlabs-eng/dust) REJECTED** (D-3038): backprop-free *training* algorithm, requires NVIDIA CUDA bfloat16 + 8 GPUs. Zero overlap with Maxwell (Apple M1 Max, MLX local *inference*, C1 $0 / C3 sovereign). Not inference accel, not speculative decode, not tool-calling.
- **BUG-793 reframed by BUG-885**: prefix cache proven (22.2× on 26,240-token prefix) → the "672 s prefill per turn" is now COLD-turn-only. Remaining diagnosis is the *anomalous cold prefill rate* (39 tok/s vs gpt-oss 210), not the per-turn cost.

## OWNER MANUAL STEPS (D-3100: noob-proof)
**1. Admission rows (proposal.docx exclude / pre-hire.pdf reroute).** Source = `~/Library/CloudStorage/Dropbox/education/journals:notes` (config/ingest_identity_gate.yaml#source_library.roots.journals_notes). The two failed rows are already quarantined at `knowledge pipeline/admission_quarantine/20261018T221225Z/`.
- *Proposal.docx* = near-empty stub (document.xml 4,048 B, no media). EXCLUDE: owner records a word that this work is not-admittable (stub), so plan_admission stops proposing it.
- *pre-hire.pdf* = 8-page PDF with real text; Docling writes 62 B (fails 100-B floor) but `pdftotext` extracts it. REROUTE = add a pdftotext fallback to `pipeline/stage0_convert.py::convert_pdf` when Docling emits <100 B but the pdftotext probe finds real text (the probe already exists, lines 119–131). Re-run `python3 scripts/plan_admission.py --plan` after, to clear the row.
**2. BUG-793 cold-prefill A/B (measurement-gated, D-332).** Run `scripts/agent_context_probe.py --prefill-ab` (opt-in) at 26,214 tokens on Qwen3.8-27B with `turboquant_kv_enabled` toggled true vs false; record tok/s + TTFT. Then `sudo sysctl iogpu.wired_limit_mb=57344` (D-334, system lever, not auto-applied). Receipt decides; no vibe-set.

## NEXT CRITICAL (consequential order)
1. Ratify D-3101 (owner word) → then implement the SPLIT (pipeline-ingestion vs harness-metering windowed/burn-rate ceilings).
2. BUG-793 cold-prefill A/B (above).
3. DFlash2 decode A/B on Qwen3.8-27B (deferred until BUG-793 diagnosed).
4. Splash engine stays NO; Prism Bonsai 2 download stays rejected; DFlash2 via mlx-dspark is the decode-speedup path (not an engine swap).
