# template_battle：饶舌对决范本（两首歌 → 3–4 分钟横式对决影片）

两位真实人物各唱一整首歌互呛、DJ 主持、最后留言投票。`battle.json` 写完整场（人物、歌词、DJ 口白、擂台、闪回地点、字卡、每一镜），`make_battle.py` 从两首歌一路做到成片、手机版和自审。

**先读编剧技能 `agent/skills/rap-battle/`**：选题、歌词规则、生歌（Suno 为主、没有 Suno 用 YuE2）、镜表写法、自审表都在那里。

范例 `battle.json`＝原频道〈微积分之战〉牛顿 vs 莱布尼兹（2026-10-28，49 镜、约 3 分 9 秒）。范本不附歌曲档（Suno 生成），要跑范例请先用 `songtext` 的文字自己生两首。

## 用法

1. 把整个 `template_battle/` 复制一份到 `pipeline/` 底下改名（例如 `pipeline/my_battle/`）。放在别的地方的话，把 `battle.json` 的 `repo_dir` 改成本 repo 根目录（可以写绝对路径）。
2. 照技能写好设计与歌词，填进 `battle.json`（栏位见下）。
3. 生歌：
   ```
   <Voice venv>\python make_battle.py songtext
   ```
   - **有 Suno**：把 `out/songtext/suno_A_lyrics.txt`、`suno_A_style.txt` 贴到 Suno 网页的 Custom 模式（B 同理），或用 `python kie_suno.py submit A`（环境变数 `KIE_API_KEY`）。
   - **没有 Suno**：`make_battle.py yue`：YuE2 14 版（配方 `templates/song_yue2_v14/README.md`）每人抽 10 首 → 只留目标 BPM、逐句听写排序 → 第一名放到 `song/`。**一定要人听 `out/yue/<A|B>/` 的候选**，换歌就转档覆盖 `song/A.mp3`。
   - 挑好的歌放成 `song/A.mp3`、`song/B.mp3`（或改 `rappers.<A|B>.song`）。
4. 在同一个 cmd 视窗：
   ```
   set PYTHONUTF8=1
   call <repo>\configs\profile.cmd
   C:\AI\tools\start_comfy.cmd
   cd <repo>\pipeline\my_battle
   C:\AI\Voice\venv\Scripts\python.exe make_battle.py songs dj audio
   ```
   看 `out/song/songs_report.json`：逐句听写低分的句子去听；`last_word_end`（最后一个字唱完）不对就在 `battle.json` 填秒数重跑。听 `out/audio/mix.wav` 确认 A→B 的接点和 DJ 口白。
5. `make_battle.py chars scenes frames` → **人工关卡 1**：`out/chars/`（三人分得出来）、`out/scenes/arena.png`（配色、没有字和旗子）、`out/first/_sheet.jpg`（每镜首帧）。重画：删那张 png，那镜加 `frame_seed_bump` 或改 `frame`，再跑 `frames`。
6. `make_battle.py specs h3` → **人工关卡 2**：`out/review/clips_*.jpg`（每镜 4 格：换脸、多出人、旗子、自己切镜、手糊）。重拍：那镜加 `seed_bump`（会切镜的再加 `last_first: true`），再跑 `specs h3`。
7. `make_battle.py cut review srt` → **人工关卡 3**：照技能的 `references/review-checklist.md` 看 `out/review/fc_v1/sheet_*.jpg`，**最后一定要人看完整成片** `out/cut/<片名>_v1_1920x1080.mp4`。改版：`--ver 2`。

### 没有显卡：整场在 Colab 跑

照 `cloud/README.md` 开好 Colab（`python cloud/colab_h3.py start`＝完整安装，已含 YuE2 与 Ming-3.0-TTS），把对决资料夹放在 repo 的 `pipeline/` 底下，分段跑、每段的 `out/` 会同步回你的电脑，人工关卡在本机看：
```
python cloud/colab_h3.py film pipeline/my_battle yue                 # 没有 Suno：云端 YuE2 生歌（有 Suno 就自己放 song/A.mp3、B.mp3，跳过这步）
python cloud/colab_h3.py film pipeline/my_battle songs dj audio      # 听 out/yue 的候选、out/audio/mix.wav
python cloud/colab_h3.py film pipeline/my_battle chars scenes frames # 看 out/first/_sheet.jpg
python cloud/colab_h3.py film pipeline/my_battle specs h3            # 看 out/review/clips_*.jpg
python cloud/colab_h3.py film pipeline/my_battle cut review srt      # 看完整成片
python cloud/colab_h3.py stop
```
资料夹里有 `battle.json`，`film` 就会改跑 `make_battle.py`。Colab 上放大用 lanczos（RTX VSR 只有 Windows）。`h3` 这段在 VM 上开 2 个 ComfyUI、第二个晚 30 秒开跑（`cloud/vm/parallel_h3.py`，跟 template_local 同一套；2026-10-29 补上，之前对决范本在云端只用 1 个，这条还没在 Colab 重跑过）。
- `film` 只同步 `out/` 回来：`yue` 选的歌放在 VM 的 `song/`，本机听 `out/yue/<A|B>/`（排序在 `pick.json`）。要换歌就把那首转成 `song/A.mp3` 放在本机资料夹，下一次 `film` 会一起上传。
- `out/` 只上传 VM 上没有的档；要重做某一镜，照样在 `battle.json` 加 `seed_bump`／`frame_seed_bump`（删本机的档不会删到 VM 上的）。
- 跑完一定要 `stop`：闲置的 G4 每小时照扣 8.9 单元。

不给 stage 就从 `songs` 依序跑到 `srt`。已存在的输出会跳过，中断后重跑会接著做。还没跑 H3 的镜，`cut` 会用首帧静态图代替（没有首帧就用灰底镜号），可以先看节奏。

| 环境变数 | 用途 |
|---|---|
| `AI_ROOT`、`AI_TOOLS` | 安装根目录（预设 `C:\AI`）、工具目录（预设 `C:\AI\tools`） |
| `COMFY_DIR` | ComfyUI 资料夹（`gen_image.py` 从它的 `output/` 拿图） |
| `H3_BACKEND` | `local`｜`colab`｜`both`（同 template_local；不设就看显卡自动选） |
| `UPSCALE` | `rtxvsr`（Windows 预设）｜`lanczos`（Linux／Colab） |
| `ONLY` | 只做这几镜（`frames`、`h3`），例如 `set ONLY=N04 L06` |
| `ALLOW_REVIEW=1` | DJ 口白候选听写都不准、但人听过没问题时继续 |
| `DJ_TTS` | `ming`（预设，Ming-3.0-TTS，MIT 可商用）｜`breezyvoice`（旧做法） |
| `YUE_SEEDS` | `yue` 每人抽哪些 seed（预设 `1,2,…,10`） |
| `FONT_JHBD`、`FONT_KAI` | 字幕／字卡字型（预设微软正黑体／标楷体，Linux 用 Noto CJK） |

## battle.json 栏位

| 栏位 | 说明 |
|---|---|
| `title` | 片名（片名卡、成片档名） |
| `image_backend` | `qwen`（预设，本机 Qwen-Image 2.1／Qwen-Image-Edit 2511，最多 3 张参考图）或 `img25`（OpenAI Image 2.5，`tools/img25.py`，要金钥，最多 5 张） |
| `seed0` | H3 seed 的起点（每镜再依镜号加） |
| `rappers.A/B` | `name`、`short`、`team`（例：金方）、`tagline`（VS 卡小字）、`color`／`glow`（字幕、特效、字卡的己方颜色 RGB）、`look`（外观完整描述，每张首帧照抄）、`person`（man／woman）、`pronoun`、`desc`（H3 用的短描述）、`song`、`suno_style`、`suno_negative`、`yue_style`、`lyrics`（见技能 `references/lyrics.md`）、`intro_card`（直排名牌 `[[文字, 字级], …]`）、`last_word_end`（选填）、`yue_bpm`（选填，`yue` 挑歌的目标 BPM；没填读 `yue_style` 的「NNN BPM」） |
| `dj` | `name`、`short`（字幕名）、`color`、`look`、`desc`、`person`、`pronoun`、`voice_design`（Breeze 设计参考音的描述；要营利就自己录 `out/voice/ref_K.wav`）、`voice_sample`（参考音念的句子＝逐字稿）、`lines`（`open`／`switch`／`verdict`（选填）／`end`）、`end_beats`（片尾三拍大字）、`tts`（选填，念错的句子改写法：Ming 用同音字）、`intro_card` |
| `arena` | `master`（擂台空景提示词，左右两半＝两人的配色）、`keep`（首帧用的擂台锁定句，`{ref}`＝参考图编号）、`light`、`setting`／`style`／`keep_h3`（H3 用） |
| `places.<地点>` | 闪回／插入镜的地点：`light`（首帧光线）、`setting`（H3）、`era`（`period`／`modern`）、`text`（画面里有要保持不变的字） |
| `style_modern`、`style_period`、`film_look`、`no_text` | 插入镜的 H3 风格句、首帧电影感句、不要字的句子 |
| `audience`、`audience_desc` | 观众外观（首帧）、H3 短描述 |
| `cards.<代号>` | 讲白字卡：`lines`（`[[文字, 颜色]]`，颜色 `A`／`B`／`J`／`ink`）、`accent`、`size`；或 `image`（自己画好的 PNG，例如精准的数学图） |
| `vote` | 投票卡：`A`、`B`（挺谁打什么字）、`title`、`sub`、`note` |
| `show_replace` | 歌词→字幕的替换表（国字数字→阿拉伯数字、同音字→原字） |
| `flash_scenes` | 切进这些地点时闪白（其他插入镜直接切） |
| `locked` | 镜头锁死不推近的镜号 |
| `crowd_sfx` | 观众欢呼音效资料夹（预设 `sfx/欢呼`） |
| `tail_ring` | 预设 `true`：杀句后留残响、补伴奏破洞、B 前奏淡入，不会突然切断 |
| `verdict_bed` | 预设 `true`：DJ 收尾口白很长时，用 A 的前奏伴奏压低垫底 |
| `lang` | `zh`（预设）｜`en`：英文对决的对齐、听写、H3 台词语言 |
| `bpm` | 抓拍子的先验（慢歌要给，不然会抓成两倍速） |
| `film_look_insert`、`arena_only` | 插入镜专用的电影感句；`no_text` 里只属于擂台的句子（插入镜会拿掉，空景才不会画出饶舌手或舞台地板） |
| `rappers.B.end_on_hold`、`rappers.B.keep_stop` | 最后一句后面有长音、自己收掉：唱到底就结束，不换伴奏分轨；最后一个音跟音乐一起停：人声慢一点收，那个空档不补 |
| `rappers.<A\|B>.align_from` | 前奏有 Suno 自己加的喊话时，对齐前把这秒数之前静音 |
| `shots[]` | 每一镜，见下表 |

每一镜（`shots[]`）：

| 栏位 | 说明 |
|---|---|
| `id` | 镜号 |
| `at` | 开始时间：秒数｜`["A", i]`（A 第 i 句开口前 0.12 秒）｜`["dj", "switch", -0.3]`｜`["mark", "a_stop", 0.3]`（`a_first`、`a_stop`、`a_end`、`b_zero`、`b_first`、`b_last`、`music_end`）。结束＝下一镜的开始。**范例的秒数是照 Suno 原曲的前奏长度写的**：换歌（例如改用 YuE2，前奏长短不同）后 `frames` 会先检查，列出顺序反掉或太短的镜，照提示改 `at` |
| `kind` | `sing`（对嘴；`voice: "dj"`＝对 DJ 口白）或 `silent` |
| `scene` | `arena` 或 `places` 的地点 |
| `subj` | 画面里的人：`A`、`B`、`K`（DJ）、`T`（观众）。**只放画面里要演戏的人**；双人镜第一位是唱的人 |
| `dist` | `ECU`／`CU`／`MCU`／`MS`／`WIDE` |
| `frame` | 首帧描述（英文，画动作开始前的姿势） |
| `action` | H3 动作（`Starting from <Picture 1>, …`，慢而清楚的手势） |
| `gfx`、`card` | 这镜要叠的字卡代号、直排名牌（`A`／`B`／`K`） |
| `still`、`custom` | 首帧静态慢推、自己做的影片档 |
| `last_first`、`calm`、`draft`、`cons`、`seed_bump`、`frame_seed_bump` | 尾帧＝首帧（防切镜）、慢动作、`false`＝14 步、额外限制句、换 H3 seed、换首帧 seed |

## 自审与修歌工具

都在本资料夹执行（Voice venv）。怎么用、什么时候用，见技能 `references/review-checklist.md` 第 H 节。

| 工具 | 用途 |
|---|---|
| `lyric_audit.py [A B]` | 全曲逐句听写，用拼音比。对齐分数高不代表字唱对 |
| `poly_check.py [--audio]` | 破音字：歌词与 DJ 口白逐字查教育部辞典（简编本＋修订本）找前后文该念的音，检查同音字对不对；`--audio` 用 DJ 录音比各种念法 → `out/review/poly_check.md` |
| `gap_check.py <A\|B>` | 列人声无声段并比对原唱：原唱有声、成品没声的一定要修 |
| `level_scan.py` | 全片音量扫描，抓突然变小声或破洞 |
| `motion_check.py` | 每镜动作量。尾帧＝首帧常把人锁死 |
| `finger_sheet.py [--clips] [镜号]` | 手部放大表。`--clips` 看 H3 成片：首帧 5 根，拍动作时可能多长一根 |
| `voice_diff.py 档案…` | 候选人声跟前面各场比声纹、音高（`BATTLE_FILMS`＝放各场对决的资料夹） |
| `suno_replace.py submit …` | Suno 局部重唱，只换唱歪的那几个字（`SUNO_SRC=标签:第几版`、`SUNO_PROMPT`、`SUNO_PART`） |
| `splice_resing.py plan.json` | 重唱候选接回定稿（人声连音乐整段换）：接点自动搬到两版都没在唱的空隙、窗头窗尾各自对拍子、伴奏音量补平，报告接完拍子差（要 ≤3 ms）与「接点还在字上」的地方 |
| `dj_pause.py <key> 字=秒 ...` | DJ 口白在指定字后面插停顿（切在句尾真正结束的地方，不照对齐器字尾切），`dj_align.json` 一起往后推；要在 DJ 对嘴镜生成前做 |
| `dj_tail_check.py <wav>...` | 查 DJ 口白「句尾被砍成静音」「停顿后冒出的小碎片」；`make_battle.py review` 会自动对 `dj.wav` 跑 |
| `run_shared.py stage…` | 跟别的工作共用 GPU 时跑 `make_battle.py`，不卸载别人的模型 |
| `colab_only.py [镜号…]` | 本机 H3 被别的工作占著时只用 Colab 拍：多帐号（`COLAB_HOMES`）共用伫列、失败重试一轮、做完关机；看到同名 VM 已开著就不碰（确定是自己的才设 `COLAB_REUSE=1`） |
| `dj_align.py` | DJ 口白逐字对齐，镜头切点与 DJ 字幕都用它；换口白档要重跑 |
| `resing_lines.py <A|B> <窗开始> <窗结束> <候选…>` | 局部重唱候选逐句听写比对（人声、混音各一次），量窗外时间差与多唱 |

换了歌要先跑 `audio` 再跑 `specs`、`cut`；漏跑的话 `make_battle.py` 会停下来提醒。

## 输出（`out/`）

`songtext/` 生歌用文字、`song/` 分轨＋对齐＋报告、`voice/` DJ 参考音与口白、`audio/` 全片音轨（`mix.wav`、`vocals.wav`、`dj.wav`、`timeline.json`）、`chars/`、`scenes/`、`first/`（首帧＋提示词＋接触表）、`h3/<镜>/`（spec、clip）、`post/`（放大、片段、字卡、特效事件）、`cut/`（成片、手机版、字幕档）、`review/`、`timing.json`。

## 验证纪录

2026-10-28～29，RTX 5090 32GB，用原频道〈微积分之战〉的两首 Suno 歌（牛顿 vs 莱布尼兹）＋本资料夹的 `battle.json`，从 `songs` 一路跑到 `srt`，首帧用本机 Qwen-Image-Edit 2511（`IMG=qwen`）。

**做出来的东西**：186.3 秒 1920×1080 成片＋27.2 MB 手机版＋srt，49 镜（43 镜 H3、其余字卡／静态），−16.0 LUFS、AAC 后真峰值 −2.1 dBTP。

| 阶段 | 时间 | 备注 |
|---|---|---|
| songs | 27 秒 | 分轨、对齐、逐句听写；最后一字的时间跟原片手工挑的差 0.05／0.26 秒 |
| dj | 数分钟 | 当时 BreezyVoice 每句 8 个候选；2026-10-29 改 Ming 后 191 秒，见下方「DJ 关卡」 |
| audio | 数秒 | A 停在 77.717 秒、B 从 79.179 秒、音乐到 174.784 秒，**跟原片手工剪的完全一致** |
| chars＋scenes | 约 2 分 | |
| frames（43 张） | 每张中位数 48 秒 → 约 35 分 | 实测 3.7 小时是因为同时有别的程式（Breeze TTS）占显存，最慢一张 1 小时 53 分。**跑 frames／h3 时不要同时跑别的 GPU 工作** |
| h3（43 镜，DMAD 4 步） | 49 分（平均约 69 秒／镜） | |
| cut | 约 11 分 | RTX VSR 放大＋特效逐格叠字（占大部分时间） |
| review | 44 秒 | |

**实测发现、已修进程式的：**

- 最后一字时间：Suno 会在最后一句后面加观众喊声，用「人声还有声音」判断会多算 14 秒 → 改成对齐的最后一字＋最多延长 0.3 秒。
- 首帧用 Qwen 时，擂台参考图要放**第一张**，不然双人镜会画在灰色摄影棚。
- 响度：加了观众声以后要再量一次 → 量 → 固定增益 → 限幅回圈到 −16 LUFS。观众音效里的拍手尖峰可达平均值的 13 倍，限幅器挡得住取样峰值，但压成 AAC 后真峰值冲到 +4.2 dBTP → 观众音效先软压到平均值的 4 倍，修后 −2.1 dBTP。
- 首帧「脸比角色多」自动警告（Qwen 会在单人镜多画一个人；这次抓到 N05、L08，另外 F01、F03 是剧情本来就有旁人）。

**本机 Qwen 首帧的已知限制（人工关卡 1 要看）：**

- 双人对峙镜（D01–D03）两人都面向镜头并肩站，画不出侧脸互瞪；要对峙感就在 `battle.json` 设 `"image_backend": "img25"`，或改成两个单人镜对切。
- 偶尔把首帧画成左右两格拼图（L06），H3 会照著演成分割画面 → 删掉重画。
- 场景里的字（书名、议会横幅）是乱码 → 首帧描述别要求写字，要字就后制字卡。
- 道具会在第一格出现、之后消失（N02 的三角帽）→ 首帧别放这镜用不到的配件。

**H3 自审**：`review` 的「构图漂走」清单 21 镜，大多是唱歌镜的手势与走位误报；真的有问题的是 T03（观众镜中途溶接到另一个舞台约 1 秒）和 L09（侧面转成正面），两个都在清单里。硬切（相邻格差 > 门槛）这次 0 镜。

**DJ 关卡**：DJ 口白当时用 BreezyVoice 念，「微积分」被听写成「我积分／为积分／危机分」，8 个候选都没过，`dj` 阶段照设计停下来，用 `ALLOW_REVIEW=1` 继续。**2026-10-29 起 DJ 改用 Ming-3.0-TTS**（原专案试听「声音非常的好，也没有大陆腔」，MIT 可商用）：同样 4 句、同一个参考音，每句 4 个候选，**4 句第一轮全部听写正确（含「微积分」）**，本机 191 秒。你自己的片遇到不合格的句子，先听那一句；真的念错就在 `dj.tts` 换同音字或换说法。

### 2026-10-29 Colab 全云端验证（基本版：YuE2＋Qwen＋Ming，全部在 Colab 跑）

G4（RTX PRO 6000 96GB，荷兰机房），用本资料夹的 `battle.json`（同一份歌词），**没有 Suno**：`yue` 在云端生两首歌，之后一路跑到 `srt`。为了省运算单元，首帧和 H3 只做 4 镜（`ONLY=W01 N01 L02 D01`），其余 45 镜用首帧静态图／镜号代替。

| 阶段 | 时间 | 备注 |
|---|---|---|
| `start`（完整安装） | 564 秒 | 新加的 YuE2（4 GB）、Ming（3 GB）下载各 13、8 秒，Ming 节点装在同一份 ComfyUI |
| yue（每人 10 首） | 524 秒 | 拍速对的：A 1／10 首、B 7／10 首；逐句听写 0.50／0.53（Suno 原曲约 0.63–0.80），有几句含糊 → 要多抽、人听 |
| songs | 57 秒 | 两首都对齐成功 |
| dj（Ming） | 114 秒 | 4 句第一轮全部听写正确 |
| chars＋scenes | 132 秒 | |
| frames（4 镜） | 317 秒 | 含载入 Qwen；之后每张约 48 秒 |
| h3（4 镜） | 429 秒 | 第一镜含载入模型 296 秒，之后每镜 42–46 秒 |
| cut | 132 秒 | lanczos 放大（45 镜是静态图，整场全 H3 约 10 分） |
| review | 32 秒 | |

成片 179.9 秒、−16.0 LUFS、手机版 26.6 MB。这次连修 bug 重跑共用了 13.8 个运算单元；**整场 49 镜估计约 1.5–2 小时、15–18 单元**（首帧约 35 分、H3 约 32 分）。

实测发现、已修进程式的：
- `colab_h3.py film` 遇到有 `battle.json` 的资料夹改跑 `make_battle.py`，而且用 Voice 环境（系统 Python 没有 opencc、stable-ts）。
- `film` 改成增量上传：`out/` 只传 VM 上没有或大小不同的档（`yue` 同步回来后整包 380 MB，上传被断线），`out/` 以外的设定、程式每次都传。
- Voice 环境补 `opencv-python-headless`（字卡避脸要用；原本本机是刚好被别的套件带进来）。
- 字卡避脸的脸侦测：没有 YuNet 模型就自动下载（约 230 KB，OpenCV 官方 opencv_zoo）；OpenCV 5 已经没有 Haar，原本的备案会直接当掉。
- 换歌之后镜头时间会跑掉（YuE2 的前奏比 Suno 短）：`frames` 会先列出顺序反掉的镜，照提示改 `at`。
