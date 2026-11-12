"""换声（voice conversion）：保留来源人声每个字的时间与语调，只把音色换成角色参考音。2026-10-23 建立。
用途：Seedance 2.5 等云端影片自己生的台词声音 → 换成你的角色参考音，嘴型时间不变（作者实测 14 句：像角色参考音 0.16 → 0.69）。
做法：用 BreezyVoice（CosyVoice-300M 架构）的零件，不经过文字：
  来源人声 → speech_tokenizer（50 Hz 语音 token，带内容与节奏）
  角色参考音 → 语音 token＋梅尔频谱（当 flow 的提示）＋CAM++ 说话人向量
  flow.inference(来源 token, 提示＝参考音) → 梅尔 → HiFT 声码器 → 角色音色的同一句话（同长度）
限制：念错的字（声调）会跟著来源一起保留——要修读音就换用 TTS 重配那一句。来源最好先用 BS-RoFormer 分离出干净人声。

执行（BreezyVoice venv，Python 3.10）：
  set PYTHONPATH=C:\\AI\\BreezyVoice\\winstub;C:\\AI\\BreezyVoice\\code;C:\\AI\\BreezyVoice\\code\\third_party\\Matcha-TTS
  C:\\AI\\BreezyVoice\\venv\\Scripts\\python.exe tools\\cosy_vc.py jobs.json
jobs.json：[{"src": "来源人声.wav", "ref": "角色参考音.wav", "out": "输出.wav"}, ...]   （相对路径以 jobs.json 所在资料夹为准）
输出 22050 Hz 单声道，长度与来源相同。"""
import json
import os
import sys
from pathlib import Path

import torch
import torchaudio

BV = Path(os.environ.get("AI_ROOT", r"C:\AI")) / "BreezyVoice"  # AI_ROOT = install root (default C:\AI)
for p in (BV / "winstub", BV / "code", BV / "code" / "third_party" / "Matcha-TTS"):
    sys.path.insert(0, str(p))
from hyperpyyaml import load_hyperpyyaml  # noqa: E402
from cosyvoice.cli.frontend import CosyVoiceFrontEnd  # noqa: E402
from cosyvoice.cli.model import CosyVoiceModel  # noqa: E402
from cosyvoice.utils.file_utils import load_wav  # noqa: E402


class _VC:
    """只载 frontend（语音 token、梅尔、说话人向量）与 flow／hift；BreezyVoice 的 frontend 多一个 model_dir 参数。"""

    def __init__(self, model_dir):
        with open(f"{model_dir}/cosyvoice.yaml", "r", encoding="utf-8") as f:
            cfg = load_hyperpyyaml(f)
        self.frontend = CosyVoiceFrontEnd(cfg["get_tokenizer"], cfg["feat_extractor"], model_dir, f"{model_dir}/campplus.onnx",
                                          f"{model_dir}/speech_tokenizer_v1.onnx", f"{model_dir}/spk2info.pt", False,
                                          cfg["allowed_special"])
        self.model = CosyVoiceModel(cfg["llm"], cfg["flow"], cfg["hift"])
        self.model.load(f"{model_dir}/llm.pt", f"{model_dir}/flow.pt", f"{model_dir}/hift.pt")

MAX_SEC = 30          # speech_tokenizer 一次最多 30 秒
REF_SEC = 12          # 参考音只取前 12 秒当提示（太长的提示会挤掉来源、变慢）


def main():
    jp = Path(sys.argv[1]).resolve()
    jobs = json.loads(jp.read_text(encoding="utf-8"))
    cv = _VC(str(BV / "model"))
    fe, m = cv.frontend, cv.model
    cache = {}
    for j in jobs:
        src, ref, out = (Path(j[k]) if Path(j[k]).is_absolute() else jp.parent / j[k] for k in ("src", "ref", "out"))
        if str(ref) not in cache:
            r16 = load_wav(str(ref), 16000)[:, :16000 * REF_SEC]
            r22 = torchaudio.transforms.Resample(16000, 22050)(r16)
            tok, tok_len = fe._extract_speech_token(r16)
            feat, feat_len = fe._extract_speech_feat(r22)
            # flow 里梅尔帧数＝token 数 ÷ 50 × 22050 ÷ 256（约 1.72 倍）；提示的 token 与梅尔要照这个比例对齐，
            # 否则 flow 会从输出前面多切掉一段（2026-10-23 写成 2 倍时，老师的句子 4 秒只剩 1.3 秒）
            n = min(tok.shape[1], int(feat.shape[1] * 50 * 256 / 22050))
            fl = int(n / 50 * 22050 / 256)
            cache[str(ref)] = (tok[:, :n], torch.tensor([n], dtype=torch.int32), feat[:, :fl],
                               torch.tensor([fl], dtype=torch.int32), fe._extract_spk_embedding(r16))
        ptok, ptok_len, pfeat, pfeat_len, emb = cache[str(ref)]
        s16 = load_wav(str(src), 16000)[:, :16000 * MAX_SEC]
        stok, stok_len = fe._extract_speech_token(s16)
        with torch.no_grad():
            mel = m.flow.inference(token=stok.to(m.device), token_len=stok_len.to(m.device), prompt_token=ptok.to(m.device),
                                   prompt_token_len=ptok_len.to(m.device), prompt_feat=pfeat.to(m.device),
                                   prompt_feat_len=pfeat_len.to(m.device), embedding=emb.to(m.device))
            wav = m.hift.inference(mel=mel).cpu()
        out.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(out), wav, 22050)
        print(f"[vc] {src.name} → {out.name}  {s16.shape[1] / 16000:.2f}s → {wav.shape[1] / 22050:.2f}s", flush=True)


if __name__ == "__main__":
    main()
