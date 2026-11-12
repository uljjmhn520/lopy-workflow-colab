# 开发进度看板与实测记录 (Progress)

本文档实时追踪项目开发进度、各阶段任务状态，并详细记录所有模块的实测指标与技术踩坑经验。关于 16G Tesla T4 硬件上的完整基准测试与云端生产决策，请参阅专题文档：[t4_benchmark.md](file:///home/debian/lopy_project/lopy-workflow-colab/docs/development/t4_benchmark.md)。

---

## 一、 任务状态看板

| 模块 / 任务编号 | 任务描述 | 负责人 | 状态 | 完成时间 |
| :--- | :--- | :--- | :---: | :---: |
| **VOICE-01** | 本机硬件环境评估（GPU、CUDA、显存、磁盘） | AI Assistant | **已完成** | 2026-11-11 |
| **VOICE-02** | 下载并校验 BreezyVoice-300M 与 G2PW 基础模型 | AI Assistant | **已完成** | 2026-11-11 |
| **VOICE-03** | 构建统一配音 Docker 镜像 (`lopy-voice:latest`) | AI Assistant | **已完成** | 2026-11-11 |
| **VOICE-04** | 编写 `docker-compose.yml` 与宿主机 CLI 包装脚本 | AI Assistant | **已完成** | 2026-11-11 |
| **VOICE-05** | 端到端全流程测试（批次配音 + Faster-Whisper ASR 挑音） | AI Assistant | **已完成** | 2026-11-11 |
| **VOICE-06** | 编写配音环境与 Docker 使用文档 | AI Assistant | **已完成** | 2026-11-11 |
| **DOC-01** | 规划开发计划 (`roadmap.md`) 与进度看板 (`progress.md`) | AI Assistant | **已完成** | 2026-11-11 |
| **ENV-02** | 迁移至 16G Tesla T4 新机器（环境评估、NVIDIA-CTK配置与配音镜像重建） | AI Assistant | **已完成** | 2026-11-11 |
| **IMG-01** | 构建与验证本地 ComfyUI 服务容器（`lopy-comfy:latest`，已在 8188 端口实测就绪） | AI Assistant | **已完成** | 2026-11-11 |
| **IMG-02** | 阶段二 Qwen-Image-Edit 权重全量校验拉取 (~30GB) | AI Assistant | **已完成** | 2026-11-12 |
| **IMG-03** | 阶段二 角色肖像卡生成（小芸 `runtime/chars/yun.png` 1024x1024） | AI Assistant | **已完成** | 2026-11-12 |
| **IMG-04** | 阶段二 镜头首帧生成（S1 教室放学场景 768x1344 竖屏 `runtime/first/s1.png`） | AI Assistant | **已完成** | 2026-11-12 |
| **VID-01** | 阶段三 MiniMax H3 视频模型及 DMAD 4步蒸馏 LoRA 全量模型拉取与校验 (~42GB) | AI Assistant | **已完成** | 2026-11-12 |
| **VID-02** | 阶段三 3秒短视频测试片段生成 (S1 教室举手，9:16 竖屏，4步蒸馏 LoRA，`clip.mp4`) | AI Assistant | **已完成** | 2026-11-12 |
| **STRUCT-01**| 物理工作区规范重构（`runtime/` 隔离、防污染与全库简体中文统一） | AI Assistant | **已完成** | 2026-11-12 |
| **COLAB-01** | Google Colab 一键运行环境交付 (`colab_lopy_pipeline.ipynb` + `colab_setup.sh`) | AI Assistant | **已完成** | 2026-11-12 |
| **IMG-05**   | MiniMax-H3-Image 图像模型可行性调研与 ComfyUI 节点方案设计 | AI Assistant | **已完成** | 2026-11-12 |
| **COLAB-02** | 云端 Colab 实测（MiniMax-H3-Image 首帧 + MiniMax H3 视频批量出片与加速评测） | AI Assistant | **待开始** | - |
| **PIPE-01**  | 基于 demo_local 跑通 4 镜头 9:16 端到端样片闭环 | - | **待开始** | - |
| **CUSTOM-01**| 建立用户自有商业 IP 角色资产卡、音色库与定制剧本 | - | **待开始** | - |

---

## 二、 阶段一（配音与 ASR 挑音）实测技术台账

### 1. 运行环境配置
* **宿主机操作系统**：Debian GNU/Linux 13 (trixie, x86_64)
* **GPU 硬件**：**NVIDIA Tesla T4 (物理显存 15360 MiB / 16GB，驱动版本 620.70.06，CUDA 13.5)**
* **宿主机内存 / 存储**：32GB RAM，`/home` 可用 178GB，`/var` 可用 238GB，存储与显存余量极大
* **容器加速支持**：NVIDIA Container Toolkit 1.20.1，已配置 `/etc/docker/daemon.json` 支持 `--gpus all`
* **基础容器镜像**：`pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime`
* **持久化模型存储**：宿主机 `./models` 卷挂载至容器 `/workspace/models`（4.2G BreezyVoice + 2.9G Voice 完整在盘）

### 2. 核心性能指标
* **BreezyVoice-300M 批次生成**：
  - 单句 2 个 seed（各 13 秒音频），模型首载耗时约 14 秒，批次推理总耗时 41 秒。
  - **实测显存峰值 (Peak VRAM)**：**2.14 GB**（占用总显存约 26.7%，余量充裕）。
* **Faster-Whisper large-v3 ASR 听写与挑音**：
  - 推理精度：`float16`（CUDA 设备加速）。
  - **实测显存峰值**：**1.63 GB**。
  - 挑音操作包括：逐字稿相似度计算、声调与拼音比对、前后静音毫秒级智能裁剪（保留开头 80ms、结尾 150ms）。

### 3. 模型与文件挂载清单
| 模型名称 | 文件位置 | 磁盘大小 | 来源 / 状态 |
| :--- | :--- | :--- | :--- |
| **BreezyVoice-300M** | `models/BreezyVoice/model/` | 3.2 GB (153 个文件) | 官方分块下载并 100% 校验 |
| **G2PWModel (注音字典)** | `models/BreezyVoice/G2PWModel/` | 588 MB (`g2pw.onnx`) | HuggingFace 镜像解包 |
| **Faster-Whisper large-v3**| `models/Voice/models/whisper/` | 3.09 GB (`model.bin` 等) | 容器首次运行自动拉取并宿主机持久化 |

### 4. 关键踩坑经验与解决方案记录
1. **PyArrow 与 NumPy 版本冲突**：
   - *问题*：最新 PyArrow wheel 强依赖 NumPy 2.x，而 BreezyVoice 及多数音频处理库依赖 NumPy 1.26.4，导致容器内出现 `ImportError: pyarrow requires NumPy 2.0 or newer`。
   - *方案*：在 `docker/voice/requirements.txt` 中将版本约束为 `pyarrow<18`，锁定安装 `pyarrow==17.0.0`，彻底解决兼容性冲突。
2. **Linux 文件名大小写敏感**：
   - *问题*：解压出的 G2PW 模型文件为 `g2pW.onnx`（大写 W），但 Linux 文件系统区分大小写，Python 代码请求 `g2pw.onnx`（全小写）报 `NO_SUCHFILE`。
   - *方案*：在 `setup/download_voice_models.sh` 和初始化时增加自动符号链接：`ln -sf g2pW.onnx g2pw.onnx`。
3. **Edge-TTS 外部服务 403 阻断与容错降级**：
   - *问题*：微软 Edge-TTS 近期更新了 WebSocket 认证机制，旧版 `edge-tts 7.2.8` 出现 `403 WSServerHandshakeError`；且作为外网服务，断网或被封禁时会导致挑音脚本崩溃退出。
   - *方案*：
     1. 升级 `edge-tts>=7.3.1`，恢复微软合成接口通信；
     2. 在 `tools/breezyvoice_pick.py` 中引入**健壮容错降级机制**：若无法获取参考音或网络异常，系统自动降级为纯 ASR 准确率排序挑音，确保全自动化工作流永不异常中断。
4. **代码路径与模型路径跨平台兼容 (`AI_ROOT`)**：
   - *问题*：原 Windows 脚本强假设 `C:\AI` 为根目录，且代码和模型混在同一路径。
   - *方案*：在 Docker 镜像内预留符号链接 `code -> /opt/BreezyVoice/code`，通过 `AI_ROOT=/workspace/models` 优雅隔离代码与权重。

### 5. 实测产物验证
* **测试任务文件**：`tests/voice_test/jobs.json`
* **合成候选音频**：
  - `tests/voice_test/out/cand/test_line_s1.wav` (347 KB)
  - `tests/voice_test/out/cand/test_line_s2.wav` (359 KB)
* **最终挑选成品质检音频**：
  - `tests/voice_test/out/test_line.wav` (343 KB，已完成静音去除)
  - `tests/voice_test/out/picks.json` (详细评测数据与裁剪时间戳)

## 三、 阶段二（首帧与图像生成评估）实测技术台账

### 1. 运行配置与服务架构
* **生图服务引擎**：ComfyUI v0.40.0，运行于 `lopy-comfy:latest` 容器，监听宿主机 `http://127.0.0.1:8188`。
* **启动参数优化**：`--disable-cuda-malloc --preview-method none --cache-none --lowvram --input-directory /workspace/input --output-directory /workspace/output`。
* **生图模型选型**：`Qwen-Image-Edit 2511 fp8mixed`（20GB）+ `Qwen-2.5-VL-7B-fp8-scaled`（8.8GB 文本/视觉编码器）+ `Qwen-Image-VAE`（243MB）。
* **两步法角色一致性流**：
  1. **Step 1 角色标准肖像图**：1024×1024，种子 11，纯浅灰无缝背景、正脸中近景、自然光，生成产物保存为 [chars/yun.png](file:///home/debian/lopy_project/lopy-workflow-colab/chars/yun.png)。
  2. **Step 2 场景首帧图**：768×1344（9:16 竖屏），以 `chars/yun.png` 作为 `<image1>` 参考图，保持五官服装一致，注入 500T 柯达电影胶片质感与教室黄昏逆光环境。

### 2. 踩坑经验与解决方案
1. **PyTorch 2.4 与 ComfyUI SDPA `enable_gqa` 兼容性崩溃**：
   - *问题*：ComfyUI 在调用 `comfy.ops.scaled_dot_product_attention` 时默认传递了 `enable_gqa` 参数，但 PyTorch 2.4 的 SDPA 原生不支持该关键字参数（PyTorch 2.5 引入），导致生图执行报错 `TypeError: scaled_dot_product_attention() got an unexpected keyword argument 'enable_gqa'`。
   - *方案*：在 [setup/comfy_patch/sitecustomize.py](file:///home/debian/lopy_project/lopy-workflow-colab/setup/comfy_patch/sitecustomize.py) 中注入 SDPA 兼容补丁，自动拦截 `enable_gqa` 参数，当注意力头数不匹配时通过 `repeat_kv_for_gqa` 进行广播重复，完美在 PyTorch 2.4 上实现 GQA 注意力机制。
2. **容器内外 I/O 目录映射不一致**：
   - *问题*：宿主机调用 CLI 脚本将参考图拷贝到 `./input`，而容器内 ComfyUI 默认工作在 `/opt/ComfyUI/input` 和 `/opt/ComfyUI/output`。
   - *方案*：在容器内将 `/opt/ComfyUI/input` 与 `/opt/ComfyUI/output` 软链接至挂载卷 `/workspace/input` 与 `/workspace/output`，并在启动参数中显式固化 `--input-directory /workspace/input --output-directory /workspace/output`。
3. **Turing 架构 (Tesla T4) 下 FP8 计算特性**：
   - *指标*：Tesla T4 不具备原生 FP8 Tensor Core，FP8 权重在推理时由 CUDA 模拟解包运算。在 1024×1024 分辨率、20 步 Euler（CFG 4.0，相当于 40 次前向计算）下，实测耗时约 35 分钟，峰值显存占用稳定在 14.3 GB（低于 15.3 GB 阈值，无 OOM 发生）。此流程证明本地 T4 能够完整闭环跑通测试验证；而在后续批量生产时，移步 Google Colab（A100/L4 原生 FP8）将提速至数十秒完成。

---

## 四、 阶段三（MiniMax H3 视频渲染）实测技术台账

### 1. 运行配置与产物验证
* **视频模型**：`minimax_h3_ref2va_pruned_int8_convrot` (21GB) + `qwen3vl_32b_minimax_h3_nvfp4_awq` (15.7GB) + `dmad_h3_4step_lora_critic_comfy` (4步蒸馏加速)。
* **内存与显存控制**：`BlockSparseAttention (tau=1.3)` + `--reserve-vram 4.0` + `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`。
* **实测显存峰值 (Peak VRAM)**：**9.61 GB**（总显存占用 62.5%，余量 6.0 GB，彻底消除 OOM）。
* **生成产物**：[tests/video_test/out/clip.mp4](file:///home/debian/lopy_project/lopy-workflow-colab/tests/video_test/out/clip.mp4)（768×1344 竖屏，24 fps，时长 3.04s，H.264+AAC）。
* **单镜耗时**：5243 秒 (~87 分钟)。瓶颈为 T4 缺少原生 FP8 核心，生产环境必须转移至 Google Colab L4/A100。

---

## 五、 下一步工作安排 (Next Steps)

1. **云端 Colab 联调（COLAB-02 核心重点）**：
   - 使用 [colab_lopy_pipeline.ipynb](file:///home/debian/lopy_project/lopy-workflow-colab/colab_lopy_pipeline.ipynb) 在 Google Colab L4 或 A100 上一键部署。
   - 验证 MiniMax H3 视频渲染在原生 FP8 架构下的生成速度（目标：3 秒视频压缩在 1.5~2.5 分钟以内）。
2. **MiniMax-H3-Image 图像实测与比对（IMG-05）**：
   - 在 Colab 环境下接入 `Comfy-Org/MiniMax-H3-Image`。
   - 实测 1~16 张参考图多图锁定能力，测试单图 ~10 秒的快速出片效果与面部一致性，替代 Qwen-Image 作为 Stage 2 核心。
3. **阶段四：四镜头全片串联与后期剪辑（PIPE-01）**：
   - 跑通 `demo_local` 完整 4 镜头管线，输出 15 秒连贯样片。
