# Lopy-Workflow 本地配音 Docker 环境指南

本项目提供一体化的本地 Docker 容器化方案，封装了 **BreezyVoice-300M (台灣國語/標準中文 TTS)**、**Faster-Whisper large-v3 (ASR 挑音)**、**G2PW (注音/拼音分析)** 与 **Edge-TTS (对比基准)**。

---

## 1. 硬件要求与实测指标

| 组件 | 资源占用 (实测) | 推荐配置 |
| :--- | :--- | :--- |
| **GPU 显存 (VRAM)** | 峰值约 **2.14 GB** | >= 4GB VRAM (NVIDIA CUDA 11.8/12.x) |
| **CPU / 内存** | 2 核 / 4GB RAM | 4 核 / 8GB+ RAM |
| **磁盘空间** | 模型权重约 7GB，Docker 镜像约 12GB | >= 25GB 可用空间 |

> 本机测试配置：NVIDIA GRID T4-8Q (8GB VRAM, CUDA 12.4)，单句 2 个 seed 批量生成耗时约 41 秒，显存占用稳定在 2.14GB。

---

## 2. 目录架构与模型权重

所有模型权重集中存放在宿主机的 `models/` 目录下（已加入 `.gitignore` 防止误提交）：

```
lopy-workflow-colab/
├── models/
│   ├── BreezyVoice/
│   │   ├── model/                  # BreezyVoice-300M 权重 (153 个文件, ~3.2GB)
│   │   ├── G2PWModel/              # G2PW 注音字典模型 (g2pw.onnx 等, ~600MB)
│   │   ├── code -> /opt/BreezyVoice/code
│   │   └── winstub -> /opt/BreezyVoice/winstub
│   └── Voice/
│       └── models/
│           └── whisper/            # Faster-Whisper large-v3 权重 (~3.1GB)
├── docker/
│   └── voice/
│       ├── Dockerfile              # PyTorch 2.4.1 + CUDA 12.4 一体化镜像
│       └── requirements.txt        # 依赖清单
├── tools/
│   ├── docker_voice.sh             # 快捷 CLI 脚本
│   ├── breezyvoice_batch.py        # 批次语音合成
│   └── breezyvoice_pick.py         # 智能 ASR 腔调筛选
└── docker-compose.yml              # GPU 与卷挂载定义
```

---

## 3. 快速上手

### 步骤 1：下载模型权重
运行自动下载脚本，获取 BreezyVoice-300M 和 G2PW 模型：
```bash
./setup/download_voice_models.sh
```

### 步骤 2：构建 Docker 镜像
```bash
./tools/docker_voice.sh build
```

### 步骤 3：执行语音生成与挑音

通过 `tools/docker_voice.sh` 提供的一键命令：

```bash
# 一键完成：生成全部 seed 候选音频并执行 ASR 腔调优选
./tools/docker_voice.sh all path/to/jobs.json

# 仅批次生成候选项
./tools/docker_voice.sh batch path/to/jobs.json

# 仅执行 ASR 听写与腔调挑音
./tools/docker_voice.sh pick path/to/jobs.json
```

---

## 4. 辅助指令

```bash
# 在配音容器内执行任意命令 (例如查看 GPU 状态)
./tools/docker_voice.sh run nvidia-smi

# 进入容器的交互式 Bash 终端进行调试
./tools/docker_voice.sh bash
```

---

## 5. jobs.json 配置示例

```json
{
  "out_dir": "out",
  "seeds": 8,
  "jobs": [
    {
      "name": "line_01",
      "text": "大家好，这是本地配音环境测试，运转一切正常。",
      "ref_audio": "ref_sample.wav",
      "ref_text": "A man said to the universe: Sir, I exist."
    }
  ]
}
```
- `out_dir`：输出目录（相对于 `jobs.json` 所在位置）。
- `seeds`：每句生成的候选数量（建议 4-8 个）。
- `ref_audio`：音色克隆参考音频（16kHz/22.05kHz 单声道 WAV）。
- `ref_text`：参考音频的逐字稿文本。
