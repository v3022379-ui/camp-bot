import os
import sqlite3
import telebot
from telebot import types
import schedule
import time
import threading
from datetime import datetime, timedelta
import requests
from datetime import datetime

# Конфигурация из переменных окружения Railway
BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = int(os.environ['ADMIN_ID'])
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
        "Ставьте 👍, если сегодня было хоть что-то, что вас удивило/развеселило/вдохновило.\n"
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
    
# Команда для полного сброса распределения по группам
@bot.message_handler(commands=['reset_groups'])
def reset_groups_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Нет прав")
        return
    
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # ВАЖНО: Полностью очищаем таблицу пользователей
        cursor.execute("DELETE FROM users")
        
        # Также очищаем состояния пользователей в оперативной памяти
        user_states.clear()
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, "✅ База данных полностью очищена!\n\n"
                             "Теперь:\n"
                             "• В статистике 0 пользователей\n"
                             "• Все участники удалены\n"
                             "• Можно начать регистрацию заново\n\n"
                             "Отправьте /start новым участникам для регистрации!")
        print("🔄 База данных полностью сброшена администратором")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при сбросе базы: {e}")
        print(f"🚨 Ошибка сброса базы: {e}")
        
# Команда для администратора - запуск Капсулы Времени
@bot.message_handler(commands=['start_capsule'])
def start_time_capsule(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return
    
    # Получаем всех участников из базы
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, full_name, squad FROM users WHERE squad IS NOT NULL')
    users = cursor.fetchall()
    conn.close()
    
    # Запускаем капсулу для каждого участника
    for user_id, full_name, squad in users:
        try:
            # Запускаем в отдельном потоке с задержкой между пользователями
            threading.Thread(
                target=send_personal_capsule_questions, 
                args=(user_id, full_name, squad)
            ).start()
            time.sleep(1)  # Задержка 1 секунда между пользователями
        except Exception as e:
            print(f"Ошибка запуска капсулы для {user_id}: {e}")
    
    bot.reply_to(message, f"✅ Капсула времени запущена для {len(users)} участников!")

def send_personal_capsule_questions(user_id, full_name, squad):
    """Отправляет вопросы капсулы в личные сообщения"""
    
    try:
        # Приветственное сообщение
        welcome_msg = (
            f"Привет, {full_name}! 👋\n\n"
            "Наша миссия подходит к концу. 🚀\n"
            "Прежде чем разойтись, давай создадим Капсулу Времени — послание в будущее для тебя самого.\n\n"
            "Я задам 3 вопроса. Ответь на них честно. Через неделю я пришлю эту капсулу тебе.\n\n"
            "Это твоя личная память о нашем путешествии."
        )
        bot.send_message(user_id, welcome_msg)
        time.sleep(2)
        
        # Вопрос 1
        question1 = (
            "📝 ВОПРОС ПЕРВЫЙ:\n\n"
            "«Какой момент за эти 2 дня стал для тебя самым ярким?✨ Опиши в 2-3 предложениях.\n\n"
            "Может, это была та дурацкая шутка, когда все валялись со смеху? Или тихий разговор с незнакомым человеком, который стал другом? Та секунда, когда вы поняли, что победили?»"
        )
        bot.send_message(user_id, question1)
        
        # Сохраняем состояние для отслеживания ответов
        save_user_state(user_id, 'waiting_question_1')
        
    except Exception as e:
        print(f"Не удалось отправить вопросы пользователю {user_id}: {e}")

def save_user_state(user_id, state):
    """Сохраняет состояние пользователя"""
    user_states[user_id] = state

def send_answer_to_admin(user_id, question, answer):
    """Отправляет ответ администратору"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT full_name, squad FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        conn.close()
        
        if user_info:
            full_name, squad = user_info
            admin_message = (
                f"📨 Новый ответ на Капсулу Времени:\n"
                f"👤 Участник: {full_name}\n"
                f"🎯 Отряд: {squad}\n"
                f"❓ Вопрос: {question}\n"
                f"💬 Ответ: {answer}\n"
                f"🕒 Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
            bot.send_message(ADMIN_ID, admin_message)
    except Exception as e:
        print(f"Не удалось отправить ответ администратору: {e}")

def get_user_squad(user_id):
    """Возвращает отряд пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT squad FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_capsule_answer(user_id, answer1, answer2, answer3):
    """Сохраняет ответы в базу данных"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Получаем отряд пользователя
    squad = get_user_squad(user_id)
    
    # Проверяем, есть ли уже запись для этого пользователя
    cursor.execute('SELECT * FROM time_capsules WHERE user_id = ?', (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Обновляем существующую запись
        cursor.execute('''
            UPDATE time_capsules 
            SET question_1 = COALESCE(?, question_1),
                question_2 = COALESCE(?, question_2), 
                question_3 = COALESCE(?, question_3)
            WHERE user_id = ?
        ''', (answer1, answer2, answer3, user_id))
    else:
        # Создаем новую запись
        cursor.execute('''
            INSERT INTO time_capsules (user_id, squad, question_1, question_2, question_3)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, squad, answer1, answer2, answer3))
    
    conn.commit()
    conn.close()

# Обработчик для сохранения ответов на вопросы капсулы
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
    # Сначала проверяем, является ли сообщение ответом на капсулу времени
    user_id = message.from_user.id
    
    if user_id in user_states:
        state = user_states[user_id]
        answer = message.text
        
        if state == 'waiting_question_1':
            # Сохраняем ответ на вопрос 1
            save_capsule_answer(user_id, answer, None, None)
            save_user_state(user_id, 'waiting_question_2')
            
            # Задаем вопрос 2
            question2 = (
                "📝 ВОПРОС ВТОРОЙ:\n\n"
                "«Что ты узнал о себе или о других за эти сумасшедшие 19 часов?⏰\n\n"
                "Может, ты обнаружил, что можешь договориться с кем угодно? Или что самый тихий парень в отряде на самом деле — гений тактики? Или что усталость — это не конец, а начало?»"
            )
            bot.send_message(user_id, question2)
            
            # Отправляем ответ администратору
            send_answer_to_admin(user_id, "Вопрос 1", answer)
            
        elif state == 'waiting_question_2':
            # Сохраняем ответ на вопрос 2
            save_capsule_answer(user_id, None, answer, None)
            save_user_state(user_id, 'waiting_question_3')
            
            # Задаем вопрос 3
            question3 = (
                "📝 ВОПРОС ТРЕТИЙ:\n\n"
                "«Какая одна черта/навык/мысль из этих сборов останется с тобой надолго?\n\n"
                "Одно слово или фраза. Например: «смелость первым заговорить», «доверять команде» или просто «кайфовать от процесса»."
            )
            bot.send_message(user_id, question3)
            
            # Отправляем ответ администратору
            send_answer_to_admin(user_id, "Вопрос 2", answer)
            
        elif state == 'waiting_question_3':
            # Сохраняем ответ на вопрос 3
            save_capsule_answer(user_id, None, None, answer)
            
            # Завершаем диалог
            bot.send_message(
                user_id, 
                "✅ Спасибо! Твои ответы сохранены. Через неделю ты получишь Капсулу Времени с твоими мыслями! ✨"
            )
            
            # Удаляем состояние
            del user_states[user_id]
            
            # Отправляем ответ администратору
            send_answer_to_admin(user_id, "Вопрос 3", answer)
    
    else:
        # Если это не ответ на капсулу, игнорируем сообщение
        # чтобы другие обработчики (команды) могли работать
        pass

# Функция для отправки капсул через неделю
def send_time_capsules():
    """Отправляет капсулы времени через неделю после создания"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Находим капсулы, созданные неделю назад
    week_ago = datetime.now() - timedelta(days=7)
    
    cursor.execute('''
        SELECT tc.user_id, u.full_name, tc.question_1, tc.question_2, tc.question_3, tc.squad
        FROM time_capsules tc
        JOIN users u ON tc.user_id = u.user_id
        WHERE tc.created_date <= ?
    ''', (week_ago,))
    
    capsules = cursor.fetchall()
    
    for user_id, full_name, q1, q2, q3, squad in capsules:
        # Получаем случайные ответы других участников отряда
        cursor.execute('''
            SELECT question_1, question_2, question_3 
            FROM time_capsules 
            WHERE squad = ? AND user_id != ? 
            ORDER BY RANDOM() LIMIT 2
        ''', (squad, user_id))
        
        other_responses = cursor.fetchall()
        
        # Формируем сообщение
        message = f"""Капсула времени из прошлого ⏳

Привет, {full_name}!

Неделю назад ты был на лидерских сборах. Помнишь? Ты и твой безумный отряд.

Как и обещал, возвращаю тебе твои мысли. Сохрани это письмо❤️

ТВОИ ОТВЕТЫ:

· Яркий момент: «{q1 or 'Нет ответа'}»
· Открытие: «{q2 or 'Нет ответа'}»
· Что забрал с собой: «{q3 or 'Нет ответа'}»

А ВОТ ЧТО ВИДЕЛИ ДРУГИЕ (анонимно):
"""
        
        for i, (oq1, oq2, oq3) in enumerate(other_responses, 1):
            if oq1:
                message += f"\n· «{oq1}»"
            if oq2:
                message += f"\n· «{oq2}»"
            if oq3:
                message += f"\n· «{oq3}»"
        
        if not other_responses:
            message += "\n· Пока нет ответов от других участников"
        
        message += "\n\nТвой отряд был космос! 🚀"
        
        try:
            bot.send_message(user_id, message)    
        except Exception as e:
            print(f"Не удалось отправить капсулу пользователю {user_id}: {e}")
    
    conn.close()
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
from flask import Flask
import threading

# Создаем простой веб-сервер для Render
app = Flask('bot-server')

@app.route('/')
def home():
    return "🤖 Бот для 6 отрядов работает!"

@app.route('/health')
def health():
    return "OK"

def keep_alive():
    """Периодически отправляет запросы чтобы сервис не засыпал"""
    while True:
        try:
            # ЗАМЕНИТЕ "your-service-name" на ваш реальный URL из Render
            # Пример: если ваш URL "camp-bot-123.onrender.com", то строка будет:
            # requests.get("https://camp-bot-123.onrender.com/")
            requests.get("https://camp-bot-xna8.onrender.com")
            print(f"🔄 Self-ping sent at {datetime.now()}")
        except Exception as e:
            print(f"⚠️ Self-ping failed: {e}")
        
        # Ждем 10 минут между запросами
        time.sleep(86400)
        
def run_web_server():
    @app.route('/')
    def home():
        return f"🤖 Бот для 6 отрядов работает!<br>Последнее обновление: {datetime.now()}"
    
    @app.route('/health')
    def health():
        return "OK"
    
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    """Функция запуска бота с автоматическим восстановлением"""
    while True:
        try:
            print("🔄 Запускаю бота...")
            init_db()
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
            
        except Exception as e:
            error_msg = str(e)
            print(f"🚨 Ошибка бота: {error_msg}")
            
            # Если это ошибка 409 - ждем дольше
            if "409" in error_msg:
                print("⏳ Обнаружена ошибка 409. Жду 30 секунд перед перезапуском...")
                time.sleep(30)
            else:
                print("⏳ Жду 10 секунд перед перезапуском...")
                time.sleep(10)
            
            print("🔄 Перезапускаю бота...")
            
# Планировщик для отправки капсул времени
def start_capsule_scheduler():
    """Запускает планировщик для ежедневной проверки капсул"""
    while True:
        try:
            now = datetime.now()
            # Проверяем капсулы каждый день в 10:00
            if now.hour == 10 and now.minute == 0:
                send_time_capsules()
                print(f"✅ Проверка капсул выполнена в {now}")
            time.sleep(60)  # Проверяем каждую минуту
        except Exception as e:
            print(f"❌ Ошибка в планировщике капсул: {e}")
            time.sleep(300)

if __name__== "__main__":
    init_db()  # инициализация базы ДО запуска потоков
    # Запускаются все вспомогательные потоки
    # И потом запускается бот
    run_bot()  # в основном потоке
    
    # Запускаем само-пинг в отдельном потоке
    ping_thread = threading.Thread(target=keep_alive)
    ping_thread.daemon = True
    ping_thread.start()
    print("🔁 Само-пинг запущен")

    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    print("🌐 Веб-сервер запущен на порту 8080")

    # Запускаем планировщик капсул времени в отдельном потоке
    capsule_thread = threading.Thread(target=start_capsule_scheduler)
    capsule_thread.daemon = True
    capsule_thread.start()
    print("⏰ Планировщик капсул времени запущен")
    
    # Запускаем бота с автоматическим восстановлением
    run_bot()








