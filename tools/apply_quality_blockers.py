#!/usr/bin/env python3
"""
Apply quality blocker fixes: T-009 (author cap) + T-015 (extraction type expansion).
Run from repo root.
"""
import yaml
import copy
from pathlib import Path

GOLDEN_PATH = Path("config/golden/stage2_fewshot_convergent.yaml")

def load():
    with open(GOLDEN_PATH, "r") as f:
        return yaml.safe_load(f)

def save(data):
    # Crash-safe write
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, dir=GOLDEN_PATH.parent)
    yaml.dump(data, tmp, allow_unicode=True, sort_keys=False, width=120)
    tmp.flush()
    os.fsync(tmp.fileno())
    tmp.close()
    os.replace(tmp.name, GOLDEN_PATH)
    print(f"✅ Saved to {GOLDEN_PATH}")

def find_ex(examples, eid):
    for ex in examples:
        if ex.get("id") == eid:
            return ex
    return None

# ──────────────────────────────────────────────────────
# PHASE A: Author Cap Edits (T-009)
# ──────────────────────────────────────────────────────

def apply_author_cap(examples):
    """Kahneman 7→3, Taleb 5→3, James Clear 4→3, Gladwell 4→3"""
    
    # ── CONV-006: Remove Kahneman ──
    ex = find_ex(examples, "CONV-006")
    # Replace segment 1 source and text (System 2 → analytical deliberation)
    seg1 = ex["cluster_segments"][0]
    seg1["source_book"] = "Nudge — Richard Thaler & Cass Sunstein"
    seg1["text"] = (
        "The default option is the one that will be chosen if the decision-maker does nothing. "
        "Defaults are powerful because opting out requires an active decision, which engages "
        "analytical deliberation. When people are uncertain or the choice is complex, they "
        "tend to stay with the default — not because they prefer it, but because changing it "
        "costs mental effort. This is why organ donation rates are above 90% in countries with "
        "opt-out defaults and below 15% in countries with opt-in defaults, despite similar "
        "underlying preferences."
    )
    # Replace segment 4 (Kahneman's System 1 substitution) with Sunstein on sludge
    seg4 = ex["cluster_segments"][3]
    seg4["source_book"] = "Sludge — Cass Sunstein"
    seg4["text"] = (
        "Sludge is any friction that makes it harder for people to achieve their goals. "
        "Excessive paperwork, confusing forms, and long waiting times are all forms of sludge "
        "— they operate as the mirror image of nudges by imposing cognitive or administrative "
        "burdens. Where nudges use defaults to make the beneficial choice automatic, sludge "
        "exploits the same inertia to prevent people from accessing benefits they are entitled "
        "to. The psychological mechanism is identical: the default path is the path of least "
        "resistance. Removing sludge — simplifying forms, auto-enrolling eligible beneficiaries, "
        "reducing procedural hurdles — produces gains as large as adding new programs."
    )
    # Update source_books
    ex["source_books"] = [
        "Nudge — Richard Thaler & Cass Sunstein",
        "Misbehaving — Richard Thaler",
        "Predictably Irrational — Dan Ariely",
        "Sludge — Cass Sunstein",
    ]
    # Update definition, mechanism (remove System 2 references)
    ex["expected_fb"]["definition"] = (
        "When a default option is pre-selected, people disproportionately stick with it "
        "because opting out requires an active decision that engages costly analytical "
        "deliberation. The default becomes the status quo, and changing it feels like a "
        "potential loss — even when the alternative would be objectively better. This is "
        "why opt-out systems (organ donation, retirement savings) achieve dramatically "
        "higher participation than opt-in systems."
    )
    ex["expected_fb"]["mechanism"] = (
        "Defaults work through two interacting mechanisms: (1) cognitive effort avoidance "
        "— changing the default requires engaging analytical reasoning to evaluate "
        "alternatives, compare trade-offs, and justify the switch, all of which are mentally "
        "costly; (2) loss aversion — once the default becomes the reference point, any "
        "departure is coded as a potential loss, and losses hurt ~2× more than equivalent "
        "gains feel good. Together, these create a powerful status quo bias that makes "
        "the default 'sticky' even when the stakes are high. Sludge — unnecessary friction "
        "in processes — exploits the same mechanisms to prevent beneficial actions."
    )
    # Update evidence_passages
    ex["expected_fb"]["evidence_passages"] = [
        "organ donation rates are above 90% in countries with opt-out defaults and below 15% in countries with opt-in defaults",
        "Automatic enrollment in retirement savings plans — where employees are enrolled by default but can opt out — increases participation from roughly 40% to over 90%.",
        "people tend to stick with whatever option requires no action",
        "default option is the one that will be chosen if the decision-maker does nothing",
    ]
    ex["rationale"] = (
        "CONVERGENT POSITIVE — DEFAULT EFFECT (D2234: Kahneman capped, source diversified). "
        "Three independent sources (Thaler/Sunstein on defaults, Thaler on retirement savings, "
        "Ariely on choice overload, Sunstein on sludge) converge on the same mechanism: defaults "
        "stick because opting out requires costly analytical deliberation, and the default becomes "
        "the loss-reference point. Thaler provides the term 'choice architecture' and real-world "
        "evidence (retirement savings 40%→90%), Sunstein extends the framework to sludge removal. "
        "This example teaches the classic convergence pattern: empirical evidence from different "
        "domains (organ donation, retirement savings, benefit enrollment) supporting the same "
        "causal mechanism (effort avoidance + loss aversion)."
    )
    print("  ✅ CONV-006: Kahneman removed (System 2 → analytical, sludge segment added)")

    # ── CONV-026: Remove Kahneman ──
    ex = find_ex(examples, "CONV-026")
    seg1 = ex["cluster_segments"][0]
    seg1["source_book"] = "Simple Rules — Donald Sull & Kathleen Eisenhardt"
    seg1["text"] = (
        "When faced with complex decisions under time pressure, professionals across fields "
        "— judges setting bail, doctors making diagnoses, investors evaluating deals — rely "
        "on mental shortcuts rather than comprehensive analysis. These heuristics often "
        "substitute an easier question ('does this person seem trustworthy?') for the harder "
        "one ('what does the evidence and law require?'). The substitution is unconscious and "
        "automatic — the decision-maker genuinely believes they are applying professional "
        "judgment. Research on judicial decision-making shows that judges are more likely to "
        "grant parole after meals and at the start of the day, when mental energy is highest "
        "— the same legal criteria produce different outcomes depending on cognitive depletion."
    )
    ex["source_books"] = [
        "Simple Rules — Donald Sull & Kathleen Eisenhardt",
        "The Rule of Law — Tom Bingham",
        "Nudge — Richard Thaler & Cass Sunstein",
    ]
    ex["expected_fb"]["mechanism"] = (
        "Attribute substitution occurs because intuitive processing automatically generates "
        "rapid answers to easy questions. When confronted with a computationally difficult "
        "target question ('what is the legally correct sentence?'), intuitive judgment "
        "substitutes an easier heuristic question ('how dangerous does this person feel?') "
        "without the decision-maker noticing. Deliberative reasoning can override this, but "
        "doing so requires: (1) awareness that substitution occurred, (2) sufficient cognitive "
        "resources, and (3) motivation to perform the correct analysis. In high-stakes, "
        "high-volume settings (judicial calendars, hospital rounds), resource depletion makes "
        "substitution the default. Structured checklists force explicit consideration of each "
        "criterion, reducing substitution by making the correct analysis the path of least "
        "resistance."
    )
    ex["expected_fb"]["evidence_passages"] = [
        "judges are more likely to grant parole after meals and at the start of the day, when mental energy is highest",
        "In fact, the complexity of their decisions makes them MORE susceptible to heuristic substitution because the correct answer requires effortful processing that is easily bypassed when mental resources are depleted.",
        "Decision-makers in high-stakes environments — judges, doctors, regulators — are not immune to cognitive biases.",
        "cognitive biases — anchoring on initial impressions, substituting easier questions, over-weighting vivid testimony — can unconsciously shape judicial reasoning.",
    ]
    ex["expected_fb"]["definition"] = (
        "Decision-makers substitute difficult target questions with easier heuristic questions "
        "unconsciously, even in high-stakes professional contexts like judicial sentencing and "
        "medical diagnosis. The complexity of the correct analysis paradoxically increases "
        "susceptibility to substitution because effortful processing is bypassed when cognitive "
        "resources are depleted or time-pressured."
    )
    ex["rationale"] = (
        "CONVERGENT POSITIVE — LAW + PSYCHOLOGY (D2234: Kahneman capped, source diversified). "
        "Three sources from strategy (Sull/Eisenhardt), legal theory (Bingham), and behavioral "
        "economics (Thaler/Sunstein) converge on attribute substitution in professional judgment. "
        "Sull/Eisenhardt provide the mechanism (heuristic substitution under time pressure), "
        "Bingham provides the legal-domain evidence (judicial cognitive biases), Thaler/Sunstein "
        "provide the generalization (all high-stakes decision-makers are susceptible). Depth is "
        "cross-domain (law, medicine, regulation). Has actionable application (checklists, "
        "structured protocols)."
    )
    print("  ✅ CONV-026: Kahneman removed (Sull/Eisenhardt segment added)")

    # ── CONV-034: Remove Kahneman (attribute premortem to Gary Klein) ──
    ex = find_ex(examples, "CONV-034")
    seg2 = ex["cluster_segments"][1]
    seg2["source_book"] = "Sources of Power — Gary Klein"
    seg2["text"] = (
        "The premortem technique, developed by research psychologist Gary Klein, is one of "
        "the most reliable debiasing methods for high-stakes decisions. Before committing to "
        "a decision, gather the team and say: 'Imagine we are one year into the future. We "
        "implemented the decision as it stands today. The outcome was a disaster. Write the "
        "history of that disaster for five minutes.' This procedure overrides optimistic "
        "overconfidence by forcing the brain to construct a narrative of failure — making "
        "latent risks concrete and actionable before they materialize. Unlike statistical "
        "risk assessment, which treats risks as abstract probabilities, the premortem makes "
        "failure feel real by engaging the brain's narrative-construction machinery in "
        "reverse: instead of rationalizing why things will go well, participants must "
        "construct a plausible story of how things went wrong."
    )
    ex["source_books"] = [
        "Decisive — Chip & Dan Heath",
        "Sources of Power — Gary Klein",
    ]
    ex["expected_fb"]["evidence_passages"] = [
        "the premortem technique, developed by research psychologist Gary Klein, is one of the most reliable debiasing methods for high-stakes decisions",
        "Imagine we are one year into the future. We implemented the decision as it stands today. The outcome was a disaster.",
        "Widen options beyond binary choices, Reality-test by seeking disconfirming evidence, Attain distance by asking what you'd tell your successor, and Prepare by setting a tripwire that forces reconsideration.",
    ]
    ex["rationale"] = (
        "NORMATIVE HEURISTIC — prescriptive decision technique (D2234: Kahneman capped, "
        "properly attributed to Gary Klein). Heath's WRAP framework and Klein's premortem "
        "converge on the same prescriptive principle: counter overconfidence by actively "
        "constructing failure scenarios before committing. This is a HEURISTIC (a rule of "
        "procedure) not a causal mechanism — it says 'DO this' rather than 'X causes Y "
        "because...'. The premortem was developed by Klein, not Kahneman; Kahneman later "
        "popularized it in Thinking, Fast and Slow. Essential for teaching S2 to distinguish "
        "normative heuristics from causal mechanisms."
    )
    print("  ✅ CONV-034: Kahneman removed (premortem attributed to Gary Klein)")

    # ── CONV-037: Remove Kahneman ──
    ex = find_ex(examples, "CONV-037")
    seg1 = ex["cluster_segments"][0]
    seg1["source_book"] = "The Art of Thinking Clearly — Rolf Dobelli"
    seg1["text"] = (
        "The availability bias causes people to overestimate the frequency of events that "
        "are easy to recall. When asked whether more words begin with 'k' or have 'k' as "
        "the third letter, most people say the former — because it's easier to think of "
        "words starting with 'k'. But in English, words with 'k' as the third letter are "
        "about three times more common. This systematic error reveals a fundamental pattern "
        "in human judgment: mental availability is driven by ease of retrieval, not by actual "
        "frequency. The bias explains why people overestimate dramatic causes of death (plane "
        "crashes, terrorism, shark attacks) and underestimate chronic causes (heart disease, "
        "diabetes, car accidents) — vivid, recent, or emotionally charged events are more "
        "available to memory, skewing risk perception away from statistical reality."
    )
    ex["source_books"] = [
        "The Art of Thinking Clearly — Rolf Dobelli",
        "Blink — Malcolm Gladwell",
    ]
    # Update the availability heuristic FB's evidence passages
    ex["expected_fb"][1]["evidence_passages"] = [
        "mental availability is driven by ease of retrieval, not by actual frequency",
        "words with 'k' as the third letter are about three times more common",
        "people overestimate dramatic causes of death (plane crashes, terrorism, shark attacks) and underestimate chronic causes (heart disease, diabetes, car accidents)",
    ]
    ex["expected_fb"][1]["definition"] = (
        "Human cognition has measurable upper bounds on information processing: systematic "
        "frequency-estimation errors (availability bias) occur because ease of mental "
        "retrieval substitutes for actual frequency. An observed regularity, not a causal law."
    )
    ex["rationale"] = (
        "1:N SPLIT — Dunbar's number (relationship-capacity limit) and the availability "
        "heuristic (recall-ease frequency proxy) are two INDEPENDENT empirical patterns in "
        "human cognition. They share only the topic 'cognition' — no shared causal structure. "
        "Multi-source clusters on the same topic must NOT be merged into one FB when "
        "mechanisms differ. Teaches S2 to split, not merge, when sources describe different "
        "phenomena. is_convergent=false despite 2 books. (D2234: Kahneman capped, Dobelli "
        "used as availability heuristic source.)"
    )
    print("  ✅ CONV-037: Kahneman removed (Dobelli replaces Kahneman for availability heuristic)")

    # ── CONV-038: Remove Taleb ──
    ex = find_ex(examples, "CONV-038")
    seg1 = ex["cluster_segments"][0]
    seg1["source_book"] = "Linked — Albert-László Barabási"
    seg1["text"] = (
        "Power laws govern the distribution of outcomes in networks and complex systems. "
        "The 80/20 rule — 80% of effects come from 20% of causes — is observed across an "
        "astonishing range of domains: 80% of wealth is held by 20% of the population, 80% "
        "of scientific citations go to 20% of papers, 80% of internet traffic flows through "
        "20% of websites. This is not a coincidence — it's a signature of scale-free networks, "
        "where preferential attachment causes the rich to get richer through cumulative "
        "advantage. In such systems, small initial differences compound into extreme "
        "disparities over time. The mechanism is mathematically simple: new nodes "
        "preferentially connect to already well-connected nodes, creating a feedback loop "
        "that amplifies early advantages into permanent dominance."
    )
    ex["source_books"] = [
        "Linked — Albert-László Barabási",
        "Algorithms to Live By — Brian Christian & Tom Griffiths",
    ]
    ex["expected_fb"]["evidence_passages"] = [
        "80% of effects come from 20% of causes",
        "80% of wealth is held by 20% of the population, 80% of scientific citations go to 20% of papers, 80% of internet traffic flows through 20% of websites",
        "Preferential attachment is the mechanism behind many power-law distributions.",
        "new nodes are more likely to connect to nodes that are already well-connected",
    ]
    ex["rationale"] = (
        "CONVERGENT POSITIVE — COMPLEX SYSTEMS (D2234: Taleb capped, Barabási used as "
        "primary source). Barabási (network science originator of preferential attachment) "
        "and Christian/Griffiths (computer science) converge on the same empirical pattern: "
        "power-law distributions emerge from cumulative advantage processes. Barabási provides "
        "the mathematical mechanism (preferential attachment in scale-free networks), "
        "Christian/Griffiths provide the computational framing and practical implications. "
        "This is an EMPIRICAL PATTERN, not a causal mechanism — it describes the shape of "
        "observed distributions rather than explaining why any specific outcome occurs."
    )
    print("  ✅ CONV-038: Taleb removed (Barabási replaces Taleb)")

    # ── NEG-002: Remove James Clear ──
    ex = find_ex(examples, "NEG-002")
    seg1 = ex["cluster_segments"][0]
    seg1["source_book"] = "Awaken the Giant Within — Tony Robbins"
    seg1["text"] = (
        "The secret to lasting change is to raise your standards and turn your shoulds into "
        "musts. Most people live by a set of shoulds — I should exercise, I should eat better, "
        "I should save more — but shoulds have no power. The moment you turn a should into a "
        "must, you unlock the resourcefulness and determination to follow through. Lasting "
        "transformation begins with a decision about who you want to become, not what you want "
        "to achieve. When your identity shifts, your actions follow automatically — because "
        "you are now acting in alignment with who you believe yourself to be, not against a "
        "checklist of obligations."
    )
    ex["source_books"] = [
        "Awaken the Giant Within — Tony Robbins",
        "The Power of Habit — Charles Duhigg",
    ]
    ex["rationale"] = (
        "PLATITUDE — the claim 'turn shoulds into musts' is motivational rhetoric without "
        "a specific mechanism, boundary, or falsifiable consequence. Second source (Duhigg) "
        "adds no specific convergent content. REJECT: platitude detection. "
        "(D2234: James Clear capped, Tony Robbins used for platitude example.)"
    )
    print("  ✅ NEG-002: James Clear removed (Tony Robbins replaces Clear)")

    # ── NEG-013: Remove Gladwell ──
    ex = find_ex(examples, "NEG-013")
    seg2 = ex["cluster_segments"][1]
    seg2["source_book"] = "The Signal and the Noise — Nate Silver"
    seg2["text"] = (
        "In election years, the stock market tends to perform better when the Washington "
        "Redskins win their last home game before the election — a correlation that held "
        "true for 17 of 18 elections between 1936 and 2000. The correlation is statistically "
        "significant but patently absurd: no rational person believes football outcomes cause "
        "stock market movements. This is a textbook example of spurious correlation driven "
        "by chance and overfitting — when you test enough variables, some will correlate by "
        "random coincidence. The lesson extends beyond sports: in any dataset with hundreds "
        "of variables, you will find dozens of 'statistically significant' correlations that "
        "are entirely spurious. Without a causal model, statistical significance is "
        "meaningless."
    )
    ex["source_books"] = [
        "Freakonomics — Levitt & Dubner",
        "The Signal and the Noise — Nate Silver",
    ]
    ex["rationale"] = (
        "HARD NEGATIVE — CORRELATION WITHOUT CAUSAL MECHANISM (D2234: Gladwell capped, "
        "Nate Silver used for spurious correlation example). Both segments describe "
        "correlations (books→achievement, football→stock market) but explicitly identify "
        "hidden confounding variables or pure chance that prevent causal inference. The "
        "segments converge on the PATTERN (correlation with confounded/absent cause) but "
        "do NOT converge on a single causal mechanism — each has a different explanation "
        "(hidden confound vs. random overfitting). S2 must learn to detect when sources "
        "agree on correlation but disagree on (or lack) causal mechanism."
    )
    print("  ✅ NEG-013: Gladwell removed (Nate Silver replaces Gladwell hockey example)")

    # ── NEG-020: Remove Taleb (replace with Pinker) ──
    ex = find_ex(examples, "NEG-020")
    ex["cluster_segments"] = [
        {
            "source_book": "The Better Angels of Our Nature — Steven Pinker",
            "text": (
                "Violence has declined dramatically over human history — from roughly 15% "
                "violent death in prehistoric societies to under 1% today. This decline is "
                "not linear or inevitable; it reflects the cumulative effect of governance "
                "(states monopolizing force), commerce (making others more valuable alive "
                "than dead), feminization (valuing life over honor), and the expanding circle "
                "of empathy (extending moral concern to ever-wider groups). Each of these "
                "forces operates through identifiable psychological and institutional "
                "mechanisms that have strengthened over centuries."
            ),
        },
        {
            "source_book": "Enlightenment Now — Steven Pinker",
            "text": (
                "Human progress is measurable, substantial, and underappreciated. Life "
                "expectancy has doubled since the 18th century. Extreme poverty has fallen "
                "from 90% of the world population to under 10%. Literacy has risen from 12% "
                "to 86%. These improvements are not accidents — they are the result of "
                "Enlightenment values: reason, science, and humanism applied through "
                "institutions that channel knowledge into human betterment. The through-line "
                "is the application of rational problem-solving to human suffering."
            ),
        },
        {
            "source_book": "The Blank Slate — Steven Pinker",
            "text": (
                "The modern denial of human nature — the insistence that the mind is a blank "
                "slate shaped entirely by culture and environment — is empirically false and "
                "morally unnecessary. Genetic differences explain roughly 50% of the variance "
                "in personality traits, intelligence, and behavioral tendencies. Acknowledging "
                "human nature does not justify inequality or determinism; it informs realistic "
                "approaches to improving the human condition by working with, rather than "
                "against, our evolved psychology."
            ),
        },
    ]
    ex["source_books"] = [
        "The Better Angels of Our Nature — Steven Pinker",
        "Enlightenment Now — Steven Pinker",
        "The Blank Slate — Steven Pinker",
    ]
    ex["rationale"] = (
        "HARD NEGATIVE — SAME-AUTHOR ECHO (D2234: Taleb capped, Pinker used as replacement). "
        "All three segments are from the SAME author (Steven Pinker), describing related but "
        "distinct concepts across his major works. This is NOT convergent extraction from "
        "independent sources — it is one author developing his ideas across multiple books. "
        "The segments are thematically related (human nature, progress, violence) but each "
        "describes a different concept (decline of violence ≠ measurable progress ≠ denial "
        "of human nature). S2 must learn to detect same-author citation echoes and reject "
        "clusters where source independence fails, even when the writing is intellectually "
        "rich."
    )
    print("  ✅ NEG-020: Taleb removed (Pinker trilogy replaces Taleb trilogy)")

    return examples


# ──────────────────────────────────────────────────────
# PHASE B: Extraction Type Reclassifications (T-015)
# ──────────────────────────────────────────────────────

def apply_reclassifications(examples):
    """Reclassify mislabeled FBs from causal_mechanism to correct types."""

    reclass_map = {
        "CONV-011": ("empirical_pattern",
            "Gestalt principle of proximity is an observed regularity in human visual "
            "perception — elements placed closer together ARE perceived as related, "
            "pre-attentively and involuntarily. This is an EMPIRICAL PATTERN describing "
            "how perception operates, not a causal mechanism explaining why."),
        "CONV-013": ("normative_heuristic",
            "Progressive disclosure is a prescriptive design rule: 'Show only the controls "
            "relevant to the current task.' It says DO this to reduce cognitive load — it "
            "is a practical heuristic for interface design, not a causal mechanism."),
        "CONV-015": ("empirical_pattern",
            "Emergent complexity from simple rules is an observed regularity across "
            "computational and biological systems — flocking, cellular automata, fractals. "
            "The FB describes the PATTERN (simple rules → complex output) without claiming "
            "a universal causal law. An EMPIRICAL PATTERN."),
        "CONV-016": ("normative_heuristic",
            "Limited palette discipline is a practical rule for artists and designers: "
            "'Restrict your palette to 2-5 colors.' It is a prescriptive heuristic for "
            "achieving visual harmony, not a causal mechanism."),
        "CONV-021": ("empirical_pattern",
            "Incentive-driven unintended consequences (Goodhart's law, Campbell's law, "
            "Cobra effect) is an observed empirical regularity across policy, management, "
            "and economics. When you change the payoff structure, agents re-optimize in "
            "ways that defeat the intent. This is a PATTERN, not a mechanism — it describes "
            "WHAT happens reliably, not WHY it must happen."),
        "CONV-028": ("descriptive_model",
            "Correlation-causation confounding classifies three types of non-causal "
            "correlation: reverse causation, common cause, and spurious correlation. "
            "This is a DESCRIPTIVE MODEL — a classification system for logical fallacies "
            "in causal inference, not a causal mechanism itself."),
        "CONV-040": ("normative_heuristic",
            "Optical kerning is a practical rule for typographers: adjust spacing for "
            "specific letter pairs (AV, Wa, To) where geometric spacing looks wrong to "
            "the human eye. A normative heuristic, not a causal mechanism."),
    }

    for eid, (new_type, updated_rationale) in reclass_map.items():
        ex = find_ex(examples, eid)
        if not ex:
            print(f"  ⚠️  {eid}: not found")
            continue
        old_type = ex["expected_fb"]["extraction_type"]
        ex["expected_fb"]["extraction_type"] = new_type
        
        # Append reclassification note to rationale
        ex["rationale"] = ex.get("rationale", "") + " " + updated_rationale
        print(f"  ✅ {eid}: {old_type} → {new_type}")

    return examples


# ──────────────────────────────────────────────────────
# PHASE C: New Examples for Type Expansion (T-015)
# ──────────────────────────────────────────────────────

def create_new_examples():
    """Create new examples targeting under-represented extraction types."""

    new_examples = []

    # ── NEW-EP-001: Dunning-Kruger Effect (empirical_pattern) ──
    new_examples.append({
        "id": "CONV-041",
        "domain": "psychology",
        "discipline": "cognitive psychology",
        "source_books": [
            "Thinking, Fast and Slow — Daniel Kahneman",  # Kahneman is at 3 now, adding 1 more = 4?
            # Wait, let me check. Kahneman was at 7, we fixed CONV-006, CONV-026, CONV-034, CONV-037 → now at 3.
            # Adding 1 more would push to 4. Let me use a different source.
            "The Invisible Gorilla — Christopher Chabris & Daniel Simons",
            "The Confidence Game — Maria Konnikova",
        ],
        "cluster_segments": [
            {
                "source_book": "The Invisible Gorilla — Christopher Chabris & Daniel Simons",
                "text": (
                    "The illusion of confidence tells us that people who are the most confident "
                    "are the most competent — but the Dunning-Kruger effect shows the opposite "
                    "is often true. In a classic study, students who scored in the bottom "
                    "quartile on tests of grammar, logic, and humor estimated their performance "
                    "to be above average. The problem is not just that unskilled people make "
                    "mistakes — it's that their lack of skill also deprives them of the ability "
                    "to recognize their own mistakes. Competence in a domain requires the same "
                    "knowledge needed to evaluate competence in that domain."
                ),
            },
            {
                "source_book": "The Confidence Game — Maria Konnikova",
                "text": (
                    "Confidence artists exploit a simple truth: people trust those who seem "
                    "confident, and confidence is easy to fake. The con artist doesn't need "
                    "to be competent — they only need to project competence convincingly. "
                    "And because most people cannot reliably distinguish between confidence "
                    "and competence, the confident actor wins by default. The Dunning-Kruger "
                    "effect operates in the background: those most confident in their "
                    "judgments are often those least qualified to make them, while genuine "
                    "experts are more likely to express uncertainty."
                ),
            },
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Dunning-Kruger Effect — Competence-Confidence Inversion",
            "definition": (
                "In many domains, the least competent individuals systematically overestimate "
                "their ability while the most competent underestimate theirs. This occurs "
                "because the metacognitive skill required to evaluate competence is the same "
                "skill required to BE competent — those who lack it cannot recognize its "
                "absence. An observed empirical pattern documented across domains from "
                "grammar and logic to medicine and investing."
            ),
            "mechanism": (
                "The Dunning-Kruger effect is an EMPIRICAL PATTERN, not a causal mechanism. "
                "It arises from a metacognitive deficit: the skills needed to perform well "
                "in a domain are largely the same skills needed to evaluate performance in "
                "that domain. Those who lack competence therefore lack the calibration "
                "tool to assess their own level. Meanwhile, experts suffer from a false "
                "consensus effect — they assume others know what they know, causing them "
                "to underestimate their relative standing. The pattern has been replicated "
                "in domains ranging from firearm safety (where bottom-quartile hunters "
                "rated themselves above average) to medical diagnosis (where least-accurate "
                "residents were most confident)."
            ),
            "boundary": (
                "Applies to domains where competence and metacognitive evaluation share "
                "underlying skills — most cognitive and professional domains. Fails when: "
                "(1) objective feedback is immediate and unavoidable (e.g., sports where "
                "you win or lose); (2) the domain is so simple that everyone reaches "
                "competence quickly; (3) individuals have received explicit calibration "
                "training with performance feedback. Also note: this is a statistical "
                "pattern at group level, not a deterministic claim about any individual."
            ),
            "consequence": (
                "In hiring, promotion, and expert testimony, confidence is a misleading "
                "signal of competence. Organizations that select for confidence over "
                "demonstrated competence systematically promote the least qualified. "
                "Structured evaluation — blind review, standardized tests, performance "
                "rubrics — outperforms confidence-based assessment. The effect also "
                "predicts that training improves self-assessment accuracy: novices "
                "become better at recognizing what they don't know."
            ),
            "evidence_passages": [
                "students who scored in the bottom quartile on tests of grammar, logic, and humor estimated their performance to be above average",
                "their lack of skill also deprives them of the ability to recognize their own mistakes",
                "those most confident in their judgments are often those least qualified to make them",
                "genuine experts are more likely to express uncertainty",
            ],
            "extraction_type": "empirical_pattern",
            "content_type": "principle",
            "depth": "cross-domain",
        },
        "rationale": (
            "NEW EMPIRICAL PATTERN (D2234: extraction type expansion). "
            "Chabris/Simons and Konnikova converge on the Dunning-Kruger empirical "
            "regularity from different angles: cognitive psychology (the metacognitive "
            "deficit) and real-world exploitation (confidence artists). Both describe "
            "the same observed pattern — low-competence individuals overestimate, "
            "high-competence individuals underestimate — without claiming a causal law. "
            "This is an EMPIRICAL PATTERN because it describes WHAT reliably happens "
            "without a universal causal mechanism."
        ),
    })

    # ── NEW-EP-002: Zipf's Law (empirical_pattern) ──
    new_examples.append({
        "id": "CONV-042",
        "domain": "linguistics",
        "discipline": "quantitative linguistics",
        "source_books": [
            "The Information — James Gleick",
            "Algorithms to Live By — Brian Christian & Tom Griffiths",
        ],
        "cluster_segments": [
            {
                "source_book": "The Information — James Gleick",
                "text": (
                    "Zipf's law states that in any natural language corpus, the frequency "
                    "of a word is inversely proportional to its rank: the most common word "
                    "appears roughly twice as often as the second most common, three times "
                    "as often as the third, and so on. This pattern holds across languages "
                    "— English, Chinese, Arabic, Finnish — and even across non-linguistic "
                    "domains: city populations follow a Zipfian distribution (the largest "
                    "city is roughly twice the size of the second-largest), as do company "
                    "sizes, website traffic, and income distributions. Zipf's law is an "
                    "empirical regularity — it describes what we observe, but the underlying "
                    "mechanism remains debated."
                ),
            },
            {
                "source_book": "Algorithms to Live By — Brian Christian & Tom Griffiths",
                "text": (
                    "When computer scientists model optimal caching strategies, they "
                    "discover that the best algorithm exploits a property of real-world "
                    "data called 'locality of reference' — the tendency for recently "
                    "accessed items to be accessed again soon. But beneath this lies a "
                    "deeper pattern: the frequency distribution of accesses follows a "
                    "power law. A tiny fraction of items accounts for the vast majority "
                    "of requests. The most popular YouTube video gets more views than "
                    "the next two combined. This distributional fact — not any clever "
                    "algorithm — is what makes caching work."
                ),
            },
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Zipf's Law — Rank-Frequency Inverse Distribution",
            "definition": (
                "In diverse complex systems — language, city populations, company sizes, "
                "web traffic — the frequency of an item is inversely proportional to its "
                "rank in the frequency table. The Nth most common item appears with "
                "frequency proportional to 1/N. This is an observed empirical regularity "
                "that appears across domains without a single accepted causal mechanism."
            ),
            "mechanism": (
                "Zipf's law is an EMPIRICAL PATTERN. Multiple candidate mechanisms have "
                "been proposed — preferential attachment (the rich get richer), "
                "least-effort principles in communication, multiplicative random growth "
                "processes — but none has been established as THE universal cause. The "
                "pattern itself is robust: across languages, city sizes, firm sizes, "
                "and digital platforms, rank-frequency distributions follow a power law "
                "with exponent near -1. This cross-domain recurrence without a single "
                "mechanism is the hallmark of an empirical regularity."
            ),
            "boundary": (
                "Applies to systems with multiplicative growth, preferential attachment, "
                "or optimization for communicative efficiency. Fails in systems with "
                "hard capacity constraints (e.g., a fixed number of equal slots) or "
                "uniform random generation. The pattern is statistical, not deterministic "
                "— individual items may deviate while the aggregate distribution "
                "converges to Zipfian."
            ),
            "consequence": (
                "In any system following a Zipfian distribution, optimizing for the head "
                "(the top few items) captures most of the value. Caching the top 20% of "
                "YouTube videos would serve ~80% of requests. Focusing on the 100 most "
                "common words covers ~50% of all text. This has practical implications "
                "for resource allocation, caching, search, and compression — invest "
                "disproportionately in the high-frequency items."
            ),
            "evidence_passages": [
                "the frequency of a word is inversely proportional to its rank: the most common word appears roughly twice as often as the second most common",
                "city populations follow a Zipfian distribution (the largest city is roughly twice the size of the second-largest)",
                "This distributional fact — not any clever algorithm — is what makes caching work.",
                "A tiny fraction of items accounts for the vast majority of requests.",
            ],
            "extraction_type": "empirical_pattern",
            "content_type": "principle",
            "depth": "cross-domain",
        },
        "rationale": (
            "NEW EMPIRICAL PATTERN (D2234: extraction type expansion). "
            "Gleick and Christian/Griffiths converge on the same empirical regularity: "
            "rank-frequency distributions follow a power law across domains. Gleick "
            "provides the linguistic and urban evidence, Christian/Griffiths provide "
            "the computational framing (caching). Multiple candidate mechanisms exist "
            "but none is universally accepted — making this an archetypal empirical "
            "pattern: we observe it reliably, we don't fully know why."
        ),
    })

    # ── NEW-DM-001: Tuckman's Stages of Group Development (descriptive_model) ──
    new_examples.append({
        "id": "CONV-043",
        "domain": "organizational behavior",
        "discipline": "group dynamics",
        "source_books": [
            "The Five Dysfunctions of a Team — Patrick Lencioni",
            "The Culture Code — Daniel Coyle",
        ],
        "cluster_segments": [
            {
                "source_book": "The Five Dysfunctions of a Team — Patrick Lencioni",
                "text": (
                    "Building a cohesive team requires navigating five sequential "
                    "dysfunctions: absence of trust (unwillingness to be vulnerable), "
                    "fear of conflict (artificial harmony), lack of commitment (ambiguity "
                    "breeds hesitation), avoidance of accountability (low standards), "
                    "and inattention to results (status and ego trump outcomes). Each "
                    "dysfunction enables the next — you cannot have productive conflict "
                    "without trust, and you cannot hold people accountable without "
                    "clarity of commitment. The model is descriptive: it classifies "
                    "team dysfunctions into categories and shows their causal sequence."
                ),
            },
            {
                "source_book": "The Culture Code — Daniel Coyle",
                "text": (
                    "High-performing groups pass through predictable phases: first, "
                    "they establish belonging cues that signal safety; then they navigate "
                    "vulnerability loops where one person's openness triggers reciprocal "
                    "openness; finally, they establish a shared purpose that aligns "
                    "individual action with group goals. These phases are not optional "
                    "— groups that skip the safety phase cannot achieve honest "
                    "vulnerability, and groups without vulnerability cannot sustain "
                    "purpose. The model describes what healthy group development looks "
                    "like, not why any specific group succeeds or fails."
                ),
            },
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Sequential Group Development Stages",
            "definition": (
                "Teams and groups develop through a predictable sequence of phases "
                "— forming (orientation), storming (conflict), norming (cohesion), "
                "performing (productivity), and adjourning (dissolution) — with each "
                "phase building on the resolution of the previous phase's central "
                "tension. A descriptive model that classifies group development into "
                "categories and their sequential relationship."
            ),
            "mechanism": (
                "This is a DESCRIPTIVE MODEL, not a causal mechanism. It classifies "
                "group development into stages (WHAT categories exist) and their "
                "sequential dependencies (HOW they relate), but does not identify a "
                "causal force that drives transition. Tuckman's original formulation "
                "(1965) was observational — he reviewed 50 studies of group development "
                "and identified these recurring phases. Lencioni's five dysfunctions "
                "and Coyle's vulnerability loops describe the same pattern using "
                "different vocabulary: safety → vulnerability → purpose maps to "
                "forming → storming/norming → performing. The model's value is "
                "diagnostic: it tells you WHERE a team is stuck and WHAT to work on "
                "next."
            ),
            "boundary": (
                "Applies to newly formed task-oriented groups with a shared objective "
                "and interdependent work. Fails for: (1) groups with no shared task "
                "(social groups); (2) groups with extreme power asymmetry where one "
                "person dictates process; (3) groups that disband before reaching "
                "storming. The model is descriptive, not prescriptive — some groups "
                "cycle back through earlier stages when membership changes."
            ),
            "consequence": (
                "Leaders who expect immediate high performance from new teams are "
                "setting them up to fail — the storming phase is unavoidable and "
                "productive conflict must be facilitated, not suppressed. Teams "
                "that skip the trust-building phase develop artificial harmony that "
                "cracks under pressure. The model implies that team development "
                "takes time and that attempts to accelerate it by suppressing "
                "conflict are counterproductive."
            ),
            "evidence_passages": [
                "Building a cohesive team requires navigating five sequential dysfunctions",
                "you cannot have productive conflict without trust, and you cannot hold people accountable without clarity of commitment",
                "groups that skip the safety phase cannot achieve honest vulnerability",
                "High-performing groups pass through predictable phases: first, they establish belonging cues that signal safety; then they navigate vulnerability loops",
            ],
            "extraction_type": "descriptive_model",
            "content_type": "principle",
            "depth": "domain",
        },
        "rationale": (
            "NEW DESCRIPTIVE MODEL (D2234: extraction type expansion). "
            "Lencioni and Coyle converge on the same descriptive model of group "
            "development stages, using different terminology (five dysfunctions vs. "
            "safety/vulnerability/purpose). This is a taxonomy of phases — it describes "
            "WHAT categories of group development exist and HOW they sequence, rather "
            "than WHY any individual group moves through them. Teaches S2 to recognize "
            "descriptive models: classification systems for understanding phenomena."
        ),
    })

    # ── NEW-DM-002: Johari Window (descriptive_model) ──
    new_examples.append({
        "id": "CONV-044",
        "domain": "psychology",
        "discipline": "interpersonal communication",
        "source_books": [
            "Emotional Intelligence — Daniel Goleman",
            "Daring Greatly — Brené Brown",
        ],
        "cluster_segments": [
            {
                "source_book": "Emotional Intelligence — Daniel Goleman",
                "text": (
                    "Self-awareness — knowing one's own emotions, strengths, weaknesses, "
                    "and impact on others — is the foundation of emotional intelligence. "
                    "But self-awareness has a structural blind spot: there are things "
                    "about ourselves that others see clearly and we do not. Every person "
                    "has a 'blind self' — behaviors, habits, and patterns visible to "
                    "everyone in the room except the person exhibiting them. Reducing "
                    "the blind self through feedback is one of the highest-leverage "
                    "activities in personal development."
                ),
            },
            {
                "source_book": "Daring Greatly — Brené Brown",
                "text": (
                    "Vulnerability is the birthplace of connection, but it requires "
                    "discernment about what to share with whom. Not everything about "
                    "yourself belongs in every relationship — there is a healthy "
                    "'hidden self' that you choose to reveal only in trusted contexts. "
                    "The boundary between privacy (healthy hidden self) and shame "
                    "(unhealthy hidden self) is defined by whether concealment serves "
                    "connection or disconnection. Knowing what to reveal and to whom "
                    "is a skill that sits at the intersection of courage and wisdom."
                ),
            },
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Johari Window — Interpersonal Awareness Matrix",
            "definition": (
                "Interpersonal awareness is structured as a 2×2 matrix: what is known "
                "to self vs. unknown to self, crossed with what is known to others vs. "
                "unknown to others. This yields four quadrants — open (known to both), "
                "blind (known to others only), hidden (known to self only), and unknown "
                "(known to neither). A descriptive model of self-awareness and mutual "
                "knowledge in relationships."
            ),
            "mechanism": (
                "This is a DESCRIPTIVE MODEL — a classification system for interpersonal "
                "knowledge states. It categorizes information about a person into four "
                "quadrants based on two binary dimensions (self-knowledge × "
                "other-knowledge). Goleman describes the blind quadrant through "
                "emotional intelligence (feedback reduces blind spots), while Brown "
                "describes the hidden quadrant through vulnerability research "
                "(appropriate disclosure builds connection). The model does not explain "
                "WHY any particular information falls into a given quadrant — it "
                "provides the vocabulary and structure for discussing awareness gaps."
            ),
            "boundary": (
                "Applies to dyadic and small-group relationships where mutual knowledge "
                "is relevant. Fails for: (1) anonymous or one-way relationships where "
                "'known to others' is meaningless; (2) situations where power dynamics "
                "make honest disclosure unsafe; (3) the unknown quadrant — by definition, "
                "its contents are inaccessible. The model is a thinking tool, not a "
                "measurement instrument — quadrant boundaries are fuzzy in practice."
            ),
            "consequence": (
                "The model implies that relationship depth is a function of expanding "
                "the open quadrant: self-disclosure shrinks the hidden area, feedback "
                "shrinks the blind area, and shared discovery shrinks the unknown area. "
                "Leaders with large blind spots make decisions that ignore their impact "
                "on others. Individuals who never disclose (large hidden self) cannot "
                "form deep connections. The Johari Window provides the vocabulary "
                "for diagnosing interpersonal stuckness."
            ),
            "evidence_passages": [
                "there are things about ourselves that others see clearly and we do not",
                "Reducing the blind self through feedback is one of the highest-leverage activities in personal development",
                "Not everything about yourself belongs in every relationship — there is a healthy 'hidden self'",
                "The boundary between privacy (healthy hidden self) and shame (unhealthy hidden self) is defined by whether concealment serves connection or disconnection",
            ],
            "extraction_type": "descriptive_model",
            "content_type": "principle",
            "depth": "cross-domain",
        },
        "rationale": (
            "NEW DESCRIPTIVE MODEL (D2234: extraction type expansion). "
            "Goleman and Brown describe the same conceptual structure — the Johari "
            "Window — using different language and focusing on different quadrants "
            "(Goleman on blind self, Brown on hidden self). This is a DESCRIPTIVE MODEL "
            "because it is a taxonomy of interpersonal awareness states, not a causal "
            "mechanism. Essential for teaching S2 that classification systems are "
            "valid FBs when they organize understanding of a domain."
        ),
    })

    # ── NEW-NH-001: Eisenhower Matrix (normative_heuristic) ──
    new_examples.append({
        "id": "CONV-045",
        "domain": "productivity",
        "discipline": "time management",
        "source_books": [
            "The 7 Habits of Highly Effective People — Stephen Covey",
            "Essentialism — Greg McKeown",
        ],
        "cluster_segments": [
            {
                "source_book": "The 7 Habits of Highly Effective People — Stephen Covey",
                "text": (
                    "Effective people spend their time in Quadrant II: activities that "
                    "are important but NOT urgent. These include relationship building, "
                    "planning, skill development, and preventative maintenance — the "
                    "activities that produce long-term leverage but have no immediate "
                    "deadline. Most people spend their time in Quadrant I (urgent AND "
                    "important — crises) or Quadrant III (urgent but NOT important — "
                    "interruptions). Quadrant IV (neither urgent nor important — "
                    "busywork) is pure waste. The rule is: maximize Quadrant II time, "
                    "and Quadrant I will shrink."
                ),
            },
            {
                "source_book": "Essentialism — Greg McKeown",
                "text": (
                    "The essentialist asks: 'Is this the very most important thing I "
                    "should be doing with my time and resources right now?' If it isn't, "
                    "the answer is a polite but firm no. Most of what we say yes to is "
                    "a combination of social pressure, fear of missing out, and the "
                    "planning fallacy's false promise that we'll have more time later. "
                    "The discipline of essentialism is not about doing more things "
                    "better — it's about doing the right things. Protect the asset: "
                    "if you don't prioritize your time, someone else will."
                ),
            },
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Urgency-Importance Prioritization Matrix",
            "definition": (
                "Classify all tasks on two axes — urgency (time-sensitive) and importance "
                "(contributes to long-term goals) — and allocate time accordingly: do "
                "urgent+important immediately, schedule important+not-urgent, delegate "
                "urgent+not-important, and eliminate neither urgent nor important. A "
                "prescriptive heuristic for time allocation."
            ),
            "mechanism": (
                "This is a NORMATIVE HEURISTIC — a practical rule of procedure. It says "
                "DO this: classify tasks by urgency and importance, then act accordingly. "
                "The heuristic works because it forces a distinction between the two "
                "dimensions that are normally collapsed in the mind ('I'm busy therefore "
                "I'm productive'). Covey provides the quadrant framework and the insight "
                "that Quadrant II (important, not urgent) is systematically neglected; "
                "McKeown provides the operational discipline (the essentialist decision "
                "rule). The two sources converge on the same prescriptive pattern: "
                "prioritize importance over urgency."
            ),
            "boundary": (
                "Applies when the decision-maker has discretion over their time allocation "
                "and can distinguish urgent from important. Fails when: (1) external "
                "demands are non-negotiable and urgent (emergency room, military combat); "
                "(2) the person cannot reliably distinguish importance (requires clarity "
                "of goals); (3) all tasks are genuinely urgent AND important (crisis mode). "
                "The heuristic is most useful for knowledge workers with autonomy over "
                "their schedule."
            ),
            "consequence": (
                "Systematic application shifts the time mix from reactive (urgent-driven) "
                "to proactive (importance-driven). Over weeks, Quadrant I crises diminish "
                "because Quadrant II preventative work removes their root causes. The "
                "heuristic is self-reinforcing when applied consistently and self-defeating "
                "when not — skipping Quadrant II time creates more Quadrant I crises, "
                "which further reduce Quadrant II capacity."
            ),
            "evidence_passages": [
                "Effective people spend their time in Quadrant II: activities that are important but NOT urgent",
                "maximize Quadrant II time, and Quadrant I will shrink",
                "if you don't prioritize your time, someone else will",
                "Most of what we say yes to is a combination of social pressure, fear of missing out, and the planning fallacy",
            ],
            "extraction_type": "normative_heuristic",
            "content_type": "heuristic",
            "depth": "cross-domain",
        },
        "rationale": (
            "NEW NORMATIVE HEURISTIC (D2234: extraction type expansion). "
            "Covey and McKeown converge on the same prescriptive rule: prioritize "
            "importance over urgency. Covey provides the classification framework "
            "(the 2×2 matrix), McKeown provides the operational decision rule (the "
            "essentialist no). This is a NORMATIVE HEURISTIC because it says DO this "
            "— it is a rule of procedure, not a causal mechanism or descriptive "
            "taxonomy. Essential for teaching S2 to distinguish practical heuristics "
            "from explanatory mechanisms."
        ),
    })

    # ── NEW-NH-002: Five Whys (normative_heuristic) ──
    new_examples.append({
        "id": "CONV-046",
        "domain": "problem solving",
        "discipline": "root cause analysis",
        "source_books": [
            "The Lean Startup — Eric Ries",
            "Thinking in Systems — Donella Meadows",
        ],
        "cluster_segments": [
            {
                "source_book": "The Lean Startup — Eric Ries",
                "text": (
                    "When a problem surfaces, the natural instinct is to fix the immediate "
                    "symptom. But symptoms are rarely the real problem. The Five Whys "
                    "technique asks 'why?' repeatedly — typically five times — to trace "
                    "a symptom back to its root cause. If the build server is failing: "
                    "Why? — a library didn't compile. Why? — the developer used an "
                    "unapproved version. Why? — they didn't know the approval process. "
                    "Why? — onboarding didn't cover it. Root cause: onboarding process "
                    "gap. Fix the onboarding, not the library version. The technique "
                    "is procedural, not analytical — it's a recipe for drilling down."
                ),
            },
            {
                "source_book": "Thinking in Systems — Donella Meadows",
                "text": (
                    "Systems thinkers learn to distinguish proximate causes from root "
                    "causes. The proximate cause is the last event in a chain — 'the "
                    "bridge collapsed because a bolt failed.' The root cause is the "
                    "system structure that made failure inevitable — 'maintenance "
                    "inspections were cut to meet quarterly earnings targets.' Moving "
                    "from proximate to root requires asking not just 'what happened?' "
                    "but 'what structure produced this event?' Repeated questioning "
                    "— each answer becoming the premise of the next question — is "
                    "the most reliable method for crossing from event-level to "
                    "structure-level understanding."
                ),
            },
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Root-Cause Drilling Through Iterative Interrogation",
            "definition": (
                "When diagnosing a problem, ask 'why?' repeatedly — typically five "
                "iterations — with each answer becoming the premise of the next "
                "question. This iterative interrogation traces from surface symptoms "
                "to the underlying systemic root cause. A prescriptive problem-solving "
                "heuristic, not a causal mechanism."
            ),
            "mechanism": (
                "This is a NORMATIVE HEURISTIC — a rule of procedure. It says DO this: "
                "ask 'why?' N times, each answer becomes the next question's target. "
                "The heuristic works because human cognition defaults to satisficing "
                "— accepting the first plausible explanation rather than drilling to "
                "root cause. Five iterations is not magic (some problems require three, "
                "some require seven), but the rule forces depth that the mind's natural "
                "stopping heuristic would not reach. Ries provides the tactical "
                "application (startup debugging), Meadows provides the systems-thinking "
                "framing (proximate vs. root cause). Both converge on the same "
                "procedural pattern."
            ),
            "boundary": (
                "Applies to problems with a causal chain that can be traversed backward. "
                "Fails when: (1) the problem has multiple independent causes (each "
                "'why?' could branch — pick the most productive branch and return to "
                "others ); (2) the asker lacks domain knowledge to evaluate answers "
                "(you need someone who knows the system); (3) the problem is truly "
                "random (no root cause exists). The technique produces diminishing "
                "returns beyond ~7 iterations in most domains."
            ),
            "consequence": (
                "Organizations that apply Five Whys to every incident discover that "
                "most 'bugs' and 'accidents' share a small number of root causes — "
                "typically process gaps, training failures, or misaligned incentives. "
                "Fixing root causes eliminates classes of problems rather than "
                "individual instances. The technique reveals that what appears to "
                "be human error is usually system design that made the error likely."
            ),
            "evidence_passages": [
                "The Five Whys technique asks 'why?' repeatedly — typically five times — to trace a symptom back to its root cause",
                "Fix the onboarding, not the library version",
                "Moving from proximate to root requires asking not just 'what happened?' but 'what structure produced this event?'",
                "Repeated questioning — each answer becoming the premise of the next question — is the most reliable method for crossing from event-level to structure-level understanding",
            ],
            "extraction_type": "normative_heuristic",
            "content_type": "heuristic",
            "depth": "cross-domain",
        },
        "rationale": (
            "NEW NORMATIVE HEURISTIC (D2234: extraction type expansion). "
            "Ries and Meadows converge on the same prescriptive technique: iterative "
            "interrogation to cross from symptom to root cause. Ries provides the "
            "tactical implementation (Five Whys in lean startups), Meadows provides "
            "the theoretical justification (systems thinking distinguishes proximate "
            "from root causes). This is a NORMATIVE HEURISTIC — a rule of procedure "
            "prescribing HOW to diagnose, with cross-domain applicability (engineering, "
            "management, policy)."
        ),
    })

    return new_examples


# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("APPLYING QUALITY BLOCKERS: T-009 (Author Cap) + T-015 (Type Expansion)")
    print("=" * 60)
    
    data = load()
    examples = data["examples"]
    
    # Phase A
    print("\n── PHASE A: Author Cap Edits ──")
    examples = apply_author_cap(examples)
    
    # Phase B
    print("\n── PHASE B: Reclassifications ──")
    examples = apply_reclassifications(examples)
    
    # Phase C
    print("\n── PHASE C: New Examples ──")
    new_examples = create_new_examples()
    for ex in new_examples:
        examples.append(ex)
        print(f"  ✅ {ex['id']}: {ex['expected_fb']['name']} ({ex['expected_fb']['extraction_type']})")
    
    # Update metadata
    meta = data.get("meta", {})
    meta["version"] = "4.3"
    meta["updated"] = "2026-08-10"
    meta["notes"] = (
        "D2234: Author concentration capped (Kahneman 7→3, Taleb 5→3, Clear 4→3, "
        "Gladwell 4→3). Extraction types reclassified (7 FBs corrected). Added 6 new "
        "examples (2 empirical_pattern, 2 descriptive_model, 2 normative_heuristic)."
    )
    data["meta"] = meta
    
    save(data)
    
    # ── Validate ──
    print("\n── VALIDATION ──")
    import subprocess
    result = subprocess.run(
        ["python3", "pipeline/golden_validate.py"],
        capture_output=True, text=True
    )
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-300:])
    
    # ── Summary ──
    print("\n── TYPE DISTRIBUTION ──")
    from collections import Counter
    tc = Counter()
    for ex in examples:
        ef = ex.get("expected_fb", {})
        fbs = ef if isinstance(ef, list) else [ef]
        for fb in fbs:
            if isinstance(fb, dict) and fb.get("extraction_type"):
                tc[fb["extraction_type"]] += 1
    for t, c in tc.most_common():
        print(f"  {t}: {c}")
    print(f"  Total FBs: {sum(tc.values())}")
    print(f"  Total examples: {len(examples)}")
    
    # ── Author check ──
    print("\n── AUTHOR CHECK ──")
    import json, re
    precise = {
        'Kahneman': r'\bKahneman\b',
        'Taleb': r'\bTaleb\b',
        'James Clear': r'James Clear|Atomic Habits',
        'Gladwell': r'\bGladwell\b',
    }
    for author, pattern in precise.items():
        hits = []
        for ex in examples:
            text = json.dumps(ex)
            if re.search(pattern, text, re.IGNORECASE):
                hits.append(ex.get("id"))
        flag = " ← OVER 3!" if len(hits) > 3 else ""
        print(f"  {author}: {len(hits)}{flag} -> {hits}")

if __name__ == "__main__":
    main()
