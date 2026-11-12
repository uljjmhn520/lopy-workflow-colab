# 唱词歌范本：YuE2「14 版」（本机唱词歌的主要范本）

> **歌曲（有人声）生成顺序（2026-10-27 实测后定案）**
> 1. **Suno**（例如经 Kie.ai 的 API）：有帐号就用它。编曲最丰富、rap 最有攻击性，还会有刷碟声。
> 2. **YuE2 14 版（本范本）**：没有 Suno 帐号时，**先问使用者**要不要改用本机 YuE2，不要自己换。要变体就从 14 版改。
> 3. **ACE-Step 1.5 XL**（`tools/ace_song.py`）：Plan C。拍速最稳，歌可以用，但人声带金属声。
>
> 纯配乐（不唱词）仍用 MiniMax Music 3（`tools/gen_music3.py`）。

这个配方是在 RTX 5090、ComfyUI 0.40 上，用一首中文饶舌对决（牛顿 vs 莱布尼兹）试了 13 种以上做法后，制作人听过选出来的。
同一场试做也记下了失败的做法：
- 自己写 ABC 谱：拍速锁得住，但编曲太平。
- 翻唱参考歌：拍速对，但跟原歌还有一段差距。
- full／off 规划模式：拍速乱跳。
- 段落之间留空档，想让 DJ 刷碟：反而比较差。

## 配方
| 项目 | 设定 |
|:--|:--|
| 模型 | ComfyUI 原生 YuE2，`yue2_3b_int8_convrot.safetensors`（`setup/downloads_yue2.json`）；bf16 没有明显较好 |
| 规划模式 | **melody**：YuE2 只规划人声旋律，伴奏自由发挥 |
| 风格 | 英文逗号标签，**语言放第一个**（越前面影响越大），依序写：Chinese → rap → boom bap battle rap → **DJ scratching, vinyl record scratches, turntablism** → aggressive rapid-fire rap flow, staccato punchy delivery → 声音 → 鼓与 808 → 一个招牌取样乐器 → 气氛 → BPM。范例 `style_A_deep_raspy.txt`、`style_B_bright_sharp.txt` |
| 歌词 | 每段 4 句、段落标签大写、段落之间空一行：`[Verse]`×2 → `[Pre-Chorus]`（2 句）→ `[Chorus]`（最狠的句子）；有反转再接 `[Bridge]` → `[Chorus]`。不要放空的 `[Intro]`／`[Interlude]`。范例 `lyrics_example_*.txt` |
| 抽数 | **每首抽 10–12 个 seed**。约一半会掉到 89 BPM 或跳到 152，只留 143.6 的，再用逐句听写挑 |

## 指令
```
python tools/yue_song.py <名称> <角色> --style templates/song_yue2_v14/style_A_deep_raspy.txt --lyrics 我的歌词.txt --out work/song_A
<Voice venv>/python tools/pick_song.py work/song_A 我的歌词.txt
```
- 先开 ComfyUI（`tools/start_comfy.cmd`）。在 5090 上每首约 12–30 秒，12 首约 5 分钟。
- `pick_song.py` 会跳过拍速不对的歌，其余依逐句听写排序，写进 `pick.json`。
- **不要整首直接听写**：rap 会让听写幻觉出「中文字幕志愿者」之类的字。
- rap 的听写分数天生偏低，人工确认全对的 Suno 歌也只量到 0.63–0.70。**最后一定要人听。**

## 做变体时改哪里
- **换曲风**：只换取样乐器、鼓型（boom bap／trap／drill）和气氛词。Chinese、rap、DJ scratching、连珠炮 flow 要留在前段。
- **换声音**：只改「male rapper, … voice」那一组。两人对决时，每人用不同声音描述，**各生一首**。同一首歌里要求两种声音，出来会是同一个人。
- **换速度**：改风格最后的 BPM，`pick_song.py` 加 `--bpm`，填 librosa 实际量到的值。
- **做不到的**：刷碟声不一定每首都有，因为 ABC 谱写不进去，需要的话后制补。攻击性和韵律感仍比 Suno 弱。

## 授权
YuE2 权重是 CC BY-NC 4.0，不能商用。要营利就改用 Suno（看你的方案条款）或 ACE-Step（MIT）。
