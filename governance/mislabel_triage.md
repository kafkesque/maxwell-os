# MISLABEL TRIAGE — intersection of k-NN + T-NLI audits

> Highest-confidence mislabel/human-review candidates: an FB is listed only if it is flagged by BOTH the k-NN neighbor-disagreement audit (agreement ≤ 0.3) AND the T-NLI entailment audit (contradiction-dominant). Ranked by T-NLI contradiction gap (contra − entail), desc.

| # | fb_id | knn min agree | nli contra gap | knn axes | nli axes |
|---|-------|--------------:|---------------:|----------|----------|
| 1 | `7833ce70b0c4ed38215331d7726e9284b0d510d0ec3e1ecd67d9a81f4e7f9e82` | 0.0 | 0.9993 | discipline:philosophy | discipline:philosophy |
| 2 | `f7e8a83f8273165a2540d765d4986ed753b17255a8d9191edec00ed00f3c2dd0` | 0.0 | 0.9993 | discipline:literary theory | domain:graphic design |
| 3 | `12ccd8c88104b63de2d796b405902642b8890c280ea871a1e2b710ec34813c6e` | 0.0 | 0.9993 | discipline:philosophy | discipline:philosophy, domain:business operations |
| 4 | `c15a53302fea3ba8892eb23903f71465ff1509f4993e7e3a40291ffe528dd628` | 0.2 | 0.9992 | discipline:philosophy | domain:personal productivity |
| 5 | `eb4a73655de67455ba0919966e77a8d40d093967172ba221ad9e02b40f3e8151` | 0.1 | 0.9991 | discipline:organizational theory | domain:personal productivity |
| 6 | `d873459542ccec49f52c4ebeba78c0d132358c6b5accf6090ac0cd1213dc061a` | 0.2 | 0.9991 | discipline:political economy | domain:engineering & infrastructure |
| 7 | `f8e2472650a92b84e4e4728a28f83de0fb69b5716a94244a5e4f4323d5461f22` | 0.2 | 0.9991 | discipline:information science | domain:data visualization, domain:engineering & infrastructure |
| 8 | `bfc2bc75b2d4433fc781d5408494f1522520abfe6cf89204a784824b048a5f68` | 0.2 | 0.9991 | discipline:cognitive science | discipline:cognitive science, domain:personal productivity |
| 9 | `753c6edf95e08122424227da9c3473e7f3a17367593e7e44ed817780ae8b72be` | 0.2 | 0.9991 | discipline:machine learning | domain:health & wellness |
| 10 | `649dcebfbe6fd6c73c4a3d6d2d62ecdb010a1a2558cebe5b327d8f1846d41822` | 0.0 | 0.999 | discipline:operations research | discipline:operations research |
| 11 | `db50778cba0f82f6a17966743c3871c3f8759434243e5c208c49a972ea83878a` | 0.0 | 0.999 | discipline:sociology | domain:business operations, domain:organizational behavior |
| 12 | `88a917b09ade9e3996f2b424309e9db7e9c71e0c5a78615a22360cce504cb4d0` | 0.1 | 0.999 | discipline:linguistics | discipline:linguistics |
| 13 | `b48549b9f2a745345f18863378126d1f7f09a31e98d76dd8315e27ce30cec49e` | 0.1 | 0.999 | discipline:political economy | discipline:political economy, domain:engineering & infrastructure |
| 14 | `b465e7866d1bd9b4f4585c66c7c7e4254152755639e0b8532e56973470d3ec25` | 0.2 | 0.999 | discipline:strategic thinking | domain:design strategy, domain:marketing & communications |
| 15 | `f5d41fc33370cdb5e853f65c2935d8419b9770427bf1f9ede08e9c0f31bb0725` | 0.2 | 0.999 | discipline:marketing | domain:digital product |
| 16 | `7b11605ffe4c672bff9f8c7f7c654aecb2ed80599c6ac6f8450f133796ad279d` | 0.3 | 0.999 | discipline:media studies | domain:motion design |
| 17 | `a03273db4f9e5ca0c192b9c7fd45acb4f18a3d3a3e02bfba46153694e9f9dfa0` | 0.0 | 0.9989 | discipline:semiotics | discipline:semiotics |
| 18 | `209fe626195cfbf5b86a4328ed3bd7d5c9c4bcf4215e870d3fa9425265511b34` | 0.1 | 0.9989 | discipline:creative process | discipline:creative process |
| 19 | `cf9357f1fad7b90d67479d47654cb3c4e2a638a8e007d52190ee8853a1a207a7` | 0.2 | 0.9989 | discipline:sociology | domain:project management |
| 20 | `f0bd37b0248017c0726afc1080184201b69ca53c95e10432dbd009fc7c94be5a` | 0.3 | 0.9989 | discipline:artificial intelligence | domain:health & wellness |
| 21 | `2412d041e372525a9341bc521f881a356f612c1a11d0daddd793ce666fb95228` | 0.1 | 0.9988 | discipline:philosophy | domain:health & wellness |
| 22 | `3a51aaab2c44ffad41ef6a472089da188e6476357faf000e0f3167aeed86338e` | 0.1 | 0.9988 | discipline:sociology | domain:personal productivity |
| 23 | `baab3230adb97c4b073a24d23837c1f1f15b6d98728a4f717b54e21e0136d28e` | 0.0 | 0.9987 | discipline:anthropology | domain:personal productivity |
| 24 | `d8ce13707ccef04c51caad8774bf7078433b5c850830373e47869f9d399ce9f0` | 0.0 | 0.9987 | discipline:health & medicine | discipline:health & medicine |
| 25 | `3f45c164feba7e1ec24f15880abd981359172bfd70dd540b4f30749867ccb149` | 0.0 | 0.9987 | discipline:computational geometry | domain:engineering practice |
| 26 | `4c6da2601c51d7ad9d04109b1118e299d70918976f854a1ed8ccea7421d28a76` | 0.1 | 0.9987 | discipline:software engineering | discipline:software engineering, domain:engineering & infrastructure |
| 27 | `602d124fbb00866368649eb542d2c087ca038c25b671dc2d4d246250dc6e4ae6` | 0.1 | 0.9987 | discipline:law | domain:project management |
| 28 | `4d9905752d06889dba87a75528363b5fa33dc2b7d7d8117fb68682bdd6d0e22a` | 0.2 | 0.9987 | discipline:cultural design | discipline:cultural design, domain:industrial design |
| 29 | `dac290df6ff42331e8cab9a6ff31007c887faccbb49764ca16121315cc8e774b` | 0.2 | 0.9987 | discipline:philosophy | discipline:philosophy |
| 30 | `073410105c9c4abba6bbcd53ef7b371d478561715122f8167afa19ae47659657` | 0.0 | 0.9986 | discipline:systems thinking | domain:health & wellness, domain:legal & public policy, domain:project management, domain:urban planning |
| 31 | `4e89c948c01046dd9f8606cfc02da04b126541bc7c0789ab2beef30d253777a9` | 0.0 | 0.9986 | discipline:social network analysis | domain:brand identity |
| 32 | `b455f08b95fc9b47068556fdc6fb6c776b5d9da7fdfe32ed593d22b601acb18e` | 0.1 | 0.9986 | discipline:linguistics | discipline:linguistics, domain:health & wellness |
| 33 | `64a3a2f9f528a0e39be4248f0a46a32ddc93ea88ca913c55e3eaa002c995a97d` | 0.3 | 0.9986 | discipline:research methodology | discipline:research methodology, domain:engineering & infrastructure, domain:user experience |
| 34 | `81e5267f4a9d9b7835556b577e5d22a9cebe1d077e752c1eb55dc762a695fb4f` | 0.0 | 0.9985 | discipline:economics | discipline:economics, domain:marketing & communications |
| 35 | `79b6bde89195ac876e79e599d5d8861260aa83707213d8ec23012cfb6d5c71f6` | 0.0 | 0.9985 | discipline:creative process | discipline:creative process |
| 36 | `6d71448442b29796257728b5f8f3152f0e3225717434ec9b87b17335bd647e06` | 0.0 | 0.9985 | discipline:creative process | discipline:creative process |
| 37 | `44facab212962866d1afdbbde2d7c3a028d370937221589b709db7ebb73773b4` | 0.1 | 0.9985 | discipline:literary theory | domain:brand identity |
| 38 | `28c38f9e6443dc1455098a2c62048f214e0b85823c29cb89a7910e4bffcf5b09` | 0.1 | 0.9985 | discipline:cultural design | discipline:cultural design, domain:engineering practice |
| 39 | `d5e1f032fe2565d35b77859176c6dd3e9d0749d954a204db04d141dbecc4982f` | 0.2 | 0.9985 | discipline:law | domain:engineering & infrastructure |
| 40 | `faa1fe14c20472834d0b2d8c1c4c5eb417cabcf9d174b06150b8df19c550a252` | 0.2 | 0.9985 | discipline:design thinking | discipline:design thinking, domain:engineering & infrastructure, domain:product design, domain:user experience |
| 41 | `e624a0fc123e9070914e224517b278675f7957beff9b3b4c709b0832225d0b91` | 0.2 | 0.9985 | discipline:cognitive science | discipline:cognitive science, domain:business operations |
| 42 | `ee4bb3b7da6c766454d210c4d5bf53ec8af236e95c8509f63209fdfc8b4696b6` | 0.3 | 0.9985 | discipline:information science | domain:business operations |
| 43 | `e8c2a975b731c2dccbb3e893405ad40bf2b6bb3f355e0d91c192bc9bb1d10075` | 0.0 | 0.9984 | discipline:economics | domain:engineering & infrastructure |
| 44 | `0fc2285827c1d79d2823876972d362c3f874bfbd757704957e7c5bac9af65538` | 0.0 | 0.9984 | discipline:creative process | discipline:creative process |
| 45 | `9683d48971204f05cdcc755aaaf34c1c3908f3bb5d7d8a969d41485e679c49b2` | 0.0 | 0.9984 | discipline:anthropology | discipline:anthropology |
| 46 | `ece9470c35dc7f04c0761d93903ea6e3504e4d710a05132de57384d7bd874ff1` | 0.1 | 0.9984 | discipline:information security | domain:engineering & infrastructure |
| 47 | `8380d95144efad66fd62b7dbec0b89a652191428914511738b5347706db7d92a` | 0.2 | 0.9984 | discipline:information science | domain:data visualization, domain:engineering & infrastructure |
| 48 | `612420bc14fc66370ab5656ad2668f248437db036b6b27392072337a4b1a856d` | 0.2 | 0.9984 | discipline:design thinking | domain:engineering & infrastructure |
| 49 | `244a51e918d1c032c929d290dba71a791b0d1a99338d2c31070f6bde6fb12035` | 0.2 | 0.9984 | discipline:cultural design | discipline:cultural design |
| 50 | `dbb02e4cacef8e2978eaa880aab45018f7ff7c9d726db81a311cb3b95c670344` | 0.3 | 0.9984 | discipline:strategic thinking | domain:digital product |
