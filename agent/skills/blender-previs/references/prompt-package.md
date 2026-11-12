# 提示词与素材包（交付包）

> **2026-09-28 起：实际送 H3 的提示词一律用 `C:\AI\tools\make_shot.cmd`（`h3_shot.py`）产生**，不要手抄下面的范本。把本技能产出的首帧、Blender 镜位影片（`camera_video`）、声音（`audio.voice_ref` 或 `audio.fixed`）、每镜动作与台词写进分镜 JSON，工具会组成官方六段格式（段名**要有冒号**、`<Subject N> (S1)`、`<d>[Chinese]…</d>`、画外音 `says in an off-screen voiceover … lips remain completely closed`、环境音不写台词、无配乐写 `N/A`）并做格式检查。下面 v5 范本保留作为**内容**参考（每个参考素材要写清楚用途），格式以工具为准。说明见 `C:\AI\tools\README.md` §2b。

## 一个已修好的关键缺陷

早期版本的 `build_prompt()` 把参考影片接进去，却**没有定义 `<Video 1>` 的用途**，模型不知道那只是镜位参考。修正后必须在 `subject_definitions` 明确说明每个参考的角色。**这是已记录的实际缺失，新片不要再犯。**

## 提示词结构（v5 已验证）

```
subject_definitions
<Picture 1> is the exact photographic first frame, supplying real human identities, skin,
clothing, room materials, lighting and camera composition.
<Video 1> is ONLY a Blender camera and spatial-layout guide. Its low-poly figures and colors
are proxies, NOT characters or visual style. Ignore proxy material, shape and rigid-body
stillness; keep the camera path and spatial relationships.
<Audio 1> is the exact final vocal track, including all pauses and silence, to be copied
unchanged.

summary
[keyframe completion + reference generation + audio reuse] One continuous real live-action
Taiwanese dramatic film shot, not animation.

retention_analysis
<Picture 1>: fully_preserved - identities, real clothing, layout, lighting.
<Video 1>: partially_preserved - camera trajectory and room geometry only, discard mannequin
appearance and stiffness.
<Audio 1>: fully_copy - precise waveform, timing and pauses.

detailed_description
Real camera cinematography, natural skin detail and cloth. [Shot 1] Begin exactly from
<Picture 1>. <本镜动作> <本镜台词或静默>. The real human lips, jaw, cheeks, breathing,
eye-lines and subtle expressions belong to one coherent performance, not a photograph with
only a moving mouth. Maintain the original seats throughout.
One shot only; no cuts, portraits, inserts or new people. Follow the guide camera while
retaining the photographic first-frame composition. No text or graphics.

overall_soundscape
Reuse <Audio 1> exactly with its silence; no additional speech.

non_diegetic_music
None.
```

## 台词写法

| 情况 | 写法 |
|:---|:---|
| 有说话者 | `The <角色> (S1) says exactly: <d>[Chinese] <台词></d>` |
| 说话者在画面外 | `The <角色> is OFFSCREEN (S1) and asks: <d>[Chinese] <台词></d>` |
| 无人或静默 | `No physical speaker. The guide audio is silence. Keep visible mouths quiet.` |

## 静止镜的相机契约（必加）

```
CAMERA CONTRACT: Completely locked tripod at the first-frame position, same lens, same
framing for the entire shot. No pan, track, orbit, push, zoom or change of viewpoint.
Keep the same visible people and background from beginning to end. Any other person remains
physically offscreen; nobody enters. Natural facial performance, not a frozen frame.
```

**只有真的做过 keyframe 运镜的镜头才能不写这句。** 标 locked 却写推进是已记录的自相矛盾。

## 逐镜加注（依实际问题）

| 镜头类型 | 加注 |
|:---|:---|
| 多人同框 | `Both men must stay visible simultaneously, friend LEFT and teacher RIGHT, throughout the complete shot.` |
| 只该出现一人 | `Only the <角色> is visible. The other remains outside the frame to the right. Exactly one visible person.` |
| 道具不可举起 | `hand quietly tucks paper below the crop, without raising or displaying it.` |
| 实体道具帽 | `is a real sewn costume prop with rigid resin button eyes and sewn muzzle: these have no eyelids, no blinking or animal expressions. Only the real human face beneath it performs.` |

## 对嘴相关（本专案的实际界线）

- **配音先定稿**，画面与引导用同一份音讯；**不要用后换声音掩盖不同步**。
- 冻结实际 audio latent（v5 脚本 version ≥ 4）比只靠引导更稳。
- **长静默**（说话→停顿→再说话）要另外处理：依音讯 RMS 找出静默段，在该段中央加入**完整参考画面的闭口引导**，并在提示词写明时段。D1 长停顿、D2 片首开口经此改善（抽查，非逐音素认证）。
- 过多首尾／中间锚点会让表演僵硬：**只在需要的区间设锚点**。
- **未量测音素同步就照实写「未做逐音素认证」**，不可写成完美对嘴。

## 素材包内容

```
<片名>/交付包/
├── 提示词_<镜号>.txt            每镜完整提示词
├── 素材/
│   ├── refs/<镜号>/image.png    该镜第一帧参考
│   ├── guide/<镜号>.mp4         Blender 运镜或静止 guide（512×288）
│   ├── guide/<镜号>.png         布置图静帧
│   └── audio/<镜号>/dialogue.wav 该镜配音
├── 逐镜参数.json                 frames / lens / motion / seed / 版本
└── 限制与未验证.md
```

## 其他目标模型

本专案预设 H3。若交外部模型（例 Seedance），**另存一份该模型的提示词**，不要直接沿用 H3 的 `<Picture 1>` 标签语法；共用的是**素材与镜位契约**，不是提示词字串。
