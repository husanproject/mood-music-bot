import asyncio
import os
import re
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Kalitlar topilmadi! Koyeb’da Variables tekshiring.")

openai.api_key = OPENAI_API_KEY
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
    'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
    'quiet': True,
}

def safe_filename(name): return re.sub(r'[^\w\-_\. ]', '_', name)[:100]

async def get_songs(text):
    prompt = f'"{text}" — shu kayfiyatga 10 ta qo‘shiq (nomi - ijrochi):'
    resp = await openai.chat.completions.acreate(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=500)
    songs = []
    for line in resp.choices[0].message.content.split('\n'):
        if '-' in line: songs.append(line.split('-',1)[-1].strip())
    return songs[:10]

async def send_song(chat_id, query, i):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            title = info['entries'][0]['title']
            orig = ydl.prepare_filename(info['entries'][0]).rsplit('.',1)[0] + ".mp3"
            safe = f"{TEMP_DIR}/{safe_filename(title)}.mp3"
            if os.path.exists(orig): os.rename(orig, safe)
            await bot.send_audio(chat_id, FSInputFile(safe), caption=f"{i}. {title}")
            os.remove(safe)
    except: await bot.send_message(chat_id, f"{i}. Topilmadi: {query}")

@dp.message(Command("start"))
async def start(m): await m.answer("Kayfiyatingizni yozing – 10 ta MP3 yuboraman!")

@dp.message()
async def mood(m):
    if len(m.text) < 6: return await m.answer("Ko‘proq yozing!")
    await m.answer("⏳ Tahlil qilyapman...")
    songs = await get_songs(m.text)
    if not songs: return await m.answer("Topa olmadim 😔")
    await m.answer(f"🎧 {len(songs)} ta qo‘shiq yuklanmoqda...")
    for i, s in enumerate(songs, 1):
        await send_song(m.chat.id, s, i)
        await asyncio.sleep(20)
    await m.answer("Tayyor! Yana yozing ❤️")

async def main():
    print("Bot Koyeb’da ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
