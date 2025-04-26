import telebot
from telebot import types
import json
import os

# === Настройки ===
TOKEN = '7365948334:AAH8cDVwQk5GYtjSIpzsfuzi423kOf93ATs'  
DATA_FILE = 'profile_data.json'

bot = telebot.TeleBot(TOKEN)

# === Загрузка и сохранение профиля ===

def load_profile():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_profile(profile):
    with open(DATA_FILE, 'w') as f:
        json.dump(profile, f)

profile = load_profile()

# === Вспомогательные функции ===

def get_user_profile(user_id):
    if str(user_id) not in profile:
        profile[str(user_id)] = {
            'rating': 1500,
            'k': 40,
            'history': [],
            'tournament': 'Default Tournament',
            'tournament_changes': []
        }
        save_profile(profile)
    return profile[str(user_id)]

def calculate_change(user_rating, opponent_rating, result, k):
    expected = 1 / (1 + 10 ** ((opponent_rating - user_rating) / 400))
    change = k * (result - expected)
    return round(change, 1), expected

# === Команды ===

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "\u2728 Привет! Я помогу тебе считать твой шахматный рейтинг!\n\nДоступные команды:\n/profile — твой профиль\n/calc — посчитать изменение рейтинга\n/edit — изменить рейтинг или коэффициент\n/tournament — установить турнир\n/history — история турнира\n/reset — сбросить профиль\n/resettournament — сбросить турнир")

@bot.message_handler(commands=['profile'])
def send_profile(message):
    user = get_user_profile(message.from_user.id)
    text = f"📈 Профиль:\nРейтинг: {user['rating']}\nКоэффициент: {user['k']}\nТекущий турнир: {user['tournament']}\n\nИстория турнира:\n"
    if user['tournament_changes']:
        for change in user['tournament_changes']:
            text += f"\u2022 {change}\n"
    else:
        text += "(пока нет партий)"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['edit'])
def edit_profile(message):
    msg = bot.send_message(message.chat.id, "Введите новый рейтинг и коэффициент через пробел. Например: 1500 40")
    bot.register_next_step_handler(msg, save_edited_profile)

def save_edited_profile(message):
    try:
        rating, k = map(int, message.text.split())
        user = get_user_profile(message.from_user.id)
        user['rating'] = rating
        user['k'] = k
        save_profile(profile)
        bot.send_message(message.chat.id, "✅ Профиль обновлен!")
    except:
        bot.send_message(message.chat.id, "\u26a0\ufe0f Неверный формат. Попробуй снова команду /edit.")

@bot.message_handler(commands=['calc'])
def start_calc(message):
    msg = bot.send_message(message.chat.id, "Введите рейтинг соперника:")
    bot.register_next_step_handler(msg, ask_result)

def ask_result(message):
    try:
        opponent_rating = int(message.text)
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        btn1 = types.KeyboardButton('Победа')
        btn2 = types.KeyboardButton('Ничья')
        btn3 = types.KeyboardButton('Поражение')
        markup.add(btn1, btn2, btn3)
        msg = bot.send_message(message.chat.id, "Выберите результат партии:", reply_markup=markup)
        bot.register_next_step_handler(msg, calculate_rating_change, opponent_rating)
    except:
        bot.send_message(message.chat.id, "\u26a0\ufe0f Нужно ввести число. Попробуй снова /calc.")

def calculate_rating_change(message, opponent_rating):
    user = get_user_profile(message.from_user.id)
    result_text = message.text.lower()

    if result_text == 'победа':
        result = 1
    elif result_text == 'ничья':
        result = 0.5
    elif result_text == 'поражение':
        result = 0
    else:
        bot.send_message(message.chat.id, "\u26a0\ufe0f Неверный выбор. Попробуй снова /calc.")
        return

    change, expected = calculate_change(user['rating'], opponent_rating, result, user['k'])
    old_rating = user['rating']
    user['rating'] += round(change)
    change_text = f"\u2694\ufe0f Старый рейтинг: {old_rating}\nОжидание: {round(expected*100,1)}%\nРезультат: {result*100}%\nИзменение: {change}\nНовый рейтинг: {user['rating']}"

    # История турнира
    user['tournament_changes'].append(f"{old_rating} ➔ {user['rating']} ({'+' if change>=0 else ''}{change})")

    save_profile(profile)
    bot.send_message(message.chat.id, change_text, reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['tournament'])
def set_tournament(message):
    msg = bot.send_message(message.chat.id, "Введите название турнира:")
    bot.register_next_step_handler(msg, save_tournament)

def save_tournament(message):
    user = get_user_profile(message.from_user.id)
    user['tournament'] = message.text
    user['tournament_changes'] = []
    save_profile(profile)
    bot.send_message(message.chat.id, f"✅ Турнир '{message.text}' установлен.")

@bot.message_handler(commands=['history'])
def show_history(message):
    user = get_user_profile(message.from_user.id)
    if user['tournament_changes']:
        text = f"🔍 История изменений в турнире '{user['tournament']}':\n"
        for change in user['tournament_changes']:
            text += f"\u2022 {change}\n"
    else:
        text = "(пока нет изменений в турнире)"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['reset'])
def reset_profile(message):
    profile.pop(str(message.from_user.id), None)
    save_profile(profile)
    bot.send_message(message.chat.id, "\u274c Профиль сброшен. Наберите /start для новой настройки.")

@bot.message_handler(commands=['resettournament'])
def reset_tournament(message):
    user = get_user_profile(message.from_user.id)
    user['tournament_changes'] = []
    save_profile(profile)
    bot.send_message(message.chat.id, "♻️ История турнира сброшена.")

# === Запуск ===

print("\u2728 Бот запущен!")
bot.infinity_polling()