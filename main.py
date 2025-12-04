import asyncio
import os
import re
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# === O'Z MA'LUMOTLARINGIZ ===
    
# =============================

openai.api_key = OPENAI_API_KEY
bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# temp papka
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# YouTube'dan yuklash (eng tez va barqaror sozlamalar)
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'extractaudio': True,
    'audioformat': 'mp3',
}

# Tozalash funksiyasi
def safe_filename(name):
    return re.sub(r'[^\w\-_\. ]', '_', name)[:100]

# GPT'dan 10 ta qo'shiq olish (eng aniq prompt)
async def get_songs(user_text: str) -> list[str]:
    prompt = f"""
Foydalanuvchi shunday his qilmoqda: "{user_text}"

Shu hissiyotga 100% mos keladigan 10 ta qo'shiq nomi + ijrochisini aniq yoz.
Til: o'zbek, rus, turk yoki inglizcha (foydalanuvchi tiliga qarab).
Faqat shu formatda, boshqa hech narsa yozma:

1. Qo'shiq nomi - Ijrochi
2. Qo'shiq nomi - Ijrochi
...
10. Qo'shiq nomi - Ijrochi
"""

    try:
        response = await openai.chat.completions.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=600
        )
        text = response.choices[0].message.content
        songs = []
        for line in text.split('\n'):
            if '.' in line and '-' in line:
                song = line.split('-', 1)[-1].strip()
                if song and len(song) > 3:
                    songs.append(song)
        return songs[:10]
    except Exception as e:
        print("GPT xatosi:", e)
        return []

# Bitta qo'shiqni yuklab yuborish (eng tezkor)
async def send_song(chat_id: int, query: str, num: int):
    status_msg = await bot.send_message(chat_id, f"<b>{num}/10</b> yuklanmoqda...", parse_mode="HTML")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            title = info['entries'][0]['title']
            original_file = ydl.prepare_filename(info['entries'][0]).rsplit(".", 1)[0] + ".mp3"
            
            safe_title = safe_filename(title)
            final_file = f"{TEMP_DIR}/{safe_title}.mp3"
            if os.path.exists(original_file):
                os.rename(original_file, final_file)

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"<b>{num}/10</b> Tayyorlanmoqda: <i>{title}</i>",
                parse_mode="HTML"
            )

            audio = FSInputFile(final_file)
            await bot.send_audio(
                chat_id,
                audio,
                caption=f"<b>{num}. {title}</b>",
                title=title
            )
            os.remove(final_file)
            
    except Exception as e:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"{num}/10 – topilmadi: <code>{query}</code>",
            parse_mode="HTML"
        )
    finally:
        await asyncio.sleep(1)

# Tugmalar
def get_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Yana 10 ta qo'shiq", callback_data="again")],
        [InlineKeyboardButton("Yangi kayfiyat", callback_data="new")]
    ])

# /start
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        "<b>Salom! Kayfiyat bo'yicha qo'shiq topuvchi bot</b>\n\n"
        "O'zingiz yozing – men darrov <b>10 ta qo'shiq MP3</b> qilib yuboraman!\n\n"
        "<i>Misol:</i>\n"
        "• Yigitim tashlab ketdi, sog'inyapman\n"
        "• Bugun juda baxtliman\n"
        "• Turkcha xafa qo'shiqlar kerak",
        reply_markup=get_menu()
    )

# Har qanday matn
@dp.message()
async def handle_mood(msg: types.Message):
    text = msg.text.strip()
    if len(text) < 6:
        await msg.answer("Ko'proq yozing, iltimos")
        return

    await msg.answer("Hissiyotingiz tahlil qilinmoqda...")
    songs = await get_songs(text)

    if not songs:
        await msg.answer("Kechirasiz, qo'shiq topa olmadim. Yana urining!")
        return

    await msg.answer(f"<b>{len(songs)} ta qo'shiq topdim!</b> Yuklayapman...", reply_markup=get_menu())
    
    # Parallel yuklash emas – Telegram limiti uchun ketma-ket
    for i, song in enumerate(songs, 1):
        await send_song(msg.chat.id, song, i)
        await asyncio.sleep(20)  # 3 ta xabar/sekund limitdan himoya

    await msg.answer("Hammasi tayyor! Yana xohlasangiz – yozing", reply_markup=get_menu())

# Tugmalar
@dp.callback_query(lambda c: c.data in ["again", "new"])
async def buttons(call: types.CallbackQuery):
    if call.data == "again":
        await call.message.answer("Yana qanday kayfiyatdasiz? Yozing – yana 10 ta yuboraman!")
    else:
        await call.message.answer("Yangi kayfiyatni yozing:")
    await call.answer()

# Ishga tushirish
async def main():
    print("Bot ishga tushdi! Foydalanuvchi yozishi bilan 10 ta MP3 keladi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
