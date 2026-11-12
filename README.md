# 山狮霸的多重宇宙：AI 短片制作工作流（Colab 云端版：Google Colab 云端）

YouTube 频道「山狮霸的多重宇宙」的完整制作做法：每支片 1–3 分钟、16:9、24fps，台湾校园奇幻喜剧。剧本由 AI agent（Claude Code）协作，首帧、影片、配音、配乐用开源模型生成，挑音、后制、自审全部脚本化；人只在剧本、首帧、成片三个关卡验收。

**这一份是给「电脑跑不动 H3、但有 Google AI 方案（或 Colab 运算单元）」的人**：最吃硬体的 MiniMax H3 影片生成送到 Google Colab 的 G4 显卡（RTX PRO 6000 Blackwell 96GB）跑，其余在你的电脑做；连配音都跑不动的人可以整套在云端做。素材和成品一直都在你的硬碟。

> 原专案的本人照片、本人克隆声音、API 金钥、第三方素材、角色定妆照都没有放进来。

## 饶舌对决三分钟上手

两位历史人物各唱一整首歌互呛、DJ 主持的 3–4 分钟横式影片（范例：〈微积分之战〉牛顿 vs 莱布尼兹）。把 `agent/skills/rap-battle/` 复制到你专案的 `.claude/skills/`，跟 Claude Code 说「做一场饶舌对决」，它会带你选题、写歌词、填 `battle.json`，再跑下面这些指令。**整场在 Colab 跑，你的电脑不需要显卡**；每段跑完 `out/` 会同步回本机，看过再跑下一段。

先准备 Google AI Pro（或 Colab 运算单元）＋ Colab CLI（见 [cloud/README.md](cloud/README.md)），然后：
```
xcopy /E /I pipeline\template_battle pipeline\my_battle      # 复制范本（macOS／Linux：cp -r pipeline/template_battle pipeline/my_battle）
python cloud/colab_h3.py start                               # 开 G4＋完整安装（含 YuE2、Ming-3.0-TTS），约 10 分钟
```

### 基本版：全部在 Colab、不用任何金钥（YuE2 生歌＋Qwen-Image 2.1 画图＋Ming 念 DJ）
```
python cloud/colab_h3.py film pipeline/my_battle yue                    # 每人抽 10 首、只留拍速对的 → 听 out/yue/
python cloud/colab_h3.py film pipeline/my_battle songs dj audio         # 听 out/audio/mix.wav
python cloud/colab_h3.py film pipeline/my_battle chars scenes frames    # 看 out/first/_sheet.jpg
python cloud/colab_h3.py film pipeline/my_battle specs h3               # 看 out/review/clips_*.jpg
python cloud/colab_h3.py film pipeline/my_battle cut review srt         # 看 out/cut/ 的完整成片
python cloud/colab_h3.py stop                                           # 一定要关：闲置的 G4 每小时照扣 8.9 单元
```
2026-10-29 在 Colab G4 从头实测通过：一整场约 1.5–2 小时、15–18 运算单元。YuE2 的 rap 狠劲较弱、要多抽；Qwen 画不出双人对峙、场景里的字会乱码；**Qwen-Image 2.1 只能非商业使用**。

### 优化版：Suno 生歌＋Image 2.5 画图（要 Kie.ai 与 OpenAI 金钥）
在 `battle.json` 加一行 `"image_backend": "img25"`，然后：
```
python cloud/colab_h3.py film pipeline/my_battle songtext               # 产生 out/songtext/suno_*.txt
set KIE_API_KEY=你的金钥                                                  # macOS／Linux 用 export
cd pipeline/my_battle
python kie_suno.py submit A a1 && python kie_suno.py poll a1            # 每次 2 版，约 $0.06
python kie_suno.py submit B b1 && python kie_suno.py poll b1            # 听 out/suno/，挑好的存成 song/A.mp3、song/B.mp3
cd ../..
set OPENAI_API_KEY=你的金钥                                               # film 会自动带到 VM，画面上只显示 ***
python cloud/colab_h3.py film pipeline/my_battle songs dj audio         # 听 out/audio/mix.wav
python cloud/colab_h3.py film pipeline/my_battle chars scenes frames    # 看 out/first/_sheet.jpg
python cloud/colab_h3.py film pipeline/my_battle specs h3               # 看 out/review/clips_*.jpg
python cloud/colab_h3.py film pipeline/my_battle cut review srt         # 看 out/cut/ 的完整成片
python cloud/colab_h3.py stop
```
没有 Kie：把 `out/songtext/suno_A_lyrics.txt`、`suno_A_style.txt` 贴到 Suno 网页的 Custom 模式（B 同理）也一样。Suno 编曲最丰富、rap 最凶；Image 2.5 画得出双人对峙和正确的字。原频道两场对决用的就是 Suno＋Image 2.5，但**范本的 Image 2.5 分支还没在 Colab 从头重跑过**。

有显卡想在本机跑：同样的 stage 改成 `make_battle.py <stage…>`，详见 [pipeline/template_battle/README.md](pipeline/template_battle/README.md)。

## 1. 这份是给谁的

| 项目 | 内容 |
|---|---|
| 需要 | **Google AI Pro**（每月约 200 Colab 运算单元；免费试用期间不发）或 Colab 随用随付运算单元；Google 官方 **Colab CLI** |
| 你的电脑 | 任何 Windows／macOS／Linux；有 8GB 以上 NVIDIA 显卡可以在本机做配音，12GB 以上可以本机做首帧；都没有就用全云端模式 |
| 状态 | **2026-10-10 在 Colab 实测**：H3 在 G4 上的成品与 RTX 5090 本机肉眼一致（PSNR 45.9 dB）；全套 smoke_test 在 Linux 上除 RTX VSR（Windows 限定）外全部通过 |
| 速度 | G4 一支 90 格镜头 42 秒（≈ RTX 5090）；2 个 ComfyUI 错开跑每小时约 123 支；从开机到能跑约 3.5–4 分钟 |
| 费用 | G4 每小时 8.90 运算单元；一支 30 镜短片的 H3 约 3 单元 → 200 单元约可做 60 支 |
| ⚠️ 授权 | Colab 的 G4 机房实测只在**美国或欧盟**，正是 MiniMax H3 授权排除的地区。**工具照常使用这些机房、只显示警语，风险由你自负**（详见 [cloud/README.md](cloud/README.md)） |

详细：[cloud/README.md](cloud/README.md)（操作、实测数据、踩坑）、[docs/hardware.md](docs/hardware.md)

### 三分钟上手（Colab 版）

```
uv tool install google-colab-cli
python cloud/colab_cli_windows_patch.py        # 只有 Windows 需要
colab usage                                    # 登入有 Google AI 方案的帐号（浏览器授权，自己做）
python setup/detect_hardware.py                # 看每个元件建议在本机还是云端跑
python cloud/colab_h3.py start                 # 开 G4、完整安装（同第一份完整版，约 10.5 分钟）；只要 H3 加 --h3-only（约 3.7 分钟）
python cloud/colab_h3.py batch <你的分镜>/spec.json ...
python cloud/colab_h3.py stop
```
本机什么都跑不动：`python cloud/colab_h3.py start` → `smoke` → `film pipeline/template_local <stage…>`（见 [cloud/README.md](cloud/README.md) §3）。2026-10-10 一个没看过本专案的 agent 只看这份 repo，用全云端模式约 54 分钟、约 8 个运算单元做出范本短片（38.5 秒 1080p）。

> 下面第 2–4 节是四份 repo 共用的本机流程说明（装 ComfyUI、`C:\AI` 路径、`configs\profile.cmd`）。**Colab 版只要做你本机要跑的那部分**；完全不在本机跑的人，直接照上面的三分钟上手和 [cloud/README.md](cloud/README.md)。

## 四个版本

同一套工作流，依硬体分成四份 repo，内容只差在硬体说明与设定档（每一份都有 cloud/，本机跑不动时可以把 H3 送到 Colab）：

| repo | 硬体 | 显卡 | 记忆体 |
|---|---|---|---|
| [shanshiba-workflow-32gvram-64gram](https://github.com/mathruffian-dot/shanshiba-workflow-32gvram-64gram) | 32GB VRAM＋64GB RAM | RTX 5090 32GB（或其他 32GB 显卡） | 64GB 以上 |
| [shanshiba-workflow-16gvram-64gram](https://github.com/mathruffian-dot/shanshiba-workflow-16gvram-64gram) | 16GB VRAM＋64GB RAM | RTX 4080／5070 Ti／5080 16GB | 64GB |
| [shanshiba-workflow-16gvram-32gram](https://github.com/mathruffian-dot/shanshiba-workflow-16gvram-32gram) | 16GB VRAM＋32GB RAM | RTX 4080／5070 Ti／5080 16GB | 32GB |
| **→ 本 repo** | Google Colab 云端 | 不需要（H3 用 Colab G4；有 8–12GB 显卡可本机做配音、首帧） | 不限 |

> ⚠️ **本 repo 预设给非商业用途**（教学、研究、个人创作）。用到的 **Qwen-Image 2.1、Breeze TTS 2 只能非商业使用**；要营利请照 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 换掉这两个（例如生图改用云端 Image 2.5、角色参考音改用 VoxCPM2 声音设计或真人录音）。台词配音用的 BreezyVoice 是 Apache-2.0，可商用。另外**MiniMax H3 的授权排除美国、欧盟、英国、南韩**；MiniMax H3／Music 3 要求公开内容标示 AI 生成。本 repo 不含任何模型权重。

## 2. 流程一览

```
选题 → 剧本 ─✅─→ 角色定妆照（Qwen-Image 2.1）→ 首帧（Qwen-Image-Edit）─✅─→ 角色参考音（Breeze 设计，一次）
     → H3 生成（DMAD 4 步，台词由 H3 拿角色参考音自己念）→ 听写比对台词 → RTX VSR 放大 → 后制（名片、字卡、音效、配乐、字幕）
     → 组装 → 片尾 → 自审五遍 → 封面＋YouTube 资讯 ─✅─→ 上片
                                           ✅ = 人工验收关卡
```

全部在本机生成（只有 BreezyVoice 备案挑音用的「台湾国语答案卷」edge-tts 需要连网，没网路可改用本地 Breeze）。

> **2026-10-23 预设改变：画面内的台词改成「H3 自己念＋角色参考音」**（h3_shot spec 的 `audio.voice_ref`），不再先用 BreezyVoice 配音当固定音轨。原频道在 RTX 5090 实测（同一场戏三镜）：声音像参考音的程度和 TTS 差不多（声纹 0.66 对 0.68）、三镜最像同一个人（0.75）、表演比固定音轨生动。BreezyVoice 固定音轨改当备案（H3 念错抽不出来、数字日期难字、要精准时间点的声画同步）。⚠ **本 repo 的成片范本 `make_film.py` 已改成这个预设，但还没在本 repo 从头实测**；遇到问题可在 `film.json` 设 `"voice_mode": "fixed"` 退回旧做法。
> **2026-10-24 新增（选用）：远景小脸精修 `tools/face_refine.py`**。远景里脸小于约 50 px 的角色，放大前追脸、用 H3 低强度重画脸再贴回，原频道 3 镜实测 25–30 px 的脸从一团糊变成认得出本人、不闪，每镜约 30 秒（只在 ComfyUI 0.40＋RTX 5090 测过；要另装节点与 23GB 模型，见 [docs/06_安装.md](docs/06_安装.md)）。同日也实测了社群微调模型 Singularity V2，**不采用**（参考音较不像本人、会改掉首帧背景），结果在 [docs/03_规则与踩坑.md](docs/03_规则与踩坑.md)。

每一步用哪支脚本、输入输出是什么：[docs/02_端到端流程.md](docs/02_端到端流程.md)；本地角色与首帧做法：[docs/07_本地角色与首帧.md](docs/07_本地角色与首帧.md)。

**装好之后先跑全本地示范片** `pipeline/demo_local/run_demo.py`：从零做两个角色、4 镜、配音、配乐，约 17 秒成片，证明整条工作流在你的电脑上能跑通。

## 3. 目录

```
README.md
docs/
  01_总览与架构.md          三层架构、为什么这样分
  02_端到端流程.md          逐步骤：工具、产出、耗时、人工关卡
  03_规则与踩坑.md          所有规则（附理由）＋踩坑对策
  04_自审清单.md            review.py 五遍＋常退件清单
  05_agent协作与知识库.md   让 AI agent 长期接手的做法
  06_安装.md                环境、模型、资料夹惯例
  07_本地角色与首帧.md      不用云端：Qwen 做角色与首帧（两种做法）
  hardware.md               ⭐ 你这个硬体版本：模型组合、启动参数、实测数据、风险
tools/                      全域工具（放到 C:\AI\tools）
  h3_shot.py ⭐             分镜 JSON → 官方格式提示词 → 格式检查 → H3 生成
  make_breezyvoice.cmd      台词配音备案：BreezyVoice 每句 8 候选 → 听写＋腔调自动挑（预设改由 H3 自己念）
  gen_image.py              本机 Qwen-Image 2.1／Qwen-Image-Edit 生图（`--turbo`＝8 步草稿模式）
  make_whitemodel.py        舞蹈／武打：原片 → 灰色白模影片，当 H3 动作参考
  make_narration.py         口播／旁白：BreezyVoice 一次念 2–3 句、停顿照标点、自动挑候选
  cosy_vc.py                换声：Seedance 等云端影片的台词换成角色音色，字的时间不变（选用）
  vc_swap.py                换字：念错的字用 Ming 角色声音重念、接回原位置再整句换声，不重拍影片（选用）
  start_comfy.cmd           启动 ComfyUI
  img25.py                  OpenAI Image 2.5 生图／编辑（选用，云端）
  pron_check.py／pron_compare.py  中文配音声调审核
  ...（完整清单见 docs/06_安装.md）
pipeline/template_local/    ⭐ 做新片的范本：改 film.json → make_film.py 从角色做到成片＋自审
pipeline/demo_local/        全本地示范片（4 镜，安装验证用，不需要任何素材）
pipeline/example_D-7/       原专案一支真实短片〈D-7〉的全套脚本（参考用：首帧用云端 Image 2.5、旧配音流程，不能直接照跑）
setup/                      安装：模型下载清单（锁定版本＋逐档杂凑）、套件清单、smoke_test、硬体侦测
cloud/                      ⭐ 本机跑不动时：H3（或整套流程）送到 Google Colab G4 跑（colab_h3.py；见 cloud/README.md）
sfx/                        58 个 Freesound CC0 音效（脚步、翻页、门、球、欢呼…）
templates/                  片尾范本、咒印法阵素材
agent/                      CLAUDE.md 范本、编剧技能、Blender 预演技能
configs/profile.cmd         这个硬体版本的环境变数
```

## 4. 最快上手

0. **AI agent 请先读 [AGENT_SETUP.md](AGENT_SETUP.md)**，它会一步步带你检查硬体、安装、下载、验证。`python setup/detect_hardware.py` 会列出每个元件建议在本机还是云端跑；**本机跑不动 H3 → [cloud/README.md](cloud/README.md)**（用 Google AI 方案的 Colab 运算单元跑）。
1. 照 [AGENT_SETUP.md](AGENT_SETUP.md) 装好 ComfyUI＋H3、Voice 环境、Breeze TTS、BreezyVoice，把 `tools/` 复制到 `C:\AI\tools`。
2. 先读 [docs/hardware.md](docs/hardware.md)，再在同一个 cmd 视窗 `call configs\profile.cmd` 套用这个硬体版本的设定，然后执行 `C:\AI\tools\start_comfy.cmd`。
3. 跑 `setup\smoke_test.py` 与 `pipeline\demo_local\run_demo.py` 确认全部正常。
4. 开始做自己的片，照下面的检查表一步一步来（2026-10-07 实测：一个没看过本专案的 agent 照这个 repo，约 45 分钟做出 7 镜、28 秒的片）。

| # | 步骤 | 工具 | 看哪份文件 | 产出 | 要人工看吗 |
|---|---|---|---|---|---|
| 1 | 剧本＋镜表（每镜 ≤12 秒） | `agent/skills/shanshiba-drama` | SKILL.md 开头的版本说明、`docs/03` | `剧本.md` | ✅ 确认剧本 |
| 1.5 | 生成前试映：16 宫格分镜草图＋**文字读本**（不做 TTS；用字数估片长与每镜 H3 镜长＝字数÷3＋2 秒） | `make_storyboard.py`（要 OpenAI 金钥，没有就跳过草图）、`assemble_read.py` | `agent/skills/shanshiba-drama/references/table-read.md` | `preview/读本试映.mp4`、`读本_timeline.json` | ✅ 看完说「通过」才做首帧 |
| 2 | 角色定妆照（单张、灰底、半身） | `gen_image.py`（Qwen-Image 2.1） | `docs/07` §1 | `chars/<角色>.png` | ✅ 挑一张定案 |
| 3 | 场景母版（空景，之后裁成各镜景别） | `gen_image.py` | `docs/07` §4 | `masters/*.png` | |
| 4 | 首帧（附定妆照＋母版裁切，**每镜照抄角色完整外观描述**） | `gen_image.py --model qwen-edit --ref` | `docs/07` §2–3 | `first/<镜>.png` | ✅ 逐张看：脸、服装、多手多脚、背景有没有字 |
| 5 | 角色声音（一次） | `breeze_batch.py`（设计参考音） | `docs/03` §5 | `voice/ref_<角色>.wav` | ✅ 听一次、定案后不换 |
| 6 | H3 每镜（DMAD 4 步、只给首帧；**有台词给角色参考音 `audio.voice_ref`、H3 自己念**（两三人对话同镜用 `voice_refs` 各给参考音）；看得到脸又没台词的镜给静音；**`action` 照官方结构写 50–120 字具体动作**，动作镜首帧画动作开始前） | `h3_shot.py`（spec 加 `"draft": true`） | `docs/02` §6「动作写法」、`docs/03` §4–5、`tools/examples/` | `h3/<镜>/clip.mp4` | ✅ 抽格看：换脸、多人、镜头漂移；**听写比对台词**（H3 会改用词） |
| 7 | 配乐（纯器乐、多抽几个 seed，挑人声残留最少的） | `gen_music3.py` → `audio-separator` | `docs/02` §9 | `music/*.flac` | |
| 8 | 放大、剪接（H3 自己念的台词不提前；BreezyVoice 备案台词提前 0.2 秒）、配乐压低（台词期间 15–30%）、响度、字幕 | `upscale_vsr.py`、ffmpeg | `docs/02` §7、§10（**响度指令照抄，`alimiter` 要 `level=false`**） | `cut/<片名>_1080p.mp4` | |
| 9 | 片尾（工具名单＋AI 生成标示） | `templates/ending/render_ending.py` | `templates/ending/README.md` | `ending.mp4` | |
| 10 | 自审五遍（抽格、ASR、杂讯、黑画面与响度、切点） | 参考 `pipeline/example_D-7/review.py`、`noise_scan.py`、`stt.py`、`framecheck.py`（每秒一格）、`clipcheck.py`、`flashcheck.py` | `docs/04_自审清单.md` | `review/` | ✅ 最后一定给人看成片 |

**最快的做法：复制 [`pipeline/template_local/`](pipeline/template_local/README.md)，只改 `film.json`**，`make_film.py` 会把上面 2–10 步全部做完（已附一支 7 镜范例片的设定，从零重跑验证过）。`pipeline/demo_local/` 是 4 镜的最小安装验证；`pipeline/example_D-7/` 是原频道一支 120 秒成片的完整脚本，可参考剪接与自审写法，但它用云端 Image 2.5 首帧和旧配音流程，**不能直接照跑**。

建议让 AI agent 来跑：把 [agent/CLAUDE.md范本.md](agent/CLAUDE.md范本.md) 放进专案根目录，它会照规则做、自审、写纪录。

## 5. 最重要的十条经验

1. **H3 提示词一律用官方六段格式**，用 `h3_shot.py` 从 JSON 组，不手写。
2. **预设只给首帧**；多人镜加身份参考图会多长出一个人。
3. **DMAD 4 步就是定稿**：抽到满意的直接用，同 seed 换 14 步画面会不同。
4. **单镜 ≤12 秒**；15 秒会漂移、自己切镜。
5. **不说话的镜头给静音引导音轨**，否则角色会自己嘟囔。
6. **画面上的中文一律后制叠字**，H3 会把字写成乱码。
7. **台词让 H3 拿角色参考音自己念**（2026-10-23 起）：Breeze 设计角色声音（一次）→ spec 写 `audio.voice_ref` → 听写比对原文（H3 会改用词，例：「二十四号」→「二十四日」）、抽 2 个 seed。念错抽不出来的句子才改用 **BreezyVoice** 固定音轨（每句 8 候选、念不准的字标注音 `连假[:ㄐㄧㄚ4]`）。
8. **低头、转身后脸会换人** → 再生一张「动作结束时」的画面当尾帧锁住（原频道用 Image 2.5；本地可用 Qwen-Image-Edit 附定妆照）。
9. **先做最难的一镜再批次**，不要整片生完才发现共通问题。
10. **不合格就重拍到合格**，不靠剪掉躲；给人看并排影片，数字只当备注。

## 6. 这个 repo 没有放的东西

| 东西 | 原因 | 你要自己准备 |
|---|---|---|
| 原频道的角色定妆照、转面图、表情表 | 频道角色资产 | 用本机 Qwen-Image 2.1 为自己的角色做单张半身定妆照（见 [07_本地角色与首帧.md](docs/07_本地角色与首帧.md)） |
| 配音参考音 | 含本人授权克隆声音 | 自己录或用 Breeze 设计；台词预设由 H3 拿参考音自己念，BreezyVoice 为备案 |
| 模型权重 | 档案大、各有授权 | 照 [AGENT_SETUP.md](AGENT_SETUP.md) 第 3 节下载（约 150GB） |
| 成片影片 | 档案大 | 看频道 |
| OpenAI 金钥（选用） | 预设不用；想改用云端 Image 2.5 生首帧才需要 | 设环境变数 `OPENAI_API_KEY`，用 `tools/img25.py` |
| Kie.ai 金钥（选用） | 想用云端 Seedance 2.5 生影片才需要（约 63 点／秒，200 点 ≈ 1 美元） | 设环境变数 `KIE_API_KEY`，用 `tools/sd25_shot.py`；有台词的镜一定给角色参考音 |
| Google AI 方案／Colab 运算单元（选用） | 本机跑不动 H3 时才需要 | 见 [cloud/README.md](cloud/README.md) |

（音效有附：`sfx/` 里 58 个 Freesound CC0 音效。）

## 7. 授权

| 内容 | 授权 | 档案 |
|---|---|---|
| 本 repo 的程式码（`*.py`、`*.ps1`、`*.cmd`、`*.sh`、设定档） | **MIT** | [LICENSE](LICENSE) |
| 本 repo 的文件与素材（`*.md`、技能文字、范例图） | **CC BY-NC 4.0**（姓名标示、非商业） | [LICENSE-docs.md](LICENSE-docs.md) |
| 用到的模型与第三方工具 | 各自的授权（**不随本 repo 散布，自行下载**） | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

fork 或转载时请保留这三个档案。用这套工作流做出来的影片要遵守各模型的条款，特别是：MiniMax H3 的使用地区限制、MiniMax Music 3 的标示与 AI 揭露、Breeze TTS 2 的非商用限制（细节见 THIRD_PARTY_NOTICES.md）。
