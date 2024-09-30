import telebot
from telebot import types
import threading
import sqlite3
from datetime import datetime
import time
import base64
import requests

import config_tg

admins = config_tg.admins #Администраторы бота

"""API keys"""
API_TOKEN = config_tg.API_TOKEN
CONVERTIO_API_KEY = config_tg.CONVERTIO_API_KEY
CONVERTIO_API_URL = config_tg.CONVERTIO_API_URL

bot = telebot.TeleBot(API_TOKEN)
start_time = datetime.now()


"""Словари для использования инлайн-кнопок"""

# Словарь с предметами для каждого семестра
subjects_by_semester = config_tg.subjects_by_semester

# Словарь с ссылками для каждого предмета
links_by_subject = config_tg.links_by_subject

"""База данных"""

# Функция для создания таблицы пользователей, если её нет
def create_users_table():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT)''')
    conn.commit()
    conn.close()

# Функция для регистрации нового пользователя
def register_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                   (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

# Функция для проверки, зарегистрирован ли пользователь
def is_registered(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Создадим таблицу при запуске бота

create_users_table()

# Функция для подсчета количества зарегистрированных пользователей
def count_registered_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Функция для получения списка всех зарегистрированных пользователей
def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, first_name FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

"""Администраторские команды"""

"""Проверка статуса работы бота"""

def send_status():
    while True:
        try:
            time_sleep = 1800 # Время проверки статуса работы
            current_time = datetime.now()
            uptime = current_time - start_time
            uptime_str = str(uptime).split('.')[0]  # Убираем микросекунды
            start_time_str = start_time.strftime('%H:%M:%S')
            message = (f"Статус: <b>работает</b>\n"
                       f"Время работы: <b>{uptime_str}</b>\n"
                       f"Следующая проверка через: <b>{time_sleep} сек</b>\n"
                       f"Текущее время: <b>{current_time.strftime('%H:%M:%S')}</b>\n"
                       f"Время старта: <b>{start_time_str}</b>\n")
            for admin_id in admins:
                bot.send_message(admin_id, message, parse_mode='HTML')
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
            for admin_id in admins:
                error_bot = f'''{str(e)}'''
                formatted_code = f"<pre><code>{error_bot}</code></pre>"
                bot.send_message(admin_id, f"Ошибка при запуске бота:{formatted_code}", parse_mode='HTML')
        time.sleep(time_sleep)

# Запускаем поток для отправки состояния
status_thread = threading.Thread(target=send_status)
status_thread.daemon = True
status_thread.start()

"""Работа с администраторской командой /count_users"""

# Обработчик команды /count_users для вывода количества зарегистрированных пользователей
@bot.message_handler(commands=['count_users'])
def count_users(message):
    # Проверяем, является ли отправитель сообщения владельцем бота
    if str(message.from_user.id) in admins:
        users = get_all_users()

        if not users:
            bot.send_message(message.chat.id, "Нет зарегистрированных пользователей.")
        else:
            response = f"Количество зарегистрированных пользователей: {len(users)}\n\n"
            response += "Список пользователей:\n\n"
            messages = []
            current_message = response

            for user_id, first_name in users:
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute('SELECT username FROM users WHERE id=?', (user_id,))
                username = cursor.fetchone()[0]
                conn.close()

                user_info = f"username: @{username}, имя: {first_name}, id:{user_id}\n\n"

                # Проверяем длину текущего сообщения и добавляем в очередь, если слишком длинное
                if len(current_message) + len(user_info) > 4000:  # оставляем небольшой запас
                    messages.append(current_message)
                    current_message = user_info
                else:
                    current_message += user_info

            messages.append(current_message)

            for msg in messages:
                bot.send_message(message.chat.id, msg)
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


"""Работа с администраторской командой /message"""

# Обработчик команды /message
@bot.message_handler(commands=['message'])
def admin_command(message):

    # Проверяем, является ли отправитель администратором
    if str(message.from_user.id) in admins:
        # Проверяем, есть ли текст после команды
        if len(message.text.split()) > 1:
            # Получаем текст сообщения от администратора
            text = message.text.split(maxsplit=1)[1]

            # Отправляем сообщение всем пользователям бота
            send_to_all_users(text)
        else:
            bot.reply_to(message, "Вы не ввели текст для отправки!")
    else:
        bot.reply_to(message, "Вы не являетесь администратором!")


# Функция для отправки сообщения всем пользователям бота
def send_to_all_users(text):
    # Получаем список всех зарегистрированных пользователей
    users = get_all_users()

    # Отправляем сообщение каждому пользователю
    for user_id, _ in users:
        try:
            bot.send_message(user_id, text, parse_mode='HTML')
        except telebot.apihelper.ApiException as e:
            if e.result.status_code == 403:
                print(f"Пользователь id:{user_id} заблокировал бота. Сообщение не отправлено.")
            else:
                print(f"Произошла ошибка при отправке сообщения пользователю id{user_id}: {e}")
        except Exception as e:
            print(f"Произошла ошибка при отправке сообщения пользователю id{user_id}: {e}")

"""Узнать id пользователя"""

@bot.message_handler(func=lambda message: message.text.lower() == 'id')
def send_id(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"Ваш ID: {user_id}")


"""Описание команды /info"""

@bot.message_handler(commands=['info'])
def help_user(message):
    button_help_1 = types.InlineKeyboardMarkup()
    button_help_1.row(types.InlineKeyboardButton('Поддержка', callback_data='Поддержка'))
    button_help_1.row(types.InlineKeyboardButton('Функционал бота', callback_data='Функционал бота'))
    button_help_1.row(types.InlineKeyboardButton('Предложить материал', callback_data='Предложить материал'))

    # Отправляем и кнопки, и картинку
    photo_path = 'zayavka.jpg'
    caption = f'{message.from_user.first_name}, вот, что я могу предложить:'
    with open(photo_path, 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=button_help_1)

@bot.callback_query_handler(func=lambda call: call.data == "Поддержка")
def handle_support(call):
    photo_error_path="Eror_ph.jpg"
    support_message = "Возникли трудности с работой бота? Нашли ошибку, недочет и т.п? " \
                      "Вы можете обратиться к <a href='https://t.me/grandmaslippers'><i>администратору</i></a>."
    with open(photo_error_path, 'rb') as photo:
        bot.send_photo(call.message.chat.id, photo, caption=support_message,parse_mode='HTML')



@bot.callback_query_handler(func=lambda call: call.data == "Функционал бота")
def handle_support(call):

    photo_path = 'botman-3.png'
    caption_path1 = config_tg.caption_path1
    caption_part2 = config_tg.caption_part2
    caption_part3 = config_tg.caption_part3
    caption_part4 = config_tg.caption_part4

    with open(photo_path, 'rb') as photo:
        bot.send_photo(call.message.chat.id, photo, caption=caption_path1, parse_mode='HTML')
        bot.send_message(call.message.chat.id, caption_part2, parse_mode='HTML')
        bot.send_message(call.message.chat.id, caption_part3, parse_mode='HTML')
        bot.send_message(call.message.chat.id, caption_part4, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == 'Предложить материал')
def handle_support(call):
    functional_message = ("<b>Если у вас есть материал:</b>\n\n" 
                          "📜<i>• Курсовых</i>\n"
                          "📄<i>• Контрольных мероприятий</i>\n" 
                          "🔬<i>• Лабораторных работ</i>\n"
                          "📚<i>• Практических занятий</i>\n" 
                          "<b>\nВы хотите ими поделиться?</b>\n"
                          "Отлично! Для этого отправьте свой материал <a href='https://t.me/grandmaslippers'><i>администратору</i></a>"
                          " и мы внесем ваш материал в базу. 📥")
    bot.send_message(call.message.chat.id, functional_message, parse_mode='HTML', reply_markup=None)

"""Описание команды /help"""

@bot.message_handler(commands=['help'])
def help(message):
    commands_list = "/start - начать взаимодействие\n" \
                    "/help - список команд\n" \
                    "/info - информация о боте\n" \
                    "/support - помощь с учебой\n" \
                    "/mail - почты преподавателей"
    bot.send_message(message.chat.id, "Список доступных команд:\n\n{}".format(commands_list))

"""Описание команды /support"""

@bot.message_handler(commands=['support'])
def support(message):
    photo_laba = 'изображение_2023-01-15_014700858.png'

    commands_list = (
        "1. <b>Информатика</b> 💻\n"
        "2. <b>Математическое моделирование</b> 📊\n\n"
        "<b>Мы можем помочь выполнить ваши работы.</b> 🚀\n"
        "Для этого напишите <a href='https://t.me/grandmaslippers'><i>Сергею Баранову</i></a>📝\n"
        "<b>Формат обращения:</b>\n\n"
        "<i>1. ФИО</i>\n"
        "<i>2. Предмет</i>\n"
        "<i>3. Номер лабораторной работы</i>\n"
        "<i>4. Вариант</i>\n"
        "<i>5. Группа</i>\n"
        "<i>6. Преподаватель</i>\n\n"
        "Мы имеем более 100 успешных сданных лабораторных работ по этим предметам. 🏆\n\n"
        "<b>Гарантируем своевременное и качественное выполнение работы.</b> 🕒🌟"
    )

    # Отправляем фото и сообщение с HTML-разметкой
    with open(photo_laba, 'rb') as lab_photo:
        bot.send_photo(message.chat.id, lab_photo,
                       caption="Если у вас появились трудности по следующим предметам:\n\n{}".format(commands_list),
                       parse_mode="HTML")

"""Описание команды /mail"""

@bot.message_handler(commands=["mail"])
def help(message):
    commands_list = config_tg.commands_list
    bot.send_message(message.chat.id, "Список преподавателей:\n{}".format(commands_list), parse_mode='HTML')

"""Описание команды /start"""

# Начало работы программы
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    if not is_registered(user_id):
        register_user(user_id, username, first_name, last_name)
        bot.send_message(message.chat.id, f"Привет, {first_name}! Теперь вы зарегистрированы.")
    else:
        bot.send_message(message.chat.id, f"С возвращением, {first_name}!")


    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("Учеба📚")
    button_programs = types.KeyboardButton("Программы для учебы💻")
    button_links = types.KeyboardButton("Полезные ссылки🔗")
    button_servise = types.KeyboardButton("Сервисы⚙️")

    keyboard.row(button)
    keyboard.row(button_programs)
    keyboard.row(button_links,button_servise)

    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=keyboard)

# Обработчик для кнопки "Полезные ссылки🔗"
@bot.message_handler(func=lambda message: message.text == "Полезные ссылки🔗")
def links(message):

    links_path = config_tg.links_path
    links_message = config_tg.links_message
    with open(links_path, 'rb') as photo:
        bot.send_photo(message.chat.id, photo, caption=links_message, parse_mode='HTML')

# Обработчик для кнопки "Сервисы"
@bot.message_handler(func=lambda message: message.text == "Сервисы⚙️")
def servise(message):

    if str(message.from_user.id) in admins:
        servise_message = "Выберите сервис:"
        servise_keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

        button_discord = types.KeyboardButton("Discord🎮")
        button_konvert_to_pdf = types.KeyboardButton("Конвектор Word - PDF📝")
        button_return = types.KeyboardButton("Назад")

        servise_keyboard.add(button_discord, button_konvert_to_pdf, button_return)
        bot.send_message(message.chat.id, servise_message, reply_markup=servise_keyboard)

    else:
        bot.reply_to(message, "К сожалению, данный раздел пока не готов. В скором времени он будет доделан. Как только он будет функционировать, мы вам сообщим!")


# Обработчик для кнопки "Программы для учебы"
@bot.message_handler(func=lambda message: message.text == "Программы для учебы💻")
def send_materials(message):
    programs_link = config_tg.programs_link
    programs_list = config_tg.programs_list
    bot.send_message(message.chat.id, f"Вот ссылка: {programs_link}\n\nСписок имеющихся программ:\n\n{programs_list}", parse_mode="HTML")

# Обработчик нажатия на кнопку "Учеба"
@bot.message_handler(func=lambda message: message.text == "Учеба📚")
def handle_education(message):
    # Убираем кнопку "Учеба" с клавиатуры
    remove_keyboard = types.ReplyKeyboardRemove()
    # Отправляем клавиатуру выбора семестра
    bot.send_message(message.chat.id, "Выберите курс:", reply_markup=send_semester_keyboard())

@bot.message_handler(func=lambda message: message.text == "Назад")
def handle_education(message):
    # Убираем кнопку "Учеба" с клавиатуры
    remove_keyboard = types.ReplyKeyboardRemove()
    # Отправляем клавиатуру выбора семестра
    bot.send_message(message.chat.id, "Выберите курс:", reply_markup=send_semester_keyboard())

# Обработчик нажатия на кнопки выбора семестра
@bot.message_handler(func=lambda message: message.text in subjects_by_semester.keys())
def handle_semester(message):
    semester = message.text
    # Отправляем сообщение с всплывающей клавиатурой выбора предмета
    bot.send_message(message.chat.id, "Выберите предмет:", reply_markup=send_subject_keyboard(message, subjects_by_semester[semester]))


# Обработчик нажатия на кнопку "Назад"
@bot.message_handler(func=lambda message: message.text == "Меню")
def handle_back(message):

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("Учеба📚")
    button_programs = types.KeyboardButton("Программы для учебы💻")
    button_links = types.KeyboardButton("Полезные ссылки🔗")
    button_servise = types.KeyboardButton("Сервисы⚙️")

    keyboard.row(button)
    keyboard.row(button_programs)
    keyboard.row(button_links, button_servise)

    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "1 курс")
def handle_back(message):
    keyboard_1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_1.row("1 семестр", "2 семестр")
    keyboard_1.row("Назад")
    bot.send_message(message.chat.id, "Выберите семестр:", reply_markup=keyboard_1)

@bot.message_handler(func=lambda message: message.text == "2 курс")
def handle_back(message):
    keyboard_1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_1.row("3 семестр", "4 семестр")
    keyboard_1.row("Назад")
    bot.send_message(message.chat.id, "Выберите семестр:", reply_markup=keyboard_1)

@bot.message_handler(func=lambda message: message.text == "3 курс")
def handle_back(message):
    keyboard_1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_1.row("5 семестр", "6 семестр")
    keyboard_1.row("Назад")
    bot.send_message(message.chat.id, "Выберите семестр:", reply_markup=keyboard_1)



"""Работа конвектора PDF"""
@bot.message_handler(func=lambda message: message.text == "Конвектор Word - PDF📝")
def ask_for_document(message):
    bot.reply_to(message, "Отправь мне файл в формате Word, и я конвертирую его в PDF.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_path}"

        # Загрузка файла с сервера Telegram
        file_content = requests.get(file_url).content

        # Подготовка данных для загрузки на Convertio
        payload = {
            'apikey': CONVERTIO_API_KEY,
            'input': 'base64',
            'file': base64.b64encode(file_content).decode('utf-8'),
            'filename': message.document.file_name,
            'outputformat': 'pdf'
        }

        # Загрузка файла на Convertio
        response = requests.post(CONVERTIO_API_URL, json=payload)
        conversion_data = response.json()

        if conversion_data['status'] == 'ok':
            conversion_id = conversion_data['data']['id']
            bot.reply_to(message, f"Файл загружен...")

            # Ожидание завершения конвертации
            while True:
                status_response = requests.get(f"{CONVERTIO_API_URL}/{conversion_id}/status")
                status_data = status_response.json()

                if status_data['status'] != 'ok':
                    bot.reply_to(message, f"Ошибка при проверке статуса: {status_data}")
                    return

                if status_data['data']['step'] == 'finish':
                    break
                time.sleep(3)

            # Получение ссылки на конвертированный файл
            result_url = status_data['data']['output']['url']

            # Вывод отладочной информации
            #bot.reply_to(message, f"Отладочная информация: {json.dumps(status_data, indent=2)}")

            # Скачивание конвертированного файла и отправка пользователю
            pdf_content = requests.get(result_url).content
            bot.send_document(message.chat.id, (f"{message.document.file_name.split('.')[0]}.pdf", pdf_content))
        else:
            send_long_message(message.chat.id, f"Ошибка при конвертации: {conversion_data['error']}")
    except Exception as e:
        send_long_message(message.chat.id, f"Произошла ошибка: {str(e)}")

def send_long_message(chat_id, text):
    """Разбивает длинное сообщение на несколько более коротких и отправляет их по отдельности."""
    max_length = 4096  # Максимальная длина сообщения в Telegram
    for i in range(0, len(text), max_length):
        bot.send_message(chat_id, text[i:i+max_length])

"""Описание работы со словарями"""

# Функция для отправки сообщения с всплывающей клавиатурой выбора предмета
def send_subject_keyboard(message, subjects):
    # Создаем всплывающую клавиатуру с выбором предмета
    inline_keyboard = types.InlineKeyboardMarkup()
    for subject in subjects:
        subject_button = types.InlineKeyboardButton(subject, url=links_by_subject[subject])
        inline_keyboard.row(subject_button)
    return inline_keyboard

# Функция для отправки сообщения с клавиатурой выбора семестра
def send_semester_keyboard():
    # Создаем клавиатуру с выбором семестра
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("1 курс", "2 курс")
    keyboard.row("3 курс", "4 курс")
    keyboard.row("Меню")
    return keyboard

# Запускаем бота
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        for admin_id in admins:
            error_bot = f'''{str(e)}'''
            formatted_code = f"<pre><code>{error_bot}</code></pre>"
            bot.send_message(admin_id, f"Ошибка при запуске бота:{formatted_code}", parse_mode='HTML')
        time.sleep(5)  # Перезапускаем бота через 5 секунд, если произошла ошибка
