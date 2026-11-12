# pipeline：每支片的制作脚本

> **做新片请用 [`template_local/`](template_local/README.md)**：复制资料夹、改 `film.json`、跑 `make_film.py`，全本地从角色做到成片＋自审。下面的 `example_D-7/` 是原频道的完整脚本（云端 Image 2.5 首帧、旧配音流程），留作参考。
>
> **饶舌对决请用 [`template_battle/`](template_battle/README.md)**：两首歌（Suno 或本机 YuE2）＋`battle.json` → `make_battle.py` 做到 3–4 分钟横式对决成片＋自审；先读技能 `agent/skills/rap-battle/`。

`example_D-7/` 是〈D-7〉（段考三种学生，2026-10-05，120 秒）实际用过的全套脚本，只把写死的个人路径改成 `C:\AI\tools` 惯例。

## 开新片

1. 复制整个资料夹，改名 `<片名>_<日期>/`，放在专案的 `短片/` 底下。脚本用 `HERE.parents[1]`（专案根目录）找 `角色资产/`、`音效库/`、`templates/seals/`，所以把本 repo 的 `templates/` 也复制到专案根目录，`sfx/` 复制到专案根目录并改名 `音效库/`。
2. 改这几张表，其他通常不用动：

| 档案 | 改什么 |
|---|---|
| `剧本.md` | 你的剧本与镜表 |
| `blender/make_plan.py` | 机位与站位（不做预演可略） |
| `gen_frames.py` | `REF`（角色定妆照路径）、`KEEP`（角色外观锁定句）、`SHOTS`（每镜首帧描述） |
| `voice_plan.py` | `REFS`（各角色参考音）、`LINES`（台词）、`TTS`（同音字替换；**新片改用 BreezyVoice＋注音标记，见 docs/02 第 4–5 步**） |
| `plan_h3.py` | `SUBJ`（角色英文描述与声音）、`S(...)` 每镜动作／台词秒数／长度 |
| `assemble.py` | `SEGS`（剪接顺序与段落类型）、`VO`（旁白位置）、`build_audio` 的音效时间点 |
| `music_scenes.py` | `SC`（每段配乐的风格描述与起讫段落） |
| `ending/config.json` | 片尾特写图与工具名单 |

3. 新片建议在 `pipeline_gen.py` 的 `make_spec` 把 `steps=14` 改成加上 `draft=True`（DMAD 4 步；〈D-7〉时还没定案）。

## 执行顺序

```
H3 venv:    python gen_frames.py                 # 首帧 → 人工审 → 建空档 frames_ok
bash:       ./run_queue.sh                        # 等 GPU 空 → 配音 → Breeze → 挑音 → H3
H3 venv:    python assemble.py --ver 1 --vsr      # 先跑一次产生 post/starts.json
H3 venv:    python music_scenes.py                # 依片长生配乐
H3 venv:    python ../../templates/ending/render_ending.py ending/config.json
H3 venv:    python assemble.py --ver 1 --vsr      # 有配乐、有片尾的完整版
H3 venv:    python review.py cut/<片名>_v1_1080p.mp4
Voice venv: python review.py cut/<片名>_v1_1080p.mp4 --asr
```

重拍单镜：`python pipeline_gen.py --retake S07`，再 `python assemble.py --ver 2 --vsr S07`。

## 档案一览

| 档案 | 用途 |
|---|---|
| `gen_frames.py` | Image 2.5 首帧（3 路并行，旧图自动移到 `first/old/`） |
| `sheet_frames.py`、`clip_sheet.py` | 首帧总览图、H3 片段抽格表（给人审） |
| `voice_plan.py`、`voice_stage1.py`、`voice_pick.py` | 配音候选与自动挑音 |
| `voice_more.py`、`voice_robust.py` | 单句补候选、叠环境音测可懂度 |
| `plan_h3.py`、`pipeline_gen.py` | H3 逐镜设定与批次生成＋品检＋换 seed |
| `run_queue.sh` | GPU 排队与串接 |
| `post_fx.py` | 字卡、咒印名片、手机画面、调色 |
| `music_scenes.py` | MiniMax Music 3 分段配乐 |
| `assemble.py` | 剪接、混音、字幕、输出 1080p＋手机版 |
| `review.py` | 自审五遍 |
| `youtube/make_youtube.py` | 封面与 srt 字幕 |
| `制作纪录.md` | 这支片实际遇到的问题与修法 |
