import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO_DIR = HERE / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
SFX_DIR = HERE.parents[1] / "sfx"

def make_silence(duration, out_path):
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(duration),
        "-c:a", "pcm_s16le",
        str(out_path)
    ]
    subprocess.run(cmd, check=True)

def main():
    print("=== [Stage 1] 准备音效与音轨素材 ===")
    
    # S01: 脚步声与空旷环境
    s01_wav = AUDIO_DIR / "s01.wav"
    foot_sfx = SFX_DIR / "脚步" / "foot_shoes_stone_637555.mp3"
    if foot_sfx.exists():
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(foot_sfx),
            "-t", "3.8",
            "-ar", "24000", "-ac", "1",
            str(s01_wav)
        ]
        subprocess.run(cmd, check=True)
    else:
        make_silence(3.8, s01_wav)
    print(f"✔ S01 音频就绪: {s01_wav}")

    # S02: 气氛音
    s02_wav = AUDIO_DIR / "s02.wav"
    make_silence(4.2, s02_wav)
    print(f"✔ S02 音频就绪: {s02_wav}")

    # S03: 坐下沉闷摩擦
    s03_wav = AUDIO_DIR / "s03.wav"
    make_silence(4.5, s03_wav)
    print(f"✔ S03 音频就绪: {s03_wav}")

    # S04: 台词对嘴音频占位 / 生成
    s04_wav = AUDIO_DIR / "s04.wav"
    if not s04_wav.exists():
        make_silence(4.5, s04_wav)
    print(f"✔ S04 音频就绪: {s04_wav}")
    print("Stage 1 音频准备完成！")

if __name__ == "__main__":
    main()
