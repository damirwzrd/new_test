import os
import asyncio
import requests
from flask import Flask, request

from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, ContextTypes

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "https://your-render-url.onrender.com")  # Заменить на свой URL
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Flask-приложение
app = Flask(__name__)

# Telegram Application
bot_app = Application.builder().token(TOKEN).build()

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Нажми /pay чтобы оплатить.")

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

# Webhook обработка
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    # Используем очередь обновлений, чтобы безопасно передать обновление
    bot_app.update_queue.put_nowait(update)
    return "ok"

# Установка webhook и инициализация бота
async def setup():
    # Устанавливаем webhook
    response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
    )
    print("Webhook setup response:", response.text)
    await bot_app.initialize()
    await bot_app.start()
    print("Bot started and initialized.")

# Flask запуск
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(setup())  # запускаем установку в фоне
    app.run(host="0.0.0.0", port=10000)
