# 专题五：短剧全链路执行逻辑与云端生命周期规划 (Pipeline & Session Lifecycle)

本文档定义了 LoPy 影视级短剧在 **本地 Tesla T4 与云端 Google Colab** 混合算力环境下的端到端执行流、双模式生命周期控制策略、GPU 智能分级调度，以及首帧拼图画廊核验标准。

---

## 一、 核心硬件与任务分工矩阵 (Hardware & Stage Division)

基于 Tesla T4 (16GB, sm_75) 与 Colab L4/G4 的实测物理特性，管线实行严格的硬件职责切分：

```
本地 Tesla T4 (16GB, 零成本高敏测试台)          Google Colab (按需弹性高性能引擎)
┌──────────────────────────────────────┐        ┌──────────────────────────────────────┐
│ Stage 0: 剧本台词编排与语法注音排雷  │        │ Stage 2: 锁衣控姿首帧生成            │
│ Stage 1: BreezyVoice-300M 批量配音   │──TTS─> │  • 统一定向调度: L4 GPU (24GB)       │
│          + Whisper ASR 评分 (>=0.95) │        │  • 货源充足稳定，单图仅需 30 秒      │
│ Stage 4: FFmpeg 自动拼接剪辑         │<─MP4── ├──────────────────────────────────────┤
│          + 双层中文字幕 + 音效混音   │        │ Stage 3: MiniMax H3 视频动态口型渲染 │
│          (全片仅需 5 秒，零算力开销) │        │  • 优先调度: G4 GPU (RTX 6000 96GB)  │
└──────────────────────────────────────┘        │    (单镜 42s 极速，总成本降低 60%)   │
                                                │  • 遇抢占受限自动平滑回退: L4 GPU    │
                                                └──────────────────────────────────────┘
```

### 分工红线：
1. **配音与剪辑（Stage 1 & Stage 4）死守本地**：BreezyVoice 与 Whisper 在本地 T4 显存占用仅 2.1GB，整剧 4 句对白合成仅需 14 秒；FFmpeg 剪辑混流仅需 5 秒，完全不需要占用昂贵的云端 GPU。
2. **生图与视频（Stage 2 & Stage 3）必须上云**：MiniMax H3 依赖原生 FP8 Tensor Core 与 24GB+ 大显存，在云端 L4/G4 上几分钟即可搞定，避免本地 T4 长达 87 分钟的漫长等待。

---

## 二、 首帧审核与云端生命周期控制 (双模式架构)

为了彻底解决“人工审核期间 Colab 是否关机”的矛盾，系统提供可通过环境变量 `PIPELINE_SESSION_MODE` 或命令行 `--mode` 切换的两种执行模式：

### 模式 A：两阶段彻底解耦模式 (`two_stage`，推荐默认)
* **设计哲学**：**零闲置、零倒计时压力、离线从容审核**。
* **执行流程**：
  1. **阶段 1（首帧云端批量生产）**：
     - 本地启动 Colab L4 实例；
     - 自动拉取 H3 图像权重，批量生成全剧所有分镜首帧（约 2 分钟）；
     - 自动调用 `tools/make_gallery.py` 将所有首帧拼接为一张 **2×2（或 4 格）总览画廊**；
     - 将所有图片与画廊拉回本地 `runtime/first/`；
     - **素材落盘即刻执行 `colab stop` 彻底注销云端 VM，算力计费归零**。
  2. **离线人眼核验 (Human Review Gate)**：
     - 创作者在本地终端、聊天窗口或看图软件查看画廊，耗时 2~5 秒核对衣服与面部神态；
     - 创作者没有时间限制，去吃饭、开会或次日再看均可，完全不用担心后台跑冒滴漏。
  3. **阶段 2（批量视频无人值守发单）**：
     - 创作者回复「`通过`」（或「`重抽 S02`」修改首帧后通过）；
     - 调度器自动拉起 Stage 3 云端实例（优先 G4，回退 L4）；
     - 14 步批量渲染全剧视频，全部 `.mp4` 回传本地后再次自动注销 VM。

---

### 模式 B：单会话连续交互模式 (`single_session`，带 5 分钟超时保底)
* **设计哲学**：**在线连贯作业、免除二次拉取模型时间、安全超时守卫**。
* **执行流程**：
  1. 创作者正坐在电脑前工作，启动管线单会话执行；
  2. 首帧在云端 L4 生成后回传本地，并在界面弹出拼图画廊，**后台启动 5 分钟保底计时器**；
  3. **快速确认通路**：
     - 若创作者在 5 分钟内敲击回车或回复「`通过`」，**当前实例不关机**，直接复用已挂载入显存的 14.6GB 文本编码器与 VAE，无缝切入 Stage 3 视频渲染（节省二次开机拉取模型的 3 分钟）；
  4. **超时安全保底**：
     - 若创作者临时离开走开超过 5 分钟未作回应，**安全守卫立即自动触发 `colab stop` 销毁实例**；
     - 首帧与画廊已安全保存在本地，创作者随时回来回复「`通过`」，依然能无缝唤醒进入 Stage 3。

---

## 三、 云端 GPU 智能分级调度 (GPU Tiering Strategy)

| 阶段 | 优先 GPU | 回退备选 GPU | 选型依据与优势 |
| :--- | :--- | :--- | :--- |
| **Stage 2: 首帧生图** | **L4 (24GB Ada)** | 无（L4 货源最充足） | 首帧仅需 6 steps，单图 32~36 秒，L4 单价低平稳，性价比极高。 |
| **Stage 3: 视频渲染** | **G4 (RTX 6000 96GB)** | **L4 (24GB Ada)** | **G4 极速降本秘籍**：单镜 14 步仅需 **42 秒**（L4 需 9~12 分钟）。虽单价略高，但耗时缩短 90%，单片综合扣费降低 60% 以上！若 G4 缺货则平滑降级 L4。 |

---

## 四、 首帧人机交互与指令设计

首帧生成并拉回本地后，系统直接在交互界面呈交 **2×2 拼图画廊**，创作者只需输入简短指令：

```
┌─────────────────────────────────────────────────────────────────┐
│                     首帧审查交互指令                            │
├────────────────────────────────┬────────────────────────────────┤
│ 用户指令                       │ 触发动作                       │
├────────────────────────────────┼────────────────────────────────┤
│ 通过 或 y                      │ 4 镜首帧全部核准，启动视频渲染 │
│ 重抽 S02                       │ 仅重跑分镜 S02 (换 seed)       │
│ 重抽 S02 --prompt "调整为微笑" │ 仅微调分镜 S02 Prompt 并重生成 │
└────────────────────────────────┴────────────────────────────────┘
```

---

## 五、 状态机流转图 (Workflow State Machine)

```mermaid
stateDiagram-v2
    [*] --> Stage0_Script: 本地 T4 剧本打磨与注音排雷
    Stage0_Script --> Stage1_Voice: BreezyVoice 批量合成
    Stage1_Voice --> Voice_ASR_Check: Faster-Whisper 反向打分
    
    state Voice_ASR_Check {
        [*] --> ScoreEval
        ScoreEval --> Pass_Silent: 评分 >= 0.95 (静默入库)
        ScoreEval --> Alert_Human: 评分 < 0.90 (弹窗报警修正)
    }

    Pass_Silent --> Stage2_Keyframes: 唤醒 Colab L4 生成首帧
    Alert_Human --> Stage2_Keyframes: 修正后放行

    Stage2_Keyframes --> Make_Gallery: tools/make_gallery.py 合成 2x2 画廊
    Make_Gallery --> Mode_Branch{"PIPELINE_SESSION_MODE ?"}

    Mode_Branch --> TwoStage_Flow: two_stage (默认解耦)
    Mode_Branch --> SingleSession_Flow: single_session (连续交互)

    state TwoStage_Flow {
        ColabStop1: 即刻 colab stop 释放 VM
        HumanReview1: 创作者离线看图
        ColabStop1 --> HumanReview1
    }

    state SingleSession_Flow {
        TimerWait: 启动 5 分钟超时保底计时器
        TimerWait --> QuickPass: 5分钟内用户确认「通过」
        TimerWait --> TimeoutStop: 超时未操作自动 colab stop
    }

    TwoStage_Flow --> Stage3_Videos: 用户确认「通过」
    QuickPass --> Stage3_Videos: 直接在当前实例渲染
    TimeoutStop --> Stage3_Videos: 用户归来确认「通过」后重新拉起

    Stage3_Videos --> Stage4_Assembly: 视频落盘 + 自动 colab stop 关机
    Stage4_Assembly --> [*]: 本地 FFmpeg 剪辑混流出片
```
