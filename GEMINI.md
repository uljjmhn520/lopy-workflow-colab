# LoPy 影视级自动化工作流 - 开发与协作规范 (GEMINI.md)

本文档定义了 LoPy 项目的架构标准、硬件分工、商用合规红线与运行目录规范，适用于所有参与本项目的开发者与 AI Agent。

---

## 一、 项目定位与交付规格

LoPy 是一套全流程自动化的影视级 AI 短片生成管线，覆盖「剧本编排 → 角色立绘 → 场景首帧 → 语音合成 → 视频生成 → 自动剪辑与对齐」全链路。

- **画面比例与规格**：严格采用 **9:16 竖屏短视频规格**（基础分辨率 **768×1344**，帧率 **24 fps**，音频 **24kHz/48kHz Stereo AAC**）。
- **目标场景**：抖音、微信视频号、小红书、TikTok 等短视频内容规模化制作。
- **运行原则**：零外部付费 API 强依赖，全本地/私有 GPU 节点闭环运行。

---

## 二、 严格商用合规红线 (Commercial Compliance)

本项目为严肃商用项目，必须遵守以下不可违背的合规底线：

1. **零非商用模型 (Zero Non-Commercial Licenses)**：
   - 严禁引入任何带有 `CC-BY-NC`、`Non-Commercial` 或禁止商业变现条款的模型与权重。
   - 已淘汰不合规组件：**Breeze-TTS-2**（NC 条款）、**YuE2 原始版**（NC 条款）。
   - 经审计可商用替代方案：
     - **语音 Stage 1**：BreezyVoice-300M (Apache-2.0) + Faster-Whisper Large-v3 (MIT)
     - **首帧 Stage 2**：Qwen-Image / MiniMax-H3-Image (Open Weights 商业许可)
     - **视频 Stage 3**：MiniMax H3 Ref2VA (Open Weights 商业许可，依规备案)
2. **零 AGPL 传染风险**：
   - 核心业务代码严禁使用 AGPL-3.0 类强传染开源库，统一遵循 Apache-2.0 / MIT 友好协议。
3. **零云端 API 依赖 (Offline Closure)**：
   - 不依赖 OpenAI、Claude、Midjourney 等外部公网闭源付费接口，全套流程在自有算力或 Colab 上自给自足。

---

## 三、 硬件分工与混合云架构 (Local vs Colab)

根据 Tesla T4 (16GB) 的实测基准数据，项目采用**混合算力分工策略**：

| 阶段 | 任务模块 | 推荐运行环境 | 显存占用 | 预计耗时 (单镜) | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 1** | 配音合成 & ASR 对齐 | **本地 Tesla T4** | ~2.1 GB | ~14 秒 | 丝滑极速，无需占用云端算力 |
| **Stage 2** | 角色立绘与首帧生图 | **Google Colab L4/A100** | ~14.4 GB | ~30~45 秒 | T4 需 35~122 分钟，强力建议云端 |
| **Stage 3** | MiniMax H3 视频渲染 | **Google Colab L4/A100** | ~9.6 GB | ~1.5~2.5 分钟 | T4 缺少原生 FP8 Tensor Core，需 87 分钟 |
| **Stage 4** | 音视频剪辑、EDL 对齐、混音 | **本地 Tesla T4 / CPU** | < 1.0 GB | ~5 秒 | 纯 FFmpeg 封装与批处理 |

- **本地 T4 (16GB)**：作为**开发、调试、测试、剧本打磨与语法校验 (Lint) 的零成本测试台**。
- **Google Colab (L4/A100)**：作为**批量成片、高质量视频渲染的高性能执行引擎**。

---

## 四、 工作区与目录规范 (Runtime Conventions)

为了避免代码、模型权重与生成数据混乱混淆，项目实施严格的物理隔离：

```
lopy-workflow-colab/
├── cloud/               # 云端 Colab 部署脚本与批处理工具 (colab_setup.sh 等)
├── configs/             # 预设工作流配置文件
├── docker/              # Docker 镜像与 ComfyUI 环境定义
├── docs/                # 项目架构文档、安装指导与 Benchmark 报告
├── models/              # 超大基础模型权重目录 (42GB，由 .gitignore 忽略)
│   └── H3/models/       # MiniMax H3 扩散模型、文本编码器、VAE、LoRA
├── pipeline/            # 分镜制作管线与业务编排逻辑
├── runtime/             # 运行时动态数据目录 (由 .gitignore 完全忽略)
│   ├── inputs/          # 待处理的输入素材、参考图像缓存
│   ├── outputs/         # 最终生成的音视频成片、合并资产
│   ├── temp/            # 渲染中间帧序列、临时特征文件
│   ├── shots/           # 分镜任务 JSON 与生成 Prompt 缓存
│   ├── chars/           # 角色设定立绘卡
│   └── first/           # 分镜首帧渲染产物
├── sfx/                 # 开源商业合规音效素材库
├── templates/           # 剧本与片尾模板
├── tools/               # 独立命令行执行工具 (h3_shot.py, gen_image.py 等)
├── colab_lopy_pipeline.ipynb # Google Colab 一键运行交互笔记本
└── GEMINI.md            # 本规范文件
```

### 规则要点：
1. **生成数据不出 `runtime/`**：所有测试运行、生成脚本的产物统一写入 `runtime/`。
2. **根目录快捷软链接**：根目录下保留 `input -> runtime/inputs`, `output -> runtime/outputs`, `chars -> runtime/chars`, `first -> runtime/first`，保证向下兼容现有工具。
3. **版本控制纯净度**：`runtime/` 下除了各子目录的 `.gitkeep` 外，任何动态产物（`.mp4`, `.png`, `.wav` 等）均不得提交至 Git。

---

## 五、 语言与代码规范

1. **全库语言标准**：
   - 所有文档、代码注释、分镜描述统一采用**简体中文**。
   - 分镜 Prompt 结构遵循官方推荐的 6 段式（Subject 主体、Lighting 光照、Camera 镜头运镜、Atmosphere 氛围、Dynamic 动态幅度、Audio-Sync 口型同步）。
2. **防御式资源管理**：
   - 针对 16GB / 24GB 显卡，执行 ComfyUI 推理必须带 `--lowvram` 并预留 `--reserve-vram`。
   - 显存敏感型任务必须开启 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 避免碎片化 OOM。

---

## 六、 严苛人机协同与审查铁律 (Human-in-the-Loop Iron Laws)

为了最大化保护创作者的精力与宝贵的云端 GPU 算力，管线执行必须无条件遵守以下四大铁律：

1. **首帧一票否决铁律 (First-Frame Gate)**：
   - **首帧未审，严禁启渲**：分镜首帧（Keyframe）在未经使用者或质检肉眼确认前，**严禁向云端或本地提交任何多步长（>10 steps）视频扩散渲染任务**。
   - 首帧是视频生成的物理起点锚点。首帧若存在多指、脸崩、衣物穿帮、机位反向越轴，后续 14 步视频必定全废。2 秒的看图确认能避免 40 分钟的算力浪费。
2. **文字排雷前置铁律 (Script Lint Gate)**：
   - 台词剧本必须前置完成语法与多音字排雷（如通过注音标 `两千万[:ㄨㄢ4]`），严禁携带易混淆生硬读音直接进入大批量语音合成与对嘴环节。
3. **机器阈值自检与防骚扰铁律 (Silent Auto-Pass / Alert-on-Fail)**：
   - **及格静默放行**：对于语音合成与 ASR 对齐，当 Faster-Whisper 反向评分 >= 0.95 时，系统必须**自动挑选最高分静默入库，严禁将候选音频挨个抛给创作者逐一试听**；
   - **仅在异常时报警**：只有当评分 < 0.90（判定存在严重吞字、多音字错误）时，系统才允许阻断并向创作者弹出报警与推荐修正方案。
4. **云端算力零闲置停机铁律 (Zero-Idle-Cost Mandate)**：
   - 云端渲染任务完成且素材确认落盘本地后，必须**立刻自动执行 `colab stop` 彻底注销 VM 释放算力**，严禁任何形式的开机空转跑冒滴漏。
