# P5 HUMAN ADJUDICATION REVIEW PACK (D2585 P5 Step 3)

**135 high-suspicion FBs** (tier both/nli_only) with evidence.
Fill the blank fields in `temp/p5_review_pack.jsonl`, then save as `temp/p5_human_adjudication.jsonl` (freeze script input).

| example_id | tier | silver | challenger consensus | proposed correction | p_mislabel |
|---|---|---|---|---|---|
| S4-GOLD-MINED-00003 | both | psychology | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00008 | both | interdisciplinary studies | systems thinking | systems thinking | 1.0 |
| S4-GOLD-MINED-00009 | both | engineering | emerging | - | 0.9679 |
| S4-GOLD-MINED-00018 | both | media studies | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00056 | both | performing arts | emerging | - | 0.9679 |
| S4-GOLD-MINED-00057 | both | cultural studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00066 | both | anthropology | semiotics | semiotics | 1.0 |
| S4-GOLD-MINED-00067 | both | health & medicine | cognitive science | cognitive science | 1.0 |
| S4-GOLD-MINED-00082 | both | complex adaptive systems | complex adaptive systems | - | 0.6953 |
| S4-GOLD-MINED-00091 | both | theoretical physics | emerging | - | 0.9679 |
| S4-GOLD-MINED-00132 | both | cultural design | visual semiotics | visual semiotics | 1.0 |
| S4-GOLD-MINED-00134 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00147 | both | sociology | emerging | - | 0.9679 |
| S4-GOLD-MINED-00156 | both | interdisciplinary studies | urban planning | urban planning | 1.0 |
| S4-GOLD-MINED-00163 | both | privacy & surveillance | emerging | - | 0.9679 |
| S4-GOLD-MINED-00176 | both | cultural design | emerging | - | 0.9679 |
| S4-GOLD-MINED-00222 | both | linguistics | semiotics | semiotics | 1.0 |
| S4-GOLD-MINED-00228 | both | health & medicine | emerging | - | 0.9679 |
| S4-GOLD-MINED-00233 | both | evolutionary biology | emerging | - | 0.9679 |
| S4-GOLD-MINED-00239 | both | cultural design | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00242 | both | political economy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00252 | both | human-computer interaction | artificial intelligence | artificial intelligence | 1.0 |
| S4-GOLD-MINED-00273 | both | creative process | emerging | - | 0.9679 |
| S4-GOLD-MINED-00278 | both | research methodology | emerging | - | 0.9679 |
| S4-GOLD-MINED-00282 | both | cognitive science | complex adaptive systems | complex adaptive systems | 1.0 |
| S4-GOLD-MINED-00292 | both | philosophy | behavioral economics | behavioral economics | 1.0 |
| S4-GOLD-MINED-00314 | both | performing arts | creative process | creative process | 1.0 |
| S4-GOLD-MINED-00338 | both | creative process | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00343 | both | political economy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00368 | both | media studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00373 | both | cultural studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00374 | both | philosophy | artificial intelligence | artificial intelligence | 1.0 |
| S4-GOLD-MINED-00378 | both | cultural studies | risk management | risk management | 1.0 |
| S4-GOLD-MINED-00402 | both | political economy | political economy | - | 0.6953 |
| S4-GOLD-MINED-00411 | both | performing arts | emerging | - | 0.9679 |
| S4-GOLD-MINED-00420 | both | research methodology | emerging | - | 0.9679 |
| S4-GOLD-MINED-00423 | both | theoretical physics | systems thinking | systems thinking | 1.0 |
| S4-GOLD-MINED-00434 | both | cognitive science | emerging | - | 0.9679 |
| S4-GOLD-MINED-00440 | both | game design | generative ai | generative ai | 1.0 |
| S4-GOLD-MINED-00463 | both | health & medicine | psychology | psychology | 1.0 |
| S4-GOLD-MINED-00475 | both | creative process | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00481 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00505 | both | systems engineering | emerging | - | 0.9679 |
| S4-GOLD-MINED-00506 | both | systems engineering | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00507 | both | research methodology | emerging | - | 0.9679 |
| S4-GOLD-MINED-00527 | both | political economy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00529 | both | cultural design | visual perception | visual perception | 1.0 |
| S4-GOLD-MINED-00541 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00548 | both | media studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00557 | both | health & medicine | psychology | psychology | 1.0 |
| S4-GOLD-MINED-00581 | both | finance | human-computer interaction | human-computer interaction | 1.0 |
| S4-GOLD-MINED-00587 | both | human-computer interaction | emerging | - | 0.9679 |
| S4-GOLD-MINED-00604 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00606 | both | operations research | research methodology | research methodology | 1.0 |
| S4-GOLD-MINED-00624 | both | political economy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00625 | both | health & medicine | neuroscience | neuroscience | 1.0 |
| S4-GOLD-MINED-00631 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00655 | both | media studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00656 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00658 | both | interdisciplinary studies | political economy | political economy | 1.0 |
| S4-GOLD-MINED-00665 | both | research methodology | emerging | - | 0.9679 |
| S4-GOLD-MINED-00671 | both | computational theory | emerging | - | 0.9679 |
| S4-GOLD-MINED-00699 | both | operations research | emerging | - | 0.9679 |
| S4-GOLD-MINED-00703 | both | political economy | political economy | - | 0.6953 |
| S4-GOLD-MINED-00712 | both | creative process | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00713 | both | human-computer interaction | research methodology | research methodology | 1.0 |
| S4-GOLD-MINED-00722 | both | political economy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00726 | both | health & medicine | design psychology | design psychology | 1.0 |
| S4-GOLD-MINED-00729 | both | media studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00734 | both | cultural design | design psychology | design psychology | 1.0 |
| S4-GOLD-MINED-00746 | both | media studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-00747 | both | visual perception | color theory | color theory | 1.0 |
| S4-GOLD-MINED-00777 | both | risk management | research methodology | research methodology | 1.0 |
| S4-GOLD-MINED-00790 | both | philosophy | design psychology | design psychology | 1.0 |
| S4-GOLD-MINED-00807 | both | computational physics & simulation | emerging | - | 0.9679 |
| S4-GOLD-MINED-00850 | both | cultural design | emerging | - | 0.9679 |
| S4-GOLD-MINED-00853 | both | motion & time | visual semiotics | visual semiotics | 1.0 |
| S4-GOLD-MINED-00857 | both | interdisciplinary studies | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00864 | both | cultural design | emerging | - | 0.9679 |
| S4-GOLD-MINED-00885 | both | health & medicine | psychology | psychology | 1.0 |
| S4-GOLD-MINED-00898 | both | cultural design | systems thinking | systems thinking | 1.0 |
| S4-GOLD-MINED-00912 | both | software engineering | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00927 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00932 | both | information security | emerging | - | 0.9679 |
| S4-GOLD-MINED-00936 | both | political economy | strategic thinking | strategic thinking | 1.0 |
| S4-GOLD-MINED-00937 | both | creative process | strategic thinking | strategic thinking | 1.0 |
| S4-GOLD-MINED-00939 | both | research methodology | psychology | psychology | 1.0 |
| S4-GOLD-MINED-00945 | both | cognitive science | emerging | - | 0.9679 |
| S4-GOLD-MINED-00955 | both | game design | emerging | - | 0.9679 |
| S4-GOLD-MINED-00963 | both | theoretical physics | emerging | - | 0.9679 |
| S4-GOLD-MINED-00965 | both | finance | organizational theory | organizational theory | 1.0 |
| S4-GOLD-MINED-00972 | both | linguistics | semiotics | semiotics | 1.0 |
| S4-GOLD-MINED-00973 | both | political economy | semiotics | semiotics | 1.0 |
| S4-GOLD-MINED-00975 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-00977 | both | creative process | emerging | - | 0.9679 |
| S4-GOLD-MINED-00987 | both | organizational theory | interdisciplinary studies | interdisciplinary studies | 1.0 |
| S4-GOLD-MINED-00995 | both | cultural studies | sociology | sociology | 1.0 |
| S4-GOLD-MINED-01002 | both | human-computer interaction | design psychology | design psychology | 1.0 |
| S4-GOLD-MINED-01010 | both | media studies | emerging | - | 0.9679 |
| S4-GOLD-MINED-01017 | both | philosophy | emerging | - | 0.9679 |
| S4-GOLD-MINED-01021 | both | performing arts | emerging | - | 0.9679 |
| S4-GOLD-MINED-00014 | nli_only | motion & time | emerging | - | 0.9343 |
| S4-GOLD-MINED-00037 | nli_only | anthropology | cultural studies | cultural studies | 1.0 |
| S4-GOLD-MINED-00063 | nli_only | software engineering | emerging | - | 0.9343 |
| S4-GOLD-MINED-00083 | nli_only | philosophy | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00098 | nli_only | strategic thinking | strategic thinking | - | 0.5184 |
| S4-GOLD-MINED-00112 | nli_only | motion & time | motion & time | - | 0.5184 |
| S4-GOLD-MINED-00114 | nli_only | machine learning | emerging | - | 0.9343 |
| S4-GOLD-MINED-00182 | nli_only | cultural design | visual semiotics | visual semiotics | 1.0 |
| S4-GOLD-MINED-00199 | nli_only | research methodology | research methodology | - | 0.5184 |
| S4-GOLD-MINED-00210 | nli_only | creative process | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00245 | nli_only | visual semiotics | visual semiotics | - | 0.5184 |
| S4-GOLD-MINED-00274 | nli_only | philosophy | emerging | - | 0.9343 |
| S4-GOLD-MINED-00294 | nli_only | interdisciplinary studies | emerging | - | 0.9343 |
| S4-GOLD-MINED-00299 | nli_only | strategic thinking | communication theory | communication theory | 1.0 |
| S4-GOLD-MINED-00310 | nli_only | strategic thinking | organizational theory | organizational theory | 1.0 |
| S4-GOLD-MINED-00348 | nli_only | cultural studies | emerging | - | 0.9343 |
| S4-GOLD-MINED-00366 | nli_only | evolutionary biology | emerging | - | 0.9343 |
| S4-GOLD-MINED-00372 | nli_only | media studies | emerging | - | 0.9343 |
| S4-GOLD-MINED-00421 | nli_only | media studies | emerging | - | 0.9343 |
| S4-GOLD-MINED-00452 | nli_only | human-computer interaction | design thinking | design thinking | 1.0 |
| S4-GOLD-MINED-00482 | nli_only | motion & time | emerging | - | 0.9343 |
| S4-GOLD-MINED-00525 | nli_only | cultural studies | emerging | - | 0.9343 |
| S4-GOLD-MINED-00602 | nli_only | creative coding | generative ai | generative ai | 1.0 |
| S4-GOLD-MINED-00668 | nli_only | computational physics & simulation | emerging | - | 0.9343 |
| S4-GOLD-MINED-00681 | nli_only | linguistics | philosophy | philosophy | 1.0 |
| S4-GOLD-MINED-00693 | nli_only | cultural design | emerging | - | 0.9343 |
| S4-GOLD-MINED-00795 | nli_only | anthropology | emerging | - | 0.9343 |
| S4-GOLD-MINED-00862 | nli_only | cultural design | visual semiotics | visual semiotics | 1.0 |
| S4-GOLD-MINED-00895 | nli_only | philosophy | emerging | - | 0.9343 |
| S4-GOLD-MINED-00909 | nli_only | computational geometry | semiotics | semiotics | 1.0 |
| S4-GOLD-MINED-00968 | nli_only | communication theory | interdisciplinary studies | interdisciplinary studies | 1.0 |
| S4-GOLD-MINED-00971 | nli_only | cultural design | visual semiotics | visual semiotics | 1.0 |
| S4-GOLD-MINED-00984 | nli_only | interdisciplinary studies | creative coding | creative coding | 1.0 |
| S4-GOLD-MINED-00998 | nli_only | human-computer interaction | systems thinking | systems thinking | 1.0 |
