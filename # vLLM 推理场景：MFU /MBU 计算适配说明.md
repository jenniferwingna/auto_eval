# vLLM 推理场景：MFU / MBU 计算适配说明

> 交付对象：负责适配的 agent。
> 目标：在现有评测框架（用 vLLM 跑推理）里，加上 MFU 和 MBU 的计算与上报，用来诊断"评测跑得慢，慢在哪"。
> 原则：**凡是标注"需确认"的项，先去代码、配置或日志里查实，不要凭默认值假设。** 查不到的，写进最终报告的"未确认项"，不要编造。

---

## 1. 术语定义

| 术语 | 全称 | 含义 |
|---|---|---|
| FLOPs | Floating Point Operations | 浮点运算次数，衡量"计算量"。注意与 FLOPS（每秒浮点运算次数，衡量硬件速度）区分 |
| MFU | Model FLOPs Utilization | 模型算力利用率：模型本来就该做的计算，占硬件理论峰值算力的比例 |
| HFU | Hardware FLOPs Utilization | 硬件算力利用率：GPU 实际执行的计算（含重计算等额外开销）占峰值的比例。**本任务不算 HFU** |
| MBU | Model Bandwidth Utilization | 显存带宽利用率：每秒实际从显存读取的数据量，占显存带宽峰值的比例 |
| Prefill | 预填充 | 把整段输入一次性送入模型，计算受算力限制（compute-bound） |
| Decode | 解码 | 每步生成一个 token，每步都要读取全部权重，受显存带宽限制（memory-bound） |
| Continuous batching | 连续批处理 | vLLM 默认机制，不同请求动态拼进同一个 batch |
| Prefix caching | 前缀缓存 | 命中缓存的输入 token 不重新计算 |
| Chunked prefill | 分块预填充 | 把长 prefill 切块，与 decode 混在同一个调度步里 |
| GQA | Grouped-Query Attention | 分组查询注意力，KV 头数少于 Query 头数，影响 KV cache 大小 |

**为什么要分开看两个指标**：prefill 阶段瓶颈在算力，看 MFU 有意义；decode 阶段瓶颈在带宽，MFU 天然很低（个位数很常见），应看 MBU。把两阶段混成一个 MFU，会被耗时占比大的阶段主导，看不出问题。

---

## 2. 算法

### 2.1 MFU

```
MFU = (每 token 的模型 FLOPs × 有效 token 数 / 耗时) / (GPU 数 × 单卡峰值 FLOPs)
```

**每 token 的模型 FLOPs（仅前向，推理用）**：

```
flops_per_token = 2 × N_active + 4 × L × H × Q × T_ctx
```

- `N_active`：参与矩阵乘法的参数量。稠密模型取总参数量，但**不含输入 embedding 查表**（查表不是矩阵乘法），**含 lm_head**；MoE 模型取每个 token 实际激活的参数量，不是总参数量
- `L`：层数；`H`：Query 头数；`Q`：每个头的维度
- `T_ctx`：该 token 看到的上下文长度（见 2.3 的口径选择）
- 第一项是线性层（矩阵乘法），第二项是注意力本身（QK^T 和 AV）。公式来源：PaLM 论文附录的训练公式去掉反向部分（训练是 `6N + 12LHQT`，前向占其中的 1/3）

**多模态/音频模型**：编码器（音频或视觉部分）的 FLOPs 要单独按其结构计算，再与语言模型部分相加，**不能只用语言模型的参数量**。编码器每个样本的计算量通常与输入长度有关（如音频时长），需要按样本累加。

### 2.2 MBU

```
MBU = (每个 decode 步读取的字节数 × 每秒 decode 步数) / (GPU 数 × 单卡显存带宽峰值)

每步读取字节数 = 权重字节数 + 本步所有并发序列的 KV cache 读取字节数
权重字节数     = 参数量 × 每参数字节数（BF16=2，FP8=1，INT4≈0.5）
单序列 KV 字节 = 2 × L × n_kv_heads × head_dim × 每元素字节数 × 当前上下文长度
```

- 单位是 **decode 步**，不是 token。一步里 batch 内每条序列各出一个 token，权重只读一次
- 开张量并行（tensor parallel）时，每张卡只存一部分权重，权重和 KV 的字节数、GPU 数在分子分母必须**同口径**（要么都按全局算，要么都按单卡算）
- MoE 模型：一个 batch 内不同 token 会路由到不同专家，每步实际读取的权重量介于"激活参数"和"全部参数"之间，**精确计算较复杂，先给出上下界，不要给单一精确值**
- KV 大小用 `n_kv_heads`（GQA 下小于 Query 头数 H），不是 H

### 2.3 口径选择（必须在输出里写明用了哪种）

注意力项的上下文长度 `T_ctx` 有两种口径：

- **保守口径**（与 PaLM 公式一致）：prefill 时所有 token 都按完整长度 T 算
- **因果口径**：因为 causal mask，prefill 中第 i 个 token 只看前 i 个，平均上下文约 T/2

两种口径差异只体现在注意力项，输入很长时差距才明显。**默认用因果口径，并在报告里注明**；decode 阶段 `T_ctx` 取当前已有的上下文长度（输入 + 已生成），用平均值估算即可。

---

## 3. 需要确认的事项（按优先级）

对每一项，先查实，再按"如果…就…"处理。

### 3.1 硬件与精度

| 需确认 | 如果是 A | 如果是 B |
|---|---|---|
| GPU 型号 | 查官方规格表取 **dense（稠密）** 峰值，**不要用带 sparsity 的数字**。参考量级：A100 BF16 约 312 TFLOPs、显存带宽约 2039 GB/s（80G 版）；H100 SXM BF16 约 989 TFLOPs、带宽约 3350 GB/s。**这些仅为量级参考，必须以官方规格表核对后写进配置** | 型号不在已知列表：不要猜，写进"未确认项"，让使用者手填 |
| 推理精度（dtype / 量化） | BF16/FP16：用 BF16/FP16 峰值，权重每参数 2 字节 | FP8/INT8/INT4：峰值和字节数都要按对应精度换；注意量化后实际计算可能仍在更高精度下进行（反量化），**需查 vLLM 实际用的 kernel，不能只看配置名**；无法确认时 MFU 用 BF16 峰值作保守值并注明 |
| GPU 数与并行方式（tensor / pipeline / data parallel） | 纯 tensor parallel：GPU 数 = tp_size，吞吐为全局吞吐 | 有 data parallel：先确认吞吐是单副本还是多副本合计，分母 GPU 数要与分子对应 |

### 3.2 模型结构

| 需确认 | 如果是 A | 如果是 B |
|---|---|---|
| 从模型的 `config.json` 读取：层数、Query 头数、head_dim、n_kv_heads、hidden_size、intermediate_size、vocab_size | 全部读到：直接代入 | 缺字段：写进"未确认项"，不要用默认值补 |
| 是否 MoE | 稠密：`N_active` = 总参数量（扣除输入 embedding） | MoE：读取每 token 激活的专家数和专家大小，自行计算 `N_active`；MBU 给上下界 |
| 是否多模态/音频 | 纯文本：只算语言模型 | 有编码器：单独计算编码器 FLOPs，按每个样本的输入长度累加，并**在报告里分项列出**（编码器 / 语言模型） |
| 参数量怎么得到 | 优先从加载后的模型对象统计（`sum(p.numel())`），再扣除输入 embedding | 无法加载：从 config 按结构公式推算，并与模型卡标称值交叉核对 |

### 3.3 vLLM 运行配置

| 需确认 | 如果是 A | 如果是 B |
|---|---|---|
| vLLM 版本（V0 / V1 引擎） | 不同版本的 metrics 名称和 `RequestOutput` 里可用的时间字段不同，**先确认版本，再去查该版本实际暴露了哪些指标**，不要照搬其他版本的字段名 | — |
| 该版本是否已自带 MFU 或类似指标 | 有：先拿来与自己的计算**交叉对比**，口径不同时以本文档口径为准并说明差异 | 没有：自行计算 |
| 是否开启 prefix caching | 开启：必须取每个请求的"命中缓存 token 数"，**从 prefill 有效 token 中扣除**，否则 MFU 虚高。若该版本取不到命中数：关掉 prefix caching 重跑一次作为 MFU 测量口径，或在报告里明确标注"含缓存命中，MFU 不可靠" | 关闭：无需处理 |
| 是否开启 chunked prefill | 开启：prefill 和 decode 混在同一调度步，**无法按"步"干净地区分阶段**。改用 3.5 里的"两次测量法" | 关闭：可直接按阶段区分 |
| 是否开启 speculative decoding | 开启：被拒绝的草稿 token 消耗了算力但不是有效产出，分子只算最终采纳的 token；额外的草稿模型 FLOPs 单独记录 | 关闭：无需处理 |
| 是否有 padding | vLLM 正常调度下通常没有 padding，但如果评测框架在外层自行补齐了输入，要扣除 | 无：无需处理 |
| 是否开启 CUDA graph / `enforce_eager` | 开启 CUDA graph：首次捕获有一次性开销，计时必须排除 | — |

### 3.4 评测框架侧

| 需确认 | 如果是 A | 如果是 B |
|---|---|---|
| 评测数据的输入长度分布与输出长度分布 | 取均值、P50、P95 和最大值，写进报告。输入长、输出短（如打分、分类类）→ prefill 主导，重点报 MFU；输出长 → decode 主导，重点报 MBU | 分布未知：先统计，不要假设 |
| 并发方式（离线 `LLM.generate` 批量，还是在线 server 加并发请求） | 离线批量：用请求级别的时间戳和总耗时 | 在线 server：并发数决定了 batch size，**必须把并发数写进报告**，MBU 随它变化很大 |
| 总耗时里包含哪些 CPU 侧开销（tokenize、音频预处理、请求排队、结果写盘） | 能区分：分别记录"端到端耗时"和"GPU 忙碌耗时" | 不能区分：只报端到端 MFU，并注明它包含 CPU 侧开销，是下界 |

### 3.5 分阶段测量方法（chunked prefill 开启或无法按步区分时）

**两次测量法**（近似，需在报告里说明其近似性）：

1. **Prefill 测量**：对同一批请求，设 `max_tokens=1` 跑一遍，耗时近似为纯 prefill 耗时。此时 prefill 有效 token 数 = 输入 token 数 − 缓存命中数
2. **Decode 测量**：正常跑完整请求，总耗时减去上一步的 prefill 耗时，得到 decode 耗时；decode 步数近似为"总生成 token 数 / 平均并发序列数"

近似点：`max_tokens=1` 仍包含 1 步 decode；两次运行间有调度差异。对 MFU/MBU 的诊断用途来说精度够用，但不要把它当精确值。

---

## 4. 实现骨架

```python
def flops_per_token_fwd(n_active, n_layers, n_heads, head_dim, ctx_len):
    """仅前向。ctx_len 的口径见文档 2.3。"""
    return 2 * n_active + 4 * n_layers * n_heads * head_dim * ctx_len


def mfu(flops_per_token, effective_tokens, seconds, n_gpus, peak_tflops_per_gpu):
    achieved = flops_per_token * effective_tokens / seconds
    return achieved / (n_gpus * peak_tflops_per_gpu * 1e12)


def kv_bytes_per_seq(n_layers, n_kv_heads, head_dim, ctx_len, bytes_per_elem):
    return 2 * n_layers * n_kv_heads * head_dim * bytes_per_elem * ctx_len


def mbu(weight_bytes, kv_bytes_all_seqs, decode_steps, seconds,
        n_gpus, peak_bw_gb_per_gpu):
    bytes_per_step = weight_bytes + kv_bytes_all_seqs
    bytes_per_sec = bytes_per_step * decode_steps / seconds
    return bytes_per_sec / (n_gpus * peak_bw_gb_per_gpu * 1e9)
```

**实现要点**：

- prefill 的 `flops_per_token` 因注意力项依赖上下文长度，**按请求逐个计算再求和**，不要用单一平均值乘总 token 数（输入长度方差大时误差明显）
- 计时在稳定运行阶段取，排除模型加载、预热、CUDA graph 捕获；GPU 侧计时前后用 `torch.cuda.synchronize()`
- 所有配置项（峰值、字节数、口径选择）放进一个配置文件，**不要写死在计算函数里**

---

## 5. 输出格式要求

每次评测运行，输出一份下面格式的记录（JSON 或表格均可），**以下字段缺一不可**，缺失的写 `null` 并说明原因：

```
运行配置：模型名、vLLM 版本、dtype/量化、GPU 型号与数量、并行方式、
          是否开启 prefix caching / chunked prefill / speculative decoding、并发数
数据特征：样本数、输入 token 数（均值/P50/P95/最大）、输出 token 数（同上）、
          prefix 缓存命中 token 数
测量结果：
  - prefill：有效 token 数、耗时、MFU
  - decode：步数、耗时、平均 batch size、MBU
  - 端到端：总耗时、总吞吐（tokens/s）、端到端 MFU
  - 多模态：编码器 FLOPs 与语言模型 FLOPs 分项
口径声明：注意力项用保守口径还是因果口径；MFU 分子用的是理论 FLOPs 还是实测 FLOPs
未确认项：列出所有没能查实、使用了假设的项
```

---

## 6. 自检（实现完成后必须做）

1. **手算核对**：任选一个请求，手工算出 FLOPs 和字节数，与代码输出比对，误差应在几个百分点内。
   示例（仅为算术核对，非实测）：稠密 7B 模型 BF16，忽略注意力项，每 token 前向约 `2 × 7e9 = 14 GFLOPs`。一个 2000 token 的 prefill 约 28 TFLOPs，在 312 TFLOPs 峰值的卡上，理想耗时约 0.09 秒；若实测 0.2 秒，则 MFU 约 45%。
   同模型 decode：权重 14 GB，在 2039 GB/s 带宽下，仅读权重一遍理想耗时约 6.9 ms；若实测每步 10 ms（忽略 KV），MBU 约 69%。
2. **合理性边界**：MFU 和 MBU 都不应超过 100%。超过说明分子口径错了（常见原因：把缓存命中 token 算进去了、峰值取错了精度、GPU 数对不上）。
3. **趋势核对**：增大并发或 batch size 后，decode 的 MBU 应上升（因为权重读取开销被摊薄）；如果不升反降，检查是否被调度或 CPU 侧瓶颈限制。
4. **与 vLLM 自带指标交叉对比**：若 3.3 中确认该版本有自带指标，两者应在同一量级，差异需要能用口径不同解释。

---

## 7. 解读指引（写进报告结论部分）

| 现象 | 可能的含义 | 下一步 |
|---|---|---|
| prefill MFU 低（远低于 40%） | 输入太短、batch 太小、编码器或 CPU 预处理拖后腿、attention kernel 不理想 | 看 GPU 忙碌耗时 vs 端到端耗时，判断瓶颈是否在 GPU 上 |
| decode MFU 低但 MBU 高 | 正常，已接近带宽极限 | 想继续提速只能减少字节数（量化）或增大 batch |
| decode MBU 低 | batch 太小、KV cache 管理低效、调度开销大 | 提高并发，检查 `max_num_seqs` 与 GPU 显存利用率配置 |
| 端到端 MFU 远低于 GPU 侧 MFU | CPU 侧开销大（tokenize、音频解码、写盘） | 优化数据流水线，而不是 GPU 侧 |
| 数值 > 100% | 口径错误 | 回到第 6 节自检 |

**注意**：评测场景下，MFU/MBU 是诊断工具，不是目标。如果整体耗时（GPU 小时）已经可接受，不需要为了让数字好看而继续优化。
