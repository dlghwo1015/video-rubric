#!/usr/bin/env python3
"""EP00 English Narration — JennyNeural +10%"""

import asyncio
import edge_tts
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "narration" / "en"
OUT_DIR.mkdir(exist_ok=True)

VOICE = "en-US-JennyNeural"
RATE  = "+10%"

SCENES = [
    {
        "id": "s01_hook",
        "text": "If you've ever looked at YouTube analytics, you've probably seen terms like CPM, RPM, Blue Ocean, and Market Saturation — and had no idea what they actually meant. Knowing these 6 terms will completely change how you read the data. Let's break them all down in just 3 minutes."
    },
    {
        "id": "s02_cpm",
        "text": "First up is CPM — Cost Per Mille. It's easy to assume that a high CPM means more money in your pocket, but here's the thing: CPM is not your money. CPM is what advertisers — like insurance companies or big brands — pay YouTube to show their ads 1,000 times. Financial ads have high CPMs because signing up one person for insurance can be worth hundreds of dollars, so advertisers will pay a premium. Gaming ads, on the other hand, have low CPMs because clicks rarely lead to immediate purchases."
    },
    {
        "id": "s03_rpm",
        "text": "Number 2 is RPM — Revenue Per Mille. It looks similar to CPM, but they're completely different. RPM is the money that actually hits your bank account. YouTube takes roughly a 45 percent cut, so even if CPM is 45 dollars, your RPM might only land around 12 to 15 dollars. A lot less than you'd expect, right? That's exactly why RPM is the number you should actually be watching — it's your real earnings."
    },
    {
        "id": "s04_faceless",
        "text": "Number 3 is Faceless. A Faceless channel is one where the creator never shows their face. With a face-based channel, you are the channel — if you stop, everything stops. But Faceless channels can be fully automated, meaning videos can go live while you sleep. Common types include narration-only, AI-generated visuals, infographic-style, and ASMR or ambient sound formats."
    },
    {
        "id": "s05_ocean",
        "text": "Numbers 4 and 5 are Red Ocean and Blue Ocean. A Blue Ocean is an untapped market with little to no competition. A Red Ocean is one already crowded with established creators. You might think Blue Ocean is always the right move — but here's the catch: Blue Oceans don't stay blue for long. The moment people catch on, competition floods in and it turns Red fast. That's why timing matters."
    },
    {
        "id": "s06_saturation",
        "text": "So how do you know when the timing is right? That's where Market Saturation comes in. Saturation shows how full a market currently is. But the key isn't the current number — it's the direction. A market with low saturation that's rising fast could become a Red Ocean in just 6 months. You need to watch the trend, not just the snapshot."
    },
    {
        "id": "s07_outro",
        "text": "So here's a quick recap of all 6 terms. CPM is what advertisers pay YouTube. RPM is what actually lands in your account. Faceless means running a channel without showing your face. Red Ocean is a saturated, highly competitive market. Blue Ocean is an open, low-competition market. And Market Saturation shows how full a market is. Ready for the main series? In the next video, we'll break down 40 content categories one by one."
    }
]

async def generate(scene):
    sid, text = scene["id"], scene["text"]
    out = OUT_DIR / f"{sid}.mp3"
    print(f"  → {sid} ...", end="", flush=True)
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    await comm.save(str(out))
    print(f" ✅")

async def main():
    print(f"\n🎙️  EP00 English Narration (JennyNeural, +10%)\n")
    for s in SCENES:
        await generate(s)
    print(f"\n✅ Done → {OUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
