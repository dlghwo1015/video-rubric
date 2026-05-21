#!/usr/bin/env python3
"""
HTML 슬라이드 → MP4 (Playwright 비디오 녹화)
스크린샷 방식 대신 실시간 녹화 → 애니메이션 살아있음
"""

import asyncio, subprocess, shutil
from pathlib import Path
from playwright.async_api import async_playwright

BASE     = Path(__file__).parent.parent
NARR     = BASE / "narration" / "ko"
OUT_DIR  = BASE / "scenes" / "ko"
OUT_DIR.mkdir(exist_ok=True)

URL      = "http://localhost:7890/ep00_visual_ko.html"
WIDTH    = 1920
HEIGHT   = 1080

SCENE_IDS = ["s01_hook","s02_cpm","s03_rpm","s04_faceless","s05_ocean","s06_saturation","s07_outro"]
SLIDE_NUM = {sid: i+1 for i, sid in enumerate(SCENE_IDS)}

# 씬별 애니메이션 트리거 JS
ANIM_TRIGGERS = {
    "s01_hook": """
        // 키워드 3행 순차 fadeUp
        ['w1','w2','w3'].forEach((id,i) => {
            setTimeout(() => {
                const el = document.getElementById(id);
                if(el) el.classList.add('go');
            }, i * 500);
        });
        setTimeout(() => {
            const s = document.getElementById('s1-sub');
            if(s) s.classList.add('go');
        }, 1700);
        setTimeout(() => {
            const h = document.getElementById('s1-hl');
            if(h) h.classList.add('go');
        }, 2500);
    """,
    "s02_cpm": """
        // term tag 즉시
        const tl2 = document.getElementById('tl-2');
        if(tl2) tl2.classList.add('go');
        // typing title
        setTimeout(() => {
            const tt = document.getElementById('tt-2');
            if(tt) tt.classList.add('go');
        }, 200);
        // 설명 텍스트
        setTimeout(() => {
            const td = document.getElementById('td-2');
            if(td) td.classList.add('go');
        }, 1600);
        // 비교 박스
        setTimeout(() => {
            const tc = document.getElementById('tc-2');
            if(tc) tc.classList.add('go');
        }, 2200);
        // 차트 헤더
        setTimeout(() => {
            const ch = document.getElementById('ch-2');
            if(ch) ch.classList.add('go');
        }, 400);
        // 바 차트 순차 성장
        setTimeout(() => {
            document.querySelectorAll('#bc-2 .bar-wrap').forEach((b,i) => {
                setTimeout(() => b.classList.add('go'), i * 150);
            });
        }, 800);
    """,
    "s03_rpm": """
        // 헤더
        const rh = document.getElementById('rh-3');
        if(rh) rh.classList.add('go');
        // 카드 순차 등장
        setTimeout(() => {
            const rc1 = document.getElementById('rc1-3');
            if(rc1) rc1.classList.add('go');
        }, 400);
        setTimeout(() => {
            const ra = document.getElementById('ra-3');
            if(ra) ra.classList.add('go');
        }, 700);
        setTimeout(() => {
            const rc2 = document.getElementById('rc2-3');
            if(rc2) rc2.classList.add('go');
        }, 600);
        // 노트
        setTimeout(() => {
            const rn = document.getElementById('rn-3');
            if(rn) rn.classList.add('go');
        }, 1400);
    """,
    "s04_faceless": """
        // 왼쪽 타이틀 순차
        const ft4 = document.getElementById('ft-4');
        if(ft4) ft4.classList.add('go');
        setTimeout(() => {
            const fn4 = document.getElementById('fn-4');
            if(fn4) fn4.classList.add('go');
        }, 200);
        setTimeout(() => {
            const fd4 = document.getElementById('fd-4');
            if(fd4) fd4.classList.add('go');
        }, 600);
        // 오른쪽 카드 순차 슬라이드업
        ['fc1-4','fc2-4','fc3-4','fc4-4'].forEach((id,i) => {
            setTimeout(() => {
                const c = document.getElementById(id);
                if(c) c.classList.add('go');
            }, 400 + i * 200);
        });
    """,
    "s05_ocean": """
        // 헤드
        const oh5 = document.getElementById('oh-5');
        if(oh5) oh5.classList.add('go');
        // 카드 좌우 슬라이드인
        setTimeout(() => {
            const oc1 = document.getElementById('oc1-5');
            if(oc1) oc1.classList.add('go');
        }, 300);
        setTimeout(() => {
            const oc2 = document.getElementById('oc2-5');
            if(oc2) oc2.classList.add('go');
        }, 500);
        // 노트
        setTimeout(() => {
            const on5 = document.getElementById('on-5');
            if(on5) on5.classList.add('go');
        }, 1500);
    """,
    "s06_saturation": """
        // 왼쪽 텍스트 순차
        const sgt = document.getElementById('sg-tag');
        if(sgt) sgt.classList.add('go');
        setTimeout(() => {
            const sgi = document.getElementById('sg-title');
            if(sgi) sgi.classList.add('go');
        }, 200);
        setTimeout(() => {
            const sgb = document.getElementById('sg-body');
            if(sgb) sgb.classList.add('go');
        }, 600);
        // SVG 라인 드로잉
        setTimeout(() => {
            document.querySelectorAll('.draw-line').forEach((l,i) => {
                setTimeout(() => l.classList.add('go'), i * 200);
            });
            // 도트는 라인 그려진 후
            setTimeout(() => {
                document.querySelectorAll('.dot-ap').forEach((d,i) => {
                    setTimeout(() => d.classList.add('go'), i * 150);
                });
            }, 2200);
        }, 500);
    """,
    "s07_outro": """
        // 헤드
        const oh7 = document.getElementById('oh-7');
        if(oh7) oh7.classList.add('go');
        // 6카드 순차 슬라이드업
        ['sc1-7','sc2-7','sc3-7','sc4-7','sc5-7','sc6-7'].forEach((id,i) => {
            setTimeout(() => {
                const c = document.getElementById(id);
                if(c) c.classList.add('go');
            }, 200 + i * 150);
        });
        // CTA
        setTimeout(() => {
            const oc = document.getElementById('oc-7');
            if(oc) oc.classList.add('go');
        }, 1800);
    """,
}

def narr_duration(sid):
    path = NARR / f"{sid}.mp3"
    r = subprocess.run(
        ["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())

async def record_scene(browser, sid, slide_n, dur):
    tmp_dir = OUT_DIR / f"{sid}_vid_tmp"
    tmp_dir.mkdir(exist_ok=True)

    # 비디오 녹화 컨텍스트
    context = await browser.new_context(
        viewport={"width": WIDTH, "height": HEIGHT},
        record_video_dir=str(tmp_dir),
        record_video_size={"width": WIDTH, "height": HEIGHT},
    )
    page = await context.new_page()
    await page.goto(URL, wait_until="networkidle")
    await asyncio.sleep(0.3)

    # 해당 슬라이드만 표시 + 모든 요소 visible 초기화
    await page.evaluate(f"""
        for (let i = 1; i <= 7; i++) {{
            const s = document.getElementById('slide-' + i);
            if (!s) continue;
            s.style.display = i === {slide_n} ? 'flex' : 'none';
            s.style.opacity = '1';
            s.style.transform = 'scale(1)';
        }}
        const ctrl = document.querySelector('.controls');
        if (ctrl) ctrl.style.display = 'none';
        const wrap = document.querySelector('.slides-wrap');
        if (wrap) wrap.style.transform = 'scale(1)';
    """)
    await asyncio.sleep(0.1)

    # 애니메이션 트리거
    trigger = ANIM_TRIGGERS.get(sid, "")
    if trigger:
        await page.evaluate(trigger)

    # 나레이션 길이만큼 녹화
    await asyncio.sleep(dur)

    await context.close()
    await browser.close()

    # webm 파일 찾아서 mp4 변환
    webm_files = list(tmp_dir.glob("*.webm"))
    if not webm_files:
        print(f"  ❌ {sid} webm 생성 실패")
        return None

    webm = webm_files[0]
    out_mp4 = OUT_DIR / f"{sid}.mp4"

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(webm),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-vf", f"scale={WIDTH}:{HEIGHT},format=yuv420p,fade=t=in:st=0:d=0.5:color=white",
        str(out_mp4)
    ], capture_output=True)

    shutil.rmtree(tmp_dir)
    print(f"  ✅ {sid} ({dur:.1f}s) → {out_mp4.name}")
    return out_mp4

async def main():
    print(f"\n🎨 HTML 애니메이션 녹화 시작\n")

    async with async_playwright() as p:
        for sid in SCENE_IDS:
            slide_n = SLIDE_NUM[sid]
            dur = narr_duration(sid)
            # 씬마다 브라우저 새로 시작 (녹화 컨텍스트 독립)
            browser = await p.chromium.launch()
            await record_scene(browser, sid, slide_n, dur)

    print(f"\n✅ 완료 → {OUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
