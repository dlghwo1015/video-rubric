#!/usr/bin/env python3
"""EP00 English Version Assembly — Visual + Narration + BGM"""

import subprocess
from pathlib import Path

BASE     = Path(__file__).parent.parent
SCENES   = BASE / "scenes" / "en"
NARR     = BASE / "narration" / "en"
BGM      = BASE.parent / "_shared" / "bgm" / "nocturne_full.mp3"
OUT_DIR  = BASE / "output" / "en"
OUT_DIR.mkdir(exist_ok=True)

BGM_VOL   = 0.30
INTRO_SEC = 10
GAP_SEC   = 2.0

SCENE_IDS = ["s01_hook","s02_cpm","s03_rpm","s04_faceless","s05_ocean","s06_saturation","s07_outro"]

def duration(path):
    r = subprocess.run(
        ["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",str(path)],
        capture_output=True, text=True)
    return float(r.stdout.strip())

def make_scene(sid, intro=False, add_gap=True, is_last=False):
    visual   = SCENES / f"{sid}.mp4"
    narr     = NARR   / f"{sid}.mp3"
    out      = OUT_DIR / f"{sid}.mp4"

    narr_dur = duration(narr)
    gap      = GAP_SEC if add_gap else 0.0
    fade_out_vf = f",fade=t=out:st={narr_dur - 2.0}:d=2.0:color=white" if is_last else ""

    if intro:
        total_dur = INTRO_SEC + narr_dur + gap
        print(f"  {sid} [intro {INTRO_SEC}s + narration {narr_dur:.1f}s + gap {gap}s = {total_dur:.1f}s]")
        subprocess.run([
            "ffmpeg","-y",
            "-stream_loop","-1","-i",str(visual),
            "-i",str(narr),
            "-i",str(BGM),
            "-filter_complex",
            f"""
            [0:v]trim=duration={total_dur},setpts=PTS-STARTPTS{fade_out_vf}[vout];
            [1:a]adelay={int(INTRO_SEC*1000)}|{int(INTRO_SEC*1000)}[narr_delayed];
            [2:a]volume={BGM_VOL},afade=t=out:st={total_dur-2}:d=2[bgm];
            [narr_delayed][bgm]amix=inputs=2:duration=longest:normalize=0[aout]
            """,
            "-map","[vout]","-map","[aout]",
            "-c:v","libx264","-c:a","aac","-shortest",
            str(out)
        ], capture_output=True)
    else:
        total_dur = narr_dur + gap
        bgm_fade_d = 3.0 if is_last else 1.5
        print(f"  {sid} [narration {narr_dur:.1f}s + gap {gap}s = {total_dur:.1f}s]{'  ← ending' if is_last else ''}")
        subprocess.run([
            "ffmpeg","-y",
            "-stream_loop","-1","-i",str(visual),
            "-i",str(narr),
            "-i",str(BGM),
            "-filter_complex",
            f"""
            [0:v]trim=duration={total_dur},setpts=PTS-STARTPTS{fade_out_vf}[vout];
            [2:a]volume={BGM_VOL},afade=t=out:st={total_dur-bgm_fade_d}:d={bgm_fade_d}[bgm];
            [1:a][bgm]amix=inputs=2:duration=longest:normalize=0[aout]
            """,
            "-map","[vout]","-map","[aout]",
            "-c:v","libx264","-c:a","aac","-shortest",
            str(out)
        ], capture_output=True)

    print(f"     ✅ {out.name}")
    return out

def concat_all(scene_files):
    out = BASE / "final" / "EP00_en.mp4"
    list_file = OUT_DIR / "concat_list.txt"
    with open(list_file,"w") as f:
        for p in scene_files:
            f.write(f"file '{p}'\n")
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0",
        "-i",str(list_file),"-c","copy",str(out)
    ], capture_output=True)
    total = duration(out)
    print(f"\n🎬 EP00_en_demo.mp4 complete! ({total:.1f}s = {total/60:.1f}min)")
    return out

def main():
    print("\n🎬 EP00 English Version Assembly Start\n")
    files = []
    for i, sid in enumerate(SCENE_IDS):
        is_last = (i == len(SCENE_IDS) - 1)
        f = make_scene(sid, intro=(i==0), add_gap=not is_last, is_last=is_last)
        files.append(f)
    print("\n📎 Concatenating all scenes...")
    final = concat_all(files)
    print(f"\n▶ Play: open '{final}'")
    subprocess.run(["open", str(final)])

if __name__ == "__main__":
    main()
