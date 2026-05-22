#!/usr/bin/env python3
"""
Shorts 품질 검증 + 지정 장소 배포
shorts_final.mp4 → {series}/ep{NN}/final/ep{NN}_shorts_{lang}.mp4

이 단계를 통과하지 않으면 "완료" 처리 불가.

품질 기준:
  1. shorts_final.mp4 존재 여부
  2. 자막 파일 (narration/shorts.srt) 존재 여부
  3. 영상 길이: 40s ~ 75s (벗어나면 경고 후 중단)
  4. 파일 크기: 1MB 이상 (너무 작으면 렌더 실패)
  5. 영상 해상도: 1080×1920 확인

사용법:
    python3 06_deploy.py <output_dir_name>
    python3 06_deploy.py demo_952aa01f
"""

import sys, json, subprocess, shutil
from pathlib import Path

OUT_BASE = Path(__file__).parent.parent / "output"
ROOT     = Path(__file__).parent.parent.parent  # video-rubric/

MIN_DURATION_S = 40.0
MAX_DURATION_S = 75.0
MIN_SIZE_MB    = 1.0
EXPECTED_W     = 1080
EXPECTED_H     = 1920


def ffprobe(path: Path, entries: str) -> str:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", entries,
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    return r.stdout.strip()


def check(condition: bool, msg: str):
    if not condition:
        print(f"\n❌ 품질 체크 실패: {msg}")
        print("   shorts_final.mp4를 다시 생성하세요.")
        sys.exit(1)
    print(f"  ✅ {msg}")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 06_deploy.py <output_dir_name>")
        sys.exit(1)

    out_dir    = OUT_BASE / sys.argv[1]
    final_mp4  = out_dir / "shorts_final.mp4"
    srt_path   = out_dir / "narration" / "shorts.srt"
    script     = json.loads((out_dir / "script.json").read_text())

    series     = script.get("series")
    ep_number  = script.get("ep_number")
    lang       = script.get("lang", "ko")

    print(f"\n🔍 품질 검증 시작\n  파일: {final_mp4.name}\n  대상: {series}/ep{ep_number:02d} [{lang}]\n")

    # ── 1. 파일 존재 ──────────────────────────────────────
    check(final_mp4.exists(), f"shorts_final.mp4 존재")

    # ── 2. 자막 파일 존재 ────────────────────────────────
    check(srt_path.exists(), f"narration/shorts.srt 존재")
    srt_lines = len([l for l in srt_path.read_text().splitlines() if "-->" in l])
    check(srt_lines >= 4, f"자막 항목 수 ({srt_lines}개) — 최소 4개")

    # ── 3. 파일 크기 ──────────────────────────────────────
    size_mb = final_mp4.stat().st_size / 1024 / 1024
    check(size_mb >= MIN_SIZE_MB, f"파일 크기 {size_mb:.1f}MB ≥ {MIN_SIZE_MB}MB")

    # ── 4. 영상 길이 ──────────────────────────────────────
    dur_str = ffprobe(final_mp4, "format=duration")
    duration = float(dur_str)
    check(
        MIN_DURATION_S <= duration <= MAX_DURATION_S,
        f"영상 길이 {duration:.1f}s (기준: {MIN_DURATION_S}~{MAX_DURATION_S}s)"
    )

    # ── 5. 해상도 ─────────────────────────────────────────
    wh = ffprobe(final_mp4, "stream=width,height")
    lines = [l for l in wh.splitlines() if l.strip() and "N/A" not in l]
    if lines:
        parts = lines[0].split(",")
        if len(parts) == 2:
            w, h = int(parts[0]), int(parts[1])
            check(w == EXPECTED_W and h == EXPECTED_H,
                  f"해상도 {w}×{h} == {EXPECTED_W}×{EXPECTED_H}")

    # ── 배포: 지정 장소로 복사 ────────────────────────────
    if not series or ep_number is None:
        print(f"\n⚠️  script.json에 series/ep_number 없음 — 복사 스킵")
        print(f"   수동 복사: {final_mp4}")
        return

    dest_dir = ROOT / series / f"ep{ep_number:02d}" / "final"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / f"ep{ep_number:02d}_shorts_{lang}.mp4"

    # 기존 파일 아카이브
    if dest_file.exists():
        from datetime import datetime
        archive_dir = dest_dir / "archive" / datetime.now().strftime("%Y%m%d")
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived = archive_dir / f"{dest_file.stem}_prev.mp4"
        shutil.move(str(dest_file), str(archived))
        print(f"\n  📦 기존 파일 아카이브: archive/{datetime.now().strftime('%Y%m%d')}/{archived.name}")

    shutil.copy2(str(final_mp4), str(dest_file))

    # 복사된 파일 크기 재확인
    copied_size = dest_file.stat().st_size / 1024 / 1024
    check(copied_size >= MIN_SIZE_MB, f"복사 완료 ({copied_size:.1f}MB)")

    print(f"\n{'='*55}")
    print(f"  ✅ 배포 완료")
    print(f"  📁 {dest_file}")
    print(f"  📊 {duration:.1f}s | {copied_size:.1f}MB | 자막 {srt_lines}개")
    print(f"{'='*55}")
    print(f"\n  다음:")
    print(f"  → YouTube 업로드: python3 pipeline/07_upload_youtube.py {ep_number} {lang} --series {series} --shorts-only")


if __name__ == "__main__":
    main()
