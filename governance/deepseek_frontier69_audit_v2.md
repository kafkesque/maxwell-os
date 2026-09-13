# Ontology-Bound Audit (v4 — definition-grounded, bge-m3 pre-ranked, local verifier)

**Verifier:** Qwen3.8-27B-MLX-4bit (local OMLX)  |  **Objects:** 69/69

| example_id | depth | discipline | domains | content_type | confidence |
|---|---|---|---|---|---|
| S4-GOLD-MINED-00020 | override:universal | override:cognitive science | override:semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00022 | override:universal | agree:systems thinking | agree:systems & frameworks | `principle` | high |
| S4-GOLD-MINED-00051 | override:cross-domain | override:complex adaptive systems | override:media & entertainment,business development | `principle` | medium |
| S4-GOLD-MINED-00065 | agree:domain | agree:color theory | agree:graphic design,brand identity,editorial & advertising | `principle` | high |
| S4-GOLD-MINED-00085 | override:cross-domain | override:systems thinking | override:systems & frameworks | `principle` | medium |
| S4-GOLD-MINED-00087 | override:universal | agree:computational theory | override:engineering practice,systems & frameworks | `principle` | high |
| S4-GOLD-MINED-00094 | agree:domain | override:strategic thinking | override:entrepreneurship,illustration | `principle` | medium |
| S4-GOLD-MINED-00096 | override:cross-domain | override:visual semiotics | override:brand identity,marketing & communications,editorial & advertising,semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00097 | agree:universal | override:systems thinking | override:graphic design,product design,science & research | `principle` | high |
| S4-GOLD-MINED-00139 | agree:cross-domain | agree:semiotics | agree:science & research,semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00145 | agree:domain | agree:privacy & surveillance | agree:ai & agents,legal & public policy | `principle` | high |
| S4-GOLD-MINED-00148 | agree:domain | agree:robotics | agree:ai & agents,engineering & infrastructure | `principle` | high |
| S4-GOLD-MINED-00161 | agree:domain | agree:law | agree:legal & public policy,finance & investment | `principle` | high |
| S4-GOLD-MINED-00168 | agree:domain | agree:color theory | agree:graphic design,editorial & advertising,brand identity | `principle` | high |
| S4-GOLD-MINED-00173 | agree:domain | agree:information science | agree:data visualization,information architecture,graphic design | `principle` | high |
| S4-GOLD-MINED-00177 | agree:domain | agree:information security | agree:engineering practice,web & ui | `tool_instruction` | high |
| S4-GOLD-MINED-00184 | agree:domain | agree:motion & time | agree:creative technology,motion design,performing arts | `principle` | high |
| S4-GOLD-MINED-00188 | agree:cross-domain | agree:linguistics | agree:semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00232 | agree:specialized | agree:generative ai | agree:ai & agents,engineering practice | `principle` | high |
| S4-GOLD-MINED-00237 | agree:domain | agree:social network analysis | agree:data visualization,systems & frameworks | `principle` | high |
| S4-GOLD-MINED-00253 | agree:domain | agree:creative process | agree:arts & culture | `principle` | high |
| S4-GOLD-MINED-00263 | agree:cross-domain | agree:complex adaptive systems | agree:systems & frameworks,ai & agents | `principle` | high |
| S4-GOLD-MINED-00313 | agree:domain | agree:computational geometry | agree:science & research | `principle` | high |
| S4-GOLD-MINED-00316 | agree:domain | agree:computational theory | agree:code & computation,systems & frameworks | `principle` | high |
| S4-GOLD-MINED-00323 | override:cross-domain | override:visual semiotics | override:data visualization,semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00334 | agree:domain | agree:finance | agree:entrepreneurship,finance & investment | `noise_drop` | high |
| S4-GOLD-MINED-00337 | agree:domain | agree:finance | agree:business operations,finance & investment | `principle` | high |
| S4-GOLD-MINED-00385 | agree:domain | agree:linguistics | agree:social sciences,media & entertainment | `noise_drop` | high |
| S4-GOLD-MINED-00386 | override:cross-domain | agree:information retrieval | agree:research & methodology,personal productivity | `principle` | high |
| S4-GOLD-MINED-00418 | agree:specialized | override:research methodology | agree:research & methodology,ai & agents | `process_template` | high |
| S4-GOLD-MINED-00422 | agree:domain | agree:semiotics | agree:semiotics & communication,data visualization | `principle` | high |
| S4-GOLD-MINED-00454 | override:domain | override:interdisciplinary studies | override:education,science & research | `principle` | medium |
| S4-GOLD-MINED-00461 | agree:domain | agree:human-computer interaction | agree:user experience,web & ui,information architecture | `principle` | high |
| S4-GOLD-MINED-00477 | agree:domain | agree:typography | agree:graphic design | `noise_drop` | high |
| S4-GOLD-MINED-00495 | agree:domain | agree:neuroscience | agree:science & research | `noise_drop` | high |
| S4-GOLD-MINED-00509 | agree:cross-domain | agree:health & medicine | agree:health & wellness,science & research | `principle` | medium |
| S4-GOLD-MINED-00516 | agree:domain | agree:health & medicine | agree:science & research,health & wellness | `noise_drop` | high |
| S4-GOLD-MINED-00531 | agree:domain | agree:creative process | agree:design strategy,product design | `principle` | high |
| S4-GOLD-MINED-00536 | agree:domain | agree:law | agree:legal & public policy,brand identity | `noise_drop` | high |
| S4-GOLD-MINED-00547 | agree:domain | agree:privacy & surveillance | agree:social sciences,research & methodology | `process_template` | medium |
| S4-GOLD-MINED-00558 | agree:domain | agree:media studies | agree:media & entertainment | `principle` | high |
| S4-GOLD-MINED-00562 | override:cross-domain | agree:human-computer interaction | agree:digital product,user experience | `principle` | high |
| S4-GOLD-MINED-00567 | agree:domain | agree:economics | agree:business operations,organizational behavior | `principle` | high |
| S4-GOLD-MINED-00584 | agree:domain | agree:information retrieval | agree:engineering practice,ai & agents | `principle` | high |
| S4-GOLD-MINED-00586 | agree:cross-domain | agree:complex adaptive systems | agree:systems & frameworks | `principle` | high |
| S4-GOLD-MINED-00590 | agree:domain | agree:economics | agree:media & entertainment,marketing & communications | `principle` | high |
| S4-GOLD-MINED-00594 | agree:domain | agree:visual perception | agree:graphic design,media & entertainment | `principle` | high |
| S4-GOLD-MINED-00601 | agree:domain | agree:performing arts | agree:arts & culture | `principle` | high |
| S4-GOLD-MINED-00613 | agree:domain | agree:design psychology | agree:graphic design,brand identity,editorial & advertising | `principle` | high |
| S4-GOLD-MINED-00629 | agree:universal | agree:computational physics & simulation | agree:computational science & physics,motion design | `principle` | high |
| S4-GOLD-MINED-00641 | agree:domain | agree:computational physics & simulation | agree:computational science & physics,code & computation | `principle` | high |
| S4-GOLD-MINED-00642 | agree:domain | agree:evolutionary biology | agree:science & research | `principle` | high |
| S4-GOLD-MINED-00650 | agree:domain | agree:typography | agree:graphic design,code & computation | `principle` | high |
| S4-GOLD-MINED-00686 | agree:domain | agree:information retrieval | agree:ai & agents,engineering practice | `principle` | high |
| S4-GOLD-MINED-00714 | agree:cross-domain | agree:generative ai | agree:computational art,code & computation | `principle` | high |
| S4-GOLD-MINED-00716 | agree:domain | agree:finance | agree:finance & investment | `principle` | high |
| S4-GOLD-MINED-00738 | agree:domain | agree:computational physics & simulation | agree:computational science & physics,engineering & infrastructure | `principle` | high |
| S4-GOLD-MINED-00835 | override:cross-domain | override:machine learning | agree:ai & agents,health & wellness | `principle` | high |
| S4-GOLD-MINED-00852 | override:universal | agree:health & medicine | agree:health & wellness,science & research | `principle` | high |
| S4-GOLD-MINED-00875 | override:cross-domain | override:complex adaptive systems | agree:systems & frameworks,science & research | `principle` | high |
| S4-GOLD-MINED-00882 | agree:cross-domain | agree:privacy & surveillance | agree:systems & frameworks,legal & public policy | `principle` | high |
| S4-GOLD-MINED-00883 | agree:domain | agree:typography | agree:graphic design | `principle` | high |
| S4-GOLD-MINED-00896 | override:cross-domain | agree:social network analysis | agree:marketing & communications,business development | `principle` | high |
| S4-GOLD-MINED-00900 | agree:domain | agree:performing arts | agree:arts & culture | `noise_drop` | high |
| S4-GOLD-MINED-00911 | override:cross-domain | agree:privacy & surveillance | agree:ai & agents,engineering practice | `principle` | high |
| S4-GOLD-MINED-00922 | override:universal | agree:creative process | agree:design strategy,project management | `principle` | high |
| S4-GOLD-MINED-00934 | override:specialized | agree:computational geometry | agree:data visualization,code & computation | `noise_drop` | high |
| S4-GOLD-MINED-00950 | override:universal | agree:computational theory | agree:code & computation,systems & frameworks | `principle` | high |
| S4-GOLD-MINED-01013 | override:cross-domain | agree:ecology | agree:systems & frameworks,science & research | `principle` | high |

> SIGNAL NOT PROOF — human remains arbiter (D2595).