# Session Handoff — 2026-09-06 (data-absent disciplines resolved + vote prep)

> **Phase:** v3.0 auto-sorter (discipline/domain classifier) + label-quality pipeline
> **Current time:** 2026-09-06 ~10:00 +02:00
> **Working tree:** UNCOMMITTED (this session + prior D2578→D2583 work)
> **Supersedes:** SESSION-HANDOFF-2026-09-05.md

---

## 0. TL;DR — where we are

The three "next critical steps" from 2026-09-05 were picked up:

1. **`bug197_kind_swap` — DONE.** 400 FBs kind-swapped (2 discipline + 35 domain
   recovered). Net discipline=emerging 761→759.
2. **Generate FBs for the 3 data-absent disciplines — DONE via D2584 (refined).**
   Re-inspection showed the 3 disciplines were NOT missing content — their FBs
   exist with complete skeletons but had **unresolved domain axes**
   (`domains=["emerging"]` despite real `domains_raw`). Fixed deterministically
   (alias-map extension + re-derivation), **no new FB fabrication needed**.
   Result: computational theory 4→5, ecology 4→5, robotics 1→5; **61/61
   disciplines trainable** (was 58); golden set 1026→1027 examples.
3. **3-model vote — PREPARED, BLOCKED on OMLX (down).** `--golden` source added
   to `scripts/label_vote.py`; dry-run validated. The actual `--run` needs the
   OMLX server up (currently not listening on port 11435).

---

## 1. What was done (this session)

| Item | State | What |
|---|---|---|
| bug197_kind_swap | ✅ APPLIED | 400 FBs (2 discipline + 35 domain recovered). DB backed up `maxwell.db.bak_20260906_080236`. |
| **D2584** | RESOLVED | Domain-axis re-derivation for data-absent disciplines. Added 19 robotics/autonomous-systems + theoretical-CS aliases to `config/alias_map.yaml` → `domain_aliases` (→ `engineering & infrastructure`, `computational science & physics`). New `scripts/resolve_data_absent_domains.py` (dry-run/apply, idempotent, backup+reconcile). Re-mined golden set. |
| ecology | ✅ (via D2583 swap) | 4→5 golden examples. |
| computational theory | ✅ (D2584) | 4→5. |
| robotics | ✅ (D2584) | 1→5. |
| `label_vote.py --golden` | ✅ ADDED | New `--golden PATH` source (targets the mined golden YAML 1:1 with classifier examples); dry-run validated. |
| Governance | ✅ SYNCED | `decisions.yaml` 559→560 (D2584); summary recomputed (resolved 47→48); DECISION-LOG.md + MASTER-TASK-REGISTER.md updated. |

---

## 2. Current system state (verified ~10:00)

- **DB:** `knowledge pipeline/maxwell.db` — total 7,995 FBs; discipline=emerging **759**.
- **Golden set:** `config/golden/stage4_golden_mined.yaml` — **1,027** examples, 61/61 disciplines, all trainable (≥5). backfilled=27.
- **Decisions:** total **560**, active 460, resolved **48** — `recompute_decision_summary.py --check` exit 0.
- **OMLX:** **DOWN** (port 11435 not listening — no process). Required for the vote.
- **DB backups created:** `maxwell.db.bak_20260906_080236` (kind-swap), `maxwell.db.bak_20260906_080915` (resolve).
- **alias_map backup:** `config/alias_map.yaml.bak_20260906_080819_pre_d2584_domains`.

---

## 3. Next critical steps (priority order)

1. **Start OMLX** (via `/Applications/oMLX.app` — the single-source canonical
   launcher) and load the 3 voter models (Qwen3.8-27B-MLX-4bit,
   gemma-4-E4B-it-MLX-4bit, Phi-4-mini-instruct-8bit).
2. **Run the 3-model vote** over the golden set (small first, then full):
   ```
   python3 scripts/label_vote.py --golden config/golden/stage4_golden_mined.yaml --limit 5 --run --output temp/label_vote_golden_validate.jsonl
   python3 scripts/label_vote.py --golden config/golden/stage4_golden_mined.yaml --run --output temp/label_vote_golden.jsonl
   ```
   BUG-224 note: single-FB calls are already enforced; Qwen3.8 may wedge on long
   output — the D2581 wedge-recovery handles it, but keep an eye on the first ~20
   FBs. 1,027 FBs × 3 voters ≈ 6–8 h.
3. **Re-train the auto-sorter** (`scripts/train_discipline_classifier.py`) with the
   now-complete 61/61 training set — longer epochs + hparam/label-smoothing sweep;
   hold macro-F1 ≥ 0.75 (baseline 0.2621).
4. **Stand up the 4-way depth classifier** (ModernBERT) + A/B vs gpt-oss (gate ≥0.85).

---

## 4. Open items / notes

- **D2582 TODO(1)** — upgrade missing-close-domain flag from "any-absent" to
  bge-m3 embedding-similarity closeness (still open).
- **D2582 TODO(3)** — third-voter policy: default Phi-4-mini is already wired in
  config; confirm before the full vote run (DeepSeek rejected: CLOUD + DELEGATE-001).
- **BUG-224 full verification** — wedge-recovery (D2581) still unverified under a
  live sustained-load wedge; the full vote run is the natural test.
- **Latent bug (from 2026-09-05 §5)** — kind-swap/demotion scripts clear
  `discipline_raw` without resetting `taxonomy_match_method` → `emerging_unmapped`.
  `scripts/resolve_data_absent_domains.py` deliberately does NOT touch either field.
  Still worth a low-severity fix + regression check.
- **`bug197_kind_swap.py` docstring/code mismatch** — docstring says `--apply`, but
  the code applies by default (no `--apply` flag). Fix the CLI flag for safety.

---

## 5. Uncommitted working tree

**Modified (this session):** `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`,
`config/alias_map.yaml`, `config/decisions.yaml`, `scripts/label_vote.py`.

**Modified (prior session, still uncommitted):** `config/pipeline_config.yaml`,
`governance/buglog.md`, `pipeline/omlx_call.py`, `pipeline/pipeline_paths.py`,
`pipeline/schemas.py`, `scripts/train_discipline_classifier.py`.

**Untracked (new):** `scripts/resolve_data_absent_domains.py` (this session);
`config/golden/stage4_golden_mined.yaml`, `scripts/label_vote.py`,
`scripts/mine_classifier_golden.py` (prior session).
