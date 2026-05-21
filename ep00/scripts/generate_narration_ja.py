#!/usr/bin/env python3
"""EP00 日本語ナレーション — NanamiNeural +10%"""

import asyncio
import edge_tts
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "narration" / "ja"
OUT_DIR.mkdir(exist_ok=True)

VOICE = "ja-JP-NanamiNeural"
RATE  = "+10%"

SCENES = [
    {
        "id": "s01_hook",
        "text": "YouTubeの収益データを読んでいると、CPM、RPM、ブルーオーシャン、飽和度といった言葉が頻繁に出てきますが、これらを知らないとどんなデータも正しく読めません。今から3分で全部まとめてしまいましょう。"
    },
    {
        "id": "s02_cpm",
        "text": "まず1つ目はCPMです。CPMが高ければ当然もっと稼げると思いがちですが、実はCPMはあなたのお金ではないんです。サムスンや保険会社などの広告主がYouTubeに広告を出稿するとき、その広告が1,000回表示されるのにかかる費用、それがCPMです。金融広告のCPMが高い理由は、保険に1人加入するだけで数十万円の利益になるため、広告主が費用を多く出せるからです。反対にゲーム広告はクリックしてもすぐ収益につながりにくいので、CPMが低くなりやすいんですよ。"
    },
    {
        "id": "s03_rpm",
        "text": "2つ目はRPMです。CPMに似ていますが、全く別物です。RPMが実際に自分の口座に振り込まれるお金なんです。YouTubeが中間で45%の手数料を取るため、CPMが45ドルでも実際に口座に入るのは12ドルから15ドル程度しかありません。思ったより少ないですよね？だからCPMよりRPMを見るべきなんです。本当の収益がここにあるからです。"
    },
    {
        "id": "s04_faceless",
        "text": "3つ目はFacelessです。顔出しなしで運営するYouTubeスタイルのことです。顔が出るチャンネルはその人自身がチャンネルになってしまうため、休めばチャンネルも止まります。一方Facelessチャンネルは自動化できるので、寝ている間にも動画をアップし続けることができます。"
    },
    {
        "id": "s05_ocean",
        "text": "4つ目と5つ目はレッドオーシャンとブルーオーシャンです。ブルーオーシャンはまだ競合がいない空白の市場、レッドオーシャンはすでに実力者たちが席を占めている市場です。当然ブルーオーシャンに入るべきだと思いますが、問題があります。ブルーオーシャンは長続きしないんです。知れ渡った途端に競合が押し寄せてすぐレッドオーシャンになってしまうので、タイミングが大切です。"
    },
    {
        "id": "s06_saturation",
        "text": "そのタイミングをどうやって知ればいいのでしょうか？答えは飽和度を見ることです。市場がどれだけ埋まっているかを示すものですが、重要なのは今の数値ではなく方向性です。飽和度が今は低くても急速に上昇していれば、6ヶ月後にはレッドオーシャンになっている可能性があります。現状だけでなく、方向性を一緒に見ることが大切です。"
    },
    {
        "id": "s07_outro",
        "text": "今日は6つの用語を学びました。CPMは広告主がYouTubeに払うお金、RPMは自分の口座に実際に入るお金、Facelessは顔出しなしで運営するチャンネルスタイル、レッドオーシャンは競争が激しい市場、ブルーオーシャンはまだ空いている市場、そして飽和度はその市場がどれだけ埋まっているかです。本編を見る準備はできましたか？次の動画から40のカテゴリーを一緒に見ていきましょう。"
    }
]

async def generate(scene):
    sid  = scene["id"]
    text = scene["text"]
    out  = OUT_DIR / f"{sid}.mp3"
    print(f"  → {sid} ...", end="", flush=True)
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    await comm.save(str(out))
    print(f" ✅")

async def main():
    print(f"\n🎙️  EP00 日本語ナレーション (NanamiNeural, +10%)\n")
    for s in SCENES:
        await generate(s)
    print(f"\n✅ 完了 → {OUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
