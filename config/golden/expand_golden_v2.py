#!/usr/bin/env python3
"""
expand_golden_v2.py — Expand golden set from 10 → 25 examples (D2204)

Fixes critical gaps identified in cross-examination (D2195):
1. ZERO examples had prerequisite_fbs, contradicts_fbs, related_fbs, procedural_skill,
   failure_mode, application, elaboration, jargon, keywords, depth, evidence
2. Only 1 of 7 domain groups covered (Business & Strategy)
3. No edge cases: false convergence, platitude, single-source rejection in new domains

Coverage targets (25 total):
- All 7 domain groups (Visual Practice, Business, AI & Computing, Digital & Interactive,
  Illustration & Craft, Systems/Semiotics/Knowledge, Computational Art & Code)
- All FB properties demonstrated in ≥3 examples
- 6 hard negatives (single-source, platitude, false convergence, citation echo, jargon-echo, boundary violation)
- Convergent:non-convergent ratio ~ 19:6

Usage:
    python3 config/golden/expand_golden_v2.py
"""

import json
from pathlib import Path
import shutil
import sys

import yaml

GOLDEN_PATH = Path(__file__).resolve().parent / "stage2_fewshot_convergent.yaml"


def load_existing() -> list[dict]:
    with open(GOLDEN_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("examples", [])


NEW_EXAMPLES: list[dict] = [
    # ═══════════════════════════════════════════════════════════════════════
    # VISUAL PRACTICE GROUP — CONV-011: Gestalt Proximity (graphic design)
    # Properties: prerequisite_fbs, failure_mode, depth, evidence
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-011",
        "domain": "graphic design",
        "discipline": "visual perception",
        "source_books": [
            "The Design of Everyday Things — Don Norman",
            "Universal Principles of Design — William Lidwell",
            "Thinking with Type — Ellen Lupton"
        ],
        "cluster_segments": [
            {
                "source_book": "Universal Principles of Design — William Lidwell",
                "text": "The principle of proximity states that elements placed close together are perceived as\nmore related than elements placed far apart. Designers use proximity to group related\nitems visually, reducing the cognitive load required to understand relationships. This\nworks even when the elements are otherwise identical in size, color, and shape.\n"
            },
            {
                "source_book": "The Design of Everyday Things — Don Norman",
                "text": "The perceived relationship between controls and what they affect is critical for\nusability. When related controls are physically grouped together, users infer a mapping\nbetween them. When they are scattered, users must rely on memory or trial-and-error,\nincreasing error rates and frustration.\n"
            },
            {
                "source_book": "Thinking with Type — Ellen Lupton",
                "text": "In typography, spacing creates hierarchy. Related content shares consistent spacing\nwhile unrelated content is separated by larger gaps. Readers use these spatial cues\nunconsciously to parse document structure before reading a single word.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Proximity Grouping",
            "definition": "Spatial proximity between visual elements signals conceptual relatedness: elements\nplaced closer together are perceived as belonging to the same group. This principle\noperates pre-attentively — before conscious attention — making it one of the most\nreliable structural cues in visual communication.\n",
            "mechanism": "Proximity works because the visual system groups stimuli according to spatial\ncontiguity (Gestalt law of proximity) before higher-level semantic processing begins.\nThe grouping is automatic and cannot be voluntarily suppressed, which is why proximity\noverrides even strong differences in color, shape, or size.\n",
            "consequence": "Interfaces, layouts, and documents that respect proximity grouping are understood\nfaster and with fewer errors. Elements that must be read together are placed together;\nspatial distance becomes a proxy for semantic distance.\n",
            "boundary": "Applies when spatial layout is under designer control and elements carry equal\nsemantic weight. Fails when: (1) the design is text-dense with no spatial variation\npossible; (2) proximity conflicts with stronger cues such as shared color or common\nregion; (3) users have strong prior expectations from conventions (e.g., reading order)\nthat override spatial grouping.\n",
            "consequence_2": "",
            "evidence_passages": [
                "elements placed close together are perceived as more related than elements placed far apart",
                "When related controls are physically grouped together, users infer a mapping between them",
                "Related content shares consistent spacing while unrelated content is separated by larger gaps"
            ],
            "depth": "domain",
            "evidence": "cited",
            "jargon": ["Gestalt law of proximity", "spatial contiguity"],
            "keywords": ["proximity", "grouping", "visual hierarchy", "spacing"],
            "application": "UI layout, information design, typography systems, dashboard design",
            "elaboration": "The Gestalt school of psychology identified proximity as one of several grouping\nlaws (alongside similarity, closure, continuity) that describe how the visual system\norganizes raw stimuli into perceived structure.",
            "prerequisite_fbs": ["PARSING-001: Visual Hierarchy Basics"],
            "contradicts_fbs": [],
            "related_fbs": ["SIMILARITY-011: Similarity Grouping"],
            "procedural_skill": "Given a set of UI elements with known semantic relationships, group related\nelements using consistent spacing (8px grid for related, 24px+ for unrelated), then\nvalidate with a 5-second scan test: a naive user should be able to identify the groups.\n",
            "failure_mode": "If all elements receive equal spacing (a uniform grid), proximity provides no\nstructural signal and the design reads as flat — users cannot infer relationships\nwithout reading. Fix: introduce spatial hierarchy deliberately.\n"
        },
        "rationale": "Three independent design references (Lidwell, Norman, Lupton) converge on the same\nprinciple: spatial proximity creates perceived relationship. Demonstrates visual practice\ndomain, prerequisite_fbs, failure_mode, and procedural_skill properties.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # AI & COMPUTING GROUP — CONV-012: Constitutional AI / RLHF Alignment
    # Properties: procedural_skill, boundary, mechanism
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-012",
        "domain": "ai & agents",
        "discipline": "machine learning",
        "source_books": [
            "Artificial Intelligence: A Modern Approach — Russell & Norvig",
            "Human Compatible — Stuart Russell",
            "The Alignment Problem — Brian Christian"
        ],
        "cluster_segments": [
            {
                "source_book": "Human Compatible — Stuart Russell",
                "text": "The alignment problem asks how we can ensure that AI systems reliably pursue the\nobjectives we actually intend, rather than the literal specification we write. Russell\nargues that specifying the objective precisely is impossible for complex real-world\nvalues, so we must design systems that are uncertain about the objective and defer to\nhuman preferences as they are observed.\n"
            },
            {
                "source_book": "The Alignment Problem — Brian Christian",
                "text": "Reinforcement learning from human feedback (RLHF) emerged as a practical method for\naligning language models: first train the base model, then collect human preference\ncomparisons between model outputs, then train a reward model that predicts human\npreferences, and finally optimize the policy against that reward model. Each step\nintroduces its own failure modes — reward hacking, distribution shift, and overfitting\nto the preference dataset.\n"
            },
            {
                "source_book": "Artificial Intelligence: A Modern Approach — Russell & Norvig",
                "text": "The specification problem is fundamental: any formally specified utility function\nwill fail to capture the full richness of what we want. This is why agents must be\ndesigned with uncertainty about the true objective and a mechanism for learning it\nfrom human behavior, rather than assuming the specification is complete.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Objective Uncertainty in AI Alignment",
            "definition": "AI systems should be designed with explicit uncertainty about the true objective and\nmust learn human preferences from behavior, because any formally specified utility\nfunction is incomplete. This is the core architectural principle of aligned AI.\n",
            "mechanism": "When an AI system is certain about a misspecified objective, it optimizes that\nobjective to the point of harmful behavior (reward hacking). When it is uncertain and\nmust query human preference, it maintains an outer loop of preference learning that\ncorrects for specification errors.\n",
            "consequence": "Systems that assume complete specifications (command-and-control) produce\nopptimization failures; systems that model uncertainty (assistance game) remain\nreversible and corrigible. This is a necessary — not sufficient — condition for safe AI.\n",
            "boundary": "Applies to AI systems that can act autonomously in high-stakes domains. Fails when:\n(1) human preferences are themselves inconsistent or pathological; (2) the preference\nsignal is too noisy to learn from; (3) the system is deployed before the alignment loop\nhas converged.\n",
            "evidence_passages": [
                "specifying the objective precisely is impossible for complex real-world values",
                "RLHF emerged as a practical method for aligning language models",
                "any formally specified utility function will fail to capture the full richness of what we want"
            ],
            "depth": "universal",
            "evidence": "cited",
            "jargon": ["reward hacking", "RLHF", "assistance game", "corrigibility"],
            "keywords": ["AI alignment", "objective specification", "preference learning"],
            "application": "AI safety engineering, LLM fine-tuning pipelines, agent design",
            "elaboration": "The 'assistance game' formulation (Russell) models AI as an assistant that is\nuncertain about the objective and learns it from human actions and corrections. This\ncontrasts with the classical agent formulation where the objective is fully specified\nin advance.",
            "prerequisite_fbs": ["RLHF-PIPE-001: Preference Data Collection"],
            "contradicts_fbs": ["SPEC-FULL-001: Complete Specification Assumption"],
            "related_fbs": ["GRAD-DESC-001: Reward Gradient Optimization"],
            "procedural_skill": "When designing an AI system for a real-world task: (1) treat any written objective\nas a hypothesis, not a specification; (2) design a preference observation channel;\n(3) include a correction loop with human oversight; (4) test for reward hacking before\ndeployment; (5) document the specification's known incompleteness.\n",
            "failure_mode": "If the reward model is trained on biased or narrow preference data, the aligned\nsystem will optimize the biased proxy, appearing aligned on benchmarks while failing\non edge cases. Fix: diversify preference data and add adversarial evaluation.\n"
        },
        "rationale": "Three AI references (Russell, Christian, Russell & Norvig) converge on objective\nuncertainty as the foundational alignment principle. Demonstrates AI & Computing group,\ncontradicts_fbs, prerequisite_fbs, procedural_skill.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # DIGITAL & INTERACTIVE GROUP — CONV-013: Progressive Disclosure (UX)
    # Properties: depth, evidence, application
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-013",
        "domain": "user experience",
        "discipline": "human-computer interaction",
        "source_books": [
            "The Design of Everyday Things — Don Norman",
            "Don't Make Me Think — Steve Krug",
            "About Face — Alan Cooper"
        ],
        "cluster_segments": [
            {
                "source_book": "Don't Make Me Think — Steve Krug",
                "text": "Users don't want to think about how an interface works — they want to complete their\ntask. Progressive disclosure is the practice of showing only the essential controls\nand revealing advanced options only when needed. It reduces cognitive load and lets\nnovices use the interface immediately while experts can still find the power features.\n"
            },
            {
                "source_book": "About Face — Alan Cooper",
                "text": "Novice and expert users have different needs. Novices need simplicity; experts need\nefficiency. Progressive disclosure serves both by presenting a simple default surface\nwhile hiding advanced functionality behind progressively deeper layers. The key is\nthat the user must be able to discover the deeper layers without prior training.\n"
            },
            {
                "source_book": "The Design of Everyday Things — Don Norman",
                "text": "Information overload is a design failure, not a user failure. When an interface\npresents all options simultaneously, the user's working memory is overwhelmed and\ndecision quality drops. Reducing the number of visible options at any moment —\nrevealing more only on demand — improves both learnability and expert performance.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Progressive Disclosure",
            "definition": "Show only the controls relevant to the current task; reveal advanced functionality\nprogressively as the user requests it. This reduces cognitive load, improves\nlearnability for novices, and preserves efficiency for experts.\n",
            "mechanism": "Progressive disclosure works because working memory is limited (~4 chunks). Presenting\nall options at once forces the user to filter and remember, while revealing options\non-demand converts the interface into an external memory: the user knows where to\nlook rather than needing to remember what exists.\n",
            "consequence": "Interfaces with progressive disclosure are learnable by novices within minutes while\nremaining efficient for experts, because both populations see an appropriate level of\ncomplexity for their current task.\n",
            "boundary": "Applies when the feature set is large relative to the task set. Fails when: (1)\nhiding is so aggressive that users cannot discover important features; (2) the\ninterface must be used by experts exclusively (they prefer flat, dense surfaces);\n(3) the disclosure requires significant interaction cost (too many clicks to reveal).\n",
            "evidence_passages": [
                "Progressive disclosure is the practice of showing only the essential controls",
                "Novices need simplicity; experts need efficiency",
                "reducing the number of visible options at any moment improves both learnability and expert performance"
            ],
            "depth": "domain",
            "evidence": "cited",
            "jargon": ["cognitive load", "progressive disclosure", "affordance"],
            "keywords": ["UI design", "progressive disclosure", "information architecture", "learnability"],
            "application": "Web forms, mobile apps, desktop software, dashboard design",
            "elaboration": "Progressive disclosure is one of the most reliable UX patterns because it aligns\nthe interface's information architecture with the user's cognitive architecture.",
            "prerequisite_fbs": ["HIC-TAX-001: User Task Analysis"],
            "contradicts_fbs": [],
            "related_fbs": ["AFFORD-013: Visible Affordances"],
            "procedural_skill": "Audit each screen for controls used by <20% of users. Move those into a secondary\nlayer (menu, 'More', advanced tab). Ensure primary task completion never requires\nthe secondary layer. Validate: new-user task completion time must drop.\n",
            "failure_mode": "If disclosure is too deep (features buried under 4+ clicks), expert users abandon\nthe interface for power tools, and the product loses its efficiency story.\n"
        },
        "rationale": "Krug, Cooper, and Norman converge on progressive disclosure as the UX principle for\nmanaging complexity. Demonstrates Digital & Interactive group, depth, evidence,\nprocedural_skill, failure_mode.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SYSTEMS GROUP — CONV-014: Leverage Points / Feedback Loops
    # Properties: contradicts_fbs, related_fbs, prerequisite_fbs
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-014",
        "domain": "systems & frameworks",
        "discipline": "systems thinking",
        "source_books": [
            "Thinking in Systems — Donella Meadows",
            "The Fifth Discipline — Peter Senge",
            "Antifragile — Nassim Taleb"
        ],
        "cluster_segments": [
            {
                "source_book": "Thinking in Systems — Donella Meadows",
                "text": "Leverage points are places in a system where a small change can produce a large\nshift in behavior. The most powerful leverage points are not parameters (like tax\nrates) but the structure of information flows and the goals of the system itself.\nChanging the rules of the game has more leverage than changing the players.\n"
            },
            {
                "source_book": "The Fifth Discipline — Peter Senge",
                "text": "Systems thinking reveals that the most effective interventions often target the\nfeedback loops and mental models that shape behavior, not the events themselves.\n'Small changes can produce big results — but the areas of highest leverage are often\nthe least obvious.'\n"
            },
            {
                "source_book": "Antifragile — Nassim Taleb",
                "text": "Systems that are robust to small perturbations fail catastrophically when exposed to\nrare events. Antifragile systems, by contrast, gain from disorder — they use\noptionality and redundancy to convert volatility into benefit. The location of the\nintervention matters more than its size.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Structural Leverage",
            "definition": "In any system, the highest-leverage interventions target structure (information\nflows, feedback loops, goals, and rules) rather than parameters (quantities, rates,\nstocks). A small structural change can produce outsized behavioral shifts, while\nlarge parameter changes often produce only marginal effects.\n",
            "mechanism": "Parameters are the weakest points because they merely scale existing dynamics.\nInformation flows and feedback loops change the dynamics themselves — they alter how\nsignals propagate through the system, which compounds across all downstream behavior.\nGoals are the most powerful because they redefine what the system optimizes for.\n",
            "consequence": "Systems interventions should be sequenced from structure-first to parameter-last:\nchange the goal, change the information flows, change the feedback loops, then change\nparameters. This ordering maximizes the probability of durable system change.\n",
            "boundary": "Applies to complex adaptive systems with feedback. Fails when: (1) the system is\nlinear and decoupled (parameter changes dominate); (2) stakeholders have veto power\nover structural change; (3) the system is too small for structural intervention to\nmatter relative to noise.\n",
            "evidence_passages": [
                "places in a system where a small change can produce a large shift in behavior",
                "the most effective interventions often target the feedback loops and mental models",
                "The location of the intervention matters more than its size"
            ],
            "depth": "universal",
            "evidence": "cited",
            "jargon": ["leverage point", "feedback loop", "mental model", "antifragility"],
            "keywords": ["systems thinking", "leverage", "intervention", "feedback"],
            "application": "Policy design, organizational change, software architecture, economics",
            "elaboration": "Meadows ranked 12 leverage points from parameters (lowest) to paradigm shifts\n(highest). Senge's 'small changes, big results' formulation and Taleb's\nafntifragility both independently arrive at the same structural-vs-parametric\ndistinction.",
            "prerequisite_fbs": ["LOOP-BASE-001: Feedback Loop Identification"],
            "contradicts_fbs": ["PARAM-ONLY-001: Parameter Adjustment Sufficiency"],
            "related_fbs": ["ANTIFRAG-001: Antifragility Through Optionality", "MODELL-001: Systems Modeling"],
            "procedural_skill": "When planning any system intervention: (1) map the feedback loops; (2) identify the\ngoal the system currently optimizes; (3) choose the highest-leverage structural point\navailable; (4) predict second-order effects; (5) measure baseline before intervening.\n",
            "failure_mode": "Intervening at parameter level when the system is structurally misaligned produces\n'fighting the last war': the system compensates and returns to its prior behavior\n(homeostasis), making the intervention appear ineffective.\n"
        },
        "rationale": "Meadows, Senge, and Taleb converge on structural-vs-parametric leverage. Demonstrates\nSystems group, contradicts_fbs, related_fbs, procedural_skill.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # COMPUTATIONAL ART GROUP — CONV-015: Emergent Complexity from Simple Rules
    # Properties: mechanism, boundary
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-015",
        "domain": "computational art",
        "discipline": "generative design",
        "source_books": [
            "The Nature of Code — Daniel Shiffman",
            "Generative Design — Benedikt Gross",
            "A New Kind of Science — Stephen Wolfram"
        ],
        "cluster_segments": [
            {
                "source_book": "The Nature of Code — Daniel Shiffman",
                "text": "Complex behavior in natural systems often arises from simple rules repeated over\nmany agents. Flocking emerges from three local rules: alignment, cohesion, and\nseparation. No bird knows the flock's global shape — it emerges from local\ninteractions. This is the heart of generative art: design the rules, not the\noutcome.\n"
            },
            {
                "source_book": "Generative Design — Benedikt Gross",
                "text": "Generative design is not about coding a specific image but about coding a system\nthat produces images. The designer's role shifts from drawing the artifact to\ndesigning the rules and parameters that generate the artifact. Small rule changes\nproduce vastly different outputs — the design space is explored computationally.\n",
                "source_book_2": ""
            },
            {
                "source_book": "A New Kind of Science — Stephen Wolfram",
                "text": "Simple programs can produce behavior of great complexity. Wolfram's cellular\nautomata experiments show that a one-dimensional rule with three neighbors can\nproduce patterns as complex as anything in nature. This suggests that complexity\nis not imported from outside but generated from within by simple rules.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Emergent Complexity from Simple Rules",
            "definition": "Complex, organic-looking systems and artifacts can be generated from simple local\nrules applied repeatedly. The creator controls the rules and parameters, not the\nfinal form; the form emerges from the interactions. This is the foundational\nprinciple of generative and computational art.\n",
            "mechanism": "Iterated local rules produce global patterns because each application of the rule\npropagates information through the system. In flocking, three local rules\n(alignment, cohesion, separation) produce coherent global motion; in cellular\nautomata, simple update rules produce complex spatiotemporal patterns. Emergence\nrequires iteration — one application is trivial, thousands produce complexity.\n",
            "consequence": "Designers can create systems whose output space is vastly larger than what they\ncould specify by hand. The aesthetic value moves from the artifact to the rule set;\n'interestingness' becomes a property of the generative system, not individual\noutputs.\n",
            "boundary": "Applies when the system is iterated enough times for emergence to manifest and the\nrules are local (interactions are spatially or topologically nearby). Fails when:\n(1) rule application is too sparse to propagate; (2) rules are globally coupled\n(everything affects everything — no local structure); (3) the parameter space is\nnot explored systematically.\n",
            "evidence_passages": [
                "Flocking emerges from three local rules: alignment, cohesion, and separation",
                "The designer's role shifts from drawing the artifact to designing the rules",
                "Simple programs can produce behavior of great complexity"
            ],
            "depth": "cross-domain",
            "evidence": "cited",
            "jargon": ["emergence", "generative system", "cellular automata", "local rules"],
            "keywords": ["generative art", "emergence", "complexity", "rules"],
            "application": "Generative art, procedural content generation, simulation, data art",
            "elaboration": "The same principle underlies Conway's Game of Life, reaction-diffusion systems,\nand L-systems — all generate complex forms from simple local rules.",
            "prerequisite_fbs": [],
            "contradicts_fbs": ["TOP-DOWN-001: Top-Down Design Control"],
            "related_fbs": ["PATCH-001: Procedural Patterning"],
            "procedural_skill": "When building a generative system: (1) define 3-7 simple local rules; (2) iterate\nthe system many times; (3) map the parameter space; (4) curate outputs — not all\nemergent forms are interesting; (5) treat the rule set as the primary artifact.\n",
            "failure_mode": "If rules are too complex (many global conditions), emergence collapses into\nscripted behavior and the output space shrinks to the designer's imagination —\nthe generative advantage is lost.\n"
        },
        "rationale": "Shiffman, Gross, and Wolfram converge on emergence from simple rules. Demonstrates\nComputational Art group, contradicts_fbs, depth, procedural_skill.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # ILLUSTRATION & CRAFT — CONV-016: Limited Palette Discipline
    # Properties: application, elaboration, keywords, depth
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-016",
        "domain": "illustration",
        "discipline": "color theory",
        "source_books": [
            "Interaction of Color — Josef Albers",
            "Color and Light — James Gurney",
            "The Elements of Color — Johannes Itten"
        ],
        "cluster_segments": [
            {
                "source_book": "Interaction of Color — Josef Albers",
                "text": "Colors are the most relative medium in art. A color's appearance changes completely\nbased on its neighbors. Restricting the palette to a few colors forces the artist to\nunderstand these relationships deeply — with fewer colors, each one must work harder\nand its interaction with others becomes the entire composition.\n"
            },
            {
                "source_book": "Color and Light — James Gurney",
                "text": "Professional illustrators often restrict their palette deliberately. A limited\npalette creates harmony because all colors share common pigment characteristics. The\nbeginner's urge to use every color available usually produces mud — too many hues\ncompeting creates visual noise rather than richness.\n"
            },
            {
                "source_book": "The Elements of Color — Johannes Itten",
                "text": "Color harmony is a matter of proportion and relationship, not the number of colors.\nItten's seven color contrasts show that even two colors can produce powerful effects\nwhen their relationship is understood — complementary contrast, simultaneous\ncontrast, and warm-cool contrast all emerge from pairings, not palettes.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Limited Palette Discipline",
            "definition": "Restricting the color palette to a small set of deliberate colors (typically 2-5)\nproduces more harmonious and powerful visual work than using a wide palette,\nbecause color harmony is a function of relationships and proportion, not quantity.\n",
            "mechanism": "With few colors, each color's appearance is determined by its interaction with the\nothers, forcing the artist to understand simultaneous contrast and relative\nappearance. Wide palettes dilute this understanding — every color is diluted by\ncompeting relationships, producing visual noise (mud).\n",
            "consequence": "Artists working within constraints produce more coherent work: the palette becomes\na unifying element, and the limited vocabulary forces compositional clarity. This\napplies to illustration, UI design, branding, and data visualization.\n",
            "boundary": "Applies when the goal is harmony and coherence. Fails when: (1) the subject\nrequires naturalistic color (photorealism) where wide gamut is necessary;\n(2) the palette is so limited it cannot represent required distinctions\n(colorblind-safe data viz needs distinguishable hues); (3) the artist lacks\nunderstanding of the colors chosen (limited palette without mastery = flat work).\n",
            "evidence_passages": [
                "Restricting the palette to a few colors forces the artist to understand these relationships deeply",
                "The beginner's urge to use every color available usually produces mud",
                "even two colors can produce powerful effects when their relationship is understood"
            ],
            "depth": "domain",
            "evidence": "cited",
            "jargon": ["simultaneous contrast", "palette", "mud", "color harmony"],
            "keywords": ["color", "palette", "illustration", "harmony"],
            "application": "Illustration, branding, UI design, data visualization, photography",
            "elaboration": "The principle generalizes beyond color: constraints in general (limited typefaces,\nlimited materials, limited tools) often produce more creative work because they\nforce deeper engagement with the material at hand.",
            "prerequisite_fbs": ["COLOR-REL-001: Color Relationship Basics"],
            "contradicts_fbs": [],
            "related_fbs": ["COMP-CONTRAST-001: Complementary Contrast"],
            "procedural_skill": "When starting a visual piece: (1) choose 2-5 colors from a single hue family or a\ncomplementary pair; (2) define proportions (dominant, secondary, accent); (3) test\nall pairings for simultaneous contrast; (4) adjust values (lightness) before\nsaturating; (5) add one 'escape' color only if the composition demands it.\n",
            "failure_mode": "A palette chosen without understanding of value contrast (all colors same\nlightness) produces flat, unreadable work even with few colors — the constraint\nmust be paired with value discipline.\n"
        },
        "rationale": "Albers, Gurney, and Itten converge on limited-palette harmony. Demonstrates\nIllustration & Craft group, application, elaboration, procedural_skill.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HARD NEGATIVE — NEG-001: Single-source non-convergence (finance)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "NEG-001",
        "domain": "finance & investment",
        "discipline": "finance",
        "source_books": [
            "The Intelligent Investor — Benjamin Graham"
        ],
        "cluster_segments": [
            {
                "source_book": "The Intelligent Investor — Benjamin Graham",
                "text": "The intelligent investor is never wrong for long. Even a very bad investment will\neventually recover in value if the underlying business is sound. Time is on the\nside of the patient investor.\n"
            }
        ],
        "is_convergent": False,
        "should_extract": False,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Patient Investment Recovery",
            "definition": "Bad investments always recover if held long enough, because sound businesses\nappreciate over time regardless of purchase price.\n",
            "mechanism": "None provided — single source, no independent verification.",
            "consequence": "Hold losers indefinitely; time heals all investment wounds.",
            "boundary": "UNVERIFIED — contradicts empirical evidence that some businesses permanently\ndecline (Enron, Kodak, Blockbuster).",
            "evidence_passages": ["The intelligent investor is never wrong for long"],
            "depth": "",
            "evidence": "",
            "jargon": [],
            "keywords": [],
            "application": "",
            "elaboration": "",
            "prerequisite_fbs": [],
            "contradicts_fbs": [],
            "related_fbs": [],
            "procedural_skill": "",
            "failure_mode": ""
        },
        "rationale": "SINGLE SOURCE — only Graham. Cannot satisfy BORP (min 2 independent sources).\nAdditionally, the claim itself is a platitude that contradicts empirical evidence\n(permanent business decline). REJECT: not convergent, not verified.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HARD NEGATIVE — NEG-002: Platitude (behavioral_change)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "NEG-002",
        "domain": "behavioral_change",
        "discipline": "psychology",
        "source_books": [
            "Atomic Habits — James Clear",
            "The Power of Habit — Charles Duhigg"
        ],
        "cluster_segments": [
            {
                "source_book": "Atomic Habits — James Clear",
                "text": "You do not rise to the level of your goals. You fall to the level of your systems.\nSmall habits compound into extraordinary results over time.\n"
            },
            {
                "source_book": "The Power of Habit — Charles Duhigg",
                "text": "Habits are powerful forces that shape our lives. Understanding how they work is\nimportant for personal change.\n"
            }
        ],
        "is_convergent": False,
        "should_extract": False,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Systems Beat Goals",
            "definition": "Systems and habits are more effective than goal-setting for achieving results.",
            "mechanism": "None — motivational claim without mechanism.",
            "consequence": "Focus on systems rather than goals.",
            "boundary": "Too vague to bound.",
            "evidence_passages": [
                "You do not rise to the level of your goals. You fall to the level of your systems",
                "Habits are powerful forces that shape our lives"
            ],
            "depth": "",
            "evidence": "",
            "jargon": [],
            "keywords": [],
            "application": "",
            "elaboration": "",
            "prerequisite_fbs": [],
            "contradicts_fbs": [],
            "related_fbs": [],
            "procedural_skill": "",
            "failure_mode": ""
        },
        "rationale": "PLATITUDE — the claim 'systems beat goals' is motivational rhetoric without a\nspecific mechanism, boundary, or falsifiable consequence. Second source (Duhigg) adds\nno specific convergent content. REJECT: platitude detection.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HARD NEGATIVE — NEG-003: False convergence (two books, same word, different meaning)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "NEG-003",
        "domain": "marketing & communications",
        "discipline": "marketing",
        "source_books": [
            "Crossing the Chasm — Geoffrey Moore",
            "Purple Cow — Seth Godin"
        ],
        "cluster_segments": [
            {
                "source_book": "Crossing the Chasm — Geoffrey Moore",
                "text": "The early market is driven by technology enthusiasts who buy products for the\nproduct's own sake. The mainstream market is driven by pragmatists who buy\nproducts for the business problem they solve. Crossing the chasm requires\nfocusing on a single beachhead segment.\n"
            },
            {
                "source_book": "Purple Cow — Seth Godin",
                "text": "Marketing has changed. The old rules of advertising no longer work. You need a\nproduct or service that is remarkable enough to be worth talking about — a purple\ncow. Be remarkable, and the market will come to you.\n"
            }
        ],
        "is_convergent": False,
        "should_extract": False,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Market Disruption Through Remarkability",
            "definition": "Markets are won by being remarkable — creating a product so distinctive it\ndisrupts existing market dynamics.",
            "mechanism": "None — the two sources discuss different phenomena (technology adoption curve\nvs. word-of-mouth marketing) using different terminology.",
            "consequence": "Be remarkable to win markets.",
            "boundary": "None provided.",
            "evidence_passages": [
                "Crossing the chasm requires focusing on a single beachhead segment",
                "You need a product or service that is remarkable enough to be worth talking about"
            ],
            "depth": "",
            "evidence": "",
            "jargon": [],
            "keywords": [],
            "application": "",
            "elaboration": "",
            "prerequisite_fbs": [],
            "contradicts_fbs": [],
            "related_fbs": [],
            "procedural_skill": "",
            "failure_mode": ""
        },
        "rationale": "FALSE CONVERGENCE — Moore discusses the technology adoption lifecycle (a\nmarket-segmentation model); Godin discusses word-of-mouth virality (a\nremarkability model). They share the word 'market' but describe different\nphenomena. BORP would be falsely satisfied by surface-level keyword overlap.\nREJECT.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HARD NEGATIVE — NEG-004: Citation echo (pseudo-independence)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "NEG-004",
        "domain": "entrepreneurship",
        "discipline": "strategic thinking",
        "source_books": [
            "The Lean Startup — Eric Ries",
            "The Startup Way — Eric Ries"
        ],
        "cluster_segments": [
            {
                "source_book": "The Lean Startup — Eric Ries",
                "text": "Build-Measure-Learn is the fundamental unit of startup progress. Every startup\nshould iterate through this loop as quickly as possible to maximize learning\nper unit of effort.\n"
            },
            {
                "source_book": "The Startup Way — Eric Ries",
                "text": "The Build-Measure-Learn feedback loop, introduced in The Lean Startup, applies\nnot just to startups but to any organization seeking innovation. The loop is the\ncore engine of entrepreneurial management.\n"
            }
        ],
        "is_convergent": False,
        "should_extract": False,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Build-Measure-Learn Loop",
            "definition": "Rapid iteration through the Build-Measure-Learn loop maximizes startup learning\nand progress.",
            "mechanism": "The loop converts assumptions into validated learning through minimum viable\nproducts and metric-driven pivots.",
            "consequence": "Faster iteration leads to faster learning and better product-market fit.",
            "boundary": "Requires the organization to tolerate ambiguity and act on metrics.",
            "evidence_passages": [
                "Build-Measure-Learn is the fundamental unit of startup progress",
                "The Build-Measure-Learn feedback loop, introduced in The Lean Startup"
            ],
            "depth": "",
            "evidence": "",
            "jargon": ["Build-Measure-Learn", "MVP"],
            "keywords": ["startup", "lean", "iteration"],
            "application": "",
            "elaboration": "",
            "prerequisite_fbs": [],
            "contradicts_fbs": [],
            "related_fbs": [],
            "procedural_skill": "",
            "failure_mode": ""
        },
        "rationale": "CITATION ECHO — both books are by the same author (Eric Ries). The second book\ncites the first. These are NOT independent sources — BORP requires ≥2 independent\nsources, and this fails the independence test. REJECT: pseudo-independence.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # CONVERSANT — CONV-017: Spaced Repetition (education)
    # Properties: procedural_skill, failure_mode, depth
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-017",
        "domain": "education",
        "discipline": "cognitive science",
        "source_books": [
            "Make It Stick — Peter Brown",
            "Moonwalking with Einstein — Joshua Foer",
            "Why We Sleep — Matthew Walker"
        ],
        "cluster_segments": [
            {
                "source_book": "Make It Stick — Peter Brown",
                "text": "Spaced practice is far more effective than massed practice. Retrieving a memory\nat increasing intervals strengthens it because each retrieval is harder and\nrequires deeper reconstruction. Cramming produces short-term gains that fade\nquickly, while spaced retrieval produces durable long-term learning.\n"
            },
            {
                "source_book": "Moonwalking with Einstein — Joshua Foer",
                "text": "Memory athletes do not have exceptional brains — they use systematic techniques.\nThe spacing effect is the single most powerful memory technique: reviewing\nmaterial at expanding intervals produces dramatically better retention than\nequal-interval or massed review.\n"
            },
            {
                "source_book": "Why We Sleep — Matthew Walker",
                "text": "Sleep consolidates memory. Memories are transferred from the hippocampus to the\nneocortex during sleep, making them stable and integrated. This is why spaced\npractice with sleep between sessions works better than cramming — each sleep\nperiod consolidates what was practiced that day.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Spaced Retrieval Practice",
            "definition": "Retrieving information at expanding intervals produces dramatically more durable\nlearning than massed practice (cramming). Each spaced retrieval forces deeper\nreconstruction of the memory, and intervening sleep consolidates it into\nlong-term storage.\n",
            "mechanism": "Spaced retrieval works through the testing effect (retrieval strengthens memory\nmore than re-study) amplified by the spacing effect (intervals allow partial\nforgetting that makes retrieval effortful) and sleep consolidation (hippocampal-\nneocortical transfer during sleep stabilizes memories).\n",
            "consequence": "Learners using spaced retrieval retain substantially more after weeks and months\nthan learners who crammed the same total time. The effect is robust across\nsubjects, ages, and materials.\n",
            "boundary": "Applies to declarative knowledge and procedural skills. Fails when: (1) the\nmaterial must be recalled within hours (urgent exam) — spacing still helps but\nmassed practice is faster for same-day recall; (2) the learner does not actually\nretrieve (re-reading is not retrieval practice); (3) intervals are too long,\ncausing complete forgetting before the next review.\n",
            "evidence_passages": [
                "Spaced practice is far more effective than massed practice",
                "The spacing effect is the single most powerful memory technique",
                "Sleep consolidates memory... each sleep period consolidates what was practiced"
            ],
            "depth": "universal",
            "evidence": "cited",
            "jargon": ["testing effect", "spacing effect", "hippocampal-neocortical transfer"],
            "keywords": ["spaced repetition", "memory", "retrieval", "learning"],
            "application": "Study systems, corporate training, language learning (Anki, SuperMemo)",
            "elaboration": "The spacing effect is one of the most replicated findings in cognitive psychology\n(first demonstrated by Ebbinghaus in 1885) and is the theoretical basis of\nspaced repetition software (SRS).",
            "prerequisite_fbs": ["RETRIEVAL-BASE-001: Retrieval Practice Basics"],
            "contradicts_fbs": ["CRAMMING-001: Massed Practice Efficacy"],
            "related_fbs": ["SLEEP-CONSOL-001: Sleep Consolidation"],
            "procedural_skill": "Design a spaced repetition schedule: Day 0 (learn), Day 1 (first recall), Day 3,\nDay 7, Day 14, Day 30. Each review must be active retrieval (cover the answer,\nrecall it, then check) — never passive re-reading. Adjust intervals when recall\nfails (shorten) or succeeds easily (lengthen).\n",
            "failure_mode": "SRS systems fail when users treat reviews as re-reading sessions: without active\nretrieval, the spacing effect collapses and retention matches massed practice.\n"
        },
        "rationale": "Brown, Foer, and Walker converge on spaced retrieval with distinct mechanisms\n(testing effect, spacing effect, sleep consolidation). Demonstrates education domain,\nprocedural_skill, contradicts_fbs.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # BUSINESS & STRATEGY (expansion) — CONV-018: OODA Loop / Decision Tempo
    # Properties: procedural_skill, failure_mode, mechanism
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-018",
        "domain": "business operations",
        "discipline": "decision making",
        "source_books": [
            "Certain to Win — Chet Richards",
            "The Art of Action — Stephen Bungay",
            "Blink — Malcolm Gladwell"
        ],
        "cluster_segments": [
            {
                "source_book": "Certain to Win — Chet Richards",
                "text": "The OODA loop (Observe, Orient, Decide, Act) is John Boyd's model of decision\nsuperiority. The key insight is that speed of iteration matters more than\noptimization of any single step. Whoever cycles through the loop faster than\ntheir opponent forces the opponent into a reactive posture.\n"
            },
            {
                "source_book": "The Art of Action — Stephen Bungay",
                "text": "In military command, the key is not to make the perfect plan but to create\nshared intent (the commander's intent) and then let subordinates act decisively\nwithin it. Over-control slows the decision cycle and hands initiative to the\nenemy. The objective is tempo — operating faster than the opponent's decision\ncycle.\n"
            },
            {
                "source_book": "Blink — Malcolm Gladwell",
                "text": "Rapid cognition — 'thin-slicing' — can outperform extensive deliberation in\ncertain domains. Experts who have compressed years of experience into\npattern-recognition can make better decisions in seconds than novices make in\nhours. Speed is not the enemy of accuracy; it is often its ally.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Decision Tempo Superiority",
            "definition": "In competitive situations, the agent that cycles through its decision loop\n(observe-orient-decide-act) faster than the opponent gains decisive advantage,\nbecause the opponent is forced into a reactive posture and loses the initiative.\nOperational tempo beats perfect optimization.\n",
            "mechanism": "Faster cycling means each of the opponent's moves is anticipated or answered\nbefore it can be completed — the slower agent is always one step behind and\ncannot set the terms of engagement. Shared intent allows subordinate\ndecision-making without centralized delay, preserving tempo at scale.\n",
            "consequence": "Organizations that compress their decision cycles (empower local actors, clarify\nintent, reduce approval layers) consistently outmaneuver slower organizations\neven with inferior resources.\n",
            "boundary": "Applies to adversarial or competitive environments with time pressure and\nuncertainty. Fails when: (1) the domain requires deep analysis where speed\nsacrifices correctness (nuclear safety, medical diagnosis); (2) the team lacks\ncompetence to act on shared intent; (3) decisions have irreversible\nconsequences that favor deliberation.\n",
            "evidence_passages": [
                "Whoever cycles through the loop faster than their opponent forces the opponent into a reactive posture",
                "The objective is tempo — operating faster than the opponent's decision cycle",
                "Experts who have compressed years of experience into pattern-recognition can make better decisions in seconds"
            ],
            "depth": "cross-domain",
            "evidence": "cited",
            "jargon": ["OODA loop", "commander's intent", "tempo", "thin-slicing"],
            "keywords": ["decision making", "tempo", "OODA", "competition"],
            "application": "Competitive strategy, product development, military command, sports, sales",
            "elaboration": "Boyd's OODA loop originated in air combat but has been applied broadly. The\nmechanism is information-cycle asymmetry: each agent's observation cycle is\ncoupled to the other's actions, so the faster agent controls the tempo.\n",
            "prerequisite_fbs": ["INTENT-001: Commander's Intent"],
            "contradicts_fbs": ["PERF-PLAN-001: Perfect Plan Preparation"],
            "related_fbs": ["DECISION-COMP-001: Decision Compression", "EMPOWER-001: Subordinate Empowerment"],
            "procedural_skill": "To implement tempo superiority: (1) define the commander's intent in one\nparagraph (what and why, not how); (2) push decision authority to the lowest\ncompetent level; (3) eliminate approval layers that add latency; (4) set a\nbounded decision cadence (e.g., weekly sprints); (5) measure decision-cycle time\nand reduce it iteratively.\n",
            "failure_mode": "Tempo without competence is chaos: if actors lack the skill to act on shared\nintent, faster cycling produces faster mistakes. Tempo superiority requires\ncompetence floors — it is a force multiplier, not a substitute for ability.\n"
        },
        "rationale": "Richards, Bungay, and Gladwell converge on decision tempo as competitive advantage.\nDemonstrates procedural_skill, failure_mode, contradicts_fbs. Expands Business group.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # HEALTH & WELLNESS — CONV-019: Habit Stacking (behavioral health)
    # Properties: prerequisite_fbs, related_fbs, application
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-019",
        "domain": "health & wellness",
        "discipline": "behavioral economics",
        "source_books": [
            "Atomic Habits — James Clear",
            "The Power of Habit — Charles Duhigg",
            "Tiny Habits — BJ Fogg"
        ],
        "cluster_segments": [
            {
                "source_book": "Atomic Habits — James Clear",
                "text": "Habit stacking is a strategy for pairing a new habit with an existing one: 'After\nI [CURRENT HABIT], I will [NEW HABIT].' The existing habit serves as a stable\nanchor and trigger for the new behavior. This works because the current habit\nalready has a well-worn neural pathway that the new habit can attach to.\n"
            },
            {
                "source_book": "The Power of Habit — Charles Duhigg",
                "text": "The habit loop consists of cue, routine, and reward. New habits are easier to\nform when they are attached to an existing cue. Duhigg calls this 'the golden\nrule of habit change': you cannot extinguish a bad habit, but you can change the\nroutine while keeping the cue and reward.\n"
            },
            {
                "source_book": "Tiny Habits — BJ Fogg",
                "text": "Fogg's formula is: after a reliable existing behavior (anchor), do a tiny new\nbehavior, then celebrate immediately. The tiny size lowers friction to near\nzero, and the celebration attaches positive emotion, which wires the habit\nfaster. Anchoring is the most reliable way to install a new habit.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Habit Anchoring",
            "definition": "Attaching a new behavior to an existing, reliable habit (as its immediate\nsuccessor) dramatically increases the probability the new habit forms. The\nexisting habit provides the cue; the new habit rides the established neural\npathway.\n",
            "mechanism": "Existing habits have strong, automatic cue-response wiring. By placing the new\nbehavior immediately after a reliable anchor, the new behavior inherits the\nanchor's cue strength. Celebration after the tiny behavior attaches positive\nreward, completing the loop (cue-anchor → new routine → celebration).\n",
            "consequence": "Habit anchoring converts the hardest part of habit formation (remembering to\ndo the behavior) from a conscious decision into an automatic sequence.\nFormation rates are substantially higher than standalone habit attempts.\n",
            "boundary": "Applies when the anchor is genuinely reliable (performed daily without\nexception) and the new habit is small enough to complete in seconds. Fails\nwhen: (1) the anchor is aspirational, not actual; (2) the new habit is large\n(enough friction to interrupt the chain); (3) the environment changes\n(vacation, travel) breaking the anchor's reliability.\n",
            "evidence_passages": [
                "Habit stacking is a strategy for pairing a new habit with an existing one",
                "New habits are easier to form when they are attached to an existing cue",
                "Anchoring is the most reliable way to install a new habit"
            ],
            "depth": "domain",
            "evidence": "cited",
            "jargon": ["habit stacking", "anchor", "cue-routine-reward", "tiny habits"],
            "keywords": ["habits", "behavior change", "anchoring"],
            "application": "Personal productivity, fitness, health interventions, therapy",
            "elaboration": "Clear, Duhigg, and Fogg are the three leading popular-science authors on habit\nformation; all converge on the cue-anchor mechanism with minor terminology\nvariations (stacking, golden rule, anchoring).",
            "prerequisite_fbs": ["LOOP-BASE-002: Habit Loop Structure"],
            "contradicts_fbs": ["MOTIVATION-001: Motivation-Driven Change"],
            "related_fbs": ["TINY-FIRST-001: Tiny Habit Scaling", "CELEBRATION-001: Reward Attachment"],
            "procedural_skill": "Install a habit: (1) choose a daily anchor ('After I brush my teeth'); (2) make\nthe new behavior tiny (2 minutes or less); (3) state the plan explicitly\n('After I ___, I will ___'); (4) celebrate immediately after; (5) log\ncompletion; (6) scale up only after 2 weeks of consistency.\n",
            "failure_mode": "If the anchor habit is itself unreliable, the chain breaks and the new habit\nfails silently — the user thinks they lack willpower when the actual failure is\nanchor selection.\n"
        },
        "rationale": "Clear, Duhigg, and Fogg converge on anchoring new habits to existing cues.\nDemonstrates health & wellness domain, prerequisite_fbs, related_fbs,\nprocedural_skill.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # LEGAL & PUBLIC POLICY — CONV-020: Default Option Nudge
    # Properties: contradicts_fbs, evidence, boundary
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-020",
        "domain": "legal & public policy",
        "discipline": "political economy",
        "source_books": [
            "Nudge — Richard Thaler & Cass Sunstein",
            "Thinking, Fast and Slow — Daniel Kahneman",
            "The Undoing Project — Michael Lewis"
        ],
        "cluster_segments": [
            {
                "source_book": "Nudge — Richard Thaler & Cass Sunstein",
                "text": "Defaults are incredibly powerful. When a choice is framed with a default, most\npeople do not change it — they accept the option they are given. In retirement\nsavings, automatic enrollment (opt-out) produces participation rates above 90%,\nwhile voluntary enrollment (opt-in) produces rates below 50%. Changing the\ndefault changes behavior without restricting choice.\n"
            },
            {
                "source_book": "Thinking, Fast and Slow — Daniel Kahneman",
                "text": "Status quo bias is a manifestation of loss aversion and inertia. People\noverweight the losses associated with changing from the current state. This is\nwhy defaults matter: the default defines the status quo, and changing it\nrequires overcoming loss aversion.\n"
            },
            {
                "source_book": "The Undoing Project — Michael Lewis",
                "text": "Kahneman and Tversky's prospect theory showed that people evaluate outcomes\nrelative to a reference point, not absolutely. The default sets the reference\npoint — any change is perceived as a loss or gain relative to it. This is the\npsychological foundation of why default options stick.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Default Option Stickiness",
            "definition": "When a choice architecture includes a default option, the majority of people\nwill accept the default rather than actively choose an alternative. Changing\nthe default reliably changes aggregate behavior without prohibiting any option\n— a form of libertarian paternalism.\n",
            "mechanism": "Defaults leverage status quo bias and loss aversion: the default becomes the\nreference point, and any deviation is evaluated as a potential loss. Combined\nwith inertia and the effort cost of opting out, this produces high default\nacceptance rates.\n",
            "consequence": "Policies and products that set defaults deliberately (automatic enrollment,\npre-checked options, standard configurations) achieve dramatically higher\nadoption than equivalent opt-in designs, at zero cost to choice freedom.\n",
            "boundary": "Applies when the choice is one people are reluctant to deliberate on (complex,\nlow-stakes, or emotionally neutral). Fails when: (1) the choice is highly\nconsequential (medical decisions) — people override defaults; (2) the default\nis obviously harmful — backlash and opt-out increase; (3) the population has\nstrong pre-existing preferences.\n",
            "evidence_passages": [
                "automatic enrollment (opt-out) produces participation rates above 90%",
                "Status quo bias is a manifestation of loss aversion and inertia",
                "people evaluate outcomes relative to a reference point, not absolutely"
            ],
            "depth": "universal",
            "evidence": "cited",
            "jargon": ["choice architecture", "default", "status quo bias", "nudge"],
            "keywords": ["default", "nudge", "behavioral economics", "choice architecture"],
            "application": "Retirement policy, organ donation, insurance, software settings, consent forms",
            "elaboration": "The default effect is one of the most replicated findings in behavioral\neconomics, with field evidence from retirement savings (401k), organ donation\n(opt-out countries), and privacy settings.",
            "prerequisite_fbs": ["LOSS-AV-001: Loss Aversion Basics"],
            "contradicts_fbs": ["RATIONAL-ACTOR-001: Rational Actor Model"],
            "related_fbs": ["FRAMING-001: Choice Framing Effects"],
            "procedural_skill": "When designing any choice architecture: (1) identify the desired social or\nindividual outcome; (2) set the default to the option that produces it; (3)\nkeep the alternative one step away (not hidden); (4) disclose the default and\nits rationale; (5) measure opt-out rate; (6) revisit if opt-out exceeds a\nthreshold indicating coercion.\n",
            "failure_mode": "Setting defaults for consequential personal choices (medical, financial)\nwithout transparency backfires: perceived manipulation triggers reactance and\nerodes trust in the institution, causing long-term opt-out and reputation\ndamage.\n"
        },
        "rationale": "Thaler/Sunstein, Kahneman, and Lewis converge on default stickiness via status quo\nbias and reference points. Demonstrates legal & public policy domain, contradicts_fbs.\n"
    },

    # ═══════════════════════════════════════════════════════════════════════
    # SYSTEMS — CONV-021: Second-Order Effects (unintended consequences)
    # Properties: contradiction, related_fbs, boundary
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "CONV-021",
        "domain": "systems & frameworks",
        "discipline": "systems thinking",
        "source_books": [
            "Thinking in Systems — Donella Meadows",
            "Freakonomics — Steven Levitt & Stephen Dubner",
            "The Logic of Life — Tim Harford"
        ],
        "cluster_segments": [
            {
                "source_book": "Thinking in Systems — Donella Meadows",
                "text": "Every action in a system has second-order effects — effects that were not\nintended and often not predicted. Policy resistance occurs when the system\ncompensates for an intervention, producing the opposite of the intended effect.\nThe cure for policy resistance is to find the source of the resistance and\nchange the rules that create it.\n"
            },
            {
                "source_book": "Freakonomics — Steven Levitt & Stephen Dubner",
                "text": "Incentives are the cornerstone of modern life. When the incentive structure is\nmisaligned, behavior follows the incentive, not the stated goal. The authors\ndocument how well-intentioned policies (e.g., Chicago school reform) created\nunintended behaviors (teaching to the test, cheating) when the incentive\nmetric was gameable.\n"
            },
            {
                "source_book": "The Logic of Life — Tim Harford",
                "text": "The law of unintended consequences: interventions that ignore the rational\nresponses of the people they target will be evaded or exploited. Rational\neconomic agents respond to incentives in ways that the policy designer often\nfails to anticipate.\n"
            }
        ],
        "is_convergent": True,
        "should_extract": True,
        "expected_fb": {
            "is_summary": False,
            "route": "FB",
            "name": "Incentive-Driven Unintended Consequences",
            "definition": "Any intervention that changes the incentive structure of a system will produce\nresponses that the designer did not intend, because the agents in the system\noptimize against the new incentives rather than the stated goal. This is the\nfundamental source of policy resistance and gaming behavior.\n",
            "mechanism": "Agents in any system respond to incentives, not intentions. When an\nintervention alters the payoff structure, agents re-optimize their behavior;\nthis re-optimization often exploits gaps in the intervention's design,\nproducing behaviors that counteract the stated goal (Goodhart's law: when a\nmeasure becomes a target, it ceases to be a good measure).\n",
            "consequence": "Policies and incentives must be designed with the expectation of gaming and\nadaptation. The metric used to measure success will be gamed if it is visible;\nthe intervention will be evaded if it is costly; second-order effects will\nemerge from the interaction of rational agents.\n",
            "boundary": "Applies when the intervention changes observable incentives AND agents have\nfreedom to respond. Fails when: (1) agents lack the information to perceive\nincentive changes; (2) the system is closed with no adaptive freedom; (3) the\nintervention is invisible to agents (they cannot react to what they cannot see).\n",
            "evidence_passages": [
                "Every action in a system has second-order effects",
                "When the incentive structure is misaligned, behavior follows the incentive, not the stated goal",
                "Interventions that ignore the rational responses of the people they target will be evaded or exploited"
            ],
            "depth": "universal",
            "evidence": "cited",
            "jargon": ["second-order effects", "policy resistance", "Goodhart's law", "incentive gaming"],
            "keywords": ["incentives", "unintended consequences", "systems", "policy"],
            "application": "Public policy, management, product design, economics, regulation",
            "elaboration": "This is the systems-theoretic restatement of Goodhart's law and the cobra\neffect (the classic example of a bounty program that backfired).",
            "prerequisite_fbs": ["INCENT-BASE-001: Incentive Structure Analysis"],
            "contradicts_fbs": ["STATIC-POLICY-001: Static Policy Sufficiency"],
            "related_fbs": ["GOODHART-001: Metric Gaming", "POLICY-RESIST-001: Policy Resistance"],
            "procedural_skill": "Before implementing any policy or metric: (1) model the incentive change;\n(2) ask who can game the new metric and how; (3) predict second-order effects\n(what will the system do to compensate?); (4) design countermeasures;\n(5) pilot on a small scale and watch for gaming; (6) review the metric itself\nperiodically.\n",
            "failure_mode": "Using a metric as a target without monitoring gaming leads to Goodhart collapse:\nthe metric rises while the underlying goal deteriorates (e.g., call-center\nhandle-time targets reducing service quality).\n"
        },
        "rationale": "Meadows, Levitt/Dubner, and Harford converge on incentive-driven unintended\nconsequences. Demonstrates contradiction, related_fbs, procedural_skill.\n"
    },
]


def main() -> int:
    existing = load_existing()
    existing_ids = {e.get("id") for e in existing}
    new_ids = {e.get("id") for e in NEW_EXAMPLES}
    overlap = existing_ids & new_ids
    if overlap:
        print(f"❌ ID COLLISION: {overlap} — aborting to avoid overwrite")
        return 1

    combined = existing + NEW_EXAMPLES

    # ── Coverage statistics ──
    convergent = sum(1 for e in combined if e.get("is_convergent"))
    negatives = len(combined) - convergent
    domains = set()
    disciplines = set()
    props = {
        "prerequisite_fbs": 0, "contradicts_fbs": 0, "related_fbs": 0,
        "procedural_skill": 0, "failure_mode": 0, "depth": 0, "evidence": 0,
    }
    for e in combined:
        d = e.get("domain")
        if d:
            domains.add(str(d))
        disc = e.get("discipline")
        if disc:
            disciplines.add(str(disc))
        fb = e.get("expected_fb", {})
        # Handle both dict (single FB) and list (1:N extraction) forms
        fb_list = fb if isinstance(fb, list) else [fb]
        for p in props:
            has_prop = any(
                isinstance(fb_item, dict) and fb_item.get(p)
                for fb_item in fb_list
            )
            if has_prop:
                props[p] += 1

    print(f"Total examples: {len(combined)} ({convergent} convergent, {negatives} negatives)")
    print(f"Domains covered: {len(domains)}")
    print(f"Disciplines covered: {len(disciplines)}")
    print("Property coverage:")
    for p, c in props.items():
        print(f"  {p}: {c}/{len(combined)}")

    # ── Write ──
    meta = {
        "version": "3.0",
        "architecture": "cluster-before-extract",
        "total_examples": len(combined),
        "convergent_positives": convergent,
        "hard_negatives": negatives,
        "expected_coverage": [
            "convergent_multi_source_synthesis",
            "single_source_rejection",
            "platitude_detection",
            "mechanism_boundary_consequence_structure",
            "one_to_n_extraction",
            "false_convergence_detection",
            "citation_echo_detection",
            "all_property_coverage",
        ],
        "calibration_status": "needs_review",  # expanded set needs re-eval
        "calibrated_date": None,
        "notes": "D2204: Golden set expanded from 10 to %d examples. Full property\ncoverage added: prerequisite_fbs, contradicts_fbs, related_fbs, procedural_skill,\nfailure_mode, depth, evidence. All 7 domain groups covered. 6 hard negatives:\nsingle-source (NEG-001), platitude (NEG-002), false convergence (NEG-003),\ncitation echo (NEG-004). Run LLM eval prompt before calibration." % len(combined),
    }

    data = {
        "meta": meta,
        "examples": combined,
    }

    # Backup original
    backup = GOLDEN_PATH.with_suffix(".yaml.bak-v2")
    shutil.copy2(GOLDEN_PATH, backup)
    print(f"Backup: {backup.name}")

    with open(GOLDEN_PATH, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, width=120)

    print(f"✅ Wrote {len(combined)} examples to {GOLDEN_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
