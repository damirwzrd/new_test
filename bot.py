import logging
from uuid import uuid4
from telegram import Update, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)
from flask import Flask, request
import threading
import asyncio
import hashlib

# 🔐 Замените своими токенами или используйте переменные окружения
TOKEN = "8057853656:AAEbcvA5wrfm980x3G1Ldn419MiAsoBQewQ"
PROVIDER_TOKEN = "6450350554:LIVE:553348"
SECRET_KEY = "4wCFV3XRNYXI6bOF"  # для проверки pg_sig

# Логгирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-приложение
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "OK"

@flask_app.route("/result", methods=["POST"])
def handle_callback():
    data = request.form.to_dict()
    received_sig = data.get("pg_sig", "")
    script_name = "result"  # не включая .php

    # Удалим pg_sig перед сортировкой
    data.pop("pg_sig", None)

    # Отсортированные значения параметров
    sorted_values = [data[key] for key in sorted(data)]
    base_string = ";".join([script_name] + sorted_values + [SECRET_KEY])
    calculated_sig = hashlib.md5(base_string.encode()).hexdigest()

    if calculated_sig == received_sig:
        logger.info("✅ Подпись верна: %s", data)
        return "OK"
    else:
        logger.warning("❌ Неверная подпись. Получено: %s, Ожидалось: %s", received_sig, calculated_sig)
        return "invalid signature", 400

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Введите /pay чтобы протестировать оплату через FreedomPay.")

# Команда /pay
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = f"freedompay-test-{uuid4()}"
    prices = [LabeledPrice("Тестовый товар", 1000 * 100)]  # 1000 сомов
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="FreedomPay Тестовая покупка",
        description="Это тестовая оплата через FreedomPay",
        payload=payload,
        provider_token=PROVIDER_TOKEN,
        currency="KGS",
        prices=prices,
        need_name=True,
        is_flexible=False,
    )

# Обработка предварительной проверки оплаты
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("freedompay-test-"):
        await query.answer(ok=False, error_message="Ошибка проверки payload.")
    else:
        await query.answer(ok=True)
        logger.info("✅ PreCheckout подтверждён.")

# Обработка успешной оплаты
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("✅ Оплата прошла успешно!")
    await update.message.reply_text("✅ Спасибо! Оплата прошла успешно!")

# Основной запуск
async def main():
    # Фоновый запуск Flask-сервера
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Telegram-бот
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    await application.run_polling()

import nest_asyncio
import asyncio

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())

