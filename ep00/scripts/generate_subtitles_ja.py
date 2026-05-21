#!/usr/bin/env python3
"""日本語ナレーション → SRT 字幕生成 (SentenceBoundary)"""

import asyncio, re
import edge_tts
from pathlib import Path

BASE  = Path(__file__).parent.parent
OUT   = BASE / "subtitles"
OUT.mkdir(exist_ok=True)

VOICE = "ja-JP-NanamiNeural"
RATE  = "+10%"

SCENES = [
    {"id": "s01_hook",       "text": "YouTubeの収益データを読んでいると、CPM、RPM、ブルーオーシャン、飽和度といった言葉が頻繁に出てきますが、これらを知らないとどんなデータも正しく読めません。今から3分で全部まとめてしまいましょう。"},
    {"id": "s02_cpm",        "text": "まず1つ目はCPMです。CPMが高ければ当然もっと稼げると思いがちですが、実はCPMはあなたのお金ではないんです。サムスンや保険会社などの広告主がYouTubeに広告を出稿するとき、その広告が1,000回表示されるのにかかる費用、それがCPMです。金融広告のCPMが高い理由は、保険に1人加入するだけで数十万円の利益になるため、広告主が費用を多く出せるからです。反対にゲーム広告はクリックしてもすぐ収益につながりにくいので、CPMが低くなりやすいんですよ。"},
    {"id": "s03_rpm",        "text": "2つ目はRPMです。CPMに似ていますが、全く別物です。RPMが実際に自分の口座に振り込まれるお金なんです。YouTubeが中間で45%の手数料を取るため、CPMが45ドルでも実際に口座に入るのは12ドルから15ドル程度しかありません。思ったより少ないですよね？だからCPMよりRPMを見るべきなんです。本当の収益がここにあるからです。"},
    {"id": "s04_faceless",   "text": "3つ目はFacelessです。顔出しなしで運営するYouTubeスタイルのことです。顔が出るチャンネルはその人自身がチャンネルになってしまうため、休めばチャンネルも止まります。一方Facelessチャンネルは自動化できるので、寝ている間にも動画をアップし続けることができます。"},
    {"id": "s05_ocean",      "text": "4つ目と5つ目はレッドオーシャンとブルーオーシャンです。ブルーオーシャンはまだ競合がいない空白の市場、レッドオーシャンはすでに実力者たちが席を占めている市場です。当然ブルーオーシャンに入るべきだと思いますが、問題があります。ブルーオーシャンは長続きしないんです。知れ渡った途端に競合が押し寄せてすぐレッドオーシャンになってしまうので、タイミングが大切です。"},
    {"id": "s06_saturation", "text": "そのタイミングをどうやって知ればいいのでしょうか？答えは飽和度を見ることです。市場がどれだけ埋まっているかを示すものですが、重要なのは今の数値ではなく方向性です。飽和度が今は低くても急速に上昇していれば、6ヶ月後にはレッドオーシャンになっている可能性があります。現状だけでなく、方向性を一緒に見ることが大切です。"},
    {"id": "s07_outro",      "text": "今日は6つの用語を学びました。CPMは広告主がYouTubeに払うお金、RPMは自分の口座に実際に入るお金、Facelessは顔出しなしで運営するチャンネルスタイル、レッドオーシャンは競争が激しい市場、ブルーオーシャンはまだ空いている市場、そして飽和度はその市場がどれだけ埋まっているかです。本編を見る準備はできましたか？次の動画から40のカテゴリーを一緒に見ていきましょう。"},
]

def ms_to_srt(ms):
    h  = int(ms) // 3600000
    m  = (int(ms) % 3600000) // 60000
    s  = (int(ms) % 60000) // 1000
    cs = int(ms) % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{cs:03d}"

def split_natural_ja(text, max_len=14):
    """日本語字幕分割 — 句読点優先 / 中間均等分割"""
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    # 1. 読点「、」「，」で分割
    for i, ch in enumerate(text):
        if ch in ('、', '，', '。') and 4 < i < len(text) - 3:
            left  = text[:i+1].strip()
            right = text[i+1:].strip()
            result = []
            result += split_natural_ja(left,  max_len) if len(left)  > max_len else [left]
            result += split_natural_ja(right, max_len) if len(right) > max_len else [right]
            return result

    # 2. 中間分割
    mid = len(text) // 2
    return [text[:mid], text[mid:]]

def merge_orphans_ja(chunks, min_len=3):
    if len(chunks) <= 1:
        return chunks
    merged = [chunks[0]]
    for c in chunks[1:]:
        if len(c) <= min_len and len(merged[-1]) + len(c) <= 18:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    return merged

def sentence_to_entries(text, start_ms, end_ms):
    chunks = merge_orphans_ja(split_natural_ja(text))
    groups = []
    for i in range(0, len(chunks), 2):
        groups.append("\n".join(chunks[i:i+2]))
    if len(groups) == 1:
        return [(start_ms, end_ms, groups[0])]
    char_counts = [len(g) for g in groups]
    total_chars = sum(char_counts)
    dur = end_ms - start_ms
    entries, t = [], start_ms
    for i, (g, c) in enumerate(zip(groups, char_counts)):
        seg_dur = int(dur * c / total_chars)
        end_t = t + seg_dur if i < len(groups) - 1 else end_ms
        entries.append((t, end_t, g))
        t = end_t
    return entries

async def get_boundaries(text):
    boundaries = []
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    async for event in comm.stream():
        if event["type"] == "SentenceBoundary":
            boundaries.append({
                "text":     event["text"],
                "offset":   event["offset"] // 10000,
                "duration": event["duration"] // 10000,
            })
    return boundaries

async def process_scene(scene, global_offset_ms):
    sid, text = scene["id"], scene["text"]
    print(f"  → {sid} ...", end="", flush=True)
    boundaries = await get_boundaries(text)
    if not boundaries:
        print(" ⚠️ なし")
        return [], 0
    srt_lines = []
    for b in boundaries:
        start = b["offset"] + global_offset_ms
        end   = b["offset"] + b["duration"] + global_offset_ms
        entries = sentence_to_entries(b["text"], start, end)
        srt_lines.extend(entries)
    scene_dur = boundaries[-1]["offset"] + boundaries[-1]["duration"]
    print(f" ✅ ({scene_dur/1000:.1f}s, {len(srt_lines)}ライン)")
    return srt_lines, scene_dur

async def main():
    print("\n📝 日本語字幕生成開始\n")
    INTRO_MS = 10 * 1000
    GAP_MS   =  2 * 1000
    all_lines, offset = [], INTRO_MS

    for i, scene in enumerate(SCENES):
        lines, dur = await process_scene(scene, offset)
        all_lines.extend(lines)
        is_last = (i == len(SCENES) - 1)
        offset += dur + (0 if is_last else GAP_MS)

    srt_path = OUT / "ja.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(all_lines, 1):
            f.write(f"{i}\n{ms_to_srt(start)} --> {ms_to_srt(end)}\n{text}\n\n")

    print(f"\n✅ SRT保存 → {srt_path}  ({len(all_lines)}ライン)")

if __name__ == "__main__":
    asyncio.run(main())
