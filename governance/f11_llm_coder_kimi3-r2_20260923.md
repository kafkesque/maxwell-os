# F-11 second coder — human↔LLM agreement (20260923)

> ADVISORY — this is a THIRD attested label set produced by a model. It measures RULER RELIABILITY (human↔LLM agreement). It is NOT human-blind, it is NOT independent human truth, and it CANNOT license adoption (D-300) or unfreeze config/eval_integrity.yaml (F-11).

First coder: single human, `governance/RULER_BLIND_SHEET_20260917.csv` (sha256 `383231921fffda2c`)  
Second coder: `kimi-k3` (tier `llm-attested`, temp 0.0)

| axis | n | agreement | kappa | LLM labels human never used | disagreements |
|---|---|---|---|---|---|
| content_type | 150 | 75.3% | 0.5543 | 0 | 37 |
| discipline | 122 | 41.8% | 0.4031 | 8 | 71 |
| extraction_type | 145 | 46.9% | 0.266 | 0 | 77 |

## Reading rule

* high kappa → the ruler is reliable on that axis; *low kappa* → read the disagreement list: if the
  same class pair recurs, the TAXONOMY is ambiguous there (a boundary decision in
  `config/boundary_discriminators.yaml`), not a model failure.
* a coder label that leaves the closed menu is an EMISSION error (the menu-compliance defect
  measured in D-327), never a wrong label.
