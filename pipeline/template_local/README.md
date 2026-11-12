# template_local：全本地多镜短片范本（做新片从这里开始）

一个设定档 `film.json` 写完整支片（角色、场景、每一镜、台词、配乐、片尾），`make_film.py` 从角色定妆照一路做到成片和自审。全部本机模型，不需要任何云端金钥。

范例 `film.json` 是〈被狗吃掉的作业〉：7 镜、正片约 28 秒＋片尾 9.5 秒。2026-10-07 一个没看过本专案的 agent，只靠本 repo 做出这支片，之后把它写的脚本整理成这个范本，再从零重跑验证过（时间见最后一节）。

## 用法

1. 把整个 `template_local/` 复制一份到 `pipeline/` 底下，改名成你的片名，例如 `pipeline/my_film/`。如果复制到别的地方，请把 `film.json` 的 `repo_dir` 改成指向本 repo 根目录（片尾范本在 `<repo>/templates/ending/`）。
2. 改 `film.json`（栏位说明见下一节）。剧本先用 `agent/skills/shanshiba-drama` 写好、做完生成前试映（16 宫格草图＋读本，`tools/make_storyboard.py`、`tools/assemble_read.py`，见技能的 `references/table-read.md`），听过说「通过」再把镜表填进 `shots`。
3. 在同一个 cmd 视窗执行：
   ```
   set PYTHONUTF8=1
   call <repo>\configs\profile.cmd
   C:\AI\tools\start_comfy.cmd
   cd <repo>\pipeline\my_film
   C:\AI\H3\venv\Scripts\python.exe make_film.py chars masters frames
   ```
4. **人工关卡 1**：看 `out/first/_sheet.jpg`。脸、服装要一致，不能多手多脚，背景不能有字，窗户方向要对。不满意的镜：删 `out/first/<镜>.png`，在 `film.json` 的 `seeds` 加 `"frame_<镜>": 新数字`，或改该镜的 `frame` 描述，再跑 `frames`。
5. `make_film.py voices h3`
   - **2026-10-23 起预设 `voice_mode: "h3_ref"`**：`voices` 只用 Breeze 设计角色参考音（`out/voice/ref_<角色>.wav`），台词由 H3 在 `h3` 阶段拿参考音自己念；`h3` 结尾自动从成片分离人声、听写、比对原文，结果写在 `out/voice_picks.json`（`heard`、`match`）。⚠ 这个预设在本范本**还没从头实测**（原频道已在 RTX 5090 实测 H3＋参考音）。
   - H3 念的和原文差太多时程式会停下来：在 `seeds` 加 `"h3_<镜>": 新数字`、删 `out/h3/<镜>/clip.mp4`，再跑 `set ONLY=<镜>` → `make_film.py h3`。抽 2–3 次都不对（常见：数字日期、H3 改成大陆用词），在该句 `line` 加 `"voice_mode": "fixed"`，再跑 `voices h3`（改用 BreezyVoice 固定音轨）。
   - BreezyVoice（`fixed`）的句子 8 个候选都念错时程式也会停下来：在该句加 `"tts"`，念错的字后面标注音，例如 `"tts": "老师，连假[:ㄐㄧㄚ4]要去哪？"`。删掉 `out/voice/bv` 再跑 `voices`。
   - 单字喊叫、同音字这类 ASR 本来就听不准的句子，人听过没问题就用 `set ALLOW_REVIEW=1` 继续。
6. **人工关卡 2**：看 `out/review/clips_<镜>.jpg`（每镜 6 格），检查有没有换脸、多出人、镜头漂移。不满意就删 `out/h3/<镜>/clip.mp4`，在 `seeds` 加 `"h3_<镜>": 新数字`，再跑 `set ONLY=S3 S5` → `make_film.py h3`。
7. `make_film.py amb edl music ending cut review`
8. **人工关卡 3**：看 `out/review/` 的自审结果，最后**一定要人看完整的** `out/cut/film_1080p.mp4`。
   - 只改剪接（`cut_in`、`tail`）：跑 `edl cut review`。
   - 换配乐：改 `music.seeds`，删 `out/music`，跑 `music cut review`。

不给 stage 就是全部依序跑。每一步已经存在的档案都会跳过，所以中断后重跑会从断点接著做。

## film.json 栏位

| 栏位 | 说明 |
|---|---|
| `title` | 片名（片尾标题） |
| `repo_dir` | 本 repo 根目录，相对于这个资料夹（放在 `pipeline/<片名>/` 时用预设 `../..`） |
| `cine` | 每张首帧开头的电影感句（底片、镜头、光线、调色）。光线要写具体，只写 soft daylight 会变平淡白光 |
| `set_sentence` | 场景参考图那句，`{n}` 会换成场景图的编号（角色数＋1） |
| `frame_suffix` | 每张首帧结尾（不要字、不要浮水印…） |
| `voice_mode` | 台词声音：`"h3_ref"`（预设，H3 拿角色参考音自己念）或 `"fixed"`（旧做法：BreezyVoice 配音当固定音轨）。单句可在 `line` 里另设 |
| `h3` | H3 共用设定：`style`、`setting`、`soundscape`（不写台词）、`camera`、`constraints`（每镜都加的限制） |
| `chars.<代号>` | `name`（字幕显示）、`look`（**完整外观描述**，每张首帧都会照抄）、`voice_design`（Breeze 设计声音的描述）、`voice_sample`（设计声音时念的句子，也是 BreezyVoice 的参考逐字稿）、`h3_voice`、`edge_voice`（挑音用的台湾国语答案卷声音）、`sub_color`（字幕颜色，ASS 格式 `&H00BBGGRR`） |
| `masters.<名称>` | 场景母版（空景）提示词。同一个场景的镜头都裁同一张母版，空间才一致 |
| `shots[]` | 每一镜，见下表 |
| `seeds` | 想换的 seed：`char_<角色>`、`master_<名称>`、`frame_<镜>`、`h3_<镜>`、`voice_<角色>` |
| `music` | `caption`（纯器乐描述，写明 Vocal: NONE）、`seeds`（抽几首，挑人声残留最少的） |
| `mix` | `say_lead`（台词比画面提前几秒，预设 0.2）、`default_tail`、`music_under_lines`（台词期间配乐音量，0.15–0.30）、`music_bed_rms`、`target_lufs` |
| `ending` | 片尾：`closeups`（拿哪几镜的首帧当特写）、`cards`（每张卡最多 3 行工具）、`card_dur`、`title_dur`；不要片尾就删掉这个栏位 |

每一镜（`shots[]`）：

| 栏位 | 说明 |
|---|---|
| `id` | 镜号 |
| `refs` | 画面里的角色代号（依序对应 `<image1>`、`<image2>`…）。**只放画面里要演戏的人**，有定义但不入镜的角色 H3 会把他叫进画面 |
| `scene` | `[母版名称, [x0, y0, x1, y1]]`：从母版裁哪一块当场景参考（0–1 比例） |
| `dur` | 秒数（4–12）。有台词时会自动延长：`h3_ref` 到「开口时间＋估计台词长度（每秒约 4 字）＋1.2 秒」，`fixed` 到「开口时间＋配音长度＋0.8 秒」 |
| `line` | `{"who", "text", "at"}`：谁说、字幕文字、第几秒开口（`h3_ref` 时只是参考，实际开口时间由听写抓）；`"voice_mode"`（选填）这句改用别的模式；`"tts"`（选填）是送给 BreezyVoice 的写法（可加注音）。没台词写 `null`（H3 会收到静音音轨，角色不会自己嘟囔） |
| `frame` | 首帧描述：景别、角色在哪、做什么、表情、窗户在画面哪一边 |
| `action` | H3 的动作描述（没台词的镜头写明 He does not speak）。**2026-10-23 起照官方结构写 50–120 字**：「Starting from <Picture 1>, …」首帧定锚→动作开始→持续发展→结果，写身体部位、幅度、次数（见 `docs/02` §6「动作写法」；一句话版动作量只有 1/2.7）。范例 film.json 的 7 镜已改成新写法，2026-10-24 从头重跑验证过（推眼镜、抓头、滑进椅子等动作都照描述演出） |
| `extra_constraints` | 这一镜额外的限制 |
| `amb`、`amb_seed` | `true`＝这镜需要动作音效（翻书包、脚步）：另拍一支 H3 原生音效版，听写确认没有人声才取它的音轨；有人声就换 `amb_seed` 或改用 `sfx/` 的音效 |
| `cut_in` | 剪掉镜头开头几秒（H3 常晚开口） |
| `cut_out` | `"full"`＝用到镜尾；不写＝台词结束＋`tail` 秒 |
| `tail` | 台词后留几秒反应（喜剧停顿） |

## 输出（`out/`）

`chars/` 定妆照、`masters/` 场景母版与每镜裁切、`first/` 首帧与 `_sheet.jpg`、`voice/` 角色参考音、答案卷与 `bv/`（候选、`picks.json`、选中的台词）、`h3/<镜>/` 每镜 spec、提示词与 clip、`music/`、`ending/`、`post/`（`edl.json` 时间轴、放大片段、混音、字幕）、`cut/film_1080p.mp4` 成片＋手机版、`review/` 自审、`timing.json` 各阶段时间。

## 验证纪录

- 2026-10-07 原始版（agent 自己写的 film.py／post.py）：约 45 分钟做完，成片 6 句听写全对、−15.8 LUFS、峰值 −2.0 dBFS。
- 2026-10-07 整理成本范本后，在 RTX 5090 从零重跑（`make_film.py` 不带参数一次跑完）：**共 28.7 分钟**，成片 37.7 秒。

| 阶段 | 秒数 | 备注 |
|---|---|---|
| chars | 26 | 2 张定妆照 |
| masters | 118 | 2 张 2K 场景母版 |
| frames | 605 | 7 张首帧，每张附 2 张参考图约 85 秒 |
| voices | 231 | 2 个角色声音设计＋6 句 × 8 候选＋自动挑选，6 句全部合格 |
| h3 | 414 | 7 镜 DMAD，每镜约 1 分钟 |
| amb | 59 | S2 原生音效版，听写确认没有人声 |
| music | 124 | 3 首，挑人声残留最少的 |
| ending | 66 | |
| cut | 65 | VSR、剪接、混音、字幕、手机版 |
| review | 15 | |

自审结果：响度 −15.7 LUFS、峰值 −2.1 dBFS；没有黑画面、定格、切点明暗跳动、台词重叠或被镜尾切掉；杂讯 7 镜都 ok；成片听写 6 句里 5 句 1.00，「是……邻居的狗」听成「邻居的歌」（0.80，挑音阶段听写正确，混音后的成片要人听确认）。

- **2026-10-24 现行预设重跑**（`voice_mode: "h3_ref"`＝H3 拿 Breeze 设计的参考音自己念、action 照官方结构写 75–101 字、修剪点对齐 1/24 秒；RTX 5090、ComfyUI 0.40、工具用 repo 的 `tools/`）：**共约 27 分钟**，成片 29.5 秒＋片尾 9.5 秒＝39.0 秒（影像、声音都是 39.000 秒）。

| 阶段 | 秒数 | 备注 |
|---|---|---|
| chars | 26 | |
| masters | 124 | |
| frames | 556 | |
| voices | 86 | 只做 2 个角色参考音（台词改由 H3 念，不再每句 8 候选） |
| h3 | 564 | 7 镜 DMAD＋每镜分离人声、听写比对：6 句全部相似度 1.00 |
| amb | 65 | |
| music | 134 | |
| ending | 71 | |
| cut | 65 | |
| review | 17 | |

自审结果：响度 −15.7 LUFS、峰值 −1.9 dBFS；没有黑画面、定格、切点明暗跳动、台词重叠或被镜尾切掉；成片听写 6 句全部 1.00。抽帧：推眼镜再放下手、抓头、慢慢滑进椅子等动作都照 action 演出，脸与服装稳定、没有多出人。
