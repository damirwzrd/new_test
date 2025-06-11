from flask import Flask, request
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests
import asyncio

# Настройки из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://new-test-axkz.onrender.com")  # заменишь на свой Render URL

WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Инициализация Flask
app = Flask(__name__)

# Инициализация Telegram Application
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
        prices=[LabeledPrice("Товар", 10000)],
        start_parameter="test-payment",
    )

# Регистрируем команды
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("pay", pay))

# Flask endpoint для Telegram Webhook
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.create_task(bot_app.process_update(update))
    return "ok"

# Установка Webhook один раз при запуске
@app.before_first_request
def init_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(bot_app.initialize())

    # Установить webhook
    response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")
    print("Webhook setup response:", response.text)

# Запуск Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
