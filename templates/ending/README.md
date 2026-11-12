# 《山狮霸的多重宇宙》片尾范本（2026-09-30 定稿，可重复使用）

频道品牌：**山狮霸的多重宇宙**。每支短片片尾固定用这个结构（使用者指示「之后会重复使用」）：

1. **特写照片＋AI 工具名单**：N 张片中特写（缓推、下缘压暗、淡入淡出），每张左下 2 行「工具・用途」，**每张停留 3.3 秒**（1.9 秒太短，使用者要求加长）。第一张上方小标「本片使用的 AI 工具」。
2. **大标题「山狮霸的多重宇宙」**：金色咒印法阵（`assets/seal_gold.png`，Image 2.5 生成的黑底光图）慢转，标楷体 176pt 逐字由光浮现、爆光定格，约 7.5 秒；配乐在这里收尾。
3. **声音**：配乐贯穿片尾（没有人声也要有音乐）；最后约 3.5 秒音乐淡出、画面约 2.4 秒渐黑；标题爆光处叠一下低频不重的 boom＋钟声（主片后制叠）。

## 用法
```
C:\AI\H3\venv\Scripts\python.exe render_ending.py config.json
```
`config_example.json` 是 4 张特写＋工具名单的范例（约 21 秒）；30 秒左右的短片用 `config_short_example.json`（2 张、约 9 秒）。`title` 改成你的片名或频道名（原频道用「山狮霸的多重宇宙」）。**每张卡最多 3 行工具**，超过程式会停下来提醒。MiniMax Music3 的授权要求商业使用时显著标示「MiniMax-Music3」，公开内容要标示 AI 生成，所以最后一张建议保留「本片画面、配音与配乐皆由 AI 生成」。把特写静帧放进 `frames/`、依本片实际工具修改 tools。输出 1920×1080、24fps、无音讯。

## 名单规则
- 只列实际用到的工具；使用者指示**不列非商用授权工具**（例如 Breeze TTS 2、YuE2）——但授权义务不会因不列名消失，商用前要另外处理。
- **MiniMax Music 3** 官方 Community License 要求显著标示「MiniMax-Music3」并揭露机器生成 → 有用到就要列，并在最后一张加「本片画面、配音与配乐皆由 AI 生成」。
- 常用名单：MiniMax H3、OpenAI Image 2.5、VoxCPM2、MiniMax Music 3、faster-whisper、BS-RoFormer、NVIDIA RTX VSR、ComfyUI、Claude Code。

## 素材
- `assets/seal_gold.png`：Image 2.5 生成的金色法阵（黑底光图）。其他三色法阵在 `templates/seals/`。
- 实际效果请看频道任一支片的片尾。
