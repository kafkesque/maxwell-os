# FORENSIC AUDIT — Owner re-derivation decisions (2026-10-06)

**Subject:** Owner's consolidated adjudication of the D-2820 re-derivation worklist
(`governance/Surveillance Capitalism and Soviet Discourse.numbers`, table
`rederive_v6_differences_only`, 142 rows) against menu v6.

**Verdict:** CLEAN. 0 off-menu labels. No cascade / drift / blindspot / conflict / bug /
hidden-failure / error-leak / mismatch / bloat detected. Four (4) owner-gated items remain
(drops, emerging-mix, taxonomy boundaries) — flagged below, NONE silently applied.

---

## 1. Column I — "Final discipline" (142 owner-decided rows)

| Finding | Count | Detail |
|---|---|---|
| OFF-MENU discipline | **0** | every label ∈ menu v6 ∪ {emerging} |
| Empty (DROP) | **3** | `R084`, `R106`, `R148` — owner wrote "noise/drop irrelevant" |
| `emerging` (abstain) | **7** | `R006 R059 R127 R140 R146 R165 R202` — valid abstention token |

## 2. Column J — "Final Domain" (142 owner-decided rows)

| Finding | Count | Detail |
|---|---|---|
| OFF-MENU domain | **0** | every token ∈ menu v6 ∪ {emerging} |
| Empty | **2** | `R084`, `R106` (full DROP — both axes empty) |
| Separator typos (`,` / `.`) | **4** | normalized to `\|`: `R159 R177 R188 R195` |
| `emerging` mixed with real domains | **4** | `R023 R112 R177 R188` — semantic contradiction, see §4 |

Separator normalization applied:
- `R159`: `user experience, research & methodology` → `user experience|research & methodology`
- `R177`: `semiotics & communication. emerging` → `semiotics & communication|emerging`
- `R188`: `education,emerging` → `education|emerging`
- `R195`: `ai & agents , engineering & infrastructure` → `ai & agents|engineering & infrastructure`

## 3. Column K — notes (6 typo/grammar fixes, cosmetic only)

| Row | Before | After |
|---|---|---|
| R036 | It all software based jargon  nothing to do with psychology | It's all software-based jargon — nothing to do with psychology. |
| R049 / R104 | Its more complex than just a decision making | It's more complex than just decision making. |
| R084 / R106 | Thi is noise drop it is irrelevant | This is noise — drop; it is irrelevant. |
| R148 | Noise drop irrelevant | Noise — drop; irrelevant. |

## 4. Owner-gated items (do NOT auto-apply)

### 4a. DROP rows (3) — needs a triage decision
`R084` (Data Visualization Research Lab Leadership), `R106` (The Invisible Art of Film Editing),
`R148` (Professional Development Through Studio Experience) — owner marked "noise / drop irrelevant".
Dropping them reduces the anchor 204 → 201 and changes the full-204 A/B denominator.
**R148 is inconsistent:** discipline empty but domain still `education|design strategy|leadership`.
Recommendation: confirm all 3 as DROP, clear both axes, re-cut the anchor to total=201.

### 4b. `emerging` mixed with real domains (4) — needs owner confirmation
`R023 R112 R177 R188` carry `emerging` alongside one or more real domain tokens. The abstention
token is meant to stand alone (off-menu / not-yet-classified). Mixing it with real domains is
ambiguous for the emerging-rate gate (≤0.35). Owner must pick: (a) keep `emerging` alone (full
domain abstain), or (b) drop `emerging` and keep only the real domains.

### 4c. Taxonomy boundary clarifications — PROPOSED (menu edits need owner sign-off)
`config/closed_menu_v6.json` is PROTECTED. The following boundary rules are proposed as D-2844
but must NOT be edited without owner sign-off (menu edit ⇒ re-render ⇒ pin change ⇒ re-derive).

## 5. Taxonomy boundary analysis (ambiguity / overlap)

Boundary rules proposed (discipline, most-consequential first):

1. **strategic thinking vs decision making** — strategic thinking = *direction/goal over a horizon*
   (WHERE/WHY: positioning, long-term goal-setting, planning). decision making = *the act of choosing
   among alternatives at commitment* (WHICH: framing, criteria, decision rules, bounded rationality).
   Tie-break: choice-mechanism → decision making; direction/horizon → strategic thinking.
2. **business administration vs operations research** — operations research = *quantitative methods*
   (optimization, LP/IP, queueing, simulation, named criteria like minimin/minimax, Fermi estimation,
   complexity). business administration = *management/organization lens* (structure, governance, HR,
   strategy, coordination). Tie-break: named numerical/analytical method → OR; run/coordinate a firm → BA.
3. **business administration vs organizational theory** — organizational theory = *descriptive/analytic*
   (why/how orgs behave, design principles, dynamics). business administration = *applied/prescriptive*
   (how to run/govern). Biggest data-driven confusion (4 relabels OT→BA). Needs distinct wording
   ("structured, coordinated" appears verbatim in both definitions).
4. **marketing vs design psychology vs behavioral economics** — behavioral economics = *describes* the
   bias; design psychology = *exploits* the bias to change a decision; marketing = *market lens*
   (value exchange, positioning, segmentation, buyer behavior). Tie-break: bias-as-topic → BE;
   bias-as-lever → DP; market/exchange → marketing.
5. **generative ai vs artificial intelligence vs machine learning** — content-generation → genAI;
   learn-from-data → ML; broad capability/agents → AI. (Hierarchy: AI ⊃ ML; genAI ⊂ AI.)

Domain overlaps (same boundary-fuzziness treatment):
6. **business development vs business operations vs entrepreneurship** — external revenue/market
   expansion → BD; internal process/admin → BO; venture creation/startup → entrepreneurship.
7. **digital product vs web & ui vs product design** — software app UI/UX → digital product;
   responsive website/UI components → web & ui; end-to-end physical+digital → product design.
8. **research & methodology vs science & research** — methodology-of-research → R&M; specific
   scientific-domain findings → science & research.
9. **semiotics & communication (domain) vs communication theory / visual semiotics (disciplines)** —
   three labels span one concept cluster; recommend clarifying that the domain is the *subject-matter
   bucket* while the disciplines are the *analytic lens*.

## 6. Normalized artifacts written

- `governance/rederive_v6_owner_decisions_normalized.csv` — full 204 rows (62 carried + 142 decided),
  clean pipe-separated labels, `status` ∈ {carried, owner_decided, drop}, corrected notes.
- `governance/rederive_v6_owner_decisions.json` — `{decisions: {item_id → {discipline, domains}},
  drops, emerging_mix_pending, abstain_discipline}` for `--adjudicate`.

## 7. What was NOT done (and why)

- `--adjudicate` / `--verify` / `--finalize` were NOT run: the harness `apply_owner_decisions` is
  fail-closed and requires every one of the 204 rows to carry a non-empty on-menu discipline + domains.
  The 3 DROP rows have empty discipline, so the run would fail-closed by design until the drop triage
  is resolved (4a). Finalize is additionally gated on D-2839 owner sign-off + the full-204 A/B.
- `config/closed_menu_v6.json` was NOT edited (protected); boundary clarifications are PROPOSED only.
