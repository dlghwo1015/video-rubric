#!/usr/bin/env python3
"""
유튜브 수익 루브릭 — 최종 합성
씬 MP4 + 나레이션 MP3 → concat → BGM 믹스 → {series}/ep{NN}/final/ep{NN}_final_{lang}.mp4

사용법:
    python3 pipeline/05_assemble.py 1
    python3 pipeline/05_assemble.py 1 --series kanzen-japan --lang ja
"""
from __future__ import annotations

import sys, subprocess, json, argparse, shutil
from pathlib import Path
from datetime import datetime

ROOT      = Path(__file__).parent.parent
BGM_VOL   = "0.06"     # 본 영상은 나레이션 집중 — BGM 은은하게
FFMPEG    = "/opt/homebrew/Cellar/ffmpeg-full/8.1.1/bin/ffmpeg"

# ── BGM 곡 목록 (섹션/성향별) ─────────────────────────────────────────────────
BGM_DIR = ROOT / "_shared/bgm"

# calm: 금융·비즈니스·분석 — 집중력, 지적 긴장감 (쇼팽 녹턴 + 베토벤 월광 + 파헬벨 캐논)
CALM = sorted((BGM_DIR / "calm").glob("*.mp3"))

# study: 기술·교육·튜토리얼 — 구조적, 논리적 (바흐 골드베르크 + 모차르트 터키 행진곡)
STUDY = sorted((BGM_DIR / "study").glob("*.mp3"))

# ambient: 라이프스타일·스토리·감성 — 여유, 분위기 (사티 + 드뷔시)
AMBIENT = sorted((BGM_DIR / "ambient").glob("*.mp3"))

# vivaldi: 시사·지정학 — 계절별 긴장감 변화 (비발디 사계 느린악장)
# EP 번호로 순환 → 봄→여름→가을→겨울→봄... 연속 EP마다 계절 자동 교체
VIVALDI = sorted((BGM_DIR / "vivaldi").glob("*.mp3"))

# japan: 일본서 사랑받는 명곡 (그리그·슈만·슈베르트·생상스·포레·마스네·드보르작·라벨·엘가)
# 일본어 타깃 영상, 라이프·감성·스토리 섹션 보강용 — 퍼블릭 도메인 안전
JAPAN = sorted((BGM_DIR / "japan").glob("*.mp3"))

# 섹션 → BGM 폴더 매핑
# B-1(금융) → calm / B-2(기술교육) → study / B-3(라이프) → ambient+japan 혼합
# B-4(게임) → calm / B-5(스토리) → ambient+japan 혼합 / B-6(시사) → vivaldi(사계)
# B-7(키즈) → ambient / B-8(니치취미) → ambient / intro/final → calm
# japan(일본어 타깃) → japan 전용
SECTION_BGM: dict[str, list[Path]] = {
    "B-1": CALM,
    "B-2": STUDY,
    "B-3": AMBIENT + JAPAN,   # 라이프스타일·감성 — 다채롭게 (15곡 풀)
    "B-4": CALM,
    "B-5": AMBIENT + JAPAN,   # 스토리·미스터리 — 감성 넓게 (15곡 풀)
    "B-6": VIVALDI,           # 비발디 사계 — 봄/여름/가을/겨울 순환
    "B-7": AMBIENT,
    "B-8": AMBIENT,
    "intro": CALM,
    "final": CALM,
    "japan": JAPAN,           # 일본어 타깃 전용 섹션 (context.json에서 명시)
}


def select_bgm(ep_number: int, section: str) -> Path:
    """
    섹션으로 BGM 폴더를 정하고, ep_number로 트랙을 순환 선택.
    같은 폴더 안에서 EP마다 트랙이 달라져 앞뒤 EP와 다른 곡이 흘러나온다.
    (calm 9곡 → 9 EP마다 한 바퀴, ambient 4곡 → 4 EP마다 한 바퀴)
    """
    pool = SECTION_BGM.get(section, CALM)
    if not pool:
        fallback = CALM or STUDY or AMBIENT
        return fallback[ep_number % len(fallback)] if fallback else None
    return pool[ep_number % len(pool)]
DEFAULT_SCENE_IDS = [
    "s01_hook", "s02_data_comparison",
    "s03_channel_1", "s04_channel_2",
    "s05_why_high_cpm", "s06_entry_strategy", "s07_verdict",
]


def get_scene_ids(ep_dir: Path) -> list:
    """script.json에서 씬 ID 목록 읽기, 없으면 youtube-rubric 기본값 반환"""
    script_path = ep_dir / "script.json"
    if script_path.exists():
        try:
            data = json.loads(script_path.read_text())
            scenes = data.get("scenes", [])
            if scenes:
                return [s["id"] for s in scenes]
        except Exception:
            pass
    return DEFAULT_SCENE_IDS


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("ep_number", type=int)
    parser.add_argument("--series", default="youtube-rubric")
    parser.add_argument("--lang", default="ko", choices=["ko", "ja", "en"])
    return parser.parse_args()


def run(cmd, label=""):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ {label} 실패:\n{r.stderr[-500:]}")
        sys.exit(1)
    return r


def get_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 0.0


def archive_if_exists(path: Path):
    """기존 파일이 있으면 archive/YYYYMMDD/ 로 이동"""
    if not path.exists():
        return
    archive_dir = path.parent / "archive" / datetime.now().strftime("%Y%m%d")
    archive_dir.mkdir(parents=True, exist_ok=True)
    dest = archive_dir / path.name
    shutil.move(str(path), str(dest))
    print(f"  📦 archive: {path.name} → {dest.relative_to(ROOT)}")


def main():
    args = parse_args()
    ep_number = args.ep_number
    series    = args.series
    lang      = args.lang

    out_dir   = ROOT / series / f"ep{ep_number:02d}"
    scene_dir = out_dir / "scenes" / lang        # scenes/ko/
    narr_dir  = out_dir / "narration" / lang     # narration/ko/
    final_dir = out_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir   = out_dir / "tmp_assemble"
    tmp_dir.mkdir(exist_ok=True)

    # context.json에서 섹션 읽기
    ctx_file = out_dir / "context.json"
    section  = "B-1"   # 기본값
    if ctx_file.exists():
        try:
            ctx     = json.loads(ctx_file.read_text())
            section = ctx.get("ep", {}).get("section", "B-1") or "B-1"
        except Exception:
            pass

    bgm_path = select_bgm(ep_number, section)
    print(f"\n[05] {series}/EP{ep_number:02d} [{lang}] 최종 합성  (섹션:{section})\n")
    if bgm_path:
        print(f"  🎵 BGM 선택: {bgm_path.name}")

    # Step 1: 씬 MP4 + 나레이션 MP3 합치기 (video+audio per scene)
    scene_ids = get_scene_ids(out_dir)
    merged_list = []
    for sid in scene_ids:
        video = scene_dir / f"{sid}.mp4"
        audio = narr_dir  / f"{sid}.mp3"
        merged = tmp_dir / f"{sid}_merged.mp4"

        if not video.exists():
            print(f"  ⚠  {sid}.mp4 없음 — 스킵")
            continue

        if audio.exists():
            run([
                FFMPEG, "-y",
                "-i", str(video),
                "-i", str(audio),
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(merged)
            ], f"{sid} 비디오+오디오 합성")
        else:
            # 나레이션 없으면 묵음으로
            dur = get_duration(video)
            run([
                FFMPEG, "-y",
                "-i", str(video),
                "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(dur),
                "-shortest",
                str(merged)
            ], f"{sid} 묵음 합성")

        merged_list.append(merged)
        print(f"  ✅ {sid} 합성 완료")

    if not merged_list:
        print("❌ 합성할 씬이 없습니다")
        sys.exit(1)

    # Step 2: 씬들 concat
    concat_txt = tmp_dir / "concat.txt"
    concat_txt.write_text(
        "\n".join(f"file '{m.resolve()}'" for m in merged_list)
    )
    concat_mp4 = tmp_dir / "concat.mp4"
    run([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(concat_mp4)
    ], "concat")
    print(f"\n  📎 씬 연결 완료 ({len(merged_list)}개)")

    # Step 3: BGM 믹스
    # 파일명: final/ep{NN}_final_{lang}.mp4
    final_mp4 = final_dir / f"ep{ep_number:02d}_final_{lang}.mp4"
    archive_if_exists(final_mp4)

    if bgm_path and bgm_path.exists():
        total_dur  = get_duration(concat_mp4)
        fade_start = max(0.0, total_dur - 3.0)   # 영상 끝 3초 전부터 페이드 아웃
        run([
            FFMPEG, "-y",
            "-i", str(concat_mp4),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-filter_complex",
            f"[1:a]volume={BGM_VOL},afade=t=out:st={fade_start:.2f}:d=3[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            str(final_mp4)
        ], "BGM 믹스")
        print(f"  🎵 BGM 믹스 완료 ({bgm_path.name}, volume={BGM_VOL}, 총 {total_dur:.1f}초, fade@{fade_start:.1f}s)")
    else:
        shutil.copy(str(concat_mp4), str(final_mp4))
        print(f"  ⚠  BGM 파일 없음 → BGM 없이 저장")

    # 정리
    shutil.rmtree(tmp_dir)

    dur = get_duration(final_mp4)
    size_mb = final_mp4.stat().st_size / 1024 / 1024

    print(f"\n[05] ✅ 최종 파일 → {final_mp4.relative_to(ROOT)}")
    print(f"     길이: {dur:.1f}초 ({dur/60:.1f}분), 크기: {size_mb:.1f}MB")


if __name__ == "__main__":
    main()
