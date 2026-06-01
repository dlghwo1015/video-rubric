#!/usr/bin/env python3
"""
유튜브 수익 루브릭 — HTML → MP4 씬 렌더러 (Playwright, 1920×1080)
나레이션 길이 기준으로 각 슬라이드 녹화

사용법:
    python3 pipeline/04_render_html.py 1
    python3 pipeline/04_render_html.py 1 --series kanzen-japan --lang ja
"""

import sys, asyncio, subprocess, shutil, http.server, threading, os, argparse, json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT     = Path(__file__).parent.parent
WIDTH    = 1920
HEIGHT   = 1080
PORT     = 7892   # Shorts는 7891, 본 영상은 7892

DEFAULT_SCENE_ORDER = [
    "s01_hook", "s02_data_comparison",
    "s03_channel_1", "s04_channel_2",
    "s05_why_high_cpm", "s06_entry_strategy", "s07_verdict",
]


def get_scene_order(ep_dir: Path) -> list:
    """script.json에서 씬 순서 읽기, 없으면 youtube-rubric 기본값 반환"""
    script_path = ep_dir / "script.json"
    if script_path.exists():
        try:
            data = json.loads(script_path.read_text())
            scenes = data.get("scenes", [])
            if scenes:
                return [s["id"] for s in scenes]
        except Exception:
            pass
    return DEFAULT_SCENE_ORDER


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("ep_number", type=int)
    parser.add_argument("--series", default="youtube-rubric")
    parser.add_argument("--lang", default="ko", choices=["ko", "ja", "en"])
    return parser.parse_args()


def narr_duration(narr_dir: Path, sid: str) -> float:
    """narration/{lang}/{sid}.mp3 길이 반환"""
    path = narr_dir / f"{sid}.mp3"
    if not path.exists():
        return 3.0  # fallback
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 3.0


async def record_scene(playwright, page_url: str, sid: str, slide_idx: int,
                       dur: float, scenes_dir: Path, ep_dir: Path):
    narr_dur = dur + 0.8  # 나레이션 끝 후 0.8초 여유
    tmp_dir  = ep_dir / f"{sid}_tmp"
    tmp_dir.mkdir(exist_ok=True)

    browser = await playwright.chromium.launch()
    context = await browser.new_context(
        viewport={"width": WIDTH, "height": HEIGHT},
        record_video_dir=str(tmp_dir),
        record_video_size={"width": WIDTH, "height": HEIGHT},
    )
    page = await context.new_page()
    await page.goto(page_url, wait_until="networkidle")
    await asyncio.sleep(0.3)

    # ★ 모든 슬라이드 먼저 숨김 — goToSlide(0) 자동 실행으로 인한 s01 잔상 방지
    await page.evaluate(
        "document.querySelectorAll('.slide').forEach(s => {"
        "  s.style.display = 'none';"
        "  s.classList.remove('active');"
        "})"
    )
    await asyncio.sleep(0.15)

    # 해당 슬라이드만 표시 (window.goToSlide API 사용)
    await page.evaluate(f"window.goToSlide({slide_idx})")
    await asyncio.sleep(0.35)  # 애니메이션 시작 대기 (0.2 → 0.35)

    # 나레이션 길이만큼 녹화
    await asyncio.sleep(narr_dur)
    await context.close()
    await browser.close()

    # webm → mp4
    webm_files = list(tmp_dir.glob("*.webm"))
    if not webm_files:
        print(f"  ❌ {sid} webm 없음")
        return

    # scenes/{lang}/{sid}.mp4
    out_mp4 = scenes_dir / f"{sid}.mp4"

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(webm_files[0]),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-vf", f"scale={WIDTH}:{HEIGHT},format=yuv420p,fade=t=in:st=0:d=0.6:color=black",
        "-r", "30",
        str(out_mp4)
    ], capture_output=True, text=True)

    shutil.rmtree(tmp_dir)
    print(f"  ✅ {sid} ({dur:.1f}s) → {out_mp4.relative_to(ROOT)}")


async def main_async(ep_number: int, series: str, lang: str):
    out_dir  = ROOT / series / f"ep{ep_number:02d}"
    narr_dir = out_dir / "narration" / lang      # narration/ko/
    # HTML: html/ep{NN}_{lang}.html
    html_path = out_dir / "html" / f"ep{ep_number:02d}_{lang}.html"

    if not html_path.exists():
        print(f"❌ HTML 없음: {html_path}")
        print(f"   → html/ 폴더에 ep{ep_number:02d}_{lang}.html 을 먼저 생성하세요")
        sys.exit(1)

    # scenes/{lang}/ 서브폴더 생성
    scenes_dir = out_dir / "scenes" / lang
    scenes_dir.mkdir(parents=True, exist_ok=True)

    # 로컬 HTTP 서버 (html/ 폴더 기준)
    orig_cwd = os.getcwd()
    html_dir = html_path.parent
    os.chdir(str(html_dir))
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a: None
    server = http.server.HTTPServer(("", PORT), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    PAGE_URL = f"http://localhost:{PORT}/ep{ep_number:02d}_{lang}.html"

    print(f"\n[04] {series}/EP{ep_number:02d} [{lang}] 씬 렌더링 (1920×1080)\n")

    async with async_playwright() as p:
        scene_order = get_scene_order(out_dir)
        for idx, sid in enumerate(scene_order):
            dur = narr_duration(narr_dir, sid)
            print(f"  {sid} ({dur:.1f}s) ...", end="", flush=True)
            await record_scene(p, PAGE_URL, sid, idx, dur, scenes_dir, out_dir)

    server.shutdown()
    os.chdir(orig_cwd)

    mp4_count = len(list(scenes_dir.glob("*.mp4")))
    print(f"\n[04] ✅ 씬 렌더링 완료 → {scenes_dir} ({mp4_count}개)")


def main():
    args = parse_args()
    asyncio.run(main_async(args.ep_number, args.series, args.lang))


if __name__ == "__main__":
    main()
