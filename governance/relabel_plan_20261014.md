# RELABEL PLAN — 2026-10-14

Rendered by `scripts/apply_relabel_rulings.py` (D-2977) from `config/relabel_rulings.yaml` + `canonical_relabel_review_20261014.csv`. **DO NOT hand-edit: re-run the applier.**

- units: 72 — **CONFIRM** 38 (192 rows), **CORRECT** 16 (98 rows), **ABSTAIN** 4 (7 rows), **LEAVE** 14 (14 rows)
- CONFIRM declarations to add: **38** alias(es) in config/taxonomy.yaml, making 192 row(s) reproducible
- the CONFIRM half is a raw-alias declaration: MEASURED to move neither `menu_hash` nor the answer space, so it rewrites no provenance (I2/D-2896) and relabels nothing
- CORRECT/ABSTAIN are RECORDED HERE AS OWED: a canonical relabel is a separate owner-gated store write with its own backup and decision (D-2898) — this applier never performs it

## CONFIRM — the raw labels to declare (one line each in config/taxonomy.yaml)

| canonical (the ONE home) | raw labels to declare | rows made reproducible |
|---|---|---|
| `anthropology` | `religious studies` | 23 |
| `artificial intelligence` | `knowledge representation and reasoning` | 2 |
| `communication theory` | `rhetorical studies` | 3 |
| `computational physics & simulation` | `numerical analysis` | 3 |
| `cultural design` | `architectural theory` | 6 |
| `cultural studies` | `mythology` | 6 |
| `decision making` | `problem solving theory` | 1 |
| `design psychology` | `customer experience management` | 1 |
| `health & medicine` | `clinical epidemiology`, `exercise physiology`, `nutrition science` | 12 |
| `human-computer interaction` | `affective computing`, `web accessibility` | 2 |
| `information science` | `visual analytics` | 5 |
| `interdisciplinary studies` | `urban studies` | 6 |
| `linguistics` | `phonology`, `psycholinguistics` | 4 |
| `literary theory` | `narrative theory` | 23 |
| `media studies` | `film theory`, `journalism studies` | 3 |
| `neuroscience` | `chronobiology`, `psychophysiology` | 2 |
| `operations research` | `statistical theory`, `time series analysis` | 5 |
| `philosophy` | `theology` | 5 |
| `political economy` | `community development`, `nonprofit management`, `public administration`, `public policy`, `social entrepreneurship` | 47 |
| `psychology` | `career counseling` | 14 |
| `research methodology` | `biostatistics`, `community-based participatory research`, `educational measurement`, `psychometrics` | 12 |
| `software engineering` | `cloud computing`, `web development` | 6 |
| `theoretical physics` | `optics` | 1 |

## CORRECT — 16 unit(s), 98 row(s)

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `innovation management -> creative process` | 29 | `entrepreneurship studies` | PROVENANCE-UNRESOLVED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `information visualization -> information science` | 23 | `emerging` | PROVENANCE-UNRESOLVED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `sports science -> health & medicine` | 8 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `animation studies -> computer graphics` | 7 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `health informatics -> information science` | 7 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `distributed systems -> software engineering` | 6 | `emerging` | PROVENANCE-UNRESOLVED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `financial regulation -> law` | 4 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `translation studies -> linguistics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `industrial relations -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `medical informatics -> health & medicine` | 2 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `implementation science -> research methodology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `problem solving -> cognitive science` | 1 | `emerging` | PROVENANCE-UNRESOLVED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `rhetorical theory -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `software architecture -> software engineering` | 1 | `emerging` | PROVENANCE-UNRESOLVED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:3bd897791f45a5796840971068a33144c4d4721498759b461836af071ef99892` | 1 | `marketing` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:9d6aa605c70cac702f12a47f738dacf2e63225ad9700f9a3486fbb40658ce646` | 1 | `design thinking` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |

## ABSTAIN — 4 unit(s), 7 row(s)

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `higher education administration -> organizational theory` | 4 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `medical humanities -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `molecular biology -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:c1a46f7a5bae2ba23574cf731d1538a46b8a10e20c707a0a6db6a442d9bbb86c` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |

## LEAVE — 14 unit(s), 14 row(s)

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `row:0f808ed97f0df455f77adcb3d78bcc020e911106d2874f4ac947248576ec2225` | 1 | `creative process` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:1dcb9f1d7b15f12041428e909a309ecaa65f8ba50295aec42067445b5d786be6` | 1 | `emerging` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:1f9d2696b37072d165fe786d8e83dfbc6bd4cdf30023c19846fbad4e0adf7503` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:2dbf74fca79b7302df0537696958c9c6b155c3d9352bdb4d993a7ae337aca7a6` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:3d25109da166538e711ab327f1619265871c082b3f4d152b01825114ee4d13b2` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:4ff20c35c6edd8a137d3c05d843d07a936295e3545ac93842e8b096b557c3476` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:7196e92b224bc5710254570558807e2939df002c78af825ecbee6d0522256097` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:960bd1bd87207aeccd3c61424b365d4a81fb8ae89419ff990cab6822e896d26f` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:d22d5313ff89b7f47c9daad0eea8be29227e527259712d97cbb96a738b614847` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:d5024f08d859d11a10f6d84805bb8b00e0ffc97d3e2148d7130292112d3ab528` | 1 | `communication theory` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:e42033a1a09216dea09bc55070d8f7b007320f8d933c1f09957b44d9c3c9dc04` | 1 | `business administration` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:ea8aa125fa0d0df62ebcfd1ef820cafa1be3f1eac0db636b6b16e91de9067bf1` | 1 | `behavioral economics` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:eb4a73655de67455ba0919966e77a8d40d093967172ba221ad9e02b40f3e8151` | 1 | `psychology` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `row:f8d167628442655e18110f11ace2d0854c12f4aaf3cfc467291b56b7a025a2f1` | 1 | `psychology` | DEFINITION-RE-SCOPE | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
