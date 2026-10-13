# T-107 — the payload decision: ONE line per field (owner sheet)

**What this is:** the manual task. You write **one word per field** into `config/served_fields.yaml`, and the rail
does the rest. The explanation behind it is `governance/BORP_FEEDBACK_ASSESSMENT_20261013.md` (evidence) — this file
is only the writing surface.
**Why a file is needed at all:** changing what an agent is told is a contract change; no agent may decide it
(D-2898). The row you fill is the OWNER WORD; `config/served_fields.yaml#owner_word` is its ONE home (the record is
not the rule — BUG-548).

---

## 1. The vocabulary — real tokens, enforced

The T-101 lesson: `keep/replace/drop/add` are accepted **nowhere**. These are the tokens the rail accepts, and it
**fails closed** on anything else:

| token | means | the code act it licenses |
|---|---|---|
| `retire` | the field leaves the served surface(s) completely | delete its keys from every surface; remove its disposition here |
| `keep` | the field stays, unchanged, and its absence stays as it is | delete its disposition here if its registers are clean; otherwise keep an explicit `keep-and-declare` |
| `keep-and-declare` | the field stays, but its ABSENCE must be made explicit on the wire | publish `{score, count, state, prior, effective}` instead of a bare `null` |
| `keep-and-repair` | the field stays and its VALUE must be repaired at source | the writer/stage fix named in `why`, then re-record |
| `promote <field>` | a DIFFERENT, healthier field replaces it on the surface | advertise the named field (its home must be recorded) |

## 2. What you write (3 rows — 3 words)

Open `config/served_fields.yaml`, section `owner_word.rows`, and replace each `word: pending` with exactly one token.
Your `anchor` (owner signature) goes on the same line: `anchor: <your initials+date>`.

| # | field | today (measured 2026-10-13) | the recommendation | why it matters |
|---|---|---|---|---|
| 1 | `borp_score` | **constant `0.0` on 7,640/7,640 rows**, nothing writes it; the formula it inherited is degenerate (a pass-ratio whose floor equals its bar ⇒ always 1.0 on admitted rows); still published to agents + OKF + Anytype as a trust metric | **`retire`** + **`promote corroboration`** (from `isor`, D2284 — already stored on 6,591 rows) | agents currently read `0.0` as "no corroboration" on rows that are `strong` with 21 sources; the fabricated number also leaves the machine in exports |
| 2 | `feedback_score` | **NULL on 7,640/7,640 rows** — but its ledger (`fb_feedback`) and its writer (`pipeline/feedback.py::_update_fb_aggregates`) both exist; the serving path already ranks on it through a neutral prior | **`keep-and-declare`** | a bare `null` cannot be told from "score 0.0 = useless"; declaring the state keeps the contract for the one primitive that lets the corpus learn from use |
| 3 | `classification_status` | **constant `'CLEAN'` on 4,503/4,503 PASS rows**; both registers that own the fact call it a defect (`config/store_columns.yaml` `status: debt`, `config/derivations.yaml` `orphan_magic_threshold`) | **`keep-and-repair`** (or `retire` if the payload should not carry it at all) | the payload publishes a status while the store's own status column QUARANTINEs 2,972 rows — two statuses on one row is the D-2987 defect on the wire |

If you want the corroboration block on the wire, the word for row 1 is `retire` **and** `promote corroboration` —
one row, two tokens, and the rail requires BOTH halves (a deleted key with no promoted signal would just remove
information).

## 3. What happens after you write it (no further work for you)

```
python3 scripts/check_served_fields.py            # rc 2 = declared debt (loud, not fatal) | rc 1 = an UNDECLARED
                                                  # dead advert  | rc 0 = every advertised field is true
python3 scripts/check_served_fields.py --selftest # 8 known-answer controls (each refusal named by its guard)
python3 scripts/check_feedback_parity.py          # the ledger -> cache parity rail (D-2642)
just health                                       # the full ladder
```

The rail then tells the agent exactly which code edits the word licenses, and it **refuses a half-move**: a
declaration without the code edit is an assertion (BUG-488 class), a code edit without the declaration is an
undeclared advert (BUG-511 class). Debt today = **3** and the ceiling is shrink-only (it may only fall).

## 4. The one question that is NOT a payload question (T-118)

79.2% of served rows (`status='PASS'`) are **single-source** — the Book of Record Principle is satisfied on 938 of
4,503. That is a policy ruling, not a schema edit:

* `tier` — serve them, but every answer carries `corroboration.tier = "single_source"`;
* `withhold` — they stay out of the default answer path (a serving-gate change);
* `leave` — accept single-source rows as first-class and say so in the mission.

One word on **T-118** in `config/task_register.yaml` (or in chat) — and it does not block the three rows above.
