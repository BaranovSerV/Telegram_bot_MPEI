import openai
import telebot
import logging
import os
import time

openai.api_key = 'sk-svcacct-ZWHxdjVKI--ZipPXsqR6X91mWFU3cMDhWQO1aDwt6pZAq8F8I042RklIi2FVhB8CT3BlbkFJAkZ8UPnqQfteWMkknvIR6ng7LsrhgKLdFo3g7bxJkpTUvKRoLV0ljgCcDJ8rasEA'
bot = telebot.TeleBot('6718122659:AAETeWZjwaEa6d5stXF_tNUwqSuWNA4A6bo')

log_dir = os.path.join(os.path.dirname(__file__), 'ChatGPT_Logs')

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(filename=os.path.join(log_dir, 'error.log'), level=logging.ERROR,
                    format='%(levelname)s: %(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 'Привет!\nЯ ChatGPT 3.5 Telegram Bot\U0001F916\nЗадай мне любой вопрос и я постараюсь на него ответиь')

def generate_response(prompt):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content


@bot.message_handler(commands=['bot'])
def command_message(message):
    prompt = message.text
    response = generate_response(prompt)
    bot.reply_to(message, text=response)


@bot.message_handler(func = lambda _: True)
def handle_message(message):
    prompt = message.text
    response = generate_response(prompt)
    bot.send_message(chat_id=message.from_user.id, text=response)


print('ChatGPT Bot is working')

while True:
    try:
        bot.polling()
    except (telebot.apihelper.ApiException, ConnectionError) as e:
        logging.error(str(e))
        time.sleep(5)
        continue
