import os
import logging
import requests
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters
import threading

# Загружаем токены из переменных окружения
TOKEN = os.getenv("TOKEN")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Указываем 1 worker для асинхронных колбеков
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

logging.basicConfig(level=logging.INFO)


@app.before_first_request
def setup_webhook():
    webhook_url = f"https://your-app-name.onrender.com/{TOKEN}"
    bot.delete_webhook()
    bot.set_webhook(url=webhook_url)


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
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
    currency = "KGS"
    price = 1000  # 10 сомов

    prices = [LabeledPrice("Товар", price * 100)]

    logging.info(f"Отправка инвойса: chat_id={chat_id}, price={price}")

    try:
        bot.send_invoice(
            chat_id, title, description, payload,
            PROVIDER_TOKEN, currency, prices
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке инвойса: {e}")
        update.message.reply_text(f"Ошибка при отправке: {e}")


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
    app.run(host='0.0.0.0', port=5000)


if __name__ == "__main__":
    thread = threading.Thread(target=run_bot)
    thread.start()
