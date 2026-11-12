# 来源标注

本技能的流程骨架（八阶段编剧流程、剧本格式规范、审阅清单结构）改写自：

**[POUND0423/AI-drama-pound](https://github.com/POUND0423/AI-drama-pound)** — `ai-short-drama-screenwriter`，MIT License，v0.1.0（2026-08-26）。

## 本专案的改动

| 项目 | 原版 | 本版 |
|:---|:---|:---|
| 平台 | OpenAI Codex（`~/.agents/skills/`） | Claude Code（专案内 `.claude/skills/`） |
| 画面比例 | 竖屏 9:16 | **预设 9:16 直式（Shorts），可指定 16:9** |
| 篇幅结构 | 8–12 集连续短剧 | **单支 1–3 分钟；系列作每集独立成篇** |
| 角色 | 每次从零设计 | **固定主角山狮霸**，引用专案 Character Bible |
| 技术限制 | 无 | **本机 MiniMax H3 可行性检查**（每镜 ≤12 秒、一镜最多 3 位说话者（各给参考音）、画面字由首帧画好） |
| 阶段数 | 8 | **9**（新增〈片段切分与素材备料〉） |
| 新增档案 | — | `references/segmentation.md`、`references/table-read.md`（生成前试映）、`references/drama-hooks.md`（抓马上位模式） |
| 新增流程 | — | 主题锚点、观众预期曲线、情绪流、因果链、人物五面向、阶段关卡、生成前试映（2026-10-12） |

原专案的 `agents/openai.yaml` 未沿用（Claude Code 不使用该格式）。

## 原作授权全文

见同资料夹 `LICENSE-AI-drama-pound.txt`（MIT，Copyright (c) 2026 POUND0423）。
