#!/usr/bin/env python3
"""
블로그 Draft 발행 (Claude Code용)
{series}/ep{NN}/blog/blog_ko.html + blog_ja.html + blog_en.html → Blogger API

Claude Code가 blog/blog_*.html 을 직접 생성한 뒤 이 스크립트로 발행한다.

사용법:
    python3 pipeline/publish_draft.py 1
    python3 pipeline/publish_draft.py 1 --ko-only
    python3 pipeline/publish_draft.py 1 --series kanzen-japan
"""

import sys, json, os, sqlite3, urllib.request, urllib.parse, argparse
from pathlib import Path
from datetime import datetime

ROOT    = Path(__file__).parent.parent
DB_PATH = Path.home() / "Documents/Claude/blog.db"

BLOG_SLUGS = {"ko": "honest-lab", "ja": "youtube-rubric-jp", "en": "youtube-rubric-en"}
BLOG_LABELS = {
    "ko": ["유튜브수익", "CPM", "유튜브루브릭"],
    "ja": ["YouTube収益", "CPM", "YouTubeルーブリック"],
    "en": ["YouTube Revenue", "CPM", "YouTube Rubric"],
}

# 시리즈별 블로그 slug / labels 오버라이드
SERIES_BLOG_SLUGS = {
    "signal": {"ko": "aitrendlog", "ja": "dx-pioneer-jp", "en": "dx-pioneer-en"},
}
SERIES_BLOG_LABELS = {
    "signal": {
        "ko": ["기업분석", "주식분석", "SIGNAL", "팔란티어"],
        "ja": ["企業分析", "株式分析", "SIGNAL", "パランティア"],
        "en": ["CompanyAnalysis", "StockAnalysis", "SIGNAL", "Palantir"],
    }
}


def get_blog_slugs(series: str) -> dict:
    return SERIES_BLOG_SLUGS.get(series, BLOG_SLUGS)


def get_blog_labels(series: str) -> dict:
    return SERIES_BLOG_LABELS.get(series, BLOG_LABELS)


def load_blogger_token():
    for p in [
        Path.home() / "Documents/Claude/teamkintai/apps/blog-manager/.env.local",
        Path.home() / "Documents/Claude/.env",
    ]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("BLOGGER_REFRESH_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"')
    raise EnvironmentError("BLOGGER_REFRESH_TOKEN 없음")


def get_access_token(refresh_token: str) -> str:
    client_id = client_secret = ""
    for p in [Path.home() / "Documents/Claude/teamkintai/apps/blog-manager/.env.local"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("GOOGLE_CLIENT_ID=") or line.startswith("BLOGGER_CLIENT_ID="):
                    client_id = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("GOOGLE_CLIENT_SECRET=") or line.startswith("BLOGGER_CLIENT_SECRET="):
                    client_secret = line.split("=", 1)[1].strip().strip('"')
    data = urllib.parse.urlencode({
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def get_video_ids(series: str, ep_number: int) -> dict:
    """video_episodes에서 언어별 YouTube ID 조회"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT youtube_video_id, youtube_shorts_id,
               youtube_video_id_ja, youtube_shorts_id_ja,
               youtube_video_id_en, youtube_shorts_id_en
        FROM video_episodes WHERE series=? AND ep_number=?
    """, (series, ep_number)).fetchone()
    conn.close()
    if not row:
        return {}
    return {
        "ko": {"main": row[0], "shorts": row[1]},
        "ja": {"main": row[2], "shorts": row[3]},
        "en": {"main": row[4], "shorts": row[5]},
    }


def fix_video_ids(content: str, lang: str, video_ids: dict) -> str:
    """콘텐츠 내 KO 영상 ID를 해당 언어 ID로 교체"""
    if lang == "ko" or not video_ids:
        return content

    ko = video_ids.get("ko", {})
    target = video_ids.get(lang, {})

    # 본편 교체
    ko_main = ko.get("main")
    tgt_main = target.get("main")
    if ko_main and tgt_main and ko_main != tgt_main:
        content = content.replace(ko_main, tgt_main)

    # Shorts 교체
    ko_shorts = ko.get("shorts")
    tgt_shorts = target.get("shorts")
    if ko_shorts and tgt_shorts and ko_shorts != tgt_shorts:
        content = content.replace(ko_shorts, tgt_shorts)

    return content


def get_blogger_id(slug: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT blogger_id FROM blogs WHERE id=?", (slug,)).fetchone()
    conn.close()
    if not row or not row[0]:
        raise ValueError(f"blogger_id 없음: {slug}")
    return row[0]


def save_post_id(ep_number: int, lang: str, post_id: str, series: str = "youtube-rubric"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        f"UPDATE video_episodes SET post_id_{lang}=? WHERE series=? AND ep_number=?",
        (post_id, series, ep_number)
    )
    conn.commit()
    conn.close()


def create_draft(blogger_id: str, access_token: str, title: str,
                 content: str, labels: list) -> str:
    body = json.dumps({
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": labels,
        "status": "DRAFT",
    }).encode("utf-8")
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blogger_id}/posts/?isDraft=true"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["id"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("ep_number", type=int)
    parser.add_argument("--series", default="youtube-rubric")
    parser.add_argument("--lang", default="ko", choices=["ko", "ja", "en"])
    parser.add_argument("--ko-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    ep_number = args.ep_number
    series    = args.series
    ko_only   = args.ko_only
    langs     = ["ko"] if ko_only else ["ko", "ja", "en"]

    ep_dir   = ROOT / series / f"ep{ep_number:02d}"
    blog_dir = ep_dir / "blog"

    print(f"\n[publish] {series}/EP{ep_number:02d} 블로그 Draft 발행\n")

    refresh_token = load_blogger_token()
    access_token  = get_access_token(refresh_token)
    video_ids     = get_video_ids(series, ep_number)

    for lang in langs:
        # blog/blog_{lang}.html
        blog_file = blog_dir / f"blog_{lang}.html"
        meta_file = blog_dir / f"blog_{lang}_meta.json"

        if not blog_file.exists():
            print(f"  [{lang}] ⚠️  blog_{lang}.html 없음 — 스킵")
            continue

        content = blog_file.read_text(encoding="utf-8")

        # 언어별 YouTube ID 자동 치환 (KO → JA/EN)
        content = fix_video_ids(content, lang, video_ids)
        replaced = []
        if lang != "ko" and video_ids:
            ko = video_ids.get("ko", {})
            tgt = video_ids.get(lang, {})
            if ko.get("main") and tgt.get("main") and ko["main"] != tgt["main"]:
                replaced.append(f"본편 {ko['main']}→{tgt['main']}")
            if ko.get("shorts") and tgt.get("shorts") and ko["shorts"] != tgt["shorts"]:
                replaced.append(f"Shorts {ko['shorts']}→{tgt['shorts']}")
        if replaced:
            print(f"  [{lang}] 🔄 영상 ID 치환: {', '.join(replaced)}")

        # 제목은 meta 파일 또는 첫 줄 h1에서 추출
        title = ""
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            title = meta.get("title", "")
        if not title:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else f"EP{ep_number:02d}"

        slug   = get_blog_slugs(series)[lang]
        labels = get_blog_labels(series)[lang]

        try:
            blogger_id = get_blogger_id(slug)
            post_id    = create_draft(blogger_id, access_token, title, content, labels)
            save_post_id(ep_number, lang, post_id, series)
            print(f"  [{lang}] ✅ {title[:40]} → post_id: {post_id}")
        except Exception as e:
            print(f"  [{lang}] ❌ 실패: {e}")

    print(f"\n[publish] ✅ 완료 → Blog Manager에서 리뷰 후 발행")


if __name__ == "__main__":
    main()
