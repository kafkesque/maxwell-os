#!/usr/bin/env python3
"""plan_quality_fixture.py — the PLANNING instrument BUG-1055 said did not exist.

WHY THIS FILE EXISTS (measured, 2026-10-27)
-------------------------------------------
`config/hardware_profile.yaml` ranks every role by speed: `plan: {objective: decode_tps}`,
`analyze: {objective: prefill_tps}`. Four of the six roles carry `require_gate: null`, so
"the best planner" operationally meant "the FASTEST model that DECLARES the plan role" — and
nothing in the OS had ever asked a model to plan anything. BUG-1055 named that as the defect:
a role whose only arbiter is a stopwatch cannot tell a planner from a fast talker.

The `review` role already has the shape this file copies: a balanced fixture, a declared
constant-answer baseline, and thresholds enforced mechanically against a journal artifact
(`config/r5_review_gate.yaml#bench`, `governance/r5_review_gate_bench.jsonl`). This module is
that same instrument pointed at PLANNING, not a new framework (D-3189 limb b).

WHAT AN ITEM IS (the T-187 shape)
---------------------------------
Each item is a PLANNING DECISION, never a knowledge question:

    MATERIAL          the only evidence the planner may use (a measured table, a rail verdict,
                      a config excerpt, a rule, a register row)
    PROPOSED NEXT STEP  one step, as it would actually be written into the plan
    gold              APPROVE — every claim it makes is SUPPORTED by the MATERIAL and its ORDER
                                is correct given the dependencies the MATERIAL states
                      REJECT  — it asserts something the MATERIAL contradicts, skips a declared
                                dependency, violates a declared rule, or claims a result it
                                cannot have verified

The answer must SURVIVE REASONING OVER THE MATERIAL: the numbers a wrong step quotes are drawn
from the material itself (so a proposal that pattern-matches "looks reasonable" and quotes a
plausible figure fails), and several APPROVE items read suspicious at first glance. This is why
a keyword matcher cannot score much above the constant-answer baseline, and why the baseline is
the correct comparator.

DESIGN RULES (each one inherited, none invented)
------------------------------------------------
* DETERMINISTIC GROUND TRUTH. Gold is written by the item author. No LLM judge anywhere in the
  grading path, so the grader cannot drift.
* NO SECOND PARSER. The verdict is parsed by `scripts/r5_code_review.extract_verdict`, the
  production parser, imported lazily (it imports model_eval_suite.call at module scope).
* BALANCED 12/12, so the constant-answer baseline is exactly 0.5000 and no prior can beat it.
* ONTOLOGICALLY ALIGNED. Every seeded flaw is one this OS actually commits or nearly committed:
  the symlink double count (BUG-1050), the weights-only fit claim (BUG-1055), a hardcoded figure
  beside a config value (BUG-1062), promotion on speed alone (BUG-1055), minting a decision
  before the census (D-2660 gate), a gate lookup keyed by model so one gate satisfies another
  (BUG-1063), an extension flag read as birth proof (BUG-873), a fixture-version pool
  (D-3167/D-3168), absence read as a pass, a journal written after the run (D-3036), and a
  "delete the symlinks to reclaim the bytes" half-delete (BUG-1050/D-3188).

VERSIONING (v1 -> v2, 2026-10-27). v1's items carried `pq1-*` ids and v2's carry `pq2-*`, built from ONE
constant (VERSION). The gate counts only the CURRENT ids, so the bump re-points it automatically and an old
row can never be pooled in. v1 was retired the day it was built, for the MEASURED reason recorded beside
VERSION: a reasoning model's unclosed JSON was being scored as a planning failure.

WHAT IS MEASURED (identical vocabulary to the reviewer gate, so one enforcement function reads it)
-------------------------------------------------------------------------------------------------
`acc`            exact gold match out of 24
`false_approve`  share of REJECT-gold steps answered APPROVE — the DANGEROUS error: a flawed step
                 that gets committed
`false_reject`   share of APPROVE-gold steps answered REJECT — the over-block rate
`unparsed`       share of rows with no parseable verdict JSON (BUG-738's truncation mode)
"""
from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO: Path = Path(__file__).resolve().parents[1]
_CONFIG: Path = REPO / "config" / "plan_quality_gate.yaml"

# Fallback only: the declared budget in config/plan_quality_gate.yaml wins whenever it exists.
_DEFAULT_MAX_TOKENS: int = 900

# THE FIXTURE VERSION. Item ids are built as VERSION + '-' + the case's own name, so one constant re-points the
# gate (the gate counts only the CURRENT ids - the rvv2 -> rvv3 precedent).
#   pq1 (retired 2026-10-27, the day it was built): the system prompt said "Reply with JSON only" and a reasoning
#       model (Ornith-1.5-35B-A3B-REAP-19B) answered with an UNCLOSED object - 189 characters, 626 of its 726
#       completion tokens spent on reasoning - and produced the IDENTICAL truncation at max_tokens 900 and 1600, so
#       the budget was NOT the cause. The production parser refuses to invent a verdict (correctly), so v1 scored a
#       FORMAT HABIT as a planning failure: the BUG-262 shape, and a defect of the INSTRUMENT, not of the model.
#   pq2 (current): the prompt states the contract explicitly - the JSON object comes FIRST and is never left
#       unclosed - after which the same call returned a complete, parseable verdict.
VERSION: str = "pq2"


def _gate_config() -> dict[str, Any]:
    """Load the plan-gate config, fail-closed (a missing gate must never pass silently, C16)."""
    import yaml  # local import: the harness must import even where yaml is absent

    if not _CONFIG.is_file():
        raise RuntimeError("plan_quality fixture: gate config missing at " + str(_CONFIG))
    with _CONFIG.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _plan_task() -> str:
    """Return the planner question DECLARED by the gate, so the fixture cannot drift from it."""
    task = str(_gate_config().get("task") or "").strip()
    if not task:
        raise RuntimeError("plan_quality fixture: config declares no 'task' for the planner")
    return task


def _plan_budget() -> int:
    """Return the declared output budget (a truncated verdict is scored as a model failure)."""
    return int(_gate_config().get("max_tokens") or _DEFAULT_MAX_TOKENS)


SYSTEM: str = (
    "You judge a PROPOSED NEXT STEP against supplied evidence and decide whether it may be committed. "
    "Use ONLY the MATERIAL provided; never assume facts it does not state. "
    "Approve only when the step's claims are supported AND its order respects every dependency the "
    "material states. Reject when it contradicts the material, skips a dependency, breaks a stated rule, "
    "or claims a result it could not have verified. If the material truly cannot decide it, answer "
    "INSUFFICIENT. "
    "Reply with a single COMPLETE JSON object as the FIRST characters of your reply - no narration "
    "before it, and never leave the object unclosed (a truncated object cannot be parsed and scores as "
    "no answer): {\"verdict\": \"APPROVE\" or \"REJECT\" or \"INSUFFICIENT\", "
    "\"reason\": \"one sentence citing the material\", \"confidence\": 0.0-1.0}"
)

# ---------------------------------------------------------------------------------------------
# REJECT-GOLD (12). Every one is a step this OS has actually taken, proposed again.
# ---------------------------------------------------------------------------------------------
REJECT_CASES: list[dict[str, str]] = [
    {
        "id": "delete-base-first",
        "name": "delete the base, keep the farm for later",
        "why": "order inverted: the farm's payload IS the base, and the farm is advertised; the rail refuses this for two independent axes.",
        "material": (
            "MEASURED (du -sh, never -L): base ~/.omlx/models/Qwen3.8-27B-MLX-4bit = 15.0G (its own inodes 16,081,501,977 B);\n"
            "farm ~/.omlx/models_staged/Qwen3.8-27B-MTP4 = 228M of its OWN bytes (239,146,670 B), and its remaining\n"
            "entries are 13 SYMLINKS resolving INTO the base (model-00001..3-of-00003.safetensors, tokenizer.json,\n"
            "tokenizer_config.json, ...); _heads = 456M (477,868,591 B).\n"
            "RAIL (read-only, four axes): check_delete_target reports SERVED (a loadable entry in ~/.omlx/models resolves\n"
            "into the base), SYMLINK-REFERENCED (13 referrers under models_staged/Qwen3.8-27B-MTP4) and ADVERTISED\n"
            "(engine id Qwen3.8-27B-MLX-4bit) -> verdict REFUSE (exit 2).\n"
            "REGISTER: the base declares roles: [] and its why: reads \"kept as the control, not as a production brain\";\n"
            "it is the reference arm of a MEASURED 1.54x decode claim. The farm IS the plan/analyze candidate."
        ),
        "proposal": (
            "Step 1: delete ~/.omlx/models/Qwen3.8-27B-MLX-4bit now (15.0G reclaimed).\n"
            "Step 2: delete the farm and _heads next week; the farm is only 228M so it is not urgent."
        ),
    },
    {
        "id": "weights-fit-is-working-set",
        "name": "run plan and analyze concurrently because the weights fit",
        "why": "the fit figure is a WEIGHTS-ONLY sum and the KV working set at the declared 131072 context is not modelled at all.",
        "material": (
            "REPORT: RESIDENCY 40.0 GiB of 43.0 usable - \"the WEIGHTS of all assigned models fit at once (KV excluded)\".\n"
            "The 40.0 GiB is the sum of each assigned model's weight file size. 43.0 = 57.5 budget x 0.80 - 3.0.\n"
            "CONFIG: memory.kv_headroom_gb = 3.0 with memory.kv_headroom_ctx = null (the flat reserve declares NO context\n"
            "basis). roles.plan.min_ctx = 131072 and roles.analyze.min_ctx = 131072.\n"
            "KV line printed by the report: \"NOT MODELLED: KV is a 3.0 GiB flat reserve that declares NO context basis,\n"
            "so no role is covered by it; highest declared min_ctx 131072 tokens - analyze, plan (BUG-1055)\"."
        ),
        "proposal": (
            "Because 40.0 GiB of 43.0 is already established, run the plan call and the analyze call concurrently in one\n"
            "pass at their declared 131072 contexts; the headroom covers the difference."
        ),
    },
    {
        "id": "du-L-double-count",
        "name": "reclaim about 30.2 GB by deleting the pair",
        "why": "the 30.2 GB figure is the symlink farm counted twice (du -shL artefact, BUG-1050); real bytes are 15.6 GiB.",
        "material": (
            "MEASURED sizes: base 15.0G; farm 228M (its own bytes); _heads 456M.\n"
            "The farm counted WITH its symlink targets is 16,320,425,434 B (15.2G) - that count follows the links.\n"
            "Distinct (device, inode) totals for the three: 16,081,501,977 + 239,146,670 + 477,868,591 = 16,798,517,238 B.\n"
            "df -h / before: 121Gi avail."
        ),
        "proposal": (
            "Deleting the set reclaims roughly 30.2 GB (15.0G for the base plus 15.2G for the farm), which is worth doing\n"
            "today; verify afterwards with du -shL on the parent directory."
        ),
    },
    {
        "id": "literals-are-fine-today",
        "name": "leave the hardcoded figure because it agrees with config",
        "why": "agreement today is not a resolution (D-3034/C12): the literal and the config are two declarations of one fact with nothing joining them.",
        "material": (
            "CONFIG memory: max_resident_fraction: 0.80, kv_headroom_gb: 3.0.\n"
            "CODE site A (main/report path): usable = round(budget_gb * cfg[\"memory\"][\"max_resident_fraction\"]\n"
            "  - cfg[\"memory\"][\"kv_headroom_gb\"], 1)\n"
            "CODE site B (render path): usable = round(budget_gb * 0.8 - 3.0, 1)\n"
            "Live budget_gb = 57.5, so both sites print 43.0 today. C12 requires that if a value CAN be configurable it\n"
            "MUST come from config, and C12d requires scanning for hardcoded values before accepting output."
        ),
        "proposal": (
            "Leave site B as literals: the two sites print the same 43.0 today, so the figure is correct and the change\n"
            "would be cosmetic churn."
        ),
    },
    {
        "id": "fastest-declaring-wins",
        "name": "assign plan to the faster of the two candidates",
        "why": "with require_gate null, 'the best planner' collapses to 'the fastest model that declares plan' - BUG-1055 itself.",
        "material": (
            "ROLES: plan: {objective: decode_tps, require_gate: null, min_ctx: 131072}; analyze: {objective: prefill_tps,\n"
            "require_gate: null, min_ctx: 131072}. Only `review` names a gate (r5_review).\n"
            "CANDIDATES declaring plan: A = MTP4 (decoded 16.98 t/s on one checkpoint and 12.34 on another, median of\n"
            "3 readings) and B = Ornith-1.5-35B-A3B-REAP-19B. No planning task has ever been run against either.\n"
            "RESOLVER RULE (as written): a candidate may only take a role it DECLARES; the pool is sorted by the role's\n"
            "objective and the top value wins."
        ),
        "proposal": (
            "Assign `plan` to A because its measured decode is higher than B's and both declare the role; no further\n"
            "evidence is required, since decode speed is the declared objective for this role."
        ),
    },
    {
        "id": "mint-before-census",
        "name": "commit the new decision and let the nightly job fix the census",
        "why": "the census gate compares declared vs actual and fails at commit time; there is no nightly job, so the claim is false as well as mistimed.",
        "material": (
            "GATE (scripts/recompute_decision_summary.py): after appending a record, config/decisions_summary.json goes\n"
            "stale; the gate prints \"declared 1315, actual 1316\" and \"decisions_sha256_16: declared 2412c9f2c1c0b118,\n"
            "actual <new>\" and refuses the commit until the census is re-derived from the bytes on disk.\n"
            "The census is written BY that same script (write_census), with backup and journal. No scheduled job in this\n"
            "repo re-derives it; `just health` only runs the gates."
        ),
        "proposal": (
            "Append the new decision record and commit now; the census still declares 1315 records, and the nightly\n"
            "governance job will regenerate it from the appended bytes."
        ),
    },
    {
        "id": "config-flag-as-birth-proof",
        "name": "conclude the subagent had the tool because the flag is true",
        "why": "a subagent's named extensions are FILTERED by the config flag at birth, and a session born earlier carries no such key at all.",
        "material": (
            "MEASURED 2026-10-17: a delegate given extensions [\"developer\",\"filesystem\"] while filesystem was\n"
            "enabled: false in the config was born with `developer` ALONE (session 20261017_15); the same call given\n"
            "[\"analyze\",\"memory\"] while both were enabled was born with exactly those two (20261017_16).\n"
            "The birth record lives in sessions.db under enabled_extensions.v0; session 20261012_1 (still being written\n"
            "on 2026-10-16) has NO such key and must be reported NOT RECORDED, never \"absent\".\n"
            "A dead extension reports to the TERMINAL, never to the session."
        ),
        "proposal": (
            "The config shows filesystem: enabled: true and the delegate's profile named it, so conclude that the\n"
            "delegate ran with the filesystem tool and that its file report is trustworthy."
        ),
    },
    {
        "id": "delete-while-loaded",
        "name": "delete the served directory now and reload afterwards",
        "why": "the model is resident and advertised; the bytes are in use, and a reload cannot repair a directory removed beneath a running model.",
        "material": (
            "ENGINE: GET /v1/models lists 17 ids including `Qwen3.8-27B-MTP4`; ~/.omlx/model_settings.json carries a key for\n"
            "it, and the engine's own pool was last told to preload it. A reload (POST /admin/api/reload) re-reads\n"
            "model_settings.json and re-discovers ids from the effective directories; it does NOT restore deleted files.\n"
            "RAIL: a candidate is SERVED when a loadable model-root entry resolves into it; ADVERTISED when the engine\n"
            "lists its id. Either axis returns REFUSE (exit 2) - the rail is read-only and the delete stays an owner act.\n"
            "REGISTER: 17 ids advertised, 14 model_settings keys."
        ),
        "proposal": (
            "Delete the model directory now to free the disk immediately, then call the engine reload so the id\n"
            "disappears; the reload cleans up the leftovers."
        ),
    },
    {
        "id": "pool-fixture-versions",
        "name": "pool two fixture versions to reach min_n",
        "why": "rvv2 and rvv3 are different fixtures (the scoped-clause change flipped results); pooling measures neither and the gate filters by current ids for exactly this reason.",
        "material": (
            "RECEIPT rows for one model: rvv2 fixture -> acc 0.6250, margin +0.1250, false_approve 0.0421 (n=24);\n"
            "rvv3 fixture -> acc 0.9167, margin +0.4167, false_approve 0.0000 (n=24). Thresholds: min_n 20,\n"
            "min_margin_over_baseline 0.15, false_approve_ceiling 0.10.\n"
            "D-3167/D-3168: v2 scoped \"verify its own work\" to world-acting scripts; that single clause change flipped the\n"
            "model from serial-rejector to passing reviewer. The gate resolves the CURRENT fixture's ids only."
        ),
        "proposal": (
            "Pool the rvv2 and rvv3 rows for this model into n=48 so the sample is larger and sturdier, then use the pooled\n"
            "accuracy to promote it."
        ),
    },
    {
        "id": "absence-read-as-pass",
        "name": "treat a missing failure record as a pass",
        "why": "absence is not a measurement; the resolver is fail-closed and a role naming a gate may only be filled by a row that RESOLVES to pass.",
        "material": (
            "ROLE: analyze: {objective: prefill_tps, require_gate: plan_quality, min_ctx: 131072}.\n"
            "RECEIPTS: governance/plan_quality_gate_bench.jsonl exists and contains rows for two OTHER models only; there\n"
            "is no row for the candidate in question, and governance/model_eval_checkpoint.jsonl has no plan_quality rows\n"
            "for it either.\n"
            "RESOLVER (fail-closed): `if need_gate and row[\"gate\"] is not True: continue` - a model with no gate row\n"
            "cannot enter the pool for a gated role."
        ),
        "proposal": (
            "Since no plan_quality failure is recorded for this candidate, mark its gate as passed and assign it the\n"
            "analyze role; the sample can be taken later."
        ),
    },
    {
        "id": "journal-after-the-run",
        "name": "declare the detached run after it finishes",
        "why": "the journal's whole purpose is the declaration BEFORE the call; an artifact claimed but absent is a NAMED fault, and an undeclared run leaves no record.",
        "material": (
            "RULE (D-3036 / BUG-844): a delegated or detached run declares its budget, purpose and the exact files it MAY\n"
            "write BEFORE it starts (scripts/delegate_journal.py start --purpose ... --may-write ... --budget-s N) and is\n"
            "closed with end --id <id> --state <done|failed|cancelled> --artifact <path>. `status` names every open run\n"
            "past its budget (rc 2). A `done` whose artifact is absent is REFUSED rather than recorded."
        ),
        "proposal": (
            "Start the 40-minute benchmark detached in the background now, and write its journal entry (purpose, budget,\n"
            "allowed writes) once it has finished, so the record reflects the real duration."
        ),
    },
    {
        "id": "delete-the-symlinks",
        "name": "reclaim the farm's 15.2 GB by deleting its links",
        "why": "the links carry no bytes; the bytes are the base, so this reclaims ~0 and breaks the advertised farm.",
        "material": (
            "MEASURED: the farm's own bytes are 239,146,670 B (228M); the remaining 16.08 GB counted under it are SYMLINKS\n"
            "resolving INTO the base (a count that follows links reports 16,320,425,434 B for the farm).\n"
            "Symlinks consume only their own inode (a few hundred bytes each). The farm is the register's plan/analyze\n"
            "candidate and its id is advertised by the engine."
        ),
        "proposal": (
            "Keep the base directory and delete only the farm's symlinked safetensors files: that reclaims the farm's\n"
            "15.2 GB of counted size while leaving the control arm intact."
        ),
    },
]

# ---------------------------------------------------------------------------------------------
# APPROVE-GOLD (12). Several read suspicious at first glance; approving blindly is as wrong as
# rejecting blindly, which is why the fixture is balanced.
# ---------------------------------------------------------------------------------------------
APPROVE_CASES: list[dict[str, str]] = [
    {
        "id": "reload-before-citing",
        "name": "reload the engine, then cite the id only if the engine lists it",
        "why": "discovery is the engine's own act: a completed download is not an id until a reload re-discovers it.",
        "material": (
            "MEASURED: a completed HF-cache download did NOT appear in GET /v1/models (16 ids, without the new model) even\n"
            "though its directory was on disk. POST /admin/api/reload answered {\"status\":\"ok\",\"message\":\"Re-discovered\n"
            "17 models from 2 directories\"}, after which the new id appeared. The in-process pool never re-checks the\n"
            "filesystem on its own (BUG-1057 shape)."
        ),
        "proposal": (
            "Step 1: call POST /admin/api/reload. Step 2: re-read GET /v1/models. Step 3: cite the model id as servable\n"
            "only after it appears in that list; if it is still absent, report the id as NOT SERVED rather than assume it."
        ),
    },
    {
        "id": "rail-then-owner-act",
        "name": "read the rail's verdict, then perform the delete as an owner act with df receipts",
        "why": "the rail is read-only by design; the delete is a separate, receipted act and df before/after is the only honest measure of what was freed.",
        "material": (
            "RAIL: scripts/check_delete_target.py is READ-ONLY (it never deletes). Exit codes: 0 SAFE_TO_DELETE, 2 REFUSE,\n"
            "3 UNDETERMINED (engine unreachable, fail-closed), 4 USAGE/SETUP. Verdicts printed as a VERDICT line, and the\n"
            "rail's own code is propagated. Deletion is `pipeline/safe_delete.py` under owner control.\n"
            "BUG-1058: a tool's own 'freed N bytes' line is not a receipt; the receipt is df -h before/after plus a\n"
            "per-repo du -sh."
        ),
        "proposal": (
            "Step 1: run the rail and read its verdict. Step 2: only if it is SAFE_TO_DELETE, delete via safe_delete.py.\n"
            "Step 3: record df -h before and after plus du -sh of the parent as the receipt - never the tool's own\n"
            "reported byte count."
        ),
    },
    {
        "id": "append-then-rederive",
        "name": "append the record, re-derive the census, then commit",
        "why": "the census describes the bytes on disk; the gate requires the re-derivation in the same sitting.",
        "material": (
            "GATE: scripts/recompute_decision_summary.py prints declared-vs-actual (total_decisions and\n"
            "decisions_sha256_16) and refuses while they disagree. Re-running it writes the census with a NEW stamp and a\n"
            "source_sha256 taken from the bytes on disk.\n"
            "MEASURED this sitting: 1315 -> 1316 records moved the stamp 2412c9f2c1c0b118 -> 30692892469e189e.\n"
            "A state transition is a governed write with the same obligation (D-3035/M2)."
        ),
        "proposal": (
            "Step 1: append the record (fsync). Step 2: run the census re-derivation so the summary describes the new\n"
            "bytes. Step 3: commit, and record the new stamp in the commit message."
        ),
    },
    {
        "id": "gate-the-role",
        "name": "build a planning fixture and let the resolver gate the ROLE",
        "why": "gating the role reuses an instrument shape that already works and leaves the ranking code untouched.",
        "material": (
            "FACTS: 4 of 6 roles declare require_gate: null; `review` declares r5_review and is filled only by a row that\n"
            "RESOLVES to pass. That gate's shape: a balanced fixture (24 items, 12/12), a constant-answer baseline\n"
            "(0.5000), thresholds min_n 20 / min_margin_over_baseline 0.15 / false_approve_ceiling 0.10, enforced against\n"
            "a journal artifact, with the resolver's existing fail-closed path doing the exclusion.\n"
            "BUG-1055's other limb: the flat 3.0 GiB KV reserve declares no context basis."
        ),
        "proposal": (
            "Step 1: add a balanced planning fixture of the same shape and enforce the same thresholds against its own\n"
            "receipt. Step 2: have plan and analyze declare require_gate: plan_quality. Step 3: let the existing\n"
            "fail-closed pool exclusion remove every non-passing model - no new ranking code, and a model with no row is\n"
            "simply not eligible."
        ),
    },
    {
        "id": "disclose-then-measure",
        "name": "print the reserve as NOT MODELLED, then measure it",
        "why": "disclosure is cheap and correct; the receipt is the only thing that may replace the flat reserve.",
        "material": (
            "CONFIG: memory.kv_headroom_gb 3.0, memory.kv_headroom_ctx null. Roles at the ceiling: analyze, plan\n"
            "(min_ctx 131072). RESIDENCY prints a WEIGHTS-ONLY sum and must say so.\n"
            "MEASURED 2026-10-27: no KV formula was accepted because 4 of 6 candidates answer nothing at top level (the\n"
            "geometry nests under text_config) and three families need three different rules (layer_types +\n"
            "full_attention_interval; num_global_key_value_heads + num_kv_shared_layers + sliding_window; alternating\n"
            "sliding windows). Accepted negative (D-3038)."
        ),
        "proposal": (
            "Step 1: make the report print the KV line as NOT MODELLED, naming the roles at the declared ceiling, so no\n"
            "reader can mistake the weights sum for a working set. Step 2: obtain a receipt - load the plan model with a\n"
            "full-context request and read the engine's current_model_memory - and only then replace the flat reserve."
        ),
    },
    {
        "id": "different-family-review",
        "name": "have another model family review the changed files and journal the digest",
        "why": "generator != verifier is the R5 discipline; the digest is what makes the verdict resolvable later.",
        "material": (
            "RULE (C8/R5): the generator and the verifier must be different model families. The verdict journal is\n"
            "governance/r5_reviews.jsonl, keyed by sha256_16 of the reviewed file.\n"
            "MEASURED this sitting: gemma-4-E4B-it-MLX-4bit reviewed two rails written by a Qwen-family generator and\n"
            "returned APPROVE with digests b4a583dd9168c253 and 8c4474abd4238160; each APPROVE cites one named concern\n"
            "it checked, and neither file was written by it."
        ),
        "proposal": (
            "Step 1: send the changed files to a model of a different family. Step 2: append the verdict to\n"
            "governance/r5_reviews.jsonl with the file's sha256_16 so the review resolves to exact bytes."
        ),
    },
    {
        "id": "correct-by-new-record",
        "name": "restate the wrong figure in a new record, leave the old bytes intact",
        "why": "the register is a ledger; a correction is a citable new record naming what it supersedes, not a rewrite of a minted one.",
        "material": (
            "FACTS: D-3185 section 6 states \"~30.2 GB\" for the pair; the measured figure is 15.6 GiB. D-3185 is minted,\n"
            "committed and cited by later records. The register is records-only (D-2655) and its census digest is taken\n"
            "over the RECORDS, so any change moves the stamp.\n"
            "PRECEDENT: a state transition is done through the governed route (--set-state <id> <STATE> --because <id>),\n"
            "and supersession is recorded with superseded_by rather than by deleting the earlier text."
        ),
        "proposal": (
            "Append a new decision that (a) restates the measured 15.6 GiB with its readings, (b) names D-3185 section 6\n"
            "as superseded ON THAT FIGURE ONLY, and (c) leaves the earlier record's bytes untouched; then re-derive the\n"
            "census and commit."
        ),
    },
    {
        "id": "measure-the-reference",
        "name": "record the vendor number as CLAIMED and measure the reference on this host",
        "why": "a vendor or aggregator rate is a hypothesis; evidence is a device-matched receipt with runtime and quant named.",
        "material": (
            "RULE (D-3161): every research answer names the best MEASURED implementation of the capability on comparable\n"
            "hardware, with runtime and quant, and states what THIS stack measures against it. A number read off a vendor\n"
            "page or a README is a HYPOTHESIS, never evidence.\n"
            "OURS: 34.5 tok/s decode from a two-tool probe on this host (runtime mlx_lm, 4-bit, model resident).\n"
            "CLAIMED elsewhere: a faster runtime at the same quant."
        ),
        "proposal": (
            "Step 1: record the competitor rate as CLAIMED with its source. Step 2: run its runtime on this host at the same\n"
            "quant and context. Step 3: publish both cells in one row - ours measured, theirs measured - and name which\n"
            "cell is claimed and which is measured."
        ),
    },
    {
        "id": "refuse-is-a-verdict",
        "name": "print the verdict and propagate the rail's own exit code",
        "why": "a deliberate REFUSE must not be rendered as a crash; the exit code is the contract and must survive the wrapper.",
        "material": (
            "FACTS: `just` renders ANY non-zero recipe as \"error: Recipe ... failed on line N with exit code M\" and exits\n"
            "101; only a recipe declared [no-exit-message] with a body that re-exits the rail's own code preserves it.\n"
            "The rail's codes: 0 SAFE_TO_DELETE, 2 REFUSE (the gate working), 3 UNDETERMINED (fail-closed), 4 USAGE.\n"
            "MEASURED: the owner saw \"error: ... exit code 2\" for a CORRECT refusal and could not tell it from a crash."
        ),
        "proposal": (
            "Declare the recipe [no-exit-message], print one VERDICT line per code (2 = the GATE, not a failure), and exit\n"
            "with the rail's own code unchanged so the caller can act on it."
        ),
    },
    {
        "id": "pin-the-interpreter",
        "name": "resolve the interpreter and fail with the command to run",
        "why": "the wrong interpreter makes a config-reading rail die with a traceback, which is indistinguishable from a bug in the rail.",
        "material": (
            "MEASURED on this host: `command -v python3` -> /usr/bin/python3, which has NO PyYAML\n"
            "(ModuleNotFoundError: No module named 'yaml'), so scripts/check_delete_target.py died at `import yaml`.\n"
            "The repo interpreter is the one resolved by `sh scripts/resolve_python.sh --dir` (yaml 6.0.2, Python 3.13.12),\n"
            "and the justfile exports it on PATH (BUG-1000).\n"
            "Exit vocabulary in use: 4 = USAGE/SETUP."
        ),
        "proposal": (
            "Step 1: resolve the interpreter through the repo's resolver rather than the ambient python3. Step 2: guard the\n"
            "yaml import so a missing dependency prints the interpreter, the reason and the exact command to run, and exits\n"
            "4 - never a traceback (C16: loud, and not silent either)."
        ),
    },
    {
        "id": "name-the-blocker",
        "name": "record the PASS but name the open blockers instead of promoting",
        "why": "a bench PASS is a measurement of one axis; promotion is gated by other open defects, and naming them is what keeps a later reader from promoting on this receipt alone.",
        "material": (
            "MEASURED: a candidate returned PASS n=24 acc=0.7083 margin=+0.208 false_approve=0.0 false_reject=0.25\n"
            "unparsed=1 on the reviewer bench, against an incumbent at acc 0.9167 / false_approve 0.0.\n"
            "OPEN: BUG-1048 (R5 review coverage silently depends on file length) and BUG-1041 (no re-measure channel;\n"
            "tag-blind _done_keys) both block every second-reviewer change.\n"
            "PRECEDENT: `status` in the resolver output is QUALIFIED only when a gate row RESOLVES to pass."
        ),
        "proposal": (
            "Record the PASS in the bench receipt with its n and rates, state plainly that it does NOT displace the\n"
            "incumbent (0.9167 vs 0.7083), and cite BUG-1048 and BUG-1041 as the open blockers so no reader can promote on\n"
            "this receipt alone."
        ),
    },
    {
        "id": "one-derivation",
        "name": "derive the figure once from config and prove the output did not move",
        "why": "a single derivation removes the two-declaration defect, and the diff against a baseline is what proves the refactor changed no number.",
        "material": (
            "FACTS: site A derives the usable budget from config (max_resident_fraction 0.80, kv_headroom_gb 3.0); site B\n"
            "hardcodes * 0.8 - 3.0. They agree today at budget 57.5 -> 43.0.\n"
            "The report also prints RESIDENCY 40.0 GiB of 43.0 usable, disk_free_gb and a candidates table.\n"
            "RULE (C12): one fact, one resolution; a value that merely MENTIONS a threshold declares nothing (D-3034)."
        ),
        "proposal": (
            "Step 1: extract one function that derives the figure from config and call it from every site. Step 2: run the\n"
            "report before and after and diff the output, expecting only the intended wording change (a live disk_free\n"
            "reading may differ); reject the change if any number moves."
        ),
    },
]


def _prompt(case: dict[str, str], task: str) -> str:
    """Build the planner prompt: the declared question, then the material, then the proposed step."""
    return (
        "Planner question: " + task + chr(10) + chr(10)
        + "MATERIAL (the only evidence you may use; it is measured, not hypothetical):" + chr(10)
        + case["material"] + chr(10) + chr(10)
        + "PROPOSED NEXT STEP (" + case["name"] + "):" + chr(10)
        + case["proposal"] + chr(10) + chr(10)
        + "May this step be COMMITTED as the next step of the work? Answer APPROVE only if its claims are supported by\n"
        + "the MATERIAL and its order respects the dependencies the MATERIAL states; otherwise REJECT.\n"
        + "Answer INSUFFICIENT only if the MATERIAL truly cannot decide it."
    )


def _make_grader(gold: str) -> Callable[[str], tuple[bool, str]]:
    """Grade one reply against its gold verdict using the PRODUCTION parser (no second parser)."""

    def grade(pred: str) -> tuple[bool, str]:
        # Lazy import: scripts/r5_code_review.py imports model_eval_suite.call at module scope,
        # so importing it at module scope would close an import cycle.
        scripts = str(REPO / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from r5_code_review import extract_verdict  # noqa: PLC0415 — cycle avoidance, see docstring

        verdict = str(extract_verdict(pred).get("verdict") or "UNPARSED").upper()
        return (verdict == gold, "gold=" + gold + " got=" + verdict)

    return grade


def suite_plan_quality() -> list[dict[str, Any]]:
    """Build the balanced planning fixture (24 items: 12 APPROVE-gold, 12 REJECT-gold).

    Returns:
        Harness items in the shape tools/model_eval_suite.py consumes.
    """
    task = _plan_task()
    max_tokens = _plan_budget()
    items: list[dict[str, Any]] = []
    for gold, cases in (("REJECT", REJECT_CASES), ("APPROVE", APPROVE_CASES)):
        for case in cases:
            items.append({
                "id": VERSION + "-" + str(case["id"]),
                "system": SYSTEM,
                "max_tokens": max_tokens,
                "user": _prompt(case, task),
                "grader": _make_grader(gold),
                "gold": gold,
                "why": case["why"],
            })
    return items


def baseline_scores() -> dict[str, float]:
    """Return the constant-answer baselines, computed from the fixture rather than assumed.

    A planner that emits one verdict for every item scores exactly the share of items carrying
    that gold verdict; a balanced 12/12 fixture therefore makes the baseline 0.5000.
    """
    total = len(REJECT_CASES) + len(APPROVE_CASES)
    return {
        "always_APPROVE": round(len(APPROVE_CASES) / total, 4),
        "always_REJECT": round(len(REJECT_CASES) / total, 4),
    }


def _selftest() -> int:
    """Known-answer controls: the fixture must build, balance, and grade both directions.

    No network and no model. Every control here has been SEEN to fire (D-3036: a control that
    cannot go red proves nothing).
    """
    items = suite_plan_quality()
    problems: list[str] = []
    if len(items) != 24:
        problems.append("expected 24 items, built " + str(len(items)))
    ids = [str(it["id"]) for it in items]
    if len(set(ids)) != len(ids):
        problems.append("duplicate item ids")
    base = baseline_scores()
    if abs(max(base.values()) - 0.5) > 1e-9:
        problems.append("fixture is not balanced: baseline " + str(base))
    passes = sum(1 for it in items if it["gold"] == "APPROVE")
    if passes != 12:
        problems.append("expected 12 APPROVE-gold, got " + str(passes))
    # both directions of the grader, against a known-answer reply
    approve_first = next(it for it in items if it["gold"] == "APPROVE")
    reject_first = next(it for it in items if it["gold"] == "REJECT")
    ok_a, detail_a = approve_first["grader"]('{"verdict": "APPROVE", "reason": "x"}')
    ok_r, detail_r = reject_first["grader"]('{"verdict": "REJECT", "reason": "x"}')
    if not (ok_a and ok_r):
        problems.append("grader failed a known-answer reply: " + detail_a + " / " + detail_r)
    ok_x, detail_x = approve_first["grader"]("I think it is fine, honestly.")
    if ok_x or "UNPARSED" not in detail_x:
        problems.append("grader accepted a reply with no verdict: " + detail_x)
    for it in items:
        if len(it["user"]) < 200:
            problems.append(it["id"] + ": material too thin to require reasoning")
        if not it.get("why"):
            problems.append(it["id"] + ": no recorded gold reason (D-3038)")
    for problem in problems:
        print("FAIL " + problem)
    if problems:
        return 1
    print("ok plan_quality fixture: 24 items (12 APPROVE / 12 REJECT), baseline " + str(base)
          + ", grader red on unparsed and green on both known answers, every item carries its reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
