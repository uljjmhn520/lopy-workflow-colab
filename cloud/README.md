# cloud/：用 Google Colab 跑 H3（本机跑不动的人用）

**做法：本机准备、云端只跑 H3。** 剧本、首帧、配音、剪接在你的电脑做；H3 影片整批送到 Google Colab 的 G4 显卡跑，跑完下载回来。素材和成品一直都在你的硬碟，Colab 机器一关掉就清空。
本机连配音都跑不动（没有 NVIDIA 显卡、Mac）的人，可以用**全云端模式**：整套环境装在 Colab 上，整支片在云端做完再下载。

> 所有数字都是 2026-10-10 在 Colab（Google AI Pro 帐号，每月 200 运算单元）实测。Colab 的方案、价格、可用显卡随时会变。
>
> 💡 **模型存储与 Google Drive 避坑指南**：切勿将 42GB 的 H3 核心权重放在 Google Drive 中直接挂载读取（会导致加载卡死 15~30 分钟、FUSE 虚拟驱动崩溃或触发 Google 24 小时下载配额限制）。推荐采用「本地 NVMe 临时盘多线程动态拉取大模型＋成片自动回传 Drive 归档」的动静分离架构。详细技术与基准对比请参阅 [docs/colab_storage_architecture.md](file:///home/debian/lopy_project/lopy-workflow-colab/docs/colab_storage_architecture.md)。

## ⚠️ 先读：H3 授权与机房位置

- MiniMax H3 授权（第 I.5、V.4 条）**排除在美国、欧盟、英国、南韩使用**（含复制、执行、散布、展示 H3 与其产出）。
- 实测 Colab **G4 开机 30 次：美国 18 次（俄亥俄 17、拉斯维加斯 1）、欧盟荷兰 12 次，从没分到亚洲**；L4／A100 偶尔分到新加坡，但跑 H3 又慢又贵。
- 授权**没有定义「使用」看使用者所在地还是机器所在地**；照字面，权重在美国／欧盟机器上被复制、执行，比较可能被认为不在授权范围内。
- **本工具预设照常使用这些机房，不会挡、也不会换机器**，`colab_h3.py` 只在每次开机时显示机房国家与警语；风险由你自负（这里不是法律意见）。想确定可以照授权第 II 条写信问 MiniMax。
- 想避开的替代做法：台湾或日本机房的云端 GPU（例如台湾 GPUtw 的 RTX 5090／RTX PRO 6000、RunPod 日本 AP-JP-1），用同一套 `cloud/vm/setup_h3.py` 自己装即可（未在本 repo 实测）。

## 1. 准备（一次）

1. 有一个 **Google AI 方案**（AI Pro 每月约 200 运算单元；**免费试用期间不发**）或在 Colab 买**随用随付**运算单元（100 个 US$10.49）。
2. 安装 Colab CLI（Google 官方，Apache-2.0）：
   ```
   uv tool install google-colab-cli
   ```
3. **Windows 一定要修补**（官方只支援 Linux／macOS，Windows 上连 `colab version` 都会因 `import termios` 当掉）：
   ```
   python cloud/colab_cli_windows_patch.py
   ```
   只包住两行 import（会留备份 `console.py.bak`），之后 new／exec／upload／download／stop 都正常；`colab console`、`colab ssh` 仍不能用（本工具不用）。更新 CLI 后要重跑。
4. 登入（要你自己在终端机做，浏览器里选有方案的那个 Google 帐号、把授权码贴回终端机）：
   ```
   colab usage
   ```
5. 确认：`python cloud/colab_h3.py check` 会显示余额。

> **预设 `start`＝完整安装**（2026-10-11 起）：跟第一份 repo 完整版（32GB 显卡＋64GB 记忆体）一样，语音三环境、ComfyUI（H3、Qwen、Music 3、FlashVSR、YuE2 歌曲、Ming-3.0-TTS 配音）、中文字型全部装，约 10.5 分钟、约 1.5 单元；G4 有 96GB 显存，完整版的设定都跑得动。只要 H3 的人加 `--h3-only`（约 3.7 分钟）。
> **两种安装都开 2 个 ComfyUI**（2026-10-11 起，完整安装原本只开 1 个）：各 `--reserve-vram 46`、第二个晚 30 秒开工＝实测最快（每小时 123 支，见 §4）。要单一个就 `start --instances 1`（完整安装用环境变数 `H3_INSTANCES`）。开完可以看 `/content/h3_state.json` 有没有列出 2 个。

## 2. 只有 H3 上云端（本机能做首帧和配音）

```
python cloud/colab_h3.py start --h3-only           # 开 G4、只装 ComfyUI＋H3（约 3.5–4 分钟）、开 2 个 ComfyUI
python cloud/colab_h3.py batch S01/spec.json S02/spec.json ...   # 打包上传 → 云端跑 → 成品下载回各 spec 旁边
python cloud/colab_h3.py keepalive --minutes 20    # （选用）审片时保住机器
python cloud/colab_h3.py stop                      # 确定不再需要 H3 才关（见下方「什么时候关机」）
```
- **什么时候关机（2026-10-11 实作定案）**：拍完 → 自己（或 agent）看接触表 → 要重拍就直接送到**同一台**，中间**不要关机、不要用 `--stop-after`**（重开只装 H3 要约 4 分钟、完整安装约 10 分钟，比开著等更花时间）。**看完重拍、确定都不需要再用 H3，要交给人工审片了，才 `stop`。** 审片超过约 15 分钟才回来就先 `keepalive`，否则闲置约 20 分钟会被收回。
- `batch` 吃的就是 `tools/h3_shot.py` 的分镜 JSON；首帧、配音、参考图等档案会自动一起打包（相对路径以 spec 所在资料夹为准）。成品放在 spec 旁边：档名是 `spec.json` 就放同一个资料夹，否则放在同名资料夹。
- **多镜范本自动判断**：`pipeline/template_local/make_film.py` 侦测到本机显卡跑不动 H3（不到 15GB 显存或 30GB 记忆体）时，h3／amb 两步会自动整批送到 Colab；也可以用 `set H3_BACKEND=colab`（或 `local`、`both`＝本机＋Colab 一起跑，见 §3b）强制。只跑 h3 时本机不必开 ComfyUI。
- 没开机就直接 `batch` 会自动先 `start`（预设完整安装；只要 H3 就 `batch --h3-only …`）；加 `--stop-after` 跑完自动关机——**只用在最后一批**（确定不会再重拍），审片重拍的来回中间不要用。

## 3. 全云端（本机什么都跑不动）

```
python cloud/colab_h3.py start                     # 预设＝完整安装：语音三环境、ComfyUI（H3、Qwen、Music 3、FlashVSR、YuE2、Ming TTS）、中文字型（旧名 full-setup 也可以）
python cloud/colab_h3.py smoke                     # 跑 setup/smoke_test.py，结果下载到 setup/smoke_out_colab/
python cloud/colab_h3.py film pipeline/template_local chars masters frames   # 在云端跑 make_film.py 指定阶段，out/ 同步回本机
python cloud/colab_h3.py film pipeline/template_local voices h3 amb edl music ending cut review
python cloud/colab_h3.py film pipeline/my_battle yue songs dj audio   # 饶舌对决（资料夹有 battle.json 就改跑 make_battle.py），见 pipeline/template_battle/README.md
python cloud/colab_h3.py stop
```
- **2026-10-10 新 agent 实测（只看本 repo、从零）**：`full-setup` **约 10.5 分钟**（VM 端 540 秒；10 份模型清单约 8 分钟）→ `smoke` 约 13 分钟 → 范本片〈被狗吃掉的作业〉分三段 `film` 共约 28 分钟，成片 38.5 秒 1080p、−15.9 LUFS，自审全过；G4 开机到关机约 54 分钟、**约 8 个运算单元**。Colab 硬碟约 236GB，装完剩约 40–80GB。
- 全云端模式**现在预设也开 2 个 ComfyUI**（2026-10-11 起；之前只有 1 个，还要跟 Qwen、Music 3 轮流换模型，H3 每镜约 70 秒）。`film` 跑到 h3／amb 时用 2 个 ComfyUI 错开跑（`cloud/vm/parallel_h3.py`，`H3_PARALLEL=2`）。2026-10-11 实战：完整安装后 `batch` 25 镜 1 个 ComfyUI 跑 1594 秒（含上传下载）→ 之后改 2 个。
- 范本可以直接跑 `pipeline/template_local`；做自己的片时照 `pipeline/template_local/README.md` 复制成 `pipeline/<片名>/`，再 `film pipeline/<片名> …`（资料夹一定要在 repo 里面）。
- 每个人工关卡（首帧、H3 接触表、成片）之间，`film` 会把 `out/` 下载回来给你看；改了要重做的档案删掉，再跑下一段，`film` 会把整个片子资料夹重新上传，从断点接著做。
- **本机设的 `ONLY`（只重做某几镜）、`ALLOW_REVIEW`、`UPSCALE` 会自动带到 VM**；其他设定用 `--env KEY=VALUE`（例：`film pipeline/template_local h3 --env ONLY=S3`）。
- **VM 被收回（闲置约 20 分钟）或你 `stop` 之后**：重新 `full-setup`（约 10 分钟、约 1.5 单元），再 `film` 同一个资料夹就会从断点接著做。
- 注意：云端跑出来的 `out/*.json`（`voice_picks`、`amb`、`music_pick`、`edl`）里存的是 `/content/...` 的云端路径；要在本机接著跑 `edl`／`cut` 得重跑前面那几段，建议全程在云端做完。
- smoke_test 在 Linux 上自动跳过 `rtx_vsr`（只有 Windows 有），其余全部通过；Linux 的放大用 lanczos（`UPSCALE=lanczos`，预设）或 FlashVSR（`UPSCALE=flashvsr`）。片尾名单会依实际做法自动写成「在 Google Colab 执行」、放大工具照实列名。

## 3b. 本机＋Colab 一起跑（本机有显卡、也有 Google AI 订阅）

```
set H3_BACKEND=both                                # Linux/Mac：export H3_BACKEND=both
python pipeline/template_local/make_film.py h3 amb # 或直接：python cloud/hybrid_h3.py out/h3/S01 out/h3/S02 ...
```
- **做法**（`cloud/hybrid_h3.py`）：所有镜头放进同一个伫列。本机从前面一支一支拿、马上开跑；Colab（只装 H3）开机约 3.5 分钟后加入，每次从后面拿一批（预设最多 8 支）交给 `colab_h3.py batch`，做完再拿。不事先对半分，因为两边速度不同、云端晚开始。**伫列快空时依两边实测速度估算云端该拿几支**（让两边差不多同时做完，少于 2 支就不再派云端）。云端失败的镜头放回伫列给本机重跑；做完在背景 `stop`（`HYBRID_KEEP=1` 不关，审片后重抽可以接著用）。
- **2026-10-11 实测**（直式短片 34 镜、3370 格、DMAD 4 步，RTX 5090＋G4、每批 8 支）：**17.9 分钟**完成（本机 15 支、云端 19 支、失败 0）；同一轮本机每格 0.58 秒 → 全部本机推算 32.6 分钟，**省 45%**；Colab **1.97 单元**（含开机、关机）。G4 开机 216 秒（本机同时先做了 4 支）；每批 8 支约 304–314 秒，其中上传、解压、轮询、下载约 70 秒。
- **这次修进工具的坑**：①最后一批云端拿走 3 支、本机只剩 1 支 → 本机做完空等约 140 秒 → 改成依速度估算尾巴的分配；②每 45 秒轮询一次 → 改 15 秒（`COLAB_POLL`）；③每批 4 支耗损占比太高 → 预设 8 支；④关机算进等待 → 改背景关机；⑤本机要用自己正式版的 `h3_shot.py` → `HYBRID_TOOLS` 指定资料夹；⑥机房每次不同（美国俄亥俄、荷兰），都在授权排除地区；⑦中途要停：本机连 `h3_shot.py` 子程序和 ComfyUI 伫列一起清（`POST /queue {"clear": true}`、`POST /interrupt`），Colab 上的批次要另外 `stop`。
- **什么时候值得**：镜头少于 `HYBRID_MIN`（预设 8）支会自动全部本机跑（不值得等云端开机）；约 20 支以上才明显快。少量重抽直接本机跑。
- **限制**：接力镜头（spec 有 `first_clip`）等两边做完才由本机照顺序跑；本机显卡跑 H3 时不能同时配音（配音要先做完）；云端部分一样有上面的 H3 授权地区问题。本机要先开 ComfyUI。
- 环境变数：`HYBRID_CHUNK`（云端每批最多几支，预设 8）、`HYBRID_MIN`（预设 8）、`HYBRID_KEEP=1`、`HYBRID_TOOLS`、`COLAB_NAME`、`COLAB_POLL`、`HYBRID_COLAB_HOMES`（两个以上帐号，见下）。
- **大量分镜要开几台：开机前先跑 `python cloud/colab_plan.py <spec 清单或镜头资料夹>`，把它印的建议告诉使用者、等使用者同意再开（2026-11-06 起，agent 必做）**。它会读每支 spec 的秒数、步数、解析度估算，查本机忙不忙（ComfyUI 伫列、显卡用量）和各帐号余额，印出 0–4 台的时间与单元，以及一段可以直接问使用者的话。
  - 参数（〈孔子来代课〉第 9 集 220 镜全本机 205.5 分、主题曲 MV 云端两批 29／30 镜校正）：本机 DMAD 每格约 0.51 秒（14 步约 1.07）＋每镜 5 秒；一台 G4（2 个 ComfyUI）≈ 本机 1.5 倍速；开机约 3.7 分、收尾约 1 分；余额实扣每台 8.0–9.7 单元／小时（算 9）。
  - M＝本机全部跑完的分钟数；本机一起跑 T ≈ 3.7 ＋ (M − 3.7) ÷ (1 ＋ 1.5k) ＋ 1；只有云端 T ≈ 3.7 ＋ M ÷ 1.5k ＋ 1；单元 ≈ k × T × 9 ÷ 60。
  - 建议台数：一台一台往上加，多开这台「每多花 1 单元至少省 5 分钟」才加；上限＝帐号数 × 2、余额要够。同帐号两台：家目录写两次（`HYBRID_COLAB_HOMES=default;default`）。
  - 对照实测：第 9 集 220 镜本机独跑公式 205 分／实测 205.5 分（照建议本机＋4 台约 34 分、约 20 单元）；MV 29 镜云端 1 台公式 23.6 分／实测 21.7 分；〈One Minute with Mina〉50 镜云端 1 台 46.7 分／48 分；〈Make Our Own Light〉40 镜 31.9 分／30 分。
  - ⚠ Colab 开机失败时 `hybrid_h3.py` 会默默全部改本机跑（第 9 集就这样多跑了约 3 小时）→ 开跑后看 log 确认云端真的接到镜头，没接到就告诉使用者。
- **同一个帐号开两台 G4 也可以（2026-11-06 实测，Google AI 方案帐号）**：`colab new -s <名称> --gpu G4` 用不同名称连开两台，各约 5 秒 READY，两台都是完整的 RTX PRO 6000 96 GB（机房可能不同，例如一台荷兰一台美国）；`colab usage` 显示扣费率 20.1 单元／小时（两台合计，单台约 10）。用 `colab_h3.py --name h3_2 ...` 就能在同一个家目录开第二台；记得两台都要各自 stop。
- **两个 Colab 帐号同时跑（2026-10-29 实测）**：Colab CLI 的登入凭证放在家目录（`~/.config/colab-cli/token.json`），一个家目录＝一个帐号。第二个帐号：建一个空资料夹（例如 `C:\colab_home2`），在 cmd 跑 `set USERPROFILE=C:\colab_home2`、`set HOME=C:\colab_home2`、`colab usage`，浏览器登入第二个帐号（一次就好）。之后 `set HYBRID_COLAB_HOMES=default;C:\colab_home2`（Linux／macOS 用 `:` 分隔）→ 本机 1 个 ComfyUI＋每台 G4 各 2 个，各扣各自帐号的单元。实测 38 支 3–4.5 秒短镜：**16.5 分钟**（本机 10、两台云端 10＋18；推算全部本机约 37 分），两个帐号各扣约 2.0 单元。G4 开机看机房：美国 216 秒、荷兰 8.5 分（下载模型慢）→ 镜头少于约 20 支时开第二台不太划算。

## 4. 实测：该租哪张卡

同一个镜头（90 格、1344×768、DMAD 4 步）、同一个 seed，与 RTX 5090 本机成品比较：

| GPU（Colab） | 显存／记忆体 | 每小时运算单元 | 每支秒数 | 每支单元 | 跟 5090 成品比 |
|---|---|---|---|---|---|
| **G4＝RTX PRO 6000 Blackwell** | 96GB／176GB | **8.90** | **42**（模型留在显存）／50（每支重载） | **0.10** | PSNR 45.9 dB |
| A100 40GB | 40GB／83GB | 5.30 | 210–270 | 0.31–0.40 | PSNR 45.8 dB |
| L4 | 22.5GB／52GB | 1.54 | 310–399 | 0.13–0.17 | PSNR 43–45 dB |
| T4 | 15GB／**12GB** | 1.07 | 记忆体太小，跑不了 | — | — |
| H100 | — | — | AI Pro 帐号不能开（「没有配额或权限」） | — | — |

- **H3 只用 G4**：L4 每一步取样约 33 秒、G4 约 4.4 秒（慢 7.5 倍，主因是晶片算力，不是记忆体），单元反而多 3 成；A100 吃不到这套 int8／FP16 累加加速，慢 4–5 倍、单元 3 倍。画面都一样，只差速度。
- G4 和 RTX 5090 是同一颗 GB202 晶片、记忆体频宽相同，所以**单支速度跟 5090 一样**；多出来的是显存、记忆体和 48 核 CPU。

### 榨干 G4（`setup_h3.py` 预设已套用）

| 设定 | 每小时几支 | 每支单元 |
|---|---|---|
| 一次 1 支、`--cache-none`（Windows 原设定） | 71 | 0.125 |
| 一次 1 支、模型留在显存 | 85（连续 24 支稳定） | 0.105 |
| 2 个 ComfyUI 同时开始 | 110，但 8 支失败 1 支（两边同时载入文字编码器，96GB 撞满） | — |
| 3 个 ComfyUI | 101，每支 100–116 秒 | 0.088 |
| SageAttention | 每支 46 秒，比 comfy kitchen 的 42 秒慢 | — |
| **2 个 ComfyUI、各 `--reserve-vram 46`、第二个晚 30 秒开始** | **123（10/10 成功）** | **0.073** |

单一支 H3 时 GPU 没满载（存每格 PNG、ffmpeg 合成等 CPU 工作），两支交错可以补空档；但要错开，否则同时载入文字编码器会撞满显存。以上都是同一个 90 格镜头的数字，实际片子长短不一，比例应该差不多。

## 5. 时间、费用、审片

| 项目 | 实测 |
|---|---|
| 从开机到可以跑 H3 | **约 3.5–4 分钟**（下载 55GB 约 170 秒、装套件约 165 秒，两者同时进行） |
| 一支 30 镜短片的 H3 | 约 15 分钟（加开机约 20 分钟、**约 3 单元**） |
| 200 运算单元 | 约 60 支 30 镜短片（只算 H3） |
| 换算台币 | 随用随付每单元约 NT$3.4 → G4 每小时约 NT$30；外租同级 RTX PRO 6000 约 NT$52–67／小时 |

- **Colab 闲置约 20 分钟会自动收回机器**（实测：最后一次下指令后约 18–20 分钟；机器上有程式在等待也一样）。所以：
  - 忘了关机最多浪费约 3 单元；
  - 拍片过程中（拍完 → 检查 → 重拍）**一律开著**，等「确定不再需要 H3、要交给人工审片」才关（重开只装 H3 约 4 分钟、完整安装约 10 分钟）；超过 20 分钟没动作机器会被收回，回来重新 `start` 即可；
  - 要多保一会用 `keepalive`（照样扣单元）。
- `batch` 执行期间每 45 秒查一次进度，顺便维持连线。H3 正在跑但完全不查进度会不会被收回，未测。
- 单元 **90 天后失效**；买太多用不完会浪费。

### Google 方案怎么选

| 方案 | 价格 | Colab 单元 | 每单元 |
|---|---|---|---|
| 随用随付 | 100 个 US$10.49／500 个 US$52.49 | — | 约 US$0.105 |
| Colab Pro | US$10.49／月 | 100 | 约 US$0.105 |
| Colab Pro+ | US$52.49／月 | 600（方案页；有第三方写 500） | 约 US$0.0875 |
| Google AI Plus | NT$165／月 | 未公布 | — |
| Google AI Pro | NT$650／月 | 约 200 | 另含 5TB、Gemini 等 |
| Google AI Ultra | NT$3,300 起 | 未公布（含高阶 GPU、背景执行） | — |

本来就用 Gemini 的人 → AI Pro（等于附送）；只为了 H3 偶尔做片 → 随用随付；量很大 → Pro+；**不建议为了 Colab 买 Ultra**（高阶 GPU 不保证是 H100，G4 已是跑 H3 最划算的卡）。

## 6. 网路

- 55GB 模型是 Colab 机器直接下载，**不经过你家网路**。
- 经过你家网路的只有素材和成品：一张首帧约 1.5MB、一句配音约 0.4MB、一支 768p 成品约 3MB（FlashVSR 1080p 约 15MB）。`batch` 会把一整批打包成一个 zip 上传、一个 zip 下载（Colab CLI 每个档案往返要 2–5 秒，逐档传很慢）。

## 7. 踩坑纪录（都已修进这套工具）

| 问题 | 原因 → 解法 |
|---|---|
| Windows 上 `colab` 一执行就当掉 | `import termios` → `colab_cli_windows_patch.py` |
| Git Bash 上传到 `/content/...` 变成 `C:/.../PortableGit/content/...` | Git Bash 自动转路径 → 本工具用 Python 呼叫 CLI，不经过 Git Bash；自己在 Git Bash 下指令要 `MSYS_NO_PATHCONV=1` |
| `colab exec` 偶尔 `Connection was lost`／`Timeout waiting for reply` | CLI 连线不稳（机器其实正常）→ 自动重试；长工作一律在 VM 上 `nohup` 背景跑、再轮询记录档 |
| 下载模型大量 `HTTP 429 Too Many Requests` | 旧 `download.py` 每 8MB 一个请求打 huggingface.co（26GB＝3,000 多次），多份清单同时跑就被限速 → 改写 `download.py`：转址只解析一次、每档 16 段长串流、可续传、429 退避；全云端安装一次只跑一份清单；可设 `HF_TOKEN` |
| 旧 `download.py` 大档要两倍硬碟 | 先存分段再合并 → 新版直接写进同一个档 |
| whisper：`libcublas.so.12` 找不到 | Linux 的 CUDA 12 函式库是 pip 套件，安装时被滤掉、执行时也不在搜寻路径 → 安装只滤掉 `名称==` 完全相符的 Windows 套件；`tools/stt.py` 在 Linux 先预载 |
| BreezyVoice：`No module named torchmetrics` | 过滤 `^torch` 时连 torchmetrics 一起拿掉 → 同上 |
| 第 2、3 个 ComfyUI 启动失败 | 复制程式码时「跳过 models 资料夹」连 `comfy/ldm/models`（程式码）也跳过 → 只跳过最上层 |
| 字幕、片尾中文变方块 | 字型写死 Windows 路径 → `tools/fonts.py`（Linux 用 Noto CJK／文鼎楷书，`install_full.sh` 会装） |
| RTX VSR 在 Linux 不能用 | `nvvfx` 只有 Windows → `UPSCALE=lanczos`（预设）或 `flashvsr` |
| Colab 的 L4／A100 跑 H3 | 能跑但又慢又贵 → 只用 G4 |

## 8. 档案

| 档案 | 在哪执行 | 做什么 |
|---|---|---|
| `colab_h3.py` | 你的电脑 | 开机、装环境、批次跑 H3、保持连线、关机、全云端 smoke／film（只用 Python 标准函式库） |
| `hybrid_h3.py` | 你的电脑 | 本机＋Colab 一起跑 H3（共用伫列；`H3_BACKEND=both`；`HYBRID_COLAB_HOMES` 可同时用两个以上帐号） |
| `colab_cli_windows_patch.py` | 你的电脑（Windows） | 让 Colab CLI 在 Windows 上能启动 |
| `vm/setup_h3.py` | Colab | ComfyUI 0.40＋H3＋DMAD＋Veda（2026-10-16），开 1–3 个 ComfyUI（预设 2 个、错开） |
| `vm/run_batch.py` | Colab | 把一批镜头分给各个 ComfyUI 跑，写进度、打包成品 |
| `vm/install_full.sh` | Colab | 全云端：语音三环境＋ComfyUI 全套＋字型＋全部模型 |

已有类似但只做「上传参考图＋提示词 → Colab 跑 H3 → 下载」的开源工具：[killkli/minimax-h3-colab-skill](https://github.com/killkli/minimax-h3-colab-skill)（Codex 技能）。
