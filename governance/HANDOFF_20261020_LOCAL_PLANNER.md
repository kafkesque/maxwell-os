# HANDOFF 2026-10-20 — THE COST LEAK NAMED: GOOSE_PLANNER override + birth-pin; D-3113 applied

> Written for a NEW goose session (start `goose run` fresh to pick up the LOCAL planner — knobs are read
> at session BIRTH, so THIS session can never show them; see BUG-877). Read
> `governance/CONTEXT_INDEX.md` first for where the long-lived registers live; this file is the
> session-scoped delta.

## THE REVELATION — "am I charged right now?" (measured, not assumed)

YES. At 2026-10-19T22:11Z the usage ledger's newest row was `deepseek-v4-pro`, session `20261019_2`
(this session), ~$0.01/call. Oct-18 $8.41 + Oct-19 $7.70 = **$16.11 over 2 days**, matching the DeepSeek
dashboard's ~$17. Lifetime real spend since May: **~$1200** ($600 May→Aug + $600 Aug→now). A **$39.35
compensation credit** (2026-10-15) offsets ~5 days at this rate — a buffer, not a fix.

TWO independent layers kept the charge running:

1. **GOOSE_PLANNER override (the fixable one).** D-3104 (owner, 2026-10-19) declared
   "active=local, escalation=cloud, **GOOSE_PLANNER stays deepseek**" — a clause that contradicted its
   own first clause. `~/.config/goose/config.yaml` carried `GOOSE_PLANNER_PROVIDER: custom_deepseek` /
   `GOOSE_PLANNER_MODEL: deepseek-v4-pro`, so the session PLANNER (which runs EVERY turn) was deepseek.
   "everyday decisions on gpt-oss-20b, $0 marginal" was therefore never achieved.
2. **Session-birth pin (BUG-877, OPEN).** A running session keeps the model it was BORN with and never
   re-reads the config mid-run. So a correct file alone is insufficient — **routing local requires a NEW
   session (`goose run`)**.

## WHAT LANDED THIS SESSION (commit `6c44b47`; tree clean)

- **Config fix (system file, backed up):** `~/.config/goose/config.yaml` lines 313-314 changed
  `custom_deepseek`/`deepseek-v4-pro` → `maxwell_omlx`/`gpt-oss-20b-MXFP4-Q8`
  (backup: `~/.config/goose/config.yaml.bak.20261020_prelocalplanner`). `active_provider` was already
  `maxwell_omlx`; YAML re-validated. Everyday loop is now local (gpt-oss-20b, $0 marginal).
- **D-3113 (RESOLVED)** in `config/decisions.yaml`: overturns D-3104's planner clause; deepseek is now an
  EXPLICIT escalation for strategic D-3xxx decisions only, never the ambient planner.
- **Census re-derived:** 1239 → **1240** decisions (resolved 334→335); stamp `0fb5f9b41e2d2d09` →
  `0c8a9e564ca3fd8d`. Faces re-cut; `gov_sync.py` GREEN (4 faces, rc 0), `check_harness_homes.py` 5/5 BOUND.
- **Hard-won mechanic (do not repeat the miss):** the decision CENSUS is `config/decisions_summary.json`,
  NOT `config/decisions.yaml`. A decision append needs the chain:
  append → `python3 scripts/recompute_decision_summary.py` → `python3 scripts/gov_sync.py --apply` →
  `python3 scripts/gov_sync.py` (must be GREEN). Skipping the middle step leaves faces at the OLD count
  (this is exactly the "4-step manual chain" drift the 2026-10-19 handoff flagged).

## FIRST THING THE NEW SESSION MUST DO (verify the switch)

1. It is already born on `maxwell_omlx`/gpt-oss-20b if started with a plain `goose run`.
2. Verify with this read (token-cheap):
   ```
   sqlite3 "file:$HOME/.local/share/goose/sessions/sessions.db?mode=ro" \
   "SELECT datetime(created_timestamp,'unixepoch'),model,round(cost,4) FROM usage_ledger ORDER BY created_timestamp DESC LIMIT 5;"
   ```
   Expected: top rows name `gpt-oss-20b-MXFP4-Q8`, cost blank/0. If they STILL say `deepseek-*`, the
   planner key is not the operative lever and BUG-877 is the sole cause — report the exact rows.
3. **Counter rule (never confuse again):** the goose COUNTER counts TOKENS across all models and rises
   even at $0 — it is NOT a cost signal. You are charged **iff the ledger row's MODEL is deepseek/cloud**;
   the dashboard balance drops only on a deepseek row.
4. Optional, since gpt-oss-20b is a 20B loop model: if its quality proves too thin for a long turn, the
   escalation path is a DELIBERATE deepseek call (e.g. `delegate` to `custom_deepseek`), never resetting
   the planner.

## NEXT CRITICAL STEPS (consequential order — highest leverage first)

1. **BUG-917 SPLIT — now urgent.** `pipeline/delegation_economy.py --check` compares LIFETIME cloud cost
   ($130.19) to a shrink-only ceiling ($130.00, D-3023). Going local STOPS the burn but does not lower the
   lifetime total, so `just health` keeps RED at that line on a historical number. Fix: windowed
   burn-rate on ACTUAL billed cost, estimate kept only as a labelled proxy. This also closes the
   "tripwire measured estimates, not dollars" blindspot (all 38,892 ledger cost rows are `estimated`).
2. **BUG-877** — append the 2026-10-20 live reading to the buglog; the defect (a governed config write not
   reaching the running session) is structural, not this session's doing.
3. **BUG-948** — highest OPEN bug (`owner_marks.rule_digest` whole-file sha256 stale-ifies the pair
   object; red-loop-first D-3036).
4. **T-187 receipt persistence** — the two-step receipt lives only in gitignored `temp/`; persist it.
5. **F-03** — confirm status (CONTEXT_INDEX: re-scoped designed state, deferred until content_type
   certified).

## CURRENT CENSUS (verified this session)

**1240 decisions** (stamp `0c8a9e564ca3fd8d`) · **713 bugs (252 open / 461 closed; highest OPEN =
BUG-948)** · 57 open tasks. BUG-941 is ALREADY RESOLVED (buglog L18787); D-3110/3111/3112 already
present. The older "consequential order" (BUG-941 close, D-3108 commit) was already done before this
session — do not redo it.

## CAREFUL / DO-NOT-DRIFT

- `config/decisions.yaml` + `governance/buglog.md` are APPEND-ONLY by convention — append, never rewrite.
- `~/.config/goose/config.yaml` is a SYSTEM file outside the repo's `config/*.yaml` protection — back up,
  re-validate YAML, and remember the running session never picks it up (birth-pin).
- The repo's protected files (CONSTITUTION.md, DECISION-LOG.md, AGENTS.md, config/*.yaml, governance/*.md)
  are untouched this session EXCEPT the gov_sync face re-cuts (DECISION-LOG.md / MASTER-TASK-REGISTER.md /
  buglog.md census lines) which gov_sync owns by design.

---

# DELTA 2026-10-20T09:5x local — THE TWO QUESTIONS ANSWERED, TWO REPAIRS LANDED, ONE OWNER WORD OWED

> Session: `20261020_1` ("Maxwell OS provider selection"). **This session was BORN on
> `custom_deepseek/deepseek-v4-flash` and billed every turn** — see §1.3. Read this section first; §"THE
> REVELATION" above is still true and is now superseded in one respect (the planner fix HELD; the executor knob
> was moved by hand afterwards).

## 1. THE ANSWERS (each with the reading that decides it)

### 1.1 oMLX version: **0.7.1rc1. Do not go back to 0.7.0.**

- **Measured:** `~/.omlx/bin/omlx --version` → `0.7.1rc1`; `GET /health` (with `OMLX_API_KEY`) →
  `status: healthy`, `model_count: 8`, `loaded_count: 3`, `current_model_memory: 24.1GB`, `final_ceiling: 61.4GB`.
- **Governed:** D-3102 (2026-10-19, RESOLVED) A/B-measured rc1 vs 0.7.0 on cold
  `Ornith-1.5-35B-A3B-REAP-19B` @4010 tok: **load 5.9s → 3.68s (−37.6%), wall 17.7s → 15.8s (−10.7%),
  prefill/TTFT flat**. ADOPTED. Rollback is preserved at `/Applications/oMLX-0.7.0.app` — the downgrade question
  is therefore not "which is safer", it is "why give up a measured −37.6% load for a rollback you already have".
- **Honest caveat (D-3102 already states it):** the `decode 96.91 → 222.13 tok/s` line in that decision is a
  SINGLE-TOKEN artifact (`max_tokens=1`) and was NOT promoted; the real shipped number came later from
  `measure_prefill.py --max-tokens 128` (~39 tok/s on that model). The adoption stands on **load + wall**, not on
  decode.
- **DRIFT FOUND AND REPAIRED THIS SESSION:** `config/pipeline_config.yaml` still pinned `pinned_version: 0.7.0`
  (D-2772, 2026-10-02) while the adopted, running engine is 0.7.1rc1 — the BUG-623 stale-pin class. Synced to
  `0.7.1rc1` with the D-3102 receipt in a comment; `min_version: 0.4.0` untouched. **`pinned_version` has no
  runtime consumer** (`monitor_stacks.py` gates on `min_version`) — so this was documentation truth (D-3034),
  not a functional fix, and it is labelled as such in the file.

### 1.2 Provider: **`maxwell_omlx` + `gpt-oss-20b-MXFP4-Q8` is the right ambient brain.** DeepSeek is a
### per-call ESCALATION, never the session default.

There are **TWO independent knobs** — confusing them is what produced this morning's bill:

| role | knob (in `~/.config/goose/config.yaml`) | correct value | why (measured / governed) |
|---|---|---|---|
| **planner** (runs every turn) | `GOOSE_PLANNER_PROVIDER` / `GOOSE_PLANNER_MODEL` | `maxwell_omlx` / `gpt-oss-20b-MXFP4-Q8` | D-3113; **verified HOLDS in the file this session** |
| **session executor** (the model you talk to) | `active_provider` + the session's `model_config_json` | `maxwell_omlx` / `gpt-oss-20b-MXFP4-Q8` | C1/C3; $0 marginal — **MOVED to `custom_deepseek` at 09:31 today** |
| **cloud escalation** | `delegate(provider: "custom_deepseek", model: "deepseek-v4-flash")` | explicit, per call, with a D-3023 reason | D-3023 |
| **pipeline generation** | n/a (never a harness provider) | local (Qwen3-Coder / gpt-oss classifier) | C1 |

**Why gpt-oss-20b is not a downgrade-by-vibes:** D-3103 re-ruled the capability axes **on receipts** —
gpt-oss-20b **PASSES** the native-tool two-step dependent loop on T-187 (slowest turn 35.3 s, decode 42.4/42.4/42.0
tok/s) and scores **6/6 = 1.0** on 16k long-context reasoning. Its old 0.0 was measured on the RAW-JSON tool
format, which is not the format Goose uses. It is slower than DeepSeek; it is **$0 marginal**. That is the trade
C1 asks for.

**On "DeepSeek as the delegate, gpt-oss as the brain" — the correct reading and the inversion to avoid:**
- ✅ **local brain + explicit cloud delegate** is the sanctioned shape. Rule: **every `delegate` call must name
  `provider` and `model`**, because an unnamed delegate **inherits the session's provider** — if the session is
  cloud, an "accidentally local" delegate is a myth.
- ❌ **cloud brain + local delegate** — i.e. what is running right now — is the expensive shape, and the reason is
  arithmetic, not preference: the **session's own context is the cost driver** (this session's input per turn grew
  12,598 → 37,339 tokens across 10 turns; every turn re-sends it). Delegates are small by comparison.

### 1.3 "Am I being charged right now?" — **YES, and here is the exact proof**

- `ps`/`lsof` at 09:34 showed process `goose` with an ESTABLISHED TLS connection to **3.173.21.63**, and
  `dig +short api.deepseek.com` → **3.173.21.63** (CloudFront).
- `usage_ledger` rows for **this session id** `20261020_1`, all `model=deepseek-flash`,
  `cost_source=estimated`: **10 rows by 07:35:43Z, $0.0128**, input tokens climbing 12,598 → 37,339. **Zero
  local-model rows on 2026-10-20.**
- The local engine was healthy **three minutes before** this session was born: `~/.omlx/logs/server.log` records
  `model=gemma-4-E4B-it-MLX-4bit` completions at 09:30:49 / 09:31:15 / 09:31:28 local (prompt 17,318 / 17,555
  tok), belonging to session `20261018_6` (`maxwell_omlx`, `updated_at` 07:31:28Z). Session `20261020_1` was then
  **born at 07:34:23Z on deepseek**. The 3-minute gap between "last local completion" and "cloud-born session" is
  the entire cost of the two knobs being set independently.
- **The counter rule, restated:** the goose token counter rises even at $0 — it is NOT a cost signal. You are
  charged **iff the ledger row's MODEL is a cloud model**. The dashboard balance drops only on a deepseek row.

## 2. WHAT LANDED THIS SESSION (both safe, both verified)

1. **Stale pin repaired** — `config/pipeline_config.yaml`: `pinned_version: 0.7.0` → **`0.7.1rc1`**, with the
   D-3102 receipt + rollback path inline, YAML re-validated, and the "no runtime consumer" fact stated so nobody
   reads it as a gate.
2. **BUG-877 live reading appended** (`governance/buglog.md`, bullet under the BUG-877 entry) — **the writer is
   now NAMED, one layer outside the bug's original frame**: the harness app rewrote `active_provider` (and the
   provider's `model`) at 09:31 and **its write survived**, while the agent's D-3113 planner edit from ~9h earlier
   **also survived**. That refutes "the home reverts agent writes" and narrows the defect to *two writers, last
   write wins per key*. Cause still a HYPOTHESIS (D-3036) with the red loop named: read → switch in app → re-read.
3. **Verification after both:** `python3 scripts/gov_sync.py` → **GREEN, rc 0**, 4 faces equal re-derivation
   (**1240 decisions / 713 bugs / 57 open tasks** — census unchanged, as a doc-truth edit must leave it).
   `scripts/check_harness_homes.py` → **rc 2, 4 bound / 1 conflicting** (`active_provider`) — the rail is RIGHT
   and is reporting the owner's 09:31 switch, not a new defect.

## 3. MANUAL STEPS (D-3100 — numbered, copy-paste-able, with the branch if it differs)

### Step 1 — put the SESSION back on the local brain (stops the meter)

1. In the Goose app, open the **provider/model selector** — the same control you used this morning to switch to
   DeepSeek. Select **`Maxwell OMLX`** as provider and **`gpt-oss-20b-MXFP4-Q8`** as model.
2. **Start a NEW chat** (new session). The running chat **cannot** change providers mid-run (birth pin, BUG-877) —
   switching the selector alone will not move this conversation off DeepSeek.
3. Verify the file took the switch:
   ```
   grep -n "active_provider" ~/.config/goose/config.yaml
   ```
   **Expected:** `active_provider: maxwell_omlx`.
   **If it still says `custom_deepseek`:** the app wrote the value but kept the old one for the open session — quit
   and reopen the app, re-read. If it still will not take, start the session from a terminal instead:
   ```
   cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0" && goose run
   ```
4. Verify the NEW session is actually local (the only reading that settles it):
   ```
   sqlite3 "file:$HOME/.local/share/goose/sessions/sessions.db?mode=ro" \
   "SELECT datetime(created_timestamp,'unixepoch'),model,round(cost,4) FROM usage_ledger ORDER BY created_timestamp DESC LIMIT 5;"
   ```
   **Expected:** newest rows name `gpt-oss-20b-MXFP4-Q8` with cost blank/0.
   **If they name `deepseek-*`:** the session is still cloud-born — go back to 1.3's proof and report the rows
   verbatim; do not "fix" it by editing the file again (that is the mistake BUG-877 records).
5. Verify the rail closes:
   ```
   python3 scripts/check_harness_homes.py; echo rc=$?
   ```
   **Expected:** `5 declared fact(s) | bound 5 | conflicting 0`, `rc=0`.
6. **Known cost of Step 1:** the first local turn pays a cold model load (measured 42 s – 134 s TTFT on this
   machine). That is a one-time latency bill, not a money bill.

### Step 2 — ONE OWNER WORD: BUG-917 (see §4). Nothing else on the critical path needs you.

## 4. THE ONE OWNER DECISION OWED — BUG-917 (this is the highest-leverage step and it is yours)

`just health` **stops at line 54 of 184** on this single line:

```
BREACH  cloud cost USD: 130.44 > ceiling 130.00
```

The ceiling is a **LIFETIME** counter (D-3023, shrink-only). Going local STOPS the burn but can never lower a
number already over the line — so `just health` stays RED forever, and **130 lines of the ladder stay dark**.
BUG-917's own entry names the three routes; the two interim raises already happened for the other two counters
(calls 37,000→50,000 on 10-18, tokens 4.6B→5.0B on 10-19) **"pending the SAME SPLIT named below"** — i.e. the
file itself says the split is the intended durable fix.

| option | what it costs | consequence |
|---|---|---|
| **1. Raise `cloud_cost_usd` with a named reason** | one line + one owner word | fastest green; keeps the *defect class* (a lifetime counter always re-breaches) and keeps pipeline + harness answered by ONE number — the conflation BUG-917 calls "the uncomfortable part" |
| **2. SPLIT into two declared streams** — `pipeline` (must be $0, C1) and `harness` (metered, capped separately) | one owner word + ~1 decision + selftests on `delegation_economy.py` (it already has 14/14 known-answer controls) | **ontologically correct**: it stops one counter answering two different questions; each stream can go green honestly; no ceiling is raised |
| **3. Keep it red, read it every session** | nothing | `just health` cannot be the first line of defence; `just health-full` (1087 s) becomes mandatory |

**Recommendation: option 2, then option 1 only if you want green today while 2 is built.** Rationale is
measurement-grounded: the instrument already distinguishes the tiers (`local 467 calls / $0.00` vs
`cloud 39,956 / $130.44`), and **`cost_source` shows 38,951 of 40,424 rows are `estimated`** — so the split must
ALSO carry a *windowed burn-rate on billed rows*, or it stays a proxy wearing a dollar sign (BUG-917's second
blindspot). Both belong in the same act.

**Not done here, deliberately:** no ceiling was raised, no counter was split, no task row invented for an
undecided route (D-3035: an open owner-lane row is a proposal, not an approval). The red loop for the split is
already available — `delegation_economy.py --selftest` is 14/14 and the fixture that reads a cloud row over a
ceiling already exists (`a_cloud_row_over_the_ceiling_reads_BREACH`); the split needs a control that proves the
same ledger yields TWO readings and that a pipeline row can never be counted as harness.

## 5. NEXT CRITICAL STEPS — revised consecutive order (supersedes §"NEXT CRITICAL STEPS" above)

1. **Step 1 of §3 — move the session to local.** Zero engineering, stops the meter, ~1 minute. Everything else
   is paid for in tokens until this is done.
2. **BUG-917 split (§4)** — the only line dark-ing 130 of 184 health lines; unblocks the ladder for every
   downstream fault.
3. **BUG-948** (highest OPEN bug) — `owner_marks.rule_digest` is a whole-file sha256, so any append to
   `config/corroboration_collapse.yaml` stale-ifies the pair object. Red-loop-first (D-3036).
4. **BUG-877 remedy (b)** — make the provider switch SAY "new session required", and decide whether the app may
   keep writing a governed key. The reading is landed; the rail gap is not.
5. **T-187 receipt persistence** — the two-step receipt lives only in gitignored `temp/`.
6. **F-03** — unchanged, deferred until `content_type` is certified.

**DONE and must not be redone:** BUG-941 close, D-3108, D-3110/3111/3112/3113, the D-3113 planner flip
(verified intact), BUG-877's append (landed this session), the 0.7.1rc1 pin sync (landed this session).

## 6. DO-NOT-DRIFT (additions from this session)

- **Two knobs, not one.** `GOOSE_PLANNER_*` and `active_provider` are independent; a handoff that fixes only the
  planner still bills the executor. State BOTH in any provider handoff.
- **The app is a second writer of `~/.config/goose/config.yaml`.** Never conclude "an agent write was reverted"
  without a two-point reading either side of a switch (that mistake is what BUG-877's original frame recorded).
- **`pinned_version` is documentation, `min_version` is the gate.** Do not describe the pin as protection.
- **A ceiling on a lifetime counter is not a rail, it is a ratchet.** Any new ceiling must carry its window and
  its provenance (billed vs estimated) in the same declaration.
