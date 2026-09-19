# RULER MEASUREMENT (2026-09-17)

The certified core: 150 blind-human-answered rows (100 proportional + 50 forced-minority).

Reviewer: human | sheet: RULER_BLIND_SHEET_20260917.csv

## How the written answers were read (C16: every non-exact resolution is listed)

The reviewer answered by NAME, not by index, and left some cells blank. Blank is a datum:
it means the reviewer, holding the full menu, could not assign any label at all.

| axis | exact | index | fuzzy (typo) | blank | unresolved | scored n |
|---|---|---|---|---|---|---|
| content_type | 150 | 0 | 0 | 0 | 0 | 150 |
| discipline | 119 | 0 | 0 | 29 | 2 | 119 |
| extraction_type | 97 | 0 | 31 | 22 | 0 | 128 |

Fuzzy (typo) resolutions, itemised so none is silent:

- extraction_type R001: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R049: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R064: 'escriptive model' -> 'descriptive_model'
- extraction_type R065: 'escriptive model' -> 'descriptive_model'
- extraction_type R066: 'escriptive model' -> 'descriptive_model'
- extraction_type R073: 'escriptive model' -> 'descriptive_model'
- extraction_type R086: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R099: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R102: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R104: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R105: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R108: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R111: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R113: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R114: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R115: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R116: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R117: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R118: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R119: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R123: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R125: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R127: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R129: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R131: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R134: 'normativ heuristic' -> 'normative_heuristic'
- extraction_type R136: 'escriptive_model' -> 'descriptive_model'
- extraction_type R137: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R139: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R143: 'casual mechanism' -> 'causal_mechanism'
- extraction_type R149: 'casual mechanism' -> 'causal_mechanism'

UNRESOLVED on discipline (answered but not a menu value): R027='leadership', R146='leadership'

The FLOOR columns are the accuracy of the STORED labels against the blind human answer on the
PROPORTIONAL stratum only, always beside the constant-answer baseline (BUG-269). An accuracy
without its baseline is not evidence. Rows the reviewer could not label are EXCLUDED from the
numerator and the denominator BOTH, and counted in `stratum A unanswered` below -- excluding
them from only one side is how a floor gets flattered.

| axis | stratum A n | unanswered | stored-label accuracy | 95% Wilson | baseline | lift | floor | verdict |
|---|---|---|---|---|---|---|---|---|
| content_type | 100 | 0 | 0.740 | [0.646, 0.816] | 0.750 (principle) | -0.010 | 0.60 | STOPPED: decisive |
| discipline | 83 | 17 | 0.506 | [0.401, 0.611] | 0.084 (operations research) | +0.422 | 0.60 | CONTINUE: inside the margin |
| extraction_type | 89 | 11 | 0.831 | [0.740, 0.895] | 0.360 (descriptive_model) | +0.472 | 0.60 | STOPPED: decisive |

`emerging` agreements are excluded and counted separately (it is the absence of a
taxonomy home, not a label): content_type=0, discipline=0, extraction_type=0

## Per-class precision (stratum B, forced-minority -- never a raw accuracy)

**content_type**
- growth_edge: 0/1
- noise_drop: 2/3
- principle: 10/34
- process_instance: 1/2
- process_template: 2/3
- quarantine: 1/4
- tool_instruction: 3/3
- F-14 test, stratum A: untraceable 34/51 vs traceable 40/49 (the stored labels are not better on the pre-repair pocket)

**discipline**
- artificial intelligence: 1/2
- computational physics & simulation: 1/1
- computer graphics: 1/1
- creative process: 0/1
- cultural design: 0/1
- cultural studies: 0/1
- decision making: 1/2
- design psychology: 0/2
- design thinking: 0/1
- economics: 1/1
- emerging: 0/2
- engineering: 1/1
- generative ai: 1/1
- generative design: 2/2
- human-computer interaction: 1/1
- information retrieval: 1/1
- information security: 0/1
- literary theory: 0/1
- media studies: 1/1
- operations research: 1/1
- performing arts: 0/1
- psychology: 1/1
- research methodology: 1/2
- risk management: 0/1
- semiotics: 1/2
- software engineering: 1/1
- strategic thinking: 1/1
- systems engineering: 1/1
- visual perception: 0/1
- F-14 test, stratum A: untraceable 24/39 vs traceable 18/44 (the stored labels are no worse on the pre-repair pocket)

**extraction_type**
- causal_mechanism: 11/15
- descriptive_model: 9/11
- empirical_pattern: 5/6
- normative_heuristic: 4/7
- F-14 test, stratum A: untraceable 37/43 vs traceable 37/46 (the stored labels are no worse on the pre-repair pocket)

