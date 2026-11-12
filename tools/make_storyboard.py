"""生成前试映（一）：16 宫格分镜草图。读 preview/shots.json，每 16 镜画一张 4×4 直式草图（OpenAI Image 2.5，tools/img25.py），
多张同时生成；镜号用 PIL 叠在每格左上角（不叫模型写字，模型会写错）。只看故事顺序与构图，不附角色参考图、不验角色像不像。
2026-10-23 由原频道各片的 preview/make_storyboard.py 改成通用版（〈台风假作业包〉27 镜 2 张约 3 分钟）。

shots.json（跟 assemble_read.py 共用；说明见 agent/skills/shanshiba-drama/references/table-read.md）：
  {"cast": "Characters (keep consistent across panels): ...",            # 角色外观一句话（英文），每张草图都带
   "shots": [{"id": "S01", "sec": 3, "panel": "extreme close-up: ...", "lines": [...]}, ...],
   "end_card": "频道名"}                                                   # 有的话最后补一格空白片尾卡
用法：python tools/make_storyboard.py <片资料夹>/preview/shots.json [--landscape]
  → 同资料夹 storyboard_<k>.png（原图）＋ storyboard_<k>_label.png（叠镜号）；--landscape＝16:9 格子"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import img25  # noqa: E402
from fonts import font  # noqa: E402

PER_SHEET = 16


def panels(spec):
    p = [(s["id"], s["panel"]) for s in spec["shots"]]
    if spec.get("end_card"):
        p.append(("END", "a plain dark panel, empty, for an end title card"))
    return [p[i:i + PER_SHEET] for i in range(0, len(p), PER_SHEET)]


def prompt(cast, ps, rows, landscape):
    shape = "horizontal 16:9" if landscape else "vertical 9:16"
    lines = "\n".join(f"Panel {i + 1} (row {i // 4 + 1}, column {i % 4 + 1}): {d}" for i, (_, d) in enumerate(ps))
    return (f"A film storyboard sheet: exactly 4 columns and {rows} rows of equal-sized {shape} panels, separated by thin white gutters, "
            "read left to right, top to bottom. Rough pencil sketch with light watercolor tint, simple and clear staging, cinematic "
            "framing, exaggerated comedic acting. Absolutely NO text, letters, numbers, logos or captions anywhere in the image. "
            f"{cast}\n{lines}")


def make(out_dir, k, cast, ps, landscape):
    rows = (len(ps) + 3) // 4
    stem = out_dir / f"storyboard_{k}"
    files = img25.generate(prompt(cast, ps, rows, landscape), str(stem), n=1, size="1536x1024" if landscape else "1024x1536")
    src = Path(files[0]) if files else stem.with_suffix(".png")
    if src != stem.with_suffix(".png"):
        Image.open(src).save(stem.with_suffix(".png"))
    im = Image.open(src).convert("RGB"); W, H = im.size; d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font("jhbd"), max(18, W // 28))
    for i, (sid, _) in enumerate(ps):
        x, y = (i % 4) * W / 4 + 6, (i // 4) * H / rows + 4
        d.rectangle([x, y, x + W // 9, y + W // 22], fill=(0, 0, 0))
        d.text((x + 4, y), sid, font=f, fill=(255, 220, 120))
    out = out_dir / f"storyboard_{k}_label.png"; im.save(out)
    return out


def main():
    sp = Path(sys.argv[1]).resolve()
    spec = json.loads(sp.read_text(encoding="utf-8"))
    landscape = "--landscape" in sys.argv
    sheets = panels(spec)
    with ThreadPoolExecutor(len(sheets)) as ex:
        for p in ex.map(lambda a: make(sp.parent, a[0] + 1, spec.get("cast", ""), a[1], landscape), enumerate(sheets)):
            print(p, flush=True)
    print(f"{len(spec['shots'])} 镜 → {len(sheets)} 张草图。这是看节奏与构图顺序用的草图，不是首帧。")


if __name__ == "__main__":
    main()
