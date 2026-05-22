#!/usr/bin/env python3
"""
Shorts 나레이션 생성 (Edge TTS) + 문장 타이밍 저장
script.json → narration/*.mp3 + narration/*_timing.json

타이밍 형식:
  [{"sentence": "...", "offset_ms": 100.0, "duration_ms": 3500.0}, ...]

사용법:
    python3 03_generate_narration.py <output_dir_name>
"""

import sys, asyncio, json
from pathlib import Path
import edge_tts

OUT_BASE = Path(__file__).parent.parent / "output"
RATE     = "+10%"

VOICE_MAP = {
    "ko": "ko-KR-SunHiNeural",
    "ja": "ja-JP-NanamiNeural",
    "en": "en-US-AriaNeural",
}


async def generate(scene: dict, narr_dir: Path, voice: str):
    sid      = scene["id"]
    text     = scene["text"]
    out_mp3  = narr_dir / f"{sid}.mp3"
    out_time = narr_dir / f"{sid}_timing.json"

    print(f"  → {sid} ...", end="", flush=True)

    comm = edge_tts.Communicate(text, voice, rate=RATE)

    audio_chunks = []
    sentences    = []

    async for event in comm.stream():
        if event["type"] == "audio":
            audio_chunks.append(event["data"])
        elif event["type"] == "SentenceBoundary":
            sentences.append({
                "sentence":    event["text"],
                "offset_ms":   round(event["offset"]   / 10000, 1),   # 100ns → ms
                "duration_ms": round(event["duration"] / 10000, 1),
            })

    out_mp3.write_bytes(b"".join(audio_chunks))
    out_time.write_text(json.dumps(sentences, ensure_ascii=False, indent=2))

    print(f" ✅ ({len(sentences)}문장)")


async def main_async(out_dir_name: str):
    out_dir  = OUT_BASE / out_dir_name
    script   = json.loads((out_dir / "script.json").read_text())
    lang     = script.get("lang", "ko")
    voice    = VOICE_MAP.get(lang, VOICE_MAP["ko"])
    narr_dir = out_dir / "narration"
    narr_dir.mkdir(exist_ok=True)

    print(f"\n🎙️  나레이션 생성 ({voice}, {RATE})\n")
    for s in script["scenes"]:
        await generate(s, narr_dir, voice)
    print(f"\n✅ 완료 → {narr_dir}/")
    print(f"   다음: python3 03b_generate_srt.py {out_dir_name}")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 03_generate_narration.py <output_dir_name>")
        sys.exit(1)
    asyncio.run(main_async(sys.argv[1]))


if __name__ == "__main__":
    main()
