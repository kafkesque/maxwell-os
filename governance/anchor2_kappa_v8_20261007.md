# ANCHOR-2 per-axis agreement (60-row R2 adjudication sheet)

Sheet: governance/ANCHOR2_BLIND_SHEET_V8_20261007.csv  vs  pipeline key: governance/ANCHOR2_KEY_V8_20261007.json  (n=60).
D-275a: report chance-corrected agreement and error rate, never 'accuracy'.

| axis | n | observed agree | error rate | Cohen kappa | contra kappa | clean kappa |
|---|---|---|---|---|---|---|
| discipline | 60 | 0.4667 | 0.5333 | **0.4314** | 0.4042 | 0.4578 |
| domains (micro-binary, 41 classes) | 60 | 0.9659 | 0.0341 | **0.6408** | 0.6563 | 0.6189 |
| content_type | 60 | 0.5833 | 0.4167 | **0.0** | 0.0 | 0.0 |

## Domain set agreement

- mean Jaccard per row: **0.54**; exact set match: **14/60**
- human positives 136 vs pipeline 110 (both 81)
- macro kappa over 37 active domains: 0.4818

## Repair queue

51 rows disagree on at least one axis.

| row | stratum | max_contra | issue |
|---|---|---|---|
| 1 | contra | 0.999 | discipline: human=cognitive science pipeline=psychology; domains: human_only=['marketing & communications'] pipeline_only=['research practice'] |
| 2 | contra | 0.999 | discipline: human=political economy pipeline=economics; domains: human_only=['industrial design'] pipeline_only=['product design'] |
| 3 | contra | 0.999 | domains: human_only=[] pipeline_only=['marketing & communications'] |
| 4 | contra | 0.999 | discipline: human=finance pipeline=strategic thinking; domains: human_only=['finance & investment'] pipeline_only=[] |
| 5 | contra | 0.999 | domains: human_only=['personal productivity'] pipeline_only=[] |
| 6 | contra | 0.999 | domains: human_only=['editorial & advertising', 'graphic design', 'illustration', 'web & ui'] pipeline_only=['design strategy', 'user experience'] |
| 7 | contra | 0.999 | discipline: human=cognitive science pipeline=psychology; domains: human_only=['arts & culture', 'leadership', 'organizational behavior', 'user experience'] pipeline_only=['legal & public policy'] |
| 8 | contra | 0.999 | domains: human_only=['systems & frameworks'] pipeline_only=[] |
| 9 | contra | 0.999 | discipline: human=research methodology pipeline=risk management; domains: human_only=['research practice'] pipeline_only=[] |
| 10 | contra | 0.999 | discipline: human=operations research pipeline=strategic thinking |
| 11 | contra | 0.999 | discipline: human=operations research pipeline=behavioral economics; domains: human_only=[] pipeline_only=['business development', 'marketing & communications'] |
| 13 | contra | 0.999 | discipline: human=visual semiotics pipeline=communication theory; domains: human_only=['editorial & advertising'] pipeline_only=[] |
| 15 | contra | 0.999 | discipline: human=emerging pipeline=media studies; domains: human_only=['media & entertainment'] pipeline_only=[] |
| 16 | contra | 0.999 | discipline: human=artificial intelligence pipeline=economics |
| 17 | contra | 0.999 | domains: human_only=['brand identity'] pipeline_only=['business operations', 'marketing & communications'] |
| 18 | contra | 0.999 | discipline: human=research methodology pipeline=behavioral economics; domains: human_only=['user experience'] pipeline_only=[] |
| 19 | contra | 0.999 | domains: human_only=['personal productivity'] pipeline_only=['organizational behavior'] |
| 21 | contra | 0.998 | domains: human_only=['code & computation'] pipeline_only=[] |
| 22 | contra | 0.998 | discipline: human=systems thinking pipeline=software engineering; domains: human_only=['engineering & infrastructure'] pipeline_only=[] |
| 24 | contra | 0.998 | domains: human_only=['digital product', 'industrial design'] pipeline_only=['business operations'] |
| 25 | contra | 0.998 | domains: human_only=[] pipeline_only=['product design'] |
| 26 | contra | 0.998 | discipline: human=finance pipeline=strategic thinking; domains: human_only=['finance & investment', 'legal & public policy'] pipeline_only=['business operations'] |
| 27 | contra | 0.998 | discipline: human=visual semiotics pipeline=psychology; domains: human_only=['semiotics & communication'] pipeline_only=[] |
| 28 | contra | 0.998 | discipline: human=psychology pipeline=behavioral economics; domains: human_only=['personal productivity'] pipeline_only=['health & wellness', 'legal & public policy'] |
| 29 | contra | 0.998 | discipline: human=creative process pipeline=cultural design; domains: human_only=['semiotics & communication'] pipeline_only=['brand identity', 'editorial & advertising'] |
| 30 | contra | 0.998 | discipline: human=design thinking pipeline=human-computer interaction |
| 31 | clean | 0.009 | discipline: human=political economy pipeline=economics; domains: human_only=['business development'] pipeline_only=['emerging'] |
| 33 | clean | 0.279 | domains: human_only=['environmental design'] pipeline_only=[] |
| 35 | clean | 0.084 | discipline: human=behavioral economics pipeline=emerging |
| 36 | clean | 0.403 | domains: human_only=[] pipeline_only=['user experience'] |
| 37 | clean | 0.221 | discipline: human=strategic thinking pipeline=psychology; domains: human_only=['business development', 'design strategy', 'entrepreneurship', 'organizational behavior'] pipeline_only=[] |
| 38 | clean | 0.027 | discipline: human=cognitive science pipeline=neuroscience; domains: human_only=[] pipeline_only=['arts & culture', 'user experience'] |
| 39 | clean | 0.051 | domains: human_only=['code & computation'] pipeline_only=['computational science & physics'] |
| 40 | clean | 0.357 | discipline: human=operations research pipeline=creative process; domains: human_only=['design strategy'] pipeline_only=[] |
| 41 | clean | 0.008 | discipline: human=motion & time pipeline=human-computer interaction; domains: human_only=['motion design'] pipeline_only=[] |
| 42 | clean | 0.01 | discipline: human=finance pipeline=economics |
| 43 | clean | 0.016 | domains: human_only=['legal & public policy', 'organizational behavior'] pipeline_only=[] |
| 44 | clean | 0.057 | discipline: human=design psychology pipeline=emerging; domains: human_only=['user experience'] pipeline_only=['project management'] |
| 45 | clean | 0.34 | discipline: human=artificial intelligence pipeline=software engineering; domains: human_only=['ai & agents'] pipeline_only=['emerging'] |
| 46 | clean | 0.004 | domains: human_only=['design systems', 'web & ui'] pipeline_only=['digital product'] |
| 47 | clean | 0.351 | domains: human_only=['leadership', 'personal productivity'] pipeline_only=[] |
| 49 | clean | 0.208 | domains: human_only=[] pipeline_only=['business operations', 'organizational behavior'] |
| 50 | clean | 0.373 | domains: human_only=['business development', 'entrepreneurship'] pipeline_only=[] |
| 52 | clean | 0.006 | domains: human_only=['media & entertainment'] pipeline_only=[] |
| 53 | clean | 0.007 | discipline: human=design thinking pipeline=human-computer interaction; domains: human_only=['project management'] pipeline_only=[] |
| 54 | clean | 0.114 | domains: human_only=[] pipeline_only=['leadership'] |
| 56 | clean | 0.047 | discipline: human=research methodology pipeline=finance; domains: human_only=['finance & investment'] pipeline_only=['emerging'] |
| 57 | clean | 0.131 | discipline: human=strategic thinking pipeline=behavioral economics; domains: human_only=[] pipeline_only=['business development'] |
| 58 | clean | 0.304 | discipline: human=psychology pipeline=health & medicine; domains: human_only=['legal & public policy'] pipeline_only=[] |
| 59 | clean | 0.449 | discipline: human=cognitive science pipeline=psychology; domains: human_only=['ai & agents'] pipeline_only=['health & wellness'] |
| 60 | clean | 0.033 | discipline: human=behavioral economics pipeline=psychology; domains: human_only=['education', 'marketing & communications', 'user experience'] pipeline_only=['emerging'] |
