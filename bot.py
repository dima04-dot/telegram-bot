import telebot
import requests
import re
import os
from telebot import types
from flask import Flask
from threading import Thread
import time

# ========== FLASK ДЛЯ PING ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🌌 Планетарный анализатор работает"

@app.route('/ping')
def ping():
    return "pong"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    print("🚀 Запуск Flask сервера...")
    app.run(host='0.0.0.0', port=8080)

# ========== СИСТЕМА ДОСТУПА ==========
# 🔹 ЗАМЕНИТЕ ЭТИ ID НА СВОИ!
ALLOWED_USERS = [1948172415]  # Ваш ID уже есть

def check_access(user_id):
    return user_id in ALLOWED_USERS

def private_access_required(func):
    def wrapper(message):
        if not check_access(message.from_user.id):
            bot.reply_to(message, 
                f"⛔ Доступ запрещен. Ваш ID: `{message.from_user.id}`\n"
                "Запросите доступ у администратора.",
                parse_mode='Markdown')
            return
        return func(message)
    return wrapper

# ========== ТЕЛЕГРАМ БОТ ==========
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEN_API_KEY = os.getenv('GEN_API_KEY') 
GEN_API_URL = os.getenv('GEN_API_URL', 'https://api.gen-api.ru/api/v1/networks/gpt-4o-mini')

if not TELEGRAM_TOKEN or not GEN_API_KEY:
    print("❌ ОШИБКА: Не заданы TELEGRAM_TOKEN или GEN_API_KEY в Render!")
    print("Задайте их в Environment Variables")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ========== КОМАНДА ДЛЯ ПОЛУЧЕНИЯ ID ==========
@bot.message_handler(commands=['myid'])
def show_my_id(message):
    user = message.from_user
    response = (
        f"🆔 *Ваш ID:* `{user.id}`\n"
        f"👤 *Имя:* {user.first_name}\n"
        f"📛 *Юзернейм:* @{user.username if user.username else 'нет'}\n"
        f"✅ *Доступ:* {'ЕСТЬ ✅' if check_access(user.id) else 'НЕТ ❌'}"
    )
    bot.reply_to(message, response, parse_mode='Markdown')

# ========== ВАШ ОРИГИНАЛЬНЫЙ КОД ==========
PLANET_KEYWORDS = {
    "Солнце": ["я", "мне", "меня", "мой", "моя", "моё", "мои",
               "сам", "сама", "само", "сами", "личность",  "индивидуальность", "личный"],
    # ... остальной ваш код НЕ МЕНЯЕТСЯ ...
}

PLANET_SYMBOLS = {
    "Солнце": "☉",
    "Луна": "☽",
    "Меркурий": "☿",
    "Венера": "♀",
    "Марс": "♂",
    "Юпитер": "♃",
    "Сатурн": "♄",
    "Уран": "♅",
    "Нептун": "♆",
    "Плутон": "♇"
}

WORD_TO_PLANET = {}
for planet, words in PLANET_KEYWORDS.items():
    for word in words:
        WORD_TO_PLANET[word] = planet

def analyze_text_locally_by_words(text):
    """Локальный анализ текста по словам"""
    text_lower = text.lower()
    text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
    words = text_clean.split()
    
    result_symbols = []
    
    for word in words:
        if word in WORD_TO_PLANET:
            result_symbols.append(PLANET_SYMBOLS[WORD_TO_PLANET[word]])
            continue
            
        found = False
        for keyword, planet in WORD_TO_PLANET.items():
            if len(keyword) > 3 and len(word) > 3:
                if (keyword in word or word in keyword or
                        keyword.startswith(word[:3]) or word.startswith(keyword[:3])):
                    result_symbols.append(PLANET_SYMBOLS[planet])
                    found = True
                    break
        
        if not found:
            result_symbols.append("    ")
    
    if result_symbols:
        return "    ".join(result_symbols)
    else:
        return "    "

def analyze_text_with_gpt_simple(text):
    """Простой анализ через GPT API"""
    headers = {
        "Authorization": f"Bearer {GEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f'''Определи какие слова соответствуют планетам и покажи эти планеты по порядку:
Текст: "{text}"
выдавай подобные слова, если они пишутся похоже как и в тексте.
Верни ТОЛЬКО символы планет в порядке слов. Если символы слов повторяются, также показывай повторно планеты.'''
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(GEN_API_URL, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if any(symbol in line for symbol in PLANET_SYMBOLS.values()):
                    cleaned = re.sub(r'[^☉☽☿♀♂♃♄♅♆♇\s]', '', line)
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    if cleaned:
                        return cleaned
            return None
        else:
            print(f"GPT API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"GPT Connection Error: {e}")
        return None

def create_keyboard():
    """Создает клавиатуру с кнопками"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    btn_start = types.KeyboardButton("🚀 Старт")
    btn_reset = types.KeyboardButton("🔄 Сброс")
    btn_input = types.KeyboardButton("✍️ Ввести")
    keyboard.add(btn_start, btn_reset, btn_input)
    return keyboard

# ========== ОБРАБОТЧИКИ С ПРОВЕРКОЙ ДОСТУПА ==========
@bot.message_handler(commands=['start'])
@private_access_required
def send_welcome(message):
    """Обработчик команды /start"""
    chat_id = message.chat.id
    keyboard = create_keyboard()
    welcome_text = "🌌 *Планетарный Анализатор* 🌌\n\nНажмите '✍️ Ввести' → напишите предложение\n→ получите символы планет"
    bot.send_message(chat_id, welcome_text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🚀 Старт")
@private_access_required
def handle_start_button(message):
    chat_id = message.chat.id
    start_text = "📝 *Примеры:*\n\n`Я живу дома и ем сладкое`\n→ ☉ ☽ ♀\n\n`Еду на работу за деньгами`\n→ ☿ ♄ ♀\n\n`Хочу купить машину`\n→ ♆ ♀ ☿"
    bot.send_message(chat_id, start_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🔄 Сброс")
@private_access_required
def handle_reset_button(message):
    bot.send_message(message.chat.id, "✅ Готово")

@bot.message_handler(func=lambda message: message.text == "✍️ Ввести")
@private_access_required
def handle_input_button(message):
    bot.send_message(message.chat.id, "📝 *Введите предложение:*", parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
@private_access_required
def handle_text(message):
    chat_id = message.chat.id
    user_text = message.text.strip()
    
    if user_text in ["🚀 Старт", "🔄 Сброс", "✍️ Ввести"]:
        return
    
    if not user_text:
        bot.send_message(chat_id, "Пожалуйста, введите текст.")
        return
    
    bot.send_chat_action(chat_id, 'typing')
    
    result = analyze_text_locally_by_words(user_text)
    
    if result == "—" or "—" in result:
        gpt_result = analyze_text_with_gpt_simple(user_text)
        if gpt_result:
            result = gpt_result
    
    if result:
        result = result.replace("—", "").strip()
        result = re.sub(r'\s+', ' ', result)
    
    if result:
        bot.send_message(chat_id, f"<b>{result}</b>", parse_mode='HTML')
    else:
        bot.send_message(chat_id, " ")
    
    keyboard = create_keyboard()

def setup_bot():
    """Настройка бота перед запуском"""
    print("🔧 Настройка бота...")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        response = requests.get(url, timeout=5)
        if response.json().get("ok"):
            print("✅ Вебхук удален")
    except:
        print("ℹ️ Вебхук не активен")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Запускаем Flask сервер в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Настраиваем и запускаем бота
    setup_bot()
    
    print("=" * 50)
    print("🚀 Запуск Telegram бота...")
    print(f"🤖 Токен: {TELEGRAM_TOKEN[:10]}...")
    print(f"🔑 API ключ: {GEN_API_KEY[:10]}...")
    print(f"👥 Разрешено пользователей: {len(ALLOWED_USERS)}")
    print("🌐 Flask сервер на порту 8080")
    print("📱 Идите в Telegram → найдите бота")
    print("✍️ Напишите /start или /myid")
    print("=" * 50)
    
    try:
        bot.polling(none_stop=True, interval=2, timeout=30)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        time.sleep(10)
