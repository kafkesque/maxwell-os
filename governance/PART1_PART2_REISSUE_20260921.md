# MENU REPAIR - PART 1 / PART 2 RE-ISSUE - 2026-09-21

Supersedes the PART 1 / PART 2 of `MENU_REPAIR_WORKSHEET_20260921.md` only as a CORRECTED
READING. The owner's rulings in that worksheet stand; this file fixes what was shown to them
(BUG-348). Regenerating the ruled worksheet is forbidden (R-D410: a published artifact is evidence).

## Pins this artifact was generated against (D-318)

| input | sha256 |
|---|---|
| governance/ANCHOR2_BLIND_SHEET_20260920.csv | `a91f9c859a998d4d27d7ce91939c4ccf4c23e3e9d20aa0cb34ccadcb294ee821` |
| governance/ANCHOR2_KEY_20260920.json | `20a4a437eab902fc703a210bad26b8d3220c7c2574852fb9b97b01baf567526c` |
| config/taxonomy_v5.yaml | `8d3c90e949ab1988e097c9fc58c80b6f4279477c9651436dddf4d8ffa91d3ae0` |
| config/closed_menu_v5.json (bytes) | `bc53770103595f2a3674ced132e04297e87b590f6d7fb141c7eac6351c680544` |
| config/closed_menu_v5.json (menu_hash) | `73597ee2b1bb1eb92edb08e743ffa0654c1e5994edcd3535d814c7942a89df6f` |
| config/normalization_map.yaml | `303dc2b809413bbcf1e6003dded8c9e6d97f666d5597470d1bacf173adbe65a1` |

## PART 1 (RE-ISSUED) - the four failure classes

| class | n | meaning |
|---|---|---|
| ARTIFACT | 2 | sheet hygiene only (a stray quote); slot exists AND was emitted - NOT a menu item |
| ALIAS_RESOLVED | 5 | a surface variant of a slot the pipeline DID emit - spelling, not ontology |
| UNEMITTED_EXISTING | 11 | slot EXISTS in the menu, pipeline NEVER emitted it - EMISSION class (the real defect) |
| NOVEL | 0 | no slot, no near-match - genuine ontology gap (Absence class) |
| NEAR_MISS | 0 | unresolved but >=0.90 similar to a slot - needs an explicit alias ruling |

### 1a. UNEMITTED_EXISTING - slots the menu offers and the pipeline never selects

| # | slot | human uses | rows |
|---|---|---|---|
| 1 | systems & frameworks | 4 | 6, 8, 22, 31 |
| 2 | web & ui | 2 | 6, 46 |
| 3 | illustration | 1 | 6 |
| 4 | code & computation | 1 | 21 |
| 5 | environmental design | 1 | 33 |
| 6 | motion design | 1 | 41 |
| 7 | design systems | 1 | 46 |

### 1b. ARTIFACT - sheet hygiene, no action

| raw cell token | row | resolves to | nearest |
|---|---|---|---|
| ` marketing & communications"` | 12 | marketing & communications | - |
| ` "leadership"` | 12 | leadership | - |

### 1c. ALIAS_RESOLVED - already covered by an alias

| raw cell token | row | resolves to | nearest |
|---|---|---|---|
| `social science` | 14 | social sciences | - |
| `social science` | 18 | social sciences | - |
| `media & entertainmen` | 21 | media & entertainment | - |
| ` product desig` | 22 | product design | - |
| `business operation` | 40 | business operations | - |

### 1d. NEAR_MISS - needs an alias ruling

_none_

### 1e. NOVEL - genuine ontology gap

_none_

## PART 2 (RE-ISSUED) - all 26 disagreeing discipline pairs, with excerpts

Column 4 is the excerpt the first issue left EMPTY: the generator read `row`/`name` but never the
`definition` column that carries the text the label was derived from. Read it before ruling.

| # | your label | stored label | n | rows | excerpt (first 200 chars of the definition) |
|---|---|---|---|---|---|
| 1 | cognitive science | psychology | 3 | 1, 7, 59 | Human reasoning and decision-making are context-dependent, with different mental modules or processing pathways activated based on situational framing rather than abstract logical principles. The same... |
| 2 | political economy | economics | 2 | 2, 31 | The dominant economic model that prioritizes planned obsolescence over durability, maintaining consumer economy through continuous replacement cycles and resisting shifts toward sustainable manufactur... |
| 3 | finance | strategic thinking | 2 | 4, 26 | A business management practice where daily cash flow accounts (parta) are maintained to provide real-time visibility into organizational financial health. |
| 4 | design thinking | human-computer interaction | 2 | 30, 53 | Design methods that address the specific challenges of conducting research and design with underserved communities by considering context, identity, and dissent voices. |
| 5 | research methodology | risk management | 1 | 9 | The quality of output in any domain is inherently context-dependent and must be evaluated using domain-specific metrics rather than universal standards. Assessing quality requires understanding the in... |
| 6 | operations research | strategic thinking | 1 | 10 | Effective pricing and compensation models are determined by analyzing the specific resources, capabilities, and value propositions that define a professional's or organization's unique market position... |
| 7 | operations research | behavioral economics | 1 | 11 | Effective demand-side sales begins with deep understanding of the actual customer journey and motivations, not assumptions about a generic or average customer. The approach requires analyzing existing... |
| 8 | visual semiotics | communication theory | 1 | 13 | Sales presentations often use analogies and metaphors to explain complex technical concepts by comparing them to familiar, everyday experiences. This principle describes a specific rhetorical techniqu... |
| 9 | artificial intelligence | economics | 1 | 16 | Economic mechanisms and incentive structures are designed to align the behavior of autonomous AI agents with system-wide goals while enabling decentralized participation and resource allocation. These... |
| 10 | research methodology | behavioral economics | 1 | 18 | A qualitative research method that moves beyond surface-level product characteristics to uncover deeper personal motivations and concerns that drive consumer purchasing decisions. |
| 11 | systems thinking | software engineering | 1 | 22 | Digital systems process information through structured decomposition rather than holistic composition, losing contextual meaning in the process. |
| 12 | visual semiotics | psychology | 1 | 27 | Meaning and interpretation of visual or symbolic elements depend on cultural, contextual, and experiential cues rather than universal or inherent properties. The same element can carry different meani... |
| 13 | psychology | behavioral economics | 1 | 28 | A behavioral strategy that uses specific conditional statements (if X, then Y) to strengthen good intentions and protect against lapses in self-control or inaction when moral action is required. |
| 14 | creative process | cultural design | 1 | 29 | A design strategy where designers exploit fortuitous connections or unusual circumstances to carry meaning, rather than using standard or straightforward elements. |
| 15 | behavioral economics | emerging | 1 | 35 | A pattern where consumers are influenced by television advertising to make purchasing decisions based on perceived product quality, leading to increased demand for advertised products and reduced supp... |
| 16 | strategic thinking | psychology | 1 | 37 | Presenting a drawback or limitation early in a communication increases perceived credibility and reduces resistance by providing balanced information. This principle describes a strategic disclosure t... |
| 17 | cognitive science | neuroscience | 1 | 38 | Abstract conceptualization and reasoning emerge from neural representations that integrate sensory-motor experiences rather than from purely abstract mental processes. The principle describes how conc... |
| 18 | operations research | creative process | 1 | 40 | Successful implementation of design thinking requires starting small and embedding it within existing organizational processes rather than pursuing large-scale transformation. The approach emphasizes ... |
| 19 | motion & time | human-computer interaction | 1 | 41 | Motion design is a deliberate communication strategy that requires systematic planning and integration into the overall design process, not an afterthought or decorative element. The principle emphasi... |
| 20 | finance | economics | 1 | 42 | Investing with a long-term horizon and focusing on quality companies at reasonable prices generates superior returns over time, while the investment management industry as a whole fails to add value f... |
| 21 | design psychology | emerging | 1 | 44 | A principle for product development that emphasizes proactively identifying and addressing potential consumer objections before they arise, particularly for products requiring installation or complex ... |
| 22 | artificial intelligence | software engineering | 1 | 45 | Agentic AI systems require careful engineering to bridge the gap between model capabilities and real-world system reliability. These systems must address technical constraints like latency, connection... |
| 23 | research methodology | finance | 1 | 56 | A method for detecting regime changes in financial time series data by identifying significant directional movements in price or return data, originally developed by Richard Olsen. |
| 24 | strategic thinking | behavioral economics | 1 | 57 | Great marketing is characterized by the bold assertion that a better alternative exists and a willingness to lead users toward it, rather than simply offering a marginal improvement or alternative. Th... |
| 25 | psychology | health & medicine | 1 | 58 | A controversial therapeutic approach where patients allegedly recover memories of abuse through therapy, which can lead to false accusations and severe emotional trauma for all parties involved. |
| 26 | behavioral economics | psychology | 1 | 60 | Individuals are more effectively influenced by models who share their age group, particularly when the model's experience directly mirrors their own life stage. This principle describes a psychologica... |
