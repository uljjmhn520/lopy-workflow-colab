"""〈D-7〉台词与声音来源。LINES: (id, speaker, 字幕文字)。TTS 文字去掉删节号与～。
speaker：shb 山狮霸（三师爸克隆）／xw 小雯（只用 Breeze 直出）／afu 阿福／ahe 阿禾旁白。"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CH = ROOT / "角色资产/老师这次换你"
REFS = {
    "shb": (ROOT / "角色资产/老师_山狮霸/voice_ref.wav"   # 原专案为本人授权录音，不公开,
            "<参考录音的逐字稿>"),
    "xw": (CH / "班长小雯/voice_ref.wav", "各位同学请安静，我是班长，老师马上就要到了。"),
    "afu": (CH / "阿福/voice_ref.wav", "老师,我刚刚真的都有听,我只是眼睛闭起来而已啦。"),
    "ahe": (ROOT / "短片/阿福三个绝招_20260929/voice_tw/ref/ahe_tw.wav", None),   # 逐字稿由 voice_stage1.py 用 ASR 取得
}
EDGE = {"shb": "zh-TW-YunJheNeural", "ahe": "zh-TW-YunJheNeural", "afu": "zh-TW-YunJheNeural", "xw": "zh-TW-HsiaoChenNeural"}
LINES = [
    ("L01", "shb", "下周段考喔。"), ("L02", "xw", "老师，是下周四吗？"), ("L03", "shb", "……对。"),
    ("L05", "shb", "明天段考。早点睡。"), ("L14", "afu", "又有学习单～"), ("L16", "afu", "……今天，段考？"),
    ("L17", "afu", "老师，考卷……是热的。"), ("L19", "shb", "……开始作答。"), ("L21", "afu", "……好温暖。"),
    ("V01", "ahe", "段考，有三种人。"), ("V02", "ahe", "第一种，先知先觉。一周前就开始。"),
    ("V03", "ahe", "第二种跟第三种，那时候还没出现。"), ("V04", "ahe", "第二种，后知后觉。也就是我。"),
    ("V05", "ahe", "没关系。一个晚上，够了。"), ("V06", "ahe", "跟班长借笔记好了。"), ("V07", "ahe", "……上周四。"),
    ("V08", "ahe", "第三种人，睡得很好。"), ("V09", "ahe", "第三种，不知不觉。"), ("V10", "ahe", "原来，段考有四种人。"),
]
TTS = {lid: tx.replace("……", "").replace("～", "！") for lid, _, tx in LINES}
TTS["L03"] = "对。"; TTS["V07"] = "上周四。"
