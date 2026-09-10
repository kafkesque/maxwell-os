# GOLDEN SOURCE MAP (D2585 P5 Step 1)

**1027 examples** → 1027 with fb_id → 1027 in DB.
Provenance present on 1027 (100%); books 1027 (100%); authors 1027 (100%).

- distinct authors: 773 | distinct books: 914
- authors spanning >1 golden example: 741
- books spanning >1 golden example: 859

**Shared authors** (book/author-disjointness constraint):

- `string` (97 examples)
- `Marcel Danesi` (78 examples)
- `Anonymous` (77 examples)
- `Marcel Danesi Ph. D.` (62 examples)
- `Various` (55 examples)
- `Chip Huyen` (48 examples)
- `Rob Thomas, Paul Zikopoulos, Kate Soule` (47 examples)
- `Rex Hartson, Pardha S Pyla` (45 examples)
- `Martin Kunc` (43 examples)
- `Philip Kotler, Kevin Lane Keller, Alexander Chernev, Jagdish N. Sheth, G. Shainesh` (42 examples)

**Shared books**:

- `[Marcel_Danesi_Ph._D.]_Messages,_Signs,_and_Meanin(z-lib.org).md` (62 examples)
- `The UX book process and guidelines for ensuring a quality user experience Hartson, Rex_Pyla, Pardha S liber3.md` (45 examples)
- `AI Value Creators (Rob Thomas, Paul Zikopoulos, Kate Soule) (z-library.sk, 1lib.sk, z-lib.sk).md` (45 examples)
- `[Marcel_Danesi_(auth.)]_Of_Cigarettes,_High_Heels,(z-lib.org).md` (44 examples)
- `Strategic Analytics (Martin Kunc) (z-library.sk, 1lib.sk, z-lib.sk).md` (43 examples)
- `AI Value Creators Beyond the Generative AI User Mindset (Rob Thomas, Paul Zikopoulos, Kate Soule) (z-library.sk, 1lib.sk, z-lib.sk).md` (43 examples)
- `[Marcel_Danesi]_The_Quest_for_Meaning__A_Guide_to_(z-lib.org).md` (43 examples)
- `Marketing Management 16th Edition Paperback -- Kotler,philip & keller lane, kevin & N_ seth, Jagdish & -- 16th, 2022 -- Pearson India Education -- isbn13 9789356062665 -- da2a9abaab3f94f052564b00a563b198 -- Anna’s Archive.md` (42 examples)
- `Semiotics The Basics Daniel Chandler liber3.md` (42 examples)
- `Seeking Wisdom_ From Darwin to Munger, 3rd Edition -- Bevelin, Peter -- Third edition, 2018_2007 -- PCA Publications L_L_C__ PCA Publications -- 9781578644285 -- fc29e83e825ec3045c15f31e225e2324 -- Anna’s Archive.md` (40 examples)

## Author cleaning (P5 Step 2)

- junk author values dropped: **235**
- alias duplicates merged: **64**
- examples with >=1 clean author: **1026/1027**
- distinct clean authors: **767**
