#!/usr/bin/env python3
"""
유튜브 수익 루브릭 — YouTube 업로드 (3개 언어 지원)
ep{NN}_final_{lang}.mp4 → YouTube 본 영상 (언어별 플레이리스트 자동 배정)
ep{NN}_shorts_{lang}.mp4 → YouTube Shorts

언어 파라미터:
    python3 07_upload_youtube.py 1 ko          # 한국어
    python3 07_upload_youtube.py 1 ja          # 일본어
    python3 07_upload_youtube.py 1 en          # 영어
    python3 07_upload_youtube.py 1 ko --dry-run

OAuth: ~/Documents/Claude/.google_token.pickle
플레이리스트 ID: ~/Documents/Claude/Projects/video-rubric/config/playlists.json (자동 생성)
"""
from __future__ import annotations

import sys, json, os, sqlite3, pickle, argparse
from pathlib import Path
from datetime import datetime

ROOT       = Path(__file__).parent.parent
DB_PATH    = Path.home() / "Documents/Claude/blog.db"
PLAYLIST_CONFIG = ROOT / "config" / "playlists.json"  # youtube-rubric 기본값


def get_playlist_config_path(series: str) -> Path:
    """시리즈별 플레이리스트 config 경로 반환"""
    if series == "youtube-rubric":
        return ROOT / "config" / "playlists.json"
    return ROOT / "config" / f"playlists_{series}.json"

# 토큰 탐색 순서 (pickle / json 모두 지원)
TOKEN_CANDIDATES = [
    Path.home() / "Documents/Claude/.google_token.pickle",
    Path.home() / "Documents/Claude/.google_token.json",
    Path.home() / "Documents/vlog-editor/token_youtube.json",
    ROOT / "config" / "youtube_token.json",
]

# 플레이리스트 관리 + 업로드 둘 다 필요
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
]

LANG_META = {
    "ko": {
        "label":    "한국어",
        "yt_lang":  "ko",
        "playlist_main":   "유튜브 수익 루브릭 — 한국어",
        "playlist_shorts": "유튜브 수익 루브릭 Shorts — 한국어",
        "hashtag":  "#유튜브수익 #유튜브CPM #유튜브루브릭",
    },
    "ja": {
        "label":    "日本語",
        "yt_lang":  "ja",
        "playlist_main":   "YouTubeルーブリック — 日本語",
        "playlist_shorts": "YouTubeルーブリック Shorts — 日本語",
        "hashtag":  "#YouTube収益 #YouTubeCPM #YouTubeルーブリック",
    },
    "en": {
        "label":    "English",
        "yt_lang":  "en",
        "playlist_main":   "YouTube Rubric — English",
        "playlist_shorts": "YouTube Rubric Shorts — English",
        "hashtag":  "#YouTubeRevenue #YouTubeCPM #YouTubeRubric",
    },
}

# SIGNAL 시리즈 전용 플레이리스트 메타 (시리즈별 오버라이드 테이블)
SERIES_LANG_META_OVERRIDE = {
    "signal": {
        "ko": {
            "playlist_main":   "SIGNAL — 기업분석 시리즈 KO",
            "playlist_shorts": "SIGNAL Shorts — 기업분석 시리즈 KO",
            "hashtag":  "#기업분석 #주식분석 #팔란티어",
        },
        "ja": {
            "playlist_main":   "SIGNAL — 企業分析シリーズ JA",
            "playlist_shorts": "SIGNAL Shorts — 企業分析シリーズ JA",
            "hashtag":  "#企業分析 #株式分析 #パランティア",
        },
        "en": {
            "playlist_main":   "SIGNAL — Company Analysis Series EN",
            "playlist_shorts": "SIGNAL Shorts — Company Analysis EN",
            "hashtag":  "#CompanyAnalysis #StockAnalysis #Palantir",
        },
    }
}


def get_lang_meta(lang: str, series: str) -> dict:
    """시리즈별 LANG_META (오버라이드 있으면 merge)"""
    base = dict(LANG_META[lang])
    override = SERIES_LANG_META_OVERRIDE.get(series, {}).get(lang, {})
    base.update(override)
    return base


CATEGORY_MAP = {
    "B-1": "22",   # People & Blogs
    "B-2": "28",   # Science & Technology
    "B-3": "22",
    "B-4": "20",   # Gaming
    "B-5": "22",
    "B-6": "25",   # News & Politics
    "B-7": "20",
    "B-8": "26",   # Howto & Style
    "intro": "22",
    "final": "22",
}


# ── 자격증명 ────────────────────────────────────────────────────────────────

STANDARD_TOKEN = Path.home() / "Documents/Claude/.google_token.json"

def _load_token_from_path(path: Path):
    """pickle / json 두 형식 모두 로드"""
    from google.oauth2.credentials import Credentials

    if path.suffix == ".pickle":
        with open(path, "rb") as f:
            return pickle.load(f)
    else:
        import json as _json
        d = _json.loads(path.read_text())
        return Credentials(
            token         = d.get("token"),
            refresh_token = d.get("refresh_token"),
            token_uri     = d.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id     = d.get("client_id"),
            client_secret = d.get("client_secret"),
            scopes        = d.get("scopes"),
        )

def _save_token(creds) -> None:
    """표준 경로(JSON)에 토큰 저장 — 다음 실행부터 이 파일 우선 사용"""
    import json as _json
    STANDARD_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes or []),
    }
    STANDARD_TOKEN.write_text(_json.dumps(data, indent=2))

def get_credentials():
    from google.auth.transport.requests import Request

    # 1) 토큰 파일 탐색
    creds = None
    found_path = None
    for candidate in TOKEN_CANDIDATES:
        if candidate.exists():
            try:
                creds = _load_token_from_path(candidate)
                found_path = candidate
                print(f"  🔑 토큰 로드: {candidate}")
                break
            except Exception as e:
                print(f"  ⚠️  {candidate} 로드 실패: {e}")

    if creds is None:
        _run_oauth_flow()
        creds = _load_token_from_path(STANDARD_TOKEN)
        found_path = STANDARD_TOKEN

    # 2) 만료 시 refresh
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("  🔄 토큰 갱신 중...")
            creds.refresh(Request())
            _save_token(creds)
            print(f"  ✅ 갱신 완료 → {STANDARD_TOKEN}")
        else:
            # refresh_token도 없으면 재인증
            _run_oauth_flow()
            creds = _load_token_from_path(STANDARD_TOKEN)

    # 3) 플레이리스트 스코프 없으면 재인증
    needed = set(SCOPES)
    have   = set(creds.scopes or [])
    if not needed.issubset(have):
        print(f"  ⚠️  스코프 부족: {needed - have}")
        print("  → 재인증으로 스코프 확장합니다...")
        _run_oauth_flow()
        creds = _load_token_from_path(STANDARD_TOKEN)

    return creds


def _run_oauth_flow():
    """브라우저로 OAuth 인증 — client_id/secret은 기존 토큰에서 추출"""
    from google_auth_oauthlib.flow import InstalledAppFlow
    import json as _json

    # 기존 토큰에서 client 정보 추출
    client_config = None
    for candidate in TOKEN_CANDIDATES:
        if candidate.exists() and candidate.suffix == ".json":
            try:
                d = _json.loads(candidate.read_text())
                if d.get("client_id") and d.get("client_secret"):
                    client_config = {
                        "installed": {
                            "client_id":     d["client_id"],
                            "client_secret": d["client_secret"],
                            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                            "token_uri":     d.get("token_uri", "https://oauth2.googleapis.com/token"),
                            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                        }
                    }
                    break
            except Exception:
                pass

    if not client_config:
        raise RuntimeError(
            "client_id/secret을 찾을 수 없습니다.\n"
            f"다음 중 하나에 JSON 토큰을 놓으세요:\n"
            + "\n".join(f"  {p}" for p in TOKEN_CANDIDATES if p.suffix == ".json")
        )

    print("\n  🌐 브라우저가 열립니다. Google 계정으로 로그인 후 권한을 허용하세요...")
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    _save_token(creds)
    print(f"  ✅ 인증 완료 → {STANDARD_TOKEN}")


# ── DB ──────────────────────────────────────────────────────────────────────

def get_episode(ep_number: int, series: str = "youtube-rubric") -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM video_episodes WHERE series=? AND ep_number=?",
        (series, ep_number)
    ).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"EP{ep_number:02d} (series={series}) DB에 없음")
    return dict(row)


def update_video_ids(ep_number: int, lang: str, video_id: str | None, shorts_id: str | None,
                     shorts_only: bool = False, series: str = "youtube-rubric"):
    """DB에 언어별 video_id 저장 — 전 언어 DB에 기록"""
    conn = sqlite3.connect(DB_PATH)
    if lang == "ko":
        vid_col    = "youtube_video_id"
        shorts_col = "youtube_shorts_id"
    else:
        vid_col    = f"youtube_video_id_{lang}"
        shorts_col = f"youtube_shorts_id_{lang}"

    if shorts_only and shorts_id:
        conn.execute(
            f"UPDATE video_episodes SET {shorts_col}=? "
            "WHERE series=? AND ep_number=?",
            (shorts_id, series, ep_number)
        )
    elif video_id and shorts_id:
        conn.execute(
            f"UPDATE video_episodes SET {vid_col}=?, {shorts_col}=? "
            "WHERE series=? AND ep_number=?",
            (video_id, shorts_id, series, ep_number)
        )
    elif video_id:
        conn.execute(
            f"UPDATE video_episodes SET {vid_col}=? "
            "WHERE series=? AND ep_number=?",
            (video_id, series, ep_number)
        )
    conn.commit()
    conn.close()


# ── 플레이리스트 관리 ────────────────────────────────────────────────────────

def load_playlist_config(series: str = "youtube-rubric") -> dict:
    """시리즈별 playlists config 로드 (없으면 빈 dict, TBD 값 제거)"""
    cfg_path = get_playlist_config_path(series)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if cfg_path.exists():
        raw = json.loads(cfg_path.read_text())
        # TBD 값은 '없는 것'과 동일하게 처리
        return {k: v for k, v in raw.items() if v and v != "TBD" and not k.startswith("_")}
    return {}


def save_playlist_config(cfg: dict, series: str = "youtube-rubric"):
    cfg_path = get_playlist_config_path(series)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def get_or_create_playlist(youtube, lang: str, is_shorts: bool, cfg: dict,
                           series: str = "youtube-rubric") -> str:
    """
    플레이리스트 ID를 config에서 읽어오거나, 없으면 YouTube API로 생성 후 저장.
    key 예: 'ko_main', 'ko_shorts', 'ja_main', 'en_shorts'
    """
    key = f"{lang}_{'shorts' if is_shorts else 'main'}"
    if key in cfg:
        return cfg[key]

    meta  = get_lang_meta(lang, series)
    title = meta["playlist_shorts"] if is_shorts else meta["playlist_main"]
    series_label = {
        "signal": "SIGNAL 기업분석 시리즈",
        "kanzen-japan": "kanzen-japan 시리즈",
    }.get(series, "유튜브 수익 루브릭 시리즈")

    print(f"  📋 플레이리스트 없음 → 신규 생성: {title}")
    res = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": f"{series_label} — {meta['label']}",
                "defaultLanguage": meta["yt_lang"],
            },
            "status": {"privacyStatus": "public"},
        }
    ).execute()

    playlist_id = res["id"]
    cfg[key] = playlist_id
    save_playlist_config(cfg, series)
    print(f"  ✅ 플레이리스트 생성 → {playlist_id}")
    return playlist_id


def add_to_playlist(youtube, video_id: str, playlist_id: str):
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                }
            }
        }
    ).execute()


# ── 업로드 ───────────────────────────────────────────────────────────────────

def upload_video(youtube, video_path: Path, title: str, description: str,
                 tags: list, category_id: str, yt_lang: str,
                 is_shorts: bool = False) -> str:
    from googleapiclient.http import MediaFileUpload

    if is_shorts:
        title = f"{title} #Shorts"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
            "defaultLanguage": yt_lang,
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    print(f"  업로드 중: {video_path.name} ...")
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    {int(status.progress() * 100)}%", end="\r", flush=True)

    video_id = response["id"]
    print(f"  ✅ 업로드 완료 → https://youtu.be/{video_id}")
    return video_id


# ── 설명 빌더 ────────────────────────────────────────────────────────────────

DESCRIPTION_TEMPLATES = {
    "ko": """\
[유튜브 수익 루브릭] EP{ep_num:02d} — {title}

카테고리: {category} ({section})
CPM: {cpm_2025} → {cpm_2026}
RPM: {rpm_2026}
포화도: {sat_2025} → {sat_2026}
{faceless_line}
목차:
{toc}

---
유튜브 수익 루브릭은 2025 Q1 vs 2026 실측 데이터를 비교하며
카테고리별 CPM/RPM/포화도를 심층 분석하는 시리즈입니다.

{hashtag}""",
    "ja": """\
【YouTubeルーブリック】EP{ep_num:02d} — {title}

カテゴリー: {category} ({section})
CPM: {cpm_2025} → {cpm_2026}
RPM: {rpm_2026}
飽和度: {sat_2025} → {sat_2026}
{faceless_line}
目次:
{toc}

---
YouTubeルーブリックは2025Q1 vs 2026の実測データを比較し、
カテゴリー別のCPM/RPM/飽和度を徹底分析するシリーズです。

{hashtag}""",
    "en": """\
[YouTube Rubric] EP{ep_num:02d} — {title}

Category: {category} ({section})
CPM: {cpm_2025} → {cpm_2026}
RPM: {rpm_2026}
Saturation: {sat_2025} → {sat_2026}
{faceless_line}
Chapters:
{toc}

---
YouTube Rubric compares 2025 Q1 vs 2026 real data,
analyzing CPM/RPM/saturation depth for each category.

{hashtag}""",
}

FACELESS_LINE = {
    "ko": "🎤 얼굴 없이(Faceless) 제작 가능",
    "ja": "🎤 顔出し不要(Faceless)で制作可能",
    "en": "🎤 Faceless production possible",
}

TAGS_BASE = {
    "ko": ["유튜브수익", "유튜브CPM", "유튜브RPM", "유튜브수익화", "유튜브루브릭", "Faceless유튜브"],
    "ja": ["YouTube収益", "YouTubeCPM", "YouTubeRPM", "YouTubeルーブリック", "Faceless", "ユーチューブ収益化"],
    "en": ["YouTubeRevenue", "YouTubeCPM", "YouTubeRPM", "YouTubeRubric", "FacelessYouTube", "YouTubeMonetization"],
}

SHORTS_TAGS = {
    "ko": ["유튜브수익", "유튜브CPM", "유튜브쇼츠", "Shorts", "유튜브루브릭"],
    "ja": ["YouTube収益", "YouTubeCPM", "Shorts", "YouTubeルーブリック", "ショート"],
    "en": ["YouTubeRevenue", "YouTubeCPM", "Shorts", "YouTubeRubric", "YoutubeShorts"],
}


SIGNAL_ROLE_LABELS = {
    "hook":    {"ko": "🎯 Hook", "ja": "🎯 フック", "en": "🎯 Hook"},
    "data":    {"ko": "📊 기업 개요", "ja": "📊 企業概要", "en": "📊 Overview"},
    "analysis":{"ko": "💡 실체 분석", "ja": "💡 実体分析", "en": "💡 Deep Dive"},
    "pros":    {"ko": "✅ PROS", "ja": "✅ PROS", "en": "✅ PROS"},
    "cons":    {"ko": "❌ CONS", "ja": "❌ CONS", "en": "❌ CONS"},
    "verdict": {"ko": "⚖️ 결론", "ja": "⚖️ 結論", "en": "⚖️ Verdict"},
}

SIGNAL_DESC_TEMPLATE = {
    "ko": """\
【SIGNAL】EP{ep_num:02d} — {title}

기업: {company} | 섹터: {sector}

목차:
{toc}

---
SIGNAL은 글로벌 기업의 실체를 데이터와 시나리오로 분석하는 기업분석 시리즈입니다.

{hashtag}""",
    "ja": """\
【SIGNAL】EP{ep_num:02d} — {title}

企業: {company} | セクター: {sector}

目次:
{toc}

---
SIGNALはグローバル企業の実態をデータとシナリオで分析する企業分析シリーズです。

{hashtag}""",
    "en": """\
[SIGNAL] EP{ep_num:02d} — {title}

Company: {company} | Sector: {sector}

Chapters:
{toc}

---
SIGNAL is a company analysis series that examines global companies through data and scenario analysis.

{hashtag}""",
}


def build_signal_description(ep: dict, script: dict, lang: str) -> str:
    scenes = script.get("scenes", [])
    toc_lines = []
    cumulative = 0
    for s in scenes:
        mins, secs = divmod(int(cumulative), 60)
        role_label = SIGNAL_ROLE_LABELS.get(s.get("role", ""), {}).get(lang, s.get("id", ""))
        toc_lines.append(f"{mins:02d}:{secs:02d} {role_label}")
        cumulative += s.get("duration", 30)

    meta = get_lang_meta(lang, "signal")
    return SIGNAL_DESC_TEMPLATE[lang].format(
        ep_num=ep["ep_number"],
        title=ep.get(f"title_{lang}") or ep.get("title_ko", ""),
        company=ep.get("company", ""),
        sector=ep.get("sector", ""),
        toc="\n".join(toc_lines),
        hashtag=meta["hashtag"],
    )


def build_description(ep: dict, script: dict, lang: str, series: str = "youtube-rubric") -> str:
    if series == "signal":
        return build_signal_description(ep, script, lang)
    return _build_rubric_description(ep, script, lang)


def _build_rubric_description(ep: dict, script: dict, lang: str) -> str:
    scenes = script.get("scenes", [])
    toc_lines = []
    cumulative = 0
    for s in scenes:
        mins, secs = divmod(cumulative, 60)
        role_label = {
            "hook": {"ko": "🎯 도입", "ja": "🎯 導入", "en": "🎯 Hook"},
            "data": {"ko": "📊 데이터 비교", "ja": "📊 データ比較", "en": "📊 Data Comparison"},
            "channel_analysis": {"ko": "🔍 채널 분석", "ja": "🔍 チャンネル分析", "en": "🔍 Channel Analysis"},
            "analysis": {"ko": "💡 CPM이 높은 이유", "ja": "💡 CPMが高い理由", "en": "💡 Why High CPM"},
            "strategy": {"ko": "🗺 진입 전략", "ja": "🗺 参入戦略", "en": "🗺 Entry Strategy"},
            "verdict": {"ko": "⚖️ 최종 판정", "ja": "⚖️ 最終判定", "en": "⚖️ Verdict"},
        }.get(s.get("role", ""), {}).get(lang, s.get("id", ""))
        toc_lines.append(f"{mins:02d}:{secs:02d} {role_label}")
        cumulative += s.get("duration", 50)

    faceless_line = FACELESS_LINE[lang] if ep.get("faceless") == "O" else ""
    title_field = ep.get(f"title_{lang}") or ep.get("title_ko", "")

    return DESCRIPTION_TEMPLATES[lang].format(
        ep_num=ep["ep_number"],
        title=title_field,
        category=ep.get("category", ""),
        section=ep.get("section", ""),
        cpm_2025=ep.get("cpm_2025", "?"),
        cpm_2026=ep.get("cpm_2026", "?"),
        rpm_2026=ep.get("rpm_2026", "?"),
        sat_2025=ep.get("saturation_2025", "?"),
        sat_2026=ep.get("saturation_2026", "?"),
        faceless_line=faceless_line,
        toc="\n".join(toc_lines),
        hashtag=LANG_META[lang]["hashtag"],
    )


def build_shorts_description(ep: dict, lang: str) -> str:
    cpm = ep.get("cpm_2026") or ep.get("cpm_2025") or "?"
    sat = ep.get("saturation_2026") or "?"
    title = ep.get(f"title_{lang}") or ep.get("title_ko", "")
    prefix = {"ko": "[루브릭]", "ja": "【ルーブリック】", "en": "[Rubric]"}[lang]
    return f"{prefix} {title}\nCPM {cpm} | {sat}\n{LANG_META[lang]['hashtag']}"


# ── main ─────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("ep_number", type=int)
    parser.add_argument("lang", choices=["ko", "ja", "en"])
    parser.add_argument("--series", default="youtube-rubric")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--shorts-only", action="store_true", help="Shorts만 업로드 (본편 건너뜀)")
    return parser.parse_args()


def main():
    args = parse_args()

    ep_number   = args.ep_number
    lang        = args.lang
    series      = args.series
    dry_run     = args.dry_run
    shorts_only = args.shorts_only

    meta      = get_lang_meta(lang, series)
    ep_dir    = ROOT / series / f"ep{ep_number:02d}"
    final_dir = ep_dir / "final"

    # 언어별 파일: final/ep{NN}_final_{lang}.mp4
    final_mp4  = final_dir / f"ep{ep_number:02d}_final_{lang}.mp4"
    shorts_mp4 = final_dir / f"ep{ep_number:02d}_shorts_{lang}.mp4"
    # fallback: 언어 suffix 없는 파일 (레거시)
    if not final_mp4.exists():
        final_mp4  = final_dir / f"ep{ep_number:02d}_final.mp4"
        shorts_mp4 = final_dir / f"ep{ep_number:02d}_shorts.mp4"

    if not final_mp4.exists():
        print(f"❌ final MP4 없음: {final_mp4}")
        sys.exit(1)

    ep          = get_episode(ep_number, series)
    script_path = ep_dir / "script.json"
    script      = json.loads(script_path.read_text()) if script_path.exists() else {}

    title       = ep.get(f"title_{lang}") or ep["title_ko"]
    description = build_description(ep, script, lang, series)
    category_id = CATEGORY_MAP.get(ep.get("section", ""), "22")
    if series == "signal":
        signal_tags = {
            "ko": ["기업분석", "주식분석", "팔란티어", "SIGNAL", ep.get("company", "")],
            "ja": ["企業分析", "株式分析", "パランティア", "SIGNAL", ep.get("company", "")],
            "en": ["CompanyAnalysis", "StockAnalysis", "Palantir", "SIGNAL", ep.get("company", "")],
        }
        tags = signal_tags[lang] + [f"EP{ep_number:02d}"]
    else:
        tags = TAGS_BASE[lang] + [ep.get("category", ""), f"EP{ep_number:02d}"]

    if dry_run:
        print(f"\n[07] Dry Run — {series}/EP{ep_number:02d} [{meta['label']}]")
        print(f"     본 영상: {final_mp4} ({final_mp4.stat().st_size/1024/1024:.1f}MB)")
        if shorts_mp4.exists():
            print(f"     Shorts:  {shorts_mp4} ({shorts_mp4.stat().st_size/1024/1024:.1f}MB)")
        print(f"     제목: {title}")
        print(f"     언어: {meta['yt_lang']} | 카테고리ID: {category_id}")
        print(f"     플레이리스트 (본편): {meta['playlist_main']}")
        print(f"     플레이리스트 (Shorts): {meta['playlist_shorts']}")
        print(f"     태그: {', '.join(tags[:5])}...")
        print(f"\n     설명 (앞 300자):\n{description[:300]}...")
        return

    print(f"\n[07] {series}/EP{ep_number:02d} YouTube 업로드 [{meta['label']}]\n")
    print(f"⚠️  업로드 후 status=private → YouTube Studio에서 Public 전환 필요\n")

    creds = get_credentials()
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=creds)

    # 플레이리스트 ID 로드 (없으면 자동 생성)
    pl_cfg = load_playlist_config(series)

    result = {"lang": lang, "ep_number": ep_number}

    # ① 본 영상 업로드 → 플레이리스트 배정 (--shorts-only 시 건너뜀)
    video_id = None
    if not shorts_only:
        video_id = upload_video(
            youtube, final_mp4, title, description, tags,
            category_id, meta["yt_lang"], is_shorts=False
        )
        result["video_id"]  = video_id
        result["video_url"] = f"https://youtu.be/{video_id}"

        pl_id = get_or_create_playlist(youtube, lang, is_shorts=False, cfg=pl_cfg, series=series)
        add_to_playlist(youtube, video_id, pl_id)
        print(f"  📋 플레이리스트 추가 완료: {meta['playlist_main']}")
    else:
        print(f"  ⏭️  본 영상 건너뜀 (--shorts-only)")

    # ② Shorts 업로드 → Shorts 플레이리스트 배정
    shorts_id = None
    if shorts_mp4.exists():
        print(f"\n  Shorts 업로드...")
        shorts_desc = build_shorts_description(ep, lang)
        shorts_id = upload_video(
            youtube, shorts_mp4, title, shorts_desc, SHORTS_TAGS[lang],
            category_id, meta["yt_lang"], is_shorts=True
        )
        result["shorts_id"]  = shorts_id
        result["shorts_url"] = f"https://youtu.be/{shorts_id}"

        pl_shorts_id = get_or_create_playlist(youtube, lang, is_shorts=True, cfg=pl_cfg, series=series)
        add_to_playlist(youtube, shorts_id, pl_shorts_id)
        print(f"  📋 Shorts 플레이리스트 추가 완료: {meta['playlist_shorts']}")

    # ③ DB 업데이트
    update_video_ids(ep_number, lang, video_id, shorts_id, shorts_only=shorts_only, series=series)

    # ④ upload_result.json 업데이트 (기존 내용 유지 + 현재 언어 추가)
    result_path = ep_dir / "upload_result.json"
    existing = json.loads(result_path.read_text()) if result_path.exists() else {}
    existing[lang] = {
        "video_id": video_id, "video_url": result.get("video_url"),
        "shorts_id": shorts_id, "shorts_url": result.get("shorts_url"),
        "uploaded_at": datetime.now().isoformat(),
        "playlist_main": meta["playlist_main"],
        "playlist_shorts": meta["playlist_shorts"],
    }
    result_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))

    print(f"\n[07] ✅ 업로드 완료 [{meta['label']}]")
    if result.get("video_url"):
        print(f"     본 영상: {result['video_url']}")
    if shorts_id:
        print(f"     Shorts:  {result.get('shorts_url', '')}")
    print(f"     ⚠️  YouTube Studio에서 Private → Public 전환 후 블로그 발행 진행")


if __name__ == "__main__":
    main()
