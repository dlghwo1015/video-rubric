#!/usr/bin/env python3
"""
Shorts 원클릭 실행기
post_id 하나로 01~05 전체 실행

사용법:
    python3 run_all.py <post_id>
    python3 run_all.py 952aa01f

출력: shorts/output/<timestamp>_<post_id>/shorts_final.mp4
"""

import sys, subprocess
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).parent


def run_step(script: str, arg: str, label: str) -> str:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    r = subprocess.run(
        ["python3", str(SCRIPTS_DIR / script), arg],
        capture_output=False  # stdout/stderr 그대로 출력
    )
    if r.returncode != 0:
        print(f"\n❌ {label} 실패. 중단.")
        sys.exit(1)
    return r


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 run_all.py <post_id>")
        print("예시:   python3 run_all.py 952aa01f")
        sys.exit(1)

    post_id = sys.argv[1]
    start   = datetime.now()

    print(f"\n🚀 Shorts 파이프라인 시작")
    print(f"   post_id: {post_id}")
    print(f"   시작: {start.strftime('%H:%M:%S')}\n")

    # Step 1: 스크립트 생성 → out_dir_name 추출
    r = subprocess.run(
        ["python3", str(SCRIPTS_DIR / "01_generate_script.py"), post_id],
        capture_output=True, text=True
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)

    # out_dir_name 파싱 (마지막 줄에서 추출)
    out_dir_name = None
    for line in r.stdout.split("\n"):
        if "다음:" in line and "02_generate_html.py" in line:
            out_dir_name = line.split()[-1]
            break

    if not out_dir_name:
        print("❌ output 디렉토리 이름 파싱 실패")
        sys.exit(1)

    print(f"\n   output: {out_dir_name}")

    # Step 2~6
    for script, label in [
        ("02_generate_html.py",     "② HTML 슬라이드 생성"),
        ("03_generate_narration.py","③ 나레이션 생성 (Edge TTS) + 문장 타이밍"),
        ("03b_generate_srt.py",    "③b SRT 자막 생성"),
        ("04_render_html.py",      "④ HTML 렌더링 (Playwright)"),
        ("05_assemble.py",         "⑤ 최종 합성 + 자막 번인 (ffmpeg)"),
        ("06_deploy.py",           "⑥ 품질 검증 + 지정 장소 배포"),
    ]:
        run_step(script, out_dir_name, label)

    elapsed = (datetime.now() - start).seconds
    out_path = Path(__file__).parent.parent / "output" / out_dir_name / "shorts_final.mp4"

    print(f"\n{'='*50}")
    print(f"  ✅ 완료! 총 {elapsed}초")
    print(f"  📁 {out_path}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
