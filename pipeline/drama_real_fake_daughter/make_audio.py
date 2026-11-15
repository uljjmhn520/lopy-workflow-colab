import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO_DIR = HERE / "audio"
CAND_DIR = AUDIO_DIR / "cand"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
CAND_DIR.mkdir(parents=True, exist_ok=True)

LINES = [
    {
        "id": "s01",
        "speaker": "wanwan",
        "voice": "zh-CN-XiaoxiaoNeural",
        "ref_sample": "姐姐，你终于回来了，我真的好想你。",
        "text": "姐姐，你终于回来了。你要是嫌我占了你的位置，我明天就搬走。"
    },
    {
        "id": "s02",
        "speaker": "guchu",
        "voice": "zh-CN-XiaoyiNeural",
        "ref_sample": "在这个家里，不是谁会哭谁就有理的。",
        "text": "不用等明天，我看门口这箱子，不是早替我收拾好了吗？"
    },
    {
        "id": "s03",
        "speaker": "mother",
        "voice": "zh-TW-HsiaoChenNeural",
        "ref_sample": "在苏家，一切规矩都由我说了算。",
        "text": "顾初！你刚进这个家门，就这么容不下晚晚？"
    },
    {
        "id": "s04",
        "speaker": "guchu",
        "voice": "zh-CN-XiaoyiNeural",
        "ref_sample": "在这个家里，不是谁会哭谁就有理的。",
        "text": "苏夫人别急着心疼，当年换掉我的幕后主使，正是她的亲生母亲。"
    }
]

import edge_tts

async def gen_refs():
    for item in LINES:
        sp = item["speaker"]
        ref_wav = AUDIO_DIR / f"ref_{sp}.wav"
        if not ref_wav.exists():
            mp3 = AUDIO_DIR / f"ref_{sp}.mp3"
            await edge_tts.Communicate(item["ref_sample"], item["voice"]).save(str(mp3))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(ref_wav)], check=True)
            mp3.unlink(missing_ok=True)
            print(f"✔ 角色参考音已生成: ref_{sp}.wav")

async def gen_lines():
    for item in LINES:
        sid = item["id"]
        final_wav = AUDIO_DIR / f"{sid}.wav"
        if final_wav.exists():
            print(f"✔ 分镜音频已存在: {final_wav.name}")
            continue

        mp3 = CAND_DIR / f"{sid}.mp3"
        await edge_tts.Communicate(item["text"], item["voice"]).save(str(mp3))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(final_wav)], check=True)
        mp3.unlink(missing_ok=True)
        print(f"✔ 分镜音频已合成: {final_wav.name} ({final_wav.stat().st_size / 1024:.1f} KB)")

def evaluate_asr():
    print("\n>>> 使用 Faster-Whisper 执行 Stage 1 ASR 反向质检打分...")
    from faster_whisper import WhisperModel
    # 使用 CPU 或 GPU
    try:
        asr = WhisperModel("large-v3", device="cpu", compute_type="int8", download_root="/workspace/models/Voice/models/whisper")
    except Exception:
        asr = WhisperModel("base", device="cpu", compute_type="int8")

    scores = {}
    for item in LINES:
        sid = item["id"]
        wav = AUDIO_DIR / f"{sid}.wav"
        segs, _ = asr.transcribe(str(wav), language="zh", beam_size=5)
        recognized = "".join(s.text for s in segs).strip()

        # 简单比对字形
        import difflib
        clean_text = "".join(c for c in item["text"] if c not in "，。！？…、")
        clean_rec = "".join(c for c in recognized if c not in "，。！？…、")
        ratio = difflib.SequenceMatcher(None, clean_text, clean_rec).ratio()
        scores[sid] = {"expected": item["text"], "heard": recognized, "score": round(ratio, 3)}
        print(f"  {sid} ({item['speaker']}): 期望「{clean_text}」 ➔ 识别「{clean_rec}」 (得分: {ratio:.3f})")

    log_file = AUDIO_DIR / "asr_score.json"
    log_file.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ Stage 1 ASR 评测结果已写入: {log_file}")

async def main():
    print("=== [Stage 1] 真假千金短剧 - 极速双角色语音合成与 ASR 对齐 ===")
    await gen_refs()
    await gen_lines()
    evaluate_asr()
    print("=== [Stage 1] 全部完成！===\n")

if __name__ == "__main__":
    asyncio.run(main())
