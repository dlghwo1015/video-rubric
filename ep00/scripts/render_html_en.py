#!/usr/bin/env python3
"""English HTML Animation → MP4 (Playwright recording)"""

import asyncio, subprocess, shutil
from pathlib import Path
from playwright.async_api import async_playwright

BASE     = Path(__file__).parent.parent
NARR     = BASE / "narration" / "en"
OUT_DIR  = BASE / "scenes" / "en"
OUT_DIR.mkdir(exist_ok=True)

URL      = "http://localhost:7890/ep00_visual_en.html"
WIDTH    = 1920
HEIGHT   = 1080

SCENE_IDS = ["s01_hook","s02_cpm","s03_rpm","s04_faceless","s05_ocean","s06_saturation","s07_outro"]
SLIDE_NUM = {sid: i+1 for i, sid in enumerate(SCENE_IDS)}

ANIM_TRIGGERS = {
    "s01_hook": """
        ['w1','w2','w3'].forEach((id,i) => {
            setTimeout(() => {
                const el = document.getElementById(id);
                if(el) el.classList.add('go');
            }, i * 500);
        });
        setTimeout(() => { const s = document.getElementById('s1-sub'); if(s) s.classList.add('go'); }, 1700);
        setTimeout(() => { const h = document.getElementById('s1-hl');  if(h) h.classList.add('go'); }, 2500);
    """,
    "s02_cpm": """
        const tl2 = document.getElementById('tl-2'); if(tl2) tl2.classList.add('go');
        setTimeout(() => { const tt = document.getElementById('tt-2'); if(tt) tt.classList.add('go'); }, 200);
        setTimeout(() => { const td = document.getElementById('td-2'); if(td) td.classList.add('go'); }, 1600);
        setTimeout(() => { const tc = document.getElementById('tc-2'); if(tc) tc.classList.add('go'); }, 2200);
        setTimeout(() => { const ch = document.getElementById('ch-2'); if(ch) ch.classList.add('go'); }, 400);
        setTimeout(() => {
            document.querySelectorAll('#bc-2 .bar-wrap').forEach((b,i) => {
                setTimeout(() => b.classList.add('go'), i * 150);
            });
        }, 800);
    """,
    "s03_rpm": """
        const rh = document.getElementById('rh-3'); if(rh) rh.classList.add('go');
        setTimeout(() => { const rc1 = document.getElementById('rc1-3'); if(rc1) rc1.classList.add('go'); }, 400);
        setTimeout(() => { const ra  = document.getElementById('ra-3');  if(ra)  ra.classList.add('go');  }, 700);
        setTimeout(() => { const rc2 = document.getElementById('rc2-3'); if(rc2) rc2.classList.add('go'); }, 600);
        setTimeout(() => { const rn  = document.getElementById('rn-3');  if(rn)  rn.classList.add('go');  }, 1400);
    """,
    "s04_faceless": """
        const ft4 = document.getElementById('ft-4'); if(ft4) ft4.classList.add('go');
        setTimeout(() => { const fn4 = document.getElementById('fn-4'); if(fn4) fn4.classList.add('go'); }, 200);
        setTimeout(() => { const fd4 = document.getElementById('fd-4'); if(fd4) fd4.classList.add('go'); }, 600);
        ['fc1-4','fc2-4','fc3-4','fc4-4'].forEach((id,i) => {
            setTimeout(() => { const c = document.getElementById(id); if(c) c.classList.add('go'); }, 400 + i * 200);
        });
    """,
    "s05_ocean": """
        const oh5 = document.getElementById('oh-5'); if(oh5) oh5.classList.add('go');
        setTimeout(() => { const oc1 = document.getElementById('oc1-5'); if(oc1) oc1.classList.add('go'); }, 300);
        setTimeout(() => { const oc2 = document.getElementById('oc2-5'); if(oc2) oc2.classList.add('go'); }, 500);
        setTimeout(() => { const on5 = document.getElementById('on-5');  if(on5) on5.classList.add('go'); }, 1500);
    """,
    "s06_saturation": """
        const sgt = document.getElementById('sg-tag');   if(sgt) sgt.classList.add('go');
        setTimeout(() => { const sgi = document.getElementById('sg-title'); if(sgi) sgi.classList.add('go'); }, 200);
        setTimeout(() => { const sgb = document.getElementById('sg-body');  if(sgb) sgb.classList.add('go'); }, 600);
        setTimeout(() => {
            document.querySelectorAll('.draw-line').forEach((l,i) => { setTimeout(() => l.classList.add('go'), i * 200); });
            setTimeout(() => {
                document.querySelectorAll('.dot-ap').forEach((d,i) => { setTimeout(() => d.classList.add('go'), i * 150); });
            }, 2200);
        }, 500);
    """,
    "s07_outro": """
        const oh7 = document.getElementById('oh-7'); if(oh7) oh7.classList.add('go');
        ['sc1-7','sc2-7','sc3-7','sc4-7','sc5-7','sc6-7'].forEach((id,i) => {
            setTimeout(() => { const c = document.getElementById(id); if(c) c.classList.add('go'); }, 200 + i * 150);
        });
        setTimeout(() => { const oc = document.getElementById('oc-7'); if(oc) oc.classList.add('go'); }, 1800);
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

    context = await browser.new_context(
        viewport={"width": WIDTH, "height": HEIGHT},
        record_video_dir=str(tmp_dir),
        record_video_size={"width": WIDTH, "height": HEIGHT},
    )
    page = await context.new_page()
    await page.goto(URL, wait_until="networkidle")
    await asyncio.sleep(0.3)

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
    """)
    await asyncio.sleep(0.1)

    trigger = ANIM_TRIGGERS.get(sid, "")
    if trigger:
        await page.evaluate(trigger)

    await asyncio.sleep(dur)
    await context.close()
    await browser.close()

    webm_files = list(tmp_dir.glob("*.webm"))
    if not webm_files:
        print(f"  ❌ {sid} webm generation failed")
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
    print(f"\n🎨 English HTML Animation Recording Start\n")
    async with async_playwright() as p:
        for sid in SCENE_IDS:
            slide_n = SLIDE_NUM[sid]
            dur = narr_duration(sid)
            browser = await p.chromium.launch()
            await record_scene(browser, sid, slide_n, dur)
    print(f"\n✅ Done → {OUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
