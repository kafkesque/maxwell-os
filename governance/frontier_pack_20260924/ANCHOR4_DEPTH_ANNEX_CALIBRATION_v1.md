# ANCHOR-4 DEPTH ANNEX — CLASS-1 CALIBRATION (CANDIDATES)
**Artifact ID:** `ANCHOR4_DEPTH_ANNEX_CALIBRATION_v1` · **schema_version:** 1.0 · **tier:** `annex-illustrative`
**Status:** `OWNER-CONFIRMED` (2026-09-25) — all four candidates ruled **universal, DEPTH (1-4) = 1**; the gold column is filled in the annex CSV.
**Date:** 2026-09-25 · **Owner gate:** C22 (no promotion write, no training) · **D274d** (no S4/depth-head training before the freeze)

---

## §0 Why this artifact exists (and why it is NOT four new rows in the 150)

Fact on the record: across the owner's reviewed 148 rows, depth class **1 (universal) is assigned ZERO times**. It is not that class 1 was never used — the owner's first blind pass assigned it **7 times** (R033, R049, R062, R085, R087, R101, R139) and then **retracted all 7** after seeing four independent coders (1→2 four times, 1→3 three times).

Two explanations remain unfalsified:
- **(a) the class-1 bar rises once disagreement is visible** — i.e. the definition is too loose to survive scrutiny; or
- **(b) universal genuinely does not occur among design-principle claims** — i.e. the class is empty and the axis is really 3-class.

An LLM coder cannot tell these apart without a reference. Hence this annex: **candidate class-1 principles, stated so they can be falsified by inspection**, with the 7 retracted rows kept alongside as the **negative set**.

Appending these to the 150 would move the denominator of every depth statistic (145/150 extraction_type, the 28% owner self-revision churn, 73/150 coder-owner plurality mismatch, F-11 comparisons, D274f test-retest scope) and would seed prevalence into a ruler whose whole value is that it was labelled blind. So the annex is a **separate versioned artifact, class-1 admissible, never scored, never trained**.

---

## §1 The scope test, and what a class-1 candidate must satisfy

From `config/depth_classes.yaml` (the only authority for this axis):

> measurable axis = **epistemic SCOPE**, never subject matter. Scope test: *would this claim survive substitution into a DIFFERENT field with no domain-specific change? Highest surviving scope wins.* Guards: **D282** (scope is the depth axis, never the content_type discriminator), **D2130** (the soft band informs, it does not decide). Band: universal `>=3 domains` · cross-domain `>=2` · domain `1..N adjacent` · specialized `1`. The menu is CLOSED.

A candidate earns class 1 only if **all three** hold:
1. **No domain noun survives** in the statement — nothing that only a designer, an engineer or a biologist could act on.
2. **Attested in >= 3 unrelated fields** by claims already in the corpus at *narrower* scope (a class-1 row should be the generalisation of rows we already hold).
3. **It is a falsifiable claim, not a method or a stance** — a procedure ("use X steps") is the thing the axis is *not* measuring.

---

## §2 The four candidates

### U001 — Iterative Feedback Refinement
- **Statement.** When the outcome of an act cannot be fully predicted from the plan, repeated *act → observe → correct* cycles reach a better result at equal total effort than one fully-specified attempt; the gain rises with how informative the observation is and falls with its delay and noise.
- **Application.** Wherever you can observe the result of what you just did before committing the next step, budget for repeat cycles instead of a better first plan — writing, surgery, engineering, logistics, research, strategy.
- **Mechanism.** Each cycle replaces prior uncertainty with evidence, so correction is applied to a *measured* gap rather than a predicted one and error does not accumulate.
- **Boundary.** Fails where feedback is unavailable, delayed past the decision horizon, or dominated by noise; fails where the cost of a cycle exceeds its information gain.
- **Scope test walked.** Nothing in the statement is field-bound: substitute surgery, music, logistics, science — it holds verbatim. **Survives → class 1.**
- **Attested at narrower scope in the 150:** R071 Iterative Design Validation · R059 Aesthetic Refinement Through Iteration · R010 Iterative Launch Process · R046 Cyclical Design Lifecycle · R069 Lean Startup Experimentation Framework · R139 Learning Through Failure Process (retracted from 1).
- **Honest weakness — what would make it FAIL:** it is the nearest to a tautology of the four; if the owner requires a claim that adds information beyond "use your observations", the correct landing is **class 2**, and the reason to record is *vacuous rather than cross-domain*.

### U002 — Proxy Decay (the measure becomes the target)
- **Statement.** When a proxy is optimised as if it were the goal, effort migrates to the proxy and the proxy's correlation with the goal decays; decay is faster the cheaper the proxy is to move.
- **Application.** Before adopting any metric as a target, ask how it can be moved without moving the underlying goal, and expect that move.
- **Mechanism.** Agents optimise what is observed and rewarded, not what is intended; the map becomes the territory once the map is rewarded.
- **Boundary.** Holds where the proxy *is* the goal, or where the gap is measured continuously and re-anchored.
- **Scope test walked.** Education (test scores), medicine (wait times), science (publication counts), finance (return targets), software (lines of code) — no change needed. **Survives → class 1.**
- **Attested at narrower scope in the 150:** R090 Measurable Outcome Focus · R051 Methodological Accountability · R061 Falsifiable Variable Measurement · R080 Data Quality and Method Transparency in Journalism.
- **Honest weakness — what would make it FAIL:** it is *received law* (Goodhart / Campbell), and it presupposes incentive-responsive agents — a social-science premise. If the owner reads that premise as a domain import, the landing is **class 2**.

### U003 — Constraint–Originality Inversion
- **Statement.** Bounding the space of admissible moves in a generative task raises the value of the result, because the bound collapses the search and forces recombination of what remains; the relation inverts once the bound leaves no admissible move.
- **Application.** When output is generic, add constraints rather than options; when output is dead, loosen them.
- **Mechanism.** Search-space collapse plus forced recombination; an inverted-U between freedom and result quality.
- **Boundary.** Tightness beyond feasibility; and tasks whose value is coverage rather than resolution.
- **Scope test walked.** Engineering design envelope, music form, poetic metre, constrained models in science — the *mechanism* survives; but the success measure named is "value of the result", and in science that is truth, in business profit. **Survives only if "value" stays generic.**
- **Attested at narrower scope in the 150:** R048 Creative Process Through Drawing and Sketching · R035 Negative Space Alphabet Challenge · R044 Alpha State Thinking and Creative Problem-solving · R029 Innovation Through Challenge to Assumptions (*name-level citation, to be row-verified before any promotion*).
- **Honest weakness — what would make it FAIL:** if the claim cannot be stated without importing a *creativity/originality* success measure, it is arts-bound and the landing is **class 2**. This is the most likely of the four to be rejected — and the most instructive rejection.

### U004 — Relative-Difference (Contrast) Law of Evaluation
- **Statement.** Perception, attention and preference respond to the difference between a stimulus and its local comparison frame, not to its absolute magnitude; the same absolute value is therefore judged good or bad by its frame.
- **Application.** To change how something is judged, change the frame or the neighbours, not only the absolute value.
- **Mechanism.** Judgement is computed against a local reference; the reference, not the stimulus, sets the sign of the evaluation.
- **Boundary.** Fails where an external absolute reference is enforced — calibrated instruments, published standards, legal thresholds.
- **Scope test walked.** Vision, pricing, typography, survey design, music, negotiation — holds. **Survives → class 1.**
- **Attested at narrower scope in the 150:** R127 Visual Hierarchy Through Contrast (2) · R064 Optical Alignment in Typography · R036 Color and Typography Readability · R084 Symbolic Meaning Through Consumption · R104 Choice Architecture and Identity Framing.
- **Honest weakness — what would make it FAIL:** it imports a perceptual/psychological mechanism, i.e. a domain premise. A strict reader lands it at **class 2** for that reason alone.

---

## §3 The negative set — the 7 rows whose class-1 was retracted

| item | name | drop-in DEPTH | retracted to | owner domains count | primary domain |
|---|---|---|---|---|---|
| R033 | Postmodern Critique of Realist Assumptions | 1 | **2** cross-domain | 2 | social sciences |
| R049 | Fermi Estimation Method | 1 | **2** cross-domain | **5** | research & methodology |
| R062 | Somatic Marker Decision Making | 1 | **2** cross-domain | 3 | marketing & communications |
| R085 | Discursive Strategy Abstraction | 1 | **3** domain | 1 | arts & culture |
| R087 | In-group Identity and Social Bonding | 1 | **3** domain | 2 | social sciences |
| R101 | Pragmatist View of Truth and Knowledge | 1 | **3** domain | 1 | social sciences |
| R139 | Learning Through Failure Process | 1 | **2** cross-domain | 2 | education |

**What the negative set teaches (and why it is worth keeping in the family):**
- **R049 is the band falsifier.** Five domains listed — the widest count in the whole review — yet the owner graded it **cross-domain (2)**. Under the declared soft band that row "should" have been universal. **This is D2130 in the data**: the band informs, it does not decide.
- **R139 is the positive near-miss.** "Learning through failure" is the same mechanism as U001 in a narrower statement — retracted to 2. If the owner accepts U001 as class 1, R139 becomes the worked example of the *scope* difference between a universal claim and its cross-domain instance.
- **R085 / R101 are methodological/philosophical and land at 3**: the retraction is not "the class-1 bar got stricter", it is **scope discipline** — a stance about knowledge is a domain-scoped claim about knowledge.
- Six of the seven retractions are 4 coders disagreeing *upward* (1→2/1→3). That is consistent with explanation **(a)**: the bar rises when disagreement becomes visible.

---

## §4 Owner ruling slots (one word per row, no work)

For each of U001–U004, the owner fills exactly one:

| verdict | meaning | what I do downstream |
|---|---|---|
| `KEEP-CLASS1` | the claim is universal | write **1** into that row's `DEPTH (1-4)` in the annex CSV; the row becomes the class-1 reference for rubric review; **no change to the scored 150** |
| `NOT-UNIVERSAL <class>` | name the class it is (2/3/4) | write that class + append the reason line from §2 ("what would make it FAIL") to the annex as a worked boundary example |
| `DROP-ROW` | not a claim / not usable | remove the row from the annex, keep it in the record as a withdrawn candidate |

The 7 negatives need no ruling — they are already ruled, and they are recorded here for exactly that reason.

**If any candidate is `KEEP-CLASS1`,** the depth axis keeps **4 classes**, and class 1 acquires the reference examples the LLMs were missing. **If all four are rejected,** that is the strongest available evidence for explanation **(b)**: declare the depth axis **3-class**, delete class 1 from the head's output space (D2577 4-way head → 3-way), and say so in the promotion write.

---

## §5 What this artifact deliberately does NOT do

- **No change to the 150.** The scored ruler keeps its denominator; regression against F-11, D274f and the 28% stability floor stays comparable.
- **Not wired into the frontier rubric yet.** `governance/frontier_pack_20260924/taxonomy_domain_depth.md` is NOT amended by this annex: seeding class-1 examples into the coder instruction mid-experiment would change coder behaviour and destroy the comparability of the 4-coder cross-exam. Wiring happens only on the owner's verdict.
- **Never trained on.** **D274d** forbids S4 / depth-head training on current labels before the anchor freezes; `annex-illustrative` rows are excluded from any train set permanently, not just now.
- **Never scored.** Not a ruler row, not a gold row; `tier: annex-illustrative`.

## §6 Honest risk statement (recorded deliberately)

Authoring candidate universals *after* seeing the gold is the exact mechanism by which a measurement instrument starts producing the answer it was built to test — prevalence seeding. It is admissible **only** because the annex is a **rubric-calibration artifact, not a ruler row**: the prevalence of class 1 must still be measured **blind**, on the frozen held-out block, with the frontier pair asked only *"does class 1 appear, unprompted?"*. If that blind run finds class 1, the class lives. If it does not, the four examples here were good rubric material and the axis is 3-class.

---

**Files:** annex rows `governance/frontier_pack_20260924/ANCHOR4_DEPTH_ANNEX_CAL1_v1.csv` · declaration `config/anchor4_depth_annex.yaml`
**Negative-set source of truth:** `governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` (sha256 bc1cc956…, sealed) + `governance/anchor_adjudication_workbook_20260924.csv` (owner rev 2)

---

## §7 RULING RECORDED (2026-09-25)

**Owner, verbatim:** *"agree with those 4 theyare universal"*

| row | candidate | owner verdict | DEPTH (1-4) written |
|---|---|---|---|
| U001 | Iterative Feedback Refinement | universal | **1** |
| U002 | Proxy Decay (the measure becomes the target) | universal | **1** |
| U003 | Constraint-Originality Inversion | universal | **1** |
| U004 | Relative-Difference (Contrast) Law of Evaluation | universal | **1** |

**Consequences, in order of weight:**
1. **Explanation (a) is the one that holds.** The class-1 bar was too loose to survive scrutiny, not empty: universal is *reachable* in this corpus once the claim is stated without a domain noun. The 3-class fallback is **dead** — the depth axis keeps **4 classes** and the D2577 head stays **4-way**.
2. **Class 1 now has a reference set**, which is the whole reason this annex exists and the reason it is *not* inside the 150.
3. **The retraction of the 7 stands and is now explained.** R049 (five domains, graded 2), R085/R101 (domain-scoped stances about knowledge), R139 (the cross-domain instance of U001) are the boundary cases that show *where* the class-1 bar sits: U001 is what R139 becomes once the field noun is removed.
4. **Prevalence is still measured, not assumed.** The blind held-out run stays owed and is unchanged in design: the frontier pair on the frozen 58 rows, asked only whether class 1 appears unprompted. The annex is calibration material, so the run that produced the 4-coder cross-exam stays comparable — the coder rubric is **not** amended mid-record.
5. **Confidence not recorded.** The owner ruled acceptance, not a certainty level, so `conf_depth` is left blank on these rows rather than invented (nothing is fabricated into a gold column, ever).
6. **Still never trained** (D274d) and **still not a ruler row**: `tier: annex-illustrative`, `scored: false`, no denominator change. The 150 keep their 28% stability floor, their 145/150 extraction_type and their F-11 comparability.
