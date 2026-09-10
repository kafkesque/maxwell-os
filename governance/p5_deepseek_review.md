# DeepSeek-v4-pro P5 Review — discipline/domain adjudication (69 FBs)

**Model:** deepseek-v4-pro (frontier, C22 opt-in)  |  **Adjudicated:** 69/69

Replaces the local-LLM vote splits that conflated domain/discipline. Strict separation: discipline = field of study (61-list), domain = application area (43-list).

**Contamination flags:** 0 (fail-closed — review these first)

| example_id | discipline | domains | confidence | reason |
|---|---|---|---|---|
| S4-GOLD-MINED-00009 | `generative design` | computational art, product design, industrial design | medium | Parametric design systems use adjustable variables to generate variations, exemplifying generative design methodology. |
| S4-GOLD-MINED-00014 | `motion & time` | media & entertainment, motion design | high | Coordinating audio and visuals in motion graphics projects is a motion and time discipline. |
| S4-GOLD-MINED-00056 | `aesthetics` | media & entertainment, motion design | high | Systems esthetics integrates media forms into unified expressive frameworks, an aesthetic discipline. |
| S4-GOLD-MINED-00057 | `cultural studies` | brand identity, marketing & communications | high | This analyzes how brands commodify cultural markers, a cultural studies lens. |
| S4-GOLD-MINED-00063 | `software engineering` | digital product, graphic design | high | Vector file interoperability between design tools is a software engineering concern. |
| S4-GOLD-MINED-00091 | `philosophy` | science & research | medium | The observation that abstract mathematics later becomes physically useful is an epistemological pattern in philosophy of science. |
| S4-GOLD-MINED-00114 | `machine learning` | data visualization, research & methodology | high | PCA and t-SNE are machine learning techniques for dimensionality reduction used in visualization. |
| S4-GOLD-MINED-00134 | `philosophy` | user experience, product design, urban planning | high | Inclusive design politics raises ethical and political questions about nonhuman stakeholders, a philosophical design concern. |
| S4-GOLD-MINED-00147 | `sociology` | digital product, web & ui | high | Web 2.0 platforms enable multi-party interaction and collective social outcomes, a sociological framework. |
| S4-GOLD-MINED-00156 | `systems thinking` | urban planning | high | The critique of functional zoning and spontaneous interaction in planned cities uses a systems lens on urban dynamics. |
| S4-GOLD-MINED-00163 | `risk management` | engineering & infrastructure | high | The 3-copy backup strategy mitigates data loss risks through redundancy, a risk management heuristic. |
| S4-GOLD-MINED-00176 | `visual perception` | graphic design, motion design | high | Contrast directs attention and hierarchy through opposing visual elements, a perceptual design principle. |
| S4-GOLD-MINED-00228 | `psychology` | personal productivity | high | The inner critic is a psychological defense mechanism affecting creative individuals' productivity. |
| S4-GOLD-MINED-00233 | `evolutionary biology` | science & research | high | Genetic regulatory networks are a biological concept explaining gene expression hierarchy and evolutionary adaptability. |
| S4-GOLD-MINED-00242 | `political economy` | legal & public policy | medium | The model describes covert social control through manipulation of societal systems, analyzed from a political economy perspective. |
| S4-GOLD-MINED-00273 | `organizational theory` | business operations, project management, entrepreneurship | high | Innovation failure rates reflect organizational behavior and project management practices in business contexts. |
| S4-GOLD-MINED-00274 | `cultural design` | graphic design, brand identity, product design | high | The principle guides culturally sensitive and inclusive design across graphic, brand, and product contexts. |
| S4-GOLD-MINED-00278 | `sociology` | science & research | high | Stigler's Law describes a social pattern in scientific attribution, best analyzed through sociology. |
| S4-GOLD-MINED-00294 | `visual semiotics` | data visualization | medium | The method uses visual encoding to reveal textual structure, applying semiotic principles to data visualization. |
| S4-GOLD-MINED-00343 | `political economy` | finance & investment | high | Social innovation funding models are structured by political and economic forces, analyzed through political economy. |
| S4-GOLD-MINED-00348 | `cultural studies` | graphic design, brand identity, marketing & communications | high | The evolution of design styles follows cultural transmission and commodification processes studied in cultural studies. |
| S4-GOLD-MINED-00366 | `evolutionary biology` | science & research | medium | CRISPR-Cas9 gene editing is a biological technology with evolutionary implications, classified under evolutionary biology. |
| S4-GOLD-MINED-00368 | `creative coding` | creative technology, code & computation, user experience | high | Dynamic shape rendering is a creative coding technique applied in interactive media and user experience. |
| S4-GOLD-MINED-00372 | `computer graphics` | graphic design, web & ui, media & entertainment | high | Resolution and scaling control are technical aspects of computer graphics applied in digital media workflows. |
| S4-GOLD-MINED-00373 | `cultural design` | graphic design, industrial design, digital product, design systems | medium | Cultural synthesis in design reflects cultural design principles across multiple design domains. |
| S4-GOLD-MINED-00411 | `creative coding` | arts & culture, media & entertainment | high | Parameterized sound variation is a creative coding technique for dynamic audio in media and arts contexts. |
| S4-GOLD-MINED-00420 | `information science` | business operations, legal & public policy, marketing & communications | high | Data-driven bias arises from information systems and their social context, analyzed through information science. |
| S4-GOLD-MINED-00421 | `computer graphics` | graphic design, motion design | high | Layer ordering controls visual stacking and rendering order in digital design and animation software, which is a core topic of computer graphics. |
| S4-GOLD-MINED-00423 | `theoretical physics` | education, science & research | medium | The periodic table ordering by atomic weight reflects atomic structure and chemical periodicity, a physical science principle. |
| S4-GOLD-MINED-00434 | `sociology` | education | medium | The composite of academic role and personal interests shaping professional identity is a sociological analysis of roles and self-presentation in education. |
| S4-GOLD-MINED-00440 | `creative coding` | arts & culture, media & entertainment, computational art | high | Algorithmic composition uses computational processes to generate audio and visual structures, a core creative coding practice. |
| S4-GOLD-MINED-00481 | `behavioral economics` | marketing & communications, leadership | medium | The perception of mutual benefit in two-way exchanges and its influence on cooperation aligns with behavioral economics principles applied to marketing and leadership. |
| S4-GOLD-MINED-00482 | `color theory` | media & entertainment | high | Systematic color meanings and cultural associations as emotional narrative cues in film directly address color theory within media storytelling. |
| S4-GOLD-MINED-00505 | `operations research` | business operations, data visualization | high | Pareto chart analysis is a quantitative decision-making tool rooted in operations research, used to prioritize factors in business operations through data visualization. |
| S4-GOLD-MINED-00507 | `visual semiotics` | graphic design, semiotics & communication | medium | Cosmic maps blend scientific observation with symbolic interpretation, functioning as visual signs that communicate cosmic order, which is the study of visual semiotics. |
| S4-GOLD-MINED-00525 | `cultural studies` | urban planning | high | The embedding of colonial power structures into mapping platforms through translation of local knowledge is a cultural studies critique of representation and power in spatial systems. |
| S4-GOLD-MINED-00527 | `privacy & surveillance` | urban planning | high | The cartographic gaze as an elevated observational perspective enabling surveillance and social control is a core concept in privacy and surveillance studies applied to mapped urban space. |
| S4-GOLD-MINED-00541 | `philosophy` | user experience, product design, urban planning | high | The critique of human-centered design's neglect of ecological and long-term consequences raises philosophical questions about values and responsibility in design practice. |
| S4-GOLD-MINED-00548 | `media studies` | editorial & advertising | high | The transformation of illustrated book quality through technological advances in printing and binding is a historical media studies topic within editorial publishing. |
| S4-GOLD-MINED-00587 | `sociology` | (none) | low | Thing-powered agency as distributed across human and nonhuman actors is a sociological actor-network theory concept without a specific application domain in the text. |
| S4-GOLD-MINED-00602 | `generative design` | computational art, media & entertainment | high | The foundation of generative art through computational elements and parameter expansion is a generative design approach. |
| S4-GOLD-MINED-00604 | `economics` | organizational behavior, leadership | medium | Flexibility as a third currency in value exchange models is an economic concept applied to negotiating work conditions and autonomy in organizational leadership contexts. |
| S4-GOLD-MINED-00624 | `cultural studies` | data visualization | medium | Feminist data visualization centering marginalized perspectives to challenge dominant narratives is a cultural studies approach applied to data visualization practice. |
| S4-GOLD-MINED-00631 | `risk management` | ai & agents | high | Ethical safeguards and proactive risk mitigation for AI systems are core risk management practices applied within the AI & agents domain. |
| S4-GOLD-MINED-00655 | `computer graphics` | motion design, media & entertainment | high | Visual effects, compositing, and motion graphics workflow integration through layer management and scripting are technical computer graphics topics applied in motion design and media production. |
| S4-GOLD-MINED-00656 | `philosophy` | product design, industrial design | high | Ethical design principle about moral value of craft and rejection of mass production. |
| S4-GOLD-MINED-00665 | `information science` | legal & public policy, research & methodology, education, science & research | high | Open data ecosystems are about shared information infrastructure and reuse across sectors. |
| S4-GOLD-MINED-00668 | `machine learning` | health & wellness, science & research | high | Computational method using network-derived features for drug discovery prediction. |
| S4-GOLD-MINED-00671 | `computational theory` | code & computation | high | Theoretical problem about recursive set generation and ordering unpredictability. |
| S4-GOLD-MINED-00693 | `cultural studies` | graphic design, arts & culture | high | Historical cultural shift in typography toward artistic and cultural expression. |
| S4-GOLD-MINED-00699 | `strategic thinking` | business operations, digital product, project management, entrepreneurship | high | Resource-constrained focus strategy for prioritizing a single objective under scarcity. |
| S4-GOLD-MINED-00722 | `political economy` | legal & public policy | high | Arbitrary rule enforcement in totalitarian systems as a mechanism of political control. |
| S4-GOLD-MINED-00729 | `software engineering` | media & entertainment | high | Systematic debugging and testing methodology for interactive media systems. |
| S4-GOLD-MINED-00746 | `media studies` | education, legal & public policy | high | Selective historical representation in narrative construction and timeline curation. |
| S4-GOLD-MINED-00795 | `semiotics` | graphic design, brand identity, marketing & communications | high | Archetypal symbols and their shared meanings across cultural and design contexts. |
| S4-GOLD-MINED-00807 | `artificial intelligence` | ai & agents | medium | Neural network phenomenon of bidirectional processing leading to emergent meaning. |
| S4-GOLD-MINED-00850 | `aesthetics` | arts & culture | high | Material transparency in sculpture as artistic mastery rendering the medium invisible. |
| S4-GOLD-MINED-00864 | `visual perception` | editorial & advertising, graphic design, media & entertainment, user experience | high | Structural composition dynamics and how viewers perceive and process graphic design. |
| S4-GOLD-MINED-00895 | `philosophy` | graphic design, semiotics & communication | high | Ethical dimensions and responsibilities inherent in graphic design practice. |
| S4-GOLD-MINED-00927 | `risk management` | health & wellness | high | Asymmetric risk trade-off favoring early and frequent medical screening. |
| S4-GOLD-MINED-00932 | `psychology` | (none) | high | The principle focuses on predictable human behavior and cognitive biases in social engineering, making psychology the correct theoretical lens. |
| S4-GOLD-MINED-00945 | `creative process` | arts & culture | medium | The principle prescribes a practical mindset and method for creative work, aligning with the creative process discipline; its application is in arts and culture. |
| S4-GOLD-MINED-00955 | `cultural design` | graphic design, user experience | high | The principle concerns integration of digital culture into graphic design practice, which is cultural design; it applies to graphic design and UX. |
| S4-GOLD-MINED-00963 | `theoretical physics` | (none) | high | The mechanism describes light scattering and atmospheric optics, a topic in theoretical physics, with no specific application domain. |
| S4-GOLD-MINED-00975 | `organizational theory` | business operations | high | B-Corp certification involves organizational standards and governance, studied under organizational theory; its application is business operations. |
| S4-GOLD-MINED-00977 | `economics` | business operations, digital product, marketing & communications | high | The mechanism describes market penetration and displacement of technologies, an economics topic; it applies to business, product, and marketing. |
| S4-GOLD-MINED-01010 | `economics` | ai & agents, business operations, entrepreneurship | medium | The visibility threshold is determined by investment and market conditions, an economics pattern; applied to AI commercialization and business. |
| S4-GOLD-MINED-01017 | `anthropology` | (none) | medium | The principle provides a descriptive model of how religious systems use symbols and rituals to organize moral behavior, which is anthropological; no specific application domain. |
| S4-GOLD-MINED-01021 | `aesthetics` | creative technology, media & entertainment, computational art, arts & culture | high | The object describes aesthetic effects emerging from video feedback systems, making aesthetics the disciplinary lens, applied in creative technology and arts/media contexts. |

> SIGNAL NOT PROOF — human remains arbiter (D2595). Contamination flags must be re-adjudicated.