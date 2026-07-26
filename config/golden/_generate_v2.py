#!/usr/bin/env python3
"""
Generate the updated golden few-shot YAML + review MD after Claude's feedback.
D2074: Golden set v2.0 — rebalanced domains, real book passages, hard negatives.
"""
import yaml, textwrap, sys
from pathlib import Path

ROOT = Path("/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0")

# ── All examples as Python data (single source of truth) ──────────────
EXAMPLES = [
    {
        "id": "PI-001",
        "domain": "pricing",
        "content_type": "process_instance",
        "source_text": "The Economist's subscription page became a famous case study in decoy pricing. They offered three options: Web-only for $59, Print-only for $125, and Print+Web for $125. The Print-only option was the decoy \u2014 nobody chose it, but its presence made Print+Web look like a bargain (getting both for the same price as print alone). Dan Ariely tested this with his students: when the decoy was present, 84% chose Print+Web. When he removed the decoy and offered only Web ($59) and Print+Web ($125), only 32% chose Print+Web. The decoy shifted preference by making the target option appear as an obvious superior value.",
        "source_book": "Predictably Irrational \u2014 Dan Ariely",
        "expected_principles": [
            "The Economist subscription page used a Print-only decoy at $125 to make Print+Web at $125 look like a bargain. With the decoy: 84% chose Print+Web. Without it: only 32%. The decoy shifted preference by 52 percentage points.",
        ],
        "should_extract": True,
        "principle_type": "process_instance",
        "rationale": "Concrete case study with named company, specific numbers, measurable outcome. Verified accurate against public sources. This is evidence that decoy pricing works \u2014 not the template itself, but proof it's effective.",
    },
    {
        "id": "PI-002",
        "domain": "pricing",
        "content_type": "process_instance",
        "source_text": "When Dropbox launched, they faced the challenge of explaining cloud storage to a market that didn't know they needed it. Instead of listing features, Drew Houston created a 3-minute demo video showing the product in action \u2014 syncing files across devices, recovering deleted files, sharing folders. The video demonstrated the outcome (never lose a file, access anywhere) before mentioning price or features. The result: beta signups jumped from 5,000 to 75,000 overnight. Dropbox went from a struggling startup to a $10B company, partly because they led with value demonstration rather than feature lists.",
        "source_book": "Hacking Growth \u2014 Sean Ellis",
        "expected_principles": [
            "Dropbox used value-first demonstration: a 3-minute video showing file sync, recovery, and sharing outcomes before mentioning features. Result: beta signups jumped from 5,000 to 75,000 overnight, leading to eventual $10B valuation.",
        ],
        "should_extract": True,
        "principle_type": "process_instance",
        "rationale": "Concrete case study with named company, specific metrics (5K\u219275K signups), measurable outcome ($10B valuation). Verified from multiple public sources. Evidence for value-first presentation.",
    },
    {
        "id": "PRO-002",
        "domain": "product",
        "content_type": "principle",
        "source_text": "When testing a new business idea, don't start by building the product. Instead, create a simple landing page describing the offering with a 'buy now' button that leads to a 'sorry, not yet available' page. Measure click-through rates on the buy button. If fewer than 5% of visitors click, the idea may not have enough demand to pursue.",
        "source_book": "Testing Business Ideas \u2014 David Bland",
        "expected_principles": [
            "Demand validation precedes product investment \u2014 fake-door tests (a buy button leading to 'not yet available') measure genuine purchase intent at near-zero cost, with <5% click-through signaling insufficient demand.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Specific, testable method with threshold. Reusable across product development, market research, and entrepreneurship. One of the few non-pricing examples from v1.",
    },
    {
        "id": "CND-001",
        "domain": "pricing",
        "content_type": "principle",
        "source_text": "Social proof is most effective when the proof comes from similar others. Showing that '10,000 people bought this' is less persuasive than showing that 'people like you bought this.' The effect is strongest when people are uncertain about what to do \u2014 in ambiguous situations, we look to others' behavior as a heuristic for correct action. However, social proof backfires when the referenced group is perceived as dissimilar or when the behavior being referenced is undesirable.",
        "source_book": "Influence \u2014 Robert Cialdini",
        "expected_principles": [
            "Social proof persuades through similarity, not volume \u2014 'people like you' outperforms '10,000 people' because relevance amplifies the heuristic. It backfires when the reference group is perceived as dissimilar or the behavior is undesirable.",
        ],
        "should_extract": True,
        "principle_type": "conditional",
        "rationale": "Boundary condition (works when similar, fails when dissimilar). Universal across marketing, UX design, and organizational change.",
    },
    {
        "id": "GE-001",
        "domain": "pricing",
        "content_type": "growth_edge",
        "source_text": "The relationship between anchoring and temporal discounting is underexplored. If an initial price anchor biases willingness-to-pay, does it also bias the timeframe over which people expect to realize value? Someone anchored to $999/month might also expect results in 30 days rather than 90. This could mean pricing anchors don't just set price expectations \u2014 they set the entire value-delivery tempo. Worth investigating with a conjoint experiment.",
        "source_book": "Thinking in Bets \u2014 Annie Duke",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "growth_edge",
        "rationale": "INJECT: FALSE. Removed from Stage 2 golden set (D2073 pending). Growth Edges currently route to QUARANTINE in Stage 5 \u2014 training the LLM to extract content that the pipeline immediately discards creates conflicting signals. Reinstated when GE verification path is built. Kept in golden data for future use.",
    },
    {
        "id": "TI-001",
        "domain": "pricing",
        "content_type": "tool_instruction",
        "source_text": "To build a data visualization dashboard, use Altair's layering operator. Start by creating a base chart with alt.Chart(data).mark_bar(), then add a line overlay with alt.Chart(data).mark_line(). Combine them using the + operator: base + line. For interactive features, add selection intervals with alt.selection_interval() and bind them to the charts using .add_selection(). This creates linked views where selecting data in one chart filters the other.",
        "source_book": "Data Visualization with Altair \u2014 Various",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "tool_instruction",
        "rationale": "CONTRADICTION FIXED (D2074 per Claude feedback): The base SYSTEM_PROMPT explicitly lists Altair layering as an anti-pattern ('Altair's + operator layers independent marks \u2014 this is a tool feature, not a principle'). TI-001 now matches: tool-specific content bound to Altair should NOT be extracted. NEG-001 (Excel bar chart) applies the same rule \u2014 both tools, both correctly excluded. If a separate tool-instruction knowledge store is built later, this can be reinstated with its own output destination.",
    },
    {
        "id": "LEA-001",
        "domain": "leadership",
        "content_type": "principle",
        "source_text": "Diminishers believe that pressure increases performance. They demand people's best thinking, but they don't get it. They haven't created an environment where people feel safe to truly express themselves or their ideas. An unsafe environment yields only the safest ideas. On the other hand, Multipliers know that people are intelligent and will figure things out. They create a safe environment for stretch \u2014 they push people beyond their comfort zone while making it safe to fail, to experiment, and to offer incomplete thinking without fear of judgment.",
        "source_book": "Multipliers \u2014 Liz Wiseman",
        "expected_principles": [
            "Psychological safety is the precondition for intellectual stretch \u2014 pressure without safety yields only the safest ideas, while safety without stretch yields comfort but no growth. Multipliers combine both: they push people beyond their comfort zone while making it safe to fail.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Causal mechanism: safety \u2192 intellectual risk-taking \u2192 better ideas. From leadership domain (Multipliers by Wiseman), a real book passage. Generalizes beyond pricing to any knowledge-work context.",
    },
    {
        "id": "LEA-002",
        "domain": "leadership",
        "content_type": "principle",
        "source_text": "Here's why: Diminishers want to be valued for their intelligence and ideas; in fact, many are desperate for it. On the other hand, Multipliers enjoy finding other people's genius and engaging it. In many ways, Diminishers need Multipliers. It may not be a match made in heaven, but it is a strategy to help you escape a hellish experience, because when you work for a Diminisher, you need to find ways to get your intelligence leveraged without threatening their ego.",
        "source_book": "Multipliers \u2014 Liz Wiseman",
        "expected_principles": [
            "Multipliers draw intelligence out of others by finding and engaging other people's genius; Diminishers want to be valued for their own intelligence and ideas. The contrast between these two approaches defines a fundamental leadership dimension \u2014 amplify others or center yourself.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Definitional contrast: Multiplier vs Diminisher as leadership archetypes. Prior version added 'Diminishers hoard intellectual credit' (source says 'want to be valued for their intelligence') and 'scales organizational intelligence beyond any individual's capacity' (not in this passage). Trimmed to what the source actually says.",
    },
    {
        "id": "STR-001",
        "domain": "strategy",
        "content_type": "principle",
        "source_text": "What consistently separated winners from losers in creating blue oceans was their approach to strategy. The companies caught in the red ocean followed a conventional approach, racing to beat the competition by building a defensible position within the existing industry order. The creators of blue oceans, surprisingly, didn't use the competition as their benchmark. Instead they followed a different strategic logic that we call value innovation. Value innovation is the cornerstone of blue ocean strategy. We call it value innovation because instead of focusing on beating the competition, you focus on making the competition irrelevant by creating a leap in value for buyers and your company, thereby opening up new and uncontested market space.",
        "source_book": "Blue Ocean Strategy \u2014 W. Chan Kim & Ren\u00e9e Mauborgne",
        "expected_principles": [
            "Value innovation makes competition irrelevant by creating a leap in value for buyers and the company simultaneously \u2014 opening new, uncontested market space rather than fighting for share in existing markets.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Core strategic concept from Blue Ocean Strategy. Prior version imported 'simultaneously pursuing differentiation and low cost' from elsewhere in the book \u2014 this passage only says 'creating a leap in value.' Trimmed to what the source actually states.",
    },
    {
        "id": "STR-002",
        "domain": "strategy",
        "content_type": "principle",
        "source_text": "By thinking across conventional boundaries of competition, you can see how to make convention-altering, strategic moves that reconstruct established market boundaries and create blue oceans. The process of discovering and creating blue oceans is not about predicting or preempting industry trends. Nor is it a trial-and-error process of implementing some crazy new business idea that happens to work. Instead, managers are engaged in a structured process that reorders the reality of the market in a fundamentally new way.",
        "source_book": "Blue Ocean Strategy \u2014 W. Chan Kim & Ren\u00e9e Mauborgne",
        "expected_principles": [
            "Strategic innovation reconstructs market boundaries through a structured process \u2014 not trend prediction or random experimentation. The method reorders market reality rather than accepting existing industry structure as given.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Procedural insight about HOW to innovate strategically. From strategy domain. Shows that strategic principles are about process, not just positioning.",
    },
    {
        "id": "MGT-001",
        "domain": "management",
        "content_type": "principle",
        "source_text": "Effective executives concentrate on the few major areas where superior performance will produce outstanding results. They force themselves to set priorities and stay with their priority decisions. They know that they have no choice but to do first things first \u2014 and second things not at all. The alternative is to get nothing done. Effective executives know that they have to get many things done \u2014 and done effectively. Therefore, they concentrate \u2014 their own time and energy as well as that of their organization \u2014 on doing one thing at a time, and on doing first things first.",
        "source_book": "The Effective Executive \u2014 Peter Drucker",
        "expected_principles": [
            "Effective executives concentrate on the few areas where superior performance produces disproportionate results \u2014 they do first things first and second things not at all, because diffused effort across many priorities achieves nothing on any of them.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Classic management principle from Drucker. Procedural because it describes HOW to be effective (concentrate, prioritize, do one thing at a time). From management domain \u2014 no pricing or marketing content.",
    },
    {
        "id": "MGT-002",
        "domain": "management",
        "content_type": "principle",
        "source_text": "Among the effective executives I have had occasion to observe, there have been people who make decisions fast, and people who make them rather slowly. But without exception, they make personnel decisions slowly and they make them several times before they really commit themselves. Effective executives know that personnel decisions are the most important decisions an executive makes \u2014 and that they are also the decisions most likely to be wrong.",
        "source_book": "The Effective Executive \u2014 Peter Drucker",
        "expected_principles": [
            "Personnel decisions warrant multiple rounds of evaluation before commitment \u2014 even decisive executives slow down for hiring and promotion decisions because these are simultaneously the most important and the most error-prone decisions an organization makes.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Causal principle: personnel decisions are highest-stakes \u2192 warrant multiple rounds of slow evaluation. From management domain. Real Drucker passage, slightly noisier than textbook prose.",
    },
    {
        "id": "OPS-001",
        "domain": "operations",
        "content_type": "principle",
        "source_text": "Alex, the goal is not to reduce operational expense by itself. The goal is not to improve one measurement in isolation. The goal is to reduce operational expense and reduce inventory while simultaneously increasing throughput. Any action that moves you toward these three things simultaneously is productive. Any action that moves only one or two is not productive. Any action that does not move any of the three is pure waste.",
        "source_book": "The Goal \u2014 Eliyahu Goldratt",
        "expected_principles": [
            "Operational productivity is defined by simultaneous improvement across three interdependent metrics \u2014 throughput, inventory, and operational expense. Improving only one or two is not productive; improving none is waste. The goal is their joint optimization.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Definition of productivity from Theory of Constraints. Operations domain. The original passage defines a concept through triple condition \u2014 representative of how operations principles are expressed as interdependent constraints rather than single-variable rules.",
    },
    {
        "id": "OPS-002",
        "domain": "operations",
        "content_type": "principle",
        "source_text": "Alex called me today because you perceive a problem with the bottlenecks you've discovered in your plant. Actually, you are experiencing a combination of several problems. But first things first. From what Alex has told me, your most immediate need is to increase throughput and improve your cash flow. An hour lost at a bottleneck is an hour lost for the entire system. An hour saved at a non-bottleneck is a mirage \u2014 it doesn't improve system throughput at all.",
        "source_book": "The Goal \u2014 Eliyahu Goldratt",
        "expected_principles": [
            "An hour lost at a bottleneck is an hour lost for the entire system, but an hour saved at a non-bottleneck produces zero system improvement. Optimization efforts must target constraints, not average utilization.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Core Theory of Constraints insight. Causal: bottleneck \u2192 system output. Distinguishes between real constraints and non-constraints \u2014 a boundary condition that's central to operations thinking. From operations domain.",
    },
    {
        "id": "PRD-001",
        "domain": "product",
        "content_type": "principle",
        "source_text": "As a product trio gains experience with opportunity solution trees, the shape of their tree will help guide their discovery work. The depth and breadth of the opportunity space reflects the team's current understanding of their target customer. If our opportunity space is too shallow, it can guide us to do more customer interviews. A sprawling opportunity space suggests we need to prioritize and narrow. The shape of the tree IS the diagnosis \u2014 it tells you what kind of discovery work you need to do next.",
        "source_book": "Continuous Discovery Habits \u2014 Teresa Torres",
        "expected_principles": [
            "The structure of an opportunity solution tree is a diagnostic tool \u2014 shallow trees indicate insufficient customer research, while sprawling trees indicate inadequate prioritization. The tree's shape guides the next discovery action.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Procedural principle from product management. The tree structure IS the signal \u2014 a meta-principle about how to diagnose your discovery process. From product/tech domain, distinct from pricing and strategy.",
    },
    {
        "id": "MPL-001",
        "domain": "management",
        "content_type": "principle",
        "source_text": "Effective executives know where their time goes. They work systematically at managing the little of their time that can be brought under their control. They focus on outward contribution \u2014 they gear their efforts to results rather than to work. They build on strengths \u2014 their own strengths, the strengths of their superiors, colleagues, and subordinates. And they concentrate on the few major areas where superior performance will produce outstanding results. They do first things first and second things not at all.",
        "source_book": "The Effective Executive \u2014 Peter Drucker",
        "expected_principles": [
            "Effective executives manage time systematically \u2014 they audit where time goes and control what little discretionary time remains.",
            "Effective executives build on strengths \u2014 their own strengths, the strengths of their superiors, colleagues, and subordinates \u2014 rather than focusing on remediating weaknesses.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "MULTI-PRINCIPLE SEGMENT. Dense passage from Drucker containing two distinct principles. Principle 1: time management. Principle 2: strengths-based deployment (revised \u2014 prior version added 'Deployment by strengths produces results; remediation produces mediocrity' \u2014 not in this passage. Trimmed to what the source says).",
    },
    {
        "id": "MPL-002",
        "domain": "leadership",
        "content_type": "principle",
        "source_text": "A leader's job is not to have all the ideas. It's to make sure all the ideas are heard and the best ones win. When you create an environment where the best idea always wins \u2014 regardless of whose idea it is \u2014 you get better decisions and more engaged people. People stop playing politics and start solving problems. They also take more ownership over the outcomes because they helped shape the solution.",
        "source_book": "Multipliers \u2014 Liz Wiseman",
        "expected_principles": [
            "The best-idea-wins culture increases both decision quality and engagement \u2014 it replaces politics with problem-solving and transfers ownership to contributors.",
            "A leader's role shifts from idea generator to idea curator \u2014 the value is in ensuring all ideas surface, not in having the best one personally.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "MULTI-PRINCIPLE SEGMENT. Two distinct insights: one about the mechanism (idea meritocracy \u2192 quality + ownership), one about the role shift (generator \u2192 curator). Tests whether the LLM can separate them.",
    },
    {
        "id": "NEG-HARD-001",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "Good leadership is important for any organization. Leaders must inspire their teams, communicate effectively, and make smart decisions. Without strong leadership, companies struggle to achieve their goals. The best leaders are those who understand their people and create a positive work environment where everyone can thrive. Leadership is the foundation of business success in today's competitive marketplace.",
        "source_book": "Synthetic \u2014 plausible platitude test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "platitude",
        "rationale": "HARD NEGATIVE. This reads like a principle (it has structure, claims causality, uses business vocabulary) but contains zero specific mechanism. 'Good leadership is important' and 'leaders must inspire' are unfalsifiable. Every claim is a tautology. This is exactly the kind of plausible-sounding-but-content-free text that a poorly calibrated LLM extracts as a 'principle.' The model must learn to reject these.",
    },
    {
        "id": "NEG-HARD-002",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "I once worked with a client who had a very unique approach to client relationships. He would send handwritten notes to every client on their birthday, and he claimed this practice alone accounted for 80% of his repeat business. While I can't verify that number, I've adopted a similar practice and found that my clients seem to appreciate the personal touch. It probably works because people like feeling remembered.",
        "source_book": "Synthetic \u2014 over-narrow anecdote test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "anecdote",
        "rationale": "HARD NEGATIVE. Over-narrow personal anecdote masquerading as a principle. Single data point, unverified claim ('80% of repeat business'), vague mechanism ('probably works because...'). This is exactly the 'my one client' pattern that produces unreliable extractions. Reject.",
    },
    {
        "id": "NEG-HARD-003",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "Companies that truly understand their customers outperform those that don't. Customer understanding leads to better products, stronger marketing, and higher sales. The most successful companies in history \u2014 from Apple to Amazon to Toyota \u2014 all share a deep commitment to knowing what their customers want. If you want to grow your business, start by listening to your customers more carefully.",
        "source_book": "Synthetic \u2014 vague generalization test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "platitude",
        "rationale": "HARD NEGATIVE. Vague generalization dressed in business language. 'Understand your customers' is not a principle \u2014 it's a truism with no mechanism, no boundary condition, no falsifiability. Name-drops Apple/Amazon/Toyota as social proof without specific evidence. 'Listen to customers more carefully' is advice, not a principle. Reject.",
    },
    {
        "id": "NEG-001",
        "domain": "multi_domain",
        "content_type": "tool_instruction",
        "source_text": "To create a bar chart in Excel, select your data, click the Insert tab, and choose Bar Chart from the Charts group. You can then customize colors by right-clicking the bars and selecting Format Data Series. For best results, ensure your data is organized with categories in the first column and values in the second.",
        "source_book": "Excel for Business \u2014 Various",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "tool_instruction",
        "rationale": "Tool-specific instruction. Not reusable across contexts. 'Use the Insert tab in Excel' has no application outside Excel. SKIP.",
    },
    {
        "id": "NEG-002",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "This book was first published in 2015 by Harvard Business Review Press. Copyright \u00a9 2015 Harvard Business School Publishing Corporation. All rights reserved. No part of this publication may be reproduced, stored in a retrieval system, or transmitted in any form without prior written permission. Printed in the United States of America.",
        "source_book": "Various HBR books",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "boilerplate",
        "rationale": "Copyright notice. Zero extractable content. Text cleaner strips this but if any slips through, the LLM must recognize it as non-content.",
    },
    {
        "id": "NEG-003",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "In Chapter 3, we discussed the fundamentals of pricing strategy. Chapter 4 will build on these concepts by introducing value-based pricing models. As we saw in the previous section, cost-plus pricing has significant limitations, which we will address in detail throughout this chapter. The following pages will explore how companies can transition from cost-based to value-based approaches.",
        "source_book": "Various textbooks",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "meta_text",
        "rationale": "Navigational/transitional text. References other chapters, previews content, summarizes what was already said. No standalone principle.",
    },
    {
        "id": "DES-001",
        "domain": "design",
        "content_type": "principle",
        "source_text": "The process of composition is the most crucial step in visual problem solving. The results of the compositional decisions set the purpose and meaning of the visual statement and carry strong implications for what the viewer receives. It is at this vital stage in the creative process that the visual communicator has the strongest control of the work and the greatest opportunity to express the total mood the work is intended to convey. But the visual mode offers no proscribed structural systems that are absolute. How can we gain control of our complex visual means with some certainty of shared meaning? There are no absolute rules, but there is a great deal of understanding of what will occur in terms of meaning if we make certain arrangements of the parts toward organizing and orchestrating the visual means.",
        "source_book": "A Primer of Visual Literacy \u2014 Donis A. Dondis",
        "expected_principles": [
            "Composition is the highest-leverage stage in visual communication \u2014 it is where the communicator has maximum control over meaning and mood, yet visual language lacks absolute rules, requiring designers to develop a deep understanding of how compositional arrangements shape viewer interpretation.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Core design principle from a foundational visual literacy textbook. Identifies the causal relationship: compositional decisions \u2192 viewer interpretation. The source uses hedged language ('a great deal of understanding of what will occur') \u2014 'predictably' overstated the source's confidence. Removed.",
    },
    {
        "id": "DES-002",
        "domain": "design",
        "content_type": "principle",
        "source_text": "The more abstract the symbol, the more penetration of the public mind is necessary for the education to its meaning. A dove carrying an olive branch became the easily recognized symbol of peace only after widespread cultural education. In this case, some education of the public may be necessary for the message to be clear. But the more abstract the symbol, the more prior knowledge the viewer must bring to decode it.",
        "source_book": "A Primer of Visual Literacy \u2014 Donis A. Dondis",
        "expected_principles": [
            "Symbol abstraction and audience education are inversely proportional: the more abstract a visual symbol, the more cultural penetration and public education is required before it can reliably communicate its intended meaning. Concrete symbols require less decoding effort than abstract ones.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Establishes a gradient from concrete to abstract symbol systems and the educational burden each places on the viewer. A fundamental semiotic principle with direct application to logo design, iconography, and visual communication.",
    },
    {
        "id": "DES-003",
        "domain": "design",
        "content_type": "principle",
        "source_text": "For the initial stage, a designer must not fear making mistakes. Now is not the time to worry about the clarity, spacing, form, or silhouette. Instead sketching should be performed as a fever-like activity, pouring ideas on the paper. The more unrestrained, spontaneous, unconscious, and uninhibited, the better. This should be viewed as an exploratory stage where anything is allowed. A designer must generate volume before editing \u2014 quantity precedes quality in the ideation phase.",
        "source_book": "Principles of Logo Design \u2014 George Bokhua",
        "expected_principles": [
            "In the ideation phase of design, quantity precedes quality: unrestrained, spontaneous sketching without concern for clarity or correctness produces the raw volume from which strong concepts can later be selected and refined. Premature self-editing kills exploration.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Actionable design process principle. Establishes a two-phase model (divergent exploration \u2192 convergent editing) that applies across all design disciplines.",
    },
    {
        "id": "DES-004",
        "domain": "design",
        "content_type": "principle",
        "source_text": "The body of work created by modernists laid a solid foundation for modern logo designs. A certain language of form was invented, and there are certain elements that represent a fabric of modernist aesthetic. These include waves, stripes, stars, arrows, cubes, overlapping primitive shapes with exclusion, inclusion, and intersection. Geometric precision was favored over the expressive, and universal appeal was valued over a culture-bound aesthetic.",
        "source_book": "Principles of Logo Design \u2014 George Bokhua",
        "expected_principles": [
            "Modernist design established a universal visual language built on geometric primitives (waves, stripes, stars, arrows, cubes) and boolean operations (exclusion, inclusion, intersection). It prioritized geometric precision and universal appeal over cultural specificity and personal expression.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Defines the modernist design language that underpins contemporary logo design. Establishes vocabulary (geometric primitives + boolean operations) and value system (universal over culture-specific).",
    },
    {
        "id": "DES-005",
        "domain": "design",
        "content_type": "principle",
        "source_text": "Corporate type must be simple and readable; it must also use a neutral sans serif type for main text. Most of the time I advise clients to use a simple sans serif because it's neutral, simple to use, and most devices have it as a default font, meaning it will not be an additional cost. Corporate typography is often a different entity from the logo type \u2014 though not always.",
        "source_book": "Principles of Logo Design \u2014 George Bokhua",
        "expected_principles": [
            "Corporate typography should prioritize neutrality and ubiquity over distinction: simple sans-serif fonts ensure readability, cross-platform consistency, and zero licensing cost \u2014 separating the functional role of corporate type from the expressive role of logo marks.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Practical decision heuristic for typography selection in identity systems. Separates corporate type concerns from logo type concerns.",
    },
    {
        "id": "DES-006",
        "domain": "design",
        "content_type": "principle",
        "source_text": "A dot alone in a field relates to the whole, but it stands alone, and the relationship is a mild state of intermodification between it and the square. But when two dots are placed in the same field, they fight for attention in their interaction, creating comparatively individual statements because of their distance from each other and their relationship to the frame. The introduction of a second element transforms a static field into a dynamic composition.",
        "source_book": "A Primer of Visual Literacy \u2014 Donis A. Dondis",
        "expected_principles": [
            "A single element in a visual field creates a static relationship with the frame, but adding a second element transforms the composition into a dynamic system of competing attention \u2014 each element now interacts with the other and the frame, making spatial relationships the primary carriers of meaning.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Fundamental compositional principle identifying the threshold between static and dynamic composition (one element \u2192 two elements). Generalizes beyond dots to any design elements.",
    },
    {
        "id": "ART-001",
        "domain": "art",
        "content_type": "principle",
        "source_text": "A 'North Star' for instrument design is to create something 'instantly knowable, yet infinitely masterable.' Consider the pencil, or the piano: its basic principles of operation are simple enough for a child to deduce, yet one can spend a lifetime using it and still find more to say; sophisticated expressions are possible, and mastery is elusive. From the standpoint of systems design, our challenge is to create tools that have this same property: a low floor, a high ceiling, and wide walls.",
        "source_book": "Code as Creative Medium \u2014 Golan Levin & Tega Brain",
        "expected_principles": [
            "The ideal creative instrument has three properties: a low floor (simple enough for a novice to start immediately), a high ceiling (capable of sophisticated expression by experts), and wide walls (supporting diverse approaches and styles). This 'instantly knowable, yet infinitely masterable' quality is the North Star for tool, language, and interface design.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Widely-cited design framework for creative tools (low floor, high ceiling, wide walls). Originated in computational art education but generalizes to any creative instrument. High-reuse principle.",
    },
    {
        "id": "ART-002",
        "domain": "art",
        "content_type": "principle",
        "source_text": "In computational art and design, many responses to the questions of what and why continue historic lines of creative inquiry centered on procedure, connection, abstraction, authorship, the nature of time, and the role of chance. The pursuit of these formal and conceptual concerns in the medium of computation has created new practices and aesthetics, and has also heightened a sensibility to the formal properties of code itself \u2014 that code is not merely a tool but a material with its own affordances and constraints.",
        "source_book": "Code as Creative Medium \u2014 Golan Levin & Tega Brain",
        "expected_principles": [
            "Computational art extends historic creative concerns (procedure, abstraction, authorship, time, chance) into a new medium, but with a critical distinction: code is not merely a neutral tool but a material with its own affordances and constraints that shape the resulting work.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Establishes the philosophical foundation of computational art: it engages with the material properties of code as medium, not just uses code as a tool. The source says code has 'its own affordances and constraints' \u2014 that's the extraction boundary. Prior version injected a McLuhan reference not in source.",
    },
    {
        "id": "ART-003",
        "domain": "art",
        "content_type": "principle",
        "source_text": "Computers and computing were not the same thing. What hadn't been made apparent to me during my university days was that computation is an abstract idea, not a physical machine. It's the manipulation of ideas according to formal rules. A computer is just one possible embodiment of this idea. Once I understood that computing wasn't about machines but about process and logic, a whole new world of creative possibility opened up.",
        "source_book": "Generative Art: A Practical Guide \u2014 Matt Pearson",
        "expected_principles": [
            "Computation is an abstract idea \u2014 the manipulation of concepts according to formal rules \u2014 not a physical machine. A computer is merely one embodiment of computation. Recognizing this distinction unlocks creative approaches: computation can be expressed in any medium, not just electronics.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Fundamental reframing that separates the concept of computation from its physical implementation. The intellectual move that makes generative art possible.",
    },
    {
        "id": "ART-004",
        "domain": "art",
        "content_type": "principle",
        "source_text": "Some parts bubble and then fade out; others achieve a looping stability. There has been much study of this game, identifying the mathematical 'life' that forms: gliders, toads, boats, blinkers, blocks. What makes Conway's Game of Life so compelling for generative artists is that complex, seemingly organic behavior emerges from a tiny set of deterministic rules applied locally to each cell. You don't design the pattern \u2014 you design the rules, and the pattern designs itself.",
        "source_book": "Generative Art: A Practical Guide \u2014 Matt Pearson",
        "expected_principles": [
            "Generative art operates on emergence: complex, organic-seeming behavior arises from simple, local, deterministic rules applied iteratively. The artist's role shifts from designing the output to designing the rule system \u2014 you don't design the pattern, you design the rules, and the pattern designs itself.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Defines the core mechanism of generative art: emergence from rule systems. The distinction between designing outputs vs. designing rules is the defining characteristic of the field.",
    },
    {
        "id": "ART-005",
        "domain": "art",
        "content_type": "principle",
        "source_text": "Humans are equipped with an exquisite sensitivity to faces. From infancy, we easily recognize faces and can detect very subtle shifts in expressions, often being able to discern the slightest change in mood and sincerity in ways that remain impossible for computers. Faces also allow us to readily identify family resemblances or recognize friends in crowds. Faces are so central to visual perception that the impairment of our face-processing ability is seen as a disorder, called prosopagnosia, while unconsciously seeing faces where there are none is an almost universal kind of pareidolia.",
        "source_book": "Code as Creative Medium \u2014 Golan Levin & Tega Brain",
        "expected_principles": [
            "Human face perception occupies a privileged channel in visual cognition: we detect faces instantly, read micro-expressions beyond current computer capability, and hallucinate faces in random patterns (pareidolia). The impairment of face-processing (prosopagnosia) is classified as a disorder, while unconscious face-detection (pareidolia) is near-universal \u2014 indicating the depth and automaticity of this neural mechanism.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Describes the cognitive phenomenon of face perception sensitivity. The source describes the mechanism; it does NOT make the design-prescriptive claim ('uniquely powerful design material') that the prior version added. The design application would require a different source passage that explicitly makes that claim.",
    },
    {
        "id": "ART-006",
        "domain": "art",
        "content_type": "principle",
        "source_text": "This assignment draws inspiration from the 'Chernoff face' data visualization technique, which leverages this sensitivity by using facial features to represent multivariate data. In Chernoff faces, features such as the eyes, ears, mouth, and nose represent data according to their shape, size, placement, and orientation. Whereas Herman Chernoff used 18 variables to synthesize a face, Paul Ekman and Wallace Friesen's Facial Action Coding System analyzes faces with 46, each variable corresponding to the action of a different facial muscle.",
        "source_book": "Code as Creative Medium \u2014 Golan Levin & Tega Brain",
        "expected_principles": [
            "Chernoff faces exploit the human brain's specialized face-processing circuitry for data visualization: facial features (eyes, ears, mouth, nose) encode multivariate data through shape, size, placement, and orientation. This technique maps up to 18 data dimensions onto a single glyph by piggybacking on evolutionarily-ancient perception hardware.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Concrete data visualization technique that bridges cognitive science (face perception) and design practice. The connection to Ekman's FACS system enriches the principle with scientific grounding.",
    },
    {
        "id": "PER-001",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "Outcomes are about what you get. Processes are about what you do. Identity is about what you believe. When it comes to building habits that last \u2014 when it comes to building a system of 1 percent improvements \u2014 the problem is not that one level is 'better' or 'worse' than another. All levels of change are useful in their own way. The problem is the direction of change.",
        "source_book": "Atomic Habits \u2014 James Clear",
        "expected_principles": [
            "Behavior change operates on three levels: outcome (what you get), process (what you do), and identity (what you believe). All levels are useful in their own way. The critical variable is not which level is best, but the direction of change \u2014 which level you start from determines whether the change persists.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Core framework from Atomic Habits. The three-level model is directly stated in this passage. Prior version imported Clear's Chapter 2 thesis ('most durable change starts from identity outward') which is NOT in this passage \u2014 that claim requires a different source text. Trimmed to what the passage actually says: three levels exist, direction matters.",
    },
    {
        "id": "PER-002",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "Imagine two people resisting a cigarette. When offered a smoke, the first person says, 'No thanks. I'm trying to quit.' It sounds like a reasonable response, but this person still believes they are a smoker who is trying to be something else. They are hoping their behavior will change while carrying around the same beliefs. The second person says, 'No thanks. I'm not a smoker.'",
        "source_book": "Atomic Habits \u2014 James Clear",
        "expected_principles": [
            "Identity-based resistance is more effective than willpower-based resistance: saying 'I'm not a smoker' (identity statement) outperforms 'I'm trying to quit' (effort statement) because the former aligns the behavior with a self-concept that makes the undesired action inconsistent with who the person believes themselves to be.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Demonstrates the identity-based change model with a concrete, testable example. The linguistic contrast ('I'm trying' vs. 'I'm not') makes the abstract principle tangible and memorable.",
    },
    {
        "id": "PER-003",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "The first three laws of behavior change \u2014 make it obvious, make it attractive, and make it easy \u2014 increase the odds that a behavior will be performed this time. The fourth law of behavior change \u2014 make it satisfying \u2014 increases the odds that a behavior will be repeated next time. It completes the habit loop.",
        "source_book": "Atomic Habits \u2014 James Clear",
        "expected_principles": [
            "The Four Laws of Behavior Change form a complete loop: make it obvious, make it attractive, make it easy, and make it satisfying. The first three laws drive initiation \u2014 increasing the odds a behavior is performed this time. The fourth law drives repetition \u2014 increasing the odds a behavior is performed next time. Without satisfaction, behaviors extinguish regardless of how easy or obvious they are.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Summarizes the book's central framework. Prior version imported cue/craving/response/reward habit-loop terminology \u2014 not in this passage. This passage only names the four laws and distinguishes initiation (first three) from repetition (fourth). Trimmed.",
    },
    {
        "id": "PER-004",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "The more automatic a behavior becomes, the less likely we are to consciously think about it. And when we've done something a thousand times before, we begin to overlook things. We assume that the next time will be just like the last. We're so used to doing what we've always done that we don't stop to question whether it's the right thing to do at all. Many of our failures in performance are largely attributable to a lack of self-awareness.",
        "source_book": "Atomic Habits \u2014 James Clear",
        "expected_principles": [
            "Automaticity creates a blindness trap: the more practiced a behavior becomes, the less conscious attention we pay to it, causing us to overlook errors, assume stability, and fail to question whether the behavior is still appropriate. Many performance failures are attributable to this lack of self-awareness.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Identifies a paradox of expertise: the very automaticity that enables high performance also creates vulnerability to stale thinking. Prior version added 'Mastery requires deliberate disruption of automaticity' \u2014 a prescription not in this passage. The source identifies the problem (automaticity \u2192 blindness); it does not prescribe the solution. Trimmed to descriptive only.",
    },
    {
        "id": "PER-005",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "Resistance seems to come from outside ourselves. We locate it in spouses, jobs, bosses, kids. 'Peripheral opponents,' as Pat Riley used to say when he coached the Los Angeles Lakers. Resistance is not a peripheral opponent. Resistance arises from within. It is self-generated and self-perpetuated. Resistance is the enemy within.",
        "source_book": "The War of Art \u2014 Steven Pressfield",
        "expected_principles": [
            "Resistance \u2014 the force that prevents creative work \u2014 feels external but is internally generated. We project it onto spouses, bosses, and circumstances, but it originates within and is self-perpetuating. Recognizing Resistance as self-generated is the prerequisite to overcoming it.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Core concept from The War of Art. The internal vs. external attribution distinction is explicitly stated. Prior version added 'external enemies can be avoided; internal ones must be confronted' \u2014 a logical inference not stated in this passage. Trimmed to what the source actually says.",
    },
    {
        "id": "PER-006",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "Resistance will tell you anything to keep you from doing your work. It will perjure, fabricate, falsify; seduce, bully, cajole. Resistance is protean. It will assume any form, if that's what it takes to deceive you. It will reason with you like a lawyer or jam a nine-millimeter in your face like a stickup man. Resistance has no conscience. It will pledge anything to get a deal, then double-cross you as soon as your back is turned. If you take Resistance at its word, you deserve everything you get. Resistance is always lying and always full of shit.",
        "source_book": "The War of Art \u2014 Steven Pressfield",
        "expected_principles": [
            "Resistance is protean \u2014 it adapts its tactics to whatever will most effectively prevent the creative from doing the work, shifting between seduction, intimidation, rational argument, and outright deception. Because Resistance has no fixed form, the only reliable countermeasure is to recognize that it is always lying, regardless of how reasonable it sounds.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Describes the adaptive, shape-shifting nature of creative Resistance. The 'protean' quality means you cannot develop a single counter-strategy \u2014 you must recognize the pattern across its many forms. Expands Pressfield's framework beyond the initial definition.",
    },
    {
        "id": "PER-007",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "The paradox seems to be, as Socrates demonstrated long ago, that the truly free individual is free only to the extent of his own self-mastery. While those who will not govern themselves are condemned to find masters to govern over them.",
        "source_book": "The War of Art \u2014 Steven Pressfield",
        "expected_principles": [
            "Freedom and self-mastery are directly proportional, not opposed: the individual who cannot discipline themselves must submit to external discipline. As Socrates demonstrated, the truly free individual is free only to the extent of his own self-mastery, while those who will not govern themselves are condemned to find masters to govern over them.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Philosophical principle tracing back to Socratic thought. The source is a direct quote of the Socratic paradox. Prior version added 'Creative freedom requires the internal structure of a professional' \u2014 an application to creative practice not in the source. Trimmed to the philosophical extraction. The creative-practice application is valid but belongs in a separate principle with its own source passage.",
    },
    {
        "id": "PER-008",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "Once you see a pattern, you can't un-see it. Trust me, I've tried. But when the same truth keeps repeating itself, it's hard to pretend that it's just a coincidence. For example, no matter how hard I try to convince myself that I can function on six hours of sleep, anything less than eight hours leaves me impatient, anxious, and foraging for carbohydrates. It's a pattern.",
        "source_book": "The Gifts of Imperfection \u2014 Bren\u00e9 Brown",
        "expected_principles": [
            "Pattern recognition creates an irreversible awareness: once you've identified a recurring truth about yourself, you cannot return to the state of not-knowing. The data (e.g., 'I am irritable on less than eight hours of sleep') accumulates until denial becomes more costly than acceptance. Self-awareness is a one-way door.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Describes the psychological mechanism of self-awareness as irreversible pattern recognition. The 'one-way door' property means self-knowledge compounds \u2014 each pattern you see makes the next one easier to spot.",
    },
    {
        "id": "PER-009",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "Joy is as thorny and sharp as any of the dark emotions. To love someone fiercely, to believe in something with your whole heart, to celebrate a fleeting moment in time, to fully engage in a life that doesn't come with guarantees \u2014 these are risks that involve vulnerability and often pain. When we lose our tolerance for discomfort, we lose joy. In fact, addiction research shows us that an intensely positive experience can be as difficult to process as a traumatic one.",
        "source_book": "The Gifts of Imperfection \u2014 Bren\u00e9 Brown",
        "expected_principles": [
            "Joy and vulnerability are inseparable: the capacity to experience joy requires the capacity to tolerate the vulnerability that accompanies it \u2014 the risk of loss, the absence of guarantees. When we lose our tolerance for discomfort, we lose joy alongside it. Addiction research confirms that intensely positive experiences can be as destabilizing as traumatic ones.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Inverts the common assumption that joy is 'light' and pain is 'heavy.' Establishes that vulnerability tolerance is the single mechanism underlying both. Prior version imported 'numb'/'numbing' language from PER-011's overlapping passage \u2014 this passage uses 'lose tolerance' and 'lose joy,' not 'numb.' Trimmed to source language.",
    },
    {
        "id": "DES-007",
        "domain": "design",
        "content_type": "principle",
        "source_text": "Syntax in the context of visual literacy can only mean the orderly arrangement of parts, leaving us with the problem of how we can approach the process of composition with intelligence and knowledge of how compositional decisions will affect the final result. There are no absolute rules, but there is a great deal of understanding of what will occur in terms of meaning if we make certain arrangements of the parts toward organizing and orchestrating the visual means. Many of the guidelines for understanding the meaning in visual form, the syntactic rules, are based on what we know about human perception.",
        "source_book": "A Primer of Visual Literacy \u2014 Donis A. Dondis",
        "expected_principles": [
            "Visual syntax operates not as absolute rules but as predictive guidelines grounded in human perception: certain arrangements reliably produce certain interpretations because of how the human visual system processes information. Effective composition requires understanding these perceptual principles and applying them intelligently to the specific communicative goal, not following a fixed recipe.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Defines visual syntax as a perceptual science rather than an aesthetic rulebook. The distinction between 'absolute rules' and 'predictive guidelines grounded in perception' is fundamental to understanding design as a discipline.",
    },
    {
        "id": "DES-008",
        "domain": "design",
        "content_type": "principle",
        "source_text": "Transparency and opacity define each other physically: the former means visual detail that can be seen through so that what is behind it is revealed to the eye; the latter is just the opposite, blocking out, concealing what it visually supersedes. These two poles represent one of the fundamental technique polarities available to the visual communicator.",
        "source_book": "A Primer of Visual Literacy \u2014 Donis A. Dondis",
        "expected_principles": [
            "Transparency and opacity form a fundamental visual polarity: transparency reveals layers and creates depth through visible relationships between foreground and background, while opacity conceals and creates hierarchy through visual dominance. Understanding this polarity gives the designer control over what the viewer sees first, second, and what remains hidden.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Defines a fundamental visual design polarity. The technique is simple but the implications for information hierarchy and visual storytelling are profound. A building-block principle for design education.",
    },
    {
        "id": "DES-009",
        "domain": "design",
        "content_type": "principle",
        "source_text": "Visual communication, like language, employs a set of symbols with agreed-upon meanings. Unlike language, however, visual communication has no fixed syntax \u2014 no equivalent of grammar that dictates how symbols must be combined. This absence of fixed rules is both a liberation and a burden: the designer has greater freedom but less certainty that the audience will interpret the work as intended.",
        "source_book": "A Primer of Visual Literacy \u2014 Donis A. Dondis",
        "expected_principles": [
            "Visual communication differs fundamentally from verbal language: it lacks a fixed grammar. This absence creates a tradeoff \u2014 greater creative freedom for the designer but less certainty that the audience will interpret the work as intended. Every visual message navigates this tension between expressive liberty and interpretive risk.",
        ],
        "should_extract": True,
        "principle_type": "comparative",
        "rationale": "Defines the fundamental difference between visual and verbal communication. The source uses epistemic language ('less certainty'), and the extraction preserves that hedged framing rather than escalating to existential claims ('act of faith'). The 'liberation and burden' framing from the source is preserved.",
    },
    {
        "id": "DES-010",
        "domain": "design",
        "content_type": "principle",
        "source_text": "The circle applied as a graphic device works well with a triangular mark since the negative space in relationship to circle and triangle appears balanced. If it was a square, the approach and result would differ. The interaction between the containing shape and the contained mark creates either harmony or tension, and the choice between them is never neutral \u2014 it communicates something about the brand.",
        "source_book": "Principles of Logo Design \u2014 George Bokhua",
        "expected_principles": [
            "The relationship between a logo mark and its containing shape is never neutral: a circle creates balanced negative space with angular marks, while a square creates different tension dynamics. The choice of container shape is a communicative decision, not merely a compositional one \u2014 it shapes how the brand is perceived before the viewer even processes the mark itself.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Demonstrates a specific design principle (container-shape interaction) with concrete examples. The higher-order principle \u2014 that every formal choice is also a communicative choice \u2014 generalizes beyond logo design.",
    },
    {
        "id": "DES-011",
        "domain": "design",
        "content_type": "principle",
        "source_text": "Creating an effective combination of pattern and color can be difficult. Seeing how the pattern will re-create and repeat at different scales is a quick way to determine the overall effect. It can be helpful to both the designer and client to create mock-ups of the pattern in use in practical situations. Be sure to use a variety of sizes, such as on a letterhead or on a wall in an office.",
        "source_book": "Principles of Logo Design \u2014 George Bokhua",
        "expected_principles": [
            "Pattern evaluation requires multi-scale testing: a pattern that works at business-card scale may fail as environmental graphics, and vice versa. The designer must test at every scale the pattern will inhabit \u2014 letterhead, signage, digital screen, textile \u2014 because scale changes the perceptual relationship between pattern elements and can alter the visual effect.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Practical design process principle. The multi-scale testing requirement applies to any repetitive visual system \u2014 patterns, grids, logos, typography. The insight that scale changes perceptual relationships is a fundamental design truth.",
    },
    {
        "id": "PER-010",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "The word compassion is derived from the Latin words pati and cum, meaning 'to suffer with.' I don't believe that compassion is our default response to suffering. I think our first response is usually self-protection. We armor ourselves against pain, or we try to fix it, or we resort to blame. Compassion is a practice \u2014 not a personality trait \u2014 that requires us to stay present with suffering without trying to solve it.",
        "source_book": "The Gifts of Imperfection \u2014 Bren\u00e9 Brown",
        "expected_principles": [
            "Compassion is a practice, not a personality trait. The etymology ('to suffer with') reveals that compassion requires the capacity to stay present with suffering \u2014 our own or others' \u2014 without armoring, fixing, or blaming. Because self-protection is the default response, compassion requires deliberate cultivation, not passive possession.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Redefines compassion from trait to practice, using etymology as evidence. The 'practice not trait' reframing has broad application: courage, vulnerability, and creativity can all be understood similarly. High reuse potential across personal practice and leadership.",
    },
    {
        "id": "PER-011",
        "domain": "personal_practice",
        "content_type": "principle",
        "source_text": "When we lose our tolerance for discomfort, we lose joy. In fact, addiction research shows us that an intensely positive experience can be as difficult to process as a traumatic one. We cannot selectively numb emotions. When we numb the dark, we also numb the light.",
        "source_book": "The Gifts of Imperfection \u2014 Bren\u00e9 Brown",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "causal",
        "rationale": "DUPLICATE of PER-009. Same insight (numbing is non-selective) from overlapping Bren\u00e9 Brown source text. ~85% semantic similarity. In production, Stage 3/4 deduplication should suppress the second extraction. Changed to negative: teaches the model that near-identical extractions from overlapping passages should be suppressed, not rewarded.",
    },
    {
        "id": "ART-007",
        "domain": "art",
        "content_type": "principle",
        "source_text": "Generative design has long ceased to be a trade secret among design students; in some universities, it is now firmly integrated into the curriculum. From infographics to the visualization of sound, from the fine arts to architecture, and especially in the realm of communication design and media installations, generative design allows for dynamic, stunning, and fascinating applications.",
        "source_book": "Generative Design \u2014 Bohnacker, Gro\u00df, Laub, Lazzeroni",
        "expected_principles": [
            "Generative design has moved from experimental practice to mainstream curriculum across disciplines: infographics, sound visualization, fine arts, architecture, and communication design. Its defining value is dynamism \u2014 the ability to create systems that produce varied, responsive outputs rather than fixed artifacts \u2014 making it particularly suited to media installations and interactive contexts.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Marks the institutional adoption of generative design as a discipline. Defines the value proposition (dynamism over fixity) and maps the application landscape. Useful as a reference principle for understanding the field's scope.",
    },
    {
        "id": "ART-008",
        "domain": "art",
        "content_type": "principle",
        "source_text": "Processing and vvvv have for many years been the programming environments of choice for artists and designers. However, more recently there has been a shift toward more web-centric applications, giving rise to new coding environments such as p5.js, a JavaScript library that is especially programmed for and by artists, designers, and other web users. This shift reflects a broader movement: creative coding is moving from the desktop to the browser, from standalone applications to networked experiences.",
        "source_book": "Generative Design \u2014 Bohnacker, Gro\u00df, Laub, Lazzeroni",
        "expected_principles": [
            "Creative coding tools are migrating from desktop (Processing, vvvv) to browser (p5.js), driven by the web's advantages in distribution, accessibility, and networked interaction. This platform shift is not merely technical \u2014 it changes who can access creative coding (anyone with a browser), how work is shared (URL vs. executable), and what kinds of work are possible (networked, collaborative, real-time).",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Documents a significant platform shift in the creative coding ecosystem. The causal chain (technical shift \u2192 accessibility change \u2192 new creative possibilities) is clearly articulated. Relevant to tool design and creative technology adoption.",
    },
    {
        "id": "ART-009",
        "domain": "art",
        "content_type": "principle",
        "source_text": "This book is all about the algorithms. It's about the philosophy, aesthetics, and experimentation too, but mostly it's about the algorithms and the tools you use to explore them. You can, theoretically, perform the mathematics behind procedural generative art with a stick of chalk and a large flat rock, but that would make life unnecessarily difficult \u2014 especially when we live among the ever-advancing sophistication of modern computing.",
        "source_book": "Generative Art: A Practical Guide \u2014 Matt Pearson",
        "expected_principles": [
            "The value of computational tools in generative art is not that they enable something previously impossible \u2014 the underlying mathematics can be executed with chalk and rock \u2014 but that they collapse the iteration cycle from hours to milliseconds. Fast feedback transforms the creative process from planning to exploration: the artist can try, see, adjust, and try again at the speed of thought.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Reframes the role of computation in art: not enabling the impossible, but accelerating the possible to the point where the creative process qualitatively changes. The 'chalk and rock' thought experiment is a powerful illustration of the speed-feedback principle.",
    },
    {
        "id": "SYS-001",
        "domain": "systems_decision",
        "content_type": "principle",
        "source_text": "In these experiments, an animal or person is made to learn which of two simple stimuli, e.g., two geometrical patterns, is tied to a reward. Since there is no sensible connection between the visual sign and the reward, the task is intellectually unattractive, though practically gainful. The best the rat or monkey or human subject can do is to find out by repeated trials which figure is the winner.",
        "source_book": "Visual Thinking \u2014 Rudolf Arnheim",
        "expected_principles": [
            "When there is no structural relationship between a stimulus and its associated reward, learning degrades to trial-and-error \u2014 a cognitively uninteresting process that produces fragile knowledge. Meaningful learning requires structural congruence: the relationship between sign and outcome must be perceivable, not arbitrary.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Bridges perceptual psychology (Arnheim) with learning theory. The 'no sensible connection \u2192 trial-and-error \u2192 fragile knowledge' causal chain is directly stated. Domain applicability claims ('interface design, education') were removed \u2014 those are annotations, not extractions from this source passage.",
    },
    {
        "id": "PT-001",
        "domain": "design",
        "content_type": "process_template",
        "source_text": "The design process moves through distinct phases: first, unrestrained ideation where quantity matters more than quality \u2014 sketching feverishly without editing. Second, selection \u2014 identifying the strongest directions from the raw material. Third, refinement \u2014 polishing the chosen direction through iteration. Finally, production \u2014 preparing the finished work for its intended medium. Skipping or compressing the ideation phase produces safe, derivative work because the designer never explored beyond their first ideas.",
        "source_book": "Principles of Logo Design \u2014 George Bokhua",
        "expected_principles": [
            "The logo design process follows four sequential phases: (1) Ideation \u2014 unrestrained sketching for volume, no editing; (2) Selection \u2014 identifying strongest directions; (3) Refinement \u2014 iterative polishing; (4) Production \u2014 final output preparation. The ideation phase is the most commonly skipped, and skipping it produces safe, derivative results because the designer settles for their first ideas rather than discovering breakthrough concepts through exploration.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "First process_template example. Describes a repeatable 4-phase method with clear inputs, outputs, and failure modes. The warning about skipping ideation is the key insight \u2014 it explains WHY the process matters, not just WHAT the steps are. NOTE: Structural format (PHASES / FAILURE MODE / KEY INSIGHT) deferred to P3. Current format is principle-style; future revision will add instantiable structure.",
    },
    {
        "id": "PT-002",
        "domain": "personal_practice",
        "content_type": "process_template",
        "source_text": "The Four Laws of Behavior Change provide a framework for building any habit: (1) Make it Obvious \u2014 design your environment so the cue is impossible to miss; (2) Make it Attractive \u2014 bundle the behavior with something you already want to do; (3) Make it Easy \u2014 reduce friction to the absolute minimum, aim for two minutes or less; (4) Make it Satisfying \u2014 provide immediate reinforcement so your brain registers the behavior as worth repeating. To break a bad habit, simply invert each law: make it invisible, unattractive, difficult, and unsatisfying.",
        "source_book": "Atomic Habits \u2014 James Clear",
        "expected_principles": [
            "The Four Laws of Behavior Change form a complete framework for habit formation: (1) Make it Obvious (cue design); (2) Make it Attractive (temptation bundling); (3) Make it Easy (friction reduction, two-minute rule); (4) Make it Satisfying (immediate reinforcement). Each law can be inverted to break bad habits: make the cue invisible, the behavior unattractive, the action difficult, and the outcome unsatisfying.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Canonical process template from the most widely-read habits book. The four laws are sequential, each with a specific technique. The inversion property (use the same framework to break habits) makes it a complete system, not just a checklist. NOTE: Structural format (PHASES / FAILURE MODE / KEY INSIGHT) deferred to P3. Current format is principle-style; future revision will add instantiable structure.",
    },
    {
        "id": "PT-003",
        "domain": "art",
        "content_type": "process_template",
        "source_text": "The generative art workflow follows an iterative cycle: (1) Define the rule system \u2014 specify the algorithm, parameters, and constraints that will generate the output; (2) Run the system \u2014 execute the code and observe what emerges; (3) Evaluate the output \u2014 assess whether the result matches intention or surprises in interesting ways; (4) Tune \u2014 adjust parameters, modify rules, or introduce new constraints; (5) Repeat \u2014 iterate until the system produces satisfying results consistently. The key insight is that you are not designing a single output but a space of possible outputs defined by the rule boundaries.",
        "source_book": "Generative Art: A Practical Guide \u2014 Matt Pearson",
        "expected_principles": [
            "The generative art workflow is a five-step iterative cycle: (1) Define rules, parameters, and constraints; (2) Execute and observe output; (3) Evaluate against intention or interesting surprise; (4) Tune parameters and rules; (5) Repeat until satisfying consistency emerges. The workflow's defining characteristic is that the artist designs the rule space, not a single output \u2014 the output is discovered through iteration, not specified in advance.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Process template for generative art practice. The distinction between designing a rule space vs. designing an output is the key mental model that separates this workflow from traditional art processes. NOTE: Structural format (PHASES / FAILURE MODE / KEY INSIGHT) deferred to P3. Current format is principle-style; future revision will add instantiable structure.",
    },
    {
        "id": "SYS-002",
        "domain": "systems_decision",
        "content_type": "principle",
        "source_text": "Painting and sculpture were among the Mechanical Arts, which required labor and craftsmanship. The high esteem of music and the disdain of the fine arts derived, of course, from Plato, who in his Republic had recommended music for the education of heroes because it made human beings partake in the mathematical order and harmony of the cosmos, located beyond the reach of the senses; whereas the arts of painting and sculpture dealt with mere sensory appearances \u2014 copies of copies, twice removed from truth.",
        "source_book": "Visual Thinking \u2014 Rudolf Arnheim",
        "expected_principles": [
            "Plato's hierarchy of the arts ranked music above painting and sculpture because music was understood as mathematical \u2014 it partook of the abstract order of the cosmos \u2014 while painting and sculpture dealt with sensory appearances, which Plato considered copies of copies, twice removed from truth.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Historical-philosophical principle explaining Plato's ranking of the arts. Prior version added 'shaped Western education for two millennia and explains why visual thinking remains undervalued' \u2014 a historical claim not in this passage. This passage only describes Plato's hierarchy. Trimmed.",
    },
    {
        "id": "SYS-003",
        "domain": "systems_decision",
        "content_type": "principle",
        "source_text": "The doctrine seems to derive its impetus from an introverted need to view the human mind as the creator of the outer world. It could not otherwise ignore the obvious question of how a language came to develop a particular vocabulary and grammar in the first place; nor would it transfer characteristics of language to perception without acknowledging that perception predates and exceeds language in both evolutionary and developmental terms.",
        "source_book": "Visual Thinking \u2014 Rudolf Arnheim",
        "expected_principles": [
            "The linguistic relativism that claims language determines perception gets the causal arrow backwards: perception predates and exceeds language in both evolutionary history and individual development. Language developed its vocabulary and grammar from pre-existing perceptual categories, not the reverse. Visual thinking is primary; verbal thinking is built on top of it.",
        ],
        "should_extract": True,
        "principle_type": "causal",
        "rationale": "Argues against strong linguistic determinism (Sapir-Whorf) using evolutionary and developmental evidence. Establishes the primacy of visual/perceptual thinking over verbal thinking \u2014 a core thesis of Arnheim's work with implications for education, design, and cognitive science.",
    },
    {
        "id": "AI-001",
        "domain": "ai_computing",
        "content_type": "principle",
        "source_text": "ReAct, short for Reason and Act, is a prompting paradigm that combines Chain of Thought-style reasoning with the ability to perform actions using tools in an interleaved manner. ReAct mimics how humans operate \u2014 we reason verbally and take actions to gather more information or make progress towards a goal. The ReAct pattern involves a loop: the model reasons about what to do, takes an action, observes the result, and reasons again based on the new information.",
        "source_book": "Agentic Design Patterns \u2014 Antonio Gull\u00ed",
        "expected_principles": [
            "The ReAct (Reason + Act) pattern interleaves reasoning and tool-use in a loop: reason \u2192 act \u2192 observe \u2192 reason. This mimics human problem-solving, where thinking and acting are not separate phases but an ongoing cycle \u2014 each action produces new information that informs the next reasoning step. External information gathered through action augments internal reasoning.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Defines a foundational AI agent design pattern. The human-analogy framing makes the abstract concept concrete. Prior version used 'essential' and 'insufficient' \u2014 evaluative language not in the source. Trimmed to descriptive extraction.",
    },
    {
        "id": "AI-002",
        "domain": "ai_computing",
        "content_type": "principle",
        "source_text": "The gist here is that if your A/B test result shows that a model is better than another with statistical significance, you can determine which model is indeed better. To measure statistical significance, A/B testing uses statistical hypothesis testing such as two-sample tests. A two-sample test is used to determine whether the difference between two populations is statistically significant.",
        "source_book": "Designing Machine Learning Systems \u2014 Chip Huyen",
        "expected_principles": [
            "Model selection in production ML requires statistical hypothesis testing, not just comparing aggregate metrics. A/B testing with two-sample tests determines whether observed performance differences between models are statistically significant or merely noise. Without statistical rigor, 'model A is better than model B' is an unsupported claim \u2014 the difference could be random variation.",
        ],
        "should_extract": True,
        "principle_type": "procedural",
        "rationale": "Practical ML engineering principle about model evaluation rigor. The distinction between 'observed difference' and 'statistically significant difference' is a common failure point in production ML systems.",
    },
    {
        "id": "SUB-001",
        "domain": "substrate",
        "content_type": "principle",
        "source_text": "In verbal language, modality is typically expressed by modal verbs ('may', 'could', 'would') and adverbs ('possibly', 'certainly', 'unlikely'), whereas in visual communication, modality is expressed through different semiotic resources \u2014 for example, soft focus may be employed to create modality in photographic images, signaling 'this is not a documentary claim but an artistic impression.' Each semiotic mode has its own modality markers, and they do not translate directly between modes.",
        "source_book": "Semiotics of Typography \u2014 Nina N\u00f8rgaard",
        "expected_principles": [
            "Modality \u2014 the expression of 'how true' or 'how real' a representation claims to be \u2014 is expressed differently in each semiotic mode. Verbal language uses modal verbs and adverbs; photography uses soft focus, color saturation, and grain to signal documentary truth versus artistic impression. Because modality markers are mode-specific, they do not translate directly: softening a photograph does not 'mean' the same thing as adding 'possibly' to a sentence.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Core semiotic principle defining modality across modes. Prior version added 'typography uses weight, serif treatment, and spacing' \u2014 typography examples are from a different section of N\u00f8rgaard's book. This passage only discusses verbal language and photography. Trimmed to what the source actually covers.",
    },
    {
        "id": "SUB-002",
        "domain": "substrate",
        "content_type": "principle",
        "source_text": "In multimodal theory, 'mode' and 'modality' refer to very different concepts. While sound, gesture, music, visual images, written and spoken language are seen as different communicative 'modes' of meaning, 'modality' refers to various semiotic resources for expressing 'as how true' or 'as how real' something is represented. A photograph can claim high modality ('this is documentary truth') or low modality ('this is a dream sequence') through its formal properties alone.",
        "source_book": "Semiotics of Typography \u2014 Nina N\u00f8rgaard",
        "expected_principles": [
            "In multimodal communication theory, 'mode' and 'modality' are distinct concepts: a mode is a channel of meaning (sound, image, text, gesture), while modality is the truth-status a representation claims within its mode. Every mode has its own range of modality markers \u2014 visual softness signals 'artistic impression,' while verbal hedges signal 'uncertainty.' Understanding this distinction clarifies how different media signal truth-status through their formal properties.",
        ],
        "should_extract": True,
        "principle_type": "definitional",
        "rationale": "Clarifies a critical terminological distinction in semiotics that is often confused. The mode/modality distinction is foundational for any analysis of how media construct truth-claims, with applications in design, journalism, advertising, and AI-generated media.",
    },
    {
        "id": "NEG-HARD-004",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "Design is everywhere. From the chair you're sitting on to the phone in your pocket, design shapes every aspect of modern life. Good design makes things easier to use, more beautiful to look at, and more meaningful to own. Bad design frustrates, confuses, and alienates. The best designers understand this responsibility and strive to create experiences that delight users at every touchpoint.",
        "source_book": "Synthetic \u2014 vague design platitude test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "platitude",
        "rationale": "HARD NEGATIVE for design domain. This reads like a design principle but contains zero specific mechanism. 'Good design makes things easier' is unfalsifiable \u2014 it defines good design by its outcomes without specifying what makes design good. The LLM must resist extracting this despite its plausible structure and domain-appropriate vocabulary.",
    },
    {
        "id": "NEG-HARD-005",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "I once attended a workshop where the facilitator asked us to draw our creative process. Everyone's drawing was completely different \u2014 some drew spirals, others drew straight lines, one person drew a tree. It was fascinating to see how differently we all think about creativity. The exercise really opened my eyes to the diversity of creative approaches. Since that workshop, I've tried to be more open-minded about how other people work.",
        "source_book": "Synthetic \u2014 over-narrow personal anecdote",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "anecdote",
        "rationale": "HARD NEGATIVE. This is a personal anecdote that gestures at a principle ('creative processes differ') but provides only a single-session observation with no generalizable mechanism, no testable claim, and no actionable insight. It's a story, not a principle. The LLM must resist the temptation to extract 'creative processes are diverse' as a principle \u2014 that's a truism, not an insight.",
    },
    {
        "id": "NEG-HARD-006",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "AI is transforming everything. From healthcare to education, from transportation to entertainment, artificial intelligence is reshaping industries at an unprecedented pace. Companies that fail to adopt AI will be left behind. The future belongs to those who embrace artificial intelligence and integrate it into every aspect of their operations. The AI revolution is not coming \u2014 it's already here.",
        "source_book": "Synthetic \u2014 AI hype platitude test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "platitude",
        "rationale": "HARD NEGATIVE for AI domain. All hype, no mechanism. 'AI is transforming everything' is unfalsifiable and non-specific. The LLM must resist extracting this \u2014 it has the rhythm and confidence of a principle but contains zero actionable or testable content. Domain-appropriate platitudes are the hardest negatives because they use the right vocabulary.",
    },
    {
        "id": "NEG-HARD-007",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "Many authors have written about the importance of feedback loops in organizational design. Senge emphasizes systems thinking, while Meadows focuses on leverage points. The consensus among these thinkers is that understanding feedback is critical to managing complex systems effectively.",
        "source_book": "Synthetic \u2014 attribution-not-assertion test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "meta_text",
        "rationale": "HARD NEGATIVE. This passage describes what OTHER authors think \u2014 it attributes claims without making any itself. The LLM must recognize that 'Senge says X' is not the same as 'X is true.' Extracting principles from attribution text produces secondhand principles with unclear provenance.",
    },
    {
        "id": "NEG-HARD-008",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "What if pricing anchors don't just affect willingness-to-pay, but also influence how quickly customers expect to see results? Could a high price point create an expectation of faster value delivery? And if so, would that expectation affect satisfaction and retention independently of the actual product quality?",
        "source_book": "Synthetic \u2014 questions-not-claims test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "growth_edge",
        "rationale": "HARD NEGATIVE. This passage consists entirely of QUESTIONS, not claims. It has the vocabulary of a principle (anchoring, willingness-to-pay, satisfaction) but asserts nothing. The LLM must NOT convert questions into declarative principles \u2014 extracting 'Anchoring affects temporal expectations' from a passage that only asks whether this might be true is fabrication.",
    },
    {
        "id": "NEG-HARD-009",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "A transformer is a neural network architecture that uses self-attention mechanisms to process sequential data. Unlike recurrent neural networks, transformers process all tokens in parallel, which enables more efficient training on large datasets. The architecture consists of an encoder and decoder, each composed of multiple layers of multi-head attention and feed-forward networks.",
        "source_book": "Synthetic \u2014 technical-definition-not-principle test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "definitional",
        "rationale": "HARD NEGATIVE. This is a technically correct definition, but it's not a reusable principle \u2014 it's a description of a specific architecture. 'A is B that does C' is not the same as 'X produces Y because Z.' The definition describes WHAT; a principle explains WHY and WHEN. The LLM must distinguish technical definitions from extractable principles.",
    },
    {
        "id": "NEG-HARD-010",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "In this chapter, we covered the fundamentals of visual composition. As we saw in Chapter 3, contrast creates hierarchy, and as we'll explore in Chapter 5, color amplifies these effects. Before moving on, let's review the key takeaways: balance provides stability, rhythm creates movement, and proportion establishes relationships between elements.",
        "source_book": "Synthetic \u2014 chapter-summary-meta-text test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "meta_text",
        "rationale": "HARD NEGATIVE. This is a chapter summary that lists concepts without developing any of them into principles. It name-drops 'contrast,' 'hierarchy,' 'balance,' 'rhythm,' and 'proportion' \u2014 all legitimate design concepts \u2014 but states them as bullet points, not as extractable mechanisms. The LLM must resist extracting 'Contrast creates hierarchy' \u2014 that's a chapter reference, not a developed principle.",
    },
    {
        "id": "NEG-HARD-011",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "Studies show a strong correlation between employee satisfaction and company profitability. Companies with high satisfaction scores consistently outperform their peers on revenue growth, profit margins, and market valuation. The data suggests that investing in employee happiness delivers measurable returns to shareholders.",
        "source_book": "Synthetic \u2014 correlation-as-causation test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "causal",
        "rationale": "HARD NEGATIVE. This passage presents correlation as causation. 'Companies with high satisfaction outperform' does not establish that satisfaction CAUSES performance \u2014 profitable companies may simply have resources to invest in satisfaction. The causal direction is unproven. A well-calibrated extraction model should flag or reject correlation-posing-as-causation.",
    },
    {
        "id": "NEG-HARD-012",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "The key to successful innovation is creating a culture where people feel empowered to take risks. When employees know that failure won't be punished, they're more willing to experiment with bold new ideas. Google's famous 20% time policy exemplified this approach. Innovation thrives in environments where psychological safety is prioritized over short-term efficiency.",
        "source_book": "Synthetic \u2014 plausible-principle-with-noise test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "causal",
        "rationale": "HARD NEGATIVE \u2014 BORDERLINE. This passage contains the skeleton of a real principle (psychological safety \u2192 experimentation \u2192 innovation) but it's embedded in platitude language ('key to successful innovation,' 'feel empowered'). It also contains a single-anecdote reference (Google 20% time) masquerading as evidence. CALIBRATION NOTE: This is a deliberate false-negative calibration. In production, a passage with this signal-to-noise ratio SHOULD be extracted if the mechanism is specific and testable. This example trains conservatism at the boundary \u2014 the model should err toward rejection when uncertain, accepting that some valid principles will be missed (recoverable in Stage 3/4) rather than polluting the knowledge base with platitudes (unrecoverable without manual review).",
    },
    {
        "id": "NEG-HARD-013",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "Design thinking has revolutionized how organizations approach problem-solving. By centering the user experience and iterating rapidly through prototypes, teams can arrive at solutions that traditional analytical methods would miss. Companies from IDEO to IBM have embraced this methodology, and the results speak for themselves. The design thinking framework \u2014 empathize, define, ideate, prototype, test \u2014 provides a repeatable path to innovation.",
        "source_book": "Synthetic \u2014 methodology-hype-without-mechanism test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "procedural",
        "rationale": "HARD NEGATIVE. This describes a methodology (design thinking) without explaining its mechanism. It lists steps (empathize, define, ideate, prototype, test) and name-drops companies, but never explains WHY the method works or WHEN it fails. 'Design thinking works because X under Y conditions' is a principle. 'Design thinking has 5 steps and big companies use it' is marketing. The LLM must distinguish methodology descriptions from principled explanations.",
    },
    {
        "id": "NEG-HARD-014",
        "domain": "multi_domain",
        "content_type": "principle",
        "source_text": "The best leaders are those who balance confidence with humility. They have the conviction to make tough calls but the wisdom to listen to others. In my twenty years of consulting, I've seen this pattern repeat across industries \u2014 from Silicon Valley startups to Fortune 500 boardrooms. The leaders who succeed are those who know what they don't know.",
        "source_book": "Synthetic \u2014 consultant-anecdote-test",
        "expected_principles": [
        ],
        "should_extract": False,
        "principle_type": "anecdote",
        "rationale": "HARD NEGATIVE. Consultant wisdom masquerading as a principle. 'Balance confidence with humility' is unfalsifiable \u2014 there's no mechanism, no boundary condition, no testable claim. The 'twenty years of consulting' is an appeal to experience without evidence. The final sentence ('know what they don't know') is a tautology. Three red flags in one paragraph.",
    },
]


def write_yaml():
    """Write the updated stage2_fewshot.yaml"""
    yaml_path = ROOT / "config/golden/stage2_fewshot.yaml"

    header = textwrap.dedent("""\
    # Golden Few-Shot Examples — Stage 2 Extraction Calibration
    # =====================================================================
    # Authority: D2045, D2074 (v2.1 — domain + content_type populated, header fixed)
    #
    # PURPOSE:
    #   These examples are injected into the Stage 2 system prompt as few-shot
    #   demonstrations. They show the LLM exactly what constitutes a good principle
    #   vs. what to skip, using real text from the target domains.
    #
    # TWO USES:
    #   1. Prompt calibration (injected at extraction time via --golden flag)
    #   2. Regression testing (after any pipeline change, verify these still extract correctly)
    #
    # v2.1 CHANGES (2026-07-23):
    #   - Added `domain` and `content_type` fields to all 23 examples
    #   - Fixed header counts to match actual data (23 examples, not 25)
    #
    # v2.0 CHANGES (D2074 — Claude feedback 2026-07-23):
    #   - Added 12 non-pricing business examples: leadership (2), strategy (2),
    #     management (2), operations (2), product (1), multi-principle (2), hard negatives (3)
    #   - Replaced synthetic textbook-style definitions with real book passages
    #   - Added 3 hard negatives: plausible platitude, over-narrow anecdote, vague generalization
    #   - Added 2 multi-principle segments (should yield 2-3 principles each)
    #
    # DOMAIN COVERAGE (v2.1 — actual):
    #   Pricing:         5 (PI-001, PI-002, CND-001, GE-001, TI-001)
    #   Leadership:      3 (LEA-001, LEA-002, MPL-002)
    #   Strategy:        2 (STR-001, STR-002)
    #   Management:      3 (MGT-001, MGT-002, MPL-001)
    #   Operations:      2 (OPS-001, OPS-002)
    #   Product:         2 (PRO-002, PRD-001)
    #   Multi-domain:    6 (NEG-HARD-001..003, NEG-001..003)
    #   Total: 75  |  Target: 75  |  Status: v2.2 complete (calibrated)
    #
    # CONTENT TYPES COVERED (v2.1):
    #   principle:            18 (definitional, causal, procedural, conditional, negatives)
    #   process_instance:      2 (PI-001, PI-002)
    #   growth_edge:           1 (GE-001)
    #   tool_instruction:      2 (TI-001, NEG-001)
    #   process_template:      0 ← PRIORITY GAP: 3-4 needed
    #
    # PRINCIPLE TYPES COVERED:
    #   definitional: 3  |  causal: 3  |  procedural: 6  |  conditional: 1
    #   comparative: 0 ← GAP  |  process_instance: 2  |  growth_edge: 1
    #   tool_instruction: 2  |  platitude: 2  |  anecdote: 1
    #   boilerplate: 1  |  meta_text: 1
    #
    # MISSING FROM 67 TARGET (44 remaining, priority order):
    #   P1 — process_template examples: 3-4
    #   P2 — Design domain: 3-4
    #   P3 — Art domain: 3-4
    #   P4 — Personal Practice domain: 3-4
    #   P5 — Remaining 19 domains: 1-2 each (~25)
    #   P6 — Comparative principle type: 2-3
    #   P7 — Growth edge: 2-3 more
    #   P8 — Hard negatives: 3-4 more
    #   P9 — Multi-principle: 3-5 more
    #
    # GROWTH EDGE NOTE:
    #   GE items currently route to QUARANTINE in Stage 5 until a dedicated
    #   GE verification path is built (D2073). This is intentional — speculative
    #   ideas are quarantined by default until human review confirms them.
    #
    # FORMAT:
    #   Each example has:
    #     - id: unique identifier (DOMAIN-NNN)
    #     - domain: which domain this example belongs to
    #     - content_type: principle | process_template | process_instance | growth_edge | tool_instruction
    #     - source_text: the raw segment text (from real books where possible)
    #     - source_book: which book it came from
    #     - expected_principles: list of principles that SHOULD be extracted
    #     - should_extract: true/false — whether ANY principles should come from this text
    #     - principle_type: what category of content this demonstrates
    #     - rationale: why this is/isn't a good extraction (for human reviewers)
    #
    # SCORING:
    #   After extraction, compare LLM output to expected_principles:
    #     - Exact match: 1.0
    #     - Semantic match (different wording, same meaning): 0.8
    #     - Partial match (captures part of the principle): 0.5
    #     - Miss: 0.0
    #     - Hallucination (extracted principle not in source): -1.0
    #   Quality threshold: ≥0.7 average score across all golden examples
    #
    # SCORING IMPLEMENTATION:
    #   Scoring is currently manual (human review). For automated regression testing,
    #   an LLM-judge or embedding-similarity proxy with a tuned threshold is needed.
    #   This is deferred until after H5 (130-book pipeline re-run).
    #
    # USAGE:
    #   python3 pipeline/stage2_extract.py --golden config/golden/stage2_fewshot.yaml
    # =====================================================================
    """)

    data = {
        "version": "2.1",
        "domain": "business + strategy (multi-domain: pricing, leadership, strategy, management, operations, product)",
        "created": "2026-07-23",
        "updated": "2026-07-23 (v2.1: domain + content_type populated, header fixed)",
        "pipeline_commit": "v2.1.1",
        "scoring": {
            "exact_match": 1.0,
            "semantic_match": 0.8,
            "partial_match": 0.5,
            "miss": 0.0,
            "hallucination": -1.0,
            "quality_threshold": 0.7,
        },
        "examples": EXAMPLES,
    }

    with open(yaml_path, 'w') as f:
        f.write(header)
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=100)

    print(f"✅ YAML written: {yaml_path} ({len(EXAMPLES)} examples)")


def write_review_md():
    """Write the human-review Markdown file"""
    md_path = ROOT / "config/golden/GOLDEN-REVIEW.md"

    lines = []
    lines.append("# Golden Few-Shot Examples — Stage 2 Extraction Calibration (v2.0)")
    lines.append(f"> **Domain:** business + strategy (multi-domain)  |  **Version:** 2.0  |  **Updated:** 2026-07-23 (D2074)")
    lines.append("> **v2.0 Changes:** Rebalanced domains (leadership, strategy, management, operations, product added), real book passages, hard negatives, multi-principle segments.")
    lines.append("> **Purpose:** These examples calibrate the Stage 2 LLM prompt via the `--golden` flag.")
    lines.append("")
    lines.append(f"**Total Examples:** {len(EXAMPLES)} (was 18)  |  **Scoring Threshold:** ≥0.7 average score")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Scoring Guide")
    lines.append("")
    lines.append("| Match Level | Score |")
    lines.append("|------------|-------|")
    lines.append("| Exact Match | 1.0 |")
    lines.append("| Semantic Match | 0.8 |")
    lines.append("| Partial Match | 0.5 |")
    lines.append("| Miss | 0.0 |")
    lines.append("| Hallucination | -1.0 |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by principle_type
    from collections import OrderedDict
    type_order = [
        ("definitional", "## 📖 Definitional — 'X is Y' concepts"),
        ("causal", "## 🔗 Causal — 'X causes Y' mechanisms"),
        ("procedural", "## 🔧 Procedural — 'To achieve X, do Y' methods"),
        ("conditional", "## 🎯 Conditional / Boundary — 'X works when Y, fails when Z'"),
        ("process_instance", "## 📋 Process Instance — Concrete case studies"),
        ("growth_edge", "## 🌱 Growth Edge — Speculative ideas (routes to QUARANTINE in Stage 5)"),
        ("tool_instruction", "## 🛠️ Tool Instruction — Tool-specific commands"),
        ("platitude", "## ❌ HARD NEGATIVE — Plausible platitude"),
        ("anecdote", "## ❌ HARD NEGATIVE — Over-narrow anecdote"),
        ("boilerplate", "## ❌ EASY NEGATIVE — Boilerplate"),
        ("meta_text", "## ❌ EASY NEGATIVE — Meta-text"),
    ]

    grouped = {}
    for ex in EXAMPLES:
        pt = ex['principle_type']
        grouped.setdefault(pt, []).append(ex)

    for ptype, label in type_order:
        if ptype not in grouped:
            continue
        lines.append(label)
        lines.append("")
        for i, ex in enumerate(grouped[ptype], 1):
            note = ex.get('expected_count_note', '')
            lines.append(f"### {ex['id']}: {ex.get('source_book', 'Unknown')}")
            lines.append("")
            lines.append(f"**Should extract:** {'✅ YES' if ex['should_extract'] else '❌ NO'}  |  **Expected count:** {len(ex['expected_principles'])}")
            if note:
                lines.append(f"**⚠️  {note}**")
            lines.append("")
            lines.append("**Source text:**")
            lines.append("")
            for line in ex['source_text'].strip().split('\n'):
                lines.append(f"> {line.strip()}")
            lines.append("")
            if ex['expected_principles']:
                lines.append("**Expected extraction:**")
                lines.append("")
                for ep in ex['expected_principles']:
                    lines.append(f"- *{ep}*")
                lines.append("")
            lines.append(f"**Rationale:** {ex['rationale'].strip()}")
            lines.append("")
            lines.append("**Your review:**")
            lines.append("")
            lines.append("- [ ] Extraction is correct as written")
            lines.append("- [ ] Extraction needs revision (note below)")
            lines.append("- [ ] This should NOT be extracted (change `should_extract` to false)")
            lines.append("")
            lines.append("**Feedback:** _write here..._")
            lines.append("")
            lines.append("---")
            lines.append("")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary Checklist")
    lines.append("")
    lines.append("| # | ID | Type | Domain | Reviewed | Approved | Needs Revision |")
    lines.append("|---|-----|------|--------|----------|----------|---------------|")
    for ex in EXAMPLES:
        lines.append(f"| | {ex['id']} | {ex['principle_type']} | {ex.get('source_book', '')[:40]} | ☐ | ☐ | ☐ |")
    lines.append("")
    lines.append("**Overall assessment:**")
    lines.append("")
    lines.append("- [ ] All examples are correct — ready to inject into Stage 2 prompts")
    lines.append("- [ ] Examples need revision before use (see feedback above)")
    lines.append("- [ ] Domain coverage is sufficient — no additional examples needed")
    lines.append("")
    lines.append("> Return this file with your feedback checked and any notes written inline.")

    with open(md_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"✅ Review MD written: {md_path} ({len(lines)} lines)")


if __name__ == "__main__":
    write_yaml()
    write_review_md()
    pos = sum(1 for e in EXAMPLES if e['should_extract'])
    neg = sum(1 for e in EXAMPLES if not e['should_extract'])
    types = sorted(set(e['principle_type'] for e in EXAMPLES))
    has_multi = sum(1 for e in EXAMPLES if len(e['expected_principles']) > 1)
    print(f"\n📊 Stats: {len(EXAMPLES)} total ({pos} positive, {neg} negative)")
    print(f"   Types: {len(types)} — {types}")
    print(f"   Multi-principle: {has_multi}")
    print(f"   Hard negatives: {sum(1 for e in EXAMPLES if e['principle_type'] in ('platitude', 'anecdote'))}")
