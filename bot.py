from flask import Flask, request
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import os
import requests

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://your-render-url.onrender.com")  # Замени на свой Render URL
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Инициализация Flask
app = Flask(__name__)

# Инициализация Telegram Application (асинхронный бот)
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
        prices=[LabeledPrice("Товар", 10000)],  # 100.00 сом
        start_parameter="test-payment",
    )

# Регистрируем команды
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("pay", pay))

# Обработка Telegram webhook
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        asyncio.run(bot_app.process_update(update))
    except Exception as e:
        print("Ошибка при обработке вебхука:", e)
    return "ok"

# Установка webhook и запуск Flask
if __name__ == "__main__":
    # Устанавливаем webhook (можно делать каждый раз — Telegram не против)
    response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    )
    print("Webhook setup response:", response.text)

    # Инициализируем Telegram application (асинхронно)
    asyncio.run(bot_app.initialize())

    # Flask run
    app.run(host="0.0.0.0", port=10000)
