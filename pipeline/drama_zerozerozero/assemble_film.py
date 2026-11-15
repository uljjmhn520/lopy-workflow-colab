import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VIDEO_DIR = HERE / "video"
CUT_DIR = HERE / "cut"
AUDIO_DIR = HERE / "audio"
SFX_DIR = REPO / "sfx"
OUTPUT_DIR = REPO / "runtime" / "outputs"

CUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHOTS = [
    {
        "id": "s01",
        "speaker": None,
        "text": "",
        "sfx": ("sfx/脚步/foot_shoes_stone_637555.mp3", 0.5, 1.2),
    },
    {
        "id": "s02",
        "speaker": None,
        "text": "",
        "sfx": ("sfx/窗锁/window_handle_unlock_448393.mp3", 1.2, 0.9),
    },
    {
        "id": "s03",
        "speaker": None,
        "text": "",
        "sfx": ("sfx/球/thud_body_hit_276600.mp3", 2.0, 0.7),
    },
    {
        "id": "s04",
        "speaker": "艾玛",
        "text": "尸体处理完之前，我们先把货款结了。叫能做主的人出来。",
        "sfx": ("sfx/窗锁/window_click_slide_669069.mp3", 0.3, 1.4),
    },
]


def get_media_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(p.stdout.strip())


def make_ass_subtitles(shots_timing, ass_path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 768
PlayResY: 1344
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,30,30,130,1
Style: Punchline,Noto Sans CJK SC,46,&H0000E5FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.0,2.0,2,30,30,130,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for s in shots_timing:
        t_start = s["start"]
        t_end = s["end"]

        def fmt(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            sec = int(t % 60)
            cs = int(round((t - int(t)) * 100))
            if cs >= 100:
                cs = 99
            return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

        raw_text = s["text"].strip()
        if not raw_text:
            continue

        clean_text = re.sub(r"\[:.*?\]", "", raw_text)
        style = "Punchline" if "叫能做主的人出来" in clean_text else "Default"
        events.append(f"Dialogue: 0,{fmt(t_start)},{fmt(t_end)},{style},,0,0,0,,{clean_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"✔ 字幕文件生成: {ass_path}")


def main():
    print("=== [Stage 4] 影视级 4 镜无缝长镜头组装与压制 ===")
    clip_files = []
    shots_timing = []
    current_time = 0.0

    for s in SHOTS:
        v_file = VIDEO_DIR / f"{s['id']}.mp4"
        if not v_file.exists():
            v_file = VIDEO_DIR / f"h3_{s['id']}_00001_.mp4"
        if not v_file.exists():
            print(f"❌ 缺少视频源文件: {v_file}")
            sys.exit(1)

        dur = get_media_duration(v_file)
        clip_files.append(v_file)
        shots_timing.append({
            "id": s["id"],
            "speaker": s["speaker"],
            "text": s["text"],
            "start": current_time,
            "end": current_time + dur,
            "duration": dur,
            "sfx": s["sfx"]
        })
        print(f"  • {s['id']}: 时长 {dur:.2f}s | 开始 {current_time:.2f}s -> 结束 {current_time+dur:.2f}s")
        current_time += dur

    total_dur = current_time
    print(f"成片净时长: {total_dur:.2f} 秒 (约 {total_dur*24:.0f} 帧)")

    # 1. 拼接视频流与音频流
    concat_list = CUT_DIR / "concat_list.txt"
    with open(concat_list, "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf.resolve()}'\n")

    merged_raw = CUT_DIR / "merged_raw.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(merged_raw)
    ]
    subprocess.run(cmd_concat, check=True)
    print(f"✔ 4 镜物理拼接完成: {merged_raw}")

    # 2. 字幕生成
    sub_file = CUT_DIR / "subtitles.ass"
    make_ass_subtitles(shots_timing, sub_file)

    # 3. 音效叠加与压制最终成品
    final_output = OUTPUT_DIR / "drama_zerozerozero_v1.mp4"
    cmd_final = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(merged_raw),
        "-vf", f"subtitles={sub_file.resolve()}",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(final_output)
    ]
    subprocess.run(cmd_final, check=True)
    print(f"🎉 最终影视级成片导出完毕: {final_output}")
    print(f"   规格: 768x1344 竖屏 | 24fps | 净时长: {total_dur:.2f}s")


if __name__ == "__main__":
    main()
