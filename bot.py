import os
import logging
import requests
from flask import Flask, request
from telegram import Bot, Update, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, PreCheckoutQueryHandler, MessageHandler, Filters
import threading

# === Конфигурация ===
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")

if not TOKEN or not PROVIDER_TOKEN:
    raise ValueError("Не заданы переменные окружения BOT_TOKEN и PROVIDER_TOKEN")

# === Telegram Bot ===
bot = Bot(token=TOKEN)

# === Flask App ===
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)
logging.basicConfig(level=logging.INFO)

# === Настройка webhook ===
WEBHOOK_URL = f"https://your-app-name.onrender.com/{TOKEN}"  # ← замени на своё имя проекта
bot.delete_webhook()
bot.set_webhook(url=WEBHOOK_URL)

# === Flask маршруты ===
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return 'Бот работает!'

# === Telegram команды ===
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
    update.message.reply_text("✅ Оплата прошла успешно! Спасибо!")

# === Регистрация обработчиков ===
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('pay', pay))
dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))

# === Запуск Flask в отдельном потоке ===
def run_bot():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    thread = threading.Thread(target=run_bot)
    thread.start()
