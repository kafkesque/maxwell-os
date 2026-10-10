# NLI LABEL AUDIT — entailment consistency (D2540/D2541)

> **Model:** DeBERTa-v3-large (local, D2298) · hypothesis = "This text is about {label}."

## Summary

| Metric | Value |
|---|---|
| FBs audited | 12552 |
| Discipline pairings | 5104 |
| Domain pairings | 7448 |
| Mean entail (discipline) | 0.3398 |
| Mean entail (domain) | 0.3133 |
| Contradict-label (likely mislabel) | 1882 |
| Weak support (entail < 0.5) | 6648 |
| NLI errors (recorded, not silent) | 0 |

## 🚩 Contradicts own label (top 30 — human-review candidates)

- `f7e8a83f8273165a2540d765d4986ed753b17255a8d9191edec00ed00f3c2dd0` [domain] `graphic design` — ent=0.0001 contra=0.9994
- `7833ce70b0c4ed38215331d7726e9284b0d510d0ec3e1ecd67d9a81f4e7f9e82` [discipline] `philosophy` — ent=0.0001 contra=0.9994
- `35c509d3c9609637370bc9c26cda741a74147c152e9144175b83f5df1003d963` [domain] `project management` — ent=0.0001 contra=0.9994
- `12ccd8c88104b63de2d796b405902642b8890c280ea871a1e2b710ec34813c6e` [domain] `business operations` — ent=0.0001 contra=0.9994
- `c15a53302fea3ba8892eb23903f71465ff1509f4993e7e3a40291ffe528dd628` [domain] `personal productivity` — ent=0.0001 contra=0.9993
- `22123cca3870756403413034fcef52853b55680eb3056d1719f53be9d92e427d` [discipline] `motion & time` — ent=0.0001 contra=0.9993
- `a54e61098f70340b35c80b29ef8c788eca50abb0445207befa1f60118ef2567e` [domain] `business operations` — ent=0.0001 contra=0.9992
- `a1ed6ee1afadee1d4f9b2f1872003e31eb71e78aee37031d16b9758d9da7a78e` [domain] `engineering practice` — ent=0.0001 contra=0.9992
- `bfc2bc75b2d4433fc781d5408494f1522520abfe6cf89204a784824b048a5f68` [domain] `personal productivity` — ent=0.0001 contra=0.9992
- `753c6edf95e08122424227da9c3473e7f3a17367593e7e44ed817780ae8b72be` [domain] `health & wellness` — ent=0.0001 contra=0.9992
- `d873459542ccec49f52c4ebeba78c0d132358c6b5accf6090ac0cd1213dc061a` [domain] `engineering & infrastructure` — ent=0.0001 contra=0.9992
- `f8e2472650a92b84e4e4728a28f83de0fb69b5716a94244a5e4f4323d5461f22` [domain] `engineering & infrastructure` — ent=0.0001 contra=0.9992
- `eb4a73655de67455ba0919966e77a8d40d093967172ba221ad9e02b40f3e8151` [domain] `personal productivity` — ent=0.0001 contra=0.9992
- `4aa4f9a2d0031019d47a466aebac152306fe5a68ecaeb1c6fa058115025a99c5` [discipline] `motion & time` — ent=0.0001 contra=0.9992
- `649dcebfbe6fd6c73c4a3d6d2d62ecdb010a1a2558cebe5b327d8f1846d41822` [discipline] `operations research` — ent=0.0001 contra=0.9991
- `7b11605ffe4c672bff9f8c7f7c654aecb2ed80599c6ac6f8450f133796ad279d` [domain] `motion design` — ent=0.0001 contra=0.9991
- `e4b2bcf75e0502ac7607b930d0befcf5711fc89300784645c4f0b21a8cdca01e` [domain] `product design` — ent=0.0002 contra=0.9992
- `f5d41fc33370cdb5e853f65c2935d8419b9770427bf1f9ede08e9c0f31bb0725` [domain] `digital product` — ent=0.0001 contra=0.9991
- `b48549b9f2a745345f18863378126d1f7f09a31e98d76dd8315e27ce30cec49e` [domain] `engineering & infrastructure` — ent=0.0001 contra=0.9991
- `db50778cba0f82f6a17966743c3871c3f8759434243e5c208c49a972ea83878a` [domain] `business operations` — ent=0.0001 contra=0.9991
- `b465e7866d1bd9b4f4585c66c7c7e4254152755639e0b8532e56973470d3ec25` [domain] `design strategy` — ent=0.0001 contra=0.9991
- `7820867ecaee486a938e4d4c7d2a71b16cbeab4064d523510002b2c6b1e98c50` [domain] `organizational behavior` — ent=0.0001 contra=0.9991
- `88a917b09ade9e3996f2b424309e9db7e9c71e0c5a78615a22360cce504cb4d0` [discipline] `linguistics` — ent=0.0001 contra=0.9991
- `f0bd37b0248017c0726afc1080184201b69ca53c95e10432dbd009fc7c94be5a` [domain] `health & wellness` — ent=0.0001 contra=0.999
- `7d2de6588d494bc83d9850d1a72f66d5843973dbbaa7416309eb6fa412a33c7b` [domain] `health & wellness` — ent=0.0001 contra=0.999
- `c7650ce040a4a1034e5a48fb39aa7925576bad00fb146a14f968ba20d3f50857` [domain] `personal productivity` — ent=0.0001 contra=0.999
- `48fbd403c6579e036615cab5c76fbc5380ee01c55787b5081a5913384773c1d8` [domain] `health & wellness` — ent=0.0001 contra=0.999
- `876909f7480c26761b0093f636f70155b8af57a7a957b2c2be928be219a39ec5` [domain] `product design` — ent=0.0002 contra=0.9991
- `a03273db4f9e5ca0c192b9c7fd45acb4f18a3d3a3e02bfba46153694e9f9dfa0` [discipline] `semiotics` — ent=0.0001 contra=0.999
- `209fe626195cfbf5b86a4328ed3bd7d5c9c4bcf4215e870d3fa9425265511b34` [discipline] `creative process` — ent=0.0001 contra=0.999

