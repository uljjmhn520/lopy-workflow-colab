# 角色 LoRA 训练（选用，品质最好的首帧做法）

不训练也能做片（用 Qwen-Image-Edit 附参考图，见 `docs/07_本地角色与首帧.md`）。想让角色更像、细节更好时再训练。

## 1. 安装 AI Toolkit（一次）

```
git clone https://github.com/ostris/ai-toolkit C:\AI\lora\ai-toolkit
cd C:\AI\lora\ai-toolkit && git checkout 60d0c28
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
原专案用的是 commit `60d0c28`、torch 2.13.0+cu130。训练时会从 Hugging Face 下载 `Comfy-Org/Qwen-Image-2.1`（设定档 `name_or_path`），第一次要等下载。

## 2. 产生训练图

```
C:\AI\H3\venv\Scripts\python.exe C:\AI\tools\make_lora_dataset.py --ref chars\yun.png --trigger yun_local --desc "the girl Xiaoyun, a bright 11-year-old Taiwanese schoolgirl with a short black bob haircut and straight bangs, round friendly face, wearing a plain white short-sleeve school shirt" --out C:\AI\lora\datasets\yun_local
```
- 会产生 25 张（定妆照本身＋24 种景别／角度／表情／场景）和同名 caption。
- **一定要逐张看**：删掉脸不像、多手多脚、有字、穿错衣服的图。

## 3. 训练

1. 复制 `qwen21_character_lora_template.yaml`，把 `__NAME__`、`__OUTPUT_DIR__`、`__DATASET_DIR__`、`__TRIGGER__`、`__DESC__` 换掉。
2. ComfyUI 先关掉（训练要用整张显卡）。
3. `C:\AI\lora\ai-toolkit\.venv\Scripts\python.exe C:\AI\lora\ai-toolkit\run.py <你的设定档>.yaml`
4. 每 400 步存一次，`samples/` 有样图。用 1600 步那颗；样图已经很像也可以提早用 1200 步。

设定重点（原专案实际用的）：768 解析度、rank／alpha 32、学习率 1e-4、adamw8bit、梯度检查点、底模量化 convrot8、`low_vram: true`、1600 步。

| 硬体 | 实测时间 | 来源 |
|---|---|---|
| RTX 4080 Laptop 12GB＋32GB RAM | 约 3 小时（1600 步） | 原专案第二台电脑实机训练三个角色 |
| RTX 5090 模拟「16GB 显卡＋32GB 记忆体、平常程式照开」 | **33 分钟**（每步 1.13 秒）、显存峰值 14.7GB、**记忆体最低只剩 0.5GB** | 2026-10-07 本 repo 验证 |

## 4. 使用

把 `.safetensors` 复制到 `C:\AI\H3\ComfyUI-0.36.0\models\loras\`，生首帧：
```
C:\AI\H3\venv\Scripts\python.exe C:\AI\tools\gen_image.py --lora yun_local.safetensors:1.0 --prompt "yun_local, the girl Xiaoyun, <外观照抄> <电影感句> <这一镜>"
```
- 提示词一定要有触发词＋外观描述（只有触发词不保证像）。
- 单人 1.0；多人同框不要同时挂两个 LoRA（会互相稀释），改成先出构图、再用 `qwen21_face_refine.py` 对每个人的框各挂自己的 LoRA 重绘。
- LoRA 的训练图若是灰底棚拍，生出的画面光线会稍平；提示词的光线句要写足。

## 本 repo 验证

2026-10-07，用 `pipeline/demo_local` 的角色「小芸」（本机 Qwen-Image 2.1 生的单张定妆照）：
- `make_lora_dataset.py` 产生 25 张，花 18.6 分钟；目视删掉 2 张（黑板上有字、脸看起来太成熟），剩 23 张。
- 在模拟的 16GB 显卡＋32GB 记忆体下训练 1600 步：33 分钟、显存 14.7GB、记忆体最低剩 0.5GB（**能跑完但非常极限：32GB 电脑训练时务必关掉所有其他程式**）。
- 真实 16GB 卡算力较低，推估约 1–1.5 小时；原专案 12GB 笔电实测约 3 小时。
- 首帧效果（同 3 个场景、同 seed）：
  - 不附参考、不挂 LoRA：每张都是不同的女生 → 不能用。
  - Qwen-Image-Edit 附定妆照：三张都像。
  - 本地训练的 LoRA：三张都像，2K、细节最好、构图变化较多。
  → 两条路都可用；想要最好画质、或同一角色要拍很多镜，就训练 LoRA。

### 产生训练图时学到的
- 外观描述要连下半身一起写（例：navy pleated skirt）。没写的话，Qwen-Image-Edit 会在全身照里随机配裙子、长裤、短裤，LoRA 会学到不一致的下半身。
- 一定要逐张看：这次 25 张里有 1 张黑板写了字、1 张脸变成熟。
