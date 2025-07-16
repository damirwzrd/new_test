import logging
import requests
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters
import threading

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.DEBUG)

TOKEN = '7930232744:AAGIwrgqeCdYxtBLA6F8UuyFCr4AWauDTU4'
bot = Bot(token=TOKEN)

app = Flask(__name__)

# Указываем 1 worker для асинхронных колбеков
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

# Логирование информации
logging.basicConfig(level=logging.INFO)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    logging.info("Обработан запрос от Telegram: %s", update)
    return 'ok'

@app.route('/')
def index():
    return 'Бот работает!'

def start(update, context):
    update.message.reply_text("Привет! Введите /pay чтобы начать оплату.")

def pay(update, context):
    chat_id = update.message.chat_id
    title = "FreedomPay Тест"
    description = "Оплата товара"
    payload = "custom_payload"
    provider_token = "6450350554:LIVE:546523"
    currency = "KGS"
    price = 30

    prices = [LabeledPrice("Товар", price * 100)]

    logging.info(f"Отправка инвойса с параметрами: chat_id={chat_id}, title={title}, price={price}, provider_token={provider_token}")

    try:
        response = bot.send_invoice(
            chat_id, title, description, payload,
            provider_token, currency, prices
        )
        logging.info(f"Ответ на запрос: {response}")
    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        update.message.reply_text(f"Произошла ошибка при отправке инвойса: {e}")

def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != "custom_payload":
        query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        query.answer(ok=True)

def successful_payment_callback(update, context):
    update.message.reply_text("Оплата прошла успешно!")

dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('pay', pay))
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

def run_bot():
    import os
    PORT = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    thread = threading.Thread(target=run_bot)
    thread.start()
