# F-11 second coder — human↔LLM agreement (20260923)

> ADVISORY — this is a THIRD attested label set produced by a model. It measures RULER RELIABILITY (human↔LLM agreement). It is NOT human-blind, it is NOT independent human truth, and it CANNOT license adoption (D-300) or unfreeze config/eval_integrity.yaml (F-11).

First coder: single human, `governance/RULER_BLIND_SHEET_20260917.csv` (sha256 `383231921fffda2c`)  
Second coder: `claude-sonnet-4.5` (tier `llm-attested`, temp 0.0)

| axis | n | agreement | kappa | LLM labels human never used | disagreements |
|---|---|---|---|---|---|
| content_type | 150 | 71.3% | 0.4867 | 0 | 43 |
| discipline | 122 | 45.9% | 0.4449 | 6 | 66 |
| extraction_type | 145 | 48.3% | 0.305 | 0 | 75 |

## Reading rule

* high kappa → the ruler is reliable on that axis; *low kappa* → read the disagreement list: if the
  same class pair recurs, the TAXONOMY is ambiguous there (a boundary decision in
  `config/boundary_discriminators.yaml`), not a model failure.
* a coder label that leaves the closed menu is an EMISSION error (the menu-compliance defect
  measured in D-327), never a wrong label.
