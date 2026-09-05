# D2399 — Manual Review Instructions (292 genuine taxonomy gaps)

> **What this is:** 292 FBs have `discipline = 'emerging'` with a *genuine* non-empty
> `discipline_raw` that does not resolve to any of the 61 canonical disciplines.
> These are **taxonomy gaps** — real raw labels with no canonical target.
> `d2399_promotions_frozen: true` (in `config/pipeline_config.yaml`, line ~471)
> blocks auto-promotion because the D2521 auto-promote was semantically wrong.

## The population (live-verified 2026-09-05)

- **292** FBs, **257** distinct raw labels.
- **24** recurring labels (n ≥ 2) — listed below.
- **233** singletons (n = 1) — leave as `emerging`, do not act on them.

## The decision rule (one of 4 actions, per recurring label)

| # | Action | When | Where |
|---|---|---|---|
| **A** | **MAP** to an existing canonical discipline | the raw label is a synonym/variant of one of the 61 canonicals | add to `config/alias_map.yaml` → `discipline_aliases` |
| **B** | **KIND-SWAP** to the domain axis | the raw label is really a *domain*, not a discipline (cross-kind leak) | move the raw label to `domains_raw`; leave `discipline = emerging` (BUG-197 pattern) |
| **C** | **PROMOTE** to a new canonical discipline | ≥ 5 stable FBs **and** a clear definition **and** you confirm it is a real field not covered by an existing canonical | un-freeze `d2399_promotions_frozen`, add the canonical to `config/taxonomy_v5.yaml`, re-derive |
| **D** | **LEAVE** as `emerging` | nothing above applies (honest "no canonical fits") | nothing — `emerging` is the open-world state, not a failure |

## Suggested actions per recurring label (n ≥ 2)

| Raw label | n | Suggested action | Target / note |
|---|---|---|---|
| Ecology | 5 | **C** (promote) or **D** | only genuine promotion candidate; needs a definition + your confirmation |
| Musicology | 4 | **D** | nearest (performing arts / cultural studies) is a lossy fit |
| Marketing | 4 | **B** (kind-swap) | `marketing & communications` is a DOMAIN, not a discipline |
| Applied Mathematics | 4 | **D** | no clean canonical |
| audio signal processing | 3 | **D** | no `signal processing` canonical exists |
| History of Technology | 3 | **D** | no `history` canonical |
| photography | 2 | **B** or **D** | likely a domain |
| management consulting | 2 | **A→strategic thinking** or **D** | |
| history of philosophy | 2 | **A → philosophy** | clear synonym |
| financial engineering | 2 | **A → finance** | clear |
| creative industry studies | 2 | **D** | |
| Transportation Engineering | 2 | **A → engineering** | |
| Sustainability Studies | 2 | **D** | |
| Signal processing | 2 | **D** | |
| Medical Imaging | 2 | **A → health & medicine** | |
| Medical Humanities | 2 | **A → health & medicine** | |
| Materials Science | 2 | **D** | |
| Intelligence Studies | 2 | **D** | |
| Experimental Psychology | 2 | **A → psychology** | clear |
| Educational Measurement | 2 | **A → research methodology** or **D** | |
| Design Studies | 2 | **A → design thinking** | |
| Creative Economy Studies | 2 | **D** | |
| Business Administration | 2 | **D** | |
| Architectural History | 2 | **A → cultural studies** or **D** | |

## Step-by-step (what YOU actually do)

1. **Review the table above.** For each "A" row, decide yes/no on the target. For "C" rows, decide promote-or-leave.
2. **Apply the "A" (map) decisions** by editing `config/alias_map.yaml` → `discipline_aliases:` (add `raw_label: canonical`). Then run `python3 scripts/apply_alias_corrections.py --apply` (or the canonical re-derive pass) to re-map the affected FBs.
3. **Apply the "B" (kind-swap) decisions** via `python3 scripts/bug197_kind_swap.py` (moves domain raw labels from `discipline_raw` → `domains_raw`).
4. **For the one "C" candidate (Ecology, 5 FBs):** if you approve, write a one-sentence definition, add it to `config/taxonomy_v5.yaml` disciplines with a `group`, set `d2399_promotions_frozen: false` temporarily, run the promotion, then re-freeze. If not, leave it `emerging`.
5. **Leave everything else** (233 singletons + all "D" rows) as `emerging`. Do **not** bulk-promote.

## What you should NOT do

- ❌ Do **not** bulk-promote the singletons (they are honest long-tail open-world labels).
- ❌ Do **not** auto-promote on raw frequency alone (this is what D2521 got wrong).
- ❌ Do **not** create a new canonical for a label with < 5 FBs.
- ❌ Do **not** delete the raw labels — they are preserved provenance.

## After you act

- Re-run `python3 scripts/recompute_decision_summary.py` and recount `taxonomy_counts`.
- Record each action as a new decision (D2572+) in `config/decisions.yaml` and re-sync `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `agent/session_seed.yaml`.

> **Reference:** `governance/ROUNDTABLE_HANDOFF_D2569_ADJUDICATED_2026-09-05.md` §6 item 8, and the 61 canonical disciplines in `config/taxonomy_v5.yaml`.
