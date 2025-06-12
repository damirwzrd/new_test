import os
import asyncio
import requests

from flask import Flask, request

from telegram import Update, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters
)

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://your-render-url.onrender.com")  # Укажи здесь реальный URL

if not TOKEN or not PAYMENT_PROVIDER:
    raise ValueError("BOT_TOKEN и PAYMENT_PROVIDER_TOKEN должны быть заданы в переменных окружения.")

WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Flask-приложение
app = Flask(__name__)

# Telegram Application
bot_app = Application.builder().token(TOKEN).build()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Нажми /pay чтобы оплатить.")

# Команда /pay
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_invoice(
        title="Покупка",
        description="Тестовая покупка через FreedomPay",
        payload="test_payload",
        provider_token=PAYMENT_PROVIDER,
        currency="KGS",
        prices=[LabeledPrice("Товар", 10000)],  # 100 сом = 10000 (в копейках)
        start_parameter="test-payment",
    )

# Обработка pre-checkout запроса
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

# Обработка успешной оплаты
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Спасибо! Платеж успешно прошел.")

# Регистрируем обработчики
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("pay", pay))
bot_app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
bot_app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

# Webhook обработка
@app.route(WEBHOOK_PATH, methods=["POST"])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.process_update(update)
    return "ok"

# Установка webhook и запуск
async def setup():
    print("Установка Webhook...")
    response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    )
    print("Ответ Telegram:", response.text)
    await bot_app.initialize()
    print("Бот инициализирован.")

# Запуск
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
    app.run(host="0.0.0.0", port=10000)
