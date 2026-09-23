# F-11 DISC REVIEW SHEET — how to fill it

Built 2026-09-23T09:47:00 · BLANK_ABSTENTION 28 rows · CONSENSUS_DIVERGENCE 43 rows

On the 28 rows no human ever labelled, the two independent coder families agree on only 18 of them — so on the other 10 there is NO consensus to inherit. You are the only adjudicator for those.

## Columns (letters as in the CSV)

- `A1` item_id
- `B2` name
- `C3` why
- `D4` DECIDE
- `E5` human_disc_now
- `F6` claude_disc
- `G7` claude_conf
- `H8` kimi_disc
- `I9` kimi_conf
- `J10` coders_agree
- `K11` menu_check
- `L12` coders_consensus
- `M13` DEFINITION
- `N14` APPLICATION
- `O15` >>> FILL ONLY THE 3 COLUMNS AFTER THIS ONE <<<
- `P16` owner_disc_final
- `Q17` owner_keep_missing
- `R18` owner_notes

## What you do

1. Fill **only** `owner_disc_final`, `owner_keep_missing`, `owner_notes` — column `O15` is a blank fence column, and it exists so an empty column can never again be mistaken for free space (BUG-368).
2. `owner_disc_final`: exactly one value from the closed menu below, typed verbatim, **or** leave it empty and set `owner_keep_missing = yes` if you judge the row genuinely unlabelable. The two are mutually exclusive: a filled cell with `keep_missing = yes` is a contradiction and will be rejected.
3. `owner_notes`: free text, any language — the *why* (contract, provenance, ambiguity, near-neighbour).
4. Nothing else: do not rename, reorder, delete or add columns or rows. Do not edit A–N.

## Reading the columns

* `why=BLANK_ABSTENTION` — no human discipline label ever existed for this row (BUG-363).
* `why=CONSENSUS_DIVERGENCE` — you labelled it, both coder families agreed on something else.
* `coders_agree=YES` — both families independently produced the same value (`coders_consensus`).
* `coders_agree=NO` — they disagree; `coders_consensus` is empty, and there is nothing to inherit.
* `menu_check=OK` means every coder value resolves against the closed menu. Out-of-menu cells in this build: 0
* `claude_conf` / `kimi_conf` — the coder's own confidence, read as a relative signal only (Kimi is systematically more confident: mean 0.81 vs 0.59 on CT).

## Closed menu — disciplines (62 values, type verbatim)

### 

- `emerging` — Used when no canonical domain or discipline fits the principle ontologically and pragmatically. Preserves the raw S3A convergence label as s3_original…

### AI & Computing

- `artificial intelligence` — The broad field of creating systems capable of performing tasks that typically require human intelligence.
- `computational theory` — The study of the theoretical foundations of computation, including complexity and computability.
- `generative ai` — Artificial intelligence systems capable of creating new content, such as text, images, or code.
- `information retrieval` — The field of finding unstructured information, typically from documents, in response to queries.
- `machine learning` — The field of artificial intelligence focused on algorithms that learn patterns from data.
- `robotics` — The engineering and science of designing, building, and operating autonomous or controlled machines.
- `software engineering` — The systematic application of engineering principles to the design and development of software.

### Behavioral & Cognitive

- `behavioral economics` — The descriptive study of how psychological factors and cognitive biases cause systematic deviations from rational choice in economic decision-making a…
- `cognitive science` — The interdisciplinary study of how the mind works — perception, memory, attention, reasoning, language, and learning. The default home for any claim a…
- `decision making` — The cognitive and strategic process of selecting a course of action from alternatives — how options are framed, evaluated, and committed to under unce…
- `linguistics` — The scientific study of language structure, meaning, use, and its relationship to cognition.
- `neuroscience` — The scientific study of the nervous system, including the brain and neural circuits.
- `organizational theory` — The study of structures, processes, and dynamics within formal organizations and institutions — how they are designed, how they coordinate, and how th…
- `psychology` — The empirical study of mind and behavior in individuals and groups — emotion, personality, development, social behavior, and mental health — beyond th…

### Computational Craft

- `computational geometry` — The mathematical study of algorithms for solving problems involving geometric objects and structures.
- `computational physics & simulation` — The use of computer simulations to model and analyze physical systems and biological processes.
- `computer graphics` — The technology and techniques for generating and manipulating visual images using computers.
- `creative coding` — The use of programming languages and tools to create artistic and interactive digital experiences.
- `game design` — The process of creating rules, mechanics, and interactive experiences for video games.
- `generative design` — The use of algorithms and computational processes to generate design solutions and artistic forms.

### Design Cognition

- `aesthetics` — The philosophical study of beauty, taste, and the nature of artistic experience.
- `creative process` — The workflow, practices, and methodologies involved in generating and executing creative work.
- `design psychology` — The exploitation of cognitive science's known loopholes — biases, heuristics, and predictable errors of human thinking — to externally affect, persuad…
- `design thinking` — A human-centered approach to innovation — an iterative process (empathise → define → ideate → prototype → test) that integrates user needs, technology…
- `human-computer interaction` — The design and evaluation of user interfaces and systems for effective human-computer interaction.

### Form & Structure

- `color theory` — The principles governing color mixing, harmony, contrast, and their psychological impact on design.
- `motion & time` — The design and animation of visual elements involving movement, timing, and temporal sequencing.
- `typography` — The art and technique of arranging typefaces, spacing, and layout for effective visual communication.

### Heterodox

- `anthropology` — The study of human societies, cultures, and their development across time and space.
- `cultural studies` — The critical analysis of cultural practices, texts, and power relations in contemporary society — how meaning is produced, circulated, and contested w…
- `health & medicine` — The practice and science of maintaining, restoring, and promoting human physical and mental well-being.
- `information security` — The practice of protecting information systems from unauthorized access, use, or disclosure.
- `interdisciplinary studies` — Academic approaches that integrate methods and knowledge from multiple distinct disciplines.
- `law` — The system of rules created by society or government to regulate behavior and resolve disputes.
- `performing arts` — Artistic disciplines involving live performance, including music, theater, and dance.
- `philosophy` — The study of fundamental questions concerning existence, knowledge, values, reason, and mind.
- `political economy` — The study of the relationship between political institutions, economic systems, and power structures.
- `privacy & surveillance` — The study of data protection, monitoring practices, and the ethics of information observation.
- `sociology` — The scientific study of society, social institutions, and the patterns of human interaction.

### Operational & Strategy

- `economics` — The social science that studies the production, distribution, and consumption of goods and services.
- `finance` — The management of money, investments, and financial assets for individuals and organizations.
- `risk management` — The identification, assessment, prioritization, and mitigation of risks to minimize negative impact on operations, projects, or decisions — the practi…
- `strategic thinking` — The high-level planning and long-term goal setting involved in business and organizational management.

### Perception & Signal

- `communication theory` — The study of how information is transmitted, received, and interpreted across various channels.
- `cultural design` — The historical and theoretical analysis of design practices, aesthetics, and their cultural significance.
- `literary theory` — The critical frameworks and methods used to analyze and interpret literary texts.
- `media studies` — The academic analysis of media forms, technologies, and their social and cultural impacts.
- `semiotics` — The general study of signs, symbols, and their interpretation across biological and cognitive systems.
- `visual perception` — The biological and psychological process of interpreting visual sensory information and color stimuli.
- `visual semiotics` — The study of how visual signs, symbols, and rhetoric communicate meaning within cultural contexts.

### Systems & Method

- `complex adaptive systems` — The study of dynamic systems composed of interacting agents that adapt and evolve over time.
- `ecology` — The scientific study of the relationships between organisms and their physical and biological environments.
- `engineering` — The application of scientific principles to design, build, and maintain structures and machines.
- `evolutionary biology` — The study of the origin and diversification of life through genetic and natural selection processes.
- `information science` — The study of the collection, organization, and management of information and data systems.
- `operations research` — The application of advanced analytical methods to decision-making and system optimization.
- `research methodology` — The systematic frameworks and techniques used to conduct valid and reliable academic research.
- `social network analysis` — The study of social ties and structures using graph theory and network science methods.
- `systems engineering` — The interdisciplinary field focused on designing, integrating, and managing complex system architectures.
- `systems thinking` — An approach to understanding complex systems by analyzing their interrelationships and holistic behavior.
- `theoretical physics` — The branch of physics focused on mathematical models and abstract theories of natural phenomena.

## Provenance of the inputs read (R14)

- `governance/RULER_BLIND_SHEET_20260917.csv` sha256 `383231921fffda2c…`
- `governance/F11_DECISION_SHEET_20260922.csv` sha256 `6ce78e446e6015e6…`
- `config/closed_menu_v5.json` sha256 `bc53770103595f2a…`
- `coder[claude]` sha256 `0cb9ef902ad5a8cd…`
- `coder[kimi]` sha256 `dbe8a99f81616f62…`

## What happens next

You return the file. The anchor is then consolidated in ONE explicit, append-only step: your value wins where you ruled, `owner_keep_missing=yes` stays declared-missing (never imputed), and the ruler sheet is not rewritten — the consolidation lands as a new artifact with its own stamp, and the tier stays `llm-attested`/human-mixed until a genuinely independent human coder exists (F-11 stays open).