# BOUNDARY DISCRIMINATORS + default_home SENTENCES — 2026-09-21

Status: **DRAFT for R5 review.** Nothing here is applied to the pipeline. Companion to
`MENU_REPAIR_QUEUE_20260921.md` (PART2 B) and `PART1_PART2_REISSUE_20260921.md` (the corrected
PART 1 / PART 2 reading).

Why this file exists: a 16-pair disagreement list is only actionable if each pair has a **test the
annotator can apply to a single sentence**, not a vibe. The queue already carries 16 drafted tests
(items 1–16). The re-issue showed the disagreement list is actually **26 pairs / 31 rows** — so 10
pairs have no test. Those 10 are drafted below, plus the `default_home` pattern.

---

## Part A — `default_home` sentences (one per discipline group)

`default_home` is the **tie-breaker, not a rule**. It is the answer to "if the sentence carries no
evidence for any finer slot, where does it live?" It exists because the dominant error mode on the
ruler is not a missing slot (Absence) and not a silent slot (Emission) but a **boundary** claim:
two slots both look like a home and the annotator picks the more famous one. A stated default makes
that pick **auditable and reversible** instead of tacit.

The already-established precedent is 'cognitive science': *the default home for any claim about
cognition is cognitive science, unless the claim is specifically about behaviour, affect or
clinical outcome — then it is psychology.*

| group | default_home sentence |
|---|---|
| design & visual arts | The default home for any claim about how a designed artefact is made, composed or read is **design & visual arts** — unless the claim is about a user's measured response to it (→ human & behavioural science) or about the machinery that renders it (→ computing, ai & information). |
| human & behavioral science | The default home for any claim about how people perceive, judge, feel or behave is **human & behavioral science** — unless the claim is about the mechanism of a market or an incentive (→ economics & business) or about meaning carried by signs (→ communication & media). |
| computing, ai & information | The default home for any claim about how a machine represents, learns, retrieves or secures information is **computing, ai & information** — unless the claim is about the economic or organisational consequence of that system (→ economics & business) or about the construction practice of shipping it (→ software engineering, inside this same group). |
| economics & business | The default home for any claim about resource allocation, incentive or organisational choice is **economics & business** — unless the claim is about the distribution of power and institutions that set the rules (→ political economy) or about a formal optimisation model (→ systems & operations). |
| communication & media | The default home for any claim about meaning, message, audience or framing is **communication & media** — unless the sign system is specifically visual (→ visual semiotics) or the claim is about how a message is produced as an artefact (→ design & visual arts). |
| systems & operations | The default home for any claim about feedback, stocks/flows, optimisation or method is **systems & operations** — unless the claim is about the knowledge-producing procedure itself (→ research methodology) or about downside exposure (→ risk management). |
| philosophy & law | The default home for any claim about norms, justification, obligation or what may be permitted is **philosophy & law** — unless the claim is about how a norm is actually enforced or breached in practice (→ economics & business / human & behavioural science). |
| engineering, math & physics | The default home for any claim about a mathematical structure, a physical constraint or a bounded engineering artefact is **engineering, math & physics** — unless the claim is about the digital system built on it (→ computing, ai & information). |
| life & health science | The default home for any claim about biological or clinical processes is **life & health science** — unless the claim is about a cognitive or behavioural mechanism with no clinical outcome (→ cognitive science / psychology). |
| interdisciplinary | **interdisciplinary** is the default home for a claim whose evidence is a deliberate crossing of two groups, and it is the home of last resort before `emerging` — never a first choice. |

Note the second half of each sentence: a `default_home` is only useful if it names the **escape
condition**. That is what makes it a discriminator rather than a bias.

---

## Part B — the 10 pairs with no drafted test

Format: `A vs B :: <test> => A ; <test> => B`. Each test is written to be applied to one sentence
of the source text, not to the label.

17. **cognitive science vs neuroscience** :: the claim is about a representation, computation or
    strategy (how information is processed) => cognitive science ; the claim is about a neural
    substrate, a measured brain signal or a lesion => neuroscience.
18. **operations research vs creative process** :: the claim has a formal objective to be optimised
    (cost, queue, schedule) => operations research ; the claim is about how an idea is generated,
    incubated or selected for novelty => creative process.
19. **motion & time vs human-computer interaction** :: the claim is about the temporal design of an
    artefact (timing, easing, sequence, pace) => motion & time ; the claim is about the interface
    mechanism through which a user acts (control, feedback, usability) => HCI.
20. **finance vs economics** :: the claim is about the valuation, pricing or allocation of capital
    instruments => finance ; the claim is about production, trade, markets or welfare in aggregate
    => economics.
21. **design psychology vs emerging** :: the claim is about a designer's or user's cognition,
    perception or affect **within a design activity** => design psychology ; the claim has no
    settled slot and is being parked => emerging (a label of last resort, never a first choice).
22. **artificial intelligence vs software engineering** :: the claim is about learning,
    representation or model behaviour => AI ; the claim is about latency, coupling, deployment or
    maintainability of the delivered system => software engineering.
23. **research methodology vs finance** :: the claim is about a method for producing or validating
    knowledge (sampling, design, validity, a detector applied to data) => research methodology ;
    the claim's object is a return, a price or a portfolio => finance.
    *This is the pair where the two tests are closest; the discriminator is the OBJECT of the
    claim, not the instrument used.*
24. **strategic thinking vs behavioral economics** :: the claim is about a deliberate choice of ends
    or positioning taken by an actor => strategic thinking ; the claim is about a systematic
    deviation of judgement from a rational benchmark => behavioral economics.
25. **psychology vs health & medicine** :: the claim is about a mental, affective or behavioural
    mechanism => psychology ; the claim is about a diagnosis, a treatment or a clinical outcome
    => health & medicine.
26. **behavioral economics vs psychology** :: the claim is framed by an incentive, a price or a
    choice under uncertainty => behavioral economics ; the claim is about affect, personality,
    development or clinical behaviour => psychology.
    ⛔ **REJECTED BY OWNER 2026-09-21** — the test never names BE's R1 (an *economic* object), so it
    fires on `cognitive science`, `psychology` and `decision making`, the three slots BE explicitly excludes.
    Corrected test: item 24′ in Part D.
    ⛔ **REJECTED BY OWNER 2026-09-21** — "incentive / price / choice under uncertainty" is `economics`
    (which BE excludes: it is the standard model BE deviates *from*), and the B side under-scopes `psychology`
    (whose definition includes social behaviour). Corrected test: item 26′ in Part D.

---

## Part C — one structural defect these tests expose

Several of the 26 pairs are **not symmetric**. `A vs B` in the sheet means "the human wrote A, the
pipeline stored B". A pair that is DIFFERENT is only *actionable* if the pipeline's choice is
identifiably worse than the human's on the same sentence:

* rows 25/26 (`behavioral economics vs psychology` and `psychology vs behavioral economics`) are the
  **same two slots in opposite directions** — a boundary rule drawn for one direction must be
  checked against the other, or the rule will be self-contradictory;
* rows 23 and 19 pair a *method* with an *object*. A rule phrased on the method's name will not
  converge; it will just move the disagreement to the next row.

Recommendation: adopt the `default_home` + escape-condition form above rather than per-pair name
rules, for exactly these asymmetric pairs. A name rule cannot be applied by a model; a stated
default with a stated escape can.

---

## Provenance (D-318)

| input | sha256 |
|---|---|
| governance/ANCHOR2_BLIND_SHEET_20260920.csv | `a91f9c859a998d4d27d7ce91939c4ccf4c23e3e9d20aa0cb34ccadcb294ee821` |
| governance/ANCHOR2_KEY_20260920.json | `20a4a437eab902fc703a210bad26b8d3220c7c2574852fb9b97b01baf567526c` |
| config/taxonomy_v5.yaml | `8d3c90e949ab1988e097c9fc58c80b6f4279477c9651436dddf4d8ffa91d3ae0` |
| config/closed_menu_v5.json (menu_hash) | `73597ee2b1bb1eb92edb08e743ffa0654c1e5994edcd3535d814c7942a89df6f` |

Not applied: these tests change no canonical, no `raw` list and no menu slot. They become binding
only if the owner rules them in and a later decision wires them into the classifier prompt.

---

## Part D — OWNER RULINGS 2026-09-21: items 24 and 26 REJECTED; `behavioral economics` re-read from the taxonomy

Owner: *"24: reject, 26: reject — both behavioural; behavioral economics is misunderstood"*. Both rejected
tests above are **struck, not deleted**, because the rejection is itself the evidence. What follows is the
terminology re-read that was asked for, done against the text of `config/taxonomy_v5.yaml` rather than from
memory, then the corrected tests.

### D.1 The definition of record (verbatim, `config/taxonomy_v5.yaml`)

> **behavioral economics** — *"The descriptive study of how psychological factors and cognitive biases cause
> systematic deviations from rational choice in economic decision-making and market behavior — where
> heuristics, framing, and affect change what people choose (prices, incentives, markets). It describes the
> bias; it does not exploit it to design persuasion."*
> `exclude`: `economics`, `psychology`, `cognitive science`, `design psychology`, `decision making`
> `raw`: `Behavioral Economics`, `behavioral economics`, `Behavioral Analysis`, `behavioral analysis`,
> `Consumer Behavior`, `behavioural economics` (group: human & behavioral science)

Three requirements are load-bearing. A test that drops one is not a BE test:

| # | requirement | what dropping it produces |
|---|---|---|
| **R1** | **object** — an *economic* decision: a price, a purchase, demand, an incentive response, a market outcome, willingness to pay | "any deviation from the rational model" → `cognitive science`, `decision making` |
| **R2** | **mechanism** — the cause is *psychological*: heuristic, framing, affect (and, in the nudging tradition, social norms / peer influence) | "incentive / price / uncertainty" is the vocabulary of `economics`, which BE **excludes** |
| **R3** | **stance** — *descriptive*: it explains the deviation, it does not prescribe how to exploit it | "how to persuade / sell" → `marketing & communications`, `design` |

### D.2 What was wrong with the two rejected tests

* **item 24** offered R2's *marker* alone ("a systematic deviation of judgement from a rational benchmark")
  and never named R1. It therefore fires on every bias claim, including the three slots BE excludes.
  Row 57 *Generous Audacious Marketing* ("the bold assertion that a better alternative exists and a
  willingness to lead users toward it… the audacity to communicate that vision") is a deliberate
  positioning claim with **no economic-decision object**; the pipeline answered `behavioral economics`,
  which is exactly the error an R1-less test predicts and cannot see.
* **item 26** offered "an incentive, a price or a choice under uncertainty" as the BE test — that is
  `economics` / `decision making`, i.e. the *standard model* BE deviates from (choice under uncertainty is
  expected-utility territory, the baseline, not the deviation). Its B side was also mis-scoped:
  `psychology` is defined as *"the empirical study of mind and behavior in individuals and groups —
  emotion, personality, development, **social behavior**, and mental health"*, so a test naming only
  affect/personality/clinical is **not** the complement of BE and silently re-routes social-behaviour
  claims.

### D.3 Corrected tests (definition-anchored; R-D410 — the rejected text above stands as evidence)

**24′. strategic thinking vs behavioral economics**
* a *deliberate* choice of ends or positioning by an organisational actor (vision, competitive position,
  long-horizon intent, how to win) ⇒ **strategic thinking**;
* *describes* how a psychological factor (heuristic, framing, affect, social influence) systematically
  moves an **economic** choice — price, purchase, demand, incentive response, market outcome — away from the
  standard/rational model ⇒ **behavioral economics**;
* a bias or framing claim with **no economic object** ⇒ **not BE** (`cognitive science` if the mechanism is
  computational/cognitive, `psychology` if it is behaviour/affect); a prescriptive "how to persuade" claim ⇒
  `marketing & communications` / `design`, never BE (R3).

**26′. behavioral economics vs psychology**
* an **economic object** (price, purchase, demand, incentive, market, willingness to pay) *plus* a
  psychological causal mechanism, described and not prescribed ⇒ **behavioral economics**;
* a mechanism claim about the mind or behaviour of individuals or groups with **no economic object**
  (emotion, personality, development, social behaviour, perception, judgement, mental health) ⇒
  **psychology**;
* an economic object with a standard/rational account and no psychological cause ⇒ **economics**;
  no economic object and no behaviour claim ⇒ **cognitive science**.

### D.4 The defect this exposes — the written definition is NARROWER than the operational denotation

`behavioral economics` has exactly **two** human rows on the frozen 60-row sheet:

| row | name | R1 (economic object) | R2 (psychological mechanism) | written definition says |
|---|---|---|---|---|
| 35 | Tv Advertising Consumer Behavior Pattern | present (perceived quality → purchasing decisions → demand) | present | **behavioral economics** ✔ |
| 60 | Same-age Peer Modeling | **absent** (influence → "behaviour or attitude change"; no price, purchase, demand or incentive anywhere) | present | `psychology` (social psychology) |

The owner's label for row 60 is `behavioral economics`, and the pipeline answered `psychology` — which is
precisely what the **definition string read literally licenses**. So this is not a boundary question and
not a typo: it is an **ontology (denotation) defect**, and no amount of boundary-rule wiring in the
classifier prompt can fix it, because the definition string *is* the prompt's evidence for BE.

Two ways out — the owner's call, and note that **neither moves a menu slot** (denotation, never spelling):

* **(i) Widen the definition string** *(recommended)*: name the mechanism class and the second object class,
  e.g. *"…in economic decision-making, market behaviour and behaviour-change interventions, where
  heuristics, framing, affect, social norms and peer influence change what people do (prices, incentives,
  markets, choice of behaviour). It describes the bias; it does not exploit it to design persuasion."*
  Keeps all five excludes. Matches 2/2 of the owner's BE rows and keeps the **object test** as the only
  discriminator that converges.
* **(ii) Keep the definition and re-label row 60** as `psychology` — honest to the written text, but then
  the sheet's BE class has one member and the nudge / social-norms family has no home in the menu.

Logged as **BUG-357**. Until the owner rules, 24′/26′ are *drafts*, and nothing is wired into any prompt.
