#!/usr/bin/env python3
"""Make a composite preview gallery image for human keyframe review (Review Gates).

Usage:
  python3 tools/make_gallery.py img1.png img2.png img3.png img4.png --labels "S01 林总" "S02 周明" "S03 林总" "S04 周明" --out gallery.png
  python3 tools/make_gallery.py --dir runtime/first --out runtime/first/gallery.png
"""
import argparse
import math
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def get_chinese_font(size=28):
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def create_gallery(image_paths, labels=None, out_path="gallery.png", cell_width=480, cell_height=840):
    images = []
    for p in image_paths:
        path = Path(p)
        if not path.is_file():
            print(f"[WARN] 找不到图像文件: {path}", file=sys.stderr)
            continue
        try:
            im = Image.open(path).convert("RGBA")
            im = im.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
            images.append((path.stem, im))
        except Exception as e:
            print(f"[WARN] 无法打开图像 {path}: {e}", file=sys.stderr)

    if not images:
        print("[ERROR] 没有有效图像可合成画廊！", file=sys.stderr)
        return False

    num_images = len(images)
    cols = 2 if num_images in (2, 3, 4) else (3 if num_images in (5, 6) else 2)
    rows = math.ceil(num_images / cols)

    gap = 12
    margin = 16
    total_w = cols * cell_width + (cols - 1) * gap + 2 * margin
    total_h = rows * cell_height + (rows - 1) * gap + 2 * margin

    # 深色电影感背景画布
    canvas = Image.new("RGBA", (total_w, total_h), (20, 22, 28, 255))
    draw = ImageDraw.Draw(canvas)
    font = get_chinese_font(size=24)

    for idx, (stem, im) in enumerate(images):
        c = idx % cols
        r = idx // cols
        x = margin + c * (cell_width + gap)
        y = margin + r * (cell_height + gap)

        # 贴图
        canvas.paste(im, (x, y))

        # 标签处理
        label_text = labels[idx] if (labels and idx < len(labels)) else stem
        # 绘制半透明胶囊标签
        bbox = font.getbbox(label_text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        badge_pad_x = 12
        badge_pad_y = 6
        badge_x0 = x + 16
        badge_y0 = y + 16
        badge_x1 = badge_x0 + text_w + 2 * badge_pad_x
        badge_y1 = badge_y0 + text_h + 2 * badge_pad_y

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [badge_x0, badge_y0, badge_x1, badge_y1],
            radius=6,
            fill=(0, 0, 0, 180),
            outline=(255, 200, 0, 220),
            width=2
        )
        overlay_draw.text((badge_x0 + badge_pad_x, badge_y0 + badge_pad_y - 2), label_text, fill=(255, 255, 255, 255), font=font)
        canvas = Image.alpha_composite(canvas, overlay)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(str(out), "PNG", quality=95)
    print(f"✔ 首帧画廊拼图已生成: {out} ({total_w}x{total_h}, 共 {num_images} 镜)")
    return True


def main():
    parser = argparse.ArgumentParser(description="合成 2x2 审查画廊大图")
    parser.add_argument("images", nargs="*", help="分镜首帧图片路径列表")
    parser.add_argument("--dir", type=str, help="自动扫描指定目录下的 png 图片")
    parser.add_argument("--labels", nargs="*", help="每个分镜的展示名称 (如 'S01 林总')")
    parser.add_argument("--out", type=str, default="gallery.png", help="输出拼图文件路径")
    parser.add_argument("--width", type=int, default=480, help="单格宽度 (默认 480)")
    parser.add_argument("--height", type=int, default=840, help="单格高度 (默认 840)")

    args = parser.parse_args()

    paths = list(args.images)
    if args.dir:
        dir_path = Path(args.dir)
        found = sorted([p for p in dir_path.glob("*.png") if "gallery" not in p.name])
        paths.extend(found)

    if not paths:
        parser.print_help()
        sys.exit(1)

    ok = create_gallery(paths, args.labels, args.out, args.width, args.height)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
