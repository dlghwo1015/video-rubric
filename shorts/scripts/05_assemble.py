#!/usr/bin/env python3
"""
Shorts 최종 합성
씬 MP4 + 나레이션 MP3 → concat → BGM 믹스 → 자막 번인 → shorts_final.mp4

원칙:
  1. 씬 전환: 나레이션 끝 후 0.5s 페이드아웃 → 다음 씬 페이드인 0.3s
  2. 자막: narration/shorts.srt 번인 필수 (없으면 빌드 중단)
  3. 자막 스타일: 웜 미니멀 — 흰 텍스트 + 검정 외곽선, 하단 중앙

사용법:
    python3 05_assemble.py <output_dir_name>
"""

import sys, subprocess, json
from pathlib import Path

OUT_BASE   = Path(__file__).parent.parent / "output"
BGM_PATH   = Path(__file__).parent.parent.parent / "_shared/bgm/calm/chopin_nocturne_op9_no2.mp3"
BGM_VOL    = "0.08"
FFMPEG     = "/opt/homebrew/Cellar/ffmpeg-full/8.1.1/bin/ffmpeg"
SCENE_IDS  = ["s01_hook", "s02_point", "s03_insight", "s04_cta"]

# 자막 폰트 (언어별)
FONT_MAP = {
    "ko": "Apple SD Gothic Neo",
    "ja": "Hiragino Sans",
    "en": "Helvetica Neue",
}
FONT_SIZE  = 52    # ASS PlayResY=1920 기준 픽셀 (실제 렌더 크기)
MARGIN_V   = 120   # 하단에서 픽셀 (1920px 기준)


def run(cmd, label=""):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ {label} 실패:\n{r.stderr[-800:]}")
        sys.exit(1)
    return r


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 05_assemble.py <output_dir_name>")
        sys.exit(1)

    out_dir   = OUT_BASE / sys.argv[1]
    scene_dir = out_dir / "scenes"
    narr_dir  = out_dir / "narration"
    script    = json.loads((out_dir / "script.json").read_text())
    lang      = script.get("lang", "ko")
    font_name = FONT_MAP.get(lang, FONT_MAP["ko"])

    # ── 자막 파일 존재 확인 (필수) ──────────────────────────────
    srt_path = narr_dir / "shorts.srt"
    if not srt_path.exists():
        print(f"❌ 자막 파일 없음: {srt_path}")
        print(f"   먼저 실행: python3 03b_generate_srt.py {sys.argv[1]}")
        sys.exit(1)

    print(f"\n🎞️  최종 합성 (lang={lang})\n")

    # Step 1: 씬 + 나레이션 합치기 (씬 전환 페이드아웃 포함)
    mixed_dir = out_dir / "mixed"
    mixed_dir.mkdir(exist_ok=True)
    mixed_files = []

    for i, sid in enumerate(SCENE_IDS):
        vid = scene_dir / f"{sid}.mp4"
        aud = narr_dir  / f"{sid}.mp3"
        out = mixed_dir / f"{sid}.mp4"
        print(f"  믹스: {sid} ...", end="", flush=True)

        # 나레이션 길이 확인
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(aud)],
            capture_output=True, text=True
        )
        narr_dur = float(r.stdout.strip())
        total_dur = narr_dur + 0.5  # 0.5s 여유

        # 페이드아웃: 마지막 0.3초 (씬 끝 컷이 뚝 끊기지 않도록)
        fade_start = max(0.0, total_dur - 0.35)

        run([
            FFMPEG, "-y",
            "-i", str(vid),
            "-i", str(aud),
            "-filter_complex",
            (
                f"[0:v]fade=t=out:st={fade_start:.3f}:d=0.3:color=black[v];"
                f"[1:a]afade=t=out:st={narr_dur - 0.1:.3f}:d=0.15[a]"
            ),
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_dur),
            str(out)
        ], sid)
        mixed_files.append(out)
        print(" ✅")

    # Step 2: concat
    concat_txt = out_dir / "concat.txt"
    concat_txt.write_text("\n".join(f"file '{f}'" for f in mixed_files))

    concat_out = out_dir / "shorts_concat.mp4"
    print("  합치기 ...", end="", flush=True)
    run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(concat_out)
    ], "concat")
    print(" ✅")

    # Step 3: BGM 오버레이
    bgm_out = out_dir / "shorts_bgm.mp4"
    if BGM_PATH.exists():
        print("  BGM 믹스 ...", end="", flush=True)
        run([
            FFMPEG, "-y",
            "-i", str(concat_out),
            "-i", str(BGM_PATH),
            "-filter_complex",
            f"[0:a]volume=1.0[v];[1:a]volume={BGM_VOL}[b];[v][b]amix=inputs=2:duration=first[out]",
            "-map", "0:v",
            "-map", "[out]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            str(bgm_out)
        ], "bgm")
        print(" ✅")
    else:
        print("  ⚠️  BGM 없음 — 스킵")
        import shutil
        shutil.copy(concat_out, bgm_out)

    # Step 4: 자막 번인 (SRT → ASS 스타일 번인)
    final_out = out_dir / "shorts_final.mp4"
    print("  자막 번인 ...", end="", flush=True)

    # SRT 경로에 콜론 등 특수문자 방지: 절대경로를 ffmpeg subtitle filter에 맞게 이스케이프
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # PlayResX/Y 명시 필수: 기본값(384×288)으로 스케일업 되면 폰트가 폭발함
    subtitle_filter = (
        f"subtitles='{srt_escaped}'"
        f":force_style='PlayResX=1080,PlayResY=1920"
        f",FontName={font_name}"
        f",FontSize={FONT_SIZE}"
        f",PrimaryColour=&H00FFFFFF"
        f",OutlineColour=&H00000000"
        f",BackColour=&H80000000"
        f",Bold=1"
        f",Outline=3"
        f",Shadow=1"
        f",Alignment=2"
        f",MarginV={MARGIN_V}'"
    )

    run([
        FFMPEG, "-y",
        "-i", str(bgm_out),
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "copy",
        str(final_out)
    ], "subtitles")
    print(" ✅")

    # 완료 확인
    size_mb = final_out.stat().st_size / 1024 / 1024
    print(f"\n✅ 완성 → {final_out}")
    print(f"   크기: {size_mb:.1f} MB")
    print(f"\n🔍 반드시 재생 확인:")
    print(f"   open '{final_out}'")
    print(f"   체크리스트: ① 자막-나레이션 싱크 ② 씬 전환 자연스러움 ③ 디자인 색상")


if __name__ == "__main__":
    main()
