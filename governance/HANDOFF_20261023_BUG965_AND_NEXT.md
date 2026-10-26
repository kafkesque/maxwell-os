# HANDOFF — 2026-10-26 (T-206 · BUG-1026 ×2 · BUG-1020 · BUG-1029 · D-3155/3156/3157)

> **To continue in a fresh session: say `continue`.**
> Every number below was READ from disk or from a command's own output on 2026-10-26 between 11:07 and 12:1x UTC.
> Nothing here is remembered.
>
> **This file SUPERSEDES `governance/HANDOFF_20261023_BUG965_AND_NEXT.md`**, whose subject (BUG-965) is CLOSED
> 2026-10-23 (buglog, second heading). The older file's bytes remain in git at `54d3688`; nothing was deleted.
> The session before this one left `governance/HANDOFF_20261026_OMLX_HF_TOKEN_AND_PREFLIGHT.md`, and its §8 order is
> the list this session worked through.

---

## 1. STATE (resolved from disk)

| reading | value |
|---|---|
| certified commit | **`9e2a81b`** — "T-206 + BUG-1026 (both instances) + BUG-1020 close by measurement…" |
| ladder receipt | 194 declaring line(s), **0 fault(s)**, worst rc=0, **581.1 s**, schema 2, `state: finished`, `head_at_start == head_at_end == 9e2a81b`, **all four worktree readings EMPTY**, fingerprint `18d1b2d71f73dc70`; `--receipt-check` rc 0 |
| the commit carrying THIS file | the session tip — `git log -1 --oneline` (the ladder was re-run after it; `python3 scripts/run_ladder.py --receipt-check` re-takes the reading) |
| bugs | **OPEN 246 / CLOSED 547 of 793**, DIVERGENT 0 (`scripts/bug_status.py`) |
| decisions | **1283**, stamp `53b27463fb8e6d2c`, records-only (`recompute_decision_summary.py --check` rc 0) |
| gov faces | **GREEN** — `ok gov-sync: 4 face(s) equal their re-derivation (1283 decisions / 793 bugs / 59 open tasks)` |
| `just preflight` | **rc 0 end-to-end** (first time in this thread) |
| live session provider | **`custom_deepseek`** — session `20261026_1`, 20,515,807 accumulated tokens; every rail used to answer BOUND. Now LOUD (see §3.1) |

---

## 2. WHAT LANDED THIS SESSION (one commit: `9e2a81b`, plus the provider rail after it)

### 2.1 T-206 — CLOSED by measurement (`config/task_register.yaml`, `state: done`)

The ten C12 items a DEAD gate had been hiding (BUG-1025's consequence) are now classified ONCE, by **what fixes the
value** — the classification is the decision, `D-3156`:

| class | members | why it does not move to YAML |
|---|---|---|
| `FORMAT_SPEC_HARDCODED` | `PALMDB_MAGIC_OFFSET` 60, `PALMDB_HEADER_BYTES` 78, `PALMDB_RECORD_ENTRY_BYTES` 8, `OLE_HEADER_BYTES` 512 (`pipeline/container_integrity.py`) | a file-format fact is fixed by the format's spec, not by a config key; a tunable offset would let a config edit falsify what a `.pdb` IS |
| `ACKNOWLEDGED_HARDCODED` | `RC_FAULT` 1, `RC_OWNER_OWED` 2 (`pipeline/model_store_census.py`) | configuring an exit code configures the MEANING of a run |
| YAML | `probe_limits.tail_bytes/head_bytes` → `config/ingest_identity_gate.yaml`; `stage0.artifact.min_output_bytes` → `config/pipeline_config.yaml`; `s2.dspy_max_tokens` read through `pipeline/pipeline_paths.py` (imports without `dspy-ai`) | these are MEANING values: one home, in config |

Counted against a **shrink-only ceiling** declared at `config/pipeline_config.yaml#config_audit.unchecked_hardcoded`
(`direction: shrink_only`, `ceiling: 0`, `baseline: 9`, `measured_on: 2026-10-26`). `--strict` now ALSO fails when
`files_scanned == 0` — *an empty report from a gate that did not run is not zero*. The 4 known-answer controls are
**invoked by `just preflight` on the line immediately before the strict count** (a control nothing runs is a comment,
BUG-492). Receipts: `✅ UNCHECKED — 0 hardcoded value(s) not in the registry | unchecked 0 <= ceiling 0 (0 headroom)
scanned 122 pipeline module(s)` rc 0; `--selftest` 4/4.

**Rejected alternatives, kept so they are not re-proposed (D-3038):** folding the ten into `ACKNOWLEDGED_HARDCODED`
(a set that can absorb a finding cannot shrink, D-2644); and making a binary-format offset configurable.

### 2.2 BUG-1026 instance 1 — FIXED (`scripts/gov_sync.py`)

`gate_names_owner(gate, token)` replaces the substring test with
`re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}", gate, re.IGNORECASE)`: the owner token must BEGIN a word. `the
owner`, `owner's`, `OWNER WORD`, `owner-owed` still fire; `RC_OWNER_OWED` no longer does. One new known-answer row
asserts the NEGATIVE direction on the same fixture. `--selftest` → `30 known answers`, rc 0. **Named wrong fix, still
refused:** stripping underscores (it removes the boundary instead of reading it).

### 2.3 BUG-1026 instance 2 — FIXED (`scripts/lib/write_guard.py`)

`_receipt_path(path, *, journal)` resolves every artifact path **before the journal can record it**, and REFUSES a
journaled write whose resolution lies outside the audited tree; a fixture (`journal=False`) may still live outside.
Applied at the top of all four public writers (`write_rows`, `append_rows`, `append_lines`, `write_document`). Three
new two-sided controls; `--selftest` → `17 invariants hold`, rc 0; `pytest -q tests/test_handoff_obligation.py` → 6
passed. **Named wrong fix:** teaching `last_governed_write` to accept a path SUFFIX (it would let another repo's
`config/decisions.yaml` attribute this one).

### 2.4 BUG-1020 — CLOSED, and the measurement REVERSED its own diagnosis (`D-3155`)

Three consecutive completed **known-answer** delegate runs, three different model families, each journaled BEFORE the
call and closed only against an artifact on disk:

| journal id | model | surface | wall | artifact |
|---|---|---|---|---|
| `DJ-20261026T111018Z-adbb` | Ornith-1.5-9B-MLX-8bit | `[developer]` | 84.4 s | `temp/bug1020_probe3_result.txt` |
| `DJ-20261026T111445Z-fe35` | gemma-4-E4B-it-MLX-4bit | `[developer]` | 33.0 s | `temp/bug1020_probe4_result.txt` (253 B, sha16 `89931c37bc656765`) |
| `DJ-20261026T111518Z-79f4` | MiniCPM5-2B-MLX | `[developer]` | 35.1 s | `temp/bug1020_probe5_result.txt` (114 B, sha16 `a7ac9d01c9284199`) |

`delegate_journal.py status` → `58 row(s), 29 run(s), 0 open, 0 past budget`, rc 0.

**The finding that matters more than the closure:** the failing child ALREADY had a text reader — `developer` carries a
**shell**, and `cat` is one. The instruction named a PATH and let the child choose, so the child chose `read_image` and
a text diff reached a pixel parser. **The rail is therefore an INSTRUCTION rule, not a surface rule: a delegate
instruction that needs file CONTENT names the tool that reads it.** Two more measured defects are recorded: a
`max_turns: 3` budget recorded a CORRECT answer as a FAILURE, and a delegate handed a template line
`verdict: PASS if … otherwise FAIL` **copied the conditional verbatim** instead of evaluating it (a delegate artifact
must declare a RESULT, never a rule).

Limb 2 (“`Other` must name a cause”) is emitted by the **goose harness**, which this repo does not own; it was
**RE-SCOPED to BUG-1028** with the reason written into the BUG-1020 closure, not left for a reader to infer (D-3034).

### 2.5 BUG-1029 — FIXED, and it is the session's most consequential find

**The LIVE conversation ran on the CLOUD escalation provider while every rail read the CONFIG and answered BOUND.**
Measured, read-only, from the harness's own store:

| session | born | type | `provider_name` | accumulated tokens |
|---|---|---|---|---|
| `20261026_1` | 10:52:57 | **user** | **`custom_deepseek`** | **20,515,807** |
| `20261026_2`..`_7` | 11:07:44–11:15:20 | sub_agent | `maxwell_omlx` | 7,339–43,118 each |

In the same minutes `check_harness_homes.py` printed **5 BOUND / 0 conflicting**, and `config/engine.yaml#harnesses`
declares `goose_provider_id: maxwell_omlx`, `escalation_provider_id: custom_deepseek`, *allowed, never the active
provider, never silent (D-3023)*. Both readings were true; only one was about the machine's actual spend (C1).

**What was already there (D-3153 clause 1):** `scripts/goose_profile.py#born_sessions` already read that exact table
from its ONE declared pointer (`config/agent_context.yaml#homes.cache_ledger`), and `--check` was already a declaring
line in **both** `just health` (justfile:32) and `just preflight`. Its SELECT projected every column EXCEPT
`provider_name`. The fix is one column, one pure comparison (`session_provider_drift`), one loader
(`engine_providers`, fail-closed), and a printed verdict — `D-3157`.

**The trap, asserted as a control:** the **newest row is a SUB-AGENT** (six of them sat above the cloud user session),
so a rail that read the newest row would have answered “maxwell_omlx” for ever. The subject is the newest
`session_type == "user"` row. Six new controls; `--selftest` → **47/47**, rc 0. Live: `--check` →
`OWNER-OWED provider (D-3023): 1 reading(s) say this conversation is NOT on the declared active provider maxwell_omlx`,
rc **2** (loud, non-fatal — `justfile:32` tolerates 2, the BUG-457 convention, so it cannot cascade into a FATAL that
hides the lines after it). `--born N` now prints the provider each session is BILLED on beside the surface it was
GIVEN.

### 2.6 Governance sync (the standing rule)

`gov_sync --apply` re-derived all four faces; `--check` is GREEN. `bug_status.py` re-derived (793 ids, DIVERGENT 0);
`check_bug_status.py`, `check_buglog_coverage.py`, `check_decision_membership.py`, `check_governance_faces.py`,
`check_revoked_references.py`, `verify_handoffs.py`, `integrity_check.py --quick` (10/10), `check_repo_integrity.py`
all rc 0. `write_guard --audit` → 11/14 declared script writers guarded against a shrink-only ceiling of **3**
(rc 2 OWNER-OWED, pre-existing and declared).

---

## 3. HIDDEN CONFLICTS FOUND (each with the reading that produced it)

1. **The conversation was not sovereign while the config said it was** — §2.5. **Now visible**, still live: the
   session you are reading is billed upstream and DELEGATE-001's `reasoning_content` defect applies to it. The rail
   does not unspend it; only a NEW session started on the local provider changes the cost.
2. **`just health` does NOT run `just preflight` and does NOT run the config audit.** The 194-line certified set and
   the config audit are DISJOINT: `grep -n config_audit justfile` → line 257 (`preflight`) and 492 (`audit`), neither
   inside `health`. So the whole-set green of `9e2a81b` does **not** include the C12 count or the lint gate. This is
   the highest-value structural gap left by this session and it is a DECISION, not an edit: adding lines changes the
   certified set from 194 → 196+ and re-fingerprints every future receipt.
3. **The ladder's fingerprint hashes the LINE SET, not the line BODIES** (`run_ladder.py#line_set_fingerprint`). A
   line added INSIDE `preflight` (this session added the config-audit selftest there) does not move coverage
   `18d1b2d71f73dc70` by one character. Consequence: a change to a recipe's BODY is invisible to the coverage proof —
   it is visible only through `head_at_start/head_at_end`.
4. **BUG-1015 is still OPEN and is now measurably worse**: `just audit` pipes ruff to `tail -5`, so the exit status is
   `tail`'s; `scripts/` is linted nowhere. This session added 3 ruff findings to `pipeline/container_integrity.py`
   (UP035 `Callable`, F541 ×2) and 3 to `scripts/` (`gov_sync.py` E731/UP031 among 9, `write_guard.py` F841), and the
   audit still prints “✅ Audit complete”.
5. **BUG-957's second limb is unchanged and now directly relevant**: `~/.config/goose/custom_providers/` carries no
   `custom_deepseek.json`, so the provider this conversation actually runs on has **no `context_limit`** and no
   compaction trigger can be computed for it.
6. **`~/Library/Application Support/oMLX/config.json#hf_token`** still holds the REVOKED token `a78e54f87d15` at mode
   **644** (BUG-789 limb 3) — inert to the Python path, unrailed, owner-owned.
7. **The declared app-side rail for BUG-1027 is still NOT BUILT**: the admin settings write should REFUSE an
   `hf_endpoint` that is neither empty nor an `http(s)://` URL. Two-sided control declared: `{"hf_endpoint": "hf_…"}`
   → 400 and settings unchanged; `{"hf_endpoint": "https://hf-mirror.com"}` → 200; `""` → 200.
8. **Every register edit re-stales the four faces.** `gov_sync.py --check` goes RED until `--apply` runs; this session
   hit it twice. `--apply` is part of the LANDING ritual, not housekeeping.

---

## 4. NEXT CRITICAL STEPS, in consequential order

| # | item | why it is at this position | first command (the RED loop, D-3036) |
|---|---|---|---|
| **1** | **BUG-1015** — a lint gate that cannot fail (`just audit \| tail -5`; `scripts/` linted nowhere) | every other rail's honesty is bounded by lint, and this session added findings to it; the declared fix shape exists and is unimplemented | `python3 -m ruff check pipeline/ scripts/ \| tail -3; echo ${PIPESTATUS[0]}` — today that prints 0 |
| **2** | **§3.2** — put the config audit INSIDE the certified set (`just health`), then decide 194 → 196 | a gate outside the certified subset is a gate nobody re-reads | `grep -c "config_audit" justfile` and read where each hit lives |
| **3** | **BUG-1028** — a delegate failure reports the word `Other` | the substitute (pre-call journal row + refused `done`) is bounded, not equivalent; closure needs a cause vocabulary or a documented limit + a `--cause` slot | `grep -rn "Other" scripts/delegate_journal.py` then a failing delegate run re-read through `status` |
| **4** | **BUG-1027's declared app-side rail** — refuse a non-URL `hf_endpoint` | would have caught the 51-minute outage at 10:46 instead of 11:29 | POST the three declared controls at `/admin/api/global-settings` |
| **5** | **T-202** (gpt-oss-20b enum falsifier before any tools payload), **T-204** (the receipt message should name BOTH heads, never gate), **BUG-1021** (one receipt home, two recipes), **T-203** (a prose table may not restate a hub count) | the honesty of the instruments themselves | each has its own declared control; start from the task register `gate:` |
| **6** | **T-101 / T-116** — the retrieval golden set is saturated at recall@10 = 1.000; T-116 is the growth instrument | a saturated set measures nothing; this is a CONTENT problem, larger than a rail | `python3 scripts/check_extraction_recall.py` |
| **7** | housekeeping, folded into #1: 3 ruff findings in `pipeline/container_integrity.py`, 3 in `scripts/`, the pre-existing F841 in `write_guard.py`'s selftest | they are the baseline the ceiling in #1 must name | `python3 -m ruff check pipeline/container_integrity.py scripts/lib/write_guard.py` |

**Do NOT re-derive any of these fixed shapes** (they are recorded so no session re-derives them): the boundary-regex
gate rule (§2.2), `_receipt_path` (§2.3), the three hardcode classes (§2.1), the delegate-instruction rule (§2.4), the
newest-USER-session subject (§2.5).

---

## 5. MANUAL STEPS (owner-side, D-3100 — exact command, exact expected output, and the branch if it differs)

**5.1 Make the next session LOCAL (optional, but this conversation is billed upstream).**
The harness config ALREADY names the local provider as active, so there is nothing to edit:

1. Check the declaration: `grep -n "goose_provider_id\|active_provider" config/engine.yaml ~/.config/goose/config.yaml`
   → expect `goose_provider_id: maxwell_omlx` and `active_provider: maxwell_omlx`.
2. **Start a NEW session** (a config write is never live inside a running session — AGENTS.md harness fact). Do not
   resume this one; a resumed session keeps the provider it was born with.
3. In the new session run: `python3 scripts/goose_profile.py --check`
   - **expected:** `ok provider: the newest USER session was born on maxwell_omlx, the declared active provider (D-3023)`
   - **if instead it prints** `OWNER-OWED provider (D-3023): … born on the ESCALATION provider …` → the new session was
     ALSO born off-route: re-read `~/.config/goose/config.yaml#active_provider`; if that says `maxwell_omlx`, the
     session was started with a provider override (desktop app picker) → choose the `maxwell_omlx` entry in the
     provider selector and start again.

**5.2 The revoked HF token in the app's own config (BUG-789 limb 3).** In the oMLX app there is **no token field** (the
complete settings surface is `huggingface.endpoint` / `endpoint_hint` / `endpoint_clear_hint`), so this is a file act,
not an app act: `ls -l "$HOME/Library/Application Support/oMLX/config.json"` → expect mode `644` and a `hf_token` field
holding `a78e54f…`. **Do not paste any token into “Mirror Endpoint”** — that is exactly BUG-1027. Leave the field alone
until a rail refuses a secret-shaped literal in an app config, or delete the `hf_token` key with the app closed.

**5.3 If `just health` ever stops at line 1 with `the worktree is dirty`** — that is the ruled shape, not a bug: commit
first (`python3 scripts/check_commit_frontier.py` names what it wants committed), then re-run.

---

## 6. CONTINUE HERE (paste this block into a fresh session)

```
Continue Maxwell OS 2.0. Read governance/HANDOFF_20261023_BUG965_AND_NEXT.md (2026-10-26 revision) first.
State: certified GREEN at 9e2a81b (194 lines, 0 faults, 581.1 s, worktree empty at both ends); gov faces GREEN
(1283 decisions / 793 bugs / 59 open tasks); just preflight rc 0. This session closed T-206, BUG-1026 (both
instances), BUG-1020 and BUG-1029, and minted D-3155, D-3156, D-3157.
Next, in this order: (1) BUG-1015 — the lint gate that cannot fail; (2) put the config audit INSIDE `just health`;
(3) BUG-1028 — a delegate failure reports the word `Other`; (4) BUG-1027's declared app-side hf_endpoint rail.
Do the forensic audit first (the handoff's §3 lists the eight hidden conflicts), delegate implementation to the
right LOCAL models per D-3155 (name the tool in every instruction; never a conditional in an artifact template),
then re-sync gov faces with `python3 scripts/gov_sync.py --apply` and certify with a FOREGROUND
`python3 scripts/run_ladder.py --collect health`.
```

---

## 7. FILES THIS SESSION TOUCHED

`pipeline/config_audit.py` · `pipeline/container_integrity.py` · `pipeline/dspy_trainer.py` ·
`pipeline/pipeline_paths.py` · `pipeline/stage0_convert.py` · `scripts/gov_sync.py` · `scripts/goose_profile.py` ·
`scripts/lib/write_guard.py` · `justfile` · `config/ingest_identity_gate.yaml` · `config/pipeline_config.yaml` ·
`config/task_register.yaml` · `config/decisions.yaml` (+ `config/decisions_summary.json`) · `governance/buglog.md` ·
`governance/bug_status.json|md` · `MASTER-TASK-REGISTER.md` · `DECISION-LOG.md` · `agent/session_seed.yaml` ·
`governance/MUTATION_JOURNAL.jsonl` · `governance/delegate_journal.jsonl` · this file.

Every governed write above went through `scripts/lib/write_guard.py` (receipted in
`governance/MUTATION_JOURNAL.jsonl`); the delegate runs are receipted in `governance/delegate_journal.jsonl` with the
wall time measured from the journal's own two rows.
