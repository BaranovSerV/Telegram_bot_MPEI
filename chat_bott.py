import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Токены
TELEGRAM_TOKEN = '6718122659:AAETeWZjwaEa6d5stXF_tNUwqSuWNA4A6bo'
OPENAI_API_KEY = 'sk-svcacct-ZWHxdjVKI--ZipPXsqR6X91mWFU3cMDhWQO1aDwt6pZAq8F8I042RklIi2FVhB8CT3BlbkFJAkZ8UPnqQfteWMkknvIR6ng7LsrhgKLdFo3g7bxJkpTUvKRoLV0ljgCcDJ8rasEA'

# Настройка OpenAI API
openai.api_key = OPENAI_API_KEY


async def start(update: Update, context):
    await update.message.reply_text('Привет! Я бот с GPT. Напиши что-нибудь, и я отвечу!')


async def handle_message(update: Update, context):
    user_message = update.message.text

    # Запрос к OpenAI API
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=user_message,
            max_tokens=100
        )
        reply = response.choices[0].text.strip()
    except Exception as e:
        reply = f"Произошла ошибка: {str(e)}"

    await update.message.reply_text(reply)


def main():
    # Настройка бота
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Обработчики команд и сообщений
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    app.run_polling()


if __name__ == '__main__':
    main()
