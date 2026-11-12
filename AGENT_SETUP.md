# AGENT_SETUP：给 AI agent 的安装手册

> 写给 Claude Code、Codex 等 AI agent：照顺序做，每一步做完都有「怎么确认成功」。人也可以照著做。
> 全程只在 Windows 11＋NVIDIA 显卡上验证过。所有影像、声音、音乐都在本机生成；agent 本身可以用云端模型。

## 0. 先确认这台电脑用哪一份 repo

```
python setup\detect_hardware.py
```

| 显卡 | 记忆体 | 该用的 repo |
|---|---|---|
| 32GB（RTX 5090） | 64GB 以上 | `shanshiba-workflow-32gvram-64gram` |
| 16GB（RTX 4080／5070 Ti／5080） | 64GB | `shanshiba-workflow-16gvram-64gram` |
| 16GB | 32GB | `shanshiba-workflow-16gvram-32gram` |
| 12GB 以下、记忆体不到 32GB、没有 NVIDIA 显卡、Mac | — | **`shanshiba-workflow-colab`**：H3 送 Google Colab 跑（要 Google AI 方案或 Colab 运算单元），见 `cloud/README.md` |

如果推荐的不是目前这份 repo，**停下来告诉使用者**，请他换对应的 repo。四份的流程一样，差在 `docs/hardware.md` 和 `configs/profile.cmd`；每一份都有 `cloud/`，所以本机版的人也可以把 H3 送到 Colab 加速。

> **用 Colab 时（cloud/）**：本手册第 1–3 节只需要做你本机要跑的部分（例如只装语音环境），Colab 上的环境由 `python cloud/colab_h3.py start` 自动装好（**预设完整安装，同第一份完整版**；只要 H3 时加 `--h3-only` 比较快）；本机什么都跑不动就只要装 Colab CLI，然后 `start`。**登入 `colab usage` 一定要让使用者自己在终端机操作**（浏览器授权、贴授权码），agent 不要经手授权码。**机房在美国／欧盟也照常使用，不要因此停下来或换机器**；但要把警语告诉使用者：H3 授权排除这些地区，风险由使用者自负（`cloud/README.md` 开头）。

> **开 Colab 之前先问使用者开几台**：先跑 `python cloud/colab_plan.py <spec 清单或镜头资料夹>`，它会估算 0–4 台各要多久、花多少运算单元，并印出一段建议；把建议台数、时间、单元告诉使用者，等使用者同意再开机。开跑后看 log 确认云端真的接到镜头（开机失败时 `hybrid_h3.py` 会改成全部本机跑）。

再读 `docs/hardware.md`，了解这个配置的预期速度、显存、记忆体和风险。

## 1. 前置软体

| 项目 | 版本（原专案） | 怎么确认 |
|---|---|---|
| Windows | 11 | `winver` |
| NVIDIA 驱动 | 610.88（要支援 CUDA 13.0） | `nvidia-smi` 右上角 CUDA Version ≥ 13.0 |
| Python | 3.12（3.12.10–3.12.14 都可）；BreezyVoice 另需 3.10（用 uv 安装即可） | `py -3.12 --version` |
| uv | 任意（装 Python 3.10 与 BreezyVoice 环境用：`pip install uv`） | `uv --version` |
| Git | 任意 | `git --version` |
| ffmpeg／ffprobe | 9.0.1 full build，要在 PATH | `ffmpeg -version` |
| 硬碟 | C 槽至少 250GB 可用（必要模型约 150GB），NVMe SSD | `detect_hardware.py` |
| 分页档 | Windows 预设「系统管理」即可，不要设成固定的小数字 | 系统 → 进阶系统设定 → 效能 → 虚拟记忆体（**这是系统设定，要请使用者自己确认或改**） |

## 2. 资料夹与四个 Python 环境

所有程式假设安装在 `C:\AI`。**ComfyUI 资料夹名称请照抄 `ComfyUI-0.36.0`**（里面放的是 0.37.0，名称是历史原因，很多脚本写死这个路径）。

**顺序很重要：先做完第 2 节（尤其是 clone ComfyUI），再做第 3 节下载模型。** 部分模型清单会写进 `ComfyUI-0.36.0\models\`，先下载的话资料夹已经存在，`git clone` 会因为目录不是空的而失败。

**套件一律用 uv 装**（比 pip 快很多；2026-10-07 全新安装实测，pip 下载部分大档只有 100–200 kB/s，H3 环境卡了 20 分钟以上，改 uv 1.5 分钟装完）。四份清单都是原专案 `pip freeze` 的完整结果，所以都加 `--no-deps` 照清单装，不要让 pip／uv 自己重新解依赖（语音环境的 voxcpm 依赖会跟锁定的 fsspec 冲突，照清单装则没问题）。uv 也卡住时，见文末常见问题。

```
mkdir C:\AI\H3  C:\AI\Voice  C:\AI\BreezeTTS  C:\AI\BreezyVoice  C:\AI\tools
```

### 2a. 主环境 C:\AI\H3（ComfyUI、H3、Qwen-Image、Music 3、放大）

```
git clone https://github.com/comfyanonymous/ComfyUI C:\AI\H3\ComfyUI-0.36.0
cd C:\AI\H3\ComfyUI-0.36.0 && git checkout v0.37.0
py -3.12 -m venv C:\AI\H3\venv
uv pip install --python C:\AI\H3\venv\Scripts\python.exe --no-deps -r <repo>\setup\env\requirements_h3_venv.txt --extra-index-url https://download.pytorch.org/whl/cu130 --index-strategy unsafe-best-match
copy <repo>\setup\extra_model_paths.yaml C:\AI\H3\ComfyUI-0.36.0\extra_model_paths.yaml
```
自订节点照 `setup\custom_nodes.txt` clone 到 `ComfyUI-0.36.0\custom_nodes\` 并 checkout 指定 commit。**节点自己的 requirements.txt 不用另外装**（需要的套件，例如 triton-windows、nvidia-vfx，已经在上面的清单里）。
确认：`C:\AI\H3\venv\Scripts\python.exe -c "import torch;print(torch.__version__, torch.cuda.is_available())"` → `2.14.0+cu130 True`

### 2b. 语音环境 C:\AI\Voice（VoxCPM2、faster-whisper、分轨、声调比对）

```
py -3.12 -m venv C:\AI\Voice\venv
uv pip install --python C:\AI\Voice\venv\Scripts\python.exe --no-deps -r <repo>\setup\env\requirements_voice_venv.txt --extra-index-url https://download.pytorch.org/whl/cu130 --index-strategy unsafe-best-match
```
确认：`C:\AI\Voice\venv\Scripts\python.exe -c "import voxcpm, faster_whisper, audio_separator, stable_whisper, edge_tts;print('ok')"` → `ok`

### 2c. Breeze TTS 2 环境 C:\AI\BreezeTTS（只用来「设计新角色的参考音」）

```
git clone https://github.com/breezeblue-ai/breeze-tts C:\AI\BreezeTTS\breeze-tts
py -3.12 -m venv C:\AI\BreezeTTS\venv
uv pip install --python C:\AI\BreezeTTS\venv\Scripts\python.exe --no-deps -r <repo>\setup\env\requirements_breeze_venv.txt --extra-index-url https://download.pytorch.org/whl/cu128 --index-strategy unsafe-best-match
```
（Breeze 用 cu128 的 torch，跟另外两个环境不同，这是原专案实际状态。）

### 2d. BreezyVoice 环境 C:\AI\BreezyVoice（⭐ 所有台词配音）

BreezyVoice（联发科＋台大，Apache-2.0）是本工作流的台词配音引擎：用角色参考音念任何台词，台湾国语腔，念不准的字可直接标注音。官方只支援 Linux，下面是原专案在 Windows 上实际跑通的装法：

```
git clone --recurse-submodules https://github.com/mtkresearch/BreezyVoice C:\AI\BreezyVoice\code
cd C:\AI\BreezyVoice\code && git checkout d592c9d3e8927a0f53f68616387060dcd32a05ea && git submodule update --init --recursive
uv python install 3.10
uv venv --python 3.10 C:\AI\BreezyVoice\venv
uv pip install --python C:\AI\BreezyVoice\venv\Scripts\python.exe "setuptools<70" wheel
uv pip install --python C:\AI\BreezyVoice\venv\Scripts\python.exe --no-build-isolation --no-deps -r <repo>\setup\env\requirements_breezyvoice_venv.txt --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cu128
xcopy /E /I <repo>\setup\breezyvoice\winstub C:\AI\BreezyVoice\winstub
```
- 一定要 `--no-deps` 照清单装：`g2pw` 会要求编不起来的旧版 transformers；`openai-whisper` 要先有 `setuptools<70` 再用 `--no-build-isolation` 建置；`HyperPyYAML` 要 `ruamel.yaml<0.18`（清单已锁）。
- `winstub`：官方的文字正规化（WeTextProcessing）需要 pynini，Windows 装不了，用这个直通替身取代。**它不会把数字转成国字**，`breezyvoice_batch.py` 会自动转阿拉伯整数，其他（小数、英文缩写）请在台词里写成国字。
- 第一次执行会自动下载 g2pW 注音模型（607MB，到 `C:\AI\BreezyVoice\code\G2PWModel`）和 bert-base-chinese 的 tokenizer（不到 1MB）。
- 确认：`C:\AI\BreezyVoice\venv\Scripts\python.exe -c "import torch;print(torch.__version__, torch.cuda.is_available())"` → `2.7.1+cu128 True`

### 2e. 工具

```
xcopy /E /I <repo>\tools C:\AI\tools
```

### 2f.（选用）Ming-3.0-TTS 0.5B 固定音轨（MIT，可营利；原专案 2026-10-29 起的配音备案预设）

H3 念错抽不出来的台词，用角色参考音念成固定音轨（`tools\make_ming.cmd jobs.json`，格式同 BreezyVoice）；饶舌对决范本的 DJ 口白也用它。**Colab 完整安装已内建**（节点装在 VM 的 ComfyUI、8188 埠，`colab_h3.py` 自动设好环境变数），下面是本机安装。原专案把节点装在**另一份 ComfyUI 0.41**（`C:\AI\H3\ComfyUI-0.41.0`、8189 埠，`models`／`input`／`output` 连到主 ComfyUI），H3 用的那份不动；节点只在 0.41 测过。

```
git clone https://github.com/Saganaki22/ComfyUI-Ming-3-tts C:\AI\H3\ComfyUI-0.41.0\custom_nodes\ComfyUI-Ming-3-tts
cd C:\AI\H3\ComfyUI-0.41.0\custom_nodes\ComfyUI-Ming-3-tts && git checkout 1e97248
C:\AI\H3\venv\Scripts\python.exe -m pip install onnxruntime flatbuffers protobuf
cd <repo>\setup && C:\AI\H3\venv\Scripts\python.exe download.py downloads_ming.json
```
- 路径或埠不同：设环境变数 `MING_COMFY_DIR`、`MING_COMFY_PORT`、`MING_COMFY_INPUT`、`MING_COMFY_OUTPUT`。`make_ming.py` 会自己在背景启动那份 ComfyUI，跑完叫它释放显存。
- 装之前先存一份 `pip freeze`（原专案装完是 onnxruntime 1.31.1，H3 照常）。

## 3. 下载模型（全部锁定版本、逐档验证杂凑、可续传）

cmd 视窗：
```
cd <repo>\setup
for %f in (downloads.json downloads_uncensored.json downloads_dmad.json downloads_qwen_image.json downloads_qwen_image_edit.json downloads_music3.json downloads_voxcpm2.json downloads_breeze_tts2.json downloads_breezyvoice.json downloads_flashvsr.json) do C:\AI\H3\venv\Scripts\python.exe download.py %f
```
（写进 .bat 档要把 `%f` 改成 `%%f`。）PowerShell：
```
cd <repo>\setup
foreach ($f in 'downloads.json','downloads_uncensored.json','downloads_dmad.json','downloads_qwen_image.json','downloads_qwen_image_edit.json','downloads_music3.json','downloads_voxcpm2.json','downloads_breeze_tts2.json','downloads_breezyvoice.json','downloads_flashvsr.json') { C:\AI\H3\venv\Scripts\python.exe download.py $f }
```
每份清单跑完会印 `downloaded N, already present M, failed K`，全部成功才印 `ALL DOWNLOADS VERIFIED`（有失败时结束码非 0，重跑会从断点续传、已验证的档案自动跳过）。大档用 SHA-256 验证，小设定档用 Hugging Face 公布的 git 杂凑验证。

| 清单 | 内容 | 大小 |
|---|---|---|
| `downloads.json` | H3 主模型（剪枝 int8）、官方 NVFP4 文字编码器、影音 VAE | 约 41GB |
| `downloads_uncensored.json` | H3 文字编码器 int8（**本工作流实际使用的那颗**） | 24.6GB |
| `downloads_dmad.json` | DMAD 4 步 LoRA（下载后要转档，见下） | 2.6GB |
| `downloads_qwen_image.json` | Qwen-Image 2.1 int8＋文字编码器＋VAE（角色定妆照、LoRA 首帧） | 16.1GB |
| `downloads_qwen_image_edit.json` | Qwen-Image-Edit 2511 fp8＋文字编码器＋VAE（**预设的首帧做法**） | 28.1GB |
| `downloads_music3.json` | MiniMax Music 3 | 11.1GB |
| `downloads_voxcpm2.json` | VoxCPM2 主权重 | 4.6GB（另需同 repo 的 config／tokenizer 小档，见下） |
| `downloads_breeze_tts2.json` | Breeze TTS 2（含 tokenizer、audio_tokenizer；只用来设计新角色的参考音） | 7.1GB |
| `downloads_breezyvoice.json` | BreezyVoice-300M（**台词配音**） | 3.0GB |
| `downloads_flashvsr.json` | FlashVSR v1.1 | 6.3GB |
| `downloads_ming.json`（选用） | Ming-3.0-TTS 0.5B（固定音轨配音，见 2f） | 3.0GB |
| 选用 | `downloads_action_loras.json`（动作 LoRA）、`downloads_funcontrol.json`（舞蹈骨架控制）、`downloads_whitemodel.json`（舞蹈／武打白模动作参考，7.2GB；多人上色节点在 `setup/comfy_nodes/whitemodel_color`）、`downloads_qwen_turbo.json`（首帧草稿模式，7.3GB）、`downloads_swap.json`（换角色／换头 LoRA，`h3_edit.py` 的 `recipe`，约 390MB） | — |

另外四个会自动下载的：
- VoxCPM2 小档：`C:\AI\Voice\venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download as s; s('openbmb/VoxCPM2', revision='32279effe8c19989596f05d353d1447f51d9e915', local_dir=r'C:\AI\Voice\models\VoxCPM2')"`
- faster-whisper large-v3：`C:\AI\Voice\venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', download_root='C:/AI/Voice/models/whisper')"`
- g2pW 注音模型：第一次跑 BreezyVoice 时自动下载（见 2d）。
- BS-RoFormer：第一次跑 `audio-separator` 时自动下载到 `C:\AI\Voice\models\separator`（`smoke_test.py` 会触发）。

DMAD 转档：
```
C:\AI\H3\venv\Scripts\python.exe C:\AI\tools\dmad_lora_convert.py C:\AI\H3\ComfyUI-0.36.0\models\loras\dmad_raw\dmad_minimax_h3_4step_lora_critic.safetensors C:\AI\H3\ComfyUI-0.36.0\models\loras\dmad_h3_4step_lora_critic_comfy.safetensors
```
（只需要 `lora_critic` 这一颗；`full_critic` 实测构图会漂，不用。）

## 4. 启动与自我验证

在**同一个 cmd 视窗**依序执行（`profile.cmd` 设定的环境变数只在这个视窗有效）：
```
set PYTHONUTF8=1
call <repo>\configs\profile.cmd
C:\AI\tools\start_comfy.cmd
C:\AI\H3\venv\Scripts\python.exe <repo>\setup\smoke_test.py
```
`smoke_test.py` 会自己设计一个声音、生一张首帧，跑完 Breeze（设计声音）→ BreezyVoice（念台词＋自动挑选）→ VoxCPM2（备用引擎）→ faster-whisper → 声调比对 → Qwen-Image 2.1 → Music 3 → BS-RoFormer → H3 → RTX VSR → FlashVSR，最后印出每一步 OK／FAIL 和秒数。
- 全部 OK，且每步时间在 `docs/hardware.md` 列的范围内（真实显卡比 5090 慢是正常的），就算安装完成。完整版 14 步；`--quick` 跳过 FlashVSR，13 步。
- 2026-10-07 全新安装实测（另一个 agent 只看本 repo、在清空的 `C:\AI` 从零安装，RTX 5090）：完整版 14 步全部 OK，共 500 秒；第一次跑 BreezyVoice 会先下载 g2pW 注音模型，那一步多约 45 秒。
- 打开 `setup\smoke_out\h3\clip.mp4` 看：画面清楚、嘴型有跟著台词动。

## 5. 跑全本地示范片

```
C:\AI\H3\venv\Scripts\python.exe <repo>\pipeline\demo_local\run_demo.py
```
从零做两个角色、4 镜首帧、配音、H3、配乐，输出 `pipeline\demo_local\out\cut\demo_1080p.mp4`（约 17 秒）。2026-10-07 全新安装实测 12.8 分钟（RTX 5090）；「16GB 显卡＋32GB 记忆体」模拟条件下约 15 分钟（5090 运算速度；真实 16GB 卡推估 30–40 分钟）。看成片确认：两个角色每镜长得一样、嘴型跟著台词、字幕念的跟声音一致。

## 6. 开始做片

读 `docs/03_规则与踩坑.md`（规则）和 `pipeline/template_local/README.md`（做法），把 `agent/CLAUDE.md范本.md` 放到使用者的专案根目录改名 `CLAUDE.md`。做新片：用 `agent/skills/shanshiba-drama` 写剧本 → 复制 `pipeline/template_local/` 成新资料夹 → 把角色、场景、镜表填进 `film.json` → `make_film.py` 分段跑，三个人工关卡（首帧总览、每镜抽格、成片）都要给使用者看。做饶舌对决：用 `agent/skills/rap-battle`（生歌前先问使用者有没有 Suno）→ 复制 `pipeline/template_battle/` → 填 `battle.json` → `make_battle.py`。

## 常见问题

| 症状 | 处理 |
|---|---|
| `ComfyUI not reachable` | 先 `call configs\profile.cmd`，再 `C:\AI\tools\start_comfy.cmd` |
| 跑 H3 时整台电脑卡住 | 关掉浏览器等大程式；确认没有两个 GPU 工作同时跑 |
| 「分页档太小」（Windows error 1455） | 请使用者把分页档改回「系统管理」或设 64GB 以上 |
| VAE 解码时当掉 | `configs\profile.cmd` 的 `COMFY_EXTRA_ARGS` 加 `--disable-pinned-memory --disable-async-offload` |
| faster-whisper 找不到 cuBLAS | 用 `stt.py`（它会自动把 venv 里 nvidia 的 DLL 加进路径） |
| 装套件时某个大档（例如 `nvidia-cudnn-cu12` 700MB）下载只有几百 kB/s、卡很久 | 确认用的是 `uv pip install`；还是卡住就先用浏览器或多连线下载工具把那个 wheel 抓下来，`uv pip install --python <venv> --no-deps <wheel档>` 先装它，再重跑整份清单 |
| 指令输出的中文变乱码 | 先 `set PYTHONUTF8=1`（或在 Git Bash 用 `export PYTHONUTF8=1`）；不影响结果，只影响显示 |
| 下载清单印出 `failed` | 再跑一次同一份清单（会续传）；一直失败就检查网路能不能连 huggingface.co |
