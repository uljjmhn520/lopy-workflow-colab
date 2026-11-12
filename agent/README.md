# agent：让 AI agent 接手制作

| 档案 | 用途 |
|---|---|
| `CLAUDE.md范本.md` | 专案入口范本，改名 `CLAUDE.md` 放专案根目录 |
| `skills/shanshiba-drama/` | 编剧技能（2026-10-23 更新）：九阶段＋阶段关卡、主题锚点、预设 9:16 剧本与镜表格式、**生成前试映**（16 宫格分镜草图＋读本，`tools/make_storyboard.py`、`tools/assemble_read.py`）、抓马上位模式、审稿清单（改写自 AI-drama-pound，MIT，见 NOTICE.md） |
| `skills/blender-previs/` | Blender 预演技能：需求访谈、镜位契约、布置图规则、提示词包、检查清单 |
| `skills/rap-battle/` | 饶舌对决技能（2026-10-28）：选题与对决设计、歌词规则（押法混用、唱段像流行副歌、杀句、两边一起改、读音）、生歌（**先问有没有 Suno**，没有才用 YuE2 14 版）、镜表规格、逐秒自审表；成片交给 `pipeline/template_battle/` |

技能放到专案的 `.claude/skills/` 底下，Claude Code 会自动载入。

> ⚠️ `shanshiba-drama` 已在 2026-10-23 更新到原频道现行版；`blender-previs` 写于专案早期（2026-08～09），references 里还有几处旧说法，用的时候以 `docs/` 为准：
> - 「Seedance 2.5、每段 30 秒」→ 本机 H3、单镜 ≤12 秒、对话靠切镜
> - 「山狮霸」「角色资产/山狮霸/角色设定.md」→ 原频道的例子，请换成你自己的角色设定档
> - 「voice-clone 技能」→ BreezyVoice（`make_breezyvoice.cmd`）
> - 首帧 → 本 repo 预设 Qwen-Image-Edit 2511 附定妆照（原频道用云端 Image 2.5）；定稿用 DMAD 4 步
> - 「14 步＋EasyCache」→ 定稿不开 EasyCache

协作方法（知识库分层、记忆、工作习惯）见 [docs/05_agent协作与知识库.md](../docs/05_agent协作与知识库.md)。
