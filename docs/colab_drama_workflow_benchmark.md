# Google Colab L4 短剧全流程实测基准与使用记录 (Benchmark & Ops)

本文档记录了在 Google Colab L4 (24GB) 算力实例上，首次完整跑通 LoPy 4 镜都市短剧《离职底牌》从**大模型高速拉取、锁衣首帧生图、4 镜 MiniMax H3 视频渲染、素材回传到实例自动销毁**的实测数据、算力消耗与工程踩坑经验。

---

## 一、 核心执行与算力消耗总结 (Executive Summary)

* **硬件规格**：Google Colab **NVIDIA L4 (24GB GDDR6 VRAM)**，宿主机 62GB 内存，150GB 本地 NVMe 磁盘。
* **算力消耗**：
  - 任务启动前余额：约 **597.00 CUs**
  - 全部完成释放后余额：**593.88 CUs**
  - **全套 4 镜短剧实际净消耗**：仅 **~3.12 个算力点 (Compute Units)**
  - **闲置防护**：渲染产物落盘后即刻触发 `colab stop`，计费速率实时归零（`Usage rate: 0.00/hr`），无任何多余扣费。
* **总产出资产**：
  - 4 个 9:16 竖屏（768×1344 @ 24fps）独立对白与动态口型视频（总计 462 帧，净时长 19.30 秒）。
  - 本地混音混流与双层中文字幕压制成片（`runtime/outputs/drama_workplace_v1.mp4`，8.12 MB）。

---

## 二、 分阶段耗时与性能实测指标 (Detailed Metrics)

### 1. 60GB 模型极速并发下载（aria2c 16 线程）

依托 Google Cloud 数据中心内部高带宽，利用 `aria2c -c -x 16 -s 16` 直连 Hugging Face 官方开放权重：

| 模型名称 | 文件规格 | 平均下载带宽 | 实测耗时 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `minimax_h3_image_pruned_int8_convrot.safetensors` | 19.54 GB | **342 MB/s** | **60.4 秒** | H3 图像扩散模型 |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 14.61 GB | **363 MB/s** | **44.4 秒** | 32B 文本/多模态编码器 |
| `minimax_h3_image_vae_fp16.safetensors` | 1.09 GB | **292 MB/s** | **5.7 秒** | 图像 VAE |
| `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | 19.53 GB | **345 MB/s** | **59.8 秒** | H3 音视同步扩散模型 |
| `minimax_h3_video_vae_fp16.safetensors` | 4.85 GB | **310 MB/s** | **16.3 秒** | 视频 VAE 解码器 |
| `minimax_h3_audio_vae_fp32.safetensors` | 0.56 GB | **258 MB/s** | **4.3 秒** | 音频 VAE 解码器 |
| **全套 6 大模型累计** | **60.18 GB** | **~340 MB/s** | **约 3 分 11 秒** | **远快于从 Google Drive 挂载读取** |

---

### 2. 首帧生图与一致性锁定 (MiniMax-H3-Image)

采用 6 steps 高效扩散推理与参考图锁衣 Prompt：
- **周明基准肖像 (`ref_zhou.png`)**：耗时 **8.3 秒**（冷启动首次文本编码耗时约 25 秒，后续秒级）。
- **S04 锁衣控姿首帧 (`frame_s04.png`)**：耗时 **36.2 秒**（Edit `<Picture 1>` 模式，完美保留纯白挺括衬衫与坐姿）。

---

### 3. MiniMax H3 视频动态口型渲染 (14 Steps @ 24fps)

在 768×1344 竖屏分辨率下，单步采样耗时与总帧数严格呈线性相关：

| 分镜 ID | 角色与情节 | 帧数 | 视频时长 | 单步耗时 (s/it) | VAE 解码+封装 | 单镜总耗时 | 生成产物大小 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S01** | 林总前倾质问 | 141 帧 | 5.88s | ~50.0 秒 | ~30 秒 | 705 秒 (11.7分) | 7.99 MB |
| **S02** | 周明从容应对 | 107 帧 | 4.46s | ~34.0 秒 | ~25 秒 | 567 秒 (9.4分) | 3.79 MB |
| **S03** | 林总疑窦特写 | 90 帧 | 3.75s | ~27.6 秒 | ~20 秒 | 465 秒 (7.7分) | 5.53 MB |
| **S04** | 周明亮出底牌反转 | 124 帧 | 5.17s | ~41.2 秒 | ~28 秒 | 739 秒 (12.3分) | 4.66 MB |
| **全片合计** | **4 镜连贯短剧** | **462 帧** | **19.30s** | **平均 38s/步** | **~103 秒** | **约 41.2 分钟** | **21.97 MB** |

> [!TIP]
> **显存管理实测**：
> 在 NVIDIA L4 (24GB) 上，ComfyUI 开启 `--lowvram` 并动态调度 VRAM。文本编码器加载占 ~14.9GB，扩散模型加载占 ~19.9GB，两者在采样过程中自动交替换入换出，峰值显存锁定在 20.8GB，**全程零 OOM 崩溃**。

---

## 三、 本次实测遭遇的工程坑点与终极解决方案 (Troubleshooting)

### 坑点 1：ComfyUI 路径映射与 `h3_shot.py` 寻找失败
- **问题现象**：ComfyUI 启动时带了参数 `--output-directory /content/lopy-workflow-colab/runtime/outputs`，而 `tools/h3_shot.py` 默认从 `COMFY / "output"` 查找产物，导致抛出 `FileNotFoundError: /content/lopy-workflow-colab/output/h3_shot/...`。
- **根因分析**：未在工作区根目录下创建 `output -> runtime/outputs` 快捷软链接。
- **解决方案**：
  1. 在 `colab_setup.sh` 中固化软链接指令：`ln -sfn runtime/outputs output`。
  2. 在 `tools/h3_shot.py` 中增加候选路径 fallback：同时搜索 `COMFY / "output"` 与 `COMFY / "runtime" / "outputs"`。

---

### 坑点 2：Hugging Face 仓库的授权机制阻断
- **问题现象**：Aria2c 下载报错 `errorCode=24 Authorization failed`。
- **根因分析**：部分 Hugging Face 仓库（例如名字带有 `_ComfyUI` 后缀的衍生仓）设置了 Gated 访问权限，必须提供 HF Token；而原始公开仓不需要。
- **解决方案**：统一使用官方 Direct Resolve 开放路径：
  - `https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/...`
  - `https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/...`

---

### 坑点 3：Colab CLI `exec` 默认 30 秒静默超时
- **问题现象**：使用 `colab exec` 启动安装脚本时，由于安装依赖静默运行超过 30 秒无控制台输出，本地抛出 `TimeoutError: Timeout waiting for output: no message from the kernel for 30s`。
- **根因分析**：Colab CLI 的 WebSocket 监听机制默认在 30 秒内未收到 IOPub 消息便判定超时中断。
- **解决方案**：
  - 对耗时操作统一使用后台脱机运行：`nohup python3 -u script.py > pipeline.log 2>&1 &`；
  - 本地轮询使用轻量的 `colab download -s lopy logfile` 检查日志，互不阻塞。

---

### 坑点 4：抢占式实例中断与断点续跑机制
- **问题现象**：在 S03 完成后，原 Colab 实例触发了生命周期中断（`EVENT: session_terminated`）。
- **根因分析**：云端免费或普通 GPU 实例受平台调度影响可能会被回收。
- **解决方案（高韧性架构）**：
  - **素材即刻落盘**：每个分镜渲染完成第一时间（S01、S02、S03）立刻同步下载至本地开发机。
  - **镜头解耦独立运行**：新实例仅需 3 分钟拉取模型，执行 `run_s04_standalone.py` 直接生成 S04，避免从头重跑前 3 镜，节省了半小时以上的重复算力。

---

### 坑点 5：防止闲置扣除算力积分 (Zero Idle Cost)
- **解决方案**：
  - 任务末尾执行 `colab stop -s <session>`，彻底注销 VM 实例。
  - 实测验证：实例注销后 `Usage rate` 立即归为 `0.00/hr`，算力余额锁定在 593.88 CUs。

---

## 四、 本地与云端协同最佳实践 (Hybrid Architecture Rule)

```
本地 Tesla T4 (零成本调试台)              Google Colab L4 (高性能渲染引擎)
┌───────────────────────────────┐        ┌───────────────────────────────┐
│ • 剧本打磨与语法校验 (Lint)    │        │ • aria2c 350MB/s 极速拉取模型 │
│ • BreezyVoice 快速语音合成     │──TTS─> │ • MiniMax H3 Image 锁衣控姿   │
│ • Faster-Whisper ASR 对齐评测 │        │ • MiniMax H3 Ref2VA 视频渲染  │
│ • FFmpeg 字幕/音效剪辑混流     │<─MP4── │ • 渲染完成自动触发 colab stop  │
└───────────────────────────────┘        └───────────────────────────────┘
```
通过这种「本地配音/剪辑 + 云端批量渲染」的混合架构，既规避了本地显卡缺乏 FP8 张量核心导致的 80 分钟渲染瓶颈，又将云端算力消耗压缩到了极致（单片仅约 3 个积分，成本不足几毛钱）。
