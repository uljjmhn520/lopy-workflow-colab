# THIRD_PARTY_NOTICES：第三方模型与工具授权

> 2026-10-07 依各官方页面查核整理。**本 repo 不含任何模型权重**，只提供下载清单（`setup/downloads_*.json`）；下载与使用前请自行阅读并同意各自的授权。
> 这是授权条文整理，**不是法律意见**。频道若要营利，请先就下方「⚠️」项目找律师确认，或写信向权利方取得书面授权。

## ⚠️ 先看这四件事

1. **非商业限制**（本 repo 的预设就是非商业用途）：以下三者**只能非商业使用**，有广告、赞助、会员收入的频道不能直接用，要换成下方「营利时的替换方向」：
   - **Qwen-Image 2.1**（Qwen Research License）：本 repo 用它生「角色定妆照」与「LoRA 首帧」。可商用的替代：Qwen-Image-Edit 2511（Apache-2.0）。
   - **Breeze TTS 2**（BreezeBlue Research and Non-Commercial License v1.1，**自己架设产生的声音也算**）：本 repo 只用它「设计角色参考音」；每句台词由 BreezyVoice（Apache-2.0）念。条款另禁止用其产出训练／微调／蒸馏其他模型；拿它设计出来的声音当 BreezyVoice 的零样本参考音是否违约，条文没写清楚。要营利请把角色参考音换成可商用来源（VoxCPM2 声音设计或真人录音）。
   - **YuE2**（CC BY-NC 4.0，选用的歌曲模型）。
2. **MiniMax H3 地区限制**：授权不允许在**美国、欧盟、英国、南韩**使用，条文（第 I.5、V.4 条）也涵盖在这些地区散布或展示 H3 本身与其产出。公开影片在这些地区看得到，属灰色地带，请自行评估。
   **用 Google Colab 跑 H3（cloud/）时特别注意**：实测 Colab 的 G4 机器 30 次全在美国或欧盟（荷兰）。授权没有定义「使用」看使用者还是机器所在地；权重在那些机器上被复制、执行，照字面比较可能不在授权范围内。本工具预设照常使用这些机器，只显示警语，风险由使用者自负；想确定可依授权第 II 条联络 MiniMax。另外 Colab 本身有使用条款（不得挖矿、不得当代理伺服器等），本工具不开网页介面、不用外连通道，ComfyUI 只在机器内部被程式呼叫。
3. **AI 生成标示**：MiniMax H3、MiniMax Music 3 的使用规范要求公开发布的内容**清楚标示为机器生成**；商业产品上要显著标示「MiniMax H3」「MiniMax-Music3」。
4. **不得冒充真人**：VoxCPM2、Breeze、H3 都禁止未经本人同意模仿真人的脸或声音；BreezyVoice 的参考音也请只用你有权利的声音。

## 模型

| 项目 | 授权 | 商用 | 主要义务与限制 | 来源 |
|---|---|---|---|---|
| MiniMax H3（Ref2VA 权重，含 Comfy-Org 重新打包版） | MiniMax H3 Community License Agreement（2026-08-02） | 可以（年营收 > 2,000 万美元需书面授权） | 排除美、欧盟、英、南韩；商业产品显著标示「MiniMax H3」；公开内容标示机器生成；不得用产出改进其他 AI 模型；转散布须附授权全文与 NOTICE：「MiniMax H3 is licensed under the MiniMax H3 Community License Agreement, Copyright © 2026 MiniMax. All Rights Reserved.」产出归使用者 | https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE |
| DMAD 4 步 LoRA（`minimax_h3/`） | 沿用 MiniMax H3 Community License（衍生作品） | 同 H3 | 同 H3 | https://huggingface.co/ZhengmingYu/DMAD |
| Veda R2VA 打分器（`minimax_h3_r2va_veda_preview_fp8`，Colab 版自动下载；2026-10-16 加入） | 沿用 MiniMax H3 Community License（作者标示） | 同 H3 | 同 H3 | https://huggingface.co/Veda-Sparse/Minimax-H3-R2VA-Veda-Preview |
| H3 Fun ControlNet patches | 沿用 MiniMax H3 Community License | 同 H3 | 同 H3 | https://huggingface.co/alibaba-pai/MiniMax-H3-Fun-Controlnet-Union-2.0 |
| Qwen3-VL-32B Heretic 文字编码器（ethanfel，INT8 ConvRot） | Apache-2.0（上游 Qwen3-VL-32B-Instruct 亦 Apache-2.0） | 可以 | 保留授权；与 H3 并用时 H3 使用规范照样适用 | https://huggingface.co/ethanfel/Qwen3-VL-32B-Ultra-Heretic-H3-ComfyUI-INT8-ConvRot |
| **Qwen-Image 2.1**（含 Comfy-Org 版、2.1 Turbo 草稿模型） | **Qwen RESEARCH LICENSE AGREEMENT** | **不可以**（仅研究／评估；商用请洽 model-business@notice.qwencloud.com） | 转散布附授权全文与声明「Qwen is licensed under the Qwen RESEARCH LICENSE AGREEMENT, Copyright (c) 2026 Hangzhou Tongyi Laboratory Technology Co., Ltd. All Rights Reserved.」；用它做或改进模型须标「Built with Qwen」 | https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE |
| Qwen-Image-Edit 2511（含 Comfy-Org 版）、Qwen2.5-VL-7B 文字编码器 | Apache-2.0 | 可以 | 保留授权与 NOTICE | https://huggingface.co/Qwen/Qwen-Image-Edit-2511 |
| MiniMax Music 3 | MiniMax-Music3 COMMUNITY LICENSE（2026-08-06）；Comfy-Org 版标示的 Apache-2.0 **与原始授权不符，以原始为准** | 可以（年营收 > 2,000 万美元需授权） | 保留声明；商业产品显著标示「MiniMax-Music3」；公开内容标示机器生成；不得冒充他人 | https://huggingface.co/MiniMaxAI/MiniMax-Music3/blob/main/LICENSE |
| VoxCPM2（权重与程式码） | Apache-2.0 | 可以 | 严禁冒充他人、诈骗、假讯息；强烈建议标示 AI 生成 | https://huggingface.co/openbmb/VoxCPM2 |
| **Breeze TTS 2** 权重（含自架产出） | **BreezeBlue Research and Non-Commercial License v1.1** | **不可以**（官方付费 API 的产出才可商用） | 不得用产出训练／微调／蒸馏非 BreezeBlue 模型；参考音须有权利、不得未经同意模仿真人；NOTICE：「Breeze TTS 2 is licensed under the BreezeBlue Research and Non-Commercial License Agreement. Copyright (c) 2026 RESONIA, INC. All Rights Reserved.」 | https://huggingface.co/BreezeBlue/Breeze-TTS-2/blob/main/LICENSE |
| **BreezyVoice-300M**（联发科 MediaTek Research＋台大；权重与程式码） | Apache-2.0 | 可以 | 保留授权与 NOTICE；参考音须有权利 | https://huggingface.co/MediaTek-Research/BreezyVoice-300M 、https://github.com/mtkresearch/BreezyVoice |
| **Ming-3.0-TTS 0.5B**（inclusionAI 蚂蚁集团；drbaph 的 ComfyUI 单档转档）＋ComfyUI-Ming-3-tts 节点（Saganaki22） | MIT（程式、权重、转档、节点） | 可以 | 保留授权；参考音须有权利 | https://huggingface.co/inclusionAI 、https://huggingface.co/drbaph/Ming-3.0-tts-ComfyUI 、https://github.com/Saganaki22/ComfyUI-Ming-3-tts |
| g2pW 注音模型（G2PWModel-v2-onnx，BreezyVoice 第一次执行时自动下载）＋bert-base-chinese tokenizer | Apache-2.0 | 可以 | 保留授权 | https://github.com/GitYCC/g2pW |
| Whisper large-v3（openai）／faster-whisper-large-v3（Systran 转档） | Apache-2.0／MIT | 可以 | 保留授权 | https://huggingface.co/Systran/faster-whisper-large-v3 |
| **MMS_FA 强制对齐模型**（torchaudio `pipelines.MMS_FA`，Meta MMS；第一次执行自动下载。`tools/pron_check.py` 声调审核、`tools/vc_swap.py` 换字找位置用，只算时间、不产生声音） | **CC-BY-NC 4.0** | **不可以**（非商用） | 标示出处；要营利请改用可商用的对齐器 | https://pytorch.org/audio/stable/generated/torchaudio.pipelines.MMS_FA.html |
| BS-RoFormer `model_bs_roformer_ep_317_sdr_12.9755`（viperx 训练） | **未标示授权** | 不明 | 只附下载连结，不转散布，自行评估 | https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/main/docs/pretrained_models.md |
| FlashVSR v1.1 | Apache-2.0（含 Wan2.1 VAE，Apache-2.0） | 可以 | 保留授权 | https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1 |
| 动作 LoRA：JOKER141 Combat-Base-V2、GunFu、Motion-Continuity-Repair；RunningHubAI speed-slider-1.1 | **未标示授权**（等同保留所有权利）；同时是 H3 衍生作品 | 不明 | 只附连结、不转散布；至少须遵守 H3 授权 | https://huggingface.co/JOKER141 、https://huggingface.co/RunningHubAI/rh-h3-speed-slider-1.1-lora |
| 换角色 LoRA：Alissonerdx `minimax_h3_character_swap_v1.1_ref2va_fro`（`tools/h3_edit.py` 的 `"recipe": "body_swap"`，2026-11-01 加入） | BFS Character Swap License | 可以（影片、电影可直接用；年营收超过 100 万美元的组织要标示 Alissonerdx 与 BFS Character Swap LoRA；不可做成 API／SaaS 服务）；同时是 H3 衍生作品 | 只附下载清单 `setup/downloads_swap.json` | https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/blob/main/LICENSE_CHARACTER_SWAP.md |
| 换头 LoRA：Alissonerdx `minimax_h3_head_swap_v1.0_r32`（`"recipe": "head_swap"`） | **未标示授权**（repo 的 LICENSES.md 只涵盖换角色与动作迁移）；H3 衍生作品 | 不明 | 只附下载连结、不转散布 | https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI |
| SDPose（Comfy-Org 打包）、RT-DETRv4 | MIT／Apache-2.0（SD 底模授权未查） | 大致可以 | 保留授权 | https://huggingface.co/Comfy-Org/SDPose |
| SAM 3D Body、SAM 3.1、MoGe-3（Comfy-Org 打包；白模动作参考 `make_whitemodel.py`，2026-10-23 加入） | 各自官方授权（Meta SAM License／Microsoft MoGe；**本 repo 未逐条查核**） | 请自行查核 | 本 repo 不含权重，只附下载清单 `setup/downloads_whitemodel.json` | https://huggingface.co/Comfy-Org/sam-3d-body 、 https://huggingface.co/Comfy-Org/sam3.1 、 https://huggingface.co/Comfy-Org/MoGe |
| MiniMax 官方 `h3-prompt-writing` 技能（写提示词的规则文件） | MiniMax H3 Community License | 同 H3 | 本 repo 不含，文件只教你从官方 repo 安装 | https://github.com/MiniMax-AI/MiniMax-H3/tree/main/skills/h3-prompt-writing |
| 远景小脸精修（`tools/face_refine.py`，选用，2026-10-24 加入）：MiniMax H3 FL2VA 剪枝 int8（Comfy-Org） | MiniMax H3 Community License | 同 H3 | 同 H3 | https://huggingface.co/Comfy-Org/MiniMax-H3 |
| 同上：lightx2v `minimax_h3_fl2v_turbo_8step_v1.0` LoRA | **模型卡未标示授权**；H3 蒸馏衍生作品 | 不明（至少受 H3 授权约束） | 只附下载连结、不转散布 | https://huggingface.co/lightx2v/Minimax-h3-Turbo |
| 同上：`face_yolov8m.pt`（Bingsu/adetailer） | Apache-2.0 | 可以 | 保留授权；`.pt` 是 pickle 格式，只从这个来源下载并核对 sha256 | https://huggingface.co/Bingsu/adetailer |
| 同上：ComfyUI-H3-FaceRefine 节点 | MIT | 可以 | 保留授权 | https://github.com/Carasibana/ComfyUI-H3-FaceRefine |
| 同上：ComfyUI-H3-NativeAudioLock 节点（71 行，放在另一个工作流 repo 里） | **原 repo 没有授权档**（等同保留所有权利） | 不明 | 本 repo 不复制，只教你自己去拿；用前先读过程式 | https://github.com/Shrek3OnVH5/MiniMax-H3-NativeAudio-MusicVideo-Workflow |
| 同上：ultralytics（侦测器执行套件） | **AGPL-3.0** | 有条件（散布或提供网路服务须依 AGPL 开放原始码；只在自己电脑上跑不受影响） | 保留授权 | https://github.com/ultralytics/ultralytics |
| YuE2（选用） | CC BY-NC 4.0 | 不可以 | 署名、非商业 | https://huggingface.co/m-a-p |
| ACE-Step 1.5 XL（选用，`tools/ace_song.py`；2026-10-27 加入） | MIT（ACE-Step 官方模型卡）；Comfy-Org 打包页标 Apache-2.0 | 可以 | 保留授权 | https://huggingface.co/ACE-Step/Ace-Step1.5 |
| OpenAI Image 2.5 API（选用，云端） | OpenAI Services Agreement | 可以 | 产出归客户（第 4.1 条）；另须遵守 Usage Policies | https://cdn.openai.com/osa/openai-services-agreement.pdf |

## 软体

| 项目 | 授权 | 对本 repo 的影响 | 来源 |
|---|---|---|---|
| ComfyUI | GPL-3.0 | 本 repo 不含 ComfyUI；大多数脚本只透过 HTTP API 呼叫它。**`tools/flashvsr_cli.py` 执行时会直接 import ComfyUI 与 FlashVSR 节点（GPL-3.0）的程式码，因此该档以 GPL-3.0-or-later 授权** | https://github.com/comfyanonymous/ComfyUI |
| ComfyUI-FlashVSR_Ultra_Fast 节点 | GPL-3.0 | 同上 | https://github.com/lihaoyun6/ComfyUI-FlashVSR_Ultra_Fast |
| Veda-on-ComfyUI 节点（稀疏注意力；需要 ComfyUI ≥ 0.38） | MIT（INT8 核心改写自 SageAttention v1，BSD-3-Clause） | 本 repo 不含；Colab 安装时下载 | https://github.com/veda-sparse/Veda-on-ComfyUI |
| Nvidia_RTX_Nodes_ComfyUI | Apache-2.0 | — | https://github.com/Comfy-Org/Nvidia_RTX_Nodes_ComfyUI |
| nvidia-vfx（RTX Video Super Resolution） | NVIDIA 专有授权 | 不可放进 repo，请使用者自行 `pip install` | https://pypi.org/project/nvidia-vfx/ |
| ostris/ai-toolkit | MIT（Copyright (c) 2024 Ostris, LLC） | 保留声明 | https://github.com/ostris/ai-toolkit |
| faster-whisper | MIT | — | https://github.com/SYSTRAN/faster-whisper |
| CosyVoice（BreezyVoice 程式码的上游）、g2pw 套件 | Apache-2.0 | 随 BreezyVoice 安装，不在本 repo | https://github.com/FunAudioLLM/CosyVoice |
| Matcha-TTS（BreezyVoice 的 submodule） | MIT（Copyright (c) 2023 Shivam Mehta） | 随 BreezyVoice 安装，不在本 repo | https://github.com/shivammehta25/Matcha-TTS |
| `setup/breezyvoice/winstub`（取代 WeTextProcessing 的直通替身） | 本 repo 原创，MIT | 不含 WeTextProcessing 程式码 | — |
| python-audio-separator | MIT（README 请使用者标注 UVR 专案） | 建议在片尾或说明栏标注 | https://github.com/nomadkaraoke/python-audio-separator |
| edge-tts | LGPL-3.0（套件）；**微软朗读服务没有公开授权第三方使用** | 本 repo 只用它产生「发音对照」参考音、不放进成片；离线替代为 Breeze（同样非商用） | https://github.com/rany2/edge-tts |
| Blender | GPL（只约束程式本身；算出的图与 .blend 归使用者） | 无 | https://www.blender.org/about/license/ |
| Google Colab CLI（google-colab-cli） | Apache-2.0 | `cloud/` 透过它开 Colab 机器；本 repo 不含它的程式码，`cloud/colab_cli_windows_patch.py` 只在使用者电脑上修改已安装的套件（包住 `import termios`） | https://github.com/googlecolab/google-colab-cli |
| Google Colab 服务 | Google 服务条款＋Colab 使用限制 | 运算单元依各人方案计费；不得挖矿、当代理伺服器等；本工具不开网页介面、不用外连通道 | https://research.google.com/colaboratory/faq.html |
| Noto Sans/Serif CJK、AR PL UKai（Linux 字型，`cloud/vm/install_full.sh` 用 apt 安装） | SIL OFL 1.1／Arphic Public License | 不在 repo 内；`tools/fonts.py` 只指向系统字型路径 | https://github.com/notofonts/noto-cjk |
| `sfx/` 音效 58 个（Freesound） | CC0 1.0（每个档的编号、网址、授权确认见 `sfx/manifest.json`） | 公有领域，可商用、免标示；本 repo 直接附档 | https://freesound.org |
| POUND0423/AI-drama-pound | MIT（Copyright (c) 2026 POUND0423） | `agent/skills/shanshiba-drama/` 改写自此，已附原授权全文 | https://github.com/POUND0423/AI-drama-pound |

## 本 repo 的定位：非商业使用

本工作流预设给**非商业**用途（教学、研究、个人创作、非营利频道），所以预设用 Qwen-Image 2.1 与 Breeze TTS 2（只用于设计角色参考音；台词由可商用的 BreezyVoice 念）。**要营利（广告、赞助、会员、接案）就必须换掉非商用的元件**，方向如下：

| 环节 | 本 repo 预设（非商用） | 营利时的替换方向 | 本 repo 验证状态 |
|---|---|---|---|
| 角色定妆照、LoRA 首帧 | Qwen-Image 2.1 | 云端 OpenAI Image 2.5（`tools/img25.py`，产出归使用者，依 OpenAI 条款）；或向 Qwen 申请商业授权 | Image 2.5 是原专案实际出片用的首帧工具；替换后的整条流程未在本 repo 重测 |
| 首帧（附参考图） | Qwen-Image-Edit 2511 | 不用换（Apache-2.0） | 已测 |
| 台词配音 | BreezyVoice；或 Ming-3.0-TTS 0.5B（`tools/make_ming.py`，2026-10-29 起原专案的固定音轨预设） | 不用换（Apache-2.0／MIT） | BreezyVoice 已测：三种硬体配置都通过；2026-10-07 整片 53 句台湾国语腔调分数 0.85（旧做法 Breeze／VoxCPM2 0.80）。Ming 原专案 2026-10-28 实测（RTX 5090）：9 句全对、像参考音 0.86（Breeze 0.81），使用者听「没有大陆腔」；三种硬体配置未测 |
| 角色参考音（声音设计） | Breeze TTS 2 | VoxCPM2 文字声音设计（`gen_voice.py --design --control "描述"`，Apache-2.0）或自己有权利的真人录音，再交给 BreezyVoice | VoxCPM2 声音设计已能产生声音；设计出的声音台湾腔够不够未系统比较 |
| 挑音的发音对照 | edge-tts | 自己录标准音，或只靠听写（ASR）挑 | 未测 |
| H3、Music 3 | — | 不用换，但要遵守地区限制、标示 AI 生成、商业显著标示模型名称 | — |

### 台湾腔、可商用的声音工具（2026-10-07 依官方页面整理；BreezyVoice 已实测并成为本 repo 预设，其余未实测）

| 选项 | 本机／云端 | 授权 | 台湾腔证据 | 备注 |
|---|---|---|---|---|
| **Ming-3.0-TTS 0.5B（蚂蚁 inclusionAI）** | 本机（ComfyUI 节点） | MIT | 原专案 2026-10-28 试听：使用者「声音非常的好，也没有大陆腔」 | 参考音克隆；**一定要喂简体字**（繁体会念错，`make_ming.py` 自动转）；显存约 3GB；可用行内标签（[Sigh]、[Laughter]） |
| **BreezyVoice（联发科＋台大）＝本 repo 预设** | 本机 | Apache-2.0（程式与权重） | 强：官方专为台湾华语设计，注音控制、破音字处理；本 repo 实测腔调分数最高 | 参考音克隆；没有文字声音设计；底子是 CosyVoice 1。https://github.com/mtkresearch/BreezyVoice |
| BreezeBlue 官方付费 API（Breeze TTS 2 云端版） | 云端 | 经官方平台产生的音讯可商用（模型卡与价格页说法不一致，订阅前请向官方确认） | 与本 repo 用的 Breeze TTS 2 同一模型 | https://breezeblue.ai/pricing |
| Microsoft Azure Speech zh-TW | 云端 | 付费可商用 | 强：官方「Taiwanese Mandarin」 | 只有 3 个声音、没有童声 |
| VoAI 绝好声创 | 云端 | 商用条款未查到 | 强：主打台湾口音 | 快速克隆、多位配音员。https://www.voai.ai/ |
| VoxCPM2＋自己训练的台湾腔 LoRA | 本机 | Apache-2.0 | 视训练资料 | 用自己有权利的台湾腔录音 5–10 分钟；**不能拿 Breeze 自架产出当训练资料** |

不能商用（权重非商用授权）：F5-TTS、MaskGCT、Llasa、Spark-TTS（权重 CC BY-NC-SA）、Fish-Speech／OpenAudio。
