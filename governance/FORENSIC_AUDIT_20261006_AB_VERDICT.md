# Forensic Audit — D-2767 A/B Verdict + BUG-658 (2026-10-06)

## 0. Headline (supersedes prior "in-flight / wedged" narrative)
The flag-ON D-2767 A/B **completed** at 20:28 local (`governance/d2767_ab_flagon_20261006d.json`):

| metric | value | gate | verdict |
|---|---|---|---|
| Cohen's kappa | **0.4313** | >= 0.800 | **FAIL** |
| emerging rate | 0.0299 | <= 0.35 | pass |
| raw agreement | 0.4478 | (reported, not gated) | — |
| determinism (prefix) | 8/8 | byte-identity | pass |
| disagreements | 111 / 201 | — | 55% |

The definition-anchored flag-ON classifier does **NOT** reproduce the owner referee
(kappa 0.43 ≪ 0.80). **D-2839 gate is FAILED → `definition_anchored_menu_enabled`
must stay OFF.** The prior session's "client wedged, no CSV landed" was a
misdiagnosis: the wedge (PID 15071) was a *separate later* re-run; the gate result
and the 111-row disagreement CSV had already landed.

## 1. Break / hidden-failure (BUG-658) — root cause, now mitigated
- **Mechanism:** `call_omlx` uses `requests.post(timeout=(connect, read))` with
  `READ_TIMEOUT=60` = time *between bytes*. OMLX `sse_keepalive_mode: 'chunk'` emits
  periodic keepalive bytes → the read timer is reset forever → no total wall-clock
  deadline → silent hang (no exception → circuit breaker never opens).
- **Blindspot:** `omlx_watchdog.py` watches only server RSS, not client liveness.
  `d2767_ab_eval.py` had no pre-flight model-loaded check.
- **Fix applied (unlocked, harness level):** `scripts/d2767_ab_eval.py` now (a) runs a
  fail-closed preflight smoke classification of `examples[0]` under a wall-clock
  deadline, and (b) wraps every `call_omlx_json` in `_call_omlx_json_with_deadline`
  (daemon thread + `join(timeout)`; one recovery-sleep retry, then `WedgeError`).
  Config keys added: `services.omlx.wall_clock_deadline_sec=180`,
  `preflight_smoke_deadline_sec=120`.
- **Still open (pipeline lock):** the ROOT fix in `pipeline/omlx_call.py::call_omlx`
  (a total wall-clock deadline inside the retry loop, not just in the harness) needs
  owner ack. Until then, any *other* caller of `call_omlx_json` (stage2/4 pipelines)
  remains vulnerable.

## 2. Taxonomy decision C — APPROVED; defect inventory (actual labels)
Exact cross-axis collision is only `emerging` (the abstention, expected in both).
The real contamination is **near-identical cross-axis + within-axis clusters**:

Cross-axis (discipline vs domain, same concept, different label):
`artificial intelligence`↔`ai & agents`, `finance`↔`finance & investment`,
`marketing`↔`marketing & communications`, `entrepreneurship studies`↔`entrepreneurship`,
`research methodology`↔`research & methodology`, `semiotics`↔`semiotics & communication`,
`engineering`↔`engineering & infrastructure`/`engineering practice`.

Within-axis near-synonyms (discipline): `machine learning`/`artificial intelligence`/
`generative ai`; `systems thinking`/`systems engineering`/`complex adaptive systems`;
`psychology`/`cognitive science`/`decision making`/`behavioral economics`/`design
psychology`; `visual perception`/`visual semiotics`/`semiotics`. (domain):
`code & computation`/`computational art`/`creative technology`; `digital product`/
`product design`/`web & ui`/`user experience`/`information architecture`;
`business development`/`business operations`/`organizational behavior`.

Decision C: freeze `closed_menu_v6.json` (menu_hash-pinned to the ratified 201-row
referee), build `closed_menu_v7.json` as a new versioned file from the 111 disagreement
rows + above clusters (merge true near-synonyms, rename cross-axis collisions to
axis-scoped labels, add one-line discriminator fields), gate v7 behind its own A/B
(adopt only if kappa improves).

## 3. Drift guard (mandatory prerequisite — do NOT skip)
Consolidating labels invalidates every anchor/golden/config/script that references an
old label string. Before v7 adoption: remap all affected (anchors, golden examples,
`domain_disciplines.yaml`, `alias_map.yaml`, `menu_*_map.yaml`, `discipline_anchor_*`
manifests, any script comparing label strings). Unremapped = silent drift.

## 4. Next critical steps (strategic order)
DECISIONS:
- D-A: Ratify A/B verdict (kappa 0.4313 → gate FAILED). Supersedes "A/B unblocked".
- D-3 (taxonomy C): APPROVED (this turn). Owner signs menu v7 consolidation plan.
- D-B: Owner ack to add total wall-clock deadline in `pipeline/omlx_call.py` (root fix).

BUGS:
- BUG-658: OPEN (harness mitigated; root fix pending).
- BUG-NEW: `FORENSIC_AUDIT_20261006_RESOLUTION.md` omitted the 6 cross-axis
  near-identical labels (menu-audit blindspot) — fixed in this doc.

TASKS (in order):
1. Relaunch A/B with the harness fix → confirm preflight runs + no wedge + reproduce kappa.
2. Build `closed_menu_v7.json` from the 111-row disagreement CSV + clusters.
3. Remap all anchor/golden/config/script label references to v7.
4. Re-run A/B on v7 → adopt only if kappa improves toward >= 0.800.
5. Root-fix `call_omlx` wall-clock deadline (pipeline lock, owner ack).
6. Sync DECISION-LOG / MTR with D-A and this verdict.

## 5. Governance sync performed this turn
- `agent/session_seed.yaml` status updated to the real verdict (was "A/B unblocked").
- `governance/buglog.md` BUG-658 heading corrected (gate landed; wedge was separate).
- Counters unchanged (BUG-658 still OPEN → open_bugs_n 163, highest_bug BUG-658).
