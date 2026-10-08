# Domain Ruler Review - reference sheet (2026-10-08)

Frozen ruler: DOMAIN_RULER_FROZEN_20261008.json - 201 rows, sha256 affe259e1c5a12da...
Review CSV: DOMAIN_RULER_REVIEW_20261008.csv (201 rows).

## The 41 canonical domains (closed menu)

- graphic design (dom-001): The practice of visual communication through layout, typography, and print media composition.
- brand identity (dom-002): The development of visual symbols, logos, and consistent aesthetic systems for corporate recognition.
- editorial & advertising (dom-003): The design and copywriting of publications, advertisements, and promotional visual materials.
- motion design (dom-004): The creation of animated visual content, motion graphics, and time-based digital media.
- environmental design (dom-005): The design of physical spaces, interiors, and wayfinding systems for human interaction.
- digital product (dom-006): The design and development of user interfaces and experiences for software applications.
- data visualization (dom-007): The graphical representation of quantitative data to facilitate understanding and analysis.
- creative technology (dom-008): The intersection of artistic practice and programming for interactive digital experiences.
- web & ui (dom-009): The design and architecture of responsive websites and user interface components.
- user experience (dom-010): The study of user behavior, research, and interaction design for digital products.
- illustration (dom-011): The creation of original visual artwork for narrative, decorative, or explanatory purposes.
- packaging (dom-012): The design of physical containers and structural materials for product protection and presentation.
- business operations (dom-013): The management of internal processes, accounting, and administrative functions within organizations.
- business development (dom-014): Strategic activities focused on market expansion, sales psychology, and revenue generation.
- entrepreneurship (dom-015): The process of creating, managing, and scaling new business ventures and startups.
- organizational behavior (dom-016): The study of human behavior, culture, and psychology within workplace structures.
- ai & agents (dom-017): The design and implementation of autonomous artificial intelligence systems and agents.
- urban planning (dom-018): The strategic development of cities, towns, and regional land use infrastructure.
- engineering practice (dom-019): The application of software architecture, programming languages, and development methodologies.
- computational art (dom-020): The creation of artistic works using algorithms, generative systems, and code.
- code & computation (dom-021): The use of specific programming frameworks and tools for creative and computational design.
- computational science & physics (dom-022): The application of computational models to simulate physical, biological, and social systems.
- systems & frameworks (dom-023): The theoretical analysis and design of complex interconnected systems and structures.
- semiotics & communication (dom-024): The study of signs, symbols, and visual rhetoric in human communication.
- research practice (dom-025): The professional activity of conducting, publishing, and applying scholarly and scientific research.
- education (dom-026): The design of instructional strategies, academic policy, and learning environments.
- health & wellness (dom-027): The promotion of physical, mental, and public health through healthcare systems.
- finance & investment (dom-028): The management of assets, portfolio theory, and financial planning strategies.
- marketing & communications (dom-029): Strategic promotion, public relations, and digital marketing for brand engagement.
- legal & public policy (dom-030): The study of law, public administration, and regulatory policy frameworks.
- arts & culture (dom-032): The practice and theory of visual arts, performance, and cultural expression.
- engineering & infrastructure (dom-033): The design of mechanical, aerospace, and distributed cloud computing systems.
- media & entertainment (dom-034): The development of video games, media technology, and publishing platforms.
- product design (dom-036): The holistic design of physical and digital products from concept to market.
- design strategy (dom-037): The management and strategic direction of design practices and organizations.
- project management (dom-038): The planning, execution, and oversight of projects and product development lifecycles.
- leadership (dom-039): The practice of guiding teams, strategic direction, and organizational dynamics.
- personal productivity (dom-040): Individual techniques for personal development, effectiveness, and time management.
- industrial design (dom-041): The design of manufactured physical products for mass production and usability.
- information architecture (dom-042): The structural organization of information for websites and digital interfaces.
- design systems (dom-043): The creation of reusable component libraries and design language standards.
- emerging (catch-all): no single field applies / not yet classified

## Review rubric (OntoClean: domain = role read off content, never inferred from discipline)

1. primary_domain: single highest-confidence application field?
2. domains (multi): every co-listed domain genuinely co-applicable? (no padding to hit 5)
3. emerging rows (8): catch-all means NO concrete field decided - assign one or confirm. See below.
4. over-assignment: single-field principle listed with 3+ domains = cardinality error (BUG-273).

Fill owner_review = KEEP / FIX / DROP and owner_notes with the correction.

## Rows whose primary_domain is the emerging catch-all (8) - owner must decide a concrete field

- R032 | Heckel's Diff Algorithm for Version Tracking | computational theory | domains=emerging
- R066 | N-dimensional Sphere Volume Properties | computational geometry | domains=emerging
- R085 | Discursive Strategy Abstraction | cultural studies | domains=emerging
- R101 | Pragmatist View of Truth and Knowledge | philosophy | domains=emerging
- R113 | Traveling Salesman Problem Computational Complexity | computational theory | domains=emerging
- R141 | Contextual Redundancy and Representation Efficiency | information science | domains=emerging
- R172 | Digital System Context Decomposition | engineering | domains=emerging
- R209 | Procedural Vs Declarative Knowledge Retrieval | cognitive science | domains=emerging