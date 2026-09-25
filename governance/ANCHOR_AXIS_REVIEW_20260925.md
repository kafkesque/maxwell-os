# ANCHOR adjudication - REVIEW SHEET (read this before the CSV)

Every row the cross-examination puts in front of you, with what each independent reader said and
the recommendation this repo can defend. Advisory only: your `*_final` values are written by you,
in the workbooks CSV (`governance/anchor_adjudication_workbook_20260924.csv`), whose owner
columns are EMPTY and must stay empty until you type in them.

`machine_recommendation` legend: `domain=<label> as PRIMARY` = a coder plurality exists, confirm
or replace | `domain=OWNER_ONLY` = no label reaches share 0.5, yours to name |
`depth=KEEP` = coders agree with you, nothing to do | `depth=CHECK_OWNER_FIRST` = coders agree with
EACH OTHER against you, so it is a clean signal about the cell or the rubric | `depth=OWNER_RULING_NEAR`
= one class apart, the D2/D3 boundary | `depth=RECODE_BAND` = span >= 2 classes, do not adjudicate it,
re-code it | `depth=NOT_A_CLAIM?` = a coder refused the menu.

## HARD (36 rows)

### R005 - Graphics Algebra Cross Operator
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational art | claude-sonnet-5: d=4 / data visualization|code & computation | deepseek-v4-pro: d=None / data visualization | kimi: d=4 / data visualization
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: code & computation|computational art|data visualization
- **RECOMMEND** `domain=data visualization as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with data visualization - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R013 - Innovation Fund Risk Management
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business development|business operations|design strategy | claude-sonnet-5: d=3 / organizational behavior|finance & investment|leadership | deepseek-v4-pro: d=None / business operations|entrepreneurship|finance & investment|organizational behavior|project management | kimi: d=3 / business operations|entrepreneurship
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: business development|business operations|design strategy|entrepreneurship|finance & investment|leadership|organizational behavior|project management
- **RECOMMEND** `domain=business operations as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R015 - Long-term Strategic Planning in Different Industries
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|design strategy | claude-sonnet-5: d=2 / business operations|finance & investment | deepseek-v4-pro: d=None / business development|business operations|finance & investment|leadership | kimi: d=2 / business development|leadership
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: business development|business operations|design strategy|finance & investment|leadership
- **RECOMMEND** `domain=business development as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R017 - Chemical Reaction Equation Automation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational science & physics | claude-sonnet-5: d=4 / science & research|code & computation|engineering practice | deepseek-v4-pro: d=None / computational science & physics|science & research | kimi: d=4 / computational science & physics|code & computation
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: code & computation|computational science & physics|engineering practice|science & research
- **RECOMMEND** `domain=computational science & physics as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with computational science & physics - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R023 - Focused Action Selection
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|design strategy | claude-sonnet-5: d=2 / leadership|personal productivity|business operations | deepseek-v4-pro: d=None / business development|design strategy|leadership|project management | kimi: d=2 / business development|leadership
- **owner depth** 2 (conf 3) | coder spread 0 | domain union: business development|business operations|design strategy|leadership|personal productivity|project management
- **RECOMMEND** `domain=business development as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R024 - Execution Gap From Technological Readiness
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|design strategy | claude-sonnet-5: d=2 / organizational behavior|business operations|leadership | deepseek-v4-pro: d=None / business development|entrepreneurship|leadership|organizational behavior|project management | kimi: d=2 / business operations|business development
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|business operations|design strategy|entrepreneurship|leadership|organizational behavior|project management
- **RECOMMEND** `domain=business operations as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R028 - Gpu Acceleration Configuration
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|engineering practice | claude-sonnet-5: d=4 / ai & agents|engineering practice|code & computation | deepseek-v4-pro: d=None / ai & agents|code & computation|engineering & infrastructure|engineering practice | kimi: d=4 / code & computation|engineering & infrastructure
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|engineering & infrastructure|engineering practice
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R032 - Heckel's Diff Algorithm for Version Tracking
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|engineering practice | claude-sonnet-5: d=4 / code & computation|information architecture|data visualization | deepseek-v4-pro: d=None / engineering practice | kimi: d=4 / code & computation|data visualization
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: code & computation|data visualization|engineering practice|information architecture
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R035 - Visual Evidence Recognition
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|semiotics & communication | claude-sonnet-5: d=2 / research & methodology|data visualization|science & research | deepseek-v4-pro: d=None / science & research|semiotics & communication|systems & frameworks | kimi: d=2 / research & methodology|data visualization
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: data visualization|research & methodology|science & research|semiotics & communication|systems & frameworks
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R043 - Alpha State Thinking and Creative Problem-solving
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|creative technology | claude-sonnet-5: d=2 / personal productivity|health & wellness | deepseek-v4-pro: d=None / design strategy|personal productivity | kimi: d=2 / personal productivity|health & wellness
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|creative technology|design strategy|health & wellness|personal productivity
- **RECOMMEND** `domain=personal productivity as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with personal productivity - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R048 - Creative Process Through Drawing and Sketching
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|illustration | claude-sonnet-5: d=3 / arts & culture|design strategy|personal productivity | deepseek-v4-pro: d=None / graphic design|illustration|product design | kimi: d=2 / graphic design|illustration
- **owner depth** 2 (conf 3) | coder spread 1 | domain union: arts & culture|design strategy|graphic design|illustration|personal productivity|product design
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R062 - Somatic Marker Decision Making
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|user experience | claude-sonnet-5: d=2 / marketing & communications|social sciences | deepseek-v4-pro: d=None / marketing & communications|social sciences|user experience | kimi: d=2 / marketing & communications|social sciences
- **owner depth** 1 (conf 2) | coder spread 0 | domain union: design strategy|marketing & communications|social sciences|user experience
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R066 - N-dimensional Sphere Volume Properties
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational science & physics | claude-sonnet-5: d=1 / computational science & physics|code & computation | deepseek-v4-pro: d=None / computational science & physics|science & research | kimi: d=4 / computational science & physics
- **owner depth** 4 (conf 2) | coder spread 3 | domain union: code & computation|computational science & physics|science & research
- **RECOMMEND** `domain=computational science & physics as PRIMARY; depth=RECODE_BAND`
- why: 3/4 coders LEAD with computational science & physics - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders span 3 classes - name the boundary in the rubric and re-code this band
- **you must answer: domain;depth**
- flags: `DEPTH_HARD_SPLIT;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R067 - Schemat's Wasser Interactive Art Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|creative technology|digital product | claude-sonnet-5: d=4 / arts & culture|creative technology|media & entertainment | deepseek-v4-pro: d=None / arts & culture|creative technology|media & entertainment|user experience | kimi: d=4 / computational art|media & entertainment
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: arts & culture|computational art|creative technology|digital product|media & entertainment|user experience
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R074 - Attention Economy Externalities
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|digital product|user experience | claude-sonnet-5: d=3 / social sciences|health & wellness|media & entertainment | deepseek-v4-pro: d=None / digital product|marketing & communications|media & entertainment|social sciences|user experience | kimi: d=2 / social sciences|digital product
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: design strategy|digital product|health & wellness|marketing & communications|media & entertainment|social sciences|user experience
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R075 - Paradigm Shift Through Disruption
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|design strategy | claude-sonnet-5: d=2 / science & research|research & methodology|systems & frameworks | deepseek-v4-pro: d=None / research & methodology|science & research|systems & frameworks | kimi: d=2 / science & research|systems & frameworks
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: arts & culture|design strategy|research & methodology|science & research|systems & frameworks
- **RECOMMEND** `domain=science & research as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with science & research - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R080 - Information Design Community Networks
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|information architecture|social sciences | claude-sonnet-5: d=3 / information architecture|organizational behavior|education | deepseek-v4-pro: d=None / organizational behavior|social sciences | kimi: d=3 / information architecture|data visualization
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: data visualization|design strategy|education|information architecture|organizational behavior|social sciences
- **RECOMMEND** `domain=information architecture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with information architecture - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R089 - Vr Body Constraint and Physical Immersion
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / creative technology|digital product|user experience | claude-sonnet-5: d=4 / creative technology|user experience | deepseek-v4-pro: d=None / digital product|media & entertainment|user experience | kimi: d=3 / creative technology|media & entertainment
- **owner depth** 4 (conf 3) | coder spread 1 | domain union: creative technology|digital product|media & entertainment|user experience
- **RECOMMEND** `domain=creative technology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with creative technology - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R090 - Culture Jamming
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|marketing & communications|semiotics & communication | claude-sonnet-5: d=3 / media & entertainment|marketing & communications|arts & culture | deepseek-v4-pro: d=None / arts & culture|editorial & advertising|media & entertainment|semiotics & communication | kimi: d=3 / media & entertainment|marketing & communications
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: arts & culture|editorial & advertising|marketing & communications|media & entertainment|semiotics & communication
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R092 - Data Quality and Method Transparency in Journalism
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|media & entertainment|research & methodology | claude-sonnet-5: d=3 / media & entertainment|research & methodology | deepseek-v4-pro: d=None / media & entertainment|research & methodology | kimi: d=3 / editorial & advertising|data visualization
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: data visualization|editorial & advertising|media & entertainment|research & methodology
- **RECOMMEND** `domain=media & entertainment as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with media & entertainment - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R093 - Numerical Symbolism in Design and Biology
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|science & research|semiotics & communication | claude-sonnet-5: d=2 / arts & culture|science & research|semiotics & communication | deepseek-v4-pro: d=None / arts & culture|science & research|semiotics & communication | kimi: d=4 / semiotics & communication|graphic design
- **owner depth** 3 (conf 1) | coder spread 2 | domain union: arts & culture|graphic design|science & research|semiotics & communication
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=RECODE_BAND`
- why: 3/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders span 2 classes - name the boundary in the rubric and re-code this band
- **you must answer: domain;depth**
- flags: `DEPTH_HARD_SPLIT;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R097 - Minimin Decision Criterion
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy | claude-sonnet-5: d=4 / research & methodology|finance & investment|business development | deepseek-v4-pro: d=None / business operations|finance & investment|project management | kimi: d=4 / systems & frameworks|research & methodology
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: business development|business operations|design strategy|finance & investment|project management|research & methodology|systems & frameworks
- **RECOMMEND** `domain=OWNER_ONLY; depth=no dispute`
- why: no label is LED by half the coders (best primary share 0.25 of 4, best set-membership share 0.50) - the PRIMARY label is yours to name; the coder sets stay in this row as provenance
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R101 - Pragmatist View of Truth and Knowledge
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture | claude-sonnet-5: d=2 / social sciences|research & methodology | deepseek-v4-pro: d=None / research & methodology | kimi: d=3 / social sciences|research & methodology
- **owner depth** 1 (conf 2) | coder spread 1 | domain union: arts & culture|research & methodology|social sciences
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R103 - Temporal Consistency in Visual Narrative Analysis
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|illustration|semiotics & communication | claude-sonnet-5: d=3 / media & entertainment|semiotics & communication|illustration | deepseek-v4-pro: d=None / arts & culture|media & entertainment|semiotics & communication | kimi: d=3 / research & methodology|media & entertainment
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: arts & culture|illustration|media & entertainment|research & methodology|semiotics & communication
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R105 - Probabilistic Forecasting with Prediction Intervals
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|design strategy|research & methodology | claude-sonnet-5: d=2 / business operations|research & methodology|finance & investment | deepseek-v4-pro: d=None / business operations|finance & investment|project management | kimi: d=2 / research & methodology|business operations
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business operations|data visualization|design strategy|finance & investment|project management|research & methodology
- **RECOMMEND** `domain=business operations as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R113 - Traveling Salesman Problem Computational Complexity
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|systems & frameworks | claude-sonnet-5: d=1 / code & computation|science & research | deepseek-v4-pro: d=None / engineering practice|systems & frameworks | kimi: d=4 / code & computation|computational science & physics
- **owner depth** 4 (conf 3) | coder spread 3 | domain union: code & computation|computational science & physics|engineering practice|science & research|systems & frameworks
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=RECODE_BAND`
- why: 3/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders span 3 classes - name the boundary in the rubric and re-code this band
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DEPTH_HARD_SPLIT;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R126 - Embodied Knowledge in Design
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|design strategy | claude-sonnet-5: d=3 / design strategy|arts & culture|industrial design | deepseek-v4-pro: d=None / arts & culture|product design|semiotics & communication | kimi: d=3 / design strategy|product design
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: arts & culture|design strategy|industrial design|product design|semiotics & communication
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R128 - Choice Architecture and Identity Framing
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / marketing & communications|personal productivity|social sciences | claude-sonnet-5: d=3 / marketing & communications|organizational behavior|brand identity | deepseek-v4-pro: d=None / marketing & communications|organizational behavior|personal productivity | kimi: d=2 / organizational behavior|social sciences
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: brand identity|marketing & communications|organizational behavior|personal productivity|social sciences
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R131 - Differential Privacy in Data Collection
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|legal & public policy|research & methodology | claude-sonnet-5: d=2 / code & computation|ai & agents | deepseek-v4-pro: d=None / ai & agents|engineering practice|legal & public policy|research & methodology|science & research | kimi: d=4 / code & computation|legal & public policy
- **owner depth** 4 (conf 3) | coder spread 2 | domain union: ai & agents|code & computation|data visualization|engineering practice|legal & public policy|research & methodology|science & research
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=RECODE_BAND`
- why: 2/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders span 2 classes - name the boundary in the rubric and re-code this band
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DEPTH_HARD_SPLIT;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R133 - Three-holes-in-the-cheese Model of Error Cascades
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / systems & frameworks | claude-sonnet-5: d=2 / engineering practice|organizational behavior|legal & public policy | deepseek-v4-pro: d=None / business operations|engineering & infrastructure|health & wellness|systems & frameworks | kimi: d=2 / organizational behavior|systems & frameworks
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: business operations|engineering & infrastructure|engineering practice|health & wellness|legal & public policy|organizational behavior|systems & frameworks
- **RECOMMEND** `domain=OWNER_ONLY; depth=no dispute`
- why: no label is LED by half the coders (best primary share 0.25 of 4, best set-membership share 0.75) - the PRIMARY label is yours to name; the coder sets stay in this row as provenance
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R141 - Contextual Redundancy and Representation Efficiency
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|information architecture|semiotics & communication | claude-sonnet-5: d=2 / ai & agents|code & computation|research & methodology | deepseek-v4-pro: d=None / ai & agents|information architecture|systems & frameworks | kimi: d=2 / systems & frameworks|code & computation
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: ai & agents|code & computation|data visualization|information architecture|research & methodology|semiotics & communication|systems & frameworks
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 0.50 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R144 - Abra-kadabra Number Classification
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|systems & frameworks | claude-sonnet-5: d=1 / code & computation|education | deepseek-v4-pro: d=None / code & computation | kimi: d=4 / code & computation|education
- **owner depth** 4 (conf 3) | coder spread 3 | domain union: code & computation|education|systems & frameworks
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=RECODE_BAND`
- why: 4/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders span 3 classes - name the boundary in the rubric and re-code this band
- **you must answer: domain;depth**
- flags: `DEPTH_HARD_SPLIT;DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R145 - Color As Cultural and Emotional Marker
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|graphic design|semiotics & communication | claude-sonnet-5: d=3 / brand identity|arts & culture|marketing & communications | deepseek-v4-pro: d=None / arts & culture|brand identity|graphic design|semiotics & communication | kimi: d=2 / graphic design|semiotics & communication
- **owner depth** 2 (conf 3) | coder spread 1 | domain union: arts & culture|brand identity|graphic design|marketing & communications|semiotics & communication
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R148 - Professional Development Through Studio Experience
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|design strategy | claude-sonnet-5: d=3 / education|design strategy|organizational behavior | deepseek-v4-pro: d=None / design strategy|education|organizational behavior | kimi: d=3 / education|graphic design
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|design strategy|education|graphic design|organizational behavior
- **RECOMMEND** `domain=education as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with education - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R149 - Perceptual Mapping Through Camouflage
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|computational art|data visualization | claude-sonnet-5: d=4 / data visualization|creative technology | deepseek-v4-pro: d=None / arts & culture|creative technology|research & methodology|semiotics & communication | kimi: d=4 / data visualization|creative technology
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|computational art|creative technology|data visualization|research & methodology|semiotics & communication
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R150 - Triple Bottom Line Business Approach
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|design strategy | claude-sonnet-5: d=2 / business operations|leadership | deepseek-v4-pro: d=None / business development|business operations|entrepreneurship|organizational behavior | kimi: d=3 / business development|finance & investment
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: business development|business operations|design strategy|entrepreneurship|finance & investment|leadership|organizational behavior
- **RECOMMEND** `domain=business development as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 0.75 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_NO_OVERLAP;DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

## SOFT (112 rows)

### R001 - Surveillance Capitalism Value Proposition
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / digital product|marketing & communications|user experience | claude-sonnet-5: d=3 / business development|marketing & communications|legal & public policy | deepseek-v4-pro: d=None / business development|digital product|marketing & communications | kimi: d=3 / digital product|marketing & communications
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|digital product|legal & public policy|marketing & communications|user experience
- **RECOMMEND** `domain=business development as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R002 - Soviet Underground Discourse Reception
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|media & entertainment|semiotics & communication | claude-sonnet-5: d=4 / arts & culture|social sciences|media & entertainment | deepseek-v4-pro: d=None / arts & culture|media & entertainment|semiotics & communication|social sciences | kimi: d=3 / arts & culture|social sciences
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: arts & culture|media & entertainment|semiotics & communication|social sciences
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R004 - Lockdown Effectiveness and Economic Impact
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / health & wellness|research & methodology|social sciences | claude-sonnet-5: d=4 / legal & public policy|health & wellness | deepseek-v4-pro: d=None / health & wellness|legal & public policy|research & methodology|social sciences | kimi: d=3 / health & wellness|legal & public policy
- **owner depth** 4 (conf 3) | coder spread 1 | domain union: health & wellness|legal & public policy|research & methodology|social sciences
- **RECOMMEND** `domain=health & wellness as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with health & wellness - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R006 - Generative Algorithmic Composition
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational art|creative technology | claude-sonnet-5: d=2 / computational art|creative technology | deepseek-v4-pro: d=None / computational art|creative technology|media & entertainment | kimi: d=3 / computational art|creative technology
- **owner depth** 4 (conf 3) | coder spread 1 | domain union: code & computation|computational art|creative technology|media & entertainment
- **RECOMMEND** `domain=computational art as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with computational art - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R007 - Accessible Electronic Prototyping Ecosystem
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / creative technology|engineering practice | claude-sonnet-5: d=3 / engineering practice|education|creative technology | deepseek-v4-pro: d=None / creative technology|education|engineering practice | kimi: d=3 / creative technology|education
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: creative technology|education|engineering practice
- **RECOMMEND** `domain=creative technology as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with creative technology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R008 - Inescapable Shock Syndrome
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / health & wellness|social sciences | claude-sonnet-5: d=3 / health & wellness|science & research | deepseek-v4-pro: d=None / health & wellness|science & research|social sciences | kimi: d=3 / health & wellness|social sciences
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: health & wellness|science & research|social sciences
- **RECOMMEND** `domain=health & wellness as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with health & wellness - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R009 - Entrepreneurial Risk Assessment Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / entrepreneurship | claude-sonnet-5: d=2 / entrepreneurship|finance & investment | deepseek-v4-pro: d=None / entrepreneurship|finance & investment | kimi: d=3 / entrepreneurship|finance & investment
- **owner depth** 2 (conf 2) | coder spread 1 | domain union: entrepreneurship|finance & investment
- **RECOMMEND** `domain=entrepreneurship as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with entrepreneurship - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R010 - Iterative Launch Process
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|product design|user experience | claude-sonnet-5: d=2 / product design|project management|business development | deepseek-v4-pro: d=None / design strategy|digital product|entrepreneurship|product design|project management | kimi: d=2 / business development|product design
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: business development|design strategy|digital product|entrepreneurship|product design|project management|user experience
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R011 - Agentic Decision-making Through Contextual Retrieval
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|engineering practice | claude-sonnet-5: d=3 / ai & agents|code & computation | deepseek-v4-pro: d=None / ai & agents|engineering practice | kimi: d=3 / ai & agents
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|engineering practice
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R012 - Evolution of Game Art and Design
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|media & entertainment | claude-sonnet-5: d=3 / media & entertainment|arts & culture | deepseek-v4-pro: d=None / arts & culture|digital product|media & entertainment | kimi: d=3 / media & entertainment|arts & culture
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: arts & culture|digital product|media & entertainment
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R014 - Sacred Geometry and Symbolic Resonance
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|illustration|semiotics & communication | claude-sonnet-5: d=2 / arts & culture|semiotics & communication|social sciences | deepseek-v4-pro: d=None / arts & culture|semiotics & communication|social sciences | kimi: d=2 / arts & culture|semiotics & communication
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|illustration|semiotics & communication|social sciences
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R016 - Modelans-modelandum Relationship
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|semiotics & communication | claude-sonnet-5: d=2 / semiotics & communication|research & methodology | deepseek-v4-pro: d=None / semiotics & communication | kimi: d=2 / semiotics & communication|systems & frameworks
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: design strategy|research & methodology|semiotics & communication|systems & frameworks
- **RECOMMEND** `domain=semiotics & communication as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with semiotics & communication - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R018 - Color and Typography Readability
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / graphic design | claude-sonnet-5: d=2 / graphic design|user experience | deepseek-v4-pro: d=None / editorial & advertising|graphic design | kimi: d=3 / graphic design
- **owner depth** 2 (conf 3) | coder spread 1 | domain union: editorial & advertising|graphic design|user experience
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R019 - Scientific Research Evaluation Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / research & methodology|science & research | claude-sonnet-5: d=3 / research & methodology|education|science & research | deepseek-v4-pro: d=None / research & methodology|science & research | kimi: d=3 / research & methodology|science & research
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: education|research & methodology|science & research
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R020 - Dynamic System Complexity
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|systems & frameworks | claude-sonnet-5: d=2 / systems & frameworks|business operations|science & research | deepseek-v4-pro: d=None / systems & frameworks | kimi: d=2 / systems & frameworks|business development
- **owner depth** 2 (conf 1) | coder spread 0 | domain union: business development|business operations|design strategy|science & research|systems & frameworks
- **RECOMMEND** `domain=systems & frameworks as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with systems & frameworks - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R021 - Index Section
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / editorial & advertising|information architecture | claude-sonnet-5: d=none_fits / - | deepseek-v4-pro: d=None / editorial & advertising|information architecture | kimi: d=2 / information architecture
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: editorial & advertising|information architecture
- **RECOMMEND** `domain=editorial & advertising as PRIMARY; depth=NOT_A_CLAIM?`
- why: 2/3 coders LEAD with editorial & advertising - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | a coder REFUSED the menu ('none_fits') - decide whether the row is a claim at all
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_MENU_DECLINED;OWNER_coder_majority_DIFFERS`

### R022 - Coupon Code Feature Placement Strategy
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / digital product|user experience|web & ui | claude-sonnet-5: d=4 / user experience|web & ui|marketing & communications | deepseek-v4-pro: d=None / digital product|marketing & communications|user experience|web & ui | kimi: d=4 / user experience|digital product
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: digital product|marketing & communications|user experience|web & ui
- **RECOMMEND** `domain=digital product as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with digital product - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R025 - Design for Management and Organizational Culture
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|leadership|organizational behavior | claude-sonnet-5: d=3 / design strategy|organizational behavior|leadership | deepseek-v4-pro: d=None / business operations|design strategy|leadership|organizational behavior | kimi: d=3 / design strategy|organizational behavior
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business operations|design strategy|leadership|organizational behavior
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R026 - Index of Motion Graphic Title Design Terms
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / information architecture|media & entertainment|motion design | claude-sonnet-5: d=none_fits / - | deepseek-v4-pro: d=None / graphic design|media & entertainment|motion design | kimi: d=4 / motion design
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: graphic design|information architecture|media & entertainment|motion design
- **RECOMMEND** `domain=OWNER_ONLY; depth=NOT_A_CLAIM?`
- why: no label is LED by half the coders (best primary share 0.33 of 3, best set-membership share 1.00) - the PRIMARY label is yours to name; the coder sets stay in this row as provenance | a coder REFUSED the menu ('none_fits') - decide whether the row is a claim at all
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_MENU_DECLINED`

### R027 - Decentralized Strategic Command
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|leadership|organizational behavior | claude-sonnet-5: d=2 / leadership|organizational behavior|project management | deepseek-v4-pro: d=None / leadership|organizational behavior | kimi: d=2 / leadership|organizational behavior
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: design strategy|leadership|organizational behavior|project management
- **RECOMMEND** `domain=leadership as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with leadership - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R029 - Innovation Through Challenge to Assumptions
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|design strategy | claude-sonnet-5: d=3 / brand identity|business development|marketing & communications | deepseek-v4-pro: d=None / brand identity|business development|design strategy|marketing & communications | kimi: d=3 / brand identity|marketing & communications
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: brand identity|business development|design strategy|marketing & communications
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R030 - Digital Iconic Reproduction in Computer Graphics
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational art | claude-sonnet-5: d=4 / computational art|engineering practice|code & computation | deepseek-v4-pro: d=None / code & computation|computational art | kimi: d=4 / code & computation|semiotics & communication
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: code & computation|computational art|engineering practice|semiotics & communication
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R031 - Questionnaire Validation and Modification Risk
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / research & methodology | claude-sonnet-5: d=3 / research & methodology|user experience | deepseek-v4-pro: d=None / research & methodology | kimi: d=3 / research & methodology|user experience
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: research & methodology|user experience
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R033 - Postmodern Critique of Realist Assumptions
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|research & methodology|social sciences | claude-sonnet-5: d=2 / social sciences|research & methodology | deepseek-v4-pro: d=None / research & methodology|social sciences | kimi: d=3 / social sciences|research & methodology
- **owner depth** 1 (conf 2) | coder spread 1 | domain union: arts & culture|research & methodology|social sciences
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R034 - Negative Space Alphabet Challenge
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / creative technology|graphic design|illustration | claude-sonnet-5: d=4 / graphic design|creative technology|illustration | deepseek-v4-pro: d=None / arts & culture|graphic design|illustration | kimi: d=4 / graphic design|illustration
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|creative technology|graphic design|illustration
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R036 - Domain Name Call-to-action Strategy
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|marketing & communications|web & ui | claude-sonnet-5: d=4 / brand identity|marketing & communications|web & ui | deepseek-v4-pro: d=None / brand identity|marketing & communications|semiotics & communication | kimi: d=3 / brand identity|marketing & communications
- **owner depth** 4 (conf 2) | coder spread 1 | domain union: brand identity|marketing & communications|semiotics & communication|web & ui
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R037 - Style Precedence and Override Behavior
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design systems|engineering practice | claude-sonnet-5: d=4 / digital product|design systems|engineering practice | deepseek-v4-pro: d=None / design systems|editorial & advertising|graphic design | kimi: d=4 / design systems|graphic design
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: design systems|digital product|editorial & advertising|engineering practice|graphic design
- **RECOMMEND** `domain=design systems as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with design systems - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R038 - Multiple Imputation Procedure
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|research & methodology | claude-sonnet-5: d=3 / research & methodology|data visualization|science & research | deepseek-v4-pro: d=None / research & methodology|science & research | kimi: d=4 / research & methodology
- **owner depth** 3 (conf 3) | coder spread 1 | domain union: data visualization|research & methodology|science & research
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R039 - Identity As Social Positioning and Lifestyle Signifiers
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|marketing & communications|social sciences | claude-sonnet-5: d=3 / social sciences|marketing & communications|semiotics & communication | deepseek-v4-pro: d=None / marketing & communications|semiotics & communication|social sciences | kimi: d=2 / social sciences|marketing & communications
- **owner depth** 2 (conf 2) | coder spread 1 | domain union: arts & culture|marketing & communications|semiotics & communication|social sciences
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R040 - Commercial Advertising Souring of Artistic Vision
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|marketing & communications | claude-sonnet-5: d=4 / arts & culture|editorial & advertising | deepseek-v4-pro: d=None / arts & culture|editorial & advertising|marketing & communications | kimi: d=4 / arts & culture|editorial & advertising
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|editorial & advertising|marketing & communications
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R041 - Consumer Anticipation of Objections
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / marketing & communications|product design|user experience | claude-sonnet-5: d=3 / marketing & communications|product design|business development | deepseek-v4-pro: d=None / business development|design strategy|marketing & communications|product design|user experience | kimi: d=3 / marketing & communications|product design
- **owner depth** 2 (conf 1) | coder spread 0 | domain union: business development|design strategy|marketing & communications|product design|user experience
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R042 - Destination-control Elevator Interaction Pattern
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design systems|digital product|user experience | claude-sonnet-5: d=4 / user experience|engineering & infrastructure|product design | deepseek-v4-pro: d=None / engineering & infrastructure|industrial design|product design|systems & frameworks|user experience | kimi: d=3 / user experience|product design
- **owner depth** 3 (conf 1) | coder spread 1 | domain union: design systems|digital product|engineering & infrastructure|industrial design|product design|systems & frameworks|user experience
- **RECOMMEND** `domain=user experience as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with user experience - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R044 - Cyclical Design Lifecycle
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|industrial design|product design | claude-sonnet-5: d=3 / industrial design|environmental design|product design | deepseek-v4-pro: d=None / design strategy|industrial design|product design|systems & frameworks | kimi: d=3 / industrial design|environmental design
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: design strategy|environmental design|industrial design|product design|systems & frameworks
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R045 - Wpi Consumer Value Proposition Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|business development|marketing & communications | claude-sonnet-5: d=3 / marketing & communications|business development|brand identity | deepseek-v4-pro: d=None / brand identity|business development|marketing & communications|product design | kimi: d=4 / marketing & communications|business development
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: brand identity|business development|marketing & communications|product design
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R046 - Bitcoin Mining As Digital Ownership Model
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / engineering practice|finance & investment | claude-sonnet-5: d=4 / finance & investment|code & computation | deepseek-v4-pro: d=None / engineering & infrastructure|finance & investment|legal & public policy|systems & frameworks | kimi: d=4 / finance & investment|code & computation
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: code & computation|engineering & infrastructure|engineering practice|finance & investment|legal & public policy|systems & frameworks
- **RECOMMEND** `domain=finance & investment as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with finance & investment - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R047 - Emotional Transaction Design
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / marketing & communications|organizational behavior|user experience | claude-sonnet-5: d=3 / user experience|marketing & communications|organizational behavior | deepseek-v4-pro: d=None / design strategy|marketing & communications|organizational behavior|user experience | kimi: d=2 / user experience|marketing & communications
- **owner depth** 2 (conf 2) | coder spread 1 | domain union: design strategy|marketing & communications|organizational behavior|user experience
- **RECOMMEND** `domain=user experience as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with user experience - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R049 - Fermi Estimation Method
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|research & methodology | claude-sonnet-5: d=2 / research & methodology|personal productivity|science & research | deepseek-v4-pro: d=None / engineering practice|finance & investment|project management|research & methodology|science & research | kimi: d=1 / research & methodology|systems & frameworks
- **owner depth** 1 (conf 2) | coder spread 1 | domain union: design strategy|engineering practice|finance & investment|personal productivity|project management|research & methodology|science & research|systems & frameworks
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D1.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R050 - Methodological Accountability
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / research & methodology | claude-sonnet-5: d=3 / research & methodology|education | deepseek-v4-pro: d=None / research & methodology | kimi: d=3 / research & methodology
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: education|research & methodology
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R051 - Central Emptiness in Urban Design
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|environmental design|urban planning | claude-sonnet-5: d=4 / urban planning|environmental design|semiotics & communication | deepseek-v4-pro: d=None / environmental design|systems & frameworks|urban planning | kimi: d=3 / urban planning|environmental design
- **owner depth** 3 (conf 3) | coder spread 1 | domain union: design strategy|environmental design|semiotics & communication|systems & frameworks|urban planning
- **RECOMMEND** `domain=urban planning as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with urban planning - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R052 - Interior Design Fixture Selection Challenge
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|product design | claude-sonnet-5: d=3 / industrial design|product design | deepseek-v4-pro: d=None / design strategy|environmental design|product design | kimi: d=3 / industrial design|product design
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: design strategy|environmental design|industrial design|product design
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R053 - Self-referential Incompleteness
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|systems & frameworks | claude-sonnet-5: d=1 / systems & frameworks|code & computation | deepseek-v4-pro: d=None / systems & frameworks | kimi: d=1 / systems & frameworks|code & computation
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: code & computation|systems & frameworks
- **RECOMMEND** `domain=systems & frameworks as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with systems & frameworks - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R054 - Shap Explainability Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|code & computation | claude-sonnet-5: d=4 / ai & agents|code & computation|data visualization | deepseek-v4-pro: d=None / ai & agents|code & computation|research & methodology | kimi: d=4 / ai & agents|code & computation
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: ai & agents|code & computation|data visualization|research & methodology
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R055 - Demand-side Sales Pattern
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business development|marketing & communications | claude-sonnet-5: d=3 / marketing & communications|business development | deepseek-v4-pro: d=None / business development|marketing & communications | kimi: d=3 / marketing & communications|business development
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|marketing & communications
- **RECOMMEND** `domain=business development as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `PRIMARY_DOMAIN_DIFFERS`

### R056 - Quiz Generation with Llm Integration
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|education | claude-sonnet-5: d=4 / ai & agents|education|code & computation | deepseek-v4-pro: d=None / ai & agents|education | kimi: d=4 / education|ai & agents
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|education
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R057 - Annual Percentage Rate Standardization
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / finance & investment|legal & public policy | claude-sonnet-5: d=4 / finance & investment|legal & public policy | deepseek-v4-pro: d=None / finance & investment|legal & public policy | kimi: d=3 / finance & investment|legal & public policy
- **owner depth** 3 (conf 3) | coder spread 1 | domain union: finance & investment|legal & public policy
- **RECOMMEND** `domain=finance & investment as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with finance & investment - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R058 - Illustration As Propaganda Tool
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / illustration|marketing & communications|semiotics & communication | claude-sonnet-5: d=2 / illustration|marketing & communications|editorial & advertising | deepseek-v4-pro: d=None / editorial & advertising|illustration|semiotics & communication | kimi: d=2 / illustration|editorial & advertising
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: editorial & advertising|illustration|marketing & communications|semiotics & communication
- **RECOMMEND** `domain=illustration as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with illustration - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R059 - First Course Development Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|education|entrepreneurship | claude-sonnet-5: d=3 / education|entrepreneurship|business development | deepseek-v4-pro: d=None / business development|education|entrepreneurship|marketing & communications|product design | kimi: d=3 / education|entrepreneurship
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|design strategy|education|entrepreneurship|marketing & communications|product design
- **RECOMMEND** `domain=education as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with education - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R060 - Aiga Transportation Symbol System Development
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design systems|graphic design|semiotics & communication | claude-sonnet-5: d=4 / graphic design|semiotics & communication|urban planning | deepseek-v4-pro: d=None / environmental design|graphic design|semiotics & communication | kimi: d=4 / graphic design|design systems
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: design systems|environmental design|graphic design|semiotics & communication|urban planning
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R061 - Core Focus As Organizational Discipline
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|leadership|organizational behavior | claude-sonnet-5: d=3 / leadership|organizational behavior | deepseek-v4-pro: d=None / business operations|leadership|organizational behavior | kimi: d=3 / leadership|organizational behavior
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business operations|design strategy|leadership|organizational behavior
- **RECOMMEND** `domain=leadership as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with leadership - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R063 - Textbook Representation and State of Exception Legitimation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|education|social sciences | claude-sonnet-5: d=4 / education|legal & public policy|media & entertainment | deepseek-v4-pro: d=None / education|legal & public policy|semiotics & communication|social sciences | kimi: d=4 / education|legal & public policy
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: arts & culture|education|legal & public policy|media & entertainment|semiotics & communication|social sciences
- **RECOMMEND** `domain=education as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with education - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R064 - Optical Alignment in Typography
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design systems|graphic design|web & ui | claude-sonnet-5: d=3 / graphic design|design systems | deepseek-v4-pro: d=None / brand identity|design systems|editorial & advertising|graphic design|web & ui | kimi: d=3 / graphic design
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: brand identity|design systems|editorial & advertising|graphic design|web & ui
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R065 - Media Construction of Crime Waves
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / media & entertainment|social sciences | claude-sonnet-5: d=3 / media & entertainment|social sciences|legal & public policy | deepseek-v4-pro: d=None / media & entertainment|semiotics & communication|social sciences | kimi: d=3 / media & entertainment|social sciences
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: legal & public policy|media & entertainment|semiotics & communication|social sciences
- **RECOMMEND** `domain=media & entertainment as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with media & entertainment - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R068 - Imagination and the Image
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|design strategy | claude-sonnet-5: d=3 / arts & culture|design strategy|editorial & advertising | deepseek-v4-pro: d=None / design strategy|graphic design|product design|semiotics & communication | kimi: d=3 / graphic design|design strategy
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: arts & culture|design strategy|editorial & advertising|graphic design|product design|semiotics & communication
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R069 - Falsifiable Variable Measurement
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / research & methodology|science & research | claude-sonnet-5: d=2 / research & methodology|science & research | deepseek-v4-pro: d=None / research & methodology | kimi: d=2 / research & methodology|science & research
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: research & methodology|science & research
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R070 - Iterative Design Validation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|project management|user experience | claude-sonnet-5: d=3 / design strategy|project management|user experience | deepseek-v4-pro: d=None / design strategy|product design|project management|user experience | kimi: d=2 / design strategy|user experience
- **owner depth** 2 (conf 2) | coder spread 1 | domain union: design strategy|product design|project management|user experience
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R071 - Lean Startup Experimentation Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business development|design strategy|entrepreneurship | claude-sonnet-5: d=3 / entrepreneurship|business development | deepseek-v4-pro: d=None / business development|entrepreneurship|product design | kimi: d=3 / entrepreneurship|business development
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|design strategy|entrepreneurship|product design
- **RECOMMEND** `domain=business development as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R072 - Park24 Nondisruptive Market Creation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business development|design strategy|urban planning | claude-sonnet-5: d=4 / business development|urban planning|entrepreneurship | deepseek-v4-pro: d=None / business development|entrepreneurship|urban planning | kimi: d=3 / business development|entrepreneurship
- **owner depth** 4 (conf 3) | coder spread 1 | domain union: business development|design strategy|entrepreneurship|urban planning
- **RECOMMEND** `domain=business development as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R073 - Evolution of Language Through Mental Models
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|social sciences | claude-sonnet-5: d=4 / social sciences|education | deepseek-v4-pro: d=None / science & research|semiotics & communication|social sciences | kimi: d=4 / social sciences|semiotics & communication
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|education|science & research|semiotics & communication|social sciences
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R076 - Linguistic Fetish in Visual Communication
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|marketing & communications|semiotics & communication | claude-sonnet-5: d=3 / marketing & communications|semiotics & communication|brand identity | deepseek-v4-pro: d=None / brand identity|editorial & advertising|marketing & communications|semiotics & communication | kimi: d=3 / semiotics & communication|marketing & communications
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: brand identity|editorial & advertising|marketing & communications|semiotics & communication
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R077 - Symbolic Meaning Through Consumption
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|social sciences | claude-sonnet-5: d=2 / social sciences|marketing & communications|arts & culture | deepseek-v4-pro: d=None / semiotics & communication|social sciences | kimi: d=2 / social sciences|marketing & communications
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: arts & culture|marketing & communications|semiotics & communication|social sciences
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R078 - Parameterized Design Generation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational art|creative technology | claude-sonnet-5: d=2 / computational art|design systems|creative technology | deepseek-v4-pro: d=None / code & computation|computational art|creative technology|design systems|product design | kimi: d=2 / computational art|creative technology
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: code & computation|computational art|creative technology|design systems|product design
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R079 - Bar-hillel Paradox
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / semiotics & communication | claude-sonnet-5: d=3 / semiotics & communication|research & methodology | deepseek-v4-pro: d=None / semiotics & communication | kimi: d=3 / semiotics & communication|social sciences
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: research & methodology|semiotics & communication|social sciences
- **RECOMMEND** `domain=semiotics & communication as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with semiotics & communication - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R081 - Shift From Trend-chasing to Intentional Consumption
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / marketing & communications|social sciences | claude-sonnet-5: d=4 / marketing & communications|social sciences | deepseek-v4-pro: d=None / marketing & communications|social sciences | kimi: d=3 / marketing & communications|social sciences
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: marketing & communications|social sciences
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R082 - Historical Data Sources for Manufacturing and Economic Analysis
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|research & methodology | claude-sonnet-5: d=4 / research & methodology|legal & public policy | deepseek-v4-pro: d=None / research & methodology|social sciences | kimi: d=3 / research & methodology
- **owner depth** 3 (conf 1) | coder spread 1 | domain union: business operations|legal & public policy|research & methodology|social sciences
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R083 - Self-herding Behavior
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / marketing & communications|user experience | claude-sonnet-5: d=2 / social sciences|marketing & communications|business development | deepseek-v4-pro: d=None / marketing & communications|social sciences|user experience | kimi: d=2 / social sciences|marketing & communications
- **owner depth** 2 (conf 1) | coder spread 0 | domain union: business development|marketing & communications|social sciences|user experience
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R084 - Data Visualization Research Lab Leadership
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|leadership|research & methodology | claude-sonnet-5: d=4 / data visualization|research & methodology | deepseek-v4-pro: d=None / data visualization|leadership|research & methodology | kimi: d=3 / data visualization|science & research
- **owner depth** 3 (conf 1) | coder spread 1 | domain union: data visualization|leadership|research & methodology|science & research
- **RECOMMEND** `domain=data visualization as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with data visualization - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R085 - Discursive Strategy Abstraction
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|social sciences | claude-sonnet-5: d=3 / social sciences|education|arts & culture | deepseek-v4-pro: d=None / arts & culture|research & methodology|semiotics & communication|social sciences | kimi: d=3 / social sciences|education
- **owner depth** 1 (conf 1) | coder spread 0 | domain union: arts & culture|education|research & methodology|semiotics & communication|social sciences
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R086 - Commitment and Consistency Principle (2)
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / digital product|marketing & communications|user experience | claude-sonnet-5: d=2 / marketing & communications|social sciences|leadership | deepseek-v4-pro: d=None / marketing & communications|product design|user experience | kimi: d=2 / social sciences|marketing & communications
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: digital product|leadership|marketing & communications|product design|social sciences|user experience
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R087 - In-group Identity and Social Bonding
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / organizational behavior|social sciences | claude-sonnet-5: d=2 / social sciences|organizational behavior | deepseek-v4-pro: d=None / marketing & communications|organizational behavior|social sciences | kimi: d=2 / social sciences|organizational behavior
- **owner depth** 1 (conf 1) | coder spread 0 | domain union: marketing & communications|organizational behavior|social sciences
- **RECOMMEND** `domain=social sciences as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with social sciences - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R088 - Gradio Web Interface for Ml Models
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|code & computation|web & ui | claude-sonnet-5: d=4 / ai & agents|code & computation|web & ui | deepseek-v4-pro: d=None / ai & agents|code & computation|engineering practice|web & ui | kimi: d=4 / code & computation|ai & agents
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|engineering practice|web & ui
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R091 - Autopoesis in Design Education
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|education | claude-sonnet-5: d=3 / education|design strategy|arts & culture | deepseek-v4-pro: d=None / arts & culture|education|systems & frameworks | kimi: d=3 / education|graphic design
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: arts & culture|design strategy|education|graphic design|systems & frameworks
- **RECOMMEND** `domain=education as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with education - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R094 - Progressive Feature Introduction
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / digital product|user experience|web & ui | claude-sonnet-5: d=3 / user experience|web & ui|product design | deepseek-v4-pro: d=None / design strategy|digital product|user experience|web & ui | kimi: d=3 / user experience|digital product
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: design strategy|digital product|product design|user experience|web & ui
- **RECOMMEND** `domain=user experience as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with user experience - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R095 - Sensory Engagement As Quality Signal
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / marketing & communications|product design|user experience | claude-sonnet-5: d=3 / marketing & communications|product design|brand identity | deepseek-v4-pro: d=None / industrial design|marketing & communications|product design | kimi: d=2 / marketing & communications|product design
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: brand identity|industrial design|marketing & communications|product design|user experience
- **RECOMMEND** `domain=marketing & communications as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with marketing & communications - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R096 - Transportation and Setup Costs in Construction Projects
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|engineering & infrastructure | claude-sonnet-5: d=3 / engineering & infrastructure|finance & investment|business operations | deepseek-v4-pro: d=None / business operations|engineering & infrastructure|project management | kimi: d=3 / engineering & infrastructure|business operations
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: business operations|engineering & infrastructure|finance & investment|project management
- **RECOMMEND** `domain=business operations as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R098 - Aesthetic Refinement Through Iteration
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|design strategy | claude-sonnet-5: d=3 / design strategy|graphic design|brand identity | deepseek-v4-pro: d=None / brand identity|design strategy|design systems|graphic design|product design | kimi: d=2 / design strategy|graphic design
- **owner depth** 2 (conf 3) | coder spread 1 | domain union: arts & culture|brand identity|design strategy|design systems|graphic design|product design
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R099 - Charismatic Brand Discipline
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|design strategy | claude-sonnet-5: d=3 / brand identity|marketing & communications | deepseek-v4-pro: d=None / brand identity|design strategy|marketing & communications | kimi: d=3 / brand identity|marketing & communications
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: brand identity|design strategy|marketing & communications
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R100 - Network Marketing Business Model
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|entrepreneurship|marketing & communications | claude-sonnet-5: d=4 / business development|entrepreneurship|finance & investment | deepseek-v4-pro: d=None / business development|entrepreneurship|marketing & communications|organizational behavior | kimi: d=3 / business development|entrepreneurship
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: business development|business operations|entrepreneurship|finance & investment|marketing & communications|organizational behavior
- **RECOMMEND** `domain=business development as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R102 - Social Entrepreneur's Playbook
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|entrepreneurship|social sciences | claude-sonnet-5: d=3 / entrepreneurship|organizational behavior | deepseek-v4-pro: d=None / business development|entrepreneurship|leadership|project management | kimi: d=3 / entrepreneurship|business development
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|design strategy|entrepreneurship|leadership|organizational behavior|project management|social sciences
- **RECOMMEND** `domain=entrepreneurship as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with entrepreneurship - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R104 - Strategic Information Gathering
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|research & methodology | claude-sonnet-5: d=2 / research & methodology|business operations|leadership | deepseek-v4-pro: d=None / research & methodology|science & research | kimi: d=2 / research & methodology|systems & frameworks
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business operations|design strategy|leadership|research & methodology|science & research|systems & frameworks
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R106 - The Invisible Art of Film Editing
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / media & entertainment | claude-sonnet-5: d=4 / media & entertainment | deepseek-v4-pro: d=None / media & entertainment | kimi: d=4 / media & entertainment
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: media & entertainment
- **RECOMMEND** `domain=media & entertainment as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with media & entertainment - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `OWNER_coder_majority_DIFFERS`

### R107 - Lived Experience Focus
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / research & methodology | claude-sonnet-5: d=3 / research & methodology|social sciences | deepseek-v4-pro: d=None / research & methodology | kimi: d=2 / research & methodology|social sciences
- **owner depth** 2 (conf 2) | coder spread 1 | domain union: research & methodology|social sciences
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R108 - Typography in Brand Positioning and Magazine Design
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / brand identity|editorial & advertising|graphic design | claude-sonnet-5: d=3 / graphic design|brand identity|editorial & advertising | deepseek-v4-pro: d=None / brand identity|editorial & advertising|graphic design|web & ui | kimi: d=3 / graphic design|brand identity
- **owner depth** 2 (conf 3) | coder spread 0 | domain union: brand identity|editorial & advertising|graphic design|web & ui
- **RECOMMEND** `domain=brand identity as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with brand identity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R109 - Project Completion Bias
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / personal productivity|project management | claude-sonnet-5: d=2 / personal productivity|organizational behavior | deepseek-v4-pro: d=None / digital product|personal productivity|product design|project management|user experience | kimi: d=2 / personal productivity|organizational behavior
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: digital product|organizational behavior|personal productivity|product design|project management|user experience
- **RECOMMEND** `domain=personal productivity as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with personal productivity - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R110 - Federated Information Architecture
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design systems|information architecture|web & ui | claude-sonnet-5: d=3 / information architecture|systems & frameworks|organizational behavior | deepseek-v4-pro: d=None / design systems|information architecture|systems & frameworks|web & ui | kimi: d=3 / information architecture|systems & frameworks
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: design systems|information architecture|organizational behavior|systems & frameworks|web & ui
- **RECOMMEND** `domain=design systems as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with design systems - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R111 - Pmt Camera Typography Manipulation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|graphic design|illustration | claude-sonnet-5: d=4 / graphic design|illustration|creative technology | deepseek-v4-pro: d=None / graphic design | kimi: d=4 / graphic design|illustration
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: arts & culture|creative technology|graphic design|illustration
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R112 - Content Analysis Approaches in Visual Research
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|media & entertainment|research & methodology | claude-sonnet-5: d=3 / research & methodology|media & entertainment | deepseek-v4-pro: d=None / research & methodology | kimi: d=2 / research & methodology|media & entertainment
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: arts & culture|media & entertainment|research & methodology
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R114 - Measurable Outcome Focus
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|design strategy | claude-sonnet-5: d=2 / personal productivity|business operations|leadership | deepseek-v4-pro: d=None / business operations|personal productivity|project management | kimi: d=2 / personal productivity|business operations
- **owner depth** 2 (conf 3) | coder spread 0 | domain union: business operations|design strategy|leadership|personal productivity|project management
- **RECOMMEND** `domain=business operations as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R115 - Heuristic Reasoning in Problem Solving
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / research & methodology | claude-sonnet-5: d=3 / research & methodology|education|science & research | deepseek-v4-pro: d=None / education|research & methodology|science & research | kimi: d=2 / research & methodology|education
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: education|research & methodology|science & research
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R116 - Ai Model Deployment Risk
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|engineering practice|organizational behavior | claude-sonnet-5: d=3 / ai & agents|organizational behavior|engineering practice | deepseek-v4-pro: d=None / ai & agents|business operations|engineering practice|organizational behavior | kimi: d=3 / ai & agents|organizational behavior
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: ai & agents|business operations|engineering practice|organizational behavior
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R117 - Sustained Purpose Over Temporary Gratification
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / finance & investment|personal productivity | claude-sonnet-5: d=2 / personal productivity|finance & investment|leadership | deepseek-v4-pro: d=None / finance & investment|health & wellness|personal productivity | kimi: d=2 / personal productivity|finance & investment
- **owner depth** 2 (conf 2) | coder spread 0 | domain union: finance & investment|health & wellness|leadership|personal productivity
- **RECOMMEND** `domain=finance & investment as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with finance & investment - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R118 - Pass@k Evaluation Method
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|code & computation | claude-sonnet-5: d=4 / ai & agents|code & computation | deepseek-v4-pro: d=None / ai & agents|engineering practice|research & methodology | kimi: d=4 / ai & agents|code & computation
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|engineering practice|research & methodology
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R119 - Strategic Human Resource Planning for Social Enterprises
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|leadership|organizational behavior | claude-sonnet-5: d=4 / organizational behavior|entrepreneurship|leadership | deepseek-v4-pro: d=None / business operations|entrepreneurship|organizational behavior | kimi: d=3 / organizational behavior|entrepreneurship
- **owner depth** 3 (conf 3) | coder spread 1 | domain union: business operations|entrepreneurship|leadership|organizational behavior
- **RECOMMEND** `domain=business operations as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R120 - Nonlinear Magnification Fields
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational art|data visualization | claude-sonnet-5: d=3 / data visualization|code & computation | deepseek-v4-pro: d=None / data visualization | kimi: d=4 / data visualization|computational science & physics
- **owner depth** 4 (conf 2) | coder spread 1 | domain union: code & computation|computational art|computational science & physics|data visualization
- **RECOMMEND** `domain=data visualization as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with data visualization - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R121 - Consumers Hero Refurbishment Strategy
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|marketing & communications | claude-sonnet-5: d=3 / business operations|marketing & communications | deepseek-v4-pro: d=None / business operations|finance & investment|legal & public policy | kimi: d=3 / business operations|marketing & communications
- **owner depth** 4 (conf 2) | coder spread 0 | domain union: business operations|finance & investment|legal & public policy|marketing & communications
- **RECOMMEND** `domain=business operations as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with business operations - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R122 - Visual Hierarchy Through Contrast (2)
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / graphic design|user experience|web & ui | claude-sonnet-5: d=3 / graphic design|design systems | deepseek-v4-pro: d=None / graphic design | kimi: d=2 / graphic design|user experience
- **owner depth** 2 (conf 3) | coder spread 1 | domain union: design systems|graphic design|user experience|web & ui
- **RECOMMEND** `domain=graphic design as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with graphic design - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D2.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R123 - Superquadric Parameterization in 3d Space
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational art | claude-sonnet-5: d=4 / computational art|code & computation|data visualization | deepseek-v4-pro: d=None / code & computation|computational art | kimi: d=4 / computational art|code & computation
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: code & computation|computational art|data visualization
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R124 - Foundation Model Integration Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|engineering practice|systems & frameworks | claude-sonnet-5: d=3 / ai & agents|engineering practice|digital product | deepseek-v4-pro: d=None / ai & agents|code & computation|engineering practice|systems & frameworks | kimi: d=3 / ai & agents|code & computation
- **owner depth** 3 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|digital product|engineering practice|systems & frameworks
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R125 - Dell Computer's Direct-sale Business Model
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business development|business operations|design strategy | claude-sonnet-5: d=4 / business development|marketing & communications | deepseek-v4-pro: d=None / business development|business operations|entrepreneurship | kimi: d=3 / business development|marketing & communications
- **owner depth** 3 (conf 3) | coder spread 1 | domain union: business development|business operations|design strategy|entrepreneurship|marketing & communications
- **RECOMMEND** `domain=business development as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with business development - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R127 - Guild of Handicraft Educational Model
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / arts & culture|design strategy|education | claude-sonnet-5: d=4 / education|industrial design|arts & culture | deepseek-v4-pro: d=None / arts & culture|education | kimi: d=4 / education|arts & culture
- **owner depth** 4 (conf 1) | coder spread 0 | domain union: arts & culture|design strategy|education|industrial design
- **RECOMMEND** `domain=arts & culture as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with arts & culture - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R129 - Use of Proxies and Analogues in Market Sizing
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / business operations|research & methodology | claude-sonnet-5: d=3 / research & methodology|finance & investment|business development | deepseek-v4-pro: d=None / business development|finance & investment|marketing & communications|research & methodology | kimi: d=3 / research & methodology|business development
- **owner depth** 3 (conf 2) | coder spread 0 | domain union: business development|business operations|finance & investment|marketing & communications|research & methodology
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R130 - Typographic Principles of William Morris
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / editorial & advertising|graphic design | claude-sonnet-5: d=3 / graphic design|editorial & advertising | deepseek-v4-pro: d=None / editorial & advertising|graphic design | kimi: d=4 / graphic design|editorial & advertising
- **owner depth** 3 (conf 3) | coder spread 1 | domain union: editorial & advertising|graphic design
- **RECOMMEND** `domain=editorial & advertising as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 2/4 coders LEAD with editorial & advertising - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D3.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS`

### R132 - Monte Carlo PDE Solution Method
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / code & computation|computational science & physics | claude-sonnet-5: d=4 / computational science & physics|code & computation | deepseek-v4-pro: d=None / code & computation|computational science & physics | kimi: d=4 / computational science & physics|code & computation
- **owner depth** 4 (conf 1) | coder spread 0 | domain union: code & computation|computational science & physics
- **RECOMMEND** `domain=code & computation as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with code & computation - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `PRIMARY_DOMAIN_DIFFERS`

### R134 - Holistic Interpretation Problem in Index-aware Retrieval
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|code & computation | claude-sonnet-5: d=3 / ai & agents|information architecture|code & computation | deepseek-v4-pro: d=None / ai & agents|information architecture|systems & frameworks | kimi: d=3 / ai & agents|information architecture
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|code & computation|information architecture|systems & frameworks
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R135 - Ase  Design Problem Solving Model
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design strategy|user experience | claude-sonnet-5: d=3 / design strategy|product design | deepseek-v4-pro: d=None / design strategy|product design|systems & frameworks | kimi: d=3 / design strategy|systems & frameworks
- **owner depth** 2 (conf 3) | coder spread 0 | domain union: design strategy|product design|systems & frameworks|user experience
- **RECOMMEND** `domain=design strategy as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with design strategy - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R136 - Chatgpt Prompt Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / ai & agents|creative technology | claude-sonnet-5: d=4 / ai & agents|personal productivity | deepseek-v4-pro: d=None / ai & agents|digital product|systems & frameworks|user experience | kimi: d=4 / ai & agents|personal productivity
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: ai & agents|creative technology|digital product|personal productivity|systems & frameworks|user experience
- **RECOMMEND** `domain=ai & agents as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with ai & agents - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R137 - Desire-friction Conversion Formula
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / digital product|marketing & communications|user experience | claude-sonnet-5: d=3 / user experience|marketing & communications|digital product | deepseek-v4-pro: d=None / business development|digital product|marketing & communications|user experience | kimi: d=3 / marketing & communications|user experience
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: business development|digital product|marketing & communications|user experience
- **RECOMMEND** `domain=OWNER_ONLY; depth=no dispute`
- why: no label is LED by half the coders (best primary share 0.25 of 4, best set-membership share 1.00) - the PRIMARY label is yours to name; the coder sets stay in this row as provenance
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R138 - Hjelmslev's Trichotomy and Linguistic Theory
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / semiotics & communication | claude-sonnet-5: d=4 / semiotics & communication|education | deepseek-v4-pro: d=None / semiotics & communication | kimi: d=4 / semiotics & communication|social sciences
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: education|semiotics & communication|social sciences
- **RECOMMEND** `domain=semiotics & communication as PRIMARY; depth=no dispute`
- why: 4/4 coders LEAD with semiotics & communication - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS`

### R139 - Learning Through Failure Process
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / education | claude-sonnet-5: d=2 / education|personal productivity | deepseek-v4-pro: d=None / education|personal productivity | kimi: d=1 / education|personal productivity
- **owner depth** 1 (conf 2) | coder spread 1 | domain union: education|personal productivity
- **RECOMMEND** `domain=education as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 4/4 coders LEAD with education - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D1.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

### R140 - Digital Culture Integration in Graphic Design
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / creative technology|digital product|graphic design | claude-sonnet-5: d=3 / graphic design|web & ui|digital product | deepseek-v4-pro: d=None / creative technology|digital product|graphic design|user experience | kimi: d=3 / graphic design|digital product
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: creative technology|digital product|graphic design|user experience|web & ui
- **RECOMMEND** `domain=creative technology as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with creative technology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;OWNER_coder_majority_DIFFERS`

### R142 - Global Village Conceptual Framework
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / media & entertainment|semiotics & communication | claude-sonnet-5: d=3 / media & entertainment|semiotics & communication | deepseek-v4-pro: d=None / media & entertainment|semiotics & communication|social sciences|systems & frameworks | kimi: d=3 / semiotics & communication|media & entertainment
- **owner depth** 3 (conf 1) | coder spread 0 | domain union: media & entertainment|semiotics & communication|social sciences|systems & frameworks
- **RECOMMEND** `domain=media & entertainment as PRIMARY; depth=no dispute`
- why: 3/4 coders LEAD with media & entertainment - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R143 - Figma Hamburger Icon Creation
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / design systems|user experience|web & ui | claude-sonnet-5: d=4 / web & ui|user experience|graphic design | deepseek-v4-pro: d=None / design systems|graphic design|web & ui | kimi: d=4 / web & ui|graphic design
- **owner depth** 4 (conf 3) | coder spread 0 | domain union: design systems|graphic design|user experience|web & ui
- **RECOMMEND** `domain=design systems as PRIMARY; depth=no dispute`
- why: 2/4 coders LEAD with design systems - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets)
- **you must answer: domain**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS`

### R147 - Randomness in Data Measurement
- **coders** - Qwen3.8-27B-MLX-4bit: d=None / data visualization|research & methodology | claude-sonnet-5: d=1 / research & methodology|science & research | deepseek-v4-pro: d=None / research & methodology|science & research | kimi: d=2 / research & methodology
- **owner depth** 3 (conf 2) | coder spread 1 | domain union: data visualization|research & methodology|science & research
- **RECOMMEND** `domain=research & methodology as PRIMARY; depth=OWNER_RULING_NEAR`
- why: 3/4 coders LEAD with research & methodology - confirm it, or replace it if it is wrong (it is also shared by 1.00 of the coder sets) | coders differ by ONE class (mean D1.5) - this is the D2/D3 boundary; a ruling here is what teaches the rubric
- **you must answer: domain;depth**
- flags: `DOMAIN_DIFFERS;PRIMARY_DOMAIN_DIFFERS;DEPTH_DIFFERS;OWNER_coder_majority_DIFFERS`

