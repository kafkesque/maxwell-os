# RULER — INVERTED KEY, all axes — 2026-09-20

Reference = blind **human** label (ground truth). Under test = **stored** free-generated label. Reported = stored-label ERROR RATE (1 − agreement).
This is the honest replacement for the corrupt ruler_measurement `0.740 / 0.506 / 0.831` figures. (D-275a, BUG-303)

## content_type (CT)

### Stored-label error rate

| scope | error rate | 95% Wilson | stored agrees |
|---|---|---|---|
| stratum all | **0.353** | [0.281, 0.433] | 97/150 |
| stratum A | **0.290** | [0.210, 0.385] | 71/100 |
| stratum B | **0.480** | [0.348, 0.615] | 26/50 |

- scored: 150 | abstained: {} | typos/dups resolved on human side: {'exact': 150}

### Per-class stored reliability (human class = truth)

| human class | n | stored agrees | stored error rate |
|---|---|---|---|
| principle | 89 | 71 | 0.202 |
| quarantine | 18 | 1 | 0.944 |
| process_template | 16 | 6 | 0.625 |
| noise_drop | 13 | 9 | 0.308 |
| tool_instruction | 8 | 6 | 0.250 |
| process_instance | 3 | 2 | 0.333 |
| growth_edge | 3 | 2 | 0.333 |

### Confusion matrix (human rows x stored cols)

| human \ stored | principle | process_template | process_instance | tool_instruction | growth_edge | noise_drop | quarantine |
|---|---|---|---|---|---|---|---|--- |
| principle | 71 | 1 | 2 | 0 | 4 | 8 | 3 |
| process_template | 10 | 6 | 0 | 0 | 0 | 0 | 0 |
| process_instance | 0 | 0 | 2 | 0 | 0 | 1 | 0 |
| tool_instruction | 0 | 1 | 0 | 6 | 0 | 0 | 1 |
| growth_edge | 1 | 0 | 0 | 0 | 2 | 0 | 0 |
| noise_drop | 2 | 0 | 1 | 0 | 0 | 9 | 1 |
| quarantine | 9 | 1 | 3 | 0 | 0 | 4 | 1 |

## discipline (DISC)

### Stored-label error rate

| scope | error rate | 95% Wilson | stored agrees |
|---|---|---|---|
| stratum all | **0.474** | [0.386, 0.564] | 61/116 |
| stratum A | **0.487** | [0.381, 0.595] | 41/80 |
| stratum B | **0.444** | [0.295, 0.604] | 20/36 |

- scored: 116 | abstained: {'blank': 28, 'abstain-emerging': 6} | typos/dups resolved on human side: {'exact': 116, 'blank': 28, 'abstain-emerging': 6}

### Per-class stored reliability (human class = truth)

| human class | n | stored agrees | stored error rate |
|---|---|---|---|
| operations research | 8 | 5 | 0.375 |
| psychology | 7 | 5 | 0.286 |
| design thinking | 7 | 4 | 0.429 |
| research methodology | 6 | 5 | 0.167 |
| human-computer interaction | 5 | 5 | 0.000 |
| organizational theory | 5 | 3 | 0.400 |
| design psychology | 5 | 0 | 1.000 |
| cultural studies | 4 | 0 | 1.000 |
| risk management | 4 | 0 | 1.000 |
| behavioral economics | 4 | 1 | 0.750 |
| typography | 4 | 3 | 0.250 |
| decision making | 4 | 1 | 0.750 |
| semiotics | 3 | 2 | 0.333 |
| strategic thinking | 3 | 3 | 0.000 |
| creative process | 3 | 1 | 0.667 |
| information science | 3 | 3 | 0.000 |
| privacy & surveillance | 2 | 0 | 1.000 |
| political economy | 2 | 0 | 1.000 |
| computer graphics | 2 | 2 | 0.000 |
| generative design | 2 | 2 | 0.000 |
| information retrieval | 2 | 1 | 0.500 |
| engineering | 2 | 1 | 0.500 |
| visual perception | 2 | 0 | 1.000 |
| finance | 2 | 0 | 1.000 |
| software engineering | 2 | 2 | 0.000 |
| philosophy | 2 | 2 | 0.000 |
| artificial intelligence | 2 | 1 | 0.500 |
| media studies | 2 | 2 | 0.000 |
| cultural design | 2 | 0 | 1.000 |
| systems engineering | 1 | 1 | 0.000 |
| sociology | 1 | 0 | 1.000 |
| neuroscience | 1 | 1 | 0.000 |
| performing arts | 1 | 0 | 1.000 |
| cognitive science | 1 | 0 | 1.000 |
| linguistics | 1 | 1 | 0.000 |
| economics | 1 | 1 | 0.000 |
| communication theory | 1 | 0 | 1.000 |
| machine learning | 1 | 1 | 0.000 |
| computational geometry | 1 | 0 | 1.000 |
| generative ai | 1 | 1 | 0.000 |
| information security | 1 | 0 | 1.000 |
| computational physics & simulation | 1 | 1 | 0.000 |
| literary theory | 1 | 0 | 1.000 |
| color theory | 1 | 0 | 1.000 |

### Discipline disagreements (human → stored), non-zero

| human (truth) | stored (under test) | n |
|---|---|---|
| design psychology | emerging_dump | 3 |
| design thinking | software engineering | 2 |
| privacy & surveillance | law | 1 |
| cultural studies | communication theory | 1 |
| political economy | health & medicine | 1 |
| psychology | health & medicine | 1 |
| risk management | finance | 1 |
| information retrieval | artificial intelligence | 1 |
| risk management | creative process | 1 |
| semiotics | anthropology | 1 |
| operations research | strategic thinking | 1 |
| visual perception | color theory | 1 |
| finance | strategic thinking | 1 |
| organizational theory | strategic thinking | 1 |
| risk management | research methodology | 1 |
| sociology | psychology | 1 |
| operations research | emerging_dump | 1 |
| creative process | design thinking | 1 |
| engineering | design thinking | 1 |
| operations research | behavioral economics | 1 |
| finance | law | 1 |
| design psychology | communication theory | 1 |
| behavioral economics | neuroscience | 1 |
| performing arts | cultural design | 1 |
| creative process | cultural design | 1 |
| design thinking | emerging_dump | 1 |
| cognitive science | linguistics | 1 |
| design psychology | psychology | 1 |
| political economy | philosophy | 1 |
| cultural studies | semiotics | 1 |
| cultural studies | sociology | 1 |
| behavioral economics | emerging_dump | 1 |
| behavioral economics | psychology | 1 |
| cultural design | media studies | 1 |
| communication theory | behavioral economics | 1 |
| typography | emerging_dump | 1 |
| research methodology | motion & time | 1 |
| decision making | operations research | 1 |
| decision making | cognitive science | 1 |
| artificial intelligence | generative ai | 1 |
| psychology | behavioral economics | 1 |
| visual perception | emerging_dump | 1 |
| computational geometry | computer graphics | 1 |
| cultural design | design thinking | 1 |
| cultural studies | cultural design | 1 |
| decision making | strategic thinking | 1 |
| information security | privacy & surveillance | 1 |
| risk management | human-computer interaction | 1 |
| literary theory | linguistics | 1 |
| color theory | cultural studies | 1 |
| organizational theory | emerging_dump | 1 |
| privacy & surveillance | psychology | 1 |

### Discipline group-level near-miss (softer agreement)

- exact-canonical error: **0.430** (61/107)
- same-group error: **0.271** (78/107)
- → 29 stored labels land in a DIFFERENT discipline group than the human.

## extraction_type (FORM)

### Stored-label error rate

| scope | error rate | 95% Wilson | stored agrees |
|---|---|---|---|
| stratum all | **0.283** | [0.216, 0.361] | 104/145 |
| stratum A | **0.255** | [0.179, 0.349] | 73/98 |
| stratum B | **0.340** | [0.222, 0.483] | 31/47 |

- scored: 145 | abstained: {'blank': 5} | typos/dups resolved on human side: {'typo': 82, 'exact': 63, 'blank': 5}

### Per-class stored reliability (human class = truth)

| human class | n | stored agrees | stored error rate |
|---|---|---|---|
| normative_heuristic | 50 | 22 | 0.560 |
| descriptive_model | 41 | 38 | 0.073 |
| causal_mechanism | 40 | 31 | 0.225 |
| empirical_pattern | 14 | 13 | 0.071 |

### Confusion matrix (human rows x stored cols)

| human \ stored | causal_mechanism | descriptive_model | normative_heuristic | empirical_pattern |
|---|---|---|---|---|--- |
| causal_mechanism | 31 | 3 | 4 | 2 |
| descriptive_model | 1 | 38 | 1 | 1 |
| normative_heuristic | 16 | 6 | 22 | 6 |
| empirical_pattern | 0 | 1 | 0 | 13 |

## Notes

- `emerging` on the DISC human side is an ABSTENTION (reviewer could not map to the 61-menu).
- `emerging` on the DISC stored side is a DUMP = a stored-label FAILURE (alias map failed to land a slot).
- `irrelevant` is read as an abstention (a relevance judgement, not a FORM/discipline value) — evidence for the missing R4 relevance axis.
- Stratum A is the pre-agreed clean subset; stratum B is included here in the `all` row. D1/D2: stratum B is non-proportional and the sampling frame mixes PASS/QUARANTINE — treat `all` as the honest bound, `A` as the comparable-to-prior subset.

