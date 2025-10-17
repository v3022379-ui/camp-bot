import os
import sqlite3
import telebot
from telebot import types
import schedule
import time
import threading
from datetime import datetime, timedelta

# Конфигурация из переменных окружения Railway
BOT_TOKEN = os.environ['8364795745:AAFua_2qWp8jp3jB70I3ZkAMCAB0NWIDFW0']
ADMIN_ID = int(os.environ['1320734792'])
DATABASE_NAME = 'camp_bot.db'

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}


# Состояния для капсулы времени
user_states = {}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            squad INTEGER DEFAULT NULL,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_capsules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            squad INTEGER,
            question_1 TEXT,
            question_2 TEXT,
            question_3 TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT squad FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        squad = result[0]
        if squad:
            squad_chat_link = get_squad_chat_link(squad)
            bot.send_message(
                message.chat.id,
                f"🎉 Жеребьевка завершена! Ты в ОТРЯДЕ №{squad}\n\n"
                f"Переходи в чат отряда: {squad_chat_link}\n\n"
                f"Представься ребятам и готовься к приключениям! 🔥"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"Привет, {full_name}! 👋\n"
                f"Ты успешно зарегистрирован на жеребьевку по отрядам! 🎪\n"
                f"Жди команды от организатора."
            )
    else:
        cursor.execute(
            'INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)',
            (user_id, username, full_name)
        )
        conn.commit()
        
        bot.send_message(
            message.chat.id,
            f"Привет, {full_name}! 👋\n"
            f"Ты успешно зарегистрирован на жеребьевку по отрядам! 🎪\n"
            f"Жди команды от организатора."
        )
    
    conn.close()

# Команда /getid (только для админа)
@bot.message_handler(commands=['getid'])
def get_chat_id(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Эта команда только для администратора")
        return
        
    chat_id = message.chat.id
    chat_type = message.chat.type
    chat_title = message.chat.title or "Личные сообщения"
    
    bot.reply_to(
        message,
        f"📋 Информация о чате:\n"
        f"• Название: {chat_title}\n"
        f"• Тип: {chat_type}\n"
        f"• ID чата: `{chat_id}`",
        parse_mode='Markdown'
    )

# Команда /distribute
@bot.message_handler(commands=['distribute'])
def distribute_squads(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Нет прав")
        return
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, full_name FROM users WHERE squad IS NULL')
    users = cursor.fetchall()
    
    if not users:
        bot.reply_to(message, "Нет пользователей для распределения.")
        conn.close()
        return
    
    NUM_SQUADS = 6
    for i, (user_id, full_name) in enumerate(users):
        squad_number = (i % NUM_SQUADS) + 1
        cursor.execute(
'UPDATE users SET squad = ? WHERE user_id = ?',
            (squad_number, user_id)
        )
        
        squad_chat_link = get_squad_chat_link(squad_number)
        try:
            bot.send_message(
                user_id,
                f"🎉 Жеребьевка завершена! Ты в ОТРЯДЕ №{squad_number}\n\n"
                f"Переходи в чат отряда: {squad_chat_link}"
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Распределение завершено! Создано {NUM_SQUADS} отрядов.")

# Команда /morning
@bot.message_handler(commands=['morning'])
def morning_command(message):
    print("🔔 Команда /morning вызвана")
    
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Нет прав")
        return

    morning_message = (
        "Доброе утро, команда! ☀️ Всем срочно на борт!\n"
        "Система распознала низкий уровень утренней мотивации. Для разблокировки специальной миссии требуется активация котикового модуля🐾\n"
        "Принцип действия: все, кто отправит стикер с котиком размораживают мой секретный рецепт виртуальных оладушек! 🥞✨"
    )
    
    send_to_all_squad_chats(morning_message)
    bot.reply_to(message, "✅ Утреннее сообщение отправлено!")

# Команда /evening
@bot.message_handler(commands=['evening'])
def evening_command(message):
    print("🔔 Команда /evening вызвана")
    
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Нет прав")
        return

    evening_message = (
        "Ставьте +, если сегодня было хоть что-то, что вас удивило/развеселило/вдохновило.\n"
        "А теперь ставьте ❤️, если вы гордитесь тем, что сделали сегодня для отряда.\n\n"
        "Думаю, у нас тут собралась команда с большим сердцем!"
    )
    
    send_to_all_squad_chats(evening_message)
    bot.reply_to(message, "✅ Вечернее сообщение отправлено!")

# Команда /stats
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Нет прав")
        return
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT squad, COUNT(*) FROM users WHERE squad IS NOT NULL GROUP BY squad')
    squad_stats = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    report = f"📊 Статистика (всего: {total_users}):\n"
    for squad, count in squad_stats:
        report += f"Отряд {squad}: {count} человек\n"
    
    conn.close()
    bot.reply_to(message, report)

# Вспомогательные функции
def get_squad_chat_link(squad_number):
    links = {
        1: "https://t.me/+mcWOgdDVjuIzNDYy",
        2: "https://t.me/+65crPBlnZQVlYTIy", 
        3: "https://t.me/+ZHyKA9ZX1FQ1MjY6",
        4: "https://t.me/+--6MKDxUXIRiNDI6",
        5: "https://t.me/+Jt89U6exSuk2YzYy",
        6: "https://t.me/+LR6BtyXuVo9lNTgy",
    }
    return links.get(squad_number, "Ссылка будет позже")

def get_squad_chat_id(squad_number):
    squad_chats = {
        1: -4764309202,
        2: -4614231470,
        3: -4965369333,
        4: -4961778285,
        5: -4960496927,
        6: -4800228594,
    }
    return squad_chats.get(squad_number)

def send_to_all_squad_chats(message_text):
    print(f"📨 Отправляю сообщение в чаты")
    
    for squad in range(1, 7):
        chat_id = get_squad_chat_id(squad)
        if chat_id:
            try:
                bot.send_message(chat_id, message_text)
                print(f"✅ Отправлено в отряд {squad}")
            except Exception as e:
                print(f"❌ Ошибка в отряде {squad}: {e}")
        else:
            print(f"⚠️ Нет ID для отряда {squad}")

# Запуск бота
if __name__ == "__main__":
    init_db()
    print("🚀 Бот для 6 отрядов запущен на Railway!")

    bot.infinity_polling()
