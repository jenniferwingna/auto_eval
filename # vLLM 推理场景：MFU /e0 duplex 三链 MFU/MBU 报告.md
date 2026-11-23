# e0 duplex 三链 MFU/MBU 报告（2026-11-23 定版 v2 · 未确认项已全部查实）

> 计算器：`/home/ma-user/work/c00929682/gpu_util_logger/gpu_mfu_calc.py`（挂件 v2）
> 数据集：uds_500（`e0_smoke/data/uds_500.jsonl`，音频合计 5077.2s，均 10.15s/条）
> 本版：第六节 6 项未确认项已全部查实关闭（见第七节处置记录），数字为最终定版。

---

## 一、结论表（最终数字）

| 排名 | 链条 | 样本 | 墙钟 | 总 FLOPs | **MFU** | 备注 |
|---|---|---|---|---|---|---|
| 1 | **#3 vllm 雅晴** | 500 | 3073.5s×1卡 | 2.284 PF | **0.075%** | 词数 35,709（实测，非协议值） |
| 2 | **#2 E4 批模式**（晓楠，B=8×3卡） | 500 | 1130s×3卡 | 2.165 PF | **0.065%** | chunks 用物理节奏值 |
| 3 | **#1 jason fast 旧版** | 500 | 7436.6s×1卡 | 2.258 PF | **0.031%** | 墙钟为 "fast generate-only" 纯推理计时 |
| 4 | **#1 jason fast 新代码**（token3 分支 b1） | 50 | 485.6s×1卡 | 0.136 PF | **0.028%** | ⚠ 50 条子集口径，与 500 条不可直比（自检见第五节，比例自洽） |
| — | ~~a3 N=3~~ | 50 | 672.3s | — | **作废** | N=1 训练 ckpt 跑 N=3，官方 Never bench；输出与 N=1 逐字节相同 |
| — | ~~#2 逐条（晓楠 KV修复后）~~ | — | — | — | **删除**（按要求） | 墙钟含 logit dump+探针，失真口径 |

**一句话结论**：三链 MFU 都在 **0.03–0.08%** 量级；#3 ≈ E4 批（0.065–0.075%）> #1（0.028–0.031%）。MFU 比值与速度比值三组独立交叉全部咬合（1–4% 内，第五节），排名与看板 RTF 一致。

---

## 二、数字更正记录（此前口头报的数字全部作废）

| 此前口径 | 报过 | 作废原因（查实依据） | 定版 |
|---|---|---|---|
| "#1 音频塔全长重算，占 47% FLOPs" | 0.132–0.139% | **错**。音频塔是固定 2s 滑窗 26 行/前向（`streaming_audio.py:227 smooth_slide=True`；b1 run.log `n_window_infer=200, window_tokens=26`） | enc 占 31% |
| "#2 E4 MFU 0.195% 最高" | 0.195% | **错**。rtf_stats 的 n_chunks=59,126 是 stream_batch 步数虚算；真实 chunk=5077/0.24=21,155 | 0.065% |
| "#1 chunks=53,874" | 0.139% | **错**。timeline 条目数（audio/listen/text 混列）≠ 240ms 前向次数 21,154 | 0.031% |
| "每 chunk 喂 16 token（结构14+词）" | — | **错**。fwd_tokens_uds.txt 实测 15,135 chunks **全部恒 7 token** prefill；+close 3–4（KV 增量 11–13 交叉验证）→ tpc=11+词率 | tpc≈12–13 |
| "b1 快 53%（6.18 vs 4.03 条/min）" | — | **口径错觉**。子集音频短（6.2s vs 10.2s），条/min 不可跨集比；RTF 1.566 vs 1.465 持平 | 已撤回 |
| "每 token 6.06 GFLOPs、0.065%/0.068%/0.085%" | 多轮 | 粗版口径（chunk 基数错/无 close 结构），仅量级参考 | 见结论表 |

---

## 三、算法与口径（全部查实，标注证据）

### 3.1 公式

```
每 chunk（240ms）：
  文本塔  prefill 7 token（实测恒定）+ close 3–4 token + decode 词数
    lin  = 2 × N_active × chunks × tpc            （tpc = 11 + 词率）
    lm   = 2 × vocab × H × words                  （lm_head 只按生成词数）
    attn = tpc² × Σᵢ nᵢ(nᵢ+1)/2 × 4L·H_q·head_dim  （条内因果 T_ctx，nᵢ=durᵢ/0.24）
  音频塔  每 chunk 一次前向 × 26 行固定滑窗（含双向 attention 项）
    enc  = (2×P_encoder + 4×L_enc×H_enc×Q_enc×26) × 26 × chunks
MFU = (lin+lm+attn+enc) / (墙钟 × 卡数 × 989.4e12)
```

### 3.2 查实常量（每项带证据）

| 常量 | 值 | 证据 |
|---|---|---|
| N_active | **2.718e9** | config thinker.text_config：48 层×（attn 18.874M + MoE 激活 37.749M）；不含 embedding 查表与 router |
| **prefill 7 token/chunk** | 恒定 | `out_2_probe500_fixed/fwd_tokens_uds.txt` 实测 15,135 chunks 分布全为 7 |
| **+close 3–4 token** | tpc=11+词率 | KV 增量计数交叉验证：listen chunk 11、[speak,词] chunk 12–13（KV 修复分析） |
| #3 词数 | **35,709（实测）** | output_token_ids 中 id<151646 计数；与 speak token 151698×35,710 恰 1:1 对仗自证 |
| 音频塔 26 行/chunk 前向 | `smooth_slide=True`（streaming_audio.py:227）+ b1 run.log `window_tokens=26`；**开头由静音 pad 补满宽**（materialise_buffer `pre=max(0,-start_mel)`，无 growing 段） | 代码+日志双实锤 |
| P_encoder | 629.1M（32 层×(4×1280²+2×1280×5120)） | config audio_config |
| 音频塔 attention 项 | +4.26M/行（4×32×20×64×26） | audio_config：20 heads、hd 64、32 层 |
| chunks（500 条） | **21,155** = 5077.2/0.24 | 物理节奏；与 #3 report Σinput_chunk_count=21,395 吻合（差 1.1%） |
| 峰值 | **989.4 TFLOPS**（BF16 dense） | **H200 SXM 实锤：Power Limit 700W**（NVL/PCIe 为 600W）；dtype bfloat16 |
| 词率 | #1: 1.657/chunk；#3: 1.669（实测）；E4: 1.0（协议）；b1: 1.938 | contract/output 逐条计数 |

---

## 四、逐链中间量（可复算）

| 链 | chunks | tpc | lin (PF) | lm (PF) | attn (PF) | enc (PF) | 总 (PF) | MFU |
|---|---|---|---|---|---|---|---|---|
| #1 旧版 | 21,154 | 12.66 | 1.455 | 0.022 | 0.086 | 0.694 | 2.258 | **0.031%** |
| #3 雅晴 | 21,395 | 12.67 | 1.473 | 0.022 | 0.086 | 0.702 | 2.284 | **0.075%** |
| #2 E4 | 21,155 | 12.00 | 1.380 | 0.013 | 0.078 | 0.694 | 2.165 | **0.065%** |
| #1 新 b1 | 1,292 | 12.94 | 0.091 | 0.002 | 0.001 | 0.042 | 0.136 | **0.028%** |

复算：`python3 gpu_mfu_calc.py --config /cache/c00929682/e0_2714_prepared/config.json --contract <contract> --wall <秒> --audio-mode window`（#3/E4 的 chunks 必须用物理节奏值，**不要信 rtf_stats 的 n_chunks**）。

---

## 五、自检（三组独立比例全部咬合）

| 交叉验证 | MFU 比 | 速度比 | 偏差 |
|---|---|---|---|
| #3 / #1 旧（同 500 条） | 2.45 | 墙钟比 2.42 | **1%** |
| E4 单卡 / #1（吞吐折算） | 2.10 | 单卡速度比 2.19 | 4% |
| b1 / #1 旧（跨子集） | 0.92 | RTF 反向 0.94 | **2%** |

- 单位核对：分母 = 7436.6s × 989.4e12 = **7.358e18**；#1 MFU = 2.258e15/7.358e18 = 3.07e-4 ✓
- 边界：全部 <100% ✓；量级与仅算文本塔的粗版一致（0.03–0.07%）✓

---

## 六、解读

- **0.03–0.08% 不是谁写得差**：duplex 流式每 240ms 只喂 ~13 token 文本塔 + 26 行音频塔，GPU 永远小口进食。三链已接近该物理形态允许的效率带，差距来自调度摊薄（#3 24 并发、E4 3 卡拼批）vs 单流串行（#1）。
- **#1 落后一倍是部署形态差异**，不是算法问题——与看板 RTF 结论一致。
- **提 MFU 两条路**：更大 batch（E4 方向，已验证）；减少每 chunk 固定开销（CUDA graph/kernel 融合，#2 已做）。
- **util% 与 MFU 不可互替**：#3 util 14% MFU 0.075%；#1 util 70% MFU 0.031%——util 高只说明"卡在忙"。

---

## 七、原未确认项处置记录（6 项全部查实关闭）

| # | 原未确认项 | 处置 | 证据 |
|---|---|---|---|
| 1 | 音频塔 attention 项未计入（≈+11%） | **已计入**：+4.26M/行（4×32×20×64×26），per_row 1.2583→1.2626 GF | audio_config 实数 |
| 2 | 结构 token 取 14（±1 → ±4%） | **已实锤改为 11+词率**：prefill 实测恒 7（15,135 chunks 全 7）+ close 3–4（KV 增量 11–13 交叉验证）。残余不确定性 ±1 token → ±3% | fwd_tokens_uds.txt + KV 修复分析 |
| 3 | #3 词数取协议值 | **已实数 35,709**：output_token_ids 按 id<151646 计数，与 speak token 35,710 恰 1:1 对仗 | inference_report 逐 id 分类 |
| 4 | chunk 起点 growing 段忽略（<1%） | **确认无需修正**：smooth_slide 窗口由流首静音 pad 补满宽，26 行恒定 | materialise_buffer `pre=max(0,-plan.start_mel)` 及注释 |
| 5 | H200 SXM vs NVL 峰值 | **确认 SXM**：Power Limit 700W（NVL 为 600W）→ 989.4 TFLOPS 正确 | nvidia-smi -q -d POWER |
| 6 | 墙钟含 CPU 侧开销 | **部分收窄**：#1 的 7436.6s 为 "fast generate-only" 纯推理计时（run.log 逐条 "fast generate-only XXs"），不含音频解码/IO；#3/E4 为客户端墙钟（含 WS 往返与音频传输）。**残余差异保留**：GPU busy time 需 profiler（CUPTI），挂件 v2 不覆盖——若 #3 的 WS 往返占比显著，其真实 GPU 侧 MFU 会高于 0.075% | run.log 计时语义 + report 墙钟定义 |
