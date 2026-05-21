# 영상 제작 파이프라인 — video-rubric

> 기획 → HTML 비주얼 → TTS 나레이션 → Playwright 렌더링 → FFmpeg 조립 → 자막 → YouTube + GitHub Pages + Blogger

---

## 전체 흐름 한눈에

```
📝 기획
  └─ 스크립트 작성 (ko/ja/en)
       │
       ▼
🎨 HTML 비주얼 (epXX/html/)
  └─ epXX_visual_ko.html / ja / en
       │
       ▼
🎙 TTS 나레이션 (epXX/narration/)
  └─ generate_narration_*.py → ko/ ja/ en/ (s01~s07.mp3)
       │
       ▼
🎬 Playwright 렌더링 (epXX/scenes/)
  └─ render_html_*.py → ko/ ja/ en/ (s01~s07.mp4)
       │
       ▼
🎵 FFmpeg 조립 (epXX/output/ → final/)
  └─ assemble_*.py → EPXX_ko.mp4 / ja / en
       │
       ▼
📝 자막 생성 & 번인 (epXX/subtitles/ → final/)
  └─ generate_subtitles_*.py → ko.srt / ja.srt / en.srt
  └─ burn_subtitles_*.py   → EPXX_ko_sub.mp4 / ja / en
       │
       ▼
🚀 3채널 배포
  ├─ YouTube    → EPXX_ko_sub.mp4 (업로드)
  ├─ GitHub Pages → epXX_visual_ko.html (CDN)
  └─ Blogger    → 포스트 (YouTube iframe + GitHub Pages iframe)
```

---

## Phase 1 — 기획

### 산출물
- `epXX/scripts/` 안에 Python 스크립트 15개
- 콘텐츠 방향: 슬라이드 수, 언어별 나레이션 텍스트

### 작업 기준
| 항목 | 기준 |
|------|------|
| 슬라이드 수 | 7개 권장 (s01~s07) |
| 언어 | ko / ja / en |
| 영상 길이 목표 | 3~5분 |
| 나레이션 스타일 | 교육적, 친근한 어조 |

---

## Phase 2 — HTML 비주얼 제작

### 파일 위치
```
epXX/html/
  epXX_visual_ko.html
  epXX_visual_ja.html
  epXX_visual_en.html
```

### 디자인 규칙
- 배경: 파스텔 크림 (`#fdfbf7`)
- 딥그린 포인트: `#1a4d2e`, 민트: `#52d4a0`
- 폰트: Noto Sans KR (ko), Noto Sans JP (ja), Inter (en)
- 슬라이드 전환: CSS 애니메이션 (`.go` 클래스 트리거)

### 애니메이션 트리거 매핑 (ANIM_TRIGGERS)
```python
ANIM_TRIGGERS = {
    "s01": [],
    "s02": ["fadeUp"],
    "s03": ["typing"],
    "s04": ["barChart"],
    "s05": ["drawLine"],
    "s06": ["drawLine"],
    "s07": [],
}
```

---

## Phase 3 — TTS 나레이션

### 스크립트
```
epXX/scripts/generate_narration_ko.py
epXX/scripts/generate_narration_ja.py
epXX/scripts/generate_narration_en.py
```

### 음성 설정
| 언어 | 모델 | 속도 |
|------|------|------|
| 한국어 | `ko-KR-SunHiNeural` | +10% |
| 日本語 | `ja-JP-NanamiNeural` | +10% |
| English | `en-US-JennyNeural` | +10% |

### 출력
```
epXX/narration/ko/s01.mp3 ~ s07.mp3
epXX/narration/ja/s01.mp3 ~ s07.mp3
epXX/narration/en/s01.mp3 ~ s07.mp3
```

### 실행
```bash
cd epXX/scripts
python generate_narration_ko.py
python generate_narration_ja.py
python generate_narration_en.py
```

---

## Phase 4 — Playwright 렌더링

### 스크립트
```
epXX/scripts/render_html_ko.py
epXX/scripts/render_html_ja.py
epXX/scripts/render_html_en.py
```

### 동작 원리
1. `http://localhost:7890/epXX_visual_*.html` 열기
2. 슬라이드별 이동 (`goSlide(n)`)
3. `.go` 클래스 부여 → 애니메이션 시작
4. 나레이션 mp3 길이만큼 webm 녹화
5. webm → mp4 변환 (ffmpeg)

### 사전 조건
```bash
# 로컬 서버 실행 (별도 터미널)
cd epXX/html && python -m http.server 7890
```

### 출력
```
epXX/scenes/ko/s01.mp4 ~ s07.mp4
epXX/scenes/ja/s01.mp4 ~ s07.mp4
epXX/scenes/en/s01.mp4 ~ s07.mp4
```

### 실행
```bash
python render_html_ko.py
python render_html_ja.py
python render_html_en.py
```

---

## Phase 5 — FFmpeg 조립

### 스크립트
```
epXX/scripts/assemble_ko.py
epXX/scripts/assemble_ja.py
epXX/scripts/assemble_en.py
```

### 조립 순서
1. 씬 mp4 파일 순서대로 concat
2. 씬 사이 2초 갭 (검정 또는 흰색 fade)
3. BGM 믹싱: `_shared/bgm/calm/chopin_nocturne_op9_no2.mp3` @ 30% 볼륨
4. 첫 씬 fade-in (0.5초), 마지막 씬 fade-out (2초, 흰색)

### BGM 라이브러리
```
_shared/bgm/
  calm/     ← 쇼팽 녹턴 9곡 (잔잔한 나레이션 배경) ✅
  study/    ← 바흐 골드베르크 4곡 (집중/교육 영상) ✅
  ambient/  ← 사티 짐노페디·그노시엔 4곡 (여백 있는 씬) ✅
```

> 모두 Musopen via Internet Archive — 퍼블릭 도메인

### 출력
```
epXX/output/ko/ (중간 concat 파일)
epXX/final/EPXX_ko.mp4   ← BGM 믹싱 완료
epXX/final/EPXX_ja.mp4
epXX/final/EPXX_en.mp4
```

### 실행
```bash
python assemble_ko.py
python assemble_ja.py
python assemble_en.py
```

---

## Phase 6 — 자막 생성 & 번인

### 스크립트 (자막 생성)
```
epXX/scripts/generate_subtitles_ko.py
epXX/scripts/generate_subtitles_ja.py
epXX/scripts/generate_subtitles_en.py
```

### 동작 원리
1. Edge TTS `SentenceBoundary` 이벤트로 타이밍 획득
2. 자연스러운 문장 분리 (언어별 split 함수)
3. 짧은 조각 병합 (orphan merge)
4. SRT 파일 출력

### 자막 파일
```
epXX/subtitles/ko.srt → ko.ass
epXX/subtitles/ja.srt → ja.ass
epXX/subtitles/en.srt → en.ass
```

### 스크립트 (번인)
```
epXX/scripts/burn_subtitles_ko.py
epXX/scripts/burn_subtitles_ja.py
epXX/scripts/burn_subtitles_en.py
```

### 자막 스타일
| 언어 | 폰트 | 크기 | MarginV |
|------|------|------|---------|
| 한국어 | Apple SD Gothic Neo | 52px | 60 |
| 日本語 | Hiragino Sans W6 | 52px | 60 |
| English | Arial | 72px | 60 |

### FFmpeg 경로
```
/opt/homebrew/Cellar/ffmpeg-full/8.1.1/bin/ffmpeg
```

### 출력
```
epXX/final/EPXX_ko_sub.mp4  ← 최종 완성본
epXX/final/EPXX_ja_sub.mp4
epXX/final/EPXX_en_sub.mp4
```

### 실행
```bash
python generate_subtitles_ko.py && python burn_subtitles_ko.py
python generate_subtitles_ja.py && python burn_subtitles_ja.py
python generate_subtitles_en.py && python burn_subtitles_en.py
```

---

## Phase 7 — 3채널 배포

### 채널 역할 분담
| 채널 | 역할 | 콘텐츠 |
|------|------|--------|
| **YouTube** | 영상 호스팅 + 주 수익 | `EPXX_ko_sub.mp4` (한국어 우선) |
| **GitHub Pages** | HTML 슬라이드 CDN | `epXX_visual_ko.html` |
| **Blogger** | 블로그 포스트 | YouTube iframe + GitHub Pages iframe |

---

### 7-1. YouTube 업로드

```
업로드 파일: epXX/final/EPXX_ko_sub.mp4
제목 (ko): [유튜브 수익 루브릭 EPXX] 제목
설명: 해시태그 + 타임스탬프 + 링크 (Blogger 포스트 URL)
태그: 유튜브수익, 유튜브용어, CPM, RPM, 루브릭
공개 설정: 즉시 공개 또는 예약
```

> ⚠️ 현재 YouTube Data API 자동 업로드 미구현 → 수동 업로드

---

### 7-2. GitHub Pages 배포

#### 레포 구조
```
dlghwo1015/video-rubric (GitHub 레포)
  └─ docs/
       ├─ ep00/
       │    ep00_visual_ko.html
       │    ep00_visual_ja.html
       │    ep00_visual_en.html
       └─ ep01/
            ep01_visual_ko.html ...
```

#### 설정
```
Settings → Pages → Source: main branch / docs folder
URL: https://dlghwo1015.github.io/video-rubric/ep00/ep00_visual_ko.html
```

#### 배포 명령
```bash
cd ~/Documents/Claude/Projects/video-rubric
mkdir -p docs/ep00
cp ep00/html/*.html docs/ep00/
git add docs/
git commit -m "feat: EP00 HTML slides"
git push origin main
```

---

### 7-3. Blogger 포스트 작성

#### 표준 포스트 구조
```html
<!-- 포스트 제목: [유튜브 수익 루브릭 EP00] 유튜브 핵심 용어 6가지 -->

<!-- 1. 인트로 텍스트 (200~300자) -->
<p>유튜브를 시작하거나 수익화를 준비한다면 꼭 알아야 할 핵심 용어 6가지를 정리했습니다...</p>

<!-- 2. 인터랙티브 슬라이드 (GitHub Pages) -->
<div style="position:relative;padding-top:56.25%;margin:2em 0;">
  <iframe
    src="https://dlghwo1015.github.io/video-rubric/ep00/ep00_visual_ko.html"
    style="position:absolute;top:0;left:0;width:100%;height:100%;border:none;"
    loading="lazy"
    allowfullscreen>
  </iframe>
</div>

<!-- 3. 유튜브 영상 -->
<div style="position:relative;padding-top:56.25%;margin:2em 0;">
  <iframe
    src="https://www.youtube.com/embed/[VIDEO_ID]"
    style="position:absolute;top:0;left:0;width:100%;height:100%;border:none;"
    loading="lazy"
    allowfullscreen>
  </iframe>
</div>

<!-- 4. 주요 내용 요약 (SEO 텍스트) -->
<h2>핵심 내용 요약</h2>
<ul>
  <li>CPM / RPM 차이</li>
  <li>조회수 vs 시청 시간</li>
  ...
</ul>

<!-- 5. 레이블 -->
유튜브수익, 유튜브루브릭, 유튜브용어, EP00
```

---

## 전체 산출물 체크리스트

### EP00 기준

| 단계 | 파일 | ko | ja | en |
|------|------|----|----|-----|
| HTML | `ep00/html/ep00_visual_*.html` | ✅ | ✅ | ✅ |
| 나레이션 | `ep00/narration/*/s01~s07.mp3` | ✅ | ✅ | ✅ |
| 씬 | `ep00/scenes/*/s01~s07.mp4` | ✅ | ✅ | ✅ |
| 조립 | `ep00/final/EP00_*.mp4` | ✅ | ✅ | ✅ |
| 자막 SRT | `ep00/subtitles/*.srt` | ✅ | ✅ | ✅ |
| 최종 | `ep00/final/EP00_*_sub.mp4` | ✅ | ✅ | ✅ |
| GitHub Pages | `docs/ep00/ep00_visual_*.html` | ⬜ | ⬜ | ⬜ |
| YouTube | 업로드 완료 | ⬜ | ⬜ | ⬜ |
| Blogger | 포스트 발행 | ⬜ | ⬜ | ⬜ |

---

## 새 에피소드 체크리스트 (EP01~)

```
□ 1. ep00/ 구조 복사 → ep01/
□ 2. html/ 에 새 슬라이드 작성
□ 3. scripts/ 내 경로 확인 (BASE = Path(__file__).parent.parent)
□ 4. 나레이션 텍스트 수정 (generate_narration_*.py)
□ 5. ANIM_TRIGGERS 조정
□ 6. Phase 3~6 순서대로 실행
□ 7. docs/epXX/ 에 HTML 복사 + GitHub push
□ 8. YouTube 업로드
□ 9. Blogger 포스트 작성 + 발행
□ 10. 대시보드 확인 (localhost:3002/video)
```

---

## 빠른 실행 명령 (EP 전체 빌드)

```bash
#!/bin/bash
# run_all.sh — ep번호를 인자로 받아 전체 파이프라인 실행
# 사용법: bash run_all.sh ep00

EP=${1:-"ep00"}
BASE=~/Documents/Claude/Projects/video-rubric

echo "=== [$EP] Phase 3: 나레이션 ==="
cd $BASE/$EP/scripts
python generate_narration_ko.py
python generate_narration_ja.py
python generate_narration_en.py

echo "=== [$EP] Phase 4: Playwright 렌더링 ==="
# 주의: html/ 서버가 포트 7890 에서 실행 중이어야 함
# cd $BASE/$EP/html && python -m http.server 7890 &
python render_html_ko.py
python render_html_ja.py
python render_html_en.py

echo "=== [$EP] Phase 5: FFmpeg 조립 ==="
python assemble_ko.py
python assemble_ja.py
python assemble_en.py

echo "=== [$EP] Phase 6: 자막 ==="
python generate_subtitles_ko.py && python burn_subtitles_ko.py
python generate_subtitles_ja.py && python burn_subtitles_ja.py
python generate_subtitles_en.py && python burn_subtitles_en.py

echo "=== 완료! final/ 확인 ==="
ls -lh $BASE/$EP/final/
```

---

## 대시보드 확인

```
http://localhost:3002/video          ← 시리즈 목록
http://localhost:3002/video/video-rubric  ← 에피소드 목록 + 영상 재생
```

---

*최종 업데이트: 2026-05-21*
