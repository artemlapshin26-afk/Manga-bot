import telebot
import requests
from io import BytesIO
import urllib.parse
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
import threading
import random

# --- НАСТРОЙКИ ---
TOKEN = '8544559089:AAElVSZP62-MIKoyFhjdJPNTVtLDd_ABu0o'
DONATE_LINK = "https://www.donationalerts.com/r/temohagame"
ADMIN_ID = 760757633

bot = telebot.TeleBot(TOKEN)

# --- 🗄️ БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY,
                  tier TEXT DEFAULT 'free',
                  generations_today INTEGER DEFAULT 0,
                  total_generations INTEGER DEFAULT 0,
                  last_use DATE,
                  subscribe_end DATE)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    today = datetime.now().date()
    
    if not user:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 (user_id, "free", 0, 0, today, None))
        conn.commit()
        user = (user_id, "free", 0, 0, today, None)
    else:
        if user[5]:
            sub_end = datetime.strptime(str(user[5]), "%Y-%m-%d").date()
            if sub_end < today:
                c.execute("UPDATE users SET tier = 'free', subscribe_end = NULL WHERE user_id = ?", (user_id,))
                conn.commit()
        if str(user[4]) != str(today):            c.execute("UPDATE users SET generations_today = 0, last_use = ? WHERE user_id = ?", (today, user_id))
            conn.commit()
    
    conn.close()
    return user

def use_generation(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET generations_today = generations_today + 1, total_generations = total_generations + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def upgrade_user(user_id, tier, days=30):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    end_date = datetime.now() + timedelta(days=days)
    c.execute("UPDATE users SET tier = ?, subscribe_end = ? WHERE user_id = ?", (tier, end_date.date(), user_id))
    conn.commit()
    conn.close()

init_db()

# --- 🌐 СЕРВЕР ---
app = Flask('')
@app.route('/')
def home():
    return "MangaGen Bot is running!"
def run():
    app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run, daemon=True).start()

# --- 🎨 ГЕНЕРАЦИЯ ---
def generate_image(prompt, quality="normal"):
    style = "solo leveling style, manhwa, dark fantasy, detailed"
    if quality == "hd":
        style += ", 8k, ultra hd, masterpiece"
    full_prompt = f"{prompt}, {style}"
    size = 1024 if quality == "normal" else 2048
    seed = random.randint(1, 999999999)
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_prompt)}"
    url += f"?width={size}&height={size}&nologo=true&seed={seed}"
    try:
        response = requests.get(url, timeout=180)
        if response.status_code == 200 and len(response.content) > 1000:
            return response.content
    except: pass
    return None

# --- 📱 КЛАВИАТУРЫ ---def main_kb(tier):
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)
    if tier == "free":
        kb.add(telebot.types.InlineKeyboardButton("🎨 Генерация (SD)", callback_data="gen_free"))
        kb.add(telebot.types.InlineKeyboardButton("⭐ Купить VIP", callback_data="buy_vip"))
        kb.add(telebot.types.InlineKeyboardButton("💎 Купить PREMIUM", callback_data="buy_prem"))
        kb.add(telebot.types.InlineKeyboardButton("💝 Поддержать", callback_data="donate"))
        kb.add(telebot.types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    elif tier == "vip":
        kb.add(telebot.types.InlineKeyboardButton("🎨 HD Генерация", callback_data="gen_vip"))
        kb.add(telebot.types.InlineKeyboardButton("💎 Купить PREMIUM", callback_data="buy_prem"))
        kb.add(telebot.types.InlineKeyboardButton("💝 Поддержать", callback_data="donate"))
        kb.add(telebot.types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    else:
        kb.add(telebot.types.InlineKeyboardButton("🎨 Ultra HD (Безлимит)", callback_data="gen_prem"))
        kb.add(telebot.types.InlineKeyboardButton("💝 Поддержать", callback_data="donate"))
        kb.add(telebot.types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    return kb

# --- 📱 КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    tier = user[1]
    emoji = "🆓" if tier == "free" else "⭐" if tier == "vip" else "💎"
    tier_name = "Free" if tier == "free" else "VIP" if tier == "vip" else "PREMIUM"
    text = f"{emoji} **Генератор Манхвы | {tier_name}**\n\n🎨 Рисую в стиле Solo Leveling!\n\n📊 **Твои лимиты:**\n• Сегодня: {user[2]}\n• Всего: {user[3]}\n• Тариф: {tier_name}\n\n👇 Нажми кнопку:"
    bot.reply_to(message, text, reply_markup=main_kb(tier))

@bot.message_handler(commands=['vip'])
def vip_info(message):
    bot.reply_to(message, "⭐ **VIP**\n\n💰 300₽/мес\n✅ 100 генераций/день\n✅ HD качество")

@bot.message_handler(commands=['premium'])
def prem_info(message):
    bot.reply_to(message, "💎 **PREMIUM**\n\n💰 500₽/мес\n✅ БЕЗЛИМИТ\n✅ Ultra HD")

@bot.message_handler(commands=['donate'])
def donate_menu(message):
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
    bot.reply_to(message, "💝 **Поддержать проект**\n\nЛюбой донат помогает!", reply_markup=kb)

# --- 🔘 КНОПКИ ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user = get_user(call.from_user.id)
    tier = user[1]
    
    if call.data == "buy_vip":        msg = f"⭐ **VIP (300₽)**\n\n1. Перейди по ссылке\n2. Укажи 300₽\n3. В комментарии: `{call.from_user.id}`"
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
    
    elif call.data == "buy_prem":
        msg = f"💎 **PREMIUM (500₽)**\n\n1. Перейди по ссылке\n2. Укажи 500₽\n3. В комментарии: `{call.from_user.id}`"
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💳 Оплатить", url=DONATE_LINK))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="Markdown")
    
    elif call.data == "donate":
        donate_menu(call.message)
    
    elif call.data == "stats":
        text = f"📊 **Статистика**\n\nСегодня: {user[2]}\nВсего: {user[3]}\nТариф: {tier.upper()}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    
    elif call.data == "gen_free":
        if user[2] >= 10:
            bot.answer_callback_query(call.id, "❌ Лимит исчерпан!", show_alert=True)
        else:
            msg = bot.send_message(call.message.chat.id, "✏️ **Что нарисовать?**")
            bot.register_next_step_handler(msg, process_image, "normal", call.from_user.id)
    
    elif call.data == "gen_vip":
        if user[2] >= 100:
            bot.answer_callback_query(call.id, "❌ Лимит исчерпан!", show_alert=True)
        else:
            msg = bot.send_message(call.message.chat.id, "✏️ **Что нарисовать (HD)?**")
            bot.register_next_step_handler(msg, process_image, "hd", call.from_user.id)
    
    elif call.data == "gen_prem":
        msg = bot.send_message(call.message.chat.id, "✏️ **Что нарисовать (Ultra HD)?**")
        bot.register_next_step_handler(msg, process_image, "hd", call.from_user.id)

def process_image(message, quality, user_id):
    if not message.text: return
    user = get_user(user_id)
    if user[1] == "free" and user[2] >= 10:
        bot.reply_to(message, "❌ Лимит исчерпан!")
        return
    if user[1] == "vip" and user[2] >= 100:
        bot.reply_to(message, "❌ Лимит исчерпан!")
        return
    
    status = bot.reply_to(message, "⏳ Генерирую...")
    img = generate_image(message.text, quality)
    
    if img:        use_generation(user_id)
        new_user = get_user(user_id)
        left = "♾️" if user[1] == "premium" else (100 - new_user[2]) if user[1] == "vip" else (10 - new_user[2])
        cap = f"✨ **ГОТОВО!**\n\n📝 {message.text}\n🎨 Качество: {quality.upper()}\n📊 Осталось: {left}"
        bot.send_photo(user_id, BytesIO(img), caption=cap)
        bot.delete_message(user_id, status.message_id)
    else:
        bot.edit_message_text("❌ Ошибка", user_id, status.message_id)

# --- 🛠 АДМИН ---
@bot.message_handler(commands=['upgrade'])
def admin_upgrade(message):
    if message.chat.id != ADMIN_ID: return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        tier = parts[2].lower()
        upgrade_user(uid, tier)
        bot.send_message(uid, f"✅ Аккаунт улучшен до **{tier.upper()}**!")
        bot.reply_to(message, f"✅ {uid} получил {tier.upper()}")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

print("🚀 Бот запущен!")
bot.polling(none_stop=True)
