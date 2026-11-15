# -*- coding: utf-8 -*-
"""
نسخه‌ی مخصوص Render: سلف‌بات سروش پلاس + وب‌سرور کوچیک + پینگ خودکار

- سشن از Environment Variable به اسم SESSION_STRING خونده می‌شه
- هر ۱۰ دقیقه سرویس به آدرس عمومی خودش درخواست می‌زنه تا Render نخوابونتش
"""

import os
import asyncio
import random
import time

from aiohttp import web, ClientSession, ClientTimeout
from splusthon import SoroushClient, events
from splusthon.sessions import StringSession

SESSION_STRING = os.environ.get("SESSION_STRING", "")
PORT = int(os.environ.get("PORT", "10000"))
# Render خودش این متغیر رو با آدرس عمومی سرویس پر می‌کنه
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

PING_INTERVAL = 10 * 60      # ثانیه
COOLDOWN_PER_USER = 20
DELAY_RANGE = (1.5, 4.0)

GENERIC = [
    "این رو با کدوم مغزت تایپ کردی؟ 😐",
    "جدی؟ این بهترین چیزی بود که به ذهنت رسید؟",
    "ممنون که نظرت رو دادی، ولی کسی نپرسیده بود 🙂",
    "آفرین، حالا برو یه کم فکر کن بعد بیا.",
    "این جمله رو باید قاب کنن بزنن به دیوار خنده‌دارترین‌ها 😂",
    "اگه سکوت طلا بود، تو الان فقیرترین آدم دنیا بودی.",
    "نصف حرفت رو نفهمیدم، نصف دیگه‌ش رو هم نخواستم.",
    "کاش خنده‌دار بودنت به اندازه‌ی اعتماد به نفست بود 😌",
    "ریپلای زدی که چی بشه؟ ثواب داره؟",
    "تلاشت قشنگ بود، نتیجه‌ش نه.",
]

KEYWORDS = {
    ("😂", "🤣", "هاها", "خخخ", "هه"): [
        "خندیدنت از خود حرفت خنده‌دارتره 😂",
        "اینقدر نخند، دندونات خشک می‌شه.",
    ],
    ("نه", "غلطه", "اشتباه"): [
        "اشتباه؟ تو که اشتباه خودتی، بقیه رو ولش کن.",
        "نظر شما محترم، فقط غلطه 🙂",
    ],
    ("چرا", "چطور", "چی", "؟", "?"): [
        "سوال خوبیه، ولی جوابش رو گوگل بهتر می‌دونه، منم حوصله ندارم.",
        "این‌همه سوال، یه ذره هم فکر کن!",
    ],
    ("سلام", "hi", "hello"): [
        "سلام. حالا که اومدی، یه چیز با مزه بگو 😏",
    ],
    ("احمق", "بی‌شعور", "مزخرف", "ضایع"): [
        "تعریف از خودت رو همین‌جا تموم کن 😌",
        "اینا رو از آینه یاد گرفتی؟",
    ],
}

last_reply_time = {}


def pick_reply(text):
    low = (text or "").lower()
    for keys, replies in KEYWORDS.items():
        if any(k in low for k in keys):
            return random.choice(replies)
    return random.choice(GENERIC)


client = SoroushClient(StringSession(SESSION_STRING))


@client.on(events.NewMessage(incoming=True))
async def on_message(event):
    try:
        if not event.is_reply:
            return
        replied = await event.get_reply_message()
        if not replied or not replied.out:
            return
        sender = await event.get_sender()
        if sender is None or getattr(sender, "bot", False):
            return

        now = time.time()
        uid = sender.id
        if now - last_reply_time.get(uid, 0) < COOLDOWN_PER_USER:
            return
        last_reply_time[uid] = now

        await asyncio.sleep(random.uniform(*DELAY_RANGE))
        await event.reply(pick_reply(event.raw_text))
    except Exception as e:
        print("خطا:", e, flush=True)


# ---------- وب‌سرور و پینگ ----------
async def health(request):
    return web.Response(text="ok")


async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    print(f"وب‌سرور روی پورت {PORT} بالا اومد", flush=True)


async def keep_alive():
    if not PUBLIC_URL:
        print("RENDER_EXTERNAL_URL تنظیم نشده؛ پینگ خودکار غیرفعاله.", flush=True)
        return
    timeout = ClientTimeout(total=30)
    while True:
        await asyncio.sleep(PING_INTERVAL)
        try:
            async with ClientSession(timeout=timeout) as s:
                async with s.get(PUBLIC_URL) as r:
                    print("ping:", r.status, flush=True)
        except Exception as e:
            print("ping خطا:", e, flush=True)


async def main():
    if not SESSION_STRING:
        raise SystemExit("متغیر SESSION_STRING تنظیم نشده.")
    await start_web()
    asyncio.create_task(keep_alive())
    await client.start()
    me = await client.get_me()
    print("بات فعاله:", getattr(me, "first_name", ""), flush=True)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
