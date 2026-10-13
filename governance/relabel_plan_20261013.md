# RELABEL PLAN — 2026-10-13

Rendered by `scripts/apply_relabel_rulings.py` (D-2977) from `config/relabel_rulings.yaml` + `canonical_relabel_review_20261013.csv`. **DO NOT hand-edit: re-run the applier.**

- units: 70 — **CORRECT** 4 (103 rows), **ABSTAIN** 1 (60 rows), **ESCALATE** 65 (304 rows)
- CONFIRM declarations to add: **0** alias(es) in config/taxonomy.yaml, making 0 row(s) reproducible
- the CONFIRM half is a raw-alias declaration: MEASURED to move neither `menu_hash` nor the answer space, so it rewrites no provenance (I2/D-2896) and relabels nothing
- CORRECT/ABSTAIN are RECORDED HERE AS OWED: a canonical relabel is a separate owner-gated store write with its own backup and decision (D-2898) — this applier never performs it

## CONFIRM — the raw labels to declare (one line each in config/taxonomy.yaml)

| canonical (the ONE home) | raw labels to declare | rows made reproducible |
|---|---|---|

## CORRECT — 4 unit(s), 103 row(s)

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `marketing science -> emerging` | 94 | `marketing` | LATE-HOME | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `entrepreneurial studies -> emerging` | 4 | `entrepreneurship studies` | LATE-HOME | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |
| `marketing strategy -> emerging` | 4 | `marketing` | LATE-HOME | class LATE-HOME ruled CORRECT |
| `market research -> emerging` | 1 | `marketing` | LATE-HOME | class LATE-HOME ruled CORRECT |

## ABSTAIN — 1 unit(s), 60 row(s)

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `computer science -> software engineering` | 60 | `emerging` | PROVENANCE-UNRESOLVED | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |

## ESCALATE — 65 unit(s), 304 row(s)

These units NO ruling reaches. They are the owner's remaining decision, ordered by leverage — nothing here is inferred from a neighbour.

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `innovation management -> creative process` | 29 | `entrepreneurship studies` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `public policy -> political economy` | 28 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `information visualization -> information science` | 23 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `narrative theory -> literary theory` | 23 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `narrative theory` shares no content token with `literary theory` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `religious studies -> anthropology` | 23 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `religious studies` shares no content token with `anthropology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `career counseling -> psychology` | 14 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `career counseling` shares no content token with `psychology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `public administration -> political economy` | 9 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `sports science -> health & medicine` | 8 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `sports science` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `animation studies -> computer graphics` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `animation studies` shares no content token with `computer graphics` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `health informatics -> information science` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `health informatics` shares no content token with `information science` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `psychometrics -> research methodology` | 7 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `architectural theory -> cultural design` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `architectural theory` shares no content token with `cultural design` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `distributed systems -> software engineering` | 6 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `mythology -> cultural studies` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `mythology` shares no content token with `cultural studies` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `nutrition science -> health & medicine` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `nutrition science` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `social entrepreneurship -> political economy` | 6 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `urban studies -> interdisciplinary studies` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `urban studies` shares no content token with `interdisciplinary studies` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `exercise physiology -> health & medicine` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `exercise physiology` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `theology -> philosophy` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `theology` shares no content token with `philosophy` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `visual analytics -> information science` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `visual analytics` shares no content token with `information science` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `financial regulation -> law` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `financial regulation` shares no content token with `law` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `higher education administration -> organizational theory` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `higher education administration` shares no content token with `organizational theory` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `translation studies -> linguistics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `translation studies` shares no content token with `linguistics` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `cloud computing -> software engineering` | 3 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `educational measurement -> research methodology` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `educational measurement` shares no content token with `research methodology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `nonprofit management -> political economy` | 3 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `numerical analysis -> computational physics & simulation` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `numerical analysis` shares no content token with `computational physics & simulation` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `rhetorical studies -> communication theory` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `rhetorical studies` shares no content token with `communication theory` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `statistical theory -> operations research` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `statistical theory` shares no content token with `operations research` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `web development -> software engineering` | 3 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `film theory -> media studies` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `film theory` shares no content token with `media studies` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `industrial relations -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `industrial relations` shares no content token with `sociology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `knowledge representation and reasoning -> artificial intelligence` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `knowledge representation and reasoning` shares no content token with `artificial intelligence` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `medical informatics -> health & medicine` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `medical informatics` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `phonology -> linguistics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `phonology` shares no content token with `linguistics` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `psycholinguistics -> linguistics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `psycholinguistics` shares no content token with `linguistics` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `time series analysis -> operations research` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `time series analysis` shares no content token with `operations research` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `affective computing -> human-computer interaction` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `affective computing` shares no content token with `human-computer interaction` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `biostatistics -> research methodology` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `chronobiology -> neuroscience` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `chronobiology` shares no content token with `neuroscience` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `clinical epidemiology -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `clinical epidemiology` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `community development -> political economy` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `community-based participatory research -> research methodology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `community-based participatory research` shares no content token with `research methodology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `customer experience management -> design psychology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `customer experience management` shares no content token with `design psychology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `implementation science -> research methodology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `implementation science` shares no content token with `research methodology` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `journalism studies -> media studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `journalism studies` shares no content token with `media studies` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `medical humanities -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `medical humanities` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `molecular biology -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `molecular biology` shares no content token with `health & medicine` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `optics -> theoretical physics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `optics` shares no content token with `theoretical physics` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `problem solving -> cognitive science` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `problem solving theory -> decision making` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `problem solving theory` shares no content token with `decision making` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `psychophysiology -> neuroscience` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `psychophysiology` shares no content token with `neuroscience` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `rhetorical theory -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `rhetorical theory` shares no content token with `communication theory` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `software architecture -> software engineering` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `web accessibility -> human-computer interaction` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED ruled CONFIRM, but `web accessibility` shares no content token with `human-computer interaction` (its name, raws or definition) — the lexical guard holds it back for the owner |
| `row:3bd897791f45a5796840971068a33144c4d4721498759b461836af071ef99892` | 1 | `marketing` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:9d6aa605c70cac702f12a47f738dacf2e63225ad9700f9a3486fbb40658ce646` | 1 | `design thinking` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:0f808ed97f0df455f77adcb3d78bcc020e911106d2874f4ac947248576ec2225` | 1 | `creative process` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:1dcb9f1d7b15f12041428e909a309ecaa65f8ba50295aec42067445b5d786be6` | 1 | `emerging` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:1f9d2696b37072d165fe786d8e83dfbc6bd4cdf30023c19846fbad4e0adf7503` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:2dbf74fca79b7302df0537696958c9c6b155c3d9352bdb4d993a7ae337aca7a6` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:3d25109da166538e711ab327f1619265871c082b3f4d152b01825114ee4d13b2` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:4ff20c35c6edd8a137d3c05d843d07a936295e3545ac93842e8b096b557c3476` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:7196e92b224bc5710254570558807e2939df002c78af825ecbee6d0522256097` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:960bd1bd87207aeccd3c61424b365d4a81fb8ae89419ff990cab6822e896d26f` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
