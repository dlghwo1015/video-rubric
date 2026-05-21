#!/usr/bin/env python3
"""English Narration → SRT Subtitles (SentenceBoundary + word-aware splitting)"""

import asyncio, re
import edge_tts
from pathlib import Path

BASE  = Path(__file__).parent.parent
OUT   = BASE / "subtitles"
OUT.mkdir(exist_ok=True)

VOICE = "en-US-JennyNeural"
RATE  = "+10%"

SCENES = [
    {"id": "s01_hook",       "text": "If you've ever looked at YouTube analytics, you've probably seen terms like CPM, RPM, Blue Ocean, and Market Saturation — and had no idea what they actually meant. Knowing these 6 terms will completely change how you read the data. Let's break them all down in just 3 minutes."},
    {"id": "s02_cpm",        "text": "First up is CPM — Cost Per Mille. It's easy to assume that a high CPM means more money in your pocket, but here's the thing: CPM is not your money. CPM is what advertisers — like insurance companies or big brands — pay YouTube to show their ads 1,000 times. Financial ads have high CPMs because signing up one person for insurance can be worth hundreds of dollars, so advertisers will pay a premium. Gaming ads, on the other hand, have low CPMs because clicks rarely lead to immediate purchases."},
    {"id": "s03_rpm",        "text": "Number 2 is RPM — Revenue Per Mille. It looks similar to CPM, but they're completely different. RPM is the money that actually hits your bank account. YouTube takes roughly a 45 percent cut, so even if CPM is 45 dollars, your RPM might only land around 12 to 15 dollars. A lot less than you'd expect, right? That's exactly why RPM is the number you should actually be watching — it's your real earnings."},
    {"id": "s04_faceless",   "text": "Number 3 is Faceless. A Faceless channel is one where the creator never shows their face. With a face-based channel, you are the channel — if you stop, everything stops. But Faceless channels can be fully automated, meaning videos can go live while you sleep. Common types include narration-only, AI-generated visuals, infographic-style, and ASMR or ambient sound formats."},
    {"id": "s05_ocean",      "text": "Numbers 4 and 5 are Red Ocean and Blue Ocean. A Blue Ocean is an untapped market with little to no competition. A Red Ocean is one already crowded with established creators. You might think Blue Ocean is always the right move — but here's the catch: Blue Oceans don't stay blue for long. The moment people catch on, competition floods in and it turns Red fast. That's why timing matters."},
    {"id": "s06_saturation", "text": "So how do you know when the timing is right? That's where Market Saturation comes in. Saturation shows how full a market currently is. But the key isn't the current number — it's the direction. A market with low saturation that's rising fast could become a Red Ocean in just 6 months. You need to watch the trend, not just the snapshot."},
    {"id": "s07_outro",      "text": "So here's a quick recap of all 6 terms. CPM is what advertisers pay YouTube. RPM is what actually lands in your account. Faceless means running a channel without showing your face. Red Ocean is a saturated, highly competitive market. Blue Ocean is an open, low-competition market. And Market Saturation shows how full a market is. Ready for the main series? In the next video, we'll break down 40 content categories one by one."},
]

def ms_to_srt(ms):
    h  = int(ms) // 3600000
    m  = (int(ms) % 3600000) // 60000
    s  = (int(ms) % 60000) // 1000
    cs = int(ms) % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{cs:03d}"

def split_natural_en(text, max_len=38):
    """English subtitle splitting — punctuation-first / balanced word split"""
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    # 1. Split on sentence-ending punctuation first (. ! ?)
    for i, ch in enumerate(text):
        if ch in ('.', '!', '?') and 8 < i < len(text) - 5:
            # only split if next char is space (end of sentence)
            if i + 1 < len(text) and text[i+1] == ' ':
                left  = text[:i+1].strip()
                right = text[i+2:].strip()
                result = []
                result += split_natural_en(left,  max_len) if len(left)  > max_len else [left]
                result += split_natural_en(right, max_len) if len(right) > max_len else [right]
                return result

    # 2. Split on em-dash or comma
    for sep in [' — ', ', ']:
        idx = text.find(sep)
        if 8 < idx < len(text) - 5:
            left  = text[:idx + (3 if sep == ' — ' else 1)].strip()
            right = text[idx + len(sep):].strip()
            result = []
            result += split_natural_en(left,  max_len) if len(left)  > max_len else [left]
            result += split_natural_en(right, max_len) if len(right) > max_len else [right]
            return result

    # 3. Word-boundary balanced split
    words = text.split(' ')
    if len(words) == 1:
        return [text]

    half = len(text) // 2
    best_i, best_dist, cum = 1, float('inf'), 0
    for i, w in enumerate(words[:-1]):
        cum += len(w) + 1
        dist = abs(cum - half)
        if dist < best_dist:
            best_dist, best_i = dist, i + 1

    left  = ' '.join(words[:best_i])
    right = ' '.join(words[best_i:])
    result = []
    result += split_natural_en(left,  max_len) if len(left)  > max_len else [left]
    result += split_natural_en(right, max_len) if len(right) > max_len else [right]
    return result

def merge_orphans_en(chunks, min_len=8):
    if len(chunks) <= 1:
        return chunks
    merged = [chunks[0]]
    for c in chunks[1:]:
        if len(c) <= min_len and len(merged[-1]) + 1 + len(c) <= 44:
            merged[-1] = merged[-1] + ' ' + c
        else:
            merged.append(c)
    return merged

def sentence_to_entries(text, start_ms, end_ms):
    chunks = merge_orphans_en(split_natural_en(text))
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
        print(" ⚠️ none")
        return [], 0
    srt_lines = []
    for b in boundaries:
        start = b["offset"] + global_offset_ms
        end   = b["offset"] + b["duration"] + global_offset_ms
        entries = sentence_to_entries(b["text"], start, end)
        srt_lines.extend(entries)
    scene_dur = boundaries[-1]["offset"] + boundaries[-1]["duration"]
    print(f" ✅ ({scene_dur/1000:.1f}s, {len(srt_lines)} lines)")
    return srt_lines, scene_dur

async def main():
    print("\n📝 English subtitle generation start\n")
    INTRO_MS = 10 * 1000
    GAP_MS   =  2 * 1000
    all_lines, offset = [], INTRO_MS

    for i, scene in enumerate(SCENES):
        lines, dur = await process_scene(scene, offset)
        all_lines.extend(lines)
        is_last = (i == len(SCENES) - 1)
        offset += dur + (0 if is_last else GAP_MS)

    srt_path = OUT / "en.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(all_lines, 1):
            f.write(f"{i}\n{ms_to_srt(start)} --> {ms_to_srt(end)}\n{text}\n\n")

    print(f"\n✅ SRT saved → {srt_path}  ({len(all_lines)} lines)")

if __name__ == "__main__":
    asyncio.run(main())
