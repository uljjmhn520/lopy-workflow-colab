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
        "speaker": "林总",
        "text": "周明，公司刚拿到两千万融资，你现在跟我提离职？",
        "sfx": ("sfx/球/thud_body_hit_276600.mp3", 0.6, 1.2),  # (file, offset_sec, volume)
    },
    {
        "id": "s02",
        "speaker": "周明",
        "text": "林总，您可能误会了，我不是来提离职的。",
        "sfx": None,
    },
    {
        "id": "s03",
        "speaker": "林总",
        "text": "那你递这份协议是什么意思？",
        "sfx": ("sfx/球/thud_body_hit_276600.mp3", 0.2, 0.8),
    },
    {
        "id": "s04",
        "speaker": "周明",
        "text": "这是新资方的委派函，从今天起，我是这里的控股股东。",
        "sfx": ("sfx/砝码/coin_knock_place_580375.mp3", 0.5, 1.5),
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
    """生成高对比度 9:16 短视频高级字幕 (白字黑边金高光)"""
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
        # Format time to H:MM:SS.cs
        def fmt(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            sec = int(t % 60)
            cs = int(round((t - int(t)) * 100))
            if cs >= 100: cs = 99
            return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

        st = fmt(t_start)
        et = fmt(t_end)
        style = "Punchline" if "控股股东" in s["text"] else "Default"
        txt = s['text']
        if len(txt) > 14 and "，" in txt:
            p1, p2 = txt.split("，", 1)
            txt = f"{p1}，\\N{p2}"
        events.append(f"Dialogue: 0,{st},{et},{style},,0,0,0,,{txt}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"✔ 字幕文件已生成: {ass_path}")


def assemble():
    print("=== [Stage 4] 开始执行短剧成片自动剪辑与混流 ===")

    # 1. 检查 4 个分镜视频
    mp4_files = []
    for shot in SHOTS:
        p = VIDEO_DIR / f"{shot['id']}.mp4"
        if not p.exists():
            print(f"❌ 缺少视频分镜文件: {p}")
            sys.exit(1)
        mp4_files.append(p)

    # 2. 测量各分镜实际精确时长
    cur_time = 0.0
    shots_timing = []
    for shot, mp4 in zip(SHOTS, mp4_files):
        dur = get_media_duration(mp4)
        shots_timing.append({
            "id": shot["id"],
            "speaker": shot["speaker"],
            "text": shot["text"],
            "start": cur_time,
            "end": cur_time + dur,
            "dur": dur,
            "sfx": shot["sfx"]
        })
        print(f"  分镜 {shot['id']}: 时长 {dur:.2f}s [{cur_time:.2f}s -> {cur_time+dur:.2f}s]")
        cur_time += dur
    total_dur = cur_time
    print(f"总片长: {total_dur:.2f}s")

    # 3. 生成精确对齐的 ASS 字幕
    ass_file = CUT_DIR / "subtitles.ass"
    make_ass_subtitles(shots_timing, ass_file)

    # 4. 生成 concat 列表
    concat_list = CUT_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for mp4 in mp4_files:
            f.write(f"file '{mp4.resolve()}'\n")

    # 5. 拼接原始视频序列
    raw_concat = CUT_DIR / "raw_concat.mp4"
    print(">>> 正在拼接 4 镜视频流...")
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_concat)
    ]
    subprocess.run(cmd_concat, check=True)

    # 6. 构建 SFX 音效轨道
    sfx_inputs = []
    filter_complex = []
    amix_inputs = ["[0:a]"]
    idx = 1
    for s in shots_timing:
        if s["sfx"]:
            sfx_rel, offset, vol = s["sfx"]
            sfx_path = REPO / sfx_rel
            if sfx_path.exists():
                delay_ms = int((s["start"] + offset) * 1000)
                sfx_inputs.extend(["-i", str(sfx_path)])
                filter_complex.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol}[sfx{idx}];")
                amix_inputs.append(f"[sfx{idx}]")
                idx += 1

    # 如果有音效则混音，否则直接直通
    ass_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    if len(amix_inputs) > 1:
        mix_filter = "".join(filter_complex) + f"{''.join(amix_inputs)}amix=inputs={len(amix_inputs)}:duration=first:dropout_transition=0[aout]"
        filter_str = f"[0:v]subtitles='{ass_escaped}'[vout];{mix_filter}"
        map_opts = ["-map", "[vout]", "-map", "[aout]"]
    else:
        filter_str = f"subtitles='{ass_escaped}'"
        filter_str_opt = ["-vf", filter_str]
        map_opts = []

    # 7. 终极压制：烧录字幕 + 音频混流 + H.264/AAC 标准压制
    final_output = CUT_DIR / "drama_workplace_v1.mp4"
    print(">>> 正在进行全片综合压制 (烧录字幕 + 音效叠加 + 9:16 对齐)...")
    cmd_final = [
        "ffmpeg", "-y",
        "-i", str(raw_concat),
        *sfx_inputs,
    ]
    if len(amix_inputs) > 1:
        cmd_final.extend([
            "-filter_complex", filter_str,
            "-map", "[vout]", "-map", "[aout]",
        ])
    else:
        cmd_final.extend([
            "-vf", f"subtitles={ass_file}",
            "-c:a", "aac", "-b:a", "192k",
        ])

    cmd_final.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        str(final_output)
    ])

    subprocess.run(cmd_final, check=True)

    # 8. 归档到 runtime/outputs/
    final_target = OUTPUT_DIR / "drama_workplace_v1.mp4"
    shutil.copy2(final_output, final_target)
    print(f"\n🎉 恭喜！成片剪辑全部完成！")
    print(f"成片路径: {final_target} ({final_target.stat().st_size / 1024**2:.2f} MB)")


if __name__ == "__main__":
    assemble()
