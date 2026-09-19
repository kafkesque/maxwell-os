# MODEL EVALUATION — oMLX, temperature 0.0, identical system prompts
  (119 checkpoint rows excluded as INVALID ITEMS — bad gold, see INVALID_ITEM_IDS / BUG-253)

model                                stability toolcalli  planning reviewing  hardcode      mbpp humaneval  mmlu_pro     gsm8k   math500    ifeval lc_reason      niah
----------------------------------------------------------------------------------------------------------------------------------------------------------------------
Ornith-1.5-35B-A3B-REAP-19B                0.2       0.6      0.79      0.83       1.0       0.6      0.56        --        --        --      0.84       0.5       1.0
Ornith-1.5-9B-MLX-8bit                     0.3       0.3      0.79      0.83       1.0      0.52       0.8      0.12      0.96      0.68      0.92      0.83      0.44
Phi-4-mini-instruct-8bit                   0.5       0.4      0.79      0.83       0.5      0.48      0.52        --        --        --      0.92        --        --
Qwen3-Coder-30B-A3B-Instruct-MLX-4b        0.5       0.7      0.71      0.83       1.0      0.68       0.8        --        --        --      0.96       0.0       1.0
Qwen3.8-27B-MLX-4bit                       0.6       0.6      0.75       1.0       1.0      0.56      0.96        --        --        --       1.0       1.0       1.0
gemma-4-E4B-it-MLX-4bit                    0.7      0.55      0.71      0.83       0.5      0.44      0.16        --        --        --       1.0       0.0       1.0
gpt-oss-20b-MXFP4-Q8                       0.2       0.0      0.79      0.83       1.0      0.56      0.88        --        --        --      0.88        --        --

Per-suite detail (n, median latency s, transport errors)
------------------------------------------------------------------------------
  Ornith-1.5-35B-A3B-REAP-19B        stability     acc=0.2    n=30   med=1.2    s
  Ornith-1.5-35B-A3B-REAP-19B        toolcalling   acc=0.6    n=20   med=2.8    s
  Ornith-1.5-35B-A3B-REAP-19B        planning      acc=0.792  n=24   med=15.0   s
  Ornith-1.5-35B-A3B-REAP-19B        reviewing     acc=0.833  n=6    med=4.7    s
  Ornith-1.5-35B-A3B-REAP-19B        hardcode      acc=1.0    n=4    med=5.8    s
  Ornith-1.5-35B-A3B-REAP-19B        mbpp          acc=0.6    n=25   med=3.4    s
  Ornith-1.5-35B-A3B-REAP-19B        humaneval     acc=0.56   n=25   med=8.5    s
  Ornith-1.5-35B-A3B-REAP-19B        ifeval        acc=0.84   n=25   med=11.6   s
  Ornith-1.5-35B-A3B-REAP-19B        lc_reasoning  acc=0.5    n=6    med=83.3   s
  Ornith-1.5-35B-A3B-REAP-19B        niah          acc=1.0    n=15   med=69.4   s
  Ornith-1.5-9B-MLX-8bit             stability     acc=0.3    n=30   med=2.3    s
  Ornith-1.5-9B-MLX-8bit             toolcalling   acc=0.3    n=20   med=5.2    s
  Ornith-1.5-9B-MLX-8bit             planning      acc=0.792  n=24   med=29.9   s
  Ornith-1.5-9B-MLX-8bit             reviewing     acc=0.833  n=6    med=9.5    s
  Ornith-1.5-9B-MLX-8bit             hardcode      acc=1.0    n=4    med=15.6   s
  Ornith-1.5-9B-MLX-8bit             mbpp          acc=0.52   n=25   med=5.6    s
  Ornith-1.5-9B-MLX-8bit             humaneval     acc=0.8    n=25   med=18.3   s
  Ornith-1.5-9B-MLX-8bit             mmlu_pro      acc=0.12   n=25   med=40.9   s
  Ornith-1.5-9B-MLX-8bit             gsm8k         acc=0.96   n=25   med=17.9   s
  Ornith-1.5-9B-MLX-8bit             math500       acc=0.68   n=25   med=25.4   s
  Ornith-1.5-9B-MLX-8bit             ifeval        acc=0.92   n=25   med=19.3   s
  Ornith-1.5-9B-MLX-8bit             lc_reasoning  acc=0.833  n=6    med=165.1  s
  Ornith-1.5-9B-MLX-8bit             niah          acc=0.444  n=9    med=92.2   s
  Phi-4-mini-instruct-8bit           stability     acc=0.5    n=30   med=0.3    s
  Phi-4-mini-instruct-8bit           toolcalling   acc=0.4    n=20   med=1.3    s
  Phi-4-mini-instruct-8bit           planning      acc=0.792  n=24   med=4.0    s
  Phi-4-mini-instruct-8bit           reviewing     acc=0.833  n=6    med=0.8    s
  Phi-4-mini-instruct-8bit           hardcode      acc=0.5    n=4    med=3.5    s
  Phi-4-mini-instruct-8bit           mbpp          acc=0.48   n=25   med=1.3    s
  Phi-4-mini-instruct-8bit           humaneval     acc=0.52   n=25   med=1.7    s
  Phi-4-mini-instruct-8bit           ifeval        acc=0.92   n=25   med=3.2    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 stability     acc=0.5    n=30   med=0.6    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 toolcalling   acc=0.7    n=20   med=1.8    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 planning      acc=0.708  n=24   med=10.2   s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 reviewing     acc=0.833  n=6    med=1.8    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 hardcode      acc=1.0    n=4    med=3.7    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 mbpp          acc=0.68   n=25   med=1.6    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 humaneval     acc=0.8    n=25   med=3.6    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 ifeval        acc=0.96   n=25   med=3.7    s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 lc_reasoning  acc=0.0    n=6    med=130.7  s
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 niah          acc=1.0    n=9    med=54.3   s
  Qwen3.8-27B-MLX-4bit               stability     acc=0.6    n=30   med=2.3    s
  Qwen3.8-27B-MLX-4bit               toolcalling   acc=0.6    n=20   med=7.5    s
  Qwen3.8-27B-MLX-4bit               planning      acc=0.75   n=24   med=58.5   s
  Qwen3.8-27B-MLX-4bit               reviewing     acc=1.0    n=6    med=6.4    s
  Qwen3.8-27B-MLX-4bit               hardcode      acc=1.0    n=4    med=18.6   s
  Qwen3.8-27B-MLX-4bit               mbpp          acc=0.56   n=25   med=8.0    s
  Qwen3.8-27B-MLX-4bit               humaneval     acc=0.96   n=25   med=19.0   s
  Qwen3.8-27B-MLX-4bit               ifeval        acc=1.0    n=25   med=16.7   s
  Qwen3.8-27B-MLX-4bit               lc_reasoning  acc=1.0    n=6    med=361.5  s
  Qwen3.8-27B-MLX-4bit               niah          acc=1.0    n=15   med=275.3  s
  gemma-4-E4B-it-MLX-4bit            stability     acc=0.7    n=30   med=0.5    s
  gemma-4-E4B-it-MLX-4bit            toolcalling   acc=0.55   n=20   med=1.9    s
  gemma-4-E4B-it-MLX-4bit            planning      acc=0.708  n=24   med=18.0   s
  gemma-4-E4B-it-MLX-4bit            reviewing     acc=0.833  n=6    med=1.0    s
  gemma-4-E4B-it-MLX-4bit            hardcode      acc=0.5    n=4    med=4.7    s
  gemma-4-E4B-it-MLX-4bit            mbpp          acc=0.44   n=25   med=1.9    s
  gemma-4-E4B-it-MLX-4bit            humaneval     acc=0.16   n=25   med=3.3    s
  gemma-4-E4B-it-MLX-4bit            ifeval        acc=1.0    n=25   med=1.9    s
  gemma-4-E4B-it-MLX-4bit            lc_reasoning  acc=0.0    n=6    med=47.2   s
  gemma-4-E4B-it-MLX-4bit            niah          acc=1.0    n=9    med=17.9   s
  gpt-oss-20b-MXFP4-Q8               stability     acc=0.2    n=30   med=1.4    s
  gpt-oss-20b-MXFP4-Q8               toolcalling   acc=0.0    n=20   med=2.8    s
  gpt-oss-20b-MXFP4-Q8               planning      acc=0.792  n=24   med=10.4   s
  gpt-oss-20b-MXFP4-Q8               reviewing     acc=0.833  n=6    med=4.8    s
  gpt-oss-20b-MXFP4-Q8               hardcode      acc=1.0    n=4    med=8.0    s
  gpt-oss-20b-MXFP4-Q8               mbpp          acc=0.56   n=25   med=5.6    s
  gpt-oss-20b-MXFP4-Q8               humaneval     acc=0.88   n=25   med=8.4    s
  gpt-oss-20b-MXFP4-Q8               ifeval        acc=0.88   n=25   med=12.4   s

Long-context — niah (by prompt size; n in brackets; errors excluded)
------------------------------------------------------------------------------
model                                    4000tok      12000tok      16000tok      24000tok      32000tok
--------------------------------------------------------------------------------------------------------
Ornith-1.5-35B-A3B-REAP-19B              1.0 (3)       1.0 (3)       1.0 (3)       1.0 (3)       1.0 (3)
Ornith-1.5-9B-MLX-8bit                   1.0 (3)      0.33 (3)            --       0.0 (3)            --
Qwen3-Coder-30B-A3B-Instruct-MLX-        1.0 (3)       1.0 (3)       1.0 (3)            --            --
Qwen3.8-27B-MLX-4bit                     1.0 (3)       1.0 (3)       1.0 (3)       1.0 (3)       1.0 (3)
gemma-4-E4B-it-MLX-4bit                  1.0 (3)       1.0 (3)       1.0 (3)            --            --

Long-context — lc_reasoning (by prompt size; n in brackets; errors excluded)
------------------------------------------------------------------------------
model                                   16000tok
------------------------------------------------
Ornith-1.5-35B-A3B-REAP-19B              0.5 (6)
Ornith-1.5-9B-MLX-8bit                  0.83 (6)
Qwen3-Coder-30B-A3B-Instruct-MLX-        0.0 (6)
Qwen3.8-27B-MLX-4bit                     1.0 (6)
gemma-4-E4B-it-MLX-4bit                  0.0 (6)

Stability — self-agreement across 3 identical repeats
------------------------------------------------------------------------------
  Ornith-1.5-35B-A3B-REAP-19B        unanimous 10/10
  Ornith-1.5-9B-MLX-8bit             unanimous 10/10
  Phi-4-mini-instruct-8bit           unanimous 10/10
  Qwen3-Coder-30B-A3B-Instruct-MLX-4 unanimous 10/10
  Qwen3.8-27B-MLX-4bit               unanimous 10/10
  gemma-4-E4B-it-MLX-4bit            unanimous 10/10
  gpt-oss-20b-MXFP4-Q8               unanimous 10/10

PRUNED — historical rows only, NOT in the portfolio (do not quote as a candidate)
------------------------------------------------------------------------------
  Ornith-1.5-9B-OptiQ-4bit           rows=197   transport_err=15   suites=stability,toolcalling,planning,reviewing,hardcode,mbpp,humaneval,mmlu_pro,gsm8k,math500,ifeval
  Qwen3.8-27B-OptiQ-4bit             rows=0     transport_err=0    suites=
  gemma-4-12B-it-qat-OptiQ-4bit      rows=122   transport_err=0    suites=stability,toolcalling,planning,reviewing,hardcode,mbpp,humaneval,ifeval
  granite-4.2-8b-MLX-8bit            rows=116   transport_err=0    suites=stability,toolcalling,planning,hardcode,mbpp,humaneval,ifeval
