#!/usr/bin/env python3
"""
SIGNAL — 기업분석 시리즈 전체 자동 파이프라인
매일 새벽 3시 (launchd 트리거)

CC 스텝(context/script/HTML/blog)도 claude -p 로 자동 처리.

Steps:
  1  context.json 생성       → claude -p (기업 리서치 + DB 메타)
  2  script.json 생성         → claude -p (7씬 × 3언어 나레이션)
  3  HTML 슬라이드 생성        → claude -p (ep_ko/ja/en.html)
  4  03_generate_narration.py → narration/{lang}/*.mp3
  5  04_render_html.py        → scenes/{lang}/*.mp4
  6  05_assemble.py           → final/ep{N}_final_{lang}.mp4
  7  06_generate_shorts.py    → final/ep{N}_shorts_{lang}.mp4
  8  07_upload_youtube.py     → YouTube Private 업로드
  9  blog HTML 생성           → claude -p (blog_ko/ja/en.html + meta)
  10 publish_draft.py         → Blogger Draft 발행

완료 후 macOS 알림: "SIGNAL EP{N} 완료 — YouTube Studio에서 Public 전환 필요"

수동 실행:
    python3 scheduler/signal_pipeline.py
    python3 scheduler/signal_pipeline.py --ep 4
    python3 scheduler/signal_pipeline.py --check
"""

from __future__ import annotations
import sys, subprocess, sqlite3, json, logging
from pathlib import Path
from datetime import datetime

ROOT     = Path(__file__).parent.parent
DB_PATH  = Path.home() / "Documents/Claude/blog.db"
PIPELINE = ROOT / "pipeline"
LOG_PATH = Path(__file__).parent / "signal_pipeline.log"
CLAUDE   = "/opt/homebrew/bin/claude"
SERIES   = "signal"

# ── 로깅 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── DB ────────────────────────────────────────────────
def get_next_ep() -> dict | None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT * FROM video_episodes
        WHERE series = ? AND status = 'planned'
        ORDER BY ep_number LIMIT 1
    """, (SERIES,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_ep(ep_number: int) -> dict | None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM video_episodes WHERE series=? AND ep_number=?",
        (SERIES, ep_number)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── 실행 헬퍼 ─────────────────────────────────────────
def run(cmd: list, cwd=None) -> subprocess.CompletedProcess:
    log.info(f"▶ {' '.join(str(c) for c in cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True,
                       cwd=str(cwd or ROOT))
    for line in r.stdout.splitlines():
        log.info(f"  {line}")
    if r.returncode != 0:
        log.error(f"  stderr: {r.stderr[-300:]}")
        raise RuntimeError(f"실패 (exit {r.returncode}): {cmd[0]}")
    return r


def claude_run(prompt: str) -> subprocess.CompletedProcess:
    log.info(f"🤖 claude -p [{prompt[:80]}...]")
    r = subprocess.run(
        [CLAUDE, "-p", prompt, "--dangerously-skip-permissions"],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    for line in r.stdout.splitlines():
        log.info(f"  {line}")
    if r.returncode != 0:
        log.error(f"  claude stderr: {r.stderr[-300:]}")
        raise RuntimeError(f"claude -p 실패 (exit {r.returncode})")
    return r


def notify(title: str, body: str):
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{body}" with title "{title}"'],
            capture_output=True, timeout=5
        )
    except Exception:
        pass


# ── 스텝별 함수 ───────────────────────────────────────

def step1_context(N: int, ep: dict, out_dir: Path):
    """context.json 생성 — 기업 리서치 + DB 메타 통합"""
    log.info(f"\n{'─'*40}\nStep 1: context.json 생성 (Claude)\n{'─'*40}")
    context_path = out_dir / "context.json"
    if context_path.exists():
        log.info("  context.json 이미 존재 — 스킵")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    company  = ep.get("company", "")
    ep_role  = ep.get("ep_role", "ep1")
    title_ko = ep.get("title_ko", "")
    title_ja = ep.get("title_ja", "")
    title_en = ep.get("title_en", "")
    sector   = ep.get("sector", "")

    # 같은 회사 이전 에피소드 참조
    prev_refs = ""
    for prev_n in [N-3, N-2, N-1]:
        if prev_n >= 1:
            prev_ctx = ROOT / SERIES / f"ep{prev_n:02d}" / "context.json"
            if prev_ctx.exists():
                prev_refs += f"\nPrevious EP{prev_n:02d} context: {prev_ctx}"

    prompt = f"""Create context.json for SIGNAL series EP{N:02d}.

Episode metadata:
- ep_number: {N}
- company: {company}
- sector: {sector}
- ep_role: {ep_role}  (ep1=overview, ep2=bear scenarios, ep3=domination+verdict, compare=multi-company)
- title_ko: {title_ko}
- title_ja: {title_ja}
- title_en: {title_en}
{prev_refs}

OUTPUT: {context_path}

TASK:
1. Research {company} thoroughly using your knowledge (latest financials, products, competitive position)
2. If ep_role is 'compare': research all companies mentioned in title_ko
3. Structure the context.json with:
   - "ep": episode metadata (copy from above)
   - "obsidian_notes": comprehensive markdown with company overview, financials, products, moat, PROS/CONS, scenarios
   - "scene_structure": array matching the ep_role pattern below
   - "series_config": {{blogs: {{ko: "aitrendlog", ja: "dx-pioneer-jp", en: "dx-pioneer-en"}}, langs: ["ko","ja","en"]}}

Scene structure by ep_role:
- ep1: [s01_hook, s02_overview, s03_what_they_do, s04_moat, s05_pros, s06_cons, s07_verdict]
- ep2: [s01_hook, s02_setup, s03_bear_1, s04_bear_23, s05_bull_1, s06_bull_23, s07_verdict]
- ep3: [s01_hook, s02_scurve, s03_signal_bear, s04_signal_bull, s05_my_life, s06_verdict, s07_cta]
- compare: [s01_hook, s02_overview, s03_tech_compare, s04_revenue_compare, s05_risk_compare, s06_scurve_compare, s07_verdict]

Write context.json now."""

    claude_run(prompt)


def step2_script(N: int, out_dir: Path):
    """script.json 생성 — 7씬 × 3언어"""
    log.info(f"\n{'─'*40}\nStep 2: script.json 생성 (Claude)\n{'─'*40}")
    context = out_dir / "context.json"
    script  = out_dir / "script.json"

    # 같은 ep_role 참조 찾기
    ref1 = ROOT / "signal/ep01/script.json"
    ref2 = ROOT / "signal/ep02/script.json"
    ref3 = ROOT / "signal/ep03/script.json"

    prompt = f"""Create script.json for SIGNAL series EP{N:02d}.

TASK: Read the context file and write a complete script.json with 7 scenes × 3 languages.

Context: {context}
Reference scripts: {ref1}, {ref2}, {ref3}
Output: {script}

RULES:
- Root fields: series("signal"), ep_number, ep_role, company, title_ko, title_ja, title_en, color_system, scenes
- Exactly 7 scenes — IDs depend on ep_role (from context.json scene_structure)
- Each scene: id, role, tone (sage/cream/slate), bg, accent, visual_note, narration, narration_ja, narration_en

3-Tone color system:
  Sage:  bg=#e4ece1 accent=#4d7a5a  (fresh analysis, hook, moat, bull)
  Cream: bg=#faf7f0 accent=#8a5a1e  (warm data, overview, pros, verdict/cta)
  Slate: bg=#edf1f8 accent=#2c4c7e  (cold risk, bear, cons)

Tone assignment by ep_role:
  ep1:     s01=Sage, s02=Cream, s03=Slate, s04=Sage, s05=Cream, s06=Slate, s07=Cream
  ep2:     s01=Sage, s02=Cream, s03=Slate, s04=Slate, s05=Sage, s06=Cream, s07=Cream
  ep3:     s01=Sage, s02=Cream, s03=Slate, s04=Sage, s05=Cream, s06=Slate, s07=Cream
  compare: s01=Sage, s02=Cream, s03=Slate, s04=Cream, s05=Slate, s06=Sage, s07=Cream

Narration:
- KO: natural spoken Korean, 100-220 chars/scene (15-35 seconds)
- JA: natural Japanese
- EN: natural English (slightly longer)

Write script.json now."""

    claude_run(prompt)


def step3_html(N: int, out_dir: Path):
    """HTML 슬라이드 3언어 생성"""
    log.info(f"\n{'─'*40}\nStep 3: HTML 슬라이드 생성 (Claude)\n{'─'*40}")
    script  = out_dir / "script.json"
    html_dir = out_dir / "html"

    # 같은 ep_role 참조
    ref_ep1_ko = ROOT / "signal/ep01/html/ep01_ko.html"
    ref_ep2_ko = ROOT / "signal/ep02/html/ep02_ko.html"
    ref_ep3_ko = ROOT / "signal/ep03/html/ep03_ko.html"

    prompt = f"""Create 3 HTML slide files for SIGNAL EP{N:02d}.

TASK: Read the script and reference HTMLs, then create 3 complete HTML files.

Script: {script}
Reference KO (EP01 ep1): {ref_ep1_ko}
Reference KO (EP02 ep2): {ref_ep2_ko}
Reference KO (EP03 ep3): {ref_ep3_ko}

OUTPUT FILES (mkdir -p html/ first):
1. {html_dir}/ep{N:02d}_ko.html  (lang="ko", Noto Sans KR)
2. {html_dir}/ep{N:02d}_ja.html  (lang="ja", Noto Sans JP)
3. {html_dir}/ep{N:02d}_en.html  (lang="en", Inter)

CRITICAL RULES:
- body: width=1920px, height=1080px, overflow=hidden
- 7 slides: .slide.sage / .slide.cream / .slide.slate (match tones from script.json)
- MUST expose: window.goToSlide = showSlide; (Playwright depends on this)
- Animations: fadeUp/fadeIn/slideInLeft/slideInRight keyframes + .go class (added after 300ms delay)
- .slide-label top-left (Roboto Mono, 22px, #a09880), .slide-num top-right
- All slides start hidden: display:none → flex on activation
- 3-Tone: .sage{{bg:#e4ece1}} .cream{{bg:#faf7f0}} .slate{{bg:#edf1f8}}
- Choose the reference HTML matching ep_role from script.json for design pattern
- JA/EN: same CSS, only text and font differ

Write all 3 files now. Create the html/ directory first with Bash."""

    claude_run(prompt)


def step4to8_auto(N: int):
    """Steps 4–8: TTS → 렌더 → 합성 → Shorts → YouTube"""
    log.info(f"\n{'─'*40}\nSteps 4–8: 나레이션→렌더→합성→Shorts→업로드\n{'─'*40}")
    for lang in ["ko", "ja", "en"]:
        log.info(f"\n  [{lang.upper()}]")
        run(["python3", str(PIPELINE / "03_generate_narration.py"), str(N), "--series", SERIES, "--lang", lang])
        run(["python3", str(PIPELINE / "04_render_html.py"),        str(N), "--series", SERIES, "--lang", lang])
        run(["python3", str(PIPELINE / "05_assemble.py"),           str(N), "--series", SERIES, "--lang", lang])
        run(["python3", str(PIPELINE / "06_generate_shorts.py"),    str(N), "--series", SERIES, "--lang", lang])
        run(["python3", str(PIPELINE / "07_upload_youtube.py"),     str(N), lang,       "--series", SERIES])


def step9_blog(N: int, out_dir: Path):
    """블로그 HTML 3언어 생성"""
    log.info(f"\n{'─'*40}\nStep 9: 블로그 HTML 생성 (Claude)\n{'─'*40}")
    script   = out_dir / "script.json"
    upload   = out_dir / "upload_result.json"
    blog_dir = out_dir / "blog"

    ref_ko = ROOT / "signal/ep03/blog/blog_ko.html"
    ref_ja = ROOT / "signal/ep03/blog/blog_ja.html"
    ref_en = ROOT / "signal/ep03/blog/blog_en.html"

    prompt = f"""Create blog HTML posts for SIGNAL EP{N:02d}.

TASK: Read the script and upload results, write 6 blog files.

Script: {script}
Upload result (video IDs): {upload}
Reference KO: {ref_ko}
Reference JA: {ref_ja}
Reference EN: {ref_en}

OUTPUT FILES (mkdir -p blog/ first):
1. {blog_dir}/blog_ko.html — Korean (aitrendlog blog)
2. {blog_dir}/blog_ko_meta.json — {{"title": "[Korean title]", "lang": "ko", "series": "signal", "ep_number": {N}}}
3. {blog_dir}/blog_ja.html — Japanese (use KO video IDs — publish_draft.py auto-replaces)
4. {blog_dir}/blog_ja_meta.json — {{"title": "[Japanese title]", "lang": "ja", "series": "signal", "ep_number": {N}}}
5. {blog_dir}/blog_en.html — English (use KO video IDs — publish_draft.py auto-replaces)
6. {blog_dir}/blog_en_meta.json — {{"title": "[English title]", "lang": "en", "series": "signal", "ep_number": {N}}}

STRUCTURE (match reference EP03 blog):
- Series badge: 📡 SIGNAL — 기업분석 시리즈 EP{N:02d}
- YouTube embed (KO video_id from upload_result.json)
- Lead summary paragraph
- S-curve or company overview section
- Bear signals check (if ep2/ep3)
- Bull signals check (if ep2/ep3)
- PROS/CONS cards (if ep1)
- Real-life impact section (if ep3)
- Verdict section with WATCH/BUY/PASS call
- Next episode preview
- Dark box with next episode info

font-family: KO='Apple SD Gothic Neo','Noto Sans KR' / JA='Hiragino Kaku Gothic ProN','Noto Sans JP' / EN='Inter','Helvetica Neue'

Write all 6 files now."""

    claude_run(prompt)


def step10_publish(N: int):
    """Blogger Draft 발행"""
    log.info(f"\nStep 10: Blogger Draft 발행\n")
    run(["python3", str(PIPELINE / "publish_draft.py"), str(N), "--series", SERIES])


# ── 메인 ─────────────────────────────────────────────
def main():
    check_only = "--check" in sys.argv
    force_ep   = None
    for i, a in enumerate(sys.argv):
        if a == "--ep" and i + 1 < len(sys.argv):
            force_ep = int(sys.argv[i + 1])

    ep = get_ep(force_ep) if force_ep else get_next_ep()
    if not ep:
        log.info("✅ 모든 에피소드 완료 (planned 없음).")
        return

    N = ep["ep_number"]
    log.info(f"{'='*50}")
    log.info(f"SIGNAL EP{N:02d} — {ep.get('title_ko', '')} ({ep.get('ep_role', '')})")
    log.info(f"Company: {ep.get('company', '')} | Sector: {ep.get('sector', '')}")
    log.info(f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*50}")

    if check_only:
        print(f"\n다음 실행 예정: SIGNAL EP{N:02d} — {ep.get('title_ko', '')}")
        print(f"Company: {ep.get('company', '')} | ep_role: {ep.get('ep_role', '')}")
        return

    out_dir = ROOT / SERIES / f"ep{N:02d}"
    start   = datetime.now()

    try:
        step1_context(N, ep, out_dir)
        step2_script(N, out_dir)
        step3_html(N, out_dir)
        step4to8_auto(N)
        step9_blog(N, out_dir)
        step10_publish(N)

        elapsed = (datetime.now() - start).seconds // 60
        log.info(f"\n{'='*50}")
        log.info(f"✅ SIGNAL EP{N:02d} 완료! 소요: {elapsed}분")
        log.info(f"{'='*50}")

        notify(
            "SIGNAL EP 제작 완료",
            f"EP{N:02d} {ep.get('company', '')} — YouTube Studio에서 Public 전환 필요"
        )

    except Exception as e:
        log.error(f"\n❌ 파이프라인 실패: {e}")
        notify("SIGNAL 파이프라인 실패", f"EP{N:02d}: {str(e)[:80]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
