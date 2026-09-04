# NLI LABEL AUDIT — entailment consistency (D2540/D2541)

> **Model:** DeBERTa-v3-large (local, D2298) · hypothesis = "This text is about {label}."

## Summary

| Metric | Value |
|---|---|
| FBs audited | 23364 |
| Discipline pairings | 7068 |
| Domain pairings | 16296 |
| Mean entail (discipline) | 0.3273 |
| Mean entail (domain) | 0.2646 |
| Contradict-label (likely mislabel) | 4640 |
| Weak support (entail < 0.1) | 10071 |
| NLI errors (recorded, not silent) | 0 |

## 🚩 Contradicts own label (top 30 — human-review candidates)

- `dad393759b08c847a58ce2a3534d013dbba634d889a9d1213c3965d75963eab1` [domain] `engineering practice` — ent=0.0001 contra=0.9996
- `6ebf78c131bf761df8f7d594dd40683aec654d924f618466d0c2cd24bb35752b` [domain] `business operations` — ent=0.0001 contra=0.9996
- `015b40f08499323ba7dd08333988ab2514630fa3e3af29553d1cc06a3365b63e` [domain] `engineering practice` — ent=0.0001 contra=0.9996
- `8d3809b024eff0a4cf4d6416eed846f3a784a5e4d1ba375f4ad3953c7fae5a61` [discipline] `software engineering` — ent=0.0001 contra=0.9996
- `46d4e1a8dfce09e03e54ee671928207a0b642d748760f95b3b501f75b071ea63` [domain] `environmental design` — ent=0.0001 contra=0.9995
- `6887817ecd209b0c1898d27a7fcfa169abace69a3ef35620fb85afed789e550f` [domain] `personal productivity` — ent=0.0001 contra=0.9995
- `8d0d8ab93ed841e1cf488a7b2d057141c502fd6a5b8d19c93322b9dce08252f5` [discipline] `philosophy` — ent=0.0001 contra=0.9995
- `e714509eeac5ed8149bd8a8bfc63e4b843fc2252a1c87a7e704f03b7a89fbdd8` [domain] `engineering & infrastructure` — ent=0.0001 contra=0.9995
- `c64f086db7187e36f29cae9d931c429bd21be2088aa26924e08a29e4df9883a2` [domain] `business operations` — ent=0.0001 contra=0.9994
- `faa4f2d3d0280af035e4f23c2fd4c65e01690052c4120c124423daa55fa1d002` [domain] `personal productivity` — ent=0.0001 contra=0.9994
- `8d077b9a74599e7bc23388e2be82eb894610ce31da4ab4675338e1f8109706fd` [domain] `business operations` — ent=0.0001 contra=0.9994
- `4bf7c5a53525881538fc3a2b302bc05af6538086a393f8c3db6d348a697b9393` [domain] `health & wellness` — ent=0.0001 contra=0.9994
- `276e2f256075cb43baa1280d8d862722098f7e68400e8475e1fefc0a3c9574f7` [domain] `health & wellness` — ent=0.0001 contra=0.9994
- `127edfab2c0fa00bc3391b7c8c805b43bfb05cec33c3905718f94f188c5ebf23` [domain] `digital product` — ent=0.0001 contra=0.9994
- `d0b799314e05abae39f23cccc5ba5aa8e7d41f841b771aaabcb584432230ff53` [domain] `packaging` — ent=0.0001 contra=0.9994
- `41a88cbab9a06a3b4b7ba83b22a9cc83e29bf5b4f90407e4fceb008d9bc415dc` [domain] `business operations` — ent=0.0001 contra=0.9994
- `e053dc7eaf15fc81fcbc91cbf3e0bc233cac7836e6a40f25e727e68146f2797e` [domain] `business operations` — ent=0.0001 contra=0.9994
- `b469d8b4370c757a04d3aa4fe67c3d088c0cce39077a2ebc544f5e4ad79d69c7` [domain] `personal productivity` — ent=0.0001 contra=0.9994
- `9f8c31e5030a65359a72442ec8024942275f1c998af3665b1a1a9175d61d02a4` [discipline] `motion & time` — ent=0.0001 contra=0.9994
- `554a22ebb2e5b9829eb343d6912a448d4eb396105c81a9a085fc673eaa0a0148` [domain] `media & entertainment` — ent=0.0001 contra=0.9993
- `86a996c254b8756cc96336595926336f5415882aca52118fa60967c5136f1bce` [domain] `engineering & infrastructure` — ent=0.0001 contra=0.9993
- `8d6943fe6f9215bc4ba9bb90a92b89440d8397b82dbb70084e57f64eb1999b40` [domain] `project management` — ent=0.0001 contra=0.9993
- `a34696fb9d0c7d3fe564da5de56cb89114e2e117b5c8023ac66c8b978e7b2719` [domain] `arts & culture` — ent=0.0001 contra=0.9993
- `ea0a48cbfaf764b2777927fa1cd56e2c5579cd7d08ece5169ce92832879afb59` [domain] `product design` — ent=0.0001 contra=0.9993
- `c819167859647ada2f05e8013cd8820b43a9de2d93ca57a4f570386a24d8bfc2` [domain] `personal productivity` — ent=0.0001 contra=0.9993
- `e83062e9cf96f1808c37e8d60fc6284db3a937b60abf6bb86afa56e658109fd0` [domain] `health & wellness` — ent=0.0001 contra=0.9993
- `2c6256273bd1ec966fbc13413b75de7b8fa640669cbfb50a730bc2befeb11fab` [domain] `personal productivity` — ent=0.0001 contra=0.9993
- `61e45b7d6dfe4933f94e9ab9b6ac92ecec39886d8f655dca824a5b8ba2c6a7f1` [domain] `user experience` — ent=0.0001 contra=0.9993
- `402fa50814c912bfee490da199bb4587adc04a383837c3cc985ddf49de91ca8b` [domain] `engineering & infrastructure` — ent=0.0001 contra=0.9993
- `3468303fb3258bfbc2498aa5d8477759a4a75cda4eacec81cf001706dcc0fd02` [domain] `motion design` — ent=0.0001 contra=0.9992

