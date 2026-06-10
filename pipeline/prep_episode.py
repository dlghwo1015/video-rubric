#!/usr/bin/env python3
"""
prep_episode.py — context.json 생성 (worldcup-2026 & other series)

Usage:
    python3 pipeline/prep_episode.py 1 --series worldcup-2026
"""
from __future__ import annotations
import sys, json, sqlite3, argparse
from pathlib import Path
from datetime import datetime

ROOT    = Path(__file__).parent.parent
DB_PATH = Path.home() / "Documents/Claude/blog.db"

SERIES_CONFIGS = {
    "worldcup-2026": {
        "name": "2026 월드컵 예측 대결",
        "tagline": "역사상 가장 큰 월드컵을 예측하다",
        "blogs": {"ko": "honest-lab", "ja": "dx-pioneer-jp", "en": "dx-pioneer-en"},
        "youtube_channel": "honest-lab",
        "langs": ["ko", "ja", "en"],
        "tts": {
            "ko": "ko-KR-SunHiNeural",
            "ja": "ja-JP-NanamiNeural",
            "en": "en-US-AriaNeural",
        },
        "scene_structures": {
            "overview": [
                {"id": "s01_hook",     "role": "hook",     "desc": "훅 — 역사상 가장 큰 월드컵"},
                {"id": "s02_format",   "role": "data",     "desc": "48팀·12조 포맷 설명"},
                {"id": "s03_hosts",    "role": "analysis", "desc": "개최지 USA/Canada/Mexico"},
                {"id": "s04_schedule", "role": "analysis", "desc": "일정 + 주요 경기장"},
                {"id": "s05_teams",    "role": "analysis", "desc": "주요 참가국 & 아시아"},
                {"id": "s06_stories",  "role": "analysis", "desc": "빅 스토리 & 관전 포인트"},
                {"id": "s07_verdict",  "role": "verdict",  "desc": "최종 결론 + 다음 EP 예고"},
            ],
            "group_preview": [
                {"id": "s01_hook",     "role": "hook",     "desc": "훅 — 이 조의 핵심"},
                {"id": "s02_teams",    "role": "data",     "desc": "4개 팀 소개"},
                {"id": "s03_team1",    "role": "analysis", "desc": "1번 시드 분석"},
                {"id": "s04_team2",    "role": "analysis", "desc": "2번 팀 분석"},
                {"id": "s05_team3",    "role": "analysis", "desc": "3번 팀 분석"},
                {"id": "s06_predict",  "role": "analysis", "desc": "예측 + 변수"},
                {"id": "s07_verdict",  "role": "verdict",  "desc": "통과 예상 2팀 발표"},
            ],
            "analysis": [
                {"id": "s01_hook",     "role": "hook",     "desc": "훅"},
                {"id": "s02_overview", "role": "data",     "desc": "분석 개요"},
                {"id": "s03_point1",   "role": "analysis", "desc": "핵심 포인트 1"},
                {"id": "s04_point2",   "role": "analysis", "desc": "핵심 포인트 2"},
                {"id": "s05_point3",   "role": "analysis", "desc": "핵심 포인트 3"},
                {"id": "s06_risk",     "role": "analysis", "desc": "리스크 & 변수"},
                {"id": "s07_verdict",  "role": "verdict",  "desc": "최종 결론"},
            ],
            "special": [
                {"id": "s01_hook",     "role": "hook",     "desc": "훅 — 레전드의 대결"},
                {"id": "s02_careers",  "role": "data",     "desc": "커리어 개요 비교"},
                {"id": "s03_wc_stats", "role": "analysis", "desc": "월드컵 통계 비교"},
                {"id": "s04_moments",  "role": "analysis", "desc": "명장면 비교"},
                {"id": "s05_legacy",   "role": "analysis", "desc": "레거시 & 2026"},
                {"id": "s06_debate",   "role": "analysis", "desc": "GOAT 논쟁"},
                {"id": "s07_verdict",  "role": "verdict",  "desc": "최종 결론"},
            ],
        },
        "research_guides": {
            "overview": "48-team format, 12 groups, host cities (USA/Canada/Mexico), schedule, Asia/Africa expansion, key storylines",
            "group_preview": "FIFA rankings, recent form, key players for all 4 teams in the group, head-to-head history",
            "analysis": "contenders, dark horses, Messi/Ronaldo last WC, Korea squad",
            "special": "Messi vs Ronaldo career WC stats comparison",
        },
    }
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ep_number", type=int)
    parser.add_argument("--series", required=True)
    args = parser.parse_args()

    N      = args.ep_number
    series = args.series

    if series not in SERIES_CONFIGS:
        print(f"Unknown series: {series}", file=sys.stderr)
        sys.exit(1)

    config = SERIES_CONFIGS[series]

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM video_episodes WHERE series=? AND ep_number=?",
        (series, N)
    ).fetchone()
    conn.close()

    if not row:
        print(f"EP{N:02d} not found in {series}", file=sys.stderr)
        sys.exit(1)

    ep = dict(row)
    ep_role = ep.get("ep_role", "overview")

    scene_structure = config["scene_structures"].get(ep_role, config["scene_structures"]["overview"])
    research_guide  = config["research_guides"].get(ep_role, "")
    needs_live_data = bool(ep.get("needs_live_data", 0))

    ctx = {
        "series": series,
        "series_config": {
            "name": config["name"],
            "tagline": config["tagline"],
            "blogs": config["blogs"],
            "youtube_channel": config["youtube_channel"],
            "langs": config["langs"],
            "tts": config["tts"],
        },
        "ep": ep,
        "ep_role": ep_role,
        "scene_structure": scene_structure,
        "research_guide": research_guide,
        "needs_live_data": needs_live_data,
        "pub_date": ep.get("pub_date"),
        "blogs": config["blogs"],
        "langs": config["langs"],
        "tts": config["tts"],
    }

    out_dir = ROOT / series / f"ep{N:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx_path = out_dir / "context.json"
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2))
    print(f"context.json → {ctx_path}")
    print(f"ep_role: {ep_role}")
    print(f"needs_live_data: {needs_live_data}")


if __name__ == "__main__":
    main()
