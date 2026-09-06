# LF DEPENDENCY AUDIT — Step 3A (D2585 P1)

| Metric | Value |
|---|---|
| T-NLI discipline FBs | 7068 |
| cleanlab assessed FBs | 7236 |
| cleanlab flagged FBs | 3422 (0.4873) |

## 2x2 dependence — T-NLI contradiction vs cleanlab

| Cell | Count |
|---|---|
| both flag | 532 |
| cleanlab only | 2890 |
| NLI only | 342 |
| neither | 3278 |

| Stat | Contradiction | Weak |
|---|---|---|
| phi | 0.0925 | 0.0976 |
| kappa | 0.0623 | 0.0961 |
| agreement | 0.541 | 0.5462 |
| P(cleanlab\|NLI) | 0.6087 | 0.5279 |
| P(cleanlab\|~NLI) | 0.4685 | 0.4292 |

**Verdict:** near-independent (phi = 0.0925).

## Top labels targeted by both LFs

| Label | n | cleanlab | NLI | both |
|---|---|---|---|---|
| philosophy | 189 | 133 | 63 | 48 |
| behavioral economics | 235 | 150 | 24 | 11 |
| political economy | 184 | 118 | 54 | 35 |
| research methodology | 264 | 97 | 54 | 35 |
| human-computer interaction | 364 | 102 | 52 | 29 |
| software engineering | 317 | 115 | 25 | 14 |
| cognitive science | 129 | 112 | 16 | 12 |
| health & medicine | 126 | 101 | 23 | 22 |
| design thinking | 171 | 107 | 15 | 14 |
| communication theory | 173 | 112 | 14 | 9 |
| operations research | 144 | 98 | 25 | 17 |
| creative process | 115 | 84 | 43 | 31 |
| cultural design | 262 | 72 | 115 | 41 |
| media studies | 150 | 91 | 24 | 19 |
| economics | 171 | 104 | 6 | 5 |
