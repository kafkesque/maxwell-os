# Ontology-Bound Audit (v4 — definition-grounded, bge-m3 pre-ranked, local verifier)

**Verifier:** Qwen3.8-27B-MLX-4bit (local OMLX)  |  **Objects:** 80/80

| example_id | depth | discipline | domains | content_type | confidence |
|---|---|---|---|---|---|
| S4-GOLD-MINED-00005 | agree:specialized | agree:machine learning | override:research & methodology | `principle` | high |
| S4-GOLD-MINED-00006 | override:cross-domain | agree:cultural design | override:arts & culture,engineering practice | `growth_edge` | high |
| S4-GOLD-MINED-00010 | agree:specialized | agree:human-computer interaction | override:user experience | `principle` | high |
| S4-GOLD-MINED-00025 | agree:domain | override:generative ai | override:research & methodology | `noise_drop` | high |
| S4-GOLD-MINED-00049 | override:universal | agree:cognitive science | override:business operations,product design | `principle` | high |
| S4-GOLD-MINED-00061 | agree:specialized | agree:machine learning | override:ai & agents | `principle` | high |
| S4-GOLD-MINED-00062 | agree:universal | agree:systems thinking | override:organizational behavior,leadership | `principle` | high |
| S4-GOLD-MINED-00069 | agree:cross-domain | agree:linguistics | override:education,semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00082 | agree:universal | override:complex adaptive systems | override:engineering & infrastructure | `principle` | high |
| S4-GOLD-MINED-00100 | override:cross-domain | override:psychology | agree:health & wellness | `principle` | high |
| S4-GOLD-MINED-00108 | agree:cross-domain | agree:cognitive science | agree:business operations,science & research | `principle` | high |
| S4-GOLD-MINED-00116 | agree:cross-domain | agree:creative process | agree:digital product,project management | `principle` | high |
| S4-GOLD-MINED-00124 | agree:domain | agree:strategic thinking | agree:business operations,organizational behavior,leadership | `principle` | high |
| S4-GOLD-MINED-00133 | agree:cross-domain | override:decision making | agree:business operations,digital product,legal & public policy,project management,personal productivity | `principle` | high |
| S4-GOLD-MINED-00140 | agree:universal | agree:risk management | agree:finance & investment,legal & public policy | `principle` | high |
| S4-GOLD-MINED-00159 | override:domain | agree:political economy | override:legal & public policy | `noise_drop` | medium |
| S4-GOLD-MINED-00175 | override:universal | agree:cognitive science | agree:business operations,entrepreneurship,education,research & methodology | `principle` | high |
| S4-GOLD-MINED-00200 | override:universal | override:decision making | override:business operations,legal & public policy,leadership | `principle` | high |
| S4-GOLD-MINED-00206 | agree:universal | agree:systems thinking | agree:business operations,legal & public policy | `principle` | high |
| S4-GOLD-MINED-00221 | agree:universal | agree:theoretical physics | agree:engineering & infrastructure,computational science & physics | `principle` | high |
| S4-GOLD-MINED-00272 | agree:domain | agree:anthropology | agree:social sciences | `noise_drop` | high |
| S4-GOLD-MINED-00277 | agree:specialized | agree:machine learning | agree:ai & agents | `tool_instruction` | high |
| S4-GOLD-MINED-00281 | agree:domain | agree:law | agree:ai & agents,legal & public policy | `growth_edge` | high |
| S4-GOLD-MINED-00295 | agree:specialized | agree:software engineering | agree:ai & agents,engineering practice | `tool_instruction` | high |
| S4-GOLD-MINED-00296 | agree:universal | agree:complex adaptive systems | override:science & research,systems & frameworks,computational science & physics | `principle` | high |
| S4-GOLD-MINED-00297 | agree:universal | agree:operations research | override:finance & investment,science & research,systems & frameworks | `principle` | high |
| S4-GOLD-MINED-00322 | agree:universal | agree:semiotics | override:arts & culture,systems & frameworks,research & methodology | `principle` | high |
| S4-GOLD-MINED-00329 | override:domain | agree:typography | override:graphic design,brand identity,editorial & advertising | `principle` | high |
| S4-GOLD-MINED-00336 | agree:domain | agree:semiotics | agree:semiotics & communication,arts & culture | `principle` | high |
| S4-GOLD-MINED-00341 | override:cross-domain | agree:human-computer interaction | override:user experience,software engineering,product design | `principle` | medium |
| S4-GOLD-MINED-00384 | agree:universal | agree:design thinking | override:arts & culture,engineering practice,user experience | `principle` | high |
| S4-GOLD-MINED-00390 | override:noise_drop | agree:artificial intelligence | agree:business operations,code & computation,research & methodology | `noise_drop` | high |
| S4-GOLD-MINED-00398 | agree:specialized | agree:computer graphics | agree:media & entertainment | `principle` | high |
| S4-GOLD-MINED-00434 | agree:domain | agree:cognitive science | agree:education | `noise_drop` | high |
| S4-GOLD-MINED-00439 | override:cross-domain | agree:sociology | agree:organizational behavior | `principle` | medium |
| S4-GOLD-MINED-00444 | override:specialized | agree:computational geometry | agree:education | `noise_drop` | high |
| S4-GOLD-MINED-00448 | agree:cross-domain | agree:neuroscience | agree:digital product,marketing & communications,editorial & advertising | `principle` | high |
| S4-GOLD-MINED-00455 | override:universal | agree:systems engineering | agree:engineering practice,product design | `principle` | medium |
| S4-GOLD-MINED-00464 | agree:cross-domain | agree:complex adaptive systems | agree:industrial design | `principle` | high |
| S4-GOLD-MINED-00467 | agree:universal | agree:human-computer interaction | agree:user experience,product design | `principle` | high |
| S4-GOLD-MINED-00507 | override:domain | override:visual semiotics | override:semiotics & communication | `noise_drop` | high |
| S4-GOLD-MINED-00527 | override:cross-domain | agree:political economy | override:urban planning,legal & public policy | `principle` | high |
| S4-GOLD-MINED-00541 | override:cross-domain | agree:philosophy | override:product design,urban planning,user experience | `principle` | high |
| S4-GOLD-MINED-00548 | override:domain | agree:media studies | agree:editorial & advertising | `noise_drop` | high |
| S4-GOLD-MINED-00552 | agree:cross-domain | agree:information science | agree:education,marketing & communications,data visualization | `principle` | high |
| S4-GOLD-MINED-00561 | override:domain | agree:visual semiotics | override:brand identity,graphic design | `principle` | high |
| S4-GOLD-MINED-00624 | override:cross-domain | agree:political economy | override:data visualization,education | `principle` | medium |
| S4-GOLD-MINED-00645 | override:cross-domain | override:linguistics | override:health & wellness,education | `principle` | medium |
| S4-GOLD-MINED-00655 | agree:specialized | override:computer graphics | override:motion design | `principle` | high |
| S4-GOLD-MINED-00662 | agree:specialized | override:creative process | override:graphic design | `principle` | high |
| S4-GOLD-MINED-00665 | agree:cross-domain | override:information science | override:research & methodology,legal & public policy | `noise_drop` | high |
| S4-GOLD-MINED-00668 | override:specialized | override:computational physics & simulation | agree:science & research | `process_instance` | high |
| S4-GOLD-MINED-00682 | override:universal | agree:research methodology | agree:research & methodology | `principle` | high |
| S4-GOLD-MINED-00684 | agree:cross-domain | override:systems thinking | agree:digital product,user experience,project management | `principle` | high |
| S4-GOLD-MINED-00713 | agree:domain | agree:human-computer interaction | agree:user experience,design strategy | `principle` | medium |
| S4-GOLD-MINED-00737 | agree:cross-domain | override:creative process | agree:digital product,entrepreneurship,project management | `principle` | high |
| S4-GOLD-MINED-00743 | override:universal | override:systems thinking | override:systems & frameworks,organizational behavior,legal & public policy | `principle` | high |
| S4-GOLD-MINED-00759 | agree:domain | agree:economics | override:business operations,entrepreneurship | `principle` | high |
| S4-GOLD-MINED-00791 | agree:specialized | agree:generative design | override:computational art,creative technology | `noise_drop` | high |
| S4-GOLD-MINED-00823 | agree:specialized | agree:computational theory | override:code & computation,computational science & physics | `noise_drop` | high |
| S4-GOLD-MINED-00824 | agree:universal | agree:semiotics | override:systems & frameworks,information architecture | `principle` | high |
| S4-GOLD-MINED-00847 | agree:specialized | agree:computer graphics | override:code & computation,media & entertainment | `principle` | high |
| S4-GOLD-MINED-00859 | agree:domain | agree:health & medicine | agree:health & wellness,science & research | `process_template` | medium |
| S4-GOLD-MINED-00862 | agree:specialized | agree:aesthetics | agree:graphic design,brand identity,editorial & advertising | `noise_drop` | high |
| S4-GOLD-MINED-00891 | override:universal | agree:cognitive science | override:ai & agents,project management,business operations | `principle` | high |
| S4-GOLD-MINED-00919 | agree:domain | agree:systems engineering | override:industrial design,business operations | `principle` | high |
| S4-GOLD-MINED-00938 | agree:universal | agree:complex adaptive systems | override:computational science & physics,computational art | `principle` | high |
| S4-GOLD-MINED-00969 | agree:specialized | agree:machine learning | override:ai & agents | `principle` | high |
| S4-GOLD-MINED-00970 | agree:cross-domain | agree:semiotics | agree:arts & culture,graphic design,semiotics & communication | `principle` | high |
| S4-GOLD-MINED-00971 | agree:domain | agree:cultural design | agree:arts & culture,graphic design,media & entertainment,motion design | `principle` | high |
| S4-GOLD-MINED-00972 | agree:domain | override:semiotics | override:semiotics & communication | `noise_drop` | high |
| S4-GOLD-MINED-00975 | agree:domain | override:strategic thinking | override:business operations,legal & public policy | `noise_drop` | high |
| S4-GOLD-MINED-00984 | override:domain | override:creative coding | override:computational art,creative technology | `noise_drop` | high |
| S4-GOLD-MINED-00995 | agree:domain | agree:cultural studies | override:social sciences,research & methodology | `noise_drop` | high |
| S4-GOLD-MINED-01000 | agree:specialized | agree:generative design | override:computational art,code & computation | `principle` | medium |
| S4-GOLD-MINED-01012 | agree:specialized | agree:machine learning | override:ai & agents,engineering practice | `principle` | high |
| S4-GOLD-MINED-01014 | agree:domain | agree:software engineering | override:ai & agents,engineering practice | `principle` | high |
| S4-GOLD-MINED-01018 | agree:universal | override:systems thinking | override:finance & investment,systems & frameworks,social sciences | `principle` | high |
| S4-GOLD-MINED-01023 | agree:universal | override:cognitive science | override:finance & investment,business operations,legal & public policy | `principle` | high |
| S4-GOLD-MINED-01027 | agree:specialized | agree:typography | override:graphic design,arts & culture | `principle` | medium |

> SIGNAL NOT PROOF — human remains arbiter (D2595).