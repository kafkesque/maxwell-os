# MISLABEL TRIAGE — intersection of k-NN + T-NLI audits

> Highest-confidence mislabel/human-review candidates: an FB is listed only if it is flagged by BOTH the k-NN neighbor-disagreement audit (agreement ≤ 0.3) AND the T-NLI entailment audit (contradiction-dominant). Ranked by T-NLI contradiction gap (contra − entail), desc.

| # | fb_id | knn min agree | nli contra gap | knn axes | nli axes |
|---|-------|--------------:|---------------:|----------|----------|
| 1 | `8d3809b024eff0a4cf4d6416eed846f3a784a5e4d1ba375f4ad3953c7fae5a61` | 0.0 | 0.9995 | discipline:software engineering | discipline:software engineering, domain:marketing & communications |
| 2 | `dad393759b08c847a58ce2a3534d013dbba634d889a9d1213c3965d75963eab1` | 0.1 | 0.9995 | discipline:aesthetics | domain:engineering practice |
| 3 | `015b40f08499323ba7dd08333988ab2514630fa3e3af29553d1cc06a3365b63e` | 0.2 | 0.9995 | domain:engineering practice|environmental design|product design | domain:engineering practice, domain:environmental design, domain:product design |
| 4 | `8d0d8ab93ed841e1cf488a7b2d057141c502fd6a5b8d19c93322b9dce08252f5` | 0.0 | 0.9994 | discipline:philosophy | discipline:philosophy |
| 5 | `e714509eeac5ed8149bd8a8bfc63e4b843fc2252a1c87a7e704f03b7a89fbdd8` | 0.1 | 0.9994 | discipline:political economy | domain:engineering & infrastructure |
| 6 | `46d4e1a8dfce09e03e54ee671928207a0b642d748760f95b3b501f75b071ea63` | 0.2 | 0.9994 | domain:design strategy|engineering practice|environmental design|project management | domain:design strategy, domain:engineering practice, domain:environmental design, domain:project management |
| 7 | `276e2f256075cb43baa1280d8d862722098f7e68400e8475e1fefc0a3c9574f7` | 0.0 | 0.9993 | discipline:philosophy, domain:health & wellness | discipline:philosophy, domain:health & wellness |
| 8 | `d0b799314e05abae39f23cccc5ba5aa8e7d41f841b771aaabcb584432230ff53` | 0.0 | 0.9993 | discipline:decision making, domain:engineering & infrastructure|packaging | discipline:decision making, domain:engineering & infrastructure, domain:packaging |
| 9 | `127edfab2c0fa00bc3391b7c8c805b43bfb05cec33c3905718f94f188c5ebf23` | 0.0 | 0.9993 | discipline:information science, domain:digital product | domain:digital product |
| 10 | `4bf7c5a53525881538fc3a2b302bc05af6538086a393f8c3db6d348a697b9393` | 0.1 | 0.9993 | discipline:systems engineering, domain:engineering & infrastructure|health & wellness | domain:health & wellness |
| 11 | `9f8c31e5030a65359a72442ec8024942275f1c998af3665b1a1a9175d61d02a4` | 0.2 | 0.9993 | discipline:motion & time | discipline:motion & time |
| 12 | `ea0a48cbfaf764b2777927fa1cd56e2c5579cd7d08ece5169ce92832879afb59` | 0.0 | 0.9992 | discipline:cognitive science | domain:brand identity, domain:graphic design, domain:marketing & communications, domain:product design, domain:user experience |
| 13 | `86a996c254b8756cc96336595926336f5415882aca52118fa60967c5136f1bce` | 0.0 | 0.9992 | discipline:information security, domain:engineering & infrastructure | domain:engineering & infrastructure |
| 14 | `c819167859647ada2f05e8013cd8820b43a9de2d93ca57a4f570386a24d8bfc2` | 0.0 | 0.9992 | discipline:systems thinking | domain:personal productivity |
| 15 | `8d6943fe6f9215bc4ba9bb90a92b89440d8397b82dbb70084e57f64eb1999b40` | 0.0 | 0.9992 | discipline:economics, domain:project management | discipline:economics, domain:project management |
| 16 | `e83062e9cf96f1808c37e8d60fc6284db3a937b60abf6bb86afa56e658109fd0` | 0.1 | 0.9992 | domain:health & wellness|science & research | discipline:research methodology, domain:health & wellness |
| 17 | `a34696fb9d0c7d3fe564da5de56cb89114e2e117b5c8023ac66c8b978e7b2719` | 0.1 | 0.9992 | discipline:computer graphics, domain:arts & culture|media & entertainment | domain:arts & culture, domain:media & entertainment |
| 18 | `61e45b7d6dfe4933f94e9ab9b6ac92ecec39886d8f655dca824a5b8ba2c6a7f1` | 0.2 | 0.9992 | discipline:information security, domain:user experience | domain:user experience |
| 19 | `554a22ebb2e5b9829eb343d6912a448d4eb396105c81a9a085fc673eaa0a0148` | 0.2 | 0.9992 | discipline:software engineering, domain:code & computation|media & entertainment | domain:media & entertainment |
| 20 | `402fa50814c912bfee490da199bb4587adc04a383837c3cc985ddf49de91ca8b` | 0.2 | 0.9992 | discipline:cultural studies, domain:engineering & infrastructure|legal & public policy | discipline:cultural studies, domain:engineering & infrastructure |
| 21 | `d6fe7483cc730356d854a0eb5b9cccc601499ce27875672b98dc1dbefc46177a` | 0.0 | 0.9991 | discipline:organizational theory, domain:education | domain:education |
| 22 | `35f42d8ca5bc1c4cb1fd97f87c7918cdbaa25c188178e0c28abfab14b98f2261` | 0.0 | 0.9991 | discipline:linguistics | discipline:linguistics |
| 23 | `4eaf655cb36e1d3f7292204930001a7cdfb16d61ddf1a6ce70d9d1ded3e228a1` | 0.0 | 0.9991 | discipline:economics | domain:engineering & infrastructure, domain:leadership |
| 24 | `3d484e37cf1ffc2d52351203745669998af0bc4c1c60d7b28886140899156611` | 0.0 | 0.9991 | discipline:philosophy, domain:health & wellness | domain:health & wellness |
| 25 | `b147a82b64686053fef559454ebd6cc0cc8199c506663756af4579b75519160a` | 0.1 | 0.9991 | discipline:philosophy, domain:social sciences | discipline:philosophy, domain:social sciences |
| 26 | `dd6bb15b6c947e76a6b0b981d3e6ba59874c267602480009c46db5014f8fb228` | 0.1 | 0.9991 | discipline:cultural studies, domain:brand identity|editorial & advertising | domain:brand identity, domain:editorial & advertising |
| 27 | `7d391e4c34671ac659d2badaa4143d1301187baecb0512a419efcd3f6a019419` | 0.0 | 0.999 | discipline:psychology, domain:user experience | discipline:psychology, domain:user experience |
| 28 | `7daa9d225677ad6891b36aa4548a44589259cd06ed648f41fea90ea15aa4aa0c` | 0.0 | 0.999 | discipline:research methodology, domain:health & wellness|project management|urban planning | discipline:research methodology, domain:health & wellness |
| 29 | `9f98c5fd5c652f4819adf5747c3ff8d29e7edde78f35a8edb8dbc5f5cdf7ed5a` | 0.0 | 0.999 | discipline:political economy | discipline:political economy |
| 30 | `6c98af237315fd0cde140d96771f21f9086ff0ad26582c3c708ff8a7425f192c` | 0.0 | 0.999 | discipline:game design | discipline:game design |
| 31 | `fad2d7486aa8e19a277c2c1c5bf3afc45f185f77a802afff6c7680c65fdd8481` | 0.0 | 0.999 | discipline:economics, domain:business operations|leadership | domain:leadership |
| 32 | `b4a1eb9457e8f093c7593f118c979678860104e18412ec671f521081f0b827c8` | 0.1 | 0.999 | discipline:design thinking, domain:education|leadership | discipline:design thinking, domain:education, domain:leadership |
| 33 | `1e5bf9207c96b77594342c70c85740fcdb3ad64a9b7573ba292cba80e4ea513d` | 0.1 | 0.999 | discipline:health & medicine, domain:education|health & wellness | domain:education |
| 34 | `1bf8fda07f7a237c65415cdbc300e1dbdefc871534bd77adfb86d8a6a4a1ee16` | 0.1 | 0.999 | domain:engineering practice|health & wellness|urban planning | domain:health & wellness, domain:urban planning |
| 35 | `13580ceac2467c8b150b0378289d8a799a6979f024f82b93792653a3b77e84b2` | 0.1 | 0.999 | discipline:performing arts, domain:education|graphic design | domain:education, domain:graphic design |
| 36 | `302fd361096382c01edc060ff1cce8bf93b6230204f1ba114f3c5e3c933d6a0d` | 0.1 | 0.999 | discipline:behavioral economics | discipline:behavioral economics, domain:environmental design, domain:product design |
| 37 | `a254e81bcea9a00ad65b590db3f73793576e2076d328d3dad75d7247930352b2` | 0.1 | 0.999 | discipline:research methodology | discipline:research methodology, domain:data visualization, domain:engineering & infrastructure, domain:leadership |
| 38 | `e0a16d5687ea5d5bbf2109aba2ee698704fe0e19100885527251839d8d14f387` | 0.1 | 0.999 | discipline:communication theory, domain:engineering & infrastructure | domain:engineering & infrastructure |
| 39 | `d0e2634eb710ebd43b27f01980501821552c4e7b5ae995b21084fcf74f87f9eb` | 0.1 | 0.999 | discipline:law, domain:engineering & infrastructure | domain:engineering & infrastructure |
| 40 | `881759b2c3c2f6cf36ec5c1a6a146b0a6ee242079dc222f128988cd94c3357f8` | 0.2 | 0.999 | discipline:anthropology, domain:health & wellness|personal productivity | domain:health & wellness, domain:personal productivity |
| 41 | `4a3b72f7b8740d83f27b0129a404436541867e1cb7ecabf065cdb510facefb0b` | 0.2 | 0.999 | domain:education|legal & public policy | domain:education, domain:legal & public policy |
| 42 | `0b00ce6bfcaa4f01dfb12fe49718dfad5f289e6b2b4c91e65ca4554fcb968b62` | 0.2 | 0.999 | discipline:cultural design, domain:engineering practice|urban planning | discipline:cultural design, domain:engineering practice |
| 43 | `59e10b16c55162734c219a55ca08c4e2acd4e9ca5e9f9f223c54794a6d91964d` | 0.2 | 0.999 | discipline:philosophy | discipline:philosophy, domain:engineering & infrastructure |
| 44 | `41815a5831e9d3573b7d73556c8ad281c5a0aaac0b1a25db170002ee252c3c19` | 0.0 | 0.9989 | discipline:information science | domain:engineering & infrastructure |
| 45 | `eff18efe43dd54d55de4b49d38f1bb0be9d81f92d76417ea11f62f67c04b1180` | 0.0 | 0.9989 | discipline:information science | discipline:information science, domain:education |
| 46 | `65f35199042cf1775f97c30a973db98b6195edc6b46ad68d70c6a33229d4d1bf` | 0.0 | 0.9989 | discipline:research methodology, domain:engineering & infrastructure|finance & investment | discipline:research methodology, domain:engineering & infrastructure, domain:finance & investment |
| 47 | `dd1b1430f8b974972288c6379d9a1d0e7f7e7c82a5c1bbb39d0b619a20fe521c` | 0.0 | 0.9989 | discipline:information science | domain:design strategy, domain:personal productivity |
| 48 | `071870f90e5dcf4eac7ce40a5a8ec97b7492520c83f16045c8ca18a18d75e131` | 0.0 | 0.9989 | discipline:software engineering | discipline:software engineering, domain:graphic design |
| 49 | `e7e317889a65313188350dcc4ac258644b570e4c0242bc2f2ce404acc8750ca6` | 0.0 | 0.9989 | discipline:game design | discipline:game design |
| 50 | `2f8185358632b9bf490cc74c24ed5d73cd61bc8387bab55a26e0b1d14bcc67d9` | 0.0 | 0.9989 | discipline:communication theory | discipline:communication theory, domain:brand identity, domain:product design |
