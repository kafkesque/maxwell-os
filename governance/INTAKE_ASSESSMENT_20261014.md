# INTAKE ASSESSMENT — external methods, models and decision techniques

> **Authority:** owner request 2026-10-14 (T-124 session, same-day as the D-2995/ladder work). **Status:** ASSESSMENT —
> nothing here is adopted until it is a decision with a rail. **Reader rule:** every row is either a MEASUREMENT
> (machine-read on the date shown) or a METADATA-ONLY read (state it). No row is a claim about a system we did not read.
> **NOT a decision record.** Adoption = a `D-` record + a home + a rail (C12/C21). This file names candidates.

---

## §0 — PROVENANCE (what was actually read, and what was not)

| source | how it was read | what was measured |
| --- | --- | --- |
| `github.com/Mapika/decider` | README + repo metadata, machine-read 2026-10-14 | full README (36 KB), Apache-2.0, 1,140★ |
| `aclanthology.org/N19-1300` | page + abstract, machine-read 2026-10-14 | title + abstract (BoolQ) |
| `scikit-learn.org/0.19/datasets/twenty_newsgroups.html` | page, machine-read 2026-10-14 | the dataset protocol + the filtering section |
| `youtube.com/watch?v=dW-ktsvhQQI` | metadata only (title/channel/date/description) | marimo, "We ran some benchmarks", 2026-10-12, 968s |
| `youtube.com/watch?v=olIve0D8pJQ` | metadata only | The AI Automators, 2026-09-24, 966s |
| `youtube.com/watch?v=HIRDzMtuWFk` | metadata only | Nate Herk, 2026-09-13, 587s |
| `youtube.com/watch?v=2H0zj28ECak` | **transcript captured** (559 words, `temp/intake_20261014/tr3_multibug_video.txt`) | the Anthropic multi-agent bug-hunt protocol |
| `github.com/mattpocock/skills` | repo tree + 30 docs downloaded to `temp/intake_20261014/` | tree + README read; per-doc digest delegate FAILED (decode error) — see §8 |
| `github.com/tester-army/e2e` | README, machine-read | the runner's stated mechanisms |
| `github.com/topics/e2e-testing`, `.../end-to-end-testing` | topic pages, machine-read | 20 repos each (names captured) |

**TRANSCRIPT BLOCKER (declared, not hidden):** three of the four YouTube videos returned **HTTP 429 / SABR** from this
machine on the subtitle endpoint (yt-dlp, 4 client variants, plus two third-party transcript services) — so the three
un-captured videos are **title/description-level evidence only**, and their claims are NOT relied on below. The one
transcript that did resolve is the one whose content is load-bearing (§5).

---

## §1 — THE SINGLE MOST CONSEQUENTIAL FINDING: a DECISION MODEL is not a generator

`Mapika/decider` (and the `Jev`/`Laya` family the two videos are about — identified in §1.2) is a language model that
**does not generate text**. It reads a *state* plus a set of *typed questions* and returns, **from one forward pass**, a
probability distribution over every question. The types are `Choice` (2–255 options), `Score` (2–10 described levels)
and `Noul` (P(yes)). Its own README states the consequence plainly: *"There is no decoding, no parsing, and no output
outside the options you defined."*

**Why this is the highest-leverage external idea in this intake.** Maxwell OS already spends its hardest engineering on
exactly the failure this removes:

| Maxwell's existing control | what it defends against | how a typed decision changes it |
| --- | --- | --- |
| R7 `temp=0.0` on every generation script | sampling drift | **structurally unnecessary**: there is no sampling step to set |
| Closed menus (D-371, `closed_menu_v*`, `check_menu_reclass_gate`) | answer-space drift | becomes the MODEL'S interface: options are the interface, not a post-hoc check |
| `check_label_provenance` / fail-closed parsers (C16) | a model that returns prose where a token is required | **no parsing exists** — the output cannot be outside the declared set |
| D2635 ARM-2: gpt-oss-20b **2/6 schema-valid** vs Qwen3-Coder 6/6 | instruction-following JSON is a WEAK spot | a schema-valid response is not a hope; it is the only possible response |
| `isor`/corroboration tiers, PASS/QUARANTINE, depth (4-way) | ordinal judgement | `Score` over *described levels* is the native form |
| CRIBS field quality (this session's question) | slop in enrichment | a `Noul`/`Score` head MEASURES; a humanizer only re-writes |

**The honest limits (stated, because an adoption without its cost is marketing):** (i) the served models are 2B–12B
fine-tunes of Qwen3.5/Gemma-4 — they carry **no Maxwell domain knowledge**, so the *state* must contain the retrieved
evidence (a RAG-shaped input, which is the point, not a problem); (ii) `decider-12b` is *Gemma-4-12B-it with a
state-tracking LoRA* — i.e. **the same base family OMLX already serves** (`gemma-4-12B-it-qat-OptiQ-4bit`), so the M1's
fit is plausible and testable at zero marginal cost (`$0`/C1 holds: it is a local forward pass); (iii) 4B/2B accuracy
numbers on the vendor's own benchmark are **vendor measurements** until re-measured here (the D-2635 lesson).

### §1.1 Where it maps onto Maxwell OS, role by role

| Maxwell role | today | typed-decision candidate | verdict |
| --- | --- | --- | --- |
| **S4 classifier** (discipline/domains/depth) | `gpt-oss-20b-MXFP4-Q8` + a JSON contract | `Choice` over the closed menus (discipline) + `Score` over depth levels | **WORTH — highest**: this is the role with a MEASURED schema-validity defect (2/6) |
| **S5 verifier** | DeBERTa-v3-large NLI (D2298) | keep NLI (see §4.1: BoolQ validates entailment transfer) — but add a `Noul` head as a SECOND, independent verifier | **HOLD** — R5 (generator ≠ verifier) is already satisfied; a second head must be *independent*, and a sibling model family is not |
| **CRIBS enrichment quality** | an advisory guard in `stage4_merge.py` (informational, not blocking) | `Noul` heads: "does the body entail this `failure_mode`?", "is this `elaboration` template-shaped?" | **WORTH** — the detector this session recommended, with a calibrated probability instead of a judged string |
| **Routing / preflight** ("is this FB in scope?", "does this need a human?") | rules + string matching | `Noul` | **WORTH** — cheap, and each one replaces an undeclared heuristic |
| **Decision *minting*** (what a `D-` record should say) | owner + agent | **REJECT** — an answer-space decision is the owner's (D-2898/D-371), and a 2B head must never mint governance |
| **Corpus admission** | `is_convergent` + S1.5 gate | **REJECT** for now — the gate's policy question is T-118 and is the owner's; the model may *measure*, not *gate* (R2 in `BORP_REVITALIZATION_RISK_20261013.md`) |

### §1.2 `Laya` identified (the owner's second question)

`Laya` is **not a state-machine framework**. It is a **typed-decision classifier model family** in the same
System-One ecosystem as `Jev`: a 322M/421M **ModernBERT**-class encoder with open weights, **local MLX** support, and
typed decisions — one public SDK describes it as *"Classify text in PHP without an LLM bill: typed decisions in 100+
languages, self-hosted"*. Adjacent community work places `Jev` and `Laya` together as `System 1` decision models
(`harshavarma02/system1-jev-laya-agent`; `datenwissenschaften/retro-speedlab-core`), and one repo pairs a `Laya` head
with a **Control-Barrier-Function "shield"** — a control-theory construct for guaranteeing that a chosen action stays
inside a declared safe set.

**Consequence for the owner's question ("can a state machine or Laya be used for the knowledge base for primitives and
non-principles"):** the two are answers to **different** questions and should not be conflated.

* **`Laya`/`decider` (a decision head)** answers *"what is this, from a closed set?"* — the RIGHT tool for
  classification over primitives, tiers and gates; the WRONG tool for representing structure (it has no notion of a
  relation between two things).
* **A state machine** answers *"what may happen next, from where we are?"* — the right tool for the **row LIFECYCLE**
  and for **non-principles** (a *non-principle* is, by construction, a claim about what is NOT established — i.e. an
  ordering/absence property, not a type), and the wrong tool for *what a thing IS*.

See §6 for the concrete design (it is not a rewrite; the lifecycle already exists implicitly in D-2992/D2625).

---

## §2 — ADOPTION MATRIX BY PART OF MAXWELL OS

Verdict vocabulary: **MUST** (a defect it fixes is already measured here) · **SHOULD** (clear gain, bounded cost) ·
**WORTH** (candidate, needs a measurement first) · **HOLD** (blocked on a ruling) · **REJECT** (with the reason).

### Knowledge pipeline
| item | source | verdict | what it fixes here |
| --- | --- | --- | --- |
| Typed decisions for S4/discipline/depth | `decider` §1 | **MUST (measured)** | D2635 ARM-2: 2/6 schema-valid on the classifier role. A `Choice` over the closed menu cannot return off-menu |
| **Shard + fresh-context hunt + ADVERSARIAL falsifier** as a *program*, not a chat | video 3 transcript | **MUST** | this session's own evidence: BUG-777/778 hid because one red line masked 68 rails. The transcript's numbers: one agent found 14/15/27 of 70 planted bugs, *"each time it planted its flag and called the job done"*; the workflow found **66, three times** |
| Budgeted agent sessions (a session budget that PAUSES the run; ≤1,000 agents/run) | video 3 | **SHOULD** | the `run_wall_budget`/`omlx_guard_ceiling` labels are declared but a *run* has no per-session spend stop |
| The plan written down AS A PROGRAM (so the plan is never summarised away) | video 3 | **SHOULD** | `pipeline/parallel.py` + subprocess is already this shape; the missing half is that a repair *campaign* has no written program — each session re-derives it |

### Knowledge-base retrieval
| item | source | verdict | what it fixes here |
| --- | --- | --- | --- |
| **Entailment-transfer** for yes/no decisions (transfer from NLI beats paraphrase/extractive transfer) | BoolQ (ACL N19-1300) | **ADOPT — validates D2298** | our verifier IS an MNLI/FEVER/ANLI DeBERTa; BoolQ is peer-reviewed evidence that this is the right axis, and it names what to train on next if we ever fine-tune |
| **Majority-class baseline + human ceiling published with every accuracy** | BoolQ (80.4% vs 90% human vs 62% majority) | **MUST (cheap)** | T-101's ruler is saturated at recall@10 = 1.000 — a number with no baseline and no ceiling is not a measurement. Every decision rail owes (a) a majority baseline, (b) a human ceiling |
| **Date-ordered (temporal) splits**, not random folds | 20 newsgroups | **SHOULD** | our classifier is never evaluated in time order; the corpus has THREE times (D-2992) and a random fold leaks the future into the past — the exact drift class D-2992 exists to name |
| **Leak-filtering the metadata before training/eval** (headers, footers, quoted text) | 20 newsgroups "Filtering text for more realistic training" | **SHOULD** | our FBs carry `name`/`keywords`/`source_*` — a classifier that can read the *title* is not being tested on the *body* |
| Explainable graded tuples, never scalar oracles | `BORP_REVITALIZATION_RISK` R7 (in-repo, 2026-10-13) | already decided | reinforced by §1: a calibrated distribution IS the graded tuple, machine-readable |
| **Calibration (ECE) as a rail**, not only accuracy | `decider`'s ECE/Decision-Index columns | **WORTH** | we publish no calibration number for any classifier; a `Noul` head is useless for a rail unless its probabilities are calibrated, and ECE is how that is checked |

### Skill orchestration
| item | source | verdict | what it fixes here |
| --- | --- | --- | --- |
| Small, composable, **model-agnostic** skill files with explicit invocation semantics | `mattpocock/skills` (`SKILL.md` + `agents/openai.yaml` per skill; the README states "they work with any model") | **SHOULD** | our skills live as prose in `agent/`; the intake shows a portable shape: one directory per skill, a `SKILL.md`, and a per-provider binding *beside* it — the C25 (agent-agnostic) rule made concrete |
| `diagnosing-bugs` (a bug-diagnosis skill) + `code-review` + `tdd` as **named, invocable procedures** | same repo | **WORTH** | this session's own need: "diagnose before you repair" is unstated practice here; BUG-778's mis-diagnosis is what happens without it |
| `.out-of-scope/` as a first-class directory (a written record of what was deliberately NOT built, with the reason) | same repo | **WORTH** | our equivalent is scattered across buglog "NOT DONE, DELIBERATELY" lines — one home would let a rail hold it |

### Harness / everyday scaffold
| item | source | verdict | what it fixes here |
| --- | --- | --- | --- |
| **A natural-language step that becomes a deterministic replay** — *"An agent step that a later assertion verifies records its actions, and the next run replays them with no model calls until the app changes"* | `tester-army/e2e` README | **MUST (this is the missing half of our rails)** | our rails are deterministic but a **fix** is re-derived by an agent every time. Recording the repair's actions once and replaying them (no model) is exactly the D-2861 "re-baseline as its own receipted act" pattern, generalised |
| Agent step + **assertion in the same test** (the assertion decides, the agent only drives) | `tester-army/e2e` | **MUST** | R5 (generator ≠ verifier) applied to *instrumentation*: today an agent both proposes and self-reports; the runner's model is one step, one independent assertion |
| Bring-your-own local model, incl. **no model at all** for the non-agent path | `tester-army/e2e` | **ADOPT (C1/C22)** | confirms local-first is a viable *test* posture, not a compromise |
| Mutation testing as a standing gate, seen to fire | already ours (D-2676) — and `mattpocock/skills` has a "prove-mutation" changeset | **KEEP** | the intake independently arrives at the rule we already enforce; the *harness defect* (BUG-778 limb c) is ours to fix |
| `topics/e2e-testing` + `topics/end-to-end-testing` feeds | owner request | **ADDED** to `feed.opml` 2026-10-14 | the harness axis now has a standing review feed (not for web QA — see the feed's own comment) |

### Future ambition / projects
| item | source | verdict |
| --- | --- | --- |
| A **decision head** as a first-class, swappable component (C21) with the generator path kept for prose | §1 | **WORTH→MUST after one measurement** |
| **Control-Barrier-Function "shield"** framing for guaranteeing an agent stays inside a declared safe set | community `Laya` work | **WORTH** — it is the formal name for what our "fail-closed + closed menu" already approximates; it would let a rail state the guarantee instead of testing for its violation |
| A public, re-derivable **decision benchmark** (a `JevBench` of our own: frozen FB states + typed questions + expected answers) | `decider`'s benchmark posture; our D2635 ARM-2 | **SHOULD** — we already have ARM-1/ARM-2 harnesses; a frozen, published benchmark with a majority baseline is what makes "6/6 vs 2/6" durable across model swaps |

---

## §3 — DEBUG FASTER AND CHEAPER (the owner's second question, answered from measured evidence)

The evidence for this is not opinion; it is **this session's own log plus the captured transcript**.

1. **The bottleneck was never bug-detection speed. It was that the instrument lied about scope.** `run_ladder
   --receipt-check` returns rc 2 (UNKNOWN): the recorded whole-set scan covers 128 declaring lines while the ladder now
   has 138, so every `just health` opens with UNKNOWN and then reports a PREFIX. **Cheapest fix in the whole
   programme: re-collect the receipt.** Cost: ~12 minutes, zero new code. Value: every subsequent run starts with a
   measured fault count.
2. **A wrong remedy costs more than a missing one.** BUG-778's table told the next agent that `check_store_columns`
   would go green with `--record`. It cannot — the rc=1 cause is a fatal store-shape drift owned by BUG-766.
   **Rule worth adopting (not yet a decision): a causal verdict in a register must name the fault CLASS that actually
   determines the exit code, and a re-record remedy may only be claimed where the fault class is OWNS-CENSUS.** That
   is how a session burns 40 minutes on a non-fix.
3. **Shard the hunt; give the falsifier a clean head.** From the captured transcript: one agent with the whole job in
   one context found 14→15→27 of 70 bugs, and *stopped when "the pile of what's left looks finished enough"*. The
   workflow — split into shards, each with an **empty** context, then every finding handed to a **fresh agent whose
   only job is to disprove it** — found 66, three times, for ~1.3M tokens over 3.5 minutes on a comparable codebase.
   Our mapping is direct and already half-built: `pipeline/parallel.py` (shard), R5 (fresh, independent verifier),
   `governance/*.jsonl` journals (results move between phases by FILE, never by an agent's memory).
4. **Typed decisions replace a whole class of debugging.** A generation that must be parsed can fail in a dozen ways
   (truncation, schema drift, off-menu tokens). A typed decision has **one** failure mode (a wrong probability), and
   that failure is *measurable* (ECE/accuracy), not *diagnosable*. This is the token-efficiency argument too: one
   forward pass, no decode loop, no retry-on-parse-error.
5. **Token economics of the above, explicitly:** today a repair session pays for (a) re-reading the registers, (b)
   re-deriving the fault set, and (c) discovering that a remedy does not apply. (a)+(b) collapse to the receipt; (c)
   collapses to the fault-class rule in (2); and the sharded hunt/n²-falsifier pattern spends tokens on *shards*
   (bounded, parallel) rather than on one growing context (unbounded, degrading — DELEGATE-002 in this repo measured
   exactly that collapse: 6.8→0.4 tok/s as an agentic context grew).

---

## §4 — PEER-REVIEWED / METHODOLOGICAL ADOPTIONS, ONE LINE EACH

1. **BoolQ (Clark et al., NAACL 2019, `N19-1300`)** — yes/no questions over naturally-occurring text are unexpectedly
   hard; **entailment-transfer beats paraphrase and extractive transfer**, and keeps helping even from BERT. → Adopt:
   (a) keep the NLI axis for our verifier; (b) publish a **majority baseline and a human ceiling** with every decision
   rail's accuracy; (c) when hardening, fine-tune *from entailment data*, not from QA data.
2. **20 Newsgroups (sklearn protocol page)** — a date-based train/test split, plus explicit filtering of headers and
   quoted text for "more realistic" training. → Adopt: a **temporal split** protocol for the taxonomy classifier and an
   explicit **leak filter** (title/keywords/source metadata) before evaluating body-level judgements.
3. **Calibration (ECE) + a public decision benchmark** (`decider`'s Decision Index / ECE columns) → Adopt: a
   `check_calibration.py`-shaped rail for any probability-emitting head, and a frozen in-repo decision benchmark.
4. **Source dependence / copy-collapse** and **pooled qrels (TREC)** — already named in
   `BORP_REVITALIZATION_RISK_20261013.md` §6 as "independence and relevance are SETS with ancestry, not COUNTS of
   names". This intake adds no contradiction and one confirmation (`decider` scores a *distribution over options*,
   which is a set-valued answer, not a scalar oracle).
5. **Control Barrier Functions** (community `Laya` work) → the formal framing for "the system cannot leave the safe
   set", i.e. a guarantee a rail can *state* rather than a violation it can only *detect*. WORTH, not owed.

---

## §5 — THE ROBUSTNESS QUESTION: is adopting any of this safe? (R1–R6)

| # | risk | control |
| --- | --- | --- |
| R1 | a new model becomes a SECOND home for a decision that already has one (D-2646) | the decision head is a **backend of the same declared rule** (like `stage1_5_*.py` backends), never a rival rule |
| R2 | vendor benchmark numbers adopted as facts | every adopted number is **re-measured here** (D-2635 precedent); the vendor's number is a hypothesis |
| R3 | a decision head starts GATING admission | the head may **measure and declare**; a gate needs an owner policy (T-118/R2 of the BORP doc) |
| R4 | a hunts-faster workflow floods the register with false findings | the adversarial falsifier phase is **mandatory**, and a survived finding is filed with its falsifier's verdict |
| R5 | the typed-decision path becomes a vendor lock-in | MLX + GGUF + Apache-2.0 + local weights; the interface (state + typed questions) is 40 lines and portable (C2/C4/C21) |
| R6 | `$0` marginal cost is broken by a 12B head | it is a **local forward pass** (C1); the memory budget is already declared (`delegate_model_budget` ~24 GB) and a 4B/2B head is GB-scale |

---

## §6 — STATE MACHINES AND `Laya` FOR THE KNOWLEDGE BASE (the owner's "primitives and non-principles")

**The distinction that decides the design:** a *primitive* question is **"what IS this?"** (a TYPE over a closed set — a
decision head's job). A *non-principle* is **"what is NOT established, and in what ORDER may things become true?"** — a
question about **transitions and absence**, which is precisely what a state machine exists to represent and what a
classifier cannot represent at all (a classifier has no edges).

**Where a state machine is genuinely the right instrument here (and largely already exists implicitly):**

| lifecycle | states it already has (implicit) | what declaring it as a machine buys |
| --- | --- | --- |
| **row lifecycle** | chunked → clustered → extracted → merged → verified (§S5) → committed → retrieved | D2625/D2630's "mark, never delete" is a **transition rule** stated in prose in ~6 places; a declared machine makes `QUARANTINE` a state with an allowed exit, and refuses an undeclared transition mechanically (the C16 form) |
| **corroboration** (D-2992/D-2993) | single-source → convergent → corroboration RAISED by a later independent source | T-120 ("a later independent source must be able to RAISE an existing row's corroboration") is **a missing transition**, not a missing field — the row lifecycle has no edge for it |
| **classification_status** (T-122) | CLEAN → (error found) → repaired | the column says CLEAN on 1,049 QUARANTINE rows because there is no declared state set at all |
| **decision records** | draft → proposed → accepted → active → superseded → archived | already a machine; `recompute_decision_summary` enforces it — the precedent that this works here |

**Where it is the WRONG instrument (state it, so the idea does not metastasise):** the *ontology* itself (disciplines,
domains, the taxonomy) is **not** a state machine — it is a set of answer spaces with declared members; modelling it as
states would be a category error and would mutate the taxonomy (the exact "progression must not mutate" risk). Likewise
the corpus is not a machine: a book has a lifecycle, a *claim* has an evidence set.

**Concrete, minimal proposal (WORTH, one pilot):** declare ONE machine — the **row lifecycle** — in
`config/row_lifecycle.yaml` (`states`, `transitions`, `who` may fire each, `evidence` required per transition), plus a
rail `scripts/check_row_lifecycle.py` asserting that every stored `status`/`classification_status` value is a DECLARED
state and that every state is reachable. That single act would (a) give T-122 and T-120 a home, (b) make BUG-766's
"which tier is this row in" a declared question, and (c) cost no model. `Laya`/`decider` then supplies the **labels**
for the transitions it can see (e.g. a `Noul` "is this the same voice?" head for T-119), never the machine itself.

---

## §7 — CANDIDATE ACTS THIS INTAKE CREATES (none minted here)

| # | act | kind | why now |
| --- | --- | --- | --- |
| A1 | **T-126** — typed-decision pilot on the S4 classifier role against the frozen ARM-2 benchmark | task | fixes a MEASURED defect (2/6 schema-valid) with a local, $0, MLX-compatible head |
| A2 | **T-127** — majority-baseline + human-ceiling for every decision rail (starting with the saturated T-101 ruler) | task | a number without a baseline/ceiling is the defect BoolQ's own protocol names |
| A3 | **D-candidate** — a fault-CLASS rule for register remedies (a re-record may be claimed only where the fault class is a census move) | decision | BUG-778's wrong remedy, this session |
| A4 | **T-128** — the row-lifecycle machine (§6 pilot) | task | gives T-120/T-122 a home; no model needed |
| A5 | **T-129** — an ECE/calibration rail for any probability-emitting component | task | precondition for A1 being more than a swap |
| A6 | the record-replay harness for repairs (§2, harness row) | task | the missing half of the ladder; needs a spec before code |

---

## §8 — WHAT THIS FILE DOES **NOT** CLAIM (blindspots, declared)

1. **Three of four videos were not transcribed** (HTTP 429/SABR on the subtitle endpoint, 4 client variants + 2
   third-party services). Only `2H0zj28ECak` is transcript-grounded. The claim about `Jev`/`Laya` rests on repo
   metadata and READMEs, not on the videos.
2. **The `mattpocock/skills` per-document digest FAILED** (the local delegate returned a decode error on a 226 KB
   read). The repo's tree, README and file names were read; the *content* of its `docs/engineering/*.md` is NOT
   represented above beyond the file names and the README's own claims. Re-run before acting on the "SHOULD" rows.
3. **No benchmark was reproduced.** Every vendor number (0.784, ECE 0.047, Decision Index 57.33, 66/70 bugs) is a
   quoted claim. R2 above is the control.
4. **`Laya`'s provenance is community metadata**, not a vendor page: the family identification is inference from
   co-occurrence in repo descriptions, and is stated as such.
5. **Nothing here is wired.** No config key, no rail, no model was changed by this file.
