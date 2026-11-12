# 创作者三步极速出片实操教程 (Quickstart)

本教程带领您以创作者视角，用 **最少的操作步骤** 生成您的第一支 9:16 影视级竖屏短片。

---

## 步骤一：选定出场角色（或使用预设主角）

系统默认已预装并固化了标准示范角色资产：
* **角色 A：小芸 (`yun`)** —— 女高中生，马尾辫、校服、清纯活泼。已生成专属定妆卡与青年女声参考音。
* **角色 B：林老师 (`teacher`)** —— 青年男教师，眼镜、衬衫、儒雅严谨。已生成专属定妆卡与青年男声参考音。

> *💡 如果您希望使用自己的新角色，只需将您的角色正面肖像放入 `runtime/chars/<角色名>/portrait.png` 即可。*

---

## 步骤二：准备您的分镜文案

在本地新建一个分镜描述文件（例如 `runtime/shots/demo_story.json`，或直接编写一段剧本文本）：

```json
{
  "title": "林老师的点名",
  "shots": [
    {
      "id": "S01",
      "char": "yun",
      "line": "老师，我今天真的带作业了！",
      "action": "小芸坐在课桌前，神情紧张地高高举起右手，身体微微前倾，眼神闪烁，窗外夕阳在她发丝勾勒出金色轮廓，中景，固定机位。"
    },
    {
      "id": "S02",
      "char": "teacher",
      "line": "那你拿出来放在桌上，我看看写完没有。",
      "action": "林老师站在讲台旁，双手撑在教案前，眼神关切又带着一丝微笑，特写，镜头缓慢微推。"
    }
  ]
}
```

---

## 步骤三：一键合成与取片

### 运行方式 A（推荐）：在 Google Colab 上极速出片
1. 打开浏览器登录并上传 [colab_lopy_pipeline.ipynb](file:///home/debian/lopy_project/lopy-workflow-colab/colab_lopy_pipeline.ipynb)；
2. 选择 **L4 GPU** 运行时；
3. 点击全部执行，系统将在 3~5 分钟内完成全剧生图、配音与对嘴视频渲染；
4. 页面底部的播放器中直接点击播放成片，或在绑定的 Google Drive `lopy_outputs/` 中直接下载 MP4！

### 运行方式 B：在本地 T4 机器上执行全自动化构建
如果您在本地 Linux/T4 环境，直接在终端执行端到端自动化编排：
```bash
python3 pipeline/demo_local/run_demo.py
```
系统将自动执行：
1. `BreezyVoice` 本地极速配音与静音切除；
2. 首帧图像提取与角色面部一致性注入；
3. 生成动态视频并由 `FFmpeg` 压入字幕与混缩背景音轨；
4. 产物直接输出在 [runtime/outputs/](file:///home/debian/lopy_project/lopy-workflow-colab/runtime/outputs/)！
