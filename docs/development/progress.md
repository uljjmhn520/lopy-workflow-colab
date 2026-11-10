# 开发进度看板与实测记录 (Progress)

本文档实时追踪项目开发进度、各阶段任务状态，并详细记录所有模块的实测指标与技术踩坑经验。

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
| **IMG-01** | 评估首帧与角色图像生成方案（OpenAI / 本地 / 云端） | - | **待开始** | - |
| **VID-01** | 搭建与验证视频生成环境（H3 / ComfyUI / Colab） | - | **待开始** | - |
| **PIPE-01** | 端到端 1-2 镜头极简样片全链路跑通 | - | **待开始** | - |
| **CUSTOM-01**| 全项目文案与剧本模版简体中文重构 | - | **待开始** | - |
| **CUSTOM-02**| 建立用户自有业务角色资产卡与音色库 | - | **待开始** | - |

---

## 二、 阶段一（配音与 ASR 挑音）实测技术台账

### 1. 运行环境配置
* **宿主机操作系统**：Debian Linux (x86_64)
* **GPU 硬件**：NVIDIA GRID T4-8Q (8GB 物理显存，驱动版本 550.127.05，CUDA 12.4)
* **宿主机内存 / 存储**：32GB RAM，Docker 可用磁盘空间约 98GB
* **基础容器镜像**：`pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime` (PyTorch 2.4.1 + CUDA 12.4 + cuDNN 9)
* **持久化模型存储**：宿主机 `./models` 卷挂载至容器 `/workspace/models`

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

---

## 三、 下一步工作安排 (Next Steps)

1. **进入阶段二（首帧与图像生成评估）**：
   - 梳理目前使用的图像提示词生成逻辑与角色参考图。
   - 确定是优先调用 API（如 OpenAI 图像接口）还是在本地部署开源图像底模。
2. **准备阶段三与四的极简跑通素材**：
   - 挑选或编写一个 1 句话或 2 个分镜的微型短剧样例，为后续端到端串联测试提供输入。
