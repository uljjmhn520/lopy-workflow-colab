# 生歌、检查、接法

## 先问：有没有 Suno？

| 情况 | 用什么 | 备注 |
|:--|:--|:--|
| 有 Suno 帐号 | **Suno**（网页 Custom 模式，或 Kie.ai API） | 编曲最丰富、rap 最有攻击性、会自带刷碟声。四场对决都用它 |
| 没有 Suno | 先问使用者 → **YuE2 14 版**（`make_battle.py yue`，配方 `templates/song_yue2_v14/`） | ComfyUI 原生节点；比 Suno 平、攻击性弱；权重 CC BY-NC |
| YuE2 也不行 | ACE-Step 1.5 XL（`tools/ace_song.py`） | 拍速最稳、MIT；人声有金属声 |
| 本机没显卡 | Suno 最省事；没有 Suno 就在 Colab 跑 YuE2 | Colab 完整安装已预装 YuE2：`colab_h3.py film <对决资料夹> yue` |

不要自己从 Suno 换成 YuE2：换之前一定问。

## Suno

1. `make_battle.py songtext` → `out/songtext/suno_A_lyrics.txt`、`suno_A_style.txt`（B 同理）。
2. **网页**：Create → Custom，Lyrics 贴歌词、Styles 贴风格，每人各生一首（一次 2 版）。**API**：`python kie_suno.py submit A` → `poll a1`（环境变数 `KIE_API_KEY`；每次 2 版约 12 点）。
3. 每人先抽 2 版，不满意再改风格抽；挑好的放到 `song/A.mp3`、`song/B.mp3`。

### 风格写法（英文，≤ 1000 字元）

依序写：
1. 结构：`ONE CONTINUOUS RAP SONG by ONE rapper … EXACTLY 144 BPM`（有唱段就写 `rap verse, then a short 4-line SUNG melodic hook, then back to rap`）。
2. 曲风＋招牌乐器（每场不同）：英国巴洛克 boom-bap＋大键琴、德国巴洛克 trap＋管风琴、G-funk＋里拉琴、爵士 boom-bap＋古琴洞箫、铜管进行曲 hard trap……
3. 前奏与收尾：A＝4 小节乐器前奏、`the beat STOPS DEAD on one huge hit (hard stop, no outro)`；B＝4 小节 DJ 刷碟前奏、`the LAST EIGHT LINES build gradually …（见第 6 点）… crowd roars 'OHHH' … rides out 4 bars with scratches`。
4. 声音：`ONE SOLO MALE RAPPER only: a DEEP, RASPY baritone …` vs `a BRIGHT, SHARP young TENOR …`——**两人一定要一低一高、个性不同**。
5. 咬字：`crystal-clear Mandarin rap with Taiwanese diction, every number clear`。
6. 杀招段：`The LAST EIGHT LINES build GRADUALLY at the same BPM, never faster: first two lines stripped back with no drums, a quiet restrained voice; then drums return; every two lines add one layer and the voice gets louder and higher; one beat of silence before the final line, which is the loudest moment of the song`（使用者 2026-11-01 要情绪慢慢堆）。**实测（〈瑜亮之战〉16 版）：Suno 不太听话**：长描述标签几乎没用；短标签 `[Breakdown: no drums, ...]`、`[Build-up: ...]`、`[Drop: shouted]` 约四分之一的版本会在杀句前真的空一拍，但人声响度仍很平。做法：多抽，量伴奏有没有收、杀句前有没有空拍，挑有的版本给人听；也可以用分轨做一版音量与滤波的后制当对照（这场使用者选 Suno 原版，没选后制）。
7. negative：`slow ballad, mumble rap, autotune-heavy, female voice, choir, second rapper, duet, featuring, melisma, vocal runs, Indian scale`。

Suno 不吃艺人名字，要写成特征。范例见 `pipeline/template_battle/battle.json` 的 `suno_style`。

### 两人声音太像

- 两人的声音描述拉开（低沉沙哑 vs 明亮尖锐），两首都生完用声纹比对（CAM++，越低越像两个人；0.7 左右可以接受）。
- 还是太像：Suno 的 persona（用某一版的声音当角色）锁住其中一人的声音再生。

### 人声每场都要换（使用者 2026-11-02）

前面每一场都写「低沉 baritone vs 明亮 tenor」，听起来都是同几个人。使用者：「不要老是用类的几个人声。」
- **开工先列前几场写过的声音**，这场换不同类型：烟嗓气音、尖鼻音嘲讽、懒散拖拍、老派、戏剧腔……同时换曲风，Suno 的声音会跟著曲风走。
- **一个角色试 2–3 种声音描述**，不要只抽同一段风格；negative 写上不要的类型（`deep baritone, bright tenor`）。
- **选版前跑 `voice_diff.py`**（比对前面所有场次的人声分轨，列最像的 3 个和音高），分数只是辅助，最后要人听。

## YuE2（没有 Suno 时）

一条指令（配方照 `templates/song_yue2_v14/README.md`）：
```
make_battle.py yue                           # songtext → 每人 YuE2 抽 YUE_SEEDS 首（预设 10）→ 只留目标 BPM、逐句听写排序 → 第一名放 song/
python cloud/colab_h3.py film pipeline/my_battle yue   # 没有显卡：同一件事在 Colab 跑，out/ 同步回来
```
- 目标 BPM 读 `yue_style` 里的「144 BPM」（或填 `rappers.<A|B>.yue_bpm`）；约一半会跑掉，全掉就多抽（`YUE_SEEDS=11,12,…,20`）。
- 第一名只是听写初筛，**人听过 `out/yue/<A|B>/` 的候选再定**；换歌就把那首转档覆盖 `song/A.mp3`，再跑 `songs`。
- YuE2 没有器乐前奏、刷碟不一定有：A 停在拍上→B 的接法照样能用，但前奏很短时 DJ 口白会把音乐往后推（范本自动处理）。

## 检查（`make_battle.py songs` 自动做）

- BS-RoFormer 分人声 → 歌词强制对齐 → **逐句**听写、BPM、最后一个字唱完的时间。
- **不要整首直接听写**：rap 会让听写幻觉出「中文字幕志愿者」之类的字，连好的歌都量成 0。
- rap 的逐句听写天生偏低：人工确认全对的 Suno 歌也只有 0.63–0.80。看低分句（< 0.5）是唱错还是只是听写不准，**最后一定要人听**。
- 对齐出来的段数跟歌词句数不同＝歌词跟送去生歌的不一样，先修。
- 最后一个字的时间不对（Suno 自己在后面加喊声）→ `rappers.<A|B>.last_word_end` 填秒数。
- **冷僻专有名词（尧舜这类）Suno 每版都唱歪**（2026-11-01〈人性之辩〉：10 版全唱成「老钻／药犯／老残」）→ 写歌词时就先查听写，或改常用字同音（字幕再换回）。歌已定稿才发现：**Kie `replace-section` 局部重唱**（最短 10 秒、每次 2 版，同音字当歌词，例「姚 顺」）→ 分人声、逐句听写挑最清楚的 → **只把那几个字的人声剪回定稿**（定稿混音＋〔新人声－旧人声〕，两端 25 ms 交叉淡化、对齐候选与定稿的时间差），伴奏和其他句不动、时间轴不变，只重拍唱那句的对嘴镜。重唱窗外的部分 Suno 会整段重生（窗后完全不同），不能整首换。范例 `短片/人性之辩_孟子vs荀子_20261101/battle/suno_replace.py`、`resing_eval.py`、`splice_resing.py`。

- **杀招段太平也可以用 `replace-section` 救**（2026-11-03〈向日葵之战〉）：`SUNO_PART` 给段落标签（`[Breakdown: no drums…]`、`[Build-up…]`、`[Drop…]`）、`SUNO_PROMPT` 讲清楚先收再堆，抽 4 版量伴奏走势。实测：Suno 会从窗前 6–10 秒开始重生（窗 74 秒，68 秒就不一样），歌会变长，句子可能唱慢一倍，窗后会接著乱唱；原版窗前的句子要留，就在两句之间的拍点接回（两版只差 0.017 秒，先算样本偏移，40 毫秒交叉淡化），杀句唱完后由范本硬停。`voice_diff.py` 只取前 40 秒，比不出重唱段，不能拿来判断重唱的声音。
- **整首对齐可能把几句压成 0.1 秒**（前奏长、某段含糊时；〈瑜亮之战〉孔明 1–4、21–24 句）：看 `align_*.json` 每句长度，太短的只取那段人声重新对齐，同时更新 `words`，字幕韵脚才对得上。
- **Suno 常自己把副歌多唱一遍**（2026-11-02〈瑜亮之战〉周瑜：歌词只写一遍，实际唱两遍；v1 把第二遍当器乐段，放观众镜、没字幕，使用者一看就抓到）→ `songs` 阶段会印「⚠ 人声还在唱，但歌词没对到」；照实把那几句补进歌词（后面句子的编号要跟著移）和字幕，并拍唱的人本人。**说「器乐段」前先看人声分轨，不要凭对齐结果判断**。
- **Suno 也会在开口前自加「喔耶」长音**：对齐把它算进第一句，字幕会早出现。要嘛剪掉（人声分轨归零），要嘛对齐列加 `show_start`（字幕从真正开口的字开始）。
- **Suno 会多唱字，对齐不会告诉你**（2026-11-02〈瑜亮之战〉孔明「那把火**车**」「站在船上**想**看戏」，使用者抓到）：对齐只对我给的字，多唱的字会被吃进那句。`align_*.json` 的 `ok` 低于 0.3 的句子一定要查，不能当成气音段听写不准；**逐句切窗（前后多 0.3 秒）听写混音、比字数**，整首连续听写在前奏和分轨上会幻听。局部重唱也一样会多唱：候选除了字对，**句与句的空档也要单独切窗听写、看频谱**（〈瑜亮之战〉有一版字全对，但空档多唱「欸欸、哇哇哇」）。候选唱得比原版快时，**不要把人声搬开留空**（〈瑜亮之战〉v3、v4 使用者：声音不见了、异常）：人声连音乐整段用候选的，它提早几小节进下一句，就接回原版同一句、全曲少那几小节，重拍受影响的对嘴镜。
- **人声分轨里可能混著音乐，伴奏分轨也可能有破洞**（2026-11-02〈瑜亮之战〉使用者抓到两处）：①气音段、没鼓段的音乐底常被分到人声轨，清人声会一起清掉，停顿变成无声（1:16「声音不见了」）；所以不要只清人声，要换就人声连音乐整段换；自己铺的低音底手机喇叭放不出来（〈瑜亮之战〉v4 量起来有 −27 dB，使用者还是听不到）。②Suno 在前奏自加喊话时，分人声会连音乐挖掉，而前奏用的是伴奏分轨，留下破洞（1:56、0:08）；用前一小节同拍位补。**每版都扫全片音量，要先滤掉 300 Hz 以下（手机喇叭放不出来）再量，单声道：50 毫秒低于 −42 dB 持续 0.1 秒以上、或相邻半秒掉 8 dB 以上的地方，逐一确认。不要为了特效压音乐（使用者：音乐突然变小声）。**
- 局部重唱**要在最终混音上听写**：分轨上听写对，混音里可能还是错（〈瑜亮之战〉「传」分轨是「赚」、混音是「穿」，换同音字「篆」再抽才过）。单字剪不干净就换整句，换到有对嘴的句子要重拍那一镜。
- **副歌不好听，只换副歌**：`replace-section` 窗对齐小节线、每次 2 版，只把窗内接回定稿（前后 30 ms 交叉淡化）。Suno 可能把原本唱两遍的副歌改成慢慢唱一遍；若把下一段也唱进窗内就淘汰。

- **局部重唱的三个坑（2026-11-04〈Bravo 之战〉，20 多版的结果）**：①窗内放 `[Breakdown…]`、`[Melodic Hook…]` 这类标签，Suno 会唱慢、句子往后掉（5 句掉 2 秒）→ 整窗只用 `[Verse]`，`SUNO_PROMPT` 写「每句刚好两小节、不要放慢」，同一窗多抽就回到原本时间；②窗从副歌接主歌的地方开始，Suno 常整窗不开口 → 标签改 `[Rap Verse: vocals start immediately on the first beat, no pause]`；③同一个字抽 4 版都唱成别的（「到处讲」→「出家」），换同音字没用，改一个押同韵的词（「到处张扬」）。挑版看 `resing_lines.py`（逐句＋窗前后时间差），接回用 `splice_songs.py`（整段连音乐换），接前逐段量低频包络差（10 ms 内才算对）。

## 两首怎么接（`make_battle.py audio` 自动做）

1. A 整首：前奏改用伴奏分轨（拿掉 Suno 前奏里含糊的喊话，免得跟 DJ 开场口白打架）。
2. A 最后一个字唱完后的**第一拍重拍收**：留 0.25 秒原音＋0.6 秒短衰减，**不淡出**。
3. **正好 1 小节后** B 那首的第一拍进来（B 自带 DJ 刷碟前奏，换场口白压在上面）。
4. B 最后一个字后换伴奏分轨（Suno 常自己再唱），走到「最后一句的小节线＋8 小节」，最后 2 小节淡出。
5. DJ：开场口白在 1 秒开始（塞不下就整段音乐往后延）、换场口白在 B 开口前 1.2 秒讲完、定论口白在 B 唱完 3.2 秒后、片尾口白在音乐结束后；口白期间音乐压 −5 dB。
6. 两人饶舌段调成一样大声；两首 BPM 不同时 A→B 会接不准，尽量同 BPM（前四场三场 144、一场 94）。

Suno 的 extend 生的「自然尾奏」接起来不好，不要用；需要收尾就写进 B 歌词的 `[Outro]`。
