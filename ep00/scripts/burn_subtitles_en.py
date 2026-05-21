#!/usr/bin/env python3
"""English SRT → ASS → ffmpeg burn-in"""

import subprocess, re
from pathlib import Path

BASE = Path(__file__).parent.parent
SRT  = BASE / "subtitles/en.srt"
ASS  = BASE / "subtitles/en.ass"
IN   = BASE / "final" / "EP00_en.mp4"
OUT  = BASE / "final" / "EP00_en_sub.mp4"

def srt_time_to_ass(t):
    t = t.replace(",", ".")
    parts = t.split(":")
    h, m, s = parts[0], parts[1], parts[2]
    s_parts = s.split(".")
    sec = s_parts[0]
    cs  = s_parts[1][:2] if len(s_parts) > 1 else "00"
    return f"{int(h)}:{m}:{sec}.{cs}"

def srt_to_ass(srt_path, ass_path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Collisions: Normal

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00111111,&HAA000000,1,0,0,0,100,100,0,0,1,4,3,2,40,40,80,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    content = srt_path.read_text(encoding="utf-8")
    blocks  = re.split(r'\n\n+', content.strip())
    events  = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        times = lines[1].split(" --> ")
        start = srt_time_to_ass(times[0].strip())
        end   = srt_time_to_ass(times[1].strip())
        text  = "\\N".join(lines[2:])
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    ass_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    print(f"  ASS converted: {len(events)} lines")

def burn():
    print("\n🎬 English subtitle burn-in start\n")
    srt_to_ass(SRT, ASS)

    FFMPEG = "/opt/homebrew/Cellar/ffmpeg-full/8.1.1/bin/ffmpeg"
    result = subprocess.run([
        FFMPEG, "-y",
        "-i", str(IN),
        "-vf", f"ass={ASS}",
        "-c:a", "copy",
        str(OUT)
    ], capture_output=True, text=True)

    if result.returncode == 0:
        size = OUT.stat().st_size // (1024*1024)
        print(f"\n✅ Done! EP00_en_sub.mp4 ({size}MB)")
        subprocess.run(["open", str(OUT)])
    else:
        print("❌ Error:\n", result.stderr[-800:])

if __name__ == "__main__":
    burn()
