#!/usr/bin/env python3
"""
문장 타이밍 → SRT 생성
narration/*_timing.json → narration/shorts.srt

원칙:
  - 씬별 누적 오프셋 계산 (씬1 종료 후 씬2 시작)
  - 자막 단위 = TTS SentenceBoundary 1문장 = 1자막 항목
  - 너무 긴 문장(30자+)은 절반으로 분리
  - 씬 전환 직전 자막은 0.3s 일찍 종료 (컷 겹침 방지)

사용법:
    python3 03b_generate_srt.py <output_dir_name>
"""

import sys, json, subprocess
from pathlib import Path

OUT_BASE  = Path(__file__).parent.parent / "output"
SCENE_IDS = ["s01_hook", "s02_point", "s03_insight", "s04_cta"]

MAX_CHARS_CJK = 22   # 한/일 최대 자막 글자수
MAX_WORDS_EN  = 8    # 영어 최대 자막 단어수


def get_audio_duration_ms(mp3_path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(mp3_path)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip()) * 1000


def ms_to_srt(ms: float) -> str:
    ms = max(0.0, ms)
    total_s = int(ms // 1000)
    millis  = int(ms % 1000)
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def split_long_sentence(text: str, lang: str) -> list:
    """긴 문장을 절반으로 분리 (타이밍은 호출자가 처리)"""
    if lang in ("ko", "ja"):
        if len(text) <= MAX_CHARS_CJK:
            return [text]
        # 중간 지점에서 분리
        mid = len(text) // 2
        # 구두점 위치 우선
        for i in range(mid, len(text)):
            if text[i] in "。、，,. ":
                return [text[:i+1].strip(), text[i+1:].strip()]
        return [text[:mid], text[mid:]]
    else:
        words = text.split()
        if len(words) <= MAX_WORDS_EN:
            return [text]
        mid = len(words) // 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 03b_generate_srt.py <output_dir_name>")
        sys.exit(1)

    out_dir  = OUT_BASE / sys.argv[1]
    narr_dir = out_dir / "narration"
    script   = json.loads((out_dir / "script.json").read_text())
    lang     = script.get("lang", "ko")

    print(f"\n📝 SRT 생성 (lang={lang})\n")

    srt_blocks   = []
    idx          = 1
    scene_offset = 0.0  # ms 단위 누적

    for sid in SCENE_IDS:
        time_path = narr_dir / f"{sid}_timing.json"
        mp3_path  = narr_dir / f"{sid}.mp3"

        if not mp3_path.exists():
            print(f"  ⚠️  {sid}.mp3 없음 — 스킵")
            continue

        mp3_dur_ms = get_audio_duration_ms(mp3_path)

        if not time_path.exists():
            print(f"  ⚠️  {sid}_timing.json 없음 — 나레이션 재생성 필요")
            scene_offset += mp3_dur_ms + 500
            continue

        sentences = json.loads(time_path.read_text())
        scene_subs = []

        for sent in sentences:
            parts = split_long_sentence(sent["sentence"], lang)
            n     = len(parts)
            part_dur = sent["duration_ms"] / n

            for i, part in enumerate(parts):
                start_ms = scene_offset + sent["offset_ms"] + i * part_dur
                end_ms   = start_ms + part_dur - 50  # 50ms 여유
                scene_subs.append({
                    "text":     part,
                    "start_ms": start_ms,
                    "end_ms":   end_ms,
                })

        # 씬 마지막 자막: 씬 종료 300ms 전에 끊기
        scene_end_ms = scene_offset + mp3_dur_ms
        if scene_subs:
            scene_subs[-1]["end_ms"] = min(
                scene_subs[-1]["end_ms"],
                scene_end_ms - 300
            )

        for sub in scene_subs:
            if sub["end_ms"] > sub["start_ms"]:
                srt_blocks.append(
                    f"{idx}\n"
                    f"{ms_to_srt(sub['start_ms'])} --> {ms_to_srt(sub['end_ms'])}\n"
                    f"{sub['text']}\n"
                )
                idx += 1

        scene_offset += mp3_dur_ms + 500  # 씬 간 0.5s 여유
        print(f"  ✅ {sid}: {len(scene_subs)}개 자막, 누적 오프셋 {scene_offset/1000:.1f}s")

    srt_text = "\n".join(srt_blocks)
    srt_path = narr_dir / "shorts.srt"
    srt_path.write_text(srt_text, encoding="utf-8")

    print(f"\n✅ SRT 저장 → {srt_path} (총 {idx-1}개)")
    print(f"   다음: python3 04_render_html.py {sys.argv[1]}")


if __name__ == "__main__":
    main()
