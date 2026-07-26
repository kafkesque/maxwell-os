# Golden Few-Shot Examples — Stage 2 Extraction Calibration (v2.0)
> **Domain:** business + strategy (multi-domain)  |  **Version:** 2.0  |  **Updated:** 2026-07-23 (D2074)
> **v2.0 Changes:** Rebalanced domains (leadership, strategy, management, operations, product added), real book passages, hard negatives, multi-principle segments.
> **Purpose:** These examples calibrate the Stage 2 LLM prompt via the `--golden` flag.

**Total Examples:** 75 (was 18)  |  **Scoring Threshold:** ≥0.7 average score

---

## Scoring Guide

| Match Level | Score |
|------------|-------|
| Exact Match | 1.0 |
| Semantic Match | 0.8 |
| Partial Match | 0.5 |
| Miss | 0.0 |
| Hallucination | -1.0 |

---

## 📖 Definitional — 'X is Y' concepts

### LEA-002: Multipliers — Liz Wiseman

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Here's why: Diminishers want to be valued for their intelligence and ideas; in fact, many are desperate for it. On the other hand, Multipliers enjoy finding other people's genius and engaging it. In many ways, Diminishers need Multipliers. It may not be a match made in heaven, but it is a strategy to help you escape a hellish experience, because when you work for a Diminisher, you need to find ways to get your intelligence leveraged without threatening their ego.

**Expected extraction:**

- *Multipliers draw intelligence out of others by finding and engaging other people's genius; Diminishers want to be valued for their own intelligence and ideas. The contrast between these two approaches defines a fundamental leadership dimension — amplify others or center yourself.*

**Rationale:** Definitional contrast: Multiplier vs Diminisher as leadership archetypes. Prior version added 'Diminishers hoard intellectual credit' (source says 'want to be valued for their intelligence') and 'scales organizational intelligence beyond any individual's capacity' (not in this passage). Trimmed to what the source actually says.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### STR-001: Blue Ocean Strategy — W. Chan Kim & Renée Mauborgne

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> What consistently separated winners from losers in creating blue oceans was their approach to strategy. The companies caught in the red ocean followed a conventional approach, racing to beat the competition by building a defensible position within the existing industry order. The creators of blue oceans, surprisingly, didn't use the competition as their benchmark. Instead they followed a different strategic logic that we call value innovation. Value innovation is the cornerstone of blue ocean strategy. We call it value innovation because instead of focusing on beating the competition, you focus on making the competition irrelevant by creating a leap in value for buyers and your company, thereby opening up new and uncontested market space.

**Expected extraction:**

- *Value innovation makes competition irrelevant by creating a leap in value for buyers and the company simultaneously — opening new, uncontested market space rather than fighting for share in existing markets.*

**Rationale:** Core strategic concept from Blue Ocean Strategy. Prior version imported 'simultaneously pursuing differentiation and low cost' from elsewhere in the book — this passage only says 'creating a leap in value.' Trimmed to what the source actually states.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### OPS-001: The Goal — Eliyahu Goldratt

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Alex, the goal is not to reduce operational expense by itself. The goal is not to improve one measurement in isolation. The goal is to reduce operational expense and reduce inventory while simultaneously increasing throughput. Any action that moves you toward these three things simultaneously is productive. Any action that moves only one or two is not productive. Any action that does not move any of the three is pure waste.

**Expected extraction:**

- *Operational productivity is defined by simultaneous improvement across three interdependent metrics — throughput, inventory, and operational expense. Improving only one or two is not productive; improving none is waste. The goal is their joint optimization.*

**Rationale:** Definition of productivity from Theory of Constraints. Operations domain. The original passage defines a concept through triple condition — representative of how operations principles are expressed as interdependent constraints rather than single-variable rules.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-004: Principles of Logo Design — George Bokhua

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The body of work created by modernists laid a solid foundation for modern logo designs. A certain language of form was invented, and there are certain elements that represent a fabric of modernist aesthetic. These include waves, stripes, stars, arrows, cubes, overlapping primitive shapes with exclusion, inclusion, and intersection. Geometric precision was favored over the expressive, and universal appeal was valued over a culture-bound aesthetic.

**Expected extraction:**

- *Modernist design established a universal visual language built on geometric primitives (waves, stripes, stars, arrows, cubes) and boolean operations (exclusion, inclusion, intersection). It prioritized geometric precision and universal appeal over cultural specificity and personal expression.*

**Rationale:** Defines the modernist design language that underpins contemporary logo design. Establishes vocabulary (geometric primitives + boolean operations) and value system (universal over culture-specific).

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-001: Code as Creative Medium — Golan Levin & Tega Brain

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> A 'North Star' for instrument design is to create something 'instantly knowable, yet infinitely masterable.' Consider the pencil, or the piano: its basic principles of operation are simple enough for a child to deduce, yet one can spend a lifetime using it and still find more to say; sophisticated expressions are possible, and mastery is elusive. From the standpoint of systems design, our challenge is to create tools that have this same property: a low floor, a high ceiling, and wide walls.

**Expected extraction:**

- *The ideal creative instrument has three properties: a low floor (simple enough for a novice to start immediately), a high ceiling (capable of sophisticated expression by experts), and wide walls (supporting diverse approaches and styles). This 'instantly knowable, yet infinitely masterable' quality is the North Star for tool, language, and interface design.*

**Rationale:** Widely-cited design framework for creative tools (low floor, high ceiling, wide walls). Originated in computational art education but generalizes to any creative instrument. High-reuse principle.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-002: Code as Creative Medium — Golan Levin & Tega Brain

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> In computational art and design, many responses to the questions of what and why continue historic lines of creative inquiry centered on procedure, connection, abstraction, authorship, the nature of time, and the role of chance. The pursuit of these formal and conceptual concerns in the medium of computation has created new practices and aesthetics, and has also heightened a sensibility to the formal properties of code itself — that code is not merely a tool but a material with its own affordances and constraints.

**Expected extraction:**

- *Computational art extends historic creative concerns (procedure, abstraction, authorship, time, chance) into a new medium, but with a critical distinction: code is not merely a neutral tool but a material with its own affordances and constraints that shape the resulting work.*

**Rationale:** Establishes the philosophical foundation of computational art: it engages with the material properties of code as medium, not just uses code as a tool. The source says code has 'its own affordances and constraints' — that's the extraction boundary. Prior version injected a McLuhan reference not in source.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-003: Generative Art: A Practical Guide — Matt Pearson

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Computers and computing were not the same thing. What hadn't been made apparent to me during my university days was that computation is an abstract idea, not a physical machine. It's the manipulation of ideas according to formal rules. A computer is just one possible embodiment of this idea. Once I understood that computing wasn't about machines but about process and logic, a whole new world of creative possibility opened up.

**Expected extraction:**

- *Computation is an abstract idea — the manipulation of concepts according to formal rules — not a physical machine. A computer is merely one embodiment of computation. Recognizing this distinction unlocks creative approaches: computation can be expressed in any medium, not just electronics.*

**Rationale:** Fundamental reframing that separates the concept of computation from its physical implementation. The intellectual move that makes generative art possible.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-004: Generative Art: A Practical Guide — Matt Pearson

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Some parts bubble and then fade out; others achieve a looping stability. There has been much study of this game, identifying the mathematical 'life' that forms: gliders, toads, boats, blinkers, blocks. What makes Conway's Game of Life so compelling for generative artists is that complex, seemingly organic behavior emerges from a tiny set of deterministic rules applied locally to each cell. You don't design the pattern — you design the rules, and the pattern designs itself.

**Expected extraction:**

- *Generative art operates on emergence: complex, organic-seeming behavior arises from simple, local, deterministic rules applied iteratively. The artist's role shifts from designing the output to designing the rule system — you don't design the pattern, you design the rules, and the pattern designs itself.*

**Rationale:** Defines the core mechanism of generative art: emergence from rule systems. The distinction between designing outputs vs. designing rules is the defining characteristic of the field.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-001: Atomic Habits — James Clear

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Outcomes are about what you get. Processes are about what you do. Identity is about what you believe. When it comes to building habits that last — when it comes to building a system of 1 percent improvements — the problem is not that one level is 'better' or 'worse' than another. All levels of change are useful in their own way. The problem is the direction of change.

**Expected extraction:**

- *Behavior change operates on three levels: outcome (what you get), process (what you do), and identity (what you believe). All levels are useful in their own way. The critical variable is not which level is best, but the direction of change — which level you start from determines whether the change persists.*

**Rationale:** Core framework from Atomic Habits. The three-level model is directly stated in this passage. Prior version imported Clear's Chapter 2 thesis ('most durable change starts from identity outward') which is NOT in this passage — that claim requires a different source text. Trimmed to what the passage actually says: three levels exist, direction matters.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-003: Atomic Habits — James Clear

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The first three laws of behavior change — make it obvious, make it attractive, and make it easy — increase the odds that a behavior will be performed this time. The fourth law of behavior change — make it satisfying — increases the odds that a behavior will be repeated next time. It completes the habit loop.

**Expected extraction:**

- *The Four Laws of Behavior Change form a complete loop: make it obvious, make it attractive, make it easy, and make it satisfying. The first three laws drive initiation — increasing the odds a behavior is performed this time. The fourth law drives repetition — increasing the odds a behavior is performed next time. Without satisfaction, behaviors extinguish regardless of how easy or obvious they are.*

**Rationale:** Summarizes the book's central framework. Prior version imported cue/craving/response/reward habit-loop terminology — not in this passage. This passage only names the four laws and distinguishes initiation (first three) from repetition (fourth). Trimmed.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-005: The War of Art — Steven Pressfield

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Resistance seems to come from outside ourselves. We locate it in spouses, jobs, bosses, kids. 'Peripheral opponents,' as Pat Riley used to say when he coached the Los Angeles Lakers. Resistance is not a peripheral opponent. Resistance arises from within. It is self-generated and self-perpetuated. Resistance is the enemy within.

**Expected extraction:**

- *Resistance — the force that prevents creative work — feels external but is internally generated. We project it onto spouses, bosses, and circumstances, but it originates within and is self-perpetuating. Recognizing Resistance as self-generated is the prerequisite to overcoming it.*

**Rationale:** Core concept from The War of Art. The internal vs. external attribution distinction is explicitly stated. Prior version added 'external enemies can be avoided; internal ones must be confronted' — a logical inference not stated in this passage. Trimmed to what the source actually says.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-007: A Primer of Visual Literacy — Donis A. Dondis

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Syntax in the context of visual literacy can only mean the orderly arrangement of parts, leaving us with the problem of how we can approach the process of composition with intelligence and knowledge of how compositional decisions will affect the final result. There are no absolute rules, but there is a great deal of understanding of what will occur in terms of meaning if we make certain arrangements of the parts toward organizing and orchestrating the visual means. Many of the guidelines for understanding the meaning in visual form, the syntactic rules, are based on what we know about human perception.

**Expected extraction:**

- *Visual syntax operates not as absolute rules but as predictive guidelines grounded in human perception: certain arrangements reliably produce certain interpretations because of how the human visual system processes information. Effective composition requires understanding these perceptual principles and applying them intelligently to the specific communicative goal, not following a fixed recipe.*

**Rationale:** Defines visual syntax as a perceptual science rather than an aesthetic rulebook. The distinction between 'absolute rules' and 'predictive guidelines grounded in perception' is fundamental to understanding design as a discipline.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-008: A Primer of Visual Literacy — Donis A. Dondis

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Transparency and opacity define each other physically: the former means visual detail that can be seen through so that what is behind it is revealed to the eye; the latter is just the opposite, blocking out, concealing what it visually supersedes. These two poles represent one of the fundamental technique polarities available to the visual communicator.

**Expected extraction:**

- *Transparency and opacity form a fundamental visual polarity: transparency reveals layers and creates depth through visible relationships between foreground and background, while opacity conceals and creates hierarchy through visual dominance. Understanding this polarity gives the designer control over what the viewer sees first, second, and what remains hidden.*

**Rationale:** Defines a fundamental visual design polarity. The technique is simple but the implications for information hierarchy and visual storytelling are profound. A building-block principle for design education.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-010: The Gifts of Imperfection — Brené Brown

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The word compassion is derived from the Latin words pati and cum, meaning 'to suffer with.' I don't believe that compassion is our default response to suffering. I think our first response is usually self-protection. We armor ourselves against pain, or we try to fix it, or we resort to blame. Compassion is a practice — not a personality trait — that requires us to stay present with suffering without trying to solve it.

**Expected extraction:**

- *Compassion is a practice, not a personality trait. The etymology ('to suffer with') reveals that compassion requires the capacity to stay present with suffering — our own or others' — without armoring, fixing, or blaming. Because self-protection is the default response, compassion requires deliberate cultivation, not passive possession.*

**Rationale:** Redefines compassion from trait to practice, using etymology as evidence. The 'practice not trait' reframing has broad application: courage, vulnerability, and creativity can all be understood similarly. High reuse potential across personal practice and leadership.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-007: Generative Design — Bohnacker, Groß, Laub, Lazzeroni

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Generative design has long ceased to be a trade secret among design students; in some universities, it is now firmly integrated into the curriculum. From infographics to the visualization of sound, from the fine arts to architecture, and especially in the realm of communication design and media installations, generative design allows for dynamic, stunning, and fascinating applications.

**Expected extraction:**

- *Generative design has moved from experimental practice to mainstream curriculum across disciplines: infographics, sound visualization, fine arts, architecture, and communication design. Its defining value is dynamism — the ability to create systems that produce varied, responsive outputs rather than fixed artifacts — making it particularly suited to media installations and interactive contexts.*

**Rationale:** Marks the institutional adoption of generative design as a discipline. Defines the value proposition (dynamism over fixity) and maps the application landscape. Useful as a reference principle for understanding the field's scope.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### AI-001: Agentic Design Patterns — Antonio Gullí

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> ReAct, short for Reason and Act, is a prompting paradigm that combines Chain of Thought-style reasoning with the ability to perform actions using tools in an interleaved manner. ReAct mimics how humans operate — we reason verbally and take actions to gather more information or make progress towards a goal. The ReAct pattern involves a loop: the model reasons about what to do, takes an action, observes the result, and reasons again based on the new information.

**Expected extraction:**

- *The ReAct (Reason + Act) pattern interleaves reasoning and tool-use in a loop: reason → act → observe → reason. This mimics human problem-solving, where thinking and acting are not separate phases but an ongoing cycle — each action produces new information that informs the next reasoning step. External information gathered through action augments internal reasoning.*

**Rationale:** Defines a foundational AI agent design pattern. The human-analogy framing makes the abstract concept concrete. Prior version used 'essential' and 'insufficient' — evaluative language not in the source. Trimmed to descriptive extraction.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### SUB-001: Semiotics of Typography — Nina Nørgaard

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> In verbal language, modality is typically expressed by modal verbs ('may', 'could', 'would') and adverbs ('possibly', 'certainly', 'unlikely'), whereas in visual communication, modality is expressed through different semiotic resources — for example, soft focus may be employed to create modality in photographic images, signaling 'this is not a documentary claim but an artistic impression.' Each semiotic mode has its own modality markers, and they do not translate directly between modes.

**Expected extraction:**

- *Modality — the expression of 'how true' or 'how real' a representation claims to be — is expressed differently in each semiotic mode. Verbal language uses modal verbs and adverbs; photography uses soft focus, color saturation, and grain to signal documentary truth versus artistic impression. Because modality markers are mode-specific, they do not translate directly: softening a photograph does not 'mean' the same thing as adding 'possibly' to a sentence.*

**Rationale:** Core semiotic principle defining modality across modes. Prior version added 'typography uses weight, serif treatment, and spacing' — typography examples are from a different section of Nørgaard's book. This passage only discusses verbal language and photography. Trimmed to what the source actually covers.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### SUB-002: Semiotics of Typography — Nina Nørgaard

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> In multimodal theory, 'mode' and 'modality' refer to very different concepts. While sound, gesture, music, visual images, written and spoken language are seen as different communicative 'modes' of meaning, 'modality' refers to various semiotic resources for expressing 'as how true' or 'as how real' something is represented. A photograph can claim high modality ('this is documentary truth') or low modality ('this is a dream sequence') through its formal properties alone.

**Expected extraction:**

- *In multimodal communication theory, 'mode' and 'modality' are distinct concepts: a mode is a channel of meaning (sound, image, text, gesture), while modality is the truth-status a representation claims within its mode. Every mode has its own range of modality markers — visual softness signals 'artistic impression,' while verbal hedges signal 'uncertainty.' Understanding this distinction clarifies how different media signal truth-status through their formal properties.*

**Rationale:** Clarifies a critical terminological distinction in semiotics that is often confused. The mode/modality distinction is foundational for any analysis of how media construct truth-claims, with applications in design, journalism, advertising, and AI-generated media.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-009: Synthetic — technical-definition-not-principle test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> A transformer is a neural network architecture that uses self-attention mechanisms to process sequential data. Unlike recurrent neural networks, transformers process all tokens in parallel, which enables more efficient training on large datasets. The architecture consists of an encoder and decoder, each composed of multiple layers of multi-head attention and feed-forward networks.

**Rationale:** HARD NEGATIVE. This is a technically correct definition, but it's not a reusable principle — it's a description of a specific architecture. 'A is B that does C' is not the same as 'X produces Y because Z.' The definition describes WHAT; a principle explains WHY and WHEN. The LLM must distinguish technical definitions from extractable principles.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## 🔗 Causal — 'X causes Y' mechanisms

### LEA-001: Multipliers — Liz Wiseman

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Diminishers believe that pressure increases performance. They demand people's best thinking, but they don't get it. They haven't created an environment where people feel safe to truly express themselves or their ideas. An unsafe environment yields only the safest ideas. On the other hand, Multipliers know that people are intelligent and will figure things out. They create a safe environment for stretch — they push people beyond their comfort zone while making it safe to fail, to experiment, and to offer incomplete thinking without fear of judgment.

**Expected extraction:**

- *Psychological safety is the precondition for intellectual stretch — pressure without safety yields only the safest ideas, while safety without stretch yields comfort but no growth. Multipliers combine both: they push people beyond their comfort zone while making it safe to fail.*

**Rationale:** Causal mechanism: safety → intellectual risk-taking → better ideas. From leadership domain (Multipliers by Wiseman), a real book passage. Generalizes beyond pricing to any knowledge-work context.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### MGT-002: The Effective Executive — Peter Drucker

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Among the effective executives I have had occasion to observe, there have been people who make decisions fast, and people who make them rather slowly. But without exception, they make personnel decisions slowly and they make them several times before they really commit themselves. Effective executives know that personnel decisions are the most important decisions an executive makes — and that they are also the decisions most likely to be wrong.

**Expected extraction:**

- *Personnel decisions warrant multiple rounds of evaluation before commitment — even decisive executives slow down for hiring and promotion decisions because these are simultaneously the most important and the most error-prone decisions an organization makes.*

**Rationale:** Causal principle: personnel decisions are highest-stakes → warrant multiple rounds of slow evaluation. From management domain. Real Drucker passage, slightly noisier than textbook prose.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### OPS-002: The Goal — Eliyahu Goldratt

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Alex called me today because you perceive a problem with the bottlenecks you've discovered in your plant. Actually, you are experiencing a combination of several problems. But first things first. From what Alex has told me, your most immediate need is to increase throughput and improve your cash flow. An hour lost at a bottleneck is an hour lost for the entire system. An hour saved at a non-bottleneck is a mirage — it doesn't improve system throughput at all.

**Expected extraction:**

- *An hour lost at a bottleneck is an hour lost for the entire system, but an hour saved at a non-bottleneck produces zero system improvement. Optimization efforts must target constraints, not average utilization.*

**Rationale:** Core Theory of Constraints insight. Causal: bottleneck → system output. Distinguishes between real constraints and non-constraints — a boundary condition that's central to operations thinking. From operations domain.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-001: A Primer of Visual Literacy — Donis A. Dondis

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The process of composition is the most crucial step in visual problem solving. The results of the compositional decisions set the purpose and meaning of the visual statement and carry strong implications for what the viewer receives. It is at this vital stage in the creative process that the visual communicator has the strongest control of the work and the greatest opportunity to express the total mood the work is intended to convey. But the visual mode offers no proscribed structural systems that are absolute. How can we gain control of our complex visual means with some certainty of shared meaning? There are no absolute rules, but there is a great deal of understanding of what will occur in terms of meaning if we make certain arrangements of the parts toward organizing and orchestrating the visual means.

**Expected extraction:**

- *Composition is the highest-leverage stage in visual communication — it is where the communicator has maximum control over meaning and mood, yet visual language lacks absolute rules, requiring designers to develop a deep understanding of how compositional arrangements shape viewer interpretation.*

**Rationale:** Core design principle from a foundational visual literacy textbook. Identifies the causal relationship: compositional decisions → viewer interpretation. The source uses hedged language ('a great deal of understanding of what will occur') — 'predictably' overstated the source's confidence. Removed.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-002: A Primer of Visual Literacy — Donis A. Dondis

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The more abstract the symbol, the more penetration of the public mind is necessary for the education to its meaning. A dove carrying an olive branch became the easily recognized symbol of peace only after widespread cultural education. In this case, some education of the public may be necessary for the message to be clear. But the more abstract the symbol, the more prior knowledge the viewer must bring to decode it.

**Expected extraction:**

- *Symbol abstraction and audience education are inversely proportional: the more abstract a visual symbol, the more cultural penetration and public education is required before it can reliably communicate its intended meaning. Concrete symbols require less decoding effort than abstract ones.*

**Rationale:** Establishes a gradient from concrete to abstract symbol systems and the educational burden each places on the viewer. A fundamental semiotic principle with direct application to logo design, iconography, and visual communication.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-006: A Primer of Visual Literacy — Donis A. Dondis

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> A dot alone in a field relates to the whole, but it stands alone, and the relationship is a mild state of intermodification between it and the square. But when two dots are placed in the same field, they fight for attention in their interaction, creating comparatively individual statements because of their distance from each other and their relationship to the frame. The introduction of a second element transforms a static field into a dynamic composition.

**Expected extraction:**

- *A single element in a visual field creates a static relationship with the frame, but adding a second element transforms the composition into a dynamic system of competing attention — each element now interacts with the other and the frame, making spatial relationships the primary carriers of meaning.*

**Rationale:** Fundamental compositional principle identifying the threshold between static and dynamic composition (one element → two elements). Generalizes beyond dots to any design elements.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-005: Code as Creative Medium — Golan Levin & Tega Brain

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Humans are equipped with an exquisite sensitivity to faces. From infancy, we easily recognize faces and can detect very subtle shifts in expressions, often being able to discern the slightest change in mood and sincerity in ways that remain impossible for computers. Faces also allow us to readily identify family resemblances or recognize friends in crowds. Faces are so central to visual perception that the impairment of our face-processing ability is seen as a disorder, called prosopagnosia, while unconsciously seeing faces where there are none is an almost universal kind of pareidolia.

**Expected extraction:**

- *Human face perception occupies a privileged channel in visual cognition: we detect faces instantly, read micro-expressions beyond current computer capability, and hallucinate faces in random patterns (pareidolia). The impairment of face-processing (prosopagnosia) is classified as a disorder, while unconscious face-detection (pareidolia) is near-universal — indicating the depth and automaticity of this neural mechanism.*

**Rationale:** Describes the cognitive phenomenon of face perception sensitivity. The source describes the mechanism; it does NOT make the design-prescriptive claim ('uniquely powerful design material') that the prior version added. The design application would require a different source passage that explicitly makes that claim.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-002: Atomic Habits — James Clear

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Imagine two people resisting a cigarette. When offered a smoke, the first person says, 'No thanks. I'm trying to quit.' It sounds like a reasonable response, but this person still believes they are a smoker who is trying to be something else. They are hoping their behavior will change while carrying around the same beliefs. The second person says, 'No thanks. I'm not a smoker.'

**Expected extraction:**

- *Identity-based resistance is more effective than willpower-based resistance: saying 'I'm not a smoker' (identity statement) outperforms 'I'm trying to quit' (effort statement) because the former aligns the behavior with a self-concept that makes the undesired action inconsistent with who the person believes themselves to be.*

**Rationale:** Demonstrates the identity-based change model with a concrete, testable example. The linguistic contrast ('I'm trying' vs. 'I'm not') makes the abstract principle tangible and memorable.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-004: Atomic Habits — James Clear

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The more automatic a behavior becomes, the less likely we are to consciously think about it. And when we've done something a thousand times before, we begin to overlook things. We assume that the next time will be just like the last. We're so used to doing what we've always done that we don't stop to question whether it's the right thing to do at all. Many of our failures in performance are largely attributable to a lack of self-awareness.

**Expected extraction:**

- *Automaticity creates a blindness trap: the more practiced a behavior becomes, the less conscious attention we pay to it, causing us to overlook errors, assume stability, and fail to question whether the behavior is still appropriate. Many performance failures are attributable to this lack of self-awareness.*

**Rationale:** Identifies a paradox of expertise: the very automaticity that enables high performance also creates vulnerability to stale thinking. Prior version added 'Mastery requires deliberate disruption of automaticity' — a prescription not in this passage. The source identifies the problem (automaticity → blindness); it does not prescribe the solution. Trimmed to descriptive only.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-006: The War of Art — Steven Pressfield

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Resistance will tell you anything to keep you from doing your work. It will perjure, fabricate, falsify; seduce, bully, cajole. Resistance is protean. It will assume any form, if that's what it takes to deceive you. It will reason with you like a lawyer or jam a nine-millimeter in your face like a stickup man. Resistance has no conscience. It will pledge anything to get a deal, then double-cross you as soon as your back is turned. If you take Resistance at its word, you deserve everything you get. Resistance is always lying and always full of shit.

**Expected extraction:**

- *Resistance is protean — it adapts its tactics to whatever will most effectively prevent the creative from doing the work, shifting between seduction, intimidation, rational argument, and outright deception. Because Resistance has no fixed form, the only reliable countermeasure is to recognize that it is always lying, regardless of how reasonable it sounds.*

**Rationale:** Describes the adaptive, shape-shifting nature of creative Resistance. The 'protean' quality means you cannot develop a single counter-strategy — you must recognize the pattern across its many forms. Expands Pressfield's framework beyond the initial definition.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-007: The War of Art — Steven Pressfield

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The paradox seems to be, as Socrates demonstrated long ago, that the truly free individual is free only to the extent of his own self-mastery. While those who will not govern themselves are condemned to find masters to govern over them.

**Expected extraction:**

- *Freedom and self-mastery are directly proportional, not opposed: the individual who cannot discipline themselves must submit to external discipline. As Socrates demonstrated, the truly free individual is free only to the extent of his own self-mastery, while those who will not govern themselves are condemned to find masters to govern over them.*

**Rationale:** Philosophical principle tracing back to Socratic thought. The source is a direct quote of the Socratic paradox. Prior version added 'Creative freedom requires the internal structure of a professional' — an application to creative practice not in the source. Trimmed to the philosophical extraction. The creative-practice application is valid but belongs in a separate principle with its own source passage.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-008: The Gifts of Imperfection — Brené Brown

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Once you see a pattern, you can't un-see it. Trust me, I've tried. But when the same truth keeps repeating itself, it's hard to pretend that it's just a coincidence. For example, no matter how hard I try to convince myself that I can function on six hours of sleep, anything less than eight hours leaves me impatient, anxious, and foraging for carbohydrates. It's a pattern.

**Expected extraction:**

- *Pattern recognition creates an irreversible awareness: once you've identified a recurring truth about yourself, you cannot return to the state of not-knowing. The data (e.g., 'I am irritable on less than eight hours of sleep') accumulates until denial becomes more costly than acceptance. Self-awareness is a one-way door.*

**Rationale:** Describes the psychological mechanism of self-awareness as irreversible pattern recognition. The 'one-way door' property means self-knowledge compounds — each pattern you see makes the next one easier to spot.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-009: The Gifts of Imperfection — Brené Brown

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Joy is as thorny and sharp as any of the dark emotions. To love someone fiercely, to believe in something with your whole heart, to celebrate a fleeting moment in time, to fully engage in a life that doesn't come with guarantees — these are risks that involve vulnerability and often pain. When we lose our tolerance for discomfort, we lose joy. In fact, addiction research shows us that an intensely positive experience can be as difficult to process as a traumatic one.

**Expected extraction:**

- *Joy and vulnerability are inseparable: the capacity to experience joy requires the capacity to tolerate the vulnerability that accompanies it — the risk of loss, the absence of guarantees. When we lose our tolerance for discomfort, we lose joy alongside it. Addiction research confirms that intensely positive experiences can be as destabilizing as traumatic ones.*

**Rationale:** Inverts the common assumption that joy is 'light' and pain is 'heavy.' Establishes that vulnerability tolerance is the single mechanism underlying both. Prior version imported 'numb'/'numbing' language from PER-011's overlapping passage — this passage uses 'lose tolerance' and 'lose joy,' not 'numb.' Trimmed to source language.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-010: Principles of Logo Design — George Bokhua

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The circle applied as a graphic device works well with a triangular mark since the negative space in relationship to circle and triangle appears balanced. If it was a square, the approach and result would differ. The interaction between the containing shape and the contained mark creates either harmony or tension, and the choice between them is never neutral — it communicates something about the brand.

**Expected extraction:**

- *The relationship between a logo mark and its containing shape is never neutral: a circle creates balanced negative space with angular marks, while a square creates different tension dynamics. The choice of container shape is a communicative decision, not merely a compositional one — it shapes how the brand is perceived before the viewer even processes the mark itself.*

**Rationale:** Demonstrates a specific design principle (container-shape interaction) with concrete examples. The higher-order principle — that every formal choice is also a communicative choice — generalizes beyond logo design.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PER-011: The Gifts of Imperfection — Brené Brown

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> When we lose our tolerance for discomfort, we lose joy. In fact, addiction research shows us that an intensely positive experience can be as difficult to process as a traumatic one. We cannot selectively numb emotions. When we numb the dark, we also numb the light.

**Rationale:** DUPLICATE of PER-009. Same insight (numbing is non-selective) from overlapping Brené Brown source text. ~85% semantic similarity. In production, Stage 3/4 deduplication should suppress the second extraction. Changed to negative: teaches the model that near-identical extractions from overlapping passages should be suppressed, not rewarded.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-008: Generative Design — Bohnacker, Groß, Laub, Lazzeroni

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Processing and vvvv have for many years been the programming environments of choice for artists and designers. However, more recently there has been a shift toward more web-centric applications, giving rise to new coding environments such as p5.js, a JavaScript library that is especially programmed for and by artists, designers, and other web users. This shift reflects a broader movement: creative coding is moving from the desktop to the browser, from standalone applications to networked experiences.

**Expected extraction:**

- *Creative coding tools are migrating from desktop (Processing, vvvv) to browser (p5.js), driven by the web's advantages in distribution, accessibility, and networked interaction. This platform shift is not merely technical — it changes who can access creative coding (anyone with a browser), how work is shared (URL vs. executable), and what kinds of work are possible (networked, collaborative, real-time).*

**Rationale:** Documents a significant platform shift in the creative coding ecosystem. The causal chain (technical shift → accessibility change → new creative possibilities) is clearly articulated. Relevant to tool design and creative technology adoption.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-009: Generative Art: A Practical Guide — Matt Pearson

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> This book is all about the algorithms. It's about the philosophy, aesthetics, and experimentation too, but mostly it's about the algorithms and the tools you use to explore them. You can, theoretically, perform the mathematics behind procedural generative art with a stick of chalk and a large flat rock, but that would make life unnecessarily difficult — especially when we live among the ever-advancing sophistication of modern computing.

**Expected extraction:**

- *The value of computational tools in generative art is not that they enable something previously impossible — the underlying mathematics can be executed with chalk and rock — but that they collapse the iteration cycle from hours to milliseconds. Fast feedback transforms the creative process from planning to exploration: the artist can try, see, adjust, and try again at the speed of thought.*

**Rationale:** Reframes the role of computation in art: not enabling the impossible, but accelerating the possible to the point where the creative process qualitatively changes. The 'chalk and rock' thought experiment is a powerful illustration of the speed-feedback principle.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### SYS-001: Visual Thinking — Rudolf Arnheim

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> In these experiments, an animal or person is made to learn which of two simple stimuli, e.g., two geometrical patterns, is tied to a reward. Since there is no sensible connection between the visual sign and the reward, the task is intellectually unattractive, though practically gainful. The best the rat or monkey or human subject can do is to find out by repeated trials which figure is the winner.

**Expected extraction:**

- *When there is no structural relationship between a stimulus and its associated reward, learning degrades to trial-and-error — a cognitively uninteresting process that produces fragile knowledge. Meaningful learning requires structural congruence: the relationship between sign and outcome must be perceivable, not arbitrary.*

**Rationale:** Bridges perceptual psychology (Arnheim) with learning theory. The 'no sensible connection → trial-and-error → fragile knowledge' causal chain is directly stated. Domain applicability claims ('interface design, education') were removed — those are annotations, not extractions from this source passage.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### SYS-002: Visual Thinking — Rudolf Arnheim

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Painting and sculpture were among the Mechanical Arts, which required labor and craftsmanship. The high esteem of music and the disdain of the fine arts derived, of course, from Plato, who in his Republic had recommended music for the education of heroes because it made human beings partake in the mathematical order and harmony of the cosmos, located beyond the reach of the senses; whereas the arts of painting and sculpture dealt with mere sensory appearances — copies of copies, twice removed from truth.

**Expected extraction:**

- *Plato's hierarchy of the arts ranked music above painting and sculpture because music was understood as mathematical — it partook of the abstract order of the cosmos — while painting and sculpture dealt with sensory appearances, which Plato considered copies of copies, twice removed from truth.*

**Rationale:** Historical-philosophical principle explaining Plato's ranking of the arts. Prior version added 'shaped Western education for two millennia and explains why visual thinking remains undervalued' — a historical claim not in this passage. This passage only describes Plato's hierarchy. Trimmed.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### SYS-003: Visual Thinking — Rudolf Arnheim

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The doctrine seems to derive its impetus from an introverted need to view the human mind as the creator of the outer world. It could not otherwise ignore the obvious question of how a language came to develop a particular vocabulary and grammar in the first place; nor would it transfer characteristics of language to perception without acknowledging that perception predates and exceeds language in both evolutionary and developmental terms.

**Expected extraction:**

- *The linguistic relativism that claims language determines perception gets the causal arrow backwards: perception predates and exceeds language in both evolutionary history and individual development. Language developed its vocabulary and grammar from pre-existing perceptual categories, not the reverse. Visual thinking is primary; verbal thinking is built on top of it.*

**Rationale:** Argues against strong linguistic determinism (Sapir-Whorf) using evolutionary and developmental evidence. Establishes the primacy of visual/perceptual thinking over verbal thinking — a core thesis of Arnheim's work with implications for education, design, and cognitive science.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-011: Synthetic — correlation-as-causation test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> Studies show a strong correlation between employee satisfaction and company profitability. Companies with high satisfaction scores consistently outperform their peers on revenue growth, profit margins, and market valuation. The data suggests that investing in employee happiness delivers measurable returns to shareholders.

**Rationale:** HARD NEGATIVE. This passage presents correlation as causation. 'Companies with high satisfaction outperform' does not establish that satisfaction CAUSES performance — profitable companies may simply have resources to invest in satisfaction. The causal direction is unproven. A well-calibrated extraction model should flag or reject correlation-posing-as-causation.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-012: Synthetic — plausible-principle-with-noise test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> The key to successful innovation is creating a culture where people feel empowered to take risks. When employees know that failure won't be punished, they're more willing to experiment with bold new ideas. Google's famous 20% time policy exemplified this approach. Innovation thrives in environments where psychological safety is prioritized over short-term efficiency.

**Rationale:** HARD NEGATIVE — BORDERLINE. This passage contains the skeleton of a real principle (psychological safety → experimentation → innovation) but it's embedded in platitude language ('key to successful innovation,' 'feel empowered'). It also contains a single-anecdote reference (Google 20% time) masquerading as evidence. CALIBRATION NOTE: This is a deliberate false-negative calibration. In production, a passage with this signal-to-noise ratio SHOULD be extracted if the mechanism is specific and testable. This example trains conservatism at the boundary — the model should err toward rejection when uncertain, accepting that some valid principles will be missed (recoverable in Stage 3/4) rather than polluting the knowledge base with platitudes (unrecoverable without manual review).

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## 🔧 Procedural — 'To achieve X, do Y' methods

### PRO-002: Testing Business Ideas — David Bland

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> When testing a new business idea, don't start by building the product. Instead, create a simple landing page describing the offering with a 'buy now' button that leads to a 'sorry, not yet available' page. Measure click-through rates on the buy button. If fewer than 5% of visitors click, the idea may not have enough demand to pursue.

**Expected extraction:**

- *Demand validation precedes product investment — fake-door tests (a buy button leading to 'not yet available') measure genuine purchase intent at near-zero cost, with <5% click-through signaling insufficient demand.*

**Rationale:** Specific, testable method with threshold. Reusable across product development, market research, and entrepreneurship. One of the few non-pricing examples from v1.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### STR-002: Blue Ocean Strategy — W. Chan Kim & Renée Mauborgne

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> By thinking across conventional boundaries of competition, you can see how to make convention-altering, strategic moves that reconstruct established market boundaries and create blue oceans. The process of discovering and creating blue oceans is not about predicting or preempting industry trends. Nor is it a trial-and-error process of implementing some crazy new business idea that happens to work. Instead, managers are engaged in a structured process that reorders the reality of the market in a fundamentally new way.

**Expected extraction:**

- *Strategic innovation reconstructs market boundaries through a structured process — not trend prediction or random experimentation. The method reorders market reality rather than accepting existing industry structure as given.*

**Rationale:** Procedural insight about HOW to innovate strategically. From strategy domain. Shows that strategic principles are about process, not just positioning.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### MGT-001: The Effective Executive — Peter Drucker

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Effective executives concentrate on the few major areas where superior performance will produce outstanding results. They force themselves to set priorities and stay with their priority decisions. They know that they have no choice but to do first things first — and second things not at all. The alternative is to get nothing done. Effective executives know that they have to get many things done — and done effectively. Therefore, they concentrate — their own time and energy as well as that of their organization — on doing one thing at a time, and on doing first things first.

**Expected extraction:**

- *Effective executives concentrate on the few areas where superior performance produces disproportionate results — they do first things first and second things not at all, because diffused effort across many priorities achieves nothing on any of them.*

**Rationale:** Classic management principle from Drucker. Procedural because it describes HOW to be effective (concentrate, prioritize, do one thing at a time). From management domain — no pricing or marketing content.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PRD-001: Continuous Discovery Habits — Teresa Torres

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> As a product trio gains experience with opportunity solution trees, the shape of their tree will help guide their discovery work. The depth and breadth of the opportunity space reflects the team's current understanding of their target customer. If our opportunity space is too shallow, it can guide us to do more customer interviews. A sprawling opportunity space suggests we need to prioritize and narrow. The shape of the tree IS the diagnosis — it tells you what kind of discovery work you need to do next.

**Expected extraction:**

- *The structure of an opportunity solution tree is a diagnostic tool — shallow trees indicate insufficient customer research, while sprawling trees indicate inadequate prioritization. The tree's shape guides the next discovery action.*

**Rationale:** Procedural principle from product management. The tree structure IS the signal — a meta-principle about how to diagnose your discovery process. From product/tech domain, distinct from pricing and strategy.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### MPL-001: The Effective Executive — Peter Drucker

**Should extract:** ✅ YES  |  **Expected count:** 2

**Source text:**

> Effective executives know where their time goes. They work systematically at managing the little of their time that can be brought under their control. They focus on outward contribution — they gear their efforts to results rather than to work. They build on strengths — their own strengths, the strengths of their superiors, colleagues, and subordinates. And they concentrate on the few major areas where superior performance will produce outstanding results. They do first things first and second things not at all.

**Expected extraction:**

- *Effective executives manage time systematically — they audit where time goes and control what little discretionary time remains.*
- *Effective executives build on strengths — their own strengths, the strengths of their superiors, colleagues, and subordinates — rather than focusing on remediating weaknesses.*

**Rationale:** MULTI-PRINCIPLE SEGMENT. Dense passage from Drucker containing two distinct principles. Principle 1: time management. Principle 2: strengths-based deployment (revised — prior version added 'Deployment by strengths produces results; remediation produces mediocrity' — not in this passage. Trimmed to what the source says).

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### MPL-002: Multipliers — Liz Wiseman

**Should extract:** ✅ YES  |  **Expected count:** 2

**Source text:**

> A leader's job is not to have all the ideas. It's to make sure all the ideas are heard and the best ones win. When you create an environment where the best idea always wins — regardless of whose idea it is — you get better decisions and more engaged people. People stop playing politics and start solving problems. They also take more ownership over the outcomes because they helped shape the solution.

**Expected extraction:**

- *The best-idea-wins culture increases both decision quality and engagement — it replaces politics with problem-solving and transfers ownership to contributors.*
- *A leader's role shifts from idea generator to idea curator — the value is in ensuring all ideas surface, not in having the best one personally.*

**Rationale:** MULTI-PRINCIPLE SEGMENT. Two distinct insights: one about the mechanism (idea meritocracy → quality + ownership), one about the role shift (generator → curator). Tests whether the LLM can separate them.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-003: Principles of Logo Design — George Bokhua

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> For the initial stage, a designer must not fear making mistakes. Now is not the time to worry about the clarity, spacing, form, or silhouette. Instead sketching should be performed as a fever-like activity, pouring ideas on the paper. The more unrestrained, spontaneous, unconscious, and uninhibited, the better. This should be viewed as an exploratory stage where anything is allowed. A designer must generate volume before editing — quantity precedes quality in the ideation phase.

**Expected extraction:**

- *In the ideation phase of design, quantity precedes quality: unrestrained, spontaneous sketching without concern for clarity or correctness produces the raw volume from which strong concepts can later be selected and refined. Premature self-editing kills exploration.*

**Rationale:** Actionable design process principle. Establishes a two-phase model (divergent exploration → convergent editing) that applies across all design disciplines.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-005: Principles of Logo Design — George Bokhua

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Corporate type must be simple and readable; it must also use a neutral sans serif type for main text. Most of the time I advise clients to use a simple sans serif because it's neutral, simple to use, and most devices have it as a default font, meaning it will not be an additional cost. Corporate typography is often a different entity from the logo type — though not always.

**Expected extraction:**

- *Corporate typography should prioritize neutrality and ubiquity over distinction: simple sans-serif fonts ensure readability, cross-platform consistency, and zero licensing cost — separating the functional role of corporate type from the expressive role of logo marks.*

**Rationale:** Practical decision heuristic for typography selection in identity systems. Separates corporate type concerns from logo type concerns.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### ART-006: Code as Creative Medium — Golan Levin & Tega Brain

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> This assignment draws inspiration from the 'Chernoff face' data visualization technique, which leverages this sensitivity by using facial features to represent multivariate data. In Chernoff faces, features such as the eyes, ears, mouth, and nose represent data according to their shape, size, placement, and orientation. Whereas Herman Chernoff used 18 variables to synthesize a face, Paul Ekman and Wallace Friesen's Facial Action Coding System analyzes faces with 46, each variable corresponding to the action of a different facial muscle.

**Expected extraction:**

- *Chernoff faces exploit the human brain's specialized face-processing circuitry for data visualization: facial features (eyes, ears, mouth, nose) encode multivariate data through shape, size, placement, and orientation. This technique maps up to 18 data dimensions onto a single glyph by piggybacking on evolutionarily-ancient perception hardware.*

**Rationale:** Concrete data visualization technique that bridges cognitive science (face perception) and design practice. The connection to Ekman's FACS system enriches the principle with scientific grounding.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### DES-011: Principles of Logo Design — George Bokhua

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Creating an effective combination of pattern and color can be difficult. Seeing how the pattern will re-create and repeat at different scales is a quick way to determine the overall effect. It can be helpful to both the designer and client to create mock-ups of the pattern in use in practical situations. Be sure to use a variety of sizes, such as on a letterhead or on a wall in an office.

**Expected extraction:**

- *Pattern evaluation requires multi-scale testing: a pattern that works at business-card scale may fail as environmental graphics, and vice versa. The designer must test at every scale the pattern will inhabit — letterhead, signage, digital screen, textile — because scale changes the perceptual relationship between pattern elements and can alter the visual effect.*

**Rationale:** Practical design process principle. The multi-scale testing requirement applies to any repetitive visual system — patterns, grids, logos, typography. The insight that scale changes perceptual relationships is a fundamental design truth.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PT-001: Principles of Logo Design — George Bokhua

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The design process moves through distinct phases: first, unrestrained ideation where quantity matters more than quality — sketching feverishly without editing. Second, selection — identifying the strongest directions from the raw material. Third, refinement — polishing the chosen direction through iteration. Finally, production — preparing the finished work for its intended medium. Skipping or compressing the ideation phase produces safe, derivative work because the designer never explored beyond their first ideas.

**Expected extraction:**

- *The logo design process follows four sequential phases: (1) Ideation — unrestrained sketching for volume, no editing; (2) Selection — identifying strongest directions; (3) Refinement — iterative polishing; (4) Production — final output preparation. The ideation phase is the most commonly skipped, and skipping it produces safe, derivative results because the designer settles for their first ideas rather than discovering breakthrough concepts through exploration.*

**Rationale:** First process_template example. Describes a repeatable 4-phase method with clear inputs, outputs, and failure modes. The warning about skipping ideation is the key insight — it explains WHY the process matters, not just WHAT the steps are. NOTE: Structural format (PHASES / FAILURE MODE / KEY INSIGHT) deferred to P3. Current format is principle-style; future revision will add instantiable structure.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PT-002: Atomic Habits — James Clear

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The Four Laws of Behavior Change provide a framework for building any habit: (1) Make it Obvious — design your environment so the cue is impossible to miss; (2) Make it Attractive — bundle the behavior with something you already want to do; (3) Make it Easy — reduce friction to the absolute minimum, aim for two minutes or less; (4) Make it Satisfying — provide immediate reinforcement so your brain registers the behavior as worth repeating. To break a bad habit, simply invert each law: make it invisible, unattractive, difficult, and unsatisfying.

**Expected extraction:**

- *The Four Laws of Behavior Change form a complete framework for habit formation: (1) Make it Obvious (cue design); (2) Make it Attractive (temptation bundling); (3) Make it Easy (friction reduction, two-minute rule); (4) Make it Satisfying (immediate reinforcement). Each law can be inverted to break bad habits: make the cue invisible, the behavior unattractive, the action difficult, and the outcome unsatisfying.*

**Rationale:** Canonical process template from the most widely-read habits book. The four laws are sequential, each with a specific technique. The inversion property (use the same framework to break habits) makes it a complete system, not just a checklist. NOTE: Structural format (PHASES / FAILURE MODE / KEY INSIGHT) deferred to P3. Current format is principle-style; future revision will add instantiable structure.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PT-003: Generative Art: A Practical Guide — Matt Pearson

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The generative art workflow follows an iterative cycle: (1) Define the rule system — specify the algorithm, parameters, and constraints that will generate the output; (2) Run the system — execute the code and observe what emerges; (3) Evaluate the output — assess whether the result matches intention or surprises in interesting ways; (4) Tune — adjust parameters, modify rules, or introduce new constraints; (5) Repeat — iterate until the system produces satisfying results consistently. The key insight is that you are not designing a single output but a space of possible outputs defined by the rule boundaries.

**Expected extraction:**

- *The generative art workflow is a five-step iterative cycle: (1) Define rules, parameters, and constraints; (2) Execute and observe output; (3) Evaluate against intention or interesting surprise; (4) Tune parameters and rules; (5) Repeat until satisfying consistency emerges. The workflow's defining characteristic is that the artist designs the rule space, not a single output — the output is discovered through iteration, not specified in advance.*

**Rationale:** Process template for generative art practice. The distinction between designing a rule space vs. designing an output is the key mental model that separates this workflow from traditional art processes. NOTE: Structural format (PHASES / FAILURE MODE / KEY INSIGHT) deferred to P3. Current format is principle-style; future revision will add instantiable structure.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### AI-002: Designing Machine Learning Systems — Chip Huyen

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The gist here is that if your A/B test result shows that a model is better than another with statistical significance, you can determine which model is indeed better. To measure statistical significance, A/B testing uses statistical hypothesis testing such as two-sample tests. A two-sample test is used to determine whether the difference between two populations is statistically significant.

**Expected extraction:**

- *Model selection in production ML requires statistical hypothesis testing, not just comparing aggregate metrics. A/B testing with two-sample tests determines whether observed performance differences between models are statistically significant or merely noise. Without statistical rigor, 'model A is better than model B' is an unsupported claim — the difference could be random variation.*

**Rationale:** Practical ML engineering principle about model evaluation rigor. The distinction between 'observed difference' and 'statistically significant difference' is a common failure point in production ML systems.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-013: Synthetic — methodology-hype-without-mechanism test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> Design thinking has revolutionized how organizations approach problem-solving. By centering the user experience and iterating rapidly through prototypes, teams can arrive at solutions that traditional analytical methods would miss. Companies from IDEO to IBM have embraced this methodology, and the results speak for themselves. The design thinking framework — empathize, define, ideate, prototype, test — provides a repeatable path to innovation.

**Rationale:** HARD NEGATIVE. This describes a methodology (design thinking) without explaining its mechanism. It lists steps (empathize, define, ideate, prototype, test) and name-drops companies, but never explains WHY the method works or WHEN it fails. 'Design thinking works because X under Y conditions' is a principle. 'Design thinking has 5 steps and big companies use it' is marketing. The LLM must distinguish methodology descriptions from principled explanations.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## 🎯 Conditional / Boundary — 'X works when Y, fails when Z'

### CND-001: Influence — Robert Cialdini

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> Social proof is most effective when the proof comes from similar others. Showing that '10,000 people bought this' is less persuasive than showing that 'people like you bought this.' The effect is strongest when people are uncertain about what to do — in ambiguous situations, we look to others' behavior as a heuristic for correct action. However, social proof backfires when the referenced group is perceived as dissimilar or when the behavior being referenced is undesirable.

**Expected extraction:**

- *Social proof persuades through similarity, not volume — 'people like you' outperforms '10,000 people' because relevance amplifies the heuristic. It backfires when the reference group is perceived as dissimilar or the behavior is undesirable.*

**Rationale:** Boundary condition (works when similar, fails when dissimilar). Universal across marketing, UX design, and organizational change.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## 📋 Process Instance — Concrete case studies

### PI-001: Predictably Irrational — Dan Ariely

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> The Economist's subscription page became a famous case study in decoy pricing. They offered three options: Web-only for $59, Print-only for $125, and Print+Web for $125. The Print-only option was the decoy — nobody chose it, but its presence made Print+Web look like a bargain (getting both for the same price as print alone). Dan Ariely tested this with his students: when the decoy was present, 84% chose Print+Web. When he removed the decoy and offered only Web ($59) and Print+Web ($125), only 32% chose Print+Web. The decoy shifted preference by making the target option appear as an obvious superior value.

**Expected extraction:**

- *The Economist subscription page used a Print-only decoy at $125 to make Print+Web at $125 look like a bargain. With the decoy: 84% chose Print+Web. Without it: only 32%. The decoy shifted preference by 52 percentage points.*

**Rationale:** Concrete case study with named company, specific numbers, measurable outcome. Verified accurate against public sources. This is evidence that decoy pricing works — not the template itself, but proof it's effective.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### PI-002: Hacking Growth — Sean Ellis

**Should extract:** ✅ YES  |  **Expected count:** 1

**Source text:**

> When Dropbox launched, they faced the challenge of explaining cloud storage to a market that didn't know they needed it. Instead of listing features, Drew Houston created a 3-minute demo video showing the product in action — syncing files across devices, recovering deleted files, sharing folders. The video demonstrated the outcome (never lose a file, access anywhere) before mentioning price or features. The result: beta signups jumped from 5,000 to 75,000 overnight. Dropbox went from a struggling startup to a $10B company, partly because they led with value demonstration rather than feature lists.

**Expected extraction:**

- *Dropbox used value-first demonstration: a 3-minute video showing file sync, recovery, and sharing outcomes before mentioning features. Result: beta signups jumped from 5,000 to 75,000 overnight, leading to eventual $10B valuation.*

**Rationale:** Concrete case study with named company, specific metrics (5K→75K signups), measurable outcome ($10B valuation). Verified from multiple public sources. Evidence for value-first presentation.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## 🌱 Growth Edge — Speculative ideas (routes to QUARANTINE in Stage 5)

### GE-001: Thinking in Bets — Annie Duke

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> The relationship between anchoring and temporal discounting is underexplored. If an initial price anchor biases willingness-to-pay, does it also bias the timeframe over which people expect to realize value? Someone anchored to $999/month might also expect results in 30 days rather than 90. This could mean pricing anchors don't just set price expectations — they set the entire value-delivery tempo. Worth investigating with a conjoint experiment.

**Rationale:** INJECT: FALSE. Removed from Stage 2 golden set (D2073 pending). Growth Edges currently route to QUARANTINE in Stage 5 — training the LLM to extract content that the pipeline immediately discards creates conflicting signals. Reinstated when GE verification path is built. Kept in golden data for future use.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-008: Synthetic — questions-not-claims test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> What if pricing anchors don't just affect willingness-to-pay, but also influence how quickly customers expect to see results? Could a high price point create an expectation of faster value delivery? And if so, would that expectation affect satisfaction and retention independently of the actual product quality?

**Rationale:** HARD NEGATIVE. This passage consists entirely of QUESTIONS, not claims. It has the vocabulary of a principle (anchoring, willingness-to-pay, satisfaction) but asserts nothing. The LLM must NOT convert questions into declarative principles — extracting 'Anchoring affects temporal expectations' from a passage that only asks whether this might be true is fabrication.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## 🛠️ Tool Instruction — Tool-specific commands

### TI-001: Data Visualization with Altair — Various

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> To build a data visualization dashboard, use Altair's layering operator. Start by creating a base chart with alt.Chart(data).mark_bar(), then add a line overlay with alt.Chart(data).mark_line(). Combine them using the + operator: base + line. For interactive features, add selection intervals with alt.selection_interval() and bind them to the charts using .add_selection(). This creates linked views where selecting data in one chart filters the other.

**Rationale:** CONTRADICTION FIXED (D2074 per Claude feedback): The base SYSTEM_PROMPT explicitly lists Altair layering as an anti-pattern ('Altair's + operator layers independent marks — this is a tool feature, not a principle'). TI-001 now matches: tool-specific content bound to Altair should NOT be extracted. NEG-001 (Excel bar chart) applies the same rule — both tools, both correctly excluded. If a separate tool-instruction knowledge store is built later, this can be reinstated with its own output destination.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-001: Excel for Business — Various

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> To create a bar chart in Excel, select your data, click the Insert tab, and choose Bar Chart from the Charts group. You can then customize colors by right-clicking the bars and selecting Format Data Series. For best results, ensure your data is organized with categories in the first column and values in the second.

**Rationale:** Tool-specific instruction. Not reusable across contexts. 'Use the Insert tab in Excel' has no application outside Excel. SKIP.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## ❌ HARD NEGATIVE — Plausible platitude

### NEG-HARD-001: Synthetic — plausible platitude test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> Good leadership is important for any organization. Leaders must inspire their teams, communicate effectively, and make smart decisions. Without strong leadership, companies struggle to achieve their goals. The best leaders are those who understand their people and create a positive work environment where everyone can thrive. Leadership is the foundation of business success in today's competitive marketplace.

**Rationale:** HARD NEGATIVE. This reads like a principle (it has structure, claims causality, uses business vocabulary) but contains zero specific mechanism. 'Good leadership is important' and 'leaders must inspire' are unfalsifiable. Every claim is a tautology. This is exactly the kind of plausible-sounding-but-content-free text that a poorly calibrated LLM extracts as a 'principle.' The model must learn to reject these.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-003: Synthetic — vague generalization test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> Companies that truly understand their customers outperform those that don't. Customer understanding leads to better products, stronger marketing, and higher sales. The most successful companies in history — from Apple to Amazon to Toyota — all share a deep commitment to knowing what their customers want. If you want to grow your business, start by listening to your customers more carefully.

**Rationale:** HARD NEGATIVE. Vague generalization dressed in business language. 'Understand your customers' is not a principle — it's a truism with no mechanism, no boundary condition, no falsifiability. Name-drops Apple/Amazon/Toyota as social proof without specific evidence. 'Listen to customers more carefully' is advice, not a principle. Reject.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-004: Synthetic — vague design platitude test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> Design is everywhere. From the chair you're sitting on to the phone in your pocket, design shapes every aspect of modern life. Good design makes things easier to use, more beautiful to look at, and more meaningful to own. Bad design frustrates, confuses, and alienates. The best designers understand this responsibility and strive to create experiences that delight users at every touchpoint.

**Rationale:** HARD NEGATIVE for design domain. This reads like a design principle but contains zero specific mechanism. 'Good design makes things easier' is unfalsifiable — it defines good design by its outcomes without specifying what makes design good. The LLM must resist extracting this despite its plausible structure and domain-appropriate vocabulary.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-006: Synthetic — AI hype platitude test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> AI is transforming everything. From healthcare to education, from transportation to entertainment, artificial intelligence is reshaping industries at an unprecedented pace. Companies that fail to adopt AI will be left behind. The future belongs to those who embrace artificial intelligence and integrate it into every aspect of their operations. The AI revolution is not coming — it's already here.

**Rationale:** HARD NEGATIVE for AI domain. All hype, no mechanism. 'AI is transforming everything' is unfalsifiable and non-specific. The LLM must resist extracting this — it has the rhythm and confidence of a principle but contains zero actionable or testable content. Domain-appropriate platitudes are the hardest negatives because they use the right vocabulary.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## ❌ HARD NEGATIVE — Over-narrow anecdote

### NEG-HARD-002: Synthetic — over-narrow anecdote test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> I once worked with a client who had a very unique approach to client relationships. He would send handwritten notes to every client on their birthday, and he claimed this practice alone accounted for 80% of his repeat business. While I can't verify that number, I've adopted a similar practice and found that my clients seem to appreciate the personal touch. It probably works because people like feeling remembered.

**Rationale:** HARD NEGATIVE. Over-narrow personal anecdote masquerading as a principle. Single data point, unverified claim ('80% of repeat business'), vague mechanism ('probably works because...'). This is exactly the 'my one client' pattern that produces unreliable extractions. Reject.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-005: Synthetic — over-narrow personal anecdote

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> I once attended a workshop where the facilitator asked us to draw our creative process. Everyone's drawing was completely different — some drew spirals, others drew straight lines, one person drew a tree. It was fascinating to see how differently we all think about creativity. The exercise really opened my eyes to the diversity of creative approaches. Since that workshop, I've tried to be more open-minded about how other people work.

**Rationale:** HARD NEGATIVE. This is a personal anecdote that gestures at a principle ('creative processes differ') but provides only a single-session observation with no generalizable mechanism, no testable claim, and no actionable insight. It's a story, not a principle. The LLM must resist the temptation to extract 'creative processes are diverse' as a principle — that's a truism, not an insight.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-014: Synthetic — consultant-anecdote-test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> The best leaders are those who balance confidence with humility. They have the conviction to make tough calls but the wisdom to listen to others. In my twenty years of consulting, I've seen this pattern repeat across industries — from Silicon Valley startups to Fortune 500 boardrooms. The leaders who succeed are those who know what they don't know.

**Rationale:** HARD NEGATIVE. Consultant wisdom masquerading as a principle. 'Balance confidence with humility' is unfalsifiable — there's no mechanism, no boundary condition, no testable claim. The 'twenty years of consulting' is an appeal to experience without evidence. The final sentence ('know what they don't know') is a tautology. Three red flags in one paragraph.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## ❌ EASY NEGATIVE — Boilerplate

### NEG-002: Various HBR books

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> This book was first published in 2015 by Harvard Business Review Press. Copyright © 2015 Harvard Business School Publishing Corporation. All rights reserved. No part of this publication may be reproduced, stored in a retrieval system, or transmitted in any form without prior written permission. Printed in the United States of America.

**Rationale:** Copyright notice. Zero extractable content. Text cleaner strips this but if any slips through, the LLM must recognize it as non-content.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

## ❌ EASY NEGATIVE — Meta-text

### NEG-003: Various textbooks

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> In Chapter 3, we discussed the fundamentals of pricing strategy. Chapter 4 will build on these concepts by introducing value-based pricing models. As we saw in the previous section, cost-plus pricing has significant limitations, which we will address in detail throughout this chapter. The following pages will explore how companies can transition from cost-based to value-based approaches.

**Rationale:** Navigational/transitional text. References other chapters, previews content, summarizes what was already said. No standalone principle.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-007: Synthetic — attribution-not-assertion test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> Many authors have written about the importance of feedback loops in organizational design. Senge emphasizes systems thinking, while Meadows focuses on leverage points. The consensus among these thinkers is that understanding feedback is critical to managing complex systems effectively.

**Rationale:** HARD NEGATIVE. This passage describes what OTHER authors think — it attributes claims without making any itself. The LLM must recognize that 'Senge says X' is not the same as 'X is true.' Extracting principles from attribution text produces secondhand principles with unclear provenance.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---

### NEG-HARD-010: Synthetic — chapter-summary-meta-text test

**Should extract:** ❌ NO  |  **Expected count:** 0

**Source text:**

> In this chapter, we covered the fundamentals of visual composition. As we saw in Chapter 3, contrast creates hierarchy, and as we'll explore in Chapter 5, color amplifies these effects. Before moving on, let's review the key takeaways: balance provides stability, rhythm creates movement, and proportion establishes relationships between elements.

**Rationale:** HARD NEGATIVE. This is a chapter summary that lists concepts without developing any of them into principles. It name-drops 'contrast,' 'hierarchy,' 'balance,' 'rhythm,' and 'proportion' — all legitimate design concepts — but states them as bullet points, not as extractable mechanisms. The LLM must resist extracting 'Contrast creates hierarchy' — that's a chapter reference, not a developed principle.

**Your review:**

- [ ] Extraction is correct as written
- [ ] Extraction needs revision (note below)
- [ ] This should NOT be extracted (change `should_extract` to false)

**Feedback:** _write here..._

---


---

## Summary Checklist

| # | ID | Type | Domain | Reviewed | Approved | Needs Revision |
|---|-----|------|--------|----------|----------|---------------|
| | PI-001 | process_instance | Predictably Irrational — Dan Ariely | ☐ | ☐ | ☐ |
| | PI-002 | process_instance | Hacking Growth — Sean Ellis | ☐ | ☐ | ☐ |
| | PRO-002 | procedural | Testing Business Ideas — David Bland | ☐ | ☐ | ☐ |
| | CND-001 | conditional | Influence — Robert Cialdini | ☐ | ☐ | ☐ |
| | GE-001 | growth_edge | Thinking in Bets — Annie Duke | ☐ | ☐ | ☐ |
| | TI-001 | tool_instruction | Data Visualization with Altair — Various | ☐ | ☐ | ☐ |
| | LEA-001 | causal | Multipliers — Liz Wiseman | ☐ | ☐ | ☐ |
| | LEA-002 | definitional | Multipliers — Liz Wiseman | ☐ | ☐ | ☐ |
| | STR-001 | definitional | Blue Ocean Strategy — W. Chan Kim & René | ☐ | ☐ | ☐ |
| | STR-002 | procedural | Blue Ocean Strategy — W. Chan Kim & René | ☐ | ☐ | ☐ |
| | MGT-001 | procedural | The Effective Executive — Peter Drucker | ☐ | ☐ | ☐ |
| | MGT-002 | causal | The Effective Executive — Peter Drucker | ☐ | ☐ | ☐ |
| | OPS-001 | definitional | The Goal — Eliyahu Goldratt | ☐ | ☐ | ☐ |
| | OPS-002 | causal | The Goal — Eliyahu Goldratt | ☐ | ☐ | ☐ |
| | PRD-001 | procedural | Continuous Discovery Habits — Teresa Tor | ☐ | ☐ | ☐ |
| | MPL-001 | procedural | The Effective Executive — Peter Drucker | ☐ | ☐ | ☐ |
| | MPL-002 | procedural | Multipliers — Liz Wiseman | ☐ | ☐ | ☐ |
| | NEG-HARD-001 | platitude | Synthetic — plausible platitude test | ☐ | ☐ | ☐ |
| | NEG-HARD-002 | anecdote | Synthetic — over-narrow anecdote test | ☐ | ☐ | ☐ |
| | NEG-HARD-003 | platitude | Synthetic — vague generalization test | ☐ | ☐ | ☐ |
| | NEG-001 | tool_instruction | Excel for Business — Various | ☐ | ☐ | ☐ |
| | NEG-002 | boilerplate | Various HBR books | ☐ | ☐ | ☐ |
| | NEG-003 | meta_text | Various textbooks | ☐ | ☐ | ☐ |
| | DES-001 | causal | A Primer of Visual Literacy — Donis A. D | ☐ | ☐ | ☐ |
| | DES-002 | causal | A Primer of Visual Literacy — Donis A. D | ☐ | ☐ | ☐ |
| | DES-003 | procedural | Principles of Logo Design — George Bokhu | ☐ | ☐ | ☐ |
| | DES-004 | definitional | Principles of Logo Design — George Bokhu | ☐ | ☐ | ☐ |
| | DES-005 | procedural | Principles of Logo Design — George Bokhu | ☐ | ☐ | ☐ |
| | DES-006 | causal | A Primer of Visual Literacy — Donis A. D | ☐ | ☐ | ☐ |
| | ART-001 | definitional | Code as Creative Medium — Golan Levin &  | ☐ | ☐ | ☐ |
| | ART-002 | definitional | Code as Creative Medium — Golan Levin &  | ☐ | ☐ | ☐ |
| | ART-003 | definitional | Generative Art: A Practical Guide — Matt | ☐ | ☐ | ☐ |
| | ART-004 | definitional | Generative Art: A Practical Guide — Matt | ☐ | ☐ | ☐ |
| | ART-005 | causal | Code as Creative Medium — Golan Levin &  | ☐ | ☐ | ☐ |
| | ART-006 | procedural | Code as Creative Medium — Golan Levin &  | ☐ | ☐ | ☐ |
| | PER-001 | definitional | Atomic Habits — James Clear | ☐ | ☐ | ☐ |
| | PER-002 | causal | Atomic Habits — James Clear | ☐ | ☐ | ☐ |
| | PER-003 | definitional | Atomic Habits — James Clear | ☐ | ☐ | ☐ |
| | PER-004 | causal | Atomic Habits — James Clear | ☐ | ☐ | ☐ |
| | PER-005 | definitional | The War of Art — Steven Pressfield | ☐ | ☐ | ☐ |
| | PER-006 | causal | The War of Art — Steven Pressfield | ☐ | ☐ | ☐ |
| | PER-007 | causal | The War of Art — Steven Pressfield | ☐ | ☐ | ☐ |
| | PER-008 | causal | The Gifts of Imperfection — Brené Brown | ☐ | ☐ | ☐ |
| | PER-009 | causal | The Gifts of Imperfection — Brené Brown | ☐ | ☐ | ☐ |
| | DES-007 | definitional | A Primer of Visual Literacy — Donis A. D | ☐ | ☐ | ☐ |
| | DES-008 | definitional | A Primer of Visual Literacy — Donis A. D | ☐ | ☐ | ☐ |
| | DES-009 | comparative | A Primer of Visual Literacy — Donis A. D | ☐ | ☐ | ☐ |
| | DES-010 | causal | Principles of Logo Design — George Bokhu | ☐ | ☐ | ☐ |
| | DES-011 | procedural | Principles of Logo Design — George Bokhu | ☐ | ☐ | ☐ |
| | PER-010 | definitional | The Gifts of Imperfection — Brené Brown | ☐ | ☐ | ☐ |
| | PER-011 | causal | The Gifts of Imperfection — Brené Brown | ☐ | ☐ | ☐ |
| | ART-007 | definitional | Generative Design — Bohnacker, Groß, Lau | ☐ | ☐ | ☐ |
| | ART-008 | causal | Generative Design — Bohnacker, Groß, Lau | ☐ | ☐ | ☐ |
| | ART-009 | causal | Generative Art: A Practical Guide — Matt | ☐ | ☐ | ☐ |
| | SYS-001 | causal | Visual Thinking — Rudolf Arnheim | ☐ | ☐ | ☐ |
| | PT-001 | procedural | Principles of Logo Design — George Bokhu | ☐ | ☐ | ☐ |
| | PT-002 | procedural | Atomic Habits — James Clear | ☐ | ☐ | ☐ |
| | PT-003 | procedural | Generative Art: A Practical Guide — Matt | ☐ | ☐ | ☐ |
| | SYS-002 | causal | Visual Thinking — Rudolf Arnheim | ☐ | ☐ | ☐ |
| | SYS-003 | causal | Visual Thinking — Rudolf Arnheim | ☐ | ☐ | ☐ |
| | AI-001 | definitional | Agentic Design Patterns — Antonio Gullí | ☐ | ☐ | ☐ |
| | AI-002 | procedural | Designing Machine Learning Systems — Chi | ☐ | ☐ | ☐ |
| | SUB-001 | definitional | Semiotics of Typography — Nina Nørgaard | ☐ | ☐ | ☐ |
| | SUB-002 | definitional | Semiotics of Typography — Nina Nørgaard | ☐ | ☐ | ☐ |
| | NEG-HARD-004 | platitude | Synthetic — vague design platitude test | ☐ | ☐ | ☐ |
| | NEG-HARD-005 | anecdote | Synthetic — over-narrow personal anecdot | ☐ | ☐ | ☐ |
| | NEG-HARD-006 | platitude | Synthetic — AI hype platitude test | ☐ | ☐ | ☐ |
| | NEG-HARD-007 | meta_text | Synthetic — attribution-not-assertion te | ☐ | ☐ | ☐ |
| | NEG-HARD-008 | growth_edge | Synthetic — questions-not-claims test | ☐ | ☐ | ☐ |
| | NEG-HARD-009 | definitional | Synthetic — technical-definition-not-pri | ☐ | ☐ | ☐ |
| | NEG-HARD-010 | meta_text | Synthetic — chapter-summary-meta-text te | ☐ | ☐ | ☐ |
| | NEG-HARD-011 | causal | Synthetic — correlation-as-causation tes | ☐ | ☐ | ☐ |
| | NEG-HARD-012 | causal | Synthetic — plausible-principle-with-noi | ☐ | ☐ | ☐ |
| | NEG-HARD-013 | procedural | Synthetic — methodology-hype-without-mec | ☐ | ☐ | ☐ |
| | NEG-HARD-014 | anecdote | Synthetic — consultant-anecdote-test | ☐ | ☐ | ☐ |

**Overall assessment:**

- [ ] All examples are correct — ready to inject into Stage 2 prompts
- [ ] Examples need revision before use (see feedback above)
- [ ] Domain coverage is sufficient — no additional examples needed

> Return this file with your feedback checked and any notes written inline.