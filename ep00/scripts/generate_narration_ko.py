#!/usr/bin/env python3
"""
EP00 나레이션 v2 — 여자 단독 (SunHi), 문장형 자연스러운 설명체
"""

import asyncio
import edge_tts
from pathlib import Path

OUT_DIR = Path(__file__).parent.parent / "narration" / "ko"
OUT_DIR.mkdir(exist_ok=True)

VOICE = "ko-KR-SunHiNeural"
RATE  = "+10%"

SCENES = [
    {
        "id": "s01_hook",
        "text": "유튜브 마케팅 자료를 보다 보면 CPM, RPM, 블루오션, 포화도 같은 단어들이 쏟아지는데요, 이 단어들을 모르면 어떤 데이터도 제대로 읽히지 않아요. 지금부터 3분이면 다 정리할 수 있어요."
    },
    {
        "id": "s02_cpm",
        "text": "첫 번째는 CPM이에요. CPM이 높으면 당연히 돈을 더 버는 거라고 생각하기 쉬운데, 사실 CPM은 내 돈이 아니에요. 삼성이나 보험회사 같은 광고주가 유튜브에 광고를 실을 때, 그 광고가 1,000번 노출되는 데 드는 비용이 바로 CPM이거든요. 금융 광고 CPM이 높은 이유는, 보험 한 명만 가입해도 수십만 원이 되니까 광고주 입장에서 비용을 더 낼 수 있는 거예요. 반대로 게임 광고는 클릭해도 바로 수익으로 연결되기 어려워서 CPM이 낮은 편이고요."
    },
    {
        "id": "s03_rpm",
        "text": "두 번째는 RPM이에요. CPM이랑 비슷하게 생겼지만 완전히 달라요. RPM이 진짜 내 통장에 들어오는 돈이거든요. 유튜브가 중간에서 수수료 45%를 가져가고, 광고를 건너뛴 시청자도 있으니까, CPM이 45달러라도 실제로 내 통장에는 12달러에서 15달러 정도밖에 안 들어와요. 생각보다 훨씬 적죠? 그래서 CPM보다 RPM을 봐야 해요. 진짜 내 수익이 여기 있거든요."
    },
    {
        "id": "s04_faceless",
        "text": "세 번째는 Faceless예요. 얼굴 없이 목소리만으로, 혹은 화면이랑 자막만으로 운영하는 채널을 말해요. 얼굴이 나오는 채널은 그 사람 자체가 채널이 되기 때문에, 쉬면 채널도 같이 쉬어야 해요. 반면 Faceless 채널은 자동화가 가능해서, 내가 자는 동안에도 영상이 올라갈 수 있어요."
    },
    {
        "id": "s05_ocean",
        "text": "네 번째와 다섯 번째는 레드오션과 블루오션이에요. 블루오션은 아직 경쟁자가 없는 빈 시장이고, 레드오션은 이미 잘하는 사람들이 자리를 다 잡아버린 시장이에요. 당연히 블루오션에 들어가야 할 것 같지만, 문제가 있어요. 블루오션은 오래 안 가거든요. 알려지는 순간 경쟁자들이 몰려와서 금방 레드오션이 돼버리니까, 타이밍이 중요해요."
    },
    {
        "id": "s06_saturation",
        "text": "그 타이밍을 어떻게 알 수 있을까요? 바로 포화도를 보면 돼요. 그 시장이 얼마나 꽉 찼는지를 보여주는 건데, 중요한 건 지금 숫자가 아니라 방향이에요. 포화도가 지금 낮더라도 빠르게 차오르고 있으면 6개월 후엔 레드오션이 될 수 있거든요. 현재 상태만 보면 안 되고, 방향을 같이 봐야 해요."
    },
    {
        "id": "s07_outro",
        "text": "지금까지 여섯 가지 용어를 알아봤어요. CPM은 광고주가 유튜브에 내는 돈, RPM은 내 통장에 실제로 들어오는 돈, Faceless는 얼굴 없이 운영하는 채널 방식, 레드오션은 경쟁이 심한 시장, 블루오션은 아직 빈 시장, 그리고 포화도는 그 시장이 얼마나 찼는지예요. 이제 본편 볼 준비 되셨죠? 다음 편부터 40개 카테고리를 하나씩 같이 알아가볼게요."
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
    print(f"\n🎙️  EP00 나레이션 v2 (여 단독, +5%)\n")
    await asyncio.gather(*[generate(s) for s in SCENES])
    print(f"\n✅ 완료 → {OUT_DIR}/")

if __name__ == "__main__":
    asyncio.run(main())
